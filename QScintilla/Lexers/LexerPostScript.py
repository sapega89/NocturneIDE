# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a PostScript lexer with some additional methods.
"""

from PyQt6.Qsci import QsciLexerPostScript

from eric7 import Preferences

from .Lexer import Lexer


class LexerPostScript(Lexer, QsciLexerPostScript):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerPostScript.__init__(self, parent)
        Lexer.__init__(self)

        self.commentString = "%"

        self.keywordSetDescriptions = [
            self.tr("PS Level 1 operators"),
            self.tr("PS Level 2 operators"),
            self.tr("PS Level 3 operators"),
            self.tr("RIP specific operators"),
            self.tr("User defined operators"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        self.setTokenize(Preferences.getEditor("PostScriptTokenize"))
        self.setLevel(Preferences.getEditor("PostScriptLevel"))
        self.setFoldAtElse(Preferences.getEditor("PostScriptFoldAtElse"))
        self.setFoldCompact(Preferences.getEditor("AllFoldCompact"))

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [QsciLexerPostScript.Comment]

    def isStringStyle(self, _style):
        """
        Public method to check, if a style is a string style.

        @param _style style to check (unused)
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return False

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerPostScript.keywords(self, kwSet)

    def maximumKeywordSet(self):
        """
        Public method to get the maximum keyword set.

        @return maximum keyword set
        @rtype int
        """
        return 5


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerPostScript
    """
    return LexerPostScript(parent=parent)
