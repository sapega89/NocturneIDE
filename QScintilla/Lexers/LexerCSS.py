# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a CSS lexer with some additional methods.
"""

import contextlib

from PyQt6.Qsci import QsciLexerCSS

from eric7 import Preferences

from .Lexer import Lexer


class LexerCSS(Lexer, QsciLexerCSS):
    """
    Subclass to implement some additional lexer dependant methods.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget of this lexer
        @type QWidget
        """
        QsciLexerCSS.__init__(self, parent)
        Lexer.__init__(self)

        self.streamCommentString = {"start": "/* ", "end": " */"}

        self.keywordSetDescriptions = [
            self.tr("CSS1 Properties"),
            self.tr("Pseudo-Classes"),
            self.tr("CSS2 Properties"),
            self.tr("CSS3 Properties"),
            self.tr("Pseudo-Elements"),
            self.tr("Browser-Specific CSS Properties"),
            self.tr("Browser-Specific Pseudo-Classes"),
            self.tr("Browser-Specific Pseudo-Elements"),
        ]

    def initProperties(self):
        """
        Public slot to initialize the properties.
        """
        self.setFoldComments(Preferences.getEditor("CssFoldComment"))
        self.setFoldCompact(Preferences.getEditor("AllFoldCompact"))
        with contextlib.suppress(AttributeError):
            self.setHSSLanguage(Preferences.getEditor("CssHssSupport"))
            self.setLessLanguage(Preferences.getEditor("CssLessSupport"))
            self.setSCSSLanguage(Preferences.getEditor("CssSassySupport"))

    def isCommentStyle(self, style):
        """
        Public method to check, if a style is a comment style.

        @param style style to check
        @type int
        @return flag indicating a comment style
        @rtype bool
        """
        return style in [QsciLexerCSS.Comment]

    def isStringStyle(self, style):
        """
        Public method to check, if a style is a string style.

        @param style style to check
        @type int
        @return flag indicating a string style
        @rtype bool
        """
        return style in [
            QsciLexerCSS.DoubleQuotedString,
            QsciLexerCSS.SingleQuotedString,
        ]

    def defaultKeywords(self, kwSet):
        """
        Public method to get the default keywords.

        @param kwSet number of the keyword set
        @type int
        @return string giving the keywords or None
        @rtype str
        """
        if kwSet == 1:
            return (
                "color background-color background-image background-repeat"
                " background-attachment background-position background"
                " font-family font-style font-variant font-weight font-size"
                " font word-spacing letter-spacing text-decoration"
                " vertical-align text-transform text-align text-indent"
                " line-height margin-top margin-right margin-bottom"
                " margin-left margin padding-top padding-right padding-bottom"
                " padding-left padding border-top-width border-right-width"
                " border-bottom-width border-left-width border-width"
                " border-top border-right border-bottom border-left border"
                " border-color border-style width height float clear display"
                " white-space list-style-type list-style-image"
                " list-style-position list-style"
            )

        if kwSet == 2:
            return (
                "link active visited first-child focus hover lang left"
                " right first empty enabled disabled checked not root target"
                " only-child last-child nth-child nth-last-child first-of-type"
                " last-of-type nth-of-type nth-last-of-type only-of-type valid"
                " invalid required optional first-letter first-line before"
                " after"
            )

        if kwSet == 3:
            return (
                "border-top-color border-right-color border-bottom-color"
                " border-left-color border-color border-top-style"
                " border-right-style border-bottom-style border-left-style"
                " border-style top right bottom left position z-index"
                " direction unicode-bidi min-width max-width min-height"
                " max-height overflow clip visibility content quotes"
                " counter-reset counter-increment marker-offset size marks"
                " page-break-before page-break-after page-break-inside page"
                " orphans widows font-stretch font-size-adjust unicode-range"
                " units-per-em src panose-1 stemv stemh slope cap-height"
                " x-height ascent descent widths bbox definition-src baseline"
                " centerline mathline topline text-shadow caption-side"
                " table-layout border-collapse border-spacing empty-cells"
                " speak-header cursor outline outline-width outline-style"
                " outline-color volume speak pause-before pause-after pause"
                " cue-before cue-after cue play-during azimuth elevation"
                " speech-rate voice-family pitch pitch-range stress richness"
                " speak-punctuation speak-numeral"
            )

        if kwSet == 4:
            return (
                "background-size border-radius border-top-right-radius"
                " border-bottom-right-radius border-bottom-left-radius"
                " border-top-left-radius box-shadow columns column-width"
                " column-count column-rule column-gap column-rule-color"
                " column-rule-style column-rule-width resize opacity word-wrap"
            )

        if kwSet == 5:
            return "first-letter first-line before after selection"

        if kwSet == 6:
            return "^-moz- ^-webkit- ^-o- ^-ms- filter"

        if kwSet == 7:
            return "indeterminate default ^-moz- ^-webkit- ^-o- ^-ms-"

        if kwSet == 8:
            return "selection ^-moz- ^-webkit- ^-o- ^-ms-"

        return QsciLexerCSS.keywords(self, kwSet)


def createLexer(variant, parent=None):  # noqa: U100
    """
    Function to instantiate a lexer object.

    @param variant name of the language variant (unused)
    @type str
    @param parent parent widget of this lexer
    @type QObject
    @return instantiated lexer object
    @rtype LexerCSS
    """
    return LexerCSS(parent=parent)
