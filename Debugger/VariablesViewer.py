# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the variables viewer view based on QTreeView.
"""

import ast
import contextlib
import re

from PyQt6.QtCore import (
    QAbstractItemModel,
    QCoreApplication,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QBrush, QFontMetrics
from PyQt6.QtWidgets import QAbstractItemView, QMenu, QToolTip, QTreeView

from eric7 import EricUtilities, Preferences
from eric7.DebugClients.Python.DebugConfig import UnknownAttributeValueMarker
from eric7.EricWidgets.EricApplication import ericApp

from .Config import ConfigVarTypeDispStrings

SORT_ROLE = Qt.ItemDataRole.UserRole


class VariableItem:
    """
    Class implementing the data structure for all variable items.
    """

    # Initialize regular expression for unprintable strings
    rx_nonprintable = re.compile(r"""(\\x\d\d)+""")

    noOfItemsStr = QCoreApplication.translate("VariablesViewer", "{0} items")
    unsized = QCoreApplication.translate("VariablesViewer", "unsized")

    def __init__(self, parent, dvar, indicator, dtype, hasChildren, length, dvalue):
        """
        Constructor

        @param parent reference to the parent item
        @type VariableItem
        @param dvar variable name
        @type str
        @param indicator type indicator appended to the name
        @type str
        @param dtype type string
        @type str
        @param hasChildren indicator for children
        @type bool
        @param length length of the array or string (-1 if uninitialized
            numpy.ndarray)
        @type int
        @param dvalue value string
        @type str
        """
        self.parent = parent
        # Take the additional methods into account for childCount
        self.methodCount = 0
        self.childCount = 0
        self.currentCount = -1  # -1 indicates to (re)load children
        # Indicator that there are children
        self.hasChildren = hasChildren
        self.populated = False
        # Indicator that item was at least once fully populated
        self.wasPopulated = False

        self.children = []
        # Flag to prevent endless reloading of current item while waiting on
        # a response from debugger
        self.pendigFetch = False

        # Set of child items, which are displayed the first time or changed
        self.newItems = set()
        self.changedItems = set()
        # Name including its ID if it's a dict, set, etc.
        self.nameWithId = dvar

        self.name = ""
        self.sort = ""
        vtype = ConfigVarTypeDispStrings.get(dtype, dtype)
        self.type = QCoreApplication.translate("VariablesViewer", vtype)
        self.indicator = indicator
        self.value = dvalue
        self.valueShort = None
        self.tooltip = ""

        self.__getName(dvar)
        self.__getValue(dtype, dvalue, indicator, length)

    def __getName(self, dvar):
        """
        Private method to extract the variable name.

        @param dvar name of variable maybe with ID
        @type str
        """
        try:
            idx = dvar.index(" (ID:")
            dvar = dvar[:idx]
        except AttributeError:
            idx = dvar
            dvar = str(dvar)
        except ValueError:
            pass

        self.name = dvar
        try:
            # Convert numbers to strings with preceding zeros
            asInt = int(dvar)
            self.sort = "{0:06}".format(asInt)
        except ValueError:
            self.sort = dvar.lower()

    def __getValue(self, dtype, dvalue, indicator, length):
        """
        Private method to process the variables value.

        Define and limit value, set tooltip text. If type is known to have
        children, the corresponding flag is set.

        @param dtype type string
        @type str
        @param dvalue value of variable encoded as utf-8
        @type str
        @param indicator type indicator appended to the name
        @type str
        @param length length of the array or string (-1 if uninitialized
            numpy.ndarray)
        @type int or str
        """
        length_code = length
        if isinstance(length, str):
            length = int(length.split("x")[0])

        if indicator and length > -2:
            self.childCount = max(0, length)  # Update count if array
            if dtype == "numpy.ndarray" and length == -1:
                self.value = VariableItem.unsized
            else:
                self.value = VariableItem.noOfItemsStr.format(length_code)

        if dtype != "str":
            if self.value is None:
                return

            if len(self.value) > 256:
                self.valueShort = QCoreApplication.translate(
                    "VariableItem", "<double click to show value>"
                )
            else:
                self.valueShort = self.value[:256]

            self.tooltip = str(self.value)[:256]
            return

        if VariableItem.rx_nonprintable.search(dvalue) is None:
            with contextlib.suppress(Exception):  # secok
                dvalue = ast.literal_eval(dvalue)

        if dvalue.startswith(UnknownAttributeValueMarker):
            self.value = QCoreApplication.translate(
                "VariablesViewer", "[unknown attribute value]"
            )
            self.valueShort = self.value
            self.tooltip = QCoreApplication.translate(
                "VariablesViewer",
                "The attribute value could not be determined.\nReason: {0}",
            ).format(dvalue.replace(UnknownAttributeValueMarker, ""))
            return

        dvalue = str(dvalue)
        self.value = dvalue

        if len(dvalue) > 2048:  # 2 kB
            self.tooltip = dvalue[:2048]
            dvalue = QCoreApplication.translate(
                "VariableItem", "<double click to show value>"
            )
        else:
            self.tooltip = dvalue

        lines = dvalue[:2048].splitlines()
        if len(lines) > 1:
            # only show the first non-empty line;
            # indicate skipped lines by <...> at the
            # beginning and/or end
            index = 0
            while index < len(lines) - 1 and lines[index].strip(" \t") == "":
                index += 1

            dvalue = ""
            if index > 0:
                dvalue += "<...>"
            dvalue += lines[index]
            if index < len(lines) - 1 or len(dvalue) > 2048:
                dvalue += "<...>"

        self.valueShort = dvalue

    @property
    def absolutCount(self):
        """
        Public property to get the total number of children.

        @return total number of children
        @rtype int
        """
        return self.childCount + self.methodCount


class VariablesModel(QAbstractItemModel):
    """
    Class implementing the data model for QTreeView.

    @signal expand trigger QTreeView to expand given index
    """

    expand = pyqtSignal(QModelIndex)

    def __init__(self, treeView, globalScope):
        """
        Constructor

        @param treeView QTreeView showing the data
        @type VariablesViewer
        @param globalScope flag indicating global (True) or local (False)
            variables
        @type bool
        """
        super().__init__()
        self.treeView = treeView
        self.proxyModel = treeView.proxyModel

        self.framenr = -1
        self.openItems = []
        self.closedItems = []

        visibility = self.tr("Globals") if globalScope else self.tr("Locals")
        self.rootNode = VariableItem(
            None, visibility, "", self.tr("Type"), True, 0, self.tr("Value")
        )

        self.__globalScope = globalScope

    def clear(self, reset=False):
        """
        Public method to clear the complete data model.

        @param reset flag to clear the expanded keys also
        @type bool
        """
        self.beginResetModel()
        self.rootNode.children = []
        self.rootNode.newItems.clear()
        self.rootNode.changedItems.clear()
        self.rootNode.wasPopulated = False
        if reset:
            self.openItems = []
            self.closedItems = []
        self.endResetModel()

    def __findVariable(self, pathlist):
        """
        Private method to get to the given variable.

        @param pathlist full path to the variable
        @type list of str
        @return the found variable or None if it doesn't exist
        @rtype VariableItem or None
        """
        node = self.rootNode

        for childName in pathlist or []:
            for item in node.children:
                if item.nameWithId == childName:
                    node = item
                    break
            else:
                return None

        return node  # __IGNORE_WARNING_M834__

    def showVariables(self, vlist, frmnr, pathlist=None):
        """
        Public method to update the data model of variable in pathlist.

        @param vlist the list of variables to be displayed. Each
                list entry is a tuple of six values.
                <ul>
                <li>the variable name (str)</li>
                <li>list, tuple, dict or set indicator (str)</li>
                <li>the variables type (str)</li>
                <li>a flag indicating the presence of children (bool)</li>
                <li>the length of the array or string (int)</li>
                <li>the variables value (str)</li>
                </ul>
        @type list of str
        @param frmnr frame number (0 is the current frame)
        @type int
        @param pathlist full path to the variable
        @type list of str
        """
        if pathlist:
            itemStartIndex = pathlist.pop(0)
        else:
            itemStartIndex = -1
            if self.framenr != frmnr:
                self.clear()
                self.framenr = frmnr

        parent = self.__findVariable(pathlist)
        if parent is None:
            return

        parent.pendigFetch = False

        if parent == self.rootNode:
            parentIdx = QModelIndex()
            parent.methodCount = len(vlist)
        else:
            row = parent.parent.children.index(parent)
            parentIdx = self.createIndex(row, 0, parent)

        if itemStartIndex == -3:
            # Item doesn't exist any more
            parentIdx = self.parent(parentIdx)
            self.beginRemoveRows(parentIdx, row, row)
            del parent.parent.children[row]
            self.endRemoveRows()
            parent.parent.childCount -= 1
            return

        elif itemStartIndex == -2:
            parent.wasPopulated = True
            parent.currentCount = parent.absolutCount
            parent.populated = True
            # Remove items which are left over at the end of child list
            self.__cleanupParentList(parent, parentIdx)
            return

        elif itemStartIndex == -1:
            parent.methodCount = len(vlist)
            idx = max(parent.currentCount, 0)
            parent.currentCount = idx + len(vlist)
            parent.populated = True
        else:
            idx = itemStartIndex
            parent.currentCount = idx + len(vlist)

        # Now update the table
        endIndex = idx + len(vlist)
        newChild = None
        knownChildrenCount = len(parent.children)
        while idx < endIndex:
            # Fetch next old item from last cycle
            try:
                child = parent.children[idx]
            except IndexError:
                child = None

            # Fetch possible new item
            if not newChild and vlist:
                newChild = vlist.pop(0)

                # Process parameters of new item
                newItem = VariableItem(parent, *newChild)
                sort = newItem.sort

            # Append or insert before already existing item
            if child is None or newChild and sort < child.sort:
                self.beginInsertRows(parentIdx, idx, idx)
                parent.children.insert(idx, newItem)
                if knownChildrenCount <= idx and not parent.wasPopulated:
                    parent.newItems.add(newItem)
                    knownChildrenCount += 1
                else:
                    parent.changedItems.add(newItem)
                self.endInsertRows()

                idx += 1
                newChild = None
                continue

            # Check if same name, type and afterwards value
            elif sort == child.sort and child.type == newItem.type:
                # Check if value has changed
                if child.value != newItem.value:
                    child.value = newItem.value
                    child.valueShort = newItem.valueShort
                    child.tooltip = newItem.tooltip
                    child.nameWithId = newItem.nameWithId

                    child.currentCount = -1
                    child.populated = False
                    child.childCount = newItem.childCount

                    # Highlight item because it has changed
                    parent.changedItems.add(child)

                    changedIndexStart = self.index(idx, 0, parentIdx)
                    changedIndexEnd = self.index(idx, 2, parentIdx)
                    self.dataChanged.emit(changedIndexStart, changedIndexEnd)

                newChild = None
                idx += 1
                continue

            # Remove obsolete item
            self.beginRemoveRows(parentIdx, idx, idx)
            parent.children.remove(child)
            self.endRemoveRows()
            # idx stay unchanged
            knownChildrenCount -= 1

        # Remove items which are left over at the end of child list
        if itemStartIndex == -1:
            parent.wasPopulated = True
            self.__cleanupParentList(parent, parentIdx)

        # Request data for any expanded node
        self.getMore()

    def __cleanupParentList(self, parent, parentIdx):
        """
        Private method to remove items which are left over at the end of the
        child list.

        @param parent to clean up
        @type VariableItem
        @param parentIdx the parent index as QModelIndex
        @type QModelIndex
        """
        end = len(parent.children)
        if end > parent.absolutCount:
            self.beginRemoveRows(parentIdx, parent.absolutCount, end)
            del parent.children[parent.absolutCount :]
            self.endRemoveRows()

    def resetModifiedMarker(self, parentIdx=None, pathlist=None):
        """
        Public method to remove the modified marker from changed items.

        @param parentIdx item to reset marker (defaults to None)
        @type QModelIndex (optional)
        @param pathlist full path to the variable (defaults to None)
        @type list of str (optional)
        """
        if parentIdx is None:
            parentIdx = QModelIndex()
        if pathlist is None:
            pathlist = []

        parent = parentIdx.internalPointer() if parentIdx.isValid() else self.rootNode

        parent.newItems.clear()
        parent.changedItems.clear()

        pll = len(pathlist)
        posPaths = {x for x in self.openItems if len(x) > pll}
        posPaths |= {x for x in self.closedItems if len(x) > pll}
        posPaths = {x[pll] for x in posPaths if x[:pll] == pathlist}

        if posPaths:
            for child in parent.children:
                if (
                    child.hasChildren
                    and child.nameWithId in posPaths
                    and child.currentCount >= 0
                ):
                    # Discard loaded elements and refresh if still expanded
                    child.currentCount = -1
                    child.populated = False
                    row = parent.children.index(child)
                    newParentIdx = self.index(row, 0, parentIdx)
                    self.resetModifiedMarker(
                        newParentIdx, pathlist + (child.nameWithId,)
                    )

        self.closedItems = []

        # Little quirk: Refresh all visible items to clear the changed marker
        if parentIdx == QModelIndex():
            self.rootNode.currentCount = -1
            self.rootNode.populated = False
            idxStart = self.index(0, 0, QModelIndex())
            idxEnd = self.index(0, 2, QModelIndex())
            self.dataChanged.emit(idxStart, idxEnd)

    def columnCount(self, parent=None):  # noqa: U100
        """
        Public method to get the column count.

        @param parent the model parent (defaults to None) (unused)
        @type QModelIndex (optional)
        @return number of columns
        @rtype int
        """
        return 3

    def rowCount(self, parent=None):
        """
        Public method to get the row count.

        @param parent the model parent (defaults to None)
        @type QModelIndex (optional)
        @return number of rows
        @rtype int
        """
        node = (
            parent.internalPointer()
            if parent is not None and parent.isValid()
            else self.rootNode
        )

        return len(node.children)

    def flags(self, index):
        """
        Public method to get the item flags.

        @param index of item
        @type QModelIndex
        @return item flags
        @rtype QtCore.Qt.ItemFlag
        """
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags

        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def hasChildren(self, parent=None):
        """
        Public method to get a flag if parent has children.

        @param parent the model parent (defaults to None)
        @type QModelIndex (optional)
        @return flag indicating parent has children
        @rtype bool
        """
        if parent is None or not parent.isValid():
            return self.rootNode.children != []

        return parent.internalPointer().hasChildren

    def index(self, row, column, parent=None):
        """
        Public method to get the index of item at row:column of parent.

        @param row number of rows
        @type int
        @param column number of columns
        @type int
        @param parent the model parent (defaults to None)
        @type QModelIndex (optional)
        @return new model index for child
        @rtype QModelIndex
        """
        if parent is None:
            parent = QModelIndex()

        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        node = parent.internalPointer() if parent.isValid() else self.rootNode

        return self.createIndex(row, column, node.children[row])

    def parent(self, child):
        """
        Public method to get the parent of the given child.

        @param child the model child node
        @type QModelIndex
        @return new model index for parent
        @rtype QModelIndex
        """
        if not child.isValid():
            return QModelIndex()

        childNode = child.internalPointer()
        if childNode == self.rootNode:
            return QModelIndex()

        parentNode = childNode.parent

        if parentNode == self.rootNode:
            return QModelIndex()

        row = parentNode.parent.children.index(parentNode)
        return self.createIndex(row, 0, parentNode)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method get the role data of item.

        @param index the model index
        @type QModelIndex
        @param role the requested data role
        @type QtCore.Qt.ItemDataRole
        @return role data of item
        @rtype Any
        """
        if not index.isValid() or index.row() < 0:
            return None

        node = index.internalPointer()
        column = index.column()

        if role in (Qt.ItemDataRole.DisplayRole, SORT_ROLE, Qt.ItemDataRole.EditRole):
            try:
                if column == 0:
                    # Sort first column with values from third column
                    if role == SORT_ROLE:
                        return node.sort
                    return node.name + node.indicator
                else:
                    return {1: node.valueShort, 2: node.type, 3: node.sort}.get(column)
            except AttributeError:
                return ("None", "", "", "")[column]

        elif role == Qt.ItemDataRole.BackgroundRole:
            if node in node.parent.changedItems:
                return self.__bgColorChanged
            elif node in node.parent.newItems:
                return self.__bgColorNew

        elif role == Qt.ItemDataRole.ToolTipRole:
            if column == 0:
                tooltip = node.name + node.indicator
            elif column == 1:
                tooltip = node.tooltip
            elif column == 2:
                tooltip = node.type
            elif column == 3:
                tooltip = node.sort
            else:
                return None

            if Qt.mightBeRichText(tooltip):
                tooltip = EricUtilities.html_encode(tooltip)

            if column == 0:
                indentation = self.treeView.indentation()
                indentCount = 0
                currentNode = node
                while currentNode.parent:
                    indentCount += 1
                    currentNode = currentNode.parent

                indentation *= indentCount
            else:
                indentation = 0
            # Check if text is longer than available space
            fontMetrics = QFontMetrics(self.treeView.font())
            textSize = fontMetrics.horizontalAdvance(tooltip) + indentation + 5
            # How to determine border size?
            header = self.treeView.header()
            if textSize >= header.sectionSize(column):
                return tooltip
            else:
                QToolTip.hideText()

        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        """
        Public method get the header names.

        @param section the header section (row/column)
        @type int
        @param orientation the header's orientation
        @type QtCore.Qt.Orientation
        @param role the requested data role
        @type QtCore.Qt.ItemDataRole
        @return header name
        @rtype str or None
        """
        if (
            role != Qt.ItemDataRole.DisplayRole
            or orientation != Qt.Orientation.Horizontal
        ):
            return None

        return {
            0: self.rootNode.name,
            1: self.rootNode.value,
            2: self.rootNode.type,
            3: self.rootNode.sort,
        }.get(section)

    def __findPendingItem(self, parent=None, pathlist=()):
        """
        Private method to find the next item to request data from debugger.

        @param parent the model parent
        @type VariableItem
        @param pathlist full path to the variable
        @type list of str
        @return next item index to request data from debugger
        @rtype QModelIndex
        """
        if parent is None:
            parent = self.rootNode

        for child in parent.children:
            if not child.hasChildren:
                continue

            if pathlist + (child.nameWithId,) in self.openItems:
                if child.populated:
                    index = None
                else:
                    idx = parent.children.index(child)
                    index = self.createIndex(idx, 0, child)
                    self.expand.emit(index)

                if child.currentCount < 0:
                    return index

                possibleIndex = self.__findPendingItem(
                    child, pathlist + (child.nameWithId,)
                )

                if (possibleIndex or index) is None:
                    continue

                return possibleIndex or index

        return None

    def getMore(self):
        """
        Public method to fetch the next variable from debugger.
        """
        # step 1: find expanded but not populated items
        item = self.__findPendingItem()
        if not item or not item.isValid():
            return

        # step 2: check if data has to be retrieved
        node = item.internalPointer()
        lastVisibleItem = self.index(node.currentCount - 1, 0, item)
        lastVisibleItem = self.proxyModel.mapFromSource(lastVisibleItem)
        rect = self.treeView.visualRect(lastVisibleItem)
        if rect.y() > self.treeView.height() or node.pendigFetch:
            return

        node.pendigFetch = True
        # step 3: get a pathlist up to the requested variable
        pathlist = self.__buildTreePath(node)
        # step 4: request the variable from the debugger
        variablesFilter = (
            ericApp().getObject("DebugUI").variablesFilter(self.__globalScope)
        )
        ericApp().getObject("DebugServer").remoteClientVariable(
            ericApp().getObject("DebugUI").getSelectedDebuggerId(),
            1 if self.__globalScope else 0,
            variablesFilter,
            pathlist,
            self.framenr,
        )

    def setExpanded(self, index, state):
        """
        Public method to set the expanded state of item.

        @param index item to change expanded state
        @type QModelIndex
        @param state state of the item
        @type bool
        """
        node = index.internalPointer()
        pathlist = self.__buildTreePath(node)
        if state:
            if pathlist not in self.openItems:
                self.openItems.append(pathlist)
                if pathlist in self.closedItems:
                    self.closedItems.remove(pathlist)
                self.getMore()
        else:
            if pathlist in self.openItems:
                self.openItems.remove(pathlist)
            self.closedItems.append(pathlist)

    def __buildTreePath(self, parent):
        """
        Private method to build up a path from the root to parent.

        @param parent item to build the path for
        @type VariableItem
        @return list of names denoting the path from the root
        @rtype tuple of str
        """
        pathlist = []

        # build up a path from the top to the item
        while parent.parent:
            pathlist.append(parent.nameWithId)
            parent = parent.parent

        pathlist.reverse()
        return tuple(pathlist)

    def handlePreferencesChanged(self):
        """
        Public slot to handle the preferencesChanged signal.
        """
        self.__bgColorNew = QBrush(Preferences.getDebugger("BgColorNew"))
        self.__bgColorChanged = QBrush(Preferences.getDebugger("BgColorChanged"))

        idxStart = self.index(0, 0, QModelIndex())
        idxEnd = self.index(0, 2, QModelIndex())
        self.dataChanged.emit(idxStart, idxEnd)


class VariablesProxyModel(QSortFilterProxyModel):
    """
    Class for handling the sort operations.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent the parent model index
        @type QModelIndex
        """
        super().__init__(parent)
        self.setSortRole(SORT_ROLE)

    def hasChildren(self, parent):
        """
        Public method to get a flag if parent has children.

        The given model index has to be transformed to the underlying source
        model to get the correct result.

        @param parent the model parent
        @type QModelIndex
        @return flag if parent has children
        @rtype bool
        """
        return self.sourceModel().hasChildren(self.mapToSource(parent))

    def setExpanded(self, index, state):
        """
        Public slot to get a flag if parent has children.

        The given model index has to be transformed to the underlying source
        model to get the correct result.
        @param index item to change expanded state
        @type QModelIndex
        @param state state of the item
        @type bool
        """
        self.sourceModel().setExpanded(self.mapToSource(index), state)


class VariablesViewer(QTreeView):
    """
    Class implementing the variables viewer view.

    This view is used to display the variables of the program being
    debugged in a tree. Compound types will be shown with
    their main entry first. Once the subtree has been expanded, the
    individual entries will be shown. Double clicking an entry will
    expand or collapse the item, if it has children and the double click
    was performed on the first column of the tree, otherwise it'll
    popup a dialog showing the variables parameters in a more readable
    form. This is especially useful for lengthy strings.

    This view has two modes for displaying the global and the local
    variables.

    @signal preferencesChanged() to inform model about new background colours
    """

    preferencesChanged = pyqtSignal()

    def __init__(self, viewer, globalScope, parent=None):
        """
        Constructor

        @param viewer reference to the debug viewer object
        @type DebugViewer
        @param globalScope flag indicating global (True) or local (False)
            variables
        @type bool
        @param parent the parent
        @type QWidget
        """
        super().__init__(parent)

        self.__debugViewer = viewer
        self.__globalScope = globalScope
        self.framenr = 0

        # Massive performance gain
        self.setUniformRowHeights(True)

        # Implements sorting and filtering
        self.proxyModel = VariablesProxyModel()
        # Variable model implements the underlying data model
        self.varModel = VariablesModel(self, globalScope)
        self.proxyModel.setSourceModel(self.varModel)
        self.setModel(self.proxyModel)
        self.preferencesChanged.connect(self.varModel.handlePreferencesChanged)
        self.preferencesChanged.emit()  # Force initialization of colors

        self.expanded.connect(lambda idx: self.proxyModel.setExpanded(idx, True))
        self.collapsed.connect(lambda idx: self.proxyModel.setExpanded(idx, False))

        self.setExpandsOnDoubleClick(False)
        self.doubleClicked.connect(self.__itemDoubleClicked)

        self.varModel.expand.connect(self.__mdlRequestExpand)

        self.setSortingEnabled(True)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        if self.__globalScope:
            self.setWindowTitle(self.tr("Global Variables"))
            self.setWhatsThis(
                self.tr(
                    """<b>The Global Variables Viewer Window</b>"""
                    """<p>This window displays the global variables"""
                    """ of the debugged program.</p>"""
                )
            )
        else:
            self.setWindowTitle(self.tr("Local Variables"))
            self.setWhatsThis(
                self.tr(
                    """<b>The Local Variables Viewer Window</b>"""
                    """<p>This window displays the local variables"""
                    """ of the debugged program.</p>"""
                )
            )

        header = self.header()
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        header.setSortIndicatorShown(True)

        try:
            header.setSectionsClickable(True)
        except Exception:
            header.setClickable(True)

        header.resizeSection(0, 130)  # variable column
        header.resizeSection(1, 180)  # value column
        header.resizeSection(2, 50)  # type column

        header.sortIndicatorChanged.connect(lambda *_x: self.varModel.getMore())

        self.__createPopupMenus()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__showContextMenu)

        self.resortEnabled = True

    def showVariables(self, vlist, frmnr):
        """
        Public method to show variables in a list.

        @param vlist the list of variables to be displayed. Each
                list entry is a tuple of six values.
                <ul>
                <li>the variable name (str)</li>
                <li>list, tuple, dict or set indicator (str)</li>
                <li>the variables type (str)</li>
                <li>a flag indicating the presence of children (bool)</li>
                <li>the length of the array or string (int)</li>
                <li>the variables value (str)</li>
                </ul>
        @type list
        @param frmnr frame number (0 is the current frame)
        @type int
        """
        self.varModel.resetModifiedMarker()
        self.varModel.showVariables(vlist, frmnr)

    def showVariable(self, vlist):
        """
        Public method to show variables in a list.

        @param vlist the list of subitems to be displayed.
                The first element gives the path of the
                parent variable. Each other list entry is
                a tuple of six values.
                <ul>
                <li>the variable name (str)</li>
                <li>list, tuple, dict or set indicator (str)</li>
                <li>the variables type (str)</li>
                <li>a flag indicating the presence of children (bool)</li>
                <li>the length of the array or string (int)</li>
                <li>the variables value (str)</li>
                </ul>
        @type list
        """
        self.varModel.showVariables(vlist[1:], 0, vlist[0])

    def handleResetUI(self):
        """
        Public method to reset the VariablesViewer.
        """
        self.varModel.clear(True)

    def verticalScrollbarValueChanged(self, value):
        """
        Public slot informing about the scrollbar change.

        @param value current value of the vertical scrollbar
        @type int
        """
        self.varModel.getMore()
        super().verticalScrollbarValueChanged(value)

    def resizeEvent(self, event):
        """
        Protected slot informing about the widget size change.

        @param event information
        @type QResizeEvent
        """
        self.varModel.getMore()
        super().resizeEvent(event)

    def __itemDoubleClicked(self, index):
        """
        Private method called if an item was double clicked.

        @param index the double clicked item
        @type QModelIndex
        """
        node = self.proxyModel.mapToSource(index).internalPointer()
        if node:
            if node.hasChildren and index.column() == 0:
                state = self.isExpanded(index)
                self.setExpanded(index, not state)
            else:
                self.__showVariableDetails(index)

    def __mdlRequestExpand(self, modelIndex):
        """
        Private method to inform the view about items to be expand.

        @param modelIndex the model index
        @type QModelIndex
        """
        index = self.proxyModel.mapFromSource(modelIndex)
        self.expand(index)

    def __createPopupMenus(self):
        """
        Private method to generate the popup menus.
        """
        self.menu = QMenu()
        self.menu.addAction(self.tr("Show Details..."), self.__showDetails)
        self.menu.addSeparator()
        self.__expandChildrenAct = self.menu.addAction(
            self.tr("Expand Subitems"), self.__expandChildren
        )
        self.__collapseChildrenAct = self.menu.addAction(
            self.tr("Collapse Subitems"), self.__collapseChildren
        )
        self.menu.addAction(self.tr("Collapse All"), self.collapseAll)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Refresh"), self.__refreshView)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Configure..."), self.__configure)
        self.menu.addAction(self.tr("Variables Type Filter..."), self.__configureFilter)

        self.backMenu = QMenu()
        self.backMenu.addAction(self.tr("Refresh"), self.__refreshView)
        self.backMenu.addSeparator()
        self.backMenu.addAction(self.tr("Configure..."), self.__configure)
        self.backMenu.addAction(
            self.tr("Variables Type Filter..."), self.__configureFilter
        )

    def __showContextMenu(self, coord):
        """
        Private slot to show the context menu.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        gcoord = self.mapToGlobal(coord)
        index = self.indexAt(coord)
        if index.isValid():
            expanded = self.isExpanded(index)
            self.__expandChildrenAct.setEnabled(expanded)
            self.__collapseChildrenAct.setEnabled(expanded)
            self.menu.popup(gcoord)
        else:
            self.backMenu.popup(gcoord)

    def __expandChildren(self):
        """
        Private slot to expand all child items of current parent.
        """
        index = self.currentIndex()
        node = self.proxyModel.mapToSource(index).internalPointer()
        if node:
            for child in node.children:
                if child.hasChildren:
                    row = node.children.index(child)
                    idx = self.varModel.createIndex(row, 0, child)
                    idx = self.proxyModel.mapFromSource(idx)
                    self.expand(idx)

    def __collapseChildren(self):
        """
        Private slot to collapse all child items of current parent.
        """
        index = self.currentIndex()
        node = self.proxyModel.mapToSource(index).internalPointer()
        if node:
            for child in node.children:
                row = node.children.index(child)
                idx = self.varModel.createIndex(row, 0, child)
                idx = self.proxyModel.mapFromSource(idx)
                if self.isExpanded(idx):
                    self.collapse(idx)

    def __refreshView(self):
        """
        Private slot to refresh the view.
        """
        if self.__globalScope:
            self.__debugViewer.setGlobalsFilter()
        else:
            self.__debugViewer.setLocalsFilter()

    def __showDetails(self):
        """
        Private slot to show details about the selected variable.
        """
        idx = self.currentIndex()
        self.__showVariableDetails(idx)

    def __showVariableDetails(self, index):
        """
        Private method to show details about a variable.

        @param index reference to the variable item
        @type QModelIndex
        """
        from .VariableDetailDialog import VariableDetailDialog

        node = self.proxyModel.mapToSource(index).internalPointer()
        if node is None:
            return

        val = node.value
        vtype = node.type
        name = node.name

        par = node.parent
        nlist = [name]

        # build up the fully qualified name
        while par.parent is not None:
            pname = par.name
            if par.indicator:
                if nlist[0].endswith("."):
                    nlist[0] = "[{0}].".format(nlist[0][:-1])
                else:
                    nlist[0] = "[{0}]".format(nlist[0])
                nlist.insert(0, pname)
            else:
                if par.type == "django.MultiValueDict":
                    nlist[0] = "getlist({0})".format(nlist[0])
                elif par.type == "numpy.ndarray":
                    if nlist and nlist[0][0].isalpha():
                        if nlist[0] in ["min", "max", "mean"]:
                            nlist[0] = ".{0}()".format(nlist[0])
                        else:
                            nlist[0] = ".{0}".format(nlist[0])
                    nlist.insert(0, pname)
                else:
                    nlist.insert(0, "{0}.".format(pname))
            par = par.parent

        name = "".join(nlist)
        # now show the dialog
        dlg = VariableDetailDialog(name, vtype, val, parent=self)
        dlg.exec()

    def __configure(self):
        """
        Private method to open the configuration dialog.
        """
        ericApp().getObject("UserInterface").showPreferences("debuggerGeneralPage")

    def __configureFilter(self):
        """
        Private method to open the variables filter dialog.
        """
        ericApp().getObject("DebugUI").dbgFilterAct.triggered.emit()

    def clear(self):
        """
        Public method to clear the viewer.
        """
        self.varModel.clear()


#
# eflag: noqa = M822
