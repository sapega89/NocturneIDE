# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to scan for Bluetooth devices.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QHeaderView, QTreeWidgetItem, QWidget

from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox

from .Ui_BluetoothScanWindow import Ui_BluetoothScanWindow


class BluetoothScanWindow(QWidget, Ui_BluetoothScanWindow):
    """
    Class implementing a dialog to scan for Bluetooth devices.
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

        self.devicesList.setColumnCount(4)
        self.devicesList.headerItem().setText(3, "")

        self.scanButton.clicked.connect(self.scanDevices)

        self.devicesList.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    @pyqtSlot()
    def scanDevices(self):
        """
        Public slot to ask the device for a Bluetooth scan and display the result.
        """
        self.devicesList.clear()
        self.statusLabel.clear()

        self.scanButton.setEnabled(False)
        with EricOverrideCursor():
            scanResults, error = self.__device.getDeviceScan(
                timeout=self.durationSpinBox.value()
            )
        self.scanButton.setEnabled(True)

        if error:
            EricMessageBox.warning(
                self,
                self.tr("Bluetooth Scan"),
                self.tr(
                    """<p>The scan for available devices failed.</p>"""
                    """<p>Reason: {0}</p>"""
                ).format(error),
            )

        else:
            self.statusLabel.setText(
                self.tr("<p>Detected <b>%n</b> device(s).</p>", "", len(scanResults))
            )
            for res in scanResults.values():
                name = res.name
                if not name:
                    name = self.tr("N/A")
                itm = QTreeWidgetItem(
                    self.devicesList, [name, res.address, str(res.rssi)]
                )
                itm.setTextAlignment(1, Qt.AlignmentFlag.AlignHCenter)
                itm.setTextAlignment(2, Qt.AlignmentFlag.AlignHCenter)

                for serviceID, serviceName, isComplete in res.services:
                    if len(serviceID) == 6:
                        bits = 16
                    elif len(serviceID) == 10:
                        bits = 32
                    else:
                        bits = 128
                    template = (
                        self.tr("Complete {0}-bit Service UUID: {1}{2}")
                        if isComplete
                        else self.tr("Incomplete {0}-bit Service UUID: {1}{2}")
                    )
                    citm = QTreeWidgetItem(
                        itm,
                        [
                            template.format(
                                bits,
                                serviceID,
                                (
                                    self.tr(" - {0}").format(serviceName)
                                    if serviceName
                                    else ""
                                ),
                            )
                        ],
                    )
                    citm.setFirstColumnSpanned(True)

                seenMIds = []
                for mid, _, mname in res.manufacturer(withName=True):
                    if mid not in seenMIds:
                        citm = QTreeWidgetItem(
                            itm,
                            [
                                (
                                    self.tr("Manufacturer ID: 0x{0:x} - {1}").format(
                                        mid, mname
                                    )
                                    if bool(mname)
                                    else self.tr("Manufacturer ID: 0x{0:x}").format(mid)
                                )
                            ],
                        )
                        citm.setFirstColumnSpanned(True)
                        seenMIds.append(mid)

                txPower = res.txPower
                if txPower:
                    citm = QTreeWidgetItem(
                        itm, [self.tr("Tx Power Level [dBm]: {0}").format(txPower)]
                    )
                    citm.setFirstColumnSpanned(True)

            self.__resizeColumns()
            self.__resort()

    def __resort(self):
        """
        Private method to resort the devices list.
        """
        self.devicesList.sortItems(
            self.devicesList.sortColumn(),
            self.devicesList.header().sortIndicatorOrder(),
        )

    def __resizeColumns(self):
        """
        Private method to resize the columns of the result list.
        """
        self.devicesList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.devicesList.header().setStretchLastSection(True)
