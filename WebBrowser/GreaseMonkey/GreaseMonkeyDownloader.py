# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the downloader for GreaseMonkey scripts.
"""

import enum
import os
import pathlib

from PyQt6.QtCore import QObject, QSettings, pyqtSignal, pyqtSlot
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest

from eric7.WebBrowser.Tools import WebBrowserTools
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow


class GreaseMonkeyDownloadType(enum.Enum):
    """
    Class defining the download types.
    """

    MainScript = 1
    RequireScript = 2


class GreaseMonkeyDownloader(QObject):
    """
    Class implementing the downloader for GreaseMonkey scripts.

    @signal finished(fileName) emitted to indicate the end of a script download
        (str)
    @signal error() emitted to indicate a script download error
    """

    finished = pyqtSignal(str)
    error = pyqtSignal()

    def __init__(self, url, manager, mode):
        """
        Constructor

        @param url URL to download script from
        @type QUrl
        @param manager reference to the GreaseMonkey manager
        @type GreaseMonkeyManager
        @param mode download mode
        @type GreaseMonkeyDownloadType
        """
        super().__init__()

        self.__manager = manager

        self.__reply = WebBrowserWindow.networkManager().get(QNetworkRequest(url))
        if mode == GreaseMonkeyDownloadType.MainScript:
            self.__reply.finished.connect(self.__scriptDownloaded)
        else:
            self.__reply.finished.connect(self.__requireDownloaded)

        self.__fileName = ""

    def updateScript(self, fileName):
        """
        Public method to set the file name for the script to be downloaded.

        @param fileName file name for the script
        @type str
        """
        self.__fileName = fileName

    @pyqtSlot()
    def __scriptDownloaded(self):
        """
        Private slot to handle the finished download of a script.
        """
        self.deleteLater()
        self.__reply.deleteLater()

        if self.__reply.error() != QNetworkReply.NetworkError.NoError:
            self.error.emit()
            return

        response = bytes(self.__reply.readAll()).decode()

        if "// ==UserScript==" not in response:
            self.error.emit()
            return

        if not self.__fileName:
            filePath = os.path.join(
                self.__manager.scriptsDirectory(),
                WebBrowserTools.getFileNameFromUrl(self.__reply.url()),
            )
            self.__fileName = WebBrowserTools.ensureUniqueFilename(filePath)

        try:
            with open(self.__fileName, "w", encoding="utf-8") as f:
                f.write(response)
        except OSError:
            self.error.emit()
            return

        self.finished.emit(self.__fileName)

    @pyqtSlot()
    def __requireDownloaded(self):
        """
        Private slot to handle the finished download of a required script.
        """
        self.deleteLater()
        self.__reply.deleteLater()

        if self.__reply.error() != QNetworkReply.NetworkError.NoError:
            self.error.emit()
            return

        response = bytes(self.__reply.readAll()).decode()

        if not response:
            self.error.emit()
            return

        settings = QSettings(
            os.path.join(self.__manager.requireScriptsDirectory(), "requires.ini"),
            QSettings.Format.IniFormat,
        )
        settings.beginGroup("Files")

        if not self.__fileName:
            self.__fileName = settings.value(self.__reply.request().url().toString())
            if not self.__fileName:
                name = pathlib.Path(self.__reply.request().url().path()).name
                if not name:
                    name = "require.js"
                elif not name.endswith(".js"):
                    name += ".js"
                filePath = os.path.join(self.__manager.requireScriptsDirectory(), name)
                self.__fileName = WebBrowserTools.ensureUniqueFilename(filePath, "{0}")
            if not pathlib.Path(self.__fileName).is_absolute():
                self.__fileName = os.path.join(
                    self.__manager.requireScriptsDirectory(), self.__fileName
                )

        try:
            with open(self.__fileName, "w", encoding="utf-8") as f:
                f.write(response)
        except OSError:
            self.error.emit()
            return

        settings.setValue(
            self.__reply.request().url().toString(), pathlib.Path(self.__fileName).name
        )

        self.finished.emit(self.__fileName)
