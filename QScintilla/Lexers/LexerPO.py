# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a Gettext lexer with some additional methods.
"""

from PyQt6.Qsci import QsciLexerPO

from eric7 import Preferences

from .Lexer import Lexer


class LexerPO(Lexer, QsciLexerPO):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerPO.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "#"

        self.keywordSetDescriptions = []

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        self.setFoldComments(Preferences.getEditor("PoFoldComment"))
        self.setFoldCompact(Preferences.getEditor("AllFoldCompact"))

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [QsciLexerPO.Comment, QsciLexerPO.ProgrammerComment]

    def isStringStyle(self, style):
        """
        Public method to check, if a style is a string style.

        @param style style to check
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return style in [
            QsciLexerPO.MessageIdText,
            QsciLexerPO.MessageStringText,
            QsciLexerPO.MessageContextText,
        ]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerPO.keywords(self, kwSet)


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerPO
    """
    return LexerPO(parent=parent)
