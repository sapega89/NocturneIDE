# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show a list of tags or branches.
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

from .Ui_GitTagBranchListDialog import Ui_GitTagBranchListDialog


class GitTagBranchListDialog(QDialog, Ui_GitTagBranchListDialog):
    """
    Class implementing a dialog to show a list of tags or branches.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Git
        @param parent parent widget
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

    def start(self, path, tags, listAll=True, merged=True):
        """
        Public slot to start the tag/branch list command.

        @param path name of directory to be listed
        @type str
        @param tags flag indicating a list of tags is requested
            (False = branches, True = tags)
        @type bool
        @param listAll flag indicating to show all tags or branches
        @type bool
        @param merged flag indicating to show only merged or non-merged
            branches
        @type bool
        """
        self.tagList.clear()

        self.errorGroup.hide()

        self.intercept = False
        self.tagsMode = tags
        if tags:
            self.tagList.setHeaderItem(
                QTreeWidgetItem(
                    [self.tr("Commit"), self.tr("Name"), self.tr("Annotation Message")]
                )
            )
        else:
            self.setWindowTitle(self.tr("Git Branches List"))
            self.tagList.setHeaderItem(
                QTreeWidgetItem([self.tr("Commit"), self.tr("Name")])
            )
        self.activateWindow()

        dname, _fname = self.vcs.splitPath(path)

        # find the root of the repo
        self.repodir = self.vcs.findRepoRoot(dname)
        if not self.repodir:
            return

        if self.tagsMode:
            args = self.vcs.initCommand("tag")
            args.append("--list")
            args.append("-n")
        else:
            args = self.vcs.initCommand("branch")
            args.append("--list")
            args.append("--all")
            args.append("--verbose")
            if not listAll:
                if merged:
                    args.append("--merged")
                else:
                    args.append("--no-merged")

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

    def __generateItem(
        self,
        commit,
        name,
        msg="",
        bold=False,
        italic=False,
        underlined=False,
        tooltip="",
    ):
        """
        Private method to generate a tag item in the tag list.

        @param commit commit id of the tag/branch
        @type str
        @param name name of the tag/branch
        @type str
        @param msg tag annotation message (defaults to "")
        @type str (optional)
        @param bold flag indicating to show the entry in bold (defaults to False)
        @type bool (optional)
        @param italic flag indicating to show the entry in italic (defaults to False)
        @type bool (optional)
        @param underlined flag indicating to show the entry underlined (defaults to
            False)
        @type bool (optional)
        @param tooltip tooltip string to be shown for the item (defaults to "")
        @type str (optional)
        """
        itm = QTreeWidgetItem(self.tagList)
        itm.setText(0, commit)
        itm.setText(1, name)
        if msg:
            itm.setText(2, msg)
        itm.setTextAlignment(0, Qt.AlignmentFlag.AlignRight)
        if tooltip:
            itm.setToolTip(1, tooltip)

        font = itm.font(1)
        if bold:
            font.setBold(True)
        if italic:
            font.setItalic(True)
        if underlined:
            font.setUnderline(True)
        itm.setFont(1, font)

    def __getCommit(self, tag):
        """
        Private method to get the commit id for a tag.

        @param tag tag name
        @type str
        @return commit id shortened to 10 characters
        @rtype str
        """
        args = self.vcs.initCommand("show")
        args.append("--abbrev-commit")
        args.append(
            "--abbrev={0}".format(self.vcs.getPlugin().getPreferences("CommitIdLength"))
        )
        args.append("--no-patch")
        args.append(tag)

        output = ""
        process = QProcess()
        process.setWorkingDirectory(self.repodir)
        process.start("git", args)
        procStarted = process.waitForStarted(5000)
        if procStarted:
            finished = process.waitForFinished(30000)
            if finished and process.exitCode() == 0:
                output = str(
                    process.readAllStandardOutput(),
                    Preferences.getSystem("IOEncoding"),
                    "replace",
                )

        if output:
            for line in output.splitlines():
                if line.startswith("commit "):
                    commitId = line.split()[1]
                    return commitId

        return ""

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
            self.__processOutputLine(s)

    def __processOutputLine(self, line):
        """
        Private method to process the lines of output.

        @param line output line to be processed
        @type str
        """
        if self.tagsMode:
            name, msg = line.strip().split(None, 1)
            commit = self.__getCommit(name)
            self.__generateItem(commit, name, msg=msg.strip())
        else:
            tooltip = ""
            bold = underlined = False
            if line.startswith("* "):
                bold = True
                tooltip = self.tr("current branch")
            elif line.startswith("+ "):
                underlined = True
                tooltip = self.tr("checked out in linked worktree")
            line = line[2:]
            if line.startswith("("):
                name, line = line[1:].split(")", 1)
                commit = line.strip().split(None, 1)[0]
            else:
                data = line.split(None, 2)
                if data[1].startswith("->"):
                    name = " ".join(line.strip().split())
                    commit = ""
                else:
                    commit = data[1]
                    name = data[0]
            italic = name.startswith("remotes/")
            self.__generateItem(
                commit,
                name,
                bold=bold,
                italic=italic,
                underlined=underlined,
                tooltip=tooltip,
            )

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
