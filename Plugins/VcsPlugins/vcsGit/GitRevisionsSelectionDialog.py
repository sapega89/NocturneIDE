# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the revisions for the git diff command.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_GitRevisionsSelectionDialog import Ui_GitRevisionsSelectionDialog


class GitRevisionsSelectionDialog(QDialog, Ui_GitRevisionsSelectionDialog):
    """
    Class implementing a dialog to enter the revisions for the git diff
    command.
    """

    def __init__(self, tagsList, branchesList, parent=None):
        """
        Constructor

        @param tagsList list of tags
        @type list of str
        @param branchesList list of branches
        @type list of str
        @param parent parent widget of the dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.tag1Combo.addItems(sorted(tagsList))
        self.tag2Combo.addItems(sorted(tagsList))
        self.branch1Combo.addItems(["main"] + sorted(branchesList))
        self.branch2Combo.addItems(["main"] + sorted(branchesList))

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = True
        if self.rev1Button.isChecked():
            enabled = enabled and self.rev1Edit.text() != ""
        elif self.tag1Button.isChecked():
            enabled = enabled and self.tag1Combo.currentText() != ""
        elif self.branch1Button.isChecked():
            enabled = enabled and self.branch1Combo.currentText() != ""

        if self.rev2Button.isChecked():
            enabled = enabled and self.rev2Edit.text() != ""
        elif self.tag2Button.isChecked():
            enabled = enabled and self.tag2Combo.currentText() != ""
        elif self.branch2Button.isChecked():
            enabled = enabled and self.branch2Combo.currentText() != ""

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    @pyqtSlot(bool)
    def on_rev1Button_toggled(self, _checked):
        """
        Private slot to handle changes of the rev1 select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(bool)
    def on_rev2Button_toggled(self, _checked):
        """
        Private slot to handle changes of the rev2 select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(bool)
    def on_tag1Button_toggled(self, _checked):
        """
        Private slot to handle changes of the Tag1 select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(bool)
    def on_tag2Button_toggled(self, _checked):
        """
        Private slot to handle changes of the Tag2 select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(bool)
    def on_branch1Button_toggled(self, _checked):
        """
        Private slot to handle changes of the Branch1 select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(bool)
    def on_branch2Button_toggled(self, _checked):
        """
        Private slot to handle changes of the Branch2 select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_rev1Edit_textChanged(self, _txt):
        """
        Private slot to handle changes of the rev1 edit.

        @param _txt text of the edit (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_rev2Edit_textChanged(self, _txt):
        """
        Private slot to handle changes of the rev2 edit.

        @param _txt text of the edit (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_tag1Combo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the Tag1 combo.

        @param _txt text of the combo (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_tag2Combo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the Tag2 combo.

        @param _txt text of the combo (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_branch1Combo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the Branch1 combo.

        @param _txt text of the combo (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_branch2Combo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the Branch2 combo.

        @param _txt text of the combo (unused)
        @type str
        """
        self.__updateOK()

    def __getRevision(self, no):
        """
        Private method to generate the revision.

        @param no revision number to generate (1 or 2)
        @type int
        @return revision
        @rtype str
        """
        if no == 1:
            revButton = self.rev1Button
            revEdit = self.rev1Edit
            tagButton = self.tag1Button
            tagCombo = self.tag1Combo
            branchButton = self.branch1Button
            branchCombo = self.branch1Combo
            tipButton = self.tip1Button
            prevButton = self.prev1Button
            noneButton = self.none1Button
        else:
            revButton = self.rev2Button
            revEdit = self.rev2Edit
            tagButton = self.tag2Button
            tagCombo = self.tag2Combo
            branchButton = self.branch2Button
            branchCombo = self.branch2Combo
            tipButton = self.tip2Button
            prevButton = self.prev2Button
            noneButton = self.none2Button

        if revButton.isChecked():
            return revEdit.text()
        elif tagButton.isChecked():
            return tagCombo.currentText()
        elif branchButton.isChecked():
            return branchCombo.currentText()
        elif tipButton.isChecked():
            return "HEAD"
        elif prevButton.isChecked():
            return "HEAD^"
        elif noneButton.isChecked():
            return ""

        return ""

    def getRevisions(self):
        """
        Public method to get the revisions.

        @return list of two revisions
        @rtype list of str
        """
        rev1 = self.__getRevision(1)
        rev2 = self.__getRevision(2)

        return [rev1, rev2]
