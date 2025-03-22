# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the bookmark node.
"""

import enum

from PyQt6.QtCore import QDateTime


class BookmarkNodeType(enum.Enum):
    """
    Class defining the bookmark node types.
    """

    Root = 0
    Folder = 1
    Bookmark = 2
    Separator = 3


class BookmarkTimestampType(enum.Enum):
    """
    Class defining the bookmark timestamp types.
    """

    Added = 0
    Modified = 1
    Visited = 2


class BookmarkNode:
    """
    Class implementing the bookmark node type.
    """

    def __init__(self, type_=BookmarkNodeType.Root, parent=None):
        """
        Constructor

        @param type_ type of the bookmark node
        @type BookmarkNode.Type
        @param parent reference to the parent node
        @type BookmarkNode
        """
        self.url = ""
        self.title = ""
        self.desc = ""
        self.expanded = False
        self.added = QDateTime()
        self.modified = QDateTime()
        self.visited = QDateTime()
        self.visitCount = 0

        self._children = []
        self._parent = parent
        self._type = type_

        if parent is not None:
            parent.add(self)

    def type(self):
        """
        Public method to get the bookmark's type.

        @return bookmark type
        @rtype BookmarkNode.Type
        """
        return self._type

    def setType(self, type_):
        """
        Public method to set the bookmark's type.

        @param type_ type of the bookmark node
        @type BookmarkNode.Type
        """
        self._type = type_

    def children(self):
        """
        Public method to get the list of child nodes.

        @return list of all child nodes
        @rtype list of BookmarkNode
        """
        return self._children[:]

    def parent(self):
        """
        Public method to get a reference to the parent node.

        @return reference to the parent node
        @rtype BookmarkNode
        """
        return self._parent

    def add(self, child, offset=-1):
        """
        Public method to add/insert a child node.

        @param child reference to the node to add
        @type BookmarkNode
        @param offset position where to insert child (-1 = append)
        @type int
        """
        if child._type == BookmarkNodeType.Root:
            return

        if child._parent is not None:
            child._parent.remove(child)

        child._parent = self
        if offset == -1:
            self._children.append(child)
        else:
            self._children.insert(offset, child)

    def remove(self, child):
        """
        Public method to remove a child node.

        @param child reference to the child node
        @type BookmarkNode
        """
        child._parent = None
        if child in self._children:
            self._children.remove(child)
