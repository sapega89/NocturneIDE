# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter cherry-pick data.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_GitCherryPickDialog import Ui_GitCherryPickDialog


class GitCherryPickDialog(QDialog, Ui_GitCherryPickDialog):
    """
    Class implementing a dialog to enter cherry-pick data.
    """

    def __init__(self, commits=None, parent=None):
        """
        Constructor

        @param commits list of commits to show in the commits pane
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        if commits:
            self.commitsEdit.setPlainText("\n".join(commits))

        self.on_commitsEdit_textChanged()

    @pyqtSlot()
    def on_commitsEdit_textChanged(self):
        """
        Private slot to react upon changes of commits.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self.commitsEdit.toPlainText() != ""
        )

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple with list of commits, a flag indicating to append
            cherry-pick info to the commit message, a flag indicating to append
            a signed-off-by line to the commit message and a flag indicating to
            not commit the action
        @rtype tuple of (list of str, bool, bool, bool)
        """
        return (
            self.commitsEdit.toPlainText().strip().splitlines(),
            self.appendCheckBox.isChecked(),
            self.signoffCheckBox.isChecked(),
            self.nocommitCheckBox.isChecked(),
        )
