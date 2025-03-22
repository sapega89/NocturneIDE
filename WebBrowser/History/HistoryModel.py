# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the history model.
"""

import contextlib

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, QUrl

from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow


class HistoryModel(QAbstractTableModel):
    """
    Class implementing the history model.
    """

    DateRole = Qt.ItemDataRole.UserRole + 1
    DateTimeRole = Qt.ItemDataRole.UserRole + 2
    UrlRole = Qt.ItemDataRole.UserRole + 3
    UrlStringRole = Qt.ItemDataRole.UserRole + 4
    TitleRole = Qt.ItemDataRole.UserRole + 5
    VisitCountRole = Qt.ItemDataRole.UserRole + 6
    MaxRole = VisitCountRole

    def __init__(self, historyManager, parent=None):
        """
        Constructor

        @param historyManager reference to the history manager object
        @type HistoryManager
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__historyManager = historyManager

        self.__headers = [self.tr("Title"), self.tr("Address"), self.tr("Visit Count")]

        self.__historyManager.historyReset.connect(self.historyReset)
        self.__historyManager.entryRemoved.connect(self.historyReset)
        self.__historyManager.entryAdded.connect(self.entryAdded)
        self.__historyManager.entryUpdated.connect(self.entryUpdated)

    def historyReset(self):
        """
        Public slot to reset the model.
        """
        self.beginResetModel()
        self.endResetModel()

    def entryAdded(self):
        """
        Public slot to handle the addition of a history entry.
        """
        self.beginInsertRows(QModelIndex(), 0, 0)
        self.endInsertRows()

    def entryUpdated(self, row):
        """
        Public slot to handle the update of a history entry.

        @param row row number of the updated entry
        @type int
        """
        idx = self.index(row, 0)
        self.dataChanged.emit(idx, idx)

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
        return QAbstractTableModel.headerData(self, section, orientation, role)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method to get data from the model.

        @param index index of history entry to get data for
        @type QModelIndex
        @param role data role
        @type int
        @return history entry data
        @rtype Any
        """
        lst = self.__historyManager.history()
        if index.row() < 0 or index.row() > len(lst):
            return None

        itm = lst[index.row()]
        if role == self.DateTimeRole:
            return itm.dateTime
        elif role == self.DateRole:
            return itm.dateTime.date()
        elif role == self.UrlRole:
            return QUrl(itm.url)
        elif role == self.UrlStringRole:
            return itm.url
        elif role == self.TitleRole:
            return itm.userTitle()
        elif role == self.VisitCountRole:
            return itm.visitCount
        elif role in [Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole]:
            if index.column() == 0:
                return itm.userTitle()
            elif index.column() == 1:
                return itm.url
            elif index.column() == 2:
                return itm.visitCount
        elif role == Qt.ItemDataRole.DecorationRole and index.column() == 0:
            return WebBrowserWindow.icon(QUrl(itm.url))

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

        if parent.isValid():
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

        if parent.isValid():
            return 0
        else:
            return len(self.__historyManager.history())

    def removeRows(self, row, count, parent=None):
        """
        Public method to remove history entries from the model.

        @param row row of the first history entry to remove
        @type int
        @param count number of history entries to remove
        @type int
        @param parent index of the parent entry
        @type QModelIndex
        @return flag indicating successful removal
        @rtype bool
        """
        if parent is None:
            parent = QModelIndex()

        if parent.isValid():
            return False

        lastRow = row + count - 1
        self.beginRemoveRows(parent, row, lastRow)
        lst = self.__historyManager.history()[:]
        for index in range(lastRow, row - 1, -1):
            del lst[index]
        self.__historyManager.historyReset.disconnect(self.historyReset)
        self.__historyManager.setHistory(lst)
        self.__historyManager.historyReset.connect(self.historyReset)
        self.endRemoveRows()
        return True
