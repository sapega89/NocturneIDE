# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a typing completer for Python.
"""

import re

from PyQt6.Qsci import QsciLexerPython, QsciScintilla

from eric7 import Preferences
from eric7.Utilities import rxIndex

from .CompleterBase import CompleterBase


class CompleterPython(CompleterBase):
    """
    Class implementing typing completer for Python.
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

        self.__defRX = re.compile(r"^[ \t]*(async[ \t]+)?(def|cdef|cpdef) \w+\(")
        self.__defSelfRX = re.compile(
            r"^[ \t]*(async[ \t]+)?(def|cdef|cpdef) \w+\([ \t]*self[ \t]*[,)]"
        )
        self.__defClsRX = re.compile(
            r"^[ \t]*(async[ \t]+)?(def|cdef|cpdef) \w+\([ \t]*cls[ \t]*[,)]"
        )
        self.__classRX = re.compile(r"^[ \t]*(cdef[ \t]+)?class \w+[(:]")
        self.__importRX = re.compile(r"^[ \t]*from [\w.]+ ")
        self.__classmethodRX = re.compile(r"^[ \t]*@classmethod")
        self.__staticmethodRX = re.compile(r"^[ \t]*@staticmethod")

        self.__defOnlyRX = re.compile(r"^[ \t]*def ")

        self.__ifRX = re.compile(r"^[ \t]*if ")
        self.__elifRX = re.compile(r"^[ \t]*elif ")
        self.__elseRX = re.compile(r"^[ \t]*else:")

        self.__tryRX = re.compile(r"^[ \t]*try:")
        self.__finallyRX = re.compile(r"^[ \t]*finally:")
        self.__exceptRX = re.compile(r"^[ \t]*except ")
        self.__exceptcRX = re.compile(r"^[ \t]*except:")

        self.__whileRX = re.compile(r"^[ \t]*while ")
        self.__forRX = re.compile(r"^[ \t]*(async[ \t]+)?for ")

        self.__trailingBlankRe = re.compile(r"(?:,)(\s*)\r?\n")

        self.readSettings()

    def readSettings(self):
        """
        Public slot called to reread the configuration parameters.
        """
        self.setEnabled(Preferences.getEditorTyping("Python/EnabledTypingAids"))
        self.__insertClosingBrace = Preferences.getEditorTyping(
            "Python/InsertClosingBrace"
        )
        self.__indentBrace = Preferences.getEditorTyping("Python/IndentBrace")
        self.__skipBrace = Preferences.getEditorTyping("Python/SkipBrace")
        self.__insertQuote = Preferences.getEditorTyping("Python/InsertQuote")
        self.__dedentElse = Preferences.getEditorTyping("Python/DedentElse")
        self.__dedentExcept = Preferences.getEditorTyping("Python/DedentExcept")
        self.__insertImport = Preferences.getEditorTyping("Python/InsertImport")
        self.__importBraceType = Preferences.getEditorTyping("Python/ImportBraceType")
        self.__insertSelf = Preferences.getEditorTyping("Python/InsertSelf")
        self.__insertBlank = Preferences.getEditorTyping("Python/InsertBlank")
        self.__colonDetection = Preferences.getEditorTyping("Python/ColonDetection")
        self.__dedentDef = Preferences.getEditorTyping("Python/DedentDef")

    def charAdded(self, charNumber):
        """
        Public slot called to handle the user entering a character.

        @param charNumber value of the character entered
        @type int
        """
        char = chr(charNumber)
        if char not in ["(", ")", "{", "}", "[", "]", " ", ",", "'", '"', "\n", ":"]:
            return  # take the short route

        line, col = self.editor.getCursorPosition()

        if (
            self.__inComment(line, col)
            or (char != '"' and self.__inDoubleQuotedString())
            or (char != '"' and self.__inTripleDoubleQuotedString())
            or (char != "'" and self.__inSingleQuotedString())
            or (char != "'" and self.__inTripleSingleQuotedString())
        ):
            return

        # open parenthesis
        # insert closing parenthesis and self
        if char == "(":
            txt = self.editor.text(line)[:col]
            self.editor.beginUndoAction()
            if self.__insertSelf and self.__defRX.fullmatch(txt) is not None:
                if self.__isClassMethodDef():
                    self.editor.insert("cls")
                    self.editor.setCursorPosition(line, col + 3)
                elif self.__isStaticMethodDef():
                    # nothing to insert
                    pass
                elif self.__isClassMethod():
                    self.editor.insert("self")
                    self.editor.setCursorPosition(line, col + 4)
            if self.__insertClosingBrace:
                if self.__defRX.fullmatch(txt) is not None or (
                    self.__classRX.fullmatch(txt) is not None and txt.endswith("(")
                ):
                    self.editor.insert("):")
                else:
                    self.editor.insert(")")
            self.editor.endUndoAction()

        # closing parenthesis
        # skip matching closing parenthesis
        elif char in [")", "}", "]"]:
            txt = self.editor.text(line)
            if col < len(txt) and char == txt[col] and self.__skipBrace:
                self.editor.setSelection(line, col, line, col + 1)
                self.editor.removeSelectedText()

        # space
        # insert import, dedent to if for elif, dedent to try for except,
        # dedent def
        elif char == " ":
            txt = self.editor.text(line)[:col]
            if self.__insertImport and self.__importRX.fullmatch(txt):
                self.editor.beginUndoAction()
                if self.__importBraceType:
                    self.editor.insert("import ()")
                    self.editor.setCursorPosition(line, col + 8)
                else:
                    self.editor.insert("import ")
                    self.editor.setCursorPosition(line, col + 7)
                self.editor.endUndoAction()
            elif self.__dedentElse and self.__elifRX.fullmatch(txt):
                self.__dedentToIf()
            elif self.__dedentExcept and self.__exceptRX.fullmatch(txt):
                self.__dedentExceptToTry()
            elif self.__dedentDef and self.__defOnlyRX.fullmatch(txt):
                self.__dedentDefStatement()

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

        # colon
        # skip colon, dedent to if for else:
        elif char == ":":
            text = self.editor.text(line)
            if col < len(text) and char == text[col]:
                if self.__colonDetection:
                    self.editor.setSelection(line, col, line, col + 1)
                    self.editor.removeSelectedText()
            else:
                txt = text[:col]
                if self.__dedentElse and self.__elseRX.fullmatch(txt):
                    self.__dedentElseToIfWhileForTry()
                elif self.__dedentExcept and self.__exceptcRX.fullmatch(txt):
                    self.__dedentExceptToTry()
                elif self.__dedentExcept and self.__finallyRX.fullmatch(txt):
                    self.__dedentFinallyToTry()

        # new line
        # indent to opening brace
        elif char == "\n" and self.__indentBrace:
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

            if re.search(":\r?\n", txt) is None:
                self.editor.beginUndoAction()
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
                self.editor.endUndoAction()

    def __dedentToIf(self):
        """
        Private method to dedent the last line to the last if statement with
        less (or equal) indentation.
        """
        line, col = self.editor.getCursorPosition()
        indentation = self.editor.indentation(line)
        ifLine = line - 1
        while ifLine >= 0:
            txt = self.editor.text(ifLine)
            edInd = self.editor.indentation(ifLine)
            if rxIndex(self.__elseRX, txt) == 0 and edInd <= indentation:
                indentation = edInd - 1
            elif (
                rxIndex(self.__ifRX, txt) == 0 or rxIndex(self.__elifRX, txt) == 0
            ) and edInd <= indentation:
                self.editor.cancelList()
                self.editor.setIndentation(line, edInd)
                break
            ifLine -= 1

    def __dedentElseToIfWhileForTry(self):
        """
        Private method to dedent the line of the else statement to the last
        if, while, for or try statement with less (or equal) indentation.
        """
        line, col = self.editor.getCursorPosition()
        indentation = self.editor.indentation(line)
        if line > 0:
            prevInd = self.editor.indentation(line - 1)
        ifLine = line - 1
        while ifLine >= 0:
            txt = self.editor.text(ifLine)
            edInd = self.editor.indentation(ifLine)
            if (rxIndex(self.__elseRX, txt) == 0 and edInd <= indentation) or (
                rxIndex(self.__elifRX, txt) == 0
                and edInd == indentation
                and edInd == prevInd
            ):
                indentation = edInd - 1
            elif (
                rxIndex(self.__ifRX, txt) == 0
                or rxIndex(self.__whileRX, txt) == 0
                or rxIndex(self.__forRX, txt) == 0
                or rxIndex(self.__tryRX, txt) == 0
            ) and edInd <= indentation:
                self.editor.cancelList()
                self.editor.setIndentation(line, edInd)
                break
            ifLine -= 1

    def __dedentExceptToTry(self):
        """
        Private method to dedent the line of the except statement to the last
        try statement with less (or equal) indentation.
        """
        line, col = self.editor.getCursorPosition()
        indentation = self.editor.indentation(line)
        tryLine = line - 1
        while tryLine >= 0:
            txt = self.editor.text(tryLine)
            edInd = self.editor.indentation(tryLine)
            if (
                rxIndex(self.__exceptcRX, txt) == 0
                or rxIndex(self.__finallyRX, txt) == 0
            ) and edInd <= indentation:
                indentation = edInd - 1
            elif (
                rxIndex(self.__exceptRX, txt) == 0 or rxIndex(self.__tryRX, txt) == 0
            ) and edInd <= indentation:
                self.editor.cancelList()
                self.editor.setIndentation(line, edInd)
                break
            tryLine -= 1

    def __dedentFinallyToTry(self):
        """
        Private method to dedent the line of the except statement to the last
        try statement with less (or equal) indentation.
        """
        line, col = self.editor.getCursorPosition()
        indentation = self.editor.indentation(line)
        tryLine = line - 1
        while tryLine >= 0:
            txt = self.editor.text(tryLine)
            edInd = self.editor.indentation(tryLine)
            if rxIndex(self.__finallyRX, txt) == 0 and edInd <= indentation:
                indentation = edInd - 1
            elif (
                rxIndex(self.__tryRX, txt) == 0
                or rxIndex(self.__exceptcRX, txt) == 0
                or rxIndex(self.__exceptRX, txt) == 0
            ) and edInd <= indentation:
                self.editor.cancelList()
                self.editor.setIndentation(line, edInd)
                break
            tryLine -= 1

    def __dedentDefStatement(self):
        """
        Private method to dedent the line of the def statement to a previous
        def statement or class statement.
        """
        line, col = self.editor.getCursorPosition()
        indentation = self.editor.indentation(line)
        tryLine = line - 1
        inMultiLineString = False
        while tryLine >= 0:
            txt = self.editor.text(tryLine)
            if txt.count('"""') % 2 != 0 or txt.count("'''") % 2 != 0:
                inMultiLineString = not inMultiLineString
            if not inMultiLineString:
                edInd = self.editor.indentation(tryLine)
                newInd = -1
                if rxIndex(self.__defRX, txt) == 0 and edInd < indentation:
                    newInd = edInd
                elif rxIndex(self.__classRX, txt) == 0 and edInd < indentation:
                    newInd = edInd + (
                        self.editor.indentationWidth() or self.editor.tabWidth()
                    )
                if newInd >= 0:
                    self.editor.cancelList()
                    self.editor.setIndentation(line, newInd)
                    break
            tryLine -= 1

    def __isClassMethod(self):
        """
        Private method to check, if the user is defining a class method.

        @return flag indicating the definition of a class method
        @rtype bool
        """
        line, col = self.editor.getCursorPosition()
        indentation = self.editor.indentation(line)
        curLine = line - 1
        inMultiLineString = False
        while curLine >= 0:
            txt = self.editor.text(curLine)
            if txt.count('"""') % 2 != 0 or txt.count("'''") % 2 != 0:
                inMultiLineString = not inMultiLineString
            if not inMultiLineString:
                if (
                    (
                        rxIndex(self.__defSelfRX, txt) == 0
                        or rxIndex(self.__defClsRX, txt) == 0
                    )
                    and self.editor.indentation(curLine) == indentation
                ) or (
                    rxIndex(self.__classRX, txt) == 0
                    and self.editor.indentation(curLine) < indentation
                ):
                    return True
                elif (
                    rxIndex(self.__defRX, txt) == 0
                    and self.editor.indentation(curLine) <= indentation
                ):
                    return False
            curLine -= 1
        return False

    def __isClassMethodDef(self):
        """
        Private method to check, if the user is defing a class method
        (@classmethod).

        @return flag indicating the definition of a class method
        @rtype bool
        """
        line, col = self.editor.getCursorPosition()
        indentation = self.editor.indentation(line)
        curLine = line - 1
        if (
            rxIndex(self.__classmethodRX, self.editor.text(curLine)) == 0
            and self.editor.indentation(curLine) == indentation
        ):
            return True
        return False

    def __isStaticMethodDef(self):
        """
        Private method to check, if the user is defing a static method
        (@staticmethod) method.

        @return flag indicating the definition of a static method
        @rtype bool
        """
        line, col = self.editor.getCursorPosition()
        indentation = self.editor.indentation(line)
        curLine = line - 1
        if (
            rxIndex(self.__staticmethodRX, self.editor.text(curLine)) == 0
            and self.editor.indentation(curLine) == indentation
        ):
            return True
        return False

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
        return self.editor.currentStyle() == QsciLexerPython.DoubleQuotedString

    def __inTripleDoubleQuotedString(self):
        """
        Private method to check, if the cursor is within a triple double
        quoted string.

        @return flag indicating, if the cursor is inside a triple double
            quoted string
        @rtype bool
        """
        return self.editor.currentStyle() == QsciLexerPython.TripleDoubleQuotedString

    def __inSingleQuotedString(self):
        """
        Private method to check, if the cursor is within a single quoted
        string.

        @return flag indicating, if the cursor is inside a single
            quoted string
        @rtype bool
        """
        return self.editor.currentStyle() == QsciLexerPython.SingleQuotedString

    def __inTripleSingleQuotedString(self):
        """
        Private method to check, if the cursor is within a triple single
        quoted string.

        @return flag indicating, if the cursor is inside a triple single
            quoted string
        @rtype bool
        """
        return self.editor.currentStyle() == QsciLexerPython.TripleSingleQuotedString


def createCompleter(editor, parent=None):
    """
    Function to instantiate a typing completer object.

    @param editor reference to the editor object
    @type QScintilla.Editor
    @param parent reference to the parent object (defaults to None)
    @type QObject (optional)
    @return reference to the instantiated typing completer object
    @rtype CompleterPython
    """
    return CompleterPython(editor, parent=parent)
