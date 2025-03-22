# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select files and directories simultaneously.
"""

import pathlib

from PyQt6.QtCore import QCoreApplication, QItemSelection, pyqtSlot
from PyQt6.QtGui import QFileSystemModel
from PyQt6.QtWidgets import QFileDialog, QLineEdit, QPushButton, QTreeView


class EricDirFileDialog(QFileDialog):
    """
    Derived QFileDialog to select files and directories simultaneously.

    For this purpose the none native file dialog is used.
    """

    def __init__(self, parent=None, caption="", directory="", filterStr=""):
        """
        Constructor

        @param parent parent widget of the dialog
        @type QWidget
        @param caption window title of the dialog
        @type str
        @param directory working directory of the dialog
        @type str
        @param filterStr filter string for the dialog
        @type str
        """
        self.__selectedFilesFolders = []
        if parent is None:
            parent = QCoreApplication.instance().getMainWindow()

        super().__init__(parent, caption, directory, filterStr)
        self.setFileMode(QFileDialog.FileMode.ExistingFiles)

    @pyqtSlot()
    def exec(self):
        """
        Public slot to finalize initialization and start the event loop.

        @return accepted or rejected
        @rtype QDialog.DialogCode
        """
        self.__openBtn = self.findChildren(QPushButton)[0]
        self.__fileNameEdit = self.findChild(QLineEdit)
        self.directoryEntered.connect(self.on_directoryEntered)
        self.__tree = self.findChild(QTreeView)
        self.__tree.selectionModel().selectionChanged.connect(self.on_selectionChanged)

        return QFileDialog.exec(self)

    @pyqtSlot()
    def accept(self):
        """
        Public slot to update the list with the selected files and folders.
        """
        # Avoid to close the dialog if only return is pressed
        if not self.__openBtn.isEnabled():
            return

        self.__selectedFilesFolders = [
            x.data(QFileSystemModel.Roles.FilePathRole)
            for x in self.__tree.selectionModel().selectedIndexes()
            if x.column() == 0
        ]

        self.hide()

    @pyqtSlot(str)
    def on_directoryEntered(self, directory):
        """
        Private slot to reset selections if another directory was entered.

        @param directory name of the directory entered
        @type str
        """
        self.__tree.selectionModel().clear()
        self.__fileNameEdit.clear()
        self.__openBtn.setEnabled(False)

    @pyqtSlot(QItemSelection, QItemSelection)
    def on_selectionChanged(self, _selected, _deselected):
        """
        Private method to determine the selected files and folders and update
        the line edit.

        @param _selected newly selected entries (unused)
        @type QItemSelection
        @param _deselected deselected entries (unused)
        @type QItemSelection
        """
        selectedItems = self.__tree.selectionModel().selectedIndexes()
        if self.__tree.rootIndex() in selectedItems or selectedItems == []:
            return

        selectedFiles = [
            x.data(QFileSystemModel.Roles.FileNameRole)
            for x in selectedItems
            if x.column() == 0
        ]
        enteredFiles = self.__fileNameEdit.text().split('"')
        enteredFiles = [x.strip() for x in enteredFiles if x.strip()]

        # Check if there is a directory in the selection. Then update the
        # lineEdit.
        for selectedFile in selectedFiles:
            if selectedFile not in enteredFiles:
                txt = '" "'.join(selectedFiles)
                if len(selectedFiles) > 1:
                    txt = '"{0}"'.format(txt)
                self.__fileNameEdit.setText(txt)
                break

    @staticmethod
    def getOpenFileAndDirNames(
        parent=None, caption="", directory="", filterStr="", options=None
    ):
        """
        Static method to get the names of files and directories for opening it.

        @param parent parent widget of the dialog
        @type QWidget
        @param caption window title of the dialog
        @type str
        @param directory working directory of the dialog
        @type str
        @param filterStr filter string for the dialog
        @type str
        @param options various options for the dialog
        @type QFileDialog.Options
        @return names of the selected files and folders
        @rtype list of str
        """
        if options is None:
            options = QFileDialog.Option(0)
        options |= QFileDialog.Option.DontUseNativeDialog
        dlg = EricDirFileDialog(
            parent=parent, caption=caption, directory=directory, filterStr=filterStr
        )
        dlg.setOptions(options)
        dlg.exec()

        return dlg.__selectedFilesFolders

    @staticmethod
    def getOpenFileAndDirPaths(
        parent=None, caption="", directory="", filterStr="", options=None
    ):
        """
        Static method to get the paths of files and directories for opening it.

        @param parent parent widget of the dialog
        @type QWidget
        @param caption window title of the dialog
        @type str
        @param directory working directory of the dialog
        @type str or pathlib.Path
        @param filterStr filter string for the dialog
        @type str
        @param options various options for the dialog
        @type QFileDialog.Options
        @return paths of the selected files and folders
        @rtype list of pathlib.Path
        """
        if options is None:
            options = QFileDialog.Option(0)
        options |= QFileDialog.Option.DontUseNativeDialog
        dlg = EricDirFileDialog(
            parent=parent,
            caption=caption,
            directory=str(directory),
            filterStr=filterStr,
        )
        dlg.setOptions(options)
        dlg.exec()

        return [pathlib.Path(p) for p in dlg.__selectedFilesFolders]
