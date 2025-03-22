# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the add project dialog.
"""

import os

from PyQt6.QtCore import QUuid, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities

from .MultiProjectProjectMeta import MultiProjectProjectMeta
from .Ui_AddProjectDialog import Ui_AddProjectDialog


class AddProjectDialog(QDialog, Ui_AddProjectDialog):
    """
    Class implementing the add project dialog.
    """

    def __init__(
        self, parent=None, startdir="", project=None, categories=None, category=""
    ):
        """
        Constructor

        @param parent parent widget of this dialog
        @type QWidget
        @param startdir start directory for the selection dialog
        @type str
        @param project dictionary containing project metadata
        @type MultiProjectProjectMeta
        @param categories list of already used categories
        @type list of str
        @param category category to be preset
        @type str
        """
        super().__init__(parent)
        self.setupUi(self)

        self.filenamePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.filenamePicker.setFilters(self.tr("Project Files (*.epj)"))
        self.filenamePicker.setDefaultDirectory(
            Preferences.getMultiProject("Workspace")
        )

        if categories:
            self.categoryComboBox.addItem("")
            self.categoryComboBox.addItems(sorted(categories))
        self.categoryComboBox.setEditText(category)

        self.startdir = startdir
        self.uid = ""

        self.__okButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.__okButton.setEnabled(False)

        if project is not None:
            self.setWindowTitle(self.tr("Project Properties"))

            self.nameEdit.setText(project.name)
            self.filenamePicker.setText(project.file)
            self.descriptionEdit.setPlainText(project.description)
            self.mainCheckBox.setChecked(project.main)
            index = self.categoryComboBox.findText(project.category)
            if index == -1:
                index = 0
            self.categoryComboBox.setCurrentIndex(index)
            self.uid = project.uid

    def getProjectMetadata(self):
        """
        Public method to get the entered project metadata.

        @return project metadata iaw. the entered values
        @rtype MultiProjectProjectMeta
        """
        if not self.uid:
            # new project entry
            self.uid = QUuid.createUuid().toString()

        return MultiProjectProjectMeta(
            name=self.nameEdit.text(),
            file=self.__getFileName(),
            uid=self.uid,
            main=self.mainCheckBox.isChecked(),
            description=self.descriptionEdit.toPlainText(),
            category=self.categoryComboBox.currentText(),
        )

    def __getFileName(self):
        """
        Private method to get the file name of the project file.

        @return project file name
        @rtype str
        """
        filename = self.filenamePicker.text()
        if not os.path.isabs(filename):
            filename = FileSystemUtilities.toNativeSeparators(
                os.path.join(self.startdir, filename)
            )
        return filename

    @pyqtSlot(str)
    def on_nameEdit_textChanged(self, _txt):
        """
        Private slot called when the project name has changed.

        @param _txt text of the edit (unused)
        @type str
        """
        self.__updateUi()

    @pyqtSlot(str)
    def on_filenamePicker_textChanged(self, _txt):
        """
        Private slot called when the project filename has changed.

        @param _txt text of the edit (unused)
        @type str
        """
        self.__updateUi()

    def __updateUi(self):
        """
        Private method to update the dialog.
        """
        self.__okButton.setEnabled(
            self.nameEdit.text() != ""
            and self.filenamePicker.text() != ""
            and os.path.exists(self.__getFileName())
        )
