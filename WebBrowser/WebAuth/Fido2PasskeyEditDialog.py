# -*- coding: utf-8 -*-
# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog for editing passkey parameters.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_Fido2PasskeyEditDialog import Ui_Fido2PasskeyEditDialog


class Fido2PasskeyEditDialog(QDialog, Ui_Fido2PasskeyEditDialog):
    """
    Class implementing a dialog for editing passkey parameters.
    """

    def __init__(self, displayName, userName, relyingParty, parent=None):
        """
        Constructor

        @param displayName string to be shown for this passkey
        @type str
        @param userName user name of this passkey
        @type str
        @param relyingParty relying part this passkey belongs to
        @type str
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.displayNameEdit.textChanged.connect(self.__updateOk)
        self.userNameEdit.textChanged.connect(self.__updateOk)

        self.headerLabel.setText(
            self.tr("<b>Passkey Parameters for {0}</b>").format(relyingParty)
        )
        self.displayNameEdit.setText(displayName)
        self.userNameEdit.setText(userName)

        self.displayNameEdit.setFocus(Qt.FocusReason.OtherFocusReason)
        self.displayNameEdit.selectAll()

    @pyqtSlot()
    def __updateOk(self):
        """
        Private method to update the state of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.displayNameEdit.text()) and bool(self.userNameEdit.text())
        )

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the display and user names
        @rtype tuple[str, str]
        """
        return self.displayNameEdit.text(), self.userNameEdit.text()
