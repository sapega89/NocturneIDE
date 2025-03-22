# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing QTextEdit and QPlainTextEdit widgets with embedded spell
checking.
"""

import contextlib

try:
    import enchant
    import enchant.tokenize

    from enchant.errors import DictNotFoundError, TokenizerNotFoundError
    from enchant.utils import trim_suggestions

    ENCHANT_AVAILABLE = True
except ImportError:
    ENCHANT_AVAILABLE = False

from PyQt6.QtCore import QCoreApplication, QPoint, Qt, pyqtSlot
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QSyntaxHighlighter,
    QTextBlockUserData,
    QTextCharFormat,
    QTextCursor,
)
from PyQt6.QtWidgets import QMenu, QPlainTextEdit, QTextEdit

if ENCHANT_AVAILABLE:

    class SpellCheckMixin:
        """
        Class implementing the spell-check mixin for the widget classes.
        """

        # don't show more than this to keep the menu manageable
        MaxSuggestions = 20

        # default language to be used when no other is set
        DefaultLanguage = None

        # default user lists
        DefaultUserWordList = None
        DefaultUserExceptionList = None

        def __init__(self):
            """
            Constructor
            """
            self.__highlighter = EnchantHighlighter(self.document())
            try:
                # Start with a default dictionary based on the current locale
                # or the configured default language.
                spellDict = enchant.DictWithPWL(
                    SpellCheckMixin.DefaultLanguage,
                    SpellCheckMixin.DefaultUserWordList,
                    SpellCheckMixin.DefaultUserExceptionList,
                )
            except DictNotFoundError:
                try:
                    # Use English dictionary if no locale dictionary is
                    # available or the default one could not be found.
                    spellDict = enchant.DictWithPWL(
                        "en",
                        SpellCheckMixin.DefaultUserWordList,
                        SpellCheckMixin.DefaultUserExceptionList,
                    )
                except DictNotFoundError:
                    # Still no dictionary could be found. Forget about spell
                    # checking.
                    spellDict = None

            self.__highlighter.setDict(spellDict)

        @pyqtSlot(QPoint)
        def _showContextMenu(self, pos):
            """
            Protected slot to show a context menu.

            @param pos position for the context menu
            @type QPoint
            """
            menu = self.__createSpellcheckContextMenu(pos)
            menu.exec(self.mapToGlobal(pos))

        def __createSpellcheckContextMenu(self, pos):
            """
            Private method to create the spell-check context menu.

            @param pos position of the mouse pointer
            @type QPoint
            @return context menu with additional spell-check entries
            @rtype QMenu
            """
            menu = self.createStandardContextMenu(pos)

            # Add a submenu for setting the spell-check language and
            # document format.
            menu.addSeparator()
            self.__addRemoveEntry(self.__cursorForPosition(pos), menu)
            menu.addMenu(self.__createLanguagesMenu(menu))
            menu.addMenu(self.__createFormatsMenu(menu))

            # Try to retrieve a menu of corrections for the right-clicked word
            spellMenu = self.__createCorrectionsMenu(
                self.__cursorForMisspelling(pos), menu
            )

            if spellMenu:
                menu.insertSeparator(menu.actions()[0])
                menu.insertMenu(menu.actions()[0], spellMenu)

            return menu

        def __createCorrectionsMenu(self, cursor, parent=None):
            """
            Private method to create a menu for corrections of the selected
            word.

            @param cursor reference to the text cursor
            @type QTextCursor
            @param parent reference to the parent widget (defaults to None)
            @type QWidget (optional)
            @return menu with corrections
            @rtype QMenu
            """
            if cursor is None:
                return None

            text = cursor.selectedText()
            suggestions = trim_suggestions(
                text,
                self.__highlighter.dict().suggest(text),
                SpellCheckMixin.MaxSuggestions,
            )

            spellMenu = QMenu(
                QCoreApplication.translate("SpellCheckMixin", "Spelling Suggestions"),
                parent,
            )
            for word in suggestions:
                act = spellMenu.addAction(word)
                act.setData((cursor, word))

            if suggestions:
                spellMenu.addSeparator()

            # add management entry
            act = spellMenu.addAction(
                QCoreApplication.translate("SpellCheckMixin", "Add to Dictionary")
            )
            act.setData((cursor, text, "add"))

            spellMenu.triggered.connect(self.__spellMenuTriggered)
            return spellMenu

        def __addRemoveEntry(self, cursor, menu):
            """
            Private method to create a menu entry to remove the word at the
            menu position.

            @param cursor reference to the text cursor for the misspelled word
            @type QTextCursor
            @param menu reference to the context menu
            @type QMenu
            """
            if cursor is None:
                return

            text = cursor.selectedText()
            menu.addAction(
                QCoreApplication.translate(
                    "SpellCheckMixin", "Remove '{0}' from Dictionary"
                ).format(text),
                lambda: self.__addToUserDict(text, "remove"),
            )

        def __createLanguagesMenu(self, parent=None):
            """
            Private method to create a menu for selecting the spell-check
            language.

            @param parent reference to the parent widget (defaults to None)
            @type QWidget (optional)
            @return menu with spell-check languages
            @rtype QMenu
            """
            curLanguage = self.__highlighter.dict().tag.lower()
            languageMenu = QMenu(
                QCoreApplication.translate("SpellCheckMixin", "Language"), parent
            )
            languageActions = QActionGroup(languageMenu)

            for language in sorted(enchant.list_languages()):
                act = QAction(language, languageActions)
                act.setCheckable(True)
                act.setChecked(language.lower() == curLanguage)
                act.setData(language)
                languageMenu.addAction(act)

            languageMenu.triggered.connect(self.__setLanguage)
            return languageMenu

        def __createFormatsMenu(self, parent=None):
            """
            Private method to create a menu for selecting the document format.

            @param parent reference to the parent widget (defaults to None)
            @type QWidget (optional)
            @return menu with document formats
            @rtype QMenu
            """
            formatMenu = QMenu(
                QCoreApplication.translate("SpellCheckMixin", "Format"), parent
            )
            formatActions = QActionGroup(formatMenu)

            curFormat = self.__highlighter.chunkers()
            for name, chunkers in (
                (QCoreApplication.translate("SpellCheckMixin", "Text"), []),
                (
                    QCoreApplication.translate("SpellCheckMixin", "HTML"),
                    [enchant.tokenize.HTMLChunker],
                ),
            ):
                act = QAction(name, formatActions)
                act.setCheckable(True)
                act.setChecked(chunkers == curFormat)
                act.setData(chunkers)
                formatMenu.addAction(act)

            formatMenu.triggered.connect(self.__setFormat)
            return formatMenu

        def __cursorForPosition(self, pos):
            """
            Private method to create a text cursor selecting the word at the
            given position.

            @param pos position of the misspelled word
            @type QPoint
            @return text cursor for the word
            @rtype QTextCursor
            """
            cursor = self.cursorForPosition(pos)
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)

            if cursor.hasSelection():
                return cursor
            else:
                return None

        def __cursorForMisspelling(self, pos):
            """
            Private method to create a text cursor selecting the misspelled
            word.

            @param pos position of the misspelled word
            @type QPoint
            @return text cursor for the misspelled word
            @rtype QTextCursor
            """
            cursor = self.cursorForPosition(pos)
            misspelledWords = getattr(cursor.block().userData(), "misspelled", [])

            # If the cursor is within a misspelling, select the word
            for start, end in misspelledWords:
                if start <= cursor.positionInBlock() <= end:
                    blockPosition = cursor.block().position()

                    cursor.setPosition(
                        blockPosition + start, QTextCursor.MoveMode.MoveAnchor
                    )
                    cursor.setPosition(
                        blockPosition + end, QTextCursor.MoveMode.KeepAnchor
                    )
                    break

            if cursor.hasSelection():
                return cursor
            else:
                return None

        def __correctWord(self, cursor, word):
            """
            Private method to replace some misspelled text.

            @param cursor reference to the text cursor for the misspelled word
            @type QTextCursor
            @param word replacement text
            @type str
            """
            cursor.beginEditBlock()
            cursor.removeSelectedText()
            cursor.insertText(word)
            cursor.endEditBlock()

        def __addToUserDict(self, word, command):
            """
            Private method to add a word to the user word or exclude list.

            @param word text to be added
            @type str
            @param command command indicating the user dictionary type
            @type str
            """
            if word:
                dictionary = self.__highlighter.dict()
                if command == "add":
                    dictionary.add(word)
                elif command == "remove":
                    dictionary.remove(word)

                self.__highlighter.rehighlight()

        @pyqtSlot(QAction)
        def __spellMenuTriggered(self, act):
            """
            Private slot to handle a selection of the spell menu.

            @param act reference to the selected action
            @type QAction
            """
            data = act.data()
            if len(data) == 2:
                # replace the misspelled word
                self.__correctWord(*data)

            elif len(data) == 3:
                # dictionary management action
                _, word, command = data
                self.__addToUserDict(word, command)

        @pyqtSlot(QAction)
        def __setLanguage(self, act):
            """
            Private slot to set the selected language.

            @param act reference to the selected action
            @type QAction
            """
            language = act.data()
            self.setLanguage(language)

        @pyqtSlot(QAction)
        def __setFormat(self, act):
            """
            Private slot to set the selected document format.

            @param act reference to the selected action
            @type QAction
            """
            chunkers = act.data()
            self.__highlighter.setChunkers(chunkers)

        def setFormat(self, formatName):
            """
            Public method to set the document format.

            @param formatName name of the document format
            @type str
            """
            self.__highlighter.setChunkers(
                [enchant.tokenize.HTMLChunker] if formatName == "html" else []
            )

        def dict(self):
            """
            Public method to get a reference to the dictionary in use.

            @return reference to the current dictionary
            @rtype enchant.Dict
            """
            return self.__highlighter.dict()

        def setDict(self, spellDict):
            """
            Public method to set the dictionary to be used.

            @param spellDict reference to the spell-check dictionary
            @type emchant.Dict
            """
            self.__highlighter.setDict(spellDict)

        @pyqtSlot(str)
        def setLanguage(self, language):
            """
            Public slot to set the spellchecker language.

            @param language language to be set
            @type str
            """
            epwl = self.dict().pwl
            pwl = epwl.provider.file if isinstance(epwl, enchant.Dict) else None

            epel = self.dict().pel
            pel = epel.provider.file if isinstance(epel, enchant.Dict) else None
            self.setLanguageWithPWL(language, pwl, pel)

        @pyqtSlot(str, str, str)
        def setLanguageWithPWL(self, language, pwl, pel):
            """
            Public slot to set the spellchecker language and associated user
            word lists.

            @param language language to be set
            @type str
            @param pwl file name of the personal word list
            @type str
            @param pel file name of the personal exclude list
            @type str
            """
            try:
                spellDict = enchant.DictWithPWL(language, pwl, pel)
            except DictNotFoundError:
                try:
                    # Use English dictionary if a dictionary for the given
                    # language is not available.
                    spellDict = enchant.DictWithPWL("en", pwl, pel)
                except DictNotFoundError:
                    # Still no dictionary could be found. Forget about spell
                    # checking.
                    spellDict = None
            self.__highlighter.setDict(spellDict)

        @classmethod
        def setDefaultLanguage(cls, language, pwl=None, pel=None):
            """
            Class method to set the default spell-check language.

            @param language language to be set as default
            @type str
            @param pwl file name of the personal word list
            @type str
            @param pel file name of the personal exclude list
            @type str
            """
            with contextlib.suppress(DictNotFoundError):
                cls.DefaultUserWordList = pwl
                cls.DefaultUserExceptionList = pel

                # set default language only, if a dictionary is available
                enchant.Dict(language)
                cls.DefaultLanguage = language

    class EnchantHighlighter(QSyntaxHighlighter):
        """
        Class implementing a QSyntaxHighlighter subclass that consults a
        pyEnchant dictionary to highlight misspelled words.
        """

        TokenFilters = (enchant.tokenize.EmailFilter, enchant.tokenize.URLFilter)

        # Define the spell-check style once and just assign it as necessary
        ErrorFormat = QTextCharFormat()
        ErrorFormat.setUnderlineColor(Qt.GlobalColor.red)
        ErrorFormat.setUnderlineStyle(
            QTextCharFormat.UnderlineStyle.SpellCheckUnderline
        )

        def __init__(self, *args, **kwargs):
            """
            Constructor

            @param *args list of arguments for the QSyntaxHighlighter
            @type list
            @keyparam **kwargs dictionary of keyword arguments for the
                QSyntaxHighlighter
            @type dict
            """
            QSyntaxHighlighter.__init__(self, *args, **kwargs)

            self.__spellDict = None
            self.__tokenizer = None
            self.__chunkers = []

        def chunkers(self):
            """
            Public method to get the chunkers in use.

            @return list of chunkers in use
            @rtype list
            """
            return self.__chunkers

        def setChunkers(self, chunkers):
            """
            Public method to set the chunkers to be used.

            @param chunkers chunkers to be used
            @type list
            """
            self.__chunkers = chunkers
            self.setDict(self.dict())

        def dict(self):
            """
            Public method to get the spelling dictionary in use.

            @return spelling dictionary
            @rtype enchant.Dict
            """
            return self.__spellDict

        def setDict(self, spellDict):
            """
            Public method to set the spelling dictionary to be used.

            @param spellDict spelling dictionary
            @type enchant.Dict
            """
            if spellDict:
                try:
                    self.__tokenizer = enchant.tokenize.get_tokenizer(
                        spellDict.tag,
                        chunkers=self.__chunkers,
                        filters=EnchantHighlighter.TokenFilters,
                    )
                except TokenizerNotFoundError:
                    # Fall back to the "good for most euro languages"
                    # English tokenizer
                    self.__tokenizer = enchant.tokenize.get_tokenizer(
                        chunkers=self.__chunkers,
                        filters=EnchantHighlighter.TokenFilters,
                    )
            else:
                self.__tokenizer = None

            self.__spellDict = spellDict

            self.rehighlight()

        def highlightBlock(self, text):
            """
            Public method to apply the text highlight.

            @param text text to be spell-checked
            @type str
            """
            """Overridden QSyntaxHighlighter method to apply the highlight"""
            if self.__spellDict is None or self.__tokenizer is None:
                return

            # Build a list of all misspelled words and highlight them
            misspellings = []
            with contextlib.suppress(enchant.errors.Error):
                for word, pos in self.__tokenizer(text):
                    if not self.__spellDict.check(word):
                        self.setFormat(pos, len(word), EnchantHighlighter.ErrorFormat)
                        misspellings.append((pos, pos + len(word)))

            # Store the list so the context menu can reuse this tokenization
            # pass (Block-relative values so editing other blocks won't
            # invalidate them)
            data = QTextBlockUserData()
            data.misspelled = misspellings
            self.setCurrentBlockUserData(data)

else:

    class SpellCheckMixin:
        """
        Class implementing the spell-check mixin for the widget classes.
        """

        #
        # This is just a stub to provide the same API as the enchant enabled
        # one.
        #
        def __init__(self):
            """
            Constructor
            """
            pass

        @pyqtSlot(QPoint)
        def _showContextMenu(self, pos):
            """
            Protected slot to show a context menu.

            @param pos position for the context menu
            @type QPoint
            """
            pass

        def setFormat(self, formatName):
            """
            Public method to set the document format.

            @param formatName name of the document format
            @type str
            """
            pass

        def dict(self):
            """
            Public method to get a reference to the dictionary in use.

            @return reference to the current dictionary
            @rtype enchant.Dict
            """
            pass

        def setDict(self, spellDict):
            """
            Public method to set the dictionary to be used.

            @param spellDict reference to the spell-check dictionary
            @type emchant.Dict
            """
            pass

        @pyqtSlot(str)
        def setLanguage(self, language):
            """
            Public slot to set the spellchecker language.

            @param language language to be set
            @type str
            """
            pass

        @pyqtSlot(str, str, str)
        def setLanguageWithPWL(self, language, pwl, pel):
            """
            Public slot to set the spellchecker language and associated user
            word lists.

            @param language language to be set
            @type str
            @param pwl file name of the personal word list
            @type str
            @param pel file name of the personal exclude list
            @type str
            """
            pass

        @classmethod
        def setDefaultLanguage(cls, language, pwl=None, pel=None):
            """
            Class method to set the default spell-check language.

            @param language language to be set as default
            @type str
            @param pwl file name of the personal word list
            @type str
            @param pel file name of the personal exclude list
            @type str
            """
            pass


class EricSpellCheckedPlainTextEdit(QPlainTextEdit, SpellCheckMixin):
    """
    Class implementing a QPlainTextEdit with built-in spell checker.
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor

        @param *args list of arguments for the QPlainTextEdit constructor.
        @type list
        @keyparam **kwargs dictionary of keyword arguments for the QSyntaxHighlighter
        @type dict
        """
        QPlainTextEdit.__init__(self, *args, **kwargs)
        SpellCheckMixin.__init__(self)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._showContextMenu)


class EricSpellCheckedTextEdit(QTextEdit, SpellCheckMixin):
    """
    Class implementing a QTextEdit with built-in spell checker.
    """

    def __init__(self, *args, **kwargs):
        """
        Constructor

        @param *args list of arguments for the QPlainTextEdit constructor.
        @type list
        @keyparam **kwargs dictionary of keyword arguments for the QSyntaxHighlighter
        @type dict
        """
        QTextEdit.__init__(self, *args, **kwargs)
        SpellCheckMixin.__init__(self)

        self.setFormat("html")

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._showContextMenu)

    def setAcceptRichText(self, accept):
        """
        Public method to set the text edit mode.

        @param accept flag indicating to accept rich text
        @type bool
        """
        QTextEdit.setAcceptRichText(self, accept)
        self.setFormat("html" if accept else "text")


if __name__ == "__main__":
    import os
    import sys

    from PyQt6.QtWidgets import QApplication

    if ENCHANT_AVAILABLE:
        dictPath = os.path.expanduser(os.path.join("~", ".eric7", "spelling"))
        SpellCheckMixin.setDefaultLanguage(
            "en_US",
            os.path.join(dictPath, "pwl.dic"),
            os.path.join(dictPath, "pel.dic"),
        )

    app = QApplication(sys.argv)
    spellEdit = EricSpellCheckedPlainTextEdit()
    spellEdit.show()

    sys.exit(app.exec())
