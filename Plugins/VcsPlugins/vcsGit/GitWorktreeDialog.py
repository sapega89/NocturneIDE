# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to offer the worktree management functionality.
"""

import os

from PyQt6.QtCore import QDateTime, QProcess, QSize, Qt, QTime, QTimer, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractButton,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMenu,
    QTreeWidgetItem,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox, EricPathPickerDialog

from .GitDialog import GitDialog
from .Ui_GitWorktreeDialog import Ui_GitWorktreeDialog


class GitWorktreeDialog(QWidget, Ui_GitWorktreeDialog):
    """
    Class implementing a dialog to offer the worktree management functionality.
    """

    StatusRole = Qt.ItemDataRole.UserRole

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Git
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__nameColumn = 0
        self.__pathColumn = 1
        self.__commitColumn = 2
        self.__branchColumn = 3

        self.worktreeList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.__refreshButton = self.buttonBox.addButton(
            self.tr("Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__refreshButton.setToolTip(self.tr("Press to refresh the status display"))
        self.__refreshButton.setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setDefault(True)

        self.__vcs = vcs
        self.__process = QProcess()
        self.__process.finished.connect(self.__procFinished)
        self.__process.readyReadStandardOutput.connect(self.__readStdout)
        self.__process.readyReadStandardError.connect(self.__readStderr)

        self.__initActionsMenu()

    def __initActionsMenu(self):
        """
        Private method to initialize the actions menu.
        """
        self.__actionsMenu = QMenu()
        self.__actionsMenu.setTearOffEnabled(True)
        self.__actionsMenu.setToolTipsVisible(True)
        self.__actionsMenu.aboutToShow.connect(self.__showActionsMenu)

        self.__addAct = self.__actionsMenu.addAction(
            self.tr("Add..."), self.__worktreeAdd
        )
        self.__addAct.setToolTip(self.tr("Add a new linked worktree"))
        self.__actionsMenu.addSeparator()
        self.__lockAct = self.__actionsMenu.addAction(
            self.tr("Lock..."), self.__worktreeLock
        )
        self.__lockAct.setToolTip(self.tr("Lock the selected worktree"))
        self.__unlockAct = self.__actionsMenu.addAction(
            self.tr("Unlock"), self.__worktreeUnlock
        )
        self.__unlockAct.setToolTip(self.tr("Unlock the selected worktree"))
        self.__actionsMenu.addSeparator()
        self.__moveAct = self.__actionsMenu.addAction(
            self.tr("Move..."), self.__worktreeMove
        )
        self.__moveAct.setToolTip(
            self.tr("Move the selected worktree to a new location")
        )
        self.__actionsMenu.addSeparator()
        self.__removeAct = self.__actionsMenu.addAction(
            self.tr("Remove"), self.__worktreeRemove
        )
        self.__removeAct.setToolTip(self.tr("Remove the selected worktree"))
        self.__removeForcedAct = self.__actionsMenu.addAction(
            self.tr("Forced Remove"), self.__worktreeRemoveForced
        )
        self.__removeForcedAct.setToolTip(
            self.tr("Remove the selected worktree forcefully")
        )
        self.__actionsMenu.addSeparator()
        self.__pruneAct = self.__actionsMenu.addAction(
            self.tr("Prune..."), self.__worktreePrune
        )
        self.__pruneAct.setToolTip(self.tr("Prune worktree information"))
        self.__actionsMenu.addSeparator()
        self.__repairAct = self.__actionsMenu.addAction(
            self.tr("Repair"), self.__worktreeRepair
        )
        self.__repairAct.setToolTip(self.tr("Repair worktree administrative files"))
        self.__repairMultipleAct = self.__actionsMenu.addAction(
            self.tr("Repair Multiple"), self.__worktreeRepairMultiple
        )
        self.__repairMultipleAct.setToolTip(
            self.tr("Repair administrative files of multiple worktrees")
        )

        self.actionsButton.setIcon(EricPixmapCache.getIcon("actionsToolButton"))
        self.actionsButton.setMenu(self.__actionsMenu)

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

        self.__vcs.getPlugin().setPreferences(
            "WorktreeDialogGeometry", self.saveGeometry()
        )

        e.accept()

    def show(self):
        """
        Public slot to show the dialog.
        """
        super().show()

        geom = self.__vcs.getPlugin().getPreferences("WorktreeDialogGeometry")
        if geom.isEmpty():
            s = QSize(900, 600)
            self.resize(s)
        else:
            self.restoreGeometry(geom)

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.worktreeList.sortItems(
            self.worktreeList.sortColumn(),
            self.worktreeList.header().sortIndicatorOrder(),
        )

    def __resizeColumns(self):
        """
        Private method to resize the list columns.
        """
        self.worktreeList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.worktreeList.header().setStretchLastSection(True)

    def __generateItem(self, dataLines):
        """
        Private method to generate a worktree entry with the given data.

        @param dataLines lines extracted from the git worktree list output
            with porcelain format
        @type list of str
        """
        checkoutPath = worktreeName = commit = branch = status = ""
        iconName = tooltip = ""
        for line in dataLines:
            if " " in line:
                option, value = line.split(None, 1)
            else:
                option, value = line, ""

            if option == "worktree":
                checkoutPath = value
                worktreeName = os.path.basename(value)
            elif option == "HEAD":
                commit = value[: self.__commitIdLength]
            elif option == "branch":
                branch = value.rsplit("/", 1)[-1]
            elif option == "bare":
                branch = self.tr("(bare)")
            elif option == "detached":
                branch = self.tr("(detached HEAD)")
            elif option == "prunable":
                iconName = "trash"
                tooltip = value
                status = option
            elif option == "locked":
                iconName = "locked"
                tooltip = value
                status = option

        itm = QTreeWidgetItem(
            self.worktreeList, [worktreeName, checkoutPath, commit, branch]
        )
        if iconName:
            itm.setIcon(0, EricPixmapCache.getIcon(iconName))
            if tooltip:
                itm.setToolTip(0, tooltip)

        if self.worktreeList.topLevelItemCount() == 1:
            # the first item is the main worktree
            status = "main"
            font = itm.font(0)
            font.setBold(True)
            if checkoutPath == self.__projectDir:
                # it is the current project as well
                status = "main+current"
                font.setItalic(True)
            for col in range(self.worktreeList.columnCount()):
                itm.setFont(col, font)
        elif checkoutPath == self.__projectDir:
            # it is the current project
            if not status:
                status = "current"
            elif status == "locked":
                status = "locked+current"
            font = itm.font(0)
            font.setItalic(True)
            for col in range(self.worktreeList.columnCount()):
                itm.setFont(col, font)
        itm.setData(0, GitWorktreeDialog.StatusRole, status)

    def start(self, projectDir):
        """
        Public slot to start the git worktree list command.

        @param projectDir name of the project directory
        @type str
        """
        self.errorGroup.hide()
        self.worktreeList.clear()

        self.__ioEncoding = Preferences.getSystem("IOEncoding")

        args = self.__vcs.initCommand("worktree")
        args += ["list", "--porcelain"]
        if self.expireCheckBox.isChecked():
            args += [
                "--expire",
                self.expireDateTimeEdit.dateTime().toString(Qt.DateFormat.ISODate),
            ]

        self.__projectDir = projectDir

        # find the root of the repo
        self.__repodir = self.__vcs.findRepoRoot(projectDir)
        if not self.__repodir:
            return

        self.__outputLines = []
        self.__commitIdLength = self.__vcs.getPlugin().getPreferences("CommitIdLength")

        self.__process.kill()
        self.__process.setWorkingDirectory(self.__repodir)

        self.__process.start("git", args)
        procStarted = self.__process.waitForStarted(5000)
        if not procStarted:
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

            self.__refreshButton.setEnabled(False)

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

        self.__refreshButton.setEnabled(True)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setEnabled(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setEnabled(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        self.__resort()
        self.__resizeColumns()

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
            self.__finish()
        elif button == self.__refreshButton:
            self.__refreshButtonClicked()

    @pyqtSlot()
    def __refreshButtonClicked(self):
        """
        Private slot to refresh the worktree display.
        """
        self.start(self.__projectDir)

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
        if self.__process is not None:
            self.__process.setReadChannel(QProcess.ProcessChannel.StandardOutput)

            while self.__process.canReadLine():
                line = str(
                    self.__process.readLine(), self.__ioEncoding, "replace"
                ).strip()
                if line:
                    self.__outputLines.append(line)
                else:
                    self.__generateItem(self.__outputLines)
                    self.__outputLines = []

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

    @pyqtSlot(bool)
    def on_expireCheckBox_toggled(self, checked):
        """
        Private slot to handle a change of the expire checkbox.

        @param checked state of the checkbox
        @type bool
        """
        if checked:
            now = QDateTime.currentDateTime()
            self.expireDateTimeEdit.setMaximumDateTime(now)
            self.expireDateTimeEdit.setMinimumDate(now.date().addDays(-2 * 365))
            self.expireDateTimeEdit.setMinimumTime(QTime(0, 0, 0))
            self.expireDateTimeEdit.setDateTime(now)
        else:
            self.__refreshButtonClicked()

    @pyqtSlot(QDateTime)
    def on_expireDateTimeEdit_dateTimeChanged(self, dateTime):
        """
        Private slot to handle a change of the expire date and time.

        @param dateTime DESCRIPTION
        @type QDateTime
        """
        self.__refreshButtonClicked()

    ###########################################################################
    ## Menu handling methods
    ###########################################################################

    def __showActionsMenu(self):
        """
        Private slot to prepare the actions button menu before it is shown.
        """
        prunableWorktrees = []
        for row in range(self.worktreeList.topLevelItemCount()):
            itm = self.worktreeList.topLevelItem(row)
            status = itm.data(0, GitWorktreeDialog.StatusRole)
            if status == "prunable":
                prunableWorktrees.append(itm.text(self.__pathColumn))

        selectedItems = self.worktreeList.selectedItems()
        enable = bool(selectedItems)
        status = (
            selectedItems[0].data(0, GitWorktreeDialog.StatusRole)
            if selectedItems
            else ""
        )

        self.__lockAct.setEnabled(
            enable
            and status not in ("locked", "locked+current", "main", "main+current")
        )
        self.__unlockAct.setEnabled(enable and status in ("locked", "locked+current"))
        self.__moveAct.setEnabled(
            enable
            and status
            not in (
                "prunable",
                "locked",
                "main",
                "main+current",
                "current",
                "locked+current",
            )
        )
        self.__removeAct.setEnabled(
            enable
            and status
            not in ("locked", "main", "main+current", "current", "locked+current")
        )
        self.__removeForcedAct.setEnabled(
            enable
            and status not in ("main", "main+current", "current", "locked+current")
        )
        self.__pruneAct.setEnabled(bool(prunableWorktrees))

    @pyqtSlot()
    def __worktreeAdd(self):
        """
        Private slot to add a linked worktree.
        """
        from .GitWorktreeAddDialog import GitWorktreeAddDialog

        # find current worktree and take its parent path as the parent directory
        for row in range(self.worktreeList.topLevelItemCount()):
            itm = self.worktreeList.topLevelItem(row)
            if "current" in itm.data(0, GitWorktreeDialog.StatusRole):
                parentDirectory = os.path.dirname(itm.text(self.__pathColumn))
                break
        else:
            parentDirectory = ""

        dlg = GitWorktreeAddDialog(
            parentDirectory,
            self.__vcs.gitGetTagsList(self.__repodir),
            self.__vcs.gitGetBranchesList(self.__repodir),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            params = dlg.getParameters()
            args = ["worktree", "add"]
            if params["force"]:
                args.append("--force")
            if params["detach"]:
                args.append("--detach")
            if params["lock"]:
                args.append("--lock")
                if params["lock_reason"]:
                    args += ["--reason", params["lock_reason"]]
            if params["branch"]:
                args += ["-B" if params["force_branch"] else "-b", params["branch"]]
            args.append(params["path"])
            if params["commit"]:
                args.append(params["commit"])

        dlg = GitDialog(self.tr("Add Worktree"), self.__vcs, parent=self)
        started = dlg.startProcess(args, workingDir=self.__repodir)
        if started:
            dlg.exec()

            self.__refreshButtonClicked()

    @pyqtSlot()
    def __worktreeLock(self):
        """
        Private slot to lock a worktree.
        """
        worktree = self.worktreeList.selectedItems()[0].text(self.__pathColumn)
        if not worktree:
            return

        reason, ok = QInputDialog.getText(
            self,
            self.tr("Lock Worktree"),
            self.tr("Enter a reason for the lock:"),
            QLineEdit.EchoMode.Normal,
        )
        if not ok:
            return

        args = ["worktree", "lock"]
        if reason:
            args += ["--reason", reason]
        args.append(worktree)

        proc = QProcess()
        ok = self.__vcs.startSynchronizedProcess(proc, "git", args, self.__repodir)
        if not ok:
            err = str(proc.readAllStandardError(), self.__ioEncoding, "replace")
            EricMessageBox.critical(
                self,
                self.tr("Lock Worktree"),
                self.tr(
                    "<p>Locking the selected worktree failed.</p><p>{0}</p>"
                ).format(err),
            )

        self.__refreshButtonClicked()

    @pyqtSlot()
    def __worktreeUnlock(self):
        """
        Private slot to unlock a worktree.
        """
        worktree = self.worktreeList.selectedItems()[0].text(self.__pathColumn)
        if not worktree:
            return

        args = ["worktree", "unlock", worktree]

        proc = QProcess()
        ok = self.__vcs.startSynchronizedProcess(proc, "git", args, self.__repodir)
        if not ok:
            err = str(proc.readAllStandardError(), self.__ioEncoding, "replace")
            EricMessageBox.critical(
                self,
                self.tr("Unlock Worktree"),
                self.tr(
                    "<p>Unlocking the selected worktree failed.</p><p>{0}</p>"
                ).format(err),
            )

        self.__refreshButtonClicked()

    @pyqtSlot()
    def __worktreeMove(self):
        """
        Private slot to move a worktree to a new location.
        """
        worktree = self.worktreeList.selectedItems()[0].text(self.__pathColumn)
        if not worktree:
            return

        newPath, ok = EricPathPickerDialog.getStrPath(
            self,
            self.tr("Move Worktree"),
            self.tr("Enter the new path for the worktree:"),
            mode=EricPathPickerDialog.EricPathPickerModes.DIRECTORY_MODE,
            strPath=worktree,
            defaultDirectory=os.path.dirname(worktree),
        )
        if not ok:
            return

        args = ["worktree", "move", worktree, newPath]

        proc = QProcess()
        ok = self.__vcs.startSynchronizedProcess(proc, "git", args, self.__repodir)
        if not ok:
            err = str(proc.readAllStandardError(), self.__ioEncoding, "replace")
            EricMessageBox.critical(
                self,
                self.tr("Move Worktree"),
                self.tr("<p>Moving the selected worktree failed.</p><p>{0}</p>").format(
                    err
                ),
            )

        self.__refreshButtonClicked()

    @pyqtSlot()
    def __worktreeRemove(self, force=False):
        """
        Private slot to remove a linked worktree.

        @param force flag indicating a forceful remove (defaults to False)
        @type bool (optional
        """
        worktree = self.worktreeList.selectedItems()[0].text(self.__pathColumn)
        if not worktree:
            return

        title = (
            self.tr("Remove Worktree")
            if force
            else self.tr("Remove Worktree Forcefully")
        )

        ok = EricMessageBox.yesNo(
            self,
            title,
            self.tr(
                "<p>Do you really want to remove the worktree <b>{0}</b>?</p>"
            ).format(worktree),
        )
        if not ok:
            return

        args = ["worktree", "remove"]
        if force:
            args.append("--force")
            if (
                self.worktreeList.selectedItems()[0].data(
                    0, GitWorktreeDialog.StatusRole
                )
                == "locked"
            ):
                # a second '--force' is needed
                args.append("--force")
        args.append(worktree)

        proc = QProcess()
        ok = self.__vcs.startSynchronizedProcess(proc, "git", args, self.__repodir)
        if not ok:
            err = str(proc.readAllStandardError(), self.__ioEncoding, "replace")
            EricMessageBox.critical(
                self,
                title,
                self.tr(
                    "<p>Removing the selected worktree failed.</p><p>{0}</p>"
                ).format(err),
            )

        self.__refreshButtonClicked()

    @pyqtSlot()
    def __worktreeRemoveForced(self):
        """
        Private slot to remove a linked worktree forcefully.
        """
        self.__worktreeRemove(force=True)

    @pyqtSlot()
    def __worktreePrune(self):
        """
        Private slot to prune worktree information.
        """
        from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog

        prunableWorktrees = []
        for row in range(self.worktreeList.topLevelItemCount()):
            itm = self.worktreeList.topLevelItem(row)
            status = itm.data(0, GitWorktreeDialog.StatusRole)
            if status == "prunable":
                prunableWorktrees.append(itm.text(self.__pathColumn))

        if prunableWorktrees:
            dlg = DeleteFilesConfirmationDialog(
                self,
                self.tr("Prune Worktree Information"),
                self.tr(
                    "Do you really want to prune the information of these worktrees?"
                ),
                prunableWorktrees,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                args = ["worktree", "prune"]
                if self.expireCheckBox.isChecked():
                    args += [
                        "--expire",
                        self.expireDateTimeEdit.dateTime().toString(
                            Qt.DateFormat.ISODate
                        ),
                    ]

                proc = QProcess()
                ok = self.__vcs.startSynchronizedProcess(
                    proc, "git", args, self.__repodir
                )
                if not ok:
                    err = str(proc.readAllStandardError(), self.__ioEncoding, "replace")
                    EricMessageBox.critical(
                        self,
                        self.tr("Prune Worktree Information"),
                        self.tr(
                            "<p>Pruning of the worktree information failed.</p>"
                            "<p>{0}</p>"
                        ).format(err),
                    )

                self.__refreshButtonClicked()

    @pyqtSlot()
    def __worktreeRepair(self, worktreePaths=None):
        """
        Private slot to repair worktree administrative files.

        @param worktreePaths list of worktree paths to be repaired (defaults to None)
        @type list of str (optional)
        """
        args = ["worktree", "repair"]
        if worktreePaths:
            args += worktreePaths

        proc = QProcess()
        ok = self.__vcs.startSynchronizedProcess(proc, "git", args, self.__repodir)
        if ok:
            out = str(proc.readAllStandardError(), self.__ioEncoding, "replace")
            EricMessageBox.information(
                self,
                self.tr("Repair Worktree"),
                self.tr(
                    "<p>Repairing of the worktree administrative files succeeded.</p>"
                    "<p>{0}</p>"
                ).format(out),
            )

        else:
            err = str(proc.readAllStandardError(), self.__ioEncoding, "replace")
            EricMessageBox.critical(
                self,
                self.tr("Repair Worktree"),
                self.tr(
                    "<p>Repairing of the worktree administrative files failed.</p>"
                    "<p>{0}</p>"
                ).format(err),
            )

        self.__refreshButtonClicked()

    @pyqtSlot()
    def __worktreeRepairMultiple(self):
        """
        Private slot to repair worktree administrative files for multiple worktree
        paths.
        """
        from .GitWorktreePathsDialog import GitWorktreePathsDialog

        # find current worktree and take its parent path as the parent directory
        for row in range(self.worktreeList.topLevelItemCount()):
            itm = self.worktreeList.topLevelItem(row)
            if "current" in itm.data(0, GitWorktreeDialog.StatusRole):
                parentDirectory = os.path.dirname(itm.text(self.__pathColumn))
                break
        else:
            parentDirectory = ""

        dlg = GitWorktreePathsDialog(parentDirectory, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            paths = dlg.getPathsList()

            if paths:
                self.__worktreeRepair(worktreePaths=paths)
