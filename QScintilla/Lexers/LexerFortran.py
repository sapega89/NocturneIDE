# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a Fortran lexer with some additional methods.
"""

from PyQt6.Qsci import QsciLexerFortran

from eric7 import Preferences

from .Lexer import Lexer


class LexerFortran(Lexer, QsciLexerFortran):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerFortran.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "c "

        self.keywordSetDescriptions = [
            self.tr("Primary keywords and identifiers"),
            self.tr("Intrinsic functions"),
            self.tr("Extended and user defined functions"),
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
        return ["."]

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [QsciLexerFortran.Comment]

    def isStringStyle(self, style):
        """
        Public method to check, if a style is a string style.

        @param style style to check
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return style in [
            QsciLexerFortran.DoubleQuotedString,
            QsciLexerFortran.SingleQuotedString,
            QsciLexerFortran.UnclosedString,
        ]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerFortran.keywords(self, kwSet)


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerFortran
    """
    return LexerFortran(parent=parent)
