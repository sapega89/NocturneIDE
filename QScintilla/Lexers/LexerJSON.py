# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a JSON lexer with some additional methods.
"""

from PyQt6.Qsci import QsciLexerJSON

from eric7 import Preferences

from .Lexer import Lexer


class LexerJSON(Lexer, QsciLexerJSON):
    """
    Subclass to implement some additional lexer dependent methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerJSON.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "//"
        self.streamCommentString = {"start": "/* ", "end": " */"}

        self.keywordSetDescriptions = [
            self.tr("JSON Keywords"),
            self.tr("JSON-LD Keywords"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        self.setHighlightComments(Preferences.getEditor("JSONHightlightComments"))
        self.setHighlightEscapeSequences(
            Preferences.getEditor("JSONHighlightEscapeSequences")
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
        return style in [QsciLexerJSON.CommentLine, QsciLexerJSON.CommentBlock]

    def isStringStyle(self, style):
        """
        Public method to check, if a style is a string style.

        @param style style to check
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return style in [QsciLexerJSON.String, QsciLexerJSON.UnclosedString]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerJSON.keywords(self, kwSet)

    def maximumKeywordSet(self):
        """
        Public method to get the maximum keyword set.

        @return maximum keyword set
        @rtype int
        """
        return 2


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerJSON
    """
    return LexerJSON(parent=parent)
