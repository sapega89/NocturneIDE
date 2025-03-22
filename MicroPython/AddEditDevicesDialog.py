# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to add or edit data of unknown MicroPython
devices.
"""

from PyQt6.QtCore import Qt, QUrl, QUrlQuery, pyqtSlot
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.UI.Info import BugAddress

from .Devices import getSupportedDevices
from .Ui_AddEditDevicesDialog import Ui_AddEditDevicesDialog


class AddEditDevicesDialog(QDialog, Ui_AddEditDevicesDialog):
    """
    Class implementing a dialog to add or edit data of unknown MicroPython
    devices.
    """

    def __init__(self, vid=0, pid=0, description=0, deviceData=None, parent=None):
        """
        Constructor

        Note: Either vid and pid and description or deviceData dictionary
        must be given.

        @param vid vendor ID of the device (defaults to 0)
        @type int (optional)
        @param pid product ID of the device (defaults to 0)
        @type int (optional)
        @param description description for the device (defaults to "")
        @type str (optional)
        @param deviceData type of the device (defaults to None)
        @type dict (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        # populate the device type combo box
        self.deviceTypeComboBox.addItem("", "")
        for board, desc in sorted(getSupportedDevices(), key=lambda x: x[1]):
            self.deviceTypeComboBox.addItem(desc, board)

        if deviceData is not None:
            self.vidEdit.setText("0x{0:04x}".format(deviceData["vid"]))
            self.pidEdit.setText("0x{0:04x}".format(deviceData["pid"]))
            self.descriptionEdit.setText(deviceData["description"])
            self.deviceTypeComboBox.setCurrentIndex(
                self.deviceTypeComboBox.findData(deviceData["type"])
            )
            self.dataVolumeEdit.setText(deviceData["data_volume"])
            self.flashVolumeEdit.setText(deviceData["flash_volume"])
        else:
            self.vidEdit.setText("0x{0:04x}".format(vid))
            self.pidEdit.setText("0x{0:04x}".format(pid))
            self.descriptionEdit.setText(description)
            self.deviceTypeComboBox.setCurrentText("")
            self.dataVolumeEdit.setText("")
            self.flashVolumeEdit.setText("")

        self.deviceTypeComboBox.setFocus(Qt.FocusReason.OtherFocusReason)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(int)
    def on_deviceTypeComboBox_currentIndexChanged(self, _index):
        """
        Private slot to handle the selection of a device type.

        @param _index index of the current item (unused)
        @type int
        """
        board = self.deviceTypeComboBox.currentData()
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(board)
        )
        self.reportButton.setEnabled(bool(board))

    @pyqtSlot()
    def on_reportButton_clicked(self):
        """
        Private slot to report the entered data to the eric-bugs email address.
        """
        body = "\r\n".join(
            [
                "This is an unknown MicroPython device. Please add it.",
                "",
                "VID: {0}".format(self.vidEdit.text()),
                "PID: {0}".format(self.pidEdit.text()),
                "Description: {0}".format(self.descriptionEdit.text()),
                "Device Type: {0}".format(self.deviceTypeComboBox.currentData()),
                "Data Volume: {0}".format(self.dataVolumeEdit.text().strip()),
                "Flash Volume: {0}".format(self.flashVolumeEdit.text().strip()),
            ]
        )

        urlQuery = QUrlQuery()
        urlQuery.addQueryItem("subject", "Unsupported MicroPython Device")
        urlQuery.addQueryItem("body", body)

        url = QUrl("mailto:{0}".format(BugAddress))
        url.setQuery(urlQuery)

        QDesktopServices.openUrl(url)

    def getDeviceDict(self):
        """
        Public method to get the entered data as a dictionary.

        @return dictionary containing the entered data
        @rtype dict
        """
        return {
            "vid": int(self.vidEdit.text(), 16),
            "pid": int(self.pidEdit.text(), 16),
            "description": self.descriptionEdit.text(),
            "type": self.deviceTypeComboBox.currentData(),
            "data_volume": self.dataVolumeEdit.text().strip(),
            "flash_volume": self.flashVolumeEdit.text().strip(),
        }
