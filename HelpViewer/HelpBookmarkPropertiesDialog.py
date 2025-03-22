# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit the bookmark properties.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_HelpBookmarkPropertiesDialog import Ui_HelpBookmarkPropertiesDialog


class HelpBookmarkPropertiesDialog(QDialog, Ui_HelpBookmarkPropertiesDialog):
    """
    Class implementing a dialog to edit the bookmark properties.
    """

    def __init__(self, title="", url="", parent=None):
        """
        Constructor

        @param title title for the bookmark (defaults to "")
        @type str (optional)
        @param url URL for the bookmark (defaults to "")
        @type str (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.titleEdit.textChanged.connect(self.__updateOkButton)
        self.urlEdit.textChanged.connect(self.__updateOkButton)

        self.titleEdit.setText(title)
        self.urlEdit.setText(url)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __updateOkButton(self):
        """
        Private method to set the enabled state of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.titleEdit.text().strip()) and bool(self.urlEdit.text().strip())
        )

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple containing the title and URL for the bookmark
        @rtype tuple of (str, str)
        """
        return (
            self.titleEdit.text().strip(),
            self.urlEdit.text().strip(),
        )
