# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a manager for site specific zoom level settings.
"""

import contextlib
import json

from PyQt6.QtCore import QObject, pyqtSignal

from eric7 import Preferences
from eric7.Utilities.AutoSaver import AutoSaver


class ZoomManager(QObject):
    """
    Class implementing a manager for site specific zoom level settings.

    @signal changed() emitted to indicate a change of the zoom level
    """

    changed = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__zoomDB = {}

        self.__saveTimer = AutoSaver(self, self.save)

        self.changed.connect(self.__saveTimer.changeOccurred)

        self.__loaded = False

    def close(self):
        """
        Public method to close the zoom manager.
        """
        self.__saveTimer.saveIfNeccessary()

    def load(self):
        """
        Public method to load the bookmarks.
        """
        if self.__loaded:
            return

        dbString = Preferences.getWebBrowser("ZoomValuesDB")
        if dbString:
            with contextlib.suppress(ValueError):
                db = json.loads(dbString)
                self.__zoomDB = db

        self.__loaded = True

    def save(self):
        """
        Public method to save the zoom values.
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        if not self.__loaded:
            return

        if not WebBrowserWindow.isPrivate():
            dbString = json.dumps(self.__zoomDB)
            Preferences.setWebBrowser("ZoomValuesDB", dbString)

    def __keyFromUrl(self, url):
        """
        Private method to generate a DB key for an URL.

        @param url URL to generate a key for
        @type QUrl
        @return key for the given URL
        @rtype str
        """
        if url.isEmpty():
            key = ""
        else:
            scheme = url.scheme()
            host = url.host()
            if host:
                key = host
            elif scheme == "file":
                path = url.path()
                key = path.rsplit("/", 1)[0]
            else:
                key = ""

        return key

    def setZoomValue(self, url, zoomValue):
        """
        Public method to record the zoom value for the given URL.

        Note: Only zoom values not equal 100% are recorded.

        @param url URL of the page to remember the zoom value for
        @type QUrl
        @param zoomValue zoom value for the URL
        @type int
        """
        self.load()

        key = self.__keyFromUrl(url)
        if not key:
            return

        if (zoomValue == 100 and key not in self.__zoomDB) or (
            key in self.__zoomDB and self.__zoomDB[key] == zoomValue
        ):
            return

        if zoomValue == 100:
            del self.__zoomDB[key]
        else:
            self.__zoomDB[key] = zoomValue

        self.changed.emit()

    def zoomValue(self, url):
        """
        Public method to get the zoom value for an URL.

        @param url URL of the page to get the zoom value for
        @type QUrl
        @return zoomValue zoom value for the URL
        @rtype int
        """
        self.load()

        key = self.__keyFromUrl(url)
        if not key:
            zoom = 100

        # default zoom value (i.e. no zoom)
        zoom = self.__zoomDB.get(key, 100)

        return zoom

    def clear(self):
        """
        Public method to clear the saved zoom values.
        """
        self.__zoomDB = {}
        self.__loaded = True

        self.changed.emit()

    def removeZoomValue(self, site):
        """
        Public method to remove a zoom value entry.

        @param site web site name
        @type str
        """
        self.load()

        if site in self.__zoomDB:
            del self.__zoomDB[site]
            self.changed.emit()

    def allSiteNames(self):
        """
        Public method to get a list of all site names.

        @return sorted list of all site names
        @rtype list of str
        """
        self.load()

        return sorted(self.__zoomDB)

    def sitesCount(self):
        """
        Public method to get the number of available sites.

        @return number of sites
        @rtype int
        """
        self.load()

        return len(self.__zoomDB)

    def siteInfo(self, site):
        """
        Public method to get the zoom value for the site.

        @param site web site name
        @type str
        @return zoom value for the site
        @rtype int
        """
        self.load()

        if site not in self.__zoomDB:
            return None

        return self.__zoomDB[site]


_ZoomManager = None


def instance():
    """
    Global function to get a reference to the zoom manager and create it, if
    it hasn't been yet.

    @return reference to the zoom manager object
    @rtype ZoomManager
    """
    global _ZoomManager

    if _ZoomManager is None:
        _ZoomManager = ZoomManager()

    return _ZoomManager
