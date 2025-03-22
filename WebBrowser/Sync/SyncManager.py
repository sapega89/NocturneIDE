# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the synchronization manager class.
"""

import contextlib

from PyQt6.QtCore import QObject, pyqtSignal

from eric7 import Preferences
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from . import SyncGlobals


class SyncManager(QObject):
    """
    Class implementing the synchronization manager.

    @signal syncError(message) emitted for a general error with the error message
    @signal syncMessage(message) emitted to give status info about the sync process
    @signal syncStatus(type_, message) emitted to indicate the synchronization status
    @signal syncFinished(type_, done, download) emitted after a synchronization
        has finished
    """

    syncError = pyqtSignal(str)
    syncMessage = pyqtSignal(str)
    syncStatus = pyqtSignal(str, str)
    syncFinished = pyqtSignal(str, bool, bool)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__handler = None

    def handler(self):
        """
        Public method to get a reference to the sync handler object.

        @return reference to the sync handler object
        @rtype SyncHandler
        """
        return self.__handler

    def showSyncDialog(self):
        """
        Public method to show the synchronization dialog.
        """
        from .SyncAssistantDialog import SyncAssistantDialog

        dlg = SyncAssistantDialog()
        dlg.exec()

    def loadSettings(self, forceUpload=False):
        """
        Public method to load the settings.

        @param forceUpload flag indicating a forced upload of the files
        @type bool
        """
        if self.__handler is not None:
            self.__handler.syncError.disconnect(self.__syncError)
            self.__handler.syncFinished.disconnect(self.__syncFinished)
            self.__handler.syncStatus.disconnect(self.__syncStatus)
            self.__handler.syncMessage.disconnect(self.syncMessage)
            self.__handler.shutdown()

        if self.syncEnabled():
            if Preferences.getWebBrowser("SyncType") == SyncGlobals.SyncTypeFtp:
                from .FtpSyncHandler import FtpSyncHandler  # __IGNORE_WARNING_I101__

                self.__handler = FtpSyncHandler(self)
            elif Preferences.getWebBrowser("SyncType") == SyncGlobals.SyncTypeDirectory:
                from .DirectorySyncHandler import (  # __IGNORE_WARNING_I101__
                    DirectorySyncHandler,
                )

                self.__handler = DirectorySyncHandler(self)
            self.__handler.syncError.connect(self.__syncError)
            self.__handler.syncFinished.connect(self.__syncFinished)
            self.__handler.syncStatus.connect(self.__syncStatus)
            self.__handler.syncMessage.connect(self.syncMessage)

            self.__handler.initialLoadAndCheck(forceUpload=forceUpload)

            # connect sync manager to bookmarks manager
            if Preferences.getWebBrowser("SyncBookmarks"):
                (
                    WebBrowserWindow.bookmarksManager().bookmarksSaved.connect(
                        self.__syncBookmarks
                    )
                )
            else:
                with contextlib.suppress(TypeError):
                    (
                        WebBrowserWindow.bookmarksManager().bookmarksSaved.disconnect(
                            self.__syncBookmarks
                        )
                    )

            # connect sync manager to history manager
            if Preferences.getWebBrowser("SyncHistory"):
                (
                    WebBrowserWindow.historyManager().historySaved.connect(
                        self.__syncHistory
                    )
                )
            else:
                with contextlib.suppress(TypeError):
                    (
                        WebBrowserWindow.historyManager().historySaved.disconnect(
                            self.__syncHistory
                        )
                    )

            # connect sync manager to passwords manager
            if Preferences.getWebBrowser("SyncPasswords"):
                (
                    WebBrowserWindow.passwordManager().passwordsSaved.connect(
                        self.__syncPasswords
                    )
                )
            else:
                with contextlib.suppress(TypeError):
                    (
                        WebBrowserWindow.passwordManager().passwordsSaved.disconnect(
                            self.__syncPasswords
                        )
                    )

            # connect sync manager to user agent manager
            if Preferences.getWebBrowser("SyncUserAgents"):
                (
                    WebBrowserWindow.userAgentsManager().userAgentSettingsSaved.connect(
                        self.__syncUserAgents
                    )
                )
            else:
                with contextlib.suppress(TypeError):
                    uam = WebBrowserWindow.userAgentsManager()
                    uam.userAgentSettingsSaved.disconnect(self.__syncUserAgents)

            # connect sync manager to speed dial
            if Preferences.getWebBrowser("SyncSpeedDial"):
                (
                    WebBrowserWindow.speedDial().speedDialSaved.connect(
                        self.__syncSpeedDial
                    )
                )
            else:
                with contextlib.suppress(TypeError):
                    (
                        WebBrowserWindow.speedDial().speedDialSaved.disconnect(
                            self.__syncSpeedDial
                        )
                    )
        else:
            self.__handler = None

            with contextlib.suppress(TypeError):
                (
                    WebBrowserWindow.bookmarksManager().bookmarksSaved.disconnect(
                        self.__syncBookmarks
                    )
                )
            with contextlib.suppress(TypeError):
                (
                    WebBrowserWindow.historyManager().historySaved.disconnect(
                        self.__syncHistory
                    )
                )
            with contextlib.suppress(TypeError):
                (
                    WebBrowserWindow.passwordManager().passwordsSaved.disconnect(
                        self.__syncPasswords
                    )
                )
            with contextlib.suppress(TypeError):
                uam = WebBrowserWindow.userAgentsManager()
                uam.userAgentSettingsSaved.disconnect(self.__syncUserAgents)
            with contextlib.suppress(TypeError):
                WebBrowserWindow.speedDial().speedDialSaved.disconnect(
                    self.__syncSpeedDial
                )

    def syncEnabled(self):
        """
        Public method to check, if synchronization is enabled.

        @return flag indicating enabled synchronization
        @rtype bool
        """
        from . import SyncGlobals

        return (
            Preferences.getWebBrowser("SyncEnabled")
            and Preferences.getWebBrowser("SyncType") != SyncGlobals.SyncTypeNone
        )

    def __syncBookmarks(self):
        """
        Private slot to synchronize the bookmarks.
        """
        if self.__handler is not None:
            self.__handler.syncBookmarks()

    def __syncHistory(self):
        """
        Private slot to synchronize the history.
        """
        if self.__handler is not None:
            self.__handler.syncHistory()

    def __syncPasswords(self):
        """
        Private slot to synchronize the passwords.
        """
        if self.__handler is not None:
            self.__handler.syncPasswords()

    def __syncUserAgents(self):
        """
        Private slot to synchronize the user agent settings.
        """
        if self.__handler is not None:
            self.__handler.syncUserAgents()

    def __syncSpeedDial(self):
        """
        Private slot to synchronize the speed dial settings.
        """
        if self.__handler is not None:
            self.__handler.syncSpeedDial()

    def __syncError(self, message):
        """
        Private slot to handle general synchronization issues.

        @param message error message
        @type str
        """
        self.syncError.emit(message)

    def __syncFinished(self, type_, status, download):
        """
        Private slot to handle a finished synchronization event.

        @param type_ type of the synchronization event (one of "bookmarks",
            "history", "passwords", "useragents" or "speeddial")
        @type str
        @param status flag indicating success
        @type bool
        @param download flag indicating a download of a file
        @type bool
        """
        if status and download:
            if type_ == "bookmarks":
                WebBrowserWindow.bookmarksManager().reload()
            elif type_ == "history":
                WebBrowserWindow.historyManager().reload()
            elif type_ == "passwords":
                WebBrowserWindow.passwordManager().reload()
            elif type_ == "useragents":
                WebBrowserWindow.userAgentsManager().reload()
            elif type_ == "speeddial":
                WebBrowserWindow.speedDial().reload()
        self.syncFinished.emit(type_, status, download)

    def __syncStatus(self, type_, message):
        """
        Private slot to handle a status update of a synchronization event.

        @param type_ type of the synchronization event (one of "bookmarks",
            "history", "passwords", "useragents" or "speeddial")
        @type str
        @param message status message for the event
        @type str
        """
        self.syncMessage.emit(message)
        self.syncStatus.emit(type_, message)

    def close(self):
        """
        Public slot to shut down the synchronization manager.
        """
        if not self.syncEnabled():
            return

        if self.__handler is not None:
            self.__handler.shutdown()
