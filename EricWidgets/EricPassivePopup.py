# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing dialog-like popup that displays messages without
interrupting the user.
"""

import enum

from PyQt6.QtCore import QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication, QFrame, QVBoxLayout


class EricPassivePopupStyle(enum.Enum):
    """
    Class defining the popup styles.
    """

    BOXED = 0  # box with no shadow
    STYLED = 1  # styled panel with no shadow
    CUSTOM = 128  # reserved for extensions


class EricPassivePopup(QFrame):
    """
    Class implementing dialog-like popup that displays messages without
    interrupting the user.

    @signal clicked emitted to indicate a mouse button click
    """

    DefaultPopupTime = 6 * 1000  # time im milliseconds

    clicked = pyqtSignal((), (QPoint,))

    def __init__(self, style=EricPassivePopupStyle.BOXED, parent=None):
        """
        Constructor

        @param style style of the popup
        @type EricPassivePopupStyle
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(None)

        self.__msgView = None
        self.__topLayout = None
        self.__hideDelay = EricPassivePopup.DefaultPopupTime
        self.__hideTimer = QTimer(self)
        self.__fixedPosition = QPoint()

        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.X11BypassWindowManagerHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        if style == EricPassivePopupStyle.STYLED:
            self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)
        else:
            # default style is Boxed - Plain
            self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.setLineWidth(2)
        self.__hideTimer.timeout.connect(self.hide)
        self.clicked.connect(self.hide)

        self.__customData = {}  # dictionary to store some custom data

    def setView(self, child):
        """
        Public method to set the message view.

        @param child reference to the widget to set as the message view
        @type QWidget
        """
        self.__msgView = child
        self.__topLayout = QVBoxLayout(self)
        self.__topLayout.addWidget(self.__msgView)
        self.__topLayout.activate()

    def view(self):
        """
        Public method to get a reference to the message view.

        @return reference to the message view
        @rtype QWidget
        """
        return self.__msgView

    def setVisible(self, visible):
        """
        Public method to show or hide the popup.

        @param visible flag indicating the visibility status
        @type bool
        """
        if not visible:
            super().setVisible(visible)
            return

        if self.size() != self.sizeHint():
            self.resize(self.sizeHint())

        if self.__fixedPosition.isNull():
            self.__positionSelf()
        else:
            self.move(self.__fixedPosition)
        super().setVisible(True)

        delay = self.__hideDelay
        if delay < 0:
            delay = EricPassivePopup.DefaultPopupTime
        if delay > 0:
            self.__hideTimer.start(delay)

    def show(self, p=None):
        """
        Public slot to show the popup.

        @param p position for the popup
        @type QPoint
        """
        if p is not None:
            self.__fixedPosition = p
        super().show()

    def setTimeout(self, delay):
        """
        Public method to set the delay for the popup is removed automatically.

        Setting the delay to 0 disables the timeout. If you're doing this, you
        may want to connect the clicked() signal to the hide() slot. Setting
        the delay to -1 makes it use the default value.

        @param delay value for the delay in milliseconds
        @type int
        """
        self.__hideDelay = delay
        if self.__hideTimer.isActive():
            if delay:
                if delay == -1:
                    delay = EricPassivePopup.DefaultPopupTime
                self.__hideTimer.start(delay)
            else:
                self.__hideTimer.stop()

    def timeout(self):
        """
        Public method to get the delay before the popup is removed
        automatically.

        @return the delay before the popup is removed automatically
        @rtype int
        """
        return self.__hideDelay

    def mouseReleaseEvent(self, evt):
        """
        Protected method to handle a mouse release event.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        self.clicked.emit()
        self.clicked.emit(evt.position().toPoint())

    def hideEvent(self, evt):
        """
        Protected method to handle the hide event.

        @param evt reference to the hide event
        @type QHideEvent
        """
        self.__hideTimer.stop()

    def __defaultArea(self):
        """
        Private method to determine the default rectangle to be passed to
        moveNear().

        @return default rectangle
        @rtype QRect
        """
        return QRect(100, 100, 200, 200)

    def __positionSelf(self):
        """
        Private method to position the popup.
        """
        self.__moveNear(self.__defaultArea())

    def __moveNear(self, target):
        """
        Private method to move the popup to be adjacent to the specified
        rectangle.

        @param target rectangle to be placed at
        @type QRect
        """
        pos = self.__calculateNearbyPoint(target)
        self.move(pos.x(), pos.y())

    def __calculateNearbyPoint(self, target):
        """
        Private method to calculate the position to place the popup near the
        specified rectangle.

        @param target rectangle to be placed at
        @type QRect
        @return position to place the popup
        @rtype QPoint
        """
        pos = target.topLeft()
        x = pos.x()
        y = pos.y()
        w = self.minimumSizeHint().width()
        h = self.minimumSizeHint().height()

        r = QApplication.screenAt(QPoint(x + w // 2, y + h // 2)).geometry()

        if x < r.center().x():
            x += target.width()
        else:
            x -= w

        # It's apparently trying to go off screen, so display it ALL at the
        # bottom.
        if (y + h) > r.bottom():
            y = r.bottom() - h

        if (x + w) > r.right():
            x = r.right() - w

        if y < r.top():
            y = r.top()

        if x < r.left():
            x = r.left()

        return QPoint(x, y)

    def setCustomData(self, key, data):
        """
        Public method to set some custom data.

        @param key key for the custom data
        @type str
        @param data data to be stored
        @type Any
        """
        self.__customData[key] = data

    def getCustomData(self, key):
        """
        Public method to get some custom data.

        @param key key for the custom data
        @type str
        @return stored data
        @rtype Any
        """
        return self.__customData[key]
