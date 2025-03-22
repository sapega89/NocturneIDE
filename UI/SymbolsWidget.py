# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to select a symbol in various formats.
"""

import html.entities
import sys
import unicodedata

from PyQt6.QtCore import (
    QAbstractTableModel,
    QItemSelectionModel,
    QLocale,
    QModelIndex,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QAbstractItemView, QHeaderView, QWidget

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp

from .Ui_SymbolsWidget import Ui_SymbolsWidget


class SymbolsModel(QAbstractTableModel):
    """
    Class implementing the model for the symbols widget.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__locale = QLocale()

        self.__headerData = [
            self.tr("Code"),
            self.tr("Char"),
            self.tr("Hex"),
            self.tr("HTML"),
            self.tr("Name"),
        ]

        self.__isDark = ericApp().usesDarkPalette()

        self.__tables = [
            # Source: https://www.unicode.org/Public/UCD/latest/ucd/Blocks.txt
            # first   last     display name
            (0x0, 0x1F, self.tr("Control Characters")),
            (0x20, 0x7F, self.tr("Basic Latin")),
            (0x80, 0xFF, self.tr("Latin-1 Supplement")),
            (0x100, 0x17F, self.tr("Latin Extended-A")),
            (0x180, 0x24F, self.tr("Latin Extended-B")),
            (0x250, 0x2AF, self.tr("IPA Extensions")),
            (0x2B0, 0x2FF, self.tr("Spacing Modifier Letters")),
            (0x300, 0x36F, self.tr("Combining Diacritical Marks")),
            (0x370, 0x3FF, self.tr("Greek and Coptic")),
            (0x400, 0x4FF, self.tr("Cyrillic")),
            (0x500, 0x52F, self.tr("Cyrillic Supplement")),
            (0x530, 0x58F, self.tr("Armenian")),
            (0x590, 0x5FF, self.tr("Hebrew")),
            (0x600, 0x6FF, self.tr("Arabic")),
            (0x700, 0x74F, self.tr("Syriac")),
            (0x780, 0x7BF, self.tr("Thaana")),
            (0x750, 0x77F, self.tr("Arabic Supplement")),
            (0x7C0, 0x7FF, self.tr("N'Ko")),
            (0x800, 0x83F, self.tr("Samaritan")),
            (0x840, 0x85F, self.tr("Mandaic")),
            (0x860, 0x86F, self.tr("Syriac Supplement")),
            (0x870, 0x89F, self.tr("Arabic Extended-B")),
            (0x8A0, 0x8FF, self.tr("Arabic Extended-A")),
            (0x900, 0x97F, self.tr("Devanagari")),
            (0x980, 0x9FF, self.tr("Bengali")),
            (0xA00, 0xA7F, self.tr("Gurmukhi")),
            (0xA80, 0xAFF, self.tr("Gujarati")),
            (0xB00, 0xB7F, self.tr("Oriya")),
            (0xB80, 0xBFF, self.tr("Tamil")),
            (0xC00, 0xC7F, self.tr("Telugu")),
            (0xC80, 0xCFF, self.tr("Kannada")),
            (0xD00, 0xD7F, self.tr("Malayalam")),
            (0xD80, 0xDFF, self.tr("Sinhala")),
            (0xE00, 0xE7F, self.tr("Thai")),
            (0xE80, 0xEFF, self.tr("Lao")),
            (0xF00, 0xFFF, self.tr("Tibetan")),
            (0x1000, 0x109F, self.tr("Myanmar")),
            (0x10A0, 0x10FF, self.tr("Georgian")),
            (0x1100, 0x11FF, self.tr("Hangul Jamo")),
            (0x1200, 0x137F, self.tr("Ethiopic")),
            (0x1380, 0x139F, self.tr("Ethiopic Supplement")),
            (0x13A0, 0x13FF, self.tr("Cherokee")),
            (0x1400, 0x167F, self.tr("Unified Canadian Aboriginal Syllabics")),
            (0x1680, 0x169F, self.tr("Ogham")),
            (0x16A0, 0x16FF, self.tr("Runic")),
            (0x1700, 0x171F, self.tr("Tagalog")),
            (0x1720, 0x173F, self.tr("Hanunoo")),
            (0x1740, 0x175F, self.tr("Buhid")),
            (0x1760, 0x177F, self.tr("Tagbanwa")),
            (0x1780, 0x17FF, self.tr("Khmer")),
            (0x1800, 0x18AF, self.tr("Mongolian")),
            (0x18B0, 0x18FF, self.tr("Unified Canadian Aboriginal Syllabics Extended")),
            (0x1900, 0x194F, self.tr("Limbu")),
            (0x1950, 0x197F, self.tr("Tai Le")),
            (0x1980, 0x19DF, self.tr("New Tai Lue")),
            (0x19E0, 0x19FF, self.tr("Khmer Symbols")),
            (0x1A00, 0x1A1F, self.tr("Buginese")),
            (0x1A20, 0x1AAF, self.tr("Tai Tham")),
            (0x1AB0, 0x1AFF, self.tr("Combining Diacritical Marks Extended")),
            (0x1B00, 0x1B7F, self.tr("Balinese")),
            (0x1B80, 0x1BBF, self.tr("Sundanese")),
            (0x1BC0, 0x1BFF, self.tr("Batak")),
            (0x1C00, 0x1C4F, self.tr("Lepcha")),
            (0x1C50, 0x1C7F, self.tr("Ol Chiki")),
            (0x1C80, 0x1C8F, self.tr("Cyrillic Extended-C")),
            (0x1C90, 0x1CBF, self.tr("Georgian Extended")),
            (0x1CC0, 0x1CCF, self.tr("Sundanese Supplement")),
            (0x1CD0, 0x1CFF, self.tr("Vedic Extensions")),
            (0x1D00, 0x1D7F, self.tr("Phonetic Extensions")),
            (0x1D80, 0x1DBF, self.tr("Phonetic Extensions Supplement")),
            (0x1DC0, 0x1DFF, self.tr("Combining Diacritical Marks Supplement")),
            (0x1E00, 0x1EFF, self.tr("Latin Extended Additional")),
            (0x1F00, 0x1FFF, self.tr("Greek Extended")),
            (0x2000, 0x206F, self.tr("General Punctuation")),
            (0x2070, 0x209F, self.tr("Superscripts and Subscripts")),
            (0x20A0, 0x20CF, self.tr("Currency Symbols")),
            (0x20D0, 0x20FF, self.tr("Combining Diacritical Marks")),
            (0x2100, 0x214F, self.tr("Letterlike Symbols")),
            (0x2150, 0x218F, self.tr("Number Forms")),
            (0x2190, 0x21FF, self.tr("Arrows")),
            (0x2200, 0x22FF, self.tr("Mathematical Operators")),
            (0x2300, 0x23FF, self.tr("Miscellaneous Technical")),
            (0x2400, 0x243F, self.tr("Control Pictures")),
            (0x2440, 0x245F, self.tr("Optical Character Recognition")),
            (0x2460, 0x24FF, self.tr("Enclosed Alphanumerics")),
            (0x2500, 0x257F, self.tr("Box Drawing")),
            (0x2580, 0x259F, self.tr("Block Elements")),
            (0x25A0, 0x25FF, self.tr("Geometric Shapes")),
            (0x2600, 0x26FF, self.tr("Miscellaneous Symbols")),
            (0x2700, 0x27BF, self.tr("Dingbats")),
            (0x27C0, 0x27EF, self.tr("Miscellaneous Mathematical Symbols-A")),
            (0x27F0, 0x27FF, self.tr("Supplement Arrows-A")),
            (0x2800, 0x28FF, self.tr("Braille Patterns")),
            (0x2900, 0x297F, self.tr("Supplement Arrows-B")),
            (0x2980, 0x29FF, self.tr("Miscellaneous Mathematical Symbols-B")),
            (0x2A00, 0x2AFF, self.tr("Supplemental Mathematical Operators")),
            (0x2B00, 0x2BFF, self.tr("Miscellaneous Symbols and Arcolumns")),
            (0x2C00, 0x2C5F, self.tr("Glagolitic")),
            (0x2C60, 0x2C7F, self.tr("Latin Extended-C")),
            (0x2C80, 0x2CFF, self.tr("Coptic")),
            (0x2D00, 0x2D2F, self.tr("Georgian Supplement")),
            (0x2D30, 0x2D7F, self.tr("Tifinagh")),
            (0x2D80, 0x2DDF, self.tr("Ethiopic Extended")),
            (0x2DE0, 0x2DFF, self.tr("Cyrillic Extended-A")),
            (0x2E00, 0x2E7F, self.tr("Supplemental Punctuation")),
            (0x2E80, 0x2EFF, self.tr("CJK Radicals Supplement")),
            (0x2F00, 0x2FDF, self.tr("KangXi Radicals")),
            (0x2FF0, 0x2FFF, self.tr("Ideographic Description Chars")),
            (0x3000, 0x303F, self.tr("CJK Symbols and Punctuation")),
            (0x3040, 0x309F, self.tr("Hiragana")),
            (0x30A0, 0x30FF, self.tr("Katakana")),
            (0x3100, 0x312F, self.tr("Bopomofo")),
            (0x3130, 0x318F, self.tr("Hangul Compatibility Jamo")),
            (0x3190, 0x319F, self.tr("Kanbun")),
            (0x31A0, 0x31BF, self.tr("Bopomofo Extended")),
            (0x31C0, 0x31EF, self.tr("CJK Strokes")),
            (0x31F0, 0x31FF, self.tr("Katakana Phonetic Extensions")),
            (0x3200, 0x32FF, self.tr("Enclosed CJK Letters and Months")),
            (0x3300, 0x33FF, self.tr("CJK Compatibility")),
            (0x3400, 0x4DBF, self.tr("CJK Unified Ideographs Extension A")),
            (0x4DC0, 0x4DFF, self.tr("Yijing Hexagram Symbols")),
            (0x4E00, 0x9FFF, self.tr("CJK Unified Ideographs")),
            (0xA000, 0xA48F, self.tr("Yi Syllables")),
            (0xA490, 0xA4CF, self.tr("Yi Radicals")),
            (0xA4D0, 0xA4FF, self.tr("Lisu")),
            (0xA500, 0xA63F, self.tr("Vai")),
            (0xA640, 0xA69F, self.tr("Cyrillic Extended-B")),
            (0xA6A0, 0xA6FF, self.tr("Bamum")),
            (0xA700, 0xA71F, self.tr("Modifier Tone Letters")),
            (0xA720, 0xA7FF, self.tr("Latin Extended-D")),
            (0xA800, 0xA82F, self.tr("Syloti Nagri")),
            (0xA830, 0xA83F, self.tr("Common Indic Number Forms")),
            (0xA840, 0xA87F, self.tr("Phags-pa")),
            (0xA880, 0xA8DF, self.tr("Saurashtra")),
            (0xA8E0, 0xA8FF, self.tr("Devanagari Extended")),
            (0xA900, 0xA92F, self.tr("Kayah Li")),
            (0xA930, 0xA95F, self.tr("Rejang")),
            (0xA960, 0xA97F, self.tr("Hangul Jamo Extended-A")),
            (0xA980, 0xA9DF, self.tr("Javanese")),
            (0xA9E0, 0xA9FF, self.tr("Myanmar Extended-B")),
            (0xAA00, 0xAA5F, self.tr("Cham")),
            (0xAA60, 0xAA7F, self.tr("Myanmar Extended-A")),
            (0xAA80, 0xAADF, self.tr("Tai Viet")),
            (0xAAE0, 0xAAFF, self.tr("Meetei Mayek Extensions")),
            (0xAB00, 0xAB2F, self.tr("Ethiopic Extended-A")),
            (0xAB30, 0xAB6F, self.tr("Latin Extended-E")),
            (0xAB70, 0xABBF, self.tr("Cherokee Supplement")),
            (0xABC0, 0xABFF, self.tr("Meetei Mayek")),
            (0xAC00, 0xD7AF, self.tr("Hangul Syllables")),
            (0xD7B0, 0xD7FF, self.tr("Hangul Jamo Extended-B")),
            (0xD800, 0xDB7F, self.tr("High Surrogates")),
            (0xDB80, 0xDBFF, self.tr("High Private Use Surrogates")),
            (0xDC00, 0xDFFF, self.tr("Low Surrogates")),
            (0xE000, 0xF8FF, self.tr("Private Use")),
            (0xF900, 0xFAFF, self.tr("CJK Compatibility Ideographs")),
            (0xFB00, 0xFB4F, self.tr("Alphabetic Presentation Forms")),
            (0xFB50, 0xFDFF, self.tr("Arabic Presentation Forms-A")),
            (0xFE00, 0xFE0F, self.tr("Variation Selectors")),
            (0xFE10, 0xFE1F, self.tr("Vertical Forms")),
            (0xFE20, 0xFE2F, self.tr("Combining Half Marks")),
            (0xFE30, 0xFE4F, self.tr("CJK Compatibility Forms")),
            (0xFE50, 0xFE6F, self.tr("Small Form Variants")),
            (0xFE70, 0xFEFF, self.tr("Arabic Presentation Forms-B")),
            (0xFF00, 0xFFEF, self.tr("Half- and Fullwidth Forms")),
            (0xFFF0, 0xFFFF, self.tr("Specials")),
        ]
        if sys.maxunicode > 0xFFFF:
            self.__tables.extend(
                [
                    (0x10000, 0x1007F, self.tr("Linear B Syllabary")),
                    (0x10080, 0x100FF, self.tr("Linear B Ideograms")),
                    (0x10100, 0x1013F, self.tr("Aegean Numbers")),
                    (0x10140, 0x1018F, self.tr("Ancient Greek Numbers")),
                    (0x10190, 0x101CF, self.tr("Ancient Symbols")),
                    (0x101D0, 0x101FF, self.tr("Phaistos Disc")),
                    (0x10280, 0x1029F, self.tr("Lycian")),
                    (0x102A0, 0x102DF, self.tr("Carian")),
                    (0x102E0, 0x102FF, self.tr("Coptic Epact Numbers")),
                    (0x10300, 0x1032F, self.tr("Old Italic")),
                    (0x10330, 0x1034F, self.tr("Gothic")),
                    (0x10350, 0x1037F, self.tr("Old Permic")),
                    (0x10380, 0x1039F, self.tr("Ugaritic")),
                    (0x103A0, 0x103DF, self.tr("Old Persian")),
                    (0x10400, 0x1044F, self.tr("Deseret")),
                    (0x10450, 0x1047F, self.tr("Shavian")),
                    (0x10480, 0x104AF, self.tr("Osmanya")),
                    (0x104B0, 0x104FF, self.tr("Osage")),
                    (0x10500, 0x1052F, self.tr("Elbasan")),
                    (0x10530, 0x1056F, self.tr("Caucasian Albanian")),
                    (0x10570, 0x105BF, self.tr("Vithkuqi")),
                    (0x10600, 0x1077F, self.tr("Linear A")),
                    (0x10780, 0x107BF, self.tr("Latin Extended-F")),
                    (0x10800, 0x1083F, self.tr("Cypriot Syllabary")),
                    (0x10840, 0x1085F, self.tr("Imperial Aramaic")),
                    (0x10860, 0x1087F, self.tr("Palmyrene")),
                    (0x10880, 0x108AF, self.tr("Nabataean")),
                    (0x108E0, 0x108FF, self.tr("Hatran")),
                    (0x10900, 0x1091F, self.tr("Phoenician")),
                    (0x10920, 0x1093F, self.tr("Lydian")),
                    (0x10980, 0x1099F, self.tr("Meroitic Hieroglyphs")),
                    (0x109A0, 0x109FF, self.tr("Meroitic Cursive")),
                    (0x10A00, 0x10A5F, self.tr("Kharoshthi")),
                    (0x10A60, 0x10A7F, self.tr("Old South Arabian")),
                    (0x10A80, 0x10A9F, self.tr("Old North Arabian")),
                    (0x10AC0, 0x10AFF, self.tr("Manichaean")),
                    (0x10B00, 0x10B3F, self.tr("Avestan")),
                    (0x10B40, 0x10B5F, self.tr("Inscriptional Parthian")),
                    (0x10B60, 0x10B7F, self.tr("Inscriptional Pahlavi")),
                    (0x10B80, 0x10BAF, self.tr("Psalter Pahlavi")),
                    (0x10C00, 0x10C4F, self.tr("Old Turkic")),
                    (0x10C80, 0x10CFF, self.tr("Old Hungarian")),
                    (0x10D00, 0x10D3F, self.tr("Hanifi Rohingya")),
                    (0x10E60, 0x10E7F, self.tr("Rumi Numeral Symbols")),
                    (0x10E80, 0x10EBF, self.tr("Yezidi")),
                    (0x10EC0, 0x10EFF, self.tr("Arabic Extended-C")),
                    (0x10F00, 0x10F2F, self.tr("Old Sogdian")),
                    (0x10F30, 0x10F6F, self.tr("Sogdian")),
                    (0x10F70, 0x10FAF, self.tr("Old Uyghur")),
                    (0x10FB0, 0x10FDF, self.tr("Chorasmian")),
                    (0x10FE0, 0x10FFF, self.tr("Elymaic")),
                    (0x11000, 0x1107F, self.tr("Brahmi")),
                    (0x11080, 0x110CF, self.tr("Kaithi")),
                    (0x110D0, 0x110FF, self.tr("Sora Sompeng")),
                    (0x11100, 0x1114F, self.tr("Chakma")),
                    (0x11150, 0x1117F, self.tr("Mahajani")),
                    (0x11180, 0x111DF, self.tr("Sharada")),
                    (0x111E0, 0x111FF, self.tr("Sinhala Archaic Numbers")),
                    (0x11200, 0x1124F, self.tr("Khojki")),
                    (0x11280, 0x112AF, self.tr("Multani")),
                    (0x112B0, 0x112FF, self.tr("Khudawadi")),
                    (0x11300, 0x1137F, self.tr("Grantha")),
                    (0x11400, 0x1147F, self.tr("Newa")),
                    (0x11480, 0x114DF, self.tr("Tirhuta")),
                    (0x11580, 0x115FF, self.tr("Siddham")),
                    (0x11600, 0x1165F, self.tr("Modi")),
                    (0x11660, 0x1167F, self.tr("Mongolian Supplement")),
                    (0x11680, 0x116CF, self.tr("Takri")),
                    (0x11700, 0x1174F, self.tr("Ahom")),
                    (0x11800, 0x1184F, self.tr("Dogra")),
                    (0x118A0, 0x118FF, self.tr("Warang Citi")),
                    (0x11900, 0x1195F, self.tr("Dives Akuru")),
                    (0x119A0, 0x119FF, self.tr("Nandinagari")),
                    (0x11A00, 0x11A4F, self.tr("Zanabazar Square")),
                    (0x11A50, 0x11AAF, self.tr("Soyombo")),
                    (
                        0x11AB0,
                        0x11ABF,
                        self.tr("Unified Canadian Aboriginal Syllabics Extended-A"),
                    ),
                    (0x11AC0, 0x11AFF, self.tr("Pau Cin Hau")),
                    (0x11B00, 0x11B5F, self.tr("Devanagari Extended-A")),
                    (0x11C00, 0x11C6F, self.tr("Bhaiksuki")),
                    (0x11C70, 0x11CBF, self.tr("Marchen")),
                    (0x11D00, 0x11D5F, self.tr("Masaram Gondi")),
                    (0x11D60, 0x11DAF, self.tr("Gunjala Gondi")),
                    (0x11EE0, 0x11EFF, self.tr("Makasar")),
                    (0x11F00, 0x11F5F, self.tr("Kawi")),
                    (0x11FB0, 0x11FBF, self.tr("Lisu Supplement")),
                    (0x11FC0, 0x11FFF, self.tr("Tamil Supplement")),
                    (0x12000, 0x123FF, self.tr("Cuneiform")),
                    (0x12400, 0x1247F, self.tr("Cuneiform Numbers and Punctuation")),
                    (0x12480, 0x1254F, self.tr("Early Dynastic Cuneiform")),
                    (0x12F90, 0x12FFF, self.tr("Cypro-Minoan")),
                    (0x13000, 0x1342F, self.tr("Egyptian Hieroglyphs")),
                    (0x13430, 0x1345F, self.tr("Egyptian Hieroglyph Format Controls")),
                    (0x14400, 0x1467F, self.tr("Anatolian Hieroglyphs")),
                    (0x16800, 0x16A3F, self.tr("Bamum Supplement")),
                    (0x16A40, 0x16A6F, self.tr("Mro")),
                    (0x16A70, 0x16ACF, self.tr("Tangsa")),
                    (0x16AD0, 0x16AFF, self.tr("Bassa Vah")),
                    (0x16B00, 0x16B8F, self.tr("Pahawh Hmong")),
                    (0x16E40, 0x16E9F, self.tr("Medefaidrin")),
                    (0x16F00, 0x16F9F, self.tr("Miao")),
                    (0x16FE0, 0x16FFF, self.tr("Ideographic Symbols and Punctuation")),
                    (0x17000, 0x187FF, self.tr("Tangut")),
                    (0x18800, 0x18AFF, self.tr("Tangut Components")),
                    (0x18B00, 0x18CFF, self.tr("Khitan Small Script")),
                    (0x18D00, 0x18D7F, self.tr("Tangut Supplement")),
                    (0x1AFF0, 0x1AFFF, self.tr("Kana Extended-B")),
                    (0x1B000, 0x1B0FF, self.tr("Kana Supplement")),
                    (0x1B100, 0x1B12F, self.tr("Kana Extended-A")),
                    (0x1B130, 0x1B16F, self.tr("Small Kana Extension")),
                    (0x1B170, 0x1B2FF, self.tr("Nushu")),
                    (0x1BC00, 0x1BC9F, self.tr("Duployan")),
                    (0x1BCA0, 0x1BCAF, self.tr("Shorthand Format Controls")),
                    (0x1CF00, 0x1CFCF, self.tr("Znamenny Musical Notation")),
                    (0x1D000, 0x1D0FF, self.tr("Byzantine Musical Symbols")),
                    (0x1D100, 0x1D1FF, self.tr("Musical Symbols")),
                    (0x1D200, 0x1D24F, self.tr("Ancient Greek Musical Notation")),
                    (0x1D2C0, 0x1D2DF, self.tr("Kaktovik Numerals")),
                    (0x1D2E0, 0x1D2FF, self.tr("Mayan Numerals")),
                    (0x1D300, 0x1D35F, self.tr("Tai Xuan Jing Symbols")),
                    (0x1D360, 0x1D37F, self.tr("Counting Rod Numerals")),
                    (0x1D400, 0x1D7FF, self.tr("Mathematical Alphanumeric Symbols")),
                    (0x1D800, 0x1DAAF, self.tr("Sutton SignWriting")),
                    (0x1DF00, 0x1DFFF, self.tr("Latin Extended-G")),
                    (0x1E000, 0x1E02F, self.tr("Glagolitic Supplement")),
                    (0x1E030, 0x1E08F, self.tr("Cyrillic Extended-D")),
                    (0x1E100, 0x1E14F, self.tr("Nyiakeng Puachue Hmong")),
                    (0x1E290, 0x1E2BF, self.tr("Toto")),
                    (0x1E2C0, 0x1E2FF, self.tr("Wancho")),
                    (0x1E4D0, 0x1E4FF, self.tr("Nag Mundari")),
                    (0x1E7E0, 0x1E7FF, self.tr("Ethiopic Extended-B")),
                    (0x1E800, 0x1E8DF, self.tr("Mende Kikakui")),
                    (0x1E900, 0x1E95F, self.tr("Adlam")),
                    (0x1EC70, 0x1ECBF, self.tr("Indic Siyaq Numbers")),
                    (0x1ED00, 0x1ED4F, self.tr("Ottoman Siyaq Numbers")),
                    (
                        0x1EE00,
                        0x1EEFF,
                        self.tr("Arabic Mathematical Alphabetic Symbols"),
                    ),
                    (0x1F000, 0x1F02F, self.tr("Mahjong Tiles")),
                    (0x1F030, 0x1F09F, self.tr("Domino Tiles")),
                    (0x1F0A0, 0x1F0FF, self.tr("Playing Cards")),
                    (0x1F100, 0x1F1FF, self.tr("Enclosed Alphanumeric Supplement")),
                    (0x1F200, 0x1F2FF, self.tr("Enclosed Ideographic Supplement")),
                    (
                        0x1F300,
                        0x1F5FF,
                        self.tr("Miscellaneous Symbols And Pictographs"),
                    ),
                    (0x1F600, 0x1F64F, self.tr("Emoticons")),
                    (0x1F650, 0x1F67F, self.tr("Ornamental Dingbats")),
                    (0x1F680, 0x1F6FF, self.tr("Transport And Map Symbols")),
                    (0x1F700, 0x1F77F, self.tr("Alchemical Symbols")),
                    (0x1F780, 0x1F7FF, self.tr("Geometric Shapes Extended")),
                    (0x1F800, 0x1F8FF, self.tr("Supplemental Arrows-C")),
                    (0x1F900, 0x1F9FF, self.tr("Supplemental Symbols and Pictographs")),
                    (0x1FA00, 0x1FA6F, self.tr("Chess Symbols")),
                    (0x1FA70, 0x1FAFF, self.tr("Symbols and Pictographs Extended-A")),
                    (0x1FB00, 0x1FBFF, self.tr("Symbols for Legacy Computing")),
                    (0x20000, 0x2A6DF, self.tr("CJK Unified Ideographs Extension B")),
                    (0x2A700, 0x2B73F, self.tr("CJK Unified Ideographs Extension C")),
                    (0x2B740, 0x2B81F, self.tr("CJK Unified Ideographs Extension D")),
                    (0x2B820, 0x2CEAF, self.tr("CJK Unified Ideographs Extension E")),
                    (0x2CEB0, 0x2EBEF, self.tr("CJK Unified Ideographs Extension F")),
                    (0x2EBF0, 0x2EE5F, self.tr("CJK Unified Ideographs Extension I")),
                    (0x2F800, 0x2FA1F, self.tr("CJK Compatapility Ideogr. Suppl.")),
                    (0x30000, 0x3134F, self.tr("CJK Unified Ideographs Extension G")),
                    (0x31350, 0x323AF, self.tr("CJK Unified Ideographs Extension H")),
                    (0xE0000, 0xE007F, self.tr("Tags")),
                    (0xE0100, 0xE01EF, self.tr("Variation Selectors Supplement")),
                    (0xF0000, 0xFFFFF, self.tr("Supplementary Private Use Area-A")),
                    (0x100000, 0x10FFFF, self.tr("Supplementary Private Use Area-B")),
                ]
            )
        self.__currentTableIndex = 0

    def getTableNames(self):
        """
        Public method to get a list of table names.

        @return list of table names
        @rtype list of str
        """
        return [table[2] for table in self.__tables]

    def getTableBoundaries(self, index):
        """
        Public method to get the first and last character position
        of the given table.

        @param index index of the character table
        @type int
        @return first and last character position
        @rtype tuple of (int, int)
        """
        return self.__tables[index][0], self.__tables[index][1]

    def getTableIndex(self):
        """
        Public method to get the current table index.

        @return current table index
        @rtype int
        """
        return self.__currentTableIndex

    def selectTable(self, index):
        """
        Public method to select the shown character table.

        @param index index of the character table
        @type int
        """
        self.beginResetModel()
        self.__currentTableIndex = index
        self.endResetModel()

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method to get header data from the model.

        @param section section number
        @type int
        @param orientation orientation
        @type Qt.Orientation
        @param role role of the data to retrieve
        @type Qt.ItemDataRole
        @return requested data
        @rtype Any
        """
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return self.__headerData[section]

        return QAbstractTableModel.headerData(self, section, orientation, role)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method to get data from the model.

        @param index index to get data for
        @type QModelIndex
        @param role role of the data to retrieve
        @type int
        @return requested data
        @rtype Any
        """
        symbolId = self.__tables[self.__currentTableIndex][0] + index.row()

        if role == Qt.ItemDataRole.DisplayRole:
            col = index.column()
            if col == 0:
                return self.__locale.toString(symbolId)
            elif col == 1:
                return chr(symbolId)
            elif col == 2:
                return "0x{0:04x}".format(symbolId)
            elif col == 3:
                if symbolId in html.entities.codepoint2name:
                    return "&{0};".format(html.entities.codepoint2name[symbolId])
            elif col == 4:
                return unicodedata.name(chr(symbolId), "").title()

        if role == Qt.ItemDataRole.BackgroundRole and index.column() == 0:
            if self.__isDark:
                return QColor("#4d4d4d")
            else:
                return QColor(Qt.GlobalColor.lightGray)

        if role == Qt.ItemDataRole.ForegroundRole:
            char = chr(symbolId)
            if self.__isDark:
                if self.__isDigit(char):
                    return QColor("#8787ff")
                elif self.__isLetter(char):
                    return QColor("#87ff87")
                elif self.__isMark(char):
                    return QColor("#ff8787")
                elif self.__isSymbol(char):
                    return QColor("#ffc060")
                elif self.__isPunct(char):
                    return QColor("#d080ff")
                else:
                    return QColor(Qt.GlobalColor.lightGray)
            else:
                if self.__isDigit(char):
                    return QColor(Qt.GlobalColor.darkBlue)
                elif self.__isLetter(char):
                    return QColor(Qt.GlobalColor.darkGreen)
                elif self.__isMark(char):
                    return QColor(Qt.GlobalColor.darkRed)
                elif self.__isSymbol(char):
                    return QColor(Qt.GlobalColor.darkYellow)
                elif self.__isPunct(char):
                    return QColor(Qt.GlobalColor.darkMagenta)
                else:
                    return QColor(Qt.GlobalColor.darkGray)

        if role == Qt.ItemDataRole.TextAlignmentRole and index.column() in [0, 1, 3]:
            return Qt.AlignmentFlag.AlignHCenter.value

        return None

    def columnCount(self, parent):
        """
        Public method to get the number of columns of the model.

        @param parent parent index
        @type QModelIndex
        @return number of columns
        @rtype int
        """
        if parent.column() > 0:
            return 0
        else:
            return len(self.__headerData)

    def rowCount(self, parent):
        """
        Public method to get the number of rows of the model.

        @param parent parent index
        @type QModelIndex
        @return number of columns
        @rtype int
        """
        if parent.isValid():
            return 0
        else:
            first, last = self.__tables[self.__currentTableIndex][:2]
            return last - first + 1

    def __isDigit(self, char):
        """
        Private method to check, if a character is a digit.

        @param char character to test
        @type str
        @return flag indicating a digit
        @rtype bool
        """
        return unicodedata.category(str(char)) in ("Nd", "Nl", "No")

    def __isLetter(self, char):
        """
        Private method to check, if a character is a letter.

        @param char character to test
        @type str
        @return flag indicating a letter
        @rtype bool
        """
        return unicodedata.category(str(char)) in ("Lu", "Ll", "Lt", "Lm", "Lo")

    def __isMark(self, char):
        """
        Private method to check, if a character is a mark character.

        @param char character to test
        @type str
        @return flag indicating a mark character
        @rtype bool
        """
        return unicodedata.category(str(char)) in ("Mn", "Mc", "Me")

    def __isPunct(self, char):
        """
        Private method to check, if a character is a punctuation character.

        @param char character to test
        @type str
        @return flag indicating a punctuation character
        @rtype boolean)
        """
        return unicodedata.category(str(char)) in (
            "Pc",
            "Pd",
            "Ps",
            "Pe",
            "Pi",
            "Pf",
            "Po",
        )

    def __isSymbol(self, char):
        """
        Private method to check, if a character is a symbol.

        @param char character to test
        @type str
        @return flag indicating a symbol
        @rtype bool
        """
        return unicodedata.category(str(char)) in ("Sm", "Sc", "Sk", "So")

    def getLocale(self):
        """
        Public method to get the used locale.

        @return used locale
        @rtype QLocale
        """
        return self.__locale


class SymbolsWidget(QWidget, Ui_SymbolsWidget):
    """
    Class implementing a widget to select a symbol in various formats.

    @signal insertSymbol(str) emitted after the user has selected a symbol
    """

    insertSymbol = pyqtSignal(str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowIcon(EricPixmapCache.getIcon("eric"))

        self.__model = SymbolsModel(self)
        self.symbolsTable.setModel(self.__model)
        self.symbolsTable.selectionModel().currentRowChanged.connect(
            self.__currentRowChanged
        )

        self.symbolsTable.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Fixed
        )
        fm = self.fontMetrics()
        em = fm.horizontalAdvance("M")
        self.symbolsTable.horizontalHeader().resizeSection(0, em * 5)
        self.symbolsTable.horizontalHeader().resizeSection(1, em * 5)
        self.symbolsTable.horizontalHeader().resizeSection(2, em * 6)
        self.symbolsTable.horizontalHeader().resizeSection(3, em * 8)
        self.symbolsTable.horizontalHeader().resizeSection(4, em * 85)
        self.symbolsTable.verticalHeader().setDefaultSectionSize(fm.height() + 4)

        tableIndex = int(Preferences.getSettings().value("Symbols/CurrentTable", 1))
        self.tableCombo.addItems(self.__model.getTableNames())
        self.tableCombo.setCurrentIndex(tableIndex)

        index = self.__model.index(
            int(Preferences.getSettings().value("Symbols/Top", 0)), 0
        )
        self.symbolsTable.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtTop)
        self.symbolsTable.selectionModel().setCurrentIndex(
            index,
            QItemSelectionModel.SelectionFlag.SelectCurrent
            | QItemSelectionModel.SelectionFlag.Rows,
        )

    @pyqtSlot(QModelIndex)
    def on_symbolsTable_activated(self, index):
        """
        Private slot to signal the selection of a symbol.

        @param index index of the selected symbol
        @type QModelIndex
        """
        txt = self.__model.data(index)
        if txt:
            self.insertSymbol.emit(txt)

    @pyqtSlot()
    def on_symbolSpinBox_editingFinished(self):
        """
        Private slot to move the table to the entered symbol id.
        """
        symbolId = self.symbolSpinBox.value()
        first, last = self.__model.getTableBoundaries(self.__model.getTableIndex())
        row = symbolId - first
        self.symbolsTable.selectRow(row)
        self.symbolsTable.scrollTo(
            self.__model.index(row, 0), QAbstractItemView.ScrollHint.PositionAtCenter
        )

    @pyqtSlot(int)
    def on_tableCombo_currentIndexChanged(self, index):
        """
        Private slot to select the current character table.

        @param index index of the character table
        @type int
        """
        self.symbolsTable.setUpdatesEnabled(False)
        self.__model.selectTable(index)
        self.symbolsTable.setUpdatesEnabled(True)
        self.symbolsTable.resizeColumnsToContents()

        first, last = self.__model.getTableBoundaries(index)
        self.symbolSpinBox.setMinimum(first)
        self.symbolSpinBox.setMaximum(last)

        Preferences.getSettings().setValue("Symbols/CurrentTable", index)

    @pyqtSlot(QModelIndex, QModelIndex)
    def __currentRowChanged(self, current, _previous):
        """
        Private slot recording the currently selected row.

        @param current current index
        @type QModelIndex
        @param _previous previous current index (unused)
        @type QModelIndex
        """
        Preferences.getSettings().setValue("Symbols/Top", current.row())
        self.symbolSpinBox.setValue(
            self.__model.getLocale().toInt(
                self.__model.data(self.__model.index(current.row(), 0))
            )[0]
        )
