# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor Spellchecking configuration page.
"""

from eric7 import Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.QScintilla.SpellChecker import SpellChecker

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorSpellCheckingPage import Ui_EditorSpellCheckingPage


class EditorSpellCheckingPage(ConfigurationPageBase, Ui_EditorSpellCheckingPage):
    """
    Class implementing the Editor Spellchecking configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorSpellCheckingPage")

        self.pwlPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.pwlPicker.setFilters(self.tr("Dictionary File (*.dic);;All Files (*)"))

        self.pelPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.pelPicker.setFilters(self.tr("Dictionary File (*.dic);;All Files (*)"))

        languages = sorted(SpellChecker.getAvailableLanguages())
        self.defaultLanguageCombo.addItems(languages)
        if languages:
            self.errorLabel.hide()
        else:
            self.spellingFrame.setEnabled(False)

        # set initial values
        self.checkingEnabledCheckBox.setChecked(
            Preferences.getEditor("SpellCheckingEnabled")
        )

        self.defaultLanguageCombo.setCurrentIndex(
            self.defaultLanguageCombo.findText(
                Preferences.getEditor("SpellCheckingDefaultLanguage")
            )
        )

        self.stringsOnlyCheckBox.setChecked(
            Preferences.getEditor("SpellCheckStringsOnly")
        )
        self.fullCheckUnknownCheckBox.setChecked(
            Preferences.getEditor("FullSpellCheckUnknown")
        )
        self.minimumWordSizeSlider.setValue(
            Preferences.getEditor("SpellCheckingMinWordSize")
        )
        self.spellCheckTextFilesLineEdit.setText(
            " ".join(Preferences.getEditor("FullSpellCheckExtensions"))
        )

        self.initColour(
            "SpellingMarkers",
            self.spellingMarkerButton,
            Preferences.getEditorColour,
            hasAlpha=True,
        )

        self.pwlPicker.setText(Preferences.getEditor("SpellCheckingPersonalWordList"))
        self.pelPicker.setText(
            Preferences.getEditor("SpellCheckingPersonalExcludeList")
        )

        if self.spellingFrame.isEnabled():
            self.enabledCheckBox.setChecked(
                Preferences.getEditor("AutoSpellCheckingEnabled")
            )
        else:
            self.enabledCheckBox.setChecked(False)  # not available
        self.chunkSizeSpinBox.setValue(Preferences.getEditor("AutoSpellCheckChunkSize"))

    def save(self):
        """
        Public slot to save the Editor Search configuration.
        """
        Preferences.setEditor(
            "SpellCheckingEnabled", self.checkingEnabledCheckBox.isChecked()
        )

        Preferences.setEditor(
            "SpellCheckingDefaultLanguage", self.defaultLanguageCombo.currentText()
        )

        Preferences.setEditor(
            "SpellCheckStringsOnly", self.stringsOnlyCheckBox.isChecked()
        )
        Preferences.setEditor(
            "FullSpellCheckUnknown", self.fullCheckUnknownCheckBox.isChecked()
        )
        Preferences.setEditor(
            "SpellCheckingMinWordSize", self.minimumWordSizeSlider.value()
        )
        Preferences.setEditor(
            "FullSpellCheckExtensions",
            [ext.strip() for ext in self.spellCheckTextFilesLineEdit.text().split()],
        )

        self.saveColours(Preferences.setEditorColour)

        Preferences.setEditor("SpellCheckingPersonalWordList", self.pwlPicker.text())
        Preferences.setEditor("SpellCheckingPersonalExcludeList", self.pelPicker.text())

        Preferences.setEditor(
            "AutoSpellCheckingEnabled", self.enabledCheckBox.isChecked()
        )
        Preferences.setEditor("AutoSpellCheckChunkSize", self.chunkSizeSpinBox.value())


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorSpellCheckingPage()
    return page
