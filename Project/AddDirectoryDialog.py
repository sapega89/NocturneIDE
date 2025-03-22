# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to add files of a directory to the project.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_AddDirectoryDialog import Ui_AddDirectoryDialog


class AddDirectoryDialog(QDialog, Ui_AddDirectoryDialog):
    """
    Class implementing a dialog to add files of a directory to the project.
    """

    def __init__(
        self, pro, fileTypeFilter="SOURCES", parent=None, name=None, startdir=None
    ):
        """
        Constructor

        @param pro reference to the project object
        @type Project
        @param fileTypeFilter file type filter
        @type str
        @param parent parent widget of this dialog
        @type QWidget
        @param name name of this dialog
        @type str
        @param startdir start directory for the selection dialog
        @type str
        """
        super().__init__(parent)
        if name:
            self.setObjectName(name)
        self.setupUi(self)

        self.__remoteMode = (
            bool(startdir) and FileSystemUtilities.isRemoteFileName(startdir)
        ) or FileSystemUtilities.isRemoteFileName(pro.getProjectPath())

        self.sourceDirPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.sourceDirPicker.setDefaultDirectory(startdir)
        self.sourceDirPicker.setRemote(self.__remoteMode)

        self.targetDirPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.targetDirPicker.setDefaultDirectory(startdir)
        self.targetDirPicker.setRemote(self.__remoteMode)

        self.__project = pro
        if startdir:
            self.targetDirPicker.setText(startdir)
        else:
            self.targetDirPicker.setText(pro.getProjectPath())

        if fileTypeFilter and fileTypeFilter != "TRANSLATIONS":
            self.filterComboBox.addItem(
                self.__project.getFileCategoryString(fileTypeFilter),
                fileTypeFilter,
            )
        else:
            for fileCategory in sorted(
                c for c in self.__project.getFileCategories() if c != "TRANSLATIONS"
            ):
                self.filterComboBox.addItem(
                    self.__project.getFileCategoryString(fileCategory),
                    fileCategory,
                )
        self.filterComboBox.setCurrentIndex(0)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(int)
    def on_filterComboBox_currentIndexChanged(self, index):
        """
        Private slot to handle the selection of a file type.

        @param index index of the selected entry
        @type int
        """
        fileType = self.filterComboBox.itemData(index)

        if fileType == "OTHERS":
            self.targetDirLabel.setEnabled(False)
            self.targetDirPicker.setEnabled(False)
            self.recursiveCheckBox.setEnabled(False)
        else:
            self.targetDirLabel.setEnabled(True)
            self.targetDirPicker.setEnabled(True)
            self.recursiveCheckBox.setEnabled(True)

    @pyqtSlot(str)
    def on_sourceDirPicker_textChanged(self, directory):
        """
        Private slot to handle the source directory text changed.

        If the entered source directory is a subdirectory of the current
        projects main directory, the target directory path is synchronized.
        It is assumed, that the user wants to add a bunch of files to
        the project in place.

        @param directory the text of the source directory line edit
        @type str
        """
        if directory.startswith(self.__project.getProjectPath()):
            self.targetDirPicker.setText(directory)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(directory)
        )

    def getData(self):
        """
        Public slot to retrieve the dialogs data.

        @return tuple of four values giving the selected file type, the source
            and target directory and a flag indicating a recursive add
        @rtype tuple of (str, str, str, bool)
        """
        filetype = self.filterComboBox.itemData(self.filterComboBox.currentIndex())
        return (
            filetype,
            self.sourceDirPicker.text(),
            self.targetDirPicker.text(),
            self.recursiveCheckBox.isChecked(),
        )
