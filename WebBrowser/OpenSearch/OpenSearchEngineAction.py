# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a QAction subclass for open search.
"""

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QAction, QIcon, QPixmap

from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow


class OpenSearchEngineAction(QAction):
    """
    Class implementing a QAction subclass for open search.
    """

    def __init__(self, engine, parent=None):
        """
        Constructor

        @param engine reference to the open search engine object
        @type OpenSearchEngine
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__engine = engine
        if self.__engine.networkAccessManager() is None:
            self.__engine.setNetworkAccessManager(WebBrowserWindow.networkManager())

        self.setText(engine.name())
        self.__imageChanged()

        engine.imageChanged.connect(self.__imageChanged)

    def __imageChanged(self):
        """
        Private slot handling a change of the associated image.
        """
        image = self.__engine.image()
        if image.isNull():
            self.setIcon(WebBrowserWindow.icon(QUrl(self.__engine.imageUrl())))
        else:
            self.setIcon(QIcon(QPixmap.fromImage(image)))
