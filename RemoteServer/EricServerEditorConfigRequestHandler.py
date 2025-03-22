# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the editor config request handler of the eric-ide server.
"""

import editorconfig

from .EricRequestCategory import EricRequestCategory
from .EricServerBaseRequestHandler import EricServerBaseRequestHandler


class EricServerEditorConfigRequestHandler(EricServerBaseRequestHandler):
    """
    Class implementing the editor config request handler of the eric-ide server.
    """

    def __init__(self, server):
        """
        Constructor

        @param server reference to the eric-ide server object
        @type EricServer
        """
        super().__init__(server)

        self._category = EricRequestCategory.EditorConfig

        self._requestMethodMapping = {
            "LoadEditorConfig": self.__loadEditorConfig,
        }

    ############################################################################
    ## Editor Config related methods below
    ############################################################################

    def __loadEditorConfig(self, params):
        """
        Private method to load the EditorConfig properties for the given
        file name.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        fileName = params["filename"]

        if fileName:
            try:
                editorConfig = editorconfig.get_properties(fileName)
                return {
                    "ok": True,
                    "config": editorConfig,
                }
            except editorconfig.EditorConfigError:
                return {
                    "ok": False,
                    "config": {},
                }

        return {
            "ok": True,
            "config": {},
        }
