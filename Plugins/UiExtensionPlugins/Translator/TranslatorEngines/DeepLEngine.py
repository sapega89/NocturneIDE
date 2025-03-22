# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the DeepL translation engine.
"""

import json

from PyQt6.QtCore import QByteArray, QTimer, QUrl

from .TranslationEngine import TranslationEngine


class DeepLEngine(TranslationEngine):
    """
    Class implementing the translation engine for the DeepL
    translation service.
    """

    TranslatorUrls = {
        "pro": "https://api.deepl.com/v2/translate",
        "free": "https://api-free.deepl.com/v2/translate",
    }
    MaxTranslationTextLen = 128 * 1024

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
        return "deepl"

    def supportedLanguages(self):
        """
        Public method to get the supported languages.

        @return list of supported language codes
        @rtype list of str
        """
        return [
            "bg",
            "cs",
            "da",
            "de",
            "el",
            "en",
            "es",
            "et",
            "fi",
            "fr",
            "hu",
            "id",
            "it",
            "ja",
            "ko",
            "lt",
            "lv",
            "nb",
            "nl",
            "pl",
            "pt",
            "ro",
            "ru",
            "sk",
            "sl",
            "sv",
            "tr",
            "uk",
            "zh",
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
        if len(text) > self.MaxTranslationTextLen:
            return (
                self.tr(
                    "DeepL: Text to be translated exceeds the translation"
                    " limit of {0} characters."
                ).format(self.MaxTranslationTextLen),
                False,
            )

        apiKey = self.plugin.getPreferences("DeeplKey")
        if not apiKey:
            return self.tr("A valid DeepL Pro key is required."), False

        translatorUrl = (
            DeepLEngine.TranslatorUrls["free"]
            if apiKey.endswith(":fx")
            else DeepLEngine.TranslatorUrls["pro"]
        )

        requestDict = {
            "text": [text],
            "source_lang": originalLanguage,
            "target_lang": translationLanguage,
        }
        request = QByteArray(json.dumps(requestDict).encode("utf-8"))

        extraHeaders = [
            (
                b"Authorization",
                b"DeepL-Auth-Key " + QByteArray(apiKey.encode("utf-8")),
            )
        ]

        response, ok = requestObject.post(
            QUrl(translatorUrl), request, dataType="json", extraHeaders=extraHeaders
        )
        if ok:
            try:
                responseDict = json.loads(response)
            except ValueError:
                return self.tr("Invalid response received from DeepL"), False

            if "translations" not in responseDict:
                return self.tr("DeepL call returned an unknown result"), False

            translations = responseDict["translations"]
            if len(translations) == 0:
                return self.tr("<p>DeepL: No translation found</p>"), True

            # show sentence by sentence separated by a line
            result = "<p>" + "<hr/>".join([t["text"] for t in translations]) + "</p>"

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
    @rtype DeepLEngine
    """
    return DeepLEngine(plugin, parent=parent)
