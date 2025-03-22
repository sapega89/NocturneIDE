# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an importer for Apple Safari bookmarks.
"""

import os
import plistlib

from PyQt6.QtCore import QCoreApplication, QDate, Qt

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
    if sourceId != "safari":
        raise ValueError("Unsupported browser ID given ({0}).".format(sourceId))

    if OSUtilities.isWindowsPlatform():
        standardDir = os.path.expandvars("%APPDATA%\\Apple Computer\\Safari")
    elif OSUtilities.isMacPlatform():
        standardDir = os.path.expanduser("~/Library/Safari")
    else:
        standardDir = ""
    return (
        EricPixmapCache.getPixmap("safari"),
        "Apple Safari",
        "Bookmarks.plist",
        QCoreApplication.translate(
            "SafariImporter",
            """Apple Safari stores its bookmarks in the"""
            """ <b>Bookmarks.plist</b> file. This file is usually"""
            """ located in""",
        ),
        QCoreApplication.translate(
            "SafariImporter", """Please choose the file to begin importing bookmarks."""
        ),
        standardDir,
    )


class SafariImporter(BookmarksImporter):
    """
    Class implementing the Apple Safari bookmarks importer.
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
        from ..BookmarkNode import BookmarkNode, BookmarkNodeType

        try:
            with open(self.__fileName, "rb") as f:
                bookmarksDict = plistlib.load(f)
        except (OSError, plistlib.InvalidFileException) as err:
            self._error = True
            self._errorString = self.tr(
                "Bookmarks file cannot be read.\nReason: {0}".format(str(err))
            )
            return None

        importRootNode = BookmarkNode(BookmarkNodeType.Folder)
        if (
            bookmarksDict["WebBookmarkFileVersion"] == 1
            and bookmarksDict["WebBookmarkType"] == "WebBookmarkTypeList"
        ):
            self.__processChildren(bookmarksDict["Children"], importRootNode)

        if self._id == "safari":
            importRootNode.title = self.tr("Apple Safari Import")
        else:
            importRootNode.title = self.tr("Imported {0}").format(
                QDate.currentDate().toString(Qt.DateFormat.ISODate)
            )
        return importRootNode

    def __processChildren(self, children, rootNode):
        """
        Private method to process the list of children.

        @param children list of child nodes to be processed
        @type list of dict
        @param rootNode node to add the bookmarks to
        @type BookmarkNode
        """
        from ..BookmarkNode import BookmarkNode, BookmarkNodeType

        for child in children:
            if child["WebBookmarkType"] == "WebBookmarkTypeList":
                folder = BookmarkNode(BookmarkNodeType.Folder, rootNode)
                folder.title = child["Title"].replace("&", "&&")
                if "Children" in child:
                    self.__processChildren(child["Children"], folder)
            elif child["WebBookmarkType"] == "WebBookmarkTypeLeaf":
                url = child["URLString"]
                if url.startswith(("place:", "about:")):
                    continue

                bookmark = BookmarkNode(BookmarkNodeType.Bookmark, rootNode)
                bookmark.url = url
                bookmark.title = child["URIDictionary"]["title"].replace("&", "&&")


def createImporter(sourceId="", parent=None):
    """
    Constructor

    @param sourceId source ID (defaults to "")
    @type str (optional)
    @param parent reference to the parent object (defaults to None)
    @type QObject (optional)
    @return reference to the instantiated importer object
    @rtype SafariImporter
    """
    return SafariImporter(sourceId=sourceId, parent=parent)
