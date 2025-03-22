# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a new project sub-directory.
"""

from PyQt6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

from eric7.EricWidgets.EricPathPicker import EricPathPicker, EricPathPickerModes


class NewDirectoryDialog(QDialog):
    """
    Class implementing a dialog to enter the data for a new project sub-directory.
    """

    def __init__(
        self,
        title=None,
        label=None,
        mode=EricPathPickerModes.DIRECTORY_MODE,
        strPath=None,
        defaultDirectory=None,
        remote=False,
        parent=None,
    ):
        """
        Constructor

        @param title title of the dialog (defaults to None)
        @type str (optional)
        @param label text to be shown above the directory path picker (defaults to None)
        @type str (optional)
        @param mode mode of the path picker (defaults to
            EricPathPickerModes.DIRECTORY_MODE)
        @type EricPathPickerModes (optional)
        @param strPath initial path to be shown (defaults to None)
        @type str (optional)
        @param defaultDirectory default directory of the path picker selection dialog
            (defaults to None)
        @type str (optional)
        @param remote flag indicating the remote mode (defaults to False)
        @type bool (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)

        self.setMinimumWidth(400)

        self.__layout = QVBoxLayout(self)

        self.__label = QLabel(self)
        self.__label.setWordWrap(True)

        self.__pathPicker = EricPathPicker(self)
        self.__pathPicker.setMode(mode)
        self.__addToProjectCheckBox = QCheckBox(self.tr("Add to project"), self)
        self.__buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok,
            self,
        )

        self.__layout.addWidget(self.__label)
        self.__layout.addWidget(self.__pathPicker)
        self.__layout.addWidget(self.__addToProjectCheckBox)
        self.__layout.addWidget(self.__buttonBox)

        self.setWindowTitle(self.tr("New directory") if title is None else title)
        self.__label.setText(
            self.tr("Enter the path of the new directory:") if label is None else label
        )
        if strPath:
            self.__pathPicker.setText(strPath)
        if defaultDirectory:
            self.__pathPicker.setDefaultDirectory(defaultDirectory)
        self.__pathPicker.setRemote(remote)

        self.__buttonBox.accepted.connect(self.accept)
        self.__buttonBox.rejected.connect(self.reject)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getDirectory(self):
        """
        Public method to get the entered directory.

        @return tuple containing the entered directory and a flag indicating to add
            that directory to the project
        @rtype tuple of (str, bool)
        """
        return (
            self.__pathPicker.text().strip(),
            self.__addToProjectCheckBox.isChecked(),
        )
