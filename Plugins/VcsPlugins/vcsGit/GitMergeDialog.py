# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the merge data.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricApplication import ericApp

from .Ui_GitMergeDialog import Ui_GitMergeDialog


class GitMergeDialog(QDialog, Ui_GitMergeDialog):
    """
    Class implementing a dialog to enter the merge data.
    """

    def __init__(
        self, tagsList, branchesList, currentBranch, remoteBranchesList, parent=None
    ):
        """
        Constructor

        @param tagsList list of tags
        @type list of str
        @param branchesList list of branches
        @type list of str
        @param currentBranch name of the current branch
        @type str
        @param remoteBranchesList list of remote branches
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        project = ericApp().getObject("Project")
        pwl, pel = project.getProjectDictionaries()
        language = project.getProjectSpellLanguage()
        self.commitMessageEdit.setLanguageWithPWL(language, pwl or None, pel or None)

        self.__currentBranch = currentBranch

        self.tagCombo.addItems(sorted(tagsList))
        if currentBranch in branchesList:
            branchesList.remove(currentBranch)
        self.branchCombo.addItems(sorted(branchesList))
        self.remoteBranchCombo.addItems(sorted(remoteBranchesList))

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = True
        if self.idButton.isChecked():
            enabled = self.idEdit.text() != ""
        elif self.tagButton.isChecked():
            enabled = self.tagCombo.currentText() != ""
        elif self.branchButton.isChecked():
            enabled = self.branchCombo.currentText() != ""
        elif self.remoteBranchButton.isChecked():
            enabled = self.remoteBranchCombo.currentText() != ""

        enabled &= (
            self.commitGroupBox.isChecked()
            and self.commitMessageEdit.toPlainText() != ""
        )

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    def __generateDefaultCommitMessage(self):
        """
        Private slot to generate a default commit message based on the
        data entered.
        """
        if self.commitGroupBox.isChecked():
            if self.idButton.isChecked():
                msg = "Merged commit {0} into {1}.".format(
                    self.idEdit.text(), self.__currentBranch
                )
            elif self.tagButton.isChecked():
                msg = "Merged tag {0} into {1}.".format(
                    self.tagCombo.currentText(), self.__currentBranch
                )
            elif self.branchButton.isChecked():
                msg = "Merged branch {0} into {1}.".format(
                    self.branchCombo.currentText(), self.__currentBranch
                )
            elif self.remoteBranchButton.isChecked():
                msg = "Merged remote branch {0} into {1}.".format(
                    self.remoteBranchCombo.currentText(), self.__currentBranch
                )
            else:
                msg = "Merged into {0}.".format(self.__currentBranch)
            self.commitMessageEdit.setPlainText(msg)
        else:
            self.commitMessageEdit.clear()

    @pyqtSlot(bool)
    def on_idButton_toggled(self, _checked):
        """
        Private slot to handle changes of the ID select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__generateDefaultCommitMessage()
        self.__updateOK()

    @pyqtSlot(bool)
    def on_tagButton_toggled(self, _checked):
        """
        Private slot to handle changes of the Tag select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__generateDefaultCommitMessage()
        self.__updateOK()

    @pyqtSlot(bool)
    def on_branchButton_toggled(self, _checked):
        """
        Private slot to handle changes of the Branch select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__generateDefaultCommitMessage()
        self.__updateOK()

    @pyqtSlot(bool)
    def on_remoteBranchButton_toggled(self, _checked):
        """
        Private slot to handle changes of the Remote Branch select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__generateDefaultCommitMessage()
        self.__updateOK()

    @pyqtSlot(bool)
    def on_noneButton_toggled(self, _checked):
        """
        Private slot to handle changes of the None select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__generateDefaultCommitMessage()

    @pyqtSlot(str)
    def on_idEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the Commit edit.

        @param _txt text of the edit (unused)
        @type str
        """
        self.__generateDefaultCommitMessage()
        self.__updateOK()

    @pyqtSlot(str)
    def on_tagCombo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the Tag combo.

        @param _txt text of the combo (unused)
        @type str
        """
        self.__generateDefaultCommitMessage()
        self.__updateOK()

    @pyqtSlot(str)
    def on_branchCombo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the Branch combo.

        @param _txt text of the combo (unused)
        @type str
        """
        self.__generateDefaultCommitMessage()
        self.__updateOK()

    @pyqtSlot(str)
    def on_remoteBranchCombo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the Remote Branch combo.

        @param _txt text of the combo (unused)
        @type str
        """
        self.__generateDefaultCommitMessage()
        self.__updateOK()

    @pyqtSlot(bool)
    def on_commitGroupBox_toggled(self, _checked):
        """
        Private slot to handle changes of the Commit select group.

        @param _checked state of the group (unused)
        @type bool
        """
        self.__generateDefaultCommitMessage()
        self.__updateOK()

    @pyqtSlot()
    def on_commitMessageEdit_textChanged(self):
        """
        Private slot to handle changes of the commit message edit.
        """
        self.__updateOK()

    def getParameters(self):
        """
        Public method to retrieve the merge data.

        @return tuple naming the revision, a flag indicating that the merge
            shall be committed, the commit message, a flag indicating that a
            log summary shall be appended and a flag indicating to show diff
            statistics at the end of the merge
        @rtype tuple of (str, bool, str, bool, bool)
        """
        if self.idButton.isChecked():
            rev = self.idEdit.text()
        elif self.tagButton.isChecked():
            rev = self.tagCombo.currentText()
        elif self.branchButton.isChecked():
            rev = self.branchCombo.currentText()
        elif self.remoteBranchButton.isChecked():
            rev = self.remoteBranchCombo.currentText()
        else:
            rev = ""

        return (
            rev,
            self.commitGroupBox.isChecked(),
            self.commitMessageEdit.toPlainText(),
            self.addLogCheckBox.isChecked(),
            self.diffstatCheckBox.isChecked(),
        )
