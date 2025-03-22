# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for an extended bisect start.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_GitBisectStartDialog import Ui_GitBisectStartDialog


class GitBisectStartDialog(QDialog, Ui_GitBisectStartDialog):
    """
    Class implementing a dialog to enter the data for an extended bisect start.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.okButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateOK(self):
        """
        Private method used to enable/disable the OK-button.
        """
        enable = self.badEdit.text() != ""
        self.okButton.setEnabled(enable)

    @pyqtSlot(str)
    def on_badEdit_textChanged(self, _txt):
        """
        Private slot to handle a change of the bad commit.

        @param _txt bad commit entered (unused)
        @type str
        """
        self.__updateOK()

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing a bad commit, a list of good commits and
            a flag indicating to not checkout the working tree
        @rtype tuple of (str, list of str, bool)
        """
        return (
            self.badEdit.text().strip(),
            self.goodEdit.text().strip().split(),
            self.noCheckoutCheckBox.isChecked(),
        )
