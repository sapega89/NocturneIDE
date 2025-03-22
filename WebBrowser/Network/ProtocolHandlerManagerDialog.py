# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to manage registered protocol handlers.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

from .Ui_ProtocolHandlerManagerDialog import Ui_ProtocolHandlerManagerDialog


class ProtocolHandlerManagerDialog(QDialog, Ui_ProtocolHandlerManagerDialog):
    """
    Class implementing a dialog to manage registered protocol handlers.
    """

    def __init__(self, manager, parent=None):
        """
        Constructor

        @param manager reference to the protocol handlers manager object
        @type ProtocolHandlerManager
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        self.__manager = manager
        handlers = self.__manager.protocolHandlers()
        for scheme in sorted(handlers):
            QTreeWidgetItem(
                self.protocolHandlersList, [scheme, handlers[scheme].toString()]
            )

        self.on_protocolHandlersList_itemSelectionChanged()

    @pyqtSlot()
    def on_protocolHandlersList_itemSelectionChanged(self):
        """
        Private slot handling a change of the selection.
        """
        self.deleteButton.setEnabled(
            len(self.protocolHandlersList.selectedItems()) == 1
        )

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to delete the selected protocol handler.
        """
        itm = self.protocolHandlersList.selectedItems()[0]
        self.__manager.removeProtocolHandler(itm.text(0))

        self.protocolHandlersList.takeTopLevelItem(
            self.protocolHandlersList.indexOfTopLevelItem(itm)
        )
        del itm
