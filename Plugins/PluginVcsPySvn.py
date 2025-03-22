# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the PySvn version control plugin.
"""

import contextlib
import importlib.util
import os

from PyQt6.QtCore import QCoreApplication, QObject

from eric7 import EricUtilities, Preferences
from eric7.__version__ import VersionOnly
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Plugins.VcsPlugins.vcsPySvn.SvnUtilities import getConfigPath, getServersPath
from eric7.Preferences.Shortcuts import readShortcuts

# Start-Of-Header
__header__ = {
    "name": "PySvn Plugin",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": False,
    "deactivateable": True,
    "version": VersionOnly,
    "pluginType": "version_control",
    "pluginTypename": "PySvn",
    "className": "VcsPySvnPlugin",
    "packageName": "__core__",
    "shortDescription": "Implements the PySvn version control interface.",
    "longDescription": """This plugin provides the PySvn version control interface.""",
    "pyqtApi": 2,
}
# End-Of-Header

error = ""  # noqa: U200


def exeDisplayData():
    """
    Public method to support the display of some executable info.

    @return dictionary containing the data to be shown
    @rtype dict
    """
    try:
        import pysvn  # __IGNORE_WARNING_I10__

        try:
            text = os.path.dirname(pysvn.__file__)
        except AttributeError:
            text = "PySvn"
        version = ".".join([str(v) for v in pysvn.version])
    except ImportError:
        text = "PySvn"
        version = ""

    data = {
        "programEntry": False,
        "header": QCoreApplication.translate(
            "VcsPySvnPlugin", "Version Control - Subversion (pysvn)"
        ),
        "text": text,
        "version": version,
    }

    return data


def getVcsSystemIndicator():
    """
    Public function to get the indicators for this version control system.

    @return dictionary with indicator as key and a tuple with the vcs name
        and vcs display string
    @rtype dict
    """
    return {
        ".svn": (__header__["pluginTypename"], displayString()),
        "_svn": (__header__["pluginTypename"], displayString()),
    }


def displayString():
    """
    Public function to get the display string.

    @return display string
    @rtype str
    """
    if importlib.util.find_spec("pysvn") is None:
        return ""
    else:
        return QCoreApplication.translate("VcsPySvnPlugin", "Subversion (pysvn)")


subversionCfgPluginObject = None


def createConfigurationPage(_configDlg):
    """
    Module function to create the configuration page.

    @param _configDlg reference to the configuration dialog (unused)
    @type QDialog
    @return reference to the configuration page
    @rtype SubversionPage
    """
    from eric7.Plugins.VcsPlugins.vcsPySvn.ConfigurationPage.SubversionPage import (
        SubversionPage,
    )

    global subversionCfgPluginObject

    if subversionCfgPluginObject is None:
        subversionCfgPluginObject = VcsPySvnPlugin(None)
    page = SubversionPage(subversionCfgPluginObject)
    return page


def getConfigData():
    """
    Module function returning data as required by the configuration dialog.

    @return dictionary with key "zzz_subversionPage" containing the relevant
    data
    @rtype dict
    """
    return {
        "zzz_subversionPage": [
            QCoreApplication.translate("VcsPySvnPlugin", "Subversion"),
            os.path.join(
                "VcsPlugins", "vcsPySvn", "icons", "preferences-subversion.svg"
            ),
            createConfigurationPage,
            "vcsPage",
            None,
        ],
    }


def prepareUninstall():
    """
    Module function to prepare for an uninstallation.
    """
    if not ericApp().getObject("PluginManager").isPluginLoaded("PluginVcsSubversion"):
        Preferences.getSettings().remove("Subversion")


class VcsPySvnPlugin(QObject):
    """
    Class implementing the PySvn version control plugin.
    """

    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UserInterface
        """
        from eric7.Plugins.VcsPlugins.vcsPySvn.ProjectHelper import PySvnProjectHelper

        super().__init__(ui)
        self.__ui = ui

        self.__subversionDefaults = {
            "StopLogOnCopy": 1,
            "LogLimit": 20,
        }

        self.__projectHelperObject = PySvnProjectHelper(None, None, ui)
        with contextlib.suppress(KeyError):
            ericApp().registerPluginObject(
                __header__["pluginTypename"],
                self.__projectHelperObject,
                __header__["pluginType"],
            )
        readShortcuts(pluginName=__header__["pluginTypename"])

    def getProjectHelper(self):
        """
        Public method to get a reference to the project helper object.

        @return reference to the project helper object
        @rtype PySvnProjectHelper
        """
        return self.__projectHelperObject

    def initToolbar(self, ui, toolbarManager):
        """
        Public slot to initialize the VCS toolbar.

        @param ui reference to the main window
        @type UserInterface
        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        """
        if self.__projectHelperObject:
            self.__projectHelperObject.initToolbar(ui, toolbarManager)

    def activate(self):
        """
        Public method to activate this plugin.

        @return tuple of reference to instantiated viewmanager and
            activation status
        @rtype  tuple of (Subversion, bool)
        """
        from eric7.Plugins.VcsPlugins.vcsPySvn.subversion import Subversion

        self.__object = Subversion(self, self.__ui)

        tb = self.__ui.getToolbar("vcs")[1]
        tb.setVisible(False)
        tb.setEnabled(False)

        tb = self.__ui.getToolbar("pysvn")[1]
        tb.setVisible(Preferences.getVCS("ShowVcsToolbar"))
        tb.setEnabled(True)

        return self.__object, True

    def deactivate(self):
        """
        Public method to deactivate this plugin.
        """
        self.__object = None

        tb = self.__ui.getToolbar("pysvn")[1]
        tb.setVisible(False)
        tb.setEnabled(False)

        tb = self.__ui.getToolbar("vcs")[1]
        tb.setVisible(Preferences.getVCS("ShowVcsToolbar"))
        tb.setEnabled(True)

    def getPreferences(self, key):
        """
        Public method to retrieve the various settings.

        @param key the key of the value to get
        @type str
        @return the requested refactoring setting
        @rtype Any
        """
        if key in ["StopLogOnCopy"]:
            return EricUtilities.toBool(
                Preferences.getSettings().value(
                    "Subversion/" + key, self.__subversionDefaults[key]
                )
            )
        elif key in ["LogLimit"]:
            return int(
                Preferences.getSettings().value(
                    "Subversion/" + key, self.__subversionDefaults[key]
                )
            )
        elif key in ["Commits"]:
            return EricUtilities.toList(
                Preferences.getSettings().value("Subversion/" + key)
            )
        else:
            return Preferences.getSettings().value("Subversion/" + key)

    def setPreferences(self, key, value):
        """
        Public method to store the various settings.

        @param key the key of the setting to be set
        @type str
        @param value the value to be set
        @type Any
        """
        Preferences.getSettings().setValue("Subversion/" + key, value)

    def getServersPath(self):
        """
        Public method to get the filename of the servers file.

        @return filename of the servers file
        @rtype str
        """
        return getServersPath()

    def getConfigPath(self):
        """
        Public method to get the filename of the config file.

        @return filename of the config file
        @rtype str
        """
        return getConfigPath()

    def prepareUninstall(self):
        """
        Public method to prepare for an uninstallation.
        """
        ericApp().unregisterPluginObject(__header__["pluginTypename"])

    def prepareUnload(self):
        """
        Public method to prepare for an unload.
        """
        if self.__projectHelperObject:
            self.__projectHelperObject.removeToolbar(
                self.__ui, ericApp().getObject("ToolbarManager")
            )
        ericApp().unregisterPluginObject(__header__["pluginTypename"])
