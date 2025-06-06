# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the VCS project helper for Subversion.
"""

import os

from PyQt6.QtWidgets import QToolBar

from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets.EricApplication import ericApp
from eric7.VCS.ProjectHelper import VcsProjectHelper


class SvnProjectHelper(VcsProjectHelper):
    """
    Class implementing the VCS project helper for Subversion.
    """

    def __init__(self, vcsObject, projectObject, parent=None, name=None):
        """
        Constructor

        @param vcsObject reference to the vcs object
        @type Subversion
        @param projectObject reference to the project object
        @type Project
        @param parent parent widget
        @type QWidget
        @param name name of this object
        @type str
        """
        VcsProjectHelper.__init__(self, vcsObject, projectObject, parent, name)

    def getActions(self):
        """
        Public method to get a list of all actions.

        @return list of all actions
        @rtype list of EricAction
        """
        return self.actions[:]

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
            "subversion_new",
        )
        self.vcsNewAct.setStatusTip(
            self.tr("Create a new project from the VCS repository")
        )
        self.vcsNewAct.setWhatsThis(
            self.tr(
                """<b>New from repository</b>"""
                """<p>This creates a new local project from the VCS"""
                """ repository.</p>"""
            )
        )
        self.vcsNewAct.triggered.connect(self._vcsCheckout)
        self.actions.append(self.vcsNewAct)

        self.vcsUpdateAct = EricAction(
            self.tr("Update from repository"),
            EricPixmapCache.getIcon("vcsUpdate"),
            self.tr("&Update from repository"),
            0,
            0,
            self,
            "subversion_update",
        )
        self.vcsUpdateAct.setStatusTip(
            self.tr("Update the local project from the VCS repository")
        )
        self.vcsUpdateAct.setWhatsThis(
            self.tr(
                """<b>Update from repository</b>"""
                """<p>This updates the local project from the VCS"""
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
            "subversion_commit",
        )
        self.vcsCommitAct.setStatusTip(
            self.tr("Commit changes to the local project to the VCS repository")
        )
        self.vcsCommitAct.setWhatsThis(
            self.tr(
                """<b>Commit changes to repository</b>"""
                """<p>This commits changes to the local project to the VCS"""
                """ repository.</p>"""
            )
        )
        self.vcsCommitAct.triggered.connect(self._vcsCommit)
        self.actions.append(self.vcsCommitAct)

        self.svnLogBrowserAct = EricAction(
            self.tr("Show log browser"),
            EricPixmapCache.getIcon("vcsLog"),
            self.tr("Show log browser"),
            0,
            0,
            self,
            "subversion_log_browser",
        )
        self.svnLogBrowserAct.setStatusTip(
            self.tr("Show a dialog to browse the log of the local project")
        )
        self.svnLogBrowserAct.setWhatsThis(
            self.tr(
                """<b>Show log browser</b>"""
                """<p>This shows a dialog to browse the log of the local"""
                """ project. A limited number of entries is shown first. More"""
                """ can be retrieved later on.</p>"""
            )
        )
        self.svnLogBrowserAct.triggered.connect(self._vcsLogBrowser)
        self.actions.append(self.svnLogBrowserAct)

        self.vcsDiffAct = EricAction(
            self.tr("Show differences"),
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show &difference"),
            0,
            0,
            self,
            "subversion_diff",
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

        self.svnExtDiffAct = EricAction(
            self.tr("Show differences (extended)"),
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences (extended)"),
            0,
            0,
            self,
            "subversion_extendeddiff",
        )
        self.svnExtDiffAct.setStatusTip(
            self.tr("Show the difference of revisions of the project to the repository")
        )
        self.svnExtDiffAct.setWhatsThis(
            self.tr(
                """<b>Show differences (extended)</b>"""
                """<p>This shows differences of selectable revisions of"""
                """ the project.</p>"""
            )
        )
        self.svnExtDiffAct.triggered.connect(self.__svnExtendedDiff)
        self.actions.append(self.svnExtDiffAct)

        self.svnUrlDiffAct = EricAction(
            self.tr("Show differences (URLs)"),
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences (URLs)"),
            0,
            0,
            self,
            "subversion_urldiff",
        )
        self.svnUrlDiffAct.setStatusTip(
            self.tr("Show the difference of the project between two repository URLs")
        )
        self.svnUrlDiffAct.setWhatsThis(
            self.tr(
                """<b>Show differences (URLs)</b>"""
                """<p>This shows differences of the project between"""
                """ two repository URLs.</p>"""
            )
        )
        self.svnUrlDiffAct.triggered.connect(self.__svnUrlDiff)
        self.actions.append(self.svnUrlDiffAct)

        self.vcsStatusAct = EricAction(
            self.tr("Show status"),
            EricPixmapCache.getIcon("vcsStatus"),
            self.tr("Show &status"),
            0,
            0,
            self,
            "subversion_status",
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

        self.svnChangeListsAct = EricAction(
            self.tr("Show change lists"),
            EricPixmapCache.getIcon("vcsChangeLists"),
            self.tr("Show change lists"),
            0,
            0,
            self,
            "subversion_changelists",
        )
        self.svnChangeListsAct.setStatusTip(
            self.tr("Show the change lists and associated files of the local project")
        )
        self.svnChangeListsAct.setWhatsThis(
            self.tr(
                """<b>Show change lists</b>"""
                """<p>This shows the change lists and associated files of the"""
                """ local project.</p>"""
            )
        )
        self.svnChangeListsAct.triggered.connect(self.__svnChangeLists)
        self.actions.append(self.svnChangeListsAct)

        self.vcsTagAct = EricAction(
            self.tr("Tag in repository"),
            EricPixmapCache.getIcon("vcsTag"),
            self.tr("&Tag in repository..."),
            0,
            0,
            self,
            "subversion_tag",
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

        self.vcsExportAct = EricAction(
            self.tr("Export from repository"),
            EricPixmapCache.getIcon("vcsExport"),
            self.tr("&Export from repository..."),
            0,
            0,
            self,
            "subversion_export",
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

        self.vcsPropsAct = EricAction(
            self.tr("Command options"),
            self.tr("Command &options..."),
            0,
            0,
            self,
            "subversion_options",
        )
        self.vcsPropsAct.setStatusTip(self.tr("Show the VCS command options"))
        self.vcsPropsAct.setWhatsThis(
            self.tr(
                """<b>Command options...</b>"""
                """<p>This shows a dialog to edit the VCS command options.</p>"""
            )
        )
        self.vcsPropsAct.triggered.connect(self._vcsCommandOptions)
        self.actions.append(self.vcsPropsAct)

        self.vcsRevertAct = EricAction(
            self.tr("Revert changes"),
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Re&vert changes"),
            0,
            0,
            self,
            "subversion_revert",
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
        self.vcsRevertAct.triggered.connect(self._vcsRevert)
        self.actions.append(self.vcsRevertAct)

        self.vcsMergeAct = EricAction(
            self.tr("Merge"),
            EricPixmapCache.getIcon("vcsMerge"),
            self.tr("Mer&ge changes..."),
            0,
            0,
            self,
            "subversion_merge",
        )
        self.vcsMergeAct.setStatusTip(
            self.tr("Merge changes of a tag/revision into the local project")
        )
        self.vcsMergeAct.setWhatsThis(
            self.tr(
                """<b>Merge</b>"""
                """<p>This merges changes of a tag/revision into the local"""
                """ project.</p>"""
            )
        )
        self.vcsMergeAct.triggered.connect(self._vcsMerge)
        self.actions.append(self.vcsMergeAct)

        self.vcsSwitchAct = EricAction(
            self.tr("Switch"),
            EricPixmapCache.getIcon("vcsSwitch"),
            self.tr("S&witch..."),
            0,
            0,
            self,
            "subversion_switch",
        )
        self.vcsSwitchAct.setStatusTip(
            self.tr("Switch the local copy to another tag/branch")
        )
        self.vcsSwitchAct.setWhatsThis(
            self.tr(
                """<b>Switch</b>"""
                """<p>This switches the local copy to another tag/branch.</p>"""
            )
        )
        self.vcsSwitchAct.triggered.connect(self._vcsSwitch)
        self.actions.append(self.vcsSwitchAct)

        self.vcsResolveAct = EricAction(
            self.tr("Conflicts resolved"),
            self.tr("Con&flicts resolved"),
            0,
            0,
            self,
            "subversion_resolve",
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
        self.vcsResolveAct.triggered.connect(self.__svnResolve)
        self.actions.append(self.vcsResolveAct)

        self.vcsCleanupAct = EricAction(
            self.tr("Cleanup"), self.tr("Cleanu&p"), 0, 0, self, "subversion_cleanup"
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
            "subversion_command",
        )
        self.vcsCommandAct.setStatusTip(self.tr("Execute an arbitrary VCS command"))
        self.vcsCommandAct.setWhatsThis(
            self.tr(
                """<b>Execute command</b>"""
                """<p>This opens a dialog to enter an arbitrary VCS command.</p>"""
            )
        )
        self.vcsCommandAct.triggered.connect(self._vcsCommand)
        self.actions.append(self.vcsCommandAct)

        self.svnTagListAct = EricAction(
            self.tr("List tags"),
            self.tr("List tags..."),
            0,
            0,
            self,
            "subversion_list_tags",
        )
        self.svnTagListAct.setStatusTip(self.tr("List tags of the project"))
        self.svnTagListAct.setWhatsThis(
            self.tr("""<b>List tags</b><p>This lists the tags of the project.</p>""")
        )
        self.svnTagListAct.triggered.connect(self.__svnTagList)
        self.actions.append(self.svnTagListAct)

        self.svnBranchListAct = EricAction(
            self.tr("List branches"),
            self.tr("List branches..."),
            0,
            0,
            self,
            "subversion_list_branches",
        )
        self.svnBranchListAct.setStatusTip(self.tr("List branches of the project"))
        self.svnBranchListAct.setWhatsThis(
            self.tr(
                """<b>List branches</b>"""
                """<p>This lists the branches of the project.</p>"""
            )
        )
        self.svnBranchListAct.triggered.connect(self.__svnBranchList)
        self.actions.append(self.svnBranchListAct)

        self.svnListAct = EricAction(
            self.tr("List repository contents"),
            self.tr("List repository contents..."),
            0,
            0,
            self,
            "subversion_contents",
        )
        self.svnListAct.setStatusTip(self.tr("Lists the contents of the repository"))
        self.svnListAct.setWhatsThis(
            self.tr(
                """<b>List repository contents</b>"""
                """<p>This lists the contents of the repository.</p>"""
            )
        )
        self.svnListAct.triggered.connect(self.__svnTagList)
        self.actions.append(self.svnListAct)

        self.svnPropSetAct = EricAction(
            self.tr("Set Property"),
            self.tr("Set Property..."),
            0,
            0,
            self,
            "subversion_property_set",
        )
        self.svnPropSetAct.setStatusTip(self.tr("Set a property for the project files"))
        self.svnPropSetAct.setWhatsThis(
            self.tr(
                """<b>Set Property</b>"""
                """<p>This sets a property for the project files.</p>"""
            )
        )
        self.svnPropSetAct.triggered.connect(self.__svnPropSet)
        self.actions.append(self.svnPropSetAct)

        self.svnPropListAct = EricAction(
            self.tr("List Properties"),
            self.tr("List Properties..."),
            0,
            0,
            self,
            "subversion_property_list",
        )
        self.svnPropListAct.setStatusTip(
            self.tr("List properties of the project files")
        )
        self.svnPropListAct.setWhatsThis(
            self.tr(
                """<b>List Properties</b>"""
                """<p>This lists the properties of the project files.</p>"""
            )
        )
        self.svnPropListAct.triggered.connect(self.__svnPropList)
        self.actions.append(self.svnPropListAct)

        self.svnPropDelAct = EricAction(
            self.tr("Delete Property"),
            self.tr("Delete Property..."),
            0,
            0,
            self,
            "subversion_property_delete",
        )
        self.svnPropDelAct.setStatusTip(
            self.tr("Delete a property for the project files")
        )
        self.svnPropDelAct.setWhatsThis(
            self.tr(
                """<b>Delete Property</b>"""
                """<p>This deletes a property for the project files.</p>"""
            )
        )
        self.svnPropDelAct.triggered.connect(self.__svnPropDel)
        self.actions.append(self.svnPropDelAct)

        self.svnRelocateAct = EricAction(
            self.tr("Relocate"),
            EricPixmapCache.getIcon("vcsSwitch"),
            self.tr("Relocate..."),
            0,
            0,
            self,
            "subversion_relocate",
        )
        self.svnRelocateAct.setStatusTip(
            self.tr("Relocate the working copy to a new repository URL")
        )
        self.svnRelocateAct.setWhatsThis(
            self.tr(
                """<b>Relocate</b>"""
                """<p>This relocates the working copy to a new repository"""
                """ URL.</p>"""
            )
        )
        self.svnRelocateAct.triggered.connect(self.__svnRelocate)
        self.actions.append(self.svnRelocateAct)

        self.svnRepoBrowserAct = EricAction(
            self.tr("Repository Browser"),
            EricPixmapCache.getIcon("vcsRepoBrowser"),
            self.tr("Repository Browser..."),
            0,
            0,
            self,
            "subversion_repo_browser",
        )
        self.svnRepoBrowserAct.setStatusTip(
            self.tr("Show the Repository Browser dialog")
        )
        self.svnRepoBrowserAct.setWhatsThis(
            self.tr(
                """<b>Repository Browser</b>"""
                """<p>This shows the Repository Browser dialog.</p>"""
            )
        )
        self.svnRepoBrowserAct.triggered.connect(self.__svnRepoBrowser)
        self.actions.append(self.svnRepoBrowserAct)

        self.svnConfigAct = EricAction(
            self.tr("Configure"),
            self.tr("Configure..."),
            0,
            0,
            self,
            "subversion_configure",
        )
        self.svnConfigAct.setStatusTip(
            self.tr("Show the configuration dialog with the Subversion page selected")
        )
        self.svnConfigAct.setWhatsThis(
            self.tr(
                """<b>Configure</b>"""
                """<p>Show the configuration dialog with the Subversion page"""
                """ selected.</p>"""
            )
        )
        self.svnConfigAct.triggered.connect(self.__svnConfigure)
        self.actions.append(self.svnConfigAct)

        self.svnUpgradeAct = EricAction(
            self.tr("Upgrade"), self.tr("Upgrade..."), 0, 0, self, "subversion_upgrade"
        )
        self.svnUpgradeAct.setStatusTip(
            self.tr("Upgrade the working copy to the current format")
        )
        self.svnUpgradeAct.setWhatsThis(
            self.tr(
                """<b>Upgrade</b>"""
                """<p>Upgrades the working copy to the current format.</p>"""
            )
        )
        self.svnUpgradeAct.triggered.connect(self.__svnUpgrade)
        self.actions.append(self.svnUpgradeAct)

    def initMenu(self, menu):
        """
        Public method to generate the VCS menu.

        @param menu reference to the menu to be populated
        @type QMenu
        """
        menu.clear()

        act = menu.addAction(
            EricPixmapCache.getIcon(
                os.path.join("VcsPlugins", "vcsSubversion", "icons", "subversion.svg")
            ),
            self.vcs.vcsName(),
            self._vcsInfoDisplay,
        )
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        menu.addSeparator()

        menu.addAction(self.vcsUpdateAct)
        menu.addAction(self.vcsCommitAct)
        menu.addSeparator()
        menu.addAction(self.vcsTagAct)
        if self.vcs.otherData["standardLayout"]:
            menu.addAction(self.svnTagListAct)
            menu.addAction(self.svnBranchListAct)
        else:
            menu.addAction(self.svnListAct)
        menu.addSeparator()
        menu.addAction(self.svnLogBrowserAct)
        menu.addSeparator()
        menu.addAction(self.vcsStatusAct)
        menu.addAction(self.svnChangeListsAct)
        menu.addSeparator()
        menu.addAction(self.vcsDiffAct)
        menu.addAction(self.svnExtDiffAct)
        menu.addAction(self.svnUrlDiffAct)
        menu.addSeparator()
        menu.addAction(self.vcsRevertAct)
        menu.addAction(self.vcsMergeAct)
        menu.addAction(self.vcsResolveAct)
        menu.addSeparator()
        menu.addAction(self.svnRelocateAct)
        menu.addAction(self.vcsSwitchAct)
        menu.addSeparator()
        menu.addAction(self.svnPropSetAct)
        menu.addAction(self.svnPropListAct)
        menu.addAction(self.svnPropDelAct)
        menu.addSeparator()
        menu.addAction(self.vcsCleanupAct)
        menu.addSeparator()
        menu.addAction(self.vcsCommandAct)
        menu.addAction(self.svnRepoBrowserAct)
        menu.addAction(self.svnUpgradeAct)
        menu.addSeparator()
        menu.addAction(self.vcsPropsAct)
        menu.addSeparator()
        menu.addAction(self.svnConfigAct)
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
        self.__toolbar = QToolBar(self.tr("Subversion (svn)"), ui)
        self.__toolbar.setObjectName("SubversionToolbar")
        self.__toolbar.setToolTip(self.tr("Subversion (svn)"))

        self.__toolbar.addAction(self.svnLogBrowserAct)
        self.__toolbar.addAction(self.vcsStatusAct)
        self.__toolbar.addSeparator()
        self.__toolbar.addAction(self.vcsDiffAct)
        self.__toolbar.addSeparator()
        self.__toolbar.addAction(self.svnRepoBrowserAct)
        self.__toolbar.addAction(self.vcsNewAct)
        self.__toolbar.addAction(self.vcsExportAct)
        self.__toolbar.addSeparator()

        title = self.__toolbar.windowTitle()
        toolbarManager.addToolBar(self.__toolbar, title)
        toolbarManager.addAction(self.vcsUpdateAct, title)
        toolbarManager.addAction(self.vcsCommitAct, title)
        toolbarManager.addAction(self.svnExtDiffAct, title)
        toolbarManager.addAction(self.svnUrlDiffAct, title)
        toolbarManager.addAction(self.svnChangeListsAct, title)
        toolbarManager.addAction(self.vcsTagAct, title)
        toolbarManager.addAction(self.vcsRevertAct, title)
        toolbarManager.addAction(self.vcsMergeAct, title)
        toolbarManager.addAction(self.vcsSwitchAct, title)
        toolbarManager.addAction(self.svnRelocateAct, title)

        self.__toolbar.setEnabled(False)
        self.__toolbar.setVisible(False)

        ui.registerToolbar(
            "subversion", self.__toolbar.windowTitle(), self.__toolbar, "vcs"
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
        ui.unregisterToolbar("subversion")

        title = self.__toolbar.windowTitle()
        toolbarManager.removeCategoryActions(title)
        toolbarManager.removeToolBar(self.__toolbar)

        self.__toolbar.deleteLater()
        self.__toolbar = None

    def __svnResolve(self):
        """
        Private slot used to resolve conflicts of the local project.
        """
        self.vcs.vcsResolved(self.project.ppath)

    def __svnPropList(self):
        """
        Private slot used to list the properties of the project files.
        """
        self.vcs.svnListProps(self.project.ppath, True)

    def __svnPropSet(self):
        """
        Private slot used to set a property for the project files.
        """
        self.vcs.svnSetProp(self.project.ppath, True)

    def __svnPropDel(self):
        """
        Private slot used to delete a property for the project files.
        """
        self.vcs.svnDelProp(self.project.ppath, True)

    def __svnTagList(self):
        """
        Private slot used to list the tags of the project.
        """
        self.vcs.svnListTagBranch(self.project.ppath, True)

    def __svnBranchList(self):
        """
        Private slot used to list the branches of the project.
        """
        self.vcs.svnListTagBranch(self.project.ppath, False)

    def __svnExtendedDiff(self):
        """
        Private slot used to perform a svn diff with the selection of
        revisions.
        """
        self.vcs.svnExtendedDiff(self.project.ppath)

    def __svnUrlDiff(self):
        """
        Private slot used to perform a svn diff with the selection of
        repository URLs.
        """
        self.vcs.svnUrlDiff(self.project.ppath)

    def __svnRelocate(self):
        """
        Private slot used to relocate the working copy to a new repository URL.
        """
        self.vcs.svnRelocate(self.project.ppath)

    def __svnRepoBrowser(self):
        """
        Private slot to open the repository browser.
        """
        self.vcs.svnRepoBrowser(projectPath=self.project.ppath)

    def __svnConfigure(self):
        """
        Private slot to open the configuration dialog.
        """
        ericApp().getObject("UserInterface").showPreferences("zzz_subversionPage")

    def __svnChangeLists(self):
        """
        Private slot used to show a list of change lists.
        """
        self.vcs.svnShowChangelists(self.project.ppath)

    def __svnUpgrade(self):
        """
        Private slot used to upgrade the working copy format.
        """
        self.vcs.svnUpgrade(self.project.ppath)
