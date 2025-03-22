# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a special list widget for GreaseMonkey scripts.
"""

from PyQt6.QtCore import QRect, pyqtSignal
from PyQt6.QtWidgets import QListWidget, QListWidgetItem

from .GreaseMonkeyConfigurationListDelegate import GreaseMonkeyConfigurationListDelegate


class GreaseMonkeyConfigurationListWidget(QListWidget):
    """
    Class implementing a special list widget for GreaseMonkey scripts.

    @signal removeItemRequested(item) emitted to indicate an item removal
        request (QListWidgetItem)
    """

    removeItemRequested = pyqtSignal(QListWidgetItem)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__delegate = GreaseMonkeyConfigurationListDelegate(self)
        self.setItemDelegate(self.__delegate)

    def __containsRemoveIcon(self, pos):
        """
        Private method to check, if the given position is inside the remove
        icon.

        @param pos position to check for
        @type QPoint
        @return flag indicating success
        @rtype bool
        """
        itm = self.itemAt(pos)
        if itm is None:
            return False

        rect = self.visualItemRect(itm)
        iconSize = GreaseMonkeyConfigurationListDelegate.RemoveIconSize
        removeIconXPos = rect.right() - self.__delegate.padding() - iconSize
        center = rect.height() // 2 + rect.top()
        removeIconYPos = center - iconSize // 2

        removeIconRect = QRect(removeIconXPos, removeIconYPos, iconSize, iconSize)
        return removeIconRect.contains(pos)

    def mousePressEvent(self, evt):
        """
        Protected method handling presses of mouse buttons.

        @param evt mouse press event
        @type QMouseEvent
        """
        if self.__containsRemoveIcon(evt.position().toPoint()):
            self.removeItemRequested.emit(self.itemAt(evt.position().toPoint()))
            return

        super().mousePressEvent(evt)

    def mouseDoubleClickEvent(self, evt):
        """
        Protected method handling mouse double click events.

        @param evt mouse press event
        @type QMouseEvent
        """
        if self.__containsRemoveIcon(evt.position().toPoint()):
            self.removeItemRequested.emit(self.itemAt(evt.position().toPoint()))
            return

        super().mouseDoubleClickEvent(evt)
