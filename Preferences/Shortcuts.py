# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing functions dealing with keyboard shortcuts.
"""

import contextlib

from PyQt6.QtGui import QKeySequence

from eric7.EricWidgets.EricApplication import ericApp
from eric7.Preferences import Prefs, syncPreferences

from .ShortcutsFile import ShortcutsFile


def __readShortcut(act, category, prefClass):
    """
    Private function to read a single keyboard shortcut from the settings.

    @param act reference to the action object
    @type EricAction
    @param category category the action belongs to
    @type str
    @param prefClass preferences class used as the storage area
    @type Prefs
    """
    if act.objectName():
        accel = prefClass.settings.value(
            "Shortcuts/{0}/{1}/Accel".format(category, act.objectName())
        )
        if accel is not None:
            act.setShortcut(QKeySequence(accel))
        accel = prefClass.settings.value(
            "Shortcuts/{0}/{1}/AltAccel".format(category, act.objectName())
        )
        if accel is not None:
            act.setAlternateShortcut(QKeySequence(accel), removeEmpty=True)


def readShortcuts(prefClass=Prefs, webBrowser=None, pluginName=None):
    """
    Module function to read the keyboard shortcuts for the defined QActions.

    @param prefClass preferences class used as the storage area
    @type Prefs
    @param webBrowser reference to the web browser window object
    @type WebBrowserWindow
    @param pluginName name of the plugin for which to load shortcuts
    @type str
    """
    if webBrowser is None and pluginName is None:
        for act in ericApp().getObject("Project").getActions():
            __readShortcut(act, "Project", prefClass)

        for act in ericApp().getObject("UserInterface").getActions("ui"):
            __readShortcut(act, "General", prefClass)

        for act in ericApp().getObject("UserInterface").getActions("wizards"):
            __readShortcut(act, "Wizards", prefClass)

        for act in ericApp().getObject("DebugUI").getActions():
            __readShortcut(act, "Debug", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("edit"):
            __readShortcut(act, "Edit", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("file"):
            __readShortcut(act, "File", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("search"):
            __readShortcut(act, "Search", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("view"):
            __readShortcut(act, "View", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("macro"):
            __readShortcut(act, "Macro", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("bookmark"):
            __readShortcut(act, "Bookmarks", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("spelling"):
            __readShortcut(act, "Spelling", prefClass)

        actions = ericApp().getObject("ViewManager").getActions("window")
        if actions:
            for act in actions:
                __readShortcut(act, "Window", prefClass)

        for category, ref in ericApp().getPluginObjects():
            if hasattr(ref, "getActions"):
                actions = ref.getActions()
                for act in actions:
                    __readShortcut(act, category, prefClass)

    if webBrowser is not None:
        webBrowserCategory = webBrowser.getActionsCategory()
        for act in webBrowser.getActions():
            __readShortcut(act, webBrowserCategory, prefClass)

    if pluginName is not None:
        with contextlib.suppress(KeyError):
            ref = ericApp().getPluginObject(pluginName)
            if hasattr(ref, "getActions"):
                actions = ref.getActions()
                for act in actions:
                    __readShortcut(act, pluginName, prefClass)


def __saveShortcut(act, category, prefClass):
    """
    Private function to write a single keyboard shortcut to the settings.

    @param act reference to the action object
    @type EricAction
    @param category category the action belongs to
    @type str
    @param prefClass preferences class used as the storage area
    @type Prefs
    """
    if act.objectName():
        prefClass.settings.setValue(
            "Shortcuts/{0}/{1}/Accel".format(category, act.objectName()),
            act.shortcut().toString(),
        )
        prefClass.settings.setValue(
            "Shortcuts/{0}/{1}/AltAccel".format(category, act.objectName()),
            act.alternateShortcut().toString(),
        )


def saveShortcuts(prefClass=Prefs, webBrowser=None):
    """
    Module function to write the keyboard shortcuts for the defined QActions.

    @param prefClass preferences class used as the storage area
    @type Prefs
    @param webBrowser reference to the web browser window object
    @type WebBrowserWindow
    """
    if webBrowser is None:
        # step 1: clear all previously saved shortcuts
        prefClass.settings.beginGroup("Shortcuts")
        prefClass.settings.remove("")
        prefClass.settings.endGroup()

        # step 2: save the various shortcuts
        for act in ericApp().getObject("Project").getActions():
            __saveShortcut(act, "Project", prefClass)

        for act in ericApp().getObject("UserInterface").getActions("ui"):
            __saveShortcut(act, "General", prefClass)

        for act in ericApp().getObject("UserInterface").getActions("wizards"):
            __saveShortcut(act, "Wizards", prefClass)

        for act in ericApp().getObject("DebugUI").getActions():
            __saveShortcut(act, "Debug", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("edit"):
            __saveShortcut(act, "Edit", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("file"):
            __saveShortcut(act, "File", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("search"):
            __saveShortcut(act, "Search", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("view"):
            __saveShortcut(act, "View", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("macro"):
            __saveShortcut(act, "Macro", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("bookmark"):
            __saveShortcut(act, "Bookmarks", prefClass)

        for act in ericApp().getObject("ViewManager").getActions("spelling"):
            __saveShortcut(act, "Spelling", prefClass)

        actions = ericApp().getObject("ViewManager").getActions("window")
        if actions:
            for act in actions:
                __saveShortcut(act, "Window", prefClass)

        for category, ref in ericApp().getPluginObjects():
            if hasattr(ref, "getActions"):
                actions = ref.getActions()
                for act in actions:
                    __saveShortcut(act, category, prefClass)

    else:
        webBrowserCategory = webBrowser.getActionsCategory()

        # step 1: clear all previously saved shortcuts
        prefClass.settings.beginGroup("Shortcuts/{0}".format(webBrowserCategory))
        prefClass.settings.remove("")
        prefClass.settings.endGroup()

        # step 2: save the shortcuts
        for act in webBrowser.getActions():
            __saveShortcut(act, webBrowserCategory, prefClass)


def exportShortcuts(fn, helpViewer=None):
    """
    Module function to export the keyboard shortcuts for the defined QActions.

    @param fn filename of the export file
    @type str
    @param helpViewer reference to the help window object
    @type WebBrowserWindow
    """
    # let the plugin manager create on demand plugin objects
    pm = ericApp().getObject("PluginManager")
    pm.initOnDemandPlugins()

    shortcutsFile = ShortcutsFile()
    shortcutsFile.writeFile(fn, helpViewer)


def importShortcuts(fn, helpViewer=None):
    """
    Module function to import the keyboard shortcuts for the defined actions.

    @param fn filename of the import file
    @type str
    @param helpViewer reference to the help window object
    @type WebBrowserWindow
    """
    # let the plugin manager create on demand plugin objects
    pm = ericApp().getObject("PluginManager")
    pm.initOnDemandPlugins()

    shortcutsFile = ShortcutsFile()
    shortcuts = shortcutsFile.readFile(fn)
    if shortcuts:
        setActions(shortcuts, helpViewer=helpViewer)
        saveShortcuts()
        syncPreferences()


def __setAction(actions, shortcutsDict):
    """
    Private function to set a single keyboard shortcut category shortcuts.

    @param actions list of actions to set
    @type list of EricAction
    @param shortcutsDict dictionary containing accelerator information for
        one category
    @type dict
    """
    for act in actions:
        if act.objectName():
            with contextlib.suppress(KeyError):
                accel, altAccel = shortcutsDict[act.objectName()]
                act.setShortcut(QKeySequence(accel))
                act.setAlternateShortcut(QKeySequence(altAccel), removeEmpty=True)


def setActions(shortcuts, helpViewer=None):
    """
    Module function to set actions based on the imported shortcuts file.

    @param shortcuts dictionary containing the accelerator information
        read from a JSON or XML file
    @type dict
    @param helpViewer reference to the help window object
    @type WebBrowserWindow
    """
    if helpViewer is None:
        if "Project" in shortcuts:
            __setAction(
                ericApp().getObject("Project").getActions(), shortcuts["Project"]
            )

        if "General" in shortcuts:
            __setAction(
                ericApp().getObject("UserInterface").getActions("ui"),
                shortcuts["General"],
            )

        if "Wizards" in shortcuts:
            __setAction(
                ericApp().getObject("UserInterface").getActions("wizards"),
                shortcuts["Wizards"],
            )

        if "Debug" in shortcuts:
            __setAction(ericApp().getObject("DebugUI").getActions(), shortcuts["Debug"])

        if "Edit" in shortcuts:
            __setAction(
                ericApp().getObject("ViewManager").getActions("edit"), shortcuts["Edit"]
            )

        if "File" in shortcuts:
            __setAction(
                ericApp().getObject("ViewManager").getActions("file"), shortcuts["File"]
            )

        if "Search" in shortcuts:
            __setAction(
                ericApp().getObject("ViewManager").getActions("search"),
                shortcuts["Search"],
            )

        if "View" in shortcuts:
            __setAction(
                ericApp().getObject("ViewManager").getActions("view"), shortcuts["View"]
            )

        if "Macro" in shortcuts:
            __setAction(
                ericApp().getObject("ViewManager").getActions("macro"),
                shortcuts["Macro"],
            )

        if "Bookmarks" in shortcuts:
            __setAction(
                ericApp().getObject("ViewManager").getActions("bookmark"),
                shortcuts["Bookmarks"],
            )

        if "Spelling" in shortcuts:
            __setAction(
                ericApp().getObject("ViewManager").getActions("spelling"),
                shortcuts["Spelling"],
            )

        if "Window" in shortcuts:
            actions = ericApp().getObject("ViewManager").getActions("window")
            if actions:
                __setAction(actions, shortcuts["Window"])

        for category, ref in ericApp().getPluginObjects():
            if category in shortcuts and hasattr(ref, "getActions"):
                actions = ref.getActions()
                __setAction(actions, shortcuts[category])

    else:
        category = helpViewer.getActionsCategory()
        if category in shortcuts:
            __setAction(helpViewer.getActions(), shortcuts[category])
