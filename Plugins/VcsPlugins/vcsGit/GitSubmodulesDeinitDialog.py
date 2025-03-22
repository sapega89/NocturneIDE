# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to get the data for a submodule deinit operation.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_GitSubmodulesDeinitDialog import Ui_GitSubmodulesDeinitDialog


class GitSubmodulesDeinitDialog(QDialog, Ui_GitSubmodulesDeinitDialog):
    """
    Class implementing a dialog to get the data for a submodule deinit
    operation.
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

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def __updateOK(self):
        """
        Private slot to update the state of the OK button.
        """
        enable = (
            self.allCheckBox.isChecked() or len(self.submodulesList.selectedItems()) > 0
        )
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    @pyqtSlot(bool)
    def on_allCheckBox_toggled(self, _checked):
        """
        Private slot to react on changes of the all checkbox.

        @param _checked state of the checkbox (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot()
    def on_submodulesList_itemSelectionChanged(self):
        """
        Private slot to react on changes of the submodule selection.
        """
        self.__updateOK()

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing a flag to indicate all submodules, a list of
            selected submodules and a flag indicating an enforced operation
        @rtype tuple of (bool, list of str, bool)
        """
        submodulePaths = []
        deinitAll = self.allCheckBox.isChecked()
        if not deinitAll:
            for itm in self.submodulesList.selectedItems():
                submodulePaths.append(itm.text())

        return all, submodulePaths, self.forceCheckBox.isChecked()
