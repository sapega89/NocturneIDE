# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit feed data.
"""

from PyQt6.QtCore import QUrl, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_FeedEditDialog import Ui_FeedEditDialog


class FeedEditDialog(QDialog, Ui_FeedEditDialog):
    """
    Class implementing a dialog to edit feed data.
    """

    def __init__(self, urlString, title, parent=None):
        """
        Constructor

        @param urlString feed URL
        @type str
        @param title feed title
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.titleEdit.setText(title)
        self.urlEdit.setText(urlString)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __setOkButton(self):
        """
        Private slot to enable or disable the OK button.
        """
        enable = True

        enable = enable and bool(self.titleEdit.text())

        urlString = self.urlEdit.text()
        enable = enable and bool(urlString)
        if urlString:
            url = QUrl(urlString)
            enable = enable and bool(url.scheme())
            enable = enable and bool(url.host())

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    @pyqtSlot(str)
    def on_titleEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the feed title.

        @param _txt new feed title (unused)
        @type str
        """
        self.__setOkButton()

    @pyqtSlot(str)
    def on_urlEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the feed URL.

        @param _txt new feed URL (unused)
        @type str
        """
        self.__setOkButton()

    def getData(self):
        """
        Public method to get the entered feed data.

        @return tuple of two strings giving the feed URL and feed title
        @rtype tuple of (str, str)
        """
        return (self.urlEdit.text(), self.titleEdit.text())
