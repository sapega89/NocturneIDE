# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to set the tab and indentation width override for
a language.
"""

from pygments.lexers import get_all_lexers
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_EditorLanguageTabIndentOverrideDialog import (
    Ui_EditorLanguageTabIndentOverrideDialog,
)


class EditorLanguageTabIndentOverrideDialog(
    QDialog, Ui_EditorLanguageTabIndentOverrideDialog
):
    """
    Class implementing a dialog to set the tab and indentation width override
    for a language.
    """

    PygmentsMarker = "Pygments|"

    def __init__(
        self, *, editMode=False, languages=None, tabWidth=0, indentWidth=0, parent=None
    ):
        """
        Constructor

        @keyparam editMode flag indicating the edit mode (Note: in edit mode
            the language is fixed)
        @type bool
        @keyparam languages list of existing languages (if in add mode) or
            a list containing the language to be edited
        @type list of str
        @keyparam tabWidth tab width to be set
        @type int
        @keyparam indentWidth indentation width to be set
        @type int
        @keyparam parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__extras = ["-----------", self.tr("Alternative")]

        if editMode:
            self.languageComboBox.addItems(languages)
        else:
            self.__populateLanguages(languages)
        self.tabWidthSpinBox.setValue(tabWidth)
        self.indentWidthSpinBox.setValue(indentWidth)

    def __populateLanguages(self, filterLanguages):
        """
        Private method to populate the language combo boxes.

        @param filterLanguages list of languages to be filtered out
        @type list of str
        """
        from eric7.QScintilla import Lexers

        languages = list(Lexers.getSupportedLanguages())
        for lang in filterLanguages:
            if lang in languages:
                languages.remove(lang)
        self.languageComboBox.addItems([""] + sorted(languages) + self.__extras)

        pygmentsLanguages = [lex[0] for lex in get_all_lexers()]
        for lang in filterLanguages:
            if lang.startswith(self.PygmentsMarker):
                lang = lang.replace(self.PygmentsMarker, "")
                if lang in pygmentsLanguages:
                    pygmentsLanguages.remove(lang)
        self.pygmentsLexerCombo.addItems([""] + sorted(pygmentsLanguages))

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the language, the tab width and the
            indentation width
        @rtype tuple of (str, int, int)
        """
        language = self.languageComboBox.currentText()
        if language in self.__extras:
            pygmentsLanguage = self.pygmentsLexerCombo.currentText()
            language = self.PygmentsMarker + pygmentsLanguage
        return (
            language,
            self.tabWidthSpinBox.value(),
            self.indentWidthSpinBox.value(),
        )

    def __updateOkButton(self):
        """
        Private method to set the enabled status of the OK button.
        """
        lang = self.languageComboBox.currentText()
        if lang in self.__extras:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                bool(self.pygmentsLexerCombo.currentText())
            )
        else:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                bool(lang)
            )

    @pyqtSlot(int)
    def on_languageComboBox_currentIndexChanged(self, index):
        """
        Private slot to handle the selection of a language.

        @param index index of the current item
        @type int
        """
        lang = self.languageComboBox.itemText(index)
        if lang in self.__extras:
            self.pygmentsLexerCombo.setEnabled(True)
            self.pygmentsLabel.setEnabled(True)
        else:
            self.pygmentsLexerCombo.setEnabled(False)
            self.pygmentsLabel.setEnabled(False)

        self.__updateOkButton()

    @pyqtSlot(int)
    def on_pygmentsLexerCombo_currentIndexChanged(self, index):
        """
        Private slot to handle the selection of a language.

        @param index index of the current item
        @type int
        """
        self.__updateOkButton()
