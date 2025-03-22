# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Breakpoint model.
"""

import copy

from PyQt6.QtCore import (
    QAbstractItemModel,
    QCoreApplication,
    QModelIndex,
    Qt,
    pyqtSignal,
)


class BreakPointModel(QAbstractItemModel):
    """
    Class implementing a custom model for breakpoints.

    @signal dataAboutToBeChanged(QModelIndex, QModelIndex) emitted to indicate
        a change of the data
    """

    dataAboutToBeChanged = pyqtSignal(QModelIndex, QModelIndex)

    FilenameColumn = 0
    LineNumberColumn = 1
    ConditionColumn = 2
    TemporaryColumn = 3
    EnabledColumn = 4
    IgnoreCountColumn = 5

    Header = (
        QCoreApplication.translate("BreakPointModel", "Filename"),
        QCoreApplication.translate("BreakPointModel", "Line"),
        QCoreApplication.translate("BreakPointModel", "Condition"),
        QCoreApplication.translate("BreakPointModel", "Temporary"),
        QCoreApplication.translate("BreakPointModel", "Enabled"),
        QCoreApplication.translate("BreakPointModel", "Ignore Count"),
    )

    Alignments = (
        Qt.AlignmentFlag.AlignLeft,
        Qt.AlignmentFlag.AlignRight,
        Qt.AlignmentFlag.AlignLeft,
        Qt.AlignmentFlag.AlignHCenter,
        Qt.AlignmentFlag.AlignHCenter,
        Qt.AlignmentFlag.AlignRight,
        Qt.AlignmentFlag.AlignHCenter,
    )

    def __init__(self, project, parent=None):
        """
        Constructor

        @param project reference to the project object
        @type Project
        @param parent reference to the parent widget
        @type QObject
        """
        super().__init__(parent)

        self.__project = project

        self.breakpoints = []

    def columnCount(self, parent=None):  # noqa: U100
        """
        Public method to get the current column count.

        @param parent reference to parent index (unused)
        @type QModelIndex
        @return column count
        @rtype int
        """
        return len(BreakPointModel.Header)

    def rowCount(self, parent=None):
        """
        Public method to get the current row count.

        @param parent reference to parent index
        @type QModelIndex
        @return row count
        @rtype int
        """
        # we do not have a tree, parent should always be invalid
        if parent is None or not parent.isValid():
            return len(self.breakpoints)
        else:
            return 0

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method to get the requested data.

        @param index index of the requested data
        @type QModelIndex
        @param role role of the requested data
        @type Qt.ItemDataRole
        @return the requested data
        @rtype Any
        """
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == BreakPointModel.FilenameColumn:
                filename = self.breakpoints[index.row()][0]
                if self.__project.isOpen():
                    return self.__project.getRelativePath(filename)
                else:
                    return filename
            elif index.column() in (
                BreakPointModel.LineNumberColumn,
                BreakPointModel.ConditionColumn,
                BreakPointModel.IgnoreCountColumn,
            ):
                return self.breakpoints[index.row()][index.column()]

        if role == Qt.ItemDataRole.CheckStateRole and index.column() in (
            BreakPointModel.TemporaryColumn,
            BreakPointModel.EnabledColumn,
        ):
            if self.breakpoints[index.row()][index.column()]:
                return Qt.CheckState.Checked
            else:
                return Qt.CheckState.Unchecked

        if role == Qt.ItemDataRole.ToolTipRole and index.column() in (
            BreakPointModel.FilenameColumn,
            BreakPointModel.ConditionColumn,
        ):
            return self.breakpoints[index.row()][index.column()]

        if role == Qt.ItemDataRole.TextAlignmentRole and index.column() < len(
            BreakPointModel.Alignments
        ):
            return BreakPointModel.Alignments[index.column()].value

        return None

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):  # noqa: U100
        """
        Public method to change data in the model.

        @param index index of the changed data
        @type QModelIndex
        @param value value of the changed data
        @type  any
        @param role role of the changed data (unused)
        @type Qt.ItemDataRole
        @return flag indicating success
        @rtype bool
        """
        if (
            not index.isValid()
            or index.column() >= len(BreakPointModel.Header)
            or index.row() >= len(self.breakpoints)
        ):
            return False

        self.dataAboutToBeChanged.emit(index, index)
        self.breakpoints[index.row()][index.column()] = value
        self.dataChanged.emit(index, index)
        return True

    def flags(self, index):
        """
        Public method to get item flags.

        @param index index of the requested flags
        @type QModelIndex
        @return item flags for the given index
        @rtype Qt.ItemFlags
        """
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled

        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method to get header data.

        @param section section number of the requested header data
        @type int
        @param orientation orientation of the header
        @type Qt.Orientation
        @param role role of the requested data
        @type Qt.ItemDataRole
        @return header data
        @rtype str
        """
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            if section >= len(BreakPointModel.Header):
                return ""
            else:
                return BreakPointModel.Header[section]

        return None

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
        if (
            (parent and parent.isValid())
            or row < 0
            or row >= len(self.breakpoints)
            or column < 0
            or column >= len(BreakPointModel.Header)
        ):
            return QModelIndex()

        return self.createIndex(row, column, self.breakpoints[row])

    def parent(self, _index):
        """
        Public method to get the parent index.

        @param _index index of item to get parent (unused)
        @type QModelIndex
        @return index of parent
        @rtype QModelIndex
        """
        return QModelIndex()

    def hasChildren(self, parent=None):
        """
        Public method to check for the presence of child items.

        @param parent index of parent item
        @type QModelIndex
        @return flag indicating the presence of child items
        @rtype bool
        """
        if parent is None or not parent.isValid():
            return len(self.breakpoints) > 0
        else:
            return False

    ###########################################################################

    def addBreakPoint(self, fn, line, properties):
        """
        Public method to add a new breakpoint to the list.

        @param fn filename of the breakpoint
        @type str
        @param line line number of the breakpoint
        @type int
        @param properties properties of the breakpoint
            (tuple of condition, temporary flag, enabled flag, ignore count)
        @type tuple of (str, bool, bool, int)
        """
        bp = [fn, line] + list(properties)
        if bp not in self.breakpoints:
            # add it only, if not present already
            cnt = len(self.breakpoints)
            self.beginInsertRows(QModelIndex(), cnt, cnt)
            self.breakpoints.append(bp)
            self.endInsertRows()

    def addBreakPoints(self, breakpoints):
        """
        Public method to add multiple breakpoints to the list.

        @param breakpoints list of breakpoints with file name, line number,
            condition, temporary flag, enabled flag and ignore count each
        @type list of (str, int, str, bool, bool, int)
        """
        # eliminate redundant break points
        newBreakpoints = []
        for breakpointToAdd in breakpoints:
            if (
                breakpointToAdd not in self.breakpoints
                and breakpointToAdd not in newBreakpoints
            ):
                newBreakpoints.append(breakpointToAdd)

        if newBreakpoints:
            cnt = len(self.breakpoints)
            self.beginInsertRows(QModelIndex(), cnt, cnt + len(newBreakpoints) - 1)
            self.breakpoints += newBreakpoints
            self.endInsertRows()

    def setBreakPointByIndex(self, index, fn, line, properties):
        """
        Public method to set the values of a breakpoint given by index.

        @param index index of the breakpoint
        @type QModelIndex
        @param fn filename of the breakpoint
        @type str
        @param line line number of the breakpoint
        @type int
        @param properties properties of the breakpoint
            (tuple of condition, temporary flag, enabled flag, ignore count)
        @type tuple of (str, bool, bool, int)
        """
        if index.isValid():
            row = index.row()
            index1 = self.createIndex(row, 0, self.breakpoints[row])
            index2 = self.createIndex(
                row, len(self.breakpoints[row]) - 1, self.breakpoints[row]
            )
            self.dataAboutToBeChanged.emit(index1, index2)
            self.breakpoints[row] = [fn, line] + list(properties)
            self.dataChanged.emit(index1, index2)

    def setBreakPointEnabledByIndex(self, index, enabled):
        """
        Public method to set the enabled state of a breakpoint given by index.

        @param index index of the breakpoint
        @type QModelIndex
        @param enabled flag giving the enabled state
        @type bool
        """
        if index.isValid():
            row = index.row()
            col = 4
            index1 = self.createIndex(row, col, self.breakpoints[row])
            self.dataAboutToBeChanged.emit(index1, index1)
            self.breakpoints[row][col] = enabled
            self.dataChanged.emit(index1, index1)

    def deleteBreakPointByIndex(self, index):
        """
        Public method to set the values of a breakpoint given by index.

        @param index index of the breakpoint
        @type QModelIndex
        """
        if index.isValid():
            row = index.row()
            self.beginRemoveRows(QModelIndex(), row, row)
            del self.breakpoints[row]
            self.endRemoveRows()

    def deleteBreakPoints(self, idxList):
        """
        Public method to delete a list of breakpoints given by their indexes.

        @param idxList list of breakpoint indexes
        @type list of QModelIndex
        """
        rows = []
        for index in idxList:
            if index.isValid():
                rows.append(index.row())
        rows.sort(reverse=True)
        for row in rows:
            if row < len(self.breakpoints):
                self.beginRemoveRows(QModelIndex(), row, row)
                del self.breakpoints[row]
                self.endRemoveRows()

    def deleteAll(self):
        """
        Public method to delete all breakpoints.
        """
        if self.breakpoints:
            self.beginRemoveRows(QModelIndex(), 0, len(self.breakpoints) - 1)
            self.breakpoints = []
            self.endRemoveRows()

    def getBreakPointByIndex(self, index):
        """
        Public method to get the values of a breakpoint given by index.

        @param index index of the breakpoint
        @type QModelIndex
        @return breakpoint (list of six values (filename, line number,
            condition, temporary flag, enabled flag, ignore count))
        @rtype list of (str, int, str, bool, bool, int)
        """
        if index.isValid():
            return self.breakpoints[index.row()][:]  # return a copy
        else:
            return []

    def getAllBreakpoints(self):
        """
        Public method to get a copy of the breakpoints.

        @return list of breakpoints
        @rtype list of list of [str, int, str, bool, bool, int]
        """
        return copy.deepcopy(self.breakpoints)

    def getBreakPointIndex(self, fn, lineno):
        """
        Public method to get the index of a breakpoint given by filename and
        line number.

        @param fn filename of the breakpoint
        @type str
        @param lineno line number of the breakpoint
        @type int
        @return index
        @rtype QModelIndex
        """
        for row in range(len(self.breakpoints)):
            bp = self.breakpoints[row]
            if bp[0] == fn and bp[1] == lineno:
                return self.createIndex(row, 0, self.breakpoints[row])

        return QModelIndex()

    def isBreakPointTemporaryByIndex(self, index):
        """
        Public method to test, if a breakpoint given by its index is temporary.

        @param index index of the breakpoint to test
        @type QModelIndex
        @return flag indicating a temporary breakpoint
        @rtype bool
        """
        if index.isValid():
            return self.breakpoints[index.row()][3]
        else:
            return False
