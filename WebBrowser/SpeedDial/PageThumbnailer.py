# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an object to create a thumbnail image of a web site.
"""

from PyQt6.QtCore import QObject, QSize, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtWebEngineWidgets import QWebEngineView


class PageThumbnailer(QObject):
    """
    Class implementing a thumbnail creator for web sites.

    @signal thumbnailCreated(QPixmap) emitted after the thumbnail has been
        created
    """

    thumbnailCreated = pyqtSignal(QPixmap)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__size = QSize(231, 130)
        self.__loadTitle = False
        self.__title = ""
        self.__url = QUrl()

        self.__view = QWebEngineView()
        self.__view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.__view.resize(1920, 1080)
        self.__view.show()

    def setSize(self, size):
        """
        Public method to set the size of the image.

        @param size size of the image
        @type QSize
        """
        if size.isValid():
            self.__size = QSize(size)

    def setUrl(self, url):
        """
        Public method to set the URL of the site to be thumbnailed.

        @param url URL of the web site
        @type QUrl
        """
        if url.isValid():
            self.__url = QUrl(url)

    def url(self):
        """
        Public method to get the URL of the thumbnail.

        @return URL of the thumbnail
        @rtype QUrl
        """
        return QUrl(self.__url)

    def loadTitle(self):
        """
        Public method to check, if the title is loaded from the web site.

        @return flag indicating, that the title is loaded
        @rtype bool
        """
        return self.__loadTitle

    def setLoadTitle(self, load):
        """
        Public method to set a flag indicating to load the title from
        the web site.

        @param load flag indicating to load the title
        @type bool
        """
        self.__loadTitle = load

    def title(self):
        """
        Public method to get the title of the thumbnail.

        @return title of the thumbnail
        @rtype str
        """
        title = self.__title if self.__title else self.__url.host()
        if not title:
            title = self.__url.toString()
        return title

    def start(self):
        """
        Public method to start the thumbnailing action.
        """
        self.__view.loadFinished.connect(self.__createThumbnail)
        self.__view.load(self.__url)

    def __createThumbnail(self, status):
        """
        Private slot creating the thumbnail of the web site.

        @param status flag indicating a successful load of the web site
        @type bool
        """
        if not status:
            self.thumbnailCreated.emit(QPixmap())
            return

        QTimer.singleShot(1000, self.__grabThumbnail)

    def __grabThumbnail(self):
        """
        Private slot to grab the thumbnail image from the view.
        """
        self.__title = self.__view.title()

        image = QImage(self.__view.size(), QImage.Format.Format_ARGB32)
        painter = QPainter(image)
        self.__view.render(painter)
        painter.end()

        scaledImage = image.scaled(
            self.__size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.thumbnailCreated.emit(QPixmap.fromImage(scaledImage))
