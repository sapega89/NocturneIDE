# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Git version control plugin.
"""

import contextlib
import os

from PyQt6.QtCore import QByteArray, QCoreApplication, QObject

from eric7 import EricUtilities, Preferences
from eric7.__version__ import VersionOnly
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Plugins.VcsPlugins.vcsGit.GitUtilities import getConfigPath
from eric7.Preferences.Shortcuts import readShortcuts
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities

# Start-Of-Header
__header__ = {
    "name": "Git Plugin",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": False,
    "deactivateable": True,
    "version": VersionOnly,
    "pluginType": "version_control",
    "pluginTypename": "Git",
    "className": "VcsGitPlugin",
    "packageName": "__core__",
    "shortDescription": "Implements the Git version control interface.",
    "longDescription": """This plugin provides the Git version control interface.""",
    "pyqtApi": 2,
}
# End-Of-Header

error = ""  # noqa: U200


def exeDisplayData():
    """
    Public method to support the display of some executable info.

    @return dictionary containing the data to query the presence of
        the executable
    @rtype dict
    """
    exe = "git"
    if OSUtilities.isWindowsPlatform():
        exe += ".exe"

    data = {
        "programEntry": True,
        "header": QCoreApplication.translate("VcsGitPlugin", "Version Control - Git"),
        "exe": exe,
        "versionCommand": "version",
        "versionStartsWith": "git",
        "versionPosition": 2,
        "version": "",
        "versionCleanup": None,
    }

    return data


def getVcsSystemIndicator():
    """
    Public function to get the indicators for this version control system.

    @return dictionary with indicator as key and a tuple with the vcs name
        and vcs display string
    @rtype dict
    """
    data = {}
    exe = "git"
    if OSUtilities.isWindowsPlatform():
        exe += ".exe"
    if FileSystemUtilities.isinpath(exe):
        data[".git"] = (__header__["pluginTypename"], displayString())
        data["_git"] = (__header__["pluginTypename"], displayString())
    return data


def displayString():
    """
    Public function to get the display string.

    @return display string
    @rtype str
    """
    exe = "git"
    if OSUtilities.isWindowsPlatform():
        exe += ".exe"
    if FileSystemUtilities.isinpath(exe):
        return QCoreApplication.translate("VcsGitPlugin", "Git")
    else:
        return ""


gitCfgPluginObject = None


def createConfigurationPage(_configDlg):
    """
    Module function to create the configuration page.

    @param _configDlg reference to the configuration dialog (unused)
    @type QDialog
    @return reference to the configuration page
    @rtype GitPage
    """
    from eric7.Plugins.VcsPlugins.vcsGit.ConfigurationPage.GitPage import GitPage

    global gitCfgPluginObject

    if gitCfgPluginObject is None:
        gitCfgPluginObject = VcsGitPlugin(None)
    page = GitPage(gitCfgPluginObject)
    return page


def getConfigData():
    """
    Module function returning data as required by the configuration dialog.

    @return dictionary with key "zzz_gitPage" containing the relevant data
    @rtype dict
    """
    return {
        "zzz_gitPage": [
            QCoreApplication.translate("VcsGitPlugin", "Git"),
            os.path.join("VcsPlugins", "vcsGit", "icons", "preferences-git.svg"),
            createConfigurationPage,
            "vcsPage",
            None,
        ],
    }


def prepareUninstall():
    """
    Module function to prepare for an uninstallation.
    """
    if not ericApp().getObject("PluginManager").isPluginLoaded("PluginVcsGit"):
        Preferences.getSettings().remove("Git")


def clearPrivateData():
    """
    Module function to clear the private data of the plug-in.
    """
    for key in ["RepositoryUrlHistory"]:
        VcsGitPlugin.setPreferences(key, [])


class VcsGitPlugin(QObject):
    """
    Class implementing the Git version control plugin.
    """

    GitDefaults = {
        "StopLogOnCopy": True,  # used in log browser
        "ShowAuthorColumns": True,  # used in log browser
        "ShowCommitterColumns": True,  # used in log browser
        "ShowCommitIdColumn": True,  # used in log browser
        "ShowBranchesColumn": True,  # used in log browser
        "ShowTagsColumn": True,  # used in log browser
        "FindCopiesHarder": False,  # used in log browser
        "LogLimit": 20,
        "LogSubjectColumnWidth": 30,
        "LogBrowserGeometry": QByteArray(),
        "LogBrowserSplitterStates": [QByteArray(), QByteArray(), QByteArray()],
        # mainSplitter, detailsSplitter, diffSplitter
        "StatusDialogGeometry": QByteArray(),
        "StatusDialogSplitterStates": [QByteArray(), QByteArray()],
        # vertical splitter, horizontal splitter
        "WorktreeDialogGeometry": QByteArray(),
        "Commits": [],
        "CommitIdLength": 10,
        "CleanupPatterns": "*.orig *.rej *~",
        "AggressiveGC": True,
        "RepositoryUrlHistory": [],
    }

    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UserInterface
        """
        from eric7.Plugins.VcsPlugins.vcsGit.ProjectHelper import GitProjectHelper

        super().__init__(ui)
        self.__ui = ui

        self.__projectHelperObject = GitProjectHelper(None, None, ui)
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
        @rtype GitProjectHelper
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

        @return tuple of reference to instantiated version control and
            activation status
        @rtype tuple of (Git, bool)
        """
        from eric7.Plugins.VcsPlugins.vcsGit.git import Git

        self.__object = Git(self, self.__ui)

        tb = self.__ui.getToolbar("vcs")[1]
        tb.setVisible(False)
        tb.setEnabled(False)

        tb = self.__ui.getToolbar("git")[1]
        tb.setVisible(Preferences.getVCS("ShowVcsToolbar"))
        tb.setEnabled(True)

        return self.__object, True

    def deactivate(self):
        """
        Public method to deactivate this plugin.
        """
        self.__object = None

        tb = self.__ui.getToolbar("git")[1]
        tb.setVisible(False)
        tb.setEnabled(False)

        tb = self.__ui.getToolbar("vcs")[1]
        tb.setVisible(Preferences.getVCS("ShowVcsToolbar"))
        tb.setEnabled(True)

    @classmethod
    def getPreferences(cls, key):
        """
        Class method to retrieve the various settings.

        @param key the key of the value to get
        @type str
        @return the requested setting
        @rtype Any
        """
        if key in [
            "StopLogOnCopy",
            "ShowReflogInfo",
            "ShowAuthorColumns",
            "ShowCommitterColumns",
            "ShowCommitIdColumn",
            "ShowBranchesColumn",
            "ShowTagsColumn",
            "FindCopiesHarder",
            "AggressiveGC",
        ]:
            return EricUtilities.toBool(
                Preferences.getSettings().value("Git/" + key, cls.GitDefaults[key])
            )
        elif key in ["LogLimit", "CommitIdLength", "LogSubjectColumnWidth"]:
            return int(
                Preferences.getSettings().value("Git/" + key, cls.GitDefaults[key])
            )
        elif key in ["Commits", "RepositoryUrlHistory"]:
            return EricUtilities.toList(Preferences.getSettings().value("Git/" + key))
        elif key in ["LogBrowserGeometry", "StatusDialogGeometry"]:
            v = Preferences.getSettings().value("Git/" + key)
            if v is not None:
                return v
            else:
                return cls.GitDefaults[key]
        elif key in ["LogBrowserSplitterStates", "StatusDialogSplitterStates"]:
            states = Preferences.getSettings().value("Git/" + key)
            if states is not None:
                return states
            else:
                return cls.GitDefaults[key]
        else:
            return Preferences.getSettings().value("Git/" + key, cls.GitDefaults[key])

    @classmethod
    def setPreferences(cls, key, value):
        """
        Class method to store the various settings.

        @param key the key of the setting to be set
        @type str
        @param value the value to be set
        @type Any
        """
        Preferences.getSettings().setValue("Git/" + key, value)

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


#
# eflag: noqa = M801
