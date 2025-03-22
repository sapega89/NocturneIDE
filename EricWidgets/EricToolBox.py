# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a horizontal and a vertical toolbox class.
"""

from PyQt6.QtWidgets import QTabWidget, QToolBox

from .EricTabWidget import EricTabWidget


class EricVerticalToolBox(QToolBox):
    """
    Class implementing a ToolBox class substituting QToolBox to support wheel
    events.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

    def setCurrentWidget(self, widget):
        """
        Public slot to set the current widget.

        @param widget reference to the widget to become the current widget
        @type QWidget
        """
        try:
            index = self.indexOf(widget)
            if index < 0:
                # not found, set first widget as default
                index = 0
        except RuntimeError:
            index = 0
        self.setCurrentIndex(index)


class EricHorizontalToolBox(EricTabWidget):
    """
    Class implementing a vertical QToolBox like widget.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        EricTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.West)
        self.setUsesScrollButtons(True)

    def addItem(self, widget, icon, text):
        """
        Public method to add a widget to the toolbox.

        @param widget reference to the widget to be added
        @type QWidget
        @param icon the icon to be shown
        @type QIcon
        @param text the text to be shown
        @type str
        @return index of the added widget
        @rtype int
        """
        index = self.addTab(widget, icon, "")
        self.setTabToolTip(index, text)
        return index

    def insertItem(self, index, widget, icon, text):
        """
        Public method to add a widget to the toolbox.

        @param index position at which the widget should be inserted
        @type int
        @param widget reference to the widget to be added
        @type QWidget
        @param icon the icon to be shown
        @type QIcon
        @param text the text to be shown
        @type str
        @return index of the added widget
        @rtype int
        """
        index = self.insertTab(index, widget, icon, "")
        self.setTabToolTip(index, text)
        return index

    def removeItem(self, index):
        """
        Public method to remove a widget from the toolbox.

        @param index index of the widget to remove
        @type int
        """
        self.removeTab(index)

    def setItemToolTip(self, index, toolTip):
        """
        Public method to set the tooltip of an item.

        @param index index of the item
        @type int
        @param toolTip tooltip text to be set
        @type str
        """
        self.setTabToolTip(index, toolTip)

    def setItemEnabled(self, index, enabled):
        """
        Public method to set the enabled state of an item.

        @param index index of the item
        @type int
        @param enabled flag indicating the enabled state
        @type bool
        """
        self.setTabEnabled(index, enabled)

    def setCurrentWidget(self, widget):
        """
        Public slot to set the current widget.

        @param widget reference to the widget to become the current widget
        @type QWidget
        """
        try:
            index = self.indexOf(widget)
            if index < 0:
                # not found, set first widget as default
                index = 0
        except RuntimeError:
            index = 0
        self.setCurrentIndex(index)
