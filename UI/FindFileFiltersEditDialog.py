# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to configure the file filters.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.QScintilla import Lexers

from .FindFileFilterPropertiesDialog import FindFileFilterPropertiesDialog
from .Ui_FindFileFiltersEditDialog import Ui_FindFileFiltersEditDialog


class FindFileFiltersEditDialog(QDialog, Ui_FindFileFiltersEditDialog):
    """
    Class implementing a dialog to configure the file filters.
    """

    FilterTextRole = Qt.ItemDataRole.UserRole
    FilterPatternRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, filters, parent=None):
        """
        Constructor

        @param filters dictionary with the filter name as key and a list of
            file name patterns as value
        @type dict
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.fileFiltersList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        self.__populateFilters(filters)

    def __populateFilters(self, filters):
        """
        Private method to populate the filters list.

        @param filters dictionary containing the existing file filters
        @type dict
        """
        self.fileFiltersList.clear()

        for name in sorted(filters):
            QTreeWidgetItem(self.fileFiltersList, [name, " ".join(filters[name])])

        self.__adjustColumns()

    def __adjustColumns(self):
        """
        Private method to adjust the column widths.
        """
        self.fileFiltersList.resizeColumnToContents(0)
        self.fileFiltersList.resizeColumnToContents(1)

    @pyqtSlot()
    def on_fileFiltersList_itemSelectionChanged(self):
        """
        Private slot to handle a change of the selected items.
        """
        selectedItemsLength = len(self.fileFiltersList.selectedItems())
        self.editFileFilterButton.setEnabled(selectedItemsLength == 1)
        self.deleteFileFilterButton.setEnabled(selectedItemsLength > 0)

    @pyqtSlot()
    def on_addFileFilterButton_clicked(self):
        """
        Private slot to add a new filter entry.
        """
        filters = self.__getFilterNames()
        dlg = FindFileFilterPropertiesDialog(filters, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, patterns = dlg.getProperties()
            QTreeWidgetItem(self.fileFiltersList, [name, patterns])
            self.__adjustColumns()

    @pyqtSlot()
    def on_editFileFilterButton_clicked(self):
        """
        Private slot to edit the selected filter entry..
        """
        filters = self.__getFilterNames(forEdit=True)
        selectedEntry = self.fileFiltersList.selectedItems()[0]
        dlg = FindFileFilterPropertiesDialog(
            filters,
            properties=(selectedEntry.text(0), selectedEntry.text(1)),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, patterns = dlg.getProperties()
            selectedEntry.setText(0, name)
            selectedEntry.setText(1, patterns)

    @pyqtSlot()
    def on_deleteFileFilterButton_clicked(self):
        """
        Private slot to delete the selected filter entries.
        """
        yes = EricMessageBox.yesNo(
            self,
            self.tr("Delete Selected Filters"),
            self.tr("""Shall the selected filters really be deleted?"""),
        )
        if yes:
            for itm in self.fileFiltersList.selectedItems():
                self.fileFiltersList.takeTopLevelItem(
                    self.fileFiltersList.indexOfTopLevelItem(itm)
                )
                del itm

    @pyqtSlot()
    def on_defaultFiltersButton_clicked(self):
        """
        Private slot to create the default list of file filters.
        """
        if self.fileFiltersList.topLevelItemCount():
            ok = EricMessageBox.yesNo(
                self,
                self.tr("Default Filters"),
                self.tr(
                    "Do you really want to clear the list of defined file filters and"
                    " replace it with the list of default filters?"
                ),
            )
            if not ok:
                return

        openFileFiltersList = (
            Lexers.getOpenFileFiltersList(False, withAdditional=False)
            + Preferences.getEditor("AdditionalOpenFilters")[:]
        )

        filters = {}
        for openFileFilter in openFileFiltersList:
            name, pattern = openFileFilter.strip().rstrip(")").split(" (", 1)
            patterns = pattern.strip().split()
            filters[name.strip()] = patterns

        self.__populateFilters(filters)

    def __getFilterNames(self, forEdit=False):
        """
        Private method to get the list of defined filter names.

        @param forEdit flag indicating a list for an edit operation
            (defaults to False)
        @type bool (optional)
        @return list of defined filter names
        @rtype list of str
        """
        selectedItems = self.fileFiltersList.selectedItems() if forEdit else []

        filters = []
        for row in range(self.fileFiltersList.topLevelItemCount()):
            itm = self.fileFiltersList.topLevelItem(row)
            if itm not in selectedItems:
                filters.append(itm.text(0))

        return filters

    def getFilters(self):
        """
        Public method to retrieve the edited filter list.

        @return dictionary containing the defined file filters with the
            filter name as key and a list of file name patterns as value
        @rtype dict
        """
        filters = {}
        for row in range(self.fileFiltersList.topLevelItemCount()):
            itm = self.fileFiltersList.topLevelItem(row)
            filters[itm.text(0)] = itm.text(1).split()

        return filters
