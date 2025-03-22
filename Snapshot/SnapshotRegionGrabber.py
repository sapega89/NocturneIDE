# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a grabber widget for a rectangular snapshot region.
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
    QRegion,
)
from PyQt6.QtWidgets import QToolTip, QWidget

from eric7.SystemUtilities import OSUtilities


def drawRect(painter, rect, outline, fill=None):
    """
    Module function to draw a rectangle with the given parameters.

    @param painter reference to the painter to be used
    @type QPainter
    @param rect rectangle to be drawn
    @type QRect
    @param outline color of the outline
    @type QColor
    @param fill fill color
    @type QColor
    """
    clip = QRegion(rect)
    clip = clip.subtracted(QRegion(rect.adjusted(1, 1, -1, -1)))

    painter.save()
    painter.setClipRegion(clip)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(outline)
    painter.drawRect(rect)
    if fill is not None and fill.isValid():
        painter.setClipping(False)
        painter.setBrush(fill)
        painter.drawRect(rect.adjusted(1, 1, -1, -1))
    painter.restore()


class SnapshotRegionGrabber(QWidget):
    """
    Class implementing a grabber widget for a rectangular snapshot region.

    @signal grabbed(QPixmap) emitted after the region was grabbed
    """

    grabbed = pyqtSignal(QPixmap)

    StrokeMask = 0
    FillMask = 1

    Rectangle = 0
    Ellipse = 1

    def __init__(self, mode=Rectangle):
        """
        Constructor

        @param mode region grabber mode (SnapshotRegionGrabber.Rectangle or
            SnapshotRegionGrabber.Ellipse)
        @type int
        @exception ValueError raised to indicate a bad value for the 'mode'
            parameter
        """
        super().__init__(
            None,
            Qt.WindowType.X11BypassWindowManagerHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool,
        )

        if mode not in [SnapshotRegionGrabber.Rectangle, SnapshotRegionGrabber.Ellipse]:
            raise ValueError("Bad value for 'mode' parameter.")
        self.__mode = mode

        self.__selection = QRect()
        self.__mouseDown = False
        self.__newSelection = False
        self.__handleSize = 10
        self.__mouseOverHandle = None
        self.__showHelp = True
        self.__grabbing = False
        self.__dragStartPoint = QPoint()
        self.__selectionBeforeDrag = QRect()
        self.__locale = QLocale()

        # naming conventions for handles
        # T top, B bottom, R Right, L left
        # 2 letters: a corner
        # 1 letter: the handle on the middle of the corresponding side
        self.__TLHandle = QRect(0, 0, self.__handleSize, self.__handleSize)
        self.__TRHandle = QRect(0, 0, self.__handleSize, self.__handleSize)
        self.__BLHandle = QRect(0, 0, self.__handleSize, self.__handleSize)
        self.__BRHandle = QRect(0, 0, self.__handleSize, self.__handleSize)
        self.__LHandle = QRect(0, 0, self.__handleSize, self.__handleSize)
        self.__THandle = QRect(0, 0, self.__handleSize, self.__handleSize)
        self.__RHandle = QRect(0, 0, self.__handleSize, self.__handleSize)
        self.__BHandle = QRect(0, 0, self.__handleSize, self.__handleSize)
        self.__handles = [
            self.__TLHandle,
            self.__TRHandle,
            self.__BLHandle,
            self.__BRHandle,
            self.__LHandle,
            self.__THandle,
            self.__RHandle,
            self.__BHandle,
        ]
        self.__helpTextRect = QRect()
        self.__helpText = self.tr(
            "Select a region using the mouse. To take the snapshot, press"
            " the Enter key or double click. Press Esc to quit."
        )

        self.__pixmap = QPixmap()

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

        r = QRect(self.__selection)
        if not self.__selection.isNull():
            grey = QRegion(self.rect())
            if self.__mode == SnapshotRegionGrabber.Ellipse:
                reg = QRegion(r, QRegion.RegionType.Ellipse)
            else:
                reg = QRegion(r)
            grey = grey.subtracted(reg)
            painter.setClipRegion(grey)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(overlayColor)
            painter.drawRect(self.rect())
            painter.setClipRect(self.rect())
            drawRect(painter, r, handleColor)

        if self.__showHelp:
            painter.setPen(textColor)
            painter.setBrush(textBackgroundColor)
            self.__helpTextRect = painter.boundingRect(
                self.rect().adjusted(2, 2, -2, -2),
                Qt.TextFlag.TextWordWrap,
                self.__helpText,
            ).translated(0, 0)
            self.__helpTextRect.adjust(-2, -2, 4, 2)
            drawRect(painter, self.__helpTextRect, textColor, textBackgroundColor)
            painter.drawText(
                self.__helpTextRect.adjusted(3, 3, -3, -3),
                Qt.TextFlag.TextWordWrap,
                self.__helpText,
            )

        if self.__selection.isNull():
            return

        # The grabbed region is everything which is covered by the drawn
        # rectangles (border included). This means that there is no 0px
        # selection, since a 0px wide rectangle will always be drawn as a line.
        txt = "{0}, {1} ({2} x {3})".format(
            self.__locale.toString(self.__selection.x()),
            self.__locale.toString(self.__selection.y()),
            self.__locale.toString(self.__selection.width()),
            self.__locale.toString(self.__selection.height()),
        )
        textRect = painter.boundingRect(self.rect(), Qt.AlignmentFlag.AlignLeft, txt)
        boundingRect = textRect.adjusted(-4, 0, 0, 0)

        if (
            textRect.width() < r.width() - 2 * self.__handleSize
            and textRect.height() < r.height() - 2 * self.__handleSize
            and r.width() > 100
            and r.height() > 100
        ):
            # center, unsuitable for small selections
            boundingRect.moveCenter(r.center())
            textRect.moveCenter(r.center())
        elif (
            r.y() - 3 > textRect.height()
            and r.x() + textRect.width() < self.rect().width()
        ):
            # on top, left aligned
            boundingRect.moveBottomLeft(QPoint(r.x(), r.y() - 3))
            textRect.moveBottomLeft(QPoint(r.x() + 2, r.y() - 3))
        elif r.x() - 3 > textRect.width():
            # left, top aligned
            boundingRect.moveTopRight(QPoint(r.x() - 3, r.y()))
            textRect.moveTopRight(QPoint(r.x() - 5, r.y()))
        elif (
            r.bottom() + 3 + textRect.height() < self.rect().bottom()
            and r.right() > textRect.width()
        ):
            # at bottom, right aligned
            boundingRect.moveTopRight(QPoint(r.right(), r.bottom() + 3))
            textRect.moveTopRight(QPoint(r.right() - 2, r.bottom() + 3))
        elif r.right() + textRect.width() + 3 < self.rect().width():
            # right, bottom aligned
            boundingRect.moveBottomLeft(QPoint(r.right() + 3, r.bottom()))
            textRect.moveBottomLeft(QPoint(r.right() + 5, r.bottom()))

        # If the above didn't catch it, you are running on a very
        # tiny screen...
        drawRect(painter, boundingRect, textColor, textBackgroundColor)
        painter.drawText(textRect, Qt.AlignmentFlag.AlignHCenter, txt)

        if (
            r.height() > self.__handleSize * 2 and r.width() > self.__handleSize * 2
        ) or not self.__mouseDown:
            self.__updateHandles()
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(handleColor)
            painter.setClipRegion(self.__handleMask(SnapshotRegionGrabber.StrokeMask))
            painter.drawRect(self.rect())
            handleColor.setAlpha(60)
            painter.setBrush(handleColor)
            painter.setClipRegion(self.__handleMask(SnapshotRegionGrabber.FillMask))
            painter.drawRect(self.rect())

    def resizeEvent(self, evt):
        """
        Protected method to handle resize events.

        @param evt resize event
        @type QResizeEvent
        """
        if self.__selection.isNull():
            return

        r = QRect(self.__selection)
        r.setTopLeft(self.__limitPointToRect(r.topLeft(), self.rect()))
        r.setBottomRight(self.__limitPointToRect(r.bottomRight(), self.rect()))
        if r.width() <= 1 or r.height() <= 1:
            # This just results in ugly drawing...
            self.__selection = QRect()
        else:
            self.__selection = self.__normalizeSelection(r)

    def mousePressEvent(self, evt):
        """
        Protected method to handle mouse button presses.

        @param evt mouse press event
        @type QMouseEvent
        """
        self.__showHelp = not self.__helpTextRect.contains(evt.position().toPoint())
        if evt.button() == Qt.MouseButton.LeftButton:
            self.__mouseDown = True
            self.__dragStartPoint = evt.position().toPoint()
            self.__selectionBeforeDrag = QRect(self.__selection)
            if not self.__selection.contains(evt.position().toPoint()):
                self.__newSelection = True
                self.__selection = QRect()
            else:
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif evt.button() == Qt.MouseButton.RightButton:
            self.__newSelection = False
            self.__selection = QRect()
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
                r = self.rect()
                self.__selection = self.__normalizeSelection(
                    QRect(self.__dragStartPoint, self.__limitPointToRect(p, r))
                )
            elif self.__mouseOverHandle is None:
                # moving the whole selection
                r = self.rect().normalized()
                s = self.__selectionBeforeDrag.normalized()
                p = s.topLeft() + evt.position().toPoint() - self.__dragStartPoint
                r.setBottomRight(
                    r.bottomRight() - QPoint(s.width(), s.height()) + QPoint(1, 1)
                )
                if not r.isNull() and r.isValid():
                    self.__selection.moveTo(self.__limitPointToRect(p, r))
            else:
                # dragging a handle
                r = QRect(self.__selectionBeforeDrag)
                offset = evt.position().toPoint() - self.__dragStartPoint

                if self.__mouseOverHandle in [
                    self.__TLHandle,
                    self.__THandle,
                    self.__TRHandle,
                ]:
                    r.setTop(r.top() + offset.y())

                if self.__mouseOverHandle in [
                    self.__TLHandle,
                    self.__LHandle,
                    self.__BLHandle,
                ]:
                    r.setLeft(r.left() + offset.x())

                if self.__mouseOverHandle in [
                    self.__BLHandle,
                    self.__BHandle,
                    self.__BRHandle,
                ]:
                    r.setBottom(r.bottom() + offset.y())

                if self.__mouseOverHandle in [
                    self.__TRHandle,
                    self.__RHandle,
                    self.__BRHandle,
                ]:
                    r.setRight(r.right() + offset.x())

                r.setTopLeft(self.__limitPointToRect(r.topLeft(), self.rect()))
                r.setBottomRight(self.__limitPointToRect(r.bottomRight(), self.rect()))
                self.__selection = self.__normalizeSelection(r)

            self.update()
        else:
            if self.__selection.isNull():
                return

            found = False
            for r in self.__handles:
                if r.contains(evt.position().toPoint()):
                    self.__mouseOverHandle = r
                    found = True
                    break

            if not found:
                self.__mouseOverHandle = None
                if self.__selection.contains(evt.position().toPoint()):
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
                else:
                    self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                if self.__mouseOverHandle in [self.__TLHandle, self.__BRHandle]:
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif self.__mouseOverHandle in [self.__TRHandle, self.__BLHandle]:
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
                elif self.__mouseOverHandle in [self.__LHandle, self.__RHandle]:
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif self.__mouseOverHandle in [self.__THandle, self.__BHandle]:
                    self.setCursor(Qt.CursorShape.SizeVerCursor)

    def mouseReleaseEvent(self, evt):
        """
        Protected method to handle mouse button releases.

        @param evt mouse release event
        @type QMouseEvent
        """
        self.__mouseDown = False
        self.__newSelection = False
        if self.__mouseOverHandle is None and self.__selection.contains(
            evt.position().toPoint()
        ):
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.update()

    def mouseDoubleClickEvent(self, evt):
        """
        Protected method to handle mouse double clicks.

        @param evt mouse double click event
        @type QMouseEvent
        """
        self.__grabRect()

    def keyPressEvent(self, evt):
        """
        Protected method to handle key presses.

        @param evt key press event
        @type QKeyEvent
        """
        if evt.key() == Qt.Key.Key_Escape:
            self.grabbed.emit(QPixmap())
        elif evt.key() in [Qt.Key.Key_Enter, Qt.Key.Key_Return]:
            self.__grabRect()
        else:
            evt.ignore()

    def __updateHandles(self):
        """
        Private method to update the handles.
        """
        r = QRect(self.__selection)
        s2 = self.__handleSize // 2

        self.__TLHandle.moveTopLeft(r.topLeft())
        self.__TRHandle.moveTopRight(r.topRight())
        self.__BLHandle.moveBottomLeft(r.bottomLeft())
        self.__BRHandle.moveBottomRight(r.bottomRight())

        self.__LHandle.moveTopLeft(QPoint(r.x(), r.y() + r.height() // 2 - s2))
        self.__THandle.moveTopLeft(QPoint(r.x() + r.width() // 2 - s2, r.y()))
        self.__RHandle.moveTopRight(QPoint(r.right(), r.y() + r.height() // 2 - s2))
        self.__BHandle.moveBottomLeft(QPoint(r.x() + r.width() // 2 - s2, r.bottom()))

    def __handleMask(self, maskType):
        """
        Private method to calculate the handle mask.

        @param maskType type of the mask to be used
            (SnapshotRegionGrabber.FillMask or
            SnapshotRegionGrabber.StrokeMask)
        @type int
        @return calculated mask
        @rtype QRegion
        """
        mask = QRegion()
        for rect in self.__handles:
            if maskType == SnapshotRegionGrabber.StrokeMask:
                r = QRegion(rect)
                mask += r.subtracted(QRegion(rect.adjusted(1, 1, -1, -1)))
            else:
                mask += QRegion(rect.adjusted(1, 1, -1, -1))
        return mask

    def __limitPointToRect(self, point, rect):
        """
        Private method to limit the given point to the given rectangle.

        @param point point to be limited
        @type QPoint
        @param rect rectangle the point shall be limited to
        @type QRect
        @return limited point
        @rtype QPoint
        """
        q = QPoint()
        if point.x() < rect.x():
            q.setX(rect.x())
        elif point.x() < rect.right():
            q.setX(point.x())
        else:
            q.setX(rect.right())
        if point.y() < rect.y():
            q.setY(rect.y())
        elif point.y() < rect.bottom():
            q.setY(point.y())
        else:
            q.setY(rect.bottom())
        return q

    def __normalizeSelection(self, sel):
        """
        Private method to normalize the given selection.

        @param sel selection to be normalized
        @type QRect
        @return normalized selection
        @rtype QRect
        """
        rect = QRect(sel)
        if rect.width() <= 0:
            left = rect.left()
            width = rect.width()
            rect.setLeft(left + width - 1)
            rect.setRight(left)
        if rect.height() <= 0:
            top = rect.top()
            height = rect.height()
            rect.setTop(top + height - 1)
            rect.setBottom(top)
        return rect

    def __grabRect(self):
        """
        Private method to grab the selected rectangle (i.e. do the snapshot).
        """
        if self.__mode == SnapshotRegionGrabber.Ellipse:
            ell = QRegion(self.__selection, QRegion.RegionType.Ellipse)
            if not ell.isEmpty():
                self.__grabbing = True

                xOffset = self.__pixmap.rect().x() - ell.boundingRect().x()
                yOffset = self.__pixmap.rect().y() - ell.boundingRect().y()
                translatedEll = ell.translated(xOffset, yOffset)

                pixmap2 = QPixmap(ell.boundingRect().size())
                pixmap2.fill(Qt.GlobalColor.transparent)

                pt = QPainter()
                pt.begin(pixmap2)
                if pt.paintEngine().hasFeature(
                    QPaintEngine.PaintEngineFeature.PorterDuff
                ):
                    pt.setRenderHints(
                        QPainter.RenderHint.Antialiasing
                        | QPainter.RenderHint.SmoothPixmapTransform,
                        True,
                    )
                    pt.setBrush(Qt.GlobalColor.black)
                    pt.setPen(QPen(QBrush(Qt.GlobalColor.black), 0.5))
                    pt.drawEllipse(translatedEll.boundingRect())
                    pt.setCompositionMode(
                        QPainter.CompositionMode.CompositionMode_SourceIn
                    )
                else:
                    pt.setClipRegion(translatedEll)
                    pt.setCompositionMode(
                        QPainter.CompositionMode.CompositionMode_Source
                    )

                pt.drawPixmap(pixmap2.rect(), self.__pixmap, ell.boundingRect())
                pt.end()

                self.grabbed.emit(pixmap2)
        else:
            r = QRect(self.__selection)
            if not r.isNull() and r.isValid():
                self.__grabbing = True
                self.grabbed.emit(self.__pixmap.copy(r))
