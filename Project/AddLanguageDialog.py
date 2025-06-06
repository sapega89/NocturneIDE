# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to add a new language to the project.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_AddLanguageDialog import Ui_AddLanguageDialog


class AddLanguageDialog(QDialog, Ui_AddLanguageDialog):
    """
    Class implementing a dialog to add a new language to the project.
    """

    def __init__(self, parent=None, name=None):
        """
        Constructor

        @param parent parent widget of this dialog
        @type QWidget
        @param name name of this dialog
        @type str
        """
        super().__init__(parent)
        if name:
            self.setObjectName(name)
        self.setupUi(self)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getSelectedLanguage(self):
        """
        Public method to retrieve the selected language.

        @return the selected language
        @rtype str
        """
        return self.languageCombo.currentText()
