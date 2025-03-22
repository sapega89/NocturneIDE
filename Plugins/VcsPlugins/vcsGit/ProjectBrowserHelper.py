# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the VCS project browser helper for Git.
"""

import os

from PyQt6.QtWidgets import QDialog, QMenu

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Project.ProjectBrowserModel import ProjectBrowserFileItem
from eric7.VCS.ProjectBrowserHelper import VcsProjectBrowserHelper


class GitProjectBrowserHelper(VcsProjectBrowserHelper):
    """
    Class implementing the VCS project browser helper for Git.
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
        @type Git
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
        VcsProjectBrowserHelper.__init__(
            self,
            vcsObject,
            browserObject,
            projectObject,
            isTranslationsBrowser,
            parent,
            name,
        )

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
            for act in self.vcsMenuActions:
                act.setEnabled(True)
            for act in standardItems:
                act.setEnabled(False)
            # special conditions below
            self.annotateSkipAct.setEnabled(os.path.exists(self.__skipListFileName()))
        else:
            for act in self.vcsMenuActions:
                act.setEnabled(False)
            for act in standardItems:
                act.setEnabled(True)

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
            if vcsItems != len(items):
                for act in self.vcsMultiMenuActions:
                    act.setEnabled(False)
            else:
                for act in self.vcsMultiMenuActions:
                    act.setEnabled(True)
            for act in standardItems:
                act.setEnabled(False)
        else:
            for act in self.vcsMultiMenuActions:
                act.setEnabled(False)
            for act in standardItems:
                act.setEnabled(True)

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
            for act in self.vcsDirMenuActions:
                act.setEnabled(True)
            for act in standardItems:
                act.setEnabled(False)
        else:
            for act in self.vcsDirMenuActions:
                act.setEnabled(False)
            for act in standardItems:
                act.setEnabled(True)

    def showContextMenuDirMulti(self, _menu, standardItems):
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
        vcsName = self.vcs.vcsName()
        items = self.browser.getSelectedItems()
        vcsItems = 0
        # determine number of selected items under VCS control
        for itm in items:
            if itm.data(1) == vcsName:
                vcsItems += 1

        if vcsItems > 0:
            if vcsItems != len(items):
                for act in self.vcsDirMultiMenuActions:
                    act.setEnabled(False)
            else:
                for act in self.vcsDirMultiMenuActions:
                    act.setEnabled(True)
            for act in standardItems:
                act.setEnabled(False)
        else:
            for act in self.vcsDirMultiMenuActions:
                act.setEnabled(False)
            for act in standardItems:
                act.setEnabled(True)

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
                os.path.join("VcsPlugins", "vcsGit", "icons", "git.svg")
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
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add/Stage to repository"),
            self._VCSAdd,
        )
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Unstage changes"),
            self.__GitUnstage,
        )
        self.vcsMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Remove from repository (and disk)"),
            self._VCSRemove,
        )
        self.vcsMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Remove from repository only"),
            self.__GitForget,
        )
        self.vcsMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(self.tr("Copy"), self.__GitCopy)
        self.vcsMenuActions.append(act)
        act = menu.addAction(self.tr("Move"), self.__GitMove)
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
            self.__GitSbsDiff,
        )
        self.vcsMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsDiff"),
            self.tr("Show differences (extended)"),
            self.__GitExtendedDiff,
        )
        self.vcsMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsSbsDiff"),
            self.tr("Show differences side-by-side (extended)"),
            self.__GitSbsExtendedDiff,
        )
        self.vcsMenuActions.append(act)
        menu.addSeparator()
        self.annotateAct = menu.addAction(
            self.tr("Show annotated file"), self.__GitBlame
        )
        self.vcsMenuActions.append(self.annotateAct)
        self.annotateSkipAct = menu.addAction(
            self.tr("Show annotated file with skip list"), self.__GitBlameSkip
        )
        self.vcsMenuActions.append(self.annotateSkipAct)
        self.annotateSkipListAct = menu.addAction(
            self.tr("Create skip list file"), self.__GitBlameSkipListFile
        )
        self.vcsMenuActions.append(self.annotateSkipListAct)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Revert changes"),
            self.__GitRevert,
        )
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
        menu.addAction(self.tr("Configure..."), self.__GitConfigure)

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

        menu = QMenu(self.tr("Version Control"))

        act = menu.addAction(
            EricPixmapCache.getIcon(
                os.path.join("VcsPlugins", "vcsGit", "icons", "git.svg")
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
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add/Stage to repository"),
            self._VCSAdd,
        )
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Unstage changes"),
            self.__GitUnstage,
        )
        self.vcsMultiMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Remove from repository (and disk)"),
            self._VCSRemove,
        )
        self.vcsMultiMenuActions.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Remove from repository only"),
            self.__GitForget,
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
            self.__GitExtendedDiff,
        )
        self.vcsMultiMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Revert changes"),
            self.__GitRevert,
        )
        self.vcsMultiMenuActions.append(act)
        menu.addSeparator()

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
        menu.addAction(self.tr("Configure..."), self.__GitConfigure)

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
                os.path.join("VcsPlugins", "vcsGit", "icons", "git.svg")
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
        menu.addAction(self.tr("Configure..."), self.__GitConfigure)

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
                os.path.join("VcsPlugins", "vcsGit", "icons", "git.svg")
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
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add/Stage to repository"),
            self._VCSAdd,
        )
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Unstage changes"),
            self.__GitUnstage,
        )
        self.vcsDirMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRemove"),
            self.tr("Remove from repository (and disk)"),
            self._VCSRemove,
        )
        self.vcsDirMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(self.tr("Copy"), self.__GitCopy)
        self.vcsDirMenuActions.append(act)
        act = menu.addAction(self.tr("Move"), self.__GitMove)
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
            self.__GitExtendedDiff,
        )
        self.vcsDirMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Revert changes"),
            self.__GitRevert,
        )
        self.vcsDirMenuActions.append(act)
        menu.addSeparator()

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
        menu.addAction(self.tr("Configure..."), self.__GitConfigure)

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

        menu = QMenu(self.tr("Version Control"))

        act = menu.addAction(
            EricPixmapCache.getIcon(
                os.path.join("VcsPlugins", "vcsGit", "icons", "git.svg")
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
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add/Stage to repository"),
            self._VCSAdd,
        )
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Unstage changes"),
            self.__GitUnstage,
        )
        self.vcsDirMultiMenuActions.append(act)
        menu.addSeparator()
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
            self.__GitExtendedDiff,
        )
        self.vcsDirMultiMenuActions.append(act)
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsRevert"),
            self.tr("Revert changes"),
            self.__GitRevert,
        )
        self.vcsDirMultiMenuActions.append(act)
        menu.addSeparator()

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
        menu.addAction(self.tr("Configure..."), self.__GitConfigure)

        mainMenu.addSeparator()
        mainMenu.addMenu(menu)
        self.menuDirMulti = menu

    def __GitConfigure(self):
        """
        Private method to open the configuration dialog.
        """
        ericApp().getObject("UserInterface").showPreferences("zzz_gitPage")

    def __GitForget(self):
        """
        Private slot called by the context menu to remove the selected file
        from the Git repository leaving a copy in the project directory.
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
            self.vcs.vcsRemove(names, stageOnly=True)

        for fn in names:
            self._updateVCSStatus(fn)

    def __GitCopy(self):
        """
        Private slot called by the context menu to copy the selected file.
        """
        itm = self.browser.currentItem()
        try:
            fn = itm.fileName()
        except AttributeError:
            fn = itm.dirName()
        self.vcs.gitCopy(fn, self.project)

    def __GitMove(self):
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

    def __GitExtendedDiff(self):
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
        self.vcs.gitExtendedDiff(names)

    def __GitSbsDiff(self):
        """
        Private slot called by the context menu to show the difference of a
        file to the repository side-by-side.
        """
        itm = self.browser.currentItem()
        fn = itm.fileName()
        self.vcs.vcsSbsDiff(fn)

    def __GitSbsExtendedDiff(self):
        """
        Private slot called by the context menu to show the difference of a
        file to the repository side-by-side.

        It allows the selection of revisions to compare.
        """
        itm = self.browser.currentItem()
        fn = itm.fileName()
        self.vcs.vcsSbsDiff(fn, extended=True)

    def __GitUnstage(self):
        """
        Private slot to unstage changes.
        """
        names = []
        for itm in self.browser.getSelectedItems():
            try:
                name = itm.fileName()
            except AttributeError:
                name = itm.dirName()
            names.append(name)
        self.vcs.gitUnstage(names)

    def __GitRevert(self):
        """
        Private slot to revert changes of the working area.
        """
        names = []
        for itm in self.browser.getSelectedItems():
            try:
                name = itm.fileName()
            except AttributeError:
                name = itm.dirName()
            names.append(name)
        self.vcs.vcsRevert(names)

    def __GitBlame(self):
        """
        Private slot called by the context menu to show the annotations of a
        file.
        """
        itm = self.browser.currentItem()
        fn = itm.fileName()
        self.vcs.gitBlame(fn)

    def __GitBlameSkip(self):
        """
        Private slot called by the context menu to show the annotations of a
        file with a project specific skip list.
        """
        itm = self.browser.currentItem()
        fn = itm.fileName()
        self.vcs.gitBlame(fn, skiplist=self.__skipListFileName())

    def __GitBlameSkipListFile(self):
        """
        Private method to create an empty 'git blame' skip list file.
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
                # create a .gitblame_skiplist file
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
        Private method to generate the file name for a 'git blame' skip list file.

        @return name of the skip list file
        @rtype str
        """
        return os.path.join(self.project.getProjectPath(), ".gitblame_skiplist")
