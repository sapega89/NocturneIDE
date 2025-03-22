# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the listspace viewmanager class.
"""

import itertools
import os

from PyQt6.QtCore import QEvent, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QApplication,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp
from eric7.QScintilla.Editor import Editor
from eric7.QScintilla.EditorAssembly import EditorAssembly
from eric7.ViewManager.ViewManager import ViewManager


class StackedWidget(QStackedWidget):
    """
    Class implementing a custimized StackedWidget.
    """

    def __init__(self, parent):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.editors = []

    def addWidget(self, assembly):
        """
        Public method to add a new widget.

        @param assembly editor assembly object to be added
        @type QScintilla.EditorAssembly.EditorAssembly
        """
        editor = assembly.getEditor()
        super().addWidget(assembly)
        if editor not in self.editors:
            self.editors.append(editor)

    def removeWidget(self, widget):
        """
        Public method to remove a widget.

        @param widget widget to be removed
        @type QWidget
        """
        if isinstance(widget, Editor):
            self.editors.remove(widget)
            widget = widget.getAssembly()
        super().removeWidget(widget)

    def currentWidget(self):
        """
        Public method to get a reference to the current editor.

        @return reference to the current editor
        @rtype Editor
        """
        widget = super().currentWidget()
        if widget is not None:
            widget = widget.getEditor()
        return widget

    def setCurrentWidget(self, widget):
        """
        Public method to set the current widget.

        @param widget widget to be made current
        @type QWidget
        """
        if widget is not None:
            if isinstance(widget, Editor):
                self.editors.remove(widget)
                self.editors.insert(0, widget)
                widget = widget.getAssembly()
            super().setCurrentWidget(widget)

    def setCurrentIndex(self, index):
        """
        Public method to set the current widget by its index.

        @param index index of widget to be made current
        @type int
        """
        widget = self.widget(index)
        if widget is not None:
            self.setCurrentWidget(widget)

    def nextTab(self):
        """
        Public slot used to show the next tab.
        """
        ind = self.currentIndex() + 1
        if ind == self.count():
            ind = 0

        self.setCurrentIndex(ind)
        self.currentWidget().setFocus()

    def prevTab(self):
        """
        Public slot used to show the previous tab.
        """
        ind = self.currentIndex() - 1
        if ind == -1:
            ind = self.count() - 1

        self.setCurrentIndex(ind)
        self.currentWidget().setFocus()

    def hasEditor(self, editor):
        """
        Public method to check for an editor.

        @param editor editor object to check for
        @type Editor
        @return flag indicating, whether the editor to be checked belongs
            to the list of editors managed by this stacked widget.
        @rtype bool
        """
        return editor in self.editors

    def firstEditor(self):
        """
        Public method to retrieve the first editor in the list of managed
            editors.

        @return first editor in list
        @rtype QScintilla.Editor.Editor
        """
        return len(self.editors) and self.editors[0] or None


class Listspace(ViewManager):
    """
    Class implementing the listspace viewmanager class.

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
    @signal checkActions(Editor) emitted when some actions should be checked
        for their status
    @signal cursorChanged(Editor) emitted after the cursor position of the
        active window has changed
    @signal breakpointToggled(Editor) emitted when a breakpoint is toggled.
    @signal bookmarkToggled(Editor) emitted when a bookmark is toggled.
    @signal syntaxerrorToggled(Editor) emitted when a syntax error is toggled.
    @signal previewStateChanged(bool) emitted to signal a change in the
        preview state
    @signal previewStateChanged(bool) emitted to signal a change in the
        preview state
    @signal astViewerStateChanged(bool) emitted to signal a change in the
        AST viewer state
    @signal editorLanguageChanged(Editor) emitted to signal a change of an
        editors language
    @signal editorTextChanged(Editor) emitted to signal a change of an
        editor's text
    @signal editorLineChanged(str,int) emitted to signal a change of an
        editor's current line (line is given one based)
    @signal editorLineChangedEd(Editor,int) emitted to signal a change of an
        editor's current line (line is given one based)
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
    checkActions = pyqtSignal(Editor)
    cursorChanged = pyqtSignal(Editor)
    breakpointToggled = pyqtSignal(Editor)
    bookmarkToggled = pyqtSignal(Editor)
    syntaxerrorToggled = pyqtSignal(Editor)
    previewStateChanged = pyqtSignal(bool)
    astViewerStateChanged = pyqtSignal(bool)
    editorLanguageChanged = pyqtSignal(Editor)
    editorTextChanged = pyqtSignal(Editor)
    editorLineChanged = pyqtSignal(str, int)
    editorLineChangedEd = pyqtSignal(Editor, int)

    def __init__(self, parent):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        """
        self.stacks = []

        self.__splitter = QSplitter(parent)
        ViewManager.__init__(self)
        self.__splitter.setChildrenCollapsible(False)

        self.viewlist = QListWidget(self)
        policy = self.viewlist.sizePolicy()
        policy.setHorizontalPolicy(QSizePolicy.Policy.Ignored)
        self.viewlist.setSizePolicy(policy)
        self.__splitter.addWidget(self.viewlist)
        self.viewlist.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.viewlist.currentRowChanged.connect(self.__showSelectedView)
        self.viewlist.customContextMenuRequested.connect(self.__showMenu)

        self.stackArea = QSplitter(self)
        self.stackArea.setChildrenCollapsible(False)
        self.__splitter.addWidget(self.stackArea)
        self.stackArea.setOrientation(Qt.Orientation.Vertical)
        stack = StackedWidget(self.stackArea)
        self.stackArea.addWidget(stack)
        self.stacks.append(stack)
        self.currentStack = stack
        stack.currentChanged.connect(self.__currentChanged)
        stack.installEventFilter(self)
        self.__splitter.setSizes([int(self.width() * 0.2), int(self.width() * 0.8)])
        # 20% for viewlist, 80% for the editors
        self.__inRemoveView = False

        self.__initMenu()
        self.contextMenuEditor = None
        self.contextMenuIndex = -1

    def __initMenu(self):
        """
        Private method to initialize the viewlist context menu.
        """
        self.__startMenu = QMenu(self.tr("Start"), self)
        self.__startMenu.addAction(
            EricPixmapCache.getIcon("runScript"),
            self.tr("Run Script..."),
            self.__contextMenuRunScript,
        )
        self.__startMenu.addAction(
            EricPixmapCache.getIcon("debugScript"),
            self.tr("Debug Script..."),
            self.__contextMenuDebugScript,
        )
        self.__startMenu.addAction(
            EricPixmapCache.getIcon("profileScript"),
            self.tr("Profile Script..."),
            self.__contextMenuProfileScript,
        )
        self.__startMenu.addAction(
            EricPixmapCache.getIcon("coverageScript"),
            self.tr("Coverage run of Script..."),
            self.__contextMenuCoverageScript,
        )

        self.__menu = QMenu(self)
        self.__menu.addAction(
            EricPixmapCache.getIcon("tabClose"),
            self.tr("Close"),
            self.__contextMenuClose,
        )
        self.closeOthersMenuAct = self.__menu.addAction(
            EricPixmapCache.getIcon("tabCloseOther"),
            self.tr("Close Others"),
            self.__contextMenuCloseOthers,
        )
        self.closeAboveMenuAct = self.__menu.addAction(
            self.tr("Close Editors Above"),
            self.__contextMenuCloseAbove,
        )
        self.closeBelowMenuAct = self.__menu.addAction(
            self.tr("Close Editors Below"),
            self.__contextMenuCloseBelow,
        )
        self.__menu.addAction(self.tr("Close All"), self.__contextMenuCloseAll)
        self.__menu.addSeparator()
        self.saveMenuAct = self.__menu.addAction(
            EricPixmapCache.getIcon("fileSave"), self.tr("Save"), self.__contextMenuSave
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("fileSaveAs"),
            self.tr("Save As..."),
            self.__contextMenuSaveAs,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("fileSaveAll"),
            self.tr("Save All"),
            self.__contextMenuSaveAll,
        )
        self.__menu.addSeparator()
        self.openRejectionsMenuAct = self.__menu.addAction(
            self.tr("Open 'rejection' file"), self.__contextMenuOpenRejections
        )
        self.__menu.addSeparator()
        self.__startAct = self.__menu.addMenu(self.__startMenu)
        self.__menu.addSeparator()
        self.__menu.addAction(
            EricPixmapCache.getIcon("printPreview"),
            self.tr("Print Preview"),
            self.__contextMenuPrintPreviewFile,
        )
        self.__menu.addAction(
            EricPixmapCache.getIcon("print"),
            self.tr("Print"),
            self.__contextMenuPrintFile,
        )
        self.__menu.addSeparator()
        self.copyPathAct = self.__menu.addAction(
            self.tr("Copy Path to Clipboard"), self.__contextMenuCopyPathToClipboard
        )

    def __showMenu(self, point):
        """
        Private slot to handle the customContextMenuRequested signal of
        the viewlist.

        @param point position to open the menu at
        @type QPoint
        """
        if self.editors:
            itm = self.viewlist.itemAt(point)
            if itm is not None:
                row = self.viewlist.row(itm)
                self.contextMenuEditor = self.editors[row]
                self.contextMenuIndex = row
                if self.contextMenuEditor:
                    self.saveMenuAct.setEnabled(self.contextMenuEditor.isModified())
                    fileName = self.contextMenuEditor.getFileName()
                    self.copyPathAct.setEnabled(bool(fileName))
                    if fileName:
                        rej = "{0}.rej".format(fileName)
                        self.openRejectionsMenuAct.setEnabled(os.path.exists(rej))

                        ext = os.path.splitext(fileName)[1]
                        self.__startAct.setEnabled(
                            ext in Preferences.getDebugger("Python3Extensions").split()
                        )
                    else:
                        self.openRejectionsMenuAct.setEnabled(False)
                        self.__startAct.setEnabled(False)

                    self.closeOthersMenuAct.setEnabled(self.viewlist.count() > 1)
                    self.closeAboveMenuAct.setEnabled(row > 0)
                    self.closeBelowMenuAct.setEnabled(row < self.viewlist.count() - 1)

                    self.__menu.popup(self.viewlist.mapToGlobal(point))

    def mainWidget(self):
        """
        Public method to return a reference to the main Widget of a
        specific view manager subclass.

        @return reference to the main widget
        @rtype QWidget
        """
        return self.__splitter

    def canCascade(self):
        """
        Public method to signal if cascading of managed windows is available.

        @return flag indicating cascading of windows is available
        @rtype bool
        """
        return False

    def canTile(self):
        """
        Public method to signal if tiling of managed windows is available.

        @return flag indicating tiling of windows is available
        @rtype bool
        """
        return False

    def canSplit(self):
        """
        public method to signal if splitting of the view is available.

        @return flag indicating splitting of the view is available
        @rtype bool
        """
        return True

    def tile(self):
        """
        Public method to tile the managed windows.
        """
        pass

    def cascade(self):
        """
        Public method to cascade the managed windows.
        """
        pass

    def _removeAllViews(self):
        """
        Protected method to remove all views (i.e. windows).
        """
        self.viewlist.clear()
        for win in self.editors:
            for stack in self.stacks:
                if stack.hasEditor(win):
                    stack.removeWidget(win)
                    break
            win.closeIt()

    def _removeView(self, win):
        """
        Protected method to remove a view (i.e. window).

        @param win editor window to be removed
        @type Editor
        """
        self.__inRemoveView = True
        ind = self.editors.index(win)
        itm = self.viewlist.takeItem(ind)
        if itm:
            del itm
        for stack in self.stacks:
            if stack.hasEditor(win):
                stack.removeWidget(win)
                break
        win.closeIt()
        self.__inRemoveView = False
        if ind > 0:
            ind -= 1
        else:
            if len(self.editors) > 1:
                ind = 1
            else:
                return
        stack.setCurrentWidget(stack.firstEditor())
        self._showView(self.editors[ind].getAssembly())

        aw = self.activeWindow()
        fn = aw and aw.getFileName() or None
        if fn:
            self.changeCaption.emit(fn)
            self.editorChanged.emit(fn)
            self.editorLineChanged.emit(fn, aw.getCursorPosition()[0] + 1)
        else:
            self.changeCaption.emit("")
        self.editorChangedEd.emit(aw)

    def _addView(
        self, win, fn=None, noName="", addNext=False, indexes=None  # noqa: U100
    ):
        """
        Protected method to add a view (i.e. window).

        @param win editor assembly to be added
        @type EditorAssembly
        @param fn filename of this editor
        @type str
        @param noName name to be used for an unnamed editor
        @type str
        @param addNext flag indicating to add the view next to the current
            view (unused)
        @type bool
        @param indexes of the editor, first the split view index, second the
            index within the view
        @type tuple of two int
        """
        editor = win.getEditor()
        if not fn:
            if not noName:
                self.untitledCount += 1
                noName = self.tr("Untitled {0}").format(self.untitledCount)
            self.viewlist.addItem(noName)
            editor.setNoName(noName)
        else:
            txt = os.path.basename(fn)
            if editor.checkReadOnly():
                txt = self.tr("{0} (ro)").format(txt)
            itm = QListWidgetItem(txt)
            itm.setToolTip(fn)
            self.viewlist.addItem(itm)
        if indexes:
            if indexes[0] < len(self.stacks):
                stack = self.stacks[indexes[0]]
            else:
                stack = self.stacks[-1]
            stack.addWidget(win)
        else:
            self.currentStack.addWidget(win)
            self.currentStack.setCurrentWidget(win)
        editor.captionChanged.connect(self.__captionChange)
        editor.cursorLineChanged.connect(
            lambda lineno: self.__cursorLineChanged(lineno, editor)
        )

        index = self.editors.index(editor)
        self.viewlist.setCurrentRow(index)
        editor.setFocus()
        if fn:
            self.changeCaption.emit(fn)
            self.editorChanged.emit(fn)
            self.editorLineChanged.emit(fn, editor.getCursorPosition()[0] + 1)
        else:
            self.changeCaption.emit("")
        self.editorChangedEd.emit(editor)

    def __captionChange(self, _cap, editor):
        """
        Private method to handle caption change signals from the editor.

        Updates the listwidget text to reflect the new caption information.

        @param _cap caption for the editor (unused)
        @type str
        @param editor Editor to update the caption for
        @type Editor
        """
        fn = editor.getFileName()
        if fn:
            self.setEditorName(editor, fn)

    def __cursorLineChanged(self, lineno, editor):
        """
        Private slot to handle a change of the current editor's cursor line.

        @param lineno line number of the editor's cursor (zero based)
        @type int
        @param editor reference to the editor
        @type Editor
        """
        if editor:
            fn = editor.getFileName()
            if fn:
                self.editorLineChanged.emit(fn, lineno + 1)
            self.editorLineChangedEd.emit(editor, lineno + 1)

    def _showView(self, win, fn=None):
        """
        Protected method to show a view (i.e. window).

        @param win editor assembly to be shown
        @type EditorAssembly
        @param fn filename of this editor
        @type string
        """
        editor = win.getEditor()
        for stack in self.stacks:
            if stack.hasEditor(editor):
                stack.setCurrentWidget(win)
                self.currentStack = stack
                break
        index = self.editors.index(editor)
        self.viewlist.setCurrentRow(index)
        editor.setFocus()
        fn = editor.getFileName()
        if fn:
            self.changeCaption.emit(fn)
            self.editorChanged.emit(fn)
            self.editorLineChanged.emit(fn, editor.getCursorPosition()[0] + 1)
        else:
            self.changeCaption.emit("")
        self.editorChangedEd.emit(editor)

    def __showSelectedView(self, row):
        """
        Private slot called to show a view selected in the list.

        @param row row number of the item clicked on
        @type int
        """
        if row != -1:
            self._showView(self.editors[row].getAssembly())
            self._checkActions(self.editors[row])

    def activeWindow(self):
        """
        Public method to return the active (i.e. current) window.

        @return reference to the active editor
        @rtype EditorAssembly
        """
        return self.currentStack.currentWidget()

    def showWindowMenu(self, _windowMenu):
        """
        Public method to set up the viewmanager part of the Window menu.

        @param _windowMenu reference to the window menu (unused)
        @type QMenu
        """
        pass

    def _initWindowActions(self):
        """
        Protected method to define the user interface actions for window
        handling.
        """
        pass

    def setEditorName(self, editor, newName):
        """
        Public method to change the displayed name of the editor.

        @param editor editor window to be changed
        @type Editor
        @param newName new name to be shown
        @type str
        """
        if newName and editor in self.editors:
            currentRow = self.viewlist.currentRow()
            index = self.editors.index(editor)
            txt = os.path.basename(newName)
            if editor.checkReadOnly():
                txt = self.tr("{0} (ro)").format(txt)
            itm = self.viewlist.item(index)
            if itm:
                itm.setText(txt)
                itm.setToolTip(newName)
            self.viewlist.setCurrentRow(currentRow)
            self.changeCaption.emit(newName)

    def __setIcon(self, editor, modified):
        """
        Private method to set the icon for the given editor.

        @param editor reference to the editor to set the icon for
        @type Editor
        @param modified flag indicating the modification status
        @type bool
        """
        currentRow = self.viewlist.currentRow()
        index = self.editors.index(editor)
        keys = []
        if modified:
            keys.append("fileModified")
        if editor.hasSyntaxErrors():
            keys.append("syntaxError22")
        elif editor.hasWarnings():
            keys.append("warning22")
        if not keys:
            keys.append("empty")
        item = self.viewlist.item(index)
        if item:
            item.setIcon(EricPixmapCache.getCombinedIcon(keys))
        self.viewlist.setCurrentRow(currentRow)

    def _modificationStatusChanged(self, modified, editor):
        """
        Protected slot to handle the modificationStatusChanged signal.

        @param modified flag indicating the modification status
        @type bool
        @param editor editor that sent the signal
        @type Editor
        """
        self.__setIcon(editor, modified)
        self._checkActions(editor)

    def _syntaxErrorToggled(self, editor):
        """
        Protected slot to handle the syntaxerrorToggled signal.

        @param editor editor that sent the signal
        @type Editor
        """
        self.__setIcon(editor, editor.isModified())
        ViewManager._syntaxErrorToggled(self, editor)

    def addSplit(self):
        """
        Public method used to split the current view.
        """
        stack = StackedWidget(self.stackArea)
        stack.show()
        self.stackArea.addWidget(stack)
        self.stacks.append(stack)
        self.currentStack = stack
        stack.currentChanged.connect(self.__currentChanged)
        stack.installEventFilter(self)
        size = (
            self.stackArea.width()
            if self.stackArea.orientation() == Qt.Orientation.Horizontal
            else self.stackArea.height()
        )
        self.stackArea.setSizes([int(size / len(self.stacks))] * len(self.stacks))
        self.splitRemoveAct.setEnabled(True)
        self.nextSplitAct.setEnabled(True)
        self.prevSplitAct.setEnabled(True)

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
        if len(self.stacks) > 1:
            if index == -1:
                stack = self.currentStack
            else:
                if index < len(self.stacks):
                    stack = self.stacks[index]
                else:
                    stack = self.stacks[-1]
            res = True
            savedEditors = stack.editors[:]
            for editor in savedEditors:
                res &= self.closeEditor(editor)
            if res:
                try:
                    i = self.stacks.index(stack)
                except ValueError:
                    return True
                if i == len(self.stacks) - 1:
                    i -= 1
                self.stacks.remove(stack)
                stack.close()
                self.currentStack = self.stacks[i]
                if len(self.stacks) == 1:
                    self.splitRemoveAct.setEnabled(False)
                    self.nextSplitAct.setEnabled(False)
                    self.prevSplitAct.setEnabled(False)
                return True

        return False

    def splitCount(self):
        """
        Public method to get the number of splitted views.

        @return number of splitted views
        @rtype int
        """
        return len(self.stacks)

    def setSplitCount(self, count):
        """
        Public method to set the number of split views.

        @param count number of split views
        @type int
        """
        if count > self.splitCount():
            while self.splitCount() < count:
                self.addSplit()
        elif count < self.splitCount():
            while self.splitCount() > count:
                # use an arbitrarily large index to remove the last one
                self.removeSplit(index=100)

    def getSplitOrientation(self):
        """
        Public method to get the orientation of the split view.

        @return orientation of the split
        @rtype Qt.Orientation.Horizontal or Qt.Orientation.Vertical
        """
        return self.stackArea.orientation()

    def setSplitOrientation(self, orientation):
        """
        Public method used to set the orientation of the split view.

        @param orientation orientation of the split
        @type Qt.Orientation.Horizontal or Qt.Orientation.Vertical
        """
        self.stackArea.setOrientation(orientation)

    def nextSplit(self):
        """
        Public slot used to move to the next split.
        """
        aw = self.activeWindow()
        _hasFocus = aw and aw.hasFocus()
        ind = self.stacks.index(self.currentStack) + 1
        if ind == len(self.stacks):
            ind = 0

        self.currentStack = self.stacks[ind]
        if _hasFocus:
            aw = self.activeWindow()
            if aw:
                aw.setFocus()

        cw = self.currentStack.currentWidget()
        if cw:
            index = self.editors.index(cw)
            self.viewlist.setCurrentRow(index)

    def prevSplit(self):
        """
        Public slot used to move to the previous split.
        """
        aw = self.activeWindow()
        _hasFocus = aw and aw.hasFocus()
        ind = self.stacks.index(self.currentStack) - 1
        if ind == -1:
            ind = len(self.stacks) - 1

        self.currentStack = self.stacks[ind]
        if _hasFocus:
            aw = self.activeWindow()
            if aw:
                aw.setFocus()

        cw = self.currentStack.currentWidget()
        if cw:
            index = self.editors.index(cw)
            self.viewlist.setCurrentRow(index)

    def __contextMenuClose(self):
        """
        Private method to close the selected editor.
        """
        if self.contextMenuEditor:
            self.closeEditorWindow(self.contextMenuEditor)

    def __contextMenuCloseOthers(self):
        """
        Private method to close the other editors.
        """
        index = self.contextMenuIndex
        for i in itertools.chain(
            range(self.viewlist.count() - 1, index, -1), range(index - 1, -1, -1)
        ):
            editor = self.editors[i]
            self.closeEditorWindow(editor)

    def __contextMenuCloseAbove(self):
        """
        Private method to close editors above.
        """
        index = self.contextMenuIndex
        for i in range(index - 1, -1, -1):
            editor = self.editors[i]
            self.closeEditorWindow(editor)

    def __contextMenuCloseBelow(self):
        """
        Private method to close editors below.
        """
        index = self.contextMenuIndex
        for i in range(self.viewlist.count() - 1, index, -1):
            editor = self.editors[i]
            self.closeEditorWindow(editor)

    def __contextMenuCloseAll(self):
        """
        Private method to close all editors.
        """
        savedEditors = self.editors[:]
        for editor in savedEditors:
            self.closeEditorWindow(editor)

    def __contextMenuSave(self):
        """
        Private method to save the selected editor.
        """
        if self.contextMenuEditor:
            self.saveEditorEd(self.contextMenuEditor)

    def __contextMenuSaveAs(self):
        """
        Private method to save the selected editor to a new file.
        """
        if self.contextMenuEditor:
            self.saveAsEditorEd(self.contextMenuEditor)

    def __contextMenuSaveAll(self):
        """
        Private method to save all editors.
        """
        self.saveEditorsList(self.editors)

    def __contextMenuOpenRejections(self):
        """
        Private slot to open a rejections file associated with the selected
        editor.
        """
        if self.contextMenuEditor:
            fileName = self.contextMenuEditor.getFileName()
            if fileName:
                rej = "{0}.rej".format(fileName)
                if os.path.exists(rej):
                    self.openSourceFile(rej)

    def __contextMenuPrintFile(self):
        """
        Private method to print the selected editor.
        """
        if self.contextMenuEditor:
            self.printEditor(self.contextMenuEditor)

    def __contextMenuPrintPreviewFile(self):
        """
        Private method to show a print preview of the selected editor.
        """
        if self.contextMenuEditor:
            self.printPreviewEditor(self.contextMenuEditor)

    def __contextMenuCopyPathToClipboard(self):
        """
        Private method to copy the file name of the selected editor to the
        clipboard.
        """
        if self.contextMenuEditor:
            fn = self.contextMenuEditor.getFileName()
            if fn:
                cb = QApplication.clipboard()
                cb.setText(fn)

    def __contextMenuRunScript(self):
        """
        Private method to run the editor script.
        """
        if self.contextMenuEditor:
            fn = self.contextMenuEditor.getFileName()
            if fn:
                ericApp().getObject("DebugUI").doRun(False, script=fn)

    def __contextMenuDebugScript(self):
        """
        Private method to debug the editor script.
        """
        if self.contextMenuEditor:
            fn = self.contextMenuEditor.getFileName()
            if fn:
                ericApp().getObject("DebugUI").doDebug(False, script=fn)

    def __contextMenuProfileScript(self):
        """
        Private method to profile the editor script.
        """
        if self.contextMenuEditor:
            fn = self.contextMenuEditor.getFileName()
            if fn:
                ericApp().getObject("DebugUI").doProfile(False, script=fn)

    def __contextMenuCoverageScript(self):
        """
        Private method to run a coverage test of the editor script.
        """
        if self.contextMenuEditor:
            fn = self.contextMenuEditor.getFileName()
            if fn:
                ericApp().getObject("DebugUI").doCoverage(False, script=fn)

    def __currentChanged(self, index):
        """
        Private slot to handle the currentChanged signal.

        @param index index of the current editor
        @type int
        """
        if index == -1 or not self.editors:
            return

        editor = self.activeWindow()
        if editor is None:
            return

        self._checkActions(editor)
        editor.setFocus()
        fn = editor.getFileName()
        if fn:
            self.changeCaption.emit(fn)
            if not self.__inRemoveView:
                self.editorChanged.emit(fn)
                self.editorLineChanged.emit(fn, editor.getCursorPosition()[0] + 1)
        else:
            self.changeCaption.emit("")
        self.editorChangedEd.emit(editor)

        cindex = self.editors.index(editor)
        self.viewlist.setCurrentRow(cindex)

    def eventFilter(self, watched, event):
        """
        Public method called to filter the event queue.

        @param watched the QObject being watched
        @type QObject
        @param event the event that occurred
        @type QEvent
        @return flag indicating, if we handled the event
        @rtype bool
        """
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() != Qt.MouseButton.RightButton
        ):
            switched = True
            if isinstance(watched, QStackedWidget):
                switched = watched is not self.currentStack
                self.currentStack = watched
            elif isinstance(watched, Editor):
                for stack in self.stacks:
                    if stack.hasEditor(watched):
                        switched = stack is not self.currentStack
                        self.currentStack = stack
                        break
            currentWidget = self.currentStack.currentWidget()
            if currentWidget:
                index = self.editors.index(currentWidget)
                self.viewlist.setCurrentRow(index)

            aw = self.activeWindow()
            if aw is not None:
                self._checkActions(aw)
                aw.setFocus()
                fn = aw.getFileName()
                if fn:
                    self.changeCaption.emit(fn)
                    if switched:
                        self.editorChanged.emit(fn)
                        self.editorLineChanged.emit(fn, aw.getCursorPosition()[0] + 1)
                else:
                    self.changeCaption.emit("")
                self.editorChangedEd.emit(aw)

        return False

    def getOpenEditorsForSession(self):
        """
        Public method to get a lists of all open editors.

        The returned list contains one list per split view. If the view manager
        cannot split the view, only one list of editors is returned.

        @return list of list of editor references
        @rtype list of list of Editor
        """
        editorLists = []
        for stack in self.stacks:
            editors = []
            for index in range(stack.count()):
                widget = stack.widget(index)
                if isinstance(widget, EditorAssembly):
                    editor = widget.getEditor()
                    editors.append(editor)
            editorLists.append(editors)
        return editorLists
