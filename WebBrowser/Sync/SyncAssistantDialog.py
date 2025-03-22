# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a wizard dialog to enter the synchronization data.
"""

from PyQt6.QtWidgets import QWizard

from eric7.EricGui import EricPixmapCache
from eric7.SystemUtilities import OSUtilities

from . import SyncGlobals
from .SyncCheckPage import SyncCheckPage
from .SyncDataPage import SyncDataPage
from .SyncDirectorySettingsPage import SyncDirectorySettingsPage
from .SyncEncryptionPage import SyncEncryptionPage
from .SyncFtpSettingsPage import SyncFtpSettingsPage
from .SyncHostTypePage import SyncHostTypePage


class SyncAssistantDialog(QWizard):
    """
    Class implementing a wizard dialog to enter the synchronization data.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setPage(SyncGlobals.PageData, SyncDataPage(self))
        self.setPage(SyncGlobals.PageEncryption, SyncEncryptionPage(self))
        self.setPage(SyncGlobals.PageType, SyncHostTypePage(self))
        self.setPage(SyncGlobals.PageFTPSettings, SyncFtpSettingsPage(self))
        self.setPage(SyncGlobals.PageDirectorySettings, SyncDirectorySettingsPage(self))
        self.setPage(SyncGlobals.PageCheck, SyncCheckPage(self))

        self.setPixmap(
            QWizard.WizardPixmap.LogoPixmap, EricPixmapCache.getPixmap("ericWeb48")
        )
        self.setPixmap(
            QWizard.WizardPixmap.WatermarkPixmap, EricPixmapCache.getPixmap("eric256")
        )
        self.setPixmap(
            QWizard.WizardPixmap.BackgroundPixmap, EricPixmapCache.getPixmap("eric256")
        )

        self.setMinimumSize(650, 450)
        if OSUtilities.isWindowsPlatform():
            self.setWizardStyle(QWizard.WizardStyle.ModernStyle)

        self.setOption(QWizard.WizardOption.NoCancelButtonOnLastPage, True)
