# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the VCS project helper for Mercurial.
"""

import os

from PyQt6.QtWidgets import QMenu, QToolBar

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.VCS.ProjectHelper import VcsProjectHelper


class HgProjectHelper(VcsProjectHelper):
    """
    Class implementing the VCS project helper for Mercurial.
    """

    def __init__(self, vcsObject, projectObject, parent=None, name=None):
        """
        Constructor

        @param vcsObject reference to the vcs object
        @type Hg
        @param projectObject reference to the project object
        @type Project
        @param parent parent widget
        @type QWidget
        @param name name of this object
        @type str
        """
        from .CloseheadExtension.ProjectHelper import CloseheadProjectHelper
        from .FastexportExtension.ProjectHelper import FastexportProjectHelper
        from .GpgExtension.ProjectHelper import GpgProjectHelper
        from .HisteditExtension.ProjectHelper import HisteditProjectHelper
        from .LargefilesExtension.ProjectHelper import LargefilesProjectHelper
        from .PurgeBuiltin.ProjectHelper import PurgeProjectHelper
        from .QueuesExtension.ProjectHelper import QueuesProjectHelper
        from .RebaseExtension.ProjectHelper import RebaseProjectHelper
        from .ShelveBuiltin.ProjectHelper import ShelveProjectHelper
        from .UncommitExtension.ProjectHelper import UncommitProjectHelper

        super().__init__(vcsObject, projectObject, parent, name)

        # instantiate interfaces for additional built-in functions
        self.__builtins = {
            "purge": PurgeProjectHelper(),
            "shelve": ShelveProjectHelper(),
        }
        self.__builtinMenuTitles = {
            self.__builtins[b].menuTitle(): b for b in self.__builtins
        }

        # instantiate the extensions
        self.__extensions = {
            "closehead": CloseheadProjectHelper(),
            "fastexport": FastexportProjectHelper(),
            "gpg": GpgProjectHelper(),
            "histedit": HisteditProjectHelper(),
            "largefiles": LargefilesProjectHelper(),
            "mq": QueuesProjectHelper(),
            "rebase": RebaseProjectHelper(),
            "uncommit": UncommitProjectHelper(),
        }
        self.__extensionMenuTitles = {
            self.__extensions[e].menuTitle(): e for e in self.__extensions
        }

        self.__toolbarManager = None

    def setObjects(self, vcsObject, projectObject):
        """
        Public method to set references to the vcs and project objects.

        @param vcsObject reference to the vcs object
        @type Hg
        @param projectObject reference to the project object
        @type Project
        """
        self.vcs = vcsObject
        self.project = projectObject

        for builtin in self.__builtins.values():
            builtin.setObjects(vcsObject, projectObject)

        for extension in self.__extensions.values():
            extension.setObjects(vcsObject, projectObject)

        self.vcs.iniFileChanged.connect(self.__checkActions)

        # add Mercurial version dependent actions here
        title = self.__toolbar.windowTitle()
        if self.vcs.version >= (5, 7):
            self.actions.append(self.hgBookmarkPushAllAct)
            self.__toolbarManager.addAction(self.hgBookmarkPushAllAct, title)

        if self.vcs.version < (4, 7, 0):
            self.hgGraftStopAct.setEnabled(False)
            self.hgGraftAbortAct.setEnabled(False)

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
        for extension in self.__extensions.values():
            actions.extend(extension.getActions())
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
            "mercurial_new",
        )
        self.vcsNewAct.setStatusTip(
            self.tr("Create (clone) a new project from a Mercurial repository")
        )
        self.vcsNewAct.setWhatsThis(
            self.tr(
                """<b>New from repository</b>"""
                """<p>This creates (clones) a new local project from """
                """a Mercurial repository.</p>"""
            )
        )
        self.vcsNewAct.triggered.connect(self._vcsCheckout)
        self.actions.append(self.vcsNewAct)

        self.hgIncomingAct = EricAction(
            self.tr("Show incoming log"),
            EricPixmapCache.getIcon("vcsUpdate"),
            self.tr("Show incoming log"),
            0,
            0,
            self,
            "mercurial_incoming",
        )
        self.hgIncomingAct.setStatusTip(self.tr("Show the log of incoming changes"))
        self.hgIncomingAct.setWhatsThis(
            self.tr(
                """<b>Show incoming log</b>"""
                """<p>This shows the log of changes coming into the"""
                """ repository.</p>"""
            )
        )
        self.hgIncomingAct.triggered.connect(self.__hgIncoming)
        self.actions.append(self.hgIncomingAct)

        self.hgPullAct = EricAction(
            self.tr("Pull changes"),
            EricPixmapCache.getIcon("vcsUpdate"),
            self.tr("Pull changes"),
            0,
            0,
            self,
            "mercurial_pull",
        )
        self.hgPullAct.setStatusTip(self.tr("Pull changes from a remote repository"))
        self.hgPullAct.setWhatsThis(
            self.tr(
                """<b>Pull changes</b>"""
                """<p>This pulls changes from a remote repository into the """
                """local repository.</p>"""
            )
        )
        self.hgPullAct.triggered.connect(self.__hgPull)
        self.actions.append(self.hgPullAct)

        self.vcsUpdateAct = EricAction(
            self.tr("Update from repository"),
            EricPixmapCache.getIcon("vcsUpdate"),
            self.tr("&Update from repository"),
            0,
            0,
            self,
            "mercurial_update",
        )
        self.vcsUpdateAct.setStatusTip(
            self.tr("Update the local project from the Mercurial repository")
        )
        self.vcsUpdateAct.setWhatsThis(
            self.tr(
                """<b>Update from repository</b>"""
                """<p>This updates the local project from the Mercurial"""
                """ repository.</p>"""
            )
        )
        self.vcsUpdateAct.triggered.connect(self._vcsUpdate)
        self.actions.append(self.vcsUpdateAct)

        self.vcsCommitAct = EricAction(
            self.tr("Commit changes to repository"),
            EricPixmapCache.getIcon("vcsCommit"),
            self.tr("&Commit changes to repository..."),
            0,
            0,
            self,
            "mercurial_commit",
        )
        self.vcsCommitAct.setStatusTip(
            self.tr("Commit changes to the local project to the Mercurial repository")
        )
        self.vcsCommitAct.setWhatsThis(
            self.tr(
                """<b>Commit changes to repository</b>"""
                """<p>This commits changes to the local project to the """
                """Mercurial repository.</p>"""
            )
        )
        self.vcsCommitAct.triggered.connect(self._vcsCommit)
        self.actions.append(self.vcsCommitAct)

        self.hgOutgoingAct = EricAction(
            self.tr("Show outgoing log"),
            EricPixmapCache.getIcon("vcsCommit"),
            self.tr("Show outgoing log"),
            0,
            0,
            self,
            "mercurial_outgoing",
        )
        self.hgOutgoingAct.setStatusTip(self.tr("Show the log of outgoing changes"))
        self.hgOutgoingAct.setWhatsThis(
            self.tr(
                """<b>Show outgoing log</b>"""
                """<p>This shows the log of changes outgoing out of the"""
                """ repository.</p>"""
            )
        )
        self.hgOutgoingAct.triggered.connect(self.__hgOutgoing)
        self.actions.append(self.hgOutgoingAct)

        self.hgPushAct = EricAction(
            self.tr("Push changes"),
            EricPixmapCache.getIcon("vcsCommit"),
            self.tr("Push changes"),
            0,
            0,
            self,
            "mercurial_push",
        )
        self.hgPushAct.setStatusTip(self.tr("Push changes to a remote repository"))
        self.hgPushAct.setWhatsThis(
            self.tr(
                """<b>Push changes</b>"""
                """<p>This pushes changes from the local repository to a """
                """remote repository.</p>"""
            )
        )
        self.hgPushAct.triggered.connect(self.__hgPush)
        self.actions.append(self.hgPushAct)

        self.hgPushForcedAct = EricAction(
            self.tr("Push changes (force)"),
            EricPixmapCache.getIcon("vcsCommit"),
            self.tr("Push changes (force)"),
            0,
            0,
            self,
            "mercurial_push_forced",
        )
        self.hgPushForcedAct.setStatusTip(
            self.tr("Push changes to a remote repository with force option")
        )
        self.hgPushForcedAct.setWhatsThis(
            self.tr(
                """<b>Push changes (force)</b>"""
                """<p>This pushes changes from the local repository to a """
                """remote repository using the 'force' option.</p>"""
            )
        )
        self.hgPushForcedAct.triggered.connect(self.__hgPushForced)
        self.actions.append(self.hgPushForcedAct)

        self.vcsExportAct = EricAction(
            self.tr("Export from repository"),
            EricPixmapCache.getIcon("vcsExport"),
            self.tr("&Export from repository..."),
            0,
            0,
            self,
            "mercurial_export_repo",
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

        self.hgLogBrowserAct = EricAction(
            self.tr("Show log browser"),
            EricPixmapCache.getIcon("vcsLog"),
            self.tr("Show log browser"),
            0,
            0,
            self,
            "mercurial_log_browser",
        )
        self.hgLogBrowserAct.setStatusTip(
            self.tr("Show a dialog to browse the log of the local project")
        )
        self.hgLogBrowserAct.setWhatsThis(
            self.tr(
                """<b>Show log browser</b>"""
                """<p>This shows a dialog to browse the log of the local"""
                """ project. A limited number of entries is shown first."""
                """ More can be retrieved later on.</p>"""
            )
        )
        self.hgLogBrowserAct.triggered.connect(self._vcsLogBrowser)
        self.actions.append(self.hgLogBrowserAct)

        self.vcsDiffAct = EricAction(
            self.tr("Show differences"),
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show &difference"),
            0,
            0,
            self,
            "mercurial_diff",
        )
        self.vcsDiffAct.setStatusTip(
            self.tr("Show the difference of the local project to the repository")
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

        self.hgExtDiffAct = EricAction(
            self.tr("Show differences (extended)"),
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences (extended)"),
            0,
            0,
            self,
            "mercurial_extendeddiff",
        )
        self.hgExtDiffAct.setStatusTip(
            self.tr("Show the difference of revisions of the project to the repository")
        )
        self.hgExtDiffAct.setWhatsThis(
            self.tr(
                """<b>Show differences (extended)</b>"""
                """<p>This shows differences of selectable revisions of the"""
                """ project.</p>"""
            )
        )
        self.hgExtDiffAct.triggered.connect(self.__hgExtendedDiff)
        self.actions.append(self.hgExtDiffAct)

        self.vcsStatusAct = EricAction(
            self.tr("Show status"),
            EricPixmapCache.getIcon("vcsStatus"),
            self.tr("Show &status..."),
            0,
            0,
            self,
            "mercurial_status",
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

        self.hgSummaryAct = EricAction(
            self.tr("Show Summary"),
            EricPixmapCache.getIcon("vcsSummary"),
            self.tr("Show summary..."),
            0,
            0,
            self,
            "mercurial_summary",
        )
        self.hgSummaryAct.setStatusTip(
            self.tr("Show summary information of the working directory status")
        )
        self.hgSummaryAct.setWhatsThis(
            self.tr(
                """<b>Show summary</b>"""
                """<p>This shows some summary information of the working"""
                """ directory status.</p>"""
            )
        )
        self.hgSummaryAct.triggered.connect(self.__hgSummary)
        self.actions.append(self.hgSummaryAct)

        self.hgHeadsAct = EricAction(
            self.tr("Show heads"), self.tr("Show heads"), 0, 0, self, "mercurial_heads"
        )
        self.hgHeadsAct.setStatusTip(self.tr("Show the heads of the repository"))
        self.hgHeadsAct.setWhatsThis(
            self.tr(
                """<b>Show heads</b>"""
                """<p>This shows the heads of the repository.</p>"""
            )
        )
        self.hgHeadsAct.triggered.connect(self.__hgHeads)
        self.actions.append(self.hgHeadsAct)

        self.hgParentsAct = EricAction(
            self.tr("Show parents"),
            self.tr("Show parents"),
            0,
            0,
            self,
            "mercurial_parents",
        )
        self.hgParentsAct.setStatusTip(self.tr("Show the parents of the repository"))
        self.hgParentsAct.setWhatsThis(
            self.tr(
                """<b>Show parents</b>"""
                """<p>This shows the parents of the repository.</p>"""
            )
        )
        self.hgParentsAct.triggered.connect(self.__hgParents)
        self.actions.append(self.hgParentsAct)

        self.hgTipAct = EricAction(
            self.tr("Show tip"), self.tr("Show tip"), 0, 0, self, "mercurial_tip"
        )
        self.hgTipAct.setStatusTip(self.tr("Show the tip of the repository"))
        self.hgTipAct.setWhatsThis(
            self.tr("""<b>Show tip</b><p>This shows the tip of the repository.</p>""")
        )
        self.hgTipAct.triggered.connect(self.__hgTip)
        self.actions.append(self.hgTipAct)

        self.vcsRevertAct = EricAction(
            self.tr("Revert changes"),
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Re&vert changes"),
            0,
            0,
            self,
            "mercurial_revert",
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
        self.vcsRevertAct.triggered.connect(self.__hgRevert)
        self.actions.append(self.vcsRevertAct)

        self.vcsMergeAct = EricAction(
            self.tr("Merge"),
            EricPixmapCache.getIcon("vcsMerge"),
            self.tr("Mer&ge changes..."),
            0,
            0,
            self,
            "mercurial_merge",
        )
        self.vcsMergeAct.setStatusTip(
            self.tr("Merge changes of a revision into the local project")
        )
        self.vcsMergeAct.setWhatsThis(
            self.tr(
                """<b>Merge</b>"""
                """<p>This merges changes of a revision into the local"""
                """ project.</p>"""
            )
        )
        self.vcsMergeAct.triggered.connect(self._vcsMerge)
        self.actions.append(self.vcsMergeAct)

        self.hgCommitMergeAct = EricAction(
            self.tr("Commit Merge"),
            self.tr("Commit Merge"),
            0,
            0,
            self,
            "mercurial_commit_merge",
        )
        self.hgCommitMergeAct.setStatusTip(self.tr("Commit all the merged changes."))
        self.hgCommitMergeAct.setWhatsThis(
            self.tr(
                """<b>Commit a merge</b>"""
                """<p>This commits a merge working directory</p>"""
            )
        )
        self.hgCommitMergeAct.triggered.connect(self.__hgCommitMerge)
        self.actions.append(self.hgCommitMergeAct)

        self.hgAbortMergeAct = EricAction(
            self.tr("Abort Merge"),
            self.tr("Abort Merge"),
            0,
            0,
            self,
            "mercurial_cancel_merge",
        )
        self.hgAbortMergeAct.setStatusTip(
            self.tr("Abort an uncommitted merge and lose all changes")
        )
        self.hgAbortMergeAct.setWhatsThis(
            self.tr(
                """<b>Abort uncommitted merge</b>"""
                """<p>This aborts an uncommitted merge causing all changes"""
                """ to be lost.</p>"""
            )
        )
        self.hgAbortMergeAct.triggered.connect(self.__hgAbortMerge)
        self.actions.append(self.hgAbortMergeAct)

        self.hgReMergeAct = EricAction(
            self.tr("Re-Merge"),
            EricPixmapCache.getIcon("vcsMerge"),
            self.tr("Re-Merge"),
            0,
            0,
            self,
            "mercurial_remerge",
        )
        self.hgReMergeAct.setStatusTip(
            self.tr("Re-Merge all conflicting, unresolved files of the project")
        )
        self.hgReMergeAct.setWhatsThis(
            self.tr(
                """<b>Re-Merge</b>"""
                """<p>This re-merges all conflicting, unresolved files of the"""
                """ project discarding any previous merge attempt.</p>"""
            )
        )
        self.hgReMergeAct.triggered.connect(self.__hgReMerge)
        self.actions.append(self.hgReMergeAct)

        self.hgShowConflictsAct = EricAction(
            self.tr("Show conflicts"),
            self.tr("Show conflicts..."),
            0,
            0,
            self,
            "mercurial_show_conflicts",
        )
        self.hgShowConflictsAct.setStatusTip(
            self.tr("Show a dialog listing all files with conflicts")
        )
        self.hgShowConflictsAct.setWhatsThis(
            self.tr(
                """<b>Show conflicts</b>"""
                """<p>This shows a dialog listing all files which had or still"""
                """ have conflicts.</p>"""
            )
        )
        self.hgShowConflictsAct.triggered.connect(self.__hgShowConflicts)
        self.actions.append(self.hgShowConflictsAct)

        self.vcsResolveAct = EricAction(
            self.tr("Conflicts resolved"),
            self.tr("Con&flicts resolved"),
            0,
            0,
            self,
            "mercurial_resolve",
        )
        self.vcsResolveAct.setStatusTip(
            self.tr("Mark all conflicts of the local project as resolved")
        )
        self.vcsResolveAct.setWhatsThis(
            self.tr(
                """<b>Conflicts resolved</b>"""
                """<p>This marks all conflicts of the local project as"""
                """ resolved.</p>"""
            )
        )
        self.vcsResolveAct.triggered.connect(self.__hgResolved)
        self.actions.append(self.vcsResolveAct)

        self.hgUnresolveAct = EricAction(
            self.tr("Conflicts unresolved"),
            self.tr("Conflicts unresolved"),
            0,
            0,
            self,
            "mercurial_unresolve",
        )
        self.hgUnresolveAct.setStatusTip(
            self.tr("Mark all conflicts of the local project as unresolved")
        )
        self.hgUnresolveAct.setWhatsThis(
            self.tr(
                """<b>Conflicts unresolved</b>"""
                """<p>This marks all conflicts of the local project as"""
                """ unresolved.</p>"""
            )
        )
        self.hgUnresolveAct.triggered.connect(self.__hgUnresolved)
        self.actions.append(self.hgUnresolveAct)

        self.vcsTagAct = EricAction(
            self.tr("Tag in repository"),
            EricPixmapCache.getIcon("vcsTag"),
            self.tr("&Tag in repository..."),
            0,
            0,
            self,
            "mercurial_tag",
        )
        self.vcsTagAct.setStatusTip(self.tr("Tag the local project in the repository"))
        self.vcsTagAct.setWhatsThis(
            self.tr(
                """<b>Tag in repository</b>"""
                """<p>This tags the local project in the repository.</p>"""
            )
        )
        self.vcsTagAct.triggered.connect(self._vcsTag)
        self.actions.append(self.vcsTagAct)

        self.hgTagListAct = EricAction(
            self.tr("List tags"),
            self.tr("List tags..."),
            0,
            0,
            self,
            "mercurial_list_tags",
        )
        self.hgTagListAct.setStatusTip(self.tr("List tags of the project"))
        self.hgTagListAct.setWhatsThis(
            self.tr("""<b>List tags</b><p>This lists the tags of the project.</p>""")
        )
        self.hgTagListAct.triggered.connect(self.__hgTagList)
        self.actions.append(self.hgTagListAct)

        self.hgBranchListAct = EricAction(
            self.tr("List branches"),
            self.tr("List branches..."),
            0,
            0,
            self,
            "mercurial_list_branches",
        )
        self.hgBranchListAct.setStatusTip(self.tr("List branches of the project"))
        self.hgBranchListAct.setWhatsThis(
            self.tr(
                """<b>List branches</b>"""
                """<p>This lists the branches of the project.</p>"""
            )
        )
        self.hgBranchListAct.triggered.connect(self.__hgBranchList)
        self.actions.append(self.hgBranchListAct)

        self.hgBranchAct = EricAction(
            self.tr("Create branch"),
            EricPixmapCache.getIcon("vcsBranch"),
            self.tr("Create &branch..."),
            0,
            0,
            self,
            "mercurial_branch",
        )
        self.hgBranchAct.setStatusTip(
            self.tr("Create a new branch for the local project in the repository")
        )
        self.hgBranchAct.setWhatsThis(
            self.tr(
                """<b>Create branch</b>"""
                """<p>This creates a new branch for the local project """
                """in the repository.</p>"""
            )
        )
        self.hgBranchAct.triggered.connect(self.__hgBranch)
        self.actions.append(self.hgBranchAct)

        self.hgPushBranchAct = EricAction(
            self.tr("Push new branch"),
            EricPixmapCache.getIcon("vcsCommit"),
            self.tr("Push new branch"),
            0,
            0,
            self,
            "mercurial_push_branch",
        )
        self.hgPushBranchAct.setStatusTip(
            self.tr(
                "Push the current branch of the local project as a new named branch"
            )
        )
        self.hgPushBranchAct.setWhatsThis(
            self.tr(
                """<b>Push new branch</b>"""
                """<p>This pushes the current branch of the local project"""
                """ as a new named branch.</p>"""
            )
        )
        self.hgPushBranchAct.triggered.connect(self.__hgPushNewBranch)
        self.actions.append(self.hgPushBranchAct)

        self.hgCloseBranchAct = EricAction(
            self.tr("Close branch"),
            EricPixmapCache.getIcon("closehead"),
            self.tr("Close branch"),
            0,
            0,
            self,
            "mercurial_close_branch",
        )
        self.hgCloseBranchAct.setStatusTip(
            self.tr("Close the current branch of the local project")
        )
        self.hgCloseBranchAct.setWhatsThis(
            self.tr(
                """<b>Close branch</b>"""
                """<p>This closes the current branch of the local project.</p>"""
            )
        )
        self.hgCloseBranchAct.triggered.connect(self.__hgCloseBranch)
        self.actions.append(self.hgCloseBranchAct)

        self.hgShowBranchAct = EricAction(
            self.tr("Show current branch"),
            self.tr("Show current branch"),
            0,
            0,
            self,
            "mercurial_show_branch",
        )
        self.hgShowBranchAct.setStatusTip(
            self.tr("Show the current branch of the project")
        )
        self.hgShowBranchAct.setWhatsThis(
            self.tr(
                """<b>Show current branch</b>"""
                """<p>This shows the current branch of the project.</p>"""
            )
        )
        self.hgShowBranchAct.triggered.connect(self.__hgShowBranch)
        self.actions.append(self.hgShowBranchAct)

        self.vcsSwitchAct = EricAction(
            self.tr("Switch"),
            EricPixmapCache.getIcon("vcsSwitch"),
            self.tr("S&witch..."),
            0,
            0,
            self,
            "mercurial_switch",
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

        self.vcsCleanupAct = EricAction(
            self.tr("Cleanup"), self.tr("Cleanu&p"), 0, 0, self, "mercurial_cleanup"
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
            "mercurial_command",
        )
        self.vcsCommandAct.setStatusTip(
            self.tr("Execute an arbitrary Mercurial command")
        )
        self.vcsCommandAct.setWhatsThis(
            self.tr(
                """<b>Execute command</b>"""
                """<p>This opens a dialog to enter an arbitrary Mercurial"""
                """ command.</p>"""
            )
        )
        self.vcsCommandAct.triggered.connect(self._vcsCommand)
        self.actions.append(self.vcsCommandAct)

        self.hgConfigAct = EricAction(
            self.tr("Configure"),
            self.tr("Configure..."),
            0,
            0,
            self,
            "mercurial_configure",
        )
        self.hgConfigAct.setStatusTip(
            self.tr("Show the configuration dialog with the Mercurial page selected")
        )
        self.hgConfigAct.setWhatsThis(
            self.tr(
                """<b>Configure</b>"""
                """<p>Show the configuration dialog with the Mercurial page"""
                """ selected.</p>"""
            )
        )
        self.hgConfigAct.triggered.connect(self.__hgConfigure)
        self.actions.append(self.hgConfigAct)

        self.hgEditUserConfigAct = EricAction(
            self.tr("Edit user configuration"),
            self.tr("Edit user configuration..."),
            0,
            0,
            self,
            "mercurial_user_configure",
        )
        self.hgEditUserConfigAct.setStatusTip(
            self.tr("Show an editor to edit the user configuration file")
        )
        self.hgEditUserConfigAct.setWhatsThis(
            self.tr(
                """<b>Edit user configuration</b>"""
                """<p>Show an editor to edit the user configuration file.</p>"""
            )
        )
        self.hgEditUserConfigAct.triggered.connect(self.__hgEditUserConfig)
        self.actions.append(self.hgEditUserConfigAct)

        self.hgRepoConfigAct = EricAction(
            self.tr("Edit repository configuration"),
            self.tr("Edit repository configuration..."),
            0,
            0,
            self,
            "mercurial_repo_configure",
        )
        self.hgRepoConfigAct.setStatusTip(
            self.tr("Show an editor to edit the repository configuration file")
        )
        self.hgRepoConfigAct.setWhatsThis(
            self.tr(
                """<b>Edit repository configuration</b>"""
                """<p>Show an editor to edit the repository configuration"""
                """ file.</p>"""
            )
        )
        self.hgRepoConfigAct.triggered.connect(self.__hgEditRepoConfig)
        self.actions.append(self.hgRepoConfigAct)

        self.hgShowConfigAct = EricAction(
            self.tr("Show combined configuration settings"),
            self.tr("Show combined configuration settings..."),
            0,
            0,
            self,
            "mercurial_show_config",
        )
        self.hgShowConfigAct.setStatusTip(
            self.tr(
                "Show the combined configuration settings from all configuration"
                " files"
            )
        )
        self.hgShowConfigAct.setWhatsThis(
            self.tr(
                """<b>Show combined configuration settings</b>"""
                """<p>This shows the combined configuration settings"""
                """ from all configuration files.</p>"""
            )
        )
        self.hgShowConfigAct.triggered.connect(self.__hgShowConfig)
        self.actions.append(self.hgShowConfigAct)

        self.hgShowPathsAct = EricAction(
            self.tr("Show paths"),
            self.tr("Show paths..."),
            0,
            0,
            self,
            "mercurial_show_paths",
        )
        self.hgShowPathsAct.setStatusTip(
            self.tr("Show the aliases for remote repositories")
        )
        self.hgShowPathsAct.setWhatsThis(
            self.tr(
                """<b>Show paths</b>"""
                """<p>This shows the aliases for remote repositories.</p>"""
            )
        )
        self.hgShowPathsAct.triggered.connect(self.__hgShowPaths)
        self.actions.append(self.hgShowPathsAct)

        self.hgVerifyAct = EricAction(
            self.tr("Verify repository"),
            self.tr("Verify repository..."),
            0,
            0,
            self,
            "mercurial_verify",
        )
        self.hgVerifyAct.setStatusTip(self.tr("Verify the integrity of the repository"))
        self.hgVerifyAct.setWhatsThis(
            self.tr(
                """<b>Verify repository</b>"""
                """<p>This verifies the integrity of the repository.</p>"""
            )
        )
        self.hgVerifyAct.triggered.connect(self.__hgVerify)
        self.actions.append(self.hgVerifyAct)

        self.hgRecoverAct = EricAction(
            self.tr("Recover"), self.tr("Recover..."), 0, 0, self, "mercurial_recover"
        )
        self.hgRecoverAct.setStatusTip(
            self.tr("Recover from an interrupted transaction")
        )
        self.hgRecoverAct.setWhatsThis(
            self.tr(
                """<b>Recover</b>"""
                """<p>This recovers from an interrupted transaction.</p>"""
            )
        )
        self.hgRecoverAct.triggered.connect(self.__hgRecover)
        self.actions.append(self.hgRecoverAct)

        self.hgIdentifyAct = EricAction(
            self.tr("Identify"),
            self.tr("Identify..."),
            0,
            0,
            self,
            "mercurial_identify",
        )
        self.hgIdentifyAct.setStatusTip(self.tr("Identify the project directory"))
        self.hgIdentifyAct.setWhatsThis(
            self.tr(
                """<b>Identify</b>"""
                """<p>This identifies the project directory.</p>"""
            )
        )
        self.hgIdentifyAct.triggered.connect(self.__hgIdentify)
        self.actions.append(self.hgIdentifyAct)

        self.hgCreateIgnoreAct = EricAction(
            self.tr("Create .hgignore"),
            self.tr("Create .hgignore"),
            0,
            0,
            self,
            "mercurial_create ignore",
        )
        self.hgCreateIgnoreAct.setStatusTip(
            self.tr("Create a .hgignore file with default values")
        )
        self.hgCreateIgnoreAct.setWhatsThis(
            self.tr(
                """<b>Create .hgignore</b>"""
                """<p>This creates a .hgignore file with default values.</p>"""
            )
        )
        self.hgCreateIgnoreAct.triggered.connect(self.__hgCreateIgnore)
        self.actions.append(self.hgCreateIgnoreAct)

        self.hgBundleAct = EricAction(
            self.tr("Create changegroup"),
            EricPixmapCache.getIcon("vcsCreateChangegroup"),
            self.tr("Create changegroup..."),
            0,
            0,
            self,
            "mercurial_bundle",
        )
        self.hgBundleAct.setStatusTip(
            self.tr("Create changegroup file collecting changesets")
        )
        self.hgBundleAct.setWhatsThis(
            self.tr(
                """<b>Create changegroup</b>"""
                """<p>This creates a changegroup file collecting selected"""
                """ changesets (hg bundle).</p>"""
            )
        )
        self.hgBundleAct.triggered.connect(self.__hgBundle)
        self.actions.append(self.hgBundleAct)

        self.hgPreviewBundleAct = EricAction(
            self.tr("Preview changegroup"),
            EricPixmapCache.getIcon("vcsPreviewChangegroup"),
            self.tr("Preview changegroup..."),
            0,
            0,
            self,
            "mercurial_preview_bundle",
        )
        self.hgPreviewBundleAct.setStatusTip(
            self.tr("Preview a changegroup file containing a collection of changesets")
        )
        self.hgPreviewBundleAct.setWhatsThis(
            self.tr(
                """<b>Preview changegroup</b>"""
                """<p>This previews a changegroup file containing a collection"""
                """ of changesets.</p>"""
            )
        )
        self.hgPreviewBundleAct.triggered.connect(self.__hgPreviewBundle)
        self.actions.append(self.hgPreviewBundleAct)

        self.hgUnbundleAct = EricAction(
            self.tr("Apply changegroups"),
            EricPixmapCache.getIcon("vcsApplyChangegroup"),
            self.tr("Apply changegroups..."),
            0,
            0,
            self,
            "mercurial_unbundle",
        )
        self.hgUnbundleAct.setStatusTip(
            self.tr("Apply one or several changegroup files")
        )
        self.hgUnbundleAct.setWhatsThis(
            self.tr(
                """<b>Apply changegroups</b>"""
                """<p>This applies one or several changegroup files generated by"""
                """ the 'Create changegroup' action (hg unbundle).</p>"""
            )
        )
        self.hgUnbundleAct.triggered.connect(self.__hgUnbundle)
        self.actions.append(self.hgUnbundleAct)

        self.hgBisectGoodAct = EricAction(
            self.tr('Mark as "good"'),
            self.tr('Mark as "good"...'),
            0,
            0,
            self,
            "mercurial_bisect_good",
        )
        self.hgBisectGoodAct.setStatusTip(
            self.tr("Mark a selectable changeset as good")
        )
        self.hgBisectGoodAct.setWhatsThis(
            self.tr(
                """<b>Mark as good</b>"""
                """<p>This marks a selectable changeset as good.</p>"""
            )
        )
        self.hgBisectGoodAct.triggered.connect(self.__hgBisectGood)
        self.actions.append(self.hgBisectGoodAct)

        self.hgBisectBadAct = EricAction(
            self.tr('Mark as "bad"'),
            self.tr('Mark as "bad"...'),
            0,
            0,
            self,
            "mercurial_bisect_bad",
        )
        self.hgBisectBadAct.setStatusTip(self.tr("Mark a selectable changeset as bad"))
        self.hgBisectBadAct.setWhatsThis(
            self.tr(
                """<b>Mark as bad</b>"""
                """<p>This marks a selectable changeset as bad.</p>"""
            )
        )
        self.hgBisectBadAct.triggered.connect(self.__hgBisectBad)
        self.actions.append(self.hgBisectBadAct)

        self.hgBisectSkipAct = EricAction(
            self.tr("Skip"), self.tr("Skip..."), 0, 0, self, "mercurial_bisect_skip"
        )
        self.hgBisectSkipAct.setStatusTip(self.tr("Skip a selectable changeset"))
        self.hgBisectSkipAct.setWhatsThis(
            self.tr("""<b>Skip</b><p>This skips a selectable changeset.</p>""")
        )
        self.hgBisectSkipAct.triggered.connect(self.__hgBisectSkip)
        self.actions.append(self.hgBisectSkipAct)

        self.hgBisectResetAct = EricAction(
            self.tr("Reset"), self.tr("Reset"), 0, 0, self, "mercurial_bisect_reset"
        )
        self.hgBisectResetAct.setStatusTip(self.tr("Reset the bisect search data"))
        self.hgBisectResetAct.setWhatsThis(
            self.tr("""<b>Reset</b><p>This resets the bisect search data.</p>""")
        )
        self.hgBisectResetAct.triggered.connect(self.__hgBisectReset)
        self.actions.append(self.hgBisectResetAct)

        self.hgBackoutAct = EricAction(
            self.tr("Back out changeset"),
            self.tr("Back out changeset"),
            0,
            0,
            self,
            "mercurial_backout",
        )
        self.hgBackoutAct.setStatusTip(
            self.tr("Back out changes of an earlier changeset")
        )
        self.hgBackoutAct.setWhatsThis(
            self.tr(
                """<b>Back out changeset</b>"""
                """<p>This backs out changes of an earlier changeset.</p>"""
            )
        )
        self.hgBackoutAct.triggered.connect(self.__hgBackout)
        self.actions.append(self.hgBackoutAct)

        self.hgRollbackAct = EricAction(
            self.tr("Rollback last transaction"),
            self.tr("Rollback last transaction"),
            0,
            0,
            self,
            "mercurial_rollback",
        )
        self.hgRollbackAct.setStatusTip(self.tr("Rollback the last transaction"))
        self.hgRollbackAct.setWhatsThis(
            self.tr(
                """<b>Rollback last transaction</b>"""
                """<p>This performs a rollback of the last transaction."""
                """ Transactions are used to encapsulate the effects of all"""
                """ commands that create new changesets or propagate existing"""
                """ changesets into a repository. For example, the following"""
                """ commands are transactional, and their effects can be"""
                """ rolled back:<ul>"""
                """<li>commit</li>"""
                """<li>import</li>"""
                """<li>pull</li>"""
                """<li>push (with this repository as the destination)</li>"""
                """<li>unbundle</li>"""
                """</ul>"""
                """</p><p><strong>This command is dangerous. Please use with"""
                """ care. </strong></p>"""
            )
        )
        self.hgRollbackAct.triggered.connect(self.__hgRollback)
        self.actions.append(self.hgRollbackAct)

        self.hgServeAct = EricAction(
            self.tr("Serve project repository"),
            self.tr("Serve project repository..."),
            0,
            0,
            self,
            "mercurial_serve",
        )
        self.hgServeAct.setStatusTip(self.tr("Serve the project repository"))
        self.hgServeAct.setWhatsThis(
            self.tr(
                """<b>Serve project repository</b>"""
                """<p>This serves the project repository.</p>"""
            )
        )
        self.hgServeAct.triggered.connect(self.__hgServe)
        self.actions.append(self.hgServeAct)

        self.hgImportAct = EricAction(
            self.tr("Import Patch"),
            EricPixmapCache.getIcon("vcsImportPatch"),
            self.tr("Import Patch..."),
            0,
            0,
            self,
            "mercurial_import",
        )
        self.hgImportAct.setStatusTip(self.tr("Import a patch from a patch file"))
        self.hgImportAct.setWhatsThis(
            self.tr(
                """<b>Import Patch</b>"""
                """<p>This imports a patch from a patch file into the"""
                """ project.</p>"""
            )
        )
        self.hgImportAct.triggered.connect(self.__hgImport)
        self.actions.append(self.hgImportAct)

        self.hgExportAct = EricAction(
            self.tr("Export Patches"),
            EricPixmapCache.getIcon("vcsExportPatch"),
            self.tr("Export Patches..."),
            0,
            0,
            self,
            "mercurial_export",
        )
        self.hgExportAct.setStatusTip(self.tr("Export revisions to patch files"))
        self.hgExportAct.setWhatsThis(
            self.tr(
                """<b>Export Patches</b>"""
                """<p>This exports revisions of the project to patch files.</p>"""
            )
        )
        self.hgExportAct.triggered.connect(self.__hgExport)
        self.actions.append(self.hgExportAct)

        self.hgPhaseAct = EricAction(
            self.tr("Change Phase"),
            self.tr("Change Phase..."),
            0,
            0,
            self,
            "mercurial_change_phase",
        )
        self.hgPhaseAct.setStatusTip(self.tr("Change the phase of revisions"))
        self.hgPhaseAct.setWhatsThis(
            self.tr(
                """<b>Change Phase</b>"""
                """<p>This changes the phase of revisions.</p>"""
            )
        )
        self.hgPhaseAct.triggered.connect(self.__hgPhase)
        self.actions.append(self.hgPhaseAct)

        self.hgGraftAct = EricAction(
            self.tr("Copy Changesets"),
            EricPixmapCache.getIcon("vcsGraft"),
            self.tr("Copy Changesets"),
            0,
            0,
            self,
            "mercurial_graft",
        )
        self.hgGraftAct.setStatusTip(self.tr("Copies changesets from another branch"))
        self.hgGraftAct.setWhatsThis(
            self.tr(
                """<b>Copy Changesets</b>"""
                """<p>This copies changesets from another branch on top of the"""
                """ current working directory with the user, date and"""
                """ description of the original changeset.</p>"""
            )
        )
        self.hgGraftAct.triggered.connect(self.__hgGraft)
        self.actions.append(self.hgGraftAct)

        self.hgGraftContinueAct = EricAction(
            self.tr("Continue Copying Session"),
            self.tr("Continue Copying Session"),
            0,
            0,
            self,
            "mercurial_graft_continue",
        )
        self.hgGraftContinueAct.setStatusTip(
            self.tr("Continue the last copying session after conflicts were resolved")
        )
        self.hgGraftContinueAct.setWhatsThis(
            self.tr(
                """<b>Continue Copying Session</b>"""
                """<p>This continues the last copying session after conflicts"""
                """ were resolved.</p>"""
            )
        )
        self.hgGraftContinueAct.triggered.connect(self.__hgGraftContinue)
        self.actions.append(self.hgGraftContinueAct)

        self.hgGraftStopAct = EricAction(
            self.tr("Stop Copying Session"),
            self.tr("Stop Copying Session"),
            0,
            0,
            self,
            "mercurial_graft_stop",
        )
        self.hgGraftStopAct.setStatusTip(
            self.tr("Stop the interrupted copying session")
        )
        self.hgGraftStopAct.setWhatsThis(
            self.tr(
                """<b>Stop Copying Session</b>"""
                """<p>This stops the interrupted copying session.</p>"""
            )
        )
        self.hgGraftStopAct.triggered.connect(self.__hgGraftStop)
        self.actions.append(self.hgGraftStopAct)

        self.hgGraftAbortAct = EricAction(
            self.tr("Abort Copying Session"),
            self.tr("Abort Copying Session"),
            0,
            0,
            self,
            "mercurial_graft_abort",
        )
        self.hgGraftAbortAct.setStatusTip(
            self.tr("Abort the interrupted copying session and rollback")
        )
        self.hgGraftAbortAct.setWhatsThis(
            self.tr(
                """<b>Abort Copying Session</b>"""
                """<p>This aborts the interrupted copying session and"""
                """ rollbacks to the state before the copy.</p>"""
            )
        )
        self.hgGraftAbortAct.triggered.connect(self.__hgGraftAbort)
        self.actions.append(self.hgGraftAbortAct)

        self.hgAddSubrepoAct = EricAction(
            self.tr("Add"),
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add..."),
            0,
            0,
            self,
            "mercurial_add_subrepo",
        )
        self.hgAddSubrepoAct.setStatusTip(self.tr("Add a sub-repository"))
        self.hgAddSubrepoAct.setWhatsThis(
            self.tr("""<b>Add...</b><p>Add a sub-repository to the project.</p>""")
        )
        self.hgAddSubrepoAct.triggered.connect(self.__hgAddSubrepository)
        self.actions.append(self.hgAddSubrepoAct)

        self.hgRemoveSubreposAct = EricAction(
            self.tr("Remove"),
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Remove..."),
            0,
            0,
            self,
            "mercurial_remove_subrepos",
        )
        self.hgRemoveSubreposAct.setStatusTip(self.tr("Remove sub-repositories"))
        self.hgRemoveSubreposAct.setWhatsThis(
            self.tr(
                """<b>Remove...</b>"""
                """<p>Remove sub-repositories from the project.</p>"""
            )
        )
        self.hgRemoveSubreposAct.triggered.connect(self.__hgRemoveSubrepositories)
        self.actions.append(self.hgRemoveSubreposAct)

        self.hgArchiveAct = EricAction(
            self.tr("Create unversioned archive"),
            EricPixmapCache.getIcon("vcsExport"),
            self.tr("Create unversioned archive..."),
            0,
            0,
            self,
            "mercurial_archive",
        )
        self.hgArchiveAct.setStatusTip(
            self.tr("Create an unversioned archive from the repository")
        )
        self.hgArchiveAct.setWhatsThis(
            self.tr(
                """<b>Create unversioned archive...</b>"""
                """<p>This creates an unversioned archive from the"""
                """ repository.</p>"""
            )
        )
        self.hgArchiveAct.triggered.connect(self.__hgArchive)
        self.actions.append(self.hgArchiveAct)

        self.hgBookmarksListAct = EricAction(
            self.tr("List bookmarks"),
            EricPixmapCache.getIcon("listBookmarks"),
            self.tr("List bookmarks..."),
            0,
            0,
            self,
            "mercurial_list_bookmarks",
        )
        self.hgBookmarksListAct.setStatusTip(self.tr("List bookmarks of the project"))
        self.hgBookmarksListAct.setWhatsThis(
            self.tr(
                """<b>List bookmarks</b>"""
                """<p>This lists the bookmarks of the project.</p>"""
            )
        )
        self.hgBookmarksListAct.triggered.connect(self.__hgBookmarksList)
        self.actions.append(self.hgBookmarksListAct)

        self.hgBookmarkDefineAct = EricAction(
            self.tr("Define bookmark"),
            EricPixmapCache.getIcon("addBookmark"),
            self.tr("Define bookmark..."),
            0,
            0,
            self,
            "mercurial_define_bookmark",
        )
        self.hgBookmarkDefineAct.setStatusTip(
            self.tr("Define a bookmark for the project")
        )
        self.hgBookmarkDefineAct.setWhatsThis(
            self.tr(
                """<b>Define bookmark</b>"""
                """<p>This defines a bookmark for the project.</p>"""
            )
        )
        self.hgBookmarkDefineAct.triggered.connect(self.__hgBookmarkDefine)
        self.actions.append(self.hgBookmarkDefineAct)

        self.hgBookmarkDeleteAct = EricAction(
            self.tr("Delete bookmark"),
            EricPixmapCache.getIcon("deleteBookmark"),
            self.tr("Delete bookmark..."),
            0,
            0,
            self,
            "mercurial_delete_bookmark",
        )
        self.hgBookmarkDeleteAct.setStatusTip(
            self.tr("Delete a bookmark of the project")
        )
        self.hgBookmarkDeleteAct.setWhatsThis(
            self.tr(
                """<b>Delete bookmark</b>"""
                """<p>This deletes a bookmark of the project.</p>"""
            )
        )
        self.hgBookmarkDeleteAct.triggered.connect(self.__hgBookmarkDelete)
        self.actions.append(self.hgBookmarkDeleteAct)

        self.hgBookmarkRenameAct = EricAction(
            self.tr("Rename bookmark"),
            EricPixmapCache.getIcon("renameBookmark"),
            self.tr("Rename bookmark..."),
            0,
            0,
            self,
            "mercurial_rename_bookmark",
        )
        self.hgBookmarkRenameAct.setStatusTip(
            self.tr("Rename a bookmark of the project")
        )
        self.hgBookmarkRenameAct.setWhatsThis(
            self.tr(
                """<b>Rename bookmark</b>"""
                """<p>This renames a bookmark of the project.</p>"""
            )
        )
        self.hgBookmarkRenameAct.triggered.connect(self.__hgBookmarkRename)
        self.actions.append(self.hgBookmarkRenameAct)

        self.hgBookmarkMoveAct = EricAction(
            self.tr("Move bookmark"),
            EricPixmapCache.getIcon("moveBookmark"),
            self.tr("Move bookmark..."),
            0,
            0,
            self,
            "mercurial_move_bookmark",
        )
        self.hgBookmarkMoveAct.setStatusTip(self.tr("Move a bookmark of the project"))
        self.hgBookmarkMoveAct.setWhatsThis(
            self.tr(
                """<b>Move bookmark</b>"""
                """<p>This moves a bookmark of the project to another"""
                """ changeset.</p>"""
            )
        )
        self.hgBookmarkMoveAct.triggered.connect(self.__hgBookmarkMove)
        self.actions.append(self.hgBookmarkMoveAct)

        self.hgBookmarkIncomingAct = EricAction(
            self.tr("Show incoming bookmarks"),
            EricPixmapCache.getIcon("incomingBookmark"),
            self.tr("Show incoming bookmarks"),
            0,
            0,
            self,
            "mercurial_incoming_bookmarks",
        )
        self.hgBookmarkIncomingAct.setStatusTip(
            self.tr("Show a list of incoming bookmarks")
        )
        self.hgBookmarkIncomingAct.setWhatsThis(
            self.tr(
                """<b>Show incoming bookmarks</b>"""
                """<p>This shows a list of new bookmarks available at the remote"""
                """ repository.</p>"""
            )
        )
        self.hgBookmarkIncomingAct.triggered.connect(self.__hgBookmarkIncoming)
        self.actions.append(self.hgBookmarkIncomingAct)

        self.hgBookmarkPullAct = EricAction(
            self.tr("Pull bookmark"),
            EricPixmapCache.getIcon("pullBookmark"),
            self.tr("Pull bookmark"),
            0,
            0,
            self,
            "mercurial_pull_bookmark",
        )
        self.hgBookmarkPullAct.setStatusTip(
            self.tr("Pull a bookmark from a remote repository")
        )
        self.hgBookmarkPullAct.setWhatsThis(
            self.tr(
                """<b>Pull bookmark</b>"""
                """<p>This pulls a bookmark from a remote repository into the """
                """local repository.</p>"""
            )
        )
        self.hgBookmarkPullAct.triggered.connect(self.__hgBookmarkPull)
        self.actions.append(self.hgBookmarkPullAct)

        self.hgBookmarkPullCurrentAct = EricAction(
            self.tr("Pull current bookmark"),
            EricPixmapCache.getIcon("pullBookmark"),
            self.tr("Pull current bookmark"),
            0,
            0,
            self,
            "mercurial_pull_current_bookmark",
        )
        self.hgBookmarkPullCurrentAct.setStatusTip(
            self.tr("Pull the current bookmark from a remote repository")
        )
        self.hgBookmarkPullCurrentAct.setWhatsThis(
            self.tr(
                """<b>Pull current bookmark</b>"""
                """<p>This pulls the current bookmark from a remote"""
                """ repository into the local repository.</p>"""
            )
        )
        self.hgBookmarkPullCurrentAct.triggered.connect(self.__hgBookmarkPullCurrent)

        self.hgBookmarkOutgoingAct = EricAction(
            self.tr("Show outgoing bookmarks"),
            EricPixmapCache.getIcon("outgoingBookmark"),
            self.tr("Show outgoing bookmarks"),
            0,
            0,
            self,
            "mercurial_outgoing_bookmarks",
        )
        self.hgBookmarkOutgoingAct.setStatusTip(
            self.tr("Show a list of outgoing bookmarks")
        )
        self.hgBookmarkOutgoingAct.setWhatsThis(
            self.tr(
                """<b>Show outgoing bookmarks</b>"""
                """<p>This shows a list of new bookmarks available at the local"""
                """ repository.</p>"""
            )
        )
        self.hgBookmarkOutgoingAct.triggered.connect(self.__hgBookmarkOutgoing)
        self.actions.append(self.hgBookmarkOutgoingAct)

        self.hgBookmarkPushAct = EricAction(
            self.tr("Push bookmark"),
            EricPixmapCache.getIcon("pushBookmark"),
            self.tr("Push bookmark"),
            0,
            0,
            self,
            "mercurial_push_bookmark",
        )
        self.hgBookmarkPushAct.setStatusTip(
            self.tr("Push a bookmark to a remote repository")
        )
        self.hgBookmarkPushAct.setWhatsThis(
            self.tr(
                """<b>Push bookmark</b>"""
                """<p>This pushes a bookmark from the local repository to a """
                """remote repository.</p>"""
            )
        )
        self.hgBookmarkPushAct.triggered.connect(self.__hgBookmarkPush)
        self.actions.append(self.hgBookmarkPushAct)

        self.hgBookmarkPushCurrentAct = EricAction(
            self.tr("Push current bookmark"),
            EricPixmapCache.getIcon("pushBookmark"),
            self.tr("Push current bookmark"),
            0,
            0,
            self,
            "mercurial_push_current_bookmark",
        )
        self.hgBookmarkPushCurrentAct.setStatusTip(
            self.tr("Push the current bookmark to a remote repository")
        )
        self.hgBookmarkPushCurrentAct.setWhatsThis(
            self.tr(
                """<b>Push current bookmark</b>"""
                """<p>This pushes the current bookmark from the local"""
                """ repository to a remote repository.</p>"""
            )
        )
        self.hgBookmarkPushCurrentAct.triggered.connect(self.__hgBookmarkPushCurrent)
        self.actions.append(self.hgBookmarkPushCurrentAct)

        self.hgBookmarkPushAllAct = EricAction(
            self.tr("Push all bookmarks"),
            EricPixmapCache.getIcon("pushBookmark"),
            self.tr("Push all bookmarks"),
            0,
            0,
            self,
            "mercurial_push_all_bookmarks",
        )
        self.hgBookmarkPushAllAct.setStatusTip(
            self.tr("Push all bookmarks to a remote repository")
        )
        self.hgBookmarkPushAllAct.setWhatsThis(
            self.tr(
                """<b>Push all bookmarks</b>"""
                """<p>This pushes all bookmark from the local"""
                """ repository to a remote repository.</p>"""
            )
        )
        self.hgBookmarkPushAllAct.triggered.connect(self.__hgBookmarkPushAll)

        self.hgDeleteBackupsAct = EricAction(
            self.tr("Delete all backups"),
            EricPixmapCache.getIcon("clearPrivateData"),
            self.tr("Delete all backups"),
            0,
            0,
            self,
            "mercurial_delete_all_backups",
        )
        self.hgDeleteBackupsAct.setStatusTip(
            self.tr("Delete all backup bundles stored in the backup area")
        )
        self.hgDeleteBackupsAct.setWhatsThis(
            self.tr(
                """<b>Delete all backups</b>"""
                """<p>This deletes all backup bundles stored in the backup"""
                """ area of the repository.</p>"""
            )
        )
        self.hgDeleteBackupsAct.triggered.connect(self.__hgDeleteBackups)
        self.actions.append(self.hgDeleteBackupsAct)

    def __checkActions(self):
        """
        Private slot to set the enabled status of actions.
        """
        self.hgPullAct.setEnabled(self.vcs.canPull())
        self.hgIncomingAct.setEnabled(self.vcs.canPull())
        self.hgBookmarkPullAct.setEnabled(self.vcs.canPull())
        self.hgBookmarkIncomingAct.setEnabled(self.vcs.canPull())
        self.hgBookmarkPullCurrentAct.setEnabled(self.vcs.canPull())

        self.hgPushAct.setEnabled(self.vcs.canPush())
        self.hgPushBranchAct.setEnabled(self.vcs.canPush())
        self.hgPushForcedAct.setEnabled(self.vcs.canPush())
        self.hgOutgoingAct.setEnabled(self.vcs.canPush())
        self.hgBookmarkPushAct.setEnabled(self.vcs.canPush())
        self.hgBookmarkOutgoingAct.setEnabled(self.vcs.canPush())
        self.hgBookmarkPushCurrentAct.setEnabled(self.vcs.canPush())
        if self.vcs.version >= (5, 7):
            self.hgBookmarkPushAllAct.setEnabled(self.vcs.canPush())

        self.hgCommitMergeAct.setEnabled(self.vcs.canCommitMerge())

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
        adminMenu.addAction(self.hgHeadsAct)
        adminMenu.addAction(self.hgParentsAct)
        adminMenu.addAction(self.hgTipAct)
        adminMenu.addAction(self.hgShowBranchAct)
        adminMenu.addAction(self.hgIdentifyAct)
        adminMenu.addSeparator()
        adminMenu.addAction(self.hgShowPathsAct)
        adminMenu.addSeparator()
        adminMenu.addAction(self.hgShowConfigAct)
        adminMenu.addAction(self.hgRepoConfigAct)
        adminMenu.addSeparator()
        adminMenu.addAction(self.hgCreateIgnoreAct)
        adminMenu.addSeparator()
        adminMenu.addAction(self.hgRecoverAct)
        adminMenu.addSeparator()
        adminMenu.addAction(self.hgBackoutAct)
        adminMenu.addAction(self.hgRollbackAct)
        adminMenu.addSeparator()
        adminMenu.addAction(self.hgVerifyAct)
        adminMenu.addSeparator()
        adminMenu.addAction(self.hgDeleteBackupsAct)
        self.subMenus.append(adminMenu)

        specialsMenu = QMenu(self.tr("Specials"), menu)
        specialsMenu.setTearOffEnabled(True)
        specialsMenu.addAction(self.hgArchiveAct)
        specialsMenu.addSeparator()
        specialsMenu.addAction(self.hgPushForcedAct)
        specialsMenu.addSeparator()
        specialsMenu.addAction(self.hgServeAct)
        self.subMenus.append(specialsMenu)

        bundleMenu = QMenu(self.tr("Changegroup Management"), menu)
        bundleMenu.setTearOffEnabled(True)
        bundleMenu.addAction(self.hgBundleAct)
        bundleMenu.addAction(self.hgPreviewBundleAct)
        bundleMenu.addAction(self.hgUnbundleAct)
        self.subMenus.append(bundleMenu)

        patchMenu = QMenu(self.tr("Patch Management"), menu)
        patchMenu.setTearOffEnabled(True)
        patchMenu.addAction(self.hgImportAct)
        patchMenu.addAction(self.hgExportAct)
        self.subMenus.append(patchMenu)

        bisectMenu = QMenu(self.tr("Bisect"), menu)
        bisectMenu.setTearOffEnabled(True)
        bisectMenu.addAction(self.hgBisectGoodAct)
        bisectMenu.addAction(self.hgBisectBadAct)
        bisectMenu.addAction(self.hgBisectSkipAct)
        bisectMenu.addAction(self.hgBisectResetAct)
        self.subMenus.append(bisectMenu)

        tagsMenu = QMenu(self.tr("Tags"), menu)
        tagsMenu.setIcon(EricPixmapCache.getIcon("vcsTag"))
        tagsMenu.setTearOffEnabled(True)
        tagsMenu.addAction(self.vcsTagAct)
        tagsMenu.addAction(self.hgTagListAct)
        self.subMenus.append(tagsMenu)

        branchesMenu = QMenu(self.tr("Branches"), menu)
        branchesMenu.setIcon(EricPixmapCache.getIcon("vcsBranch"))
        branchesMenu.setTearOffEnabled(True)
        branchesMenu.addAction(self.hgBranchAct)
        branchesMenu.addAction(self.hgPushBranchAct)
        branchesMenu.addAction(self.hgCloseBranchAct)
        branchesMenu.addAction(self.hgBranchListAct)
        self.subMenus.append(branchesMenu)

        bookmarksMenu = QMenu(self.tr("Bookmarks"), menu)
        bookmarksMenu.setIcon(EricPixmapCache.getIcon("bookmark22"))
        bookmarksMenu.setTearOffEnabled(True)
        bookmarksMenu.addAction(self.hgBookmarkDefineAct)
        bookmarksMenu.addAction(self.hgBookmarkDeleteAct)
        bookmarksMenu.addAction(self.hgBookmarkRenameAct)
        bookmarksMenu.addAction(self.hgBookmarkMoveAct)
        bookmarksMenu.addSeparator()
        bookmarksMenu.addAction(self.hgBookmarksListAct)
        bookmarksMenu.addSeparator()
        bookmarksMenu.addAction(self.hgBookmarkIncomingAct)
        bookmarksMenu.addAction(self.hgBookmarkPullAct)
        bookmarksMenu.addAction(self.hgBookmarkPullCurrentAct)
        bookmarksMenu.addSeparator()
        bookmarksMenu.addAction(self.hgBookmarkOutgoingAct)
        bookmarksMenu.addAction(self.hgBookmarkPushAct)
        bookmarksMenu.addAction(self.hgBookmarkPushCurrentAct)
        if self.vcs.version >= (5, 7):
            bookmarksMenu.addAction(self.hgBookmarkPushAllAct)
        self.subMenus.append(bookmarksMenu)

        self.__builtinsMenu = QMenu(self.tr("Other Functions"), menu)
        self.__builtinsMenu.setTearOffEnabled(True)
        self.__builtinMenus = {}
        for builtinMenuTitle in sorted(self.__builtinMenuTitles):
            builtinName = self.__builtinMenuTitles[builtinMenuTitle]
            builtinMenu = self.__builtins[builtinName].initMenu(self.__builtinsMenu)
            self.__builtinMenus[builtinName] = builtinMenu
            self.__builtinsMenu.addMenu(builtinMenu)

        self.__extensionsMenu = QMenu(self.tr("Extensions"), menu)
        self.__extensionsMenu.setTearOffEnabled(True)
        self.__extensionsMenu.aboutToShow.connect(self.__showExtensionMenu)
        self.__extensionMenus = {}
        for extensionMenuTitle in sorted(self.__extensionMenuTitles):
            extensionName = self.__extensionMenuTitles[extensionMenuTitle]
            extensionMenu = self.__extensions[extensionName].initMenu(
                self.__extensionsMenu
            )
            self.__extensionMenus[extensionName] = extensionMenu
            self.__extensionsMenu.addMenu(extensionMenu)
        self.vcs.activeExtensionsChanged.connect(self.__showExtensionMenu)

        graftMenu = QMenu(self.tr("Copy Changesets"), menu)
        graftMenu.setIcon(EricPixmapCache.getIcon("vcsGraft"))
        graftMenu.setTearOffEnabled(True)
        graftMenu.addAction(self.hgGraftAct)
        graftMenu.addAction(self.hgGraftContinueAct)
        if self.vcs.version >= (4, 7, 0):
            graftMenu.addAction(self.hgGraftStopAct)
            graftMenu.addAction(self.hgGraftAbortAct)

        subrepoMenu = QMenu(self.tr("Sub-Repository"), menu)
        subrepoMenu.setTearOffEnabled(True)
        subrepoMenu.addAction(self.hgAddSubrepoAct)
        subrepoMenu.addAction(self.hgRemoveSubreposAct)

        mergeMenu = QMenu(self.tr("Merge Changesets"), menu)
        mergeMenu.setIcon(EricPixmapCache.getIcon("vcsMerge"))
        mergeMenu.setTearOffEnabled(True)
        mergeMenu.addAction(self.vcsMergeAct)
        mergeMenu.addAction(self.hgShowConflictsAct)
        mergeMenu.addAction(self.vcsResolveAct)
        mergeMenu.addAction(self.hgUnresolveAct)
        mergeMenu.addAction(self.hgReMergeAct)
        mergeMenu.addAction(self.hgCommitMergeAct)
        mergeMenu.addAction(self.hgAbortMergeAct)

        act = menu.addAction(
            EricPixmapCache.getIcon(
                os.path.join("VcsPlugins", "vcsMercurial", "icons", "mercurial.svg")
            ),
            self.vcs.vcsName(),
            self._vcsInfoDisplay,
        )
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        menu.addSeparator()

        menu.addAction(self.hgIncomingAct)
        menu.addAction(self.hgPullAct)
        menu.addAction(self.vcsUpdateAct)
        menu.addSeparator()
        menu.addAction(self.vcsCommitAct)
        menu.addAction(self.hgOutgoingAct)
        menu.addAction(self.hgPushAct)
        menu.addSeparator()
        menu.addAction(self.vcsRevertAct)
        menu.addMenu(mergeMenu)
        menu.addMenu(graftMenu)
        menu.addAction(self.hgPhaseAct)
        menu.addSeparator()
        menu.addMenu(bundleMenu)
        menu.addMenu(patchMenu)
        menu.addSeparator()
        menu.addMenu(tagsMenu)
        menu.addMenu(branchesMenu)
        menu.addMenu(bookmarksMenu)
        menu.addSeparator()
        menu.addAction(self.hgLogBrowserAct)
        menu.addSeparator()
        menu.addAction(self.vcsStatusAct)
        menu.addAction(self.hgSummaryAct)
        menu.addSeparator()
        menu.addAction(self.vcsDiffAct)
        menu.addAction(self.hgExtDiffAct)
        menu.addSeparator()
        menu.addMenu(self.__builtinsMenu)
        menu.addMenu(self.__extensionsMenu)
        menu.addSeparator()
        menu.addAction(self.vcsSwitchAct)
        menu.addSeparator()
        menu.addMenu(subrepoMenu)
        menu.addSeparator()
        menu.addMenu(bisectMenu)
        menu.addSeparator()
        menu.addAction(self.vcsCleanupAct)
        menu.addSeparator()
        menu.addAction(self.vcsCommandAct)
        menu.addSeparator()
        menu.addMenu(adminMenu)
        menu.addMenu(specialsMenu)
        menu.addSeparator()
        menu.addAction(self.hgEditUserConfigAct)
        menu.addAction(self.hgConfigAct)
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
        self.__toolbarManager = toolbarManager

        self.__toolbar = QToolBar(self.tr("Mercurial"), ui)
        self.__toolbar.setObjectName("MercurialToolbar")
        self.__toolbar.setToolTip(self.tr("Mercurial"))

        self.__toolbar.addAction(self.hgLogBrowserAct)
        self.__toolbar.addAction(self.vcsStatusAct)
        self.__toolbar.addSeparator()
        self.__toolbar.addAction(self.vcsDiffAct)
        self.__toolbar.addSeparator()
        self.__toolbar.addAction(self.vcsNewAct)
        self.__toolbar.addAction(self.vcsExportAct)
        self.__toolbar.addSeparator()

        title = self.__toolbar.windowTitle()
        toolbarManager.addToolBar(self.__toolbar, title)
        toolbarManager.addAction(self.hgIncomingAct, title)
        toolbarManager.addAction(self.hgPullAct, title)
        toolbarManager.addAction(self.vcsUpdateAct, title)
        toolbarManager.addAction(self.vcsCommitAct, title)
        toolbarManager.addAction(self.hgOutgoingAct, title)
        toolbarManager.addAction(self.hgPushAct, title)
        toolbarManager.addAction(self.hgPushForcedAct, title)
        toolbarManager.addAction(self.hgExtDiffAct, title)
        toolbarManager.addAction(self.hgSummaryAct, title)
        toolbarManager.addAction(self.vcsRevertAct, title)
        toolbarManager.addAction(self.vcsMergeAct, title)
        toolbarManager.addAction(self.hgReMergeAct, title)
        toolbarManager.addAction(self.hgCommitMergeAct, title)
        toolbarManager.addAction(self.vcsTagAct, title)
        toolbarManager.addAction(self.hgBranchAct, title)
        toolbarManager.addAction(self.vcsSwitchAct, title)
        toolbarManager.addAction(self.hgGraftAct, title)
        toolbarManager.addAction(self.hgAddSubrepoAct, title)
        toolbarManager.addAction(self.hgRemoveSubreposAct, title)
        toolbarManager.addAction(self.hgArchiveAct, title)
        toolbarManager.addAction(self.hgBookmarksListAct, title)
        toolbarManager.addAction(self.hgBookmarkDefineAct, title)
        toolbarManager.addAction(self.hgBookmarkDeleteAct, title)
        toolbarManager.addAction(self.hgBookmarkRenameAct, title)
        toolbarManager.addAction(self.hgBookmarkMoveAct, title)
        toolbarManager.addAction(self.hgBookmarkIncomingAct, title)
        toolbarManager.addAction(self.hgBookmarkPullAct, title)
        toolbarManager.addAction(self.hgBookmarkPullCurrentAct, title)
        toolbarManager.addAction(self.hgBookmarkOutgoingAct, title)
        toolbarManager.addAction(self.hgBookmarkPushAct, title)
        toolbarManager.addAction(self.hgBookmarkPushCurrentAct, title)
        toolbarManager.addAction(self.hgImportAct, title)
        toolbarManager.addAction(self.hgExportAct, title)
        toolbarManager.addAction(self.hgBundleAct, title)
        toolbarManager.addAction(self.hgPreviewBundleAct, title)
        toolbarManager.addAction(self.hgUnbundleAct, title)
        toolbarManager.addAction(self.hgDeleteBackupsAct, title)

        self.__toolbar.setEnabled(False)
        self.__toolbar.setVisible(False)

        ui.registerToolbar(
            "mercurial", self.__toolbar.windowTitle(), self.__toolbar, "vcs"
        )
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
        ui.unregisterToolbar("mercurial")

        title = self.__toolbar.windowTitle()
        toolbarManager.removeCategoryActions(title)
        toolbarManager.removeToolBar(self.__toolbar)

        self.__toolbar.deleteLater()
        self.__toolbar = None

    def showMenu(self):
        """
        Public slot called before the vcs menu is shown.
        """
        super().showMenu()

        self.__checkActions()

    def shutdown(self):
        """
        Public method to perform shutdown actions.
        """
        self.vcs.activeExtensionsChanged.disconnect(self.__showExtensionMenu)
        self.vcs.iniFileChanged.disconnect(self.__checkActions)

        # close torn off sub menus
        for menu in self.subMenus:
            if menu.isTearOffMenuVisible():
                menu.hideTearOffMenu()

        # close torn off extension menus
        for extensionName in self.__extensionMenus:
            self.__extensions[extensionName].shutdown()
            menu = self.__extensionMenus[extensionName]
            if menu.isTearOffMenuVisible():
                menu.hideTearOffMenu()

        if self.__extensionsMenu.isTearOffMenuVisible():
            self.__extensionsMenu.hideTearOffMenu()

    def __showExtensionMenu(self):
        """
        Private slot showing the extensions menu.
        """
        for extensionName in self.__extensionMenus:
            extensionMenu = self.__extensionMenus[extensionName]
            extensionMenu.menuAction().setEnabled(
                self.vcs.isExtensionActive(extensionName)
            )
            if (
                not extensionMenu.menuAction().isEnabled()
                and extensionMenu.isTearOffMenuVisible()
            ):
                extensionMenu.hideTearOffMenu()

    def __hgExtendedDiff(self):
        """
        Private slot used to perform a hg diff with the selection of revisions.
        """
        self.vcs.hgExtendedDiff(self.project.ppath)

    def __hgIncoming(self):
        """
        Private slot used to show the log of changes coming into the
        repository.
        """
        self.vcs.hgIncoming()

    def __hgOutgoing(self):
        """
        Private slot used to show the log of changes going out of the
        repository.
        """
        self.vcs.hgOutgoing()

    def __hgPull(self):
        """
        Private slot used to pull changes from a remote repository.
        """
        shouldReopen = self.vcs.hgPull()
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Pull"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __hgPush(self):
        """
        Private slot used to push changes to a remote repository.
        """
        self.vcs.hgPush()

    def __hgPushForced(self):
        """
        Private slot used to push changes to a remote repository using
        the force option.
        """
        self.vcs.hgPush(force=True)

    def __hgHeads(self):
        """
        Private slot used to show the heads of the repository.
        """
        self.vcs.hgInfo(mode="heads")

    def __hgParents(self):
        """
        Private slot used to show the parents of the repository.
        """
        self.vcs.hgInfo(mode="parents")

    def __hgTip(self):
        """
        Private slot used to show the tip of the repository.
        """
        self.vcs.hgInfo(mode="tip")

    def __hgResolved(self):
        """
        Private slot used to mark conflicts of the local project as being
        resolved.
        """
        self.vcs.vcsResolved(self.project.ppath)

    def __hgUnresolved(self):
        """
        Private slot used to mark conflicts of the local project as being
        unresolved.
        """
        self.vcs.vcsResolved(self.project.ppath, unresolve=True)

    def __hgCommitMerge(self):
        """
        Private slot used to commit a merge.
        """
        self.vcs.vcsCommit(self.project.ppath, self.tr("Merge"), merge=True)

    def __hgAbortMerge(self):
        """
        Private slot used to abort an uncommitted merge.
        """
        self.vcs.hgAbortMerge()

    def __hgShowConflicts(self):
        """
        Private slot used to list all files with conflicts.
        """
        self.vcs.hgConflicts()

    def __hgReMerge(self):
        """
        Private slot used to list all files with conflicts.
        """
        self.vcs.hgReMerge(self.project.ppath)

    def __hgTagList(self):
        """
        Private slot used to list the tags of the project.
        """
        self.vcs.hgListTagBranch(True)

    def __hgBranchList(self):
        """
        Private slot used to list the branches of the project.
        """
        self.vcs.hgListTagBranch(False)

    def __hgBranch(self):
        """
        Private slot used to create a new branch for the project.
        """
        self.vcs.hgBranch()

    def __hgShowBranch(self):
        """
        Private slot used to show the current branch for the project.
        """
        self.vcs.hgShowBranch()

    def __hgConfigure(self):
        """
        Private method to open the configuration dialog.
        """
        ericApp().getObject("UserInterface").showPreferences("zzz_mercurialPage")

    def __hgCloseBranch(self):
        """
        Private slot used to close the current branch of the local project.
        """
        if Preferences.getVCS("AutoSaveProject"):
            self.project.saveProject()
        if Preferences.getVCS("AutoSaveFiles"):
            self.project.saveAllScripts()
        self.vcs.vcsCommit(self.project.ppath, "", closeBranch=True)

    def __hgPushNewBranch(self):
        """
        Private slot to push a new named branch.
        """
        self.vcs.hgPush(newBranch=True)

    def __hgEditUserConfig(self):
        """
        Private slot used to edit the user configuration file.
        """
        self.vcs.hgEditUserConfig()

    def __hgEditRepoConfig(self):
        """
        Private slot used to edit the repository configuration file.
        """
        self.vcs.hgEditConfig()

    def __hgShowConfig(self):
        """
        Private slot used to show the combined configuration.
        """
        self.vcs.hgShowConfig()

    def __hgVerify(self):
        """
        Private slot used to verify the integrity of the repository.
        """
        self.vcs.hgVerify()

    def __hgShowPaths(self):
        """
        Private slot used to show the aliases for remote repositories.
        """
        self.vcs.hgShowPaths()

    def __hgRecover(self):
        """
        Private slot used to recover from an interrupted transaction.
        """
        self.vcs.hgRecover()

    def __hgIdentify(self):
        """
        Private slot used to identify the project directory.
        """
        self.vcs.hgIdentify()

    def __hgCreateIgnore(self):
        """
        Private slot used to create a .hgignore file for the project.
        """
        self.vcs.hgCreateIgnoreFile(self.project.ppath, autoAdd=True)

    def __hgBundle(self):
        """
        Private slot used to create a changegroup file.
        """
        self.vcs.hgBundle()

    def __hgPreviewBundle(self):
        """
        Private slot used to preview a changegroup file.
        """
        self.vcs.hgPreviewBundle()

    def __hgUnbundle(self):
        """
        Private slot used to apply changegroup files.
        """
        shouldReopen = self.vcs.hgUnbundle()
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Apply changegroups"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __hgBisectGood(self):
        """
        Private slot used to execute the bisect --good command.
        """
        self.vcs.hgBisect("good")

    def __hgBisectBad(self):
        """
        Private slot used to execute the bisect --bad command.
        """
        self.vcs.hgBisect("bad")

    def __hgBisectSkip(self):
        """
        Private slot used to execute the bisect --skip command.
        """
        self.vcs.hgBisect("skip")

    def __hgBisectReset(self):
        """
        Private slot used to execute the bisect --reset command.
        """
        self.vcs.hgBisect("reset")

    def __hgBackout(self):
        """
        Private slot used to back out changes of a changeset.
        """
        self.vcs.hgBackout()

    def __hgRollback(self):
        """
        Private slot used to rollback the last transaction.
        """
        self.vcs.hgRollback()

    def __hgServe(self):
        """
        Private slot used to serve the project.
        """
        self.vcs.hgServe(self.project.ppath)

    def __hgImport(self):
        """
        Private slot used to import a patch file.
        """
        shouldReopen = self.vcs.hgImport()
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Import Patch"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __hgExport(self):
        """
        Private slot used to export revisions to patch files.
        """
        self.vcs.hgExport()

    def __hgRevert(self):
        """
        Private slot used to revert changes made to the local project.
        """
        shouldReopen = self.vcs.vcsRevert(self.project.ppath)
        if shouldReopen:
            res = EricMessageBox.yesNo(
                self.parent(),
                self.tr("Revert Changes"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __hgPhase(self):
        """
        Private slot used to change the phase of revisions.
        """
        self.vcs.hgPhase()

    def __hgGraft(self):
        """
        Private slot used to copy changesets from another branch.
        """
        shouldReopen = self.vcs.hgGraft()
        if shouldReopen:
            res = EricMessageBox.yesNo(
                None,
                self.tr("Copy Changesets"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __hgGraftContinue(self):
        """
        Private slot used to continue the last copying session after conflicts
        were resolved.
        """
        shouldReopen = self.vcs.hgGraftContinue()
        if shouldReopen:
            res = EricMessageBox.yesNo(
                None,
                self.tr("Copy Changesets (Continue)"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __hgGraftStop(self):
        """
        Private slot used to stop an interrupted copying session.
        """
        shouldReopen = self.vcs.hgGraftStop()
        if shouldReopen:
            res = EricMessageBox.yesNo(
                None,
                self.tr("Copy Changesets (Stop)"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __hgGraftAbort(self):
        """
        Private slot used to abort an interrupted copying session and perform
        a rollback.
        """
        shouldReopen = self.vcs.hgGraftAbort()
        if shouldReopen:
            res = EricMessageBox.yesNo(
                None,
                self.tr("Copy Changesets (Abort)"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __hgAddSubrepository(self):
        """
        Private slot used to add a sub-repository.
        """
        self.vcs.hgAddSubrepository()

    def __hgRemoveSubrepositories(self):
        """
        Private slot used to remove sub-repositories.
        """
        self.vcs.hgRemoveSubrepositories()

    def __hgSummary(self):
        """
        Private slot to show a working directory summary.
        """
        self.vcs.hgSummary()

    def __hgArchive(self):
        """
        Private slot to create an unversioned archive from the repository.
        """
        self.vcs.hgArchive()

    def __hgBookmarksList(self):
        """
        Private slot used to list the bookmarks.
        """
        self.vcs.hgListBookmarks()

    def __hgBookmarkDefine(self):
        """
        Private slot used to define a bookmark.
        """
        self.vcs.hgBookmarkDefine()

    def __hgBookmarkDelete(self):
        """
        Private slot used to delete a bookmark.
        """
        self.vcs.hgBookmarkDelete()

    def __hgBookmarkRename(self):
        """
        Private slot used to rename a bookmark.
        """
        self.vcs.hgBookmarkRename()

    def __hgBookmarkMove(self):
        """
        Private slot used to move a bookmark.
        """
        self.vcs.hgBookmarkMove()

    def __hgBookmarkIncoming(self):
        """
        Private slot used to show a list of incoming bookmarks.
        """
        self.vcs.hgBookmarkIncoming()

    def __hgBookmarkOutgoing(self):
        """
        Private slot used to show a list of outgoing bookmarks.
        """
        self.vcs.hgBookmarkOutgoing()

    def __hgBookmarkPull(self):
        """
        Private slot used to pull a bookmark from a remote repository.
        """
        self.vcs.hgBookmarkPull()

    def __hgBookmarkPullCurrent(self):
        """
        Private slot used to pull the current bookmark from a remote
        repository.
        """
        self.vcs.hgBookmarkPull(current=True)

    def __hgBookmarkPush(self):
        """
        Private slot used to push a bookmark to a remote repository.
        """
        self.vcs.hgBookmarkPush()

    def __hgBookmarkPushCurrent(self):
        """
        Private slot used to push the current bookmark to a remote repository.
        """
        self.vcs.hgBookmarkPush(current=True)

    def __hgBookmarkPushAll(self):
        """
        Private slot to push all bookmarks to a remote repository.
        """
        self.vcs.hgBookmarkPush(allBookmarks=True)

    def __hgDeleteBackups(self):
        """
        Private slot used to delete all backup bundles.
        """
        self.vcs.hgDeleteBackups()
