# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the GreaseMonkey script.
"""

import enum
import re

from PyQt6.QtCore import (
    QByteArray,
    QCryptographicHash,
    QObject,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest
from PyQt6.QtWebEngineCore import QWebEngineScript

from ..Tools.DelayedFileWatcher import DelayedFileWatcher
from ..WebBrowserPage import WebBrowserPage
from ..WebBrowserWindow import WebBrowserWindow
from .GreaseMonkeyDownloader import GreaseMonkeyDownloader, GreaseMonkeyDownloadType
from .GreaseMonkeyJavaScript import bootstrap_js, values_js


class GreaseMonkeyScriptStartPoint(enum.Enum):
    """
    Class defining the script start points.
    """

    DocumentStart = 0
    DocumentEnd = 1
    DocumentIdle = 2


class GreaseMonkeyScript(QObject):
    """
    Class implementing the GreaseMonkey script.

    @signal scriptChanged() emitted to indicate a script change
    @signal updatingChanged(bool) emitted to indicate a change of the
        updating state
    """

    scriptChanged = pyqtSignal()
    updatingChanged = pyqtSignal(bool)

    def __init__(self, manager, path):
        """
        Constructor

        @param manager reference to the manager object
        @type GreaseMonkeyManager
        @param path path of the Javascript file
        @type str
        """
        super().__init__(manager)

        self.__manager = manager
        self.__fileWatcher = DelayedFileWatcher(parent=None)

        self.__name = ""
        self.__namespace = "GreaseMonkeyNS"
        self.__description = ""
        self.__version = ""

        self.__include = []
        self.__exclude = []
        self.__require = []

        self.__icon = QIcon()
        self.__iconUrl = QUrl()
        self.__downloadUrl = QUrl()
        self.__updateUrl = QUrl()
        self.__startAt = GreaseMonkeyScriptStartPoint.DocumentEnd

        self.__script = ""
        self.__fileName = path
        self.__enabled = True
        self.__valid = False
        self.__noFrames = False

        self.__updating = False

        self.__downloaders = []
        self.__iconReplies = []

        self.__parseScript()

        self.__fileWatcher.delayedFileChanged.connect(self.__watchedFileChanged)

    def isValid(self):
        """
        Public method to check the validity of the script.

        @return flag indicating a valid script
        @rtype bool
        """
        return self.__valid

    def name(self):
        """
        Public method to get the name of the script.

        @return name of the script
        @rtype str
        """
        return self.__name

    def nameSpace(self):
        """
        Public method to get the name space of the script.

        @return name space of the script
        @rtype str
        """
        return self.__namespace

    def fullName(self):
        """
        Public method to get the full name of the script.

        @return full name of the script
        @rtype str
        """
        return "{0}/{1}".format(self.__namespace, self.__name)

    def description(self):
        """
        Public method to get the description of the script.

        @return description of the script
        @rtype str
        """
        return self.__description

    def version(self):
        """
        Public method to get the version of the script.

        @return version of the script
        @rtype str
        """
        return self.__version

    def icon(self):
        """
        Public method to get the icon of the script.

        @return script icon
        @rtype QIcon
        """
        return self.__icon

    def iconUrl(self):
        """
        Public method to get the icon URL of the script.

        @return icon URL of the script
        @rtype QUrl
        """
        return QUrl(self.__iconUrl)

    def downloadUrl(self):
        """
        Public method to get the download URL of the script.

        @return download URL of the script
        @rtype QUrl
        """
        return QUrl(self.__downloadUrl)

    def updateUrl(self):
        """
        Public method to get the update URL of the script.

        @return update URL of the script
        @rtype QUrl
        """
        return QUrl(self.__updateUrl)

    def startAt(self):
        """
        Public method to get the start point of the script.

        @return start point of the script
        @rtype GreaseMonkeyScriptStartPoint
        """
        return self.__startAt

    def noFrames(self):
        """
        Public method to get the noFrames flag.

        @return flag indicating to not run on sub frames
        @rtype bool
        """
        return self.__noFrames

    def isEnabled(self):
        """
        Public method to check, if the script is enabled.

        @return flag indicating an enabled state
        @rtype bool
        """
        return self.__enabled and self.__valid

    def setEnabled(self, enable):
        """
        Public method to enable a script.

        @param enable flag indicating the new enabled state
        @type bool
        """
        self.__enabled = enable

    def include(self):
        """
        Public method to get the list of included URLs.

        @return list of included URLs
        @rtype list of str
        """
        return self.__include[:]

    def exclude(self):
        """
        Public method to get the list of excluded URLs.

        @return list of excluded URLs
        @rtype list of str
        """
        return self.__exclude[:]

    def require(self):
        """
        Public method to get the list of required scripts.

        @return list of required scripts
        @rtype list of str
        """
        return self.__require[:]

    def fileName(self):
        """
        Public method to get the path of the Javascript file.

        @return path of the Javascript file
        @rtype str
        """
        return self.__fileName

    def isUpdating(self):
        """
        Public method to get the updating flag.

        @return updating flag
        @rtype bool
        """
        return self.__updating

    @pyqtSlot(str)
    def __watchedFileChanged(self, fileName):
        """
        Private slot handling changes of the script file.

        @param fileName path of the script file
        @type str
        """
        if self.__fileName == fileName:
            self.__reloadScript()

    def __parseScript(self):
        """
        Private method to parse the given script and populate the data
        structure.
        """
        self.__name = ""
        self.__namespace = "GreaseMonkeyNS"
        self.__description = ""
        self.__version = ""

        self.__include = []
        self.__exclude = []
        self.__require = []

        self.__icon = QIcon()
        self.__iconUrl = QUrl()
        self.__downloadUrl = QUrl()
        self.__updateUrl = QUrl()
        self.__startAt = GreaseMonkeyScriptStartPoint.DocumentEnd

        self.__script = ""
        self.__enabled = True
        self.__valid = False
        self.__noFrames = False

        try:
            with open(self.__fileName, "r", encoding="utf-8") as f:
                fileData = f.read()
        except OSError:
            # silently ignore because it shouldn't happen
            return

        if self.__fileName not in self.__fileWatcher.files():
            self.__fileWatcher.addPath(self.__fileName)

        rx = re.compile(r"""// ==UserScript==(.*)// ==/UserScript==""", re.DOTALL)
        match = rx.search(fileData)
        if match is None:
            # invalid script file
            return

        metaDataBlock = match.group(1).strip()
        if metaDataBlock == "":
            # invalid script file
            return

        for line in metaDataBlock.splitlines():
            if not line.strip():
                continue

            if not line.startswith("// @"):
                continue

            line = line[3:].replace("\t", " ")
            index = line.find(" ")

            key = line[:index].strip()
            value = line[index + 1 :].strip() if index > 0 else ""

            if not key:
                continue

            if key == "@name":
                self.__name = value

            elif key == "@namespace":
                self.__namespace = value

            elif key == "@description":
                self.__description = value

            elif key == "@version":
                self.__version = value

            elif key in ["@include", "@match"]:
                self.__include.append(value)

            elif key in ["@exclude", "@exclude_match"]:
                self.__exclude.append(value)

            elif key == "@require":
                self.__require.append(value)

            elif key == "@run-at":
                if value == "document-end":
                    self.__startAt = GreaseMonkeyScriptStartPoint.DocumentEnd
                elif value == "document-start":
                    self.__startAt = GreaseMonkeyScriptStartPoint.DocumentStart
                elif value == "document-idle":
                    self.__startAt = GreaseMonkeyScriptStartPoint.DocumentIdle

            elif key == "@downloadURL" and self.__downloadUrl.isEmpty():
                self.__downloadUrl = QUrl(value)

            elif key == "@updateURL" and self.__updateUrl.isEmpty():
                self.__updateUrl = QUrl(value)

            elif key == "@icon":
                self.__iconUrl = QUrl(value)

            elif key == "@noframes":
                self.__noFrames = True

        self.__iconUrl = self.__downloadUrl.resolved(self.__iconUrl)

        if not self.__include:
            self.__include.append("*")

        nspace = bytes(
            QCryptographicHash.hash(
                QByteArray(self.fullName().encode("utf-8")),
                QCryptographicHash.Algorithm.Md4,
            ).toHex()
        ).decode("ascii")
        valuesScript = values_js.format(nspace)
        self.__script = "(function(){{{0}\n{1}\n{2}\n}})();".format(
            valuesScript, self.__manager.requireScripts(self.__require), fileData
        )
        self.__valid = True

        self.__downloadIcon()
        self.__downloadRequires()

    def webScript(self):
        """
        Public method to create a script object.

        @return prepared script object
        @rtype QWebEngineScript
        """
        script = QWebEngineScript()
        script.setSourceCode("{0}\n{1}".format(bootstrap_js, self.__script))
        script.setName(self.fullName())
        script.setWorldId(WebBrowserPage.SafeJsWorld)
        script.setRunsOnSubFrames(not self.__noFrames)
        return script

    def updateScript(self):
        """
        Public method to updated the script.
        """
        if not self.__downloadUrl.isValid() or self.__updating:
            return

        self.__updating = True
        self.updatingChanged.emit(self.__updating)

        downloader = GreaseMonkeyDownloader(
            self.__downloadUrl,
            self.__manager,
            GreaseMonkeyDownloadType.MainScript,
        )
        downloader.updateScript(self.__fileName)
        downloader.finished.connect(lambda: self.__downloaderFinished(downloader))
        downloader.error.connect(lambda: self.__downloaderError(downloader))
        self.__downloaders.append(downloader)

        self.__downloadRequires()

    def __downloaderFinished(self, downloader):
        """
        Private slot to handle a finished download.

        @param downloader reference to the downloader object
        @type GreaseMonkeyDownloader
        """
        if downloader in self.__downloaders:
            self.__downloaders.remove(downloader)
        self.__updating = False
        self.updatingChanged.emit(self.__updating)

    def __downloaderError(self, downloader):
        """
        Private slot to handle a downloader error.

        @param downloader reference to the downloader object
        @type GreaseMonkeyDownloader
        """
        if downloader in self.__downloaders:
            self.__downloaders.remove(downloader)
        self.__updating = False
        self.updatingChanged.emit(self.__updating)

    def __reloadScript(self):
        """
        Private method to reload the script.
        """
        self.__parseScript()

        self.__manager.removeScript(self, False)
        self.__manager.addScript(self)

        self.scriptChanged.emit()

    def __downloadRequires(self):
        """
        Private method to download the required scripts.
        """
        for urlStr in self.__require:
            if not self.__manager.requireScripts([urlStr]):
                downloader = GreaseMonkeyDownloader(
                    QUrl(urlStr),
                    self.__manager,
                    GreaseMonkeyDownloadType.RequireScript,
                )
                downloader.finished.connect(
                    lambda: self.__requireDownloaded(downloader)
                )
                downloader.error.connect(
                    lambda: self.__requireDownloadError(downloader)
                )
                self.__downloaders.append(downloader)

    def __requireDownloaded(self, downloader):
        """
        Private slot to handle a finished download of a required script.

        @param downloader reference to the downloader object
        @type GreaseMonkeyDownloader
        """
        if downloader in self.__downloaders:
            self.__downloaders.remove(downloader)

        self.__reloadScript()

    def __requireDownloadError(self, downloader):
        """
        Private slot to handle a downloader error.

        @param downloader reference to the downloader object
        @type GreaseMonkeyDownloader
        """
        if downloader in self.__downloaders:
            self.__downloaders.remove(downloader)

    def __downloadIcon(self):
        """
        Private slot to download the script icon.
        """
        if self.__iconUrl.isValid():
            request = QNetworkRequest(self.__iconUrl)
            reply = WebBrowserWindow.networkManager().get(request)
            reply.finished.connect(lambda: self.__iconDownloaded(reply))
            self.__iconReplies.append(reply)

    def __iconDownloaded(self, reply):
        """
        Private slot to handle a finished download of a script icon.

        @param reply reference to the network reply
        @type QNetworkReply
        """
        if reply in self.__iconReplies:
            self.__iconReplies.remove(reply)

        reply.deleteLater()
        if reply.error() == QNetworkReply.NetworkError.NoError:
            self.__icon = QPixmap.fromImage(QImage.fromData(reply.readAll()))
