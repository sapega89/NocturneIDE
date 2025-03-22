# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a grabber object for non-Wayland desktops.
"""

from PyQt6.QtCore import QEvent, QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QGuiApplication, QPixmap
from PyQt6.QtWidgets import QWidget

from eric7.SystemUtilities import OSUtilities

from .SnapshotModes import SnapshotModes
from .SnapshotTimer import SnapshotTimer


class SnapshotDefaultGrabber(QObject):
    """
    Class implementing a grabber object for non-Wayland desktops.

    @signal grabbed(QPixmap) emitted after the grab operation is finished
    """

    grabbed = pyqtSignal(QPixmap)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__grabber = None
        self.__grabberWidget = QWidget(None, Qt.WindowType.X11BypassWindowManagerHint)
        self.__grabberWidget.move(-10000, -10000)
        self.__grabberWidget.installEventFilter(self)

        self.__grabTimer = SnapshotTimer()
        self.__grabTimer.timeout.connect(self.__grabTimerTimeout)

    def supportedModes(self):
        """
        Public method to get the supported screenshot modes.

        @return tuple of supported screenshot modes
        @rtype tuple of SnapshotModes
        """
        return (
            SnapshotModes.FULLSCREEN,
            SnapshotModes.SELECTEDSCREEN,
            SnapshotModes.RECTANGLE,
            SnapshotModes.FREEHAND,
            SnapshotModes.ELLIPSE,
        )

    def grab(self, mode, delay, _captureCursor, _captureDecorations):
        """
        Public method to perform a grab operation potentially after a delay.

        @param mode screenshot mode
        @type ScreenshotModes
        @param delay delay in seconds
        @type int
        @param _captureCursor flag indicating to include the mouse cursor (unused)
        @type bool
        @param _captureDecorations flag indicating to include the window
            decorations (unused)
        @type bool
        """
        self.__mode = mode
        if delay:
            self.__grabTimer.start(delay)
        else:
            QTimer.singleShot(200, self.__startUndelayedGrab)

    def __grabTimerTimeout(self):
        """
        Private slot to perform a delayed grab operation.
        """
        if self.__mode == SnapshotModes.RECTANGLE:
            self.__grabRectangle()
        elif self.__mode == SnapshotModes.ELLIPSE:
            self.__grabEllipse()
        elif self.__mode == SnapshotModes.FREEHAND:
            self.__grabFreehand()
        else:
            self.__performGrab(self.__mode)

    def __startUndelayedGrab(self):
        """
        Private slot to perform an undelayed grab operation.
        """
        if self.__mode == SnapshotModes.RECTANGLE:
            self.__grabRectangle()
        elif self.__mode == SnapshotModes.ELLIPSE:
            self.__grabEllipse()
        elif self.__mode == SnapshotModes.FREEHAND:
            self.__grabFreehand()
        else:
            if OSUtilities.isMacPlatform():
                self.__performGrab(self.__mode)
            else:
                self.__grabberWidget.show()
                self.__grabberWidget.grabMouse(Qt.CursorShape.CrossCursor)

    def __grabRectangle(self):
        """
        Private method to grab a rectangular screen region.
        """
        from .SnapshotRegionGrabber import SnapshotRegionGrabber

        self.__grabber = SnapshotRegionGrabber(mode=SnapshotRegionGrabber.Rectangle)
        self.__grabber.grabbed.connect(self.__captured)

    def __grabEllipse(self):
        """
        Private method to grab an elliptical screen region.
        """
        from .SnapshotRegionGrabber import SnapshotRegionGrabber

        self.__grabber = SnapshotRegionGrabber(mode=SnapshotRegionGrabber.Ellipse)
        self.__grabber.grabbed.connect(self.__captured)

    def __grabFreehand(self):
        """
        Private method to grab a non-rectangular screen region.
        """
        from .SnapshotFreehandGrabber import SnapshotFreehandGrabber

        self.__grabber = SnapshotFreehandGrabber()
        self.__grabber.grabbed.connect(self.__captured)

    def __performGrab(self, mode):
        """
        Private method to perform a screen grab other than a selected region.

        @param mode screenshot mode
        @type SnapshotModes
        """
        self.__grabberWidget.releaseMouse()
        self.__grabberWidget.hide()
        self.__grabTimer.stop()

        if mode == SnapshotModes.FULLSCREEN:
            screen = QGuiApplication.screens()[0]
            vgeom = screen.availableVirtualGeometry()
            snapshot = screen.grabWindow(
                0, vgeom.x(), vgeom.y(), vgeom.width(), vgeom.height()
            )
        elif mode == SnapshotModes.SELECTEDSCREEN:
            screen = QGuiApplication.screenAt(QCursor.pos())
            sgeom = screen.geometry()
            if OSUtilities.isMacPlatform():
                # macOS variant
                snapshot = screen.grabWindow(
                    0, sgeom.x(), sgeom.y(), sgeom.width(), sgeom.height()
                )
            else:
                # Linux variant
                # Windows variant
                snapshot = screen.grabWindow(0, 0, 0, sgeom.width(), sgeom.height())
        else:
            snapshot = QPixmap()

        self.grabbed.emit(snapshot)

    def __captured(self, pixmap):
        """
        Private slot to show a preview of the snapshot.

        @param pixmap pixmap of the snapshot
        @type QPixmap
        """
        self.__grabber.close()
        snapshot = QPixmap(pixmap)

        self.__grabber.grabbed.disconnect(self.__captured)
        self.__grabber = None

        self.grabbed.emit(snapshot)

    def eventFilter(self, obj, evt):
        """
        Public method to handle event for other objects.

        @param obj reference to the object
        @type QObject
        @param evt reference to the event
        @type QEvent
        @return flag indicating that the event should be filtered out
        @rtype bool
        """
        if obj == self.__grabberWidget and evt.type() == QEvent.Type.MouseButtonPress:
            if QWidget.mouseGrabber() != self.__grabberWidget:
                return False
            if evt.button() == Qt.MouseButton.LeftButton:
                self.__performGrab(self.__mode)

        return False
