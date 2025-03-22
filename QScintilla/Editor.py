# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the editor component of the eric IDE.
"""

import bisect
import collections
import contextlib
import difflib
import enum
import os
import pathlib
import re

import editorconfig

from PyQt6.Qsci import QsciMacro, QsciScintilla, QsciStyledText
from PyQt6.QtCore import (
    QCryptographicHash,
    QDateTime,
    QDir,
    QEvent,
    QModelIndex,
    QPoint,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QAction,
    QActionGroup,
    QCursor,
    QFont,
    QKeyEvent,
    QPainter,
    QPalette,
    QPixmap,
)
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
    QLineEdit,
    QMenu,
    QToolTip,
)

from eric7 import EricUtilities, Preferences, Utilities
from eric7.CodeFormatting.BlackFormattingAction import BlackFormattingAction
from eric7.CodeFormatting.BlackUtilities import aboutBlack
from eric7.CodeFormatting.IsortFormattingAction import IsortFormattingAction
from eric7.CodeFormatting.IsortUtilities import aboutIsort
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricUtilities.EricCache import EricCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Globals import recentNameBreakpointConditions
from eric7.RemoteServerInterface import EricServerFileDialog
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities, PythonUtilities
from eric7.UI import PythonDisViewer
from eric7.Utilities import MouseUtilities

from . import Exporters, Lexers, TypingCompleters
from .EditorMarkerMap import EditorMarkerMap
from .QsciScintillaCompat import QsciScintillaCompat
from .SpellChecker import SpellChecker

EditorAutoCompletionListID = 1
TemplateCompletionListID = 2
ReferencesListID = 3

ReferenceItem = collections.namedtuple(  # noqa: U200
    "ReferenceItem", ["modulePath", "codeLine", "line", "column"]
)


class EditorIconId(enum.IntEnum):
    """
    Class defining the completion icon IDs.
    """

    Class = 1
    ClassProtected = 2
    ClassPrivate = 3
    Method = 4
    MethodProtected = 5
    MethodPrivate = 6
    Attribute = 7
    AttributeProtected = 8
    AttributePrivate = 9
    Enum = 10
    Keywords = 11
    Module = 12

    FromDocument = 99
    TemplateImage = 100


class EditorWarningKind(enum.Enum):
    """
    Class defining the kind of warnings supported by the Editor class.
    """

    Code = 1
    Python = 2
    Style = 3
    Info = 4
    Error = 5


class Editor(QsciScintillaCompat):
    """
    Class implementing the editor component of the eric IDE.

    @signal modificationStatusChanged(bool, QsciScintillaCompat) emitted when
        the modification status has changed
    @signal undoAvailable(bool) emitted to signal the undo availability
    @signal redoAvailable(bool) emitted to signal the redo availability
    @signal cursorChanged(str, int, int) emitted when the cursor position
        was changed
    @signal cursorLineChanged(int) emitted when the cursor line was changed
    @signal editorAboutToBeSaved(str) emitted before the editor is saved
    @signal editorSaved(str) emitted after the editor has been saved
    @signal editorRenamed(str) emitted after the editor got a new name
        (i.e. after a 'Save As')
    @signal captionChanged(str, QsciScintillaCompat) emitted when the caption
        is updated. Typically due to a readOnly attribute change.
    @signal breakpointToggled(QsciScintillaCompat) emitted when a breakpoint
        is toggled
    @signal bookmarkToggled(QsciScintillaCompat) emitted when a bookmark is
        toggled
    @signal syntaxerrorToggled(QsciScintillaCompat) emitted when a syntax error
        was discovered
    @signal autoCompletionAPIsAvailable(bool) emitted after the autocompletion
        function has been configured
    @signal coverageMarkersShown(bool) emitted after the coverage markers have
        been shown or cleared
    @signal taskMarkersUpdated(QsciScintillaCompat) emitted when the task
        markers were updated
    @signal changeMarkersUpdated(QsciScintillaCompat) emitted when the change
        markers were updated
    @signal showMenu(str, QMenu, QsciScintillaCompat) emitted when a menu is
        about to be shown. The name of the menu, a reference to the menu and
        a reference to the editor are given.
    @signal languageChanged(str) emitted when the editors language was set. The
        language is passed as a parameter.
    @signal eolChanged(str) emitted when the editors eol type was set. The eol
        string is passed as a parameter.
    @signal encodingChanged(str) emitted when the editors encoding was set. The
            encoding name is passed as a parameter.
    @signal spellLanguageChanged(str) emitted when the editor spell check
            language was set. The language is passed as a parameter.
    @signal lastEditPositionAvailable() emitted when a last edit position is
        available
    @signal refreshed() emitted to signal a refresh of the editor contents
    @signal settingsRead() emitted to signal, that the settings have been read
        and set
    @signal mouseDoubleClick(position, buttons) emitted to signal a mouse
        double click somewhere in the editor area
    """

    modificationStatusChanged = pyqtSignal(bool, QsciScintillaCompat)
    undoAvailable = pyqtSignal(bool)
    redoAvailable = pyqtSignal(bool)
    cursorChanged = pyqtSignal(str, int, int)
    cursorLineChanged = pyqtSignal(int)
    editorAboutToBeSaved = pyqtSignal(str)
    editorSaved = pyqtSignal(str)
    editorRenamed = pyqtSignal(str)
    captionChanged = pyqtSignal(str, QsciScintillaCompat)
    breakpointToggled = pyqtSignal(QsciScintillaCompat)
    bookmarkToggled = pyqtSignal(QsciScintillaCompat)
    syntaxerrorToggled = pyqtSignal(QsciScintillaCompat)
    autoCompletionAPIsAvailable = pyqtSignal(bool)
    coverageMarkersShown = pyqtSignal(bool)
    taskMarkersUpdated = pyqtSignal(QsciScintillaCompat)
    changeMarkersUpdated = pyqtSignal(QsciScintillaCompat)
    showMenu = pyqtSignal(str, QMenu, QsciScintillaCompat)
    languageChanged = pyqtSignal(str)
    eolChanged = pyqtSignal(str)
    encodingChanged = pyqtSignal(str)
    spellLanguageChanged = pyqtSignal(str)
    lastEditPositionAvailable = pyqtSignal()
    refreshed = pyqtSignal()
    settingsRead = pyqtSignal()
    mouseDoubleClick = pyqtSignal(QPoint, Qt.MouseButton)

    # Cooperation related definitions
    Separator = "@@@"

    StartEditToken = "START_EDIT"
    EndEditToken = "END_EDIT"
    CancelEditToken = "CANCEL_EDIT"
    RequestSyncToken = "REQUEST_SYNC"
    SyncToken = "SYNC"

    VcsConflictMarkerLineRegExpList = (
        r"""^<<<<<<< .*?$""",
        r"""^\|\|\|\|\|\|\| .*?$""",
        r"""^=======.*?$""",
        r"""^>>>>>>> .*?$""",
    )

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

    def __init__(
        self,
        dbs,
        fn="",
        vm=None,
        filetype="",
        editor=None,
        tv=None,
        assembly=None,
        parent=None,
    ):
        """
        Constructor

        @param dbs reference to the debug server object
        @type DebugServer
        @param fn name of the file to be opened. If it is None, a new (empty)
            editor is opened. (defaults to "")
        @type str (optional)
        @param vm reference to the view manager object (defaults to None)
        @type ViewManager (optional)
        @param filetype type of the source file (defaults to "")
        @type str (optional)
        @param editor reference to an Editor object, if this is a cloned view
            (defaults to None)
        @type Editor (optional)
        @param tv reference to the task viewer object (defaults to None)
        @type TaskViewer (optional)
        @param assembly reference to the editor assembly object (defaults to None)
        @type EditorAssembly (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        @exception OSError raised to indicate an issue accessing the file
        """
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_KeyCompression)
        self.setUtf8(True)

        self.enableMultiCursorSupport()

        self.__assembly = assembly
        self.dbs = dbs
        self.taskViewer = tv
        self.fileName = ""
        self.vm = vm
        self.filetype = filetype
        self.filetypeByFlag = False
        self.noName = ""
        self.project = ericApp().getObject("Project")
        self.setFileName(fn)

        self.__remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        # clear some variables
        self.lastHighlight = None  # remember the last highlighted line
        self.lastErrorMarker = None  # remember the last error line
        self.lastCurrMarker = None  # remember the last current line

        self.breaks = {}
        # key:   marker handle,
        # value: (lineno, condition, temporary,
        #         enabled, ignorecount)
        self.bookmarks = []
        # bookmarks are just a list of handles to the
        # bookmark markers
        self.syntaxerrors = {}
        # key:   marker handle
        # value: list of (error message, error index)
        self._warnings = {}
        # key:   marker handle
        # value: list of (warning message, warning type)
        self.notcoveredMarkers = []  # just a list of marker handles
        self.showingNotcoveredMarkers = False

        self.lexer_ = None
        self.apiLanguage = ""

        self.__loadEditorConfig()

        self.__lexerReset = False
        self.completer = None
        self.encoding = self.__getEditorConfig("DefaultEncoding")
        self.lastModified = 0
        self.line = -1
        self.inReopenPrompt = False
        # true if the prompt to reload a changed source is present
        self.inFileRenamed = False
        # true if we are propagating a rename action
        self.inLanguageChanged = False
        # true if we are propagating a language change
        self.inEolChanged = False
        # true if we are propagating an eol change
        self.inEncodingChanged = False
        # true if we are propagating an encoding change
        self.inDragDrop = False
        # true if we are in drop mode
        self.inLinesChanged = False
        # true if we are propagating a lines changed event
        self.__hasTaskMarkers = False
        # no task markers present
        self.__checkExternalModification = True
        # check and reload or warn when modified externally

        self.macros = {}  # list of defined macros
        self.curMacro = None
        self.recording = False

        self.acAPI = False

        self.__lastEditPosition = None
        self.__annotationLines = 0

        self.__docstringGenerator = None

        # list of clones
        self.__clones = []

        # clear QScintilla defined keyboard commands
        # we do our own handling through the view manager
        self.clearAlternateKeys()
        self.clearKeys()

        self.__markerMap = EditorMarkerMap(self)

        # initialize the mark occurrences timer
        self.__markOccurrencesTimer = QTimer(self)
        self.__markOccurrencesTimer.setSingleShot(True)
        self.__markOccurrencesTimer.setInterval(
            Preferences.getEditor("MarkOccurrencesTimeout")
        )
        self.__markOccurrencesTimer.timeout.connect(self.__markOccurrences)
        self.__markedText = ""
        self.__searchIndicatorLines = []

        # set the autosave attributes
        self.__autosaveInterval = Preferences.getEditor("AutosaveIntervalSeconds")
        self.__autosaveManuallyDisabled = False

        # initialize the autosave timer
        self.__autosaveTimer = QTimer(self)
        self.__autosaveTimer.setObjectName("AutosaveTimer")
        self.__autosaveTimer.setSingleShot(True)
        self.__autosaveTimer.timeout.connect(self.__autosave)

        # initialize some spellchecking stuff
        self.spell = None
        self.lastLine = 0
        self.lastIndex = 0
        self.__inSpellLanguageChanged = False

        # initialize some cooperation stuff
        self.__isSyncing = False
        self.__receivedWhileSyncing = []
        self.__savedText = ""
        self.__inSharedEdit = False
        self.__isShared = False
        self.__inRemoteSharedEdit = False

        # connect signals before loading the text
        self.modificationChanged.connect(self.__modificationChanged)
        self.cursorPositionChanged.connect(self.__cursorPositionChanged)
        self.modificationAttempted.connect(self.__modificationReadOnly)

        # define the margins markers
        self.__changeMarkerSaved = self.markerDefine(
            self.__createChangeMarkerPixmap("OnlineChangeTraceMarkerSaved")
        )
        self.__changeMarkerUnsaved = self.markerDefine(
            self.__createChangeMarkerPixmap("OnlineChangeTraceMarkerUnsaved")
        )
        self.breakpoint = self.markerDefine(EricPixmapCache.getPixmap("break"))
        self.cbreakpoint = self.markerDefine(EricPixmapCache.getPixmap("cBreak"))
        self.tbreakpoint = self.markerDefine(EricPixmapCache.getPixmap("tBreak"))
        self.tcbreakpoint = self.markerDefine(EricPixmapCache.getPixmap("tCBreak"))
        self.dbreakpoint = self.markerDefine(EricPixmapCache.getPixmap("breakDisabled"))
        self.bookmark = self.markerDefine(EricPixmapCache.getPixmap("bookmark16"))
        self.syntaxerror = self.markerDefine(EricPixmapCache.getPixmap("syntaxError"))
        self.notcovered = self.markerDefine(EricPixmapCache.getPixmap("notcovered"))
        self.taskmarker = self.markerDefine(EricPixmapCache.getPixmap("task"))
        self.warning = self.markerDefine(EricPixmapCache.getPixmap("warning"))

        # define the line markers
        if Preferences.getEditor("LineMarkersBackground"):
            self.currentline = self.markerDefine(QsciScintilla.MarkerSymbol.Background)
            self.errorline = self.markerDefine(QsciScintilla.MarkerSymbol.Background)
            self.__setLineMarkerColours()
        else:
            self.currentline = self.markerDefine(
                EricPixmapCache.getPixmap("currentLineMarker")
            )
            self.errorline = self.markerDefine(
                EricPixmapCache.getPixmap("errorLineMarker")
            )

        self.breakpointMask = (
            (1 << self.breakpoint)
            | (1 << self.cbreakpoint)
            | (1 << self.tbreakpoint)
            | (1 << self.tcbreakpoint)
            | (1 << self.dbreakpoint)
        )

        self.changeMarkersMask = (1 << self.__changeMarkerSaved) | (
            1 << self.__changeMarkerUnsaved
        )

        # set the eol mode
        self.__setEolMode()

        # set the text display
        self.__setTextDisplay()

        # initialize the online syntax check timer
        try:
            self.syntaxCheckService = ericApp().getObject("SyntaxCheckService")
            self.syntaxCheckService.syntaxChecked.connect(
                self.__processSyntaxCheckResult
            )
            self.syntaxCheckService.error.connect(self.__processSyntaxCheckError)
            self.__initOnlineSyntaxCheck()
        except KeyError:
            self.syntaxCheckService = None

        self.isResourcesFile = False
        if editor is None:
            if self.fileName:
                if not Utilities.MimeTypes.isTextFile(self.fileName):
                    raise OSError()

                if FileSystemUtilities.isRemoteFileName(self.fileName):
                    fileIsRemote = True
                    fileExists = self.__remotefsInterface.exists(self.fileName)
                    try:
                        fileSizeKB = (
                            self.__remotefsInterface.stat(self.fileName, ["st_size"])[
                                "st_size"
                            ]
                            // 1024
                        )
                    except KeyError:
                        # should not happen, but play it save
                        fileSizeKB = 0
                elif FileSystemUtilities.isDeviceFileName(self.fileName):
                    fileIsRemote = False
                    fileExists = False
                    fileSizeKB = 0
                else:
                    fileIsRemote = False
                    fileExists = pathlib.Path(self.fileName).exists()
                    fileSizeKB = pathlib.Path(self.fileName).stat().st_size // 1024
                if fileExists:
                    if fileSizeKB > Preferences.getEditor("RejectFilesize"):
                        EricMessageBox.warning(
                            None,
                            self.tr("Open File"),
                            self.tr(
                                "<p>The size of the file <b>{0}</b> is <b>{1} KB</b>"
                                " and exceeds the configured limit of <b>{2} KB</b>."
                                " It will not be opened!</p>"
                            ).format(
                                self.fileName,
                                fileSizeKB,
                                Preferences.getEditor("RejectFilesize"),
                            ),
                        )
                        raise OSError()
                    elif fileSizeKB > Preferences.getEditor("WarnFilesize"):
                        res = EricMessageBox.yesNo(
                            None,
                            self.tr("Open File"),
                            self.tr(
                                """<p>The size of the file <b>{0}</b>"""
                                """ is <b>{1} KB</b>."""
                                """ Do you really want to load it?</p>"""
                            ).format(self.fileName, fileSizeKB),
                            icon=EricMessageBox.Warning,
                        )
                        if not res:
                            raise OSError()

                    self.readFile(self.fileName, createIt=True, isRemote=fileIsRemote)

                self.__bindLexer(self.fileName)
                self.__bindCompleter(self.fileName)
                self.checkSyntax()
                self.isResourcesFile = self.fileName.endswith(".qrc")

                self.__convertTabs()

                self.recolor()
        else:
            # clone the given editor
            self.setDocument(editor.document())
            self.breaks = editor.breaks
            self.bookmarks = editor.bookmarks
            self.syntaxerrors = editor.syntaxerrors
            self.notcoveredMarkers = editor.notcoveredMarkers
            self.showingNotcoveredMarkers = editor.showingNotcoveredMarkers
            self.isResourcesFile = editor.isResourcesFile
            self.lastModified = editor.lastModified

            self.addClone(editor)
            editor.addClone(self)

        # configure the margins
        self.__setMarginsDisplay()
        self.linesChanged.connect(self.__resizeLinenoMargin)

        self.marginClicked.connect(self.__marginClicked)

        self.gotoLine(1)

        # connect the mouse hover signals
        # mouse hover for the editor margins
        self.SCN_DWELLSTART.connect(self.__marginHoverStart)
        self.SCN_DWELLEND.connect(self.__marginHoverEnd)

        # mouse hover help for the editor text
        self.SCN_DWELLSTART.connect(self.__showMouseHoverHelp)
        self.SCN_DWELLEND.connect(self.__cancelMouseHoverHelp)
        self.__mouseHoverHelp = None
        self.__showingMouseHoverHelp = False

        # set the text display again
        self.__setTextDisplay()

        # set the auto-completion function
        self.__acContext = True
        self.__acText = ""
        self.__acCompletions = set()
        self.__acCompletionsFinished = 0
        self.__acCache = EricCache(
            size=Preferences.getEditor("AutoCompletionCacheSize")
        )
        self.__acCache.setMaximumCacheTime(
            Preferences.getEditor("AutoCompletionCacheTime")
        )
        self.__acCacheEnabled = Preferences.getEditor("AutoCompletionCacheEnabled")
        self.__acTimer = QTimer(self)
        self.__acTimer.setSingleShot(True)
        self.__acTimer.setInterval(Preferences.getEditor("AutoCompletionTimeout"))
        self.__acTimer.timeout.connect(self.__autoComplete)

        self.__acWatchdog = QTimer(self)
        self.__acWatchdog.setSingleShot(True)
        self.__acWatchdog.setInterval(
            Preferences.getEditor("AutoCompletionWatchdogTime")
        )
        self.__acWatchdog.timeout.connect(self.autoCompleteQScintilla)

        self.userListActivated.connect(self.__completionListSelected)
        self.SCN_CHARADDED.connect(self.__charAdded)
        self.SCN_AUTOCCANCELLED.connect(self.__autocompletionCancelled)

        self.__completionListHookFunctions = {}
        self.__completionListAsyncHookFunctions = {}
        self.__setAutoCompletion()

        # set the call-tips function
        self.__ctHookFunctions = {}
        self.__setCallTips()

        # set the mouse click handlers (fired on mouse release)
        self.__mouseClickHandlers = {}
        # dictionary with tuple of keyboard modifier and mouse button as key
        # and tuple of plug-in name and function as value

        sh = self.sizeHint()
        if sh.height() < 300:
            sh.setHeight(300)
        self.resize(sh)

        # Make sure tabbing through a QWorkspace works.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.__updateReadOnly(True)

        self.setWhatsThis(
            self.tr(
                """<b>A Source Editor Window</b>"""
                """<p>This window is used to display and edit a source file."""
                """  You can open as many of these as you like. The name of the"""
                """ file is displayed in the window's titlebar.</p>"""
                """<p>In order to set breakpoints just click in the space"""
                """ between the line numbers and the fold markers. Via the"""
                """ context menu of the margins they may be edited.</p>"""
                """<p>In order to set bookmarks just Shift click in the space"""
                """ between the line numbers and the fold markers.</p>"""
                """<p>These actions can be reversed via the context menu.</p>"""
                """<p>Ctrl clicking on a syntax error marker shows some info"""
                """ about this error.</p>"""
            )
        )

        # Set the editors size, if it is too big for the view manager.
        if self.vm is not None:
            req = self.size()
            bnd = req.boundedTo(self.vm.size())

            if bnd.width() < req.width() or bnd.height() < req.height():
                self.resize(bnd)

        # code coverage related attributes
        self.__coverageFile = ""

        self.__initContextMenu()
        self.__initContextMenuMargins()
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__showContextMenu)

        self.__checkEol()
        if editor is None:
            self.__checkLanguage()
            self.__checkEncoding()
            self.__checkSpellLanguage()
        else:
            # it's a clone
            self.__languageChanged(editor.apiLanguage, propagate=False)
            self.__encodingChanged(editor.encoding, propagate=False)
            self.__spellLanguageChanged(editor.getSpellingLanguage(), propagate=False)
            # link the warnings to the original editor
            self._warnings = editor._warnings

        self.setAcceptDrops(True)

        # breakpoint handling
        self.breakpointModel = self.dbs.getBreakPointModel()
        self.__restoreBreakpoints()
        self.breakpointModel.rowsAboutToBeRemoved.connect(self.__deleteBreakPoints)
        self.breakpointModel.dataAboutToBeChanged.connect(
            self.__breakPointDataAboutToBeChanged
        )
        self.breakpointModel.dataChanged.connect(self.__changeBreakPoints)
        self.breakpointModel.rowsInserted.connect(self.__addBreakPoints)
        self.SCN_MODIFIED.connect(self.__modified)

        # establish connection to some ViewManager action groups
        self.addActions(self.vm.editorActGrp.actions())
        self.addActions(self.vm.editActGrp.actions())
        self.addActions(self.vm.copyActGrp.actions())
        self.addActions(self.vm.viewActGrp.actions())

        # register images to be shown in autocompletion lists
        self.__registerImages()

        # connect signals after loading the text
        self.textChanged.connect(self.__textChanged)

        # initialize the online change trace timer
        self.__initOnlineChangeTrace()

        if (
            self.fileName
            and self.project.isOpen()
            and self.project.isProjectCategory(self.fileName, "SOURCES")
        ):
            self.project.projectPropertiesChanged.connect(
                self.__projectPropertiesChanged
            )

        self.grabGesture(Qt.GestureType.PinchGesture)

        self.SCN_ZOOM.connect(self.__markerMap.update)
        self.__markerMap.update()

    def getAssembly(self):
        """
        Public method to get a reference to the editor assembly object.

        @return reference to the editor assembly object
        @rtype EditorAssembly
        """
        return self.__assembly

    def setFileName(self, name):
        """
        Public method to set the file name of the current file.

        @param name name of the current file
        @type str
        """
        renamed = self.fileName != name

        oldFileName = self.fileName
        self.fileName = name

        if renamed:
            self.vm.setEditorName(self, self.fileName)
            self.vm.removeWatchedFilePath(oldFileName)
            self.vm.addWatchedFilePath(self.fileName)

        if self.fileName:
            self.__fileNameExtension = os.path.splitext(self.fileName)[1][1:].lower()
        else:
            self.__fileNameExtension = ""

    def __registerImages(self):
        """
        Private method to register images for autocompletion lists.
        """
        # finale size of the completion images
        imageSize = QSize(22, 22)

        self.registerImage(
            EditorIconId.Class,
            EricPixmapCache.getPixmap("class", imageSize),
        )
        self.registerImage(
            EditorIconId.ClassProtected,
            EricPixmapCache.getPixmap("class_protected", imageSize),
        )
        self.registerImage(
            EditorIconId.ClassPrivate,
            EricPixmapCache.getPixmap("class_private", imageSize),
        )
        self.registerImage(
            EditorIconId.Method,
            EricPixmapCache.getPixmap("method", imageSize),
        )
        self.registerImage(
            EditorIconId.MethodProtected,
            EricPixmapCache.getPixmap("method_protected", imageSize),
        )
        self.registerImage(
            EditorIconId.MethodPrivate,
            EricPixmapCache.getPixmap("method_private", imageSize),
        )
        self.registerImage(
            EditorIconId.Attribute,
            EricPixmapCache.getPixmap("attribute", imageSize),
        )
        self.registerImage(
            EditorIconId.AttributeProtected,
            EricPixmapCache.getPixmap("attribute_protected", imageSize),
        )
        self.registerImage(
            EditorIconId.AttributePrivate,
            EricPixmapCache.getPixmap("attribute_private", imageSize),
        )
        self.registerImage(
            EditorIconId.Enum,
            EricPixmapCache.getPixmap("enum", imageSize),
        )
        self.registerImage(
            EditorIconId.Keywords,
            EricPixmapCache.getPixmap("keywords", imageSize),
        )
        self.registerImage(
            EditorIconId.Module,
            EricPixmapCache.getPixmap("module", imageSize),
        )

        self.registerImage(
            EditorIconId.FromDocument,
            EricPixmapCache.getPixmap("editor", imageSize),
        )

        self.registerImage(
            EditorIconId.TemplateImage,
            EricPixmapCache.getPixmap("templateViewer", imageSize),
        )

    def addClone(self, editor):
        """
        Public method to add a clone to our list.

        @param editor reference to the cloned editor
        @type Editor
        """
        self.__clones.append(editor)

        editor.editorRenamed.connect(self.fileRenamed)
        editor.languageChanged.connect(self.languageChanged)
        editor.eolChanged.connect(self.__eolChanged)
        editor.encodingChanged.connect(self.__encodingChanged)
        editor.spellLanguageChanged.connect(self.__spellLanguageChanged)

    def removeClone(self, editor):
        """
        Public method to remove a clone from our list.

        @param editor reference to the cloned editor
        @type Editor
        """
        if editor in self.__clones:
            editor.editorRenamed.disconnect(self.fileRenamed)
            editor.languageChanged.disconnect(self.languageChanged)
            editor.eolChanged.disconnect(self.__eolChanged)
            editor.encodingChanged.disconnect(self.__encodingChanged)
            editor.spellLanguageChanged.disconnect(self.__spellLanguageChanged)
            self.__clones.remove(editor)

    def isClone(self, editor):
        """
        Public method to test, if the given editor is a clone.

        @param editor reference to the cloned editor
        @type Editor
        @return flag indicating a clone
        @rtype bool
        """
        return editor in self.__clones

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
            if (
                "python3" in line0
                or "python" in line0
                or "pypy3" in line0
                or "pypy" in line0
            ):
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
            bindName = self.fileName

        return bindName

    def getMenu(self, menuName):
        """
        Public method to get a reference to the main context menu or a submenu.

        @param menuName name of the menu
        @type str
        @return reference to the requested menu or None
        @rtype QMenu
        """
        try:
            return self.__menus[menuName]
        except KeyError:
            return None

    def hasMiniMenu(self):
        """
        Public method to check the miniMenu flag.

        @return flag indicating a minimized context menu
        @rtype bool
        """
        return self.miniMenu

    def __initContextMenu(self):
        """
        Private method used to setup the context menu.
        """
        self.miniMenu = Preferences.getEditor("MiniContextMenu")

        self.menuActs = {}
        self.menu = QMenu()
        self.__menus = {
            "Main": self.menu,
        }

        self.languagesMenu = self.__initContextMenuLanguages()
        self.__menus["Languages"] = self.languagesMenu
        if self.isResourcesFile:
            self.resourcesMenu = self.__initContextMenuResources()
            self.__menus["Resources"] = self.resourcesMenu
        else:
            self.checksMenu = self.__initContextMenuChecks()
            self.menuShow = self.__initContextMenuShow()
            self.graphicsMenu = self.__initContextMenuGraphics()
            self.autocompletionMenu = self.__initContextMenuAutocompletion()
            self.codeFormattingMenu = self.__initContextMenuFormatting()
            self.__menus["Checks"] = self.checksMenu
            self.__menus["Show"] = self.menuShow
            self.__menus["Graphics"] = self.graphicsMenu
            self.__menus["Autocompletion"] = self.autocompletionMenu
            self.__menus["Formatting"] = self.codeFormattingMenu
        self.toolsMenu = self.__initContextMenuTools()
        self.__menus["Tools"] = self.toolsMenu
        self.eolMenu = self.__initContextMenuEol()
        self.__menus["Eol"] = self.eolMenu
        self.encodingsMenu = self.__initContextMenuEncodings()
        self.__menus["Encodings"] = self.encodingsMenu
        self.spellCheckMenu = self.__initContextMenuSpellCheck()
        self.__menus["SpellCheck"] = self.spellCheckMenu

        self.menuActs["Undo"] = self.menu.addAction(
            EricPixmapCache.getIcon("editUndo"), self.tr("Undo"), self.undo
        )
        self.menuActs["Redo"] = self.menu.addAction(
            EricPixmapCache.getIcon("editRedo"), self.tr("Redo"), self.redo
        )
        self.menuActs["Revert"] = self.menu.addAction(
            self.tr("Revert to last saved state"), self.revertToUnmodified
        )
        self.menu.addSeparator()
        self.menuActs["Cut"] = self.menu.addAction(
            EricPixmapCache.getIcon("editCut"), self.tr("Cut"), self.cut
        )
        self.menuActs["Copy"] = self.menu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy"), self.copy
        )
        self.menuActs["Paste"] = self.menu.addAction(
            EricPixmapCache.getIcon("editPaste"), self.tr("Paste"), self.paste
        )
        if not self.miniMenu:
            self.menu.addSeparator()
            self.menu.addAction(
                EricPixmapCache.getIcon("editIndent"),
                self.tr("Indent"),
                self.indentLineOrSelection,
            )
            self.menu.addAction(
                EricPixmapCache.getIcon("editUnindent"),
                self.tr("Unindent"),
                self.unindentLineOrSelection,
            )
            self.menuActs["Comment"] = self.menu.addAction(
                EricPixmapCache.getIcon("editComment"),
                self.tr("Comment"),
                self.commentLineOrSelection,
            )
            self.menuActs["Uncomment"] = self.menu.addAction(
                EricPixmapCache.getIcon("editUncomment"),
                self.tr("Uncomment"),
                self.uncommentLineOrSelection,
            )
            self.menu.addSeparator()
            self.menuActs["Docstring"] = self.menu.addAction(
                self.tr("Generate Docstring"), self.__insertDocstring
            )
            self.menu.addSeparator()
            self.menu.addAction(self.tr("Select to brace"), self.selectToMatchingBrace)
            self.menu.addAction(self.tr("Select all"), self.__selectAll)
            self.menu.addAction(self.tr("Deselect all"), self.__deselectAll)
            self.menuActs["ExecuteSelection"] = self.menu.addAction(
                self.tr("Execute Selection In Console"), self.__executeSelection
            )
        else:
            self.menuActs["ExecuteSelection"] = None
        self.menu.addSeparator()
        self.menu.addMenu(self.spellCheckMenu)
        self.menu.addSeparator()
        self.menuActs["Languages"] = self.menu.addMenu(self.languagesMenu)
        self.menuActs["Encodings"] = self.menu.addMenu(self.encodingsMenu)
        self.menuActs["Eol"] = self.menu.addMenu(self.eolMenu)
        self.menu.addSeparator()
        self.menuActs["MonospacedFont"] = self.menu.addAction(
            self.tr("Use Monospaced Font"), self.handleMonospacedEnable
        )
        self.menuActs["MonospacedFont"].setCheckable(True)
        self.menuActs["MonospacedFont"].setChecked(self.useMonospaced)
        self.menuActs["AutosaveEnable"] = self.menu.addAction(
            self.tr("Autosave enabled"), self.__autosaveEnable
        )
        self.menuActs["AutosaveEnable"].setCheckable(True)
        self.menuActs["AutosaveEnable"].setChecked(self.__autosaveInterval > 0)
        self.menuActs["TypingAidsEnabled"] = self.menu.addAction(
            self.tr("Typing aids enabled"), self.__toggleTypingAids
        )
        self.menuActs["TypingAidsEnabled"].setCheckable(True)
        self.menuActs["TypingAidsEnabled"].setEnabled(self.completer is not None)
        self.menuActs["TypingAidsEnabled"].setChecked(
            self.completer is not None and self.completer.isEnabled()
        )
        self.menuActs["AutoCompletionEnable"] = self.menu.addAction(
            self.tr("Automatic Completion enabled"), self.__toggleAutoCompletionEnable
        )
        self.menuActs["AutoCompletionEnable"].setCheckable(True)
        self.menuActs["AutoCompletionEnable"].setChecked(
            self.autoCompletionThreshold() != -1
        )
        if not self.isResourcesFile:
            self.menu.addMenu(self.autocompletionMenu)
            self.menuActs["calltip"] = self.menu.addAction(
                self.tr("Calltip"), self.callTip
            )
            self.menuActs["codeInfo"] = self.menu.addAction(
                self.tr("Code Info"), self.__showCodeInfo
            )
        self.menu.addSeparator()
        if self.isResourcesFile:
            self.menu.addMenu(self.resourcesMenu)
        else:
            self.menuActs["Check"] = self.menu.addMenu(self.checksMenu)
            self.menuActs["Formatting"] = self.menu.addMenu(self.codeFormattingMenu)
            self.menuActs["Show"] = self.menu.addMenu(self.menuShow)
            self.menuActs["Diagrams"] = self.menu.addMenu(self.graphicsMenu)
        self.menu.addSeparator()
        self.menuActs["Tools"] = self.menu.addMenu(self.toolsMenu)
        self.menu.addSeparator()
        self.menu.addAction(
            EricPixmapCache.getIcon("documentNewView"),
            self.tr("New Document View"),
            self.__newView,
        )
        self.menuActs["NewSplit"] = self.menu.addAction(
            EricPixmapCache.getIcon("splitVertical"),
            self.tr("New Document View (with new split)"),
            self.__newViewNewSplit,
        )
        self.menuActs["NewSplit"].setEnabled(self.vm.canSplit())
        self.menu.addSeparator()
        self.reopenEncodingMenu = self.__initContextMenuReopenWithEncoding()
        self.menuActs["Reopen"] = self.menu.addMenu(self.reopenEncodingMenu)
        self.menuActs["Reload"] = self.menu.addAction(
            EricPixmapCache.getIcon("reload"), self.tr("Reload"), self.reload
        )
        self.menuActs["Save"] = self.menu.addAction(
            EricPixmapCache.getIcon("fileSave"), self.tr("Save"), self.__contextSave
        )
        self.menu.addAction(
            EricPixmapCache.getIcon("fileSaveAs"),
            self.tr("Save As..."),
            self.__contextSaveAs,
        )
        self.menuActs["SaveAsRemote"] = self.menu.addAction(
            EricPixmapCache.getIcon("fileSaveAsRemote"),
            self.tr("Save as (Remote)..."),
            self.__contextSaveAsRemote,
        )
        self.menu.addAction(
            EricPixmapCache.getIcon("fileSaveCopy"),
            self.tr("Save Copy..."),
            self.__contextSaveCopy,
        )

        self.menu.aboutToShow.connect(self.__aboutToShowContextMenu)

        self.spellingMenu = QMenu()
        self.__menus["Spelling"] = self.spellingMenu

        self.spellingMenu.aboutToShow.connect(self.__showContextMenuSpelling)
        self.spellingMenu.triggered.connect(self.__contextMenuSpellingTriggered)

    def __initContextMenuAutocompletion(self):
        """
        Private method used to setup the Checks context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        menu = QMenu(self.tr("Complete"))

        self.menuActs["acDynamic"] = menu.addAction(
            self.tr("Complete"), self.autoComplete
        )
        menu.addSeparator()
        self.menuActs["acClearCache"] = menu.addAction(
            self.tr("Clear Completions Cache"), self.__clearCompletionsCache
        )
        menu.addSeparator()
        menu.addAction(self.tr("Complete from Document"), self.autoCompleteFromDocument)
        self.menuActs["acAPI"] = menu.addAction(
            self.tr("Complete from APIs"), self.autoCompleteFromAPIs
        )
        self.menuActs["acAPIDocument"] = menu.addAction(
            self.tr("Complete from Document and APIs"), self.autoCompleteFromAll
        )

        menu.aboutToShow.connect(self.__showContextMenuAutocompletion)

        return menu

    def __initContextMenuChecks(self):
        """
        Private method used to setup the Checks context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        menu = QMenu(self.tr("Check"))
        menu.aboutToShow.connect(self.__showContextMenuChecks)
        return menu

    def __initContextMenuFormatting(self):
        """
        Private method used to setup the Code Formatting context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        menu = QMenu(self.tr("Code Formatting"))

        #######################################################################
        ## Black related entries
        #######################################################################

        act = menu.addAction(self.tr("Black"), aboutBlack)
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        menu.addAction(
            self.tr("Format Code"),
            lambda: self.__performFormatWithBlack(BlackFormattingAction.Format),
        )
        menu.addAction(
            self.tr("Check Formatting"),
            lambda: self.__performFormatWithBlack(BlackFormattingAction.Check),
        )
        menu.addAction(
            self.tr("Formatting Diff"),
            lambda: self.__performFormatWithBlack(BlackFormattingAction.Diff),
        )
        menu.addSeparator()

        #######################################################################
        ## isort related entries
        #######################################################################

        act = menu.addAction(self.tr("isort"), aboutIsort)
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        menu.addAction(
            self.tr("Sort Imports"),
            lambda: self.__performImportSortingWithIsort(IsortFormattingAction.Sort),
        )
        menu.addAction(
            self.tr("Imports Sorting Diff"),
            lambda: self.__performImportSortingWithIsort(IsortFormattingAction.Diff),
        )
        menu.addSeparator()

        menu.aboutToShow.connect(self.__showContextMenuFormatting)

        return menu

    def __initContextMenuTools(self):
        """
        Private method used to setup the Tools context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        menu = QMenu(self.tr("Tools"))
        menu.aboutToShow.connect(self.__showContextMenuTools)
        return menu

    def __initContextMenuShow(self):
        """
        Private method used to setup the Show context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        menu = QMenu(self.tr("Show"))

        self.codeMetricsAct = menu.addAction(
            self.tr("Code metrics..."), self.__showCodeMetrics
        )
        self.coverageMenuAct = menu.addAction(
            self.tr("Code coverage..."), self.__showCodeCoverage
        )
        self.coverageShowAnnotationMenuAct = menu.addAction(
            self.tr("Show code coverage annotations"), self.codeCoverageShowAnnotations
        )
        self.coverageHideAnnotationMenuAct = menu.addAction(
            self.tr("Hide code coverage annotations"),
            self.__codeCoverageHideAnnotations,
        )
        self.profileMenuAct = menu.addAction(
            self.tr("Profile data..."), self.__showProfileData
        )

        menu.aboutToShow.connect(self.__showContextMenuShow)

        return menu

    def __initContextMenuGraphics(self):
        """
        Private method used to setup the diagrams context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        menu = QMenu(self.tr("Diagrams"))

        menu.addAction(self.tr("Class Diagram..."), self.__showClassDiagram)
        menu.addAction(self.tr("Package Diagram..."), self.__showPackageDiagram)
        menu.addAction(self.tr("Imports Diagram..."), self.__showImportsDiagram)
        self.applicationDiagramMenuAct = menu.addAction(
            self.tr("Application Diagram..."), self.__showApplicationDiagram
        )
        menu.addSeparator()
        menu.addAction(
            EricPixmapCache.getIcon("open"),
            self.tr("Load Diagram..."),
            self.__loadDiagram,
        )

        menu.aboutToShow.connect(self.__showContextMenuGraphics)

        return menu

    def __initContextMenuLanguages(self):
        """
        Private method used to setup the Languages context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        menu = QMenu(self.tr("Languages"))

        self.languagesActGrp = QActionGroup(self)
        self.noLanguageAct = menu.addAction(
            EricPixmapCache.getIcon("fileText"), self.tr("Text")
        )
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

    def __initContextMenuEncodings(self):
        """
        Private method used to setup the Encodings context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        self.supportedEncodings = {}

        menu = QMenu(self.tr("Encodings"))

        self.encodingsActGrp = QActionGroup(self)

        for encoding in sorted(Utilities.supportedCodecs):
            act = menu.addAction(encoding)
            act.setCheckable(True)
            act.setData(encoding)
            self.supportedEncodings[encoding] = act
            self.encodingsActGrp.addAction(act)

        menu.triggered.connect(self.__encodingsMenuTriggered)
        menu.aboutToShow.connect(self.__showContextMenuEncodings)

        return menu

    def __initContextMenuReopenWithEncoding(self):
        """
        Private method used to setup the Reopen With Encoding context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        menu = QMenu(self.tr("Re-Open With Encoding"))
        menu.setIcon(EricPixmapCache.getIcon("documentOpen"))

        for encoding in sorted(Utilities.supportedCodecs):
            act = menu.addAction(encoding)
            act.setData(encoding)

        menu.triggered.connect(self.__reopenWithEncodingMenuTriggered)

        return menu

    def __initContextMenuEol(self):
        """
        Private method to setup the eol context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        self.supportedEols = {}

        menu = QMenu(self.tr("End-of-Line Type"))

        self.eolActGrp = QActionGroup(self)

        act = menu.addAction(EricPixmapCache.getIcon("eolLinux"), self.tr("Unix"))
        act.setCheckable(True)
        act.setData("\n")
        self.supportedEols["\n"] = act
        self.eolActGrp.addAction(act)

        act = menu.addAction(EricPixmapCache.getIcon("eolWindows"), self.tr("Windows"))
        act.setCheckable(True)
        act.setData("\r\n")
        self.supportedEols["\r\n"] = act
        self.eolActGrp.addAction(act)

        act = menu.addAction(EricPixmapCache.getIcon("eolMac"), self.tr("Macintosh"))
        act.setCheckable(True)
        act.setData("\r")
        self.supportedEols["\r"] = act
        self.eolActGrp.addAction(act)

        menu.triggered.connect(self.__eolMenuTriggered)
        menu.aboutToShow.connect(self.__showContextMenuEol)

        return menu

    def __initContextMenuSpellCheck(self):
        """
        Private method used to setup the spell checking context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        menu = QMenu(self.tr("Spelling"))
        menu.setIcon(EricPixmapCache.getIcon("spellchecking"))

        self.spellLanguagesMenu = self.__initContextMenuSpellLanguages()
        self.__menus["SpellLanguages"] = self.spellLanguagesMenu

        self.menuActs["SpellCheck"] = menu.addAction(
            EricPixmapCache.getIcon("spellchecking"),
            self.tr("Check spelling..."),
            self.checkSpelling,
        )
        self.menuActs["SpellCheckSelection"] = menu.addAction(
            EricPixmapCache.getIcon("spellchecking"),
            self.tr("Check spelling of selection..."),
            self.__checkSpellingSelection,
        )
        self.menuActs["SpellCheckRemove"] = menu.addAction(
            self.tr("Remove from dictionary"), self.__removeFromSpellingDictionary
        )
        self.menuActs["SpellCheckLanguages"] = menu.addMenu(self.spellLanguagesMenu)

        menu.aboutToShow.connect(self.__showContextMenuSpellCheck)

        return menu

    def __initContextMenuSpellLanguages(self):
        """
        Private method to setup the spell checking languages context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        self.supportedSpellLanguages = {}

        menu = QMenu(self.tr("Spell Check Languages"))

        self.spellLanguagesActGrp = QActionGroup(self)

        self.noSpellLanguageAct = menu.addAction(self.tr("No Language"))
        self.noSpellLanguageAct.setCheckable(True)
        self.noSpellLanguageAct.setData("")
        self.spellLanguagesActGrp.addAction(self.noSpellLanguageAct)
        menu.addSeparator()

        for language in sorted(SpellChecker.getAvailableLanguages()):
            act = menu.addAction(language)
            act.setCheckable(True)
            act.setData(language)
            self.supportedSpellLanguages[language] = act
            self.spellLanguagesActGrp.addAction(act)

        menu.triggered.connect(self.__spellLanguagesMenuTriggered)
        menu.aboutToShow.connect(self.__showContextMenuSpellLanguages)

        return menu

    def __initContextMenuMargins(self):
        """
        Private method used to setup the context menu for the margins.
        """
        self.marginMenuActs = {}

        # bookmark margin
        self.bmMarginMenu = QMenu()

        self.bmMarginMenu.addAction(self.tr("Toggle bookmark"), self.menuToggleBookmark)
        self.marginMenuActs["NextBookmark"] = self.bmMarginMenu.addAction(
            self.tr("Next bookmark"), self.nextBookmark
        )
        self.marginMenuActs["PreviousBookmark"] = self.bmMarginMenu.addAction(
            self.tr("Previous bookmark"), self.previousBookmark
        )
        self.marginMenuActs["ClearBookmark"] = self.bmMarginMenu.addAction(
            self.tr("Clear all bookmarks"), self.clearBookmarks
        )

        self.bmMarginMenu.aboutToShow.connect(
            lambda: self.__showContextMenuMargin(self.bmMarginMenu)
        )

        # breakpoint margin
        self.bpMarginMenu = QMenu()

        self.marginMenuActs["Breakpoint"] = self.bpMarginMenu.addAction(
            self.tr("Toggle breakpoint"), self.menuToggleBreakpoint
        )
        self.marginMenuActs["TempBreakpoint"] = self.bpMarginMenu.addAction(
            self.tr("Toggle temporary breakpoint"), self.__menuToggleTemporaryBreakpoint
        )
        self.marginMenuActs["EditBreakpoint"] = self.bpMarginMenu.addAction(
            self.tr("Edit breakpoint..."), self.menuEditBreakpoint
        )
        self.marginMenuActs["EnableBreakpoint"] = self.bpMarginMenu.addAction(
            self.tr("Enable breakpoint"), self.__menuToggleBreakpointEnabled
        )
        self.marginMenuActs["NextBreakpoint"] = self.bpMarginMenu.addAction(
            self.tr("Next breakpoint"), self.menuNextBreakpoint
        )
        self.marginMenuActs["PreviousBreakpoint"] = self.bpMarginMenu.addAction(
            self.tr("Previous breakpoint"), self.menuPreviousBreakpoint
        )
        self.marginMenuActs["ClearBreakpoint"] = self.bpMarginMenu.addAction(
            self.tr("Clear all breakpoints"), self.__menuClearBreakpoints
        )

        self.bpMarginMenu.aboutToShow.connect(
            lambda: self.__showContextMenuMargin(self.bpMarginMenu)
        )

        # fold margin
        self.foldMarginMenu = QMenu()

        self.marginMenuActs["ToggleAllFolds"] = self.foldMarginMenu.addAction(
            self.tr("Toggle all folds"), self.foldAll
        )
        self.marginMenuActs["ToggleAllFoldsAndChildren"] = (
            self.foldMarginMenu.addAction(
                self.tr("Toggle all folds (including children)"),
                lambda: self.foldAll(True),
            )
        )
        self.marginMenuActs["ToggleCurrentFold"] = self.foldMarginMenu.addAction(
            self.tr("Toggle current fold"), self.toggleCurrentFold
        )
        self.foldMarginMenu.addSeparator()
        self.marginMenuActs["ExpandChildren"] = self.foldMarginMenu.addAction(
            self.tr("Expand (including children)"),
            self.__contextMenuExpandFoldWithChildren,
        )
        self.marginMenuActs["CollapseChildren"] = self.foldMarginMenu.addAction(
            self.tr("Collapse (including children)"),
            self.__contextMenuCollapseFoldWithChildren,
        )
        self.foldMarginMenu.addSeparator()
        self.marginMenuActs["ClearAllFolds"] = self.foldMarginMenu.addAction(
            self.tr("Clear all folds"), self.clearFolds
        )

        self.foldMarginMenu.aboutToShow.connect(
            lambda: self.__showContextMenuMargin(self.foldMarginMenu)
        )

        # indicator margin
        self.indicMarginMenu = QMenu()

        self.marginMenuActs["GotoSyntaxError"] = self.indicMarginMenu.addAction(
            self.tr("Goto syntax error"), self.gotoSyntaxError
        )
        self.marginMenuActs["ShowSyntaxError"] = self.indicMarginMenu.addAction(
            self.tr("Show syntax error message"), self.__showSyntaxError
        )
        self.marginMenuActs["ClearSyntaxError"] = self.indicMarginMenu.addAction(
            self.tr("Clear syntax error"), self.clearSyntaxError
        )
        self.indicMarginMenu.addSeparator()
        self.marginMenuActs["NextWarningMarker"] = self.indicMarginMenu.addAction(
            self.tr("Next warning"), self.nextWarning
        )
        self.marginMenuActs["PreviousWarningMarker"] = self.indicMarginMenu.addAction(
            self.tr("Previous warning"), self.previousWarning
        )
        self.marginMenuActs["ShowWarning"] = self.indicMarginMenu.addAction(
            self.tr("Show warning message"), self.__showWarning
        )
        self.marginMenuActs["ClearWarnings"] = self.indicMarginMenu.addAction(
            self.tr("Clear warnings"), self.clearWarnings
        )
        self.indicMarginMenu.addSeparator()
        self.marginMenuActs["NextCoverageMarker"] = self.indicMarginMenu.addAction(
            self.tr("Next uncovered line"), self.nextUncovered
        )
        self.marginMenuActs["PreviousCoverageMarker"] = self.indicMarginMenu.addAction(
            self.tr("Previous uncovered line"), self.previousUncovered
        )
        self.indicMarginMenu.addSeparator()
        self.marginMenuActs["NextTaskMarker"] = self.indicMarginMenu.addAction(
            self.tr("Next task"), self.nextTask
        )
        self.marginMenuActs["PreviousTaskMarker"] = self.indicMarginMenu.addAction(
            self.tr("Previous task"), self.previousTask
        )
        self.indicMarginMenu.addSeparator()
        self.marginMenuActs["NextChangeMarker"] = self.indicMarginMenu.addAction(
            self.tr("Next change"), self.nextChange
        )
        self.marginMenuActs["PreviousChangeMarker"] = self.indicMarginMenu.addAction(
            self.tr("Previous change"), self.previousChange
        )
        self.marginMenuActs["ClearChangeMarkers"] = self.indicMarginMenu.addAction(
            self.tr("Clear changes"), self.__reinitOnlineChangeTrace
        )

        self.indicMarginMenu.aboutToShow.connect(
            lambda: self.__showContextMenuMargin(self.indicMarginMenu)
        )

    def exportFile(self, exporterFormat):
        """
        Public method to export the file.

        @param exporterFormat format the file should be exported into
        @type str
        """
        if exporterFormat:
            exporter = Exporters.getExporter(exporterFormat, self)
            if exporter:
                exporter.exportSource()
            else:
                EricMessageBox.critical(
                    self,
                    self.tr("Export source"),
                    self.tr(
                        """<p>No exporter available for the """
                        """export format <b>{0}</b>. Aborting...</p>"""
                    ).format(exporterFormat),
                )
        else:
            EricMessageBox.critical(
                self,
                self.tr("Export source"),
                self.tr("""No export format given. Aborting..."""),
            )

    @pyqtSlot()
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
        self.showMenu.emit("Languages", self.languagesMenu, self)

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
                self.filetype = language
                self.setLanguage(self.supportedLanguages[language][1])
                self.checkSyntax()

        self.resetDocstringGenerator()

    def __languageChanged(self, language, propagate=True):
        """
        Private method handling a change of a connected editor's language.

        @param language language to be set
        @type str
        @param propagate flag indicating to propagate the change
        @type bool
        """
        if language == "":
            self.__resetLanguage(propagate=propagate)
        elif language == "Guessed":
            self.setLanguage("dummy.pygments", propagate=propagate)
        elif language.startswith("Pygments|"):
            pyname = language.split("|", 1)[1]
            self.setLanguage("dummy.pygments", pyname=pyname, propagate=propagate)
        else:
            self.filetype = language
            self.setLanguage(self.supportedLanguages[language][1], propagate=propagate)
            self.checkSyntax()

        self.resetDocstringGenerator()

    def __resetLanguage(self, propagate=True):
        """
        Private method used to reset the language selection.

        @param propagate flag indicating to propagate the change
        @type bool
        """
        if self.lexer_ is not None and (
            self.lexer_.lexer() == "container" or self.lexer_.lexer() is None
        ):
            with contextlib.suppress(TypeError):
                self.SCN_STYLENEEDED.disconnect(self.__styleNeeded)

        self.apiLanguage = ""
        self.lexer_ = None
        self.__lexerReset = True
        self.setLexer()
        if self.completer is not None:
            self.completer.setEnabled(False)
            self.completer = None
        useMonospaced = self.useMonospaced
        self.__setTextDisplay()
        self.__setMarginsDisplay()
        self.setMonospaced(useMonospaced)
        with contextlib.suppress(AttributeError):
            self.menuActs["MonospacedFont"].setChecked(self.useMonospaced)

        self.resetDocstringGenerator()

        if not self.inLanguageChanged and propagate:
            self.inLanguageChanged = True
            self.languageChanged.emit(self.apiLanguage)
            self.inLanguageChanged = False

    def setLanguage(self, filename, initTextDisplay=True, propagate=True, pyname=""):
        """
        Public method to set a lexer language.

        @param filename filename used to determine the associated lexer
            language
        @type str
        @param initTextDisplay flag indicating an initialization of the text
            display is required as well
        @type bool
        @param propagate flag indicating to propagate the change
        @type bool
        @param pyname name of the pygments lexer to use
        @type str
        """
        # clear all warning and syntax error markers
        self.clearSyntaxError()
        self.clearWarnings()

        self.menuActs["MonospacedFont"].setChecked(False)

        self.__lexerReset = False
        self.__bindLexer(filename, pyname=pyname)
        self.__bindCompleter(filename)
        self.recolor()
        self.__checkLanguage()

        self.__docstringGenerator = None

        # set the text display
        if initTextDisplay:
            self.__setTextDisplay()

        # set the auto-completion and call-tips function
        self.__setAutoCompletion()
        self.__setCallTips()

        if not self.inLanguageChanged and propagate:
            self.inLanguageChanged = True
            self.languageChanged.emit(self.apiLanguage)
            self.inLanguageChanged = False

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

    @pyqtSlot()
    def projectLexerAssociationsChanged(self):
        """
        Public slot to handle changes of the project lexer associations.
        """
        self.setLanguage(self.fileName)

    @pyqtSlot()
    def __showContextMenuEncodings(self):
        """
        Private slot handling the aboutToShow signal of the encodings context
        menu.
        """
        self.showMenu.emit("Encodings", self.encodingsMenu, self)

    def __encodingsMenuTriggered(self, act):
        """
        Private method to handle the selection of an encoding.

        @param act reference to the action that was triggered
        @type QAction
        """
        encoding = act.data()
        self.setModified(True)
        self.__encodingChanged("{0}-selected".format(encoding))

    def __checkEncoding(self):
        """
        Private method to check the selected encoding of the encodings submenu.
        """
        with contextlib.suppress(AttributeError, KeyError):
            (self.supportedEncodings[self.__normalizedEncoding()].setChecked(True))

    @pyqtSlot(str)
    def __encodingChanged(self, encoding, propagate=True):
        """
        Private slot to handle a change of the encoding.

        @param encoding changed encoding
        @type str
        @param propagate flag indicating to propagate the change
        @type bool
        """
        self.encoding = encoding
        self.__checkEncoding()

        if not self.inEncodingChanged and propagate:
            self.inEncodingChanged = True
            self.encodingChanged.emit(self.encoding)
            self.inEncodingChanged = False

    def __normalizedEncoding(self, encoding=""):
        """
        Private method to calculate the normalized encoding string.

        @param encoding encoding to be normalized
        @type str
        @return normalized encoding
        @rtype str
        """
        if not encoding:
            encoding = self.encoding
        return (
            encoding.replace("-default", "")
            .replace("-guessed", "")
            .replace("-selected", "")
        )

    @pyqtSlot()
    def __showContextMenuEol(self):
        """
        Private slot handling the aboutToShow signal of the eol context menu.
        """
        self.showMenu.emit("Eol", self.eolMenu, self)

    def __eolMenuTriggered(self, act):
        """
        Private method to handle the selection of an eol type.

        @param act reference to the action that was triggered
        @type QAction
        """
        eol = act.data()
        self.setEolModeByEolString(eol)
        self.convertEols(self.eolMode())

    def __checkEol(self):
        """
        Private method to check the selected eol type of the eol submenu.
        """
        with contextlib.suppress(AttributeError, TypeError):
            self.supportedEols[self.getLineSeparator()].setChecked(True)

    @pyqtSlot()
    def __eolChanged(self):
        """
        Private slot to handle a change of the eol mode.
        """
        self.__checkEol()

        if not self.inEolChanged:
            self.inEolChanged = True
            eol = self.getLineSeparator()
            self.eolChanged.emit(eol)
            self.inEolChanged = False

    def convertEols(self, eolMode):
        """
        Public method to convert the end-of-line marker.

        This variant of the method emits a signal to update the IDE after
        the original method was called.

        @param eolMode end-of-line mode
        @type QsciScintilla.EolMode
        """
        super().convertEols(eolMode)
        self.__eolChanged()

    @pyqtSlot()
    def __showContextMenuSpellCheck(self):
        """
        Private slot handling the aboutToShow signal of the spell check
        context menu.
        """
        spellingAvailable = SpellChecker.isAvailable()
        self.menuActs["SpellCheck"].setEnabled(spellingAvailable)
        self.menuActs["SpellCheckSelection"].setEnabled(
            spellingAvailable and self.hasSelectedText()
        )
        self.menuActs["SpellCheckRemove"].setEnabled(
            spellingAvailable and self.spellingMenuPos >= 0
        )
        self.menuActs["SpellCheckLanguages"].setEnabled(spellingAvailable)

        self.showMenu.emit("SpellCheck", self.spellCheckMenu, self)

    @pyqtSlot()
    def __showContextMenuSpellLanguages(self):
        """
        Private slot handling the aboutToShow signal of the spell check
        languages context menu.
        """
        self.showMenu.emit("SpellLanguage", self.spellLanguagesMenu, self)

    def __spellLanguagesMenuTriggered(self, act):
        """
        Private method to handle the selection of a spell check language.

        @param act reference to the action that was triggered
        @type QAction
        """
        language = act.data()
        self.__setSpellingLanguage(language)
        self.spellLanguageChanged.emit(language)

    @pyqtSlot()
    def __checkSpellLanguage(self):
        """
        Private slot to check the selected spell check language action.
        """
        language = self.getSpellingLanguage()
        with contextlib.suppress(AttributeError, KeyError):
            self.supportedSpellLanguages[language].setChecked(True)

    @pyqtSlot(str)
    def __spellLanguageChanged(self, language, propagate=True):
        """
        Private slot to handle a change of the spell check language.

        @param language new spell check language
        @type str
        @param propagate flag indicating to propagate the change
        @type bool
        """
        self.__setSpellingLanguage(language)
        self.__checkSpellLanguage()

        if not self.__inSpellLanguageChanged and propagate:
            self.__inSpellLanguageChanged = True
            self.spellLanguageChanged.emit(language)
            self.__inSpellLanguageChanged = False

    def __bindLexer(self, filename, pyname=""):
        """
        Private method to set the correct lexer depending on language.

        @param filename filename used to determine the associated lexer
            language
        @type str
        @param pyname name of the pygments lexer to use
        @type str
        """
        if self.lexer_ is not None and (
            self.lexer_.lexer() == "container" or self.lexer_.lexer() is None
        ):
            self.SCN_STYLENEEDED.disconnect(self.__styleNeeded)

        language = ""
        if not self.filetype:
            if filename:
                basename = os.path.basename(filename)
                if self.project.isOpen() and self.project.isProjectFile(filename):
                    language = self.project.getEditorLexerAssoc(basename)
                if not language:
                    language = Preferences.getEditorLexerAssoc(basename)
            if language == "Text":
                # no highlighting for plain text files
                self.__resetLanguage()
                return

            if not language:
                bindName = self.__bindName(self.text(0))
                if bindName:
                    language = Preferences.getEditorLexerAssoc(bindName)
            if language == "Python":
                # correction for Python
                language = "Python3"
            if language in [
                "Python3",
                "MicroPython",
                "Cython",
                "Ruby",
                "JavaScript",
                "YAML",
                "JSON",
            ]:
                self.filetype = language
            else:
                self.filetype = ""
        else:
            language = self.filetype

        if language.startswith("Pygments|"):
            pyname = language
            self.filetype = language.split("|")[-1]
            language = ""

        self.lexer_ = Lexers.getLexer(language, self, pyname=pyname)
        if self.lexer_ is None:
            self.setLexer()
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
        self.setLexer(self.lexer_)
        self.__setMarginsDisplay()
        if self.lexer_.lexer() == "container" or self.lexer_.lexer() is None:
            self.SCN_STYLENEEDED.connect(self.__styleNeeded)

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
            self.lexer_.readSubstyles(self)

        # now set the lexer properties
        self.lexer_.initProperties()

        # initialize the lexer APIs settings
        projectType = (
            self.project.getProjectType()
            if self.project.isOpen() and self.project.isProjectFile(filename)
            else ""
        )
        api = self.vm.getAPIsManager().getAPIs(
            self.apiLanguage, projectType=projectType
        )
        if api is not None and not api.isEmpty():
            self.lexer_.setAPIs(api.getQsciAPIs())
            self.acAPI = True
        else:
            self.acAPI = False
        self.autoCompletionAPIsAvailable.emit(self.acAPI)

        self.__setAnnotationStyles()

        self.lexer_.setDefaultColor(self.lexer_.color(0))
        self.lexer_.setDefaultPaper(self.lexer_.paper(0))

    @pyqtSlot(int)
    def __styleNeeded(self, position):
        """
        Private slot to handle the need for more styling.

        @param position end position, that needs styling
        @type int
        """
        self.lexer_.styleText(self.getEndStyled(), position)

    def getLexer(self):
        """
        Public method to retrieve a reference to the lexer object.

        @return the lexer object
        @rtype Lexer
        """
        return self.lexer_

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

    def getApiLanguage(self):
        """
        Public method to get the API language of the editor.

        @return API language
        @rtype str
        """
        return self.apiLanguage

    def __bindCompleter(self, filename):
        """
        Private method to set the correct typing completer depending on language.

        @param filename filename used to determine the associated typing
            completer language
        @type str
        """
        if self.completer is not None:
            self.completer.setEnabled(False)
            self.completer = None

        filename = os.path.basename(filename)
        apiLanguage = Preferences.getEditorLexerAssoc(filename)
        if apiLanguage == "":
            if PythonUtilities.isPythonSource(self.fileName, self.text(0), self):
                apiLanguage = "Python3"
            elif self.isRubyFile():
                apiLanguage = "Ruby"

        self.completer = TypingCompleters.getCompleter(apiLanguage, self)

    def getCompleter(self):
        """
        Public method to retrieve a reference to the completer object.

        @return the completer object
        @rtype CompleterBase
        """
        return self.completer

    @pyqtSlot(bool)
    def __modificationChanged(self, m):
        """
        Private slot to handle the modificationChanged signal.

        It emits the signal modificationStatusChanged with parameters
        m and self.

        @param m modification status
        @type bool
        """
        if not m:
            self.recordModificationTime()
        self.modificationStatusChanged.emit(m, self)
        self.undoAvailable.emit(self.isUndoAvailable())
        self.redoAvailable.emit(self.isRedoAvailable())

        if not m:
            self.__autosaveTimer.stop()

    @pyqtSlot(int, int)
    def __cursorPositionChanged(self, line, index):
        """
        Private slot to handle the cursorPositionChanged signal.

        It emits the signal cursorChanged with parameters fileName,
        line and pos.

        @param line line number of the cursor
        @type int
        @param index position in line of the cursor
        @type int
        """
        self.cursorChanged.emit(self.fileName, line + 1, index)

        if Preferences.getEditor("MarkOccurrencesEnabled"):
            self.__markOccurrencesTimer.start()

        if self.lastLine != line:
            self.cursorLineChanged.emit(line)

        if self.spell is not None:
            # do spell checking
            doSpelling = True
            if self.lastLine == line:
                start, end = self.getWordBoundaries(line, index, useWordChars=False)
                if start <= self.lastIndex and self.lastIndex <= end:
                    doSpelling = False
            if doSpelling:
                pos = self.positionFromLineIndex(self.lastLine, self.lastIndex)
                self.spell.checkWord(pos)

        if self.lastLine != line:
            self.__markerMap.update()

        self.lastLine = line
        self.lastIndex = index

    @pyqtSlot()
    def __modificationReadOnly(self):
        """
        Private slot to handle the modificationAttempted signal.
        """
        EricMessageBox.warning(
            self,
            self.tr("Modification of Read Only file"),
            self.tr(
                """You are attempting to change a read only file. """
                """Please save to a different file first."""
            ),
        )

    def setNoName(self, noName):
        """
        Public method to set the display string for an unnamed editor.

        @param noName display string for this unnamed editor
        @type str
        """
        self.noName = noName

    def getNoName(self):
        """
        Public method to get the display string for an unnamed editor.

        @return display string for this unnamed editor
        @rtype str
        """
        return self.noName

    def getFileName(self):
        """
        Public method to return the name of the file being displayed.

        @return filename of the displayed file
        @rtype str
        """
        return self.fileName

    def getFileType(self):
        """
        Public method to return the type of the file being displayed.

        @return type of the displayed file
        @rtype str
        """
        return self.filetype

    def getFileTypeByFlag(self):
        """
        Public method to return the type of the file, if it was set by an
        eflag: marker.

        @return type of the displayed file, if set by an eflag: marker or an
            empty string
        @rtype str
        """
        if self.filetypeByFlag:
            return self.filetype
        else:
            return ""

    def determineFileType(self):
        """
        Public method to determine the file type using various tests.

        @return type of the displayed file or an empty string
        @rtype str
        """
        ftype = self.filetype
        if not ftype:
            if PythonUtilities.isPythonSource(self.fileName, self.text(0), self):
                ftype = "Python3"
            elif self.isRubyFile():
                ftype = "Ruby"
            else:
                ftype = ""

        return ftype

    def getEncoding(self):
        """
        Public method to return the current encoding.

        @return current encoding
        @rtype str
        """
        return self.encoding

    def isPyFile(self):
        """
        Public method to return a flag indicating a Python (2 or 3) file.

        @return flag indicating a Python3 file
        @rtype bool
        """
        return PythonUtilities.isPythonSource(self.fileName, self.text(0), self)

    def isPy3File(self):
        """
        Public method to return a flag indicating a Python3 file.

        @return flag indicating a Python3 file
        @rtype bool
        """
        return PythonUtilities.isPythonSource(self.fileName, self.text(0), self)

    def isMicroPythonFile(self):
        """
        Public method to return a flag indicating a MicroPython file.

        @return flag indicating a MicroPython file
        @rtype bool
        """
        if self.filetype == "MicroPython":
            return True

        return False

    def isCythonFile(self):
        """
        Public method to return a flag indicating a Cython file.

        @return flag indicating a Cython file
        @rtype bool
        """
        if self.filetype == "Cython":
            return True

        return False

    def isRubyFile(self):
        """
        Public method to return a flag indicating a Ruby file.

        @return flag indicating a Ruby file
        @rtype bool
        """
        if self.filetype == "Ruby":
            return True

        if self.filetype == "":
            line0 = self.text(0)
            if line0.startswith("#!") and "ruby" in line0:
                self.filetype = "Ruby"
                return True

            if bool(self.fileName) and os.path.splitext(self.fileName)[
                1
            ] in self.dbs.getExtensions("Ruby"):
                self.filetype = "Ruby"
                return True

        return False

    def isJavascriptFile(self):
        """
        Public method to return a flag indicating a Javascript file.

        @return flag indicating a Javascript file
        @rtype bool
        """
        if self.filetype == "JavaScript":
            return True

        if (
            self.filetype == ""
            and self.fileName
            and os.path.splitext(self.fileName)[1] == ".js"
        ):
            self.filetype = "JavaScript"
            return True

        return False

    def isProjectFile(self):
        """
        Public method to check, if the file of the editor belongs to the current
        project.

        @return flag indicating a project file
        @rtype bool
        """
        return (
            bool(self.fileName)
            and self.project.isOpen()
            and self.project.isProjectFile(self.fileName)
        )

    def highlightVisible(self):
        """
        Public method to make sure that the highlight is visible.
        """
        if self.lastHighlight is not None:
            lineno = self.markerLine(self.lastHighlight)
            self.ensureVisible(lineno + 1)

    def highlight(self, line=None, error=False):
        """
        Public method to highlight [or de-highlight] a particular line.

        @param line line number to highlight
        @type int
        @param error flag indicating whether the error highlight should be
            used
        @type bool
        """
        if line is None:
            self.lastHighlight = None
            if self.lastErrorMarker is not None:
                self.markerDeleteHandle(self.lastErrorMarker)
            self.lastErrorMarker = None
            if self.lastCurrMarker is not None:
                self.markerDeleteHandle(self.lastCurrMarker)
            self.lastCurrMarker = None
        else:
            if error:
                if self.lastErrorMarker is not None:
                    self.markerDeleteHandle(self.lastErrorMarker)
                self.lastErrorMarker = self.markerAdd(line - 1, self.errorline)
                self.lastHighlight = self.lastErrorMarker
            else:
                if self.lastCurrMarker is not None:
                    self.markerDeleteHandle(self.lastCurrMarker)
                self.lastCurrMarker = self.markerAdd(line - 1, self.currentline)
                self.lastHighlight = self.lastCurrMarker
            self.setCursorPosition(line - 1, 0)

    def getHighlightPosition(self):
        """
        Public method to return the position of the highlight bar.

        @return line number of the highlight bar
        @rtype int
        """
        if self.lastHighlight is not None:
            return self.markerLine(self.lastHighlight)
        else:
            return 1

    ###########################################################################
    ## Breakpoint handling methods below
    ###########################################################################

    def __modified(
        self,
        _pos,
        mtype,
        _text,
        _length,
        linesAdded,
        line,
        _foldNow,
        _foldPrev,
        _token,
        _annotationLinesAdded,
    ):
        """
        Private method to handle changes of the number of lines.

        @param _pos start position of change (unused)
        @type int
        @param mtype flags identifying the change
        @type int
        @param _text text that is given to the Undo system (unused)
        @type str
        @param _length length of the change (unused)
        @type int
        @param linesAdded number of added/deleted lines
        @type int
        @param line line number of a fold level or marker change
        @type int
        @param _foldNow new fold level (unused)
        @type int
        @param _foldPrev previous fold level (unused)
        @type int
        @param _token ??? (unused)
        @type int
        @param _annotationLinesAdded number of added/deleted annotation lines (unused)
        @type int
        """
        if mtype & (self.SC_MOD_INSERTTEXT | self.SC_MOD_DELETETEXT):
            # 1. set/reset the autosave timer
            if self.__autosaveInterval > 0:
                self.__autosaveTimer.start(self.__autosaveInterval * 1000)

            # 2. move breakpoints if a line was inserted or deleted
            if linesAdded != 0 and self.breaks:
                bps = []  # list of breakpoints
                for handle, (
                    ln,
                    cond,
                    temp,
                    enabled,
                    ignorecount,
                ) in self.breaks.items():
                    line = self.markerLine(handle) + 1
                    if ln != line:
                        bps.append((ln, line))
                        self.breaks[handle] = (line, cond, temp, enabled, ignorecount)
                self.inLinesChanged = True
                for ln, line in sorted(bps, reverse=linesAdded > 0):
                    index1 = self.breakpointModel.getBreakPointIndex(self.fileName, ln)
                    index2 = self.breakpointModel.index(index1.row(), 1)
                    self.breakpointModel.setData(index2, line)
                self.inLinesChanged = False

    def __restoreBreakpoints(self):
        """
        Private method to restore the breakpoints.
        """
        for handle in self.breaks:
            self.markerDeleteHandle(handle)
        self.__addBreakPoints(QModelIndex(), 0, self.breakpointModel.rowCount() - 1)
        self.__markerMap.update()

    @pyqtSlot(QModelIndex, int, int)
    def __deleteBreakPoints(self, parentIndex, start, end):
        """
        Private slot to delete breakpoints.

        @param parentIndex index of parent item
        @type QModelIndex
        @param start start row
        @type int
        @param end end row
        @type int
        """
        for row in range(start, end + 1):
            index = self.breakpointModel.index(row, 0, parentIndex)
            fn, lineno = self.breakpointModel.getBreakPointByIndex(index)[0:2]
            if fn == self.fileName:
                self.clearBreakpoint(lineno)

    @pyqtSlot(QModelIndex, QModelIndex)
    def __changeBreakPoints(self, startIndex, endIndex):
        """
        Private slot to set changed breakpoints.

        @param startIndex start index of the breakpoints being changed
        @type QModelIndex
        @param endIndex end index of the breakpoints being changed
        @type QModelIndex
        """
        if not self.inLinesChanged:
            self.__addBreakPoints(QModelIndex(), startIndex.row(), endIndex.row())

    @pyqtSlot(QModelIndex, QModelIndex)
    def __breakPointDataAboutToBeChanged(self, startIndex, endIndex):
        """
        Private slot to handle the dataAboutToBeChanged signal of the
        breakpoint model.

        @param startIndex start index of the rows to be changed
        @type QModelIndex
        @param endIndex end index of the rows to be changed
        @type QModelIndex
        """
        self.__deleteBreakPoints(QModelIndex(), startIndex.row(), endIndex.row())

    @pyqtSlot(QModelIndex, int, int)
    def __addBreakPoints(self, parentIndex, start, end):
        """
        Private slot to add breakpoints.

        @param parentIndex index of parent item
        @type QModelIndex
        @param start start row
        @type int
        @param end end row
        @type int
        """
        for row in range(start, end + 1):
            index = self.breakpointModel.index(row, 0, parentIndex)
            (
                fn,
                line,
                cond,
                temp,
                enabled,
                ignorecount,
            ) = self.breakpointModel.getBreakPointByIndex(index)[:6]
            if fn == self.fileName:
                self.newBreakpointWithProperties(
                    line, (cond, temp, enabled, ignorecount)
                )

    def clearBreakpoint(self, line):
        """
        Public method to clear a breakpoint.

        Note: This doesn't clear the breakpoint in the debugger,
        it just deletes it from the editor internal list of breakpoints.

        @param line line number of the breakpoint
        @type int
        """
        if self.inLinesChanged:
            return

        for handle in list(self.breaks):
            if self.markerLine(handle) == line - 1:
                del self.breaks[handle]
                self.markerDeleteHandle(handle)
                self.__markerMap.update()
                return

    def newBreakpointWithProperties(self, line, properties):
        """
        Public method to set a new breakpoint and its properties.

        @param line line number of the breakpoint
        @type int
        @param properties properties for the breakpoint
                (condition, temporary flag, enabled flag, ignore count)
        @type tuple of (str, bool, bool, int)
        """
        if not properties[2]:
            marker = self.dbreakpoint
        elif properties[0]:
            marker = properties[1] and self.tcbreakpoint or self.cbreakpoint
        else:
            marker = properties[1] and self.tbreakpoint or self.breakpoint

        if self.markersAtLine(line - 1) & self.breakpointMask == 0:
            handle = self.markerAdd(line - 1, marker)
            self.breaks[handle] = (line,) + properties
            self.breakpointToggled.emit(self)
            self.__markerMap.update()

    def __toggleBreakpoint(self, line, temporary=False):
        """
        Private method to toggle a breakpoint.

        @param line line number of the breakpoint
        @type int
        @param temporary flag indicating a temporary breakpoint
        @type bool
        """
        for handle in self.breaks:
            if self.markerLine(handle) == line - 1:
                # delete breakpoint or toggle it to the next state
                index = self.breakpointModel.getBreakPointIndex(self.fileName, line)
                if Preferences.getDebugger(
                    "ThreeStateBreakPoints"
                ) and not self.breakpointModel.isBreakPointTemporaryByIndex(index):
                    self.breakpointModel.deleteBreakPointByIndex(index)
                    self.__addBreakPoint(line, True)
                else:
                    self.breakpointModel.deleteBreakPointByIndex(index)
                    self.breakpointToggled.emit(self)
                break
        else:
            self.__addBreakPoint(line, temporary)

    def __addBreakPoint(self, line, temporary):
        """
        Private method to add a new breakpoint.

        @param line line number of the breakpoint
        @type int
        @param temporary flag indicating a temporary breakpoint
        @type bool
        """
        if self.fileName and self.isPyFile():
            linestarts = PythonDisViewer.linestarts(self.text())
            if line not in linestarts:
                if Preferences.getDebugger("IntelligentBreakpoints"):
                    # change line to the next one starting an instruction block
                    index = bisect.bisect(linestarts, line)
                    with contextlib.suppress(IndexError):
                        line = linestarts[index]
                        self.__toggleBreakpoint(line, temporary=temporary)
                else:
                    EricMessageBox.warning(
                        self,
                        self.tr("Add Breakpoint"),
                        self.tr(
                            "No Python byte code will be created for the"
                            " selected line. No break point will be set!"
                        ),
                    )
                return

            self.breakpointModel.addBreakPoint(
                self.fileName, line, ("", temporary, True, 0)
            )
            self.breakpointToggled.emit(self)

    def __toggleBreakpointEnabled(self, line):
        """
        Private method to toggle a breakpoints enabled status.

        @param line line number of the breakpoint
        @type int
        """
        for handle in self.breaks:
            if self.markerLine(handle) == line - 1:
                index = self.breakpointModel.getBreakPointIndex(self.fileName, line)
                self.breakpointModel.setBreakPointEnabledByIndex(
                    index, not self.breaks[handle][3]
                )
                break

    def curLineHasBreakpoint(self):
        """
        Public method to check for the presence of a breakpoint at the current
        line.

        @return flag indicating the presence of a breakpoint
        @rtype bool
        """
        line, _ = self.getCursorPosition()
        return self.markersAtLine(line) & self.breakpointMask != 0

    def getBreakpointLines(self):
        """
        Public method to get the lines containing a breakpoint.

        @return list of lines containing a breakpoint
        @rtype list of int
        """
        lines = []
        line = -1
        while True:
            line = self.markerFindNext(line + 1, self.breakpointMask)
            if line < 0:
                break
            else:
                lines.append(line)
        return lines

    def hasBreakpoints(self):
        """
        Public method to check for the presence of breakpoints.

        @return flag indicating the presence of breakpoints
        @rtype bool
        """
        return len(self.breaks) > 0

    @pyqtSlot()
    def __menuToggleTemporaryBreakpoint(self):
        """
        Private slot to handle the 'Toggle temporary breakpoint' context menu
        action.
        """
        if self.line < 0:
            self.line, index = self.getCursorPosition()
        self.line += 1
        self.__toggleBreakpoint(self.line, 1)
        self.line = -1

    @pyqtSlot()
    def menuToggleBreakpoint(self):
        """
        Public slot to handle the 'Toggle breakpoint' context menu action.
        """
        if self.line < 0:
            self.line, index = self.getCursorPosition()
        self.line += 1
        self.__toggleBreakpoint(self.line)
        self.line = -1

    @pyqtSlot()
    def __menuToggleBreakpointEnabled(self):
        """
        Private slot to handle the 'Enable/Disable breakpoint' context menu
        action.
        """
        if self.line < 0:
            self.line, index = self.getCursorPosition()
        self.line += 1
        self.__toggleBreakpointEnabled(self.line)
        self.line = -1

    @pyqtSlot()
    def menuEditBreakpoint(self, line=None):
        """
        Public slot to handle the 'Edit breakpoint' context menu action.

        @param line line number of the breakpoint to edit
        @type int
        """
        from eric7.Debugger.EditBreakpointDialog import EditBreakpointDialog

        if line is not None:
            self.line = line - 1
        if self.line < 0:
            self.line, index = self.getCursorPosition()

        for handle in self.breaks:
            if self.markerLine(handle) == self.line:
                ln, cond, temp, enabled, ignorecount = self.breaks[handle]
                index = self.breakpointModel.getBreakPointIndex(self.fileName, ln)
                if not index.isValid():
                    return

                # get recently used breakpoint conditions
                rs = Preferences.Prefs.rsettings.value(recentNameBreakpointConditions)
                condHistory = (
                    EricUtilities.toList(rs)[: Preferences.getDebugger("RecentNumber")]
                    if rs is not None
                    else []
                )

                dlg = EditBreakpointDialog(
                    (self.fileName, ln),
                    (cond, temp, enabled, ignorecount),
                    condHistory,
                    parent=self,
                    modal=True,
                )
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    cond, temp, enabled, ignorecount = dlg.getData()
                    self.breakpointModel.setBreakPointByIndex(
                        index, self.fileName, ln, (cond, temp, enabled, ignorecount)
                    )

                    if cond:
                        # save the recently used breakpoint condition
                        if cond in condHistory:
                            condHistory.remove(cond)
                        condHistory.insert(0, cond)
                        Preferences.Prefs.rsettings.setValue(
                            recentNameBreakpointConditions, condHistory
                        )
                        Preferences.Prefs.rsettings.sync()

                    break

        self.line = -1

    @pyqtSlot()
    def menuNextBreakpoint(self):
        """
        Public slot to handle the 'Next breakpoint' context menu action.
        """
        line, index = self.getCursorPosition()
        if line == self.lines() - 1:
            line = 0
        else:
            line += 1
        bpline = self.markerFindNext(line, self.breakpointMask)
        if bpline < 0:
            # wrap around
            bpline = self.markerFindNext(0, self.breakpointMask)
        if bpline >= 0:
            self.setCursorPosition(bpline, 0)
            self.ensureLineVisible(bpline)

    @pyqtSlot()
    def menuPreviousBreakpoint(self):
        """
        Public slot to handle the 'Previous breakpoint' context menu action.
        """
        line, index = self.getCursorPosition()
        if line == 0:
            line = self.lines() - 1
        else:
            line -= 1
        bpline = self.markerFindPrevious(line, self.breakpointMask)
        if bpline < 0:
            # wrap around
            bpline = self.markerFindPrevious(self.lines() - 1, self.breakpointMask)
        if bpline >= 0:
            self.setCursorPosition(bpline, 0)
            self.ensureLineVisible(bpline)

    @pyqtSlot()
    def __menuClearBreakpoints(self):
        """
        Private slot to handle the 'Clear all breakpoints' context menu action.
        """
        self.__clearBreakpoints(self.fileName)

    def __clearBreakpoints(self, fileName):
        """
        Private method to clear all breakpoints.

        @param fileName name of the file
        @type str
        """
        idxList = []
        for ln, _, _, _, _ in self.breaks.values():
            index = self.breakpointModel.getBreakPointIndex(fileName, ln)
            if index.isValid():
                idxList.append(index)
        if idxList:
            self.breakpointModel.deleteBreakPoints(idxList)

    ###########################################################################
    ## Bookmark handling methods below
    ###########################################################################

    def toggleBookmark(self, line):
        """
        Public method to toggle a bookmark.

        @param line line number of the bookmark
        @type int
        """
        for handle in self.bookmarks[:]:
            if self.markerLine(handle) == line - 1:
                self.bookmarks.remove(handle)
                self.markerDeleteHandle(handle)
                break
        else:
            # set a new bookmark
            handle = self.markerAdd(line - 1, self.bookmark)
            self.bookmarks.append(handle)
        self.bookmarkToggled.emit(self)
        self.__markerMap.update()

    def getBookmarks(self):
        """
        Public method to retrieve the bookmarks.

        @return sorted list of all lines containing a bookmark
        @rtype list of int
        """
        bmlist = []
        for handle in self.bookmarks:
            bmlist.append(self.markerLine(handle) + 1)

        bmlist.sort()
        return bmlist

    def getBookmarkLines(self):
        """
        Public method to get the lines containing a bookmark.

        @return list of lines containing a bookmark
        @rtype list of int
        """
        lines = []
        line = -1
        while True:
            line = self.markerFindNext(line + 1, 1 << self.bookmark)
            if line < 0:
                break
            else:
                lines.append(line)
        return lines

    def hasBookmarks(self):
        """
        Public method to check for the presence of bookmarks.

        @return flag indicating the presence of bookmarks
        @rtype bool
        """
        return len(self.bookmarks) > 0

    @pyqtSlot()
    def menuToggleBookmark(self):
        """
        Public slot to handle the 'Toggle bookmark' context menu action.
        """
        if self.line < 0:
            self.line, index = self.getCursorPosition()
        self.line += 1
        self.toggleBookmark(self.line)
        self.line = -1

    @pyqtSlot()
    def nextBookmark(self):
        """
        Public slot to handle the 'Next bookmark' context menu action.
        """
        line, index = self.getCursorPosition()
        if line == self.lines() - 1:
            line = 0
        else:
            line += 1
        bmline = self.markerFindNext(line, 1 << self.bookmark)
        if bmline < 0:
            # wrap around
            bmline = self.markerFindNext(0, 1 << self.bookmark)
        if bmline >= 0:
            self.setCursorPosition(bmline, 0)
            self.ensureLineVisible(bmline)

    @pyqtSlot()
    def previousBookmark(self):
        """
        Public slot to handle the 'Previous bookmark' context menu action.
        """
        line, index = self.getCursorPosition()
        if line == 0:
            line = self.lines() - 1
        else:
            line -= 1
        bmline = self.markerFindPrevious(line, 1 << self.bookmark)
        if bmline < 0:
            # wrap around
            bmline = self.markerFindPrevious(self.lines() - 1, 1 << self.bookmark)
        if bmline >= 0:
            self.setCursorPosition(bmline, 0)
            self.ensureLineVisible(bmline)

    @pyqtSlot()
    def clearBookmarks(self):
        """
        Public slot to handle the 'Clear all bookmarks' context menu action.
        """
        for handle in self.bookmarks:
            self.markerDeleteHandle(handle)
        self.bookmarks.clear()
        self.bookmarkToggled.emit(self)
        self.__markerMap.update()

    ###########################################################################
    ## Printing methods below
    ###########################################################################

    @pyqtSlot()
    def printFile(self):
        """
        Public slot to print the text.
        """
        from .Printer import Printer

        printer = Printer(mode=QPrinter.PrinterMode.HighResolution)
        sb = ericApp().getObject("UserInterface").statusBar()
        printDialog = QPrintDialog(printer, self)
        if self.hasSelectedText():
            printDialog.setOption(
                QAbstractPrintDialog.PrintDialogOption.PrintSelection, True
            )
        if printDialog.exec() == QDialog.DialogCode.Accepted:
            sb.showMessage(self.tr("Printing..."))
            QApplication.processEvents()
            fn = self.getFileName()
            if fn is not None:
                printer.setDocName(os.path.basename(fn))
            else:
                printer.setDocName(self.noName)
            if printDialog.printRange() == QAbstractPrintDialog.PrintRange.Selection:
                # get the selection
                fromLine, _fromIndex, toLine, toIndex = self.getSelection()
                if toIndex == 0:
                    toLine -= 1
                # QScintilla seems to print one line more than told
                res = printer.printRange(self, fromLine, toLine - 1)
            else:
                res = printer.printRange(self)
            if res:
                sb.showMessage(self.tr("Printing completed"), 2000)
            else:
                sb.showMessage(self.tr("Error while printing"), 2000)
            QApplication.processEvents()
        else:
            sb.showMessage(self.tr("Printing aborted"), 2000)
            QApplication.processEvents()

    @pyqtSlot()
    def printPreviewFile(self):
        """
        Public slot to show a print preview of the text.
        """
        from .Printer import Printer

        printer = Printer(mode=QPrinter.PrinterMode.HighResolution)
        fn = self.getFileName()
        if fn is not None:
            printer.setDocName(os.path.basename(fn))
        else:
            printer.setDocName(self.noName)
        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(self.__printPreview)
        preview.exec()

    def __printPreview(self, printer):
        """
        Private slot to generate a print preview.

        @param printer reference to the printer object
        @type QScintilla.Printer.Printer
        """
        printer.printRange(self)

    ###########################################################################
    ## Task handling methods below
    ###########################################################################

    def getTaskLines(self):
        """
        Public method to get the lines containing a task.

        @return list of lines containing a task
        @rtype list of int
        """
        lines = []
        line = -1
        while True:
            line = self.markerFindNext(line + 1, 1 << self.taskmarker)
            if line < 0:
                break
            else:
                lines.append(line)
        return lines

    def hasTaskMarkers(self):
        """
        Public method to determine, if this editor contains any task markers.

        @return flag indicating the presence of task markers
        @rtype bool
        """
        return self.__hasTaskMarkers

    @pyqtSlot()
    def nextTask(self):
        """
        Public slot to handle the 'Next task' context menu action.
        """
        line, index = self.getCursorPosition()
        if line == self.lines() - 1:
            line = 0
        else:
            line += 1
        taskline = self.markerFindNext(line, 1 << self.taskmarker)
        if taskline < 0:
            # wrap around
            taskline = self.markerFindNext(0, 1 << self.taskmarker)
        if taskline >= 0:
            self.setCursorPosition(taskline, 0)
            self.ensureLineVisible(taskline)

    @pyqtSlot()
    def previousTask(self):
        """
        Public slot to handle the 'Previous task' context menu action.
        """
        line, index = self.getCursorPosition()
        if line == 0:
            line = self.lines() - 1
        else:
            line -= 1
        taskline = self.markerFindPrevious(line, 1 << self.taskmarker)
        if taskline < 0:
            # wrap around
            taskline = self.markerFindPrevious(self.lines() - 1, 1 << self.taskmarker)
        if taskline >= 0:
            self.setCursorPosition(taskline, 0)
            self.ensureLineVisible(taskline)

    @pyqtSlot()
    def extractTasks(self):
        """
        Public slot to extract all tasks.
        """
        from eric7.Tasks.Task import Task

        markers = {
            taskType: Preferences.getTasks(markersName).split()
            for taskType, markersName in Task.TaskType2MarkersName.items()
        }
        txtList = self.text().split(self.getLineSeparator())

        # clear all task markers and tasks
        self.markerDeleteAll(self.taskmarker)
        self.taskViewer.clearFileTasks(self.fileName)
        self.__hasTaskMarkers = False

        # now search tasks and record them
        for lineIndex, line in enumerate(txtList):
            shouldBreak = False

            if line.endswith("__NO-TASK__"):
                # ignore potential task marker
                continue

            for taskType, taskMarkers in markers.items():
                for taskMarker in taskMarkers:
                    index = line.find(taskMarker)
                    if index > -1:
                        task = line[index:]
                        self.markerAdd(lineIndex, self.taskmarker)
                        self.taskViewer.addFileTask(
                            task, self.fileName, lineIndex + 1, taskType
                        )
                        self.__hasTaskMarkers = True
                        shouldBreak = True
                        break
                if shouldBreak:
                    break
        self.taskMarkersUpdated.emit(self)
        self.__markerMap.update()

    ###########################################################################
    ## Change tracing methods below
    ###########################################################################

    def __createChangeMarkerPixmap(self, key, size=16):
        """
        Private method to create a pixmap for the change markers.

        @param key key of the color to use
        @type str
        @param size size of the pixmap
        @type int
        @return create pixmap
        @rtype QPixmap
        """
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.fillRect(size - 4, 0, 4, size, Preferences.getEditorColour(key))
        painter.end()
        return pixmap

    @pyqtSlot()
    def __initOnlineChangeTrace(self):
        """
        Private slot to initialize the online change trace.
        """
        self.__hasChangeMarkers = False
        self.__oldText = self.text()
        self.__lastSavedText = self.text()
        self.__onlineChangeTraceTimer = QTimer(self)
        self.__onlineChangeTraceTimer.setSingleShot(True)
        self.__onlineChangeTraceTimer.setInterval(
            Preferences.getEditor("OnlineChangeTraceInterval")
        )
        self.__onlineChangeTraceTimer.timeout.connect(
            self.__onlineChangeTraceTimerTimeout
        )
        self.textChanged.connect(self.__resetOnlineChangeTraceTimer)

    @pyqtSlot()
    def __reinitOnlineChangeTrace(self):
        """
        Private slot to re-initialize the online change trace.
        """
        self.__oldText = self.text()
        self.__lastSavedText = self.text()
        self.__deleteAllChangeMarkers()

    def __resetOnlineChangeTraceTimer(self):
        """
        Private method to reset the online syntax check timer.
        """
        if Preferences.getEditor("OnlineChangeTrace"):
            self.__onlineChangeTraceTimer.stop()
            self.__onlineChangeTraceTimer.start()

    @pyqtSlot()
    def __onlineChangeTraceTimerTimeout(self):
        """
        Private slot to mark added and changed lines.
        """
        self.__deleteAllChangeMarkers()

        # step 1: mark saved changes
        oldL = self.__oldText.splitlines()
        newL = self.__lastSavedText.splitlines()
        matcher = difflib.SequenceMatcher(None, oldL, newL)

        for token, _, _, j1, j2 in matcher.get_opcodes():
            if token in ["insert", "replace"]:
                for lineNo in range(j1, j2):
                    self.markerAdd(lineNo, self.__changeMarkerSaved)
                    self.__hasChangeMarkers = True

        # step 2: mark unsaved changes
        oldL = self.__lastSavedText.splitlines()
        newL = self.text().splitlines()
        matcher = difflib.SequenceMatcher(None, oldL, newL)

        for token, _, _, j1, j2 in matcher.get_opcodes():
            if token in ["insert", "replace"]:
                for lineNo in range(j1, j2):
                    self.markerAdd(lineNo, self.__changeMarkerUnsaved)
                    self.__hasChangeMarkers = True

        if self.__hasChangeMarkers:
            self.changeMarkersUpdated.emit(self)
            self.__markerMap.update()

    @pyqtSlot()
    def resetOnlineChangeTraceInfo(self):
        """
        Public slot to reset the online change trace info.
        """
        self.__lastSavedText = self.text()
        self.__deleteAllChangeMarkers()

        # mark saved changes
        oldL = self.__oldText.splitlines()
        newL = self.__lastSavedText.splitlines()
        matcher = difflib.SequenceMatcher(None, oldL, newL)

        for token, _, _, j1, j2 in matcher.get_opcodes():
            if token in ["insert", "replace"]:
                for lineNo in range(j1, j2):
                    self.markerAdd(lineNo, self.__changeMarkerSaved)
                    self.__hasChangeMarkers = True

        if self.__hasChangeMarkers:
            self.changeMarkersUpdated.emit(self)
            self.__markerMap.update()

    @pyqtSlot()
    def __deleteAllChangeMarkers(self):
        """
        Private slot to delete all change markers.
        """
        self.markerDeleteAll(self.__changeMarkerUnsaved)
        self.markerDeleteAll(self.__changeMarkerSaved)
        self.__hasChangeMarkers = False
        self.changeMarkersUpdated.emit(self)
        self.__markerMap.update()

    def clearChangeMarkers(self):
        """
        Public method to clear all change markers.
        """
        self.__reinitOnlineChangeTrace()

    def getChangeLines(self):
        """
        Public method to get the lines containing a change.

        @return list of lines containing a change
        @rtype list of int
        """
        lines = []
        line = -1
        while True:
            line = self.markerFindNext(line + 1, self.changeMarkersMask)
            if line < 0:
                break
            else:
                lines.append(line)
        return lines

    def hasChangeMarkers(self):
        """
        Public method to determine, if this editor contains any change markers.

        @return flag indicating the presence of change markers
        @rtype bool
        """
        return self.__hasChangeMarkers

    @pyqtSlot()
    def nextChange(self):
        """
        Public slot to handle the 'Next change' context menu action.
        """
        line, index = self.getCursorPosition()
        if line == self.lines() - 1:
            line = 0
        else:
            line += 1
        changeline = self.markerFindNext(line, self.changeMarkersMask)
        if changeline < 0:
            # wrap around
            changeline = self.markerFindNext(0, self.changeMarkersMask)
        if changeline >= 0:
            self.setCursorPosition(changeline, 0)
            self.ensureLineVisible(changeline)

    @pyqtSlot()
    def previousChange(self):
        """
        Public slot to handle the 'Previous change' context menu action.
        """
        line, index = self.getCursorPosition()
        if line == 0:
            line = self.lines() - 1
        else:
            line -= 1
        changeline = self.markerFindPrevious(line, self.changeMarkersMask)
        if changeline < 0:
            # wrap around
            changeline = self.markerFindPrevious(
                self.lines() - 1, self.changeMarkersMask
            )
        if changeline >= 0:
            self.setCursorPosition(changeline, 0)
            self.ensureLineVisible(changeline)

    ###########################################################################
    ## Flags handling methods below
    ###########################################################################

    def __processFlags(self):
        """
        Private method to extract flags and process them.

        @return list of change flags
        @rtype list of str
        """
        txt = self.text()
        flags = Utilities.extractFlags(txt)

        changedFlags = []

        # Flag 1: FileType
        if "FileType" in flags:
            oldFiletype = self.filetype
            if isinstance(flags["FileType"], str):
                self.filetype = flags["FileType"]
                self.filetypeByFlag = True
                if oldFiletype != self.filetype:
                    changedFlags.append("FileType")
        else:
            if self.filetype != "" and self.filetypeByFlag:
                self.filetype = ""
                self.filetypeByFlag = False
                self.__bindName(txt.splitlines()[0])
                changedFlags.append("FileType")

        return changedFlags

    ###########################################################################
    ## File handling methods below
    ###########################################################################

    def checkDirty(self):
        """
        Public method to check dirty status and open a message window.

        @return flag indicating successful reset of the dirty flag
        @rtype bool
        """
        if self.isModified():
            fn = self.fileName
            if fn is None:
                fn = self.noName
            res = EricMessageBox.okToClearData(
                self,
                self.tr("File Modified"),
                self.tr("<p>The file <b>{0}</b> has unsaved changes.</p>").format(fn),
                self.saveFile,
            )
            if res:
                self.vm.setEditorName(self, self.fileName)
            return res

        return True

    def revertToUnmodified(self):
        """
        Public method to revert back to the last saved state.
        """
        undo_ = True
        while self.isModified():
            if undo_:
                # try undo first
                if self.isUndoAvailable():
                    self.undo()
                else:
                    undo_ = False
            else:
                # try redo next
                if self.isRedoAvailable():
                    self.redo()
                else:
                    break
                    # Couldn't find the unmodified state

    def readFile(self, fn, createIt=False, encoding="", noempty=False, isRemote=False):
        """
        Public method to read the text from a file.

        @param fn filename to read from
        @type str
        @param createIt flag indicating the creation of a new file, if the
            given one doesn't exist (defaults to False)
        @type bool (optional)
        @param encoding encoding to be used to read the file (defaults to "")
            (Note: this parameter overrides encoding detection)
        @type str (optional)
        @param noempty flag indicating to not set an empty text (defaults to False)
        @type bool (optional)
        @param isRemote flag indicating a remote file (defaults to False)
        @type bool (optional)
        """
        if FileSystemUtilities.isPlainFileName(fn):
            self.__loadEditorConfig(fileName=fn)

        try:
            with EricOverrideCursor():
                if FileSystemUtilities.isRemoteFileName(fn) or isRemote:
                    title = self.tr("Open Remote File")
                    if encoding:
                        (
                            txt,
                            self.encoding,
                        ) = self.__remotefsInterface.readEncodedFileWithEncoding(
                            fn, encoding, create=True
                        )
                    else:
                        txt, self.encoding = self.__remotefsInterface.readEncodedFile(
                            fn, create=True
                        )
                else:
                    title = self.tr("Open File")
                    if createIt and not os.path.exists(fn):
                        with open(fn, "w"):
                            pass
                    if encoding == "":
                        encoding = self.__getEditorConfig(
                            "DefaultEncoding", nodefault=True
                        )
                    if encoding:
                        txt, self.encoding = Utilities.readEncodedFileWithEncoding(
                            fn, encoding
                        )
                    else:
                        txt, self.encoding = Utilities.readEncodedFile(fn)
        except (OSError, UnicodeDecodeError) as why:
            EricMessageBox.critical(
                self.vm,
                title,
                self.tr(
                    "<p>The file <b>{0}</b> could not be opened.</p>"
                    "<p>Reason: {1}</p>"
                ).format(fn, str(why)),
            )
            raise

        if noempty and not bool(txt):
            return

        with EricOverrideCursor():
            self.setText(txt)
            self.setModified(False)

            # get eric specific flags
            self.__processFlags()

            # perform automatic EOL conversion
            if self.__getEditorConfig(
                "EOLMode", nodefault=True
            ) or Preferences.getEditor("AutomaticEOLConversion"):
                self.convertEols(self.eolMode())
            else:
                fileEol = self.detectEolString(txt)
                self.setEolModeByEolString(fileEol)
                self.__eolChanged()

            self.extractTasks()

            self.recordModificationTime(filename=fn)

    @pyqtSlot()
    def __convertTabs(self):
        """
        Private slot to automatically convert tabulators to spaces upon loading.
        """
        if (
            (not self.__getEditorConfig("TabForIndentation"))
            and Preferences.getEditor("ConvertTabsOnLoad")
            and not (self.lexer_ and self.lexer_.alwaysKeepTabs())
        ):
            self.expandTabs()

    @pyqtSlot()
    def expandTabs(self):
        """
        Public slot to expand tabulators to spaces.
        """
        txt = self.text()
        txtExpanded = txt.expandtabs(self.__getEditorConfig("TabWidth"))
        if txtExpanded != txt:
            self.beginUndoAction()
            self.setText(txtExpanded)
            self.endUndoAction()

            self.setModified(True)

    def __removeTrailingWhitespace(self):
        """
        Private method to remove trailing whitespace.
        """
        searchRE = r"[ \t]+$"  # whitespace at the end of a line

        ok = self.findFirstTarget(searchRE, True, False, False, 0, 0)
        self.beginUndoAction()
        while ok:
            self.replaceTarget("")
            ok = self.findNextTarget()
        self.endUndoAction()

    def writeFile(self, fn, backup=True):
        """
        Public method to write the text to a file.

        @param fn filename to write to
        @type str
        @param backup flag indicating to save a backup
        @type bool
        @return flag indicating success
        @rtype bool
        """
        config = (
            None
            if self.fileName and fn == self.fileName
            else self.__loadEditorConfigObject(fn)
        )

        eol = self.__getEditorConfig("EOLMode", nodefault=True, config=config)
        if eol is not None:
            self.convertEols(eol)

        if self.__getEditorConfig("StripTrailingWhitespace", config=config):
            self.__removeTrailingWhitespace()

        txt = self.text()

        if self.__getEditorConfig("InsertFinalNewline", config=config):
            eol = self.getLineSeparator()
            if eol:
                if len(txt) >= len(eol):
                    if txt[-len(eol) :] != eol:
                        txt += eol
                else:
                    txt += eol

        # create a backup file, if the option is set
        createBackup = backup and Preferences.getEditor("CreateBackupFile")
        if createBackup and FileSystemUtilities.isPlainFileName(fn):
            if os.path.islink(fn):
                fn = os.path.realpath(fn)
            bfn = "{0}~".format(fn)
            try:
                permissions = os.stat(fn).st_mode
                perms_valid = True
            except OSError:
                # if there was an error, ignore it
                perms_valid = False
            with contextlib.suppress(OSError):
                os.remove(bfn)
            with contextlib.suppress(OSError):
                os.rename(fn, bfn)

        # now write text to the file fn
        try:
            editorConfigEncoding = self.__getEditorConfig(
                "DefaultEncoding", nodefault=True, config=config
            )
            if FileSystemUtilities.isPlainFileName(fn):
                title = self.tr("Save File")
                self.encoding = Utilities.writeEncodedFile(
                    fn, txt, self.encoding, forcedEncoding=editorConfigEncoding
                )
                if createBackup and perms_valid:
                    os.chmod(fn, permissions)
            else:
                title = self.tr("Save Remote File")
                self.encoding = self.__remotefsInterface.writeEncodedFile(
                    fn,
                    txt,
                    self.encoding,
                    forcedEncoding=editorConfigEncoding,
                    withBackup=createBackup,
                )
            return True
        except (OSError, UnicodeError, Utilities.CodingError) as why:
            EricMessageBox.critical(
                self,
                title,
                self.tr(
                    "<p>The file <b>{0}</b> could not be saved.<br/>Reason: {1}</p>"
                ).format(fn, str(why)),
            )
            return False

    def __getSaveFileName(self, path=None, remote=False):
        """
        Private method to get the name of the file to be saved.

        @param path directory to save the file in (defaults to None)
        @type str (optional)
        @param remote flag indicating to save as a remote file (defaults to False)
        @type bool (optional)
        @return file name
        @rtype str
        """
        # save to project, if a project is loaded
        if self.project.isOpen():
            if self.fileName and self.project.startswithProjectPath(self.fileName):
                path = os.path.dirname(self.fileName)
            elif not self.fileName:
                path = self.project.getProjectPath()

        if not path and self.fileName:
            path = os.path.dirname(self.fileName)
        if not path:
            if remote:
                path = ""
            else:
                path = (
                    Preferences.getMultiProject("Workspace") or OSUtilities.getHomeDir()
                )

        if self.fileName:
            filterPattern = "(*{0})".format(os.path.splitext(self.fileName)[1])
            for fileFilter in Lexers.getSaveFileFiltersList(True):
                if filterPattern in fileFilter:
                    defaultFilter = fileFilter
                    break
            else:
                defaultFilter = Preferences.getEditor("DefaultSaveFilter")
        else:
            defaultFilter = Preferences.getEditor("DefaultSaveFilter")

        if remote or FileSystemUtilities.isRemoteFileName(path):
            title = self.tr("Save Remote File")
            fn, selectedFilter = EricServerFileDialog.getSaveFileNameAndFilter(
                self,
                title,
                path,
                Lexers.getSaveFileFiltersList(True, True),
                defaultFilter,
            )
        else:
            title = self.tr("Save File")
            fn, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
                self,
                title,
                path,
                Lexers.getSaveFileFiltersList(True, True),
                defaultFilter,
                EricFileDialog.DontConfirmOverwrite,
            )

        if fn:
            if fn.endswith("."):
                fn = fn[:-1]

            fpath = pathlib.Path(fn)
            if not fpath.suffix:
                ex = selectedFilter.split("(*")[1].split(")")[0]
                if ex:
                    fpath = fpath.with_suffix(ex)
            if (
                FileSystemUtilities.isRemoteFileName(str(fpath))
                and self.__remotefsInterface.exists(str(fpath))
            ) or (FileSystemUtilities.isPlainFileName(str(fpath)) and fpath.exists()):
                res = EricMessageBox.yesNo(
                    self,
                    title,
                    self.tr(
                        "<p>The file <b>{0}</b> already exists. Overwrite it?</p>"
                    ).format(fpath),
                    icon=EricMessageBox.Warning,
                )
                if not res:
                    return ""

            return str(fpath)

        return ""

    def saveFileCopy(self, path=None):
        """
        Public method to save a copy of the file.

        @param path directory to save the file in
        @type str
        @return flag indicating success
        @rtype bool
        """
        fn = self.__getSaveFileName(path)
        if not fn:
            return False

        res = self.writeFile(fn)
        if res and self.project.isOpen() and self.project.startswithProjectPath(fn):
            # save to project, if a project is loaded
            self.project.appendFile(fn)

        return res

    def saveFile(self, saveas=False, path=None, remote=False):
        """
        Public method to save the text to a file.

        @param saveas flag indicating a 'save as' action (defaults to False)
        @type bool (optional)
        @param path directory to save the file in (defaults to None)
        @type str (optional)
        @param remote flag indicating to save as a remote file (defaults to False)
        @type bool (optional)
        @return flag indicating success
        @rtype bool
        """
        if not saveas and not self.isModified():
            # do nothing if text was not changed
            return False

        if FileSystemUtilities.isDeviceFileName(self.fileName):
            return self.__saveDeviceFile(saveas=saveas)

        newName = None
        if saveas or self.fileName == "":
            saveas = True

            fn = self.__getSaveFileName(path=path, remote=remote)
            if not fn:
                return False

            newName = fn

            # save to project, if a project is loaded
            if self.project.isOpen() and self.project.startswithProjectPath(fn):
                editorConfigEol = self.__getEditorConfig(
                    "EOLMode", nodefault=True, config=self.__loadEditorConfigObject(fn)
                )
                if editorConfigEol is not None:
                    self.setEolMode(editorConfigEol)
                else:
                    self.setEolModeByEolString(self.project.getEolString())
                self.convertEols(self.eolMode())
        else:
            fn = self.fileName

        self.editorAboutToBeSaved.emit(self.fileName)
        if self.__autosaveTimer.isActive():
            self.__autosaveTimer.stop()
        if self.writeFile(fn):
            if saveas:
                self.__clearBreakpoints(self.fileName)
                self.__loadEditorConfig(fileName=fn)
            self.setFileName(fn)
            self.setModified(False)
            self.setReadOnly(False)
            self.setWindowTitle(self.fileName)
            # get eric specific flags
            changedFlags = self.__processFlags()
            if not self.__lexerReset and "FileType" in changedFlags:
                self.setLanguage(self.fileName)

            if saveas:
                self.isResourcesFile = self.fileName.endswith(".qrc")
                self.__initContextMenu()
                self.editorRenamed.emit(self.fileName)

                # save to project, if a project is loaded
                if self.project.isOpen() and self.project.startswithProjectPath(fn):
                    self.project.appendFile(fn)
                    self.addedToProject()

                self.setLanguage(self.fileName)

            self.recordModificationTime()
            if newName is not None:
                self.vm.addToRecentList(newName)
            self.editorSaved.emit(self.fileName)
            self.checkSyntax()
            self.extractTasks()
            self.resetOnlineChangeTraceInfo()
            self.__checkEncoding()
            return True
        else:
            self.recordModificationTime(filename=fn)
            return False

    def saveFileAs(self, path=None, remote=False):
        """
        Public method to save a file with a new name.

        @param path directory to save the file in (defaults to None)
        @type str (optional)
        @param remote flag indicating to save as a remote file (defaults to False)
        @type bool (optional)
        @return tuple containing a success indicator and the name of the saved file
        @rtype tuple of (bool, str)
        """
        return self.saveFile(True, path=path, remote=remote)

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
                    self.fileName,
                )
                if not ok or not fn:
                    # aborted
                    return False
            else:
                fn = self.fileName
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
                self.setFileName(fn)
                self.setModified(False)
                self.resetOnlineChangeTraceInfo()
            return success

        return False

    def handleRenamed(self, fn):
        """
        Public method to handle the editorRenamed signal.

        @param fn filename to be set for the editor
        @type str
        """
        self.__clearBreakpoints(fn)

        self.setFileName(fn)
        self.setWindowTitle(self.fileName)

        self.__loadEditorConfig()

        if self.lexer_ is None:
            self.setLanguage(self.fileName)

        self.recordModificationTime()
        self.vm.setEditorName(self, self.fileName)
        self.__updateReadOnly(True)

    @pyqtSlot(str)
    def fileRenamed(self, fn):
        """
        Public slot to handle the editorRenamed signal.

        @param fn filename to be set for the editor
        @type str.
        """
        self.handleRenamed(fn)
        if not self.inFileRenamed:
            self.inFileRenamed = True
            self.editorRenamed.emit(self.fileName)
            self.inFileRenamed = False

    ###########################################################################
    ## Utility methods below
    ###########################################################################

    def ensureVisible(self, line, expand=False):
        """
        Public method to ensure, that the specified line is visible.

        @param line line number to make visible
        @type int
        @param expand flag indicating to expand all folds
        @type bool
        """
        self.ensureLineVisible(line - 1)
        if expand:
            self.SendScintilla(
                QsciScintilla.SCI_FOLDCHILDREN,
                line - 1,
                QsciScintilla.SC_FOLDACTION_EXPAND,
            )

    def ensureVisibleTop(self, line, expand=False):
        """
        Public method to ensure, that the specified line is visible at the top
        of the editor.

        @param line line number to make visible
        @type int
        @param expand flag indicating to expand all folds
        @type bool
        """
        self.ensureVisible(line)
        self.setFirstVisibleLine(line - 1)
        self.ensureCursorVisible()
        if expand:
            self.SendScintilla(
                QsciScintilla.SCI_FOLDCHILDREN,
                line - 1,
                QsciScintilla.SC_FOLDACTION_EXPAND,
            )

    def __marginClicked(self, margin, line, _modifiers):
        """
        Private slot to handle the marginClicked signal.

        @param margin id of the clicked margin
        @type int
        @param line line number of the click
        @type int
        @param _modifiers keyboard modifiers (unused)
        @type Qt.KeyboardModifiers
        """
        if margin == self.__bmMargin:
            self.toggleBookmark(line + 1)
        elif margin == self.__bpMargin:
            self.__toggleBreakpoint(line + 1)
        elif margin == self.__indicMargin:
            if self.markersAtLine(line) & (1 << self.syntaxerror):
                self.__showSyntaxError(line)
            elif self.markersAtLine(line) & (1 << self.warning):
                self.__showWarning(line)

    @pyqtSlot(int, int, int)
    def __marginHoverStart(self, pos, x, y):
        """
        Private slot showing the text of a syntax error or a warning marker.

        @param pos mouse position into the document
        @type int
        @param x x-value of mouse screen position
        @type int
        @param y y-value of mouse screen position
        @type int
        """
        margin = self.__marginNumber(x)
        if margin == self.__indicMargin:
            # determine width of all margins; needed to calculate document line
            width = 0
            for margin in range(5):
                width += self.marginWidth(margin)

            message = ""
            line = self.lineIndexFromPoint(QPoint(width + 1, y))[0]
            if self.markersAtLine(line) & (1 << self.syntaxerror):
                for handle in self.syntaxerrors:
                    if self.markerLine(handle) == line:
                        message = "\n".join([e[0] for e in self.syntaxerrors[handle]])
                        break
            elif self.markersAtLine(line) & (1 << self.warning):
                for handle in self._warnings:
                    if self.markerLine(handle) == line:
                        message = "\n".join([w[0] for w in self._warnings[handle]])
                        break

            if message:
                QToolTip.showText(QCursor.pos(), message)

    @pyqtSlot()
    def __marginHoverEnd(self):
        """
        Private slot cancelling the display of syntax error or a warning marker text.
        """
        QToolTip.hideText()

    @pyqtSlot()
    def handleMonospacedEnable(self):
        """
        Public slot to handle the Use Monospaced Font context menu entry.
        """
        if self.menuActs["MonospacedFont"].isChecked():
            if not self.lexer_:
                self.setMonospaced(True)
        else:
            if self.lexer_:
                self.lexer_.readSettings(Preferences.getSettings(), "Scintilla")
                if self.lexer_.hasSubstyles():
                    self.lexer_.readSubstyles(self)
                self.lexer_.initProperties()
            self.setMonospaced(False)
            self.__setMarginsDisplay()

    def getWordBoundaries(self, line, index, useWordChars=True, forCompletion=False):
        """
        Public method to get the word boundaries at a position.

        @param line number of line to look at
        @type int
        @param index position to look at
        @type int
        @param useWordChars flag indicating to use the wordCharacters
            method (defaults to True)
        @type bool (optional)
        @param forCompletion flag indicating a modification for completions (defaults
            to False)
        @type bool (optional)
        @return tuple with start and end indexes of the word at the position
        @rtype tuple of (int, int)
        """
        wc = self.wordCharacters()
        if wc is None or not useWordChars:
            pattern = r"\b[\w_]+\b"
        else:
            wc = re.sub(r"\w", "", wc)
            pattern = r"\b[\w{0}]+\b".format(re.escape(wc))
        if forCompletion:
            pattern += "=?"
        rx = (
            re.compile(pattern)
            if self.caseSensitive()
            else re.compile(pattern, re.IGNORECASE)
        )

        text = self.text(line)
        for match in rx.finditer(text):
            start, end = match.span()
            if start <= index <= end:
                return (start, end)

        return (index, index)

    def getWord(self, line, index, direction=0, useWordChars=True, forCompletion=False):
        """
        Public method to get the word at a position.

        @param line number of line to look at
        @type int
        @param index position to look at
        @type int
        @param direction direction to look in (0 = whole word, 1 = left,
            2 = right)
        @type int
        @param useWordChars flag indicating to use the wordCharacters
            method (defaults to True)
        @type bool (optional)
        @param forCompletion flag indicating a modification for completions (defaults
            to False)
        @type bool (optional)
        @return the word at that position
        @rtype str
        """
        start, end = self.getWordBoundaries(
            line, index, useWordChars=useWordChars, forCompletion=forCompletion
        )
        if direction == 1:
            end = index
        elif direction == 2:
            start = index
        if end > start:
            text = self.text(line)
            word = text[start:end]
        else:
            word = ""
        return word

    def getWordLeft(self, line, index):
        """
        Public method to get the word to the left of a position.

        @param line number of line to look at
        @type int
        @param index position to look at
        @type int
        @return the word to the left of that position
        @rtype str
        """
        return self.getWord(line, index, 1)

    def getWordRight(self, line, index):
        """
        Public method to get the word to the right of a position.

        @param line number of line to look at
        @type int
        @param index position to look at
        @type int
        @return the word to the right of that position
        @rtype str
        """
        return self.getWord(line, index, 2)

    def getCurrentWord(self):
        """
        Public method to get the word at the current position.

        @return the word at that current position
        @rtype str
        """
        line, index = self.getCursorPosition()
        return self.getWord(line, index)

    def getCurrentWordBoundaries(self):
        """
        Public method to get the word boundaries at the current position.

        @return tuple with start and end indexes of the current word
        @rtype tuple of (int, int)
        """
        line, index = self.getCursorPosition()
        return self.getWordBoundaries(line, index)

    def selectWord(self, line, index):
        """
        Public method to select the word at a position.

        @param line number of line to look at
        @type int
        @param index position to look at
        @type int
        """
        start, end = self.getWordBoundaries(line, index)
        self.setSelection(line, start, line, end)

    def selectCurrentWord(self):
        """
        Public method to select the current word.
        """
        line, index = self.getCursorPosition()
        self.selectWord(line, index)

    def __getCharacter(self, pos):
        """
        Private method to get the character to the left of the current position
        in the current line.

        @param pos position to get character at
        @type int
        @return requested character or "", if there are no more and the next position
            (i.e. pos - 1)
        @rtype tuple of (str, int)
        """
        if pos <= 0:
            return "", pos

        pos = self.positionBefore(pos)
        ch = self.charAt(pos)

        # Don't go past the end of the previous line
        if ch in ("\n", "\r"):
            return "", pos

        return ch, pos

    def getSearchText(self, selectionOnly=False):
        """
        Public method to determine the selection or the current word for the
        next search operation.

        @param selectionOnly flag indicating that only selected text should be
            returned
        @type bool
        @return selection or current word
        @rtype str
        """
        if self.hasSelectedText():
            text = self.selectedText()
            if "\r" in text or "\n" in text:
                # the selection contains at least a newline, it is
                # unlikely to be the expression to search for
                return ""

            return text

        if not selectionOnly:
            # no selected text, determine the word at the current position
            return self.getCurrentWord()

        return ""

    def setSearchIndicator(self, startPos, indicLength):
        """
        Public method to set a search indicator for the given range.

        @param startPos start position of the indicator
        @type int
        @param indicLength length of the indicator
        @type int
        """
        self.setIndicatorRange(self.searchIndicator, startPos, indicLength)
        line = self.lineIndexFromPosition(startPos)[0]
        if line not in self.__searchIndicatorLines:
            self.__searchIndicatorLines.append(line)

    def clearSearchIndicators(self):
        """
        Public method to clear all search indicators.
        """
        self.clearAllIndicators(self.searchIndicator)
        self.__markedText = ""
        self.__searchIndicatorLines = []
        self.__markerMap.update()

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
        self.setIndicator(
            self.searchSelectionIndicator, startLine, startIndex, endLine, endIndex
        )

    def getSearchSelectionHighlight(self):
        """
        Public method to get the start and end of the selection highlight.

        @return tuple containing the start line and index and the end line and index
        @rtype tuple of (int, int, int, int)
        """
        return self.getIndicator(self.searchSelectionIndicator)

    def clearSearchSelectionHighlight(self):
        """
        Public method to clear all highlights.
        """
        self.clearAllIndicators(self.searchSelectionIndicator)

    def __markOccurrences(self):
        """
        Private method to mark all occurrences of the current word.
        """
        word = self.getCurrentWord()
        if not word:
            self.clearSearchIndicators()
            return

        if self.__markedText == word:
            return

        self.clearSearchIndicators()
        ok = self.findFirstTarget(word, False, self.caseSensitive(), True, 0, 0)
        while ok:
            tgtPos, tgtLen = self.getFoundTarget()
            self.setSearchIndicator(tgtPos, tgtLen)
            ok = self.findNextTarget()
        self.__markedText = word
        self.__markerMap.update()

    def getSearchIndicatorLines(self):
        """
        Public method to get the lines containing a search indicator.

        @return list of lines containing a search indicator
        @rtype list of int
        """
        return self.__searchIndicatorLines[:]

    def updateMarkerMap(self):
        """
        Public method to initiate an update of the marker map.
        """
        self.__markerMap.update()

    ###########################################################################
    ## Highlighting marker handling methods below
    ###########################################################################

    def setHighlight(self, startLine, startIndex, endLine, endIndex):
        """
        Public method to set a text highlight.

        @param startLine line of the highlight start
        @type int
        @param startIndex index of the highlight start
        @type int
        @param endLine line of the highlight end
        @type int
        @param endIndex index of the highlight end
        @type int
        """
        self.setIndicator(
            self.highlightIndicator, startLine, startIndex, endLine, endIndex
        )

    def clearAllHighlights(self):
        """
        Public method to clear all highlights.
        """
        self.clearAllIndicators(self.highlightIndicator)

    def clearHighlight(self, startLine, startIndex, endLine, endIndex):
        """
        Public method to clear a text highlight.

        @param startLine line of the highlight start
        @type int
        @param startIndex index of the highlight start
        @type int
        @param endLine line of the highlight end
        @type int
        @param endIndex index of the highlight end
        @type int
        """
        self.clearIndicator(
            self.highlightIndicator, startLine, startIndex, endLine, endIndex
        )

    ###########################################################################
    ## Comment handling methods below
    ###########################################################################

    def __isCommentedLine(self, line, commentStr):
        """
        Private method to check, if the given line is a comment line as
        produced by the configured comment rules.

        @param line text of the line to check
        @type str
        @param commentStr comment string to check against
        @type str
        @return flag indicating a commented line
        @rtype bool
        """
        if Preferences.getEditor("CommentColumn0"):
            return line.startswith(commentStr)
        else:
            return line.strip().startswith(commentStr)

    @pyqtSlot()
    def toggleComment(self):
        """
        Public slot to toggle a block or stream comment.

        If the lexer supports a block comment, that is used for toggling the
        comment. Otherwise a stream comment is used if that is supported. If
        none of these are supported, the request is ignored silently.
        """
        if self.lexer_ is not None:
            if self.lexer_.canBlockComment():
                self.__toggleBlockComment()
            elif self.lexer_.canStreamComment():
                self.__toggleStreamComment()

    @pyqtSlot()
    def __toggleBlockComment(self):
        """
        Private slot to toggle the comment of a block.

        If the editor contains selected text and the start line is not commented, it
        will be commented. Otherwise the selection will be un-commented. In case there
        is no selected text and the current line is not commented, it will be commented.
        If is commented, the comment block will be removed.
        """
        if self.lexer_ is None or not self.lexer_.canBlockComment():
            return

        commentStr = self.lexer_.commentStr()
        line, index = self.getCursorPosition()

        if self.hasSelectedText():
            # Check if the selection starts with our comment string (i.e. was commented
            # by our comment...() slots.
            if self.__isCommentedLine(self.text(self.getSelection()[0]), commentStr):
                self.uncommentLineOrSelection()
            else:
                self.commentLineOrSelection()
        elif not self.__isCommentedLine(self.text(line), commentStr):
            # No selected text and the current line does not start with our comment
            # string, so comment the line.
            self.commentLineOrSelection()
        else:
            # Uncomment the comment block containing the current line.
            # 1. determine the start of the comment block
            begline = line
            while begline > 0 and self.__isCommentedLine(
                self.text(begline - 1), commentStr
            ):
                begline -= 1
            # 2. determine the end of the comment block
            endline = line
            lines = self.lines()
            while endline < lines and self.__isCommentedLine(
                self.text(endline + 1), commentStr
            ):
                endline += 1

            # 3. uncomment the determined block and reset the cursor position
            self.setSelection(begline, 0, endline, self.lineLength(endline))
            self.uncommentLineOrSelection()
            self.setCursorPosition(line, index - len(commentStr))

    @pyqtSlot()
    def __commentLine(self):
        """
        Private slot to comment the current line.
        """
        if self.lexer_ is None or not self.lexer_.canBlockComment():
            return

        line, index = self.getCursorPosition()
        self.beginUndoAction()
        if Preferences.getEditor("CommentColumn0"):
            self.insertAt(self.lexer_.commentStr(), line, 0)
        else:
            lineText = self.text(line)
            pos = len(lineText.replace(lineText.lstrip(" \t"), ""))
            self.insertAt(self.lexer_.commentStr(), line, pos)
        self.endUndoAction()

    @pyqtSlot()
    def __uncommentLine(self):
        """
        Private slot to uncomment the current line.
        """
        if self.lexer_ is None or not self.lexer_.canBlockComment():
            return

        commentStr = self.lexer_.commentStr()
        line, index = self.getCursorPosition()

        # check if line starts with our comment string (i.e. was commented
        # by our comment...() slots
        if not self.__isCommentedLine(self.text(line), commentStr):
            return

        # now remove the comment string
        self.beginUndoAction()
        if Preferences.getEditor("CommentColumn0"):
            self.setSelection(line, 0, line, len(commentStr))
        else:
            lineText = self.text(line)
            pos = len(lineText.replace(lineText.lstrip(" \t"), ""))
            self.setSelection(line, pos, line, pos + len(commentStr))
        self.removeSelectedText()
        self.endUndoAction()

    @pyqtSlot()
    def __commentSelection(self):
        """
        Private slot to comment the current selection.
        """
        if self.lexer_ is None or not self.lexer_.canBlockComment():
            return

        if not self.hasSelectedText():
            return

        commentStr = self.lexer_.commentStr()

        # get the selection boundaries
        lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
        endLine = lineTo if indexTo else lineTo - 1

        self.beginUndoAction()
        # iterate over the lines
        for line in range(lineFrom, endLine + 1):
            if Preferences.getEditor("CommentColumn0"):
                self.insertAt(commentStr, line, 0)
            else:
                lineText = self.text(line)
                pos = len(lineText.replace(lineText.lstrip(" \t"), ""))
                self.insertAt(commentStr, line, pos)

        # change the selection accordingly
        self.setSelection(lineFrom, 0, endLine + 1, 0)
        self.endUndoAction()

    @pyqtSlot()
    def __uncommentSelection(self):
        """
        Private slot to uncomment the current selection.
        """
        if self.lexer_ is None or not self.lexer_.canBlockComment():
            return

        if not self.hasSelectedText():
            return

        commentStr = self.lexer_.commentStr()

        # get the selection boundaries
        lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
        endLine = lineTo if indexTo else lineTo - 1

        self.beginUndoAction()
        # iterate over the lines
        for line in range(lineFrom, endLine + 1):
            # check if line starts with our comment string (i.e. was commented
            # by our comment...() slots
            if not self.__isCommentedLine(self.text(line), commentStr):
                continue

            if Preferences.getEditor("CommentColumn0"):
                self.setSelection(line, 0, line, len(commentStr))
            else:
                lineText = self.text(line)
                pos = len(lineText.replace(lineText.lstrip(" \t"), ""))
                self.setSelection(line, pos, line, pos + len(commentStr))
            self.removeSelectedText()

            # adjust selection start
            if line == lineFrom:
                indexFrom -= len(commentStr)
                if indexFrom < 0:
                    indexFrom = 0

            # adjust selection end
            if line == lineTo:
                indexTo -= len(commentStr)
                if indexTo < 0:
                    indexTo = 0

        # change the selection accordingly
        self.setSelection(lineFrom, indexFrom, lineTo, indexTo)
        self.endUndoAction()

    @pyqtSlot()
    def commentLineOrSelection(self):
        """
        Public slot to comment the current line or current selection.

        If the lexer supports a block comment, that is used for commenting.
        Otherwise a stream comment is used if that is supported. If none of
        these are supported, the request is ignored silently.
        """
        if self.lexer_ is not None:
            if self.lexer_.canBlockComment():
                if self.hasSelectedText():
                    self.__commentSelection()
                else:
                    self.__commentLine()
            elif self.lexer_.canStreamComment():
                # delegate to the stream comment method
                self.streamCommentLineOrSelection()

    @pyqtSlot()
    def uncommentLineOrSelection(self):
        """
        Public slot to uncomment the current line or current selection.

        If the lexer supports a block comment, that is used for uncommenting.
        Otherwise a stream comment is used if that is supported. If none of
        these are supported, the request is ignored silently.
        """
        if self.lexer_ is not None:
            if self.lexer_.canBlockComment():
                if self.hasSelectedText():
                    self.__uncommentSelection()
                else:
                    self.__uncommentLine()
            elif self.lexer_.canStreamComment():
                # delegate to the stream uncomment method
                self.streamUncommentLineOrSelection()

    def __isStreamCommentedLine(self, line, streamCommentStr):
        """
        Private method to check, if the line is commented by a stream comment.

        @param line text of the line to check
        @type str
        @param streamCommentStr dictionary containing the stream comment start and
            end strings
        @type dict
        @return flag indicating a stream commented line
        @rtype bool
        """
        line = line.strip()
        return line.startswith(streamCommentStr["start"]) and line.endswith(
            streamCommentStr["end"]
        )

    @pyqtSlot()
    def __toggleStreamComment(self):
        """
        Private slot to toggle the comment of a block.

        If the editor contains selected text and the start line is not commented, it
        will be commented. Otherwise the selection will be un-commented. In case there
        is no selected text and the current line is not commented, it will be commented.
        If is commented, the comment block will be removed.
        """
        if self.lexer_ is None or not self.lexer_.canStreamComment():
            return

        streamCommentStr = self.lexer_.streamCommentStr()
        line, index = self.getCursorPosition()

        if self.hasSelectedText():
            # Check if the selection starts with a stream comment string.
            if self.text(self.getSelection()[0]).startswith(streamCommentStr["start"]):
                self.streamUncommentLineOrSelection()
            else:
                self.streamCommentLineOrSelection()
        elif self.__isStreamCommentedLine(self.text(line), streamCommentStr):
            # It is a stream commented line.
            self.streamUncommentLineOrSelection()
        elif self.text(line).lstrip(" \t").startswith(streamCommentStr["start"]):
            # The cursor is at the first line of a stream comment.
            pos = len(self.text(line).replace(self.text(line).lstrip(" \t"), ""))
            endline = line
            lines = self.lines()
            while endline < lines and not self.text(endline).rstrip().endswith(
                streamCommentStr["end"]
            ):
                endline += 1

            # Uncomment the determined block and reset the cursor position
            self.setSelection(line, pos, endline, self.lineLength(endline))
            self.uncommentLineOrSelection()
            self.setCursorPosition(line, index - len(streamCommentStr["start"]))
        elif self.text(line).rstrip().endswith(streamCommentStr["end"]):
            # The cursor is at the last line of a stream comment.
            begline = line
            while begline > 0 and not self.text(begline).lstrip(" \t").startswith(
                streamCommentStr["start"]
            ):
                begline -= 1
            pos = len(self.text(begline).replace(self.text(begline).lstrip(" \t"), ""))

            # Uncomment the determined block and reset the cursor position
            self.setSelection(begline, pos, line, self.lineLength(line))
            self.uncommentLineOrSelection()
            self.setCursorPosition(
                line, min(index, self.lineLength(line) - len(self.getLineSeparator()))
            )
        else:
            # No selected text and the current line does not start with a stream comment
            # string, so comment the line.
            self.streamCommentLineOrSelection()

    @pyqtSlot()
    def __streamCommentLine(self):
        """
        Private slot to stream comment the current line.
        """
        if self.lexer_ is None or not self.lexer_.canStreamComment():
            return

        streamCommentStr = self.lexer_.streamCommentStr()
        line, index = self.getCursorPosition()

        self.beginUndoAction()
        self.insertAt(
            streamCommentStr["end"],
            line,
            self.lineLength(line) - len(self.getLineSeparator()),
        )
        self.insertAt(streamCommentStr["start"], line, 0)
        self.endUndoAction()

    @pyqtSlot()
    def __streamCommentSelection(self):
        """
        Private slot to comment the current selection.
        """
        if self.lexer_ is None or not self.lexer_.canStreamComment():
            return

        if not self.hasSelectedText():
            return

        streamCommentStr = self.lexer_.streamCommentStr()

        # get the selection boundaries
        lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
        if indexTo == 0:
            endLine = lineTo - 1
            endIndex = self.lineLength(endLine) - len(self.getLineSeparator())
        else:
            endLine = lineTo
            endIndex = indexTo

        self.beginUndoAction()
        self.insertAt(streamCommentStr["end"], endLine, endIndex)
        self.insertAt(streamCommentStr["start"], lineFrom, indexFrom)

        # change the selection accordingly
        if indexTo > 0:
            indexTo += len(streamCommentStr["end"])
            if lineFrom == endLine:
                indexTo += len(streamCommentStr["start"])
        self.setSelection(lineFrom, indexFrom, lineTo, indexTo)
        self.endUndoAction()

    @pyqtSlot()
    def __streamUncommentLine(self):
        """
        Private slot to stream uncomment the current line.
        """
        if self.lexer_ is None or not self.lexer_.canStreamComment():
            return

        streamCommentStr = self.lexer_.streamCommentStr()
        line, index = self.getCursorPosition()

        # check if line starts and ends with the stream comment strings
        if not self.__isStreamCommentedLine(self.text(line), streamCommentStr):
            return

        self.beginUndoAction()
        # 1. remove comment end string
        self.setSelection(
            line,
            self.lineLength(line)
            - len(self.getLineSeparator())
            - len(streamCommentStr["end"]),
            line,
            self.lineLength(line) - len(self.getLineSeparator()),
        )
        self.removeSelectedText()

        # 2. remove comment start string
        lineText = self.text(line)
        pos = len(lineText.replace(lineText.lstrip(" \t"), ""))
        self.setSelection(line, pos, line, pos + len(streamCommentStr["start"]))
        self.removeSelectedText()
        self.endUndoAction()

    @pyqtSlot()
    def __streamUncommentSelection(self):
        """
        Private slot to stream uncomment the current selection.
        """
        if self.lexer_ is None or not self.lexer_.canStreamComment():
            return

        if not self.hasSelectedText():
            return

        streamCommentStr = self.lexer_.streamCommentStr()

        # get the selection boundaries
        lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
        if indexTo == 0:
            endLine = lineTo - 1
            endIndex = self.lineLength(endLine) - len(self.getLineSeparator())
        else:
            endLine = lineTo
            endIndex = indexTo

        self.beginUndoAction()
        self.setSelection(lineFrom, indexFrom, endLine, endIndex)
        selTxt = self.selectedText()
        if selTxt.endswith(streamCommentStr["end"]):
            self.setSelection(
                endLine, endIndex - len(streamCommentStr["end"]), endLine, endIndex
            )
            self.removeSelectedText()

            # modify selection end accordingly
            if indexTo > 0:
                indexTo -= len(streamCommentStr["end"])
        if selTxt.startswith(streamCommentStr["start"]):
            self.setSelection(
                lineFrom,
                indexFrom,
                lineFrom,
                indexFrom + len(streamCommentStr["start"]),
            )
            self.removeSelectedText()

            # modify selection end accordingly
            if lineFrom == lineTo and indexTo > 0:
                indexTo -= len(streamCommentStr["start"])
        self.endUndoAction()

        # now set the new selection
        self.setSelection(lineFrom, indexFrom, lineTo, indexTo)

    @pyqtSlot()
    def streamCommentLineOrSelection(self):
        """
        Public slot to stream comment the current line or current selection.
        """
        if self.hasSelectedText():
            self.__streamCommentSelection()
        else:
            self.__streamCommentLine()

    @pyqtSlot()
    def streamUncommentLineOrSelection(self):
        """
        Public slot to stream uncomment the current line or current selection.
        """
        if self.hasSelectedText():
            self.__streamUncommentSelection()
        else:
            self.__streamUncommentLine()

    @pyqtSlot()
    def __boxCommentLine(self):
        """
        Private slot to box comment the current line.
        """
        if self.lexer_ is None or not self.lexer_.canBoxComment():
            return

        boxCommentStr = self.lexer_.boxCommentStr()
        line, index = self.getCursorPosition()

        eol = self.getLineSeparator()
        self.beginUndoAction()
        self.insertAt(eol, line, self.lineLength(line))
        self.insertAt(boxCommentStr["end"], line + 1, 0)
        self.insertAt(boxCommentStr["middle"], line, 0)
        self.insertAt(eol, line, 0)
        self.insertAt(boxCommentStr["start"], line, 0)
        self.endUndoAction()

    @pyqtSlot()
    def __boxCommentSelection(self):
        """
        Private slot to box comment the current selection.
        """
        if self.lexer_ is None or not self.lexer_.canBoxComment():
            return

        if not self.hasSelectedText():
            return

        boxCommentStr = self.lexer_.boxCommentStr()

        # get the selection boundaries
        lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
        endLine = lineTo if indexTo else lineTo - 1

        self.beginUndoAction()
        # iterate over the lines
        for line in range(lineFrom, endLine + 1):
            self.insertAt(boxCommentStr["middle"], line, 0)

        # now do the comments before and after the selection
        eol = self.getLineSeparator()
        self.insertAt(eol, endLine, self.lineLength(endLine))
        self.insertAt(boxCommentStr["end"], endLine + 1, 0)
        self.insertAt(eol, lineFrom, 0)
        self.insertAt(boxCommentStr["start"], lineFrom, 0)

        # change the selection accordingly
        self.setSelection(lineFrom, 0, endLine + 3, 0)
        self.endUndoAction()

    @pyqtSlot()
    def boxCommentLineOrSelection(self):
        """
        Public slot to box comment the current line or current selection.
        """
        if self.hasSelectedText():
            self.__boxCommentSelection()
        else:
            self.__boxCommentLine()

    ###########################################################################
    ## Indentation handling methods below
    ###########################################################################

    def __indentLine(self, indent=True):
        """
        Private method to indent or unindent the current line.

        @param indent flag indicating an indent operation
            <br />If the flag is true, an indent operation is performed.
            Otherwise the current line is unindented.
        @type bool
        """
        line, index = self.getCursorPosition()
        self.beginUndoAction()
        if indent:
            self.indent(line)
        else:
            self.unindent(line)
        self.endUndoAction()
        if indent:
            self.setCursorPosition(line, index + self.indentationWidth())
        else:
            self.setCursorPosition(line, index - self.indentationWidth())

    def __indentSelection(self, indent=True):
        """
        Private method to indent or unindent the current selection.

        @param indent flag indicating an indent operation
            <br />If the flag is true, an indent operation is performed.
            Otherwise the current line is unindented.
        @type bool
        """
        if not self.hasSelectedText():
            return

        # get the selection
        lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
        endLine = lineTo if indexTo else lineTo - 1

        self.beginUndoAction()
        # iterate over the lines
        for line in range(lineFrom, endLine + 1):
            if indent:
                self.indent(line)
            else:
                self.unindent(line)
        self.endUndoAction()
        if indent:
            if indexTo == 0:
                self.setSelection(
                    lineFrom, indexFrom + self.indentationWidth(), lineTo, 0
                )
            else:
                self.setSelection(
                    lineFrom,
                    indexFrom + self.indentationWidth(),
                    lineTo,
                    indexTo + self.indentationWidth(),
                )
        else:
            indexStart = indexFrom - self.indentationWidth()
            if indexStart < 0:
                indexStart = 0
            indexEnd = indexTo - self.indentationWidth()
            if indexEnd < 0:
                indexEnd = 0
            self.setSelection(lineFrom, indexStart, lineTo, indexEnd)

    @pyqtSlot()
    def indentLineOrSelection(self):
        """
        Public slot to indent the current line or current selection.
        """
        if self.hasSelectedText():
            self.__indentSelection(True)
        else:
            self.__indentLine(True)

    @pyqtSlot()
    def unindentLineOrSelection(self):
        """
        Public slot to unindent the current line or current selection.
        """
        if self.hasSelectedText():
            self.__indentSelection(False)
        else:
            self.__indentLine(False)

    @pyqtSlot()
    def smartIndentLineOrSelection(self):
        """
        Public slot to indent current line smartly.
        """
        if self.hasSelectedText():
            if self.lexer_ and self.lexer_.hasSmartIndent():
                self.lexer_.smartIndentSelection(self)
            else:
                self.__indentSelection(True)
        else:
            if self.lexer_ and self.lexer_.hasSmartIndent():
                self.lexer_.smartIndentLine(self)
            else:
                self.__indentLine(True)

    def gotoLine(self, line, pos=1, firstVisible=False, expand=False):
        """
        Public method to jump to the beginning of a line.

        @param line line number to go to
        @type int
        @param pos position in line to go to
        @type int
        @param firstVisible flag indicating to make the line the first
            visible line
        @type bool
        @param expand flag indicating to expand all folds
        @type bool
        """
        self.setCursorPosition(line - 1, pos - 1)
        if firstVisible:
            self.ensureVisibleTop(line, expand)
        else:
            self.ensureVisible(line, expand)

    @pyqtSlot()
    def __textChanged(self):
        """
        Private slot to handle a change of the editor text.

        This slot defers the handling to the next time the event loop
        is run in order to ensure, that cursor position has been updated
        by the underlying Scintilla editor.
        """
        QTimer.singleShot(0, self.__saveLastEditPosition)

    @pyqtSlot()
    def __saveLastEditPosition(self):
        """
        Private slot to record the last edit position.
        """
        self.__lastEditPosition = self.getCursorPosition()
        self.lastEditPositionAvailable.emit()

    def isLastEditPositionAvailable(self):
        """
        Public method to check, if a last edit position is available.

        @return flag indicating availability
        @rtype bool
        """
        return self.__lastEditPosition is not None

    def gotoLastEditPosition(self):
        """
        Public method to move the cursor to the last edit position.
        """
        self.setCursorPosition(*self.__lastEditPosition)
        self.ensureVisible(self.__lastEditPosition[0])

    def gotoMethodClass(self, goUp=False):
        """
        Public method to go to the next Python method or class definition.

        @param goUp flag indicating the move direction
        @type bool
        """
        if self.isPyFile() or self.isRubyFile():
            lineNo = self.getCursorPosition()[0]
            line = self.text(lineNo)
            if line.strip().startswith(("class ", "def ", "module ")):
                if goUp:
                    lineNo -= 1
                else:
                    lineNo += 1
            while True:
                if goUp and lineNo < 0:
                    self.setCursorPosition(0, 0)
                    self.ensureVisible(0)
                    return
                elif not goUp and lineNo == self.lines():
                    lineNo = self.lines() - 1
                    self.setCursorPosition(lineNo, self.lineLength(lineNo))
                    self.ensureVisible(lineNo)
                    return

                line = self.text(lineNo)
                if line.strip().startswith(("class ", "def ", "module ")):
                    # try 'def ' first because it occurs more often
                    first = line.find("def ")
                    if first > -1:
                        first += 4
                    else:
                        first = line.find("class ")
                        if first > -1:
                            first += 6
                        else:
                            first = line.find("module ") + 7
                    match = re.search("[:(]", line)
                    if match:
                        end = match.start()
                    else:
                        end = self.lineLength(lineNo) - 1
                    self.setSelection(lineNo, first, lineNo, end)
                    self.ensureVisible(lineNo)
                    return

                if goUp:
                    lineNo -= 1
                else:
                    lineNo += 1

    ###########################################################################
    ## Setup methods below
    ###########################################################################

    @pyqtSlot()
    def readSettings(self):
        """
        Public slot to read the settings into our lexer.
        """
        # read the lexer settings and reinit the properties
        if self.lexer_ is not None:
            self.lexer_.readSettings(Preferences.getSettings(), "Scintilla")
            if self.lexer_.hasSubstyles():
                self.lexer_.readSubstyles(self)
            self.lexer_.initProperties()

            self.lexer_.setDefaultColor(self.lexer_.color(0))
            self.lexer_.setDefaultPaper(self.lexer_.paper(0))

        self.__bindLexer(self.fileName)
        self.recolor()

        # read the typing completer settings
        if self.completer is not None:
            self.completer.readSettings()

        # set the line marker colours or pixmap
        if Preferences.getEditor("LineMarkersBackground"):
            self.markerDefine(QsciScintilla.MarkerSymbol.Background, self.currentline)
            self.markerDefine(QsciScintilla.MarkerSymbol.Background, self.errorline)
            self.__setLineMarkerColours()
        else:
            self.markerDefine(
                EricPixmapCache.getPixmap("currentLineMarker"), self.currentline
            )
            self.markerDefine(
                EricPixmapCache.getPixmap("errorLineMarker"), self.errorline
            )

        # set the text display
        self.__setTextDisplay()

        # set margin 0 and 2 configuration
        self.__setMarginsDisplay()

        # set the auto-completion function
        self.__acCache.setSize(Preferences.getEditor("AutoCompletionCacheSize"))
        self.__acCache.setMaximumCacheTime(
            Preferences.getEditor("AutoCompletionCacheTime")
        )
        self.__acCacheEnabled = Preferences.getEditor("AutoCompletionCacheEnabled")
        acTimeout = Preferences.getEditor("AutoCompletionTimeout")
        if acTimeout != self.__acTimer.interval:
            self.__acTimer.setInterval(acTimeout)
        self.__setAutoCompletion()

        # set the calltips function
        self.__setCallTips()

        # set the autosave flags
        self.__autosaveInterval = Preferences.getEditor("AutosaveIntervalSeconds")
        if self.__autosaveInterval == 0:
            self.__autosaveTimer.stop()
        else:
            if self.isModified():
                self.__autosaveTimer.start(self.__autosaveInterval * 1000)

        if Preferences.getEditor("MiniContextMenu") != self.miniMenu:
            # regenerate context menu
            self.__initContextMenu()
        else:
            # set checked context menu items
            self.menuActs["AutoCompletionEnable"].setChecked(
                self.autoCompletionThreshold() != -1
            )
            self.menuActs["MonospacedFont"].setChecked(self.useMonospaced)
            self.menuActs["AutosaveEnable"].setChecked(
                self.__autosaveInterval > 0 and not self.__autosaveManuallyDisabled
            )

        # regenerate the margins context menu(s)
        self.__initContextMenuMargins()

        if Preferences.getEditor("MarkOccurrencesEnabled"):
            self.__markOccurrencesTimer.setInterval(
                Preferences.getEditor("MarkOccurrencesTimeout")
            )
        else:
            self.__markOccurrencesTimer.stop()
            self.clearSearchIndicators()

        if Preferences.getEditor("OnlineSyntaxCheck"):
            self.__onlineSyntaxCheckTimer.setInterval(
                Preferences.getEditor("OnlineSyntaxCheckInterval") * 1000
            )
        else:
            self.__onlineSyntaxCheckTimer.stop()

        if Preferences.getEditor("OnlineChangeTrace"):
            self.__onlineChangeTraceTimer.setInterval(
                Preferences.getEditor("OnlineChangeTraceInterval")
            )
        else:
            self.__onlineChangeTraceTimer.stop()
            self.__deleteAllChangeMarkers()
        self.markerDefine(
            self.__createChangeMarkerPixmap("OnlineChangeTraceMarkerUnsaved"),
            self.__changeMarkerUnsaved,
        )
        self.markerDefine(
            self.__createChangeMarkerPixmap("OnlineChangeTraceMarkerSaved"),
            self.__changeMarkerSaved,
        )

        # refresh the annotations display
        self.__refreshAnnotations()

        self.__markerMap.setMapPosition(Preferences.getEditor("ShowMarkerMapOnRight"))
        self.__markerMap.initColors()

        self.setLanguage(self.fileName, propagate=False)

        self.settingsRead.emit()

    def __setLineMarkerColours(self):
        """
        Private method to set the line marker colours.
        """
        self.setMarkerForegroundColor(
            Preferences.getEditorColour("CurrentMarker"), self.currentline
        )
        self.setMarkerBackgroundColor(
            Preferences.getEditorColour("CurrentMarker"), self.currentline
        )
        self.setMarkerForegroundColor(
            Preferences.getEditorColour("ErrorMarker"), self.errorline
        )
        self.setMarkerBackgroundColor(
            Preferences.getEditorColour("ErrorMarker"), self.errorline
        )

    def __setMarginsDisplay(self):
        """
        Private method to configure margins 0 and 2.
        """
        # set the settings for all margins
        self.setMarginsFont(Preferences.getEditorOtherFonts("MarginsFont"))
        self.setMarginsForegroundColor(Preferences.getEditorColour("MarginsForeground"))
        self.setMarginsBackgroundColor(Preferences.getEditorColour("MarginsBackground"))

        # reset standard margins settings
        for margin in range(5):
            self.setMarginLineNumbers(margin, False)
            self.setMarginMarkerMask(margin, 0)
            self.setMarginWidth(margin, 0)
            self.setMarginSensitivity(margin, False)

        # set marker margin(s) settings
        self.__bmMargin = 0
        self.__linenoMargin = 1
        self.__bpMargin = 2
        self.__foldMargin = 3
        self.__indicMargin = 4

        marginBmMask = 1 << self.bookmark
        self.setMarginWidth(self.__bmMargin, 16)
        self.setMarginSensitivity(self.__bmMargin, True)
        self.setMarginMarkerMask(self.__bmMargin, marginBmMask)

        marginBpMask = (
            (1 << self.breakpoint)
            | (1 << self.cbreakpoint)
            | (1 << self.tbreakpoint)
            | (1 << self.tcbreakpoint)
            | (1 << self.dbreakpoint)
        )
        self.setMarginWidth(self.__bpMargin, 16)
        self.setMarginSensitivity(self.__bpMargin, True)
        self.setMarginMarkerMask(self.__bpMargin, marginBpMask)

        marginIndicMask = (
            (1 << self.syntaxerror)
            | (1 << self.notcovered)
            | (1 << self.taskmarker)
            | (1 << self.warning)
            | (1 << self.__changeMarkerUnsaved)
            | (1 << self.__changeMarkerSaved)
            | (1 << self.currentline)
            | (1 << self.errorline)
        )
        self.setMarginWidth(self.__indicMargin, 16)
        self.setMarginSensitivity(self.__indicMargin, True)
        self.setMarginMarkerMask(self.__indicMargin, marginIndicMask)

        # set linenumber margin settings
        linenoMargin = Preferences.getEditor("LinenoMargin")
        self.setMarginLineNumbers(self.__linenoMargin, linenoMargin)
        if linenoMargin:
            self.__resizeLinenoMargin()
        else:
            self.setMarginWidth(self.__linenoMargin, 0)

        # set folding margin settings
        if Preferences.getEditor("FoldingMargin"):
            self.setMarginWidth(self.__foldMargin, 16)
            folding = Preferences.getEditor("FoldingStyle")
            self.setFolding(folding, self.__foldMargin)
            self.setFoldMarginColors(
                Preferences.getEditorColour("FoldmarginBackground"),
                Preferences.getEditorColour("FoldmarginBackground"),
            )
            self.setFoldMarkersColors(
                Preferences.getEditorColour("FoldMarkersForeground"),
                Preferences.getEditorColour("FoldMarkersBackground"),
            )
        else:
            self.setMarginWidth(self.__foldMargin, 0)
            self.setFolding(
                QsciScintilla.FoldStyle.NoFoldStyle.value, self.__foldMargin
            )

    @pyqtSlot()
    def __resizeLinenoMargin(self):
        """
        Private slot to resize the line numbers margin.
        """
        linenoMargin = Preferences.getEditor("LinenoMargin")
        if linenoMargin:
            self.setMarginWidth(self.__linenoMargin, "8" * (len(str(self.lines())) + 1))

    def __setTabAndIndent(self):
        """
        Private method to set indentation size and style and tab width.
        """
        self.setTabWidth(self.__getEditorConfig("TabWidth"))
        self.setIndentationWidth(self.__getEditorConfig("IndentWidth"))
        if self.lexer_ and self.lexer_.alwaysKeepTabs():
            self.setIndentationsUseTabs(True)
        else:
            self.setIndentationsUseTabs(self.__getEditorConfig("TabForIndentation"))

    def __setTextDisplay(self):
        """
        Private method to configure the text display.
        """
        self.__setTabAndIndent()

        self.setTabIndents(Preferences.getEditor("TabIndents"))
        self.setBackspaceUnindents(Preferences.getEditor("TabIndents"))
        self.setIndentationGuides(Preferences.getEditor("IndentationGuides"))
        self.setIndentationGuidesBackgroundColor(
            Preferences.getEditorColour("IndentationGuidesBackground")
        )
        self.setIndentationGuidesForegroundColor(
            Preferences.getEditorColour("IndentationGuidesForeground")
        )
        if Preferences.getEditor("ShowWhitespace"):
            self.setWhitespaceVisibility(QsciScintilla.WhitespaceVisibility.WsVisible)
            with contextlib.suppress(AttributeError):
                self.setWhitespaceForegroundColor(
                    Preferences.getEditorColour("WhitespaceForeground")
                )
                self.setWhitespaceBackgroundColor(
                    Preferences.getEditorColour("WhitespaceBackground")
                )
                self.setWhitespaceSize(Preferences.getEditor("WhitespaceSize"))
        else:
            self.setWhitespaceVisibility(QsciScintilla.WhitespaceVisibility.WsInvisible)
        self.setEolVisibility(Preferences.getEditor("ShowEOL"))
        self.setAutoIndent(Preferences.getEditor("AutoIndentation"))
        if Preferences.getEditor("BraceHighlighting"):
            self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        else:
            self.setBraceMatching(QsciScintilla.BraceMatch.NoBraceMatch)
        self.setMatchedBraceForegroundColor(
            Preferences.getEditorColour("MatchingBrace")
        )
        self.setMatchedBraceBackgroundColor(
            Preferences.getEditorColour("MatchingBraceBack")
        )
        self.setUnmatchedBraceForegroundColor(
            Preferences.getEditorColour("NonmatchingBrace")
        )
        self.setUnmatchedBraceBackgroundColor(
            Preferences.getEditorColour("NonmatchingBraceBack")
        )
        if Preferences.getEditor("CustomSelectionColours"):
            self.setSelectionBackgroundColor(
                Preferences.getEditorColour("SelectionBackground")
            )
        else:
            self.setSelectionBackgroundColor(
                QApplication.palette().color(QPalette.ColorRole.Highlight)
            )
        if Preferences.getEditor("ColourizeSelText"):
            self.resetSelectionForegroundColor()
        elif Preferences.getEditor("CustomSelectionColours"):
            self.setSelectionForegroundColor(
                Preferences.getEditorColour("SelectionForeground")
            )
        else:
            self.setSelectionForegroundColor(
                QApplication.palette().color(QPalette.ColorRole.HighlightedText)
            )
        self.setSelectionToEol(Preferences.getEditor("ExtendSelectionToEol"))
        self.setCaretForegroundColor(Preferences.getEditorColour("CaretForeground"))
        self.setCaretLineBackgroundColor(
            Preferences.getEditorColour("CaretLineBackground")
        )
        self.setCaretLineVisible(Preferences.getEditor("CaretLineVisible"))
        self.setCaretLineAlwaysVisible(Preferences.getEditor("CaretLineAlwaysVisible"))
        self.caretWidth = Preferences.getEditor("CaretWidth")
        self.setCaretWidth(self.caretWidth)
        self.caretLineFrameWidth = Preferences.getEditor("CaretLineFrameWidth")
        self.setCaretLineFrameWidth(self.caretLineFrameWidth)
        self.useMonospaced = Preferences.getEditor("UseMonospacedFont")
        self.setMonospaced(self.useMonospaced)
        edgeMode = Preferences.getEditor("EdgeMode")
        edge = QsciScintilla.EdgeMode(edgeMode)
        self.setEdgeMode(edge)
        if edgeMode:
            self.setEdgeColumn(Preferences.getEditor("EdgeColumn"))
            self.setEdgeColor(Preferences.getEditorColour("Edge"))

        wrapVisualFlag = Preferences.getEditor("WrapVisualFlag")
        self.setWrapMode(Preferences.getEditor("WrapLongLinesMode"))
        self.setWrapVisualFlags(wrapVisualFlag, wrapVisualFlag)
        self.setWrapIndentMode(Preferences.getEditor("WrapIndentMode"))
        self.setWrapStartIndent(Preferences.getEditor("WrapStartIndent"))

        self.zoomTo(Preferences.getEditor("ZoomFactor"))

        self.searchIndicator = QsciScintilla.INDIC_CONTAINER
        self.indicatorDefine(
            self.searchIndicator,
            QsciScintilla.INDIC_BOX,
            Preferences.getEditorColour("SearchMarkers"),
        )
        if (
            not Preferences.getEditor("SearchMarkersEnabled")
            and not Preferences.getEditor("QuickSearchMarkersEnabled")
            and not Preferences.getEditor("MarkOccurrencesEnabled")
        ):
            self.clearAllIndicators(self.searchIndicator)

        self.spellingIndicator = QsciScintilla.INDIC_CONTAINER + 1
        self.indicatorDefine(
            self.spellingIndicator,
            QsciScintilla.INDIC_SQUIGGLE,
            Preferences.getEditorColour("SpellingMarkers"),
        )
        self.__setSpelling()

        self.highlightIndicator = QsciScintilla.INDIC_CONTAINER + 2
        self.indicatorDefine(
            self.highlightIndicator,
            QsciScintilla.INDIC_FULLBOX,
            Preferences.getEditorColour("HighlightMarker"),
        )

        self.searchSelectionIndicator = QsciScintilla.INDIC_CONTAINER + 3
        self.indicatorDefine(
            self.searchSelectionIndicator,
            QsciScintilla.INDIC_FULLBOX,
            Preferences.getEditorColour("SearchSelectionMarker"),
        )

        self.setCursorFlashTime(QApplication.cursorFlashTime())

        with contextlib.suppress(AttributeError):
            if Preferences.getEditor("AnnotationsEnabled"):
                self.setAnnotationDisplay(
                    QsciScintilla.AnnotationDisplay.AnnotationBoxed
                )
            else:
                self.setAnnotationDisplay(
                    QsciScintilla.AnnotationDisplay.AnnotationHidden
                )
        self.__setAnnotationStyles()

        if Preferences.getEditor("OverrideEditAreaColours"):
            self.setColor(Preferences.getEditorColour("EditAreaForeground"))
            self.setPaper(Preferences.getEditorColour("EditAreaBackground"))

        self.setVirtualSpaceOptions(Preferences.getEditor("VirtualSpaceOptions"))

        if Preferences.getEditor("MouseHoverHelp"):
            self.SendScintilla(
                QsciScintilla.SCI_SETMOUSEDWELLTIME,
                Preferences.getEditor("MouseHoverTimeout"),
            )
        else:
            self.SendScintilla(
                QsciScintilla.SCI_SETMOUSEDWELLTIME, QsciScintilla.SC_TIME_FOREVER
            )

        self.setRectangularSelectionModifier(
            Preferences.getEditor("RectangularSelectionModifier")
        )

        # to avoid errors due to line endings by pasting
        self.SendScintilla(QsciScintilla.SCI_SETPASTECONVERTENDINGS, True)

        self.setPrintColorMode(Preferences.getEditor("PrintColorMode"))

        self.__markerMap.setEnabled(True)

    def __setEolMode(self):
        """
        Private method to configure the eol mode of the editor.
        """
        if (
            self.fileName
            and self.project.isOpen()
            and self.project.isProjectFile(self.fileName)
        ):
            eolMode = self.__getEditorConfig("EOLMode", nodefault=True)
            if eolMode is None:
                eolMode = self.project.getEolString()
        else:
            eolMode = self.__getEditorConfig("EOLMode")

        if isinstance(eolMode, str):
            self.setEolModeByEolString(eolMode)
        else:
            self.setEolMode(eolMode)
        self.__eolChanged()

    def __setAutoCompletion(self):
        """
        Private method to configure the autocompletion function.
        """
        if self.lexer_:
            self.setAutoCompletionFillupsEnabled(
                Preferences.getEditor("AutoCompletionFillups")
            )
        self.setAutoCompletionCaseSensitivity(
            Preferences.getEditor("AutoCompletionCaseSensitivity")
        )
        self.setAutoCompletionReplaceWord(
            Preferences.getEditor("AutoCompletionReplaceWord")
        )
        self.setAutoCompletionThreshold(0)
        if Preferences.getEditor("AutoCompletionShowSingle"):
            self.setAutoCompletionUseSingle(
                QsciScintilla.AutoCompletionUseSingle.AcusAlways
            )
        else:
            self.setAutoCompletionUseSingle(
                QsciScintilla.AutoCompletionUseSingle.AcusNever
            )
        autoCompletionSource = Preferences.getEditor("AutoCompletionSource")
        if autoCompletionSource == QsciScintilla.AutoCompletionSource.AcsDocument:
            self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsDocument)
        elif autoCompletionSource == QsciScintilla.AutoCompletionSource.AcsAPIs:
            self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAPIs)
        else:
            self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)

        self.setAutoCompletionWidgetSize(
            Preferences.getEditor("AutoCompletionMaxChars"),
            Preferences.getEditor("AutoCompletionMaxLines"),
        )

    def __setCallTips(self):
        """
        Private method to configure the calltips function.
        """
        self.setCallTipsBackgroundColor(
            Preferences.getEditorColour("CallTipsBackground")
        )
        self.setCallTipsForegroundColor(
            Preferences.getEditorColour("CallTipsForeground")
        )
        self.setCallTipsHighlightColor(Preferences.getEditorColour("CallTipsHighlight"))
        self.setCallTipsVisible(Preferences.getEditor("CallTipsVisible"))
        calltipsStyle = Preferences.getEditor("CallTipsStyle")
        with contextlib.suppress(AttributeError):
            self.setCallTipsPosition(Preferences.getEditor("CallTipsPosition"))

        if Preferences.getEditor("CallTipsEnabled"):
            if calltipsStyle == QsciScintilla.CallTipsStyle.CallTipsNoContext:
                self.setCallTipsStyle(QsciScintilla.CallTipsStyle.CallTipsNoContext)
            elif (
                calltipsStyle
                == QsciScintilla.CallTipsStyle.CallTipsNoAutoCompletionContext
            ):
                self.setCallTipsStyle(
                    QsciScintilla.CallTipsStyle.CallTipsNoAutoCompletionContext
                )
            else:
                self.setCallTipsStyle(QsciScintilla.CallTipsStyle.CallTipsContext)
        else:
            self.setCallTipsStyle(QsciScintilla.CallTipsStyle.CallTipsNone)

    ###########################################################################
    ## Autocompletion handling methods below
    ###########################################################################

    def canAutoCompleteFromAPIs(self):
        """
        Public method to check for API availablity.

        @return flag indicating autocompletion from APIs is available
        @rtype bool
        """
        return self.acAPI

    def autoCompleteQScintilla(self):
        """
        Public method to perform an autocompletion using QScintilla methods.
        """
        self.__acText = " "  # Prevent long running ACs to add results
        self.__acWatchdog.stop()
        if self.__acCompletions:
            return

        acs = Preferences.getEditor("AutoCompletionSource")
        if acs == QsciScintilla.AutoCompletionSource.AcsDocument:
            self.autoCompleteFromDocument()
        elif acs == QsciScintilla.AutoCompletionSource.AcsAPIs:
            self.autoCompleteFromAPIs()
        elif acs == QsciScintilla.AutoCompletionSource.AcsAll:
            self.autoCompleteFromAll()
        else:
            EricMessageBox.information(
                self,
                self.tr("Autocompletion"),
                self.tr(
                    """Autocompletion is not available because"""
                    """ there is no autocompletion source set."""
                ),
            )

    def setAutoCompletionEnabled(self, enable):
        """
        Public method to enable/disable autocompletion.

        @param enable flag indicating the desired autocompletion status
        @type bool
        """
        if enable:
            autoCompletionSource = Preferences.getEditor("AutoCompletionSource")
            if autoCompletionSource == QsciScintilla.AutoCompletionSource.AcsDocument:
                self.setAutoCompletionSource(
                    QsciScintilla.AutoCompletionSource.AcsDocument
                )
            elif autoCompletionSource == QsciScintilla.AutoCompletionSource.AcsAPIs:
                self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAPIs)
            else:
                self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)

    @pyqtSlot()
    def __toggleAutoCompletionEnable(self):
        """
        Private slot to handle the Enable Autocompletion context menu entry.
        """
        if self.menuActs["AutoCompletionEnable"].isChecked():
            self.setAutoCompletionEnabled(True)
        else:
            self.setAutoCompletionEnabled(False)

    #################################################################
    ## Support for autocompletion hook methods
    #################################################################

    @pyqtSlot(int)
    def __charAdded(self, charNumber):
        """
        Private slot called to handle the user entering a character.

        @param charNumber value of the character entered
        @type int
        """
        char = chr(charNumber)
        # update code documentation viewer
        if char == "(" and Preferences.getDocuViewer("ShowInfoOnOpenParenthesis"):
            self.vm.showEditorInfo(self)

        self.__delayedDocstringMenuPopup(self.getCursorPosition())

        if self.isListActive():
            if self.__isStartChar(char):
                self.cancelList()
                self.autoComplete(auto=True, context=True)
                return
            elif char == "(":
                self.cancelList()
            else:
                self.__acTimer.stop()

        if (
            self.callTipsStyle() != QsciScintilla.CallTipsStyle.CallTipsNone
            and self.lexer_ is not None
            and chr(charNumber) in "()"
        ):
            self.callTip()

        if not self.isCallTipActive():
            char = chr(charNumber)
            if self.__isStartChar(char):
                self.autoComplete(auto=True, context=True)
                return

            line, col = self.getCursorPosition()
            txt = self.getWordLeft(line, col)
            if len(txt) >= Preferences.getEditor("AutoCompletionThreshold"):
                self.autoComplete(auto=True, context=False)
                return

    def __isStartChar(self, ch):
        """
        Private method to check, if a character is an autocompletion start
        character.

        @param ch character to be checked
        @type str
        @return flag indicating the result
        @rtype bool
        """
        if self.lexer_ is None:
            return False

        wseps = self.lexer_.autoCompletionWordSeparators()
        return any(wsep.endswith(ch) for wsep in wseps)

    @pyqtSlot()
    def __autocompletionCancelled(self):
        """
        Private slot to handle the cancellation of an auto-completion list.
        """
        self.__acWatchdog.stop()

        self.__acText = ""

    #################################################################
    ## auto-completion hook interfaces
    #################################################################

    def addCompletionListHook(self, key, func, asynchroneous=False):
        """
        Public method to set an auto-completion list provider.

        @param key name of the provider
        @type str
        @param func function providing completion list. func
            should be a function taking a reference to the editor and
            a boolean indicating to complete a context. It should return
            the possible completions as a list of strings.
        @type function(editor, bool) -> list of str in case async is False
            and function(editor, bool, str) returning nothing in case async
            is True
        @param asynchroneous flag indicating an asynchroneous function
        @type bool
        """
        if (
            key in self.__completionListHookFunctions
            or key in self.__completionListAsyncHookFunctions
        ):
            # it was already registered
            EricMessageBox.warning(
                self,
                self.tr("Auto-Completion Provider"),
                self.tr(
                    """The completion list provider '{0}' was already"""
                    """ registered. Ignoring duplicate request."""
                ).format(key),
            )
            return

        if asynchroneous:
            self.__completionListAsyncHookFunctions[key] = func
        else:
            self.__completionListHookFunctions[key] = func

    def removeCompletionListHook(self, key):
        """
        Public method to remove a previously registered completion list
        provider.

        @param key name of the provider
        @type str
        """
        if key in self.__completionListHookFunctions:
            del self.__completionListHookFunctions[key]
        elif key in self.__completionListAsyncHookFunctions:
            del self.__completionListAsyncHookFunctions[key]

    def getCompletionListHook(self, key):
        """
        Public method to get the registered completion list provider.

        @param key name of the provider
        @type str
        @return function providing completion list
        @rtype function or None
        """
        return self.__completionListHookFunctions.get(
            key
        ) or self.__completionListAsyncHookFunctions.get(key)

    def autoComplete(self, auto=False, context=True):
        """
        Public method to start auto-completion.

        @param auto flag indicating a call from the __charAdded method
        @type bool
        @param context flag indicating to complete a context
        @type bool
        """
        if auto and not Preferences.getEditor("AutoCompletionEnabled"):
            # auto-completion is disabled
            return

        if self.isListActive():
            self.cancelList()

        if (
            self.__completionListHookFunctions
            or self.__completionListAsyncHookFunctions
        ):
            # Avoid delayed auto-completion after cursor repositioning
            self.__acText = self.__getAcText()
            if auto and Preferences.getEditor("AutoCompletionTimeout"):
                self.__acTimer.stop()
                self.__acContext = context
                self.__acTimer.start()
            else:
                self.__autoComplete(auto, context)
        elif not auto or (
            self.autoCompletionSource() != QsciScintilla.AutoCompletionSource.AcsNone
        ):
            self.autoCompleteQScintilla()

    def __getAcText(self):
        """
        Private method to get the text from cursor position for autocompleting.

        @return text left of cursor position
        @rtype str
        """
        line, col = self.getCursorPosition()
        text = self.text(line)
        try:
            acText = (
                self.getWordLeft(line, col - 1) + text[col - 1]
                if self.__isStartChar(text[col - 1])
                else self.getWordLeft(line, col)
            )
        except IndexError:
            acText = ""

        return acText

    def __autoComplete(self, auto=True, context=None):
        """
        Private method to start auto-completion via plug-ins.

        @param auto flag indicating a call from the __charAdded method
        @type bool
        @param context flag indicating to complete a context
        @type bool or None
        """
        self.__acCompletions.clear()
        self.__acCompletionsFinished = 0

        # Suppress empty completions
        if auto and self.__acText == "":
            return

        completions = (
            self.__acCache.get(self.__acText) if self.__acCacheEnabled else None
        )
        if completions is not None:
            # show list with cached entries
            if self.isListActive():
                self.cancelList()

            self.__showCompletionsList(completions)
        else:
            if context is None:
                context = self.__acContext

            for key in self.__completionListAsyncHookFunctions:
                self.__completionListAsyncHookFunctions[key](
                    self, context, self.__acText
                )

            for key in self.__completionListHookFunctions:
                completions = self.__completionListHookFunctions[key](self, context)
                self.completionsListReady(completions, self.__acText)

            if Preferences.getEditor("AutoCompletionScintillaOnFail"):
                self.__acWatchdog.start()

    def completionsListReady(self, completions, acText):
        """
        Public method to show the completions determined by a completions
        provider.

        @param completions list of possible completions
        @type list of str or set of str
        @param acText text to be completed
        @type str
        """
        currentWord = self.__getAcText() or " "
        # process the list only, if not already obsolete ...
        if acText != self.__acText or not self.__acText.endswith(currentWord):
            # Suppress auto-completion done by QScintilla as fallback
            self.__acWatchdog.stop()
            return

        self.__acCompletions.update(set(completions))

        self.__acCompletionsFinished += 1
        # Got all results from auto completer?
        if self.__acCompletionsFinished >= (
            len(self.__completionListAsyncHookFunctions)
            + len(self.__completionListHookFunctions)
        ):
            self.__acWatchdog.stop()

            # Autocomplete with QScintilla if no results present
            if (
                Preferences.getEditor("AutoCompletionScintillaOnFail")
                and not self.__acCompletions
            ):
                self.autoCompleteQScintilla()
                return

        # ... or completions are not empty
        if not bool(completions):
            return

        if self.isListActive():
            self.cancelList()

        if self.__acCompletions:
            if self.__acCacheEnabled:
                self.__acCache.add(acText, set(self.__acCompletions))
            self.__showCompletionsList(self.__acCompletions)

    def __showCompletionsList(self, completions):
        """
        Private method to show the completions list.

        @param completions completions to be shown
        @type list of str or set of str
        """
        acCompletions = (
            sorted(completions, key=self.__replaceLeadingUnderscores)
            if Preferences.getEditor("AutoCompletionReversedList")
            else sorted(completions)
        )
        self.showUserList(EditorAutoCompletionListID, acCompletions)

    def __replaceLeadingUnderscores(self, txt):
        """
        Private method to replace the first two underlines for invers sorting.

        @param txt completion text
        @type str
        @return modified completion text
        @rtype str
        """
        if txt.startswith("_"):
            return txt[:2].replace("_", "~") + txt[2:]
        else:
            return txt

    def __clearCompletionsCache(self):
        """
        Private method to clear the auto-completions cache.
        """
        self.__acCache.clear()

    @pyqtSlot(int, str)
    def __completionListSelected(self, listId, txt):
        """
        Private slot to handle the selection from the completion list.

        @param listId the ID of the user list (should be 1 or 2)
        @type int
        @param txt the selected text
        @type str
        """
        # custom completions via plug-ins
        if listId == EditorAutoCompletionListID:
            lst = txt.split()
            if len(lst) > 1:
                txt = lst[0]

            self.beginUndoAction()
            if Preferences.getEditor("AutoCompletionReplaceWord"):
                self.selectCurrentWord()
                self.removeSelectedText()
                line, col = self.getCursorPosition()
            else:
                line, col = self.getCursorPosition()
                wLeft = self.getWord(line, col, 1, forCompletion=True)  # word left
                if not txt.startswith(wLeft):
                    self.selectCurrentWord()
                    self.removeSelectedText()
                    line, col = self.getCursorPosition()
                elif wLeft:
                    txt = txt[len(wLeft) :]

                if txt and txt[0] in "'\"":
                    # New in jedi 0.16: AC of dict keys
                    txt = txt[1:]
            self.insert(txt)
            self.endUndoAction()
            self.setCursorPosition(line, col + len(txt))

        # template completions
        elif listId == TemplateCompletionListID:
            self.__applyTemplate(txt, self.getLanguage())

        # 'goto reference' completions
        elif listId == ReferencesListID:
            with contextlib.suppress(ValueError, IndexError):
                index = self.__referencesList.index(txt)
                filename, line, column = self.__referencesPositionsList[index]
                self.vm.openSourceFile(filename, lineno=line, pos=column, addNext=True)

    def canProvideDynamicAutoCompletion(self):
        """
        Public method to test the dynamic auto-completion availability.

        @return flag indicating the availability of dynamic auto-completion
        @rtype bool
        """
        return (
            self.acAPI
            or bool(self.__completionListHookFunctions)
            or bool(self.__completionListAsyncHookFunctions)
        )

    #################################################################
    ## call-tip hook interfaces
    #################################################################

    def addCallTipHook(self, key, func):
        """
        Public method to set a calltip provider.

        @param key name of the provider
        @type str
        @param func function providing calltips. func
            should be a function taking a reference to the editor,
            a position into the text and the amount of commas to the
            left of the cursor. It should return the possible
            calltips as a list of strings.
        @type function(editor, int, int) -> list of str
        """
        if key in self.__ctHookFunctions:
            # it was already registered
            EricMessageBox.warning(
                self,
                self.tr("Call-Tips Provider"),
                self.tr(
                    """The call-tips provider '{0}' was already"""
                    """ registered. Ignoring duplicate request."""
                ).format(key),
            )
            return

        self.__ctHookFunctions[key] = func

    def removeCallTipHook(self, key):
        """
        Public method to remove a previously registered calltip provider.

        @param key name of the provider
        @type str
        """
        if key in self.__ctHookFunctions:
            del self.__ctHookFunctions[key]

    def getCallTipHook(self, key):
        """
        Public method to get the registered calltip provider.

        @param key name of the provider
        @type str
        @return function providing calltips
        @rtype function or None
        """
        if key in self.__ctHookFunctions:
            return self.__ctHookFunctions[key]
        else:
            return None

    def canProvideCallTipps(self):
        """
        Public method to test the calltips availability.

        @return flag indicating the availability of calltips
        @rtype bool
        """
        return self.acAPI or bool(self.__ctHookFunctions)

    def callTip(self):
        """
        Public method to show calltips.
        """
        if bool(self.__ctHookFunctions):
            self.__callTip()
        else:
            super().callTip()

    def __callTip(self):
        """
        Private method to show call tips provided by a plugin.
        """
        pos = self.currentPosition()

        # move backward to the start of the current calltip working out
        # which argument to highlight
        commas = 0
        found = False
        ch, pos = self.__getCharacter(pos)
        while ch:
            if ch == ",":
                commas += 1
            elif ch == ")":
                depth = 1

                # ignore everything back to the start of the corresponding
                # parenthesis
                ch, pos = self.__getCharacter(pos)
                while ch:
                    if ch == ")":
                        depth += 1
                    elif ch == "(":
                        depth -= 1
                        if depth == 0:
                            break
                    ch, pos = self.__getCharacter(pos)
            elif ch == "(":
                found = True
                break

            ch, pos = self.__getCharacter(pos)

        self.cancelCallTips()

        if not found:
            return

        callTips = []
        if self.__ctHookFunctions:
            for key in self.__ctHookFunctions:
                callTips.extend(self.__ctHookFunctions[key](self, pos, commas))
            callTips = list(set(callTips))
            callTips.sort()
        else:
            # try QScintilla calltips
            super().callTip()
            return
        if len(callTips) == 0:
            if Preferences.getEditor("CallTipsScintillaOnFail"):
                # try QScintilla calltips
                super().callTip()
            return

        ctshift = 0
        for ct in callTips:
            shift = ct.index("(")
            if ctshift < shift:
                ctshift = shift

        cv = self.callTipsVisible()
        ct = (
            # this is just a safe guard
            self._encodeString("\n".join(callTips[:cv]))
            if cv > 0
            else
            # until here and unindent below
            self._encodeString("\n".join(callTips))
        )

        self.SendScintilla(
            QsciScintilla.SCI_CALLTIPSHOW,
            self.__adjustedCallTipPosition(ctshift, pos),
            ct,
        )
        if b"\n" in ct:
            return

        # Highlight the current argument
        if commas == 0:
            astart = ct.find(b"(")
        else:
            astart = ct.find(b",")
            commas -= 1
            while astart != -1 and commas > 0:
                astart = ct.find(b",", astart + 1)
                commas -= 1

        if astart == -1:
            return

        depth = 0
        for aend in range(astart + 1, len(ct)):
            ch = ct[aend : aend + 1]

            if ch == b"," and depth == 0:
                break
            elif ch == b"(":
                depth += 1
            elif ch == b")":
                if depth == 0:
                    break

                depth -= 1

        if astart != aend:
            self.SendScintilla(QsciScintilla.SCI_CALLTIPSETHLT, astart + 1, aend)

    def __adjustedCallTipPosition(self, ctshift, pos):
        """
        Private method to calculate an adjusted position for showing calltips.

        @param ctshift amount the calltip shall be shifted
        @type int
        @param pos position into the text
        @type int
        @return new position for the calltip
        @rtype int
        """
        ct = pos
        if ctshift:
            ctmin = self.SendScintilla(
                QsciScintilla.SCI_POSITIONFROMLINE,
                self.SendScintilla(QsciScintilla.SCI_LINEFROMPOSITION, ct),
            )
            if ct - ctshift < ctmin:
                ct = ctmin
            else:
                ct -= ctshift
        return ct

    #################################################################
    ## Methods needed by the code documentation viewer
    #################################################################

    @pyqtSlot()
    def __showCodeInfo(self):
        """
        Private slot to handle the context menu action to show code info.
        """
        self.vm.showEditorInfo(self)

    #################################################################
    ## Methods needed by the context menu
    #################################################################

    def __marginNumber(self, xPos):
        """
        Private method to calculate the margin number based on a x position.

        @param xPos x position
        @type int
        @return margin number (integer, -1 for no margin)
        @rtype int
        """
        width = 0
        for margin in range(5):
            width += self.marginWidth(margin)
            if xPos <= width:
                return margin
        return -1

    @pyqtSlot(QPoint)
    def __showContextMenu(self, pos):
        """
        Private slot to show a context menu.

        @param pos position for the context menu
        @type QPoint
        """
        if self.__marginNumber(pos.x()) == -1:
            self.spellingMenuPos = self.positionFromPoint(pos)
            if (
                self.spellingMenuPos >= 0
                and self.spell is not None
                and self.hasIndicator(self.spellingIndicator, self.spellingMenuPos)
            ):
                self.spellingMenu.popup(self.mapToGlobal(pos))
            else:
                self.menu.popup(self.mapToGlobal(pos))
        else:
            self.line = self.lineAt(pos)
            if self.__marginNumber(pos.x()) in [self.__bmMargin, self.__linenoMargin]:
                self.bmMarginMenu.popup(self.mapToGlobal(pos))
            elif self.__marginNumber(pos.x()) == self.__bpMargin:
                self.bpMarginMenu.popup(self.mapToGlobal(pos))
            elif self.__marginNumber(pos.x()) == self.__indicMargin:
                self.indicMarginMenu.popup(self.mapToGlobal(pos))
            elif self.__marginNumber(pos.x()) == self.__foldMargin:
                self.foldMarginMenu.popup(self.mapToGlobal(pos))

    @pyqtSlot()
    def __aboutToShowContextMenu(self):
        """
        Private slot handling the aboutToShow signal of the context menu.
        """
        self.menuActs["Reopen"].setEnabled(
            not self.isModified() and bool(self.fileName)
        )
        self.menuActs["Reload"].setEnabled(bool(self.fileName))
        self.menuActs["Save"].setEnabled(self.isModified())
        self.menuActs["SaveAsRemote"].setEnabled(
            ericApp().getObject("EricServer").isServerConnected()
        )
        self.menuActs["Undo"].setEnabled(self.isUndoAvailable())
        self.menuActs["Redo"].setEnabled(self.isRedoAvailable())
        self.menuActs["Revert"].setEnabled(self.isModified())
        self.menuActs["Cut"].setEnabled(self.hasSelectedText())
        self.menuActs["Copy"].setEnabled(self.hasSelectedText())
        if self.menuActs["ExecuteSelection"] is not None:
            self.menuActs["ExecuteSelection"].setEnabled(self.hasSelectedText())
        self.menuActs["Paste"].setEnabled(self.canPaste())
        if not self.isResourcesFile:
            if self.fileName and self.isPyFile():
                self.menuActs["Show"].setEnabled(True)
            else:
                self.menuActs["Show"].setEnabled(False)
            if self.fileName and (self.isPyFile() or self.isRubyFile()):
                self.menuActs["Diagrams"].setEnabled(True)
            else:
                self.menuActs["Diagrams"].setEnabled(False)
            self.menuActs["Formatting"].setEnabled(
                not FileSystemUtilities.isRemoteFileName(self.fileName)
            )
        if not self.miniMenu:
            if self.lexer_ is not None:
                self.menuActs["Comment"].setEnabled(self.lexer_.canBlockComment())
                self.menuActs["Uncomment"].setEnabled(self.lexer_.canBlockComment())
            else:
                self.menuActs["Comment"].setEnabled(False)
                self.menuActs["Uncomment"].setEnabled(False)

            cline = self.getCursorPosition()[0]
            line = self.text(cline)
            self.menuActs["Docstring"].setEnabled(
                self.getDocstringGenerator().isFunctionStart(line)
            )

        self.menuActs["TypingAidsEnabled"].setEnabled(self.completer is not None)
        self.menuActs["TypingAidsEnabled"].setChecked(
            self.completer is not None and self.completer.isEnabled()
        )

        if not self.isResourcesFile:
            self.menuActs["calltip"].setEnabled(self.canProvideCallTipps())
            self.menuActs["codeInfo"].setEnabled(
                self.vm.isEditorInfoSupported(self.getLanguage())
            )

        self.menuActs["MonospacedFont"].setEnabled(self.lexer_ is None)

        splitOrientation = self.vm.getSplitOrientation()
        if splitOrientation == Qt.Orientation.Horizontal:
            self.menuActs["NewSplit"].setIcon(
                EricPixmapCache.getIcon("splitHorizontal")
            )
        else:
            self.menuActs["NewSplit"].setIcon(EricPixmapCache.getIcon("splitVertical"))

        self.menuActs["Tools"].setEnabled(not self.toolsMenu.isEmpty())

        self.showMenu.emit("Main", self.menu, self)

    @pyqtSlot()
    def __showContextMenuAutocompletion(self):
        """
        Private slot called before the autocompletion menu is shown.
        """
        self.menuActs["acDynamic"].setEnabled(self.canProvideDynamicAutoCompletion())
        self.menuActs["acClearCache"].setEnabled(self.canProvideDynamicAutoCompletion())
        self.menuActs["acAPI"].setEnabled(self.acAPI)
        self.menuActs["acAPIDocument"].setEnabled(self.acAPI)

        self.showMenu.emit("Autocompletion", self.autocompletionMenu, self)

    @pyqtSlot()
    def __showContextMenuShow(self):
        """
        Private slot called before the show menu is shown.
        """
        prEnable = False
        coEnable = False

        # first check if the file belongs to a project
        if self.project.isOpen() and self.project.isProjectCategory(
            self.fileName, "SOURCES"
        ):
            fn = self.project.getMainScript(True)
            if fn is not None:
                prEnable = self.project.isPy3Project() and bool(
                    Utilities.getProfileFileNames(fn)
                )
                coEnable = self.project.isPy3Project() and bool(
                    Utilities.getCoverageFileNames(fn)
                )

        # now check ourselves
        fn = self.getFileName()
        if fn is not None:
            prEnable |= self.isPyFile() and bool(Utilities.getProfileFileName(fn))
            coEnable |= self.isPyFile() and bool(Utilities.getCoverageFileName(fn))

        coEnable |= bool(self.__coverageFile)

        # now check for syntax errors
        if self.hasSyntaxErrors():
            coEnable = False

        self.profileMenuAct.setEnabled(prEnable)
        self.coverageMenuAct.setEnabled(coEnable)
        self.coverageShowAnnotationMenuAct.setEnabled(
            coEnable and len(self.notcoveredMarkers) == 0
        )
        self.coverageHideAnnotationMenuAct.setEnabled(len(self.notcoveredMarkers) > 0)

        self.showMenu.emit("Show", self.menuShow, self)

    @pyqtSlot()
    def __showContextMenuGraphics(self):
        """
        Private slot handling the aboutToShow signal of the diagrams context
        menu.
        """
        if self.project.isOpen() and self.project.isProjectCategory(
            self.fileName, "SOURCES"
        ):
            self.applicationDiagramMenuAct.setEnabled(True)
        else:
            self.applicationDiagramMenuAct.setEnabled(False)

        self.showMenu.emit("Graphics", self.graphicsMenu, self)

    @pyqtSlot(QMenu)
    def __showContextMenuMargin(self, menu):
        """
        Private slot handling the aboutToShow signal of the margins context
        menu.

        @param menu reference to the menu to be shown
        @type QMenu
        """
        if menu is self.bpMarginMenu:
            supportsDebugger = bool(self.fileName and self.isPyFile())
            hasBreakpoints = bool(self.breaks)
            hasBreakpoint = bool(self.markersAtLine(self.line) & self.breakpointMask)

            self.marginMenuActs["Breakpoint"].setEnabled(supportsDebugger)
            self.marginMenuActs["TempBreakpoint"].setEnabled(supportsDebugger)
            self.marginMenuActs["NextBreakpoint"].setEnabled(
                supportsDebugger and hasBreakpoints
            )
            self.marginMenuActs["PreviousBreakpoint"].setEnabled(
                supportsDebugger and hasBreakpoints
            )
            self.marginMenuActs["ClearBreakpoint"].setEnabled(
                supportsDebugger and hasBreakpoints
            )
            self.marginMenuActs["EditBreakpoint"].setEnabled(
                supportsDebugger and hasBreakpoint
            )
            self.marginMenuActs["EnableBreakpoint"].setEnabled(
                supportsDebugger and hasBreakpoint
            )
            if supportsDebugger:
                if self.markersAtLine(self.line) & (1 << self.dbreakpoint):
                    self.marginMenuActs["EnableBreakpoint"].setText(
                        self.tr("Enable breakpoint")
                    )
                else:
                    self.marginMenuActs["EnableBreakpoint"].setText(
                        self.tr("Disable breakpoint")
                    )

        if menu is self.bmMarginMenu:
            hasBookmarks = bool(self.bookmarks)

            self.marginMenuActs["NextBookmark"].setEnabled(hasBookmarks)
            self.marginMenuActs["PreviousBookmark"].setEnabled(hasBookmarks)
            self.marginMenuActs["ClearBookmark"].setEnabled(hasBookmarks)

        if menu is self.foldMarginMenu:
            isFoldHeader = bool(
                self.SendScintilla(QsciScintilla.SCI_GETFOLDLEVEL, self.line)
                & QsciScintilla.SC_FOLDLEVELHEADERFLAG
            )

            self.marginMenuActs["ExpandChildren"].setEnabled(isFoldHeader)
            self.marginMenuActs["CollapseChildren"].setEnabled(isFoldHeader)

        if menu is self.indicMarginMenu:
            hasSyntaxErrors = bool(self.syntaxerrors)
            hasWarnings = bool(self._warnings)
            hasNotCoveredMarkers = bool(self.notcoveredMarkers)

            self.marginMenuActs["GotoSyntaxError"].setEnabled(hasSyntaxErrors)
            self.marginMenuActs["ClearSyntaxError"].setEnabled(hasSyntaxErrors)
            if hasSyntaxErrors and self.markersAtLine(self.line) & (
                1 << self.syntaxerror
            ):
                self.marginMenuActs["ShowSyntaxError"].setEnabled(True)
            else:
                self.marginMenuActs["ShowSyntaxError"].setEnabled(False)

            self.marginMenuActs["NextWarningMarker"].setEnabled(hasWarnings)
            self.marginMenuActs["PreviousWarningMarker"].setEnabled(hasWarnings)
            self.marginMenuActs["ClearWarnings"].setEnabled(hasWarnings)
            if hasWarnings and self.markersAtLine(self.line) & (1 << self.warning):
                self.marginMenuActs["ShowWarning"].setEnabled(True)
            else:
                self.marginMenuActs["ShowWarning"].setEnabled(False)

            self.marginMenuActs["NextCoverageMarker"].setEnabled(hasNotCoveredMarkers)
            self.marginMenuActs["PreviousCoverageMarker"].setEnabled(
                hasNotCoveredMarkers
            )

            self.marginMenuActs["PreviousTaskMarker"].setEnabled(self.__hasTaskMarkers)
            self.marginMenuActs["NextTaskMarker"].setEnabled(self.__hasTaskMarkers)

            self.marginMenuActs["PreviousChangeMarker"].setEnabled(
                self.__hasChangeMarkers
            )
            self.marginMenuActs["NextChangeMarker"].setEnabled(self.__hasChangeMarkers)
            self.marginMenuActs["ClearChangeMarkers"].setEnabled(
                self.__hasChangeMarkers
            )

        self.showMenu.emit("Margin", menu, self)

    @pyqtSlot()
    def __showContextMenuChecks(self):
        """
        Private slot handling the aboutToShow signal of the checks context
        menu.
        """
        self.showMenu.emit("Checks", self.checksMenu, self)

    @pyqtSlot()
    def __showContextMenuTools(self):
        """
        Private slot handling the aboutToShow signal of the tools context
        menu.
        """
        self.showMenu.emit("Tools", self.toolsMenu, self)

    @pyqtSlot()
    def __showContextMenuFormatting(self):
        """
        Private slot handling the aboutToShow signal of the code formatting context
        menu.
        """
        self.showMenu.emit("Formatting", self.codeFormattingMenu, self)

    def __reopenWithEncodingMenuTriggered(self, act):
        """
        Private method to handle the rereading of the file with a selected
        encoding.

        @param act reference to the action that was triggered
        @type QAction
        """
        encoding = act.data()
        self.readFile(self.fileName, encoding=encoding)
        self.__convertTabs()
        self.__checkEncoding()

    @pyqtSlot()
    def __contextSave(self):
        """
        Private slot handling the save context menu entry.
        """
        ok = self.saveFile()
        if ok:
            self.vm.setEditorName(self, self.fileName)

    @pyqtSlot()
    def __contextSaveAs(self):
        """
        Private slot handling the save as context menu entry.
        """
        ok = self.saveFileAs()
        if ok:
            self.vm.setEditorName(self, self.fileName)

    @pyqtSlot()
    def __contextSaveAsRemote(self):
        """
        Private slot handling the save as (remote) context menu entry.
        """
        ok = self.saveFileAs(remote=True)
        if ok:
            self.vm.setEditorName(self, self.fileName)

    @pyqtSlot()
    def __contextSaveCopy(self):
        """
        Private slot handling the save copy context menu entry.
        """
        self.saveFileCopy()

    @pyqtSlot()
    def __contextClose(self):
        """
        Private slot handling the close context menu entry.
        """
        self.vm.closeEditor(self)

    @pyqtSlot()
    def __newView(self):
        """
        Private slot to create a new view to an open document.
        """
        self.vm.newEditorView(self.fileName, self, self.filetype)

    @pyqtSlot()
    def __newViewNewSplit(self):
        """
        Private slot to create a new view to an open document.
        """
        self.vm.addSplit()
        self.vm.newEditorView(self.fileName, self, self.filetype)

    @pyqtSlot()
    def __selectAll(self):
        """
        Private slot handling the select all context menu action.
        """
        self.selectAll(True)

    @pyqtSlot()
    def __deselectAll(self):
        """
        Private slot handling the deselect all context menu action.
        """
        self.selectAll(False)

    @pyqtSlot()
    def joinLines(self):
        """
        Public slot to join the current line with the next one.
        """
        curLine = self.getCursorPosition()[0]
        if curLine == self.lines() - 1:
            return

        line0Text = self.text(curLine)
        line1Text = self.text(curLine + 1)
        if line1Text in ["", "\r", "\n", "\r\n"]:
            return

        if line0Text.rstrip("\r\n\\ \t").endswith(
            ("'", '"')
        ) and line1Text.lstrip().startswith(("'", '"')):
            # merging multi line strings
            startChars = "\r\n\\ \t'\""
            endChars = " \t'\""
        else:
            startChars = "\r\n\\ \t"
            endChars = " \t"

        # determine start index
        startIndex = len(line0Text)
        while startIndex > 0 and line0Text[startIndex - 1] in startChars:
            startIndex -= 1
        if startIndex == 0:
            return

        # determine end index
        endIndex = 0
        while line1Text[endIndex] in endChars:
            endIndex += 1

        self.setSelection(curLine, startIndex, curLine + 1, endIndex)
        self.beginUndoAction()
        self.removeSelectedText()
        self.insertAt(" ", curLine, startIndex)
        self.endUndoAction()

    @pyqtSlot()
    def shortenEmptyLines(self):
        """
        Public slot to compress lines consisting solely of whitespace
        characters.
        """
        searchRE = r"^[ \t]+$"

        ok = self.findFirstTarget(searchRE, True, False, False, 0, 0)
        self.beginUndoAction()
        while ok:
            self.replaceTarget("")
            ok = self.findNextTarget()
        self.endUndoAction()

    @pyqtSlot()
    def __autosaveEnable(self):
        """
        Private slot handling the autosave enable context menu action.
        """
        if self.menuActs["AutosaveEnable"].isChecked():
            self.__autosaveManuallyDisabled = False
        else:
            self.__autosaveManuallyDisabled = True

    def __shouldAutosave(self):
        """
        Private method to check the autosave flags.

        @return flag indicating this editor should be saved
        @rtype bool
        """
        return (
            bool(self.fileName)
            and not self.__autosaveManuallyDisabled
            and not self.isReadOnly()
            and self.isModified()
        )

    def __autosave(self):
        """
        Private slot to save the contents of the editor automatically.

        It is only saved by the autosave timer after an initial save (i.e. it already
        has a name).
        """
        if self.__shouldAutosave():
            self.saveFile()

    def checkSyntax(self):
        """
        Public method to perform an automatic syntax check of the file.
        """
        fileType = self.filetype
        if fileType == "MicroPython":
            # adjustment for MicroPython
            fileType = "Python3"

        if (
            self.syntaxCheckService is None
            or fileType not in self.syntaxCheckService.getLanguages()
        ):
            return

        if Preferences.getEditor("OnlineSyntaxCheck"):
            self.__onlineSyntaxCheckTimer.stop()

        if self.isPy3File():
            additionalBuiltins = (
                self.project.getData("CHECKERSPARMS", "SyntaxChecker", {}).get(
                    "AdditionalBuiltins", []
                )
                if self.isProjectFile()
                else Preferences.getFlakes("AdditionalBuiltins")
            )
            self.syntaxCheckService.syntaxCheck(
                fileType,
                self.fileName or "(Unnamed)",
                self.text(),
                additionalBuiltins,
            )
        else:
            self.syntaxCheckService.syntaxCheck(
                fileType,
                self.fileName or "(Unnamed)",
                self.text(),
            )

    @pyqtSlot(str, str)
    def __processSyntaxCheckError(self, fn, msg):
        """
        Private slot to report an error message of a syntax check.

        @param fn filename of the file
        @type str
        @param msg error message
        @type str
        """
        if fn != self.fileName and (bool(self.fileName) or fn != "(Unnamed)"):
            return

        self.clearSyntaxError()
        self.clearFlakesWarnings()

        self.toggleWarning(0, 0, True, msg)

        self.updateVerticalScrollBar()

    @pyqtSlot(str, dict)
    def __processSyntaxCheckResult(self, fn, problems):
        """
        Private slot to report the resulting messages of a syntax check.

        @param fn filename of the checked file
        @type str
        @param problems dictionary with the keys 'error' and 'warnings' which
            hold a list containing details about the error/ warnings
            (file name, line number, column, codestring (only at syntax
            errors), the message)
        @type dict
        """
        # Check if it's the requested file, otherwise ignore signal
        if fn != self.fileName and (bool(self.fileName) or fn != "(Unnamed)"):
            return

        self.clearSyntaxError()
        self.clearFlakesWarnings()

        error = problems.get("error")
        if error:
            _fn, lineno, col, _code, msg = error
            self.toggleSyntaxError(lineno, col, True, msg)

        for _fn, lineno, col, _code, msg in problems.get("py_warnings", []):
            self.toggleWarning(
                lineno, col, True, msg, warningType=EditorWarningKind.Python
            )

        for _fn, lineno, col, _code, msg in problems.get("warnings", []):
            self.toggleWarning(
                lineno, col, True, msg, warningType=EditorWarningKind.Code
            )

        self.updateVerticalScrollBar()

    @pyqtSlot()
    def __initOnlineSyntaxCheck(self):
        """
        Private slot to initialize the online syntax check.
        """
        self.__onlineSyntaxCheckTimer = QTimer(self)
        self.__onlineSyntaxCheckTimer.setSingleShot(True)
        self.__onlineSyntaxCheckTimer.setInterval(
            Preferences.getEditor("OnlineSyntaxCheckInterval") * 1000
        )
        self.__onlineSyntaxCheckTimer.timeout.connect(self.checkSyntax)
        self.textChanged.connect(self.__resetOnlineSyntaxCheckTimer)

    def __resetOnlineSyntaxCheckTimer(self):
        """
        Private method to reset the online syntax check timer.
        """
        if Preferences.getEditor("OnlineSyntaxCheck"):
            self.__onlineSyntaxCheckTimer.stop()
            self.__onlineSyntaxCheckTimer.start()

    def __showCodeMetrics(self):
        """
        Private method to handle the code metrics context menu action.
        """
        from eric7.DataViews.CodeMetricsDialog import CodeMetricsDialog

        if not self.checkDirty():
            return

        self.codemetrics = CodeMetricsDialog()
        self.codemetrics.show()
        self.codemetrics.start(self.fileName)

    def __getCodeCoverageFile(self):
        """
        Private method to get the file name of the file containing coverage
        info.

        @return file name of the coverage file
        @rtype str
        """
        files = []

        if bool(self.__coverageFile):
            # return the path of a previously used coverage file
            return self.__coverageFile

        # first check if the file belongs to a project and there is
        # a project coverage file
        if self.project.isOpen() and self.project.isProjectCategory(
            self.fileName, "SOURCES"
        ):
            pfn = self.project.getMainScript(True)
            if pfn is not None:
                files.extend(
                    [f for f in Utilities.getCoverageFileNames(pfn) if f not in files]
                )

        # now check, if there are coverage files belonging to ourselves
        fn = self.getFileName()
        if fn is not None:
            files.extend(
                [f for f in Utilities.getCoverageFileNames(fn) if f not in files]
            )

        files = list(files)
        if files:
            if len(files) > 1:
                cfn, ok = QInputDialog.getItem(
                    self,
                    self.tr("Code Coverage"),
                    self.tr("Please select a coverage file"),
                    files,
                    0,
                    False,
                )
                if not ok:
                    return ""
            else:
                cfn = files[0]
        else:
            cfn = None

        return cfn

    def __showCodeCoverage(self):
        """
        Private method to handle the code coverage context menu action.
        """
        from eric7.DataViews.PyCoverageDialog import PyCoverageDialog

        fn = self.__getCodeCoverageFile()
        self.__coverageFile = fn
        if fn:
            self.codecoverage = PyCoverageDialog()
            self.codecoverage.show()
            self.codecoverage.start(fn, self.fileName)

    def refreshCoverageAnnotations(self):
        """
        Public method to refresh the code coverage annotations.
        """
        if self.showingNotcoveredMarkers:
            self.codeCoverageShowAnnotations(silent=True)

    def codeCoverageShowAnnotations(self, silent=False, coverageFile=None):
        """
        Public method to handle the show code coverage annotations context
        menu action.

        @param silent flag indicating to not show any dialog (defaults to
            False)
        @type bool (optional)
        @param coverageFile path of the file containing the code coverage data
            (defaults to None)
        @type str (optional)
        """
        from coverage import Coverage  # __IGNORE_WARNING_I102__

        self.__codeCoverageHideAnnotations()

        fn = coverageFile if bool(coverageFile) else self.__getCodeCoverageFile()
        self.__coverageFile = fn

        if fn:
            if FileSystemUtilities.isRemoteFileName(fn):
                coverageInterface = (
                    ericApp().getObject("EricServer").getServiceInterface("Coverage")
                )
                ok, error = coverageInterface.loadCoverageData(fn)
                if not ok and not silent:
                    EricMessageBox.critical(
                        self,
                        self.tr("Load Coverage Data"),
                        self.tr(
                            "<p>The coverage data could not be loaded from file"
                            " <b>{0}</b>.</p><p>Reason: {1}</p>"
                        ).format(self.cfn, error),
                    )
                    return
                missing = coverageInterface.analyzeFile(self.fileName)[3]
            else:
                cover = Coverage(data_file=fn)
                cover.load()
                missing = cover.analysis2(self.fileName)[3]
            if missing:
                for line in missing:
                    handle = self.markerAdd(line - 1, self.notcovered)
                    self.notcoveredMarkers.append(handle)
                self.coverageMarkersShown.emit(True)
                self.__markerMap.update()
            else:
                if not silent:
                    EricMessageBox.information(
                        self,
                        self.tr("Show Code Coverage Annotations"),
                        self.tr("""All lines have been covered."""),
                    )
            self.showingNotcoveredMarkers = True
        else:
            if not silent:
                EricMessageBox.warning(
                    self,
                    self.tr("Show Code Coverage Annotations"),
                    self.tr("""There is no coverage file available."""),
                )

    def __codeCoverageHideAnnotations(self):
        """
        Private method to handle the hide code coverage annotations context
        menu action.
        """
        for handle in self.notcoveredMarkers:
            self.markerDeleteHandle(handle)
        self.notcoveredMarkers.clear()
        self.coverageMarkersShown.emit(False)
        self.showingNotcoveredMarkers = False
        self.__markerMap.update()

    def getCoverageLines(self):
        """
        Public method to get the lines containing a coverage marker.

        @return list of lines containing a coverage marker
        @rtype list of int
        """
        lines = []
        line = -1
        while True:
            line = self.markerFindNext(line + 1, 1 << self.notcovered)
            if line < 0:
                break
            else:
                lines.append(line)
        return lines

    def hasCoverageMarkers(self):
        """
        Public method to test, if there are coverage markers.

        @return flag indicating the presence of coverage markers
        @rtype bool
        """
        return len(self.notcoveredMarkers) > 0

    @pyqtSlot()
    def nextUncovered(self):
        """
        Public slot to handle the 'Next uncovered' context menu action.
        """
        line, index = self.getCursorPosition()
        if line == self.lines() - 1:
            line = 0
        else:
            line += 1
        ucline = self.markerFindNext(line, 1 << self.notcovered)
        if ucline < 0:
            # wrap around
            ucline = self.markerFindNext(0, 1 << self.notcovered)
        if ucline >= 0:
            self.setCursorPosition(ucline, 0)
            self.ensureLineVisible(ucline)

    @pyqtSlot()
    def previousUncovered(self):
        """
        Public slot to handle the 'Previous uncovered' context menu action.
        """
        line, index = self.getCursorPosition()
        if line == 0:
            line = self.lines() - 1
        else:
            line -= 1
        ucline = self.markerFindPrevious(line, 1 << self.notcovered)
        if ucline < 0:
            # wrap around
            ucline = self.markerFindPrevious(self.lines() - 1, 1 << self.notcovered)
        if ucline >= 0:
            self.setCursorPosition(ucline, 0)
            self.ensureLineVisible(ucline)

    def __showProfileData(self):
        """
        Private method to handle the show profile data context menu action.
        """
        from eric7.DataViews.PyProfileDialog import PyProfileDialog

        files = []

        # first check if the file belongs to a project and there is
        # a project profile file
        if self.project.isOpen() and self.project.isProjectCategory(
            self.fileName, "SOURCES"
        ):
            fn = self.project.getMainScript(True)
            if fn is not None:
                files.extend(
                    [f for f in Utilities.getProfileFileNames(fn) if f not in files]
                )

        # now check, if there are profile files belonging to ourselves
        fn = self.getFileName()
        if fn is not None:
            files.extend(
                [f for f in Utilities.getProfileFileNames(fn) if f not in files]
            )

        files = list(files)
        if files:
            if len(files) > 1:
                fn, ok = QInputDialog.getItem(
                    self,
                    self.tr("Profile Data"),
                    self.tr("Please select a profile file"),
                    files,
                    0,
                    False,
                )
                if not ok:
                    return
            else:
                fn = files[0]
        else:
            return

        self.profiledata = PyProfileDialog()
        self.profiledata.show()
        self.profiledata.start(fn, self.fileName)

    def __lmBbookmarks(self):
        """
        Private method to handle the 'LMB toggles bookmark' context menu
        action.
        """
        self.marginMenuActs["LMBbookmarks"].setChecked(True)
        self.marginMenuActs["LMBbreakpoints"].setChecked(False)

    def __lmBbreakpoints(self):
        """
        Private method to handle the 'LMB toggles breakpoint' context menu
        action.
        """
        self.marginMenuActs["LMBbookmarks"].setChecked(True)
        self.marginMenuActs["LMBbreakpoints"].setChecked(False)

    ###########################################################################
    ## Syntax error handling methods below
    ###########################################################################

    def toggleSyntaxError(self, line, index, setError, msg="", show=False):
        """
        Public method to toggle a syntax error indicator.

        @param line line number of the syntax error
        @type int
        @param index index number of the syntax error
        @type int
        @param setError flag indicating if the error marker should be
            set or deleted
        @type bool
        @param msg error message
        @type str
        @param show flag indicating to set the cursor to the error position
        @type bool
        """
        if line == 0:
            line = 1
            # hack to show a syntax error marker, if line is reported to be 0

        line = min(line, self.lines())
        # Limit the line number to the ones we really have to ensure proper display
        # of the error annotation.

        if setError:
            # set a new syntax error marker
            markers = self.markersAtLine(line - 1)
            index += self.indentation(line - 1)
            if not (markers & (1 << self.syntaxerror)):
                handle = self.markerAdd(line - 1, self.syntaxerror)
                self.syntaxerrors[handle] = [(msg, index)]
                self.syntaxerrorToggled.emit(self)
            else:
                for handle in self.syntaxerrors:
                    if (
                        self.markerLine(handle) == line - 1
                        and (msg, index) not in self.syntaxerrors[handle]
                    ):
                        self.syntaxerrors[handle].append((msg, index))
            if show:
                self.setCursorPosition(line - 1, index)
                self.ensureLineVisible(line - 1)
        else:
            for handle in list(self.syntaxerrors):
                if self.markerLine(handle) == line - 1:
                    del self.syntaxerrors[handle]
                    self.markerDeleteHandle(handle)
                    self.syntaxerrorToggled.emit(self)

        self.__setAnnotation(line - 1)
        self.__markerMap.update()

    def getSyntaxErrorLines(self):
        """
        Public method to get the lines containing a syntax error.

        @return list of lines containing a syntax error
        @rtype list of int
        """
        lines = []
        line = -1
        while True:
            line = self.markerFindNext(line + 1, 1 << self.syntaxerror)
            if line < 0:
                break
            else:
                lines.append(line)
        return lines

    def hasSyntaxErrors(self):
        """
        Public method to check for the presence of syntax errors.

        @return flag indicating the presence of syntax errors
        @rtype bool
        """
        return len(self.syntaxerrors) > 0

    @pyqtSlot()
    def gotoSyntaxError(self):
        """
        Public slot to handle the 'Goto syntax error' context menu action.
        """
        seline = self.markerFindNext(0, 1 << self.syntaxerror)
        if seline >= 0:
            index = 0
            for handle in self.syntaxerrors:
                if self.markerLine(handle) == seline:
                    index = self.syntaxerrors[handle][0][1]
            self.setCursorPosition(seline, index)
        self.ensureLineVisible(seline)

    @pyqtSlot()
    def clearSyntaxError(self):
        """
        Public slot to handle the 'Clear all syntax error' context menu action.
        """
        for handle in list(self.syntaxerrors):
            line = self.markerLine(handle) + 1
            self.toggleSyntaxError(line, 0, False)

        self.syntaxerrors.clear()
        self.syntaxerrorToggled.emit(self)

    @pyqtSlot()
    def __showSyntaxError(self, line=-1):
        """
        Private slot to handle the 'Show syntax error message'
        context menu action.

        @param line line number to show the syntax error for
        @type int
        """
        if line == -1:
            line = self.line

        for handle in self.syntaxerrors:
            if self.markerLine(handle) == line:
                errors = [e[0] for e in self.syntaxerrors[handle]]
                EricMessageBox.critical(
                    self, self.tr("Syntax Error"), "\n".join(errors)
                )
                break
        else:
            EricMessageBox.critical(
                self,
                self.tr("Syntax Error"),
                self.tr("No syntax error message available."),
            )

    ###########################################################################
    ## VCS conflict marker handling methods below
    ###########################################################################

    def getVcsConflictMarkerLines(self):
        """
        Public method to determine the lines containing a VCS conflict marker.

        @return list of line numbers containg a VCS conflict marker
        @rtype list of int
        """
        conflictMarkerLines = []

        regExp = re.compile(
            "|".join(Editor.VcsConflictMarkerLineRegExpList), re.MULTILINE
        )
        matches = list(regExp.finditer(self.text()))
        for match in matches:
            line, _ = self.lineIndexFromPosition(match.start())
            conflictMarkerLines.append(line)

        return conflictMarkerLines

    ###########################################################################
    ## Warning handling methods below
    ###########################################################################

    def toggleWarning(
        self,
        line,
        _col,
        setWarning,
        msg="",
        warningType=EditorWarningKind.Code,
    ):
        """
        Public method to toggle a warning indicator.

        Note: This method is used to set pyflakes and code style warnings.

        @param line line number of the warning
        @type int
        @param _col column of the warning (unused)
        @type int
        @param setWarning flag indicating if the warning marker should be
            set or deleted
        @type bool
        @param msg warning message
        @type str
        @param warningType type of warning message
        @type EditorWarningKind
        """
        if line == 0:
            line = 1
            # hack to show a warning marker, if line is reported to be 0

        line = min(line, self.lines())
        # Limit the line number to the ones we really have to ensure proper display
        # of the warning annotation.

        if setWarning:
            # set/amend a new warning marker
            warn = (msg, warningType)
            markers = self.markersAtLine(line - 1)
            if not (markers & (1 << self.warning)):
                handle = self.markerAdd(line - 1, self.warning)
                self._warnings[handle] = [warn]
                self.syntaxerrorToggled.emit(self)
                # signal is also used for warnings
            else:
                for handle in self._warnings:
                    if (
                        self.markerLine(handle) == line - 1
                        and warn not in self._warnings[handle]
                    ):
                        self._warnings[handle].append(warn)
        else:
            for handle in list(self._warnings):
                if self.markerLine(handle) == line - 1:
                    del self._warnings[handle]
                    self.markerDeleteHandle(handle)
                    self.syntaxerrorToggled.emit(self)
                    # signal is also used for warnings

        self.__setAnnotation(line - 1)
        self.__markerMap.update()

    def getWarningLines(self):
        """
        Public method to get the lines containing a warning.

        @return list of lines containing a warning
        @rtype list of int
        """
        lines = []
        line = -1
        while True:
            line = self.markerFindNext(line + 1, 1 << self.warning)
            if line < 0:
                break
            else:
                lines.append(line)
        return lines

    def hasWarnings(self):
        """
        Public method to check for the presence of warnings.

        @return flag indicating the presence of warnings
        @rtype bool
        """
        return len(self._warnings) > 0

    @pyqtSlot()
    def nextWarning(self):
        """
        Public slot to handle the 'Next warning' context menu action.
        """
        line, index = self.getCursorPosition()
        if line == self.lines() - 1:
            line = 0
        else:
            line += 1
        fwline = self.markerFindNext(line, 1 << self.warning)
        if fwline < 0:
            # wrap around
            fwline = self.markerFindNext(0, 1 << self.warning)
        if fwline >= 0:
            self.setCursorPosition(fwline, 0)
            self.ensureLineVisible(fwline)

    @pyqtSlot()
    def previousWarning(self):
        """
        Public slot to handle the 'Previous warning' context menu action.
        """
        line, index = self.getCursorPosition()
        if line == 0:
            line = self.lines() - 1
        else:
            line -= 1
        fwline = self.markerFindPrevious(line, 1 << self.warning)
        if fwline < 0:
            # wrap around
            fwline = self.markerFindPrevious(self.lines() - 1, 1 << self.warning)
        if fwline >= 0:
            self.setCursorPosition(fwline, 0)
            self.ensureLineVisible(fwline)

    @pyqtSlot()
    def clearFlakesWarnings(self):
        """
        Public slot to clear all pyflakes warnings.
        """
        self.__clearTypedWarning(EditorWarningKind.Code)
        self.__clearTypedWarning(EditorWarningKind.Python)

    @pyqtSlot()
    def clearStyleWarnings(self):
        """
        Public slot to clear all style warnings.
        """
        self.__clearTypedWarning(EditorWarningKind.Style)

    @pyqtSlot()
    def clearInfoWarnings(self):
        """
        Public slot to clear all info warnings.
        """
        self.__clearTypedWarning(EditorWarningKind.Info)

    @pyqtSlot()
    def clearErrorWarnings(self):
        """
        Public slot to clear all error warnings.
        """
        self.__clearTypedWarning(EditorWarningKind.Error)

    @pyqtSlot()
    def clearCodeWarnings(self):
        """
        Public slot to clear all code warnings.
        """
        self.__clearTypedWarning(EditorWarningKind.Code)

    def __clearTypedWarning(self, warningKind):
        """
        Private method to clear warnings of a specific kind.

        @param warningKind kind of warning to clear
        @type EditorWarningKind
        """
        for handle in list(self._warnings):
            issues = []
            for msg, warningType in self._warnings[handle]:
                if warningType == warningKind:
                    continue

                issues.append((msg, warningType))

            if issues:
                self._warnings[handle] = issues
                self.__setAnnotation(self.markerLine(handle))
            else:
                del self._warnings[handle]
                self.__setAnnotation(self.markerLine(handle))
                self.markerDeleteHandle(handle)
        self.syntaxerrorToggled.emit(self)
        self.__markerMap.update()

    @pyqtSlot()
    def clearWarnings(self):
        """
        Public slot to clear all warnings.
        """
        for handle in self._warnings:
            self._warnings[handle] = []
            self.__setAnnotation(self.markerLine(handle))
            self.markerDeleteHandle(handle)
        self._warnings.clear()
        self.syntaxerrorToggled.emit(self)
        self.__markerMap.update()

    @pyqtSlot()
    def __showWarning(self, line=-1):
        """
        Private slot to handle the 'Show warning' context menu action.

        @param line line number to show the warning for
        @type int
        """
        if line == -1:
            line = self.line

        for handle in self._warnings:
            if self.markerLine(handle) == line:
                EricMessageBox.warning(
                    self,
                    self.tr("Warning"),
                    "\n".join([w[0] for w in self._warnings[handle]]),
                )
                break
        else:
            EricMessageBox.warning(
                self, self.tr("Warning"), self.tr("No warning messages available.")
            )

    ###########################################################################
    ## Annotation handling methods below
    ###########################################################################

    @pyqtSlot()
    def __setAnnotationStyles(self):
        """
        Private slot to define the style used by inline annotations.
        """
        if hasattr(QsciScintilla, "annotate"):
            self.annotationWarningStyle = QsciScintilla.STYLE_LASTPREDEFINED + 1
            self.SendScintilla(
                QsciScintilla.SCI_STYLESETFORE,
                self.annotationWarningStyle,
                Preferences.getEditorColour("AnnotationsWarningForeground"),
            )
            self.SendScintilla(
                QsciScintilla.SCI_STYLESETBACK,
                self.annotationWarningStyle,
                Preferences.getEditorColour("AnnotationsWarningBackground"),
            )

            self.annotationErrorStyle = self.annotationWarningStyle + 1
            self.SendScintilla(
                QsciScintilla.SCI_STYLESETFORE,
                self.annotationErrorStyle,
                Preferences.getEditorColour("AnnotationsErrorForeground"),
            )
            self.SendScintilla(
                QsciScintilla.SCI_STYLESETBACK,
                self.annotationErrorStyle,
                Preferences.getEditorColour("AnnotationsErrorBackground"),
            )

            self.annotationStyleStyle = self.annotationErrorStyle + 1
            self.SendScintilla(
                QsciScintilla.SCI_STYLESETFORE,
                self.annotationStyleStyle,
                Preferences.getEditorColour("AnnotationsStyleForeground"),
            )
            self.SendScintilla(
                QsciScintilla.SCI_STYLESETBACK,
                self.annotationStyleStyle,
                Preferences.getEditorColour("AnnotationsStyleBackground"),
            )

            self.annotationInfoStyle = self.annotationStyleStyle + 1
            self.SendScintilla(
                QsciScintilla.SCI_STYLESETFORE,
                self.annotationInfoStyle,
                Preferences.getEditorColour("AnnotationsInfoForeground"),
            )
            self.SendScintilla(
                QsciScintilla.SCI_STYLESETBACK,
                self.annotationInfoStyle,
                Preferences.getEditorColour("AnnotationsInfoBackground"),
            )

    def __setAnnotation(self, line):
        """
        Private method to set the annotations for the given line.

        @param line number of the line that needs annotation
        @type int
        """
        if hasattr(QsciScintilla, "annotate"):
            warningAnnotations = []
            errorAnnotations = []
            styleAnnotations = []
            infoAnnotations = []

            # step 1: do warnings
            for handle in self._warnings:
                if self.markerLine(handle) == line:
                    for msg, warningType in self._warnings[handle]:
                        if warningType == EditorWarningKind.Info:
                            infoAnnotations.append(self.tr("Info: {0}").format(msg))
                        elif warningType == EditorWarningKind.Error:
                            errorAnnotations.append(self.tr("Error: {0}").format(msg))
                        elif warningType == EditorWarningKind.Style:
                            styleAnnotations.append(self.tr("Style: {0}").format(msg))
                        elif warningType == EditorWarningKind.Python:
                            warningAnnotations.append(msg)
                        else:
                            warningAnnotations.append(
                                self.tr("Warning: {0}").format(msg)
                            )

            # step 2: do syntax errors
            for handle in self.syntaxerrors:
                if self.markerLine(handle) == line:
                    for msg, _ in self.syntaxerrors[handle]:
                        errorAnnotations.append(self.tr("Error: {0}").format(msg))

            # step 3: assemble the annotation
            annotations = []
            if infoAnnotations:
                annotationInfoTxt = "\n".join(infoAnnotations)
                if styleAnnotations or warningAnnotations or errorAnnotations:
                    annotationInfoTxt += "\n"
                annotations.append(
                    QsciStyledText(annotationInfoTxt, self.annotationInfoStyle)
                )

            if styleAnnotations:
                annotationStyleTxt = "\n".join(styleAnnotations)
                if warningAnnotations or errorAnnotations:
                    annotationStyleTxt += "\n"
                annotations.append(
                    QsciStyledText(annotationStyleTxt, self.annotationStyleStyle)
                )

            if warningAnnotations:
                annotationWarningTxt = "\n".join(warningAnnotations)
                if errorAnnotations:
                    annotationWarningTxt += "\n"
                annotations.append(
                    QsciStyledText(annotationWarningTxt, self.annotationWarningStyle)
                )

            if errorAnnotations:
                annotationErrorTxt = "\n".join(errorAnnotations)
                annotations.append(
                    QsciStyledText(annotationErrorTxt, self.annotationErrorStyle)
                )

            if annotations:
                self.annotate(line, annotations)
            else:
                self.clearAnnotations(line)

    def __refreshAnnotations(self):
        """
        Private method to refresh the annotations.
        """
        if hasattr(QsciScintilla, "annotate"):
            self.clearAnnotations()
            for handle in self._warnings:
                line = self.markerLine(handle)
                self.__setAnnotation(line)
            for handle in self.syntaxerrors:
                line = self.markerLine(handle)
                self.__setAnnotation(line)

    #################################################################
    ## Fold handling methods
    #################################################################

    @pyqtSlot()
    def toggleCurrentFold(self):
        """
        Public slot to toggle the fold containing the current line.
        """
        line, index = self.getCursorPosition()
        self.foldLine(line)

    def expandFoldWithChildren(self, line=-1):
        """
        Public method to expand the current fold including its children.

        @param line number of line to be expanded
        @type int
        """
        if line == -1:
            line, index = self.getCursorPosition()

        self.SendScintilla(
            QsciScintilla.SCI_FOLDCHILDREN, line, QsciScintilla.SC_FOLDACTION_EXPAND
        )

    def collapseFoldWithChildren(self, line=-1):
        """
        Public method to collapse the current fold including its children.

        @param line number of line to be expanded
        @type int
        """
        if line == -1:
            line, index = self.getCursorPosition()

        self.SendScintilla(
            QsciScintilla.SCI_FOLDCHILDREN, line, QsciScintilla.SC_FOLDACTION_CONTRACT
        )

    @pyqtSlot()
    def __contextMenuExpandFoldWithChildren(self):
        """
        Private slot to handle the context menu expand with children action.
        """
        self.expandFoldWithChildren(self.line)

    @pyqtSlot()
    def __contextMenuCollapseFoldWithChildren(self):
        """
        Private slot to handle the context menu collapse with children action.
        """
        self.collapseFoldWithChildren(self.line)

    #################################################################
    ## Macro handling methods
    #################################################################

    def __getMacroName(self):
        """
        Private method to select a macro name from the list of macros.

        @return Tuple of macro name and a flag, indicating, if the user
            pressed ok or canceled the operation.
        @rtype tuple of (str, bool)
        """
        qs = []
        for s in self.macros:
            qs.append(s)
        qs.sort()
        return QInputDialog.getItem(
            self, self.tr("Macro Name"), self.tr("Select a macro name:"), qs, 0, False
        )

    def macroRun(self):
        """
        Public method to execute a macro.
        """
        name, ok = self.__getMacroName()
        if ok and name:
            self.macros[name].play()

    def macroDelete(self):
        """
        Public method to delete a macro.
        """
        name, ok = self.__getMacroName()
        if ok and name:
            del self.macros[name]

    def macroLoad(self):
        """
        Public method to load a macro from a file.
        """
        configDir = EricUtilities.getConfigDir()
        fname = EricFileDialog.getOpenFileName(
            self,
            self.tr("Load macro file"),
            configDir,
            self.tr("Macro files (*.macro)"),
        )

        if not fname:
            return  # user aborted

        try:
            with open(fname, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except OSError:
            EricMessageBox.critical(
                self,
                self.tr("Error loading macro"),
                self.tr("<p>The macro file <b>{0}</b> could not be read.</p>").format(
                    fname
                ),
            )
            return

        if len(lines) != 2:
            EricMessageBox.critical(
                self,
                self.tr("Error loading macro"),
                self.tr("<p>The macro file <b>{0}</b> is corrupt.</p>").format(fname),
            )
            return

        macro = QsciMacro(lines[1], self)
        self.macros[lines[0].strip()] = macro

    def macroSave(self):
        """
        Public method to save a macro to a file.
        """
        configDir = EricUtilities.getConfigDir()

        name, ok = self.__getMacroName()
        if not ok or not name:
            return  # user abort

        fname, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.tr("Save macro file"),
            configDir,
            self.tr("Macro files (*.macro)"),
            "",
            EricFileDialog.DontConfirmOverwrite,
        )

        if not fname:
            return  # user aborted

        fpath = pathlib.Path(fname)
        if not fpath.suffix:
            ex = selectedFilter.split("(*")[1].split(")")[0]
            if ex:
                fpath = fpath.with_suffix(ex)
        if fpath.exists():
            res = EricMessageBox.yesNo(
                self,
                self.tr("Save macro"),
                self.tr(
                    "<p>The macro file <b>{0}</b> already exists. Overwrite it?</p>"
                ).format(fpath),
                icon=EricMessageBox.Warning,
            )
            if not res:
                return

        try:
            with fpath.open("w", encoding="utf-8") as f:
                f.write("{0}{1}".format(name, "\n"))
                f.write(self.macros[name].save())
        except OSError:
            EricMessageBox.critical(
                self,
                self.tr("Error saving macro"),
                self.tr(
                    "<p>The macro file <b>{0}</b> could not be written.</p>"
                ).format(fpath),
            )
            return

    def macroRecordingStart(self):
        """
        Public method to start macro recording.
        """
        if self.recording:
            res = EricMessageBox.yesNo(
                self,
                self.tr("Start Macro Recording"),
                self.tr("Macro recording is already active. Start new?"),
                icon=EricMessageBox.Warning,
                yesDefault=True,
            )
            if res:
                self.macroRecordingStop()
            else:
                return
        else:
            self.recording = True

        self.curMacro = QsciMacro(self)
        self.curMacro.startRecording()

    def macroRecordingStop(self):
        """
        Public method to stop macro recording.
        """
        if not self.recording:
            return  # we are not recording

        self.curMacro.endRecording()
        self.recording = False

        name, ok = QInputDialog.getText(
            self,
            self.tr("Macro Recording"),
            self.tr("Enter name of the macro:"),
            QLineEdit.EchoMode.Normal,
        )

        if ok and name:
            self.macros[name] = self.curMacro

        self.curMacro = None

    #################################################################
    ## Overwritten methods
    #################################################################

    def undo(self):
        """
        Public method to undo the last recorded change.
        """
        super().undo()
        self.undoAvailable.emit(self.isUndoAvailable())
        self.redoAvailable.emit(self.isRedoAvailable())

    def redo(self):
        """
        Public method to redo the last recorded change.
        """
        super().redo()
        self.undoAvailable.emit(self.isUndoAvailable())
        self.redoAvailable.emit(self.isRedoAvailable())

    def close(self):
        """
        Public method called when the window gets closed.

        This overwritten method redirects the action to our
        ViewManager.closeEditor, which in turn calls our closeIt
        method.

        @return flag indicating a successful close of the editor
        @rtype bool
        """
        return self.vm.closeEditor(self)

    def closeIt(self):
        """
        Public method called by the viewmanager to finally get rid of us.
        """
        if Preferences.getEditor("ClearBreaksOnClose") and not self.__clones:
            self.__menuClearBreakpoints()

        for clone in self.__clones[:]:
            self.removeClone(clone)
            clone.removeClone(self)

        self.breakpointModel.rowsAboutToBeRemoved.disconnect(self.__deleteBreakPoints)
        self.breakpointModel.dataAboutToBeChanged.disconnect(
            self.__breakPointDataAboutToBeChanged
        )
        self.breakpointModel.dataChanged.disconnect(self.__changeBreakPoints)
        self.breakpointModel.rowsInserted.disconnect(self.__addBreakPoints)

        if self.syntaxCheckService is not None:
            self.syntaxCheckService.syntaxChecked.disconnect(
                self.__processSyntaxCheckResult
            )
            self.syntaxCheckService.error.disconnect(self.__processSyntaxCheckError)

        if self.spell:
            self.spell.stopIncrementalCheck()

        with contextlib.suppress(TypeError):
            self.project.projectPropertiesChanged.disconnect(
                self.__projectPropertiesChanged
            )

        if self.fileName:
            self.taskViewer.clearFileTasks(self.fileName, True)

        super().close()

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

        if (
            ev.key() == Qt.Key.Key_Comma
            and ev.modifiers() & Qt.KeyboardModifier.KeypadModifier
        ):
            # Change the numpad ',' to always insert a '.' because that is what
            # is needed in programming.

            # Create a new QKeyEvent to substitute the original one
            ev = QKeyEvent(
                ev.type(),
                Qt.Key.Key_Period,
                ev.modifiers(),
                ".",
                ev.isAutoRepeat(),
                ev.count(),
            )

            super().keyPressEvent(ev)
            return

        txt = ev.text()

        # See it is text to insert.
        if len(txt) and txt >= " ":
            if self.hasSelectedText() and txt in Editor.EncloseChars:
                encloseSelectedText(Editor.EncloseChars[txt])
                ev.accept()
                return

            super().keyPressEvent(ev)
        else:
            ev.ignore()

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
        self.recolor()

        self.vm.editActGrp.setEnabled(True)
        self.vm.editorActGrp.setEnabled(True)
        self.vm.copyActGrp.setEnabled(True)
        self.vm.viewActGrp.setEnabled(True)
        self.vm.searchActGrp.setEnabled(True)

        with contextlib.suppress(AttributeError):
            self.setCaretWidth(self.caretWidth)
        if not self.dbs.isDebugging:
            self.__updateReadOnly(False)
        self.setCursorFlashTime(QApplication.cursorFlashTime())

        if (
            self.fileName
            and FileSystemUtilities.isRemoteFileName(self.fileName)
            and not self.inReopenPrompt
        ):
            self.inReopenPrompt = True
            self.checkRereadFile()
            self.inReopenPrompt = False

        super().focusInEvent(event)

    def focusOutEvent(self, event):
        """
        Protected method called when the editor loses focus.

        @param event the event object
        @type QFocusEvent
        """
        if (
            Preferences.getEditor("AutosaveOnFocusLost")
            and self.__shouldAutosave()
            and not self.inReopenPrompt
        ):
            self.saveFile()

        self.vm.editorActGrp.setEnabled(False)
        self.setCaretWidth(0)

        self.cancelCallTips()

        super().focusOutEvent(event)

    def changeEvent(self, evt):
        """
        Protected method called to process an event.

        This implements special handling for the events showMaximized,
        showMinimized and showNormal. The windows caption is shortened
        for the minimized mode and reset to the full filename for the
        other modes. This is to make the editor windows work nicer
        with the QWorkspace.

        @param evt the event, that was generated
        @type QEvent
        """
        if evt.type() == QEvent.Type.WindowStateChange and bool(self.fileName):
            cap = (
                os.path.basename(self.fileName)
                if self.windowState() == Qt.WindowState.WindowMinimized
                else self.fileName
            )
            if self.checkReadOnly():
                cap = self.tr("{0} (ro)").format(cap)
            self.setWindowTitle(cap)

        super().changeEvent(evt)

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
            self.vm.eventFilter(self, event)
            super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, evt):
        """
        Protected method to handle mouse double click events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        super().mouseDoubleClickEvent(evt)

        # accept all double click events even if not handled by QScintilla
        evt.accept()

        self.mouseDoubleClick.emit(evt.position().toPoint(), evt.buttons())

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

        if evt.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if delta < 0:
                self.gotoMethodClass(False)
            elif delta > 0:
                self.gotoMethodClass(True)
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
                zoom = (self.getZoom() + 10) / 10.0
                pinch.setTotalScaleFactor(zoom)
            elif pinch.state() == Qt.GestureState.GestureUpdated:
                zoom = int(pinch.totalScaleFactor() * 10) - 10
                if zoom <= -9:
                    zoom = -9
                    pinch.setTotalScaleFactor(0.1)
                elif zoom >= 20:
                    zoom = 20
                    pinch.setTotalScaleFactor(3.0)
                self.zoomTo(zoom)
            evt.accept()

    def resizeEvent(self, evt):
        """
        Protected method handling resize events.

        @param evt reference to the resize event
        @type QResizeEvent
        """
        super().resizeEvent(evt)
        self.__markerMap.calculateGeometry()

    def viewportEvent(self, evt):
        """
        Protected method handling event of the viewport.

        @param evt reference to the event
        @type QEvent
        @return flag indiating that the event was handled
        @rtype bool
        """
        with contextlib.suppress(AttributeError):
            self.__markerMap.calculateGeometry()
        return super().viewportEvent(evt)

    def __updateReadOnly(self, bForce=True):
        """
        Private method to update the readOnly information for this editor.

        If bForce is True, then updates everything regardless if
        the attributes have actually changed, such as during
        initialization time.  A signal is emitted after the
        caption change.

        @param bForce True to force change, False to only update and emit
                signal if there was an attribute change.
        @type bool
        """
        if self.fileName == "" or FileSystemUtilities.isDeviceFileName(self.fileName):
            return

        readOnly = self.checkReadOnly()
        if not bForce and (readOnly == self.isReadOnly()):
            return

        cap = self.fileName
        if readOnly:
            cap = self.tr("{0} (ro)".format(cap))
        self.setReadOnly(readOnly)
        self.setWindowTitle(cap)
        self.captionChanged.emit(cap, self)

    def checkReadOnly(self):
        """
        Public method to check the 'read only' state.

        @return flag indicate a 'read only' state
        @rtype bool
        """
        return (
            (
                FileSystemUtilities.isPlainFileName(self.fileName)
                and not os.access(self.fileName, os.W_OK)
            )
            or (
                FileSystemUtilities.isRemoteFileName(self.fileName)
                and not self.__remotefsInterface.access(
                    FileSystemUtilities.plainFileName(self.fileName), "write"
                )
            )
            or self.isReadOnly()
        )

    def setCheckExternalModificationEnabled(self, enable):
        """
        Public method to enable or disable the check for external modifications.

        @param enable flag indicating the new enabled state
        @type bool
        """
        self.__checkExternalModification = enable

    @pyqtSlot()
    def checkRereadFile(self):
        """
        Public slot to check, if the file needs to be re-read, and refresh it if
        needed.
        """
        if self.__checkExternalModification and self.checkModificationTime():
            if Preferences.getEditor("AutoReopen") and not self.isModified():
                self.refresh()
            else:
                msg = self.tr(
                    """<p>The file <b>{0}</b> has been changed while it"""
                    """ was opened in eric. Reread it?</p>"""
                ).format(self.fileName)
                yesDefault = True
                if self.isModified():
                    msg += self.tr(
                        """<br><b>Warning:</b> You will lose"""
                        """ your changes upon reopening it."""
                    )
                    yesDefault = False
                res = EricMessageBox.yesNo(
                    self,
                    self.tr("File changed"),
                    msg,
                    icon=EricMessageBox.Warning,
                    yesDefault=yesDefault,
                )
                if res:
                    self.refresh()
                else:
                    # do not prompt for this change again...
                    self.recordModificationTime()

    def getModificationTime(self):
        """
        Public method to get the time of the latest (saved) modification.

        @return time of the latest modification
        @rtype int
        """
        return self.lastModified

    @pyqtSlot()
    def recordModificationTime(self, filename=""):
        """
        Public slot to record the modification time of our file.

        @param filename name of the file to record the modification tome for
            (defaults to "")
        @type str (optional)
        """
        if not filename:
            filename = self.fileName

        if filename:
            if FileSystemUtilities.isRemoteFileName(filename):
                filename = FileSystemUtilities.plainFileName(filename)
                if self.__remotefsInterface.exists(filename):
                    mtime = self.__remotefsInterface.stat(
                        FileSystemUtilities.plainFileName(filename), ["st_mtime"]
                    )["st_mtime"]
                    self.lastModified = mtime if mtime is not None else 0
                else:
                    self.lastModified = 0
            elif pathlib.Path(filename).exists():
                self.lastModified = pathlib.Path(filename).stat().st_mtime
            else:
                self.lastModified = 0

        else:
            self.lastModified = 0

    def checkModificationTime(self, filename=""):
        """
        Public method to check, if the modification time of the file is different
        from the recorded one.

        @param filename name of the file to check against (defaults to "")
        @type str (optional)
        @return flag indicating that the file modification time is different. For
            non-existent files a 'False' value will be reported.
        @rtype bool
        """
        if not filename:
            filename = self.fileName

        if filename:
            if (
                FileSystemUtilities.isRemoteFileName(filename)
                and not self.dbs.isDebugging
            ):
                plainFilename = FileSystemUtilities.plainFileName(filename)
                if self.__remotefsInterface.exists(plainFilename):
                    mtime = self.__remotefsInterface.stat(plainFilename, ["st_mtime"])[
                        "st_mtime"
                    ]
                    return mtime != self.lastModified

            elif (
                FileSystemUtilities.isPlainFileName(filename)
                and pathlib.Path(filename).exists()
            ):
                return pathlib.Path(filename).stat().st_mtime != self.lastModified

        return False

    @pyqtSlot()
    def refresh(self):
        """
        Public slot to refresh the editor contents.
        """
        # save cursor position
        cline, cindex = self.getCursorPosition()

        # save bookmarks and breakpoints and clear them
        bmlist = self.getBookmarks()
        self.clearBookmarks()

        # clear syntax error markers
        self.clearSyntaxError()

        # clear flakes warning markers
        self.clearWarnings()

        # clear breakpoint markers
        for handle in self.breaks:
            self.markerDeleteHandle(handle)
        self.breaks.clear()

        # reread the file
        try:
            self.readFile(self.fileName, noempty=True)
        except OSError:
            # do not prompt for this change again...
            self.lastModified = QDateTime.currentDateTime()
        self.setModified(False)
        self.__convertTabs()

        # re-initialize the online change tracer
        self.__reinitOnlineChangeTrace()

        # reset cursor position
        self.setCursorPosition(cline, cindex)
        self.ensureCursorVisible()

        # reset bookmarks and breakpoints to their old position
        if bmlist:
            for bm in bmlist:
                self.toggleBookmark(bm)
        self.__restoreBreakpoints()

        self.editorSaved.emit(self.fileName)
        self.checkSyntax()

        self.__markerMap.update()

        self.refreshed.emit()

    @pyqtSlot()
    def reload(self):
        """
        Public slot to reload the editor contents checking its modification state first.
        """
        ok = (
            EricMessageBox.yesNo(
                self,
                self.tr("Reload File"),
                self.tr(
                    "<p>The editor contains unsaved modifications.</p>"
                    "<p><b>Warning:</b> You will lose your changes upon reloading"
                    " it.</p><p>Shall the editor really be reloaded?</p>"
                ),
                icon=EricMessageBox.Warning,
            )
            if self.isModified()
            else True
        )
        if ok:
            self.refresh()

    def setMonospaced(self, on):
        """
        Public method to set/reset a monospaced font.

        @param on flag to indicate usage of a monospace font
        @type bool
        """
        if on:
            if not self.lexer_:
                f = Preferences.getEditorOtherFonts("MonospacedFont")
                self.monospacedStyles(f)
        else:
            if not self.lexer_:
                self.clearStyles()
                self.__setMarginsDisplay()
            self.setFont(Preferences.getEditorOtherFonts("DefaultFont"))

        self.useMonospaced = on

    def clearStyles(self):
        """
        Public method to set the styles according the selected Qt style
        or the selected editor colours.
        """
        super().clearStyles()
        if Preferences.getEditor("OverrideEditAreaColours"):
            self.setColor(Preferences.getEditorColour("EditAreaForeground"))
            self.setPaper(Preferences.getEditorColour("EditAreaBackground"))

    #################################################################
    ## Drag and Drop Support
    #################################################################

    def dragEnterEvent(self, event):
        """
        Protected method to handle the drag enter event.

        @param event the drag enter event
        @type QDragEnterEvent
        """
        self.inDragDrop = event.mimeData().hasUrls()
        if self.inDragDrop:
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """
        Protected method to handle the drag move event.

        @param event the drag move event
        @type QDragMoveEvent
        """
        if self.inDragDrop:
            event.accept()
        else:
            super().dragMoveEvent(event)

    def dragLeaveEvent(self, event):
        """
        Protected method to handle the drag leave event.

        @param event the drag leave event
        @type QDragLeaveEvent
        """
        if self.inDragDrop:
            self.inDragDrop = False
            event.accept()
        else:
            super().dragLeaveEvent(event)

    def dropEvent(self, event):
        """
        Protected method to handle the drop event.

        @param event the drop event
        @type QDropEvent
        """
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                fname = url.toLocalFile()
                if fname:
                    if not pathlib.Path(fname).is_dir():
                        self.vm.openSourceFile(fname)
                    else:
                        EricMessageBox.information(
                            self,
                            self.tr("Drop Error"),
                            self.tr("""<p><b>{0}</b> is not a file.</p>""").format(
                                fname
                            ),
                        )
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

        self.inDragDrop = False

    #################################################################
    ## Support for Qt resources files
    #################################################################

    def __initContextMenuResources(self):
        """
        Private method used to setup the Resources context sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        menu = QMenu(self.tr("Resources"))

        menu.addAction(self.tr("Add file..."), self.__addFileResource)
        menu.addAction(self.tr("Add files..."), self.__addFileResources)
        menu.addAction(self.tr("Add aliased file..."), self.__addFileAliasResource)
        menu.addAction(
            self.tr("Add localized resource..."), self.__addLocalizedResource
        )
        menu.addSeparator()
        menu.addAction(self.tr("Add resource frame"), self.__addResourceFrame)

        menu.aboutToShow.connect(self.__showContextMenuResources)

        return menu

    @pyqtSlot()
    def __showContextMenuResources(self):
        """
        Private slot handling the aboutToShow signal of the resources context
        menu.
        """
        self.showMenu.emit("Resources", self.resourcesMenu, self)

    def __addFileResource(self):
        """
        Private method to handle the Add file context menu action.
        """
        dirStr = os.path.dirname(self.fileName)
        file = EricFileDialog.getOpenFileName(
            self, self.tr("Add file resource"), dirStr, ""
        )
        if file:
            relFile = QDir(dirStr).relativeFilePath(file)
            line, index = self.getCursorPosition()
            self.insert("  <file>{0}</file>\n".format(relFile))
            self.setCursorPosition(line + 1, index)

    def __addFileResources(self):
        """
        Private method to handle the Add files context menu action.
        """
        dirStr = os.path.dirname(self.fileName)
        files = EricFileDialog.getOpenFileNames(
            self, self.tr("Add file resources"), dirStr, ""
        )
        if files:
            myDir = QDir(dirStr)
            filesText = ""
            for file in files:
                relFile = myDir.relativeFilePath(file)
                filesText += "  <file>{0}</file>\n".format(relFile)
            line, index = self.getCursorPosition()
            self.insert(filesText)
            self.setCursorPosition(line + len(files), index)

    def __addFileAliasResource(self):
        """
        Private method to handle the Add aliased file context menu action.
        """
        dirStr = os.path.dirname(self.fileName)
        file = EricFileDialog.getOpenFileName(
            self, self.tr("Add aliased file resource"), dirStr, ""
        )
        if file:
            relFile = QDir(dirStr).relativeFilePath(file)
            alias, ok = QInputDialog.getText(
                self,
                self.tr("Add aliased file resource"),
                self.tr("Alias for file <b>{0}</b>:").format(relFile),
                QLineEdit.EchoMode.Normal,
                relFile,
            )
            if ok and alias:
                line, index = self.getCursorPosition()
                self.insert('  <file alias="{1}">{0}</file>\n'.format(relFile, alias))
                self.setCursorPosition(line + 1, index)

    def __addLocalizedResource(self):
        """
        Private method to handle the Add localized resource context menu
        action.
        """
        from eric7.Project.AddLanguageDialog import AddLanguageDialog

        dlg = AddLanguageDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            lang = dlg.getSelectedLanguage()
            line, index = self.getCursorPosition()
            self.insert('<qresource lang="{0}">\n</qresource>\n'.format(lang))
            self.setCursorPosition(line + 2, index)

    def __addResourceFrame(self):
        """
        Private method to handle the Add resource frame context menu action.
        """
        line, index = self.getCursorPosition()
        self.insert(
            "<!DOCTYPE RCC>\n"
            '<RCC version="1.0">\n'
            "<qresource>\n"
            "</qresource>\n"
            "</RCC>\n"
        )
        self.setCursorPosition(line + 5, index)

    #################################################################
    ## Support for diagrams below
    #################################################################

    def __showClassDiagram(self):
        """
        Private method to handle the Class Diagram context menu action.
        """
        from eric7.Graphics.UMLDialog import UMLDialog, UMLDialogType

        if not self.checkDirty():
            return

        self.classDiagram = UMLDialog(
            UMLDialogType.CLASS_DIAGRAM,
            self.project,
            self.fileName,
            self,
            noAttrs=False,
        )
        self.classDiagram.show()

    def __showPackageDiagram(self):
        """
        Private method to handle the Package Diagram context menu action.
        """
        from eric7.Graphics.UMLDialog import UMLDialog, UMLDialogType

        if not self.checkDirty():
            return

        if FileSystemUtilities.isRemoteFileName(self.fileName):  # noqa: Y108
            package = (
                self.fileName
                if self.__remotefsInterface.isdir(self.fileName)
                else self.__remotefsInterface.dirname(self.fileName)
            )
        else:
            package = (
                self.fileName
                if os.path.isdir(self.fileName)
                else os.path.dirname(self.fileName)
            )
        res = EricMessageBox.yesNo(
            self,
            self.tr("Package Diagram"),
            self.tr("""Include class attributes?"""),
            yesDefault=True,
        )
        self.packageDiagram = UMLDialog(
            UMLDialogType.PACKAGE_DIAGRAM, self.project, package, self, noAttrs=not res
        )
        self.packageDiagram.show()

    def __showImportsDiagram(self):
        """
        Private method to handle the Imports Diagram context menu action.
        """
        from eric7.Graphics.UMLDialog import UMLDialog, UMLDialogType

        if not self.checkDirty():
            return

        package = os.path.dirname(self.fileName)
        res = EricMessageBox.yesNo(
            self,
            self.tr("Imports Diagram"),
            self.tr("""Include imports from external modules?"""),
        )
        self.importsDiagram = UMLDialog(
            UMLDialogType.IMPORTS_DIAGRAM,
            self.project,
            package,
            self,
            showExternalImports=res,
        )
        self.importsDiagram.show()

    def __showApplicationDiagram(self):
        """
        Private method to handle the Imports Diagram context menu action.
        """
        from eric7.Graphics.UMLDialog import UMLDialog, UMLDialogType

        res = EricMessageBox.yesNo(
            self,
            self.tr("Application Diagram"),
            self.tr("""Include module names?"""),
            yesDefault=True,
        )
        self.applicationDiagram = UMLDialog(
            UMLDialogType.APPLICATION_DIAGRAM, self.project, self, noModules=not res
        )
        self.applicationDiagram.show()

    @pyqtSlot()
    def __loadDiagram(self):
        """
        Private slot to load a diagram from file.
        """
        from eric7.Graphics.UMLDialog import UMLDialog, UMLDialogType

        self.loadedDiagram = UMLDialog(
            UMLDialogType.NO_DIAGRAM, self.project, parent=self
        )
        if self.loadedDiagram.load():
            self.loadedDiagram.show(fromFile=True)
        else:
            self.loadedDiagram = None

    #######################################################################
    ## Typing aids related methods below
    #######################################################################

    @pyqtSlot()
    def __toggleTypingAids(self):
        """
        Private slot to toggle the typing aids.
        """
        if self.menuActs["TypingAidsEnabled"].isChecked():
            self.completer.setEnabled(True)
        else:
            self.completer.setEnabled(False)

    #######################################################################
    ## Auto-completing templates
    #######################################################################

    def editorCommand(self, cmd):
        """
        Public method to perform a simple editor command.

        @param cmd the scintilla command to be performed
        @type int
        """
        if cmd == QsciScintilla.SCI_TAB:
            try:
                templateViewer = ericApp().getObject("TemplateViewer")
            except KeyError:
                # template viewer is not active
                templateViewer = None

            if templateViewer is not None:
                line, index = self.getCursorPosition()
                tmplName = self.getWordLeft(line, index)
                if tmplName:
                    if templateViewer.hasTemplate(tmplName, self.getLanguage()):
                        self.__applyTemplate(tmplName, self.getLanguage())
                        return
                    else:
                        templateNames = templateViewer.getTemplateNames(
                            tmplName, self.getLanguage()
                        )
                        if len(templateNames) == 1:
                            self.__applyTemplate(templateNames[0], self.getLanguage())
                            return
                        elif len(templateNames) > 1:
                            self.showUserList(
                                TemplateCompletionListID,
                                [
                                    "{0}?{1:d}".format(t, EditorIconId.TemplateImage)
                                    for t in templateNames
                                ],
                            )
                            return

        elif cmd == QsciScintilla.SCI_DELETEBACK:
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

    def __applyTemplate(self, templateName, language):
        """
        Private method to apply a template by name.

        @param templateName name of the template to apply
        @type str
        @param language name of the language (group) to get the template
            from
        @type str
        """
        try:
            templateViewer = ericApp().getObject("TemplateViewer")
        except KeyError:
            # template viewer is not active
            return

        if templateViewer.hasTemplate(templateName, language):
            self.extendSelectionWordLeft()
            templateViewer.applyNamedTemplate(templateName, language)

    #######################################################################
    ## Project related methods
    #######################################################################

    @pyqtSlot()
    def __projectPropertiesChanged(self):
        """
        Private slot to handle changes of the project properties.
        """
        if self.spell:
            pwl, pel = self.project.getProjectDictionaries()
            self.__setSpellingLanguage(
                self.project.getProjectSpellLanguage(), pwl=pwl, pel=pel
            )

        editorConfigEol = self.__getEditorConfig("EOLMode", nodefault=True)
        if editorConfigEol is not None:
            self.setEolMode(editorConfigEol)
        else:
            self.setEolModeByEolString(self.project.getEolString())
        self.convertEols(self.eolMode())

    def addedToProject(self):
        """
        Public method to signal, that this editor has been added to a project.
        """
        if self.spell:
            pwl, pel = self.project.getProjectDictionaries()
            self.__setSpellingLanguage(
                self.project.getProjectSpellLanguage(), pwl=pwl, pel=pel
            )

        self.project.projectPropertiesChanged.connect(self.__projectPropertiesChanged)

    @pyqtSlot()
    def projectOpened(self):
        """
        Public slot to handle the opening of a project.
        """
        if self.fileName and self.project.isProjectCategory(self.fileName, "SOURCES"):
            self.project.projectPropertiesChanged.connect(
                self.__projectPropertiesChanged
            )
            self.setSpellingForProject()

    @pyqtSlot()
    def projectClosed(self):
        """
        Public slot to handle the closing of a project.
        """
        with contextlib.suppress(TypeError):
            self.project.projectPropertiesChanged.disconnect(
                self.__projectPropertiesChanged
            )

    #######################################################################
    ## Spell checking related methods
    #######################################################################

    def getSpellingLanguage(self):
        """
        Public method to get the current spelling language.

        @return current spelling language
        @rtype str
        """
        if self.spell:
            return self.spell.getLanguage()

        return ""

    def __setSpellingLanguage(self, language, pwl="", pel=""):
        """
        Private method to set the spell checking language.

        @param language spell checking language to be set
        @type str
        @param pwl name of the personal/project word list
        @type str
        @param pel name of the personal/project exclude list
        @type str
        """
        if self.spell and self.spell.getLanguage() != language:
            self.spell.setLanguage(language, pwl=pwl, pel=pel)
            self.spell.checkDocumentIncrementally()

    def __setSpelling(self):
        """
        Private method to initialize the spell checking functionality.
        """
        if Preferences.getEditor("SpellCheckingEnabled"):
            self.__spellCheckStringsOnly = Preferences.getEditor(
                "SpellCheckStringsOnly"
            )
            if self.spell is None:
                self.spell = SpellChecker(
                    self, self.spellingIndicator, checkRegion=self.isSpellCheckRegion
                )
            self.setSpellingForProject()
            self.spell.setMinimumWordSize(
                Preferences.getEditor("SpellCheckingMinWordSize")
            )

            self.setAutoSpellChecking()
        else:
            self.spell = None
            self.clearAllIndicators(self.spellingIndicator)

    def setSpellingForProject(self):
        """
        Public method to set the spell checking options for files belonging
        to the current project.
        """
        if (
            self.fileName
            and self.project.isOpen()
            and self.project.isProjectCategory(self.fileName, "SOURCES")
        ):
            pwl, pel = self.project.getProjectDictionaries()
            self.__setSpellingLanguage(
                self.project.getProjectSpellLanguage(), pwl=pwl, pel=pel
            )

    def setAutoSpellChecking(self):
        """
        Public method to set the automatic spell checking.
        """
        if Preferences.getEditor("AutoSpellCheckingEnabled"):
            with contextlib.suppress(TypeError):
                self.SCN_CHARADDED.connect(
                    self.__spellCharAdded, Qt.ConnectionType.UniqueConnection
                )
            self.spell.checkDocumentIncrementally()
        else:
            with contextlib.suppress(TypeError):
                self.SCN_CHARADDED.disconnect(self.__spellCharAdded)
            self.clearAllIndicators(self.spellingIndicator)

    def isSpellCheckRegion(self, pos):
        """
        Public method to check, if the given position is within a region, that
        should be spell checked.

        For files with a configured full text file extension all regions will
        be regarded as to be checked. Depending on configuration, all unknown
        files (i.e. those without a file extension) will be checked fully as
        well.

        @param pos position to be checked
        @type int
        @return flag indicating pos is in a spell check region
        @rtype bool
        """
        if self.__spellCheckStringsOnly:
            if (
                self.__fileNameExtension
                in Preferences.getEditor("FullSpellCheckExtensions")
            ) or (
                not self.__fileNameExtension
                and Preferences.getEditor("FullSpellCheckUnknown")
            ):
                return True
            else:
                style = self.styleAt(pos)
                if self.lexer_ is not None:
                    return self.lexer_.isCommentStyle(
                        style
                    ) or self.lexer_.isStringStyle(style)

        return True

    @pyqtSlot(int)
    def __spellCharAdded(self, charNumber):
        """
        Private slot called to handle the user entering a character.

        @param charNumber value of the character entered
        @type int
        """
        if self.spell:
            if not chr(charNumber).isalnum():
                self.spell.checkWord(self.positionBefore(self.currentPosition()), True)
            elif self.hasIndicator(self.spellingIndicator, self.currentPosition()):
                self.spell.checkWord(self.currentPosition())

    @pyqtSlot()
    def checkSpelling(self):
        """
        Public slot to perform an interactive spell check of the document.
        """
        from .SpellCheckingDialog import SpellCheckingDialog

        if self.spell:
            cline, cindex = self.getCursorPosition()
            dlg = SpellCheckingDialog(self.spell, 0, self.length(), parent=self)
            dlg.exec()
            self.setCursorPosition(cline, cindex)
            if Preferences.getEditor("AutoSpellCheckingEnabled"):
                self.spell.checkDocumentIncrementally()

    @pyqtSlot()
    def __checkSpellingSelection(self):
        """
        Private slot to spell check the current selection.
        """
        from .SpellCheckingDialog import SpellCheckingDialog

        sline, sindex, eline, eindex = self.getSelection()
        startPos = self.positionFromLineIndex(sline, sindex)
        endPos = self.positionFromLineIndex(eline, eindex)
        dlg = SpellCheckingDialog(self.spell, startPos, endPos, parent=self)
        dlg.exec()

    @pyqtSlot()
    def __checkSpellingWord(self):
        """
        Private slot to check the word below the spelling context menu.
        """
        from .SpellCheckingDialog import SpellCheckingDialog

        line, index = self.lineIndexFromPosition(self.spellingMenuPos)
        wordStart, wordEnd = self.getWordBoundaries(line, index)
        wordStartPos = self.positionFromLineIndex(line, wordStart)
        wordEndPos = self.positionFromLineIndex(line, wordEnd)
        dlg = SpellCheckingDialog(self.spell, wordStartPos, wordEndPos, parent=self)
        dlg.exec()

    @pyqtSlot()
    def __showContextMenuSpelling(self):
        """
        Private slot to set up the spelling menu before it is shown.
        """
        self.spellingMenu.clear()
        self.spellingSuggActs = []
        line, index = self.lineIndexFromPosition(self.spellingMenuPos)
        word = self.getWord(line, index)
        suggestions = self.spell.getSuggestions(word)
        for suggestion in suggestions[:5]:
            self.spellingSuggActs.append(self.spellingMenu.addAction(suggestion))
        if suggestions:
            self.spellingMenu.addSeparator()
        self.spellingMenu.addAction(
            EricPixmapCache.getIcon("spellchecking"),
            self.tr("Check spelling..."),
            self.__checkSpellingWord,
        )
        self.spellingMenu.addAction(
            self.tr("Add to dictionary"), self.__addToSpellingDictionary
        )
        self.spellingMenu.addAction(self.tr("Ignore All"), self.__ignoreSpellingAlways)

        self.showMenu.emit("Spelling", self.spellingMenu, self)

    @pyqtSlot(QAction)
    def __contextMenuSpellingTriggered(self, action):
        """
        Private slot to handle the selection of a suggestion of the spelling
        context menu.

        @param action reference to the action that was selected
        @type QAction
        """
        if action in self.spellingSuggActs:
            replacement = action.text()
            line, index = self.lineIndexFromPosition(self.spellingMenuPos)
            wordStart, wordEnd = self.getWordBoundaries(line, index)
            self.setSelection(line, wordStart, line, wordEnd)
            self.beginUndoAction()
            self.removeSelectedText()
            self.insert(replacement)
            self.endUndoAction()

    @pyqtSlot()
    def __addToSpellingDictionary(self):
        """
        Private slot to add the word below the spelling context menu to the
        dictionary.
        """
        line, index = self.lineIndexFromPosition(self.spellingMenuPos)
        word = self.getWord(line, index)
        self.spell.add(word)

        wordStart, wordEnd = self.getWordBoundaries(line, index)
        self.clearIndicator(self.spellingIndicator, line, wordStart, line, wordEnd)
        if Preferences.getEditor("AutoSpellCheckingEnabled"):
            self.spell.checkDocumentIncrementally()

    @pyqtSlot()
    def __removeFromSpellingDictionary(self):
        """
        Private slot to remove the word below the context menu to the
        dictionary.
        """
        line, index = self.lineIndexFromPosition(self.spellingMenuPos)
        word = self.getWord(line, index)
        self.spell.remove(word)

        if Preferences.getEditor("AutoSpellCheckingEnabled"):
            self.spell.checkDocumentIncrementally()

    def __ignoreSpellingAlways(self):
        """
        Private to always ignore the word below the spelling context menu.
        """
        line, index = self.lineIndexFromPosition(self.spellingMenuPos)
        word = self.getWord(line, index)
        self.spell.ignoreAlways(word)
        if Preferences.getEditor("AutoSpellCheckingEnabled"):
            self.spell.checkDocumentIncrementally()

    #######################################################################
    ## Cooperation related methods
    #######################################################################

    def getSharingStatus(self):
        """
        Public method to get some share status info.

        @return tuple indicating, if the editor is sharable, the sharing
            status, if it is inside a locally initiated shared edit session
            and if it is inside a remotely initiated shared edit session
        @rtype tuple of (bool, bool, bool, bool)
        """
        return (
            (
                bool(self.fileName)
                and self.project.isOpen()
                and self.project.isProjectFile(self.fileName)
            ),
            self.__isShared,
            self.__inSharedEdit,
            self.__inRemoteSharedEdit,
        )

    def shareConnected(self, connected):
        """
        Public method to handle a change of the connected state.

        @param connected flag indicating the connected state
        @type bool
        """
        if not connected:
            self.__inRemoteSharedEdit = False
            self.setReadOnly(False)
            self.__updateReadOnly()
            self.cancelSharedEdit(send=False)
            self.__isSyncing = False
            self.__receivedWhileSyncing = []

    def shareEditor(self, share):
        """
        Public method to set the shared status of the editor.

        @param share flag indicating the share status
        @type bool
        """
        self.__isShared = share
        if not share:
            self.shareConnected(False)

    @pyqtSlot()
    def startSharedEdit(self):
        """
        Public slot to start a shared edit session for the editor.
        """
        self.__inSharedEdit = True
        self.__savedText = self.text()
        hashStr = str(
            QCryptographicHash.hash(
                Utilities.encode(self.__savedText, self.encoding)[0],
                QCryptographicHash.Algorithm.Sha1,
            ).toHex(),
            encoding="utf-8",
        )
        self.__send(Editor.StartEditToken, hashStr)

    @pyqtSlot()
    def sendSharedEdit(self):
        """
        Public slot to end a shared edit session for the editor and
        send the changes.
        """
        commands = self.__calculateChanges(self.__savedText, self.text())
        self.__send(Editor.EndEditToken, commands)
        self.__inSharedEdit = False
        self.__savedText = ""

    def cancelSharedEdit(self, send=True):
        """
        Public method to cancel a shared edit session for the editor.

        @param send flag indicating to send the CancelEdit command
        @type bool
        """
        self.__inSharedEdit = False
        self.__savedText = ""
        if send:
            self.__send(Editor.CancelEditToken)

    def __send(self, token, args=None):
        """
        Private method to send an editor command to remote editors.

        @param token command token
        @type str
        @param args arguments for the command
        @type str
        """
        if self.vm.isConnected():
            msg = ""
            if token in (
                Editor.StartEditToken,
                Editor.EndEditToken,
                Editor.RequestSyncToken,
                Editor.SyncToken,
            ):
                msg = "{0}{1}{2}".format(token, Editor.Separator, args)
            elif token == Editor.CancelEditToken:
                msg = "{0}{1}c".format(token, Editor.Separator)

            self.vm.send(self.fileName, msg)

    @pyqtSlot(str)
    def receive(self, command):
        """
        Public slot to handle received editor commands.

        @param command command string
        @type str
        """
        if self.__isShared:
            if self.__isSyncing and not command.startswith(
                Editor.SyncToken + Editor.Separator
            ):
                self.__receivedWhileSyncing.append(command)
            else:
                self.__dispatchCommand(command)

    def __dispatchCommand(self, command):
        """
        Private method to dispatch received commands.

        @param command command to be processed
        @type str
        """
        token, argsString = command.split(Editor.Separator, 1)
        if token == Editor.StartEditToken:
            self.__processStartEditCommand(argsString)
        elif token == Editor.CancelEditToken:
            self.shareConnected(False)
        elif token == Editor.EndEditToken:
            self.__processEndEditCommand(argsString)
        elif token == Editor.RequestSyncToken:
            self.__processRequestSyncCommand(argsString)
        elif token == Editor.SyncToken:
            self.__processSyncCommand(argsString)

    @pyqtSlot(str)
    def __processStartEditCommand(self, argsString):
        """
        Private slot to process a remote StartEdit command.

        @param argsString string containing the command parameters
        @type str
        """
        if not self.__inSharedEdit and not self.__inRemoteSharedEdit:
            self.__inRemoteSharedEdit = True
            self.setReadOnly(True)
            self.__updateReadOnly()
            hashStr = str(
                QCryptographicHash.hash(
                    Utilities.encode(self.text(), self.encoding)[0],
                    QCryptographicHash.Algorithm.Sha1,
                ).toHex(),
                encoding="utf-8",
            )
            if hashStr != argsString:
                # text is different to the remote site, request to sync it
                self.__isSyncing = True
                self.__send(Editor.RequestSyncToken, argsString)

    def __calculateChanges(self, old, new):
        """
        Private method to determine change commands to convert old text into
        new text.

        @param old old text
        @type str
        @param new new text
        @type str
        @return commands to change old into new
        @rtype str
        """
        oldL = old.splitlines()
        newL = new.splitlines()
        matcher = difflib.SequenceMatcher(None, oldL, newL)

        formatStr = "@@{0} {1} {2} {3}"
        commands = []
        for token, i1, i2, j1, j2 in matcher.get_opcodes():
            if token == "insert":  # secok
                commands.append(formatStr.format("i", j1, j2 - j1, -1))
                commands.extend(newL[j1:j2])
            elif token == "delete":  # secok
                commands.append(formatStr.format("d", j1, i2 - i1, -1))
            elif token == "replace":  # secok
                commands.append(formatStr.format("r", j1, i2 - i1, j2 - j1))
                commands.extend(newL[j1:j2])

        return "\n".join(commands) + "\n"

    @pyqtSlot(str)
    def __processEndEditCommand(self, argsString):
        """
        Private slot to process a remote EndEdit command.

        @param argsString string containing the command parameters
        @type str
        """
        commands = argsString.splitlines()
        sep = self.getLineSeparator()
        cur = self.getCursorPosition()

        self.setReadOnly(False)
        self.beginUndoAction()
        while commands:
            commandLine = commands.pop(0)
            if not commandLine.startswith("@@"):
                continue

            args = commandLine.split()
            command = args.pop(0)
            pos, l1, l2 = [int(arg) for arg in args]
            if command == "@@i":
                txt = sep.join(commands[0:l1]) + sep
                self.insertAt(txt, pos, 0)
                del commands[0:l1]
            elif command == "@@d":
                self.setSelection(pos, 0, pos + l1, 0)
                self.removeSelectedText()
            elif command == "@@r":
                self.setSelection(pos, 0, pos + l1, 0)
                self.removeSelectedText()
                txt = sep.join(commands[0:l2]) + sep
                self.insertAt(txt, pos, 0)
                del commands[0:l2]
        self.endUndoAction()
        self.__updateReadOnly()
        self.__inRemoteSharedEdit = False

        self.setCursorPosition(*cur)

    @pyqtSlot(str)
    def __processRequestSyncCommand(self, argsString):
        """
        Private slot to process a remote RequestSync command.

        @param argsString string containing the command parameters
        @type str
        """
        if self.__inSharedEdit:
            hashStr = str(
                QCryptographicHash.hash(
                    Utilities.encode(self.__savedText, self.encoding)[0],
                    QCryptographicHash.Algorithm.Sha1,
                ).toHex(),
                encoding="utf-8",
            )

            if hashStr == argsString:
                self.__send(Editor.SyncToken, self.__savedText)

    @pyqtSlot(str)
    def __processSyncCommand(self, argsString):
        """
        Private slot to process a remote Sync command.

        @param argsString string containing the command parameters
        @type str
        """
        if self.__isSyncing:
            cur = self.getCursorPosition()

            self.setReadOnly(False)
            self.beginUndoAction()
            self.selectAll()
            self.removeSelectedText()
            self.insertAt(argsString, 0, 0)
            self.endUndoAction()
            self.setReadOnly(True)

            self.setCursorPosition(*cur)

            while self.__receivedWhileSyncing:
                command = self.__receivedWhileSyncing.pop(0)
                self.__dispatchCommand(command)

            self.__isSyncing = False

    #######################################################################
    ## Special search related methods
    #######################################################################

    @pyqtSlot()
    def searchCurrentWordForward(self):
        """
        Public slot to search the current word forward.
        """
        self.__searchCurrentWord(forward=True)

    @pyqtSlot()
    def searchCurrentWordBackward(self):
        """
        Public slot to search the current word backward.
        """
        self.__searchCurrentWord(forward=False)

    def __searchCurrentWord(self, forward=True):
        """
        Private slot to search the next occurrence of the current word.

        @param forward flag indicating the search direction
        @type bool
        """
        self.hideFindIndicator()
        line, index = self.getCursorPosition()
        word = self.getCurrentWord()
        wordStart, wordEnd = self.getCurrentWordBoundaries()
        wordStartPos = self.positionFromLineIndex(line, wordStart)
        wordEndPos = self.positionFromLineIndex(line, wordEnd)

        regExp = re.compile(r"\b{0}\b".format(word))
        startPos = wordEndPos if forward else wordStartPos

        matches = list(regExp.finditer(self.text()))
        if matches:
            if forward:
                matchesAfter = [m for m in matches if m.start() >= startPos]
                if matchesAfter:
                    match = matchesAfter[0]
                else:
                    # wrap around
                    match = matches[0]
            else:
                matchesBefore = [m for m in matches if m.start() < startPos]
                if matchesBefore:
                    match = matchesBefore[-1]
                else:
                    # wrap around
                    match = matches[-1]
            line, index = self.lineIndexFromPosition(match.start())
            self.setSelection(line, index + len(match.group(0)), line, index)
            self.showFindIndicator(line, index, line, index + len(match.group(0)))

    #######################################################################
    ## Sort related methods
    #######################################################################

    @pyqtSlot()
    def sortLines(self):
        """
        Public slot to sort the lines spanned by a rectangular selection.
        """
        from .SortOptionsDialog import SortOptionsDialog

        if not self.selectionIsRectangle():
            return

        dlg = SortOptionsDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ascending, alnum, caseSensitive = dlg.getData()
            (
                origStartLine,
                origStartIndex,
                origEndLine,
                origEndIndex,
            ) = self.getRectangularSelection()
            # convert to upper-left to lower-right
            startLine = min(origStartLine, origEndLine)
            startIndex = min(origStartIndex, origEndIndex)
            endLine = max(origStartLine, origEndLine)
            endIndex = max(origStartIndex, origEndIndex)

            # step 1: extract the text of the rectangular selection and
            #         the lines
            selText = {}
            txtLines = {}
            for line in range(startLine, endLine + 1):
                txtLines[line] = self.text(line)
                txt = txtLines[line][startIndex:endIndex].strip()
                if not alnum:
                    try:
                        txt = float(txt)
                    except ValueError:
                        EricMessageBox.critical(
                            self,
                            self.tr("Sort Lines"),
                            self.tr(
                                """The selection contains illegal data for a"""
                                """ numerical sort."""
                            ),
                        )
                        return

                if txt in selText:
                    selText[txt].append(line)
                else:
                    selText[txt] = [line]

            # step 2: calculate the sort parameters
            reverse = not ascending
            if alnum and not caseSensitive:
                keyFun = str.lower
            else:
                keyFun = None

            # step 3: sort the lines
            eol = self.getLineSeparator()
            lastWithEol = True
            newLines = []
            for txt in sorted(selText, key=keyFun, reverse=reverse):
                for line in selText[txt]:
                    txt = txtLines[line]
                    if not txt.endswith(eol):
                        lastWithEol = False
                        txt += eol
                    newLines.append(txt)
            if not lastWithEol:
                newLines[-1] = newLines[-1][: -len(eol)]

            # step 4: replace the lines by the sorted ones
            self.setSelection(startLine, 0, endLine + 1, 0)
            self.beginUndoAction()
            self.replaceSelectedText("".join(newLines))
            self.endUndoAction()

            # step 5: reset the rectangular selection
            self.setRectangularSelection(
                origStartLine, origStartIndex, origEndLine, origEndIndex
            )
            self.selectionChanged.emit()

    #######################################################################
    ## Mouse click handler related methods
    #######################################################################

    def mouseReleaseEvent(self, evt):
        """
        Protected method calling a registered mouse click handler function.

        @param evt event object
        @type QMouseEvent
        """
        modifiers = evt.modifiers()
        button = evt.button()
        key = (modifiers, button)

        self.vm.eventFilter(self, evt)
        super().mouseReleaseEvent(evt)

        if (
            button != Qt.MouseButton.NoButton
            and Preferences.getEditor("MouseClickHandlersEnabled")
            and key in self.__mouseClickHandlers
        ):
            evt.accept()
            self.__mouseClickHandlers[key][1](self)
        else:
            super().mouseReleaseEvent(evt)

    def setMouseClickHandler(self, name, modifiers, button, function):
        """
        Public method to set a mouse click handler.

        @param name name of the plug-in (or 'internal') setting this handler
        @type str
        @param modifiers keyboard modifiers of the handler
        @type Qt.KeyboardModifiers or int
        @param button mouse button of the handler
        @type Qt.MouseButton or int
        @param function handler function
        @type func
        @return flag indicating success
        @rtype bool
        """
        if button and button != Qt.MouseButton.NoButton:
            key = (modifiers, button)
            if key in self.__mouseClickHandlers:
                EricMessageBox.warning(
                    self,
                    self.tr("Register Mouse Click Handler"),
                    self.tr(
                        """A mouse click handler for "{0}" was already"""
                        """ registered by "{1}". Aborting request by"""
                        """ "{2}"..."""
                    ).format(
                        MouseUtilities.MouseButtonModifier2String(modifiers, button),
                        self.__mouseClickHandlers[key][0],
                        name,
                    ),
                )
                return False

            self.__mouseClickHandlers[key] = (name, function)
            return True

        return False

    def getMouseClickHandler(self, modifiers, button):
        """
        Public method to get a registered mouse click handler.

        @param modifiers keyboard modifiers of the handler
        @type Qt.KeyboardModifiers
        @param button mouse button of the handler
        @type Qt.MouseButton
        @return plug-in name and registered function
        @rtype tuple of str and func
        """
        key = (modifiers, button)
        if key in self.__mouseClickHandlers:
            return self.__mouseClickHandlers[key]
        else:
            return ("", None)

    def getMouseClickHandlers(self, name):
        """
        Public method to get all registered mouse click handlers of
        a plug-in.

        @param name name of the plug-in
        @type str
        @return registered mouse click handlers as list of modifiers,
            mouse button and function
        @rtype list of tuple of (Qt.KeyboardModifiers, Qt.MouseButton, func)
        """
        lst = []
        for key, value in self.__mouseClickHandlers.items():
            if value[0] == name:
                lst.append((key[0], key[1], value[1]))
        return lst

    def removeMouseClickHandler(self, modifiers, button):
        """
        Public method to un-registered a mouse click handler.

        @param modifiers keyboard modifiers of the handler
        @type Qt.KeyboardModifiers
        @param button mouse button of the handler
        @type Qt.MouseButton
        """
        key = (modifiers, button)
        if key in self.__mouseClickHandlers:
            del self.__mouseClickHandlers[key]

    def removeMouseClickHandlers(self, name):
        """
        Public method to un-registered all mouse click handlers of
        a plug-in.

        @param name name of the plug-in
        @type str
        """
        for key in list(self.__mouseClickHandlers):
            if self.__mouseClickHandlers[key][0] == name:
                del self.__mouseClickHandlers[key]

    def gotoReferenceHandler(self, referencesList):
        """
        Public method to handle a list of references to perform a goto.

        @param referencesList list of references for a 'goto' action
        @type ReferenceItem
        """
        references = []
        referencePositions = []

        for reference in referencesList:
            if (
                reference.modulePath != self.getFileName()
                or self.getCursorPosition()[0] + 1 != reference.line
            ):
                if reference.modulePath == self.getFileName():
                    references.append(
                        self.tr("{0:4d}    {1}", "line number, source code").format(
                            reference.line, reference.codeLine.strip()
                        )
                    )
                else:
                    references.append(
                        self.tr(
                            "{0:4d}    {1}\n    =>  {2}",
                            "line number, source code, file name",
                        ).format(
                            reference.line,
                            reference.codeLine.strip(),
                            self.project.getRelativePath(reference.modulePath),
                        )
                    )
                referencePositions.append(
                    (reference.modulePath, reference.line, reference.column)
                )

        if references:
            if self.isCallTipActive():
                self.cancelCallTips()
            self.__referencesList = references
            self.__referencesPositionsList = referencePositions
            self.showUserList(ReferencesListID, references)

    #######################################################################
    ## Methods implementing a Shell interface
    #######################################################################

    @pyqtSlot()
    def __executeSelection(self):
        """
        Private slot to execute the selected text in the shell window.
        """
        txt = self.selectedText()
        ericApp().getObject("Shell").executeLines(txt)

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
            fileName = self.fileName

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

        if fileName:
            try:
                if FileSystemUtilities.isRemoteFileName(fileName):
                    if ericApp().getObject("EricServer").isServerConnected():
                        editorConfigInterface = (
                            ericApp()
                            .getObject("EricServer")
                            .getServiceInterface("EditorConfig")
                        )
                        editorConfig = editorConfigInterface.loadEditorConfig(fileName)
                elif FileSystemUtilities.isPlainFileName(fileName):
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
        will be used (Preferences.getEditor() ). The option must be given as
        the Preferences option key. The mapping to the EditorConfig option name
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
            # use Preferences in case of error
            value = self.__getOverrideValue(option)
            if value is None:
                # no override
                value = Preferences.getEditor(option)

        return value

    def getEditorConfig(self, option):
        """
        Public method to get the requested option via EditorConfig.

        @param option Preferences option key
        @type str
        @return value of requested setting
        @rtype Any
        """
        return self.__getEditorConfig(option)

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
                    return overrides[language][0]
                elif option == "IndentWidth":
                    return overrides[language][1]

        return None

    #######################################################################
    ## Methods implementing the docstring generator interface
    #######################################################################

    def resetDocstringGenerator(self):
        """
        Public method to reset the current docstring generator.
        """
        self.__docstringGenerator = None

    def getDocstringGenerator(self):
        """
        Public method to get a reference to the docstring generator.

        @return reference to the docstring generator
        @rtype BaseDocstringGenerator
        """
        from . import DocstringGenerator

        if self.__docstringGenerator is None:
            self.__docstringGenerator = DocstringGenerator.getDocstringGenerator(self)

        return self.__docstringGenerator

    def insertDocstring(self):
        """
        Public method to generate and insert a docstring for the function under
        the cursor.

        Note: This method is called via a keyboard shortcut or through the
        global 'Edit' menu.
        """
        generator = self.getDocstringGenerator()
        generator.insertDocstringFromShortcut(self.getCursorPosition())

    @pyqtSlot()
    def __insertDocstring(self):
        """
        Private slot to generate and insert a docstring for the function under
        the cursor.
        """
        generator = self.getDocstringGenerator()
        generator.insertDocstring(self.getCursorPosition(), fromStart=True)

    def __delayedDocstringMenuPopup(self, cursorPosition):
        """
        Private method to test, if the user might want to insert a docstring.

        @param cursorPosition current cursor position (line and column)
        @type tuple of (int, int)
        """
        if Preferences.getEditor(
            "DocstringAutoGenerate"
        ) and self.getDocstringGenerator().isDocstringIntro(cursorPosition):
            lineText2Cursor = self.text(cursorPosition[0])[: cursorPosition[1]]

            QTimer.singleShot(
                300, lambda: self.__popupDocstringMenu(lineText2Cursor, cursorPosition)
            )

    def __popupDocstringMenu(self, lastLineText, lastCursorPosition):
        """
        Private method to pop up a menu asking the user, if a docstring should be
        inserted.

        @param lastLineText line contents when the delay timer was started
        @type str
        @param lastCursorPosition position of the cursor when the delay timer
            was started (line and index)
        @type tuple of (int, int)
        """
        from .DocstringGenerator.BaseDocstringGenerator import DocstringMenuForEnterOnly

        cursorPosition = self.getCursorPosition()
        if lastCursorPosition != cursorPosition:
            return

        if self.text(cursorPosition[0])[: cursorPosition[1]] != lastLineText:
            return

        generator = self.getDocstringGenerator()
        if generator.hasFunctionDefinition(cursorPosition):
            docstringMenu = DocstringMenuForEnterOnly(self)
            act = docstringMenu.addAction(
                EricPixmapCache.getIcon("fileText"),
                self.tr("Generate Docstring"),
                lambda: generator.insertDocstring(cursorPosition, fromStart=False),
            )
            docstringMenu.setActiveAction(act)
            docstringMenu.popup(self.mapToGlobal(self.getGlobalCursorPosition()))

    #######################################################################
    ## Methods implementing the mouse hover help interface
    #######################################################################

    @pyqtSlot(int, int, int)
    def __showMouseHoverHelp(self, pos, x, y):
        """
        Private slot showing code information about the symbol under the
        cursor.

        @param pos mouse position into the document
        @type int
        @param x x-value of mouse screen position
        @type int
        @param y y-value of mouse screen position
        @type int
        """
        if (
            not self.isCallTipActive()
            and not self.isListActive()
            and not self.menu.isVisible()
            and not self.spellingMenu.isVisible()
        ):
            if self.__mouseHoverHelp is not None and pos > 0 and y > 0:
                line, index = self.lineIndexFromPosition(pos)
                if index > 0:
                    self.__mouseHoverHelp(self, line, index)
                else:
                    self.__cancelMouseHoverHelp()
            else:
                self.__cancelMouseHoverHelp()

    @pyqtSlot()
    def __cancelMouseHoverHelp(self):
        """
        Private slot cancelling the display of mouse hover help.
        """
        if self.__showingMouseHoverHelp:
            self.cancelCallTips()
            self.__showingMouseHoverHelp = False

    def registerMouseHoverHelpFunction(self, func):
        """
        Public method to register a mouse hover help function.

        Note: Only one plugin should provide this function. Otherwise
        the last one wins.

        @param func function accepting a reference to the calling editor and
            the line and column position (zero based each)
        @type func
        """
        self.__mouseHoverHelp = func

    def unregisterMouseHoverHelpFunction(self, func):
        """
        Public method to unregister a mouse hover help function.

        @param func function accepting a reference to the calling editor and
            the line and column position (zero based each)
        @type func
        """
        if self.__mouseHoverHelp is func:
            self.__mouseHoverHelp = None

    def showMouseHoverHelpData(self, line, index, data):
        """
        Public method to show the mouse hover help data.

        @param line line of mouse cursor position
        @type int
        @param index column of mouse cursor position
        @type int
        @param data information text to be shown
        @type str
        """
        if data and self.hasFocus() and not self.isListActive():
            pos = self.positionFromLineIndex(line, index)
            self.SendScintilla(
                QsciScintilla.SCI_CALLTIPSHOW, pos, self._encodeString(data)
            )
            self.__showingMouseHoverHelp = True
        else:
            self.__cancelMouseHoverHelp()

    #######################################################################
    ## Methods implementing the code formatting interface
    #######################################################################

    def __performFormatWithBlack(self, action):
        """
        Private method to format the source code using the 'Black' tool.

        Following actions are supported.
        <ul>
        <li>BlackFormattingAction.Format - the code reformatting is performed</li>
        <li>BlackFormattingAction.Check - a check is performed, if code formatting
            is necessary</li>
        <li>BlackFormattingAction.Diff - a unified diff of potential code formatting
            changes is generated</li>
        </ul>

        @param action formatting operation to be performed
        @type BlackFormattingAction
        """
        from eric7.CodeFormatting.BlackConfigurationDialog import (
            BlackConfigurationDialog,
        )
        from eric7.CodeFormatting.BlackFormattingDialog import BlackFormattingDialog

        if not self.isModified() or self.saveFile():
            withProject = (
                self.fileName
                and self.project.isOpen()
                and self.project.isProjectCategory(self.fileName, "SOURCES")
            )
            dlg = BlackConfigurationDialog(withProject=withProject, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                config = dlg.getConfiguration()

                formattingDialog = BlackFormattingDialog(
                    config,
                    [self.fileName],
                    project=self.project,
                    action=action,
                    parent=self,
                )
                formattingDialog.exec()

    def __performImportSortingWithIsort(self, action):
        """
        Private method to sort the import statements using the 'isort' tool.

        Following actions are supported.
        <ul>
        <li>IsortFormattingAction.Sort - the import statement sorting is performed</li>
        <li>IsortFormattingAction.Check - a check is performed, if import statement
            resorting is necessary</li>
        <li>IsortFormattingAction.Diff - a unified diff of potential import statement
            changes is generated</li>
        </ul>

        @param action sorting operation to be performed
        @type IsortFormattingAction
        """
        from eric7.CodeFormatting.IsortConfigurationDialog import (
            IsortConfigurationDialog,
        )
        from eric7.CodeFormatting.IsortFormattingDialog import IsortFormattingDialog

        if not self.isModified() or self.saveFile():
            withProject = (
                self.fileName
                and self.project.isOpen()
                and self.project.isProjectCategory(self.fileName, "SOURCES")
            )
            dlg = IsortConfigurationDialog(withProject=withProject, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                config = dlg.getConfiguration()

                formattingDialog = IsortFormattingDialog(
                    config,
                    [self.fileName],
                    project=self.project if withProject else None,
                    action=action,
                    parent=self,
                )
                formattingDialog.exec()
