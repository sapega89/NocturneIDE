# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a tree view and associated model to show the test result
data.
"""

import contextlib
import copy
import locale

from collections import Counter
from operator import attrgetter

from PyQt6.QtCore import (
    QAbstractItemModel,
    QCoreApplication,
    QModelIndex,
    QPoint,
    QSortFilterProxyModel,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import QMenu, QTreeView

from eric7 import Preferences
from eric7.EricWidgets.EricApplication import ericApp

from .Interfaces.TestExecutorBase import TestResultCategory

TopLevelId = 2**32 - 1


class TestResultsModel(QAbstractItemModel):
    """
    Class implementing the item model containing the test data.

    @signal summary(str) emitted whenever the model data changes. The element
        is a summary of the test results of the model.
    """

    summary = pyqtSignal(str)

    Headers = [
        QCoreApplication.translate("TestResultsModel", "Status"),
        QCoreApplication.translate("TestResultsModel", "Name"),
        QCoreApplication.translate("TestResultsModel", "Message"),
        QCoreApplication.translate("TestResultsModel", "Duration [ms]"),
    ]

    StatusColumn = 0
    NameColumn = 1
    MessageColumn = 2
    DurationColumn = 3

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

        if ericApp().usesDarkPalette():
            self.__backgroundColors = {
                TestResultCategory.RUNNING: None,
                TestResultCategory.FAIL: QBrush(QColor("#880000")),
                TestResultCategory.OK: QBrush(QColor("#005500")),
                TestResultCategory.SKIP: QBrush(QColor("#3f3f3f")),
                TestResultCategory.PENDING: QBrush(QColor("#004768")),
            }
        else:
            self.__backgroundColors = {
                TestResultCategory.RUNNING: None,
                TestResultCategory.FAIL: QBrush(QColor("#ff8080")),
                TestResultCategory.OK: QBrush(QColor("#c1ffba")),
                TestResultCategory.SKIP: QBrush(QColor("#c5c5c5")),
                TestResultCategory.PENDING: QBrush(QColor("#6fbaff")),
            }

        self.__testResults = []
        self.__testResultsById = {}

    def index(self, row, column, parent=None):
        """
        Public method to generate an index for the given row and column to
        identify the item.

        @param row row for the index
        @type int
        @param column column for the index
        @type int
        @param parent index of the parent item (defaults to None)
        @type QModelIndex (optional)
        @return index for the item
        @rtype QModelIndex
        """
        if parent is None:
            parent = QModelIndex()

        if not self.hasIndex(row, column, parent):  # check bounds etc.
            return QModelIndex()

        if not parent.isValid():
            # top level item
            return self.createIndex(row, column, TopLevelId)
        else:
            testResultIndex = parent.row()
            return self.createIndex(row, column, testResultIndex)

    def data(self, index, role):
        """
        Public method to get the data for the various columns and roles.

        @param index index of the data to be returned
        @type QModelIndex
        @param role role designating the data to return
        @type Qt.ItemDataRole
        @return requested data item
        @rtype Any
        """
        if not index.isValid():
            return None

        row = index.row()
        column = index.column()
        idx = index.internalId()

        if role == Qt.ItemDataRole.DisplayRole:
            if idx != TopLevelId:
                if bool(self.__testResults[idx].extra):
                    return self.__testResults[idx].extra[index.row()]
                else:
                    return None
            elif column == TestResultsModel.StatusColumn:
                return self.__testResults[row].status
            elif column == TestResultsModel.NameColumn:
                return self.__testResults[row].name
            elif column == TestResultsModel.MessageColumn:
                return self.__testResults[row].message
            elif column == TestResultsModel.DurationColumn:
                duration = self.__testResults[row].duration
                return (
                    ""
                    if duration is None
                    else locale.format_string("%.2f", duration, grouping=True)
                )
        elif (
            role == Qt.ItemDataRole.ToolTipRole
            and idx == TopLevelId
            and column == TestResultsModel.NameColumn
        ):
            return self.__testResults[row].name
        elif role == Qt.ItemDataRole.FontRole and idx != TopLevelId:
            return Preferences.getEditorOtherFonts("MonospacedFont")
        elif role == Qt.ItemDataRole.BackgroundRole and idx == TopLevelId:
            testResult = self.__testResults[row]
            with contextlib.suppress(KeyError):
                return self.__backgroundColors[testResult.category]
        elif (
            role == Qt.ItemDataRole.TextAlignmentRole
            and idx == TopLevelId
            and column == TestResultsModel.DurationColumn
        ):
            return Qt.AlignmentFlag.AlignRight.value
        elif role == Qt.ItemDataRole.UserRole and idx == TopLevelId:
            testresult = self.__testResults[row]
            return (testresult.filename, testresult.lineno)

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method to get the header string for the various sections.

        @param section section number
        @type int
        @param orientation orientation of the header
        @type Qt.Orientation
        @param role data role (defaults to Qt.ItemDataRole.DisplayRole)
        @type Qt.ItemDataRole (optional)
        @return header string of the section
        @rtype str
        """
        if (
            orientation == Qt.Orientation.Horizontal
            and role == Qt.ItemDataRole.DisplayRole
        ):
            return TestResultsModel.Headers[section]
        else:
            return None

    def parent(self, index):
        """
        Public method to get the parent of the item pointed to by index.

        @param index index of the item
        @type QModelIndex
        @return index of the parent item
        @rtype QModelIndex
        """
        if not index.isValid():
            return QModelIndex()

        idx = index.internalId()
        if idx == TopLevelId:
            return QModelIndex()
        else:
            return self.index(idx, 0)

    def rowCount(self, parent=None):
        """
        Public method to get the number of row for a given parent index.

        @param parent index of the parent item (defaults to None)
        @type QModelIndex (optional)
        @return number of rows
        @rtype int
        """
        if parent is None or not parent.isValid():
            return len(self.__testResults)

        if (
            parent.internalId() == TopLevelId
            and parent.column() == 0
            and self.__testResults[parent.row()].extra is not None
        ):
            return len(self.__testResults[parent.row()].extra)

        return 0

    def columnCount(self, parent=None):
        """
        Public method to get the number of columns.

        @param parent index of the parent item (defaults to None)
        @type QModelIndex (optional)
        @return number of columns
        @rtype int
        """
        if parent is None or not parent.isValid():
            return len(TestResultsModel.Headers)
        else:
            return 1

    def clear(self):
        """
        Public method to clear the model data.
        """
        self.beginResetModel()
        self.__testResults.clear()
        self.__testResultsById.clear()
        self.endResetModel()

        self.summary.emit("")

    def sort(self, column, order):
        """
        Public method to sort the model data by column in order.

        @param column sort column number
        @type int
        @param order sort order
        @type Qt.SortOrder
        """  # __IGNORE_WARNING_D234r__

        def durationKey(result):
            """
            Function to generate a key for duration sorting

            @param result result object
            @type TestResult
            @return sort key
            @rtype float
            """
            return result.duration or -1.0

        self.beginResetModel()
        reverse = order == Qt.SortOrder.DescendingOrder
        if column == TestResultsModel.StatusColumn:
            self.__testResults.sort(
                key=attrgetter("category", "status"), reverse=reverse
            )
        elif column == TestResultsModel.NameColumn:
            self.__testResults.sort(key=attrgetter("name"), reverse=reverse)
        elif column == TestResultsModel.MessageColumn:
            self.__testResults.sort(key=attrgetter("message"), reverse=reverse)
        elif column == TestResultsModel.DurationColumn:
            self.__testResults.sort(key=durationKey, reverse=reverse)
        self.endResetModel()

    def getTestResults(self):
        """
        Public method to get the list of test results managed by the model.

        @return list of test results managed by the model
        @rtype list of TestResult
        """
        return copy.deepcopy(self.__testResults)

    def setTestResults(self, testResults):
        """
        Public method to set the list of test results of the model.

        @param testResults test results to be managed by the model
        @type list of TestResult
        """
        self.beginResetModel()
        self.__testResults = copy.deepcopy(testResults)
        self.__testResultsById.clear()
        for testResult in testResults:
            self.__testResultsById[testResult.id] = testResult
        self.endResetModel()

        self.summary.emit(self.__summary())

    def addTestResults(self, testResults):
        """
        Public method to add test results to the ones already managed by the
        model.

        @param testResults test results to be added to the model
        @type list of TestResult
        """
        firstRow = len(self.__testResults)
        lastRow = firstRow + len(testResults) - 1
        self.beginInsertRows(QModelIndex(), firstRow, lastRow)
        self.__testResults.extend(testResults)
        for testResult in testResults:
            self.__testResultsById[testResult.id] = testResult
        self.endInsertRows()

        self.summary.emit(self.__summary())

    def updateTestResults(self, testResults):
        """
        Public method to update the data of managed test result items.

        @param testResults test results to be updated
        @type list of TestResult
        """
        minIndex = None
        maxIndex = None

        testResultsToBeAdded = []

        for testResult in testResults:
            if testResult.id in self.__testResultsById:
                result = self.__testResultsById[testResult.id]
                index = self.__testResults.index(result)
                self.__testResults[index] = testResult
                self.__testResultsById[testResult.id] = testResult
                if minIndex is None:
                    minIndex = index
                    maxIndex = index
                else:
                    minIndex = min(minIndex, index)
                    maxIndex = max(maxIndex, index)

            else:
                # Test result with given id was not found.
                # Just add it to the list (could be a sub test)
                testResultsToBeAdded.append(testResult)

        if minIndex is not None:
            self.dataChanged.emit(
                self.index(minIndex, 0),
                self.index(maxIndex, len(TestResultsModel.Headers) - 1),
            )

            self.summary.emit(self.__summary())

        if testResultsToBeAdded:
            self.addTestResults(testResultsToBeAdded)

    def getFailedTests(self):
        """
        Public method to extract the test ids of all failed tests.

        @return test ids of all failed tests
        @rtype list of str
        """
        failedIds = [
            res.id
            for res in self.__testResults
            if (res.category == TestResultCategory.FAIL and not res.subtestResult)
        ]
        return failedIds

    def __summary(self):
        """
        Private method to generate a test results summary text.

        @return test results summary text
        @rtype str
        """
        if len(self.__testResults) == 0:
            return self.tr("No results to show")

        counts = Counter(res.category for res in self.__testResults)
        if all(
            counts[category] == 0
            for category in (
                TestResultCategory.FAIL,
                TestResultCategory.OK,
                TestResultCategory.SKIP,
            )
        ):
            return self.tr("Collected %n test(s)", "", len(self.__testResults))

        return self.tr(
            "%n test(s)/subtest(s) total, {0} failed, {1} passed,"
            " {2} skipped, {3} pending",
            "",
            len(self.__testResults),
        ).format(
            counts[TestResultCategory.FAIL],
            counts[TestResultCategory.OK],
            counts[TestResultCategory.SKIP],
            counts[TestResultCategory.PENDING],
        )

    def getStatusFilterList(self):
        """
        Public method to get a list of the unique test result status.

        @return test result status
        @rtype set of str
        """
        return {t.status for t in self.__testResults}


class TestResultsFilterModel(QSortFilterProxyModel):
    """
    Class implementing a filter model to filter the test results by status.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__statusFilterString = ""

    def filterAcceptsRow(self, sourceRow, sourceParent):
        """
        Public method to determine, if the row is acceptable.

        @param sourceRow row number in the source model
        @type int
        @param sourceParent index of the source item
        @type QModelIndex
        @return flag indicating acceptance
        @rtype bool
        """
        sm = self.sourceModel()
        idx = sm.index(sourceRow, 0, sourceParent)
        status = sm.data(idx, Qt.ItemDataRole.DisplayRole)
        return (
            sourceParent.isValid()
            or self.__statusFilterString == ""
            or status == self.__statusFilterString
        )

    def setStatusFilterString(self, filterString):
        """
        Public method to set the status filter string.

        @param filterString status filter string
        @type str
        """
        self.__statusFilterString = filterString
        self.invalidateRowsFilter()


class TestResultsTreeView(QTreeView):
    """
    Class implementing a tree view to show the test result data.

    @signal goto(str, int) emitted to go to the position given by file name
        and line number
    """

    goto = pyqtSignal(str, int)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)

        self.setItemsExpandable(True)
        self.setExpandsOnDoubleClick(False)
        self.setSortingEnabled(True)

        self.header().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.header().setSortIndicatorShown(False)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # connect signals and slots
        self.activated.connect(self.__gotoTestDefinition)
        self.customContextMenuRequested.connect(self.__showContextMenu)

        self.header().sortIndicatorChanged.connect(self.sortByColumn)
        self.header().sortIndicatorChanged.connect(
            lambda _col, _order: self.header().setSortIndicatorShown(True)
        )

    def reset(self):
        """
        Public method to reset the internal state of the view.
        """
        super().reset()

        self.resizeColumns()
        self.spanFirstColumn(0, self.model().rowCount() - 1)

    def rowsInserted(self, parent, startRow, endRow):
        """
        Public method called when rows are inserted.

        @param parent model index of the parent item
        @type QModelIndex
        @param startRow first row been inserted
        @type int
        @param endRow last row been inserted
        @type int
        """
        super().rowsInserted(parent, startRow, endRow)

        self.spanFirstColumn(startRow, endRow)

    def dataChanged(self, topLeft, bottomRight, roles=None):
        """
        Public method called when the model data has changed.

        @param topLeft index of the top left element
        @type QModelIndex
        @param bottomRight index of the bottom right element
        @type QModelIndex
        @param roles list of roles changed (defaults to None)
        @type list of Qt.ItemDataRole (optional)
        """
        if roles is None:
            roles = []

        super().dataChanged(topLeft, bottomRight, roles)

        while topLeft.parent().isValid():
            topLeft = topLeft.parent()
        while bottomRight.parent().isValid():
            bottomRight = bottomRight.parent()
        self.spanFirstColumn(topLeft.row(), bottomRight.row())

    def resizeColumns(self):
        """
        Public method to resize the columns to their contents.
        """
        for column in range(self.model().columnCount()):
            self.resizeColumnToContents(column)

    def spanFirstColumn(self, startRow, endRow):
        """
        Public method to make the first column span the row for second level
        items.

        These items contain the test results.

        @param startRow index of the first row to span
        @type QModelIndex
        @param endRow index of the last row (including) to span
        @type QModelIndex
        """
        model = self.model()
        for row in range(startRow, endRow + 1):
            index = model.index(row, 0)
            for i in range(model.rowCount(index)):
                self.setFirstColumnSpanned(i, index, True)

    def __canonicalIndex(self, index):
        """
        Private method to create the canonical index for a given index.

        The canonical index is the index of the first column of the test
        result entry (i.e. the top-level item). If the index is invalid,
        None is returned.

        @param index index to determine the canonical index for
        @type QModelIndex
        @return index of the firt column of the associated top-level item index
        @rtype QModelIndex
        """
        if not index.isValid():
            return None

        while index.parent().isValid():  # find the top-level node
            index = index.parent()
        index = index.sibling(index.row(), 0)  # go to first column
        return index

    @pyqtSlot(QModelIndex)
    def __gotoTestDefinition(self, index):
        """
        Private slot to show the test definition.

        @param index index for the double-clicked item
        @type QModelIndex
        """
        cindex = self.__canonicalIndex(index)
        filename, lineno = self.model().data(cindex, Qt.ItemDataRole.UserRole)
        if filename:
            if lineno is None:
                lineno = 1
            self.goto.emit(filename, lineno)

    @pyqtSlot(QPoint)
    def __showContextMenu(self, pos):
        """
        Private slot to show the context menu.

        @param pos relative position for the context menu
        @type QPoint
        """
        index = self.indexAt(pos)
        cindex = self.__canonicalIndex(index)

        contextMenu = (
            self.__createContextMenu(cindex)
            if cindex
            else self.__createBackgroundContextMenu()
        )
        contextMenu.exec(self.mapToGlobal(pos))

    def __createContextMenu(self, index):
        """
        Private method to create a context menu for the item pointed to by the
        given index.

        @param index index of the item
        @type QModelIndex
        @return created context menu
        @rtype QMenu
        """
        menu = QMenu(self)
        if self.isExpanded(index):
            menu.addAction(self.tr("Collapse"), lambda: self.collapse(index))
        else:
            act = menu.addAction(self.tr("Expand"), lambda: self.expand(index))
            act.setEnabled(self.model().hasChildren(index))
        menu.addSeparator()

        act = menu.addAction(
            self.tr("Show Source"), lambda: self.__gotoTestDefinition(index)
        )
        act.setEnabled(
            self.model().data(index, Qt.ItemDataRole.UserRole)[0] is not None
        )
        menu.addSeparator()

        menu.addAction(self.tr("Collapse All"), self.collapseAll)
        menu.addAction(self.tr("Expand All"), self.expandAll)

        return menu

    def __createBackgroundContextMenu(self):
        """
        Private method to create a context menu for the background.

        @return created context menu
        @rtype QMenu
        """
        menu = QMenu(self)
        menu.addAction(self.tr("Collapse All"), self.collapseAll)
        menu.addAction(self.tr("Expand All"), self.expandAll)

        return menu


#
# eflag: noqa = M821, M822
