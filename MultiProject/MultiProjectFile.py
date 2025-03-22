# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class representing the multi project JSON file.
"""

import json
import os
import time
import typing

from PyQt6.QtCore import QObject

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverridenCursor
from eric7.EricWidgets import EricMessageBox

from .MultiProjectProjectMeta import MultiProjectProjectMeta

MultiProject = typing.TypeVar("MultiProject")


class MultiProjectFile(QObject):
    """
    Class representing the multi project JSON file.
    """

    def __init__(self, multiProject: MultiProject, parent: QObject = None):
        """
        Constructor

        @param multiProject reference to the multi project object
        @type MultiProject
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)
        self.__multiProject = multiProject

    def writeFile(self, filename: str) -> bool:
        """
        Public method to write the multi project data to a multi project
        JSON file.

        @param filename name of the multi project file
        @type str
        @return flag indicating a successful write
        @rtype bool
        """
        name = os.path.splitext(os.path.basename(filename))[0]

        multiProjectDict = {
            "header": {
                "comment": f"eric multi project file for multi project {name}",
            }
        }

        if Preferences.getMultiProject("TimestampFile"):
            multiProjectDict["header"]["saved"] = time.strftime("%Y-%m-%d, %H:%M:%S")

        multiProjectDict["description"] = self.__multiProject.description
        multiProjectDict["projects"] = [
            p.as_dict() for p in self.__multiProject.getProjects()
        ]

        try:
            jsonString = json.dumps(multiProjectDict, indent=2) + "\n"
            with open(filename, "w") as f:
                f.write(jsonString)
        except (OSError, TypeError) as err:
            with EricOverridenCursor():
                EricMessageBox.critical(
                    None,
                    self.tr("Save Multi Project File"),
                    self.tr(
                        "<p>The multi project file <b>{0}</b> could not be "
                        "written.</p><p>Reason: {1}</p>"
                    ).format(filename, str(err)),
                )
                return False

        return True

    def readFile(self, filename: str) -> bool:
        """
        Public method to read the multi project data from a multi project
        JSON file.

        @param filename name of the multi project file
        @type str
        @return flag indicating a successful read
        @rtype bool
        """
        try:
            with open(filename, "r") as f:
                jsonString = f.read()
            multiProjectDict = json.loads(jsonString)
        except (OSError, json.JSONDecodeError) as err:
            EricMessageBox.critical(
                None,
                self.tr("Read Multi Project File"),
                self.tr(
                    "<p>The multi project file <b>{0}</b> could not be "
                    "read.</p><p>Reason: {1}</p>"
                ).format(filename, str(err)),
            )
            return False

        self.__multiProject.description = multiProjectDict["description"]
        for project in multiProjectDict["projects"]:
            self.__multiProject.addProject(MultiProjectProjectMeta.from_dict(project))

        return True
