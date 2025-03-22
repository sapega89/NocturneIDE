# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a CMake lexer with some additional methods.
"""

from PyQt6.Qsci import QsciLexerCMake

from eric7 import Preferences

from .Lexer import Lexer


class LexerCMake(Lexer, QsciLexerCMake):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerCMake.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "#"

        self.keywordSetDescriptions = [
            self.tr("Commands"),
            self.tr("Parameters"),
            self.tr("User defined"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        self.setFoldAtElse(Preferences.getEditor("CMakeFoldAtElse"))

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [QsciLexerCMake.Comment]

    def isStringStyle(self, style):
        """
        Public method to check, if a style is a string style.

        @param style style to check
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return style in [QsciLexerCMake.String]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerCMake.keywords(self, kwSet)


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerCMake
    """
    return LexerCMake(parent=parent)
