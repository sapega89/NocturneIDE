# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the snapshot timer widget.
"""

from PyQt6.QtCore import QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPalette
from PyQt6.QtWidgets import QApplication, QToolTip, QWidget


class SnapshotTimer(QWidget):
    """
    Class implementing the snapshot timer widget.

    @signal timeout() emitted after the timer timed out
    """

    timeout = pyqtSignal()

    def __init__(self):
        """
        Constructor
        """
        super().__init__(None)

        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.X11BypassWindowManagerHint
        )

        self.__timer = QTimer()
        self.__textRect = QRect()
        self.__time = 0
        self.__length = 0
        self.__toggle = True

        # text is taken from paintEvent with maximum number plus some margin
        fmWidth = self.fontMetrics().horizontalAdvance(
            self.tr("Snapshot will be taken in %n seconds", "", 99)
        )
        self.resize(fmWidth + 6, self.fontMetrics().height() + 4)

        self.__timer.timeout.connect(self.__bell)

    def start(self, seconds):
        """
        Public method to start the timer.

        @param seconds timeout value
        @type int
        """
        screenGeom = QApplication.screens()[0].geometry()
        self.move(screenGeom.width() // 2 - self.size().width() // 2, screenGeom.top())
        self.__toggle = True
        self.__time = 0
        self.__length = seconds
        self.__timer.start(1000)
        self.show()

    def stop(self):
        """
        Public method to stop the timer.
        """
        self.setVisible(False)
        self.hide()
        self.__timer.stop()

    def __bell(self):
        """
        Private slot handling timer timeouts.
        """
        if self.__time == self.__length - 1:
            self.hide()
        else:
            if self.__time == self.__length:
                self.__timer.stop()
                self.timeout.emit()

        self.__time += 1
        self.__toggle = not self.__toggle
        self.update()

    def paintEvent(self, _evt):
        """
        Protected method handling paint events.

        @param _evt paint event (unused)
        @type QPaintEvent
        """
        painter = QPainter(self)

        if self.__time < self.__length:
            pal = QToolTip.palette()
            textBackgroundColor = pal.color(
                QPalette.ColorGroup.Active, QPalette.ColorRole.Base
            )
            if self.__toggle:
                textColor = pal.color(
                    QPalette.ColorGroup.Active, QPalette.ColorRole.Text
                )
            else:
                textColor = pal.color(
                    QPalette.ColorGroup.Active, QPalette.ColorRole.Base
                )
            painter.setPen(textColor)
            painter.setBrush(textBackgroundColor)
            helpText = self.tr(
                "Snapshot will be taken in %n seconds", "", self.__length - self.__time
            )
            textRect = painter.boundingRect(
                self.rect().adjusted(2, 2, -2, -2),
                Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextSingleLine,
                helpText,
            )
            painter.drawText(
                textRect,
                Qt.AlignmentFlag.AlignHCenter | Qt.TextFlag.TextSingleLine,
                helpText,
            )

    def enterEvent(self, _evt):
        """
        Protected method handling the mouse cursor entering the widget.

        @param _evt enter event (unused)
        @type QEvent
        """
        screenGeom = QApplication.screens()[0].geometry()
        if self.x() == screenGeom.left():
            self.move(
                screenGeom.x() + (screenGeom.width() // 2 - self.size().width() // 2),
                screenGeom.top(),
            )
        else:
            self.move(screenGeom.topLeft())
