# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the MyMemory translation engine.
"""

import json

from PyQt6.QtCore import QTimer, QUrl

from .TranslationEngine import TranslationEngine


class MyMemoryEngine(TranslationEngine):
    """
    Class implementing the translation engine for the MyMemory
    translation service.
    """

    TranslatorUrl = "http://api.mymemory.translated.net/get"
    TranslatorLimit = 500

    def __init__(self, plugin, parent=None):
        """
        Constructor

        @param plugin reference to the plugin object
        @type TranslatorPlugin
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(plugin, parent)

        QTimer.singleShot(0, self.availableTranslationsLoaded.emit)

    def engineName(self):
        """
        Public method to return the name of the engine.

        @return engine name
        @rtype str
        """
        return "mymemory"

    def supportedLanguages(self):
        """
        Public method to get the supported languages.

        @return list of supported language codes
        @rtype list of str
        """
        return [
            "ar",
            "be",
            "bg",
            "bs",
            "ca",
            "cs",
            "da",
            "de",
            "el",
            "en",
            "es",
            "et",
            "fi",
            "fr",
            "ga",
            "gl",
            "hi",
            "hr",
            "hu",
            "id",
            "is",
            "it",
            "iw",
            "ja",
            "ka",
            "ko",
            "lt",
            "lv",
            "mk",
            "mt",
            "nl",
            "no",
            "pl",
            "pt",
            "ro",
            "ru",
            "sk",
            "sl",
            "sq",
            "sr",
            "sv",
            "th",
            "tl",
            "tr",
            "uk",
            "vi",
            "zh-CN",
            "zh-TW",
        ]

    def getTranslation(
        self, requestObject, text, originalLanguage, translationLanguage
    ):
        """
        Public method to translate the given text.

        @param requestObject reference to the request object
        @type TranslatorRequest
        @param text text to be translated
        @type str
        @param originalLanguage language code of the original
        @type str
        @param translationLanguage language code of the translation
        @type str
        @return tuple of translated text and flag indicating success
        @rtype tuple of (str, bool)
        """
        if len(text) > self.TranslatorLimit:
            return (
                self.tr(
                    "MyMemory: Only texts up to {0} characters are allowed."
                ).format(self.TranslatorLimit),
                False,
            )

        myMemoryKey = self.plugin.getPreferences("MyMemoryKey")
        keyParam = "&key={0}".format(myMemoryKey) if myMemoryKey else ""

        myMemoryEmail = self.plugin.getPreferences("MyMemoryEmail")
        emailParam = "&de={0}".format(myMemoryEmail) if myMemoryEmail else ""

        params = "?of=json{3}{4}&langpair={0}|{1}&q={2}".format(
            originalLanguage, translationLanguage, text, keyParam, emailParam
        )
        url = QUrl(self.TranslatorUrl + params)
        response, ok = requestObject.get(url)
        if ok:
            response = str(response, "utf-8", "replace")
            try:
                responseDict = json.loads(response)
            except ValueError:
                return self.tr("MyMemory: Invalid response received"), False
            result = responseDict["responseData"]["translatedText"]
        else:
            result = response
        return result, ok


def createEngine(plugin, parent=None):
    """
    Function to instantiate a translator engine object.

    @param plugin reference to the plugin object
    @type TranslatorPlugin
    @param parent reference to the parent object (defaults to None)
    @type QObject (optional)
    @return reference to the instantiated translator engine object
    @rtype MyMemoryEngine
    """
    return MyMemoryEngine(plugin, parent=parent)
