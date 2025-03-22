# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data to rename a patch.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_HgQueuesRenamePatchDialog import Ui_HgQueuesRenamePatchDialog


class HgQueuesRenamePatchDialog(QDialog, Ui_HgQueuesRenamePatchDialog):
    """
    Class implementing a dialog to enter the data to rename a patch.
    """

    def __init__(self, currentPatch, patchesList, parent=None):
        """
        Constructor

        @param currentPatch name of the current patch
        @type str
        @param patchesList list of patches to select from
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.currentButton.setText(self.tr("Current Patch ({0})").format(currentPatch))
        self.nameCombo.addItems([""] + patchesList)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateUI(self):
        """
        Private slot to update the UI.
        """
        enable = self.nameEdit.text() != ""
        if self.namedButton.isChecked():
            enable = enable and self.nameCombo.currentText() != ""

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    @pyqtSlot(str)
    def on_nameEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the new name.

        @param _txt text of the edit (unused)
        @type str
        """
        self.__updateUI()

    @pyqtSlot(bool)
    def on_namedButton_toggled(self, _checked):
        """
        Private slot to handle changes of the selection method.

        @param _checked state of the check box (unused)
        @type bool
        """
        self.__updateUI()

    @pyqtSlot(int)
    def on_nameCombo_currentIndexChanged(self, _index):
        """
        Private slot to handle changes of the selected patch name.

        @param _index current index (unused)
        @type int
        """
        self.__updateUI()

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple of new name and selected patch
        @rtype tuple of (str, str)
        """
        selectedPatch = ""
        if self.namedButton.isChecked():
            selectedPatch = self.nameCombo.currentText()

        return self.nameEdit.text().replace(" ", "_"), selectedPatch
