# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an importer for HTML bookmark files.
"""

import os

from PyQt6.QtCore import QCoreApplication, QDate, Qt

from eric7.EricGui import EricPixmapCache

from .BookmarksImporter import BookmarksImporter


def getImporterInfo(sourceId):
    """
    Module function to get information for the given HTML source id.

    @param sourceId id of the browser
    @type str
    @return tuple with an icon, readable name, name of the default
        bookmarks file, an info text, a prompt and the default directory
        of the bookmarks file
    @rtype tuple of (QPixmap, str, str, str, str, str)
    @exception ValueError raised to indicate an invalid browser ID
    """
    if sourceId != "html":
        raise ValueError("Unsupported browser ID given ({0}).".format(sourceId))

    return (
        EricPixmapCache.getPixmap("html"),
        "HTML Netscape Bookmarks",
        QCoreApplication.translate("HtmlImporter", "HTML Netscape Bookmarks")
        + " (*.htm *.html)",
        QCoreApplication.translate(
            "HtmlImporter",
            """You can import bookmarks from any browser that supports"""
            """ HTML exporting. This file has usually the extension"""
            """ .htm or .html.""",
        ),
        QCoreApplication.translate(
            "HtmlImporter", """Please choose the file to begin importing bookmarks."""
        ),
        "",
    )


class HtmlImporter(BookmarksImporter):
    """
    Class implementing the HTML bookmarks importer.
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
        self.__inFile = None

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
        from ..NsHtmlReader import NsHtmlReader

        reader = NsHtmlReader()
        importRootNode = reader.read(self.__fileName)

        importRootNode.setType(BookmarkNodeType.Folder)
        if self._id == "html":
            importRootNode.title = self.tr("HTML Import")
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
    @rtype HtmlImporter
    """
    return HtmlImporter(sourceId=sourceId, parent=parent)
