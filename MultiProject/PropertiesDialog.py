# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the multi project properties dialog.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_PropertiesDialog import Ui_PropertiesDialog


class PropertiesDialog(QDialog, Ui_PropertiesDialog):
    """
    Class implementing the multi project properties dialog.
    """

    def __init__(self, multiProject, new=True, parent=None):
        """
        Constructor

        @param multiProject reference to the multi project object
        @type MultiProject
        @param new flag indicating the generation of a new multi project
            (defaults to True)
        @type bool (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.multiProject = multiProject
        self.newMultiProject = new

        if not new:
            self.descriptionEdit.setPlainText(self.multiProject.description)

    def storeData(self):
        """
        Public method to store the entered/modified data.
        """
        self.multiProject.description = self.descriptionEdit.toPlainText()
