# -*- coding: utf-8 -*-
# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to handle the various WebAuth requests.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWebEngineCore import QWebEngineWebAuthUxRequest
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QLineEdit,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
)

from eric7.EricGui import EricPixmapCache

from .Ui_WebBrowserWebAuthDialog import Ui_WebBrowserWebAuthDialog


class WebBrowserWebAuthDialog(QDialog, Ui_WebBrowserWebAuthDialog):
    """
    Class implementing a dialog to handle the various WebAuth requests.
    """

    def __init__(self, uxRequest, parent=None):
        """
        Constructor

        @param uxRequest reference to the WebAuth request object
        @type QWebEngineWebAuthUxRequest
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__uxRequest = uxRequest

        self.pinButton.setIcon(EricPixmapCache.getIcon("showPassword"))

        self.selectAccountButtonGroup = QButtonGroup(self)
        self.selectAccountButtonGroup.setExclusive(True)

        self.selectAccountLayout = QVBoxLayout(self.selectAccountWidget)
        self.selectAccountLayout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.buttonBox.accepted.connect(self.__acceptRequest)
        self.buttonBox.rejected.connect(self.__cancelRequest)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Retry).clicked.connect(
            self.__retry
        )

        self.updateDialog()

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    @pyqtSlot(str)
    def on_pinEdit_textEdited(self, pin):
        """
        Private slot handling entering a PIN.

        @param pin entered PIN
        @type str
        """
        self.confirmPinErrorLabel.setVisible(
            self.confirmPinEdit.isVisible() and pin != self.confirmPinEdit.text()
        )
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            (self.confirmPinEdit.isVisible() and pin == self.confirmPinEdit.text())
            or not self.confirmPinEdit.isVisible()
        )

        self.adjustSize()

    @pyqtSlot(bool)
    def on_pinButton_toggled(self, checked):
        """
        Private slot to handle the toggling of the PIN visibility.

        @param checked state of the PIN visibility button
        @type bool
        """
        pinRequestInfo = self.__uxRequest.pinRequest()

        if checked:
            self.pinButton.setIcon(EricPixmapCache.getIcon("hidePassword"))
            self.pinEdit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.pinButton.setIcon(EricPixmapCache.getIcon("showPassword"))
            self.pinEdit.setEchoMode(QLineEdit.EchoMode.Password)

        if pinRequestInfo.reason != QWebEngineWebAuthUxRequest.PinEntryReason.Challenge:
            self.confirmPinLabel.setVisible(not checked)
            self.confirmPinEdit.setVisible(not checked)
            self.on_pinEdit_textEdited(self.pinEdit.text())

    @pyqtSlot(str)
    def on_confirmPinEdit_textEdited(self, pin):
        """
        Private slot handling entering of a confirmation PIN.

        @param pin entered confirmation PIN
        @type str
        """
        self.confirmPinErrorLabel.setVisible(pin != self.pinEdit.text())
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            pin == self.confirmPinEdit.text()
        )

        self.adjustSize()

    @pyqtSlot()
    def __acceptRequest(self):
        """
        Private slot to accept the WebAuth request.
        """
        requestState = self.__uxRequest.state()
        if requestState == QWebEngineWebAuthUxRequest.WebAuthUxState.SelectAccount:
            checkedButton = self.selectAccountButtonGroup.checkedButton()
            if checkedButton:
                self.__uxRequest.setSelectedAccount(checkedButton.text())
        elif requestState == QWebEngineWebAuthUxRequest.WebAuthUxState.CollectPin:
            self.__uxRequest.setPin(self.pinEdit.text())

    @pyqtSlot()
    def __cancelRequest(self):
        """
        Private slot to cancel the WebAuth request.
        """
        self.__uxRequest.cancel()

    @pyqtSlot()
    def __retry(self):
        """
        Private slot to retry the WebAuth request.
        """
        self.__uxRequest.retry()

    @pyqtSlot()
    def updateDialog(self):
        """
        Public slot to update the dialog depending on the current WebAuth request state.
        """
        requestState = self.__uxRequest.state()
        if requestState == QWebEngineWebAuthUxRequest.WebAuthUxState.SelectAccount:
            self.__setupSelectAccountUi()
        elif requestState == QWebEngineWebAuthUxRequest.WebAuthUxState.CollectPin:
            self.__setupCollectPinUi()
        elif (
            requestState
            == QWebEngineWebAuthUxRequest.WebAuthUxState.FinishTokenCollection
        ):
            self.__setupFinishCollectTokenUi()
        elif requestState == QWebEngineWebAuthUxRequest.WebAuthUxState.RequestFailed:
            self.__setupErrorUi()

        self.adjustSize()

    def __setupSelectAccountUi(self):
        """
        Private method to configure the 'Select Account' UI.
        """
        self.__clearSelectAccountButtons()

        self.headerLabel.setText(self.tr("<b>Choose Passkey</b>"))
        self.descriptionLabel.setText(
            self.tr("Which passkey do you want to use for {0}?").format(
                self.__uxRequest.relyingPartyId()
            )
        )
        self.pinGroupBox.setVisible(False)

        self.selectAccountArea.setVisible(True)
        self.selectAccountWidget.resize(self.width(), self.height())
        userNames = self.__uxRequest.userNames()
        for name in sorted(userNames):
            button = QRadioButton(name)
            self.selectAccountLayout.addWidget(button)
            self.selectAccountButtonGroup.addButton(button)
        if len(userNames) == 1:
            # nothing to select from, select the one and only button
            self.selectAccountButtonGroup.buttons()[0].setChecked(True)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(self.tr("Ok"))
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setVisible(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setVisible(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Retry).setVisible(False)

        if len(userNames) > 1:
            self.selectAccountButtonGroup.buttons()[0].setFocus(
                Qt.FocusReason.OtherFocusReason
            )
        else:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setFocus(
                Qt.FocusReason.OtherFocusReason
            )

    def __setupCollectPinUi(self):
        """
        Private method to configure the 'Collect PIN' UI.
        """
        self.__clearSelectAccountButtons()

        self.selectAccountArea.setVisible(False)

        self.pinGroupBox.setVisible(True)
        self.confirmPinLabel.setVisible(False)
        self.confirmPinEdit.setVisible(False)
        self.confirmPinErrorLabel.setVisible(False)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(
            self.tr("Next")
        )
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setVisible(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setVisible(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Retry).setVisible(False)

        pinRequestInfo = self.__uxRequest.pinRequest()
        if pinRequestInfo.reason == QWebEngineWebAuthUxRequest.PinEntryReason.Challenge:
            self.headerLabel.setText(self.tr("<b>PIN Required</b>"))
            self.descriptionLabel.setText(
                self.tr("Enter the PIN for your security key.")
            )
        else:
            if pinRequestInfo.reason == QWebEngineWebAuthUxRequest.PinEntryReason.Set:
                self.headerLabel.setText(self.tr("<b>New PIN Required</b>"))
                self.descriptionLabel.setText(
                    self.tr("Set new PIN for your security key.")
                )
            else:
                self.headerLabel.setText(self.tr("<b>PIN Change Required</b>"))
                self.descriptionLabel.setText(
                    self.tr("Change the PIN for your security key.")
                )
            self.confirmPinLabel.setVisible(True)
            self.confirmPinEdit.setVisible(True)

        errorDetails = ""
        if (
            pinRequestInfo.error
            == QWebEngineWebAuthUxRequest.PinEntryError.InternalUvLocked
        ):
            errorDetails = self.tr("Internal User Verification Locked!")
        elif pinRequestInfo.error == QWebEngineWebAuthUxRequest.PinEntryError.WrongPin:
            errorDetails = self.tr("Wrong PIN!")
        elif pinRequestInfo.error == QWebEngineWebAuthUxRequest.PinEntryError.TooShort:
            errorDetails = self.tr("PIN Too Short!")
        elif (
            pinRequestInfo.error
            == QWebEngineWebAuthUxRequest.PinEntryError.InvalidCharacters
        ):
            errorDetails = self.tr("PIN Contains Invalid Characters!")
        elif (
            pinRequestInfo.error
            == QWebEngineWebAuthUxRequest.PinEntryError.SameAsCurrentPin
        ):
            errorDetails = self.tr("New PIN is same as current PIN!")
        if errorDetails:
            errorDetails = self.tr(
                "{0} %n attempt(s) remaining.", "", pinRequestInfo.remainingAttempts
            ).format(errorDetails)
        self.pinErrorLabel.setText(errorDetails)
        self.pinErrorLabel.setVisible(bool(errorDetails))

        self.pinEdit.setFocus(Qt.FocusReason.OtherFocusReason)

    def __setupFinishCollectTokenUi(self):
        """
        Private method to configure the 'Finish Collect Token' UI.
        """
        self.__clearSelectAccountButtons()

        self.headerLabel.setText(
            self.tr("<b>Use your security key with {0}</b>").format(
                self.__uxRequest.relyingPartyId()
            )
        )
        self.descriptionLabel.setText(
            self.tr("Touch your security key to complete the request.")
        )

        self.pinGroupBox.setVisible(False)
        self.selectAccountArea.setVisible(False)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setVisible(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setVisible(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Retry).setVisible(False)

    def __setupErrorUi(self):
        """
        Private method to configure the 'Error' UI.
        """
        self.__clearSelectAccountButtons()

        errorMsg = ""
        retryVisible = False

        requestFailureReason = self.__uxRequest.requestFailureReason()
        if (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.Timeout
        ):
            errorMsg = self.tr("Request Timeout")
        elif (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.KeyNotRegistered
        ):
            errorMsg = self.tr("Security key is not registered.")
        elif (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.KeyAlreadyRegistered
        ):
            errorMsg = self.tr(
                "You already registered this security key. Try again with another"
                " security key."
            )
            retryVisible = True
        elif (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.SoftPinBlock
        ):
            errorMsg = self.tr(
                "The security key is locked because the wrong PIN was entered too"
                " many times. To unlock it, remove and reinsert it."
            )
            retryVisible = True
        elif (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.HardPinBlock
        ):
            errorMsg = self.tr(
                "The security key is locked because the wrong PIN was entered too"
                " many times. You will need to reset the security key."
            )
        elif (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.AuthenticatorRemovedDuringPinEntry  # noqa: E501
        ):
            errorMsg = self.tr(
                "Security key removed during verification. Please reinsert and try"
                " again."
            )
        elif (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.AuthenticatorMissingResidentKeys  # noqa: E501
        ):
            errorMsg = self.tr("Security key does not have resident key support.")
        elif (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.AuthenticatorMissingUserVerification  # noqa: E501
        ):
            errorMsg = self.tr("Security key is missing user verification.")
        elif (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.AuthenticatorMissingLargeBlob  # noqa: E501
        ):
            errorMsg = self.tr("Security key is missing Large Blob support.")
        elif (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.NoCommonAlgorithms
        ):
            errorMsg = self.tr("Security key does not provide a common algorithm.")
        elif (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.StorageFull
        ):
            errorMsg = self.tr("No storage space left on the security key.")
        elif (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.UserConsentDenied
        ):
            errorMsg = self.tr("User consent denied.")
        elif (
            requestFailureReason
            == QWebEngineWebAuthUxRequest.RequestFailureReason.WinUserCancelled
        ):
            errorMsg = self.tr("User canceled the WebAuth request.")

        self.headerLabel.setText(self.tr("<b>Something went wrong</b>"))
        self.descriptionLabel.setText(errorMsg)
        self.descriptionLabel.adjustSize()

        self.pinGroupBox.setVisible(False)
        self.selectAccountArea.setVisible(False)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setVisible(False)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setVisible(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel).setText(
            self.tr("Close")
        )
        self.buttonBox.button(QDialogButtonBox.StandardButton.Retry).setVisible(
            retryVisible
        )
        if retryVisible:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Retry).setFocus()

    def __clearSelectAccountButtons(self):
        """
        Private method to remove the account selection buttons.
        """
        for button in self.selectAccountButtonGroup.buttons():
            self.selectAccountLayout.removeWidget(button)
            self.selectAccountButtonGroup.removeButton(button)
