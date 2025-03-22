# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the icon editor main window.
"""

import contextlib
import os
import pathlib

from PyQt6.QtCore import (
    QBuffer,
    QByteArray,
    QEvent,
    QSignalMapper,
    QSize,
    Qt,
    pyqtSignal,
)
from PyQt6.QtGui import QImage, QImageReader, QImageWriter, QKeySequence, QPalette
from PyQt6.QtWidgets import QDockWidget, QLabel, QScrollArea, QWhatsThis

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction, createActionGroup
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.EricWidgets.EricZoomWidget import EricZoomWidget
from eric7.SystemUtilities import FileSystemUtilities

from .IconEditorGrid import IconEditorGrid, IconEditorTool


class IconEditorWindow(EricMainWindow):
    """
    Class implementing the web browser main window.

    @signal editorClosed() emitted after the window was requested to close down
    """

    editorClosed = pyqtSignal()

    windows = []

    def __init__(
        self,
        fileName="",
        parent=None,
        fromEric=False,
        initShortcutsOnly=False,
        project=None,
    ):
        """
        Constructor

        @param fileName name of a file to load on startup
        @type str
        @param parent parent widget of this window
        @type QWidget
        @param fromEric flag indicating whether it was called from within
            eric
        @type bool
        @param initShortcutsOnly flag indicating to just initialize the
            keyboard shortcuts
        @type bool
        @param project reference to the project object
        @type Project
        """
        super().__init__(parent)
        self.setObjectName("eric7_icon_editor")

        self.fromEric = fromEric
        self.initShortcutsOnly = initShortcutsOnly
        self.setWindowIcon(EricPixmapCache.getIcon("iconEditor"))

        if self.initShortcutsOnly:
            self.__initActions()
        else:
            if not self.fromEric:
                self.setStyle(
                    styleName=Preferences.getUI("Style"),
                    styleSheetFile=Preferences.getUI("StyleSheet"),
                    itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
                )
            self.__editor = IconEditorGrid()
            self.__scrollArea = QScrollArea()
            self.__scrollArea.setWidget(self.__editor)
            self.__scrollArea.viewport().setBackgroundRole(QPalette.ColorRole.Dark)
            self.__scrollArea.viewport().setAutoFillBackground(True)
            self.setCentralWidget(self.__scrollArea)

            g = Preferences.getGeometry("IconEditorGeometry")
            if g.isEmpty():
                s = QSize(600, 500)
                self.resize(s)
            else:
                self.restoreGeometry(g)

            self.__initActions()
            self.__initMenus()
            self.__initToolbars()
            self.__createStatusBar()
            self.__initFileFilters()
            self.__createPaletteDock()

            self.__palette.previewChanged(self.__editor.previewPixmap())
            self.__palette.colorChanged(self.__editor.penColor())
            self.__palette.setCompositingMode(self.__editor.compositingMode())

            self.__class__.windows.append(self)

            state = Preferences.getIconEditor("IconEditorState")
            self.restoreState(state)

            self.__editor.imageChanged.connect(self.__modificationChanged)
            self.__editor.positionChanged.connect(self.__updatePosition)
            self.__editor.sizeChanged.connect(self.__updateSize)
            self.__editor.previewChanged.connect(self.__palette.previewChanged)
            self.__editor.colorChanged.connect(self.__palette.colorChanged)
            self.__palette.colorSelected.connect(self.__editor.setPenColor)
            self.__palette.compositingChanged.connect(self.__editor.setCompositingMode)

            self.__setCurrentFile("")
            if fileName:
                self.__loadIconFile(fileName)

            self.__checkActions()

            self.__project = project
            self.__lastOpenPath = ""
            self.__lastSavePath = ""

            self.grabGesture(Qt.GestureType.PinchGesture)

    def __initFileFilters(self):
        """
        Private method to define the supported image file filters.
        """
        filters = {
            "bmp": self.tr("Windows Bitmap File (*.bmp)"),
            "cur": self.tr("Windows Cursor File (*.cur)"),
            "dds": self.tr("DirectDraw-Surface File (*.dds)"),
            "gif": self.tr("Graphic Interchange Format File (*.gif)"),
            "icns": self.tr("Apple Icon File (*.icns)"),
            "ico": self.tr("Windows Icon File (*.ico)"),
            "jp2": self.tr("JPEG2000 File (*.jp2)"),
            "jpg": self.tr("JPEG File (*.jpg)"),
            "jpeg": self.tr("JPEG File (*.jpeg)"),
            "mng": self.tr("Multiple-Image Network Graphics File (*.mng)"),
            "pbm": self.tr("Portable Bitmap File (*.pbm)"),
            "pcx": self.tr("Paintbrush Bitmap File (*.pcx)"),
            "pgm": self.tr("Portable Graymap File (*.pgm)"),
            "png": self.tr("Portable Network Graphics File (*.png)"),
            "ppm": self.tr("Portable Pixmap File (*.ppm)"),
            "sgi": self.tr("Silicon Graphics Image File (*.sgi)"),
            "svg": self.tr("Scalable Vector Graphics File (*.svg)"),
            "svgz": self.tr("Compressed Scalable Vector Graphics File (*.svgz)"),
            "tga": self.tr("Targa Graphic File (*.tga)"),
            "tif": self.tr("TIFF File (*.tif)"),
            "tiff": self.tr("TIFF File (*.tiff)"),
            "wbmp": self.tr("WAP Bitmap File (*.wbmp)"),
            "webp": self.tr("WebP Image File (*.webp)"),
            "xbm": self.tr("X11 Bitmap File (*.xbm)"),
            "xpm": self.tr("X11 Pixmap File (*.xpm)"),
        }

        inputFormats = []
        readFormats = QImageReader.supportedImageFormats()
        for readFormat in readFormats:
            with contextlib.suppress(KeyError):
                inputFormats.append(filters[bytes(readFormat).decode()])
        inputFormats.sort()
        inputFormats.append(self.tr("All Files (*)"))
        self.__inputFilter = ";;".join(inputFormats)

        outputFormats = []
        writeFormats = QImageWriter.supportedImageFormats()
        for writeFormat in writeFormats:
            with contextlib.suppress(KeyError):
                outputFormats.append(filters[bytes(writeFormat).decode()])
        outputFormats.sort()
        self.__outputFilter = ";;".join(outputFormats)

        self.__defaultFilter = filters["png"]

    def __initActions(self):
        """
        Private method to define the user interface actions.
        """
        # list of all actions
        self.__actions = []

        self.__initFileActions()
        self.__initEditActions()
        self.__initViewActions()
        self.__initToolsActions()
        self.__initHelpActions()

    def __initFileActions(self):
        """
        Private method to define the file related user interface actions.
        """
        self.newAct = EricAction(
            self.tr("New"),
            EricPixmapCache.getIcon("new"),
            self.tr("&New"),
            QKeySequence(self.tr("Ctrl+N", "File|New")),
            0,
            self,
            "iconEditor_file_new",
        )
        self.newAct.setStatusTip(self.tr("Create a new icon"))
        self.newAct.setWhatsThis(
            self.tr("""<b>New</b><p>This creates a new icon.</p>""")
        )
        self.newAct.triggered.connect(self.__newIcon)
        self.__actions.append(self.newAct)

        self.newWindowAct = EricAction(
            self.tr("New Window"),
            EricPixmapCache.getIcon("newWindow"),
            self.tr("New &Window"),
            0,
            0,
            self,
            "iconEditor_file_new_window",
        )
        self.newWindowAct.setStatusTip(self.tr("Open a new icon editor window"))
        self.newWindowAct.setWhatsThis(
            self.tr(
                """<b>New Window</b>"""
                """<p>This opens a new icon editor window.</p>"""
            )
        )
        self.newWindowAct.triggered.connect(self.__newWindow)
        self.__actions.append(self.newWindowAct)

        self.openAct = EricAction(
            self.tr("Open"),
            EricPixmapCache.getIcon("documentOpen"),
            self.tr("&Open..."),
            QKeySequence(self.tr("Ctrl+O", "File|Open")),
            0,
            self,
            "iconEditor_file_open",
        )
        self.openAct.setStatusTip(self.tr("Open an icon file for editing"))
        self.openAct.setWhatsThis(
            self.tr(
                """<b>Open File</b>"""
                """<p>This opens a new icon file for editing."""
                """ It pops up a file selection dialog.</p>"""
            )
        )
        self.openAct.triggered.connect(self.__openIcon)
        self.__actions.append(self.openAct)

        self.saveAct = EricAction(
            self.tr("Save"),
            EricPixmapCache.getIcon("fileSave"),
            self.tr("&Save"),
            QKeySequence(self.tr("Ctrl+S", "File|Save")),
            0,
            self,
            "iconEditor_file_save",
        )
        self.saveAct.setStatusTip(self.tr("Save the current icon"))
        self.saveAct.setWhatsThis(
            self.tr(
                """<b>Save File</b>"""
                """<p>Save the contents of the icon editor window.</p>"""
            )
        )
        self.saveAct.triggered.connect(self.__saveIcon)
        self.__actions.append(self.saveAct)

        self.saveAsAct = EricAction(
            self.tr("Save As"),
            EricPixmapCache.getIcon("fileSaveAs"),
            self.tr("Save &As..."),
            QKeySequence(self.tr("Shift+Ctrl+S", "File|Save As")),
            0,
            self,
            "iconEditor_file_save_as",
        )
        self.saveAsAct.setStatusTip(self.tr("Save the current icon to a new file"))
        self.saveAsAct.setWhatsThis(
            self.tr(
                """<b>Save As...</b>"""
                """<p>Saves the current icon to a new file.</p>"""
            )
        )
        self.saveAsAct.triggered.connect(self.__saveIconAs)
        self.__actions.append(self.saveAsAct)

        self.closeAct = EricAction(
            self.tr("Close"),
            EricPixmapCache.getIcon("close"),
            self.tr("&Close"),
            QKeySequence(self.tr("Ctrl+W", "File|Close")),
            0,
            self,
            "iconEditor_file_close",
        )
        self.closeAct.setStatusTip(self.tr("Close the current icon editor window"))
        self.closeAct.setWhatsThis(
            self.tr("""<b>Close</b><p>Closes the current icon editor window.</p>""")
        )
        self.closeAct.triggered.connect(self.close)
        self.__actions.append(self.closeAct)

        self.closeAllAct = EricAction(
            self.tr("Close All"),
            self.tr("Close &All"),
            0,
            0,
            self,
            "iconEditor_file_close_all",
        )
        self.closeAllAct.setStatusTip(self.tr("Close all icon editor windows"))
        self.closeAllAct.setWhatsThis(
            self.tr(
                """<b>Close All</b>"""
                """<p>Closes all icon editor windows except the first one.</p>"""
            )
        )
        self.closeAllAct.triggered.connect(self.__closeAll)
        self.__actions.append(self.closeAllAct)

        self.closeOthersAct = EricAction(
            self.tr("Close Others"),
            self.tr("Close Others"),
            0,
            0,
            self,
            "iconEditor_file_close_others",
        )
        self.closeOthersAct.setStatusTip(self.tr("Close all other icon editor windows"))
        self.closeOthersAct.setWhatsThis(
            self.tr(
                """<b>Close Others</b>"""
                """<p>Closes all other icon editor windows.</p>"""
            )
        )
        self.closeOthersAct.triggered.connect(self.__closeOthers)
        self.__actions.append(self.closeOthersAct)

        self.exitAct = EricAction(
            self.tr("Quit"),
            EricPixmapCache.getIcon("exit"),
            self.tr("&Quit"),
            QKeySequence(self.tr("Ctrl+Q", "File|Quit")),
            0,
            self,
            "iconEditor_file_quit",
        )
        self.exitAct.setStatusTip(self.tr("Quit the icon editor"))
        self.exitAct.setWhatsThis(
            self.tr("""<b>Quit</b><p>Quit the icon editor.</p>""")
        )
        if not self.fromEric:
            self.exitAct.triggered.connect(self.__closeAll)
        self.__actions.append(self.exitAct)

    def __initEditActions(self):
        """
        Private method to create the Edit actions.
        """
        self.undoAct = EricAction(
            self.tr("Undo"),
            EricPixmapCache.getIcon("editUndo"),
            self.tr("&Undo"),
            QKeySequence(self.tr("Ctrl+Z", "Edit|Undo")),
            QKeySequence(self.tr("Alt+Backspace", "Edit|Undo")),
            self,
            "iconEditor_edit_undo",
        )
        self.undoAct.setStatusTip(self.tr("Undo the last change"))
        self.undoAct.setWhatsThis(
            self.tr("""<b>Undo</b><p>Undo the last change done.</p>""")
        )
        self.undoAct.triggered.connect(self.__editor.editUndo)
        self.__actions.append(self.undoAct)

        self.redoAct = EricAction(
            self.tr("Redo"),
            EricPixmapCache.getIcon("editRedo"),
            self.tr("&Redo"),
            QKeySequence(self.tr("Ctrl+Shift+Z", "Edit|Redo")),
            0,
            self,
            "iconEditor_edit_redo",
        )
        self.redoAct.setStatusTip(self.tr("Redo the last change"))
        self.redoAct.setWhatsThis(
            self.tr("""<b>Redo</b><p>Redo the last change done.</p>""")
        )
        self.redoAct.triggered.connect(self.__editor.editRedo)
        self.__actions.append(self.redoAct)

        self.cutAct = EricAction(
            self.tr("Cut"),
            EricPixmapCache.getIcon("editCut"),
            self.tr("Cu&t"),
            QKeySequence(self.tr("Ctrl+X", "Edit|Cut")),
            QKeySequence(self.tr("Shift+Del", "Edit|Cut")),
            self,
            "iconEditor_edit_cut",
        )
        self.cutAct.setStatusTip(self.tr("Cut the selection"))
        self.cutAct.setWhatsThis(
            self.tr(
                """<b>Cut</b>"""
                """<p>Cut the selected image area to the clipboard.</p>"""
            )
        )
        self.cutAct.triggered.connect(self.__editor.editCut)
        self.__actions.append(self.cutAct)

        self.copyAct = EricAction(
            self.tr("Copy"),
            EricPixmapCache.getIcon("editCopy"),
            self.tr("&Copy"),
            QKeySequence(self.tr("Ctrl+C", "Edit|Copy")),
            QKeySequence(self.tr("Ctrl+Ins", "Edit|Copy")),
            self,
            "iconEditor_edit_copy",
        )
        self.copyAct.setStatusTip(self.tr("Copy the selection"))
        self.copyAct.setWhatsThis(
            self.tr(
                """<b>Copy</b>"""
                """<p>Copy the selected image area to the clipboard.</p>"""
            )
        )
        self.copyAct.triggered.connect(self.__editor.editCopy)
        self.__actions.append(self.copyAct)

        self.pasteAct = EricAction(
            self.tr("Paste"),
            EricPixmapCache.getIcon("editPaste"),
            self.tr("&Paste"),
            QKeySequence(self.tr("Ctrl+V", "Edit|Paste")),
            QKeySequence(self.tr("Shift+Ins", "Edit|Paste")),
            self,
            "iconEditor_edit_paste",
        )
        self.pasteAct.setStatusTip(self.tr("Paste the clipboard image"))
        self.pasteAct.setWhatsThis(
            self.tr("""<b>Paste</b><p>Paste the clipboard image.</p>""")
        )
        self.pasteAct.triggered.connect(self.__editor.editPaste)
        self.__actions.append(self.pasteAct)

        self.pasteNewAct = EricAction(
            self.tr("Paste as New"),
            self.tr("Paste as &New"),
            0,
            0,
            self,
            "iconEditor_edit_paste_as_new",
        )
        self.pasteNewAct.setStatusTip(
            self.tr("Paste the clipboard image replacing the current one")
        )
        self.pasteNewAct.setWhatsThis(
            self.tr(
                """<b>Paste as New</b>"""
                """<p>Paste the clipboard image replacing the current one.</p>"""
            )
        )
        self.pasteNewAct.triggered.connect(self.__editor.editPasteAsNew)
        self.__actions.append(self.pasteNewAct)

        self.deleteAct = EricAction(
            self.tr("Clear"),
            EricPixmapCache.getIcon("editDelete"),
            self.tr("Cl&ear"),
            QKeySequence(self.tr("Alt+Shift+C", "Edit|Clear")),
            0,
            self,
            "iconEditor_edit_clear",
        )
        self.deleteAct.setStatusTip(self.tr("Clear the icon image"))
        self.deleteAct.setWhatsThis(
            self.tr(
                """<b>Clear</b>"""
                """<p>Clear the icon image and set it to be completely"""
                """ transparent.</p>"""
            )
        )
        self.deleteAct.triggered.connect(self.__editor.editClear)
        self.__actions.append(self.deleteAct)

        self.selectAllAct = EricAction(
            self.tr("Select All"),
            self.tr("&Select All"),
            QKeySequence(self.tr("Ctrl+A", "Edit|Select All")),
            0,
            self,
            "iconEditor_edit_select_all",
        )
        self.selectAllAct.setStatusTip(self.tr("Select the complete icon image"))
        self.selectAllAct.setWhatsThis(
            self.tr("""<b>Select All</b><p>Selects the complete icon image.</p>""")
        )
        self.selectAllAct.triggered.connect(self.__editor.editSelectAll)
        self.__actions.append(self.selectAllAct)

        self.resizeAct = EricAction(
            self.tr("Change Size"),
            EricPixmapCache.getIcon("transformResize"),
            self.tr("Change Si&ze..."),
            0,
            0,
            self,
            "iconEditor_edit_change_size",
        )
        self.resizeAct.setStatusTip(self.tr("Change the icon size"))
        self.resizeAct.setWhatsThis(
            self.tr("""<b>Change Size...</b><p>Changes the icon size.</p>""")
        )
        self.resizeAct.triggered.connect(self.__editor.editResize)
        self.__actions.append(self.resizeAct)

        self.grayscaleAct = EricAction(
            self.tr("Grayscale"),
            EricPixmapCache.getIcon("grayscale"),
            self.tr("&Grayscale"),
            0,
            0,
            self,
            "iconEditor_edit_grayscale",
        )
        self.grayscaleAct.setStatusTip(self.tr("Change the icon to grayscale"))
        self.grayscaleAct.setWhatsThis(
            self.tr("""<b>Grayscale</b><p>Changes the icon to grayscale.</p>""")
        )
        self.grayscaleAct.triggered.connect(self.__editor.grayScale)
        self.__actions.append(self.grayscaleAct)

        self.redoAct.setEnabled(False)
        self.__editor.canRedoChanged.connect(self.redoAct.setEnabled)

        self.undoAct.setEnabled(False)
        self.__editor.canUndoChanged.connect(self.undoAct.setEnabled)

        self.cutAct.setEnabled(False)
        self.copyAct.setEnabled(False)
        self.__editor.selectionAvailable.connect(self.cutAct.setEnabled)
        self.__editor.selectionAvailable.connect(self.copyAct.setEnabled)

        self.pasteAct.setEnabled(self.__editor.canPaste())
        self.pasteNewAct.setEnabled(self.__editor.canPaste())
        self.__editor.clipboardImageAvailable.connect(self.pasteAct.setEnabled)
        self.__editor.clipboardImageAvailable.connect(self.pasteNewAct.setEnabled)

    def __initViewActions(self):
        """
        Private method to create the View actions.
        """
        self.zoomInAct = EricAction(
            self.tr("Zoom in"),
            EricPixmapCache.getIcon("zoomIn"),
            self.tr("Zoom &in"),
            QKeySequence(self.tr("Ctrl++", "View|Zoom in")),
            0,
            self,
            "iconEditor_view_zoom_in",
        )
        self.zoomInAct.setStatusTip(self.tr("Zoom in on the icon"))
        self.zoomInAct.setWhatsThis(
            self.tr(
                """<b>Zoom in</b>"""
                """<p>Zoom in on the icon. This makes the grid bigger.</p>"""
            )
        )
        self.zoomInAct.triggered.connect(self.__zoomIn)
        self.__actions.append(self.zoomInAct)

        self.zoomOutAct = EricAction(
            self.tr("Zoom out"),
            EricPixmapCache.getIcon("zoomOut"),
            self.tr("Zoom &out"),
            QKeySequence(self.tr("Ctrl+-", "View|Zoom out")),
            0,
            self,
            "iconEditor_view_zoom_out",
        )
        self.zoomOutAct.setStatusTip(self.tr("Zoom out on the icon"))
        self.zoomOutAct.setWhatsThis(
            self.tr(
                """<b>Zoom out</b>"""
                """<p>Zoom out on the icon. This makes the grid smaller.</p>"""
            )
        )
        self.zoomOutAct.triggered.connect(self.__zoomOut)
        self.__actions.append(self.zoomOutAct)

        self.zoomResetAct = EricAction(
            self.tr("Zoom reset"),
            EricPixmapCache.getIcon("zoomReset"),
            self.tr("Zoom &reset"),
            QKeySequence(self.tr("Ctrl+0", "View|Zoom reset")),
            0,
            self,
            "iconEditor_view_zoom_reset",
        )
        self.zoomResetAct.setStatusTip(self.tr("Reset the zoom of the icon"))
        self.zoomResetAct.setWhatsThis(
            self.tr(
                """<b>Zoom reset</b>"""
                """<p>Reset the zoom of the icon. """
                """This sets the zoom factor to 100%.</p>"""
            )
        )
        self.zoomResetAct.triggered.connect(self.__zoomReset)
        self.__actions.append(self.zoomResetAct)

        self.showGridAct = EricAction(
            self.tr("Show Grid"),
            EricPixmapCache.getIcon("grid"),
            self.tr("Show &Grid"),
            0,
            0,
            self,
            "iconEditor_view_show_grid",
        )
        self.showGridAct.setStatusTip(self.tr("Toggle the display of the grid"))
        self.showGridAct.setWhatsThis(
            self.tr("""<b>Show Grid</b><p>Toggle the display of the grid.</p>""")
        )
        self.showGridAct.triggered[bool].connect(self.__editor.setGridEnabled)
        self.__actions.append(self.showGridAct)
        self.showGridAct.setCheckable(True)
        self.showGridAct.setChecked(self.__editor.isGridEnabled())

    def __initToolsActions(self):
        """
        Private method to create the View actions.
        """
        self.esm = QSignalMapper(self)
        self.esm.mappedInt.connect(self.__editor.setTool)

        self.drawingActGrp = createActionGroup(self)
        self.drawingActGrp.setExclusive(True)

        self.drawPencilAct = EricAction(
            self.tr("Freehand"),
            EricPixmapCache.getIcon("drawBrush"),
            self.tr("&Freehand"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_pencil",
        )
        self.drawPencilAct.setWhatsThis(
            self.tr("""<b>Free hand</b><p>Draws non linear lines.</p>""")
        )
        self.drawPencilAct.setCheckable(True)
        self.esm.setMapping(self.drawPencilAct, IconEditorTool.PENCIL)
        self.drawPencilAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawPencilAct)

        self.drawColorPickerAct = EricAction(
            self.tr("Color Picker"),
            EricPixmapCache.getIcon("colorPicker"),
            self.tr("&Color Picker"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_color_picker",
        )
        self.drawColorPickerAct.setWhatsThis(
            self.tr(
                """<b>Color Picker</b>"""
                """<p>The color of the pixel clicked on will become """
                """the current draw color.</p>"""
            )
        )
        self.drawColorPickerAct.setCheckable(True)
        self.esm.setMapping(self.drawColorPickerAct, IconEditorTool.COLOR_PICKER)
        self.drawColorPickerAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawColorPickerAct)

        self.drawRectangleAct = EricAction(
            self.tr("Rectangle"),
            EricPixmapCache.getIcon("drawRectangle"),
            self.tr("&Rectangle"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_rectangle",
        )
        self.drawRectangleAct.setWhatsThis(
            self.tr("""<b>Rectangle</b><p>Draw a rectangle.</p>""")
        )
        self.drawRectangleAct.setCheckable(True)
        self.esm.setMapping(self.drawRectangleAct, IconEditorTool.RECTANGLE)
        self.drawRectangleAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawRectangleAct)

        self.drawFilledRectangleAct = EricAction(
            self.tr("Filled Rectangle"),
            EricPixmapCache.getIcon("drawRectangleFilled"),
            self.tr("F&illed Rectangle"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_filled_rectangle",
        )
        self.drawFilledRectangleAct.setWhatsThis(
            self.tr("""<b>Filled Rectangle</b><p>Draw a filled rectangle.</p>""")
        )
        self.drawFilledRectangleAct.setCheckable(True)
        self.esm.setMapping(
            self.drawFilledRectangleAct, IconEditorTool.FILLED_RECTANGLE
        )
        self.drawFilledRectangleAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawFilledRectangleAct)

        self.drawCircleAct = EricAction(
            self.tr("Circle"),
            EricPixmapCache.getIcon("drawCircle"),
            self.tr("Circle"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_circle",
        )
        self.drawCircleAct.setWhatsThis(
            self.tr("""<b>Circle</b><p>Draw a circle.</p>""")
        )
        self.drawCircleAct.setCheckable(True)
        self.esm.setMapping(self.drawCircleAct, IconEditorTool.CIRCLE)
        self.drawCircleAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawCircleAct)

        self.drawFilledCircleAct = EricAction(
            self.tr("Filled Circle"),
            EricPixmapCache.getIcon("drawCircleFilled"),
            self.tr("Fille&d Circle"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_filled_circle",
        )
        self.drawFilledCircleAct.setWhatsThis(
            self.tr("""<b>Filled Circle</b><p>Draw a filled circle.</p>""")
        )
        self.drawFilledCircleAct.setCheckable(True)
        self.esm.setMapping(self.drawFilledCircleAct, IconEditorTool.FILLED_CIRCLE)
        self.drawFilledCircleAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawFilledCircleAct)

        self.drawEllipseAct = EricAction(
            self.tr("Ellipse"),
            EricPixmapCache.getIcon("drawEllipse"),
            self.tr("&Ellipse"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_ellipse",
        )
        self.drawEllipseAct.setWhatsThis(
            self.tr("""<b>Ellipse</b><p>Draw an ellipse.</p>""")
        )
        self.drawEllipseAct.setCheckable(True)
        self.esm.setMapping(self.drawEllipseAct, IconEditorTool.ELLIPSE)
        self.drawEllipseAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawEllipseAct)

        self.drawFilledEllipseAct = EricAction(
            self.tr("Filled Ellipse"),
            EricPixmapCache.getIcon("drawEllipseFilled"),
            self.tr("Fille&d Elli&pse"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_filled_ellipse",
        )
        self.drawFilledEllipseAct.setWhatsThis(
            self.tr("""<b>Filled Ellipse</b><p>Draw a filled ellipse.</p>""")
        )
        self.drawFilledEllipseAct.setCheckable(True)
        self.esm.setMapping(self.drawFilledEllipseAct, IconEditorTool.FILLED_ELLIPSE)
        self.drawFilledEllipseAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawFilledEllipseAct)

        self.drawFloodFillAct = EricAction(
            self.tr("Flood Fill"),
            EricPixmapCache.getIcon("drawFill"),
            self.tr("Fl&ood Fill"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_flood_fill",
        )
        self.drawFloodFillAct.setWhatsThis(
            self.tr(
                """<b>Flood Fill</b>"""
                """<p>Fill adjoining pixels with the same color with """
                """the current color.</p>"""
            )
        )
        self.drawFloodFillAct.setCheckable(True)
        self.esm.setMapping(self.drawFloodFillAct, IconEditorTool.FILL)
        self.drawFloodFillAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawFloodFillAct)

        self.drawLineAct = EricAction(
            self.tr("Line"),
            EricPixmapCache.getIcon("drawLine"),
            self.tr("&Line"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_line",
        )
        self.drawLineAct.setWhatsThis(self.tr("""<b>Line</b><p>Draw a line.</p>"""))
        self.drawLineAct.setCheckable(True)
        self.esm.setMapping(self.drawLineAct, IconEditorTool.LINE)
        self.drawLineAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawLineAct)

        self.drawEraserAct = EricAction(
            self.tr("Eraser (Transparent)"),
            EricPixmapCache.getIcon("drawEraser"),
            self.tr("Eraser (&Transparent)"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_eraser",
        )
        self.drawEraserAct.setWhatsThis(
            self.tr(
                """<b>Eraser (Transparent)</b>"""
                """<p>Erase pixels by setting them to transparent.</p>"""
            )
        )
        self.drawEraserAct.setCheckable(True)
        self.esm.setMapping(self.drawEraserAct, IconEditorTool.RUBBER)
        self.drawEraserAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawEraserAct)

        self.drawRectangleSelectionAct = EricAction(
            self.tr("Rectangular Selection"),
            EricPixmapCache.getIcon("selectRectangle"),
            self.tr("Rect&angular Selection"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_selection_rectangle",
        )
        self.drawRectangleSelectionAct.setWhatsThis(
            self.tr(
                """<b>Rectangular Selection</b>"""
                """<p>Select a rectangular section of the icon using"""
                """ the mouse.</p>"""
            )
        )
        self.drawRectangleSelectionAct.setCheckable(True)
        self.esm.setMapping(
            self.drawRectangleSelectionAct, IconEditorTool.SELECT_RECTANGLE
        )
        self.drawRectangleSelectionAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawRectangleSelectionAct)

        self.drawCircleSelectionAct = EricAction(
            self.tr("Circular Selection"),
            EricPixmapCache.getIcon("selectCircle"),
            self.tr("Rect&angular Selection"),
            0,
            0,
            self.drawingActGrp,
            "iconEditor_tools_selection_circle",
        )
        self.drawCircleSelectionAct.setWhatsThis(
            self.tr(
                """<b>Circular Selection</b>"""
                """<p>Select a circular section of the icon using"""
                """ the mouse.</p>"""
            )
        )
        self.drawCircleSelectionAct.setCheckable(True)
        self.esm.setMapping(self.drawCircleSelectionAct, IconEditorTool.SELECT_CIRCLE)
        self.drawCircleSelectionAct.triggered.connect(self.esm.map)
        self.__actions.append(self.drawCircleSelectionAct)

        self.drawPencilAct.trigger()

    def __initHelpActions(self):
        """
        Private method to create the Help actions.
        """
        self.aboutAct = EricAction(
            self.tr("About"), self.tr("&About"), 0, 0, self, "iconEditor_help_about"
        )
        self.aboutAct.setStatusTip(self.tr("Display information about this software"))
        self.aboutAct.setWhatsThis(
            self.tr(
                """<b>About</b>"""
                """<p>Display some information about this software.</p>"""
            )
        )
        self.aboutAct.triggered.connect(self.__about)
        self.__actions.append(self.aboutAct)

        self.aboutQtAct = EricAction(
            self.tr("About Qt"),
            self.tr("About &Qt"),
            0,
            0,
            self,
            "iconEditor_help_about_qt",
        )
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
        self.__actions.append(self.aboutQtAct)

        self.whatsThisAct = EricAction(
            self.tr("What's This?"),
            EricPixmapCache.getIcon("whatsThis"),
            self.tr("&What's This?"),
            QKeySequence(self.tr("Shift+F1", "Help|What's This?'")),
            0,
            self,
            "iconEditor_help_whats_this",
        )
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
        self.__actions.append(self.whatsThisAct)

    def __initMenus(self):
        """
        Private method to create the menus.
        """
        mb = self.menuBar()

        menu = mb.addMenu(self.tr("&File"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.newAct)
        menu.addAction(self.newWindowAct)
        menu.addAction(self.openAct)
        menu.addSeparator()
        menu.addAction(self.saveAct)
        menu.addAction(self.saveAsAct)
        menu.addSeparator()
        menu.addAction(self.closeAct)
        menu.addAction(self.closeOthersAct)
        if self.fromEric:
            menu.addAction(self.closeAllAct)
        else:
            menu.addSeparator()
            menu.addAction(self.exitAct)

        menu = mb.addMenu(self.tr("&Edit"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.undoAct)
        menu.addAction(self.redoAct)
        menu.addSeparator()
        menu.addAction(self.cutAct)
        menu.addAction(self.copyAct)
        menu.addAction(self.pasteAct)
        menu.addAction(self.pasteNewAct)
        menu.addAction(self.deleteAct)
        menu.addSeparator()
        menu.addAction(self.selectAllAct)
        menu.addSeparator()
        menu.addAction(self.resizeAct)
        menu.addAction(self.grayscaleAct)

        menu = mb.addMenu(self.tr("&View"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.zoomInAct)
        menu.addAction(self.zoomResetAct)
        menu.addAction(self.zoomOutAct)
        menu.addSeparator()
        menu.addAction(self.showGridAct)

        menu = mb.addMenu(self.tr("&Tools"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.drawPencilAct)
        menu.addAction(self.drawColorPickerAct)
        menu.addAction(self.drawRectangleAct)
        menu.addAction(self.drawFilledRectangleAct)
        menu.addAction(self.drawCircleAct)
        menu.addAction(self.drawFilledCircleAct)
        menu.addAction(self.drawEllipseAct)
        menu.addAction(self.drawFilledEllipseAct)
        menu.addAction(self.drawFloodFillAct)
        menu.addAction(self.drawLineAct)
        menu.addAction(self.drawEraserAct)
        menu.addSeparator()
        menu.addAction(self.drawRectangleSelectionAct)
        menu.addAction(self.drawCircleSelectionAct)

        mb.addSeparator()

        menu = mb.addMenu(self.tr("&Help"))
        menu.addAction(self.aboutAct)
        menu.addAction(self.aboutQtAct)
        menu.addSeparator()
        menu.addAction(self.whatsThisAct)

    def __initToolbars(self):
        """
        Private method to create the toolbars.
        """
        filetb = self.addToolBar(self.tr("File"))
        filetb.setObjectName("FileToolBar")
        filetb.addAction(self.newAct)
        filetb.addAction(self.newWindowAct)
        filetb.addAction(self.openAct)
        filetb.addSeparator()
        filetb.addAction(self.saveAct)
        filetb.addAction(self.saveAsAct)
        filetb.addSeparator()
        filetb.addAction(self.closeAct)
        if not self.fromEric:
            filetb.addAction(self.exitAct)

        edittb = self.addToolBar(self.tr("Edit"))
        edittb.setObjectName("EditToolBar")
        edittb.addAction(self.undoAct)
        edittb.addAction(self.redoAct)
        edittb.addSeparator()
        edittb.addAction(self.cutAct)
        edittb.addAction(self.copyAct)
        edittb.addAction(self.pasteAct)
        edittb.addSeparator()
        edittb.addAction(self.resizeAct)
        edittb.addAction(self.grayscaleAct)

        viewtb = self.addToolBar(self.tr("View"))
        viewtb.setObjectName("ViewToolBar")
        viewtb.addAction(self.showGridAct)

        toolstb = self.addToolBar(self.tr("Tools"))
        toolstb.setObjectName("ToolsToolBar")
        toolstb.addAction(self.drawPencilAct)
        toolstb.addAction(self.drawColorPickerAct)
        toolstb.addAction(self.drawRectangleAct)
        toolstb.addAction(self.drawFilledRectangleAct)
        toolstb.addAction(self.drawCircleAct)
        toolstb.addAction(self.drawFilledCircleAct)
        toolstb.addAction(self.drawEllipseAct)
        toolstb.addAction(self.drawFilledEllipseAct)
        toolstb.addAction(self.drawFloodFillAct)
        toolstb.addAction(self.drawLineAct)
        toolstb.addAction(self.drawEraserAct)
        toolstb.addSeparator()
        toolstb.addAction(self.drawRectangleSelectionAct)
        toolstb.addAction(self.drawCircleSelectionAct)

        helptb = self.addToolBar(self.tr("Help"))
        helptb.setObjectName("HelpToolBar")
        helptb.addAction(self.whatsThisAct)

    def __createStatusBar(self):
        """
        Private method to initialize the status bar.
        """
        self.__statusBar = self.statusBar()
        self.__statusBar.setSizeGripEnabled(True)

        self.__sbSize = QLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.__sbSize)
        self.__sbSize.setWhatsThis(
            self.tr("""<p>This part of the status bar displays the icon size.</p>""")
        )
        self.__updateSize(*self.__editor.iconSize())

        self.__sbPos = QLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.__sbPos)
        self.__sbPos.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays the cursor"""
                """ position.</p>"""
            )
        )
        self.__updatePosition(0, 0)

        self.__zoomWidget = EricZoomWidget(
            EricPixmapCache.getPixmap("zoomOut"),
            EricPixmapCache.getPixmap("zoomIn"),
            EricPixmapCache.getPixmap("zoomReset"),
            self,
        )
        self.__zoomWidget.setMinimum(IconEditorGrid.ZoomMinimum)
        self.__zoomWidget.setMaximum(IconEditorGrid.ZoomMaximum)
        self.__zoomWidget.setDefault(IconEditorGrid.ZoomDefault)
        self.__zoomWidget.setSingleStep(IconEditorGrid.ZoomStep)
        self.__zoomWidget.setPercent(IconEditorGrid.ZoomPercent)
        self.__statusBar.addPermanentWidget(self.__zoomWidget)
        self.__zoomWidget.setValue(self.__editor.zoomFactor())
        self.__zoomWidget.valueChanged.connect(self.__editor.setZoomFactor)
        self.__editor.zoomChanged.connect(self.__zoomWidget.setValue)

        self.__updateZoom()

    def __createPaletteDock(self):
        """
        Private method to initialize the palette dock widget.
        """
        from .IconEditorPalette import IconEditorPalette

        self.__paletteDock = QDockWidget(self)
        self.__paletteDock.setObjectName("paletteDock")
        self.__paletteDock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.__paletteDock.setWindowTitle("Palette")
        self.__palette = IconEditorPalette()
        self.__paletteDock.setWidget(self.__palette)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.__paletteDock)

    def closeEvent(self, evt):
        """
        Protected event handler for the close event.

        @param evt the close event
        @type QCloseEvent
            <br />This event is simply accepted after the history has been
            saved and all window references have been deleted.
        """
        if self.__maybeSave():
            self.__editor.shutdown()

            state = self.saveState()
            Preferences.setIconEditor("IconEditorState", state)

            Preferences.setGeometry("IconEditorGeometry", self.saveGeometry())

            with contextlib.suppress(ValueError):
                if self.fromEric or len(self.__class__.windows) > 1:
                    del self.__class__.windows[self.__class__.windows.index(self)]

            if not self.fromEric:
                Preferences.syncPreferences()

            evt.accept()
            self.editorClosed.emit()
        else:
            evt.ignore()

    def __newIcon(self):
        """
        Private slot to create a new icon.
        """
        if self.__maybeSave():
            self.__editor.editNew()
            self.__setCurrentFile("")

        self.__checkActions()

    def __newWindow(self):
        """
        Private slot called to open a new icon editor window.
        """
        ie = IconEditorWindow(
            parent=self.parent(), fromEric=self.fromEric, project=self.__project
        )
        ie.setRecentPaths(self.__lastOpenPath, self.__lastSavePath)
        ie.show()

    def __openIcon(self):
        """
        Private slot to open an icon file.
        """
        if self.__maybeSave():
            if (
                not self.__lastOpenPath
                and self.__project is not None
                and self.__project.isOpen()
            ):
                self.__lastOpenPath = self.__project.getProjectPath()

            fileName = EricFileDialog.getOpenFileNameAndFilter(
                self,
                self.tr("Open icon file"),
                self.__lastOpenPath,
                self.__inputFilter,
                self.__defaultFilter,
            )[0]
            if fileName:
                self.__loadIconFile(fileName)
                self.__lastOpenPath = os.path.dirname(fileName)
        self.__checkActions()

    def __saveIcon(self):
        """
        Private slot to save the icon.

        @return flag indicating success
        @rtype bool
        """
        if not self.__fileName:
            return self.__saveIconAs()
        else:
            return self.__saveIconFile(self.__fileName)

    def __saveIconAs(self):
        """
        Private slot to save the icon with a new name.

        @return flag indicating success
        @rtype bool
        """
        if (
            not self.__lastSavePath
            and self.__project is not None
            and self.__project.isOpen()
        ):
            self.__lastSavePath = self.__project.getProjectPath()
        if not self.__lastSavePath and self.__lastOpenPath:
            self.__lastSavePath = self.__lastOpenPath

        fileName, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.tr("Save icon file"),
            self.__lastSavePath,
            self.__outputFilter,
            self.__defaultFilter,
            EricFileDialog.DontConfirmOverwrite,
        )
        if not fileName:
            return False

        fpath = pathlib.Path(fileName)
        if not fpath.suffix:
            ex = selectedFilter.split("(*")[1].split(")")[0]
            if ex:
                fpath = fpath.with_suffix(ex)
        if fpath.exists():
            res = EricMessageBox.yesNo(
                self,
                self.tr("Save icon file"),
                self.tr(
                    "<p>The file <b>{0}</b> already exists. Overwrite it?</p>"
                ).format(fpath),
                icon=EricMessageBox.Warning,
            )
            if not res:
                return False

        self.__lastSavePath = str(fpath.parent)

        return self.__saveIconFile(str(fpath))

    def __closeAll(self):
        """
        Private slot to close all windows.
        """
        self.__closeOthers()
        self.close()

    def __closeOthers(self):
        """
        Private slot to close all other windows.
        """
        for win in self.__class__.windows[:]:
            if win != self:
                win.close()

    def __loadIconFile(self, fileName):
        """
        Private method to load an icon file.

        @param fileName name of the icon file to load
        @type str
        """
        img = QImage()
        if self.fromEric and FileSystemUtilities.isRemoteFileName(fileName):
            try:
                data = (
                    ericApp()
                    .getObject("EricServer")
                    .getServiceInterface("FileSystem")
                    .readFile(fileName)
                )
                img.loadFromData(data)
            except OSError as err:
                EricMessageBox.warning(
                    self,
                    self.tr("eric Icon Editor"),
                    self.tr(
                        """<p>The file <b>{0}</b> cannot be loaded.</p>"""
                        """<p>Reason: {1}</p>"""
                    ).format(fileName, str(err)),
                )
                return
        else:
            img.load(fileName)
        if img.isNull():
            EricMessageBox.warning(
                self,
                self.tr("eric Icon Editor"),
                self.tr("Cannot read file '{0}'.").format(fileName),
            )
        else:
            self.__editor.setIconImage(img, clearUndo=True)
            self.__setCurrentFile(fileName)

    def __saveIconFile(self, fileName):
        """
        Private method to save to the given file.

        @param fileName name of the file to save to
        @type str
        @return flag indicating success
        @rtype bool
        """
        img = self.__editor.iconImage()
        if self.fromEric and FileSystemUtilities.isRemoteFileName(fileName):
            fsInterface = (
                ericApp().getObject("EricServer").getServiceInterface("FileSystem")
            )
            imageFormat = fsInterface.splitext(fileName)[1][1:].upper()
            data = QByteArray()
            buffer = QBuffer(data)
            res = img.save(buffer, imageFormat)
            if res:
                try:
                    fsInterface.writeFile(fileName, data)
                except OSError as err:
                    EricMessageBox.warning(
                        self,
                        self.tr("eric Icon Editor"),
                        self.tr(
                            """<p>The file <b>{0}</b> cannot be written.</p>"""
                            """<p>Reason: {1}</p>"""
                        ).format(fileName, str(err)),
                    )
                    self.__checkActions()
                    return False
        else:
            res = img.save(fileName)

        if not res:
            EricMessageBox.warning(
                self,
                self.tr("eric Icon Editor"),
                self.tr("Cannot write file '{0}'.").format(fileName),
            )
            self.__checkActions()
            return False

        self.__editor.setDirty(False, setCleanState=True)

        self.__setCurrentFile(fileName)
        self.__statusBar.showMessage(self.tr("Icon saved"), 2000)

        self.__checkActions()

        return True

    def __setCurrentFile(self, fileName):
        """
        Private method to register the file name of the current file.

        @param fileName name of the file to register
        @type str
        """
        self.__fileName = fileName

        shownName = (
            self.__strippedName(self.__fileName)
            if self.__fileName
            else self.tr("Untitled")
        )

        self.setWindowTitle(
            self.tr("{0}[*] - {1}").format(shownName, self.tr("Icon Editor"))
        )

        self.setWindowModified(self.__editor.isDirty())

    def __strippedName(self, fullFileName):
        """
        Private method to return the filename part of the given path.

        @param fullFileName full pathname of the given file
        @type str
        @return filename part
        @rtype str
        """
        return pathlib.Path(fullFileName).name

    def __maybeSave(self):
        """
        Private method to ask the user to save the file, if it was modified.

        @return flag indicating, if it is ok to continue
        @rtype bool
        """
        if self.__editor.isDirty():
            ret = EricMessageBox.okToClearData(
                self,
                self.tr("eric Icon Editor"),
                self.tr("""The icon image has unsaved changes."""),
                self.__saveIcon,
            )
            if not ret:
                return False
        return True

    def setRecentPaths(self, openPath, savePath):
        """
        Public method to set the last open and save paths.

        @param openPath least recently used open path
        @type str
        @param savePath least recently used save path
        @type str
        """
        if openPath:
            self.__lastOpenPath = openPath
        if savePath:
            self.__lastSavePath = savePath

    def __checkActions(self):
        """
        Private slot to check some actions for their enable/disable status.
        """
        self.saveAct.setEnabled(self.__editor.isDirty())

    def __modificationChanged(self, m):
        """
        Private slot to handle the modificationChanged signal.

        @param m modification status
        @type bool
        """
        self.setWindowModified(m)
        self.__checkActions()

    def __updatePosition(self, x, y):
        """
        Private slot to show the current cursor position.

        @param x x-coordinate
        @type int
        @param y y-coordinate
        @type int
        """
        self.__sbPos.setText("X: {0:d} Y: {1:d}".format(x + 1, y + 1))

    def __updateSize(self, w, h):
        """
        Private slot to show the current icon size.

        @param w width of the icon
        @type int
        @param h height of the icon
        @type int
        """
        self.__sbSize.setText("Size: {0:d} x {1:d}".format(w, h))

    def __updateZoom(self):
        """
        Private slot to show the current zoom factor.
        """
        self.zoomOutAct.setEnabled(
            self.__editor.zoomFactor() > IconEditorGrid.ZoomMinimum
        )
        self.zoomInAct.setEnabled(
            self.__editor.zoomFactor() < IconEditorGrid.ZoomMaximum
        )

    def __zoomIn(self):
        """
        Private slot called to handle the zoom in action.
        """
        self.__editor.setZoomFactor(
            self.__editor.zoomFactor() + IconEditorGrid.ZoomStep
        )
        self.__updateZoom()

    def __zoomOut(self):
        """
        Private slot called to handle the zoom out action.
        """
        self.__editor.setZoomFactor(
            self.__editor.zoomFactor() - IconEditorGrid.ZoomStep
        )
        self.__updateZoom()

    def __zoomReset(self):
        """
        Private slot called to handle the zoom reset action.
        """
        self.__editor.setZoomFactor(IconEditorGrid.ZoomDefault)
        self.__updateZoom()

    def __about(self):
        """
        Private slot to show a little About message.
        """
        EricMessageBox.about(
            self,
            self.tr("About eric Icon Editor"),
            self.tr(
                "The eric Icon Editor is a simple editor component"
                " to perform icon drawing tasks."
            ),
        )

    def __aboutQt(self):
        """
        Private slot to handle the About Qt dialog.
        """
        EricMessageBox.aboutQt(self, "eric Icon Editor")

    def __whatsThis(self):
        """
        Private slot called in to enter Whats This mode.
        """
        QWhatsThis.enterWhatsThisMode()

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
                pinch.setTotalScaleFactor(self.__editor.zoomFactor() / 100.0)
            elif pinch.state() == Qt.GestureState.GestureUpdated:
                self.__editor.setZoomFactor(int(pinch.totalScaleFactor() * 100))
                self.__updateZoom()
            evt.accept()
