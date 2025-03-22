# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a grabber object for non-Wayland desktops.
"""

import contextlib
import os
import uuid

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QCursor, QPixmap
from PyQt6.QtWidgets import QApplication

try:
    from PyQt6.QtDBus import QDBusInterface, QDBusMessage

    DBusAvailable = True
except ImportError:
    DBusAvailable = False

from eric7.EricWidgets import EricMessageBox
from eric7.SystemUtilities import DesktopUtilities

from .SnapshotModes import SnapshotModes
from .SnapshotTimer import SnapshotTimer


class SnapshotWaylandGrabber(QObject):
    """
    Class implementing a grabber object for non-Wayland desktops.

    @signal grabbed(QPixmap) emitted after the grab operation is finished
    """

    grabbed = pyqtSignal(QPixmap)

    GnomeScreenShotService = "org.gnome.Shell"
    GnomeScreenShotObjectPath = "/org/gnome/Shell/Screenshot"
    GnomeScreenShotInterface = "org.gnome.Shell.Screenshot"

    KdeScreenShotService = "org.kde.KWin"
    KdeScreenShotObjectPath = "/Screenshot"
    KdeScreenShotInterface = "org.kde.kwin.Screenshot"

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__grabTimer = SnapshotTimer()
        self.__grabTimer.timeout.connect(self.__performGrab)

    def supportedModes(self):
        """
        Public method to get the supported screenshot modes.

        @return tuple of supported screenshot modes
        @rtype tuple of SnapshotModes
        """
        if DBusAvailable:
            if DesktopUtilities.isKdeDesktop():
                return (
                    SnapshotModes.FULLSCREEN,
                    SnapshotModes.SELECTEDSCREEN,
                    SnapshotModes.SELECTEDWINDOW,
                )
            elif DesktopUtilities.isGnomeDesktop():
                return (
                    SnapshotModes.FULLSCREEN,
                    SnapshotModes.SELECTEDSCREEN,
                    SnapshotModes.SELECTEDWINDOW,
                    SnapshotModes.RECTANGLE,
                )
            else:
                return ()
        else:
            return ()

    def grab(self, mode, delay=0, captureCursor=False, captureDecorations=False):
        """
        Public method to perform a grab operation potentially after a delay.

        @param mode screenshot mode
        @type ScreenshotModes
        @param delay delay in seconds
        @type int
        @param captureCursor flag indicating to include the mouse cursor
        @type bool
        @param captureDecorations flag indicating to include the window
            decorations (only used for mode SnapshotModes.SELECTEDWINDOW)
        @type bool
        """
        if not DBusAvailable:
            # just to play it safe
            self.grabbed.emit(QPixmap())
            return

        self.__mode = mode
        self.__captureCursor = captureCursor
        self.__captureDecorations = captureDecorations
        if delay:
            self.__grabTimer.start(delay)
        else:
            QTimer.singleShot(200, self.__performGrab)

    def __performGrab(self):
        """
        Private method to perform the grab operations.

        @exception RuntimeError raised to indicate an unsupported grab mode
        """
        if self.__mode not in (
            SnapshotModes.FULLSCREEN,
            SnapshotModes.SELECTEDSCREEN,
            SnapshotModes.SELECTEDWINDOW,
            SnapshotModes.RECTANGLE,
        ):
            raise RuntimeError("unsupported grab mode given")

        if self.__mode == SnapshotModes.FULLSCREEN:
            self.__grabFullscreen()
        elif self.__mode == SnapshotModes.SELECTEDSCREEN:
            self.__grabSelectedScreen()
        elif self.__mode == SnapshotModes.SELECTEDWINDOW:
            self.__grabSelectedWindow()
        else:
            self.__grabRectangle()

    def __grabFullscreen(self):
        """
        Private method to grab the complete desktop.
        """
        snapshot = QPixmap()

        if DesktopUtilities.isKdeDesktop():
            interface = QDBusInterface(
                SnapshotWaylandGrabber.KdeScreenShotService,
                SnapshotWaylandGrabber.KdeScreenShotObjectPath,
                SnapshotWaylandGrabber.KdeScreenShotInterface,
            )
            reply = interface.call("screenshotFullscreen", self.__captureCursor)
            if self.__checkReply(reply, 1):
                filename = reply.arguments()[0]
                if filename:
                    snapshot = QPixmap(filename)
                    with contextlib.suppress(OSError):
                        os.remove(filename)
        elif DesktopUtilities.isGnomeDesktop():
            path = self.__temporaryFilename()
            interface = QDBusInterface(
                SnapshotWaylandGrabber.GnomeScreenShotService,
                SnapshotWaylandGrabber.GnomeScreenShotObjectPath,
                SnapshotWaylandGrabber.GnomeScreenShotInterface,
            )
            reply = interface.call("Screenshot", self.__captureCursor, False, path)
            if self.__checkReply(reply, 2):
                filename = reply.arguments()[1]
                if filename:
                    snapshot = QPixmap(filename)
                    with contextlib.suppress(OSError):
                        os.remove(filename)

        self.grabbed.emit(snapshot)

    def __grabSelectedScreen(self):
        """
        Private method to grab a selected screen.
        """
        snapshot = QPixmap()

        if DesktopUtilities.isKdeDesktop():
            screen = QApplication.screenAt(QCursor.pos())
            try:
                screenId = QApplication.screens().index(screen)
            except ValueError:
                # default to screen 0
                screenId = 0

            # Step 2: grab the screen
            interface = QDBusInterface(
                SnapshotWaylandGrabber.KdeScreenShotService,
                SnapshotWaylandGrabber.KdeScreenShotObjectPath,
                SnapshotWaylandGrabber.KdeScreenShotInterface,
            )
            reply = interface.call("screenshotScreen", screenId, self.__captureCursor)
            if self.__checkReply(reply, 1):
                filename = reply.arguments()[0]
                if filename:
                    snapshot = QPixmap(filename)
                    with contextlib.suppress(OSError):
                        os.remove(filename)
        elif DesktopUtilities.isGnomeDesktop():
            # Step 1: grab entire desktop
            path = self.__temporaryFilename()
            interface = QDBusInterface(
                SnapshotWaylandGrabber.GnomeScreenShotService,
                SnapshotWaylandGrabber.GnomeScreenShotObjectPath,
                SnapshotWaylandGrabber.GnomeScreenShotInterface,
            )
            reply = interface.call(
                "ScreenshotWindow",
                self.__captureDecorations,
                self.__captureCursor,
                False,
                path,
            )
            if self.__checkReply(reply, 2):
                filename = reply.arguments()[1]
                if filename:
                    snapshot = QPixmap(filename)
                    with contextlib.suppress(OSError):
                        os.remove(filename)

                    # Step 2: extract the area of the screen containing
                    #         the cursor
                    if not snapshot.isNull():
                        screen = QApplication.screenAt(QCursor.pos())
                        geom = screen.geometry()
                        snapshot = snapshot.copy(geom)

        self.grabbed.emit(snapshot)

    def __grabSelectedWindow(self):
        """
        Private method to grab a selected window.
        """
        snapshot = QPixmap()

        if DesktopUtilities.isKdeDesktop():
            mask = 0
            if self.__captureDecorations:
                mask |= 1
            if self.__captureCursor:
                mask |= 2
            interface = QDBusInterface(
                SnapshotWaylandGrabber.KdeScreenShotService,
                SnapshotWaylandGrabber.KdeScreenShotObjectPath,
                SnapshotWaylandGrabber.KdeScreenShotInterface,
            )
            reply = interface.call("interactive", mask)
            if self.__checkReply(reply, 1):
                filename = reply.arguments()[0]
                if filename:
                    snapshot = QPixmap(filename)
                    with contextlib.suppress(OSError):
                        os.remove(filename)
        elif DesktopUtilities.isGnomeDesktop():
            path = self.__temporaryFilename()
            interface = QDBusInterface(
                SnapshotWaylandGrabber.GnomeScreenShotService,
                SnapshotWaylandGrabber.GnomeScreenShotObjectPath,
                SnapshotWaylandGrabber.GnomeScreenShotInterface,
            )
            reply = interface.call(
                "ScreenshotWindow",
                self.__captureDecorations,
                self.__captureCursor,
                False,
                path,
            )
            if self.__checkReply(reply, 2):
                filename = reply.arguments()[1]
                if filename:
                    snapshot = QPixmap(filename)
                    with contextlib.suppress(OSError):
                        os.remove(filename)

        self.grabbed.emit(snapshot)

    def __grabRectangle(self):
        """
        Private method to grab a rectangular desktop area.
        """
        snapshot = QPixmap()

        if DesktopUtilities.isGnomeDesktop():
            # Step 1: let the user select the area
            interface = QDBusInterface(
                "org.gnome.Shell",
                "/org/gnome/Shell/Screenshot",
                "org.gnome.Shell.Screenshot",
            )
            reply = interface.call("SelectArea")
            if self.__checkReply(reply, 4):
                x, y, width, height = reply.arguments()[:4]

                # Step 2: grab the selected area
                path = self.__temporaryFilename()
                reply = interface.call(
                    "ScreenshotArea", x, y, width, height, False, path
                )
                if self.__checkReply(reply, 2):
                    filename = reply.arguments()[1]
                    if filename:
                        snapshot = QPixmap(filename)
                        with contextlib.suppress(OSError):
                            os.remove(filename)

        self.grabbed.emit(snapshot)

    def __checkReply(self, reply, argumentsCount):
        """
        Private method to check, if a reply is valid.

        @param reply reference to the reply message
        @type QDBusMessage
        @param argumentsCount number of expected arguments
        @type int
        @return flag indicating validity
        @rtype bool
        """
        if reply.type() == QDBusMessage.MessageType.ReplyMessage:
            if len(reply.arguments()) == argumentsCount:
                return True

            EricMessageBox.warning(
                None,
                self.tr("Screenshot Error"),
                self.tr(
                    "<p>Received an unexpected number of reply arguments."
                    " Expected {0} but got {1}</p>"
                ).format(
                    argumentsCount,
                    len(reply.arguments()),
                ),
            )

        elif reply.type() == QDBusMessage.MessageType.ErrorMessage:
            EricMessageBox.warning(
                None,
                self.tr("Screenshot Error"),
                self.tr(
                    "<p>Received error <b>{0}</b> from DBus while"
                    " performing screenshot.</p><p>{1}</p>"
                ).format(
                    reply.errorName(),
                    reply.errorMessage(),
                ),
            )

        elif reply.type() == QDBusMessage.MessageType.InvalidMessage:
            EricMessageBox.warning(
                None, self.tr("Screenshot Error"), self.tr("Received an invalid reply.")
            )

        else:
            EricMessageBox.warning(
                None,
                self.tr("Screenshot Error"),
                self.tr("Received an unexpected reply."),
            )

        return False

    def __temporaryFilename(self):
        """
        Private method to generate a temporary filename.

        @return path name for a unique, temporary file
        @rtype str
        """
        return "/tmp/eric-snap-{0}.png".format(uuid.uuid4().hex)  # secok
