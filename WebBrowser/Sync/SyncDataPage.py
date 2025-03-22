# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the synchronization data wizard page.
"""

from PyQt6.QtWidgets import QWizardPage

from eric7 import Preferences

from . import SyncGlobals
from .Ui_SyncDataPage import Ui_SyncDataPage


class SyncDataPage(QWizardPage, Ui_SyncDataPage):
    """
    Class implementing the synchronization data wizard page.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.bookmarksCheckBox.setChecked(Preferences.getWebBrowser("SyncBookmarks"))
        self.historyCheckBox.setChecked(Preferences.getWebBrowser("SyncHistory"))
        self.passwordsCheckBox.setChecked(Preferences.getWebBrowser("SyncPasswords"))
        self.userAgentsCheckBox.setChecked(Preferences.getWebBrowser("SyncUserAgents"))
        self.speedDialCheckBox.setChecked(Preferences.getWebBrowser("SyncSpeedDial"))

        self.activeCheckBox.setChecked(Preferences.getWebBrowser("SyncEnabled"))

    def nextId(self):
        """
        Public method returning the ID of the next wizard page.

        @return next wizard page ID
        @rtype int
        """
        # save the settings
        Preferences.setWebBrowser("SyncEnabled", self.activeCheckBox.isChecked())

        Preferences.setWebBrowser("SyncBookmarks", self.bookmarksCheckBox.isChecked())
        Preferences.setWebBrowser("SyncHistory", self.historyCheckBox.isChecked())
        Preferences.setWebBrowser("SyncPasswords", self.passwordsCheckBox.isChecked())
        Preferences.setWebBrowser("SyncUserAgents", self.userAgentsCheckBox.isChecked())
        Preferences.setWebBrowser("SyncSpeedDial", self.speedDialCheckBox.isChecked())

        if self.activeCheckBox.isChecked():
            return SyncGlobals.PageEncryption
        else:
            return SyncGlobals.PageCheck
