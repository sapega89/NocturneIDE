# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select one entry from a list of strings.
"""

from PyQt6.QtCore import QCoreApplication, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_EricComboSelectionDialog import Ui_EricComboSelectionDialog


class EricComboSelectionDialog(QDialog, Ui_EricComboSelectionDialog):
    """
    Class implementing a dialog to select one entry from a list of strings.
    """

    def __init__(self, entries, title="", message="", parent=None):
        """
        Constructor

        @param entries list of entries to select from
        @type list of str or list of tuples of (str, any)
        @param title title of the dialog (defaults to "")
        @type str (optional)
        @param message message to be show in the dialog (defaults to "")
        @type str (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        if parent is None:
            parent = QCoreApplication.instance().getMainWindow()

        super().__init__(parent)
        self.setupUi(self)

        for entry in entries:
            if isinstance(entry, tuple):
                self.selectionComboBox.addItem(*entry)
            else:
                self.selectionComboBox.addItem(entry)

        self.on_selectionComboBox_currentTextChanged(self.selectionComboBox.itemText(0))

        if message:
            self.messageLabel.setText(message)
        if title:
            self.setWindowTitle(title)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_selectionComboBox_currentTextChanged(self, txt):
        """
        Private slot to react upon changes of the selected entry.

        @param txt text of the selected entry
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(txt))

    def getSelection(self):
        """
        Public method to retrieve the selected item and its data.

        @return tuple containing the selected entry and its associated data
        @rtype tuple of (str, any)
        """
        return (
            self.selectionComboBox.currentText(),
            self.selectionComboBox.currentData(),
        )
