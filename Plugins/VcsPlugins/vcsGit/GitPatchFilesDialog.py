# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select a list of patch files.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_GitPatchFilesDialog import Ui_GitPatchFilesDialog


class GitPatchFilesDialog(QDialog, Ui_GitPatchFilesDialog):
    """
    Class implementing a dialog to select a list of patch files.
    """

    def __init__(self, rootDir, patchCheckData, parent=None):
        """
        Constructor

        @param rootDir root of the directory tree
        @type str
        @param patchCheckData tuple of data as returned by the
            getData() method
        @type tuple of (list of str, int, bool, bool)
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__rootDir = rootDir
        if patchCheckData is not None:
            self.patchFilesList.addItems(patchCheckData[0])
            self.stripSpinBox.setValue(patchCheckData[1])
            self.eofCheckBox.setChecked(patchCheckData[2])
            self.lineCountsCheckBox.setChecked(patchCheckData[3])

        self.addButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.deleteButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.upButton.setIcon(EricPixmapCache.getIcon("1uparrow"))
        self.downButton.setIcon(EricPixmapCache.getIcon("1downarrow"))

        self.__okButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.__okButton.setEnabled(len(self.__getPatchFilesList()) > 0)

        self.deleteButton.setEnabled(False)
        self.upButton.setEnabled(False)
        self.downButton.setEnabled(False)

    @pyqtSlot()
    def on_patchFilesList_itemSelectionChanged(self):
        """
        Private slot to enable button states depending on selection.
        """
        selectedItems = self.patchFilesList.selectedItems()
        count = len(selectedItems)
        isFirst = count == 1 and self.patchFilesList.row(selectedItems[0]) == 0
        isLast = (
            count == 1
            and self.patchFilesList.row(selectedItems[0])
            == self.patchFilesList.count() - 1
        )
        self.deleteButton.setEnabled(count > 0)
        self.upButton.setEnabled(count == 1 and not isFirst)
        self.downButton.setEnabled(count == 1 and not isLast)

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add patch files to the list.
        """
        patchFiles = EricFileDialog.getOpenFileNames(
            self,
            self.tr("Patch Files"),
            self.__rootDir,
            self.tr("Patch Files (*.diff *.patch);;All Files (*)"),
        )
        if patchFiles:
            currentPatchFiles = self.__getPatchFilesList()
            for patchFile in patchFiles:
                patchFile = FileSystemUtilities.toNativeSeparators(patchFile)
                if patchFile not in currentPatchFiles:
                    self.patchFilesList.addItem(patchFile)

        self.__okButton.setEnabled(len(self.__getPatchFilesList()) > 0)
        self.on_patchFilesList_itemSelectionChanged()

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to delete the selected patch files.
        """
        for itm in self.patchFilesList.selectedItems():
            row = self.patchFilesList.row(itm)
            self.patchFilesList.takeItem(row)
            del itm

        self.__okButton.setEnabled(len(self.__getPatchFilesList()) > 0)
        self.on_patchFilesList_itemSelectionChanged()

    @pyqtSlot()
    def on_upButton_clicked(self):
        """
        Private slot to move an entry up in the list.
        """
        row = self.patchFilesList.row(self.patchFilesList.selectedItems()[0])
        itm = self.patchFilesList.takeItem(row)
        self.patchFilesList.insertItem(row - 1, itm)
        itm.setSelected(True)

    @pyqtSlot()
    def on_downButton_clicked(self):
        """
        Private slot to move an entry down in the list.
        """
        row = self.patchFilesList.row(self.patchFilesList.selectedItems()[0])
        itm = self.patchFilesList.takeItem(row)
        self.patchFilesList.insertItem(row + 1, itm)
        itm.setSelected(True)

    def __getPatchFilesList(self):
        """
        Private method to get the list of patch files.

        @return list of patch files
        @rtype list of str
        """
        patchFiles = []
        for row in range(self.patchFilesList.count()):
            itm = self.patchFilesList.item(row)
            patchFiles.append(itm.text())

        return patchFiles

    def getData(self):
        """
        Public slot to get the entered data.

        @return tuple of list of patch files, strip count, flag indicating
            that the patch has inaccurate end-of-file marker and a flag
            indicating to not trust the line count information
        @rtype tuple of (list of str, int, bool, bool)
        """
        return (
            self.__getPatchFilesList(),
            self.stripSpinBox.value(),
            self.eofCheckBox.isChecked(),
            self.lineCountsCheckBox.isChecked(),
        )
