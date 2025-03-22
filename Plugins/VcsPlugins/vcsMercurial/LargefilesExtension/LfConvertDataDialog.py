# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for the repo conversion.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities

from . import getDefaults
from .Ui_LfConvertDataDialog import Ui_LfConvertDataDialog


class LfConvertDataDialog(QDialog, Ui_LfConvertDataDialog):
    """
    Class implementing a dialog to enter the data for the repo conversion.
    """

    def __init__(self, currentPath, mode, parent=None):
        """
        Constructor

        @param currentPath directory name of the current project
        @type str
        @param mode dialog mode (one of 'largefiles' or 'normal')
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.newProjectPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)

        self.__defaults = getDefaults()
        self.__currentPath = FileSystemUtilities.toNativeSeparators(currentPath)

        self.currentProjectLabel.setPath(currentPath)
        self.newProjectPicker.setText(os.path.dirname(currentPath))

        self.lfFileSizeSpinBox.setValue(self.__defaults["minsize"])
        self.lfFilePatternsEdit.setText(" ".join(self.__defaults["pattern"]))

        if mode == "normal":
            self.lfFileSizeSpinBox.setEnabled(False)
            self.lfFilePatternsEdit.setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_newProjectPicker_textChanged(self, txt):
        """
        Private slot to handle editing of the new project directory.

        @param txt new project directory name
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            txt
            and FileSystemUtilities.toNativeSeparators(txt)
            != os.path.dirname(self.__currentPath)
        )

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple containing the new project directory name, minimum file size
            and file patterns
        @rtype tuple of (str, int, list of str)
        """
        patterns = self.lfFilePatternsEdit.text().split()
        if set(patterns) == set(self.__defaults["pattern"]):
            patterns = []

        return (
            self.newProjectPicker.text(),
            self.lfFileSizeSpinBox.value(),
            patterns,
        )
