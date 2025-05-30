# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of the svn status command
process.
"""

import os
import re

from PyQt6.QtCore import QProcess, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QDialogButtonBox,
    QHeaderView,
    QLineEdit,
    QMenu,
    QTreeWidgetItem,
    QWidget,
)

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Globals import strToQByteArray

from .Ui_SvnStatusDialog import Ui_SvnStatusDialog


class SvnStatusDialog(QWidget, Ui_SvnStatusDialog):
    """
    Class implementing a dialog to show the output of the svn status command
    process.
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

        self.__toBeCommittedColumn = 0
        self.__changelistColumn = 1
        self.__statusColumn = 2
        self.__propStatusColumn = 3
        self.__lockedColumn = 4
        self.__historyColumn = 5
        self.__switchedColumn = 6
        self.__lockinfoColumn = 7
        self.__upToDateColumn = 8
        self.__pathColumn = 12
        self.__lastColumn = self.statusList.columnCount()

        self.refreshButton = self.buttonBox.addButton(
            self.tr("Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.refreshButton.setToolTip(self.tr("Press to refresh the status display"))
        self.refreshButton.setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.diff = None
        self.vcs = vcs
        self.vcs.committed.connect(self.__committed)

        self.process = QProcess()
        self.process.finished.connect(self.__procFinished)
        self.process.readyReadStandardOutput.connect(self.__readStdout)
        self.process.readyReadStandardError.connect(self.__readStderr)

        self.statusList.headerItem().setText(self.__lastColumn, "")
        self.statusList.header().setSortIndicator(
            self.__pathColumn, Qt.SortOrder.AscendingOrder
        )
        if self.vcs.version < (1, 5, 0):
            self.statusList.header().hideSection(self.__changelistColumn)

        self.menuactions = []
        self.menu = QMenu()
        self.menuactions.append(
            self.menu.addAction(
                self.tr("Commit changes to repository..."), self.__commit
            )
        )
        self.menuactions.append(
            self.menu.addAction(
                self.tr("Select all for commit"), self.__commitSelectAll
            )
        )
        self.menuactions.append(
            self.menu.addAction(
                self.tr("Deselect all from commit"), self.__commitDeselectAll
            )
        )
        self.menu.addSeparator()
        self.menuactions.append(
            self.menu.addAction(self.tr("Add to repository"), self.__add)
        )
        self.menuactions.append(
            self.menu.addAction(self.tr("Show differences"), self.__diff)
        )
        self.menuactions.append(
            self.menu.addAction(
                self.tr("Show differences side-by-side"), self.__sbsDiff
            )
        )
        self.menuactions.append(
            self.menu.addAction(self.tr("Revert changes"), self.__revert)
        )
        self.menuactions.append(
            self.menu.addAction(self.tr("Restore missing"), self.__restoreMissing)
        )
        if self.vcs.version >= (1, 5, 0):
            self.menu.addSeparator()
            self.menuactions.append(
                self.menu.addAction(
                    self.tr("Add to Changelist"), self.__addToChangelist
                )
            )
            self.menuactions.append(
                self.menu.addAction(
                    self.tr("Remove from Changelist"), self.__removeFromChangelist
                )
            )
        if self.vcs.version >= (1, 2, 0):
            self.menu.addSeparator()
            self.menuactions.append(self.menu.addAction(self.tr("Lock"), self.__lock))
            self.menuactions.append(
                self.menu.addAction(self.tr("Unlock"), self.__unlock)
            )
            self.menuactions.append(
                self.menu.addAction(self.tr("Break lock"), self.__breakLock)
            )
            self.menuactions.append(
                self.menu.addAction(self.tr("Steal lock"), self.__stealLock)
            )
        self.menu.addSeparator()
        self.menuactions.append(
            self.menu.addAction(self.tr("Adjust column sizes"), self.__resizeColumns)
        )
        for act in self.menuactions:
            act.setEnabled(False)

        self.statusList.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.statusList.customContextMenuRequested.connect(self.__showContextMenu)

        self.modifiedIndicators = [
            self.tr("added"),
            self.tr("deleted"),
            self.tr("modified"),
        ]

        self.missingIndicators = [
            self.tr("missing"),
        ]

        self.unversionedIndicators = [
            self.tr("unversioned"),
        ]

        self.lockedIndicators = [
            self.tr("locked"),
        ]

        self.stealBreakLockIndicators = [
            self.tr("other lock"),
            self.tr("stolen lock"),
            self.tr("broken lock"),
        ]

        self.unlockedIndicators = [
            self.tr("not locked"),
        ]

        self.status = {
            " ": self.tr("normal"),
            "A": self.tr("added"),
            "C": self.tr("conflict"),
            "D": self.tr("deleted"),
            "I": self.tr("ignored"),
            "M": self.tr("modified"),
            "R": self.tr("replaced"),
            "X": self.tr("external"),
            "?": self.tr("unversioned"),
            "!": self.tr("missing"),
            "~": self.tr("type error"),
        }
        self.propStatus = {
            " ": self.tr("normal"),
            "M": self.tr("modified"),
            "C": self.tr("conflict"),
        }
        self.locked = {
            " ": self.tr("no"),
            "L": self.tr("yes"),
        }
        self.history = {
            " ": self.tr("no"),
            "+": self.tr("yes"),
        }
        self.switched = {
            " ": self.tr("no"),
            "S": self.tr("yes"),
            "X": self.tr("external"),
        }
        self.lockinfo = {
            " ": self.tr("not locked"),
            "K": self.tr("locked"),
            "O": self.tr("other lock"),
            "T": self.tr("stolen lock"),
            "B": self.tr("broken lock"),
        }
        self.uptodate = {
            " ": self.tr("yes"),
            "*": self.tr("no"),
        }

        self.rx_status = re.compile(
            "(.{8,9})\\s+([0-9-]+)\\s+([0-9?]+)\\s+(\\S+)\\s+(.+)\\s*"
        )
        # flags (8 or 9 anything), revision, changed rev, author, path
        self.rx_status2 = re.compile("(.{8,9})\\s+(.+)\\s*")
        # flags (8 or 9 anything), path
        self.rx_changelist = re.compile("--- \\S+ .([\\w\\s]+).:\\s+")
        # three dashes, Changelist (translated), quote,
        # changelist name, quote, :

        self.__nonverbose = True

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.statusList.sortItems(
            self.statusList.sortColumn(), self.statusList.header().sortIndicatorOrder()
        )

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.statusList.header().resizeSections(QHeaderView.ResizeMode.ResizeToContents)
        self.statusList.header().setStretchLastSection(True)

    def __generateItem(
        self,
        status,
        propStatus,
        locked,
        history,
        switched,
        lockinfo,
        uptodate,
        revision,
        change,
        author,
        path,
    ):
        """
        Private method to generate a status item in the status list.

        @param status status indicator
        @type str
        @param propStatus property status indicator
        @type str
        @param locked locked indicator
        @type str
        @param history history indicator
        @type str
        @param switched switched indicator
        @type str
        @param lockinfo lock indicator
        @type str
        @param uptodate up to date indicator
        @type str
        @param revision revision string
        @type str
        @param change revision of last change
        @type str
        @param author author of the last change
        @type str
        @param path path of the file or directory
        @type str
        """
        if (
            self.__nonverbose
            and status == " "
            and propStatus == " "
            and locked == " "
            and history == " "
            and switched == " "
            and lockinfo == " "
            and uptodate == " "
            and self.currentChangelist == ""
        ):
            return

        if revision == "":
            rev = ""
        else:
            try:
                rev = int(revision)
            except ValueError:
                rev = revision
        if change == "":
            chg = ""
        else:
            try:
                chg = int(change)
            except ValueError:
                chg = change
        statusText = self.status[status]

        itm = QTreeWidgetItem(self.statusList)
        itm.setData(0, Qt.ItemDataRole.DisplayRole, "")
        itm.setData(1, Qt.ItemDataRole.DisplayRole, self.currentChangelist)
        itm.setData(2, Qt.ItemDataRole.DisplayRole, statusText)
        itm.setData(3, Qt.ItemDataRole.DisplayRole, self.propStatus[propStatus])
        itm.setData(4, Qt.ItemDataRole.DisplayRole, self.locked[locked])
        itm.setData(5, Qt.ItemDataRole.DisplayRole, self.history[history])
        itm.setData(6, Qt.ItemDataRole.DisplayRole, self.switched[switched])
        itm.setData(7, Qt.ItemDataRole.DisplayRole, self.lockinfo[lockinfo])
        itm.setData(8, Qt.ItemDataRole.DisplayRole, self.uptodate[uptodate])
        itm.setData(9, Qt.ItemDataRole.DisplayRole, rev)
        itm.setData(10, Qt.ItemDataRole.DisplayRole, chg)
        itm.setData(11, Qt.ItemDataRole.DisplayRole, author)
        itm.setData(12, Qt.ItemDataRole.DisplayRole, path)

        itm.setTextAlignment(1, Qt.AlignmentFlag.AlignLeft)
        itm.setTextAlignment(2, Qt.AlignmentFlag.AlignHCenter)
        itm.setTextAlignment(3, Qt.AlignmentFlag.AlignHCenter)
        itm.setTextAlignment(4, Qt.AlignmentFlag.AlignHCenter)
        itm.setTextAlignment(5, Qt.AlignmentFlag.AlignHCenter)
        itm.setTextAlignment(6, Qt.AlignmentFlag.AlignHCenter)
        itm.setTextAlignment(7, Qt.AlignmentFlag.AlignHCenter)
        itm.setTextAlignment(8, Qt.AlignmentFlag.AlignHCenter)
        itm.setTextAlignment(9, Qt.AlignmentFlag.AlignRight)
        itm.setTextAlignment(10, Qt.AlignmentFlag.AlignRight)
        itm.setTextAlignment(11, Qt.AlignmentFlag.AlignLeft)
        itm.setTextAlignment(12, Qt.AlignmentFlag.AlignLeft)

        if status in "ADM" or propStatus in "M":
            itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            itm.setCheckState(self.__toBeCommittedColumn, Qt.CheckState.Checked)
        else:
            itm.setFlags(itm.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)

        self.hidePropertyStatusColumn = (
            self.hidePropertyStatusColumn and propStatus == " "
        )
        self.hideLockColumns = (
            self.hideLockColumns and locked == " " and lockinfo == " "
        )
        self.hideUpToDateColumn = self.hideUpToDateColumn and uptodate == " "
        self.hideHistoryColumn = self.hideHistoryColumn and history == " "
        self.hideSwitchedColumn = self.hideSwitchedColumn and switched == " "

        if statusText not in self.__statusFilters:
            self.__statusFilters.append(statusText)

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

    def start(self, fn):
        """
        Public slot to start the svn status command.

        @param fn filename(s)/directoryname(s) to show the status of
        @type str or list of str
        """
        self.errorGroup.hide()
        self.intercept = False
        self.args = fn

        for act in self.menuactions:
            act.setEnabled(False)

        self.addButton.setEnabled(False)
        self.commitButton.setEnabled(False)
        self.diffButton.setEnabled(False)
        self.sbsDiffButton.setEnabled(False)
        self.revertButton.setEnabled(False)
        self.restoreButton.setEnabled(False)

        self.statusFilterCombo.clear()
        self.__statusFilters = []
        self.statusList.clear()

        self.currentChangelist = ""
        self.changelistFound = False

        self.hidePropertyStatusColumn = True
        self.hideLockColumns = True
        self.hideUpToDateColumn = True
        self.hideHistoryColumn = True
        self.hideSwitchedColumn = True

        self.process.kill()

        args = []
        args.append("status")
        self.vcs.addArguments(args, self.vcs.options["global"])
        self.vcs.addArguments(args, self.vcs.options["status"])
        if (
            "--verbose" not in self.vcs.options["global"]
            and "--verbose" not in self.vcs.options["status"]
        ):
            args.append("--verbose")
            self.__nonverbose = True
        else:
            self.__nonverbose = False
        if (
            "--show-updates" in self.vcs.options["status"]
            or "-u" in self.vcs.options["status"]
        ):
            self.activateWindow()
            self.raise_()
        if isinstance(fn, list):
            self.dname, fnames = self.vcs.splitPathList(fn)
            self.vcs.addArguments(args, fnames)
        else:
            self.dname, fname = self.vcs.splitPath(fn)
            args.append(fname)

        self.process.setWorkingDirectory(self.dname)

        self.setWindowTitle(self.tr("Subversion Status"))

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

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        self.inputGroup.setEnabled(False)
        self.inputGroup.hide()
        self.refreshButton.setEnabled(True)

        self.__statusFilters.sort()
        self.__statusFilters.insert(0, "<{0}>".format(self.tr("all")))
        self.statusFilterCombo.addItems(self.__statusFilters)

        for act in self.menuactions:
            act.setEnabled(True)

        self.__resort()
        self.__resizeColumns()

        self.statusList.setColumnHidden(
            self.__changelistColumn, not self.changelistFound
        )
        self.statusList.setColumnHidden(
            self.__propStatusColumn, self.hidePropertyStatusColumn
        )
        self.statusList.setColumnHidden(self.__lockedColumn, self.hideLockColumns)
        self.statusList.setColumnHidden(self.__lockinfoColumn, self.hideLockColumns)
        self.statusList.setColumnHidden(self.__upToDateColumn, self.hideUpToDateColumn)
        self.statusList.setColumnHidden(self.__historyColumn, self.hideHistoryColumn)
        self.statusList.setColumnHidden(self.__switchedColumn, self.hideSwitchedColumn)

        self.__updateButtons()
        self.__updateCommitButton()

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
                s = str(
                    self.process.readLine(),
                    Preferences.getSystem("IOEncoding"),
                    "replace",
                )
                match = (
                    self.rx_status.fullmatch(s)
                    or self.rx_status2.fullmatch(s)
                    or self.rx_changelist.fullmatch(s)
                )
                if match.re is self.rx_status:
                    flags = match.group(1)
                    rev = match.group(2)
                    change = match.group(3)
                    author = match.group(4)
                    path = match.group(5).strip()

                    self.__generateItem(
                        flags[0],
                        flags[1],
                        flags[2],
                        flags[3],
                        flags[4],
                        flags[5],
                        flags[-1],
                        rev,
                        change,
                        author,
                        path,
                    )
                elif match.re is self.rx_status2:
                    flags = match.group(1)
                    path = match.group(2).strip()

                    if flags[-1] in self.uptodate:
                        self.__generateItem(
                            flags[0],
                            flags[1],
                            flags[2],
                            flags[3],
                            flags[4],
                            flags[5],
                            flags[-1],
                            "",
                            "",
                            "",
                            path,
                        )
                elif match.re is self.rx_changelist:
                    self.currentChangelist = match.group(1)
                    self.changelistFound = True

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal.

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

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot to refresh the status display.
        """
        self.start(self.args)

    def __updateButtons(self):
        """
        Private method to update the VCS buttons status.
        """
        modified = len(self.__getModifiedItems())
        unversioned = len(self.__getUnversionedItems())
        missing = len(self.__getMissingItems())

        self.addButton.setEnabled(unversioned)
        self.diffButton.setEnabled(modified)
        self.sbsDiffButton.setEnabled(modified == 1)
        self.revertButton.setEnabled(modified)
        self.restoreButton.setEnabled(missing)

    def __updateCommitButton(self):
        """
        Private method to update the Commit button status.
        """
        commitable = len(self.__getCommitableItems())
        self.commitButton.setEnabled(commitable)

    @pyqtSlot(int)
    def on_statusFilterCombo_activated(self, index):
        """
        Private slot to react to the selection of a status filter.

        @param index index of the selected entry
        @type int
        """
        txt = self.statusFilterCombo.itemText(index)
        if txt == "<{0}>".format(self.tr("all")):
            for topIndex in range(self.statusList.topLevelItemCount()):
                topItem = self.statusList.topLevelItem(topIndex)
                topItem.setHidden(False)
        else:
            for topIndex in range(self.statusList.topLevelItemCount()):
                topItem = self.statusList.topLevelItem(topIndex)
                topItem.setHidden(topItem.text(self.__statusColumn) != txt)

    @pyqtSlot(QTreeWidgetItem, int)
    def on_statusList_itemChanged(self, _item, column):
        """
        Private slot to act upon item changes.

        @param _item reference to the changed item (unused)
        @type QTreeWidgetItem
        @param column index of column that changed
        @type int
        """
        if column == self.__toBeCommittedColumn:
            self.__updateCommitButton()

    @pyqtSlot()
    def on_statusList_itemSelectionChanged(self):
        """
        Private slot to act upon changes of selected items.
        """
        self.__updateButtons()

    @pyqtSlot()
    def on_commitButton_clicked(self):
        """
        Private slot to handle the press of the Commit button.
        """
        self.__commit()

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to handle the press of the Add button.
        """
        self.__add()

    @pyqtSlot()
    def on_diffButton_clicked(self):
        """
        Private slot to handle the press of the Differences button.
        """
        self.__diff()

    @pyqtSlot()
    def on_sbsDiffButton_clicked(self):
        """
        Private slot to handle the press of the Side-by-Side Diff button.
        """
        self.__sbsDiff()

    @pyqtSlot()
    def on_revertButton_clicked(self):
        """
        Private slot to handle the press of the Revert button.
        """
        self.__revert()

    @pyqtSlot()
    def on_restoreButton_clicked(self):
        """
        Private slot to handle the press of the Restore button.
        """
        self.__restoreMissing()

    ###########################################################################
    ## Context menu handling methods
    ###########################################################################

    def __showContextMenu(self, coord):
        """
        Private slot to show the context menu of the status list.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        self.menu.popup(self.statusList.mapToGlobal(coord))

    def __commit(self):
        """
        Private slot to handle the Commit context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getCommitableItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Commit"),
                self.tr("""There are no entries selected to be committed."""),
            )
            return

        if Preferences.getVCS("AutoSaveFiles"):
            vm = ericApp().getObject("ViewManager")
            for name in names:
                vm.saveEditor(name)
        self.vcs.vcsCommit(names, "")

    def __committed(self):
        """
        Private slot called after the commit has finished.
        """
        if self.isVisible():
            self.on_refreshButton_clicked()
            self.vcs.checkVCSStatus()

    def __commitSelectAll(self):
        """
        Private slot to select all entries for commit.
        """
        self.__commitSelect(True)

    def __commitDeselectAll(self):
        """
        Private slot to deselect all entries from commit.
        """
        self.__commitSelect(False)

    def __add(self):
        """
        Private slot to handle the Add context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getUnversionedItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Add"),
                self.tr("""There are no unversioned entries available/selected."""),
            )
            return

        self.vcs.vcsAdd(names)
        self.on_refreshButton_clicked()

        project = ericApp().getObject("Project")
        for name in names:
            project.getModel().updateVCSStatus(name)
        self.vcs.checkVCSStatus()

    def __revert(self):
        """
        Private slot to handle the Revert context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getModifiedItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Revert"),
                self.tr("""There are no uncommitted changes available/selected."""),
            )
            return

        self.vcs.vcsRevert(names)
        self.raise_()
        self.activateWindow()
        self.on_refreshButton_clicked()

        project = ericApp().getObject("Project")
        for name in names:
            project.getModel().updateVCSStatus(name)
        self.vcs.checkVCSStatus()

    def __restoreMissing(self):
        """
        Private slot to handle the Restore Missing context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getMissingItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Revert"),
                self.tr("""There are no missing entries available/selected."""),
            )
            return

        self.vcs.vcsRevert(names)
        self.on_refreshButton_clicked()
        self.vcs.checkVCSStatus()

    def __diff(self):
        """
        Private slot to handle the Diff context menu entry.
        """
        from .SvnDiffDialog import SvnDiffDialog

        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getModifiedItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Differences"),
                self.tr("""There are no uncommitted changes available/selected."""),
            )
            return

        if self.diff is None:
            self.diff = SvnDiffDialog(self.vcs)
        self.diff.show()
        QApplication.processEvents()
        self.diff.start(names, refreshable=True)

    def __sbsDiff(self):
        """
        Private slot to handle the Side-by-Side Diff context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getModifiedItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Side-by-Side Diff"),
                self.tr("""There are no uncommitted changes available/selected."""),
            )
            return
        elif len(names) > 1:
            EricMessageBox.information(
                self,
                self.tr("Side-by-Side Diff"),
                self.tr(
                    """Only one file with uncommitted changes"""
                    """ must be selected."""
                ),
            )
            return

        self.vcs.vcsSbsDiff(names[0])

    def __lock(self):
        """
        Private slot to handle the Lock context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getLockActionItems(self.unlockedIndicators)
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Lock"),
                self.tr("""There are no unlocked files available/selected."""),
            )
            return

        self.vcs.svnLock(names, parent=self)
        self.on_refreshButton_clicked()

    def __unlock(self):
        """
        Private slot to handle the Unlock context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getLockActionItems(self.lockedIndicators)
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Unlock"),
                self.tr("""There are no locked files available/selected."""),
            )
            return

        self.vcs.svnUnlock(names, parent=self)
        self.on_refreshButton_clicked()

    def __breakLock(self):
        """
        Private slot to handle the Break Lock context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getLockActionItems(self.stealBreakLockIndicators)
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Break Lock"),
                self.tr("""There are no locked files available/selected."""),
            )
            return

        self.vcs.svnUnlock(names, parent=self, breakIt=True)
        self.on_refreshButton_clicked()

    def __stealLock(self):
        """
        Private slot to handle the Break Lock context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getLockActionItems(self.stealBreakLockIndicators)
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Steal Lock"),
                self.tr("""There are no locked files available/selected."""),
            )
            return

        self.vcs.svnLock(names, parent=self, stealIt=True)
        self.on_refreshButton_clicked()

    def __addToChangelist(self):
        """
        Private slot to add entries to a changelist.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getNonChangelistItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Remove from Changelist"),
                self.tr(
                    """There are no files available/selected not """
                    """belonging to a changelist."""
                ),
            )
            return
        self.vcs.svnAddToChangelist(names)
        self.on_refreshButton_clicked()

    def __removeFromChangelist(self):
        """
        Private slot to remove entries from their change lists.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getChangelistItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Remove from Changelist"),
                self.tr(
                    """There are no files available/selected belonging"""
                    """ to a changelist."""
                ),
            )
            return
        self.vcs.svnRemoveFromChangelist(names)
        self.on_refreshButton_clicked()

    def __getCommitableItems(self):
        """
        Private method to retrieve all entries the user wants to commit.

        @return list of all items, the user has checked
        @rtype list of QTreeWidgetItem
        """
        commitableItems = []
        for index in range(self.statusList.topLevelItemCount()):
            itm = self.statusList.topLevelItem(index)
            if itm.checkState(self.__toBeCommittedColumn) == Qt.CheckState.Checked:
                commitableItems.append(itm)
        return commitableItems

    def __getModifiedItems(self):
        """
        Private method to retrieve all entries, that have a modified status.

        @return list of all items with a modified status
        @rtype list of QTreeWidgetItem
        """
        modifiedItems = []
        for itm in self.statusList.selectedItems():
            if (
                itm.text(self.__statusColumn) in self.modifiedIndicators
                or itm.text(self.__propStatusColumn) in self.modifiedIndicators
            ):
                modifiedItems.append(itm)
        return modifiedItems

    def __getUnversionedItems(self):
        """
        Private method to retrieve all entries, that have an unversioned
        status.

        @return list of all items with an unversioned status
        @rtype list of QTreeWidgetItem
        """
        unversionedItems = []
        for itm in self.statusList.selectedItems():
            if itm.text(self.__statusColumn) in self.unversionedIndicators:
                unversionedItems.append(itm)
        return unversionedItems

    def __getMissingItems(self):
        """
        Private method to retrieve all entries, that have a missing status.

        @return list of all items with a missing status
        @rtype list of QTreeWidgetItem
        """
        missingItems = []
        for itm in self.statusList.selectedItems():
            if itm.text(self.__statusColumn) in self.missingIndicators:
                missingItems.append(itm)
        return missingItems

    def __getLockActionItems(self, indicators):
        """
        Private method to retrieve all emtries, that have a locked status.

        @param indicators list of indicators to check against
        @type list of str
        @return list of all items with a locked status
        @rtype list of QTreeWidgetItem
        """
        lockitems = []
        for itm in self.statusList.selectedItems():
            if itm.text(self.__lockinfoColumn) in indicators:
                lockitems.append(itm)
        return lockitems

    def __getChangelistItems(self):
        """
        Private method to retrieve all entries, that are members of
        a changelist.

        @return list of all items belonging to a changelist
        @rtype list of QTreeWidgetItem
        """
        clitems = []
        for itm in self.statusList.selectedItems():
            if itm.text(self.__changelistColumn) != "":
                clitems.append(itm)
        return clitems

    def __getNonChangelistItems(self):
        """
        Private method to retrieve all entries, that are not members of
        a changelist.

        @return list of all items not belonging to a changelist
        @rtype list of QTreeWidgetItem
        """
        clitems = []
        for itm in self.statusList.selectedItems():
            if itm.text(self.__changelistColumn) == "":
                clitems.append(itm)
        return clitems

    def __commitSelect(self, selected):
        """
        Private slot to select or deselect all entries.

        @param selected commit selection state to be set
        @type bool
        """
        for index in range(self.statusList.topLevelItemCount()):
            itm = self.statusList.topLevelItem(index)
            if (
                itm.flags() & Qt.ItemFlag.ItemIsUserCheckable
                == Qt.ItemFlag.ItemIsUserCheckable
            ):
                if selected:
                    itm.setCheckState(self.__toBeCommittedColumn, Qt.CheckState.Checked)
                else:
                    itm.setCheckState(
                        self.__toBeCommittedColumn, Qt.CheckState.Unchecked
                    )
