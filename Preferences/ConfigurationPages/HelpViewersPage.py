# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Help Viewers configuration page.
"""

from PyQt6.QtWidgets import QButtonGroup

from eric7 import Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.Globals import getWebBrowserSupport

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_HelpViewersPage import Ui_HelpViewersPage


class HelpViewersPage(ConfigurationPageBase, Ui_HelpViewersPage):
    """
    Class implementing the Help Viewers configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("HelpViewersPage")

        self.customViewerPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)

        self.helpViewerGroup = QButtonGroup()
        self.helpViewerGroup.addButton(self.internalViewerButton, 0)
        self.helpViewerGroup.addButton(self.helpBrowserButton, 1)
        self.helpViewerGroup.addButton(self.qtAssistantButton, 2)
        self.helpViewerGroup.addButton(self.webBrowserButton, 3)
        self.helpViewerGroup.addButton(self.customViewerButton, 4)

        # set initial values
        hvId = Preferences.getHelp("HelpViewerType")
        webBrowserVariant = getWebBrowserSupport()
        if webBrowserVariant != "QtWebEngine":
            if hvId == 1:
                hvId = 0
            self.helpBrowserButton.setEnabled(False)

        self.helpViewerGroup.button(hvId).setChecked(True)
        self.customViewerPicker.setText(Preferences.getHelp("CustomViewer"))
        self.enforceQTBCheckBox.setChecked(Preferences.getHelp("ForceQTextBrowser"))

    def save(self):
        """
        Public slot to save the Help Viewers configuration.
        """
        Preferences.setHelp("HelpViewerType", self.helpViewerGroup.checkedId())
        Preferences.setHelp("CustomViewer", self.customViewerPicker.text())
        Preferences.setHelp("ForceQTextBrowser", self.enforceQTBCheckBox.isChecked())


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = HelpViewersPage()
    return page
