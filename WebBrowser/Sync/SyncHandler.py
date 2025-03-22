# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module containing a base class for synchronization handlers.
"""

import os

from PyQt6.QtCore import QByteArray, QObject, pyqtSignal

from eric7 import Preferences
from eric7.EricUtilities.crypto import dataDecrypt, dataEncrypt


class SyncHandler(QObject):
    """
    Base class for synchronization handlers.

    @signal syncStatus(type_, message) emitted to indicate the synchronization status
    @signal syncError(message) emitted for a general error with the error message
    @signal syncMessage(message) emitted to send a message about synchronization
    @signal syncFinished(type_, done, download) emitted after a synchronization
        has finished
    """

    syncStatus = pyqtSignal(str, str)
    syncError = pyqtSignal(str)
    syncMessage = pyqtSignal(str)
    syncFinished = pyqtSignal(str, bool, bool)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self._firstTimeSynced = False

        self._remoteFiles = {
            "bookmarks": "Bookmarks",
            "history": "History",
            "passwords": "Logins",
            "useragents": "UserAgentSettings",
            "speeddial": "SpeedDial",
        }

        self._messages = {
            "bookmarks": {
                "RemoteExists": self.tr(
                    "Remote bookmarks file exists! Syncing local copy..."
                ),
                "RemoteMissing": self.tr(
                    "Remote bookmarks file does NOT exist. Exporting local copy..."
                ),
                "LocalNewer": self.tr(
                    "Local bookmarks file is NEWER. Exporting local copy..."
                ),
                "LocalMissing": self.tr(
                    "Local bookmarks file does NOT exist. Skipping synchronization!"
                ),
                "Uploading": self.tr("Uploading local bookmarks file..."),
            },
            "history": {
                "RemoteExists": self.tr(
                    "Remote history file exists! Syncing local copy..."
                ),
                "RemoteMissing": self.tr(
                    "Remote history file does NOT exist. Exporting local copy..."
                ),
                "LocalNewer": self.tr(
                    "Local history file is NEWER. Exporting local copy..."
                ),
                "LocalMissing": self.tr(
                    "Local history file does NOT exist. Skipping synchronization!"
                ),
                "Uploading": self.tr("Uploading local history file..."),
            },
            "passwords": {
                "RemoteExists": self.tr(
                    "Remote logins file exists! Syncing local copy..."
                ),
                "RemoteMissing": self.tr(
                    "Remote logins file does NOT exist. Exporting local copy..."
                ),
                "LocalNewer": self.tr(
                    "Local logins file is NEWER. Exporting local copy..."
                ),
                "LocalMissing": self.tr(
                    "Local logins file does NOT exist. Skipping synchronization!"
                ),
                "Uploading": self.tr("Uploading local logins file..."),
            },
            "useragents": {
                "RemoteExists": self.tr(
                    "Remote user agent settings file exists! Syncing local copy..."
                ),
                "RemoteMissing": self.tr(
                    "Remote user agent settings file does NOT exist."
                    " Exporting local copy..."
                ),
                "LocalNewer": self.tr(
                    "Local user agent settings file is NEWER. Exporting"
                    " local copy..."
                ),
                "LocalMissing": self.tr(
                    "Local user agent settings file does NOT exist."
                    " Skipping synchronization!"
                ),
                "Uploading": self.tr("Uploading local user agent settings file..."),
            },
            "speeddial": {
                "RemoteExists": self.tr(
                    "Remote speed dial settings file exists! Syncing local copy..."
                ),
                "RemoteMissing": self.tr(
                    "Remote speed dial settings file does NOT exist."
                    " Exporting local copy..."
                ),
                "LocalNewer": self.tr(
                    "Local speed dial settings file is NEWER. Exporting"
                    " local copy..."
                ),
                "LocalMissing": self.tr(
                    "Local speed dial settings file does NOT exist."
                    " Skipping synchronization!"
                ),
                "Uploading": self.tr("Uploading local speed dial settings file..."),
            },
        }

    def syncBookmarks(self):
        """
        Public method to synchronize the bookmarks.

        @exception NotImplementedError raised to indicate that this method
            must be implemented by subclasses
        """
        raise NotImplementedError

    def syncHistory(self):
        """
        Public method to synchronize the history.

        @exception NotImplementedError raised to indicate that this method
            must be implemented by subclasses
        """
        raise NotImplementedError

    def syncPasswords(self):
        """
        Public method to synchronize the passwords.

        @exception NotImplementedError raised to indicate that this method
            must be implemented by subclasses
        """
        raise NotImplementedError

    def syncUserAgents(self):
        """
        Public method to synchronize the user agents.

        @exception NotImplementedError raised to indicate that this method
            must be implemented by subclasses
        """
        raise NotImplementedError

    def syncSpeedDial(self):
        """
        Public method to synchronize the speed dial data.

        @exception NotImplementedError raised to indicate that this method
            must be implemented by subclasses
        """
        raise NotImplementedError

    def initialLoadAndCheck(self, forceUpload):
        """
        Public method to do the initial check.

        @param forceUpload flag indicating a forced upload of the files
        @type bool
        @exception NotImplementedError raised to indicate that this method
            must be implemented by subclasses
        """
        raise NotImplementedError

    def shutdown(self):
        """
        Public method to shut down the handler.

        @exception NotImplementedError raised to indicate that this method
            must be implemented by subclasses
        """
        raise NotImplementedError

    def readFile(self, fileName, type_):
        """
        Public method to read a file.

        If encrypted synchronization is enabled, the data will be encrypted
        using the relevant encryption key.

        @param fileName name of the file to be read
        @type str
        @param type_ type of the synchronization event (one of "bookmarks",
            "history", "passwords", "useragents" or "speeddial")
        @type str
        @return data of the file, optionally encrypted
        @rtype QByteArray
        """
        if os.path.exists(fileName):
            try:
                with open(fileName, "rb") as inputFile:
                    data = inputFile.read()
            except OSError:
                return QByteArray()

            if Preferences.getWebBrowser("SyncEncryptData") and (
                not Preferences.getWebBrowser("SyncEncryptPasswordsOnly")
                or (
                    Preferences.getWebBrowser("SyncEncryptPasswordsOnly")
                    and type_ == "passwords"
                )
            ):
                key = Preferences.getWebBrowser("SyncEncryptionKey")
                if not key:
                    return QByteArray()

                data, ok = dataEncrypt(
                    data,
                    key,
                    keyLength=Preferences.getWebBrowser("SyncEncryptionKeyLength"),
                    hashIterations=100,
                )
                if not ok:
                    return QByteArray()

            return QByteArray(data)

        return QByteArray()

    def writeFile(self, data, fileName, type_, timestamp=0):
        """
        Public method to write the data to a file.

        If encrypted synchronization is enabled, the data will be decrypted
        using the relevant encryption key.

        @param data data to be written and optionally decrypted
        @type QByteArray
        @param fileName name of the file the data is to be written to
        @type str
        @param type_ type of the synchronization event (one of "bookmarks",
            "history", "passwords", "useragents" or "speeddial")
        @type str
        @param timestamp timestamp to be given to the file
        @type int
        @return tuple giving a success flag and an error string
        @rtype tuple of (bool, str)
        """
        data = bytes(data)

        if Preferences.getWebBrowser("SyncEncryptData") and (
            not Preferences.getWebBrowser("SyncEncryptPasswordsOnly")
            or (
                Preferences.getWebBrowser("SyncEncryptPasswordsOnly")
                and type_ == "passwords"
            )
        ):
            key = Preferences.getWebBrowser("SyncEncryptionKey")
            if not key:
                return False, self.tr("Invalid encryption key given.")

            data, ok = dataDecrypt(
                data,
                key,
                keyLength=Preferences.getWebBrowser("SyncEncryptionKeyLength"),
            )
            if not ok:
                return False, self.tr("Data cannot be decrypted.")

        try:
            with open(fileName, "wb") as outputFile:
                outputFile.write(data)
            if timestamp > 0:
                os.utime(fileName, (timestamp, timestamp))
            return True, ""
        except OSError as error:
            return False, str(error)
