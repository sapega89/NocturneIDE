# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a synchronous network request handler for translation
requests.
"""

from PyQt6.QtCore import QByteArray, QEventLoop, QObject
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from eric7.EricNetwork.EricNetworkProxyFactory import proxyAuthenticationRequired


class TranslatorRequest(QObject):
    """
    Class implementing a synchronous network request handler for translation
    requests.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__contentTypes = {
            "form": b"application/x-www-form-urlencoded",
            "json": b"application/json",
        }

        self.__networkManager = QNetworkAccessManager(self)
        self.__networkManager.proxyAuthenticationRequired.connect(
            proxyAuthenticationRequired
        )

        self.__loop = QEventLoop()
        self.__networkManager.finished.connect(self.__loop.quit)

    def get(self, requestUrl, extraHeaders=None):
        """
        Public method to issue a GET request.

        @param requestUrl URL of the request
        @type QUrl
        @param extraHeaders list of tuples of additional headers giving
            header name and header value
        @type tuple of (bytes, bytes)
        @return server response or an error message and a success flag
        @rtype tuple of (QByteArray or str, bool)
        """
        request = QNetworkRequest(requestUrl)
        if extraHeaders:
            for name, value in extraHeaders:
                request.setRawHeader(name, value)
        reply = self.__networkManager.get(request)
        if not self.__loop.isRunning():
            self.__loop.exec()
        if reply.error() != QNetworkReply.NetworkError.NoError:
            return reply.errorString(), False
        else:
            return reply.readAll(), True

    def post(self, requestUrl, requestData, dataType="form", extraHeaders=None):
        """
        Public method to issue a POST request.

        @param requestUrl URL of the request
        @type QUrl
        @param requestData data of the request
        @type QByteArray
        @param dataType type of the request data
        @type str
        @param extraHeaders list of tuples of additional headers giving
            header name and header value
        @type list of tuple of (bytes, bytes)
        @return tuple of server response (string) and flag indicating
            success (boolean)
        @rtype tuple of (str, bool)
        """
        request = QNetworkRequest(requestUrl)
        request.setRawHeader(b"User-Agent", b"Mozilla/5.0")
        request.setRawHeader(b"Content-Type", self.__contentTypes[dataType])
        request.setRawHeader(b"Content-Length", QByteArray.number(requestData.size()))
        if extraHeaders:
            for name, value in extraHeaders:
                request.setRawHeader(name, value)
        request.setUrl(requestUrl)
        reply = self.__networkManager.post(request, requestData)
        if not self.__loop.isRunning():
            self.__loop.exec()
        if reply.error() != QNetworkReply.NetworkError.NoError:
            return reply.errorString(), False
        else:
            return str(reply.readAll(), "utf-8", "replace"), True
