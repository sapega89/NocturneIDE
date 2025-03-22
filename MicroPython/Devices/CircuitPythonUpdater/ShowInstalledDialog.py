# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the modules installed on the connected device.
"""

import circup

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

from .Ui_ShowInstalledDialog import Ui_ShowInstalledDialog


class ShowInstalledDialog(QDialog, Ui_ShowInstalledDialog):
    """
    Class implementing a dialog to show the modules installed on the connected device.
    """

    def __init__(self, devicePath, parent=None):
        """
        Constructor

        @param devicePath path to the connected board
        @type str
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        backend = circup.DiskBackend(devicePath, circup.logger)
        self.modulesList.clear()
        deviceModules = backend.get_device_versions()
        for name, metadata in deviceModules.items():
            QTreeWidgetItem(
                self.modulesList,
                [name, metadata.get("__version__", self.tr("unknown"))],
            )

        self.modulesList.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.modulesList.resizeColumnToContents(0)
        self.modulesList.resizeColumnToContents(1)
