# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter an IPv4 address.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_IPv4AddressDialog import Ui_IPv4AddressDialog


class IPv4AddressDialog(QDialog, Ui_IPv4AddressDialog):
    """
    Class implementing a dialog to enter an IPv4 address.
    """

    def __init__(self, withDhcp=False, parent=None):
        """
        Constructor

        @param withDhcp flag indicating to allow the DHCP selection
        @type bool
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__withDhcp = withDhcp
        self.dhcpCheckBox.setVisible(withDhcp)
        if withDhcp:
            self.dhcpCheckBox.clicked.connect(self.__updateOk)
            self.dhcpCheckBox.clicked.connect(self.ipAddressGroup.setDisabled)

        self.addressEdit.addressChanged.connect(self.__updateOk)
        self.netmaskEdit.addressChanged.connect(self.__updateOk)
        self.gatewayEdit.addressChanged.connect(self.__updateOk)
        self.dnsEdit.addressChanged.connect(self.__updateOk)

        self.__updateOk()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __updateOk(self):
        """
        Private method to update the enabled state of the OK button.
        """
        enable = (self.__withDhcp and self.dhcpCheckBox.isChecked()) or (
            self.addressEdit.hasAcceptableInput()
            and self.netmaskEdit.hasAcceptableInput()
            and self.gatewayEdit.hasAcceptableInput()
            and self.dnsEdit.hasAcceptableInput()
        )

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    def getIPv4Address(self):
        """
        Public method to get the entered IPv4 address.

        @return tuple containing a tuple of the IPv4 address, the netmask, the gateway
            address and the resolver address or the string 'dhcp' if dynamic addressing
            was selected and the hostname for the device
        @rtype tuple of ((str, str, str, str), str) or (str, str)
        """
        if self.dhcpCheckBox.isChecked():
            return "dhcp", self.hostnameEdit.text()
        else:
            return (
                (
                    self.addressEdit.text(),
                    self.netmaskEdit.text(),
                    self.gatewayEdit.text(),
                    self.dnsEdit.text(),
                ),
                self.hostnameEdit.text(),
            )
