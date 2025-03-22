# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a specialized PDF view class.
"""

import collections
import enum

from dataclasses import dataclass

from PyQt6.QtCore import (
    QEvent,
    QPoint,
    QPointF,
    QRect,
    QRectF,
    QSize,
    QSizeF,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QColor, QGuiApplication, QPainter, QPen
from PyQt6.QtPdf import QPdfDocument, QPdfLink
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import QRubberBand

from .PdfZoomSelector import PdfZoomSelector


class PdfMarkerType(enum.Enum):
    """
    Class defining the various marker types.
    """

    SEARCHRESULT = 0
    SELECTION = 1


@dataclass
class PdfMarker:
    """
    Class defining the data structure for markers.
    """

    rectangle: QRectF
    markerType: PdfMarkerType


@dataclass
class PdfMarkerGeometry:
    """
    Class defining the data structure for marker geometries.
    """

    rectangle: QRect
    markerType: PdfMarkerType


class PdfView(QPdfView):
    """
    Class implementing a specialized PDF view.

    @signal selectionAvailable(bool) emitted to indicate the availability of a selection
    """

    MarkerColors = {
        # merker type: (pen color, brush color)
        PdfMarkerType.SEARCHRESULT: (QColor(255, 200, 0, 255), QColor(255, 200, 0, 64)),
        PdfMarkerType.SELECTION: (QColor(0, 0, 255, 255), QColor(0, 0, 255, 64)),
    }

    selectionAvailable = pyqtSignal(bool)

    def __init__(self, parent):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__screenResolution = (
            QGuiApplication.primaryScreen().logicalDotsPerInch() / 72.0
        )

        self.__documentViewport = QRect()
        self.__documentSize = QSize()
        self.__pageGeometries = {}
        self.__markers = collections.defaultdict(list)
        self.__markerGeometries = collections.defaultdict(list)
        self.__rubberBand = None

        self.pageModeChanged.connect(self.__calculateDocumentLayout)
        self.zoomModeChanged.connect(self.__calculateDocumentLayout)
        self.zoomFactorChanged.connect(self.__calculateDocumentLayout)
        self.pageSpacingChanged.connect(self.__calculateDocumentLayout)
        self.documentMarginsChanged.connect(self.__calculateDocumentLayout)

        self.pageNavigator().currentPageChanged.connect(self.__currentPageChanged)

        self.grabGesture(Qt.GestureType.PinchGesture)

    def setDocument(self, document):
        """
        Public method to set the PDF document.

        @param document reference to the PDF document object
        @type QPdfDocument
        """
        super().setDocument(document)

        document.statusChanged.connect(self.__calculateDocumentLayout)

    def __zoomInOut(self, zoomIn):
        """
        Private method to zoom into or out of the view.

        @param zoomIn flag indicating to zoom into the view
        @type bool
        """
        zoomFactor = self.__zoomFactorForMode(self.zoomMode())

        factors = list(PdfZoomSelector.ZoomValues)
        factors.append(self.__zoomFactorForMode(QPdfView.ZoomMode.FitInView))
        factors.append(self.__zoomFactorForMode(QPdfView.ZoomMode.FitToWidth))
        if zoomIn:
            factors.sort()
            if zoomFactor >= factors[-1]:
                return
            newIndex = next(x for x, val in enumerate(factors) if val > zoomFactor)
        else:
            factors.sort(reverse=True)
            if zoomFactor <= factors[-1]:
                return
            newIndex = next(x for x, val in enumerate(factors) if val < zoomFactor)
        newFactor = factors[newIndex]
        if newFactor == self.__zoomFactorForMode(QPdfView.ZoomMode.FitInView):
            self.setZoomMode(QPdfView.ZoomMode.FitInView)
            self.zoomModeChanged.emit(QPdfView.ZoomMode.FitInView)
        elif newFactor == self.__zoomFactorForMode(QPdfView.ZoomMode.FitToWidth):
            self.setZoomMode(QPdfView.ZoomMode.FitToWidth)
            self.zoomModeChanged.emit(QPdfView.ZoomMode.FitToWidth)
        else:
            self.setZoomFactor(newFactor)
            self.zoomFactorChanged.emit(newFactor)
            self.setZoomMode(QPdfView.ZoomMode.Custom)
            self.zoomModeChanged.emit(QPdfView.ZoomMode.Custom)

    def __zoomFactorForMode(self, zoomMode):
        """
        Private method to calculate the zoom factor iaw. the current zoom mode.

        @param zoomMode zoom mode to get the zoom factor for
        @type QPdfView.ZoomMode
        @return zoom factor
        @rtype float
        """
        self.__calculateDocumentViewport()

        if zoomMode == QPdfView.ZoomMode.Custom:
            return self.zoomFactor()
        else:
            curPage = self.pageNavigator().currentPage()
            margins = self.documentMargins()
            if zoomMode == QPdfView.ZoomMode.FitToWidth:
                pageSize = (
                    self.document().pagePointSize(curPage) * self.__screenResolution
                ).toSize()
                factor = (
                    self.__documentViewport.width() - margins.left() - margins.right()
                ) / pageSize.width()
                pageSize *= factor
            else:
                # QPdfView.ZoomMode.FitInView
                viewportSize = self.__documentViewport.size() + QSize(
                    -margins.left() - margins.right(), -self.pageSpacing()
                )
                pageSize = (
                    self.document().pagePointSize(curPage) * self.__screenResolution
                ).toSize()
                pageSize = pageSize.scaled(
                    viewportSize, Qt.AspectRatioMode.KeepAspectRatio
                )
            zoomFactor = (
                pageSize.width()
                / (
                    self.document().pagePointSize(curPage) * self.__screenResolution
                ).width()
            )
            return zoomFactor

    @pyqtSlot()
    def zoomIn(self):
        """
        Public slot to zoom into the view.
        """
        self.__zoomInOut(True)

    @pyqtSlot()
    def zoomOut(self):
        """
        Public slot to zoom out of the view.
        """
        self.__zoomInOut(False)

    @pyqtSlot()
    def zoomReset(self):
        """
        Public slot to reset the zoom factor of the view.
        """
        if self.zoomMode() != QPdfView.ZoomMode.Custom or self.zoomFactor() != 1.0:
            self.setZoomFactor(1.0)
            self.zoomFactorChanged.emit(1.0)
            self.setZoomMode(QPdfView.ZoomMode.Custom)
            self.zoomModeChanged.emit(QPdfView.ZoomMode.Custom)

    def wheelEvent(self, evt):
        """
        Protected method to handle wheel events.

        @param evt reference to the wheel event
        @type QWheelEvent
        """
        delta = evt.angleDelta().y()
        if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if delta < 0:
                self.zoomOut()
            elif delta > 0:
                self.zoomIn()
            evt.accept()
            return

        elif evt.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if delta < 0:
                self.pageNavigator().back()
            elif delta > 0:
                self.pageNavigator().forward()
            evt.accept()
            return

        super().wheelEvent(evt)

    def keyPressEvent(self, evt):
        """
        Protected method handling key press events.

        @param evt reference to the key event
        @type QKeyEvent
        """
        if evt.key() == Qt.Key.Key_Escape:
            self.clearSelection()

    def mousePressEvent(self, evt):
        """
        Protected method to handle mouse press events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.LeftButton:
            self.clearMarkers(PdfMarkerType.SELECTION)
            self.selectionAvailable.emit(False)

            self.__rubberBandOrigin = evt.pos()
            if self.__rubberBand is None:
                self.__rubberBand = QRubberBand(
                    QRubberBand.Shape.Rectangle, self.viewport()
                )
            self.__rubberBand.setGeometry(QRect(self.__rubberBandOrigin, QSize()))
            self.__rubberBand.show()

        super().mousePressEvent(evt)

    def mouseMoveEvent(self, evt):
        """
        Protected method to handle mouse move events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if evt.buttons() & Qt.MouseButton.LeftButton:
            self.__rubberBand.setGeometry(
                QRect(self.__rubberBandOrigin, evt.pos()).normalized()
            )

        super().mousePressEvent(evt)

    def mouseReleaseEvent(self, evt):
        """
        Protected method to handle mouse release events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.LeftButton:
            self.__rubberBand.hide()
            translatedRubber = self.__rubberBand.geometry().translated(
                self.__documentViewport.topLeft()
            )
            for page in self.__pageGeometries:
                if self.__pageGeometries[page].intersects(translatedRubber):
                    translatedRubber = translatedRubber.translated(
                        -self.__pageGeometries[page].topLeft()
                    )
                    factor = self.__zoomFactorForMode(self.zoomMode())
                    selectionSize = (
                        QSizeF(translatedRubber.size())
                        / factor
                        / self.__screenResolution
                    )
                    selectionTopLeft = (
                        QPointF(translatedRubber.topLeft())
                        / factor
                        / self.__screenResolution
                    )
                    selectionRect = QRectF(selectionTopLeft, selectionSize)
                    selection = self.document().getSelection(
                        page, selectionRect.topLeft(), selectionRect.bottomRight()
                    )
                    if selection.isValid():
                        for bound in selection.bounds():
                            self.addMarker(
                                page, bound.boundingRect(), PdfMarkerType.SELECTION
                            )
                            self.selectionAvailable.emit(True)

        super().mousePressEvent(evt)

    def event(self, evt):
        """
        Public method handling events.

        @param evt reference to the event
        @type QEvent
        @return flag indicating, if the event was handled
        @rtype bool
        """
        if evt.type() == QEvent.Type.Gesture:
            self.gestureEvent(evt)
            return True

        return super().event(evt)

    def gestureEvent(self, evt):
        """
        Protected method handling gesture events.

        @param evt reference to the gesture event
        @type QGestureEvent
        """
        pinch = evt.gesture(Qt.GestureType.PinchGesture)
        if pinch:
            if pinch.state() == Qt.GestureState.GestureStarted:
                pinch.setTotalScaleFactor(self.__zoomFactorForMode(self.zoomMode()))
            elif pinch.state() == Qt.GestureState.GestureUpdated:
                if self.zoomMode() != QPdfView.ZoomMode.Custom:
                    self.setZoomMode(QPdfView.ZoomMode.Custom)
                    self.zoomModeChanged.emit(QPdfView.ZoomMode.Custom)
                zoomFactor = pinch.totalScaleFactor()
                self.setZoomFactor(zoomFactor)
                self.zoomFactorChanged.emit(zoomFactor)
            evt.accept()

    def resizeEvent(self, evt):
        """
        Protected method to handle a widget resize.

        @param evt reference to the resize event
        @type QResizeEvent
        """
        super().resizeEvent(evt)

        self.__calculateDocumentViewport()

    def paintEvent(self, evt):
        """
        Protected method to paint the view.

        This event handler calls the original paint event handler of the super class
        and paints the markers on top of the result.

        @param evt reference to the paint event
        @type QPaintEvent
        """
        super().paintEvent(evt)

        painter = QPainter(self.viewport())
        painter.translate(-self.__documentViewport.x(), -self.__documentViewport.y())
        for page in self.__markerGeometries:
            for markerGeom in self.__markerGeometries[page]:
                if markerGeom.rectangle.intersects(self.__documentViewport):
                    painter.setPen(
                        QPen(PdfView.MarkerColors[markerGeom.markerType][0], 2)
                    )
                    painter.setBrush(PdfView.MarkerColors[markerGeom.markerType][1])
                    painter.drawRect(markerGeom.rectangle)
        painter.end()

    def __calculateDocumentViewport(self):
        """
        Private method to calculate the document viewport.

        This is a PyQt implementation of the code found in the QPdfView class
        because it is calculated in a private part and not accessible.
        """
        x = self.horizontalScrollBar().value()
        y = self.verticalScrollBar().value()
        width = self.viewport().width()
        height = self.viewport().height()

        docViewport = QRect(x, y, width, height)
        if self.__documentViewport == docViewport:
            return

        oldSize = self.__documentViewport.size()

        self.__documentViewport = docViewport

        if oldSize != self.__documentViewport.size():
            self.__calculateDocumentLayout()

    @pyqtSlot()
    def __calculateDocumentLayout(self):
        """
        Private slot to calculate the document layout data.

        This is a PyQt implementation of the code found in the QPdfView class
        because it is calculated in a private part and not accessible.
        """
        self.__documentSize = QSize()
        self.__pageGeometries.clear()
        self.__markerGeometries.clear()

        document = self.document()
        margins = self.documentMargins()

        if document is None or document.status() != QPdfDocument.Status.Ready:
            return

        pageCount = document.pageCount()

        totalWidth = 0

        startPage = (
            self.pageNavigator().currentPage()
            if self.pageMode() == QPdfView.PageMode.SinglePage
            else 0
        )
        endPage = (
            self.pageNavigator().currentPage() + 1
            if self.pageMode() == QPdfView.PageMode.SinglePage
            else pageCount
        )

        # calculate pageSizes
        for page in range(startPage, endPage):
            if self.zoomMode() == QPdfView.ZoomMode.Custom:
                pageSize = QSizeF(
                    document.pagePointSize(page)
                    * self.__screenResolution
                    * self.zoomFactor()
                ).toSize()
            elif self.zoomMode() == QPdfView.ZoomMode.FitToWidth:
                pageSize = QSizeF(
                    document.pagePointSize(page) * self.__screenResolution
                ).toSize()
                factor = (
                    self.__documentViewport.width() - margins.left() - margins.right()
                ) / pageSize.width()
                pageSize *= factor
            elif self.zoomMode() == QPdfView.ZoomMode.FitInView:
                viewportSize = self.__documentViewport.size() + QSize(
                    -margins.left() - margins.right(), -self.pageSpacing()
                )
                pageSize = QSizeF(
                    document.pagePointSize(page) * self.__screenResolution
                ).toSize()
                pageSize = pageSize.scaled(
                    viewportSize, Qt.AspectRatioMode.KeepAspectRatio
                )

            totalWidth = max(totalWidth, pageSize.width())

            self.__pageGeometries[page] = QRect(QPoint(0, 0), pageSize)

        totalWidth += margins.left() + margins.right()

        pageY = margins.top()

        # calculate page positions
        for page in range(startPage, endPage):
            pageSize = self.__pageGeometries[page].size()

            # center horizontally inside the viewport
            pageX = (
                max(totalWidth, self.__documentViewport.width()) - pageSize.width()
            ) // 2
            self.__pageGeometries[page].moveTopLeft(QPoint(pageX, pageY))

            self.__calculateMarkerGeometries(page, QPoint(pageX, pageY))

            pageY += pageSize.height() + self.pageSpacing()

        pageY += margins.bottom()

        self.__documentSize = QSize(totalWidth, pageY)

    @pyqtSlot()
    def __currentPageChanged(self):
        """
        Private slot to handle a change of the current page.
        """
        if self.pageMode() == QPdfView.PageMode.SinglePage:
            self.__calculateDocumentLayout()
            self.update()

    def __calculateMarkerGeometries(self, page, offset):
        """
        Private method to calculate the marker geometries.

        @param page page number
        @type int
        @param offset page offset
        @type QPoint or QPointF
        """
        # calculate search marker sizes
        if page in self.__markers:
            factor = self.__zoomFactorForMode(self.zoomMode())
            for marker in self.__markers[page]:
                markerSize = (
                    QSizeF(marker.rectangle.size()) * factor * self.__screenResolution
                ).toSize()
                markerTopLeft = (
                    QPointF(marker.rectangle.topLeft())
                    * factor
                    * self.__screenResolution
                ).toPoint()

                markerGeometry = QRect(markerTopLeft, markerSize)
                self.__markerGeometries[page].append(
                    PdfMarkerGeometry(
                        rectangle=markerGeometry.translated(offset),
                        markerType=marker.markerType,
                    )
                )

    def scrollContentsBy(self, dx, dy):
        """
        Public method called when the scrollbars are moved.

        @param dx change of the horizontal scroll bar
        @type int
        @param dy change of the vertical scroll bar
        @type int
        """
        super().scrollContentsBy(dx, dy)

        self.__calculateDocumentViewport()

    def __updateView(self):
        """
        Private method to update the view.
        """
        self.__calculateDocumentLayout()
        self.update()

    @pyqtSlot(int, QRectF, PdfMarkerType)
    @pyqtSlot(int, QRect, PdfMarkerType)
    def addMarker(self, page, rect, markerType):
        """
        Public slot to add a marker.

        @param page page number for the marker
        @type int
        @param rect marker rectangle
        @type QRect or QRectF
        @param markerType type of the marker
        @type PdfMarkerType
        """
        marker = PdfMarker(rectangle=QRectF(rect), markerType=markerType)
        if marker not in self.__markers[page]:
            self.__markers[page].append(marker)
        self.__updateView()

    @pyqtSlot(PdfMarkerType)
    def clearMarkers(self, markerType):
        """
        Public slot to clear the markers of a specific type.

        @param markerType type of the marker
        @type PdfMarkerType
        """
        markers = collections.defaultdict(list)
        for page in self.__markers:
            markersList = [
                m for m in self.__markers[page] if m.markerType != markerType
            ]
            if markersList:
                markers[page] = markersList

        self.__markers = markers
        self.__updateView()

    @pyqtSlot()
    def clearAllMarkers(self):
        """
        Public slot to clear all markers.
        """
        self.__markers.clear()
        self.__updateView()

    @pyqtSlot(QPdfLink)
    def addSearchMarker(self, link):
        """
        Public slot to add a search marker given a PDF link.

        @param link reference to the PDF link object
        @type QPdfLink
        """
        for rect in link.rectangles():
            self.addMarker(link.page(), rect, PdfMarkerType.SEARCHRESULT)

    @pyqtSlot()
    def clearSearchMarkers(self):
        """
        Public slot to clear the search markers.
        """
        self.clearMarkers(PdfMarkerType.SEARCHRESULT)

    def hasSelection(self):
        """
        Public method to check the presence of a selection.

        @return flag indicating the presence of a selection
        @rtype bool
        """
        return any(
            m.markerType == PdfMarkerType.SELECTION
            for p in self.__markers
            for m in self.__markers[p]
        )

    def getSelection(self):
        """
        Public method to get a PDF selection object.

        @return reference to the PDF selection object
        @rtype QPdfSelection
        """
        for page in self.__markers:
            markersList = [
                m
                for m in self.__markers[page]
                if m.markerType == PdfMarkerType.SELECTION
            ]
            if markersList:
                selection = self.document().getSelection(
                    page,
                    markersList[0].rectangle.topLeft(),
                    markersList[-1].rectangle.bottomRight(),
                )
                if selection.isValid():
                    return selection

        return None

    @pyqtSlot()
    def clearSelection(self):
        """
        Public slot to clear the current selection.
        """
        self.clearMarkers(PdfMarkerType.SELECTION)
