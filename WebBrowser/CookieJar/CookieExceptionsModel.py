# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the cookie exceptions model.
"""

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, QSize, Qt
from PyQt6.QtGui import QFont, QFontMetrics


class CookieExceptionsModel(QAbstractTableModel):
    """
    Class implementing the cookie exceptions model.
    """

    def __init__(self, cookieJar, parent=None):
        """
        Constructor

        @param cookieJar reference to the cookie jar
        @type CookieJar
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__cookieJar = cookieJar
        self.__allowedCookies = self.__cookieJar.allowedCookies()
        self.__blockedCookies = self.__cookieJar.blockedCookies()
        self.__sessionCookies = self.__cookieJar.allowForSessionCookies()

        self.__headers = [
            self.tr("Website"),
            self.tr("Status"),
        ]

    def headerData(self, section, orientation, role):
        """
        Public method to get header data from the model.

        @param section section number
        @type int
        @param orientation orientation
        @type Qt.Orientation
        @param role role of the data to retrieve
        @type Qt.ItemDataRole
        @return requested data
        @rtype Any
        """
        if role == Qt.ItemDataRole.SizeHintRole:
            fm = QFontMetrics(QFont())
            height = fm.height() + fm.height() // 3
            width = fm.horizontalAdvance(
                self.headerData(section, orientation, Qt.ItemDataRole.DisplayRole)
            )
            return QSize(width, height)

        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            try:
                return self.__headers[section]
            except IndexError:
                return None

        return QAbstractTableModel.headerData(self, section, orientation, role)

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
        if index.row() < 0 or index.row() >= self.rowCount():
            return None

        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            row = index.row()
            if row < len(self.__allowedCookies):
                if index.column() == 0:
                    return self.__allowedCookies[row]
                elif index.column() == 1:
                    return self.tr("Allow")
                else:
                    return None

            row -= len(self.__allowedCookies)
            if row < len(self.__blockedCookies):
                if index.column() == 0:
                    return self.__blockedCookies[row]
                elif index.column() == 1:
                    return self.tr("Block")
                else:
                    return None

            row -= len(self.__blockedCookies)
            if row < len(self.__sessionCookies):
                if index.column() == 0:
                    return self.__sessionCookies[row]
                elif index.column() == 1:
                    return self.tr("Allow For Session")
                else:
                    return None

            return None

        return None

    def columnCount(self, parent=None):
        """
        Public method to get the number of columns of the model.

        @param parent parent index
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
        Public method to get the number of rows of the model.

        @param parent parent index
        @type QModelIndex
        @return number of rows
        @rtype int
        """
        if parent is None:
            parent = QModelIndex()

        if parent.isValid() or self.__cookieJar is None:
            return 0
        else:
            return (
                len(self.__allowedCookies)
                + len(self.__blockedCookies)
                + len(self.__sessionCookies)
            )

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

        if parent.isValid() or self.__cookieJar is None:
            return False

        lastRow = row + count - 1
        self.beginRemoveRows(parent, row, lastRow)
        for i in range(lastRow, row - 1, -1):
            rowToRemove = i

            if rowToRemove < len(self.__allowedCookies):
                del self.__allowedCookies[rowToRemove]
                continue

            rowToRemove -= len(self.__allowedCookies)
            if rowToRemove < len(self.__blockedCookies):
                del self.__blockedCookies[rowToRemove]
                continue

            rowToRemove -= len(self.__blockedCookies)
            if rowToRemove < len(self.__sessionCookies):
                del self.__sessionCookies[rowToRemove]
                continue

        self.__cookieJar.setAllowedCookies(self.__allowedCookies)
        self.__cookieJar.setBlockedCookies(self.__blockedCookies)
        self.__cookieJar.setAllowForSessionCookies(self.__sessionCookies)
        self.endRemoveRows()

        return True

    def addRule(self, host, rule):
        """
        Public method to add an exception rule.

        @param host name of the host to add a rule for
        @type str
        @param rule type of rule to add
        @type CookieExceptionRuleType
        """
        from .CookieJar import CookieExceptionRuleType

        if not host:
            return

        if rule == CookieExceptionRuleType.Allow:
            self.__addHost(
                host,
                self.__allowedCookies,
                self.__blockedCookies,
                self.__sessionCookies,
            )
            return
        elif rule == CookieExceptionRuleType.Block:
            self.__addHost(
                host,
                self.__blockedCookies,
                self.__allowedCookies,
                self.__sessionCookies,
            )
            return
        elif rule == CookieExceptionRuleType.AllowForSession:
            self.__addHost(
                host,
                self.__sessionCookies,
                self.__allowedCookies,
                self.__blockedCookies,
            )
            return

    def __addHost(self, host, addList, removeList1, removeList2):
        """
        Private method to add a host to an exception list.

        @param host name of the host to add
        @type str
        @param addList reference to the list to add it to
        @type list of str
        @param removeList1 reference to first list to remove it from
        @type list of str
        @param removeList2 reference to second list to remove it from
        @type list of str
        """
        if host not in addList:
            addList.append(host)
            if host in removeList1:
                removeList1.remove(host)
            if host in removeList2:
                removeList2.remove(host)

        # Avoid to have similar rules (with or without leading dot)
        # e.g. python-projects.org and .python-projects.org
        otherRule = host[1:] if host.startswith(".") else "." + host
        if otherRule in addList:
            addList.remove(otherRule)
        if otherRule in removeList1:
            removeList1.remove(otherRule)
        if otherRule in removeList2:
            removeList2.remove(otherRule)

        self.__cookieJar.setAllowedCookies(self.__allowedCookies)
        self.__cookieJar.setBlockedCookies(self.__blockedCookies)
        self.__cookieJar.setAllowForSessionCookies(self.__sessionCookies)

        self.beginResetModel()
        self.endResetModel()
