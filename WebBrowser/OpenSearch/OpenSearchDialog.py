# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog for the configuration of search engines.
"""

from PyQt6.QtCore import QItemSelection, pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7.EricWidgets import EricFileDialog, EricMessageBox

from .OpenSearchEngineModel import OpenSearchEngineModel
from .Ui_OpenSearchDialog import Ui_OpenSearchDialog


class OpenSearchDialog(QDialog, Ui_OpenSearchDialog):
    """
    Class implementing a dialog for the configuration of search engines.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.setModal(True)

        self.__mw = parent

        self.__model = OpenSearchEngineModel(self.__mw.openSearchManager(), self)
        self.enginesTable.setModel(self.__model)
        self.enginesTable.horizontalHeader().resizeSection(0, 200)
        self.enginesTable.horizontalHeader().setStretchLastSection(True)
        self.enginesTable.verticalHeader().hide()
        self.enginesTable.verticalHeader().setDefaultSectionSize(
            int(1.2 * self.fontMetrics().height())
        )

        self.enginesTable.selectionModel().selectionChanged.connect(
            self.__selectionChanged
        )
        self.editButton.setEnabled(False)

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add a new search engine.
        """
        fileNames = EricFileDialog.getOpenFileNames(
            self,
            self.tr("Add search engine"),
            "",
            self.tr("OpenSearch (*.xml);;All Files (*)"),
        )

        osm = self.__mw.openSearchManager()
        for fileName in fileNames:
            if not osm.addEngine(fileName):
                EricMessageBox.critical(
                    self,
                    self.tr("Add search engine"),
                    self.tr(
                        """{0} is not a valid OpenSearch 1.1 description or"""
                        """ is already on your list."""
                    ).format(fileName),
                )

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to delete the selected search engines.
        """
        if self.enginesTable.model().rowCount() == 1:
            EricMessageBox.critical(
                self,
                self.tr("Delete selected engines"),
                self.tr("""You must have at least one search engine."""),
            )

        self.enginesTable.removeSelected()

    @pyqtSlot()
    def on_restoreButton_clicked(self):
        """
        Private slot to restore the default search engines.
        """
        self.__mw.openSearchManager().restoreDefaults()

    @pyqtSlot()
    def on_editButton_clicked(self):
        """
        Private slot to edit the data of the current search engine.
        """
        from .OpenSearchEditDialog import OpenSearchEditDialog

        rows = self.enginesTable.selectionModel().selectedRows()
        row = (
            self.enginesTable.selectionModel().currentIndex().row()
            if len(rows) == 0
            else rows[0].row()
        )

        osm = self.__mw.openSearchManager()
        engineName = osm.allEnginesNames()[row]
        engine = osm.engine(engineName)
        dlg = OpenSearchEditDialog(engine, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            osm.enginesChanged()

    @pyqtSlot(QItemSelection, QItemSelection)
    def __selectionChanged(self, _selected, _deselected):
        """
        Private slot to handle a change of the selection.

        @param _selected item selection of selected items (unused)
        @type QItemSelection
        @param _deselected item selection of deselected items (unused)
        @type QItemSelection
        """
        self.editButton.setEnabled(
            len(self.enginesTable.selectionModel().selectedRows()) <= 1
        )
