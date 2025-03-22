# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget showing the list of bookmarks.
"""

import contextlib
import datetime
import json
import os

from PyQt6.QtCore import QPoint, Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QClipboard, QGuiApplication
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QMenu,
)

from eric7 import Preferences
from eric7.EricWidgets import EricFileDialog, EricMessageBox

from .HelpBookmarkPropertiesDialog import HelpBookmarkPropertiesDialog


class HelpBookmarksWidget(QListWidget):
    """
    Class implementing a widget showing the list of bookmarks.

    @signal escapePressed() emitted when the ESC key was pressed
    @signal openUrl(QUrl, str) emitted to open an entry in the current tab
    @signal newTab(QUrl, str) emitted to open an entry in a new tab
    @signal newBackgroundTab(QUrl, str) emitted to open an entry in a
        new background tab
    """

    escapePressed = pyqtSignal()
    openUrl = pyqtSignal(QUrl)
    newTab = pyqtSignal(QUrl)
    newBackgroundTab = pyqtSignal(QUrl)

    UrlRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setObjectName("HelpBookmarksWidget")

        self.__helpViewer = parent

        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setSortingEnabled(True)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__showContextMenu)

        self.__bookmarks = []
        self.__loadBookmarks()

        self.itemDoubleClicked.connect(self.__bookmarkActivated)

    @pyqtSlot(QPoint)
    def __showContextMenu(self, point):
        """
        Private slot to handle the customContextMenuRequested signal of
        the viewlist.

        @param point position to open the menu at
        @type QPoint
        """
        selectedItemsCount = len(self.selectedItems())
        if selectedItemsCount == 0:
            # background menu
            self.__showBackgroundMenu(point)
        elif selectedItemsCount == 1:
            # single bookmark menu
            self.__showBookmarkContextMenu(point)
        else:
            # multiple selected bookmarks
            self.__showBookmarksContextMenu(point)

    @pyqtSlot(QPoint)
    def __showBackgroundMenu(self, point):
        """
        Private slot to show the background menu (i.e. no selection).

        @param point position to open the menu at
        @type QPoint
        """
        menu = QMenu()
        openBookmarks = menu.addAction(self.tr("Open All Bookmarks"))
        menu.addSeparator()
        newBookmark = menu.addAction(self.tr("New Bookmark"))
        addBookmark = menu.addAction(self.tr("Bookmark Page"))
        menu.addSeparator()
        deleteBookmarks = menu.addAction(self.tr("Delete All Bookmarks"))
        menu.addSeparator()
        exportBookmarks = menu.addAction(self.tr("Export All Bookmarks"))
        importBookmarks = menu.addAction(self.tr("Import Bookmarks"))

        act = menu.exec(self.mapToGlobal(point))
        if act == openBookmarks:
            self.__openBookmarks(selected=False)
        elif act == newBookmark:
            self.__newBookmark()
        elif act == addBookmark:
            self.__bookmarkCurrentPage()
        elif act == deleteBookmarks:
            self.__deleteBookmarks([self.item(row) for row in range(self.count())])
        elif act == exportBookmarks:
            self.__exportBookmarks(selected=False)
        elif act == importBookmarks:
            self.__importBookmarks()

    @pyqtSlot(QPoint)
    def __showBookmarkContextMenu(self, point):
        """
        Private slot to show the context menu for a bookmark.

        @param point position to open the menu at
        @type QPoint
        """
        itm = self.selectedItems()[0]
        url = itm.data(self.UrlRole)
        validUrl = url is not None and not url.isEmpty() and url.isValid()

        menu = QMenu()
        curPage = menu.addAction(self.tr("Open Link"))
        curPage.setEnabled(validUrl)
        newPage = menu.addAction(self.tr("Open Link in New Page"))
        newPage.setEnabled(validUrl)
        newBackgroundPage = menu.addAction(self.tr("Open Link in Background Page"))
        newBackgroundPage.setEnabled(validUrl)
        menu.addSeparator()
        copyUrl = menu.addAction(self.tr("Copy URL to Clipboard"))
        copyUrl.setEnabled(validUrl)
        menu.addSeparator()
        newBookmark = menu.addAction(self.tr("New Bookmark"))
        addBookmark = menu.addAction(self.tr("Bookmark Page"))
        menu.addSeparator()
        editBookmark = menu.addAction(self.tr("Edit Bookmark"))
        menu.addSeparator()
        deleteBookmark = menu.addAction(self.tr("Delete Bookmark"))
        menu.addSeparator()
        exportBookmarks = menu.addAction(self.tr("Export All Bookmarks"))
        importBookmarks = menu.addAction(self.tr("Import Bookmarks"))

        act = menu.exec(self.mapToGlobal(point))
        if act == curPage:
            self.openUrl.emit(url)
        elif act == newPage:
            self.newTab.emit(url)
        elif act == newBackgroundPage:
            self.newBackgroundTab.emit(url)
        elif act == copyUrl:
            # copy the URL to both clipboard areas
            QGuiApplication.clipboard().setText(
                url.toString(), QClipboard.Mode.Clipboard
            )
            QGuiApplication.clipboard().setText(
                url.toString(), QClipboard.Mode.Selection
            )
        elif act == newBookmark:
            self.__newBookmark()
        elif act == addBookmark:
            self.__bookmarkCurrentPage()
        elif act == editBookmark:
            self.__editBookmark(itm)
        elif act == deleteBookmark:
            self.__deleteBookmarks([itm])
        elif act == exportBookmarks:
            self.__exportBookmarks(selected=False)
        elif act == importBookmarks:
            self.__importBookmarks()

    @pyqtSlot(QPoint)
    def __showBookmarksContextMenu(self, point):
        """
        Private slot to show the context menu for multiple bookmark.

        @param point position to open the menu at
        @type QPoint
        """
        menu = QMenu()
        openBookmarks = menu.addAction(self.tr("Open Selected Bookmarks"))
        menu.addSeparator()
        deleteBookmarks = menu.addAction(self.tr("Delete Selected Bookmarks"))
        menu.addSeparator()
        exportBookmarks = menu.addAction(self.tr("Export Selected Bookmarks"))
        exportAllBookmarks = menu.addAction(self.tr("Export All Bookmarks"))
        importBookmarks = menu.addAction(self.tr("Import Bookmarks"))

        act = menu.exec(self.mapToGlobal(point))
        if act == openBookmarks:
            self.__openBookmarks(selected=True)
        elif act == deleteBookmarks:
            self.__deleteBookmarks(self.selectedItems())
        elif act == exportBookmarks:
            self.__exportBookmarks(selected=True)
        elif act == exportAllBookmarks:
            self.__exportBookmarks(selected=False)
        elif act == importBookmarks:
            self.__importBookmarks()

    @pyqtSlot(str, str)
    def __addBookmark(self, title, url):
        """
        Private slot to add a bookmark entry.

        @param title title for the bookmark
        @type str
        @param url URL for the bookmark
        @type str
        """
        url = url.strip()

        itm = QListWidgetItem(title, self)
        itm.setData(self.UrlRole, QUrl(url))
        itm.setToolTip(url)

    @pyqtSlot(str, QUrl)
    def addBookmark(self, title, url):
        """
        Public slot to add a bookmark with given data.

        @param title title for the bookmark
        @type str
        @param url URL for the bookmark
        @type QUrl
        """
        dlg = HelpBookmarkPropertiesDialog(title, url.toString(), parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            title, url = dlg.getData()
            self.__addBookmark(title, url)
            self.sortItems()
            self.__saveBookmarks()

    @pyqtSlot()
    def __bookmarkCurrentPage(self):
        """
        Private slot to bookmark the current page.
        """
        currentViewer = self.__helpViewer.currentViewer()
        title = currentViewer.pageTitle()
        url = currentViewer.link()
        self.addBookmark(title, url)

    @pyqtSlot()
    def __newBookmark(self):
        """
        Private slot to create a new bookmark.
        """
        dlg = HelpBookmarkPropertiesDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            title, url = dlg.getData()
            self.__addBookmark(title, url)
            self.sortItems()
            self.__saveBookmarks()

    @pyqtSlot()
    def __editBookmark(self, itm):
        """
        Private slot to edit a bookmark.

        @param itm reference to the bookmark item to be edited
        @type QListWidgetItem
        """
        dlg = HelpBookmarkPropertiesDialog(
            itm.text(), itm.data(self.UrlRole).toString(), parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            title, url = dlg.getData()
            itm.setText(title)
            itm.setData(self.UrlRole, QUrl(url))
            itm.setToolTip(url)
            self.sortItems()
            self.__saveBookmarks()

    @pyqtSlot(QListWidgetItem)
    def __bookmarkActivated(self, itm):
        """
        Private slot handling the activation of a bookmark.

        @param itm reference to the activated item
        @type QListWidgetItem
        """
        url = itm.data(self.UrlRole)
        if url and not url.isEmpty() and url.isValid():
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

    def __openBookmarks(self, selected=False):
        """
        Private method to open all or selected bookmarks.

        @param selected flag indicating to open the selected bookmarks
            (defaults to False)
        @type bool (optional)
        """
        items = (
            self.selectedItems()
            if selected
            else [self.item(row) for row in range(self.count())]
        )

        for itm in items:
            url = itm.data(self.UrlRole)
            if url is not None and not url.isEmpty() and url.isValid():
                self.newTab.emit(url)

    def __deleteBookmarks(self, items):
        """
        Private method to delete the given bookmark items.

        @param items list of bookmarks to be deleted
        @type list of QListWidgetItem
        """
        from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog

        dlg = DeleteFilesConfirmationDialog(
            self,
            self.tr("Delete Bookmarks"),
            self.tr("Shall these bookmarks really be deleted?"),
            [itm.text() for itm in items],
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            for itm in items:
                self.takeItem(self.row(itm))
                del itm
            self.__saveBookmarks()

    def __loadBookmarks(self):
        """
        Private method to load the defined bookmarks.
        """
        bookmarksStr = Preferences.getHelp("Bookmarks")
        with contextlib.suppress(ValueError):
            bookmarks = json.loads(bookmarksStr)

        self.clear()
        for bookmark in bookmarks:
            self.__addBookmark(bookmark["title"], bookmark["url"])
        self.sortItems()

    def __saveBookmarks(self):
        """
        Private method to save the defined bookmarks.
        """
        bookmarks = []
        for row in range(self.count()):
            itm = self.item(row)
            bookmarks.append(
                {
                    "title": itm.text(),
                    "url": itm.data(self.UrlRole).toString(),
                }
            )
        Preferences.setHelp("Bookmarks", json.dumps(bookmarks))

    @pyqtSlot()
    def __exportBookmarks(self, selected=False):
        """
        Private slot to export the bookmarks into a JSON file.

        @param selected flag indicating to export the selected bookmarks
            (defaults to False)
        @type bool (optional)
        """
        filename, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.tr("Export Bookmarks"),
            "",
            self.tr("eric Bookmarks Files (*.json);;All Files (*)"),
            None,
            EricFileDialog.DontConfirmOverwrite,
        )
        if filename:
            ext = os.path.splitext(filename)[1]
            if not ext:
                ex = selectedFilter.split("(*")[1].split(")")[0]
                if ex:
                    filename += ex

            if os.path.exists(filename):
                ok = EricMessageBox.yesNo(
                    self,
                    self.tr("Export Bookmarks"),
                    self.tr(
                        """The file <b>{0}</b> already exists. Do you"""
                        """ want to overwrite it?"""
                    ).format(filename),
                )
                if not ok:
                    return

            bookmarksDict = {
                "creator": "eric7",
                "version": 1,
                "created": datetime.datetime.now(tz=datetime.timezone.utc).isoformat(
                    sep=" ", timespec="seconds"
                ),
                "bookmarks": [],
            }
            bookmarkItems = (
                self.selectedItems()
                if selected
                else [self.item(row) for row in range(self.count())]
            )
            for bookmarkItem in bookmarkItems:
                bookmarksDict["bookmarks"].append(
                    {
                        "type": "url",
                        "title": bookmarkItem.text(),
                        "url": bookmarkItem.data(self.UrlRole).toString(),
                    }
                )

            jsonStr = json.dumps(bookmarksDict, indent=2, sort_keys=True)
            try:
                with open(filename, "w") as f:
                    f.write(jsonStr)
            except OSError as err:
                EricMessageBox.critical(
                    self,
                    self.tr("Export Bookmarks"),
                    self.tr(
                        """<p>The bookmarks could not be exported"""
                        """ to <b>{0}</b>.</p><p>Reason: {1}</p>"""
                    ).format(filename, str(err)),
                )

    @pyqtSlot()
    def __importBookmarks(self):
        """
        Private slot to import bookmarks from a JSON file.
        """
        from .HelpBookmarksImportDialog import HelpBookmarksImportDialog

        dlg = HelpBookmarksImportDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            replace, filename = dlg.getData()

            try:
                with open(filename, "r") as f:
                    jsonStr = f.read()
                    bookmarks = json.loads(jsonStr)
            except (OSError, json.JSONDecodeError) as err:
                EricMessageBox.critical(
                    self,
                    self.tr("Import Bookmarks"),
                    self.tr(
                        "<p>The bookmarks file <b>{0}</b> could not be "
                        "read.</p><p>Reason: {1}</p>"
                    ).format(filename, str(err)),
                )
                return

            if not isinstance(bookmarks, dict):
                EricMessageBox.critical(
                    self,
                    self.tr("Import Bookmarks"),
                    self.tr(
                        "The bookmarks file <b>{0}</b> has invalid contents."
                    ).format(filename),
                )
                return

            try:
                if bookmarks["creator"] != "eric7":
                    EricMessageBox.critical(
                        self,
                        self.tr("Import Bookmarks"),
                        self.tr(
                            "The bookmarks file <b>{0}</b> was not created"
                            " with 'eric7'."
                        ).format(filename),
                    )
                    return

                if bookmarks["version"] != 1:
                    EricMessageBox.critical(
                        self,
                        self.tr("Import Bookmarks"),
                        self.tr(
                            "The bookmarks file <b>{0}</b> has an unsupported"
                            " format version."
                        ).format(filename),
                    )
                    return

                if replace:
                    self.clear()

                for bookmark in bookmarks["bookmarks"]:
                    if bookmark["type"] == "url":
                        self.__addBookmark(bookmark["title"], bookmark["url"])
                self.sortItems()
                self.__saveBookmarks()

            except KeyError:
                EricMessageBox.critical(
                    self,
                    self.tr("Import Bookmarks"),
                    self.tr(
                        "The bookmarks file <b>{0}</b> has invalid contents."
                    ).format(filename),
                )

    def keyPressEvent(self, evt):
        """
        Protected method handling key press events.

        @param evt reference to the key press event
        @type QKeyEvent
        """
        if evt.key() == Qt.Key.Key_Escape:
            self.escapePressed.emit()
