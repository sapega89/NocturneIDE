# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a HTML lexer with some additional methods.
"""

import contextlib

from PyQt6.Qsci import QsciLexerHTML

from eric7 import Preferences

from .Lexer import Lexer


class LexerHTML(Lexer, QsciLexerHTML):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerHTML.__init__(self, parent)
        Lexer.__init__(self)

        self.streamCommentString = {"start": "<!-- ", "end": " -->"}

        self.keywordSetDescriptions = [
            self.tr("HTML elements and attributes"),
            self.tr("JavaScript keywords"),
            self.tr("VBScript keywords"),
            self.tr("Python keywords"),
            self.tr("PHP keywords"),
            self.tr("SGML and DTD keywords"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        self.setFoldPreprocessor(Preferences.getEditor("HtmlFoldPreprocessor"))
        self.setCaseSensitiveTags(Preferences.getEditor("HtmlCaseSensitiveTags"))
        self.setFoldCompact(Preferences.getEditor("AllFoldCompact"))
        with contextlib.suppress(AttributeError):
            self.setFoldScriptComments(Preferences.getEditor("HtmlFoldScriptComments"))
            self.setFoldScriptHeredocs(Preferences.getEditor("HtmlFoldScriptHeredocs"))
        with contextlib.suppress(AttributeError):
            self.setDjangoTemplates(Preferences.getEditor("HtmlDjangoTemplates"))
            self.setMakoTemplates(Preferences.getEditor("HtmlMakoTemplates"))

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [
            QsciLexerHTML.HTMLComment,
            QsciLexerHTML.ASPXCComment,
            QsciLexerHTML.SGMLComment,
            QsciLexerHTML.SGMLParameterComment,
            QsciLexerHTML.JavaScriptComment,
            QsciLexerHTML.JavaScriptCommentDoc,
            QsciLexerHTML.JavaScriptCommentLine,
            QsciLexerHTML.ASPJavaScriptComment,
            QsciLexerHTML.ASPJavaScriptCommentDoc,
            QsciLexerHTML.ASPJavaScriptCommentLine,
            QsciLexerHTML.VBScriptComment,
            QsciLexerHTML.ASPVBScriptComment,
            QsciLexerHTML.PythonComment,
            QsciLexerHTML.ASPPythonComment,
            QsciLexerHTML.PHPComment,
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
            QsciLexerHTML.HTMLDoubleQuotedString,
            QsciLexerHTML.HTMLSingleQuotedString,
            QsciLexerHTML.SGMLDoubleQuotedString,
            QsciLexerHTML.SGMLSingleQuotedString,
            QsciLexerHTML.JavaScriptDoubleQuotedString,
            QsciLexerHTML.JavaScriptSingleQuotedString,
            QsciLexerHTML.JavaScriptUnclosedString,
            QsciLexerHTML.ASPJavaScriptDoubleQuotedString,
            QsciLexerHTML.ASPJavaScriptSingleQuotedString,
            QsciLexerHTML.ASPJavaScriptUnclosedString,
            QsciLexerHTML.VBScriptString,
            QsciLexerHTML.VBScriptUnclosedString,
            QsciLexerHTML.ASPVBScriptString,
            QsciLexerHTML.ASPVBScriptUnclosedString,
            QsciLexerHTML.PythonDoubleQuotedString,
            QsciLexerHTML.PythonSingleQuotedString,
            QsciLexerHTML.PythonTripleDoubleQuotedString,
            QsciLexerHTML.PythonTripleSingleQuotedString,
            QsciLexerHTML.ASPPythonDoubleQuotedString,
            QsciLexerHTML.ASPPythonSingleQuotedString,
            QsciLexerHTML.ASPPythonTripleDoubleQuotedString,
            QsciLexerHTML.ASPPythonTripleSingleQuotedString,
            QsciLexerHTML.PHPDoubleQuotedString,
            QsciLexerHTML.PHPSingleQuotedString,
        ]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerHTML.keywords(self, kwSet)


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerHTML
    """
    return LexerHTML(parent=parent)
