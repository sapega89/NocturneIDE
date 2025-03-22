# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter a list of worktree paths.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem

from eric7.EricWidgets import EricPathPickerDialog

from .Ui_GitWorktreePathsDialog import Ui_GitWorktreePathsDialog


class GitWorktreePathsDialog(QDialog, Ui_GitWorktreePathsDialog):
    """
    Class implementing a dialog to enter a list of worktree paths.
    """

    def __init__(self, parentDirectory, parent=None):
        """
        Constructor

        @param parentDirectory path of the worktrees parent directory
        @type str
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__parentDir = parentDirectory

        self.removeButton.setEnabled(False)

        self.__updateOK

    def __updateOK(self):
        """
        Private method to set the enabled state of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self.pathsList.count() > 0
        )

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add a path entry.
        """
        worktree, ok = EricPathPickerDialog.getStrPath(
            self,
            self.tr("Worktree Path"),
            self.tr("Enter new path of the worktree:"),
            mode=EricPathPickerDialog.EricPathPickerModes.DIRECTORY_MODE,
            strPath=self.__parentDir,
            defaultDirectory=self.__parentDir,
        )
        if ok and worktree:
            QListWidgetItem(worktree, self.pathsList)

            self.__updateOK()

    @pyqtSlot()
    def on_removeButton_clicked(self):
        """
        Private slot to remove the selected items.
        """
        for itm in self.pathsList.selectedItems():
            self.pathsList.takeItem(self.pathsList.row(itm))
            del itm

        self.__updateOK()

    @pyqtSlot()
    def on_removeAllButton_clicked(self):
        """
        Private slot to remove all items from the list.
        """
        self.pathsList.clear()
        self.__updateOK()

    @pyqtSlot()
    def on_pathsList_itemSelectionChanged(self):
        """
        Private slot handling a change of selected items.
        """
        self.removeButton.setEnabled(bool(self.pathsList.selectedItems()))

    def getPathsList(self):
        """
        Public method to get the entered worktree paths.

        @return list of worktree paths
        @rtype list of str
        """
        return [
            self.pathsList.item(row).text() for row in range(self.pathsList.count())
        ]
