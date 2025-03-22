# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a SQL lexer with some additional methods.
"""

import contextlib

from PyQt6.Qsci import QsciLexerSQL

from eric7 import Preferences

from .Lexer import Lexer


class LexerSQL(Lexer, QsciLexerSQL):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerSQL.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "--"

        self.keywordSetDescriptions = [
            self.tr("Keywords"),
            self.tr("Database Objects"),
            self.tr("PLDoc"),
            self.tr("SQL*Plus"),
            self.tr("Standard Packages"),
            self.tr("User defined 1"),
            self.tr("User defined 2"),
            self.tr("User defined 3"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        self.setFoldComments(Preferences.getEditor("SqlFoldComment"))
        self.setBackslashEscapes(Preferences.getEditor("SqlBackslashEscapes"))
        self.setFoldCompact(Preferences.getEditor("AllFoldCompact"))
        with contextlib.suppress(AttributeError):
            self.setDottedWords(Preferences.getEditor("SqlDottedWords"))
            self.setFoldAtElse(Preferences.getEditor("SqlFoldAtElse"))
            self.setFoldOnlyBegin(Preferences.getEditor("SqlFoldOnlyBegin"))
            self.setHashComments(Preferences.getEditor("SqlHashComments"))
            self.setQuotedIdentifiers(Preferences.getEditor("SqlQuotedIdentifiers"))

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [
            QsciLexerSQL.Comment,
            QsciLexerSQL.CommentDoc,
            QsciLexerSQL.CommentLine,
            QsciLexerSQL.CommentLineHash,
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
            QsciLexerSQL.DoubleQuotedString,
            QsciLexerSQL.SingleQuotedString,
        ]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerSQL.keywords(self, kwSet)

    def maximumKeywordSet(self):
        """
        Public method to get the maximum keyword set.

        @return maximum keyword set
        @rtype int
        """
        return 8


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerSQL
    """
    return LexerSQL(parent=parent)
