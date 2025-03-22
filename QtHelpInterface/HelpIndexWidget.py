# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a window for showing the QtHelp index.
"""

from PyQt6.QtCore import QEvent, Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QClipboard, QGuiApplication
from PyQt6.QtHelp import QHelpLink
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QVBoxLayout,
    QWidget,
)


class HelpIndexWidget(QWidget):
    """
    Class implementing a window for showing the QtHelp index.

    @signal escapePressed() emitted when the ESC key was pressed
    @signal openUrl(QUrl, str) emitted to open an entry in the current tab
    @signal newTab(QUrl, str) emitted to open an entry in a new tab
    @signal newBackgroundTab(QUrl, str) emitted to open an entry in a
        new background tab
    @signal newWindow(QUrl, str) emitted to open an entry in a new window
    """

    escapePressed = pyqtSignal()
    openUrl = pyqtSignal(QUrl)
    newTab = pyqtSignal(QUrl)
    newBackgroundTab = pyqtSignal(QUrl)
    newWindow = pyqtSignal(QUrl)

    def __init__(self, engine, internal=False, parent=None):
        """
        Constructor

        @param engine reference to the help engine
        @type QHelpEngine
        @param internal flag indicating the internal help viewer
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__engine = engine
        self.__internal = internal

        self.__searchEdit = None
        self.__index = None

        self.__layout = QVBoxLayout(self)
        if internal:
            # no margins for the internal variant
            self.__layout.setContentsMargins(0, 0, 0, 0)

        self.__searchEditLayout = QHBoxLayout()
        label = QLabel(self.tr("&Look for:"))
        self.__searchEditLayout.addWidget(label)

        self.__searchEdit = QLineEdit()
        self.__searchEdit.setClearButtonEnabled(True)
        label.setBuddy(self.__searchEdit)
        self.__searchEdit.textChanged.connect(self.__filterIndices)
        self.__searchEdit.installEventFilter(self)
        self.__searchEditLayout.addWidget(self.__searchEdit)
        self.__layout.addLayout(self.__searchEditLayout)

        self.__index = self.__engine.indexWidget()
        self.__index.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.__engine.indexModel().indexCreationStarted.connect(
            self.__disableSearchEdit
        )
        self.__engine.indexModel().indexCreated.connect(self.__enableSearchEdit)
        self.__index.documentActivated.connect(self.__documentActivated)
        self.__index.documentsActivated.connect(self.__documentsActivated)
        self.__index.customContextMenuRequested.connect(self.__showContextMenu)
        self.__searchEdit.returnPressed.connect(self.__index.activateCurrentItem)
        self.__layout.addWidget(self.__index)

    @pyqtSlot(QHelpLink, str)
    def __documentActivated(self, document, _keyword, modifiers=None):
        """
        Private slot to handle the activation of a keyword entry.

        @param document reference to a data structure containing the
            document info
        @type QHelpLink
        @param _keyword keyword for the URL (unused)
        @type str
        @param modifiers keyboard modifiers
        @type Qt.KeyboardModifiers or None
        """
        if modifiers is None:
            modifiers = QApplication.keyboardModifiers()
        if not document.url.isEmpty() and document.url.isValid():
            if modifiers & (
                Qt.KeyboardModifier.ControlModifier
                | Qt.KeyboardModifier.ControlModifier
            ):
                self.newBackgroundTab.emit(document.url)
            elif modifiers & Qt.KeyboardModifier.ControlModifier:
                self.newTab.emit(document.url)
            elif modifiers & Qt.KeyboardModifier.ShiftModifier and not self.__internal:
                self.newWindow.emit(document.url)
            else:
                self.openUrl.emit(document.url)

    def __documentsActivated(self, documents, helpKeyword):
        """
        Private slot to handle the activation of an entry with multiple help
        documents.

        @param documents list of help document link data structures
        @type list of QHelpLink
        @param helpKeyword keyword for the entry
        @type str
        """
        modifiers = QApplication.keyboardModifiers()
        document = (
            documents[0]
            if len(documents) == 1
            else self.__selectDocument(documents, helpKeyword)
        )
        self.__documentActivated(document, helpKeyword, modifiers)

    def __selectDocument(self, documents, helpKeyword):
        """
        Private method to give the user a chance to select among the
        given documents.

        @param documents list of help document link data structures
        @type list of QHelpLink
        @param helpKeyword keyword for the documents
        @type str
        @return selected document
        @rtype QHelpLink
        """
        from .HelpTopicDialog import HelpTopicDialog

        document = QHelpLink()

        dlg = HelpTopicDialog(self, helpKeyword, documents)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            document = dlg.document()

        return document

    def __filterIndices(self, indexFilter):
        """
        Private slot to filter the indexes according to the given filter.

        @param indexFilter filter to be used
        @type str
        """
        if "*" in indexFilter:
            self.__index.filterIndices(indexFilter, indexFilter)
        else:
            self.__index.filterIndices(indexFilter)

    def __enableSearchEdit(self):
        """
        Private slot to enable the search edit.
        """
        self.__searchEdit.setEnabled(True)
        self.__filterIndices(self.__searchEdit.text())

    def __disableSearchEdit(self):
        """
        Private slot to enable the search edit.
        """
        self.__searchEdit.setEnabled(False)

    def focusInEvent(self, evt):
        """
        Protected method handling focus in events.

        @param evt reference to the focus event object
        @type QFocusEvent
        """
        if evt.reason() != Qt.FocusReason.MouseFocusReason:
            self.__searchEdit.selectAll()
            self.__searchEdit.setFocus()

    def eventFilter(self, watched, event):
        """
        Public method called to filter the event queue.

        @param watched the QObject being watched
        @type QObject
        @param event the event that occurred
        @type QEvent
        @return flag indicating whether the event was handled
        @rtype bool
        """
        if (
            self.__searchEdit
            and watched == self.__searchEdit
            and event.type() == QEvent.Type.KeyPress
        ):
            idx = self.__index.currentIndex()
            if event.key() == Qt.Key.Key_Up:
                idx = self.__index.model().index(
                    idx.row() - 1, idx.column(), idx.parent()
                )
                if idx.isValid():
                    self.__index.setCurrentIndex(idx)
            elif event.key() == Qt.Key.Key_Down:
                idx = self.__index.model().index(
                    idx.row() + 1, idx.column(), idx.parent()
                )
                if idx.isValid():
                    self.__index.setCurrentIndex(idx)
            elif event.key() == Qt.Key.Key_Escape:
                self.escapePressed.emit()

        return QWidget.eventFilter(self, watched, event)

    def __showContextMenu(self, pos):
        """
        Private slot showing the context menu.

        @param pos position to show the menu at
        @type QPoint
        """
        idx = self.__index.indexAt(pos)
        if idx.isValid():
            menu = QMenu()
            curTab = menu.addAction(self.tr("Open Link"))
            if self.__internal:
                newTab = menu.addAction(self.tr("Open Link in New Page"))
                newBackgroundTab = menu.addAction(
                    self.tr("Open Link in Background Page")
                )
            else:
                newTab = menu.addAction(self.tr("Open Link in New Tab"))
                newBackgroundTab = menu.addAction(
                    self.tr("Open Link in Background Tab")
                )
                newWindow = menu.addAction(self.tr("Open Link in New Window"))
            menu.addSeparator()
            copyLink = menu.addAction(self.tr("Copy URL to Clipboard"))
            menu.move(self.__index.mapToGlobal(pos))

            act = menu.exec()
            model = self.__index.model()
            if model is not None:
                helpKeyword = model.data(idx, Qt.ItemDataRole.DisplayRole)
                helpLinks = self.__engine.documentsForKeyword(helpKeyword, "")
                if len(helpLinks) == 1:
                    link = helpLinks[0].url
                else:
                    link = self.__selectDocument(helpLinks, helpKeyword).url

                if not link.isEmpty() and link.isValid():
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
