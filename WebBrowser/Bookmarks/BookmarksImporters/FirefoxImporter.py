# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an importer for Firefox bookmarks.
"""

import os
import sqlite3

from PyQt6.QtCore import QCoreApplication, QDate, Qt, QUrl

from eric7.EricGui import EricPixmapCache
from eric7.SystemUtilities import OSUtilities

from .BookmarksImporter import BookmarksImporter


def getImporterInfo(sourceId):
    """
    Module function to get information for the given source id.

    @param sourceId id of the browser
    @type str
    @return tuple with an icon, readable name, name of the default
        bookmarks file, an info text, a prompt and the default directory
        of the bookmarks file
    @rtype tuple of (QPixmap, str, str, str, str, str)
    @exception ValueError raised to indicate an invalid browser ID
    """
    if sourceId != "firefox":
        raise ValueError("Unsupported browser ID given ({0}).".format(sourceId))

    if OSUtilities.isWindowsPlatform():
        standardDir = os.path.expandvars("%APPDATA%\\Mozilla\\Firefox\\Profiles")
    elif OSUtilities.isMacPlatform():
        standardDir = os.path.expanduser(
            "~/Library/Application Support/Firefox/Profiles"
        )
    else:
        standardDir = os.path.expanduser("~/.mozilla/firefox")
    return (
        EricPixmapCache.getPixmap("chrome"),
        "Mozilla Firefox",
        "places.sqlite",
        QCoreApplication.translate(
            "FirefoxImporter",
            """Mozilla Firefox stores its bookmarks in the"""
            """ <b>places.sqlite</b> SQLite database. This file is"""
            """ usually located in""",
        ),
        QCoreApplication.translate(
            "FirefoxImporter",
            """Please choose the file to begin importing bookmarks.""",
        ),
        standardDir,
    )


class FirefoxImporter(BookmarksImporter):
    """
    Class implementing the Chrome bookmarks importer.
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
        self.__db = None

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

        try:
            self.__db = sqlite3.connect(self.__fileName)
        except sqlite3.DatabaseError as err:
            self._error = True
            self._errorString = self.tr("Unable to open database.\nReason: {0}").format(
                str(err)
            )
            return False

        return True

    def importedBookmarks(self):
        """
        Public method to get the imported bookmarks.

        @return imported bookmarks
        @rtype BookmarkNode
        """
        from ..BookmarkNode import BookmarkNode, BookmarkNodeType

        importRootNode = BookmarkNode(BookmarkNodeType.Root)

        # step 1: build the hierarchy of bookmark folders
        folders = {}

        try:
            cursor = self.__db.cursor()
            cursor.execute(
                "SELECT id, parent, title FROM moz_bookmarks "
                "WHERE type = 2 and title !=''"
            )
            for row in cursor:
                id_ = row[0]
                parent = row[1]
                title = row[2]
                folder = (
                    BookmarkNode(BookmarkNodeType.Folder, folders[parent])
                    if parent in folders
                    else BookmarkNode(BookmarkNodeType.Folder, importRootNode)
                )
                folder.title = title.replace("&", "&&")
                folders[id_] = folder
        except sqlite3.DatabaseError as err:
            self._error = True
            self._errorString = self.tr("Unable to open database.\nReason: {0}").format(
                str(err)
            )
            return None

        try:
            cursor = self.__db.cursor()
            cursor.execute(
                "SELECT parent, title, fk, position FROM moz_bookmarks"
                " WHERE type = 1 and title != '' ORDER BY position"
            )
            for row in cursor:
                parent = row[0]
                title = row[1]
                placesId = row[2]

                cursor2 = self.__db.cursor()
                cursor2.execute(
                    "SELECT url FROM moz_places WHERE id = {0}".format(  # secok
                        placesId
                    )
                )
                row2 = cursor2.fetchone()
                if row2:
                    url = QUrl(row2[0])
                    if not title or url.isEmpty() or url.scheme() in ["place", "about"]:
                        continue

                    if parent in folders:
                        bookmark = BookmarkNode(
                            BookmarkNodeType.Bookmark, folders[parent]
                        )
                    else:
                        bookmark = BookmarkNode(
                            BookmarkNodeType.Bookmark, importRootNode
                        )
                    bookmark.url = url.toString()
                    bookmark.title = title.replace("&", "&&")
        except sqlite3.DatabaseError as err:
            self._error = True
            self._errorString = self.tr("Unable to open database.\nReason: {0}").format(
                str(err)
            )
            return None

        importRootNode.setType(BookmarkNodeType.Folder)
        if self._id == "firefox":
            importRootNode.title = self.tr("Mozilla Firefox Import")
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
    @rtype FirefoxImporter
    """
    return FirefoxImporter(sourceId=sourceId, parent=parent)
