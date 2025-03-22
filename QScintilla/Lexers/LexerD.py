# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a D lexer with some additional methods.
"""

from PyQt6.Qsci import QsciLexerD, QsciScintilla

from eric7 import Preferences

from .Lexer import Lexer


class LexerD(Lexer, QsciLexerD):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerD.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "//"
        self.streamCommentString = {"start": "/+ ", "end": " +/"}
        self.boxCommentString = {"start": "/* ", "middle": " * ", "end": " */"}

        self.keywordSetDescriptions = [
            self.tr("Primary keywords and identifiers"),
            self.tr("Secondary keywords and identifiers"),
            self.tr("Documentation comment keywords"),
            self.tr("Type definitions and aliases"),
            self.tr("User defined 1"),
            self.tr("User defined 2"),
            self.tr("User defined 3"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        self.setFoldComments(Preferences.getEditor("DFoldComment"))
        self.setFoldAtElse(Preferences.getEditor("DFoldAtElse"))
        indentStyle = 0
        if Preferences.getEditor("DIndentOpeningBrace"):
            indentStyle |= QsciScintilla.AiOpening
        if Preferences.getEditor("DIndentClosingBrace"):
            indentStyle |= QsciScintilla.AiClosing
        self.setAutoIndentStyle(indentStyle)
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
        return style in [
            QsciLexerD.Comment,
            QsciLexerD.CommentDoc,
            QsciLexerD.CommentLine,
            QsciLexerD.CommentLineDoc,
            QsciLexerD.CommentNested,
        ]

    def isStringStyle(self, style):
        """
        Public method to check, if a style is a string style.

        @param style style to check
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return style in [QsciLexerD.String, QsciLexerD.UnclosedString]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerD.keywords(self, kwSet)

    def maximumKeywordSet(self):
        """
        Public method to get the maximum keyword set.

        @return maximum keyword set
        @rtype int
        """
        return 7


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerD
    """
    return LexerD(parent=parent)
