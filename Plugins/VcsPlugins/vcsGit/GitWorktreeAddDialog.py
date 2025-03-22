# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a 'git worktree add' operation.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_GitWorktreeAddDialog import Ui_GitWorktreeAddDialog


class GitWorktreeAddDialog(QDialog, Ui_GitWorktreeAddDialog):
    """
    Class implementing a dialog to enter the data for a 'git worktree add' operation.
    """

    def __init__(self, parentDirectory, tagsList, branchesList, parent=None):
        """
        Constructor

        @param parentDirectory path of the worktrees parent directory
        @type str
        @param tagsList list of tags
        @type list of str
        @param branchesList list of branches
        @type list of str
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__parentDirectory = parentDirectory

        self.worktreePathPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.worktreePathPicker.setDefaultDirectory(parentDirectory)
        self.worktreePathPicker.setText(parentDirectory)

        self.tagCombo.addItems(sorted(tagsList))
        self.branchCombo.addItems(["main"] + sorted(branchesList))

        self.__updateOK()

    def __updateOK(self):
        """
        Private method to set the enabled state of the OK button.
        """
        enable = True
        if self.revButton.isChecked():
            enable = self.revEdit.text() != ""
        elif self.tagButton.isChecked():
            enable = self.tagCombo.currentText() != ""
        elif self.branchButton.isChecked():
            enable = self.branchCombo.currentText() != ""

        worktreePath = self.worktreePathPicker.text()
        enable &= bool(worktreePath) and worktreePath not in (
            self.__parentDirectory,
            self.__parentDirectory + "/",
            self.__parentDirectory + "\\",
        )

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    @pyqtSlot(str)
    def on_worktreePathPicker_textChanged(self, _worktree):
        """
        Private slot handling a change of the worktree path.

        @param _worktree entered worktree path (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(bool)
    def on_revButton_toggled(self, _checked):
        """
        Private slot to handle changes of the rev select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_revEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the rev edit.

        @param _txt text of the edit (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(bool)
    def on_tagButton_toggled(self, _checked):
        """
        Private slot to handle changes of the Tag select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_tagCombo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the Tag combo.

        @param _txt text of the combo (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(bool)
    def on_branchButton_toggled(self, _checked):
        """
        Private slot to handle changes of the Branch select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_branchCombo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the Branch combo.

        @param _txt text of the combo (unused)
        @type str
        """
        self.__updateOK()

    def getParameters(self):
        """
        Public method to get the entered parameters for the 'git worktree add'
        operation.

        @return dictionary containing the entered data. This dictionary has these keys.
            <ul>
            <li>path: path for the new worktree</li>
            <li>branch: name for the worktree branch</li>
            <li>force_branch: enforce creating the branch</li>
            <li>lock: flag indicating to lock the worktree</li>
            <li>lock_reason: optional reason string for the lock</li>
            <li>detach: flag indicating to detach the HEAD in the new worktree</li>
            <li>commit: commit to check out in the new worktree (branch, tag, commit ID
                or empty for HEAD) </li>
            <li>force: flag indicating to enforce the worktree creation</li>
            </ul>
        @rtype dict
        """
        if self.revButton.isChecked():
            commit = self.revEdit.text()
        elif self.tagButton.isChecked():
            commit = self.tagCombo.currentText()
        elif self.branchButton.isChecked():
            commit = self.branchCombo.currentText()
        else:
            commit = ""

        return {
            "path": self.worktreePathPicker.text(),
            "branch": self.branchNameEdit.text(),
            "force_branch": self.forceBranchCheckBox.isChecked(),
            "lock": self.lockCheckBox.isChecked(),
            "lock_reason": self.lockReasonEdit.text(),
            "detach": self.detachCheckBox.isChecked(),
            "commit": commit,
            "force": self.forceCheckBox.isChecked(),
        }
