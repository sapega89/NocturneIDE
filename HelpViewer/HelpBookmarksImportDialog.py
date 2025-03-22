# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the bookmarks import parameters.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_HelpBookmarksImportDialog import Ui_HelpBookmarksImportDialog


class HelpBookmarksImportDialog(QDialog, Ui_HelpBookmarksImportDialog):
    """
    Class implementing a dialog to enter the bookmarks import parameters.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.bookmarksPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.bookmarksPicker.setFilters(
            self.tr("eric Bookmarks Files (*.json);;All Files (*)")
        )
        self.bookmarksPicker.textChanged.connect(self.__updateOkButton)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

        self.__updateOkButton()

    @pyqtSlot()
    def __updateOkButton(self):
        """
        Private method to update the state of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.bookmarksPicker.text())
        )

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple containing a flag indicating to replace the existing
            bookmarks and the path of the bookmarks file to be imported
        @rtype tuple of (bool, str)
        """
        return (
            self.replaceCheckBox.isChecked(),
            self.bookmarksPicker.text(),
        )
