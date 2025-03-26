# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to confirm deletion of multiple files.
"""

from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_DeleteFilesConfirmationDialog import Ui_DeleteFilesConfirmationDialog


class DeleteFilesConfirmationDialog(QDialog, Ui_DeleteFilesConfirmationDialog):
    """
    Class implementing a dialog to confirm deletion of multiple files.
    """

    def __init__(self, parent, caption, message, files):
        """
        Constructor

        @param parent parent of this dialog
        @type QWidget
        @param caption window title for the dialog
        @type str
        @param message message to be shown
        @type str
        @param files list of filenames to be shown
        @type list of str
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setModal(True)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Yes).setAutoDefault(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.No).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.No).setFocus()

        self.setWindowTitle(caption)
        self.message.setText(message)

        self.filesList.addItems(files)

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Yes):
            self.accept()
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.No):
            self.reject()
