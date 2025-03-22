# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter or change the main password.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricUtilities.crypto.py3PBKDF2 import verifyPassword

from .Ui_MainPasswordEntryDialog import Ui_MainPasswordEntryDialog


class MainPasswordEntryDialog(QDialog, Ui_MainPasswordEntryDialog):
    """
    Class implementing a dialog to enter or change the main password.
    """

    def __init__(self, oldPasswordHash, parent=None):
        """
        Constructor

        @param oldPasswordHash hash of the current password
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__oldPasswordHash = oldPasswordHash
        if self.__oldPasswordHash == "":
            self.currentPasswordEdit.setEnabled(False)
            if hasattr(self.currentPasswordEdit, "setPlaceholderText"):
                self.currentPasswordEdit.setPlaceholderText(
                    self.tr("(not defined yet)")
                )

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def __updateUI(self):
        """
        Private slot to update the variable parts of the UI.
        """
        enable = True
        error = ""
        if self.currentPasswordEdit.isEnabled():
            enable = verifyPassword(
                self.currentPasswordEdit.text(), self.__oldPasswordHash
            )
            if not enable:
                error = error or self.tr("Wrong password entered.")

        if self.newPasswordEdit.text() == "":
            enable = False
            error = error or self.tr("New password must not be empty.")

        if (
            self.newPasswordEdit.text() != ""
            and self.newPasswordEdit.text() != self.newPasswordAgainEdit.text()
        ):
            enable = False
            error = error or self.tr("Repeated password is wrong.")

        if (
            self.currentPasswordEdit.isEnabled()
            and self.newPasswordEdit.text() == self.currentPasswordEdit.text()
        ):
            enable = False
            error = error or self.tr("Old and new password must not be the same.")

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)
        self.errorLabel.setText(error)

    @pyqtSlot(str)
    def on_currentPasswordEdit_textChanged(self, txt):
        """
        Private slot to handle changes of the current password.

        @param txt content of the edit widget
        @type str
        """
        self.__updateUI()

    @pyqtSlot(str)
    def on_newPasswordEdit_textChanged(self, txt):
        """
        Private slot to handle changes of the new password.

        @param txt content of the edit widget
        @type str
        """
        self.passwordMeter.checkPasswordStrength(txt)
        self.__updateUI()

    @pyqtSlot(str)
    def on_newPasswordAgainEdit_textChanged(self, txt):
        """
        Private slot to handle changes of the new again password.

        @param txt content of the edit widget
        @type str
        """
        self.__updateUI()

    def getMainPassword(self):
        """
        Public method to get the new main password.

        @return new main password
        @rtype str
        """
        return self.newPasswordEdit.text()

    def getCurrentPassword(self):
        """
        Public method to get the current main password.

        @return current main password
        @rtype str
        """
        return self.currentPasswordEdit.text()
