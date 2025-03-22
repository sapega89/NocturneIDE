# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing a dialog to enter the country code for the WiFi interface.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Preferences

from .Ui_WifiCountryDialog import Ui_WifiCountryDialog


class WifiCountryDialog(QDialog, Ui_WifiCountryDialog):
    """
    Class implementing a dialog to enter the country code for the WiFi interface.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.countryEdit.setText(Preferences.getMicroPython("WifiCountry").upper())

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_countryEdit_textChanged(self, country):
        """
        Private slot handling a change of the country.

        @param country entered country code
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(country)
        )

    def getCountry(self):
        """
        Public method to get the entered country code.

        @return tuple containing the country code and a flag indicating to save it to
            the settings
        @rtype tuple of (str, bool)
        """
        return self.countryEdit.text().upper(), self.rememberCheckBox.isChecked()
