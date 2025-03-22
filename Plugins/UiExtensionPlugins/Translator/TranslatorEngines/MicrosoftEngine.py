# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Microsoft translation engine.
"""

import json

from PyQt6.QtCore import QByteArray, QTimer, QUrl

from .TranslationEngine import TranslationEngine


class MicrosoftEngine(TranslationEngine):
    """
    Class implementing the translation engine for the Microsoft
    translation service.
    """

    TranslatorUrl = (
        "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0"
    )

    def __init__(self, plugin, parent=None):
        """
        Constructor

        @param plugin reference to the plugin object
        @type TranslatorPlugin
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(plugin, parent)

        self.__mappings = {
            "zh-CN": "zh-CHS",
            "zh-TW": "zh-CHT",
        }

        QTimer.singleShot(0, self.availableTranslationsLoaded.emit)

    def engineName(self):
        """
        Public method to return the name of the engine.

        @return engine name
        @rtype str
        """
        return "microsoft"

    def supportedLanguages(self):
        """
        Public method to get the supported languages.

        @return list of supported language codes
        @rtype list of str
        """
        return [
            "ar",
            "bg",
            "ca",
            "cs",
            "da",
            "de",
            "en",
            "es",
            "et",
            "fi",
            "fr",
            "hi",
            "hu",
            "id",
            "it",
            "ja",
            "ko",
            "lt",
            "lv",
            "mt",
            "nl",
            "no",
            "pl",
            "pt",
            "ro",
            "ru",
            "sk",
            "sl",
            "sv",
            "th",
            "tr",
            "uk",
            "vi",
            "zh-CN",
            "zh-TW",
        ]

    def __mapLanguageCode(self, code):
        """
        Private method to map a language code to the Microsoft code.

        @param code language code
        @type str
        @return mapped language code
        @rtype str
        """
        if code in self.__mappings:
            return self.__mapping[code]
        else:
            return code

    def __getClientDataAzure(self):
        """
        Private method to retrieve the client data.

        @return tuple giving the API subscription key, the API subscription
            region and a flag indicating validity
        @rtype tuple of (str, str, bool)
        """
        subscriptionKey = self.plugin.getPreferences("MsTranslatorKey")
        subscriptionRegion = self.plugin.getPreferences("MsTranslatorRegion")
        valid = bool(subscriptionKey) and bool(subscriptionRegion)
        return subscriptionKey, subscriptionRegion, valid

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
        subscriptionKey, subscriptionRegion, valid = self.__getClientDataAzure()
        if not valid:
            return (
                self.tr(
                    """You have not registered for the Microsoft"""
                    """ Azure Translation service."""
                ),
                False,
            )

        params = "&from={0}&to={1}".format(
            self.__mapLanguageCode(originalLanguage),
            self.__mapLanguageCode(translationLanguage),
        )
        url = QUrl(self.TranslatorUrl + params)

        requestList = [{"Text": text}]
        request = QByteArray(json.dumps(requestList).encode("utf-8"))

        headers = [
            (b"Ocp-Apim-Subscription-Key", subscriptionKey.encode("utf8")),
            (b"Ocp-Apim-Subscription-Region", subscriptionRegion.encode("utf8")),
            (b"Content-Type", b"application/json; charset=UTF-8"),
            (b"Content-Length", str(len(request)).encode("utf-8")),
        ]
        response, ok = requestObject.post(
            url, request, dataType="json", extraHeaders=headers
        )
        if ok:
            try:
                responseList = json.loads(response)
                responseDict = responseList[0]
            except ValueError:
                return (self.tr("MS Translator: Invalid response received"), False)

            if "translations" not in responseDict:
                return (self.tr("MS Translator: No translation available."), False)

            result = ""
            translations = responseDict["translations"]
            for translation in translations:
                result += translation["text"]
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
    @rtype MicrosoftEngine
    """
    return MicrosoftEngine(plugin, parent=parent)
