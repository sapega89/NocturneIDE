# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a typing completer for TOML.
"""

import re

from PyQt6.Qsci import QsciScintilla

from eric7 import Preferences

from .CompleterBase import CompleterBase


class CompleterYaml(CompleterBase):
    """
    Class implementing typing completer for TOML.
    """

    def __init__(self, editor, parent=None):
        """
        Constructor

        @param editor reference to the editor object
        @type QScintilla.Editor
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(editor, parent)

        self.__autoIndentationRe = re.compile(r"(?:\(|\[|{)(\s*)\r?\n")
        self.__trailingBlankRe = re.compile(r"(?:[=:,])(\s*)\r?\n")

        self.readSettings()

    def readSettings(self):
        """
        Public slot called to reread the configuration parameters.
        """
        self.setEnabled(Preferences.getEditorTyping("Toml/EnabledTypingAids"))
        self.__insertClosingBrace = Preferences.getEditorTyping(
            "Toml/InsertClosingBrace"
        )
        self.__skipBrace = Preferences.getEditorTyping("Toml/SkipBrace")
        self.__insertQuote = Preferences.getEditorTyping("Toml/InsertQuote")
        self.__autoIndentation = Preferences.getEditorTyping("Toml/AutoIndentation")
        self.__colonDetection = Preferences.getEditorTyping("Toml/ColonDetection")
        self.__insertBlankEqual = Preferences.getEditorTyping("Toml/InsertBlankEqual")
        self.__insertBlankColon = Preferences.getEditorTyping("Toml/InsertBlankColon")
        self.__insertBlankComma = Preferences.getEditorTyping("Toml/InsertBlankComma")

    def charAdded(self, charNumber):
        """
        Public slot called to handle the user entering a character.

        @param charNumber value of the character entered
        @type int
        """
        char = chr(charNumber)
        if char not in ["{", "}", "[", "]", "(", ")", "'", '"', "=", ":", ",", "\n"]:
            return  # take the short route

        line, col = self.editor.getCursorPosition()

        if self.__inComment(line, col):
            return

        # open parenthesis
        # insert closing parenthesis
        if char == "(" and self.__insertClosingBrace:
            self.editor.insert(")")

        # open curly bracket
        # insert closing bracket
        if char == "{" and self.__insertClosingBrace:
            self.editor.insert("}")

        # open bracket
        # insert closing bracket
        elif char == "[" and self.__insertClosingBrace:
            self.editor.insert("]")

        # closing parenthesis
        # skip matching closing parenthesis
        elif char in [")", "}", "]"]:
            txt = self.editor.text(line)
            if col < len(txt) and char == txt[col] and self.__skipBrace:
                self.editor.setSelection(line, col, line, col + 1)
                self.editor.removeSelectedText()

        # colon
        # 1. skip colon if not last character
        # 2. insert blank if last character
        elif char == ":":
            text = self.editor.text(line)
            if col < len(text) and char == text[col]:
                if self.__colonDetection:
                    self.editor.setSelection(line, col, line, col + 1)
                    self.editor.removeSelectedText()
            elif self.__insertBlankColon and col == len(text.rstrip()):
                self.editor.insert(" ")
                self.editor.setCursorPosition(line, col + 1)

        # equal sign or comma
        # insert blank
        elif (char == "=" and self.__insertBlankEqual) or (
            char == "," and self.__insertBlankComma
        ):
            self.editor.insert(" ")
            self.editor.setCursorPosition(line, col + 1)

        # double quote
        # insert double quote
        elif char == '"' and self.__insertQuote:
            self.editor.insert('"')

        # single quote
        # insert single quote
        elif char == "'" and self.__insertQuote:
            self.editor.insert("'")

        # new line
        elif char == "\n":
            txt = self.editor.text(line - 1)
            if self.__autoIndentation and self.__autoIndentationRe.search(txt):
                # indent after line ending with auto indentation character
                match = self.__autoIndentationRe.search(txt)
                if match is not None:
                    startBlanks = match.start(1)
                    endBlanks = match.end(1)
                    if startBlanks != -1 and startBlanks != endBlanks:
                        # previous line ends with whitespace, e.g. caused by
                        # blank insertion above
                        self.editor.setSelection(
                            line - 1, startBlanks, line - 1, endBlanks
                        )
                        self.editor.removeSelectedText()

                    self.editor.indent(line)
                    self.editor.setCursorPosition(line, 0)
                    self.editor.editorCommand(QsciScintilla.SCI_VCHOME)

            elif (
                self.__insertBlankColon
                or self.__insertBlankComma
                or self.__insertBlankEqual
            ) and self.__trailingBlankRe.search(txt):
                # remove blank at end of line inserted by blank insertion above
                match = self.__trailingBlankRe.search(txt)
                if match is not None:
                    startBlanks = match.start(1)
                    endBlanks = match.end(1)
                    if startBlanks != -1 and startBlanks != endBlanks:
                        self.editor.setSelection(
                            line - 1, startBlanks, line - 1, endBlanks
                        )
                        self.editor.removeSelectedText()

                    self.editor.setCursorPosition(line, 0)
                    self.editor.editorCommand(QsciScintilla.SCI_VCHOME)

    def __inComment(self, line, col):
        """
        Private method to check, if the cursor is inside a comment.

        @param line current line
        @type int
        @param col current position within line
        @type int
        @return flag indicating, if the cursor is inside a comment
        @rtype bool
        """
        txt = self.editor.text(line)
        if col == len(txt):
            col -= 1
        while col >= 0:
            if txt[col] == "#":
                return True
            col -= 1
        return False


def createCompleter(editor, parent=None):
    """
    Function to instantiate a typing completer object.

    @param editor reference to the editor object
    @type QScintilla.Editor
    @param parent reference to the parent object (defaults to None)
    @type QObject (optional)
    @return reference to the instantiated typing completer object
    @rtype CompleterYaml
    """
    return CompleterYaml(editor, parent=parent)
