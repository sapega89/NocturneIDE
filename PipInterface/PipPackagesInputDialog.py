# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter package specifications.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_PipPackagesInputDialog import Ui_PipPackagesInputDialog


class PipPackagesInputDialog(QDialog, Ui_PipPackagesInputDialog):
    """
    Class implementing a dialog to enter package specifications.
    """

    def __init__(self, title, install=True, parent=None):
        """
        Constructor

        @param title dialog title
        @type str
        @param install flag indicating an install action
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.setWindowTitle(title)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.userCheckBox.setVisible(install)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_packagesEdit_textChanged(self, txt):
        """
        Private slot handling entering package names.

        @param txt name of the requirements file
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(txt))

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple with the list of package specifications and a flag
            indicating to install to the user install directory
        @rtype tuple of (list of str, bool)
        """
        packages = [p.strip() for p in self.packagesEdit.text().split()]

        return (packages, self.userCheckBox.isChecked())
