# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select a revision.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_HgRevisionSelectionDialog import Ui_HgRevisionSelectionDialog


class HgRevisionSelectionDialog(QDialog, Ui_HgRevisionSelectionDialog):
    """
    Class implementing a dialog to select a revision.
    """

    def __init__(
        self,
        tagsList,
        branchesList,
        bookmarksList=None,
        noneLabel="",
        revset=True,
        parent=None,
    ):
        """
        Constructor

        @param tagsList list of tags
        @type list of str
        @param branchesList list of branches
        @type list of str
        @param bookmarksList list of bookmarks
        @type list of str
        @param noneLabel labeltext for "no revision selected"
        @type str
        @param revset flag indicating to allow the revision or ID given as a
            revset
        @type bool
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.tagCombo.addItems(sorted(tagsList))
        self.branchCombo.addItems(["default"] + sorted(branchesList))
        if bookmarksList is not None:
            self.bookmarkCombo.addItems(sorted(bookmarksList))
        else:
            self.bookmarkButton.setHidden(True)
            self.bookmarkCombo.setHidden(True)

        if noneLabel:
            self.noneButton.setText(noneLabel)

        self.__revset = revset
        self.expressionButton.setEnabled(revset)

        # connect various radio buttons and input fields
        self.idButton.toggled.connect(self.__updateOK)
        self.tagButton.toggled.connect(self.__updateOK)
        self.branchButton.toggled.connect(self.__updateOK)
        self.bookmarkButton.toggled.connect(self.__updateOK)
        self.expressionButton.toggled.connect(self.__updateOK)

        self.idEdit.textChanged.connect(self.__updateOK)
        self.expressionEdit.textChanged.connect(self.__updateOK)

        self.tagCombo.editTextChanged.connect(self.__updateOK)
        self.branchCombo.editTextChanged.connect(self.__updateOK)
        self.bookmarkCombo.editTextChanged.connect(self.__updateOK)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = True
        if self.idButton.isChecked():
            enabled = bool(self.idEdit.text())
        elif self.tagButton.isChecked():
            enabled = bool(self.tagCombo.currentText())
        elif self.branchButton.isChecked():
            enabled = bool(self.branchCombo.currentText())
        elif self.bookmarkButton.isChecked():
            enabled = bool(self.bookmarkCombo.currentText())
        elif self.expressionButton.isChecked():
            enabled = enabled and bool(self.expressionEdit.text())

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    def getRevision(self):
        """
        Public method to retrieve the selected revision.

        @return selected revision
        @rtype str
        """
        if self.numberButton.isChecked():
            if self.__revset:
                rev = "rev({0})".format(self.numberSpinBox.value())
            else:
                rev = str(self.numberSpinBox.value())
        elif self.idButton.isChecked():
            if self.__revset:
                rev = "id({0})".format(self.idEdit.text())
            else:
                rev = self.idEdit.text()
        elif self.tagButton.isChecked():
            rev = self.tagCombo.currentText()
        elif self.branchButton.isChecked():
            rev = self.branchCombo.currentText()
        elif self.bookmarkButton.isChecked():
            rev = self.bookmarkCombo.currentText()
        elif self.expressionButton.isChecked():
            rev = self.expressionEdit.text()
        elif self.tipButton.isChecked():
            rev = "tip"
        else:
            rev = ""

        return rev
