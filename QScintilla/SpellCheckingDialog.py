# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the spell checking dialog.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7 import EricUtilities

from .Ui_SpellCheckingDialog import Ui_SpellCheckingDialog


class SpellCheckingDialog(QDialog, Ui_SpellCheckingDialog):
    """
    Class implementing the spell checking dialog.
    """

    def __init__(self, spellChecker, startPos, endPos, parent=None):
        """
        Constructor

        @param spellChecker reference to the spell checker
        @type SpellChecker
        @param startPos position to start spell checking
        @type int
        @param endPos end position for spell checking
        @type int
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__spell = spellChecker
        self.languageLabel.setText("<b>{0}</b>".format(self.__spell.getLanguage()))
        if not self.__spell.initCheck(startPos, endPos):
            self.__enableButtons(False)
        else:
            self.__advance()

    def __enableButtons(self, enable):
        """
        Private method to set the buttons enabled state.

        @param enable enable state
        @type bool
        """
        self.addButton.setEnabled(enable)
        self.ignoreButton.setEnabled(enable)
        self.ignoreAllButton.setEnabled(enable)
        self.replaceButton.setEnabled(enable)
        self.replaceAllButton.setEnabled(enable)

    def __advance(self):
        """
        Private method to advance to the next error.
        """
        try:
            next(self.__spell)
        except StopIteration:
            self.__enableButtons(False)
            self.contextLabel.setText("")
            self.changeEdit.setText("")
            self.suggestionsList.clear()
            return

        self.__enableButtons(True)
        self.word, self.wordStart, self.wordEnd = self.__spell.getError()
        lcontext, rcontext = self.__spell.getContext(self.wordStart, self.wordEnd)
        self.changeEdit.setText(self.word)
        self.contextLabel.setText(
            '{0}<font color="#FF0000">{1}</font>{2}'.format(
                EricUtilities.html_encode(lcontext),
                self.word,
                EricUtilities.html_encode(rcontext),
            )
        )
        suggestions = self.__spell.getSuggestions(self.word)
        self.suggestionsList.clear()
        self.suggestionsList.addItems(suggestions)

    @pyqtSlot(str)
    def on_changeEdit_textChanged(self, text):
        """
        Private method to handle a change of the replacement text.

        @param text contents of the line edit
        @type str
        """
        self.replaceButton.setEnabled(text != "")
        self.replaceAllButton.setEnabled(text != "")

    @pyqtSlot(str)
    def on_suggestionsList_currentTextChanged(self, currentText):
        """
        Private method to handle the selection of a suggestion.

        @param currentText the currently selected text
        @type str
        """
        if currentText:
            self.changeEdit.setText(currentText)

    @pyqtSlot()
    def on_ignoreButton_clicked(self):
        """
        Private slot to ignore the found error.
        """
        self.__advance()

    @pyqtSlot()
    def on_ignoreAllButton_clicked(self):
        """
        Private slot to always ignore the found error.
        """
        self.__spell.ignoreAlways()
        self.__advance()

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add the current word to the personal word list.
        """
        self.__spell.add()
        self.__advance()

    @pyqtSlot()
    def on_replaceButton_clicked(self):
        """
        Private slot to replace the current word with the given replacement.
        """
        self.__spell.replace(self.changeEdit.text())
        self.__advance()

    @pyqtSlot()
    def on_replaceAllButton_clicked(self):
        """
        Private slot to replace the current word with the given replacement.
        """
        self.__spell.replaceAlways(self.changeEdit.text())
        self.__advance()
