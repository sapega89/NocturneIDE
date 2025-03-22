# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Shell configuration page.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QFontDialog

from eric7 import Preferences
from eric7.QScintilla.Shell import ShellHistoryStyle

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_ShellPage import Ui_ShellPage


class ShellPage(ConfigurationPageBase, Ui_ShellPage):
    """
    Class implementing the Shell configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("ShellPage")

        self.shellHistoryStyleComboBox.addItem(
            self.tr("Disabled"), ShellHistoryStyle.DISABLED.value
        )
        self.shellHistoryStyleComboBox.addItem(
            self.tr("Linux Style"), ShellHistoryStyle.LINUXSTYLE.value
        )
        self.shellHistoryStyleComboBox.addItem(
            self.tr("Windows Style"), ShellHistoryStyle.WINDOWSSTYLE.value
        )

        # set initial values
        self.shellLinenoCheckBox.setChecked(Preferences.getShell("LinenoMargin"))
        self.shellWordWrapCheckBox.setChecked(Preferences.getShell("WrapEnabled"))
        self.shellACEnabledCheckBox.setChecked(
            Preferences.getShell("AutoCompletionEnabled")
        )
        self.shellCTEnabledCheckBox.setChecked(Preferences.getShell("CallTipsEnabled"))
        self.shellSyntaxHighlightingCheckBox.setChecked(
            Preferences.getShell("SyntaxHighlightingEnabled")
        )
        self.rememberCheckBox.setChecked(
            Preferences.getShell("StartWithMostRecentlyUsedEnvironment")
        )
        self.shellHistorySpinBox.setValue(Preferences.getShell("MaxHistoryEntries"))
        index = self.shellHistoryStyleComboBox.findData(
            Preferences.getShell("HistoryStyle").value
        )
        self.shellHistoryStyleComboBox.setCurrentIndex(index)
        self.shellHistoryWrapCheckBox.setChecked(Preferences.getShell("HistoryWrap"))
        self.shellHistoryCursorKeysCheckBox.setChecked(
            Preferences.getShell("HistoryNavigateByCursor")
        )
        self.stdOutErrCheckBox.setChecked(Preferences.getShell("ShowStdOutErr"))

        self.monospacedFont = Preferences.getShell("MonospacedFont")
        self.monospacedFontSample.setFont(self.monospacedFont)
        self.monospacedCheckBox.setChecked(Preferences.getShell("UseMonospacedFont"))
        self.marginsFont = Preferences.getShell("MarginsFont")
        self.marginsFontSample.setFont(self.marginsFont)

        self.timeoutSpinBox.setValue(Preferences.getShell("CommandExecutionTimeout"))

    def save(self):
        """
        Public slot to save the Shell configuration.
        """
        Preferences.setShell("LinenoMargin", self.shellLinenoCheckBox.isChecked())
        Preferences.setShell("WrapEnabled", self.shellWordWrapCheckBox.isChecked())
        Preferences.setShell(
            "AutoCompletionEnabled", self.shellACEnabledCheckBox.isChecked()
        )
        Preferences.setShell("CallTipsEnabled", self.shellCTEnabledCheckBox.isChecked())
        Preferences.setShell(
            "SyntaxHighlightingEnabled",
            self.shellSyntaxHighlightingCheckBox.isChecked(),
        )
        Preferences.setShell(
            "StartWithMostRecentlyUsedEnvironment", self.rememberCheckBox.isChecked()
        )
        Preferences.setShell("MaxHistoryEntries", self.shellHistorySpinBox.value())
        Preferences.setShell(
            "HistoryStyle",
            ShellHistoryStyle(self.shellHistoryStyleComboBox.currentData()),
        )
        Preferences.setShell("HistoryWrap", self.shellHistoryWrapCheckBox.isChecked())
        Preferences.setShell(
            "HistoryNavigateByCursor", self.shellHistoryCursorKeysCheckBox.isChecked()
        )
        Preferences.setShell("ShowStdOutErr", self.stdOutErrCheckBox.isChecked())

        Preferences.setShell("MonospacedFont", self.monospacedFont)
        Preferences.setShell("UseMonospacedFont", self.monospacedCheckBox.isChecked())
        Preferences.setShell("MarginsFont", self.marginsFont)

        Preferences.setShell("CommandExecutionTimeout", self.timeoutSpinBox.value())

    @pyqtSlot()
    def on_monospacedFontButton_clicked(self):
        """
        Private method used to select the font to be used as the monospaced
        font.
        """
        self.monospacedFont = self.selectFont(
            self.monospacedFontSample,
            self.monospacedFont,
            options=QFontDialog.FontDialogOption.MonospacedFonts,
        )

    @pyqtSlot()
    def on_linenumbersFontButton_clicked(self):
        """
        Private method used to select the font for the editor margins.
        """
        self.marginsFont = self.selectFont(
            self.marginsFontSample,
            self.marginsFont,
            options=QFontDialog.FontDialogOption.MonospacedFonts,
        )

    def polishPage(self):
        """
        Public slot to perform some polishing actions.
        """
        self.monospacedFontSample.setFont(self.monospacedFont)
        self.marginsFontSample.setFont(self.marginsFont)


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = ShellPage()
    return page
