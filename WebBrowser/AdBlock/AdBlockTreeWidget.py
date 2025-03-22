# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a tree widget for the AdBlock configuration dialog.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QInputDialog,
    QLineEdit,
    QMenu,
    QTreeWidgetItem,
)

from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricTreeWidget import EricTreeWidget, EricTreeWidgetItemsState


class AdBlockTreeWidget(EricTreeWidget):
    """
    Class implementing a tree widget for the AdBlock configuration dialog.
    """

    def __init__(self, subscription, parent=None):
        """
        Constructor

        @param subscription reference to the subscription
        @type AdBlockSubscription
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__subscription = subscription
        self.__topItem = None
        self.__ruleToBeSelected = ""
        self.__itemChangingBlock = False

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setDefaultItemShowMode(EricTreeWidgetItemsState.EXPANDED)
        self.setHeaderHidden(True)
        self.setAlternatingRowColors(True)

        self.__darkMode = ericApp().usesDarkPalette()

        self.customContextMenuRequested.connect(self.__contextMenuRequested)
        self.itemChanged.connect(self.__itemChanged)
        self.__subscription.changed.connect(self.__subscriptionChanged)
        self.__subscription.rulesChanged.connect(self.__subscriptionChanged)

    def subscription(self):
        """
        Public method to get a reference to the subscription.

        @return reference to the subscription
        @rtype AdBlockSubscription
        """
        return self.__subscription

    def showRule(self, rule):
        """
        Public method to highlight the given rule.

        @param rule AdBlock rule to be shown
        @type AdBlockRule
        """
        if not bool(self.__topItem) and bool(rule):
            self.__ruleToBeSelected = rule.filter()
        elif self.__ruleToBeSelected:
            items = self.findItems(self.__ruleToBeSelected, Qt.MatchFlag.MatchRecursive)
            if items:
                item = items[0]
                self.setCurrentItem(item)
                self.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)

            self.__ruleToBeSelected = ""

    def refresh(self):
        """
        Public method to refresh the tree.
        """
        with EricOverrideCursor():
            self.__itemChangingBlock = True
            self.clear()

            boldFont = QFont()
            boldFont.setBold(True)

            self.__topItem = QTreeWidgetItem(self)
            self.__topItem.setText(0, self.__subscription.title())
            self.__topItem.setFont(0, boldFont)
            self.addTopLevelItem(self.__topItem)

            allRules = self.__subscription.allRules()

            for index, rule in enumerate(allRules):
                item = QTreeWidgetItem(self.__topItem)
                item.setText(0, rule.filter())
                item.setData(0, Qt.ItemDataRole.UserRole, index)
                if self.__subscription.canEditRules():
                    item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                self.__adjustItemFeatures(item, rule)

            self.expandAll()
            self.showRule(None)
            self.__itemChangingBlock = False

    def addRule(self, filterRule=""):
        """
        Public slot to add a new rule.

        @param filterRule filter to be added
        @type str
        """
        from .AdBlockRule import AdBlockRule

        if not self.__subscription.canEditRules():
            return

        if not filterRule:
            filterRule, ok = QInputDialog.getText(
                self,
                self.tr("Add Custom Rule"),
                self.tr("Write your rule here:"),
                QLineEdit.EchoMode.Normal,
            )
            if not ok or filterRule == "":
                return

        rule = AdBlockRule(filterRule, self.__subscription)
        self.__subscription.addRule(rule)

    def removeRule(self):
        """
        Public slot to remove the current rule.
        """
        item = self.currentItem()
        if (
            item is None
            or not self.__subscription.canEditRules()
            or item == self.__topItem
        ):
            return

        offset = item.data(0, Qt.ItemDataRole.UserRole)
        self.__subscription.removeRule(offset)
        self.deleteItem(item)

    def __contextMenuRequested(self, pos):
        """
        Private slot to show the context menu.

        @param pos position for the menu
        @type QPoint
        """
        if not self.__subscription.canEditRules():
            return

        item = self.itemAt(pos)
        if item is None:
            return

        menu = QMenu()
        menu.addAction(self.tr("Add Rule"), self.addRule)
        menu.addSeparator()
        act = menu.addAction(self.tr("Remove Rule"), self.removeRule)
        if item.parent() is None:
            act.setDisabled(True)

        menu.exec(self.viewport().mapToGlobal(pos))

    def __itemChanged(self, itm):
        """
        Private slot to handle the change of an item.

        @param itm changed item
        @type QTreeWidgetItem
        """
        from .AdBlockRule import AdBlockRule

        if itm is None or self.__itemChangingBlock:
            return

        self.__itemChangingBlock = True

        offset = itm.data(0, Qt.ItemDataRole.UserRole)
        oldRule = self.__subscription.rule(offset)

        if itm.checkState(0) == Qt.CheckState.Unchecked and oldRule.isEnabled():
            # Disable rule
            rule = self.__subscription.setRuleEnabled(offset, False)
            self.__adjustItemFeatures(itm, rule)
        elif itm.checkState(0) == Qt.CheckState.Checked and not oldRule.isEnabled():
            # Enable rule
            rule = self.__subscription.setRuleEnabled(offset, True)
            self.__adjustItemFeatures(itm, rule)
        elif self.__subscription.canEditRules():
            # Custom rule has been changed
            rule = self.__subscription.replaceRule(
                AdBlockRule(itm.text(0), self.__subscription), offset
            )
            self.__adjustItemFeatures(itm, rule)

        self.__itemChangingBlock = False

    def __copyFilter(self):
        """
        Private slot to copy the current filter to the clipboard.
        """
        item = self.currentItem()
        if item is not None:
            QApplication.clipboard().setText(item.text(0))

    def __subscriptionChanged(self):
        """
        Private slot handling a subscription change.
        """
        self.refresh()

        self.__itemChangingBlock = True
        self.__topItem.setText(
            0, self.tr("{0} (recently updated)").format(self.__subscription.title())
        )
        self.__itemChangingBlock = False

    def __adjustItemFeatures(self, itm, rule):
        """
        Private method to adjust an item.

        @param itm item to be adjusted
        @type QTreeWidgetItem
        @param rule rule for the adjustment
        @type AdBlockRule
        """
        if not rule.isEnabled():
            font = QFont()
            font.setItalic(True)
            if self.__darkMode:
                itm.setForeground(0, QColor("#a3a3a3"))
            else:
                itm.setForeground(0, QColor(Qt.GlobalColor.gray))

            if not rule.isComment() and not rule.isHeader():
                itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                itm.setCheckState(0, Qt.CheckState.Unchecked)
                itm.setFont(0, font)

            return

        itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        itm.setCheckState(0, Qt.CheckState.Checked)

        if rule.isCSSRule():
            if self.__darkMode:
                itm.setForeground(0, QColor("#7897d1"))
            else:
                itm.setForeground(0, QColor(Qt.GlobalColor.darkBlue))
            itm.setFont(0, QFont())
        elif rule.isException():
            if self.__darkMode:
                itm.setForeground(0, QColor("#75d180"))
            else:
                itm.setForeground(0, QColor(Qt.GlobalColor.darkGreen))
            itm.setFont(0, QFont())
        else:
            if self.__darkMode:
                itm.setForeground(0, QColor("#fefefe"))
            else:
                itm.setForeground(0, QColor("#000000"))
            itm.setFont(0, QFont())

    def keyPressEvent(self, evt):
        """
        Protected method handling key presses.

        @param evt key press event
        @type QKeyEvent
        """
        if (
            evt.key() == Qt.Key.Key_C
            and evt.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            self.__copyFilter()
        elif evt.key() == Qt.Key.Key_Delete:
            self.removeRule()
        else:
            super().keyPressEvent(evt)
