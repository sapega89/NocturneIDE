# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Subversion command dialog.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Utilities
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_SvnCommandDialog import Ui_SvnCommandDialog


class SvnCommandDialog(QDialog, Ui_SvnCommandDialog):
    """
    Class implementing the Subversion command dialog.

    It implements a dialog that is used to enter an
    arbitrary subversion command. It asks the user to enter
    the commandline parameters and the working directory.
    """

    def __init__(self, argvList, wdList, ppath, parent=None):
        """
        Constructor

        @param argvList history list of commandline arguments
        @type list of str
        @param wdList history list of working directories
        @type list of str
        @param ppath pathname of the project directory
        @type str
        @param parent parent widget of this dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.workdirPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)

        self.okButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)

        self.commandCombo.completer().setCaseSensitivity(
            Qt.CaseSensitivity.CaseSensitive
        )
        self.commandCombo.clear()
        self.commandCombo.addItems(argvList)
        if len(argvList) > 0:
            self.commandCombo.setCurrentIndex(0)
        self.workdirPicker.clear()
        self.workdirPicker.addItems(wdList)
        if len(wdList) > 0:
            self.workdirPicker.setCurrentIndex(0)
        self.projectDirLabel.setText(ppath)

        # modify some what's this help texts
        t = self.commandCombo.whatsThis()
        if t:
            t += Utilities.getPercentReplacementHelp()
            self.commandCombo.setWhatsThis(t)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_commandCombo_editTextChanged(self, _text):
        """
        Private method used to enable/disable the OK-button.

        @param _text text of the command combobox (unused)
        @type str
        """
        self.okButton.setDisabled(self.commandCombo.currentText() == "")

    def getData(self):
        """
        Public method to retrieve the data entered into this dialog.

        @return tuple cotaining the command line arguments and the working directory
        @rtype tuple of (str, str)
        """
        return (self.commandCombo.currentText(), self.workdirPicker.currentText())
