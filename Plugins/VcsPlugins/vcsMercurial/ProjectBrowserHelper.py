# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the VCS project browser helper for Mercurial.
"""

import os

from PyQt6.QtWidgets import QDialog, QMenu

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Project.ProjectBrowserModel import ProjectBrowserFileItem
from eric7.VCS.ProjectBrowserHelper import VcsProjectBrowserHelper


class HgProjectBrowserHelper(VcsProjectBrowserHelper):
    """
    Class implementing the VCS project browser helper for Mercurial.
    """

    def __init__(
        self,
        vcsObject,
        browserObject,
        projectObject,
        isTranslationsBrowser,
        parent=None,
        name=None,
    ):
        """
        Constructor

        @param vcsObject reference to the vcs object
        @type Hg
        @param browserObject reference to the project browser object
        @type ProjectBaseBrowser
        @param projectObject reference to the project object
        @type Project
        @param isTranslationsBrowser flag indicating, the helper is requested
            for the translations browser (this needs some special treatment)
        @type bool
        @param parent parent widget
        @type QWidget
        @param name name of this object
        @type str
        """
        from .LargefilesExtension.ProjectBrowserHelper import (
            LargefilesProjectBrowserHelper,
        )
        from .ShelveBuiltin.ProjectBrowserHelper import ShelveProjectBrowserHelper
        from .UncommitExtension.ProjectBrowserHelper import UncommitProjectBrowserHelper

        super().__init__(
            vcsObject,
            browserObject,
            projectObject,
            isTranslationsBrowser,
            parent,
            name,
        )

        # instantiate interfaces for additional built-in functions
        self.__builtins = {
            "shelve": ShelveProjectBrowserHelper(
                vcsObject, browserObject, projectObject
            ),
        }
        self.__builtinMenuTitles = {
            self.__builtins[b].menuTitle(): b for b in self.__builtins
        }
        self.__builtinMenus = {
            b: self.__builtins[b].initMenus() for b in self.__builtins
        }

        # instantiate the extensions
        self.__extensions = {
            "largefiles": LargefilesProjectBrowserHelper(
                vcsObject, browserObject, projectObject
            ),
            "uncommit": UncommitProjectBrowserHelper(
                vcsObject, browserObject, projectObject
            ),
        }
        self.__extensionMenuTitles = {
            self.__extensions[e].menuTitle(): e for e in self.__extensions
        }
        self.__extensionMenus = {
            e: self.__extensions[e].initMenus() for e in self.__extensions
        }

    def __showBuiltinsMenu(self, key, controlled):
        """
        Private slot showing the 'Other Functions' menu.

        @param key menu key (one of 'mainMenu', 'multiMenu', 'backMenu', 'dirMenu'
            or 'dirMultiMenu')
        @type str
        @param controlled flag indicating to show the menu for a
            version controlled entry or a non-version controlled entry
        @type bool
        """
        for builtinName in self.__builtinMenus:
            if key in self.__builtinMenus[builtinName]:
                # adjust individual extension menu entries
                self.__builtins[builtinName].showMenu(key, controlled)

    def __showExtensionMenu(self, key, controlled):
        """
        Private slot showing the extensions menu.

        @param key menu key (one of 'mainMenu', 'multiMenu', 'backMenu', 'dirMenu'
            or 'dirMultiMenu')
        @type str
        @param controlled flag indicating to show the menu for a
            version controlled entry or a non-version controlled entry
        @type bool
        """
        for extensionName in self.__extensionMenus:
            if key in self.__extensionMenus[extensionName]:
                self.__extensionMenus[extensionName][key].setEnabled(
                    self.vcs.isExtensionActive(extensionName)
                )
                if self.__extensionMenus[extensionName][key].isEnabled():
                    # adjust individual extension menu entries
                    self.__extensions[extensionName].showMenu(key, controlled)
                if (
                    not self.__extensionMenus[extensionName][key].isEnabled()
                    and self.__extensionMenus[extensionName][key].isTearOffMenuVisible()
                ):
                    self.__extensionMenus[extensionName][key].hideTearOffMenu()

    def showContextMenu(self, _menu, standardItems):
        """
        Public slot called before the context menu is shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the file status.

        @param _menu reference to the menu to be shown (unused)
        @type QMenu
        @param standardItems array of standard items that need
            activation/deactivation depending on the overall VCS status
        @type list of QAction
        """
        if self.browser.currentItem().data(1) == self.vcs.vcsName():
            controlled = True
            for act in self.vcsMenuActions:
                act.setEnabled(True)
            for act in self.vcsAddMenuActions:
                act.setEnabled(False)
            for act in standardItems:
                act.setEnabled(False)
            self.annotateAct.setEnabled(hasattr(self.browser.currentItem(), "fileName"))
            self.annotateSkipAct.setEnabled(
                os.path.exists(self.__skipListFileName())
                and hasattr(self.browser.currentItem(), "fileName")
            )
        else:
            controlled = False
            for act in self.vcsMenuActions:
                act.setEnabled(False)
            for act in self.vcsAddMenuActions:
                act.setEnabled(True)
            for act in standardItems:
                act.setEnabled(True)
        self.__showExtensionMenu("mainMenu", controlled)

    def showContextMenuMulti(self, _menu, standardItems):
        """
        Public slot called before the context menu (multiple selections) is
        shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the files status.

        @param _menu reference to the menu to be shown (unused)
        @type QMenu
        @param standardItems array of standard items that need
            activation/deactivation depending on the overall VCS status
        @type list of QAction
        """
        vcsName = self.vcs.vcsName()
        items = self.browser.getSelectedItems()
        vcsItems = 0
        # determine number of selected items under VCS control
        for itm in items:
            if itm.data(1) == vcsName:
                vcsItems += 1

        if vcsItems > 0:
            controlled = True
            if vcsItems != len(items):
                for act in self.vcsMultiMenuActions:
                    act.setEnabled(False)
            else:
                for act in self.vcsMultiMenuActions:
                    act.setEnabled(True)
            for act in self.vcsAddMultiMenuActions:
                act.setEnabled(False)
            for act in standardItems:
                act.setEnabled(False)
        else:
            controlled = False
            for act in self.vcsMultiMenuActions:
                act.setEnabled(False)
            for act in self.vcsAddMultiMenuActions:
                act.setEnabled(True)
            for act in standardItems:
                act.setEnabled(True)
        self.__showExtensionMenu("multiMenu", controlled)

    def showContextMenuDir(self, _menu, standardItems):
        """
        Public slot called before the context menu is shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the directory status.

        @param _menu reference to the menu to be shown (unused)
        @type QMenu
        @param standardItems array of standard items that need
            activation/deactivation depending on the overall VCS status
        @type list of QAction
        """
        if self.browser.currentItem().data(1) == self.vcs.vcsName():
            controlled = True
            for act in self.vcsDirMenuActions:
                act.setEnabled(True)
            for act in self.vcsAddDirMenuActions:
                act.setEnabled(False)
            for act in standardItems:
                act.setEnabled(False)
        else:
            controlled = False
            for act in self.vcsDirMenuActions:
                act.setEnabled(False)
            for act in self.vcsAddDirMenuActions:
                act.setEnabled(True)
            for act in standardItems:
                act.setEnabled(True)
        self.__showExtensionMenu("dirMenu", controlled)

    def showContextMenuDirMulti(self, _menu, standardItems):
        """
        Public slot called before the context menu is shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the directory status.

        @param _menu reference to the menu to be shown (unused)
        @type QMenu
        @param standardItems list of standard items that need
            activation/deactivation depending on the overall VCS status
        @type list of QAction
        """
        vcsName = self.vcs.vcsName()
        items = self.browser.getSelectedItems()
        vcsItems = 0
        # determine number of selected items under VCS control
        for itm in items:
            if itm.data(1) == vcsName:
                vcsItems += 1

        if vcsItems > 0:
            controlled = True
            if vcsItems != len(items):
                for act in self.vcsDirMultiMenuActions:
                    act.setEnabled(False)
            else:
                for act in self.vcsDirMultiMenuActions:
                    act.setEnabled(True)
            for act in self.vcsAddDirMultiMenuActions:
                act.setEnabled(False)
            for act in standardItems:
                act.setEnabled(False)
        else:
            controlled = False
            for act in self.vcsDirMultiMenuActions:
                act.setEnabled(False)
            for act in self.vcsAddDirMultiMenuActions:
                act.setEnabled(True)
            for act in standardItems:
                act.setEnabled(True)
        self.__showExtensionMenu("dirMultiMenu", controlled)

    ###########################################################################
    ## Private menu generation methods below
    ###########################################################################

    def __addBuiltinsMenu(self, menu, key):
        """
        Private method to add a 'Other Functions' menu entry.

        @param menu menu to add it to
        @type QMenu
        @param key menu key (one of 'mainMenu', 'multiMenu', 'backMenu', 'dirMenu'
            or 'dirMultiMenu')
        @type str
        @return reference to the menu action
        @rtype QAction
        """
        act = None
        if key in ["mainMenu", "multiMenu", "backMenu", "dirMenu", "dirMultiMenu"]:
            builtinsMenu = QMenu(self.tr("Other Functions"), menu)
            builtinsMenu.setTearOffEnabled(True)
            for othersMenuTitle in sorted(self.__builtinMenuTitles):
                builtinName = self.__builtinMenuTitles[othersMenuTitle]
                if key in self.__builtinMenus[builtinName]:
                    builtinsMenu.addMenu(self.__builtinMenus[builtinName][key])
            if not builtinsMenu.isEmpty():
                if not menu.isEmpty():
                    menu.addSeparator()
                act = menu.addMenu(builtinsMenu)
        return act

    def __addExtensionsMenu(self, menu, key):
        """
        Private method to add an extension menu entry.

        @param menu menu to add it to
        @type QMenu
        @param key menu key (one of 'mainMenu', 'multiMenu', 'backMenu', 'dirMenu'
            or 'dirMultiMenu')
        @type str
        @return reference to the menu action
        @rtype QAction
        """
        act = None
        if key in ["mainMenu", "multiMenu", "backMenu", "dirMenu", "dirMultiMenu"]:
            extensionsMenu = QMenu(self.tr("Extensions"), menu)
            extensionsMenu.setTearOffEnabled(True)
            for extensionMenuTitle in sorted(self.__extensionMenuTitles):
                extensionName = self.__extensionMenuTitles[extensionMenuTitle]
                if key in self.__extensionMenus[extensionName]:
                    extensionsMenu.addMenu(self.__extensionMenus[extensionName][key])
            if not extensionsMenu.isEmpty():
                if not menu.isEmpty():
                    menu.addSeparator()
                act = menu.addMenu(extensionsMenu)
        return act

    ###########################################################################
    ## Protected menu generation methods below
    ###########################################################################

    def _addVCSMenu(self, mainMenu):
        """
        Protected method used to add the VCS menu to all project browsers.

        @param mainMenu reference to the menu to be amended
        @type QMenu
        """
        self.vcsMenuActions = []
        self.vcsAddMenuActions = []

        menu = QMenu(self.tr("Version Control"))

        act = menu.addAction(
            EricPixmapCache.getIcon(
                os.path.join("VcsPlugins", "vcsMercurial", "icons", "mercurial.svg")
            ),
            self.vcs.vcsName(),
            self._VCSInfoDisplay,
        )
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("vcsCommit"),
            self.tr("Commit changes to repository..."),
            self._VCSCommit,
        )
        self.vcsMenuActions.append(act)
        self.__addBuiltinsMenu(menu, "mainMenu")
        self.__addExtensionsMenu(menu, "mainMenu")
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add to repository"),
            self._VCSAdd,
        )
        self.vcsAddMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Remove from repository (and disk)"),
            self._VCSRemove,
        )
        self.vcsMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Remove from repository only"),
            self.__HgForget,
        )
        self.vcsMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(self.tr("Copy"), self.__HgCopy)
        self.vcsMenuActions.append(act)
        act = menu.addAction(self.tr("Move"), self.__HgMove)
        self.vcsMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsLog"),
            self.tr("Show log browser"),
            self._VCSLogBrowser,
        )
        self.vcsMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsStatus"),
            self.tr("Show status"),
            self._VCSStatus,
        )
        self.vcsMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences"),
            self._VCSDiff,
        )
        self.vcsMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsSbsDiff"),
            self.tr("Show differences side-by-side"),
            self.__HgSbsDiff,
        )
        self.vcsMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences (extended)"),
            self.__HgExtendedDiff,
        )
        self.vcsMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsSbsDiff"),
            self.tr("Show differences side-by-side (extended)"),
            self.__HgSbsExtendedDiff,
        )
        self.vcsMenuActions.append(act)
        menu.addSeparator()
        self.annotateAct = menu.addAction(
            self.tr("Show annotated file"), self.__HgAnnotate
        )
        self.vcsMenuActions.append(self.annotateAct)
        self.annotateSkipAct = menu.addAction(
            self.tr("Show annotated file with skip list"), self.__HgAnnotateSkip
        )
        self.vcsMenuActions.append(self.annotateSkipAct)
        self.annotateSkipListAct = menu.addAction(
            self.tr("Create skip list file"), self.__HgAnnotateSkipListFile
        )
        self.vcsMenuActions.append(self.annotateSkipListAct)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Revert changes"),
            self.__HgRevert,
        )
        self.vcsMenuActions.append(act)
        act = menu.addAction(self.tr("Conflicts resolved"), self.__HgResolved)
        self.vcsMenuActions.append(act)
        act = menu.addAction(self.tr("Conflicts unresolved"), self.__HgUnresolved)
        self.vcsMenuActions.append(act)
        act = menu.addAction(self.tr("Re-Merge"), self.__HgReMerge)
        self.vcsMenuActions.append(act)
        menu.addSeparator()
        menu.addAction(
            self.tr("Select all local file entries"), self.browser.selectLocalEntries
        )
        menu.addAction(
            self.tr("Select all versioned file entries"), self.browser.selectVCSEntries
        )
        menu.addAction(
            self.tr("Select all local directory entries"),
            self.browser.selectLocalDirEntries,
        )
        menu.addAction(
            self.tr("Select all versioned directory entries"),
            self.browser.selectVCSDirEntries,
        )
        menu.addSeparator()
        menu.addAction(self.tr("Configure..."), self.__HgConfigure)

        mainMenu.addSeparator()
        mainMenu.addMenu(menu)
        self.menu = menu

    def _addVCSMenuMulti(self, mainMenu):
        """
        Protected method used to add the VCS menu for multi selection to all
        project browsers.

        @param mainMenu reference to the menu to be amended
        @type QMenu
        """
        self.vcsMultiMenuActions = []
        self.vcsAddMultiMenuActions = []

        menu = QMenu(self.tr("Version Control"))

        act = menu.addAction(
            EricPixmapCache.getIcon(
                os.path.join("VcsPlugins", "vcsMercurial", "icons", "mercurial.svg")
            ),
            self.vcs.vcsName(),
            self._VCSInfoDisplay,
        )
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("vcsCommit"),
            self.tr("Commit changes to repository..."),
            self._VCSCommit,
        )
        self.vcsMultiMenuActions.append(act)
        self.__addBuiltinsMenu(menu, "multiMenu")
        self.__addExtensionsMenu(menu, "multiMenu")
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add to repository"),
            self._VCSAdd,
        )
        self.vcsAddMultiMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Remove from repository (and disk)"),
            self._VCSRemove,
        )
        self.vcsMultiMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Remove from repository only"),
            self.__HgForget,
        )
        self.vcsMultiMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsStatus"),
            self.tr("Show status"),
            self._VCSStatus,
        )
        self.vcsMultiMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences"),
            self._VCSDiff,
        )
        self.vcsMultiMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences (extended)"),
            self.__HgExtendedDiff,
        )
        self.vcsMultiMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Revert changes"),
            self.__HgRevert,
        )
        self.vcsMultiMenuActions.append(act)
        act = menu.addAction(self.tr("Conflicts resolved"), self.__HgResolved)
        self.vcsMultiMenuActions.append(act)
        act = menu.addAction(self.tr("Conflicts unresolved"), self.__HgUnresolved)
        self.vcsMultiMenuActions.append(act)
        act = menu.addAction(self.tr("Re-Merge"), self.__HgReMerge)
        self.vcsMultiMenuActions.append(act)
        menu.addSeparator()
        menu.addAction(
            self.tr("Select all local file entries"), self.browser.selectLocalEntries
        )
        menu.addAction(
            self.tr("Select all versioned file entries"), self.browser.selectVCSEntries
        )
        menu.addAction(
            self.tr("Select all local directory entries"),
            self.browser.selectLocalDirEntries,
        )
        menu.addAction(
            self.tr("Select all versioned directory entries"),
            self.browser.selectVCSDirEntries,
        )
        menu.addSeparator()
        menu.addAction(self.tr("Configure..."), self.__HgConfigure)

        mainMenu.addSeparator()
        mainMenu.addMenu(menu)
        self.menuMulti = menu

    def _addVCSMenuBack(self, mainMenu):
        """
        Protected method used to add the VCS menu to all project browsers.

        @param mainMenu reference to the menu to be amended
        @type QMenu
        """
        if mainMenu is None:
            return

        menu = QMenu(self.tr("Version Control"))

        act = menu.addAction(
            EricPixmapCache.getIcon(
                os.path.join("VcsPlugins", "vcsMercurial", "icons", "mercurial.svg")
            ),
            self.vcs.vcsName(),
            self._VCSInfoDisplay,
        )
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        menu.addSeparator()

        menu.addAction(
            self.tr("Select all local file entries"), self.browser.selectLocalEntries
        )
        menu.addAction(
            self.tr("Select all versioned file entries"), self.browser.selectVCSEntries
        )
        menu.addAction(
            self.tr("Select all local directory entries"),
            self.browser.selectLocalDirEntries,
        )
        menu.addAction(
            self.tr("Select all versioned directory entries"),
            self.browser.selectVCSDirEntries,
        )
        menu.addSeparator()
        menu.addAction(self.tr("Configure..."), self.__HgConfigure)

        mainMenu.addSeparator()
        mainMenu.addMenu(menu)
        self.menuBack = menu

    def _addVCSMenuDir(self, mainMenu):
        """
        Protected method used to add the VCS menu to all project browsers.

        @param mainMenu reference to the menu to be amended
        @type QMenu
        """
        if mainMenu is None:
            return

        self.vcsDirMenuActions = []
        self.vcsAddDirMenuActions = []

        menu = QMenu(self.tr("Version Control"))

        act = menu.addAction(
            EricPixmapCache.getIcon(
                os.path.join("VcsPlugins", "vcsMercurial", "icons", "mercurial.svg")
            ),
            self.vcs.vcsName(),
            self._VCSInfoDisplay,
        )
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("vcsCommit"),
            self.tr("Commit changes to repository..."),
            self._VCSCommit,
        )
        self.vcsDirMenuActions.append(act)
        self.__addBuiltinsMenu(menu, "dirMenu")
        self.__addExtensionsMenu(menu, "dirMenu")
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add to repository"),
            self._VCSAdd,
        )
        self.vcsAddDirMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Remove from repository (and disk)"),
            self._VCSRemove,
        )
        self.vcsDirMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(self.tr("Copy"), self.__HgCopy)
        self.vcsDirMenuActions.append(act)
        act = menu.addAction(self.tr("Move"), self.__HgMove)
        self.vcsDirMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsLog"),
            self.tr("Show log browser"),
            self._VCSLogBrowser,
        )
        self.vcsDirMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsStatus"),
            self.tr("Show status"),
            self._VCSStatus,
        )
        self.vcsDirMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences"),
            self._VCSDiff,
        )
        self.vcsDirMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences (extended)"),
            self.__HgExtendedDiff,
        )
        self.vcsDirMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Revert changes"),
            self.__HgRevert,
        )
        self.vcsDirMenuActions.append(act)
        act = menu.addAction(self.tr("Conflicts resolved"), self.__HgResolved)
        self.vcsDirMenuActions.append(act)
        act = menu.addAction(self.tr("Conflicts unresolved"), self.__HgUnresolved)
        self.vcsDirMenuActions.append(act)
        act = menu.addAction(self.tr("Re-Merge"), self.__HgReMerge)
        self.vcsDirMenuActions.append(act)
        menu.addSeparator()
        menu.addAction(
            self.tr("Select all local file entries"), self.browser.selectLocalEntries
        )
        menu.addAction(
            self.tr("Select all versioned file entries"), self.browser.selectVCSEntries
        )
        menu.addAction(
            self.tr("Select all local directory entries"),
            self.browser.selectLocalDirEntries,
        )
        menu.addAction(
            self.tr("Select all versioned directory entries"),
            self.browser.selectVCSDirEntries,
        )
        menu.addSeparator()
        menu.addAction(self.tr("Configure..."), self.__HgConfigure)

        mainMenu.addSeparator()
        mainMenu.addMenu(menu)
        self.menuDir = menu

    def _addVCSMenuDirMulti(self, mainMenu):
        """
        Protected method used to add the VCS menu to all project browsers.

        @param mainMenu reference to the menu to be amended
        @type QMenu
        """
        if mainMenu is None:
            return

        self.vcsDirMultiMenuActions = []
        self.vcsAddDirMultiMenuActions = []

        menu = QMenu(self.tr("Version Control"))

        act = menu.addAction(
            EricPixmapCache.getIcon(
                os.path.join("VcsPlugins", "vcsMercurial", "icons", "mercurial.svg")
            ),
            self.vcs.vcsName(),
            self._VCSInfoDisplay,
        )
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("vcsCommit"),
            self.tr("Commit changes to repository..."),
            self._VCSCommit,
        )
        self.vcsDirMultiMenuActions.append(act)
        self.__addBuiltinsMenu(menu, "dirMultiMenu")
        self.__addExtensionsMenu(menu, "dirMultiMenu")
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add to repository"),
            self._VCSAdd,
        )
        self.vcsAddDirMultiMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Remove from repository (and disk)"),
            self._VCSRemove,
        )
        self.vcsDirMultiMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsStatus"),
            self.tr("Show status"),
            self._VCSStatus,
        )
        self.vcsDirMultiMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences"),
            self._VCSDiff,
        )
        self.vcsDirMultiMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences (extended)"),
            self.__HgExtendedDiff,
        )
        self.vcsDirMultiMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Revert changes"),
            self.__HgRevert,
        )
        self.vcsDirMultiMenuActions.append(act)
        act = menu.addAction(self.tr("Conflicts resolved"), self.__HgResolved)
        self.vcsDirMultiMenuActions.append(act)
        act = menu.addAction(self.tr("Conflicts unresolved"), self.__HgUnresolved)
        self.vcsDirMultiMenuActions.append(act)
        act = menu.addAction(self.tr("Re-Merge"), self.__HgReMerge)
        self.vcsDirMultiMenuActions.append(act)
        menu.addSeparator()
        menu.addAction(
            self.tr("Select all local file entries"), self.browser.selectLocalEntries
        )
        menu.addAction(
            self.tr("Select all versioned file entries"), self.browser.selectVCSEntries
        )
        menu.addAction(
            self.tr("Select all local directory entries"),
            self.browser.selectLocalDirEntries,
        )
        menu.addAction(
            self.tr("Select all versioned directory entries"),
            self.browser.selectVCSDirEntries,
        )
        menu.addSeparator()
        menu.addAction(self.tr("Configure..."), self.__HgConfigure)

        mainMenu.addSeparator()
        mainMenu.addMenu(menu)
        self.menuDirMulti = menu

    ###########################################################################
    ## Menu handling methods below
    ###########################################################################

    def __HgRevert(self):
        """
        Private slot called by the context menu to revert changes made.
        """
        names = []
        for itm in self.browser.getSelectedItems():
            try:
                name = itm.fileName()
            except AttributeError:
                name = itm.dirName()
            names.append(name)
        self.vcs.vcsRevert(names)

    def __HgCopy(self):
        """
        Private slot called by the context menu to copy the selected file.
        """
        itm = self.browser.currentItem()
        try:
            fn = itm.fileName()
        except AttributeError:
            fn = itm.dirName()
        self.vcs.hgCopy(fn, self.project)

    def __HgMove(self):
        """
        Private slot called by the context menu to move the selected file.
        """
        itm = self.browser.currentItem()
        try:
            fn = itm.fileName()
        except AttributeError:
            fn = itm.dirName()
        isFile = os.path.isfile(fn)
        movefiles = self.browser.project.getFiles(fn)
        self.browser.project.stopFileSystemMonitoring()
        if self.vcs.vcsMove(fn, self.project):
            if isFile:
                self.browser.closeSourceWindow.emit(fn)
            else:
                for mf in movefiles:
                    self.browser.closeSourceWindow.emit(mf)
        self.browser.project.startFileSystemMonitoring()

    def __HgExtendedDiff(self):
        """
        Private slot called by the context menu to show the difference of a
        file to the repository.

        This gives the chance to enter the revisions to compare.
        """
        names = []
        for itm in self.browser.getSelectedItems():
            try:
                names.append(itm.fileName())
            except AttributeError:
                names.append(itm.dirName())
        self.vcs.hgExtendedDiff(names)

    def __HgSbsDiff(self):
        """
        Private slot called by the context menu to show the difference of a
        file to the repository side-by-side.
        """
        itm = self.browser.currentItem()
        fn = itm.fileName()
        self.vcs.vcsSbsDiff(fn)

    def __HgSbsExtendedDiff(self):
        """
        Private slot called by the context menu to show the difference of a
        file to the repository side-by-side.

        It allows the selection of revisions to compare.
        """
        itm = self.browser.currentItem()
        fn = itm.fileName()
        self.vcs.vcsSbsDiff(fn, extended=True)

    def __HgAnnotate(self):
        """
        Private slot called by the context menu to show the annotations of a
        file.
        """
        itm = self.browser.currentItem()
        fn = itm.fileName()
        self.vcs.hgAnnotate(fn)

    def __HgAnnotateSkip(self):
        """
        Private slot called by the context menu to show the annotations of a
        file with a project specific skip list.
        """
        itm = self.browser.currentItem()
        fn = itm.fileName()
        self.vcs.hgAnnotate(fn, skiplist=self.__skipListFileName())

    def __HgAnnotateSkipListFile(self):
        """
        Private method to create an empty 'hg annotate' skip list file.
        """
        skipList = self.__skipListFileName()
        res = (
            EricMessageBox.yesNo(
                self.browser,
                self.tr("Create {0} file").format(skipList),
                self.tr(
                    """<p>The file <b>{0}</b> exists already."""
                    """ Overwrite it?</p>"""
                ).format(skipList),
                icon=EricMessageBox.Warning,
            )
            if os.path.exists(skipList)
            else True
        )
        if res:
            try:
                # create a .hgannotate_skiplist file
                with open(skipList, "w") as skip:
                    skip.write("\n")
                status = True
            except OSError:
                status = False

            if status:
                self.vcs.vcsAdd(skipList, noDialog=True)
                self.project.appendFile(skipList)

    def __skipListFileName(self):
        """
        Private method to generate the file name for a 'hg annotate' skip list file.

        @return name of the skip list file
        @rtype str
        """
        return os.path.join(self.project.getProjectPath(), ".hgannotate_skiplist")

    def __HgResolved(self):
        """
        Private slot called by the context menu to mark conflicts of a file
        as being resolved.
        """
        names = []
        for itm in self.browser.getSelectedItems():
            try:
                names.append(itm.fileName())
            except AttributeError:
                names.append(itm.dirName())
        self.vcs.vcsResolved(names)

    def __HgUnresolved(self):
        """
        Private slot called by the context menu to mark conflicts of a file
        as being unresolved.
        """
        names = []
        for itm in self.browser.getSelectedItems():
            try:
                names.append(itm.fileName())
            except AttributeError:
                names.append(itm.dirName())
        self.vcs.vcsResolved(names, unresolve=True)

    def __HgReMerge(self):
        """
        Private slot called by the context menu to re-merge a file.
        """
        names = []
        for itm in self.browser.getSelectedItems():
            try:
                names.append(itm.fileName())
            except AttributeError:
                names.append(itm.dirName())
        self.vcs.hgReMerge(names)

    def __HgForget(self):
        """
        Private slot called by the context menu to remove the selected file
        from the Mercurial repository leaving a copy in the project directory.
        """
        from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog

        if self.isTranslationsBrowser:
            items = self.browser.getSelectedItems([ProjectBrowserFileItem])
            names = [itm.fileName() for itm in items]

            dlg = DeleteFilesConfirmationDialog(
                self.parent(),
                self.tr("Remove from repository only"),
                self.tr(
                    "Do you really want to remove these files from the repository?"
                ),
                names,
            )
        else:
            items = self.browser.getSelectedItems()
            names = [itm.fileName() for itm in items]
            files = [self.browser.project.getRelativePath(name) for name in names]

            dlg = DeleteFilesConfirmationDialog(
                self.parent(),
                self.tr("Remove from repository only"),
                self.tr(
                    "Do you really want to remove these files from the repository?"
                ),
                files,
            )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.vcs.vcsForget(names)

        for fn in names:
            self._updateVCSStatus(fn)

    def __HgConfigure(self):
        """
        Private method to open the configuration dialog.
        """
        ericApp().getObject("UserInterface").showPreferences("zzz_mercurialPage")
