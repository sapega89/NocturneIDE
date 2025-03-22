# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the LibreTranslate translation engine.
"""

import contextlib
import json

from PyQt6.QtCore import QByteArray, QTimer, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from eric7 import EricUtilities
from eric7.EricNetwork.EricNetworkProxyFactory import proxyAuthenticationRequired
from eric7.EricWidgets import EricMessageBox

from .TranslationEngine import TranslationEngine


class LibreTranslateEngine(TranslationEngine):
    """
    Class implementing the translation engine for the LibreTranslate service.
    """

    # Documentation:
    # https://de.libretranslate.com/docs/
    #
    # Github
    # https://github.com/LibreTranslate/LibreTranslate
    #
    # Start page:
    # http://localhost:5000
    # https://translate.argosopentech.com (no API key required)

    def __init__(self, plugin, parent=None):
        """
        Constructor

        @param plugin reference to the plugin object
        @type TranslatorPlugin
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(plugin, parent)

        self.__ui = parent

        self.__networkManager = QNetworkAccessManager(self)
        self.__networkManager.proxyAuthenticationRequired.connect(
            proxyAuthenticationRequired
        )

        self.__availableTranslations = {}
        # dictionary of sets of available translations

        self.__replies = []

        QTimer.singleShot(0, self.__getTranslationModels)

    def engineName(self):
        """
        Public method to return the name of the engine.

        @return engine name
        @rtype str
        """
        return "libre_translate"

    def supportedLanguages(self):
        """
        Public method to get the supported languages.

        @return list of supported language codes
        @rtype list of str
        """
        return list(self.__availableTranslations)

    def supportedTargetLanguages(self, original):
        """
        Public method to get a list of supported target languages for an
        original language.

        @param original original language
        @type str
        @return list of supported target languages for the given original
        @rtype list of str
        """
        targets = self.__availableTranslations.get(original, set())
        return list(targets)

    def hasTTS(self):
        """
        Public method indicating the Text-to-Speech capability.

        @return flag indicating the Text-to-Speech capability
        @rtype bool
        """
        return False

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
        apiKey = self.plugin.getPreferences("libreTranslateKey")

        translatorUrl = self.plugin.getPreferences("LibreTranslateUrl")
        if not translatorUrl:
            return (
                self.tr("LibreTranslate: A valid Language Translator URL is required."),
                False,
            )
        url = QUrl(translatorUrl + "/translate")

        paramsStr = "source={0}&target={1}&format=text".format(
            originalLanguage, translationLanguage
        )
        if apiKey:
            paramsStr += "&api_key={0}".format(apiKey)
        paramsStr += "&q="
        params = QByteArray(paramsStr.encode("utf-8"))
        encodedText = QByteArray(
            EricUtilities.html_encode(text).encode("utf-8")
        ).toPercentEncoding()
        request = params + encodedText
        response, ok = requestObject.post(QUrl(url), request)
        if ok:
            try:
                responseDict = json.loads(response)
            except ValueError:
                return self.tr("LibreTranslate: Invalid response received"), False

            try:
                return EricUtilities.html_encode(responseDict["translatedText"]), True
            except KeyError:
                return self.tr("LibreTranslate: No translation available."), False
        else:
            with contextlib.suppress(ValueError, KeyError):
                responseDict = json.loads(response)
                return responseDict["error"], False

            return response, False

    def __getTranslationModels(self):
        """
        Private method to get the translation models supported by IBM Watson
        Language Translator.
        """
        translatorUrl = self.plugin.getPreferences("LibreTranslateUrl")
        if not translatorUrl:
            EricMessageBox.critical(
                self.__ui,
                self.tr("Error Getting Available Translations"),
                self.tr("LibreTranslate: A valid Language Translator URL is required."),
            )
            return

        url = QUrl(translatorUrl + "/languages")

        extraHeaders = [(b"accept", b"application/json")]

        request = QNetworkRequest(url)
        if extraHeaders:
            for name, value in extraHeaders:
                request.setRawHeader(name, value)
        reply = self.__networkManager.get(request)
        reply.finished.connect(lambda: self.__getTranslationModelsReplyFinished(reply))
        self.__replies.append(reply)

    def __getTranslationModelsReplyFinished(self, reply):
        """
        Private slot handling the receipt of the available translations.

        @param reply reference to the network reply object
        @type QNetworkReply
        """
        if reply in self.__replies:
            self.__replies.remove(reply)
            reply.deleteLater()

            if reply.error() != QNetworkReply.NetworkError.NoError:
                errorStr = reply.errorString()
                EricMessageBox.critical(
                    self.__ui,
                    self.tr("Error Getting Available Translations"),
                    self.tr(
                        "LibreTranslate: The server sent an error indication."
                        "\n Error: {0}"
                    ).format(errorStr),
                )
                return
            else:
                response = str(reply.readAll(), "utf-8", "replace")
                try:
                    languageEntries = json.loads(response)
                except ValueError:
                    EricMessageBox.critical(
                        self.__ui,
                        self.tr("Error Getting Available Translations"),
                        self.tr("LibreTranslate: Invalid response received"),
                    )
                    return

                for languageEntry in languageEntries:
                    source = languageEntry["code"]
                    self.__availableTranslations[source] = set(languageEntry["targets"])

                self.availableTranslationsLoaded.emit()


def createEngine(plugin, parent=None):
    """
    Function to instantiate a translator engine object.

    @param plugin reference to the plugin object
    @type TranslatorPlugin
    @param parent reference to the parent object (defaults to None)
    @type QObject (optional)
    @return reference to the instantiated translator engine object
    @rtype IbmWatsonEngine
    """
    return LibreTranslateEngine(plugin, parent=parent)
