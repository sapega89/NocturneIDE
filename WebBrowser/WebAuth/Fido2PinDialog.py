# -*- coding: utf-8 -*-
# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the current and potentially new PIN.
"""

import enum

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QLineEdit

from eric7.EricGui import EricPixmapCache

from .Ui_Fido2PinDialog import Ui_Fido2PinDialog


class Fido2PinDialogMode(enum.Enum):
    """
    Class defining the various PIN dialog mode.
    """

    GET = 0
    SET = 1
    CHANGE = 2


class Fido2PinDialog(QDialog, Ui_Fido2PinDialog):
    """
    Class implementing a dialog to enter the current and potentially new PIN.
    """

    def __init__(self, mode, title, message, minLength, retries, parent=None):
        """
        Constructor

        @param mode mode of the dialog
        @type Fido2PinDialogMode
        @param title header title to be shown
        @type str
        @param message more decriptive text to be shown
        @type str
        @param minLength minimum PIN length
        @type int
        @param retries number of attempts remaining before the security key get locked
        @type int
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.pinButton.setIcon(EricPixmapCache.getIcon("showPassword"))
        self.newPinButton.setIcon(EricPixmapCache.getIcon("showPassword"))

        self.__minLength = minLength
        self.__mode = mode

        if title:
            self.headerLabel.setText(f"<b>{title}</b>")
        else:
            self.headerLabel.setVisible(False)
        if message:
            self.descriptionLabel.setText(message)
        else:
            self.descriptionLabel.setVisible(False)
        if self.__mode == Fido2PinDialogMode.SET:
            self.remainingWidget.setVisible(False)
        else:
            self.remainingWidget.setVisible(True)
            self.remainingLabel.setText(str(retries))
        self.pinErrorLabel.setVisible(False)

        if mode == Fido2PinDialogMode.GET:
            self.newPinGroupBox.setVisible(False)
        elif mode == Fido2PinDialogMode.SET:
            self.pinLabel.setVisible(False)
            self.pinEdit.setVisible(False)
            self.pinButton.setVisible(False)
        elif mode == Fido2PinDialogMode.CHANGE:
            # all entries visible
            pass

        self.pinEdit.textEdited.connect(self.__checkPins)
        self.newPinEdit.textEdited.connect(self.__checkPins)
        self.confirmNewPinEdit.textEdited.connect(self.__checkPins)

        self.__checkPins()

    @pyqtSlot()
    def __checkPins(self):
        """
        Private slot to check the entered PIN(s).

        Appropriate error messages are shown in case of issues and the state of
        the OK button is set accordingly.
        """
        messages = []

        if self.__mode in (Fido2PinDialogMode.SET, Fido2PinDialogMode.CHANGE):
            if len(self.newPinEdit.text()) < self.__minLength:
                messages.append(
                    self.tr("New PIN is too short (minimum length: {0}).").format(
                        self.__minLength
                    )
                )
            if (
                self.confirmNewPinEdit.isVisible()
                and self.confirmNewPinEdit.text() != self.newPinEdit.text()
            ):
                messages.append("New PIN confirmation does not match.")
        if (
            self.__mode == Fido2PinDialogMode.CHANGE
            and self.pinEdit.text() == self.newPinEdit.text()
        ):
            messages.append(self.tr("Old and new PIN must not be identical."))

        self.__showPinErrors(messages)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            not bool(messages)
        )

    def __showPinErrors(self, errorMessages):
        """
        Private method to show some error messages.

        @param errorMessages list of error messages
        @type list of str
        """
        if not errorMessages:
            self.pinErrorLabel.clear()
            self.pinErrorLabel.setVisible(False)
        else:
            if len(errorMessages) == 1:
                msg = errorMessages[0]
            else:
                msg = "- {0}".format("\n- ".join(errorMessages))
            self.pinErrorLabel.setText(msg)
            self.pinErrorLabel.setVisible(True)

        self.adjustSize()

    @pyqtSlot(bool)
    def on_pinButton_toggled(self, checked):
        """
        Private slot to handle the toggling of the PIN visibility.

        @param checked state of the PIN visibility button
        @type bool
        """
        if checked:
            self.pinButton.setIcon(EricPixmapCache.getIcon("hidePassword"))
            self.pinEdit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.pinButton.setIcon(EricPixmapCache.getIcon("showPassword"))
            self.pinEdit.setEchoMode(QLineEdit.EchoMode.Password)

    @pyqtSlot(bool)
    def on_newPinButton_toggled(self, checked):
        """
        Private slot to handle the toggling of the new PIN visibility.

        @param checked state of the new PIN visibility button
        @type bool
        """
        if checked:
            self.newPinButton.setIcon(EricPixmapCache.getIcon("hidePassword"))
            self.newPinEdit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.newPinButton.setIcon(EricPixmapCache.getIcon("showPassword"))
            self.newPinEdit.setEchoMode(QLineEdit.EchoMode.Password)

        self.confirmNewPinLabel.setVisible(not checked)
        self.confirmNewPinEdit.setVisible(not checked)
        self.__checkPins()

    def getPins(self):
        """
        Public method to get the entered PINs.

        @return tuple containing the current and new PIN
        @rtype tuple of (str, str)
        """
        if self.__mode == Fido2PinDialogMode.GET:
            return self.pinEdit.text(), None
        elif self.__mode == Fido2PinDialogMode.SET:
            return None, self.newPinEdit.text()
        elif self.__mode == Fido2PinDialogMode.CHANGE:
            return self.pinEdit.text(), self.newPinEdit.text()
        else:
            return None, None
