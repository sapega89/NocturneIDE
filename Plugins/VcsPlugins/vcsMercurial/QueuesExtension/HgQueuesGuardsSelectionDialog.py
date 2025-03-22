# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select a list of guards.
"""

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QListWidgetItem,
)

from .Ui_HgQueuesGuardsSelectionDialog import Ui_HgQueuesGuardsSelectionDialog


class HgQueuesGuardsSelectionDialog(QDialog, Ui_HgQueuesGuardsSelectionDialog):
    """
    Class implementing a dialog to select a list of guards.
    """

    def __init__(self, guards, activeGuards=None, listOnly=False, parent=None):
        """
        Constructor

        @param guards list of guards to select from
        @type list of str
        @param activeGuards list of active guards
        @type list of str
        @param listOnly flag indicating to only list the guards
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        for guard in guards:
            itm = QListWidgetItem(guard, self.guardsList)
            if activeGuards is not None and guard in activeGuards:
                font = itm.font()
                font.setBold(True)
                itm.setFont(font)
        self.guardsList.sortItems()

        if listOnly:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).hide()
            self.guardsList.setSelectionMode(
                QAbstractItemView.SelectionMode.NoSelection
            )
            self.setWindowTitle(self.tr("Active Guards"))

    def getData(self):
        """
        Public method to retrieve the data.

        @return list of selected guards
        @rtype list of str
        """
        guardsList = []

        for itm in self.guardsList.selectedItems():
            guardsList.append(itm.text())

        return guardsList
