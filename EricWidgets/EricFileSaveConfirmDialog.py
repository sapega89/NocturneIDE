# -*- coding: utf-8 -*-

# Copyright (c) 2018 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter a file system path using a file picker.
"""

import os

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout

from .EricPathPicker import EricPathPicker, EricPathPickerModes


class EricFileSaveConfirmDialog(QDialog):
    """
    Class implementing a dialog to enter a file system path using a file
    picker.
    """

    def __init__(self, filename, title, message="", picker=True, parent=None):
        """
        Constructor

        @param filename file name to be shown
        @type str
        @param title title for the dialog
        @type str
        @param message message to be shown
        @type str
        @param picker flag indicating to use a path picker
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setMinimumWidth(400)

        self.__selectedAction = "cancel"
        self.__filename = filename

        self.__layout = QVBoxLayout(self)

        self.__label = QLabel(self)
        self.__label.setWordWrap(True)
        if message:
            self.__label.setText(message)
        else:
            self.__label.setText(self.tr("The given file exists already."))

        if picker:
            self.__pathPicker = EricPathPicker(self)
            self.__pathPicker.setMode(EricPathPickerModes.SAVE_FILE_MODE)
        else:
            self.__pathPicker = QLineEdit(self)
            self.__pathPicker.setClearButtonEnabled(True)

        self.__buttonBox = QDialogButtonBox(self)
        self.__cancelButton = self.__buttonBox.addButton(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.__overwriteButton = self.__buttonBox.addButton(
            self.tr("Overwrite"), QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.__renameButton = self.__buttonBox.addButton(
            self.tr("Rename"), QDialogButtonBox.ButtonRole.AcceptRole
        )

        self.__layout.addWidget(self.__label)
        self.__layout.addWidget(self.__pathPicker)
        self.__layout.addWidget(self.__buttonBox)

        # set values and states
        self.__pathPicker.setText(filename)
        if picker:
            self.__pathPicker.setDefaultDirectory(os.path.dirname(filename))
        self.__renameButton.setEnabled(False)
        self.__cancelButton.setDefault(True)

        self.__buttonBox.clicked.connect(self.__buttonBoxClicked)
        self.__pathPicker.textChanged.connect(self.__filenameChanged)

    def __buttonBoxClicked(self, button):
        """
        Private slot to handle the user clicking a button.

        @param button reference to the clicked button
        @type QAbstractButton
        """
        if button == self.__cancelButton:
            self.__selectedAction = "cancel"
            self.reject()
        elif button == self.__renameButton:
            self.__selectedAction = "rename"
            self.accept()
        elif button == self.__overwriteButton:
            self.__selectedAction = "overwrite"
            self.accept()

    def __filenameChanged(self, text):
        """
        Private slot to handle a change of the file name.

        @param text new file name
        @type str
        """
        self.__renameButton.setEnabled(text != self.__filename)

    def selectedAction(self):
        """
        Public method to get the selected action and associated data.

        @return tuple containing the selected action (cancel, rename,
            overwrite) and the filename (in case of 'rename' or 'overwrite')
        @rtype tuple of (str, str)
        """
        if self.__selectedAction == "rename":
            filename = self.__pathPicker.text()
        elif self.__selectedAction == "overwrite":
            filename = self.__filename
        else:
            filename = ""
        return self.__selectedAction, filename


def confirmOverwrite(filename, title, message="", picker=True, parent=None):
    """
    Function to confirm that a file shall be overwritten.

    @param filename file name to be shown
    @type str
    @param title title for the dialog
    @type str
    @param message message to be shown
    @type str
    @param picker flag indicating to use a path picker
    @type bool
    @param parent reference to the parent widget
    @type QWidget
    @return tuple containing the selected action (cancel, rename,
        overwrite) and the filename (in case of 'rename' or 'overwrite')
    @rtype tuple of (str, str)
    """
    if parent is None:
        parent = QCoreApplication.instance().getMainWindow()

    dlg = EricFileSaveConfirmDialog(
        filename, title, message=message, picker=picker, parent=parent
    )
    dlg.exec()
    return dlg.selectedAction()
