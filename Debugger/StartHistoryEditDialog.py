# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit a list of history entries.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QInputDialog, QLineEdit

from eric7.EricWidgets import EricMessageBox

from .Ui_StartHistoryEditDialog import Ui_StartHistoryEditDialog


class StartHistoryEditDialog(QDialog, Ui_StartHistoryEditDialog):
    """
    Class implementing a dialog to edit a list of history entries.
    """

    def __init__(self, history, parent=None):
        """
        Constructor

        @param history list of history entries to be edited
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.historyList.addItems(history)
        for row in range(self.historyList.count()):
            itm = self.historyList.item(row)
            flags = itm.flags() | Qt.ItemFlag.ItemIsEditable
            itm.setFlags(flags)

        self.__updateEditButtons()

    def __updateEditButtons(self):
        """
        Private method to set the state of the edit buttons.
        """
        selectedCount = len(self.historyList.selectedItems())
        self.editButton.setEnabled(selectedCount == 1)
        self.deleteButton.setEnabled(selectedCount > 0)
        self.deleteAllButton.setEnabled(self.historyList.count() > 0)

    @pyqtSlot()
    def on_historyList_itemSelectionChanged(self):
        """
        Private slot to handle the selection of entries.
        """
        self.__updateEditButtons()

    @pyqtSlot()
    def on_editButton_clicked(self):
        """
        Private slot to edit the selected entry.
        """
        itm = self.historyList.selectedItems()[0]
        historyText, ok = QInputDialog.getText(
            self,
            self.tr("Edit History Entry"),
            self.tr("Enter the new text:"),
            QLineEdit.EchoMode.Normal,
            itm.text(),
        )
        if ok:
            itm.setText(historyText)

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to delete the selected entries.
        """
        yes = EricMessageBox.yesNo(
            self,
            self.tr("Delete Selected Entries"),
            self.tr("""Do you really want to delete the selected history entries?"""),
        )
        if yes:
            for itm in self.historyList.selectedItems():
                row = self.historyList.row(itm)
                self.historyList.takeItem(row)
                del itm

    @pyqtSlot()
    def on_deleteAllButton_clicked(self):
        """
        Private slot to delete all entries.
        """
        yes = EricMessageBox.yesNo(
            self,
            self.tr("Delete All Entries"),
            self.tr("""Do you really want to delete the shown history?"""),
        )
        if yes:
            self.historyList.clear()

    def getHistory(self):
        """
        Public method to get the new list of history entries.

        @return list of history entries
        @rtype list of str
        """
        history = []
        for row in range(self.historyList.count()):
            entry = self.historyList.item(row).text()
            history.append(entry)

        return history
