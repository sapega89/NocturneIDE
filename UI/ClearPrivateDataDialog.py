# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select which private data to clear.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_ClearPrivateDataDialog import Ui_ClearPrivateDataDialog


class ClearPrivateDataDialog(QDialog, Ui_ClearPrivateDataDialog):
    """
    Class implementing a dialog to select which private data to clear.
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
        Public method to get the data from the dialog.

        @return flags indicating which data to clear
            (recent files, recent projects, recent multi projects,
             debug histories, shell histories, test histories,
             VCS histories, private data of plugins)
        @rtype tuple of bool
        """
        return (
            self.filesCheckBox.isChecked(),
            self.projectsCheckBox.isChecked(),
            self.multiProjectsCheckBox.isChecked(),
            self.debugCheckBox.isChecked(),
            self.shellCheckBox.isChecked(),
            self.testCheckBox.isChecked(),
            self.vcsCheckBox.isChecked(),
            self.pluginsCheckBox.isChecked(),
        )
