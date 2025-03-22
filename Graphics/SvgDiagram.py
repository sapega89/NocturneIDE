# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing a SVG graphic.
"""

from PyQt6.QtCore import QEvent, QMarginsF, QSize, Qt
from PyQt6.QtGui import QAction, QColor, QFont, QPageLayout, QPainter, QPalette
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter, QPrintPreviewDialog
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtWidgets import QMenu, QScrollArea, QSizePolicy, QToolBar

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.EricWidgets.EricZoomWidget import EricZoomWidget
from eric7.SystemUtilities import FileSystemUtilities


class SvgDiagram(EricMainWindow):
    """
    Class implementing a dialog showing a SVG graphic.
    """

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

    def __init__(self, svgFile, parent=None, name=None):
        """
        Constructor

        @param svgFile filename of a SVG graphics file to show
        @type str
        @param parent parent widget of the view
        @type QWidget
        @param name name of the view widget
        @type str
        """
        super().__init__(parent)
        if name:
            self.setObjectName(name)
        else:
            self.setObjectName("SvgDiagram")
        self.setWindowTitle(self.tr("SVG-Viewer"))

        self.svgWidget = QSvgWidget()
        self.svgWidget.setObjectName("svgWidget")
        self.svgWidget.setBackgroundRole(QPalette.ColorRole.Base)
        self.svgWidget.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored
        )

        self.svgView = QScrollArea()
        self.svgView.setObjectName("svgView")
        self.svgView.setBackgroundRole(QPalette.ColorRole.Dark)
        self.svgView.setWidget(self.svgWidget)

        self.setCentralWidget(self.svgView)

        self.__zoomWidget = EricZoomWidget(
            EricPixmapCache.getPixmap("zoomOut"),
            EricPixmapCache.getPixmap("zoomIn"),
            EricPixmapCache.getPixmap("zoomReset"),
            self,
        )
        self.statusBar().addPermanentWidget(self.__zoomWidget)
        self.__zoomWidget.setMapping(SvgDiagram.ZoomLevels, SvgDiagram.ZoomLevelDefault)
        self.__zoomWidget.valueChanged.connect(self.__doZoom)

        # polish up the dialog
        self.resize(QSize(800, 600).expandedTo(self.minimumSizeHint()))

        self.zoom = 1.0
        self.__loadSvgFile(svgFile)
        self.svgWidget.resize(self.svgWidget.renderer().defaultSize())

        self.__initActions()
        self.__initContextMenu()
        self.__initToolBars()

        self.grabGesture(Qt.GestureType.PinchGesture)

    def __loadSvgFile(self, svgFile):
        """
        Private method to load a given SVG file.

        @param svgFile file path of the SVG file
        @type str
        """
        self.svgFile = svgFile
        if FileSystemUtilities.isRemoteFileName(svgFile):
            try:
                data = (
                    ericApp()
                    .getObject("EricServer")
                    .getServiceInterface("FileSystem")
                    .readFile(svgFile)
                )
                self.svgWidget.load(data)
            except OSError as err:
                EricMessageBox.warning(
                    self,
                    self.tr("SVG-Viewer"),
                    self.tr(
                        "<p>The SVG file <b>{0}</b> could not be loaded.</p>"
                        "<p>Reason: {1}</p>"
                    ).format(svgFile, str(err)),
                )

        else:
            self.svgWidget.load(self.svgFile)

    def __initActions(self):
        """
        Private method to initialize the view actions.
        """
        self.closeAct = QAction(
            EricPixmapCache.getIcon("close"), self.tr("Close"), self
        )
        self.closeAct.triggered.connect(self.close)

        self.printAct = QAction(
            EricPixmapCache.getIcon("print"), self.tr("Print"), self
        )
        self.printAct.triggered.connect(self.__printDiagram)

        self.printPreviewAct = QAction(
            EricPixmapCache.getIcon("printPreview"), self.tr("Print Preview"), self
        )
        self.printPreviewAct.triggered.connect(self.__printPreviewDiagram)

    def __initContextMenu(self):
        """
        Private method to initialize the context menu.
        """
        self.__menu = QMenu(self)
        self.__menu.addAction(self.closeAct)
        self.__menu.addSeparator()
        self.__menu.addAction(self.printPreviewAct)
        self.__menu.addAction(self.printAct)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__showContextMenu)

    def __showContextMenu(self, coord):
        """
        Private slot to show the context menu of the listview.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        self.__menu.popup(self.mapToGlobal(coord))

    def __initToolBars(self):
        """
        Private method to populate the toolbars with our actions.
        """
        self.windowToolBar = QToolBar(self.tr("Window"), self)
        self.windowToolBar.addAction(self.closeAct)

        self.graphicsToolBar = QToolBar(self.tr("Graphics"), self)
        self.graphicsToolBar.addAction(self.printPreviewAct)
        self.graphicsToolBar.addAction(self.printAct)

        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.windowToolBar)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.graphicsToolBar)

    def getDiagramName(self):
        """
        Public method to retrieve a name for the diagram.

        @return name for the diagram
        @rtype str
        """
        return self.svgFile

    def wheelEvent(self, evt):
        """
        Protected method to handle wheel events.

        @param evt reference to the wheel event
        @type QWheelEvent
        """
        if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = evt.angleDelta().y()
            if delta < 0:
                self.__zoomOut()
            elif delta > 0:
                self.__zoomIn()
            evt.accept()
            return

        super().wheelEvent(evt)

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
                pinch.setTotalScaleFactor(self.__zoom() / 100)
            elif pinch.state() == Qt.GestureState.GestureUpdated:
                self.__doZoom(int(pinch.totalScaleFactor() * 100))
            evt.accept()

    ###########################################################################
    ## Private menu handling methods below.
    ###########################################################################

    def __adjustScrollBar(self, scrollBar, factor):
        """
        Private method to adjust a scrollbar by a certain factor.

        @param scrollBar reference to the scrollbar object
        @type QScrollBar
        @param factor factor to adjust by
        @type float
        """
        scrollBar.setValue(
            int(factor * scrollBar.value() + ((factor - 1) * scrollBar.pageStep() / 2))
        )

    def __levelForZoom(self, zoom):
        """
        Private method determining the zoom level index given a zoom factor.

        @param zoom zoom factor
        @type int
        @return index of zoom factor
        @rtype int
        """
        try:
            index = SvgDiagram.ZoomLevels.index(zoom)
        except ValueError:
            for index in range(len(SvgDiagram.ZoomLevels)):
                if zoom <= SvgDiagram.ZoomLevels[index]:
                    break
        return index

    def __doZoom(self, value):
        """
        Private method to set the zoom value in percent.

        @param value zoom value in percent
        @type int
        """
        oldValue = self.__zoom()
        if value != oldValue:
            self.svgWidget.resize(value / 100 * self.svgWidget.sizeHint())

            factor = value / oldValue
            self.__adjustScrollBar(self.svgView.horizontalScrollBar(), factor)
            self.__adjustScrollBar(self.svgView.verticalScrollBar(), factor)

            self.__zoomWidget.setValue(value)

    def __zoomIn(self):
        """
        Private method to zoom into the SVG.
        """
        index = self.__levelForZoom(self.__zoom())
        if index < len(SvgDiagram.ZoomLevels) - 1:
            self.__doZoom(SvgDiagram.ZoomLevels[index + 1])

    def __zoomOut(self):
        """
        Private method to zoom out of the SVG.
        """
        index = self.__levelForZoom(self.__zoom())
        if index > 0:
            self.__doZoom(SvgDiagram.ZoomLevels[index - 1])

    def __zoomReset(self):
        """
        Private method to reset the zoom value.
        """
        self.__doZoom(SvgDiagram.ZoomLevels[SvgDiagram.ZoomLevelDefault])

    def __zoom(self):
        """
        Private method to get the current zoom factor in percent.

        @return current zoom factor in percent
        @rtype int
        """
        return int(self.svgWidget.width() / self.svgWidget.sizeHint().width() * 100.0)

    def __printDiagram(self):
        """
        Private slot called to print the diagram.
        """
        printer = QPrinter(mode=QPrinter.PrinterMode.ScreenResolution)
        printer.setFullPage(True)
        if Preferences.getPrinter("ColorMode"):
            printer.setColorMode(QPrinter.ColorMode.Color)
        else:
            printer.setColorMode(QPrinter.ColorMode.GrayScale)
        if Preferences.getPrinter("FirstPageFirst"):
            printer.setPageOrder(QPrinter.PageOrder.FirstPageFirst)
        else:
            printer.setPageOrder(QPrinter.PageOrder.LastPageFirst)
        printerName = Preferences.getPrinter("PrinterName")
        if printerName:
            printer.setPrinterName(printerName)

        printDialog = QPrintDialog(printer, parent=self)
        if printDialog.exec():
            self.__print(printer)

    def __printPreviewDiagram(self):
        """
        Private slot called to show a print preview of the diagram.
        """
        printer = QPrinter(mode=QPrinter.PrinterMode.ScreenResolution)
        printer.setFullPage(True)
        if Preferences.getPrinter("ColorMode"):
            printer.setColorMode(QPrinter.ColorMode.Color)
        else:
            printer.setColorMode(QPrinter.ColorMode.GrayScale)
        if Preferences.getPrinter("FirstPageFirst"):
            printer.setPageOrder(QPrinter.PageOrder.FirstPageFirst)
        else:
            printer.setPageOrder(QPrinter.PageOrder.LastPageFirst)
        printer.setPageMargins(
            QMarginsF(
                Preferences.getPrinter("LeftMargin") * 10,
                Preferences.getPrinter("TopMargin") * 10,
                Preferences.getPrinter("RightMargin") * 10,
                Preferences.getPrinter("BottomMargin") * 10,
            ),
            QPageLayout.Unit.Millimeter,
        )
        printerName = Preferences.getPrinter("PrinterName")
        if printerName:
            printer.setPrinterName(printerName)

        preview = QPrintPreviewDialog(printer, parent=self)
        preview.paintRequested[QPrinter].connect(self.__print)
        preview.exec()

    def __print(self, printer):
        """
        Private slot to the actual printing.

        @param printer reference to the printer object
        @type QPrinter
        """
        painter = QPainter()
        painter.begin(printer)

        # calculate margin and width of printout
        font = QFont(["times"], 10)
        painter.setFont(font)
        fm = painter.fontMetrics()
        fontHeight = fm.lineSpacing()
        marginX = (
            printer.pageLayout().paintRectPixels(printer.resolution()).x()
            - printer.pageLayout().fullRectPixels(printer.resolution()).x()
        )
        marginX = (
            int(Preferences.getPrinter("LeftMargin") * printer.resolution() / 2.54)
            - marginX
        )
        marginY = (
            printer.pageLayout().paintRectPixels(printer.resolution()).y()
            - printer.pageLayout().fullRectPixels(printer.resolution()).y()
        )
        marginY = (
            int(Preferences.getPrinter("TopMargin") * printer.resolution() / 2.54)
            - marginY
        )

        width = (
            printer.width()
            - marginX
            - int(Preferences.getPrinter("RightMargin") * printer.resolution() / 2.54)
        )
        height = (
            printer.height()
            - fontHeight
            - 4
            - marginY
            - int(Preferences.getPrinter("BottomMargin") * printer.resolution() / 2.54)
        )

        # write a foot note
        s = self.tr("Diagram: {0}").format(self.getDiagramName())
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
            s,
        )

        # render the diagram
        painter.setViewport(marginX, marginY, width, height)
        self.svgWidget.renderer().render(painter)
        painter.end()
