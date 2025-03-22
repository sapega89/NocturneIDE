# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a TCL/Tk lexer with some additional methods.
"""

import contextlib

from PyQt6.Qsci import QsciLexerTCL

from eric7 import Preferences

from .Lexer import Lexer


class LexerTCL(Lexer, QsciLexerTCL):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerTCL.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "#"

        self.keywordSetDescriptions = [
            self.tr("TCL Keywords"),
            self.tr("TK Keywords"),
            self.tr("iTCL Keywords"),
            self.tr("TK Commands"),
            self.tr("expand"),
            self.tr("User defined 1"),
            self.tr("User defined 2"),
            self.tr("User defined 3"),
            self.tr("User defined 4"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        with contextlib.suppress(AttributeError):
            self.setFoldCompact(Preferences.getEditor("AllFoldCompact"))
        with contextlib.suppress(AttributeError):
            self.setFoldComments(Preferences.getEditor("TclFoldComment"))

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [
            QsciLexerTCL.Comment,
            QsciLexerTCL.CommentBlock,
            QsciLexerTCL.CommentBox,
            QsciLexerTCL.CommentLine,
        ]

    def isStringStyle(self, style):
        """
        Public method to check, if a style is a string style.

        @param style style to check
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return style in [QsciLexerTCL.QuotedString]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerTCL.keywords(self, kwSet)

    def maximumKeywordSet(self):
        """
        Public method to get the maximum keyword set.

        @return maximum keyword set
        @rtype int
        """
        return 9


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerTCL
    """
    return LexerTCL(parent=parent)
