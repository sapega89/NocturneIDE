# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a grabber widget for a freehand snapshot region.
"""

from PyQt6.QtCore import QLocale, QPoint, QRect, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QGuiApplication,
    QPaintEngine,
    QPainter,
    QPalette,
    QPen,
    QPixmap,
    QPolygon,
    QRegion,
)
from PyQt6.QtWidgets import QToolTip, QWidget

from eric7.SystemUtilities import OSUtilities


def drawPolygon(painter, polygon, outline, fill=None):
    """
    Module function to draw a polygon with the given parameters.

    @param painter reference to the painter to be used
    @type QPainter
    @param polygon polygon to be drawn
    @type QPolygon
    @param outline color of the outline
    @type QColor
    @param fill fill color
    @type QColor
    """
    clip = QRegion(polygon)
    clip -= QRegion(polygon)
    pen = QPen(
        outline,
        1,
        Qt.PenStyle.SolidLine,
        Qt.PenCapStyle.SquareCap,
        Qt.PenJoinStyle.BevelJoin,
    )

    painter.save()
    painter.setClipRegion(clip)
    painter.setPen(pen)
    painter.drawPolygon(QPolygon(polygon))
    if fill and fill.isValid():
        painter.setClipping(False)
        painter.setBrush(fill or QColor())
        painter.drawPolygon(QPolygon(polygon))
    painter.restore()


class SnapshotFreehandGrabber(QWidget):
    """
    Class implementing a grabber widget for a freehand snapshot region.

    @signal grabbed(QPixmap) emitted after the region was grabbed
    """

    grabbed = pyqtSignal(QPixmap)

    def __init__(self):
        """
        Constructor
        """
        super().__init__(
            None,
            Qt.WindowType.X11BypassWindowManagerHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool,
        )

        self.__selection = QPolygon()
        self.__mouseDown = False
        self.__newSelection = False
        self.__handleSize = 10
        self.__showHelp = True
        self.__grabbing = False
        self.__dragStartPoint = QPoint()
        self.__selectionBeforeDrag = QPolygon()
        self.__locale = QLocale()

        self.__helpTextRect = QRect()
        self.__helpText = self.tr(
            "Select a region using the mouse. To take the snapshot,"
            " press the Enter key or double click. Press Esc to quit."
        )

        self.__pixmap = QPixmap()
        self.__pBefore = QPoint()

        self.setMouseTracking(True)

        QTimer.singleShot(200, self.__initialize)

    def __initialize(self):
        """
        Private slot to initialize the rest of the widget.
        """
        if OSUtilities.isMacPlatform():
            # macOS variant
            screen = QGuiApplication.screenAt(QCursor.pos())
            geom = screen.geometry()
            self.__pixmap = screen.grabWindow(
                0, geom.x(), geom.y(), geom.width(), geom.height()
            )
        else:
            # Linux variant
            # Windows variant
            screen = QGuiApplication.screens()[0]
            geom = screen.availableVirtualGeometry()
            self.__pixmap = screen.grabWindow(
                0, geom.x(), geom.y(), geom.width(), geom.height()
            )
        self.resize(self.__pixmap.size())
        self.move(geom.x(), geom.y())
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.show()

        self.grabMouse()
        self.grabKeyboard()
        self.activateWindow()

    def paintEvent(self, evt):
        """
        Protected method handling paint events.

        @param evt paint event
        @type QPaintEvent
        """
        if self.__grabbing:  # grabWindow() should just get the background
            return

        painter = QPainter(self)
        pal = QPalette(QToolTip.palette())
        font = QToolTip.font()

        handleColor = pal.color(
            QPalette.ColorGroup.Active, QPalette.ColorRole.Highlight
        )
        handleColor.setAlpha(160)
        overlayColor = QColor(0, 0, 0, 160)
        textColor = pal.color(QPalette.ColorGroup.Active, QPalette.ColorRole.Text)
        textBackgroundColor = pal.color(
            QPalette.ColorGroup.Active, QPalette.ColorRole.Base
        )
        painter.drawPixmap(0, 0, self.__pixmap)
        painter.setFont(font)

        pol = QPolygon(self.__selection)
        if not self.__selection.boundingRect().isNull():
            # Draw outline around selection.
            # Important: the 1px-wide outline is *also* part of the
            # captured free-region
            pen = QPen(
                handleColor,
                1,
                Qt.PenStyle.SolidLine,
                Qt.PenCapStyle.SquareCap,
                Qt.PenJoinStyle.BevelJoin,
            )
            painter.setPen(pen)
            painter.drawPolygon(pol)

            # Draw the grey area around the selection.
            grey = QRegion(self.rect())
            grey -= QRegion(pol)
            painter.setClipRegion(grey)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(overlayColor)
            painter.drawRect(self.rect())
            painter.setClipRect(self.rect())
            drawPolygon(painter, pol, handleColor)

        if self.__showHelp:
            painter.setPen(textColor)
            painter.setBrush(textBackgroundColor)
            self.__helpTextRect = painter.boundingRect(
                self.rect().adjusted(2, 2, -2, -2),
                Qt.TextFlag.TextWordWrap,
                self.__helpText,
            ).translated(0, 0)
            self.__helpTextRect.adjust(-2, -2, 4, 2)
            drawPolygon(painter, self.__helpTextRect, textColor, textBackgroundColor)
            painter.drawText(
                self.__helpTextRect.adjusted(3, 3, -3, -3),
                Qt.TextFlag.TextWordWrap,
                self.__helpText,
            )

        if self.__selection.isEmpty():
            return

        # The grabbed region is everything which is covered by the drawn
        # rectangles (border included). This means that there is no 0px
        # selection, since a 0px wide rectangle will always be drawn as a line.
        boundingRect = self.__selection.boundingRect()
        txt = "{0}, {1} ({2} x {3})".format(
            self.__locale.toString(boundingRect.x()),
            self.__locale.toString(boundingRect.y()),
            self.__locale.toString(boundingRect.width()),
            self.__locale.toString(boundingRect.height()),
        )
        textRect = painter.boundingRect(self.rect(), Qt.AlignmentFlag.AlignLeft, txt)
        boundingRect = textRect.adjusted(-4, 0, 0, 0)

        polBoundingRect = pol.boundingRect()
        if (
            (textRect.width() < polBoundingRect.width() - 2 * self.__handleSize)
            and (textRect.height() < polBoundingRect.height() - 2 * self.__handleSize)
            and polBoundingRect.width() > 100
            and polBoundingRect.height() > 100
        ):
            # center, unsuitable for small selections
            boundingRect.moveCenter(polBoundingRect.center())
            textRect.moveCenter(polBoundingRect.center())
        elif (
            polBoundingRect.y() - 3 > textRect.height()
            and polBoundingRect.x() + textRect.width() < self.rect().width()
        ):
            # on top, left aligned
            boundingRect.moveBottomLeft(
                QPoint(polBoundingRect.x(), polBoundingRect.y() - 3)
            )
            textRect.moveBottomLeft(
                QPoint(polBoundingRect.x() + 2, polBoundingRect.y() - 3)
            )
        elif polBoundingRect.x() - 3 > textRect.width():
            # left, top aligned
            boundingRect.moveTopRight(
                QPoint(polBoundingRect.x() - 3, polBoundingRect.y())
            )
            textRect.moveTopRight(QPoint(polBoundingRect.x() - 5, polBoundingRect.y()))
        elif (
            polBoundingRect.bottom() + 3 + textRect.height() < self.rect().bottom()
        ) and polBoundingRect.right() > textRect.width():
            # at bottom, right aligned
            boundingRect.moveTopRight(
                QPoint(polBoundingRect.right(), polBoundingRect.bottom() + 3)
            )
            textRect.moveTopRight(
                QPoint(polBoundingRect.right() - 2, polBoundingRect.bottom() + 3)
            )
        elif polBoundingRect.right() + textRect.width() + 3 < self.rect().width():
            # right, bottom aligned
            boundingRect.moveBottomLeft(
                QPoint(polBoundingRect.right() + 3, polBoundingRect.bottom())
            )
            textRect.moveBottomLeft(
                QPoint(polBoundingRect.right() + 5, polBoundingRect.bottom())
            )

        # If the above didn't catch it, you are running on a very
        # tiny screen...
        drawPolygon(painter, boundingRect, textColor, textBackgroundColor)
        painter.drawText(textRect, Qt.AlignmentFlag.AlignHCenter, txt)

        if (
            polBoundingRect.height() > self.__handleSize * 2
            and polBoundingRect.width() > self.__handleSize * 2
        ) or not self.__mouseDown:
            painter.setBrush(Qt.GlobalColor.transparent)
            painter.setClipRegion(QRegion(pol))
            painter.drawPolygon(QPolygon(self.rect()))

    def mousePressEvent(self, evt):
        """
        Protected method to handle mouse button presses.

        @param evt mouse press event
        @type QMouseEvent
        """
        self.__pBefore = evt.position().toPoint()

        self.__showHelp = not self.__helpTextRect.contains(evt.position().toPoint())
        if evt.button() == Qt.MouseButton.LeftButton:
            self.__mouseDown = True
            self.__dragStartPoint = evt.position().toPoint()
            self.__selectionBeforeDrag = QPolygon(self.__selection)
            if not self.__selection.containsPoint(
                evt.position().toPoint(), Qt.FillRule.WindingFill
            ):
                self.__newSelection = True
                self.__selection = QPolygon()
            else:
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif evt.button() == Qt.MouseButton.RightButton:
            self.__newSelection = False
            self.__selection = QPolygon()
            self.setCursor(Qt.CursorShape.CrossCursor)
        self.update()

    def mouseMoveEvent(self, evt):
        """
        Protected method to handle mouse movements.

        @param evt mouse move event
        @type QMouseEvent
        """
        shouldShowHelp = not self.__helpTextRect.contains(evt.position().toPoint())
        if shouldShowHelp != self.__showHelp:
            self.__showHelp = shouldShowHelp
            self.update()

        if self.__mouseDown:
            if self.__newSelection:
                p = evt.position().toPoint()
                self.__selection.append(p)
            else:
                # moving the whole selection
                p = evt.position().toPoint() - self.__pBefore  # Offset
                self.__pBefore = evt.position().toPoint()
                # save position for next iteration
                self.__selection.translate(p)

            self.update()
        else:
            if self.__selection.boundingRect().isEmpty():
                return

            if self.__selection.containsPoint(
                evt.position().toPoint(), Qt.FillRule.WindingFill
            ):
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)

    def mouseReleaseEvent(self, evt):
        """
        Protected method to handle mouse button releases.

        @param evt mouse release event
        @type QMouseEvent
        """
        self.__mouseDown = False
        self.__newSelection = False
        if self.__selection.containsPoint(
            evt.position().toPoint(), Qt.FillRule.WindingFill
        ):
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.update()

    def mouseDoubleClickEvent(self, evt):
        """
        Protected method to handle mouse double clicks.

        @param evt mouse double click event
        @type QMouseEvent
        """
        self.__grabRegion()

    def keyPressEvent(self, evt):
        """
        Protected method to handle key presses.

        @param evt key press event
        @type QKeyEvent
        """
        if evt.key() == Qt.Key.Key_Escape:
            self.grabbed.emit(QPixmap())
        elif evt.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]:
            self.__grabRegion()
        else:
            evt.ignore()

    def __grabRegion(self):
        """
        Private method to grab the selected region (i.e. do the snapshot).
        """
        pol = QPolygon(self.__selection)
        if not pol.isEmpty():
            self.__grabbing = True

            xOffset = self.__pixmap.rect().x() - pol.boundingRect().x()
            yOffset = self.__pixmap.rect().y() - pol.boundingRect().y()
            translatedPol = pol.translated(xOffset, yOffset)

            pixmap2 = QPixmap(pol.boundingRect().size())
            pixmap2.fill(Qt.GlobalColor.transparent)

            pt = QPainter()
            pt.begin(pixmap2)
            if pt.paintEngine().hasFeature(QPaintEngine.PaintEngineFeature.PorterDuff):
                pt.setRenderHints(
                    QPainter.RenderHint.Antialiasing
                    | QPainter.RenderHint.SmoothPixmapTransform,
                    True,
                )
                pt.setBrush(Qt.GlobalColor.black)
                pt.setPen(QPen(QBrush(Qt.GlobalColor.black), 0.5))
                pt.drawPolygon(translatedPol)
                pt.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            else:
                pt.setClipRegion(QRegion(translatedPol))
                pt.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)

            pt.drawPixmap(pixmap2.rect(), self.__pixmap, pol.boundingRect())
            pt.end()

            self.grabbed.emit(pixmap2)
