# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog for the Mercurial server.
"""

import os

from PyQt6.QtCore import QProcess, QSize, Qt, pyqtSlot
from PyQt6.QtGui import QAction, QBrush, QTextCursor
from PyQt6.QtWidgets import QComboBox, QPlainTextEdit, QSpinBox, QToolBar

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricMainWindow import EricMainWindow

from .HgUtilities import getHgExecutable


class HgServeDialog(EricMainWindow):
    """
    Class implementing a dialog for the Mercurial server.
    """

    def __init__(self, vcs, path, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Hg
        @param path path of the repository to serve
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.vcs = vcs
        self.__repoPath = path

        self.__styles = [
            "paper",
            "coal",
            "gitweb",
            "monoblue",
            "spartan",
        ]

        self.setWindowTitle(self.tr("Mercurial Server"))

        iconSuffix = "dark" if ericApp().usesDarkPalette() else "light"

        self.__startAct = QAction(
            EricPixmapCache.getIcon(
                os.path.join(
                    "VcsPlugins",
                    "vcsMercurial",
                    "icons",
                    "startServer-{0}.svg".format(iconSuffix),
                )
            ),
            self.tr("Start Server"),
            self,
        )
        self.__startAct.triggered.connect(self.__startServer)
        self.__stopAct = QAction(
            EricPixmapCache.getIcon(
                os.path.join(
                    "VcsPlugins",
                    "vcsMercurial",
                    "icons",
                    "stopServer-{0}.svg".format(iconSuffix),
                )
            ),
            self.tr("Stop Server"),
            self,
        )
        self.__stopAct.triggered.connect(self.__stopServer)
        self.__browserAct = QAction(
            EricPixmapCache.getIcon("home"), self.tr("Start Browser"), self
        )
        self.__browserAct.triggered.connect(self.__startBrowser)

        self.__portSpin = QSpinBox(self)
        self.__portSpin.setMinimum(2048)
        self.__portSpin.setMaximum(65535)
        self.__portSpin.setToolTip(self.tr("Enter the server port"))
        self.__portSpin.setValue(self.vcs.getPlugin().getPreferences("ServerPort"))

        self.__styleCombo = QComboBox(self)
        self.__styleCombo.addItems(self.__styles)
        self.__styleCombo.setToolTip(self.tr("Select the style to use"))
        self.__styleCombo.setCurrentIndex(
            self.__styleCombo.findText(
                self.vcs.getPlugin().getPreferences("ServerStyle")
            )
        )

        self.__serverToolbar = QToolBar(self.tr("Server"), self)
        self.__serverToolbar.addAction(self.__startAct)
        self.__serverToolbar.addAction(self.__stopAct)
        self.__serverToolbar.addSeparator()
        self.__serverToolbar.addWidget(self.__portSpin)
        self.__serverToolbar.addWidget(self.__styleCombo)

        self.__browserToolbar = QToolBar(self.tr("Browser"), self)
        self.__browserToolbar.addAction(self.__browserAct)

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.__serverToolbar)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.__browserToolbar)

        self.__log = QPlainTextEdit(self)
        self.setCentralWidget(self.__log)

        # polish up the dialog
        self.__startAct.setEnabled(True)
        self.__stopAct.setEnabled(False)
        self.__browserAct.setEnabled(False)
        self.__portSpin.setEnabled(True)
        self.__styleCombo.setEnabled(True)
        self.resize(QSize(800, 600).expandedTo(self.minimumSizeHint()))

        self.process = QProcess()
        self.process.finished.connect(self.__procFinished)
        self.process.readyReadStandardOutput.connect(self.__readStdout)
        self.process.readyReadStandardError.connect(self.__readStderr)

        self.cNormalFormat = self.__log.currentCharFormat()
        self.cErrorFormat = self.__log.currentCharFormat()
        self.cErrorFormat.setForeground(QBrush(Preferences.getUI("LogStdErrColour")))

    def __startServer(self):
        """
        Private slot to start the Mercurial server.
        """
        port = self.__portSpin.value()
        style = self.__styleCombo.currentText()

        exe = getHgExecutable()

        args = self.vcs.initCommand("serve")
        args.append("-v")
        args.append("--port")
        args.append(str(port))
        args.append("--style")
        args.append(style)

        self.process.setWorkingDirectory(self.__repoPath)

        self.process.start(exe, args)
        procStarted = self.process.waitForStarted(5000)
        if procStarted:
            self.__startAct.setEnabled(False)
            self.__stopAct.setEnabled(True)
            self.__browserAct.setEnabled(True)
            self.__portSpin.setEnabled(False)
            self.__styleCombo.setEnabled(False)
            self.vcs.getPlugin().setPreferences("ServerPort", port)
            self.vcs.getPlugin().setPreferences("ServerStyle", style)
        else:
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path."
                ).format(exe),
            )

    def __stopServer(self):
        """
        Private slot to stop the Mercurial server.
        """
        if (
            self.process is not None
            and self.process.state() != QProcess.ProcessState.NotRunning
        ):
            self.process.terminate()
            self.process.waitForFinished(5000)
            if self.process.state() != QProcess.ProcessState.NotRunning:
                self.process.kill()

        self.__startAct.setEnabled(True)
        self.__stopAct.setEnabled(False)
        self.__browserAct.setEnabled(False)
        self.__portSpin.setEnabled(True)
        self.__styleCombo.setEnabled(True)

    def __startBrowser(self):
        """
        Private slot to start a browser for the served repository.
        """
        ui = ericApp().getObject("UserInterface")
        ui.launchHelpViewer("http://localhost:{0}".format(self.__portSpin.value()))

    def closeEvent(self, _evt):
        """
        Protected slot implementing a close event handler.

        @param _evt reference to the close event object (unused)
        @type QCloseEvent
        """
        self.__stopServer()

    @pyqtSlot(int, QProcess.ExitStatus)
    def __procFinished(self, _exitCode, _exitStatus):
        """
        Private slot connected to the finished signal.

        @param _exitCode exit code of the process (unused)
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
        """
        self.__stopServer()

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process and inserts it into the log.
        """
        if self.process is not None:
            s = str(
                self.process.readAllStandardOutput(), self.vcs.getEncoding(), "replace"
            )
            self.__appendText(s, False)

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the log.
        """
        if self.process is not None:
            s = str(
                self.process.readAllStandardError(), self.vcs.getEncoding(), "replace"
            )
            self.__appendText(s, True)

    def __appendText(self, txt, error=False):
        """
        Private method to append text to the end.

        @param txt text to insert
        @type str
        @param error flag indicating to insert error text
        @type bool
        """
        tc = self.__log.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.End)
        self.__log.setTextCursor(tc)
        if error:
            self.__log.setCurrentCharFormat(self.cErrorFormat)
        else:
            self.__log.setCurrentCharFormat(self.cNormalFormat)
        self.__log.insertPlainText(txt)
        self.__log.ensureCursorVisible()
