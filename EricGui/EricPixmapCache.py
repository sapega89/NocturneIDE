# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a pixmap cache for icons.
"""

import os

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QIcon, QPainter, QPixmap


class EricPixmapCache:
    """
    Class implementing a pixmap cache for icons.
    """

    SupportedExtensionsVector = [".svgz", ".svg"]
    SupportedExtensionsPixel = [".png"]

    def __init__(self):
        """
        Constructor
        """
        self.EricPixmapCache = {}
        self.searchPath = []
        self.__extensions = (
            EricPixmapCache.SupportedExtensionsVector
            + EricPixmapCache.SupportedExtensionsPixel
        )

    def getPixmap(self, key, size=None):
        """
        Public method to retrieve a pixmap.

        @param key name of the wanted pixmap
        @type str
        @param size requested size (defaults to None)
        @type QSize (optional)
        @return the requested pixmap
        @rtype QPixmap
        """
        if key:
            basename, _ext = os.path.splitext(key)
            if size and not size.isEmpty():
                key = "{0}_{1}_{2}".format(basename, size.width(), size.height())
            else:
                key = basename

            try:
                return self.EricPixmapCache[key]
            except KeyError:
                pm = QPixmap()
                for extension in self.__extensions:
                    filename = basename + extension
                    if not os.path.isabs(filename):
                        for path in self.searchPath:
                            pm = QPixmap(path + "/" + filename)
                            if not pm.isNull():
                                break
                    else:
                        pm = QPixmap(filename)
                    if not pm.isNull():
                        if size and not size.isEmpty():
                            pm = pm.scaled(size)
                        break
                else:
                    pm = QPixmap()

                self.EricPixmapCache[key] = pm
                return self.EricPixmapCache[key]

        return QPixmap()

    def addSearchPath(self, path):
        """
        Public method to add a path to the search path.

        @param path path to add
        @type str
        """
        if path not in self.searchPath:
            self.searchPath.append(path)

    def removeSearchPath(self, path):
        """
        Public method to remove a path from the search path.

        @param path path to remove
        @type str
        """
        if path in self.searchPath:
            self.searchPath.remove(path)

    def setPreferVectorIcons(self, vectorFirst=True):
        """
        Public method to set the preference of vector based icons.

        @param vectorFirst flag indicating the preference of vector icons
            (defaults to True)
        @type bool (optional)
        """
        self.__extensions = (
            EricPixmapCache.SupportedExtensionsVector
            + EricPixmapCache.SupportedExtensionsPixel
            if vectorFirst
            else EricPixmapCache.SupportedExtensionsPixel
            + EricPixmapCache.SupportedExtensionsVector
        )


pixCache = EricPixmapCache()


def getPixmap(key, size=None, cache=pixCache):
    """
    Module function to retrieve a pixmap.

    @param key name of the wanted pixmap
    @type str
    @param size requested size (defaults to None)
    @type QSize (optional)
    @param cache reference to the pixmap cache object (defaults to pixCache)
    @type EricPixmapCache (optional)
    @return the requested pixmap
    @rtype QPixmap
    """
    return cache.getPixmap(key, size=size)


def getIcon(key, size=None, cache=pixCache):
    """
    Module function to retrieve an icon.

    @param key name of the wanted pixmap
    @type str
    @param size requested size (defaults to None)
    @type QSize (optional)
    @param cache reference to the pixmap cache object (defaults to pixCache)
    @type EricPixmapCache (optional)
    @return the requested icon
    @rtype QIcon
    """
    return QIcon(cache.getPixmap(key, size=size))


def getSymlinkIcon(key, size=None, cache=pixCache):
    """
    Module function to retrieve a symbolic link icon.

    @param key name of the wanted pixmap
    @type str
    @param size requested size (defaults to None)
    @type QSize (optional)
    @param cache reference to the pixmap cache object (defaults to pixCache)
    @type EricPixmapCache (optional)
    @return the requested icon
    @rtype QIcon
    """
    pix1 = QPixmap(cache.getPixmap(key, size=size))
    pix2 = cache.getPixmap("symlink")
    painter = QPainter(pix1)
    painter.drawPixmap(0, 10, pix2)
    painter.end()
    return QIcon(pix1)


def getCombinedIcon(keys, size=None, cache=pixCache):
    """
    Module function to retrieve a symbolic link icon.

    @param keys list of names of icons
    @type list of str
    @param size requested size of individual icons (defaults to None)
    @type QSize (optional)
    @param cache reference to the pixmap cache object (defaults to pixCache)
    @type EricPixmapCache (optional)
    @return the requested icon
    @rtype QIcon
    """
    height = width = 0
    pixmaps = []
    for key in keys:
        pix = cache.getPixmap(key, size=size)
        if not pix.isNull():
            height = max(height, pix.height())
            width = max(width, pix.width())
            pixmaps.append(pix)
    if pixmaps:
        pix = QPixmap(len(pixmaps) * width, height)
        pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pix)
        x = 0
        for pixmap in pixmaps:
            painter.drawPixmap(x, 0, pixmap.scaled(QSize(width, height)))
            x += width
        painter.end()
        icon = QIcon(pix)
    else:
        icon = QIcon()
    return icon


def addSearchPath(path, cache=pixCache):
    """
    Module function to add a path to the search path.

    @param path path to add
    @type str
    @param cache reference to the pixmap cache object (defaults to pixCache)
    @type EricPixmapCache (optional)
    """
    cache.addSearchPath(path)


def removeSearchPath(path, cache=pixCache):
    """
    Public method to remove a path from the search path.

    @param path path to remove
    @type str
    @param cache reference to the pixmap cache object (defaults to pixCache)
    @type EricPixmapCache (optional)
    """
    cache.removeSearchPath(path)


def setPreferVectorIcons(vectorFirst=True, cache=pixCache):
    """
    Function to set the preference of vector based icons.

    @param vectorFirst flag indicating the preference of vector icons
        (defaults to True)
    @type bool (optional)
    @param cache reference to the pixmap cache object (defaults to pixCache)
    @type EricPixmapCache (optional)
    """
    cache.setPreferVectorIcons(vectorFirst)
