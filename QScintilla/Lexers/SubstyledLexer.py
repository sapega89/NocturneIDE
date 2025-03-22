# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the lexer mixin class.
"""

import copy

from PyQt6.QtGui import QColor

from eric7 import EricUtilities, Preferences

from .Lexer import Lexer


class SubstyledLexer(Lexer):
    """
    Class to implement the sub-styled lexer mixin class.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.baseStyles = []
        # list of style numbers, that support sub-styling
        self.defaultSubStyles = {}
        # dictionary with sub-styling data
        # main key: base style number, value : dict with
        #       key: sub-style number, value: dict with
        #           'Description': string containing a short description
        #           'Words': string of whitespace separated words to be styled
        #           'Style': dictionary with styling data (only difference to
        #                    the base style is required
        #               'fore': foreground color (int containing RGB values)
        #               'paper': background color (int containing RGB values)
        #               'eolfill': fill to eol (bool)
        #               'font_family': font family (str)
        #               'font_size: point size (int)
        #               'font_bold: bold font (bool)
        #               'font_italic: italic font (bool)
        #               'font_underline: underlined font (bool)

        self.__subStyles = {}
        self.__subStylesInitialized = False

    def loadAllDefaultSubStyles(self):
        """
        Public method to load the default sub-style definitions.
        """
        self.__subStyles = copy.deepcopy(self.defaultSubStyles)

        self.__subStylesInitialized = True

    def loadDefaultSubStyles(self, style):
        """
        Public method to load the default sub-styles for a given base style.

        @param style style number
        @type int
        """
        if style in self.defaultSubStyles:
            self.__subStyles[style] = copy.deepcopy(self.defaultSubStyles[style])

    def loadSubstyles(self):
        """
        Public method to load the sub-styles from the settings file.
        """
        settings = Preferences.getSettings()

        # Step 1: check if sub-styles were defined and saved
        subStylesDefined = False
        for baseStyle in self.baseStyles:
            key = "Scintilla/{0}/style{1}/SubStyleLength".format(
                self.language(), baseStyle
            )
            subStylesDefined |= settings.contains(key)
        # Step 2.1: load default sub-styles, if none were defined
        if not subStylesDefined:
            self.loadAllDefaultSubStyles()

        # Step 2.2: load from settings file
        else:
            self.__subStyles = {}
            for baseStyle in self.baseStyles:
                key = "Scintilla/{0}/style{1}/SubStyleLength".format(
                    self.language(), baseStyle
                )
                if settings.contains(key):
                    subStyleLength = int(settings.value(key))
                    if subStyleLength:
                        self.__subStyles[baseStyle] = {}
                        for subStyle in range(subStyleLength):
                            substyleKey = (
                                "Scintilla/{0}/style{1}/substyle{2}/"
                            ).format(self.language(), baseStyle, subStyle)
                            if settings.contains(substyleKey + "Description"):
                                subStyleData = {
                                    "Description": settings.value(
                                        substyleKey + "Description", ""
                                    ),
                                    "Words": settings.value(substyleKey + "Words", ""),
                                }

                                style = {}
                                key = substyleKey + "fore"
                                if settings.contains(key):
                                    style["fore"] = int(settings.value(key))
                                key = substyleKey + "paper"
                                if settings.contains(key):
                                    style["paper"] = int(settings.value(key))
                                key = substyleKey + "eolfill"
                                if settings.contains(key):
                                    style["eolfill"] = EricUtilities.toBool(
                                        settings.value(key)
                                    )
                                key = substyleKey + "font_family"
                                if settings.contains(key):
                                    style["font_family"] = settings.value(key)
                                key = substyleKey + "font_size"
                                if settings.contains(key):
                                    style["font_size"] = int(settings.value(key))
                                key = substyleKey + "font_bold"
                                if settings.contains(key):
                                    style["font_bold"] = EricUtilities.toBool(
                                        settings.value(key)
                                    )
                                key = substyleKey + "font_italic"
                                if settings.contains(key):
                                    style["font_italic"] = EricUtilities.toBool(
                                        settings.value(key)
                                    )
                                key = substyleKey + "font_underline"
                                if settings.contains(key):
                                    style["font_underline"] = EricUtilities.toBool(
                                        settings.value(key)
                                    )

                                subStyleData["Style"] = style

                                self.__subStyles[baseStyle][subStyle] = subStyleData

                            else:
                                # initialize with default
                                self.__subStyles[baseStyle][subStyle] = copy.deepcopy(
                                    self.defaultSubStyles[baseStyle][subStyle]
                                )

        self.__subStylesInitialized = True

    def readSubstyles(self, editor):
        """
        Public method to load the sub-styles and configure the editor.

        @param editor reference to the editor object
        @type QsciScintilla
        """
        subStyleBasesLength = editor.SendScintilla(editor.SCI_GETSUBSTYLEBASES, 0, None)
        if not subStyleBasesLength:
            # lexer does not support sub-styling
            return

        self.loadSubstyles()

        # free existing sub-styles first
        editor.SendScintilla(editor.SCI_FREESUBSTYLES)
        subStyleBases = b"\00" * (subStyleBasesLength + 1)
        editor.SendScintilla(editor.SCI_GETSUBSTYLEBASES, 0, subStyleBases)
        distanceToSecondary = editor.SendScintilla(editor.SCI_DISTANCETOSECONDARYSTYLES)

        subStyleBases = list(bytearray(subStyleBases[:-1]))
        if distanceToSecondary:
            subStyleBases.extend(b + distanceToSecondary for b in subStyleBases[:])
        for baseStyleNo in subStyleBases:
            if baseStyleNo in self.__subStyles:
                subStylesData = self.__subStyles[baseStyleNo]
                subStyleLength = len(subStylesData)
                subStyleStart = editor.SendScintilla(
                    editor.SCI_ALLOCATESUBSTYLES, baseStyleNo, subStyleLength
                )
                if subStyleStart < 0:
                    continue

                for subStyleIndex, subStyleKey in enumerate(sorted(subStylesData)):
                    styleNo = subStyleStart + subStyleIndex
                    subStyle = subStylesData[subStyleKey]
                    # set the words
                    editor.SendScintilla(
                        editor.SCI_SETIDENTIFIERS, styleNo, subStyle["Words"].encode()
                    )

                    # set the style
                    style = subStyle["Style"]
                    color = (
                        QColor(
                            style["fore"] >> 16 & 0xFF,
                            style["fore"] >> 8 & 0xFF,
                            style["fore"] & 0xFF,
                        )
                        if "fore" in style
                        else self.color(baseStyleNo)
                    )
                    self.setColor(color, styleNo)

                    color = (
                        QColor(
                            style["paper"] >> 16 & 0xFF,
                            style["paper"] >> 8 & 0xFF,
                            style["paper"] & 0xFF,
                        )
                        if "paper" in style
                        else self.paper(baseStyleNo)
                    )
                    self.setPaper(color, styleNo)

                    eolFill = (
                        style["eolfill"]
                        if "eolfill" in style
                        else self.eolFill(baseStyleNo)
                    )
                    self.setEolFill(eolFill, styleNo)

                    font = self.font(baseStyleNo)
                    if "font_family" in style:
                        font.setFamily(style["font_family"])
                    if "font_size" in style:
                        font.setPointSize(style["font_size"])
                    if "font_bold" in style:
                        font.setBold(style["font_bold"])
                    if "font_italic" in style:
                        font.setItalic(style["font_italic"])
                    if "font_underline" in style:
                        font.setUnderline(style["font_underline"])
                    self.setFont(font, styleNo)

    def writeSubstyles(self):
        """
        Public method to save the sub-styles.
        """
        if not self.__subStylesInitialized:
            return

        settings = Preferences.getSettings()

        # Step 1: remove all sub-style definitions first
        for baseStyle in self.baseStyles:
            key = "Scintilla/{0}/style{1}/SubStyleLength".format(
                self.language(), baseStyle
            )
            if settings.contains(key):
                subStyleLength = int(settings.value(key))
                if subStyleLength:
                    for subStyle in range(subStyleLength):
                        substyleKey = ("Scintilla/{0}/style{1}/substyle{2}/").format(
                            self.language(), baseStyle, subStyle
                        )
                        settings.remove(substyleKey)

        # Step 2: save the defined sub-styles
        for baseStyle in self.baseStyles:
            key = "Scintilla/{0}/style{1}/SubStyleLength".format(
                self.language(), baseStyle
            )
            settings.setValue(key, len(self.__subStyles[baseStyle]))
            for subStyleIndex, subStyle in enumerate(
                sorted(self.__subStyles[baseStyle])
            ):
                substyleKey = "Scintilla/{0}/style{1}/substyle{2}/".format(
                    self.language(), baseStyle, subStyleIndex
                )
                subStyleData = self.__subStyles[baseStyle][subStyle]

                if not subStyleData["Description"] and not subStyleData["Words"]:
                    # invalid or incomplete sub-style definition
                    continue

                settings.setValue(
                    substyleKey + "Description", subStyleData["Description"]
                )
                settings.setValue(substyleKey + "Words", subStyleData["Words"])

                style = subStyleData["Style"]
                if "fore" in style:
                    color = style["fore"]
                else:
                    col = self.color(baseStyle)
                    color = col.red() << 16 | col.green() << 8 | col.blue()
                settings.setValue(substyleKey + "fore", color)
                if "paper" in style:
                    color = style["paper"]
                else:
                    col = self.paper(baseStyle)
                    color = col.red() << 16 | col.green() << 8 | col.blue()
                settings.setValue(substyleKey + "paper", color)
                eolfill = style.get("eolfill", self.eolFill(baseStyle))
                settings.setValue(substyleKey + "eolfill", eolfill)
                font = self.font(baseStyle)
                family = style.get("font_family", font.family())
                settings.setValue(substyleKey + "font_family", family)
                size = style.get("font_size", font.pointSize())
                settings.setValue(substyleKey + "font_size", size)
                bold = style.get("font_bold", font.bold())
                settings.setValue(substyleKey + "font_bold", bold)
                italic = style.get("font_italic", font.italic())
                settings.setValue(substyleKey + "font_italic", italic)
                underline = (
                    style["font_underline"]
                    if "font_underline" in style
                    else font.underline()
                )
                settings.setValue(substyleKey + "font_underline", underline)

    def hasSubstyles(self):
        """
        Public method to indicate the support of sub-styles.

        @return flag indicating sub-styling support
        @rtype bool
        """
        return True

    def getBaseStyles(self):
        """
        Public method to get the list of supported base styles.

        @return list of base styles
        @rtype list of int
        """
        return self.baseStyles[:]

    def substylesCount(self, style):
        """
        Public method to get the number of defined sub-styles.

        @param style base style number
        @type int
        @return number of defined sub-styles
        @rtype int
        """
        count = len(self.__subStyles[style]) if style in self.__subStyles else 0

        return count

    def setSubstyleDescription(self, description, style, substyle):
        """
        Public method to set the description for a sub-style.

        @param description description to be set
        @type str
        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        """
        if style in self.__subStyles and substyle in self.__subStyles[style]:
            self.__subStyles[style][substyle]["Description"] = description.strip()

    def substyleDescription(self, style, substyle):
        """
        Public method to get the description of a sub-style.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return sub-style description
        @rtype str
        """
        desc = (
            self.__subStyles[style][substyle]["Description"].strip()
            if (style in self.__subStyles and substyle in self.__subStyles[style])
            else ""
        )

        return desc

    def setSubstyleWords(self, words, style, substyle):
        """
        Public method to set the words for a sub-style.

        @param words words to be set separated by white-space
        @type str
        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        """
        if style in self.__subStyles and substyle in self.__subStyles[style]:
            self.__subStyles[style][substyle]["Words"] = words.strip()

    def substyleWords(self, style, substyle):
        """
        Public method to get the words of a sub-style.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return white-space separated word list
        @rtype str
        """
        words = (
            self.__subStyles[style][substyle]["Words"].strip()
            if (style in self.__subStyles and substyle in self.__subStyles[style])
            else ""
        )

        return words

    def setSubstyleColor(self, color, style, substyle):
        """
        Public method to set the foreground color of a sub-style.

        @param color foreground color to be set
        @type QColor
        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        """
        if style in self.__subStyles and substyle in self.__subStyles[style]:
            self.__subStyles[style][substyle]["Style"]["fore"] = (
                color.red() << 16 | color.green() << 8 | color.blue()
            )

    def substyleColor(self, style, substyle):
        """
        Public method to get the sub-style foreground color.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return foreground color
        @rtype QColor
        """
        color = self.color(style)

        if style in self.__subStyles and substyle in self.__subStyles[style]:
            styleData = self.__subStyles[style][substyle]["Style"]
            if "fore" in styleData:
                color = QColor(
                    styleData["fore"] >> 16 & 0xFF,
                    styleData["fore"] >> 8 & 0xFF,
                    styleData["fore"] & 0xFF,
                )

        return color

    def setSubstylePaper(self, color, style, substyle):
        """
        Public method to set the background color of a sub-style.

        @param color background color to be set
        @type QColor
        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        """
        if style in self.__subStyles and substyle in self.__subStyles[style]:
            self.__subStyles[style][substyle]["Style"]["paper"] = (
                color.red() << 16 | color.green() << 8 | color.blue()
            )

    def substylePaper(self, style, substyle):
        """
        Public method to get the sub-style background color.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return background color
        @rtype QColor
        """
        color = self.paper(style)

        if style in self.__subStyles and substyle in self.__subStyles[style]:
            styleData = self.__subStyles[style][substyle]["Style"]
            if "paper" in styleData:
                color = QColor(
                    styleData["paper"] >> 16 & 0xFF,
                    styleData["paper"] >> 8 & 0xFF,
                    styleData["paper"] & 0xFF,
                )

        return color

    def setSubstyleEolFill(self, eolFill, style, substyle):
        """
        Public method to set the eolfill flag of a sub-style.

        @param eolFill eolfill flag to be set
        @type bool
        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        """
        if style in self.__subStyles and substyle in self.__subStyles[style]:
            self.__subStyles[style][substyle]["Style"]["eolfill"] = eolFill

    def substyleEolFill(self, style, substyle):
        """
        Public method to get the eolfill flag.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return eolfill flag
        @rtype bool
        """
        eolFill = self.eolFill(style)

        if style in self.__subStyles and substyle in self.__subStyles[style]:
            styleData = self.__subStyles[style][substyle]["Style"]
            eolFill = styleData.get("eolfill", self.eolFill(style))

        return eolFill

    def setSubstyleFont(self, font, style, substyle):
        """
        Public method to set the font of a sub-style.

        @param font font to be set
        @type QFont
        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        """
        if style in self.__subStyles and substyle in self.__subStyles[style]:
            self.__subStyles[style][substyle]["Style"]["font_family"] = font.family()
            self.__subStyles[style][substyle]["Style"]["font_size"] = font.pointSize()
            self.__subStyles[style][substyle]["Style"]["font_bold"] = font.bold()
            self.__subStyles[style][substyle]["Style"]["font_italic"] = font.italic()
            self.__subStyles[style][substyle]["Style"][
                "font_underline"
            ] = font.underline()

    def substyleFont(self, style, substyle):
        """
        Public method to get the sub-style font.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return font
        @rtype QFont
        """
        font = self.font(style)

        if style in self.__subStyles and substyle in self.__subStyles[style]:
            styleData = self.__subStyles[style][substyle]["Style"]
            if "font_family" in styleData:
                font.setFamily(styleData["font_family"])
            if "font_size" in styleData:
                font.setPointSize(styleData["font_size"])
            if "font_bold" in styleData:
                font.setBold(styleData["font_bold"])
            if "font_italic" in styleData:
                font.setItalic(styleData["font_italic"])
            if "font_underline" in styleData:
                font.setUnderline(styleData["font_underline"])

        return font

    def substyleDefaultDescription(self, style, substyle):
        """
        Public method to get the default description of a sub-style.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return sub-style default description
        @rtype str
        """
        description = ""

        if style in self.defaultSubStyles and substyle in self.defaultSubStyles[style]:
            substyleData = self.defaultSubStyles[style][substyle]
            description = substyleData["Description"].strip()

        return description

    def substyleDefaultWords(self, style, substyle):
        """
        Public method to get the default words of a sub-style.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return white-space separated default word list
        @rtype str
        """
        words = ""

        if style in self.defaultSubStyles and substyle in self.defaultSubStyles[style]:
            substyleData = self.defaultSubStyles[style][substyle]
            words = substyleData["Words"].strip()

        return words

    def substyleDefaultColor(self, style, substyle):
        """
        Public method to get the sub-style default foreground color.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return default foreground color
        @rtype QColor
        """
        color = self.defaultColor(style)

        if style in self.defaultSubStyles and substyle in self.defaultSubStyles[style]:
            styleData = self.defaultSubStyles[style][substyle]["Style"]
            if "fore" in styleData:
                color = QColor(
                    styleData["fore"] >> 16 & 0xFF,
                    styleData["fore"] >> 8 & 0xFF,
                    styleData["fore"] & 0xFF,
                )

        return color

    def substyleDefaultPaper(self, style, substyle):
        """
        Public method to get the sub-style default background color.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return default background color
        @rtype QColor
        """
        color = self.defaultPaper(style)

        if style in self.defaultSubStyles and substyle in self.defaultSubStyles[style]:
            styleData = self.defaultSubStyles[style][substyle]["Style"]
            if "paper" in styleData:
                color = QColor(
                    styleData["paper"] >> 16 & 0xFF,
                    styleData["paper"] >> 8 & 0xFF,
                    styleData["paper"] & 0xFF,
                )

        return color

    def substyleDefaultEolFill(self, style, substyle):
        """
        Public method to get the default eolfill flag.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return default eolfill flag
        @rtype bool
        """
        eolFill = self.defaultEolFill(style)

        if style in self.defaultSubStyles and substyle in self.defaultSubStyles[style]:
            styleData = self.defaultSubStyles[style][substyle]["Style"]
            eolFill = styleData.get("eolfill", self.defaultEolFill(style))

        return eolFill

    def substyleDefaultFont(self, style, substyle):
        """
        Public method to get the default sub-style font.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return default font
        @rtype QFont
        """
        font = self.defaultFont(style)

        if style in self.defaultSubStyles and substyle in self.defaultSubStyles[style]:
            styleData = self.defaultSubStyles[style][substyle]["Style"]
            if "font_family" in styleData:
                font.setFamily(styleData["font_family"])
            if "font_size" in styleData:
                font.setPointSize(styleData["font_size"])
            if "font_bold" in styleData:
                font.setBold(styleData["font_bold"])
            if "font_italic" in styleData:
                font.setItalic(styleData["font_italic"])
            if "font_underline" in styleData:
                font.setUnderline(styleData["font_underline"])

        return font

    def addSubstyle(self, style):
        """
        Public method to add an empty sub-style to a given base style.

        @param style base style number
        @type int
        @return allocated sub-style number or -1 to indicate an error
        @rtype int
        """
        if style in self.__subStyles:
            lastSubStyle = sorted(self.__subStyles[style])[-1]
            subStyle = lastSubStyle + 1
            self.__subStyles[style][subStyle] = {
                "Description": "",
                "Words": "",
                "Style": {},
            }
        else:
            subStyle = -1

        return subStyle

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
        ok = False

        if style in self.__subStyles and substyle in self.__subStyles[style]:
            del self.__subStyles[style][substyle]
            ok = True

        return ok

    def hasSubstyle(self, style, substyle):
        """
        Public method to test for a given sub-style definition.

        @param style base style number
        @type int
        @param substyle sub-style number
        @type int
        @return flag indicating the existence of a sub-style definition
        @rtype bool
        """
        return style in self.__subStyles and substyle in self.__subStyles[style]

    def isBaseStyle(self, style):
        """
        Public method to test, if a given style may have sub-styles.

        @param style base style number
        @type int
        @return flag indicating that the style may have sub-styles
        @rtype bool
        """
        return style in self.baseStyles
