# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a manager object for color themes.
"""

import json
import os
import re

from PyQt6.QtCore import QObject

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.Globals import getConfig


class ThemeManager(QObject):
    """
    Class implementing a manager object for color themes.
    """

    ColorKeyPatternList = [
        "Diff/.*Color",
        "Editor/Colour/",
        "IRC/.*Colou?r",
        "Project/Colour",
        "Python/.*Color",
        "Scintilla/.*color",
        "Scintilla/.*paper",
        "Tasks/.*Color",
        "WebBrowser/.*Colou?r",
    ]
    ColorKeyList = [
        "Debugger/BgColorChanged",
        "Debugger/BgColorNew",
        "UI/IconBarColor",
        "UI/LogStdErrColour",
        "UI/NotificationCriticalBackground",
        "UI/NotificationCriticalForeground",
        "UI/NotificationWarningBackground",
        "UI/NotificationWarningForeground",
    ]

    def __init__(self: "ThemeManager", parent: QObject = None):
        """
        Constructor

        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

    def importTheme(self: "ThemeManager") -> bool:
        """
        Public method to import a theme file and set the colors.

        @return flag indicating a successful import
        @rtype bool
        """
        filename = EricFileDialog.getOpenFileName(
            None,
            self.tr("Import Theme"),
            getConfig("ericThemesDir"),
            self.tr("eric Theme Files (*.ethj);;All Files (*)"),
        )
        if filename:
            try:
                with open(filename, "r") as f:
                    jsonString = f.read()
                themeDict = json.loads(jsonString)
            except (OSError, TypeError) as err:
                EricMessageBox.critical(
                    None,
                    self.tr("Import Theme"),
                    self.tr(
                        "<p>The theme file <b>{0}</b> could not"
                        " be read.</p><p>Reason: {1}</p>"
                    ).format(filename, str(err)),
                )
                return False

            # step 1: process stylesheet data
            stylesheetDict = themeDict["stylesheet"]
            if stylesheetDict["name"]:
                stylesheetsDir = os.path.join(
                    EricUtilities.getConfigDir(), "stylesheets"
                )
                if not os.path.exists(stylesheetsDir):
                    os.makedirs(stylesheetsDir)
                stylesheetFile = os.path.join(stylesheetsDir, stylesheetDict["name"])
                ok = (
                    EricMessageBox.yesNo(
                        None,
                        self.tr("Import Theme"),
                        self.tr(
                            "The stylesheet file {0} exists already."
                            " Shall it be overwritten?"
                        ).format(stylesheetDict["name"]),
                    )
                    if os.path.exists(stylesheetFile)
                    else True
                )
                if ok:
                    try:
                        with open(stylesheetFile, "w") as f:
                            f.write(stylesheetDict["contents"])
                    except OSError as err:
                        EricMessageBox.critical(
                            None,
                            self.tr("Import Theme"),
                            self.tr(
                                "<p>The stylesheet file <b>{0}</b> could"
                                " not be written.</p><p>Reason: {1}</p>"
                            ).format(stylesheetFile, str(err)),
                        )
                        stylesheetFile = ""
                Preferences.setUI("StyleSheet", stylesheetFile)

            # step 2: transfer the color entries
            settings = Preferences.getSettings()
            colorsDict = themeDict["colors"]
            for key, value in colorsDict.items():
                settings.setValue(key, value)

            Preferences.syncPreferences()
            return True

        return False

    def exportTheme(self: "ThemeManager"):
        """
        Public method to export the current colors to a theme file.
        """
        filename, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            None,
            self.tr("Export Theme"),
            os.path.expanduser("~"),
            self.tr("eric Theme Files (*.ethj)"),
            "",
            EricFileDialog.DontConfirmOverwrite,
        )
        if filename:
            ext = os.path.splitext(filename)[1]
            if not ext:
                filename = "{0}{1}".format(
                    filename, selectedFilter.rsplit(None, 1)[-1][2:-1]
                )

            ok = (
                EricMessageBox.yesNo(
                    None,
                    self.tr("Export Theme"),
                    self.tr(
                        """<p>The theme file <b>{0}</b> exists"""
                        """ already. Overwrite it?</p>"""
                    ).format(filename),
                )
                if os.path.exists(filename)
                else True
            )

            if ok:
                # step 1: generate a dictionary with all color settings
                settings = Preferences.getSettings()
                colorKeyFilterRe = re.compile(
                    "|".join(
                        ThemeManager.ColorKeyPatternList + ThemeManager.ColorKeyList
                    )
                )

                keys = [k for k in settings.allKeys() if colorKeyFilterRe.match(k)]
                colorsDict = {}
                for key in keys:
                    colorsDict[key] = settings.value(key)

                # step 2: read the contents of the current stylesheet
                stylesheetDict = {"contents": "", "name": ""}
                stylesheet = Preferences.getUI("StyleSheet")
                if stylesheet and os.path.exists(stylesheet):
                    try:
                        with open(stylesheet, "r") as f:
                            stylesheetDict["contents"] = f.read()
                        stylesheetDict["name"] = os.path.basename(stylesheet)
                    except OSError as err:
                        EricMessageBox.critical(
                            None,
                            self.tr("Export Theme"),
                            self.tr(
                                "<p>The stylesheet file <b>{0}</b> could not"
                                " be read.</p><p>Reason: {1}</p>"
                            ).format(stylesheet, str(err)),
                        )

                themeDict = {
                    "colors": colorsDict,
                    "stylesheet": stylesheetDict,
                }

                try:
                    jsonString = json.dumps(themeDict, indent=2) + "\n"
                    with open(filename, "w") as f:
                        f.write(jsonString)
                except (OSError, TypeError) as err:
                    EricMessageBox.critical(
                        None,
                        self.tr("Export Theme"),
                        self.tr(
                            "<p>The theme file <b>{0}</b> could not"
                            " be written.</p><p>Reason: {1}</p>"
                        ).format(filename, str(err)),
                    )
