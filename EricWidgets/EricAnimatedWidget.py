# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an animated widget.
"""

#
# Code was inspired by qupzilla web browser
#

import enum

from PyQt6.QtCore import QPoint, QTimeLine, pyqtSlot
from PyQt6.QtWidgets import QWidget


class EricAnimationDirection(enum.Enum):
    """
    Class defining the animation directions.
    """

    Down = 0
    Up = 1


class EricAnimatedWidget(QWidget):
    """
    Class implementing an animated widget.
    """

    def __init__(
        self, direction=EricAnimationDirection.Down, duration=300, parent=None
    ):
        """
        Constructor

        @param direction direction of the animation
        @type EricAnimationDirection
        @param duration duration of the animation
        @type int
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__direction = direction
        self.__stepHeight = 0.0
        self.__stepY = 0.0
        self.__startY = 0
        self.__widget = QWidget(self)

        self.__timeline = QTimeLine(duration)
        self.__timeline.setFrameRange(0, 100)
        self.__timeline.frameChanged.connect(self.__animateFrame)

        self.setMaximumHeight(0)

    def widget(self):
        """
        Public method to get a reference to the animated widget.

        @return reference to the animated widget
        @rtype QWidget
        """
        return self.__widget

    @pyqtSlot()
    def startAnimation(self):
        """
        Public slot to start the animation.
        """
        if self.__timeline.state() == QTimeLine.State.Running:
            return

        shown = 0
        hidden = 0

        if self.__direction == EricAnimationDirection.Down:
            shown = 0
            hidden = -self.__widget.height()

        self.__widget.move(QPoint(self.__widget.pos().x(), hidden))

        self.__stepY = (hidden - shown) / 100.0
        self.__startY = hidden
        self.__stepHeight = self.__widget.height() / 100.0

        self.__timeline.setDirection(QTimeLine.Direction.Forward)
        self.__timeline.start()

    @pyqtSlot(int)
    def __animateFrame(self, frame):
        """
        Private slot to animate the next frame.

        @param frame frame number
        @type int
        """
        self.setFixedHeight(int(frame * self.__stepHeight))
        self.__widget.move(self.pos().x(), int(self.__startY - frame * self.__stepY))

    @pyqtSlot()
    def hide(self):
        """
        Public slot to hide the animated widget.
        """
        if self.__timeline.state() == QTimeLine.State.Running:
            return

        self.__timeline.setDirection(QTimeLine.Direction.Backward)
        self.__timeline.finished.connect(self.close)
        self.__timeline.start()

        p = self.parentWidget()
        if p is not None:
            p.setFocus()

    def resizeEvent(self, evt):
        """
        Protected method to handle a resize event.

        @param evt reference to the event object
        @type QResizeEvent
        """
        if evt.size().width() != self.__widget.width():
            self.__widget.resize(evt.size().width(), self.__widget.height())

        super().resizeEvent(evt)
