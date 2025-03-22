# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the VCS project helper for Git.
"""

import os
import pathlib

from PyQt6.QtWidgets import QInputDialog, QMenu, QToolBar

from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.VCS.ProjectHelper import VcsProjectHelper


class GitProjectHelper(VcsProjectHelper):
    """
    Class implementing the VCS project helper for Git.
    """

    def __init__(self, vcsObject, projectObject, parent=None, name=None):
        """
        Constructor

        @param vcsObject reference to the vcs object
        @type Git
        @param projectObject reference to the project object
        @type Project
        @param parent parent widget
        @type QWidget
        @param name name of this object
        @type str
        """
        VcsProjectHelper.__init__(self, vcsObject, projectObject, parent, name)

    def setObjects(self, vcsObject, projectObject):
        """
        Public method to set references to the vcs and project objects.

        @param vcsObject reference to the vcs object
        @type Git
        @param projectObject reference to the project object
        @type Project
        """
        self.vcs = vcsObject
        self.project = projectObject

    def getProject(self):
        """
        Public method to get a reference to the project object.

        @return reference to the project object
        @rtype Project
        """
        return self.project

    def getActions(self):
        """
        Public method to get a list of all actions.

        @return list of all actions
        @rtype list of EricAction
        """
        actions = self.actions[:]
        return actions

    def initActions(self):
        """
        Public method to generate the action objects.
        """
        self.vcsNewAct = EricAction(
            self.tr("New from repository"),
            EricPixmapCache.getIcon("vcsCheckout"),
            self.tr("&New from repository..."),
            0,
            0,
            self,
            "git_new",
        )
        self.vcsNewAct.setStatusTip(
            self.tr("Create (clone) a new project from a Git repository")
        )
        self.vcsNewAct.setWhatsThis(
            self.tr(
                """<b>New from repository</b>"""
                """<p>This creates (clones) a new local project from """
                """a Git repository.</p>"""
            )
        )
        self.vcsNewAct.triggered.connect(self._vcsCheckout)
        self.actions.append(self.vcsNewAct)

        self.gitFetchAct = EricAction(
            self.tr("Fetch changes"),
            EricPixmapCache.getIcon("vcsUpdate"),
            self.tr("Fetch changes"),
            0,
            0,
            self,
            "git_fetch",
        )
        self.gitFetchAct.setStatusTip(self.tr("Fetch changes from a remote repository"))
        self.gitFetchAct.setWhatsThis(
            self.tr(
                """<b>Fetch changes</b>"""
                """<p>This fetches changes from a remote repository into the """
                """local repository.</p>"""
            )
        )
        self.gitFetchAct.triggered.connect(self.__gitFetch)
        self.actions.append(self.gitFetchAct)

        self.gitPullAct = EricAction(
            self.tr("Pull changes"),
            EricPixmapCache.getIcon("vcsUpdate"),
            self.tr("Pull changes"),
            0,
            0,
            self,
            "git_pull",
        )
        self.gitPullAct.setStatusTip(
            self.tr("Pull changes from a remote repository and update the work area")
        )
        self.gitPullAct.setWhatsThis(
            self.tr(
                """<b>Pull changes</b>"""
                """<p>This pulls changes from a remote repository into the """
                """local repository and updates the work area.</p>"""
            )
        )
        self.gitPullAct.triggered.connect(self.__gitPull)
        self.actions.append(self.gitPullAct)

        self.vcsCommitAct = EricAction(
            self.tr("Commit changes to repository"),
            EricPixmapCache.getIcon("vcsCommit"),
            self.tr("Commit changes to repository..."),
            0,
            0,
            self,
            "git_commit",
        )
        self.vcsCommitAct.setStatusTip(
            self.tr("Commit changes of the local project to the Git repository")
        )
        self.vcsCommitAct.setWhatsThis(
            self.tr(
                """<b>Commit changes to repository</b>"""
                """<p>This commits changes of the local project to the """
                """Git repository.</p>"""
            )
        )
        self.vcsCommitAct.triggered.connect(self._vcsCommit)
        self.actions.append(self.vcsCommitAct)

        self.gitPushAct = EricAction(
            self.tr("Push changes"),
            EricPixmapCache.getIcon("vcsCommit"),
            self.tr("Push changes"),
            0,
            0,
            self,
            "git_push",
        )
        self.gitPushAct.setStatusTip(self.tr("Push changes to a remote repository"))
        self.gitPushAct.setWhatsThis(
            self.tr(
                """<b>Push changes</b>"""
                """<p>This pushes changes from the local repository to a """
                """remote repository.</p>"""
            )
        )
        self.gitPushAct.triggered.connect(self.__gitPush)
        self.actions.append(self.gitPushAct)

        self.vcsExportAct = EricAction(
            self.tr("Export from repository"),
            EricPixmapCache.getIcon("vcsExport"),
            self.tr("&Export from repository..."),
            0,
            0,
            self,
            "git_export_repo",
        )
        self.vcsExportAct.setStatusTip(self.tr("Export a project from the repository"))
        self.vcsExportAct.setWhatsThis(
            self.tr(
                """<b>Export from repository</b>"""
                """<p>This exports a project from the repository.</p>"""
            )
        )
        self.vcsExportAct.triggered.connect(self._vcsExport)
        self.actions.append(self.vcsExportAct)

        self.gitLogBrowserAct = EricAction(
            self.tr("Show log browser"),
            EricPixmapCache.getIcon("vcsLog"),
            self.tr("Show log browser"),
            0,
            0,
            self,
            "git_log_browser",
        )
        self.gitLogBrowserAct.setStatusTip(
            self.tr("Show a dialog to browse the log of the local project")
        )
        self.gitLogBrowserAct.setWhatsThis(
            self.tr(
                """<b>Show log browser</b>"""
                """<p>This shows a dialog to browse the log of the local"""
                """ project. A limited number of entries is shown first."""
                """ More can be retrieved later on.</p>"""
            )
        )
        self.gitLogBrowserAct.triggered.connect(self._vcsLogBrowser)
        self.actions.append(self.gitLogBrowserAct)

        self.gitReflogBrowserAct = EricAction(
            self.tr("Show reflog browser"),
            EricPixmapCache.getIcon("vcsLog"),
            self.tr("Show reflog browser"),
            0,
            0,
            self,
            "git_reflog_browser",
        )
        self.gitReflogBrowserAct.setStatusTip(
            self.tr("Show a dialog to browse the reflog of the local project")
        )
        self.gitReflogBrowserAct.setWhatsThis(
            self.tr(
                """<b>Show reflog browser</b>"""
                """<p>This shows a dialog to browse the reflog of the local"""
                """ project. A limited number of entries is shown first."""
                """ More can be retrieved later on.</p>"""
            )
        )
        self.gitReflogBrowserAct.triggered.connect(self.__gitReflogBrowser)
        self.actions.append(self.gitReflogBrowserAct)

        self.vcsDiffAct = EricAction(
            self.tr("Show differences"),
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show &differences..."),
            0,
            0,
            self,
            "git_diff",
        )
        self.vcsDiffAct.setStatusTip(
            self.tr("Show the differences of the local project to the repository")
        )
        self.vcsDiffAct.setWhatsThis(
            self.tr(
                """<b>Show differences</b>"""
                """<p>This shows differences of the local project to the"""
                """ repository.</p>"""
            )
        )
        self.vcsDiffAct.triggered.connect(self._vcsDiff)
        self.actions.append(self.vcsDiffAct)

        self.gitExtDiffAct = EricAction(
            self.tr("Show differences (extended)"),
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences (extended) ..."),
            0,
            0,
            self,
            "git_extendeddiff",
        )
        self.gitExtDiffAct.setStatusTip(
            self.tr("Show the difference of revisions of the project to the repository")
        )
        self.gitExtDiffAct.setWhatsThis(
            self.tr(
                """<b>Show differences (extended)</b>"""
                """<p>This shows differences of selectable revisions of the"""
                """ project.</p>"""
            )
        )
        self.gitExtDiffAct.triggered.connect(self.__gitExtendedDiff)
        self.actions.append(self.gitExtDiffAct)

        self.vcsStatusAct = EricAction(
            self.tr("Show status"),
            EricPixmapCache.getIcon("vcsStatus"),
            self.tr("Show &status..."),
            0,
            0,
            self,
            "git_status",
        )
        self.vcsStatusAct.setStatusTip(self.tr("Show the status of the local project"))
        self.vcsStatusAct.setWhatsThis(
            self.tr(
                """<b>Show status</b>"""
                """<p>This shows the status of the local project.</p>"""
            )
        )
        self.vcsStatusAct.triggered.connect(self._vcsStatus)
        self.actions.append(self.vcsStatusAct)

        self.vcsSwitchAct = EricAction(
            self.tr("Switch"),
            EricPixmapCache.getIcon("vcsSwitch"),
            self.tr("S&witch..."),
            0,
            0,
            self,
            "git_switch",
        )
        self.vcsSwitchAct.setStatusTip(
            self.tr("Switch the working directory to another revision")
        )
        self.vcsSwitchAct.setWhatsThis(
            self.tr(
                """<b>Switch</b>"""
                """<p>This switches the working directory to another"""
                """ revision.</p>"""
            )
        )
        self.vcsSwitchAct.triggered.connect(self._vcsSwitch)
        self.actions.append(self.vcsSwitchAct)

        self.vcsTagAct = EricAction(
            self.tr("Tag in repository"),
            EricPixmapCache.getIcon("vcsTag"),
            self.tr("&Tag in repository..."),
            0,
            0,
            self,
            "git_tag",
        )
        self.vcsTagAct.setStatusTip(
            self.tr("Perform tag operations for the local project")
        )
        self.vcsTagAct.setWhatsThis(
            self.tr(
                """<b>Tag in repository</b>"""
                """<p>This performs selectable tag operations for the local"""
                """ project.</p>"""
            )
        )
        self.vcsTagAct.triggered.connect(self._vcsTag)
        self.actions.append(self.vcsTagAct)

        self.gitTagListAct = EricAction(
            self.tr("List tags"), self.tr("&List tags..."), 0, 0, self, "git_list_tags"
        )
        self.gitTagListAct.setStatusTip(self.tr("List tags of the project"))
        self.gitTagListAct.setWhatsThis(
            self.tr("""<b>List tags</b><p>This lists the tags of the project.</p>""")
        )
        self.gitTagListAct.triggered.connect(self.__gitTagList)
        self.actions.append(self.gitTagListAct)

        self.gitDescribeTagAct = EricAction(
            self.tr("Show most recent tag"),
            self.tr("Show most recent tag"),
            0,
            0,
            self,
            "git_describe_tag",
        )
        self.gitDescribeTagAct.setStatusTip(
            self.tr("Show the most recent tag reachable from the work tree")
        )
        self.gitDescribeTagAct.setWhatsThis(
            self.tr(
                """<b>Show most recent tag</b>"""
                """<p>This shows the most recent tag reachable from the work"""
                """ tree.</p>"""
            )
        )
        self.gitDescribeTagAct.triggered.connect(self.__gitDescribeTag)
        self.actions.append(self.gitDescribeTagAct)

        self.gitBranchListAct = EricAction(
            self.tr("List branches"),
            self.tr("&List branches..."),
            0,
            0,
            self,
            "git_list_branches",
        )
        self.gitBranchListAct.setStatusTip(self.tr("List branches of the project"))
        self.gitBranchListAct.setWhatsThis(
            self.tr(
                """<b>List branches</b>"""
                """<p>This lists the branches of the project.</p>"""
            )
        )
        self.gitBranchListAct.triggered.connect(self.__gitBranchList)
        self.actions.append(self.gitBranchListAct)

        self.gitMergedBranchListAct = EricAction(
            self.tr("List merged branches"),
            self.tr("List &merged branches..."),
            0,
            0,
            self,
            "git_list_merged_branches",
        )
        self.gitMergedBranchListAct.setStatusTip(
            self.tr("List merged branches of the project")
        )
        self.gitMergedBranchListAct.setWhatsThis(
            self.tr(
                """<b>List merged branches</b>"""
                """<p>This lists the merged branches of the project.</p>"""
            )
        )
        self.gitMergedBranchListAct.triggered.connect(self.__gitMergedBranchList)
        self.actions.append(self.gitMergedBranchListAct)

        self.gitNotMergedBranchListAct = EricAction(
            self.tr("List non-merged branches"),
            self.tr("List &non-merged branches..."),
            0,
            0,
            self,
            "git_list_non_merged_branches",
        )
        self.gitNotMergedBranchListAct.setStatusTip(
            self.tr("List non-merged branches of the project")
        )
        self.gitNotMergedBranchListAct.setWhatsThis(
            self.tr(
                """<b>List non-merged branches</b>"""
                """<p>This lists the non-merged branches of the project.</p>"""
            )
        )
        self.gitNotMergedBranchListAct.triggered.connect(self.__gitNotMergedBranchList)
        self.actions.append(self.gitNotMergedBranchListAct)

        self.gitBranchAct = EricAction(
            self.tr("Branch in repository"),
            EricPixmapCache.getIcon("vcsBranch"),
            self.tr("&Branch in repository..."),
            0,
            0,
            self,
            "git_branch",
        )
        self.gitBranchAct.setStatusTip(
            self.tr("Perform branch operations for the local project")
        )
        self.gitBranchAct.setWhatsThis(
            self.tr(
                """<b>Branch in repository</b>"""
                """<p>This performs selectable branch operations for the local"""
                """ project.</p>"""
            )
        )
        self.gitBranchAct.triggered.connect(self.__gitBranch)
        self.actions.append(self.gitBranchAct)

        self.gitDeleteRemoteBranchAct = EricAction(
            self.tr("Delete Remote Branch"),
            self.tr("&Delete Remote Branch..."),
            0,
            0,
            self,
            "git_delete_remote_branch",
        )
        self.gitDeleteRemoteBranchAct.setStatusTip(
            self.tr("Delete a branch from a remote repository")
        )
        self.gitDeleteRemoteBranchAct.setWhatsThis(
            self.tr(
                """<b>Delete Remote Branch</b>"""
                """<p>This deletes a branch from a remote repository.</p>"""
            )
        )
        self.gitDeleteRemoteBranchAct.triggered.connect(self.__gitDeleteBranch)
        self.actions.append(self.gitDeleteRemoteBranchAct)

        self.gitShowBranchAct = EricAction(
            self.tr("Show current branch"),
            self.tr("Show current branch"),
            0,
            0,
            self,
            "git_show_branch",
        )
        self.gitShowBranchAct.setStatusTip(
            self.tr("Show the current branch of the project")
        )
        self.gitShowBranchAct.setWhatsThis(
            self.tr(
                """<b>Show current branch</b>"""
                """<p>This shows the current branch of the project.</p>"""
            )
        )
        self.gitShowBranchAct.triggered.connect(self.__gitShowBranch)
        self.actions.append(self.gitShowBranchAct)

        self.vcsRevertAct = EricAction(
            self.tr("Revert changes"),
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Re&vert changes"),
            0,
            0,
            self,
            "git_revert",
        )
        self.vcsRevertAct.setStatusTip(
            self.tr("Revert all changes made to the local project")
        )
        self.vcsRevertAct.setWhatsThis(
            self.tr(
                """<b>Revert changes</b>"""
                """<p>This reverts all changes made to the local project.</p>"""
            )
        )
        self.vcsRevertAct.triggered.connect(self.__gitRevert)
        self.actions.append(self.vcsRevertAct)

        self.gitUnstageAct = EricAction(
            self.tr("Unstage changes"),
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("&Unstage changes"),
            0,
            0,
            self,
            "git_revert",
        )
        self.gitUnstageAct.setStatusTip(
            self.tr("Unstage all changes made to the local project")
        )
        self.gitUnstageAct.setWhatsThis(
            self.tr(
                """<b>Unstage changes</b>"""
                """<p>This unstages all changes made to the local project.</p>"""
            )
        )
        self.gitUnstageAct.triggered.connect(self.__gitUnstage)
        self.actions.append(self.gitUnstageAct)

        self.vcsMergeAct = EricAction(
            self.tr("Merge"),
            EricPixmapCache.getIcon("vcsMerge"),
            self.tr("Mer&ge changes..."),
            0,
            0,
            self,
            "git_merge",
        )
        self.vcsMergeAct.setStatusTip(self.tr("Merge changes into the local project"))
        self.vcsMergeAct.setWhatsThis(
            self.tr(
                """<b>Merge</b>"""
                """<p>This merges changes into the local project.</p>"""
            )
        )
        self.vcsMergeAct.triggered.connect(self._vcsMerge)
        self.actions.append(self.vcsMergeAct)

        self.gitCancelMergeAct = EricAction(
            self.tr("Cancel uncommitted/failed merge"),
            self.tr("Cancel uncommitted/failed merge"),
            0,
            0,
            self,
            "git_cancel_merge",
        )
        self.gitCancelMergeAct.setStatusTip(
            self.tr("Cancel an uncommitted or failed merge and lose all changes")
        )
        self.gitCancelMergeAct.setWhatsThis(
            self.tr(
                """<b>Cancel uncommitted/failed merge</b>"""
                """<p>This cancels an uncommitted or failed merge causing all"""
                """ changes to be lost.</p>"""
            )
        )
        self.gitCancelMergeAct.triggered.connect(self.__gitCancelMerge)
        self.actions.append(self.gitCancelMergeAct)

        self.gitCommitMergeAct = EricAction(
            self.tr("Commit failed merge"),
            self.tr("Commit failed merge"),
            0,
            0,
            self,
            "git_commit_merge",
        )
        self.gitCommitMergeAct.setStatusTip(
            self.tr("Commit a failed merge after conflicts have been resolved")
        )
        self.gitCommitMergeAct.setWhatsThis(
            self.tr(
                """<b>Commit failed merge</b>"""
                """<p>This commits a failed merge after conflicts have been"""
                """ resolved.</p>"""
            )
        )
        self.gitCommitMergeAct.triggered.connect(self.__gitCommitMerge)
        self.actions.append(self.gitCommitMergeAct)

        self.vcsCleanupAct = EricAction(
            self.tr("Cleanup"), self.tr("Cleanu&p"), 0, 0, self, "git_cleanup"
        )
        self.vcsCleanupAct.setStatusTip(self.tr("Cleanup the local project"))
        self.vcsCleanupAct.setWhatsThis(
            self.tr(
                """<b>Cleanup</b>"""
                """<p>This performs a cleanup of the local project.</p>"""
            )
        )
        self.vcsCleanupAct.triggered.connect(self._vcsCleanup)
        self.actions.append(self.vcsCleanupAct)

        self.vcsCommandAct = EricAction(
            self.tr("Execute command"),
            self.tr("E&xecute command..."),
            0,
            0,
            self,
            "git_command",
        )
        self.vcsCommandAct.setStatusTip(self.tr("Execute an arbitrary Git command"))
        self.vcsCommandAct.setWhatsThis(
            self.tr(
                """<b>Execute command</b>"""
                """<p>This opens a dialog to enter an arbitrary Git"""
                """ command.</p>"""
            )
        )
        self.vcsCommandAct.triggered.connect(self._vcsCommand)
        self.actions.append(self.vcsCommandAct)

        self.gitConfigAct = EricAction(
            self.tr("Configure"), self.tr("Configure..."), 0, 0, self, "git_configure"
        )
        self.gitConfigAct.setStatusTip(
            self.tr("Show the configuration dialog with the Git page selected")
        )
        self.gitConfigAct.setWhatsThis(
            self.tr(
                """<b>Configure</b>"""
                """<p>Show the configuration dialog with the Git page"""
                """ selected.</p>"""
            )
        )
        self.gitConfigAct.triggered.connect(self.__gitConfigure)
        self.actions.append(self.gitConfigAct)

        self.gitRemotesShowAct = EricAction(
            self.tr("Show Remotes"),
            self.tr("Show Remotes..."),
            0,
            0,
            self,
            "git_show_remotes",
        )
        self.gitRemotesShowAct.setStatusTip(
            self.tr("Show the available remote repositories")
        )
        self.gitRemotesShowAct.setWhatsThis(
            self.tr(
                """<b>Show Remotes</b>"""
                """<p>This shows the remote repositories available for"""
                """ pulling, fetching and pushing.</p>"""
            )
        )
        self.gitRemotesShowAct.triggered.connect(self.__gitShowRemotes)
        self.actions.append(self.gitRemotesShowAct)

        self.gitRemoteShowAct = EricAction(
            self.tr("Show Remote Info"),
            self.tr("Show Remote Info..."),
            0,
            0,
            self,
            "git_show_remote_info",
        )
        self.gitRemoteShowAct.setStatusTip(
            self.tr("Show information about a remote repository")
        )
        self.gitRemoteShowAct.setWhatsThis(
            self.tr(
                """<b>Show Remotes</b>"""
                """<p>This shows the remote repositories available for"""
                """ pulling, fetching and pushing.</p>"""
            )
        )
        self.gitRemoteShowAct.triggered.connect(self.__gitShowRemote)
        self.actions.append(self.gitRemoteShowAct)

        self.gitRemoteAddAct = EricAction(
            self.tr("Add"), self.tr("Add..."), 0, 0, self, "git_add_remote"
        )
        self.gitRemoteAddAct.setStatusTip(self.tr("Add a remote repository"))
        self.gitRemoteAddAct.setWhatsThis(
            self.tr("""<b>Add</b><p>This adds a remote repository.</p>""")
        )
        self.gitRemoteAddAct.triggered.connect(self.__gitAddRemote)
        self.actions.append(self.gitRemoteAddAct)

        self.gitRemoteRemoveAct = EricAction(
            self.tr("Remove"), self.tr("Remove..."), 0, 0, self, "git_remove_remote"
        )
        self.gitRemoteRemoveAct.setStatusTip(self.tr("Remove a remote repository"))
        self.gitRemoteRemoveAct.setWhatsThis(
            self.tr("""<b>Remove</b><p>This removes a remote repository.</p>""")
        )
        self.gitRemoteRemoveAct.triggered.connect(self.__gitRemoveRemote)
        self.actions.append(self.gitRemoteRemoveAct)

        self.gitRemotePruneAct = EricAction(
            self.tr("Prune"), self.tr("Prune..."), 0, 0, self, "git_prune_remote"
        )
        self.gitRemotePruneAct.setStatusTip(
            self.tr("Prune stale remote-tracking branches of a remote repository")
        )
        self.gitRemotePruneAct.setWhatsThis(
            self.tr(
                """<b>Prune</b>"""
                """<p>This prunes stale remote-tracking branches of a remote"""
                """ repository.</p>"""
            )
        )
        self.gitRemotePruneAct.triggered.connect(self.__gitPruneRemote)
        self.actions.append(self.gitRemotePruneAct)

        self.gitRemoteRenameAct = EricAction(
            self.tr("Rename"), self.tr("Rename..."), 0, 0, self, "git_rename_remote"
        )
        self.gitRemoteRenameAct.setStatusTip(self.tr("Rename a remote repository"))
        self.gitRemoteRenameAct.setWhatsThis(
            self.tr("""<b>Rename</b><p>This renames a remote repository.</p>""")
        )
        self.gitRemoteRenameAct.triggered.connect(self.__gitRenameRemote)
        self.actions.append(self.gitRemoteRenameAct)

        self.gitRemoteChangeUrlAct = EricAction(
            self.tr("Change URL"),
            self.tr("Change URL..."),
            0,
            0,
            self,
            "git_change_remote_url",
        )
        self.gitRemoteChangeUrlAct.setStatusTip(
            self.tr("Change the URL of a remote repository")
        )
        self.gitRemoteChangeUrlAct.setWhatsThis(
            self.tr(
                """<b>Change URL</b>"""
                """<p>This changes the URL of a remote repository.</p>"""
            )
        )
        self.gitRemoteChangeUrlAct.triggered.connect(self.__gitChangeRemoteUrl)
        self.actions.append(self.gitRemoteChangeUrlAct)

        self.gitRemoteCredentialsAct = EricAction(
            self.tr("Credentials"),
            self.tr("Credentials..."),
            0,
            0,
            self,
            "git_remote_credentials",
        )
        self.gitRemoteCredentialsAct.setStatusTip(
            self.tr("Change or set the user credentials of a remote repository")
        )
        self.gitRemoteCredentialsAct.setWhatsThis(
            self.tr(
                """<b>Credentials</b>"""
                """<p>This changes or sets the user credentials of a"""
                """ remote repository.</p>"""
            )
        )
        self.gitRemoteCredentialsAct.triggered.connect(self.__gitRemoteCredentials)
        self.actions.append(self.gitRemoteCredentialsAct)

        self.gitCherryPickAct = EricAction(
            self.tr("Copy Commits"),
            EricPixmapCache.getIcon("vcsGraft"),
            self.tr("Copy Commits"),
            0,
            0,
            self,
            "git_cherrypick",
        )
        self.gitCherryPickAct.setStatusTip(
            self.tr("Copies commits into the current branch")
        )
        self.gitCherryPickAct.setWhatsThis(
            self.tr(
                """<b>Copy Commits</b>"""
                """<p>This copies commits on top of the current branch.</p>"""
            )
        )
        self.gitCherryPickAct.triggered.connect(self.__gitCherryPick)
        self.actions.append(self.gitCherryPickAct)

        self.gitCherryPickContinueAct = EricAction(
            self.tr("Continue Copying Session"),
            self.tr("Continue Copying Session"),
            0,
            0,
            self,
            "git_cherrypick_continue",
        )
        self.gitCherryPickContinueAct.setStatusTip(
            self.tr("Continue the last copying session after conflicts were resolved")
        )
        self.gitCherryPickContinueAct.setWhatsThis(
            self.tr(
                """<b>Continue Copying Session</b>"""
                """<p>This continues the last copying session after conflicts"""
                """ were resolved.</p>"""
            )
        )
        self.gitCherryPickContinueAct.triggered.connect(self.__gitCherryPickContinue)
        self.actions.append(self.gitCherryPickContinueAct)

        self.gitCherryPickQuitAct = EricAction(
            self.tr("Quit Copying Session"),
            self.tr("Quit Copying Session"),
            0,
            0,
            self,
            "git_cherrypick_quit",
        )
        self.gitCherryPickQuitAct.setStatusTip(
            self.tr("Quit the current copying session")
        )
        self.gitCherryPickQuitAct.setWhatsThis(
            self.tr(
                """<b>Quit Copying Session</b>"""
                """<p>This quits the current copying session.</p>"""
            )
        )
        self.gitCherryPickQuitAct.triggered.connect(self.__gitCherryPickQuit)
        self.actions.append(self.gitCherryPickQuitAct)

        self.gitCherryPickAbortAct = EricAction(
            self.tr("Cancel Copying Session"),
            self.tr("Cancel Copying Session"),
            0,
            0,
            self,
            "git_cherrypick_abort",
        )
        self.gitCherryPickAbortAct.setStatusTip(
            self.tr(
                "Cancel the current copying session and return to the previous state"
            )
        )
        self.gitCherryPickAbortAct.setWhatsThis(
            self.tr(
                """<b>Cancel Copying Session</b>"""
                """<p>This cancels the current copying session and returns to"""
                """ the previous state.</p>"""
            )
        )
        self.gitCherryPickAbortAct.triggered.connect(self.__gitCherryPickAbort)
        self.actions.append(self.gitCherryPickAbortAct)

        self.gitStashAct = EricAction(
            self.tr("Stash changes"),
            self.tr("Stash changes..."),
            0,
            0,
            self,
            "git_stash",
        )
        self.gitStashAct.setStatusTip(
            self.tr("Stash all current changes of the project")
        )
        self.gitStashAct.setWhatsThis(
            self.tr(
                """<b>Stash changes</b>"""
                """<p>This stashes all current changes of the project.</p>"""
            )
        )
        self.gitStashAct.triggered.connect(self.__gitStashSave)
        self.actions.append(self.gitStashAct)

        self.gitStashBrowserAct = EricAction(
            self.tr("Show stash browser"),
            self.tr("Show stash browser..."),
            0,
            0,
            self,
            "git_stash_browser",
        )
        self.gitStashBrowserAct.setStatusTip(self.tr("Show a dialog with all stashes"))
        self.gitStashBrowserAct.setWhatsThis(
            self.tr(
                """<b>Show stash browser...</b>"""
                """<p>This shows a dialog listing all available stashes."""
                """ Actions on these stashes may be executed via the"""
                """ context menu.</p>"""
            )
        )
        self.gitStashBrowserAct.triggered.connect(self.__gitStashBrowser)
        self.actions.append(self.gitStashBrowserAct)

        self.gitStashShowAct = EricAction(
            self.tr("Show stash"),
            self.tr("Show stash..."),
            0,
            0,
            self,
            "git_stash_show",
        )
        self.gitStashShowAct.setStatusTip(
            self.tr("Show a dialog with a patch of a stash")
        )
        self.gitStashShowAct.setWhatsThis(
            self.tr(
                """<b>Show stash...</b>"""
                """<p>This shows a dialog with a patch of a selectable"""
                """ stash.</p>"""
            )
        )
        self.gitStashShowAct.triggered.connect(self.__gitStashShow)
        self.actions.append(self.gitStashShowAct)

        self.gitStashApplyAct = EricAction(
            self.tr("Restore && Keep"),
            self.tr("Restore && Keep"),
            0,
            0,
            self,
            "git_stash_apply",
        )
        self.gitStashApplyAct.setStatusTip(self.tr("Restore a stash but keep it"))
        self.gitStashApplyAct.setWhatsThis(
            self.tr(
                """<b>Restore &amp; Keep</b>"""
                """<p>This restores a selectable stash and keeps it.</p>"""
            )
        )
        self.gitStashApplyAct.triggered.connect(self.__gitStashApply)
        self.actions.append(self.gitStashApplyAct)

        self.gitStashPopAct = EricAction(
            self.tr("Restore && Delete"),
            self.tr("Restore && Delete"),
            0,
            0,
            self,
            "git_stash_pop",
        )
        self.gitStashPopAct.setStatusTip(self.tr("Restore a stash and delete it"))
        self.gitStashPopAct.setWhatsThis(
            self.tr(
                """<b>Restore &amp; Delete</b>"""
                """<p>This restores a selectable stash and deletes it.</p>"""
            )
        )
        self.gitStashPopAct.triggered.connect(self.__gitStashPop)
        self.actions.append(self.gitStashPopAct)

        self.gitStashBranchAct = EricAction(
            self.tr("Create Branch"),
            self.tr("Create Branch"),
            0,
            0,
            self,
            "git_stash_branch",
        )
        self.gitStashBranchAct.setStatusTip(
            self.tr("Create a new branch and restore a stash into it")
        )
        self.gitStashBranchAct.setWhatsThis(
            self.tr(
                """<b>Create Branch</b>"""
                """<p>This creates a new branch and restores a stash into"""
                """ it.</p>"""
            )
        )
        self.gitStashBranchAct.triggered.connect(self.__gitStashBranch)
        self.actions.append(self.gitStashBranchAct)

        self.gitStashDropAct = EricAction(
            self.tr("Delete"), self.tr("Delete"), 0, 0, self, "git_stash_delete"
        )
        self.gitStashDropAct.setStatusTip(self.tr("Delete a stash"))
        self.gitStashDropAct.setWhatsThis(
            self.tr("""<b>Delete</b><p>This deletes a stash.</p>""")
        )
        self.gitStashDropAct.triggered.connect(self.__gitStashDrop)
        self.actions.append(self.gitStashDropAct)

        self.gitStashClearAct = EricAction(
            self.tr("Delete All"),
            self.tr("Delete All"),
            0,
            0,
            self,
            "git_stash_delete_all",
        )
        self.gitStashClearAct.setStatusTip(self.tr("Delete all stashes"))
        self.gitStashClearAct.setWhatsThis(
            self.tr("""<b>Delete All</b><p>This deletes all stashes.</p>""")
        )
        self.gitStashClearAct.triggered.connect(self.__gitStashClear)
        self.actions.append(self.gitStashClearAct)

        self.gitEditUserConfigAct = EricAction(
            self.tr("Edit user configuration"),
            self.tr("Edit user configuration..."),
            0,
            0,
            self,
            "git_user_configure",
        )
        self.gitEditUserConfigAct.setStatusTip(
            self.tr("Show an editor to edit the user configuration file")
        )
        self.gitEditUserConfigAct.setWhatsThis(
            self.tr(
                """<b>Edit user configuration</b>"""
                """<p>Show an editor to edit the user configuration file.</p>"""
            )
        )
        self.gitEditUserConfigAct.triggered.connect(self.__gitEditUserConfig)
        self.actions.append(self.gitEditUserConfigAct)

        self.gitRepoConfigAct = EricAction(
            self.tr("Edit repository configuration"),
            self.tr("Edit repository configuration..."),
            0,
            0,
            self,
            "git_repo_configure",
        )
        self.gitRepoConfigAct.setStatusTip(
            self.tr("Show an editor to edit the repository configuration file")
        )
        self.gitRepoConfigAct.setWhatsThis(
            self.tr(
                """<b>Edit repository configuration</b>"""
                """<p>Show an editor to edit the repository configuration"""
                """ file.</p>"""
            )
        )
        self.gitRepoConfigAct.triggered.connect(self.__gitEditRepoConfig)
        self.actions.append(self.gitRepoConfigAct)

        self.gitCreateIgnoreAct = EricAction(
            self.tr("Create .gitignore"),
            self.tr("Create .gitignore"),
            0,
            0,
            self,
            "git_create_ignore",
        )
        self.gitCreateIgnoreAct.setStatusTip(
            self.tr("Create a .gitignore file with default values")
        )
        self.gitCreateIgnoreAct.setWhatsThis(
            self.tr(
                """<b>Create .gitignore</b>"""
                """<p>This creates a .gitignore file with default values.</p>"""
            )
        )
        self.gitCreateIgnoreAct.triggered.connect(self.__gitCreateIgnore)
        self.actions.append(self.gitCreateIgnoreAct)

        self.gitShowConfigAct = EricAction(
            self.tr("Show combined configuration settings"),
            self.tr("Show combined configuration settings..."),
            0,
            0,
            self,
            "git_show_config",
        )
        self.gitShowConfigAct.setStatusTip(
            self.tr(
                "Show the combined configuration settings from all configuration"
                " files"
            )
        )
        self.gitShowConfigAct.setWhatsThis(
            self.tr(
                """<b>Show combined configuration settings</b>"""
                """<p>This shows the combined configuration settings"""
                """ from all configuration files.</p>"""
            )
        )
        self.gitShowConfigAct.triggered.connect(self.__gitShowConfig)
        self.actions.append(self.gitShowConfigAct)

        self.gitVerifyAct = EricAction(
            self.tr("Verify repository"),
            self.tr("Verify repository..."),
            0,
            0,
            self,
            "git_verify",
        )
        self.gitVerifyAct.setStatusTip(
            self.tr("Verify the connectivity and validity of objects of the database")
        )
        self.gitVerifyAct.setWhatsThis(
            self.tr(
                """<b>Verify repository</b>"""
                """<p>This verifies the connectivity and validity of objects"""
                """ of the database.</p>"""
            )
        )
        self.gitVerifyAct.triggered.connect(self.__gitVerify)
        self.actions.append(self.gitVerifyAct)

        self.gitHouseKeepingAct = EricAction(
            self.tr("Optimize repository"),
            self.tr("Optimize repository..."),
            0,
            0,
            self,
            "git_housekeeping",
        )
        self.gitHouseKeepingAct.setStatusTip(
            self.tr("Cleanup and optimize the local repository")
        )
        self.gitHouseKeepingAct.setWhatsThis(
            self.tr(
                """<b>Optimize repository</b>"""
                """<p>This cleans up and optimizes the local repository.</p>"""
            )
        )
        self.gitHouseKeepingAct.triggered.connect(self.__gitHouseKeeping)
        self.actions.append(self.gitHouseKeepingAct)

        self.gitStatisticsAct = EricAction(
            self.tr("Repository Statistics"),
            self.tr("Repository Statistics..."),
            0,
            0,
            self,
            "git_statistics",
        )
        self.gitStatisticsAct.setStatusTip(
            self.tr("Show some statistics of the local repository")
        )
        self.gitStatisticsAct.setWhatsThis(
            self.tr(
                """<b>Repository Statistics</b>"""
                """<p>This show some statistics of the local repository.</p>"""
            )
        )
        self.gitStatisticsAct.triggered.connect(self.__gitStatistics)
        self.actions.append(self.gitStatisticsAct)

        self.gitCreateArchiveAct = EricAction(
            self.tr("Create Archive"),
            self.tr("Create Archive"),
            0,
            0,
            self,
            "git_create_archive",
        )
        self.gitCreateArchiveAct.setStatusTip(
            self.tr("Create an archive from the local repository")
        )
        self.gitCreateArchiveAct.setWhatsThis(
            self.tr(
                """<b>Create Archive</b>"""
                """<p>This creates an archive from the local repository.</p>"""
            )
        )
        self.gitCreateArchiveAct.triggered.connect(self.__gitCreateArchive)
        self.actions.append(self.gitCreateArchiveAct)

        self.gitBundleAct = EricAction(
            self.tr("Create bundle"),
            self.tr("Create bundle..."),
            0,
            0,
            self,
            "mercurial_bundle_create",
        )
        self.gitBundleAct.setStatusTip(
            self.tr("Create bundle file collecting changesets")
        )
        self.gitBundleAct.setWhatsThis(
            self.tr(
                """<b>Create bundle</b>"""
                """<p>This creates a bundle file collecting selected"""
                """ changesets (git bundle create).</p>"""
            )
        )
        self.gitBundleAct.triggered.connect(self.__gitBundle)
        self.actions.append(self.gitBundleAct)

        self.gitBundleVerifyAct = EricAction(
            self.tr("Verify bundle"),
            self.tr("Verify bundle..."),
            0,
            0,
            self,
            "mercurial_bundle_verify",
        )
        self.gitBundleVerifyAct.setStatusTip(
            self.tr("Verify the validity and applicability of a bundle file")
        )
        self.gitBundleVerifyAct.setWhatsThis(
            self.tr(
                """<b>Verify bundle</b>"""
                """<p>This verifies that a bundle file is valid and will"""
                """ apply cleanly.</p>"""
            )
        )
        self.gitBundleVerifyAct.triggered.connect(self.__gitVerifyBundle)
        self.actions.append(self.gitBundleVerifyAct)

        self.gitBundleListHeadsAct = EricAction(
            self.tr("List bundle heads"),
            self.tr("List bundle heads..."),
            0,
            0,
            self,
            "mercurial_bundle_list_heads",
        )
        self.gitBundleListHeadsAct.setStatusTip(
            self.tr("List all heads contained in a bundle file")
        )
        self.gitBundleListHeadsAct.setWhatsThis(
            self.tr(
                """<b>List bundle heads</b>"""
                """<p>This lists all heads contained in a bundle file.</p>"""
            )
        )
        self.gitBundleListHeadsAct.triggered.connect(self.__gitBundleListHeads)
        self.actions.append(self.gitBundleListHeadsAct)

        self.gitBundleApplyFetchAct = EricAction(
            self.tr("Apply Bundle (fetch)"),
            self.tr("Apply Bundle (fetch)..."),
            0,
            0,
            self,
            "mercurial_bundle_apply_fetch",
        )
        self.gitBundleApplyFetchAct.setStatusTip(
            self.tr("Apply a head of a bundle file using fetch")
        )
        self.gitBundleApplyFetchAct.setWhatsThis(
            self.tr(
                """<b>Apply Bundle (fetch)</b>"""
                """<p>This applies a head of a bundle file using fetch.</p>"""
            )
        )
        self.gitBundleApplyFetchAct.triggered.connect(self.__gitBundleFetch)
        self.actions.append(self.gitBundleApplyFetchAct)

        self.gitBundleApplyPullAct = EricAction(
            self.tr("Apply Bundle (pull)"),
            self.tr("Apply Bundle (pull)..."),
            0,
            0,
            self,
            "mercurial_bundle_apply_pull",
        )
        self.gitBundleApplyPullAct.setStatusTip(
            self.tr("Apply a head of a bundle file using pull")
        )
        self.gitBundleApplyPullAct.setWhatsThis(
            self.tr(
                """<b>Apply Bundle (pull)</b>"""
                """<p>This applies a head of a bundle file using pull.</p>"""
            )
        )
        self.gitBundleApplyPullAct.triggered.connect(self.__gitBundlePull)
        self.actions.append(self.gitBundleApplyPullAct)

        self.gitBisectStartAct = EricAction(
            self.tr("Start"), self.tr("Start"), 0, 0, self, "git_bisect_start"
        )
        self.gitBisectStartAct.setStatusTip(self.tr("Start a bisect session"))
        self.gitBisectStartAct.setWhatsThis(
            self.tr("""<b>Start</b><p>This starts a bisect session.</p>""")
        )
        self.gitBisectStartAct.triggered.connect(self.__gitBisectStart)
        self.actions.append(self.gitBisectStartAct)

        self.gitBisectStartExtendedAct = EricAction(
            self.tr("Start (Extended)"),
            self.tr("Start (Extended)"),
            0,
            0,
            self,
            "git_bisect_start_extended",
        )
        self.gitBisectStartExtendedAct.setStatusTip(
            self.tr("Start a bisect session giving a bad and optionally good commits")
        )
        self.gitBisectStartExtendedAct.setWhatsThis(
            self.tr(
                """<b>Start (Extended)</b>"""
                """<p>This starts a bisect session giving a bad and optionally"""
                """ good commits.</p>"""
            )
        )
        self.gitBisectStartExtendedAct.triggered.connect(self.__gitBisectStartExtended)
        self.actions.append(self.gitBisectStartExtendedAct)

        self.gitBisectGoodAct = EricAction(
            self.tr('Mark as "good"'),
            self.tr('Mark as "good"...'),
            0,
            0,
            self,
            "git_bisect_good",
        )
        self.gitBisectGoodAct.setStatusTip(
            self.tr("Mark a selectable revision as good")
        )
        self.gitBisectGoodAct.setWhatsThis(
            self.tr(
                """<b>Mark as "good"</b>"""
                """<p>This marks a selectable revision as good.</p>"""
            )
        )
        self.gitBisectGoodAct.triggered.connect(self.__gitBisectGood)
        self.actions.append(self.gitBisectGoodAct)

        self.gitBisectBadAct = EricAction(
            self.tr('Mark as "bad"'),
            self.tr('Mark as "bad"...'),
            0,
            0,
            self,
            "git_bisect_bad",
        )
        self.gitBisectBadAct.setStatusTip(self.tr("Mark a selectable revision as bad"))
        self.gitBisectBadAct.setWhatsThis(
            self.tr(
                """<b>Mark as "bad"</b>"""
                """<p>This marks a selectable revision as bad.</p>"""
            )
        )
        self.gitBisectBadAct.triggered.connect(self.__gitBisectBad)
        self.actions.append(self.gitBisectBadAct)

        self.gitBisectSkipAct = EricAction(
            self.tr("Skip"), self.tr("Skip..."), 0, 0, self, "git_bisect_skip"
        )
        self.gitBisectSkipAct.setStatusTip(self.tr("Skip a selectable revision"))
        self.gitBisectSkipAct.setWhatsThis(
            self.tr("""<b>Skip</b><p>This skips a selectable revision.</p>""")
        )
        self.gitBisectSkipAct.triggered.connect(self.__gitBisectSkip)
        self.actions.append(self.gitBisectSkipAct)

        self.gitBisectResetAct = EricAction(
            self.tr("Reset"), self.tr("Reset..."), 0, 0, self, "git_bisect_reset"
        )
        self.gitBisectResetAct.setStatusTip(self.tr("Reset the bisect session"))
        self.gitBisectResetAct.setWhatsThis(
            self.tr("""<b>Reset</b><p>This resets the bisect session.</p>""")
        )
        self.gitBisectResetAct.triggered.connect(self.__gitBisectReset)
        self.actions.append(self.gitBisectResetAct)

        self.gitBisectLogBrowserAct = EricAction(
            self.tr("Show bisect log browser"),
            EricPixmapCache.getIcon("vcsLog"),
            self.tr("Show bisect log browser"),
            0,
            0,
            self,
            "git_bisect_log_browser",
        )
        self.gitBisectLogBrowserAct.setStatusTip(
            self.tr("Show a dialog to browse the bisect log of the local project")
        )
        self.gitBisectLogBrowserAct.setWhatsThis(
            self.tr(
                """<b>Show bisect log browser</b>"""
                """<p>This shows a dialog to browse the bisect log of the local"""
                """ project.</p>"""
            )
        )
        self.gitBisectLogBrowserAct.triggered.connect(self.__gitBisectLogBrowser)
        self.actions.append(self.gitBisectLogBrowserAct)

        self.gitBisectCreateReplayAct = EricAction(
            self.tr("Create replay file"),
            self.tr("Create replay file"),
            0,
            0,
            self,
            "git_bisect_create_replay",
        )
        self.gitBisectCreateReplayAct.setStatusTip(
            self.tr("Create a replay file to repeat the current bisect session")
        )
        self.gitBisectCreateReplayAct.setWhatsThis(
            self.tr(
                """<b>Create replay file</b>"""
                """<p>This creates a replay file to repeat the current bisect"""
                """ session.</p>"""
            )
        )
        self.gitBisectCreateReplayAct.triggered.connect(self.__gitBisectCreateReplay)
        self.actions.append(self.gitBisectCreateReplayAct)

        self.gitBisectEditReplayAct = EricAction(
            self.tr("Edit replay file"),
            self.tr("Edit replay file"),
            0,
            0,
            self,
            "git_bisect_edit_replay",
        )
        self.gitBisectEditReplayAct.setStatusTip(self.tr("Edit a bisect replay file"))
        self.gitBisectEditReplayAct.setWhatsThis(
            self.tr(
                """<b>Edit replay file</b>"""
                """<p>This edits a bisect replay file.</p>"""
            )
        )
        self.gitBisectEditReplayAct.triggered.connect(self.__gitBisectEditReplay)
        self.actions.append(self.gitBisectEditReplayAct)

        self.gitBisectReplayAct = EricAction(
            self.tr("Replay session"),
            self.tr("Replay session"),
            0,
            0,
            self,
            "git_bisect_replay",
        )
        self.gitBisectReplayAct.setStatusTip(
            self.tr("Replay a bisect session from file")
        )
        self.gitBisectReplayAct.setWhatsThis(
            self.tr(
                """<b>Replay session</b>"""
                """<p>This replays a bisect session from file.</p>"""
            )
        )
        self.gitBisectReplayAct.triggered.connect(self.__gitBisectReplay)
        self.actions.append(self.gitBisectReplayAct)

        self.gitCheckPatchesAct = EricAction(
            self.tr("Check patch files"),
            self.tr("Check patch files"),
            0,
            0,
            self,
            "git_check_patches",
        )
        self.gitCheckPatchesAct.setStatusTip(
            self.tr("Check a list of patch files, if they would apply cleanly")
        )
        self.gitCheckPatchesAct.setWhatsThis(
            self.tr(
                """<b>Check patch files</b>"""
                """<p>This checks a list of patch files, if they would apply"""
                """ cleanly.</p>"""
            )
        )
        self.gitCheckPatchesAct.triggered.connect(self.__gitCheckPatches)
        self.actions.append(self.gitCheckPatchesAct)

        self.gitApplyPatchesAct = EricAction(
            self.tr("Apply patch files"),
            self.tr("Apply patch files"),
            0,
            0,
            self,
            "git_apply_patches",
        )
        self.gitApplyPatchesAct.setStatusTip(self.tr("Apply a list of patch files"))
        self.gitApplyPatchesAct.setWhatsThis(
            self.tr(
                """<b>Apply patch files</b>"""
                """<p>This applies a list of patch files.</p>"""
            )
        )
        self.gitApplyPatchesAct.triggered.connect(self.__gitApplyPatches)
        self.actions.append(self.gitApplyPatchesAct)

        self.gitShowPatcheStatisticsAct = EricAction(
            self.tr("Show patch statistics"),
            self.tr("Show patch statistics"),
            0,
            0,
            self,
            "git_show_patches_statistics",
        )
        self.gitShowPatcheStatisticsAct.setStatusTip(
            self.tr("Show some statistics for a list of patch files")
        )
        self.gitShowPatcheStatisticsAct.setWhatsThis(
            self.tr(
                """<b>Show patch statistics</b>"""
                """<p>This shows some statistics for a list of patch files.</p>"""
            )
        )
        self.gitShowPatcheStatisticsAct.triggered.connect(self.__gitShowPatchStatistics)
        self.actions.append(self.gitShowPatcheStatisticsAct)

        self.gitSubmoduleAddAct = EricAction(
            self.tr("Add"), self.tr("Add"), 0, 0, self, "git_submodule_add"
        )
        self.gitSubmoduleAddAct.setStatusTip(
            self.tr("Add a submodule to the current project")
        )
        self.gitSubmoduleAddAct.setWhatsThis(
            self.tr(
                """<b>Add</b>"""
                """<p>This adds a submodule to the current project.</p>"""
            )
        )
        self.gitSubmoduleAddAct.triggered.connect(self.__gitSubmoduleAdd)
        self.actions.append(self.gitSubmoduleAddAct)

        self.gitSubmodulesListAct = EricAction(
            self.tr("List"), self.tr("List"), 0, 0, self, "git_submodules_list"
        )
        self.gitSubmodulesListAct.setStatusTip(
            self.tr("List the submodule of the current project")
        )
        self.gitSubmodulesListAct.setWhatsThis(
            self.tr(
                """<b>List</b>"""
                """<p>This lists the submodules of the current project.</p>"""
            )
        )
        self.gitSubmodulesListAct.triggered.connect(self.__gitSubmodulesList)
        self.actions.append(self.gitSubmodulesListAct)

        self.gitSubmodulesInitAct = EricAction(
            self.tr("Initialize"),
            self.tr("Initialize"),
            0,
            0,
            self,
            "git_submodules_init",
        )
        self.gitSubmodulesInitAct.setStatusTip(
            self.tr("Initialize the submodules of the current project")
        )
        self.gitSubmodulesInitAct.setWhatsThis(
            self.tr(
                """<b>Initialize</b>"""
                """<p>This initializes the submodules of the current"""
                """ project.</p>"""
            )
        )
        self.gitSubmodulesInitAct.triggered.connect(self.__gitSubmodulesInit)
        self.actions.append(self.gitSubmodulesInitAct)

        self.gitSubmodulesDeinitAct = EricAction(
            self.tr("Unregister"),
            self.tr("Unregister"),
            0,
            0,
            self,
            "git_submodules_deinit",
        )
        self.gitSubmodulesDeinitAct.setStatusTip(
            self.tr("Unregister submodules of the current project")
        )
        self.gitSubmodulesDeinitAct.setWhatsThis(
            self.tr(
                """<b>Unregister</b>"""
                """<p>This unregisters submodules of the current project.</p>"""
            )
        )
        self.gitSubmodulesDeinitAct.triggered.connect(self.__gitSubmodulesDeinit)
        self.actions.append(self.gitSubmodulesDeinitAct)

        self.gitSubmodulesUpdateAct = EricAction(
            self.tr("Update"), self.tr("Update"), 0, 0, self, "git_submodules_update"
        )
        self.gitSubmodulesUpdateAct.setStatusTip(
            self.tr("Update submodules of the current project")
        )
        self.gitSubmodulesUpdateAct.setWhatsThis(
            self.tr(
                """<b>Update</b>"""
                """<p>This updates submodules of the current project.</p>"""
            )
        )
        self.gitSubmodulesUpdateAct.triggered.connect(self.__gitSubmodulesUpdate)
        self.actions.append(self.gitSubmodulesUpdateAct)

        self.gitSubmodulesUpdateInitAct = EricAction(
            self.tr("Initialize and Update"),
            self.tr("Initialize and Update"),
            0,
            0,
            self,
            "git_submodules_update_init",
        )
        self.gitSubmodulesUpdateInitAct.setStatusTip(
            self.tr("Initialize and update submodules of the current project")
        )
        self.gitSubmodulesUpdateInitAct.setWhatsThis(
            self.tr(
                """<b>Initialize and Update</b>"""
                """<p>This initializes and updates submodules of the current"""
                """ project.</p>"""
            )
        )
        self.gitSubmodulesUpdateInitAct.triggered.connect(
            self.__gitSubmodulesUpdateInit
        )
        self.actions.append(self.gitSubmodulesUpdateInitAct)

        self.gitSubmodulesUpdateRemoteAct = EricAction(
            self.tr("Fetch and Update"),
            self.tr("Fetch and Update"),
            0,
            0,
            self,
            "git_submodules_update_remote",
        )
        self.gitSubmodulesUpdateRemoteAct.setStatusTip(
            self.tr("Fetch and update submodules of the current project")
        )
        self.gitSubmodulesUpdateRemoteAct.setWhatsThis(
            self.tr(
                """<b>Fetch and Update</b>"""
                """<p>This fetches and updates submodules of the current"""
                """ project.</p>"""
            )
        )
        self.gitSubmodulesUpdateRemoteAct.triggered.connect(
            self.__gitSubmodulesUpdateRemote
        )
        self.actions.append(self.gitSubmodulesUpdateRemoteAct)

        self.gitSubmodulesUpdateOptionsAct = EricAction(
            self.tr("Update with Options"),
            self.tr("Update with Options"),
            0,
            0,
            self,
            "git_submodules_update_options",
        )
        self.gitSubmodulesUpdateOptionsAct.setStatusTip(
            self.tr(
                "Update submodules of the current project offering a dialog"
                " to enter options"
            )
        )
        self.gitSubmodulesUpdateOptionsAct.setWhatsThis(
            self.tr(
                """<b>Update with Options</b>"""
                """<p>This updates submodules of the current project"""
                """ offering a dialog to enter update options.</p>"""
            )
        )
        self.gitSubmodulesUpdateOptionsAct.triggered.connect(
            self.__gitSubmodulesUpdateOptions
        )
        self.actions.append(self.gitSubmodulesUpdateOptionsAct)

        self.gitSubmodulesSyncAct = EricAction(
            self.tr("Synchronize URLs"),
            self.tr("Synchronize URLs"),
            0,
            0,
            self,
            "git_submodules_sync",
        )
        self.gitSubmodulesSyncAct.setStatusTip(
            self.tr("Synchronize URLs of submodules of the current project")
        )
        self.gitSubmodulesSyncAct.setWhatsThis(
            self.tr(
                """<b>Synchronize URLs</b>"""
                """<p>This synchronizes URLs of submodules of the current"""
                """ project.</p>"""
            )
        )
        self.gitSubmodulesSyncAct.triggered.connect(self.__gitSubmodulesSync)
        self.actions.append(self.gitSubmodulesSyncAct)

        self.gitSubmodulesStatusAct = EricAction(
            self.tr("Show Status"),
            self.tr("Show Status"),
            0,
            0,
            self,
            "git_submodules_status",
        )
        self.gitSubmodulesStatusAct.setStatusTip(
            self.tr("Show the status of submodules of the current project")
        )
        self.gitSubmodulesStatusAct.setWhatsThis(
            self.tr(
                """<b>Show Status</b>"""
                """<p>This shows a dialog with the status of submodules of the"""
                """ current project.</p>"""
            )
        )
        self.gitSubmodulesStatusAct.triggered.connect(self.__gitSubmodulesStatus)
        self.actions.append(self.gitSubmodulesStatusAct)

        self.gitSubmodulesSummaryAct = EricAction(
            self.tr("Show Summary"),
            self.tr("Show Summary"),
            0,
            0,
            self,
            "git_submodules_summary",
        )
        self.gitSubmodulesSummaryAct.setStatusTip(
            self.tr("Show summary information for submodules of the current project")
        )
        self.gitSubmodulesSummaryAct.setWhatsThis(
            self.tr(
                """<b>Show Summary</b>"""
                """<p>This shows some summary information for submodules of the"""
                """ current project.</p>"""
            )
        )
        self.gitSubmodulesSummaryAct.triggered.connect(self.__gitSubmodulesSummary)
        self.actions.append(self.gitSubmodulesSummaryAct)

        self.gitWorktreeManagementAct = EricAction(
            self.tr("Show Worktree Management"),
            EricPixmapCache.getIcon("viewListTree"),
            self.tr("Show Worktree Management"),
            0,
            0,
            self,
            "git_worktree_management",
        )
        self.gitWorktreeManagementAct.setStatusTip(
            self.tr("Show a dialog to manage the worktree containing the project")
        )
        self.gitWorktreeManagementAct.setWhatsThis(
            self.tr(
                """<b>Show Worktree Management</b>"""
                """<p>This shows a dialog to manage the worktree containing the"""
                """ current project.</p>"""
            )
        )
        self.gitWorktreeManagementAct.triggered.connect(self.__gitWorktreeManagement)
        self.actions.append(self.gitWorktreeManagementAct)

    def initMenu(self, menu):
        """
        Public method to generate the VCS menu.

        @param menu reference to the menu to be populated
        @type QMenu
        """
        menu.clear()

        self.subMenus = []

        adminMenu = QMenu(self.tr("Administration"), menu)
        adminMenu.setTearOffEnabled(True)
        adminMenu.addAction(self.gitShowConfigAct)
        adminMenu.addAction(self.gitRepoConfigAct)
        adminMenu.addSeparator()
        adminMenu.addAction(self.gitReflogBrowserAct)
        adminMenu.addSeparator()
        adminMenu.addAction(self.gitCreateIgnoreAct)
        adminMenu.addSeparator()
        adminMenu.addAction(self.gitCreateArchiveAct)
        adminMenu.addSeparator()
        adminMenu.addAction(self.gitStatisticsAct)
        adminMenu.addAction(self.gitVerifyAct)
        adminMenu.addAction(self.gitHouseKeepingAct)
        self.subMenus.append(adminMenu)

        bundleMenu = QMenu(self.tr("Bundle Management"), menu)
        bundleMenu.setTearOffEnabled(True)
        bundleMenu.addAction(self.gitBundleAct)
        bundleMenu.addSeparator()
        bundleMenu.addAction(self.gitBundleVerifyAct)
        bundleMenu.addAction(self.gitBundleListHeadsAct)
        bundleMenu.addSeparator()
        bundleMenu.addAction(self.gitBundleApplyFetchAct)
        bundleMenu.addAction(self.gitBundleApplyPullAct)
        self.subMenus.append(bundleMenu)

        patchMenu = QMenu(self.tr("Patch Management"), menu)
        patchMenu.setTearOffEnabled(True)
        patchMenu.addAction(self.gitCheckPatchesAct)
        patchMenu.addAction(self.gitApplyPatchesAct)
        patchMenu.addSeparator()
        patchMenu.addAction(self.gitShowPatcheStatisticsAct)
        self.subMenus.append(patchMenu)

        bisectMenu = QMenu(self.tr("Bisect"), menu)
        bisectMenu.setTearOffEnabled(True)
        bisectMenu.addAction(self.gitBisectStartAct)
        bisectMenu.addAction(self.gitBisectStartExtendedAct)
        bisectMenu.addSeparator()
        bisectMenu.addAction(self.gitBisectGoodAct)
        bisectMenu.addAction(self.gitBisectBadAct)
        bisectMenu.addAction(self.gitBisectSkipAct)
        bisectMenu.addSeparator()
        bisectMenu.addAction(self.gitBisectResetAct)
        bisectMenu.addSeparator()
        bisectMenu.addAction(self.gitBisectLogBrowserAct)
        bisectMenu.addSeparator()
        bisectMenu.addAction(self.gitBisectCreateReplayAct)
        bisectMenu.addAction(self.gitBisectEditReplayAct)
        bisectMenu.addAction(self.gitBisectReplayAct)
        self.subMenus.append(bisectMenu)

        tagsMenu = QMenu(self.tr("Tags"), menu)
        tagsMenu.setIcon(EricPixmapCache.getIcon("vcsTag"))
        tagsMenu.setTearOffEnabled(True)
        tagsMenu.addAction(self.vcsTagAct)
        tagsMenu.addAction(self.gitTagListAct)
        tagsMenu.addAction(self.gitDescribeTagAct)
        self.subMenus.append(tagsMenu)

        branchesMenu = QMenu(self.tr("Branches"), menu)
        branchesMenu.setIcon(EricPixmapCache.getIcon("vcsBranch"))
        branchesMenu.setTearOffEnabled(True)
        branchesMenu.addAction(self.gitBranchAct)
        branchesMenu.addSeparator()
        branchesMenu.addAction(self.gitBranchListAct)
        branchesMenu.addAction(self.gitMergedBranchListAct)
        branchesMenu.addAction(self.gitNotMergedBranchListAct)
        branchesMenu.addAction(self.gitShowBranchAct)
        branchesMenu.addSeparator()
        branchesMenu.addAction(self.gitDeleteRemoteBranchAct)
        self.subMenus.append(branchesMenu)

        changesMenu = QMenu(self.tr("Manage Changes"), menu)
        changesMenu.setTearOffEnabled(True)
        changesMenu.addAction(self.gitUnstageAct)
        changesMenu.addAction(self.vcsRevertAct)
        changesMenu.addAction(self.vcsMergeAct)
        changesMenu.addAction(self.gitCommitMergeAct)
        changesMenu.addAction(self.gitCancelMergeAct)

        remotesMenu = QMenu(self.tr("Remote Repositories"), menu)
        remotesMenu.setTearOffEnabled(True)
        remotesMenu.addAction(self.gitRemotesShowAct)
        remotesMenu.addAction(self.gitRemoteShowAct)
        remotesMenu.addSeparator()
        remotesMenu.addAction(self.gitRemoteAddAct)
        remotesMenu.addAction(self.gitRemoteRenameAct)
        remotesMenu.addAction(self.gitRemoteChangeUrlAct)
        remotesMenu.addAction(self.gitRemoteCredentialsAct)
        remotesMenu.addAction(self.gitRemoteRemoveAct)
        remotesMenu.addAction(self.gitRemotePruneAct)

        cherrypickMenu = QMenu(self.tr("Cherry-pick"), menu)
        cherrypickMenu.setIcon(EricPixmapCache.getIcon("vcsGraft"))
        cherrypickMenu.setTearOffEnabled(True)
        cherrypickMenu.addAction(self.gitCherryPickAct)
        cherrypickMenu.addAction(self.gitCherryPickContinueAct)
        cherrypickMenu.addAction(self.gitCherryPickQuitAct)
        cherrypickMenu.addAction(self.gitCherryPickAbortAct)

        stashMenu = QMenu(self.tr("Stash"), menu)
        stashMenu.setTearOffEnabled(True)
        stashMenu.addAction(self.gitStashAct)
        stashMenu.addSeparator()
        stashMenu.addAction(self.gitStashBrowserAct)
        stashMenu.addAction(self.gitStashShowAct)
        stashMenu.addSeparator()
        stashMenu.addAction(self.gitStashApplyAct)
        stashMenu.addAction(self.gitStashPopAct)
        stashMenu.addSeparator()
        stashMenu.addAction(self.gitStashBranchAct)
        stashMenu.addSeparator()
        stashMenu.addAction(self.gitStashDropAct)
        stashMenu.addAction(self.gitStashClearAct)

        submodulesMenu = QMenu(self.tr("Submodules"), menu)
        submodulesMenu.setTearOffEnabled(True)
        submodulesMenu.addAction(self.gitSubmoduleAddAct)
        submodulesMenu.addSeparator()
        submodulesMenu.addAction(self.gitSubmodulesInitAct)
        submodulesMenu.addAction(self.gitSubmodulesUpdateInitAct)
        submodulesMenu.addAction(self.gitSubmodulesDeinitAct)
        submodulesMenu.addSeparator()
        submodulesMenu.addAction(self.gitSubmodulesUpdateAct)
        submodulesMenu.addAction(self.gitSubmodulesUpdateRemoteAct)
        submodulesMenu.addAction(self.gitSubmodulesUpdateOptionsAct)
        submodulesMenu.addSeparator()
        submodulesMenu.addAction(self.gitSubmodulesSyncAct)
        submodulesMenu.addSeparator()
        submodulesMenu.addAction(self.gitSubmodulesListAct)
        submodulesMenu.addSeparator()
        submodulesMenu.addAction(self.gitSubmodulesStatusAct)
        submodulesMenu.addAction(self.gitSubmodulesSummaryAct)

        act = menu.addAction(
            EricPixmapCache.getIcon(
                os.path.join("VcsPlugins", "vcsGit", "icons", "git.svg")
            ),
            self.vcs.vcsName(),
            self._vcsInfoDisplay,
        )
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        menu.addSeparator()

        menu.addAction(self.gitFetchAct)
        menu.addAction(self.gitPullAct)
        menu.addSeparator()
        menu.addAction(self.vcsCommitAct)
        menu.addAction(self.gitPushAct)
        menu.addSeparator()
        menu.addMenu(changesMenu)
        menu.addMenu(stashMenu)
        menu.addSeparator()
        menu.addMenu(cherrypickMenu)
        menu.addSeparator()
        menu.addMenu(bundleMenu)
        menu.addMenu(patchMenu)
        menu.addSeparator()
        menu.addMenu(remotesMenu)
        menu.addMenu(submodulesMenu)
        menu.addSeparator()
        menu.addMenu(tagsMenu)
        menu.addMenu(branchesMenu)
        menu.addSeparator()
        menu.addAction(self.gitLogBrowserAct)
        menu.addSeparator()
        menu.addAction(self.vcsStatusAct)
        menu.addSeparator()
        menu.addAction(self.vcsDiffAct)
        menu.addAction(self.gitExtDiffAct)
        menu.addSeparator()
        menu.addAction(self.vcsSwitchAct)
        menu.addSeparator()
        menu.addMenu(bisectMenu)
        menu.addSeparator()
        menu.addAction(self.vcsCleanupAct)
        menu.addSeparator()
        menu.addAction(self.vcsCommandAct)
        menu.addSeparator()
        menu.addAction(self.gitWorktreeManagementAct)
        menu.addMenu(adminMenu)
        menu.addSeparator()
        menu.addAction(self.gitEditUserConfigAct)
        menu.addAction(self.gitConfigAct)
        menu.addSeparator()
        menu.addAction(self.vcsNewAct)
        menu.addAction(self.vcsExportAct)

    def initToolbar(self, ui, toolbarManager):
        """
        Public slot to initialize the VCS toolbar.

        @param ui reference to the main window
        @type UserInterface
        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        """
        self.__toolbar = QToolBar(self.tr("Git"), ui)
        self.__toolbar.setObjectName("GitToolbar")
        self.__toolbar.setToolTip(self.tr("Git"))

        self.__toolbar.addAction(self.gitLogBrowserAct)
        self.__toolbar.addAction(self.vcsStatusAct)
        self.__toolbar.addSeparator()
        self.__toolbar.addAction(self.vcsDiffAct)
        self.__toolbar.addSeparator()
        self.__toolbar.addAction(self.vcsNewAct)
        self.__toolbar.addAction(self.vcsExportAct)
        self.__toolbar.addSeparator()

        title = self.__toolbar.windowTitle()
        toolbarManager.addToolBar(self.__toolbar, title)
        toolbarManager.addAction(self.gitFetchAct, title)
        toolbarManager.addAction(self.gitPullAct, title)
        toolbarManager.addAction(self.vcsCommitAct, title)
        toolbarManager.addAction(self.gitPushAct, title)
        toolbarManager.addAction(self.gitReflogBrowserAct, title)
        toolbarManager.addAction(self.gitExtDiffAct, title)
        toolbarManager.addAction(self.vcsSwitchAct, title)
        toolbarManager.addAction(self.vcsTagAct, title)
        toolbarManager.addAction(self.gitBranchAct, title)
        toolbarManager.addAction(self.vcsRevertAct, title)
        toolbarManager.addAction(self.gitUnstageAct, title)
        toolbarManager.addAction(self.vcsMergeAct, title)
        toolbarManager.addAction(self.gitCherryPickAct, title)
        toolbarManager.addAction(self.gitBisectLogBrowserAct, title)

        self.__toolbar.setEnabled(False)
        self.__toolbar.setVisible(False)

        ui.registerToolbar("git", self.__toolbar.windowTitle(), self.__toolbar, "vcs")
        ui.addToolBar(self.__toolbar)

    def removeToolbar(self, ui, toolbarManager):
        """
        Public method to remove a toolbar created by initToolbar().

        @param ui reference to the main window
        @type UserInterface
        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        """
        ui.removeToolBar(self.__toolbar)
        ui.unregisterToolbar("git")

        title = self.__toolbar.windowTitle()
        toolbarManager.removeCategoryActions(title)
        toolbarManager.removeToolBar(self.__toolbar)

        self.__toolbar.deleteLater()
        self.__toolbar = None

    def shutdown(self):
        """
        Public method to perform shutdown actions.
        """
        # close torn off sub menus
        for menu in self.subMenus:
            if menu.isTearOffMenuVisible():
                menu.hideTearOffMenu()

    def __gitTagList(self):
        """
        Private slot used to list the tags of the project.
        """
        self.vcs.gitListTagBranch(self.project.getProjectPath(), True)

    def __gitDescribeTag(self):
        """
        Private slot to show the most recent tag.
        """
        self.vcs.gitDescribe(self.project.getProjectPath(), [])

    def __gitBranchList(self):
        """
        Private slot used to list the branches of the project.
        """
        self.vcs.gitListTagBranch(self.project.getProjectPath(), False)

    def __gitMergedBranchList(self):
        """
        Private slot used to list the merged branches of the project.
        """
        self.vcs.gitListTagBranch(
            self.project.getProjectPath(), False, listAll=False, merged=True
        )

    def __gitNotMergedBranchList(self):
        """
        Private slot used to list the not merged branches of the project.
        """
        self.vcs.gitListTagBranch(
            self.project.getProjectPath(), False, listAll=False, merged=False
        )

    def __gitBranch(self):
        """
        Private slot used to perform branch operations for the project.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitBranch(self.project.getProjectPath())[1]
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Branch"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitDeleteBranch(self):
        """
        Private slot used to delete a branch from a remote repository.
        """
        self.vcs.gitDeleteRemoteBranch(self.project.getProjectPath())

    def __gitShowBranch(self):
        """
        Private slot used to show the current branch for the project.
        """
        self.vcs.gitShowBranch(self.project.getProjectPath())

    def __gitExtendedDiff(self):
        """
        Private slot used to perform a git diff with the selection of
        revisions.
        """
        self.vcs.gitExtendedDiff(self.project.getProjectPath())

    def __gitFetch(self):
        """
        Private slot used to fetch changes from a remote repository.
        """
        self.vcs.gitFetch(self.project.getProjectPath())

    def __gitPull(self):
        """
        Private slot used to pull changes from a remote repository.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitPull(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Pull"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitPush(self):
        """
        Private slot used to push changes to a remote repository.
        """
        self.vcs.gitPush(self.project.getProjectPath())

    def __gitRevert(self):
        """
        Private slot used to revert changes made to the local project.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.vcsRevert(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Revert Changes"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitUnstage(self):
        """
        Private slot used to unstage changes made to the local project.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitUnstage(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Unstage Changes"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitCancelMerge(self):
        """
        Private slot used to cancel an uncommitted or failed merge.
        """
        self.vcs.gitCancelMerge(self.project.getProjectPath())

    def __gitCommitMerge(self):
        """
        Private slot used to commit the ongoing merge.
        """
        self.vcs.gitCommitMerge(self.project.getProjectPath())

    def __gitShowRemotes(self):
        """
        Private slot used to show the available remote repositories.
        """
        self.vcs.gitShowRemotes(self.project.getProjectPath())

    def __gitShowRemote(self):
        """
        Private slot used to show information about a remote repository.
        """
        remotes = self.vcs.gitGetRemotesList(self.project.getProjectPath())
        remote, ok = QInputDialog.getItem(
            None,
            self.tr("Show Remote Info"),
            self.tr("Select a remote repository:"),
            remotes,
            0,
            False,
        )
        if ok:
            self.vcs.gitShowRemote(self.project.getProjectPath(), remote)

    def __gitAddRemote(self):
        """
        Private slot to add a remote repository.
        """
        self.vcs.gitAddRemote(self.project.getProjectPath())

    def __gitRemoveRemote(self):
        """
        Private slot to remove a remote repository.
        """
        remotes = self.vcs.gitGetRemotesList(self.project.getProjectPath())
        remote, ok = QInputDialog.getItem(
            None,
            self.tr("Remove"),
            self.tr("Select a remote repository:"),
            remotes,
            0,
            False,
        )
        if ok:
            self.vcs.gitRemoveRemote(self.project.getProjectPath(), remote)

    def __gitPruneRemote(self):
        """
        Private slot to prune stale tracking branches of a remote repository.
        """
        remotes = self.vcs.gitGetRemotesList(self.project.getProjectPath())
        remote, ok = QInputDialog.getItem(
            None,
            self.tr("Prune"),
            self.tr("Select a remote repository:"),
            remotes,
            0,
            False,
        )
        if ok:
            self.vcs.gitPruneRemote(self.project.getProjectPath(), remote)

    def __gitRenameRemote(self):
        """
        Private slot to rename a remote repository.
        """
        remotes = self.vcs.gitGetRemotesList(self.project.getProjectPath())
        remote, ok = QInputDialog.getItem(
            None,
            self.tr("Rename"),
            self.tr("Select a remote repository:"),
            remotes,
            0,
            False,
        )
        if ok:
            self.vcs.gitRenameRemote(self.project.getProjectPath(), remote)

    def __gitChangeRemoteUrl(self):
        """
        Private slot to change the URL of a remote repository.
        """
        remotes = self.vcs.gitGetRemotesList(self.project.getProjectPath())
        remote, ok = QInputDialog.getItem(
            None,
            self.tr("Rename"),
            self.tr("Select a remote repository:"),
            remotes,
            0,
            False,
        )
        if ok:
            self.vcs.gitChangeRemoteUrl(self.project.getProjectPath(), remote)

    def __gitRemoteCredentials(self):
        """
        Private slot to change or set the user credentials for a remote
        repository.
        """
        remotes = self.vcs.gitGetRemotesList(self.project.getProjectPath())
        remote, ok = QInputDialog.getItem(
            None,
            self.tr("Rename"),
            self.tr("Select a remote repository:"),
            remotes,
            0,
            False,
        )
        if ok:
            self.vcs.gitChangeRemoteCredentials(self.project.getProjectPath(), remote)

    def __gitCherryPick(self):
        """
        Private slot used to copy commits into the current branch.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitCherryPick(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                None,
                self.tr("Copy Commits"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitCherryPickContinue(self):
        """
        Private slot used to continue the last copying session after conflicts
        were resolved.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitCherryPickContinue(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                None,
                self.tr("Copy Commits (Continue)"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitCherryPickQuit(self):
        """
        Private slot used to quit the current copying operation.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitCherryPickQuit(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                None,
                self.tr("Copy Commits (Quit)"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitCherryPickAbort(self):
        """
        Private slot used to cancel the last copying session and return to
        the previous state.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitCherryPickAbort(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                None,
                self.tr("Copy Commits (Cancel)"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitStashSave(self):
        """
        Private slot to stash all current changes.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitStashSave(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Save Stash"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitStashBrowser(self):
        """
        Private slot used to show the stash browser dialog.
        """
        self.vcs.gitStashBrowser(self.project.getProjectPath())

    def __gitStashShow(self):
        """
        Private slot to show the contents of the selected stash.
        """
        self.vcs.gitStashShowPatch(self.project.getProjectPath())

    def __gitStashApply(self):
        """
        Private slot to restore a stash and keep it.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitStashApply(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Restore Stash"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitStashPop(self):
        """
        Private slot to restore a stash and delete it.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitStashPop(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Restore Stash"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitStashBranch(self):
        """
        Private slot to create a new branch and restore a stash into it.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitStashBranch(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Create Branch"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitStashDrop(self):
        """
        Private slot to drop a stash.
        """
        self.vcs.gitStashDrop(self.project.getProjectPath())

    def __gitStashClear(self):
        """
        Private slot to clear all stashes.
        """
        self.vcs.gitStashClear(self.project.getProjectPath())

    def __gitConfigure(self):
        """
        Private method to open the configuration dialog.
        """
        ericApp().getObject("UserInterface").showPreferences("zzz_gitPage")

    def __gitEditUserConfig(self):
        """
        Private slot used to edit the user configuration file.
        """
        self.vcs.gitEditUserConfig()

    def __gitEditRepoConfig(self):
        """
        Private slot used to edit the repository configuration file.
        """
        self.vcs.gitEditConfig(self.project.getProjectPath())

    def __gitCreateIgnore(self):
        """
        Private slot used to create a .gitignore file for the project.
        """
        self.vcs.gitCreateIgnoreFile(self.project.getProjectPath(), autoAdd=True)

    def __gitShowConfig(self):
        """
        Private slot used to show the combined configuration.
        """
        self.vcs.gitShowConfig(self.project.getProjectPath())

    def __gitVerify(self):
        """
        Private slot used to verify the connectivity and validity of objects
        of the database.
        """
        self.vcs.gitVerify(self.project.getProjectPath())

    def __gitHouseKeeping(self):
        """
        Private slot used to cleanup and optimize the local repository.
        """
        self.vcs.gitHouseKeeping(self.project.getProjectPath())

    def __gitStatistics(self):
        """
        Private slot used to show some statistics of the local repository.
        """
        self.vcs.gitStatistics(self.project.getProjectPath())

    def __gitCreateArchive(self):
        """
        Private slot used to create an archive from the local repository.
        """
        self.vcs.gitCreateArchive(self.project.getProjectPath())

    def __gitReflogBrowser(self):
        """
        Private slot to show the reflog of the current project.
        """
        self.vcs.gitReflogBrowser(self.project.getProjectPath())

    def __gitBundle(self):
        """
        Private slot used to create a bundle file.
        """
        self.vcs.gitBundle(self.project.getProjectPath())

    def __gitVerifyBundle(self):
        """
        Private slot used to verify a bundle file.
        """
        self.vcs.gitVerifyBundle(self.project.getProjectPath())

    def __gitBundleListHeads(self):
        """
        Private slot used to list the heads contained in a bundle file.
        """
        self.vcs.gitBundleListHeads(self.project.getProjectPath())

    def __gitBundleFetch(self):
        """
        Private slot to apply a head of a bundle file using the fetch method.
        """
        self.vcs.gitBundleFetch(self.project.getProjectPath())

    def __gitBundlePull(self):
        """
        Private slot to apply a head of a bundle file using the pull method.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitBundlePull(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Apply Bundle (pull)"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitBisectStart(self):
        """
        Private slot used to execute the bisect start command.
        """
        self.vcs.gitBisect(self.project.getProjectPath(), "start")

    def __gitBisectStartExtended(self):
        """
        Private slot used to execute the bisect start command with options.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitBisect(self.project.getProjectPath(), "start_extended")
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Bisect"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitBisectGood(self):
        """
        Private slot used to execute the bisect good command.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitBisect(self.project.getProjectPath(), "good")
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Bisect"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitBisectBad(self):
        """
        Private slot used to execute the bisect bad command.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitBisect(self.project.getProjectPath(), "bad")
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Bisect"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitBisectSkip(self):
        """
        Private slot used to execute the bisect skip command.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitBisect(self.project.getProjectPath(), "skip")
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Bisect"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitBisectReset(self):
        """
        Private slot used to execute the bisect reset command.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitBisect(self.project.getProjectPath(), "reset")
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Bisect"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitBisectLogBrowser(self):
        """
        Private slot used to show the bisect log browser window.
        """
        self.vcs.gitBisectLogBrowser(self.project.getProjectPath())

    def __gitBisectCreateReplay(self):
        """
        Private slot used to create a replay file for the current bisect
        session.
        """
        self.vcs.gitBisectCreateReplayFile(self.project.getProjectPath())

    def __gitBisectEditReplay(self):
        """
        Private slot used to edit a bisect replay file.
        """
        self.vcs.gitBisectEditReplayFile(self.project.getProjectPath())

    def __gitBisectReplay(self):
        """
        Private slot used to replay a bisect session.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        shouldReopen = (
            self.vcs.gitBisectReplay(self.project.getProjectPath())
            or pfile.stat().st_mtime != lastModified
        )
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Bisect"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitCheckPatches(self):
        """
        Private slot to check a list of patch files, if they would apply
        cleanly.
        """
        self.vcs.gitApplyCheckPatches(self.project.getProjectPath(), check=True)

    def __gitApplyPatches(self):
        """
        Private slot to apply a list of patch files.
        """
        pfile = pathlib.Path(self.project.getProjectFile())
        lastModified = pfile.stat().st_mtime
        self.vcs.gitApplyCheckPatches(self.project.getProjectPath())
        if pfile.stat().st_mtime != lastModified:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Apply patch files"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __gitShowPatchStatistics(self):
        """
        Private slot to show some patch statistics.
        """
        self.vcs.gitShowPatchesStatistics(self.project.getProjectPath())

    def __gitSubmoduleAdd(self):
        """
        Private slot to add a submodule to the current project.
        """
        self.vcs.gitSubmoduleAdd(self.project.getProjectPath())

    def __gitSubmodulesList(self):
        """
        Private slot to list the submodules defined for the current project.
        """
        self.vcs.gitSubmoduleList(self.project.getProjectPath())

    def __gitSubmodulesInit(self):
        """
        Private slot to initialize submodules of the project.
        """
        self.vcs.gitSubmoduleInit(self.project.getProjectPath())

    def __gitSubmodulesDeinit(self):
        """
        Private slot to unregister submodules of the project.
        """
        self.vcs.gitSubmoduleDeinit(self.project.getProjectPath())

    def __gitSubmodulesUpdate(self):
        """
        Private slot to update submodules of the project.
        """
        self.vcs.gitSubmoduleUpdate(self.project.getProjectPath())

    def __gitSubmodulesUpdateInit(self):
        """
        Private slot to initialize and update submodules of the project.
        """
        self.vcs.gitSubmoduleUpdate(self.project.getProjectPath(), initialize=True)

    def __gitSubmodulesUpdateRemote(self):
        """
        Private slot to fetch and update submodules of the project.
        """
        self.vcs.gitSubmoduleUpdate(self.project.getProjectPath(), remote=True)

    def __gitSubmodulesUpdateOptions(self):
        """
        Private slot to update submodules of the project with options.
        """
        self.vcs.gitSubmoduleUpdateWithOptions(self.project.getProjectPath())

    def __gitSubmodulesSync(self):
        """
        Private slot to synchronize URLs of submodules of the project.
        """
        self.vcs.gitSubmoduleSync(self.project.getProjectPath())

    def __gitSubmodulesStatus(self):
        """
        Private slot to show the status of submodules of the project.
        """
        self.vcs.gitSubmoduleStatus(self.project.getProjectPath())

    def __gitSubmodulesSummary(self):
        """
        Private slot to show summary information for submodules of the project.
        """
        self.vcs.gitSubmoduleSummary(self.project.getProjectPath())

    def __gitWorktreeManagement(self):
        """
        Private slot to show the worktree management dialog.
        """
        self.vcs.gitWorktreeManagement(self.project.getProjectPath())
