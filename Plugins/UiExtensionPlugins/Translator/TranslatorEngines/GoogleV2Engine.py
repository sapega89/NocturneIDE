# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Google V2 translation engine.
"""

import json

from PyQt6.QtCore import QByteArray, QTimer, QUrl

from eric7 import EricUtilities

from .TranslationEngine import TranslationEngine


class GoogleV2Engine(TranslationEngine):
    """
    Class implementing the translation engine for the new Google
    translation service.
    """

    TranslatorUrl = "https://translation.googleapis.com/language/translate/v2"

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
        return "googlev2"

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
        apiKey = self.plugin.getPreferences("GoogleV2Key")
        if not apiKey:
            return (
                self.tr("Google V2: A valid Google Translate key is required."),
                False,
            )

        params = QByteArray(
            "key={2}&source={0}&target={1}&format=text&q=".format(
                originalLanguage, translationLanguage, apiKey
            ).encode("utf-8")
        )
        encodedText = QByteArray(
            EricUtilities.html_encode(text).encode("utf-8")
        ).toPercentEncoding()
        request = params + encodedText
        response, ok = requestObject.post(QUrl(self.TranslatorUrl), request)
        if ok:
            response = str(response, "utf-8", "replace")
            try:
                responseDict = json.loads(response)
            except ValueError:
                return self.tr("Google V2: Invalid response received"), False

            if "data" not in responseDict or "translations" not in responseDict["data"]:
                return self.tr("Google V2: No translation available."), False

            result = ""
            translations = responseDict["data"]["translations"]
            for translation in translations:
                result += translation["translatedText"]
                if translation != translations[-1]:
                    result += "<br/>"
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
    @rtype GoogleV2Engine
    """
    return GoogleV2Engine(plugin, parent=parent)
