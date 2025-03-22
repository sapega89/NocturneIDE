# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor Autocompletion configuration page.
"""

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorAutocompletionPage import Ui_EditorAutocompletionPage


class EditorAutocompletionPage(ConfigurationPageBase, Ui_EditorAutocompletionPage):
    """
    Class implementing the Editor Autocompletion configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorAutocompletionPage")

        # set initial values
        self.acEnabledGroupBox.setChecked(
            Preferences.getEditor("AutoCompletionEnabled")
        )
        self.acCaseSensitivityCheckBox.setChecked(
            Preferences.getEditor("AutoCompletionCaseSensitivity")
        )
        self.acReversedCheckBox.setChecked(
            Preferences.getEditor("AutoCompletionReversedList")
        )
        self.acReplaceWordCheckBox.setChecked(
            Preferences.getEditor("AutoCompletionReplaceWord")
        )
        self.acThresholdSlider.setValue(
            Preferences.getEditor("AutoCompletionThreshold")
        )
        self.acScintillaCheckBox.setChecked(
            Preferences.getEditor("AutoCompletionScintillaOnFail")
        )
        self.acTimeoutSpinBox.setValue(Preferences.getEditor("AutoCompletionTimeout"))
        self.acCacheGroup.setChecked(
            Preferences.getEditor("AutoCompletionCacheEnabled")
        )
        self.acCacheSizeSpinBox.setValue(
            Preferences.getEditor("AutoCompletionCacheSize")
        )
        self.acCacheTimeSpinBox.setValue(
            Preferences.getEditor("AutoCompletionCacheTime")
        )
        self.acWatchdogDoubleSpinBox.setValue(
            Preferences.getEditor("AutoCompletionWatchdogTime") / 1000.0
        )
        self.acLinesSlider.setValue(Preferences.getEditor("AutoCompletionMaxLines"))
        self.acCharSlider.setValue(Preferences.getEditor("AutoCompletionMaxChars"))

    def setMode(self, displayMode):
        """
        Public method to perform mode dependent setups.

        @param displayMode mode of the configuration dialog
        @type ConfigurationMode
        """
        from ..ConfigurationDialog import ConfigurationMode

        if displayMode in (ConfigurationMode.SHELLMODE,):
            self.pluginGroupBox.hide()
            self.acCacheGroup.hide()

    def save(self):
        """
        Public slot to save the Editor Autocompletion configuration.
        """
        Preferences.setEditor(
            "AutoCompletionEnabled", self.acEnabledGroupBox.isChecked()
        )
        Preferences.setEditor(
            "AutoCompletionCaseSensitivity", self.acCaseSensitivityCheckBox.isChecked()
        )

        Preferences.setEditor(
            "AutoCompletionReversedList", self.acReversedCheckBox.isChecked()
        )
        Preferences.setEditor(
            "AutoCompletionReplaceWord", self.acReplaceWordCheckBox.isChecked()
        )
        Preferences.setEditor("AutoCompletionThreshold", self.acThresholdSlider.value())
        Preferences.setEditor(
            "AutoCompletionScintillaOnFail", self.acScintillaCheckBox.isChecked()
        )
        Preferences.setEditor("AutoCompletionTimeout", self.acTimeoutSpinBox.value())
        Preferences.setEditor(
            "AutoCompletionCacheEnabled", self.acCacheGroup.isChecked()
        )
        Preferences.setEditor(
            "AutoCompletionCacheSize", self.acCacheSizeSpinBox.value()
        )
        Preferences.setEditor(
            "AutoCompletionCacheTime", self.acCacheTimeSpinBox.value()
        )
        Preferences.setEditor(
            "AutoCompletionWatchdogTime", self.acWatchdogDoubleSpinBox.value() * 1000
        )
        Preferences.setEditor("AutoCompletionMaxLines", self.acLinesSlider.value())
        Preferences.setEditor("AutoCompletionMaxChars", self.acCharSlider.value())


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorAutocompletionPage()
    return page
