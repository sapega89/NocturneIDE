# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit the parameters for a WebREPL connection.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Devices import getSupportedDevices
from .Ui_MicroPythonWebreplUrlAddEditDialog import Ui_MicroPythonWebreplUrlAddEditDialog


class MicroPythonWebreplUrlAddEditDialog(
    QDialog, Ui_MicroPythonWebreplUrlAddEditDialog
):
    """
    Class implementing a dialog to edit the parameters for a WebREPL connection.
    """

    def __init__(self, definedNames, connectionParams=None, parent=None):
        """
        Constructor

        @param definedNames list of already define WebREPL connection names
        @type list of str
        @param connectionParams parameters for the WebREPL connection to be edited
            (default to None)
        @type tuple of (str, str, str) (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__definedNames = definedNames[:]

        self.deviceTypeComboBox.addItem("", "")
        for board, description in sorted(getSupportedDevices(), key=lambda x: x[1]):
            self.deviceTypeComboBox.addItem(description, board)

        self.nameEdit.textChanged.connect(self.__updateOkButton)
        self.descriptionEdit.textChanged.connect(self.__updateOkButton)
        self.hostEdit.textChanged.connect(self.__updateOkButton)
        self.portEdit.textChanged.connect(self.__updateOkButton)
        self.deviceTypeComboBox.currentIndexChanged.connect(self.__updateOkButton)

        if connectionParams:
            self.__editName = connectionParams[0]
            self.__populateFields(connectionParams)
        else:
            self.__editName = ""
            self.__updateOkButton()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __populateFields(self, params):
        """
        Private method to populate the various dialog fields with the given parameters.

        @param params arameters for the WebREPL connection to be edited
        @type tuple of (str, str, str)
        """
        self.nameEdit.setText(params[0])
        self.descriptionEdit.setText(params[1])

        url = params[2].replace("ws://", "")
        password, hostPort = url.split("@", 1) if "@" in url else ("", url)
        host, port = hostPort.split(":", 1) if ":" in hostPort else (hostPort, "")
        self.hostEdit.setText(host)
        self.portEdit.setText(port)
        self.passwordEdit.setText(password)

        typeIndex = self.deviceTypeComboBox.findData(params[3])
        self.deviceTypeComboBox.setCurrentIndex(typeIndex)

    @pyqtSlot()
    def __updateOkButton(self):
        """
        Private slot to update the enabled state of the OK button.
        """
        port = self.portEdit.text()
        if port == "":
            portOk = True
        else:
            try:
                portNo = int(port)
                portOk = 1024 < portNo <= 65535
            except ValueError:
                portOk = False

        name = self.nameEdit.text()
        nameOk = bool(name) and (
            name == self.__editName or name not in self.__definedNames
        )

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            nameOk
            and bool(self.descriptionEdit.text())
            and bool(self.hostEdit.text())
            and portOk
            and bool(self.deviceTypeComboBox.currentData())
        )

    def getWebreplUrl(self):
        """
        Public method to retrieve the entered WebREPL connection data.

        @return tuple containing the name, description, URL and device type for
            the WebREPL connection
        @rtype tuple of (str, str, str, str)
        """
        password = self.passwordEdit.text()
        host = self.hostEdit.text()
        port = self.portEdit.text()

        if password and port:
            url = f"ws://{password}@{host}:{port}"
        elif password:
            url = f"ws://{password}@{host}"
        elif port:
            url = f"ws://{host}:{port}"
        else:
            url = f"ws://{host}"

        return (
            self.nameEdit.text(),
            self.descriptionEdit.text(),
            url,
            self.deviceTypeComboBox.currentData(),
        )
