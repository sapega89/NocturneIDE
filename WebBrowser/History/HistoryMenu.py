# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the history menu.
"""

import functools
import sys

from PyQt6.QtCore import (
    QAbstractProxyModel,
    QMimeData,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtWidgets import QMenu

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricModelMenu import EricModelMenu
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .HistoryModel import HistoryModel


class HistoryMenuModel(QAbstractProxyModel):
    """
    Class implementing a model for the history menu.

    It maps the first bunch of items of the source model to the root.
    """

    MOVEDROWS = 15

    def __init__(self, sourceModel, parent=None):
        """
        Constructor

        @param sourceModel reference to the source model
        @type QAbstractItemModel
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__treeModel = sourceModel

        self.setSourceModel(sourceModel)

    def bumpedRows(self):
        """
        Public method to determine the number of rows moved to the root.

        @return number of rows moved to the root
        @rtype int
        """
        first = self.__treeModel.index(0, 0)
        if not first.isValid():
            return 0
        return min(self.__treeModel.rowCount(first), self.MOVEDROWS)

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

        return self.__treeModel.columnCount(self.mapToSource(parent))

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
            folders = self.sourceModel().rowCount()
            bumpedItems = self.bumpedRows()
            if (
                bumpedItems <= self.MOVEDROWS
                and bumpedItems
                == self.sourceModel().rowCount(self.sourceModel().index(0, 0))
            ):
                folders -= 1
            return bumpedItems + folders

        if parent.internalId() == sys.maxsize and parent.row() < self.bumpedRows():
            return 0

        idx = self.mapToSource(parent)
        defaultCount = self.sourceModel().rowCount(idx)
        if idx == self.sourceModel().index(0, 0):
            return defaultCount - self.bumpedRows()

        return defaultCount

    def mapFromSource(self, sourceIndex):
        """
        Public method to map an index to the proxy model index.

        @param sourceIndex reference to a source model index
        @type QModelIndex
        @return proxy model index
        @rtype QModelIndex
        """
        sourceRow = self.__treeModel.mapToSource(sourceIndex).row()
        return self.createIndex(sourceIndex.row(), sourceIndex.column(), sourceRow)

    def mapToSource(self, proxyIndex):
        """
        Public method to map an index to the source model index.

        @param proxyIndex reference to a proxy model index
        @type QModelIndex
        @return source model index
        @rtype QModelIndex
        """
        if not proxyIndex.isValid():
            return QModelIndex()

        if proxyIndex.internalId() == sys.maxsize:
            bumpedItems = self.bumpedRows()
            if proxyIndex.row() < bumpedItems:
                return self.__treeModel.index(
                    proxyIndex.row(), proxyIndex.column(), self.__treeModel.index(0, 0)
                )
            if (
                bumpedItems <= self.MOVEDROWS
                and bumpedItems
                == self.sourceModel().rowCount(self.__treeModel.index(0, 0))
            ):
                bumpedItems -= 1
            return self.__treeModel.index(
                proxyIndex.row() - bumpedItems, proxyIndex.column()
            )

        historyIndex = self.__treeModel.sourceModel().index(
            proxyIndex.internalId(), proxyIndex.column()
        )
        treeIndex = self.__treeModel.mapFromSource(historyIndex)
        return treeIndex

    def index(self, row, column, parent=None):
        """
        Public method to create an index.

        @param row row number for the index
        @type int
        @param column column number for the index
        @type int
        @param parent index of the parent item
        @type QModelIndex
        @return requested index
        @rtype QModelIndex
        """
        if parent is None:
            parent = QModelIndex()

        if (
            row < 0
            or column < 0
            or column >= self.columnCount(parent)
            or parent.column() > 0
        ):
            return QModelIndex()

        if not parent.isValid():
            return self.createIndex(row, column, sys.maxsize)

        treeIndexParent = self.mapToSource(parent)

        bumpedItems = 0
        if treeIndexParent == self.sourceModel().index(0, 0):
            bumpedItems = self.bumpedRows()
        treeIndex = self.__treeModel.index(row + bumpedItems, column, treeIndexParent)
        historyIndex = self.__treeModel.mapToSource(treeIndex)
        historyRow = historyIndex.row()
        if historyRow == -1:
            historyRow = treeIndex.row()
        return self.createIndex(row, column, historyRow)

    def parent(self, index):
        """
        Public method to get the parent index.

        @param index index of item to get parent
        @type QModelIndex
        @return index of parent
        @rtype QModelIndex
        """
        offset = index.internalId()
        if offset == sys.maxsize or not index.isValid():
            return QModelIndex()

        historyIndex = self.__treeModel.sourceModel().index(index.internalId(), 0)
        treeIndex = self.__treeModel.mapFromSource(historyIndex)
        treeIndexParent = treeIndex.parent()

        sourceRow = self.sourceModel().mapToSource(treeIndexParent).row()
        bumpedItems = self.bumpedRows()
        if bumpedItems <= self.MOVEDROWS and bumpedItems == self.sourceModel().rowCount(
            self.sourceModel().index(0, 0)
        ):
            bumpedItems -= 1

        return self.createIndex(
            bumpedItems + treeIndexParent.row(), treeIndexParent.column(), sourceRow
        )

    def mimeData(self, indexes):
        """
        Public method to return the mime data.

        @param indexes list of indexes
        @type QModelIndexList
        @return mime data
        @rtype QMimeData
        """
        urls = []
        for index in indexes:
            url = index.data(HistoryModel.UrlRole)
            urls.append(url)

        mdata = QMimeData()
        mdata.setUrls(urls)
        return mdata


class HistoryMostVisitedMenuModel(QSortFilterProxyModel):
    """
    Class implementing a model to show the most visited history entries.
    """

    def __init__(self, sourceModel, parent=None):
        """
        Constructor

        @param sourceModel reference to the source model
        @type QAbstractItemModel
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.setDynamicSortFilter(True)
        self.setSourceModel(sourceModel)

    def lessThan(self, left, right):
        """
        Public method used to sort the displayed items.

        @param left index of left item
        @type QModelIndex
        @param right index of right item
        @type QModelIndex
        @return true, if left is less than right
        @rtype bool
        """
        from .HistoryFilterModel import HistoryFilterModel

        frequency_L = self.sourceModel().data(left, HistoryFilterModel.FrequencyRole)
        dateTime_L = self.sourceModel().data(left, HistoryModel.DateTimeRole)
        frequency_R = self.sourceModel().data(right, HistoryFilterModel.FrequencyRole)
        dateTime_R = self.sourceModel().data(right, HistoryModel.DateTimeRole)

        # Sort results in descending frequency-derived score. If frequencies
        # are equal, sort on most recently viewed
        if frequency_R == frequency_L:
            return dateTime_R < dateTime_L

        return frequency_R < frequency_L


class HistoryMenu(EricModelMenu):
    """
    Class implementing the history menu.

    @signal openUrl(QUrl, str) emitted to open a URL in the current tab
    @signal newTab(QUrl, str) emitted to open a URL in a new tab
    @signal newBackgroundTab(QUrl, str) emitted to open a URL in a new
        background tab
    @signal newWindow(QUrl, str) emitted to open a URL in a new window
    @signal newPrivateWindow(QUrl, str) emitted to open a URL in a new
        private window
    """

    openUrl = pyqtSignal(QUrl, str)
    newTab = pyqtSignal(QUrl, str)
    newBackgroundTab = pyqtSignal(QUrl, str)
    newWindow = pyqtSignal(QUrl, str)
    newPrivateWindow = pyqtSignal(QUrl, str)

    def __init__(self, parent=None, tabWidget=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        @param tabWidget reference to the tab widget managing the browser
            tabs
        @type WebBrowserTabWidget
        """
        EricModelMenu.__init__(self, parent)

        self.__tabWidget = tabWidget
        self.__mw = parent

        self.__historyManager = None
        self.__historyMenuModel = None
        self.__initialActions = []
        self.__mostVisitedMenu = None

        self.__closedTabsMenu = QMenu(self.tr("Closed Tabs"))
        self.__closedTabsMenu.aboutToShow.connect(self.__aboutToShowClosedTabsMenu)
        self.__tabWidget.closedTabsManager().closedTabAvailable.connect(
            self.__closedTabAvailable
        )

        self.setMaxRows(7)

        self.activated.connect(self.__activated)
        self.setStatusBarTextRole(HistoryModel.UrlStringRole)

    def __activated(self, idx):
        """
        Private slot handling the activated signal.

        @param idx index of the activated item
        @type QModelIndex
        """
        if self._keyboardModifiers & Qt.KeyboardModifier.ControlModifier:
            self.newTab.emit(
                idx.data(HistoryModel.UrlRole), idx.data(HistoryModel.TitleRole)
            )
        elif self._keyboardModifiers & Qt.KeyboardModifier.ShiftModifier:
            self.newWindow.emit(
                idx.data(HistoryModel.UrlRole), idx.data(HistoryModel.TitleRole)
            )
        else:
            self.openUrl.emit(
                idx.data(HistoryModel.UrlRole), idx.data(HistoryModel.TitleRole)
            )

    def prePopulated(self):
        """
        Public method to add any actions before the tree.

        @return flag indicating if any actions were added
        @rtype bool
        """
        if self.__historyManager is None:
            self.__historyManager = WebBrowserWindow.historyManager()
            self.__historyMenuModel = HistoryMenuModel(
                self.__historyManager.historyTreeModel(), self
            )
            self.setModel(self.__historyMenuModel)

        # initial actions
        for act in self.__initialActions:
            self.addAction(act)
        if len(self.__initialActions) != 0:
            self.addSeparator()
        self.setFirstSeparator(self.__historyMenuModel.bumpedRows())

        return False

    def postPopulated(self):
        """
        Public method to add any actions after the tree.
        """
        if len(self.__historyManager.history()) > 0:
            self.addSeparator()

        if self.__mostVisitedMenu is None:
            self.__mostVisitedMenu = HistoryMostVisitedMenu(10, self)
            self.__mostVisitedMenu.setTitle(self.tr("Most Visited"))
            self.__mostVisitedMenu.openUrl.connect(self.openUrl)
            self.__mostVisitedMenu.newTab.connect(self.newTab)
            self.__mostVisitedMenu.newBackgroundTab.connect(self.newBackgroundTab)
            self.__mostVisitedMenu.newWindow.connect(self.newWindow)
            self.__mostVisitedMenu.newPrivateWindow.connect(self.newPrivateWindow)
        self.addMenu(self.__mostVisitedMenu)
        act = self.addMenu(self.__closedTabsMenu)
        act.setIcon(EricPixmapCache.getIcon("trash"))
        act.setEnabled(self.__tabWidget.canRestoreClosedTab())
        self.addSeparator()

        act = self.addAction(
            EricPixmapCache.getIcon("history"), self.tr("Show All History...")
        )
        act.triggered.connect(self.showHistoryDialog)
        act = self.addAction(
            EricPixmapCache.getIcon("historyClear"), self.tr("Clear History...")
        )
        act.triggered.connect(self.__clearHistoryDialog)

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

    def showHistoryDialog(self):
        """
        Public slot to show the history dialog.
        """
        from .HistoryDialog import HistoryDialog

        dlg = HistoryDialog(self.__mw)
        dlg.openUrl.connect(self.openUrl)
        dlg.newTab.connect(self.newTab)
        dlg.newBackgroundTab.connect(self.newBackgroundTab)
        dlg.newWindow.connect(self.newWindow)
        dlg.newPrivateWindow.connect(self.newPrivateWindow)
        dlg.show()

    def __clearHistoryDialog(self):
        """
        Private slot to clear the history.
        """
        if self.__historyManager is not None and EricMessageBox.yesNo(
            self,
            self.tr("Clear History"),
            self.tr("""Do you want to clear the history?"""),
        ):
            self.__historyManager.clear()
            self.__tabWidget.clearClosedTabsList()

    def __aboutToShowClosedTabsMenu(self):
        """
        Private slot to populate the closed tabs menu.
        """
        fm = self.__closedTabsMenu.fontMetrics()
        maxWidth = fm.horizontalAdvance("m") * 40

        self.__closedTabsMenu.clear()
        for index, tab in enumerate(
            self.__tabWidget.closedTabsManager().allClosedTabs()
        ):
            title = fm.elidedText(tab.title, Qt.TextElideMode.ElideRight, maxWidth)
            act = self.__closedTabsMenu.addAction(WebBrowserWindow.icon(tab.url), title)
            act.setData(index)
            act.triggered.connect(
                functools.partial(self.__tabWidget.restoreClosedTab, act)
            )
        self.__closedTabsMenu.addSeparator()
        self.__closedTabsMenu.addAction(
            self.tr("Restore All Closed Tabs"), self.__tabWidget.restoreAllClosedTabs
        )
        self.__closedTabsMenu.addAction(
            self.tr("Clear List"), self.__tabWidget.clearClosedTabsList
        )

    def __closedTabAvailable(self, avail):
        """
        Private slot to handle changes of the availability of closed tabs.

        @param avail flag indicating the availability of closed tabs
        @type bool
        """
        self.__closedTabsMenu.setEnabled(avail)


class HistoryMostVisitedMenu(EricModelMenu):
    """
    Class implementing the most visited history menu.

    @signal openUrl(QUrl, str) emitted to open a URL in the current tab
    @signal newTab(QUrl, str) emitted to open a URL in a new tab
    @signal newBackgroundTab(QUrl, str) emitted to open a URL in a new
        background tab
    @signal newWindow(QUrl, str) emitted to open a URL in a new window
    @signal newPrivateWindow(QUrl, str) emitted to open a URL in a new
        private window
    """

    openUrl = pyqtSignal(QUrl, str)
    newTab = pyqtSignal(QUrl, str)
    newBackgroundTab = pyqtSignal(QUrl, str)
    newWindow = pyqtSignal(QUrl, str)
    newPrivateWindow = pyqtSignal(QUrl, str)

    def __init__(self, count, parent=None):
        """
        Constructor

        @param count maximum number of entries to be shown
        @type int
        @param parent reference to the parent widget
        @type QWidget
        """
        EricModelMenu.__init__(self, parent)

        self.__historyMenuModel = None

        self.setMaxRows(count + 1)

        self.setStatusBarTextRole(HistoryModel.UrlStringRole)

    def __activated(self, idx):
        """
        Private slot handling the activated signal.

        @param idx index of the activated item
        @type QModelIndex
        """
        if self._keyboardModifiers & Qt.KeyboardModifier.ControlModifier:
            self.newTab.emit(
                idx.data(HistoryModel.UrlRole), idx.data(HistoryModel.TitleRole)
            )
        elif self._keyboardModifiers & Qt.KeyboardModifier.ShiftModifier:
            self.newWindow.emit(
                idx.data(HistoryModel.UrlRole), idx.data(HistoryModel.TitleRole)
            )
        else:
            self.openUrl.emit(
                idx.data(HistoryModel.UrlRole), idx.data(HistoryModel.TitleRole)
            )

    def prePopulated(self):
        """
        Public method to add any actions before the tree.

        @return flag indicating if any actions were added
        @rtype bool
        """
        if self.__historyMenuModel is None:
            historyManager = WebBrowserWindow.historyManager()
            self.__historyMenuModel = HistoryMostVisitedMenuModel(
                historyManager.historyFilterModel(), self
            )
            self.setModel(self.__historyMenuModel)
        self.__historyMenuModel.sort(0)

        return False
