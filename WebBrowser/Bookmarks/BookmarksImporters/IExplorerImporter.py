# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an importer for Internet Explorer bookmarks.
"""

import os

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
    if sourceId != "ie":
        raise ValueError("Unsupported browser ID given ({0}).".format(sourceId))

    standardDir = (
        os.path.expandvars("%USERPROFILE%\\Favorites")
        if OSUtilities.isWindowsPlatform()
        else ""
    )
    return (
        EricPixmapCache.getPixmap("internet_explorer"),
        "Internet Explorer",
        "",
        QCoreApplication.translate(
            "IExplorerImporter",
            """Internet Explorer stores its bookmarks in the"""
            """ <b>Favorites</b> folder This folder is usually"""
            """ located in""",
        ),
        QCoreApplication.translate(
            "IExplorerImporter",
            """Please choose the folder to begin importing bookmarks.""",
        ),
        standardDir,
    )


class IExplorerImporter(BookmarksImporter):
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
            self._errorString = self.tr("Folder '{0}' does not exist.").format(
                self.__fileName
            )
            return False
        if not os.path.isdir(self.__fileName):
            self._error = True
            self._errorString = self.tr("'{0}' is not a folder.").format(
                self.__fileName
            )
        return True

    def importedBookmarks(self):
        """
        Public method to get the imported bookmarks.

        @return imported bookmarks
        @rtype BookmarkNode
        """
        from ..BookmarkNode import BookmarkNode, BookmarkNodeType

        folders = {}

        importRootNode = BookmarkNode(BookmarkNodeType.Folder)
        folders[self.__fileName] = importRootNode

        for directory, subdirs, files in os.walk(self.__fileName):
            for subdir in subdirs:
                path = os.path.join(directory, subdir)
                folder = (
                    BookmarkNode(BookmarkNodeType.Folder, folders[directory])
                    if directory in folders
                    else BookmarkNode(BookmarkNodeType.Folder, importRootNode)
                )
                folder.title = subdir.replace("&", "&&")
                folders[path] = folder

            for file in files:
                name, ext = os.path.splitext(file)
                if ext.lower() == ".url":
                    path = os.path.join(directory, file)
                    try:
                        with open(path, "r") as f:
                            contents = f.read()
                    except OSError:
                        continue
                    url = ""
                    for line in contents.splitlines():
                        if line.startswith("URL="):
                            url = line.replace("URL=", "")
                            break
                    if url:
                        if directory in folders:
                            bookmark = BookmarkNode(
                                BookmarkNodeType.Bookmark, folders[directory]
                            )
                        else:
                            bookmark = BookmarkNode(
                                BookmarkNodeType.Bookmark, importRootNode
                            )
                        bookmark.url = url
                        bookmark.title = name.replace("&", "&&")

        if self._id == "ie":
            importRootNode.title = self.tr("Internet Explorer Import")
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
    @rtype IExplorerImporter
    """
    return IExplorerImporter(sourceId=sourceId, parent=parent)
