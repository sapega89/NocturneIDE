# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a Java lexer with some additional methods.
"""

from PyQt6.Qsci import QsciLexerJava, QsciScintilla

from eric7 import Preferences

from .Lexer import Lexer


class LexerJava(Lexer, QsciLexerJava):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerJava.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "//"
        self.streamCommentString = {"start": "/* ", "end": " */"}
        self.boxCommentString = {"start": "/* ", "middle": " * ", "end": " */"}

        self.keywordSetDescriptions = [
            self.tr("Primary keywords and identifiers"),
            self.tr("Secondary keywords and identifiers"),
            self.tr("Documentation comment keywords"),
            self.tr("Global classes and typedefs"),
            self.tr("Preprocessor definitions"),
            self.tr("Task marker and error marker keywords"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        self.setFoldComments(Preferences.getEditor("CppFoldComment"))
        self.setFoldPreprocessor(Preferences.getEditor("CppFoldPreprocessor"))
        self.setFoldAtElse(Preferences.getEditor("CppFoldAtElse"))
        indentStyle = 0
        if Preferences.getEditor("CppIndentOpeningBrace"):
            indentStyle |= QsciScintilla.AiOpening
        if Preferences.getEditor("CppIndentClosingBrace"):
            indentStyle |= QsciScintilla.AiClosing
        self.setAutoIndentStyle(indentStyle)
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
            QsciLexerJava.Comment,
            QsciLexerJava.CommentDoc,
            QsciLexerJava.CommentLine,
            QsciLexerJava.CommentLineDoc,
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
            QsciLexerJava.DoubleQuotedString,
            QsciLexerJava.SingleQuotedString,
            QsciLexerJava.UnclosedString,
            QsciLexerJava.VerbatimString,
        ]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerJava.keywords(self, kwSet)

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
    @rtype LexerJava
    """
    return LexerJava(parent=parent)
