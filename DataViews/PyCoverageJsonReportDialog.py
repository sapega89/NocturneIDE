# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the parameters for a coverage JSON
report.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_PyCoverageJsonReportDialog import Ui_PyCoverageJsonReportDialog


class PyCoverageJsonReportDialog(QDialog, Ui_PyCoverageJsonReportDialog):
    """
    Class implementing a dialog to enter the parameters for a coverage JSON
    report.
    """

    def __init__(self, defaultDirectory, parent=None):
        """
        Constructor

        @param defaultDirectory default directory for selecting the output
            directory
        @type str
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.outputFilePicker.setMode(
            EricPathPickerModes.SAVE_FILE_ENSURE_EXTENSION_MODE
        )
        self.outputFilePicker.setDefaultDirectory(defaultDirectory)
        self.outputFilePicker.setFilters(self.tr("JSON Files (*.json);;All Files (*)"))
        self.outputFilePicker.setText(os.path.join(defaultDirectory, "coverage.json"))

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_outputFilePicker_textChanged(self, filename):
        """
        Private slot handling a change of the output file.

        @param filename current text of the file picker
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(filename)
        )

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the output file and a flag indicating the
            creation of a compact JSON file
        @rtype tuple of (str, bool)
        """
        return (
            self.outputFilePicker.currentText(),
            self.compactCheckBox.isChecked(),
        )
