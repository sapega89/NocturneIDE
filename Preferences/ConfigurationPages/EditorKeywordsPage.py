# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the editor highlighter keywords configuration page.
"""

from PyQt6.QtCore import pyqtSlot

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.QScintilla import Lexers
from eric7.QScintilla.Lexers.LexerContainer import LexerContainer

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorKeywordsPage import Ui_EditorKeywordsPage


class EditorKeywordsPage(ConfigurationPageBase, Ui_EditorKeywordsPage):
    """
    Class implementing the editor highlighter keywords configuration page.
    """

    MaxKeywordSets = 8  # max. 8 sets are allowed

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorKeywordsPage")

        # set initial values
        self.__keywords = {
            "": {
                "Sets": [""] * (self.MaxKeywordSets + 1),
                "Descriptions": [""] * (self.MaxKeywordSets + 1),
                "MaxSets": 0,
            }
        }

        languages = sorted([""] + list(Lexers.getSupportedLanguages()))
        self.__populateLanguages(languages)

    def setMode(self, displayMode):
        """
        Public method to perform mode dependent setups.

        @param displayMode mode of the configuration dialog
        @type ConfigurationMode
        """
        from ..ConfigurationDialog import ConfigurationMode

        if displayMode in (ConfigurationMode.SHELLMODE,):
            self.__populateLanguages(["Python3"])

    def save(self):
        """
        Public slot to save the editor highlighter keywords configuration.
        """
        lang = self.languageCombo.currentText()
        kwSet = self.setSpinBox.value()
        self.__keywords[lang]["Sets"][kwSet] = self.keywordsEdit.toPlainText()

        for lang, keywords in self.__keywords.items():
            Preferences.setEditorKeywords(lang, keywords["Sets"])

    def __populateLanguages(self, languages):
        """
        Private method to populate the language selection box.

        @param languages list of languages to include in the language selector
        @type list of str
        """
        self.languageCombo.clear()
        for lang in languages:
            if lang:
                lex = Lexers.getLexer(lang)
                if isinstance(lex, LexerContainer):
                    continue
                keywords = Preferences.getEditorKeywords(lang)[:]
                if keywords:
                    # set empty entries to default values
                    for kwSet in range(1, self.MaxKeywordSets + 1):
                        if not keywords[kwSet]:
                            kw = lex.defaultKeywords(kwSet)
                            if kw is None:
                                kw = ""
                            keywords[kwSet] = kw
                else:
                    keywords = [""]
                    descriptions = [""]
                    for kwSet in range(1, self.MaxKeywordSets + 1):
                        kw = lex.keywords(kwSet)
                        if kw is None:
                            kw = ""
                        keywords.append(kw)
                descriptions = [""]
                for kwSet in range(1, self.MaxKeywordSets + 1):
                    desc = lex.keywordsDescription(kwSet)
                    descriptions.append(desc)
                defaults = [""]
                for kwSet in range(1, self.MaxKeywordSets + 1):
                    dkw = lex.defaultKeywords(kwSet)
                    if dkw is None:
                        dkw = ""
                    defaults.append(dkw)
                self.__keywords[lang] = {
                    "Sets": keywords,
                    "Descriptions": descriptions,
                    "DefaultSets": defaults,
                    "MaxSets": lex.maximumKeywordSet(),
                }
            self.languageCombo.addItem(Lexers.getLanguageIcon(lang, False), lang)

        self.currentLanguage = ""
        self.currentSet = 1
        self.on_languageCombo_activated(0)

    @pyqtSlot(int)
    def on_languageCombo_activated(self, index):
        """
        Private slot to fill the keywords edit.

        @param index index of the selected entry
        @type int
        """
        language = self.languageCombo.itemText(index)

        self.defaultButton.setEnabled(bool(language))
        self.allDefaultButton.setEnabled(bool(language))

        if self.currentLanguage == language:
            return

        if self.setSpinBox.value() == 1:
            self.on_setSpinBox_valueChanged(1)
        if self.__keywords[language]["MaxSets"]:
            first = 1
            last = self.__keywords[language]["MaxSets"]
        else:
            first, last = self.MaxKeywordSets + 1, 0
            for kwSet in range(1, self.MaxKeywordSets + 1):
                if self.__keywords[language]["Descriptions"][kwSet] != "":
                    first = min(first, kwSet)
                    last = max(last, kwSet)
        self.setSpinBox.setEnabled(language != "" and first <= self.MaxKeywordSets)
        self.keywordsEdit.setEnabled(language != "" and first <= self.MaxKeywordSets)
        if first <= self.MaxKeywordSets:
            self.setSpinBox.setMinimum(first)
            self.setSpinBox.setMaximum(last)
            self.setSpinBox.setValue(first)
        else:
            self.setSpinBox.setMinimum(0)
            self.setSpinBox.setMaximum(0)
            self.setSpinBox.setValue(0)

    @pyqtSlot(int)
    def on_setSpinBox_valueChanged(self, kwSet):
        """
        Private slot to fill the keywords edit.

        @param kwSet number of the selected keyword set
        @type int
        """
        language = self.languageCombo.currentText()
        if self.currentLanguage == language and self.currentSet == kwSet:
            return

        self.__keywords[self.currentLanguage]["Sets"][
            self.currentSet
        ] = self.keywordsEdit.toPlainText()

        self.currentLanguage = language
        self.currentSet = kwSet
        self.setDescriptionLabel.setText(
            "<b>{0}</b>".format(self.__keywords[language]["Descriptions"][kwSet])
        )
        self.keywordsEdit.setPlainText(self.__keywords[language]["Sets"][kwSet])

    @pyqtSlot()
    def on_defaultButton_clicked(self):
        """
        Private slot to set the current keyword set to default values.
        """
        ok = (
            EricMessageBox.yesNo(
                self,
                self.tr("Reset to Default"),
                self.tr(
                    "Shall the current keyword set really be reset to"
                    " default values?"
                ),
            )
            if bool(self.keywordsEdit.toPlainText())
            else True
        )
        if ok:
            language = self.languageCombo.currentText()
            kwSet = self.setSpinBox.value()
            self.__keywords[language]["Sets"][kwSet] = self.__keywords[language][
                "DefaultSets"
            ][kwSet]
            self.keywordsEdit.setPlainText(self.__keywords[language]["Sets"][kwSet])

    @pyqtSlot()
    def on_allDefaultButton_clicked(self):
        """
        Private slot to set all keyword sets of the current language to default
        values.
        """
        ok = EricMessageBox.yesNo(
            self,
            self.tr("Reset All to Default"),
            self.tr(
                "Shall all keyword sets of the current language really be"
                " reset to default values?"
            ),
        )
        if ok:
            language = self.languageCombo.currentText()
            kwSet = self.setSpinBox.value()
            self.__keywords[language]["Sets"] = self.__keywords[language][
                "DefaultSets"
            ][:]
            self.keywordsEdit.setPlainText(self.__keywords[language]["Sets"][kwSet])


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationWidget
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorKeywordsPage()
    return page
