# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a rebase session.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QButtonGroup, QDialog, QDialogButtonBox

from .Ui_HgRebaseDialog import Ui_HgRebaseDialog


class HgRebaseDialog(QDialog, Ui_HgRebaseDialog):
    """
    Class implementing a dialog to enter the data for a rebase session.
    """

    def __init__(self, tagsList, branchesList, bookmarksList, version, parent=None):
        """
        Constructor

        @param tagsList list of tags
        @type list of str
        @param branchesList list of branches
        @type list of str
        @param bookmarksList list of bookmarks
        @type list of str
        @param version tuple giving the Mercurial version
        @type tuple of int
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__sourceRevisionButtonGroup = QButtonGroup(self)
        self.__sourceRevisionButtonGroup.addButton(self.parentButton)
        self.__sourceRevisionButtonGroup.addButton(self.sourceButton)
        self.__sourceRevisionButtonGroup.addButton(self.baseButton)

        self.tag1Combo.addItems(sorted(tagsList))
        self.tag2Combo.addItems(sorted(tagsList))
        self.branch1Combo.addItems(["default"] + sorted(branchesList))
        self.branch2Combo.addItems(["default"] + sorted(branchesList))
        self.bookmark1Combo.addItems(sorted(bookmarksList))
        self.bookmark2Combo.addItems(sorted(bookmarksList))

        self.dryRunGroup.setEnabled(version >= (4, 7, 0))

        # connect various radio buttons and input fields
        self.id1Button.toggled.connect(self.__updateOK)
        self.tag1Button.toggled.connect(self.__updateOK)
        self.branch1Button.toggled.connect(self.__updateOK)
        self.bookmark1Button.toggled.connect(self.__updateOK)
        self.expression1Button.toggled.connect(self.__updateOK)
        self.id2Button.toggled.connect(self.__updateOK)
        self.tag2Button.toggled.connect(self.__updateOK)
        self.branch2Button.toggled.connect(self.__updateOK)
        self.bookmark2Button.toggled.connect(self.__updateOK)
        self.expression2Button.toggled.connect(self.__updateOK)

        self.id1Edit.textChanged.connect(self.__updateOK)
        self.expression1Edit.textChanged.connect(self.__updateOK)
        self.id2Edit.textChanged.connect(self.__updateOK)
        self.expression2Edit.textChanged.connect(self.__updateOK)

        self.tag1Combo.editTextChanged.connect(self.__updateOK)
        self.branch1Combo.editTextChanged.connect(self.__updateOK)
        self.bookmark1Combo.editTextChanged.connect(self.__updateOK)
        self.tag2Combo.editTextChanged.connect(self.__updateOK)
        self.branch2Combo.editTextChanged.connect(self.__updateOK)
        self.bookmark2Combo.editTextChanged.connect(self.__updateOK)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = True
        if not self.parentButton.isChecked():
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
            tipButton = None
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
        elif tipButton and tipButton.isChecked():
            return ""

        return ""

    def getData(self):
        """
        Public method to retrieve the data for the rebase session.

        @return tuple with a source indicator of "S" or "B", the source
            revision, the destination revision, a flag indicating to collapse,
            a flag indicating to keep the original changesets, a flag
            indicating to keep the original branch name, a flag indicating
            to detach the source, a flag indicating to perform a dry-run only
            and a flag indicating to perform a dry-run first, than ask for
            confirmation
        @rtype tuple of (str, str, str, bool, bool, bool, bool, bool, bool)
        """
        if self.sourceButton.isChecked():
            indicator = "S"
        elif self.baseButton.isChecked():
            indicator = "B"
        else:
            indicator = ""
        rev1 = self.__getRevision(1) if indicator else ""

        return (
            indicator,
            rev1,
            self.__getRevision(2),
            self.collapseCheckBox.isChecked(),
            self.keepChangesetsCheckBox.isChecked(),
            self.keepBranchCheckBox.isChecked(),
            self.detachCheckBox.isChecked(),
            self.dryRunOnlyButton.isChecked(),
            self.dryRunConfirmButton.isChecked(),
        )
