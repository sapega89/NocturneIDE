# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class representing the project JSON file.
"""

import contextlib
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


class ProjectFile(QObject):
    """
    Class representing the project JSON file.
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
        Public method to write the project data to a project JSON file.

        @param filename name of the project file
        @type str
        @return flag indicating a successful write
        @rtype bool
        """
        fsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )
        isRemote = FileSystemUtilities.isRemoteFileName(filename)

        projectDict = {
            "header": {
                "comment": "eric project file for project {0}".format(
                    self.__project.getProjectName()
                ),
                "copyright": "Copyright (C) {0} {1}, {2}".format(
                    time.strftime("%Y"),
                    self.__project.getProjectData(dataKey="AUTHOR"),
                    self.__project.getProjectData(dataKey="EMAIL"),
                ),
            }
        }

        if Preferences.getProject("TimestampFile"):
            projectDict["header"]["saved"] = time.strftime("%Y-%m-%d, %H:%M:%S")

        projectDict["project"] = self.__project.getProjectData()

        # modify paths to contain universal separators
        for key in self.__project.getFileCategories() + ["TRANSLATIONEXCEPTIONS"]:
            with contextlib.suppress(KeyError):
                projectDict["project"][key] = sorted(
                    [
                        FileSystemUtilities.fromNativeSeparators(f)
                        for f in projectDict["project"][key]
                    ]
                )
        for key in (
            "SPELLWORDS",
            "SPELLEXCLUDES",
            "TRANSLATIONPATTERN",
            "TRANSLATIONSBINPATH",
            "TRANSLATIONSOURCESTARTPATH",
            "MAINSCRIPT",
            "SOURCESDIR",
        ):
            with contextlib.suppress(KeyError):
                projectDict["project"][key] = (
                    fsInterface.fromNativeSeparators(projectDict["project"][key])
                    if isRemote
                    else FileSystemUtilities.fromNativeSeparators(
                        projectDict["project"][key]
                    )
                )

        try:
            jsonString = json.dumps(projectDict, indent=2, sort_keys=True) + "\n"
            if isRemote:
                title = self.tr("Save Remote Project File")
                fsInterface.writeFile(filename, jsonString.encode("utf-8"))
            else:
                title = self.tr("Save Project File")
                with open(filename, "w", newline="") as f:
                    f.write(jsonString)
        except (OSError, TypeError) as err:
            with EricOverridenCursor():
                EricMessageBox.critical(
                    None,
                    title,
                    self.tr(
                        "<p>The project file <b>{0}</b> could not be "
                        "written.</p><p>Reason: {1}</p>"
                    ).format(filename, str(err)),
                )
                return False

        return True

    def readFile(self, filename: str) -> bool:
        """
        Public method to read the project data from a project JSON file.

        @param filename name of the project file
        @type str
        @return flag indicating a successful read
        @rtype bool
        """
        fsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        isRemote = FileSystemUtilities.isRemoteFileName(filename)
        try:
            if isRemote:
                title = self.tr("Read Remote Project File")
                jsonString = fsInterface.readFile(filename).decode("utf-8")
            else:
                title = self.tr("Read Project File")
                with open(filename, "r") as f:
                    jsonString = f.read()
            projectDict = json.loads(jsonString)
        except (OSError, json.JSONDecodeError) as err:
            EricMessageBox.critical(
                None,
                title,
                self.tr(
                    "<p>The project file <b>{0}</b> could not be "
                    "read.</p><p>Reason: {1}</p>"
                ).format(filename, str(err)),
            )
            return False

        # modify paths to contain native separators
        for key in self.__project.getFileCategories() + ["TRANSLATIONEXCEPTIONS"]:
            with contextlib.suppress(KeyError):
                projectDict["project"][key] = (
                    [
                        fsInterface.toNativeSeparators(f)
                        for f in projectDict["project"][key]
                    ]
                    if isRemote
                    else [
                        FileSystemUtilities.toNativeSeparators(f)
                        for f in projectDict["project"][key]
                    ]
                )
        for key in (
            "SPELLWORDS",
            "SPELLEXCLUDES",
            "TRANSLATIONPATTERN",
            "TRANSLATIONSBINPATH",
            "TRANSLATIONSOURCESTARTPATH",
            "MAINSCRIPT",
            "SOURCESDIR",
        ):
            with contextlib.suppress(KeyError):
                projectDict["project"][key] = (
                    fsInterface.toNativeSeparators(projectDict["project"][key])
                    if isRemote
                    else FileSystemUtilities.toNativeSeparators(
                        projectDict["project"][key]
                    )
                )

        self.__project.setProjectData(projectDict["project"])

        return True
