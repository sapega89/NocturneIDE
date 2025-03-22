# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the debugger UI.
"""

import contextlib
import copy
import os
import shlex

from PyQt6.QtCore import QKeyCombination, QObject, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QKeySequence
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QToolBar

from eric7 import EricUtilities, Preferences, Utilities
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction, createActionGroup
from eric7.EricWidgets import EricMessageBox
from eric7.Globals import recentNameBreakpointConditions
from eric7.SystemUtilities import FileSystemUtilities
from eric7.UI.Info import Program
from eric7.UI.NotificationWidget import NotificationTypes

from .DebugClientCapabilities import (
    HasCoverage,
    HasDebugger,
    HasInterpreter,
    HasProfiler,
)


class DebugUI(QObject):
    """
    Class implementing the debugger part of the UI.

    @signal clientStack(stack, debuggerId) emitted at breaking after a reported
        exception
    @signal debuggingStarted(filename) emitted when a debugging session was
        started
    @signal debuggingFinished emitted to signal the end of a debugging session
    @signal resetUI(full) emitted to reset the UI partially or fully
    @signal exceptionInterrupt() emitted after the execution was interrupted
        by an exception and acknowledged by the user
    @signal processChangedProjectFiles() emitted to indicate, that changed project files
        should be processed
    """

    clientStack = pyqtSignal(list, str)
    resetUI = pyqtSignal(bool)
    exceptionInterrupt = pyqtSignal()
    debuggingStarted = pyqtSignal(str)
    debuggingFinished = pyqtSignal()
    processChangedProjectFiles = pyqtSignal()

    def __init__(self, ui, vm, debugServer, debugViewer, project):
        """
        Constructor

        @param ui reference to the main UI
        @type UserInterface
        @param vm reference to the viewmanager
        @type ViewManager
        @param debugServer reference to the debug server
        @type DebugServer
        @param debugViewer reference to the debug viewer widget
        @type DebugViewer
        @param project reference to the project object
        @type Project
        """
        super().__init__(ui)

        self.ui = ui
        self.viewmanager = vm
        self.debugServer = debugServer
        self.debugViewer = debugViewer
        self.project = project

        # Clear some variables
        self.projectOpen = False
        self.editorOpen = False

        # read the saved debug info values
        self.lastUsedVenvName = Preferences.getSettings().value(
            "DebugInfo/VirtualEnvironment", ""
        )
        self.scriptsHistory = EricUtilities.toList(
            Preferences.getSettings().value("DebugInfo/ScriptsHistory")
        )
        self.argvHistory = EricUtilities.toList(
            Preferences.getSettings().value("DebugInfo/ArgumentsHistory")
        )
        self.wdHistory = EricUtilities.toList(
            Preferences.getSettings().value("DebugInfo/WorkingDirectoryHistory")
        )
        self.envHistory = EricUtilities.toList(
            Preferences.getSettings().value("DebugInfo/EnvironmentHistory")
        )
        self.excList = EricUtilities.toList(
            Preferences.getSettings().value("DebugInfo/Exceptions")
        )
        self.excIgnoreList = EricUtilities.toList(
            Preferences.getSettings().value("DebugInfo/IgnoredExceptions")
        )
        self.autoClearShell = EricUtilities.toBool(
            Preferences.getSettings().value("DebugInfo/AutoClearShell", True)
        )
        self.tracePython = EricUtilities.toBool(
            Preferences.getSettings().value("DebugInfo/TracePython", False)
        )
        self.autoContinue = EricUtilities.toBool(
            Preferences.getSettings().value("DebugInfo/AutoContinue", True)
        )
        self.reportAllExceptions = EricUtilities.toBool(
            Preferences.getSettings().value("DebugInfo/ReportAllExceptions", False)
        )
        self.enableMultiprocess = EricUtilities.toBool(
            Preferences.getSettings().value("DebugInfo/EnableMultiprocess", False)
        )
        self.multiprocessNoDebugHistory = EricUtilities.toList(
            Preferences.getSettings().value("DebugInfo/MultiprocessNoDebugHistory")
        )
        self.overrideGlobalConfig = {
            "enable": EricUtilities.toBool(
                Preferences.getSettings().value("DebugInfo/OverrideGlobal", False)
            ),
            "redirect": EricUtilities.toBool(
                Preferences.getSettings().value("DebugInfo/RedirectStdinStdout", True)
            ),
        }

        self.lastDebuggedFile = None
        self.lastStartAction = 0  # 0=None, 1=Script, 2=Project
        self.clientType = ""
        self.lastAction = -1
        self.debugActions = [
            self.__continue,
            self.__step,
            self.__stepOver,
            self.__stepOut,
            self.__stepQuit,
            self.__runToCursor,
            self.__runUntil,
            self.__moveInstructionPointer,
        ]
        (
            self.__localsVarFilterList,
            self.__globalsVarFilterList,
        ) = Preferences.getVarFilters()
        self.debugViewer.setVariablesFilter(
            self.__globalsVarFilterList, self.__localsVarFilterList
        )

        self.__clientDebuggerIds = set()

        # Connect the signals emitted by the debug-server
        debugServer.clientGone.connect(self.__clientGone)
        debugServer.clientLine.connect(self.__clientLine)
        debugServer.clientDisconnected.connect(self.__clientDisconnected)
        debugServer.clientExit.connect(self.__clientExit)
        debugServer.mainClientExit.connect(self.__mainClientExit)
        debugServer.clientSyntaxError.connect(self.__clientSyntaxError)
        debugServer.clientException.connect(self.__clientException)
        debugServer.clientSignal.connect(self.__clientSignal)
        debugServer.clientVariables.connect(self.__clientVariables)
        debugServer.clientVariable.connect(self.__clientVariable)
        debugServer.clientBreakConditionError.connect(self.__clientBreakConditionError)
        debugServer.clientWatchConditionError.connect(self.__clientWatchConditionError)
        debugServer.passiveDebugStarted.connect(self.__passiveDebugStarted)
        debugServer.clientThreadSet.connect(self.__clientThreadSet)
        debugServer.clientDebuggerId.connect(self.__clientDebuggerId)

        # Connect the signals emitted by the viewmanager
        vm.editorOpened.connect(self.__editorOpened)
        vm.lastEditorClosed.connect(self.__lastEditorClosed)
        vm.checkActions.connect(self.__checkActions)
        vm.cursorChanged.connect(self.__cursorChanged)
        vm.breakpointToggled.connect(self.__cursorChanged)

        # Connect the signals emitted by the project
        project.projectOpened.connect(self.__projectOpened)
        project.newProject.connect(self.__projectOpened)
        project.projectClosed.connect(self.__projectClosed)

        # Set a flag for the passive debug mode
        self.passive = Preferences.getDebugger("PassiveDbgEnabled")

    def showNotification(
        self, notification, kind=NotificationTypes.INFORMATION, timeout=None
    ):
        """
        Public method to show some notification message.

        @param notification message to be shown
        @type str
        @param kind kind of notification to be shown
        @type NotificationTypes
        @param timeout timeout for the notification (None = use configured
            default, 0 = indefinitely)
        @type int
        """
        self.ui.showNotification(
            EricPixmapCache.getPixmap("debug48"),
            self.tr("Notification"),
            notification,
            kind=kind,
            timeout=timeout,
        )

    def variablesFilter(self, scope):
        """
        Public method to get the variables filter for a scope.

        @param scope flag indicating global (True) or local (False) scope
        @type bool
        @return filters list
        @rtype list of str
        """
        if scope:
            return self.__globalsVarFilterList[:]
        else:
            return self.__localsVarFilterList[:]

    def initActions(self):
        """
        Public method defining the user interface actions.
        """
        self.actions = []

        self.runAct = EricAction(
            self.tr("Run Script"),
            EricPixmapCache.getIcon("runScript"),
            self.tr("&Run Script..."),
            Qt.Key.Key_F2,
            0,
            self,
            "dbg_run_script",
        )
        self.runAct.setStatusTip(self.tr("Run the current Script"))
        self.runAct.setWhatsThis(
            self.tr(
                """<b>Run Script</b>"""
                """<p>Set the command line arguments and run the script outside"""
                """ the debugger. If the file has unsaved changes it may be"""
                """ saved first.</p>"""
            )
        )
        self.runAct.triggered.connect(self.__runScript)
        self.actions.append(self.runAct)

        self.runProjectAct = EricAction(
            self.tr("Run Project"),
            EricPixmapCache.getIcon("runProject"),
            self.tr("Run &Project..."),
            QKeyCombination(Qt.Modifier.SHIFT, Qt.Key.Key_F2),
            0,
            self,
            "dbg_run_project",
        )
        self.runProjectAct.setStatusTip(self.tr("Run the current Project"))
        self.runProjectAct.setWhatsThis(
            self.tr(
                """<b>Run Project</b>"""
                """<p>Set the command line arguments and run the current project"""
                """ outside the debugger."""
                """ If files of the current project have unsaved changes they"""
                """ may be saved first.</p>"""
            )
        )
        self.runProjectAct.triggered.connect(self.__runProject)
        self.actions.append(self.runProjectAct)

        self.coverageAct = EricAction(
            self.tr("Coverage run of Script"),
            EricPixmapCache.getIcon("coverageScript"),
            self.tr("Coverage run of Script..."),
            0,
            0,
            self,
            "dbg_coverage_script",
        )
        self.coverageAct.setStatusTip(
            self.tr("Perform a coverage run of the current Script")
        )
        self.coverageAct.setWhatsThis(
            self.tr(
                """<b>Coverage run of Script</b>"""
                """<p>Set the command line arguments and run the script under"""
                """ the control of a coverage analysis tool. If the file has"""
                """ unsaved changes it may be saved first.</p>"""
            )
        )
        self.coverageAct.triggered.connect(self.__coverageScript)
        self.actions.append(self.coverageAct)

        self.coverageProjectAct = EricAction(
            self.tr("Coverage run of Project"),
            EricPixmapCache.getIcon("coverageProject"),
            self.tr("Coverage run of Project..."),
            0,
            0,
            self,
            "dbg_coverage_project",
        )
        self.coverageProjectAct.setStatusTip(
            self.tr("Perform a coverage run of the current Project")
        )
        self.coverageProjectAct.setWhatsThis(
            self.tr(
                """<b>Coverage run of Project</b>"""
                """<p>Set the command line arguments and run the current project"""
                """ under the control of a coverage analysis tool."""
                """ If files of the current project have unsaved changes"""
                """ they may be saved first.</p>"""
            )
        )
        self.coverageProjectAct.triggered.connect(self.__coverageProject)
        self.actions.append(self.coverageProjectAct)

        self.profileAct = EricAction(
            self.tr("Profile Script"),
            EricPixmapCache.getIcon("profileScript"),
            self.tr("Profile Script..."),
            0,
            0,
            self,
            "dbg_profile_script",
        )
        self.profileAct.setStatusTip(self.tr("Profile the current Script"))
        self.profileAct.setWhatsThis(
            self.tr(
                """<b>Profile Script</b>"""
                """<p>Set the command line arguments and profile the script."""
                """ If the file has unsaved changes it may be saved first.</p>"""
            )
        )
        self.profileAct.triggered.connect(self.__profileScript)
        self.actions.append(self.profileAct)

        self.profileProjectAct = EricAction(
            self.tr("Profile Project"),
            EricPixmapCache.getIcon("profileProject"),
            self.tr("Profile Project..."),
            0,
            0,
            self,
            "dbg_profile_project",
        )
        self.profileProjectAct.setStatusTip(self.tr("Profile the current Project"))
        self.profileProjectAct.setWhatsThis(
            self.tr(
                """<b>Profile Project</b>"""
                """<p>Set the command line arguments and profile the current"""
                """ project. If files of the current project have unsaved"""
                """ changes they may be saved first.</p>"""
            )
        )
        self.profileProjectAct.triggered.connect(self.__profileProject)
        self.actions.append(self.profileProjectAct)

        self.debugAct = EricAction(
            self.tr("Debug Script"),
            EricPixmapCache.getIcon("debugScript"),
            self.tr("&Debug Script..."),
            Qt.Key.Key_F5,
            0,
            self,
            "dbg_debug_script",
        )
        self.debugAct.setStatusTip(self.tr("Debug the current Script"))
        self.debugAct.setWhatsThis(
            self.tr(
                """<b>Debug Script</b>"""
                """<p>Set the command line arguments and set the current line"""
                """ to be the first executable Python statement of the current"""
                """ editor window. If the file has unsaved changes it may be"""
                """ saved first.</p>"""
            )
        )
        self.debugAct.triggered.connect(self.__debugScript)
        self.actions.append(self.debugAct)

        self.debugProjectAct = EricAction(
            self.tr("Debug Project"),
            EricPixmapCache.getIcon("debugProject"),
            self.tr("Debug &Project..."),
            QKeyCombination(Qt.Modifier.SHIFT, Qt.Key.Key_F5),
            0,
            self,
            "dbg_debug_project",
        )
        self.debugProjectAct.setStatusTip(self.tr("Debug the current Project"))
        self.debugProjectAct.setWhatsThis(
            self.tr(
                """<b>Debug Project</b>"""
                """<p>Set the command line arguments and set the current line"""
                """ to be the first executable Python statement of the main"""
                """ script of the current project. If files of the current"""
                """ project have unsaved changes they may be saved first.</p>"""
            )
        )
        self.debugProjectAct.triggered.connect(self.__debugProject)
        self.actions.append(self.debugProjectAct)

        self.restartAct = EricAction(
            self.tr("Restart"),
            EricPixmapCache.getIcon("debugRestart"),
            self.tr("Restart"),
            Qt.Key.Key_F4,
            0,
            self,
            "dbg_restart_script",
        )
        self.restartAct.setStatusTip(self.tr("Restart the last debugged script"))
        self.restartAct.setWhatsThis(
            self.tr(
                """<b>Restart</b>"""
                """<p>Set the command line arguments and set the current line"""
                """ to be the first executable Python statement of the script"""
                """ that was debugged last. If there are unsaved changes, they"""
                """ may be saved first.</p>"""
            )
        )
        self.restartAct.triggered.connect(self.__doRestart)
        self.actions.append(self.restartAct)

        self.stopAct = EricAction(
            self.tr("Stop"),
            EricPixmapCache.getIcon("stopScript"),
            self.tr("Stop"),
            QKeyCombination(Qt.Modifier.SHIFT, Qt.Key.Key_F10),
            0,
            self,
            "dbg_stop_script",
        )
        self.stopAct.setStatusTip(self.tr("""Stop the running script."""))
        self.stopAct.setWhatsThis(
            self.tr(
                """<b>Stop</b>"""
                """<p>This stops the script running in the debugger backend.</p>"""
            )
        )
        self.stopAct.triggered.connect(self.__stopScript)
        self.actions.append(self.stopAct)

        self.debugActGrp = createActionGroup(self)

        act = EricAction(
            self.tr("Continue"),
            EricPixmapCache.getIcon("continue"),
            self.tr("&Continue"),
            Qt.Key.Key_F6,
            0,
            self.debugActGrp,
            "dbg_continue",
        )
        act.setStatusTip(self.tr("Continue running the program from the current line"))
        act.setWhatsThis(
            self.tr(
                """<b>Continue</b>"""
                """<p>Continue running the program from the current line. The"""
                """ program will stop when it terminates or when a breakpoint"""
                """ is reached.</p>"""
            )
        )
        act.triggered.connect(self.__continue)
        self.actions.append(act)

        act = EricAction(
            self.tr("Continue to Cursor"),
            EricPixmapCache.getIcon("continueToCursor"),
            self.tr("Continue &To Cursor"),
            QKeyCombination(Qt.Modifier.SHIFT, Qt.Key.Key_F6),
            0,
            self.debugActGrp,
            "dbg_continue_to_cursor",
        )
        act.setStatusTip(
            self.tr(
                """Continue running the program from the"""
                """ current line to the current cursor position"""
            )
        )
        act.setWhatsThis(
            self.tr(
                """<b>Continue To Cursor</b>"""
                """<p>Continue running the program from the current line to the"""
                """ current cursor position.</p>"""
            )
        )
        act.triggered.connect(self.__runToCursor)
        self.actions.append(act)

        act = EricAction(
            self.tr("Continue Until"),
            EricPixmapCache.getIcon("continueUntil"),
            self.tr("Continue &Until"),
            QKeyCombination(Qt.Modifier.CTRL, Qt.Key.Key_F6),
            0,
            self.debugActGrp,
            "dbg_continue_until",
        )
        act.setStatusTip(
            self.tr(
                """Continue running the program from the current line to the"""
                """ current cursor position or until leaving the current frame"""
            )
        )
        act.setWhatsThis(
            self.tr(
                """<b>Continue Until</b>"""
                """<p>Continue running the program from the current line to the"""
                """ cursor position greater than the current line or until"""
                """ leaving the current frame.</p>"""
            )
        )
        act.triggered.connect(self.__runUntil)
        self.actions.append(act)

        act = EricAction(
            self.tr("Move Instruction Pointer to Cursor"),
            EricPixmapCache.getIcon("moveInstructionPointer"),
            self.tr("&Jump To Cursor"),
            Qt.Key.Key_F12,
            0,
            self.debugActGrp,
            "dbg_jump_to_cursor",
        )
        act.setStatusTip(
            self.tr(
                """Skip the code from the"""
                """ current line to the current cursor position"""
            )
        )
        act.setWhatsThis(
            self.tr(
                """<b>Move Instruction Pointer to Cursor</b>"""
                """<p>Move the Python internal instruction pointer to the"""
                """ current cursor position without executing the code in"""
                """ between.</p>"""
                """<p>It's not possible to jump out of a function or jump"""
                """ in a code block, e.g. a loop. In these cases, a error"""
                """ message is printed to the log window.</p>"""
            )
        )
        act.triggered.connect(self.__moveInstructionPointer)
        self.actions.append(act)

        act = EricAction(
            self.tr("Single Step"),
            EricPixmapCache.getIcon("step"),
            self.tr("Sin&gle Step"),
            Qt.Key.Key_F7,
            0,
            self.debugActGrp,
            "dbg_single_step",
        )
        act.setStatusTip(self.tr("Execute a single Python statement"))
        act.setWhatsThis(
            self.tr(
                """<b>Single Step</b>"""
                """<p>Execute a single Python statement. If the statement"""
                """ is an <tt>import</tt> statement, a class constructor, or a"""
                """ method or function call then control is returned to the"""
                """ debugger at the next statement.</p>"""
            )
        )
        act.triggered.connect(self.__step)
        self.actions.append(act)

        act = EricAction(
            self.tr("Step Over"),
            EricPixmapCache.getIcon("stepOver"),
            self.tr("Step &Over"),
            Qt.Key.Key_F8,
            0,
            self.debugActGrp,
            "dbg_step_over",
        )
        act.setStatusTip(
            self.tr(
                """Execute a single Python statement staying"""
                """ in the current frame"""
            )
        )
        act.setWhatsThis(
            self.tr(
                """<b>Step Over</b>"""
                """<p>Execute a single Python statement staying in the same"""
                """ frame. If the statement is an <tt>import</tt> statement,"""
                """ a class constructor, or a method or function call then"""
                """ control is returned to the debugger after the statement"""
                """ has completed.</p>"""
            )
        )
        act.triggered.connect(self.__stepOver)
        self.actions.append(act)

        act = EricAction(
            self.tr("Step Out"),
            EricPixmapCache.getIcon("stepOut"),
            self.tr("Step Ou&t"),
            Qt.Key.Key_F9,
            0,
            self.debugActGrp,
            "dbg_step_out",
        )
        act.setStatusTip(
            self.tr("""Execute Python statements until leaving the current frame""")
        )
        act.setWhatsThis(
            self.tr(
                """<b>Step Out</b>"""
                """<p>Execute Python statements until leaving the current"""
                """ frame. If the statements are inside an <tt>import</tt>"""
                """ statement, a class constructor, or a method or function"""
                """ call then control is returned to the debugger after the"""
                """ current frame has been left.</p>"""
            )
        )
        act.triggered.connect(self.__stepOut)
        self.actions.append(act)

        act = EricAction(
            self.tr("Stop"),
            EricPixmapCache.getIcon("stepQuit"),
            self.tr("&Stop"),
            Qt.Key.Key_F10,
            0,
            self.debugActGrp,
            "dbg_stop",
        )
        act.setStatusTip(self.tr("Stop debugging"))
        act.setWhatsThis(
            self.tr("""<b>Stop</b><p>Stop the running debugging session.</p>""")
        )
        act.triggered.connect(self.__stepQuit)
        self.actions.append(act)

        self.dbgFilterAct = EricAction(
            self.tr("Variables Type Filter"),
            self.tr("Varia&bles Type Filter..."),
            0,
            0,
            self,
            "dbg_variables_filter",
        )
        self.dbgFilterAct.setStatusTip(self.tr("Configure variables type filter"))
        self.dbgFilterAct.setWhatsThis(
            self.tr(
                """<b>Variables Type Filter</b>"""
                """<p>Configure the variables type filter. Only variable types"""
                """ that are not selected are displayed in the global or local"""
                """ variables window during a debugging session.</p>"""
            )
        )
        self.dbgFilterAct.triggered.connect(self.__configureVariablesFilters)
        self.actions.append(self.dbgFilterAct)

        self.excFilterAct = EricAction(
            self.tr("Exceptions Filter"),
            self.tr("&Exceptions Filter..."),
            0,
            0,
            self,
            "dbg_exceptions_filter",
        )
        self.excFilterAct.setStatusTip(self.tr("Configure exceptions filter"))
        self.excFilterAct.setWhatsThis(
            self.tr(
                """<b>Exceptions Filter</b>"""
                """<p>Configure the exceptions filter. Only exception types"""
                """ that are listed are highlighted during a debugging"""
                """ session.</p><p>Please note, that all unhandled exceptions"""
                """ are highlighted indepent from the filter list.</p>"""
            )
        )
        self.excFilterAct.triggered.connect(self.__configureExceptionsFilter)
        self.actions.append(self.excFilterAct)

        self.excIgnoreFilterAct = EricAction(
            self.tr("Ignored Exceptions"),
            self.tr("&Ignored Exceptions..."),
            0,
            0,
            self,
            "dbg_ignored_exceptions",
        )
        self.excIgnoreFilterAct.setStatusTip(self.tr("Configure ignored exceptions"))
        self.excIgnoreFilterAct.setWhatsThis(
            self.tr(
                """<b>Ignored Exceptions</b>"""
                """<p>Configure the ignored exceptions. Only exception types"""
                """ that are not listed are highlighted during a debugging"""
                """ session.</p><p>Please note, that unhandled exceptions"""
                """ cannot be ignored.</p>"""
            )
        )
        self.excIgnoreFilterAct.triggered.connect(self.__configureIgnoredExceptions)
        self.actions.append(self.excIgnoreFilterAct)

        self.dbgSetBpActGrp = createActionGroup(self)

        self.dbgToggleBpAct = EricAction(
            self.tr("Toggle Breakpoint"),
            EricPixmapCache.getIcon("breakpointToggle"),
            self.tr("Toggle Breakpoint"),
            QKeySequence(self.tr("Shift+F11", "Debug|Toggle Breakpoint")),
            0,
            self.dbgSetBpActGrp,
            "dbg_toggle_breakpoint",
        )
        self.dbgToggleBpAct.setStatusTip(self.tr("Toggle Breakpoint"))
        self.dbgToggleBpAct.setWhatsThis(
            self.tr(
                """<b>Toggle Breakpoint</b>"""
                """<p>Toggles a breakpoint at the current line of the"""
                """ current editor.</p>"""
            )
        )
        self.dbgToggleBpAct.triggered.connect(self.__toggleBreakpoint)
        self.actions.append(self.dbgToggleBpAct)

        self.dbgEditBpAct = EricAction(
            self.tr("Edit Breakpoint"),
            EricPixmapCache.getIcon("cBreakpointToggle"),
            self.tr("Edit Breakpoint..."),
            QKeySequence(self.tr("Shift+F12", "Debug|Edit Breakpoint")),
            0,
            self.dbgSetBpActGrp,
            "dbg_edit_breakpoint",
        )
        self.dbgEditBpAct.setStatusTip(self.tr("Edit Breakpoint"))
        self.dbgEditBpAct.setWhatsThis(
            self.tr(
                """<b>Edit Breakpoint</b>"""
                """<p>Opens a dialog to edit the breakpoints properties."""
                """ It works at the current line of the current editor.</p>"""
            )
        )
        self.dbgEditBpAct.triggered.connect(self.__editBreakpoint)
        self.actions.append(self.dbgEditBpAct)

        self.dbgNextBpAct = EricAction(
            self.tr("Next Breakpoint"),
            EricPixmapCache.getIcon("breakpointNext"),
            self.tr("Next Breakpoint"),
            QKeySequence(self.tr("Ctrl+Shift+PgDown", "Debug|Next Breakpoint")),
            0,
            self.dbgSetBpActGrp,
            "dbg_next_breakpoint",
        )
        self.dbgNextBpAct.setStatusTip(self.tr("Next Breakpoint"))
        self.dbgNextBpAct.setWhatsThis(
            self.tr(
                """<b>Next Breakpoint</b>"""
                """<p>Go to next breakpoint of the current editor.</p>"""
            )
        )
        self.dbgNextBpAct.triggered.connect(self.__nextBreakpoint)
        self.actions.append(self.dbgNextBpAct)

        self.dbgPrevBpAct = EricAction(
            self.tr("Previous Breakpoint"),
            EricPixmapCache.getIcon("breakpointPrevious"),
            self.tr("Previous Breakpoint"),
            QKeySequence(self.tr("Ctrl+Shift+PgUp", "Debug|Previous Breakpoint")),
            0,
            self.dbgSetBpActGrp,
            "dbg_previous_breakpoint",
        )
        self.dbgPrevBpAct.setStatusTip(self.tr("Previous Breakpoint"))
        self.dbgPrevBpAct.setWhatsThis(
            self.tr(
                """<b>Previous Breakpoint</b>"""
                """<p>Go to previous breakpoint of the current editor.</p>"""
            )
        )
        self.dbgPrevBpAct.triggered.connect(self.__previousBreakpoint)
        self.actions.append(self.dbgPrevBpAct)

        act = EricAction(
            self.tr("Clear Breakpoints"),
            self.tr("Clear Breakpoints"),
            0,
            0,
            self.dbgSetBpActGrp,
            "dbg_clear_breakpoint",
        )
        act.setStatusTip(self.tr("Clear Breakpoints"))
        act.setWhatsThis(
            self.tr(
                """<b>Clear Breakpoints</b>"""
                """<p>Clear breakpoints of all editors.</p>"""
            )
        )
        act.triggered.connect(self.__clearBreakpoints)
        self.actions.append(act)

        self.debugActGrp.setEnabled(False)
        self.dbgSetBpActGrp.setEnabled(False)
        self.runProjectAct.setEnabled(False)
        self.profileProjectAct.setEnabled(False)
        self.coverageProjectAct.setEnabled(False)
        self.debugProjectAct.setEnabled(False)
        self.restartAct.setEnabled(False)
        self.stopAct.setEnabled(False)

    def initMenus(self):
        """
        Public slot to initialize the project menu.

        @return the generated menu
        @rtype QMenu
        """
        dmenu = QMenu(self.tr("&Debug"), self.parent())
        dmenu.setTearOffEnabled(True)
        smenu = QMenu(self.tr("Sta&rt"), self.parent())
        smenu.setTearOffEnabled(True)
        self.breakpointsMenu = QMenu(self.tr("&Breakpoints"), dmenu)

        smenu.addAction(self.restartAct)
        smenu.addAction(self.stopAct)
        smenu.addSeparator()
        smenu.addAction(self.runAct)
        smenu.addAction(self.runProjectAct)
        smenu.addSeparator()
        smenu.addAction(self.debugAct)
        smenu.addAction(self.debugProjectAct)
        smenu.addSeparator()
        smenu.addAction(self.profileAct)
        smenu.addAction(self.profileProjectAct)
        smenu.addSeparator()
        smenu.addAction(self.coverageAct)
        smenu.addAction(self.coverageProjectAct)

        dmenu.addActions(self.debugActGrp.actions())
        dmenu.addSeparator()
        dmenu.addActions(self.dbgSetBpActGrp.actions())
        self.menuBreakpointsAct = dmenu.addMenu(self.breakpointsMenu)
        dmenu.addSeparator()
        dmenu.addAction(self.dbgFilterAct)
        dmenu.addAction(self.excFilterAct)
        dmenu.addAction(self.excIgnoreFilterAct)

        self.breakpointsMenu.aboutToShow.connect(self.__showBreakpointsMenu)
        self.breakpointsMenu.triggered.connect(self.__breakpointSelected)
        dmenu.aboutToShow.connect(self.__showDebugMenu)

        return smenu, dmenu

    def initToolbars(self, toolbarManager):
        """
        Public slot to initialize the debug toolbars.

        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        @return the generated toolbars
        @rtype list of QToolBar
        """
        starttb = QToolBar(self.tr("Start"), self.ui)
        starttb.setObjectName("StartToolbar")
        starttb.setToolTip(self.tr("Start"))

        starttb.addAction(self.restartAct)
        starttb.addAction(self.stopAct)
        starttb.addSeparator()
        starttb.addAction(self.runAct)
        starttb.addAction(self.runProjectAct)
        starttb.addSeparator()
        starttb.addAction(self.debugAct)
        starttb.addAction(self.debugProjectAct)

        debugtb = QToolBar(self.tr("Debug"), self.ui)
        debugtb.setObjectName("DebugToolbar")
        debugtb.setToolTip(self.tr("Debug"))

        debugtb.addActions(self.debugActGrp.actions())
        debugtb.addSeparator()
        debugtb.addAction(self.dbgToggleBpAct)
        debugtb.addAction(self.dbgEditBpAct)
        debugtb.addAction(self.dbgNextBpAct)
        debugtb.addAction(self.dbgPrevBpAct)

        toolbarManager.addToolBar(starttb, starttb.windowTitle())
        toolbarManager.addToolBar(debugtb, debugtb.windowTitle())
        toolbarManager.addAction(self.profileAct, starttb.windowTitle())
        toolbarManager.addAction(self.profileProjectAct, starttb.windowTitle())
        toolbarManager.addAction(self.coverageAct, starttb.windowTitle())
        toolbarManager.addAction(self.coverageProjectAct, starttb.windowTitle())

        return [starttb, debugtb]

    def setScriptsHistory(self, scriptName, clearHistories=False, history=None):
        """
        Public slot to initialize the scripts history.

        @param scriptName script name
        @type str
        @param clearHistories flag indicating, that the list should
            be cleared (defaults to False)
        @type bool (optional)
        @param history list of history entries to be set (defaults to None)
        @type list of str (optional)
        """
        if clearHistories:
            del self.scriptsHistory[1:]
        elif history is not None:
            self.scriptsHistory = history[:]
        else:
            if scriptName in self.scriptsHistory:
                self.scriptsHistory.remove(scriptName)
            self.scriptsHistory.insert(0, scriptName)

    def setArgvHistory(self, argsStr, clearHistories=False, history=None):
        """
        Public slot to initialize the argv history.

        @param argsStr command line arguments
        @type str
        @param clearHistories flag indicating, that the list should be cleared
        @type bool
        @param history list of history entries to be set
        @type list of str
        """
        if clearHistories:
            del self.argvHistory[1:]
        elif history is not None:
            self.argvHistory = history[:]
        else:
            if argsStr in self.argvHistory:
                self.argvHistory.remove(argsStr)
            self.argvHistory.insert(0, argsStr)

    def setWdHistory(self, wdStr, clearHistories=False, history=None):
        """
        Public slot to initialize the wd history.

        @param wdStr working directory
        @type str
        @param clearHistories flag indicating, that the list should be cleared
        @type bool
        @param history list of history entries to be set
        @type list of str
        """
        if clearHistories:
            del self.wdHistory[1:]
        elif history is not None:
            self.wdHistory = history[:]
        else:
            if wdStr in self.wdHistory:
                self.wdHistory.remove(wdStr)
            self.wdHistory.insert(0, wdStr)

    def setEnvHistory(self, envStr, clearHistories=False, history=None):
        """
        Public slot to initialize the env history.

        @param envStr the environment settings
        @type str
        @param clearHistories flag indicating, that the list should be cleared
        @type bool
        @param history list of history entries to be set
        @type list of str
        """
        if clearHistories:
            del self.envHistory[1:]
        elif history is not None:
            self.envHistory = history[:]
        else:
            if envStr in self.envHistory:
                self.envHistory.remove(envStr)
            self.envHistory.insert(0, envStr)

    def setExceptionReporting(self, reportAllExceptions):
        """
        Public slot to initialize the exception reporting flag.

        @param reportAllExceptions flag indicating to report all exceptions
        @type bool
        """
        self.reportAllExceptions = reportAllExceptions

    def setExcList(self, excList):
        """
        Public slot to initialize the exceptions type list.

        @param excList list of exception types
        @type list of str
        """
        self.excList = excList[:]  # keep a copy

    def setExcIgnoreList(self, excIgnoreList):
        """
        Public slot to initialize the ignored exceptions type list.

        @param excIgnoreList list of ignored exception types
        @type list of str
        """
        self.excIgnoreList = excIgnoreList[:]  # keep a copy

    def setAutoClearShell(self, autoClearShell):
        """
        Public slot to initialize the autoClearShell flag.

        @param autoClearShell flag indicating, that the interpreter window
            should be cleared
        @type bool
        """
        self.autoClearShell = autoClearShell

    def setTracePython(self, tracePython):
        """
        Public slot to initialize the trace Python flag.

        @param tracePython flag indicating if the Python library should be
            traced as well
        @type bool
        """
        self.tracePython = tracePython

    def setAutoContinue(self, autoContinue):
        """
        Public slot to initialize the autoContinue flag.

        @param autoContinue flag indicating, that the debugger should not
            stop at the first executable line
        @type bool
        """
        self.autoContinue = autoContinue

    def __editorOpened(self, fn):
        """
        Private slot to handle the editorOpened signal.

        @param fn filename of the opened editor
        @type str
        """
        self.editorOpen = True

        editor = self.viewmanager.getOpenEditor(fn) if fn else None
        self.__checkActions(editor)

    def __lastEditorClosed(self):
        """
        Private slot to handle the closeProgram signal.
        """
        self.editorOpen = False
        self.debugActGrp.setEnabled(False)
        self.dbgSetBpActGrp.setEnabled(False)
        self.lastAction = -1
        if not self.projectOpen:
            self.restartAct.setEnabled(False)
            self.lastDebuggedFile = None
            self.lastStartAction = 0
            self.clientType = ""

    def __checkActions(self, editor):
        """
        Private slot to check some actions for their enable/disable status.

        @param editor editor window
        @type Editor
        """
        fn = editor.getFileName() if editor else None

        cap = 0
        if fn:
            for language in self.debugServer.getSupportedLanguages():
                exts = self.debugServer.getExtensions(language)
                if fn.endswith(exts):
                    cap = self.debugServer.getClientCapabilities(language)
                    break
            else:
                if editor.isPy3File():
                    cap = self.debugServer.getClientCapabilities("Python3")
                elif editor.isRubyFile():
                    cap = self.debugServer.getClientCapabilities("Ruby")

            self.dbgSetBpActGrp.setEnabled(cap & HasDebugger)
            if editor.curLineHasBreakpoint():
                self.dbgEditBpAct.setEnabled(True)
            else:
                self.dbgEditBpAct.setEnabled(False)
            if editor.hasBreakpoints():
                self.dbgNextBpAct.setEnabled(True)
                self.dbgPrevBpAct.setEnabled(True)
            else:
                self.dbgNextBpAct.setEnabled(False)
                self.dbgPrevBpAct.setEnabled(False)
        else:
            self.dbgSetBpActGrp.setEnabled(False)

    def __cursorChanged(self, editor):
        """
        Private slot handling the cursorChanged signal of the viewmanager.

        @param editor editor window
        @type Editor
        """
        if editor is None:
            return

        if editor.isPyFile() or editor.isRubyFile():
            if editor.curLineHasBreakpoint():
                self.dbgEditBpAct.setEnabled(True)
            else:
                self.dbgEditBpAct.setEnabled(False)
            if editor.hasBreakpoints():
                self.dbgNextBpAct.setEnabled(True)
                self.dbgPrevBpAct.setEnabled(True)
            else:
                self.dbgNextBpAct.setEnabled(False)
                self.dbgPrevBpAct.setEnabled(False)

    def __projectOpened(self):
        """
        Private slot to handle the projectOpened signal.
        """
        self.projectOpen = True
        cap = self.debugServer.getClientCapabilities(self.project.getProjectLanguage())
        if not self.passive:
            self.debugProjectAct.setEnabled(cap & HasDebugger)
            self.runProjectAct.setEnabled(cap & HasInterpreter)
            self.profileProjectAct.setEnabled(cap & HasProfiler)
            self.coverageProjectAct.setEnabled(cap & HasCoverage)

    def __projectClosed(self):
        """
        Private slot to handle the projectClosed signal.
        """
        self.projectOpen = False
        self.runProjectAct.setEnabled(False)
        self.profileProjectAct.setEnabled(False)
        self.coverageProjectAct.setEnabled(False)
        self.debugProjectAct.setEnabled(False)

        if not self.editorOpen:
            self.restartAct.setEnabled(False)
            self.lastDebuggedFile = None
            self.lastStartAction = 0
            self.clientType = ""

    def clearHistories(self):
        """
        Public method to clear the various debug histories.
        """
        self.scriptsHistory = []
        self.argvHistory = []
        self.wdHistory = []
        self.envHistory = []
        self.multiprocessNoDebugHistory = []

        Preferences.getSettings().setValue(
            "DebugInfo/ScriptsHistory", self.scriptsHistory
        )
        Preferences.getSettings().setValue(
            "DebugInfo/ArgumentsHistory", self.argvHistory
        )
        Preferences.getSettings().setValue(
            "DebugInfo/WorkingDirectoryHistory", self.wdHistory
        )
        Preferences.getSettings().setValue(
            "DebugInfo/EnvironmentHistory", self.envHistory
        )
        Preferences.getSettings().setValue(
            "DebugInfo/MultiprocessNoDebugHistory", self.multiprocessNoDebugHistory
        )

        self.debugViewer.breakpointViewer.clearHistories()

    def shutdown(self):
        """
        Public method to perform shutdown actions.
        """
        # Just save the 10 most recent entries
        del self.scriptsHistory[10:]
        del self.argvHistory[10:]
        del self.wdHistory[10:]
        del self.envHistory[10:]

        Preferences.getSettings().setValue(
            "DebugInfo/VirtualEnvironment", self.lastUsedVenvName
        )
        Preferences.getSettings().setValue(
            "DebugInfo/ScriptsHistory", self.scriptsHistory
        )
        Preferences.getSettings().setValue(
            "DebugInfo/ArgumentsHistory", self.argvHistory
        )
        Preferences.getSettings().setValue(
            "DebugInfo/WorkingDirectoryHistory", self.wdHistory
        )
        Preferences.getSettings().setValue(
            "DebugInfo/EnvironmentHistory", self.envHistory
        )
        Preferences.getSettings().setValue("DebugInfo/Exceptions", self.excList)
        Preferences.getSettings().setValue(
            "DebugInfo/IgnoredExceptions", self.excIgnoreList
        )
        Preferences.getSettings().setValue(
            "DebugInfo/AutoClearShell", self.autoClearShell
        )
        Preferences.getSettings().setValue("DebugInfo/TracePython", self.tracePython)
        Preferences.getSettings().setValue("DebugInfo/AutoContinue", self.autoContinue)
        Preferences.getSettings().setValue(
            "DebugInfo/ReportAllExceptions", self.reportAllExceptions
        )
        Preferences.getSettings().setValue(
            "DebugInfo/EnableMultiprocess", self.enableMultiprocess
        )
        Preferences.getSettings().setValue(
            "DebugInfo/MultiprocessNoDebugHistory", self.multiprocessNoDebugHistory
        )
        Preferences.getSettings().setValue(
            "DebugInfo/OverrideGlobal", self.overrideGlobalConfig["enable"]
        )
        Preferences.getSettings().setValue(
            "DebugInfo/RedirectStdinStdout", self.overrideGlobalConfig["redirect"]
        )

    def shutdownServer(self):
        """
        Public method to shut down the debug server.

        This is needed to cleanly close the sockets on Win OS.

        @return always true
        @rtype bool
        """
        self.debugServer.shutdownServer()
        return True

    def __resetUI(self, fullReset=True):
        """
        Private slot to reset the user interface.

        @param fullReset flag indicating a full reset is required
        @type bool
        """
        self.lastAction = -1
        self.debugActGrp.setEnabled(False)
        self.__clientDebuggerIds.clear()

        if not self.passive:
            if self.editorOpen:
                editor = self.viewmanager.activeWindow()
            else:
                editor = None
            self.__checkActions(editor)

            self.debugProjectAct.setEnabled(self.projectOpen)
            self.runProjectAct.setEnabled(self.projectOpen)
            self.profileProjectAct.setEnabled(self.projectOpen)
            self.coverageProjectAct.setEnabled(self.projectOpen)
            if self.lastDebuggedFile is not None and (
                self.editorOpen or self.projectOpen
            ):
                self.restartAct.setEnabled(True)
            else:
                self.restartAct.setEnabled(False)
            self.stopAct.setEnabled(False)

        self.resetUI.emit(fullReset)

    def __clientDebuggerId(self, debuggerId):
        """
        Private slot to track the list of connected debuggers.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.__clientDebuggerIds.add(debuggerId)

    def __clientLine(self, fn, line, debuggerId, _threadName, forStack):
        """
        Private method to handle a change to the current line.

        @param fn filename
        @type str
        @param line linenumber
        @type int
        @param debuggerId ID of the debugger backend
        @type str
        @param _threadName name of the thread signaling the event (unused)
        @type str
        @param forStack flag indicating this is for a stack dump
        @type bool
        """
        self.ui.raise_()
        self.ui.activateWindow()
        if self.ui.getViewProfile() != "debug":
            self.ui.setDebugProfile()
        self.viewmanager.setFileLine(fn, line)
        if not forStack:
            self.__getThreadList(debuggerId)
            self.__getClientVariables(debuggerId)

        self.debugActGrp.setEnabled(True)

    @pyqtSlot(str)
    def __clientDisconnected(self, debuggerId):
        """
        Private slot to handle a debug client disconnecting its control
        socket.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.__clientDebuggerIds.discard(debuggerId)

        if len(self.__clientDebuggerIds) == 0:
            self.viewmanager.exit()
            self.__resetUI(fullReset=False)

    @pyqtSlot(str, int, str, bool, str)
    def __clientExit(self, program, status, message, quiet, debuggerId):
        """
        Private slot to handle the debugged program terminating.

        @param program name of the exited program
        @type str
        @param status exit code of the debugged program
        @type int
        @param message exit message of the debugged program
        @type str
        @param quiet flag indicating to suppress exit info display
        @type bool
        @param debuggerId ID of the debugger backend
        @type str
        """
        self.__clientDisconnected(debuggerId)

        if not quiet:
            if not program:
                program = self.ui.currentProg

            if message:
                info = self.tr("Message: {0}").format(
                    EricUtilities.html_uencode(message)
                )
            else:
                info = ""
            if program is None:
                msg = self.tr(
                    "<p>The program has terminated with an exit status of"
                    " {0}.</p><p>{1}</p>"
                ).format(status, info)
            else:
                msg = self.tr(
                    "<p><b>{0}</b> has terminated with an exit status of"
                    " {1}.</p><p>{2}</p>"
                ).format(os.path.basename(program), status, info)
            if status != 0:
                timeout = 0
                kind = NotificationTypes.WARNING
            else:
                timeout = None
                kind = NotificationTypes.INFORMATION
            self.ui.showNotification(
                EricPixmapCache.getPixmap("debug48"),
                self.tr("Program terminated"),
                msg,
                kind=kind,
                timeout=timeout,
            )

    def __mainClientExit(self):
        """
        Private slot handling the exit of the last client.
        """
        self.viewmanager.exit()
        self.__resetUI()

        self.debuggingFinished.emit()

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
        self.__resetUI()
        self.ui.raise_()
        self.ui.activateWindow()

        if message is None:
            EricMessageBox.critical(
                self.ui,
                Program,
                self.tr(
                    "The program being debugged contains an unspecified"
                    " syntax error."
                ),
            )
            return

        if not os.path.isabs(filename):
            if os.path.exists(os.path.join(self.project.getProjectPath(), filename)):
                filename = os.path.join(self.project.getProjectPath(), filename)
            else:
                ms = self.project.getMainScript(normalized=True)
                if ms is not None:
                    d = os.path.dirname(ms)
                    if os.path.exists(os.path.join(d, filename)):
                        filename = os.path.join(d, filename)
        self.viewmanager.setFileLine(filename, lineNo, error=True)
        EricMessageBox.critical(
            self.ui,
            Program,
            self.tr(
                "<p>The file <b>{0}</b> contains the syntax error"
                " <b>{1}</b> at line <b>{2}</b>, character <b>{3}</b>."
                "</p>"
            ).format(filename, message, lineNo, characterNo),
        )

    def __clientException(
        self, exceptionType, exceptionMessage, stackTrace, debuggerId
    ):
        """
        Private method to handle an exception of the debugged program.

        @param exceptionType type of exception raised
        @type str
        @param exceptionMessage message given by the exception
        @type (str
        @param stackTrace list of stack entries
        @type list of str
        @param debuggerId ID of the debugger backend
        @type str
        """
        self.ui.raise_()
        QApplication.processEvents()
        if not exceptionType:
            EricMessageBox.critical(
                self.ui,
                Program,
                self.tr(
                    "An unhandled exception occured."
                    " See the shell window for details."
                ),
            )
            return

        if (
            self.reportAllExceptions
            and exceptionType not in self.excIgnoreList
            and (len(self.excList) == 0 or exceptionType in self.excList)
        ) or exceptionType.startswith("unhandled"):
            res = None
            if stackTrace:
                with contextlib.suppress(UnicodeError, OSError):
                    file, line = stackTrace[0][:2]
                    source, _encoding = Utilities.readEncodedFile(file)
                    source = source.splitlines(True)
                    if len(source) >= line:
                        lineFlags = Utilities.extractLineFlags(source[line - 1].strip())
                        with contextlib.suppress(IndexError):
                            lineFlags += Utilities.extractLineFlags(
                                source[line].strip(), flagsLine=True
                            )
                        if "__IGNORE_EXCEPTION__" in lineFlags:
                            res = EricMessageBox.No
                if res != EricMessageBox.No:
                    self.viewmanager.setFileLine(
                        stackTrace[0][0], stackTrace[0][1], error=True
                    )
            if res != EricMessageBox.No:
                self.ui.activateWindow()
                if Preferences.getDebugger("BreakAlways"):
                    res = EricMessageBox.Yes
                else:
                    if stackTrace:
                        if exceptionType.startswith("unhandled"):
                            buttons = EricMessageBox.No | EricMessageBox.Yes
                        else:
                            buttons = (
                                EricMessageBox.No
                                | EricMessageBox.Yes
                                | EricMessageBox.Ignore
                            )
                        filename = stackTrace[0][0]
                        res = (
                            EricMessageBox.critical(
                                self.ui,
                                Program,
                                self.tr(
                                    "<p>The debugged program raised the exception"
                                    ' <b>{0}</b><br>"<b>{1}</b>"<br>'
                                    "File: <b>{2}</b>, Line: <b>{3}</b></p>"
                                    "<p>Break here?</p>"
                                ).format(
                                    exceptionType,
                                    EricUtilities.html_encode(exceptionMessage),
                                    filename,
                                    stackTrace[0][1],
                                ),
                                buttons,
                                EricMessageBox.No,
                            )
                            if Utilities.MimeTypes.isTextFile(filename)
                            else EricMessageBox.critical(
                                self.ui,
                                Program,
                                self.tr(
                                    "<p>The debugged program raised the exception"
                                    ' <b>{0}</b><br>"<b>{1}</b>"<br>'
                                    "File: <b>{2}</b>, Line: <b>{3}</b></p>"
                                ).format(
                                    exceptionType,
                                    EricUtilities.html_encode(exceptionMessage),
                                    filename,
                                    stackTrace[0][1],
                                ),
                            )
                        )
                    else:
                        res = EricMessageBox.critical(
                            self.ui,
                            Program,
                            self.tr(
                                "<p>The debugged program raised the exception"
                                ' <b>{0}</b><br>"<b>{1}</b>"</p>'
                            ).format(
                                exceptionType,
                                EricUtilities.html_encode(exceptionMessage),
                            ),
                        )
            if res == EricMessageBox.Yes:
                self.debugServer.setDebugging(True)
                self.exceptionInterrupt.emit()
                stack = []
                for fn, ln, func, args in stackTrace:
                    stack.append((fn, ln, func, args))
                self.clientStack.emit(stack, debuggerId)
                self.__getClientVariables(debuggerId)
                self.__getClientDisassembly(debuggerId)
                self.ui.setDebugProfile()
                self.debugActGrp.setEnabled(True)
                return
            elif (
                res == EricMessageBox.Ignore and exceptionType not in self.excIgnoreList
            ):
                self.excIgnoreList.append(exceptionType)

        if self.lastAction != -1:
            if self.lastAction == 2:
                self.__specialContinue(debuggerId)
            else:
                self.debugActions[self.lastAction](debuggerId)
        else:
            self.__continue(debuggerId)

    def __clientSignal(
        self, message, filename, lineNo, _funcName, _funcArgs, _debuggerId
    ):
        """
        Private method to handle a signal generated on the client side.

        @param message message of the syntax error
        @type str
        @param filename translated filename of the syntax error position
        @type str
        @param lineNo line number of the syntax error position
        @type int
        @param _funcName name of the function causing the signal (unused)
        @type str
        @param _funcArgs function arguments (unused)
        @type str
        @param _debuggerId ID of the debugger backend (unused)
        @type str
        """
        self.ui.raise_()
        self.ui.activateWindow()
        QApplication.processEvents()
        self.viewmanager.setFileLine(filename, lineNo, error=True)
        EricMessageBox.critical(
            self.ui,
            Program,
            self.tr(
                """<p>The program generate the signal "{0}".<br/>"""
                """File: <b>{1}</b>, Line: <b>{2}</b></p>"""
            ).format(message, filename, lineNo),
        )

    def __clientGone(self, unplanned):
        """
        Private method to handle the disconnection of the debugger client.

        @param unplanned True if the client died, False otherwise
        @type bool
        """
        self.__resetUI()
        if unplanned:
            EricMessageBox.information(
                self.ui,
                Program,
                self.tr("The program being debugged has terminated unexpectedly."),
            )

    def __getThreadList(self, debuggerId):
        """
        Private method to get the list of threads from the client.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.debugServer.remoteThreadList(debuggerId)

    def __clientThreadSet(self, debuggerId):
        """
        Private method to handle a change of the client's current thread.

        @param debuggerId ID of the debugger backend
        @type str
        """
        if self.debugServer.isDebugging():
            self.__getClientVariables(debuggerId)

    def __getClientVariables(self, debuggerId):
        """
        Private method to request the global and local variables.

        In the first step, the global variables are requested from the client.
        Once these have been received, the local variables are requested.
        This happens in the method '__clientVariables'.

        @param debuggerId ID of the debugger backend
        @type str
        """
        # get globals first
        self.debugServer.remoteClientVariables(
            debuggerId, 1, self.__globalsVarFilterList
        )
        # get locals second
        self.debugServer.remoteClientVariables(
            debuggerId, 0, self.__localsVarFilterList
        )

    def __clientVariables(self, scope, variables, debuggerId):
        """
        Private method to write the clients variables to the user interface.

        @param scope scope of the variables
            (-2 = no frame found, -1 = empty locals, 1 = global, 0 = local)
        @type int
        @param variables the list of variables from the client
        @type list
        @param debuggerId ID of the debugger backend
        @type str
        """
        if debuggerId == self.getSelectedDebuggerId() and scope > -2:
            self.ui.activateDebugViewer()
            if scope > 0:
                self.debugViewer.showVariables(variables, True)
            elif scope == 0:
                self.debugViewer.showVariables(variables, False)
            elif scope == -1:
                vlist = [(self.tr("No locals available."), "", "", False, -2, "")]
                self.debugViewer.showVariables(vlist, False)

    def __clientVariable(self, scope, variables, debuggerId):
        """
        Private method to write the contents of a clients classvariable to
        the user interface.

        @param scope scope of the variables (-1 = empty locals, 1 = global,
            0 = local)
        @type int
        @param variables the list of variables from the client
        @type list
        @param debuggerId ID of the debugger backend
        @type str
        """
        if debuggerId == self.getSelectedDebuggerId():
            self.ui.activateDebugViewer()
            if scope == 1:
                self.debugViewer.showVariable(variables, True)
            elif scope == 0:
                self.debugViewer.showVariable(variables, False)

    def __getClientDisassembly(self, debuggerId):
        """
        Private method to ask the client for the latest traceback disassembly.

        @param debuggerId ID of the debugger backend
        @type str
        """
        self.debugServer.remoteClientDisassembly(debuggerId)

    def __clientBreakConditionError(self, filename, lineno, _debuggerId):
        """
        Private method to handle a condition error of a breakpoint.

        @param filename filename of the breakpoint
        @type str
        @param lineno line umber of the breakpoint
        @type int
        @param _debuggerId ID of the debugger backend (unused)
        @type str
        """
        from .EditBreakpointDialog import EditBreakpointDialog

        EricMessageBox.critical(
            self.ui,
            self.tr("Breakpoint Condition Error"),
            self.tr(
                """<p>The condition of the breakpoint <b>{0}, {1}</b>"""
                """ contains a syntax error.</p>"""
            ).format(filename, lineno),
        )

        model = self.debugServer.getBreakPointModel()
        index = model.getBreakPointIndex(filename, lineno)
        if not index.isValid():
            return

        bp = model.getBreakPointByIndex(index)
        if not bp:
            return

        fn, line, cond, temp, enabled, count = bp[:6]

        # get recently used breakpoint conditions
        rs = Preferences.Prefs.rsettings.value(recentNameBreakpointConditions)
        condHistory = (
            EricUtilities.toList(rs)[: Preferences.getDebugger("RecentNumber")]
            if rs is not None
            else []
        )

        dlg = EditBreakpointDialog(
            (fn, line),
            (cond, temp, enabled, count),
            condHistory,
            parent=self.ui,
            modal=True,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            cond, temp, enabled, count = dlg.getData()
            model.setBreakPointByIndex(index, fn, line, (cond, temp, enabled, count))

            if cond:
                # save the recently used breakpoint condition
                if cond in condHistory:
                    condHistory.remove(cond)
                condHistory.insert(0, cond)
                Preferences.Prefs.rsettings.setValue(
                    recentNameBreakpointConditions, condHistory
                )
                Preferences.Prefs.rsettings.sync()

    def __clientWatchConditionError(self, cond, _debuggerId):
        """
        Private method to handle a expression error of a watch expression.

        Note: This can only happen for normal watch expressions

        @param cond expression of the watch expression
        @type str
        @param _debuggerId ID of the debugger backend (unused)
        @type str
        """
        from .EditWatchpointDialog import EditWatchpointDialog

        EricMessageBox.critical(
            self.ui,
            self.tr("Watch Expression Error"),
            self.tr(
                """<p>The watch expression <b>{0}</b>"""
                """ contains a syntax error.</p>"""
            ).format(cond),
        )

        model = self.debugServer.getWatchPointModel()
        index = model.getWatchPointIndex(cond)
        if not index.isValid():
            return

        wp = model.getWatchPointByIndex(index)
        if not wp:
            return

        cond, special, temp, enabled, count = wp[:5]

        dlg = EditWatchpointDialog(
            (cond, temp, enabled, count, special), parent=self.ui
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            cond, temp, enabled, count, special = dlg.getData()

            # check for duplicates
            idx = model.getWatchPointIndex(cond, special)
            duplicate = (
                idx.isValid() and idx.internalPointer() != index.internalPointer()
            )
            if duplicate:
                if not special:
                    msg = self.tr(
                        """<p>A watch expression '<b>{0}</b>'"""
                        """ already exists.</p>"""
                    ).format(EricUtilities.html_encode(cond))
                else:
                    msg = self.tr(
                        """<p>A watch expression '<b>{0}</b>'"""
                        """ for the variable <b>{1}</b> already"""
                        """ exists.</p>"""
                    ).format(special, EricUtilities.html_encode(cond))
                EricMessageBox.warning(
                    self.ui, self.tr("Watch expression already exists"), msg
                )
                model.deleteWatchPointByIndex(index)
            else:
                model.setWatchPointByIndex(index, cond, special, (temp, enabled, count))

    def __configureVariablesFilters(self):
        """
        Private slot for displaying the variables filter configuration dialog.
        """
        from .VariablesFilterDialog import VariablesFilterDialog

        dlg = VariablesFilterDialog(parent=self.ui, name="Filter Dialog", modal=True)
        dlg.applyFilterLists.connect(self.__applyVariablesFilters)
        dlg.setSelection(self.__localsVarFilterList, self.__globalsVarFilterList)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.__localsVarFilterList, self.__globalsVarFilterList = dlg.getSelection()
        self.__applyVariablesFilters(
            self.__localsVarFilterList, self.__globalsVarFilterList
        )

    @pyqtSlot(list, list)
    def __applyVariablesFilters(self, localsFilter, globalsFilter):
        """
        Private slot to apply the given variables filter lists.

        @param localsFilter variables filter for the local variables
        @type list of str
        @param globalsFilter variables filter for the global variables
        @type list of str
        """
        self.debugViewer.setVariablesFilter(globalsFilter, localsFilter)
        self.debugViewer.refreshVariablesLists()

    def __configureExceptionsFilter(self):
        """
        Private slot for displaying the exception filter dialog.
        """
        from .ExceptionsFilterDialog import ExceptionsFilterDialog

        dlg = ExceptionsFilterDialog(self.excList, ignore=False, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.excList = dlg.getExceptionsList()[:]  # keep a copy

    def __configureIgnoredExceptions(self):
        """
        Private slot for displaying the ignored exceptions dialog.
        """
        from .ExceptionsFilterDialog import ExceptionsFilterDialog

        dlg = ExceptionsFilterDialog(self.excIgnoreList, ignore=True, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.excIgnoreList = dlg.getExceptionsList()[:]  # keep a copy

    def __toggleBreakpoint(self):
        """
        Private slot to handle the 'Set/Reset breakpoint' action.
        """
        self.viewmanager.activeWindow().menuToggleBreakpoint()

    def __editBreakpoint(self):
        """
        Private slot to handle the 'Edit breakpoint' action.
        """
        self.viewmanager.activeWindow().menuEditBreakpoint()

    def __nextBreakpoint(self):
        """
        Private slot to handle the 'Next breakpoint' action.
        """
        self.viewmanager.activeWindow().menuNextBreakpoint()

    def __previousBreakpoint(self):
        """
        Private slot to handle the 'Previous breakpoint' action.
        """
        self.viewmanager.activeWindow().menuPreviousBreakpoint()

    def __clearBreakpoints(self):
        """
        Private slot to handle the 'Clear breakpoints' action.
        """
        self.debugServer.getBreakPointModel().deleteAll()

    def __showDebugMenu(self):
        """
        Private method to set up the debug menu.
        """
        bpCount = self.debugServer.getBreakPointModel().rowCount()
        self.menuBreakpointsAct.setEnabled(bpCount > 0)

    def __showBreakpointsMenu(self):
        """
        Private method to handle the show breakpoints menu signal.
        """
        self.breakpointsMenu.clear()

        model = self.debugServer.getBreakPointModel()
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            filename, line, cond = model.getBreakPointByIndex(index)[:3]
            formattedCond = " : {0}".format(cond[:20]) if cond else ""
            bpSuffix = " : {0:d}{1}".format(line, formattedCond)
            act = self.breakpointsMenu.addAction(
                "{0}{1}".format(
                    FileSystemUtilities.compactPath(
                        filename, self.ui.maxMenuFilePathLen - len(bpSuffix)
                    ),
                    bpSuffix,
                )
            )
            act.setData([filename, line])

    def __breakpointSelected(self, act):
        """
        Private method to handle the breakpoint selected signal.

        @param act reference to the action that triggered
        @type QAction
        """
        qvList = act.data()
        filename = qvList[0]
        line = qvList[1]
        self.viewmanager.openSourceFile(filename, line)

    def __coverageScript(self):
        """
        Private slot to handle the coverage of script action.
        """
        self.doCoverage(False)

    def __coverageProject(self):
        """
        Private slot to handle the coverage of project action.
        """
        self.processChangedProjectFiles.emit()
        self.doCoverage(True)

    def doCoverage(self, runProject, script=""):
        """
        Public method to handle the coverage actions.

        @param runProject flag indicating coverage of the current project
            (True) or script (false)
        @type bool
        @param script name of a script (optional)
        @type str
        """
        from .StartDialog import StartDialog, StartDialogMode

        self.__resetUI()
        doNotStart = False

        # Get the command line arguments, the working directory and the
        # exception reporting flag.
        cap = (
            self.tr("Coverage Run of Project")
            if runProject
            else self.tr("Coverage Run of Script")
        )
        if runProject:
            scriptName = self.project.getMainScript(True)
            if not scriptName:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Coverage Run of Project"),
                    self.tr(
                        "There is no main script defined for the"
                        " current project. Aborting"
                    ),
                )
                return
        elif script:
            scriptName = script
        elif self.lastDebuggedFile:
            scriptName = self.lastDebuggedFile
        else:
            scriptName = ""
        dlg = StartDialog(
            cap,
            self.lastUsedVenvName,
            self.argvHistory,
            self.wdHistory,
            self.envHistory,
            parent=self.ui,
            dialogMode=StartDialogMode.Coverage,
            autoClearShell=self.autoClearShell,
            configOverride=self.overrideGlobalConfig,
            forProject=runProject,
            scriptName=scriptName,
            scriptsList=self.scriptsHistory,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            (
                lastUsedVenvName,
                scriptName,
                argv,
                wd,
                env,
                clearShell,
                console,
            ) = dlg.getData()
            configOverride = dlg.getGlobalOverrideData()
            eraseCoverage = dlg.getCoverageData()

            if runProject:
                fn = self.project.getMainScript(True)

                if Preferences.getDebugger(
                    "Autosave"
                ) and not self.project.saveAllScripts(reportSyntaxErrors=True):
                    doNotStart = True

                # save the info for later use
                self.project.setDbgInfo(
                    lastUsedVenvName,
                    argv,
                    wd,
                    env,
                    self.excList,
                    self.excIgnoreList,
                    clearShell,
                    configOverride=configOverride,
                )

                self.lastStartAction = 6
                self.clientType = self.project.getProjectLanguage()
            else:
                if scriptName:
                    fn = scriptName
                    self.clientType = "Python3"
                    editor = self.viewmanager.getOpenEditor(scriptName)
                    if editor and not self.viewmanager.checkDirty(
                        editor, Preferences.getDebugger("Autosave")
                    ):
                        return
                else:
                    # run current editor
                    editor = self.viewmanager.activeWindow()
                    if editor is None:
                        return

                    if (
                        not self.viewmanager.checkDirty(
                            editor, Preferences.getDebugger("Autosave")
                        )
                        or editor.getFileName() is None
                    ):
                        return

                    fn = editor.getFileName()
                    self.clientType = editor.determineFileType()
                self.lastStartAction = 5

            if (
                FileSystemUtilities.isRemoteFileName(fn)
                and not self.ui.isEricServerConnected()
            ):
                self.__showNotConnectedWarning(title=cap)
                return

            # save the filename for use by the restart method
            self.lastDebuggedFile = fn
            self.restartAct.setEnabled(True)

            # save the most recently used virtual environment
            self.lastUsedVenvName = lastUsedVenvName

            # This moves any previous occurrence of these arguments to the head
            # of the list.
            self.setScriptsHistory(scriptName)
            self.setArgvHistory(argv)
            self.setWdHistory(wd)
            self.setEnvHistory(env)

            # Save the erase coverage flag
            self.eraseCoverage = eraseCoverage

            # Save the clear interpreter flag
            self.autoClearShell = clearShell

            # Save the run in console flag
            self.runInConsole = console

            # Save the global config override data
            self.overrideGlobalConfig = copy.deepcopy(configOverride)

            # Hide all error highlights
            self.viewmanager.unhighlight()

            if not doNotStart:
                if runProject and self.project.getProjectType() in ["E7Plugin"]:
                    argv = '--plugin="{0}" {1}'.format(fn, argv)
                    fn = ""  # script name of the eric IDE is set in debug client

                self.debugViewer.initCallStackViewer(runProject)

                # Ask the client to open the new program.
                self.debugServer.remoteCoverage(
                    lastUsedVenvName,
                    fn,
                    Utilities.parseOptionString(argv),
                    wd,
                    env,
                    autoClearShell=self.autoClearShell,
                    erase=eraseCoverage,
                    forProject=runProject,
                    runInConsole=console,
                    clientType=self.clientType,
                    configOverride=self.overrideGlobalConfig,
                )

                self.stopAct.setEnabled(True)

        if dlg.clearHistories():
            self.setScriptsHistory("", clearHistories=True)
            self.setArgvHistory("", clearHistories=True)
            self.setWdHistory("", clearHistories=True)
            self.setEnvHistory("", clearHistories=True)
            self.setMultiprocessNoDebugHistory("", clearHistories=True)
        elif dlg.historiesModified():
            (scriptsHistory, argvHistory, wdHistory, envHistory, _) = dlg.getHistories()
            self.setScriptsHistory("", history=scriptsHistory)
            self.setArgvHistory("", history=argvHistory)
            self.setWdHistory("", history=wdHistory)
            self.setEnvHistory("", history=envHistory)

    def __profileScript(self):
        """
        Private slot to handle the profile script action.
        """
        self.doProfile(False)

    def __profileProject(self):
        """
        Private slot to handle the profile project action.
        """
        self.processChangedProjectFiles.emit()
        self.doProfile(True)

    def doProfile(self, runProject, script=""):
        """
        Public method to handle the profile actions.

        @param runProject flag indicating profiling of the current project
            (True) or script (False)
        @type bool
        @param script name of a script (optional)
        @type str
        """
        from .StartDialog import StartDialog, StartDialogMode

        self.__resetUI()
        doNotStart = False

        # Get the command line arguments, the working directory and the
        # exception reporting flag.
        cap = (
            self.tr("Profile Run of Project")
            if runProject
            else self.tr("Profile Run of Script")
        )
        if runProject:
            scriptName = self.project.getMainScript(True)
            if not scriptName:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Profile Run of Project"),
                    self.tr(
                        "There is no main script defined for the"
                        " current project. Aborting"
                    ),
                )
                return
        elif script:
            scriptName = script
        elif self.lastDebuggedFile:
            scriptName = self.lastDebuggedFile
        else:
            scriptName = ""
        dlg = StartDialog(
            cap,
            self.lastUsedVenvName,
            self.argvHistory,
            self.wdHistory,
            self.envHistory,
            parent=self.ui,
            dialogMode=StartDialogMode.Profile,
            autoClearShell=self.autoClearShell,
            configOverride=self.overrideGlobalConfig,
            forProject=runProject,
            scriptName=scriptName,
            scriptsList=self.scriptsHistory,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            (
                lastUsedVenvName,
                scriptName,
                argv,
                wd,
                env,
                clearShell,
                console,
            ) = dlg.getData()
            configOverride = dlg.getGlobalOverrideData()
            eraseTimings = dlg.getProfilingData()

            if runProject:
                fn = self.project.getMainScript(True)

                if Preferences.getDebugger(
                    "Autosave"
                ) and not self.project.saveAllScripts(reportSyntaxErrors=True):
                    doNotStart = True

                # save the info for later use
                self.project.setDbgInfo(
                    lastUsedVenvName,
                    argv,
                    wd,
                    env,
                    self.excList,
                    self.excIgnoreList,
                    clearShell,
                    configOverride=configOverride,
                )

                self.lastStartAction = 8
                self.clientType = self.project.getProjectLanguage()
            else:
                if scriptName:
                    fn = scriptName
                    self.clientType = "Python3"
                    editor = self.viewmanager.getOpenEditor(scriptName)
                    if editor and not self.viewmanager.checkDirty(
                        editor, Preferences.getDebugger("Autosave")
                    ):
                        return
                else:
                    # run current editor
                    editor = self.viewmanager.activeWindow()
                    if editor is None:
                        return

                    if (
                        not self.viewmanager.checkDirty(
                            editor, Preferences.getDebugger("Autosave")
                        )
                        or editor.getFileName() is None
                    ):
                        return

                    fn = editor.getFileName()
                    self.clientType = editor.determineFileType()
                self.lastStartAction = 7

            if (
                FileSystemUtilities.isRemoteFileName(fn)
                and not self.ui.isEricServerConnected()
            ):
                self.__showNotConnectedWarning(title=cap)
                return

            # save the filename for use by the restart method
            self.lastDebuggedFile = fn
            self.restartAct.setEnabled(True)

            # save the most recently used virtual environment
            self.lastUsedVenvName = lastUsedVenvName

            # This moves any previous occurrence of these arguments to the head
            # of the list.
            self.setScriptsHistory(scriptName)
            self.setArgvHistory(argv)
            self.setWdHistory(wd)
            self.setEnvHistory(env)

            # Save the erase timing flag
            self.eraseTimings = eraseTimings

            # Save the clear interpreter flag
            self.autoClearShell = clearShell

            # Save the run in console flag
            self.runInConsole = console

            # Save the global config override data
            self.overrideGlobalConfig = copy.deepcopy(configOverride)

            # Hide all error highlights
            self.viewmanager.unhighlight()

            if not doNotStart:
                if runProject and self.project.getProjectType() in ["E7Plugin"]:
                    argv = '--plugin="{0}" {1}'.format(fn, argv)
                    fn = ""  # script name of the eric IDE is set in debug client

                self.debugViewer.initCallStackViewer(runProject)

                # Ask the client to open the new program.
                self.debugServer.remoteProfile(
                    lastUsedVenvName,
                    fn,
                    Utilities.parseOptionString(argv),
                    wd,
                    env,
                    autoClearShell=self.autoClearShell,
                    erase=eraseTimings,
                    forProject=runProject,
                    runInConsole=console,
                    clientType=self.clientType,
                    configOverride=self.overrideGlobalConfig,
                )

                self.stopAct.setEnabled(True)

        if dlg.clearHistories():
            self.setScriptsHistory("", clearHistories=True)
            self.setArgvHistory("", clearHistories=True)
            self.setWdHistory("", clearHistories=True)
            self.setEnvHistory("", clearHistories=True)
            self.setMultiprocessNoDebugHistory("", clearHistories=True)
        elif dlg.historiesModified():
            (scriptsHistory, argvHistory, wdHistory, envHistory, _) = dlg.getHistories()
            self.setScriptsHistory("", history=scriptsHistory)
            self.setArgvHistory("", history=argvHistory)
            self.setWdHistory("", history=wdHistory)
            self.setEnvHistory("", history=envHistory)

    def __runScript(self):
        """
        Private slot to handle the run script action.
        """
        self.doRun(False)

    def __runProject(self):
        """
        Private slot to handle the run project action.
        """
        self.processChangedProjectFiles.emit()
        self.doRun(True)

    def doRun(self, runProject, script=""):
        """
        Public method to handle the run actions.

        @param runProject flag indicating running the current project (True)
                or script (False)
        @type bool
        @param script name of a script (optional)
        @type str
        """
        from .StartDialog import StartDialog, StartDialogMode

        self.__resetUI()
        doNotStart = False

        # Get the command line arguments, the working directory and the
        # exception reporting flag.
        cap = self.tr("Run Project") if runProject else self.tr("Run Script")
        if runProject:
            scriptName = self.project.getMainScript(True)
            if not scriptName:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Run Project"),
                    self.tr(
                        "There is no main script defined for the"
                        " current project. Aborting"
                    ),
                )
                return
        elif script:
            scriptName = script
        elif self.lastDebuggedFile:
            scriptName = self.lastDebuggedFile
        else:
            scriptName = ""
        dlg = StartDialog(
            cap,
            self.lastUsedVenvName,
            self.argvHistory,
            self.wdHistory,
            self.envHistory,
            parent=self.ui,
            dialogMode=StartDialogMode.Run,
            autoClearShell=self.autoClearShell,
            configOverride=self.overrideGlobalConfig,
            forProject=runProject,
            scriptName=scriptName,
            scriptsList=self.scriptsHistory,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            (
                lastUsedVenvName,
                scriptName,
                argv,
                wd,
                env,
                clearShell,
                console,
            ) = dlg.getData()
            configOverride = dlg.getGlobalOverrideData()

            if runProject:
                fn = self.project.getMainScript(True)

                if Preferences.getDebugger(
                    "Autosave"
                ) and not self.project.saveAllScripts(reportSyntaxErrors=True):
                    doNotStart = True

                # save the info for later use
                self.project.setDbgInfo(
                    lastUsedVenvName,
                    argv,
                    wd,
                    env,
                    self.excList,
                    self.excIgnoreList,
                    clearShell,
                    configOverride=configOverride,
                )

                self.lastStartAction = 4
                self.clientType = self.project.getProjectLanguage()
            else:
                if scriptName:
                    fn = scriptName
                    self.clientType = "Python3"
                    editor = self.viewmanager.getOpenEditor(scriptName)
                    if editor and not self.viewmanager.checkDirty(
                        editor, Preferences.getDebugger("Autosave")
                    ):
                        return
                else:
                    # run current editor
                    editor = self.viewmanager.activeWindow()
                    if editor is None:
                        return

                    if (
                        not self.viewmanager.checkDirty(
                            editor, Preferences.getDebugger("Autosave")
                        )
                        or editor.getFileName() is None
                    ):
                        return

                    fn = editor.getFileName()
                    self.clientType = editor.determineFileType()
                self.lastStartAction = 3

            if (
                FileSystemUtilities.isRemoteFileName(fn)
                and not self.ui.isEricServerConnected()
            ):
                self.__showNotConnectedWarning(title=cap)
                return

            # save the filename for use by the restart method
            self.lastDebuggedFile = fn
            self.restartAct.setEnabled(True)

            # save the most recently used virtual environment
            self.lastUsedVenvName = lastUsedVenvName

            # This moves any previous occurrence of these arguments to the head
            # of the list.
            self.setScriptsHistory(scriptName)
            self.setArgvHistory(argv)
            self.setWdHistory(wd)
            self.setEnvHistory(env)

            # Save the clear interpreter flag
            self.autoClearShell = clearShell

            # Save the run in console flag
            self.runInConsole = console

            # Save the global config override data
            self.overrideGlobalConfig = copy.deepcopy(configOverride)

            # Hide all error highlights
            self.viewmanager.unhighlight()

            if not doNotStart:
                if runProject and self.project.getProjectType() in ["E7Plugin"]:
                    argv = '--plugin="{0}" {1}'.format(fn, argv)
                    fn = ""  # script name of the eric IDE is set in debug client

                self.debugViewer.initCallStackViewer(runProject)

                # Ask the client to open the new program.
                self.debugServer.remoteRun(
                    lastUsedVenvName,
                    fn,
                    Utilities.parseOptionString(argv),
                    wd,
                    env,
                    autoClearShell=self.autoClearShell,
                    forProject=runProject,
                    runInConsole=console,
                    clientType=self.clientType,
                    configOverride=self.overrideGlobalConfig,
                )

                self.stopAct.setEnabled(True)

        if dlg.clearHistories():
            self.setScriptsHistory("", clearHistories=True)
            self.setArgvHistory("", clearHistories=True)
            self.setWdHistory("", clearHistories=True)
            self.setEnvHistory("", clearHistories=True)
            self.setMultiprocessNoDebugHistory("", clearHistories=True)
        elif dlg.historiesModified():
            (scriptsHistory, argvHistory, wdHistory, envHistory, _) = dlg.getHistories()
            self.setScriptsHistory("", history=scriptsHistory)
            self.setArgvHistory("", history=argvHistory)
            self.setWdHistory("", history=wdHistory)
            self.setEnvHistory("", history=envHistory)

    def __debugScript(self):
        """
        Private slot to handle the debug script action.
        """
        self.doDebug(False)

    def __debugProject(self):
        """
        Private slot to handle the debug project action.
        """
        self.processChangedProjectFiles.emit()
        self.doDebug(True)

    def doDebug(self, debugProject, script=""):
        """
        Public method to handle the debug actions.

        @param debugProject flag indicating debugging the current project
            (True) or script (False)
        @type bool
        @param script name of a script (defaults to "")
        @type str (optional)
        """
        from .StartDialog import StartDialog, StartDialogMode

        self.__resetUI()
        doNotStart = False

        # Get the command line arguments, the working directory and the
        # exception reporting flag.
        cap = self.tr("Debug Project") if debugProject else self.tr("Debug Script")
        if debugProject:
            scriptName = self.project.getMainScript(True)
            if not scriptName:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Debug Project"),
                    self.tr(
                        "There is no main script defined for the"
                        " current project. No debugging possible."
                    ),
                )
                return
        elif script:
            scriptName = script
        elif self.lastDebuggedFile:
            scriptName = self.lastDebuggedFile
        else:
            scriptName = ""
        if (
            scriptName
            and FileSystemUtilities.isRemoteFileName(scriptName)
            and not self.ui.isEricServerConnected()
        ):
            self.__showNotConnectedWarning(title=cap, name=scriptName)
            return

        dlg = StartDialog(
            cap,
            self.lastUsedVenvName,
            self.argvHistory,
            self.wdHistory,
            self.envHistory,
            parent=self.ui,
            dialogMode=StartDialogMode.Debug,
            tracePython=self.tracePython,
            autoClearShell=self.autoClearShell,
            autoContinue=self.autoContinue,
            reportAllExceptions=self.reportAllExceptions,
            enableMultiprocess=self.enableMultiprocess,
            multiprocessNoDebugHistory=self.multiprocessNoDebugHistory,
            configOverride=self.overrideGlobalConfig,
            forProject=debugProject,
            scriptName=scriptName,
            scriptsList=self.scriptsHistory,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            (
                lastUsedVenvName,
                scriptName,
                argv,
                wd,
                env,
                clearShell,
                console,
            ) = dlg.getData()
            configOverride = dlg.getGlobalOverrideData()
            (
                tracePython,
                autoContinue,
                reportAllExceptions,
                enableMultiprocess,
                multiprocessNoDebug,
            ) = dlg.getDebugData()

            if debugProject:
                fn = self.project.getMainScript(True)

                if Preferences.getDebugger(
                    "Autosave"
                ) and not self.project.saveAllScripts(reportSyntaxErrors=True):
                    doNotStart = True

                # save the info for later use
                self.project.setDbgInfo(
                    lastUsedVenvName,
                    argv,
                    wd,
                    env,
                    self.excList,
                    self.excIgnoreList,
                    clearShell,
                    tracePython=tracePython,
                    autoContinue=autoContinue,
                    reportAllExceptions=reportAllExceptions,
                    enableMultiprocess=enableMultiprocess,
                    multiprocessNoDebug=multiprocessNoDebug,
                    configOverride=configOverride,
                )

                self.lastStartAction = 2
                self.clientType = self.project.getProjectLanguage()
            else:
                if scriptName:
                    fn = scriptName
                    self.clientType = "Python3"
                    editor = self.viewmanager.getOpenEditor(scriptName)
                    if editor and not self.viewmanager.checkDirty(
                        editor, Preferences.getDebugger("Autosave")
                    ):
                        return
                else:
                    # debug current editor
                    editor = self.viewmanager.activeWindow()
                    if editor is None:
                        return

                    if (
                        not self.viewmanager.checkDirty(
                            editor, Preferences.getDebugger("Autosave")
                        )
                        or editor.getFileName() is None
                    ):
                        return

                    fn = editor.getFileName()
                    self.clientType = editor.determineFileType()
                self.lastStartAction = 1

            if (
                FileSystemUtilities.isRemoteFileName(fn)
                and not self.ui.isEricServerConnected()
            ):
                self.__showNotConnectedWarning(title=cap, name=fn)
                return

            # save the filename for use by the restart method
            self.lastDebuggedFile = fn
            self.restartAct.setEnabled(True)

            # save the most recently used virtual environment
            self.lastUsedVenvName = lastUsedVenvName

            # This moves any previous occurrence of these arguments to the head
            # of the list.
            self.setScriptsHistory(scriptName)
            self.setArgvHistory(argv)
            self.setWdHistory(wd)
            self.setEnvHistory(env)

            # Save the tracePython flag
            self.tracePython = tracePython

            # Save the clear interpreter flag
            self.autoClearShell = clearShell

            # Save the run in console flag
            self.runInConsole = console

            # Save the auto continue flag
            self.autoContinue = autoContinue

            # Save the exception reporting flag
            self.reportAllExceptions = reportAllExceptions

            # Save the multiprocess debugging data
            self.enableMultiprocess = enableMultiprocess
            self.setMultiprocessNoDebugHistory(multiprocessNoDebug)

            # Save the global config override data
            self.overrideGlobalConfig = copy.deepcopy(configOverride)

            # Hide all error highlights
            self.viewmanager.unhighlight()

            if not doNotStart:
                if debugProject and self.project.getProjectType() in ["E7Plugin"]:
                    argv = '--plugin="{0}" {1}'.format(fn, argv)
                    fn = ""  # script name of the eric IDE is set in debug client
                    tracePython = True  # override flag because it must be true

                self.debugViewer.initCallStackViewer(debugProject)

                # Ask the client to send call trace info
                enableCallTrace = self.debugViewer.isCallTraceEnabled()
                self.debugViewer.clearCallTrace()
                self.debugViewer.setCallTraceToProjectMode(debugProject)

                # Ask the client to open the new program.
                self.debugServer.remoteLoad(
                    lastUsedVenvName,
                    fn,
                    Utilities.parseOptionString(argv),
                    wd,
                    env,
                    autoClearShell=self.autoClearShell,
                    tracePython=tracePython,
                    autoContinue=autoContinue,
                    forProject=debugProject,
                    runInConsole=console,
                    clientType=self.clientType,
                    enableCallTrace=enableCallTrace,
                    enableMultiprocess=enableMultiprocess,
                    multiprocessNoDebug=multiprocessNoDebug,
                    configOverride=self.overrideGlobalConfig,
                    reportAllExceptions=self.reportAllExceptions,
                )

                if (
                    self.debugServer.isClientProcessUp()
                    and self.debugServer.getClientType() == self.clientType
                ):
                    # Signal that we have started a debugging session
                    self.debuggingStarted.emit(fn)

                    self.stopAct.setEnabled(True)

        if dlg.clearHistories():
            self.setScriptsHistory("", clearHistories=True)
            self.setArgvHistory("", clearHistories=True)
            self.setWdHistory("", clearHistories=True)
            self.setEnvHistory("", clearHistories=True)
            self.setMultiprocessNoDebugHistory("", clearHistories=True)
        elif dlg.historiesModified():
            (
                scriptsHistory,
                argvHistory,
                wdHistory,
                envHistory,
                noDebugHistory,
            ) = dlg.getHistories()
            self.setScriptsHistory("", history=scriptsHistory)
            self.setArgvHistory("", history=argvHistory)
            self.setWdHistory("", history=wdHistory)
            self.setEnvHistory("", history=envHistory)
            self.setMultiprocessNoDebugHistory("", history=noDebugHistory)

    def debugInternalScript(
        self, venvName, scriptName, argv, workDir, environment, clientType, forProject
    ):
        """
        Public method to run an internal script with debugger support.

        @param venvName name of the environment for the debug tests run
        @type str
        @param scriptName name of the internal script to be run
        @type str
        @param argv string or list containing the parameters for the script
        @type str or list of str
        @param workDir working directory for the script
        @type str
        @param environment environment parameter override for the debug run
        @type str or dict
        @param clientType type (language) of the debug client to be used
        @type str
        @param forProject flag indicating a project related debug session
        @type bool
        """
        self.__resetUI()

        # Hide all error highlights
        self.viewmanager.unhighlight()

        self.debugViewer.initCallStackViewer(forProject)

        # Ask the client to send call trace info
        enableCallTrace = self.debugViewer.isCallTraceEnabled()
        self.debugViewer.clearCallTrace()
        self.debugViewer.setCallTraceToProjectMode(forProject)

        args = argv if isinstance(argv, list) else shlex.split(argv)
        # Ask the client to open the new program.
        self.debugServer.remoteLoad(
            venvName,
            scriptName,
            args,
            workDir,
            environment,
            clientType=clientType,
            enableCallTrace=enableCallTrace,
        )

        if (
            self.debugServer.isClientProcessUp()
            and self.debugServer.getClientType() == clientType
        ):
            # Signal that we have started a debugging session
            self.debuggingStarted.emit(scriptName)

            self.stopAct.setEnabled(True)

    def __doRestart(self):
        """
        Private slot to handle the restart action to restart the last
        debugged file.
        """
        self.__resetUI()
        doNotStart = False

        # first save any changes
        if self.lastStartAction in [1, 3, 5, 7, 9]:
            editor = self.viewmanager.getOpenEditor(self.lastDebuggedFile)
            if editor and not self.viewmanager.checkDirty(
                editor, Preferences.getDebugger("Autosave")
            ):
                return
            forProject = False
        elif self.lastStartAction in [2, 4, 6, 8, 10]:
            if Preferences.getDebugger("Autosave") and not self.project.saveAllScripts(
                reportSyntaxErrors=True
            ):
                doNotStart = True
            self.processChangedProjectFiles.emit()
            forProject = True
        else:
            return  # should not happen

        # get the saved stuff
        venvName = self.lastUsedVenvName
        wd = self.wdHistory[0]
        argv = self.argvHistory[0]
        fn = self.lastDebuggedFile
        env = self.envHistory[0]

        # Hide all error highlights
        self.viewmanager.unhighlight()

        if not doNotStart:
            if (
                FileSystemUtilities.isRemoteFileName(fn)
                and not self.ui.isEricServerConnected()
            ):
                self.__showNotConnectedWarning(title=self.tr("Restart"))
                return

            if forProject and self.project.getProjectType() in ["E7Plugin"]:
                argv = '--plugin="{0}" {1}'.format(fn, argv)
                fn = ""  # script name of the eric IDE is set in debug client

            self.debugViewer.initCallStackViewer(forProject)

            if self.lastStartAction in [1, 2]:
                # Ask the client to send call trace info
                enableCallTrace = self.debugViewer.isCallTraceEnabled()
                self.debugViewer.clearCallTrace()
                self.debugViewer.setCallTraceToProjectMode(forProject)
                multiprocessNoDebug = self.multiprocessNoDebugHistory[0]

                # Ask the client to debug the new program.
                self.debugServer.remoteLoad(
                    venvName,
                    fn,
                    Utilities.parseOptionString(argv),
                    wd,
                    env,
                    autoClearShell=self.autoClearShell,
                    tracePython=self.tracePython,
                    autoContinue=self.autoContinue,
                    forProject=forProject,
                    runInConsole=self.runInConsole,
                    clientType=self.clientType,
                    enableCallTrace=enableCallTrace,
                    enableMultiprocess=self.enableMultiprocess,
                    multiprocessNoDebug=multiprocessNoDebug,
                    configOverride=self.overrideGlobalConfig,
                    reportAllExceptions=self.reportAllExceptions,
                )

                # Signal that we have started a debugging session
                self.debuggingStarted.emit(fn)

            elif self.lastStartAction in [3, 4]:
                # Ask the client to run the new program.
                self.debugServer.remoteRun(
                    venvName,
                    fn,
                    Utilities.parseOptionString(argv),
                    wd,
                    env,
                    autoClearShell=self.autoClearShell,
                    forProject=forProject,
                    runInConsole=self.runInConsole,
                    clientType=self.clientType,
                    configOverride=self.overrideGlobalConfig,
                )

            elif self.lastStartAction in [5, 6]:
                # Ask the client to coverage run the new program.
                self.debugServer.remoteCoverage(
                    venvName,
                    fn,
                    Utilities.parseOptionString(argv),
                    wd,
                    env,
                    autoClearShell=self.autoClearShell,
                    erase=self.eraseCoverage,
                    forProject=forProject,
                    runInConsole=self.runInConsole,
                    clientType=self.clientType,
                    configOverride=self.overrideGlobalConfig,
                )

            elif self.lastStartAction in [7, 8]:
                # Ask the client to profile run the new program.
                self.debugServer.remoteProfile(
                    venvName,
                    fn,
                    Utilities.parseOptionString(argv),
                    wd,
                    env,
                    autoClearShell=self.autoClearShell,
                    erase=self.eraseTimings,
                    forProject=forProject,
                    runInConsole=self.runInConsole,
                    clientType=self.clientType,
                    configOverride=self.overrideGlobalConfig,
                )

            self.stopAct.setEnabled(True)

    def __stopScript(self):
        """
        Private slot to stop the running script.
        """
        self.debugServer.startClient(False)

    def __passiveDebugStarted(self, fn, exc):
        """
        Private slot to handle a passive debug session start.

        @param fn filename of the debugged script
        @type str
        @param exc flag to enable exception reporting of the IDE
        @type bool
        """
        # Hide all error highlights
        self.viewmanager.unhighlight()

        # Set filename of script being debugged
        self.ui.currentProg = fn

        # Set exception reporting
        self.setExceptionReporting(exc)

        # Signal that we have started a debugging session
        self.debuggingStarted.emit(fn)

        # Initialize the call stack viewer
        self.debugViewer.initCallStackViewer(False)

    def __continue(self, debuggerId=""):
        """
        Private method to handle the Continue action.

        @param debuggerId ID of the debugger backend
        @type str
        """
        if not debuggerId:
            debuggerId = self.getSelectedDebuggerId()

        self.lastAction = 0
        self.__enterRemote()
        self.debugServer.remoteContinue(debuggerId)

    def __specialContinue(self, debuggerId=""):
        """
        Private method to handle the Special Continue action.

        @param debuggerId ID of the debugger backend
        @type str
        """
        if not debuggerId:
            debuggerId = self.getSelectedDebuggerId()

        self.lastAction = 2
        self.__enterRemote()
        self.debugServer.remoteContinue(debuggerId, 1)

    def __step(self, debuggerId=""):
        """
        Private method to handle the Step action.

        @param debuggerId ID of the debugger backend
        @type str
        """
        if not debuggerId:
            debuggerId = self.getSelectedDebuggerId()

        self.lastAction = 1
        self.__enterRemote()
        self.debugServer.remoteStep(debuggerId)

    def __stepOver(self, debuggerId=""):
        """
        Private method to handle the Step Over action.

        @param debuggerId ID of the debugger backend
        @type str
        """
        if not debuggerId:
            debuggerId = self.getSelectedDebuggerId()

        self.lastAction = 2
        self.__enterRemote()
        self.debugServer.remoteStepOver(debuggerId)

    def __stepOut(self, debuggerId=""):
        """
        Private method to handle the Step Out action.

        @param debuggerId ID of the debugger backend
        @type str
        """
        if not debuggerId:
            debuggerId = self.getSelectedDebuggerId()

        self.lastAction = 3
        self.__enterRemote()
        self.debugServer.remoteStepOut(debuggerId)

    def __stepQuit(self, debuggerId=""):
        """
        Private method to handle the Step Quit action.

        @param debuggerId ID of the debugger backend
        @type str
        """
        if not debuggerId:
            debuggerId = self.getSelectedDebuggerId()

        self.lastAction = 4
        self.__enterRemote()
        self.debugServer.remoteStepQuit(debuggerId)
        self.__resetUI()

    def __runToCursor(self, debuggerId=""):
        """
        Private method to handle the Run to Cursor action.

        @param debuggerId ID of the debugger backend
        @type str
        """
        if not debuggerId:
            debuggerId = self.getSelectedDebuggerId()

        self.lastAction = 0
        aw = self.viewmanager.activeWindow()
        line = aw.getCursorPosition()[0] + 1
        self.__enterRemote()
        self.debugServer.remoteBreakpoint(
            self.getSelectedDebuggerId(), aw.getFileName(), line, 1, None, 1
        )
        self.debugServer.remoteContinue(debuggerId)

    def __runUntil(self, debuggerId=""):
        """
        Private method to handle the Run Until action.

        @param debuggerId ID of the debugger backend
        @type str
        """
        if not debuggerId:
            debuggerId = self.getSelectedDebuggerId()

        self.lastAction = 0
        aw = self.viewmanager.activeWindow()
        line = aw.getCursorPosition()[0] + 1
        self.__enterRemote()
        self.debugServer.remoteContinueUntil(debuggerId, line)

    def __moveInstructionPointer(self, debuggerId=""):
        """
        Private method to move the instruction pointer to a different line.

        @param debuggerId ID of the debugger backend
        @type str
        """
        if not debuggerId:
            debuggerId = self.getSelectedDebuggerId()

        self.lastAction = 0
        aw = self.viewmanager.activeWindow()
        line = aw.getCursorPosition()[0] + 1
        self.debugServer.remoteMoveIP(debuggerId, line)

    def __enterRemote(self):
        """
        Private method to update the user interface.

        This method is called just prior to executing some of
        the program being debugged.
        """
        # Disable further debug commands from the user.
        self.debugActGrp.setEnabled(False)

        self.viewmanager.unhighlight(True)

    def getActions(self):
        """
        Public method to get a list of all actions.

        @return list of all actions
        @rtype list of EricAction
        """
        return self.actions[:]

    def getSelectedDebuggerId(self):
        """
        Public method to get the currently selected debugger ID.

        @return selected debugger ID
        @rtype str
        """
        return self.debugViewer.getSelectedDebuggerId()

    def setDebugActionsEnabled(self, enable):
        """
        Public method to set the enabled state of the debug actions.

        @param enable enable state to be set
        @type bool
        """
        self.debugActGrp.setEnabled(enable)

    def setMultiprocessNoDebugHistory(
        self, noDebugList, clearHistories=False, history=None
    ):
        """
        Public slot to initialize the no debug list history.

        @param noDebugList whitespace separated list of programs not to be
            debugged
        @type str
        @param clearHistories flag indicating, that the list should be cleared
        @type bool
        @param history list of history entries to be set
        @type list of str
        """
        if clearHistories:
            del self.multiprocessNoDebugHistory[1:]
        elif history is not None:
            self.multiprocessNoDebugHistory = history[:]
        else:
            if noDebugList in self.multiprocessNoDebugHistory:
                self.multiprocessNoDebugHistory.remove(noDebugList)
            self.multiprocessNoDebugHistory.insert(0, noDebugList)

    def setEnableMultiprocess(self, enableMultiprocess):
        """
        Public slot to initialize the enableMultiprocess flag.

        @param enableMultiprocess flag indicating, that the debugger should be
            run in multi process mode
        @type bool
        """
        self.enableMultiprocess = enableMultiprocess

    def setEnableGlobalConfigOverride(self, overrideData):
        """
        Public method to initialize the global config override data.

        @param overrideData dictionary containing a flag indicating to enable
            global config override and a flag indicating to redirect
            stdin/stdout/stderr
        @type dict
        """
        self.overrideGlobalConfig = copy.deepcopy(overrideData)

    def getProjectEnvironmentString(self):
        """
        Public method to get the string for the project environment.

        @return string for the project environment
        @rtype str
        """
        return self.debugServer.getProjectEnvironmentString()

    def __showNotConnectedWarning(self, title, name=""):
        """
        Private method to show a warning about a not connected eric-ide server.

        @param title title for the dialog
        @type str
        @param name name of the file (defaults to "")
        @type str (optional)
        """
        EricMessageBox.warning(
            None,
            title,
            self.tr(
                "<p>The selected file <b>{0}</b> is located on an eric-ide server but"
                " no such server is connected. Aborting...</p>"
            ).format(name),
        )
