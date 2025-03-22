# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show a list of tags or branches.
"""

import os
import re

from PyQt6.QtCore import QProcess, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QTreeWidgetItem,
)

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.Globals import strToQByteArray

from .Ui_SvnTagBranchListDialog import Ui_SvnTagBranchListDialog


class SvnTagBranchListDialog(QDialog, Ui_SvnTagBranchListDialog):
    """
    Class implementing a dialog to show a list of tags or branches.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Subversion
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.vcs = vcs
        self.tagsList = None
        self.allTagsList = None

        self.tagList.headerItem().setText(self.tagList.columnCount(), "")
        self.tagList.header().setSortIndicator(3, Qt.SortOrder.AscendingOrder)

        self.process = QProcess()
        self.process.finished.connect(self.__procFinished)
        self.process.readyReadStandardOutput.connect(self.__readStdout)
        self.process.readyReadStandardError.connect(self.__readStderr)

        self.rx_list = re.compile(
            r"""\w*\s*(\d+)\s+(\w+)\s+\d*\s*"""
            r"""((?:\w+\s+\d+|[0-9.]+\s+\w+)\s+[0-9:]+)\s+(.+)/\s*"""
        )

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

    def start(self, path, tags, tagsList, allTagsList):
        """
        Public slot to start the svn status command.

        @param path name of directory to be listed
        @type str
        @param tags flag indicating a list of tags is requested
            (False = branches, True = tags)
        @type bool
        @param tagsList reference to string list receiving the tags
        @type list of str
        @param allTagsList reference to string list all tags
        @type list of str
        """
        self.errorGroup.hide()

        self.tagList.clear()

        self.intercept = False
        if not tags:
            self.setWindowTitle(self.tr("Subversion Branches List"))
        self.activateWindow()

        self.tagsList = tagsList
        self.allTagsList = allTagsList
        dname, _fname = self.vcs.splitPath(path)

        self.process.kill()

        reposURL = self.vcs.svnGetReposName(dname)
        if reposURL is None:
            EricMessageBox.critical(
                self,
                self.tr("Subversion Error"),
                self.tr(
                    """The URL of the project repository could not be"""
                    """ retrieved from the working copy. The list operation"""
                    """ will be aborted"""
                ),
            )
            self.close()
            return

        args = []
        args.append("list")
        self.vcs.addArguments(args, self.vcs.options["global"])
        args.append("--verbose")

        if self.vcs.otherData["standardLayout"]:
            # determine the base path of the project in the repository
            rx_base = re.compile("(.+)/(trunk|tags|branches).*")
            match = rx_base.fullmatch(reposURL)
            if match is None:
                EricMessageBox.critical(
                    self,
                    self.tr("Subversion Error"),
                    self.tr(
                        """The URL of the project repository has an"""
                        """ invalid format. The list operation will"""
                        """ be aborted"""
                    ),
                )
                return

            reposRoot = match.group(1)

            if tags:
                args.append("{0}/tags".format(reposRoot))
            else:
                args.append("{0}/branches".format(reposRoot))
            self.path = None
        else:
            reposPath, ok = QInputDialog.getText(
                self,
                self.tr("Subversion List"),
                self.tr("Enter the repository URL containing the tags or branches"),
                QLineEdit.EchoMode.Normal,
                self.vcs.svnNormalizeURL(reposURL),
            )
            if not ok:
                self.close()
                return
            if not reposPath:
                EricMessageBox.critical(
                    self,
                    self.tr("Subversion List"),
                    self.tr("""The repository URL is empty. Aborting..."""),
                )
                self.close()
                return
            args.append(reposPath)
            self.path = reposPath

        self.process.setWorkingDirectory(dname)

        self.process.start("svn", args)
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
                ).format("svn"),
            )
        else:
            self.inputGroup.setEnabled(True)
            self.inputGroup.show()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed the
        button.
        """
        if (
            self.process is not None
            and self.process.state() != QProcess.ProcessState.NotRunning
        ):
            self.process.terminate()
            QTimer.singleShot(2000, self.process.kill)
            self.process.waitForFinished(3000)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        self.inputGroup.setEnabled(False)
        self.inputGroup.hide()

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

    def __generateItem(self, revision, author, date, name):
        """
        Private method to generate a tag item in the taglist.

        @param revision revision string
        @type str
        @param author author of the tag
        @type str
        @param date date of the tag
        @type str
        @param name name (path) of the tag
        @type str
        """
        itm = QTreeWidgetItem(self.tagList)
        itm.setData(0, Qt.ItemDataRole.DisplayRole, int(revision))
        itm.setData(1, Qt.ItemDataRole.DisplayRole, author)
        itm.setData(2, Qt.ItemDataRole.DisplayRole, date)
        itm.setData(3, Qt.ItemDataRole.DisplayRole, name)
        itm.setTextAlignment(0, Qt.AlignmentFlag.AlignRight)

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
            match = self.rx_list.fullmatch(s)
            if match is not None:
                rev = "{0:6}".format(match.group(1))
                author = match.group(2)
                date = match.group(3)
                path = match.group(4)
                if path == ".":
                    continue
                self.__generateItem(rev, author, date, path)
                if not self.vcs.otherData["standardLayout"]:
                    path = self.path + "/" + path
                if self.tagsList is not None:
                    self.tagsList.append(path)
                if self.allTagsList is not None:
                    self.allTagsList.append(path)

    def __readStderr(self):
        """
        Private slot to handle the readyReadStderr signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        if self.process is not None:
            self.errorGroup.show()
            s = str(
                self.process.readAllStandardError(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
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
        Private slot to send the input to the subversion process.
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
