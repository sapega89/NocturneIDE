# -*- coding: utf-8 -*-
# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing information about the selected security key.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

from .Ui_Fido2InfoDialog import Ui_Fido2InfoDialog


class Fido2InfoDialog(QDialog, Ui_Fido2InfoDialog):
    """
    Class implementing a dialog showing information about the selected security key.
    """

    def __init__(self, header, manager, parent=None):
        """
        Constructor

        @param header header string
        @type str
        @param manager reference to the FIDO2 manager object
        @type Fido2Management
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.headerLabel.setText(f"<b>{header}</b>")

        data = manager.getSecurityKeyInfo()
        if not data:
            itm = QTreeWidgetItem(
                self.infoWidget, [self.tr("No information available.")]
            )
            itm.setFirstColumnSpanned(True)
            return

        for key in data:
            if data[key]:
                topItem = QTreeWidgetItem(
                    self.infoWidget, [manager.FidoInfoCategories2Str.get(key, key)]
                )
                topItem.setFirstColumnSpanned(True)
                topItem.setExpanded(True)
                for entry in data[key]:
                    QTreeWidgetItem(topItem, [str(e) for e in entry])

        self.infoWidget.sortItems(1, Qt.SortOrder.AscendingOrder)
        self.infoWidget.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.infoWidget.resizeColumnToContents(0)
        self.infoWidget.resizeColumnToContents(1)
