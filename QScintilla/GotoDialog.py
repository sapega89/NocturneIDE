# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Goto dialog.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_GotoDialog import Ui_GotoDialog


class GotoDialog(QDialog, Ui_GotoDialog):
    """
    Class implementing the Goto dialog.
    """

    def __init__(self, maximum, curLine, parent, name=None, modal=False):
        """
        Constructor

        @param maximum maximum allowed for the spinbox
        @type int
        @param curLine current line number
        @type int
        @param parent parent widget of this dialog
        @type QWidget
        @param name name of this dialog
        @type str
        @param modal flag indicating a modal dialog
        @type bool
        """
        super().__init__(parent)
        if name:
            self.setObjectName(name)
        self.setupUi(self)
        self.setModal(modal)

        self.linenumberSpinBox.setMaximum(maximum)
        self.linenumberSpinBox.setValue(curLine)
        self.linenumberSpinBox.selectAll()
        self.linenumberSpinBox.setFocus(Qt.FocusReason.OtherFocusReason)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setDefault(True)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getLinenumber(self):
        """
        Public method to retrieve the linenumber.

        @return line number
        @rtype int
        """
        return self.linenumberSpinBox.value()
