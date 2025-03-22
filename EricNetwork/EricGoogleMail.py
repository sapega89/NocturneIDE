# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to send bug reports.
"""

import base64
import os

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials, UserAccessTokenCredentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import discovery, errors
from PyQt6.QtCore import QObject, pyqtSignal

from eric7 import EricUtilities

from .EricGoogleMailHelpers import CLIENT_SECRET_FILE, SCOPES, TOKEN_FILE


class EricGoogleMail(QObject):
    """
    Class implementing the logic to send emails via Google Mail.

    @signal sendResult(bool, str) emitted to indicate the transmission result
        and a result message
    """

    sendResult = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent=parent)

        self.__messages = []

        self.__credentials = None

    def sendMessage(self, message):
        """
        Public method to send a message via Google Mail.

        @param message email message to be sent
        @type email.mime.text.MIMEBase
        """
        self.__messages.append(message)

        if not self.__credentials:
            self.__startSession()

        self.__doSendMessages()

    def __prepareMessage(self, message):
        """
        Private method to prepare the message for sending.

        @param message message to be prepared
        @type email.mime.text.MIMEBase
        @return prepared message dictionary
        @rtype dict
        """
        messageAsBase64 = base64.urlsafe_b64encode(message.as_bytes())
        raw = messageAsBase64.decode()
        return {"raw": raw}

    def __startSession(self):
        """
        Private method to start an authorized session and optionally execute the
        authorization flow.
        """
        # check for availability of secrets file
        if not os.path.exists(
            os.path.join(EricUtilities.getConfigDir(), CLIENT_SECRET_FILE)
        ):
            self.sendResult.emit(
                False,
                self.tr(
                    "The client secrets file is not present. Has the Gmail"
                    " API been enabled?"
                ),
            )
            return

        credentials = self.__loadCredentials()
        credentials = UserAccessTokenCredentials()
        # If there are no (valid) credentials available, let the user log in.
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                try:
                    credentials.refresh(Request())
                except RefreshError:
                    credentials = None
            if not credentials or not credentials.valid:
                flow = InstalledAppFlow.from_client_secrets_file(
                    os.path.join(EricUtilities.getConfigDir(), CLIENT_SECRET_FILE),
                    SCOPES,
                )
                credentials = flow.run_local_server(port=0)
            # Save the credentials for the next run
            self.__saveCredentials(credentials)

        self.__credentials = credentials

    def __doSendMessages(self):
        """
        Private method to send all queued messages.
        """
        if not self.__credentials or not self.__credentials.valid:
            self.sendResult.emit(False, self.tr("No valid credentials available."))
            return

        try:
            results = []
            service = discovery.build(
                "gmail", "v1", credentials=self.__credentials, cache_discovery=False
            )
            count = 0
            while self.__messages:
                count += 1
                message = self.__messages.pop(0)
                message1 = self.__prepareMessage(message)
                service.users().messages().send(userId="me", body=message1).execute()
                results.append(self.tr("Message #{0} sent.").format(count))

            self.sendResult.emit(True, "\n\n".join(results))
        except errors.HttpError as err:
            self.sendResult.emit(False, str(err))

    def __loadCredentials(self):
        """
        Private method to load credentials from the token file.

        @return created credentials object
        @rtype Credentials
        """
        homeDir = os.path.expanduser("~")
        credentialsDir = os.path.join(homeDir, ".credentials")
        if not os.path.exists(credentialsDir):
            os.makedirs(credentialsDir)
        tokenPath = os.path.join(credentialsDir, TOKEN_FILE)

        if os.path.exists(tokenPath):
            return Credentials.from_authorized_user_file(tokenPath, SCOPES)
        else:
            return None

    def __saveCredentials(self, credentials):
        """
        Private method to save credentials to the token file.

        @param credentials credentials to be saved
        @type Credentials
        """
        homeDir = os.path.expanduser("~")
        credentialsDir = os.path.join(homeDir, ".credentials")
        if not os.path.exists(credentialsDir):
            os.makedirs(credentialsDir)
        tokenPath = os.path.join(credentialsDir, TOKEN_FILE)

        with open(tokenPath, "w") as tokenFile:
            tokenFile.write(credentials.to_json())


def GoogleMailHelp():
    """
    Module function to get some help about how to enable the Google Mail
    OAuth2 service.

    @return help text
    @rtype str
    """
    return (
        "<h2>Steps to turn on the Gmail API</h2>"
        "<ol>"
        "<li>Use <a href='{0}'>this wizard</a> to create or select a project"
        " in the Google Developers Console and automatically turn on the API."
        " Click <b>Continue</b>.</li>"
        "<li>Select <b>Create Project</b>, fill out the form and select <b>Create</b>."
        " Select <b>Continue</b> and <b>Activate</b>.</li>"
        "<li>In the left side pane (menu) select <b>APIs and Services</b></li>"
        "<li>Select <b>OAuth consent screen</b>, press <b>Create</b> and"
        " fill out the form.</li>"
        "<li>In the menu select <b>Credentials</b> and create OAuth credentials.</li>"
        "<li>At the end of the process select the <b>Download</b> button below the"
        "Client-ID. Save the credentials file to the eric configuration directory"
        " <code>{1}</code> with the name <code>{2}</code>.</li>"
        "</ol>".format(
            "https://console.developers.google.com/start/api?id=gmail",
            EricUtilities.getConfigDir(),
            CLIENT_SECRET_FILE,
        )
    )
