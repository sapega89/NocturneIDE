# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter submodule summary options.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_GitSubmodulesSummaryOptionsDialog import Ui_GitSubmodulesSummaryOptionsDialog


class GitSubmodulesSummaryOptionsDialog(QDialog, Ui_GitSubmodulesSummaryOptionsDialog):
    """
    Class implementing a dialog to enter submodule summary options.
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

        @return tuple containing a list of selected submodules, a flag
            indicating to show summary for the superproject index, a flag
            indicating to show summary for the submodules index, an optional
            commit ID and a value for the number of entries to be shown
        @rtype tuple of (list of str, bool, bool, str, int)
        """
        submodulePaths = []
        for itm in self.submodulesList.selectedItems():
            submodulePaths.append(itm.text())

        limit = self.limitSpinBox.value()
        if limit == 0:
            # adjust for unlimited
            limit = -1

        superProject = self.filesCheckBox.isChecked()
        if superProject:
            index = False
            commit = ""
        else:
            index = self.indexCheckBox.isChecked()
            commit = self.commitEdit.text().strip()

        return submodulePaths, superProject, index, commit, limit
