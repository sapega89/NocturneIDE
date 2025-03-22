# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Yandex translation engine.
"""

import json

from PyQt6.QtCore import QByteArray, QTimer, QUrl

from eric7 import EricUtilities

from .TranslationEngine import TranslationEngine


class YandexEngine(TranslationEngine):
    """
    Class implementing the translation engine for the Yandex
    translation service.
    """

    TranslatorUrl = "https://translate.yandex.net/api/v1.5/tr.json/translate"
    TranslatorLimit = 10000

    def __init__(self, plugin, parent=None):
        """
        Constructor

        @param plugin reference to the plugin object
        @type TranslatorPlugin
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(plugin, parent)

        self.__errors = {
            401: self.tr("Yandex: Invalid API key."),
            402: self.tr("Yandex: API key has been blocked."),
            403: self.tr("Yandex: Daily limit for requests has been reached."),
            404: self.tr(
                "Yandex: Daily limit for the volume of translated text reached."
            ),
            413: self.tr("Yandex: Text size exceeds the maximum."),
            422: self.tr("Yandex: Text could not be translated."),
            501: self.tr(
                "Yandex: The specified translation direction is not supported."
            ),
        }

        QTimer.singleShot(0, self.availableTranslationsLoaded.emit)

    def engineName(self):
        """
        Public method to return the name of the engine.

        @return engine name
        @rtype str
        """
        return "yandex"

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
                self.tr("Yandex: Only texts up to {0} characters are allowed.").format(
                    self.TranslatorLimit
                ),
                False,
            )

        apiKey = self.plugin.getPreferences("YandexKey")
        if not apiKey:
            return self.tr("Yandex: A valid key is required."), False

        params = QByteArray(
            "key={0}&lang={1}-{2}&text=".format(
                apiKey, originalLanguage, translationLanguage
            ).encode("utf-8")
        )
        encodedText = QByteArray(
            EricUtilities.html_encode(text).encode("utf-8")
        ).toPercentEncoding()
        request = params + encodedText
        response, ok = requestObject.post(QUrl(self.TranslatorUrl), request)
        if ok:
            try:
                responseDict = json.loads(response)
            except ValueError:
                return self.tr("Yandex: Invalid response received"), False

            if responseDict["code"] != 200:
                try:
                    error = self.__errors[responseDict["code"]]
                except KeyError:
                    error = self.tr(
                        "Yandex: Unknown error code ({0}) received."
                    ).format(responseDict["code"])
                return error, False

            sentences = responseDict["text"]
            result = ""
            for sentence in sentences:
                result += sentence.replace("\n", "<br/>")
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
    @rtype YandexEngine
    """
    return YandexEngine(plugin, parent=parent)
