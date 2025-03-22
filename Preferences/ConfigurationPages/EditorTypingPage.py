# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor Typing configuration page.
"""

from PyQt6.QtCore import pyqtSlot

from eric7 import Preferences
from eric7.QScintilla.TypingCompleters import CompleterRegistry

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorTypingPage import Ui_EditorTypingPage


class EditorTypingPage(ConfigurationPageBase, Ui_EditorTypingPage):
    """
    Class implementing the Editor Typing configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorTypingPage")

        self.__pageIds = {
            " ": self.stackedWidget.indexOf(self.emptyPage),
            "Python": self.stackedWidget.indexOf(self.pythonPage),
            "Ruby": self.stackedWidget.indexOf(self.rubyPage),
            "TOML": self.stackedWidget.indexOf(self.tomlPage),
            "YAML": self.stackedWidget.indexOf(self.yamlPage),
        }

        self.__extensionPages = {}
        for language in CompleterRegistry:
            page = CompleterRegistry[language].createConfigPage()
            if page is not None:
                language = language.replace("Pygments|", "")  # more readable
                self.__extensionPages[language] = page
                self.__pageIds[language] = self.stackedWidget.addWidget(page)

        for language in sorted(self.__pageIds):
            self.languageCombo.addItem(language, self.__pageIds[language])

        # set initial values
        # Python
        self.pythonGroup.setChecked(
            Preferences.getEditorTyping("Python/EnabledTypingAids")
        )
        self.pythonInsertClosingBraceCheckBox.setChecked(
            Preferences.getEditorTyping("Python/InsertClosingBrace")
        )
        self.pythonSkipBraceCheckBox.setChecked(
            Preferences.getEditorTyping("Python/SkipBrace")
        )
        self.pythonIndentBraceCheckBox.setChecked(
            Preferences.getEditorTyping("Python/IndentBrace")
        )
        self.pythonInsertQuoteCheckBox.setChecked(
            Preferences.getEditorTyping("Python/InsertQuote")
        )
        self.pythonDedentElseCheckBox.setChecked(
            Preferences.getEditorTyping("Python/DedentElse")
        )
        self.pythonDedentExceptCheckBox.setChecked(
            Preferences.getEditorTyping("Python/DedentExcept")
        )
        self.pythonInsertImportCheckBox.setChecked(
            Preferences.getEditorTyping("Python/InsertImport")
        )
        self.pythonImportBraceTypeCheckBox.setChecked(
            Preferences.getEditorTyping("Python/ImportBraceType")
        )
        self.pythonInsertSelfCheckBox.setChecked(
            Preferences.getEditorTyping("Python/InsertSelf")
        )
        self.pythonInsertBlankCheckBox.setChecked(
            Preferences.getEditorTyping("Python/InsertBlank")
        )
        self.pythonColonDetectionCheckBox.setChecked(
            Preferences.getEditorTyping("Python/ColonDetection")
        )
        self.pythonDedentDefCheckBox.setChecked(
            Preferences.getEditorTyping("Python/DedentDef")
        )

        # Ruby
        self.rubyGroup.setChecked(Preferences.getEditorTyping("Ruby/EnabledTypingAids"))
        self.rubyInsertClosingBraceCheckBox.setChecked(
            Preferences.getEditorTyping("Ruby/InsertClosingBrace")
        )
        self.rubySkipBraceCheckBox.setChecked(
            Preferences.getEditorTyping("Ruby/SkipBrace")
        )
        self.rubyIndentBraceCheckBox.setChecked(
            Preferences.getEditorTyping("Ruby/IndentBrace")
        )
        self.rubyInsertQuoteCheckBox.setChecked(
            Preferences.getEditorTyping("Ruby/InsertQuote")
        )
        self.rubyInsertBlankCheckBox.setChecked(
            Preferences.getEditorTyping("Ruby/InsertBlank")
        )
        self.rubyInsertHereDocCheckBox.setChecked(
            Preferences.getEditorTyping("Ruby/InsertHereDoc")
        )
        self.rubyInsertInlineDocCheckBox.setChecked(
            Preferences.getEditorTyping("Ruby/InsertInlineDoc")
        )

        # TOML
        self.tomlGroup.setChecked(Preferences.getEditorTyping("Toml/EnabledTypingAids"))
        self.tomlInsertClosingBraceCheckBox.setChecked(
            Preferences.getEditorTyping("Toml/InsertClosingBrace")
        )
        self.tomlSkipBraceCheckBox.setChecked(
            Preferences.getEditorTyping("Toml/SkipBrace")
        )
        self.tomlInsertQuoteCheckBox.setChecked(
            Preferences.getEditorTyping("Toml/InsertQuote")
        )
        self.tomlAutoIndentationCheckBox.setChecked(
            Preferences.getEditorTyping("Toml/AutoIndentation")
        )
        self.tomlColonDetectionCheckBox.setChecked(
            Preferences.getEditorTyping("Toml/ColonDetection")
        )
        self.tomlInsertBlankEqualCheckBox.setChecked(
            Preferences.getEditorTyping("Toml/InsertBlankEqual")
        )
        self.tomlInsertBlankColonCheckBox.setChecked(
            Preferences.getEditorTyping("Toml/InsertBlankColon")
        )
        self.tomlInsertBlankCommaCheckBox.setChecked(
            Preferences.getEditorTyping("Toml/InsertBlankComma")
        )

        # YAML
        self.yamlGroup.setChecked(Preferences.getEditorTyping("Yaml/EnabledTypingAids"))
        self.yamlInsertClosingBraceCheckBox.setChecked(
            Preferences.getEditorTyping("Yaml/InsertClosingBrace")
        )
        self.yamlSkipBraceCheckBox.setChecked(
            Preferences.getEditorTyping("Yaml/SkipBrace")
        )
        self.yamlInsertQuoteCheckBox.setChecked(
            Preferences.getEditorTyping("Yaml/InsertQuote")
        )
        self.yamlAutoIndentationCheckBox.setChecked(
            Preferences.getEditorTyping("Yaml/AutoIndentation")
        )
        self.yamlColonDetectionCheckBox.setChecked(
            Preferences.getEditorTyping("Yaml/ColonDetection")
        )
        self.yamlInsertBlankDashCheckBox.setChecked(
            Preferences.getEditorTyping("Yaml/InsertBlankDash")
        )
        self.yamlInsertBlankColonCheckBox.setChecked(
            Preferences.getEditorTyping("Yaml/InsertBlankColon")
        )
        self.yamlInsertBlankQuestionCheckBox.setChecked(
            Preferences.getEditorTyping("Yaml/InsertBlankQuestion")
        )
        self.yamlInsertBlankCommaCheckBox.setChecked(
            Preferences.getEditorTyping("Yaml/InsertBlankComma")
        )

        self.on_languageCombo_activated(0)

    def save(self):
        """
        Public slot to save the Editor Typing configuration.
        """
        # Python
        Preferences.setEditorTyping(
            "Python/EnabledTypingAids", self.pythonGroup.isChecked()
        )
        Preferences.setEditorTyping(
            "Python/InsertClosingBrace",
            self.pythonInsertClosingBraceCheckBox.isChecked(),
        )
        Preferences.setEditorTyping(
            "Python/SkipBrace", self.pythonSkipBraceCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Python/IndentBrace", self.pythonIndentBraceCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Python/InsertQuote", self.pythonInsertQuoteCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Python/DedentElse", self.pythonDedentElseCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Python/DedentExcept", self.pythonDedentExceptCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Python/InsertImport", self.pythonInsertImportCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Python/ImportBraceType", self.pythonImportBraceTypeCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Python/InsertSelf", self.pythonInsertSelfCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Python/InsertBlank", self.pythonInsertBlankCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Python/ColonDetection", self.pythonColonDetectionCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Python/DedentDef", self.pythonDedentDefCheckBox.isChecked()
        )

        # Ruby
        Preferences.setEditorTyping(
            "Ruby/EnabledTypingAids", self.rubyGroup.isChecked()
        )
        Preferences.setEditorTyping(
            "Ruby/InsertClosingBrace", self.rubyInsertClosingBraceCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Ruby/SkipBrace", self.rubySkipBraceCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Ruby/IndentBrace", self.rubyIndentBraceCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Ruby/InsertQuote", self.rubyInsertQuoteCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Ruby/InsertBlank", self.rubyInsertBlankCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Ruby/InsertHereDoc", self.rubyInsertHereDocCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Ruby/InsertInlineDoc", self.rubyInsertInlineDocCheckBox.isChecked()
        )

        # TOML
        Preferences.setEditorTyping(
            "Toml/EnabledTypingAids", self.tomlGroup.isChecked()
        )
        Preferences.setEditorTyping(
            "Toml/InsertClosingBrace", self.tomlInsertClosingBraceCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Toml/SkipBrace", self.tomlSkipBraceCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Toml/InsertQuote", self.tomlInsertQuoteCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Toml/AutoIndentation", self.tomlAutoIndentationCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Toml/ColonDetection", self.tomlColonDetectionCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Toml/InsertBlankEqual", self.tomlInsertBlankEqualCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Toml/InsertBlankColon", self.tomlInsertBlankColonCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Toml/InsertBlankComma", self.tomlInsertBlankCommaCheckBox.isChecked()
        )

        # YAML
        Preferences.setEditorTyping(
            "Yaml/EnabledTypingAids", self.yamlGroup.isChecked()
        )
        Preferences.setEditorTyping(
            "Yaml/InsertClosingBrace", self.yamlInsertClosingBraceCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Yaml/SkipBrace", self.yamlSkipBraceCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Yaml/InsertQuote", self.yamlInsertQuoteCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Yaml/AutoIndentation", self.yamlAutoIndentationCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Yaml/ColonDetection", self.yamlColonDetectionCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Yaml/InsertBlankDash", self.yamlInsertBlankDashCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Yaml/InsertBlankColon", self.yamlInsertBlankColonCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Yaml/InsertBlankQuestion", self.yamlInsertBlankQuestionCheckBox.isChecked()
        )
        Preferences.setEditorTyping(
            "Yaml/InsertBlankComma", self.yamlInsertBlankCommaCheckBox.isChecked()
        )

        for page in self.__extensionPages.values():
            page.save()

    @pyqtSlot(int)
    def on_languageCombo_activated(self, index):
        """
        Private slot to select the page related to the selected language.

        @param index index of the selected entry
        @type int
        """
        language = self.languageCombo.itemText(index)
        try:
            index = self.__pageIds[language]
        except KeyError:
            index = self.__pageIds[" "]
        self.stackedWidget.setCurrentIndex(index)


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorTypingPage()
    return page
