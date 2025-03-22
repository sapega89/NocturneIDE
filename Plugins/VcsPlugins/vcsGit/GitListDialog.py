# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select from a list.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_GitListDialog import Ui_GitListDialog


class GitListDialog(QDialog, Ui_GitListDialog):
    """
    Class implementing a dialog to select from a list.
    """

    def __init__(self, selections, parent=None):
        """
        Constructor

        @param selections list of entries to select from
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.selectionList.addItems(selections)

    def getSelection(self):
        """
        Public method to return the selected entries.

        @return list of selected entries
        @rtype list of str
        """
        selection = []
        for itm in self.selectionList.selectedItems():
            selection.append(itm.text())

        return selection
