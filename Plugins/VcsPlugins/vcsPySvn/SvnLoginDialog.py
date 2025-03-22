# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the login dialog for pysvn.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_SvnLoginDialog import Ui_SvnLoginDialog


class SvnLoginDialog(QDialog, Ui_SvnLoginDialog):
    """
    Class implementing the login dialog for pysvn.
    """

    def __init__(self, realm, username, may_save, parent=None):
        """
        Constructor

        @param realm name of the realm of the requested credentials
        @type str
        @param username username as supplied by subversion
        @type str
        @param may_save flag indicating, that subversion is willing to save
            the answers returned
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.realmLabel.setText(
            self.tr("<b>Enter login data for realm {0}.</b>").format(realm)
        )
        self.usernameEdit.setText(username)
        self.saveCheckBox.setEnabled(may_save)
        if not may_save:
            self.saveCheckBox.setChecked(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getData(self):
        """
        Public method to retrieve the login data.

        @return tuple containing the username, the password and a flag to save the data
        @rtype tuple of (str, str, bool)
        """
        return (
            self.usernameEdit.text(),
            self.passwordEdit.text(),
            self.saveCheckBox.isChecked(),
        )
