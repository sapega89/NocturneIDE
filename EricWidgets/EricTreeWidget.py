# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing specialized tree views.
"""

import enum

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QAbstractItemView, QTreeWidget, QTreeWidgetItem


class EricTreeWidgetItemsState(enum.Enum):
    """
    Class defining the items expansion state.
    """

    COLLAPSED = 0
    EXPANDED = 1


class EricTreeWidget(QTreeWidget):
    """
    Class implementing an extended tree widget.

    @signal itemControlClicked(QTreeWidgetItem) emitted after a Ctrl-Click
            on an item
    @signal itemMiddleButtonClicked(QTreeWidgetItem) emitted after a click
            of the middle button on an item
    """

    itemControlClicked = pyqtSignal(QTreeWidgetItem)
    itemMiddleButtonClicked = pyqtSignal(QTreeWidgetItem)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__refreshAllItemsNeeded = True
        self.__allTreeItems = []
        self.__showMode = EricTreeWidgetItemsState.COLLAPSED

        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        self.itemChanged.connect(self.__scheduleRefresh)

    def setDefaultItemShowMode(self, mode):
        """
        Public method to set the default item show mode.

        @param mode default mode
        @type EricTreeWidgetItemsState
        """
        self.__showMode = mode

    def allItems(self):
        """
        Public method to get a list of all items.

        @return list of all items
        @rtype list of QTreeWidgetItem
        """
        if self.__refreshAllItemsNeeded:
            self.__allTreeItems = []
            self.__iterateAllItems(None)
            self.__refreshAllItemsNeeded = False

        return self.__allTreeItems

    def appendToParentItem(self, parent, item):
        """
        Public method to append an item to a parent item.

        @param parent text of the parent item or the parent item
        @type str or QTreeWidgetItem
        @param item item to be appended
        @type QTreeWidgetItem
        @return flag indicating success
        @rtype bool
        @exception RuntimeError raised to indicate an illegal type for
            the parent
        """
        if not isinstance(parent, (QTreeWidgetItem, str)):
            raise RuntimeError("illegal type for parent")

        if isinstance(parent, QTreeWidgetItem):
            if parent is None or parent.treeWidget() != self:
                return False
            parentItem = parent
        else:
            lst = self.findItems(parent, Qt.MatchFlag.MatchExactly)
            if not lst:
                return False
            parentItem = lst[0]
            if parentItem is None:
                return False

        self.__allTreeItems.append(item)
        parentItem.addChild(item)
        return True

    def prependToParentItem(self, parent, item):
        """
        Public method to prepend an item to a parent item.

        @param parent text of the parent item or the parent item
        @type str or QTreeWidgetItem
        @param item item to be prepended
        @type QTreeWidgetItem
        @return flag indicating success
        @rtype bool
        @exception RuntimeError raised to indicate an illegal type for
            the parent
        """
        if not isinstance(parent, (QTreeWidgetItem, str)):
            raise RuntimeError("illegal type for parent")

        if isinstance(parent, QTreeWidgetItem):
            if parent is None or parent.treeWidget() != self:
                return False
            parentItem = parent
        else:
            lst = self.findItems(parent, Qt.MatchFlag.MatchExactly)
            if not lst:
                return False
            parentItem = lst[0]
            if parentItem is None:
                return False

        self.__allTreeItems.append(item)
        parentItem.insertChild(0, item)
        return True

    def addTopLevelItem(self, item):
        """
        Public method to add a top level item.

        @param item item to be added as a top level item
        @type QTreeWidgetItem
        """
        self.__allTreeItems.append(item)
        super().addTopLevelItem(item)

    def addTopLevelItems(self, items):
        """
        Public method to add a list of top level items.

        @param items items to be added as top level items
        @type list of QTreeWidgetItem
        """
        self.__allTreeItems.extend(items)
        super().addTopLevelItems(items)

    def insertTopLevelItem(self, index, item):
        """
        Public method to insert a top level item.

        @param index index for the insertion
        @type int
        @param item item to be inserted as a top level item
        @type QTreeWidgetItem
        """
        self.__allTreeItems.append(item)
        super().insertTopLevelItem(index, item)

    def insertTopLevelItems(self, index, items):
        """
        Public method to insert a list of top level items.

        @param index index for the insertion
        @type int
        @param items items to be inserted as top level items
        @type list of QTreeWidgetItem
        """
        self.__allTreeItems.extend(items)
        super().insertTopLevelItems(index, items)

    def deleteItem(self, item):
        """
        Public method to delete an item.

        @param item item to be deleted
        @type QTreeWidgetItem
        """
        if item in self.__allTreeItems:
            self.__allTreeItems.remove(item)

        self.__refreshAllItemsNeeded = True

        del item

    def deleteItems(self, items):
        """
        Public method to delete a list of items.

        @param items items to be deleted
        @type list of QTreeWidgetItem
        """
        for item in items:
            self.deleteItem(item)

    def filterString(self, filterStr):
        """
        Public slot to set a new filter.

        @param filterStr filter to be set
        @type str
        """
        self.expandAll()
        allItems = self.allItems()

        if filterStr:
            lFilter = filterStr.lower()
            for itm in allItems:
                itm.setHidden(lFilter not in itm.text(0).lower())
                itm.setExpanded(True)
            for index in range(self.topLevelItemCount()):
                self.topLevelItem(index).setHidden(False)

            firstItm = self.topLevelItem(0)
            belowItm = self.itemBelow(firstItm)
            topLvlIndex = 0
            while firstItm:
                if lFilter in firstItm.text(0).lower():
                    firstItm.setHidden(False)
                elif not firstItm.parent() and (not belowItm or not belowItm.parent()):
                    firstItm.setHidden(True)
                elif not belowItm:
                    break

                topLvlIndex += 1
                firstItm = self.topLevelItem(topLvlIndex)
                belowItm = self.itemBelow(firstItm)
        else:
            for itm in allItems:
                itm.setHidden(False)
            for index in range(self.topLevelItemCount()):
                self.topLevelItem(index).setHidden(False)
            if self.__showMode == EricTreeWidgetItemsState.COLLAPSED:
                self.collapseAll()

    def clear(self):
        """
        Public slot to clear the tree.
        """
        self.__allTreeItems = []
        super().clear()

    def __scheduleRefresh(self):
        """
        Private slot to schedule a refresh of the tree.
        """
        self.__refreshAllItemsNeeded = True

    def mousePressEvent(self, evt):
        """
        Protected method handling mouse press events.

        @param evt mouse press event
        @type QMouseEvent
        """
        if (
            evt.modifiers() == Qt.KeyboardModifier.ControlModifier
            and evt.buttons() == Qt.MouseButton.LeftButton
        ):
            self.itemControlClicked.emit(self.itemAt(evt.position().toPoint()))
            return
        elif evt.buttons() == Qt.MouseButton.MiddleButton:
            self.itemMiddleButtonClicked.emit(self.itemAt(evt.position().toPoint()))
            return
        else:
            super().mousePressEvent(evt)

    def __iterateAllItems(self, parent):
        """
        Private method to iterate over the child items of the parent.

        @param parent parent item to iterate
        @type QTreeWidgetItem
        """
        count = parent.childCount() if parent else self.topLevelItemCount()

        for index in range(count):
            itm = parent.child(index) if parent else self.topLevelItem(index)

            if itm.childCount() == 0:
                self.__allTreeItems.append(itm)

            self.__iterateAllItems(itm)
