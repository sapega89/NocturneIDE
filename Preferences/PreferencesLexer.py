# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a special QScintilla lexer to handle the preferences.
"""

from PyQt6.Qsci import QsciScintillaBase
from PyQt6.QtCore import QCoreApplication, QObject

from eric7 import Preferences
from eric7.QScintilla import Lexers
from eric7.SystemUtilities import OSUtilities


class PreferencesLexerError(Exception):
    """
    Class defining a special error for the PreferencesLexer class.
    """

    def __init__(self):
        """
        Constructor
        """
        self._errorMessage = QCoreApplication.translate(
            "PreferencesLexerError", "Unspecific PreferencesLexer error."
        )

    def __repr__(self):
        """
        Special method returning a representation of the exception.

        @return string representing the error message
        @rtype str
        """
        return repr(self._errorMessage)

    def __str__(self):
        """
        Special method returning a string representation of the exception.

        @return string representing the error message
        @rtype str
        """
        return self._errorMessage


class PreferencesLexerLanguageError(PreferencesLexerError):
    """
    Class defining a special error for the PreferencesLexer class.
    """

    def __init__(self, language):
        """
        Constructor

        @param language lexer language
        @type str
        """
        PreferencesLexerError.__init__(self)
        self._errorMessage = QCoreApplication.translate(
            "PreferencesLexerError", "Unsupported Lexer Language: {0}"
        ).format(language)


class PreferencesLexer(QObject):
    """
    Class implementing a Lexer facade for the highlighting styles
    configuration.
    """

    def __init__(self, language, parent=None):
        """
        Constructor

        @param language language of the lexer
        @type str
        @param parent parent widget of this lexer
        @type QWidget
        @exception PreferencesLexerLanguageError raised to indicate an invalid
            lexer language
        """
        super().__init__(parent)

        # These default font families are taken from eric7.QScintilla
        if OSUtilities.isWindowsPlatform():
            self.__defaultFontFamily = "Courier New"
        elif OSUtilities.isMacPlatform():
            self.__defaultFontFamily = "Courier"
        else:
            self.__defaultFontFamily = "Bitstream Vera Sans Mono"

        # instantiate a lexer object for the given language
        self.__lex = Lexers.getLexer(language)
        if self.__lex is None:
            raise PreferencesLexerLanguageError(language)

        # read the last stored values from preferences file
        self.__lex.readSettings(Preferences.getSettings(), "Scintilla")
        if self.__lex.hasSubstyles():
            self.__lex.loadSubstyles()

    def writeSettings(self):
        """
        Public method to write the lexer settings.
        """
        self.__lex.writeSettings(Preferences.getSettings(), "Scintilla")
        if self.__lex.hasSubstyles():
            self.__lex.writeSubstyles()

    def getStyles(self):
        """
        Public method to get a list of all supported styles.

        @return list of tuples each containing the description of the style,
            style number and sub-style number (or -1 for no sub-style)
        @rtype list of tuples of (str, int, int)
        """
        styles = []

        for i in range(QsciScintillaBase.STYLE_MAX):
            desc = self.__lex.description(i)
            if desc:
                styles.append((desc, i, -1))
        if self.__lex.hasSubstyles():
            for baseStyle in self.__lex.getBaseStyles():
                for subStyle in range(self.__lex.substylesCount(baseStyle)):
                    desc = self.__lex.substyleDescription(baseStyle, subStyle)
                    styles.append((desc, baseStyle, subStyle))

        return styles

    def getSubStyles(self, style):
        """
        Public method to get a list of all sub-styles of a style.

        @param style style number
        @type int
        @return list of tuples each containing the description of the style,
            style number and sub-style number (or -1 for no sub-style)
        @rtype list of tuples of (str, int, int)
        """
        styles = []

        if self.isBaseStyle(style):
            for subStyle in range(self.__lex.substylesCount(style)):
                desc = self.__lex.substyleDescription(style, subStyle)
                styles.append((desc, style, subStyle))

        return styles

    def defaultColor(self, style, substyle=-1):
        """
        Public method to get the default color of a style.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @return default color
        @rtype QColor
        """
        color = (
            self.__lex.substyleDefaultColor(style, substyle)
            if substyle >= 0
            else self.__lex.defaultColor(style)
        )

        return color

    def color(self, style, substyle=-1):
        """
        Public method to get the color of a style.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @return color
        @rtype QColor
        """
        color = (
            self.__lex.substyleColor(style, substyle)
            if substyle >= 0
            else self.__lex.color(style)
        )

        return color

    def setColor(self, c, style, substyle=-1):
        """
        Public method to set the color for a style.

        @param c color
        @type QColor
        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        """
        if substyle >= 0:
            self.__lex.setSubstyleColor(c, style, substyle)
        else:
            self.__lex.setColor(c, style)

    def defaultPaper(self, style, substyle=-1):
        """
        Public method to get the default background for a style.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @return default background color
        @rtype QColor
        """
        color = (
            self.__lex.substyleDefaultPaper(style, substyle)
            if substyle >= 0
            else self.__lex.defaultPaper(style)
        )

        return color

    def paper(self, style, substyle=-1):
        """
        Public method to get the background for a style.

        @param style the style number
        @type int
        @param substyle sub-style number
        @type int
        @return background color
        @rtype QColor
        """
        color = (
            self.__lex.substylePaper(style, substyle)
            if substyle >= 0
            else self.__lex.paper(style)
        )

        return color

    def setPaper(self, c, style, substyle=-1):
        """
        Public method to set the background for a style.

        @param c background color
        @type QColor
        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        """
        if substyle >= 0:
            self.__lex.setSubstylePaper(c, style, substyle)
        else:
            self.__lex.setPaper(c, style)

    def defaultEolFill(self, style, substyle=-1):
        """
        Public method to get the default eolFill flag for a style.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @return default eolFill flag
        @rtype bool
        """
        eolFill = (
            self.__lex.substyleDefaultEolFill(style, substyle)
            if substyle >= 0
            else self.__lex.defaultEolFill(style)
        )

        return eolFill

    def eolFill(self, style, substyle=-1):
        """
        Public method to get the eolFill flag for a style.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @return eolFill flag
        @rtype bool
        """
        eolFill = (
            self.__lex.substyleEolFill(style, substyle)
            if substyle >= 0
            else self.__lex.eolFill(style)
        )

        return eolFill

    def setEolFill(self, eolfill, style, substyle=-1):
        """
        Public method to set the eolFill flag for a style.

        @param eolfill eolFill flag
        @type bool
        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        """
        if substyle >= 0:
            self.__lex.setSubstyleEolFill(eolfill, style, substyle)
        else:
            self.__lex.setEolFill(eolfill, style)

    def defaultFont(self, style, substyle=-1):
        """
        Public method to get the default font for a style.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @return default font
        @rtype QFont
        """
        font = (
            self.__lex.substyleDefaultFont(style, substyle)
            if substyle >= 0
            else self.__lex.defaultFont(style)
        )

        return font

    def font(self, style, substyle=-1):
        """
        Public method to get the font for a style.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @return font
        @rtype QFont
        """
        font = (
            self.__lex.substyleFont(style, substyle)
            if substyle >= 0
            else self.__lex.font(style)
        )

        return font

    def setFont(self, f, style, substyle=-1):
        """
        Public method to set the font for a style.

        @param f font
        @type QFont
        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        """
        if substyle >= 0:
            self.__lex.setSubstyleFont(f, style, substyle)
        else:
            self.__lex.setFont(f, style)

    def defaultWords(self, style, substyle=-1):
        """
        Public method to get the default list of words for a style.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @return whitespace separated default list of words
        @rtype str
        """
        words = (
            self.__lex.substyleDefaultWords(style, substyle) if substyle >= 0 else ""
        )

        return words

    def words(self, style, substyle=-1):
        """
        Public method to get the list of words for a style.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @return whitespace separated list of words
        @rtype str
        """
        words = self.__lex.substyleWords(style, substyle) if substyle >= 0 else ""

        return words

    def setWords(self, words, style, substyle=-1):
        """
        Public method to set the list of words for a style.

        @param words whitespace separated list of words
        @type str
        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        """
        if substyle >= 0:
            # only supported for sub-styles
            self.__lex.setSubstyleWords(words, style, substyle)

    def defaultDescription(self, style, substyle=-1):
        """
        Public method to get the default descriptive string for a style.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @return default description of the style
        @rtype str
        """
        desc = (
            self.__lex.substyleDefaultDescription(style, substyle)
            if substyle >= 0
            else
            # for base styles return the hard coded description
            self.__lex.description(style)
        )

        return desc

    def description(self, style, substyle=-1):
        """
        Public method to get a descriptive string for a style.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @return description of the style
        @rtype str
        """
        desc = (
            self.__lex.substyleDescription(style, substyle)
            if substyle >= 0
            else self.__lex.description(style)
        )

        return desc

    def setDescription(self, description, style, substyle=-1):
        """
        Public method to set a descriptive string for a style.

        @param description description for the style
        @type str
        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        """
        if substyle >= 0:
            # only supported for sub-styles
            self.__lex.setSubstyleDescription(description, style, substyle)

    def language(self):
        """
        Public method to get the lexers programming language.

        @return lexer programming language
        @rtype str
        """
        return self.__lex.language()

    def hasStyle(self, style, substyle):
        """
        Public method to test for a given style definition.

        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @return flag indicating the existence of a style definition
        @rtype bool
        """
        ok = self.__lex.hasSubstyle(style, substyle) if substyle >= 0 else True

        return ok

    def isBaseStyle(self, style):
        """
        Public method to test, if a given style may have sub-styles.

        @param style base style number
        @type int
        @return flag indicating that the style may have sub-styles
        @rtype bool
        """
        return self.__lex.hasSubstyles() and self.__lex.isBaseStyle(style)

    def addSubstyle(self, style):
        """
        Public method to add an empty sub-style to a given style.

        @param style style number
        @type int
        @return allocated sub-style number or -1 to indicate an error
        @rtype int
        """
        return self.__lex.addSubstyle(style)

    def delSubstyle(self, style, substyle):
        """
        Public method to delete a given sub-style definition.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return flag indicating successful deletion
        @rtype bool
        """
        return self.__lex.delSubstyle(style, substyle)

    def loadDefaultSubStyles(self, style):
        """
        Public method to load the default sub-styles for a given base style.

        @param style style number
        @type int
        """
        self.__lex.loadDefaultSubStyles(style)
