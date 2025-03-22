# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter personal data.
"""

from PyQt6.QtWidgets import QDialog

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache

from .Ui_PersonalDataDialog import Ui_PersonalDataDialog


class PersonalDataDialog(QDialog, Ui_PersonalDataDialog):
    """
    Class implementing a dialog to enter personal data.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.iconLabel.setPixmap(EricPixmapCache.getPixmap("pim48"))

        self.firstnameEdit.setText(Preferences.getWebBrowser("PimFirstName"))
        self.lastnameEdit.setText(Preferences.getWebBrowser("PimLastName"))
        self.fullnameEdit.setText(Preferences.getWebBrowser("PimFullName"))
        self.emailEdit.setText(Preferences.getWebBrowser("PimEmail"))
        self.phoneEdit.setText(Preferences.getWebBrowser("PimPhone"))
        self.mobileEdit.setText(Preferences.getWebBrowser("PimMobile"))
        self.addressEdit.setText(Preferences.getWebBrowser("PimAddress"))
        self.cityEdit.setText(Preferences.getWebBrowser("PimCity"))
        self.zipEdit.setText(Preferences.getWebBrowser("PimZip"))
        self.stateEdit.setText(Preferences.getWebBrowser("PimState"))
        self.countryEdit.setText(Preferences.getWebBrowser("PimCountry"))
        self.homepageEdit.setText(Preferences.getWebBrowser("PimHomePage"))
        self.special1Edit.setText(Preferences.getWebBrowser("PimSpecial1"))
        self.special2Edit.setText(Preferences.getWebBrowser("PimSpecial2"))
        self.special3Edit.setText(Preferences.getWebBrowser("PimSpecial3"))
        self.special4Edit.setText(Preferences.getWebBrowser("PimSpecial4"))

    def storeData(self):
        """
        Public method to store the entered personal information.
        """
        Preferences.setWebBrowser("PimFirstName", self.firstnameEdit.text())
        Preferences.setWebBrowser("PimLastName", self.lastnameEdit.text())
        Preferences.setWebBrowser("PimFullName", self.fullnameEdit.text())
        Preferences.setWebBrowser("PimEmail", self.emailEdit.text())
        Preferences.setWebBrowser("PimPhone", self.phoneEdit.text())
        Preferences.setWebBrowser("PimMobile", self.mobileEdit.text())
        Preferences.setWebBrowser("PimAddress", self.addressEdit.text())
        Preferences.setWebBrowser("PimCity", self.cityEdit.text())
        Preferences.setWebBrowser("PimZip", self.zipEdit.text())
        Preferences.setWebBrowser("PimState", self.stateEdit.text())
        Preferences.setWebBrowser("PimCountry", self.countryEdit.text())
        Preferences.setWebBrowser("PimHomePage", self.homepageEdit.text())
        Preferences.setWebBrowser("PimSpecial1", self.special1Edit.text())
        Preferences.setWebBrowser("PimSpecial2", self.special2Edit.text())
        Preferences.setWebBrowser("PimSpecial3", self.special3Edit.text())
        Preferences.setWebBrowser("PimSpecial4", self.special4Edit.text())
