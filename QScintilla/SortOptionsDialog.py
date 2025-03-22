# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the sort options for a line sort.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_SortOptionsDialog import Ui_SortOptionsDialog


class SortOptionsDialog(QDialog, Ui_SortOptionsDialog):
    """
    Class implementing a dialog to enter the sort options for a line sort.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getData(self):
        """
        Public method to get the selected options.

        @return tuple of three flags indicating ascending order, alphanumeric
            sort and case sensitivity
        @rtype tuple of (bool, bool, bool)
        """
        return (
            self.ascendingButton.isChecked(),
            self.alnumButton.isChecked(),
            self.respectCaseButton.isChecked(),
        )
