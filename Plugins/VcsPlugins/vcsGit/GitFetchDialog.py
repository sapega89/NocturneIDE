# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter data for a Fetch operation.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_GitFetchDialog import Ui_GitFetchDialog


class GitFetchDialog(QDialog, Ui_GitFetchDialog):
    """
    Class implementing a dialog to enter data for a Fetch operation.
    """

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

        self.__all = self.tr("<All>")
        self.__custom = self.tr("<Custom>")

        remoteUrlsList = self.__vcs.gitGetRemoteUrlsList(self.__repodir)
        self.__repos = dict(remoteUrlsList)

        self.__okButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)

        self.remotesComboBox.addItems(sorted(self.__repos))
        self.remotesComboBox.addItem(self.__all)
        self.remotesComboBox.addItem(self.__custom)

        index = self.remotesComboBox.findText("origin")
        if index == -1:
            index = 0
        self.remotesComboBox.setCurrentIndex(index)

        localBranches = self.__vcs.gitGetBranchesList(self.__repodir)
        self.localBranchComboBox.addItems([""] + sorted(localBranches))
        self.localBranchComboBox.setEnabled(False)

    def __okButtonEnable(self):
        """
        Private slot to set the enabled state of the OK button.
        """
        self.__okButton.setEnabled(
            self.remoteBranchesList.count() > 0
            or self.remotesComboBox.currentText() == self.__all
        )

    def __updateButtonEnable(self):
        """
        Private slot to set the enabled state of the update button.
        """
        remote = self.remotesComboBox.currentText()
        enable = remote != self.__all
        if remote == self.__custom:
            enable = self.remoteEdit.text() != ""

        self.updateButton.setEnabled(enable)

    @pyqtSlot(str)
    def on_remotesComboBox_currentTextChanged(self, txt):
        """
        Private slot to handle changes of the selected repository.

        @param txt current text of the combo box
        @type str
        """
        self.remoteEdit.setReadOnly(txt != self.__custom)
        self.remoteBranchesList.setEnabled(txt != self.__all)
        self.remoteEdit.clear()
        self.remoteBranchesList.clear()
        self.__updateButtonEnable()
        self.__okButtonEnable()

        if txt not in [self.__all, self.__custom]:
            remoteBranches = self.__vcs.gitGetRemoteBranchesList(self.__repodir, txt)
            self.remoteBranchesList.addItems(sorted(remoteBranches))

            if txt in self.__repos:
                self.remoteEdit.setText(self.__repos[txt])

    @pyqtSlot(str)
    def on_remoteEdit_textChanged(self, txt):
        """
        Private slot to handle changes of the URL edit.

        @param txt current text of the URL edit
        @type str
        """
        self.__updateButtonEnable()

        if self.remotesComboBox.currentText() == self.__custom and txt != "":
            remoteBranches = self.__vcs.gitGetRemoteBranchesList(self.__repodir, txt)
            self.remoteBranchesList.clear()
            self.remoteBranchesList.addItems(sorted(remoteBranches))

        self.__okButtonEnable()

    @pyqtSlot()
    def on_remoteBranchesList_itemSelectionChanged(self):
        """
        Private slot to handle a change of selected remote branches.
        """
        singleSelection = len(self.remoteBranchesList.selectedItems()) == 1
        self.localBranchComboBox.setEnabled(singleSelection)
        txt = (
            self.remoteBranchesList.selectedItems()[0].text() if singleSelection else ""
        )
        index = self.localBranchComboBox.findText(txt)
        if index == -1:
            self.localBranchComboBox.setEditText(txt)
        else:
            self.localBranchComboBox.setCurrentIndex(index)

    @pyqtSlot()
    def on_updateButton_clicked(self):
        """
        Private slot to update the list of remote branches.
        """
        remote = self.remotesComboBox.currentText()
        if remote == self.__all:
            # shouldn't happen
            return

        if remote == self.__custom:
            remote = self.remoteEdit.text()
            if remote == "":
                # shouldn't happen either
                return

        remoteBranches = self.__vcs.gitGetRemoteBranchesList(self.__repodir, remote)
        self.remoteBranchesList.clear()
        self.remoteBranchesList.addItems(sorted(remoteBranches))

        self.__okButtonEnable()

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple of remote name, remote url (for custom remotes),
            remote branches, local branch, a flag indicating to fetch from
            all repositories, a flag indicating to remove obsolete tracking
            references and a flag indicating to fetch tags as well
        @rtype tuple of (str, str, list of str, str, bool, bool, bool)
        """
        remote = ""
        url = ""
        remoteBranches = []
        allRepos = False
        localBranch = ""

        remoteRepo = self.remotesComboBox.currentText()
        if remoteRepo == self.__all:
            allRepos = True
        else:
            if remoteRepo == self.__custom:
                url = self.remoteEdit.text()
            else:
                remote = remoteRepo
            for itm in self.remoteBranchesList.selectedItems():
                remoteBranches.append(itm.text())
            if len(remoteBranches) == 1:
                localBranch = self.localBranchComboBox.currentText()

        return (
            remote,
            url,
            remoteBranches,
            localBranch,
            allRepos,
            self.pruneCheckBox.isChecked(),
            self.tagsCheckBox.isChecked(),
        )
