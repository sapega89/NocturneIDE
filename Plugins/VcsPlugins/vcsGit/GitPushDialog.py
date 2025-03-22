# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter data for a Push operation.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QComboBox, QDialog, QTreeWidgetItem

from .Ui_GitPushDialog import Ui_GitPushDialog


class GitPushDialog(QDialog, Ui_GitPushDialog):
    """
    Class implementing a dialog to enter data for a Push operation.
    """

    PushColumn = 0
    LocalBranchColumn = 1
    RemoteBranchColumn = 2
    ForceColumn = 3

    def __init__(self, vcs, repodir, parent=None):
        """
        Constructor

        @param vcs reference to the git object
        @type Git
        @param repodir directory name of the local repository
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__vcs = vcs
        self.__repodir = repodir

        remoteUrlsList = self.__vcs.gitGetRemoteUrlsList(self.__repodir)
        self.__repos = dict(remoteUrlsList)

        remoteBranches = self.__vcs.gitGetBranchesList(self.__repodir, remotes=True)
        self.__remotes = {}
        for remoteBranch in remoteBranches:
            repo, branch = remoteBranch.rsplit("/", 2)[-2:]
            if repo not in self.__remotes:
                self.__remotes[repo] = []
            self.__remotes[repo].append(branch)

        self.__localBranches = self.__vcs.gitGetBranchesList(self.__repodir)

        self.remotesComboBox.addItems(sorted(self.__repos))

        for localBranch in self.__localBranches:
            itm = QTreeWidgetItem(self.branchesTree, ["", localBranch, "", ""])
            combo = QComboBox()
            combo.setEditable(True)
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            self.branchesTree.setItemWidget(
                itm, GitPushDialog.RemoteBranchColumn, combo
            )

        self.__resizeColumns()

        self.branchesTree.header().setSortIndicator(
            GitPushDialog.LocalBranchColumn, Qt.SortOrder.AscendingOrder
        )

        self.forceWarningLabel.setVisible(False)

        index = self.remotesComboBox.findText("origin")
        if index == -1:
            index = 0
        self.remotesComboBox.setCurrentIndex(index)

    def __resizeColumns(self):
        """
        Private slot to adjust the column sizes.
        """
        for col in range(self.branchesTree.columnCount()):
            self.branchesTree.resizeColumnToContents(col)

    @pyqtSlot(str)
    def on_remotesComboBox_currentTextChanged(self, txt):
        """
        Private slot to handle changes of the selected repository.

        @param txt current text of the combo box
        @type str
        """
        self.remoteEdit.setText(self.__repos[txt])

        for row in range(self.branchesTree.topLevelItemCount()):
            itm = self.branchesTree.topLevelItem(row)
            localBranch = itm.text(GitPushDialog.LocalBranchColumn)
            combo = self.branchesTree.itemWidget(itm, GitPushDialog.RemoteBranchColumn)
            combo.clear()
            combo.addItems([""] + sorted(self.__remotes[txt]))
            index = combo.findText(localBranch)
            if index != -1:
                combo.setCurrentIndex(index)
                itm.setCheckState(GitPushDialog.PushColumn, Qt.CheckState.Checked)
            else:
                itm.setCheckState(GitPushDialog.PushColumn, Qt.CheckState.Unchecked)
            itm.setCheckState(GitPushDialog.ForceColumn, Qt.CheckState.Unchecked)

        self.__resizeColumns()

    @pyqtSlot(QTreeWidgetItem, int)
    def on_branchesTree_itemChanged(self, item, column):
        """
        Private slot handling changes of a branch item.

        @param item reference to the changed item
        @type QTreeWidgetItem
        @param column changed column
        @type int
        """
        if column == GitPushDialog.PushColumn:
            # step 1: set the item's remote branch, if it is empty
            if item.checkState(GitPushDialog.PushColumn) == Qt.CheckState.Checked and (
                self.branchesTree.itemWidget(
                    item, GitPushDialog.RemoteBranchColumn
                ).currentText()
                == ""
            ):
                self.branchesTree.itemWidget(
                    item, GitPushDialog.RemoteBranchColumn
                ).setEditText(item.text(GitPushDialog.LocalBranchColumn))

            # step 2: count checked items
            checkedItemsCount = 0
            for row in range(self.branchesTree.topLevelItemCount()):
                itm = self.branchesTree.topLevelItem(row)
                if itm.checkState(GitPushDialog.PushColumn) == Qt.CheckState.Checked:
                    checkedItemsCount += 1
            if checkedItemsCount == len(self.__localBranches):
                self.selectAllCheckBox.setCheckState(Qt.CheckState.Checked)
            elif checkedItemsCount == 0:
                self.selectAllCheckBox.setCheckState(Qt.CheckState.Unchecked)
            else:
                self.selectAllCheckBox.setCheckState(Qt.CheckState.PartiallyChecked)

        elif column == GitPushDialog.ForceColumn:
            forceItemsCount = 0
            for row in range(self.branchesTree.topLevelItemCount()):
                itm = self.branchesTree.topLevelItem(row)
                if itm.checkState(GitPushDialog.ForceColumn) == Qt.CheckState.Checked:
                    forceItemsCount += 1
            self.forceWarningLabel.setVisible(forceItemsCount > 0)

    @pyqtSlot(int)
    def on_selectAllCheckBox_stateChanged(self, state):
        """
        Private slot to select/deselect all branch items.

        @param state check state of the check box
        @type Qt.CheckState
        """
        if state != Qt.CheckState.PartiallyChecked:
            for row in range(self.branchesTree.topLevelItemCount()):
                itm = self.branchesTree.topLevelItem(row)
                if itm.checkState(GitPushDialog.PushColumn) != state:
                    itm.setCheckState(GitPushDialog.PushColumn, state)

    def getData(self):
        """
        Public method to get the entered data.

        @return remote name, list of branches to be pushed,
            a flag indicating to push tags as well, a flag indicating
            to set tracking information and the push method for submodules
        @rtype tuple of (str, list of str, bool, bool, str)
        """
        refspecs = []
        for row in range(self.branchesTree.topLevelItemCount()):
            itm = self.branchesTree.topLevelItem(row)
            force = itm.checkState(GitPushDialog.ForceColumn) == Qt.CheckState.Checked
            if itm.checkState(GitPushDialog.PushColumn) == Qt.CheckState.Checked:
                localBranch = itm.text(GitPushDialog.LocalBranchColumn)
                remoteBranch = self.branchesTree.itemWidget(
                    itm, GitPushDialog.RemoteBranchColumn
                ).currentText()
                refspecs.append(
                    "{0}{1}:{2}".format("+" if force else "", localBranch, remoteBranch)
                )

        # submodule stuff (--recurse-submodules=)
        if self.submodulesOnDemandButton.isChecked():
            submodulesPush = "on-demand"
        elif self.submodulesCheckButton.isChecked():
            submodulesPush = "check"
        elif self.submodulesOnlyButton.isChecked():
            submodulesPush = "only"
        else:
            submodulesPush = "no"

        return (
            self.remotesComboBox.currentText(),
            refspecs,
            self.tagsCheckBox.isChecked(),
            self.trackingCheckBox.isChecked(),
            submodulesPush,
        )
