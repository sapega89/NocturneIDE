# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the results of the git describe action.
"""

import os

from PyQt6.QtCore import QCoreApplication, QProcess, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLineEdit,
    QTreeWidgetItem,
)

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.Globals import strToQByteArray

from .Ui_GitDescribeDialog import Ui_GitDescribeDialog


class GitDescribeDialog(QDialog, Ui_GitDescribeDialog):
    """
    Class implementing a dialog to show the results of the git describe action.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Git
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.process = QProcess()
        self.vcs = vcs

        self.tagList.headerItem().setText(self.tagList.columnCount(), "")
        self.tagList.header().setSortIndicator(1, Qt.SortOrder.AscendingOrder)

        self.process.finished.connect(self.__procFinished)
        self.process.readyReadStandardOutput.connect(self.__readStdout)
        self.process.readyReadStandardError.connect(self.__readStderr)

        self.show()
        QCoreApplication.processEvents()

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        if (
            self.process is not None
            and self.process.state() != QProcess.ProcessState.NotRunning
        ):
            self.process.terminate()
            QTimer.singleShot(2000, self.process.kill)
            self.process.waitForFinished(3000)

        e.accept()

    def start(self, path, commits):
        """
        Public slot to start the tag/branch list command.

        @param path name of directory to be listed
        @type str
        @param commits list of commits to be described
        @type list of str
        """
        self.tagList.clear()
        self.errorGroup.hide()

        self.intercept = False
        self.activateWindow()

        self.__commits = commits[:]
        self.__tagInfoLines = []

        dname, _fname = self.vcs.splitPath(path)

        # find the root of the repo
        self.repodir = self.vcs.findRepoRoot(dname)
        if not self.repodir:
            return

        args = self.vcs.initCommand("describe")
        args.append(
            "--abbrev={0}".format(self.vcs.getPlugin().getPreferences("CommitIdLength"))
        )
        if commits:
            args.extend(commits)
        else:
            args.append("--dirty")

        self.process.kill()
        self.process.setWorkingDirectory(self.repodir)

        self.process.start("git", args)
        procStarted = self.process.waitForStarted(5000)
        if not procStarted:
            self.inputGroup.setEnabled(False)
            self.inputGroup.hide()
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "The process {0} could not be started. "
                    "Ensure, that it is in the search path."
                ).format("git"),
            )
        else:
            self.inputGroup.setEnabled(True)
            self.inputGroup.show()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed
        the button.
        """
        if (
            self.process is not None
            and self.process.state() != QProcess.ProcessState.NotRunning
        ):
            self.process.terminate()
            QTimer.singleShot(2000, self.process.kill)
            self.process.waitForFinished(3000)

        self.inputGroup.setEnabled(False)
        self.inputGroup.hide()

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        self.__resizeColumns()
        self.__resort()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.__finish()

    @pyqtSlot(int, QProcess.ExitStatus)
    def __procFinished(self, _exitCode, _exitStatus):
        """
        Private slot connected to the finished signal.

        @param _exitCode exit code of the process (unused)
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
        """
        if self.__tagInfoLines:
            if self.__commits:
                for commit, tagInfo in zip(self.__commits, self.__tagInfoLines):
                    QTreeWidgetItem(self.tagList, [commit, tagInfo])
            else:
                for tagInfo in self.__tagInfoLines:
                    QTreeWidgetItem(self.tagList, ["", tagInfo])

        self.__finish()

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.tagList.sortItems(
            self.tagList.sortColumn(), self.tagList.header().sortIndicatorOrder()
        )

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.tagList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.tagList.header().setStretchLastSection(True)

    def __readStdout(self):
        """
        Private slot to handle the readyReadStdout signal.

        It reads the output of the process, formats it and inserts it into
        the contents pane.
        """
        self.process.setReadChannel(QProcess.ProcessChannel.StandardOutput)

        while self.process.canReadLine():
            s = str(
                self.process.readLine(), Preferences.getSystem("IOEncoding"), "replace"
            )
            self.__tagInfoLines.append(s.strip())

    def __readStderr(self):
        """
        Private slot to handle the readyReadStderr signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        if self.process is not None:
            s = str(
                self.process.readAllStandardError(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.errorGroup.show()
            self.errors.insertPlainText(s)
            self.errors.ensureCursorVisible()

    def on_passwordCheckBox_toggled(self, isOn):
        """
        Private slot to handle the password checkbox toggled.

        @param isOn flag indicating the status of the check box
        @type bool
        """
        if isOn:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
        else:
            self.input.setEchoMode(QLineEdit.EchoMode.Normal)

    @pyqtSlot()
    def on_sendButton_clicked(self):
        """
        Private slot to send the input to the git process.
        """
        inputTxt = self.input.text()
        inputTxt += os.linesep

        if self.passwordCheckBox.isChecked():
            self.errors.insertPlainText(os.linesep)
            self.errors.ensureCursorVisible()
        else:
            self.errors.insertPlainText(inputTxt)
            self.errors.ensureCursorVisible()

        self.process.write(strToQByteArray(inputTxt))

        self.passwordCheckBox.setChecked(False)
        self.input.clear()

    def on_input_returnPressed(self):
        """
        Private slot to handle the press of the return key in the input field.
        """
        self.intercept = True
        self.on_sendButton_clicked()

    def keyPressEvent(self, evt):
        """
        Protected slot to handle a key press event.

        @param evt the key press event
        @type QKeyEvent
        """
        if self.intercept:
            self.intercept = False
            evt.accept()
            return

        super().keyPressEvent(evt)
