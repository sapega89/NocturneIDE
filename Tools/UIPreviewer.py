# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the UI Previewer main window.
"""

import contextlib
import pathlib

from PyQt6 import uic
from PyQt6.QtCore import QDir, QEvent, QSize, Qt
from PyQt6.QtGui import QAction, QImageWriter, QKeySequence, QPainter
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter, QPrintPreviewDialog
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QStyleFactory,
    QVBoxLayout,
    QWhatsThis,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricMainWindow import EricMainWindow


class UIPreviewer(EricMainWindow):
    """
    Class implementing the UI Previewer main window.
    """

    def __init__(self, filename=None, parent=None, name=None):
        """
        Constructor

        @param filename name of a UI file to load
        @type str
        @param parent parent widget of this window
        @type QWidget
        @param name name of this window
        @type str
        """
        self.mainWidget = None
        self.currentFile = QDir.currentPath()

        super().__init__(parent)
        if not name:
            self.setObjectName("UIPreviewer")
        else:
            self.setObjectName(name)

        self.setStyle(
            styleName=Preferences.getUI("Style"),
            styleSheetFile=Preferences.getUI("StyleSheet"),
            itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
        )

        self.resize(QSize(600, 480).expandedTo(self.minimumSizeHint()))
        self.statusBar()

        self.setWindowIcon(EricPixmapCache.getIcon("eric"))
        self.setWindowTitle(self.tr("UI Previewer"))

        self.cw = QWidget(self)
        self.cw.setObjectName("centralWidget")

        self.UIPreviewerLayout = QVBoxLayout(self.cw)
        self.UIPreviewerLayout.setContentsMargins(6, 6, 6, 6)
        self.UIPreviewerLayout.setSpacing(6)
        self.UIPreviewerLayout.setObjectName("UIPreviewerLayout")

        self.styleLayout = QHBoxLayout()
        self.styleLayout.setContentsMargins(0, 0, 0, 0)
        self.styleLayout.setSpacing(6)
        self.styleLayout.setObjectName("styleLayout")

        self.styleLabel = QLabel(self.tr("Select GUI Theme"), self.cw)
        self.styleLabel.setObjectName("styleLabel")
        self.styleLayout.addWidget(self.styleLabel)

        self.styleCombo = QComboBox(self.cw)
        self.styleCombo.setObjectName("styleCombo")
        self.styleCombo.setEditable(False)
        self.styleCombo.setToolTip(self.tr("Select the GUI Theme"))
        self.styleLayout.addWidget(self.styleCombo)
        self.styleCombo.addItems(sorted(QStyleFactory().keys()))
        currentStyle = Preferences.getSettings().value("UIPreviewer/style")
        if currentStyle is not None:
            self.styleCombo.setCurrentIndex(int(currentStyle))

        styleSpacer = QSpacerItem(
            40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.styleLayout.addItem(styleSpacer)
        self.UIPreviewerLayout.addLayout(self.styleLayout)

        self.previewSV = QScrollArea(self.cw)
        self.previewSV.setObjectName("preview")
        self.previewSV.setFrameShape(QFrame.Shape.NoFrame)
        self.previewSV.setFrameShadow(QFrame.Shadow.Plain)
        self.previewSV.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.UIPreviewerLayout.addWidget(self.previewSV)

        self.setCentralWidget(self.cw)

        self.styleCombo.activated[int].connect(self.__guiStyleSelected)

        self.__initActions()
        self.__initMenus()
        self.__initToolbars()

        self.__updateActions()

        # defere loading of a UI file until we are shown
        self.fileToLoad = filename

    def show(self):
        """
        Public slot to show this dialog.

        This overloaded slot loads a UI file to be previewed after
        the main window has been shown. This way, previewing a dialog
        doesn't interfere with showing the main window.
        """
        super().show()
        if self.fileToLoad is not None:
            fn, self.fileToLoad = (self.fileToLoad, None)
            self.__loadFile(fn)

    def __initActions(self):
        """
        Private method to define the user interface actions.
        """
        self.openAct = QAction(
            EricPixmapCache.getIcon("openUI"), self.tr("&Open File"), self
        )
        self.openAct.setShortcut(QKeySequence(self.tr("Ctrl+O", "File|Open")))
        self.openAct.setStatusTip(self.tr("Open a UI file for display"))
        self.openAct.setWhatsThis(
            self.tr(
                """<b>Open File</b>"""
                """<p>This opens a new UI file for display.</p>"""
            )
        )
        self.openAct.triggered.connect(self.__openFile)

        self.printAct = QAction(
            EricPixmapCache.getIcon("print"), self.tr("&Print"), self
        )
        self.printAct.setShortcut(QKeySequence(self.tr("Ctrl+P", "File|Print")))
        self.printAct.setStatusTip(self.tr("Print a screen capture"))
        self.printAct.setWhatsThis(
            self.tr("""<b>Print</b><p>Print a screen capture.</p>""")
        )
        self.printAct.triggered.connect(self.__printImage)

        self.printPreviewAct = QAction(
            EricPixmapCache.getIcon("printPreview"), self.tr("Print Preview"), self
        )
        self.printPreviewAct.setStatusTip(self.tr("Print preview a screen capture"))
        self.printPreviewAct.setWhatsThis(
            self.tr("""<b>Print Preview</b><p>Print preview a screen capture.</p>""")
        )
        self.printPreviewAct.triggered.connect(self.__printPreviewImage)

        self.imageAct = QAction(
            EricPixmapCache.getIcon("screenCapture"), self.tr("&Screen Capture"), self
        )
        self.imageAct.setShortcut(
            QKeySequence(self.tr("Ctrl+S", "File|Screen Capture"))
        )
        self.imageAct.setStatusTip(self.tr("Save a screen capture to an image file"))
        self.imageAct.setWhatsThis(
            self.tr(
                """<b>Screen Capture</b>"""
                """<p>Save a screen capture to an image file.</p>"""
            )
        )
        self.imageAct.triggered.connect(self.__saveImage)

        self.exitAct = QAction(EricPixmapCache.getIcon("exit"), self.tr("&Quit"), self)
        self.exitAct.setShortcut(QKeySequence(self.tr("Ctrl+Q", "File|Quit")))
        self.exitAct.setStatusTip(self.tr("Quit the application"))
        self.exitAct.setWhatsThis(
            self.tr("""<b>Quit</b><p>Quit the application.</p>""")
        )
        self.exitAct.triggered.connect(ericApp().closeAllWindows)

        self.copyAct = QAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("&Copy"), self
        )
        self.copyAct.setShortcut(QKeySequence(self.tr("Ctrl+C", "Edit|Copy")))
        self.copyAct.setStatusTip(self.tr("Copy screen capture to clipboard"))
        self.copyAct.setWhatsThis(
            self.tr("""<b>Copy</b><p>Copy screen capture to clipboard.</p>""")
        )
        self.copyAct.triggered.connect(self.__copyImageToClipboard)

        self.whatsThisAct = QAction(
            EricPixmapCache.getIcon("whatsThis"), self.tr("&What's This?"), self
        )
        self.whatsThisAct.setShortcut(QKeySequence(self.tr("Shift+F1")))
        self.whatsThisAct.setStatusTip(self.tr("Context sensitive help"))
        self.whatsThisAct.setWhatsThis(
            self.tr(
                """<b>Display context sensitive help</b>"""
                """<p>In What's This? mode, the mouse cursor shows an arrow"""
                """ with a question mark, and you can click on the interface"""
                """ elements to get a short description of what they do and"""
                """ how to use them. In dialogs, this feature can be accessed"""
                """ using the context help button in the titlebar.</p>"""
            )
        )
        self.whatsThisAct.triggered.connect(self.__whatsThis)

        self.aboutAct = QAction(self.tr("&About"), self)
        self.aboutAct.setStatusTip(self.tr("Display information about this software"))
        self.aboutAct.setWhatsThis(
            self.tr(
                """<b>About</b>"""
                """<p>Display some information about this software.</p>"""
            )
        )
        self.aboutAct.triggered.connect(self.__about)

        self.aboutQtAct = QAction(self.tr("About &Qt"), self)
        self.aboutQtAct.setStatusTip(
            self.tr("Display information about the Qt toolkit")
        )
        self.aboutQtAct.setWhatsThis(
            self.tr(
                """<b>About Qt</b>"""
                """<p>Display some information about the Qt toolkit.</p>"""
            )
        )
        self.aboutQtAct.triggered.connect(self.__aboutQt)

    def __initMenus(self):
        """
        Private method to create the menus.
        """
        mb = self.menuBar()

        menu = mb.addMenu(self.tr("&File"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.openAct)
        menu.addAction(self.imageAct)
        menu.addSeparator()
        menu.addAction(self.printPreviewAct)
        menu.addAction(self.printAct)
        menu.addSeparator()
        menu.addAction(self.exitAct)

        menu = mb.addMenu(self.tr("&Edit"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.copyAct)

        mb.addSeparator()

        menu = mb.addMenu(self.tr("&Help"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.aboutAct)
        menu.addAction(self.aboutQtAct)
        menu.addSeparator()
        menu.addAction(self.whatsThisAct)

    def __initToolbars(self):
        """
        Private method to create the toolbars.
        """
        filetb = self.addToolBar(self.tr("File"))
        filetb.addAction(self.openAct)
        filetb.addAction(self.imageAct)
        filetb.addSeparator()
        filetb.addAction(self.printPreviewAct)
        filetb.addAction(self.printAct)
        filetb.addSeparator()
        filetb.addAction(self.exitAct)

        edittb = self.addToolBar(self.tr("Edit"))
        edittb.addAction(self.copyAct)

        helptb = self.addToolBar(self.tr("Help"))
        helptb.addAction(self.whatsThisAct)

    def __whatsThis(self):
        """
        Private slot called in to enter Whats This mode.
        """
        QWhatsThis.enterWhatsThisMode()

    def __guiStyleSelected(self, index):
        """
        Private slot to handle the selection of a GUI style.

        @param index index of the selected entry
        @type int
        """
        selectedStyle = self.styleCombo.itemText(index)
        if self.mainWidget:
            self.__updateChildren(selectedStyle)

    def __about(self):
        """
        Private slot to show the about information.
        """
        EricMessageBox.about(
            self,
            self.tr("UI Previewer"),
            self.tr(
                """<h3> About UI Previewer </h3>"""
                """<p>The UI Previewer loads and displays Qt User-Interface"""
                """ files with various styles, which are selectable via a"""
                """ selection list.</p>"""
            ),
        )

    def __aboutQt(self):
        """
        Private slot to show info about Qt.
        """
        EricMessageBox.aboutQt(self, self.tr("UI Previewer"))

    def __openFile(self):
        """
        Private slot to load a new file.
        """
        fn = EricFileDialog.getOpenFileName(
            self,
            self.tr("Select UI file"),
            self.currentFile,
            self.tr("Qt User-Interface Files (*.ui)"),
        )
        if fn:
            self.__loadFile(fn)

    def __loadFile(self, fn):
        """
        Private slot to load a ui file.

        @param fn name of the ui file to be laoded
        @type str
        """
        if self.mainWidget:
            self.mainWidget.close()
            self.previewSV.takeWidget()
            del self.mainWidget
            self.mainWidget = None

        # load the file
        with contextlib.suppress(
            ImportError, NotImplementedError, SyntaxError, TypeError
        ):
            self.mainWidget = uic.loadUi(fn)

        if self.mainWidget:
            self.currentFile = fn
            self.__updateChildren(self.styleCombo.currentText())
            if isinstance(self.mainWidget, (QDialog, QMainWindow)):
                self.mainWidget.show()
                self.mainWidget.installEventFilter(self)
            else:
                self.previewSV.setWidget(self.mainWidget)
                self.mainWidget.show()
        else:
            EricMessageBox.warning(
                self,
                self.tr("Load UI File"),
                self.tr("""<p>The file <b>{0}</b> could not be loaded.</p>""").format(
                    fn
                ),
            )
        self.__updateActions()

    def __updateChildren(self, sstyle):
        """
        Private slot to change the style of the show UI.

        @param sstyle name of the selected style
        @type str
        """
        with EricOverrideCursor():
            qstyle = QStyleFactory.create(sstyle)
            self.mainWidget.setStyle(qstyle)

            lst = self.mainWidget.findChildren(QWidget)
            for obj in lst:
                with contextlib.suppress(AttributeError):
                    obj.setStyle(qstyle)
            del lst

            self.mainWidget.hide()
            self.mainWidget.show()

            self.lastQStyle = qstyle
            self.lastStyle = sstyle
            Preferences.getSettings().setValue(
                "UIPreviewer/style", self.styleCombo.currentIndex()
            )

    def __updateActions(self):
        """
        Private slot to update the actions state.
        """
        if self.mainWidget:
            self.imageAct.setEnabled(True)
            self.printAct.setEnabled(True)
            if self.printPreviewAct:
                self.printPreviewAct.setEnabled(True)
            self.copyAct.setEnabled(True)
            self.styleCombo.setEnabled(True)
        else:
            self.imageAct.setEnabled(False)
            self.printAct.setEnabled(False)
            if self.printPreviewAct:
                self.printPreviewAct.setEnabled(False)
            self.copyAct.setEnabled(False)
            self.styleCombo.setEnabled(False)

    def __handleCloseEvent(self):
        """
        Private slot to handle the close event of a viewed QMainWidget.
        """
        if self.mainWidget:
            self.mainWidget.removeEventFilter(self)
            del self.mainWidget
            self.mainWidget = None
        self.__updateActions()

    def eventFilter(self, obj, ev):
        """
        Public method called to filter an event.

        @param obj object, that generated the event
        @type QObject
        @param ev the event, that was generated by object
        @type QEvent
        @return flag indicating if event was filtered out
        @rtype bool
        """
        if obj == self.mainWidget:
            if ev.type() == QEvent.Type.Close:
                self.__handleCloseEvent()
            return True
        else:
            if isinstance(self.mainWidget, QDialog):
                return QDialog.eventFilter(self, obj, ev)
            elif isinstance(self.mainWidget, QMainWindow):
                return QMainWindow.eventFilter(self, obj, ev)
            else:
                return False

    def __saveImage(self):
        """
        Private slot to handle the Save Image menu action.
        """
        if self.mainWidget is None:
            EricMessageBox.critical(
                self, self.tr("Save Image"), self.tr("""There is no UI file loaded.""")
            )
            return

        defaultExt = "PNG"
        filters = ""
        formats = QImageWriter.supportedImageFormats()
        for imageFormat in formats:
            filters = "{0}*.{1} ".format(filters, bytes(imageFormat).decode().lower())
        fileFilter = self.tr("Images ({0})").format(filters[:-1])

        fname = EricFileDialog.getSaveFileName(
            self, self.tr("Save Image"), "", fileFilter
        )
        if not fname:
            return

        fpath = pathlib.Path(fname)
        ext = fpath.suffix.upper().replace(".", "")
        if not ext:
            ext = defaultExt
            fpath = fpath.with_suffix(".{0}".format(defaultExt.lower()))

        pix = self.mainWidget.grab()
        self.__updateChildren(self.lastStyle)
        if not pix.save(str(fpath), str(ext)):
            EricMessageBox.critical(
                self,
                self.tr("Save Image"),
                self.tr("""<p>The file <b>{0}</b> could not be saved.</p>""").format(
                    fpath
                ),
            )

    def __copyImageToClipboard(self):
        """
        Private slot to handle the Copy Image menu action.
        """
        if self.mainWidget is None:
            EricMessageBox.critical(
                self, self.tr("Save Image"), self.tr("""There is no UI file loaded.""")
            )
            return

        cb = QApplication.clipboard()
        cb.setPixmap(self.mainWidget.grab())
        self.__updateChildren(self.lastStyle)

    def __printImage(self):
        """
        Private slot to handle the Print Image menu action.
        """
        if self.mainWidget is None:
            EricMessageBox.critical(
                self, self.tr("Print Image"), self.tr("""There is no UI file loaded.""")
            )
            return

        settings = Preferences.getSettings()
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setFullPage(True)

        printerName = Preferences.getPrinter("UIPreviewer/printername")
        if printerName:
            printer.setPrinterName(printerName)
        printer.setPageSize(
            QPrinter.PageSize(int(settings.value("UIPreviewer/pagesize")))
        )
        printer.setPageOrder(
            QPrinter.PageOrder(int(settings.value("UIPreviewer/pageorder")))
        )
        printer.setOrientation(
            QPrinter.Orientation(int(settings.value("UIPreviewer/orientation")))
        )
        printer.setColorMode(
            QPrinter.ColorMode(int(settings.value("UIPreviewer/colormode")))
        )

        printDialog = QPrintDialog(printer, self)
        if printDialog.exec() == QDialog.DialogCode.Accepted:
            self.statusBar().showMessage(self.tr("Printing the image..."))
            self.__print(printer)

            settings.setValue("UIPreviewer/printername", printer.printerName())
            settings.setValue("UIPreviewer/pagesize", printer.pageSize())
            settings.setValue("UIPreviewer/pageorder", printer.pageOrder())
            settings.setValue("UIPreviewer/orientation", printer.orientation())
            settings.setValue("UIPreviewer/colormode", printer.colorMode())

        self.statusBar().showMessage(self.tr("Image sent to printer..."), 2000)

    def __printPreviewImage(self):
        """
        Private slot to handle the Print Preview menu action.
        """
        if self.mainWidget is None:
            EricMessageBox.critical(
                self,
                self.tr("Print Preview"),
                self.tr("""There is no UI file loaded."""),
            )
            return

        settings = Preferences.getSettings()
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setFullPage(True)

        printerName = Preferences.getPrinter("UIPreviewer/printername")
        if printerName:
            printer.setPrinterName(printerName)
        printer.setPageSize(
            QPrinter.PageSize(int(settings.value("UIPreviewer/pagesize")))
        )
        printer.setPageOrder(
            QPrinter.PageOrder(int(settings.value("UIPreviewer/pageorder")))
        )
        printer.setOrientation(
            QPrinter.Orientation(int(settings.value("UIPreviewer/orientation")))
        )
        printer.setColorMode(
            QPrinter.ColorMode(int(settings.value("UIPreviewer/colormode")))
        )

        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(self.__print)
        preview.exec()

    def __print(self, printer):
        """
        Private slot to the actual printing.

        @param printer reference to the printer object
        @type QPrinter
        """
        p = QPainter(printer)
        marginX = (
            printer.pageLayout().paintRectPixels(printer.resolution()).x()
            - printer.pageLayout().fullRectPixels(printer.resolution()).x()
        ) // 2
        marginY = (
            printer.pageLayout().paintRectPixels(printer.resolution()).y()
            - printer.pageLayout().fullRectPixels(printer.resolution()).y()
        ) // 2

        # double the margin on bottom of page
        if printer.orientation() == QPrinter.Orientation.Portrait:
            width = printer.width() - marginX * 2
            height = printer.height() - marginY * 3
        else:
            marginX *= 2
            width = printer.width() - marginX * 2
            height = printer.height() - marginY * 2
        img = self.mainWidget.grab().toImage()
        self.__updateChildren(self.lastStyle)
        p.drawImage(
            marginX,
            marginY,
            img.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ),
        )
        p.end()
