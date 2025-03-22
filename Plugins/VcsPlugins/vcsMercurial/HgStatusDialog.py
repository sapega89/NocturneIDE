# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the output of the hg status command
process.
"""

import os

from PyQt6.QtCore import QSize, Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import (
    QDialogButtonBox,
    QHeaderView,
    QMenu,
    QTreeWidgetItem,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from .HgDiffGenerator import HgDiffGenerator
from .HgDiffHighlighter import HgDiffHighlighter
from .Ui_HgStatusDialog import Ui_HgStatusDialog


class HgStatusDialog(QWidget, Ui_HgStatusDialog):
    """
    Class implementing a dialog to show the output of the hg status command
    process.
    """

    def __init__(self, vcs, mq=False, parent=None):
        """
        Constructor

        @param vcs reference to the vcs object
        @type Hg
        @param mq flag indicating to show a queue repo status
        @type bool
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__toBeCommittedColumn = 0
        self.__statusColumn = 1
        self.__pathColumn = 2
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
        self.__hgClient = self.vcs.getClient()
        self.__mq = mq

        self.statusList.headerItem().setText(self.__lastColumn, "")
        self.statusList.header().setSortIndicator(
            self.__pathColumn, Qt.SortOrder.AscendingOrder
        )

        font = Preferences.getEditorOtherFonts("MonospacedFont")
        self.diffEdit.document().setDefaultFont(font)

        self.diffHighlighter = HgDiffHighlighter(self.diffEdit.document())
        self.__diffGenerator = HgDiffGenerator(vcs, self)
        self.__diffGenerator.finished.connect(self.__generatorFinished)

        self.__selectedName = ""

        self.modifiedIndicators = [
            self.tr("added"),
            self.tr("modified"),
            self.tr("removed"),
        ]

        self.unversionedIndicators = [
            self.tr("not tracked"),
        ]

        self.missingIndicators = [self.tr("missing")]

        self.status = {
            "A": self.tr("added"),
            "C": self.tr("normal"),
            "I": self.tr("ignored"),
            "M": self.tr("modified"),
            "R": self.tr("removed"),
            "?": self.tr("not tracked"),
            "!": self.tr("missing"),
        }

        self.__initActionsMenu()

        if mq:
            self.diffLabel.setVisible(False)
            self.diffEdit.setVisible(False)
            self.actionsButton.setEnabled(False)
            self.diffSplitter.setSizes([600, 0])
        else:
            self.diffSplitter.setSizes([300, 300])

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
        self.__commitSelectAct = self.__actionsMenu.addAction(
            self.tr("Select all for commit"), self.__commitSelectAll
        )
        self.__commitDeselectAct = self.__actionsMenu.addAction(
            self.tr("Unselect all from commit"), self.__commitDeselectAll
        )

        self.__actionsMenu.addSeparator()

        self.__addAct = self.__actionsMenu.addAction(self.tr("Add"), self.__add)
        self.__addAct.setToolTip(self.tr("Add the selected files"))
        self.__lfAddLargeAct = self.__actionsMenu.addAction(
            self.tr("Add as Large Files"), lambda: self.__lfAdd("large")
        )
        self.__lfAddLargeAct.setToolTip(
            self.tr(
                "Add the selected files as a large files using the 'Large Files'"
                " extension"
            )
        )
        self.__lfAddNormalAct = self.__actionsMenu.addAction(
            self.tr("Add as Normal Files"), lambda: self.__lfAdd("normal")
        )
        self.__lfAddNormalAct.setToolTip(
            self.tr(
                "Add the selected files as a normal files using the 'Large Files'"
                " extension"
            )
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

        self.__commitMergeAct = self.__actionsMenu.addAction(
            self.tr("Commit Merge"), self.__commitMerge
        )
        self.__commitMergeAct.setToolTip(self.tr("Commit all the merged changes."))
        self.__abortMergeAct = self.__actionsMenu.addAction(
            self.tr("Abort Merge"), self.__abortMerge
        )
        self.__commitMergeAct.setToolTip(
            self.tr("Abort an uncommitted merge and lose all changes")
        )

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
        if self.__hgClient.isExecuting():
            self.__hgClient.cancel()

        if self.__mq:
            self.vcs.getPlugin().setPreferences(
                "MqStatusDialogGeometry", self.saveGeometry()
            )
            self.vcs.getPlugin().setPreferences(
                "MqStatusDialogSplitterState", self.diffSplitter.saveState()
            )
        else:
            self.vcs.getPlugin().setPreferences(
                "StatusDialogGeometry", self.saveGeometry()
            )
            self.vcs.getPlugin().setPreferences(
                "StatusDialogSplitterState", self.diffSplitter.saveState()
            )

        e.accept()

    def show(self):
        """
        Public slot to show the dialog.
        """
        super().show()

        geom = (
            self.vcs.getPlugin().getPreferences("MqStatusDialogGeometry")
            if self.__mq
            else self.vcs.getPlugin().getPreferences("StatusDialogGeometry")
        )
        if geom.isEmpty():
            s = QSize(800, 600)
            self.resize(s)
        else:
            self.restoreGeometry(geom)

        diffSplitterState = (
            self.vcs.getPlugin().getPreferences("MqStatusDialogSplitterState")
            if self.__mq
            else self.vcs.getPlugin().getPreferences("StatusDialogSplitterState")
        )
        if diffSplitterState is not None:
            self.diffSplitter.restoreState(diffSplitterState)

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
        statusText = self.status[status]
        itm = QTreeWidgetItem(
            self.statusList,
            [
                "",
                statusText,
                path,
            ],
        )

        itm.setTextAlignment(1, Qt.AlignmentFlag.AlignHCenter)
        itm.setTextAlignment(2, Qt.AlignmentFlag.AlignLeft)

        if status in "AMR":
            itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            itm.setCheckState(self.__toBeCommittedColumn, Qt.CheckState.Checked)
        else:
            itm.setFlags(itm.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)

        if statusText not in self.__statusFilters:
            self.__statusFilters.append(statusText)

    def start(self, fn):
        """
        Public slot to start the hg status command.

        @param fn filename(s)/directoryname(s) to show the status of
        @type str or list of str
        """
        self.errorGroup.hide()
        self.intercept = False
        self.args = fn

        self.actionsButton.setEnabled(False)

        self.statusFilterCombo.clear()
        self.__statusFilters = []
        self.statusList.clear()

        if self.__mq:
            self.setWindowTitle(self.tr("Mercurial Queue Repository Status"))
        else:
            self.setWindowTitle(self.tr("Mercurial Status"))

        args = self.vcs.initCommand("status")
        if self.__mq:
            args.append("--mq")
        else:
            if self.vcs.hasSubrepositories():
                args.append("--subrepos")

            if isinstance(fn, list):
                self.vcs.addArguments(args, fn)
            else:
                args.append(fn)

        self.refreshButton.setEnabled(False)

        self.__repoPath = self.__hgClient.getRepository()

        out, err = self.__hgClient.runcommand(args)
        if err:
            self.__showError(err)
        if out:
            for line in out.splitlines():
                self.__processOutputLine(line)
                if self.__hgClient.wasCanceled():
                    break
        self.__finish()

    def __finish(self):
        """
        Private slot called when the process finished or the user pressed
        the button.
        """
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

        if not self.__mq:
            self.actionsButton.setEnabled(True)

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
            self.__hgClient.cancel()
        elif button == self.refreshButton:
            self.on_refreshButton_clicked()

    def __processOutputLine(self, line):
        """
        Private method to process the lines of output.

        @param line output line to be processed
        @type str
        """
        if line[0] in "ACIMR?!" and line[1] == " ":
            status, path = line.strip().split(" ", 1)
            self.__generateItem(status, path)

    def __showError(self, out):
        """
        Private slot to show some error.

        @param out error to be shown
        @type str
        """
        self.errorGroup.show()
        self.errors.insertPlainText(out)
        self.errors.ensureCursorVisible()

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
                topItem.setHidden(topItem.text(self.__statusColumn) != txt)

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
        if self.vcs.canCommitMerge():
            self.__commitMergeAct.setEnabled(True)
            self.__abortMergeAct.setEnabled(True)

            self.__addAct.setEnabled(False)
            self.__diffAct.setEnabled(False)
            self.__sbsDiffAct.setEnabled(False)
            self.__revertAct.setEnabled(False)
            self.__forgetAct.setEnabled(False)
            self.__restoreAct.setEnabled(False)
            self.__commitAct.setEnabled(False)
            self.__commitSelectAct.setEnabled(False)
            self.__commitDeselectAct.setEnabled(False)

            self.__lfAddLargeAct.setEnabled(False)
            self.__lfAddNormalAct.setEnabled(False)

        else:
            self.__commitMergeAct.setEnabled(False)
            self.__abortMergeAct.setEnabled(False)

            modified = len(self.__getModifiedItems())
            unversioned = len(self.__getUnversionedItems())
            missing = len(self.__getMissingItems())
            commitable = len(self.__getCommitableItems())
            commitableUnselected = len(self.__getCommitableUnselectedItems())

            self.__addAct.setEnabled(unversioned)
            self.__diffAct.setEnabled(modified)
            self.__sbsDiffAct.setEnabled(modified == 1)
            self.__revertAct.setEnabled(modified)
            self.__forgetAct.setEnabled(missing)
            self.__restoreAct.setEnabled(missing)
            self.__commitAct.setEnabled(commitable)
            self.__commitSelectAct.setEnabled(commitableUnselected)
            self.__commitDeselectAct.setEnabled(commitable)

            if self.vcs.isExtensionActive("largefiles"):
                enable = bool(unversioned)
            else:
                enable = False
            self.__lfAddLargeAct.setEnabled(enable)
            self.__lfAddNormalAct.setEnabled(enable)

    def __commit(self):
        """
        Private slot to handle the Commit context menu entry.
        """
        if self.__mq:
            self.vcs.vcsCommit(self.__repoPath, "", mq=True)
        else:
            names = [
                os.path.join(self.__repoPath, itm.text(self.__pathColumn))
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
            os.path.join(self.__repoPath, itm.text(self.__pathColumn))
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

    def __lfAdd(self, mode):
        """
        Private slot to add a file to the repository.

        @param mode add mode (one of 'normal' or 'large')
        @type str
        """
        names = [
            os.path.join(self.__repoPath, itm.text(self.__pathColumn))
            for itm in self.__getUnversionedItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Add"),
                self.tr("""There are no unversioned entries available/selected."""),
            )
            return

        self.vcs.getExtensionObject("largefiles").hgAdd(names, mode)
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
            os.path.join(self.__repoPath, itm.text(self.__pathColumn))
            for itm in self.__getMissingItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Forget Missing"),
                self.tr("""There are no missing entries available/selected."""),
            )
            return

        self.vcs.vcsForget(names)
        self.on_refreshButton_clicked()

    def __revert(self):
        """
        Private slot to handle the Revert context menu entry.
        """
        names = [
            os.path.join(self.__repoPath, itm.text(self.__pathColumn))
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
            os.path.join(self.__repoPath, itm.text(self.__pathColumn))
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

    def __diff(self):
        """
        Private slot to handle the Diff context menu entry.
        """
        from .HgDiffDialog import HgDiffDialog

        names = [
            os.path.join(self.__repoPath, itm.text(self.__pathColumn))
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
            self.diff = HgDiffDialog(self.vcs)
        self.diff.show()
        self.diff.start(names, refreshable=True)

    def __sbsDiff(self):
        """
        Private slot to handle the Side-By-Side Diff context menu entry.
        """
        names = [
            os.path.join(self.__repoPath, itm.text(self.__pathColumn))
            for itm in self.__getModifiedItems()
        ]
        if not names:
            EricMessageBox.information(
                self,
                self.tr("Differences Side-By-Side"),
                self.tr("""There are no uncommitted changes available/selected."""),
            )
            return
        elif len(names) > 1:
            EricMessageBox.information(
                self,
                self.tr("Differences Side-By-Side"),
                self.tr(
                    """Only one file with uncommitted changes"""
                    """ must be selected."""
                ),
            )
            return

        self.vcs.vcsSbsDiff(names[0])

    def __getCommitableItems(self):
        """
        Private method to retrieve all entries the user wants to commit.

        @return list of all items, the user has checked
        @rtype list of QTreeWidgetItems
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

        @return list of all items, the user has checked
        @rtype list of QTreeWidgetItems
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
        @rtype list of QTreeWidgetItems
        """
        modifiedItems = []
        for itm in self.statusList.selectedItems():
            if itm.text(self.__statusColumn) in self.modifiedIndicators:
                modifiedItems.append(itm)
        return modifiedItems

    def __getUnversionedItems(self):
        """
        Private method to retrieve all entries, that have an unversioned
        status.

        @return list of all items with an unversioned status
        @rtype list of QTreeWidgetItems
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
        @rtype list of QTreeWidgetItems
        """
        missingItems = []
        for itm in self.statusList.selectedItems():
            if itm.text(self.__statusColumn) in self.missingIndicators:
                missingItems.append(itm)
        return missingItems

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

    def __commitMerge(self):
        """
        Private slot to handle the Commit Merge context menu entry.
        """
        self.vcs.vcsCommit(self.__repoPath, self.tr("Merge"), merge=True)
        self.__committed()

    def __abortMerge(self):
        """
        Private slot used to abort an uncommitted merge.
        """
        self.vcs.hgAbortMerge()
        self.__committed()

    ###########################################################################
    ## Diff handling methods below
    ###########################################################################

    def __generateDiffs(self):
        """
        Private slot to generate diff outputs for the selected item.
        """
        self.diffHighlighter.regenerateRules(
            {
                "text": Preferences.getDiffColour("TextColor"),
                "added": Preferences.getDiffColour("AddedColor"),
                "removed": Preferences.getDiffColour("RemovedColor"),
                "replaced": Preferences.getDiffColour("ReplacedColor"),
                "context": Preferences.getDiffColour("ContextColor"),
                "header": Preferences.getDiffColour("HeaderColor"),
                "whitespace": Preferences.getDiffColour("BadWhitespaceColor"),
            },
            Preferences.getEditorOtherFonts("MonospacedFont"),
        )

        self.diffEdit.clear()

        if not self.__mq:
            selectedItems = self.statusList.selectedItems()
            if len(selectedItems) == 1:
                fn = os.path.join(
                    self.__repoPath, selectedItems[0].text(self.__pathColumn)
                )
                self.__diffGenerator.start(fn)

    def __generatorFinished(self):
        """
        Private slot connected to the finished signal of the diff generator.
        """
        diff = self.__diffGenerator.getResult()[0]

        if diff:
            for line in diff[:]:
                if line.startswith("@@ "):
                    break
                else:
                    diff.pop(0)
            self.diffEdit.setPlainText("".join(diff))

        tc = self.diffEdit.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.Start)
        self.diffEdit.setTextCursor(tc)
        self.diffEdit.ensureCursorVisible()

    def __refreshDiff(self):
        """
        Private method to refresh the diff output after a refresh.
        """
        if self.__selectedName and not self.__mq:
            for index in range(self.statusList.topLevelItemCount()):
                itm = self.statusList.topLevelItem(index)
                if itm.text(self.__pathColumn) == self.__selectedName:
                    itm.setSelected(True)
                    break

        self.__selectedName = ""
