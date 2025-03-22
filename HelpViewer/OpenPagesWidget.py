# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget showing the list of open pages.
"""

from PyQt6.QtCore import QPoint, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QClipboard, QGuiApplication
from PyQt6.QtWidgets import QAbstractItemView, QListWidget, QMenu

from eric7.EricGui import EricPixmapCache


class OpenPagesWidget(QListWidget):
    """
    Class implementing a widget showing the list of open pages.

    @signal currentPageChanged(index) emitted to signal a change of the current
        page index
    """

    currentPageChanged = pyqtSignal(int)

    def __init__(self, stack, parent=None):
        """
        Constructor

        @param stack reference to the stack widget containing the open
            help pages
        @type QStackedWidget
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setObjectName("OpenPagesWidget")

        self.__helpViewer = parent

        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.currentRowChanged.connect(self.__currentRowChanged)
        self.customContextMenuRequested.connect(self.__showContextMenu)

        self.__stack = stack
        self.__stack.currentChanged.connect(self.__currentPageChanged)

        self.__initContextMenu()

        self.__defaultFont = self.font()
        self.__boldFont = self.font()
        self.__boldFont.setBold(True)

    def __initContextMenu(self):
        """
        Private method to initialize the context menu.
        """
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
        self.__menu.addAction(self.tr("Close All"), self.__contextMenuCloseAll)
        self.__menu.addSeparator()
        self.__copyUrlAct = self.__menu.addAction(
            self.tr("Copy URL to Clipboard"), self.__contextMenuCopyUrlToClipboard
        )

    @pyqtSlot(QPoint)
    def __showContextMenu(self, point):
        """
        Private slot to handle the customContextMenuRequested signal of
        the viewlist.

        @param point position to open the menu at
        @type QPoint
        """
        itm = self.itemAt(point)
        self.__copyUrlAct.setEnabled(bool(itm) and itm.text() != "about:blank")
        self.closeOthersMenuAct.setEnabled(self.count() > 1)
        self.__menu.popup(self.mapToGlobal(point))

    @pyqtSlot(int)
    def __currentPageChanged(self, index):
        """
        Private slot to handle a change of the shown page.

        @param index index of the current page
        @type int
        """
        for row in range(self.count()):
            itm = self.item(row)
            itm.setFont(self.__boldFont if row == index else self.__defaultFont)

    @pyqtSlot(int)
    def __currentRowChanged(self, row):
        """
        Private slot handling a change of the current row.

        @param row current row
        @type int
        """
        self.__stack.setCurrentIndex(row)
        self.currentPageChanged.emit(row)

    def addPage(self, viewer, background=False):
        """
        Public method to add a viewer page to our list.

        @param viewer reference to the viewer object
        @type HelpViewerImpl
        @param background flag indicating to not change the current page
            (defaults to False)
        @type bool (optional)
        """
        self.addItem(viewer.pageTitle())
        viewer.titleChanged.connect(lambda: self.__viewerTitleChanged(viewer))

        if not background:
            self.setCurrentRow(self.count() - 1)
        if self.count() == 1:
            self.__currentPageChanged(0)

    def insertPage(self, index, viewer, background=False):
        """
        Public method to insert a viewer page into our list.

        @param index index to insert at
        @type int
        @param viewer reference to the viewer object
        @type HelpViewerImpl
        @param background flag indicating to not change the current page
            (defaults to False)
        @type bool (optional)
        """
        currentRow = self.currentRow()
        self.insertItem(index, viewer.pageTitle())
        viewer.titleChanged.connect(lambda: self.__viewerTitleChanged(viewer))

        if not background:
            self.setCurrentRow(index)
        else:
            self.setCurrentRow(currentRow)

    def __viewerTitleChanged(self, viewer):
        """
        Private method to handle the change of a viewer title.

        @param viewer reference to the viewer that change title
        @type HelpViewerImpl
        """
        index = self.__stack.indexOf(viewer)
        itm = self.item(index)
        itm.setText(viewer.pageTitle())
        self.currentPageChanged.emit(index)

    #######################################################################
    ## Context menu action methods
    #######################################################################

    @pyqtSlot()
    def __contextMenuClose(self):
        """
        Private slot to close a page via the context menu.
        """
        self.closeCurrentPage()

    @pyqtSlot()
    def __contextMenuCloseOthers(self):
        """
        Private slot to close all other pages via the context menu.
        """
        self.closeOtherPages()

    @pyqtSlot()
    def __contextMenuCloseAll(self):
        """
        Private slot to close all pages via the context menu.
        """
        self.closeAllPages()

    @pyqtSlot()
    def __contextMenuCopyUrlToClipboard(self):
        """
        Private slot to copy the URL to the clipboard.
        """
        row = self.currentRow()
        viewer = self.__stack.widget(row)
        url = viewer.link()
        if url.isValid():
            urlStr = url.toString()

            # copy the URL to both clipboard areas
            QGuiApplication.clipboard().setText(urlStr, QClipboard.Mode.Clipboard)
            QGuiApplication.clipboard().setText(urlStr, QClipboard.Mode.Selection)

    def __removeViewer(self, row):
        """
        Private method to remove a viewer page.

        @param row row associated with the viewer
        @type int
        """
        viewer = self.__stack.widget(row)
        self.__stack.removeWidget(viewer)
        viewer.deleteLater()

        itm = self.takeItem(row)
        del itm

    #######################################################################
    ## Slots for external access below
    #######################################################################

    @pyqtSlot()
    def closeCurrentPage(self):
        """
        Public slot to close the current page.
        """
        row = self.currentRow()
        self.__removeViewer(row)

        if self.count() == 0:
            self.__helpViewer.addPage()

    @pyqtSlot()
    def closeOtherPages(self):
        """
        Public slot to close all other pages.
        """
        currentRow = self.currentRow()
        for row in range(self.count() - 1, -1, -1):
            if row != currentRow:
                self.__removeViewer(row)

    @pyqtSlot()
    def closeAllPages(self):
        """
        Public slot to close all pages.
        """
        while self.count() != 0:
            self.__removeViewer(0)
        self.__helpViewer.addPage()
