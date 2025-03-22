# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the file filter properties.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_FindFileFilterPropertiesDialog import Ui_FindFileFilterPropertiesDialog


class FindFileFilterPropertiesDialog(QDialog, Ui_FindFileFilterPropertiesDialog):
    """
    Class implementing a dialog to enter the file filter properties.
    """

    def __init__(self, currentFilters, properties=None, parent=None):
        """
        Constructor

        @param currentFilters list of existing filters to check against
        @type list of str
        @param properties tuple containing the filter name and pattern
            to be edited (defaults to None)
        @type tuple of (str, str) (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__filters = currentFilters

        self.__editMode = properties is not None
        if self.__editMode:
            self.textEdit.setText(properties[0])
            self.patternEdit.setText(properties[1])

        self.__updateOKAndError()

        self.textEdit.textChanged.connect(self.__updateOKAndError)
        self.patternEdit.textChanged.connect(self.__updateOKAndError)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __updateOKAndError(self):
        """
        Private slot to set the enabled state of the OK button.
        """
        filterText = self.textEdit.text()
        patternText = self.patternEdit.text()

        # 1. Set state of the OK button.
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(filterText) and filterText not in self.__filters and bool(patternText)
        )

        # 2. Give the user an indication why OK is not enabled.
        if filterText in self.__filters:
            self.errorLabel.setText(self.tr("The filter name exists already."))
        elif not bool(filterText) or not bool(patternText):
            self.errorLabel.setText(
                self.tr("The filter name and/or pattern must not be empty.")
            )
        else:
            self.errorLabel.clear()

    def getProperties(self):
        """
        Public method to retrieve the entered filter properties.

        @return tuple cotaining the filter name and pattern
        @rtype tuple of (str, str)
        """
        return self.textEdit.text(), self.patternEdit.text().strip()
