# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class representing the shortcuts JSON file.
"""

import json
import time
import typing

from PyQt6.QtCore import QObject

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverridenCursor
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

HelpViewer = typing.TypeVar("WebBrowserWindow")


class ShortcutsFile(QObject):
    """
    Class representing the shortcuts JSON file.
    """

    def __init__(self: "ShortcutsFile", parent: QObject = None) -> None:
        """
        Constructor

        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

    def __addActionsToDict(
        self: "ShortcutsFile", category: str, actions: list, actionsDict: dict
    ) -> None:
        """
        Private method to add a list of actions to the actions dictionary.

        @param category category of the actions
        @type str
        @param actions list of actions
        @type list of QAction
        @param actionsDict reference to the actions dictionary to be modified
        @type dict
        """
        if actions:
            if category not in actionsDict:
                actionsDict[category] = {}
            for act in actions:
                if act.objectName():
                    # shortcuts are only exported, if their objectName is set
                    actionsDict[category][act.objectName()] = (
                        act.shortcut().toString(),
                        act.alternateShortcut().toString(),
                    )

    def writeFile(
        self: "ShortcutsFile", filename: str, helpViewer: HelpViewer = None
    ) -> bool:
        """
        Public method to write the shortcuts data to a shortcuts JSON file.

        @param filename name of the shortcuts file
        @type str
        @param helpViewer reference to the help window object
        @type WebBrowserWindow
        @return flag indicating a successful write
        @rtype bool
        """
        actionsDict = {}

        # step 1: collect all the shortcuts
        if helpViewer is None:
            self.__addActionsToDict(
                "Project", ericApp().getObject("Project").getActions(), actionsDict
            )
            self.__addActionsToDict(
                "General",
                ericApp().getObject("UserInterface").getActions("ui"),
                actionsDict,
            )
            self.__addActionsToDict(
                "Wizards",
                ericApp().getObject("UserInterface").getActions("wizards"),
                actionsDict,
            )
            self.__addActionsToDict(
                "Debug", ericApp().getObject("DebugUI").getActions(), actionsDict
            )
            self.__addActionsToDict(
                "Edit",
                ericApp().getObject("ViewManager").getActions("edit"),
                actionsDict,
            )
            self.__addActionsToDict(
                "File",
                ericApp().getObject("ViewManager").getActions("file"),
                actionsDict,
            )
            self.__addActionsToDict(
                "Search",
                ericApp().getObject("ViewManager").getActions("search"),
                actionsDict,
            )
            self.__addActionsToDict(
                "View",
                ericApp().getObject("ViewManager").getActions("view"),
                actionsDict,
            )
            self.__addActionsToDict(
                "Macro",
                ericApp().getObject("ViewManager").getActions("macro"),
                actionsDict,
            )
            self.__addActionsToDict(
                "Bookmarks",
                ericApp().getObject("ViewManager").getActions("bookmark"),
                actionsDict,
            )
            self.__addActionsToDict(
                "Spelling",
                ericApp().getObject("ViewManager").getActions("spelling"),
                actionsDict,
            )
            self.__addActionsToDict(
                "Window",
                ericApp().getObject("ViewManager").getActions("window"),
                actionsDict,
            )

            for category, ref in ericApp().getPluginObjects():
                if hasattr(ref, "getActions"):
                    self.__addActionsToDict(category, ref.getActions(), actionsDict)

        else:
            self.__addActionsToDict(
                helpViewer.getActionsCategory(), helpViewer.getActions(), actionsDict
            )

        # step 2: assemble the data structure to be written
        shortcutsDict = {
            # step 2.0: header
            "header": {
                "comment": "eric keyboard shortcuts file",
                "saved": time.strftime("%Y-%m-%d, %H:%M:%S"),
                "author": Preferences.getUser("Email"),
            },
            # step 2.1: keyboard shortcuts
            "shortcuts": actionsDict,
        }

        try:
            jsonString = json.dumps(shortcutsDict, indent=2) + "\n"
            with open(filename, "w") as f:
                f.write(jsonString)
        except (OSError, TypeError) as err:
            with EricOverridenCursor():
                EricMessageBox.critical(
                    None,
                    self.tr("Export Keyboard Shortcuts"),
                    self.tr(
                        "<p>The keyboard shortcuts file <b>{0}</b> could not"
                        " be written.</p><p>Reason: {1}</p>"
                    ).format(filename, str(err)),
                )
                return False

        return True

    def readFile(self: "ShortcutsFile", filename: str) -> bool:
        """
        Public method to read the shortcuts data from a shortcuts JSON file.

        @param filename name of the shortcuts file
        @type str
        @return Dictionary of dictionaries of shortcuts. The keys of the
            dictionary are the shortcuts categories, the values are
            dictionaries. These dictionaries have the shortcut name as their
            key and a tuple of accelerators as their value.
        @rtype dict
        """
        try:
            with open(filename, "r") as f:
                jsonString = f.read()
            shortcutsDict = json.loads(jsonString)
        except (OSError, json.JSONDecodeError) as err:
            EricMessageBox.critical(
                None,
                self.tr("Import Keyboard Shortcuts"),
                self.tr(
                    "<p>The keyboard shortcuts file <b>{0}</b> could not be"
                    " read.</p><p>Reason: {1}</p>"
                ).format(filename, str(err)),
            )
            return {}

        return shortcutsDict["shortcuts"]
