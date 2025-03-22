# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a model for search engines.
"""

import contextlib
import re

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt, QUrl
from PyQt6.QtGui import QIcon, QPixmap

from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow


class OpenSearchEngineModel(QAbstractTableModel):
    """
    Class implementing a model for search engines.
    """

    def __init__(self, manager, parent=None):
        """
        Constructor

        @param manager reference to the search engine manager
        @type OpenSearchManager
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__manager = manager
        manager.changed.connect(self.__enginesChanged)

        self.__headers = [
            self.tr("Name"),
            self.tr("Keywords"),
        ]

    def removeRows(self, row, count, parent=None):
        """
        Public method to remove entries from the model.

        @param row start row
        @type int
        @param count number of rows to remove
        @type int
        @param parent parent index
        @type QModelIndex
        @return flag indicating success
        @rtype bool
        """
        if parent is None:
            parent = QModelIndex()

        if parent.isValid():
            return False

        if count <= 0:
            return False

        if self.rowCount() <= 1:
            return False

        lastRow = row + count - 1

        self.beginRemoveRows(parent, row, lastRow)

        nameList = self.__manager.allEnginesNames()
        for index in range(row, lastRow + 1):
            self.__manager.removeEngine(nameList[index])

        return True

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
            return self.__manager.enginesCount()

    def columnCount(self, parent=None):  # noqa: U100
        """
        Public method to get the number of columns of the model.

        @param parent parent index (unused)
        @type QModelIndex
        @return number of columns
        @rtype int
        """
        return 2

    def flags(self, index):
        """
        Public method to get flags for a model cell.

        @param index index of the model cell
        @type QModelIndex
        @return flags
        @rtype Qt.ItemFlags
        """
        if index.column() == 1:
            return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEditable
            )
        else:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

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
        if index.row() >= self.__manager.enginesCount() or index.row() < 0:
            return None

        engine = self.__manager.engine(self.__manager.allEnginesNames()[index.row()])

        if engine is None:
            return None

        if index.column() == 0:
            if role == Qt.ItemDataRole.DisplayRole:
                return engine.name()

            elif role == Qt.ItemDataRole.DecorationRole:
                image = engine.image()
                if image.isNull():
                    icon = WebBrowserWindow.icon(QUrl(engine.imageUrl()))
                else:
                    icon = QIcon(QPixmap.fromImage(image))
                return icon

            elif role == Qt.ItemDataRole.ToolTipRole:
                description = self.tr("<strong>Description:</strong> {0}").format(
                    engine.description()
                )
                if engine.providesSuggestions():
                    description += "<br/>"
                    description += self.tr(
                        "<strong>Provides contextual suggestions</strong>"
                    )

                return description
        elif index.column() == 1:
            if role in [Qt.ItemDataRole.EditRole, Qt.ItemDataRole.DisplayRole]:
                return ",".join(self.__manager.keywordsForEngine(engine))
            elif role == Qt.ItemDataRole.ToolTipRole:
                return self.tr(
                    "Comma-separated list of keywords that may"
                    " be entered in the location bar followed by search terms"
                    " to search with this engine"
                )

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        """
        Public method to set the data of a model cell.

        @param index index of the model cell
        @type QModelIndex
        @param value value to be set
        @type Any
        @param role role of the data
        @type int
        @return flag indicating success
        @rtype bool
        """
        if not index.isValid() or index.column() != 1:
            return False

        if index.row() >= self.rowCount() or index.row() < 0:
            return False

        if role != Qt.ItemDataRole.EditRole:
            return False

        engineName = self.__manager.allEnginesNames()[index.row()]
        keywords = re.split("[ ,]+", value)
        self.__manager.setKeywordsForEngine(self.__manager.engine(engineName), keywords)

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

        return None

    def __enginesChanged(self):
        """
        Private slot handling a change of the registered engines.
        """
        self.beginResetModel()
        self.endResetModel()
