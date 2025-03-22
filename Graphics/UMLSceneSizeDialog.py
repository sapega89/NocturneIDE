# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to set the scene sizes.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_UMLSceneSizeDialog import Ui_UMLSceneSizeDialog


class UMLSceneSizeDialog(QDialog, Ui_UMLSceneSizeDialog):
    """
    Class implementing a dialog to set the scene sizes.
    """

    def __init__(self, w, h, minW, minH, parent=None, name=None):
        """
        Constructor

        @param w current width of scene
        @type int
        @param h current height of scene
        @type int
        @param minW minimum width allowed
        @type int
        @param minH minimum height allowed
        @type int
        @param parent parent widget of this dialog
        @type QWidget
        @param name name of this widget
        @type str
        """
        super().__init__(parent)
        if name:
            self.setObjectName(name)
        self.setupUi(self)

        self.widthSpinBox.setValue(w)
        self.heightSpinBox.setValue(h)
        self.widthSpinBox.setMinimum(minW)
        self.heightSpinBox.setMinimum(minH)
        self.widthSpinBox.selectAll()
        self.widthSpinBox.setFocus()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple giving the selected width and height
        @rtype tuple of (int, int)
        """
        return (self.widthSpinBox.value(), self.heightSpinBox.value())
