# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing the available WiFi networks.
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import QHeaderView, QTreeWidgetItem, QWidget

from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox

from .Ui_WifiNetworksWindow import Ui_WifiNetworksWindow


class WifiNetworksWindow(QWidget, Ui_WifiNetworksWindow):
    """
    Class implementing a dialog showing the available WiFi networks.
    """

    def __init__(self, device, parent=None):
        """
        Constructor

        @param device reference to the connected device
        @type BaseDevice
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        windowFlags = self.windowFlags()
        windowFlags |= Qt.WindowType.Window
        windowFlags |= Qt.WindowType.WindowContextHelpButtonHint
        self.setWindowFlags(windowFlags)

        self.__device = device

        self.__scanTimer = QTimer(self)
        self.__scanTimer.timeout.connect(self.scanNetworks)

        self.scanButton.clicked.connect(self.scanNetworks)

        self.networkList.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    @pyqtSlot()
    def scanNetworks(self):
        """
        Public slot to ask the device for a network scan and display the result.
        """
        self.networkList.clear()
        self.statusLabel.clear()

        if not self.periodicCheckBox.isChecked():
            self.scanButton.setEnabled(False)
        with EricOverrideCursor():
            networks, error = self.__device.scanNetworks()
        if not self.periodicCheckBox.isChecked():
            self.scanButton.setEnabled(True)

        if error:
            EricMessageBox.warning(
                self,
                self.tr("Scan WiFi Networks"),
                self.tr(
                    """<p>The scan for available WiFi networks failed.</p>"""
                    """<p>Reason: {0}</p>"""
                ).format(error),
            )
            if self.periodicCheckBox.isChecked():
                self.periodicCheckBox.setChecked(False)

        else:
            self.statusLabel.setText(
                self.tr("<p>Detected <b>%n</b> network(s).</p>", "", len(networks))
            )
            macSeen = False
            for network in networks:
                if network[1]:
                    macSeen = True
                itm = QTreeWidgetItem(
                    self.networkList,
                    [
                        network[0],
                        str(network[2]),
                        network[1],
                        str(network[3]),
                        network[4],
                    ],
                )
                itm.setTextAlignment(1, Qt.AlignmentFlag.AlignHCenter)
                itm.setTextAlignment(2, Qt.AlignmentFlag.AlignHCenter)
                itm.setTextAlignment(3, Qt.AlignmentFlag.AlignHCenter)
                itm.setTextAlignment(4, Qt.AlignmentFlag.AlignHCenter)

            self.networkList.setColumnHidden(2, not macSeen)
            self.__resizeColumns()
            self.__resort()

    def __resort(self):
        """
        Private method to resort the networks list.
        """
        self.networkList.sortItems(
            self.networkList.sortColumn(),
            self.networkList.header().sortIndicatorOrder(),
        )

    def __resizeColumns(self):
        """
        Private method to resize the columns of the result list.
        """
        self.networkList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.networkList.header().setStretchLastSection(True)

    def closeEvent(self, _evt):
        """
        Protected method to handle a window close event.

        @param _evt reference to the close event (unused)
        @type QCloseEvent
        """
        self.__scanTimer.stop()

    @pyqtSlot(bool)
    def on_periodicCheckBox_toggled(self, checked):
        """
        Private slot handling the selection of a periodic scan.

        @param checked flag indicating a periodic scan
        @type bool
        """
        self.scanButton.setEnabled(not checked)
        if checked:
            self.__scanTimer.setInterval(self.intervalSpinBox.value() * 1000)
            self.__scanTimer.start()
        else:
            self.__scanTimer.stop()

    @pyqtSlot(int)
    def on_intervalSpinBox_valueChanged(self, interval):
        """
        Private slot handling a change of the periodic scan interval.

        @param interval periodic scan interval
        @type int
        """
        if self.periodicCheckBox.isChecked():
            self.__scanTimer.setInterval(interval * 1000)
