# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a bundle operation.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_GitBundleDialog import Ui_GitBundleDialog


class GitBundleDialog(QDialog, Ui_GitBundleDialog):
    """
    Class implementing a dialog to enter the data for a bundle operation.
    """

    def __init__(self, tagsList, branchesList, parent=None):
        """
        Constructor

        @param tagsList list of tags
        @type list of str
        @param branchesList list of branches
        @type list of str
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.tagCombo.addItems(sorted(tagsList))
        self.branchCombo.addItems(["main"] + sorted(branchesList))

    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = True
        if self.revisionsButton.isChecked():
            enabled = self.revisionsEdit.text() != ""
        elif self.tagButton.isChecked():
            enabled = self.tagCombo.currentText() != ""
        elif self.branchButton.isChecked():
            enabled = self.branchCombo.currentText() != ""

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    @pyqtSlot(bool)
    def on_revisionsButton_toggled(self, _checked):
        """
        Private slot to handle changes of the revisions select button.

        @param _checked state of the button (unused)
        @type bool
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

    @pyqtSlot(bool)
    def on_branchButton_toggled(self, _checked):
        """
        Private slot to handle changes of the Branch select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_revisionsEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the Revisions edit.

        @param _txt text of the line edit (unused)
        @type str
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

    @pyqtSlot(str)
    def on_branchCombo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the Branch combo.

        @param _txt text of the combo (unused)
        @type str
        """
        self.__updateOK()

    def getData(self):
        """
        Public method to retrieve the bundle data.

        @return list of revision expressions
        @rtype list of str
        """
        if self.revisionsButton.isChecked():
            revs = self.revisionsEdit.text().strip().split()
        elif self.tagButton.isChecked():
            revs = [self.tagCombo.currentText()]
        elif self.branchButton.isChecked():
            revs = [self.branchCombo.currentText()]
        else:
            revs = []

        return revs
