# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to get the data to rename a bookmark.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_HgBookmarkRenameDialog import Ui_HgBookmarkRenameDialog


class HgBookmarkRenameDialog(QDialog, Ui_HgBookmarkRenameDialog):
    """
    Class implementing a dialog to get the data to rename a bookmark.
    """

    def __init__(self, bookmarksList, parent=None):
        """
        Constructor

        @param bookmarksList list of bookmarks
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.bookmarkCombo.addItems(sorted(bookmarksList))

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateUI(self):
        """
        Private slot to update the UI.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self.nameEdit.text() != "" and self.bookmarkCombo.currentText() != ""
        )

    @pyqtSlot(str)
    def on_nameEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the bookmark name.

        @param _txt text of the edit (unused)
        @type str
        """
        self.__updateUI()

    @pyqtSlot(str)
    def on_bookmarkCombo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the selected bookmark.

        @param _txt name of the selected bookmark (unused)
        @type str
        """
        self.__updateUI()

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple naming the old and new bookmark names
        @rtype tuple of (str, str)
        """
        return (
            self.bookmarkCombo.currentText().replace(" ", "_"),
            self.nameEdit.text().replace(" ", "_"),
        )
