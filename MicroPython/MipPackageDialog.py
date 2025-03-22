# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the package data for 'mip'.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox
from semver import VersionInfo

from .MipLocalInstaller import MicroPythonPackageIndex
from .Ui_MipPackageDialog import Ui_MipPackageDialog


class MipPackageDialog(QDialog, Ui_MipPackageDialog):
    """
    Class implementing a dialog to enter the package data for 'mip'.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.indexEdit.setToolTip(
            self.tr(
                "Enter the URL of the package index. Leave empty to use the default"
                " index ({0})."
            ).format(MicroPythonPackageIndex)
        )

        self.packageEdit.textChanged.connect(self.__updateOk)
        self.versionEdit.textChanged.connect(self.__updateOk)

        self.__updateOk()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __updateOk(self):
        """
        Private slot to set the enabled state of the OK button.
        """
        enable = bool(self.packageEdit.text())
        version = self.versionEdit.text()
        if version:
            try:
                enable &= VersionInfo.is_valid(version)
            except AttributeError:
                enable &= VersionInfo.isvalid(version)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    def getData(self):
        """
        Public method to get the entered package installation data.

        @return tuple containing the package name, package version, a flag indicating
            to install the package as '.mpy ' file, the target directory on the device
            and the package index to get the package from
        @rtype tuple of (str, str, bool, str, str)
        """
        return (
            self.packageEdit.text(),
            self.versionEdit.text(),
            self.mpyCheckBox.isChecked(),
            self.targetEdit.text(),
            self.indexEdit.text(),
        )
