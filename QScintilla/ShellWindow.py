# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a stand alone shell window.
"""

import os

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtCore import (
    QCoreApplication,
    QPoint,
    QProcess,
    QSignalMapper,
    QSize,
    Qt,
    pyqtSlot,
)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QWhatsThis, QWidget

from eric7 import Preferences
from eric7.Debugger.DebugServer import DebugServer
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction, createActionGroup
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.EricWidgets.EricZoomWidget import EricZoomWidget
from eric7.Globals import getConfig
from eric7.SystemUtilities import OSUtilities, PythonUtilities
from eric7.UI.SearchWidget import SearchWidget
from eric7.VirtualEnv.VirtualenvManager import VirtualenvManager

from .APIsManager import APIsManager
from .Shell import Shell, ShellHistoryStyle


class ShellWindow(EricMainWindow):
    """
    Class implementing a stand alone shell window.
    """

    def __init__(self, originalPathString, parent=None, name=None):
        """
        Constructor

        @param originalPathString original PATH environment variable
        @type str
        @param parent reference to the parent widget
        @type QWidget
        @param name object name of the window
        @type str
        """
        super().__init__(parent)
        if name is not None:
            self.setObjectName(name)
        self.setWindowIcon(EricPixmapCache.getIcon("shell"))
        self.setWindowTitle(self.tr("eric Shell"))

        self.setStyle(
            styleName=Preferences.getUI("Style"),
            styleSheetFile=Preferences.getUI("StyleSheet"),
            itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
        )

        self.__lastDebuggerId = ""

        # initialize the APIs manager
        self.__apisManager = APIsManager(parent=self)

        # initialize the debug server and shell widgets
        self.__debugServer = DebugServer(
            originalPathString, preventPassiveDebugging=True, parent=self
        )
        self.__debugServer.clientDebuggerId.connect(self.__clientDebuggerId)

        self.__shell = Shell(self.__debugServer, self, None, True, self)
        self.__shell.registerDebuggerIdMethod(self.getDebuggerId)

        self.__searchWidget = SearchWidget(self.__shell, self, showLine=True)

        centralWidget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addWidget(self.__shell)
        layout.addWidget(self.__searchWidget)
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)
        self.__searchWidget.hide()

        self.__searchWidget.searchNext.connect(self.__shell.searchNext)
        self.__searchWidget.searchPrevious.connect(self.__shell.searchPrev)
        self.__shell.searchStringFound.connect(self.__searchWidget.searchStringFound)

        self.__shell.zoomValueChanged.connect(self.__zoomValueChanged)

        self.__createActions()
        self.__createMenus()
        self.__createToolBars()
        self.__createStatusBar()

        self.__readSettings()

        self.__shell.historyStyleChanged.connect(self.__historyStyleChanged)

        # Generate the virtual environment manager and register it
        self.virtualenvManager = VirtualenvManager(self)
        ericApp().registerObject("VirtualEnvManager", self.virtualenvManager)

        self.__shell.virtualEnvironmentChanged.connect(self.__virtualEnvironmentChanged)

        # now start the debug client with the most recently used virtual
        # environment
        self.__debugServer.startClient(
            False, venvName=Preferences.getShell("LastVirtualEnvironment")
        )

        # set the keyboard input interval
        interval = Preferences.getUI("KeyboardInputInterval")
        if interval > 0:
            QApplication.setKeyboardInputInterval(interval)

    def closeEvent(self, event):
        """
        Protected method to handle the close event.

        @param event close event
        @type QCloseEvent
        """
        self.__writeSettings()
        self.__debugServer.shutdownServer()
        self.__shell.closeShell()
        Preferences.syncPreferences()

        event.accept()

    def __clientDebuggerId(self, debuggerId):
        """
        Private slot to receive the ID of a newly connected debugger backend.

        @param debuggerId ID of a newly connected debugger backend
        @type str
        """
        self.__lastDebuggerId = debuggerId

    def getDebuggerId(self):
        """
        Public method to get the most recently registered debugger ID.

        @return debugger ID
        @rtype str
        """
        return self.__lastDebuggerId

    ##################################################################
    ## Below are API handling methods
    ##################################################################

    def getAPIsManager(self):
        """
        Public method to get a reference to the APIs manager.

        @return the APIs manager object
        @rtype QScintilla.APIsManager
        """
        return self.__apisManager

    ##################################################################
    ## Below are action related methods
    ##################################################################

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
        self.searchActions = []
        self.viewActions = []
        self.helpActions = []

        self.viewActGrp = createActionGroup(self)

        self.__createFileActions()
        self.__createEditActions()
        self.__createSearchActions()
        self.__createViewActions()
        self.__createHelpActions()
        self.__createHistoryActions()
        self.__createSettingsActions()

        # read the keyboard shortcuts and make them identical to the main
        # eric shortcuts
        for act in self.helpActions:
            self.__readShortcut(act, "General")
        for act in self.editActions:
            self.__readShortcut(act, "Edit")
        for act in self.fileActions:
            self.__readShortcut(act, "View")
        for act in self.searchActions:
            self.__readShortcut(act, "Search")

    def __createFileActions(self):
        """
        Private method defining the user interface actions for the file
        commands.
        """
        self.exitAct = EricAction(
            self.tr("Quit"),
            EricPixmapCache.getIcon("exit"),
            self.tr("&Quit"),
            QKeySequence(self.tr("Ctrl+Q", "File|Quit")),
            0,
            self,
            "quit",
        )
        self.exitAct.setStatusTip(self.tr("Quit the Shell"))
        self.exitAct.setWhatsThis(
            self.tr("""<b>Quit the Shell</b><p>This quits the Shell window.</p>""")
        )
        self.exitAct.triggered.connect(self.quit)
        self.exitAct.setMenuRole(QAction.MenuRole.QuitRole)
        self.fileActions.append(self.exitAct)

        self.newWindowAct = EricAction(
            self.tr("New Window"),
            EricPixmapCache.getIcon("newWindow"),
            self.tr("New &Window"),
            QKeySequence(self.tr("Ctrl+Shift+N", "File|New Window")),
            0,
            self,
            "new_window",
        )
        self.newWindowAct.setStatusTip(self.tr("Open a new Shell window"))
        self.newWindowAct.setWhatsThis(
            self.tr(
                """<b>New Window</b>"""
                """<p>This opens a new instance of the Shell window.</p>"""
            )
        )
        self.newWindowAct.triggered.connect(self.__newWindow)
        self.fileActions.append(self.newWindowAct)

        self.restartAct = EricAction(
            self.tr("Restart"),
            EricPixmapCache.getIcon("restart"),
            self.tr("Restart"),
            0,
            0,
            self,
            "shell_restart",
        )
        self.restartAct.setStatusTip(self.tr("Restart the shell"))
        self.restartAct.setWhatsThis(
            self.tr(
                """<b>Restart</b>"""
                """<p>Restart the shell for the currently selected"""
                """ environment.</p>"""
            )
        )
        self.restartAct.triggered.connect(self.__shell.doRestart)
        self.fileActions.append(self.restartAct)

        self.clearRestartAct = EricAction(
            self.tr("Restart and Clear"),
            EricPixmapCache.getIcon("restartDelete"),
            self.tr("Restart and Clear"),
            Qt.Key.Key_F4,
            0,
            self,
            "shell_clear_restart",
        )
        self.clearRestartAct.setStatusTip(
            self.tr("Clear the window and restart the shell")
        )
        self.clearRestartAct.setWhatsThis(
            self.tr(
                """<b>Restart and Clear</b>"""
                """<p>Clear the shell window and restart the shell for the"""
                """ currently selected environment.</p>"""
            )
        )
        self.clearRestartAct.triggered.connect(self.__shell.doClearRestart)
        self.fileActions.append(self.clearRestartAct)

        self.saveContentsAct = EricAction(
            self.tr("Save Contents"),
            EricPixmapCache.getIcon("fileSave"),
            self.tr("Save Contents..."),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+S", "File|Save")
            ),
            0,
            self,
            "vm_file_save",
        )
        self.saveContentsAct.setStatusTip(
            self.tr("Save the current contents of the shell to a file")
        )
        self.saveContentsAct.setWhatsThis(
            self.tr(
                """<b>Save Contents</b>"""
                """<p>Save the current contents of the shell to a file.</p>"""
            )
        )
        self.saveContentsAct.triggered.connect(self.__shell.saveContents)
        self.fileActions.append(self.saveContentsAct)

    def __createEditActions(self):
        """
        Private method defining the user interface actions for the edit
        commands.
        """
        self.editActGrp = createActionGroup(self)
        self.copyActGrp = createActionGroup(self.editActGrp)

        self.cutAct = EricAction(
            QCoreApplication.translate("ViewManager", "Cut"),
            EricPixmapCache.getIcon("editCut"),
            QCoreApplication.translate("ViewManager", "Cu&t"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+X", "Edit|Cut")
            ),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Shift+Del", "Edit|Cut")
            ),
            self.copyActGrp,
            "vm_edit_cut",
        )
        self.cutAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Cut the selection")
        )
        self.cutAct.setWhatsThis(
            self.tr("""<b>Cut</b><p>Cut the selected text to the clipboard.</p>""")
        )
        self.cutAct.triggered.connect(self.__shell.cut)
        self.editActions.append(self.cutAct)

        self.copyAct = EricAction(
            QCoreApplication.translate("ViewManager", "Copy"),
            EricPixmapCache.getIcon("editCopy"),
            QCoreApplication.translate("ViewManager", "&Copy"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+C", "Edit|Copy")
            ),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+Ins", "Edit|Copy")
            ),
            self.copyActGrp,
            "vm_edit_copy",
        )
        self.copyAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Copy the selection")
        )
        self.copyAct.setWhatsThis(
            self.tr("""<b>Copy</b><p>Copy the selected text to the clipboard.</p>""")
        )
        self.copyAct.triggered.connect(self.__shell.copy)
        self.editActions.append(self.copyAct)

        self.pasteAct = EricAction(
            QCoreApplication.translate("ViewManager", "Paste"),
            EricPixmapCache.getIcon("editPaste"),
            QCoreApplication.translate("ViewManager", "&Paste"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+V", "Edit|Paste")
            ),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Shift+Ins", "Edit|Paste")
            ),
            self.copyActGrp,
            "vm_edit_paste",
        )
        self.pasteAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Paste the last cut/copied text")
        )
        self.pasteAct.setWhatsThis(
            self.tr(
                """<b>Paste</b>"""
                """<p>Paste the last cut/copied text from the clipboard.</p>"""
            )
        )
        self.pasteAct.triggered.connect(self.__shell.paste)
        self.editActions.append(self.pasteAct)

        self.clearAct = EricAction(
            QCoreApplication.translate("ViewManager", "Clear"),
            EricPixmapCache.getIcon("editDelete"),
            QCoreApplication.translate("ViewManager", "Clear"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Alt+Shift+C", "Edit|Clear")
            ),
            0,
            self.copyActGrp,
            "vm_edit_clear",
        )
        self.clearAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Clear all text")
        )
        self.clearAct.setWhatsThis(self.tr("""<b>Clear</b><p>Delete all text.</p>"""))
        self.clearAct.triggered.connect(self.__shell.clear)
        self.editActions.append(self.clearAct)

        self.cutAct.setEnabled(False)
        self.copyAct.setEnabled(False)
        self.__shell.copyAvailable.connect(self.cutAct.setEnabled)
        self.__shell.copyAvailable.connect(self.copyAct.setEnabled)

        ####################################################################
        ## Below follow the actions for QScintilla standard commands.
        ####################################################################

        self.esm = QSignalMapper(self)
        self.esm.mappedInt.connect(self.__shell.editorCommand)

        self.editorActGrp = createActionGroup(self)

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
        if not OSUtilities.isMacPlatform():
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
            self.tr("Move forward one history entry"),
            self.tr("Move forward one history entry"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Down")),
            0,
            self.editorActGrp,
            "vm_edit_scroll_down_line",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_LINESCROLLDOWN)
        act.triggered.connect(self.esm.map)
        self.editActions.append(act)

        act = EricAction(
            self.tr("Move back one history entry"),
            self.tr("Move back one history entry"),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Up")),
            0,
            self.editorActGrp,
            "vm_edit_scroll_up_line",
        )
        self.esm.setMapping(act, QsciScintilla.SCI_LINESCROLLUP)
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

    def __createSearchActions(self):
        """
        Private method defining the user interface actions for the search
        commands.
        """
        self.searchActGrp = createActionGroup(self)

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
                """<p>Search for some text in the shell window. A"""
                """ dialog is shown to enter the search text and options"""
                """ for the search.</p>""",
            )
        )
        self.searchAct.triggered.connect(self.__showFind)
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
                """<p>Search the next occurrence of some text in the shell"""
                """ window. The previously entered search text and options are"""
                """ reused.</p>""",
            )
        )
        self.searchNextAct.triggered.connect(
            self.__searchWidget.on_findNextButton_clicked
        )
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
                """<p>Search the previous occurrence of some text in the shell"""
                """ window. The previously entered search text and options are"""
                """ reused.</p>""",
            )
        )
        self.searchPrevAct.triggered.connect(
            self.__searchWidget.on_findPrevButton_clicked
        )
        self.searchActions.append(self.searchPrevAct)

    def __createViewActions(self):
        """
        Private method defining the user interface actions for the view
        commands.
        """
        self.viewActGrp = createActionGroup(self)

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
            self.viewActGrp,
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
            self.viewActGrp,
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
            self.viewActGrp,
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
            self.viewActGrp,
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

    def __createHistoryActions(self):
        """
        Private method defining the user interface actions for the history
        commands.
        """
        self.showHistoryAct = EricAction(
            self.tr("Show History"),
            EricPixmapCache.getIcon("history"),
            self.tr("&Show History..."),
            0,
            0,
            self,
            "shell_show_history",
        )
        self.showHistoryAct.setStatusTip(self.tr("Show the shell history in a dialog"))
        self.showHistoryAct.triggered.connect(self.__shell.showHistory)

        self.clearHistoryAct = EricAction(
            self.tr("Clear History"),
            EricPixmapCache.getIcon("historyClear"),
            self.tr("&Clear History..."),
            0,
            0,
            self,
            "shell_clear_history",
        )
        self.clearHistoryAct.setStatusTip(self.tr("Clear the shell history"))
        self.clearHistoryAct.triggered.connect(self.__shell.clearHistory)

        self.selectHistoryAct = EricAction(
            self.tr("Select History Entry"),
            self.tr("Select History &Entry"),
            0,
            0,
            self,
            "shell_select_history",
        )
        self.selectHistoryAct.setStatusTip(
            self.tr("Select an entry of the shell history")
        )
        self.selectHistoryAct.triggered.connect(self.__shell.selectHistory)

    def __createSettingsActions(self):
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
            "shell_settings_preferences",
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

    def __showFind(self):
        """
        Private method to display the search widget.
        """
        txt = self.__shell.selectedText()
        self.showFind(txt)

    def showFind(self, txt=""):
        """
        Public method to display the search widget.

        @param txt text to be shown in the combo
        @type str
        """
        self.__searchWidget.showFind(txt)

    def activeWindow(self):
        """
        Public method to get a reference to the active shell.

        @return reference to the shell widget
        @rtype Shell
        """
        return self.__shell

    def __readSettings(self):
        """
        Private method to read the settings remembered last time.
        """
        settings = Preferences.getSettings()
        pos = settings.value("ShellWindow/Position", QPoint(0, 0))
        size = settings.value("ShellWindow/Size", QSize(800, 600))
        self.resize(size)
        self.move(pos)

    def __writeSettings(self):
        """
        Private method to write the settings for reuse.
        """
        settings = Preferences.getSettings()
        settings.setValue("ShellWindow/Position", self.pos())
        settings.setValue("ShellWindow/Size", self.size())

    def quit(self):
        """
        Public method to quit the application.
        """
        ericApp().closeAllWindows()

    def __newWindow(self):
        """
        Private slot to start a new instance of eric.
        """
        program = PythonUtilities.getPythonExecutable()
        eric7 = os.path.join(getConfig("ericDir"), "eric7_shell.py")
        args = [eric7]
        QProcess.startDetached(program, args)

    def __virtualEnvironmentChanged(self, venvName):
        """
        Private slot handling a change of the shell's virtual environment.

        @param venvName name of the virtual environment of the shell
        @type str
        """
        if venvName:
            self.setWindowTitle(self.tr("eric Shell [{0}]").format(venvName))
        else:
            self.setWindowTitle(self.tr("eric Shell"))

    ##################################################################
    ## Below are the action methods for the view menu
    ##################################################################

    def __zoomIn(self):
        """
        Private method to handle the zoom in action.
        """
        self.__shell.zoomIn()
        self.__sbZoom.setValue(self.__shell.getZoom())

    def __zoomOut(self):
        """
        Private method to handle the zoom out action.
        """
        self.__shell.zoomOut()
        self.__sbZoom.setValue(self.__shell.getZoom())

    def __zoomReset(self):
        """
        Private method to reset the zoom factor.
        """
        self.__shell.zoomTo(0)
        self.__sbZoom.setValue(self.__shell.getZoom())

    def __zoom(self):
        """
        Private method to handle the zoom action.
        """
        from eric7.QScintilla.ZoomDialog import ZoomDialog

        dlg = ZoomDialog(self.__shell.getZoom(), parent=self, modal=True)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            value = dlg.getZoomSize()
            self.__zoomTo(value)

    def __zoomTo(self, value):
        """
        Private slot to zoom to a given value.

        @param value zoom value to be set
        @type int
        """
        self.__shell.zoomTo(value)
        self.__sbZoom.setValue(self.__shell.getZoom())

    def __zoomValueChanged(self, value):
        """
        Private slot to handle changes of the zoom value.

        @param value new zoom value
        @type int
        """
        self.__sbZoom.setValue(value)

    ##################################################################
    ## Below are the action methods for the help menu
    ##################################################################

    def __about(self):
        """
        Private slot to show a little About message.
        """
        EricMessageBox.about(
            self,
            self.tr("About eric Shell Window"),
            self.tr(
                "The eric Shell is a standalone shell window."
                " It uses the same backend as the debugger of"
                " the full IDE, but is executed independently."
            ),
        )

    def __aboutQt(self):
        """
        Private slot to handle the About Qt dialog.
        """
        EricMessageBox.aboutQt(self, "eric Shell Window")

    def __whatsThis(self):
        """
        Private slot called in to enter Whats This mode.
        """
        QWhatsThis.enterWhatsThisMode()

    ##################################################################
    ## Below are the main menu handling methods
    ##################################################################

    def __createMenus(self):
        """
        Private method to create the menus of the menu bar.
        """
        self.__fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self.__fileMenu.setTearOffEnabled(True)
        self.__fileMenu.addAction(self.newWindowAct)
        self.__fileMenu.addSeparator()
        self.__fileMenu.addAction(self.restartAct)
        self.__fileMenu.addAction(self.clearRestartAct)
        self.__fileMenu.addSeparator()
        self.__fileMenu.addAction(self.saveContentsAct)
        self.__fileMenu.addSeparator()
        self.__fileMenu.addAction(self.exitAct)

        self.__editMenu = self.menuBar().addMenu(self.tr("&Edit"))
        self.__editMenu.setTearOffEnabled(True)
        self.__editMenu.addAction(self.cutAct)
        self.__editMenu.addAction(self.copyAct)
        self.__editMenu.addAction(self.pasteAct)
        self.__editMenu.addAction(self.clearAct)
        self.__editMenu.addSeparator()
        self.__editMenu.addAction(self.searchAct)
        self.__editMenu.addAction(self.searchNextAct)
        self.__editMenu.addAction(self.searchPrevAct)

        self.__viewMenu = self.menuBar().addMenu(self.tr("&View"))
        self.__viewMenu.setTearOffEnabled(True)
        self.__viewMenu.addAction(self.zoomInAct)
        self.__viewMenu.addAction(self.zoomOutAct)
        self.__viewMenu.addAction(self.zoomResetAct)
        self.__viewMenu.addAction(self.zoomToAct)

        self.__historyMenu = self.menuBar().addMenu(self.tr("Histor&y"))
        self.__historyMenu.setTearOffEnabled(True)
        self.__historyMenu.addAction(self.selectHistoryAct)
        self.__historyMenu.addAction(self.showHistoryAct)
        self.__historyMenu.addAction(self.clearHistoryAct)
        self.__historyMenu.setEnabled(self.__shell.isHistoryEnabled())

        self.__startMenu = self.menuBar().addMenu(self.tr("&Start"))
        self.__startMenu.aboutToShow.connect(self.__showStartMenu)
        self.__startMenu.triggered.connect(self.__startShell)

        self.__settingsMenu = self.menuBar().addMenu(self.tr("Se&ttings"))
        self.__settingsMenu.setTearOffEnabled(True)
        self.__settingsMenu.addAction(self.prefAct)

        self.menuBar().addSeparator()

        self.__helpMenu = self.menuBar().addMenu(self.tr("&Help"))
        self.__helpMenu.setTearOffEnabled(True)
        self.__helpMenu.addAction(self.aboutAct)
        self.__helpMenu.addAction(self.aboutQtAct)
        self.__helpMenu.addSeparator()
        self.__helpMenu.addAction(self.whatsThisAct)

    def __showStartMenu(self):
        """
        Private slot to prepare the language menu.
        """
        self.__startMenu.clear()
        for venvName in sorted(
            self.virtualenvManager.getVirtualenvNames(noServer=True)
        ):
            self.__startMenu.addAction(venvName)

    def __startShell(self, action):
        """
        Private slot to start a shell according to the action triggered.

        @param action menu action that was triggered
        @type QAction
        """
        venvName = action.text()
        self.__debugServer.startClient(False, venvName=venvName)
        self.__debugServer.remoteBanner()

    ##################################################################
    ## Below are the toolbar handling methods
    ##################################################################

    def __createToolBars(self):
        """
        Private method to create the various toolbars.
        """
        filetb = self.addToolBar(self.tr("File"))
        filetb.addAction(self.newWindowAct)
        filetb.addSeparator()
        filetb.addAction(self.restartAct)
        filetb.addAction(self.clearRestartAct)
        filetb.addSeparator()
        filetb.addAction(self.saveContentsAct)
        filetb.addSeparator()
        filetb.addAction(self.exitAct)

        edittb = self.addToolBar(self.tr("Edit"))
        edittb.addAction(self.cutAct)
        edittb.addAction(self.copyAct)
        edittb.addAction(self.pasteAct)
        edittb.addAction(self.clearAct)

        findtb = self.addToolBar(self.tr("Find"))
        findtb.addAction(self.searchAct)
        findtb.addAction(self.searchNextAct)
        findtb.addAction(self.searchPrevAct)

        viewtb = self.addToolBar(self.tr("View"))
        viewtb.addAction(self.zoomInAct)
        viewtb.addAction(self.zoomOutAct)
        viewtb.addAction(self.zoomResetAct)
        viewtb.addAction(self.zoomToAct)

        self.__historyToolbar = self.addToolBar(self.tr("History"))
        self.__historyToolbar.addAction(self.showHistoryAct)
        self.__historyToolbar.addAction(self.clearHistoryAct)
        self.__historyToolbar.setEnabled(self.__shell.isHistoryEnabled())

        helptb = self.addToolBar(self.tr("Help"))
        helptb.addAction(self.whatsThisAct)

    ##################################################################
    ## Below are the status bar handling methods
    ##################################################################

    def __createStatusBar(self):
        """
        Private slot to set up the status bar.
        """
        self.__statusBar = self.statusBar()
        self.__statusBar.setSizeGripEnabled(True)

        self.__sbZoom = EricZoomWidget(
            EricPixmapCache.getPixmap("zoomOut"),
            EricPixmapCache.getPixmap("zoomIn"),
            EricPixmapCache.getPixmap("zoomReset"),
            self.__statusBar,
        )
        self.__statusBar.addPermanentWidget(self.__sbZoom)
        self.__sbZoom.setWhatsThis(
            self.tr("""<p>This part of the status bar allows zooming the  shell.</p>""")
        )

        self.__sbZoom.valueChanged.connect(self.__zoomTo)
        self.__sbZoom.setValue(0)

    @pyqtSlot(ShellHistoryStyle)
    def __historyStyleChanged(self, _historyStyle):
        """
        Private slot to handle a change of the shell history style.

        @param _historyStyle style to be used for the history (unused)
        @type ShellHistoryStyle
        """
        enabled = self.__shell.isHistoryEnabled()
        self.__historyMenu.setEnabled(enabled)
        self.__historyToolbar.setEnabled(enabled)

    @pyqtSlot()
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
            fromEric=False,
            displayMode=ConfigurationMode.SHELLMODE,
        )
        dlg.show()
        dlg.showConfigurationPageByName("0shellPage")
        dlg.exec()
        if dlg.result() == QDialog.DialogCode.Accepted:
            dlg.setPreferences()
            Preferences.syncPreferences()
            self.__shell.handlePreferencesChanged()
