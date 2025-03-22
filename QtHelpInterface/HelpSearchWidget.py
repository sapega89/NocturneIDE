# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a window for showing the QtHelp index.
"""

from PyQt6.QtCore import QPoint, Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QClipboard, QGuiApplication
from PyQt6.QtWidgets import QApplication, QMenu, QTextBrowser, QVBoxLayout, QWidget


class HelpSearchWidget(QWidget):
    """
    Class implementing a window for showing the QtHelp index.

    @signal escapePressed() emitted when the ESC key was pressed
    @signal openUrl(QUrl, str) emitted to open a search result entry in the
        current tab
    @signal newTab(QUrl, str) emitted to open a search result entry in a
        new tab
    @signal newBackgroundTab(QUrl, str) emitted to open a search result entry
        in a new background tab
    @signal newWindow(QUrl, str) emitted to open a search result entry in a
        new window
    """

    escapePressed = pyqtSignal()
    openUrl = pyqtSignal(QUrl)
    newTab = pyqtSignal(QUrl)
    newBackgroundTab = pyqtSignal(QUrl)
    newWindow = pyqtSignal(QUrl)

    def __init__(self, engine, internal=False, parent=None):
        """
        Constructor

        @param engine reference to the help search engine
        @type QHelpSearchEngine
        @param internal flag indicating the internal help viewer
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__engine = engine
        self.__internal = internal

        self.__layout = QVBoxLayout(self)
        if internal:
            # no margins for the internal variant
            self.__layout.setContentsMargins(0, 0, 0, 0)

        self.__result = self.__engine.resultWidget()
        self.__query = self.__engine.queryWidget()

        self.__layout.addWidget(self.__query)
        self.__layout.addWidget(self.__result)

        self.setFocusProxy(self.__query)

        self.__query.search.connect(self.__search)
        self.__result.requestShowLink.connect(self.__linkActivated)

        self.__engine.searchingStarted.connect(self.__searchingStarted)
        self.__engine.searchingFinished.connect(self.__searchingFinished)

        self.__browser = self.__result.findChildren(QTextBrowser)[0]

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__showContextMenu)

    @pyqtSlot()
    def __search(self):
        """
        Private slot to perform a search of the database.
        """
        query = self.__query.searchInput()
        self.__engine.search(query)

    @pyqtSlot()
    def __searchingStarted(self):
        """
        Private slot to handle the start of a search.
        """
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

    @pyqtSlot(int)
    def __searchingFinished(self, _hits):
        """
        Private slot to handle the end of the search.

        @param _hits number of hits (unused)
        @type int
        """
        QApplication.restoreOverrideCursor()

    @pyqtSlot(QUrl)
    def __linkActivated(self, url):
        """
        Private slot handling the activation of an entry.

        @param url URL of the activated entry
        @type QUrl
        """
        if not url.isEmpty() and url.isValid():
            buttons = QApplication.mouseButtons()
            modifiers = QApplication.keyboardModifiers()

            if buttons & Qt.MouseButton.MiddleButton:
                self.newTab.emit(url)
            else:
                if modifiers & (
                    Qt.KeyboardModifier.ControlModifier
                    | Qt.KeyboardModifier.ShiftModifier
                ) == (
                    Qt.KeyboardModifier.ControlModifier
                    | Qt.KeyboardModifier.ShiftModifier
                ):
                    self.newBackgroundTab.emit(url)
                elif modifiers & Qt.KeyboardModifier.ControlModifier:
                    self.newTab.emit(url)
                elif (
                    modifiers & Qt.KeyboardModifier.ShiftModifier
                    and not self.__internal
                ):
                    self.newWindow.emit(url)
                else:
                    self.openUrl.emit(url)

    def keyPressEvent(self, evt):
        """
        Protected method handling key press events.

        @param evt reference to the key press event
        @type QKeyEvent
        """
        if evt.key() == Qt.Key.Key_Escape:
            self.escapePressed.emit()
        else:
            evt.ignore()

    @pyqtSlot(QPoint)
    def __showContextMenu(self, pos):
        """
        Private slot to show a context menu.

        @param pos position for the context menu
        @type QPoint
        """
        point = self.mapToGlobal(pos)

        if self.__browser:
            point = self.__browser.mapFromGlobal(point)
            if not self.__browser.rect().contains(point, True):
                return
            link = QUrl(self.__browser.anchorAt(point))
        else:
            point = self.__result.mapFromGlobal(point)
            link = self.__result.linkAt(point)

        if link.isEmpty() or not link.isValid():
            return

        menu = QMenu()
        curTab = menu.addAction(self.tr("Open Link"))
        if self.__internal:
            newTab = menu.addAction(self.tr("Open Link in New Page"))
            newBackgroundTab = menu.addAction(self.tr("Open Link in Background Page"))
        else:
            newTab = menu.addAction(self.tr("Open Link in New Tab"))
            newBackgroundTab = menu.addAction(self.tr("Open Link in Background Tab"))
            newWindow = menu.addAction(self.tr("Open Link in New Window"))
        menu.addSeparator()
        copyLink = menu.addAction(self.tr("Copy URL to Clipboard"))

        act = menu.exec(self.mapToGlobal(pos))
        if act == curTab:
            self.openUrl.emit(link)
        elif act == newTab:
            self.newTab.emit(link)
        elif act == newBackgroundTab:
            self.newBackgroundTab.emit(link)
        elif not self.__internal and act == newWindow:
            self.newWindow.emit(link)
        elif act == copyLink:
            # copy the URL to both clipboard areas
            QGuiApplication.clipboard().setText(
                link.toString(), QClipboard.Mode.Clipboard
            )
            QGuiApplication.clipboard().setText(
                link.toString(), QClipboard.Mode.Selection
            )
