# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the icon editor grid.
"""

import enum
import os

from PyQt6.QtCore import QPoint, QRect, QSize, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QCursor,
    QImage,
    QPainter,
    QPixmap,
    QUndoCommand,
    QUndoStack,
    qAlpha,
    qGray,
    qRgba,
)
from PyQt6.QtWidgets import QApplication, QDialog, QSizePolicy, QWidget

from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp


class IconEditCommand(QUndoCommand):
    """
    Class implementing an undo command for the icon editor.
    """

    def __init__(self, grid, text, oldImage, parent=None):
        """
        Constructor

        @param grid reference to the icon editor grid
        @type IconEditorGrid
        @param text text for the undo command
        @type str
        @param oldImage copy of the icon before the changes were applied
        @type QImage
        @param parent reference to the parent command
        @type QUndoCommand
        """
        super().__init__(text, parent)

        self.__grid = grid
        self.__imageBefore = QImage(oldImage)
        self.__imageAfter = None

    def setAfterImage(self, image):
        """
        Public method to set the image after the changes were applied.

        @param image copy of the icon after the changes were applied
        @type QImage
        """
        self.__imageAfter = QImage(image)

    def undo(self):
        """
        Public method to perform the undo.
        """
        self.__grid.setIconImage(self.__imageBefore, undoRedo=True)

    def redo(self):
        """
        Public method to perform the redo.
        """
        if self.__imageAfter:
            self.__grid.setIconImage(self.__imageAfter, undoRedo=True)


class IconEditorTool(enum.IntEnum):
    """
    Class defining the edit tools.
    """

    PENCIL = 1
    RUBBER = 2
    LINE = 3
    RECTANGLE = 4
    FILLED_RECTANGLE = 5
    CIRCLE = 6
    FILLED_CIRCLE = 7
    ELLIPSE = 8
    FILLED_ELLIPSE = 9
    FILL = 10
    COLOR_PICKER = 11

    SELECT_RECTANGLE = 100
    SELECT_CIRCLE = 101


class IconEditorGrid(QWidget):
    """
    Class implementing the icon editor grid.

    @signal canRedoChanged(bool) emitted after the redo status has changed
    @signal canUndoChanged(bool) emitted after the undo status has changed
    @signal clipboardImageAvailable(bool) emitted to signal the availability
        of an image to be pasted
    @signal colorChanged(QColor) emitted after the drawing color was changed
    @signal imageChanged(bool) emitted after the image was modified
    @signal positionChanged(int, int) emitted after the cursor poition was
        changed
    @signal previewChanged(QPixmap) emitted to signal a new preview pixmap
    @signal selectionAvailable(bool) emitted to signal a change of the
        selection
    @signal sizeChanged(int, int) emitted after the size has been changed
    @signal zoomChanged(int) emitted to signal a change of the zoom value
    """

    canRedoChanged = pyqtSignal(bool)
    canUndoChanged = pyqtSignal(bool)
    clipboardImageAvailable = pyqtSignal(bool)
    colorChanged = pyqtSignal(QColor)
    imageChanged = pyqtSignal(bool)
    positionChanged = pyqtSignal(int, int)
    previewChanged = pyqtSignal(QPixmap)
    selectionAvailable = pyqtSignal(bool)
    sizeChanged = pyqtSignal(int, int)
    zoomChanged = pyqtSignal(int)

    MarkColor = QColor(255, 255, 255, 255)
    NoMarkColor = QColor(0, 0, 0, 0)

    ZoomMinimum = 100
    ZoomMaximum = 10000
    ZoomStep = 100
    ZoomDefault = 1200
    ZoomPercent = True

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setAttribute(Qt.WidgetAttribute.WA_StaticContents)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.__curColor = Qt.GlobalColor.black
        self.__zoom = 12
        self.__curTool = IconEditorTool.PENCIL
        self.__startPos = QPoint()
        self.__endPos = QPoint()
        self.__dirty = False
        self.__selecting = False
        self.__selRect = QRect()
        self.__isPasting = False
        self.__clipboardSize = QSize()
        self.__pasteRect = QRect()

        self.__undoStack = QUndoStack(self)
        self.__currentUndoCmd = None

        self.__image = QImage(32, 32, QImage.Format.Format_ARGB32)
        self.__image.fill(Qt.GlobalColor.transparent)
        self.__markImage = QImage(self.__image)
        self.__markImage.fill(self.NoMarkColor.rgba())

        self.__compositingMode = QPainter.CompositionMode.CompositionMode_SourceOver
        self.__lastPos = (-1, -1)

        self.__gridEnabled = True
        self.__selectionAvailable = False

        self.__initCursors()
        self.__initUndoTexts()

        self.setMouseTracking(True)

        self.__undoStack.canRedoChanged.connect(self.canRedoChanged)
        self.__undoStack.canUndoChanged.connect(self.canUndoChanged)
        self.__undoStack.cleanChanged.connect(self.__cleanChanged)

        self.imageChanged.connect(self.__updatePreviewPixmap)
        QApplication.clipboard().dataChanged.connect(self.__checkClipboard)

        self.__checkClipboard()

    def __initCursors(self):
        """
        Private method to initialize the various cursors.
        """
        cursorsPath = os.path.join(os.path.dirname(__file__), "cursors")

        self.__normalCursor = QCursor(Qt.CursorShape.ArrowCursor)

        pix = QPixmap(os.path.join(cursorsPath, "colorpicker-cursor.xpm"))
        mask = pix.createHeuristicMask()
        pix.setMask(mask)
        self.__colorPickerCursor = QCursor(pix, 1, 21)

        pix = QPixmap(os.path.join(cursorsPath, "paintbrush-cursor.xpm"))
        mask = pix.createHeuristicMask()
        pix.setMask(mask)
        self.__paintCursor = QCursor(pix, 0, 19)

        pix = QPixmap(os.path.join(cursorsPath, "fill-cursor.xpm"))
        mask = pix.createHeuristicMask()
        pix.setMask(mask)
        self.__fillCursor = QCursor(pix, 3, 20)

        pix = QPixmap(os.path.join(cursorsPath, "aim-cursor.xpm"))
        mask = pix.createHeuristicMask()
        pix.setMask(mask)
        self.__aimCursor = QCursor(pix, 10, 10)

        pix = QPixmap(os.path.join(cursorsPath, "eraser-cursor.xpm"))
        mask = pix.createHeuristicMask()
        pix.setMask(mask)
        self.__rubberCursor = QCursor(pix, 1, 16)

    def __initUndoTexts(self):
        """
        Private method to initialize texts to be associated with undo commands
        for the various drawing tools.
        """
        self.__undoTexts = {
            IconEditorTool.PENCIL: self.tr("Set Pixel"),
            IconEditorTool.RUBBER: self.tr("Erase Pixel"),
            IconEditorTool.LINE: self.tr("Draw Line"),
            IconEditorTool.RECTANGLE: self.tr("Draw Rectangle"),
            IconEditorTool.FILLED_RECTANGLE: self.tr("Draw Filled Rectangle"),
            IconEditorTool.CIRCLE: self.tr("Draw Circle"),
            IconEditorTool.FILLED_CIRCLE: self.tr("Draw Filled Circle"),
            IconEditorTool.ELLIPSE: self.tr("Draw Ellipse"),
            IconEditorTool.FILLED_ELLIPSE: self.tr("Draw Filled Ellipse"),
            IconEditorTool.FILL: self.tr("Fill Region"),
        }

    def isDirty(self):
        """
        Public method to check the dirty status.

        @return flag indicating a modified status
        @rtype bool
        """
        return self.__dirty

    def setDirty(self, dirty, setCleanState=False):
        """
        Public slot to set the dirty flag.

        @param dirty flag indicating the new modification status
        @type bool
        @param setCleanState flag indicating to set the undo stack to clean
        @type bool
        """
        self.__dirty = dirty
        self.imageChanged.emit(dirty)

        if not dirty and setCleanState:
            self.__undoStack.setClean()

    def sizeHint(self):
        """
        Public method to report the size hint.

        @return size hint
        @rtype QSize
        """
        size = self.__zoom * self.__image.size()
        if self.__zoom >= 3 and self.__gridEnabled:
            size += QSize(1, 1)
        return size

    def setPenColor(self, newColor):
        """
        Public method to set the drawing color.

        @param newColor reference to the new color
        @type QColor
        """
        self.__curColor = QColor(newColor)
        self.colorChanged.emit(QColor(newColor))

    def penColor(self):
        """
        Public method to get the current drawing color.

        @return current drawing color
        @rtype QColor
        """
        return QColor(self.__curColor)

    def setCompositingMode(self, mode):
        """
        Public method to set the compositing mode.

        @param mode compositing mode to set
        @type QPainter.CompositionMode
        """
        self.__compositingMode = mode

    def compositingMode(self):
        """
        Public method to get the compositing mode.

        @return compositing mode
        @rtype QPainter.CompositionMode
        """
        return self.__compositingMode

    def setTool(self, tool):
        """
        Public method to set the current drawing tool.

        @param tool drawing tool to be used
        @type IconEditorTool
        """
        self.__curTool = tool
        self.__lastPos = (-1, -1)

        if self.__curTool in [
            IconEditorTool.SELECT_RECTANGLE,
            IconEditorTool.SELECT_CIRCLE,
        ]:
            self.__selecting = True
        else:
            self.__selecting = False

        if self.__curTool in [
            IconEditorTool.SELECT_RECTANGLE,
            IconEditorTool.SELECT_CIRCLE,
            IconEditorTool.LINE,
            IconEditorTool.RECTANGLE,
            IconEditorTool.FILLED_RECTANGLE,
            IconEditorTool.CIRCLE,
            IconEditorTool.FILLED_CIRCLE,
            IconEditorTool.ELLIPSE,
            IconEditorTool.FILLED_ELLIPSE,
        ]:
            self.setCursor(self.__aimCursor)
        elif self.__curTool == IconEditorTool.FILL:
            self.setCursor(self.__fillCursor)
        elif self.__curTool == IconEditorTool.COLOR_PICKER:
            self.setCursor(self.__colorPickerCursor)
        elif self.__curTool == IconEditorTool.PENCIL:
            self.setCursor(self.__paintCursor)
        elif self.__curTool == IconEditorTool.RUBBER:
            self.setCursor(self.__rubberCursor)
        else:
            self.setCursor(self.__normalCursor)

    def tool(self):
        """
        Public method to get the current drawing tool.

        @return current drawing tool
        @rtype IconEditorTool
        """
        return self.__curTool

    def setIconImage(self, newImage, undoRedo=False, clearUndo=False):
        """
        Public method to set a new icon image.

        @param newImage reference to the new image
        @type QImage
        @param undoRedo flag indicating an undo or redo operation
        @type bool
        @param clearUndo flag indicating to clear the undo stack
        @type bool
        """
        if newImage != self.__image:
            self.__image = newImage.convertToFormat(QImage.Format.Format_ARGB32)
            self.update()
            self.updateGeometry()
            self.resize(self.sizeHint())

            self.__markImage = QImage(self.__image)
            self.__markImage.fill(self.NoMarkColor.rgba())

            if undoRedo:
                self.setDirty(not self.__undoStack.isClean())
            else:
                self.setDirty(False)

            if clearUndo:
                self.__undoStack.clear()

            self.sizeChanged.emit(*self.iconSize())

    def iconImage(self):
        """
        Public method to get a copy of the icon image.

        @return copy of the icon image
        @rtype QImage
        """
        return QImage(self.__image)

    def iconSize(self):
        """
        Public method to get the size of the icon.

        @return width and height of the image as a tuple
        @rtype tuple of (int, int)
        """
        return self.__image.width(), self.__image.height()

    def setZoomFactor(self, newZoom):
        """
        Public method to set the zoom factor in percent.

        @param newZoom zoom factor (>= 100)
        @type int
        """
        newZoom = max(100, newZoom)  # must not be less than 100
        if newZoom != self.__zoom:
            self.__zoom = newZoom // 100
            self.update()
            self.updateGeometry()
            self.resize(self.sizeHint())
            self.zoomChanged.emit(int(self.__zoom * 100))

    def zoomFactor(self):
        """
        Public method to get the current zoom factor in percent.

        @return zoom factor
        @rtype int
        """
        return self.__zoom * 100

    def setGridEnabled(self, enable):
        """
        Public method to enable the display of grid lines.

        @param enable enabled status of the grid lines
        @type bool
        """
        if enable != self.__gridEnabled:
            self.__gridEnabled = enable
            self.update()

    def isGridEnabled(self):
        """
        Public method to get the grid lines status.

        @return enabled status of the grid lines
        @rtype bool
        """
        return self.__gridEnabled

    def paintEvent(self, evt):
        """
        Protected method called to repaint some of the widget.

        @param evt reference to the paint event object
        @type QPaintEvent
        """
        painter = QPainter(self)

        if self.__zoom >= 3 and self.__gridEnabled:
            if ericApp().usesDarkPalette():
                painter.setPen(self.palette().window().color())
            else:
                painter.setPen(self.palette().windowText().color())
            i = 0
            while i <= self.__image.width():
                painter.drawLine(
                    self.__zoom * i,
                    0,
                    self.__zoom * i,
                    self.__zoom * self.__image.height(),
                )
                i += 1
            j = 0
            while j <= self.__image.height():
                painter.drawLine(
                    0,
                    self.__zoom * j,
                    self.__zoom * self.__image.width(),
                    self.__zoom * j,
                )
                j += 1

        col = QColor("#aaa")
        painter.setPen(Qt.PenStyle.DashLine)
        for i in range(0, self.__image.width()):
            for j in range(0, self.__image.height()):
                rect = self.__pixelRect(i, j)
                if evt.region().intersects(rect):
                    color = QColor.fromRgba(self.__image.pixel(i, j))
                    painter.fillRect(rect, QBrush(Qt.GlobalColor.white))
                    painter.fillRect(QRect(rect.topLeft(), rect.center()), col)
                    painter.fillRect(QRect(rect.center(), rect.bottomRight()), col)
                    painter.fillRect(rect, QBrush(color))

                    if self.__isMarked(i, j):
                        painter.drawRect(rect.adjusted(0, 0, -1, -1))

        painter.end()

    def __pixelRect(self, i, j):
        """
        Private method to determine the rectangle for a given pixel coordinate.

        @param i x-coordinate of the pixel in the image
        @type int
        @param j y-coordinate of the pixel in the image
        @type int
        @return rectangle for the given pixel coordinates
        @rtype QRect
        """
        if self.__zoom >= 3 and self.__gridEnabled:
            return QRect(
                self.__zoom * i + 1,
                self.__zoom * j + 1,
                self.__zoom - 1,
                self.__zoom - 1,
            )
        else:
            return QRect(self.__zoom * i, self.__zoom * j, self.__zoom, self.__zoom)

    def mousePressEvent(self, evt):
        """
        Protected method to handle mouse button press events.

        @param evt reference to the mouse event object
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.LeftButton:
            if self.__isPasting:
                self.__isPasting = False
                self.editPaste(True)
                self.__markImage.fill(self.NoMarkColor.rgba())
                self.update(self.__pasteRect)
                self.__pasteRect = QRect()
                return

            if self.__curTool == IconEditorTool.PENCIL:
                cmd = IconEditCommand(
                    self, self.__undoTexts[self.__curTool], self.__image
                )
                self.__setImagePixel(evt.position().toPoint(), True)
                self.setDirty(True)
                self.__undoStack.push(cmd)
                self.__currentUndoCmd = cmd
            elif self.__curTool == IconEditorTool.RUBBER:
                cmd = IconEditCommand(
                    self, self.__undoTexts[self.__curTool], self.__image
                )
                self.__setImagePixel(evt.position().toPoint(), False)
                self.setDirty(True)
                self.__undoStack.push(cmd)
                self.__currentUndoCmd = cmd
            elif self.__curTool == IconEditorTool.FILL:
                i, j = self.__imageCoordinates(evt.position().toPoint())
                col = QColor()
                col.setRgba(self.__image.pixel(i, j))
                cmd = IconEditCommand(
                    self, self.__undoTexts[self.__curTool], self.__image
                )
                self.__drawFlood(i, j, col)
                self.setDirty(True)
                self.__undoStack.push(cmd)
                cmd.setAfterImage(self.__image)
            elif self.__curTool == IconEditorTool.COLOR_PICKER:
                i, j = self.__imageCoordinates(evt.position().toPoint())
                col = QColor()
                col.setRgba(self.__image.pixel(i, j))
                self.setPenColor(col)
            else:
                self.__unMark()
                self.__startPos = evt.position().toPoint()
                self.__endPos = evt.position().toPoint()

    def mouseMoveEvent(self, evt):
        """
        Protected method to handle mouse move events.

        @param evt reference to the mouse event object
        @type QMouseEvent
        """
        self.positionChanged.emit(*self.__imageCoordinates(evt.position().toPoint()))

        if self.__isPasting and not (evt.buttons() & Qt.MouseButton.LeftButton):
            self.__drawPasteRect(evt.position().toPoint())
            return

        if evt.buttons() & Qt.MouseButton.LeftButton:
            if self.__curTool == IconEditorTool.PENCIL:
                self.__setImagePixel(evt.position().toPoint(), True)
                self.setDirty(True)
            elif self.__curTool == IconEditorTool.RUBBER:
                self.__setImagePixel(evt.position().toPoint(), False)
                self.setDirty(True)
            elif self.__curTool in [IconEditorTool.FILL, IconEditorTool.COLOR_PICKER]:
                pass  # do nothing
            else:
                self.__drawTool(evt.position().toPoint(), True)

    def mouseReleaseEvent(self, evt):
        """
        Protected method to handle mouse button release events.

        @param evt reference to the mouse event object
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.LeftButton:
            if (
                self.__curTool in [IconEditorTool.PENCIL, IconEditorTool.RUBBER]
                and self.__currentUndoCmd
            ):
                self.__currentUndoCmd.setAfterImage(self.__image)
                self.__currentUndoCmd = None

            if self.__curTool not in [
                IconEditorTool.PENCIL,
                IconEditorTool.RUBBER,
                IconEditorTool.FILL,
                IconEditorTool.COLOR_PICKER,
                IconEditorTool.SELECT_RECTANGLE,
                IconEditorTool.SELECT_CIRCLE,
            ]:
                cmd = IconEditCommand(
                    self, self.__undoTexts[self.__curTool], self.__image
                )
                if self.__drawTool(evt.position().toPoint(), False):
                    self.__undoStack.push(cmd)
                    cmd.setAfterImage(self.__image)
                    self.setDirty(True)

    def __setImagePixel(self, pos, opaque):
        """
        Private slot to set or erase a pixel.

        @param pos position of the pixel in the widget
        @type QPoint
        @param opaque flag indicating a set operation
        @type bool
        """
        i, j = self.__imageCoordinates(pos)

        if self.__image.rect().contains(i, j) and (i, j) != self.__lastPos:
            if opaque:
                painter = QPainter(self.__image)
                painter.setPen(self.penColor())
                painter.setCompositionMode(self.__compositingMode)
                painter.drawPoint(i, j)
            else:
                self.__image.setPixel(i, j, qRgba(0, 0, 0, 0))
            self.__lastPos = (i, j)

            self.update(self.__pixelRect(i, j))

    def __imageCoordinates(self, pos):
        """
        Private method to convert from widget to image coordinates.

        @param pos widget coordinate
        @type QPoint
        @return tuple with the image coordinates
        @rtype tuple of (int, int)
        """
        i = pos.x() // self.__zoom
        j = pos.y() // self.__zoom
        return i, j

    def __drawPasteRect(self, pos):
        """
        Private slot to draw a rectangle for signaling a paste operation.

        @param pos widget position of the paste rectangle
        @type QPoint
        """
        self.__markImage.fill(self.NoMarkColor.rgba())
        if self.__pasteRect.isValid():
            self.__updateImageRect(
                self.__pasteRect.topLeft(),
                self.__pasteRect.bottomRight() + QPoint(1, 1),
            )

        x, y = self.__imageCoordinates(pos)
        isize = self.__image.size()
        sx = (
            self.__clipboardSize.width()
            if x + self.__clipboardSize.width() <= isize.width()
            else isize.width() - x
        )
        sy = (
            self.__clipboardSize.height()
            if y + self.__clipboardSize.height() <= isize.height()
            else isize.height() - y
        )

        self.__pasteRect = QRect(QPoint(x, y), QSize(sx - 1, sy - 1))

        painter = QPainter(self.__markImage)
        painter.setPen(self.MarkColor)
        painter.drawRect(self.__pasteRect)
        painter.end()

        self.__updateImageRect(
            self.__pasteRect.topLeft(), self.__pasteRect.bottomRight() + QPoint(1, 1)
        )

    def __drawTool(self, pos, mark):
        """
        Private method to perform a draw operation depending of the current
        tool.

        @param pos widget coordinate to perform the draw operation at
        @type QPoint
        @param mark flag indicating a mark operation
        @type bool
        @return flag indicating a successful draw
        @rtype bool
        """
        self.__unMark()

        if mark:
            self.__endPos = QPoint(pos)
            drawColor = self.MarkColor
            img = self.__markImage
        else:
            drawColor = self.penColor()
            img = self.__image

        start = QPoint(*self.__imageCoordinates(self.__startPos))
        end = QPoint(*self.__imageCoordinates(pos))

        painter = QPainter(img)
        painter.setPen(drawColor)
        painter.setCompositionMode(self.__compositingMode)

        if self.__curTool == IconEditorTool.LINE:
            painter.drawLine(start, end)

        elif self.__curTool in [
            IconEditorTool.RECTANGLE,
            IconEditorTool.FILLED_RECTANGLE,
            IconEditorTool.SELECT_RECTANGLE,
        ]:
            left = min(start.x(), end.x())
            top = min(start.y(), end.y())
            right = max(start.x(), end.x())
            bottom = max(start.y(), end.y())
            if self.__curTool == IconEditorTool.SELECT_RECTANGLE:
                painter.setBrush(QBrush(drawColor))
            if self.__curTool == IconEditorTool.FILLED_RECTANGLE:
                for y in range(top, bottom + 1):
                    painter.drawLine(left, y, right, y)
            else:
                painter.drawRect(left, top, right - left, bottom - top)
            if self.__selecting:
                self.__selRect = QRect(left, top, right - left + 1, bottom - top + 1)
                self.__selectionAvailable = True
                self.selectionAvailable.emit(True)

        elif self.__curTool in [
            IconEditorTool.CIRCLE,
            IconEditorTool.FILLED_CIRCLE,
            IconEditorTool.SELECT_CIRCLE,
        ]:
            deltaX = abs(start.x() - end.x())
            deltaY = abs(start.y() - end.y())
            r = max(deltaX, deltaY)
            if self.__curTool in [
                IconEditorTool.FILLED_CIRCLE,
                IconEditorTool.SELECT_CIRCLE,
            ]:
                painter.setBrush(QBrush(drawColor))
            painter.drawEllipse(start, r, r)
            if self.__selecting:
                self.__selRect = QRect(
                    start.x() - r, start.y() - r, 2 * r + 1, 2 * r + 1
                )
                self.__selectionAvailable = True
                self.selectionAvailable.emit(True)

        elif self.__curTool in [IconEditorTool.ELLIPSE, IconEditorTool.FILLED_ELLIPSE]:
            r1 = abs(start.x() - end.x())
            r2 = abs(start.y() - end.y())
            if r1 == 0 or r2 == 0:
                return False
            if self.__curTool == IconEditorTool.FILLED_ELLIPSE:
                painter.setBrush(QBrush(drawColor))
            painter.drawEllipse(start, r1, r2)

        painter.end()

        if self.__curTool in [
            IconEditorTool.CIRCLE,
            IconEditorTool.FILLED_CIRCLE,
            IconEditorTool.ELLIPSE,
            IconEditorTool.FILLED_ELLIPSE,
        ]:
            self.update()
        else:
            self.__updateRect(self.__startPos, pos)

        return True

    def __drawFlood(self, i, j, oldColor, doUpdate=True):
        """
        Private method to perform a flood fill operation.

        @param i x-value in image coordinates
        @type int
        @param j y-value in image coordinates
        @type int
        @param oldColor reference to the color at position i, j
        @type QColor
        @param doUpdate flag indicating an update is requested
            (used for speed optimizations)
        @type bool
        """
        if (
            not self.__image.rect().contains(i, j)
            or self.__image.pixel(i, j) != oldColor.rgba()
            or self.__image.pixel(i, j) == self.penColor().rgba()
        ):
            return

        self.__image.setPixel(i, j, self.penColor().rgba())

        self.__drawFlood(i, j - 1, oldColor, False)
        self.__drawFlood(i, j + 1, oldColor, False)
        self.__drawFlood(i - 1, j, oldColor, False)
        self.__drawFlood(i + 1, j, oldColor, False)

        if doUpdate:
            self.update()

    def __updateRect(self, pos1, pos2):
        """
        Private slot to update parts of the widget.

        @param pos1 top, left position for the update in widget coordinates
        @type QPoint
        @param pos2 bottom, right position for the update in widget
            coordinates
        @type QPoint
        """
        self.__updateImageRect(
            QPoint(*self.__imageCoordinates(pos1)),
            QPoint(*self.__imageCoordinates(pos2)),
        )

    def __updateImageRect(self, ipos1, ipos2):
        """
        Private slot to update parts of the widget.

        @param ipos1 top, left position for the update in image coordinates
        @type QPoint
        @param ipos2 bottom, right position for the update in image
            coordinates
        @type QPoint
        """
        r1 = self.__pixelRect(ipos1.x(), ipos1.y())
        r2 = self.__pixelRect(ipos2.x(), ipos2.y())

        left = min(r1.x(), r2.x())
        top = min(r1.y(), r2.y())
        right = max(r1.x() + r1.width(), r2.x() + r2.width())
        bottom = max(r1.y() + r1.height(), r2.y() + r2.height())
        self.update(left, top, right - left + 1, bottom - top + 1)

    def __unMark(self):
        """
        Private slot to remove the mark indicator.
        """
        self.__markImage.fill(self.NoMarkColor.rgba())
        if self.__curTool in [
            IconEditorTool.CIRCLE,
            IconEditorTool.FILLED_CIRCLE,
            IconEditorTool.ELLIPSE,
            IconEditorTool.FILLED_ELLIPSE,
            IconEditorTool.SELECT_CIRCLE,
        ]:
            self.update()
        else:
            self.__updateRect(self.__startPos, self.__endPos)

        if self.__selecting:
            self.__selRect = QRect()
            self.__selectionAvailable = False
            self.selectionAvailable.emit(False)

    def __isMarked(self, i, j):
        """
        Private method to check, if a pixel is marked.

        @param i x-value in image coordinates
        @type int
        @param j y-value in image coordinates
        @type int
        @return flag indicating a marked pixel
        @rtype bool
        """
        return self.__markImage.pixel(i, j) == self.MarkColor.rgba()

    def __updatePreviewPixmap(self):
        """
        Private slot to generate and signal an updated preview pixmap.
        """
        p = QPixmap.fromImage(self.__image)
        self.previewChanged.emit(p)

    def previewPixmap(self):
        """
        Public method to generate a preview pixmap.

        @return preview pixmap
        @rtype QPixmap
        """
        p = QPixmap.fromImage(self.__image)
        return p

    def __checkClipboard(self):
        """
        Private slot to check, if the clipboard contains a valid image, and
        signal the result.
        """
        ok = self.__clipboardImage()[1]
        self.__clipboardImageAvailable = ok
        self.clipboardImageAvailable.emit(ok)

    def canPaste(self):
        """
        Public slot to check the availability of the paste operation.

        @return flag indicating availability of paste
        @rtype bool
        """
        return self.__clipboardImageAvailable

    def __clipboardImage(self):
        """
        Private method to get an image from the clipboard.

        @return tuple with the image (QImage) and a flag indicating a
            valid image
        @rtype bool
        """
        img = QApplication.clipboard().image()
        ok = not img.isNull()
        if ok:
            img = img.convertToFormat(QImage.Format.Format_ARGB32)

        return img, ok

    def __getSelectionImage(self, cut):
        """
        Private method to get an image from the selection.

        @param cut flag indicating to cut the selection
        @type bool
        @return image of the selection
        @rtype QImage
        """
        if cut:
            cmd = IconEditCommand(self, self.tr("Cut Selection"), self.__image)

        img = QImage(self.__selRect.size(), QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        for i in range(0, self.__selRect.width()):
            for j in range(0, self.__selRect.height()):
                if self.__image.rect().contains(
                    self.__selRect.x() + i, self.__selRect.y() + j
                ) and self.__isMarked(self.__selRect.x() + i, self.__selRect.y() + j):
                    img.setPixel(
                        i,
                        j,
                        self.__image.pixel(
                            self.__selRect.x() + i, self.__selRect.y() + j
                        ),
                    )
                    if cut:
                        self.__image.setPixel(
                            self.__selRect.x() + i,
                            self.__selRect.y() + j,
                            Qt.GlobalColor.transparent,
                        )

        if cut:
            self.__undoStack.push(cmd)
            cmd.setAfterImage(self.__image)

        self.__unMark()

        if cut:
            self.update(self.__selRect)

        return img

    def editCopy(self):
        """
        Public slot to copy the selection.
        """
        if self.__selRect.isValid():
            img = self.__getSelectionImage(False)
            QApplication.clipboard().setImage(img)

    def editCut(self):
        """
        Public slot to cut the selection.
        """
        if self.__selRect.isValid():
            img = self.__getSelectionImage(True)
            QApplication.clipboard().setImage(img)

    @pyqtSlot()
    def editPaste(self, pasting=False):
        """
        Public slot to paste an image from the clipboard.

        @param pasting flag indicating part two of the paste operation
        @type bool
        """
        img, ok = self.__clipboardImage()
        if ok:
            if (
                img.width() > self.__image.width()
                or img.height() > self.__image.height()
            ):
                res = EricMessageBox.yesNo(
                    self,
                    self.tr("Paste"),
                    self.tr(
                        """<p>The clipboard image is larger than the"""
                        """ current image.<br/>Paste as new image?</p>"""
                    ),
                )
                if res:
                    self.editPasteAsNew()
                return
            elif not pasting:
                self.__isPasting = True
                self.__clipboardSize = img.size()
            else:
                cmd = IconEditCommand(self, self.tr("Paste Clipboard"), self.__image)
                self.__markImage.fill(self.NoMarkColor.rgba())
                painter = QPainter(self.__image)
                painter.setPen(self.penColor())
                painter.setCompositionMode(self.__compositingMode)
                painter.drawImage(
                    self.__pasteRect.x(),
                    self.__pasteRect.y(),
                    img,
                    0,
                    0,
                    self.__pasteRect.width() + 1,
                    self.__pasteRect.height() + 1,
                )

                self.__undoStack.push(cmd)
                cmd.setAfterImage(self.__image)

                self.__updateImageRect(
                    self.__pasteRect.topLeft(),
                    self.__pasteRect.bottomRight() + QPoint(1, 1),
                )
        else:
            EricMessageBox.warning(
                self,
                self.tr("Pasting Image"),
                self.tr("""Invalid image data in clipboard."""),
            )

    def editPasteAsNew(self):
        """
        Public slot to paste the clipboard as a new image.
        """
        img, ok = self.__clipboardImage()
        if ok:
            cmd = IconEditCommand(
                self, self.tr("Paste Clipboard as New Image"), self.__image
            )
            self.setIconImage(img)
            self.setDirty(True)
            self.__undoStack.push(cmd)
            cmd.setAfterImage(self.__image)

    def editSelectAll(self):
        """
        Public slot to select the complete image.
        """
        self.__unMark()

        self.__startPos = QPoint(0, 0)
        self.__endPos = QPoint(self.rect().bottomRight())
        self.__markImage.fill(self.MarkColor.rgba())
        self.__selRect = self.__image.rect()
        self.__selectionAvailable = True
        self.selectionAvailable.emit(True)

        self.update()

    def editClear(self):
        """
        Public slot to clear the image.
        """
        self.__unMark()

        cmd = IconEditCommand(self, self.tr("Clear Image"), self.__image)
        self.__image.fill(Qt.GlobalColor.transparent)
        self.update()
        self.setDirty(True)
        self.__undoStack.push(cmd)
        cmd.setAfterImage(self.__image)

    def editResize(self):
        """
        Public slot to resize the image.
        """
        from .IconSizeDialog import IconSizeDialog

        dlg = IconSizeDialog(self.__image.width(), self.__image.height(), parent=self)
        res = dlg.exec()
        if res == QDialog.DialogCode.Accepted:
            newWidth, newHeight = dlg.getData()
            if newWidth != self.__image.width() or newHeight != self.__image.height():
                cmd = IconEditCommand(self, self.tr("Resize Image"), self.__image)
                img = self.__image.scaled(
                    newWidth,
                    newHeight,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.setIconImage(img)
                self.setDirty(True)
                self.__undoStack.push(cmd)
                cmd.setAfterImage(self.__image)

    def editNew(self):
        """
        Public slot to generate a new, empty image.
        """
        from .IconSizeDialog import IconSizeDialog

        dlg = IconSizeDialog(self.__image.width(), self.__image.height(), parent=self)
        res = dlg.exec()
        if res == QDialog.DialogCode.Accepted:
            width, height = dlg.getData()
            img = QImage(width, height, QImage.Format.Format_ARGB32)
            img.fill(Qt.GlobalColor.transparent)
            self.setIconImage(img)

    def grayScale(self):
        """
        Public slot to convert the image to gray preserving transparency.
        """
        cmd = IconEditCommand(self, self.tr("Convert to Grayscale"), self.__image)
        for x in range(self.__image.width()):
            for y in range(self.__image.height()):
                col = self.__image.pixel(x, y)
                if col != qRgba(0, 0, 0, 0):
                    gray = qGray(col)
                    self.__image.setPixel(x, y, qRgba(gray, gray, gray, qAlpha(col)))
        self.update()
        self.setDirty(True)
        self.__undoStack.push(cmd)
        cmd.setAfterImage(self.__image)

    def editUndo(self):
        """
        Public slot to perform an undo operation.
        """
        if self.__undoStack.canUndo():
            self.__undoStack.undo()

    def editRedo(self):
        """
        Public slot to perform a redo operation.
        """
        if self.__undoStack.canRedo():
            self.__undoStack.redo()

    def canUndo(self):
        """
        Public method to return the undo status.

        @return flag indicating the availability of undo
        @rtype bool
        """
        return self.__undoStack.canUndo()

    def canRedo(self):
        """
        Public method to return the redo status.

        @return flag indicating the availability of redo
        @rtype bool
        """
        return self.__undoStack.canRedo()

    def __cleanChanged(self, clean):
        """
        Private slot to handle the undo stack clean state change.

        @param clean flag indicating the clean state
        @type bool
        """
        self.setDirty(not clean)

    def shutdown(self):
        """
        Public slot to perform some shutdown actions.
        """
        self.__undoStack.canRedoChanged.disconnect(self.canRedoChanged)
        self.__undoStack.canUndoChanged.disconnect(self.canUndoChanged)
        self.__undoStack.cleanChanged.disconnect(self.__cleanChanged)

    def isSelectionAvailable(self):
        """
        Public method to check the availability of a selection.

        @return flag indicating the availability of a selection
        @rtype bool
        """
        return self.__selectionAvailable
