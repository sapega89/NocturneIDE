# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a Notification widget.
"""

import contextlib
import enum

from PyQt6.QtCore import QPoint, Qt, QTimer
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.SystemUtilities import OSUtilities

from .Ui_NotificationFrame import Ui_NotificationFrame


class NotificationTypes(enum.Enum):
    """
    Class implementing the notification types.
    """

    INFORMATION = 0
    WARNING = 1
    CRITICAL = 2
    OTHER = 99


class NotificationFrame(QFrame, Ui_NotificationFrame):
    """
    Class implementing a Notification widget.
    """

    NotificationStyleSheetTemplate = "color:{0};background-color:{1};"

    def __init__(
        self, icon, heading, text, kind=NotificationTypes.INFORMATION, parent=None
    ):
        """
        Constructor

        @param icon icon to be used
        @type QPixmap
        @param heading heading to be used
        @type str
        @param text text to be used
        @type str
        @param kind kind of notification to be shown
        @type NotificationTypes
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.layout().setAlignment(
            self.verticalLayout,
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        )

        self.setStyleSheet(NotificationFrame.getStyleSheet(kind))

        if icon is None:
            icon = NotificationFrame.getIcon(kind)
        self.icon.setPixmap(icon)

        self.heading.setText("<b>{0}</b>".format(heading))
        self.text.setText(text)

        self.show()
        self.adjustSize()

    @classmethod
    def getIcon(cls, kind):
        """
        Class method to get the icon for a specific notification kind.

        @param kind notification kind
        @type NotificationTypes
        @return icon for the notification kind
        @rtype QPixmap
        """
        if kind == NotificationTypes.CRITICAL:
            return EricPixmapCache.getPixmap("notificationCritical48")
        elif kind == NotificationTypes.WARNING:  # __NO-TASK__
            return EricPixmapCache.getPixmap("notificationWarning48")
        elif kind == NotificationTypes.INFORMATION:
            return EricPixmapCache.getPixmap("notificationInformation48")
        else:
            return EricPixmapCache.getPixmap("notification48")

    @classmethod
    def getStyleSheet(cls, kind):
        """
        Class method to get a style sheet for specific notification kind.

        @param kind notification kind
        @type NotificationTypes
        @return string containing the style sheet for the notification kind
        @rtype str
        """
        if kind == NotificationTypes.CRITICAL:
            return NotificationFrame.NotificationStyleSheetTemplate.format(
                Preferences.getUI("NotificationCriticalForeground"),
                Preferences.getUI("NotificationCriticalBackground"),
            )
        elif kind == NotificationTypes.WARNING:  # __NO-TASK__
            return NotificationFrame.NotificationStyleSheetTemplate.format(
                Preferences.getUI("NotificationWarningForeground"),
                Preferences.getUI("NotificationWarningBackground"),
            )
        else:
            return ""


class NotificationWidget(QWidget):
    """
    Class implementing a Notification list widget.
    """

    def __init__(self, parent=None, setPosition=False):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        @param setPosition flag indicating to set the display
            position interactively
        @type bool
        """
        super().__init__(parent)

        self.__layout = QVBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

        self.__timeout = 5000
        self.__dragPosition = QPoint()
        self.__timers = {}
        self.__notifications = []

        self.__settingPosition = setPosition

        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.X11BypassWindowManagerHint
        )
        if OSUtilities.isWindowsPlatform():
            flags |= Qt.WindowType.ToolTip
        self.setWindowFlags(flags)

        if self.__settingPosition:
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def showNotification(
        self, icon, heading, text, kind=NotificationTypes.INFORMATION, timeout=0
    ):
        """
        Public method to show a notification.

        @param icon icon to be used
        @type QPixmap
        @param heading heading to be used
        @type str
        @param text text to be used
        @type str
        @param kind kind of notification to be shown
        @type NotificationTypes
        @param timeout timeout in seconds after which the notification is
            to be removed (0 = do not remove until it is clicked on)
        @type int
        """
        notificationFrame = NotificationFrame(
            icon, heading, text, kind=kind, parent=self
        )
        self.__layout.addWidget(notificationFrame)
        self.__notifications.append(notificationFrame)

        self.show()

        self.__adjustSizeAndPosition()

        if timeout:
            timer = QTimer()
            self.__timers[id(notificationFrame)] = timer
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: self.__removeNotification(notificationFrame))
            timer.setInterval(timeout * 1000)
            timer.start()

    def __adjustSizeAndPosition(self):
        """
        Private slot to adjust the notification list widget size and position.
        """
        self.adjustSize()

        if not self.__settingPosition:
            pos = Preferences.getUI("NotificationPosition")
            screen = self.screen()
            screenGeom = screen.geometry()

            newX = pos.x()
            newY = pos.y()
            if newX < screenGeom.x():
                newX = screenGeom.x()
            if newY < screenGeom.y():
                newY = screenGeom.y()
            if newX + self.width() > screenGeom.width():
                newX = screenGeom.width() - self.width()
            if newY + self.height() > screenGeom.height():
                newY = screenGeom.height() - self.height()

            self.move(newX, newY)

    def __removeNotification(self, notification):
        """
        Private method to remove a notification from the list.

        @param notification reference to the notification to be removed
        @type NotificationFrame
        """
        notification.hide()

        # delete timer of an auto close notification
        key = id(notification)
        if key in self.__timers:
            self.__timers[key].stop()
            del self.__timers[key]

        # delete the notification
        index = self.__layout.indexOf(notification)
        self.__layout.takeAt(index)
        with contextlib.suppress(ValueError):
            self.__notifications.remove(notification)
            notification.deleteLater()

        if self.__layout.count():
            self.__adjustSizeAndPosition()
        else:
            self.hide()

    def mousePressEvent(self, evt):
        """
        Protected method to handle presses of a mouse button.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if not self.__settingPosition:
            clickedLabel = self.childAt(evt.position().toPoint())
            if clickedLabel:
                clickedNotification = clickedLabel.parent()
                self.__removeNotification(clickedNotification)
            return

        if evt.button() == Qt.MouseButton.LeftButton:
            self.__dragPosition = (
                evt.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            evt.accept()

    def mouseReleaseEvent(self, evt):
        """
        Protected method to handle releases of a mouse button.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if self.__settingPosition and evt.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseMoveEvent(self, evt):
        """
        Protected method to handle dragging the window.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if evt.buttons() & Qt.MouseButton.LeftButton:
            self.move(evt.globalPosition().toPoint() - self.__dragPosition)
            evt.accept()
