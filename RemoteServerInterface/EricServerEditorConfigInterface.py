# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor Config interface to the eric-ide server.
"""

import editorconfig

from PyQt6.QtCore import QEventLoop, QObject

from eric7.RemoteServer.EricRequestCategory import EricRequestCategory
from eric7.SystemUtilities import FileSystemUtilities


class EricServerEditorConfigInterface(QObject):
    """
    Class implementing the Editor Config interface to the eric-ide server.
    """

    def __init__(self, serverInterface):
        """
        Constructor

        @param serverInterface reference to the eric-ide server interface
        @type EricServerInterface
        """
        super().__init__(parent=serverInterface)

        self.__serverInterface = serverInterface

    def loadEditorConfig(self, filename):
        """
        Public method to load the editor config for the given file.

        @param filename name of the file to get the editor config for
        @type str
        @return dictionary containing the editor config data
        @rtype dict
        @exception editorconfig.EditorConfigError raised to indicate an
            issue loading the editor config
        """
        loop = QEventLoop()
        ok = False
        config = None

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, config

            if reply == "LoadEditorConfig":
                ok = params["ok"]
                config = params["config"]
                loop.quit()

        if not self.__serverInterface.isServerConnected():
            raise editorconfig.EditorConfigError(
                "Not connected to an 'eric-ide' server."
            )
        else:
            self.__serverInterface.sendJson(
                category=EricRequestCategory.EditorConfig,
                request="LoadEditorConfig",
                params={"filename": FileSystemUtilities.plainFileName(filename)},
                callback=callback,
            )

            loop.exec()
            if not ok:
                raise editorconfig.EditorConfigError()

            return config
