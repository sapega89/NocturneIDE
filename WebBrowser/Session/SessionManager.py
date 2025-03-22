# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the session manager.
"""

import contextlib
import functools
import json
import os
import pathlib
import shutil

from dataclasses import dataclass

from PyQt6.QtCore import (
    QByteArray,
    QDateTime,
    QDir,
    QObject,
    Qt,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QActionGroup
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

from eric7 import EricUtilities, Preferences
from eric7.EricCore import EricFileSystemWatcher
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow


@dataclass
class SessionMetaData:
    """
    Class implementing a data structure to store meta data for a session.
    """

    name: str = ""
    filePath: str = ""
    isActive: bool = False
    isDefault: bool = False
    isBackup: bool = False


class SessionManager(QObject):
    """
    Class implementing the session manager.

    @signal sessionsMetaDataChanged() emitted to indicate a change of the
        list of session meta data
    """

    sessionsMetaDataChanged = pyqtSignal()

    SwitchSession = 1
    CloneSession = 2
    ReplaceSession = SwitchSession | 4
    RestoreSession = 8

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        sessionsDirName = self.getSessionsDirectory()
        sessionsDir = QDir(sessionsDirName)
        if not sessionsDir.exists():
            sessionsDir.mkpath(sessionsDirName)

        self.__sessionMetaData = []
        # list containing meta data about saved sessions

        self.__sessionDefault = os.path.join(sessionsDirName, "session.json")
        self.__sessionBackup1 = os.path.join(sessionsDirName, "session.json.old")
        self.__sessionBackup2 = os.path.join(sessionsDirName, "session.json.old1")

        self.__lastActiveSession = Preferences.getWebBrowser("SessionLastActivePath")
        if not os.path.exists(self.__lastActiveSession):
            self.__lastActiveSession = self.__sessionDefault

        watcher = EricFileSystemWatcher.instance()
        watcher.directoryChanged.connect(self.__sessionDirectoryChanged)
        watcher.addPath(self.getSessionsDirectory())

        self.__backupSavedSession()

        self.__autoSaveTimer = None
        self.__shutdown = False

    def activateTimer(self):
        """
        Public method to activate the session save timer.
        """
        if self.__autoSaveTimer is None:
            self.__autoSaveTimer = QTimer()
            self.__autoSaveTimer.setSingleShot(True)
            self.__autoSaveTimer.timeout.connect(self.__autoSaveSession)
            self.__initSessionSaveTimer()

    def preferencesChanged(self):
        """
        Public slot to react upon changes of the settings.
        """
        self.__initSessionSaveTimer()

    def getSessionsDirectory(self):
        """
        Public method to get the directory sessions are stored in.

        @return name of the sessions directory
        @rtype str
        """
        return os.path.join(EricUtilities.getConfigDir(), "web_browser", "sessions")

    def defaultSessionFile(self):
        """
        Public method to get the name of the default session file.

        @return name of the default session file
        @rtype str
        """
        return self.__sessionDefault

    def lastActiveSessionFile(self):
        """
        Public method to get the name of the last active session file.

        @return name of the last active session file
        @rtype str
        """
        return self.__lastActiveSession

    def shutdown(self):
        """
        Public method to perform any shutdown actions.
        """
        self.__autoSaveTimer.stop()
        if not self.__shutdown:
            self.__autoSaveSession(startTimer=False)
            watcher = EricFileSystemWatcher.instance()
            watcher.removePath(self.getSessionsDirectory())
        self.__shutdown = True

    def autoSaveSession(self):
        """
        Public method to save the current session state.
        """
        self.__autoSaveSession(startTimer=False)

    def __initSessionSaveTimer(self):
        """
        Private slot to initialize the auto save timer.
        """
        self.__autoSaveInterval = (
            Preferences.getWebBrowser("SessionAutoSaveInterval") * 1000
        )

        if Preferences.getWebBrowser("SessionAutoSave"):
            if not self.__autoSaveTimer.isActive():
                self.__autoSaveTimer.start(self.__autoSaveInterval)
        else:
            self.__autoSaveTimer.stop()

    @pyqtSlot()
    def __autoSaveSession(self, startTimer=True):
        """
        Private slot to save the current session state.

        @param startTimer flag indicating to restart the timer
        @type bool
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        if not WebBrowserWindow.isPrivate():
            Preferences.setWebBrowser("SessionLastActivePath", self.__lastActiveSession)
            self.writeCurrentSession(self.__lastActiveSession)

        if startTimer:
            self.__autoSaveTimer.start(self.__autoSaveInterval)

    def writeCurrentSession(self, sessionFileName):
        """
        Public method to write the current session to the given file name.

        @param sessionFileName file name of the session
        @type str
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        sessionData = {"Windows": []}

        activeWindow = WebBrowserWindow.getWindow()
        for window in WebBrowserWindow.mainWindows():
            data = window.tabWidget().getSessionData()

            # add window geometry
            geometry = window.saveGeometry()
            data["WindowGeometry"] = bytes(geometry.toBase64()).decode("ascii")

            sessionData["Windows"].append(data)

            if window is activeWindow:
                sessionData["CurrentWindowIndex"] = len(sessionData["Windows"]) - 1

        if sessionData["Windows"]:
            with open(sessionFileName, "w") as sessionFile:
                json.dump(sessionData, sessionFile, indent=2)

    @classmethod
    def readSessionFromFile(cls, sessionFileName):
        """
        Class method to read the session data from a file.

        @param sessionFileName file name of the session file
        @type str
        @return dictionary containing the session data
        @rtype dict
        """
        try:
            with open(sessionFileName, "r") as sessionFile:
                sessionData = json.load(sessionFile)
            if not cls.isValidSession(sessionData):
                sessionData = {}
        except OSError:
            sessionData = {}

        return sessionData

    @classmethod
    def isValidSession(cls, session):
        """
        Class method to check the validity of a session.

        @param session dictionary containing the session data
        @type dict
        @return flag indicating validity
        @rtype bool
        """
        if not session:
            return False

        if "Windows" not in session:
            return False

        if not session["Windows"]:
            return False

        return True

    def __backupSavedSession(self):
        """
        Private method to backup the most recently saved session.
        """
        if os.path.exists(self.__lastActiveSession):
            if os.path.exists(self.__sessionBackup1):
                if os.path.exists(self.__sessionBackup2):
                    os.remove(self.__sessionBackup2)
                shutil.copy2(self.__sessionBackup1, self.__sessionBackup2)
                os.remove(self.__sessionBackup1)

            shutil.copy2(self.__lastActiveSession, self.__sessionBackup1)

    def sessionMetaData(self, includeBackups=False):
        """
        Public method to get the sessions meta data.

        @param includeBackups flag indicating to include backup sessions
        @type bool
        @return list of session meta data
        @rtype list of SessionMetaData
        """
        self.__fillMetaDataList()

        metaDataList = self.__sessionMetaData[:]

        if includeBackups and os.path.exists(self.__sessionBackup1):
            data = SessionMetaData(
                name=self.tr("Backup 1"),
                filePath=self.__sessionBackup1,
                isBackup=True,
            )
            metaDataList.append(data)

        if includeBackups and os.path.exists(self.__sessionBackup2):
            data = SessionMetaData(
                name=self.tr("Backup 2"),
                filePath=self.__sessionBackup2,
                isBackup=True,
            )
            metaDataList.append(data)

        return metaDataList

    def __fillMetaDataList(self):
        """
        Private method to fill the sessions meta data list.

        The sessions meta data list is only populated, if the variable holding
        it is empty (i.e. it is populated on demand).
        """
        if self.__sessionMetaData:
            return

        sessionFiles = list(pathlib.Path(self.getSessionsDirectory()).glob("*.json"))

        for sessionFile in sessionFiles:
            sessionData = self.readSessionFromFile(sessionFile.resolve())
            if not sessionData or not sessionData["Windows"]:
                continue

            data = SessionMetaData(
                name=sessionFile.stem,
                filePath=sessionFile.resolve(),
            )

            if sessionFile == pathlib.Path(self.defaultSessionFile()):
                data.name = self.tr("Default Session")
                data.isDefault = True

            if self.__isActive(sessionFile):
                data.isActive = True

            if data.isDefault:
                # default session is always first
                self.__sessionMetaData.insert(0, data)
            else:
                self.__sessionMetaData.append(data)

    def __isActive(self, filePath):
        """
        Private method to check, if a given file is the active one.

        @param filePath path of the session file to be checked
        @type str or pathlib.Path
        @return flag indicating the active file
        @rtype bool
        """
        return pathlib.Path(filePath) == pathlib.Path(self.__lastActiveSession)

    @pyqtSlot(str)
    def __sessionDirectoryChanged(self, path):
        """
        Private slot handling changes of the sessions directory.

        @param path name of the changed directory
        @type str
        """
        if path == self.getSessionsDirectory():
            self.__sessionMetaData = []

            self.sessionsMetaDataChanged.emit()

    @pyqtSlot()
    def aboutToShowSessionsMenu(self, menu):
        """
        Public slot to populate the sessions selection menu.

        @param menu reference to the menu about to be shown
        @type QMenu
        """
        menu.clear()

        actionGroup = QActionGroup(menu)
        sessions = self.sessionMetaData(includeBackups=False)
        for session in sessions:
            act = menu.addAction(session.name)
            act.setCheckable(True)
            act.setChecked(session.isActive)
            act.setData(session.filePath)
            actionGroup.addAction(act)
            act.triggered.connect(functools.partial(self.__sessionActTriggered, act))

    @pyqtSlot()
    def __sessionActTriggered(self, act):
        """
        Private slot to handle the menu selection of a session.

        @param act reference to the action that triggered
        @type QAction
        """
        path = act.data()
        self.switchToSession(path)

    def openSession(self, sessionFilePath, flags=0):
        """
        Public method to open a session from a given session file.

        @param sessionFilePath name of the session file to get session from
        @type str
        @param flags flags determining the open mode
        @type int
        """
        if self.__isActive(sessionFilePath):
            return

        sessionData = self.readSessionFromFile(sessionFilePath)
        if not sessionData or not sessionData["Windows"]:
            return

        window = WebBrowserWindow.mainWindow()

        if (flags & SessionManager.SwitchSession) == SessionManager.SwitchSession:
            # save the current session
            self.writeCurrentSession(self.__lastActiveSession)

            # create new window for the new session
            window = window.newWindow(restoreSession=True)

            # close all existing windows
            for win in WebBrowserWindow.mainWindows()[:]:
                if win is not window:
                    win.forceClose()

            if (flags & SessionManager.ReplaceSession) != SessionManager.ReplaceSession:
                self.__lastActiveSession = pathlib.Path(sessionFilePath).resolve()
                self.__sessionMetaData = []

        self.restoreSessionFromData(window, sessionData)

    @classmethod
    def restoreSessionFromData(cls, window=None, sessionData=None):
        """
        Class method to restore a session from a session data dictionary.

        @param window reference to main window to restore to
        @type WebBrowserWindow
        @param sessionData dictionary containing the session data
        @type dict
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        if window is None:
            window = WebBrowserWindow.mainWindow()

        with EricOverrideCursor():
            # restore session for first window
            data = sessionData["Windows"].pop(0)
            window.tabWidget().loadFromSessionData(data)
            if "WindowGeometry" in data:
                geometry = QByteArray.fromBase64(data["WindowGeometry"].encode("ascii"))
                window.restoreGeometry(geometry)
            QApplication.processEvents()

            # restore additional windows
            for data in sessionData["Windows"]:
                window = WebBrowserWindow.mainWindow().newWindow(restoreSession=True)
                window.tabWidget().loadFromSessionData(data)
                if "WindowGeometry" in data:
                    geometry = QByteArray.fromBase64(
                        data["WindowGeometry"].encode("ascii")
                    )
                    window.restoreGeometry(geometry)
                QApplication.processEvents()

        if "CurrentWindowIndex" in sessionData:
            currentWindowIndex = sessionData["CurrentWindowIndex"]
            with contextlib.suppress(IndexError):
                currentWindow = WebBrowserWindow.mainWindows()[currentWindowIndex]
                QTimer.singleShot(0, lambda: currentWindow.raise_())

    def renameSession(self, sessionFilePath, flags=0):
        """
        Public method to rename or clone a session.

        @param sessionFilePath name of the session file
        @type str
        @param flags flags determining a rename or clone operation
        @type int
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        suggestedName = pathlib.Path(sessionFilePath).stem
        if flags & SessionManager.CloneSession:
            suggestedName += "_cloned"
            title = self.tr("Clone Session")
        else:
            suggestedName += "_renamed"
            title = self.tr("Rename Session")
        newName, ok = QInputDialog.getText(
            WebBrowserWindow.getWindow(),
            title,
            self.tr("Please enter a new name:"),
            QLineEdit.EchoMode.Normal,
            suggestedName,
        )

        if not ok:
            return

        if not newName.endswith(".json"):
            newName += ".json"

        newSessionPath = os.path.join(self.getSessionsDirectory(), newName)
        if os.path.exists(newSessionPath):
            EricMessageBox.information(
                WebBrowserWindow.getWindow(),
                title,
                self.tr(
                    """The session file "{0}" exists already. Please"""
                    """ enter another name."""
                ).format(newName),
            )
            self.renameSession(sessionFilePath, flags)
            return

        if flags & SessionManager.CloneSession:
            if not shutil.copy(sessionFilePath, newSessionPath):
                EricMessageBox.critical(
                    WebBrowserWindow.getWindow(),
                    title,
                    self.tr("""An error occurred while cloning the session file."""),
                )
                return
        else:
            try:
                os.rename(sessionFilePath, newSessionPath)
            except OSError:
                EricMessageBox.critical(
                    WebBrowserWindow.getWindow(),
                    title,
                    self.tr("""An error occurred while renaming the session file."""),
                )
                return
            if self.__isActive(sessionFilePath):
                self.__lastActiveSession = newSessionPath
                self.__sessionMetaData = []

    def saveSession(self):
        """
        Public method to save the current session.
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        newName, ok = QInputDialog.getText(
            WebBrowserWindow.getWindow(),
            self.tr("Save Session"),
            self.tr("Please enter a name for the session:"),
            QLineEdit.EchoMode.Normal,
            self.tr("Saved Session ({0})").format(
                QDateTime.currentDateTime().toString("yyyy-MM-dd HH-mm-ss")
            ),
        )

        if not ok:
            return

        if not newName.endswith(".json"):
            newName += ".json"

        newSessionPath = os.path.join(self.getSessionsDirectory(), newName)
        if os.path.exists(newSessionPath):
            EricMessageBox.information(
                WebBrowserWindow.getWindow(),
                self.tr("Save Session"),
                self.tr(
                    """The session file "{0}" exists already. Please"""
                    """ enter another name."""
                ).format(newName),
            )
            self.saveSession()
            return

        self.writeCurrentSession(newSessionPath)

    def replaceSession(self, sessionFilePath):
        """
        Public method to replace the current session with the given one.

        @param sessionFilePath file name of the session file to replace with
        @type str
        @return flag indicating success
        @rtype bool
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        res = EricMessageBox.yesNo(
            WebBrowserWindow.getWindow(),
            self.tr("Restore Backup"),
            self.tr("""Are you sure you want to replace the current session?"""),
        )
        if res:
            self.openSession(sessionFilePath, SessionManager.ReplaceSession)
            return True
        else:
            return False

    def switchToSession(self, sessionFilePath):
        """
        Public method to switch the current session to the given one.

        @param sessionFilePath file name of the session file to switch to
        @type str
        @return flag indicating success
        @rtype bool
        """
        self.openSession(sessionFilePath, SessionManager.SwitchSession)
        return True

    def cloneSession(self, sessionFilePath):
        """
        Public method to clone a session.

        @param sessionFilePath file name of the session file to be cloned
        @type str
        """
        self.renameSession(sessionFilePath, SessionManager.CloneSession)

    def deleteSession(self, sessionFilePath):
        """
        Public method to delete a session.

        @param sessionFilePath file name of the session file to be deleted
        @type str
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        sfp = pathlib.Path(sessionFilePath)
        res = EricMessageBox.yesNo(
            WebBrowserWindow.getWindow(),
            self.tr("Delete Session"),
            self.tr("""Are you sure you want to delete session "{0}"?""").format(
                sfp.stem
            ),
        )
        if res:
            sfp.unlink()

    def newSession(self):
        """
        Public method to start a new session.
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        newName, ok = QInputDialog.getText(
            WebBrowserWindow.getWindow(),
            self.tr("New Session"),
            self.tr("Please enter a name for the new session:"),
            QLineEdit.EchoMode.Normal,
            self.tr("New Session ({0})").format(
                QDateTime.currentDateTime().toString("yyyy-MM-dd HH-mm-ss")
            ),
        )

        if not ok:
            return

        if not newName.endswith(".json"):
            newName += ".json"

        newSessionPath = os.path.join(self.getSessionsDirectory(), newName)
        if os.path.exists(newSessionPath):
            EricMessageBox.information(
                WebBrowserWindow.getWindow(),
                self.tr("New Session"),
                self.tr(
                    """The session file "{0}" exists already. Please"""
                    """ enter another name."""
                ).format(newName),
            )
            self.newSession()
            return

        self.writeCurrentSession(self.__lastActiveSession)

        # create new window for the new session and close all existing windows
        window = WebBrowserWindow.mainWindow().newWindow()
        for win in WebBrowserWindow.mainWindows():
            if win is not window:
                win.forceClose()

        self.__lastActiveSession = newSessionPath
        self.__autoSaveSession()

    def showSessionManagerDialog(self):
        """
        Public method to show the session manager dialog.
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        from .SessionManagerDialog import SessionManagerDialog

        dlg = SessionManagerDialog(WebBrowserWindow.getWindow())
        dlg.open()

    def selectSession(self):
        """
        Public method to select a session to be restored.

        @return name of the session file to be restored
        @rtype str
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        self.__fillMetaDataList()

        if self.__sessionMetaData:
            # skip, if no session file available
            dlg = QDialog(
                WebBrowserWindow.getWindow(), Qt.WindowType.WindowStaysOnTopHint
            )
            lbl = QLabel(self.tr("Please select the startup session:"))
            combo = QComboBox(dlg)
            buttonBox = QDialogButtonBox(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel,
                dlg,
            )
            buttonBox.accepted.connect(dlg.accept)
            buttonBox.rejected.connect(dlg.reject)

            layout = QVBoxLayout()
            layout.addWidget(lbl)
            layout.addWidget(combo)
            layout.addWidget(buttonBox)
            dlg.setLayout(layout)

            lastActiveSessionFilePath = pathlib.Path(self.__lastActiveSession)

            for metaData in self.__sessionMetaData:
                if pathlib.Path(metaData.filePath) != lastActiveSessionFilePath:
                    combo.addItem(metaData.name, metaData.filePath)
                else:
                    combo.insertItem(
                        0,
                        self.tr("{0} (last session)").format(metaData.name),
                        metaData.filePath,
                    )
            combo.setCurrentIndex(0)

            if dlg.exec() == QDialog.DialogCode.Accepted:
                session = combo.currentData()
                if session is None:
                    self.__lastActiveSession = self.__sessionDefault
                else:
                    self.__lastActiveSession = session

        return self.__lastActiveSession
