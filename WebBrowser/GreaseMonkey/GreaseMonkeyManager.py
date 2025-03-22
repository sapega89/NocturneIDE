# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the manager for GreaseMonkey scripts.
"""

import contextlib
import os
import pathlib

from PyQt6.QtCore import (
    Q_ARG,
    QCoreApplication,
    QDir,
    QMetaObject,
    QObject,
    QSettings,
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtWidgets import QDialog

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.WebBrowser.JavaScript.ExternalJsObject import ExternalJsObject
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .GreaseMonkeyJsObject import GreaseMonkeyJsObject


class GreaseMonkeyManager(QObject):
    """
    Class implementing the manager for GreaseMonkey scripts.

    @signal scriptsChanged() emitted to indicate a change of scripts
    """

    scriptsChanged = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__disabledScripts = []
        self.__scripts = []
        self.__downloaders = []

        self.__jsObject = GreaseMonkeyJsObject(self)

        QTimer.singleShot(0, self.__load)

    def showConfigurationDialog(self, parent=None):
        """
        Public method to show the configuration dialog.

        @param parent reference to the parent widget
        @type QWidget
        """
        from .GreaseMonkeyConfiguration import GreaseMonkeyConfigurationDialog

        self.__configDiaolg = (
            GreaseMonkeyConfigurationDialog.GreaseMonkeyConfigurationDialog(
                self, parent
            )
        )
        self.__configDiaolg.show()

    def downloadScript(self, url):
        """
        Public method to download a GreaseMonkey script.

        @param url URL to download script from
        @type QUrl
        """
        QMetaObject.invokeMethod(
            self,
            "doDownloadScript",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(QUrl, url),
        )

    @pyqtSlot(QUrl)
    def doDownloadScript(self, url):
        """
        Public slot to download a GreaseMonkey script.

        Note: The download needed to be separated in the invoking part
        (s.a.) and the one doing the real download because the invoking
        part runs in a different thread (i.e. the web engine thread).

        @param url URL to download script from
        @type QUrl
        """
        from .GreaseMonkeyDownloader import (
            GreaseMonkeyDownloader,
            GreaseMonkeyDownloadType,
        )

        downloader = GreaseMonkeyDownloader(
            url, self, GreaseMonkeyDownloadType.MainScript
        )
        downloader.finished.connect(lambda f: self.__downloaderFinished(f, downloader))
        self.__downloaders.append(downloader)

    def __downloaderFinished(self, fileName, downloader):
        """
        Private slot to handle the completion of a script download.

        @param fileName name of the downloaded script
        @type str
        @param downloader reference to the downloader object
        @type GreaseMonkeyDownloader
        """
        from .GreaseMonkeyAddScriptDialog import GreaseMonkeyAddScriptDialog
        from .GreaseMonkeyScript import GreaseMonkeyScript

        if downloader in self.__downloaders:
            self.__downloaders.remove(downloader)

            deleteScript = True
            script = GreaseMonkeyScript(self, fileName)
            if script.isValid():
                if not self.containsScript(script.fullName()):
                    dlg = GreaseMonkeyAddScriptDialog(self, script)
                    deleteScript = dlg.exec() != QDialog.DialogCode.Accepted
                else:
                    EricMessageBox.information(
                        None,
                        QCoreApplication.translate(
                            "GreaseMonkeyManager", "Install GreaseMonkey Script"
                        ),
                        QCoreApplication.translate(
                            "GreaseMonkeyManager", """'{0}' is already installed."""
                        ).format(script.fullName()),
                    )

            if deleteScript:
                with contextlib.suppress(OSError):
                    os.remove(fileName)

    def scriptsDirectory(self):
        """
        Public method to get the path of the scripts directory.

        @return path of the scripts directory
        @rtype str
        """
        return os.path.join(EricUtilities.getConfigDir(), "web_browser", "greasemonkey")

    def requireScriptsDirectory(self):
        """
        Public method to get the path of the scripts directory.

        @return path of the scripts directory
        @rtype str
        """
        return os.path.join(self.scriptsDirectory(), "requires")

    def requireScripts(self, urlList):
        """
        Public method to get the sources of all required scripts.

        @param urlList list of URLs
        @type list of str
        @return sources of all required scripts
        @rtype str
        """
        requiresDir = QDir(self.requireScriptsDirectory())
        if not requiresDir.exists() or len(urlList) == 0:
            return ""

        script = ""

        settings = QSettings(
            os.path.join(self.requireScriptsDirectory(), "requires.ini"),
            QSettings.Format.IniFormat,
        )
        settings.beginGroup("Files")
        for url in urlList:
            if settings.contains(url):
                fileName = settings.value(url)
                if not pathlib.Path(fileName).is_absolute():
                    fileName = os.path.join(self.requireScriptsDirectory(), fileName)
                try:
                    with open(fileName, "r", encoding="utf-8") as f:
                        source = f.read().strip()
                except OSError:
                    source = ""
                if source:
                    script += source + "\n"

        return script

    def saveConfiguration(self):
        """
        Public method to save the configuration.
        """
        Preferences.setWebBrowser("GreaseMonkeyDisabledScripts", self.__disabledScripts)

    def allScripts(self):
        """
        Public method to get a list of all scripts.

        @return list of all scripts (list o
        @rtype GreaseMonkeyScript
        """
        return self.__scripts[:]

    def containsScript(self, fullName):
        """
        Public method to check, if the given script exists.

        @param fullName full name of the script
        @type str
        @return flag indicating the existence
        @rtype bool
        """
        return any(script.fullName() == fullName for script in self.__scripts)

    def enableScript(self, script):
        """
        Public method to enable the given script.

        @param script script to be enabled
        @type GreaseMonkeyScript
        """
        script.setEnabled(True)
        fullName = script.fullName()
        if fullName in self.__disabledScripts:
            self.__disabledScripts.remove(fullName)

        collection = WebBrowserWindow.webProfile().scripts()
        collection.insert(script.webScript())

    def disableScript(self, script):
        """
        Public method to disable the given script.

        @param script script to be disabled
        @type GreaseMonkeyScript
        """
        script.setEnabled(False)
        fullName = script.fullName()
        if fullName not in self.__disabledScripts:
            self.__disabledScripts.append(fullName)

        collection = WebBrowserWindow.webProfile().scripts()
        foundScripts = collection.find(fullName)
        if foundScripts:
            collection.remove(foundScripts[0])

    def addScript(self, script):
        """
        Public method to add a script.

        @param script script to be added
        @type GreaseMonkeyScript
        @return flag indicating success
        @rtype bool
        """
        if not script or not script.isValid():
            return False

        self.__scripts.append(script)
        script.scriptChanged.connect(lambda: self.__scriptChanged(script))

        collection = WebBrowserWindow.webProfile().scripts()
        collection.insert(script.webScript())

        self.scriptsChanged.emit()
        return True

    def removeScript(self, script, removeFile=True):
        """
        Public method to remove a script.

        @param script script to be removed
        @type GreaseMonkeyScript
        @param removeFile flag indicating to remove the script file as well
        @type bool
        @return flag indicating success
        @rtype bool
        """
        if not script:
            return False

        with contextlib.suppress(ValueError):
            self.__scripts.remove(script)

        fullName = script.fullName()
        collection = WebBrowserWindow.webProfile().scripts()
        foundScripts = collection.find(fullName)
        if foundScripts:
            collection.remove(foundScripts[0])

        if fullName in self.__disabledScripts:
            self.__disabledScripts.remove(fullName)

        if removeFile:
            os.unlink(script.fileName())
            del script

        self.scriptsChanged.emit()
        return True

    def canRunOnScheme(self, scheme):
        """
        Public method to check, if scripts can be run on a scheme.

        @param scheme scheme to check
        @type str
        @return flag indicating, that scripts can be run
        @rtype bool
        """
        return scheme in ["http", "https", "data", "ftp"]

    def __load(self):
        """
        Private slot to load the available scripts into the manager.
        """
        from .GreaseMonkeyScript import GreaseMonkeyScript

        scriptsDir = QDir(self.scriptsDirectory())
        if not scriptsDir.exists():
            scriptsDir.mkpath(self.scriptsDirectory())

        if not scriptsDir.exists("requires"):
            scriptsDir.mkdir("requires")

        self.__disabledScripts = Preferences.getWebBrowser(
            "GreaseMonkeyDisabledScripts"
        )

        for fileName in scriptsDir.entryList(["*.js"], QDir.Filter.Files):
            absolutePath = scriptsDir.absoluteFilePath(fileName)
            script = GreaseMonkeyScript(self, absolutePath)

            if not script.isValid():
                del script
                continue

            self.__scripts.append(script)

            if script.fullName() in self.__disabledScripts:
                script.setEnabled(False)
            else:
                collection = WebBrowserWindow.webProfile().scripts()
                collection.insert(script.webScript())

        self.__jsObject.setSettingsFile(
            os.path.join(
                EricUtilities.getConfigDir(), "web_browser", "greasemonkey_values.ini"
            )
        )
        ExternalJsObject.registerExtraObject("GreaseMonkey", self.__jsObject)

    def __scriptChanged(self, script):
        """
        Private slot handling a changed script.

        @param script reference to the changed script
        @type GreaseMonkeyScript
        """
        fullName = script.fullName()
        collection = WebBrowserWindow.webProfile().scripts()
        foundScripts = collection.find(fullName)
        if foundScripts:
            collection.remove(foundScripts[0])
        collection.insert(script.webScript())
