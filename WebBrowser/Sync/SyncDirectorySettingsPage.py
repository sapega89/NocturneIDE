# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the synchronization shared directory settings wizard page.
"""

from PyQt6.QtWidgets import QWizardPage

from eric7 import Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from . import SyncGlobals
from .Ui_SyncDirectorySettingsPage import Ui_SyncDirectorySettingsPage


class SyncDirectorySettingsPage(QWizardPage, Ui_SyncDirectorySettingsPage):
    """
    Class implementing the shared directory host settings wizard page.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.directoryPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.directoryPicker.setText(Preferences.getWebBrowser("SyncDirectoryPath"))

        self.directoryPicker.textChanged.connect(self.completeChanged)

    def nextId(self):
        """
        Public method returning the ID of the next wizard page.

        @return next wizard page ID
        @rtype int
        """
        # save the settings
        Preferences.setWebBrowser("SyncDirectoryPath", self.directoryPicker.text())

        return SyncGlobals.PageCheck

    def isComplete(self):
        """
        Public method to check the completeness of the page.

        @return flag indicating completeness
        @rtype bool
        """
        return self.directoryPicker.text() != ""
