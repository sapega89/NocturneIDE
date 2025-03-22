# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the bookmark model class.
"""

import contextlib

from PyQt6.QtCore import (
    QAbstractItemModel,
    QBuffer,
    QByteArray,
    QDataStream,
    QIODevice,
    QMimeData,
    QModelIndex,
    Qt,
    QUrl,
)

from eric7.EricGui import EricPixmapCache
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow


class BookmarksModel(QAbstractItemModel):
    """
    Class implementing the bookmark model.
    """

    TypeRole = Qt.ItemDataRole.UserRole + 1
    UrlRole = Qt.ItemDataRole.UserRole + 2
    UrlStringRole = Qt.ItemDataRole.UserRole + 3
    VisitCountRole = Qt.ItemDataRole.UserRole + 4
    SeparatorRole = Qt.ItemDataRole.UserRole + 5

    MIMETYPE = "application/bookmarks.xbel"

    def __init__(self, manager, parent=None):
        """
        Constructor

        @param manager reference to the bookmarks manager object
        @type BookmarksManager
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__endMacro = False
        self.__bookmarksManager = manager

        manager.entryAdded.connect(self.entryAdded)
        manager.entryRemoved.connect(self.entryRemoved)
        manager.entryChanged.connect(self.entryChanged)

        self.__headers = [
            self.tr("Title"),
            self.tr("Address"),
        ]

    def bookmarksManager(self):
        """
        Public method to get a reference to the bookmarks manager.

        @return reference to the bookmarks manager object
        @rtype BookmarksManager
        """
        return self.__bookmarksManager

    def nodeIndex(self, node):
        """
        Public method to get a model index.

        @param node reference to the node to get the index for
        @type BookmarkNode
        @return model index
        @rtype QModelIndex
        """
        parent = node.parent()
        if parent is None:
            return QModelIndex()
        return self.createIndex(parent.children().index(node), 0, node)

    def entryAdded(self, node):
        """
        Public slot to add a bookmark node.

        @param node reference to the bookmark node to add
        @type BookmarkNode
        """
        if node is None or node.parent() is None:
            return

        parent = node.parent()
        row = parent.children().index(node)
        # node was already added so remove before beginInsertRows is called
        parent.remove(node)
        self.beginInsertRows(self.nodeIndex(parent), row, row)
        parent.add(node, row)
        self.endInsertRows()

    def entryRemoved(self, parent, row, node):
        """
        Public slot to remove a bookmark node.

        @param parent reference to the parent bookmark node
        @type BookmarkNode
        @param row row number of the node
        @type int
        @param node reference to the bookmark node to remove
        @type BookmarkNode
        """
        # node was already removed, re-add so beginRemoveRows works
        parent.add(node, row)
        self.beginRemoveRows(self.nodeIndex(parent), row, row)
        parent.remove(node)
        self.endRemoveRows()

    def entryChanged(self, node):
        """
        Public method to change a node.

        @param node reference to the bookmark node to change
        @type BookmarkNode
        """
        idx = self.nodeIndex(node)
        self.dataChanged.emit(idx, idx)

    def removeRows(self, row, count, parent=None):
        """
        Public method to remove bookmarks from the model.

        @param row row of the first bookmark to remove
        @type int
        @param count number of bookmarks to remove
        @type int
        @param parent index of the parent bookmark node
        @type QModelIndex
        @return flag indicating successful removal
        @rtype bool
        """
        if parent is None:
            parent = QModelIndex()

        if row < 0 or count <= 0 or row + count > self.rowCount(parent):
            return False

        bookmarkNode = self.node(parent)
        children = bookmarkNode.children()[row : (row + count)]
        for node in children:
            if node in (
                self.__bookmarksManager.menu(),
                self.__bookmarksManager.toolbar(),
            ):
                continue
            self.__bookmarksManager.removeBookmark(node)

        if self.__endMacro:
            self.__bookmarksManager.undoRedoStack().endMacro()
            self.__endMacro = False

        return True

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method to get the header data.

        @param section section number
        @type int
        @param orientation header orientation
        @type Qt.Orientation
        @param role data role
        @type Qt.ItemDataRole
        @return header data
        @rtype Any
        """
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            with contextlib.suppress(IndexError):
                return self.__headers[section]
        return QAbstractItemModel.headerData(self, section, orientation, role)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method to get data from the model.

        @param index index of bookmark to get data for
        @type QModelIndex
        @param role data role
        @type int
        @return bookmark data
        @rtype Any
        """
        from .BookmarkNode import BookmarkNodeType

        if not index.isValid() or index.model() != self:
            return None

        bookmarkNode = self.node(index)
        if role in [Qt.ItemDataRole.EditRole, Qt.ItemDataRole.DisplayRole]:
            if bookmarkNode.type() == BookmarkNodeType.Separator:
                if index.column() == 0:
                    return 50 * "\xb7"
                elif index.column() == 1:
                    return ""

            if index.column() == 0:
                return bookmarkNode.title
            elif index.column() == 1:
                return bookmarkNode.url

        elif role == BookmarksModel.UrlRole:
            return QUrl(bookmarkNode.url)

        elif role == BookmarksModel.UrlStringRole:
            return bookmarkNode.url

        elif role == BookmarksModel.VisitCountRole:
            return bookmarkNode.visitCount

        elif role == BookmarksModel.TypeRole:
            return bookmarkNode.type()

        elif role == BookmarksModel.SeparatorRole:
            return bookmarkNode.type() == BookmarkNodeType.Separator

        elif role == Qt.ItemDataRole.DecorationRole and index.column() == 0:
            if bookmarkNode.type() == BookmarkNodeType.Folder:
                return EricPixmapCache.getIcon("dirOpen")

            return WebBrowserWindow.icon(QUrl(bookmarkNode.url))

        return None

    def columnCount(self, parent=None):
        """
        Public method to get the number of columns.

        @param parent index of parent
        @type QModelIndex
        @return number of columns
        @rtype int
        """
        if parent is None:
            parent = QModelIndex()

        if parent.column() > 0:
            return 0
        else:
            return len(self.__headers)

    def rowCount(self, parent=None):
        """
        Public method to determine the number of rows.

        @param parent index of parent
        @type QModelIndex
        @return number of rows
        @rtype int
        """
        if parent is None:
            parent = QModelIndex()

        if parent.column() > 0:
            return 0

        if not parent.isValid():
            return len(self.__bookmarksManager.bookmarks().children())

        itm = parent.internalPointer()
        return len(itm.children())

    def index(self, row, column, parent=None):
        """
        Public method to get a model index for a node cell.

        @param row row number
        @type int
        @param column column number
        @type int
        @param parent index of the parent
        @type QModelIndex
        @return index
        @rtype QModelIndex
        """
        if parent is None:
            parent = QModelIndex()

        if (
            row < 0
            or column < 0
            or row >= self.rowCount(parent)
            or column >= self.columnCount(parent)
        ):
            return QModelIndex()

        parentNode = self.node(parent)
        return self.createIndex(row, column, parentNode.children()[row])

    def parent(self, index=None):
        """
        Public method to get the index of the parent node.

        @param index index of the child node
        @type QModelIndex
        @return index of the parent node
        @rtype QModelIndex
        """
        if index is None:
            index = QModelIndex()

        if not index.isValid():
            return QModelIndex()

        itemNode = self.node(index)
        parentNode = itemNode.parent() if itemNode else None

        if parentNode is None or parentNode == self.__bookmarksManager.bookmarks():
            return QModelIndex()

        # get the parent's row
        grandParentNode = parentNode.parent()
        parentRow = grandParentNode.children().index(parentNode)
        return self.createIndex(parentRow, 0, parentNode)

    def hasChildren(self, parent=None):
        """
        Public method to check, if a parent node has some children.

        @param parent index of the parent node
        @type QModelIndex
        @return flag indicating the presence of children
        @rtype bool
        """
        from .BookmarkNode import BookmarkNodeType

        if parent is None:
            parent = QModelIndex()

        if not parent.isValid():
            return True

        parentNode = self.node(parent)
        return parentNode.type() == BookmarkNodeType.Folder

    def flags(self, index):
        """
        Public method to get flags for a node cell.

        @param index index of the node cell
        @type QModelIndex
        @return flags
        @rtype Qt.ItemFlags
        """
        from .BookmarkNode import BookmarkNodeType

        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        node = self.node(index)
        type_ = node.type()
        flags = Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled

        if self.hasChildren(index):
            flags |= Qt.ItemFlag.ItemIsDropEnabled

        if node in (self.__bookmarksManager.menu(), self.__bookmarksManager.toolbar()):
            return flags

        flags |= Qt.ItemFlag.ItemIsDragEnabled

        if (index.column() == 0 and type_ != BookmarkNodeType.Separator) or (
            index.column() == 1 and type_ == BookmarkNodeType.Bookmark
        ):
            flags |= Qt.ItemFlag.ItemIsEditable

        return flags

    def supportedDropActions(self):
        """
        Public method to report the supported drop actions.

        @return supported drop actions
        @rtype Qt.DropAction
        """
        return Qt.DropAction.CopyAction | Qt.DropAction.MoveAction

    def mimeTypes(self):
        """
        Public method to report the supported mime types.

        @return supported mime types
        @rtype list of str
        """
        return [self.MIMETYPE, "text/uri-list"]

    def mimeData(self, indexes):
        """
        Public method to return the mime data.

        @param indexes list of indexes
        @type QModelIndexList
        @return mime data
        @rtype QMimeData
        """
        from .XbelWriter import XbelWriter

        data = QByteArray()
        stream = QDataStream(data, QIODevice.OpenModeFlag.WriteOnly)
        urls = []

        for index in indexes:
            if index.column() != 0 or not index.isValid():
                continue

            encodedData = QByteArray()
            buffer = QBuffer(encodedData)
            buffer.open(QIODevice.OpenModeFlag.ReadWrite)
            writer = XbelWriter()
            parentNode = self.node(index)
            writer.write(buffer, parentNode)
            stream << encodedData
            urls.append(index.data(self.UrlRole))

        mdata = QMimeData()
        mdata.setData(self.MIMETYPE, data)
        mdata.setUrls(urls)
        return mdata

    def dropMimeData(self, data, action, row, column, parent):
        """
        Public method to accept the mime data of a drop action.

        @param data reference to the mime data
        @type QMimeData
        @param action drop action requested
        @type Qt.DropAction
        @param row row number
        @type int
        @param column column number
        @type int
        @param parent index of the parent node
        @type QModelIndex
        @return flag indicating successful acceptance of the data
        @rtype bool
        """
        from .BookmarkNode import BookmarkNode, BookmarkNodeType
        from .XbelReader import XbelReader

        if action == Qt.DropAction.IgnoreAction:
            return True

        if column > 0:
            return False

        parentNode = self.node(parent)

        if not data.hasFormat(self.MIMETYPE):
            if not data.hasUrls():
                return False

            node = BookmarkNode(BookmarkNodeType.Bookmark, parentNode)
            node.url = bytes(data.urls()[0].toEncoded()).decode()

            if data.hasText():
                node.title = data.text()
            else:
                node.title = node.url

            self.__bookmarksManager.addBookmark(parentNode, node, row)
            return True

        ba = data.data(self.MIMETYPE)
        stream = QDataStream(ba, QIODevice.OpenModeFlag.ReadOnly)
        if stream.atEnd():
            return False

        undoStack = self.__bookmarksManager.undoRedoStack()
        undoStack.beginMacro("Move Bookmarks")

        while not stream.atEnd():
            encodedData = QByteArray()
            stream >> encodedData
            buffer = QBuffer(encodedData)
            buffer.open(QIODevice.OpenModeFlag.ReadOnly)

            reader = XbelReader()
            rootNode = reader.read(buffer)
            for bookmarkNode in rootNode.children():
                rootNode.remove(bookmarkNode)
                row = max(0, row)
                self.__bookmarksManager.addBookmark(parentNode, bookmarkNode, row)
                self.__endMacro = True

        return True

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """
        Public method to set the data of a node cell.

        @param index index of the node cell
        @type QModelIndex
        @param value value to be set
        @type Any
        @param role role of the data
        @type int
        @return flag indicating success
        @rtype bool
        """
        if not index.isValid() or (self.flags(index) & Qt.ItemFlag.ItemIsEditable) == 0:
            return False

        item = self.node(index)

        if role in (Qt.ItemDataRole.EditRole, Qt.ItemDataRole.DisplayRole):
            if index.column() == 0:
                self.__bookmarksManager.setTitle(item, value)
            elif index.column() == 1:
                self.__bookmarksManager.setUrl(item, value)
            else:
                return False

        elif role == BookmarksModel.UrlRole:
            self.__bookmarksManager.setUrl(item, value.toString())

        elif role == BookmarksModel.UrlStringRole:
            self.__bookmarksManager.setUrl(item, value)

        elif role == BookmarksModel.VisitCountRole:
            self.__bookmarksManager.setVisitCount(item, value)

        else:
            return False

        return True

    def node(self, index):
        """
        Public method to get a bookmark node given its index.

        @param index index of the node
        @type QModelIndex
        @return bookmark node
        @rtype BookmarkNode
        """
        itemNode = index.internalPointer()
        if itemNode is None:
            return self.__bookmarksManager.bookmarks()
        else:
            return itemNode
