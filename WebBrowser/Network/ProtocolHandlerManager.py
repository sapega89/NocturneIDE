# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the protocol handler manager.
"""

import contextlib
import json
import os

from PyQt6.QtCore import QObject, QUrl
from PyQt6.QtWebEngineCore import QWebEnginePage

from eric7 import EricUtilities


class ProtocolHandlerManager(QObject):
    """
    Class implementing the protocol handler manager.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__protocolHandlers = {}
        # dictionary of handlers with scheme as key

        self.__load()

    def protocolHandler(self, scheme):
        """
        Public method to get the protocol handler URL for a given scheme.

        @param scheme scheme to look for
        @type str
        @return protocol handler URL
        @rtype QUrl
        """
        try:
            return QUrl(self.__protocolHandlers[scheme])
        except KeyError:
            return QUrl()

    def protocolHandlers(self):
        """
        Public method to get the registered protocol handlers.

        @return dictionary containing the registered protocol handlers
        @rtype dict
        """
        return {s: QUrl(u) for s, u in self.__protocolHandlers.items()}

    def addProtocolHandler(self, scheme, url):
        """
        Public method to add a protocol handler for a scheme.

        @param scheme scheme of the protocol handler
        @type str
        @param url URL of the protocol handler
        @type QUrl
        """
        if bool(scheme) and not url.isEmpty():
            self.__protocolHandlers[scheme] = url
            self.__registerHandler(scheme, url)
            self.__save()

    def removeProtocolHandler(self, scheme):
        """
        Public method to remove the protocol handler for a given scheme.

        @param scheme scheme to remove
        @type str
        """
        if scheme in self.__protocolHandlers:
            self.__unregisterHandler(scheme, self.__protocolHandlers[scheme])
            del self.__protocolHandlers[scheme]
            self.__save()

    def __protocolHandlersFileName(self):
        """
        Private method to determine the protocol handlers file name.

        @return name of the protocol handlers file
        @rtype str
        """
        return os.path.join(
            EricUtilities.getConfigDir(), "web_browser", "protocol_handlers.json"
        )

    def __load(self):
        """
        Private method to load the registered protocol handlers.
        """
        with contextlib.suppress(OSError):
            with open(self.__protocolHandlersFileName(), "r") as protocolHandlersFile:
                protocolHandlersData = json.load(protocolHandlersFile)

            if protocolHandlersData:
                self.__protocolHandlers = {}
                for scheme, urlStr in protocolHandlersData.items():
                    url = QUrl(urlStr)
                    self.__protocolHandlers[scheme] = url
                    self.__registerHandler(scheme, url)

    def __save(self):
        """
        Private method to save the protocol handlers.
        """
        protocolHandlers = {
            scheme: url.toString() for scheme, url in self.__protocolHandlers.items()
        }

        with open(self.__protocolHandlersFileName(), "w") as protocolHandlersFile:
            json.dump(protocolHandlers, protocolHandlersFile, indent=2)

    def __registerHandler(self, scheme, url):
        """
        Private method to register a protocol handler for a scheme.

        @param scheme scheme of the protocol handler
        @type str
        @param url URL of the protocol handler
        @type QUrl
        """
        urlStr = url.toString().replace("%25s", "%s")

        page = QWebEnginePage(self)
        page.loadFinished.connect(page.deleteLater)
        page.registerProtocolHandlerRequested.connect(lambda r: r.accept())
        page.setHtml(
            "<script>navigator.registerProtocolHandler('{0}', '{1}', '')"
            "</script>".format(scheme, urlStr),
            url,
        )

    def __unregisterHandler(self, scheme, url):
        """
        Private method to unregister a protocol handler for a scheme.

        @param scheme scheme of the protocol handler
        @type str
        @param url URL of the protocol handler
        @type QUrl
        """
        urlStr = url.toString().replace("%25s", "%s")

        page = QWebEnginePage(self)
        page.loadFinished.connect(page.deleteLater)
        page.setHtml(
            "<script>navigator.unregisterProtocolHandler('{0}', '{1}', '')"
            "</script>".format(scheme, urlStr),
            url,
        )

    def showProtocolHandlerManagerDialog(self):
        """
        Public method to show the protocol handler manager dialog.
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        from .ProtocolHandlerManagerDialog import ProtocolHandlerManagerDialog

        dlg = ProtocolHandlerManagerDialog(self, WebBrowserWindow.getWindow())
        dlg.open()
