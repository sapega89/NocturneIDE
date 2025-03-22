# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select the applicable font dialog options.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_FontDialogOptionsDialog import Ui_FontDialogOptionsDialog


class FontDialogOptionsDialog(QDialog, Ui_FontDialogOptionsDialog):
    """
    Class implementing a dialog to select the applicable font dialog options.
    """

    def __init__(self, options, parent=None):
        """
        Constructor

        @param options dictionary with flags for the various dialog options
        @type dict
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.noNativeDialogCheckBox.setChecked(options["noNativeDialog"])
        self.scalableCheckBox.setChecked(options["scalableFonts"])
        self.nonScalableCheckBox.setChecked(options["nonScalableFonts"])
        self.monospacedCheckBox.setChecked(options["monospacedFonts"])
        self.proportionalCheckBox.setChecked(options["proportionalFonts"])

    def getOptions(self):
        """
        Public method to get the selected font dialog options.

        @return dictionary with flags for the various dialog options
        @rtype dict
        """
        return {
            "noNativeDialog": self.noNativeDialogCheckBox.isChecked(),
            "scalableFonts": self.scalableCheckBox.isChecked(),
            "nonScalableFonts": self.nonScalableCheckBox.isChecked(),
            "monospacedFonts": self.monospacedCheckBox.isChecked(),
            "proportionalFonts": self.proportionalCheckBox.isChecked(),
        }
