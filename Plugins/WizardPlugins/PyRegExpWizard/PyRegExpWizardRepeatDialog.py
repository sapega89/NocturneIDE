# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog for entering repeat counts.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog

from .Ui_PyRegExpWizardRepeatDialog import Ui_PyRegExpWizardRepeatDialog


class PyRegExpWizardRepeatDialog(QDialog, Ui_PyRegExpWizardRepeatDialog):
    """
    Class implementing a dialog for entering repeat counts.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.unlimitedButton.setChecked(True)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(int)
    def on_lowerSpin_valueChanged(self, value):
        """
        Private slot to handle the lowerSpin valueChanged signal.

        @param value value of the spinbox
        @type int
        """
        if self.upperSpin.value() < value:
            self.upperSpin.setValue(value)

    @pyqtSlot(int)
    def on_upperSpin_valueChanged(self, value):
        """
        Private slot to handle the upperSpin valueChanged signal.

        @param value value of the spinbox
        @type int
        """
        if self.lowerSpin.value() > value:
            self.lowerSpin.setValue(value)

    def getRepeat(self):
        """
        Public method to retrieve the dialog's result.

        @return ready formatted repeat string
        @rtype str
        """
        minimal = "?" if self.minimalCheckBox.isChecked() else ""

        if self.unlimitedButton.isChecked():
            return "*" + minimal
        elif self.minButton.isChecked():
            reps = self.minSpin.value()
            if reps == 1:
                return "+" + minimal
            else:
                return "{{{0:d},}}{1}".format(reps, minimal)
        elif self.maxButton.isChecked():
            reps = self.maxSpin.value()
            if reps == 1:
                return "?" + minimal
            else:
                return "{{,{0:d}}}{1}".format(reps, minimal)
        elif self.exactButton.isChecked():
            reps = self.exactSpin.value()
            return "{{{0:d}}}{1}".format(reps, minimal)
        elif self.betweenButton.isChecked():
            repsMin = self.lowerSpin.value()
            repsMax = self.upperSpin.value()
            return "{{{0:d},{1:d}}}{2}".format(repsMin, repsMax, minimal)

        return ""
