# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the bookmarks menu.
"""

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QMenu

from eric7.EricWidgets.EricModelMenu import EricModelMenu
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .BookmarkNode import BookmarkNodeType
from .BookmarksModel import BookmarksModel


class BookmarksMenu(EricModelMenu):
    """
    Class implementing the bookmarks menu base class.

    @signal openUrl(QUrl, str) emitted to open a URL with the given title in
        the current tab
    @signal newTab(QUrl, str) emitted to open a URL with the given title in a
        new tab
    @signal newWindow(QUrl, str) emitted to open a URL with the given title in
        a new window
    """

    openUrl = pyqtSignal(QUrl, str)
    newTab = pyqtSignal(QUrl, str)
    newWindow = pyqtSignal(QUrl, str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        EricModelMenu.__init__(self, parent)

        self.activated.connect(self.__activated)
        self.setStatusBarTextRole(BookmarksModel.UrlStringRole)
        self.setSeparatorRole(BookmarksModel.SeparatorRole)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__contextMenuRequested)

    def createBaseMenu(self):
        """
        Public method to get the menu that is used to populate sub menu's.

        @return reference to the menu
        @rtype BookmarksMenu
        """
        menu = BookmarksMenu(self)
        menu.openUrl.connect(self.openUrl)
        menu.newTab.connect(self.newTab)
        menu.newWindow.connect(self.newWindow)
        return menu

    def __updateVisitCount(self, idx):
        """
        Private method to update the visit count of a bookmark.

        @param idx index of the bookmark item
        @type QModelIndex
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        bookmarkNode = self.model().node(idx)
        manager = WebBrowserWindow.bookmarksManager()
        manager.incVisitCount(bookmarkNode)

    def __activated(self, idx):
        """
        Private slot handling the activated signal.

        @param idx index of the activated item
        @type QModelIndex
        """
        if self._keyboardModifiers & Qt.KeyboardModifier.ControlModifier:
            self.newTab.emit(
                idx.data(BookmarksModel.UrlRole), idx.data(Qt.ItemDataRole.DisplayRole)
            )
        elif self._keyboardModifiers & Qt.KeyboardModifier.ShiftModifier:
            self.newWindow.emit(
                idx.data(BookmarksModel.UrlRole), idx.data(Qt.ItemDataRole.DisplayRole)
            )
        else:
            self.openUrl.emit(
                idx.data(BookmarksModel.UrlRole), idx.data(Qt.ItemDataRole.DisplayRole)
            )
        self.__updateVisitCount(idx)

    def postPopulated(self):
        """
        Public method to add any actions after the tree.
        """
        if self.isEmpty():
            return

        parent = self.rootIndex()

        hasBookmarks = False

        for i in range(parent.model().rowCount(parent)):
            child = parent.model().index(i, 0, parent)

            if child.data(BookmarksModel.TypeRole) == BookmarkNodeType.Bookmark:
                hasBookmarks = True
                break

        if not hasBookmarks:
            return

        self.addSeparator()
        act = self.addAction(self.tr("Open all in Tabs"))
        act.triggered.connect(lambda: self.openAll(act))

    def openAll(self, act):
        """
        Public slot to open all the menu's items.

        @param act reference to the action object
        @type QAction
        """
        menu = act.parent()
        if menu is None:
            return

        parent = menu.rootIndex()
        if not parent.isValid():
            return

        for i in range(parent.model().rowCount(parent)):
            child = parent.model().index(i, 0, parent)

            if child.data(BookmarksModel.TypeRole) != BookmarkNodeType.Bookmark:
                continue

            if i == 0:
                self.openUrl.emit(
                    child.data(BookmarksModel.UrlRole),
                    child.data(Qt.ItemDataRole.DisplayRole),
                )
            else:
                self.newTab.emit(
                    child.data(BookmarksModel.UrlRole),
                    child.data(Qt.ItemDataRole.DisplayRole),
                )
            self.__updateVisitCount(child)

    def __contextMenuRequested(self, pos):
        """
        Private slot to handle the context menu request.

        @param pos position the context menu shall be shown
        @type QPoint
        """
        act = self.actionAt(pos)

        if (
            act is not None
            and act not in self.menuActions
            and self.index(act).isValid()
        ):
            menu = QMenu()
            v = act.data()

            act2 = menu.addAction(self.tr("Open"))
            act2.setData(v)
            act2.triggered.connect(lambda: self.__openBookmark(act2))
            act2 = menu.addAction(self.tr("Open in New Tab\tCtrl+LMB"))
            act2.setData(v)
            act2.triggered.connect(lambda: self.__openBookmarkInNewTab(act2))
            act2 = menu.addAction(self.tr("Open in New Window"))
            act2.setData(v)
            act2.triggered.connect(lambda: self.__openBookmarkInNewWindow(act2))
            act2 = menu.addAction(self.tr("Open in New Private Window"))
            act2.setData(v)
            act2.triggered.connect(lambda: self.__openBookmarkInPrivateWindow(act2))
            menu.addSeparator()

            act2 = menu.addAction(self.tr("Remove"))
            act2.setData(v)
            act2.triggered.connect(lambda: self.__removeBookmark(act2))
            menu.addSeparator()

            act2 = menu.addAction(self.tr("Properties..."))
            act2.setData(v)
            act2.triggered.connect(lambda: self.__edit(act2))

            execAct = menu.exec(QCursor.pos())
            if execAct is not None:
                self.close()
                parent = self.parent()
                while parent is not None and isinstance(parent, QMenu):
                    parent.close()
                    parent = parent.parent()

    def __openBookmark(self, act):
        """
        Private slot to open a bookmark in the current browser tab.

        @param act reference to the triggering action
        @type QAction
        """
        idx = self.index(act)

        self.openUrl.emit(
            idx.data(BookmarksModel.UrlRole), idx.data(Qt.ItemDataRole.DisplayRole)
        )
        self.__updateVisitCount(idx)

    def __openBookmarkInNewTab(self, act):
        """
        Private slot to open a bookmark in a new browser tab.

        @param act reference to the triggering action
        @type QAction
        """
        idx = self.index(act)

        self.newTab.emit(
            idx.data(BookmarksModel.UrlRole), idx.data(Qt.ItemDataRole.DisplayRole)
        )
        self.__updateVisitCount(idx)

    def __openBookmarkInNewWindow(self, act):
        """
        Private slot to open a bookmark in a new window.

        @param act reference to the triggering action
        @type QAction
        """
        idx = self.index(act)
        url = idx.data(BookmarksModel.UrlRole)

        WebBrowserWindow.mainWindow().newWindow(url)
        self.__updateVisitCount(idx)

    def __openBookmarkInPrivateWindow(self, act):
        """
        Private slot to open a bookmark in a new private window.

        @param act reference to the triggering action
        @type QAction
        """
        idx = self.index(act)
        url = idx.data(BookmarksModel.UrlRole)

        WebBrowserWindow.mainWindow().newPrivateWindow(url)
        self.__updateVisitCount(idx)

    def __removeBookmark(self, act):
        """
        Private slot to remove a bookmark.

        @param act reference to the triggering action
        @type QAction
        """
        idx = self.index(act)
        self.removeEntry(idx)

    def __edit(self, act):
        """
        Private slot to edit a bookmarks properties.

        @param act reference to the triggering action
        @type QAction
        """
        from .BookmarkPropertiesDialog import BookmarkPropertiesDialog

        idx = self.index(act)
        node = self.model().node(idx)
        dlg = BookmarkPropertiesDialog(node)
        dlg.exec()


##############################################################################


class BookmarksMenuBarMenu(BookmarksMenu):
    """
    Class implementing a dynamically populated menu for bookmarks.

    @signal openUrl(QUrl, str) emitted to open a URL with the given title in
        the current tab
    """

    openUrl = pyqtSignal(QUrl, str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        BookmarksMenu.__init__(self, parent)

        self.__initialActions = []

    def prePopulated(self):
        """
        Public method to add any actions before the tree.

        @return flag indicating if any actions were added
        @rtype bool
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        manager = WebBrowserWindow.bookmarksManager()
        self.setModel(manager.bookmarksModel())
        self.setRootIndex(manager.bookmarksModel().nodeIndex(manager.menu()))

        # initial actions
        for act in self.__initialActions:
            if act == "--SEPARATOR--":
                self.addSeparator()
            else:
                self.addAction(act)
        if len(self.__initialActions) != 0:
            self.addSeparator()

        self.createMenu(manager.bookmarksModel().nodeIndex(manager.toolbar()), 1, self)
        return True

    def postPopulated(self):
        """
        Public method to add any actions after the tree.
        """
        if self.isEmpty():
            return

        parent = self.rootIndex()

        hasBookmarks = False

        for i in range(parent.model().rowCount(parent)):
            child = parent.model().index(i, 0, parent)

            if child.data(BookmarksModel.TypeRole) == BookmarkNodeType.Bookmark:
                hasBookmarks = True
                break

        if not hasBookmarks:
            return

        self.addSeparator()
        act_1 = self.addAction(self.tr("Default Home Page"))
        act_1.setData("eric:home")
        act_1.triggered.connect(lambda: self.__defaultBookmarkTriggered(act_1))
        act_2 = self.addAction(self.tr("Speed Dial"))
        act_2.setData("eric:speeddial")
        act_2.triggered.connect(lambda: self.__defaultBookmarkTriggered(act_2))
        self.addSeparator()
        act_3 = self.addAction(self.tr("Open all in Tabs"))
        act_3.triggered.connect(lambda: self.openAll(act_3))

    def setInitialActions(self, actions):
        """
        Public method to set the list of actions that should appear first in
        the menu.

        @param actions list of initial actions
        @type list of QAction
        """
        self.__initialActions = actions[:]
        for act in self.__initialActions:
            self.addAction(act)

    def __defaultBookmarkTriggered(self, act):
        """
        Private slot handling the default bookmark menu entries.

        @param act reference to the action object
        @type QAction
        """
        urlStr = act.data()
        if urlStr.startswith("eric:"):
            self.openUrl.emit(QUrl(urlStr), "")
