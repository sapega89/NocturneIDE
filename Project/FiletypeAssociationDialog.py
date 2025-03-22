# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter filetype associations for the project.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QHeaderView, QTreeWidgetItem

from .Ui_FiletypeAssociationDialog import Ui_FiletypeAssociationDialog


class FiletypeAssociationDialog(QDialog, Ui_FiletypeAssociationDialog):
    """
    Class implementing a dialog to enter filetype associations for the project.
    """

    def __init__(self, project, fileTypesDict, parent=None):
        """
        Constructor

        @param project reference to the project object
        @type Project
        @param fileTypesDict dictionary containing the file type associations
        @type dict
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.filetypeAssociationList.headerItem().setText(
            self.filetypeAssociationList.columnCount(), ""
        )
        self.filetypeAssociationList.header().setSortIndicator(
            0, Qt.SortOrder.AscendingOrder
        )

        self.filetypeCombo.addItem("", "")
        for fileCategory in sorted(project.getFileCategories()):
            self.filetypeCombo.addItem(
                project.getFileCategoryType(fileCategory), fileCategory
            )
        self.filetypeCombo.addItem(self.tr("Ignore"), "__IGNORE__")

        for pattern, filetype in fileTypesDict.items():
            try:
                self.__createItem(
                    pattern, project.getFileCategoryType(filetype), filetype
                )
            except KeyError:
                # skip entries with unknown file type
                if filetype == "__IGNORE__":
                    self.__createItem(pattern, self.tr("Ignore"), "__IGNORE__")

        self.__resort()
        self.__reformat()

    def __resort(self):
        """
        Private method to resort the tree.
        """
        self.filetypeAssociationList.sortItems(
            self.filetypeAssociationList.sortColumn(),
            self.filetypeAssociationList.header().sortIndicatorOrder(),
        )

    def __reformat(self):
        """
        Private method to reformat the tree.
        """
        self.filetypeAssociationList.header().resizeSections(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.filetypeAssociationList.header().setStretchLastSection(True)

    def __createItem(self, pattern, filetypeStr, fileCategory):
        """
        Private slot to create a new entry in the association list.

        @param pattern pattern of the entry
        @type str
        @param filetypeStr file type user string of the entry
        @type str
        @param fileCategory category of the file
        @type str
        @return reference to the newly generated entry
        @rtype QTreeWidgetItem
        """
        itm = QTreeWidgetItem(self.filetypeAssociationList, [pattern, filetypeStr])
        itm.setData(1, Qt.ItemDataRole.UserRole, fileCategory)
        return itm

    @pyqtSlot()
    def on_filetypeAssociationList_itemSelectionChanged(self):
        """
        Private slot to handle a change of the selected item.
        """
        selectedItems = self.filetypeAssociationList.selectedItems()
        if bool(selectedItems):
            self.filePatternEdit.setText(selectedItems[0].text(0))
            self.filetypeCombo.setCurrentText(selectedItems[0].text(1))
            self.deleteAssociationButton.setEnabled(True)
        else:
            self.filePatternEdit.clear()
            self.filetypeCombo.setCurrentIndex(0)
            self.deleteAssociationButton.setEnabled(False)

    @pyqtSlot()
    def on_addAssociationButton_clicked(self):
        """
        Private slot to add the association displayed to the list.
        """
        pattern = self.filePatternEdit.text()
        filetype = self.filetypeCombo.currentText()
        fileCategory = self.filetypeCombo.currentData()
        if pattern:
            items = self.filetypeAssociationList.findItems(
                pattern, Qt.MatchFlag.MatchExactly, 0
            )
            for itm in items:
                itm = self.filetypeAssociationList.takeTopLevelItem(
                    self.filetypeAssociationList.indexOfTopLevelItem(itm)
                )
                del itm
            itm = self.__createItem(pattern, filetype, fileCategory)
            self.__resort()
            self.__reformat()
            self.filePatternEdit.clear()
            self.filetypeCombo.setCurrentIndex(0)
            self.filetypeAssociationList.setCurrentItem(itm)

    @pyqtSlot()
    def on_deleteAssociationButton_clicked(self):
        """
        Private slot to delete the currently selected association of the
        listbox.
        """
        for itm in self.filetypeAssociationList.selectedItems():
            itm = self.filetypeAssociationList.takeTopLevelItem(
                self.filetypeAssociationList.indexOfTopLevelItem(itm)
            )
            del itm

            self.filetypeAssociationList.clearSelection()
            self.filePatternEdit.clear()
            self.filetypeCombo.setCurrentIndex(0)

    def on_filePatternEdit_textChanged(self, txt):
        """
        Private slot to handle the textChanged signal of the pattern lineedit.

        @param txt text of the line edit
        @type str
        """
        if not txt:
            self.deleteAssociationButton.setEnabled(False)
        else:
            if len(self.filetypeAssociationList.selectedItems()) == 0:
                self.deleteAssociationButton.setEnabled(False)
            else:
                self.deleteAssociationButton.setEnabled(
                    self.filetypeAssociationList.selectedItems()[0].text(0) == txt
                )
        self.__updateAddButton()

    @pyqtSlot(int)
    def on_filetypeCombo_currentIndexChanged(self, index):
        """
        Private slot handling the selection of a file type.

        @param index index of the selected entry
        @type int
        """
        self.__updateAddButton()

    def __updateAddButton(self):
        """
        Private method to update the enabled state of the 'add' button.
        """
        self.addAssociationButton.setEnabled(
            bool(self.filePatternEdit.text()) and bool(self.filetypeCombo.currentText())
        )

    def getData(self):
        """
        Public method to get the entered associations into.

        @return dictionary containing the defined file type associations
        @rtype dict
        """
        fileTypes = {}
        for index in range(self.filetypeAssociationList.topLevelItemCount()):
            itm = self.filetypeAssociationList.topLevelItem(index)
            fileTypes[itm.text(0)] = itm.data(1, Qt.ItemDataRole.UserRole)

        return fileTypes
