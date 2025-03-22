# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a MicroPython package installer for devices missing the onboard
'mip' package.
"""

import json

from PyQt6.QtCore import QEventLoop, QObject, QUrl
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from eric7.EricNetwork.EricNetworkProxyFactory import proxyAuthenticationRequired

MicroPythonPackageIndex = "https://micropython.org/pi/v2"


class MipLocalInstaller(QObject):
    """
    Class implementing a MicroPython package installer ('mip' replacement).
    """

    def __init__(self, device, parent=None):
        """
        Constructor

        @param device reference to the connected device
        @type BaseDevice
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

        self.__device = device
        self.__error = ""

        self.__networkManager = QNetworkAccessManager(self)
        self.__networkManager.proxyAuthenticationRequired.connect(
            proxyAuthenticationRequired
        )

        self.__loop = QEventLoop()
        self.__networkManager.finished.connect(self.__loop.quit)

    def __rewriteUrl(self, url, branch=None):
        """
        Private method to rewrite the given URL in case of a Github URL.

        @param url URL to be checked and potentially changed
        @type str
        @param branch branch name (defaults to None)
        @type str (optional)
        @return rewritten URL
        @rtype str
        """
        if url.startswith("github:"):
            urlList = url[7:].split("/")
            if branch is None:
                branch = "HEAD"
            url = (
                "https://raw.githubusercontent.com/"
                + urlList[0]
                + "/"
                + urlList[1]
                + "/"
                + branch
                + "/"
                + "/".join(urlList[2:])
            )

        return url

    def __getFile(self, fileUrl):
        """
        Private method to download the requested file.

        @param fileUrl URL of the requested file
        @type QUrl
        @return package data or an error message and a success flag
        @rtype tuple of (bytes or str, bool)
        """
        request = QNetworkRequest(fileUrl)
        reply = self.__networkManager.get(request)
        if not self.__loop.isRunning():
            self.__loop.exec()
        if reply.error() != QNetworkReply.NetworkError.NoError:
            return reply.errorString(), False
        else:
            return bytes(reply.readAll()), True

    def __installFile(self, fileUrl, targetDir, targetFile):
        """
        Private method to download a file and copy the data to the given target
        directory.

        @param fileUrl URL of the file to be downloaded and installed
        @type str
        @param targetDir target directory on the device
        @type str
        @param targetFile file name on the device
        @type str
        @return flag indicating success
        @rtype  bool
        """
        fileData, ok = self.__getFile(fileUrl)
        if not ok:
            self.__error = fileData
            return False

        try:
            targetFilePath = "{0}/{1}".format(targetDir, targetFile)
            self.__device.ensurePath(targetFilePath.rsplit("/", 1)[0])
            self.__device.putData(targetFilePath, fileData)
        except OSError as err:
            self.__error = err
            return False

        return True

    def __installJson(self, packageJson, version, mpy, target, index):
        """
        Private method to install a package and its dependencies as defined by the
        package JSON file.

        @param packageJson dictionary containing the package data
        @type dict
        @param version package version
        @type str
        @param mpy flag indicating to install as '.mpy' file
        @type bool
        @param target target directory on the device
        @type str
        @param index URL of the package index to be used
        @type str
        @return flag indicating success
        @rtype  bool
        """
        for targetFile, shortHash in packageJson.get("hashes", ()):
            fileUrl = QUrl("{0}/file/{1}/{2}".format(index, shortHash[:2], shortHash))
            if not self.__installFile(fileUrl, target, targetFile):
                return False

        for targetFile, url in packageJson.get("urls", ()):
            if not self.__installFile(
                self.__rewriteUrl(url, branch=version), target, targetFile
            ):
                return False

        for dependency, dependencyVersion in packageJson.get("deps", ()):
            self.installPackage(dependency, dependencyVersion, mpy, target=target)

        return True

    def installPackage(self, package, index=None, target=None, version=None, mpy=True):
        """
        Public method to install a MicroPython package.

        @param package package name
        @type str
        @param index URL of the package index to be used (defaults to None)
        @type str (optional)
        @param target target directory on the device (defaults to None)
        @type str (optional)
        @param version package version (defaults to None)
        @type str (optional)
        @param mpy flag indicating to install as '.mpy' file (defaults to True)
        @type bool (optional)
        @return flag indicating success
        @rtype  bool
        """
        self.__error = ""

        if not bool(index):
            index = MicroPythonPackageIndex
        index = index.rstrip("/")

        if not target:
            libPaths = self.__device.getLibPaths()
            if libPaths and libPaths[0]:
                target = libPaths[0]
            else:
                self.__error = self.tr(
                    "Unable to find 'lib' in sys.path. Please enter a target."
                )
                return False

        if package.startswith(("http://", "https://", "github:")):
            if package.endswith(".py") or package.endswith(".mpy"):
                return self.__installFile(
                    self.__rewriteUrl(package, version),
                    target,
                    package.rsplit("/", 1)[-1],
                )
            else:
                if not package.endswith(".json"):
                    if not package.endswith("/"):
                        package += "/"
                    package += "package.json"
        else:
            if not version:
                version = "latest"

            mpyVersion = "py"
            if mpy and self.__device.getDeviceData("mpy_file_version") > 0:
                mpyVersion = self.__device.getDeviceData("mpy_file_version")

            packageJsonUrl = QUrl(
                "{0}/package/{1}/{2}/{3}.json".format(
                    index, mpyVersion, package, version
                )
            )

        jsonData, ok = self.__getFile(packageJsonUrl)
        if not ok:
            self.__error = jsonData
            return False

        try:
            packageJson = json.loads(jsonData.decode("utf-8"))
        except json.JSONDecodeError as err:
            self.__error = str(err)
            return False

        ok = self.__installJson(packageJson, version, mpy, target, index)
        if not ok:
            self.__error += self.tr("\n\nPackage may be partially installed.")

        return ok

    def errorString(self):
        """
        Public method to get the last error as a string.

        @return latest error
        @rtype str
        """
        return self.__error
