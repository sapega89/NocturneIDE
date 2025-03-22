# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select the port to connect to and the type of
the attached device.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Devices import getSupportedDevices
from .Ui_ConnectionSelectionDialog import Ui_ConnectionSelectionDialog


class ConnectionSelectionDialog(QDialog, Ui_ConnectionSelectionDialog):
    """
    Class implementing a dialog to select the port to connect to and the type
    of the attached device.
    """

    PortNameRole = Qt.ItemDataRole.UserRole
    VidPidRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, ports, currentPort, currentType, parent=None):
        """
        Constructor

        @param ports list of detected ports
        @type list of str
        @param currentPort port most recently selected
        @type str
        @param currentType device type most recently selected
        @type str
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        for index, (vid, pid, description, portName) in enumerate(
            sorted(ports, key=lambda x: x[3])
        ):
            self.portNameComboBox.addItem(
                self.tr("{0} - {1}", "description - port name").format(
                    description, portName
                )
            )
            self.portNameComboBox.setItemData(index, portName, self.PortNameRole)
            self.portNameComboBox.setItemData(index, (vid, pid), self.VidPidRole)

        self.deviceTypeComboBox.addItem("", "")
        for board, description in sorted(getSupportedDevices(), key=lambda x: x[1]):
            self.deviceTypeComboBox.addItem(description, board)

        if self.portNameComboBox.currentText():
            # some ports were found; use the previously selected type as
            # default
            portIndex = self.portNameComboBox.findData(currentPort, self.PortNameRole)
            typeIndex = self.deviceTypeComboBox.findData(currentType)
        else:
            portIndex = 0
            typeIndex = 0
        self.portNameComboBox.setCurrentIndex(portIndex)
        self.deviceTypeComboBox.setCurrentIndex(typeIndex)

        self.__updateOK()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateOK(self):
        """
        Private method to update the status of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.portNameComboBox.currentData(self.PortNameRole))
            and bool(self.deviceTypeComboBox.currentData())
        )

    @pyqtSlot(str)
    def on_portNameComboBox_currentTextChanged(self, _txt):
        """
        Private slot to handle the selection of a port name.

        @param _txt selected port (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_deviceTypeComboBox_currentTextChanged(self, _txt):
        """
        Private slot to handle the selection of a device type.

        @param _txt selected device description (unused)
        @type str
        """
        self.__updateOK()

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the VID, PID and name of the selected port
            and the selected device type
        @rtype tuple of (int, int, str, str)
        """
        return (
            *self.portNameComboBox.currentData(self.VidPidRole),
            self.portNameComboBox.currentData(self.PortNameRole),
            self.deviceTypeComboBox.currentData(),
        )
