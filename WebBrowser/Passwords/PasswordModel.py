# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a model for password management.
"""

import contextlib

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt


class PasswordModel(QAbstractTableModel):
    """
    Class implementing a model for password management.
    """

    def __init__(self, manager, parent=None):
        """
        Constructor

        @param manager reference to the password manager
        @type PasswordManager
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__manager = manager
        manager.changed.connect(self.__passwordsChanged)

        self.__headers = [self.tr("Website"), self.tr("Username"), self.tr("Password")]

        self.__showPasswords = False

    def setShowPasswords(self, on):
        """
        Public methods to show passwords.

        @param on flag indicating if passwords shall be shown
        @type bool
        """
        self.__showPasswords = on
        self.beginResetModel()
        self.endResetModel()

    def showPasswords(self):
        """
        Public method to indicate, if passwords shall be shown.

        @return flag indicating if passwords shall be shown
        @rtype bool
        """
        return self.__showPasswords

    def __passwordsChanged(self):
        """
        Private slot handling a change of the registered passwords.
        """
        self.beginResetModel()
        self.endResetModel()

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

        lastRow = row + count - 1

        self.beginRemoveRows(parent, row, lastRow)

        siteList = self.__manager.allSiteNames()
        for index in range(row, lastRow + 1):
            self.__manager.removePassword(siteList[index])

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
            return self.__manager.sitesCount()

    def columnCount(self, parent=None):  # noqa: U100
        """
        Public method to get the number of columns of the model.

        @param parent parent index (unused)
        @type QModelIndex
        @return number of columns
        @rtype int
        """
        if self.__showPasswords:
            return 3
        else:
            return 2

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
        if index.row() >= self.__manager.sitesCount() or index.row() < 0:
            return None

        site = self.__manager.allSiteNames()[index.row()]
        siteInfo = self.__manager.siteInfo(site)

        if siteInfo is None:
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return site
            elif index.column() in [1, 2]:
                return siteInfo[index.column() - 1]

        return None

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
