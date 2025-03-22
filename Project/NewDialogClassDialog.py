# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a new dialog class file.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_NewDialogClassDialog import Ui_NewDialogClassDialog


class NewDialogClassDialog(QDialog, Ui_NewDialogClassDialog):
    """
    Class implementing a dialog to ente the data for a new dialog class file.
    """

    def __init__(self, defaultClassName, defaultFile, defaultPath, parent=None):
        """
        Constructor

        @param defaultClassName proposed name for the new class
        @type str
        @param defaultFile proposed name for the source file
        @type str
        @param defaultPath default path for the new file
        @type str
        @param parent parent widget if the dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.pathnamePicker.setMode(EricPathPickerModes.DIRECTORY_MODE)

        self.okButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)

        self.classnameEdit.setText(defaultClassName)
        self.filenameEdit.setText(defaultFile)
        self.pathnamePicker.setText(defaultPath)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __enableOkButton(self):
        """
        Private slot to set the enable state of theok button.
        """
        self.okButton.setEnabled(
            self.classnameEdit.text() != ""
            and self.filenameEdit.text() != ""
            and self.pathnamePicker.text() != ""
        )

    @pyqtSlot(str)
    def on_classnameEdit_textChanged(self, text):
        """
        Private slot called, when thext of the classname edit has changed.

        @param text changed text
        @type str
        """
        self.__enableOkButton()

    @pyqtSlot(str)
    def on_filenameEdit_textChanged(self, text):
        """
        Private slot called, when thext of the filename edit has changed.

        @param text changed text
        @type str
        """
        self.__enableOkButton()

    @pyqtSlot(str)
    def on_pathnamePicker_textChanged(self, text):
        """
        Private slot called, when the text of the path name has changed.

        @param text changed text
        @type str
        """
        self.__enableOkButton()

    def getData(self):
        """
        Public method to retrieve the data entered into the dialog.

        @return tuple giving the classname and the file name
        @rtype tuple of (str, str)
        """
        return (
            self.classnameEdit.text(),
            os.path.join(self.pathnamePicker.text(), self.filenameEdit.text()),
        )
