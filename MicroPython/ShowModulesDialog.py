# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the available modules of all bundles.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem

from eric7.EricGui import EricPixmapCache

from .Ui_ShowModulesDialog import Ui_ShowModulesDialog


class ShowModulesDialog(QDialog, Ui_ShowModulesDialog):
    """
    Class implementing a dialog to show the available modules of all bundles.
    """

    def __init__(self, modulesList, selectionMode=False, info="", parent=None):
        """
        Constructor

        @param modulesList list of module names to be shown
        @type list of str
        @param selectionMode flag indicating the activation of the selection mode
            (defaults to False)
        @type bool (optional)
        @param info string containing some informational data (defaults to "")
        @type str (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.filterButton.setIcon(EricPixmapCache.getIcon("check"))
        self.filterButton.clicked.connect(self.__applyFilter)
        self.filterEdit.returnPressed.connect(self.__applyFilter)

        self.__checkCount = 0
        self.__selectionMode = selectionMode
        if self.__selectionMode:
            self.buttonBox.setStandardButtons(
                QDialogButtonBox.StandardButton.Ok
                | QDialogButtonBox.StandardButton.Cancel
            )
        else:
            self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Close)

        if self.__selectionMode:
            for moduleName in modulesList:
                itm = QListWidgetItem(moduleName)
                itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                itm.setCheckState(Qt.CheckState.Unchecked)
                self.modulesList.addItem(itm)
        else:
            self.modulesList.addItems(modulesList)
        self.modulesList.sortItems(Qt.SortOrder.AscendingOrder)

        if info:
            self.infoLabel.setText(info)
        else:
            self.infoLabel.hide()

        self.__applyFilter()

        self.__checkCountUpdated()

    @pyqtSlot()
    def __applyFilter(self):
        """
        Private slot to apply the filter to the list of available modules.
        """
        filterStr = self.filterEdit.text()
        counter = 0
        for row in range(self.modulesList.count()):
            itm = self.modulesList.item(row)
            visible = filterStr in itm.text() if filterStr else True
            itm.setHidden(not visible)
            if visible:
                counter += 1

        self.statusLabel.setText(
            self.tr("Showing {0} of {1} modules/packages").format(
                counter, self.modulesList.count()
            )
        )
        self.filterEdit.selectAll()
        self.filterEdit.setFocus(Qt.FocusReason.OtherFocusReason)

    @pyqtSlot(QListWidgetItem)
    def on_modulesList_itemChanged(self, item):
        """
        Private slot to handle a change of the check state of an item.

        @param item reference to the changed item
        @type QTreeWidgetItem
        """
        if self.__selectionMode:
            if item.checkState() == Qt.CheckState.Checked:
                self.__checkCount += 1
            elif self.__checkCount > 0:
                self.__checkCount -= 1

            self.__checkCountUpdated()

    def __checkCountUpdated(self):
        """
        Private method to handle an update of the check count.
        """
        if self.__selectionMode:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                self.__checkCount > 0
            )

    def getSelection(self):
        """
        Public method to get the list of selected modules.

        @return list of selected modules
        @rtype circup.module.Module
        """
        results = []
        if self.__selectionMode:
            for row in range(self.modulesList.count()):
                itm = self.modulesList.item(row)
                if itm.checkState() == Qt.CheckState.Checked:
                    results.append(itm.text())

        return results
