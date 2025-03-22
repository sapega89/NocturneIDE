# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data of a remote repository.
"""

from PyQt6.QtCore import Qt, QUrl, pyqtSlot
from PyQt6.QtWidgets import QDialog

from .Ui_GitRemoteCredentialsDialog import Ui_GitRemoteCredentialsDialog


class GitRemoteCredentialsDialog(QDialog, Ui_GitRemoteCredentialsDialog):
    """
    Class implementing a dialog to enter the data of a remote repository.
    """

    def __init__(self, remoteName, remoteUrl, parent=None):
        """
        Constructor

        @param remoteName name of the remote repository
        @type str
        @param remoteUrl URL of the remote repository
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        url = QUrl(remoteUrl)

        self.nameEdit.setText(remoteName)
        self.urlEdit.setText(url.toString(QUrl.UrlFormattingOption.RemoveUserInfo))
        self.userEdit.setText(url.userName())
        self.passwordEdit.setText(url.password())

        self.userEdit.setFocus(Qt.FocusReason.OtherFocusReason)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

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
