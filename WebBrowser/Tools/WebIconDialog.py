# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to manage the Favicons.
"""

from PyQt6.QtCore import QPoint, Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QListWidgetItem, QMenu

from .Ui_WebIconDialog import Ui_WebIconDialog


class WebIconDialog(QDialog, Ui_WebIconDialog):
    """
    Class implementing a dialog to manage the Favicons.
    """

    def __init__(self, iconsDB, parent=None):
        """
        Constructor

        @param iconsDB icons database
        @type dict
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        for url, icon in iconsDB.items():
            QListWidgetItem(icon, url, self.iconsList)
        self.iconsList.sortItems(Qt.SortOrder.AscendingOrder)

        self.__setRemoveButtons()

    def __setRemoveButtons(self):
        """
        Private method to set the state of the 'remove' buttons.
        """
        self.removeAllButton.setEnabled(self.iconsList.count() > 0)
        self.removeButton.setEnabled(len(self.iconsList.selectedItems()) > 0)

    @pyqtSlot(QPoint)
    def on_iconsList_customContextMenuRequested(self, pos):
        """
        Private slot to show the context menu.

        @param pos cursor position
        @type QPoint
        """
        menu = QMenu()
        menu.addAction(
            self.tr("Remove Selected"), self.on_removeButton_clicked
        ).setEnabled(len(self.iconsList.selectedItems()) > 0)
        menu.addAction(
            self.tr("Remove All"), self.on_removeAllButton_clicked
        ).setEnabled(self.iconsList.count() > 0)

        menu.exec(self.iconsList.mapToGlobal(pos))

    @pyqtSlot()
    def on_iconsList_itemSelectionChanged(self):
        """
        Private slot handling the selection of entries.
        """
        self.__setRemoveButtons()

    @pyqtSlot()
    def on_removeButton_clicked(self):
        """
        Private slot to remove the selected items.
        """
        for itm in self.iconsList.selectedItems():
            row = self.iconsList.row(itm)
            self.iconsList.takeItem(row)
            del itm

    @pyqtSlot()
    def on_removeAllButton_clicked(self):
        """
        Private slot to remove all entries.
        """
        self.iconsList.clear()

    def getUrls(self):
        """
        Public method to get the list of URLs.

        @return list of URLs
        @rtype list of str
        """
        urls = []
        for row in range(self.iconsList.count()):
            urls.append(self.iconsList.item(row).text())

        return urls
