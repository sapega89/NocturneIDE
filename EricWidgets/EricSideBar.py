# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a sidebar class.
"""

import enum
import json

from PyQt6.QtCore import QSize, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QBoxLayout, QStackedWidget, QWidget

from .EricIconBar import EricIconBar


class EricSideBarSide(enum.Enum):
    """
    Class defining the sidebar sides.
    """

    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3


class EricSideBar(QWidget):
    """
    Class implementing a sidebar with a widget area, that is hidden or shown,
    if the current tab is clicked again.

    @signal currentChanged(index) emitted to indicate a change of the current
        index
    """

    Version = 4

    currentChanged = pyqtSignal(int)

    def __init__(
        self, orientation=None, iconBarSize=EricIconBar.DefaultBarSize, parent=None
    ):
        """
        Constructor

        @param orientation orientation of the sidebar widget
        @type EricSideBarSide
        @param iconBarSize size category for the bar (one of 'xs', 'sm', 'md',
            'lg', 'xl', 'xxl')
        @type str
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)

        # initial layout is done for NORTH
        self.__iconBar = EricIconBar(
            orientation=Qt.Orientation.Horizontal, barSize=iconBarSize
        )

        self.__stackedWidget = QStackedWidget(self)
        self.__stackedWidget.setContentsMargins(0, 0, 0, 0)

        self.layout = QBoxLayout(QBoxLayout.Direction.TopToBottom)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(3)
        self.layout.addWidget(self.__iconBar)
        self.layout.addWidget(self.__stackedWidget)
        self.setLayout(self.layout)

        self.__minimized = False
        self.__minSize = 0
        self.__bigSize = QSize()

        self.__orientation = EricSideBarSide.NORTH
        if orientation is None:
            orientation = EricSideBarSide.NORTH
        self.setOrientation(orientation)

        self.__iconBar.currentChanged.connect(self.__stackedWidget.setCurrentIndex)
        self.__iconBar.currentChanged.connect(self.__currentIconChanged)
        self.__iconBar.currentClicked.connect(self.__shrinkOrExpandIt)
        self.__iconBar.emptyClicked.connect(self.__shrinkOrExpandIt)

    def __shrinkIt(self):
        """
        Private method to shrink the sidebar.
        """
        self.__minimized = True
        self.__bigSize = self.size()
        if self.__orientation in (EricSideBarSide.NORTH, EricSideBarSide.SOUTH):
            self.__minSize = self.minimumSizeHint().height()
        else:
            self.__minSize = self.minimumSizeHint().width()

        self.__stackedWidget.hide()

        if self.__orientation in (EricSideBarSide.NORTH, EricSideBarSide.SOUTH):
            self.setFixedHeight(self.__iconBar.minimumSizeHint().height())
        else:
            self.setFixedWidth(self.__iconBar.minimumSizeHint().width())

    def __expandIt(self):
        """
        Private method to expand the sidebar.
        """
        self.__minimized = False
        self.__stackedWidget.show()
        self.resize(self.__bigSize)
        if self.__orientation in (EricSideBarSide.NORTH, EricSideBarSide.SOUTH):
            minSize = max(self.__minSize, self.minimumSizeHint().height())
            self.setMinimumHeight(minSize)
            self.setMaximumHeight(16777215)
        else:
            minSize = max(self.__minSize, self.minimumSizeHint().width())
            self.setMinimumWidth(minSize)
            self.setMaximumWidth(16777215)

    @pyqtSlot()
    def __shrinkOrExpandIt(self):
        """
        Private slot to shrink or expand the widget stack.
        """
        if self.isMinimized():
            self.__expandIt()
        else:
            self.__shrinkIt()

    def isMinimized(self):
        """
        Public method to check the minimized state.

        @return flag indicating the minimized state
        @rtype bool
        """
        return self.__minimized

    @pyqtSlot(int)
    def __currentIconChanged(self, index):
        """
        Private slot to handle a change of the current icon.

        @param index index of the current icon
        @type int
        """
        if self.isMinimized():
            self.__expandIt()

        self.currentChanged.emit(index)

    def addTab(self, widget, icon, label=None):
        """
        Public method to add a tab to the sidebar.

        @param widget reference to the widget to add
        @type QWidget
        @param icon reference to the icon of the widget
        @type QIcon
        @param label the label text of the widget
        @type str
        """
        self.__iconBar.addIcon(icon, label)
        self.__stackedWidget.addWidget(widget)
        if self.__orientation in (EricSideBarSide.NORTH, EricSideBarSide.SOUTH):
            self.__minSize = self.minimumSizeHint().height()
        else:
            self.__minSize = self.minimumSizeHint().width()

    def insertTab(self, index, widget, icon, label=None):
        """
        Public method to insert a tab into the sidebar.

        @param index the index to insert the tab at
        @type int
        @param widget reference to the widget to insert
        @type QWidget
        @param icon reference to the icon of the widget
        @type QIcon
        @param label the label text of the widget
        @type str
        """
        self.__iconBar.insertIcon(index, icon, label)

        self.__stackedWidget.insertWidget(index, widget)
        if self.__orientation in (EricSideBarSide.NORTH, EricSideBarSide.SOUTH):
            self.__minSize = self.minimumSizeHint().height()
        else:
            self.__minSize = self.minimumSizeHint().width()

    def removeTab(self, index):
        """
        Public method to remove a tab.

        @param index the index of the tab to remove
        @type int
        """
        self.__stackedWidget.removeWidget(self.__stackedWidget.widget(index))
        self.__iconBar.removeIcon(index)
        if self.__orientation in (EricSideBarSide.NORTH, EricSideBarSide.SOUTH):
            self.__minSize = self.minimumSizeHint().height()
        else:
            self.__minSize = self.minimumSizeHint().width()

    def setTabIcon(self, index, icon):
        """
        Public method to set the icon at the given index.

        @param index icon index
        @type int
        @param icon reference to the icon
        @type QIcon
        """
        self.__iconBar.setIcon(index, icon)

    def clear(self):
        """
        Public method to remove all tabs.
        """
        while self.count() > 0:
            self.removeTab(0)

    def prevTab(self):
        """
        Public slot used to show the previous tab.
        """
        ind = self.currentIndex() - 1
        if ind == -1:
            ind = self.count() - 1

        self.setCurrentIndex(ind)
        self.currentWidget().setFocus()

    def nextTab(self):
        """
        Public slot used to show the next tab.
        """
        ind = self.currentIndex() + 1
        if ind == self.count():
            ind = 0

        self.setCurrentIndex(ind)
        self.currentWidget().setFocus()

    def count(self):
        """
        Public method to get the number of tabs.

        @return number of tabs in the sidebar
        @rtype int
        """
        return self.__iconBar.count()

    def currentIndex(self):
        """
        Public method to get the index of the current tab.

        @return index of the current tab
        @rtype int
        """
        return self.__stackedWidget.currentIndex()

    def setCurrentIndex(self, index):
        """
        Public slot to set the current index.

        @param index the index to set as the current index
        @type int
        """
        self.__iconBar.setCurrentIndex(index)
        self.__stackedWidget.setCurrentIndex(index)
        if self.isMinimized():
            self.__expandIt()

    def currentWidget(self):
        """
        Public method to get a reference to the current widget.

        @return reference to the current widget
        @rtype QWidget
        """
        return self.__stackedWidget.currentWidget()

    def setCurrentWidget(self, widget):
        """
        Public slot to set the current widget.

        @param widget reference to the widget to become the current widget
        @type QWidget
        """
        try:
            index = self.__stackedWidget.indexOf(widget)
            if index < 0:
                # not found, set first widget as default
                index = 0
        except RuntimeError:
            index = 0
        self.setCurrentIndex(index)

    def indexOf(self, widget):
        """
        Public method to get the index of the given widget.

        @param widget reference to the widget to get the index of
        @type QWidget
        @return index of the given widget
        @rtype int
        """
        return self.__stackedWidget.indexOf(widget)

    def orientation(self):
        """
        Public method to get the orientation of the sidebar.

        @return orientation of the sidebar
        @rtype EricSideBarSide
        """
        return self.__orientation

    def setOrientation(self, orient):
        """
        Public method to set the orientation of the sidebar.

        @param orient orientation of the sidebar
        @type EricSideBarSide
        """
        if orient == EricSideBarSide.NORTH:
            self.__iconBar.setOrientation(Qt.Orientation.Horizontal)
            self.layout.setDirection(QBoxLayout.Direction.TopToBottom)
        elif orient == EricSideBarSide.EAST:
            self.__iconBar.setOrientation(Qt.Orientation.Vertical)
            self.layout.setDirection(QBoxLayout.Direction.RightToLeft)
        elif orient == EricSideBarSide.SOUTH:
            self.__iconBar.setOrientation(Qt.Orientation.Horizontal)
            self.layout.setDirection(QBoxLayout.Direction.BottomToTop)
        elif orient == EricSideBarSide.WEST:
            self.__iconBar.setOrientation(Qt.Orientation.Vertical)
            self.layout.setDirection(QBoxLayout.Direction.LeftToRight)
        self.__orientation = orient

    def widget(self, index):
        """
        Public method to get a reference to the widget associated with a tab.

        @param index index of the tab
        @type int
        @return reference to the widget
        @rtype QWidget
        """
        return self.__stackedWidget.widget(index)

    def setIconBarColor(self, color):
        """
        Public method to set the icon bar color.

        @param color icon bar color
        @type QColor
        """
        self.__iconBar.setColor(color)

    def iconBarColor(self):
        """
        Public method to get the icon bar color.

        @return icon bar color
        @rtype QColor
        """
        return self.__iconBar.color()

    def setIconBarSize(self, barSize):
        """
        Public method to set the icon bar size.

        @param barSize size category for the bar (one of 'xs', 'sm', 'md',
            'lg', 'xl', 'xxl')
        @type str
        """
        self.__iconBar.setBarSize(barSize)
        if self.isMinimized():
            self.__shrinkIt()
        else:
            self.__expandIt()

    def barSize(self):
        """
        Public method to get the icon bar size.

        @return barSize size category for the bar (one of 'xs', 'sm', 'md',
            'lg', 'xl', 'xxl')
        @rtype str
        """
        return self.__iconBar.barSize()

    def saveState(self):
        """
        Public method to save the state of the sidebar.

        @return saved state as a byte array
        @rtype QByteArray
        """
        if not self.__bigSize.isValid():
            self.__bigSize = self.size()
        if self.__orientation in (EricSideBarSide.NORTH, EricSideBarSide.SOUTH):
            self.__minSize = self.minimumSizeHint().height()
        else:
            self.__minSize = self.minimumSizeHint().width()

        dataDict = {
            "version": self.Version,
            "minimized": self.__minimized,
            "big_size": [self.__bigSize.width(), self.__bigSize.height()],
            "min_size": self.__minSize,
            "max_size": 16777215,  # maximum size for sizable widgets
        }
        data = json.dumps(dataDict)

        return data

    def restoreState(self, state):
        """
        Public method to restore the state of the sidebar.

        @param state byte array containing the saved state
        @type QByteArray
        @return flag indicating success
        @rtype bool
        """
        if not isinstance(state, str) or state == "":
            return False

        try:
            stateDict = json.loads(state)
        except json.JSONDecodeError:
            return False

        if not stateDict:
            return False

        minSize = (
            self.layout.minimumSize().height()
            if self.__orientation in (EricSideBarSide.NORTH, EricSideBarSide.SOUTH)
            else self.layout.minimumSize().width()
        )

        if stateDict["version"] in (2, 3, 4):
            if stateDict["minimized"] and not self.__minimized:
                self.__shrinkIt()

            self.__bigSize = QSize(*stateDict["big_size"])
            self.__minSize = max(stateDict["min_size"], minSize)

            if not stateDict["minimized"]:
                self.__expandIt()

            return True

        return False
