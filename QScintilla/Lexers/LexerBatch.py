# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a Batch file lexer with some additional methods.
"""

from PyQt6.Qsci import QsciLexerBatch

from .Lexer import Lexer


class LexerBatch(Lexer, QsciLexerBatch):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerBatch.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "REM "

        self.keywordSetDescriptions = [
            self.tr("Internal Commands"),
            self.tr("External Commands"),
        ]

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [QsciLexerBatch.Comment]

    def isStringStyle(self, _style):
        """
        Public method to check, if a style is a string style.

        @param _style style to check (unused)
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return False

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerBatch.keywords(self, kwSet)


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerBatch
    """
    return LexerBatch(parent=parent)
