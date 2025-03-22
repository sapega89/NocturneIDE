# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit the list of configured WebREPL URLs.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

from eric7.EricWidgets import EricMessageBox

from .MicroPythonWebreplUrlAddEditDialog import MicroPythonWebreplUrlAddEditDialog
from .Ui_MicroPythonWebreplUrlsConfigDialog import Ui_MicroPythonWebreplUrlsConfigDialog


class MicroPythonWebreplUrlsConfigDialog(
    QDialog, Ui_MicroPythonWebreplUrlsConfigDialog
):
    """
    Class implementing a dialog to edit the list of configured WebREPL URLs.
    """

    def __init__(self, webreplDict, parent=None):
        """
        Constructor

        @param webreplDict dictionary containing the configured WebREPL URLs
        @type dict
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        for name, data in webreplDict.items():
            itm = QTreeWidgetItem(
                self.webreplUrlsList,
                [name, data["description"], data["url"]],
            )
            itm.setData(0, Qt.ItemDataRole.UserRole, data["device_type"])

        self.__sortItems()
        self.__resizeColumns()
        self.__updateActionButtons()

        self.webreplUrlsList.itemSelectionChanged.connect(self.__updateActionButtons)

    @pyqtSlot()
    def __sortItems(self):
        """
        Private slot to sort the list by name column (i.e. column 0).
        """
        self.webreplUrlsList.sortItems(0, Qt.SortOrder.AscendingOrder)

    @pyqtSlot()
    def __resizeColumns(self):
        """
        Private slot to resize the columns to their contents.
        """
        for column in range(self.webreplUrlsList.columnCount()):
            self.webreplUrlsList.resizeColumnToContents(column)

    @pyqtSlot()
    def __updateActionButtons(self):
        """
        Private slot to change the enabled state of the action buttons.
        """
        selectedItemsCount = len(self.webreplUrlsList.selectedItems())
        self.editButton.setEnabled(selectedItemsCount == 1)
        self.removeButton.setEnabled(selectedItemsCount > 0)

        self.removeAllButton.setEnabled(self.webreplUrlsList.topLevelItemCount() > 0)

    def __definedNames(self):
        """
        Private method to get a list of defined connection names.

        @return list of defined connection names
        @rtype list of str
        """
        return [
            self.webreplUrlsList.topLevelItem(row).text(0)
            for row in range(self.webreplUrlsList.topLevelItemCount())
        ]

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add a new WebREPL connection.
        """
        dlg = MicroPythonWebreplUrlAddEditDialog(self.__definedNames(), parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, description, url, deviceType = dlg.getWebreplUrl()
            itm = QTreeWidgetItem(self.webreplUrlsList, [name, description, url])
            itm.setData(0, Qt.ItemDataRole.UserRole, deviceType)

            self.__sortItems()
            self.__resizeColumns()
            self.__updateActionButtons()

    @pyqtSlot()
    def on_editButton_clicked(self):
        """
        Private slot to edit the selected WebREPL connection.
        """
        itm = self.webreplUrlsList.selectedItems()[0]
        dlg = MicroPythonWebreplUrlAddEditDialog(
            self.__definedNames(),
            connectionParams=(
                itm.text(0),
                itm.text(1),
                itm.text(2),
                itm.data(0, Qt.ItemDataRole.UserRole),
            ),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, description, url, deviceType = dlg.getWebreplUrl()
            itm.setText(0, name)
            itm.setText(1, description)
            itm.setText(2, url)
            itm.setData(0, Qt.ItemDataRole.UserRole, deviceType)

            self.__sortItems()
            self.__resizeColumns()
            self.__updateActionButtons()

    @pyqtSlot()
    def on_removeButton_clicked(self):
        """
        Private slot to remove the selected entries.
        """
        ok = EricMessageBox.yesNo(
            self,
            self.tr("Remove Selected WebREPL URLs"),
            self.tr("""Shall the selected WebREPL URLs really be removed?"""),
        )
        if ok:
            for itm in self.webreplUrlsList.selectedItems():
                self.webreplUrlsList.takeTopLevelItem(
                    self.webreplUrlsList.indexOfTopLevelItem(itm)
                )
                del itm

    @pyqtSlot()
    def on_removeAllButton_clicked(self):
        """
        Private slot to remove all entries.
        """
        ok = EricMessageBox.yesNo(
            self,
            self.tr("Remove All WebREPL URLs"),
            self.tr("""Shall all WebREPL URLs really be removed?"""),
        )
        if ok:
            self.webreplUrlsList.clear()

    def getWebreplDict(self):
        """
        Public method to retrieve a dictionary containing the configured WebREPL URLs.

        @return dictionary containing the configured WebREPL URLs
        @rtype dict
        """
        webreplDict = {}
        for row in range(self.webreplUrlsList.topLevelItemCount()):
            itm = self.webreplUrlsList.topLevelItem(row)
            webreplDict[itm.text(0)] = {
                "description": itm.text(1),
                "url": itm.text(2),
                "device_type": itm.data(0, Qt.ItemDataRole.UserRole),
            }

        return webreplDict
