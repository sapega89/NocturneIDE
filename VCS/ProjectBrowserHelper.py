# -*- coding: utf-8 -*-

# Copyright (c) 2005 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the base class of the VCS project browser helper.
"""

import os

from PyQt6.QtCore import QCoreApplication, QObject
from PyQt6.QtWidgets import QDialog

from eric7 import Preferences
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Project.ProjectBrowserModel import (
    ProjectBrowserDirectoryItem,
    ProjectBrowserFileItem,
    ProjectBrowserSimpleDirectoryItem,
)
from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog


class VcsProjectBrowserHelper(QObject):
    """
    Class implementing the base class of the VCS project browser helper.
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
        @type VersionControl
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
        super().__init__(parent)
        if name:
            self.setObjectName(name)

        self.vcs = vcsObject
        self.browser = browserObject
        self.isTranslationsBrowser = isTranslationsBrowser
        self.project = projectObject

    def addVCSMenus(self, mainMenu, multiMenu, backMenu, dirMenu, dirMultiMenu):
        """
        Public method to add the VCS entries to the various project browser
        menus.

        @param mainMenu reference to the main menu
        @type QMenu
        @param multiMenu reference to the multiple selection menu
        @type QMenu
        @param backMenu reference to the background menu
        @type QMenu
        @param dirMenu reference to the directory menu
        @type QMenu
        @param dirMultiMenu reference to the multiple selection directory menu
        @type QMenu
        """
        self._addVCSMenu(mainMenu)
        self._addVCSMenuMulti(multiMenu)
        self._addVCSMenuBack(backMenu)
        self._addVCSMenuDir(dirMenu)
        self._addVCSMenuDirMulti(dirMultiMenu)

    def showContextMenu(self, menu, standardItems):
        """
        Public slot called before the context menu is shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the file status.

        @param menu reference to the menu to be shown
        @type QMenu
        @param standardItems array of standard items that need
            activation/deactivation depending on the overall VCS status
        @type list of QAction
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def showContextMenuMulti(self, menu, standardItems):
        """
        Public slot called before the context menu (multiple selections) is
        shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the files status.

        @param menu reference to the menu to be shown
        @type QMenu
        @param standardItems array of standard items that need
            activation/deactivation depending on the overall VCS status
        @type list of QAction
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def showContextMenuDir(self, menu, standardItems):
        """
        Public slot called before the context menu is shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the directory status.

        @param menu reference to the menu to be shown
        @type QMenu
        @param standardItems array of standard items that
            need activation/deactivation depending on the overall VCS status
        @type list of QAction
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    def showContextMenuDirMulti(self, menu, standardItems):
        """
        Public slot called before the context menu is shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the directory status.

        @param menu reference to the menu to be shown
        @type QMenu
        @param standardItems array of standard items that need
            activation/deactivation depending on the overall VCS status
        @type list of QAction
        @exception NotImplementedError to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("Not implemented")

    ###########################################################################
    ## General menu handling methods below
    ###########################################################################

    def _VCSUpdate(self):
        """
        Protected slot called by the context menu to update a file from the
        VCS repository.
        """
        if self.isTranslationsBrowser:
            names = [
                itm.dirName()
                for itm in self.browser.getSelectedItems(
                    [ProjectBrowserSimpleDirectoryItem]
                )
            ]
            if not names:
                names = [
                    itm.fileName()
                    for itm in self.browser.getSelectedItems([ProjectBrowserFileItem])
                ]
        else:
            names = []
            for itm in self.browser.getSelectedItems():
                try:
                    name = itm.fileName()
                except AttributeError:
                    name = itm.dirName()
                names.append(name)
        self.vcs.vcsUpdate(names)

    def _VCSCommit(self):
        """
        Protected slot called by the context menu to commit the changes to the
        VCS repository.
        """
        if self.isTranslationsBrowser:
            names = [
                itm.dirName()
                for itm in self.browser.getSelectedItems(
                    [ProjectBrowserSimpleDirectoryItem]
                )
            ]
            if not names:
                names = [
                    itm.fileName()
                    for itm in self.browser.getSelectedItems([ProjectBrowserFileItem])
                ]
        else:
            names = []
            for itm in self.browser.getSelectedItems():
                try:
                    name = itm.fileName()
                except AttributeError:
                    name = itm.dirName()
                names.append(name)
        if Preferences.getVCS("AutoSaveFiles"):
            vm = ericApp().getObject("ViewManager")
            for name in names:
                vm.saveEditor(name)
        self.vcs.vcsCommit(names, "")

    def _VCSAdd(self):
        """
        Protected slot called by the context menu to add the selected file to
        the VCS repository.
        """
        if self.isTranslationsBrowser:
            items = self.browser.getSelectedItems([ProjectBrowserSimpleDirectoryItem])
            if items:
                names = [itm.dirName() for itm in items]
                qnames = []
            else:
                items = self.browser.getSelectedItems([ProjectBrowserFileItem])
                names = []
                qnames = []
                for itm in items:
                    name = itm.fileName()
                    if name.endswith(".qm"):
                        qnames.append(name)
                    else:
                        names.append(name)
        else:
            names = []
            for itm in self.browser.getSelectedItems():
                try:
                    name = itm.fileName()
                except AttributeError:
                    name = itm.dirName()
                names.append(name)
            qnames = []

        if not len(names + qnames):
            return

        if len(names + qnames) == 1:
            if names:
                self.vcs.vcsAdd(names[0], os.path.isdir(names[0]))
            else:
                if self.vcs.canDetectBinaries:
                    self.vcs.vcsAdd(qnames)
                else:
                    self.vcs.vcsAddBinary(qnames)
        else:
            if self.vcs.canDetectBinaries:
                self.vcs.vcsAdd(names + qnames)
            else:
                self.vcs.vcsAdd(names)
                if len(qnames):
                    self.vcs.vcsAddBinary(qnames)
        for fn in names + qnames:
            self._updateVCSStatus(fn)

    def _VCSAddTree(self):
        """
        Protected slot called by the context menu.

        It is used to add the selected
        directory tree to the VCS repository.
        """
        names = []
        for itm in self.browser.getSelectedItems():
            try:
                name = itm.fileName()
            except AttributeError:
                name = itm.dirName()
            names.append(name)
        self.vcs.vcsAddTree(names)
        for fn in names:
            self._updateVCSStatus(fn)

    def _VCSRemove(self):
        """
        Protected slot called by the context menu to remove the selected file
        from the VCS repository.
        """
        if self.isTranslationsBrowser:
            items = self.browser.getSelectedItems([ProjectBrowserSimpleDirectoryItem])
            if items:
                return  # not supported

            isRemoveDirs = False
            items = self.browser.getSelectedItems([ProjectBrowserFileItem])
            names = [itm.fileName() for itm in items]

            dlg = DeleteFilesConfirmationDialog(
                self.parent(),
                QCoreApplication.translate(
                    "VcsProjectBrowserHelper", "Remove from repository (and disk)"
                ),
                QCoreApplication.translate(
                    "VcsProjectBrowserHelper",
                    "Do you really want to remove these translation files from"
                    " the repository (and disk)?",
                ),
                names,
            )
        else:
            items = self.browser.getSelectedItems()
            isRemoveDirs = len(items) == self.browser.getSelectedItemsCount(
                [ProjectBrowserSimpleDirectoryItem, ProjectBrowserDirectoryItem]
            )
            if isRemoveDirs:
                names = [itm.dirName() for itm in items]
            else:
                names = [itm.fileName() for itm in items]
            files = [self.browser.project.getRelativePath(name) for name in names]

            dlg = DeleteFilesConfirmationDialog(
                self.parent(),
                QCoreApplication.translate(
                    "VcsProjectBrowserHelper", "Remove from repository (and disk)"
                ),
                QCoreApplication.translate(
                    "VcsProjectBrowserHelper",
                    "Do you really want to remove these files/directories"
                    " from the repository (and disk)?",
                ),
                files,
            )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            status = self.vcs.vcsRemove(names)
            if status:
                if isRemoveDirs:
                    self.browser._removeDir()
                    # remove directories from Project
                else:
                    self.browser._removeFile()  # remove file(s) from project

    def _VCSLogBrowser(self):
        """
        Protected slot called by the context menu to show the log browser for a
        file.
        """
        itm = self.browser.currentItem()
        try:
            fn = itm.fileName()
            isFile = True
        except AttributeError:
            fn = itm.dirName()
            isFile = False
        self.vcs.vcsLogBrowser(fn, isFile=isFile)

    def _VCSDiff(self):
        """
        Protected slot called by the context menu to show the difference of a
        file/directory to the repository.
        """
        names = []
        for itm in self.browser.getSelectedItems():
            try:
                name = itm.fileName()
            except AttributeError:
                name = itm.dirName()
            names.append(name)
        self.vcs.vcsDiff(names)

    def _VCSStatus(self):
        """
        Protected slot called by the context menu to show the status of a file.
        """
        if self.isTranslationsBrowser:
            items = self.browser.getSelectedItems([ProjectBrowserSimpleDirectoryItem])
            if items:
                names = [itm.dirName() for itm in items]
            else:
                items = self.browser.getSelectedItems([ProjectBrowserFileItem])
                names = [itm.fileName() for itm in items]
        else:
            names = []
            for itm in self.browser.getSelectedItems():
                try:
                    name = itm.fileName()
                except AttributeError:
                    name = itm.dirName()
                names.append(name)
        self.vcs.vcsStatus(names)

    def _VCSRevert(self):
        """
        Protected slot called by the context menu to revert changes made to a
        file.
        """
        names = []
        for itm in self.browser.getSelectedItems():
            try:
                name = itm.fileName()
            except AttributeError:
                name = itm.dirName()
            names.append(name)
        self.vcs.vcsRevert(names)

    def _VCSMerge(self):
        """
        Protected slot called by the context menu to merge changes into to a
        file.
        """
        itm = self.browser.currentItem()
        try:
            name = itm.fileName()
        except AttributeError:
            name = itm.dirName()
        self.vcs.vcsMerge(name)

    def _VCSInfoDisplay(self):
        """
        Protected slot called to show some vcs information.
        """
        from .RepositoryInfoDialog import VcsRepositoryInfoDialog

        info = self.vcs.vcsRepositoryInfos(self.project.ppath)
        dlg = VcsRepositoryInfoDialog(None, info)
        dlg.exec()

    def _updateVCSStatus(self, name):
        """
        Protected method to update the VCS status of an item.

        @param name filename or directoryname of the item to be updated
        @type str
        """
        self.project.getModel().updateVCSStatus(name)
