# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the parameters needed to connect to a WiFi
network.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache

from .Ui_WifiConnectionDialog import Ui_WifiConnectionDialog


class WifiConnectionDialog(QDialog, Ui_WifiConnectionDialog):
    """
    Class implementing a dialog to enter the parameters needed to connect to a WiFi
    network.
    """

    def __init__(self, withCountry=False, parent=None):
        """
        Constructor

        @param withCountry flag indicating to show the country entry (defaults to False)
        @type bool
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.showPasswordButton.setIcon(EricPixmapCache.getIcon("showPassword"))

        self.countryLabel.setVisible(withCountry)
        self.countryEdit.setVisible(withCountry)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        # populate the field with data saved to the preferences
        self.ssidEdit.setText(Preferences.getMicroPython("WifiName"))
        self.passwordEdit.setText(Preferences.getMicroPython("WifiPassword"))
        self.hostnameEdit.setText(Preferences.getMicroPython("WifiHostname"))
        if withCountry:
            self.countryEdit.setText(Preferences.getMicroPython("WifiCountry").upper())

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_ssidEdit_textChanged(self, ssid):
        """
        Private slot handling a change of the SSID.

        @param ssid entered SSID
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(ssid))

    @pyqtSlot(bool)
    def on_showPasswordButton_clicked(self, checked):
        """
        Private slot to show or hide the password.

        @param checked state of the button
        @type bool
        """
        if checked:
            self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.showPasswordButton.setIcon(EricPixmapCache.getIcon("hidePassword"))
            self.showPasswordButton.setToolTip(self.tr("Press to hide the password"))
        else:
            self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Password)
            self.showPasswordButton.setIcon(EricPixmapCache.getIcon("showPassword"))
            self.showPasswordButton.setToolTip(self.tr("Press to show the password"))

    @pyqtSlot()
    def accept(self):
        """
        Public slot accepting the dialog.
        """
        if self.rememberCheckBox.isChecked():
            Preferences.setMicroPython("WifiName", self.ssidEdit.text())
            Preferences.setMicroPython("WifiPassword", self.passwordEdit.text())
            Preferences.setMicroPython("WifiHostname", self.hostnameEdit.text())
            if self.countryEdit.isVisible():
                Preferences.setMicroPython(
                    "WifiCountry", self.countryEdit.text().upper()
                )

        super().accept()

    def getConnectionParameters(self):
        """
        Public method to get the entered connection parameters.

        @return tuple containing the SSID, the password and the host name
        @rtype tuple of (str, str, str)
        """
        return (
            self.ssidEdit.text(),
            self.passwordEdit.text(),
            self.hostnameEdit.text(),
        )

    def getCountryCode(self):
        """
        Public method to get the entered country code.

        @return DESCRIPTION
        @rtype TYPE
        """
        return self.countryEdit.text().upper()
