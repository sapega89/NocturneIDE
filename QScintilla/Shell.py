# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a graphical Python shell.
"""

import contextlib
import enum
import pathlib
import re
import sys
import time

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtCore import QEvent, QPoint, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QClipboard, QFont, QPalette, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QInputDialog,
    QMenu,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from eric7 import Preferences, Utilities
from eric7.Debugger.DebugClientCapabilities import HasCompleter
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricSimpleHelpDialog import EricSimpleHelpDialog
from eric7.SystemUtilities import FileSystemUtilities
from eric7.UI.SearchWidget import SearchWidget

from . import Lexers
from .QsciScintillaCompat import QsciScintillaCompat


class ShellAssembly(QWidget):
    """
    Class implementing the containing widget for the shell.
    """

    def __init__(self, dbs, vm, project, horizontal=True, parent=None):
        """
        Constructor

        @param dbs reference to the debug server object
        @type DebugServer
        @param vm reference to the viewmanager object
        @type ViewManager
        @param project reference to the project object
        @type Project
        @param horizontal flag indicating a horizontal layout
        @type bool
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__shell = Shell(dbs, vm, project, False, self)

        self.__searchWidget = SearchWidget(self.__shell, self, horizontal)
        self.__searchWidget.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred
        )
        self.__searchWidget.hide()

        if horizontal:
            self.__layout = QHBoxLayout(self)
        else:
            self.__layout = QVBoxLayout(self)
        self.__layout.setContentsMargins(1, 1, 1, 1)
        self.__layout.addWidget(self.__shell)
        self.__layout.addWidget(self.__searchWidget)

        self.__searchWidget.searchNext.connect(self.__shell.searchNext)
        self.__searchWidget.searchPrevious.connect(self.__shell.searchPrev)
        self.__shell.searchStringFound.connect(self.__searchWidget.searchStringFound)

    def showFind(self, txt=""):
        """
        Public method to display the search widget.

        @param txt text to be shown in the combo
        @type str
        """
        self.__searchWidget.showFind(txt)

    def shell(self):
        """
        Public method to get a reference to the shell widget.

        @return reference to the shell widget
        @rtype Shell
        """
        return self.__shell


class ShellHistoryStyle(enum.Enum):
    """
    Class defining the shell history styles.
    """

    DISABLED = 0
    LINUXSTYLE = 1
    WINDOWSSTYLE = 2


class Shell(QsciScintillaCompat):
    """
    Class implementing a graphical Python shell.

    A user can enter commands that are executed in the remote
    Python interpreter.

    @signal searchStringFound(bool) emitted to indicate the search
        result
    @signal historyStyleChanged(ShellHistoryStyle) emitted to indicate a
        change of the history style
    @signal queueText(str) emitted to queue some text for processing
    @signal virtualEnvironmentChanged(str) emitted to signal the new virtual
        environment of the shell
    """

    searchStringFound = pyqtSignal(bool)
    historyStyleChanged = pyqtSignal(ShellHistoryStyle)
    queueText = pyqtSignal(str)
    virtualEnvironmentChanged = pyqtSignal(str)

    def __init__(self, dbs, vm, project, windowedVariant, parent=None):
        """
        Constructor

        @param dbs reference to the debug server object
        @type DebugServer
        @param vm reference to the viewmanager object
        @type ViewManager
        @param project reference to the project object
        @type Project
        @param windowedVariant flag indicating the shell window variant
        @type bool
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setUtf8(True)

        self.vm = vm
        self.__mainWindow = parent
        self.__lastSearch = ()
        self.__windowed = windowedVariant
        self.__currentVenv = ""
        self.__currentWorkingDirectory = ""
        self.__helpDialog = None

        self.linesepRegExp = r"\r\n|\n|\r"

        self.passive = (not self.__windowed) and Preferences.getDebugger(
            "PassiveDbgEnabled"
        )
        if self.passive:
            self.setWindowTitle(self.tr("Shell - Passive"))
        else:
            self.setWindowTitle(self.tr("Shell"))

        if self.__windowed:
            self.setWhatsThis(
                self.tr(
                    """<b>The Shell Window</b>"""
                    """<p>You can use the cursor keys while entering commands."""
                    """ There is also a history of commands that can be recalled"""
                    """ using the up and down cursor keys while holding down the"""
                    """ Ctrl-key. This can be switched to just the up and down"""
                    """ cursor keys on the Shell page of the configuration"""
                    """ dialog. Pressing these keys after some text has been"""
                    """ entered will start an incremental search.</p>"""
                    """<p>The shell has some special commands. Type '%help' to get"""
                    """ a list of these commands.</p>"""
                    """<p>Pressing the Tab key after some text has been entered"""
                    """ will show a list of possible completions. The relevant"""
                    """ entry may be selected from this list. If only one entry"""
                    """ is available, this will be inserted automatically.</p>"""
                )
            )
        else:
            self.setWhatsThis(
                self.tr(
                    """<b>The Shell Window</b>"""
                    """<p>This is simply an interpreter running in a window. The"""
                    """ interpreter is the one that is used to run the program"""
                    """ being debugged. This means that you can execute any"""
                    """ command while the program being debugged is running.</p>"""
                    """<p>You can use the cursor keys while entering commands."""
                    """ There is also a history of commands that can be recalled"""
                    """ using the up and down cursor keys while holding down the"""
                    """ Ctrl-key. This can be switched to just the up and down"""
                    """ cursor keys on the Shell page of the configuration"""
                    """ dialog. Pressing these keys after some text has been"""
                    """ entered will start an incremental search.</p>"""
                    """<p>The shell has some special commands. Type '%help' to get"""
                    """ a list of these commands.</p>"""
                    """<p>Pressing the Tab key after some text has been entered"""
                    """ will show a list of possible completions. The relevant"""
                    """ entry may be selected from this list. If only one entry"""
                    """ is available, this will be inserted automatically.</p>"""
                    """<p>In passive debugging mode the shell is only available"""
                    """ after the program to be debugged has connected to the"""
                    """ IDE until it has finished. This is indicated by a"""
                    """ different prompt and by an indication in the window"""
                    """ caption.</p>"""
                )
            )

        self.userListActivated.connect(self.__completionListSelected)
        self.linesChanged.connect(self.__resizeLinenoMargin)

        if self.__windowed:
            self.__showStdOutErr = True
        else:
            self.__showStdOutErr = Preferences.getShell("ShowStdOutErr")
        if self.__showStdOutErr:
            dbs.clientProcessStdout.connect(self.__writeStdOut)
            dbs.clientProcessStderr.connect(self.__writeStdErr)
        dbs.clientOutput.connect(self.__writeQueued)
        dbs.clientStatement.connect(self.__clientStatement)
        dbs.clientGone.connect(self.__initialise)
        dbs.clientRawInput.connect(self.__raw_input)
        dbs.clientBanner.connect(self.__writeBanner)
        dbs.clientCompletionList.connect(self.__showCompletions)
        dbs.clientCapabilities.connect(self.__clientCapabilities)
        dbs.clientException.connect(self.__clientException)
        dbs.clientSyntaxError.connect(self.__clientSyntaxError)
        dbs.clientSignal.connect(self.__clientSignal)
        dbs.mainClientExit.connect(self.__writePrompt)
        self.dbs = dbs

        # will register a method to get the debugger ID to work with
        self.__getSelectedDebuggerId = None

        # Make sure we have prompts.
        if self.passive:
            sys.ps1 = self.tr("Passive >>> ")
        else:
            try:
                sys.ps1
            except AttributeError:
                sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "

        # Initialize instance variables.
        self.__initialise()
        self.prline = 0
        self.prcol = 0
        self.inDragDrop = False
        self.lexer_ = None
        self.completionText = ""
        self.__shuttingDown = False

        self.clientType = ""

        self.__commandExecutionTimeout = Preferences.getShell("CommandExecutionTimeout")

        # Initialize history
        self.__historyLists = {}
        self.__maxHistoryEntries = Preferences.getShell("MaxHistoryEntries")
        self.__historyStyle = Preferences.getShell("HistoryStyle")
        self.__historyWrap = Preferences.getShell("HistoryWrap")
        self.__history = []
        self.__setHistoryIndex()
        # remove obsolete shell histories (Python and Ruby)
        for clientType in ["Python", "Ruby"]:
            Preferences.getSettings().remove("Shell/Histories/" + clientType)

        # clear QScintilla defined keyboard commands
        # we do our own handling through the view manager
        self.clearAlternateKeys()
        self.clearKeys()
        self.__actionsAdded = False

        if self.passive:
            self.__getBanner()

        if not self.__windowed:
            # Create a little language context menu
            self.lmenu = QMenu(self.tr("Start"))
            self.lmenu.aboutToShow.connect(self.__showStartMenu)
            self.lmenu.triggered.connect(self.__startDebugClient)

            # Create the history context menu
            self.hmenu = QMenu(self.tr("History"))
            self.hmenu.addAction(self.tr("Select entry"), self.selectHistory)
            self.hmenu.addAction(self.tr("Show"), self.showHistory)
            self.hmenu.addAction(self.tr("Clear"), self.clearHistory)

            # Create a little context menu
            self.menu = QMenu(self)
            self.menu.addAction(self.tr("Cut"), self.cut)
            self.menu.addAction(self.tr("Copy"), self.copy)
            self.menu.addAction(self.tr("Paste"), self.paste)
            self.menu.addMenu(self.hmenu).setEnabled(self.isHistoryEnabled())
            self.menu.addSeparator()
            self.menu.addAction(self.tr("Find"), self.__find)
            self.menu.addSeparator()
            self.menu.addAction(self.tr("Clear"), self.clear)
            self.menu.addAction(self.tr("Restart"), self.doRestart)
            self.menu.addAction(self.tr("Restart and Clear"), self.doClearRestart)
            self.menu.addSeparator()
            self.menu.addMenu(self.lmenu)
            self.menu.addAction(self.tr("Active Name"), self.__showVenvName)
            self.menu.addSeparator()
            self.menu.addAction(self.tr("Save Contents..."), self.saveContents)
            self.menu.addSeparator()
            self.menu.addAction(self.tr("Configure..."), self.__configure)
            self.menu.addSeparator()
            self.menu.addAction(self.tr("Special Commands Help"), self.__showHelp)
            self.menu.addSeparator()
            self.__showSourceAct = self.menu.addAction(
                self.tr("Show Source"), self.__showSource
            )

            self.customContextMenuRequested.connect(self.__showContextMenu)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.__bindLexer()
        self.__setTextDisplay()
        self.__setMargin0()

        # set the autocompletion and calltips function
        self.__setAutoCompletion()
        self.__setCallTips()

        self.setWindowIcon(EricPixmapCache.getIcon("eric"))

        self.incrementalSearchString = ""
        self.incrementalSearchActive = False

        self.supportedEditorCommands = {
            QsciScintilla.SCI_CANCEL: self.__QScintillaCancel,
            QsciScintilla.SCI_CHARLEFT: self.__QScintillaCharLeft,
            QsciScintilla.SCI_CHARLEFTEXTEND: self.__QScintillaCharLeftExtend,
            QsciScintilla.SCI_CHARRIGHT: self.__QScintillaCharRight,
            QsciScintilla.SCI_CHARRIGHTEXTEND: self.extendSelectionRight,
            QsciScintilla.SCI_CLEAR: self.__QScintillaDelete,
            QsciScintilla.SCI_DELETEBACK: self.__QScintillaDeleteBack,
            QsciScintilla.SCI_DELLINELEFT: self.__QScintillaDeleteLineLeft,
            QsciScintilla.SCI_DELLINERIGHT: self.__QScintillaDeleteLineRight,
            QsciScintilla.SCI_DELWORDLEFT: self.__QScintillaDeleteWordLeft,
            QsciScintilla.SCI_DELWORDRIGHT: self.__QScintillaDeleteWordRight,
            QsciScintilla.SCI_LINEDELETE: self.__clearCurrentLine,
            QsciScintilla.SCI_LINEDOWN: self.__QScintillaCursorCommand,
            QsciScintilla.SCI_LINEEND: self.__QScintillaLineEnd,
            QsciScintilla.SCI_LINEENDEXTEND: self.extendSelectionToEOL,
            QsciScintilla.SCI_LINESCROLLDOWN: self.__QScintillaCursorCommand,
            QsciScintilla.SCI_LINESCROLLUP: self.__QScintillaCursorCommand,
            QsciScintilla.SCI_LINEUP: self.__QScintillaCursorCommand,
            QsciScintilla.SCI_NEWLINE: self.__QScintillaNewline,
            QsciScintilla.SCI_PAGEDOWN: self.__QScintillaAutoCompletionCommand,
            QsciScintilla.SCI_PAGEUP: self.__QScintillaAutoCompletionCommand,
            QsciScintilla.SCI_TAB: self.__QScintillaTab,
            QsciScintilla.SCI_VCHOME: self.__QScintillaVCHome,
            QsciScintilla.SCI_VCHOMEEXTEND: self.__QScintillaVCHomeExtend,
            QsciScintilla.SCI_WORDLEFT: self.__QScintillaWordLeft,
            QsciScintilla.SCI_WORDLEFTEXTEND: self.__QScintillaWordLeftExtend,
            QsciScintilla.SCI_WORDRIGHT: self.__QScintillaWordRight,
            QsciScintilla.SCI_WORDRIGHTEXTEND: self.extendSelectionWordRight,
        }

        self.__historyNavigateByCursor = Preferences.getShell("HistoryNavigateByCursor")

        self.__queuedText = ""
        self.__blockTextProcessing = False
        self.queueText.connect(
            self.__concatenateText, Qt.ConnectionType.QueuedConnection
        )

        self.__project = project
        if self.__project:
            self.__project.projectOpened.connect(self.__projectOpened)
            self.__project.projectClosed.connect(self.__projectClosed)

        self.grabGesture(Qt.GestureType.PinchGesture)

    def __showStartMenu(self):
        """
        Private slot to prepare the start submenu.
        """
        self.lmenu.clear()
        venvManager = ericApp().getObject("VirtualEnvManager")
        for venvName in sorted(venvManager.getVirtualenvNames(noServer=True)):
            act = self.lmenu.addAction(venvName)
            act.setData(venvName)
        if self.__project and self.__project.isOpen():
            self.lmenu.addSeparator()
            act = self.lmenu.addAction(self.tr("Project"))
            act.setData("<<project>>")
        if ericApp().getObject("EricServer").isServerConnected():
            self.lmenu.addSeparator()
            for venvName in sorted(
                venvManager.getEricServerEnvironmentNames(
                    ericApp().getObject("EricServer").getHostName()
                )
            ):
                act = self.lmenu.addAction(venvName)
                act.setData(f"<<eric-server>>:{venvName}")
            act = self.lmenu.addAction(self.tr("eric-ide Server"))
            act.setData("<<eric-server>>")

    def __resizeLinenoMargin(self):
        """
        Private slot to resize the line numbers margin.
        """
        linenoMargin = Preferences.getShell("LinenoMargin")
        if linenoMargin:
            self.setMarginWidth(0, "8" * (len(str(self.lines())) + 1))

    def closeShell(self):
        """
        Public method to shutdown the shell.
        """
        for clientType in self.__historyLists:
            self.saveHistory(clientType)
        self.__shuttingDown = True

    def __bindLexer(self, language="Python3"):
        """
        Private slot to set the lexer.

        @param language lexer language to set
        @type str
        """
        self.language = language
        if Preferences.getShell("SyntaxHighlightingEnabled"):
            self.lexer_ = Lexers.getLexer(self.language, self)
        else:
            self.lexer_ = None

        if self.lexer_ is None:
            self.setLexer(None)
            font = Preferences.getShell("MonospacedFont")
            self.monospacedStyles(font)
            return

        # get the font for style 0 and set it as the default font
        key = "Scintilla/{0}/style0/font".format(self.lexer_.language())
        fdesc = Preferences.getSettings().value(key)
        if fdesc is not None:
            font = QFont([fdesc[0]], int(fdesc[1]))
            self.lexer_.setDefaultFont(font)
        self.setLexer(self.lexer_)
        self.lexer_.readSettings(Preferences.getSettings(), "Scintilla")
        if self.lexer_.hasSubstyles():
            self.lexer_.readSubstyles(self)

        # initialize the lexer APIs settings
        api = self.vm.getAPIsManager().getAPIs(self.language)
        if api is not None:
            api = api.getQsciAPIs()
            if api is not None:
                self.lexer_.setAPIs(api)

        self.lexer_.setDefaultColor(self.lexer_.color(0))
        self.lexer_.setDefaultPaper(self.lexer_.paper(0))

    def __setMargin0(self):
        """
        Private method to configure margin 0.
        """
        # set the settings for all margins
        self.setMarginsFont(Preferences.getShell("MarginsFont"))
        self.setMarginsForegroundColor(Preferences.getEditorColour("MarginsForeground"))
        self.setMarginsBackgroundColor(Preferences.getEditorColour("MarginsBackground"))

        # set margin 0 settings
        linenoMargin = Preferences.getShell("LinenoMargin")
        self.setMarginLineNumbers(0, linenoMargin)
        if linenoMargin:
            self.__resizeLinenoMargin()
        else:
            self.setMarginWidth(0, 0)

        # disable margins 1 and 2
        self.setMarginWidth(1, 0)
        self.setMarginWidth(2, 0)

    def __setTextDisplay(self):
        """
        Private method to configure the text display.
        """
        self.setTabWidth(Preferences.getEditor("TabWidth"))
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
        self.setCaretLineVisible(False)
        self.caretWidth = Preferences.getEditor("CaretWidth")
        self.setCaretWidth(self.caretWidth)
        if Preferences.getShell("WrapEnabled"):
            self.setWrapMode(QsciScintilla.WrapMode.WrapWord)
        else:
            self.setWrapMode(QsciScintilla.WrapMode.WrapNone)
        self.useMonospaced = Preferences.getShell("UseMonospacedFont")
        self.__setMonospaced(self.useMonospaced)

        self.setCursorFlashTime(QApplication.cursorFlashTime())

        if Preferences.getEditor("OverrideEditAreaColours"):
            self.setColor(Preferences.getEditorColour("EditAreaForeground"))
            self.setPaper(Preferences.getEditorColour("EditAreaBackground"))

    def __setMonospaced(self, on):
        """
        Private method to set/reset a monospaced font.

        @param on flag to indicate usage of a monospace font
        @type bool
        """
        if on:
            if not self.lexer_:
                f = Preferences.getShell("MonospacedFont")
                self.monospacedStyles(f)
        else:
            if not self.lexer_:
                self.clearStyles()
                self.__setMargin0()
            self.setFont(Preferences.getShell("MonospacedFont"))

        self.useMonospaced = on

    def __setAutoCompletion(self):
        """
        Private method to configure the autocompletion function.
        """
        self.setAutoCompletionCaseSensitivity(
            Preferences.getEditor("AutoCompletionCaseSensitivity")
        )
        self.setAutoCompletionThreshold(-1)

        self.racEnabled = Preferences.getShell("AutoCompletionEnabled")

        self.setAutoCompletionWidgetSize(
            Preferences.getEditor("AutoCompletionMaxChars"),
            Preferences.getEditor("AutoCompletionMaxLines"),
        )

    def __setCallTips(self):
        """
        Private method to configure the calltips function.
        """
        if Preferences.getShell("CallTipsEnabled"):
            self.setCallTipsBackgroundColor(
                Preferences.getEditorColour("CallTipsBackground")
            )
            self.setCallTipsForegroundColor(
                Preferences.getEditorColour("CallTipsForeground")
            )
            self.setCallTipsHighlightColor(
                Preferences.getEditorColour("CallTipsHighlight")
            )
            self.setCallTipsVisible(Preferences.getEditor("CallTipsVisible"))
            calltipsStyle = Preferences.getEditor("CallTipsStyle")
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

    def setDebuggerUI(self, ui):
        """
        Public method to set the debugger UI.

        @param ui reference to the debugger UI object
        @type DebugUI
        """
        ui.exceptionInterrupt.connect(self.__writePrompt)
        self.registerDebuggerIdMethod(ui.getSelectedDebuggerId)

    def registerDebuggerIdMethod(self, method):
        """
        Public method to register a method to get the debugger ID to send data
        to.

        @param method reference to the method
        @type function
        """
        self.__getSelectedDebuggerId = method

    def __initialise(self):
        """
        Private method to get ready for a new remote interpreter.
        """
        self.buff = ""
        self.inContinue = False
        self.__inRawMode = False
        self.__echoInput = True
        self.__rawModeDebuggerId = None
        self.__rawModeQueue = []
        self.clientCapabilities = 0
        self.inCommandExecution = False
        self.interruptCommandExecution = False

    def __clientCapabilities(self, cap, clType, venvName):
        """
        Private slot to handle the reporting of the clients capabilities.

        @param cap client capabilities
        @type int
        @param clType type of the debug client
        @type str
        @param venvName name of the virtual environment
        @type str
        """
        self.clientCapabilities = cap
        self.__currentVenv = venvName
        if clType != self.clientType:
            self.clientType = clType
            self.__bindLexer(self.clientType)
            self.__setTextDisplay()
            self.__setMargin0()
            self.__setAutoCompletion()
            self.__setCallTips()
            self.racEnabled = (
                Preferences.getShell("AutoCompletionEnabled")
                and (cap & HasCompleter) > 0
            )

            if self.clientType not in self.__historyLists:
                # load history list
                self.loadHistory(self.clientType)
            self.__history = self.__historyLists[self.clientType]
            self.__setHistoryIndex()

        self.virtualEnvironmentChanged.emit(venvName)
        Preferences.setShell("LastVirtualEnvironment", venvName)

    def __setHistoryIndex(self, index=None):
        """
        Private method to set the initial history index.

        @param index index value to be set
        @type int or None
        """
        if index is None:
            # determine based on history style
            if (
                self.clientType
                and self.__historyStyle == ShellHistoryStyle.WINDOWSSTYLE
            ):
                idx = int(
                    Preferences.getSettings().value(
                        "Shell/HistoryIndexes/" + self.clientType, -1
                    )
                )
                if idx >= len(self.__history):
                    idx = -1
                self.__histidx = idx
            else:
                self.__histidx = -1
        else:
            self.__histidx = index
            if self.__histidx >= len(self.__history):
                self.__histidx = -1
            if (
                self.clientType
                and self.__historyStyle == ShellHistoryStyle.WINDOWSSTYLE
            ):
                Preferences.getSettings().setValue(
                    "Shell/HistoryIndexes/" + self.clientType, self.__histidx
                )

    def __isHistoryIndexValid(self):
        """
        Private method to test, if the history index is valid.

        @return flag indicating validity
        @rtype bool
        """
        return 0 <= self.__histidx < len(self.__history)

    def getHistoryIndex(self):
        """
        Public method to get the current value of the history index.

        @return history index
        @rtype int
        """
        return self.__histidx

    def loadHistory(self, clientType):
        """
        Public method to load the history for the given client type.

        @param clientType type of the debug client
        @type str
        """
        hl = Preferences.getSettings().value("Shell/Histories/" + clientType)
        if hl is not None:
            self.__historyLists[clientType] = hl[-self.__maxHistoryEntries :]
        else:
            self.__historyLists[clientType] = []

    def reloadHistory(self):
        """
        Public method to reload the history of the currently selected client
        type.
        """
        self.loadHistory(self.clientType)
        self.__history = self.__historyLists[self.clientType]
        self.__setHistoryIndex()

    def saveHistory(self, clientType):
        """
        Public method to save the history for the given client type.

        @param clientType type of the debug client
        @type str
        """
        if clientType in self.__historyLists:
            Preferences.getSettings().setValue(
                "Shell/Histories/" + clientType, self.__historyLists[clientType]
            )

    def getHistory(self, clientType):
        """
        Public method to get the history for the given client type.

        @param clientType type of the debug client. If it is None, the current
            history is returned.
        @type str
        @return reference to the history list
        @rtype list of str
        """
        if clientType is None:
            return self.__history
        elif clientType in self.__historyLists:
            return self.__historyLists[clientType]
        else:
            return []

    @pyqtSlot()
    def clearHistory(self, ask=True):
        """
        Public slot to clear the current history.

        @param ask flag indicating to ask for confirmation (defaults to True)
        @type bool (optional)
        """
        if ask:
            ok = EricMessageBox.yesNo(
                self,
                self.tr("Clear History"),
                self.tr("""Shall the current history really be cleared?"""),
            )
            if not ok:
                return

        if self.clientType:
            self.__historyLists[self.clientType] = []
            self.__history = self.__historyLists[self.clientType]
        else:
            self.__history = []
        self.__setHistoryIndex(index=-1)

    @pyqtSlot()
    def selectHistory(self):
        """
        Public slot to select a history entry to execute.
        """
        current = self.__histidx
        if current == -1:
            current = len(self.__history) - 1
        cmd, ok = QInputDialog.getItem(
            self,
            self.tr("Select History"),
            self.tr("Select the history entry to execute (most recent shown last)."),
            self.__history,
            current,
            False,
        )
        if ok:
            self.__insertHistory(cmd)

    @pyqtSlot()
    def showHistory(self, histSize=None):
        """
        Public slot to show the shell history dialog.

        @param histSize number of history entries to be shown (None = show all
            entrys) (defaults to None)
        @type int (optional)
        """
        from .ShellHistoryDialog import ShellHistoryDialog

        dlg = (
            ShellHistoryDialog(self.__history, self.vm, self)
            if histSize is None
            else ShellHistoryDialog(self.__history[-histSize:], self.vm, self)
        )
        if dlg.exec() == QDialog.DialogCode.Accepted and histSize is None:
            self.__historyLists[self.clientType], idx = dlg.getHistory()
            self.__history = self.__historyLists[self.clientType]
            self.__setHistoryIndex(index=idx)

    def clearAllHistories(self):
        """
        Public method to clear all available histories and sync them.
        """
        Preferences.getSettings().beginGroup("Shell/Histories")
        for clientType in Preferences.getSettings().childKeys():
            self.__historyLists[clientType] = []
            self.saveHistory(clientType)
        Preferences.getSettings().endGroup()

        self.clearHistory(ask=False)

    def getClientType(self):
        """
        Public slot to get the clients type.

        @return client type
        @rtype str
        """
        return self.clientType

    def __getBanner(self):
        """
        Private method to get the banner for the remote interpreter.

        It requests the interpreter version and platform running on the
        debug client side.
        """
        if self.passive:
            self.__writeBanner("", "", "")
        else:
            self.dbs.remoteBanner()

    def __writeBanner(self, versionStr, platformStr, venvName):
        """
        Private method to write a banner with info from the debug client.

        @param versionStr interpreter version string
        @type str
        @param platformStr platform of the remote interpreter
        @type str
        @param venvName name of the virtual environment
        @type str
        """
        super().clear()
        if self.passive and not self.dbs.isConnected():
            self.__write(self.tr("Passive Debug Mode"))
            self.__write(self.tr("\nNot connected"))
        else:
            self.__currentVenv = venvName
            versionStr = versionStr.replace("#", self.tr("No."))
            if platformStr != "":
                self.__write(self.tr("{0} on {1}").format(versionStr, platformStr))
            else:
                self.__write(versionStr)
            if venvName:
                self.__write("\n[{0}]".format(venvName))

            self.virtualEnvironmentChanged.emit(venvName)
            Preferences.setShell("LastVirtualEnvironment", venvName)
        self.__write("\n")

        self.__write(sys.ps1)

    def __writePrompt(self):
        """
        Private method to write the prompt using a write queue.
        """
        self.queueText.emit(self.inContinue and sys.ps2 or sys.ps1)

    def __clientStatement(self, more):
        """
        Private method to handle the response from the debugger client.

        @param more flag indicating that more user input is required
        @type bool
        """
        if not self.__inRawMode:
            self.inContinue = more
            self.__writePrompt()
        self.inCommandExecution = False

    def __clientException(self, exceptionType, exceptionMessage, stackTrace):
        """
        Private method to handle an exception of the client.

        @param exceptionType type of exception raised
        @type str
        @param exceptionMessage message given by the exception
        @type str
        @param stackTrace list of stack entries
        @type list of str
        """
        self.__clientError()

        if (
            not self.__windowed
            and Preferences.getDebugger("ShowExceptionInShell")
            and exceptionType
        ):
            if stackTrace:
                self.__write(
                    self.tr('Exception "{0}"\n{1}\nFile: {2}, Line: {3}\n').format(
                        exceptionType,
                        exceptionMessage,
                        stackTrace[0][0],
                        stackTrace[0][1],
                    )
                )
            else:
                self.__write(
                    self.tr('Exception "{0}"\n{1}\n').format(
                        exceptionType, exceptionMessage
                    )
                )

    def __clientSyntaxError(self, message, filename, lineNo, characterNo):
        """
        Private method to handle a syntax error in the debugged program.

        @param message message of the syntax error
        @type str
        @param filename translated filename of the syntax error position
        @type str
        @param lineNo line number of the syntax error position
        @type int
        @param characterNo character number of the syntax error position
        @type int
        """
        self.__clientError()

        if not self.__windowed and Preferences.getDebugger("ShowExceptionInShell"):
            if message is None:
                self.__write(self.tr("Unspecified syntax error.\n"))
            else:
                self.__write(
                    self.tr(
                        'Syntax error "{1}" in file {0} at line {2},'
                        " character {3}.\n"
                    ).format(filename, message, lineNo, characterNo)
                )

    def __clientSignal(self, message, filename, lineNo, funcName, funcArgs):
        """
        Private method to handle a signal generated on the client side.

        @param message message of the syntax error
        @type str
        @param filename translated filename of the syntax error position
        @type str
        @param lineNo line number of the syntax error position
        @type int
        @param funcName name of the function causing the signal
        @type str
        @param funcArgs function arguments
        @type str
        """
        self.__clientError()

        self.__write(
            self.tr(
                """Signal "{0}" generated in file {1} at line {2}.\n"""
                """Function: {3}({4})"""
            ).format(message, filename, lineNo, funcName, funcArgs)
        )

    def __clientError(self):
        """
        Private method to handle an error in the client.
        """
        self.inCommandExecution = False
        self.interruptCommandExecution = True
        self.inContinue = False

    def __getEndPos(self):
        """
        Private method to return the line and column of the last character.

        @return tuple of two values giving the line and column
        @rtype tuple of (int, int)
        """
        line = self.lines() - 1
        return (line, len(self.text(line)))

    def __writeQueued(self, s):
        """
        Private method to display some text using a write queue.

        @param s text to be displayed
        @type str
        """
        self.queueText.emit(s)

    def __concatenateText(self, text):
        """
        Private slot to queue text and process it in one step.

        @param text text to be appended
        @type str
        """
        self.__queuedText += text
        if self.__blockTextProcessing:
            return

        self.__blockTextProcessing = True
        # Get all text which is still waiting for output
        QApplication.processEvents()

        # Finally process the accumulated text
        self.__flushQueuedText()

    def __flushQueuedText(self):
        """
        Private slot to flush the accumulated text output.
        """
        self.__write(self.__queuedText)

        self.__queuedText = ""
        self.__blockTextProcessing = False

        # little trick to get the cursor position registered within QScintilla
        self.SendScintilla(QsciScintilla.SCI_CHARLEFT)
        self.SendScintilla(QsciScintilla.SCI_CHARRIGHT)

    def __write(self, s):
        """
        Private method to display some text without queuing.

        @param s text to be displayed
        @type str
        """
        line, col = self.__getEndPos()
        self.setCursorPosition(line, col)
        self.insert(Utilities.filterAnsiSequences(s))
        self.prline, self.prcol = self.getCursorPosition()
        self.ensureCursorVisible()
        self.ensureLineVisible(self.prline)

    def __writeStdOut(self, s):
        """
        Private method to display some text with StdOut label.

        @param s text to be displayed
        @type str
        """
        self.__write(self.tr("StdOut: {0}").format(s))

    def __writeStdErr(self, s):
        """
        Private method to display some text with StdErr label.

        @param s text to be displayed
        @type str
        """
        self.__write(self.tr("StdErr: {0}").format(s))

    def __raw_input(self, prompt, echo, debuggerId):
        """
        Private method to handle raw input.

        @param prompt the input prompt
        @type str
        @param echo flag indicating an echoing of the input
        @type bool
        @param debuggerId ID of the debugger backend
        @type str
        """
        if self.__inRawMode:
            # we are processing another raw input event already
            self.__rawModeQueue.append((debuggerId, prompt, echo))
        else:
            self.setFocus(Qt.FocusReason.OtherFocusReason)
            self.__inRawMode = True
            self.__echoInput = echo
            self.__rawModeDebuggerId = debuggerId

            # Get all text which is still waiting for output
            QApplication.processEvents()
            self.__flushQueuedText()

            self.__write(self.tr("<{0}> {1}").format(debuggerId, prompt))
            line, col = self.__getEndPos()
            self.setCursorPosition(line, col)
            buf = self.text(line)
            if buf.startswith(sys.ps1):
                buf = buf.replace(sys.ps1, "")
            if buf.startswith(sys.ps2):
                buf = buf.replace(sys.ps2, "")
            self.prompt = buf
            # move cursor to end of line
            self.moveCursorToEOL()

    @pyqtSlot()
    def paste(self, lines=None):
        """
        Public slot to handle the paste action.

        @param lines list of lines to be inserted
        @type list of str
        """
        if self.__isCursorOnLastLine():
            line, col = self.getCursorPosition()
            lastLine = self.text(line)
            if lastLine.startswith(sys.ps1):
                lastLine = lastLine[len(sys.ps1) :]
                col -= len(sys.ps1)
                prompt = sys.ps1
            elif lastLine.startswith(sys.ps2):
                lastLine = lastLine[len(sys.ps2) :]
                col -= len(sys.ps2)
                prompt = sys.ps2
            else:
                prompt = ""
            if col < 0:
                col = 0
                prompt = ""

            # Remove if text is selected
            if self.hasSelectedText():
                lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
                if self.text(lineFrom).startswith(sys.ps1):
                    indexFrom -= len(sys.ps1)
                    indexTo -= len(sys.ps1)
                elif self.text(lineFrom).startswith(sys.ps2):
                    indexFrom -= len(sys.ps2)
                    indexTo -= len(sys.ps2)
                if indexFrom < 0:
                    indexFrom = 0
                lastLine = lastLine[:indexFrom] + lastLine[indexTo:]
                col = indexFrom

            self.setCursorPosition(line, len(prompt))
            self.deleteLineRight()

            if lines is None:
                lines = QApplication.clipboard().text()

            lines = lastLine[:col] + lines + lastLine[col:]
            self.executeLines(lines)
            line, _ = self.getCursorPosition()
            pos = len(self.text(line)) - (len(lastLine) - col)
            self.setCursorPosition(line, pos)

    def executeLines(self, lines, historyIndex=None):
        """
        Public method to execute a set of lines as multiple commands.

        @param lines multiple lines of text to be executed as
            single commands
        @type str
        @param historyIndex history index to be set
        @type int
        """
        lines = lines.splitlines(True)
        if not lines:
            return

        indentLen = self.__indentLength(lines[0])
        for line in lines:
            if line.startswith(sys.ps1):
                line = line[len(sys.ps1) + indentLen :]
            elif line.startswith(sys.ps2):
                line = line[len(sys.ps2) + indentLen :]
            else:
                line = line[indentLen:]

            if line.endswith(("\r\n", "\r", "\n")):
                fullline = True
                cmd = line.rstrip()
            else:
                fullline = False

            self.incrementalSearchActive = True
            self.__insertTextAtEnd(line)
            if fullline:
                self.incrementalSearchActive = False

                self.__executeCommand(cmd, historyIndex=historyIndex)
                if self.interruptCommandExecution:
                    self.__executeCommand("")
                    break

    def __indentLength(self, line):
        """
        Private method to determine the indentation length of the given line.

        @param line line to determine the indentation length for
        @type str
        @return indentation length
        @rtype int
        """
        if line.startswith(sys.ps1):
            line = line[len(sys.ps1) :]
        # If line starts with sys.ps2 or neither don't manipulate the line.
        indentLen = len(line) - len(line.lstrip())
        return indentLen

    def __clearCurrentLine(self):
        """
        Private method to clear the line containing the cursor.
        """
        line, col = self.getCursorPosition()
        if self.text(line).startswith(sys.ps1):
            col = len(sys.ps1)
        elif self.text(line).startswith(sys.ps2):
            col = len(sys.ps2)
        else:
            col = 0
        self.setCursorPosition(line, col)
        self.deleteLineRight()

    def __insertText(self, s):
        """
        Private method to insert some text at the current cursor position.

        @param s text to be inserted
        @type str
        """
        line, col = self.getCursorPosition()
        self.insertAt(Utilities.filterAnsiSequences(s), line, col)
        self.setCursorPosition(line, col + len(s))

    def __insertTextAtEnd(self, s):
        """
        Private method to insert some text at the end of the command line.

        @param s text to be inserted
        @type str
        """
        line, col = self.__getEndPos()
        self.setCursorPosition(line, col)
        self.insert(Utilities.filterAnsiSequences(s))
        self.prline, _ = self.getCursorPosition()

    def __insertTextNoEcho(self, s):
        """
        Private method to insert some text at the end of the buffer without
        echoing it.

        @param s text to be inserted
        @type str
        """
        self.buff += s
        self.prline, self.prcol = self.getCursorPosition()

    def mousePressEvent(self, event):
        """
        Protected method to handle the mouse press event.

        @param event the mouse press event
        @type QMouseEvent
        """
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        if event.button() == Qt.MouseButton.MiddleButton:
            lines = QApplication.clipboard().text(QClipboard.Mode.Selection)
            self.paste(lines)
        else:
            super().mousePressEvent(event)

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

        @param evt reference to the gesture event (QGestureEvent
        @type int
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

    def editorCommand(self, cmd):
        """
        Public method to perform an editor command.

        @param cmd the scintilla command to be performed
        @type int
        """
        try:
            self.supportedEditorCommands[cmd]()
        except TypeError:
            self.supportedEditorCommands[cmd](cmd)
        except KeyError:
            pass

    def __isCursorOnLastLine(self):
        """
        Private method to check, if the cursor is on the last line.

        @return flag indicating that the cursor is on the last line
        @rtype bool
        """
        cline, _ccol = self.getCursorPosition()
        return cline == self.lines() - 1

    def keyPressEvent(self, ev):
        """
        Protected method to handle the user input a key at a time.

        @param ev key event (QKeyEvent)
        @type int
        """
        txt = ev.text()

        # See it is text to insert.
        if len(txt) and txt >= " ":
            if not self.__isCursorOnLastLine():
                line, col = self.__getEndPos()
                self.setCursorPosition(line, col)
                self.prline, self.prcol = self.getCursorPosition()
            if self.__echoInput:
                ac = self.isListActive()
                super().keyPressEvent(ev)
                self.incrementalSearchActive = True
                if ac and self.racEnabled:
                    self.dbs.remoteCompletion(
                        self.__getSelectedDebuggerId(), self.completionText + txt
                    )
            else:
                self.__insertTextNoEcho(txt)
        else:
            ev.ignore()

    def __QScintillaCommand(self, cmd):
        """
        Private method to send the command to QScintilla.

        @param cmd QScintilla command
        @type int
        """
        self.SendScintilla(cmd)

    def __QScintillaTab(self, cmd):
        """
        Private method to handle the Tab key.

        @param cmd QScintilla command
        @type int
        """
        if self.isListActive():
            self.SendScintilla(cmd)
        elif self.__isCursorOnLastLine():
            line, index = self.getCursorPosition()
            buf = self.text(line)
            if buf.startswith(sys.ps1):
                buf = buf.replace(sys.ps1, "")
            if buf.startswith(sys.ps2):
                buf = buf.replace(sys.ps2, "")
            if self.inContinue and not buf[: index - len(sys.ps2)].strip():
                self.SendScintilla(cmd)
            elif self.racEnabled:
                self.dbs.remoteCompletion(self.__getSelectedDebuggerId(), buf)

    def __QScintillaLeftDeleteCommand(self, method):
        """
        Private method to handle a QScintilla delete command working to
        the left.

        @param method shell method to execute
        @type int
        """
        if self.__isCursorOnLastLine():
            line, col = self.getCursorPosition()
            db = 0
            ac = self.isListActive()
            oldLength = len(self.text(line))

            if self.text(line).startswith(sys.ps1):
                if col > len(sys.ps1):
                    method()
                    db = 1
            elif self.text(line).startswith(sys.ps2):
                if col > len(sys.ps2):
                    method()
                    db = 1
            elif col > 0:
                method()
                db = 1
            if db and ac and self.racEnabled and self.completionText:
                delta = len(self.text(line)) - oldLength
                self.dbs.remoteCompletion(
                    self.__getSelectedDebuggerId(), self.completionText[:delta]
                )

    def __QScintillaDeleteBack(self):
        """
        Private method to handle the Backspace key.
        """
        self.__QScintillaLeftDeleteCommand(self.deleteBack)

    def __QScintillaDeleteWordLeft(self):
        """
        Private method to handle the Delete Word Left command.
        """
        self.__QScintillaLeftDeleteCommand(self.deleteWordLeft)

    def __QScintillaDelete(self):
        """
        Private method to handle the delete command.
        """
        if self.__isCursorOnLastLine():
            if self.hasSelectedText():
                lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
                if self.text(lineFrom).startswith(sys.ps1):
                    if indexFrom >= len(sys.ps1):
                        self.delete()
                elif self.text(lineFrom).startswith(sys.ps2):
                    if indexFrom >= len(sys.ps2):
                        self.delete()
                elif indexFrom >= 0:
                    self.delete()
            else:
                self.delete()

    def __QScintillaDeleteLineLeft(self):
        """
        Private method to handle the Delete Line Left command.
        """
        if self.__isCursorOnLastLine():
            if self.isListActive():
                self.cancelList()

            line, col = self.getCursorPosition()
            if self.text(line).startswith(sys.ps1):
                prompt = sys.ps1
            elif self.text(line).startswith(sys.ps2):
                prompt = sys.ps2
            else:
                prompt = ""

            self.deleteLineLeft()
            self.insertAt(prompt, line, 0)
            self.setCursorPosition(line, len(prompt))

    def __QScintillaNewline(self, cmd):
        """
        Private method to handle the Return key.

        @param cmd QScintilla command
        @type int
        """
        if self.__isCursorOnLastLine():
            if self.isListActive():
                self.SendScintilla(cmd)
            else:
                self.incrementalSearchString = ""
                self.incrementalSearchActive = False
                line, col = self.__getEndPos()
                self.setCursorPosition(line, col)
                buf = self.text(line)
                if buf.startswith(sys.ps1):
                    buf = buf.replace(sys.ps1, "")
                if buf.startswith(sys.ps2):
                    buf = buf.replace(sys.ps2, "")
                self.insert("\n")
                self.__executeCommand(buf)
        else:
            txt = ""
            line, col = self.getCursorPosition()
            if self.hasSelectedText():
                lineFrom, indexFrom, lineTo, indexTo = self.getSelection()
                if line == lineFrom:
                    txt = self.text(line)[indexFrom:].rstrip()
                elif line == lineTo:
                    txt = self.text(line)[:indexTo]
            else:
                txt = self.text(line)[col:].rstrip()

            if txt:
                line, col = self.__getEndPos()
                self.setCursorPosition(line, col)
                self.insert(txt)

    def __QScintillaLeftCommand(self, method):
        """
        Private method to handle a QScintilla command working to the left.

        @param method shell method to execute
        @type int
        """
        line, col = self.getCursorPosition()
        if col > 0:
            method()

        # adjust cursor position
        line, col = self.getCursorPosition()
        if self.text(line).startswith(sys.ps1) and col < len(sys.ps1):
            self.setCursorPosition(line, len(sys.ps1))
        elif self.text(line).startswith(sys.ps2) and col < len(sys.ps2):
            self.setCursorPosition(line, len(sys.ps2))

    def __QScintillaCharLeft(self):
        """
        Private method to handle the Cursor Left command.
        """
        self.__QScintillaLeftCommand(self.moveCursorLeft)

    def __QScintillaWordLeft(self):
        """
        Private method to handle the Cursor Word Left command.
        """
        self.__QScintillaLeftCommand(self.moveCursorWordLeft)

    def __QScintillaRightCommand(self, method):
        """
        Private method to handle a QScintilla command working to the right.

        @param method shell method to execute
        @type function
        """
        method()

        # adjust cursor position
        line, col = self.getCursorPosition()
        if self.text(line).startswith(sys.ps1) and col < len(sys.ps1):
            self.setCursorPosition(line, len(sys.ps1))
        elif self.text(line).startswith(sys.ps2) and col < len(sys.ps2):
            self.setCursorPosition(line, len(sys.ps2))

    def __QScintillaCharRight(self):
        """
        Private method to handle the Cursor Right command.
        """
        self.__QScintillaRightCommand(self.moveCursorRight)

    def __QScintillaWordRight(self):
        """
        Private method to handle the Cursor Word Right command.
        """
        self.__QScintillaRightCommand(self.moveCursorWordRight)

    def __QScintillaDeleteWordRight(self):
        """
        Private method to handle the Delete Word Right command.
        """
        # delete is only allowed on the last line
        if self.__isCursorOnLastLine():
            self.__QScintillaRightCommand(self.deleteWordRight)

    def __QScintillaDeleteLineRight(self):
        """
        Private method to handle the Delete Line Right command.
        """
        # delete is only allowed on the last line
        if self.__isCursorOnLastLine():
            self.__QScintillaRightCommand(self.deleteLineRight)

    def __QScintillaVCHome(self, cmd):
        """
        Private method to handle the Home key.

        @param cmd QScintilla command
        @type int
        """
        if self.isListActive():
            self.SendScintilla(cmd)
        else:
            line, col = self.getCursorPosition()
            if self.text(line).startswith(sys.ps1):
                col = len(sys.ps1)
            elif self.text(line).startswith(sys.ps2):
                col = len(sys.ps2)
            else:
                col = 0
            self.setCursorPosition(line, col)

    def __QScintillaLineEnd(self, cmd):
        """
        Private method to handle the End key.

        @param cmd QScintilla command
        @type int
        """
        if self.isListActive():
            self.SendScintilla(cmd)
        else:
            self.moveCursorToEOL()

    def __QScintillaCursorCommand(self, cmd):
        """
        Private method to handle the cursor commands.

        @param cmd QScintilla command
        @type int
        """
        if self.isListActive() or self.isCallTipActive():
            if cmd in (QsciScintilla.SCI_LINEUP, QsciScintilla.SCI_LINEDOWN):
                self.SendScintilla(cmd)
        else:
            if self.__historyNavigateByCursor:
                if cmd == QsciScintilla.SCI_LINEUP:
                    self.__QScintillaHistoryUp(cmd)
                elif cmd == QsciScintilla.SCI_LINEDOWN:
                    self.__QScintillaHistoryDown(cmd)
                elif cmd == QsciScintilla.SCI_LINESCROLLUP:
                    self.__QScintillaLineUp(cmd)
                elif cmd == QsciScintilla.SCI_LINESCROLLDOWN:
                    self.__QScintillaLineDown(cmd)
            else:
                if cmd == QsciScintilla.SCI_LINEUP:
                    self.__QScintillaLineUp(cmd)
                elif cmd == QsciScintilla.SCI_LINEDOWN:
                    self.__QScintillaLineDown(cmd)
                elif cmd == QsciScintilla.SCI_LINESCROLLUP:
                    self.__QScintillaHistoryUp(cmd)
                elif cmd == QsciScintilla.SCI_LINESCROLLDOWN:
                    self.__QScintillaHistoryDown(cmd)

    def __QScintillaLineUp(self, _cmd):
        """
        Private method to handle the cursor up command.

        @param _cmd QScintilla command (unused)
        @type int
        """
        self.SendScintilla(QsciScintilla.SCI_LINEUP)

    def __QScintillaLineDown(self, _cmd):
        """
        Private method to handle the cursor down command.

        @param _cmd QScintilla command (unused)
        @type int
        """
        self.SendScintilla(QsciScintilla.SCI_LINEDOWN)

    def __QScintillaHistoryUp(self, _cmd):
        """
        Private method to handle the history up command.

        @param _cmd QScintilla command (unused)
        @type int
        """
        if self.isHistoryEnabled():
            line, col = self.__getEndPos()
            buf = self.text(line)
            if buf.startswith(sys.ps1):
                buf = buf.replace(sys.ps1, "")
            if buf.startswith(sys.ps2):
                buf = buf.replace(sys.ps2, "")
            if buf and self.incrementalSearchActive:
                if self.incrementalSearchString and buf.startswith(
                    self.incrementalSearchString
                ):
                    idx, found = self.__rsearchHistory(
                        self.incrementalSearchString, self.__histidx
                    )
                    if found and idx >= 0:
                        self.__setHistoryIndex(index=idx)
                        self.__useHistory()
                else:
                    idx, found = self.__rsearchHistory(buf)
                    if found and idx >= 0:
                        self.__setHistoryIndex(index=idx)
                        self.incrementalSearchString = buf
                        self.__useHistory()
            else:
                if self.__historyWrap:
                    if self.__histidx < 0:
                        # wrap around
                        self.__setHistoryIndex(index=len(self.__history) - 1)
                    else:
                        self.__setHistoryIndex(index=self.__histidx - 1)
                    self.__useHistory()
                else:
                    if self.__histidx < 0:
                        self.__setHistoryIndex(index=len(self.__history) - 1)
                        self.__useHistory()
                    elif self.__histidx > 0:
                        self.__setHistoryIndex(index=self.__histidx - 1)
                        self.__useHistory()

    def __QScintillaHistoryDown(self, _cmd):
        """
        Private method to handle the history down command.

        @param _cmd QScintilla command (unused)
        @type int
        """
        if self.isHistoryEnabled():
            line, col = self.__getEndPos()
            buf = self.text(line)
            if buf.startswith(sys.ps1):
                buf = buf.replace(sys.ps1, "")
            if buf.startswith(sys.ps2):
                buf = buf.replace(sys.ps2, "")
            if buf and self.incrementalSearchActive:
                if self.incrementalSearchString and buf.startswith(
                    self.incrementalSearchString
                ):
                    idx, found = self.__searchHistory(
                        self.incrementalSearchString, self.__histidx
                    )
                    if found and idx >= 0:
                        self.__setHistoryIndex(index=idx)
                        self.__useHistory()
                else:
                    idx, found = self.__searchHistory(buf)
                    if found and idx >= 0:
                        self.__setHistoryIndex(index=idx)
                        self.incrementalSearchString = buf
                        self.__useHistory()
            else:
                if self.__historyWrap:
                    if self.__histidx >= len(self.__history) - 1:
                        # wrap around
                        self.__setHistoryIndex(index=0)
                    else:
                        self.__setHistoryIndex(index=self.__histidx + 1)
                    self.__useHistory()
                else:
                    if self.__isHistoryIndexValid():
                        self.__setHistoryIndex(index=self.__histidx + 1)
                        self.__useHistory()

    def __QScintillaCancel(self):
        """
        Private method to handle the ESC command.
        """
        if self.isListActive() or self.isCallTipActive():
            self.SendScintilla(QsciScintilla.SCI_CANCEL)
        else:
            if self.incrementalSearchActive:
                self.__resetIncrementalHistorySearch()
            self.__insertHistory("")

    def __QScintillaCharLeftExtend(self):
        """
        Private method to handle the Extend Selection Left command.
        """
        self.__QScintillaLeftCommand(self.extendSelectionLeft)

    def __QScintillaWordLeftExtend(self):
        """
        Private method to handle the Extend Selection Left one word command.
        """
        self.__QScintillaLeftCommand(self.extendSelectionWordLeft)

    def __QScintillaVCHomeExtend(self):
        """
        Private method to handle the Extend Selection to start of line command.
        """
        line, col = self.getCursorPosition()
        if self.text(line).startswith(sys.ps1):
            col = len(sys.ps1)
        elif self.text(line).startswith(sys.ps2):
            col = len(sys.ps2)
        else:
            col = 0

        self.extendSelectionToBOL()
        while col > 0:
            self.extendSelectionRight()
            col -= 1

    def __QScintillaAutoCompletionCommand(self, cmd):
        """
        Private method to handle a command for autocompletion only.

        @param cmd QScintilla command
        @type int
        """
        if self.isListActive() or self.isCallTipActive():
            self.SendScintilla(cmd)

    def __executeCommand(self, cmd, historyIndex=None):
        """
        Private slot to execute a command.

        @param cmd command to be executed by debug client
        @type str
        @param historyIndex history index to be set
        @type int
        """
        if not self.__inRawMode:
            self.inCommandExecution = True
            self.interruptCommandExecution = False
            if not cmd:
                # make sure cmd is a string
                cmd = ""

            # History Handling
            if self.isHistoryEnabled():
                if cmd != "" and (
                    len(self.__history) == 0 or self.__history[-1] != cmd
                ):
                    if len(self.__history) == self.__maxHistoryEntries:
                        del self.__history[0]
                    self.__history.append(cmd)
                if self.__historyStyle == ShellHistoryStyle.LINUXSTYLE:
                    self.__setHistoryIndex(index=-1)
                elif self.__historyStyle == ShellHistoryStyle.WINDOWSSTYLE:
                    if historyIndex is None:
                        if (
                            self.__histidx - 1 > 0
                            and cmd != self.__history[self.__histidx - 1]
                        ):
                            self.__setHistoryIndex(index=-1)
                    else:
                        self.__setHistoryIndex(historyIndex)

            if cmd.startswith("%"):
                if cmd == "%start" or cmd.startswith("%start "):
                    if not self.passive:
                        cmdList = cmd.split(None, 1)
                        if len(cmdList) < 2:
                            self.dbs.startClient(False)
                            # start default backend
                        else:
                            venvName = cmdList[1]
                            if venvName in (
                                self.tr("Project"),
                                self.tr("Project").lower(),
                                "Project",
                                "project",
                            ):
                                if self.__project and self.__project.isOpen():
                                    self.dbs.startClient(
                                        False,
                                        forProject=True,
                                        workingDir=self.__project.getProjectPath(),
                                    )
                                    self.__currentWorkingDirectory = (
                                        self.__project.getProjectPath()
                                    )
                                else:
                                    self.dbs.startClient(
                                        False,
                                        venvName=self.__currentVenv,
                                        workingDir=self.__currentWorkingDirectory,
                                    )
                                    # same as reset
                            else:
                                self.dbs.startClient(False, venvName=venvName)
                                self.__currentWorkingDirectory = ""
                    self.__getBanner()
                elif cmd == "%clear":
                    # Display the banner.
                    self.__getBanner()
                elif cmd in ["%reset", "%restart"]:
                    self.doRestart()
                elif cmd in ["%envs", "%environments"]:
                    venvs = (
                        ericApp().getObject("VirtualEnvManager").getVirtualenvNames()
                    )
                    s = self.tr("Available Virtual Environments:\n{0}\n").format(
                        "\n".join("- {0}".format(venv) for venv in sorted(venvs))
                    )
                    self.__write(s)
                    self.__clientStatement(False)
                elif cmd == "%which":
                    s = self.tr("Current Virtual Environment: '{0}'\n").format(
                        self.__currentVenv
                    )
                    self.__write(s)
                    self.__clientStatement(False)
                elif (
                    cmd in ["%quit", "%quit()", "%exit", "%exit()"] and self.__windowed
                ):
                    # call main window quit()
                    self.vm.quit()
                elif cmd in ("%hist", "%history") or cmd.startswith(
                    ("%hist ", "%history ")
                ):
                    cmdList = cmd.split(None, 1)
                    if len(cmdList) == 2:
                        try:
                            histSize = int(cmdList[1])
                        except ValueError:
                            s = self.tr("Error: Argument must be an integer value.\n")
                            self.__write(s)
                            self.__clientStatement(False)
                            return
                    else:
                        histSize = None
                    self.showHistory(histSize)
                    self.__clientStatement(False)
                elif cmd in ("%shist", "%shistory", "%select_history"):
                    self.selectHistory()
                elif cmd in ("%chist", "%chistory", "%clear_history"):
                    self.clearHistory()
                    self.__clientStatement(False)
                elif cmd == "%help":
                    self.__showHelp()
                    self.__clientStatement(False)
                else:
                    s = self.tr("Error: Command '{0}' is not supported.\n").format(cmd)
                    self.__write(s)
                    self.__clientStatement(False)
                self.setFocus(Qt.FocusReason.OtherFocusReason)
            else:
                self.dbs.remoteStatement(self.__getSelectedDebuggerId(), cmd)
                now = time.monotonic()
                timeDelta = 0
                while (
                    self.inCommandExecution
                    and timeDelta <= self.__commandExecutionTimeout
                ):
                    timeDelta = time.monotonic() - now
                    # configurable timeout
                    with contextlib.suppress(KeyboardInterrupt):
                        QApplication.processEvents()
                self.inCommandExecution = False
                if timeDelta > self.__commandExecutionTimeout:
                    # timeout -> write a hint into the shell window
                    s = self.tr(
                        "Execution of the interpreter statement timed out after"
                        " {0} seconds.\n"
                    ).format(self.__commandExecutionTimeout)
                    self.__write(s)
                    self.__clientStatement(False)
        else:
            if not self.__echoInput:
                cmd = self.buff
                self.buff = ""
            elif cmd:
                cmd = cmd[len(self.prompt) :]
            self.__inRawMode = False
            self.__echoInput = True

            self.dbs.remoteRawInput(self.__rawModeDebuggerId, cmd)

            if self.__rawModeQueue:
                debuggerId, prompt, echo = self.__rawModeQueue.pop(0)
                self.__raw_input(prompt, echo, debuggerId)

    def __showVenvName(self):
        """
        Private method to show the name of the active virtual environment.
        """
        s = "\n" + self.tr("Current Virtual Environment: '{0}'\n").format(
            self.__currentVenv
        )
        self.__write(s)
        self.__clientStatement(False)

    def __useHistory(self):
        """
        Private method to display a command from the history.
        """
        if self.__isHistoryIndexValid():
            cmd = self.__history[self.__histidx]
        else:
            cmd = ""
            self.__resetIncrementalHistorySearch()

        self.__insertHistory(cmd)

    def __insertHistory(self, cmd):
        """
        Private method to insert a command selected from the history.

        @param cmd history entry to be inserted
        @type str
        """
        self.setCursorPosition(self.prline, self.prcol)
        self.setSelection(
            self.prline, self.prcol, self.prline, self.lineLength(self.prline)
        )
        self.removeSelectedText()
        self.__insertText(cmd)

    def __resetIncrementalHistorySearch(self):
        """
        Private method to reset the incremental history search.
        """
        self.incrementalSearchString = ""
        self.incrementalSearchActive = False

    def __searchHistory(self, txt, startIdx=-1):
        """
        Private method used to search the history.

        @param txt text to match at the beginning
        @type str
        @param startIdx index to start search from
        @type int
        @return tuple containing the index of found entry and a flag indicating
            that something was found
        @rtype tuple of (int, bool)
        """
        idx = 0 if startIdx == -1 else startIdx + 1
        while idx < len(self.__history) and not self.__history[idx].startswith(txt):
            idx += 1
        found = idx < len(self.__history) and self.__history[idx].startswith(txt)
        return idx, found

    def __rsearchHistory(self, txt, startIdx=-1):
        """
        Private method used to reverse search the history.

        @param txt text to match at the beginning
        @type str
        @param startIdx index to start search from
        @type int
        @return tuple containing the index of found entry and a flag indicating
            that something was found
        @rtype tuple of (int, bool)
        """
        idx = len(self.__history) - 1 if startIdx == -1 else startIdx - 1
        while idx >= 0 and not self.__history[idx].startswith(txt):
            idx -= 1
        found = idx >= 0 and self.__history[idx].startswith(txt)
        return idx, found

    def focusNextPrevChild(self, nextChild):
        """
        Public method to stop Tab moving to the next window.

        While the user is entering a multi-line command, the movement to
        the next window by the Tab key being pressed is suppressed.

        @param nextChild next window
        @type QWidget
        @return flag indicating the movement
        @rtype bool
        """
        if nextChild and self.inContinue:
            return False

        return QsciScintillaCompat.focusNextPrevChild(self, nextChild)

    @pyqtSlot(QPoint)
    def __showContextMenu(self, pos):
        """
        Private slot to show a context menu.

        @param pos position for the context menu
        @type QPoint
        """
        if not self.__windowed:
            # check, if the cursor is positioned on an exception line
            # The exception line looks like 'File: /path/of/file.py, Line: 111'.
            line = self.getCursorPosition()[0]
            text = self.text(line).strip()
            self.__showSourceAct.setEnabled(
                bool(re.search(r"File: (.*?), Line: (\d+)", text))
            )

            self.menu.popup(self.mapToGlobal(pos))

    def clear(self):
        """
        Public slot to clear the display.
        """
        # Display the banner.
        self.__getBanner()

    def doClearRestart(self):
        """
        Public slot to handle the 'restart and clear' context menu entry.
        """
        self.doRestart()
        self.clear()

    def doRestart(self):
        """
        Public slot to handle the 'restart' context menu entry.
        """
        venvName = (
            self.dbs.getProjectEnvironmentString()
            if (
                self.__project
                and self.__project.isOpen()
                and self.__currentVenv
                == self.__project.getProjectVenv(resolveDebugger=False)
            )
            else self.__currentVenv
        )
        self.dbs.startClient(
            False,
            venvName=venvName,
            workingDir=self.__currentWorkingDirectory,
        )

    def __startDebugClient(self, action):
        """
        Private slot to start a debug client according to the action
        triggered.

        @param action context menu action that was triggered
        @type QAction
        """
        venvName = action.data()
        if venvName == "<<project>>":
            if self.__project and self.__project.isOpen():
                self.__currentWorkingDirectory = self.__project.getProjectPath()
            self.dbs.startClient(
                False, forProject=True, workingDir=self.__currentWorkingDirectory
            )
        elif venvName == "<<eric-server>>":
            self.dbs.startClient(False, startViaServer=True)
        elif venvName.startswith("<<eric-server>>:"):
            venvName = venvName.split(":", 1)[1]
            self.dbs.startClient(False, venvName=venvName, startViaServer=True)
        else:
            self.dbs.startClient(False, venvName=venvName)
        self.__getBanner()

    def handlePreferencesChanged(self):
        """
        Public slot to handle the preferencesChanged signal.
        """
        # rebind the lexer
        self.__bindLexer(self.language)
        self.recolor()

        # set margin 0 configuration
        self.__setTextDisplay()
        self.__setMargin0()

        # set the autocompletion and calltips function
        self.__setAutoCompletion()
        self.__setCallTips()

        # do the history related stuff
        self.__maxHistoryEntries = Preferences.getShell("MaxHistoryEntries")
        for key in list(self.__historyLists):
            self.__historyLists[key] = self.__historyLists[key][
                -self.__maxHistoryEntries :
            ]
        self.__historyStyle = Preferences.getShell("HistoryStyle")
        self.__historyWrap = Preferences.getShell("HistoryWrap")
        self.__setHistoryIndex()
        if not self.__windowed:
            self.hmenu.menuAction().setEnabled(self.isHistoryEnabled())
        self.__historyNavigateByCursor = Preferences.getShell("HistoryNavigateByCursor")
        self.historyStyleChanged.emit(self.__historyStyle)

        # do stdout /stderr stuff
        showStdOutErr = Preferences.getShell("ShowStdOutErr")
        if self.__showStdOutErr != showStdOutErr:
            if showStdOutErr:
                self.dbs.clientProcessStdout.connect(self.__writeStdOut)
                self.dbs.clientProcessStderr.connect(self.__writeStdErr)
            else:
                self.dbs.clientProcessStdout.disconnect(self.__writeStdOut)
                self.dbs.clientProcessStderr.disconnect(self.__writeStdErr)
            self.__showStdOutErr = showStdOutErr

        # do some additional configuration parameters
        self.__commandExecutionTimeout = Preferences.getShell("CommandExecutionTimeout")

    @pyqtSlot(list, str)
    def __showCompletions(self, completions, text):
        """
        Private method to display the possible completions.

        @param completions list of possible completions
        @type list of str
        @param text text that is about to be completed
        @type str
        """
        if len(completions) == 0:
            return

        if len(completions) > 1:
            completions.sort()
            self.showUserList(1, completions)
            self.completionText = text
        else:
            txt = completions[0]
            if text != "":
                txt = txt.replace(text, "")
            self.__insertText(txt)
            self.completionText = ""

    def __completionListSelected(self, listId, txt):
        """
        Private slot to handle the selection from the completion list.

        @param listId the ID of the user list (should be 1)
        @type int
        @param txt the selected text
        @type str
        """
        if listId == 1:
            if self.completionText != "":
                txt = txt.replace(self.completionText, "")
            self.__insertText(txt)
            self.completionText = ""

    #################################################################
    ## Drag and Drop Support
    #################################################################

    def dragEnterEvent(self, event):
        """
        Protected method to handle the drag enter event.

        @param event the drag enter event
        @type QDragEnterEvent
        """
        self.inDragDrop = event.mimeData().hasUrls() or event.mimeData().hasText()
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
        if event.mimeData().hasUrls() and not self.__windowed:
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
        elif event.mimeData().hasText():
            s = event.mimeData().text()
            if s:
                event.acceptProposedAction()
                self.executeLines(s)
            del s
        else:
            super().dropEvent(event)

        self.inDragDrop = False

    def focusInEvent(self, event):
        """
        Protected method called when the shell receives focus.

        @param event the event object
        @type QFocusEvent
        """
        if not self.__actionsAdded:
            self.addActions(self.vm.editorActGrp.actions())
            self.addActions(self.vm.copyActGrp.actions())
            self.addActions(self.vm.viewActGrp.actions())
            if not self.__windowed:
                self.__searchShortcut = QShortcut(
                    self.vm.searchAct.shortcut(), self, self.__find, self.__find
                )
                self.__searchNextShortcut = QShortcut(
                    self.vm.searchNextAct.shortcut(),
                    self,
                    self.__searchNext,
                    self.__searchNext,
                )
                self.__searchPrevShortcut = QShortcut(
                    self.vm.searchPrevAct.shortcut(),
                    self,
                    self.__searchPrev,
                    self.__searchPrev,
                )

        with contextlib.suppress(AttributeError):
            self.vm.editActGrp.setEnabled(False)
            self.vm.editorActGrp.setEnabled(True)
            self.vm.copyActGrp.setEnabled(True)
            self.vm.viewActGrp.setEnabled(True)
            self.vm.searchActGrp.setEnabled(False)
        if not self.__windowed:
            self.__searchShortcut.setEnabled(True)
            self.__searchNextShortcut.setEnabled(True)
            self.__searchPrevShortcut.setEnabled(True)
        self.setCaretWidth(self.caretWidth)
        self.setCursorFlashTime(QApplication.cursorFlashTime())

        super().focusInEvent(event)

    def focusOutEvent(self, event):
        """
        Protected method called when the shell loses focus.

        @param event the event object
        @type QFocusEvent
        """
        with contextlib.suppress(AttributeError):
            self.vm.editorActGrp.setEnabled(False)
        if not self.__windowed:
            self.__searchShortcut.setEnabled(False)
            self.__searchNextShortcut.setEnabled(False)
            self.__searchPrevShortcut.setEnabled(False)
        self.setCaretWidth(0)
        super().focusOutEvent(event)

    def insert(self, txt):
        """
        Public slot to insert text at the current cursor position.

        The cursor is advanced to the end of the inserted text.

        @param txt text to be inserted
        @type str
        """
        txt = Utilities.filterAnsiSequences(txt)
        length = len(txt)
        line, col = self.getCursorPosition()
        self.insertAt(txt, line, col)
        if re.search(self.linesepRegExp, txt) is not None:
            line += 1
        self.setCursorPosition(line, col + length)

    def __configure(self):
        """
        Private method to open the configuration dialog.
        """
        ericApp().getObject("UserInterface").showPreferences("shellPage")

    def __find(self):
        """
        Private slot to show the find widget.
        """
        txt = self.selectedText()
        self.__mainWindow.showFind(txt)

    def __searchNext(self):
        """
        Private method to search for the next occurrence.
        """
        if self.__lastSearch:
            self.searchNext(*self.__lastSearch)

    def searchNext(self, txt, caseSensitive, wholeWord, regexp):
        """
        Public method to search the next occurrence of the given text.

        @param txt text to search for
        @type str
        @param caseSensitive flag indicating to perform a case sensitive
            search
        @type bool
        @param wholeWord flag indicating to search for whole words
            only
        @type bool
        @param regexp flag indicating a regular expression search
        @type bool
        """
        self.__lastSearch = (txt, caseSensitive, wholeWord, regexp)
        posixMode = Preferences.getEditor("SearchRegexpMode") == 0 and regexp
        cxx11Mode = Preferences.getEditor("SearchRegexpMode") == 1 and regexp
        ok = self.findFirst(
            txt,
            regexp,
            caseSensitive,
            wholeWord,
            True,
            forward=True,
            posix=posixMode,
            cxx11=cxx11Mode,
        )
        self.searchStringFound.emit(ok)

    def __searchPrev(self):
        """
        Private method to search for the next occurrence.
        """
        if self.__lastSearch:
            self.searchPrev(*self.__lastSearch)

    def searchPrev(self, txt, caseSensitive, wholeWord, regexp):
        """
        Public method to search the previous occurrence of the given text.

        @param txt text to search for
        @type str
        @param caseSensitive flag indicating to perform a case sensitive
            search
        @type bool
        @param wholeWord flag indicating to search for whole words
            only
        @type bool
        @param regexp flag indicating a regular expression search
        @type bool
        """
        self.__lastSearch = (txt, caseSensitive, wholeWord, regexp)
        if self.hasSelectedText():
            line, index = self.getSelection()[:2]
        else:
            line, index = -1, -1
        posixMode = Preferences.getEditor("SearchRegexpMode") == 0 and regexp
        cxx11Mode = Preferences.getEditor("SearchRegexpMode") == 1 and regexp
        ok = self.findFirst(
            txt,
            regexp,
            caseSensitive,
            wholeWord,
            True,
            forward=False,
            line=line,
            index=index,
            posix=posixMode,
            cxx11=cxx11Mode,
        )
        self.searchStringFound.emit(ok)

    def historyStyle(self):
        """
        Public method to get the shell history style.

        @return shell history style
        @rtype ShellHistoryStyle
        """
        return self.__historyStyle

    def isHistoryEnabled(self):
        """
        Public method to check, if the history is enabled.

        @return flag indicating if history is enabled
        @rtype bool
        """
        return self.__historyStyle != ShellHistoryStyle.DISABLED

    def saveContents(self):
        """
        Public method to save the current contents to a file.
        """
        txt = self.text()
        if txt:
            fn, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
                self,
                self.tr("Save Shell Contents"),
                Preferences.getMultiProject("Workspace"),
                self.tr("Text Files (*.txt);;All Files (*)"),
                None,
                EricFileDialog.DontConfirmOverwrite,
            )

            if not fn:
                return

            if fn.endswith("."):
                fn = fn[:-1]

            fpath = pathlib.Path(fn)
            if not fpath.suffix:
                ex = selectedFilter.split("(*")[1].split(")")[0]
                if ex:
                    fpath = fpath.with_suffix(ex)
            if fpath.exists():
                res = EricMessageBox.yesNo(
                    self,
                    self.tr("Save Shell Contents"),
                    self.tr(
                        "<p>The file <b>{0}</b> already exists. Overwrite it?</p>"
                    ).format(fpath),
                    icon=EricMessageBox.Warning,
                )
                if not res:
                    return
            try:
                with fpath.open("w", encoding="utf-8") as f:
                    f.write(txt)
            except (OSError, UnicodeError) as why:
                EricMessageBox.critical(
                    self,
                    self.tr("Save Shell Contents"),
                    self.tr(
                        "<p>The file <b>{0}</b> could not be saved.<br/>"
                        "Reason: {1}</p>"
                    ).format(fpath, str(why)),
                )

    @pyqtSlot()
    def __showHelp(self):
        """
        Private slot to show the list of supported special commands (i.e. those
        starting with a '%' character.
        """
        if self.__helpDialog is None:
            helpStr = "<table>"
            helpStr += self.tr(
                "<tr><td>%restart</td>"
                "<td>Kill the shell and start a new one.</td></tr>"
                "<tr><td>%clear</td>"
                "<td>Clear the display of the shell window.</td></tr>"
                "<tr><td>%start [environment]</td>"
                "<td>Start a shell for a virtual environment with the given name."
                " If no name is given, a default shell is started.</td></tr>"
                "<tr><td>%envs<br/>%environments</td>"
                "<td>Show a list of known virtual environment names.</td></tr>"
                "<tr><td>%which</td>"
                "<td>Show the name of the active virtual environment.</td></tr>"
                "<tr><td>%hist [n]<br/>%history [n]</td>"
                "<td>Show the most recent 'n' entries of the history. If 'n' is"
                " not given, show all entries.</td></tr>"
                "<tr><td>%shist<br/>%shistory<br/>%select_history</td>"
                "<td>Select a command from the history.</td></tr>"
                "<tr><td>%chist<br/>%chistory<br/>%clear_history</td>"
                "<td>Clear the current history after confirmation.</td></tr>"
                "<tr><td>%help</td><td>Show this help text.</td></tr>"
            )
            if self.__windowed:
                helpStr += self.tr(
                    "<tr><td>%quit<br/>%quit()<br/>%exit<br/>%exit()</td>"
                    "<td>Exit the application.</td></tr>"
                    "</table>"
                    "<p>These commands are available through the window menus as well."
                    "</p>"
                )
            else:
                helpStr += self.tr(
                    "</table>"
                    "<p>These commands are available through the context menu as well."
                    "</p>"
                )

            self.__helpDialog = EricSimpleHelpDialog(
                title=self.tr("Shell Special Commands"),
                label=self.tr("The shell supports these special commands:"),
                helpStr=helpStr,
                parent=self,
            )
        self.__helpDialog.show()

    #################################################################
    ## Project Support methods
    #################################################################

    def __projectOpened(self):
        """
        Private slot to start the shell for the opened project.
        """
        if Preferences.getProject("RestartShellForProject"):
            ppath = self.__project.getProjectPath()
            self.dbs.startClient(
                False,
                forProject=True,
                workingDir=ppath,
                startViaServer=FileSystemUtilities.isRemoteFileName(ppath),
            )
            self.__currentWorkingDirectory = self.__project.getProjectPath()
            self.__getBanner()

    def __projectClosed(self):
        """
        Private slot to restart the default shell when the project is closed.
        """
        if not self.__shuttingDown and Preferences.getProject("RestartShellForProject"):
            self.dbs.startClient(False)
            self.__getBanner()

    #######################################################################
    ## Tool methods
    #######################################################################

    def __showSource(self):
        """
        Private method to open an editor for an exception line.

        Note: The exception line looks like 'File: /path/of/file.py, Line: 111'.
        """
        line = self.getCursorPosition()[0]
        text = self.text(line).strip()
        match = re.search(r"File: (.*?), Line: (\d+)", text)
        if match:
            filename = match.group(1)
            linenumber = int(match.group(2))
            self.vm.openSourceFile(filename, lineno=linenumber)

    #################################################################
    ## eric-ide Server Support
    #################################################################

    @pyqtSlot(bool)
    def remoteConnectionChanged(self, connected):
        """
        Public slot handling a change of the connection state to an eric-ide server.

        @param connected flag indicating the connection state
        @type bool
        """
        if connected:
            if Preferences.getEricServer("AutostartShell"):
                self.dbs.startClient(False, startViaServer=True)
        else:
            if self.__currentVenv == self.dbs.getEricServerEnvironmentString():
                # start default backend
                self.dbs.startClient(False)
                self.__getBanner()


#
# eflag: noqa = M601
