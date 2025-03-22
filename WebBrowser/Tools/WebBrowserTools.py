# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing tool functions for the web browser.
"""

import mimetypes
import os
import re

from PyQt6.QtCore import QBuffer, QByteArray, QCoreApplication, QIODevice, QUrl
from PyQt6.QtGui import QPixmap

from eric7.SystemUtilities import OSUtilities

WebBrowserDataDirectory = {
    "html": os.path.join(os.path.dirname(__file__), "..", "data", "html"),
    "icons": os.path.join(os.path.dirname(__file__), "..", "data", "icons"),
    "js": os.path.join(os.path.dirname(__file__), "..", "data", "javascript"),
}


def readAllFileContents(filename):
    """
    Function to read the string contents of the given file.

    @param filename name of the file
    @type str
    @return contents of the file
    @rtype str
    """
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def containsSpace(string):
    """
    Function to check, if a string contains whitespace characters.

    @param string string to be checked
    @type str
    @return flag indicating the presence of at least one whitespace character
    @rtype bool
    """
    return any(ch.isspace() for ch in string)


def ensureUniqueFilename(name, appendFormat="({0})"):
    """
    Module function to generate an unique file name based on a pattern.

    @param name desired file name
    @type str
    @param appendFormat format pattern to be used to make the unique name
    @type str
    @return unique file name
    @rtype str
    """
    if not os.path.exists(name):
        return name

    tmpFileName = name
    i = 1
    while os.path.exists(tmpFileName):
        tmpFileName = name
        index = tmpFileName.rfind(".")

        appendString = appendFormat.format(i)
        if index == -1:
            tmpFileName += appendString
        else:
            tmpFileName = tmpFileName[:index] + appendString + tmpFileName[index:]
        i += 1

    return tmpFileName


def getFileNameFromUrl(url):
    """
    Module function to generate a file name based on the given URL.

    @param url URL
    @type QUrl
    @return file name
    @rtype str
    """
    fileName = url.toString(
        QUrl.UrlFormattingOption.RemoveFragment
        | QUrl.UrlFormattingOption.RemoveQuery
        | QUrl.UrlFormattingOption.RemoveScheme
        | QUrl.UrlFormattingOption.RemovePort
    )
    if fileName.find("/") != -1:
        pos = fileName.rfind("/")
        fileName = fileName[pos:]
        fileName = fileName.replace("/", "")

    fileName = filterCharsFromFilename(fileName)

    if not fileName:
        fileName = filterCharsFromFilename(url.host().replace(".", "_"))

    return fileName


def filterCharsFromFilename(name):
    """
    Module function to filter illegal characters.

    @param name name to be sanitized
    @type str
    @return sanitized name
    @rtype str
    """
    return (
        name.replace("/", "_")
        .replace("\\", "")
        .replace(":", "")
        .replace("*", "")
        .replace("?", "")
        .replace('"', "")
        .replace("<", "")
        .replace(">", "")
        .replace("|", "")
    )


def pixmapFromByteArray(data):
    """
    Module function to convert a byte array to a pixmap.

    @param data data for the pixmap
    @type bytes or QByteArray
    @return extracted pixmap
    @rtype QPixmap
    """
    pixmap = QPixmap()
    barray = QByteArray.fromBase64(data)
    pixmap.loadFromData(barray)

    return pixmap


def pixmapToByteArray(pixmap):
    """
    Module function to convert a pixmap to a byte array containing the pixmap
    as a PNG encoded as base64.

    @param pixmap pixmap to be converted
    @type QPixmap
    @return byte array containing the pixmap
    @rtype QByteArray
    """
    byteArray = QByteArray()
    buffer = QBuffer(byteArray)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if pixmap.save(buffer, "PNG"):
        return buffer.buffer().toBase64()

    return QByteArray()


def pixmapToDataUrl(pixmap, mimetype="image/png"):
    """
    Module function to convert a pixmap to a data: URL.

    @param pixmap pixmap to be converted
    @type QPixmap
    @param mimetype MIME type to be used
    @type str
    @return data: URL
    @rtype QUrl
    """
    data = bytes(pixmapToByteArray(pixmap)).decode()
    if data:
        return QUrl("data:{0};base64,{1}".format(mimetype, data))
    else:
        return QUrl()


def pixmapFileToDataUrl(pixmapFile, asString=False):
    """
    Module function to load a pixmap file and convert the pixmap to a
    data: URL.

    Note: If the given pixmap file path is not absolute, it is assumed to
    denote a pixmap file in the icons data directory.

    @param pixmapFile file name of the pixmap file
    @type str
    @param asString flag indicating a string representation is requested
    @type bool
    @return data: URL
    @rtype QUrl or str
    """
    if not os.path.isabs(pixmapFile):
        pixmapFile = os.path.join(WebBrowserDataDirectory["icons"], pixmapFile)

    mime = mimetypes.guess_type(pixmapFile, strict=False)[0]
    if mime is None:
        # assume PNG file
        mime = "image/png"
    url = pixmapToDataUrl(QPixmap(pixmapFile), mimetype=mime)

    if asString:
        return url.toString()
    else:
        return url


def getWebEngineVersions():
    """
    Module function to extract the web engine related versions from the default
    user agent string.

    Note: For PyQt 6.3.1 or newer the data is extracted via some Qt functions.

    @return tuple containing the Chromium version, the Chromium security patch
        version and the QtWebEngine version
    @rtype tuple of (str, str, str)
    """
    try:
        from PyQt6.QtWebEngineCore import (  # __IGNORE_WARNING_I10__
            qWebEngineChromiumSecurityPatchVersion,
            qWebEngineChromiumVersion,
            qWebEngineVersion,
        )

        chromiumVersion = qWebEngineChromiumVersion()
        chromiumSecurityVersion = qWebEngineChromiumSecurityPatchVersion()
        webengineVersion = qWebEngineVersion()
    except ImportError:
        # backwards compatibility for PyQt < 6.3.1
        from PyQt6.QtWebEngineCore import QWebEngineProfile  # __IGNORE_WARNING_I10__

        useragent = QWebEngineProfile.defaultProfile().httpUserAgent()
        match = re.search(r"""Chrome/([\d.]+)""", useragent)
        chromiumVersion = (
            match.group(1)
            if match
            else QCoreApplication.translate("WebBrowserTools", "<unknown>")
        )
        match = re.search(r"""QtWebEngine/([\d.]+)""", useragent)
        webengineVersion = (
            match.group(1)
            if match
            else QCoreApplication.translate("WebBrowserTools", "<unknown>")
        )
        chromiumSecurityVersion = ""
        # not available via the user agent string

    return (chromiumVersion, chromiumSecurityVersion, webengineVersion)


def getHtmlPage(pageFileName):
    """
    Module function to load a HTML page.

    Note: If the given HTML file path is not absolute, it is assumed to
    denote a HTML file in the html data directory.

    @param pageFileName file name of the HTML file
    @type str
    @return HTML page
    @rtype str
    """
    if not os.path.isabs(pageFileName):
        pageFileName = os.path.join(WebBrowserDataDirectory["html"], pageFileName)

    return readAllFileContents(pageFileName)


def getJavascript(jsFileName):
    """
    Module function to load a JavaScript source file.

    Note: If the given JavaScript source file path is not absolute, it is
    assumed to denote a JavaScript source file in the javascript data
    directory.

    @param jsFileName file name of the JavaScript source file
    @type str
    @return JavaScript source
    @rtype str
    """
    if not os.path.isabs(jsFileName):
        jsFileName = os.path.join(WebBrowserDataDirectory["js"], jsFileName)

    return readAllFileContents(jsFileName)


def getJquery(jqName):
    """
    Module function to load a JQuery source file.

    Note: If the JQuery file is not found in the javascript data directory and
    the platform is Linux, it is assumed that it is installed system wide in the
    '/usr/share/javascript' directory (e.g. as packaged by Debian).

    @param jqName name of the JQuery library to be loaded (one of 'jquery' or
        'jquery-ui')
    @type str
    @return JQuery source
    @rtype str
    """
    jsFileName = os.path.join(WebBrowserDataDirectory["js"], jqName + ".js")
    if not os.path.exists(jsFileName) and (
        OSUtilities.isLinuxPlatform() or OSUtilities.isFreeBsdPlatform()
    ):
        if jqName == "jquery":
            jsFileName = "/usr/share/javascript/jquery/jquery.min.js"
        elif jqName == "jquery-ui":
            jsFileName = "/usr/share/javascript/jquery-ui/jquery-ui.min.js"

    return readAllFileContents(jsFileName)
