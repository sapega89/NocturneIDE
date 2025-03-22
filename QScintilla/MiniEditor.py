# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an editor for simple editing tasks.
"""

import contextlib
import os
import pathlib
import re

import editorconfig

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtCore import (
    QCoreApplication,
    QPoint,
    QSignalMapper,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QAction, QActionGroup, QFont, QKeySequence, QPalette, QPixmap
from PyQt6.QtPrintSupport import (
    QAbstractPrintDialog,
    QPrintDialog,
    QPrinter,
    QPrintPreviewDialog,
)
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QSplitter,
    QVBoxLayout,
    QWhatsThis,
    QWidget,
)

from eric7 import EricUtilities, Preferences, Utilities
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction, createActionGroup
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricClickableLabel import EricClickableLabel
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.EricWidgets.EricZoomWidget import EricZoomWidget
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities

from . import Lexers
from .EditorOutline import EditorOutlineView
from .QsciScintillaCompat import QsciScintillaCompat
from .SearchReplaceWidget import SearchReplaceWidget


class MiniScintilla(QsciScintillaCompat):
    """
    Class implementing a QsciScintillaCompat subclass for handling focus
    events.
    """

    EncloseChars = {
        '"': '"',
        "'": "'",
        "(": "()",
        ")": "()",
        "{": "{}",  # __IGNORE_WARNING_M613__
        "}": "{}",  # __IGNORE_WARNING_M613__
        "[": "[]",
        "]": "[]",
        "<": "<>",
        ">": "<>",
    }

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.enableMultiCursorSupport()

        self.mw = parent

    def getFileName(self):
        """
        Public method to return the name of the file being displayed.

        @return filename of the displayed file
        @rtype str
        """
        return self.mw.getFileName()

    def editorCommand(self, cmd):
        """
        Public method to perform a simple editor command.

        @param cmd the scintilla command to be performed
        @type int
        """
        if cmd == QsciScintilla.SCI_DELETEBACK:
            line, index = self.getCursorPosition()
            text = self.text(line)[index - 1 : index + 1]
            matchingPairs = ["()", "[]", "{}", "<>", "''", '""']
            # __IGNORE_WARNING_M613__
            if text in matchingPairs:
                self.delete()

        elif (
            cmd in (QsciScintilla.SCI_LOWERCASE, QsciScintilla.SCI_UPPERCASE)
            and self.hasSelectedText()
        ):
            startLine, startIndex, endLine, endIndex = self.getSelection()
            selectedText = self.selectedText()
            replacementText = (
                selectedText.upper()
                if cmd == QsciScintilla.SCI_UPPERCASE
                else selectedText.lower()
            )
            self.replaceSelectedText(replacementText)
            self.setSelection(startLine, startIndex, endLine, endIndex)
            return

        super().editorCommand(cmd)

    def keyPressEvent(self, ev):
        """
        Protected method to handle the user input a key at a time.

        @param ev key event
        @type QKeyEvent
        """

        def encloseSelectedText(encString):
            """
            Local function to enclose the current selection with some
            characters.

            @param encString string to use to enclose the selection
                (one or two characters)
            @type str
            """
            startChar = encString[0]
            endChar = encString[1] if len(encString) == 2 else startChar

            sline, sindex, eline, eindex = self.getSelection()
            replaceText = startChar + self.selectedText() + endChar
            self.beginUndoAction()
            self.replaceSelectedText(replaceText)
            self.endUndoAction()
            self.setSelection(sline, sindex + 1, eline, eindex + 1)

        txt = ev.text()

        # See it is text to insert.
        if len(txt) and txt >= " ":
            if self.hasSelectedText() and txt in MiniScintilla.EncloseChars:
                encloseSelectedText(MiniScintilla.EncloseChars[txt])
                ev.accept()
                return

            super().keyPressEvent(ev)
        else:
            ev.ignore()

    def mousePressEvent(self, event):
        """
        Protected method to handle the mouse press event.

        @param event the mouse press event
        @type QMouseEvent
        """
        if event.button() == Qt.MouseButton.XButton1:
            self.undo()
            event.accept()
        elif event.button() == Qt.MouseButton.XButton2:
            self.redo()
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton and bool(
            event.modifiers()
            & (Qt.KeyboardModifier.MetaModifier | Qt.KeyboardModifier.AltModifier)
        ):
            line, index = self.lineIndexFromPoint(event.position().toPoint())
            self.addCursor(line, index)
            event.accept()
        else:
            super().mousePressEvent(event)

    def focusInEvent(self, event):
        """
        Protected method called when the editor receives focus.

        This method checks for modifications of the current file and
        rereads it upon request. The cursor is placed at the current position
        assuming, that it is in the vicinity of the old position after the
        reread.

        @param event the event object
        @type QFocusEvent
        """
        self.mw.editorActGrp.setEnabled(True)
        with contextlib.suppress(AttributeError):
            self.setCaretWidth(self.mw.caretWidth)

        self.setCursorFlashTime(QApplication.cursorFlashTime())

        super().focusInEvent(event)

    def focusOutEvent(self, event):
        """
        Protected method called when the editor loses focus.

        @param event the event object
        @type QFocusEvent
        """
        self.mw.editorActGrp.setEnabled(False)
        self.setCaretWidth(0)

        super().focusOutEvent(event)

    def removeTrailingWhitespace(self):
        """
        Public method to remove trailing whitespace.
        """
        searchRE = r"[ \t]+$"  # whitespace at the end of a line

        ok = self.findFirstTarget(searchRE, True, False, False, 0, 0)
        self.beginUndoAction()
        while ok:
            self.replaceTarget("")
            ok = self.findNextTarget()
        self.endUndoAction()


class MiniEditor(EricMainWindow):
    """
    Class implementing an editor for simple editing tasks.

    @signal editorSaved() emitted after the file has been saved
    @signal languageChanged(str) emitted when the editors language was set. The
        language is passed as a parameter.
    @signal editorRenamed(str) emitted after the editor got a new name
        (i.e. after a 'Save As')
    @signal cursorLineChanged(int) emitted when the cursor line was changed
    @signal closing() emitted when the editor is closed

    @signal refreshed() dummy signal to emulate the Editor interface
    """

    editorSaved = pyqtSignal()
    languageChanged = pyqtSignal(str)
    editorRenamed = pyqtSignal(str)
    cursorLineChanged = pyqtSignal(int)
    closing = pyqtSignal()

    refreshed = pyqtSignal()

    def __init__(self, filename="", filetype="", parent=None, name=None):
        """
        Constructor

        @param filename name of the file to open
        @type str
        @param filetype type of the source file
        @type str
        @param parent reference to the parent widget
        @type QWidget
        @param name object name of the window
        @type str
        """
        super().__init__(parent)
        if name is not None:
            self.setObjectName(name)
        self.setWindowIcon(EricPixmapCache.getIcon("editor"))

        self.setStyle(
            styleName=Preferences.getUI("Style"),
            styleSheetFile=Preferences.getUI("StyleSheet"),
            itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
        )

        self.__textEdit = MiniScintilla(self)
        self.__textEdit.clearSearchIndicators = self.clearSearchIndicators
        self.__textEdit.setSearchIndicator = self.setSearchIndicator
        self.__textEdit.highlightSearchSelection = self.highlightSearchSelection
        self.__textEdit.getSearchSelectionHighlight = self.getSearchSelectionHighlight
        self.__textEdit.clearSearchSelectionHighlight = (
            self.clearSearchSelectionHighlight
        )
        self.__textEdit.setUtf8(True)

        self.getCursorPosition = self.__textEdit.getCursorPosition
        self.text = self.__textEdit.text
        self.getZoom = self.__textEdit.getZoom
        self.zoomTo = self.__textEdit.zoomTo
        self.zoomIn = self.__textEdit.zoomIn
        self.zoomOut = self.__textEdit.zoomOut

        self.__curFile = filename
        self.__lastLine = 0

        self.srHistory = {"search": [], "replace": []}
        self.__searchReplaceWidget = SearchReplaceWidget(self, self)

        self.__sourceOutline = EditorOutlineView(self, populate=False)

        self.__splitter = QSplitter(Qt.Orientation.Horizontal)
        self.__splitter.setChildrenCollapsible(False)
        self.__splitter.addWidget(self.__textEdit)
        self.__splitter.addWidget(self.__sourceOutline)

        centralWidget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addWidget(self.__splitter)
        layout.addWidget(self.__searchReplaceWidget)
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)
        self.__searchReplaceWidget.hide()

        self.lexer_ = None
        self.apiLanguage = ""
        self.filetype = ""

        self.__loadEditorConfig(filename)

        self.__createActions()
        self.__createMenus()
        self.__createToolBars()
        self.__createStatusBar()

        self.__loadConfiguration()
        self.__readSettings()

        # clear QScintilla defined keyboard commands
        # we do our own handling through the view manager
        self.__textEdit.clearAlternateKeys()
        self.__textEdit.clearKeys()

        # initialise the mark occurrences timer
        self.__markOccurrencesTimer = QTimer(self)
        self.__markOccurrencesTimer.setSingleShot(True)
        self.__markOccurrencesTimer.setInterval(
            Preferences.getEditor("MarkOccurrencesTimeout")
        )
        self.__markOccurrencesTimer.timeout.connect(self.__markOccurrences)
        self.__markedText = ""

        self.__changeTimer = QTimer(self)
        self.__changeTimer.setSingleShot(True)
        self.__changeTimer.setInterval(5 * 1000)
        self.__textEdit.textChanged.connect(self.__resetChangeTimer)

        self.__textEdit.textChanged.connect(self.__documentWasModified)
        self.__textEdit.modificationChanged.connect(self.__modificationChanged)
        self.__textEdit.cursorPositionChanged.connect(self.__cursorPositionChanged)
        self.__textEdit.linesChanged.connect(self.__resizeLinenoMargin)

        self.__textEdit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.__textEdit.customContextMenuRequested.connect(self.__contextMenuRequested)

        self.__textEdit.selectionChanged.connect(
            lambda: self.__searchReplaceWidget.selectionChanged(self.__textEdit)
        )
        self.__textEdit.zoomValueChanged.connect(self.sbZoom.setValue)

        if filename:
            if FileSystemUtilities.isPlainFileName(filename):
                self.__loadFile(filename, filetype)
            else:
                self.__setCurrentFile(filename)
        else:
            self.__setCurrentFile("")
            self.encoding = self.__getEditorConfig("DefaultEncoding")

        self.__checkActions()

        self.__sourceOutline.setActive(True)
        self.__sourceOutline.setVisible(
            self.__sourceOutline.isSupportedLanguage(self.getLanguage())
        )
        self.__changeTimer.timeout.connect(self.__sourceOutline.repopulate)
        self.languageChanged.connect(self.__editorChanged)
        self.editorRenamed.connect(self.__editorChanged)

        self.__setupCompleted = False

    def show(self):
        """
        Public method to show the editor window and complete the initial setup.
        """
        super().show()

        if not self.__setupCompleted:
            splitterWidth = self.__splitter.width() - self.__splitter.handleWidth()
            outlineWidth = Preferences.getEditor("SourceOutlineWidth")
            self.__splitter.setSizes([splitterWidth - outlineWidth, outlineWidth])
            self.__setupCompleted = True

    def closeEvent(self, event):
        """
        Protected method to handle the close event.

        @param event close event
        @type QCloseEvent
        """
        if self.__maybeSave():
            self.__writeSettings()
            event.accept()
            self.closing.emit()
        else:
            event.ignore()

    def __newFile(self):
        """
        Private slot to create a new file.
        """
        if self.__maybeSave():
            self.__textEdit.clear()
            self.__setCurrentFile("")

        self.__checkActions()

    def __open(self):
        """
        Private slot to open a file.
        """
        if self.__maybeSave():
            fileName = EricFileDialog.getOpenFileName(self)
            if fileName:
                self.__loadFile(fileName)
        self.__checkActions()

    def __save(self):
        """
        Private slot to save a file.

        @return flag indicating success
        @rtype bool
        """
        if not self.__curFile:
            return self.__saveAs()
        else:
            if FileSystemUtilities.isDeviceFileName(self.__curFile):
                return self.__saveDeviceFile(saveas=False)
            else:
                return self.__saveFile(self.__curFile)

    def __saveAs(self):
        """
        Private slot to save a file with a new name.

        @return flag indicating success
        @rtype bool
        """
        if self.__curFile and FileSystemUtilities.isDeviceFileName(self.__curFile):
            return self.__saveDeviceFile(saveas=True)
        else:
            fileName = EricFileDialog.getSaveFileName(self)
            if not fileName:
                return False

            result = self.__saveFile(fileName)

            self.editorRenamed.emit(fileName)

            return result

    def __saveCopy(self):
        """
        Private slot to save a copy of the file with a new name.
        """
        fileName = EricFileDialog.getSaveFileName(self)
        if not fileName:
            return

        self.__writeFile(fileName)

    def __about(self):
        """
        Private slot to show a little About message.
        """
        EricMessageBox.about(
            self,
            self.tr("About eric Mini Editor"),
            self.tr(
                "The eric Mini Editor is an editor component"
                " based on QScintilla. It may be used for simple"
                " editing tasks, that don't need the power of"
                " a full blown editor."
            ),
        )

    def __aboutQt(self):
        """
        Private slot to handle the About Qt dialog.
        """
        EricMessageBox.aboutQt(self, "eric Mini Editor")

    def __whatsThis(self):
        """
        Private slot called in to enter Whats This mode.
        """
        QWhatsThis.enterWhatsThisMode()

    def __documentWasModified(self):
        """
        Private slot to handle a change in the documents modification status.
        """
        self.setWindowModified(self.__textEdit.isModified())

    def __checkActions(self, setSb=True):
        """
        Private slot to check some actions for their enable/disable status
        and set the statusbar info.

        @param setSb flag indicating an update of the status bar is wanted
        @type bool
        """
        self.saveAct.setEnabled(self.__textEdit.isModified())

        self.undoAct.setEnabled(self.__textEdit.isUndoAvailable())
        self.redoAct.setEnabled(self.__textEdit.isRedoAvailable())

        if setSb:
            line, pos = self.getCursorPosition()
            lang = self.getLanguage()
            self.__setSbFile(line + 1, pos, lang)

    def __setSbFile(self, line=None, pos=None, language=None, zoom=None):
        """
        Private method to set the file info in the status bar.

        @param line line number to display
        @type int
        @param pos character position to display
        @type int
        @param language language to display
        @type str
        @param zoom zoom value
        @type int
        """
        if not self.__curFile:
            writ = "   "
        else:
            if os.access(self.__curFile, os.W_OK):
                writ = " rw"
            else:
                writ = " ro"

        self.sbWritable.setText(writ)

        if line is None:
            line = ""
        self.sbLine.setText(self.tr("Line: {0:5}").format(line))

        if pos is None:
            pos = ""
        self.sbPos.setText(self.tr("Pos: {0:5}").format(pos))

        if language is None:
            pixmap = QPixmap()
        elif language == "":
            pixmap = EricPixmapCache.getPixmap("fileText")
        else:
            pixmap = Lexers.getLanguageIcon(language, True)
        self.sbLanguage.setPixmap(pixmap)
        if pixmap.isNull():
            self.sbLanguage.setText(language)
            self.sbLanguage.setToolTip("")
        else:
            self.sbLanguage.setText("")
            self.sbLanguage.setToolTip(self.tr("Language: {0}").format(language))

        if zoom is None:
            self.sbZoom.setValue(self.getZoom())
        else:
            self.sbZoom.setValue(zoom)

    def __readShortcut(self, act, category):
        """
        Private function to read a single keyboard shortcut from the settings.

        @param act reference to the action object
        @type EricAction
        @param category category the action belongs to
        @type str
        """
        if act.objectName():
            accel = Preferences.getSettings().value(
                "Shortcuts/{0}/{1}/Accel".format(category, act.objectName())
            )
            if accel is not None:
                act.setShortcut(QKeySequence(accel))
            accel = Preferences.getSettings().value(
                "Shortcuts/{0}/{1}/AltAccel".format(category, act.objectName())
            )
            if accel is not None:
                act.setAlternateShortcut(QKeySequence(accel), removeEmpty=True)

    def __createActions(self):
        """
        Private method to create the actions.
        """
        self.fileActions = []
        self.editActions = []
        self.helpActions = []
        self.searchActions = []
        self.viewActions = []
        self.configActions = []

        self.__createFileActions()
        self.__createEditActions()
        self.__createHelpActions()
        self.__createSearchActions()
        self.__createViewActions()
        self.__createConfigActions()

        # read the keyboard shortcuts and make them identical to the main
        # eric shortcuts
        for act in self.helpActions + self.configActions:
            self.__readShortcut(act, "General")
        for act in self.editActions:
            self.__readShortcut(act, "Edit")
        for act in self.fileActions:
            self.__readShortcut(act, "File")
        for act in self.searchActions:
            self.__readShortcut(act, "Search")
        for act in self.viewActions:
            self.__readShortcut(act, "View")

    def __createFileActions(self):
        """
        Private method to create the File actions.
        """
        self.newAct = EricAction(
            self.tr("New"),
            EricPixmapCache.getIcon("new"),
            self.tr("&New"),
            QKeySequence(self.tr("Ctrl+N", "File|New")),
            0,
            self,
            "vm_file_new",
        )
        self.newAct.setStatusTip(self.tr("Open an empty editor window"))
        self.newAct.setWhatsThis(
            self.tr("""<b>New</b><p>An empty editor window will be created.</p>""")
        )
        self.newAct.triggered.connect(self.__newFile)
        self.fileActions.append(self.newAct)

        self.openAct = EricAction(
            self.tr("Open"),
            EricPixmapCache.getIcon("documentOpen"),
            self.tr("&Open..."),
            QKeySequence(self.tr("Ctrl+O", "File|Open")),
            0,
            self,
            "vm_file_open",
        )
        self.openAct.setStatusTip(self.tr("Open a file"))
        self.openAct.setWhatsThis(
            self.tr(
                """<b>Open a file</b>"""
                """<p>You will be asked for the name of a file to be opened.</p>"""
            )
        )
        self.openAct.triggered.connect(self.__open)
        self.fileActions.append(self.openAct)

        self.saveAct = EricAction(
            self.tr("Save"),
            EricPixmapCache.getIcon("fileSave"),
            self.tr("&Save"),
            QKeySequence(self.tr("Ctrl+S", "File|Save")),
            0,
            self,
            "vm_file_save",
        )
        self.saveAct.setStatusTip(self.tr("Save the current file"))
        self.saveAct.setWhatsThis(
            self.tr(
                """<b>Save File</b>"""
                """<p>Save the contents of current editor window.</p>"""
            )
        )
        self.saveAct.triggered.connect(self.__save)
        self.fileActions.append(self.saveAct)

        self.saveAsAct = EricAction(
            self.tr("Save as"),
            EricPixmapCache.getIcon("fileSaveAs"),
            self.tr("Save &as..."),
            QKeySequence(self.tr("Shift+Ctrl+S", "File|Save As")),
            0,
            self,
            "vm_file_save_as",
        )
        self.saveAsAct.setStatusTip(self.tr("Save the current file to a new one"))
        self.saveAsAct.setWhatsThis(
            self.tr(
                """<b>Save File as</b>"""
                """<p>Save the contents of current editor window to a new file."""
                """ The file can be entered in a file selection dialog.</p>"""
            )
        )
        self.saveAsAct.triggered.connect(self.__saveAs)
        self.fileActions.append(self.saveAsAct)

        self.saveCopyAct = EricAction(
            self.tr("Save Copy"),
            EricPixmapCache.getIcon("fileSaveCopy"),
            self.tr("Save &Copy..."),
            0,
            0,
            self,
            "vm_file_save_copy",
        )
        self.saveCopyAct.setStatusTip(self.tr("Save a copy of the current file"))
        self.saveCopyAct.setWhatsThis(
            self.tr(
                """<b>Save Copy</b>"""
                """<p>Save a copy of the contents of current editor window."""
                """ The file can be entered in a file selection dialog.</p>"""
            )
        )
        self.saveCopyAct.triggered.connect(self.__saveCopy)
        self.fileActions.append(self.saveCopyAct)

        self.closeAct = EricAction(
            self.tr("Close"),
            EricPixmapCache.getIcon("close"),
            self.tr("&Close"),
            QKeySequence(self.tr("Ctrl+W", "File|Close")),
            0,
            self,
            "vm_file_close",
        )
        self.closeAct.setStatusTip(self.tr("Close the editor window"))
        self.closeAct.setWhatsThis(
            self.tr("""<b>Close Window</b><p>Close the current window.</p>""")
        )
        self.closeAct.triggered.connect(self.close)
        self.fileActions.append(self.closeAct)

        self.printAct = EricAction(
            self.tr("Print"),
            EricPixmapCache.getIcon("print"),
            self.tr("&Print"),
            QKeySequence(self.tr("Ctrl+P", "File|Print")),
            0,
            self,
            "vm_file_print",
        )
        self.printAct.setStatusTip(self.tr("Print the current file"))
        self.printAct.setWhatsThis(
            self.tr(
                """<b>Print File</b>"""
                """<p>Print the contents of the current file.</p>"""
            )
        )
        self.printAct.triggered.connect(self.__printFile)
        self.fileActions.append(self.printAct)

        self.printPreviewAct = EricAction(
            self.tr("Print Preview"),
            EricPixmapCache.getIcon("printPreview"),
            QCoreApplication.translate("ViewManager", "Print Preview"),
            0,
            0,
            self,
            "vm_file_print_preview",
        )
        self.printPreviewAct.setStatusTip(self.tr("Print preview of the current file"))
        self.printPreviewAct.setWhatsThis(
            self.tr(
                """<b>Print Preview</b>"""
                """<p>Print preview of the current file.</p>"""
            )
        )
        self.printPreviewAct.triggered.connect(self.__printPreviewFile)
        self.fileActions.append(self.printPreviewAct)

    def __createEditActions(self):
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
            "vm_edit_undo",
        )
        self.undoAct.setStatusTip(self.tr("Undo the last change"))
        self.undoAct.setWhatsThis(
            self.tr(
                """<b>Undo</b>"""
                """<p>Undo the last change done in the current editor.</p>"""
            )
        )
        self.undoAct.triggered.connect(self.__undo)
        self.editActions.append(self.undoAct)

        self.redoAct = EricAction(
            self.tr("Redo"),
            EricPixmapCache.getIcon("editRedo"),
            self.tr("&Redo"),
            QKeySequence(self.tr("Ctrl+Shift+Z", "Edit|Redo")),
            0,
            self,
            "vm_edit_redo",
        )
        self.redoAct.setStatusTip(self.tr("Redo the last change"))
        self.redoAct.setWhatsThis(
            self.tr(
                """<b>Redo</b>"""
                """<p>Redo the last change done in the current editor.</p>"""
            )
        )
        self.redoAct.triggered.connect(self.__redo)
        self.editActions.append(self.redoAct)

        self.cutAct = EricAction(
            self.tr("Cut"),
            EricPixmapCache.getIcon("editCut"),
            self.tr("Cu&t"),
            QKeySequence(self.tr("Ctrl+X", "Edit|Cut")),
            QKeySequence(self.tr("Shift+Del", "Edit|Cut")),
            self,
            "vm_edit_cut",
        )
        self.cutAct.setStatusTip(self.tr("Cut the selection"))
        self.cutAct.setWhatsThis(
            self.tr(
                """<b>Cut</b>"""
                """<p>Cut the selected text of the current editor to the"""
                """ clipboard.</p>"""
            )
        )
        self.cutAct.triggered.connect(self.__textEdit.cut)
        self.editActions.append(self.cutAct)

        self.copyAct = EricAction(
            self.tr("Copy"),
            EricPixmapCache.getIcon("editCopy"),
            self.tr("&Copy"),
            QKeySequence(self.tr("Ctrl+C", "Edit|Copy")),
            QKeySequence(self.tr("Ctrl+Ins", "Edit|Copy")),
            self,
            "vm_edit_copy",
        )
        self.copyAct.setStatusTip(self.tr("Copy the selection"))
        self.copyAct.setWhatsThis(
            self.tr(
                """<b>Copy</b>"""
                """<p>Copy the selected text of the current editor to the"""
                """ clipboard.</p>"""
            )
        )
        self.copyAct.triggered.connect(self.__textEdit.copy)
        self.editActions.append(self.copyAct)

        self.pasteAct = EricAction(
            self.tr("Paste"),
            EricPixmapCache.getIcon("editPaste"),
            self.tr("&Paste"),
            QKeySequence(self.tr("Ctrl+V", "Edit|Paste")),
            QKeySequence(self.tr("Shift+Ins", "Edit|Paste")),
            self,
            "vm_edit_paste",
        )
        self.pasteAct.setStatusTip(self.tr("Paste the last cut/copied text"))
        self.pasteAct.setWhatsThis(
            self.tr(
                """<b>Paste</b>"""
                """<p>Paste the last cut/copied text from the clipboard to"""
                """ the current editor.</p>"""
            )
        )
        self.pasteAct.triggered.connect(self.__textEdit.paste)
        self.editActions.append(self.pasteAct)

        self.deleteAct = EricAction(
            self.tr("Clear"),
            EricPixmapCache.getIcon("editDelete"),
            self.tr("Cl&ear"),
            QKeySequence(self.tr("Alt+Shift+C", "Edit|Clear")),
            0,
            self,
            "vm_edit_clear",
        )
        self.deleteAct.setStatusTip(self.tr("Clear all text"))
        self.deleteAct.setWhatsThis(
            self.tr("""<b>Clear</b><p>Delete all text of the current editor.</p>""")
        )
        self.deleteAct.triggered.connect(self.__textEdit.clear)
        self.editActions.append(self.deleteAct)

        self.cutAct.setEnabled(False)
        self.copyAct.setEnabled(False)
        self.__textEdit.copyAvailable.connect(self.cutAct.setEnabled)
        self.__textEdit.copyAvailable.connect(self.copyAct.setEnabled)

        ####################################################################
        ## Below follow the actions for QScintilla standard commands.
        ####################################################################

        self.esm = QSignalMapper(self)
        self.esm.mappedInt.connect(self.__textEdit.editorCommand)

        self.editorActGrp = createActionGroup(self)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move left one character"),
            QCoreApplication.translate("ViewManager", "Move left one character"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Left")),
            0,
            self.editorActGrp,
            "vm_edit_move_left_char",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_CHARLEFT)
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+B"))
            )
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move right one character"),
            QCoreApplication.translate("ViewManager", "Move right one character"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Right")),
            0,
            self.editorActGrp,
            "vm_edit_move_right_char",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+F"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_CHARRIGHT)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move up one line"),
            QCoreApplication.translate("ViewManager", "Move up one line"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Up")),
            0,
            self.editorActGrp,
            "vm_edit_move_up_line",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+P"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEUP)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move down one line"),
            QCoreApplication.translate("ViewManager", "Move down one line"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Down")),
            0,
            self.editorActGrp,
            "vm_edit_move_down_line",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+N"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEDOWN)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move left one word part"),
            QCoreApplication.translate("ViewManager", "Move left one word part"),
            0,
            0,
            self.editorActGrp,
            "vm_edit_move_left_word_part",
        )
        if not OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Left"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_WORDPARTLEFT)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move right one word part"),
            QCoreApplication.translate("ViewManager", "Move right one word part"),
            0,
            0,
            self.editorActGrp,
            "vm_edit_move_right_word_part",
        )
        if not OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Right"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_WORDPARTRIGHT)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move left one word"),
            QCoreApplication.translate("ViewManager", "Move left one word"),
            0,
            0,
            self.editorActGrp,
            "vm_edit_move_left_word",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Left"))
            )
        else:
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Left"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_WORDLEFT)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move right one word"),
            QCoreApplication.translate("ViewManager", "Move right one word"),
            0,
            0,
            self.editorActGrp,
            "vm_edit_move_right_word",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Right"))
            )
        else:
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Right"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_WORDRIGHT)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Move to first visible character in document line"
            ),
            QCoreApplication.translate(
                "ViewManager", "Move to first visible character in document line"
            ),
            0,
            0,
            self.editorActGrp,
            "vm_edit_move_first_visible_char",
        )
        if not OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Home"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_VCHOME)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move to start of display line"),
            QCoreApplication.translate("ViewManager", "Move to start of display line"),
            0,
            0,
            self.editorActGrp,
            "vm_edit_move_start_line",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Left"))
            )
        else:
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Home"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_HOMEDISPLAY)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move to end of document line"),
            QCoreApplication.translate("ViewManager", "Move to end of document line"),
            0,
            0,
            self.editorActGrp,
            "vm_edit_move_end_line",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+E"))
            )
        else:
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "End"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Scroll view down one line"),
            QCoreApplication.translate("ViewManager", "Scroll view down one line"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Down")),
            0,
            self.editorActGrp,
            "vm_edit_scroll_down_line",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_LINESCROLLDOWN)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Scroll view up one line"),
            QCoreApplication.translate("ViewManager", "Scroll view up one line"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Up")),
            0,
            self.editorActGrp,
            "vm_edit_scroll_up_line",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_LINESCROLLUP)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move up one paragraph"),
            QCoreApplication.translate("ViewManager", "Move up one paragraph"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Up")),
            0,
            self.editorActGrp,
            "vm_edit_move_up_para",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_PARAUP)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move down one paragraph"),
            QCoreApplication.translate("ViewManager", "Move down one paragraph"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Down")),
            0,
            self.editorActGrp,
            "vm_edit_move_down_para",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_PARADOWN)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move up one page"),
            QCoreApplication.translate("ViewManager", "Move up one page"),
            QKeySequence(QCoreApplication.translate("ViewManager", "PgUp")),
            0,
            self.editorActGrp,
            "vm_edit_move_up_page",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_PAGEUP)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move down one page"),
            QCoreApplication.translate("ViewManager", "Move down one page"),
            QKeySequence(QCoreApplication.translate("ViewManager", "PgDown")),
            0,
            self.editorActGrp,
            "vm_edit_move_down_page",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+V"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_PAGEDOWN)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move to start of document"),
            QCoreApplication.translate("ViewManager", "Move to start of document"),
            0,
            0,
            self.editorActGrp,
            "vm_edit_move_start_text",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Up"))
            )
        else:
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Home"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_DOCUMENTSTART)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move to end of document"),
            QCoreApplication.translate("ViewManager", "Move to end of document"),
            0,
            0,
            self.editorActGrp,
            "vm_edit_move_end_text",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Down"))
            )
        else:
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+End"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_DOCUMENTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Indent one level"),
            QCoreApplication.translate("ViewManager", "Indent one level"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Tab")),
            0,
            self.editorActGrp,
            "vm_edit_indent_one_level",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_TAB)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Unindent one level"),
            QCoreApplication.translate("ViewManager", "Unindent one level"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Shift+Tab")),
            0,
            self.editorActGrp,
            "vm_edit_unindent_one_level",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_BACKTAB)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend selection left one character"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend selection left one character"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Shift+Left")),
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_left_char",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+Shift+B"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_CHARLEFTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend selection right one character"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend selection right one character"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Shift+Right")),
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_right_char",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+Shift+F"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_CHARRIGHTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Extend selection up one line"),
            QCoreApplication.translate("ViewManager", "Extend selection up one line"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Shift+Up")),
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_up_line",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+Shift+P"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEUPEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Extend selection down one line"),
            QCoreApplication.translate("ViewManager", "Extend selection down one line"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Shift+Down")),
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_down_line",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+Shift+N"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEDOWNEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend selection left one word part"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend selection left one word part"
            ),
            0,
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_left_word_part",
        )
        if not OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Alt+Shift+Left")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_WORDPARTLEFTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend selection right one word part"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend selection right one word part"
            ),
            0,
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_right_word_part",
        )
        if not OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Alt+Shift+Right")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_WORDPARTRIGHTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Extend selection left one word"),
            QCoreApplication.translate("ViewManager", "Extend selection left one word"),
            0,
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_left_word",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Alt+Shift+Left")
                )
            )
        else:
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Ctrl+Shift+Left")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_WORDLEFTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend selection right one word"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend selection right one word"
            ),
            0,
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_right_word",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Alt+Shift+Right")
                )
            )
        else:
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Ctrl+Shift+Right")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_WORDRIGHTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager",
                "Extend selection to first visible character in document line",
            ),
            QCoreApplication.translate(
                "ViewManager",
                "Extend selection to first visible character in document line",
            ),
            0,
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_first_visible_char",
        )
        if not OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Shift+Home"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_VCHOMEEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend selection to end of document line"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend selection to end of document line"
            ),
            0,
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_end_line",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+Shift+E"))
            )
        else:
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Shift+End"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEENDEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend selection up one paragraph"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend selection up one paragraph"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Shift+Up")),
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_up_para",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_PARAUPEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend selection down one paragraph"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend selection down one paragraph"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Shift+Down")),
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_down_para",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_PARADOWNEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Extend selection up one page"),
            QCoreApplication.translate("ViewManager", "Extend selection up one page"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Shift+PgUp")),
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_up_page",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_PAGEUPEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Extend selection down one page"),
            QCoreApplication.translate("ViewManager", "Extend selection down one page"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Shift+PgDown")),
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_down_page",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+Shift+V"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_PAGEDOWNEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend selection to start of document"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend selection to start of document"
            ),
            0,
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_start_text",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Shift+Up"))
            )
        else:
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Ctrl+Shift+Home")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_DOCUMENTSTARTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend selection to end of document"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend selection to end of document"
            ),
            0,
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_end_text",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Ctrl+Shift+Down")
                )
            )
        else:
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Ctrl+Shift+End")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_DOCUMENTENDEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Delete previous character"),
            QCoreApplication.translate("ViewManager", "Delete previous character"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Backspace")),
            0,
            self.editorActGrp,
            "vm_edit_delete_previous_char",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+H"))
            )
        else:
            act.setAlternateShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Shift+Backspace")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_DELETEBACK)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Delete previous character if not at start of line"
            ),
            QCoreApplication.translate(
                "ViewManager", "Delete previous character if not at start of line"
            ),
            0,
            0,
            self.editorActGrp,
            "vm_edit_delet_previous_char_not_line_start",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_DELETEBACKNOTLINE)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Delete current character"),
            QCoreApplication.translate("ViewManager", "Delete current character"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Del")),
            0,
            self.editorActGrp,
            "vm_edit_delete_current_char",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+D"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_CLEAR)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Delete word to left"),
            QCoreApplication.translate("ViewManager", "Delete word to left"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Backspace")),
            0,
            self.editorActGrp,
            "vm_edit_delete_word_left",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_DELWORDLEFT)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Delete word to right"),
            QCoreApplication.translate("ViewManager", "Delete word to right"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Del")),
            0,
            self.editorActGrp,
            "vm_edit_delete_word_right",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_DELWORDRIGHT)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Delete line to left"),
            QCoreApplication.translate("ViewManager", "Delete line to left"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+Shift+Backspace")
            ),
            0,
            self.editorActGrp,
            "vm_edit_delete_line_left",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_DELLINELEFT)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Delete line to right"),
            QCoreApplication.translate("ViewManager", "Delete line to right"),
            0,
            0,
            self.editorActGrp,
            "vm_edit_delete_line_right",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Meta+K"))
            )
        else:
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Ctrl+Shift+Del")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_DELLINERIGHT)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Insert new line"),
            QCoreApplication.translate("ViewManager", "Insert new line"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Return")),
            QKeySequence(QCoreApplication.translate("ViewManager", "Enter")),
            self.editorActGrp,
            "vm_edit_insert_line",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_NEWLINE)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Delete current line"),
            QCoreApplication.translate("ViewManager", "Delete current line"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Shift+L")),
            0,
            self.editorActGrp,
            "vm_edit_delete_current_line",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEDELETE)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Duplicate current line"),
            QCoreApplication.translate("ViewManager", "Duplicate current line"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+D")),
            0,
            self.editorActGrp,
            "vm_edit_duplicate_current_line",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEDUPLICATE)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Swap current and previous lines"
            ),
            QCoreApplication.translate(
                "ViewManager", "Swap current and previous lines"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+T")),
            0,
            self.editorActGrp,
            "vm_edit_swap_current_previous_line",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_LINETRANSPOSE)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Reverse selected lines"),
            QCoreApplication.translate("ViewManager", "Reverse selected lines"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Meta+Alt+R")),
            0,
            self.editorActGrp,
            "vm_edit_reverse selected_lines",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEREVERSE)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Cut current line"),
            QCoreApplication.translate("ViewManager", "Cut current line"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Shift+L")),
            0,
            self.editorActGrp,
            "vm_edit_cut_current_line",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_LINECUT)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Copy current line"),
            QCoreApplication.translate("ViewManager", "Copy current line"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Shift+T")),
            0,
            self.editorActGrp,
            "vm_edit_copy_current_line",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_LINECOPY)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Toggle insert/overtype"),
            QCoreApplication.translate("ViewManager", "Toggle insert/overtype"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ins")),
            0,
            self.editorActGrp,
            "vm_edit_toggle_insert_overtype",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_EDITTOGGLEOVERTYPE)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Convert selection to lower case"
            ),
            QCoreApplication.translate(
                "ViewManager", "Convert selection to lower case"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Shift+U")),
            0,
            self.editorActGrp,
            "vm_edit_convert_selection_lower",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_LOWERCASE)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Convert selection to upper case"
            ),
            QCoreApplication.translate(
                "ViewManager", "Convert selection to upper case"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Shift+U")),
            0,
            self.editorActGrp,
            "vm_edit_convert_selection_upper",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_UPPERCASE)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Move to end of display line"),
            QCoreApplication.translate("ViewManager", "Move to end of display line"),
            0,
            0,
            self.editorActGrp,
            "vm_edit_move_end_displayed_line",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Right"))
            )
        else:
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Alt+End"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEENDDISPLAY)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend selection to end of display line"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend selection to end of display line"
            ),
            0,
            0,
            self.editorActGrp,
            "vm_edit_extend_selection_end_displayed_line",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Ctrl+Shift+Right")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEENDDISPLAYEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Formfeed"),
            QCoreApplication.translate("ViewManager", "Formfeed"),
            0,
            0,
            self.editorActGrp,
            "vm_edit_formfeed",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_FORMFEED)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Escape"),
            QCoreApplication.translate("ViewManager", "Escape"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Esc")),
            0,
            self.editorActGrp,
            "vm_edit_escape",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_CANCEL)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection down one line"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection down one line"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Ctrl+Down")),
            0,
            self.editorActGrp,
            "vm_edit_extend_rect_selection_down_line",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Meta+Alt+Shift+N")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEDOWNRECTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection up one line"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection up one line"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Ctrl+Up")),
            0,
            self.editorActGrp,
            "vm_edit_extend_rect_selection_up_line",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Meta+Alt+Shift+P")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEUPRECTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection left one character"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection left one character"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Ctrl+Left")),
            0,
            self.editorActGrp,
            "vm_edit_extend_rect_selection_left_char",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Meta+Alt+Shift+B")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_CHARLEFTRECTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection right one character"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection right one character"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Ctrl+Right")),
            0,
            self.editorActGrp,
            "vm_edit_extend_rect_selection_right_char",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Meta+Alt+Shift+F")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_CHARRIGHTRECTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager",
                "Extend rectangular selection to first"
                " visible character in document line",
            ),
            QCoreApplication.translate(
                "ViewManager",
                "Extend rectangular selection to first"
                " visible character in document line",
            ),
            0,
            0,
            self.editorActGrp,
            "vm_edit_extend_rect_selection_first_visible_char",
        )
        if not OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Alt+Shift+Home")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_VCHOMERECTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection to end of document line"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection to end of document line"
            ),
            0,
            0,
            self.editorActGrp,
            "vm_edit_extend_rect_selection_end_line",
        )
        if OSUtilities.isMacPlatform():
            act.setShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Meta+Alt+Shift+E")
                )
            )
        else:
            act.setShortcut(
                QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Shift+End"))
            )
        self.esm.setMapping(act, QsciScintilla.SCI_LINEENDRECTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection up one page"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection up one page"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Shift+PgUp")),
            0,
            self.editorActGrp,
            "vm_edit_extend_rect_selection_up_page",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_PAGEUPRECTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection down one page"
            ),
            QCoreApplication.translate(
                "ViewManager", "Extend rectangular selection down one page"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Shift+PgDown")),
            0,
            self.editorActGrp,
            "vm_edit_extend_rect_selection_down_page",
        )
        if OSUtilities.isMacPlatform():
            act.setAlternateShortcut(
                QKeySequence(
                    QCoreApplication.translate("ViewManager", "Meta+Alt+Shift+V")
                )
            )
        self.esm.setMapping(act, QsciScintilla.SCI_PAGEDOWNRECTEXTEND)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Duplicate current selection"),
            QCoreApplication.translate("ViewManager", "Duplicate current selection"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Shift+D")),
            0,
            self.editorActGrp,
            "vm_edit_duplicate_current_selection",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_SELECTIONDUPLICATE)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_SCROLLTOSTART"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Scroll to start of document"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Scroll to start of document"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_scroll_start_text",
            )
            if OSUtilities.isMacPlatform():
                act.setShortcut(
                    QKeySequence(QCoreApplication.translate("ViewManager", "Home"))
                )
            self.esm.setMapping(act, QsciScintilla.SCI_SCROLLTOSTART)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_SCROLLTOEND"):
            act = EricAction(
                QCoreApplication.translate("ViewManager", "Scroll to end of document"),
                QCoreApplication.translate("ViewManager", "Scroll to end of document"),
                0,
                0,
                self.editorActGrp,
                "vm_edit_scroll_end_text",
            )
            if OSUtilities.isMacPlatform():
                act.setShortcut(
                    QKeySequence(QCoreApplication.translate("ViewManager", "End"))
                )
            self.esm.setMapping(act, QsciScintilla.SCI_SCROLLTOEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_VERTICALCENTRECARET"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Scroll vertically to center current line"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Scroll vertically to center current line"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_scroll_vertically_center",
            )
            if OSUtilities.isMacPlatform():
                act.setShortcut(
                    QKeySequence(QCoreApplication.translate("ViewManager", "Meta+L"))
                )
            self.esm.setMapping(act, QsciScintilla.SCI_VERTICALCENTRECARET)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_WORDRIGHTEND"):
            act = EricAction(
                QCoreApplication.translate("ViewManager", "Move to end of next word"),
                QCoreApplication.translate("ViewManager", "Move to end of next word"),
                0,
                0,
                self.editorActGrp,
                "vm_edit_move_end_next_word",
            )
            if OSUtilities.isMacPlatform():
                act.setShortcut(
                    QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Right"))
                )
            self.esm.setMapping(act, QsciScintilla.SCI_WORDRIGHTEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_WORDRIGHTENDEXTEND"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Extend selection to end of next word"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Extend selection to end of next word"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_select_end_next_word",
            )
            if OSUtilities.isMacPlatform():
                act.setShortcut(
                    QKeySequence(
                        QCoreApplication.translate("ViewManager", "Alt+Shift+Right")
                    )
                )
            self.esm.setMapping(act, QsciScintilla.SCI_WORDRIGHTENDEXTEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_WORDLEFTEND"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Move to end of previous word"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Move to end of previous word"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_move_end_previous_word",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_WORDLEFTEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_WORDLEFTENDEXTEND"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Extend selection to end of previous word"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Extend selection to end of previous word"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_select_end_previous_word",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_WORDLEFTENDEXTEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_HOME"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Move to start of document line"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Move to start of document line"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_move_start_document_line",
            )
            if OSUtilities.isMacPlatform():
                act.setShortcut(
                    QKeySequence(QCoreApplication.translate("ViewManager", "Meta+A"))
                )
            self.esm.setMapping(act, QsciScintilla.SCI_HOME)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_HOMEEXTEND"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Extend selection to start of document line"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Extend selection to start of document line"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_extend_selection_start_document_line",
            )
            if OSUtilities.isMacPlatform():
                act.setShortcut(
                    QKeySequence(
                        QCoreApplication.translate("ViewManager", "Meta+Shift+A")
                    )
                )
            self.esm.setMapping(act, QsciScintilla.SCI_HOME)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_HOMERECTEXTEND"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager",
                    "Extend rectangular selection to start of document line",
                ),
                QCoreApplication.translate(
                    "ViewManager",
                    "Extend rectangular selection to start of document line",
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_select_rect_start_line",
            )
            if OSUtilities.isMacPlatform():
                act.setShortcut(
                    QKeySequence(
                        QCoreApplication.translate("ViewManager", "Meta+Alt+Shift+A")
                    )
                )
            self.esm.setMapping(act, QsciScintilla.SCI_HOMERECTEXTEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_HOMEDISPLAYEXTEND"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Extend selection to start of display line"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Extend selection to start of display line"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_extend_selection_start_display_line",
            )
            if OSUtilities.isMacPlatform():
                act.setShortcut(
                    QKeySequence(
                        QCoreApplication.translate("ViewManager", "Ctrl+Shift+Left")
                    )
                )
            self.esm.setMapping(act, QsciScintilla.SCI_HOMEDISPLAYEXTEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_HOMEWRAP"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Move to start of display or document line"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Move to start of display or document line"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_move_start_display_document_line",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_HOMEWRAP)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_HOMEWRAPEXTEND"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager",
                    "Extend selection to start of display or document line",
                ),
                QCoreApplication.translate(
                    "ViewManager",
                    "Extend selection to start of display or document line",
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_extend_selection_start_display_document_line",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_HOMEWRAPEXTEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_VCHOMEWRAP"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager",
                    "Move to first visible character in display or document line",
                ),
                QCoreApplication.translate(
                    "ViewManager",
                    "Move to first visible character in display or document line",
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_move_first_visible_char_document_line",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_VCHOMEWRAP)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_VCHOMEWRAPEXTEND"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager",
                    "Extend selection to first visible character in"
                    " display or document line",
                ),
                QCoreApplication.translate(
                    "ViewManager",
                    "Extend selection to first visible character in"
                    " display or document line",
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_extend_selection_first_visible_char_document_line",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_VCHOMEWRAPEXTEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_LINEENDWRAP"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Move to end of display or document line"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Move to end of display or document line"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_end_start_display_document_line",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_LINEENDWRAP)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_LINEENDWRAPEXTEND"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Extend selection to end of display or document line"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Extend selection to end of display or document line"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_extend_selection_end_display_document_line",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_LINEENDWRAPEXTEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_STUTTEREDPAGEUP"):
            act = EricAction(
                QCoreApplication.translate("ViewManager", "Stuttered move up one page"),
                QCoreApplication.translate("ViewManager", "Stuttered move up one page"),
                0,
                0,
                self.editorActGrp,
                "vm_edit_stuttered_move_up_page",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_STUTTEREDPAGEUP)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_STUTTEREDPAGEUPEXTEND"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Stuttered extend selection up one page"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Stuttered extend selection up one page"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_stuttered_extend_selection_up_page",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_STUTTEREDPAGEUPEXTEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_STUTTEREDPAGEDOWN"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Stuttered move down one page"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Stuttered move down one page"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_stuttered_move_down_page",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_STUTTEREDPAGEDOWN)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_STUTTEREDPAGEDOWNEXTEND"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Stuttered extend selection down one page"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Stuttered extend selection down one page"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_stuttered_extend_selection_down_page",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_STUTTEREDPAGEDOWNEXTEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_DELWORDRIGHTEND"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Delete right to end of next word"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Delete right to end of next word"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_delete_right_end_next_word",
            )
            if OSUtilities.isMacPlatform():
                act.setShortcut(
                    QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Del"))
                )
            self.esm.setMapping(act, QsciScintilla.SCI_DELWORDRIGHTEND)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_MOVESELECTEDLINESUP"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Move selected lines up one line"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Move selected lines up one line"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_move_selection_up_one_line",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_MOVESELECTEDLINESUP)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        if hasattr(QsciScintilla, "SCI_MOVESELECTEDLINESDOWN"):
            act = EricAction(
                QCoreApplication.translate(
                    "ViewManager", "Move selected lines down one line"
                ),
                QCoreApplication.translate(
                    "ViewManager", "Move selected lines down one line"
                ),
                0,
                0,
                self.editorActGrp,
                "vm_edit_move_selection_down_one_line",
            )
            self.esm.setMapping(act, QsciScintilla.SCI_MOVESELECTEDLINESDOWN)
            act.triggered.connect(self.esm.map)
            self.editActions.append(act)

        act = EricAction(
            QCoreApplication.translate("ViewManager", "Duplicate current selection"),
            QCoreApplication.translate("ViewManager", "Duplicate current selection"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Shift+D")),
            0,
            self.editorActGrp,
            "vm_edit_duplicate_current_selection",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_SELECTIONDUPLICATE)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        self.__textEdit.addActions(self.editorActGrp.actions())

    def __createSearchActions(self):
        """
        Private method defining the user interface actions for the search
            commands.
        """
        self.searchAct = EricAction(
            QCoreApplication.translate("ViewManager", "Search"),
            EricPixmapCache.getIcon("find"),
            QCoreApplication.translate("ViewManager", "&Search..."),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+F", "Search|Search")
            ),
            0,
            self,
            "vm_search",
        )
        self.searchAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Search for a text")
        )
        self.searchAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Search</b>"""
                """<p>Search for some text in the current editor. A"""
                """ dialog is shown to enter the searchtext and options"""
                """ for the search.</p>""",
            )
        )
        self.searchAct.triggered.connect(self.showSearchWidget)
        self.searchActions.append(self.searchAct)

        self.searchNextAct = EricAction(
            QCoreApplication.translate("ViewManager", "Search next"),
            EricPixmapCache.getIcon("findNext"),
            QCoreApplication.translate("ViewManager", "Search &next"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "F3", "Search|Search next")
            ),
            0,
            self,
            "vm_search_next",
        )
        self.searchNextAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Search next occurrence of text")
        )
        self.searchNextAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Search next</b>"""
                """<p>Search the next occurrence of some text in the current"""
                """ editor. The previously entered searchtext and options are"""
                """ reused.</p>""",
            )
        )
        self.searchNextAct.triggered.connect(self.__searchNext)
        self.searchActions.append(self.searchNextAct)

        self.searchPrevAct = EricAction(
            QCoreApplication.translate("ViewManager", "Search previous"),
            EricPixmapCache.getIcon("findPrev"),
            QCoreApplication.translate("ViewManager", "Search &previous"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Shift+F3", "Search|Search previous"
                )
            ),
            0,
            self,
            "vm_search_previous",
        )
        self.searchPrevAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Search previous occurrence of text"
            )
        )
        self.searchPrevAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Search previous</b>"""
                """<p>Search the previous occurrence of some text in the"""
                """ current editor. The previously entered searchtext and"""
                """ options are reused.</p>""",
            )
        )
        self.searchPrevAct.triggered.connect(self.__searchPrev)
        self.searchActions.append(self.searchPrevAct)

        self.searchClearMarkersAct = EricAction(
            QCoreApplication.translate("ViewManager", "Clear search markers"),
            EricPixmapCache.getIcon("findClear"),
            QCoreApplication.translate("ViewManager", "Clear search markers"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+3", "Search|Clear search markers"
                )
            ),
            0,
            self,
            "vm_clear_search_markers",
        )
        self.searchClearMarkersAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Clear all displayed search markers"
            )
        )
        self.searchClearMarkersAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Clear search markers</b>"""
                """<p>Clear all displayed search markers.</p>""",
            )
        )
        self.searchClearMarkersAct.triggered.connect(self.__searchClearMarkers)
        self.searchActions.append(self.searchClearMarkersAct)

        self.replaceAct = EricAction(
            QCoreApplication.translate("ViewManager", "Replace"),
            QCoreApplication.translate("ViewManager", "&Replace..."),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+R", "Search|Replace")
            ),
            0,
            self,
            "vm_search_replace",
        )
        self.replaceAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Replace some text")
        )
        self.replaceAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Replace</b>"""
                """<p>Search for some text in the current editor and replace"""
                """ it. A dialog is shown to enter the searchtext, the"""
                """ replacement text and options for the search and replace.</p>""",
            )
        )
        self.replaceAct.triggered.connect(self.showReplaceWidget)
        self.searchActions.append(self.replaceAct)

        self.replaceAndSearchAct = EricAction(
            QCoreApplication.translate("ViewManager", "Replace and Search"),
            EricPixmapCache.getIcon("editReplaceSearch"),
            QCoreApplication.translate("ViewManager", "Replace and Search"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Meta+R", "Search|Replace and Search"
                )
            ),
            0,
            self,
            "vm_replace_search",
        )
        self.replaceAndSearchAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Replace the found text and search the next occurrence"
            )
        )
        self.replaceAndSearchAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Replace and Search</b>"""
                """<p>Replace the found occurrence of text in the current"""
                """ editor and search for the next one. The previously entered"""
                """ search text and options are reused.</p>""",
            )
        )
        self.replaceAndSearchAct.triggered.connect(
            self.__searchReplaceWidget.replaceSearch
        )
        self.searchActions.append(self.replaceAndSearchAct)

        self.replaceSelectionAct = EricAction(
            QCoreApplication.translate("ViewManager", "Replace Occurrence"),
            EricPixmapCache.getIcon("editReplace"),
            QCoreApplication.translate("ViewManager", "Replace Occurrence"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+Meta+R", "Search|Replace Occurrence"
                )
            ),
            0,
            self,
            "vm_replace_occurrence",
        )
        self.replaceSelectionAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Replace the found text")
        )
        self.replaceSelectionAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Replace Occurrence</b>"""
                """<p>Replace the found occurrence of the search text in the"""
                """ current editor.</p>""",
            )
        )
        self.replaceSelectionAct.triggered.connect(self.__searchReplaceWidget.replace)
        self.searchActions.append(self.replaceSelectionAct)

        self.replaceAllAct = EricAction(
            QCoreApplication.translate("ViewManager", "Replace All"),
            EricPixmapCache.getIcon("editReplaceAll"),
            QCoreApplication.translate("ViewManager", "Replace All"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Shift+Meta+R", "Search|Replace All"
                )
            ),
            0,
            self,
            "vm_replace_all",
        )
        self.replaceAllAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Replace search text occurrences")
        )
        self.replaceAllAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Replace All</b>"""
                """<p>Replace all occurrences of the search text in the current"""
                """ editor.</p>""",
            )
        )
        self.replaceAllAct.triggered.connect(self.__searchReplaceWidget.replaceAll)
        self.searchActions.append(self.replaceAllAct)

    def __createViewActions(self):
        """
        Private method to create the View actions.
        """
        self.zoomInAct = EricAction(
            QCoreApplication.translate("ViewManager", "Zoom in"),
            EricPixmapCache.getIcon("zoomIn"),
            QCoreApplication.translate("ViewManager", "Zoom &in"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl++", "View|Zoom in")
            ),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Zoom In", "View|Zoom in")
            ),
            self,
            "vm_view_zoom_in",
        )
        self.zoomInAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Zoom in on the text")
        )
        self.zoomInAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Zoom in</b>"""
                """<p>Zoom in on the text. This makes the text bigger.</p>""",
            )
        )
        self.zoomInAct.triggered.connect(self.__zoomIn)
        self.viewActions.append(self.zoomInAct)

        self.zoomOutAct = EricAction(
            QCoreApplication.translate("ViewManager", "Zoom out"),
            EricPixmapCache.getIcon("zoomOut"),
            QCoreApplication.translate("ViewManager", "Zoom &out"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+-", "View|Zoom out")
            ),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Zoom Out", "View|Zoom out")
            ),
            self,
            "vm_view_zoom_out",
        )
        self.zoomOutAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Zoom out on the text")
        )
        self.zoomOutAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Zoom out</b>"""
                """<p>Zoom out on the text. This makes the text smaller.</p>""",
            )
        )
        self.zoomOutAct.triggered.connect(self.__zoomOut)
        self.viewActions.append(self.zoomOutAct)

        self.zoomResetAct = EricAction(
            QCoreApplication.translate("ViewManager", "Zoom reset"),
            EricPixmapCache.getIcon("zoomReset"),
            QCoreApplication.translate("ViewManager", "Zoom &reset"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+0", "View|Zoom reset")
            ),
            0,
            self,
            "vm_view_zoom_reset",
        )
        self.zoomResetAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Reset the zoom of the text")
        )
        self.zoomResetAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Zoom reset</b>"""
                """<p>Reset the zoom of the text. """
                """This sets the zoom factor to 100%.</p>""",
            )
        )
        self.zoomResetAct.triggered.connect(self.__zoomReset)
        self.viewActions.append(self.zoomResetAct)

        self.zoomToAct = EricAction(
            QCoreApplication.translate("ViewManager", "Zoom"),
            EricPixmapCache.getIcon("zoomTo"),
            QCoreApplication.translate("ViewManager", "&Zoom"),
            0,
            0,
            self,
            "vm_view_zoom",
        )
        self.zoomToAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Zoom the text")
        )
        self.zoomToAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Zoom</b>"""
                """<p>Zoom the text. This opens a dialog where the"""
                """ desired size can be entered.</p>""",
            )
        )
        self.zoomToAct.triggered.connect(self.__zoom)
        self.viewActions.append(self.zoomToAct)

    def __createHelpActions(self):
        """
        Private method to create the Help actions.
        """
        self.aboutAct = EricAction(
            self.tr("About"), self.tr("&About"), 0, 0, self, "about_eric"
        )
        self.aboutAct.setStatusTip(self.tr("Display information about this software"))
        self.aboutAct.setWhatsThis(
            self.tr(
                """<b>About</b>"""
                """<p>Display some information about this software.</p>"""
            )
        )
        self.aboutAct.triggered.connect(self.__about)
        self.helpActions.append(self.aboutAct)

        self.aboutQtAct = EricAction(
            self.tr("About Qt"), self.tr("About &Qt"), 0, 0, self, "about_qt"
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
        self.helpActions.append(self.aboutQtAct)

        self.whatsThisAct = EricAction(
            self.tr("What's This?"),
            EricPixmapCache.getIcon("whatsThis"),
            self.tr("&What's This?"),
            QKeySequence(self.tr("Shift+F1", "Help|What's This?'")),
            0,
            self,
            "help_help_whats_this",
        )
        self.whatsThisAct.setStatusTip(self.tr("Context sensitive help"))
        self.whatsThisAct.setWhatsThis(
            self.tr(
                """<b>Display context sensitive help</b>"""
                """<p>In What's This? mode, the mouse cursor shows an arrow"""
                """ with a question mark, and you can click on the interface"""
                """ elements to get a short description of what they do and"""
                """ how to use them. In dialogs, this feature can be"""
                """ accessed using the context help button in the titlebar."""
                """</p>"""
            )
        )
        self.whatsThisAct.triggered.connect(self.__whatsThis)
        self.helpActions.append(self.whatsThisAct)

    def __createConfigActions(self):
        """
        Private method to create the Settings actions.
        """
        self.prefAct = EricAction(
            self.tr("Preferences"),
            EricPixmapCache.getIcon("configure"),
            self.tr("&Preferences..."),
            0,
            0,
            self,
            "hexEditor_settings_preferences",
        )
        self.prefAct.setStatusTip(self.tr("Set the prefered configuration"))
        self.prefAct.setWhatsThis(
            self.tr(
                """<b>Preferences</b>"""
                """<p>Set the configuration items of the application"""
                """ with your prefered values.</p>"""
            )
        )
        self.prefAct.triggered.connect(self.__showPreferences)
        self.prefAct.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.configActions.append(self.prefAct)

    def __createMenus(self):
        """
        Private method to create the menus of the menu bar.
        """
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self.fileMenu.addAction(self.newAct)
        self.fileMenu.addAction(self.openAct)
        self.fileMenu.addAction(self.saveAct)
        self.fileMenu.addAction(self.saveAsAct)
        self.fileMenu.addAction(self.saveCopyAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.printPreviewAct)
        self.fileMenu.addAction(self.printAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.closeAct)

        self.editMenu = self.menuBar().addMenu(self.tr("&Edit"))
        self.editMenu.addAction(self.undoAct)
        self.editMenu.addAction(self.redoAct)
        self.editMenu.addSeparator()
        self.editMenu.addAction(self.cutAct)
        self.editMenu.addAction(self.copyAct)
        self.editMenu.addAction(self.pasteAct)
        self.editMenu.addAction(self.deleteAct)
        self.editMenu.addSeparator()

        self.searchMenu = self.menuBar().addMenu(self.tr("&Search"))
        self.searchMenu.addAction(self.searchAct)
        self.searchMenu.addAction(self.searchNextAct)
        self.searchMenu.addAction(self.searchPrevAct)
        self.searchMenu.addAction(self.searchClearMarkersAct)
        self.searchMenu.addAction(self.replaceAct)
        self.searchMenu.addAction(self.replaceAndSearchAct)
        self.searchMenu.addAction(self.replaceSelectionAct)
        self.searchMenu.addAction(self.replaceAllAct)

        self.viewMenu = self.menuBar().addMenu(self.tr("&View"))
        self.viewMenu.addAction(self.zoomInAct)
        self.viewMenu.addAction(self.zoomOutAct)
        self.viewMenu.addAction(self.zoomResetAct)
        self.viewMenu.addAction(self.zoomToAct)

        self.settingsMenu = self.menuBar().addMenu(self.tr("Se&ttings"))
        self.settingsMenu.addAction(self.prefAct)

        self.menuBar().addSeparator()

        self.helpMenu = self.menuBar().addMenu(self.tr("&Help"))
        self.helpMenu.addAction(self.aboutAct)
        self.helpMenu.addAction(self.aboutQtAct)
        self.helpMenu.addSeparator()
        self.helpMenu.addAction(self.whatsThisAct)

        self.__initContextMenu()

    def __createToolBars(self):
        """
        Private method to create the various toolbars.
        """
        filetb = self.addToolBar(self.tr("File"))
        filetb.addAction(self.newAct)
        filetb.addAction(self.openAct)
        filetb.addAction(self.saveAct)
        filetb.addAction(self.saveAsAct)
        filetb.addAction(self.saveCopyAct)
        filetb.addSeparator()
        filetb.addAction(self.printPreviewAct)
        filetb.addAction(self.printAct)
        filetb.addSeparator()
        filetb.addAction(self.closeAct)

        edittb = self.addToolBar(self.tr("Edit"))
        edittb.addAction(self.undoAct)
        edittb.addAction(self.redoAct)
        edittb.addSeparator()
        edittb.addAction(self.cutAct)
        edittb.addAction(self.copyAct)
        edittb.addAction(self.pasteAct)
        edittb.addAction(self.deleteAct)

        findtb = self.addToolBar(self.tr("Search"))
        findtb.addAction(self.searchAct)
        findtb.addAction(self.searchNextAct)
        findtb.addAction(self.searchPrevAct)
        findtb.addAction(self.searchClearMarkersAct)

        viewtb = self.addToolBar(self.tr("View"))
        viewtb.addAction(self.zoomInAct)
        viewtb.addAction(self.zoomOutAct)
        viewtb.addAction(self.zoomResetAct)
        viewtb.addAction(self.zoomToAct)

        settingstb = self.addToolBar(self.tr("Settings"))
        settingstb.addAction(self.prefAct)

        helptb = self.addToolBar(self.tr("Help"))
        helptb.addAction(self.whatsThisAct)

    def __createStatusBar(self):
        """
        Private method to initialize the status bar.
        """
        self.__statusBar = self.statusBar()
        self.__statusBar.setSizeGripEnabled(True)

        self.sbLanguage = EricClickableLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbLanguage)
        self.sbLanguage.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays the"""
                """ editor language.</p>"""
            )
        )
        self.sbLanguage.clicked.connect(self.__showLanguagesMenu)

        self.sbWritable = QLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbWritable)
        self.sbWritable.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays an indication of the"""
                """ editors files writability.</p>"""
            )
        )

        self.sbLine = QLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbLine)
        self.sbLine.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays the line number of"""
                """ the editor.</p>"""
            )
        )

        self.sbPos = QLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbPos)
        self.sbPos.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays the cursor position"""
                """ of the editor.</p>"""
            )
        )

        self.sbZoom = EricZoomWidget(
            EricPixmapCache.getPixmap("zoomOut"),
            EricPixmapCache.getPixmap("zoomIn"),
            EricPixmapCache.getPixmap("zoomReset"),
            self.__statusBar,
        )
        self.__statusBar.addPermanentWidget(self.sbZoom)
        self.sbZoom.setWhatsThis(
            self.tr(
                """<p>This part of the status bar allows zooming the editor."""
                """</p>"""
            )
        )
        self.sbZoom.valueChanged.connect(self.__zoomTo)

        self.__statusBar.showMessage(self.tr("Ready"))

    def __showPreferences(self):
        """
        Private slot to set the preferences.
        """
        from eric7.Preferences.ConfigurationDialog import (
            ConfigurationDialog,
            ConfigurationMode,
        )

        dlg = ConfigurationDialog(
            parent=self,
            name="Configuration",
            modal=True,
            fromEric=True,
            displayMode=ConfigurationMode.EDITORMODE,
        )
        dlg.preferencesChanged.connect(self.__preferencesChanged)
        dlg.show()
        dlg.showConfigurationPageByName("interfacePage")
        dlg.exec()
        QCoreApplication.processEvents()
        if dlg.result() == QDialog.DialogCode.Accepted:
            dlg.setPreferences()
            Preferences.syncPreferences()
            self.__preferencesChanged()

    @pyqtSlot()
    def __preferencesChanged(self):
        """
        Private slot to handle a configuration change.
        """
        self.__loadConfiguration()

        self.__markOccurrencesTimer.setInterval(
            Preferences.getEditor("MarkOccurrencesTimeout")
        )

    @pyqtSlot()
    def __loadConfiguration(self):
        """
        Private slot to load the configuration.
        """
        self.__setTextDisplay()
        self.__setMargins()
        self.__setEolMode()

    def __readSettings(self):
        """
        Private method to read the settings remembered last time.
        """
        settings = Preferences.getSettings()
        pos = settings.value("MiniEditor/Position", QPoint(0, 0))
        size = settings.value("MiniEditor/Size", QSize(800, 600))
        self.resize(size)
        self.move(pos)

    def __writeSettings(self):
        """
        Private method to write the settings for reuse.
        """
        settings = Preferences.getSettings()
        settings.setValue("MiniEditor/Position", self.pos())
        settings.setValue("MiniEditor/Size", self.size())

    def __maybeSave(self):
        """
        Private method to ask the user to save the file, if it was modified.

        @return flag indicating, if it is ok to continue
        @rtype bool
        """
        if self.__textEdit.isModified():
            ret = EricMessageBox.okToClearData(
                self,
                self.tr("eric Mini Editor"),
                self.tr("The document has unsaved changes."),
                self.__save,
            )
            return ret
        return True

    def __loadFile(self, fileName, filetype=None):
        """
        Private method to load the given file.

        @param fileName name of the file to load
        @type str
        @param filetype type of the source file
        @type str
        """
        self.__loadEditorConfig(fileName=fileName)

        try:
            with EricOverrideCursor():
                encoding = self.__getEditorConfig("DefaultEncoding", nodefault=True)
                if encoding:
                    txt, self.encoding = Utilities.readEncodedFileWithEncoding(
                        fileName, encoding
                    )
                else:
                    txt, self.encoding = Utilities.readEncodedFile(fileName)
        except (OSError, UnicodeDecodeError) as why:
            EricMessageBox.critical(
                self,
                self.tr("Open File"),
                self.tr(
                    "<p>The file <b>{0}</b> could not be opened.</p>"
                    "<p>Reason: {1}</p>"
                ).format(fileName, str(why)),
            )
            return

        with EricOverrideCursor():
            self.__textEdit.setText(txt)

            if filetype is None:
                self.filetype = ""
            else:
                self.filetype = filetype
            self.__setCurrentFile(fileName)

            self.__textEdit.setModified(False)
            self.setWindowModified(False)

            self.__convertTabs()

            eolMode = self.__getEditorConfig("EOLMode", nodefault=True)
            if eolMode is None:
                fileEol = self.__textEdit.detectEolString(txt)
                self.__textEdit.setEolModeByEolString(fileEol)
            else:
                self.__textEdit.convertEols(eolMode)

        self.__statusBar.showMessage(self.tr("File loaded"), 2000)

    def __convertTabs(self):
        """
        Private slot to convert tabulators to spaces.
        """
        if (
            (not self.__getEditorConfig("TabForIndentation"))
            and Preferences.getEditor("ConvertTabsOnLoad")
            and not (self.lexer_ and self.lexer_.alwaysKeepTabs())
        ):
            txt = self.__textEdit.text()
            txtExpanded = txt.expandtabs(self.__getEditorConfig("TabWidth"))
            if txtExpanded != txt:
                self.__textEdit.beginUndoAction()
                self.__textEdit.setText(txt)
                self.__textEdit.endUndoAction()

                self.__textEdit.setModified(True)
                self.setWindowModified(True)

    def __saveFile(self, fileName):
        """
        Private method to save to the given file.

        @param fileName name of the file to save to
        @type str
        @return flag indicating success
        @rtype bool
        """
        res = self.__writeFile(fileName)

        if res:
            self.editorSaved.emit()
            self.__setCurrentFile(fileName)

        self.__checkActions()

        return res

    def __writeFile(self, fileName):
        """
        Private method to write the current editor text to a file.

        @param fileName name of the file to be written to
        @type str
        @return flag indicating success
        @rtype bool
        """
        config = self.__loadEditorConfigObject(fileName)

        eol = self.__getEditorConfig("EOLMode", nodefault=True, config=config)
        if eol is not None:
            self.__textEdit.convertEols(eol)

        if self.__getEditorConfig("StripTrailingWhitespace", config=config):
            self.__textEdit.removeTrailingWhitespace()

        txt = self.__textEdit.text()

        if self.__getEditorConfig("InsertFinalNewline", config=config):
            eol = self.__textEdit.getLineSeparator()
            if eol:
                if len(txt) >= len(eol):
                    if txt[-len(eol) :] != eol:
                        txt += eol
                else:
                    txt += eol

        # now write text to the file
        try:
            with EricOverrideCursor():
                editorConfigEncoding = self.__getEditorConfig(
                    "DefaultEncoding", nodefault=True, config=config
                )
                self.encoding = Utilities.writeEncodedFile(
                    fileName, txt, self.encoding, forcedEncoding=editorConfigEncoding
                )
        except (OSError, UnicodeError, Utilities.CodingError) as why:
            EricMessageBox.critical(
                self,
                self.tr("Save File"),
                self.tr(
                    "<p>The file <b>{0}</b> could not be saved.<br/>Reason: {1}</p>"
                ).format(fileName, str(why)),
            )
            return False

        self.__statusBar.showMessage(self.tr("File saved"), 2000)

        return True

    def setWindowModified(self, modified):
        """
        Public method to set the window modification status.

        @param modified flag indicating the modification status
        @type bool
        """
        if "[*]" not in self.windowTitle():
            self.setWindowTitle(self.tr("[*] - {0}").format(self.tr("Mini Editor")))
        super().setWindowModified(modified)

    def __setCurrentFile(self, fileName):
        """
        Private method to register the file name of the current file.

        @param fileName name of the file to register
        @type str
        """
        self.__curFile = fileName

        if not self.__curFile:
            shownName = self.tr("Untitled")
        elif FileSystemUtilities.isDeviceFileName(self.__curFile):
            shownName = self.__curFile
        else:
            shownName = self.__strippedName(self.__curFile)

        self.setWindowTitle(
            self.tr("{0}[*] - {1}").format(shownName, self.tr("Mini Editor"))
        )

        self.__textEdit.setModified(False)
        self.setWindowModified(False)

        self.setLanguage(self.__bindName(self.__textEdit.text(0)))

        self.__loadEditorConfig()

    def getFileName(self):
        """
        Public method to return the name of the file being displayed.

        @return filename of the displayed file
        @rtype str
        """
        return self.__curFile

    def setFileName(self, name):
        """
        Public method to set the file name of the file being displayed.

        @param name name of the displayed file
        @type str
        """
        self.__setCurrentFile(name)

    def __strippedName(self, fullFileName):
        """
        Private method to return the filename part of the given path.

        @param fullFileName full pathname of the given file
        @type str
        @return filename part
        @rtype str
        """
        return pathlib.Path(fullFileName).name

    def __modificationChanged(self, m):
        """
        Private slot to handle the modificationChanged signal.

        @param m modification status
        @type bool
        """
        self.setWindowModified(m)
        self.__checkActions()

    def __cursorPositionChanged(self, line, pos):
        """
        Private slot to handle the cursorPositionChanged signal.

        @param line line number of the cursor
        @type int
        @param pos position in line of the cursor
        @type int
        """
        lang = self.getLanguage()
        self.__setSbFile(line + 1, pos, lang)

        if Preferences.getEditor("MarkOccurrencesEnabled"):
            self.__markOccurrencesTimer.stop()
            self.__markOccurrencesTimer.start()

        if self.__lastLine != line:
            self.cursorLineChanged.emit(line)
            self.__lastLine = line

    def __undo(self):
        """
        Private method to undo the last recorded change.
        """
        self.__textEdit.undo()
        self.__checkActions()

    def __redo(self):
        """
        Private method to redo the last recorded change.
        """
        self.__textEdit.redo()
        self.__checkActions()

    def __selectAll(self):
        """
        Private slot handling the select all context menu action.
        """
        self.__textEdit.selectAll(True)

    def __deselectAll(self):
        """
        Private slot handling the deselect all context menu action.
        """
        self.__textEdit.selectAll(False)

    def __setMargins(self):
        """
        Private method to configure the margins.
        """
        # set the settings for all margins
        self.__textEdit.setMarginsFont(Preferences.getEditorOtherFonts("MarginsFont"))
        self.__textEdit.setMarginsForegroundColor(
            Preferences.getEditorColour("MarginsForeground")
        )
        self.__textEdit.setMarginsBackgroundColor(
            Preferences.getEditorColour("MarginsBackground")
        )

        # set margin 0 settings
        linenoMargin = Preferences.getEditor("LinenoMargin")
        self.__textEdit.setMarginLineNumbers(0, linenoMargin)
        if linenoMargin:
            self.__resizeLinenoMargin()
        else:
            self.__textEdit.setMarginWidth(0, 16)

        # set margin 1 settings
        self.__textEdit.setMarginWidth(1, 0)

        # set margin 2 settings
        self.__textEdit.setMarginWidth(2, 16)
        if Preferences.getEditor("FoldingMargin"):
            folding = Preferences.getEditor("FoldingStyle")
            self.__textEdit.setFolding(folding)
            self.__textEdit.setFoldMarginColors(
                Preferences.getEditorColour("FoldmarginBackground"),
                Preferences.getEditorColour("FoldmarginBackground"),
            )
            self.__textEdit.setFoldMarkersColors(
                Preferences.getEditorColour("FoldMarkersForeground"),
                Preferences.getEditorColour("FoldMarkersBackground"),
            )
        else:
            self.__textEdit.setFolding(QsciScintilla.FoldStyle.NoFoldStyle.value)

    def __resizeLinenoMargin(self):
        """
        Private slot to resize the line numbers margin.
        """
        linenoMargin = Preferences.getEditor("LinenoMargin")
        if linenoMargin:
            self.__textEdit.setMarginWidth(
                0, "8" * (len(str(self.__textEdit.lines())) + 1)
            )

    def __setTabAndIndent(self):
        """
        Private method to set indentation size and style and tab width.
        """
        self.__textEdit.setTabWidth(self.__getEditorConfig("TabWidth"))
        self.__textEdit.setIndentationWidth(self.__getEditorConfig("IndentWidth"))
        if self.lexer_ and self.lexer_.alwaysKeepTabs():
            self.__textEdit.setIndentationsUseTabs(True)
        else:
            self.__textEdit.setIndentationsUseTabs(
                self.__getEditorConfig("TabForIndentation")
            )

    def __setTextDisplay(self):
        """
        Private method to configure the text display.
        """
        self.__setTabAndIndent()

        self.__textEdit.setTabIndents(Preferences.getEditor("TabIndents"))
        self.__textEdit.setBackspaceUnindents(Preferences.getEditor("TabIndents"))
        self.__textEdit.setIndentationGuides(Preferences.getEditor("IndentationGuides"))
        self.__textEdit.setIndentationGuidesBackgroundColor(
            Preferences.getEditorColour("IndentationGuidesBackground")
        )
        self.__textEdit.setIndentationGuidesForegroundColor(
            Preferences.getEditorColour("IndentationGuidesForeground")
        )
        if Preferences.getEditor("ShowWhitespace"):
            self.__textEdit.setWhitespaceVisibility(
                QsciScintilla.WhitespaceVisibility.WsVisible
            )
            self.__textEdit.setWhitespaceForegroundColor(
                Preferences.getEditorColour("WhitespaceForeground")
            )
            self.__textEdit.setWhitespaceBackgroundColor(
                Preferences.getEditorColour("WhitespaceBackground")
            )
            self.__textEdit.setWhitespaceSize(Preferences.getEditor("WhitespaceSize"))
        else:
            self.__textEdit.setWhitespaceVisibility(
                QsciScintilla.WhitespaceVisibility.WsInvisible
            )
        self.__textEdit.setEolVisibility(Preferences.getEditor("ShowEOL"))
        self.__textEdit.setAutoIndent(Preferences.getEditor("AutoIndentation"))
        if Preferences.getEditor("BraceHighlighting"):
            self.__textEdit.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        else:
            self.__textEdit.setBraceMatching(QsciScintilla.BraceMatch.NoBraceMatch)
        self.__textEdit.setMatchedBraceForegroundColor(
            Preferences.getEditorColour("MatchingBrace")
        )
        self.__textEdit.setMatchedBraceBackgroundColor(
            Preferences.getEditorColour("MatchingBraceBack")
        )
        self.__textEdit.setUnmatchedBraceForegroundColor(
            Preferences.getEditorColour("NonmatchingBrace")
        )
        self.__textEdit.setUnmatchedBraceBackgroundColor(
            Preferences.getEditorColour("NonmatchingBraceBack")
        )
        if Preferences.getEditor("CustomSelectionColours"):
            self.__textEdit.setSelectionBackgroundColor(
                Preferences.getEditorColour("SelectionBackground")
            )
        else:
            self.__textEdit.setSelectionBackgroundColor(
                QApplication.palette().color(QPalette.ColorRole.Highlight)
            )
        if Preferences.getEditor("ColourizeSelText"):
            self.__textEdit.resetSelectionForegroundColor()
        elif Preferences.getEditor("CustomSelectionColours"):
            self.__textEdit.setSelectionForegroundColor(
                Preferences.getEditorColour("SelectionForeground")
            )
        else:
            self.__textEdit.setSelectionForegroundColor(
                QApplication.palette().color(QPalette.ColorRole.HighlightedText)
            )
        self.__textEdit.setSelectionToEol(Preferences.getEditor("ExtendSelectionToEol"))
        self.__textEdit.setCaretForegroundColor(
            Preferences.getEditorColour("CaretForeground")
        )
        self.__textEdit.setCaretLineBackgroundColor(
            Preferences.getEditorColour("CaretLineBackground")
        )
        self.__textEdit.setCaretLineVisible(Preferences.getEditor("CaretLineVisible"))
        self.__textEdit.setCaretLineAlwaysVisible(
            Preferences.getEditor("CaretLineAlwaysVisible")
        )
        self.caretWidth = Preferences.getEditor("CaretWidth")
        self.__textEdit.setCaretWidth(self.caretWidth)
        self.caretLineFrameWidth = Preferences.getEditor("CaretLineFrameWidth")
        self.__textEdit.setCaretLineFrameWidth(self.caretLineFrameWidth)
        self.useMonospaced = Preferences.getEditor("UseMonospacedFont")
        self.__setMonospaced(self.useMonospaced)
        edgeMode = Preferences.getEditor("EdgeMode")
        edge = QsciScintilla.EdgeMode(edgeMode)
        self.__textEdit.setEdgeMode(edge)
        if edgeMode:
            self.__textEdit.setEdgeColumn(Preferences.getEditor("EdgeColumn"))
            self.__textEdit.setEdgeColor(Preferences.getEditorColour("Edge"))

        wrapVisualFlag = Preferences.getEditor("WrapVisualFlag")
        self.__textEdit.setWrapMode(Preferences.getEditor("WrapLongLinesMode"))
        self.__textEdit.setWrapVisualFlags(wrapVisualFlag, wrapVisualFlag)
        self.__textEdit.setWrapIndentMode(Preferences.getEditor("WrapIndentMode"))
        self.__textEdit.setWrapStartIndent(Preferences.getEditor("WrapStartIndent"))

        self.searchIndicator = QsciScintilla.INDIC_CONTAINER
        self.__textEdit.indicatorDefine(
            self.searchIndicator,
            QsciScintilla.INDIC_BOX,
            Preferences.getEditorColour("SearchMarkers"),
        )

        self.searchSelectionIndicator = QsciScintilla.INDIC_CONTAINER + 1
        self.__textEdit.indicatorDefine(
            self.searchSelectionIndicator,
            QsciScintilla.INDIC_FULLBOX,
            Preferences.getEditorColour("SearchSelectionMarker"),
        )

        self.__textEdit.setCursorFlashTime(QApplication.cursorFlashTime())

        if Preferences.getEditor("OverrideEditAreaColours"):
            self.__textEdit.setColor(Preferences.getEditorColour("EditAreaForeground"))
            self.__textEdit.setPaper(Preferences.getEditorColour("EditAreaBackground"))

        self.__textEdit.setVirtualSpaceOptions(
            Preferences.getEditor("VirtualSpaceOptions")
        )

        # to avoid errors due to line endings by pasting
        self.__textEdit.SendScintilla(QsciScintilla.SCI_SETPASTECONVERTENDINGS, True)

    def __setEolMode(self):
        """
        Private method to configure the eol mode of the editor.
        """
        eolMode = self.__getEditorConfig("EOLMode")
        self.__textEdit.setEolMode(eolMode)

    def __setMonospaced(self, on):
        """
        Private method to set/reset a monospaced font.

        @param on flag to indicate usage of a monospace font
        @type bool
        """
        if on:
            if not self.lexer_:
                f = Preferences.getEditorOtherFonts("MonospacedFont")
                self.__textEdit.monospacedStyles(f)
        else:
            if not self.lexer_:
                self.__textEdit.clearStyles()
                self.__setMargins()
            self.__textEdit.setFont(Preferences.getEditorOtherFonts("DefaultFont"))

        self.useMonospaced = on

    def __printFile(self):
        """
        Private slot to print the text.
        """
        from .Printer import Printer

        printer = Printer(mode=QPrinter.PrinterMode.HighResolution)
        sb = self.statusBar()
        printDialog = QPrintDialog(printer, self)
        if self.__textEdit.hasSelectedText():
            printDialog.setOption(
                QAbstractPrintDialog.PrintDialogOption.PrintSelection, True
            )
        if printDialog.exec() == QDialog.DialogCode.Accepted:
            sb.showMessage(self.tr("Printing..."))
            QApplication.processEvents()
            if self.__curFile:
                printer.setDocName(pathlib.Path(self.__curFile).name)
            else:
                printer.setDocName(self.tr("Untitled"))
            if printDialog.printRange() == QAbstractPrintDialog.PrintRange.Selection:
                # get the selection
                fromLine, _fromIndex, toLine, toIndex = self.__textEdit.getSelection()
                if toIndex == 0:
                    toLine -= 1
                # QScintilla seems to print one line more than told
                res = printer.printRange(self.__textEdit, fromLine, toLine - 1)
            else:
                res = printer.printRange(self.__textEdit)
            if res:
                sb.showMessage(self.tr("Printing completed"), 2000)
            else:
                sb.showMessage(self.tr("Error while printing"), 2000)
            QApplication.processEvents()
        else:
            sb.showMessage(self.tr("Printing aborted"), 2000)
            QApplication.processEvents()

    def __printPreviewFile(self):
        """
        Private slot to show a print preview of the text.
        """
        from .Printer import Printer

        printer = Printer(mode=QPrinter.PrinterMode.HighResolution)
        if self.__curFile:
            printer.setDocName(pathlib.Path(self.__curFile).name)
        else:
            printer.setDocName(self.tr("Untitled"))
        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(self.__printPreview)
        preview.exec()

    def __printPreview(self, printer):
        """
        Private slot to generate a print preview.

        @param printer reference to the printer object
        @type QScintilla.Printer.Printer
        """
        printer.printRange(self.__textEdit)

    #########################################################
    ## Methods needed by the context menu
    #########################################################

    def __contextMenuRequested(self, coord):
        """
        Private slot to show the context menu.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        self.contextMenu.popup(self.mapToGlobal(coord))

    def __initContextMenu(self):
        """
        Private method used to setup the context menu.
        """
        self.contextMenu = QMenu()

        self.languagesMenu = self.__initContextMenuLanguages()

        self.contextMenu.addAction(self.undoAct)
        self.contextMenu.addAction(self.redoAct)
        self.contextMenu.addSeparator()
        self.contextMenu.addAction(self.cutAct)
        self.contextMenu.addAction(self.copyAct)
        self.contextMenu.addAction(self.pasteAct)
        self.contextMenu.addSeparator()
        self.contextMenu.addAction(self.tr("Select all"), self.__selectAll)
        self.contextMenu.addAction(self.tr("Deselect all"), self.__deselectAll)
        self.contextMenu.addSeparator()
        self.languagesMenuAct = self.contextMenu.addMenu(self.languagesMenu)
        self.contextMenu.addSeparator()
        self.contextMenu.addAction(self.printPreviewAct)
        self.contextMenu.addAction(self.printAct)

    def __initContextMenuLanguages(self):
        """
        Private method used to setup the Languages context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        menu = QMenu(self.tr("Languages"))

        self.languagesActGrp = QActionGroup(self)
        self.noLanguageAct = menu.addAction(self.tr("No Language"))
        self.noLanguageAct.setCheckable(True)
        self.noLanguageAct.setData("None")
        self.languagesActGrp.addAction(self.noLanguageAct)
        menu.addSeparator()

        self.supportedLanguages = {}
        supportedLanguages = Lexers.getSupportedLanguages()
        for language in sorted(supportedLanguages):
            if language != "Guessed":
                self.supportedLanguages[language] = supportedLanguages[language][:2]
                act = menu.addAction(
                    EricPixmapCache.getIcon(supportedLanguages[language][2]),
                    self.supportedLanguages[language][0],
                )
                act.setCheckable(True)
                act.setData(language)
                self.supportedLanguages[language].append(act)
                self.languagesActGrp.addAction(act)

        menu.addSeparator()
        self.pygmentsAct = menu.addAction(self.tr("Guessed"))
        self.pygmentsAct.setCheckable(True)
        self.pygmentsAct.setData("Guessed")
        self.languagesActGrp.addAction(self.pygmentsAct)
        self.pygmentsSelAct = menu.addAction(self.tr("Alternatives"))
        self.pygmentsSelAct.setData("Alternatives")

        menu.triggered.connect(self.__languageMenuTriggered)
        menu.aboutToShow.connect(self.__showContextMenuLanguages)

        return menu

    def __showContextMenuLanguages(self):
        """
        Private slot handling the aboutToShow signal of the languages context
        menu.
        """
        if self.apiLanguage.startswith("Pygments|"):
            self.pygmentsSelAct.setText(
                self.tr("Alternatives ({0})").format(self.getLanguage(normalized=False))
            )
        else:
            self.pygmentsSelAct.setText(self.tr("Alternatives"))

    def __showLanguagesMenu(self, pos):
        """
        Private slot to show the Languages menu of the status bar.

        @param pos position the menu should be shown at
        @type QPoint
        """
        self.languagesMenu.exec(pos)

    def __selectPygmentsLexer(self):
        """
        Private method to select a specific pygments lexer.

        @return name of the selected pygments lexer
        @rtype str
        """
        from pygments.lexers import get_all_lexers  # __IGNORE_WARNING_I102__

        lexerList = sorted(lex[0] for lex in get_all_lexers())
        try:
            lexerSel = lexerList.index(
                self.getLanguage(normalized=False, forPygments=True)
            )
        except ValueError:
            lexerSel = 0
        lexerName, ok = QInputDialog.getItem(
            self,
            self.tr("Pygments Lexer"),
            self.tr("Select the Pygments lexer to apply."),
            lexerList,
            lexerSel,
            False,
        )
        if ok and lexerName:
            return lexerName
        else:
            return ""

    def __languageMenuTriggered(self, act):
        """
        Private method to handle the selection of a lexer language.

        @param act reference to the action that was triggered
        @type QAction
        """
        if act == self.noLanguageAct:
            self.__resetLanguage()
        elif act == self.pygmentsAct:
            self.setLanguage("dummy.pygments")
        elif act == self.pygmentsSelAct:
            language = self.__selectPygmentsLexer()
            if language:
                self.setLanguage("dummy.pygments", pyname=language)
        else:
            language = act.data()
            if language:
                self.setLanguage(self.supportedLanguages[language][1])

    def __resetLanguage(self):
        """
        Private method used to reset the language selection.
        """
        if self.lexer_ is not None and (
            self.lexer_.lexer() == "container" or self.lexer_.lexer() is None
        ):
            self.__textEdit.SCN_STYLENEEDED.disconnect(self.__styleNeeded)

        self.apiLanguage = ""
        self.lexer_ = None
        self.__textEdit.setLexer()
        self.__setMonospaced(self.useMonospaced)

        if Preferences.getEditor("OverrideEditAreaColours"):
            self.__textEdit.setColor(Preferences.getEditorColour("EditAreaForeground"))
            self.__textEdit.setPaper(Preferences.getEditorColour("EditAreaBackground"))

        self.languageChanged.emit(self.apiLanguage)

    def setLanguage(self, filename, initTextDisplay=True, pyname=""):
        """
        Public method to set a lexer language.

        @param filename filename used to determine the associated lexer
            language
        @type str
        @param initTextDisplay flag indicating an initialization of the text
            display is required as well
        @type bool
        @param pyname name of the pygments lexer to use
        @type str
        """
        self.__bindLexer(filename, pyname=pyname)
        self.__textEdit.recolor()
        self.__checkLanguage()

        # set the text display
        if initTextDisplay:
            self.__setTextDisplay()
            self.__setMargins()

        self.languageChanged.emit(self.apiLanguage)

    def getLanguage(self, normalized=True, forPygments=False):
        """
        Public method to retrieve the language of the editor.

        @param normalized flag indicating to normalize some Pygments
            lexer names
        @type bool
        @param forPygments flag indicating to normalize some lexer
            names for Pygments
        @type bool
        @return language of the editor
        @rtype str
        """
        if self.apiLanguage == "Guessed" or self.apiLanguage.startswith("Pygments|"):
            lang = self.lexer_.name()
            if normalized and lang in ("Python 2.x", "Python"):
                # adjust some Pygments lexer names
                lang = "Python3"

        else:
            lang = self.apiLanguage
            if forPygments and lang == "Python3":
                # adjust some names to Pygments lexer names
                lang = "Python"
        return lang

    def __checkLanguage(self):
        """
        Private method to check the selected language of the language submenu.
        """
        if self.apiLanguage == "":
            self.noLanguageAct.setChecked(True)
        elif self.apiLanguage == "Guessed":
            self.pygmentsAct.setChecked(True)
        elif self.apiLanguage.startswith("Pygments|"):
            act = self.languagesActGrp.checkedAction()
            if act:
                act.setChecked(False)
        else:
            self.supportedLanguages[self.apiLanguage][2].setChecked(True)

    def __bindLexer(self, filename, pyname=""):
        """
        Private slot to set the correct lexer depending on language.

        @param filename filename used to determine the associated lexer
            language
        @type str
        @param pyname name of the pygments lexer to use
        @type str
        """
        if self.lexer_ is not None and (
            self.lexer_.lexer() == "container" or self.lexer_.lexer() is None
        ):
            self.__textEdit.SCN_STYLENEEDED.disconnect(self.__styleNeeded)

        filename = os.path.basename(filename)
        language = Preferences.getEditorLexerAssoc(filename)
        if language == "Python":
            language = "Python3"
        if language.startswith("Pygments|"):
            pyname = language.split("|", 1)[1]
            language = ""

        if not self.filetype:
            if not language and pyname:
                self.filetype = pyname
            else:
                self.filetype = language

        self.lexer_ = Lexers.getLexer(language, self.__textEdit, pyname=pyname)
        if self.lexer_ is None:
            self.__textEdit.setLexer()
            self.apiLanguage = ""
            return

        if pyname:
            if pyname.startswith("Pygments|"):
                self.apiLanguage = pyname
            else:
                self.apiLanguage = "Pygments|{0}".format(pyname)
        else:
            # Change API language for lexer where QScintilla reports
            # an abbreviated name.
            self.apiLanguage = self.lexer_.language()
            if self.apiLanguage == "POV":
                self.apiLanguage = "Povray"
            elif self.apiLanguage == "PO":
                self.apiLanguage = "Gettext"
        self.__textEdit.setLexer(self.lexer_)
        if self.lexer_.lexer() == "container" or self.lexer_.lexer() is None:
            self.__textEdit.SCN_STYLENEEDED.connect(self.__styleNeeded)

        # get the font for style 0 and set it as the default font
        key = (
            "Scintilla/Guessed/style0/font"
            if pyname and pyname.startswith("Pygments|")
            else "Scintilla/{0}/style0/font".format(self.lexer_.language())
        )
        fdesc = Preferences.getSettings().value(key)
        if fdesc is not None:
            font = QFont([fdesc[0]], int(fdesc[1]))
            self.lexer_.setDefaultFont(font)
        self.lexer_.readSettings(Preferences.getSettings(), "Scintilla")
        if self.lexer_.hasSubstyles():
            self.lexer_.readSubstyles(self.__textEdit)

        # now set the lexer properties
        self.lexer_.initProperties()

        self.lexer_.setDefaultColor(self.lexer_.color(0))
        self.lexer_.setDefaultPaper(self.lexer_.paper(0))

    def __styleNeeded(self, position):
        """
        Private slot to handle the need for more styling.

        @param position end position, that needs styling
        @type int
        """
        self.lexer_.styleText(self.__textEdit.getEndStyled(), position)

    def __bindName(self, line0):
        """
        Private method to generate a dummy filename for binding a lexer.

        @param line0 first line of text to use in the generation process
        @type str
        @return dummy file name to be used for binding a lexer
        @rtype str
        """
        bindName = ""
        line0 = line0.lower()

        # check first line if it does not start with #!
        if line0.startswith(("<html", "<!doctype html", "<?php")):
            bindName = "dummy.html"
        elif line0.startswith(("<?xml", "<!doctype")):
            bindName = "dummy.xml"
        elif line0.startswith("index: "):
            bindName = "dummy.diff"
        elif line0.startswith("\\documentclass"):
            bindName = "dummy.tex"

        if not bindName and self.filetype:
            # check filetype
            supportedLanguages = Lexers.getSupportedLanguages()
            if self.filetype in supportedLanguages:
                bindName = supportedLanguages[self.filetype][1]
            elif self.filetype in ["Python", "Python3", "MicroPython"]:
                bindName = "dummy.py"

        if not bindName and line0.startswith("#!"):
            # #! marker detection
            if "python3" in line0 or "python" in line0:
                bindName = "dummy.py"
                self.filetype = "Python3"
            elif "/bash" in line0 or "/sh" in line0:
                bindName = "dummy.sh"
            elif "ruby" in line0:
                bindName = "dummy.rb"
                self.filetype = "Ruby"
            elif "perl" in line0:
                bindName = "dummy.pl"
            elif "lua" in line0:
                bindName = "dummy.lua"
            elif "dmd" in line0:
                bindName = "dummy.d"
                self.filetype = "D"

        if not bindName:
            # mode line detection: -*- mode: python -*-
            match = re.search(r"mode[:=]\s*([-\w_.]+)", line0)
            if match:
                mode = match.group(1).lower()
                if mode in ["python3", "pypy3"]:
                    bindName = "dummy.py"
                    self.filetype = "Python3"
                elif mode == "ruby":
                    bindName = "dummy.rb"
                    self.filetype = "Ruby"
                elif mode == "perl":
                    bindName = "dummy.pl"
                elif mode == "lua":
                    bindName = "dummy.lua"
                elif mode in ["dmd", "d"]:
                    bindName = "dummy.d"
                    self.filetype = "D"

        if not bindName:
            bindName = self.__curFile

        return bindName

    ##########################################################
    ## Methods needed for the search functionality
    ##########################################################

    def getSRHistory(self, key):
        """
        Public method to get the search or replace history list.

        @param key list to return (must be 'search' or 'replace')
        @type str
        @return the requested history list
        @rtype list of str
        """
        return self.srHistory[key][:]

    def textForFind(self):
        """
        Public method to determine the selection or the current word for the
        next find operation.

        @return selection or current word
        @rtype str
        """
        if self.__textEdit.hasSelectedText():
            text = self.__textEdit.selectedText()
            if "\r" in text or "\n" in text:
                # the selection contains at least a newline, it is
                # unlikely to be the expression to search for
                return ""

            return text

        # no selected text, determine the word at the current position
        return self.__getCurrentWord()

    def __getWord(self, line, index):
        """
        Private method to get the word at a position.

        @param line number of line to look at
        @type int
        @param index position to look at
        @type int
        @return the word at that position
        @rtype str
        """
        wc = self.__textEdit.wordCharacters()
        if wc is None:
            pattern = r"\b[\w_]+\b"
        else:
            wc = re.sub(r"\w", "", wc)
            pattern = r"\b[\w{0}]+\b".format(re.escape(wc))
        rx = (
            re.compile(pattern)
            if self.__textEdit.caseSensitive()
            else re.compile(pattern, re.IGNORECASE)
        )

        text = self.text(line)
        for match in rx.finditer(text):
            start, end = match.span()
            if start <= index <= end:
                return match.group()

        return ""

    def __getCurrentWord(self):
        """
        Private method to get the word at the current position.

        @return the word at that current position
        @rtype str
        """
        line, index = self.getCursorPosition()
        return self.__getWord(line, index)

    def showSearchWidget(self):
        """
        Public method to show the search widget.
        """
        self.__searchReplaceWidget.show(text=self.textForFind(), replaceMode=False)

    def __searchNext(self):
        """
        Private slot to handle the search next action.
        """
        self.__searchReplaceWidget.findNext()

    def __searchPrev(self):
        """
        Private slot to handle the search previous action.
        """
        self.__searchReplaceWidget.findPrev()

    def showReplaceWidget(self):
        """
        Public method to show the replace widget.
        """
        self.__searchReplaceWidget.show(text=self.textForFind(), replaceMode=True)

    def __searchClearMarkers(self):
        """
        Private method to clear the search markers of the active window.
        """
        self.clearSearchIndicators()

    def activeWindow(self):
        """
        Public method to fulfill the ViewManager interface.

        @return reference to the text edit component
        @rtype QsciScintillaCompat
        """
        return self.__textEdit

    def setSearchIndicator(self, startPos, indicLength):
        """
        Public method to set a search indicator for the given range.

        @param startPos start position of the indicator
        @type int
        @param indicLength length of the indicator
        @type int
        """
        self.__textEdit.setIndicatorRange(self.searchIndicator, startPos, indicLength)

    def clearSearchIndicators(self):
        """
        Public method to clear all search indicators.
        """
        self.__textEdit.clearAllIndicators(self.searchIndicator)
        self.__markedText = ""

    def highlightSearchSelection(self, startLine, startIndex, endLine, endIndex):
        """
        Public method to set a highlight for the selection at the start of a search.

        @param startLine line of the selection start
        @type int
        @param startIndex index of the selection start
        @type int
        @param endLine line of the selection end
        @type int
        @param endIndex index of the selection end
        @type int
        """
        self.__textEdit.setIndicator(
            self.searchSelectionIndicator, startLine, startIndex, endLine, endIndex
        )

    def getSearchSelectionHighlight(self):
        """
        Public method to get the start and end of the selection highlight.

        @return tuple containing the start line and index and the end line and index
        @rtype tuple of (int, int, int, int)
        """
        return self.__textEdit.getIndicator(self.searchSelectionIndicator)

    def clearSearchSelectionHighlight(self):
        """
        Public method to clear all highlights.
        """
        self.__textEdit.clearAllIndicators(self.searchSelectionIndicator)

    def __markOccurrences(self):
        """
        Private method to mark all occurrences of the current word.
        """
        word = self.__getCurrentWord()
        if not word:
            self.clearSearchIndicators()
            return

        if self.__markedText == word:
            return

        self.clearSearchIndicators()
        ok = self.__textEdit.findFirstTarget(
            word, False, self.__textEdit.caseSensitive(), True, 0, 0
        )
        while ok:
            tgtPos, tgtLen = self.__textEdit.getFoundTarget()
            self.setSearchIndicator(tgtPos, tgtLen)
            ok = self.__textEdit.findNextTarget()
        self.__markedText = word

    ##########################################################
    ## Methods exhibiting some QScintilla API methods
    ##########################################################

    def setText(self, txt, filetype=None):
        """
        Public method to set the text programatically.

        @param txt text to be set
        @type str
        @param filetype type of the source file
        @type str
        """
        self.__textEdit.setText(txt)

        if filetype is None:
            self.filetype = ""
        else:
            self.filetype = filetype

        eolMode = self.__getEditorConfig("EOLMode", nodefault=True)
        if eolMode is None:
            fileEol = self.__textEdit.detectEolString(txt)
            self.__textEdit.setEolModeByEolString(fileEol)
        else:
            self.__textEdit.convertEols(eolMode)

        self.__textEdit.setModified(False)
        self.setWindowModified(False)

    def gotoLine(self, line, pos=1):
        """
        Public slot to jump to the beginning of a line.

        @param line line number to go to
        @type int
        @param pos position in line to go to
        @type int
        """
        self.__textEdit.setCursorPosition(line - 1, pos - 1)
        self.__textEdit.ensureLineVisible(line - 1)
        self.__textEdit.setFirstVisibleLine(line - 1)
        self.__textEdit.ensureCursorVisible()

    def setModified(self, modified):
        """
        Public method to set the editor modification state.

        @param modified new editor modification state
        @type bool
        """
        self.__textEdit.setModified(modified)

    #######################################################################
    ## Methods implementing the interface to EditorConfig
    #######################################################################

    def __loadEditorConfig(self, fileName=""):
        """
        Private method to load the EditorConfig properties.

        @param fileName name of the file
        @type str
        """
        if not fileName:
            fileName = self.__curFile

        self.__editorConfig = self.__loadEditorConfigObject(fileName)

        if fileName:
            self.__setTabAndIndent()

    def __loadEditorConfigObject(self, fileName):
        """
        Private method to load the EditorConfig properties for the given
        file name.

        @param fileName name of the file
        @type str
        @return EditorConfig dictionary
        @rtype dict
        """
        editorConfig = {}

        if fileName and FileSystemUtilities.isPlainFileName(fileName):
            try:
                editorConfig = editorconfig.get_properties(fileName)
            except editorconfig.EditorConfigError:
                EricMessageBox.warning(
                    self,
                    self.tr("EditorConfig Properties"),
                    self.tr(
                        """<p>The EditorConfig properties for file"""
                        """ <b>{0}</b> could not be loaded.</p>"""
                    ).format(fileName),
                )

        return editorConfig

    def __getEditorConfig(self, option, nodefault=False, config=None):
        """
        Private method to get the requested option via EditorConfig.

        If there is no EditorConfig defined, the equivalent built-in option
        will be used (Preferences.getEditor(). The option must be given as the
        Preferences option key. The mapping to the EditorConfig option name
        will be done within this method.

        @param option Preferences option key
        @type str
        @param nodefault flag indicating to not get the default value from
            Preferences but return None instead
        @type bool
        @param config reference to an EditorConfig object or None
        @type dict
        @return value of requested setting or None if nothing was found and
            nodefault parameter was True
        @rtype Any
        """
        if config is None:
            config = self.__editorConfig

        if not config:
            if nodefault:
                return None
            else:
                value = self.__getOverrideValue(option)
                if value is None:
                    # no override
                    value = Preferences.getEditor(option)
                return value

        try:
            if option == "EOLMode":
                value = config["end_of_line"]
                if value == "lf":
                    value = QsciScintilla.EolMode.EolUnix
                elif value == "crlf":
                    value = QsciScintilla.EolMode.EolWindows
                elif value == "cr":
                    value = QsciScintilla.EolMode.EolMac
                else:
                    value = None
            elif option == "DefaultEncoding":
                value = config["charset"]
            elif option == "InsertFinalNewline":
                value = EricUtilities.toBool(config["insert_final_newline"])
            elif option == "StripTrailingWhitespace":
                value = EricUtilities.toBool(config["trim_trailing_whitespace"])
            elif option == "TabWidth":
                value = int(config["tab_width"])
            elif option == "IndentWidth":
                value = config["indent_size"]
                if value == "tab":
                    value = self.__getEditorConfig("TabWidth", config=config)
                else:
                    value = int(value)
            elif option == "TabForIndentation":
                value = config["indent_style"] == "tab"
        except KeyError:
            value = None

        if value is None and not nodefault:
            # use Preferences as default in case of error
            value = self.__getOverrideValue(option)
            if value is None:
                # no override
                value = Preferences.getEditor(option)

        return value

    def __getOverrideValue(self, option):
        """
        Private method to get an override value for the current file type.

        @param option Preferences option key
        @type str
        @return override value; None in case nothing is defined
        @rtype Any
        """
        if option in ("TabWidth", "IndentWidth"):
            overrides = Preferences.getEditor("TabIndentOverride")
            language = self.filetype or self.apiLanguage
            if language in overrides:
                if option == "TabWidth":
                    return overrides[self.filetype][0]
                elif option == "IndentWidth":
                    return overrides[self.filetype][1]

        return None

    #######################################################################
    ## Methods supporting the outline view below
    #######################################################################

    def __resetChangeTimer(self):
        """
        Private slot to reset the parse timer.
        """
        self.__changeTimer.stop()
        self.__changeTimer.start()

    def __editorChanged(self):
        """
        Private slot handling changes of the editor language or file name.
        """
        supported = self.__sourceOutline.isSupportedLanguage(self.getLanguage())

        self.__sourceOutline.setVisible(supported)

        line, pos = self.getCursorPosition()
        lang = self.getLanguage()
        self.__setSbFile(line + 1, pos, language=lang)

    #######################################################################
    ## Methods supporting zooming
    #######################################################################

    def __zoomIn(self):
        """
        Private method to handle the zoom in action.
        """
        self.zoomIn()
        self.sbZoom.setValue(self.getZoom())

    def __zoomOut(self):
        """
        Private method to handle the zoom out action.
        """
        self.zoomOut()
        self.sbZoom.setValue(self.getZoom())

    def __zoomReset(self):
        """
        Private method to reset the zoom factor.
        """
        self.__zoomTo(0)

    def __zoom(self):
        """
        Private method to handle the zoom action.
        """
        from eric7.QScintilla.ZoomDialog import ZoomDialog

        dlg = ZoomDialog(self.getZoom(), parent=self, modal=True)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            value = dlg.getZoomSize()
            self.__zoomTo(value)

    def __zoomTo(self, value):
        """
        Private slot to zoom to a given value.

        @param value zoom value to be set
        @type int
        """
        self.zoomTo(value)
        self.sbZoom.setValue(self.getZoom())

    #######################################################################
    ## Methods supporting MicroPython devices
    #######################################################################

    def __saveDeviceFile(self, saveas=False):
        """
        Private method to save the text to a file on the connected device.

        @param saveas flag indicating a 'save as' action (defaults to False)
        @type bool (optional)
        @return flag indicating success
        @rtype bool
        """
        with contextlib.suppress(KeyError):
            mpy = ericApp().getObject("MicroPython")
            filemanager = mpy.getFileManager()
            if saveas:
                fn, ok = QInputDialog.getText(
                    self,
                    self.tr("Save File to Device"),
                    self.tr("Enter the complete device file path:"),
                    QLineEdit.EchoMode.Normal,
                    self.__curFile,
                )
                if not ok or not fn:
                    # aborted
                    return False
            else:
                fn = self.__curFile
            # Convert the file name to device path separators ('/') and ensure,
            # intermediate directories exist (creating them if necessary)
            fn = fn.replace("\\", "/")
            if "/" in fn:
                dn = fn.rsplit("/", 1)[0]
                filemanager.makedirs(FileSystemUtilities.plainFileName(dn))
            success = filemanager.writeFile(
                FileSystemUtilities.plainFileName(fn), self.text()
            )
            if success:
                self.__setCurrentFile(fn)
            return success

        return False
