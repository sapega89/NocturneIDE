# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an importer for Opera bookmarks.
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
    if sourceId != "opera_legacy":
        raise ValueError("Unsupported browser ID given ({0}).".format(sourceId))

    if OSUtilities.isWindowsPlatform():
        standardDir = os.path.expandvars("%APPDATA%\\Opera\\Opera")
    elif OSUtilities.isMacPlatform():
        standardDir = os.path.expanduser("~/Library/Opera")
    else:
        standardDir = os.path.expanduser("~/.opera")
    return (
        EricPixmapCache.getPixmap("opera_legacy"),
        "Opera (Legacy)",
        "bookmarks.adr",
        QCoreApplication.translate(
            "OperaImporter",
            """Opera (Legacy) stores its bookmarks in the <b>bookmarks.adr</b> """
            """text file. This file is usually located in""",
        ),
        QCoreApplication.translate(
            "OperaImporter", """Please choose the file to begin importing bookmarks."""
        ),
        standardDir,
    )


class OperaImporter(BookmarksImporter):
    """
    Class implementing the Opera bookmarks importer.
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
            with open(self.__fileName, "r", encoding="utf-8") as f:
                contents = f.read()
        except OSError as err:
            self._error = True
            self._errorString = self.tr(
                "File '{0}' cannot be read.\nReason: {1}"
            ).format(self.__fileName, str(err))
            return None

        folderStack = []

        importRootNode = BookmarkNode(BookmarkNodeType.Folder)
        folderStack.append(importRootNode)

        for line in contents.splitlines():
            line = line.strip()
            if line == "#FOLDER":
                node = BookmarkNode(BookmarkNodeType.Folder, folderStack[-1])
                folderStack.append(node)
            elif line == "#URL":
                node = BookmarkNode(BookmarkNodeType.Bookmark, folderStack[-1])
            elif line == "-":
                folderStack.pop()
            elif line.startswith("NAME="):
                node.title = line.replace("NAME=", "").replace("&", "&&")
            elif line.startswith("URL="):
                node.url = line.replace("URL=", "")

        if self._id == "opera":
            importRootNode.title = self.tr("Opera Import")
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
    @rtype OperaImporter
    """
    return OperaImporter(sourceId=sourceId, parent=parent)
