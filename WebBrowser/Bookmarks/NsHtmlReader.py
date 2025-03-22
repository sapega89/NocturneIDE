# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to read Netscape HTML bookmark files.
"""

import re

from PyQt6.QtCore import QDateTime, QFile, QIODevice, QObject

from eric7 import EricUtilities

from .BookmarkNode import BookmarkNode, BookmarkNodeType


class NsHtmlReader(QObject):
    """
    Class implementing a reader object for Netscape HTML bookmark files.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.__folderRx = re.compile("<DT><H3(.*?)>(.*?)</H3>", re.IGNORECASE)
        self.__endFolderRx = re.compile("</DL>", re.IGNORECASE)
        self.__bookmarkRx = re.compile("<DT><A(.*?)>(.*?)</A>", re.IGNORECASE)
        self.__descRx = re.compile("<DD>(.*)", re.IGNORECASE)
        self.__separatorRx = re.compile("<HR>", re.IGNORECASE)
        self.__urlRx = re.compile('HREF="(.*?)"', re.IGNORECASE)
        self.__addedRx = re.compile(r'ADD_DATE="(\d*?)"', re.IGNORECASE)
        self.__modifiedRx = re.compile(r'LAST_MODIFIED="(\d*?)"', re.IGNORECASE)
        self.__visitedRx = re.compile(r'LAST_VISIT="(\d*?)"', re.IGNORECASE)
        self.__foldedRx = re.compile("FOLDED", re.IGNORECASE)

    def read(self, fileNameOrDevice):
        """
        Public method to read a Netscape HTML bookmark file.

        @param fileNameOrDevice name of the file to read
        @type str
            or reference to the device to read (QIODevice)
        @return reference to the root node
        @rtype BookmarkNode
        """
        if isinstance(fileNameOrDevice, QIODevice):
            dev = fileNameOrDevice
        else:
            f = QFile(fileNameOrDevice)
            if not f.exists():
                return BookmarkNode(BookmarkNodeType.Root)
            f.open(QIODevice.OpenModeFlag.ReadOnly)
            dev = f

        folders = []
        lastNode = None

        root = BookmarkNode(BookmarkNodeType.Root)
        folders.append(root)

        while not dev.atEnd():
            line = str(dev.readLine(), encoding="utf-8").rstrip()
            match = (
                self.__folderRx.search(line)
                or self.__endFolderRx.search(line)
                or self.__bookmarkRx.search(line)
                or self.__descRx.search(line)
                or self.__separatorRx.search(line)
            )
            if match is None:
                continue

            if match.re is self.__folderRx:
                # folder definition
                arguments = match.group(1)
                name = match.group(2)
                node = BookmarkNode(BookmarkNodeType.Folder, folders[-1])
                node.title = EricUtilities.html_udecode(name)
                node.expanded = self.__foldedRx.search(arguments) is None
                addedMatch = self.__addedRx.search(arguments)
                if addedMatch is not None:
                    node.added = QDateTime.fromSecsSinceEpoch(int(addedMatch.group(1)))
                folders.append(node)
                lastNode = node

            elif match.re is self.__endFolderRx:
                # end of folder definition
                folders.pop()

            elif match.re is self.__bookmarkRx:
                # bookmark definition
                arguments = match.group(1)
                name = match.group(2)
                node = BookmarkNode(BookmarkNodeType.Bookmark, folders[-1])
                node.title = EricUtilities.html_udecode(name)
                match1 = self.__urlRx.search(arguments)
                if match1 is not None:
                    node.url = match1.group(1)
                match1 = self.__addedRx.search(arguments)
                if match1 is not None:
                    node.added = QDateTime.fromSecsSinceEpoch(int(match1.group(1)))
                match1 = self.__modifiedRx.search(arguments)
                if match1 is not None:
                    node.modified = QDateTime.fromSecsSinceEpoch(int(match1.group(1)))
                match1 = self.__visitedRx.search(arguments)
                if match1 is not None:
                    node.visited = QDateTime.fromSecsSinceEpoch(int(match1.group(1)))
                lastNode = node

            elif match.re is self.__descRx:
                # description
                if lastNode:
                    lastNode.desc = EricUtilities.html_udecode(match.group(1))

            elif match.re is self.__separatorRx:
                # separator definition
                BookmarkNode(BookmarkNodeType.Separator, folders[-1])

        return root
