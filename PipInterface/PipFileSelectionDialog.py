# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing a dialog to enter a file to be processed.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_PipFileSelectionDialog import Ui_PipFileSelectionDialog


class PipFileSelectionDialog(QDialog, Ui_PipFileSelectionDialog):
    """
    Class implementing a dialog to enter a file to be processed.
    """

    def __init__(self, mode, install=True, parent=None):
        """
        Constructor

        @param mode mode of the dialog
        @type str
        @param install flag indicating an install action
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        if mode == "requirements":
            self.fileLabel.setText(self.tr("Enter requirements file:"))
            self.filePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
            self.filePicker.setToolTip(
                self.tr(
                    "Press to select the requirements file through a file"
                    " selection dialog."
                )
            )
            self.filePicker.setFilters(self.tr("Text Files (*.txt);;All Files (*)"))
        elif mode == "pyproject":
            self.fileLabel.setText(self.tr("Enter 'pyproject.toml' file:"))
            self.filePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
            self.filePicker.setToolTip(
                self.tr(
                    "Press to select the 'pyproject.toml' file through a file"
                    " selection dialog."
                )
            )
            self.filePicker.setFilters(self.tr("TOML Files (*.toml);;All Files (*)"))
        elif mode == "package":
            self.fileLabel.setText(self.tr("Enter package file:"))
            self.filePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
            self.filePicker.setToolTip(
                self.tr(
                    "Press to select the package file through a file"
                    " selection dialog."
                )
            )
            self.filePicker.setFilters(
                self.tr(
                    "Python Wheel (*.whl);;"
                    "Archive Files (*.tar.gz *.zip);;"
                    "All Files (*)"
                )
            )
        else:
            self.fileLabel.setText(self.tr("Enter file name:"))
            self.filePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
            self.filePicker.setToolTip(
                self.tr("Press to select a file through a file selection dialog.")
            )
            self.filePicker.setFilters(self.tr("All Files (*)"))
        self.filePicker.setDefaultDirectory(os.path.expanduser("~"))

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.userCheckBox.setVisible(install)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_filePicker_textChanged(self, txt):
        """
        Private slot to handle entering the name of a file.

        @param txt name of the file
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(txt) and os.path.exists(FileSystemUtilities.toNativeSeparators(txt))
        )

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple with the name of the selected file and a flag indicating
            to install to the user install directory
        @rtype tuple of (str, bool)
        """
        return (self.filePicker.text(), self.userCheckBox.isChecked())
