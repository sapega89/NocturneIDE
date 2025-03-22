# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class representing the templates JSON file.
"""

import json
import time
import typing

from PyQt6.QtCore import QObject

from eric7.EricGui.EricOverrideCursor import EricOverridenCursor
from eric7.EricWidgets import EricMessageBox

TemplateViewer = typing.TypeVar("TemplateViewer")


class TemplatesFile(QObject):
    """
    Class representing the templates JSON file.
    """

    def __init__(self, viewer: TemplateViewer, parent: QObject = None):
        """
        Constructor

        @param viewer reference to the template viewer object
        @type TemplateViewer
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)
        self.__viewer = viewer

    def writeFile(self, filename: str) -> bool:
        """
        Public method to write the templates data to a templates JSON file.

        @param filename name of the templates file
        @type str
        @return flag indicating a successful write
        @rtype bool
        """
        templatesDict = {
            # step 0: header
            "header": {
                "comment": "eric templates file",
                "saved": time.strftime("%Y-%m-%d, %H:%M:%S"),
                "warning": ("This file was generated automatically, do not edit."),
            }
        }

        # step 1: template groups and templates
        templateGroups = []
        for group in self.__viewer.getAllGroups():
            templates = []
            for template in group.getAllEntries():
                templates.append(
                    {
                        "name": template.getName(),
                        "description": template.getDescription().strip(),
                        "text": template.getTemplateText(),
                    }
                )
            templateGroups.append(
                {
                    "name": group.getName(),
                    "language": group.getLanguage(),
                    "templates": templates,
                }
            )
        templatesDict["template_groups"] = templateGroups

        try:
            jsonString = json.dumps(templatesDict, indent=2) + "\n"
            with open(filename, "w") as f:
                f.write(jsonString)
        except (OSError, TypeError) as err:
            with EricOverridenCursor():
                EricMessageBox.critical(
                    None,
                    self.tr("Save Templates"),
                    self.tr(
                        "<p>The templates file <b>{0}</b> could not be"
                        " written.</p><p>Reason: {1}</p>"
                    ).format(filename, str(err)),
                )
                return False

        return True

    def readFile(self, filename: str) -> bool:
        """
        Public method to read the templates data from a templates JSON file.

        @param filename name of the templates file
        @type str
        @return flag indicating a successful read
        @rtype bool
        """
        try:
            with open(filename, "r") as f:
                jsonString = f.read()
            templatesDict = json.loads(jsonString)
        except (OSError, json.JSONDecodeError) as err:
            EricMessageBox.critical(
                None,
                self.tr("Read Templates"),
                self.tr(
                    "<p>The templates file <b>{0}</b> could not be read.</p>"
                    "<p>Reason: {1}</p>"
                ).format(filename, str(err)),
            )
            return False

        for templateGroup in templatesDict["template_groups"]:
            self.__viewer.addGroup(templateGroup["name"], templateGroup["language"])
            for template in templateGroup["templates"]:
                self.__viewer.addEntry(
                    templateGroup["name"],
                    template["name"],
                    template["description"],
                    template["text"],
                    quiet=True,
                )

        return True
