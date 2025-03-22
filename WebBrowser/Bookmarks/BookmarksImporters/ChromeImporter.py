# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an importer for Chrome bookmarks.
"""

import json
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
    if sourceId not in ("chrome", "chromium", "edge", "falkon", "opera", "vivaldi"):
        raise ValueError("Unsupported browser ID given ({0}).".format(sourceId))

    if sourceId == "chrome":
        if OSUtilities.isWindowsPlatform():
            standardDir = os.path.expandvars(
                "%USERPROFILE%\\AppData\\Local\\Google\\Chrome\\User Data\\Default"
            )
        elif OSUtilities.isMacPlatform():
            standardDir = os.path.expanduser(
                "~/Library/Application Support/Google/Chrome/Default"
            )
        else:
            standardDir = os.path.expanduser("~/.config/google-chrome/Default")
        return (
            EricPixmapCache.getPixmap("chrome"),
            "Google Chrome",
            "Bookmarks",
            QCoreApplication.translate(
                "ChromeImporter",
                """Google Chrome stores its bookmarks in the"""
                """ <b>Bookmarks</b> text file. This file is usually"""
                """ located in""",
            ),
            QCoreApplication.translate(
                "ChromeImporter",
                """Please choose the file to begin importing bookmarks.""",
            ),
            standardDir,
        )

    elif sourceId == "chromium":
        if OSUtilities.isWindowsPlatform():
            standardDir = os.path.expandvars(
                "%USERPROFILE%\\AppData\\Local\\Google\\Chrome\\User Data\\Default"
            )
        else:
            standardDir = os.path.expanduser("~/.config/chromium/Default")
        return (
            EricPixmapCache.getPixmap("chromium"),
            "Chromium",
            "Bookmarks",
            QCoreApplication.translate(
                "ChromeImporter",
                """Chromium stores its bookmarks in the <b>Bookmarks</b>"""
                """ text file. This file is usually located in""",
            ),
            QCoreApplication.translate(
                "ChromeImporter",
                """Please choose the file to begin importing bookmarks.""",
            ),
            standardDir,
        )

    elif sourceId == "edge":
        if OSUtilities.isWindowsPlatform():
            standardDir = os.path.expandvars(
                "%USERPROFILE%\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default"
            )
        else:
            standardDir = os.path.expanduser("~/.config/microsoft-edge/Default")
        return (
            EricPixmapCache.getPixmap("edge"),
            "Microsoft Edge",
            "Bookmarks",
            QCoreApplication.translate(
                "ChromeImporter",
                """Microsoft Edge stores its bookmarks in the"""
                """ <b>Bookmarks</b> text file. This file is usually"""
                """ located in""",
            ),
            QCoreApplication.translate(
                "ChromeImporter",
                """Please choose the file to begin importing bookmarks.""",
            ),
            standardDir,
        )

    elif sourceId == "falkon":
        if OSUtilities.isWindowsPlatform():
            standardDir = os.path.expandvars(
                "%USERPROFILE%\\AppData\\Local\\falkon\\profiles\\default"
            )
        else:
            standardDir = os.path.expanduser("~/.config/falkon/profiles/default")
        return (
            EricPixmapCache.getPixmap("falkon"),
            "Falkon",
            "bookmarks.json",
            QCoreApplication.translate(
                "ChromeImporter",
                """Falkon stores its bookmarks in the"""
                """ <b>bookmarks.json</b> text file. This file is usually"""
                """ located in""",
            ),
            QCoreApplication.translate(
                "ChromeImporter",
                """Please choose the file to begin importing bookmarks.""",
            ),
            standardDir,
        )

    elif sourceId == "opera":
        if OSUtilities.isWindowsPlatform():
            standardDir = os.path.expandvars(
                "%USERPROFILE%\\AppData\\Roaming\\Opera Software\\Opera Stable"
            )
        else:
            standardDir = os.path.expanduser("~/.config/opera")
        return (
            EricPixmapCache.getPixmap("opera"),
            "Opera",
            "Bookmarks",
            QCoreApplication.translate(
                "ChromeImporter",
                """Opera stores its bookmarks in the"""
                """ <b>Bookmarks</b> text file. This file is usually"""
                """ located in""",
            ),
            QCoreApplication.translate(
                "ChromeImporter",
                """Please choose the file to begin importing bookmarks.""",
            ),
            standardDir,
        )

    elif sourceId == "vivaldi":
        if OSUtilities.isWindowsPlatform():
            standardDir = os.path.expandvars(
                "%USERPROFILE%\\AppData\\Local\\Vivaldi\\User Data\\Default"
            )
        else:
            standardDir = os.path.expanduser("~/.config/vivaldi/Default")
        return (
            EricPixmapCache.getPixmap("vivaldi"),
            "Vivaldi",
            "Bookmarks",
            QCoreApplication.translate(
                "ChromeImporter",
                """Vivaldi stores its bookmarks in the"""
                """ <b>Bookmarks</b> text file. This file is usually"""
                """ located in""",
            ),
            QCoreApplication.translate(
                "ChromeImporter",
                """Please choose the file to begin importing bookmarks.""",
            ),
            standardDir,
        )

    # entry if an unknown source is given
    standardDir = (
        os.path.expandvars("%USERPROFILE%\\AppData")
        if OSUtilities.isWindowsPlatform()
        else os.path.expanduser("~/.config")
    )
    return (
        EricPixmapCache.getPixmap("chrome_unknown"),
        "Unknown Chrome",
        "Bookmarks",
        QCoreApplication.translate(
            "ChromeImporter",
            """This browser stores its bookmarks in the"""
            """ <b>Bookmarks</b> text file. This file is usually"""
            """ located somewhere below""",
        ),
        QCoreApplication.translate(
            "ChromeImporter",
            """Please choose the file to begin importing bookmarks.""",
        ),
        standardDir,
    )


class ChromeImporter(BookmarksImporter):
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
                contents = json.load(f)
        except OSError as err:
            self._error = True
            self._errorString = self.tr(
                "File '{0}' cannot be read.\nReason: {1}"
            ).format(self.__fileName, str(err))
            return None

        importRootNode = BookmarkNode(BookmarkNodeType.Folder)
        if contents["version"] == 1:
            self.__processRoots(contents["roots"], importRootNode)

        if self._id == "chrome":
            importRootNode.title = self.tr("Google Chrome Import")
        elif self._id == "chromium":
            importRootNode.title = self.tr("Chromium Import")
        else:
            importRootNode.title = self.tr("Imported {0}").format(
                QDate.currentDate().toString(Qt.DateFormat.ISODate)
            )
        return importRootNode

    def __processRoots(self, data, rootNode):
        """
        Private method to process the bookmark roots.

        @param data dictionary with the bookmarks data
        @type dict
        @param rootNode node to add the bookmarks to
        @type BookmarkNode
        """
        for key, node in data.items():
            if "type" in node:
                if node["type"] == "folder":
                    self.__generateFolderNode(node, rootNode)
                elif node["type"] == "url":
                    self.__generateUrlNode(node, rootNode)
            else:
                if key == "custom_root":
                    # Opera bookmarks contain this
                    data = {
                        "name": "Custom bookmarks",
                        "children": list(node.values()),
                    }
                    self.__generateFolderNode(data, rootNode)

    def __generateFolderNode(self, data, rootNode):
        """
        Private method to process a bookmarks folder.

        @param data dictionary with the bookmarks data
        @type dict
        @param rootNode node to add the bookmarks to
        @type BookmarkNode
        """
        from ..BookmarkNode import BookmarkNode, BookmarkNodeType

        folder = BookmarkNode(BookmarkNodeType.Folder, rootNode)
        folder.title = data["name"].replace("&", "&&")
        for node in data["children"]:
            if node["type"] == "folder":
                self.__generateFolderNode(node, folder)
            elif node["type"] == "url":
                self.__generateUrlNode(node, folder)

    def __generateUrlNode(self, data, rootNode):
        """
        Private method to process a bookmarks node.

        @param data dictionary with the bookmarks data
        @type dict
        @param rootNode node to add the bookmarks to
        @type BookmarkNode
        """
        from ..BookmarkNode import BookmarkNode, BookmarkNodeType

        bookmark = BookmarkNode(BookmarkNodeType.Bookmark, rootNode)
        bookmark.url = data["url"]
        bookmark.title = data["name"].replace("&", "&&")


def createImporter(sourceId="", parent=None):
    """
    Constructor

    @param sourceId source ID (defaults to "")
    @type str (optional)
    @param parent reference to the parent object (defaults to None)
    @type QObject (optional)
    @return reference to the instantiated importer object
    @rtype ChromeImporter
    """
    return ChromeImporter(sourceId=sourceId, parent=parent)
