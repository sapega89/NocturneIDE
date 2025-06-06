# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to read XBEL bookmark files.
"""

from PyQt6.QtCore import (
    QCoreApplication,
    QDateTime,
    QFile,
    QIODevice,
    Qt,
    QXmlStreamEntityResolver,
    QXmlStreamNamespaceDeclaration,
    QXmlStreamReader,
)

from .BookmarkNode import BookmarkNode, BookmarkNodeType


class XmlEntityResolver(QXmlStreamEntityResolver):
    """
    Class implementing an XML entity resolver for bookmark files.
    """

    def resolveUndeclaredEntity(self, entity):
        """
        Public method to resolve undeclared entities.

        @param entity entity to be resolved
        @type str
        @return resolved entity
        @rtype str
        """
        if entity == "nbsp":
            return " "
        return ""


class XbelReader(QXmlStreamReader):
    """
    Class implementing a reader object for XBEL bookmark files.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.__resolver = XmlEntityResolver()
        self.setEntityResolver(self.__resolver)

    def read(self, fileNameOrDevice):
        """
        Public method to read an XBEL bookmark file.

        @param fileNameOrDevice name of the file to read
        @type str
            or reference to the device to read (QIODevice)
        @return reference to the root node
        @rtype BookmarkNode
        """
        if isinstance(fileNameOrDevice, QIODevice):
            self.setDevice(fileNameOrDevice)
        else:
            f = QFile(fileNameOrDevice)
            if not f.exists():
                return BookmarkNode(BookmarkNodeType.Root)
            f.open(QIODevice.OpenModeFlag.ReadOnly)
            self.setDevice(f)

        root = BookmarkNode(BookmarkNodeType.Root)
        while not self.atEnd():
            self.readNext()
            if self.isStartElement():
                version = self.attributes().value("version")
                if self.name() == "xbel" and (not version or version == "1.0"):
                    self.__readXBEL(root)
                else:
                    self.raiseError(
                        QCoreApplication.translate(
                            "XbelReader", "The file is not an XBEL version 1.0 file."
                        )
                    )

        return root

    def __readXBEL(self, node):
        """
        Private method to read and parse the XBEL file.

        @param node reference to the node to attach to
        @type BookmarkNode
        """
        if not self.isStartElement() and self.name() != "xbel":
            return

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break

            if self.isStartElement():
                if self.name() == "folder":
                    self.__readFolder(node)
                elif self.name() == "bookmark":
                    self.__readBookmarkNode(node)
                elif self.name() == "separator":
                    self.__readSeparator(node)
                else:
                    self.__skipUnknownElement()

    def __readFolder(self, node):
        """
        Private method to read and parse a folder subtree.

        @param node reference to the node to attach to
        @type BookmarkNode
        """
        if not self.isStartElement() and self.name() != "folder":
            return

        folder = BookmarkNode(BookmarkNodeType.Folder, node)
        folder.expanded = self.attributes().value("folded") == "no"
        folder.added = QDateTime.fromString(
            self.attributes().value("added"), Qt.DateFormat.ISODate
        )

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break

            if self.isStartElement():
                if self.name() == "title":
                    self.__readTitle(folder)
                elif self.name() == "desc":
                    self.__readDescription(folder)
                elif self.name() == "folder":
                    self.__readFolder(folder)
                elif self.name() == "bookmark":
                    self.__readBookmarkNode(folder)
                elif self.name() == "separator":
                    self.__readSeparator(folder)
                elif self.name() == "info":
                    self.__readInfo()
                else:
                    self.__skipUnknownElement()

    def __readTitle(self, node):
        """
        Private method to read the title element.

        @param node reference to the bookmark node title belongs to
        @type BookmarkNode
        """
        if not self.isStartElement() and self.name() != "title":
            return

        node.title = self.readElementText()

    def __readDescription(self, node):
        """
        Private method to read the desc element.

        @param node reference to the bookmark node desc belongs to
        @type BookmarkNode
        """
        if not self.isStartElement() and self.name() != "desc":
            return

        node.desc = self.readElementText()

    def __readSeparator(self, node):
        """
        Private method to read a separator element.

        @param node reference to the bookmark node the separator belongs to
        @type BookmarkNode
        """
        sep = BookmarkNode(BookmarkNodeType.Separator, node)
        sep.added = QDateTime.fromString(
            self.attributes().value("added"), Qt.DateFormat.ISODate
        )

        # empty elements have a start and end element
        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break

            if self.isStartElement():
                if self.name() == "info":
                    self.__readInfo()
                else:
                    self.__skipUnknownElement()

    def __readBookmarkNode(self, node):
        """
        Private method to read and parse a bookmark subtree.

        @param node reference to the node to attach to
        @type BookmarkNode
        """
        if not self.isStartElement() and self.name() != "bookmark":
            return

        bookmark = BookmarkNode(BookmarkNodeType.Bookmark, node)
        bookmark.url = self.attributes().value("href")
        bookmark.added = QDateTime.fromString(
            self.attributes().value("added"), Qt.DateFormat.ISODate
        )
        bookmark.modified = QDateTime.fromString(
            self.attributes().value("modified"), Qt.DateFormat.ISODate
        )
        bookmark.visited = QDateTime.fromString(
            self.attributes().value("visited"), Qt.DateFormat.ISODate
        )
        try:
            bookmark.visitCount = int(self.attributes().value("visitCount"))
        except ValueError:
            bookmark.visitCount = 0

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break

            if self.isStartElement():
                if self.name() == "title":
                    self.__readTitle(bookmark)
                elif self.name() == "desc":
                    self.__readDescription(bookmark)
                elif self.name() == "info":
                    self.__readInfo()
                else:
                    self.__skipUnknownElement()

        if not bookmark.title:
            bookmark.title = QCoreApplication.translate("XbelReader", "Unknown title")

    def __readInfo(self):
        """
        Private method to read and parse an info subtree.
        """
        self.addExtraNamespaceDeclaration(
            QXmlStreamNamespaceDeclaration("bookmark", "http://www.python.org")
        )
        self.skipCurrentElement()

    def __skipUnknownElement(self):
        """
        Private method to skip over all unknown elements.
        """
        self.skipCurrentElement()
