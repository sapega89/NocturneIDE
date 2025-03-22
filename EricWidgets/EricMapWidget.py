# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a base class for showing a document map.
"""

from PyQt6.QtCore import QCoreApplication, QRect, QSize, Qt
from PyQt6.QtGui import QBrush, QColor, QPainter
from PyQt6.QtWidgets import QAbstractScrollArea, QWidget


class EricMapWidget(QWidget):
    """
    Class implementing a base class for showing a document map.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

        self.__width = 14
        self.__lineBorder = 1
        self.__lineHeight = 2
        self.__backgroundColor = QColor("#e7e7e7")
        self.__setSliderColor()

        self._controller = None
        self.__enabled = False
        self.__rightSide = True

        if parent is not None and isinstance(parent, QAbstractScrollArea):
            self.setController(parent)

    def __setSliderColor(self):
        """
        Private method to set the slider color depending upon the background
        color.
        """
        if self.__backgroundColor.toHsv().value() < 128:
            # dark background, use white slider
            self.__sliderColor = Qt.GlobalColor.white
        else:
            # light background, use black slider
            self.__sliderColor = Qt.GlobalColor.black

    def __updateControllerViewportWidth(self):
        """
        Private method to update the controller's viewport width.
        """
        if self._controller:
            if self.__enabled:
                width = self.__width
            else:
                width = 0
            if self.__rightSide:
                self._controller.setViewportMargins(0, 0, width, 0)
            else:
                self._controller.setViewportMargins(width, 0, 0, 0)

    def setController(self, controller):
        """
        Public method to set the map controller widget.

        @param controller map controller widget
        @type QAbstractScrollArea
        """
        self._controller = controller
        self._controller.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOn
        )
        self._controller.verticalScrollBar().valueChanged.connect(self.update)
        self._controller.verticalScrollBar().rangeChanged.connect(self.update)
        self.__updateControllerViewportWidth()

    def setWidth(self, width):
        """
        Public method to set the widget width.

        @param width widget width
        @type int
        """
        if width != self.__width:
            self.__width = max(6, width)  # minimum width 6 pixels
            self.__updateControllerViewportWidth()
            self.update()

    def width(self):
        """
        Public method to get the widget's width.

        @return widget width
        @rtype int
        """
        return self.__width

    def setMapPosition(self, onRight):
        """
        Public method to set, whether the map should be shown to the right or
        left of the controller widget.

        @param onRight flag indicating to show the map on the right side of
            the controller widget
        @type bool
        """
        if onRight != self.__rightSide:
            self.__rightSide = onRight
            self.__updateControllerViewportWidth()
            self.update()

    def isOnRightSide(self):
        """
        Public method to test, if the map is shown on the right side of the
        controller widget.

        @return flag indicating that the map is to the right of the controller
            widget
        @rtype bool
        """
        return self.__rightSide

    def setLineDimensions(self, border, height):
        """
        Public method to set the line (indicator) dimensions.

        @param border border width on each side in x-direction
        @type int
        @param height height of the line in pixels
        @type int
        """
        if border != self.__lineBorder or height != self.__lineHeight:
            self.__lineBorder = max(1, border)  # min border 1 pixel
            self.__lineHeight = max(1, height)  # min height 1 pixel
            self.update()

    def lineDimensions(self):
        """
        Public method to get the line (indicator) dimensions.

        @return tuple with border width (integer) and line height
        @rtype int
        """
        return self.__lineBorder, self.__lineHeight

    def setEnabled(self, enable):
        """
        Public method to set the enabled state.

        @param enable flag indicating the enabled state
        @type bool
        """
        if enable != self.__enabled:
            self.__enabled = enable
            self.setVisible(enable)
            self.__updateControllerViewportWidth()

    def isEnabled(self):
        """
        Public method to check the enabled state.

        @return flag indicating the enabled state
        @rtype bool
        """
        return self.__enabled

    def setBackgroundColor(self, color):
        """
        Public method to set the widget background color.

        @param color color for the background
        @type QColor
        """
        if color != self.__backgroundColor:
            self.__backgroundColor = color
            self.__setSliderColor()
            self.update()

    def backgroundColor(self):
        """
        Public method to get the background color.

        @return background color
        @rtype QColor
        """
        return QColor(self.__backgroundColor)

    def sizeHint(self):
        """
        Public method to give an indication about the preferred size.

        @return preferred size
        @rtype QSize
        """
        return QSize(self.__width, 0)

    def paintEvent(self, event):
        """
        Protected method to handle a paint event.

        @param event paint event
        @type QPaintEvent
        """
        # step 1: fill the whole painting area
        painter = QPainter(self)
        painter.fillRect(event.rect(), self.__backgroundColor)

        # step 2: paint the indicators
        self._paintIt(painter)

        # step 3: paint the slider
        if self._controller:
            penColor = self.__sliderColor
            painter.setPen(penColor)
            brushColor = Qt.GlobalColor.transparent
            painter.setBrush(QBrush(brushColor))
            painter.drawRect(
                self.__generateSliderRange(self._controller.verticalScrollBar())
            )

    def _paintIt(self, painter):
        """
        Protected method for painting the widget's indicators.

        Note: This method should be implemented by subclasses.

        @param painter reference to the painter object
        @type QPainter
        """
        pass

    def mousePressEvent(self, event):
        """
        Protected method to handle a mouse button press.

        @param event reference to the mouse event
        @type QMouseEvent
        """
        if event.button() == Qt.MouseButton.LeftButton and self._controller:
            vsb = self._controller.verticalScrollBar()
            value = self.position2Value(event.position().toPoint().y() - 1)
            vsb.setValue(int(value - 0.5 * vsb.pageStep()))  # center on page

    def mouseMoveEvent(self, event):
        """
        Protected method to handle a mouse moves.

        @param event reference to the mouse event
        @type QMouseEvent
        """
        if event.buttons() & Qt.MouseButton.LeftButton and self._controller:
            vsb = self._controller.verticalScrollBar()
            value = self.position2Value(event.position().toPoint().y() - 1)
            vsb.setValue(int(value - 0.5 * vsb.pageStep()))  # center on page

    def wheelEvent(self, event):
        """
        Protected slot handling mouse wheel events.

        @param event reference to the wheel event
        @type QWheelEvent
        """
        isVertical = event.angleDelta().x() == 0
        if (
            self._controller
            and event.modifiers() == Qt.KeyboardModifier.NoModifier
            and isVertical
        ):
            QCoreApplication.sendEvent(self._controller.verticalScrollBar(), event)

    def calculateGeometry(self):
        """
        Public method to recalculate the map widget's geometry.
        """
        if self._controller:
            cr = self._controller.contentsRect()
            vsb = self._controller.verticalScrollBar()
            if vsb.isVisible():
                vsbw = vsb.contentsRect().width()
            else:
                vsbw = 0
            margins = self._controller.contentsMargins()
            if margins.right() > vsbw:
                vsbw = 0
            if self.__rightSide:
                self.setGeometry(
                    QRect(
                        cr.right() - self.__width - vsbw,
                        cr.top(),
                        self.__width,
                        cr.height(),
                    )
                )
            else:
                self.setGeometry(QRect(0, cr.top(), self.__width, cr.height()))
            self.update()

    def scaleFactor(self, slider=False):
        """
        Public method to determine the scrollbar's scale factor.

        @param slider flag indicating to calculate the result for the slider
        @type bool
        @return scale factor
        @rtype float
        """
        if self._controller:
            delta = 0 if slider else 2
            vsb = self._controller.verticalScrollBar()
            posHeight = vsb.height() - delta - 1
            valHeight = vsb.maximum() - vsb.minimum() + vsb.pageStep()
            return float(posHeight) / valHeight
        else:
            return 1.0

    def value2Position(self, value, slider=False):
        """
        Public method to convert a scrollbar value into a position.

        @param value value to convert
        @type int
        @param slider flag indicating to calculate the result for the slider
        @type bool
        @return position
        @rtype int
        """
        if self._controller:
            offset = 0 if slider else 1
            vsb = self._controller.verticalScrollBar()
            return int((value - vsb.minimum()) * self.scaleFactor(slider) + offset)
        else:
            return value

    def position2Value(self, position, slider=False):
        """
        Public method to convert a position into a scrollbar value.

        @param position scrollbar position to convert
        @type int
        @param slider flag indicating to calculate the result for the slider
        @type bool
        @return scrollbar value
        @rtype int
        """
        if self._controller:
            offset = 0 if slider else 1
            vsb = self._controller.verticalScrollBar()
            return vsb.minimum() + max(
                0, (position - offset) / self.scaleFactor(slider)
            )
        else:
            return position

    def generateIndicatorRect(self, position):
        """
        Public method to generate an indicator rectangle.

        @param position indicator position
        @type int
        @return indicator rectangle
        @rtype QRect
        """
        return QRect(
            self.__lineBorder,
            position - self.__lineHeight // 2,
            self.__width - self.__lineBorder,
            self.__lineHeight,
        )

    def __generateSliderRange(self, scrollbar):
        """
        Private method to generate the slider rectangle.

        @param scrollbar reference to the vertical scrollbar
        @type QScrollBar
        @return slider rectangle
        @rtype QRect
        """
        pos1 = self.value2Position(scrollbar.value(), slider=True)
        pos2 = self.value2Position(
            scrollbar.value() + scrollbar.pageStep(), slider=True
        )
        return QRect(0, pos1, self.__width - 1, pos2 - pos1)
