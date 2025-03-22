# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show some bookmark info.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QDialog

from eric7.EricGui import EricPixmapCache
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .Ui_BookmarkInfoDialog import Ui_BookmarkInfoDialog


class BookmarkInfoDialog(QDialog, Ui_BookmarkInfoDialog):
    """
    Class implementing a dialog to show some bookmark info.
    """

    def __init__(self, bookmark, parent=None):
        """
        Constructor

        @param bookmark reference to the bookmark to be shown
        @type Bookmark
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__bookmark = bookmark

        self.icon.setPixmap(EricPixmapCache.getPixmap("bookmark32"))

        font = QFont()
        font.setPointSize(font.pointSize() + 2)
        self.title.setFont(font)

        if bookmark is None:
            self.titleEdit.setEnabled(False)
        else:
            self.titleEdit.setText(bookmark.title)
            self.titleEdit.setFocus()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def on_removeButton_clicked(self):
        """
        Private slot to remove the current bookmark.
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        bm = WebBrowserWindow.bookmarksManager()
        bm.removeBookmark(self.__bookmark)
        self.close()

    def accept(self):
        """
        Public slot handling the acceptance of the dialog.
        """
        if (
            self.__bookmark is not None
            and self.titleEdit.text() != self.__bookmark.title
        ):
            bm = WebBrowserWindow.bookmarksManager()
            bm.setTitle(self.__bookmark, self.titleEdit.text())
        self.close()
