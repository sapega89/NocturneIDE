# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a subclass of EricGraphicsView for our diagrams.
"""

import pathlib

from PyQt6.QtCore import (
    QEvent,
    QMarginsF,
    QRectF,
    QSignalMapper,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QAction, QPageLayout
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter, QPrintPreviewDialog
from PyQt6.QtWidgets import QDialog, QGraphicsView, QToolBar

from eric7 import Preferences
from eric7.EricGraphics.EricGraphicsView import EricGraphicsView
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricZoomWidget import EricZoomWidget

from .AssociationItem import AssociationItem
from .ClassItem import ClassItem
from .ModuleItem import ModuleItem
from .PackageItem import PackageItem
from .UMLItem import UMLItem


class UMLGraphicsView(EricGraphicsView):
    """
    Class implementing a specialized EricGraphicsView for our diagrams.

    @signal relayout() emitted to indicate a relayout of the diagram
        is requested
    """

    relayout = pyqtSignal()

    def __init__(self, scene, parent=None):
        """
        Constructor

        @param scene reference to the scene object
        @type QGraphicsScene
        @param parent parent widget of the view
        @type QWidget
        """
        EricGraphicsView.__init__(
            self,
            scene,
            drawingMode=Preferences.getGraphics("DrawingMode"),
            parent=parent,
        )
        self.setObjectName("UMLGraphicsView")
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        self.diagramName = "Unnamed"
        self.__itemId = -1

        self.border = 10
        self.deltaSize = 100.0

        self.__zoomWidget = EricZoomWidget(
            EricPixmapCache.getPixmap("zoomOut"),
            EricPixmapCache.getPixmap("zoomIn"),
            EricPixmapCache.getPixmap("zoomReset"),
            self,
        )
        parent.statusBar().addPermanentWidget(self.__zoomWidget)
        self.__zoomWidget.setMapping(
            EricGraphicsView.ZoomLevels, EricGraphicsView.ZoomLevelDefault
        )
        self.__zoomWidget.valueChanged.connect(self.setZoom)
        self.zoomValueChanged.connect(self.__zoomWidget.setValue)

        self.__initActions()

        scene.changed.connect(self.__sceneChanged)

        self.grabGesture(Qt.GestureType.PinchGesture)

    def __initActions(self):
        """
        Private method to initialize the view actions.
        """
        self.alignMapper = QSignalMapper(self)
        self.alignMapper.mappedInt.connect(self.__alignShapes)

        self.deleteShapeAct = QAction(
            EricPixmapCache.getIcon("deleteShape"), self.tr("Delete shapes"), self
        )
        self.deleteShapeAct.triggered.connect(self.__deleteShape)

        self.incWidthAct = QAction(
            EricPixmapCache.getIcon("sceneWidthInc"),
            self.tr("Increase width by {0} points").format(self.deltaSize),
            self,
        )
        self.incWidthAct.triggered.connect(self.__incWidth)

        self.incHeightAct = QAction(
            EricPixmapCache.getIcon("sceneHeightInc"),
            self.tr("Increase height by {0} points").format(self.deltaSize),
            self,
        )
        self.incHeightAct.triggered.connect(self.__incHeight)

        self.decWidthAct = QAction(
            EricPixmapCache.getIcon("sceneWidthDec"),
            self.tr("Decrease width by {0} points").format(self.deltaSize),
            self,
        )
        self.decWidthAct.triggered.connect(self.__decWidth)

        self.decHeightAct = QAction(
            EricPixmapCache.getIcon("sceneHeightDec"),
            self.tr("Decrease height by {0} points").format(self.deltaSize),
            self,
        )
        self.decHeightAct.triggered.connect(self.__decHeight)

        self.setSizeAct = QAction(
            EricPixmapCache.getIcon("sceneSize"), self.tr("Set size"), self
        )
        self.setSizeAct.triggered.connect(self.__setSize)

        self.rescanAct = QAction(
            EricPixmapCache.getIcon("rescan"), self.tr("Re-Scan"), self
        )
        self.rescanAct.triggered.connect(self.__rescan)

        self.relayoutAct = QAction(
            EricPixmapCache.getIcon("relayout"), self.tr("Re-Layout"), self
        )
        self.relayoutAct.triggered.connect(self.__relayout)

        self.alignLeftAct = QAction(
            EricPixmapCache.getIcon("shapesAlignLeft"), self.tr("Align Left"), self
        )
        self.alignMapper.setMapping(self.alignLeftAct, Qt.AlignmentFlag.AlignLeft)
        self.alignLeftAct.triggered.connect(self.alignMapper.map)

        self.alignHCenterAct = QAction(
            EricPixmapCache.getIcon("shapesAlignHCenter"),
            self.tr("Align Center Horizontal"),
            self,
        )
        self.alignMapper.setMapping(self.alignHCenterAct, Qt.AlignmentFlag.AlignHCenter)
        self.alignHCenterAct.triggered.connect(self.alignMapper.map)

        self.alignRightAct = QAction(
            EricPixmapCache.getIcon("shapesAlignRight"), self.tr("Align Right"), self
        )
        self.alignMapper.setMapping(self.alignRightAct, Qt.AlignmentFlag.AlignRight)
        self.alignRightAct.triggered.connect(self.alignMapper.map)

        self.alignTopAct = QAction(
            EricPixmapCache.getIcon("shapesAlignTop"), self.tr("Align Top"), self
        )
        self.alignMapper.setMapping(self.alignTopAct, Qt.AlignmentFlag.AlignTop)
        self.alignTopAct.triggered.connect(self.alignMapper.map)

        self.alignVCenterAct = QAction(
            EricPixmapCache.getIcon("shapesAlignVCenter"),
            self.tr("Align Center Vertical"),
            self,
        )
        self.alignMapper.setMapping(self.alignVCenterAct, Qt.AlignmentFlag.AlignVCenter)
        self.alignVCenterAct.triggered.connect(self.alignMapper.map)

        self.alignBottomAct = QAction(
            EricPixmapCache.getIcon("shapesAlignBottom"), self.tr("Align Bottom"), self
        )
        self.alignMapper.setMapping(self.alignBottomAct, Qt.AlignmentFlag.AlignBottom)
        self.alignBottomAct.triggered.connect(self.alignMapper.map)

    def setLayoutActionsEnabled(self, enable):
        """
        Public method to enable or disable the layout related actions.

        @param enable flag indicating the desired enable state
        @type bool
        """
        self.rescanAct.setEnabled(enable)
        self.relayoutAct.setEnabled(enable)

    def __checkSizeActions(self):
        """
        Private slot to set the enabled state of the size actions.
        """
        diagramSize = self._getDiagramSize(10)
        sceneRect = self.scene().sceneRect()
        if (sceneRect.width() - self.deltaSize) < diagramSize.width():
            self.decWidthAct.setEnabled(False)
        else:
            self.decWidthAct.setEnabled(True)
        if (sceneRect.height() - self.deltaSize) < diagramSize.height():
            self.decHeightAct.setEnabled(False)
        else:
            self.decHeightAct.setEnabled(True)

    @pyqtSlot("QList<QRectF>")
    def __sceneChanged(self, _areas):
        """
        Private slot called when the scene changes.

        @param _areas list of rectangles that contain changes (unused)
        @type list of QRectF
        """
        if len(self.scene().selectedItems()) > 0:
            self.deleteShapeAct.setEnabled(True)
        else:
            self.deleteShapeAct.setEnabled(False)

        sceneRect = self.scene().sceneRect()
        newWidth = width = sceneRect.width()
        newHeight = height = sceneRect.height()
        rect = self.scene().itemsBoundingRect()
        # calculate with 10 pixel border on each side
        if sceneRect.right() - 10 < rect.right():
            newWidth = rect.right() + 10
        if sceneRect.bottom() - 10 < rect.bottom():
            newHeight = rect.bottom() + 10

        if newHeight != height or newWidth != width:
            self.setSceneSize(newWidth, newHeight)
            self.__checkSizeActions()

    def initToolBar(self):
        """
        Public method to populate a toolbar with our actions.

        @return the populated toolBar
        @rtype QToolBar
        """
        toolBar = QToolBar(self.tr("Graphics"), self)
        toolBar.addAction(self.deleteShapeAct)
        toolBar.addSeparator()
        toolBar.addAction(self.alignLeftAct)
        toolBar.addAction(self.alignHCenterAct)
        toolBar.addAction(self.alignRightAct)
        toolBar.addAction(self.alignTopAct)
        toolBar.addAction(self.alignVCenterAct)
        toolBar.addAction(self.alignBottomAct)
        toolBar.addSeparator()
        toolBar.addAction(self.incWidthAct)
        toolBar.addAction(self.incHeightAct)
        toolBar.addAction(self.decWidthAct)
        toolBar.addAction(self.decHeightAct)
        toolBar.addAction(self.setSizeAct)
        toolBar.addSeparator()
        toolBar.addAction(self.rescanAct)
        toolBar.addAction(self.relayoutAct)

        return toolBar

    def filteredItems(self, items, itemType=UMLItem):
        """
        Public method to filter a list of items.

        @param items list of items as returned by the scene object
        @type QGraphicsItem
        @param itemType type to be filtered
        @type class
        @return list of interesting collision items
        @rtype QGraphicsItem
        """
        return [itm for itm in items if isinstance(itm, itemType)]

    def selectItems(self, items):
        """
        Public method to select the given items.

        @param items list of items to be selected
        @type list of QGraphicsItemItem
        """
        # step 1: deselect all items
        self.unselectItems()

        # step 2: select all given items
        for itm in items:
            if isinstance(itm, UMLItem):
                itm.setSelected(True)

    def selectItem(self, item):
        """
        Public method to select an item.

        @param item item to be selected
        @type QGraphicsItemItem
        """
        if isinstance(item, UMLItem):
            item.setSelected(not item.isSelected())

    def __deleteShape(self):
        """
        Private method to delete the selected shapes from the display.
        """
        for item in self.scene().selectedItems():
            item.removeAssociations()
            item.setSelected(False)
            self.scene().removeItem(item)
            del item

    def __incWidth(self):
        """
        Private method to handle the increase width context menu entry.
        """
        self.resizeScene(self.deltaSize, True)
        self.__checkSizeActions()

    def __incHeight(self):
        """
        Private method to handle the increase height context menu entry.
        """
        self.resizeScene(self.deltaSize, False)
        self.__checkSizeActions()

    def __decWidth(self):
        """
        Private method to handle the decrease width context menu entry.
        """
        self.resizeScene(-self.deltaSize, True)
        self.__checkSizeActions()

    def __decHeight(self):
        """
        Private method to handle the decrease height context menu entry.
        """
        self.resizeScene(-self.deltaSize, False)
        self.__checkSizeActions()

    def __setSize(self):
        """
        Private method to handle the set size context menu entry.
        """
        from .UMLSceneSizeDialog import UMLSceneSizeDialog

        rect = self._getDiagramRect(10)
        sceneRect = self.scene().sceneRect()
        dlg = UMLSceneSizeDialog(
            sceneRect.width(),
            sceneRect.height(),
            rect.width(),
            rect.height(),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            width, height = dlg.getData()
            self.setSceneSize(width, height)
        self.__checkSizeActions()

    def autoAdjustSceneSize(self, limit=False):
        """
        Public method to adjust the scene size to the diagram size.

        @param limit flag indicating to limit the scene to the
            initial size
        @type bool
        """
        super().autoAdjustSceneSize(limit=limit)
        self.__checkSizeActions()

    def saveImage(self):
        """
        Public method to handle the save context menu entry.
        """
        fname, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.tr("Save Diagram"),
            "",
            self.tr(
                "Portable Network Graphics (*.png);;Scalable Vector Graphics (*.svg)"
            ),
            "",
            EricFileDialog.DontConfirmOverwrite,
        )
        if fname:
            fpath = pathlib.Path(fname)
            if not fpath.suffix:
                ex = selectedFilter.split("(*")[1].split(")")[0]
                if ex:
                    fpath = fpath.with_suffix(ex)
            if fpath.exists():
                res = EricMessageBox.yesNo(
                    self,
                    self.tr("Save Diagram"),
                    self.tr(
                        "<p>The file <b>{0}</b> already exists. Overwrite it?</p>"
                    ).format(fpath),
                    icon=EricMessageBox.Warning,
                )
                if not res:
                    return

            success = super().saveImage(str(fpath), fpath.suffix.upper()[1:])
            if not success:
                EricMessageBox.critical(
                    self,
                    self.tr("Save Diagram"),
                    self.tr(
                        """<p>The file <b>{0}</b> could not be saved.</p>"""
                    ).format(fpath),
                )

    def __relayout(self):
        """
        Private slot to handle the re-layout context menu entry.
        """
        self.__itemId = -1
        self.scene().clear()
        self.relayout.emit()

    def __rescan(self):
        """
        Private slot to handle the re-scan context menu entry.
        """
        # 1. save positions of all items and names of selected items
        itemPositions = {}
        selectedItems = []
        for item in self.filteredItems(self.scene().items(), UMLItem):
            name = item.getName()
            if name:
                itemPositions[name] = (item.x(), item.y())
                if item.isSelected():
                    selectedItems.append(name)

        # 2. save

        # 2. re-layout the diagram
        self.__relayout()

        # 3. move known items to the saved positions
        for item in self.filteredItems(self.scene().items(), UMLItem):
            name = item.getName()
            if name in itemPositions:
                item.setPos(*itemPositions[name])
            if name in selectedItems:
                item.setSelected(True)

    def printDiagram(self):
        """
        Public slot called to print the diagram.
        """
        printer = QPrinter(mode=QPrinter.PrinterMode.PrinterResolution)
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

        printDialog = QPrintDialog(printer, parent=self)
        if printDialog.exec():
            super().printDiagram(
                printer,
                margins=QMarginsF(
                    Preferences.getPrinter("LeftMargin"),
                    Preferences.getPrinter("TopMargin"),
                    Preferences.getPrinter("RightMargin"),
                    Preferences.getPrinter("BottomMargin"),
                ),
                diagramName=self.diagramName,
            )

    def printPreviewDiagram(self):
        """
        Public slot called to show a print preview of the diagram.
        """
        printer = QPrinter(mode=QPrinter.PrinterMode.PrinterResolution)
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
        preview.paintRequested[QPrinter].connect(self.__printPreviewPrint)
        preview.exec()

    def __printPreviewPrint(self, printer):
        """
        Private slot to generate a print preview.

        @param printer reference to the printer object
        @type QPrinter
        """
        super().printDiagram(
            printer,
            margins=QMarginsF(
                Preferences.getPrinter("LeftMargin"),
                Preferences.getPrinter("TopMargin"),
                Preferences.getPrinter("RightMargin"),
                Preferences.getPrinter("BottomMargin"),
            ),
            diagramName=self.diagramName,
        )

    def setDiagramName(self, name):
        """
        Public slot to set the diagram name.

        @param name diagram name
        @type str
        """
        self.diagramName = name

    def __alignShapes(self, alignment):
        """
        Private slot to align the selected shapes.

        @param alignment alignment type
        @type Qt.AlignmentFlag
        """
        # step 1: get all selected items
        items = self.scene().selectedItems()
        if len(items) <= 1:
            return

        # step 2: find the index of the item to align in relation to
        amount = None
        for i, item in enumerate(items):
            rect = item.sceneBoundingRect()
            if alignment == Qt.AlignmentFlag.AlignLeft and (
                amount is None or rect.x() < amount
            ):
                amount = rect.x()
                index = i
            elif alignment == Qt.AlignmentFlag.AlignRight and (
                amount is None or rect.x() + rect.width() > amount
            ):
                amount = rect.x() + rect.width()
                index = i
            elif alignment == Qt.AlignmentFlag.AlignHCenter and (
                amount is None or rect.width() > amount
            ):
                amount = rect.width()
                index = i
            elif alignment == Qt.AlignmentFlag.AlignTop and (
                amount is None or rect.y() < amount
            ):
                amount = rect.y()
                index = i
            elif alignment == Qt.AlignmentFlag.AlignBottom and (
                amount is None or rect.y() + rect.height() > amount
            ):
                amount = rect.y() + rect.height()
                index = i
            elif alignment == Qt.AlignmentFlag.AlignVCenter and (
                amount is None or rect.height() > amount
            ):
                amount = rect.height()
                index = i
        rect = items[index].sceneBoundingRect()

        # step 3: move the other items
        for i, item in enumerate(items):
            if i == index:
                continue
            itemrect = item.sceneBoundingRect()
            xOffset = yOffset = 0
            if alignment == Qt.AlignmentFlag.AlignLeft:
                xOffset = rect.x() - itemrect.x()
            elif alignment == Qt.AlignmentFlag.AlignRight:
                xOffset = (rect.x() + rect.width()) - (itemrect.x() + itemrect.width())
            elif alignment == Qt.AlignmentFlag.AlignHCenter:
                xOffset = (rect.x() + rect.width() // 2) - (
                    itemrect.x() + itemrect.width() // 2
                )
            elif alignment == Qt.AlignmentFlag.AlignTop:
                yOffset = rect.y() - itemrect.y()
            elif alignment == Qt.AlignmentFlag.AlignBottom:
                yOffset = (rect.y() + rect.height()) - (
                    itemrect.y() + itemrect.height()
                )
            elif alignment == Qt.AlignmentFlag.AlignVCenter:
                yOffset = (rect.y() + rect.height() // 2) - (
                    itemrect.y() + itemrect.height() // 2
                )
            item.moveBy(xOffset, yOffset)

        self.scene().update()

    def __itemsBoundingRect(self, items):
        """
        Private method to calculate the bounding rectangle of the given items.

        @param items list of items to operate on
        @type list of UMLItem
        @return bounding rectangle
        @rtype QRectF
        """
        rect = self.scene().sceneRect()
        right = rect.left()
        bottom = rect.top()
        left = rect.right()
        top = rect.bottom()
        for item in items:
            rect = item.sceneBoundingRect()
            left = min(rect.left(), left)
            right = max(rect.right(), right)
            top = min(rect.top(), top)
            bottom = max(rect.bottom(), bottom)
        return QRectF(left, top, right - left, bottom - top)

    def keyPressEvent(self, evt):
        """
        Protected method handling key press events.

        @param evt reference to the key event
        @type QKeyEvent
        """
        key = evt.key()
        if key in [Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right]:
            items = self.filteredItems(self.scene().selectedItems())
            if items:
                if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    stepSize = 50
                else:
                    stepSize = 5
                if key == Qt.Key.Key_Up:
                    dx = 0
                    dy = -stepSize
                elif key == Qt.Key.Key_Down:
                    dx = 0
                    dy = stepSize
                elif key == Qt.Key.Key_Left:
                    dx = -stepSize
                    dy = 0
                else:
                    dx = stepSize
                    dy = 0
                for item in items:
                    item.moveBy(dx, dy)
                evt.accept()
                return

        super().keyPressEvent(evt)

    def wheelEvent(self, evt):
        """
        Protected method to handle wheel events.

        @param evt reference to the wheel event
        @type QWheelEvent
        """
        if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = evt.angleDelta().y()
            if delta < 0:
                self.zoomOut()
            elif delta > 0:
                self.zoomIn()
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
                pinch.setTotalScaleFactor(self.zoom() / 100.0)
            elif pinch.state() == Qt.GestureState.GestureUpdated:
                self.setZoom(int(pinch.totalScaleFactor() * 100))
            evt.accept()

    def getItemId(self):
        """
        Public method to get the ID to be assigned to an item.

        @return item ID
        @rtype int
        """
        self.__itemId += 1
        return self.__itemId

    def findItem(self, itemId):
        """
        Public method to find an UML item based on the ID.

        @param itemId of the item to search for
        @type int
        @return item found or None
        @rtype UMLItem
        """
        for item in self.scene().items():
            try:
                if item.getId() == itemId:
                    return item
            except AttributeError:
                continue

        return None

    def findItemByName(self, name):
        """
        Public method to find an UML item based on its name.

        @param name name to look for
        @type str
        @return item found or None
        @rtype UMLItem
        """
        for item in self.scene().items():
            try:
                if item.getName() == name:
                    return item
            except AttributeError:
                continue

        return None

    def parsePersistenceData(self, version, data):
        """
        Public method to parse persisted data.

        @param version version of the data
        @type str
        @param data persisted data to be parsed
        @type list of str
        @return tuple of flag indicating success (boolean) and faulty line
            number
        @rtype int
        """
        umlItems = {}

        if not data[0].startswith("diagram_name:"):
            return False, 0
        self.diagramName = data[0].split(": ", 1)[1].strip()

        colors = self.getDrawingColors(
            drawingMode=Preferences.getGraphics("DrawingMode")
        )
        for linenum, line in enumerate(data[1:], start=1):
            if not line.startswith(("item:", "association:")):
                return False, linenum

            key, value = line.split(": ", 1)
            if key == "item":
                itemId, x, y, itemType, itemData = value.split(", ", 4)
                try:
                    itemId = int(itemId.split("=", 1)[1].strip())
                    x = float(x.split("=", 1)[1].strip())
                    y = float(y.split("=", 1)[1].strip())
                    itemType = itemType.split("=", 1)[1].strip()
                    if itemType == ClassItem.ItemType:
                        itm = ClassItem(x=0, y=0, scene=self.scene(), colors=colors)
                    elif itemType == ModuleItem.ItemType:
                        itm = ModuleItem(x=0, y=0, scene=self.scene(), colors=colors)
                    elif itemType == PackageItem.ItemType:
                        itm = PackageItem(x=0, y=0, scene=self.scene(), colors=colors)
                    itm.setPos(x, y)
                    itm.setId(itemId)
                    umlItems[itemId] = itm
                    if not itm.parseItemDataString(version, itemData):
                        return False, linenum
                except ValueError:
                    return False, linenum
            elif key == "association":
                (
                    srcId,
                    dstId,
                    assocType,
                    topToBottom,
                ) = AssociationItem.parseAssociationItemDataString(value.strip())
                assoc = AssociationItem(
                    umlItems[srcId], umlItems[dstId], assocType, topToBottom
                )
                self.scene().addItem(assoc)

        return True, -1

    def toDict(self):
        """
        Public method to collect data to be persisted.

        @return dictionary containing data to be persisted
        @rtype dict
        """
        items = [
            item.toDict() for item in self.filteredItems(self.scene().items(), UMLItem)
        ]

        associations = [
            assoc.toDict()
            for assoc in self.filteredItems(self.scene().items(), AssociationItem)
        ]

        data = {
            "diagram_name": self.diagramName,
            "items": items,
            "associations": associations,
        }

        return data

    def fromDict(self, _version, data):
        """
        Public method to populate the class with data persisted by 'toDict()'.

        @param _version version of the data (unused)
        @type str
        @param data dictionary containing the persisted data
        @type dict
        @return flag indicating success
        @rtype bool
        """
        from .AssociationItem import AssociationItem
        from .ClassItem import ClassItem
        from .ModuleItem import ModuleItem
        from .PackageItem import PackageItem
        from .UMLItem import UMLItem

        umlItems = {}
        colors = self.getDrawingColors(
            drawingMode=Preferences.getGraphics("DrawingMode")
        )

        try:
            self.diagramName = data["diagram_name"]
            for itemData in data["items"]:
                if itemData["type"] == UMLItem.ItemType:
                    itm = UMLItem.fromDict(itemData, colors=colors)
                elif itemData["type"] == ClassItem.ItemType:
                    itm = ClassItem.fromDict(itemData, colors=colors)
                elif itemData["type"] == ModuleItem.ItemType:
                    itm = ModuleItem.fromDict(itemData, colors=colors)
                elif itemData["type"] == PackageItem.ItemType:
                    itm = PackageItem.fromDict(itemData, colors=colors)
                if itm is not None:
                    umlItems[itm.getId()] = itm
                    self.scene().addItem(itm)

            for assocData in data["associations"]:
                assoc = AssociationItem.fromDict(assocData, umlItems, colors=colors)
                self.scene().addItem(assoc)

            return True
        except KeyError:
            return False
