# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for applying a bundle.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_GitApplyBundleDataDialog import Ui_GitApplyBundleDataDialog


class GitApplyBundleDataDialog(QDialog, Ui_GitApplyBundleDataDialog):
    """
    Class implementing a dialog to enter the data for applying a bundle.
    """

    def __init__(self, bundleHeads, branches, parent=None):
        """
        Constructor

        @param bundleHeads list of heads contained in a bundle
        @type list of str
        @param branches list of available branch names
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.headCombo.addItems(sorted(bundleHeads))
        self.branchCombo.addItems([""] + sorted(branches))

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple with the bundle head (string) and the local branch name
        @rtype str
        """
        return self.headCombo.currentText(), self.branchCombo.currentText()
