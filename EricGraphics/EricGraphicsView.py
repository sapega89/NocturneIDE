# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a canvas view class.
"""

import sys

from PyQt6.QtCore import (
    QCoreApplication,
    QMarginsF,
    QRectF,
    QSize,
    QSizeF,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPixmap
from PyQt6.QtSvg import QSvgGenerator
from PyQt6.QtWidgets import QGraphicsView


class EricGraphicsView(QGraphicsView):
    """
    Class implementing a graphics view.

    @signal zoomValueChanged(int) emitted to signal a change of the zoom value
    """

    zoomValueChanged = pyqtSignal(int)

    ZoomLevels = [
        1,
        3,
        5,
        7,
        9,
        10,
        20,
        30,
        50,
        67,
        80,
        90,
        100,
        110,
        120,
        133,
        150,
        170,
        200,
        240,
        300,
        400,
        500,
        600,
        700,
        800,
        900,
        1000,
    ]
    ZoomLevelDefault = 100

    def __init__(self, scene, drawingMode="automatic", parent=None):
        """
        Constructor

        @param scene reference to the scene object
        @type QGraphicsScene
        @param drawingMode name of the drawing mode (one of "automatic",
            "black_white" or "white_black") (defaults to "automatic")
        @type str (optional)
        @param parent parent widget
        @type QWidget
        """
        super().__init__(scene, parent)
        self.setObjectName("EricGraphicsView")

        self.__initialSceneSize = self.scene().sceneRect().size()
        self.setBackgroundBrush(
            QBrush(self.getBackgroundColor(drawingMode=drawingMode))
        )
        self.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.SmartViewportUpdate)

        self.setWhatsThis(
            self.tr(
                "<b>Graphics View</b>\n"
                "<p>This graphics view is used to show a diagram. \n"
                "There are various actions available to manipulate the \n"
                "shown items.</p>\n"
                "<ul>\n"
                "<li>Clicking on an item selects it.</li>\n"
                "<li>Ctrl-clicking adds an item to the selection.</li>\n"
                "<li>Ctrl-clicking a selected item deselects it.</li>\n"
                "<li>Clicking on an empty spot of the canvas resets the selection."
                "</li>\n"
                "<li>Dragging the mouse over the canvas spans a rubberband to \n"
                "select multiple items.</li>\n"
                "<li>Dragging the mouse over a selected item moves the \n"
                "whole selection.</li>\n"
                "</ul>\n"
            )
        )

    def getDrawingColors(self, drawingMode="automatic"):
        """
        Public method to get the configured drawing colors.

        @param drawingMode name of the drawing mode (one of "automatic",
            "black_white" or "white_black") (defaults to "automatic")
        @type str (optional)
        @return tuple containing the foreground and background colors
        @rtype tuple of (QColor, QColor)
        """
        if drawingMode == "automatic":
            if QCoreApplication.instance().usesDarkPalette():
                drawingMode = "white_black"
            else:
                drawingMode = "black_white"

        if drawingMode == "white_black":
            return (QColor("#ffffff"), QColor("#262626"))
        else:
            return (QColor("#000000"), QColor("#ffffff"))

    def getForegroundColor(self, drawingMode="automatic"):
        """
        Public method to get the configured foreground color.

        @param drawingMode name of the drawing mode (one of "automatic",
            "black_white" or "white_black") (defaults to "automatic")
        @type str (optional)
        @return foreground color
        @rtype QColor
        """
        return self.getDrawingColors(drawingMode=drawingMode)[0]

    def getBackgroundColor(self, drawingMode="automatic"):
        """
        Public method to get the configured background color.

        @param drawingMode name of the drawing mode (one of "automatic",
            "black_white" or "white_black") (defaults to "automatic")
        @type str (optional)
        @return background color
        @rtype QColor
        """
        return self.getDrawingColors(drawingMode=drawingMode)[1]

    def __levelForZoom(self, zoom):
        """
        Private method determining the zoom level index given a zoom factor.

        @param zoom zoom factor
        @type int
        @return index of zoom factor
        @rtype int
        """
        try:
            index = EricGraphicsView.ZoomLevels.index(zoom)
        except ValueError:
            for index in range(len(EricGraphicsView.ZoomLevels)):
                if zoom <= EricGraphicsView.ZoomLevels[index]:
                    break
        return index

    def zoomIn(self):
        """
        Public method to zoom in.
        """
        index = self.__levelForZoom(self.zoom())
        if index < len(EricGraphicsView.ZoomLevels) - 1:
            self.setZoom(EricGraphicsView.ZoomLevels[index + 1])

    def zoomOut(self):
        """
        Public method to zoom out.
        """
        index = self.__levelForZoom(self.zoom())
        if index > 0:
            self.setZoom(EricGraphicsView.ZoomLevels[index - 1])

    def zoomReset(self):
        """
        Public method to handle the reset the zoom value.
        """
        self.setZoom(EricGraphicsView.ZoomLevels[EricGraphicsView.ZoomLevelDefault])

    def setZoom(self, value):
        """
        Public method to set the zoom value in percent.

        @param value zoom value in percent
        @type int
        """
        if value != self.zoom():
            self.resetTransform()
            factor = value / 100.0
            self.scale(factor, factor)
            self.zoomValueChanged.emit(value)

    def zoom(self):
        """
        Public method to get the current zoom factor in percent.

        @return current zoom factor in percent
        @rtype int
        """
        return int(self.transform().m11() * 100.0)

    def resizeScene(self, amount, isWidth=True):
        """
        Public method to resize the scene.

        @param amount size increment
        @type int
        @param isWidth flag indicating width is to be resized
        @type bool
        """
        sceneRect = self.scene().sceneRect()
        width = sceneRect.width()
        height = sceneRect.height()
        if isWidth:
            width += amount
        else:
            height += amount
        rect = self._getDiagramRect(10)
        if width < rect.width():
            width = rect.width()
        if height < rect.height():
            height = rect.height()

        self.setSceneSize(width, height)

    def setSceneSize(self, width, height):
        """
        Public method to set the scene size.

        @param width width for the scene
        @type float
        @param height height for the scene
        @type float
        """
        rect = self.scene().sceneRect()
        rect.setHeight(height)
        rect.setWidth(width)
        self.scene().setSceneRect(rect)

    def autoAdjustSceneSize(self, limit=False):
        """
        Public method to adjust the scene size to the diagram size.

        @param limit flag indicating to limit the scene to the
            initial size
        @type bool
        """
        size = self._getDiagramSize(10)
        if limit:
            newWidth = max(size.width(), self.__initialSceneSize.width())
            newHeight = max(size.height(), self.__initialSceneSize.height())
        else:
            newWidth = size.width()
            newHeight = size.height()
        self.setSceneSize(newWidth, newHeight)

    def _getDiagramRect(self, border=0):
        """
        Protected method to calculate the minimum rectangle fitting the
        diagram.

        @param border border width to include in the calculation
        @type int
        @return the minimum rectangle
        @rtype QRectF
        """
        startx = sys.maxsize
        starty = sys.maxsize
        endx = 0
        endy = 0
        for itm in self.filteredItems(self.scene().items()):
            rect = itm.sceneBoundingRect()
            itmEndX = rect.x() + rect.width()
            itmEndY = rect.y() + rect.height()
            itmStartX = rect.x()
            itmStartY = rect.y()
            if startx >= itmStartX:
                startx = itmStartX
            if starty >= itmStartY:
                starty = itmStartY
            if endx <= itmEndX:
                endx = itmEndX
            if endy <= itmEndY:
                endy = itmEndY
        if border:
            startx -= border
            starty -= border
            endx += border
            endy += border

        return QRectF(startx, starty, endx - startx + 1, endy - starty + 1)

    def _getDiagramSize(self, border=0):
        """
        Protected method to calculate the minimum size fitting the diagram.

        @param border border width to include in the calculation
        @type int
        @return the minimum size
        @rtype QSizeF
        """
        endx = 0
        endy = 0
        for itm in self.filteredItems(self.scene().items()):
            rect = itm.sceneBoundingRect()
            itmEndX = rect.x() + rect.width()
            itmEndY = rect.y() + rect.height()
            if endx <= itmEndX:
                endx = itmEndX
            if endy <= itmEndY:
                endy = itmEndY
        if border:
            endx += border
            endy += border

        return QSizeF(endx + 1, endy + 1)

    def __getDiagram(self, rect, imageFormat="PNG", filename=None):
        """
        Private method to retrieve the diagram from the scene fitting it
        in the minimum rectangle.

        @param rect minimum rectangle fitting the diagram
        @type QRectF
        @param imageFormat format for the image file
        @type str
        @param filename name of the file for non pixmaps
        @type str
        @return paint device containing the diagram
        @rtype QPixmap or QSvgGenerator
        """
        selectedItems = self.scene().selectedItems()

        # step 1: deselect all widgets
        if selectedItems:
            for item in selectedItems:
                item.setSelected(False)

        # step 2: grab the diagram
        if imageFormat == "PNG":
            paintDevice = QPixmap(int(rect.width()), int(rect.height()))
            paintDevice.fill(self.backgroundBrush().color())
        else:
            paintDevice = QSvgGenerator()
            paintDevice.setFileName(filename)
            paintDevice.setResolution(100)  # 100 dpi
            paintDevice.setSize(QSize(int(rect.width()), int(rect.height())))
            paintDevice.setViewBox(rect)
        painter = QPainter(paintDevice)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.begin(paintDevice)
        self.render(painter, QRectF(), rect.toRect())
        painter.end()

        # step 3: reselect the widgets
        if selectedItems:
            for item in selectedItems:
                item.setSelected(True)

        return paintDevice

    def saveImage(self, filename, imageFormat="PNG"):
        """
        Public method to save the scene to a file.

        @param filename name of the file to write the image to
        @type float
        @param imageFormat format for the image file
        @type float
        @return flag indicating success
        @rtype bool
        """
        rect = self._getDiagramRect(self.border)
        if imageFormat == "SVG":
            self.__getDiagram(rect, imageFormat=imageFormat, filename=filename)
            return True
        else:
            pixmap = self.__getDiagram(rect)
            return pixmap.save(filename, imageFormat)

    def printDiagram(self, printer, margins=None, diagramName=""):
        """
        Public method to print the diagram.

        @param printer reference to a ready configured printer object
        @type QPrinter
        @param margins diagram margins (defaults to None)
        @type QMarginsF or None (optional)
        @param diagramName name of the diagram
        @type str
        """
        if margins is None:
            margins = QMarginsF(1.0, 1.0, 1.0, 1.0)

        painter = QPainter(printer)

        font = QFont(["times"], 10)
        painter.setFont(font)
        fm = painter.fontMetrics()
        fontHeight = fm.lineSpacing()
        marginX = (
            printer.pageLayout().paintRectPixels(printer.resolution()).x()
            - printer.pageLayout().fullRectPixels(printer.resolution()).x()
        )
        marginX = int(margins.left() * printer.resolution() / 2.54) - marginX
        marginY = (
            printer.pageLayout().paintRectPixels(printer.resolution()).y()
            - printer.pageLayout().fullRectPixels(printer.resolution()).y()
        )
        marginY = int(margins.top() * printer.resolution() / 2.54) - marginY

        width = (
            printer.width()
            - marginX
            - int(margins.right() * printer.resolution() / 2.54)
        )
        height = (
            printer.height()
            - fontHeight
            - 4
            - marginY
            - int(margins.bottom() * printer.resolution() / 2.54)
        )

        self.render(painter, target=QRectF(marginX, marginY, width, height))

        # write a foot note
        tc = QColor(50, 50, 50)
        painter.setPen(tc)
        painter.drawRect(marginX, marginY, width, height)
        painter.drawLine(
            marginX, marginY + height + 2, marginX + width, marginY + height + 2
        )
        painter.setFont(font)
        painter.drawText(
            marginX,
            marginY + height + 4,
            width,
            fontHeight,
            Qt.AlignmentFlag.AlignRight,
            diagramName,
        )

        painter.end()

    ###########################################################################
    ## The methods below should be overridden by subclasses to get special
    ## behavior.
    ###########################################################################

    def filteredItems(self, items):
        """
        Public method to filter a list of items.

        @param items list of items as returned by the scene object
        @type QGraphicsItem
        @return list of interesting collision items
        @rtype QGraphicsItem
        """
        # just return the list unchanged
        return list(items)
