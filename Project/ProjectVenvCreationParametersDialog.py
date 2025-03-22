# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the parameters for the creation of the embedded
virtual environment.
"""

from PyQt6.QtWidgets import QDialog

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import PythonUtilities

from .Ui_ProjectVenvCreationParametersDialog import (
    Ui_ProjectVenvCreationParametersDialog,
)


class ProjectVenvCreationParametersDialog(
    QDialog, Ui_ProjectVenvCreationParametersDialog
):
    """
    Class implementing a dialog to enter the parameters for the creation of the embedded
    virtual environment.
    """

    def __init__(self, withSystemSitePackages=False, parent=None):
        """
        Constructor

        @param withSystemSitePackages flag indicating to access the system site-packages
            (defaults to False)
        @type bool
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.pythonExecPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.pythonExecPicker.setWindowTitle(self.tr("Python Interpreter"))
        self.pythonExecPicker.setDefaultDirectory(PythonUtilities.getPythonExecutable())

        self.systemCheckBox.setChecked(withSystemSitePackages)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple containing the path of the Python executable and a flag indicating
            to enable access to the system wide site-packages
        @rtype tuple of (str, bool)
        """
        return self.pythonExecPicker.text().strip(), self.systemCheckBox.isChecked()
