# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a CoffeeScript lexer with some additional methods.
"""

from PyQt6.Qsci import QsciLexerCoffeeScript

from eric7 import Preferences

from .Lexer import Lexer


class LexerCoffeeScript(Lexer, QsciLexerCoffeeScript):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerCoffeeScript.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "#"
        self.streamCommentString = {"start": "###\n", "end": "\n###"}

        self.keywordSetDescriptions = [
            self.tr("Keywords"),
            self.tr("Secondary keywords"),
            self.tr("Unused"),
            self.tr("Global classes"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        self.setDollarsAllowed(Preferences.getEditor("CoffeeScriptDollarsAllowed"))
        self.setFoldComments(Preferences.getEditor("CoffeScriptFoldComment"))
        self.setStylePreprocessor(
            Preferences.getEditor("CoffeeScriptStylePreprocessor")
        )
        self.setFoldCompact(Preferences.getEditor("AllFoldCompact"))

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [
            QsciLexerCoffeeScript.Comment,
            QsciLexerCoffeeScript.CommentDoc,
            QsciLexerCoffeeScript.CommentLine,
            QsciLexerCoffeeScript.CommentLineDoc,
            QsciLexerCoffeeScript.CommentBlock,
            QsciLexerCoffeeScript.BlockRegexComment,
        ]

    def isStringStyle(self, style):
        """
        Public method to check, if a style is a string style.

        @param style style to check
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return style in [
            QsciLexerCoffeeScript.DoubleQuotedString,
            QsciLexerCoffeeScript.SingleQuotedString,
            QsciLexerCoffeeScript.UnclosedString,
            QsciLexerCoffeeScript.VerbatimString,
        ]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerCoffeeScript.keywords(self, kwSet)

    def maximumKeywordSet(self):
        """
        Public method to get the maximum keyword set.

        @return maximum keyword set
        @rtype int
        """
        return 4


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerCoffeeScript
    """
    return LexerCoffeeScript(parent=parent)
