# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the hex editor main window.
"""

import contextlib
import os
import pathlib

from PyQt6.QtCore import QCoreApplication, QLocale, QSize, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QMenu,
    QVBoxLayout,
    QWhatsThis,
    QWidget,
)

from eric7 import EricUtilities, Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricClickableLabel import EricClickableLabel
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.Globals import recentNameHexFiles, strGroup
from eric7.RemoteServerInterface import EricServerFileDialog
from eric7.SystemUtilities import FileSystemUtilities

from .HexEditGotoWidget import HexEditGotoWidget
from .HexEditSearchReplaceWidget import HexEditSearchReplaceWidget
from .HexEditWidget import HexEditWidget


class HexEditMainWindow(EricMainWindow):
    """
    Class implementing the hex editor main window.

    @signal editorClosed() emitted after the window was requested to close
    """

    editorClosed = pyqtSignal()

    windows = []

    maxMenuFilePathLen = 75

    def __init__(self, fileName="", parent=None, fromEric=False, project=None):
        """
        Constructor

        @param fileName name of a file to load on startup
        @type str
        @param parent parent widget of this window
        @type QWidget
        @param fromEric flag indicating whether it was called from within
            eric
        @type bool
        @param project reference to the project object
        @type Project
        """
        super().__init__(parent)
        self.setObjectName("eric7_hex_editor")

        self.__srHistory = {
            "search": [],
            # list of recent searches (tuple of format type index and
            # search term)
            "replace": [],
            # list of recent replaces (tuple of format type index and
            # replace term
        }

        self.__fromEric = fromEric
        self.setWindowIcon(EricPixmapCache.getIcon("hexEditor"))

        if not self.__fromEric:
            self.setStyle(
                styleName=Preferences.getUI("Style"),
                styleSheetFile=Preferences.getUI("StyleSheet"),
                itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
            )

        self.__remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
            if self.__fromEric
            else None
        )

        self.__editor = HexEditWidget()
        self.__searchWidget = HexEditSearchReplaceWidget(self.__editor, self, False)
        self.__replaceWidget = HexEditSearchReplaceWidget(self.__editor, self, True)
        self.__gotoWidget = HexEditGotoWidget(self.__editor)
        cw = QWidget()
        layout = QVBoxLayout(cw)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)
        layout.addWidget(self.__editor)
        layout.addWidget(self.__searchWidget)
        layout.addWidget(self.__gotoWidget)
        cw.setLayout(layout)
        layout.addWidget(self.__replaceWidget)
        self.__searchWidget.hide()
        self.__replaceWidget.hide()
        self.__gotoWidget.hide()
        self.setCentralWidget(cw)

        g = Preferences.getGeometry("HexEditorGeometry")
        if g.isEmpty():
            s = QSize(600, 500)
            self.resize(s)
        else:
            self.restoreGeometry(g)

        self.__initActions()
        self.__initMenus()
        self.__initToolbars()
        self.__createStatusBar()

        HexEditMainWindow.windows.append(self)

        state = Preferences.getHexEditor("HexEditorState")
        self.restoreState(state)

        self.__editor.currentAddressChanged.connect(self.__showAddress)
        self.__editor.selectionAvailable.connect(self.__showSelectionInfo)
        self.__editor.currentSizeChanged.connect(self.__showSize)
        self.__editor.dataChanged.connect(self.__modificationChanged)
        self.__editor.overwriteModeChanged.connect(self.__showEditMode)
        self.__editor.readOnlyChanged.connect(self.__showReadOnlyMode)
        self.__editor.readOnlyChanged.connect(self.__checkActions)

        self.preferencesChanged()
        self.__editor.setOverwriteMode(Preferences.getHexEditor("OpenInOverwriteMode"))

        self.__project = project
        self.__lastOpenPath = ""
        self.__lastSavePath = ""

        self.__recent = []
        self.__loadRecent()

        self.__setCurrentFile("")
        if fileName:
            self.__loadHexFile(fileName)

        self.__checkActions()

    def __initActions(self):
        """
        Private method to define the user interface actions.
        """
        # list of all actions
        self.__actions = []

        self.__initFileActions()
        self.__initEditActions()
        self.__initHelpActions()
        if not self.__fromEric:
            self.__initConfigActions()

    def __initFileActions(self):
        """
        Private method to define the file related user interface actions.
        """
        self.newWindowAct = EricAction(
            self.tr("New Window"),
            EricPixmapCache.getIcon("newWindow"),
            self.tr("New &Window"),
            0,
            0,
            self,
            "hexEditor_file_new_window",
        )
        self.newWindowAct.setStatusTip(
            self.tr("Open a binary file for editing in a new hex editor window")
        )
        self.newWindowAct.setWhatsThis(
            self.tr(
                """<b>New Window</b>"""
                """<p>This opens a binary file for editing in a new hex editor"""
                """ window.</p>"""
            )
        )
        self.newWindowAct.triggered.connect(self.__openHexFileNewWindow)
        self.__actions.append(self.newWindowAct)

        # correct texts will be set later
        self.openAct = EricAction(
            self.tr("Open"),
            EricPixmapCache.getIcon("open"),
            self.tr("&Open..."),
            QKeySequence(self.tr("Ctrl+O", "File|Open")),
            0,
            self,
            "hexEditor_file_open",
        )
        self.openAct.triggered.connect(self.__openHexFile)
        self.__actions.append(self.openAct)

        # correct texts will be set later
        self.openReadOnlyAct = EricAction(
            "", "", 0, 0, self, "hexEditor_file_open_read_only"
        )
        self.openReadOnlyAct.triggered.connect(self.__openHexFileReadOnly)
        self.__actions.append(self.openReadOnlyAct)

        self.saveAct = EricAction(
            self.tr("Save"),
            EricPixmapCache.getIcon("fileSave"),
            self.tr("&Save"),
            QKeySequence(self.tr("Ctrl+S", "File|Save")),
            0,
            self,
            "hexEditor_file_save",
        )
        self.saveAct.setStatusTip(self.tr("Save the current binary file"))
        self.saveAct.setWhatsThis(
            self.tr(
                """<b>Save File</b>"""
                """<p>Save the contents of the hex editor window.</p>"""
            )
        )
        self.saveAct.triggered.connect(self.__saveHexFile)
        self.__actions.append(self.saveAct)

        self.saveAsAct = EricAction(
            self.tr("Save As"),
            EricPixmapCache.getIcon("fileSaveAs"),
            self.tr("Save &As..."),
            QKeySequence(self.tr("Shift+Ctrl+S", "File|Save As")),
            0,
            self,
            "hexEditor_file_save_as",
        )
        self.saveAsAct.setStatusTip(
            self.tr("Save the current binary data to a new file")
        )
        self.saveAsAct.setWhatsThis(
            self.tr(
                """<b>Save As...</b>"""
                """<p>Saves the current binary data to a new file.</p>"""
            )
        )
        self.saveAsAct.triggered.connect(self.__saveHexFileAs)
        self.__actions.append(self.saveAsAct)

        self.saveReadableAct = EricAction(
            self.tr("Save As Readable"),
            self.tr("Save As &Readable..."),
            0,
            0,
            self,
            "hexEditor_file_save_readable",
        )
        self.saveReadableAct.setStatusTip(
            self.tr("Save the current binary data to a new file in a readable format")
        )
        self.saveReadableAct.setWhatsThis(
            self.tr(
                """<b>Save As Readable...</b>"""
                """<p>Saves the current binary data to a new file in a readable"""
                """ format.</p>"""
            )
        )
        self.saveReadableAct.triggered.connect(self.__saveHexFileReadable)
        self.__actions.append(self.saveReadableAct)

        self.closeAct = EricAction(
            self.tr("Close"),
            EricPixmapCache.getIcon("close"),
            self.tr("&Close"),
            QKeySequence(self.tr("Ctrl+W", "File|Close")),
            0,
            self,
            "hexEditor_file_close",
        )
        self.closeAct.setStatusTip(self.tr("Close the current hex editor window"))
        self.closeAct.setWhatsThis(
            self.tr("""<b>Close</b><p>Closes the current hex editor window.</p>""")
        )
        self.closeAct.triggered.connect(self.close)
        self.__actions.append(self.closeAct)

        self.closeAllAct = EricAction(
            self.tr("Close All"),
            self.tr("Close &All"),
            0,
            0,
            self,
            "hexEditor_file_close_all",
        )
        self.closeAllAct.setStatusTip(self.tr("Close all hex editor windows"))
        self.closeAllAct.setWhatsThis(
            self.tr("""<b>Close All</b><p>Closes all hex editor windows.</p>""")
        )
        self.closeAllAct.triggered.connect(self.__closeAll)
        self.__actions.append(self.closeAllAct)

        self.closeOthersAct = EricAction(
            self.tr("Close Others"),
            self.tr("Close Others"),
            0,
            0,
            self,
            "hexEditor_file_close_others",
        )
        self.closeOthersAct.setStatusTip(self.tr("Close all other hex editor windows"))
        self.closeOthersAct.setWhatsThis(
            self.tr(
                """<b>Close Others</b>"""
                """<p>Closes all other hex editor windows.</p>"""
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
            "hexEditor_file_quit",
        )
        self.exitAct.setStatusTip(self.tr("Quit the hex editor"))
        self.exitAct.setWhatsThis(self.tr("""<b>Quit</b><p>Quit the hex editor.</p>"""))
        if not self.__fromEric:
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
            "hexEditor_edit_undo",
        )
        self.undoAct.setStatusTip(self.tr("Undo the last change"))
        self.undoAct.setWhatsThis(
            self.tr("""<b>Undo</b><p>Undo the last change done.</p>""")
        )
        self.undoAct.triggered.connect(self.__editor.undo)
        self.__actions.append(self.undoAct)

        self.redoAct = EricAction(
            self.tr("Redo"),
            EricPixmapCache.getIcon("editRedo"),
            self.tr("&Redo"),
            QKeySequence(self.tr("Ctrl+Shift+Z", "Edit|Redo")),
            0,
            self,
            "hexEditor_edit_redo",
        )
        self.redoAct.setStatusTip(self.tr("Redo the last change"))
        self.redoAct.setWhatsThis(
            self.tr("""<b>Redo</b><p>Redo the last change done.</p>""")
        )
        self.redoAct.triggered.connect(self.__editor.redo)
        self.__actions.append(self.redoAct)

        self.revertAct = EricAction(
            self.tr("Revert to last saved state"),
            self.tr("Re&vert to last saved state"),
            QKeySequence(self.tr("Ctrl+Y", "Edit|Revert")),
            0,
            self,
            "hexEditor_edit_revert",
        )
        self.revertAct.setStatusTip(self.tr("Revert to last saved state"))
        self.revertAct.setWhatsThis(
            self.tr(
                """<b>Revert to last saved state</b>"""
                """<p>Undo all changes up to the last saved state of the"""
                """ editor.</p>"""
            )
        )
        self.revertAct.triggered.connect(self.__editor.revertToUnmodified)
        self.__actions.append(self.revertAct)

        self.cutAct = EricAction(
            self.tr("Cut"),
            EricPixmapCache.getIcon("editCut"),
            self.tr("Cu&t"),
            QKeySequence(self.tr("Ctrl+X", "Edit|Cut")),
            QKeySequence(self.tr("Shift+Del", "Edit|Cut")),
            self,
            "hexEditor_edit_cut",
        )
        self.cutAct.setStatusTip(self.tr("Cut the selection"))
        self.cutAct.setWhatsThis(
            self.tr(
                """<b>Cut</b>"""
                """<p>Cut the selected binary area to the clipboard.</p>"""
            )
        )
        self.cutAct.triggered.connect(self.__editor.cut)
        self.__actions.append(self.cutAct)

        self.copyAct = EricAction(
            self.tr("Copy"),
            EricPixmapCache.getIcon("editCopy"),
            self.tr("&Copy"),
            QKeySequence(self.tr("Ctrl+C", "Edit|Copy")),
            QKeySequence(self.tr("Ctrl+Ins", "Edit|Copy")),
            self,
            "hexEditor_edit_copy",
        )
        self.copyAct.setStatusTip(self.tr("Copy the selection"))
        self.copyAct.setWhatsThis(
            self.tr(
                """<b>Copy</b>"""
                """<p>Copy the selected binary area to the clipboard.</p>"""
            )
        )
        self.copyAct.triggered.connect(self.__editor.copy)
        self.__actions.append(self.copyAct)

        self.pasteAct = EricAction(
            self.tr("Paste"),
            EricPixmapCache.getIcon("editPaste"),
            self.tr("&Paste"),
            QKeySequence(self.tr("Ctrl+V", "Edit|Paste")),
            QKeySequence(self.tr("Shift+Ins", "Edit|Paste")),
            self,
            "hexEditor_edit_paste",
        )
        self.pasteAct.setStatusTip(self.tr("Paste the clipboard contents"))
        self.pasteAct.setWhatsThis(
            self.tr("""<b>Paste</b><p>Paste the clipboard contents.</p>""")
        )
        self.pasteAct.triggered.connect(self.__editor.paste)
        self.__actions.append(self.pasteAct)

        self.selectAllAct = EricAction(
            self.tr("Select All"),
            EricPixmapCache.getIcon("editSelectAll"),
            self.tr("&Select All"),
            QKeySequence(self.tr("Ctrl+A", "Edit|Select All")),
            0,
            self,
            "hexEditor_edit_select_all",
        )
        self.selectAllAct.setStatusTip(self.tr("Select the complete binary data"))
        self.selectAllAct.setWhatsThis(
            self.tr("""<b>Select All</b><p>Selects the complete binary data.</p>""")
        )
        self.selectAllAct.triggered.connect(self.__editor.selectAll)
        self.__actions.append(self.selectAllAct)

        self.deselectAllAct = EricAction(
            self.tr("Deselect all"),
            self.tr("&Deselect all"),
            QKeySequence(self.tr("Alt+Ctrl+A", "Edit|Deselect all")),
            0,
            self,
            "hexEditor_edit_deselect_all",
        )
        self.deselectAllAct.setStatusTip(self.tr("Deselect all binary data"))
        self.deselectAllAct.setWhatsThis(
            self.tr("""<b>Deselect All</b><p>Deselect all all binary data.</p>""")
        )
        self.deselectAllAct.triggered.connect(self.__editor.deselectAll)
        self.__actions.append(self.deselectAllAct)

        self.saveSelectionReadableAct = EricAction(
            self.tr("Save Selection Readable"),
            self.tr("Save Selection Readable..."),
            0,
            0,
            self,
            "hexEditor_edit_selection_save_readable",
        )
        self.saveSelectionReadableAct.setStatusTip(
            self.tr(
                "Save the binary data of the current selection to a file"
                " in a readable format"
            )
        )
        self.saveSelectionReadableAct.setWhatsThis(
            self.tr(
                """<b>Save Selection Readable...</b>"""
                """<p>Saves the binary data of the current selection to a file"""
                """ in a readable format.</p>"""
            )
        )
        self.saveSelectionReadableAct.triggered.connect(self.__saveSelectionReadable)
        self.__actions.append(self.saveSelectionReadableAct)

        self.readonlyAct = EricAction(
            self.tr("Set Read Only"),
            self.tr("Set Read Only"),
            0,
            0,
            self,
            "hexEditor_edit_readonly",
            True,
        )
        self.readonlyAct.setStatusTip(self.tr("Change the edit mode to read only"))
        self.readonlyAct.setWhatsThis(
            self.tr(
                """<b>Set Read Only</b>"""
                """<p>This changes the edit mode to read only (i.e. to view"""
                """ mode).</p>"""
            )
        )
        self.readonlyAct.setChecked(False)
        self.readonlyAct.toggled[bool].connect(self.__editor.setReadOnly)
        self.__editor.readOnlyChanged.connect(self.readonlyAct.setChecked)
        self.__actions.append(self.readonlyAct)

        self.searchAct = EricAction(
            self.tr("Search"),
            EricPixmapCache.getIcon("find"),
            self.tr("&Search..."),
            QKeySequence(self.tr("Ctrl+F", "Search|Search")),
            0,
            self,
            "hexEditor_edit_search",
        )
        self.searchAct.setStatusTip(self.tr("Search for data"))
        self.searchAct.setWhatsThis(
            self.tr(
                """<b>Search</b>"""
                """<p>Search for some data. A dialog is shown to enter the"""
                """ data to search for in various formats.</p>"""
            )
        )
        self.searchAct.triggered.connect(self.__search)
        self.__actions.append(self.searchAct)

        self.searchNextAct = EricAction(
            self.tr("Search next"),
            EricPixmapCache.getIcon("findNext"),
            self.tr("Search &next"),
            QKeySequence(self.tr("F3", "Search|Search next")),
            0,
            self,
            "hexEditor_edit_search_next",
        )
        self.searchNextAct.setStatusTip(self.tr("Search next occurrence"))
        self.searchNextAct.setWhatsThis(
            self.tr(
                """<b>Search next</b>"""
                """<p>Search the next occurrence of some data. The previously"""
                """ entered search data are reused.</p>"""
            )
        )
        self.searchNextAct.triggered.connect(self.__searchWidget.findPrevNext)
        self.__actions.append(self.searchNextAct)

        self.searchPrevAct = EricAction(
            self.tr("Search previous"),
            EricPixmapCache.getIcon("findPrev"),
            self.tr("Search &previous"),
            QKeySequence(self.tr("Shift+F3", "Search|Search previous")),
            0,
            self,
            "hexEditor_edit_search_previous",
        )
        self.searchPrevAct.setStatusTip(self.tr("Search previous occurrence"))
        self.searchPrevAct.setWhatsThis(
            self.tr(
                """<b>Search previous</b>"""
                """<p>Search the previous occurrence of some data. The"""
                """ previously entered search data are reused.</p>"""
            )
        )
        self.searchPrevAct.triggered.connect(
            lambda: self.__searchWidget.findPrevNext(True)
        )
        self.__actions.append(self.searchPrevAct)

        self.replaceAct = EricAction(
            self.tr("Replace"),
            self.tr("&Replace..."),
            QKeySequence(self.tr("Ctrl+R", "Search|Replace")),
            0,
            self,
            "hexEditor_edit_search_replace",
        )
        self.replaceAct.setStatusTip(self.tr("Replace data"))
        self.replaceAct.setWhatsThis(
            self.tr(
                """<b>Replace</b>"""
                """<p>Search for some data and replace it."""
                """ A dialog is shown to enter the data to search for and the"""
                """ replacement data in various formats.</p>"""
            )
        )
        self.replaceAct.triggered.connect(self.__replace)
        self.__actions.append(self.replaceAct)

        self.gotoAct = EricAction(
            self.tr("Goto Offset"),
            EricPixmapCache.getIcon("goto"),
            self.tr("&Goto Offset..."),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+G", "Search|Goto Offset"
                )
            ),
            0,
            self,
            "hexEditor_edit_goto",
        )
        self.gotoAct.setStatusTip(self.tr("Goto Offset"))
        self.gotoAct.setWhatsThis(
            self.tr(
                """<b>Goto Offset</b>"""
                """<p>Go to a specific address. A dialog is shown to enter"""
                """ the movement data.</p>"""
            )
        )
        self.gotoAct.triggered.connect(self.__goto)
        self.__actions.append(self.gotoAct)

        self.redoAct.setEnabled(False)
        self.__editor.canRedoChanged.connect(self.redoAct.setEnabled)

        self.undoAct.setEnabled(False)
        self.__editor.canUndoChanged.connect(self.undoAct.setEnabled)

        self.revertAct.setEnabled(False)
        self.__editor.dataChanged.connect(self.revertAct.setEnabled)

        self.cutAct.setEnabled(False)
        self.copyAct.setEnabled(False)
        self.saveSelectionReadableAct.setEnabled(False)
        self.__editor.selectionAvailable.connect(self.__checkActions)
        self.__editor.selectionAvailable.connect(self.copyAct.setEnabled)
        self.__editor.selectionAvailable.connect(
            self.saveSelectionReadableAct.setEnabled
        )

    def __initHelpActions(self):
        """
        Private method to create the Help actions.
        """
        self.aboutAct = EricAction(
            self.tr("About"), self.tr("&About"), 0, 0, self, "hexEditor_help_about"
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
            "hexEditor_help_about_qt",
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
            "hexEditor_help_whats_this",
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

    def __initConfigActions(self):
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
        self.__actions.append(self.prefAct)

    def __setReadOnlyActionTexts(self):
        """
        Private method to switch the 'Open Read Only' action between
        'read only' and 'read write'.
        """
        if Preferences.getHexEditor("OpenReadOnly"):
            self.openAct.setStatusTip(self.tr("Open a binary file for viewing"))
            self.openAct.setWhatsThis(
                self.tr(
                    """<b>Open File</b>"""
                    """<p>This opens a binary file for viewing (i.e. in read"""
                    """ only mode). It pops up a file selection dialog.</p>"""
                )
            )

            self.openReadOnlyAct.setText(self.tr("Open for Editing..."))
            self.openReadOnlyAct.setIconText(self.tr("Open for Editing"))
            self.openReadOnlyAct.setStatusTip(self.tr("Open a binary file for editing"))
            self.openReadOnlyAct.setWhatsThis(
                self.tr(
                    """<b>Open for Editing</b>"""
                    """<p>This opens a binary file for editing."""
                    """ It pops up a file selection dialog.</p>"""
                )
            )
        else:
            self.openAct.setStatusTip(self.tr("Open a binary file for editing"))
            self.openAct.setWhatsThis(
                self.tr(
                    """<b>Open File</b>"""
                    """<p>This opens a binary file for editing."""
                    """ It pops up a file selection dialog.</p>"""
                )
            )

            self.openReadOnlyAct.setText(self.tr("Open Read Only..."))
            self.openReadOnlyAct.setIconText(self.tr("Open Read Only"))
            self.openReadOnlyAct.setStatusTip(self.tr("Open a binary file for viewing"))
            self.openReadOnlyAct.setWhatsThis(
                self.tr(
                    """<b>Open Read Only</b>"""
                    """<p>This opens a binary file for viewing (i.e. in read"""
                    """ only mode). It pops up a file selection dialog.</p>"""
                )
            )

    def __initMenus(self):
        """
        Private method to create the menus.
        """
        mb = self.menuBar()

        menu = mb.addMenu(self.tr("&File"))
        menu.setTearOffEnabled(True)
        self.__recentMenu = QMenu(self.tr("Open &Recent Files"), menu)
        menu.addAction(self.newWindowAct)
        menu.addAction(self.openAct)
        menu.addAction(self.openReadOnlyAct)
        self.__menuRecentAct = menu.addMenu(self.__recentMenu)
        menu.addSeparator()
        menu.addAction(self.saveAct)
        menu.addAction(self.saveAsAct)
        menu.addAction(self.saveReadableAct)
        menu.addSeparator()
        menu.addAction(self.closeAct)
        menu.addAction(self.closeOthersAct)
        if self.__fromEric:
            menu.addAction(self.closeAllAct)
        else:
            menu.addSeparator()
            menu.addAction(self.exitAct)
        menu.aboutToShow.connect(self.__showFileMenu)
        self.__recentMenu.aboutToShow.connect(self.__showRecentMenu)
        self.__recentMenu.triggered.connect(self.__openRecentHexFile)

        menu = mb.addMenu(self.tr("&Edit"))
        menu.setTearOffEnabled(True)
        menu.addAction(self.undoAct)
        menu.addAction(self.redoAct)
        menu.addAction(self.revertAct)
        menu.addSeparator()
        menu.addAction(self.cutAct)
        menu.addAction(self.copyAct)
        menu.addAction(self.pasteAct)
        menu.addSeparator()
        menu.addAction(self.selectAllAct)
        menu.addAction(self.deselectAllAct)
        menu.addAction(self.saveSelectionReadableAct)
        menu.addSeparator()
        menu.addAction(self.searchAct)
        menu.addAction(self.searchNextAct)
        menu.addAction(self.searchPrevAct)
        menu.addAction(self.replaceAct)
        menu.addSeparator()
        menu.addAction(self.gotoAct)
        menu.addSeparator()
        menu.addAction(self.readonlyAct)

        if not self.__fromEric:
            menu = mb.addMenu(self.tr("Se&ttings"))
            menu.setTearOffEnabled(True)
            menu.addAction(self.prefAct)

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
        filetb.addAction(self.newWindowAct)
        filetb.addAction(self.openAct)
        filetb.addSeparator()
        filetb.addAction(self.saveAct)
        filetb.addAction(self.saveAsAct)
        filetb.addSeparator()
        filetb.addAction(self.closeAct)
        if not self.__fromEric:
            filetb.addAction(self.exitAct)

        edittb = self.addToolBar(self.tr("Edit"))
        edittb.setObjectName("EditToolBar")
        edittb.addAction(self.undoAct)
        edittb.addAction(self.redoAct)
        edittb.addSeparator()
        edittb.addAction(self.cutAct)
        edittb.addAction(self.copyAct)
        edittb.addAction(self.pasteAct)

        searchtb = self.addToolBar(self.tr("Find"))
        searchtb.setObjectName("SearchToolBar")
        searchtb.addAction(self.searchAct)
        searchtb.addAction(self.searchNextAct)
        searchtb.addAction(self.searchPrevAct)

        if not self.__fromEric:
            settingstb = self.addToolBar(self.tr("Settings"))
            settingstb.setObjectName("SettingsToolBar")
            settingstb.addAction(self.prefAct)

        helptb = self.addToolBar(self.tr("Help"))
        helptb.setObjectName("HelpToolBar")
        helptb.addAction(self.whatsThisAct)

    def __createStatusBar(self):
        """
        Private method to initialize the status bar.
        """
        self.__statusBar = self.statusBar()
        self.__statusBar.setSizeGripEnabled(True)

        self.__sbAddress = QLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.__sbAddress)
        self.__sbAddress.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays the cursor"""
                """ address.</p>"""
            )
        )
        self.__sbAddress.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)

        self.__sbSelection = QLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.__sbSelection)
        self.__sbSelection.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays some selection"""
                """ information.</p>"""
            )
        )
        self.__sbSelection.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)

        self.__sbSize = QLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.__sbSize)
        self.__sbSize.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays the size of the"""
                """ binary data.</p>"""
            )
        )
        self.__sbSize.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)

        self.__sbEditMode = EricClickableLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.__sbEditMode)
        self.__sbEditMode.setWhatsThis(
            self.tr("""<p>This part of the status bar displays the edit mode.</p>""")
        )
        self.__sbEditMode.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)
        self.__sbEditMode.clicked.connect(self.__toggleEditMode)

        self.__sbReadOnly = EricClickableLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.__sbReadOnly)
        self.__sbReadOnly.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays the read"""
                """ only mode.</p>"""
            )
        )
        self.__sbReadOnly.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)
        self.__sbReadOnly.clicked.connect(self.__toggleReadOnlyMode)

        self.__showEditMode(self.__editor.overwriteMode())
        self.__showReadOnlyMode(self.__editor.isReadOnly())

    @pyqtSlot(int)
    def __showAddress(self, address):
        """
        Private slot to show the address of the cursor position.

        @param address address of the cursor
        @type int
        """
        txt = "{0:0{1}x}".format(address, self.__editor.addressWidth())
        txt = strGroup(txt, ":", 4)
        self.__sbAddress.setText(self.tr("Address: {0}").format(txt))

    @pyqtSlot(bool)
    def __showSelectionInfo(self, avail):
        """
        Private slot to show selection information.

        @param avail flag indicating the availability of a selection.
        @type bool
        """
        if avail:
            addrWidth = self.__editor.addressWidth()
            start = "{0:0{1}x}".format(self.__editor.getSelectionBegin(), addrWidth)
            start = strGroup(start, ":", 4)
            end = "{0:0{1}x}".format(self.__editor.getSelectionEnd(), addrWidth)
            end = strGroup(end, ":", 4)
            slen = self.__editor.getSelectionLength()
            self.__sbSelection.setText(
                self.tr(
                    "Selection: {0} - {1} ({2} Bytes)",
                    "0: start, 1: end, 2: selection length",
                ).format(start, end, QLocale().toString(slen))
            )
        else:
            self.__sbSelection.setText(
                self.tr("Selection: -", "no selection available")
            )

    @pyqtSlot(bool)
    def __showReadOnlyMode(self, on):
        """
        Private slot to show the read only mode.

        @param on flag indicating the read only state
        @type bool
        """
        self.__sbReadOnly.setText(self.tr("ro") if on else self.tr("rw"))

    @pyqtSlot()
    def __toggleReadOnlyMode(self):
        """
        Private slot to toggle the read only mode upon a click on the status
        bar label.
        """
        self.__editor.setReadOnly(not self.__editor.isReadOnly())

    @pyqtSlot(bool)
    def __showEditMode(self, overwrite):
        """
        Private slot to show the edit mode.

        @param overwrite flag indicating overwrite mode
        @type bool
        """
        self.__sbEditMode.setText(
            self.tr("Overwrite") if overwrite else self.tr("Insert")
        )

    @pyqtSlot()
    def __toggleEditMode(self):
        """
        Private slot to toggle the edit mode upon a click on the status bar
        label.
        """
        self.__editor.setOverwriteMode(not self.__editor.overwriteMode())

    @pyqtSlot(int)
    def __showSize(self, size):
        """
        Private slot to show the binary data size.

        @param size size of the binary data
        @type int
        """
        self.__sbSize.setText(self.tr("Size: {0}").format(QLocale().toString(size)))

    def closeEvent(self, evt):
        """
        Protected event handler for the close event.

        @param evt reference to the close event
            <br />This event is simply accepted after the history has been
            saved and all window references have been deleted.
        @type QCloseEvent
        """
        if self.__maybeSave():
            state = self.saveState()
            Preferences.setHexEditor("HexEditorState", state)

            Preferences.setGeometry("HexEditorGeometry", self.saveGeometry())

            with contextlib.suppress(ValueError):
                if self.__fromEric or len(HexEditMainWindow.windows) > 1:
                    HexEditMainWindow.windows.remove(self)

            if not self.__fromEric:
                Preferences.syncPreferences()

            self.__saveRecent()

            evt.accept()
            self.editorClosed.emit()
        else:
            evt.ignore()

    def __openHexFileNewWindow(self):
        """
        Private slot called to open a binary file in new hex editor window.
        """
        if (
            not self.__lastOpenPath
            and self.__project is not None
            and self.__project.isOpen()
        ):
            self.__lastOpenPath = self.__project.getProjectPath()

        fileName = (
            EricServerFileDialog.getOpenFileName(
                self,
                self.tr("Open binary file"),
                self.__lastOpenPath,
                self.tr("All Files (*)"),
            )
            if FileSystemUtilities.isRemoteFileName(self.__lastOpenPath)
            else EricFileDialog.getOpenFileName(
                self,
                self.tr("Open binary file in new window"),
                self.__lastOpenPath,
                self.tr("All Files (*)"),
            )
        )
        if fileName:
            he = HexEditMainWindow(
                fileName=fileName,
                parent=self.parent(),
                fromEric=self.__fromEric,
                project=self.__project,
            )
            he.setRecentPaths("", self.__lastSavePath)
            he.show()

    def __maybeSave(self):
        """
        Private method to ask the user to save the file, if it was modified.

        @return flag indicating, if it is ok to continue
        @rtype bool
        """
        if self.__editor.isModified():
            ret = EricMessageBox.okToClearData(
                self,
                self.tr("eric Hex Editor"),
                self.tr("""The loaded file has unsaved changes."""),
                self.__saveHexFile,
            )
            if not ret:
                return False
        return True

    def __loadHexFile(self, fileName):
        """
        Private method to load a binary file.

        @param fileName name of the binary file to load
        @type str
        """
        try:
            if FileSystemUtilities.isRemoteFileName(fileName):
                data = self.__remotefsInterface.readFile(fileName)
            else:
                with open(fileName, "rb") as f:
                    data = f.read()
        except OSError as err:
            EricMessageBox.warning(
                self,
                self.tr("eric Hex Editor"),
                self.tr("<p>Cannot read file <b>{0}</b>.</p><p>Reason: {1}</p>").format(
                    fileName, str(err)
                ),
            )
            return

        self.__lastOpenPath = (
            self.__remotefsInterface.dirname(fileName)
            if FileSystemUtilities.isRemoteFileName(fileName)
            else os.path.dirname(fileName)
        )
        self.__editor.setData(data)
        self.__setCurrentFile(fileName)

        self.__editor.setReadOnly(Preferences.getHexEditor("OpenReadOnly"))

        self.__gotoWidget.reset()

    def __openHexFile(self):
        """
        Private slot to open a binary file.
        """
        if self.__maybeSave():
            if (
                not self.__lastOpenPath
                and self.__project is not None
                and self.__project.isOpen()
            ):
                self.__lastOpenPath = self.__project.getProjectPath()

            fileName = (
                EricServerFileDialog.getOpenFileName(
                    self,
                    self.tr("Open binary file"),
                    self.__lastOpenPath,
                    self.tr("All Files (*)"),
                )
                if FileSystemUtilities.isRemoteFileName(self.__lastOpenPath)
                else EricFileDialog.getOpenFileName(
                    self,
                    self.tr("Open binary file"),
                    self.__lastOpenPath,
                    self.tr("All Files (*)"),
                )
            )
            if fileName:
                self.__loadHexFile(fileName)
        self.__checkActions()

    def __openHexFileReadOnly(self):
        """
        Private slot to open a binary file in read only mode.
        """
        self.__openHexFile()
        self.__editor.setReadOnly(not Preferences.getHexEditor("OpenReadOnly"))
        self.__checkActions()

    def __saveHexFile(self):
        """
        Private method to save a binary file.

        @return flag indicating success
        @rtype bool
        """
        ok = (
            self.__saveHexDataFile(self.__fileName)
            if self.__fileName
            else self.__saveHexFileAs()
        )

        if ok:
            self.__editor.undoStack().setClean()

        return ok

    def __saveHexFileAs(self):
        """
        Private method to save the data to a new file.

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

        fileName = (
            EricServerFileDialog.getSaveFileName(
                self,
                self.tr("Save binary file"),
                self.__lastSavePath,
                self.tr("All Files (*)"),
            )
            if FileSystemUtilities.isRemoteFileName(self.__lastSavePath)
            else EricFileDialog.getSaveFileName(
                self,
                self.tr("Save binary file"),
                self.__lastSavePath,
                self.tr("All Files (*)"),
                options=EricFileDialog.DontConfirmOverwrite,
            )
        )
        if not fileName:
            return False

        if (
            FileSystemUtilities.isRemoteFileName(fileName)
            and self.__remotefsInterface.exists(fileName)
        ) or (
            FileSystemUtilities.isPlainFileName(fileName)
            and pathlib.Path(fileName).exists()
        ):
            res = EricMessageBox.yesNo(
                self,
                self.tr("Save binary file"),
                self.tr(
                    "<p>The file <b>{0}</b> already exists. Overwrite it?</p>"
                ).format(fileName),
                icon=EricMessageBox.Warning,
            )
            if not res:
                return False

        self.__lastSavePath = os.path.dirname(fileName)

        return self.__saveHexDataFile(fileName)

    def __saveHexDataFile(self, fileName):
        """
        Private method to save the binary data to a file.

        @param fileName name of the file to write to
        @type str
        @return flag indicating success
        @rtype bool
        """
        try:
            data = self.__editor.data()
            if FileSystemUtilities.isRemoteFileName(fileName):
                self.__remotefsInterface.writeFile(fileName, data)
            else:
                with open(fileName, "wb") as f:
                    f.write(data)
        except OSError as err:
            EricMessageBox.warning(
                self,
                self.tr("eric Hex Editor"),
                self.tr(
                    "<p>Cannot write file <b>{0}</b>.</p><p>Reason: {1}</p>"
                ).format(fileName, str(err)),
            )
            self.__checkActions()
            return False

        self.__editor.setModified(False, setCleanState=True)

        self.__setCurrentFile(fileName)
        self.__statusBar.showMessage(self.tr("File saved"), 2000)

        self.__checkActions()

        return True

    def __saveHexFileReadable(self, selectionOnly=False):
        """
        Private method to save the binary data in readable format.

        @param selectionOnly flag indicating to save the selection only
        @type bool
        """
        savePath = self.__lastSavePath
        if not savePath and self.__project is not None and self.__project.isOpen():
            savePath = self.__project.getProjectPath()
        if not savePath and self.__lastOpenPath:
            savePath = self.__lastOpenPath

        if FileSystemUtilities.isRemoteFileName(savePath):
            fileName, selectedFilter = EricServerFileDialog.getSaveFileNameAndFilter(
                self,
                self.tr("Save to readable file"),
                savePath,
                self.tr("Text Files (*.txt);;All Files (*)"),
                self.tr("Text Files (*.txt)"),
            )
            if not fileName:
                return

            ext = self.__remotefsInterface.splitext(fileName)[1]
            if not ext:
                ex = selectedFilter.split("(*")[1].split(")")[0]
                if ex:
                    fileName += ex
            fileExists = self.__remotefsInterface.exists(fileName)
        else:
            fileName, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
                self,
                self.tr("Save to readable file"),
                savePath,
                self.tr("Text Files (*.txt);;All Files (*)"),
                self.tr("Text Files (*.txt)"),
                EricFileDialog.DontConfirmOverwrite,
            )
            if not fileName:
                return

            fpath = pathlib.Path(fileName)
            if not fpath.suffix:
                ex = selectedFilter.split("(*")[1].split(")")[0]
                if ex:
                    fpath = fpath.with_suffix(ex)
            fileExists = fpath.exists()
            fileName = str(fpath)

        if fileExists:
            res = EricMessageBox.yesNo(
                self,
                self.tr("Save to readable file"),
                self.tr(
                    "<p>The file <b>{0}</b> already exists. Overwrite it?</p>"
                ).format(fileName),
                icon=EricMessageBox.Warning,
            )
            if not res:
                return

        readableData = (
            self.__editor.selectionToReadableString()
            if selectionOnly
            else self.__editor.toReadableString()
        )
        try:
            if FileSystemUtilities.isRemoteFileName(fileName):
                self.__remotefsInterface.writeFile(
                    fileName, readableData.encode("latin1")
                )
            else:
                with open(fileName, "w", encoding="latin1") as f:
                    f.write(readableData)
        except OSError as err:
            EricMessageBox.warning(
                self,
                self.tr("eric Hex Editor"),
                self.tr(
                    "<p>Cannot write file <b>{0}</b>.</p><p>Reason: {1}</p>"
                ).format(fpath, str(err)),
            )
            return

        self.__statusBar.showMessage(self.tr("File saved"), 2000)

    def __saveSelectionReadable(self):
        """
        Private method to save the data of the current selection in readable
        format.
        """
        self.__saveHexFileReadable(selectionOnly=True)

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
        for win in HexEditMainWindow.windows[:]:
            if win != self:
                win.close()

    def __setCurrentFile(self, fileName):
        """
        Private method to register the file name of the current file.

        @param fileName name of the file to register
        @type str
        """
        self.__fileName = fileName
        # insert filename into list of recently opened files
        self.__addToRecentList(fileName)

        shownName = (
            self.tr("Untitled")
            if not self.__fileName
            else self.__strippedName(self.__fileName)
        )

        self.setWindowTitle(
            self.tr("{0}[*] - {1}").format(shownName, self.tr("Hex Editor"))
        )

        self.setWindowModified(self.__editor.isModified())

    def __strippedName(self, fullFileName):
        """
        Private method to return the filename part of the given path.

        @param fullFileName full pathname of the given file
        @type str
        @return filename part
        @rtype str
        """
        return pathlib.Path(fullFileName).name

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

    @pyqtSlot()
    def __checkActions(self):
        """
        Private slot to check some actions for their enable/disable status.
        """
        self.saveAct.setEnabled(self.__editor.isModified())

        self.cutAct.setEnabled(
            not self.__editor.isReadOnly() and self.__editor.hasSelection()
        )
        self.pasteAct.setEnabled(not self.__editor.isReadOnly())
        self.replaceAct.setEnabled(not self.__editor.isReadOnly())

    @pyqtSlot(bool)
    def __modificationChanged(self, m):
        """
        Private slot to handle the dataChanged signal.

        @param m modification status
        @type bool
        """
        self.setWindowModified(m)
        self.__checkActions()

    def __about(self):
        """
        Private slot to show a little About message.
        """
        EricMessageBox.about(
            self,
            self.tr("About eric Hex Editor"),
            self.tr(
                "The eric Hex Editor is a simple editor component"
                " to edit binary files."
            ),
        )

    def __aboutQt(self):
        """
        Private slot to handle the About Qt dialog.
        """
        EricMessageBox.aboutQt(self, "eric Hex Editor")

    def __whatsThis(self):
        """
        Private slot called in to enter Whats This mode.
        """
        QWhatsThis.enterWhatsThisMode()

    def __search(self):
        """
        Private method to handle the search action.
        """
        self.__replaceWidget.hide()
        self.__gotoWidget.hide()
        txt = (
            self.__editor.selectionToHexString() if self.__editor.hasSelection() else ""
        )
        self.__searchWidget.show(txt)

    def __replace(self):
        """
        Private method to handle the replace action.
        """
        self.__searchWidget.hide()
        self.__gotoWidget.hide()
        txt = (
            self.__editor.selectionToHexString() if self.__editor.hasSelection() else ""
        )
        self.__replaceWidget.show(txt)

    def __goto(self):
        """
        Private method to handle the goto action.
        """
        self.__searchWidget.hide()
        self.__replaceWidget.hide()
        self.__gotoWidget.show()

    def preferencesChanged(self):
        """
        Public method to (re-)read the various settings.
        """
        self.__editor.setAddressWidth(Preferences.getHexEditor("AddressAreaWidth"))
        self.__editor.setAddressArea(Preferences.getHexEditor("ShowAddressArea"))
        self.__editor.setAsciiArea(Preferences.getHexEditor("ShowAsciiArea"))
        self.__editor.setHighlighting(Preferences.getHexEditor("HighlightChanges"))
        self.__editor.setFont(Preferences.getHexEditor("Font"))

        self.__setReadOnlyActionTexts()

    def __showPreferences(self):
        """
        Private slot to set the preferences.
        """
        from eric7.Preferences.ConfigurationDialog import (
            ConfigurationDialog,
            ConfigurationMode,
        )

        dlg = ConfigurationDialog(
            parent=None,
            name="Configuration",
            modal=True,
            fromEric=True,
            displayMode=ConfigurationMode.HEXEDITORMODE,
        )
        dlg.preferencesChanged.connect(
            self.__preferencesChangedByLocalPreferencesDialog
        )
        dlg.show()
        dlg.showConfigurationPageByName("hexEditorPage")
        dlg.exec()
        QCoreApplication.processEvents()
        if dlg.result() == QDialog.DialogCode.Accepted:
            dlg.setPreferences()
            Preferences.syncPreferences()
            self.__preferencesChangedByLocalPreferencesDialog()

    def __preferencesChangedByLocalPreferencesDialog(self):
        """
        Private slot to handle preferences changes by our local dialog.
        """
        for hexEditor in HexEditMainWindow.windows:
            hexEditor.preferencesChanged()

    def getSRHistory(self, key):
        """
        Public method to get the search or replace history list.

        @param key name of list to return
        @type str (must be 'search' or 'replace')
        @return the requested history list
        @rtype list of tuples of (int, str)
        """
        if key in ["search", "replace"]:
            return self.__srHistory[key]

        return []

    @pyqtSlot()
    def __showFileMenu(self):
        """
        Private slot to modify the file menu before being shown.
        """
        self.__menuRecentAct.setEnabled(len(self.__recent) > 0)

    @pyqtSlot()
    def __showRecentMenu(self):
        """
        Private slot to set up the recent files menu.
        """
        self.__loadRecent()

        self.__recentMenu.clear()

        connected = (
            self.__fromEric and ericApp().getObject("EricServer").isServerConnected()
        )

        for idx, rs in enumerate(self.__recent, start=1):
            formatStr = "&{0:d}. {1}" if idx < 10 else "{0:d}. {1}"
            act = self.__recentMenu.addAction(
                formatStr.format(
                    idx,
                    FileSystemUtilities.compactPath(
                        rs, HexEditMainWindow.maxMenuFilePathLen
                    ),
                )
            )
            act.setData(rs)
            act.setEnabled(
                (FileSystemUtilities.isRemoteFileName(rs) and connected)
                or pathlib.Path(rs).exists()
            )

        self.__recentMenu.addSeparator()
        self.__recentMenu.addAction(self.tr("&Clear"), self.__clearRecent)

    @pyqtSlot(QAction)
    def __openRecentHexFile(self, act):
        """
        Private method to open a file from the list of recently opened files.

        @param act reference to the action that triggered
        @type QAction
        """
        fileName = act.data()
        if fileName and self.__maybeSave():
            self.__loadHexFile(fileName)
            self.__editor.setReadOnly(Preferences.getHexEditor("OpenReadOnly"))
            self.__checkActions()

    @pyqtSlot()
    def __clearRecent(self):
        """
        Private method to clear the list of recently opened files.
        """
        self.__recent = []

    def __loadRecent(self):
        """
        Private method to load the list of recently opened files.
        """
        self.__recent = []
        Preferences.Prefs.rsettings.sync()
        rs = Preferences.Prefs.rsettings.value(recentNameHexFiles)
        if rs is not None:
            for f in EricUtilities.toList(rs):
                if FileSystemUtilities.isRemoteFileName(f) or pathlib.Path(f).exists():
                    self.__recent.append(f)

    def __saveRecent(self):
        """
        Private method to save the list of recently opened files.
        """
        Preferences.Prefs.rsettings.setValue(recentNameHexFiles, self.__recent)
        Preferences.Prefs.rsettings.sync()

    def __addToRecentList(self, fileName):
        """
        Private method to add a file name to the list of recently opened files.

        @param fileName name of the file to be added
        @type str
        """
        if fileName:
            for recent in self.__recent[:]:
                if FileSystemUtilities.samepath(fileName, recent):
                    self.__recent.remove(recent)
            self.__recent.insert(0, fileName)
            maxRecent = Preferences.getHexEditor("RecentNumber")
            if len(self.__recent) > maxRecent:
                self.__recent = self.__recent[:maxRecent]
            self.__saveRecent()
