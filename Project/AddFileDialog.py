# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to add a file to the project.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_AddFileDialog import Ui_AddFileDialog


class AddFileDialog(QDialog, Ui_AddFileDialog):
    """
    Class implementing a dialog to add a file to the project.
    """

    def __init__(self, pro, parent=None, fileTypeFilter=None, name=None, startdir=None):
        """
        Constructor

        @param pro reference to the project object
        @type Project
        @param parent parent widget of this dialog
        @type QWidget
        @param fileTypeFilter filter specification for the file to add
        @type str
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

        self.sourceFilesPicker.setMode(EricPathPickerModes.OPEN_FILES_MODE)
        self.sourceFilesPicker.setRemote(self.__remoteMode)

        self.targetDirPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.targetDirPicker.setDefaultDirectory(startdir)
        self.targetDirPicker.setRemote(self.__remoteMode)

        if startdir:
            self.targetDirPicker.setText(startdir)
        else:
            self.targetDirPicker.setText(pro.getProjectPath())
        self.fileTypeFilter = fileTypeFilter
        self.__project = pro
        self.startdir = startdir

        if self.fileTypeFilter is not None:
            self.sourcecodeCheckBox.hide()

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def on_sourceFilesPicker_aboutToShowPathPickerDialog(self):
        """
        Private slot to perform actions before the source files selection
        dialog is shown.
        """
        targetPath = self.targetDirPicker.text()
        if not targetPath:
            targetPath = self.startdir
        self.sourceFilesPicker.setDefaultDirectory(targetPath)

        caption = (
            self.tr("Select Files")
            if self.__remoteMode
            else self.tr("Select Remote Files")
        )
        if self.fileTypeFilter is None:
            dfilter = self.__project.getFileCategoryFilterString(withAll=True)
        elif (
            self.fileTypeFilter != "OTHERS"
            and self.fileTypeFilter in self.__project.getFileCategories()
        ):
            dfilter = self.__project.getFileCategoryFilterString(
                [self.fileTypeFilter], withAll=False
            )
        elif self.fileTypeFilter == "OTHERS":
            dfilter = self.tr("All Files (*)")
        else:
            dfilter = ""
            caption = ""

        self.sourceFilesPicker.setWindowTitle(caption)
        self.sourceFilesPicker.setFilters(dfilter)

    @pyqtSlot(str)
    def on_sourceFilesPicker_textChanged(self, sfile):
        """
        Private slot to handle the source file text changed.

        If the entered source directory is a subdirectory of the current
        projects main directory, the target directory path is synchronized.
        It is assumed, that the user wants to add a bunch of files to
        the project in place.

        @param sfile the text of the source file picker
        @type str
        """
        sfile = self.sourceFilesPicker.firstStrPath()
        if sfile.startswith(self.__project.getProjectPath()):
            if self.__remoteMode:
                fsInterface = (
                    ericApp().getObject("EricServer").getServiceInterface("FileSystem")
                )
                directory = (
                    sfile if fsInterface.isdir(sfile) else fsInterface.dirname(sfile)
                )
            else:
                directory = sfile if os.path.isdir(sfile) else os.path.dirname(sfile)
            self.targetDirPicker.setText(directory)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(sfile)
        )

    def getData(self):
        """
        Public slot to retrieve the dialogs data.

        @return tuple containing the source files, the target directory and a flag
            telling, whether the files shall be added as source code
        @rtype tuple of (list of string, string, boolean)
        """
        return (
            self.sourceFilesPicker.strPaths(),
            self.targetDirPicker.text(),
            self.sourcecodeCheckBox.isChecked(),
        )
