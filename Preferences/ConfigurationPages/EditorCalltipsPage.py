# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor Calltips configuration page.
"""

from PyQt6.Qsci import QsciScintilla

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorCalltipsPage import Ui_EditorCalltipsPage


class EditorCalltipsPage(ConfigurationPageBase, Ui_EditorCalltipsPage):
    """
    Class implementing the Editor Calltips configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorCalltipsPage")

        self.positionComboBox.addItem(
            self.tr("Below Text"), QsciScintilla.CallTipsPosition.CallTipsBelowText
        )
        self.positionComboBox.addItem(
            self.tr("Above Text"), QsciScintilla.CallTipsPosition.CallTipsAboveText
        )

        # set initial values
        self.ctEnabledCheckBox.setChecked(Preferences.getEditor("CallTipsEnabled"))

        self.ctVisibleSlider.setValue(Preferences.getEditor("CallTipsVisible"))

        self.initColour(
            "CallTipsBackground",
            self.calltipsBackgroundButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "CallTipsForeground",
            self.calltipsForegroundButton,
            Preferences.getEditorColour,
        )
        self.initColour(
            "CallTipsHighlight",
            self.calltipsHighlightButton,
            Preferences.getEditorColour,
        )

        self.ctScintillaCheckBox.setChecked(
            Preferences.getEditor("CallTipsScintillaOnFail")
        )

        self.positionComboBox.setCurrentIndex(
            self.positionComboBox.findData(Preferences.getEditor("CallTipsPosition"))
        )

    def setMode(self, displayMode):
        """
        Public method to perform mode dependent setups.

        @param displayMode mode of the configuration dialog
        @type ConfigurationMode
        """
        from ..ConfigurationDialog import ConfigurationMode

        if displayMode in (ConfigurationMode.SHELLMODE,):
            self.pluginsBox.hide()

    def save(self):
        """
        Public slot to save the EditorCalltips configuration.
        """
        Preferences.setEditor("CallTipsEnabled", self.ctEnabledCheckBox.isChecked())

        Preferences.setEditor("CallTipsVisible", self.ctVisibleSlider.value())

        self.saveColours(Preferences.setEditorColour)

        Preferences.setEditor(
            "CallTipsScintillaOnFail", self.ctScintillaCheckBox.isChecked()
        )

        Preferences.setEditor(
            "CallTipsPosition",
            self.positionComboBox.itemData(self.positionComboBox.currentIndex()),
        )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorCalltipsPage()
    return page
