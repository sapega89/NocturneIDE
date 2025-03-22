# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to add a sub-repository.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_HgAddSubrepositoryDialog import Ui_HgAddSubrepositoryDialog


class HgAddSubrepositoryDialog(QDialog, Ui_HgAddSubrepositoryDialog):
    """
    Class implementing a dialog to add a sub-repository.
    """

    def __init__(self, projectPath, parent=None):
        """
        Constructor

        @param projectPath project directory name
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.pathPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.pathPicker.setDefaultDirectory(projectPath)

        self.__ok = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.__ok.setEnabled(False)

        self.__projectPath = FileSystemUtilities.toNativeSeparators(projectPath)

        self.typeCombo.addItem("Mercurial", "hg")
        self.typeCombo.addItem("GIT", "git")
        self.typeCombo.addItem("Subversion", "svn")

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateOk(self):
        """
        Private slot to update the state of the OK button.
        """
        path = self.pathPicker.text()
        url = self.urlEdit.text()

        self.__ok.setEnabled(path != "" and not os.path.isabs(path) and url != "")

    @pyqtSlot(str)
    def on_pathPicker_textChanged(self, _txt):
        """
        Private slot to handle the update of the path.

        @param _txt text of the path edit (unused)
        @type str
        """
        self.__updateOk()

    @pyqtSlot(str)
    def on_urlEdit_textChanged(self, _txt):
        """
        Private slot to handle the update of the URL.

        @param _txt text of the URL edit (unused)
        @type str
        """
        self.__updateOk()

    @pyqtSlot(str)
    def on_pathPicker_pathSelected(self, path):
        """
        Private slot handling the selection of a subrepository path.

        @param path path of the subrepository
        @type str
        """
        if path.startswith(self.__projectPath + os.sep):
            path = path.replace(self.__projectPath + os.sep, "")
            self.pathPicker.setText(path)
        else:
            EricMessageBox.critical(
                self,
                self.tr("Add Sub-repository"),
                self.tr("""The sub-repository path must be inside the project."""),
            )
            self.pathPicker.setText("")

    def getData(self):
        """
        Public method to get the data.

        @return tuple containing the relative path within the project, the
            sub-repository type and the sub-repository URL
        @rtype tuple of (str, str, str)
        """
        return (
            self.pathPicker.text(),
            self.typeCombo.itemData(self.typeCombo.currentIndex()),
            self.urlEdit.text(),
        )
