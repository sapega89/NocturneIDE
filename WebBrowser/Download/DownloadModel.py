# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the download model.
"""

from PyQt6.QtCore import QAbstractListModel, QMimeData, QModelIndex, Qt, QUrl


class DownloadModel(QAbstractListModel):
    """
    Class implementing the download model.
    """

    def __init__(self, manager, parent=None):
        """
        Constructor

        @param manager reference to the download manager
        @type DownloadManager
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__manager = manager

    def data(self, index, role):
        """
        Public method to get data from the model.

        @param index index to get data for
        @type QModelIndex
        @param role role of the data to retrieve
        @type int
        @return requested data
        @rtype Any
        """
        if index.row() < 0 or index.row() >= self.rowCount(index.parent()):
            return None

        if (
            role == Qt.ItemDataRole.ToolTipRole
            and self.__manager.downloads()[index.row()].downloadedSuccessfully()
        ):
            return self.__manager.downloads()[index.row()].getInfoData()

        return None

    def rowCount(self, parent=None):
        """
        Public method to get the number of rows of the model.

        @param parent parent index
        @type QModelIndex
        @return number of rows
        @rtype int
        """
        if parent is None:
            parent = QModelIndex()

        if parent.isValid():
            return 0
        else:
            return self.__manager.downloadsCount()

    def removeRows(self, row, count, parent=None):
        """
        Public method to remove downloads from the model.

        @param row row of the first download to remove
        @type int
        @param count number of downloads to remove
        @type int
        @param parent index of the parent download node
        @type QModelIndex
        @return flag indicating successful removal
        @rtype bool
        """
        if parent is None:
            parent = QModelIndex()

        if parent.isValid():
            return False

        if row < 0 or count <= 0 or row + count > self.rowCount(parent):
            return False

        lastRow = row + count - 1
        for i in range(lastRow, row - 1, -1):
            if not self.__manager.downloads()[i].downloading():
                self.beginRemoveRows(parent, i, i)
                del self.__manager.downloads()[i]
                self.endRemoveRows()
        self.__manager.changeOccurred()
        return True

    def flags(self, index):
        """
        Public method to get flags for an item.

        @param index index of the node cell
        @type QModelIndex
        @return flags
        @rtype Qt.ItemFlags
        """
        if index.row() < 0 or index.row() >= self.rowCount(index.parent()):
            return Qt.ItemFlag.NoItemFlags

        defaultFlags = QAbstractListModel.flags(self, index)

        itm = self.__manager.downloads()[index.row()]
        if itm.downloadedSuccessfully():
            return defaultFlags | Qt.ItemFlag.ItemIsDragEnabled

        return defaultFlags

    def mimeData(self, indexes):
        """
        Public method to return the mime data.

        @param indexes list of indexes
        @type QModelIndexList
        @return mime data
        @rtype QMimeData
        """
        mimeData = QMimeData()
        urls = []
        for index in indexes:
            if index.isValid():
                itm = self.__manager.downloads()[index.row()]
                urls.append(QUrl.fromLocalFile(itm.absoluteFilePath()))
        mimeData.setUrls(urls)
        return mimeData
