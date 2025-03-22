# -*- coding: utf-8 -*-

# Copyright (c) 2018 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter some non-common rcc compiler options.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_RccCompilerOptionsDialog import Ui_RccCompilerOptionsDialog


class RccCompilerOptionsDialog(QDialog, Ui_RccCompilerOptionsDialog):
    """
    Class implementing a dialog to enter some non-common rcc compiler options.
    """

    def __init__(self, compilerOptions, parent=None):
        """
        Constructor

        @param compilerOptions dictionary containing the rcc compiler options
        @type dict
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.thresholdSpinBox.setValue(compilerOptions["CompressionThreshold"])
        self.compressionSpinBox.setValue(compilerOptions["CompressLevel"])
        self.disableCheckBox.setChecked(compilerOptions["CompressionDisable"])
        self.rootEdit.setText(compilerOptions["PathPrefix"])

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the compression threshold, compression level,
            flag indicating to disable compression and the resource access path
            prefix
        @rtype tuple of (int, int, bool, str)
        """
        return (
            self.thresholdSpinBox.value(),
            self.compressionSpinBox.value(),
            self.disableCheckBox.isChecked(),
            self.rootEdit.text().strip(),
        )
