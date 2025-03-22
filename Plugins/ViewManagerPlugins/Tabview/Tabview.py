# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a tabbed viewmanager class.
"""

import itertools
import os

from PyQt6.QtCore import (
    QByteArray,
    QEvent,
    QMimeData,
    QPoint,
    QSize,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QColor, QDrag, QMouseEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSplitter,
    QTabBar,
    QToolButton,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricLed import EricLed
from eric7.EricWidgets.EricTabWidget import EricTabWidget, EricWheelTabBar
from eric7.Globals import getConfig
from eric7.QScintilla.Editor import Editor
from eric7.QScintilla.EditorAssembly import EditorAssembly
from eric7.SystemUtilities import OSUtilities
from eric7.ViewManager.ViewManager import ViewManager


class TabBar(EricWheelTabBar):
    """
    Class implementing a customized tab bar supporting drag & drop.

    @signal tabMoveRequested(int, int) emitted to signal a tab move request
        giving the old and new index position
    @signal tabRelocateRequested(str, int, int) emitted to signal a tab
        relocation request giving the string encoded id of the old tab widget,
        the index in the old tab widget and the new index position
    @signal tabCopyRequested(str, int, int) emitted to signal a clone request
        giving the string encoded id of the source tab widget, the index in the
        source tab widget and the new index position
    @signal tabCopyRequested(int, int) emitted to signal a clone request giving
        the old and new index position
    """

    tabMoveRequested = pyqtSignal(int, int)
    tabRelocateRequested = pyqtSignal(str, int, int)
    tabCopyRequested = pyqtSignal((str, int, int), (int, int))

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setAcceptDrops(True)

        self.__dragStartPos = QPoint()

    def mousePressEvent(self, event):
        """
        Protected method to handle mouse press events.

        @param event reference to the mouse press event
        @type QMouseEvent
        """
        if event.button() == Qt.MouseButton.LeftButton:
            self.__dragStartPos = QPoint(event.position().toPoint())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Protected method to handle mouse move events.

        @param event reference to the mouse move event
        @type QMouseEvent
        """
        if (
            event.buttons() == Qt.MouseButton.LeftButton
            and (event.position().toPoint() - self.__dragStartPos).manhattanLength()
            > QApplication.startDragDistance()
        ):
            drag = QDrag(self)
            mimeData = QMimeData()
            index = self.tabAt(event.position().toPoint())
            mimeData.setText(self.tabText(index))
            mimeData.setData("action", b"tab-reordering")
            mimeData.setData("tabbar-id", str(id(self)).encode("utf-8"))
            mimeData.setData(
                "source-index", QByteArray.number(self.tabAt(self.__dragStartPos))
            )
            mimeData.setData(
                "tabwidget-id", str(id(self.parentWidget())).encode("utf-8")
            )
            drag.setMimeData(mimeData)
            if event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                drag.exec(Qt.DropAction.CopyAction)
            elif event.modifiers() == Qt.KeyboardModifier.NoModifier:
                drag.exec(Qt.DropAction.MoveAction)
        super().mouseMoveEvent(event)

    def dragEnterEvent(self, event):
        """
        Protected method to handle drag enter events.

        @param event reference to the drag enter event
        @type QDragEnterEvent
        """
        mimeData = event.mimeData()
        formats = mimeData.formats()
        if (
            "action" in formats
            and mimeData.data("action") == b"tab-reordering"
            and "tabbar-id" in formats
            and "source-index" in formats
            and "tabwidget-id" in formats
        ):
            event.acceptProposedAction()
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        """
        Protected method to handle drop events.

        @param event reference to the drop event
        @type QDropEvent
        """
        mimeData = event.mimeData()
        oldID = int(mimeData.data("tabbar-id"))
        fromIndex = int(mimeData.data("source-index"))
        toIndex = self.tabAt(event.position().toPoint())
        if oldID != id(self):
            parentID = int(mimeData.data("tabwidget-id"))
            if event.proposedAction() == Qt.DropAction.MoveAction:
                self.tabRelocateRequested.emit(str(parentID), fromIndex, toIndex)
                event.acceptProposedAction()
            elif event.proposedAction() == Qt.DropAction.CopyAction:
                self.tabCopyRequested[str, int, int].emit(
                    str(parentID), fromIndex, toIndex
                )
                event.acceptProposedAction()
        else:
            if fromIndex != toIndex:
                if event.proposedAction() == Qt.DropAction.MoveAction:
                    self.tabMoveRequested.emit(fromIndex, toIndex)
                    event.acceptProposedAction()
                elif event.proposedAction() == Qt.DropAction.CopyAction:
                    self.tabCopyRequested[int, int].emit(fromIndex, toIndex)
                    event.acceptProposedAction()
        super().dropEvent(event)


class TabWidget(EricTabWidget):
    """
    Class implementing a custimized tab widget.
    """

    def __init__(self, vm):
        """
        Constructor

        @param vm view manager widget
        @type Tabview
        """
        super().__init__()

        self.__tabBar = TabBar(self)
        self.setTabBar(self.__tabBar)
        iconSize = self.__tabBar.iconSize()
        self.__tabBar.setIconSize(QSize(2 * iconSize.width(), iconSize.height()))

        self.setUsesScrollButtons(True)
        self.setElideMode(Qt.TextElideMode.ElideNone)
        if OSUtilities.isMacPlatform():
            self.setDocumentMode(True)

        self.__tabBar.tabMoveRequested.connect(self.moveTab)
        self.__tabBar.tabRelocateRequested.connect(self.__relocateTab)
        self.__tabBar.tabCopyRequested[str, int, int].connect(self.__copyTabOther)
        self.__tabBar.tabCopyRequested[int, int].connect(self.__copyTab)

        self.vm = vm
        self.editors = []

        self.indicator = EricLed(self)
        self.setCornerWidget(self.indicator, Qt.Corner.TopLeftCorner)

        self.rightCornerWidget = QWidget(self)
        self.rightCornerWidgetLayout = QHBoxLayout(self.rightCornerWidget)
        self.rightCornerWidgetLayout.setContentsMargins(0, 0, 0, 0)
        self.rightCornerWidgetLayout.setSpacing(0)

        self.__navigationMenu = QMenu(self)
        self.__navigationMenu.aboutToShow.connect(self.__showNavigationMenu)
        self.__navigationMenu.triggered.connect(self.__navigationMenuTriggered)

        self.navigationButton = QToolButton(self)
        self.navigationButton.setIcon(EricPixmapCache.getIcon("1downarrow"))
        self.navigationButton.setToolTip(self.tr("Show a navigation menu"))
        self.navigationButton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.navigationButton.setMenu(self.__navigationMenu)
        self.navigationButton.setEnabled(False)
        self.rightCornerWidgetLayout.addWidget(self.navigationButton)

        self.tabCloseRequested.connect(self.__closeRequested)

        self.setCornerWidget(self.rightCornerWidget, Qt.Corner.TopRightCorner)

        self.__initMenu()
        self.contextMenuEditor = None
        self.contextMenuIndex = -1

        self.setTabContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customTabContextMenuRequested.connect(self.__showContextMenu)

        ericPic = QPixmap(os.path.join(getConfig("ericPixDir"), "eric_small.png"))
        self.emptyLabel = QLabel()
        self.emptyLabel.setPixmap(ericPic)
        self.emptyLabel.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
        )
        super().addTab(self.emptyLabel, EricPixmapCache.getIcon("empty"), "")

    def __initMenu(self):
        """
        Private method to initialize the tab context menu.
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
        self.leftMenuAct = self.__menu.addAction(
            EricPixmapCache.getIcon("1leftarrow"),
            self.tr("Move Left"),
            self.__contextMenuMoveLeft,
        )
        self.rightMenuAct = self.__menu.addAction(
            EricPixmapCache.getIcon("1rightarrow"),
            self.tr("Move Right"),
            self.__contextMenuMoveRight,
        )
        self.firstMenuAct = self.__menu.addAction(
            EricPixmapCache.getIcon("2leftarrow"),
            self.tr("Move First"),
            self.__contextMenuMoveFirst,
        )
        self.lastMenuAct = self.__menu.addAction(
            EricPixmapCache.getIcon("2rightarrow"),
            self.tr("Move Last"),
            self.__contextMenuMoveLast,
        )
        self.__menu.addSeparator()
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
        self.closeLeftMenuAct = self.__menu.addAction(
            self.tr("Close Tabs to the Left"),
            self.__contextMenuCloseLeft,
        )
        self.closeRightMenuAct = self.__menu.addAction(
            self.tr("Close Tabs to the Right"),
            self.__contextMenuCloseRight,
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

    def __showContextMenu(self, coord, index):
        """
        Private slot to show the tab context menu.

        @param coord the position of the mouse pointer
        @type QPoint
        @param index index of the tab the menu is requested for
        @type int
        """
        if self.editors:
            widget = self.widget(index)
            if widget is not None:
                self.contextMenuEditor = widget.getEditor()
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
                            or self.contextMenuEditor.isPy3File()
                        )
                    else:
                        self.openRejectionsMenuAct.setEnabled(False)
                        self.__startAct.setEnabled(False)

                self.contextMenuIndex = index
                self.leftMenuAct.setEnabled(index > 0)
                self.rightMenuAct.setEnabled(index < self.count() - 1)
                self.firstMenuAct.setEnabled(index > 0)
                self.lastMenuAct.setEnabled(index < self.count() - 1)

                self.closeOthersMenuAct.setEnabled(self.count() > 1)
                self.closeLeftMenuAct.setEnabled(index > 0)
                self.closeRightMenuAct.setEnabled(index < self.count() - 1)

                coord = self.mapToGlobal(coord)
                self.__menu.popup(coord)

    def __showNavigationMenu(self):
        """
        Private slot to show the navigation button menu.
        """
        self.__navigationMenu.clear()
        for index in range(self.count()):
            act = self.__navigationMenu.addAction(
                self.tabIcon(index), self.tabText(index)
            )
            act.setData(index)

    def __navigationMenuTriggered(self, act):
        """
        Private slot called to handle the navigation button menu selection.

        @param act reference to the selected action
        @type QAction
        """
        index = act.data()
        if index is not None:
            self.setCurrentIndex(index)

    def showIndicator(self, on):
        """
        Public slot to set the indicator on or off.

        @param on flag indicating the state of the indicator
        @type bool
        """
        if on:
            self.indicator.setColor(QColor("green"))
        else:
            self.indicator.setColor(QColor("red"))

    def addTab(self, assembly, title):
        """
        Public method to add a new tab.

        @param assembly editor assembly object to be added
        @type QScintilla.EditorAssembly.EditorAssembly
        @param title title for the new tab
        @type str
        """
        editor = assembly.getEditor()
        super().addTab(assembly, EricPixmapCache.getIcon("empty"), title)
        self.setTabsClosable(True)
        self.navigationButton.setEnabled(True)

        if editor not in self.editors:
            self.editors.append(editor)
            editor.captionChanged.connect(self.__captionChange)
            editor.cursorLineChanged.connect(
                lambda lineno: self.__cursorLineChanged(lineno, editor)
            )

        emptyIndex = self.indexOf(self.emptyLabel)
        if emptyIndex > -1:
            self.removeTab(emptyIndex)

    def insertWidget(self, index, assembly, title):
        """
        Public method to insert a new tab.

        @param index index position for the new tab
        @type int
        @param assembly editor assembly object to be added
        @type QScintilla.EditorAssembly.EditorAssembly
        @param title title for the new tab
        @type str
        @return index of the inserted tab
        @rtype int
        """
        editor = assembly.getEditor()
        newIndex = super().insertTab(
            index, assembly, EricPixmapCache.getIcon("empty"), title
        )
        self.setTabsClosable(True)
        self.navigationButton.setEnabled(True)

        if editor not in self.editors:
            self.editors.append(editor)
            editor.captionChanged.connect(self.__captionChange)
            editor.cursorLineChanged.connect(
                lambda lineno: self.__cursorLineChanged(lineno, editor)
            )
        emptyIndex = self.indexOf(self.emptyLabel)
        if emptyIndex > -1:
            self.removeTab(emptyIndex)

        return newIndex

    def __captionChange(self, _cap, editor):
        """
        Private slot to handle Caption change signals from the editor.

        Updates the tab text and tooltip text to reflect the new caption
        information.

        @param _cap caption for the editor (unused)
        @type str
        @param editor Editor to update the caption for
        @type Editor
        """
        fn = editor.getFileName()
        if fn:
            if Preferences.getUI("TabViewManagerFilenameOnly"):
                txt = os.path.basename(fn)
            else:
                txt = ericApp().getObject("Project").getRelativePath(fn)

            maxFileNameChars = Preferences.getUI("TabViewManagerFilenameLength")
            if len(txt) > maxFileNameChars:
                txt = "...{0}".format(txt[-maxFileNameChars:])
            if editor.checkReadOnly():
                txt = self.tr("{0} (ro)").format(txt)

            assembly = editor.getAssembly()
            index = self.indexOf(assembly)
            if index > -1:
                self.setTabText(index, txt)
                self.setTabToolTip(index, fn)

    def __cursorLineChanged(self, lineno, editor):
        """
        Private slot to handle a change of the current editor's cursor line.

        @param lineno line number of the editor's cursor (zero based)
        @type int
        @param editor reference to the editor
        @type Editor
        """
        if editor and isinstance(editor, Editor):
            fn = editor.getFileName()
            if fn:
                self.vm.editorLineChanged.emit(fn, lineno + 1)
            self.vm.editorLineChangedEd.emit(editor, lineno + 1)

    def removeWidget(self, widget):
        """
        Public method to remove a widget.

        @param widget widget to be removed
        @type QWidget
        """
        if isinstance(widget, Editor):
            widget.cursorLineChanged.disconnect()
            widget.captionChanged.disconnect()
            self.editors.remove(widget)
            index = self.indexOf(widget.getAssembly())
        else:
            index = self.indexOf(widget)
        if index > -1:
            self.removeTab(index)

        if not self.editors:
            super().addTab(self.emptyLabel, EricPixmapCache.getIcon("empty"), "")
            self.emptyLabel.show()
            self.setTabsClosable(False)
            self.navigationButton.setEnabled(False)

    def __relocateTab(self, sourceId, sourceIndex, targetIndex):
        """
        Private method to relocate an editor from another TabWidget.

        @param sourceId id of the TabWidget to get the editor from
        @type str
        @param sourceIndex index of the tab in the old tab widget
        @type int
        @param targetIndex index position to place it to
        @type int
        """
        tw = self.vm.getTabWidgetById(int(sourceId))
        if tw is not None:
            # step 1: get data of the tab of the source
            toolTip = tw.tabToolTip(sourceIndex)
            text = tw.tabText(sourceIndex)
            icon = tw.tabIcon(sourceIndex)
            whatsThis = tw.tabWhatsThis(sourceIndex)
            assembly = tw.widget(sourceIndex)

            # step 2: relocate the tab
            tw.removeWidget(assembly.getEditor())
            self.insertWidget(targetIndex, assembly, text)

            # step 3: set the tab data again
            self.setTabIcon(targetIndex, icon)
            self.setTabToolTip(targetIndex, toolTip)
            self.setTabWhatsThis(targetIndex, whatsThis)

            # step 4: set current widget
            self.setCurrentIndex(targetIndex)

    def __copyTabOther(self, sourceId, sourceIndex, targetIndex):
        """
        Private method to copy an editor from another TabWidget.

        @param sourceId id of the TabWidget to get the editor from
        @type str
        @param sourceIndex index of the tab in the old tab widget
        @type int
        @param targetIndex index position to place it to
        @type int
        """
        tw = self.vm.getTabWidgetById(int(sourceId))
        if tw is not None:
            editor = tw.widget(sourceIndex).getEditor()
            newEditor, assembly = self.vm.cloneEditor(
                editor, editor.getFileType(), editor.getFileName()
            )
            self.vm.insertView(
                assembly, self, targetIndex, editor.getFileName(), editor.getNoName()
            )
            assembly.finishSetup()

    def __copyTab(self, sourceIndex, targetIndex):
        """
        Private method to copy an editor.

        @param sourceIndex index of the tab
        @type int
        @param targetIndex index position to place it to
        @type int
        """
        editor = self.widget(sourceIndex).getEditor()
        newEditor, assembly = self.vm.cloneEditor(
            editor, editor.getFileType(), editor.getFileName()
        )
        self.vm.insertView(
            assembly, self, targetIndex, editor.getFileName(), editor.getNoName()
        )
        assembly.finishSetup()

    def currentWidget(self):
        """
        Public method to return a reference to the current page.

        @return reference to the current page
        @rtype Editor
        """
        if not self.editors:
            return None
        else:
            return super().currentWidget()

    def setCurrentWidget(self, assembly):
        """
        Public method to set the current tab by the given editor assembly.

        @param assembly editor assembly to determine current tab from
        @type EditorAssembly.EditorAssembly
        """
        super().setCurrentWidget(assembly)

    def indexOf(self, widget):
        """
        Public method to get the tab index of the given editor.

        @param widget widget to get the index for
        @type QLabel or Editor
        @return tab index of the editor
        @rtype int
        """
        if isinstance(widget, Editor):
            widget = widget.getAssembly()
        return super().indexOf(widget)

    def hasEditor(self, editor):
        """
        Public method to check for an editor.

        @param editor editor object to check for
        @type Editor
        @return flag indicating, whether the editor to be checked belongs
            to the list of editors managed by this tab widget.
        @rtype bool
        """
        return editor in self.editors

    def hasEditors(self):
        """
        Public method to test, if any editor is managed.

        @return flag indicating editors are managed
        @rtype bool
        """
        return len(self.editors) > 0

    def __contextMenuClose(self):
        """
        Private method to close the selected tab.
        """
        if self.contextMenuEditor:
            self.vm.closeEditorWindow(self.contextMenuEditor)

    def __contextMenuCloseOthers(self):
        """
        Private method to close the other tabs.
        """
        index = self.contextMenuIndex
        for i in itertools.chain(
            range(self.count() - 1, index, -1), range(index - 1, -1, -1)
        ):
            editor = self.widget(i).getEditor()
            self.vm.closeEditorWindow(editor)

    def __contextMenuCloseLeft(self):
        """
        Private method to close tabs to the left.
        """
        index = self.contextMenuIndex
        for i in range(index - 1, -1, -1):
            editor = self.widget(i).getEditor()
            self.vm.closeEditorWindow(editor)

    def __contextMenuCloseRight(self):
        """
        Private method to close tabs to the right.
        """
        index = self.contextMenuIndex
        for i in range(self.count() - 1, index, -1):
            editor = self.widget(i).getEditor()
            self.vm.closeEditorWindow(editor)

    def __contextMenuCloseAll(self):
        """
        Private method to close all tabs.
        """
        savedEditors = self.editors[:]
        for editor in savedEditors:
            self.vm.closeEditorWindow(editor)

    def __contextMenuSave(self):
        """
        Private method to save the selected tab.
        """
        if self.contextMenuEditor:
            self.vm.saveEditorEd(self.contextMenuEditor)

    def __contextMenuSaveAs(self):
        """
        Private method to save the selected tab to a new file.
        """
        if self.contextMenuEditor:
            self.vm.saveAsEditorEd(self.contextMenuEditor)

    def __contextMenuSaveAll(self):
        """
        Private method to save all tabs.
        """
        self.vm.saveEditorsList(self.editors)

    def __contextMenuOpenRejections(self):
        """
        Private slot to open a rejections file associated with the selected
        tab.
        """
        if self.contextMenuEditor:
            fileName = self.contextMenuEditor.getFileName()
            if fileName:
                rej = "{0}.rej".format(fileName)
                if os.path.exists(rej):
                    self.vm.openSourceFile(rej)

    def __contextMenuPrintFile(self):
        """
        Private method to print the selected tab.
        """
        if self.contextMenuEditor:
            self.vm.printEditor(self.contextMenuEditor)

    def __contextMenuPrintPreviewFile(self):
        """
        Private method to show a print preview of the selected tab.
        """
        if self.contextMenuEditor:
            self.vm.printPreviewEditor(self.contextMenuEditor)

    def __contextMenuCopyPathToClipboard(self):
        """
        Private method to copy the file name of the selected tab to the
        clipboard.
        """
        if self.contextMenuEditor:
            fn = self.contextMenuEditor.getFileName()
            if fn:
                cb = QApplication.clipboard()
                cb.setText(fn)

    def __contextMenuMoveLeft(self):
        """
        Private method to move a tab one position to the left.
        """
        self.moveTab(self.contextMenuIndex, self.contextMenuIndex - 1)

    def __contextMenuMoveRight(self):
        """
        Private method to move a tab one position to the right.
        """
        self.moveTab(self.contextMenuIndex, self.contextMenuIndex + 1)

    def __contextMenuMoveFirst(self):
        """
        Private method to move a tab to the first position.
        """
        self.moveTab(self.contextMenuIndex, 0)

    def __contextMenuMoveLast(self):
        """
        Private method to move a tab to the last position.
        """
        self.moveTab(self.contextMenuIndex, self.count() - 1)

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

    def __closeButtonClicked(self):
        """
        Private method to handle the press of the close button.
        """
        self.vm.closeEditorWindow(self.currentWidget().getEditor())

    def __closeRequested(self, index):
        """
        Private method to handle the press of the individual tab close button.

        @param index index of the tab
        @type int
        """
        if index >= 0:
            self.vm.closeEditorWindow(self.widget(index).getEditor())

    def mouseDoubleClickEvent(self, event):
        """
        Protected method handling double click events.

        @param event reference to the event object
        @type QMouseEvent
        """
        self.vm.newEditor()


class Tabview(ViewManager):
    """
    Class implementing a tabbed viewmanager class embedded in a splitter.

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
        self.tabWidgets = []

        self.__splitter = QSplitter(parent)
        ViewManager.__init__(self)
        self.__splitter.setChildrenCollapsible(False)

        tw = TabWidget(self)
        self.__splitter.addWidget(tw)
        self.tabWidgets.append(tw)
        self.currentTabWidget = tw
        self.currentTabWidget.showIndicator(True)
        tw.currentChanged.connect(self.__currentChanged)
        tw.installEventFilter(self)
        tw.tabBar().installEventFilter(self)
        self.__splitter.setOrientation(Qt.Orientation.Vertical)
        self.__inRemoveView = False

        self.maxFileNameChars = Preferences.getUI("TabViewManagerFilenameLength")
        self.filenameOnly = Preferences.getUI("TabViewManagerFilenameOnly")

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

        @return flag indicating splitting of the view is available.
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
        for win in self.editors:
            self._removeView(win)

    def _removeView(self, win):
        """
        Protected method to remove a view (i.e. window).

        @param win editor window to be removed
        @type Editor
        """
        self.__inRemoveView = True
        for tw in self.tabWidgets:
            if tw.hasEditor(win):
                tw.removeWidget(win)
                break
        win.closeIt()
        self.__inRemoveView = False

        # if this was the last editor in this view, switch to the next, that
        # still has open editors
        for i in itertools.chain(
            range(self.tabWidgets.index(tw), -1, -1),
            range(self.tabWidgets.index(tw) + 1, len(self.tabWidgets)),
        ):
            if self.tabWidgets[i].hasEditors():
                self.currentTabWidget.showIndicator(False)
                self.currentTabWidget = self.tabWidgets[i]
                self.currentTabWidget.showIndicator(True)
                self.activeWindow().setFocus()
                break

        aw = self.activeWindow()
        fn = aw and aw.getFileName() or None
        if fn:
            self.changeCaption.emit(fn)
            self.editorChanged.emit(fn)
            self.editorLineChanged.emit(fn, aw.getCursorPosition()[0] + 1)
        else:
            self.changeCaption.emit("")
        self.editorChangedEd.emit(aw)

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
        """
        editor = win.getEditor()
        if not fn:
            if not noName:
                self.untitledCount += 1
                noName = self.tr("Untitled {0}").format(self.untitledCount)
            if addNext:
                index = self.currentTabWidget.currentIndex() + 1
                self.currentTabWidget.insertWidget(index, win, noName)
            elif indexes:
                if indexes[0] < len(self.tabWidgets):
                    tw = self.tabWidgets[indexes[0]]
                else:
                    tw = self.tabWidgets[-1]
                tw.insertWidget(indexes[1], win, noName)
            else:
                self.currentTabWidget.addTab(win, noName)
            editor.setNoName(noName)
        else:
            if self.filenameOnly:
                txt = os.path.basename(fn)
            else:
                txt = ericApp().getObject("Project").getRelativePath(fn)
            if len(txt) > self.maxFileNameChars:
                txt = "...{0}".format(txt[-self.maxFileNameChars :])
            if editor.checkReadOnly():
                txt = self.tr("{0} (ro)").format(txt)
            if addNext:
                index = self.currentTabWidget.currentIndex() + 1
                self.currentTabWidget.insertWidget(index, win, txt)
            elif indexes:
                if indexes[0] < len(self.tabWidgets):
                    tw = self.tabWidgets[indexes[0]]
                else:
                    tw = self.tabWidgets[-1]
                tw.insertWidget(indexes[1], win, txt)
            else:
                self.currentTabWidget.addTab(win, txt)
            index = self.currentTabWidget.indexOf(win)
            self.currentTabWidget.setTabToolTip(index, fn)
        self.currentTabWidget.setCurrentWidget(win)
        win.show()
        editor.setFocus()
        if fn:
            self.changeCaption.emit(fn)
            self.editorChanged.emit(fn)
            self.editorLineChanged.emit(fn, editor.getCursorPosition()[0] + 1)
        else:
            self.changeCaption.emit("")
        self.editorChangedEd.emit(editor)

    def insertView(self, win, tabWidget, index, fn=None, noName=""):
        """
        Public method to add a view (i.e. window).

        @param win editor assembly to be inserted
        @type EditorAssembly
        @param tabWidget reference to the tab widget to insert the editor into
        @type TabWidget
        @param index index position to insert at
        @type int
        @param fn filename of this editor
        @type str
        @param noName name to be used for an unnamed editor
        @type str
        """
        editor = win.getEditor()
        if fn is None:
            if not noName:
                self.untitledCount += 1
                noName = self.tr("Untitled {0}").format(self.untitledCount)
            tabWidget.insertWidget(index, win, noName)
            editor.setNoName(noName)
        else:
            if self.filenameOnly:
                txt = os.path.basename(fn)
            else:
                txt = ericApp().getObject("Project").getRelativePath(fn)
            if len(txt) > self.maxFileNameChars:
                txt = "...{0}".format(txt[-self.maxFileNameChars :])
            if editor.checkReadOnly():
                txt = self.tr("{0} (ro)").format(txt)
            nindex = tabWidget.insertWidget(index, win, txt)
            tabWidget.setTabToolTip(nindex, fn)
        tabWidget.setCurrentWidget(win)
        win.show()
        editor.setFocus()
        if fn:
            self.changeCaption.emit(fn)
            self.editorChanged.emit(fn)
            self.editorLineChanged.emit(fn, editor.getCursorPosition()[0] + 1)
        else:
            self.changeCaption.emit("")
        self.editorChangedEd.emit(editor)

        self._modificationStatusChanged(editor.isModified(), editor)
        self._checkActions(editor)

    def _showView(self, win, fn=None):  # noqa: U100
        """
        Protected method to show a view (i.e. window).

        @param win editor assembly to be shown
        @type EditorAssembly
        @param fn filename of this editor (unused)
        @type str
        """
        win.show()
        editor = win.getEditor()
        for tw in self.tabWidgets:
            if tw.hasEditor(editor):
                tw.setCurrentWidget(win)
                self.currentTabWidget.showIndicator(False)
                self.currentTabWidget = tw
                self.currentTabWidget.showIndicator(True)
                break
        editor.setFocus()

    def activeWindow(self):
        """
        Public method to return the active (i.e. current) window.

        @return reference to the active editor
        @rtype Editor
        """
        cw = self.currentTabWidget.currentWidget()
        if cw:
            return cw.getEditor()
        else:
            return None

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
        if newName:
            if self.filenameOnly:
                tabName = os.path.basename(newName)
            else:
                tabName = ericApp().getObject("Project").getRelativePath(newName)
            if len(tabName) > self.maxFileNameChars:
                tabName = "...{0}".format(tabName[-self.maxFileNameChars :])
            index = self.currentTabWidget.indexOf(editor)
            self.currentTabWidget.setTabText(index, tabName)
            self.currentTabWidget.setTabToolTip(index, newName)
            self.changeCaption.emit(newName)

    def __setIcon(self, editor, modified):
        """
        Private method to set the icon for the given editor.

        @param editor reference to the editor to set the icon for
        @type Editor
        @param modified flag indicating the modification status
        @type bool
        """
        for tw in self.tabWidgets:
            if tw.hasEditor(editor):
                break
        index = tw.indexOf(editor)
        keys = []
        if modified:
            keys.append("fileModified")
        if editor.hasSyntaxErrors():
            keys.append("syntaxError22")
        elif editor.hasWarnings():
            keys.append("warning22")
        if not keys:
            keys.append("empty")
        tw.setTabIcon(index, EricPixmapCache.getCombinedIcon(keys))

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
        tw = TabWidget(self)
        tw.show()
        self.__splitter.addWidget(tw)
        self.tabWidgets.append(tw)
        self.currentTabWidget.showIndicator(False)
        self.currentTabWidget = self.tabWidgets[-1]
        self.currentTabWidget.showIndicator(True)
        tw.currentChanged.connect(self.__currentChanged)
        tw.installEventFilter(self)
        tw.tabBar().installEventFilter(self)
        size = (
            self.width()
            if self.__splitter.orientation() == Qt.Orientation.Horizontal
            else self.height()
        )
        self.__splitter.setSizes(
            [int(size / len(self.tabWidgets))] * len(self.tabWidgets)
        )
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
        if len(self.tabWidgets) > 1:
            if index == -1:
                tw = self.currentTabWidget
            else:
                if index < len(self.tabWidgets):
                    tw = self.tabWidgets[index]
                else:
                    tw = self.tabWidgets[-1]
            res = True
            savedEditors = tw.editors[:]
            for editor in savedEditors:
                res &= self.closeEditor(editor)
            if res:
                try:
                    i = self.tabWidgets.index(tw)
                except ValueError:
                    return True
                if i == len(self.tabWidgets) - 1:
                    i -= 1
                self.tabWidgets.remove(tw)
                tw.close()
                self.currentTabWidget = self.tabWidgets[i]
                for tw in self.tabWidgets:
                    tw.showIndicator(tw == self.currentTabWidget)
                if self.currentTabWidget is not None:
                    assembly = self.currentTabWidget.currentWidget()
                    if assembly is not None:
                        editor = assembly.getEditor()
                        if editor is not None:
                            editor.setFocus(Qt.FocusReason.OtherFocusReason)
                if len(self.tabWidgets) == 1:
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
        return len(self.tabWidgets)

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
        return self.__splitter.orientation()

    def setSplitOrientation(self, orientation):
        """
        Public method used to set the orientation of the split view.

        @param orientation orientation of the split
        @type Qt.Orientation.Horizontal or Qt.Orientation.Vertical
        """
        self.__splitter.setOrientation(orientation)

    def nextSplit(self):
        """
        Public slot used to move to the next split.
        """
        aw = self.activeWindow()
        _hasFocus = aw and aw.hasFocus()
        ind = self.tabWidgets.index(self.currentTabWidget) + 1
        if ind == len(self.tabWidgets):
            ind = 0

        self.currentTabWidget.showIndicator(False)
        self.currentTabWidget = self.tabWidgets[ind]
        self.currentTabWidget.showIndicator(True)
        if _hasFocus:
            aw = self.activeWindow()
            if aw:
                aw.setFocus()

    def prevSplit(self):
        """
        Public slot used to move to the previous split.
        """
        aw = self.activeWindow()
        _hasFocus = aw and aw.hasFocus()
        ind = self.tabWidgets.index(self.currentTabWidget) - 1
        if ind == -1:
            ind = len(self.tabWidgets) - 1

        self.currentTabWidget.showIndicator(False)
        self.currentTabWidget = self.tabWidgets[ind]
        self.currentTabWidget.showIndicator(True)
        if _hasFocus:
            aw = self.activeWindow()
            if aw:
                aw.setFocus()

    def __currentChanged(self, index):
        """
        Private slot to handle the currentChanged signal.

        @param index index of the current tab
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

    def eventFilter(self, watched, event):
        """
        Public method called to filter the event queue.

        @param watched the QObject being watched
        @type QObject
        @param event the event that occurred
        @type QEvent
        @return always False
        @rtype bool
        """
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and isinstance(event, QMouseEvent)
            and event.button() != Qt.MouseButton.RightButton
        ):
            switched = True
            self.currentTabWidget.showIndicator(False)
            if isinstance(watched, EricTabWidget):
                switched = watched is not self.currentTabWidget
                self.currentTabWidget = watched
            elif isinstance(watched, QTabBar):
                switched = watched.parent() is not self.currentTabWidget
                self.currentTabWidget = watched.parent()
                if switched:
                    index = self.currentTabWidget.selectTab(event.position().toPoint())
                    switched = (
                        self.currentTabWidget.widget(index) is self.activeWindow()
                    )
            elif isinstance(watched, Editor):
                for tw in self.tabWidgets:
                    if tw.hasEditor(watched):
                        switched = tw is not self.currentTabWidget
                        self.currentTabWidget = tw
                        break
            self.currentTabWidget.showIndicator(True)

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

    def preferencesChanged(self):
        """
        Public slot to handle the preferencesChanged signal.
        """
        ViewManager.preferencesChanged(self)

        self.maxFileNameChars = Preferences.getUI("TabViewManagerFilenameLength")
        self.filenameOnly = Preferences.getUI("TabViewManagerFilenameOnly")

        for tabWidget in self.tabWidgets:
            for index in range(tabWidget.count()):
                editor = tabWidget.widget(index)
                if isinstance(editor, Editor):
                    fn = editor.getFileName()
                    if fn:
                        if self.filenameOnly:
                            txt = os.path.basename(fn)
                        else:
                            txt = ericApp().getObject("Project").getRelativePath(fn)
                        if len(txt) > self.maxFileNameChars:
                            txt = "...{0}".format(txt[-self.maxFileNameChars :])
                        if editor.checkReadOnly():
                            txt = self.tr("{0} (ro)").format(txt)
                        tabWidget.setTabText(index, txt)

    def getTabWidgetById(self, id_):
        """
        Public method to get a reference to a tab widget knowing its ID.

        @param id_ id of the tab widget
        @type int
        @return reference to the tab widget
        @rtype TabWidget
        """
        for tw in self.tabWidgets:
            if id(tw) == id_:
                return tw
        return None

    def getOpenEditorsForSession(self):
        """
        Public method to get a lists of all open editors.

        The returned list contains one list per split view. If the view manager
        cannot split the view, only one list of editors is returned.

        @return list of list of editor references
        @rtype list of list of Editor
        """
        editorLists = []
        for tabWidget in self.tabWidgets:
            editors = []
            for index in range(tabWidget.count()):
                widget = tabWidget.widget(index)
                if isinstance(widget, EditorAssembly):
                    editor = widget.getEditor()
                    editors.append(editor)
            editorLists.append(editors)
        return editorLists
