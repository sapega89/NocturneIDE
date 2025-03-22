# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter submodule synchronization options.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_GitSubmodulesSyncDialog import Ui_GitSubmodulesSyncDialog


class GitSubmodulesSyncDialog(QDialog, Ui_GitSubmodulesSyncDialog):
    """
    Class implementing a dialog to enter submodule synchronization options.
    """

    def __init__(self, submodulePaths, parent=None):
        """
        Constructor

        @param submodulePaths list of submodule paths
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.submodulesList.addItems(sorted(submodulePaths))

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing a list of selected submodules and a flag
            indicating a recursive operation
        @rtype tuple of (list of str, bool)
        """
        submodulePaths = []
        for itm in self.submodulesList.selectedItems():
            submodulePaths.append(itm.text())

        return submodulePaths, self.recursiveCheckBox.isChecked()
