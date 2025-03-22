# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the NTP parameters.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QAbstractButton, QDialog, QDialogButtonBox

from eric7 import Preferences

from .Ui_NtpParametersDialog import Ui_NtpParametersDialog


class NtpParametersDialog(QDialog, Ui_NtpParametersDialog):
    """
    Class implementing a dialog to enter the NTP parameters.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.serverEdit.textChanged.connect(self.__updateOk)

        self.serverEdit.setText(Preferences.getMicroPython("NtpServer"))
        self.tzOffsetSpinBox.setValue(Preferences.getMicroPython("NtpOffset"))
        self.dstCheckBox.setChecked(Preferences.getMicroPython("NtpDaylight"))
        self.timeoutSpinBox.setValue(Preferences.getMicroPython("NtpTimeout"))

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __updateOk(self):
        """
        Private slot to update the enabled stat of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.serverEdit.text())
        )

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot handling the selection of a dialog button.

        @param button reference to the clicked button
        @type QAbstractButton
        """
        if button == self.buttonBox.button(
            QDialogButtonBox.StandardButton.RestoreDefaults
        ):
            self.serverEdit.setText(Preferences.Prefs.microPythonDefaults["NtpServer"])
            self.tzOffsetSpinBox.setValue(
                Preferences.Prefs.microPythonDefaults["NtpOffset"]
            )
            self.dstCheckBox.setChecked(
                Preferences.Prefs.microPythonDefaults["NtpDaylight"]
            )
            self.timeoutSpinBox.setValue(
                Preferences.Prefs.microPythonDefaults["NtpTimeout"]
            )

    @pyqtSlot()
    def accept(self):
        """
        Public slot accepting the dialog.
        """
        if self.rememberCheckBox.isChecked():
            Preferences.setMicroPython("NtpServer", self.serverEdit.text())
            Preferences.setMicroPython("NtpOffset", self.tzOffsetSpinBox.value())
            Preferences.setMicroPython("NtpDaylight", self.dstCheckBox.isChecked())
            Preferences.setMicroPython("NtpTimeout", self.timeoutSpinBox.value())

        super().accept()

    def getParameters(self):
        """
        Public method to get the entered NTP parameters.

        @return tuple containing the NTP server name, the timezone offset in hours,
            a flag indicating daylight savings is in effect and a timeout value in
            seconds
        @rtype tuple of (str, int, bool, int)
        """
        return (
            self.serverEdit.text(),
            self.tzOffsetSpinBox.value(),
            self.dstCheckBox.isChecked(),
            self.timeoutSpinBox.value(),
        )
