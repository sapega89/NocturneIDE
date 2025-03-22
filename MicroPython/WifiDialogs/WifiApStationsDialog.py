# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing the currently connected stations (clients).
"""

import binascii

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTreeWidgetItem

from .Ui_WifiApStationsDialog import Ui_WifiApStationsDialog


class WifiApStationsDialog(QDialog, Ui_WifiApStationsDialog):
    """
    Class documentation goes here.
    """

    def __init__(self, stations, parent=None):
        """
        Constructor

        @param stations list of connected stations. Each entry is a tuple containing the
            station's MAC-Address and the RSSI (if supported and available)
        @type tuple of (str, float)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        rssiFound = False

        for station in stations:
            mac = binascii.hexlify(station[0], ":").decode("utf-8")
            if len(station) > 1:
                rssiFound = True
                rssi = str(station[1])
            else:
                rssi = ""
            QTreeWidgetItem(self.stationsList, [mac, rssi, ""])

        self.stationsList.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.stationsList.resizeColumnToContents(0)
        self.stationsList.resizeColumnToContents(1)
        self.stationsList.setColumnHidden(1, not rssiFound)
        self.stationsList.header().setStretchLastSection(True)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.setFocus(Qt.FocusReason.OtherFocusReason)
