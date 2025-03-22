# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a Pascal lexer with some additional methods.
"""

import contextlib

from PyQt6.Qsci import QsciLexerPascal

from eric7 import Preferences

from .Lexer import Lexer


class LexerPascal(Lexer, QsciLexerPascal):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerPascal.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "//"
        self.streamCommentString = {"start": "{ ", "end": " }"}

        self.keywordSetDescriptions = [
            self.tr("Keywords"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        self.setFoldComments(Preferences.getEditor("PascalFoldComment"))
        self.setFoldPreprocessor(Preferences.getEditor("PascalFoldPreprocessor"))
        self.setFoldCompact(Preferences.getEditor("AllFoldCompact"))
        with contextlib.suppress(AttributeError):
            self.setSmartHighlighting(Preferences.getEditor("PascalSmartHighlighting"))

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
        try:
            return style in [
                QsciLexerPascal.Comment,
                QsciLexerPascal.CommentDoc,
                QsciLexerPascal.CommentLine,
            ]
        except AttributeError:
            return style in [
                QsciLexerPascal.Comment,
                QsciLexerPascal.CommentParenthesis,
                QsciLexerPascal.CommentLine,
            ]

    def isStringStyle(self, style):
        """
        Public method to check, if a style is a string style.

        @param style style to check
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return style in [QsciLexerPascal.SingleQuotedString]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerPascal.keywords(self, kwSet)


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerPascal
    """
    return LexerPascal(parent=parent)
