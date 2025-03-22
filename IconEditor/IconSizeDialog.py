# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the icon size.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_IconSizeDialog import Ui_IconSizeDialog


class IconSizeDialog(QDialog, Ui_IconSizeDialog):
    """
    Class implementing a dialog to enter the icon size.
    """

    def __init__(self, width, height, parent=None):
        """
        Constructor

        @param width width to be set
        @type int
        @param height height to be set
        @type int
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.widthSpin.setValue(width)
        self.heightSpin.setValue(height)

        self.widthSpin.selectAll()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple with width and height
        @rtype tuple of (int, int)
        """
        return self.widthSpin.value(), self.heightSpin.value()
