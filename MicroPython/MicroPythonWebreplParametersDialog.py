# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the parameters for the WebREPL server.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_MicroPythonWebreplParametersDialog import Ui_MicroPythonWebreplParametersDialog


class MicroPythonWebreplParametersDialog(
    QDialog, Ui_MicroPythonWebreplParametersDialog
):
    """
    Class implementing a dialog to enter the parameters for the WebREPL server.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.passwordEdit.textChanged.connect(self.__updateOk)
        self.passwordConfirmEdit.textChanged.connect(self.__updateOk)

    @pyqtSlot()
    def __updateOk(self):
        """
        Private slot to update the enabled state of the OK button.
        """
        pw = self.passwordEdit.text()
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            4 <= len(pw) <= 9 and self.passwordConfirmEdit.text() == pw
        )

    def getParameters(self):
        """
        Public method to retrieve the entered data.

        @return tuple containing the password
        @rtype tuple of (str,)
        """
        return (self.passwordEdit.text(),)
