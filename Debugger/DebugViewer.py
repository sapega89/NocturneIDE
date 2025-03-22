# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget containing various debug related views.

The views avaliable are:
<ul>
  <li>selector showing all connected debugger backends with associated
      threads</li>
  <li>variables viewer for global variables for the selected debug client</li>
  <li>variables viewer for local variables for the selected debug client</li>
  <li>call stack viewer for the selected debug client</li>
  <li>call trace viewer</li>
  <li>viewer for breakpoints</li>
  <li>viewer for watch expressions</li>
  <li>viewer for exceptions</li>
  <li>viewer for a code disassembly for an exception<li>
</ul>
"""

import os

from PyQt6.QtCore import QCoreApplication, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricTabWidget import EricTabWidget
from eric7.UI.PythonDisViewer import PythonDisViewer, PythonDisViewerModes

from .BreakPointViewer import BreakPointViewer
from .CallStackViewer import CallStackViewer
from .CallTraceViewer import CallTraceViewer
from .ExceptionLogger import ExceptionLogger
from .VariablesViewer import VariablesViewer
from .WatchPointViewer import WatchPointViewer


class DebugViewer(QWidget):
    """
    Class implementing a widget containing various debug related views.

    The individual tabs contain the interpreter shell (optional),
    the filesystem browser (optional), the two variables viewers
    (global and local), a breakpoint viewer, a watch expression viewer and
    the exception logger. Additionally a list of all threads is shown.

    @signal sourceFile(string, int) emitted to open a source file at a line
    @signal preferencesChanged() emitted to react on changed preferences
    """

    sourceFile = pyqtSignal(str, int)
    preferencesChanged = pyqtSignal()

    ThreadIdRole = Qt.ItemDataRole.UserRole + 1
    DebuggerStateRole = Qt.ItemDataRole.UserRole + 2

    # Map debug state to icon name
    StateIcon = {
        "broken": "break",
        "exception": "exceptions",
        "running": "mediaPlaybackStart",
        "syntax": "syntaxError22",
    }

    # Map debug state to user message
    StateMessage = {
        "broken": QCoreApplication.translate("DebugViewer", "waiting at breakpoint"),
        "exception": QCoreApplication.translate("DebugViewer", "waiting at exception"),
        "running": QCoreApplication.translate("DebugViewer", "running"),
        "syntax": QCoreApplication.translate("DebugViewer", "syntax error"),
    }

    def __init__(self, debugServer, parent=None):
        """
        Constructor

        @param debugServer reference to the debug server object
        @type DebugServer
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.debugServer = debugServer
        self.debugUI = None

        self.__setFocusToWidget = None

        self.setWindowIcon(EricPixmapCache.getIcon("eric"))

        self.__mainLayout = QVBoxLayout()
        self.__mainLayout.setContentsMargins(0, 3, 0, 0)
        self.setLayout(self.__mainLayout)

        self.__mainSplitter = QSplitter(Qt.Orientation.Vertical, self)
        self.__mainLayout.addWidget(self.__mainSplitter)

        # add the viewer showing the connected debug backends
        self.__debuggersWidget = QWidget()
        self.__debuggersLayout = QVBoxLayout(self.__debuggersWidget)
        self.__debuggersLayout.setContentsMargins(0, 0, 0, 0)
        self.__debuggersLayout.addWidget(QLabel(self.tr("Debuggers and Threads:")))
        self.__debuggersList = QTreeWidget()
        self.__debuggersList.setHeaderLabels([self.tr("ID"), self.tr("State"), ""])
        self.__debuggersList.header().setStretchLastSection(True)
        self.__debuggersList.setSortingEnabled(True)
        self.__debuggersList.setRootIsDecorated(True)
        self.__debuggersList.setAlternatingRowColors(True)
        self.__debuggersLayout.addWidget(self.__debuggersList)
        self.__mainSplitter.addWidget(self.__debuggersWidget)

        self.__debuggersList.currentItemChanged.connect(self.__debuggerSelected)

        # add the tab widget containing various debug related views
        self.__tabWidget = EricTabWidget()
        self.__mainSplitter.addWidget(self.__tabWidget)

        # add the global variables viewer
        self.gvvWidget = QWidget()
        self.gvvWidgetVLayout = QVBoxLayout(self.gvvWidget)
        self.gvvWidgetVLayout.setContentsMargins(0, 0, 0, 0)
        self.gvvWidgetVLayout.setSpacing(3)
        self.gvvWidget.setLayout(self.gvvWidgetVLayout)

        self.gvvWidgetHLayout1 = QHBoxLayout()
        self.gvvWidgetHLayout1.setContentsMargins(3, 3, 3, 3)

        self.gvvStackComboBox = QComboBox(self.gvvWidget)
        self.gvvStackComboBox.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.gvvWidgetHLayout1.addWidget(self.gvvStackComboBox)

        self.gvvSourceButton = QPushButton(self.tr("Source"), self.gvvWidget)
        self.gvvWidgetHLayout1.addWidget(self.gvvSourceButton)
        self.gvvSourceButton.setEnabled(False)
        self.gvvWidgetVLayout.addLayout(self.gvvWidgetHLayout1)

        self.globalsViewer = VariablesViewer(self, True, self.gvvWidget)
        self.gvvWidgetVLayout.addWidget(self.globalsViewer)

        self.gvvWidgetHLayout = QHBoxLayout()
        self.gvvWidgetHLayout.setContentsMargins(3, 3, 3, 3)

        self.globalsFilterTypeCombo = QComboBox(self.gvvWidget)
        self.globalsFilterTypeCombo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self.globalsFilterTypeCombo.addItems(
            [self.tr("Don't Show"), self.tr("Show Only")]
        )
        self.globalsFilterTypeCombo.setCurrentIndex(
            1 if Preferences.getDebugger("ShowOnlyAsDefault") else 0
        )
        self.gvvWidgetHLayout.addWidget(self.globalsFilterTypeCombo)

        self.globalsFilterEdit = QLineEdit(self.gvvWidget)
        self.globalsFilterEdit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.globalsFilterEdit.setClearButtonEnabled(True)
        self.gvvWidgetHLayout.addWidget(self.globalsFilterEdit)
        self.globalsFilterEdit.setToolTip(
            self.tr(
                "Enter regular expression patterns separated by ';'"
                " to define variable filters. "
            )
        )
        self.globalsFilterEdit.setWhatsThis(
            self.tr(
                "Enter regular expression patterns separated by ';'"
                " to define variable filters. All variables and"
                " class attributes matched by one of the expressions"
                " are not shown in the list above."
            )
        )

        self.setGlobalsFilterButton = QPushButton(self.tr("Set"), self.gvvWidget)
        self.gvvWidgetHLayout.addWidget(self.setGlobalsFilterButton)
        self.gvvWidgetVLayout.addLayout(self.gvvWidgetHLayout)

        index = self.__tabWidget.addTab(
            self.gvvWidget, EricPixmapCache.getIcon("globalVariables"), ""
        )
        self.__tabWidget.setTabToolTip(
            index, self.tr("Shows the list of global variables and their values.")
        )

        self.gvvSourceButton.clicked.connect(self.__showSource)
        self.setGlobalsFilterButton.clicked.connect(self.setGlobalsFilter)
        self.globalsFilterEdit.returnPressed.connect(self.setGlobalsFilter)
        self.globalsFilterEdit.textEdited.connect(
            lambda: self.__filterStringEdited(globalsFilter=True)
        )
        self.globalsFilterTypeCombo.currentIndexChanged.connect(
            lambda: self.__filterStringEdited(globalsFilter=True)
        )

        # add the local variables viewer
        self.lvvWidget = QWidget()
        self.lvvWidgetVLayout = QVBoxLayout(self.lvvWidget)
        self.lvvWidgetVLayout.setContentsMargins(0, 0, 0, 0)
        self.lvvWidgetVLayout.setSpacing(3)
        self.lvvWidget.setLayout(self.lvvWidgetVLayout)

        self.lvvWidgetHLayout1 = QHBoxLayout()
        self.lvvWidgetHLayout1.setContentsMargins(3, 3, 3, 3)

        self.lvvStackComboBox = QComboBox(self.lvvWidget)
        self.lvvStackComboBox.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.lvvWidgetHLayout1.addWidget(self.lvvStackComboBox)

        self.lvvSourceButton = QPushButton(self.tr("Source"), self.lvvWidget)
        self.lvvWidgetHLayout1.addWidget(self.lvvSourceButton)
        self.lvvSourceButton.setEnabled(False)
        self.lvvWidgetVLayout.addLayout(self.lvvWidgetHLayout1)

        self.localsViewer = VariablesViewer(self, False, self.lvvWidget)
        self.lvvWidgetVLayout.addWidget(self.localsViewer)

        self.lvvWidgetHLayout2 = QHBoxLayout()
        self.lvvWidgetHLayout2.setContentsMargins(3, 3, 3, 3)

        self.localsFilterTypeCombo = QComboBox(self.lvvWidget)
        self.localsFilterTypeCombo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToContents
        )
        self.localsFilterTypeCombo.addItems(
            [self.tr("Don't Show"), self.tr("Show Only")]
        )
        self.localsFilterTypeCombo.setCurrentIndex(
            1 if Preferences.getDebugger("ShowOnlyAsDefault") else 0
        )
        self.lvvWidgetHLayout2.addWidget(self.localsFilterTypeCombo)

        self.localsFilterEdit = QLineEdit(self.lvvWidget)
        self.localsFilterEdit.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.localsFilterEdit.setClearButtonEnabled(True)
        self.lvvWidgetHLayout2.addWidget(self.localsFilterEdit)
        self.localsFilterEdit.setToolTip(
            self.tr(
                "Enter regular expression patterns separated by ';' to define "
                "variable filters. "
            )
        )
        self.localsFilterEdit.setWhatsThis(
            self.tr(
                "Enter regular expression patterns separated by ';' to define "
                "variable filters. All variables and class attributes matched"
                " by one of the expressions are not shown in the list above."
            )
        )

        self.setLocalsFilterButton = QPushButton(self.tr("Set"), self.lvvWidget)
        self.lvvWidgetHLayout2.addWidget(self.setLocalsFilterButton)
        self.lvvWidgetVLayout.addLayout(self.lvvWidgetHLayout2)

        index = self.__tabWidget.addTab(
            self.lvvWidget, EricPixmapCache.getIcon("localVariables"), ""
        )
        self.__tabWidget.setTabToolTip(
            index, self.tr("Shows the list of local variables and their values.")
        )

        self.lvvSourceButton.clicked.connect(self.__showSource)
        self.lvvStackComboBox.currentIndexChanged[int].connect(self.__frameSelected)
        self.setLocalsFilterButton.clicked.connect(self.setLocalsFilter)
        self.localsFilterEdit.returnPressed.connect(self.setLocalsFilter)
        self.localsFilterEdit.textEdited.connect(
            lambda: self.__filterStringEdited(globalsFilter=False)
        )
        self.localsFilterTypeCombo.currentIndexChanged.connect(
            lambda: self.__filterStringEdited(globalsFilter=False)
        )

        self.preferencesChanged.connect(self.handlePreferencesChanged)
        self.preferencesChanged.connect(self.globalsViewer.preferencesChanged)
        self.preferencesChanged.connect(self.localsViewer.preferencesChanged)

        # interconnect the stack selectors of the variable viewers
        self.gvvStackComboBox.setModel(self.lvvStackComboBox.model())
        self.lvvStackComboBox.currentIndexChanged[int].connect(
            self.gvvStackComboBox.setCurrentIndex
        )
        self.gvvStackComboBox.currentIndexChanged[int].connect(
            self.lvvStackComboBox.setCurrentIndex
        )

        # add the call stack viewer
        self.callStackViewer = CallStackViewer(self.debugServer)
        index = self.__tabWidget.addTab(
            self.callStackViewer, EricPixmapCache.getIcon("callStack"), ""
        )
        self.__tabWidget.setTabToolTip(index, self.tr("Shows the current call stack."))
        self.callStackViewer.sourceFile.connect(self.sourceFile)
        self.callStackViewer.frameSelected.connect(self.__callStackFrameSelected)

        # add the call trace viewer
        self.callTraceViewer = CallTraceViewer(self.debugServer, self)
        index = self.__tabWidget.addTab(
            self.callTraceViewer, EricPixmapCache.getIcon("callTrace"), ""
        )
        self.__tabWidget.setTabToolTip(
            index, self.tr("Shows a trace of the program flow.")
        )
        self.callTraceViewer.sourceFile.connect(self.sourceFile)

        # add the breakpoint viewer
        self.breakpointViewer = BreakPointViewer()
        self.breakpointViewer.setModel(self.debugServer.getBreakPointModel())
        index = self.__tabWidget.addTab(
            self.breakpointViewer, EricPixmapCache.getIcon("breakpoints"), ""
        )
        self.__tabWidget.setTabToolTip(
            index, self.tr("Shows a list of defined breakpoints.")
        )
        self.breakpointViewer.sourceFile.connect(self.sourceFile)

        # add the watch expression viewer
        self.watchpointViewer = WatchPointViewer()
        self.watchpointViewer.setModel(self.debugServer.getWatchPointModel())
        index = self.__tabWidget.addTab(
            self.watchpointViewer, EricPixmapCache.getIcon("watchpoints"), ""
        )
        self.__tabWidget.setTabToolTip(
            index, self.tr("Shows a list of defined watchpoints.")
        )

        # add the exception logger
        self.exceptionLogger = ExceptionLogger()
        index = self.__tabWidget.addTab(
            self.exceptionLogger, EricPixmapCache.getIcon("exceptions"), ""
        )
        self.__tabWidget.setTabToolTip(
            index, self.tr("Shows a list of raised exceptions.")
        )

        # add the Python disassembly viewer
        self.disassemblyViewer = PythonDisViewer(
            None, mode=PythonDisViewerModes.TRACEBACK
        )
        index = self.__tabWidget.addTab(
            self.disassemblyViewer, EricPixmapCache.getIcon("disassembly"), ""
        )
        self.__tabWidget.setTabToolTip(
            index, self.tr("Shows a code disassembly in case of an exception.")
        )

        self.__tabWidget.setCurrentWidget(self.gvvWidget)

        self.__doDebuggersListUpdate = True

        self.__mainSplitter.setSizes([100, 700])

        self.currentStack = None
        self.framenr = 0

        self.__autoViewSource = Preferences.getDebugger("AutoViewSourceCode")
        self.lvvSourceButton.setVisible(not self.__autoViewSource)
        self.gvvSourceButton.setVisible(not self.__autoViewSource)

        # connect some debug server signals
        self.debugServer.clientStack.connect(self.handleClientStack)
        self.debugServer.clientThreadList.connect(self.__addThreadList)
        self.debugServer.clientDebuggerId.connect(self.__clientDebuggerId)
        self.debugServer.passiveDebugStarted.connect(self.handleDebuggingStarted)
        self.debugServer.clientLine.connect(self.__clientLine)
        self.debugServer.clientSyntaxError.connect(self.__clientSyntaxError)
        self.debugServer.clientException.connect(self.__clientException)
        self.debugServer.clientExit.connect(self.__clientExit)
        self.debugServer.clientDisconnected.connect(self.__removeDebugger)

        self.debugServer.clientException.connect(self.exceptionLogger.addException)
        self.debugServer.passiveDebugStarted.connect(
            self.exceptionLogger.debuggingStarted
        )

        self.debugServer.clientLine.connect(self.breakpointViewer.highlightBreakpoint)

    def __clearStackComboBox(self, comboBox):
        """
        Private method to clear the given stack combo box.

        @param comboBox reference to the combo box to be cleared
        @type QComboBox
        """
        block = comboBox.blockSignals(True)
        comboBox.clear()
        comboBox.blockSignals(block)

    def handlePreferencesChanged(self):
        """
        Public slot to handle the preferencesChanged signal.
        """
        self.__autoViewSource = Preferences.getDebugger("AutoViewSourceCode")
        self.lvvSourceButton.setVisible(not self.__autoViewSource)
        self.gvvSourceButton.setVisible(not self.__autoViewSource)

        if not bool(self.globalsFilterEdit.text()):
            self.globalsFilterTypeCombo.setCurrentIndex(
                1 if Preferences.getDebugger("ShowOnlyAsDefault") else 0
            )
        if not bool(self.localsFilterEdit.text()):
            self.localsFilterTypeCombo.setCurrentIndex(
                1 if Preferences.getDebugger("ShowOnlyAsDefault") else 0
            )

    def setDebugger(self, debugUI):
        """
        Public method to set a reference to the Debug UI.

        @param debugUI reference to the DebugUI object
        @type DebugUI
        """
        self.debugUI = debugUI
        self.callStackViewer.setDebugger(debugUI)

        # connect some debugUI signals
        self.debugUI.clientStack.connect(self.handleClientStack)
        self.debugUI.debuggingStarted.connect(self.exceptionLogger.debuggingStarted)
        self.debugUI.debuggingStarted.connect(self.handleDebuggingStarted)

    def handleResetUI(self, fullReset):
        """
        Public method to reset the viewer.

        @param fullReset flag indicating a full reset is required
        @type bool
        """
        self.globalsViewer.handleResetUI()
        self.localsViewer.handleResetUI()
        self.setGlobalsFilter()
        self.setLocalsFilter()
        self.lvvSourceButton.setEnabled(False)
        self.gvvSourceButton.setEnabled(False)
        self.currentStack = None
        self.__clearStackComboBox(self.lvvStackComboBox)
        self.__tabWidget.setCurrentWidget(self.gvvWidget)
        self.breakpointViewer.handleResetUI()
        if fullReset:
            self.__debuggersList.clear()
        self.disassemblyViewer.clear()

    def initCallStackViewer(self, projectMode):
        """
        Public method to initialize the call stack viewer.

        @param projectMode flag indicating to enable the project mode
        @type bool
        """
        self.callStackViewer.clear()
        self.callStackViewer.setProjectMode(projectMode)

    def isCallTraceEnabled(self):
        """
        Public method to get the state of the call trace function.

        @return flag indicating the state of the call trace function
        @rtype bool
        """
        return self.callTraceViewer.isCallTraceEnabled()

    def clearCallTrace(self):
        """
        Public method to clear the recorded call trace.
        """
        self.callTraceViewer.clear()

    def setCallTraceToProjectMode(self, enabled):
        """
        Public slot to set the call trace viewer to project mode.

        In project mode the call trace info is shown with project relative
        path names.

        @param enabled flag indicating to enable the project mode
        @type bool
        """
        self.callTraceViewer.setProjectMode(enabled)

    def showVariables(self, vlist, showGlobals):
        """
        Public method to show the variables in the respective window.

        @param vlist list of variables to display
        @type list
        @param showGlobals flag indicating global/local state
        @type bool
        """
        if showGlobals:
            self.globalsViewer.showVariables(vlist, self.framenr)
        else:
            self.localsViewer.showVariables(vlist, self.framenr)

        if self.__setFocusToWidget is not None:
            self.__setFocusToWidget.setFocus(Qt.FocusReason.MouseFocusReason)
            self.__setFocusToWidget = None  # reset it

    def showVariable(self, vlist, showGlobals):
        """
        Public method to show the variables in the respective window.

        @param vlist list of variables to display
        @type list
        @param showGlobals flag indicating global/local state
        @type bool
        """
        if showGlobals:
            self.globalsViewer.showVariable(vlist)
        else:
            self.localsViewer.showVariable(vlist)

    def showVariablesTab(self, showGlobals):
        """
        Public method to make a variables tab visible.

        @param showGlobals flag indicating global/local state
        @type bool
        """
        if showGlobals:
            self.__tabWidget.setCurrentWidget(self.gvvWidget)
        else:
            self.__tabWidget.setCurrentWidget(self.lvvWidget)

    def handleClientStack(self, stack, debuggerId):
        """
        Public slot to show the call stack of the program being debugged.

        @param stack list of tuples with call stack data (file name,
            line number, function name, formatted argument/values list)
        @type list of tuples of (str, str, str, str)
        @param debuggerId ID of the debugger backend
        @type str
        """
        if debuggerId == self.getSelectedDebuggerId():
            self.framenr = 0
            self.lvvSourceButton.setEnabled(len(stack) > 0)
            self.gvvSourceButton.setEnabled(len(stack) > 0)
            self.currentStack = stack

            block = self.lvvStackComboBox.blockSignals(True)
            self.lvvStackComboBox.clear()
            for s in stack:
                # just show base filename to make it readable
                s = (os.path.basename(s[0]), s[1], s[2])
                self.lvvStackComboBox.addItem("{0}:{1}:{2}".format(*s))
            self.lvvStackComboBox.blockSignals(block)

    def __clientLine(self, _fn, _line, debuggerId, threadName):
        """
        Private method to handle a change to the current line.

        @param _fn filename (unused)
        @type str
        @param _line linenumber (unused)
        @type int
        @param debuggerId ID of the debugger backend
        @type str
        @param threadName name of the thread signaling the event
        @type str
        """
        self.__setDebuggerIconAndState(debuggerId, "broken")
        self.__setThreadIconAndState(debuggerId, threadName, "broken")
        if debuggerId != self.getSelectedDebuggerId():
            self.__setCurrentDebugger(debuggerId)

    @pyqtSlot(str, int, str, bool, str)
    def __clientExit(self, _program, _status, _message, _quiet, debuggerId):
        """
        Private method to handle the debugged program terminating.

        @param _program name of the exited program (unused)
        @type str
        @param _status exit code of the debugged program (unused)
        @type int
        @param _message exit message of the debugged program (unused)
        @type str
        @param _quiet flag indicating to suppress exit info display (unused)
        @type bool
        @param debuggerId ID of the debugger backend
        @type str
        """
        if not self.isOnlyDebugger():
            if debuggerId == self.getSelectedDebuggerId():
                # the current client has exited
                self.globalsViewer.handleResetUI()
                self.localsViewer.handleResetUI()
                self.setGlobalsFilter()
                self.setLocalsFilter()
                self.lvvSourceButton.setEnabled(False)
                self.gvvSourceButton.setEnabled(False)
                self.currentStack = None
                self.__clearStackComboBox(self.lvvStackComboBox)

            self.__removeDebugger(debuggerId)

    def __clientSyntaxError(
        self,
        _message,
        _filename,
        _lineNo,
        _characterNo,
        debuggerId,
        threadName,
    ):
        """
        Private method to handle a syntax error in the debugged program.

        @param _message message of the syntax error (unused)
        @type str
        @param _filename translated filename of the syntax error position (unused)
        @type str
        @param _lineNo line number of the syntax error position (unused)
        @type int
        @param _characterNo character number of the syntax error position (unused)
        @type int
        @param debuggerId ID of the debugger backend
        @type str
        @param threadName name of the thread signaling the event
        @type str
        """
        self.__setDebuggerIconAndState(debuggerId, "syntax")
        self.__setThreadIconAndState(debuggerId, threadName, "syntax")

    def __clientException(
        self,
        _exceptionType,
        _exceptionMessage,
        _stackTrace,
        debuggerId,
        threadName,
    ):
        """
        Private method to handle an exception of the debugged program.

        @param _exceptionType type of exception raised (unused)
        @type str
        @param _exceptionMessage message given by the exception (unused)
        @type (str
        @param _stackTrace list of stack entries (unused)
        @type list of str
        @param debuggerId ID of the debugger backend
        @type str
        @param threadName name of the thread signaling the event
        @type str
        """
        self.__setDebuggerIconAndState(debuggerId, "exception")
        self.__setThreadIconAndState(debuggerId, threadName, "exception")

    def setVariablesFilter(self, globalsFilter, localsFilter):
        """
        Public slot to set the local variables filter.

        @param globalsFilter filter list for global variable types
        @type list of str
        @param localsFilter filter list for local variable types
        @type list of str
        """
        self.__globalsFilter = globalsFilter
        self.__localsFilter = localsFilter

    def __showSource(self):
        """
        Private slot to handle the source button press to show the selected
        file.
        """
        index = self.lvvStackComboBox.currentIndex()
        if index > -1 and self.currentStack:
            s = self.currentStack[index]
            self.sourceFile.emit(s[0], int(s[1]))

    def __frameSelected(self, frmnr):
        """
        Private slot to handle the selection of a new stack frame number.

        @param frmnr frame number (0 is the current frame)
        @type int
        """
        if frmnr >= 0:
            self.framenr = frmnr
            if self.debugServer.isDebugging():
                self.debugServer.remoteClientVariables(
                    self.getSelectedDebuggerId(), 1, self.__globalsFilter, frmnr
                )
                self.debugServer.remoteClientVariables(
                    self.getSelectedDebuggerId(), 0, self.__localsFilter, frmnr
                )

            if self.__autoViewSource:
                self.__showSource()

    def setGlobalsFilter(self):
        """
        Public slot to set the global variable filter.
        """
        if self.debugServer.isDebugging():
            filterStr = self.globalsFilterEdit.text()
            if self.globalsFilterTypeCombo.currentIndex() == 0:
                filterStr = "~ {0}".format(filterStr)
            self.globalsViewer.clear()
            self.debugServer.remoteClientSetFilter(
                self.getSelectedDebuggerId(), 1, filterStr
            )
            self.debugServer.remoteClientVariables(
                self.getSelectedDebuggerId(), 1, self.__globalsFilter
            )

    def setLocalsFilter(self):
        """
        Public slot to set the local variable filter.
        """
        if self.debugServer.isDebugging():
            filterStr = self.localsFilterEdit.text()
            if self.localsFilterTypeCombo.currentIndex() == 0:
                filterStr = "~ {0}".format(filterStr)
            self.localsViewer.clear()
            self.debugServer.remoteClientSetFilter(
                self.getSelectedDebuggerId(), 0, filterStr
            )
            if self.currentStack:
                self.debugServer.remoteClientVariables(
                    self.getSelectedDebuggerId(), 0, self.__localsFilter, self.framenr
                )

    def __filterStringEdited(self, globalsFilter):
        """
        Private method to handle the editing of the a variables filter.

        @param globalsFilter flag indicating the globals filter was edited
        @type bool
        """
        if globalsFilter:
            self.__setFocusToWidget = self.globalsFilterEdit
            self.setGlobalsFilter()
        else:
            self.__setFocusToWidget = self.localsFilterEdit
            self.setLocalsFilter()

    def refreshVariablesLists(self):
        """
        Public slot to refresh the local and global variables lists.
        """
        if self.debugServer.isDebugging():
            self.debugServer.remoteClientVariables(
                self.getSelectedDebuggerId(), 1, self.__globalsFilter
            )
            if self.currentStack:
                self.debugServer.remoteClientVariables(
                    self.getSelectedDebuggerId(), 0, self.__localsFilter, self.framenr
                )

    def handleDebuggingStarted(self):
        """
        Public slot to handle the start of a debugging session.

        This slot sets the variables filter expressions.
        """
        self.setGlobalsFilter()
        self.setLocalsFilter()
        self.showVariablesTab(False)

        self.disassemblyViewer.clear()

    def currentWidget(self):
        """
        Public method to get a reference to the current widget.

        @return reference to the current widget
        @rtype QWidget
        """
        return self.__tabWidget.currentWidget()

    def setCurrentWidget(self, widget):
        """
        Public slot to set the current page based on the given widget.

        @param widget reference to the widget
        @type QWidget
        """
        self.__tabWidget.setCurrentWidget(widget)

    def __callStackFrameSelected(self, frameNo):
        """
        Private slot to handle the selection of a call stack entry of the
        call stack viewer.

        @param frameNo frame number (index) of the selected entry
        @type int
        """
        if frameNo >= 0:
            self.lvvStackComboBox.setCurrentIndex(frameNo)

    def __debuggerSelected(self, current, _previous):
        """
        Private slot to handle the selection of a debugger backend in the
        debuggers list.

        @param current reference to the new current item
        @type QTreeWidgetItem
        @param _previous reference to the previous current item (unused)
        @type QTreeWidgetItem
        """
        if current is not None and self.__doDebuggersListUpdate:
            if current.parent() is None:
                # it is a debugger item
                debuggerId = current.text(0)
                self.globalsViewer.handleResetUI()
                self.localsViewer.handleResetUI()
                self.currentStack = None
                self.__clearStackComboBox(self.lvvStackComboBox)
                self.callStackViewer.clear()

                self.debugServer.remoteSetThread(debuggerId, -1)
                self.__showSource()
            else:
                # it is a thread item
                tid = current.data(0, self.ThreadIdRole)
                self.debugServer.remoteSetThread(self.getSelectedDebuggerId(), tid)

    def __clientDebuggerId(self, debuggerId):
        """
        Private slot to receive the ID of a newly connected debugger backend.

        @param debuggerId ID of a newly connected debugger backend
        @type str
        """
        itm = QTreeWidgetItem(self.__debuggersList, [debuggerId])
        if self.__debuggersList.topLevelItemCount() > 1:
            self.debugUI.showNotification(
                self.tr(
                    "<p>Debugger with ID <b>{0}</b> has been connected.</p>"
                ).format(debuggerId)
            )

        self.__debuggersList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )

        if self.__debuggersList.topLevelItemCount() == 1:
            # it is the only item, select it as the current one
            self.__debuggersList.setCurrentItem(itm)

    def __setCurrentDebugger(self, debuggerId):
        """
        Private method to set the current debugger based on the given ID.

        @param debuggerId ID of the debugger to set as current debugger
        @type str
        """
        debuggerItems = self.__debuggersList.findItems(
            debuggerId, Qt.MatchFlag.MatchExactly
        )
        if debuggerItems:
            debuggerItem = debuggerItems[0]
            currentItem = self.__debuggersList.currentItem()
            if currentItem is debuggerItem:
                # nothing to do
                return

            if currentItem:
                currentParent = currentItem.parent()
            else:
                currentParent = None
            if currentParent is None:
                # current is a debugger item
                self.__debuggersList.setCurrentItem(debuggerItem)
            elif currentParent is debuggerItem:
                # nothing to do
                return
            else:
                self.__debuggersList.setCurrentItem(debuggerItem)

    def isOnlyDebugger(self):
        """
        Public method to test, if only one debugger is connected.

        @return flag indicating that only one debugger is connected
        @rtype bool
        """
        return self.__debuggersList.topLevelItemCount() == 1

    def getSelectedDebuggerId(self):
        """
        Public method to get the currently selected debugger ID.

        @return selected debugger ID
        @rtype str
        """
        itm = self.__debuggersList.currentItem()
        if itm:
            if itm.parent() is None:
                # it is a debugger item
                return itm.text(0)
            else:
                # it is a thread item
                return itm.parent().text(0)
        else:
            return ""

    def getSelectedDebuggerState(self):
        """
        Public method to get the currently selected debugger's state.

        @return selected debugger's state (broken, exception, running)
        @rtype str
        """
        itm = self.__debuggersList.currentItem()
        if itm:
            if itm.parent() is None:
                # it is a debugger item
                return itm.data(0, self.DebuggerStateRole)
            else:
                # it is a thread item
                return itm.parent().data(0, self.DebuggerStateRole)
        else:
            return ""

    def __setDebuggerIconAndState(self, debuggerId, state):
        """
        Private method to set the icon for a specific debugger ID.

        @param debuggerId ID of the debugger backend (empty ID means the
            currently selected one)
        @type str
        @param state state of the debugger (broken, exception, running)
        @type str
        """
        debuggerItem = None
        if debuggerId:
            foundItems = self.__debuggersList.findItems(
                debuggerId, Qt.MatchFlag.MatchExactly
            )
            if foundItems:
                debuggerItem = foundItems[0]
        if debuggerItem is None:
            debuggerItem = self.__debuggersList.currentItem()
        if debuggerItem is not None:
            try:
                iconName = DebugViewer.StateIcon[state]
            except KeyError:
                iconName = "question"
            try:
                stateText = DebugViewer.StateMessage[state]
            except KeyError:
                stateText = self.tr("unknown state ({0})").format(state)
            debuggerItem.setIcon(0, EricPixmapCache.getIcon(iconName))
            debuggerItem.setData(0, self.DebuggerStateRole, state)
            debuggerItem.setText(1, stateText)

            self.__debuggersList.header().resizeSections(
                QHeaderView.ResizeMode.ResizeToContents
            )

    def __removeDebugger(self, debuggerId):
        """
        Private method to remove a debugger given its ID.

        @param debuggerId ID of the debugger to be removed from the list
        @type str
        """
        foundItems = self.__debuggersList.findItems(
            debuggerId, Qt.MatchFlag.MatchExactly
        )
        if foundItems:
            index = self.__debuggersList.indexOfTopLevelItem(foundItems[0])
            itm = self.__debuggersList.takeTopLevelItem(index)
            # __IGNORE_WARNING__
            del itm

    def __addThreadList(self, currentID, threadList, debuggerId):
        """
        Private method to add the list of threads to a debugger entry.

        @param currentID id of the current thread
        @type int
        @param threadList list of dictionaries containing the thread data
        @type list of dict
        @param debuggerId ID of the debugger backend
        @type str
        """
        debugStatus = -1  # i.e. running

        debuggerItems = self.__debuggersList.findItems(
            debuggerId, Qt.MatchFlag.MatchExactly
        )
        if debuggerItems:
            debuggerItem = debuggerItems[0]

            currentItem = self.__debuggersList.currentItem()
            if currentItem is not None and currentItem.parent() is debuggerItem:
                currentChild = currentItem.text(0)
            else:
                currentChild = ""
            self.__doDebuggersListUpdate = False
            debuggerItem.takeChildren()
            for thread in threadList:
                if thread.get("except", False):
                    stateText = DebugViewer.StateMessage["exception"]
                    iconName = DebugViewer.StateIcon["exception"]
                    debugStatus = 1
                elif thread["broken"]:
                    stateText = DebugViewer.StateMessage["broken"]
                    iconName = DebugViewer.StateIcon["broken"]
                    if debugStatus < 1:
                        debugStatus = 0
                else:
                    stateText = DebugViewer.StateMessage["running"]
                    iconName = DebugViewer.StateIcon["running"]
                itm = QTreeWidgetItem(debuggerItem, [thread["name"], stateText])
                itm.setData(0, self.ThreadIdRole, thread["id"])
                itm.setIcon(0, EricPixmapCache.getIcon(iconName))
                if currentChild == thread["name"]:
                    self.__debuggersList.setCurrentItem(itm)
                if thread["id"] == currentID:
                    font = debuggerItem.font(0)
                    font.setItalic(True)
                    itm.setFont(0, font)

            debuggerItem.setExpanded(debuggerItem.childCount() > 0)

            self.__debuggersList.header().resizeSections(
                QHeaderView.ResizeMode.ResizeToContents
            )
            self.__debuggersList.header().setStretchLastSection(True)
            self.__doDebuggersListUpdate = True

            if debugStatus == -1:
                debuggerState = "running"
            elif debugStatus == 0:
                debuggerState = "broken"
            else:
                debuggerState = "exception"
            self.__setDebuggerIconAndState(debuggerId, debuggerState)

    def __setThreadIconAndState(self, debuggerId, threadName, state):
        """
        Private method to set the icon for a specific thread name and
        debugger ID.

        @param debuggerId ID of the debugger backend (empty ID means the
            currently selected one)
        @type str
        @param threadName name of the thread signaling the event
        @type str
        @param state state of the debugger (broken, exception, running)
        @type str
        """
        debuggerItem = None
        if debuggerId:
            foundItems = self.__debuggersList.findItems(
                debuggerId, Qt.MatchFlag.MatchExactly
            )
            if foundItems:
                debuggerItem = foundItems[0]
        if debuggerItem is None:
            debuggerItem = self.__debuggersList.currentItem()
        if debuggerItem is not None:
            for index in range(debuggerItem.childCount()):
                childItem = debuggerItem.child(index)
                if childItem.text(0) == threadName:
                    break
            else:
                childItem = None

            if childItem is not None:
                try:
                    iconName = DebugViewer.StateIcon[state]
                except KeyError:
                    iconName = "question"
                try:
                    stateText = DebugViewer.StateMessage[state]
                except KeyError:
                    stateText = self.tr("unknown state ({0})").format(state)
                childItem.setIcon(0, EricPixmapCache.getIcon(iconName))
                childItem.setText(1, stateText)

            self.__debuggersList.header().resizeSections(
                QHeaderView.ResizeMode.ResizeToContents
            )
