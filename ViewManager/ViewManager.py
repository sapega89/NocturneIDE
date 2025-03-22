# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the view manager base class.
"""

import contextlib
import os
import pathlib
import re

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtCore import (
    QCoreApplication,
    QPoint,
    QSignalMapper,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QKeySequence, QPixmap
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QToolBar, QWidget

from eric7 import EricUtilities, Preferences
from eric7.EricCore import EricFileSystemWatcher
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction, createActionGroup
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Globals import recentNameFiles
from eric7.QScintilla import Exporters, Lexers
from eric7.QScintilla.APIsManager import APIsManager
from eric7.QScintilla.Editor import Editor
from eric7.QScintilla.EditorAssembly import EditorAssembly
from eric7.QScintilla.Shell import Shell
from eric7.QScintilla.SpellChecker import SpellChecker
from eric7.QScintilla.SpellingDictionaryEditDialog import SpellingDictionaryEditDialog
from eric7.QScintilla.ZoomDialog import ZoomDialog
from eric7.RemoteServerInterface import EricServerFileDialog
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities


class ViewManager(QWidget):
    """
    Base class inherited by all specific view manager classes.

    It defines the interface to be implemented by specific
    view manager classes and all common methods.

    @signal changeCaption(str) emitted if a change of the caption is necessary
    @signal editorChanged(str) emitted when the current editor has changed
    @signal editorChangedEd(Editor) emitted when the current editor has changed
    @signal lastEditorClosed() emitted after the last editor window was closed
    @signal editorOpened(str) emitted after an editor window was opened
    @signal editorOpenedEd(Editor) emitted after an editor window was opened
    @signal editorClosed(str) emitted just before an editor window gets closed
    @signal editorClosedEd(Editor) emitted just before an editor window gets
        closed
    @signal editorRenamed(str) emitted after an editor was renamed
    @signal editorRenamedEd(Editor) emitted after an editor was renamed
    @signal editorSaved(str) emitted after an editor window was saved
    @signal editorSavedEd(Editor) emitted after an editor window was saved
    @signal editorCountChanged(count) emitted whenever the count of open editors
        changed
    @signal checkActions(Editor) emitted when some actions should be checked
        for their status
    @signal cursorChanged(Editor) emitted after the cursor position of the
        active window has changed
    @signal breakpointToggled(Editor) emitted when a breakpoint is toggled
    @signal bookmarkToggled(Editor) emitted when a bookmark is toggled
    @signal syntaxerrorToggled(Editor) emitted when a syntax error is toggled
    @signal previewStateChanged(bool) emitted to signal a change in the
        preview state
    @signal astViewerStateChanged(bool) emitted to signal a change in the
        AST viewer state
    @signal disViewerStateChanged(bool) emitted to signal a change in the
        DIS viewer state
    @signal editorLanguageChanged(Editor) emitted to signal a change of an
        editor's language
    @signal editorTextChanged(Editor) emitted to signal a change of an
        editor's text
    @signal editorLineChanged(str,int) emitted to signal a change of an
        editor's current line (line is given one based)
    @signal editorLineChangedEd(Editor,int) emitted to signal a change of an
        editor's current line (line is given one based)
    @signal editorDoubleClickedEd(Editor, position, buttons) emitted to signal
        a mouse double click in an editor
    """

    changeCaption = pyqtSignal(str)
    editorChanged = pyqtSignal(str)
    editorChangedEd = pyqtSignal(Editor)
    lastEditorClosed = pyqtSignal()
    editorOpened = pyqtSignal(str)
    editorOpenedEd = pyqtSignal(Editor)
    editorClosed = pyqtSignal(str)
    editorClosedEd = pyqtSignal(Editor)
    editorRenamed = pyqtSignal(str)
    editorRenamedEd = pyqtSignal(Editor)
    editorSaved = pyqtSignal(str)
    editorSavedEd = pyqtSignal(Editor)
    editorCountChanged = pyqtSignal(int)
    checkActions = pyqtSignal(Editor)
    cursorChanged = pyqtSignal(Editor)
    breakpointToggled = pyqtSignal(Editor)
    bookmarkToggled = pyqtSignal(Editor)
    syntaxerrorToggled = pyqtSignal(Editor)
    previewStateChanged = pyqtSignal(bool)
    astViewerStateChanged = pyqtSignal(bool)
    disViewerStateChanged = pyqtSignal(bool)
    editorLanguageChanged = pyqtSignal(Editor)
    editorTextChanged = pyqtSignal(Editor)
    editorLineChanged = pyqtSignal(str, int)
    editorLineChangedEd = pyqtSignal(Editor, int)
    editorDoubleClickedEd = pyqtSignal(Editor, QPoint, Qt.MouseButton)

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        # initialize the instance variables
        self.editors = []
        self.currentEditor = None
        self.untitledCount = 0
        self.srHistory = {"search": [], "replace": []}
        self.editorsCheckFocusIn = True

        self.recent = []

        self.bookmarked = []
        bs = Preferences.getSettings().value("Bookmarked/Sources")
        if bs is not None:
            self.bookmarked = bs

        # initialize the APIs manager
        self.apisManager = APIsManager(parent=self)

        self.__cooperationClient = None

        self.__lastFocusWidget = None

        # initialize the file system watcher
        watcher = EricFileSystemWatcher.instance()
        watcher.fileModified.connect(self.__watchedFileChanged)
        watcher.error.connect(self.__watcherError)

        self.__watchedFilePaths = []

    def setReferences(self, ui, dbs, remoteServerInterface):
        """
        Public method to set some references needed later on.

        @param ui reference to the main user interface
        @type UserInterface
        @param dbs reference to the debug server object
        @type DebugServer
        @param remoteServerInterface reference to the 'eric-ide' server interface
        @type EricServerInterface
        """
        from eric7.QScintilla.SearchReplaceWidget import SearchReplaceSlidingWidget

        self.ui = ui
        self.dbs = dbs

        self.__remoteServer = remoteServerInterface
        self.__remotefsInterface = remoteServerInterface.getServiceInterface(
            "FileSystem"
        )

        self.__searchReplaceWidget = SearchReplaceSlidingWidget(self, ui)

        self.editorClosedEd.connect(self.__searchReplaceWidget.editorClosed)
        self.checkActions.connect(self.__searchReplaceWidget.updateSelectionCheckBox)

        self.__loadRecent()

    def searchReplaceWidget(self):
        """
        Public method to get a reference to the search widget.

        @return reference to the search widget
        @rtype SearchReplaceSlidingWidget
        """
        return self.__searchReplaceWidget

    def __loadRecent(self):
        """
        Private method to load the recently opened filenames.
        """
        self.recent = []
        Preferences.Prefs.rsettings.sync()
        rs = Preferences.Prefs.rsettings.value(recentNameFiles)
        if rs is not None:
            for f in EricUtilities.toList(rs):
                if (
                    FileSystemUtilities.isRemoteFileName(f)
                    and (
                        not self.__remoteServer.isServerConnected()
                        or self.__remotefsInterface.exists(f)
                    )
                ) or pathlib.Path(f).exists():
                    self.recent.append(f)

    def __saveRecent(self):
        """
        Private method to save the list of recently opened filenames.
        """
        Preferences.Prefs.rsettings.setValue(recentNameFiles, self.recent)
        Preferences.Prefs.rsettings.sync()

    def getMostRecent(self):
        """
        Public method to get the most recently opened file.

        @return path of the most recently opened file
        @rtype str
        """
        if len(self.recent):
            return self.recent[0]
        else:
            return None

    def setSbInfo(
        self, sbLine, sbPos, sbWritable, sbEncoding, sbLanguage, sbEol, sbZoom
    ):
        """
        Public method to transfer statusbar info from the user interface to
        viewmanager.

        @param sbLine reference to the line number part of the statusbar
        @type QLabel
        @param sbPos reference to the character position part of the statusbar
        @type QLabel
        @param sbWritable reference to the writability indicator part of
            the statusbar
        @type QLabel
        @param sbEncoding reference to the encoding indicator part of the
            statusbar
        @type QLabel
        @param sbLanguage reference to the language indicator part of the
            statusbar
        @type QLabel
        @param sbEol reference to the eol indicator part of the statusbar
        @type QLabel
        @param sbZoom reference to the zoom widget
        @type EricZoomWidget
        """
        self.sbLine = sbLine
        self.sbPos = sbPos
        self.sbWritable = sbWritable
        self.sbEnc = sbEncoding
        self.sbLang = sbLanguage
        self.sbEol = sbEol
        self.sbZoom = sbZoom
        self.sbZoom.valueChanged.connect(self.__zoomTo)
        self.__setSbFile(zoom=0)

        self.sbLang.clicked.connect(self.__showLanguagesMenu)
        self.sbEol.clicked.connect(self.__showEolMenu)
        self.sbEnc.clicked.connect(self.__showEncodingsMenu)

    ##################################################################
    ## Below are menu handling methods for status bar labels
    ##################################################################

    def __showLanguagesMenu(self, pos):
        """
        Private slot to show the Languages menu of the current editor.

        @param pos position the menu should be shown at
        @type QPoint
        """
        aw = self.activeWindow()
        if aw is not None:
            menu = aw.getMenu("Languages")
            if menu is not None:
                menu.exec(pos)

    def __showEolMenu(self, pos):
        """
        Private slot to show the EOL menu of the current editor.

        @param pos position the menu should be shown at
        @type QPoint
        """
        aw = self.activeWindow()
        if aw is not None:
            menu = aw.getMenu("Eol")
            if menu is not None:
                menu.exec(pos)

    def __showEncodingsMenu(self, pos):
        """
        Private slot to show the Encodings menu of the current editor.

        @param pos position the menu should be shown at
        @type QPoint
        """
        aw = self.activeWindow()
        if aw is not None:
            menu = aw.getMenu("Encodings")
            if menu is not None:
                menu.exec(pos)

    ###########################################################################
    ## methods below need to be implemented by a subclass
    ###########################################################################

    def canCascade(self):
        """
        Public method to signal if cascading of managed windows is available.

        @return flag indicating cascading of windows is available
        @rtype bool
        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

        return False

    def canTile(self):
        """
        Public method to signal if tiling of managed windows is available.

        @return flag indicating tiling of windows is available
        @rtype bool
        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

        return False

    def tile(self):
        """
        Public method to tile the managed windows.

        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

    def cascade(self):
        """
        Public method to cascade the managed windows.

        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

    def activeWindow(self):
        """
        Public method to return the active (i.e. current) window.

        @return reference to the active editor
        @rtype Editor
        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

        return None  # __IGNORE_WARNING_M831__

    def _removeAllViews(self):
        """
        Protected method to remove all views (i.e. windows).

        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

    def _removeView(self, win):
        """
        Protected method to remove a view (i.e. window).

        @param win editor window to be removed
        @type EditorAssembly
        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

    def _addView(self, win, fn=None, noName="", addNext=False, indexes=None):
        """
        Protected method to add a view (i.e. window).

        @param win editor assembly to be added
        @type EditorAssembly
        @param fn filename of this editor
        @type str
        @param noName name to be used for an unnamed editor
        @type str
        @param addNext flag indicating to add the view next to the current
            view
        @type bool
        @param indexes of the editor, first the split view index, second the
            index within the view
        @type tuple of two int
        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

    def _showView(self, win, fn=None):
        """
        Protected method to show a view (i.e. window).

        @param win editor assembly to be shown
        @type EditorAssembly
        @param fn filename of this editor
        @type str
        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

    def showWindowMenu(self, windowMenu):
        """
        Public method to set up the viewmanager part of the Window menu.

        @param windowMenu reference to the window menu
        @type QMenu
        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

    def _initWindowActions(self):
        """
        Protected method to define the user interface actions for window
        handling.

        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

    def setEditorName(self, editor, newName):
        """
        Public method to change the displayed name of the editor.

        @param editor editor window to be changed
        @type Editor
        @param newName new name to be shown
        @type str
        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

    def _modificationStatusChanged(self, m, editor):
        """
        Protected slot to handle the modificationStatusChanged signal.

        @param m flag indicating the modification status
        @type bool
        @param editor editor window changed
        @type Editor
        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

    def mainWidget(self):
        """
        Public method to return a reference to the main Widget of a
        specific view manager subclass.

        @exception NotImplementedError Not implemented
        """
        raise NotImplementedError("Not implemented")

    #####################################################################
    ## methods above need to be implemented by a subclass
    #####################################################################

    def canSplit(self):
        """
        Public method to signal if splitting of the view is available.

        @return flag indicating splitting of the view is available
        @rtype bool
        """
        return False

    def addSplit(self):
        """
        Public method used to split the current view.
        """
        pass

    @pyqtSlot()
    def removeSplit(self, index=-1):
        """
        Public method used to remove the current split view or a split view
        by index.

        @param index index of the split to be removed (-1 means to
            delete the current split)
        @type int
        @return flag indicating successful deletion
        @rtype bool
        """
        return False

    def splitCount(self):
        """
        Public method to get the number of split views.

        @return number of split views
        @rtype int
        """
        return 0

    def setSplitCount(self, count):
        """
        Public method to set the number of split views.

        @param count number of split views
        @type int
        """
        pass

    def getSplitOrientation(self):
        """
        Public method to get the orientation of the split view.

        @return orientation of the split
        @rtype Qt.Orientation
        """
        return Qt.Orientation.Vertical

    def setSplitOrientation(self, orientation):
        """
        Public method used to set the orientation of the split view.

        @param orientation orientation of the split
        @type Qt.Orientation
        """
        pass

    def nextSplit(self):
        """
        Public slot used to move to the next split.
        """
        pass

    def prevSplit(self):
        """
        Public slot used to move to the previous split.
        """
        pass

    def eventFilter(self, qobject, event):
        """
        Public method called to filter an event.

        @param qobject object, that generated the event
        @type QObject
        @param event the event, that was generated by object
        @type QEvent
        @return flag indicating if event was filtered out
        @rtype bool
        """
        return False

    #####################################################################
    ## methods above need to be implemented by a subclass, that supports
    ## splitting of the viewmanager area.
    #####################################################################

    def initActions(self):
        """
        Public method defining the user interface actions.
        """
        # list containing all edit actions
        self.editActions = []

        # list containing all file actions
        self.fileActions = []

        # list containing all search actions
        self.searchActions = []

        # list containing all view actions
        self.viewActions = []

        # list containing all window actions
        self.windowActions = []

        # list containing all macro actions
        self.macroActions = []

        # list containing all bookmark actions
        self.bookmarkActions = []

        # list containing all spell checking actions
        self.spellingActions = []

        self.__actions = {
            "bookmark": self.bookmarkActions,
            "edit": self.editActions,
            "file": self.fileActions,
            "macro": self.macroActions,
            "search": self.searchActions,
            "spelling": self.spellingActions,
            "view": self.viewActions,
            "window": self.windowActions,
        }

        self._initWindowActions()
        self.__initFileActions()
        self.__initEditActions()
        self.__initSearchActions()
        self.__initViewActions()
        self.__initMacroActions()
        self.__initBookmarkActions()
        self.__initSpellingActions()

    ##################################################################
    ## Initialize the file related actions, file menu and toolbar
    ##################################################################

    def __initFileActions(self):
        """
        Private method defining the user interface actions for file handling.
        """
        self.newAct = EricAction(
            QCoreApplication.translate("ViewManager", "New"),
            EricPixmapCache.getIcon("new"),
            QCoreApplication.translate("ViewManager", "&New"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+N", "File|New")
            ),
            0,
            self,
            "vm_file_new",
        )
        self.newAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Open an empty editor window")
        )
        self.newAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>New</b><p>An empty editor window will be created.</p>""",
            )
        )
        self.newAct.triggered.connect(self.newEditor)
        self.fileActions.append(self.newAct)

        self.openAct = EricAction(
            QCoreApplication.translate("ViewManager", "Open"),
            EricPixmapCache.getIcon("documentOpen"),
            QCoreApplication.translate("ViewManager", "&Open..."),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+O", "File|Open")
            ),
            0,
            self,
            "vm_file_open",
        )
        self.openAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Open a file")
        )
        self.openAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Open a file</b>"""
                """<p>You will be asked for the name of a file to be opened"""
                """ in an editor window.</p>""",
            )
        )
        self.openAct.triggered.connect(self.__openFiles)
        self.fileActions.append(self.openAct)

        self.openRemoteAct = EricAction(
            QCoreApplication.translate("ViewManager", "Open (Remote)"),
            EricPixmapCache.getIcon("open-remote"),
            QCoreApplication.translate("ViewManager", "Open (Remote)..."),
            0,
            0,
            self,
            "vm_file_open_remote",
        )
        self.openRemoteAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Open a remote file")
        )
        self.openRemoteAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Open a remote file</b>"""
                """<p>You will be asked for the name of a remote file to be opened"""
                """ in an editor window.</p>""",
            )
        )
        self.openRemoteAct.triggered.connect(self.__openRemoteFiles)
        self.openRemoteAct.setEnabled(False)
        self.fileActions.append(self.openRemoteAct)

        self.reloadAct = EricAction(
            QCoreApplication.translate("ViewManager", "Reload"),
            EricPixmapCache.getIcon("reload"),
            QCoreApplication.translate("ViewManager", "Reload"),
            0,
            0,
            self,
            "vm_file_reload",
        )
        self.reloadAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Reload the current file")
        )
        self.reloadAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Reload</b>"""
                """<p>Reload the contents of current editor window. If the editor"""
                """ contents was modified, a warning will be issued.</p>""",
            )
        )
        self.reloadAct.triggered.connect(self.__reloadCurrentEditor)
        self.fileActions.append(self.reloadAct)

        self.closeActGrp = createActionGroup(self)

        self.closeAct = EricAction(
            QCoreApplication.translate("ViewManager", "Close"),
            EricPixmapCache.getIcon("closeEditor"),
            QCoreApplication.translate("ViewManager", "&Close"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+W", "File|Close")
            ),
            0,
            self.closeActGrp,
            "vm_file_close",
        )
        self.closeAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Close the current window")
        )
        self.closeAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Close Window</b><p>Close the current window.</p>""",
            )
        )
        self.closeAct.triggered.connect(self.closeCurrentWindow)
        self.fileActions.append(self.closeAct)

        self.closeAllAct = EricAction(
            QCoreApplication.translate("ViewManager", "Close All"),
            QCoreApplication.translate("ViewManager", "Clos&e All"),
            0,
            0,
            self.closeActGrp,
            "vm_file_close_all",
        )
        self.closeAllAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Close all editor windows")
        )
        self.closeAllAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Close All Windows</b><p>Close all editor windows.</p>""",
            )
        )
        self.closeAllAct.triggered.connect(self.closeAllWindows)
        self.fileActions.append(self.closeAllAct)

        self.closeActGrp.setEnabled(False)

        self.saveActGrp = createActionGroup(self)

        self.saveAct = EricAction(
            QCoreApplication.translate("ViewManager", "Save"),
            EricPixmapCache.getIcon("fileSave"),
            QCoreApplication.translate("ViewManager", "&Save"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+S", "File|Save")
            ),
            0,
            self.saveActGrp,
            "vm_file_save",
        )
        self.saveAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Save the current file")
        )
        self.saveAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Save File</b>"""
                """<p>Save the contents of current editor window.</p>""",
            )
        )
        self.saveAct.triggered.connect(self.saveCurrentEditor)
        self.fileActions.append(self.saveAct)

        self.saveAsAct = EricAction(
            QCoreApplication.translate("ViewManager", "Save as"),
            EricPixmapCache.getIcon("fileSaveAs"),
            QCoreApplication.translate("ViewManager", "Save &as..."),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Shift+Ctrl+S", "File|Save As"
                )
            ),
            0,
            self.saveActGrp,
            "vm_file_save_as",
        )
        self.saveAsAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Save the current file to a new one"
            )
        )
        self.saveAsAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Save File as</b>"""
                """<p>Save the contents of the current editor window to a new file."""
                """ The file can be entered in a file selection dialog.</p>""",
            )
        )
        self.saveAsAct.triggered.connect(self.saveAsCurrentEditor)
        self.fileActions.append(self.saveAsAct)

        self.saveAsRemoteAct = EricAction(
            QCoreApplication.translate("ViewManager", "Save as (Remote)"),
            EricPixmapCache.getIcon("fileSaveAsRemote"),
            QCoreApplication.translate("ViewManager", "Save as (Remote)..."),
            0,
            0,
            self.saveActGrp,
            "vm_file_save_as_remote",
        )
        self.saveAsRemoteAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager",
                "Save the current file to a new one on an eric-ide server",
            )
        )
        self.saveAsRemoteAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Save File as (Remote)</b>"""
                """<p>Save the contents of the current editor window to a new file"""
                """ on the connected eric-ide server. The file can be entered in a"""
                """ file selection dialog.</p>""",
            )
        )
        self.saveAsRemoteAct.triggered.connect(self.saveAsRemoteCurrentEditor)
        self.fileActions.append(self.saveAsRemoteAct)

        self.saveCopyAct = EricAction(
            QCoreApplication.translate("ViewManager", "Save Copy"),
            EricPixmapCache.getIcon("fileSaveCopy"),
            QCoreApplication.translate("ViewManager", "Save &Copy..."),
            0,
            0,
            self.saveActGrp,
            "vm_file_save_copy",
        )
        self.saveCopyAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Save a copy of the current file")
        )
        self.saveCopyAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Save Copy</b>"""
                """<p>Save a copy of the contents of current editor window."""
                """ The file can be entered in a file selection dialog.</p>""",
            )
        )
        self.saveCopyAct.triggered.connect(self.saveCopyCurrentEditor)
        self.fileActions.append(self.saveCopyAct)

        self.saveAllAct = EricAction(
            QCoreApplication.translate("ViewManager", "Save all"),
            EricPixmapCache.getIcon("fileSaveAll"),
            QCoreApplication.translate("ViewManager", "Save a&ll"),
            0,
            0,
            self.saveActGrp,
            "vm_file_save_all",
        )
        self.saveAllAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Save all files")
        )
        self.saveAllAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Save All Files</b>"""
                """<p>Save the contents of all editor windows.</p>""",
            )
        )
        self.saveAllAct.triggered.connect(self.saveAllEditors)
        self.fileActions.append(self.saveAllAct)

        self.saveActGrp.setEnabled(False)

        self.printAct = EricAction(
            QCoreApplication.translate("ViewManager", "Print"),
            EricPixmapCache.getIcon("print"),
            QCoreApplication.translate("ViewManager", "&Print"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+P", "File|Print")
            ),
            0,
            self,
            "vm_file_print",
        )
        self.printAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Print the current file")
        )
        self.printAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Print File</b>"""
                """<p>Print the contents of current editor window.</p>""",
            )
        )
        self.printAct.triggered.connect(self.printCurrentEditor)
        self.printAct.setEnabled(False)
        self.fileActions.append(self.printAct)

        self.printPreviewAct = EricAction(
            QCoreApplication.translate("ViewManager", "Print Preview"),
            EricPixmapCache.getIcon("printPreview"),
            QCoreApplication.translate("ViewManager", "Print Preview"),
            0,
            0,
            self,
            "vm_file_print_preview",
        )
        self.printPreviewAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Print preview of the current file"
            )
        )
        self.printPreviewAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Print Preview</b>"""
                """<p>Print preview of the current editor window.</p>""",
            )
        )
        self.printPreviewAct.triggered.connect(self.printPreviewCurrentEditor)
        self.printPreviewAct.setEnabled(False)
        self.fileActions.append(self.printPreviewAct)

        self.findLocationAct = EricAction(
            QCoreApplication.translate("ViewManager", "Find File"),
            EricPixmapCache.getIcon("findLocation"),
            QCoreApplication.translate("ViewManager", "Find &File..."),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Alt+Ctrl+F", "File|Find File"
                )
            ),
            0,
            self,
            "vm_file_search_file",
        )
        self.findLocationAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Search for a file by entering a search pattern"
            )
        )
        self.findLocationAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Find File</b>"""
                """<p>This searches for a file by entering a search pattern.</p>""",
            )
        )
        self.findLocationAct.triggered.connect(self.__findLocation)
        self.fileActions.append(self.findLocationAct)

    def initFileMenu(self):
        """
        Public method to create the File menu.

        @return the generated menu
        @rtype QMenu
        """
        menu = QMenu(QCoreApplication.translate("ViewManager", "&File"), self.ui)
        self.recentMenu = QMenu(
            QCoreApplication.translate("ViewManager", "Open &Recent Files"), menu
        )
        self.recentMenu.setIcon(EricPixmapCache.getIcon("documentOpenRecent"))
        self.bookmarkedMenu = QMenu(
            QCoreApplication.translate("ViewManager", "Open &Bookmarked Files"), menu
        )
        self.exportersMenu = self.__initContextMenuExporters()
        menu.setTearOffEnabled(True)

        menu.addAction(self.newAct)
        menu.addAction(self.openAct)
        menu.addAction(self.openRemoteAct)
        menu.addAction(self.reloadAct)
        self.menuRecentAct = menu.addMenu(self.recentMenu)
        menu.addMenu(self.bookmarkedMenu)
        menu.addSeparator()
        menu.addAction(self.closeAct)
        menu.addAction(self.closeAllAct)
        menu.addSeparator()
        menu.addAction(self.findLocationAct)
        menu.addSeparator()
        menu.addAction(self.saveAct)
        menu.addAction(self.saveAsAct)
        menu.addAction(self.saveAsRemoteAct)
        menu.addAction(self.saveCopyAct)
        menu.addAction(self.saveAllAct)
        self.exportersMenuAct = menu.addMenu(self.exportersMenu)
        menu.addSeparator()
        menu.addAction(self.printPreviewAct)
        menu.addAction(self.printAct)

        self.recentMenu.aboutToShow.connect(self.__showRecentMenu)
        self.recentMenu.triggered.connect(self.__openSourceFile)
        self.bookmarkedMenu.aboutToShow.connect(self.__showBookmarkedMenu)
        self.bookmarkedMenu.triggered.connect(self.__openSourceFile)
        menu.aboutToShow.connect(self.__showFileMenu)

        self.exportersMenuAct.setEnabled(False)

        return menu

    def initFileToolbar(self, toolbarManager):
        """
        Public method to create the File toolbar.

        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        @return the generated toolbar
        @rtype QToolBar
        """
        tb = QToolBar(QCoreApplication.translate("ViewManager", "File"), self.ui)
        tb.setObjectName("FileToolbar")
        tb.setToolTip(QCoreApplication.translate("ViewManager", "File"))

        tb.addAction(self.newAct)
        tb.addAction(self.openAct)
        tb.addAction(self.openRemoteAct)
        tb.addAction(self.reloadAct)
        tb.addAction(self.closeAct)
        tb.addSeparator()
        tb.addAction(self.saveAct)
        tb.addAction(self.saveAsAct)
        tb.addAction(self.saveAsRemoteAct)
        tb.addAction(self.saveCopyAct)
        tb.addAction(self.saveAllAct)

        toolbarManager.addToolBar(tb, tb.windowTitle())
        toolbarManager.addAction(self.printPreviewAct, tb.windowTitle())
        toolbarManager.addAction(self.printAct, tb.windowTitle())

        return tb

    def __initContextMenuExporters(self):
        """
        Private method used to setup the Exporters sub menu.

        @return reference to the generated menu
        @rtype QMenu
        """
        menu = QMenu(QCoreApplication.translate("ViewManager", "Export as"))

        supportedExporters = Exporters.getSupportedFormats()
        for exporter in sorted(supportedExporters):
            act = menu.addAction(supportedExporters[exporter])
            act.setData(exporter)

        menu.triggered.connect(self.__exportMenuTriggered)

        return menu

    ##################################################################
    ## Initialize the edit related actions, edit menu and toolbar
    ##################################################################

    def __initEditActions(self):
        """
        Private method defining the user interface actions for the edit
            commands.
        """
        self.editActGrp = createActionGroup(self)

        self.undoAct = EricAction(
            QCoreApplication.translate("ViewManager", "Undo"),
            EricPixmapCache.getIcon("editUndo"),
            QCoreApplication.translate("ViewManager", "&Undo"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+Z", "Edit|Undo")
            ),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Alt+Backspace", "Edit|Undo")
            ),
            self.editActGrp,
            "vm_edit_undo",
        )
        self.undoAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Undo the last change")
        )
        self.undoAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Undo</b>"""
                """<p>Undo the last change done in the current editor.</p>""",
            )
        )
        self.undoAct.triggered.connect(self.__editUndo)
        self.editActions.append(self.undoAct)

        self.redoAct = EricAction(
            QCoreApplication.translate("ViewManager", "Redo"),
            EricPixmapCache.getIcon("editRedo"),
            QCoreApplication.translate("ViewManager", "&Redo"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+Shift+Z", "Edit|Redo")
            ),
            0,
            self.editActGrp,
            "vm_edit_redo",
        )
        self.redoAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Redo the last change")
        )
        self.redoAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Redo</b>"""
                """<p>Redo the last change done in the current editor.</p>""",
            )
        )
        self.redoAct.triggered.connect(self.__editRedo)
        self.editActions.append(self.redoAct)

        self.revertAct = EricAction(
            QCoreApplication.translate("ViewManager", "Revert to last saved state"),
            QCoreApplication.translate("ViewManager", "Re&vert to last saved state"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+Y", "Edit|Revert")
            ),
            0,
            self.editActGrp,
            "vm_edit_revert",
        )
        self.revertAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Revert to last saved state")
        )
        self.revertAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Revert to last saved state</b>"""
                """<p>Undo all changes up to the last saved state"""
                """ of the current editor.</p>""",
            )
        )
        self.revertAct.triggered.connect(self.__editRevert)
        self.editActions.append(self.revertAct)

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
            QCoreApplication.translate(
                "ViewManager",
                """<b>Cut</b>"""
                """<p>Cut the selected text of the current editor to the"""
                """ clipboard.</p>""",
            )
        )
        self.cutAct.triggered.connect(self.__editCut)
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
            QCoreApplication.translate(
                "ViewManager",
                """<b>Copy</b>"""
                """<p>Copy the selected text of the current editor to the"""
                """ clipboard.</p>""",
            )
        )
        self.copyAct.triggered.connect(self.__editCopy)
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
            QCoreApplication.translate(
                "ViewManager",
                """<b>Paste</b>"""
                """<p>Paste the last cut/copied text from the clipboard to"""
                """ the current editor.</p>""",
            )
        )
        self.pasteAct.triggered.connect(self.__editPaste)
        self.editActions.append(self.pasteAct)

        self.deleteAct = EricAction(
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
        self.deleteAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Clear all text")
        )
        self.deleteAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Clear</b><p>Delete all text of the current editor.</p>""",
            )
        )
        self.deleteAct.triggered.connect(self.__editDelete)
        self.editActions.append(self.deleteAct)

        self.joinAct = EricAction(
            QCoreApplication.translate("ViewManager", "Join Lines"),
            QCoreApplication.translate("ViewManager", "Join Lines"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+J", "Edit|Join Lines")
            ),
            0,
            self.editActGrp,
            "vm_edit_join_lines",
        )
        self.joinAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Join Lines")
        )
        self.joinAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Join Lines</b>"""
                """<p>Join the current and the next lines.</p>""",
            )
        )
        self.joinAct.triggered.connect(self.__editJoin)
        self.editActions.append(self.joinAct)

        self.indentAct = EricAction(
            QCoreApplication.translate("ViewManager", "Indent"),
            EricPixmapCache.getIcon("editIndent"),
            QCoreApplication.translate("ViewManager", "&Indent"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+I", "Edit|Indent")
            ),
            0,
            self.editActGrp,
            "vm_edit_indent",
        )
        self.indentAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Indent line")
        )
        self.indentAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Indent</b>"""
                """<p>Indents the current line or the lines of the"""
                """ selection by one level.</p>""",
            )
        )
        self.indentAct.triggered.connect(self.__editIndent)
        self.editActions.append(self.indentAct)

        self.unindentAct = EricAction(
            QCoreApplication.translate("ViewManager", "Unindent"),
            EricPixmapCache.getIcon("editUnindent"),
            QCoreApplication.translate("ViewManager", "U&nindent"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+Shift+I", "Edit|Unindent"
                )
            ),
            0,
            self.editActGrp,
            "vm_edit_unindent",
        )
        self.unindentAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Unindent line")
        )
        self.unindentAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Unindent</b>"""
                """<p>Unindents the current line or the lines of the"""
                """ selection by one level.</p>""",
            )
        )
        self.unindentAct.triggered.connect(self.__editUnindent)
        self.editActions.append(self.unindentAct)

        self.smartIndentAct = EricAction(
            QCoreApplication.translate("ViewManager", "Smart indent"),
            EricPixmapCache.getIcon("editSmartIndent"),
            QCoreApplication.translate("ViewManager", "Smart indent"),
            0,
            0,
            self.editActGrp,
            "vm_edit_smart_indent",
        )
        self.smartIndentAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Smart indent Line or Selection")
        )
        self.smartIndentAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Smart indent</b>"""
                """<p>Indents the current line or the lines of the"""
                """ current selection smartly.</p>""",
            )
        )
        self.smartIndentAct.triggered.connect(self.__editSmartIndent)
        self.editActions.append(self.smartIndentAct)

        self.commentAct = EricAction(
            QCoreApplication.translate("ViewManager", "Comment"),
            EricPixmapCache.getIcon("editComment"),
            QCoreApplication.translate("ViewManager", "C&omment"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+M", "Edit|Comment")
            ),
            0,
            self.editActGrp,
            "vm_edit_comment",
        )
        self.commentAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Comment Line or Selection")
        )
        self.commentAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Comment</b>"""
                """<p>Comments the current line or the lines of the"""
                """ current selection.</p>""",
            )
        )
        self.commentAct.triggered.connect(self.__editComment)
        self.editActions.append(self.commentAct)

        self.uncommentAct = EricAction(
            QCoreApplication.translate("ViewManager", "Uncomment"),
            EricPixmapCache.getIcon("editUncomment"),
            QCoreApplication.translate("ViewManager", "Unco&mment"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+Shift+M", "Edit|Uncomment"
                )
            ),
            0,
            self.editActGrp,
            "vm_edit_uncomment",
        )
        self.uncommentAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Uncomment Line or Selection")
        )
        self.uncommentAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Uncomment</b>"""
                """<p>Uncomments the current line or the lines of the"""
                """ current selection.</p>""",
            )
        )
        self.uncommentAct.triggered.connect(self.__editUncomment)
        self.editActions.append(self.uncommentAct)

        self.toggleCommentAct = EricAction(
            QCoreApplication.translate("ViewManager", "Toggle Comment"),
            EricPixmapCache.getIcon("editToggleComment"),
            QCoreApplication.translate("ViewManager", "Toggle Comment"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+#", "Edit|Toggle Comment"
                )
            ),
            0,
            self.editActGrp,
            "vm_edit_toggle_comment",
        )
        self.toggleCommentAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager",
                "Toggle the comment of the current line, selection or comment block",
            )
        )
        self.toggleCommentAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Toggle Comment</b>"""
                """<p>If the current line does not start with a block comment,"""
                """ the current line or selection is commented. If it is already"""
                """ commented, this comment block is uncommented. </p>""",
            )
        )
        self.toggleCommentAct.triggered.connect(self.__editToggleComment)
        self.editActions.append(self.toggleCommentAct)

        self.streamCommentAct = EricAction(
            QCoreApplication.translate("ViewManager", "Stream Comment"),
            QCoreApplication.translate("ViewManager", "Stream Comment"),
            0,
            0,
            self.editActGrp,
            "vm_edit_stream_comment",
        )
        self.streamCommentAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Stream Comment Line or Selection"
            )
        )
        self.streamCommentAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Stream Comment</b>"""
                """<p>Stream comments the current line or the current"""
                """ selection.</p>""",
            )
        )
        self.streamCommentAct.triggered.connect(self.__editStreamComment)
        self.editActions.append(self.streamCommentAct)

        self.boxCommentAct = EricAction(
            QCoreApplication.translate("ViewManager", "Box Comment"),
            QCoreApplication.translate("ViewManager", "Box Comment"),
            0,
            0,
            self.editActGrp,
            "vm_edit_box_comment",
        )
        self.boxCommentAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Box Comment Line or Selection")
        )
        self.boxCommentAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Box Comment</b>"""
                """<p>Box comments the current line or the lines of the"""
                """ current selection.</p>""",
            )
        )
        self.boxCommentAct.triggered.connect(self.__editBoxComment)
        self.editActions.append(self.boxCommentAct)

        self.selectBraceAct = EricAction(
            QCoreApplication.translate("ViewManager", "Select to brace"),
            QCoreApplication.translate("ViewManager", "Select to &brace"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+E", "Edit|Select to brace"
                )
            ),
            0,
            self.editActGrp,
            "vm_edit_select_to_brace",
        )
        self.selectBraceAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Select text to the matching brace"
            )
        )
        self.selectBraceAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Select to brace</b>"""
                """<p>Select text of the current editor to the matching"""
                """ brace.</p>""",
            )
        )
        self.selectBraceAct.triggered.connect(self.__editSelectBrace)
        self.editActions.append(self.selectBraceAct)

        self.selectAllAct = EricAction(
            QCoreApplication.translate("ViewManager", "Select all"),
            EricPixmapCache.getIcon("editSelectAll"),
            QCoreApplication.translate("ViewManager", "&Select all"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+A", "Edit|Select all")
            ),
            0,
            self.editActGrp,
            "vm_edit_select_all",
        )
        self.selectAllAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Select all text")
        )
        self.selectAllAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Select All</b>"""
                """<p>Select all text of the current editor.</p>""",
            )
        )
        self.selectAllAct.triggered.connect(self.__editSelectAll)
        self.editActions.append(self.selectAllAct)

        self.deselectAllAct = EricAction(
            QCoreApplication.translate("ViewManager", "Deselect all"),
            QCoreApplication.translate("ViewManager", "&Deselect all"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Alt+Ctrl+A", "Edit|Deselect all"
                )
            ),
            0,
            self.editActGrp,
            "vm_edit_deselect_all",
        )
        self.deselectAllAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Deselect all text")
        )
        self.deselectAllAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Deselect All</b>"""
                """<p>Deselect all text of the current editor.</p>""",
            )
        )
        self.deselectAllAct.triggered.connect(self.__editDeselectAll)
        self.editActions.append(self.deselectAllAct)

        self.convertEOLAct = EricAction(
            QCoreApplication.translate("ViewManager", "Convert Line End Characters"),
            QCoreApplication.translate("ViewManager", "Convert Line End Characters"),
            0,
            0,
            self.editActGrp,
            "vm_edit_convert_eol",
        )
        self.convertEOLAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Convert Line End Characters")
        )
        self.convertEOLAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Convert Line End Characters</b>"""
                """<p>Convert the line end characters to the currently set"""
                """ type.</p>""",
            )
        )
        self.convertEOLAct.triggered.connect(self.__convertEOL)
        self.editActions.append(self.convertEOLAct)

        self.convertTabsAct = EricAction(
            QCoreApplication.translate("ViewManager", "Convert Tabs to Spaces"),
            QCoreApplication.translate("ViewManager", "Convert Tabs to Spaces"),
            0,
            0,
            self.editActGrp,
            "vm_edit_convert_tabs",
        )
        self.convertTabsAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Convert Tabs to Spaces")
        )
        self.convertTabsAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Convert Tabs to Spaces</b>"""
                """<p>Convert tabulators to the configured amount of space"""
                """ characters.</p>""",
            )
        )
        self.convertTabsAct.triggered.connect(self.__convertTabs)
        self.editActions.append(self.convertTabsAct)

        self.shortenEmptyAct = EricAction(
            QCoreApplication.translate("ViewManager", "Shorten empty lines"),
            QCoreApplication.translate("ViewManager", "Shorten empty lines"),
            0,
            0,
            self.editActGrp,
            "vm_edit_shorten_empty_lines",
        )
        self.shortenEmptyAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Shorten empty lines")
        )
        self.shortenEmptyAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Shorten empty lines</b>"""
                """<p>Shorten lines consisting solely of whitespace"""
                """ characters.</p>""",
            )
        )
        self.shortenEmptyAct.triggered.connect(self.__shortenEmptyLines)
        self.editActions.append(self.shortenEmptyAct)

        self.autoCompleteAct = EricAction(
            QCoreApplication.translate("ViewManager", "Complete"),
            QCoreApplication.translate("ViewManager", "&Complete"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+Space", "Edit|Complete")
            ),
            0,
            self.editActGrp,
            "vm_edit_autocomplete",
        )
        self.autoCompleteAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Complete current word")
        )
        self.autoCompleteAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Complete</b>"""
                """<p>Performs a completion of the word containing"""
                """ the cursor.</p>""",
            )
        )
        self.autoCompleteAct.triggered.connect(self.__editAutoComplete)
        self.editActions.append(self.autoCompleteAct)

        self.autoCompleteFromDocAct = EricAction(
            QCoreApplication.translate("ViewManager", "Complete from Document"),
            QCoreApplication.translate("ViewManager", "Complete from Document"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+Shift+Space", "Edit|Complete from Document"
                )
            ),
            0,
            self.editActGrp,
            "vm_edit_autocomplete_from_document",
        )
        self.autoCompleteFromDocAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Complete current word from Document"
            )
        )
        self.autoCompleteFromDocAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Complete from Document</b>"""
                """<p>Performs a completion from document of the word"""
                """ containing the cursor.</p>""",
            )
        )
        self.autoCompleteFromDocAct.triggered.connect(self.__editAutoCompleteFromDoc)
        self.editActions.append(self.autoCompleteFromDocAct)

        self.autoCompleteFromAPIsAct = EricAction(
            QCoreApplication.translate("ViewManager", "Complete from APIs"),
            QCoreApplication.translate("ViewManager", "Complete from APIs"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+Alt+Space", "Edit|Complete from APIs"
                )
            ),
            0,
            self.editActGrp,
            "vm_edit_autocomplete_from_api",
        )
        self.autoCompleteFromAPIsAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Complete current word from APIs")
        )
        self.autoCompleteFromAPIsAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Complete from APIs</b>"""
                """<p>Performs a completion from APIs of the word"""
                """ containing the cursor.</p>""",
            )
        )
        self.autoCompleteFromAPIsAct.triggered.connect(self.__editAutoCompleteFromAPIs)
        self.editActions.append(self.autoCompleteFromAPIsAct)

        self.autoCompleteFromAllAct = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Complete from Document and APIs"
            ),
            QCoreApplication.translate(
                "ViewManager", "Complete from Document and APIs"
            ),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager",
                    "Alt+Shift+Space",
                    "Edit|Complete from Document and APIs",
                )
            ),
            0,
            self.editActGrp,
            "vm_edit_autocomplete_from_all",
        )
        self.autoCompleteFromAllAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Complete current word from Document and APIs"
            )
        )
        self.autoCompleteFromAllAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Complete from Document and APIs</b>"""
                """<p>Performs a completion from document and APIs"""
                """ of the word containing the cursor.</p>""",
            )
        )
        self.autoCompleteFromAllAct.triggered.connect(self.__editAutoCompleteFromAll)
        self.editActions.append(self.autoCompleteFromAllAct)

        self.calltipsAct = EricAction(
            QCoreApplication.translate("ViewManager", "Calltip"),
            QCoreApplication.translate("ViewManager", "&Calltip"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Meta+Alt+Space", "Edit|Calltip"
                )
            ),
            0,
            self.editActGrp,
            "vm_edit_calltip",
        )
        self.calltipsAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Show Calltips")
        )
        self.calltipsAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Calltip</b>"""
                """<p>Show calltips based on the characters immediately to the"""
                """ left of the cursor.</p>""",
            )
        )
        self.calltipsAct.triggered.connect(self.__editShowCallTips)
        self.editActions.append(self.calltipsAct)

        self.codeInfoAct = EricAction(
            QCoreApplication.translate("ViewManager", "Code Info"),
            EricPixmapCache.getIcon("codeDocuViewer"),
            QCoreApplication.translate("ViewManager", "Code Info"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+Alt+I", "Edit|Code Info"
                )
            ),
            0,
            self.editActGrp,
            "vm_edit_codeinfo",
        )
        self.codeInfoAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Show Code Info")
        )
        self.codeInfoAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Code Info</b>"""
                """<p>Show code information based on the cursor position.</p>""",
            )
        )
        self.codeInfoAct.triggered.connect(self.__editShowCodeInfo)
        self.editActions.append(self.codeInfoAct)

        self.sortAct = EricAction(
            QCoreApplication.translate("ViewManager", "Sort"),
            QCoreApplication.translate("ViewManager", "Sort"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+Alt+S", "Edit|Sort")
            ),
            0,
            self.editActGrp,
            "vm_edit_sort",
        )
        self.sortAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Sort the lines containing the rectangular selection"
            )
        )
        self.sortAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Sort</b>"""
                """<p>Sort the lines spanned by a rectangular selection based on"""
                """ the selection ignoring leading and trailing whitespace.</p>""",
            )
        )
        self.sortAct.triggered.connect(self.__editSortSelectedLines)
        self.editActions.append(self.sortAct)

        self.docstringAct = EricAction(
            QCoreApplication.translate("ViewManager", "Generate Docstring"),
            QCoreApplication.translate("ViewManager", "Generate Docstring"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+Alt+D", "Edit|Generate Docstring"
                )
            ),
            0,
            self.editActGrp,
            "vm_edit_generate_docstring",
        )
        self.docstringAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Generate a docstring for the current function/method"
            )
        )
        self.docstringAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Generate Docstring</b>"""
                """<p>Generate a docstring for the current function/method if"""
                """ the cursor is placed on the line starting the function"""
                """ definition or on the line thereafter. The docstring is"""
                """ inserted at the appropriate position and the cursor is"""
                """ placed at the end of the description line.</p>""",
            )
        )
        self.docstringAct.triggered.connect(self.__editInsertDocstring)
        self.editActions.append(self.docstringAct)

        self.editActGrp.setEnabled(False)
        self.copyActGrp.setEnabled(False)

        ####################################################################
        ## Below follow the actions for QScintilla standard commands.
        ####################################################################

        self.esm = QSignalMapper(self)
        self.esm.mappedInt.connect(self.__editorCommand)

        self.editorActGrp = createActionGroup(self.editActGrp)

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
            QCoreApplication.translate(
                "ViewManager", "Insert new line below current line"
            ),
            QCoreApplication.translate(
                "ViewManager", "Insert new line below current line"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Shift+Return")),
            QKeySequence(QCoreApplication.translate("ViewManager", "Shift+Enter")),
            self.editorActGrp,
            "vm_edit_insert_line_below",
        )
        act.triggered.connect(self.__newLineBelow)
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
                "Extend rectangular selection to first visible character in"
                " document line",
            ),
            QCoreApplication.translate(
                "ViewManager",
                "Extend rectangular selection to first visible character in"
                " document line",
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
            self.esm.setMapping(act, QsciScintilla.SCI_HOMEEXTEND)
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

        self.editorActGrp.setEnabled(False)

        self.editLowerCaseAct = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Convert selection to lower case"
            ),
            QCoreApplication.translate(
                "ViewManager", "Convert selection to lower case"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Alt+Shift+U")),
            0,
            self.editActGrp,
            "vm_edit_convert_selection_lower",
        )
        self.esm.setMapping(self.editLowerCaseAct, QsciScintilla.SCI_LOWERCASE)
        self.editLowerCaseAct.triggered.connect(self.esm.map)
        self.editActions.append(self.editLowerCaseAct)

        self.editUpperCaseAct = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Convert selection to upper case"
            ),
            QCoreApplication.translate(
                "ViewManager", "Convert selection to upper case"
            ),
            QKeySequence(QCoreApplication.translate("ViewManager", "Ctrl+Shift+U")),
            0,
            self.editActGrp,
            "vm_edit_convert_selection_upper",
        )
        self.esm.setMapping(self.editUpperCaseAct, QsciScintilla.SCI_UPPERCASE)
        self.editUpperCaseAct.triggered.connect(self.esm.map)
        self.editActions.append(self.editUpperCaseAct)

    def initEditMenu(self):
        """
        Public method to create the Edit menu.

        @return the generated menu
        @rtype QMenu
        """
        autocompletionMenu = QMenu(
            QCoreApplication.translate("ViewManager", "Complete"), self.ui
        )
        autocompletionMenu.setTearOffEnabled(True)
        autocompletionMenu.addAction(self.autoCompleteAct)
        autocompletionMenu.addSeparator()
        autocompletionMenu.addAction(self.autoCompleteFromDocAct)
        autocompletionMenu.addAction(self.autoCompleteFromAPIsAct)
        autocompletionMenu.addAction(self.autoCompleteFromAllAct)

        menu = QMenu(QCoreApplication.translate("ViewManager", "&Edit"), self.ui)
        menu.setTearOffEnabled(True)
        menu.addAction(self.undoAct)
        menu.addAction(self.redoAct)
        menu.addAction(self.revertAct)
        menu.addSeparator()
        menu.addAction(self.cutAct)
        menu.addAction(self.copyAct)
        menu.addAction(self.pasteAct)
        menu.addAction(self.deleteAct)
        menu.addSeparator()
        menu.addAction(self.indentAct)
        menu.addAction(self.unindentAct)
        menu.addAction(self.smartIndentAct)
        menu.addSeparator()
        menu.addAction(self.commentAct)
        menu.addAction(self.uncommentAct)
        menu.addAction(self.toggleCommentAct)
        menu.addAction(self.streamCommentAct)
        menu.addAction(self.boxCommentAct)
        menu.addSeparator()
        menu.addAction(self.docstringAct)
        menu.addSeparator()
        menu.addAction(self.editUpperCaseAct)
        menu.addAction(self.editLowerCaseAct)
        menu.addAction(self.sortAct)
        menu.addSeparator()
        menu.addMenu(autocompletionMenu)
        menu.addAction(self.calltipsAct)
        menu.addAction(self.codeInfoAct)
        menu.addSeparator()
        menu.addAction(self.gotoAct)
        menu.addAction(self.gotoBraceAct)
        menu.addAction(self.gotoLastEditAct)
        menu.addAction(self.gotoPreviousDefAct)
        menu.addAction(self.gotoNextDefAct)
        menu.addSeparator()
        menu.addAction(self.selectBraceAct)
        menu.addAction(self.selectAllAct)
        menu.addAction(self.deselectAllAct)
        menu.addSeparator()
        menu.addAction(self.shortenEmptyAct)
        menu.addAction(self.convertEOLAct)
        menu.addAction(self.convertTabsAct)

        return menu

    def initEditToolbar(self, toolbarManager):
        """
        Public method to create the Edit toolbar.

        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        @return the generated toolbar
        @rtype QToolBar
        """
        tb = QToolBar(QCoreApplication.translate("ViewManager", "Edit"), self.ui)
        tb.setObjectName("EditToolbar")
        tb.setToolTip(QCoreApplication.translate("ViewManager", "Edit"))

        tb.addAction(self.undoAct)
        tb.addAction(self.redoAct)
        tb.addSeparator()
        tb.addAction(self.cutAct)
        tb.addAction(self.copyAct)
        tb.addAction(self.pasteAct)
        tb.addAction(self.deleteAct)
        tb.addSeparator()
        tb.addAction(self.commentAct)
        tb.addAction(self.uncommentAct)
        tb.addAction(self.toggleCommentAct)

        toolbarManager.addToolBar(tb, tb.windowTitle())
        toolbarManager.addAction(self.smartIndentAct, tb.windowTitle())
        toolbarManager.addAction(self.indentAct, tb.windowTitle())
        toolbarManager.addAction(self.unindentAct, tb.windowTitle())

        return tb

    ##################################################################
    ## Initialize the search related actions and the search toolbar
    ##################################################################

    def __initSearchActions(self):
        """
        Private method defining the user interface actions for the search
        commands.
        """
        self.searchActGrp = createActionGroup(self)
        self.searchOpenFilesActGrp = createActionGroup(self)

        self.searchAct = EricAction(
            QCoreApplication.translate("ViewManager", "Search"),
            EricPixmapCache.getIcon("find"),
            QCoreApplication.translate("ViewManager", "&Search..."),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+F", "Search|Search")
            ),
            0,
            self.searchActGrp,
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
            self.searchActGrp,
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
            self.searchActGrp,
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
                """<p>Search the previous occurrence of some text in the current"""
                """ editor. The previously entered searchtext and options are"""
                """ reused.</p>""",
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
            self.searchActGrp,
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

        self.searchNextWordAct = EricAction(
            QCoreApplication.translate("ViewManager", "Search current word forward"),
            EricPixmapCache.getIcon("findWordNext"),
            QCoreApplication.translate("ViewManager", "Search current word forward"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+.", "Search|Search current word forward"
                )
            ),
            0,
            self.searchActGrp,
            "vm_search_word_next",
        )
        self.searchNextWordAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Search next occurrence of the current word"
            )
        )
        self.searchNextWordAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Search current word forward</b>"""
                """<p>Search the next occurrence of the current word of the"""
                """ current editor.</p>""",
            )
        )
        self.searchNextWordAct.triggered.connect(self.__findNextWord)
        self.searchActions.append(self.searchNextWordAct)

        self.searchPrevWordAct = EricAction(
            QCoreApplication.translate("ViewManager", "Search current word backward"),
            EricPixmapCache.getIcon("findWordPrev"),
            QCoreApplication.translate("ViewManager", "Search current word backward"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+,", "Search|Search current word backward"
                )
            ),
            0,
            self.searchActGrp,
            "vm_search_word_previous",
        )
        self.searchPrevWordAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Search previous occurrence of the current word"
            )
        )
        self.searchPrevWordAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Search current word backward</b>"""
                """<p>Search the previous occurrence of the current word of the"""
                """ current editor.</p>""",
            )
        )
        self.searchPrevWordAct.triggered.connect(self.__findPrevWord)
        self.searchActions.append(self.searchPrevWordAct)

        self.replaceAct = EricAction(
            QCoreApplication.translate("ViewManager", "Replace"),
            QCoreApplication.translate("ViewManager", "&Replace..."),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+R", "Search|Replace")
            ),
            0,
            self.searchActGrp,
            "vm_search_replace",
        )
        self.replaceAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Replace some text")
        )
        self.replaceAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Replace</b>"""
                """<p>Search for some text in the current editor and replace it."""
                """ A dialog is shown to enter the searchtext, the replacement"""
                """ text and options for the search and replace.</p>""",
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
            self.searchActGrp,
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
            self.searchActGrp,
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
            self.searchActGrp,
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

        self.gotoAct = EricAction(
            QCoreApplication.translate("ViewManager", "Goto Line"),
            EricPixmapCache.getIcon("goto"),
            QCoreApplication.translate("ViewManager", "&Goto Line..."),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+G", "Search|Goto Line")
            ),
            0,
            self.searchActGrp,
            "vm_search_goto_line",
        )
        self.gotoAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Goto Line")
        )
        self.gotoAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Goto Line</b>"""
                """<p>Go to a specific line of text in the current editor."""
                """ A dialog is shown to enter the linenumber.</p>""",
            )
        )
        self.gotoAct.triggered.connect(self.__goto)
        self.searchActions.append(self.gotoAct)

        self.gotoBraceAct = EricAction(
            QCoreApplication.translate("ViewManager", "Goto Brace"),
            EricPixmapCache.getIcon("gotoBrace"),
            QCoreApplication.translate("ViewManager", "Goto &Brace"),
            QKeySequence(
                QCoreApplication.translate("ViewManager", "Ctrl+L", "Search|Goto Brace")
            ),
            0,
            self.searchActGrp,
            "vm_search_goto_brace",
        )
        self.gotoBraceAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Goto Brace")
        )
        self.gotoBraceAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Goto Brace</b>"""
                """<p>Go to the matching brace in the current editor.</p>""",
            )
        )
        self.gotoBraceAct.triggered.connect(self.__gotoBrace)
        self.searchActions.append(self.gotoBraceAct)

        self.gotoLastEditAct = EricAction(
            QCoreApplication.translate("ViewManager", "Goto Last Edit Location"),
            EricPixmapCache.getIcon("gotoLastEditPosition"),
            QCoreApplication.translate("ViewManager", "Goto Last &Edit Location"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+Shift+G", "Search|Goto Last Edit Location"
                )
            ),
            0,
            self.searchActGrp,
            "vm_search_goto_last_edit_location",
        )
        self.gotoLastEditAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Goto Last Edit Location")
        )
        self.gotoLastEditAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Goto Last Edit Location</b>"""
                """<p>Go to the location of the last edit in the current"""
                """ editor.</p>""",
            )
        )
        self.gotoLastEditAct.triggered.connect(self.__gotoLastEditPosition)
        self.searchActions.append(self.gotoLastEditAct)

        self.gotoPreviousDefAct = EricAction(
            QCoreApplication.translate("ViewManager", "Goto Previous Method or Class"),
            QCoreApplication.translate("ViewManager", "Goto Previous Method or Class"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager",
                    "Ctrl+Shift+Up",
                    "Search|Goto Previous Method or Class",
                )
            ),
            0,
            self.searchActGrp,
            "vm_search_goto_previous_method_or_class",
        )
        self.gotoPreviousDefAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Go to the previous method or class definition"
            )
        )
        self.gotoPreviousDefAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Goto Previous Method or Class</b>"""
                """<p>Goes to the line of the previous method or class"""
                """ definition and highlights the name.</p>""",
            )
        )
        self.gotoPreviousDefAct.triggered.connect(self.__gotoPreviousMethodClass)
        self.searchActions.append(self.gotoPreviousDefAct)

        self.gotoNextDefAct = EricAction(
            QCoreApplication.translate("ViewManager", "Goto Next Method or Class"),
            QCoreApplication.translate("ViewManager", "Goto Next Method or Class"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+Shift+Down", "Search|Goto Next Method or Class"
                )
            ),
            0,
            self.searchActGrp,
            "vm_search_goto_next_method_or_class",
        )
        self.gotoNextDefAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Go to the next method or class definition"
            )
        )
        self.gotoNextDefAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Goto Next Method or Class</b>"""
                """<p>Goes to the line of the next method or class definition"""
                """ and highlights the name.</p>""",
            )
        )
        self.gotoNextDefAct.triggered.connect(self.__gotoNextMethodClass)
        self.searchActions.append(self.gotoNextDefAct)

        self.searchActGrp.setEnabled(False)

        self.searchFilesAct = EricAction(
            QCoreApplication.translate("ViewManager", "Search in Files"),
            EricPixmapCache.getIcon("projectFind"),
            QCoreApplication.translate("ViewManager", "Search in &Files..."),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Shift+Ctrl+F", "Search|Search Files"
                )
            ),
            0,
            self,
            "vm_search_in_files",
        )
        self.searchFilesAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Search for a text in files")
        )
        self.searchFilesAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Search in Files</b>"""
                """<p>Search for some text in the files of a directory tree"""
                """ or the project. A window is shown to enter the searchtext"""
                """ and options for the search and to display the result.</p>""",
            )
        )
        self.searchFilesAct.triggered.connect(self.__searchFiles)
        self.searchActions.append(self.searchFilesAct)

        self.replaceFilesAct = EricAction(
            QCoreApplication.translate("ViewManager", "Replace in Files"),
            QCoreApplication.translate("ViewManager", "Replace in F&iles..."),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Shift+Ctrl+R", "Search|Replace in Files"
                )
            ),
            0,
            self,
            "vm_replace_in_files",
        )
        self.replaceFilesAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Search for a text in files and replace it"
            )
        )
        self.replaceFilesAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Replace in Files</b>"""
                """<p>Search for some text in the files of a directory tree"""
                """ or the project and replace it. A window is shown to enter"""
                """ the searchtext, the replacement text and options for the"""
                """ search and to display the result.</p>""",
            )
        )
        self.replaceFilesAct.triggered.connect(self.__replaceFiles)
        self.searchActions.append(self.replaceFilesAct)

        self.searchOpenFilesAct = EricAction(
            QCoreApplication.translate("ViewManager", "Search in Open Files"),
            EricPixmapCache.getIcon("documentFind"),
            QCoreApplication.translate("ViewManager", "Search in Open Files..."),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Meta+Ctrl+Alt+F", "Search|Search Open Files"
                )
            ),
            0,
            self.searchOpenFilesActGrp,
            "vm_search_in_open_files",
        )
        self.searchOpenFilesAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Search for a text in open files")
        )
        self.searchOpenFilesAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Search in Open Files</b>"""
                """<p>Search for some text in the currently opened files."""
                """ A window is shown to enter the search text"""
                """ and options for the search and to display the result.</p>""",
            )
        )
        self.searchOpenFilesAct.triggered.connect(self.__searchOpenFiles)
        self.searchActions.append(self.searchOpenFilesAct)

        self.replaceOpenFilesAct = EricAction(
            QCoreApplication.translate("ViewManager", "Replace in Open Files"),
            QCoreApplication.translate("ViewManager", "Replace in Open Files..."),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Meta+Ctrl+Alt+R", "Search|Replace in Open Files"
                )
            ),
            0,
            self.searchOpenFilesActGrp,
            "vm_replace_in_open_files",
        )
        self.replaceOpenFilesAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Search for a text in open files and replace it"
            )
        )
        self.replaceOpenFilesAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Replace in Open Files</b>"""
                """<p>Search for some text in the currently opened files"""
                """ and replace it. A window is shown to enter"""
                """ the search text, the replacement text and options for the"""
                """ search and to display the result.</p>""",
            )
        )
        self.replaceOpenFilesAct.triggered.connect(self.__replaceOpenFiles)
        self.searchActions.append(self.replaceOpenFilesAct)

        self.searchOpenFilesActGrp.setEnabled(False)

    def initSearchMenu(self):
        """
        Public method to create the Search menu.

        @return the generated menu
        @rtype QMenu
        """
        menu = QMenu(QCoreApplication.translate("ViewManager", "&Search"), self.ui)
        menu.setTearOffEnabled(True)
        menu.addAction(self.searchAct)
        menu.addAction(self.searchNextAct)
        menu.addAction(self.searchPrevAct)
        menu.addAction(self.searchNextWordAct)
        menu.addAction(self.searchPrevWordAct)
        menu.addAction(self.replaceAct)
        menu.addSeparator()
        menu.addAction(self.searchClearMarkersAct)
        menu.addSeparator()
        menu.addAction(self.searchFilesAct)
        menu.addAction(self.replaceFilesAct)
        menu.addSeparator()
        menu.addAction(self.searchOpenFilesAct)
        menu.addAction(self.replaceOpenFilesAct)

        return menu

    def initSearchToolbar(self, toolbarManager):
        """
        Public method to create the Search toolbar.

        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        @return generated toolbar
        @rtype QToolBar
        """
        tb = QToolBar(QCoreApplication.translate("ViewManager", "Search"), self.ui)
        tb.setObjectName("SearchToolbar")
        tb.setToolTip(QCoreApplication.translate("ViewManager", "Search"))

        tb.addAction(self.searchAct)
        tb.addAction(self.searchNextAct)
        tb.addAction(self.searchPrevAct)
        tb.addAction(self.searchNextWordAct)
        tb.addAction(self.searchPrevWordAct)
        tb.addSeparator()
        tb.addAction(self.searchClearMarkersAct)
        tb.addSeparator()
        tb.addAction(self.searchFilesAct)
        tb.addAction(self.searchOpenFilesAct)
        tb.addSeparator()
        tb.addAction(self.gotoLastEditAct)

        tb.setAllowedAreas(
            Qt.ToolBarArea.TopToolBarArea | Qt.ToolBarArea.BottomToolBarArea
        )

        toolbarManager.addToolBar(tb, tb.windowTitle())
        toolbarManager.addAction(self.gotoAct, tb.windowTitle())
        toolbarManager.addAction(self.gotoBraceAct, tb.windowTitle())
        toolbarManager.addAction(self.replaceSelectionAct, tb.windowTitle())
        toolbarManager.addAction(self.replaceAllAct, tb.windowTitle())
        toolbarManager.addAction(self.replaceAndSearchAct, tb.windowTitle())

        return tb

    ##################################################################
    ## Initialize the view related actions, view menu and toolbar
    ##################################################################

    def __initViewActions(self):
        """
        Private method defining the user interface actions for the view
        commands.
        """
        self.viewActGrp = createActionGroup(self)
        self.viewFoldActGrp = createActionGroup(self)

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

        self.toggleAllAct = EricAction(
            QCoreApplication.translate("ViewManager", "Toggle all folds"),
            QCoreApplication.translate("ViewManager", "&Toggle all folds"),
            0,
            0,
            self.viewFoldActGrp,
            "vm_view_toggle_all_folds",
        )
        self.toggleAllAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Toggle all folds")
        )
        self.toggleAllAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Toggle all folds</b>"""
                """<p>Toggle all folds of the current editor.</p>""",
            )
        )
        self.toggleAllAct.triggered.connect(self.__toggleAll)
        self.viewActions.append(self.toggleAllAct)

        self.toggleAllChildrenAct = EricAction(
            QCoreApplication.translate(
                "ViewManager", "Toggle all folds (including children)"
            ),
            QCoreApplication.translate(
                "ViewManager", "Toggle all &folds (including children)"
            ),
            0,
            0,
            self.viewFoldActGrp,
            "vm_view_toggle_all_folds_children",
        )
        self.toggleAllChildrenAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Toggle all folds (including children)"
            )
        )
        self.toggleAllChildrenAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Toggle all folds (including children)</b>"""
                """<p>Toggle all folds of the current editor including"""
                """ all children.</p>""",
            )
        )
        self.toggleAllChildrenAct.triggered.connect(self.__toggleAllChildren)
        self.viewActions.append(self.toggleAllChildrenAct)

        self.toggleCurrentAct = EricAction(
            QCoreApplication.translate("ViewManager", "Toggle current fold"),
            QCoreApplication.translate("ViewManager", "Toggle &current fold"),
            0,
            0,
            self.viewFoldActGrp,
            "vm_view_toggle_current_fold",
        )
        self.toggleCurrentAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Toggle current fold")
        )
        self.toggleCurrentAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Toggle current fold</b>"""
                """<p>Toggle the folds of the current line of the current"""
                """ editor.</p>""",
            )
        )
        self.toggleCurrentAct.triggered.connect(self.__toggleCurrent)
        self.viewActions.append(self.toggleCurrentAct)

        self.clearAllFoldsAct = EricAction(
            QCoreApplication.translate("ViewManager", "Clear all folds"),
            QCoreApplication.translate("ViewManager", "Clear &all folds"),
            0,
            0,
            self.viewFoldActGrp,
            "vm_view_clear_all_folds",
        )
        self.clearAllFoldsAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Clear all folds")
        )
        self.clearAllFoldsAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Clear all folds</b>"""
                """<p>Clear all folds of the current editor, i.e. ensure that"""
                """ all lines are displayed unfolded.</p>""",
            )
        )
        self.clearAllFoldsAct.triggered.connect(self.__clearAllFolds)
        self.viewActions.append(self.clearAllFoldsAct)

        self.unhighlightAct = EricAction(
            QCoreApplication.translate("ViewManager", "Remove all highlights"),
            EricPixmapCache.getIcon("unhighlight"),
            QCoreApplication.translate("ViewManager", "Remove all highlights"),
            0,
            0,
            self,
            "vm_view_unhighlight",
        )
        self.unhighlightAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Remove all highlights")
        )
        self.unhighlightAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Remove all highlights</b>"""
                """<p>Remove the highlights of all editors.</p>""",
            )
        )
        self.unhighlightAct.triggered.connect(self.__unhighlight)
        self.viewActions.append(self.unhighlightAct)

        self.newDocumentViewAct = EricAction(
            QCoreApplication.translate("ViewManager", "New Document View"),
            EricPixmapCache.getIcon("documentNewView"),
            QCoreApplication.translate("ViewManager", "New &Document View"),
            0,
            0,
            self,
            "vm_view_new_document_view",
        )
        self.newDocumentViewAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Open a new view of the current document"
            )
        )
        self.newDocumentViewAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>New Document View</b>"""
                """<p>Opens a new view of the current document. Both views show"""
                """ the same document. However, the cursors may be positioned"""
                """ independently.</p>""",
            )
        )
        self.newDocumentViewAct.triggered.connect(self.__newDocumentView)
        self.viewActions.append(self.newDocumentViewAct)

        self.newDocumentSplitViewAct = EricAction(
            QCoreApplication.translate(
                "ViewManager", "New Document View (with new split)"
            ),
            EricPixmapCache.getIcon("splitVertical"),
            QCoreApplication.translate(
                "ViewManager", "New Document View (with new split)"
            ),
            0,
            0,
            self,
            "vm_view_new_document_split_view",
        )
        self.newDocumentSplitViewAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Open a new view of the current document in a new split"
            )
        )
        self.newDocumentSplitViewAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>New Document View</b>"""
                """<p>Opens a new view of the current document in a new split."""
                """ Both views show the same document. However, the cursors may"""
                """ be positioned independently.</p>""",
            )
        )
        self.newDocumentSplitViewAct.triggered.connect(self.__newDocumentSplitView)
        self.viewActions.append(self.newDocumentSplitViewAct)

        self.splitViewAct = EricAction(
            QCoreApplication.translate("ViewManager", "Split view"),
            EricPixmapCache.getIcon("splitVertical"),
            QCoreApplication.translate("ViewManager", "&Split view"),
            0,
            0,
            self,
            "vm_view_split_view",
        )
        self.splitViewAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Add a split to the view")
        )
        self.splitViewAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Split view</b><p>Add a split to the view.</p>""",
            )
        )
        self.splitViewAct.triggered.connect(self.__splitView)
        self.viewActions.append(self.splitViewAct)

        self.splitOrientationAct = EricAction(
            QCoreApplication.translate("ViewManager", "Arrange horizontally"),
            QCoreApplication.translate("ViewManager", "Arrange &horizontally"),
            0,
            0,
            self,
            "vm_view_arrange_horizontally",
            True,
        )
        self.splitOrientationAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Arrange the splitted views horizontally"
            )
        )
        self.splitOrientationAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Arrange horizontally</b>"""
                """<p>Arrange the splitted views horizontally.</p>""",
            )
        )
        self.splitOrientationAct.setChecked(False)
        self.splitOrientationAct.toggled[bool].connect(self.__splitOrientation)
        self.viewActions.append(self.splitOrientationAct)

        self.splitRemoveAct = EricAction(
            QCoreApplication.translate("ViewManager", "Remove split"),
            EricPixmapCache.getIcon("remsplitVertical"),
            QCoreApplication.translate("ViewManager", "&Remove split"),
            0,
            0,
            self,
            "vm_view_remove_split",
        )
        self.splitRemoveAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Remove the current split")
        )
        self.splitRemoveAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Remove split</b><p>Remove the current split.</p>""",
            )
        )
        self.splitRemoveAct.triggered.connect(self.removeSplit)
        self.viewActions.append(self.splitRemoveAct)

        self.nextSplitAct = EricAction(
            QCoreApplication.translate("ViewManager", "Next split"),
            QCoreApplication.translate("ViewManager", "&Next split"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+Alt+N", "View|Next split"
                )
            ),
            0,
            self,
            "vm_next_split",
        )
        self.nextSplitAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Move to the next split")
        )
        self.nextSplitAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Next split</b><p>Move to the next split.</p>""",
            )
        )
        self.nextSplitAct.triggered.connect(self.nextSplit)
        self.viewActions.append(self.nextSplitAct)

        self.prevSplitAct = EricAction(
            QCoreApplication.translate("ViewManager", "Previous split"),
            QCoreApplication.translate("ViewManager", "&Previous split"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+Alt+P", "View|Previous split"
                )
            ),
            0,
            self,
            "vm_previous_split",
        )
        self.prevSplitAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Move to the previous split")
        )
        self.prevSplitAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Previous split</b><p>Move to the previous split.</p>""",
            )
        )
        self.prevSplitAct.triggered.connect(self.prevSplit)
        self.viewActions.append(self.prevSplitAct)

        self.previewAct = EricAction(
            QCoreApplication.translate("ViewManager", "Preview"),
            EricPixmapCache.getIcon("previewer"),
            QCoreApplication.translate("ViewManager", "Preview"),
            0,
            0,
            self,
            "vm_preview",
            True,
        )
        self.previewAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Preview the current file in the web browser"
            )
        )
        self.previewAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Preview</b>"""
                """<p>This opens the web browser with a preview of"""
                """ the current file.</p>""",
            )
        )
        self.previewAct.setChecked(Preferences.getUI("ShowFilePreview"))
        self.previewAct.toggled[bool].connect(self.__previewEditor)
        self.viewActions.append(self.previewAct)

        self.astViewerAct = EricAction(
            QCoreApplication.translate("ViewManager", "Python AST Viewer"),
            EricPixmapCache.getIcon("astTree"),
            QCoreApplication.translate("ViewManager", "Python AST Viewer"),
            0,
            0,
            self,
            "vm_python_ast_viewer",
            True,
        )
        self.astViewerAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Show the AST for the current Python file"
            )
        )
        self.astViewerAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Python AST Viewer</b>"""
                """<p>This opens the a tree view of the AST of the current"""
                """ Python source file.</p>""",
            )
        )
        self.astViewerAct.setChecked(False)
        self.astViewerAct.toggled[bool].connect(self.__astViewer)
        self.viewActions.append(self.astViewerAct)

        self.disViewerAct = EricAction(
            QCoreApplication.translate("ViewManager", "Python Disassembly Viewer"),
            EricPixmapCache.getIcon("disassembly"),
            QCoreApplication.translate("ViewManager", "Python Disassembly Viewer"),
            0,
            0,
            self,
            "vm_python_dis_viewer",
            True,
        )
        self.disViewerAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Show the Disassembly for the current Python file"
            )
        )
        self.disViewerAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Python Disassembly Viewer</b>"""
                """<p>This opens the a tree view of the Disassembly of the"""
                """ current Python source file.</p>""",
            )
        )
        self.disViewerAct.setChecked(False)
        self.disViewerAct.toggled[bool].connect(self.__disViewer)
        self.viewActions.append(self.disViewerAct)

        self.viewActGrp.setEnabled(False)
        self.viewFoldActGrp.setEnabled(False)
        self.unhighlightAct.setEnabled(False)
        self.splitViewAct.setEnabled(False)
        self.splitOrientationAct.setEnabled(False)
        self.splitRemoveAct.setEnabled(False)
        self.nextSplitAct.setEnabled(False)
        self.prevSplitAct.setEnabled(False)
        self.previewAct.setEnabled(True)
        self.astViewerAct.setEnabled(False)
        self.disViewerAct.setEnabled(False)
        self.newDocumentViewAct.setEnabled(False)
        self.newDocumentSplitViewAct.setEnabled(False)

        self.splitOrientationAct.setChecked(
            Preferences.getUI("SplitOrientationVertical")
        )

    def initViewMenu(self):
        """
        Public method to create the View menu.

        @return the generated menu
        @rtype QMenu
        """
        menu = QMenu(QCoreApplication.translate("ViewManager", "&View"), self.ui)
        menu.setTearOffEnabled(True)
        menu.addActions(self.viewActGrp.actions())
        menu.addSeparator()
        menu.addActions(self.viewFoldActGrp.actions())
        menu.addSeparator()
        menu.addAction(self.previewAct)
        menu.addAction(self.astViewerAct)
        menu.addAction(self.disViewerAct)
        menu.addSeparator()
        menu.addAction(self.unhighlightAct)
        menu.addSeparator()
        menu.addAction(self.newDocumentViewAct)
        if self.canSplit():
            menu.addAction(self.newDocumentSplitViewAct)
            menu.addSeparator()
            menu.addAction(self.splitViewAct)
            menu.addAction(self.splitOrientationAct)
            menu.addAction(self.splitRemoveAct)
            menu.addAction(self.nextSplitAct)
            menu.addAction(self.prevSplitAct)

        return menu

    def initViewToolbar(self, toolbarManager):
        """
        Public method to create the View toolbar.

        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        @return the generated toolbar
        @rtype QToolBar
        """
        tb = QToolBar(QCoreApplication.translate("ViewManager", "View"), self.ui)
        tb.setObjectName("ViewToolbar")
        tb.setToolTip(QCoreApplication.translate("ViewManager", "View"))

        tb.addActions(self.viewActGrp.actions())
        tb.addSeparator()
        tb.addAction(self.previewAct)
        tb.addAction(self.astViewerAct)
        tb.addAction(self.disViewerAct)
        tb.addSeparator()
        tb.addAction(self.newDocumentViewAct)
        if self.canSplit():
            tb.addAction(self.newDocumentSplitViewAct)

        toolbarManager.addToolBar(tb, tb.windowTitle())
        toolbarManager.addAction(self.unhighlightAct, tb.windowTitle())
        toolbarManager.addAction(self.splitViewAct, tb.windowTitle())
        toolbarManager.addAction(self.splitRemoveAct, tb.windowTitle())

        return tb

    ##################################################################
    ## Initialize the macro related actions and macro menu
    ##################################################################

    def __initMacroActions(self):
        """
        Private method defining the user interface actions for the macro
        commands.
        """
        self.macroActGrp = createActionGroup(self)

        self.macroStartRecAct = EricAction(
            QCoreApplication.translate("ViewManager", "Start Macro Recording"),
            QCoreApplication.translate("ViewManager", "S&tart Macro Recording"),
            0,
            0,
            self.macroActGrp,
            "vm_macro_start_recording",
        )
        self.macroStartRecAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Start Macro Recording")
        )
        self.macroStartRecAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Start Macro Recording</b>"""
                """<p>Start recording editor commands into a new macro.</p>""",
            )
        )
        self.macroStartRecAct.triggered.connect(self.__macroStartRecording)
        self.macroActions.append(self.macroStartRecAct)

        self.macroStopRecAct = EricAction(
            QCoreApplication.translate("ViewManager", "Stop Macro Recording"),
            QCoreApplication.translate("ViewManager", "Sto&p Macro Recording"),
            0,
            0,
            self.macroActGrp,
            "vm_macro_stop_recording",
        )
        self.macroStopRecAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Stop Macro Recording")
        )
        self.macroStopRecAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Stop Macro Recording</b>"""
                """<p>Stop recording editor commands into a new macro.</p>""",
            )
        )
        self.macroStopRecAct.triggered.connect(self.__macroStopRecording)
        self.macroActions.append(self.macroStopRecAct)

        self.macroRunAct = EricAction(
            QCoreApplication.translate("ViewManager", "Run Macro"),
            QCoreApplication.translate("ViewManager", "&Run Macro"),
            0,
            0,
            self.macroActGrp,
            "vm_macro_run",
        )
        self.macroRunAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Run Macro")
        )
        self.macroRunAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Run Macro</b>"""
                """<p>Run a previously recorded editor macro.</p>""",
            )
        )
        self.macroRunAct.triggered.connect(self.__macroRun)
        self.macroActions.append(self.macroRunAct)

        self.macroDeleteAct = EricAction(
            QCoreApplication.translate("ViewManager", "Delete Macro"),
            QCoreApplication.translate("ViewManager", "&Delete Macro"),
            0,
            0,
            self.macroActGrp,
            "vm_macro_delete",
        )
        self.macroDeleteAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Delete Macro")
        )
        self.macroDeleteAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Delete Macro</b>"""
                """<p>Delete a previously recorded editor macro.</p>""",
            )
        )
        self.macroDeleteAct.triggered.connect(self.__macroDelete)
        self.macroActions.append(self.macroDeleteAct)

        self.macroLoadAct = EricAction(
            QCoreApplication.translate("ViewManager", "Load Macro"),
            QCoreApplication.translate("ViewManager", "&Load Macro"),
            0,
            0,
            self.macroActGrp,
            "vm_macro_load",
        )
        self.macroLoadAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Load Macro")
        )
        self.macroLoadAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Load Macro</b><p>Load an editor macro from a file.</p>""",
            )
        )
        self.macroLoadAct.triggered.connect(self.__macroLoad)
        self.macroActions.append(self.macroLoadAct)

        self.macroSaveAct = EricAction(
            QCoreApplication.translate("ViewManager", "Save Macro"),
            QCoreApplication.translate("ViewManager", "&Save Macro"),
            0,
            0,
            self.macroActGrp,
            "vm_macro_save",
        )
        self.macroSaveAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Save Macro")
        )
        self.macroSaveAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Save Macro</b>"""
                """<p>Save a previously recorded editor macro to a file.</p>""",
            )
        )
        self.macroSaveAct.triggered.connect(self.__macroSave)
        self.macroActions.append(self.macroSaveAct)

        self.macroActGrp.setEnabled(False)

    def initMacroMenu(self):
        """
        Public method to create the Macro menu.

        @return the generated menu
        @rtype QMenu
        """
        menu = QMenu(QCoreApplication.translate("ViewManager", "&Macros"), self.ui)
        menu.setTearOffEnabled(True)
        menu.addActions(self.macroActGrp.actions())

        return menu

    #####################################################################
    ## Initialize the bookmark related actions, bookmark menu and toolbar
    #####################################################################

    def __initBookmarkActions(self):
        """
        Private method defining the user interface actions for the bookmarks
        commands.
        """
        self.bookmarkActGrp = createActionGroup(self)

        self.bookmarkToggleAct = EricAction(
            QCoreApplication.translate("ViewManager", "Toggle Bookmark"),
            EricPixmapCache.getIcon("bookmarkToggle"),
            QCoreApplication.translate("ViewManager", "&Toggle Bookmark"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Alt+Ctrl+T", "Bookmark|Toggle"
                )
            ),
            0,
            self.bookmarkActGrp,
            "vm_bookmark_toggle",
        )
        self.bookmarkToggleAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Toggle Bookmark")
        )
        self.bookmarkToggleAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Toggle Bookmark</b>"""
                """<p>Toggle a bookmark at the current line of the current"""
                """ editor.</p>""",
            )
        )
        self.bookmarkToggleAct.triggered.connect(self.__toggleBookmark)
        self.bookmarkActions.append(self.bookmarkToggleAct)

        self.bookmarkNextAct = EricAction(
            QCoreApplication.translate("ViewManager", "Next Bookmark"),
            EricPixmapCache.getIcon("bookmarkNext"),
            QCoreApplication.translate("ViewManager", "&Next Bookmark"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+PgDown", "Bookmark|Next"
                )
            ),
            0,
            self.bookmarkActGrp,
            "vm_bookmark_next",
        )
        self.bookmarkNextAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Next Bookmark")
        )
        self.bookmarkNextAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Next Bookmark</b>"""
                """<p>Go to next bookmark of the current editor.</p>""",
            )
        )
        self.bookmarkNextAct.triggered.connect(self.__nextBookmark)
        self.bookmarkActions.append(self.bookmarkNextAct)

        self.bookmarkPreviousAct = EricAction(
            QCoreApplication.translate("ViewManager", "Previous Bookmark"),
            EricPixmapCache.getIcon("bookmarkPrevious"),
            QCoreApplication.translate("ViewManager", "&Previous Bookmark"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Ctrl+PgUp", "Bookmark|Previous"
                )
            ),
            0,
            self.bookmarkActGrp,
            "vm_bookmark_previous",
        )
        self.bookmarkPreviousAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Previous Bookmark")
        )
        self.bookmarkPreviousAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Previous Bookmark</b>"""
                """<p>Go to previous bookmark of the current editor.</p>""",
            )
        )
        self.bookmarkPreviousAct.triggered.connect(self.__previousBookmark)
        self.bookmarkActions.append(self.bookmarkPreviousAct)

        self.bookmarkClearAct = EricAction(
            QCoreApplication.translate("ViewManager", "Clear Bookmarks"),
            QCoreApplication.translate("ViewManager", "&Clear Bookmarks"),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Alt+Ctrl+C", "Bookmark|Clear"
                )
            ),
            0,
            self.bookmarkActGrp,
            "vm_bookmark_clear",
        )
        self.bookmarkClearAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Clear Bookmarks")
        )
        self.bookmarkClearAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Clear Bookmarks</b>"""
                """<p>Clear bookmarks of all editors.</p>""",
            )
        )
        self.bookmarkClearAct.triggered.connect(self.__clearAllBookmarks)
        self.bookmarkActions.append(self.bookmarkClearAct)

        self.syntaxErrorGotoAct = EricAction(
            QCoreApplication.translate("ViewManager", "Goto Syntax Error"),
            EricPixmapCache.getIcon("syntaxErrorGoto"),
            QCoreApplication.translate("ViewManager", "&Goto Syntax Error"),
            0,
            0,
            self.bookmarkActGrp,
            "vm_syntaxerror_goto",
        )
        self.syntaxErrorGotoAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Goto Syntax Error")
        )
        self.syntaxErrorGotoAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Goto Syntax Error</b>"""
                """<p>Go to next syntax error of the current editor.</p>""",
            )
        )
        self.syntaxErrorGotoAct.triggered.connect(self.__gotoSyntaxError)
        self.bookmarkActions.append(self.syntaxErrorGotoAct)

        self.syntaxErrorClearAct = EricAction(
            QCoreApplication.translate("ViewManager", "Clear Syntax Errors"),
            QCoreApplication.translate("ViewManager", "Clear &Syntax Errors"),
            0,
            0,
            self.bookmarkActGrp,
            "vm_syntaxerror_clear",
        )
        self.syntaxErrorClearAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Clear Syntax Errors")
        )
        self.syntaxErrorClearAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Clear Syntax Errors</b>"""
                """<p>Clear syntax errors of all editors.</p>""",
            )
        )
        self.syntaxErrorClearAct.triggered.connect(self.__clearAllSyntaxErrors)
        self.bookmarkActions.append(self.syntaxErrorClearAct)

        self.warningsNextAct = EricAction(
            QCoreApplication.translate("ViewManager", "Next warning message"),
            EricPixmapCache.getIcon("warningNext"),
            QCoreApplication.translate("ViewManager", "&Next warning message"),
            0,
            0,
            self.bookmarkActGrp,
            "vm_warning_next",
        )
        self.warningsNextAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Next warning message")
        )
        self.warningsNextAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Next warning message</b>"""
                """<p>Go to next line of the current editor"""
                """ having a pyflakes warning.</p>""",
            )
        )
        self.warningsNextAct.triggered.connect(self.__nextWarning)
        self.bookmarkActions.append(self.warningsNextAct)

        self.warningsPreviousAct = EricAction(
            QCoreApplication.translate("ViewManager", "Previous warning message"),
            EricPixmapCache.getIcon("warningPrev"),
            QCoreApplication.translate("ViewManager", "&Previous warning message"),
            0,
            0,
            self.bookmarkActGrp,
            "vm_warning_previous",
        )
        self.warningsPreviousAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Previous warning message")
        )
        self.warningsPreviousAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Previous warning message</b>"""
                """<p>Go to previous line of the current editor"""
                """ having a pyflakes warning.</p>""",
            )
        )
        self.warningsPreviousAct.triggered.connect(self.__previousWarning)
        self.bookmarkActions.append(self.warningsPreviousAct)

        self.warningsClearAct = EricAction(
            QCoreApplication.translate("ViewManager", "Clear Warning Messages"),
            QCoreApplication.translate("ViewManager", "Clear &Warning Messages"),
            0,
            0,
            self.bookmarkActGrp,
            "vm_warnings_clear",
        )
        self.warningsClearAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Clear Warning Messages")
        )
        self.warningsClearAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Clear Warning Messages</b>"""
                """<p>Clear pyflakes warning messages of all editors.</p>""",
            )
        )
        self.warningsClearAct.triggered.connect(self.__clearAllWarnings)
        self.bookmarkActions.append(self.warningsClearAct)

        self.notcoveredNextAct = EricAction(
            QCoreApplication.translate("ViewManager", "Next uncovered line"),
            EricPixmapCache.getIcon("notcoveredNext"),
            QCoreApplication.translate("ViewManager", "&Next uncovered line"),
            0,
            0,
            self.bookmarkActGrp,
            "vm_uncovered_next",
        )
        self.notcoveredNextAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Next uncovered line")
        )
        self.notcoveredNextAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Next uncovered line</b>"""
                """<p>Go to next line of the current editor marked as not"""
                """ covered.</p>""",
            )
        )
        self.notcoveredNextAct.triggered.connect(self.__nextUncovered)
        self.bookmarkActions.append(self.notcoveredNextAct)

        self.notcoveredPreviousAct = EricAction(
            QCoreApplication.translate("ViewManager", "Previous uncovered line"),
            EricPixmapCache.getIcon("notcoveredPrev"),
            QCoreApplication.translate("ViewManager", "&Previous uncovered line"),
            0,
            0,
            self.bookmarkActGrp,
            "vm_uncovered_previous",
        )
        self.notcoveredPreviousAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Previous uncovered line")
        )
        self.notcoveredPreviousAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Previous uncovered line</b>"""
                """<p>Go to previous line of the current editor marked"""
                """ as not covered.</p>""",
            )
        )
        self.notcoveredPreviousAct.triggered.connect(self.__previousUncovered)
        self.bookmarkActions.append(self.notcoveredPreviousAct)

        self.taskNextAct = EricAction(
            QCoreApplication.translate("ViewManager", "Next Task"),
            EricPixmapCache.getIcon("taskNext"),
            QCoreApplication.translate("ViewManager", "&Next Task"),
            0,
            0,
            self.bookmarkActGrp,
            "vm_task_next",
        )
        self.taskNextAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Next Task")
        )
        self.taskNextAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Next Task</b>"""
                """<p>Go to next line of the current editor having a task.</p>""",
            )
        )
        self.taskNextAct.triggered.connect(self.__nextTask)
        self.bookmarkActions.append(self.taskNextAct)

        self.taskPreviousAct = EricAction(
            QCoreApplication.translate("ViewManager", "Previous Task"),
            EricPixmapCache.getIcon("taskPrev"),
            QCoreApplication.translate("ViewManager", "&Previous Task"),
            0,
            0,
            self.bookmarkActGrp,
            "vm_task_previous",
        )
        self.taskPreviousAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Previous Task")
        )
        self.taskPreviousAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Previous Task</b>"""
                """<p>Go to previous line of the current editor having a"""
                """ task.</p>""",
            )
        )
        self.taskPreviousAct.triggered.connect(self.__previousTask)
        self.bookmarkActions.append(self.taskPreviousAct)

        self.changeNextAct = EricAction(
            QCoreApplication.translate("ViewManager", "Next Change"),
            EricPixmapCache.getIcon("changeNext"),
            QCoreApplication.translate("ViewManager", "&Next Change"),
            0,
            0,
            self.bookmarkActGrp,
            "vm_change_next",
        )
        self.changeNextAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Next Change")
        )
        self.changeNextAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Next Change</b>"""
                """<p>Go to next line of the current editor having a change"""
                """ marker.</p>""",
            )
        )
        self.changeNextAct.triggered.connect(self.__nextChange)
        self.bookmarkActions.append(self.changeNextAct)

        self.changePreviousAct = EricAction(
            QCoreApplication.translate("ViewManager", "Previous Change"),
            EricPixmapCache.getIcon("changePrev"),
            QCoreApplication.translate("ViewManager", "&Previous Change"),
            0,
            0,
            self.bookmarkActGrp,
            "vm_change_previous",
        )
        self.changePreviousAct.setStatusTip(
            QCoreApplication.translate("ViewManager", "Previous Change")
        )
        self.changePreviousAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Previous Change</b>"""
                """<p>Go to previous line of the current editor having"""
                """ a change marker.</p>""",
            )
        )
        self.changePreviousAct.triggered.connect(self.__previousChange)
        self.bookmarkActions.append(self.changePreviousAct)

        self.bookmarkActGrp.setEnabled(False)

    def initBookmarkMenu(self):
        """
        Public method to create the Bookmark menu.

        @return the generated menu
        @rtype QMenu
        """
        menu = QMenu(QCoreApplication.translate("ViewManager", "&Bookmarks"), self.ui)
        self.bookmarksMenu = QMenu(
            QCoreApplication.translate("ViewManager", "&Bookmarks"), menu
        )
        menu.setTearOffEnabled(True)

        menu.addAction(self.bookmarkToggleAct)
        menu.addAction(self.bookmarkNextAct)
        menu.addAction(self.bookmarkPreviousAct)
        menu.addAction(self.bookmarkClearAct)
        menu.addSeparator()
        self.menuBookmarksAct = menu.addMenu(self.bookmarksMenu)
        menu.addSeparator()
        menu.addAction(self.syntaxErrorGotoAct)
        menu.addAction(self.syntaxErrorClearAct)
        menu.addSeparator()
        menu.addAction(self.warningsNextAct)
        menu.addAction(self.warningsPreviousAct)
        menu.addAction(self.warningsClearAct)
        menu.addSeparator()
        menu.addAction(self.notcoveredNextAct)
        menu.addAction(self.notcoveredPreviousAct)
        menu.addSeparator()
        menu.addAction(self.taskNextAct)
        menu.addAction(self.taskPreviousAct)
        menu.addSeparator()
        menu.addAction(self.changeNextAct)
        menu.addAction(self.changePreviousAct)

        self.bookmarksMenu.aboutToShow.connect(self.__showBookmarksMenu)
        self.bookmarksMenu.triggered.connect(self.__bookmarkSelected)
        menu.aboutToShow.connect(self.__showBookmarkMenu)

        return menu

    def initBookmarkToolbar(self, toolbarManager):
        """
        Public method to create the Bookmark toolbar.

        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        @return the generated toolbar
        @rtype QToolBar
        """
        tb = QToolBar(QCoreApplication.translate("ViewManager", "Bookmarks"), self.ui)
        tb.setObjectName("BookmarksToolbar")
        tb.setToolTip(QCoreApplication.translate("ViewManager", "Bookmarks"))

        tb.addAction(self.bookmarkToggleAct)
        tb.addAction(self.bookmarkNextAct)
        tb.addAction(self.bookmarkPreviousAct)
        tb.addSeparator()
        tb.addAction(self.syntaxErrorGotoAct)
        tb.addSeparator()
        tb.addAction(self.warningsNextAct)
        tb.addAction(self.warningsPreviousAct)
        tb.addSeparator()
        tb.addAction(self.taskNextAct)
        tb.addAction(self.taskPreviousAct)
        tb.addSeparator()
        tb.addAction(self.changeNextAct)
        tb.addAction(self.changePreviousAct)

        toolbarManager.addToolBar(tb, tb.windowTitle())
        toolbarManager.addAction(self.notcoveredNextAct, tb.windowTitle())
        toolbarManager.addAction(self.notcoveredPreviousAct, tb.windowTitle())

        return tb

    ##################################################################
    ## Initialize the spell checking related actions
    ##################################################################

    def __initSpellingActions(self):
        """
        Private method to initialize the spell checking actions.
        """
        self.spellingActGrp = createActionGroup(self)

        self.spellCheckAct = EricAction(
            QCoreApplication.translate("ViewManager", "Check spelling"),
            EricPixmapCache.getIcon("spellchecking"),
            QCoreApplication.translate("ViewManager", "Check &spelling..."),
            QKeySequence(
                QCoreApplication.translate(
                    "ViewManager", "Shift+F7", "Spelling|Spell Check"
                )
            ),
            0,
            self.spellingActGrp,
            "vm_spelling_spellcheck",
        )
        self.spellCheckAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "Perform spell check of current editor"
            )
        )
        self.spellCheckAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Check spelling</b>"""
                """<p>Perform a spell check of the current editor.</p>""",
            )
        )
        self.spellCheckAct.triggered.connect(self.__spellCheck)
        self.spellingActions.append(self.spellCheckAct)

        self.autoSpellCheckAct = EricAction(
            QCoreApplication.translate("ViewManager", "Automatic spell checking"),
            EricPixmapCache.getIcon("autospellchecking"),
            QCoreApplication.translate("ViewManager", "&Automatic spell checking"),
            0,
            0,
            self.spellingActGrp,
            "vm_spelling_autospellcheck",
            True,
        )
        self.autoSpellCheckAct.setStatusTip(
            QCoreApplication.translate(
                "ViewManager", "(De-)Activate automatic spell checking"
            )
        )
        self.autoSpellCheckAct.setWhatsThis(
            QCoreApplication.translate(
                "ViewManager",
                """<b>Automatic spell checking</b>"""
                """<p>Activate or deactivate the automatic spell checking"""
                """ function of all editors.</p>""",
            )
        )
        self.autoSpellCheckAct.setChecked(
            Preferences.getEditor("AutoSpellCheckingEnabled")
        )
        self.autoSpellCheckAct.triggered.connect(self.__setAutoSpellChecking)
        self.spellingActions.append(self.autoSpellCheckAct)

        self.__enableSpellingActions()

    def __enableSpellingActions(self):
        """
        Private method to set the enabled state of the spelling actions.
        """
        from eric7.QScintilla.SpellChecker import SpellChecker

        spellingAvailable = SpellChecker.isAvailable()

        self.spellCheckAct.setEnabled(len(self.editors) != 0 and spellingAvailable)
        self.autoSpellCheckAct.setEnabled(spellingAvailable)

    def addToExtrasMenu(self, menu):
        """
        Public method to add some actions to the Extras menu.

        @param menu reference to the menu to add actions to
        @type QMenu
        """
        self.__editSpellingMenu = QMenu(
            QCoreApplication.translate("ViewManager", "Edit Dictionary")
        )
        self.__editProjectPwlAct = self.__editSpellingMenu.addAction(
            QCoreApplication.translate("ViewManager", "Project Word List"),
            self.__editProjectPWL,
        )
        self.__editProjectPelAct = self.__editSpellingMenu.addAction(
            QCoreApplication.translate("ViewManager", "Project Exception List"),
            self.__editProjectPEL,
        )
        self.__editSpellingMenu.addSeparator()
        self.__editUserPwlAct = self.__editSpellingMenu.addAction(
            QCoreApplication.translate("ViewManager", "User Word List"),
            self.__editUserPWL,
        )
        self.__editUserPelAct = self.__editSpellingMenu.addAction(
            QCoreApplication.translate("ViewManager", "User Exception List"),
            self.__editUserPEL,
        )
        self.__editSpellingMenu.aboutToShow.connect(self.__showEditSpellingMenu)

        menu.addAction(self.spellCheckAct)
        menu.addAction(self.autoSpellCheckAct)
        menu.addMenu(self.__editSpellingMenu)
        menu.addSeparator()

    def initSpellingToolbar(self, toolbarManager):
        """
        Public method to create the Spelling toolbar.

        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        @return the generated toolbar
        @rtype QToolBar
        """
        tb = QToolBar(QCoreApplication.translate("ViewManager", "Spelling"), self.ui)
        tb.setObjectName("SpellingToolbar")
        tb.setToolTip(QCoreApplication.translate("ViewManager", "Spelling"))

        tb.addAction(self.spellCheckAct)
        tb.addAction(self.autoSpellCheckAct)

        toolbarManager.addToolBar(tb, tb.windowTitle())

        return tb

    ##################################################################
    ## Methods and slots that deal with file and window handling
    ##################################################################

    @pyqtSlot()
    def __openFiles(self):
        """
        Private slot to open some files.
        """
        from eric7.QScintilla import Lexers

        fileFilter = self._getOpenFileFilter()
        progs = EricFileDialog.getOpenFileNamesAndFilter(
            self.ui,
            QCoreApplication.translate("ViewManager", "Open Files"),
            self._getOpenStartDir(),
            Lexers.getOpenFileFiltersList(True, True),
            fileFilter,
        )[0]
        for prog in progs:
            self.openFiles(prog)

    @pyqtSlot()
    def __openRemoteFiles(self):
        """
        Private slot to open some files.
        """
        from eric7.QScintilla import Lexers

        if self.ui.isEricServerConnected():
            fileFilter = self._getOpenFileFilter()
            progs = EricServerFileDialog.getOpenFileNames(
                self.ui,
                QCoreApplication.translate("ViewManager", "Open Remote Files"),
                self._getOpenStartDir(forRemote=True),
                Lexers.getOpenFileFiltersList(True, True),
                fileFilter,
            )
            for prog in progs:
                self.openFiles(prog)
        else:
            EricMessageBox.critical(
                self.ui,
                self.tr("Open Remote Files"),
                self.tr(
                    "You must be connected to a remote eric-ide server. Aborting..."
                ),
            )

    def openFiles(self, prog):
        """
        Public slot to open some files.

        @param prog name of file to be opened
        @type str
        """
        if FileSystemUtilities.isPlainFileName(prog):
            prog = os.path.abspath(prog)
        # Open up the new files.
        self.openSourceFile(prog)

    @pyqtSlot()
    def __reloadCurrentEditor(self):
        """
        Private slot to reload the contents of the current editor.
        """
        aw = self.activeWindow()
        if aw:
            aw.reload()

    def checkDirty(self, editor, autosave=False, closeIt=False):
        """
        Public method to check the dirty status and open a message window.

        @param editor editor window to check
        @type Editor
        @param autosave flag indicating that the file should be saved
            automatically (defaults to False)
        @type bool (optional)
        @param closeIt flag indicating a check in order to close the editor
            (defaults to False)
        @type bool (optional)
        @return flag indicating successful reset of the dirty flag
        @rtype bool
        """
        if editor.isModified():
            fn = editor.getFileName()
            # ignore the dirty status, if there is more than one open editor
            # for the same file (only for closing)
            if fn and self.getOpenEditorCount(fn) > 1 and closeIt:
                return True

            if fn is None:
                fn = editor.getNoName()
                autosave = False
            if autosave:
                res = editor.saveFile()
            else:
                res = EricMessageBox.okToClearData(
                    self.ui,
                    QCoreApplication.translate("ViewManager", "File Modified"),
                    QCoreApplication.translate(
                        "ViewManager",
                        """<p>The file <b>{0}</b> has unsaved changes.</p>""",
                    ).format(fn),
                    (
                        editor.saveFile
                        if not FileSystemUtilities.isRemoteFileName(
                            editor.getFileName()
                        )
                        else None
                    ),
                )
            if res:
                self.setEditorName(editor, editor.getFileName())
            return res

        return True

    def checkAllDirty(self):
        """
        Public method to check the dirty status of all editors.

        @return flag indicating successful reset of all dirty flags
        @rtype bool
        """
        return all(self.checkDirty(editor) for editor in self.editors)

    def checkFileDirty(self, fn):
        """
        Public method to check the dirty status of an editor given its file
        name and open a message window.

        @param fn file name of editor to be checked
        @type str
        @return flag indicating successful reset of the dirty flag
        @rtype bool
        """
        for editor in self.editors:
            if FileSystemUtilities.samepath(fn, editor.getFileName()):
                break
        else:
            return True

        res = self.checkDirty(editor)
        return res

    def hasDirtyEditor(self):
        """
        Public method to ask, if any of the open editors contains unsaved
        changes.

        @return flag indicating at least one editor has unsaved changes
        @rtype bool
        """
        return any(editor.isModified() for editor in self.editors)

    def closeEditor(self, editor, ignoreDirty=False):
        """
        Public method to close an editor window.

        @param editor editor window to be closed
        @type Editor
        @param ignoreDirty flag indicating to ignore the 'dirty' status
        @type bool
        @return flag indicating success
        @rtype bool
        """
        # save file if necessary
        if not ignoreDirty and not self.checkDirty(editor, closeIt=True):
            return False

        # get the filename of the editor for later use
        fn = editor.getFileName()

        # remove the window
        editor.getAssembly().aboutToBeClosed()
        self._removeView(editor)
        self.editors.remove(editor)

        # remove the file from the monitor list
        self.removeWatchedFilePath(fn)

        # send a signal, if it was the last editor for this filename
        if fn and self.getOpenEditor(fn) is None:
            self.editorClosed.emit(fn)
        self.editorClosedEd.emit(editor)
        self.editorCountChanged.emit(len(self.editors))

        # send a signal, if it was the very last editor
        if not len(self.editors):
            self.__lastEditorClosed()
            self.lastEditorClosed.emit()

        editor.deleteLater()

        return True

    def closeCurrentWindow(self):
        """
        Public method to close the current window.

        @return flag indicating success
        @rtype bool
        """
        aw = self.activeWindow()
        if aw is None:
            return False

        res = self.closeEditor(aw)
        if res and aw == self.currentEditor:
            self.currentEditor = None

        return res

    def closeAllWindows(self, ignoreDirty=False):
        """
        Public method to close all editor windows.

        @param ignoreDirty flag indicating to ignore the 'dirty' status
        @type bool
        """
        for editor in self.editors[:]:
            self.closeEditor(editor, ignoreDirty=ignoreDirty)

    def closeWindow(self, fn, ignoreDirty=False):
        """
        Public method to close an arbitrary source editor.

        @param fn file name of the editor to be closed
        @type str
        @param ignoreDirty flag indicating to ignore the 'dirty' status
        @type bool
        @return flag indicating success
        @rtype bool
        """
        for editor in self.editors:
            if FileSystemUtilities.samepath(fn, editor.getFileName()):
                break
        else:
            return True

        res = self.closeEditor(editor, ignoreDirty=ignoreDirty)
        if res and editor == self.currentEditor:
            self.currentEditor = None

        return res

    def closeEditorWindow(self, editor):
        """
        Public method to close an arbitrary source editor.

        @param editor editor to be closed
        @type Editor
        """
        if editor is None:
            return

        res = self.closeEditor(editor)
        if res and editor == self.currentEditor:
            self.currentEditor = None

    @pyqtSlot()
    def closeDeviceEditors(self):
        """
        Public slot to close all editors related to a MicroPython device.
        """
        for editor in self.editors[:]:
            if FileSystemUtilities.isDeviceFileName(editor.getFileName()):
                self.closeEditor(editor, ignoreDirty=True)

    @pyqtSlot()
    def closeRemoteEditors(self):
        """
        Public slot to close all editors related to a connected eric-ide server.
        """
        for editor in self.editors[:]:
            if FileSystemUtilities.isRemoteFileName(editor.getFileName()):
                self.closeEditor(editor, ignoreDirty=True)

    @pyqtSlot(bool)
    def remoteConnectionChanged(self, connected):
        """
        Public slot handling a change of the connection state to an eric-ide server.

        @param connected flag indicating the connection state
        @type bool
        """
        self.openRemoteAct.setEnabled(connected)
        self.saveAsRemoteAct.setEnabled(self.saveActGrp.isEnabled() and connected)

    def exit(self):
        """
        Public method to handle the debugged program terminating.
        """
        if self.currentEditor is not None:
            self.currentEditor.highlight()
            self.currentEditor = None

        for editor in self.editors:
            editor.refreshCoverageAnnotations()

        self.__setSbFile()

    def openSourceFile(
        self,
        fn,
        lineno=-1,
        filetype="",
        selStart=0,
        selEnd=0,
        pos=0,
        addNext=False,
        indexes=None,
    ):
        """
        Public slot to display a file in an editor.

        @param fn name of file to be opened
        @type str
        @param lineno line number to place the cursor at or list of line
            numbers (cursor will be placed at the next line greater than
            the current one)
        @type int or list of int
        @param filetype type of the source file
        @type str
        @param selStart start of an area to be selected
        @type int
        @param selEnd end of an area to be selected
        @type int
        @param pos position within the line to place the cursor at
        @type int
        @param addNext flag indicating to add the file next to the current
            editor
        @type bool
        @param indexes indexes of the editor, first the split view index, second the
            index within the view
        @type tuple of two int
        @return reference to the opened editor
        @rtype Editor
        """
        try:
            newWin, editor = self.getEditor(
                fn, filetype=filetype, addNext=addNext, indexes=indexes
            )
        except (OSError, UnicodeDecodeError):
            return None

        if newWin:
            self._modificationStatusChanged(editor.isModified(), editor)
        self._checkActions(editor)

        cline, _cindex = editor.getCursorPosition()
        cline += 1
        if isinstance(lineno, list):
            if len(lineno) > 1:
                for line in lineno:
                    if line > cline:
                        break
                else:
                    line = lineno[0]
            elif len(lineno) == 1:
                line = lineno[0]
            else:
                line = -1
        else:
            line = lineno

        if line >= 0 and line != cline:
            editor.ensureVisibleTop(line)
            editor.gotoLine(line, pos)

            if selStart != selEnd:
                editor.setSelection(line - 1, selStart, line - 1, selEnd)

        # insert filename into list of recently opened files
        self.addToRecentList(fn)

        return editor

    @pyqtSlot(str, int, int)
    def openSourceFileLinePos(self, fn, lineno, pos):
        """
        Public slot to display a file in an editor at a given line and position.

        @param fn name of file to be opened
        @type str
        @param lineno line number to place the cursor at
        @type int
        @param pos position within line to position cursor at
        @type int
        """
        self.openSourceFile(fn, lineno=lineno, pos=pos + 1)

    def __connectEditor(self, editor):
        """
        Private method to establish all editor connections.

        @param editor reference to the editor object to be connected
        @type Editor
        """
        editor.modificationStatusChanged.connect(self._modificationStatusChanged)
        editor.cursorChanged.connect(
            lambda fn, line, pos: self.__cursorChanged(fn, line, pos, editor)
        )
        editor.editorSaved.connect(lambda fn: self.__editorSaved(fn, editor))
        editor.editorRenamed.connect(lambda fn: self.__editorRenamed(fn, editor))
        editor.breakpointToggled.connect(self.__breakpointToggled)
        editor.bookmarkToggled.connect(self.__bookmarkToggled)
        editor.syntaxerrorToggled.connect(self._syntaxErrorToggled)
        editor.coverageMarkersShown.connect(self.__coverageMarkersShown)
        editor.autoCompletionAPIsAvailable.connect(
            lambda a: self.__editorAutoCompletionAPIsAvailable(a, editor)
        )
        editor.undoAvailable.connect(self.undoAct.setEnabled)
        editor.redoAvailable.connect(self.redoAct.setEnabled)
        editor.taskMarkersUpdated.connect(self.__taskMarkersUpdated)
        editor.changeMarkersUpdated.connect(self.__changeMarkersUpdated)
        editor.languageChanged.connect(lambda: self.__editorConfigChanged(editor))
        editor.eolChanged.connect(lambda: self.__editorConfigChanged(editor))
        editor.encodingChanged.connect(lambda: self.__editorConfigChanged(editor))
        editor.selectionChanged.connect(
            lambda: self.__searchReplaceWidget.selectionChanged(editor)
        )
        editor.selectionChanged.connect(lambda: self.__editorSelectionChanged(editor))
        editor.lastEditPositionAvailable.connect(self.__lastEditPositionAvailable)
        editor.mouseDoubleClick.connect(
            lambda pos, buttons: self.__editorDoubleClicked(editor, pos, buttons)
        )

        editor.languageChanged.connect(lambda: self.editorLanguageChanged.emit(editor))
        editor.textChanged.connect(lambda: self.editorTextChanged.emit(editor))
        editor.zoomValueChanged.connect(lambda z: self.zoomValueChanged(z, editor))

    def newEditorView(self, fn, caller, filetype="", indexes=None):
        """
        Public method to create a new editor displaying the given document.

        @param fn filename of this view
        @type str
        @param caller reference to the editor calling this method
        @type Editor
        @param filetype type of the source file
        @type str
        @param indexes of the editor, first the split view index, second the
            index within the view
        @type tuple of two int
        @return reference to the new editor object
        @rtype Editor
        """
        editor, assembly = self.cloneEditor(caller, filetype, fn)

        self._addView(assembly, fn, caller.getNoName(), indexes=indexes)
        assembly.finishSetup()
        self._modificationStatusChanged(editor.isModified(), editor)
        self._checkActions(editor)

        return editor

    def cloneEditor(self, caller, filetype, fn):
        """
        Public method to clone an editor displaying the given document.

        @param caller reference to the editor calling this method
        @type Editor
        @param filetype type of the source file
        @type str
        @param fn filename of this view
        @type str
        @return reference to the new editor object and the new editor
            assembly object
        @rtype tuple of (Editor, EditorAssembly)
        """
        from eric7.QScintilla.EditorAssembly import EditorAssembly

        assembly = EditorAssembly(
            self.dbs,
            fn,
            self,
            filetype=filetype,
            editor=caller,
            tv=ericApp().getObject("TaskViewer"),
        )
        editor = assembly.getEditor()
        self.editors.append(editor)
        self.__connectEditor(editor)
        self.__editorOpened()
        self.editorOpened.emit(fn)
        self.editorOpenedEd.emit(editor)
        self.editorCountChanged.emit(len(self.editors))

        if caller.isModified():
            editor.setModified(True)

        return editor, assembly

    def addToRecentList(self, fn):
        """
        Public slot to add a filename to the list of recently opened files.

        @param fn name of the file to be added
        @type str
        """
        for recent in self.recent[:]:
            if (
                FileSystemUtilities.isRemoteFileName(recent) and recent == fn
            ) or FileSystemUtilities.samepath(fn, recent):
                self.recent.remove(recent)
        self.recent.insert(0, fn)
        maxRecent = Preferences.getUI("RecentNumber")
        if len(self.recent) > maxRecent:
            self.recent = self.recent[:maxRecent]
        self.__saveRecent()

    def showDebugSource(self, fn, line):
        """
        Public method to open the given file and highlight the given line in
        it.

        @param fn filename of editor to update
        @type str
        @param line line number to highlight
        @type int
        """
        if not fn.startswith("<"):
            self.openSourceFile(fn, line)
            self.setFileLine(fn, line)

    def setFileLine(self, fn, line, error=False):
        """
        Public method to update the user interface when the current program
        or line changes.

        @param fn filename of editor to update
        @type str
        @param line line number to highlight
        @type int
        @param error flag indicating an error highlight
        @type bool
        """
        try:
            newWin, self.currentEditor = self.getEditor(fn)
        except (OSError, UnicodeDecodeError):
            return

        enc = self.currentEditor.getEncoding()
        lang = self.currentEditor.getLanguage()
        eol = self.currentEditor.getEolIndicator()
        zoom = self.currentEditor.getZoom()
        self.__setSbFile(fn, line, encoding=enc, language=lang, eol=eol, zoom=zoom)

        # Change the highlighted line.
        self.currentEditor.highlight(line=line, error=error)

        self.currentEditor.highlightVisible()
        self._checkActions(self.currentEditor, False)

        if newWin:
            # insert filename into list of recently opened files
            self.addToRecentList(fn)

    def __setSbFile(
        self,
        fn=None,
        line=None,
        pos=None,
        encoding=None,
        language=None,
        eol=None,
        zoom=None,
    ):
        """
        Private method to set the file info in the status bar.

        @param fn filename to display
        @type str
        @param line line number to display
        @type int
        @param pos character position to display
        @type int
        @param encoding encoding name to display
        @type str
        @param language language to display
        @type str
        @param eol eol indicator to display
        @type str
        @param zoom zoom value
        @type int
        """
        if not fn:
            fn = ""
            writ = "  "
        else:
            if os.access(fn, os.W_OK):
                writ = "rw"
            else:
                writ = "ro"
        self.sbWritable.setText(writ)

        if line is None:
            line = ""
        self.sbLine.setText(
            QCoreApplication.translate("ViewManager", "Line: {0:5}").format(line)
        )

        if pos is None:
            pos = ""
        self.sbPos.setText(
            QCoreApplication.translate("ViewManager", "Pos: {0:5}").format(pos)
        )

        if encoding is None:
            encoding = ""
        self.sbEnc.setText(encoding)

        if language is None:
            pixmap = QPixmap()
        elif language == "":
            pixmap = EricPixmapCache.getPixmap("fileText")
        else:
            pixmap = Lexers.getLanguageIcon(language, True)
        self.sbLang.setPixmap(pixmap)
        if pixmap.isNull():
            self.sbLang.setText("" if language is None else language)
            self.sbLang.setToolTip("")
        else:
            self.sbLang.setText("")
            self.sbLang.setToolTip(
                QCoreApplication.translate("ViewManager", "Language: {0}").format(
                    language
                )
            )

        if eol is None:
            eol = ""
        self.sbEol.setPixmap(self.__eolPixmap(eol))
        self.sbEol.setToolTip(
            QCoreApplication.translate("ViewManager", "EOL Mode: {0}").format(eol)
        )

        if zoom is None:
            if QApplication.focusWidget() == ericApp().getObject("Shell"):
                aw = ericApp().getObject("Shell")
            else:
                aw = self.activeWindow()
            if aw:
                self.sbZoom.setValue(aw.getZoom())
        else:
            self.sbZoom.setValue(zoom)

    def __eolPixmap(self, eolIndicator):
        """
        Private method to get an EOL pixmap for an EOL string.

        @param eolIndicator eol indicator string
        @type str
        @return pixmap for the eol indicator
        @rtype QPixmap
        """
        if eolIndicator == "LF":
            pixmap = EricPixmapCache.getPixmap("eolLinux")
        elif eolIndicator == "CR":
            pixmap = EricPixmapCache.getPixmap("eolMac")
        elif eolIndicator == "CRLF":
            pixmap = EricPixmapCache.getPixmap("eolWindows")
        else:
            pixmap = QPixmap()
        return pixmap

    def __unhighlight(self):
        """
        Private slot to switch of all highlights.
        """
        self.unhighlight()

    def unhighlight(self, current=False):
        """
        Public method to switch off all highlights or the highlight of
        the current editor.

        @param current flag indicating only the current editor should be
            unhighlighted
        @type bool
        """
        if current:
            if self.currentEditor is not None:
                self.currentEditor.highlight()
        else:
            for editor in self.editors:
                editor.highlight()

    def getOpenFilenames(self):
        """
        Public method returning a list of the filenames of all editors.

        @return list of all opened filenames
        @rtype list of str
        """
        filenames = []
        for editor in self.editors:
            fn = editor.getFileName()
            if fn is not None and fn not in filenames:
                # only return names of existing files
                exists = (
                    True
                    if FileSystemUtilities.isRemoteFileName(fn)
                    else os.path.exists(fn)
                )
                if exists:
                    filenames.append(fn)

        return filenames

    def getEditor(self, fn, filetype="", addNext=False, indexes=None):
        """
        Public method to return the editor displaying the given file.

        If there is no editor with the given file, a new editor window is
        created.

        @param fn filename to look for
        @type str
        @param filetype type of the source file
        @type str
        @param addNext flag indicating that if a new editor needs to be
            created, it should be added next to the current editor
        @type bool
        @param indexes tuple containing the indexes of the editor, first the split
            view index, second the index within the view
        @type tuple of two int
        @return tuple of two values giving a flag indicating a new window
            creation and a reference to the editor displaying this file
        @rtype tuple of (bool, Editor)
        """
        newWin = False
        editor = self.activeWindow()
        if editor is None or not FileSystemUtilities.samepath(fn, editor.getFileName()):
            for editor in self.editors:
                if FileSystemUtilities.samepath(fn, editor.getFileName()):
                    break
            else:
                assembly = EditorAssembly(
                    self.dbs,
                    fn,
                    self,
                    filetype=filetype,
                    tv=ericApp().getObject("TaskViewer"),
                )

                self.addWatchedFilePath(fn)

                editor = assembly.getEditor()
                self.editors.append(editor)
                self.__connectEditor(editor)
                self.__editorOpened()
                self.editorOpened.emit(fn)
                self.editorOpenedEd.emit(editor)
                self.editorCountChanged.emit(len(self.editors))

                newWin = True

        if newWin:
            self._addView(assembly, fn, addNext=addNext, indexes=indexes)
            assembly.finishSetup()
        else:
            self._showView(editor.getAssembly(), fn)

        return (newWin, editor)

    def getOpenEditors(self):
        """
        Public method to get references to all open editors.

        @return list of references to all open editors
        @rtype list of Editor
        """
        return self.editors

    def getOpenEditorsCount(self):
        """
        Public method to get the number of open editors.

        @return number of open editors
        @rtype int
        """
        return len(self.editors)

    def getOpenEditor(self, fn):
        """
        Public method to return the editor displaying the given file.

        @param fn filename to look for
        @type str
        @return a reference to the editor displaying this file or None, if
            no editor was found
        @rtype Editor or None
        """
        for editor in self.editors:
            if FileSystemUtilities.samepath(fn, editor.getFileName()):
                return editor

        return None

    def getOpenEditorList(self, fn):
        """
        Public method to return a list of all editors displaying the given file.

        @param fn filename to look for
        @type str
        @return list of references to the editors displaying this file
        @rtype list of Editor
        """
        return [
            ed
            for ed in self.editors
            if FileSystemUtilities.samepath(fn, ed.getFileName())
        ]

    def getOpenEditorCount(self, fn):
        """
        Public method to return the count of editors displaying the given file.

        @param fn filename to look for
        @type str
        @return count of editors displaying this file
        @rtype int
        """
        return len(self.getOpenEditorList(fn))

    def getOpenEditorsForSession(self):
        """
        Public method to get a lists of all open editors.

        The returned list contains one list per split view. If the view manager
        cannot split the view, only one list of editors is returned.

        Note: This method should be implemented by subclasses.

        @return list of list of editor references
        @rtype list of list of Editor
        """
        return [self.editors]

    def getActiveName(self):
        """
        Public method to retrieve the filename of the active window.

        @return filename of active window
        @rtype str
        """
        aw = self.activeWindow()
        if aw:
            return aw.getFileName()
        else:
            return None

    def saveEditor(self, fn):
        """
        Public method to save a named editor file.

        @param fn filename of editor to be saved
        @type str
        @return flag indicating success
        @rtype bool
        """
        for editor in self.editors:
            if FileSystemUtilities.samepath(fn, editor.getFileName()):
                break
        else:
            return True

        if not editor.isModified():
            return True
        else:
            ok = editor.saveFile()
            return ok

    def saveEditorEd(self, ed):
        """
        Public slot to save the contents of an editor.

        @param ed editor to be saved
        @type Editor
        @return flag indicating success
        @rtype bool
        """
        if ed:
            if not ed.isModified():
                return True
            else:
                ok = ed.saveFile()
                if ok:
                    self.setEditorName(ed, ed.getFileName())
                return ok
        else:
            return False

    def saveCurrentEditor(self):
        """
        Public slot to save the contents of the current editor.
        """
        aw = self.activeWindow()
        self.saveEditorEd(aw)

    def saveAsEditorEd(self, ed):
        """
        Public slot to save the contents of an editor to a new file.

        @param ed editor to be saved
        @type Editor
        """
        if ed:
            ok = ed.saveFileAs()
            if ok:
                self.setEditorName(ed, ed.getFileName())

    def saveAsCurrentEditor(self):
        """
        Public slot to save the contents of the current editor to a new file.
        """
        aw = self.activeWindow()
        self.saveAsEditorEd(aw)

    @pyqtSlot(Editor)
    def saveAsRemoteEditorEd(self, ed):
        """
        Public slot to save the contents of an editor to a new file on a
        connected eric-ide server.

        @param ed editor to be saved
        @type Editor
        """
        if ed:
            ok = ed.saveFileAs(remote=True)
            if ok:
                self.setEditorName(ed, ed.getFileName())

    @pyqtSlot()
    def saveAsRemoteCurrentEditor(self):
        """
        Public slot to save the contents of the current editor to a new file on a
        connected eric-ide server.
        """
        aw = self.activeWindow()
        self.saveAsRemoteEditorEd(aw)

    def saveCopyEditorEd(self, ed):
        """
        Public slot to save the contents of an editor to a new copy of
        the file.

        @param ed editor to be saved
        @type Editor
        """
        if ed:
            ed.saveFileCopy()

    def saveCopyCurrentEditor(self):
        """
        Public slot to save the contents of the current editor to a new copy
        of the file.
        """
        aw = self.activeWindow()
        self.saveCopyEditorEd(aw)

    def saveEditorsList(self, editors):
        """
        Public slot to save a list of editors.

        @param editors list of editors to be saved
        @type list of Editor
        """
        for editor in editors:
            ok = editor.saveFile()
            if ok:
                self.setEditorName(editor, editor.getFileName())

    def saveAllEditors(self):
        """
        Public slot to save the contents of all editors.
        """
        for editor in self.editors:
            ok = editor.saveFile()
            if ok:
                self.setEditorName(editor, editor.getFileName())

    def __exportMenuTriggered(self, act):
        """
        Private method to handle the selection of an export format.

        @param act reference to the action that was triggered
        @type QAction
        """
        aw = self.activeWindow()
        if aw:
            exporterFormat = act.data()
            aw.exportFile(exporterFormat)

    def newEditor(self):
        """
        Public method to generate a new empty editor.

        @return reference to the new editor
        @rtype Editor
        """
        from eric7.QScintilla.EditorAssembly import EditorAssembly

        assembly = EditorAssembly(
            self.dbs, "", self, tv=ericApp().getObject("TaskViewer")
        )
        editor = assembly.getEditor()
        self.editors.append(editor)
        self.__connectEditor(editor)
        self._addView(assembly, None)
        assembly.finishSetup()
        self.__editorOpened()
        self._checkActions(editor)
        self.editorOpened.emit("")
        self.editorOpenedEd.emit(editor)
        self.editorCountChanged.emit(len(self.editors))

        return editor

    def newEditorWithText(self, text, language="", fileName=""):
        """
        Public method to generate a new editor with a given text and associated file
        name.

        @param text text for the editor
        @type str
        @param language source language (defaults to "")
        @type str (optional)
        @param fileName associated file name (defaults to "")
        @type str (optional)
        """
        from eric7.QScintilla.EditorAssembly import EditorAssembly

        assembly = EditorAssembly(
            self.dbs,
            fileName,
            vm=self,
            filetype=language,
            tv=ericApp().getObject("TaskViewer"),
        )
        editor = assembly.getEditor()
        self.editors.append(editor)
        self.__connectEditor(editor)
        self._addView(assembly, fileName)
        assembly.finishSetup()
        self.__editorOpened()
        self._checkActions(editor)
        self.editorOpened.emit(fileName)
        self.editorOpenedEd.emit(editor)
        self.editorCountChanged.emit(len(self.editors))

        editor.setText(text)
        editor.setModified(False)
        editor.clearChangeMarkers()

        self.addWatchedFilePath(fileName)

    def printEditor(self, editor):
        """
        Public slot to print an editor.

        @param editor editor to be printed
        @type Editor
        """
        if editor:
            editor.printFile()

    def printCurrentEditor(self):
        """
        Public slot to print the contents of the current editor.
        """
        aw = self.activeWindow()
        self.printEditor(aw)

    def printPreviewEditor(self, editor):
        """
        Public slot to show a print preview of an editor.

        @param editor editor to be printed
        @type Editor
        """
        if editor:
            editor.printPreviewFile()

    def printPreviewCurrentEditor(self):
        """
        Public slot to show a print preview of the current editor.
        """
        aw = self.activeWindow()
        if aw:
            aw.printPreviewFile()

    def __showFileMenu(self):
        """
        Private method to set up the file menu.
        """
        self.menuRecentAct.setEnabled(len(self.recent) > 0)

    def __showRecentMenu(self):
        """
        Private method to set up recent files menu.
        """
        self.__loadRecent()

        self.recentMenu.clear()

        for idx, rs in enumerate(self.recent, start=1):
            formatStr = "&{0:d}. {1}" if idx < 10 else "{0:d}. {1}"
            act = self.recentMenu.addAction(
                formatStr.format(
                    idx,
                    (
                        self.__remotefsInterface.compactPath(
                            rs, self.ui.maxMenuFilePathLen
                        )
                        if FileSystemUtilities.isRemoteFileName(rs)
                        else FileSystemUtilities.compactPath(
                            rs, self.ui.maxMenuFilePathLen
                        )
                    ),
                )
            )
            act.setData(rs)
            if FileSystemUtilities.isRemoteFileName(rs):
                act.setEnabled(
                    self.__remoteServer.isServerConnected
                    and self.__remotefsInterface.exists(rs)
                )
            else:
                act.setEnabled(pathlib.Path(rs).exists())

        self.recentMenu.addSeparator()
        self.recentMenu.addAction(
            QCoreApplication.translate("ViewManager", "&Clear"), self.clearRecent
        )

    def __openSourceFile(self, act):
        """
        Private method to open a file from the list of recently opened files.

        @param act reference to the action that triggered
        @type QAction
        """
        file = act.data()
        if file:
            self.openSourceFile(file)

    def clearRecent(self):
        """
        Public method to clear the recent files menu.
        """
        self.recent = []
        self.__saveRecent()

    def __showBookmarkedMenu(self):
        """
        Private method to set up bookmarked files menu.
        """
        self.bookmarkedMenu.clear()

        for rp in self.bookmarked:
            act = self.bookmarkedMenu.addAction(
                FileSystemUtilities.compactPath(rp, self.ui.maxMenuFilePathLen)
            )
            act.setData(rp)
            act.setEnabled(pathlib.Path(rp).exists())

        if len(self.bookmarked):
            self.bookmarkedMenu.addSeparator()
        self.bookmarkedMenu.addAction(
            QCoreApplication.translate("ViewManager", "&Add"), self.__addBookmarked
        )
        self.bookmarkedMenu.addAction(
            QCoreApplication.translate("ViewManager", "&Edit..."), self.__editBookmarked
        )
        self.bookmarkedMenu.addAction(
            QCoreApplication.translate("ViewManager", "&Clear"), self.__clearBookmarked
        )

    def __addBookmarked(self):
        """
        Private method to add the current file to the list of bookmarked files.
        """
        an = self.getActiveName()
        if an is not None and an not in self.bookmarked:
            self.bookmarked.append(an)

    def __editBookmarked(self):
        """
        Private method to edit the list of bookmarked files.
        """
        from .BookmarkedFilesDialog import BookmarkedFilesDialog

        dlg = BookmarkedFilesDialog(self.bookmarked, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.bookmarked = dlg.getBookmarkedFiles()

    def __clearBookmarked(self):
        """
        Private method to clear the bookmarked files menu.
        """
        self.bookmarked = []

    def projectOpened(self):
        """
        Public slot to handle the projectOpened signal.
        """
        for editor in self.editors:
            editor.projectOpened()

        self.__editProjectPwlAct.setEnabled(True)
        self.__editProjectPelAct.setEnabled(True)

    def projectClosed(self):
        """
        Public slot to handle the projectClosed signal.
        """
        for editor in self.editors:
            editor.projectClosed()

        self.__editProjectPwlAct.setEnabled(False)
        self.__editProjectPelAct.setEnabled(False)

    def projectFileRenamed(self, oldfn, newfn):
        """
        Public slot to handle the projectFileRenamed signal.

        @param oldfn old filename of the file
        @type str
        @param newfn new filename of the file
        @type str
        """
        editor = self.getOpenEditor(oldfn)
        if editor:
            editor.fileRenamed(newfn)

    def projectLexerAssociationsChanged(self):
        """
        Public slot to handle changes of the project lexer associations.
        """
        for editor in self.editors:
            editor.projectLexerAssociationsChanged()

    def enableEditorsCheckFocusIn(self, enabled):
        """
        Public method to set a flag enabling the editors to perform focus in
        checks.

        @param enabled flag indicating focus in checks should be performed
        @type bool
        """
        self.editorsCheckFocusIn = enabled

    def editorsCheckFocusInEnabled(self):
        """
        Public method returning the flag indicating editors should perform
        focus in checks.

        @return flag indicating focus in checks should be performed
        @rtype bool
        """
        return self.editorsCheckFocusIn

    def __findLocation(self):
        """
        Private method to handle the Find File action.
        """
        self.ui.showFindLocationWidget()

    def appFocusChanged(self, old, now):
        """
        Public method to handle the global change of focus.

        @param old reference to the widget loosing focus
        @type QWidget
        @param now reference to the widget gaining focus
        @type QWidget
        """
        if now is None:
            return

        if not isinstance(now, (Editor, Shell)):
            self.editActGrp.setEnabled(False)
            self.copyActGrp.setEnabled(False)
            self.viewActGrp.setEnabled(False)
            self.sbZoom.setEnabled(False)
        else:
            self.sbZoom.setEnabled(True)
            if isinstance(now, Shell):
                self.sbZoom.setValue(now.getZoom())

        if not isinstance(now, (Editor, Shell)):
            self.searchActGrp.setEnabled(False)

        if not isinstance(now, (Editor, Shell)):
            self.__lastFocusWidget = old

    ##################################################################
    ## Below are the action methods for the edit menu
    ##################################################################

    def __editUndo(self):
        """
        Private method to handle the undo action.
        """
        self.activeWindow().undo()

    def __editRedo(self):
        """
        Private method to handle the redo action.
        """
        self.activeWindow().redo()

    def __editRevert(self):
        """
        Private method to handle the revert action.
        """
        self.activeWindow().revertToUnmodified()

    def __editCut(self):
        """
        Private method to handle the cut action.
        """
        if QApplication.focusWidget() == ericApp().getObject("Shell"):
            ericApp().getObject("Shell").cut()
        else:
            self.activeWindow().cut()

    def __editCopy(self):
        """
        Private method to handle the copy action.
        """
        if QApplication.focusWidget() == ericApp().getObject("Shell"):
            ericApp().getObject("Shell").copy()
        else:
            self.activeWindow().copy()

    def __editPaste(self):
        """
        Private method to handle the paste action.
        """
        if QApplication.focusWidget() == ericApp().getObject("Shell"):
            ericApp().getObject("Shell").paste()
        else:
            self.activeWindow().paste()

    def __editDelete(self):
        """
        Private method to handle the delete action.
        """
        if QApplication.focusWidget() == ericApp().getObject("Shell"):
            ericApp().getObject("Shell").clear()
        else:
            if EricMessageBox.yesNo(
                self,
                self.tr("Clear Editor"),
                self.tr("Do you really want to delete all text of the current editor?"),
            ):
                self.activeWindow().clear()

    def __editJoin(self):
        """
        Private method to handle the join action.
        """
        self.activeWindow().joinLines()

    def __editIndent(self):
        """
        Private method to handle the indent action.
        """
        self.activeWindow().indentLineOrSelection()

    def __editUnindent(self):
        """
        Private method to handle the unindent action.
        """
        self.activeWindow().unindentLineOrSelection()

    def __editSmartIndent(self):
        """
        Private method to handle the smart indent action.
        """
        self.activeWindow().smartIndentLineOrSelection()

    def __editToggleComment(self):
        """
        Private method to handle the toggle comment action.
        """
        self.activeWindow().toggleComment()

    def __editComment(self):
        """
        Private method to handle the comment action.
        """
        self.activeWindow().commentLineOrSelection()

    def __editUncomment(self):
        """
        Private method to handle the uncomment action.
        """
        self.activeWindow().uncommentLineOrSelection()

    def __editStreamComment(self):
        """
        Private method to handle the stream comment action.
        """
        self.activeWindow().streamCommentLineOrSelection()

    def __editBoxComment(self):
        """
        Private method to handle the box comment action.
        """
        self.activeWindow().boxCommentLineOrSelection()

    def __editSelectBrace(self):
        """
        Private method to handle the select to brace action.
        """
        self.activeWindow().selectToMatchingBrace()

    def __editSelectAll(self):
        """
        Private method to handle the select all action.
        """
        self.activeWindow().selectAll(True)

    def __editDeselectAll(self):
        """
        Private method to handle the select all action.
        """
        self.activeWindow().selectAll(False)

    def __convertEOL(self):
        """
        Private method to handle the convert line end characters action.
        """
        aw = self.activeWindow()
        aw.convertEols(aw.eolMode())

    def __shortenEmptyLines(self):
        """
        Private method to handle the shorten empty lines action.
        """
        self.activeWindow().shortenEmptyLines()

    def __convertTabs(self):
        """
        Private method to handle the convert tabs to spaces action.
        """
        self.activeWindow().expandTabs()

    def __editAutoComplete(self):
        """
        Private method to handle the autocomplete action.
        """
        self.activeWindow().autoComplete()

    def __editAutoCompleteFromDoc(self):
        """
        Private method to handle the autocomplete from document action.
        """
        self.activeWindow().autoCompleteFromDocument()

    def __editAutoCompleteFromAPIs(self):
        """
        Private method to handle the autocomplete from APIs action.
        """
        self.activeWindow().autoCompleteFromAPIs()

    def __editAutoCompleteFromAll(self):
        """
        Private method to handle the autocomplete from All action.
        """
        self.activeWindow().autoCompleteFromAll()

    def __editorAutoCompletionAPIsAvailable(self, available, editor):
        """
        Private method to handle the availability of API autocompletion signal.

        @param available flag indicating the availability of API
            autocompletion
        @type bool
        @param editor reference to the editor
        @type Editor
        """
        self.autoCompleteAct.setEnabled(editor.canProvideDynamicAutoCompletion())
        self.autoCompleteFromAPIsAct.setEnabled(available)
        self.autoCompleteFromAllAct.setEnabled(available)
        self.calltipsAct.setEnabled(editor.canProvideCallTipps())

    def __editShowCallTips(self):
        """
        Private method to handle the calltips action.
        """
        self.activeWindow().callTip()

    def __editShowCodeInfo(self):
        """
        Private method to handle the code info action.
        """
        self.showEditorInfo(self.activeWindow())

    ##################################################################
    ## Below are the action and utility methods for the search menu
    ##################################################################

    def textForFind(self, getCurrentWord=True):
        """
        Public method to determine the selection or the current word for the
        next find operation.

        @param getCurrentWord flag indicating to return the current word, if
            no selected text was found
        @type bool
        @return selection or current word
        @rtype str
        """
        aw = self.activeWindow()
        if aw is None:
            return ""

        return aw.getSearchText(not getCurrentWord)

    def getSRHistory(self, key):
        """
        Public method to get the search or replace history list.

        @param key list to return (must be 'search' or 'replace')
        @type str
        @return the requested history list
        @rtype list of str
        """
        return self.srHistory[key]

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

    def __findNextWord(self):
        """
        Private slot to find the next occurrence of the current word of the
        current editor.
        """
        self.activeWindow().searchCurrentWordForward()

    def __findPrevWord(self):
        """
        Private slot to find the previous occurrence of the current word of
        the current editor.
        """
        self.activeWindow().searchCurrentWordBackward()

    def __searchClearMarkers(self):
        """
        Private method to clear the search markers of the active window.
        """
        self.activeWindow().clearSearchIndicators()

    def __goto(self):
        """
        Private method to handle the goto action.
        """
        from eric7.QScintilla.GotoDialog import GotoDialog

        aw = self.activeWindow()
        lines = aw.lines()
        curLine = aw.getCursorPosition()[0] + 1
        dlg = GotoDialog(lines, curLine, parent=self.ui, modal=True)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            aw.gotoLine(dlg.getLinenumber(), expand=True)

    def __gotoBrace(self):
        """
        Private method to handle the goto brace action.
        """
        self.activeWindow().moveToMatchingBrace()

    def __gotoLastEditPosition(self):
        """
        Private method to move the cursor to the last edit position.
        """
        self.activeWindow().gotoLastEditPosition()

    def __lastEditPositionAvailable(self):
        """
        Private slot to handle the lastEditPositionAvailable signal of an
        editor.
        """
        self.gotoLastEditAct.setEnabled(True)

    def __gotoNextMethodClass(self):
        """
        Private slot to go to the next Python/Ruby method or class definition.
        """
        self.activeWindow().gotoMethodClass(False)

    def __gotoPreviousMethodClass(self):
        """
        Private slot to go to the previous Python/Ruby method or class
        definition.
        """
        self.activeWindow().gotoMethodClass(True)

    def __searchFiles(self):
        """
        Private method to handle the search in files action.
        """
        self.ui.showFindFilesWidget(self.textForFind())

    def __replaceFiles(self):
        """
        Private method to handle the replace in files action.
        """
        self.ui.showReplaceFilesWidget(self.textForFind())

    def __searchOpenFiles(self):
        """
        Private method to handle the search in open files action.
        """
        self.ui.showFindFilesWidget(self.textForFind(), openFiles=True)

    def __replaceOpenFiles(self):
        """
        Private method to handle the replace in open files action.
        """
        self.ui.showReplaceFilesWidget(self.textForFind(), openFiles=True)

    ##################################################################
    ## Below are the action methods for the view menu
    ##################################################################

    def __zoomIn(self):
        """
        Private method to handle the zoom in action.
        """
        if QApplication.focusWidget() == ericApp().getObject("Shell"):
            ericApp().getObject("Shell").zoomIn()
        else:
            aw = self.activeWindow()
            if aw:
                aw.zoomIn()
                self.sbZoom.setValue(aw.getZoom())

    def __zoomOut(self):
        """
        Private method to handle the zoom out action.
        """
        if QApplication.focusWidget() == ericApp().getObject("Shell"):
            ericApp().getObject("Shell").zoomOut()
        else:
            aw = self.activeWindow()
            if aw:
                aw.zoomOut()
                self.sbZoom.setValue(aw.getZoom())

    def __zoomReset(self):
        """
        Private method to reset the zoom factor.
        """
        self.__zoomTo(0)

    def __zoom(self):
        """
        Private method to handle the zoom action.
        """
        aw = (
            ericApp().getObject("Shell")
            if QApplication.focusWidget() == ericApp().getObject("Shell")
            else self.activeWindow()
        )
        if aw:
            dlg = ZoomDialog(aw.getZoom(), parent=self.ui, modal=True)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                value = dlg.getZoomSize()
                self.__zoomTo(value)

    def __zoomTo(self, value):
        """
        Private slot to zoom to a given value.

        @param value zoom value to be set
        @type int
        """
        aw = (
            ericApp().getObject("Shell")
            if QApplication.focusWidget() == ericApp().getObject("Shell")
            else self.activeWindow()
        )
        if aw:
            aw.zoomTo(value)
            self.sbZoom.setValue(aw.getZoom())

    def zoomValueChanged(self, value, zoomingWidget):
        """
        Public slot to handle changes of the zoom value.

        @param value new zoom value
        @type int
        @param zoomingWidget reference to the widget triggering the slot
        @type Editor or Shell
        """
        if QApplication.focusWidget() == ericApp().getObject("Shell"):  # noqa: Y108
            aw = ericApp().getObject("Shell")
        else:
            aw = (
                self.activeWindow()
                if self.activeWindow() == QApplication.focusWidget()
                else QApplication.focusWidget()
            )
        if aw and aw == zoomingWidget:
            self.sbZoom.setValue(value)

    def __clearAllFolds(self):
        """
        Private method to handle the clear all folds action.
        """
        aw = self.activeWindow()
        if aw:
            aw.clearFolds()

    def __toggleAll(self):
        """
        Private method to handle the toggle all folds action.
        """
        aw = self.activeWindow()
        if aw:
            aw.foldAll()

    def __toggleAllChildren(self):
        """
        Private method to handle the toggle all folds (including children)
        action.
        """
        aw = self.activeWindow()
        if aw:
            aw.foldAll(True)

    def __toggleCurrent(self):
        """
        Private method to handle the toggle current fold action.
        """
        aw = self.activeWindow()
        if aw:
            aw.toggleCurrentFold()

    def __newDocumentView(self):
        """
        Private method to open a new view of the current editor.
        """
        aw = self.activeWindow()
        if aw:
            self.newEditorView(aw.getFileName(), aw, aw.getFileType())

    def __newDocumentSplitView(self):
        """
        Private method to open a new view of the current editor in a new split.
        """
        aw = self.activeWindow()
        if aw:
            self.addSplit()
            self.newEditorView(aw.getFileName(), aw, aw.getFileType())

    def __splitView(self):
        """
        Private method to handle the split view action.
        """
        self.addSplit()

    def __splitOrientation(self, checked):
        """
        Private method to handle the split orientation action.

        @param checked flag indicating the checked state of the action.
            True means splitting horizontally.
        @type bool
        """
        if checked:
            self.setSplitOrientation(Qt.Orientation.Horizontal)
            self.splitViewAct.setIcon(EricPixmapCache.getIcon("splitHorizontal"))
            self.splitRemoveAct.setIcon(EricPixmapCache.getIcon("remsplitHorizontal"))
            self.newDocumentSplitViewAct.setIcon(
                EricPixmapCache.getIcon("splitHorizontal")
            )
        else:
            self.setSplitOrientation(Qt.Orientation.Vertical)
            self.splitViewAct.setIcon(EricPixmapCache.getIcon("splitVertical"))
            self.splitRemoveAct.setIcon(EricPixmapCache.getIcon("remsplitVertical"))
            self.newDocumentSplitViewAct.setIcon(
                EricPixmapCache.getIcon("splitVertical")
            )
        Preferences.setUI("SplitOrientationVertical", checked)

    def __previewEditor(self, checked):
        """
        Private slot to handle a change of the preview selection state.

        @param checked state of the action
        @type bool
        """
        Preferences.setUI("ShowFilePreview", checked)
        self.previewStateChanged.emit(checked)

    def __astViewer(self, checked):
        """
        Private slot to handle a change of the AST Viewer selection state.

        @param checked state of the action
        @type bool
        """
        self.astViewerStateChanged.emit(checked)

    def __disViewer(self, checked):
        """
        Private slot to handle a change of the DIS Viewer selection state.

        @param checked state of the action
        @type bool
        """
        self.disViewerStateChanged.emit(checked)

    ##################################################################
    ## Below are the action methods for the macro menu
    ##################################################################

    def __macroStartRecording(self):
        """
        Private method to handle the start macro recording action.
        """
        self.activeWindow().macroRecordingStart()

    def __macroStopRecording(self):
        """
        Private method to handle the stop macro recording action.
        """
        self.activeWindow().macroRecordingStop()

    def __macroRun(self):
        """
        Private method to handle the run macro action.
        """
        self.activeWindow().macroRun()

    def __macroDelete(self):
        """
        Private method to handle the delete macro action.
        """
        self.activeWindow().macroDelete()

    def __macroLoad(self):
        """
        Private method to handle the load macro action.
        """
        self.activeWindow().macroLoad()

    def __macroSave(self):
        """
        Private method to handle the save macro action.
        """
        self.activeWindow().macroSave()

    ##################################################################
    ## Below are the action methods for the bookmarks menu
    ##################################################################

    def __toggleBookmark(self):
        """
        Private method to handle the toggle bookmark action.
        """
        self.activeWindow().menuToggleBookmark()

    def __nextBookmark(self):
        """
        Private method to handle the next bookmark action.
        """
        self.activeWindow().nextBookmark()

    def __previousBookmark(self):
        """
        Private method to handle the previous bookmark action.
        """
        self.activeWindow().previousBookmark()

    def __clearAllBookmarks(self):
        """
        Private method to handle the clear all bookmarks action.
        """
        for editor in self.editors:
            editor.clearBookmarks()

        self.bookmarkNextAct.setEnabled(False)
        self.bookmarkPreviousAct.setEnabled(False)
        self.bookmarkClearAct.setEnabled(False)

    def __showBookmarkMenu(self):
        """
        Private method to set up the bookmark menu.
        """
        bookmarksFound = 0
        filenames = self.getOpenFilenames()
        for filename in filenames:
            editor = self.getOpenEditor(filename)
            bookmarksFound = len(editor.getBookmarks()) > 0
            if bookmarksFound:
                self.menuBookmarksAct.setEnabled(True)
                return
        self.menuBookmarksAct.setEnabled(False)

    def __showBookmarksMenu(self):
        """
        Private method to handle the show bookmarks menu signal.
        """
        self.bookmarksMenu.clear()

        filenames = self.getOpenFilenames()
        for filename in sorted(filenames):
            editor = self.getOpenEditor(filename)
            for bookmark in editor.getBookmarks():
                bmSuffix = " : {0:d}".format(bookmark)
                act = self.bookmarksMenu.addAction(
                    "{0}{1}".format(
                        FileSystemUtilities.compactPath(
                            filename, self.ui.maxMenuFilePathLen - len(bmSuffix)
                        ),
                        bmSuffix,
                    )
                )
                act.setData([filename, bookmark])

    def __bookmarkSelected(self, act):
        """
        Private method to handle the bookmark selected signal.

        @param act reference to the action that triggered
        @type QAction
        """
        bmList = act.data()
        filename = bmList[0]
        line = bmList[1]
        self.openSourceFile(filename, line)

    def __bookmarkToggled(self, editor):
        """
        Private slot to handle the bookmarkToggled signal.

        It checks some bookmark actions and reemits the signal.

        @param editor editor that sent the signal
        @type Editor
        """
        if editor.hasBookmarks():
            self.bookmarkNextAct.setEnabled(True)
            self.bookmarkPreviousAct.setEnabled(True)
            self.bookmarkClearAct.setEnabled(True)
        else:
            self.bookmarkNextAct.setEnabled(False)
            self.bookmarkPreviousAct.setEnabled(False)
            self.bookmarkClearAct.setEnabled(False)
        self.bookmarkToggled.emit(editor)

    def __gotoSyntaxError(self):
        """
        Private method to handle the goto syntax error action.
        """
        self.activeWindow().gotoSyntaxError()

    def __clearAllSyntaxErrors(self):
        """
        Private method to handle the clear all syntax errors action.
        """
        for editor in self.editors:
            editor.clearSyntaxError()

    def _syntaxErrorToggled(self, editor):
        """
        Protected slot to handle the syntaxerrorToggled signal.

        It checks some syntax error actions and reemits the signal.

        @param editor editor that sent the signal
        @type Editor
        """
        if editor.hasSyntaxErrors():
            self.syntaxErrorGotoAct.setEnabled(True)
            self.syntaxErrorClearAct.setEnabled(True)
        else:
            self.syntaxErrorGotoAct.setEnabled(False)
            self.syntaxErrorClearAct.setEnabled(False)
        if editor.hasWarnings():
            self.warningsNextAct.setEnabled(True)
            self.warningsPreviousAct.setEnabled(True)
            self.warningsClearAct.setEnabled(True)
        else:
            self.warningsNextAct.setEnabled(False)
            self.warningsPreviousAct.setEnabled(False)
            self.warningsClearAct.setEnabled(False)
        self.syntaxerrorToggled.emit(editor)

    def __nextWarning(self):
        """
        Private method to handle the next warning action.
        """
        self.activeWindow().nextWarning()

    def __previousWarning(self):
        """
        Private method to handle the previous warning action.
        """
        self.activeWindow().previousWarning()

    def __clearAllWarnings(self):
        """
        Private method to handle the clear all warnings action.
        """
        for editor in self.editors:
            editor.clearWarnings()

    def __nextUncovered(self):
        """
        Private method to handle the next uncovered action.
        """
        self.activeWindow().nextUncovered()

    def __previousUncovered(self):
        """
        Private method to handle the previous uncovered action.
        """
        self.activeWindow().previousUncovered()

    def __coverageMarkersShown(self, shown):
        """
        Private slot to handle the coverageMarkersShown signal.

        @param shown flag indicating whether the markers were shown or cleared
        @type bool
        """
        if shown:
            self.notcoveredNextAct.setEnabled(True)
            self.notcoveredPreviousAct.setEnabled(True)
        else:
            self.notcoveredNextAct.setEnabled(False)
            self.notcoveredPreviousAct.setEnabled(False)

    def __taskMarkersUpdated(self, editor):
        """
        Private slot to handle the taskMarkersUpdated signal.

        @param editor editor that sent the signal
        @type Editor
        """
        if editor.hasTaskMarkers():
            self.taskNextAct.setEnabled(True)
            self.taskPreviousAct.setEnabled(True)
        else:
            self.taskNextAct.setEnabled(False)
            self.taskPreviousAct.setEnabled(False)

    def __nextTask(self):
        """
        Private method to handle the next task action.
        """
        self.activeWindow().nextTask()

    def __previousTask(self):
        """
        Private method to handle the previous task action.
        """
        self.activeWindow().previousTask()

    def __changeMarkersUpdated(self, editor):
        """
        Private slot to handle the changeMarkersUpdated signal.

        @param editor editor that sent the signal
        @type Editor
        """
        if editor.hasChangeMarkers():
            self.changeNextAct.setEnabled(True)
            self.changePreviousAct.setEnabled(True)
        else:
            self.changeNextAct.setEnabled(False)
            self.changePreviousAct.setEnabled(False)

    def __nextChange(self):
        """
        Private method to handle the next change action.
        """
        self.activeWindow().nextChange()

    def __previousChange(self):
        """
        Private method to handle the previous change action.
        """
        self.activeWindow().previousChange()

    ##################################################################
    ## Below are the action methods for the spell checking functions
    ##################################################################

    def __showEditSpellingMenu(self):
        """
        Private method to set up the edit dictionaries menu.
        """
        proj = ericApp().getObject("Project")
        projetOpen = proj.isOpen()
        pwl = ericApp().getObject("Project").getProjectDictionaries()[0]
        self.__editProjectPwlAct.setEnabled(projetOpen and bool(pwl))
        pel = ericApp().getObject("Project").getProjectDictionaries()[1]
        self.__editProjectPelAct.setEnabled(projetOpen and bool(pel))

        pwl = SpellChecker.getUserDictionaryPath()
        self.__editUserPwlAct.setEnabled(bool(pwl))
        pel = SpellChecker.getUserDictionaryPath(True)
        self.__editUserPelAct.setEnabled(bool(pel))

    def __setAutoSpellChecking(self):
        """
        Private slot to set the automatic spell checking of all editors.
        """
        enabled = self.autoSpellCheckAct.isChecked()
        Preferences.setEditor("AutoSpellCheckingEnabled", enabled)
        for editor in self.editors:
            editor.setAutoSpellChecking()

    def __spellCheck(self):
        """
        Private slot to perform a spell check of the current editor.
        """
        aw = self.activeWindow()
        if aw:
            aw.checkSpelling()

    def __editProjectPWL(self):
        """
        Private slot to edit the project word list.
        """
        pwl = ericApp().getObject("Project").getProjectDictionaries()[0]
        self.__editSpellingDictionary(pwl)

    def __editProjectPEL(self):
        """
        Private slot to edit the project exception list.
        """
        pel = ericApp().getObject("Project").getProjectDictionaries()[1]
        self.__editSpellingDictionary(pel)

    def __editUserPWL(self):
        """
        Private slot to edit the user word list.
        """
        from eric7.QScintilla.SpellChecker import SpellChecker

        pwl = SpellChecker.getUserDictionaryPath()
        self.__editSpellingDictionary(pwl)

    def __editUserPEL(self):
        """
        Private slot to edit the user exception list.
        """
        from eric7.QScintilla.SpellChecker import SpellChecker

        pel = SpellChecker.getUserDictionaryPath(True)
        self.__editSpellingDictionary(pel)

    def __editSpellingDictionary(self, dictionaryFile):
        """
        Private slot to edit the given spelling dictionary.

        @param dictionaryFile file name of the dictionary to edit
        @type str
        """
        if os.path.exists(dictionaryFile):
            try:
                with open(dictionaryFile, "r", encoding="utf-8") as f:
                    data = f.read()
            except OSError as err:
                EricMessageBox.critical(
                    self.ui,
                    QCoreApplication.translate(
                        "ViewManager", "Edit Spelling Dictionary"
                    ),
                    QCoreApplication.translate(
                        "ViewManager",
                        """<p>The spelling dictionary file <b>{0}</b> could"""
                        """ not be read.</p><p>Reason: {1}</p>""",
                    ).format(dictionaryFile, str(err)),
                )
                return

            fileInfo = (
                dictionaryFile
                if len(dictionaryFile) < 40
                else "...{0}".format(dictionaryFile[-40:])
            )

            dlg = SpellingDictionaryEditDialog(
                data,
                QCoreApplication.translate("ViewManager", "Editing {0}").format(
                    fileInfo
                ),
                parent=self.ui,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.getData()
                try:
                    with open(dictionaryFile, "w", encoding="utf-8") as f:
                        f.write(data)
                except OSError as err:
                    EricMessageBox.critical(
                        self.ui,
                        QCoreApplication.translate(
                            "ViewManager", "Edit Spelling Dictionary"
                        ),
                        QCoreApplication.translate(
                            "ViewManager",
                            """<p>The spelling dictionary file <b>{0}</b>"""
                            """ could not be written.</p>"""
                            """<p>Reason: {1}</p>""",
                        ).format(dictionaryFile, str(err)),
                    )
                    return

                self.ui.showNotification(
                    EricPixmapCache.getPixmap("spellchecking48"),
                    QCoreApplication.translate(
                        "ViewManager", "Edit Spelling Dictionary"
                    ),
                    QCoreApplication.translate(
                        "ViewManager", "The spelling dictionary was saved successfully."
                    ),
                )

    ##################################################################
    ## Below are general utility methods
    ##################################################################

    def handleResetUI(self):
        """
        Public slot to handle the resetUI signal.
        """
        editor = self.activeWindow()
        if editor is None:
            self.__setSbFile()
        else:
            line, pos = editor.getCursorPosition()
            enc = editor.getEncoding()
            lang = editor.getLanguage()
            eol = editor.getEolIndicator()
            zoom = editor.getZoom()
            self.__setSbFile(editor.getFileName(), line + 1, pos, enc, lang, eol, zoom)

    def closeViewManager(self):
        """
        Public method to shutdown the viewmanager.

        If it cannot close all editor windows, it aborts the shutdown process.

        @return flag indicating success
        @rtype bool
        """
        with contextlib.suppress(TypeError):
            ericApp().focusChanged.disconnect(self.appFocusChanged)

        self.closeAllWindows(ignoreDirty=True)
        self.currentEditor = None

        # save the list of recently opened files
        self.__saveRecent()

        # save the list of bookmarked files
        Preferences.getSettings().setValue("Bookmarked/Sources", self.bookmarked)

        res = len(self.editors) == 0

        if not res:
            ericApp().focusChanged.connect(self.appFocusChanged)

        return res

    def __lastEditorClosed(self):
        """
        Private slot to handle the lastEditorClosed signal.
        """
        self.reloadAct.setEnabled(False)
        self.closeActGrp.setEnabled(False)
        self.saveActGrp.setEnabled(False)
        self.exportersMenuAct.setEnabled(False)
        self.printAct.setEnabled(False)
        if self.printPreviewAct:
            self.printPreviewAct.setEnabled(False)
        self.editActGrp.setEnabled(False)
        self.searchActGrp.setEnabled(False)
        self.searchOpenFilesActGrp.setEnabled(False)
        self.viewActGrp.setEnabled(False)
        self.viewFoldActGrp.setEnabled(False)
        self.unhighlightAct.setEnabled(False)
        self.newDocumentViewAct.setEnabled(False)
        self.newDocumentSplitViewAct.setEnabled(False)
        self.splitViewAct.setEnabled(False)
        self.splitOrientationAct.setEnabled(False)
        self.previewAct.setEnabled(True)
        self.astViewerAct.setEnabled(False)
        self.disViewerAct.setEnabled(False)
        self.macroActGrp.setEnabled(False)
        self.bookmarkActGrp.setEnabled(False)
        self.__enableSpellingActions()
        self.__setSbFile(zoom=0)

        # remove all split views, if this is supported
        if self.canSplit():
            while self.removeSplit():
                pass

        # hide search and replace widget
        self.__searchReplaceWidget.hide()

        # hide the AST Viewer via its action
        self.astViewerAct.setChecked(False)

        # hide the DIS Viewer via its action
        self.disViewerAct.setChecked(False)

    def __editorOpened(self):
        """
        Private slot to handle the editorOpened signal.
        """
        self.closeActGrp.setEnabled(True)
        self.saveActGrp.setEnabled(True)
        self.saveAsRemoteAct.setEnabled(self.ui.isEricServerConnected())
        self.exportersMenuAct.setEnabled(True)
        self.printAct.setEnabled(True)
        if self.printPreviewAct:
            self.printPreviewAct.setEnabled(True)
        self.editActGrp.setEnabled(True)
        self.searchActGrp.setEnabled(True)
        self.searchOpenFilesActGrp.setEnabled(True)
        self.viewActGrp.setEnabled(True)
        self.viewFoldActGrp.setEnabled(True)
        self.unhighlightAct.setEnabled(True)
        self.newDocumentViewAct.setEnabled(True)
        if self.canSplit():
            self.newDocumentSplitViewAct.setEnabled(True)
            self.splitViewAct.setEnabled(True)
            self.splitOrientationAct.setEnabled(True)
        self.macroActGrp.setEnabled(True)
        self.bookmarkActGrp.setEnabled(True)
        self.__enableSpellingActions()
        self.astViewerAct.setEnabled(True)
        self.disViewerAct.setEnabled(True)

    def _checkActions(self, editor, setSb=True):
        """
        Protected slot to check some actions for their enable/disable status
        and set the statusbar info.

        @param editor editor window
        @type Editor
        @param setSb flag indicating an update of the status bar is wanted
        @type bool
        """
        if editor is not None:
            self.reloadAct.setEnabled(bool(editor.getFileName()))
            self.saveAct.setEnabled(editor.isModified())
            self.revertAct.setEnabled(editor.isModified())

            self.undoAct.setEnabled(editor.isUndoAvailable())
            self.redoAct.setEnabled(editor.isRedoAvailable())
            self.gotoLastEditAct.setEnabled(editor.isLastEditPositionAvailable())

            lex = editor.getLexer()
            if lex is not None:
                self.commentAct.setEnabled(
                    lex.canBlockComment() or lex.canStreamComment()
                )
                self.uncommentAct.setEnabled(
                    lex.canBlockComment() or lex.canStreamComment()
                )
                self.toggleCommentAct.setEnabled(
                    lex.canBlockComment() or lex.canStreamComment()
                )
                self.streamCommentAct.setEnabled(lex.canStreamComment())
                self.boxCommentAct.setEnabled(lex.canBoxComment())
            else:
                self.commentAct.setEnabled(False)
                self.uncommentAct.setEnabled(False)
                self.toggleCommentAct.setEnabled(False)
                self.streamCommentAct.setEnabled(False)
                self.boxCommentAct.setEnabled(False)

            if editor.hasBookmarks():
                self.bookmarkNextAct.setEnabled(True)
                self.bookmarkPreviousAct.setEnabled(True)
                self.bookmarkClearAct.setEnabled(True)
            else:
                self.bookmarkNextAct.setEnabled(False)
                self.bookmarkPreviousAct.setEnabled(False)
                self.bookmarkClearAct.setEnabled(False)

            if editor.hasSyntaxErrors():
                self.syntaxErrorGotoAct.setEnabled(True)
                self.syntaxErrorClearAct.setEnabled(True)
            else:
                self.syntaxErrorGotoAct.setEnabled(False)
                self.syntaxErrorClearAct.setEnabled(False)

            if editor.hasWarnings():
                self.warningsNextAct.setEnabled(True)
                self.warningsPreviousAct.setEnabled(True)
                self.warningsClearAct.setEnabled(True)
            else:
                self.warningsNextAct.setEnabled(False)
                self.warningsPreviousAct.setEnabled(False)
                self.warningsClearAct.setEnabled(False)

            if editor.hasCoverageMarkers():
                self.notcoveredNextAct.setEnabled(True)
                self.notcoveredPreviousAct.setEnabled(True)
            else:
                self.notcoveredNextAct.setEnabled(False)
                self.notcoveredPreviousAct.setEnabled(False)

            if editor.hasTaskMarkers():
                self.taskNextAct.setEnabled(True)
                self.taskPreviousAct.setEnabled(True)
            else:
                self.taskNextAct.setEnabled(False)
                self.taskPreviousAct.setEnabled(False)

            if editor.hasChangeMarkers():
                self.changeNextAct.setEnabled(True)
                self.changePreviousAct.setEnabled(True)
            else:
                self.changeNextAct.setEnabled(False)
                self.changePreviousAct.setEnabled(False)

            if editor.canAutoCompleteFromAPIs():
                self.autoCompleteFromAPIsAct.setEnabled(True)
                self.autoCompleteFromAllAct.setEnabled(True)
            else:
                self.autoCompleteFromAPIsAct.setEnabled(False)
                self.autoCompleteFromAllAct.setEnabled(False)
            self.autoCompleteAct.setEnabled(editor.canProvideDynamicAutoCompletion())
            self.calltipsAct.setEnabled(editor.canProvideCallTipps())
            self.codeInfoAct.setEnabled(self.__isEditorInfoSupportedEd(editor))

            if editor.isPyFile() or editor.isRubyFile():
                self.gotoPreviousDefAct.setEnabled(True)
                self.gotoNextDefAct.setEnabled(True)
            else:
                self.gotoPreviousDefAct.setEnabled(False)
                self.gotoNextDefAct.setEnabled(False)

            self.sortAct.setEnabled(editor.selectionIsRectangle())
            enable = editor.hasSelection()
            self.editUpperCaseAct.setEnabled(enable)
            self.editLowerCaseAct.setEnabled(enable)

            if setSb:
                line, pos = editor.getCursorPosition()
                enc = editor.getEncoding()
                lang = editor.getLanguage()
                eol = editor.getEolIndicator()
                zoom = editor.getZoom()
                self.__setSbFile(
                    editor.getFileName(), line + 1, pos, enc, lang, eol, zoom
                )

            self.checkActions.emit(editor)

        saveAllEnable = False
        for editor in self.editors:
            if editor.isModified():
                saveAllEnable = True
        self.saveAllAct.setEnabled(saveAllEnable)

    def preferencesChanged(self):
        """
        Public slot to handle the preferencesChanged signal.

        This method performs the following actions
            <ul>
            <li>reread the colours for the syntax highlighting</li>
            <li>reloads the already created API objetcs</li>
            <li><b>Note</b>: changes in viewmanager type are activated
              on an application restart.</li>
            </ul>
        """
        # reload the APIs
        self.apisManager.reloadAPIs()

        # reload editor settings
        for editor in self.editors:
            zoom = editor.getZoom()
            contractedFolds = editor.contractedFolds()
            editor.readSettings()
            editor.setContractedFolds(contractedFolds)
            editor.zoomTo(zoom)

        self.__enableSpellingActions()

    def __editorSaved(self, fn, editor):
        """
        Private slot to handle the editorSaved signal.

        It simply re-emits the signal.

        @param fn filename of the saved editor
        @type str
        @param editor reference to the editor
        @type Editor
        """
        self.editorSaved.emit(fn)
        self.editorSavedEd.emit(editor)

    def __editorRenamed(self, fn, editor):
        """
        Private slot to handle the editorRenamed signal.

        It simply re-emits the signal.

        @param fn filename of the renamed editor
        @type str
        @param editor reference to the editor
        @type Editor
        """
        self.editorRenamed.emit(fn)
        self.editorRenamedEd.emit(editor)

    def __cursorChanged(self, fn, line, pos, editor):
        """
        Private slot to handle the cursorChanged signal.

        It emits the signal cursorChanged with parameter editor.

        @param fn filename
        @type str
        @param line line number of the cursor
        @type int
        @param pos position in line of the cursor
        @type int
        @param editor reference to the editor
        @type Editor
        """
        enc = editor.getEncoding()
        lang = editor.getLanguage()
        eol = editor.getEolIndicator()
        self.__setSbFile(fn, line, pos, enc, lang, eol)
        self.cursorChanged.emit(editor)

    def __editorDoubleClicked(self, editor, pos, buttons):
        """
        Private slot handling mouse double clicks of an editor.

        Note: This method is simply a multiplexer to re-emit the signal
        with the editor prepended.

        @param editor reference to the editor, that emitted the signal
        @type Editor
        @param pos position of the double click
        @type QPoint
        @param buttons mouse buttons that were double clicked
        @type Qt.MouseButton
        """
        self.editorDoubleClickedEd.emit(editor, pos, buttons)

    def __breakpointToggled(self, editor):
        """
        Private slot to handle the breakpointToggled signal.

        It simply reemits the signal.

        @param editor editor that sent the signal
        @type Editor
        """
        self.breakpointToggled.emit(editor)

    def getActions(self, actionSetType):
        """
        Public method to get a list of all actions.

        @param actionSetType string denoting the action set to get.
            It must be one of "edit", "file", "search", "view", "window",
            "macro", "bookmark" or "spelling".
        @type str
        @return list of all actions
        @rtype list of EricAction
        """
        try:
            return self.__actions[actionSetType][:]
        except KeyError:
            return []

    def __editorCommand(self, cmd):
        """
        Private method to send an editor command to the active window.

        @param cmd the scintilla command to be sent
        @type int
        """
        focusWidget = QApplication.focusWidget()
        if focusWidget == ericApp().getObject("Shell"):
            ericApp().getObject("Shell").editorCommand(cmd)
        else:
            aw = self.activeWindow()
            if aw:
                aw.editorCommand(cmd)

    def __newLineBelow(self):
        """
        Private method to insert a new line below the current one even if
        cursor is not at the end of the line.
        """
        focusWidget = QApplication.focusWidget()
        if focusWidget == ericApp().getObject("Shell"):
            return
        else:
            aw = self.activeWindow()
            if aw:
                aw.newLineBelow()

    def __editorConfigChanged(self, editor):
        """
        Private slot to handle changes of an editor's configuration.

        @param editor reference to the editor
        @type Editor
        """
        fn = editor.getFileName()
        line, pos = editor.getCursorPosition()
        enc = editor.getEncoding()
        lang = editor.getLanguage()
        eol = editor.getEolIndicator()
        zoom = editor.getZoom()
        self.__setSbFile(
            fn, line + 1, pos, encoding=enc, language=lang, eol=eol, zoom=zoom
        )
        self._checkActions(editor, False)

    def __editorSelectionChanged(self, editor):
        """
        Private slot to handle changes of the current editors selection.

        @param editor reference to the editor
        @type Editor
        """
        self.sortAct.setEnabled(editor.selectionIsRectangle())
        enable = editor.hasSelection()
        self.editUpperCaseAct.setEnabled(enable)
        self.editLowerCaseAct.setEnabled(enable)

    def __editSortSelectedLines(self):
        """
        Private slot to sort the selected lines.
        """
        editor = self.activeWindow()
        if editor:
            editor.sortLines()

    def __editInsertDocstring(self):
        """
        Private method to insert a docstring.
        """
        editor = self.activeWindow()
        if editor:
            editor.insertDocstring()

    def showEditorInfo(self, editor):
        """
        Public method to show some information for a given editor.

        @param editor editor to show information text for
        @type Editor
        """
        documentationViewer = self.ui.documentationViewer()
        if documentationViewer:
            documentationViewer.showInfo(editor)

    def isEditorInfoSupported(self, language):
        """
        Public method to check, if a language is supported by the
        documentation viewer.

        @param language editor programming language to check
        @type str
        @return flag indicating the support status
        @rtype bool
        """
        documentationViewer = self.ui.documentationViewer()
        if documentationViewer:
            return documentationViewer.isSupportedLanguage(language)
        else:
            return False

    def __isEditorInfoSupportedEd(self, editor):
        """
        Private method to check, if an editor is supported by the
        documentation viewer.

        @param editor reference to the editor to check for
        @type Editor
        @return flag indicating the support status
        @rtype bool
        """
        language = editor.getLanguage()
        return self.isEditorInfoSupported(language)

    #######################################################################
    ## File system watcher related methods
    #######################################################################

    @pyqtSlot(str)
    def __watchedFileChanged(self, filePath):
        """
        Private slot handling a file has been modified, renamed or removed.

        @param filePath path of the file
        @type str
        """
        editorList = self.getOpenEditorList(filePath)
        if editorList:
            # read the file for the first view only
            editorList.pop(0).checkRereadFile()

            # for all other views record the modification time only
            for editor in editorList:
                editor.recordModificationTime()

    @pyqtSlot(int, str)
    def __watcherError(self, errno, strerror):
        """
        Private slot to handle an error of the file system watcher.

        @param errno numeric error code
        @type int
        @param strerror error message as provided by the operating system
        @type str
        """
        if errno == 24:
            EricMessageBox.critical(
                self,
                self.tr("File System Watcher Error"),
                self.tr(
                    """<p>The operating system resources for file system watches"""
                    """ are exhausted. This limit should be increased. On a Linux"""
                    """ system you should """
                    """<ul>"""
                    """<li>sudo nano /etc/sysctl.conf</li>"""
                    """<li>add to the bottom "fs.inotify.max_user_instances"""
                    """ = 1024"</li>"""
                    """<li>save and close the editor</li>"""
                    """<li>sudo sysctl -p</li>"""
                    """</ul></p><p>Error Message: {0}</p>"""
                ).format(strerror),
            )
        else:
            EricMessageBox.critical(
                self,
                self.tr("File System Watcher Error"),
                self.tr(
                    "The file system watcher reported an error with code <b>{0}</b>."
                    "</p><p>Error Message: {1}</p>"
                ).format(errno, strerror),
            )

    def addWatchedFilePath(self, filePath):
        """
        Public method to add a file to the list of monitored files.

        @param filePath path of the file to be added
        @type str
        """
        if (
            filePath
            and FileSystemUtilities.isPlainFileName(filePath)
            and filePath not in self.__watchedFilePaths
        ):
            watcher = EricFileSystemWatcher.instance()
            watcher.addPath(filePath)
            self.__watchedFilePaths.append(filePath)

    def removeWatchedFilePath(self, filePath):
        """
        Public method to remove a file from the list of monitored files.

        @param filePath path of the file to be removed
        @type str
        """
        if (
            filePath
            and self.getOpenEditorCount(filePath) == 0
            and FileSystemUtilities.isPlainFileName(filePath)
            and filePath in self.__watchedFilePaths
        ):
            watcher = EricFileSystemWatcher.instance()
            watcher.removePath(filePath)
            self.__watchedFilePaths.remove(filePath)

    ##################################################################
    ## Below are protected utility methods
    ##################################################################

    def _getOpenStartDir(self, forRemote=False):
        """
        Protected method to return the starting directory for a file open
        dialog.

        The appropriate starting directory is calculated
        using the following search order, until a match is found:<br />
            1: Directory of currently active editor<br />
            2: Directory of currently active Project<br />
            3: Directory defined as the workspace (only for local access)<br />
            4: CWD

        @param forRemote flag indicating to get the start directory for a remote
            operation (defaults to False)
        @type bool (optional)
        @return name of directory to start
        @rtype str
        """
        # if we have an active source, return its path
        if self.activeWindow() is not None:
            fn = self.activeWindow().getFileName()
            if forRemote and FileSystemUtilities.isRemoteFileName(fn):
                return (
                    ericApp()
                    .getObject("EricServer")
                    .getServiceInterface("FileSystem")
                    .dirname(fn)
                )
            if not forRemote and FileSystemUtilities.isPlainFileName(fn):
                return os.path.dirname(fn)

        # check, if there is an active project and return its path
        if ericApp().getObject("Project").isOpen():
            ppath = ericApp().getObject("Project").ppath
            if (forRemote and FileSystemUtilities.isRemoteFileName(ppath)) or (
                not forRemote and FileSystemUtilities.isPlainFileName(ppath)
            ):
                return ppath

        if not forRemote:
            return Preferences.getMultiProject("Workspace") or OSUtilities.getHomeDir()

        # return empty string
        return ""

    def _getOpenFileFilter(self):
        """
        Protected method to return the active filename filter for a file open
        dialog.

        The appropriate filename filter is determined by file extension of
        the currently active editor.

        @return name of the filename filter
        @rtype str
        """
        if self.activeWindow() is not None and self.activeWindow().getFileName():
            ext = os.path.splitext(self.activeWindow().getFileName())[1]
            rx = re.compile(r".*\*\.{0}[ )].*".format(ext[1:]))
            filters = Lexers.getOpenFileFiltersList()
            index = -1
            for i in range(len(filters)):
                if rx.fullmatch(filters[i]):
                    index = i
                    break
            if index == -1:
                return Preferences.getEditor("DefaultOpenFilter")
            else:
                return filters[index]
        else:
            return Preferences.getEditor("DefaultOpenFilter")

    ##################################################################
    ## Below are API handling methods
    ##################################################################

    def getAPIsManager(self):
        """
        Public method to get a reference to the APIs manager.

        @return the APIs manager object
        @rtype QScintilla.APIsManager
        """
        return self.apisManager

    #######################################################################
    ## Cooperation related methods
    #######################################################################

    def setCooperationClient(self, client):
        """
        Public method to set a reference to the cooperation client.

        @param client reference to the cooperation client
        @type CooperationClient
        """
        self.__cooperationClient = client

    def isConnected(self):
        """
        Public method to check the connection status of the IDE.

        @return flag indicating the connection status
        @rtype bool
        """
        return self.__cooperationClient.hasConnections()

    def send(self, fileName, message):
        """
        Public method to send an editor command to remote editors.

        @param fileName file name of the editor
        @type str
        @param message command message to be sent
        @type str
        """
        project = ericApp().getObject("Project")
        if project.isProjectFile(fileName):
            self.__cooperationClient.sendEditorCommand(
                project.getHash(), project.getRelativeUniversalPath(fileName), message
            )

    def receive(self, projectHash, fileName, command):
        """
        Public slot to handle received editor commands.

        @param projectHash hash of the project
        @type str
        @param fileName project relative file name of the editor
        @type str
        @param command command string
        @type str
        """
        project = ericApp().getObject("Project")
        if projectHash == project.getHash():
            fn = project.getAbsoluteUniversalPath(fileName)
            editor = self.getOpenEditor(fn)
            if editor:
                editor.receive(command)

    def shareConnected(self, connected):
        """
        Public slot to handle a change of the connected state.

        @param connected flag indicating the connected state
        @type bool
        """
        for editor in self.getOpenEditors():
            editor.shareConnected(connected)

    def shareEditor(self, share):
        """
        Public slot to set the shared status of the current editor.

        @param share flag indicating the share status
        @type bool
        """
        aw = self.activeWindow()
        if aw is not None:
            fn = aw.getFileName()
            if fn and ericApp().getObject("Project").isProjectFile(fn):
                aw.shareEditor(share)

    def startSharedEdit(self):
        """
        Public slot to start a shared edit session for the current editor.
        """
        aw = self.activeWindow()
        if aw is not None:
            fn = aw.getFileName()
            if fn and ericApp().getObject("Project").isProjectFile(fn):
                aw.startSharedEdit()

    def sendSharedEdit(self):
        """
        Public slot to end a shared edit session for the current editor and
        send the changes.
        """
        aw = self.activeWindow()
        if aw is not None:
            fn = aw.getFileName()
            if fn and ericApp().getObject("Project").isProjectFile(fn):
                aw.sendSharedEdit()

    def cancelSharedEdit(self):
        """
        Public slot to cancel a shared edit session for the current editor.
        """
        aw = self.activeWindow()
        if aw is not None:
            fn = aw.getFileName()
            if fn and ericApp().getObject("Project").isProjectFile(fn):
                aw.cancelSharedEdit()

    #######################################################################
    ## Symbols viewer related methods
    #######################################################################

    def insertSymbol(self, txt):
        """
        Public slot to insert a symbol text into the active window.

        @param txt text to be inserted
        @type str
        """
        if self.__lastFocusWidget == ericApp().getObject("Shell"):
            ericApp().getObject("Shell").insert(txt)
        else:
            aw = self.activeWindow()
            if aw is not None:
                curline, curindex = aw.getCursorPosition()
                aw.insert(txt)
                aw.setCursorPosition(curline, curindex + len(txt))

    #######################################################################
    ## Numbers viewer related methods
    #######################################################################

    def insertNumber(self, txt):
        """
        Public slot to insert a number text into the active window.

        @param txt text to be inserted
        @type str
        """
        if self.__lastFocusWidget == ericApp().getObject("Shell"):
            aw = ericApp().getObject("Shell")
            if aw.hasSelectedText():
                aw.removeSelectedText()
            aw.insert(txt)
        else:
            aw = self.activeWindow()
            if aw is not None:
                if aw.hasSelectedText():
                    aw.removeSelectedText()
                curline, curindex = aw.getCursorPosition()
                aw.insert(txt)
                aw.setCursorPosition(curline, curindex + len(txt))

    def getNumber(self):
        """
        Public method to get a number from the active window.

        @return selected text of the active window
        @rtype str
        """
        txt = ""
        if self.__lastFocusWidget == ericApp().getObject("Shell"):
            aw = ericApp().getObject("Shell")
            if aw.hasSelectedText():
                txt = aw.selectedText()
        else:
            aw = self.activeWindow()
            if aw is not None and aw.hasSelectedText():
                txt = aw.selectedText()
        return txt
