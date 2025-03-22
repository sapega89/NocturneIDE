# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing specialized tree views.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeView


class EricTreeView(QTreeView):
    """
    Class implementing a tree view supporting removal of entries.
    """

    def keyPressEvent(self, evt):
        """
        Protected method implementing special key handling.

        @param evt reference to the event
        @type QKeyEvent
        """
        if (
            evt.key() in [Qt.Key.Key_Delete, Qt.Key.Key_Backspace]
            and self.model() is not None
        ):
            self.removeSelected()
            evt.setAccepted(True)
        else:
            super().keyPressEvent(evt)

    def removeSelected(self):
        """
        Public method to remove the selected entries.
        """
        if (
            self.model() is None
            or self.selectionModel() is None
            or not self.selectionModel().hasSelection()
        ):
            # no models available or nothing selected
            return

        selectedRows = self.selectionModel().selectedRows()
        for idx in sorted(selectedRows, reverse=True):
            self.model().removeRow(idx.row(), idx.parent())

    def removeAll(self):
        """
        Public method to clear the view.
        """
        if self.model() is not None:
            self.model().removeRows(
                0, self.model().rowCount(self.rootIndex()), self.rootIndex()
            )
