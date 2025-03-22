# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the minimum protocol for a host.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_HgUserConfigHostMinimumProtocolDialog import (
    Ui_HgUserConfigHostMinimumProtocolDialog,
)


class HgUserConfigHostMinimumProtocolDialog(
    QDialog, Ui_HgUserConfigHostMinimumProtocolDialog
):
    """
    Class implementing a dialog to enter the minimum protocol for a host.
    """

    def __init__(self, allowedProtocols, parent=None, host="", protocol=""):
        """
        Constructor

        @param allowedProtocols dictionary containing the allowed protocols
            with the value as key and the display string as value
        @type dict
        @param parent reference to the parent widget
        @type QWidget
        @param host host name
        @type str
        @param protocol name of the minimum protocol for the host
        @type str
        """
        super().__init__(parent)
        self.setupUi(self)

        self.minimumProtocolComboBox.addItem("", "")
        for minimumProtocol in sorted(allowedProtocols):
            self.minimumProtocolComboBox.addItem(
                allowedProtocols[minimumProtocol], minimumProtocol
            )

        self.hostEdit.setText(host)
        index = self.minimumProtocolComboBox.findData(protocol)
        if index == -1:
            index = 0
        self.minimumProtocolComboBox.setCurrentIndex(index)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

        self.__updateOkButton()

    def __updateOkButton(self):
        """
        Private method to update the status of the Ok button.
        """
        enabled = (
            bool(self.hostEdit.text())
            and self.minimumProtocolComboBox.currentIndex() > 0
        )
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    @pyqtSlot(str)
    def on_hostEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the host edit.

        @param _txt current text (unused)
        @type str
        """
        self.__updateOkButton()

    @pyqtSlot(int)
    def on_minimumProtocolComboBox_currentIndexChanged(self, index):
        """
        Private slot to handle the selection of a minimum protocol.

        @param index index of the selected entry
        @type int
        """
        self.__updateOkButton()

    def getData(self):
        """
        Public method to retrieve the data.

        @return tuple containig the host name and the minimum protocol
        @rtype tuple of two str
        """
        return (
            self.hostEdit.text().strip(),
            self.minimumProtocolComboBox.itemData(
                self.minimumProtocolComboBox.currentIndex()
            ),
        )
