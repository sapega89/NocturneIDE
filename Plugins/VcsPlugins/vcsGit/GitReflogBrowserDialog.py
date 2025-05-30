# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to browse the reflog history.
"""

import os

from PyQt6.QtCore import QPoint, QProcess, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QHeaderView,
    QLineEdit,
    QTreeWidgetItem,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursorProcess
from eric7.EricWidgets import EricMessageBox
from eric7.Globals import strToQByteArray

from .Ui_GitReflogBrowserDialog import Ui_GitReflogBrowserDialog


class GitReflogBrowserDialog(QWidget, Ui_GitReflogBrowserDialog):
    """
    Class implementing a dialog to browse the reflog history.
    """

    CommitIdColumn = 0
    SelectorColumn = 1
    NameColumn = 2
    OperationColumn = 3
    SubjectColumn = 4

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

        self.__position = QPoint()

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.logTree.headerItem().setText(self.logTree.columnCount(), "")

        self.refreshButton = self.buttonBox.addButton(
            self.tr("&Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(self.tr("Press to refresh the list of commits"))
        self.refreshButton.setEnabled(False)

        self.vcs = vcs

        self.__formatTemplate = (
            "format:recordstart%n"
            "commit|%h%n"
            "selector|%gd%n"
            "name|%gn%n"
            "subject|%gs%n"
            "recordend%n"
        )

        self.repodir = ""
        self.__currentCommitId = ""

        self.__initData()
        self.__resetUI()

        self.__process = EricOverrideCursorProcess()
        self.__process.finished.connect(self.__procFinished)
        self.__process.readyReadStandardOutput.connect(self.__readStdout)
        self.__process.readyReadStandardError.connect(self.__readStderr)

    def __initData(self):
        """
        Private method to (re-)initialize some data.
        """
        self.buf = []  # buffer for stdout
        self.__started = False
        self.__skipEntries = 0

    def closeEvent(self, e):
        """
        Protected slot implementing a close event handler.

        @param e close event
        @type QCloseEvent
        """
        if (
            self.__process is not None
            and self.__process.state() != QProcess.ProcessState.NotRunning
        ):
            self.__process.terminate()
            QTimer.singleShot(2000, self.__process.kill)
            self.__process.waitForFinished(3000)

        self.__position = self.pos()

        e.accept()

    def show(self):
        """
        Public slot to show the dialog.
        """
        if not self.__position.isNull():
            self.move(self.__position)
        self.__resetUI()

        super().show()

    def __resetUI(self):
        """
        Private method to reset the user interface.
        """
        self.limitSpinBox.setValue(self.vcs.getPlugin().getPreferences("LogLimit"))

        self.logTree.clear()

    def __resizeColumnsLog(self):
        """
        Private method to resize the log tree columns.
        """
        self.logTree.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.logTree.header().setStretchLastSection(True)

    def __generateReflogItem(self, commitId, selector, name, subject):
        """
        Private method to generate a reflog tree entry.

        @param commitId commit id info
        @type str
        @param selector selector info
        @type str
        @param name name info
        @type str
        @param subject subject of the reflog entry
        @type str
        @return reference to the generated item
        @rtype QTreeWidgetItem
        """
        try:
            operation, subject = subject.strip().split(": ", 1)
        except ValueError:
            operation = ""

        return QTreeWidgetItem(
            self.logTree,
            [
                commitId,
                selector,
                name,
                operation,
                subject,
            ],
        )

    def __getReflogEntries(self, skip=0):
        """
        Private method to retrieve reflog entries from the repository.

        @param skip number of reflog entries to skip
        @type int
        """
        self.refreshButton.setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)
        QApplication.processEvents()

        self.buf = []
        self.cancelled = False
        self.errors.clear()
        self.intercept = False

        args = self.vcs.initCommand("log")
        args.append("--walk-reflogs")
        args.append("--max-count={0}".format(self.limitSpinBox.value()))
        args.append(
            "--abbrev={0}".format(self.vcs.getPlugin().getPreferences("CommitIdLength"))
        )
        args.append("--format={0}".format(self.__formatTemplate))
        args.append("--skip={0}".format(skip))

        self.__process.kill()

        self.__process.setWorkingDirectory(self.repodir)

        self.inputGroup.setEnabled(True)
        self.inputGroup.show()

        self.__process.start("git", args)
        procStarted = self.__process.waitForStarted(5000)
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

    def start(self, projectdir):
        """
        Public slot to start the git log command.

        @param projectdir directory name of the project
        @type str
        """
        self.errorGroup.hide()
        QApplication.processEvents()

        self.__initData()

        # find the root of the repo
        self.repodir = self.vcs.findRepoRoot(projectdir)
        if not self.repodir:
            return

        self.activateWindow()
        self.raise_()

        self.logTree.clear()
        self.__started = True
        self.__getReflogEntries()

    @pyqtSlot(int, QProcess.ExitStatus)
    def __procFinished(self, _exitCode, _exitStatus):
        """
        Private slot connected to the finished signal.

        @param _exitCode exit code of the process (unused)
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
        """
        self.__processBuffer()
        self.__finish()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed
        the button.
        """
        if (
            self.__process is not None
            and self.__process.state() != QProcess.ProcessState.NotRunning
        ):
            self.__process.terminate()
            QTimer.singleShot(2000, self.__process.kill)
            self.__process.waitForFinished(3000)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)

        self.inputGroup.setEnabled(False)
        self.inputGroup.hide()
        self.refreshButton.setEnabled(True)

    def __processBuffer(self):
        """
        Private method to process the buffered output of the git log command.
        """
        noEntries = 0

        for line in self.buf:
            line = line.rstrip()
            if line == "recordstart":
                logEntry = {}
            elif line == "recordend":
                if len(logEntry) > 1:
                    self.__generateReflogItem(
                        logEntry["commit"],
                        logEntry["selector"],
                        logEntry["name"],
                        logEntry["subject"],
                    )
                    noEntries += 1
            else:
                try:
                    key, value = line.split("|", 1)
                except ValueError:
                    key = ""
                    value = line
                if key in ("commit", "selector", "name", "subject"):
                    logEntry[key] = value.strip()

        self.__resizeColumnsLog()

        if self.__started:
            self.logTree.setCurrentItem(self.logTree.topLevelItem(0))
            self.__started = False

        self.__skipEntries += noEntries
        if noEntries < self.limitSpinBox.value() and not self.cancelled:
            self.nextButton.setEnabled(False)
            self.limitSpinBox.setEnabled(False)
        else:
            self.nextButton.setEnabled(True)
            self.limitSpinBox.setEnabled(True)

        # restore current item
        if self.__currentCommitId:
            items = self.logTree.findItems(
                self.__currentCommitId, Qt.MatchFlag.MatchExactly, self.CommitIdColumn
            )
            if items:
                self.logTree.setCurrentItem(items[0])
                self.__currentCommitId = ""

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process and inserts it into a buffer.
        """
        self.__process.setReadChannel(QProcess.ProcessChannel.StandardOutput)

        while self.__process.canReadLine():
            line = str(
                self.__process.readLine(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.buf.append(line)

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        if self.__process is not None:
            s = str(
                self.__process.readAllStandardError(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.__showError(s)

    def __showError(self, out):
        """
        Private slot to show some error.

        @param out error to be shown
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(out)
        self.errors.ensureCursorVisible()

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel):
            self.cancelled = True
            self.__finish()
        elif button == self.refreshButton:
            self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the log.
        """
        # save the current item's commit ID
        itm = self.logTree.currentItem()
        if itm is not None:
            self.__currentCommitId = itm.text(self.CommitIdColumn)
        else:
            self.__currentCommitId = ""

        self.start(self.repodir)

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
        self.errorGroup.show()

        self.__process.write(strToQByteArray(inputTxt))

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

    @pyqtSlot()
    def on_nextButton_clicked(self):
        """
        Private slot to handle the Next button.
        """
        if self.__skipEntries > 0:
            self.__getReflogEntries(self.__skipEntries)
