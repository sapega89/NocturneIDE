# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an importer for XBEL files.
"""

import os

from PyQt6.QtCore import QCoreApplication, QDate, Qt, QXmlStreamReader

from eric7.EricGui import EricPixmapCache

from ..BookmarksManager import BookmarksManager
from .BookmarksImporter import BookmarksImporter


def getImporterInfo(sourceId):
    """
    Module function to get information for the given XBEL source id.

    @param sourceId id of the browser
    @type str
    @return tuple with an icon, readable name, name of the default
        bookmarks file, an info text, a prompt and the default directory
        of the bookmarks file
    @rtype tuple of (QPixmap, str, str, str, str, str)
    @exception ValueError raised to indicate an invalid browser ID
    """
    if sourceId not in ("e5browser", "konqueror", "xbel"):
        raise ValueError("Unsupported browser ID given ({0}).".format(sourceId))

    if sourceId == "e5browser":
        bookmarksFile = BookmarksManager.getFileName()
        return (
            EricPixmapCache.getPixmap("ericWeb48"),
            "eric Web Browser",
            os.path.basename(bookmarksFile),
            QCoreApplication.translate(
                "XbelImporter",
                """eric Web Browser stores its bookmarks in the"""
                """ <b>{0}</b> XML file. This file is usually located in""",
            ).format(os.path.basename(bookmarksFile)),
            QCoreApplication.translate(
                "XbelImporter",
                """Please choose the file to begin importing bookmarks.""",
            ),
            os.path.dirname(bookmarksFile),
        )
    elif sourceId == "konqueror":
        if os.path.exists(os.path.expanduser("~/.kde4")):
            standardDir = os.path.expanduser("~/.kde4/share/apps/konqueror")
        elif os.path.exists(os.path.expanduser("~/.kde")):
            standardDir = os.path.expanduser("~/.kde/share/apps/konqueror")
        else:
            standardDir = ""
        return (
            EricPixmapCache.getPixmap("konqueror"),
            "Konqueror",
            "bookmarks.xml",
            QCoreApplication.translate(
                "XbelImporter",
                """Konqueror stores its bookmarks in the"""
                """ <b>bookmarks.xml</b> XML file. This file is usually"""
                """ located in""",
            ),
            QCoreApplication.translate(
                "XbelImporter",
                """Please choose the file to begin importing bookmarks.""",
            ),
            standardDir,
        )
    else:
        return (
            EricPixmapCache.getPixmap("xbel"),
            "XBEL Bookmarks",
            QCoreApplication.translate("XbelImporter", "XBEL Bookmarks")
            + " (*.xbel *.xml)",
            QCoreApplication.translate(
                "XbelImporter",
                """You can import bookmarks from any browser that supports"""
                """ XBEL exporting. This file has usually the extension"""
                """ .xbel or .xml.""",
            ),
            QCoreApplication.translate(
                "XbelImporter",
                """Please choose the file to begin importing bookmarks.""",
            ),
            "",
        )


class XbelImporter(BookmarksImporter):
    """
    Class implementing the XBEL bookmarks importer.
    """

    def __init__(self, sourceId="", parent=None):
        """
        Constructor

        @param sourceId source ID (defaults to "")
        @type str (optional)
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(sourceId, parent)

        self.__fileName = ""

    def setPath(self, path):
        """
        Public method to set the path of the bookmarks file or directory.

        @param path bookmarks file or directory
        @type str
        """
        self.__fileName = path

    def open(self):
        """
        Public method to open the bookmarks file.

        @return flag indicating success
        @rtype bool
        """
        if not os.path.exists(self.__fileName):
            self._error = True
            self._errorString = self.tr("File '{0}' does not exist.").format(
                self.__fileName
            )
            return False
        return True

    def importedBookmarks(self):
        """
        Public method to get the imported bookmarks.

        @return imported bookmarks
        @rtype BookmarkNode
        """
        from ..BookmarkNode import BookmarkNodeType
        from ..XbelReader import XbelReader

        reader = XbelReader()
        importRootNode = reader.read(self.__fileName)

        if reader.error() != QXmlStreamReader.Error.NoError:
            self._error = True
            self._errorString = self.tr(
                """Error when importing bookmarks on line {0},"""
                """ column {1}:\n{2}"""
            ).format(reader.lineNumber(), reader.columnNumber(), reader.errorString())
            return None

        importRootNode.setType(BookmarkNodeType.Folder)
        if self._id == "e5browser":
            importRootNode.title = self.tr("eric Web Browser Import")
        elif self._id == "konqueror":
            importRootNode.title = self.tr("Konqueror Import")
        elif self._id == "xbel":
            importRootNode.title = self.tr("XBEL Import")
        else:
            importRootNode.title = self.tr("Imported {0}").format(
                QDate.currentDate().toString(Qt.DateFormat.ISODate)
            )
        return importRootNode


def createImporter(sourceId="", parent=None):
    """
    Constructor

    @param sourceId source ID (defaults to "")
    @type str (optional)
    @param parent reference to the parent object (defaults to None)
    @type QObject (optional)
    @return reference to the instantiated importer object
    @rtype XbelImporter
    """
    return XbelImporter(sourceId=sourceId, parent=parent)
