# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the configuration for the embedded environment
of the project.
"""

import glob
import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import OSUtilities

from .Ui_ProjectVenvConfigurationDialog import Ui_ProjectVenvConfigurationDialog


class ProjectVenvConfigurationDialog(QDialog, Ui_ProjectVenvConfigurationDialog):
    """
    Class implementing a dialog to enter the configuration for the embedded
    environment of the project.
    """

    def __init__(
        self,
        venvName="",
        venvDirectory="",
        venvInterpreter="",
        execPath="",
        parent=None,
    ):
        """
        Constructor

        @param venvName logical name of a virtual environment for editing
        @type str
        @param venvDirectory directory of the virtual environment
        @type str
        @param venvInterpreter Python interpreter of the virtual environment
        @type str
        @param execPath search path string to be prepended to the PATH
            environment variable
        @type str
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__venvName = venvName

        self.pythonExecPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.pythonExecPicker.setWindowTitle(self.tr("Python Interpreter"))
        self.pythonExecPicker.setDefaultDirectory(venvDirectory)

        self.execPathEdit.setToolTip(
            self.tr(
                "Enter the executable search path to be prepended to the PATH"
                " environment variable. Use '{0}' as the separator."
            ).format(os.pathsep)
        )

        self.nameEdit.setText(venvName)
        self.execPathEdit.setText(execPath)

        if venvDirectory:
            # try to determine a Python interpreter name
            if OSUtilities.isWindowsPlatform():
                candidates = glob.glob(
                    os.path.join(venvDirectory, "Scripts", "python*.exe")
                ) + glob.glob(os.path.join(venvDirectory, "python*.exe"))
            else:
                candidates = glob.glob(os.path.join(venvDirectory, "bin", "python*"))
            self.pythonExecPicker.addItems(sorted(candidates))

        if venvInterpreter:
            self.pythonExecPicker.setText(venvInterpreter)
        else:
            self.pythonExecPicker.setText(venvDirectory)

        self.__updateOK()

    @pyqtSlot(str)
    def __updateOK(self):
        """
        Private method to update the enabled status of the OK button.
        """
        interpreterPath = self.pythonExecPicker.text()
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(interpreterPath)
            and os.path.isfile(interpreterPath)
            and os.access(interpreterPath, os.X_OK)
        )

    @pyqtSlot(str)
    def on_pythonExecPicker_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the entered Python interpreter path.

        @param _txt entered Python interpreter path (unused)
        @type str
        """
        self.__updateOK()

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the path of the selected Python interpreter and
            a string to be prepended to the PATH environment variable
        @rtype tuple of (str, str)
        """
        return self.pythonExecPicker.text(), self.execPathEdit.text()
