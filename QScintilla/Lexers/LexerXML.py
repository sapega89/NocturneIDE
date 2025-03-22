# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a XML lexer with some additional methods.
"""

import contextlib

from PyQt6.Qsci import QsciLexerXML

from eric7 import Preferences

from .Lexer import Lexer


class LexerXML(Lexer, QsciLexerXML):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerXML.__init__(self, parent)
        Lexer.__init__(self)

        self.streamCommentString = {"start": "<!-- ", "end": " -->"}

        self.keywordSetDescriptions = [
            self.tr(""),
            self.tr(""),
            self.tr(""),
            self.tr(""),
            self.tr(""),
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
            self.setScriptsStyled(Preferences.getEditor("XMLStyleScripts"))

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [
            QsciLexerXML.HTMLComment,
            QsciLexerXML.ASPXCComment,
            QsciLexerXML.SGMLComment,
            QsciLexerXML.SGMLParameterComment,
            QsciLexerXML.JavaScriptComment,
            QsciLexerXML.JavaScriptCommentDoc,
            QsciLexerXML.JavaScriptCommentLine,
            QsciLexerXML.ASPJavaScriptComment,
            QsciLexerXML.ASPJavaScriptCommentDoc,
            QsciLexerXML.ASPJavaScriptCommentLine,
            QsciLexerXML.VBScriptComment,
            QsciLexerXML.ASPVBScriptComment,
            QsciLexerXML.PythonComment,
            QsciLexerXML.ASPPythonComment,
            QsciLexerXML.PHPComment,
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
            QsciLexerXML.HTMLDoubleQuotedString,
            QsciLexerXML.HTMLSingleQuotedString,
            QsciLexerXML.SGMLDoubleQuotedString,
            QsciLexerXML.SGMLSingleQuotedString,
            QsciLexerXML.JavaScriptDoubleQuotedString,
            QsciLexerXML.JavaScriptSingleQuotedString,
            QsciLexerXML.JavaScriptUnclosedString,
            QsciLexerXML.ASPJavaScriptDoubleQuotedString,
            QsciLexerXML.ASPJavaScriptSingleQuotedString,
            QsciLexerXML.ASPJavaScriptUnclosedString,
            QsciLexerXML.VBScriptString,
            QsciLexerXML.VBScriptUnclosedString,
            QsciLexerXML.ASPVBScriptString,
            QsciLexerXML.ASPVBScriptUnclosedString,
            QsciLexerXML.PythonDoubleQuotedString,
            QsciLexerXML.PythonSingleQuotedString,
            QsciLexerXML.PythonTripleDoubleQuotedString,
            QsciLexerXML.PythonTripleSingleQuotedString,
            QsciLexerXML.ASPPythonDoubleQuotedString,
            QsciLexerXML.ASPPythonSingleQuotedString,
            QsciLexerXML.ASPPythonTripleDoubleQuotedString,
            QsciLexerXML.ASPPythonTripleSingleQuotedString,
            QsciLexerXML.PHPDoubleQuotedString,
            QsciLexerXML.PHPSingleQuotedString,
        ]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        return QsciLexerXML.keywords(self, kwSet)


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerXML
    """
    return LexerXML(parent=parent)
