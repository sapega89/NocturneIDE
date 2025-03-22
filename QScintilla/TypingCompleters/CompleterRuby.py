# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a typing completer for Ruby.
"""

import re

from PyQt6.Qsci import QsciLexerRuby, QsciScintilla

from eric7 import Preferences

from .CompleterBase import CompleterBase


class CompleterRuby(CompleterBase):
    """
    Class implementing typing completer for Ruby.
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

        self.__beginRX = re.compile(r"""^=begin """)
        self.__beginNlRX = re.compile(r"""^=begin\r?\n""")
        self.__hereRX = re.compile(r"""<<-?['"]?(\w*)['"]?\r?\n""")

        self.__trailingBlankRe = re.compile(r"(?:,)(\s*)\r?\n")

        self.readSettings()

    def readSettings(self):
        """
        Public slot called to reread the configuration parameters.
        """
        self.setEnabled(Preferences.getEditorTyping("Ruby/EnabledTypingAids"))
        self.__insertClosingBrace = Preferences.getEditorTyping(
            "Ruby/InsertClosingBrace"
        )
        self.__indentBrace = Preferences.getEditorTyping("Ruby/IndentBrace")
        self.__skipBrace = Preferences.getEditorTyping("Ruby/SkipBrace")
        self.__insertQuote = Preferences.getEditorTyping("Ruby/InsertQuote")
        self.__insertBlank = Preferences.getEditorTyping("Ruby/InsertBlank")
        self.__insertHereDoc = Preferences.getEditorTyping("Ruby/InsertHereDoc")
        self.__insertInlineDoc = Preferences.getEditorTyping("Ruby/InsertInlineDoc")

    def charAdded(self, charNumber):
        """
        Public slot called to handle the user entering a character.

        @param charNumber value of the character entered
        @type int
        """
        char = chr(charNumber)
        if char not in ["(", ")", "{", "}", "[", "]", ",", "'", '"', "\n", " "]:
            return  # take the short route

        line, col = self.editor.getCursorPosition()

        if (
            self.__inComment(line, col)
            or self.__inDoubleQuotedString()
            or self.__inSingleQuotedString()
            or self.__inHereDocument()
            or self.__inInlineDocument()
        ):
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

        # space
        # complete inline documentation
        elif char == " ":
            txt = self.editor.text(line)[:col]
            if self.__insertInlineDoc and self.__beginRX.fullmatch(txt):
                self.editor.insert("=end")

        # comma
        # insert blank
        elif char == "," and self.__insertBlank:
            self.editor.insert(" ")
            self.editor.setCursorPosition(line, col + 1)

        # open curly brace
        # insert closing brace
        elif char == "{" and self.__insertClosingBrace:
            self.editor.insert("}")

        # open bracket
        # insert closing bracket
        elif char == "[" and self.__insertClosingBrace:
            self.editor.insert("]")

        # double quote
        # insert double quote
        elif char == '"' and self.__insertQuote:
            self.editor.insert('"')

        # quote
        # insert quote
        elif char == "'" and self.__insertQuote:
            self.editor.insert("'")

        # new line
        # indent to opening brace, complete inline documentation
        elif char == "\n":
            txt = self.editor.text(line - 1)
            if self.__insertBlank and self.__trailingBlankRe.search(txt):
                match = self.__trailingBlankRe.search(txt)
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
                        # get the line again for next check
                        txt = self.editor.text(line - 1)

                    self.editor.setCursorPosition(line, 0)
                    self.editor.editorCommand(QsciScintilla.SCI_VCHOME)

            if self.__insertInlineDoc and self.__beginNlRX.fullmatch(txt):
                self.editor.insert("=end")
            elif self.__insertHereDoc and self.__hereRX.fullmatch(txt):
                self.editor.insert(self.__hereRX.fullmatch(txt).group(1))
            elif self.__indentBrace and re.search(":\r?\n", txt) is None:
                stxt = txt.strip()
                if stxt and stxt[-1] in ("(", "[", "{"):
                    # indent one more level
                    self.editor.indent(line)
                    self.editor.editorCommand(QsciScintilla.SCI_VCHOME)
                else:
                    # indent to the level of the opening brace
                    openCount = len(re.findall("[({[]", txt))
                    closeCount = len(re.findall(r"[)}\]]", txt))
                    if openCount > closeCount:
                        openCount = 0
                        closeCount = 0
                        openList = list(re.finditer("[({[]", txt))
                        index = len(openList) - 1
                        while index > -1 and openCount == closeCount:
                            lastOpenIndex = openList[index].start()
                            txt2 = txt[lastOpenIndex:]
                            openCount = len(re.findall("[({[]", txt2))
                            closeCount = len(re.findall(r"[)}\]]", txt2))
                            index -= 1
                        if openCount > closeCount and lastOpenIndex > col:
                            self.editor.insert(" " * (lastOpenIndex - col + 1))
                            self.editor.setCursorPosition(line, lastOpenIndex + 1)

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

    def __inDoubleQuotedString(self):
        """
        Private method to check, if the cursor is within a double quoted
        string.

        @return flag indicating, if the cursor is inside a double
            quoted string
        @rtype bool
        """
        return self.editor.currentStyle() == QsciLexerRuby.DoubleQuotedString

    def __inSingleQuotedString(self):
        """
        Private method to check, if the cursor is within a single quoted
        string.

        @return flag indicating, if the cursor is inside a single
            quoted string
        @rtype bool
        """
        return self.editor.currentStyle() == QsciLexerRuby.SingleQuotedString

    def __inHereDocument(self):
        """
        Private method to check, if the cursor is within a here document.

        @return flag indicating, if the cursor is inside a here document
        @rtype bool
        """
        return self.editor.currentStyle() == QsciLexerRuby.HereDocument

    def __inInlineDocument(self):
        """
        Private method to check, if the cursor is within an inline document.

        @return flag indicating, if the cursor is inside an inline document
        @rtype bool
        """
        return self.editor.currentStyle() == QsciLexerRuby.POD


def createCompleter(editor, parent=None):
    """
    Function to instantiate a typing completer object.

    @param editor reference to the editor object
    @type QScintilla.Editor
    @param parent reference to the parent object (defaults to None)
    @type QObject (optional)
    @return reference to the instantiated typing completer object
    @rtype CompleterRuby
    """
    return CompleterRuby(editor, parent=parent)
