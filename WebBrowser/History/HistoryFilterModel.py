# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the history filter model.
"""

from PyQt6.QtCore import QAbstractProxyModel, QDateTime, QModelIndex, Qt, pyqtSlot

from .HistoryModel import HistoryModel


class HistoryData:
    """
    Class storing some history data.
    """

    def __init__(self, offset, frequency=0):
        """
        Constructor

        @param offset tail offset
        @type int
        @param frequency frequency
        @type int
        """
        self.tailOffset = offset
        self.frequency = frequency

    def __eq__(self, other):
        """
        Special method implementing equality.

        @param other reference to the object to check against
        @type HistoryData
        @return flag indicating equality
        @rtype bool
        """
        return self.tailOffset == other.tailOffset and (
            self.frequency == -1
            or other.frequency == -1
            or self.frequency == other.frequency
        )

    def __lt__(self, other):
        """
        Special method determining less relation.

        Note: Like the actual history entries the index mapping is sorted in
        reverse order by offset

        @param other reference to the history data object to compare against
        @type HistoryEntry
        @return flag indicating less
        @rtype bool
        """
        return self.tailOffset > other.tailOffset


class HistoryFilterModel(QAbstractProxyModel):
    """
    Class implementing the history filter model.
    """

    FrequencyRole = HistoryModel.MaxRole + 1
    MaxRole = FrequencyRole

    def __init__(self, sourceModel, parent=None):
        """
        Constructor

        @param sourceModel reference to the source model
        @type QAbstractItemModel
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__loaded = False
        self.__filteredRows = []
        self.__historyDict = {}
        self.__scaleTime = QDateTime()

        self.setSourceModel(sourceModel)

    def historyContains(self, url):
        """
        Public method to check the history for an entry.

        @param url URL to check for
        @type str
        @return flag indicating success
        @rtype bool
        """
        self.__load()
        return url in self.__historyDict

    def historyLocation(self, url):
        """
        Public method to get the row number of an entry in the source model.

        @param url URL to check for
        @type str
        @return row number in the source model
        @rtype int
        """
        self.__load()
        if url not in self.__historyDict:
            return 0

        return self.sourceModel().rowCount() - self.__historyDict[url]

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
        if role == self.FrequencyRole and index.isValid():
            return self.__filteredRows[index.row()].frequency

        return QAbstractProxyModel.data(self, index, role)

    def setSourceModel(self, sourceModel):
        """
        Public method to set the source model.

        @param sourceModel reference to the source model
        @type QAbstractItemModel
        """
        if self.sourceModel() is not None:
            self.sourceModel().modelReset.disconnect(self.__sourceReset)
            self.sourceModel().dataChanged.disconnect(self.__sourceDataChanged)
            self.sourceModel().rowsInserted.disconnect(self.__sourceRowsInserted)
            self.sourceModel().rowsRemoved.disconnect(self.__sourceRowsRemoved)

        super().setSourceModel(sourceModel)

        if self.sourceModel() is not None:
            self.__loaded = False
            self.sourceModel().modelReset.connect(self.__sourceReset)
            self.sourceModel().dataChanged.connect(self.__sourceDataChanged)
            self.sourceModel().rowsInserted.connect(self.__sourceRowsInserted)
            self.sourceModel().rowsRemoved.connect(self.__sourceRowsRemoved)

    def __sourceDataChanged(self, topLeft, bottomRight):
        """
        Private slot to handle the change of data of the source model.

        @param topLeft index of top left data element
        @type QModelIndex
        @param bottomRight index of bottom right data element
        @type QModelIndex
        """
        self.dataChanged.emit(
            self.mapFromSource(topLeft), self.mapFromSource(bottomRight)
        )

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
        return self.sourceModel().headerData(section, orientation, role)

    def recalculateFrequencies(self):
        """
        Public method to recalculate the frequencies.
        """
        self.__sourceReset()

    def __sourceReset(self):
        """
        Private slot to handle a reset of the source model.
        """
        self.beginResetModel()
        self.__loaded = False
        self.endResetModel()

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

        self.__load()
        if parent.isValid():
            return 0
        return len(self.__historyDict)

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

        return self.sourceModel().columnCount(self.mapToSource(parent))

    def mapToSource(self, proxyIndex):
        """
        Public method to map an index to the source model index.

        @param proxyIndex reference to a proxy model index
        @type QModelIndex
        @return source model index
        @rtype QModelIndex
        """
        self.__load()
        sourceRow = self.sourceModel().rowCount() - proxyIndex.internalId()
        return self.sourceModel().index(sourceRow, proxyIndex.column())

    def mapFromSource(self, sourceIndex):
        """
        Public method to map an index to the proxy model index.

        @param sourceIndex reference to a source model index
        @type QModelIndex
        @return proxy model index
        @rtype QModelIndex
        """
        self.__load()
        url = sourceIndex.data(HistoryModel.UrlStringRole)
        if url not in self.__historyDict:
            return QModelIndex()

        sourceOffset = self.sourceModel().rowCount() - sourceIndex.row()

        try:
            row = self.__filteredRows.index(HistoryData(sourceOffset, -1))
        except ValueError:
            return QModelIndex()

        return self.createIndex(row, sourceIndex.column(), sourceOffset)

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

        self.__load()
        if (
            row < 0
            or row >= self.rowCount(parent)
            or column < 0
            or column >= self.columnCount(parent)
        ):
            return QModelIndex()

        return self.createIndex(row, column, self.__filteredRows[row].tailOffset)

    def parent(self, _index):
        """
        Public method to get the parent index.

        @param _index index of item to get parent (unused)
        @type QModelIndex
        @return index of parent
        @rtype QModelIndex
        """
        return QModelIndex()

    def __load(self):
        """
        Private method to load the model data.
        """
        if self.__loaded:
            return

        self.__filteredRows = []
        self.__historyDict = {}
        self.__scaleTime = QDateTime.currentDateTime()

        for sourceRow in range(self.sourceModel().rowCount()):
            idx = self.sourceModel().index(sourceRow, 0)
            url = idx.data(HistoryModel.UrlStringRole)
            if url not in self.__historyDict:
                sourceOffset = self.sourceModel().rowCount() - sourceRow
                self.__filteredRows.append(
                    HistoryData(sourceOffset, self.__frequencyScore(idx))
                )
                self.__historyDict[url] = sourceOffset
            else:
                # the url is known already, so just update the frequency score
                row = self.__filteredRows.index(
                    HistoryData(self.__historyDict[url], -1)
                )
                self.__filteredRows[row].frequency += self.__frequencyScore(idx)

        self.__loaded = True

    @pyqtSlot(QModelIndex, int, int)
    def __sourceRowsInserted(self, parent, start, end):
        """
        Private slot to handle the insertion of data in the source model.

        @param parent reference to the parent index
        @type QModelIndex
        @param start start row
        @type int
        @param end end row
        @type int
        """
        if start == end and start == 0:
            if not self.__loaded:
                return

            idx = self.sourceModel().index(start, 0, parent)
            url = idx.data(HistoryModel.UrlStringRole)
            currentFrequency = 0
            if url in self.__historyDict:
                row = self.__filteredRows.index(
                    HistoryData(self.__historyDict[url], -1)
                )
                currentFrequency = self.__filteredRows[row].frequency
                self.beginRemoveRows(QModelIndex(), row, row)
                del self.__filteredRows[row]
                del self.__historyDict[url]
                self.endRemoveRows()

            self.beginInsertRows(QModelIndex(), 0, 0)
            self.__filteredRows.insert(
                0,
                HistoryData(
                    self.sourceModel().rowCount(),
                    self.__frequencyScore(idx) + currentFrequency,
                ),
            )
            self.__historyDict[url] = self.sourceModel().rowCount()
            self.endInsertRows()

    @pyqtSlot(QModelIndex, int, int)
    def __sourceRowsRemoved(self, parent, start, end):
        """
        Private slot to handle the removal of data in the source model.

        @param parent reference to the parent index
        @type QModelIndex
        @param start start row
        @type int
        @param end end row
        @type int
        """
        self.__sourceReset()

    def removeRows(self, row, count, parent=None):
        """
        Public method to remove entries from the model.

        @param row row of the first entry to remove
        @type int
        @param count number of entries to remove
        @type int
        @param parent index of the parent entry
        @type QModelIndex
        @return flag indicating successful removal
        @rtype bool
        """
        if parent is None:
            parent = QModelIndex()

        if (
            row < 0
            or count <= 0
            or row + count > self.rowCount(parent)
            or parent.isValid()
        ):
            return False

        lastRow = row + count - 1
        self.sourceModel().rowsRemoved.disconnect(self.__sourceRowsRemoved)
        self.beginRemoveRows(parent, row, lastRow)
        oldCount = self.rowCount()
        start = self.sourceModel().rowCount() - self.__filteredRows[row].tailOffset
        end = self.sourceModel().rowCount() - self.__filteredRows[lastRow].tailOffset
        self.sourceModel().removeRows(start, end - start + 1)
        self.endRemoveRows()
        self.sourceModel().rowsRemoved.connect(self.__sourceRowsRemoved)
        self.__loaded = False
        if oldCount - count != self.rowCount():
            self.beginResetModel()
            self.endResetModel()
        return True

    def __frequencyScore(self, sourceIndex):
        """
        Private method to calculate the frequency score.

        @param sourceIndex index of the source model
        @type QModelIndex
        @return frequency score
        @rtype int
        """
        loadTime = self.sourceModel().data(sourceIndex, HistoryModel.DateTimeRole)
        days = loadTime.daysTo(self.__scaleTime)

        if days <= 1:
            return 100
        elif days < 8:  # within the last week
            return 90
        elif days < 15:  # within the last two weeks
            return 70
        elif days < 31:  # within the last month
            return 50
        elif days < 91:  # within the last 3 months
            return 30
        else:
            return 10
