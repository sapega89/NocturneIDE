# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show and edit bookmark properties.
"""

from PyQt6.QtWidgets import QDialog

from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .BookmarkNode import BookmarkNodeType
from .Ui_BookmarkPropertiesDialog import Ui_BookmarkPropertiesDialog


class BookmarkPropertiesDialog(QDialog, Ui_BookmarkPropertiesDialog):
    """
    Class implementing a dialog to show and edit bookmark properties.
    """

    def __init__(self, node, parent=None):
        """
        Constructor

        @param node reference to the bookmark
        @type BookmarkNode
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__node = node
        if self.__node.type() == BookmarkNodeType.Folder:
            self.addressLabel.hide()
            self.addressEdit.hide()
            self.visitedLabel.hide()

        self.nameEdit.setText(self.__node.title)
        self.descriptionEdit.setPlainText(self.__node.desc)
        self.addressEdit.setText(self.__node.url)
        self.visitedLabel.setText(
            self.tr("Visited <b>{0}</b> times. Last visit on <b>{1}</b>.").format(
                self.__node.visitCount, self.__node.visited.toString("yyyy-MM-dd hh:mm")
            )
        )

    def accept(self):
        """
        Public slot handling the acceptance of the dialog.
        """
        if (
            self.__node.type() == BookmarkNodeType.Bookmark
            and not self.addressEdit.text()
        ) or not self.nameEdit.text():
            super().accept()
            return

        bookmarksManager = WebBrowserWindow.bookmarksManager()
        title = self.nameEdit.text()
        if title != self.__node.title:
            bookmarksManager.setTitle(self.__node, title)
        if self.__node.type() == BookmarkNodeType.Bookmark:
            url = self.addressEdit.text()
            if url != self.__node.url:
                bookmarksManager.setUrl(self.__node, url)
        description = self.descriptionEdit.toPlainText()
        if description != self.__node.desc:
            self.__node.desc = description
            bookmarksManager.setNodeChanged()

        super().accept()
