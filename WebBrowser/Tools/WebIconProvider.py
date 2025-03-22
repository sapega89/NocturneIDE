# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module containing a web site icon storage object.
"""

import contextlib
import json
import os

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QObject, QUrl, pyqtSignal
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtWidgets import QDialog

from eric7.EricGui import EricPixmapCache
from eric7.Utilities.AutoSaver import AutoSaver


class WebIconProvider(QObject):
    """
    Class implementing a web site icon storage.

    @signal changed() emitted to indicate a change of the icons database
    """

    changed = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__encoding = "iso-8859-1"
        self.__iconsFileName = "web_site_icons.json"
        self.__iconDatabasePath = ""  # saving of icons disabled

        self.__iconsDB = {}
        self.__loaded = False

        self.__saveTimer = AutoSaver(self, self.save)

        self.changed.connect(self.__saveTimer.changeOccurred)

    def setIconDatabasePath(self, path):
        """
        Public method to set the path for the web site icons store.

        @param path path to store the icons file to
        @type str
        """
        if path != self.__iconDatabasePath:
            self.close()

        self.__iconDatabasePath = path

    def iconDatabasePath(self):
        """
        Public method o get the path for the web site icons store.

        @return path to store the icons file to
        @rtype str
        """
        return self.__iconDatabasePath

    def close(self):
        """
        Public method to close the web icon provider.
        """
        self.__saveTimer.saveIfNeccessary()
        self.__loaded = False
        self.__iconsDB = {}

    def load(self):
        """
        Public method to load the web site icons.
        """
        if self.__loaded:
            return

        if self.__iconDatabasePath:
            filename = os.path.join(self.__iconDatabasePath, self.__iconsFileName)
            try:
                with open(filename, "r") as f:
                    db = json.load(f)
            except OSError:
                # ignore silentyl
                db = {}

            self.__iconsDB = {}
            for url, data in db.items():
                self.__iconsDB[url] = QIcon(
                    QPixmap.fromImage(
                        QImage.fromData(QByteArray(data.encode(self.__encoding)))
                    )
                )

        self.__loaded = True

    def save(self):
        """
        Public method to save the web site icons.
        """
        if not self.__loaded:
            return

        from eric7.WebBrowser.WebBrowserWindow import (  # __IGNORE_WARNING_I101__
            WebBrowserWindow,
        )

        if not WebBrowserWindow.isPrivate() and bool(self.__iconDatabasePath):
            db = {}
            for url, icon in self.__iconsDB.items():
                ba = QByteArray()
                buffer = QBuffer(ba)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                icon.pixmap(32).toImage().save(buffer, "PNG")
                db[url] = bytes(buffer.data()).decode(self.__encoding)

            filename = os.path.join(self.__iconDatabasePath, self.__iconsFileName)
            with contextlib.suppress(OSError), open(filename, "w") as f:
                json.dump(db, f)

    def saveIcon(self, view):
        """
        Public method to save a web site icon.

        @param view reference to the view object
        @type WebBrowserView
        """
        scheme = view.url().scheme()
        if scheme in ["eric", "about", "qthelp", "file", "abp", "ftp"]:
            return

        self.load()

        if view.mainWindow().isPrivate():
            return

        urlStr = self.__urlToString(view.url())
        self.__iconsDB[urlStr] = view.icon()

        self.changed.emit()

    def __urlToString(self, url):
        """
        Private method to convert an URL to a string.

        @param url URL to be converted
        @type QUrl
        @return string representation of the URL
        @rtype str
        """
        return url.toString(
            QUrl.UrlFormattingOption.RemoveUserInfo
            | QUrl.UrlFormattingOption.RemoveFragment
            | QUrl.UrlFormattingOption.RemovePath
        )

    def iconForUrl(self, url):
        """
        Public method to get an icon for an URL.

        @param url URL to get icon for
        @type QUrl
        @return icon for the URL
        @rtype QIcon
        """
        scheme2iconName = {
            "eric": "ericWeb",
            "about": "ericWeb",
            "qthelp": "qthelp",
            "file": "fileMisc",
            "abp": "adBlockPlus",
            "ftp": "network-server",
        }

        scheme = url.scheme()
        iconName = scheme2iconName.get(scheme)
        if iconName:
            return EricPixmapCache.getIcon(iconName)

        self.load()

        urlStr = self.__urlToString(url)
        if urlStr in self.__iconsDB:
            return self.__iconsDB[urlStr]
        else:
            for iconUrlStr in self.__iconsDB:
                if iconUrlStr.startswith(urlStr):
                    return self.__iconsDB[iconUrlStr]

        # try replacing http scheme with https scheme
        url = QUrl(url)
        if url.scheme() == "http":
            url.setScheme("https")
            urlStr = self.__urlToString(url)
            if urlStr in self.__iconsDB:
                return self.__iconsDB[urlStr]
            else:
                for iconUrlStr in self.__iconsDB:
                    if iconUrlStr.startswith(urlStr):
                        return self.__iconsDB[iconUrlStr]

        if scheme == "https":
            return EricPixmapCache.getIcon("securityHigh32")
        else:
            return EricPixmapCache.getIcon("defaultIcon")

    def clear(self):
        """
        Public method to clear the icons cache.
        """
        self.load()
        self.__iconsDB = {}
        self.changed.emit()
        self.__saveTimer.saveIfNeccessary()

    def showWebIconDialog(self, parent=None):
        """
        Public method to show a dialog to manage the Favicons.

        @param parent reference to the parent widget
        @type QWidget
        """
        from .WebIconDialog import WebIconDialog

        self.load()

        dlg = WebIconDialog(self.__iconsDB, parent=parent)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            changed = False
            urls = dlg.getUrls()
            for url in list(self.__iconsDB):
                if url not in urls:
                    del self.__iconsDB[url]
                    changed = True
            if changed:
                self.changed.emit()


_WebIconProvider = None


def instance():
    """
    Global function to get a reference to the web icon provider and create it,
    if it hasn't been yet.

    @return reference to the web icon provider object
    @rtype WebIconProvider
    """
    global _WebIconProvider

    if _WebIconProvider is None:
        _WebIconProvider = WebIconProvider()

    return _WebIconProvider
