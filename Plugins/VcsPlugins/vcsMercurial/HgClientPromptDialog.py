# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a prompt dialog for the Mercurial command server.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QTextCursor
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit

from .Ui_HgClientPromptDialog import Ui_HgClientPromptDialog


class HgClientPromptDialog(QDialog, Ui_HgClientPromptDialog):
    """
    Class implementing a prompt dialog for the Mercurial command server.
    """

    def __init__(self, size, message, parent=None):
        """
        Constructor

        @param size maximum length of the requested input
        @type int
        @param message message sent by the server
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.inputEdit.setMaxLength(size)
        self.messageEdit.setPlainText(message)

        tc = self.messageEdit.textCursor()
        tc.movePosition(QTextCursor.MoveOperation.End)
        self.messageEdit.setTextCursor(tc)
        self.messageEdit.ensureCursorVisible()

        self.inputEdit.setFocus(Qt.FocusReason.OtherFocusReason)

    @pyqtSlot(str)
    def on_inputEdit_textChanged(self, txt):
        """
        Private slot to handle changes of the user input.

        @param txt text entered by the user
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(bool(txt))

    @pyqtSlot(bool)
    def on_passwordCheckBox_toggled(self, isOn):
        """
        Private slot to handle the password checkbox toggled.

        @param isOn flag indicating the status of the check box
        @type bool
        """
        if isOn:
            self.inputEdit.setEchoMode(QLineEdit.EchoMode.Password)
        else:
            self.inputEdit.setEchoMode(QLineEdit.EchoMode.Normal)

    def getInput(self):
        """
        Public method to get the user input.

        @return user input
        @rtype str
        """
        return self.inputEdit.text()

    def isPassword(self):
        """
        Public method to check, if the input was a password.

        @return flag indicating a password
        @rtype bool
        """
        return self.passwordCheckBox.isChecked()
