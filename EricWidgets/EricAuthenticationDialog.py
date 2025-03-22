# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the authentication dialog for the help browser.
"""

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QDialog, QStyle

from .Ui_EricAuthenticationDialog import Ui_EricAuthenticationDialog


class EricAuthenticationDialog(QDialog, Ui_EricAuthenticationDialog):
    """
    Class implementing the authentication dialog for the help browser.
    """

    def __init__(self, info, username, showSave=False, saveIt=False, parent=None):
        """
        Constructor

        @param info information to be shown
        @type str
        @param username username as supplied by subversion
        @type str
        @param showSave flag to indicate to show the save checkbox
        @type bool
        @param saveIt flag indicating the value for the save checkbox
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        if parent is None:
            parent = QCoreApplication.instance().getMainWindow()

        super().__init__(parent)
        self.setupUi(self)

        self.infoLabel.setText(info)
        self.usernameEdit.setText(username)
        self.saveCheckBox.setVisible(showSave)
        self.saveCheckBox.setChecked(saveIt)

        self.iconLabel.setText("")
        self.iconLabel.setPixmap(
            self.style()
            .standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)
            .pixmap(32, 32)
        )

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def setData(self, username, password):
        """
        Public method to set the login data.

        @param username username
        @type str
        @param password password
        @type str
        """
        self.usernameEdit.setText(username)
        self.passwordEdit.setText(password)

    def getData(self):
        """
        Public method to retrieve the login data.

        @return tuple containing the user name and password
        @rtype tuple of (str, str)
        """
        return (self.usernameEdit.text(), self.passwordEdit.text())

    def shallSave(self):
        """
        Public method to check, if the login data shall be saved.

        @return flag indicating that the login data shall be saved
        @rtype bool
        """
        return self.saveCheckBox.isChecked()
