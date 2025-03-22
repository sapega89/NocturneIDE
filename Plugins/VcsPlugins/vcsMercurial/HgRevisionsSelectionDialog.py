# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the revisions for the hg diff command.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_HgRevisionsSelectionDialog import Ui_HgRevisionsSelectionDialog


class HgRevisionsSelectionDialog(QDialog, Ui_HgRevisionsSelectionDialog):
    """
    Class implementing a dialog to enter the revisions for the hg diff command.
    """

    def __init__(self, tagsList, branchesList, bookmarksList=None, parent=None):
        """
        Constructor

        @param tagsList list of tags
        @type list of str
        @param branchesList list of branches
        @type list of str
        @param bookmarksList list of bookmarks
        @type list of str
        @param parent parent widget of the dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.tag1Combo.addItems(sorted(tagsList))
        self.tag2Combo.addItems(sorted(tagsList))
        self.branch1Combo.addItems(["default"] + sorted(branchesList))
        self.branch2Combo.addItems(["default"] + sorted(branchesList))
        if bookmarksList is not None:
            self.bookmark1Combo.addItems(sorted(bookmarksList))
            self.bookmark2Combo.addItems(sorted(bookmarksList))
        else:
            self.bookmark1Button.setHidden(True)
            self.bookmark1Combo.setHidden(True)
            self.bookmark2Button.setHidden(True)
            self.bookmark2Combo.setHidden(True)

        # connect various radio buttons and input fields
        self.id1Button.toggled.connect(self.__updateOK)
        self.id2Button.toggled.connect(self.__updateOK)
        self.tag1Button.toggled.connect(self.__updateOK)
        self.tag2Button.toggled.connect(self.__updateOK)
        self.branch1Button.toggled.connect(self.__updateOK)
        self.branch2Button.toggled.connect(self.__updateOK)
        self.bookmark1Button.toggled.connect(self.__updateOK)
        self.bookmark2Button.toggled.connect(self.__updateOK)
        self.expression1Button.toggled.connect(self.__updateOK)
        self.expression2Button.toggled.connect(self.__updateOK)

        self.id1Edit.textChanged.connect(self.__updateOK)
        self.id2Edit.textChanged.connect(self.__updateOK)
        self.expression1Edit.textChanged.connect(self.__updateOK)
        self.expression2Edit.textChanged.connect(self.__updateOK)

        self.tag1Combo.editTextChanged.connect(self.__updateOK)
        self.tag2Combo.editTextChanged.connect(self.__updateOK)
        self.branch1Combo.editTextChanged.connect(self.__updateOK)
        self.branch2Combo.editTextChanged.connect(self.__updateOK)
        self.bookmark1Combo.editTextChanged.connect(self.__updateOK)
        self.bookmark2Combo.editTextChanged.connect(self.__updateOK)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = True
        if self.id1Button.isChecked():
            enabled = enabled and bool(self.id1Edit.text())
        elif self.tag1Button.isChecked():
            enabled = enabled and bool(self.tag1Combo.currentText())
        elif self.branch1Button.isChecked():
            enabled = enabled and bool(self.branch1Combo.currentText())
        elif self.bookmark1Button.isChecked():
            enabled = enabled and bool(self.bookmark1Combo.currentText())
        elif self.expression1Button.isChecked():
            enabled = enabled and bool(self.expression1Edit.text())

        if self.id2Button.isChecked():
            enabled = enabled and bool(self.id2Edit.text())
        elif self.tag2Button.isChecked():
            enabled = enabled and bool(self.tag2Combo.currentText())
        elif self.branch2Button.isChecked():
            enabled = enabled and bool(self.branch2Combo.currentText())
        elif self.bookmark2Button.isChecked():
            enabled = enabled and bool(self.bookmark2Combo.currentText())
        elif self.expression2Button.isChecked():
            enabled = enabled and bool(self.expression2Edit.text())

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    def __getRevision(self, no):
        """
        Private method to generate the revision.

        @param no revision number to generate (1 or 2)
        @type int
        @return revision
        @rtype str
        """
        if no == 1:
            numberButton = self.number1Button
            numberSpinBox = self.number1SpinBox
            idButton = self.id1Button
            idEdit = self.id1Edit
            tagButton = self.tag1Button
            tagCombo = self.tag1Combo
            branchButton = self.branch1Button
            branchCombo = self.branch1Combo
            bookmarkButton = self.bookmark1Button
            bookmarkCombo = self.bookmark1Combo
            expressionButton = self.expression1Button
            expressionEdit = self.expression1Edit
            tipButton = self.tip1Button
            prevButton = self.prev1Button
            noneButton = self.none1Button
        else:
            numberButton = self.number2Button
            numberSpinBox = self.number2SpinBox
            idButton = self.id2Button
            idEdit = self.id2Edit
            tagButton = self.tag2Button
            tagCombo = self.tag2Combo
            branchButton = self.branch2Button
            branchCombo = self.branch2Combo
            bookmarkButton = self.bookmark2Button
            bookmarkCombo = self.bookmark2Combo
            expressionButton = self.expression2Button
            expressionEdit = self.expression2Edit
            tipButton = self.tip2Button
            prevButton = self.prev2Button
            noneButton = self.none2Button

        if numberButton.isChecked():
            return "rev({0})".format(numberSpinBox.value())
        elif idButton.isChecked():
            return "id({0})".format(idEdit.text())
        elif tagButton.isChecked():
            return tagCombo.currentText()
        elif branchButton.isChecked():
            return branchCombo.currentText()
        elif bookmarkButton.isChecked():
            return bookmarkCombo.currentText()
        elif expressionButton.isChecked():
            return expressionEdit.text()
        elif tipButton.isChecked():
            return "tip"
        elif prevButton.isChecked():
            return "."
        elif noneButton.isChecked():
            return ""

        return ""

    def getRevisions(self):
        """
        Public method to get the revisions.

        @return list of two revisions
        @rtype list of [str, str]
        """
        rev1 = self.__getRevision(1)
        rev2 = self.__getRevision(2)

        return [rev1, rev2]
