# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a Lua lexer with some additional methods.
"""

from PyQt6.Qsci import QsciLexerLua

from eric7 import Preferences

from .Lexer import Lexer


class LexerLua(Lexer, QsciLexerLua):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerLua.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "--"
        self.streamCommentString = {"start": "--[[ ", "end": " ]]--"}

        self.keywordSetDescriptions = [
            self.tr("Keywords"),
            self.tr("Basic functions"),
            self.tr("String, (table) & math functions"),
            self.tr("Coroutines, I/O & system facilities"),
            self.tr("User defined 1"),
            self.tr("User defined 2"),
            self.tr("User defined 3"),
            self.tr("User defined 4"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        self.setFoldCompact(Preferences.getEditor("AllFoldCompact"))

    def autoCompletionWordSeparators(self):
        """
        Public method to return the list of separators for autocompletion.

        @return list of separators
        @rtype list of str
        """
        return [":", "."]

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [QsciLexerLua.Comment, QsciLexerLua.LineComment]

    def isStringStyle(self, style):
        """
        Public method to check, if a style is a string style.

        @param style style to check
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return style in [
            QsciLexerLua.String,
            QsciLexerLua.LiteralString,
            QsciLexerLua.UnclosedString,
        ]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerLua.keywords(self, kwSet)

    def maximumKeywordSet(self):
        """
        Public method to get the maximum keyword set.

        @return maximum keyword set
        @rtype int
        """
        return 8


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerLua
    """
    return LexerLua(parent=parent)
