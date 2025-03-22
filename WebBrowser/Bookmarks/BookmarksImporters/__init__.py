# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing bookmarks importers for various sources.
"""

import importlib

from PyQt6.QtCore import QCoreApplication

from eric7.EricGui import EricPixmapCache
from eric7.SystemUtilities import OSUtilities


def getImporters():
    """
    Module function to get a list of supported importers.

    @return list of tuples with an icon, readable name and internal name
    @rtype list of tuples of (QIcon, str, str)
    """
    importers = [
        (EricPixmapCache.getIcon("ericWeb48"), "eric Web Browser", "e5browser"),
        (EricPixmapCache.getIcon("firefox"), "Mozilla Firefox", "firefox"),
        (EricPixmapCache.getIcon("chrome"), "Google Chrome", "chrome"),
        (EricPixmapCache.getIcon("opera_legacy"), "Opera (Legacy)", "opera_legacy"),
        (EricPixmapCache.getIcon("safari"), "Apple Safari", "safari"),
        (
            EricPixmapCache.getIcon("xbel"),
            QCoreApplication.translate("BookmarksImporters", "XBEL File"),
            "xbel",
        ),
        (
            EricPixmapCache.getIcon("html"),
            QCoreApplication.translate("BookmarksImporters", "HTML File"),
            "html",
        ),
        (EricPixmapCache.getIcon("edge"), "Microsoft Edge", "edge"),
        (EricPixmapCache.getIcon("vivaldi"), "Vivaldi", "vivaldi"),
        (EricPixmapCache.getIcon("opera"), "Opera", "opera"),
        (EricPixmapCache.getIcon("falkon"), "Falkon", "falkon"),
    ]

    if OSUtilities.isLinuxPlatform():
        importers.append((EricPixmapCache.getIcon("chromium"), "Chromium", "chromium"))
        importers.append(
            (EricPixmapCache.getIcon("konqueror"), "Konqueror", "konqueror")
        )

    if OSUtilities.isWindowsPlatform():
        importers.append(
            (EricPixmapCache.getIcon("internet_explorer"), "Internet Explorer", "ie")
        )

    return importers


def getImporterInfo(sourceId):
    """
    Module function to get information for the given source id.

    @param sourceId source id to get info for
    @type str
    @return tuple with an icon, readable name, name of the default bookmarks file,
        an info text, a prompt and the default directory of the bookmarks file
    @rtype tuple of (QPixmap, str, str, str, str, str)
    """
    mod = getImporterModule(sourceId)
    return mod.getImporterInfo(sourceId)


def getImporter(sourceId, parent=None):
    """
    Module function to get an importer for the given source id.

    @param sourceId source id to get an importer for
    @type str
    @param parent reference to the parent object
    @type QObject
    @return bookmarks importer
    @rtype BookmarksImporter
    """
    mod = getImporterModule(sourceId)
    return mod.createImporter(sourceId=sourceId, parent=parent)


def getImporterModule(sourceId):
    """
    Function to get a bookmark importer module for a given source.

    @param sourceId source id to get an importer module for
    @type str
    @return reference to the imported module
    @rtype module
    @exception ValueError raised to indicate an unsupported importer
    """
    importerMapping = {
        "chrome": ".ChromeImporter",
        "chromium": ".ChromeImporter",
        "e5browser": ".XbelImporter",
        "edge": ".ChromeImporter",
        "falkon": ".ChromeImporter",
        "firefox": ".FirefoxImporter",
        "html": ".HtmlImporter",
        "ie": ".IExplorerImporter",
        "konqueror": ".XbelImporter",
        "opera": ".ChromeImporter",
        "opera_legacy": ".OperaImporter",
        "safari": ".SafariImporter",
        "vivaldi": ".ChromeImporter",
        "xbel": ".XbelImporter",
    }
    if sourceId in importerMapping:
        return importlib.import_module(importerMapping[sourceId], __package__)

    raise ValueError("Invalid importer ID given ({0}).".format(sourceId))
