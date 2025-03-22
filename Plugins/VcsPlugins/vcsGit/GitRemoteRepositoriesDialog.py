# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show available remote repositories.
"""

import os

from PyQt6.QtCore import QProcess, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QHeaderView,
    QLineEdit,
    QTreeWidgetItem,
    QWidget,
)

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.Globals import strToQByteArray

from .Ui_GitRemoteRepositoriesDialog import Ui_GitRemoteRepositoriesDialog


class GitRemoteRepositoriesDialog(QWidget, Ui_GitRemoteRepositoriesDialog):
    """
    Class implementing a dialog to show available remote repositories.
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

        self.vcs = vcs
        self.process = QProcess()
        self.process.finished.connect(self.__procFinished)
        self.process.readyReadStandardOutput.connect(self.__readStdout)
        self.process.readyReadStandardError.connect(self.__readStderr)

        self.refreshButton = self.buttonBox.addButton(
            self.tr("Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(
            self.tr("Press to refresh the repositories display")
        )
        self.refreshButton.setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.__lastColumn = self.repolist.columnCount()

        self.repolist.headerItem().setText(self.__lastColumn, "")
        self.repolist.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.__ioEncoding = Preferences.getSystem("IOEncoding")

    def __resort(self):
        """
        Private method to resort the list.
        """
        self.repolist.sortItems(
            self.repolist.sortColumn(), self.repolist.header().sortIndicatorOrder()
        )

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.repolist.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.repolist.header().setStretchLastSection(True)

    def __generateItem(self, name, url, oper):
        """
        Private method to generate a status item in the status list.

        @param name name of the remote repository
        @type str
        @param url URL of the remote repository
        @type str
        @param oper operation the remote repository may be used for
        @type str
        """
        foundItems = self.repolist.findItems(name, Qt.MatchFlag.MatchExactly, 0)
        if foundItems:
            # modify the operations column only
            foundItems[0].setText(2, "{0} + {1}".format(foundItems[0].text(2), oper))
        else:
            QTreeWidgetItem(self.repolist, [name, url, oper])

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

    def start(self, projectDir):
        """
        Public slot to start the git remote command.

        @param projectDir name of the project directory
        @type str
        """
        self.repolist.clear()

        self.errorGroup.hide()
        self.intercept = False
        self.projectDir = projectDir

        self.__ioEncoding = Preferences.getSystem("IOEncoding")

        self.removeButton.setEnabled(False)
        self.renameButton.setEnabled(False)
        self.pruneButton.setEnabled(False)
        self.showInfoButton.setEnabled(False)

        args = self.vcs.initCommand("remote")
        args.append("--verbose")

        # find the root of the repo
        repodir = self.vcs.findRepoRoot(self.projectDir)
        if not repodir:
            return

        self.process.kill()
        self.process.setWorkingDirectory(repodir)

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
            self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(
                False
            )
            self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(
                True
            )
            self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(
                True
            )

            self.inputGroup.setEnabled(True)
            self.inputGroup.show()
            self.refreshButton.setEnabled(False)

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
        self.refreshButton.setEnabled(True)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        self.__resort()
        self.__resizeColumns()

        self.__updateButtons()

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
        elif button == self.refreshButton:
            self.on_refreshButton_clicked()

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

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process, formats it and inserts it into
        the contents pane.
        """
        if self.process is not None:
            self.process.setReadChannel(QProcess.ProcessChannel.StandardOutput)

            while self.process.canReadLine():
                line = str(
                    self.process.readLine(), self.__ioEncoding, "replace"
                ).strip()

                name, line = line.split(None, 1)
                url, oper = line.rsplit(None, 1)
                oper = oper[1:-1]  # it is enclosed in ()
                self.__generateItem(name, url, oper)

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        if self.process is not None:
            s = str(self.process.readAllStandardError(), self.__ioEncoding, "replace")
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

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the status display.
        """
        self.start(self.projectDir)

    def __updateButtons(self):
        """
        Private method to update the buttons status.
        """
        enable = len(self.repolist.selectedItems()) == 1

        self.removeButton.setEnabled(enable)
        self.pruneButton.setEnabled(enable)
        self.showInfoButton.setEnabled(enable)
        self.renameButton.setEnabled(enable)
        self.changeUrlButton.setEnabled(enable)
        self.credentialsButton.setEnabled(enable)

    @pyqtSlot()
    def on_repolist_itemSelectionChanged(self):
        """
        Private slot to act upon changes of selected items.
        """
        self.__updateButtons()

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add a remote repository.
        """
        self.vcs.gitAddRemote(self.projectDir)
        self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_removeButton_clicked(self):
        """
        Private slot to remove a remote repository.
        """
        remoteName = self.repolist.selectedItems()[0].text(0)
        self.vcs.gitRemoveRemote(self.projectDir, remoteName)
        self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_showInfoButton_clicked(self):
        """
        Private slot to show information about a remote repository.
        """
        remoteName = self.repolist.selectedItems()[0].text(0)
        self.vcs.gitShowRemote(self.projectDir, remoteName)

    @pyqtSlot()
    def on_pruneButton_clicked(self):
        """
        Private slot to prune all stale remote-tracking branches.
        """
        remoteName = self.repolist.selectedItems()[0].text(0)
        self.vcs.gitPruneRemote(self.projectDir, remoteName)

    @pyqtSlot()
    def on_renameButton_clicked(self):
        """
        Private slot to rename a remote repository.
        """
        remoteName = self.repolist.selectedItems()[0].text(0)
        self.vcs.gitRenameRemote(self.projectDir, remoteName)
        self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_changeUrlButton_clicked(self):
        """
        Private slot to change the URL of a remote repository.
        """
        repositoryItem = self.repolist.selectedItems()[0]
        remoteName = repositoryItem.text(0)
        remoteUrl = repositoryItem.text(1)
        self.vcs.gitChangeRemoteUrl(self.projectDir, remoteName, remoteUrl)
        self.on_refreshButton_clicked()

    @pyqtSlot()
    def on_credentialsButton_clicked(self):
        """
        Private slot to change the credentials of a remote repository.
        """
        repositoryItem = self.repolist.selectedItems()[0]
        remoteName = repositoryItem.text(0)
        remoteUrl = repositoryItem.text(1)
        self.vcs.gitChangeRemoteCredentials(self.projectDir, remoteName, remoteUrl)
        self.on_refreshButton_clicked()
