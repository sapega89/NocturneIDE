# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to write Netscape HTML bookmark files.
"""

from PyQt6.QtCore import QFile, QIODevice, QObject

from eric7 import EricUtilities, Utilities

from .BookmarkNode import BookmarkNodeType


class NsHtmlWriter(QObject):
    """
    Class implementing a writer object to generate Netscape HTML bookmark
    files.
    """

    indentSize = 4

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

    def write(self, fileNameOrDevice, root):
        """
        Public method to write an Netscape HTML bookmark file.

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

        self.__dev = f
        return self.__write(root)

    def __write(self, root):
        """
        Private method to write an Netscape HTML bookmark file.

        @param root root node of the bookmark tree
        @type BookmarkNode
        @return flag indicating success
        @rtype bool
        """
        self.__dev.write(
            "<!DOCTYPE NETSCAPE-Bookmark-file-1>\n"
            "<!-- This is an automatically generated file.\n"
            "     It will be read and overwritten.\n"
            "     DO NOT EDIT! -->\n"
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html;'
            ' charset=UTF-8">\n'
            "<TITLE>Bookmarks</TITLE>\n"
            "<H1>Bookmarks</H1>\n"
            "\n"
            "<DL><p>\n"
        )
        if root.type() == BookmarkNodeType.Root:
            for child in root.children():
                self.__writeItem(child, self.indentSize)
        else:
            self.__writeItem(root, self.indentSize)
        self.__dev.write("</DL><p>\n")
        return True

    def __writeItem(self, node, indent):
        """
        Private method to write an entry for a node.

        @param node reference to the node to be written
        @type BookmarkNode
        @param indent size of the indentation
        @type int
        """
        if node.type() == BookmarkNodeType.Folder:
            self.__writeFolder(node, indent)
        elif node.type() == BookmarkNodeType.Bookmark:
            self.__writeBookmark(node, indent)
        elif node.type() == BookmarkNodeType.Separator:
            self.__writeSeparator(indent)

    def __writeSeparator(self, indent):
        """
        Private method to write a separator.

        @param indent size of the indentation
        @type int
        """
        self.__dev.write(" " * indent)
        self.__dev.write("<HR>\n")

    def __writeBookmark(self, node, indent):
        """
        Private method to write a bookmark node.

        @param node reference to the node to be written
        @type BookmarkNode
        @param indent size of the indentation
        @type int
        """
        added = (
            ' ADD_DATE="{0}"'.format(node.added.toTime_t())
            if node.added.isValid()
            else ""
        )
        modified = (
            ' LAST_MODIFIED="{0}"'.format(node.modified.toTime_t())
            if node.modified.isValid()
            else ""
        )
        visited = (
            ' LAST_VISIT="{0}"'.format(node.visited.toTime_t())
            if node.visited.isValid()
            else ""
        )

        self.__dev.write(" " * indent)
        self.__dev.write(
            '<DT><A HREF="{0}"{1}{2}{3}>{4}</A>\n'.format(
                node.url,
                added,
                modified,
                visited,
                EricUtilities.html_uencode(node.title),
            )
        )

        if node.desc:
            self.__dev.write(" " * indent)
            self.__dev.write(
                "<DD>{0}\n".format(
                    Utilities.html_uencode("".join(node.desc.splitlines()))
                )
            )

    def __writeFolder(self, node, indent):
        """
        Private method to write a bookmark node.

        @param node reference to the node to be written
        @type BookmarkNode
        @param indent size of the indentation
        @type int
        """
        folded = "" if node.expanded else " FOLDED"

        added = (
            ' ADD_DATE="{0}"'.format(node.added.toTime_t())
            if node.added.isValid()
            else ""
        )

        self.__dev.write(" " * indent)
        self.__dev.write(
            "<DT><H3{0}{1}>{2}</H3>\n".format(
                folded, added, EricUtilities.html_uencode(node.title)
            )
        )

        if node.desc:
            self.__dev.write(" " * indent)
            self.__dev.write("<DD>{0}\n".format("".join(node.desc.splitlines())))

        self.__dev.write(" " * indent)
        self.__dev.write("<DL><p>\n")

        for child in node.children():
            self.__writeItem(child, indent + self.indentSize)

        self.__dev.write(" " * indent)
        self.__dev.write("</DL><p>\n")
