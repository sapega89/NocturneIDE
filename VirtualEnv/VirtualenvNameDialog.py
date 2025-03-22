# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the logical name for a new virtual
environment.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_VirtualenvNameDialog import Ui_VirtualenvNameDialog


class VirtualenvNameDialog(QDialog, Ui_VirtualenvNameDialog):
    """
    Class implementing a dialog to enter the logical name for a new virtual
    environment.
    """

    def __init__(self, environments, currentName, parent=None):
        """
        Constructor

        @param environments list of environment names to be shown
        @type list of str
        @param currentName name to be shown in the name edit
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.envsList.addItems(environments)
        self.nameEdit.setText(currentName)

        self.nameEdit.setFocus(Qt.FocusReason.OtherFocusReason)
        self.nameEdit.selectAll()

    @pyqtSlot(str)
    def on_nameEdit_textChanged(self, txt):
        """
        Private slot to handle a change of the environment name.

        @param txt contens of the name edit
        @type str
        """
        items = self.envsList.findItems(txt, Qt.MatchFlag.MatchExactly)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(txt) and len(items) == 0
        )

    def getName(self):
        """
        Public method to get the entered name.

        @return name for the environment
        @rtype str
        """
        return self.nameEdit.text()
