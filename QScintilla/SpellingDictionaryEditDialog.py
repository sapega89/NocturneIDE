# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit the various spell checking dictionaries.
"""

import os

from PyQt6.QtCore import QSortFilterProxyModel, QStringListModel, Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog

from .Ui_SpellingDictionaryEditDialog import Ui_SpellingDictionaryEditDialog


class SpellingDictionaryEditDialog(QDialog, Ui_SpellingDictionaryEditDialog):
    """
    Class implementing a dialog to edit the various spell checking
    dictionaries.
    """

    def __init__(self, data, info, parent=None):
        """
        Constructor

        @param data contents to be edited
        @type str
        @param info info string to show at the header
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.infoLabel.setText(info)

        self.__model = QStringListModel(
            [line.strip() for line in data.splitlines() if line.strip()], self
        )
        self.__model.sort(0)
        self.__proxyModel = QSortFilterProxyModel(self)
        self.__proxyModel.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.__proxyModel.setDynamicSortFilter(True)
        self.__proxyModel.setSourceModel(self.__model)
        self.wordList.setModel(self.__proxyModel)

        self.searchEdit.textChanged.connect(self.__proxyModel.setFilterFixedString)

        self.removeButton.clicked.connect(self.wordList.removeSelected)
        self.removeAllButton.clicked.connect(self.wordList.removeAll)

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to handle adding an entry.
        """
        self.__model.insertRow(self.__model.rowCount())
        self.wordList.edit(self.__proxyModel.index(self.__model.rowCount() - 1, 0))

    def getData(self):
        """
        Public method to get the data.

        @return data of the dialog
        @rtype str
        """
        return (
            os.linesep.join(
                [line.strip() for line in self.__model.stringList() if line.strip()]
            )
            + os.linesep
        )
