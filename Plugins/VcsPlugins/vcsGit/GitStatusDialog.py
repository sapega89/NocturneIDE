# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of the git status command
process.
"""

import os
import tempfile

from PyQt6.QtCore import QProcess, QSize, Qt, QTimer, pyqtSlot
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QMenu,
    QTreeWidgetItem,
    QWidget,
)

from eric7 import Preferences, Utilities
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Globals import strToQByteArray

from .GitDiffGenerator import GitDiffGenerator
from .GitDiffHighlighter import GitDiffHighlighter
from .GitDiffParser import GitDiffParser
from .Ui_GitStatusDialog import Ui_GitStatusDialog


class GitStatusDialog(QWidget, Ui_GitStatusDialog):
    """
    Class implementing a dialog to show the output of the git status command
    process.
    """

    ConflictStates = ["AA", "AU", "DD", "DU", "UA", "UD", "UU"]

    ConflictRole = Qt.ItemDataRole.UserRole

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

        self.__toBeCommittedColumn = 0
        self.__statusWorkColumn = 1
        self.__statusIndexColumn = 2
        self.__pathColumn = 3
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

        self.errorGroup.hide()
        self.inputGroup.hide()

        self.vDiffSplitter.setStretchFactor(0, 2)
        self.vDiffSplitter.setStretchFactor(0, 2)
        self.vDiffSplitter.setSizes([400, 400])
        self.__hDiffSplitterState = None
        self.__vDiffSplitterState = None

        self.statusList.headerItem().setText(self.__lastColumn, "")
        self.statusList.header().setSortIndicator(
            self.__pathColumn, Qt.SortOrder.AscendingOrder
        )

        font = Preferences.getEditorOtherFonts("MonospacedFont")
        self.lDiffEdit.document().setDefaultFont(font)
        self.rDiffEdit.document().setDefaultFont(font)
        self.lDiffEdit.customContextMenuRequested.connect(self.__showLDiffContextMenu)
        self.rDiffEdit.customContextMenuRequested.connect(self.__showRDiffContextMenu)

        self.__lDiffMenu = QMenu()
        self.__stageLinesAct = self.__lDiffMenu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Stage Selected Lines"),
            self.__stageHunkOrLines,
        )
        self.__revertLinesAct = self.__lDiffMenu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Revert Selected Lines"),
            self.__revertHunkOrLines,
        )
        self.__stageHunkAct = self.__lDiffMenu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Stage Hunk"),
            self.__stageHunkOrLines,
        )
        self.__revertHunkAct = self.__lDiffMenu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Revert Hunk"),
            self.__revertHunkOrLines,
        )

        self.__rDiffMenu = QMenu()
        self.__unstageLinesAct = self.__rDiffMenu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Unstage Selected Lines"),
            self.__unstageHunkOrLines,
        )
        self.__unstageHunkAct = self.__rDiffMenu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Unstage Hunk"),
            self.__unstageHunkOrLines,
        )

        self.lDiffHighlighter = GitDiffHighlighter(self.lDiffEdit.document())
        self.rDiffHighlighter = GitDiffHighlighter(self.rDiffEdit.document())

        self.lDiffParser = None
        self.rDiffParser = None

        self.__selectedName = ""

        self.__diffGenerator = GitDiffGenerator(vcs, self)
        self.__diffGenerator.finished.connect(self.__generatorFinished)

        self.modifiedIndicators = [
            self.tr("added"),
            self.tr("copied"),
            self.tr("deleted"),
            self.tr("modified"),
            self.tr("renamed"),
        ]
        self.modifiedOnlyIndicators = [
            self.tr("modified"),
        ]

        self.unversionedIndicators = [
            self.tr("not tracked"),
        ]

        self.missingIndicators = [
            self.tr("deleted"),
        ]

        self.unmergedIndicators = [
            self.tr("unmerged"),
        ]

        self.status = {
            " ": self.tr("unmodified"),
            "A": self.tr("added"),
            "C": self.tr("copied"),
            "D": self.tr("deleted"),
            "M": self.tr("modified"),
            "R": self.tr("renamed"),
            "U": self.tr("unmerged"),
            "?": self.tr("not tracked"),
            "!": self.tr("ignored"),
        }

        self.__ioEncoding = Preferences.getSystem("IOEncoding")

        self.__initActionsMenu()

    def __initActionsMenu(self):
        """
        Private method to initialize the actions menu.
        """
        self.__actionsMenu = QMenu()
        self.__actionsMenu.setTearOffEnabled(True)
        self.__actionsMenu.setToolTipsVisible(True)
        self.__actionsMenu.aboutToShow.connect(self.__showActionsMenu)

        self.__commitAct = self.__actionsMenu.addAction(
            self.tr("Commit"), self.__commit
        )
        self.__commitAct.setToolTip(self.tr("Commit the selected changes"))
        self.__amendAct = self.__actionsMenu.addAction(self.tr("Amend"), self.__amend)
        self.__amendAct.setToolTip(
            self.tr("Amend the latest commit with the selected changes")
        )
        self.__commitSelectAct = self.__actionsMenu.addAction(
            self.tr("Select all for commit"), self.__commitSelectAll
        )
        self.__commitDeselectAct = self.__actionsMenu.addAction(
            self.tr("Unselect all from commit"), self.__commitDeselectAll
        )

        self.__actionsMenu.addSeparator()
        self.__addAct = self.__actionsMenu.addAction(self.tr("Add"), self.__add)
        self.__addAct.setToolTip(self.tr("Add the selected files"))
        self.__stageAct = self.__actionsMenu.addAction(
            self.tr("Stage changes"), self.__stage
        )
        self.__stageAct.setToolTip(self.tr("Stages all changes of the selected files"))
        self.__unstageAct = self.__actionsMenu.addAction(
            self.tr("Unstage changes"), self.__unstage
        )
        self.__unstageAct.setToolTip(
            self.tr("Unstages all changes of the selected files")
        )

        self.__actionsMenu.addSeparator()

        self.__diffAct = self.__actionsMenu.addAction(
            self.tr("Differences"), self.__diff
        )
        self.__diffAct.setToolTip(
            self.tr("Shows the differences of the selected entry in a separate dialog")
        )
        self.__sbsDiffAct = self.__actionsMenu.addAction(
            self.tr("Differences Side-By-Side"), self.__sbsDiff
        )
        self.__sbsDiffAct.setToolTip(
            self.tr(
                "Shows the differences of the selected entry side-by-side in"
                " a separate dialog"
            )
        )

        self.__actionsMenu.addSeparator()

        self.__revertAct = self.__actionsMenu.addAction(
            self.tr("Revert"), self.__revert
        )
        self.__revertAct.setToolTip(
            self.tr("Reverts the changes of the selected files")
        )

        self.__actionsMenu.addSeparator()

        self.__forgetAct = self.__actionsMenu.addAction(
            self.tr("Forget Missing"), self.__forget
        )
        self.__forgetAct.setToolTip(self.tr("Forgets about the selected missing files"))
        self.__restoreAct = self.__actionsMenu.addAction(
            self.tr("Restore Missing"), self.__restoreMissing
        )
        self.__restoreAct.setToolTip(self.tr("Restores the selected missing files"))

        self.__actionsMenu.addSeparator()

        self.__editAct = self.__actionsMenu.addAction(
            self.tr("Edit Conflict"), self.__editConflict
        )
        self.__editAct.setToolTip(self.tr("Edit the selected conflicting file"))

        self.__actionsMenu.addSeparator()

        act = self.__actionsMenu.addAction(
            self.tr("Adjust column sizes"), self.__resizeColumns
        )
        act.setToolTip(self.tr("Adjusts the width of all columns to their contents"))

        self.actionsButton.setIcon(EricPixmapCache.getIcon("actionsToolButton"))
        self.actionsButton.setMenu(self.__actionsMenu)

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

        self.vcs.getPlugin().setPreferences("StatusDialogGeometry", self.saveGeometry())
        self.vcs.getPlugin().setPreferences(
            "StatusDialogSplitterStates",
            [self.vDiffSplitter.saveState(), self.hDiffSplitter.saveState()],
        )

        e.accept()

    def show(self):
        """
        Public slot to show the dialog.
        """
        super().show()

        geom = self.vcs.getPlugin().getPreferences("StatusDialogGeometry")
        if geom.isEmpty():
            s = QSize(900, 600)
            self.resize(s)
        else:
            self.restoreGeometry(geom)

        states = self.vcs.getPlugin().getPreferences("StatusDialogSplitterStates")
        if len(states) == 2:
            # we have two splitters
            self.vDiffSplitter.restoreState(states[0])
            self.hDiffSplitter.restoreState(states[1])

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

    def __generateItem(self, status, path):
        """
        Private method to generate a status item in the status list.

        @param status status indicator
        @type str
        @param path path of the file or directory
        @type str
        """
        statusWorkText = self.status[status[1]]
        statusIndexText = self.status[status[0]]
        itm = QTreeWidgetItem(
            self.statusList,
            [
                "",
                statusWorkText,
                statusIndexText,
                path,
            ],
        )

        itm.setTextAlignment(self.__statusWorkColumn, Qt.AlignmentFlag.AlignHCenter)
        itm.setTextAlignment(self.__statusIndexColumn, Qt.AlignmentFlag.AlignHCenter)
        itm.setTextAlignment(self.__pathColumn, Qt.AlignmentFlag.AlignLeft)

        if (
            status not in self.ConflictStates + ["??", "!!"]
            and statusIndexText in self.modifiedIndicators
        ):
            itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            itm.setCheckState(self.__toBeCommittedColumn, Qt.CheckState.Checked)
        else:
            itm.setFlags(itm.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)

        if statusWorkText not in self.__statusFilters:
            self.__statusFilters.append(statusWorkText)
        if statusIndexText not in self.__statusFilters:
            self.__statusFilters.append(statusIndexText)

        if status in self.ConflictStates:
            itm.setIcon(
                self.__statusWorkColumn,
                EricPixmapCache.getIcon(
                    os.path.join("VcsPlugins", "vcsGit", "icons", "conflict.svg")
                ),
            )
        itm.setData(0, self.ConflictRole, status in self.ConflictStates)

    def start(self, fn):
        """
        Public slot to start the git status command.

        @param fn filename(s)/directoryname(s) to show the status of
        @type str or list of str
        """
        self.errorGroup.hide()
        self.intercept = False
        self.args = fn

        self.__ioEncoding = Preferences.getSystem("IOEncoding")

        self.statusFilterCombo.clear()
        self.__statusFilters = []
        self.statusList.clear()

        self.setWindowTitle(self.tr("Git Status"))

        args = self.vcs.initCommand("status")
        args.append("--porcelain")
        args.append("--")
        if isinstance(fn, list):
            self.dname, _fnames = self.vcs.splitPathList(fn)
            self.vcs.addArguments(args, fn)
        else:
            self.dname, _fname = self.vcs.splitPath(fn)
            args.append(fn)

        # find the root of the repo
        self.__repodir = self.vcs.findRepoRoot(self.dname)
        if not self.__repodir:
            return

        self.process.kill()
        self.process.setWorkingDirectory(self.__repodir)

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

        self.__statusFilters.sort()
        self.__statusFilters.insert(0, "<{0}>".format(self.tr("all")))
        self.statusFilterCombo.addItems(self.__statusFilters)

        self.__resort()
        self.__resizeColumns()

        self.__refreshDiff()

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
                line = str(self.process.readLine(), self.__ioEncoding, "replace")

                status = line[:2]
                path = line[3:].strip().split(" -> ")[-1].strip('"')
                self.__generateItem(status, path)

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

            # show input in case the process asked for some input
            self.inputGroup.setEnabled(True)
            self.inputGroup.show()

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
        selectedItems = self.statusList.selectedItems()
        if len(selectedItems) == 1:
            self.__selectedName = selectedItems[0].text(self.__pathColumn)
        else:
            self.__selectedName = ""

        self.start(self.args)

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
                topItem.setHidden(
                    topItem.text(self.__statusWorkColumn) != txt
                    and topItem.text(self.__statusIndexColumn) != txt
                )

    @pyqtSlot()
    def on_statusList_itemSelectionChanged(self):
        """
        Private slot to act upon changes of selected items.
        """
        self.__generateDiffs()

    ###########################################################################
    ## Menu handling methods
    ###########################################################################

    def __showActionsMenu(self):
        """
        Private slot to prepare the actions button menu before it is shown.
        """
        modified = len(self.__getModifiedItems())
        modifiedOnly = len(self.__getModifiedOnlyItems())
        unversioned = len(self.__getUnversionedItems())
        missing = len(self.__getMissingItems())
        commitable = len(self.__getCommitableItems())
        commitableUnselected = len(self.__getCommitableUnselectedItems())
        stageable = len(self.__getStageableItems())
        unstageable = len(self.__getUnstageableItems())
        conflicting = len(self.__getConflictingItems())

        self.__commitAct.setEnabled(commitable)
        self.__amendAct.setEnabled(commitable)
        self.__commitSelectAct.setEnabled(commitableUnselected)
        self.__commitDeselectAct.setEnabled(commitable)
        self.__addAct.setEnabled(unversioned)
        self.__stageAct.setEnabled(stageable)
        self.__unstageAct.setEnabled(unstageable)
        self.__diffAct.setEnabled(modified)
        self.__sbsDiffAct.setEnabled(modifiedOnly == 1)
        self.__revertAct.setEnabled(stageable)
        self.__forgetAct.setEnabled(missing)
        self.__restoreAct.setEnabled(missing)
        self.__editAct.setEnabled(conflicting == 1)

    def __amend(self):
        """
        Private slot to handle the Amend context menu entry.
        """
        self.__commit(amend=True)

    def __commit(self, amend=False):
        """
        Private slot to handle the Commit context menu entry.

        @param amend flag indicating to perform an amend operation
        @type bool
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
        self.vcs.vcsCommit(names, commitAll=False, amend=amend)
        # staged changes

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

    def __stage(self):
        """
        Private slot to handle the Stage context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getStageableItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Stage"),
                self.tr("""There are no stageable entries available/selected."""),
            )
            return

        self.vcs.vcsAdd(names)
        self.on_refreshButton_clicked()

        project = ericApp().getObject("Project")
        for name in names:
            project.getModel().updateVCSStatus(name)
        self.vcs.checkVCSStatus()

    def __unstage(self):
        """
        Private slot to handle the Unstage context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getUnstageableItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Unstage"),
                self.tr("""There are no unstageable entries available/selected."""),
            )
            return

        self.vcs.gitUnstage(names)
        self.on_refreshButton_clicked()

        project = ericApp().getObject("Project")
        for name in names:
            project.getModel().updateVCSStatus(name)
        self.vcs.checkVCSStatus()

    def __forget(self):
        """
        Private slot to handle the Forget Missing context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getMissingItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Forget Missing"),
                self.tr("""There are no missing entries available/selected."""),
            )
            return

        self.vcs.vcsRemove(names, stageOnly=True)
        self.on_refreshButton_clicked()

    def __revert(self):
        """
        Private slot to handle the Revert context menu entry.
        """
        names = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getStageableItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Revert"),
                self.tr(
                    """There are no uncommitted, unstaged changes"""
                    """ available/selected."""
                ),
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
                self.tr("Restore Missing"),
                self.tr("""There are no missing entries available/selected."""),
            )
            return

        self.vcs.vcsRevert(names)
        self.on_refreshButton_clicked()
        self.vcs.checkVCSStatus()

    def __editConflict(self):
        """
        Private slot to handle the Edit Conflict context menu entry.
        """
        itm = self.__getConflictingItems()[0]
        filename = os.path.join(self.__repodir, itm.text(self.__pathColumn))
        if Utilities.MimeTypes.isTextFile(filename):
            ericApp().getObject("ViewManager").getEditor(filename)

    def __diff(self):
        """
        Private slot to handle the Diff context menu entry.
        """
        from .GitDiffDialog import GitDiffDialog

        namesW = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getStageableItems()
        ]
        namesS = [
            os.path.join(self.dname, itm.text(self.__pathColumn))
            for itm in self.__getUnstageableItems()
        ]
        if not namesW and not namesS:
            EricMessageBox.information(
                self,
                self.tr("Differences"),
                self.tr("""There are no uncommitted changes available/selected."""),
            )
            return

        diffMode = "work2stage2repo"
        names = namesW + namesS

        if self.diff is None:
            self.diff = GitDiffDialog(self.vcs)
        self.diff.show()
        self.diff.start(names, diffMode=diffMode, refreshable=True)

    def __sbsDiff(self):
        """
        Private slot to handle the Side-By-Side Diff context menu entry.
        """
        itm = self.__getModifiedOnlyItems()[0]
        workModified = itm.text(self.__statusWorkColumn) in self.modifiedOnlyIndicators
        stageModified = (
            itm.text(self.__statusIndexColumn) in self.modifiedOnlyIndicators
        )
        names = [os.path.join(self.dname, itm.text(self.__pathColumn))]

        if workModified and stageModified:
            # select from all three variants
            messages = [
                self.tr("Working Tree to Staging Area"),
                self.tr("Staging Area to HEAD Commit"),
                self.tr("Working Tree to HEAD Commit"),
            ]
            result, ok = QInputDialog.getItem(
                None,
                self.tr("Differences Side-by-Side"),
                self.tr("Select the compare method."),
                messages,
                0,
                False,
            )
            if not ok:
                return

            if result == messages[0]:
                revisions = ["", ""]
            elif result == messages[1]:
                revisions = ["HEAD", "Stage"]
            else:
                revisions = ["HEAD", ""]
        elif workModified:
            # select from work variants
            messages = [
                self.tr("Working Tree to Staging Area"),
                self.tr("Working Tree to HEAD Commit"),
            ]
            result, ok = QInputDialog.getItem(
                None,
                self.tr("Differences Side-by-Side"),
                self.tr("Select the compare method."),
                messages,
                0,
                False,
            )
            if not ok:
                return

            if result == messages[0]:
                revisions = ["", ""]
            else:
                revisions = ["HEAD", ""]
        else:
            revisions = ["HEAD", "Stage"]

        self.vcs.vcsSbsDiff(names[0], revisions=revisions)

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

    def __getCommitableUnselectedItems(self):
        """
        Private method to retrieve all entries the user may commit but hasn't
        selected.

        @return list of all items, the user has not checked
        @rtype list of QTreeWidgetItem
        """
        items = []
        for index in range(self.statusList.topLevelItemCount()):
            itm = self.statusList.topLevelItem(index)
            if (
                itm.flags() & Qt.ItemFlag.ItemIsUserCheckable
                == Qt.ItemFlag.ItemIsUserCheckable
            ) and itm.checkState(self.__toBeCommittedColumn) == Qt.CheckState.Unchecked:
                items.append(itm)
        return items

    def __getModifiedItems(self):
        """
        Private method to retrieve all entries, that have a modified status.

        @return list of all items with a modified status
        @rtype list of QTreeWidgetItem
        """
        modifiedItems = []
        for itm in self.statusList.selectedItems():
            if (
                itm.text(self.__statusWorkColumn) in self.modifiedIndicators
                or itm.text(self.__statusIndexColumn) in self.modifiedIndicators
            ):
                modifiedItems.append(itm)
        return modifiedItems

    def __getModifiedOnlyItems(self):
        """
        Private method to retrieve all entries, that have a modified status.

        @return list of all items with a modified status
        @rtype list of QTreeWidgetItem
        """
        modifiedItems = []
        for itm in self.statusList.selectedItems():
            if (
                itm.text(self.__statusWorkColumn) in self.modifiedOnlyIndicators
                or itm.text(self.__statusIndexColumn) in self.modifiedOnlyIndicators
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
            if itm.text(self.__statusWorkColumn) in self.unversionedIndicators:
                unversionedItems.append(itm)
        return unversionedItems

    def __getStageableItems(self):
        """
        Private method to retrieve all entries, that have a stageable
        status.

        @return list of all items with a stageable status
        @rtype list of QTreeWidgetItem
        """
        stageableItems = []
        for itm in self.statusList.selectedItems():
            if (
                itm.text(self.__statusWorkColumn)
                in self.modifiedIndicators + self.unmergedIndicators
            ):
                stageableItems.append(itm)
        return stageableItems

    def __getUnstageableItems(self):
        """
        Private method to retrieve all entries, that have an unstageable
        status.

        @return list of all items with an unstageable status
        @rtype list of QTreeWidgetItem
        """
        unstageableItems = []
        for itm in self.statusList.selectedItems():
            if itm.text(self.__statusIndexColumn) in self.modifiedIndicators:
                unstageableItems.append(itm)
        return unstageableItems

    def __getMissingItems(self):
        """
        Private method to retrieve all entries, that have a missing status.

        @return list of all items with a missing status
        @rtype list of QTreeWidgetItem
        """
        missingItems = []
        for itm in self.statusList.selectedItems():
            if itm.text(self.__statusWorkColumn) in self.missingIndicators:
                missingItems.append(itm)
        return missingItems

    def __getConflictingItems(self):
        """
        Private method to retrieve all entries, that have a conflict status.

        @return list of all items with a conflict status
        @rtype list of QTreeWidgetItem
        """
        conflictingItems = []
        for itm in self.statusList.selectedItems():
            if itm.data(0, self.ConflictRole):
                conflictingItems.append(itm)
        return conflictingItems

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

    ###########################################################################
    ## Diff handling methods below
    ###########################################################################

    def __generateDiffs(self):
        """
        Private slot to generate diff outputs for the selected item.
        """
        colors = {
            "text": Preferences.getDiffColour("TextColor"),
            "added": Preferences.getDiffColour("AddedColor"),
            "removed": Preferences.getDiffColour("RemovedColor"),
            "replaced": Preferences.getDiffColour("ReplacedColor"),
            "context": Preferences.getDiffColour("ContextColor"),
            "header": Preferences.getDiffColour("HeaderColor"),
            "whitespace": Preferences.getDiffColour("BadWhitespaceColor"),
        }
        self.lDiffHighlighter.regenerateRules(
            colors, Preferences.getEditorOtherFonts("MonospacedFont")
        )
        self.rDiffHighlighter.regenerateRules(
            colors, Preferences.getEditorOtherFonts("MonospacedFont")
        )

        self.lDiffEdit.clear()
        self.rDiffEdit.clear()

        selectedItems = self.statusList.selectedItems()
        if len(selectedItems) == 1:
            fn = os.path.join(self.dname, selectedItems[0].text(self.__pathColumn))
            self.__diffGenerator.start(fn, diffMode="work2stage2repo")

    def __generatorFinished(self):
        """
        Private slot connected to the finished signal of the diff generator.
        """
        diff1, diff2 = self.__diffGenerator.getResult()[:2]

        if diff1:
            self.lDiffParser = GitDiffParser(diff1)
            for line in diff1[:]:
                if line.startswith("@@ "):
                    break
                else:
                    diff1.pop(0)
            self.lDiffEdit.setPlainText("".join(diff1))
        else:
            self.lDiffParser = None

        if diff2:
            self.rDiffParser = GitDiffParser(diff2)
            for line in diff2[:]:
                if line.startswith("@@ "):
                    break
                else:
                    diff2.pop(0)
            self.rDiffEdit.setPlainText("".join(diff2))
        else:
            self.rDiffParser = None

        for diffEdit in [self.lDiffEdit, self.rDiffEdit]:
            tc = diffEdit.textCursor()
            tc.movePosition(QTextCursor.MoveOperation.Start)
            diffEdit.setTextCursor(tc)
            diffEdit.ensureCursorVisible()

    def __showLDiffContextMenu(self, coord):
        """
        Private slot to show the context menu of the status list.

        @param coord position of the mouse pointer
        @type QPoint
        """
        if bool(self.lDiffEdit.toPlainText()):
            cursor = self.lDiffEdit.textCursor()
            if cursor.hasSelection():
                self.__stageLinesAct.setEnabled(True)
                self.__revertLinesAct.setEnabled(True)
                self.__stageHunkAct.setEnabled(False)
                self.__revertHunkAct.setEnabled(False)
            else:
                self.__stageLinesAct.setEnabled(False)
                self.__revertLinesAct.setEnabled(False)
                self.__stageHunkAct.setEnabled(True)
                self.__revertHunkAct.setEnabled(True)

                cursor = self.lDiffEdit.cursorForPosition(coord)
                self.lDiffEdit.setTextCursor(cursor)

            self.__lDiffMenu.popup(self.lDiffEdit.mapToGlobal(coord))

    def __showRDiffContextMenu(self, coord):
        """
        Private slot to show the context menu of the status list.

        @param coord position of the mouse pointer
        @type QPoint
        """
        if bool(self.rDiffEdit.toPlainText()):
            cursor = self.rDiffEdit.textCursor()
            if cursor.hasSelection():
                self.__unstageLinesAct.setEnabled(True)
                self.__unstageHunkAct.setEnabled(False)
            else:
                self.__unstageLinesAct.setEnabled(False)
                self.__unstageHunkAct.setEnabled(True)

                cursor = self.rDiffEdit.cursorForPosition(coord)
                self.rDiffEdit.setTextCursor(cursor)

            self.__rDiffMenu.popup(self.rDiffEdit.mapToGlobal(coord))

    def __stageHunkOrLines(self):
        """
        Private method to stage the selected lines or hunk.
        """
        cursor = self.lDiffEdit.textCursor()
        startIndex, endIndex = self.__selectedLinesIndexes(self.lDiffEdit)
        patch = (
            self.lDiffParser.createLinesPatch(startIndex, endIndex)
            if cursor.hasSelection()
            else self.lDiffParser.createHunkPatch(startIndex)
        )
        if patch:
            patchFile = self.__tmpPatchFileName()
            try:
                with open(patchFile, "w") as f:
                    f.write(patch)
                self.vcs.gitApply(self.dname, patchFile, cached=True, noDialog=True)
                self.on_refreshButton_clicked()
            finally:
                os.remove(patchFile)

    def __unstageHunkOrLines(self):
        """
        Private method to unstage the selected lines or hunk.
        """
        cursor = self.rDiffEdit.textCursor()
        startIndex, endIndex = self.__selectedLinesIndexes(self.rDiffEdit)
        patch = (
            self.rDiffParser.createLinesPatch(startIndex, endIndex, reverse=True)
            if cursor.hasSelection()
            else self.rDiffParser.createHunkPatch(startIndex)
        )
        if patch:
            patchFile = self.__tmpPatchFileName()
            try:
                with open(patchFile, "w") as f:
                    f.write(patch)
                self.vcs.gitApply(
                    self.dname, patchFile, cached=True, reverse=True, noDialog=True
                )
                self.on_refreshButton_clicked()
            finally:
                os.remove(patchFile)

    def __revertHunkOrLines(self):
        """
        Private method to revert the selected lines or hunk.
        """
        cursor = self.lDiffEdit.textCursor()
        startIndex, endIndex = self.__selectedLinesIndexes(self.lDiffEdit)
        title = (
            self.tr("Revert selected lines")
            if cursor.hasSelection()
            else self.tr("Revert hunk")
        )
        res = EricMessageBox.yesNo(
            self,
            title,
            self.tr("""Are you sure you want to revert the selected changes?"""),
        )
        if res:
            if cursor.hasSelection():
                patch = self.lDiffParser.createLinesPatch(
                    startIndex, endIndex, reverse=True
                )
            else:
                patch = self.lDiffParser.createHunkPatch(startIndex)
            if patch:
                patchFile = self.__tmpPatchFileName()
                try:
                    with open(patchFile, "w") as f:
                        f.write(patch)
                    self.vcs.gitApply(
                        self.dname, patchFile, reverse=True, noDialog=True
                    )
                    self.on_refreshButton_clicked()
                finally:
                    os.remove(patchFile)

    def __selectedLinesIndexes(self, diffEdit):
        """
        Private method to extract the indexes of the selected lines.

        @param diffEdit reference to the edit widget
        @type QTextEdit
        @return tuple of start and end indexes
        @rtype tuple of (int, int)
        """
        cursor = diffEdit.textCursor()
        selectionStart = cursor.selectionStart()
        selectionEnd = cursor.selectionEnd()

        startIndex = -1

        lineStart = 0
        for lineIdx, line in enumerate(diffEdit.toPlainText().splitlines()):
            lineEnd = lineStart + len(line)
            if lineStart <= selectionStart <= lineEnd:
                startIndex = lineIdx
            if lineStart <= selectionEnd <= lineEnd:
                endIndex = lineIdx
                break
            lineStart = lineEnd + 1

        return startIndex, endIndex

    def __tmpPatchFileName(self):
        """
        Private method to generate a temporary patch file.

        @return name of the temporary file
        @rtype str
        """
        prefix = "eric-git-{0}-".format(os.getpid())
        suffix = "-patch"
        fd, path = tempfile.mkstemp(suffix, prefix)
        os.close(fd)
        return path

    def __refreshDiff(self):
        """
        Private method to refresh the diff output after a refresh.
        """
        if self.__selectedName:
            for index in range(self.statusList.topLevelItemCount()):
                itm = self.statusList.topLevelItem(index)
                if itm.text(self.__pathColumn) == self.__selectedName:
                    itm.setSelected(True)
                    break

        self.__selectedName = ""
