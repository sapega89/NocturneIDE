# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select from a list of strings.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QListWidgetItem,
)

from .Ui_EricListSelectionDialog import Ui_EricListSelectionDialog


class EricListSelectionDialog(QDialog, Ui_EricListSelectionDialog):
    """
    Class implementing a dialog to select from a list of strings.
    """

    def __init__(
        self,
        entries,
        selectionMode=QAbstractItemView.SelectionMode.ExtendedSelection,
        title="",
        message="",
        checkBoxSelection=False,
        doubleClickOk=False,
        emptySelectionOk=False,
        showSelectAll=False,
        parent=None,
    ):
        """
        Constructor

        @param entries list of entries to select from
        @type list of str or list of tuple of (str, Any)
        @param selectionMode selection mode for the list
        @type QAbstractItemView.SelectionMode
        @param title title of the dialog
        @type str
        @param message message to be show in the dialog
        @type str
        @param checkBoxSelection flag indicating to select items via their
            checkbox
        @type bool
        @param doubleClickOk flag indicating to accept the dialog upon a
            double click of an item (single selection only)
        @type bool
        @param emptySelectionOk flag indicating that an empty selection is allowed
        @type bool
        @param showSelectAll flag indicating to show a 'Select All' button
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        if title:
            self.setWindowTitle(title)
        if message:
            self.messageLabel.setText(message)

        self.__checkCount = 0
        self.__isCheckBoxSelection = checkBoxSelection
        self.__doubleClickOk = doubleClickOk
        self.__emptySelectionOk = emptySelectionOk

        self.selectionList.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
            if self.__isCheckBoxSelection
            else selectionMode
        )

        for entry in entries:
            if isinstance(entry, tuple):
                itm = QListWidgetItem(entry[0])
                itm.setData(Qt.ItemDataRole.UserRole, entry[1])
            else:
                itm = QListWidgetItem(entry)
            if self.__isCheckBoxSelection:
                itm.setFlags(
                    Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
                )
                itm.setCheckState(Qt.CheckState.Unchecked)
            self.selectionList.addItem(itm)

        if showSelectAll:
            self.buttonBox.addButton(
                self.tr("Deselect All"), QDialogButtonBox.ButtonRole.ActionRole
            ).clicked.connect(lambda: self.__selectAll(False))
            self.buttonBox.addButton(
                self.tr("Select All"), QDialogButtonBox.ButtonRole.ActionRole
            ).clicked.connect(lambda: self.__selectAll(True))

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            emptySelectionOk
        )

    @pyqtSlot()
    def on_selectionList_itemSelectionChanged(self):
        """
        Private slot handling a change of the selection.
        """
        if not self.__isCheckBoxSelection:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                len(self.selectionList.selectedItems()) > 0 or self.__emptySelectionOk
            )

    @pyqtSlot(QListWidgetItem)
    def on_selectionList_itemChanged(self, itm):
        """
        Private slot handling a change of an item.

        @param itm reference to the changed item
        @type QListWidgetItem
        """
        if self.__isCheckBoxSelection:
            if itm.checkState() == Qt.CheckState.Checked:
                self.__checkCount += 1
            elif self.__checkCount > 0:
                self.__checkCount -= 1
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                self.__checkCount > 0 or self.__emptySelectionOk
            )

    @pyqtSlot(QListWidgetItem)
    def on_selectionList_itemDoubleClicked(self, item):
        """
        Private slot handling double clicking an item.

        @param item double clicked item
        @type QListWidgetItem
        """
        if (
            not self.__isCheckBoxSelection
            and self.selectionList.selectionMode()
            == QAbstractItemView.SelectionMode.SingleSelection
            and self.__doubleClickOk
        ):
            self.accept()

    def __selectAll(self, state):
        """
        Private method to select or deselect all entries.

        @param state flag indicating the desired selection state
        @type bool
        """
        for row in range(self.selectionList.count()):
            item = self.selectionList.item(row)
            if self.__isCheckBoxSelection:
                if state:
                    item.setCheckState(Qt.CheckState.Checked)
                else:
                    item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setSelected(state)

    def setSelection(self, selection):
        """
        Public method to preselect a list of entries.

        @param selection list of selected entries
        @type list of str
        """
        for name in selection:
            itemList = self.selectionList.findItems(
                name, Qt.MatchFlag.MatchCaseSensitive | Qt.MatchFlag.MatchStartsWith
            )
            if itemList:
                if self.__isCheckBoxSelection:
                    itemList[0].setCheckState(Qt.CheckState.Checked)
                else:
                    itemList[0].setSelected(True)

    def getSelection(self):
        """
        Public method to retrieve the selected items.

        @return selected entries
        @rtype list of str or list of tuple of (str, Any)
        """
        entries = []
        if self.__isCheckBoxSelection:
            for row in range(self.selectionList.count()):
                item = self.selectionList.item(row)
                if item.checkState() == Qt.CheckState.Checked:
                    data = item.data(Qt.ItemDataRole.UserRole)
                    if data is None:
                        entries.append(item.text())
                    else:
                        entries.append((item.text(), data))
        else:
            for item in self.selectionList.selectedItems():
                data = item.data(Qt.ItemDataRole.UserRole)
                if data is None:
                    entries.append(item.text())
                else:
                    entries.append((item.text(), data))
        return entries
