# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the image search engine.
"""

from PyQt6.QtCore import QObject, QUrl

from eric7 import Preferences


class ImageSearchEngine(QObject):
    """
    Class implementing the image search engine.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__searchEngineNames = ["Google", "TinEye", "Yandex"]

    def searchEngine(self):
        """
        Public method to get the name of the current search engine.

        @return name of the current search engine
        @rtype str
        """
        return Preferences.getWebBrowser("ImageSearchEngine")

    def setSearchEngine(self, searchEngine):
        """
        Public method to set the current search engine.

        @param searchEngine name of the search engine
        @type str
        """
        Preferences.setWebBrowser("ImageSearchEngine", searchEngine)

    def searchEngineNames(self):
        """
        Public method to get the list of supported search engines.

        @return list of supported search engines
        @rtype list of str
        """
        return self.__searchEngineNames[:]

    def getSearchQuery(self, imageUrl, searchEngine=None):
        """
        Public method to get the image search query URL.

        @param imageUrl URL of the image to search for
        @type QUrl
        @param searchEngine name of the image search engine to be used
        @type str
        @return search query URL
        @rtype QUrl
        """
        searchEngineUrlTemplates = {
            "google": "https://www.google.com/searchbyimage?site=search&image_url={0}",
            "yandex": "https://yandex.com/images/search?&img_url={0}&rpt=imageview",
            "tineye": "http://www.tineye.com/search?url={0}",
        }
        if not searchEngine:
            searchEngine = self.searchEngine()

        try:
            return QUrl(
                searchEngineUrlTemplates[searchEngine.lower()].format(
                    imageUrl.toString()
                )
            )
        except KeyError:
            return QUrl()
