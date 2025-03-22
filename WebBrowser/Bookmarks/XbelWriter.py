# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to write XBEL bookmark files.
"""

from PyQt6.QtCore import QFile, QIODevice, Qt, QXmlStreamWriter

from .BookmarkNode import BookmarkNodeType


class XbelWriter(QXmlStreamWriter):
    """
    Class implementing a writer object to generate XBEL bookmark files.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.setAutoFormatting(True)

    def write(self, fileNameOrDevice, root):
        """
        Public method to write an XBEL bookmark file.

        @param fileNameOrDevice name of the file to write
        @type str
            or device to write to (QIODevice)
        @param root root node of the bookmark tree
        @type BookmarkNode
        @return flag indicating success
        @rtype bool
        """
        if isinstance(fileNameOrDevice, QIODevice):
            f = fileNameOrDevice
        else:
            f = QFile(fileNameOrDevice)
            if root is None or not f.open(QIODevice.OpenModeFlag.WriteOnly):
                return False

        self.setDevice(f)
        return self.__write(root)

    def __write(self, root):
        """
        Private method to write an XBEL bookmark file.

        @param root root node of the bookmark tree
        @type BookmarkNode
        @return flag indicating success
        @rtype bool
        """
        self.writeStartDocument()
        self.writeDTD("<!DOCTYPE xbel>")
        self.writeStartElement("xbel")
        self.writeAttribute("version", "1.0")
        if root.type() == BookmarkNodeType.Root:
            for child in root.children():
                self.__writeItem(child)
        else:
            self.__writeItem(root)

        self.writeEndDocument()
        return True

    def __writeItem(self, node):
        """
        Private method to write an entry for a node.

        @param node reference to the node to be written
        @type BookmarkNode
        """
        if node.type() == BookmarkNodeType.Folder:
            self.writeStartElement("folder")
            if node.added.isValid():
                self.writeAttribute("added", node.added.toString(Qt.DateFormat.ISODate))
            self.writeAttribute("folded", node.expanded and "no" or "yes")
            self.writeTextElement("title", node.title)
            for child in node.children():
                self.__writeItem(child)
            self.writeEndElement()
        elif node.type() == BookmarkNodeType.Bookmark:
            self.writeStartElement("bookmark")
            if node.url:
                self.writeAttribute("href", node.url)
            if node.added.isValid():
                self.writeAttribute("added", node.added.toString(Qt.DateFormat.ISODate))
            if node.modified.isValid():
                self.writeAttribute(
                    "modified", node.modified.toString(Qt.DateFormat.ISODate)
                )
            if node.visited.isValid():
                self.writeAttribute(
                    "visited", node.visited.toString(Qt.DateFormat.ISODate)
                )
            self.writeAttribute("visitCount", str(node.visitCount))
            self.writeTextElement("title", node.title)
            if node.desc:
                self.writeTextElement("desc", node.desc)
            self.writeEndElement()
        elif node.type() == BookmarkNodeType.Separator:
            self.writeEmptyElement("separator")
            if node.added.isValid():
                self.writeAttribute("added", node.added.toString(Qt.DateFormat.ISODate))
