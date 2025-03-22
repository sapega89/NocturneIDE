# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a synchronization handler using FTP.
"""

import contextlib
import ftplib  # secok
import io
import pathlib

from PyQt6.QtCore import QByteArray, QCoreApplication, QTimer, pyqtSignal

from eric7 import Preferences
from eric7.EricCore import EricPreferences
from eric7.EricNetwork.EricFtp import EricFtp, EricFtpProxyError, EricFtpProxyType
from eric7.Utilities.FtpUtilities import FtpDirLineParser, FtpDirLineParserError
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .SyncHandler import SyncHandler


class FtpSyncHandler(SyncHandler):
    """
    Class implementing a synchronization handler using FTP.

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

        self.__state = "idle"
        self.__forceUpload = False
        self.__connected = False

        self.__remoteFilesFound = {}

    def initialLoadAndCheck(self, forceUpload):
        """
        Public method to do the initial check.

        @param forceUpload flag indicating a forced upload of the files
        @type bool
        """
        if not Preferences.getWebBrowser("SyncEnabled"):
            return

        self.__state = "initializing"
        self.__forceUpload = forceUpload

        self.__dirLineParser = FtpDirLineParser()
        self.__remoteFilesFound = {}

        self.__idleTimer = QTimer(self)
        self.__idleTimer.setInterval(
            Preferences.getWebBrowser("SyncFtpIdleTimeout") * 1000
        )
        self.__idleTimer.timeout.connect(self.__idleTimeout)

        self.__ftp = EricFtp()

        # do proxy setup
        proxyType = (
            EricFtpProxyType.NO_PROXY
            if not EricPreferences.getNetworkProxy("UseProxy")
            else EricPreferences.getNetworkProxy("ProxyType/Ftp")
        )
        if proxyType != EricFtpProxyType.NO_PROXY:
            self.__ftp.setProxy(
                proxyType,
                EricPreferences.getNetworkProxy("ProxyHost/Ftp"),
                EricPreferences.getNetworkProxy("ProxyPort/Ftp"),
            )
            if proxyType != EricFtpProxyType.NON_AUTHORIZING:
                self.__ftp.setProxyAuthentication(
                    EricPreferences.getNetworkProxy("ProxyUser/Ftp"),
                    EricPreferences.getNetworkProxy("ProxyPassword/Ftp"),
                    EricPreferences.getNetworkProxy("ProxyAccount/Ftp"),
                )

        QTimer.singleShot(0, self.__doFtpCommands)

    def __doFtpCommands(self):
        """
        Private slot executing the sequence of FTP commands.
        """
        try:
            ok = self.__connectAndLogin()
            if ok:
                self.__changeToStore()
                self.__ftp.retrlines("LIST", self.__dirListCallback)
                self.__initialSync()
                self.__state = "idle"
                self.__idleTimer.start()
        except ftplib.all_errors + (EricFtpProxyError,) as err:  # noqa: M530
            self.syncError.emit(str(err))

    def __connectAndLogin(self):
        """
        Private method to connect to the FTP server and log in.

        @return flag indicating a successful log in
        @rtype bool
        """
        self.__ftp.connect(
            Preferences.getWebBrowser("SyncFtpServer"),
            Preferences.getWebBrowser("SyncFtpPort"),
            timeout=5,
        )
        self.__ftp.login(
            Preferences.getWebBrowser("SyncFtpUser"),
            Preferences.getWebBrowser("SyncFtpPassword"),
        )
        self.__connected = True
        return True

    def __changeToStore(self):
        """
        Private slot to change to the storage directory.

        This action will create the storage path on the server, if it
        does not exist. Upon return, the current directory of the server
        is the sync directory.
        """
        storePathList = (
            Preferences.getWebBrowser("SyncFtpPath").replace("\\", "/").split("/")
        )
        if storePathList[0] == "":
            storePathList.pop(0)
        while storePathList:
            path = storePathList[0]
            try:
                self.__ftp.cwd(path)
            except ftplib.error_perm as err:
                code = err.args[0].strip()[:3]
                if code == "550":
                    # path does not exist, create it
                    self.__ftp.mkd(path)
                    self.__ftp.cwd(path)
                else:
                    raise
            storePathList.pop(0)

    def __dirListCallback(self, line):
        """
        Private slot handling the receipt of directory listing lines.

        @param line the received line of the directory listing
        @type str
        """
        try:
            urlInfo = self.__dirLineParser.parseLine(line)
        except FtpDirLineParserError:
            # silently ignore parser errors
            urlInfo = None

        if (
            urlInfo
            and urlInfo.isValid()
            and urlInfo.isFile()
            and urlInfo.name() in self._remoteFiles.values()
        ):
            self.__remoteFilesFound[urlInfo.name()] = urlInfo.lastModified()

        QCoreApplication.processEvents()

    def __downloadFile(self, type_, fileName, timestamp):
        """
        Private method to downlaod the given file.

        @param type_ type of the synchronization event (one of
            "bookmarks", "history", "passwords", "useragents" or "speeddial")
        @type str
        @param fileName name of the file to be downloaded
        @type str
        @param timestamp time stamp in seconds of the file to be downloaded
        @type int
        """
        self.syncStatus.emit(type_, self._messages[type_]["RemoteExists"])
        buffer = io.BytesIO()
        try:
            self.__ftp.retrbinary(
                "RETR {0}".format(self._remoteFiles[type_]),
                lambda x: self.__downloadFileCallback(buffer, x),
            )
            ok, error = self.writeFile(
                QByteArray(buffer.getvalue()), fileName, type_, timestamp
            )
            if not ok:
                self.syncStatus.emit(type_, error)
            self.syncFinished.emit(type_, ok, True)
        except ftplib.all_errors as err:
            self.syncStatus.emit(type_, str(err))
            self.syncFinished.emit(type_, False, True)

    def __downloadFileCallback(self, buffer, data):
        """
        Private method receiving the downloaded data.

        @param buffer reference to the buffer
        @type io.BytesIO
        @param data byte string to store in the buffer
        @type bytes
        @return number of bytes written to the buffer
        @rtype int
        """
        res = buffer.write(data)
        QCoreApplication.processEvents()
        return res

    def __uploadFile(self, type_, fileName):
        """
        Private method to upload the given file.

        @param type_ type of the synchronization event (one of "bookmarks",
            "history", "passwords", "useragents" or "speeddial")
        @type str
        @param fileName name of the file to be uploaded
        @type str
        @return flag indicating success
        @rtype bool
        """
        res = False
        data = self.readFile(fileName, type_)
        if data.isEmpty():
            self.syncStatus.emit(type_, self._messages[type_]["LocalMissing"])
            self.syncFinished.emit(type_, False, False)
        else:
            buffer = io.BytesIO(data.data())
            try:
                self.__ftp.storbinary(
                    "STOR {0}".format(self._remoteFiles[type_]),
                    buffer,
                    callback=lambda _x: QCoreApplication.processEvents(),
                )
                self.syncFinished.emit(type_, True, False)
                res = True
            except ftplib.all_errors as err:
                self.syncStatus.emit(type_, str(err))
                self.syncFinished.emit(type_, False, False)
        return res

    def __initialSyncFile(self, type_, fileName):
        """
        Private method to do the initial synchronization of the given file.

        @param type_ type of the synchronization event (one of "bookmarks",
            "history", "passwords", "useragents" or "speeddial")
        @type str
        @param fileName name of the file to be synchronized
        @type str
        """
        if (
            not self.__forceUpload
            and self._remoteFiles[type_] in self.__remoteFilesFound
        ):
            if (
                not pathlib.Path(fileName).exists()
                or pathlib.Path(fileName).stat().st_mtime
                < self.__remoteFilesFound[self._remoteFiles[type_].toSecsSinceEpoch()]
            ):
                self.__downloadFile(
                    type_,
                    fileName,
                    self.__remoteFilesFound[self._remoteFiles[type_]].toTime_t(),
                )
            else:
                self.syncStatus.emit(type_, self.tr("No synchronization required."))
                self.syncFinished.emit(type_, True, True)
        else:
            if self._remoteFiles[type_] not in self.__remoteFilesFound:
                self.syncStatus.emit(type_, self._messages[type_]["RemoteMissing"])
            else:
                self.syncStatus.emit(type_, self._messages[type_]["LocalNewer"])
            self.__uploadFile(type_, fileName)

    def __initialSync(self):
        """
        Private slot to do the initial synchronization.
        """
        # Bookmarks
        if Preferences.getWebBrowser("SyncBookmarks"):
            self.__initialSyncFile(
                "bookmarks", WebBrowserWindow.bookmarksManager().getFileName()
            )

        # History
        if Preferences.getWebBrowser("SyncHistory"):
            self.__initialSyncFile(
                "history", WebBrowserWindow.historyManager().getFileName()
            )

        # Passwords
        if Preferences.getWebBrowser("SyncPasswords"):
            self.__initialSyncFile(
                "passwords", WebBrowserWindow.passwordManager().getFileName()
            )

        # User Agent Settings
        if Preferences.getWebBrowser("SyncUserAgents"):
            self.__initialSyncFile(
                "useragents", WebBrowserWindow.userAgentsManager().getFileName()
            )

        # Speed Dial Settings
        if Preferences.getWebBrowser("SyncSpeedDial"):
            self.__initialSyncFile(
                "speeddial", WebBrowserWindow.speedDial().getFileName()
            )

        self.__forceUpload = False

    def __syncFile(self, type_, fileName):
        """
        Private method to synchronize the given file.

        @param type_ type of the synchronization event (one of "bookmarks",
            "history", "passwords", "useragents" or "speeddial")
        @type str
        @param fileName name of the file to be synchronized
        @type str
        """
        if self.__state == "initializing":
            return

        # use idle timeout to check, if we are still connected
        if self.__connected:
            self.__idleTimeout()
        if not self.__connected or self.__ftp.sock is None:
            ok = self.__connectAndLogin()
            if not ok:
                self.syncStatus.emit(type_, self.tr("Cannot log in to FTP host."))
                return

        # upload the changed file
        self.__state = "uploading"
        self.syncStatus.emit(type_, self._messages[type_]["Uploading"])
        if self.__uploadFile(type_, fileName):
            self.syncStatus.emit(type_, self.tr("Synchronization finished."))
        self.__state = "idle"

    def syncBookmarks(self):
        """
        Public method to synchronize the bookmarks.
        """
        self.__syncFile("bookmarks", WebBrowserWindow.bookmarksManager().getFileName())

    def syncHistory(self):
        """
        Public method to synchronize the history.
        """
        self.__syncFile("history", WebBrowserWindow.historyManager().getFileName())

    def syncPasswords(self):
        """
        Public method to synchronize the passwords.
        """
        self.__syncFile("passwords", WebBrowserWindow.passwordManager().getFileName())

    def syncUserAgents(self):
        """
        Public method to synchronize the user agents.
        """
        self.__syncFile(
            "useragents", WebBrowserWindow.userAgentsManager().getFileName()
        )

    def syncSpeedDial(self):
        """
        Public method to synchronize the speed dial data.
        """
        self.__syncFile("speeddial", WebBrowserWindow.speedDial().getFileName())

    def shutdown(self):
        """
        Public method to shut down the handler.
        """
        if self.__idleTimer.isActive():
            self.__idleTimer.stop()

        with contextlib.suppress(ftplib.all_errors):
            if self.__connected:
                self.__ftp.quit()
        self.__connected = False

    def __idleTimeout(self):
        """
        Private slot to prevent a disconnect from the server.
        """
        if self.__state == "idle" and self.__connected:
            try:
                self.__ftp.voidcmd("NOOP")
            except ftplib.Error as err:
                code = err.args[0].strip()[:3]
                if code == "421":
                    self.__connected = False
            except OSError:
                self.__connected = False
