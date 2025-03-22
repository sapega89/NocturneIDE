# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a LED widget.

It was inspired by KLed.
"""

import enum

from PyQt6.QtCore import QPoint, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QPainter, QPalette, QRadialGradient
from PyQt6.QtWidgets import QWidget


class EricLedType(enum.Enum):
    """
    Class defining the LED types.
    """

    RECTANGULAR = 0
    CIRCULAR = 1


class EricLed(QWidget):
    """
    Class implementing a LED widget.
    """

    def __init__(
        self, parent=None, color=None, shape=EricLedType.CIRCULAR, rectRatio=1
    ):
        """
        Constructor

        @param parent reference to parent widget
        @type QWidget
        @param color color of the LED
        @type QColor
        @param shape shape of the LED
        @type EricLedType
        @param rectRatio ratio width to height, if shape is rectangular
        @type float
        """
        super().__init__(parent)

        if color is None:
            color = QColor("green")

        self.__led_on = True
        self.__dark_factor = 300
        self.__offcolor = color.darker(self.__dark_factor)
        self.__led_color = color
        self.__framedLed = True
        self.__shape = shape
        self.__rectRatio = rectRatio

        self.setColor(color)

    def paintEvent(self, evt):
        """
        Protected slot handling the paint event.

        @param evt paint event object
        @type QPaintEvent
        """
        if self.__shape == EricLedType.CIRCULAR:
            self.__paintRound()
        elif self.__shape == EricLedType.RECTANGULAR:
            self.__paintRectangular()

    def __getBestRoundSize(self):
        """
        Private method to calculate the width of the LED.

        @return new width of the LED
        @rtype int
        """
        width = min(self.width(), self.height())
        width -= 2  # leave one pixel border
        return width > -1 and width or 0

    def __paintRound(self):
        """
        Private method to paint a round raised LED.
        """
        # Initialize coordinates, width and height of the LED
        width = self.__getBestRoundSize()

        # Calculate the gradient for the LED
        wh = width / 2
        color = self.__led_on and self.__led_color or self.__offcolor
        gradient = QRadialGradient(wh, wh, wh, 0.8 * wh, 0.8 * wh)
        gradient.setColorAt(0.0, color.lighter(200))
        gradient.setColorAt(0.6, color)
        if self.__framedLed:
            gradient.setColorAt(0.9, color.darker())
            gradient.setColorAt(1.0, self.palette().color(QPalette.ColorRole.Dark))
        else:
            gradient.setColorAt(1.0, color.darker())

        # now do the drawing
        paint = QPainter(self)
        paint.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        paint.setBrush(QBrush(gradient))
        paint.setPen(Qt.PenStyle.NoPen)
        paint.drawEllipse(1, 1, width, width)
        paint.end()

    def __paintRectangular(self):
        """
        Private method to paint a rectangular raised LED.
        """
        # Initialize coordinates, width and height of the LED
        width = self.height() * self.__rectRatio
        left = max(0, int((self.width() - width) / 2) - 1)
        right = min(int((self.width() + width) / 2), self.width())
        height = self.height()

        # now do the drawing
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        color = self.__led_on and self.__led_color or self.__offcolor

        painter.setPen(color.lighter(200))
        painter.drawLine(left, 0, left, height - 1)
        painter.drawLine(left + 1, 0, right - 1, 0)
        if self.__framedLed:
            painter.setPen(self.palette().color(QPalette.ColorRole.Dark))
        else:
            painter.setPen(color.darker())
        painter.drawLine(left + 1, height - 1, right - 1, height - 1)
        painter.drawLine(right - 1, 1, right - 1, height - 1)
        painter.fillRect(left + 1, 1, right - 2, height - 2, QBrush(color))
        painter.end()

    def isOn(self):
        """
        Public method to return the LED state.

        @return flag indicating the light state
        @rtype bool
        """
        return self.__led_on

    def shape(self):
        """
        Public method to return the LED shape.

        @return LED shape
        @rtype EricLedType
        """
        return self.__shape

    def ratio(self):
        """
        Public method to return the LED rectangular ratio [= width / height].

        @return LED rectangular ratio
        @rtype float
        """
        return self.__rectRatio

    def color(self):
        """
        Public method to return the LED color.

        @return color of the LED
        @rtype QColor
        """
        return self.__led_color

    def setOn(self, state):
        """
        Public method to set the LED to on.

        @param state new state of the LED
        @type bool
        """
        if self.__led_on != state:
            self.__led_on = state
            self.update()

    def setShape(self, shape):
        """
        Public method to set the LED shape.

        @param shape new LED shape
        @type EricLedType
        """
        if self.__shape != shape:
            self.__shape = shape
            self.update()

    def setRatio(self, ratio):
        """
        Public method to set the LED rectangular ratio (width / height).

        @param ratio new LED rectangular ratio
        @type float
        """
        if self.__rectRatio != ratio:
            self.__rectRatio = ratio
            self.update()

    def setColor(self, color):
        """
        Public method to set the LED color.

        @param color color for the LED
        @type QColor
        """
        if self.__led_color != color:
            self.__led_color = color
            self.__offcolor = color.darker(self.__dark_factor)
            self.update()

    def setDarkFactor(self, darkfactor):
        """
        Public method to set the dark factor.

        @param darkfactor value to set for the dark factor
        @type int
        """
        if self.__dark_factor != darkfactor:
            self.__dark_factor = darkfactor
            self.__offcolor = self.__led_color.darker(darkfactor)
            self.update()

    def darkFactor(self):
        """
        Public method to return the dark factor.

        @return the current dark factor
        @rtype int
        """
        return self.__dark_factor

    def toggle(self):
        """
        Public slot to toggle the LED state.
        """
        self.setOn(not self.__led_on)

    def on(self):
        """
        Public slot to set the LED to on.
        """
        self.setOn(True)

    def off(self):
        """
        Public slot to set the LED to off.
        """
        self.setOn(False)

    def setFramed(self, framed):
        """
        Public slot to set the __framedLed attribute.

        @param framed flag indicating the framed state
        @type bool
        """
        if self.__framedLed != framed:
            self.__framedLed = framed
            self.update()

    def isFramed(self):
        """
        Public method to return the framed state.

        @return flag indicating the current framed state
        @rtype bool
        """
        return self.__framedLed

    def sizeHint(self):
        """
        Public method to give a hint about our desired size.

        @return size hint
        @rtype QSize
        """
        return QSize(18, 18)

    def minimumSizeHint(self):
        """
        Public method to give a hint about our minimum size.

        @return size hint
        @rtype QSize
        """
        return QSize(18, 18)


class EricClickableLed(EricLed):
    """
    Class implementing a clickable LED widget.

    @signal clicked(QPoint) emitted upon a click on the LED with the
        left button
    @signal middleClicked(QPoint) emitted upon a click on the LED with
        the middle button or CTRL and left button
    """

    clicked = pyqtSignal(QPoint)
    middleClicked = pyqtSignal(QPoint)

    def __init__(
        self, parent=None, color=None, shape=EricLedType.CIRCULAR, rectRatio=1
    ):
        """
        Constructor

        @param parent reference to parent widget
        @type QWidget
        @param color color of the LED
        @type QColor
        @param shape shape of the LED
        @type EricLedType
        @param rectRatio ratio width to height, if shape is rectangular
        @type float
        """
        super().__init__(parent, color, shape, rectRatio)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, evt):
        """
        Protected method handling mouse release events.

        @param evt mouse event
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            evt.position().toPoint()
        ):
            if evt.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.middleClicked.emit(evt.globalPosition().toPoint())
            else:
                self.clicked.emit(evt.globalPosition().toPoint())
        elif evt.button() == Qt.MouseButton.MiddleButton and self.rect().contains(
            evt.position().toPoint()
        ):
            self.middleClicked.emit(evt.globalPosition().toPoint())
        else:
            super().mouseReleaseEvent(evt)
