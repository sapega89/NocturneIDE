# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter data for a new conda environment.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_CondaNewEnvironmentDataDialog import Ui_CondaNewEnvironmentDataDialog


class CondaNewEnvironmentDataDialog(QDialog, Ui_CondaNewEnvironmentDataDialog):
    """
    Class implementing a dialog to enter data for a new conda environment.
    """

    def __init__(self, title, showRequirements, parent=None):
        """
        Constructor

        @param title tirle of the dialog
        @type str
        @param showRequirements flag indicating to show the requirements
            file input widget
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowTitle(title)

        self.__requirementsMode = showRequirements

        self.requirementsFilePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.requirementsFilePicker.setFilters(
            self.tr("Text Files (*.txt);;All Files (*)")
        )

        self.requirementsLabel.setVisible(showRequirements)
        self.requirementsFilePicker.setVisible(showRequirements)

        self.__updateOK()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateOK(self):
        """
        Private method to update the enabled state of the OK button.
        """
        enable = bool(self.nameEdit.text()) and bool(self.condaNameEdit.text())
        if self.__requirementsMode:
            enable &= bool(self.requirementsFilePicker.text())

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    @pyqtSlot(str)
    def on_nameEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the logical name.

        @param _txt current text of the logical name entry (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_condaNameEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the conda name.

        @param _txt current text of the conda name entry (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_requirementsFilePicker_textChanged(self, _txt):
        """
        Private slot to handle changes of the requirements file name.

        @param _txt current text of the requirements file name entry (unused)
        @type str
        """
        self.__updateOK()

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple with the logical name of the new environment, the conda
            name and the requirements file name
        @rtype tuple of (str, str, str)
        """
        requirementsFile = (
            self.requirementsFilePicker.text() if self.__requirementsMode else ""
        )

        return (self.nameEdit.text(), self.condaNameEdit.text(), requirementsFile)
