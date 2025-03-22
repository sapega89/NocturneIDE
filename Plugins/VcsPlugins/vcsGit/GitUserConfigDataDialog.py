# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter some user data.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_GitUserConfigDataDialog import Ui_GitUserConfigDataDialog


class GitUserConfigDataDialog(QDialog, Ui_GitUserConfigDataDialog):
    """
    Class implementing a dialog to enter some user data.
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
        Public method to retrieve the entered data.

        @return tuple with user's first name, last name and email address
        @rtype tuple of (str, str, str)
        """
        return (
            self.firstNameEdit.text(),
            self.lastNameEdit.text(),
            self.emailEdit.text(),
        )
