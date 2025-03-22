# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the code coverage request handler of the eric-ide server.
"""

from coverage import Coverage
from coverage.misc import CoverageException

from eric7.SystemUtilities import FileSystemUtilities

from .EricRequestCategory import EricRequestCategory
from .EricServerBaseRequestHandler import EricServerBaseRequestHandler


class EricServerCoverageRequestHandler(EricServerBaseRequestHandler):
    """
    Class implementing the code coverage request handler of the eric-ide server.
    """

    def __init__(self, server):
        """
        Constructor

        @param server reference to the eric-ide server object
        @type EricServer
        """
        super().__init__(server)

        self._category = EricRequestCategory.Coverage

        self._requestMethodMapping = {
            "LoadData": self.__loadCoverageData,
            "AnalyzeFile": self.__analyzeFile,
            "AnalyzeFiles": self.__analyzeFiles,
            "AnalyzeDirectory": self.__analyzeDirectory,
        }

        self.__cover = None

    ############################################################################
    ## Coverage related methods below
    ############################################################################

    def __loadCoverageData(self, params):
        """
        Private method to load the data collected by a code coverage run.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        if self.__cover is not None:
            del self.__cover
            self.__cover = None

        try:
            self.__cover = Coverage(data_file=params["data_file"])
            self.__cover.load()
            if params["exclude"]:
                self.__cover.exclude(params["exclude"])
            return {"ok": True}
        except CoverageException as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __analyzeFile(self, params):
        """
        Private method to analyze a single file.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        if self.__cover is None:
            return {
                "ok": False,
                "error": "Coverage data has to be loaded first.",
            }

        try:
            return {
                "ok": True,
                "result": self.__cover.analysis2(params["filename"]),
            }
        except CoverageException as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __analyzeFiles(self, params):
        """
        Private method to analyze a list of files.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        if self.__cover is None:
            return {
                "ok": False,
                "error": "Coverage data has to be loaded first.",
            }

        try:
            return {
                "ok": True,
                "results": [self.__cover.analysis2(f) for f in params["filenames"]],
            }
        except CoverageException as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __analyzeDirectory(self, params):
        """
        Private method to analyze files of a directory tree.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        if self.__cover is None:
            return {
                "ok": False,
                "error": "Coverage data has to be loaded first.",
            }

        files = FileSystemUtilities.direntries(params["directory"], True, "*.py", False)

        try:
            return {
                "ok": True,
                "results": [self.__cover.analysis2(f) for f in files],
            }
        except CoverageException as err:
            return {
                "ok": False,
                "error": str(err),
            }
