# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show Bluetooth related status information.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTreeWidgetItem

from .Ui_BluetoothStatusDialog import Ui_BluetoothStatusDialog


class BluetoothStatusDialog(QDialog, Ui_BluetoothStatusDialog):
    """
    Class implementing a dialog to show Bluetooth related status information.
    """

    def __init__(self, status, parent=None):
        """
        Constructor

        @param status status data to be show
        @type list of tuples of (str, str)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.statusTree.setColumnCount(2)

        for topic, value in status:
            QTreeWidgetItem(self.statusTree, [topic, str(value)])

        for col in range(self.statusTree.columnCount()):
            self.statusTree.resizeColumnToContents(col)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.setFocus(Qt.FocusReason.OtherFocusReason)
