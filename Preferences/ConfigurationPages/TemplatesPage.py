# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Templates configuration page.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QFontDialog

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_TemplatesPage import Ui_TemplatesPage


class TemplatesPage(ConfigurationPageBase, Ui_TemplatesPage):
    """
    Class implementing the Templates configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("TemplatesPage")

        # set initial values
        self.templatesAutoOpenGroupsCheckBox.setChecked(
            Preferences.getTemplates("AutoOpenGroups")
        )
        self.templatesSeparatorCharEdit.setText(
            Preferences.getTemplates("SeparatorChar")
        )
        if Preferences.getTemplates("SingleDialog"):
            self.templatesSingleDialogButton.setChecked(True)
        else:
            self.templatesMultiDialogButton.setChecked(True)
        self.templatesToolTipCheckBox.setChecked(
            Preferences.getTemplates("ShowTooltip")
        )
        self.editorFont = Preferences.getTemplates("EditorFont")
        self.editorFontSample.setFont(self.editorFont)

    def save(self):
        """
        Public slot to save the Templates configuration.
        """
        Preferences.setTemplates(
            "AutoOpenGroups", self.templatesAutoOpenGroupsCheckBox.isChecked()
        )
        sepChar = self.templatesSeparatorCharEdit.text()
        if sepChar:
            Preferences.setTemplates("SeparatorChar", sepChar)
        Preferences.setTemplates(
            "SingleDialog", self.templatesSingleDialogButton.isChecked()
        )
        Preferences.setTemplates(
            "ShowTooltip", self.templatesToolTipCheckBox.isChecked()
        )
        Preferences.setTemplates("EditorFont", self.editorFont)

    @pyqtSlot()
    def on_editorFontButton_clicked(self):
        """
        Private method used to select the font to be used by the code editor.
        """
        self.editorFont = self.selectFont(
            self.editorFontSample,
            self.editorFont,
            options=QFontDialog.FontDialogOption.MonospacedFonts,
        )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = TemplatesPage()
    return page
