# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a branch operation.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_HgBranchInputDialog import Ui_HgBranchInputDialog


class HgBranchInputDialog(QDialog, Ui_HgBranchInputDialog):
    """
    Class implementing a dialog to enter the data for a branch operation.
    """

    def __init__(self, branches, parent=None):
        """
        Constructor

        @param branches branch names to populate the branch list with
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.branchComboBox.addItems(sorted(branches))
        self.branchComboBox.setEditText("")

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_branchComboBox_editTextChanged(self, txt):
        """
        Private slot handling a change of the branch name.

        @param txt contents of the branch combo box
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(txt))

    def getData(self):
        """
        Public method to get the data.

        @return tuple of branch name, a flag indicating to commit the branch
            and a flag indicating to force the branch creation
        @rtype tuple of (str, bool, bool)
        """
        return (
            self.branchComboBox.currentText().replace(" ", "_"),
            self.commitCheckBox.isChecked(),
            self.forceCheckBox.isChecked(),
        )
