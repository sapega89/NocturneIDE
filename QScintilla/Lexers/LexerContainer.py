# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a base class for custom lexers.
"""

from PyQt6.Qsci import QsciLexer

from .Lexer import Lexer


class LexerContainer(Lexer, QsciLexer):
    """
    Subclass as a base for the implementation of custom lexers.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexer.__init__(self, parent)
        Lexer.__init__(self)

        self.editor = parent

    def language(self):
        """
        Public method returning the language of the lexer.

        @return language of the lexer
        @rtype str
        """
        return "Container"

    def lexer(self):
        """
        Public method returning the type of the lexer.

        @return type of the lexer
        @rtype str
        """
        if hasattr(self, "lexerId"):
            return None
        else:
            return "container"

    def description(self, _style):
        """
        Public method returning the descriptions of the styles supported
        by the lexer.

        <b>Note</b>: This methods needs to be overridden by the lexer class.

        @param _style style number (unused)
        @type int
        @return description for the given style
        @rtype str
        """
        return ""

    def styleText(self, start, end):
        """
        Public method to perform the styling.

        @param start position of first character to be styled
        @type int
        @param end position of last character to be styled
        @type int
        """
        self.editor.startStyling(start, 0x1F)
        self.editor.setStyling(end - start + 1, 0)

    def keywords(self, kwSet):
        """
        Public method to get the keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return Lexer.keywords(self, kwSet)
