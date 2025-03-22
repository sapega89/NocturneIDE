# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the bookmarks manager.
"""

import contextlib
import enum
import os
import pathlib

from PyQt6.QtCore import (
    QT_TRANSLATE_NOOP,
    QCoreApplication,
    QDateTime,
    QFile,
    QIODevice,
    QObject,
    QUrl,
    QXmlStreamReader,
    pyqtSignal,
)
from PyQt6.QtGui import QUndoCommand, QUndoStack
from PyQt6.QtWidgets import QDialog

from eric7 import EricUtilities
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.Utilities.AutoSaver import AutoSaver

from .BookmarkNode import BookmarkNode, BookmarkNodeType, BookmarkTimestampType

BOOKMARKBAR = QT_TRANSLATE_NOOP("BookmarksManager", "Bookmarks Bar")
BOOKMARKMENU = QT_TRANSLATE_NOOP("BookmarksManager", "Bookmarks Menu")


class BookmarkSearchStart(enum.Enum):
    """
    Class defining the start points for bookmark searches.
    """

    Root = 0
    Menu = 1
    ToolBar = 2


class BookmarksManager(QObject):
    """
    Class implementing the bookmarks manager.

    @signal entryAdded(BookmarkNode) emitted after a bookmark node has been
        added
    @signal entryRemoved(BookmarkNode, int, BookmarkNode) emitted after a
        bookmark node has been removed
    @signal entryChanged(BookmarkNode) emitted after a bookmark node has been
        changed
    @signal bookmarksSaved() emitted after the bookmarks were saved
    @signal bookmarksReloaded() emitted after the bookmarks were reloaded
    """

    entryAdded = pyqtSignal(BookmarkNode)
    entryRemoved = pyqtSignal(BookmarkNode, int, BookmarkNode)
    entryChanged = pyqtSignal(BookmarkNode)
    bookmarksSaved = pyqtSignal()
    bookmarksReloaded = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__saveTimer = AutoSaver(self, self.save)
        self.entryAdded.connect(self.__saveTimer.changeOccurred)
        self.entryRemoved.connect(self.__saveTimer.changeOccurred)
        self.entryChanged.connect(self.__saveTimer.changeOccurred)

        self.__initialize()

    def __initialize(self):
        """
        Private method to initialize some data.
        """
        self.__loaded = False
        self.__bookmarkRootNode = None
        self.__toolbar = None
        self.__menu = None
        self.__bookmarksModel = None
        self.__commands = QUndoStack()

    @classmethod
    def getFileName(cls):
        """
        Class method to get the file name of the bookmark file.

        @return name of the bookmark file
        @rtype str
        """
        return os.path.join(
            EricUtilities.getConfigDir(), "web_browser", "bookmarks.xbel"
        )

    def close(self):
        """
        Public method to close the bookmark manager.
        """
        self.__saveTimer.saveIfNeccessary()

    def undoRedoStack(self):
        """
        Public method to get a reference to the undo stack.

        @return reference to the undo stack
        @rtype QUndoStack
        """
        return self.__commands

    def changeExpanded(self):
        """
        Public method to handle a change of the expanded state.
        """
        self.__saveTimer.changeOccurred()

    def reload(self):
        """
        Public method used to initiate a reloading of the bookmarks.
        """
        self.__initialize()
        self.load()
        self.bookmarksReloaded.emit()

    def load(self):
        """
        Public method to load the bookmarks.

        @exception RuntimeError raised to indicate an error loading the
            bookmarks
        """
        from .XbelReader import XbelReader

        if self.__loaded:
            return

        self.__loaded = True

        bookmarkFile = self.getFileName()
        if not QFile.exists(bookmarkFile):
            bookmarkFile = QFile(
                os.path.join(os.path.dirname(__file__), "DefaultBookmarks.xbel")
            )
            bookmarkFile.open(QIODevice.OpenModeFlag.ReadOnly)

        reader = XbelReader()
        self.__bookmarkRootNode = reader.read(bookmarkFile)
        if reader.error() != QXmlStreamReader.Error.NoError:
            EricMessageBox.warning(
                None,
                self.tr("Loading Bookmarks"),
                self.tr(
                    """Error when loading bookmarks on line {0},"""
                    """ column {1}:\n {2}"""
                ).format(
                    reader.lineNumber(), reader.columnNumber(), reader.errorString()
                ),
            )

        others = []
        for index in range(len(self.__bookmarkRootNode.children()) - 1, -1, -1):
            node = self.__bookmarkRootNode.children()[index]
            if node.type() == BookmarkNodeType.Folder:
                if (
                    node.title == self.tr("Toolbar Bookmarks")
                    or node.title == BOOKMARKBAR
                ) and self.__toolbar is None:
                    node.title = self.tr(BOOKMARKBAR)
                    self.__toolbar = node

                if (
                    node.title == self.tr("Menu") or node.title == BOOKMARKMENU
                ) and self.__menu is None:
                    node.title = self.tr(BOOKMARKMENU)
                    self.__menu = node
            else:
                others.append(node)
            self.__bookmarkRootNode.remove(node)

        if len(self.__bookmarkRootNode.children()) > 0:
            raise RuntimeError("Error loading bookmarks.")

        if self.__toolbar is None:
            self.__toolbar = BookmarkNode(
                BookmarkNodeType.Folder, self.__bookmarkRootNode
            )
            self.__toolbar.title = self.tr(BOOKMARKBAR)
        else:
            self.__bookmarkRootNode.add(self.__toolbar)

        if self.__menu is None:
            self.__menu = BookmarkNode(BookmarkNodeType.Folder, self.__bookmarkRootNode)
            self.__menu.title = self.tr(BOOKMARKMENU)
        else:
            self.__bookmarkRootNode.add(self.__menu)

        for node in others:
            self.__menu.add(node)

    def save(self):
        """
        Public method to save the bookmarks.
        """
        from .XbelWriter import XbelWriter

        if not self.__loaded:
            return

        writer = XbelWriter()
        bookmarkFile = self.getFileName()

        # save root folder titles in English (i.e. not localized)
        self.__menu.title = BOOKMARKMENU
        self.__toolbar.title = BOOKMARKBAR
        if not writer.write(bookmarkFile, self.__bookmarkRootNode):
            EricMessageBox.warning(
                None,
                self.tr("Saving Bookmarks"),
                self.tr("""Error saving bookmarks to <b>{0}</b>.""").format(
                    bookmarkFile
                ),
            )

        # restore localized titles
        self.__menu.title = self.tr(BOOKMARKMENU)
        self.__toolbar.title = self.tr(BOOKMARKBAR)

        self.bookmarksSaved.emit()

    def addBookmark(self, parent, node, row=-1):
        """
        Public method to add a bookmark.

        @param parent reference to the node to add to
        @type BookmarkNode
        @param node reference to the node to add
        @type BookmarkNode
        @param row row number
        @type int
        """
        if not self.__loaded:
            return

        self.setTimestamp(
            node, BookmarkTimestampType.Added, QDateTime.currentDateTime()
        )

        command = InsertBookmarksCommand(self, parent, node, row)
        self.__commands.push(command)

    def removeBookmark(self, node):
        """
        Public method to remove a bookmark.

        @param node reference to the node to be removed
        @type BookmarkNode
        """
        if not self.__loaded:
            return

        parent = node.parent()
        row = parent.children().index(node)
        command = RemoveBookmarksCommand(self, parent, row)
        self.__commands.push(command)

    def setTitle(self, node, newTitle):
        """
        Public method to set the title of a bookmark.

        @param node reference to the node to be changed
        @type BookmarkNode
        @param newTitle title to be set
        @type str
        """
        if not self.__loaded:
            return

        command = ChangeBookmarkCommand(self, node, newTitle, True)
        self.__commands.push(command)

    def setUrl(self, node, newUrl):
        """
        Public method to set the URL of a bookmark.

        @param node reference to the node to be changed
        @type BookmarkNode
        @param newUrl URL to be set
        @type str
        """
        if not self.__loaded:
            return

        command = ChangeBookmarkCommand(self, node, newUrl, False)
        self.__commands.push(command)

    def setNodeChanged(self):
        """
        Public method to signal changes of bookmarks other than title, URL
        or timestamp.
        """
        self.__saveTimer.changeOccurred()

    def setTimestamp(self, node, timestampType, timestamp):
        """
        Public method to set the URL of a bookmark.

        @param node reference to the node to be changed
        @type BookmarkNode
        @param timestampType type of the timestamp to set
        @type BookmarkTimestampType
        @param timestamp timestamp to set
        @type QDateTime
        """
        if not self.__loaded:
            return

        if timestampType == BookmarkTimestampType.Added:
            node.added = timestamp
        elif timestampType == BookmarkTimestampType.Modified:
            node.modified = timestamp
        elif timestampType == BookmarkTimestampType.Visited:
            node.visited = timestamp
        self.__saveTimer.changeOccurred()

    def incVisitCount(self, node):
        """
        Public method to increment the visit count of a bookmark.

        @param node reference to the node to be changed
        @type BookmarkNode
        """
        if not self.__loaded:
            return

        if node:
            node.visitCount += 1
            self.__saveTimer.changeOccurred()

    def setVisitCount(self, node, count):
        """
        Public method to set the visit count of a bookmark.

        @param node reference to the node to be changed
        @type BookmarkNode
        @param count visit count to be set
        @type int or str
        """
        with contextlib.suppress(ValueError):
            node.visitCount = int(count)
            self.__saveTimer.changeOccurred()

    def bookmarks(self):
        """
        Public method to get a reference to the root bookmark node.

        @return reference to the root bookmark node
        @rtype BookmarkNode
        """
        if not self.__loaded:
            self.load()

        return self.__bookmarkRootNode

    def menu(self):
        """
        Public method to get a reference to the bookmarks menu node.

        @return reference to the bookmarks menu node
        @rtype BookmarkNode
        """
        if not self.__loaded:
            self.load()

        return self.__menu

    def toolbar(self):
        """
        Public method to get a reference to the bookmarks toolbar node.

        @return reference to the bookmarks toolbar node
        @rtype BookmarkNode
        """
        if not self.__loaded:
            self.load()

        return self.__toolbar

    def bookmarksModel(self):
        """
        Public method to get a reference to the bookmarks model.

        @return reference to the bookmarks model
        @rtype BookmarksModel
        """
        from .BookmarksModel import BookmarksModel

        if self.__bookmarksModel is None:
            self.__bookmarksModel = BookmarksModel(self, self)
        return self.__bookmarksModel

    def importBookmarks(self):
        """
        Public method to import bookmarks.
        """
        from .BookmarksImportDialog import BookmarksImportDialog

        dlg = BookmarksImportDialog()
        if dlg.exec() == QDialog.DialogCode.Accepted:
            importRootNode = dlg.getImportedBookmarks()
            if importRootNode is not None:
                self.addBookmark(self.menu(), importRootNode)

    def exportBookmarks(self):
        """
        Public method to export the bookmarks.
        """
        fileName, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            None,
            self.tr("Export Bookmarks"),
            "eric7_bookmarks.xbel",
            self.tr(
                "XBEL bookmarks (*.xbel);;"
                "XBEL bookmarks (*.xml);;"
                "HTML Bookmarks (*.html)"
            ),
        )
        if not fileName:
            return

        fpath = pathlib.Path(fileName)
        if not fpath.suffix:
            ex = selectedFilter.split("(*")[1].split(")")[0]
            if ex:
                fpath = fpath.with_suffix(ex)

        if fpath.suffix == ".html":
            from .NsHtmlWriter import NsHtmlWriter  # __IGNORE_WARNING_I101__

            writer = NsHtmlWriter()
        else:
            from .XbelWriter import XbelWriter  # __IGNORE_WARNING_I101__

            writer = XbelWriter()
        if not writer.write(str(fpath), self.__bookmarkRootNode):
            EricMessageBox.critical(
                None,
                self.tr("Exporting Bookmarks"),
                self.tr("""Error exporting bookmarks to <b>{0}</b>.""").format(fpath),
            )

    def faviconChanged(self, url):
        """
        Public slot to update the icon image for an URL.

        @param url URL of the icon to update
        @type QUrl or str
        """
        if isinstance(url, QUrl):
            url = url.toString()
        nodes = self.bookmarksForUrl(url)
        for node in nodes:
            self.bookmarksModel().entryChanged(node)

    def bookmarkForUrl(self, url, start=BookmarkSearchStart.Root):
        """
        Public method to get a bookmark node for a given URL.

        @param url URL of the bookmark to search for
        @type QUrl or str
        @param start indicator for the start of the search
        @type BookmarkSearchStart
        @return bookmark node for the given url
        @rtype BookmarkNode
        """
        if start == BookmarkSearchStart.Menu:
            startNode = self.__menu
        elif start == BookmarkSearchStart.ToolBar:
            startNode = self.__toolbar
        else:
            startNode = self.__bookmarkRootNode
        if startNode is None:
            return None

        if isinstance(url, QUrl):
            url = url.toString()

        return self.__searchBookmark(url, startNode)

    def __searchBookmark(self, url, startNode):
        """
        Private method get a bookmark node for a given URL.

        @param url URL of the bookmark to search for
        @type str
        @param startNode reference to the node to start searching
        @type BookmarkNode
        @return bookmark node for the given url
        @rtype BookmarkNode
        """
        bm = None
        for node in startNode.children():
            if node.type() == BookmarkNodeType.Folder:
                bm = self.__searchBookmark(url, node)
            elif node.type() == BookmarkNodeType.Bookmark and node.url == url:
                bm = node
            if bm is not None:
                return bm
        return None

    def bookmarksForUrl(self, url, start=BookmarkSearchStart.Root):
        """
        Public method to get a list of bookmark nodes for a given URL.

        @param url URL of the bookmarks to search for
        @type QUrl or str
        @param start indicator for the start of the search
        @type BookmarkSearchStart
        @return list of bookmark nodes for the given url
        @rtype list of BookmarkNode
        """
        if start == BookmarkSearchStart.Menu:
            startNode = self.__menu
        elif start == BookmarkSearchStart.ToolBar:
            startNode = self.__toolbar
        else:
            startNode = self.__bookmarkRootNode
        if startNode is None:
            return []

        if isinstance(url, QUrl):
            url = url.toString()

        return self.__searchBookmarks(url, startNode)

    def __searchBookmarks(self, url, startNode):
        """
        Private method get a list of bookmark nodes for a given URL.

        @param url URL of the bookmarks to search for
        @type str
        @param startNode reference to the node to start searching
        @type BookmarkNode
        @return list of bookmark nodes for the given url
        @rtype list of BookmarkNode
        """
        bm = []
        for node in startNode.children():
            if node.type() == BookmarkNodeType.Folder:
                bm.extend(self.__searchBookmarks(url, node))
            elif node.type() == BookmarkNodeType.Bookmark and node.url == url:
                bm.append(node)
        return bm


class RemoveBookmarksCommand(QUndoCommand):
    """
    Class implementing the Remove undo command.
    """

    def __init__(self, bookmarksManager, parent, row):
        """
        Constructor

        @param bookmarksManager reference to the bookmarks manager
        @type BookmarksManager
        @param parent reference to the parent node
        @type BookmarkNode
        @param row row number of bookmark
        @type int
        """
        super().__init__(
            QCoreApplication.translate("BookmarksManager", "Remove Bookmark")
        )

        self._row = row
        self._bookmarksManager = bookmarksManager
        try:
            self._node = parent.children()[row]
        except IndexError:
            self._node = BookmarkNode()
        self._parent = parent

    def undo(self):
        """
        Public slot to perform the undo action.
        """
        self._parent.add(self._node, self._row)
        self._bookmarksManager.entryAdded.emit(self._node)

    def redo(self):
        """
        Public slot to perform the redo action.
        """
        self._parent.remove(self._node)
        self._bookmarksManager.entryRemoved.emit(self._parent, self._row, self._node)


class InsertBookmarksCommand(RemoveBookmarksCommand):
    """
    Class implementing the Insert undo command.
    """

    def __init__(self, bookmarksManager, parent, node, row):
        """
        Constructor

        @param bookmarksManager reference to the bookmarks manager
        @type BookmarksManager
        @param parent reference to the parent node
        @type BookmarkNode
        @param node reference to the node to be inserted
        @type BookmarkNode
        @param row row number of bookmark
        @type int
        """
        RemoveBookmarksCommand.__init__(self, bookmarksManager, parent, row)
        self.setText(QCoreApplication.translate("BookmarksManager", "Insert Bookmark"))
        self._node = node

    def undo(self):
        """
        Public slot to perform the undo action.
        """
        RemoveBookmarksCommand.redo(self)

    def redo(self):
        """
        Public slot to perform the redo action.
        """
        RemoveBookmarksCommand.undo(self)


class ChangeBookmarkCommand(QUndoCommand):
    """
    Class implementing the Insert undo command.
    """

    def __init__(self, bookmarksManager, node, newValue, title):
        """
        Constructor

        @param bookmarksManager reference to the bookmarks manager
        @type BookmarksManager
        @param node reference to the node to be changed
        @type BookmarkNode
        @param newValue new value to be set
        @type str
        @param title flag indicating a change of the title (True) or
            the URL (False)
        @type bool
        """
        super().__init__()

        self._bookmarksManager = bookmarksManager
        self._title = title
        self._newValue = newValue
        self._node = node

        if self._title:
            self._oldValue = self._node.title
            self.setText(QCoreApplication.translate("BookmarksManager", "Name Change"))
        else:
            self._oldValue = self._node.url
            self.setText(
                QCoreApplication.translate("BookmarksManager", "Address Change")
            )

    def undo(self):
        """
        Public slot to perform the undo action.
        """
        if self._title:
            self._node.title = self._oldValue
        else:
            self._node.url = self._oldValue
        self._bookmarksManager.entryChanged.emit(self._node)

    def redo(self):
        """
        Public slot to perform the redo action.
        """
        if self._title:
            self._node.title = self._newValue
        else:
            self._node.url = self._newValue
        self._bookmarksManager.entryChanged.emit(self._node)
