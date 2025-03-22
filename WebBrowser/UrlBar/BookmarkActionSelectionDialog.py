# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select the action to be performed on the
bookmark.
"""

import enum

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7.EricGui import EricPixmapCache
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .Ui_BookmarkActionSelectionDialog import Ui_BookmarkActionSelectionDialog


class BookmarkAction(enum.Enum):
    """
    Class defining the available bookmark actions.
    """

    Undefined = -1
    AddBookmark = 0
    EditBookmark = 1
    AddSpeeddial = 2
    RemoveSpeeddial = 3


class BookmarkActionSelectionDialog(QDialog, Ui_BookmarkActionSelectionDialog):
    """
    Class implementing a dialog to select the action to be performed on
    the bookmark.
    """

    def __init__(self, url, parent=None):
        """
        Constructor

        @param url URL to be worked on
        @type QUrl
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__action = BookmarkAction.Undefined

        self.icon.setPixmap(EricPixmapCache.getPixmap("bookmark32"))

        if WebBrowserWindow.bookmarksManager().bookmarkForUrl(url) is None:
            self.__bmAction = BookmarkAction.AddBookmark
            self.bookmarkPushButton.setText(self.tr("Add Bookmark"))
        else:
            self.__bmAction = BookmarkAction.EditBookmark
            self.bookmarkPushButton.setText(self.tr("Edit Bookmark"))

        if WebBrowserWindow.speedDial().pageForUrl(url).url:
            self.__sdAction = BookmarkAction.RemoveSpeeddial
            self.speeddialPushButton.setText(self.tr("Remove from Speed Dial"))
        else:
            self.__sdAction = BookmarkAction.AddSpeeddial
            self.speeddialPushButton.setText(self.tr("Add to Speed Dial"))

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def on_bookmarkPushButton_clicked(self):
        """
        Private slot handling selection of a bookmark action.
        """
        self.__action = self.__bmAction
        self.accept()

    @pyqtSlot()
    def on_speeddialPushButton_clicked(self):
        """
        Private slot handling selection of a speed dial action.
        """
        self.__action = self.__sdAction
        self.accept()

    def getAction(self):
        """
        Public method to get the selected action.

        @return reference to the associated action
        @rtype QAction
        """
        return self.__action
