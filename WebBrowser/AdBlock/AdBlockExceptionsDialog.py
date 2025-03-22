# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to configure the AdBlock exceptions.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7.EricGui import EricPixmapCache
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .Ui_AdBlockExceptionsDialog import Ui_AdBlockExceptionsDialog


class AdBlockExceptionsDialog(QDialog, Ui_AdBlockExceptionsDialog):
    """
    Class implementing a dialog to configure the AdBlock exceptions.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.iconLabel.setPixmap(EricPixmapCache.getPixmap("adBlockPlusGreen48"))

        self.buttonBox.setFocus()

    def load(self, hosts):
        """
        Public slot to load the list of excepted hosts.

        @param hosts list of excepted hosts
        @type list of str
        """
        self.hostList.clear()
        self.hostList.addItems(hosts)

    @pyqtSlot(str)
    def on_hostEdit_textChanged(self, txt):
        """
        Private slot to handle changes of the host edit.

        @param txt text of the edit
        @type str
        """
        self.addButton.setEnabled(bool(txt))

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to handle a click of the add button.
        """
        self.hostList.addItem(self.hostEdit.text())
        self.hostEdit.clear()

    @pyqtSlot()
    def on_hostList_itemSelectionChanged(self):
        """
        Private slot handling a change of the number of selected items.
        """
        self.deleteButton.setEnabled(len(self.hostList.selectedItems()) > 0)

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot handling a click of the delete button.
        """
        for itm in self.hostList.selectedItems():
            row = self.hostList.row(itm)
            removedItem = self.hostList.takeItem(row)
            del removedItem

    def accept(self):
        """
        Public slot handling the acceptance of the dialog.
        """
        hosts = []
        for row in range(self.hostList.count()):
            hosts.append(self.hostList.item(row).text())

        WebBrowserWindow.adBlockManager().setExceptions(hosts)

        super().accept()
