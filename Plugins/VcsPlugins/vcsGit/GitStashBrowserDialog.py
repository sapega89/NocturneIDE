# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the stashes.
"""

import os

from PyQt6.QtCore import QPoint, QProcess, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QDialogButtonBox,
    QHeaderView,
    QLineEdit,
    QMenu,
    QTreeWidgetItem,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursorProcess
from eric7.EricWidgets import EricMessageBox
from eric7.Globals import strToQByteArray

from .Ui_GitStashBrowserDialog import Ui_GitStashBrowserDialog


class GitStashBrowserDialog(QWidget, Ui_GitStashBrowserDialog):
    """
    Class implementing a dialog to show the stashes.
    """

    NameColumn = 0
    DateColumn = 1
    MessageColumn = 2

    Separator = "@@||@@"

    TotalStatisticsRole = Qt.ItemDataRole.UserRole
    FileStatisticsRole = Qt.ItemDataRole.UserRole + 1

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

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.__position = QPoint()

        self.__fileStatisticsRole = Qt.ItemDataRole.UserRole
        self.__totalStatisticsRole = Qt.ItemDataRole.UserRole + 1

        self.stashList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.refreshButton = self.buttonBox.addButton(
            self.tr("&Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(self.tr("Press to refresh the list of stashes"))
        self.refreshButton.setEnabled(False)

        self.vcs = vcs
        self.__resetUI()

        self.__ioEncoding = Preferences.getSystem("IOEncoding")

        self.__process = EricOverrideCursorProcess()
        self.__process.finished.connect(self.__procFinished)
        self.__process.readyReadStandardOutput.connect(self.__readStdout)
        self.__process.readyReadStandardError.connect(self.__readStderr)

        self.__contextMenu = QMenu()
        self.__differencesAct = self.__contextMenu.addAction(
            self.tr("Show"), self.__showPatch
        )
        self.__contextMenu.addSeparator()
        self.__applyAct = self.__contextMenu.addAction(
            self.tr("Restore && Keep"), self.__apply
        )
        self.__popAct = self.__contextMenu.addAction(
            self.tr("Restore && Delete"), self.__pop
        )
        self.__contextMenu.addSeparator()
        self.__branchAct = self.__contextMenu.addAction(
            self.tr("Create Branch"), self.__branch
        )
        self.__contextMenu.addSeparator()
        self.__dropAct = self.__contextMenu.addAction(self.tr("Delete"), self.__drop)
        self.__clearAct = self.__contextMenu.addAction(
            self.tr("Delete All"), self.__clear
        )

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
        self.stashList.clear()

    def __resizeColumnsStashes(self):
        """
        Private method to resize the shelve list columns.
        """
        self.stashList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.stashList.header().setStretchLastSection(True)

    def __generateStashEntry(self, name, date, message):
        """
        Private method to generate the stash items.

        @param name name of the stash
        @type str
        @param date date the stash was created
        @type str
        @param message stash message
        @type str
        """
        QTreeWidgetItem(self.stashList, [name, date, message])

    def __getStashEntries(self):
        """
        Private method to retrieve the list of stashes.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.inputGroup.setEnabled(True)
        self.inputGroup.show()
        self.refreshButton.setEnabled(False)

        self.buf = []
        self.errors.clear()
        self.intercept = False

        args = self.vcs.initCommand("stash")
        args.append("list")
        args.append("--format=format:%gd{0}%ai{0}%gs%n".format(self.Separator))

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

    def start(self, projectDir):
        """
        Public slot to start the git stash command.

        @param projectDir name of the project directory
        @type str
        """
        self.errorGroup.hide()
        QApplication.processEvents()

        self.__projectDir = projectDir

        # find the root of the repo
        self.repodir = self.vcs.findRepoRoot(self.__projectDir)
        if not self.repodir:
            return

        self.activateWindow()
        self.raise_()

        self.stashList.clear()
        self.__started = True
        self.__getStashEntries()

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
        Private method to process the buffered output of the git stash command.
        """
        for line in self.buf:
            name, date, message = line.split(self.Separator)
            date = date.strip().rsplit(":", 1)[0]
            self.__generateStashEntry(name, date, message.strip())

        self.__resizeColumnsStashes()

        if self.__started:
            self.stashList.setCurrentItem(self.stashList.topLevelItem(0))
            self.__started = False

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal.

        It reads the output of the process and inserts it into a buffer.
        """
        self.__process.setReadChannel(QProcess.ProcessChannel.StandardOutput)

        while self.__process.canReadLine():
            line = str(self.__process.readLine(), self.__ioEncoding, "replace").strip()
            if line:
                self.buf.append(line)

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

        It reads the error output of the process and inserts it into the
        error pane.
        """
        if self.__process is not None:
            s = str(self.__process.readAllStandardError(), self.__ioEncoding, "replace")
            self.errorGroup.show()
            self.errors.insertPlainText(s)
            self.errors.ensureCursorVisible()

    @pyqtSlot(QAbstractButton)
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

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_stashList_currentItemChanged(self, current, _previous):
        """
        Private slot called, when the current item of the stash list changes.

        @param current reference to the new current item
        @type QTreeWidgetItem
        @param _previous reference to the old current item (unused)
        @type QTreeWidgetItem
        """
        self.statisticsList.clear()
        self.filesLabel.setText("")
        self.insertionsLabel.setText("")
        self.deletionsLabel.setText("")

        if current:
            if current.data(0, self.TotalStatisticsRole) is None:
                args = self.vcs.initCommand("stash")
                args.append("show")
                args.append("--numstat")
                args.append(current.text(self.NameColumn))

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
                    totals = {"files": 0, "additions": 0, "deletions": 0}
                    fileData = []
                    for line in output.splitlines():
                        additions, deletions, name = line.strip().split(None, 2)
                        totals["files"] += 1
                        if additions != "-":
                            totals["additions"] += int(additions)
                        if deletions != "-":
                            totals["deletions"] += int(deletions)
                        fileData.append(
                            {
                                "file": name,
                                "total": (
                                    "-"
                                    if additions == "-"
                                    else str(int(additions) + int(deletions))
                                ),
                                "added": additions,
                                "deleted": deletions,
                            }
                        )
                    current.setData(0, self.TotalStatisticsRole, totals)
                    current.setData(0, self.FileStatisticsRole, fileData)
                else:
                    return

            for dataDict in current.data(0, self.FileStatisticsRole):
                QTreeWidgetItem(
                    self.statisticsList,
                    [
                        dataDict["file"],
                        dataDict["total"],
                        dataDict["added"],
                        dataDict["deleted"],
                    ],
                )
            self.statisticsList.header().resizeSections(
                QHeaderView.ResizeMode.ResizeToContents
            )
            self.statisticsList.header().setStretchLastSection(True)

            totals = current.data(0, self.TotalStatisticsRole)
            self.filesLabel.setText(
                self.tr("%n file(s) changed", None, totals["files"])
            )
            self.insertionsLabel.setText(
                self.tr("%n line(s) inserted", None, int(totals["additions"]))
            )
            self.deletionsLabel.setText(
                self.tr("%n line(s) deleted", None, int(totals["deletions"]))
            )

    @pyqtSlot(QPoint)
    def on_stashList_customContextMenuRequested(self, pos):
        """
        Private slot to show the context menu of the stash list.

        @param pos position of the mouse pointer
        @type QPoint
        """
        enable = len(self.stashList.selectedItems()) == 1
        self.__differencesAct.setEnabled(enable)
        self.__applyAct.setEnabled(enable)
        self.__popAct.setEnabled(enable)
        self.__branchAct.setEnabled(enable)
        self.__dropAct.setEnabled(enable)
        self.__clearAct.setEnabled(self.stashList.topLevelItemCount() > 0)

        self.__contextMenu.popup(self.mapToGlobal(pos))

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the list of shelves.
        """
        self.start(self.__projectDir)

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

    @pyqtSlot()
    def on_input_returnPressed(self):
        """
        Private slot to handle the press of the return key in the input field.
        """
        self.intercept = True
        self.on_sendButton_clicked()

    @pyqtSlot(bool)
    def on_passwordCheckBox_toggled(self, checked):
        """
        Private slot to handle the password checkbox toggled.

        @param checked flag indicating the status of the check box
        @type bool
        """
        if checked:
            self.input.setEchoMode(QLineEdit.EchoMode.Password)
        else:
            self.input.setEchoMode(QLineEdit.EchoMode.Normal)

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

    def __showPatch(self):
        """
        Private slot to show the contents of the selected stash.
        """
        stashName = self.stashList.selectedItems()[0].text(self.NameColumn)
        self.vcs.gitStashShowPatch(self.__projectDir, stashName)

    def __apply(self):
        """
        Private slot to apply the selected stash but keep it.
        """
        stashName = self.stashList.selectedItems()[0].text(self.NameColumn)
        self.vcs.gitStashApply(self.__projectDir, stashName)

    def __pop(self):
        """
        Private slot to apply the selected stash and delete it.
        """
        stashName = self.stashList.selectedItems()[0].text(self.NameColumn)
        self.vcs.gitStashPop(self.__projectDir, stashName)
        self.on_refreshButton_clicked()

    def __branch(self):
        """
        Private slot to create a branch from the selected stash.
        """
        stashName = self.stashList.selectedItems()[0].text(self.NameColumn)
        self.vcs.gitStashBranch(self.__projectDir, stashName)
        self.on_refreshButton_clicked()

    def __drop(self):
        """
        Private slot to delete the selected stash.
        """
        stashName = self.stashList.selectedItems()[0].text(self.NameColumn)
        res = self.vcs.gitStashDrop(self.__projectDir, stashName)
        if res:
            self.on_refreshButton_clicked()

    def __clear(self):
        """
        Private slot to delete all stashes.
        """
        res = self.vcs.gitStashClear(self.__projectDir)
        if res:
            self.on_refreshButton_clicked()
