# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a TabWidget class substituting QTabWidget.
"""

import contextlib

from PyQt6.QtCore import QMimeData, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import QApplication, QStyle, QTabBar, QTabWidget

from eric7.EricWidgets.EricAnimatedLabel import EricAnimatedLabel


class EricWheelTabBar(QTabBar):
    """
    Class implementing a tab bar class substituting QTabBar to support wheel
    events.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self._tabWidget = parent

    def wheelEvent(self, event):
        """
        Protected slot to support wheel events.

        @param event reference to the wheel event
        @type QWheelEvent
        """
        with contextlib.suppress(AttributeError):
            delta = event.angleDelta().y()
            if delta > 0:
                self._tabWidget.prevTab()
            elif delta < 0:
                self._tabWidget.nextTab()

            event.accept()


class EricDnDTabBar(EricWheelTabBar):
    """
    Class implementing a tab bar class substituting QTabBar.

    @signal tabMoveRequested(int, int) emitted to signal a tab move request
        giving the old and new index position
    """

    tabMoveRequested = pyqtSignal(int, int)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        EricWheelTabBar.__init__(self, parent)
        self.setAcceptDrops(True)

        self.__dragStartPos = QPoint()

    def mousePressEvent(self, event):
        """
        Protected method to handle mouse press events.

        @param event reference to the mouse press event
        @type QMouseEvent
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.__dragStartPos = QPoint(event.position().toPoint())
        EricWheelTabBar.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        """
        Protected method to handle mouse move events.

        @param event reference to the mouse move event
        @type QMouseEvent
        """
        if (
            event.buttons() == Qt.MouseButton.LeftButton
            and (event.position().toPoint() - self.__dragStartPos).manhattanLength()
            > QApplication.startDragDistance()
        ):
            drag = QDrag(self)
            mimeData = QMimeData()
            index = self.tabAt(event.position().toPoint())
            mimeData.setText(self.tabText(index))
            mimeData.setData("action", b"tab-reordering")
            mimeData.setData("tabbar-id", str(id(self)).encode("utf-8"))
            drag.setMimeData(mimeData)
            drag.exec()
        EricWheelTabBar.mouseMoveEvent(self, event)

    def dragEnterEvent(self, event):
        """
        Protected method to handle drag enter events.

        @param event reference to the drag enter event
        @type QDragEnterEvent
        """
        mimeData = event.mimeData()
        formats = mimeData.formats()
        if (
            "action" in formats
            and mimeData.data("action") == b"tab-reordering"
            and "tabbar-id" in formats
            and int(mimeData.data("tabbar-id")) == id(self)
        ):
            event.acceptProposedAction()
        EricWheelTabBar.dragEnterEvent(self, event)

    def dropEvent(self, event):
        """
        Protected method to handle drop events.

        @param event reference to the drop event
        @type QDropEvent
        """
        fromIndex = self.tabAt(self.__dragStartPos)
        toIndex = self.tabAt(event.position().toPoint())
        if fromIndex != toIndex:
            self.tabMoveRequested.emit(fromIndex, toIndex)
            event.acceptProposedAction()
        EricWheelTabBar.dropEvent(self, event)


class EricTabWidget(QTabWidget):
    """
    Class implementing a tab widget class substituting QTabWidget.

    It provides slots to show the previous and next tab and give
    them the input focus and it allows to have a context menu for the tabs.

    @signal customTabContextMenuRequested(const QPoint & point, int index)
        emitted when a context menu for a tab is requested
    """

    customTabContextMenuRequested = pyqtSignal(QPoint, int)

    def __init__(self, parent=None, dnd=False):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        @param dnd flag indicating the support for Drag & Drop
        @type bool
        """
        super().__init__(parent)

        if dnd:
            if not hasattr(self, "setMovable"):
                self.__tabBar = EricDnDTabBar(self)
                self.__tabBar.tabMoveRequested.connect(self.moveTab)
                self.setTabBar(self.__tabBar)
            else:
                self.__tabBar = EricWheelTabBar(self)
                self.setTabBar(self.__tabBar)
                self.setMovable(True)
        else:
            self.__tabBar = EricWheelTabBar(self)
            self.setTabBar(self.__tabBar)

        self.__lastCurrentIndex = -1
        self.__currentIndex = -1
        self.currentChanged.connect(self.__currentChanged)

    def setCustomTabBar(self, dnd, tabBar):
        """
        Public method to set a custom tab bar.

        @param dnd flag indicating the support for Drag & Drop
        @type bool
        @param tabBar reference to the tab bar to set
        @type QTabBar
        """
        self.__tabBar = tabBar
        self.setTabBar(self.__tabBar)
        if dnd:
            if isinstance(tabBar, EricDnDTabBar):
                self.__tabBar.tabMoveRequested.connect(self.moveTab)
            else:
                self.setMovable(True)

    def __currentChanged(self, index):
        """
        Private slot to handle the currentChanged signal.

        @param index index of the current tab
        @type int
        """
        if index == -1:
            self.__lastCurrentIndex = -1
        else:
            self.__lastCurrentIndex = self.__currentIndex
        self.__currentIndex = index

    def switchTab(self):
        """
        Public slot used to switch between the current and the previous
        current tab.
        """
        if self.__lastCurrentIndex == -1 or self.__currentIndex == -1:
            return

        self.setCurrentIndex(self.__lastCurrentIndex)
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

    def prevTab(self):
        """
        Public slot used to show the previous tab.
        """
        ind = self.currentIndex() - 1
        if ind == -1:
            ind = self.count() - 1

        self.setCurrentIndex(ind)
        self.currentWidget().setFocus()

    def setTabContextMenuPolicy(self, policy):
        """
        Public method to set the context menu policy of the tab.

        @param policy context menu policy to set
        @type Qt.ContextMenuPolicy
        """
        self.tabBar().setContextMenuPolicy(policy)
        if policy == Qt.ContextMenuPolicy.CustomContextMenu:
            self.tabBar().customContextMenuRequested.connect(
                self.__handleTabCustomContextMenuRequested
            )
        else:
            self.tabBar().customContextMenuRequested.disconnect(
                self.__handleTabCustomContextMenuRequested
            )

    def __handleTabCustomContextMenuRequested(self, point):
        """
        Private slot to handle the context menu request for the tabbar.

        @param point point the context menu was requested
        @type QPoint
        """
        _tabbar = self.tabBar()
        for index in range(_tabbar.count()):
            rect = _tabbar.tabRect(index)
            if rect.contains(point):
                self.customTabContextMenuRequested.emit(
                    _tabbar.mapToParent(point), index
                )
                return

        self.customTabContextMenuRequested.emit(_tabbar.mapToParent(point), -1)

    def selectTab(self, pos):
        """
        Public method to get the index of a tab given a position.

        @param pos position determining the tab index
        @type QPoint
        @return index of the tab
        @rtype int
        """
        _tabbar = self.tabBar()
        for index in range(_tabbar.count()):
            rect = _tabbar.tabRect(index)
            if rect.contains(pos):
                return index

        return -1

    def moveTab(self, curIndex, newIndex):
        """
        Public method to move a tab to a new index.

        @param curIndex index of tab to be moved
        @type int
        @param newIndex index the tab should be moved to
        @type int
        """
        # step 1: save the tab data of tab to be moved
        toolTip = self.tabToolTip(curIndex)
        text = self.tabText(curIndex)
        icon = self.tabIcon(curIndex)
        whatsThis = self.tabWhatsThis(curIndex)
        widget = self.widget(curIndex)
        curWidget = self.currentWidget()

        # step 2: move the tab
        self.removeTab(curIndex)
        self.insertTab(newIndex, widget, icon, text)

        # step 3: set the tab data again
        self.setTabToolTip(newIndex, toolTip)
        self.setTabWhatsThis(newIndex, whatsThis)

        # step 4: set current widget
        self.setCurrentWidget(curWidget)

    def __freeSide(self):
        """
        Private method to determine the free side of a tab.

        @return free side
        @rtype QTabBar.ButtonPosition
        """
        side = self.__tabBar.style().styleHint(
            QStyle.StyleHint.SH_TabBar_CloseButtonPosition, None, None, None
        )
        side = (
            QTabBar.ButtonPosition.RightSide
            if side == QTabBar.ButtonPosition.LeftSide
            else QTabBar.ButtonPosition.LeftSide
        )
        return side

    def animationLabel(self, index, animationFile, interval=100):
        """
        Public slot to set an animated icon.

        @param index tab index
        @type int
        @param animationFile name of the file containing the animation
        @type str
        @param interval interval in milliseconds between animation frames
        @type int
        @return reference to the created label
        @rtype EricAnimatedLabel
        """
        if index == -1:
            return None

        if hasattr(self.__tabBar, "setTabButton"):
            side = self.__freeSide()
            animation = EricAnimatedLabel(
                self, animationFile=animationFile, interval=interval
            )
            self.__tabBar.setTabButton(index, side, None)
            self.__tabBar.setTabButton(index, side, animation)
            animation.start()
            return animation
        else:
            return None

    def resetAnimation(self, index):
        """
        Public slot to reset an animated icon.

        @param index tab index
        @type int
        """
        if index == -1:
            return

        if hasattr(self.__tabBar, "tabButton"):
            side = self.__freeSide()
            animation = self.__tabBar.tabButton(index, side)
            if animation is not None:
                animation.stop()
                self.__tabBar.setTabButton(index, side, None)
                del animation
