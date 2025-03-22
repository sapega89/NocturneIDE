# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a graphics item subclass for an arrow.
"""

import enum
import math

from PyQt6.QtCore import QLineF, QPointF, QRectF, QSizeF, Qt
from PyQt6.QtGui import QColor, QPen, QPolygonF
from PyQt6.QtWidgets import QAbstractGraphicsShapeItem, QGraphicsItem, QStyle

ArrowheadAngleFactor = 0.26179938779914941
# That is: 0.5 * math.atan(math.sqrt(3.0) / 3.0)


class EricArrowType(enum.Enum):
    """
    Class defining the arrow types.
    """

    NORMAL = 1
    WIDE = 2


class EricArrowItem(QAbstractGraphicsShapeItem):
    """
    Class implementing an arrow graphics item subclass.
    """

    def __init__(
        self,
        origin=None,
        end=None,
        filled=False,
        arrowType=EricArrowType.NORMAL,
        colors=None,
        parent=None,
    ):
        """
        Constructor

        @param origin origin of the arrow
        @type QPointF
        @param end end point of the arrow
        @type QPointF
        @param filled flag indicating a filled arrow head
        @type bool
        @param arrowType arrow type
        @type EricArrowType
        @param colors tuple containing the foreground and background colors
        @type tuple of (QColor, QColor)
        @param parent reference to the parent object
        @type QGraphicsItem
        """
        super().__init__(parent)

        self._origin = QPointF() if origin is None else QPointF(origin)
        self._end = QPointF() if end is None else QPointF(end)
        self._filled = filled
        self.__type = arrowType

        if colors is None:
            self._colors = (QColor(Qt.GlobalColor.black), QColor(Qt.GlobalColor.white))
        else:
            self._colors = colors

        self._halfLength = 13.0

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

    def setPoints(self, xa, ya, xb, yb):
        """
        Public method to set the start and end points of the line.

        <b>Note:</b> This method does not redraw the item.

        @param xa x-coordinate of the start point
        @type float
        @param ya y-coordinate of the start point
        @type float
        @param xb x-coordinate of the end point
        @type float
        @param yb y-coordinate of the end point
        @type float
        """
        self._origin = QPointF(xa, ya)
        self._end = QPointF(xb, yb)

    def setStartPoint(self, x, y):
        """
        Public method to set the start point.

        <b>Note:</b> This method does not redraw the item.

        @param x x-coordinate of the start point
        @type float
        @param y y-coordinate of the start point
        @type float
        """
        self._origin = QPointF(x, y)

    def setEndPoint(self, x, y):
        """
        Public method to set the end point.

        <b>Note:</b> This method does not redraw the item.

        @param x x-coordinate of the end point
        @type float
        @param y y-coordinate of the end point
        @type float
        """
        self._end = QPointF(x, y)

    def boundingRect(self):
        """
        Public method to return the bounding rectangle.

        @return bounding rectangle
        @rtype QRectF
        """
        extra = self._halfLength / 2.0
        return (
            QRectF(
                self._origin,
                QSizeF(
                    self._end.x() - self._origin.x(), self._end.y() - self._origin.y()
                ),
            )
            .normalized()
            .adjusted(-extra, -extra, extra, extra)
        )

    def paint(self, painter, option, _widget=None):
        """
        Public method to paint the item in local coordinates.

        @param painter reference to the painter object
        @type QPainter
        @param option style options
        @type QStyleOptionGraphicsItem
        @param _widget optional reference to the widget painted on (unused)
        @type QWidget
        """
        width = (
            2
            if (
                (option.state & QStyle.StateFlag.State_Selected)
                == QStyle.StateFlag.State_Selected
            )
            else 1
        )

        # draw the line first
        line = QLineF(self._origin, self._end)
        painter.setPen(
            QPen(
                self._colors[0],
                width,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.FlatCap,
                Qt.PenJoinStyle.MiterJoin,
            )
        )
        painter.drawLine(line)

        # draw the arrow head
        arrowAngle = (
            ArrowheadAngleFactor
            if self.__type == EricArrowType.NORMAL
            else 2 * ArrowheadAngleFactor
        )
        slope = math.atan2(line.dy(), line.dx())

        # Calculate left arrow point
        arrowSlope = slope + arrowAngle
        a1 = QPointF(
            self._end.x() - self._halfLength * math.cos(arrowSlope),
            self._end.y() - self._halfLength * math.sin(arrowSlope),
        )

        # Calculate right arrow point
        arrowSlope = slope - arrowAngle
        a2 = QPointF(
            self._end.x() - self._halfLength * math.cos(arrowSlope),
            self._end.y() - self._halfLength * math.sin(arrowSlope),
        )

        if self._filled:
            painter.setBrush(self._colors[0])
        else:
            painter.setBrush(self._colors[1])
        polygon = QPolygonF()
        polygon.append(line.p2())
        polygon.append(a1)
        polygon.append(a2)
        painter.drawPolygon(polygon)
