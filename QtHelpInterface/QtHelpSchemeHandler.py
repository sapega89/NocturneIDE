# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a scheme access handler for QtHelp.
"""

import mimetypes
import os

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, QMutex, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestJob, QWebEngineUrlSchemeHandler

from eric7.EricUtilities.EricMutexLocker import EricMutexLocker

QtDocPath = "qthelp://org.qt-project."

ExtensionMap = {
    ".bmp": "image/bmp",
    ".css": "text/css",
    ".gif": "image/gif",
    ".html": "text/html",
    ".htm": "text/html",
    ".ico": "image/x-icon",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".js": "application/x-javascript",
    ".mng": "video/x-mng",
    ".pbm": "image/x-portable-bitmap",
    ".pgm": "image/x-portable-graymap",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".ppm": "image/x-portable-pixmap",
    ".rss": "application/rss+xml",
    ".svg": "image/svg+xml",
    ".svgz": "image/svg+xml",
    ".text": "text/plain",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".txt": "text/plain",
    ".xbm": "image/x-xbitmap",
    ".xml": "text/xml",
    ".xpm": "image/x-xpm",
    ".xsl": "text/xsl",
    ".xhtml": "application/xhtml+xml",
    ".wml": "text/vnd.wap.wml",
    ".wmlc": "application/vnd.wap.wmlc",
}


class QtHelpSchemeHandler(QWebEngineUrlSchemeHandler):
    """
    Class implementing a scheme handler for the qthelp: scheme.
    """

    def __init__(self, engine, parent=None):
        """
        Constructor

        @param engine reference to the help engine
        @type QHelpEngine
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__engine = engine

        self.__replies = []

    def requestStarted(self, job):
        """
        Public method handling the URL request.

        @param job URL request job
        @type QWebEngineUrlRequestJob
        """
        if job.requestUrl().scheme() == "qthelp":
            reply = QtHelpSchemeReply(job, self.__engine)
            reply.closed.connect(lambda: self.__replyClosed(reply))
            self.__replies.append(reply)
            job.reply(reply.mimeType(), reply)
        else:
            job.fail(QWebEngineUrlRequestJob.Error.UrlInvalid)

    def __replyClosed(self, reply):
        """
        Private slot handling the closed signal of a reply.

        @param reply reference to the network reply
        @type QtHelpSchemeReply
        """
        if reply in self.__replies:
            self.__replies.remove(reply)


class QtHelpSchemeReply(QIODevice):
    """
    Class implementing a reply for a requested qthelp: page.

    @signal closed emitted to signal that the web engine has read
        the data
    """

    closed = pyqtSignal()

    def __init__(self, job, engine, parent=None):
        """
        Constructor

        @param job reference to the URL request
        @type QWebEngineUrlRequestJob
        @param engine reference to the help engine
        @type QHelpEngine
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__job = job
        self.__engine = engine
        self.__mutex = QMutex()

        self.__buffer = QBuffer()

        # determine mimetype
        url = self.__job.requestUrl()
        strUrl = url.toString()

        # For some reason the url to load maybe wrong (passed from web engine)
        # though the css file and the references inside should work that way.
        # One possible problem might be that the css is loaded at the same
        # level as the html, thus a path inside the css like
        # (../images/foo.png) might cd out of the virtual folder
        if not self.__engine.findFile(url).isValid() and strUrl.startswith(QtDocPath):
            newUrl = self.__job.requestUrl()
            if not newUrl.path().startswith("/qdoc/"):
                newUrl.setPath("/qdoc" + newUrl.path())
                url = newUrl
                strUrl = url.toString()

        self.__mimeType = mimetypes.guess_type(strUrl)[0]
        if self.__mimeType is None:
            # do our own (limited) guessing
            self.__mimeType = self.__mimeFromUrl(url)

        self.__loadQtHelpPage(url)

    def __loadQtHelpPage(self, url):
        """
        Private method to load the requested QtHelp page.

        @param url URL of the requested page
        @type QUrl
        """
        data = (
            self.__engine.fileData(url)
            if self.__engine.findFile(url).isValid()
            else QByteArray(
                self.tr(
                    """<html>"""
                    """<head><title>Error 404...</title></head>"""
                    """<body><div align="center"><br><br>"""
                    """<h1>The page could not be found</h1><br>"""
                    """<h3>'{0}'</h3></div></body>"""
                    """</html>"""
                )
                .format(url.toString())
                .encode("utf-8")
            )
        )

        with EricMutexLocker(self.__mutex):
            self.__buffer.setData(data)
            self.__buffer.open(QIODevice.OpenModeFlag.ReadOnly)
            self.open(QIODevice.OpenModeFlag.ReadOnly)

        self.readyRead.emit()

    def bytesAvailable(self):
        """
        Public method to get the number of available bytes.

        @return number of available bytes
        @rtype int
        """
        with EricMutexLocker(self.__mutex):
            return self.__buffer.bytesAvailable()

    def readData(self, maxlen):
        """
        Public method to retrieve data from the reply object.

        @param maxlen maximum number of bytes to read
        @type int
        @return string containing the data
        @rtype bytes
        """
        with EricMutexLocker(self.__mutex):
            return self.__buffer.read(maxlen)

    def close(self):
        """
        Public method used to cloase the reply.
        """
        super().close()
        self.closed.emit()

    def __mimeFromUrl(self, url):
        """
        Private method to guess the mime type given an URL.

        @param url URL to guess the mime type from
        @type QUrl
        @return mime type for the given URL
        @rtype str
        """
        path = url.path()
        ext = os.path.splitext(path)[1].lower()
        if ext in ExtensionMap:
            return ExtensionMap[ext]
        else:
            return "application/octet-stream"

    def mimeType(self):
        """
        Public method to get the reply mime type.

        @return mime type of the reply
        @rtype bytes
        """
        return self.__mimeType.encode("utf-8")
