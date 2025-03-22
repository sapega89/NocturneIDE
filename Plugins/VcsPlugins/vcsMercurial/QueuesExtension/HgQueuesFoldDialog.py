# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter data to fold patches.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTreeWidgetItem

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp

from .Ui_HgQueuesFoldDialog import Ui_HgQueuesFoldDialog


class HgQueuesFoldDialog(QDialog, Ui_HgQueuesFoldDialog):
    """
    Class implementing a dialog to enter data to fold patches.
    """

    def __init__(self, patchesList, parent=None):
        """
        Constructor

        @param patchesList list of patches to select from
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.addButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.removeButton.setIcon(EricPixmapCache.getIcon("minus"))
        self.upButton.setIcon(EricPixmapCache.getIcon("1uparrow"))
        self.downButton.setIcon(EricPixmapCache.getIcon("1downarrow"))

        project = ericApp().getObject("Project")
        pwl, pel = project.getProjectDictionaries()
        language = project.getProjectSpellLanguage()
        self.messageEdit.setLanguageWithPWL(language, pwl or None, pel or None)

        for patch in patchesList:
            name, summary = patch.split("@@")
            QTreeWidgetItem(self.sourcePatches, [name, summary])

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def __updateOkButton(self):
        """
        Private slot to update the status of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self.selectedPatches.topLevelItemCount() != 0
        )

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add a patch to the list of selected patches.
        """
        row = self.sourcePatches.indexOfTopLevelItem(self.sourcePatches.currentItem())
        itm = self.sourcePatches.takeTopLevelItem(row)

        curItm = self.selectedPatches.currentItem()
        if curItm is not None:
            row = self.selectedPatches.indexOfTopLevelItem(curItm) + 1
            self.selectedPatches.insertTopLevelItem(row, itm)
        else:
            self.selectedPatches.addTopLevelItem(itm)

        self.__updateOkButton()

    @pyqtSlot()
    def on_removeButton_clicked(self):
        """
        Private slot to remove a patch from the list of selected patches.
        """
        row = self.selectedPatches.indexOfTopLevelItem(
            self.selectedPatches.currentItem()
        )
        itm = self.selectedPatches.takeTopLevelItem(row)
        self.sourcePatches.addTopLevelItem(itm)
        self.sourcePatches.sortItems(0, Qt.SortOrder.AscendingOrder)

        self.__updateOkButton()

    @pyqtSlot()
    def on_upButton_clicked(self):
        """
        Private slot to move a patch up in the list.
        """
        row = self.selectedPatches.indexOfTopLevelItem(
            self.selectedPatches.currentItem()
        )
        if row > 0:
            targetRow = row - 1
            itm = self.selectedPatches.takeTopLevelItem(row)
            self.selectedPatches.insertTopLevelItem(targetRow, itm)
            self.selectedPatches.setCurrentItem(itm)

    @pyqtSlot()
    def on_downButton_clicked(self):
        """
        Private slot to move a patch down in the list.
        """
        row = self.selectedPatches.indexOfTopLevelItem(
            self.selectedPatches.currentItem()
        )
        if row < self.selectedPatches.topLevelItemCount() - 1:
            targetRow = row + 1
            itm = self.selectedPatches.takeTopLevelItem(row)
            self.selectedPatches.insertTopLevelItem(targetRow, itm)
            self.selectedPatches.setCurrentItem(itm)

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_sourcePatches_currentItemChanged(self, current, _previous):
        """
        Private slot to react on changes of the current item of source patches.

        @param current reference to the new current item
        @type QTreeWidgetItem
        @param _previous reference to the previous current item (unused)
        @type QTreeWidgetItem
        """
        self.addButton.setEnabled(current is not None)

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_selectedPatches_currentItemChanged(self, current, _previous):
        """
        Private slot to react on changes of the current item of selected
        patches.

        @param current reference to the new current item
        @type QTreeWidgetItem
        @param _previous reference to the previous current item (unused)
        @type QTreeWidgetItem
        """
        self.removeButton.setEnabled(current is not None)

        row = self.selectedPatches.indexOfTopLevelItem(current)
        self.upButton.setEnabled(row > 0)
        self.downButton.setEnabled(row < self.selectedPatches.topLevelItemCount() - 1)

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple of commit message and list of selected patches
        @rtype tuple of (str, list of str)
        """
        patchesList = []
        for row in range(self.selectedPatches.topLevelItemCount()):
            patchesList.append(self.selectedPatches.topLevelItem(row).text(0))

        return self.messageEdit.toPlainText(), patchesList
