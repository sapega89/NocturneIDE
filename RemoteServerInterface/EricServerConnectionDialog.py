# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing a dialog to enter the parameters for a connection to an eric-ide
server.
"""

import ipaddress

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Preferences

from .Ui_EricServerConnectionDialog import Ui_EricServerConnectionDialog


class EricServerConnectionDialog(QDialog, Ui_EricServerConnectionDialog):
    """
    Class implementing a dialog to enter the parameters for a connection to an eric-ide
    server.
    """

    def __init__(self, profileNames=None, parent=None):
        """
        Constructor

        @param profileNames list of defined connection profile names (defaults to None)
        @type list of str (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.timeoutSpinBox.setToolTip(
            self.tr(
                "Enter the timeout for the connection attempt (default: {0} s)."
            ).format(Preferences.getEricServer("ConnectionTimeout"))
        )

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        if profileNames is None:
            self.nameLabel.setVisible(False)
            self.nameEdit.setVisible(False)
            self.nameEdit.setEnabled(False)

        self.__profileNames = profileNames[:] if bool(profileNames) else []
        self.__originalName = ""

        self.nameEdit.textChanged.connect(self.__updateOK)
        self.hostnameEdit.textChanged.connect(self.__updateOK)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __updateOK(self):
        """
        Private slot to update the enabled state of the OK button.
        """
        hostname = self.hostnameEdit.text()

        if hostname and hostname[0] in "0123456789" and ":" not in hostname:
            # possibly an IPv4 address
            try:
                ipaddress.IPv4Address(hostname)
                valid = True
            except ipaddress.AddressValueError:
                # leading zeros are not allowed
                valid = False
        elif ":" in hostname:
            # possibly an IPv6 address
            try:
                ipaddress.IPv6Address(hostname)
                valid = True
            except ipaddress.AddressValueError:
                # leading zeros are not allowed
                valid = False
        elif ":" not in hostname:
            valid = bool(hostname)
        else:
            valid = False

        if self.nameEdit.isEnabled():
            # connection profile mode
            name = self.nameEdit.text()
            valid &= name == self.__originalName or name not in self.__profileNames

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(valid)

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the entered host name or IP address, the port number,
            the timeout in seconds and the client ID string
        @rtype tuple of (str, int, int, str)
        """
        port = self.portSpinBox.value()
        if port == self.portSpinBox.minimum():
            port = None

        timeout = self.timeoutSpinBox.value()
        if timeout == self.timeoutSpinBox.minimum():
            timeout = None

        return self.hostnameEdit.text(), port, timeout, self.clientIdEdit.text()

    def getProfileData(self):
        """
        Public method to get the entered data for connection profile mode.

        @return tuple containing the profile name, host name or IP address,
            the port number, the timeout in seconds and the client ID string
        @rtype tuple of (str, str, int, int, str)
        """
        port = self.portSpinBox.value()
        if port == self.portSpinBox.minimum():
            port = 0

        timeout = self.timeoutSpinBox.value()
        if timeout == self.timeoutSpinBox.minimum():
            timeout = 0

        return (
            self.nameEdit.text(),
            self.hostnameEdit.text(),
            port,
            timeout,
            self.clientIdEdit.text(),
        )

    def setProfileData(self, name, hostname, port, timeout, clientId=""):
        """
        Public method to set the connection profile data to be edited.

        @param name profile name
        @type str
        @param hostname host name or IP address
        @type str
        @param port port number
        @type int
        @param timeout timeout value in seconds
        @type int
        @param clientId client ID string (defaults to "")
        @type str (optional)
        """
        # adjust some values
        if not bool(port):
            port = self.portSpinBox.minimum()
        if not bool(timeout):
            timeout = self.timeoutSpinBox.minimum()

        self.__originalName = name

        self.nameEdit.setText(name)
        self.hostnameEdit.setText(hostname)
        self.portSpinBox.setValue(port)
        self.timeoutSpinBox.setValue(timeout)
        self.clientIdEdit.setText(clientId)
