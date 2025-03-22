# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Email configuration page.
"""

import smtplib
import socket

from PyQt6.QtCore import pyqtSlot

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricSimpleHelpDialog import EricSimpleHelpDialog

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EmailPage import Ui_EmailPage


class EmailPage(ConfigurationPageBase, Ui_EmailPage):
    """
    Class implementing the Email configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EmailPage")

        self.__helpDialog = None

        pipPackages = [
            "google-api-python-client",
            "google-auth-oauthlib",
        ]
        self.__pipCommand = "pip install --upgrade {0}".format(" ".join(pipPackages))

        # set initial values
        self.__checkGoogleMail()

        self.mailServerEdit.setText(Preferences.getUser("MailServer"))
        self.portSpin.setValue(Preferences.getUser("MailServerPort"))
        self.emailEdit.setText(Preferences.getUser("Email"))
        self.signatureEdit.setPlainText(Preferences.getUser("Signature"))
        self.mailAuthenticationGroup.setChecked(
            Preferences.getUser("MailServerAuthentication")
        )
        self.mailUserEdit.setText(Preferences.getUser("MailServerUser"))
        self.mailPasswordEdit.setText(Preferences.getUser("MailServerPassword"))
        encryption = Preferences.getUser("MailServerEncryption")
        if encryption == "TLS":
            self.useTlsButton.setChecked(True)
        elif encryption == "SSL":
            self.useSslButton.setChecked(True)
        else:
            self.noEncryptionButton.setChecked(True)

    def save(self):
        """
        Public slot to save the Email configuration.
        """
        Preferences.setUser("UseGoogleMailOAuth2", self.googleMailCheckBox.isChecked())
        Preferences.setUser("MailServer", self.mailServerEdit.text())
        Preferences.setUser("MailServerPort", self.portSpin.value())
        Preferences.setUser("Email", self.emailEdit.text())
        Preferences.setUser("Signature", self.signatureEdit.toPlainText())
        Preferences.setUser(
            "MailServerAuthentication", self.mailAuthenticationGroup.isChecked()
        )
        Preferences.setUser("MailServerUser", self.mailUserEdit.text())
        Preferences.setUser("MailServerPassword", self.mailPasswordEdit.text())
        if self.useTlsButton.isChecked():
            encryption = "TLS"
        elif self.useSslButton.isChecked():
            encryption = "SSL"
        else:
            encryption = "No"
        Preferences.setUser("MailServerEncryption", encryption)

    def __updatePortSpin(self):
        """
        Private slot to set the value of the port spin box depending upon
        the selected encryption method.
        """
        if self.useSslButton.isChecked():
            self.portSpin.setValue(465)
        elif self.useTlsButton.isChecked():
            self.portSpin.setValue(587)
        else:
            self.portSpin.setValue(25)

    @pyqtSlot(bool)
    def on_noEncryptionButton_toggled(self, _checked):
        """
        Private slot handling a change of no encryption button.

        @param _checked current state of the button (unused)
        @type bool
        """
        self.__updatePortSpin()

    @pyqtSlot(bool)
    def on_useSslButton_toggled(self, _checked):
        """
        Private slot handling a change of SSL encryption button.

        @param _checked current state of the button (unused)
        @type bool
        """
        self.__updatePortSpin()

    @pyqtSlot(bool)
    def on_useTlsButton_toggled(self, _checked):
        """
        Private slot handling a change of TLS encryption button.

        @param _checked current state of the button (unused)
        @type bool
        """
        self.__updatePortSpin()

    def __updateTestButton(self):
        """
        Private slot to update the enabled state of the test button.
        """
        self.testButton.setEnabled(
            self.mailAuthenticationGroup.isChecked()
            and self.mailUserEdit.text() != ""
            and self.mailPasswordEdit.text() != ""
            and self.mailServerEdit.text() != ""
        )

    @pyqtSlot(str)
    def on_mailServerEdit_textChanged(self, _txt):
        """
        Private slot to handle a change of the text of the mail server edit.

        @param _txt current text of the edit (unused)
        @type str
        """
        self.__updateTestButton()

    @pyqtSlot(bool)
    def on_mailAuthenticationGroup_toggled(self, _checked):
        """
        Private slot to handle a change of the state of the authentication
        group.

        @param _checked state of the group (unused)
        @type bool
        """
        self.__updateTestButton()

    @pyqtSlot(str)
    def on_mailUserEdit_textChanged(self, _txt):
        """
        Private slot to handle a change of the text of the user edit.

        @param _txt current text of the edit (unused)
        @type str
        """
        self.__updateTestButton()

    @pyqtSlot(str)
    def on_mailPasswordEdit_textChanged(self, _txt):
        """
        Private slot to handle a change of the text of the user edit.

        @param _txt current text of the edit (unused)
        @type str
        """
        self.__updateTestButton()

    @pyqtSlot()
    def on_testButton_clicked(self):
        """
        Private slot to test the mail server login data.
        """
        try:
            with EricOverrideCursor():
                if self.useSslButton.isChecked():
                    server = smtplib.SMTP_SSL(
                        self.mailServerEdit.text(), self.portSpin.value(), timeout=10
                    )
                else:
                    server = smtplib.SMTP(
                        self.mailServerEdit.text(), self.portSpin.value(), timeout=10
                    )
                    if self.useTlsButton.isChecked():
                        server.starttls()
                server.login(self.mailUserEdit.text(), self.mailPasswordEdit.text())
                server.quit()
            EricMessageBox.information(
                self, self.tr("Login Test"), self.tr("""The login test succeeded.""")
            )
        except (OSError, smtplib.SMTPException) as e:
            if isinstance(e, smtplib.SMTPResponseException):
                errorStr = e.smtp_error.decode()
            elif isinstance(e, socket.timeout):
                errorStr = str(e)
            elif isinstance(e, OSError):
                try:
                    errorStr = e[1]
                except TypeError:
                    errorStr = str(e)
            else:
                errorStr = str(e)
            EricMessageBox.critical(
                self,
                self.tr("Login Test"),
                self.tr("""<p>The login test failed.<br>Reason: {0}</p>""").format(
                    errorStr
                ),
            )

    @pyqtSlot()
    def on_googleHelpButton_clicked(self):
        """
        Private slot to show some help text "how to turn on the Gmail API".
        """
        if self.__helpDialog is None:
            try:
                from eric7.EricNetwork.EricGoogleMail import (  # __IGNORE_WARNING__
                    GoogleMailHelp,
                )

                helpStr = GoogleMailHelp()
            except ImportError:
                helpStr = self.tr(
                    "<p>The Google Mail Client API is not installed."
                    " Use the <b>{0}</b> button to install it.</p>"
                ).format(self.googleInstallButton.text())

            self.__helpDialog = EricSimpleHelpDialog(
                title=self.tr("Gmail API Help"), helpStr=helpStr, parent=self
            )

        self.__helpDialog.show()

    @pyqtSlot()
    def on_googleInstallButton_clicked(self):
        """
        Private slot to install the required packages for use of Google Mail.
        """
        from eric7.EricNetwork.EricGoogleMailHelpers import installGoogleAPIPackages

        installGoogleAPIPackages()
        self.__checkGoogleMail()

    @pyqtSlot()
    def on_googleCheckAgainButton_clicked(self):
        """
        Private slot to check again the availability of Google Mail.
        """
        self.__checkGoogleMail()

    def __checkGoogleMail(self):
        """
        Private method to check the Google Mail availability and set the
        widgets accordingly.
        """
        self.googleMailInfoLabel.hide()
        self.googleInstallButton.show()
        self.googleCheckAgainButton.show()
        self.googleHelpButton.setEnabled(True)
        self.googleMailCheckBox.setEnabled(True)

        try:
            from eric7.EricNetwork import EricGoogleMail  # __IGNORE_WARNING__
            from eric7.EricNetwork.EricGoogleMailHelpers import (  # noqa: I101
                isClientSecretFileAvailable,
            )

            self.googleInstallButton.hide()
            if not isClientSecretFileAvailable():
                # secrets file is not installed
                self.googleMailCheckBox.setChecked(False)
                self.googleMailCheckBox.setEnabled(False)
                self.googleMailInfoLabel.setText(
                    self.tr(
                        "<p>The client secrets file is not present."
                        " Has the Gmail API been enabled?</p>"
                    )
                )
                self.googleMailInfoLabel.show()
                Preferences.setUser("UseGoogleMailOAuth2", False)
            else:
                self.googleMailCheckBox.setChecked(
                    Preferences.getUser("UseGoogleMailOAuth2")
                )
                self.googleMailInfoLabel.hide()
                self.googleCheckAgainButton.hide()
        except ImportError:
            # missing libraries, disable Google Mail
            self.googleMailCheckBox.setChecked(False)
            self.googleMailCheckBox.setEnabled(False)
            self.googleMailInfoLabel.setText(
                self.tr(
                    "<p>The Google Mail Client API is not installed."
                    " Use the <b>{0}</b> button to install it.</p>"
                ).format(self.googleInstallButton.text())
            )
            self.googleMailInfoLabel.show()
            self.googleHelpButton.setEnabled(False)
            Preferences.setUser("UseGoogleMailOAuth2", False)


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EmailPage()
    return page
