# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class representing the highlighting styles JSON file.
"""

import json
import time

from PyQt6.QtCore import QObject

from eric7 import Preferences
from eric7.EricGui.EricOverrideCursor import EricOverridenCursor
from eric7.EricWidgets import EricMessageBox


class HighlightingStylesFile(QObject):
    """
    Class representing the highlighting styles JSON file.
    """

    def __init__(self, parent: QObject = None):
        """
        Constructor

        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

        self.__lexerAliases = {
            "PO": "Gettext",
            "POV": "Povray",
        }

    def writeFile(self, filename: str, lexers: list) -> bool:
        """
        Public method to write the highlighting styles data to a highlighting
        styles JSON file.

        @param filename name of the highlighting styles file
        @type str
        @param lexers list of lexers for which to export the styles
        @type list of PreferencesLexer
        @return flag indicating a successful write
        @rtype bool
        """
        stylesDict = {
            # step 0: header
            "header": {
                "comment": "eric highlighting styles file",
                "saved": time.strftime("%Y-%m-%d, %H:%M:%S"),
                "author": Preferences.getUser("Email"),
            },
            # step 1: add the lexer style data
            "lexers": [],
        }
        for lexer in lexers:
            name = lexer.language()
            if name in self.__lexerAliases:
                name = self.__lexerAliases[name]
            lexerDict = {
                "name": name,
                "styles": [],
            }
            for description, style, substyle in lexer.getStyles():
                lexerDict["styles"].append(
                    {
                        "description": description,
                        "style": style,
                        "substyle": substyle,
                        "color": lexer.color(style, substyle).name(),
                        "paper": lexer.paper(style, substyle).name(),
                        "font": lexer.font(style, substyle).toString(),
                        "eolfill": lexer.eolFill(style, substyle),
                        "words": lexer.words(style, substyle).strip(),
                    }
                )
            stylesDict["lexers"].append(lexerDict)

        try:
            jsonString = json.dumps(stylesDict, indent=2) + "\n"
            with open(filename, "w") as f:
                f.write(jsonString)
        except (OSError, TypeError) as err:
            with EricOverridenCursor():
                EricMessageBox.critical(
                    None,
                    self.tr("Export Highlighting Styles"),
                    self.tr(
                        "<p>The highlighting styles file <b>{0}</b> could not"
                        " be written.</p><p>Reason: {1}</p>"
                    ).format(filename, str(err)),
                )
                return False

        return True

    def readFile(self, filename: str) -> list:
        """
        Public method to read the highlighting styles data from a highlighting
        styles JSON file.

        @param filename name of the highlighting styles file
        @type str
        @return list of read lexer style definitions
        @rtype list of dict
        """
        try:
            with open(filename, "r") as f:
                jsonString = f.read()
            stylesDict = json.loads(jsonString)
        except (OSError, json.JSONDecodeError) as err:
            EricMessageBox.critical(
                None,
                self.tr("Import Highlighting Styles"),
                self.tr(
                    "<p>The highlighting styles file <b>{0}</b> could not be"
                    " read.</p><p>Reason: {1}</p>"
                ).format(filename, str(err)),
            )
            return []

        return stylesDict["lexers"]
