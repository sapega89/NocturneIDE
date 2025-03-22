# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the code coverage interface to the eric-ide server.
"""

import contextlib

from PyQt6.QtCore import QEventLoop, QObject

from eric7.RemoteServer.EricRequestCategory import EricRequestCategory
from eric7.SystemUtilities import FileSystemUtilities


class EricServerCoverageError(Exception):
    """
    Class defining a substitute exception for coverage errors of the server.
    """

    pass


class EricServerCoverageInterface(QObject):
    """
    Class implementing the code coverage interface to the eric-ide server.
    """

    def __init__(self, serverInterface):
        """
        Constructor

        @param serverInterface reference to the eric-ide server interface
        @type EricServerInterface
        """
        super().__init__(parent=serverInterface)

        self.__serverInterface = serverInterface

    def loadCoverageData(self, dataFile, excludePattern=""):
        """
        Public method to tell the server to load the coverage data for a later analysis.

        @param dataFile name of the data file to be loaded
        @type str
        @param excludePattern regular expression determining files to be excluded
            (defaults to "")
        @type str (optional)
        @return tuple containing a success flag and an error message
        @rtype tuple of (bool, str)
        """
        loop = QEventLoop()
        ok = False
        error = ""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error

            if reply == "LoadData":
                ok = params["ok"]
                with contextlib.suppress(KeyError):
                    error = params["error"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.Coverage,
                request="LoadData",
                params={
                    "data_file": FileSystemUtilities.plainFileName(dataFile),
                    "exclude": excludePattern,
                },
                callback=callback,
            )

            loop.exec()
            return ok, error

        else:
            return False, "Not connected to an 'eric-ide' server."

    def analyzeFile(self, filename):
        """
        Public method to analyze the code coverage of one file.

        @param filename name of the file to be analyzed
        @type str
        @return list containing coverage result as reported by Coverage.analysis2()
        @rtype list of [str, list of int, list of int, list of int, str]
        @exception EricServerCoverageError raised to indicate a coverage exception
        @exception OSError raised to indicate that server is not connected
        """
        loop = QEventLoop()
        ok = False
        error = ""
        result = None

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error, result

            if reply == "AnalyzeFile":
                ok = params["ok"]
                if ok:
                    result = params["result"]
                else:
                    error = params["error"]
                loop.quit()

        if not self.__serverInterface.isServerConnected():
            raise OSError("Not connected to an 'eric-ide' server.")

        else:
            self.__serverInterface.sendJson(
                category=EricRequestCategory.Coverage,
                request="AnalyzeFile",
                params={"filename": FileSystemUtilities.plainFileName(filename)},
                callback=callback,
            )

            loop.exec()
            if not ok:
                raise EricServerCoverageError(error)

            return result

    def analyzeFiles(self, filenames):
        """
        Public method to analyze the code coverage of a list of files.

        @param filenames list of file names to be analyzed
        @type str
        @return lists containing coverage results as reported by Coverage.analysis2()
        @rtype list of [list of [str, list of int, list of int, list of int, str]]
        @exception EricServerCoverageError raised to indicate a coverage exception
        @exception OSError raised to indicate that server is not connected
        """
        loop = QEventLoop()
        ok = False
        error = ""
        result = None

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error, result

            if reply == "AnalyzeFiles":
                ok = params["ok"]
                if ok:
                    result = params["results"]
                else:
                    error = params["error"]
                loop.quit()

        if not self.__serverInterface.isServerConnected():
            raise OSError("Not connected to an 'eric-ide' server.")

        else:
            self.__serverInterface.sendJson(
                category=EricRequestCategory.Coverage,
                request="AnalyzeFiles",
                params={
                    "filenames": [
                        FileSystemUtilities.plainFileName(f) for f in filenames
                    ]
                },
                callback=callback,
            )

            loop.exec()
            if not ok:
                raise EricServerCoverageError(error)

            return result

    def analyzeDirectory(self, directory):
        """
        Public method to analyze the code coverage of a directory.

        @param directory directory name to be analyzed
        @type str
        @return lists containing coverage results as reported by Coverage.analysis2()
        @rtype list of [list of [str, list of int, list of int, list of int, str]]
        @exception EricServerCoverageError raised to indicate a coverage exception
        @exception OSError raised to indicate that server is not connected
        """
        loop = QEventLoop()
        ok = False
        error = ""
        result = None

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error, result

            if reply == "AnalyzeDirectory":
                ok = params["ok"]
                if ok:
                    result = params["results"]
                else:
                    error = params["error"]
                loop.quit()

        if not self.__serverInterface.isServerConnected():
            raise OSError("Not connected to an 'eric-ide' server.")

        else:
            self.__serverInterface.sendJson(
                category=EricRequestCategory.Coverage,
                request="AnalyzeDirectory",
                params={"directory": FileSystemUtilities.plainFileName(directory)},
                callback=callback,
            )

            loop.exec()
            if not ok:
                raise EricServerCoverageError(error)

            return result
