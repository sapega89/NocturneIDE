# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data of a remote repository.
"""

from PyQt6.QtCore import QUrl, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_GitAddRemoteDialog import Ui_GitAddRemoteDialog


class GitAddRemoteDialog(QDialog, Ui_GitAddRemoteDialog):
    """
    Class implementing a dialog to enter the data of a remote repository.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__updateOK()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateOK(self):
        """
        Private method to update the status of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self.nameEdit.text() != "" and self.urlEdit.text() != ""
        )

    @pyqtSlot(str)
    def on_nameEdit_textChanged(self, txt):
        """
        Private slot handling changes of the entered name.

        @param txt current text
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_urlEdit_textChanged(self, txt):
        """
        Private slot handling changes of the entered URL.

        @param txt current text
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_userEdit_textChanged(self, txt):
        """
        Private slot handling changes of the entered user name.

        @param txt current text
        @type str
        """
        self.passwordEdit.setEnabled(bool(txt))

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple with name and URL of the remote repository
        @rtype tuple of (str, str)
        """
        url = QUrl.fromUserInput(self.urlEdit.text())
        userName = self.userEdit.text()
        if userName:
            url.setUserName(userName)
            password = self.passwordEdit.text()
            if password:
                url.setPassword(password)

        return self.nameEdit.text(), url.toString()
