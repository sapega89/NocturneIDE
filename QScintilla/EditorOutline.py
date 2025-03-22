# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an outline widget for source code navigation of the editor.
"""

import contextlib
import functools

from PyQt6.QtCore import QCoreApplication, QModelIndex, QPoint, Qt, QTimer, pyqtSlot
from PyQt6.QtWidgets import QAbstractItemView, QApplication, QDialog, QMenu, QTreeView

from eric7 import Preferences
from eric7.UI.BrowserModel import (
    BrowserClassAttributeItem,
    BrowserGlobalsItem,
    BrowserImportItem,
    BrowserImportsItem,
)

from .EditorOutlineModel import EditorOutlineModel, EditorOutlineSortFilterProxyModel


class EditorOutlineView(QTreeView):
    """
    Class implementing an outline widget for source code navigation of the
    editor.
    """

    def __init__(self, editor, populate=True, parent=None):
        """
        Constructor

        @param editor reference to the editor widget
        @type Editor
        @param populate flag indicating to populate the outline
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__model = EditorOutlineModel(editor, populate=populate)
        self.__sortModel = EditorOutlineSortFilterProxyModel()
        self.__sortModel.setSourceModel(self.__model)
        self.setModel(self.__sortModel)

        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)

        header = self.header()
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        header.setSortIndicatorShown(True)
        header.setSectionsClickable(True)
        self.setHeaderHidden(True)

        self.setSortingEnabled(True)

        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__contextMenuRequested)
        self.__createPopupMenus()

        self.activated.connect(self.__gotoItem)
        self.expanded.connect(self.__resizeColumns)
        self.collapsed.connect(self.__resizeColumns)

        self.__expandedNames = []
        self.__currentItemName = ""
        self.__signalsConnected = False

        QTimer.singleShot(0, self.__resizeColumns)

    def setActive(self, active):
        """
        Public method to activate or deactivate the outline view.

        @param active flag indicating the requested action
        @type bool
        """
        if active and not self.__signalsConnected:
            editor = self.__model.editor()
            editor.refreshed.connect(self.repopulate)
            editor.languageChanged.connect(self.__editorLanguageChanged)
            editor.editorRenamed.connect(self.__editorRenamed)
            editor.cursorLineChanged.connect(self.__editorCursorLineChanged)

            self.__model.repopulate()
            self.__resizeColumns()

            line, _ = editor.getCursorPosition()
            self.__editorCursorLineChanged(line)

        elif not active and self.__signalsConnected:
            editor = self.__model.editor()
            editor.refreshed.disconnect(self.repopulate)
            editor.languageChanged.disconnect(self.__editorLanguageChanged)
            editor.editorRenamed.disconnect(self.__editorRenamed)
            editor.cursorLineChanged.disconnect(self.__editorCursorLineChanged)

            self.__model.clear()

    @pyqtSlot()
    def __resizeColumns(self):
        """
        Private slot to resize the view when items get expanded or collapsed.
        """
        self.resizeColumnToContents(0)

    def isPopulated(self):
        """
        Public method to check, if the model is populated.

        @return flag indicating a populated model
        @rtype bool
        """
        return self.__model.isPopulated()

    @pyqtSlot()
    def repopulate(self):
        """
        Public slot to repopulate the model.
        """
        if self.isPopulated():
            self.__prepareRepopulate()
            self.__model.repopulate()
            self.__completeRepopulate()

    @pyqtSlot()
    def __prepareRepopulate(self):
        """
        Private slot to prepare to repopulate the outline view.
        """
        itm = self.__currentItem()
        if itm is not None:
            self.__currentItemName = itm.data(0)

        self.__expandedNames = []

        childIndex = self.model().index(0, 0)
        while childIndex.isValid():
            if self.isExpanded(childIndex):
                self.__expandedNames.append(self.model().item(childIndex).data(0))
            childIndex = self.indexBelow(childIndex)

    @pyqtSlot()
    def __completeRepopulate(self):
        """
        Private slot to complete the repopulate of the outline view.
        """
        childIndex = self.model().index(0, 0)
        while childIndex.isValid():
            name = self.model().item(childIndex).data(0)
            if self.__currentItemName and self.__currentItemName == name:
                self.setCurrentIndex(childIndex)
            if name in self.__expandedNames:
                self.setExpanded(childIndex, True)
            childIndex = self.indexBelow(childIndex)
        self.__resizeColumns()

        self.__expandedNames = []
        self.__currentItemName = ""

    def isSupportedLanguage(self, language):
        """
        Public method to check, if outlining a given language is supported.

        @param language source language to be checked
        @type str
        @return flag indicating support
        @rtype bool
        """
        return language in EditorOutlineModel.getSupportedLanguages()

    @pyqtSlot(QModelIndex)
    def __gotoItem(self, index):
        """
        Private slot to set the editor cursor.

        @param index index of the item to set the cursor for
        @type QModelIndex
        """
        if index.isValid():
            itm = self.model().item(index)
            if itm:
                with contextlib.suppress(AttributeError):
                    self.__model.editor().gotoLine(itm.lineno(), itm.colOffset() + 1)
                    self.__model.editor().setFocus()

    def mouseDoubleClickEvent(self, mouseEvent):
        """
        Protected method of QAbstractItemView.

        Reimplemented to disable expanding/collapsing of items when
        double-clicking. Instead the double-clicked entry is opened.

        @param mouseEvent the mouse event
        @type QMouseEvent
        """
        index = self.indexAt(mouseEvent.position().toPoint())
        if index.isValid():
            itm = self.model().item(index)
            if isinstance(itm, (BrowserImportsItem, BrowserGlobalsItem)):
                self.setExpanded(index, not self.isExpanded(index))
            else:
                self.__gotoItem(index)

    def __currentItem(self):
        """
        Private method to get a reference to the current item.

        @return reference to the current item
        @rtype BrowserItem
        """
        itm = self.model().item(self.currentIndex())
        return itm

    #######################################################################
    ## Context menu methods below
    #######################################################################

    def __createPopupMenus(self):
        """
        Private method to generate the various popup menus.
        """
        # create the popup menu for general use
        self.__menu = QMenu(self)
        self.__menu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Goto"), self.__goto
        )
        self.__menu.addSeparator()
        self.__menu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Refresh"), self.repopulate
        )
        self.__menu.addSeparator()
        self.__menu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Copy Path to Clipboard"),
            self.__copyToClipboard,
        )
        self.__menu.addSeparator()
        self.__menu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Expand All"),
            lambda: self.expandToDepth(-1),
        )
        self.__menu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Collapse All"),
            self.collapseAll,
        )
        self.__menu.addSeparator()
        self.__menu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Set to Default Width"),
            self.__defaultWidth,
        )
        self.__menu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Change Default Width"),
            self.__changeDefaultWidth,
        )

        # create the attribute/import menu
        self.__gotoMenu = QMenu(
            QCoreApplication.translate("EditorOutlineView", "Goto"), self
        )
        self.__gotoMenu.aboutToShow.connect(self.__showGotoMenu)

        self.__attributeMenu = QMenu(self)
        self.__attributeMenu.addMenu(self.__gotoMenu)
        self.__attributeMenu.addSeparator()
        self.__attributeMenu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Refresh"), self.repopulate
        )
        self.__attributeMenu.addSeparator()
        self.__attributeMenu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Copy Path to Clipboard"),
            self.__copyToClipboard,
        )
        self.__attributeMenu.addSeparator()
        self.__attributeMenu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Expand All"),
            lambda: self.expandToDepth(-1),
        )
        self.__attributeMenu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Collapse All"),
            self.collapseAll,
        )
        self.__attributeMenu.addSeparator()
        self.__attributeMenu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Set to Default Width"),
            self.__defaultWidth,
        )
        self.__attributeMenu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Change Default Width"),
            self.__changeDefaultWidth,
        )

        # create the background menu
        self.__backMenu = QMenu(self)
        self.__backMenu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Refresh"), self.repopulate
        )
        self.__backMenu.addSeparator()
        self.__backMenu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Copy Path to Clipboard"),
            self.__copyToClipboard,
        )
        self.__backMenu.addSeparator()
        self.__backMenu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Expand All"),
            lambda: self.expandToDepth(-1),
        )
        self.__backMenu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Collapse All"),
            self.collapseAll,
        )
        self.__backMenu.addSeparator()
        self.__backMenu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Set to Default Width"),
            self.__defaultWidth,
        )
        self.__backMenu.addAction(
            QCoreApplication.translate("EditorOutlineView", "Change Default Width"),
            self.__changeDefaultWidth,
        )

    @pyqtSlot(QPoint)
    def __contextMenuRequested(self, coord):
        """
        Private slot to show the context menu.

        @param coord position of the mouse pointer
        @type QPoint
        """
        index = self.indexAt(coord)
        coord = self.mapToGlobal(coord)

        if index.isValid():
            self.setCurrentIndex(index)

            itm = self.model().item(index)
            if isinstance(itm, (BrowserClassAttributeItem, BrowserImportItem)):
                self.__attributeMenu.popup(coord)
            else:
                self.__menu.popup(coord)
        else:
            self.__backMenu.popup(coord)

    @pyqtSlot()
    def __showGotoMenu(self):
        """
        Private slot to prepare the goto submenu of the attribute menu.
        """
        self.__gotoMenu.clear()

        itm = self.model().item(self.currentIndex())
        try:
            linenos = itm.linenos()
        except AttributeError:
            try:
                linenos = [itm.lineno()]
            except AttributeError:
                return

        for lineno in sorted(linenos):
            act = self.__gotoMenu.addAction(
                QCoreApplication.translate("EditorOutlineView", "Line {0}").format(
                    lineno
                )
            )
            act.setData(lineno)
            act.triggered.connect(functools.partial(self.__gotoAttribute, act))

    #######################################################################
    ## Context menu handlers below
    #######################################################################

    @pyqtSlot()
    def __gotoAttribute(self, act):
        """
        Private slot to handle the selection of the goto menu.

        @param act reference to the action
        @type EricAction
        """
        lineno = act.data()
        self.__model.editor().gotoLine(lineno)

    @pyqtSlot()
    def __goto(self):
        """
        Private slot to move the editor cursor to the line of the context item.
        """
        self.__gotoItem(self.currentIndex())

    @pyqtSlot()
    def __copyToClipboard(self):
        """
        Private slot to copy the file name of the editor to the clipboard.
        """
        fn = self.__model.fileName()

        if fn:
            cb = QApplication.clipboard()
            cb.setText(fn)

    @pyqtSlot()
    def __defaultWidth(self):
        """
        Private slot to set the outline to the default width.
        """
        width = Preferences.getEditor("SourceOutlineWidth")
        splitterWidth = self.parent().width() - self.parent().handleWidth()
        self.parent().setSizes([splitterWidth - width, width])

    @pyqtSlot()
    def __changeDefaultWidth(self):
        """
        Private slot to open a dialog to change the default width and step
        size presetting the width with the current value.
        """
        from .EditorOutlineSizesDialog import EditorOutlineSizesDialog

        defaultWidth = Preferences.getEditor("SourceOutlineWidth")
        currentWidth = self.parent().sizes()[1]

        dlg = EditorOutlineSizesDialog(currentWidth, defaultWidth, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            newDefaultWidth = dlg.getSizes()

            Preferences.setEditor("SourceOutlineWidth", newDefaultWidth)

            if newDefaultWidth != currentWidth:
                self.__defaultWidth()

    #######################################################################
    ## Methods handling editor signals below
    #######################################################################

    @pyqtSlot()
    def __editorLanguageChanged(self):
        """
        Private slot handling a change of the associated editors source code
        language.
        """
        self.__model.repopulate()
        self.__resizeColumns()

    @pyqtSlot()
    def __editorRenamed(self):
        """
        Private slot handling a renaming of the associated editor.
        """
        self.__model.repopulate()
        self.__resizeColumns()

    @pyqtSlot(int)
    def __editorCursorLineChanged(self, lineno):
        """
        Private method to highlight a node given its line number.

        @param lineno zero based line number of the item
        @type int
        """
        sindex = self.__model.itemIndexByLine(lineno + 1)
        if sindex.isValid():
            index = self.model().mapFromSource(sindex)
            if index.isValid():
                self.setCurrentIndex(index)
                self.scrollTo(index)
        else:
            self.setCurrentIndex(QModelIndex())
