# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the parameters for a coverage HTML
report.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_PyCoverageHtmlReportDialog import Ui_PyCoverageHtmlReportDialog


class PyCoverageHtmlReportDialog(QDialog, Ui_PyCoverageHtmlReportDialog):
    """
    Class implementing a dialog to enter the parameters for a coverage HTML
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

        self.outputDirectoryPicker.setMode(
            EricPathPickerModes.DIRECTORY_SHOW_FILES_MODE
        )
        self.outputDirectoryPicker.setDefaultDirectory(defaultDirectory)

        self.extraCssPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_outputDirectoryPicker_textChanged(self, directory):
        """
        Private slot handling a change of the output directory.

        @param directory current text of the directory picker
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(directory)
        )

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the report title, the output directory, the
            path of a file containing extra CSS and a flag indicating to open
            the generated report in a browser
        @rtype tuple of (str, str, str, bool)
        """
        title = self.titleEdit.text()
        return (
            title if bool(title) else None,
            self.outputDirectoryPicker.currentText(),
            self.extraCssPicker.currentText(),
            self.openReportCheckBox.isChecked(),
        )
