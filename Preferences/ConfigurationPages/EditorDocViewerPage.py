# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor Documentation Viewer configuration page.
"""

from eric7 import Preferences
from eric7.EricWidgets.EricApplication import ericApp

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorDocViewerPage import Ui_EditorDocViewerPage


class EditorDocViewerPage(ConfigurationPageBase, Ui_EditorDocViewerPage):
    """
    Class implementing the Editor Documentation Viewer configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorExportersPage")

        try:
            providers = ericApp().getObject("DocuViewer").getProviders()
            for provider, text in providers:
                self.providerComboBox.addItem(text, provider)

            self.infoLabel.clear()

            # set initial values
            self.parenthesisCheckBox.setChecked(
                Preferences.getDocuViewer("ShowInfoOnOpenParenthesis")
            )

            provider = Preferences.getDocuViewer("Provider")
            self.viewerGroupBox.setChecked(provider != "disabled")

            index = self.providerComboBox.findData(provider)
            if index >= 0:
                self.providerComboBox.setCurrentIndex(index)
        except KeyError:
            # documentation viewer is globally disabled
            self.viewerGroupBox.setChecked(False)
            self.viewerGroupBox.setEnabled(False)
            self.infoLabel.setText(
                self.tr(
                    "The Documentation Viewer is disabled globally. Re-enable it"
                    " on the Interface/Interface configuration page and restart"
                    " the eric."
                )
            )

    def save(self):
        """
        Public slot to save the Editor Typing configuration.
        """
        enabled = self.viewerGroupBox.isChecked()
        if enabled:
            Preferences.setDocuViewer(
                "ShowInfoOnOpenParenthesis", self.parenthesisCheckBox.isChecked()
            )
            Preferences.setDocuViewer(
                "Provider",
                self.providerComboBox.itemData(self.providerComboBox.currentIndex()),
            )
        else:
            Preferences.setDocuViewer("Provider", "disabled")


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorDocViewerPage()
    return page
