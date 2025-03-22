# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the synchronization host type wizard page.
"""

from PyQt6.QtWidgets import QWizardPage

from eric7 import Preferences

from . import SyncGlobals
from .Ui_SyncHostTypePage import Ui_SyncHostTypePage


class SyncHostTypePage(QWizardPage, Ui_SyncHostTypePage):
    """
    Class implementing the synchronization host type wizard page.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        if Preferences.getWebBrowser("SyncType") == SyncGlobals.SyncTypeFtp:
            self.ftpRadioButton.setChecked(True)
        elif Preferences.getWebBrowser("SyncType") == SyncGlobals.SyncTypeDirectory:
            self.directoryRadioButton.setChecked(True)
        else:
            self.noneRadioButton.setChecked(True)

    def nextId(self):
        """
        Public method returning the ID of the next wizard page.

        @return next wizard page ID
        @rtype int
        """
        # save the settings
        if self.ftpRadioButton.isChecked():
            Preferences.setWebBrowser("SyncType", SyncGlobals.SyncTypeFtp)
            return SyncGlobals.PageFTPSettings
        elif self.directoryRadioButton.isChecked():
            Preferences.setWebBrowser("SyncType", SyncGlobals.SyncTypeDirectory)
            return SyncGlobals.PageDirectorySettings
        else:
            Preferences.setWebBrowser("SyncType", SyncGlobals.SyncTypeNone)
            return SyncGlobals.PageCheck
