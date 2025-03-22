# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the browser sort filter proxy model.
"""

import os

from PyQt6.QtCore import QModelIndex, QSortFilterProxyModel, pyqtSlot

from eric7 import Preferences

from . import BrowserModel


class BrowserSortFilterProxyModel(QSortFilterProxyModel):
    """
    Class implementing the browser sort filter proxy model.
    """

    def __init__(self, parent=None, remoteServer=None):
        """
        Constructor

        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        @param remoteServer reference to the 'eric-ide' server interface object
        @type EricServerInterface
        """
        super().__init__(parent)

        # These are needed in ProjectBrowserSortFilterProxyModel as well.
        self.hideNonPublic = Preferences.getUI("BrowsersHideNonPublic")
        self.hideHiddenFiles = not Preferences.getUI("BrowsersListHiddenFiles")

        # These are just needed by the basic filter.
        self.__filterRemoteEntries = Preferences.getUI("BrowsersFilterRemoteEntries")
        self.__remoteHost = ""
        self.__remoteServer = remoteServer
        if self.__remoteServer:
            self.__remoteServer.connectionStateChanged.connect(
                self.__remoteServerConnectionStateChanged
            )

    def sort(self, column, order):
        """
        Public method to sort the items.

        @param column column number to sort on
        @type int
        @param order sort order for the sort
        @type Qt.SortOrder
        """
        self.__sortColumn = column
        self.__sortOrder = order
        super().sort(column, order)

    def lessThan(self, left, right):
        """
        Public method used to sort the displayed items.

        It implements a special sorting function that takes into account,
        if folders should be shown first, and that __init__ is always the first
        method of a class.

        @param left index of left item
        @type QModelIndex
        @param right index of right item
        @type QModelIndex
        @return true, if left is less than right
        @rtype bool
        """
        le = left.model() and left.model().item(left) or None
        ri = right.model() and right.model().item(right) or None

        if le and ri:
            return le.lessThan(ri, self.__sortColumn, self.__sortOrder)

        return False

    def item(self, index):
        """
        Public method to get a reference to an item.

        @param index index of the data to retrieve
        @type QModelIndex
        @return requested item reference
        @rtype BrowserItem
        """
        if not index.isValid():
            return None

        sindex = self.mapToSource(index)
        return self.sourceModel().item(sindex)

    def hasChildren(self, parent=None):
        """
        Public method to check for the presence of child items.

        We always return True for normal items in order to do lazy
        population of the tree.

        @param parent index of parent item
        @type QModelIndex
        @return flag indicating the presence of child items
        @rtype bool
        """
        if parent is None:
            parent = QModelIndex()
        sindex = self.mapToSource(parent)
        return self.sourceModel().hasChildren(sindex)

    def filterAcceptsRow(self, source_row, source_parent):
        """
        Public method to filter rows.

        It implements a filter to suppress the display of hidden files and
        directories (i.e. those starting with a '.') and the display of non
        public classes, methods and attributes. These filters are independent
        of each other.

        @param source_row row number (in the source model) of item
        @type int
        @param source_parent index of parent item (in the source model)
            of item
        @type QModelIndex
        @return flag indicating, if the item should be shown
        @rtype bool
        """
        sindex = self.sourceModel().index(source_row, 0, source_parent)
        itm = self.sourceModel().item(sindex)

        if self.hideNonPublic or self.hideHiddenFiles:
            if self.hideHiddenFiles:
                if itm.type() == BrowserModel.BrowserItemType.Directory:
                    return not os.path.basename(itm.dirName()).startswith(".")
                elif itm.type() == BrowserModel.BrowserItemType.File:
                    return not os.path.basename(itm.fileName()).startswith(".")
            elif self.hideNonPublic:
                return itm.isPublic()

        if self.__filterRemoteEntries and itm.isRemote():
            return itm.getRemoteInfo() == self.__remoteHost

        return True

    def preferencesChanged(self):
        """
        Public slot called to handle a change of the preferences settings.
        """
        changed = False

        hideNonPublic = Preferences.getUI("BrowsersHideNonPublic")
        if self.hideNonPublic != hideNonPublic:
            self.hideNonPublic = hideNonPublic
            changed = True

        filterRemoteEntries = Preferences.getUI("BrowsersFilterRemoteEntries")
        if self.__filterRemoteEntries != filterRemoteEntries:
            self.__filterRemoteEntries = filterRemoteEntries
            changed = True

        if changed:
            self.invalidateFilter()

    def setShowHiddenFiles(self, show):
        """
        Public method to set, whether hidden files should be shown.

        @param show flag indicating if hidden files (i.e. those starting
            with '.' shall be shown
        @type bool
        """
        hideHiddenFiles = not show
        if self.hideHiddenFiles != hideHiddenFiles:
            self.hideHiddenFiles = hideHiddenFiles
            self.invalidateFilter()

    @pyqtSlot(bool)
    def __remoteServerConnectionStateChanged(self, connected):
        """
        Private slot to handle a change of the connection state to an 'eric-ide' server.

        @param connected connection state
        @type bool
        """
        self.__remoteHost = self.__remoteServer.getHost() if connected else ""
        self.invalidateFilter()
