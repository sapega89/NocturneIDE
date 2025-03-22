# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the translation languages database.
"""

import os

from PyQt6.QtCore import QObject

from eric7.EricGui import EricPixmapCache


class TranslatorLanguagesDb(QObject):
    """
    Class implementing the translation languages database.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__languages = {
            "af": self.tr("Afrikaans"),
            "ar": self.tr("Arabic"),
            "be": self.tr("Belarusian"),
            "bg": self.tr("Bulgarian"),
            "bs": self.tr("Bosnian"),
            "ca": self.tr("Catalan"),
            "cs": self.tr("Czech"),
            "da": self.tr("Danish"),
            "de": self.tr("German"),
            "el": self.tr("Greek"),
            "en": self.tr("English"),
            "es": self.tr("Spanish"),
            "et": self.tr("Estonian"),
            "fi": self.tr("Finnish"),
            "fr": self.tr("French"),
            "ga": self.tr("Irish"),
            "gl": self.tr("Galician"),
            "he": self.tr("Hebrew (he)"),
            "hi": self.tr("Hindi"),
            "hr": self.tr("Croatian"),
            "hu": self.tr("Hungarian"),
            "id": self.tr("Indonesian"),
            "is": self.tr("Icelandic"),
            "it": self.tr("Italian"),
            "iw": self.tr("Hebrew (iw)"),
            "ja": self.tr("Japanese"),
            "ka": self.tr("Georgian"),
            "ko": self.tr("Korean"),
            "lt": self.tr("Lithuanian"),
            "lv": self.tr("Latvian"),
            "mk": self.tr("Macedonian"),
            "mt": self.tr("Maltese"),
            "nl": self.tr("Dutch"),
            "no": self.tr("Norwegian"),
            "pl": self.tr("Polish"),
            "pt": self.tr("Portuguese"),
            "ro": self.tr("Romanian"),
            "ru": self.tr("Russian"),
            "sk": self.tr("Slovak"),
            "sl": self.tr("Slovenian"),
            "sq": self.tr("Albanian"),
            "sr": self.tr("Serbian"),
            "sv": self.tr("Swedish"),
            "th": self.tr("Thai"),
            "tl": self.tr("Filipino"),
            "tr": self.tr("Turkish"),
            "uk": self.tr("Ukrainian"),
            "vi": self.tr("Vietnamese"),
            "zh": self.tr("Chinese"),
            "zh-CN": self.tr("Chinese (China)"),
            "zh-TW": self.tr("Chinese (Taiwan)"),
        }

        self.__toThreeCharacterCode = {
            "af": "afr",
            "ar": "ara",
            "be": "bel",
            "bg": "bul",
            "bs": "bos",
            "ca": "cat",
            "cs": "ces",
            "da": "dan",
            "de": "deu",
            "el": "ell",
            "en": "eng",
            "es": "spa",
            "et": "est",
            "fi": "fin",
            "fr": "fra",
            "ga": "gle",
            "gl": "glg",
            "he": "heb",
            "hi": "hin",
            "hr": "hrv",
            "hu": "hun",
            "id": "ind",
            "is": "isl",
            "it": "ita",
            "iw": "heb",
            "ja": "jpn",
            "ka": "kat",
            "ko": "kor",
            "lt": "lit",
            "lv": "lav",
            "mk": "mkd",
            "mt": "mlt",
            "nl": "nld",
            "no": "nor",
            "pl": "pol",
            "pt": "por",
            "ro": "ron",
            "ru": "rus",
            "sk": "slk",
            "sl": "slv",
            "sq": "sqi",
            "sr": "srp",
            "sv": "swe",
            "th": "tha",
            "tl": "tgl",
            "tr": "tur",
            "uk": "ukr",
            "vi": "vie",
            "zh": "zho",
            "zh-CN": "zho",
            "zh-TW": "zho",
        }

    def getLanguageIcon(self, code):
        """
        Public method to get a language icon.

        @param code language code
        @type str
        @return language icon
        @rtype QIcon
        """
        return EricPixmapCache.getIcon(
            os.path.join(
                os.path.dirname(__file__), "icons", "flags", "{0}".format(code)
            )
        )

    def getLanguage(self, code):
        """
        Public method to get a translated language.

        @param code language code
        @type str
        @return translated language
        @rtype str
        """
        try:
            return self.__languages[code]
        except KeyError:
            return ""

    def getAllLanguages(self):
        """
        Public method to get a list of the supported language codes.

        @return list of supported language codes
        @rtype list of str
        """
        return list(self.__languages)

    def convertTwoToThree(self, code):
        """
        Public method to convert a two character language code to a
        thre character code.

        @param code two character language code
        @type str
        @return three character language code
        @rtype str
        """
        try:
            return self.__toThreeCharacterCode[code]
        except KeyError:
            return ""
