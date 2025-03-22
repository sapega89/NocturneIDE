# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a Markdown lexer with some additional methods.
"""

from PyQt6.Qsci import QsciLexerMarkdown

from .Lexer import Lexer


class LexerMarkdown(Lexer, QsciLexerMarkdown):
    """
    Subclass to implement some additional lexer dependent methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerMarkdown.__init__(self, parent)
        Lexer.__init__(self)

        self.keywordSetDescriptions = []

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerMarkdown.keywords(self, kwSet)


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerMarkdown
    """
    return LexerMarkdown(parent=parent)
