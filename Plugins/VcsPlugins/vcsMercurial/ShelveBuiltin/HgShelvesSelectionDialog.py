# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select multiple shelve names.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_HgShelvesSelectionDialog import Ui_HgShelvesSelectionDialog


class HgShelvesSelectionDialog(QDialog, Ui_HgShelvesSelectionDialog):
    """
    Class implementing a dialog to select multiple shelve names.
    """

    def __init__(self, message, shelveNames, parent=None):
        """
        Constructor

        @param message message to be shown
        @type str
        @param shelveNames list of shelve names
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.message.setText(message)
        self.shelvesList.addItems(shelveNames)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    @pyqtSlot()
    def on_shelvesList_itemSelectionChanged(self):
        """
        Private slot to enabled the OK button if items have been selected.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            len(self.shelvesList.selectedItems()) > 0
        )

    def getSelectedShelves(self):
        """
        Public method to retrieve the selected shelve names.

        @return selected shelve names
        @rtype list of str
        """
        names = []
        for itm in self.shelvesList.selectedItems():
            names.append(itm.text())

        return names
