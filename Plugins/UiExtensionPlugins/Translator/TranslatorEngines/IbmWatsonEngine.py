# -*- coding: utf-8 -*-

# Copyright (c) 2018 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the IBM Watson translation engine.
"""

import json

from PyQt6.QtCore import QByteArray, QTimer, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from eric7.EricNetwork.EricNetworkProxyFactory import proxyAuthenticationRequired
from eric7.EricWidgets import EricMessageBox

from .TranslationEngine import TranslationEngine


class IbmWatsonEngine(TranslationEngine):
    """
    Class implementing the translation engine for the IBM Watson Language
    Translator service.
    """

    # Documentation:
    # https://www.ibm.com/watson/developercloud/language-translator
    #
    # Start page:
    # https://www.ibm.com/watson/services/language-translator/

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
        return "ibm_watson"

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
        apiKey = self.plugin.getPreferences("IbmKey")
        if not apiKey:
            return (
                self.tr("IBM Watson: A valid Language Translator key is required."),
                False,
            )
        translatorUrl = self.plugin.getPreferences("IbmUrl")
        if not translatorUrl:
            return (
                self.tr("IBM Watson: A valid Language Translator URL is required."),
                False,
            )

        params = "?version=2018-05-01"
        url = QUrl(translatorUrl + "/v3/translate" + params)

        requestDict = {
            "text": [text],
            "source": originalLanguage,
            "target": translationLanguage,
        }
        request = QByteArray(json.dumps(requestDict).encode("utf-8"))

        extraHeaders = [
            (
                b"Authorization",
                b"Basic " + QByteArray(b"apikey:" + apiKey.encode("utf-8")).toBase64(),
            )
        ]

        response, ok = requestObject.post(
            url, request, dataType="json", extraHeaders=extraHeaders
        )
        if ok:
            try:
                responseDict = json.loads(response)
            except ValueError:
                return self.tr("IBM Watson: Invalid response received"), False

            if "translations" not in responseDict:
                return self.tr("IBM Watson: No translation available."), False

            result = ""
            translations = responseDict["translations"]
            for translation in translations:
                result += translation["translation"]
                if translation != translations[-1]:
                    result += "<br/>"
        else:
            result = response
        return result, ok

    def __adjustLanguageCode(self, code):
        """
        Private method to adjust a given language code.

        @param code code to be adjusted
        @type str
        @return adjusted language code
        @rtype str
        """
        if code == "zh":
            return "zh-CN"
        else:
            return code

    def __getTranslationModels(self):
        """
        Private method to get the translation models supported by IBM Watson
        Language Translator.
        """
        apiKey = self.plugin.getPreferences("IbmKey")
        if not apiKey:
            EricMessageBox.critical(
                self.__ui,
                self.tr("Error Getting Available Translations"),
                self.tr("IBM Watson: A valid Language Translator key is required."),
            )
            return
        translatorUrl = self.plugin.getPreferences("IbmUrl")
        if not translatorUrl:
            EricMessageBox.critical(
                self.__ui,
                self.tr("Error Getting Available Translations"),
                self.tr("IBM Watson: A valid Language Translator URL is required."),
            )
            return

        params = "?version=2018-05-01"
        url = QUrl(translatorUrl + "/v3/models" + params)

        extraHeaders = [
            (
                b"Authorization",
                b"Basic " + QByteArray(b"apikey:" + apiKey.encode("utf-8")).toBase64(),
            )
        ]

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
                        "IBM Watson: The server sent an error indication."
                        "\n Error: {0}"
                    ).format(errorStr),
                )
                return
            else:
                response = str(reply.readAll(), "utf-8", "replace")
                try:
                    responseDict = json.loads(response)
                except ValueError:
                    EricMessageBox.critical(
                        self.__ui,
                        self.tr("Error Getting Available Translations"),
                        self.tr("IBM Watson: Invalid response received"),
                    )
                    return

                if "models" not in responseDict:
                    EricMessageBox.critical(
                        self.__ui,
                        self.tr("Error Getting Available Translations"),
                        self.tr("IBM Watson: No translation available."),
                    )
                    return

                for model in responseDict["models"]:
                    if model["status"] == "available":
                        source = self.__adjustLanguageCode(model["source"])
                        target = self.__adjustLanguageCode(model["target"])
                        if source not in self.__availableTranslations:
                            self.__availableTranslations[source] = set()
                        self.__availableTranslations[source].add(target)

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
    return IbmWatsonEngine(plugin, parent=parent)
