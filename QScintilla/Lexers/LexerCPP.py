# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a CPP lexer with some additional methods.
"""

import contextlib

from PyQt6.Qsci import QsciLexerCPP, QsciScintilla

from eric7 import Preferences

from .SubstyledLexer import SubstyledLexer


class LexerCPP(SubstyledLexer, QsciLexerCPP):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerCPP.__init__(
            self, parent, Preferences.getEditor("CppCaseInsensitiveKeywords")
        )
        SubstyledLexer.__init__(self)

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

        ##############################################################
        ## default sub-style definitions
        ##############################################################

        diffToSecondary = 0x40
        # This may need to be changed to be in line with Scintilla C++ lexer.

        # list of style numbers, that support sub-styling
        self.baseStyles = [11, 17, 11 + diffToSecondary, 17 + diffToSecondary]

        self.defaultSubStyles = {
            11: {
                0: {
                    "Description": self.tr("Additional Identifier"),
                    "Words": "std map string vector",
                    "Style": {
                        "fore": 0xEE00AA,
                    },
                },
            },
            17: {
                0: {
                    "Description": self.tr("Additional JavaDoc keyword"),
                    "Words": "check",
                    "Style": {
                        "fore": 0x00AAEE,
                    },
                },
            },
            11
            + diffToSecondary: {
                0: {
                    "Description": self.tr("Inactive additional identifier"),
                    "Words": "std map string vector",
                    "Style": {
                        "fore": 0xBB6666,
                    },
                },
            },
            17
            + diffToSecondary: {
                0: {
                    "Description": self.tr("Inactive additional JavaDoc keyword"),
                    "Words": "check",
                    "Style": {
                        "fore": 0x6699AA,
                    },
                },
            },
        }

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
        with contextlib.suppress(AttributeError):
            self.setDollarsAllowed(Preferences.getEditor("CppDollarsAllowed"))
        with contextlib.suppress(AttributeError):
            self.setStylePreprocessor(Preferences.getEditor("CppStylePreprocessor"))
        with contextlib.suppress(AttributeError):
            self.setHighlightTripleQuotedStrings(
                Preferences.getEditor("CppHighlightTripleQuotedStrings")
            )
        with contextlib.suppress(AttributeError):
            self.setHighlightHashQuotedStrings(
                Preferences.getEditor("CppHighlightHashQuotedStrings")
            )
        with contextlib.suppress(AttributeError):
            self.setHighlightBackQuotedStrings(
                Preferences.getEditor("CppHighlightBackQuotedStrings")
            )
        with contextlib.suppress(AttributeError):
            self.setHighlightEscapeSequences(
                Preferences.getEditor("CppHighlightEscapeSequences")
            )
        with contextlib.suppress(AttributeError):
            self.setVerbatimStringEscapeSequencesAllowed(
                Preferences.getEditor("CppVerbatimStringEscapeSequencesAllowed")
            )

    def autoCompletionWordSeparators(self):
        """
        Public method to return the list of separators for autocompletion.

        @return list of separators
        @rtype list of str
        """
        return ["::", "->", "."]

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [
            QsciLexerCPP.Comment,
            QsciLexerCPP.CommentDoc,
            QsciLexerCPP.CommentLine,
            QsciLexerCPP.CommentLineDoc,
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
            QsciLexerCPP.DoubleQuotedString,
            QsciLexerCPP.SingleQuotedString,
            QsciLexerCPP.UnclosedString,
            QsciLexerCPP.VerbatimString,
        ]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerCPP.keywords(self, kwSet)

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
    @rtype LexerCPP
    """
    return LexerCPP(parent=parent)
