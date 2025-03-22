# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the speed dial.
"""

import os

from PyQt6.QtCore import (
    QByteArray,
    QCryptographicHash,
    QObject,
    QUrl,
    pyqtSignal,
    pyqtSlot,
    qWarning,
)

from eric7 import EricUtilities
from eric7.EricWidgets import EricMessageBox
from eric7.Utilities.AutoSaver import AutoSaver

from ..Tools.WebBrowserTools import pixmapFileToDataUrl
from .Page import Page


class SpeedDial(QObject):
    """
    Class implementing the speed dial.

    @signal pagesChanged() emitted after the list of pages changed
    @signal thumbnailLoaded(url, src) emitted after a thumbnail was loaded
    @signal pageTitleLoaded(url, title) emitted after a title was loaded
    @signal speedDialSaved() emitted after the speed dial data was saved
    """

    pagesChanged = pyqtSignal()
    thumbnailLoaded = pyqtSignal(str, str)
    pageTitleLoaded = pyqtSignal(str, str)
    speedDialSaved = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__regenerateScript = True

        self.__webPages = []

        self.__initialScript = ""
        self.__thumbnailsDirectory = ""

        self.__thumbnailers = []

        self.__initialize()

        self.__saveTimer = AutoSaver(self, self.save)
        self.pagesChanged.connect(self.__saveTimer.changeOccurred)

    def addPage(self, url, title):
        """
        Public method to add a page for the given data.

        @param url URL of the page
        @type QUrl
        @param title title of the page
        @type str
        """
        if url.isEmpty():
            return

        page = Page(self.__escapeUrl(url.toString()), self.__escapeTitle(title))
        self.__webPages.append(page)
        self.__regenerateScript = True

        self.pagesChanged.emit()

    def removePage(self, url):
        """
        Public method to remove a page.

        @param url URL of the page
        @type QUrl
        """
        page = self.pageForUrl(url)
        if not page.isValid():
            return

        self.removeImageForUrl(page.url)
        self.__webPages.remove(page)
        self.__regenerateScript = True

        self.pagesChanged.emit()

    def __imageFileName(self, url):
        """
        Private method to generate the image file name for a URL.

        @param url URL to generate the file name from
        @type str
        @return name of the image file
        @rtype str
        """
        return os.path.join(
            self.__thumbnailsDirectory,
            str(
                QCryptographicHash.hash(
                    QByteArray(url.encode("utf-8")), QCryptographicHash.Algorithm.Md5
                ).toHex(),
                encoding="utf-8",
            )
            + ".png",
        )

    def initialScript(self):
        """
        Public method to get the 'initial' JavaScript script.

        @return initial JavaScript script
        @rtype str
        """
        if self.__regenerateScript:
            self.__regenerateScript = False
            self.__initialScript = ""

            for page in self.__webPages:
                if page.broken:
                    imgSource = pixmapFileToDataUrl("brokenPage.png", True)
                else:
                    imgSource = self.__imageFileName(page.url)
                    if not os.path.exists(imgSource):
                        self.loadThumbnail(page.url, False)
                        imgSource = pixmapFileToDataUrl("loading.gif", True)

                        if not page.url:
                            imgSource = ""
                    else:
                        imgSource = pixmapFileToDataUrl(imgSource, True)

                self.__initialScript += ("addBox('{0}', '{1}', '{2}');\n").format(
                    page.url, EricUtilities.html_uencode(page.title), imgSource
                )

        return self.__initialScript

    def getFileName(self):
        """
        Public method to get the file name of the user agents file.

        @return name of the user agents file
        @rtype str
        """
        return os.path.join(
            EricUtilities.getConfigDir(), "web_browser", "speedDial.xml"
        )

    def __initialize(self):
        """
        Private method to initialize the speed dial.
        """
        self.__thumbnailsDirectory = os.path.join(
            EricUtilities.getConfigDir(), "web_browser", "thumbnails"
        )
        # Create directory if it does not exist yet
        if not os.path.exists(self.__thumbnailsDirectory):
            os.makedirs(self.__thumbnailsDirectory)

        self.__load()

    def reload(self):
        """
        Public method to reload the speed dial data.
        """
        self.__load()

    def __load(self):
        """
        Private method to load the speed dial configuration.
        """
        from .SpeedDialReader import SpeedDialReader

        allPages, pagesPerRow, speedDialSize = [], 0, 0

        speedDialFile = self.getFileName()
        if os.path.exists(speedDialFile):
            reader = SpeedDialReader()
            allPages, pagesPerRow, speedDialSize = reader.read(speedDialFile)

        self.__pagesPerRow = pagesPerRow if pagesPerRow else 4
        self.__speedDialSize = speedDialSize if speedDialSize else 231

        if allPages:
            self.__webPages = allPages
            self.pagesChanged.emit()
        else:
            allPages = (
                'url:"https://eric-ide.python-projects.org/"|'
                'title:"Eric Web Site";'
                'url:"https://www.riverbankcomputing.com/"|'
                'title:"PyQt Web Site";'
                'url:"https://www.qt.io/"|title:"Qt Web Site";'
                'url:"https://blog.qt.io/"|title:"Qt Blog";'
                'url:"https://www.python.org"|'
                'title:"Python Language Website";'
                'url:"https://www.google.com"|title:"Google";'
            )
            self.changed(allPages)

    def save(self):
        """
        Public method to save the speed dial configuration.
        """
        from .SpeedDialWriter import SpeedDialWriter

        speedDialFile = self.getFileName()
        writer = SpeedDialWriter()
        if not writer.write(
            speedDialFile, self.__webPages, self.__pagesPerRow, self.__speedDialSize
        ):
            EricMessageBox.critical(
                None,
                self.tr("Saving Speed Dial data"),
                self.tr(
                    """<p>Speed Dial data could not be saved to <b>{0}</b></p>"""
                ).format(speedDialFile),
            )
        else:
            self.speedDialSaved.emit()

    def resetDials(self):
        """
        Public method to reset the speed dials to the default values.
        """
        ok = EricMessageBox.yesNo(
            None,
            self.tr("Reset Speed Dials"),
            self.tr(
                """Are you sure you want to reset the speed dials to"""
                """ the default pages?"""
            ),
        )
        if ok:
            speedDialFile = self.getFileName()
            if os.path.exists(speedDialFile):
                os.remove(speedDialFile)
            self.__regenerateScript = True

            self.__load()

    def close(self):
        """
        Public method to close the user agents manager.
        """
        self.__saveTimer.saveIfNeccessary()

    def pageForUrl(self, url):
        """
        Public method to get the page for the given URL.

        @param url URL to be searched for
        @type QUrl
        @return page for the URL
        @rtype Page
        """
        urlString = url.toString()
        if urlString.endswith("/"):
            urlString = urlString[:-1]

        for page in self.__webPages:
            if page.url == urlString:
                return page

        return Page()

    def urlForShortcut(self, key):
        """
        Public method to get the URL for the given shortcut key.

        @param key shortcut key
        @type int
        @return URL for the key
        @rtype QUrl
        """
        if key < 0 or len(self.__webPages) <= key:
            return QUrl()

        return QUrl.fromEncoded(self.__webPages[key].url.encode("utf-8"))

    @pyqtSlot(str)
    def changed(self, allPages):
        """
        Public slot to react on changed pages.

        @param allPages string giving all pages
        @type str
        """
        if not allPages:
            return

        entries = allPages.split('";')
        self.__webPages = []
        self.__regenerateScript = True

        for entry in entries:
            if not entry:
                continue

            tmp = entry.split('"|')
            if len(tmp) == 2:
                broken = False
            elif len(tmp) == 3:
                broken = "brokenPage" in tmp[2][5:]
            else:
                continue

            url = tmp[0][5:]
            if url.endswith("/"):
                url = url[:-1]
            title = tmp[1][7:]
            page = Page(url, title, broken)
            self.__webPages.append(page)

        self.pagesChanged.emit()

    @pyqtSlot(str, bool)
    def loadThumbnail(self, urlStr, loadTitle):
        """
        Public slot to load a thumbnail of the given URL.

        @param urlStr URL of the thumbnail
        @type str
        @param loadTitle flag indicating to get the title for the thumbnail
            from the site
        @type bool
        """
        from .PageThumbnailer import PageThumbnailer

        if not urlStr:
            return

        url = QUrl.fromEncoded(urlStr.encode("utf-8"))
        if not url.host():
            return

        thumbnailer = PageThumbnailer(self)
        thumbnailer.setUrl(url)
        thumbnailer.setLoadTitle(loadTitle)
        thumbnailer.thumbnailCreated.connect(
            lambda imag: self.__thumbnailCreated(imag, thumbnailer)
        )
        self.__thumbnailers.append(thumbnailer)

        thumbnailer.start()

    @pyqtSlot(str)
    def removeImageForUrl(self, url):
        """
        Public slot to remove the image for a URL.

        @param url URL to remove the image for
        @type str
        """
        fileName = self.__imageFileName(url)
        if os.path.exists(fileName):
            os.remove(fileName)

    @pyqtSlot(str, result=str)
    def urlFromUserInput(self, url):
        """
        Public slot to get the URL from user input.

        @param url URL entered by the user
        @type str
        @return sanitized URL
        @rtype str
        """
        return QUrl.fromUserInput(url).toString()

    @pyqtSlot(int)
    def setPagesInRow(self, count):
        """
        Public slot to set the number of pages per row.

        @param count number of pages per row
        @type int
        """
        self.__pagesPerRow = count
        self.__saveTimer.changeOccurred()

    def pagesInRow(self):
        """
        Public method to get the number of dials per row.

        @return number of dials per row
        @rtype int
        """
        return self.__pagesPerRow

    @pyqtSlot(int)
    def setSdSize(self, size):
        """
        Public slot to set the size of the speed dial.

        @param size size of the speed dial
        @type int
        """
        self.__speedDialSize = size
        self.__saveTimer.changeOccurred()

    def sdSize(self):
        """
        Public method to get the speed dial size.

        @return speed dial size
        @rtype int
        """
        return self.__speedDialSize

    def __thumbnailCreated(self, image, thumbnailer):
        """
        Private slot to handle the creation of a thumbnail image.

        @param image thumbnail image
        @type QPixmap
        @param thumbnailer reference to the page thumbnailer
        @type PageThumbnailer
        """
        if thumbnailer in self.__thumbnailers:
            loadTitle = thumbnailer.loadTitle()
            title = thumbnailer.title()
            url = thumbnailer.url().toString()
            fileName = self.__imageFileName(url)

            if image.isNull():
                fileName = "brokenPage.png"
                title = self.tr("Unable to load")
                page = self.pageForUrl(thumbnailer.url())
                page.broken = True
            else:
                if not image.save(fileName, "PNG"):
                    qWarning(
                        "SpeedDial.__thumbnailCreated: Cannot save thumbnail"
                        " to {0}".format(fileName)
                    )

            self.__regenerateScript = True
            thumbnailer.deleteLater()
            self.__thumbnailers.remove(thumbnailer)

            if loadTitle:
                self.pageTitleLoaded.emit(url, title)

            self.thumbnailLoaded.emit(url, pixmapFileToDataUrl(fileName, True))

    def __escapeTitle(self, title):
        """
        Private method to escape a title string.

        @param title title string to be escaped
        @type str
        @return escaped title string
        @rtype str
        """
        title = title.replace('"', "&quot;").replace("'", "&apos;")
        return title

    def __escapeUrl(self, url):
        """
        Private method to escape an URL string.

        @param url URL to be escaped
        @type str
        @return escaped URL string
        @rtype str
        """
        url = url.replace('"', "").replace("'", "")
        return url
