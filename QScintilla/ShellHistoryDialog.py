# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the shell history dialog.
"""

import os

from PyQt6.QtCore import QItemSelectionModel, Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QListWidgetItem

from .Ui_ShellHistoryDialog import Ui_ShellHistoryDialog


class ShellHistoryDialog(QDialog, Ui_ShellHistoryDialog):
    """
    Class implementing the shell history dialog.
    """

    def __init__(self, history, vm, shell):
        """
        Constructor

        @param history reference to the current shell history
        @type list of str
        @param vm reference to the viewmanager object
        @type ViewManager
        @param shell reference to the shell object
        @type Shell
        """
        super().__init__(shell)
        self.setupUi(self)

        self.__vm = vm
        self.__shell = shell

        self.historyList.addItems(history)
        index = shell.getHistoryIndex()
        if index < 0 or index >= len(history):
            self.historyList.setCurrentRow(
                self.historyList.count() - 1, QItemSelectionModel.SelectionFlag.Select
            )
        else:
            self.historyList.setCurrentRow(
                index, QItemSelectionModel.SelectionFlag.Select
            )
        self.historyList.scrollToItem(self.historyList.currentItem())

    @pyqtSlot()
    def on_historyList_itemSelectionChanged(self):
        """
        Private slot to handle a change of the selection.
        """
        selected = len(self.historyList.selectedItems()) > 0
        self.copyButton.setEnabled(selected and self.__vm.activeWindow() is not None)
        self.deleteButton.setEnabled(selected)
        self.executeButton.setEnabled(selected)

    @pyqtSlot(QListWidgetItem)
    def on_historyList_itemDoubleClicked(self, item):
        """
        Private slot to handle a double click of an item.

        @param item reference to the item that was double clicked
        @type QListWidgetItem
        """
        self.on_executeButton_clicked()

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to delete the selected entries from the history.
        """
        for itm in self.historyList.selectedItems():
            ditm = self.historyList.takeItem(self.historyList.row(itm))
            del ditm
        self.historyList.scrollToItem(self.historyList.currentItem())
        self.historyList.setFocus()

    @pyqtSlot()
    def on_copyButton_clicked(self):
        """
        Private slot to copy the selected entries to the current editor.
        """
        aw = self.__vm.activeWindow()
        if aw is not None:
            lines = []
            for index in range(self.historyList.count()):
                # selectedItems() doesn't seem to preserve the order
                itm = self.historyList.item(index)
                if itm.isSelected():
                    lines.append(itm.text())
            eol = aw.getLineSeparator()
            txt = eol.join(lines) + eol
            aw.insert(txt)
        self.historyList.setFocus()

    @pyqtSlot()
    def on_executeButton_clicked(self):
        """
        Private slot to execute the selected entries in the shell.
        """
        lines = []
        for index in range(self.historyList.count()):
            # selectedItems() doesn't seem to preserve the order
            itm = self.historyList.item(index)
            if itm.isSelected():
                lines.append(itm.text())
        cmds = os.linesep.join(lines) + os.linesep
        self.__shell.executeLines(cmds, historyIndex=self.historyList.currentRow())

        # reload the list because shell modified it
        self.on_reloadButton_clicked()

    @pyqtSlot()
    def on_reloadButton_clicked(self):
        """
        Private slot to reload the history.
        """
        history = self.__shell.getHistory(None)
        index = self.__shell.getHistoryIndex()

        self.historyList.clear()
        self.historyList.addItems(history)
        if index < 0 or index >= len(history):
            self.historyList.setCurrentRow(
                self.historyList.count() - 1, QItemSelectionModel.SelectionFlag.Select
            )
        else:
            self.historyList.setCurrentRow(
                index, QItemSelectionModel.SelectionFlag.Select
            )
        self.historyList.scrollToItem(self.historyList.currentItem())

        self.historyList.setFocus(Qt.FocusReason.OtherFocusReason)

    def getHistory(self):
        """
        Public method to retrieve the history from the dialog.

        @return tuple containing the list of history entries and the
            current row
        @rtype tuple of (list of str, int)
        """
        history = []
        for index in range(self.historyList.count()):
            history.append(self.historyList.item(index).text())
        return history, self.historyList.currentRow()
