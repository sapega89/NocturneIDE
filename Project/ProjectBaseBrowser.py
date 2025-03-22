# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the baseclass for the various project browsers.
"""

import contextlib
import os

from PyQt6.QtCore import (
    QCoreApplication,
    QElapsedTimer,
    QItemSelection,
    QItemSelectionModel,
    QModelIndex,
    Qt,
    pyqtSignal,
)
from PyQt6.QtWidgets import QAbstractItemView, QApplication, QDialog, QMenu, QTreeView

from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities
from eric7.UI.Browser import Browser
from eric7.UI.BrowserModel import (
    BrowserClassItem,
    BrowserDirectoryItem,
    BrowserFileItem,
    BrowserMethodItem,
)
from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog

from .ProjectBrowserModel import (
    ProjectBrowserDirectoryItem,
    ProjectBrowserFileItem,
    ProjectBrowserSimpleDirectoryItem,
)
from .ProjectBrowserSortFilterProxyModel import ProjectBrowserSortFilterProxyModel


class ProjectBaseBrowser(Browser):
    """
    Baseclass implementing common functionality for the various project
    browsers.

    @signal closeSourceWindow(str) emitted to close a source file
    """

    closeSourceWindow = pyqtSignal(str)

    def __init__(self, project, filterType, parent=None):
        """
        Constructor

        @param project reference to the project object
        @type Project
        @param filterType filter string for file types
        @type str
        @param parent parent widget of this browser
        @type QWidget
        """
        QTreeView.__init__(self, parent)

        self.project = project

        self._model = project.getModel()
        self._sortModel = ProjectBrowserSortFilterProxyModel(filterType)
        self._sortModel.setSourceModel(self._model)
        self.setModel(self._sortModel)

        self.selectedItemsFilter = [ProjectBrowserFileItem]

        # contains codes for special menu entries
        # 1 = specials for Others browser
        self.specialMenuEntries = []
        self.isTranslationsBrowser = False
        self.expandedNames = []

        self.SelectFlags = (
            QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows
        )
        self.DeselectFlags = (
            QItemSelectionModel.SelectionFlag.Deselect
            | QItemSelectionModel.SelectionFlag.Rows
        )

        self._activating = False

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._contextMenuRequested)
        self.activated.connect(self._openItem)
        self._model.rowsInserted.connect(self.__modelRowsInserted)
        self._connectExpandedCollapsed()

        self._initHookMethods()  # perform initialization of the hooks
        self.hooksMenuEntries = {}

        self._createPopupMenus()

        self.currentItemName = None

        self._init()  # perform common initialization tasks

        self._keyboardSearchString = ""
        self._keyboardSearchTimer = QElapsedTimer()
        self._keyboardSearchTimer.invalidate()

    def _connectExpandedCollapsed(self):
        """
        Protected method to connect the expanded and collapsed signals.
        """
        self.expanded.connect(self._resizeColumns)
        self.collapsed.connect(self._resizeColumns)

    def _disconnectExpandedCollapsed(self):
        """
        Protected method to disconnect the expanded and collapsed signals.
        """
        self.expanded.disconnect(self._resizeColumns)
        self.collapsed.disconnect(self._resizeColumns)

    def _createPopupMenus(self):
        """
        Protected overloaded method to generate the popup menus.
        """
        # create the popup menu for source files
        self.sourceMenu = QMenu(self)
        self.sourceMenu.addAction(
            QCoreApplication.translate("ProjectBaseBrowser", "Open"), self._openItem
        )

        # create the popup menu for general use
        self.menu = QMenu(self)
        self.menu.addAction(
            QCoreApplication.translate("ProjectBaseBrowser", "Open"), self._openItem
        )

        # create the menu for multiple selected files
        self.multiMenu = QMenu(self)
        self.multiMenu.addAction(
            QCoreApplication.translate("ProjectBaseBrowser", "Open"), self._openItem
        )

        # create the background menu
        self.backMenu = None

        # create the directories menu
        self.dirMenu = None

        # create the directory for multiple selected directories
        self.dirMultiMenu = None

        self.menuActions = []
        self.multiMenuActions = []
        self.dirMenuActions = []
        self.dirMultiMenuActions = []

        self.mainMenu = None

    def _contextMenuRequested(self, coord):
        """
        Protected slot to show the context menu.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        if not self.project.isOpen():
            return

        cnt = self.getSelectedItemsCount()
        if cnt > 1:
            self.multiMenu.popup(self.mapToGlobal(coord))
        else:
            index = self.indexAt(coord)

            if index.isValid():
                self.menu.popup(self.mapToGlobal(coord))
            else:
                self.backMenu and self.backMenu.popup(self.mapToGlobal(coord))

    def _selectSingleItem(self, index):
        """
        Protected method to select a single item.

        @param index index of item to be selected
        @type QModelIndex
        """
        if index.isValid():
            self.setCurrentIndex(index)
            self.selectionModel().select(
                index,
                QItemSelectionModel.SelectionFlag.ClearAndSelect
                | QItemSelectionModel.SelectionFlag.Rows,
            )

    def _setItemSelected(self, index, selected):
        """
        Protected method to set the selection status of an item.

        @param index index of item to set
        @type QModelIndex
        @param selected flag giving the new selection status
        @type bool
        """
        if index.isValid():
            self.selectionModel().select(
                index, selected and self.SelectFlags or self.DeselectFlags
            )

    def _setItemRangeSelected(self, startIndex, endIndex, selected):
        """
        Protected method to set the selection status of a range of items.

        @param startIndex start index of range of items to set
        @type QModelIndex
        @param endIndex end index of range of items to set
        @type QModelIndex
        @param selected flag giving the new selection status
        @type bool
        """
        selection = QItemSelection(startIndex, endIndex)
        self.selectionModel().select(
            selection, selected and self.SelectFlags or self.DeselectFlags
        )

    def __modelRowsInserted(self, _parent, _start, _end):
        """
        Private slot called after rows have been inserted into the model.

        @param _parent parent index of inserted rows (unused)
        @type QModelIndex
        @param _start start row number (unused)
        @type int
        @param _end end row number (unused)
        @type int
        """
        self._resizeColumns()

    def _projectClosed(self):
        """
        Protected slot to handle the projectClosed signal.
        """
        self.layoutDisplay()
        if self.backMenu is not None:
            self.backMenu.setEnabled(False)

        self._createPopupMenus()

    def _projectOpened(self):
        """
        Protected slot to handle the projectOpened signal.
        """
        self.layoutDisplay()
        self.sortByColumn(0, Qt.SortOrder.DescendingOrder)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self._initMenusAndVcs()

    def _initMenusAndVcs(self):
        """
        Protected slot to initialize the menus and the Vcs interface.
        """
        self._createPopupMenus()

        if self.backMenu is not None:
            self.backMenu.setEnabled(True)

        if self.project.vcs is not None and not FileSystemUtilities.isRemoteFileName(
            self.project.getProjectPath()
        ):
            self.vcsHelper = self.project.vcs.vcsGetProjectBrowserHelper(
                self, self.project, self.isTranslationsBrowser
            )
            self.vcsHelper.addVCSMenus(
                self.mainMenu,
                self.multiMenu,
                self.backMenu,
                self.dirMenu,
                self.dirMultiMenu,
            )
        else:
            self.vcsHelper = None

    def _newProject(self):
        """
        Protected slot to handle the newProject signal.
        """
        # default to perform same actions as opening a project
        self._projectOpened()

    def _removeFile(self):
        """
        Protected method to remove a file or files from the project.
        """
        itmList = self.getSelectedItems()

        for itm in itmList[:]:
            fn = itm.fileName()
            self.closeSourceWindow.emit(fn)
            self.project.removeFile(fn)

    def _removeDir(self):
        """
        Protected method to remove a (single) directory from the project.
        """
        itmList = self.getSelectedItems(
            [ProjectBrowserSimpleDirectoryItem, ProjectBrowserDirectoryItem]
        )
        for itm in itmList[:]:
            dn = itm.dirName()
            self.project.removeDirectory(dn)

    def _deleteDirectory(self):
        """
        Protected method to delete the selected directory from the project
        data area.
        """
        itmList = self.getSelectedItems()

        dirs = []
        fullNames = []
        for itm in itmList:
            dn = itm.dirName()
            fullNames.append(dn)
            dn = self.project.getRelativePath(dn)
            dirs.append(dn)

        dlg = DeleteFilesConfirmationDialog(
            self.parent(),
            QCoreApplication.translate("ProjectBaseBrowser", "Delete directories"),
            QCoreApplication.translate(
                "ProjectBaseBrowser",
                "Do you really want to delete these directories from the project?",
            ),
            dirs,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            for dn in fullNames:
                self.project.deleteDirectory(dn)

    def _renameFile(self):
        """
        Protected method to rename a file of the project.
        """
        itm = self.model().item(self.currentIndex())
        fn = itm.fileName()
        self.project.renameFile(fn)

    def _copyToClipboard(self):
        """
        Protected method to copy the path of an entry to the clipboard.
        """
        itm = self.model().item(self.currentIndex())
        try:
            fn = itm.fileName()
        except AttributeError:
            try:
                fn = itm.dirName()
            except AttributeError:
                fn = ""

        cb = QApplication.clipboard()
        cb.setText(fn)

    def selectFile(self, fn):
        """
        Public method to highlight a node given its filename.

        @param fn filename of file to be highlighted
        @type str
        """
        newfn = os.path.abspath(fn)
        newfn = self.project.getRelativePath(newfn)
        sindex = self._model.itemIndexByName(newfn)
        if sindex.isValid():
            index = self.model().mapFromSource(sindex)
            if index.isValid():
                self._selectSingleItem(index)
                self.scrollTo(index, QAbstractItemView.ScrollHint.PositionAtTop)

    def selectFileLine(self, fn, lineno):
        """
        Public method to highlight a node given its filename.

        @param fn filename of file to be highlighted
        @type str
        @param lineno one based line number of the item
        @type int
        """
        newfn = os.path.abspath(fn)
        newfn = self.project.getRelativePath(newfn)
        sindex = self._model.itemIndexByNameAndLine(newfn, lineno)
        if sindex.isValid():
            index = self.model().mapFromSource(sindex)
            if index.isValid():
                self._selectSingleItem(index)
                self.scrollTo(index)

    def _showProjectInFileManager(self):
        """
        Protected slot to show the path of the project in a file manager application.
        """
        if not self.project.isOpen():
            EricMessageBox.warning(
                self,
                self.tr("Show in File Manager"),
                self.tr("""A project must be opened first."""),
            )
            return

        directory = self.project.getProjectPath()
        ok = FileSystemUtilities.startfile(directory)

        if not ok:
            EricMessageBox.warning(
                self,
                self.tr("Show in File Manager"),
                self.tr(
                    "<p>The directory of the current project (<b>{0}</b>) cannot be"
                    " shown in a file manager application.</p>"
                ).format(directory),
            )

    def _expandAllDirs(self):
        """
        Protected slot to handle the 'Expand all directories' menu action.
        """
        self._disconnectExpandedCollapsed()
        with EricOverrideCursor():
            index = self.model().index(0, 0)
            while index.isValid():
                itm = self.model().item(index)
                if isinstance(
                    itm,
                    (ProjectBrowserSimpleDirectoryItem, ProjectBrowserDirectoryItem),
                ) and not self.isExpanded(index):
                    self.expand(index)
                index = self.indexBelow(index)
            self.layoutDisplay()
        self._connectExpandedCollapsed()

    def _collapseAllDirs(self):
        """
        Protected slot to handle the 'Collapse all directories' menu action.
        """
        self._disconnectExpandedCollapsed()
        with EricOverrideCursor():
            # step 1: find last valid index
            vindex = QModelIndex()
            index = self.model().index(0, 0)
            while index.isValid():
                vindex = index
                index = self.indexBelow(index)

            # step 2: go up collapsing all directory items
            index = vindex
            while index.isValid():
                itm = self.model().item(index)
                if isinstance(
                    itm,
                    (ProjectBrowserSimpleDirectoryItem, ProjectBrowserDirectoryItem),
                ) and self.isExpanded(index):
                    self.collapse(index)
                index = self.indexAbove(index)
            self.layoutDisplay()
        self._connectExpandedCollapsed()

    def _collapseAllFiles(self):
        """
        Protected slot to handle the 'Collapse all files' menu action.
        """
        self._disconnectExpandedCollapsed()
        with EricOverrideCursor():
            # step 1: find last valid index
            vindex = QModelIndex()
            index = self.model().index(0, 0)
            while index.isValid():
                vindex = index
                index = self.indexBelow(index)

            # step 2: go up collapsing all directory items
            index = vindex
            while index.isValid():
                itm = self.model().item(index)
                if isinstance(itm, ProjectBrowserFileItem) and self.isExpanded(index):
                    self.collapse(index)
                index = self.indexAbove(index)
            self.layoutDisplay()
        self._connectExpandedCollapsed()

    def _showContextMenu(self, menu):
        """
        Protected slot called before the context menu is shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the file status.

        @param menu reference to the menu to be shown
        @type QMenu
        """
        if self.project.vcs is None:
            for act in self.menuActions:
                act.setEnabled(True)
        elif self.vcsHelper is not None:
            self.vcsHelper.showContextMenu(menu, self.menuActions)

    def _showContextMenuMulti(self, menu):
        """
        Protected slot called before the context menu (multiple selections) is
        shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the files status.

        @param menu reference to the menu to be shown
        @type QMenu
        """
        if self.project.vcs is None:
            for act in self.multiMenuActions:
                act.setEnabled(True)
        elif self.vcsHelper is not None:
            self.vcsHelper.showContextMenuMulti(menu, self.multiMenuActions)

    def _showContextMenuDir(self, menu):
        """
        Protected slot called before the context menu is shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the directory status.

        @param menu reference to the menu to be shown
        @type QMenu
        """
        if self.project.vcs is None:
            for act in self.dirMenuActions:
                act.setEnabled(True)
        elif self.vcsHelper is not None:
            self.vcsHelper.showContextMenuDir(menu, self.dirMenuActions)

    def _showContextMenuDirMulti(self, menu):
        """
        Protected slot called before the context menu is shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the directory status.

        @param menu reference to the menu to be shown
        @type QMenu
        """
        if self.project.vcs is None:
            for act in self.dirMultiMenuActions:
                act.setEnabled(True)
        elif self.vcsHelper is not None:
            self.vcsHelper.showContextMenuDirMulti(menu, self.dirMultiMenuActions)

    def _showContextMenuBack(self, _menu):
        """
        Protected slot called before the context menu is shown.

        @param _menu reference to the menu to be shown (unused)
        @type QMenu
        """
        # nothing to do for now
        return

    def _selectEntries(self, local=True, filterList=None):
        """
        Protected method to select entries based on their VCS status.

        @param local flag indicating local (i.e. non VCS controlled)
            file/directory entries should be selected
        @type boolean)
        @param filterList list of classes to check against
        @type Class
        """
        if self.project.vcs is None:
            return

        compareString = (
            QCoreApplication.translate("ProjectBaseBrowser", "local")
            if local
            else self.project.vcs.vcsName()
        )

        # expand all directories in order to iterate over all entries
        self._expandAllDirs()

        self.selectionModel().clear()

        with EricOverrideCursor():
            # now iterate over all entries
            startIndex = None
            endIndex = None
            selectedEntries = 0
            index = self.model().index(0, 0)
            while index.isValid():
                itm = self.model().item(index)
                if self.wantedItem(itm, filterList) and compareString == itm.data(1):
                    if startIndex is not None and startIndex.parent() != index.parent():
                        self._setItemRangeSelected(startIndex, endIndex, True)
                        startIndex = None
                    selectedEntries += 1
                    if startIndex is None:
                        startIndex = index
                    endIndex = index
                else:
                    if startIndex is not None:
                        self._setItemRangeSelected(startIndex, endIndex, True)
                        startIndex = None
                index = self.indexBelow(index)
            if startIndex is not None:
                self._setItemRangeSelected(startIndex, endIndex, True)

        if selectedEntries == 0:
            EricMessageBox.information(
                self,
                QCoreApplication.translate("ProjectBaseBrowser", "Select entries"),
                QCoreApplication.translate(
                    "ProjectBaseBrowser", """There were no matching entries found."""
                ),
            )

    def selectLocalEntries(self):
        """
        Public slot to handle the select local files context menu entries.
        """
        self._selectEntries(local=True, filterList=[ProjectBrowserFileItem])

    def selectVCSEntries(self):
        """
        Public slot to handle the select VCS files context menu entries.
        """
        self._selectEntries(local=False, filterList=[ProjectBrowserFileItem])

    def selectLocalDirEntries(self):
        """
        Public slot to handle the select local directories context menu
        entries.
        """
        self._selectEntries(
            local=True,
            filterList=[ProjectBrowserSimpleDirectoryItem, ProjectBrowserDirectoryItem],
        )

    def selectVCSDirEntries(self):
        """
        Public slot to handle the select VCS directories context menu entries.
        """
        self._selectEntries(
            local=False,
            filterList=[ProjectBrowserSimpleDirectoryItem, ProjectBrowserDirectoryItem],
        )

    def getExpandedItemNames(self):
        """
        Public method to get the file/directory names of all expanded items.

        @return list of expanded items names
        @rtype list of str
        """
        expandedNames = []

        childIndex = self.model().index(0, 0)
        while childIndex.isValid():
            if self.isExpanded(childIndex):
                with contextlib.suppress(AttributeError):
                    expandedNames.append(self.model().item(childIndex).name())
                    # only items defining the name() method are returned
            childIndex = self.indexBelow(childIndex)

        return expandedNames

    def expandItemsByName(self, names):
        """
        Public method to expand items given their names.

        @param names list of item names to be expanded
        @type list of str
        """
        model = self.model()
        for name in names:
            childIndex = model.index(0, 0)
            while childIndex.isValid():
                with contextlib.suppress(AttributeError):
                    if model.item(childIndex).name() == name:
                        self.setExpanded(childIndex, True)
                        break
                    # ignore items not supporting this method
                childIndex = self.indexBelow(childIndex)

    def _prepareRepopulateItem(self, name):
        """
        Protected slot to handle the prepareRepopulateItem signal.

        @param name relative name of file item to be repopulated
        @type str
        """
        itm = self.currentItem()
        if itm is not None:
            self.currentItemName = itm.data(0)
        self.expandedNames = []
        sindex = self._model.itemIndexByName(name)
        if not sindex.isValid():
            return

        index = self.model().mapFromSource(sindex)
        if not index.isValid():
            return

        childIndex = self.indexBelow(index)
        while childIndex.isValid():
            if childIndex.parent() == index.parent():
                break
            if self.isExpanded(childIndex):
                self.expandedNames.append(self.model().item(childIndex).data(0))
            childIndex = self.indexBelow(childIndex)

    def _completeRepopulateItem(self, name):
        """
        Protected slot to handle the completeRepopulateItem signal.

        @param name relative name of file item to be repopulated
        @type str
        """
        sindex = self._model.itemIndexByName(name)
        if sindex.isValid():
            index = self.model().mapFromSource(sindex)
            if index.isValid():
                if self.isExpanded(index):
                    childIndex = self.indexBelow(index)
                    while childIndex.isValid():
                        if (
                            not childIndex.isValid()
                            or childIndex.parent() == index.parent()
                        ):
                            break
                        itm = self.model().item(childIndex)
                        if itm is not None:
                            itemData = itm.data(0)
                            if (
                                self.currentItemName
                                and self.currentItemName == itemData
                            ):
                                self._selectSingleItem(childIndex)
                            if itemData in self.expandedNames:
                                self.setExpanded(childIndex, True)
                        childIndex = self.indexBelow(childIndex)
                else:
                    self._selectSingleItem(index)
                self.expandedNames = []
        self.currentItemName = None
        self._resort()

    def currentItem(self):
        """
        Public method to get a reference to the current item.

        @return reference to the current item
        @rtype BrowserItem
        """
        itm = self.model().item(self.currentIndex())
        return itm

    def currentDirectory(self, relative=False):
        """
        Public method to determine the directory of the currently selected entry.

        @param relative flag indicating to return the directory as a relative path
        @type bool
        @return directory of the current entry
        @rtype str
        """
        itm = self.model().item(self.currentIndex())
        if isinstance(
            itm, (ProjectBrowserFileItem, BrowserClassItem, BrowserMethodItem)
        ):
            dn = os.path.dirname(itm.fileName())
        elif isinstance(
            itm, (ProjectBrowserSimpleDirectoryItem, ProjectBrowserDirectoryItem)
        ):
            dn = itm.dirName()
        else:
            dn = ""

        if relative:
            dn = self.project.getRelativePath(dn)

        return dn

    def _keyboardSearchType(self, item):
        """
        Protected method to check, if the item is of the correct type.

        @param item reference to the item
        @type BrowserItem
        @return flag indicating a correct type
        @rtype bool
        """
        return isinstance(
            item,
            (
                BrowserDirectoryItem,
                BrowserFileItem,
                ProjectBrowserSimpleDirectoryItem,
                ProjectBrowserDirectoryItem,
                ProjectBrowserFileItem,
            ),
        )

    ###########################################################################
    ## Support for hooks below
    ###########################################################################

    def _initHookMethods(self):
        """
        Protected method to initialize the hooks dictionary.

        This method should be overridden by subclasses. All supported
        hook methods should be initialized with a None value. The keys
        must be strings.
        """
        self.hooks = {}

    def __checkHookKey(self, key):
        """
        Private method to check a hook key.

        @param key key of the hook to check
        @type str
        @exception KeyError raised to indicate an invalid hook
        """
        if len(self.hooks) == 0:
            raise KeyError("Hooks are not initialized.")

        if key not in self.hooks:
            raise KeyError(key)

    def addHookMethod(self, key, method):
        """
        Public method to add a hook method to the dictionary.

        @param key for the hook method
        @type str
        @param method reference to the hook method
        @type function
        """
        self.__checkHookKey(key)
        self.hooks[key] = method

    def addHookMethodAndMenuEntry(self, key, method, menuEntry):
        """
        Public method to add a hook method to the dictionary.

        @param key for the hook method
        @type str
        @param method reference to the hook method
        @type function
        @param menuEntry entry to be shown in the context menu
        @type str
        """
        self.addHookMethod(key, method)
        self.hooksMenuEntries[key] = menuEntry

    def removeHookMethod(self, key):
        """
        Public method to remove a hook method from the dictionary.

        @param key for the hook method
        @type str
        """
        self.__checkHookKey(key)
        self.hooks[key] = None
        if key in self.hooksMenuEntries:
            del self.hooksMenuEntries[key]

    ##################################################################
    ## Configure method below
    ##################################################################

    def _configure(self):
        """
        Protected method to open the configuration dialog.
        """
        ericApp().getObject("UserInterface").showPreferences("projectBrowserPage")
