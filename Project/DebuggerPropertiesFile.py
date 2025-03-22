# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class representing the project debugger properties
JSON file.
"""

import json
import time
import typing

from PyQt6.QtCore import QObject

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverridenCursor
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities

Project = typing.TypeVar("Project")


class DebuggerPropertiesFile(QObject):
    """
    Class representing the project debugger properties JSON file.
    """

    def __init__(self, project: Project, parent: QObject = None):
        """
        Constructor

        @param project reference to the project object
        @type Project
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)
        self.__project = project

    def writeFile(self, filename: str) -> bool:
        """
        Public method to write the project debugger properties data to a
        project debugger properties JSON file.

        @param filename name of the user project file
        @type str
        @return flag indicating a successful write
        @rtype bool
        """
        fsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        debuggerPropertiesDict = {
            "header": {
                "comment": "eric debugger properties file for project {0}".format(
                    self.__project.getProjectName()
                ),
                "warning": "This file was generated automatically, do not edit.",
            }
        }

        if Preferences.getProject("TimestampFile"):
            debuggerPropertiesDict["header"]["saved"] = time.strftime(
                "%Y-%m-%d, %H:%M:%S"
            )

        debuggerPropertiesDict["debug_properties"] = self.__project.debugProperties

        try:
            jsonString = json.dumps(debuggerPropertiesDict, indent=2) + "\n"
            if FileSystemUtilities.isRemoteFileName(filename):
                title = self.tr("Save Remote Debugger Properties")
                fsInterface.writeFile(filename, jsonString.encode("utf-8"))
            else:
                title = self.tr("Save Debugger Properties")
                with open(filename, "w") as f:
                    f.write(jsonString)
        except (OSError, TypeError) as err:
            with EricOverridenCursor():
                EricMessageBox.critical(
                    None,
                    title,
                    self.tr(
                        "<p>The project debugger properties file"
                        " <b>{0}</b> could not be written.</p>"
                        "<p>Reason: {1}</p>"
                    ).format(filename, str(err)),
                )
                return False

        return True

    def readFile(self, filename: str) -> bool:
        """
        Public method to read the project debugger properties data from a
        project debugger properties JSON file.

        @param filename name of the project file
        @type str
        @return flag indicating a successful read
        @rtype bool
        """
        fsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        try:
            if FileSystemUtilities.isRemoteFileName(filename):
                title = self.tr("Read Remote Debugger Properties")
                jsonString = fsInterface.readFile(filename).decode("utf-8")
            else:
                title = self.tr("Read Debugger Properties")
                with open(filename, "r") as f:
                    jsonString = f.read()
            debuggerPropertiesDict = json.loads(jsonString)
        except (OSError, json.JSONDecodeError) as err:
            EricMessageBox.critical(
                None,
                title,
                self.tr(
                    "<p>The project debugger properties file <b>{0}</b>"
                    " could not be read.</p><p>Reason: {1}</p>"
                ).format(filename, str(err)),
            )
            return False

        self.__project.debugProperties.update(
            debuggerPropertiesDict["debug_properties"]
        )

        return True
