# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the bookmark dialog.
"""

import enum

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_HgBookmarkDialog import Ui_HgBookmarkDialog


class HgBookmarkAction(enum.Enum):
    """
    Class defining the supported bookmark actions.
    """

    DEFINE = 0
    MOVE = 1


class HgBookmarkDialog(QDialog, Ui_HgBookmarkDialog):
    """
    Class mplementing the bookmark dialog.
    """

    def __init__(self, action, tagsList, branchesList, bookmarksList, parent=None):
        """
        Constructor

        @param action bookmark action to be performed
        @type HgBookmarkAction
        @param tagsList list of tags
        @type list of str
        @param branchesList list of branches
        @type list of str
        @param bookmarksList list of bookmarks
        @type list of str
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.__action = action
        if action == HgBookmarkAction.MOVE:
            self.nameEdit.hide()
            self.nameCombo.addItems([""] + sorted(bookmarksList))
            self.setWindowTitle(self.tr("Move Bookmark"))
        else:
            self.nameCombo.hide()
            self.setWindowTitle(self.tr("Define Bookmark"))

        self.__bookmarksList = bookmarksList[:]

        self.tagCombo.addItems(sorted(tagsList))
        self.branchCombo.addItems(["default"] + sorted(branchesList))
        self.bookmarkCombo.addItems(sorted(bookmarksList))

        # connect various radio buttons and input fields
        self.idButton.toggled.connect(self.__updateOK)
        self.tagButton.toggled.connect(self.__updateOK)
        self.branchButton.toggled.connect(self.__updateOK)
        self.bookmarkButton.toggled.connect(self.__updateOK)
        self.expressionButton.toggled.connect(self.__updateOK)

        self.nameCombo.activated.connect(self.__updateOK)
        self.nameCombo.activated.connect(self.__updateBookmarksCombo)

        self.nameEdit.textChanged.connect(self.__updateOK)
        self.idEdit.textChanged.connect(self.__updateOK)
        self.expressionEdit.textChanged.connect(self.__updateOK)

        self.tagCombo.editTextChanged.connect(self.__updateOK)
        self.branchCombo.editTextChanged.connect(self.__updateOK)
        self.bookmarkCombo.editTextChanged.connect(self.__updateOK)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = (
            bool(self.nameCombo.currentText())
            if self.__action == HgBookmarkAction.MOVE
            else bool(self.nameEdit.text())
        )

        if self.idButton.isChecked():
            enabled = bool(self.idEdit.text())
        elif self.tagButton.isChecked():
            enabled = bool(self.tagCombo.currentText())
        elif self.branchButton.isChecked():
            enabled = bool(self.branchCombo.currentText())
        elif self.bookmarkButton.isChecked():
            enabled = bool(self.bookmarkCombo.currentText())
        elif self.expressionButton.isChecked():
            enabled = enabled and bool(self.expressionEdit.text())

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    def __updateBookmarksCombo(self):
        """
        Private slot to update the bookmarks combo.
        """
        if self.__action == HgBookmarkAction.MOVE:
            bookmark = self.nameCombo.currentText()
            selectedBookmark = self.bookmarkCombo.currentText()
            self.bookmarkCombo.clearEditText()
            self.bookmarkCombo.clear()
            self.bookmarkCombo.addItems(sorted(self.__bookmarksList))
            index = self.bookmarkCombo.findText(bookmark)
            if index > -1:
                self.bookmarkCombo.removeItem(index)
            if selectedBookmark:
                index = self.bookmarkCombo.findText(selectedBookmark)
                if index > -1:
                    self.bookmarkCombo.setCurrentIndex(index)

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple naming the revision and the bookmark name
        @rtype tuple of (str, str)
        """
        if self.numberButton.isChecked():
            rev = "rev({0})".format(self.numberSpinBox.value())
        elif self.idButton.isChecked():
            rev = "id({0})".format(self.idEdit.text())
        elif self.tagButton.isChecked():
            rev = self.tagCombo.currentText()
        elif self.branchButton.isChecked():
            rev = self.branchCombo.currentText()
        elif self.bookmarkButton.isChecked():
            rev = self.bookmarkCombo.currentText()
        elif self.expressionButton.isChecked():
            rev = self.expressionEdit.text()
        else:
            rev = ""

        name = (
            self.nameCombo.currentText().replace(" ", "_")
            if self.__action == HgBookmarkAction.MOVE
            else self.nameEdit.text().replace(" ", "_")
        )

        return rev, name
