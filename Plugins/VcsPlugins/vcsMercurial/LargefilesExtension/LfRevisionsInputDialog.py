# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter a series of revisions.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_LfRevisionsInputDialog import Ui_LfRevisionsInputDialog


class LfRevisionsInputDialog(QDialog, Ui_LfRevisionsInputDialog):
    """
    Class implementing a dialog to enter a series of revisions.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    @pyqtSlot()
    def on_revisionsEdit_textChanged(self):
        """
        Private slot handling a change of revisions.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.revisionsEdit.toPlainText())
        )

    def getRevisions(self):
        """
        Public method to retrieve the entered revisions.

        @return list of revisions
        @rtype list of str
        """
        return self.revisionsEdit.toPlainText().splitlines()
