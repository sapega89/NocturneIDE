# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the open search engine.
"""

import json
import re

from PyQt6.QtCore import (
    QBuffer,
    QByteArray,
    QIODevice,
    QLocale,
    QObject,
    QUrl,
    QUrlQuery,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QImage
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from eric7 import Preferences, Utilities
from eric7.UI.Info import Program


class OpenSearchEngine(QObject):
    """
    Class implementing the open search engine.

    @signal imageChanged() emitted after the icon has been changed
    @signal suggestions(list of strings) emitted after the suggestions have
            been received
    """

    imageChanged = pyqtSignal()
    suggestions = pyqtSignal(list)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__suggestionsReply = None
        self.__networkAccessManager = None
        self._name = ""
        self._description = ""
        self._searchUrlTemplate = ""
        self._suggestionsUrlTemplate = ""
        self._searchParameters = []  # list of two tuples
        self._suggestionsParameters = []  # list of two tuples
        self._imageUrl = ""
        self.__image = QImage()
        self.__iconMoved = False
        self.__searchMethod = "get"
        self.__suggestionsMethod = "get"
        self.__requestMethods = {
            "get": QNetworkAccessManager.Operation.GetOperation,
            "post": QNetworkAccessManager.Operation.PostOperation,
        }

        self.__replies = []

    @classmethod
    def parseTemplate(cls, searchTerm, searchTemplate):
        """
        Class method to parse a search template.

        @param searchTerm term to search for
        @type str
        @param searchTemplate template to be parsed
        @type str
        @return parsed template
        @rtype str
        """
        locale = QLocale(Preferences.getWebBrowser("SearchLanguage"))
        language = locale.name().replace("_", "-")
        country = locale.name().split("_")[0].lower()

        result = searchTemplate
        result = result.replace("{count}", "20")
        result = result.replace("{startIndex}", "0")
        result = result.replace("{startPage}", "0")
        result = result.replace("{language}", language)
        result = result.replace("{country}", country)
        result = result.replace("{inputEncoding}", "UTF-8")
        result = result.replace("{outputEncoding}", "UTF-8")
        result = result.replace(
            "{searchTerms}", bytes(QUrl.toPercentEncoding(searchTerm)).decode()
        )
        result = re.sub(r"""\{([^\}]*:|)source\??\}""", Program, result)

        return result

    @pyqtSlot(result=str)
    def name(self):
        """
        Public method to get the name of the engine.

        @return name of the engine
        @rtype str
        """
        return self._name

    def setName(self, name):
        """
        Public method to set the engine name.

        @param name name of the engine
        @type str
        """
        self._name = name

    def description(self):
        """
        Public method to get the description of the engine.

        @return description of the engine
        @rtype str
        """
        return self._description

    def setDescription(self, description):
        """
        Public method to set the engine description.

        @param description description of the engine
        @type str
        """
        self._description = description

    def searchUrlTemplate(self):
        """
        Public method to get the search URL template of the engine.

        @return search URL template of the engine
        @rtype str
        """
        return self._searchUrlTemplate

    def setSearchUrlTemplate(self, searchUrlTemplate):
        """
        Public method to set the engine search URL template.

        The URL template is processed according to the specification:
        <a
          href="http://www.opensearch.org/Specifications/OpenSearch/1.1#OpenSearch_URL_template_syntax">
        http://www.opensearch.org/Specifications/OpenSearch/1.1#OpenSearch_URL_template_syntax</a>

        A list of template parameters currently supported and what they are
        replaced with:
        <table>
        <tr><td><b>Parameter</b></td><td><b>Value</b></td></tr>
        <tr><td>{count}</td><td>20</td></tr>
        <tr><td>{startIndex}</td><td>0</td></tr>
        <tr><td>{startPage}</td><td>0</td></tr>
        <tr><td>{language}</td>
          <td>the default language code (RFC 3066)</td></tr>
        <tr><td>{country}</td>
          <td>the default country code (first part of language)</td></tr>
        <tr><td>{inputEncoding}</td><td>UTF-8</td></tr>
        <tr><td>{outputEncoding}</td><td>UTF-8</td></tr>
        <tr><td>{searchTerms}</td><td>the string supplied by the user</td></tr>
        <tr><td>{*:source}</td>
          <td>application name, QCoreApplication::applicationName()</td></tr>
        </table>

        @param searchUrlTemplate search URL template of the engine
        @type str
        """
        self._searchUrlTemplate = searchUrlTemplate

    def searchUrl(self, searchTerm):
        """
        Public method to get a URL ready for searching.

        @param searchTerm term to search for
        @type str
        @return URL
        @rtype QUrl
        """
        if not self._searchUrlTemplate:
            return QUrl()

        ret = QUrl.fromEncoded(
            self.parseTemplate(searchTerm, self._searchUrlTemplate).encode("utf-8")
        )

        if self.__searchMethod != "post":
            urlQuery = QUrlQuery(ret)
            for parameter in self._searchParameters:
                urlQuery.addQueryItem(
                    parameter[0], self.parseTemplate(searchTerm, parameter[1])
                )
            ret.setQuery(urlQuery)

        return ret

    def providesSuggestions(self):
        """
        Public method to check, if the engine provides suggestions.

        @return flag indicating suggestions are provided
        @rtype bool
        """
        return self._suggestionsUrlTemplate != ""

    def suggestionsUrlTemplate(self):
        """
        Public method to get the search URL template of the engine.

        @return search URL template of the engine
        @rtype str
        """
        return self._suggestionsUrlTemplate

    def setSuggestionsUrlTemplate(self, suggestionsUrlTemplate):
        """
        Public method to set the engine suggestions URL template.

        @param suggestionsUrlTemplate suggestions URL template of the
            engine
        @type str
        """
        self._suggestionsUrlTemplate = suggestionsUrlTemplate

    def suggestionsUrl(self, searchTerm):
        """
        Public method to get a URL ready for suggestions.

        @param searchTerm term to search for
        @type str
        @return URL
        @rtype QUrl
        """
        if not self._suggestionsUrlTemplate:
            return QUrl()

        ret = QUrl.fromEncoded(
            QByteArray(
                self.parseTemplate(searchTerm, self._suggestionsUrlTemplate).encode(
                    "utf-8"
                )
            )
        )

        if self.__searchMethod != "post":
            urlQuery = QUrlQuery(ret)
            for parameter in self._suggestionsParameters:
                urlQuery.addQueryItem(
                    parameter[0], self.parseTemplate(searchTerm, parameter[1])
                )
            ret.setQuery(urlQuery)

        return ret

    def searchParameters(self):
        """
        Public method to get the search parameters of the engine.

        @return search parameters of the engine
        @rtype list of [tuple, tuple]
        """
        return self._searchParameters[:]

    def setSearchParameters(self, searchParameters):
        """
        Public method to set the engine search parameters.

        @param searchParameters search parameters of the engine
        @type list of [tuple, tuple]
        """
        self._searchParameters = searchParameters[:]

    def suggestionsParameters(self):
        """
        Public method to get the suggestions parameters of the engine.

        @return suggestions parameters of the engine
        @rtype list of [tuple, tuple]
        """
        return self._suggestionsParameters[:]

    def setSuggestionsParameters(self, suggestionsParameters):
        """
        Public method to set the engine suggestions parameters.

        @param suggestionsParameters suggestions parameters of the engine
        @type list of [tuple, tuple]
        """
        self._suggestionsParameters = suggestionsParameters[:]

    def searchMethod(self):
        """
        Public method to get the HTTP request method used to perform search
        requests.

        @return HTTP request method
        @rtype str
        """
        return self.__searchMethod

    def setSearchMethod(self, method):
        """
        Public method to set the HTTP request method used to perform search
        requests.

        @param method HTTP request method
        @type str
        """
        requestMethod = method.lower()
        if requestMethod not in self.__requestMethods:
            return

        self.__searchMethod = requestMethod

    def suggestionsMethod(self):
        """
        Public method to get the HTTP request method used to perform
        suggestions requests.

        @return HTTP request method
        @rtype str
        """
        return self.__suggestionsMethod

    def setSuggestionsMethod(self, method):
        """
        Public method to set the HTTP request method used to perform
        suggestions requests.

        @param method HTTP request method
        @type str
        """
        requestMethod = method.lower()
        if requestMethod not in self.__requestMethods:
            return

        self.__suggestionsMethod = requestMethod

    def imageUrl(self):
        """
        Public method to get the image URL of the engine.

        @return image URL of the engine
        @rtype str
        """
        return self._imageUrl

    def setImageUrl(self, imageUrl):
        """
        Public method to set the engine image URL.

        @param imageUrl image URL of the engine
        @type str
        """
        self._imageUrl = imageUrl

    def setImageUrlAndLoad(self, imageUrl):
        """
        Public method to set the engine image URL.

        @param imageUrl image URL of the engine
        @type str
        """
        self.setImageUrl(imageUrl)
        self.__iconMoved = False
        self.loadImage()

    def loadImage(self):
        """
        Public method to load the image of the engine.
        """
        if self.__networkAccessManager is None or not self._imageUrl:
            return

        reply = self.__networkAccessManager.get(
            QNetworkRequest(QUrl.fromEncoded(self._imageUrl.encode("utf-8")))
        )
        reply.finished.connect(lambda: self.__imageObtained(reply))
        self.__replies.append(reply)

    def __imageObtained(self, reply):
        """
        Private slot to receive the image of the engine.

        @param reply reference to the network reply
        @type QNetworkReply
        """
        response = reply.readAll()

        reply.close()
        if reply in self.__replies:
            self.__replies.remove(reply)
        reply.deleteLater()

        if response.isEmpty():
            return

        if response.startsWith(b"<html>") or response.startsWith(b"HTML"):
            self.__iconMoved = True
            self.__image = QImage()
        else:
            self.__image.loadFromData(response)
        self.imageChanged.emit()

    def image(self):
        """
        Public method to get the image of the engine.

        @return image of the engine
        @rtype QImage
        """
        if not self.__iconMoved and self.__image.isNull():
            self.loadImage()

        return self.__image

    def setImage(self, image):
        """
        Public method to set the image of the engine.

        @param image image to be set
        @type QImage
        """
        if not self._imageUrl:
            imageBuffer = QBuffer()
            imageBuffer.open(QIODevice.OpenModeFlag.ReadWrite)
            if image.save(imageBuffer, "PNG"):
                self._imageUrl = "data:image/png;base64,{0}".format(
                    bytes(imageBuffer.buffer().toBase64()).decode()
                )

        self.__image = QImage(image)
        self.imageChanged.emit()

    def isValid(self):
        """
        Public method to check, if the engine is valid.

        @return flag indicating validity
        @rtype bool
        """
        return self._name and self._searchUrlTemplate

    def __eq__(self, other):
        """
        Special method implementing the == operator.

        @param other reference to an open search engine
        @type OpenSearchEngine
        @return flag indicating equality
        @rtype bool
        """
        if not isinstance(other, OpenSearchEngine):
            return NotImplemented

        return (
            self._name == other._name
            and self._description == other._description
            and self._imageUrl == other._imageUrl
            and self._searchUrlTemplate == other._searchUrlTemplate
            and self._suggestionsUrlTemplate == other._suggestionsUrlTemplate
            and self._searchParameters == other._searchParameters
            and self._suggestionsParameters == other._suggestionsParameters
        )

    def __lt__(self, other):
        """
        Special method implementing the < operator.

        @param other reference to an open search engine
        @type OpenSearchEngine
        @return flag indicating less than
        @rtype bool
        """
        if not isinstance(other, OpenSearchEngine):
            return NotImplemented

        return self._name < other._name

    def requestSuggestions(self, searchTerm):
        """
        Public method to request suggestions.

        @param searchTerm term to get suggestions for
        @type str
        """
        if not searchTerm or not self.providesSuggestions():
            return

        if self.__networkAccessManager is None:
            return

        if self.__suggestionsReply is not None:
            self.__suggestionsReply.finished.disconnect(self.__suggestionsObtained)
            self.__suggestionsReply.abort()
            self.__suggestionsReply.deleteLater()
            self.__suggestionsReply = None

        if self.__suggestionsMethod not in self.__requestMethods:
            # ignore
            return

        if self.__suggestionsMethod == "get":
            self.__suggestionsReply = self.networkAccessManager().get(
                QNetworkRequest(self.suggestionsUrl(searchTerm))
            )
        else:
            parameters = []
            for parameter in self._suggestionsParameters:
                parameters.append(parameter[0] + "=" + parameter[1])
            data = "&".join(parameters)
            self.__suggestionsReply = self.networkAccessManager().post(
                QNetworkRequest(self.suggestionsUrl(searchTerm)), data
            )
        self.__suggestionsReply.finished.connect(self.__suggestionsObtained)

    def __suggestionsObtained(self):
        """
        Private slot to receive the suggestions.
        """
        if self.__suggestionsReply.error() == QNetworkReply.NetworkError.NoError:
            buffer = bytes(self.__suggestionsReply.readAll())
            response = Utilities.decodeBytes(buffer)
            response = response.strip()

            self.__suggestionsReply.close()
            self.__suggestionsReply.deleteLater()
            self.__suggestionsReply = None

            if len(response) == 0:
                return

            try:
                result = json.loads(response)
            except ValueError:
                return

            try:
                suggestions = result[1]
            except IndexError:
                return

            self.suggestions.emit(suggestions)

    def networkAccessManager(self):
        """
        Public method to get a reference to the network access manager object.

        @return reference to the network access manager object
        @rtype QNetworkAccessManager
        """
        return self.__networkAccessManager

    def setNetworkAccessManager(self, networkAccessManager):
        """
        Public method to set the reference to the network access manager.

        @param networkAccessManager reference to the network access manager
            object
        @type QNetworkAccessManager
        """
        self.__networkAccessManager = networkAccessManager
