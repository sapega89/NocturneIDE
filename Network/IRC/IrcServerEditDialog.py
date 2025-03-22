# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog for editing the IRC server configuration.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_IrcServerEditDialog import Ui_IrcServerEditDialog


class IrcServerEditDialog(QDialog, Ui_IrcServerEditDialog):
    """
    Class implementing a dialog for editing the IRC server configuration.
    """

    def __init__(self, server, parent=None):
        """
        Constructor

        @param server reference to the IRC server object
        @type IrcServer
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__okButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)

        if server:
            self.serverEdit.setText(server.getName())
            self.portSpinBox.setValue(server.getPort())
            self.passwordEdit.setText(server.getPassword())
            self.sslCheckBox.setChecked(server.useSSL())

        self.__updateOkButton()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateOkButton(self):
        """
        Private method to update the OK button state.
        """
        self.__okButton.setEnabled(self.serverEdit.text() != "")

    @pyqtSlot(str)
    def on_serverEdit_textChanged(self, _name):
        """
        Private slot handling changes of the server name.

        @param _name current name of the server (unused)
        @type str
        """
        self.__updateOkButton()

    def getServer(self):
        """
        Public method to create a server object from the data entered into
        the dialog.

        @return server object
        @rtype IrcServer
        """
        from .IrcNetworkManager import IrcServer

        server = IrcServer(self.serverEdit.text())
        server.setPort(self.portSpinBox.value())
        server.setPassword(self.passwordEdit.text())
        server.setUseSSL(self.sslCheckBox.isChecked())

        return server
