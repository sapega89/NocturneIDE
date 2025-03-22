# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the WebREPL connection parameters.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit

from eric7.EricGui import EricPixmapCache

from .Devices import getSupportedDevices
from .Ui_MicroPythonWebreplConnectionDialog import Ui_MicroPythonWebreplConnectionDialog


class MicroPythonWebreplConnectionDialog(
    QDialog, Ui_MicroPythonWebreplConnectionDialog
):
    """
    Class implementing a dialog to enter the WebREPL connection parameters.
    """

    def __init__(self, currentWebreplUrl, currentType, parent=None):
        """
        Constructor

        @param currentWebreplUrl WebREPL URL most recently configured
        @type str
        @param currentType device type most recently selected
        @type str
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.deviceTypeComboBox.addItem("", "")
        for board, description in sorted(getSupportedDevices(), key=lambda x: x[1]):
            self.deviceTypeComboBox.addItem(description, board)

        self.showPasswordButton.setIcon(EricPixmapCache.getIcon("showPassword"))

        self.hostEdit.textChanged.connect(self.__updateOkButton)
        self.portEdit.textChanged.connect(self.__updateOkButton)
        self.deviceTypeComboBox.currentIndexChanged.connect(self.__updateOkButton)

        if currentWebreplUrl:
            url = currentWebreplUrl.replace("ws://", "")
            password, hostPort = url.split("@", 1) if "@" in url else ("", url)
            host, port = hostPort.split(":", 1) if ":" in hostPort else (hostPort, "")
            self.hostEdit.setText(host)
            self.portEdit.setText(port)
            self.passwordEdit.setText(password)

            typeIndex = self.deviceTypeComboBox.findData(currentType)
            self.deviceTypeComboBox.setCurrentIndex(typeIndex)
        else:
            self.__updateOkButton()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

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
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.hostEdit.text())
            and portOk
            and bool(self.deviceTypeComboBox.currentData())
        )

    @pyqtSlot(bool)
    def on_showPasswordButton_clicked(self, checked):
        """
        Private slot to show or hide the password.

        @param checked state of the button
        @type bool
        """
        if checked:
            self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.showPasswordButton.setIcon(EricPixmapCache.getIcon("hidePassword"))
            self.showPasswordButton.setToolTip(self.tr("Press to hide the password."))
        else:
            self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Password)
            self.showPasswordButton.setIcon(EricPixmapCache.getIcon("showPassword"))
            self.showPasswordButton.setToolTip(self.tr("Press to show the password."))

    def getWebreplConnectionParameters(self):
        """
        Public method to retrieve the entered WebREPL connection data.

        @return tuple containing the URL and device type for the WebREPL connection
        @rtype tuple of (str, str)
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

        return (url, self.deviceTypeComboBox.currentData())
