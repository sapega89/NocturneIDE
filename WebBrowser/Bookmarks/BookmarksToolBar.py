# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a tool bar showing bookmarks.
"""

from PyQt6.QtCore import QCoreApplication, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWidgets import QMenu

from eric7.EricWidgets.EricModelToolBar import EricModelToolBar
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .BookmarksModel import BookmarksModel


class BookmarksToolBar(EricModelToolBar):
    """
    Class implementing a tool bar showing bookmarks.

    @signal openUrl(QUrl, str) emitted to open a URL in the current tab
    @signal newTab(QUrl, str) emitted to open a URL in a new tab
    @signal newWindow(QUrl, str) emitted to open a URL in a new window
    """

    openUrl = pyqtSignal(QUrl, str)
    newTab = pyqtSignal(QUrl, str)
    newWindow = pyqtSignal(QUrl, str)

    def __init__(self, mainWindow, model, parent=None):
        """
        Constructor

        @param mainWindow reference to the main window
        @type WebBrowserWindow
        @param model reference to the bookmarks model
        @type BookmarksModel
        @param parent reference to the parent widget
        @type QWidget
        """
        EricModelToolBar.__init__(
            self, QCoreApplication.translate("BookmarksToolBar", "Bookmarks"), parent
        )

        self.__mw = mainWindow
        self.__bookmarksModel = model

        self.__mw.bookmarksManager().bookmarksReloaded.connect(self.__rebuild)

        self.setModel(model)
        self.setRootIndex(model.nodeIndex(self.__mw.bookmarksManager().toolbar()))

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__contextMenuRequested)
        self.activated.connect(self.__bookmarkActivated)

        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        self._build()

    def __rebuild(self):
        """
        Private slot to rebuild the toolbar.
        """
        self.__bookmarksModel = self.__mw.bookmarksManager().bookmarksModel()
        self.setModel(self.__bookmarksModel)
        self.setRootIndex(
            self.__bookmarksModel.nodeIndex(self.__mw.bookmarksManager().toolbar())
        )
        self._build()

    def __contextMenuRequested(self, pos):
        """
        Private slot to handle the context menu request.

        @param pos position the context menu shall be shown
        @type QPoint
        """
        act = self.actionAt(pos)
        menu = QMenu()

        if act is not None:
            v = act.data()

            button = self.widgetForAction(act)
            if button.menu() is None:
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
            menu.addSeparator()

        menu.addAction(self.tr("Add Bookmark..."), self.__newBookmark)
        menu.addAction(self.tr("Add Folder..."), self.__newFolder)

        menu.exec(QCursor.pos())

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

    def __bookmarkActivated(self, idx):
        """
        Private slot handling the activation of a bookmark.

        @param idx index of the activated bookmark
        @type QModelIndex
        """
        if idx.isValid():
            if self._mouseButton == Qt.MouseButton.XButton1:
                self.__mw.currentBrowser().triggerPageAction(
                    QWebEnginePage.WebAction.Back
                )
            elif self._mouseButton == Qt.MouseButton.XButton2:
                self.__mw.currentBrowser().triggerPageAction(
                    QWebEnginePage.WebAction.Forward
                )
            elif self._mouseButton == Qt.MouseButton.LeftButton:
                if self._keyboardModifiers & Qt.KeyboardModifier.ControlModifier:
                    self.newTab.emit(
                        idx.data(BookmarksModel.UrlRole),
                        idx.data(Qt.ItemDataRole.DisplayRole),
                    )
                elif self._keyboardModifiers & Qt.KeyboardModifier.ShiftModifier:
                    self.newWindow.emit(
                        idx.data(BookmarksModel.UrlRole),
                        idx.data(Qt.ItemDataRole.DisplayRole),
                    )
                else:
                    self.openUrl.emit(
                        idx.data(BookmarksModel.UrlRole),
                        idx.data(Qt.ItemDataRole.DisplayRole),
                    )
                self.__updateVisitCount(idx)

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

        self.newWindow.emit(
            idx.data(BookmarksModel.UrlRole), idx.data(Qt.ItemDataRole.DisplayRole)
        )
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

        self.__bookmarksModel.removeRow(idx.row(), self.rootIndex())

    def __newBookmark(self):
        """
        Private slot to add a new bookmark.
        """
        from .AddBookmarkDialog import AddBookmarkDialog

        dlg = AddBookmarkDialog(parent=self)
        dlg.setCurrentIndex(self.rootIndex())
        dlg.exec()

    def __newFolder(self):
        """
        Private slot to add a new bookmarks folder.
        """
        from .AddBookmarkDialog import AddBookmarkDialog

        dlg = AddBookmarkDialog(parent=self)
        dlg.setCurrentIndex(self.rootIndex())
        dlg.setFolder(True)
        dlg.exec()

    def _createMenu(self):
        """
        Protected method to create the menu for a tool bar action.

        @return menu for a tool bar action
        @rtype EricModelMenu
        """
        from .BookmarksMenu import BookmarksMenu

        menu = BookmarksMenu(self)
        menu.openUrl.connect(self.openUrl)
        menu.newTab.connect(self.newTab)
        menu.newWindow.connect(self.newWindow)
        return menu

    def __edit(self, act):
        """
        Private slot to edit a bookmarks properties.

        @param act reference to the triggering action
        @type QAction
        """
        from .BookmarkPropertiesDialog import BookmarkPropertiesDialog

        idx = self.index(act)
        node = self.__bookmarksModel.node(idx)
        dlg = BookmarkPropertiesDialog(node, parent=self)
        dlg.exec()
