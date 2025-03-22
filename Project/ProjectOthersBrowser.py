# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class used to display the parts of the project, that
don't fit the other categories.
"""

import contextlib
import os

from PyQt6.QtCore import QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QMenu

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox, EricPathPickerDialog
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPickerDialog import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities
from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog
from eric7.Utilities import MimeTypes

from .FileCategoryRepositoryItem import FileCategoryRepositoryItem
from .ProjectBaseBrowser import ProjectBaseBrowser
from .ProjectBrowserModel import (
    ProjectBrowserDirectoryItem,
    ProjectBrowserFileItem,
    ProjectBrowserSimpleDirectoryItem,
)
from .ProjectBrowserRepositoryItem import ProjectBrowserRepositoryItem


class ProjectOthersBrowser(ProjectBaseBrowser):
    """
    A class used to display the parts of the project, that don't fit the
    other categories.

    @signal showMenu(str, QMenu) emitted when a menu is about to be shown.
        The name of the menu and a reference to the menu are given.
    """

    showMenu = pyqtSignal(str, QMenu)

    def __init__(self, project, projectBrowser, parent=None):
        """
        Constructor

        @param project reference to the project object
        @type Project
        @param projectBrowser reference to the project browser object
        @type ProjectBrowser
        @param parent parent widget of this browser
        @type QWidget
        """
        ProjectBaseBrowser.__init__(self, project, "other", parent)

        self.selectedItemsFilter = [ProjectBrowserFileItem, ProjectBrowserDirectoryItem]
        self.specialMenuEntries = [1]

        self.setWindowTitle(self.tr("Others"))

        self.setWhatsThis(
            self.tr(
                """<b>Project Others Browser</b>"""
                """<p>This allows to easily see all other files and directories"""
                """ contained in the current project. Several actions can be"""
                """ executed via the context menu. The entry which is registered"""
                """ in the project is shown in a different colour.</p>"""
            )
        )

        # Add the file category handled by the browser.
        project.addFileCategory(
            "OTHERS",
            FileCategoryRepositoryItem(
                fileCategoryFilterTemplate=self.tr("Other Files ({0})"),
                fileCategoryUserString=self.tr("Other Files"),
                fileCategoryTyeString=self.tr("Others"),
                fileCategoryExtensions=[],
            ),
        )

        # Add the project browser type to the browser type repository.
        projectBrowser.addTypedProjectBrowser(
            "others",
            ProjectBrowserRepositoryItem(
                projectBrowser=self,
                projectBrowserUserString=self.tr("Others Browser"),
                priority=0,
                fileCategory="OTHERS",
                fileFilter="other",
                getIcon=self.getIcon,
            ),
        )

        # Connect signals of Project.
        project.prepareRepopulateItem.connect(self._prepareRepopulateItem)
        project.completeRepopulateItem.connect(self._completeRepopulateItem)
        project.projectClosed.connect(self._projectClosed)
        project.projectOpened.connect(self._projectOpened)
        project.newProject.connect(self._newProject)
        project.reinitVCS.connect(self._initMenusAndVcs)
        project.projectPropertiesChanged.connect(self._initMenusAndVcs)

        # Connect signals of ProjectBrowser.
        projectBrowser.preferencesChanged.connect(self.handlePreferencesChanged)

        # Connect some of our own signals.
        self.closeSourceWindow.connect(projectBrowser.closeSourceWindow)
        self.sourceFile[str].connect(projectBrowser.sourceFile[str])
        self.pixmapEditFile.connect(projectBrowser.pixmapEditFile)
        self.pixmapFile.connect(projectBrowser.pixmapFile)
        self.svgFile.connect(projectBrowser.svgFile)
        self.umlFile.connect(projectBrowser.umlFile)
        self.binaryFile.connect(projectBrowser.binaryFile)
        self.pdfFile.connect(projectBrowser.pdfFile)

    def getIcon(self):
        """
        Public method to get an icon for the project browser.

        @return icon for the browser
        @rtype QIcon
        """
        return EricPixmapCache.getIcon("projectOthers")

    def _createPopupMenus(self):
        """
        Protected overloaded method to generate the popup menu.
        """
        ProjectBaseBrowser._createPopupMenus(self)

        self.menu.addAction(self.tr("Open in Hex Editor"), self._openHexEditor)
        self.editPixmapAct = self.menu.addAction(
            self.tr("Open in Icon Editor"), self._editPixmap
        )
        self.openInEditorAct = self.menu.addAction(
            self.tr("Open in Editor"), self._openFileInEditor
        )
        self.openInPdfViewerAct = self.menu.addAction(
            self.tr("Open in PDF Viewer"), self._openPdfViewer
        )
        self.menu.addSeparator()
        self.mimeTypeAct = self.menu.addAction(
            self.tr("Show Mime-Type"), self.__showMimeType
        )
        self.menu.addSeparator()
        self.renameFileAct = self.menu.addAction(
            self.tr("Rename file"), self._renameFile
        )
        self.menuActions.append(self.renameFileAct)
        act = self.menu.addAction(self.tr("Remove from project"), self.__removeItem)
        self.menuActions.append(act)
        act = self.menu.addAction(self.tr("Delete"), self.__deleteItem)
        self.menuActions.append(act)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("New file..."), self.__addNewOthersFile)
        self.menu.addAction(self.tr("New directory..."), self.__addNewOthersDirectory)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Add files..."), self.__addOthersFiles)
        self.menu.addAction(self.tr("Add directory..."), self.__addOthersDirectory)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Refresh"), self.__refreshItem)
        self.menu.addSeparator()
        self.menuFileManagerAct = self.menu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.menu.addAction(self.tr("Copy Path to Clipboard"), self._copyToClipboard)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.menu.addAction(self.tr("Collapse all directories"), self._collapseAllDirs)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Configure..."), self._configure)

        self.dirMenu = QMenu(self)
        self.removeDirAct = self.dirMenu.addAction(
            self.tr("Remove from project"), self._removeDir
        )
        self.dirMenuActions.append(self.removeDirAct)
        self.deleteDirAct = self.dirMenu.addAction(
            self.tr("Delete"), self._deleteDirectory
        )
        self.dirMenuActions.append(self.deleteDirAct)
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("New file..."), self.__addNewOthersFile)
        self.dirMenu.addAction(
            self.tr("New directory..."), self.__addNewOthersDirectory
        )
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Add files..."), self.__addOthersFiles)
        self.dirMenu.addAction(self.tr("Add directory..."), self.__addOthersDirectory)
        self.dirMenu.addSeparator()
        self.dirMenuFileManagerAct = self.dirMenu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.dirMenu.addAction(self.tr("Copy Path to Clipboard"), self._copyToClipboard)
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.dirMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Configure..."), self._configure)

        self.backMenu = QMenu(self)
        self.backMenu.addAction(
            self.tr("New file..."),
            lambda: self.__addNewOthersFile(useCurrent=False),
        )
        self.backMenu.addAction(
            self.tr("New directory..."),
            lambda: self.__addNewOthersDirectory(useCurrent=False),
        )
        self.backMenu.addSeparator()
        self.backMenu.addAction(
            self.tr("Add files..."), lambda: self.project.addFiles("OTHERS")
        )
        self.backMenu.addAction(
            self.tr("Add directory..."), lambda: self.project.addDirectory("OTHERS")
        )
        self.backMenu.addSeparator()
        self.backMenuFileManagerAct = self.backMenu.addAction(
            self.tr("Show in File Manager"), self._showProjectInFileManager
        )
        self.backMenu.addSeparator()
        self.backMenu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.backMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.backMenu.addSeparator()
        self.backMenu.addAction(self.tr("Configure..."), self._configure)
        self.backMenu.setEnabled(False)

        self.multiMenu.addSeparator()
        act = self.multiMenu.addAction(
            self.tr("Remove from project"), self.__removeItem
        )
        self.multiMenuActions.append(act)
        act = self.multiMenu.addAction(self.tr("Delete"), self.__deleteItem)
        self.multiMenuActions.append(act)
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.multiMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.tr("Configure..."), self._configure)

        self.menu.aboutToShow.connect(self.__showContextMenu)
        self.multiMenu.aboutToShow.connect(self.__showContextMenuMulti)
        self.dirMenu.aboutToShow.connect(self.__showContextMenuDir)
        self.backMenu.aboutToShow.connect(self.__showContextMenuBack)
        self.mainMenu = self.menu

    def _contextMenuRequested(self, coord):
        """
        Protected slot to show the context menu.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        if not self.project.isOpen():
            return

        isRemote = FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())

        with contextlib.suppress(Exception):  # secok
            cnt = self.getSelectedItemsCount(
                [
                    ProjectBrowserFileItem,
                    ProjectBrowserDirectoryItem,
                    ProjectBrowserSimpleDirectoryItem,
                ]
            )
            if cnt < 1:
                index = self.indexAt(coord)
                if index.isValid():
                    self._selectSingleItem(index)
                    cnt = self.getSelectedItemsCount(
                        [
                            ProjectBrowserFileItem,
                            ProjectBrowserDirectoryItem,
                            ProjectBrowserSimpleDirectoryItem,
                        ]
                    )

            if cnt > 1:
                self.multiMenu.popup(self.mapToGlobal(coord))
            else:
                index = self.indexAt(coord)
                if cnt == 1 and index.isValid():
                    itm = self.model().item(index)
                    if isinstance(itm, ProjectBrowserFileItem):
                        self.editPixmapAct.setVisible(itm.isPixmapFile())
                        self.openInEditorAct.setVisible(itm.isSvgFile())
                        self.openInPdfViewerAct.setVisible(itm.isPdfFile())
                        self.mimeTypeAct.setVisible(True)
                        self.menuFileManagerAct.setVisible(not isRemote)
                        self.menu.popup(self.mapToGlobal(coord))
                    elif isinstance(
                        itm,
                        (
                            ProjectBrowserDirectoryItem,
                            ProjectBrowserSimpleDirectoryItem,
                        ),
                    ):
                        self.removeDirAct.setVisible(True)
                        self.deleteDirAct.setVisible(True)
                        self.dirMenuFileManagerAct.setVisible(not isRemote)
                        self.dirMenu.popup(self.mapToGlobal(coord))
                    else:
                        self.backMenuFileManagerAct.setVisible(not isRemote)
                        self.backMenu.popup(self.mapToGlobal(coord))
                else:
                    self.backMenuFileManagerAct.setVisible(not isRemote)
                    self.backMenu.popup(self.mapToGlobal(coord))

    def __showContextMenu(self):
        """
        Private slot called by the menu aboutToShow signal.
        """
        self._showContextMenu(self.menu)

        self.showMenu.emit("Main", self.menu)

    def __showContextMenuMulti(self):
        """
        Private slot called by the multiMenu aboutToShow signal.
        """
        ProjectBaseBrowser._showContextMenuMulti(self, self.multiMenu)

        self.showMenu.emit("MainMulti", self.multiMenu)

    def __showContextMenuDir(self):
        """
        Private slot called by the dirMenu aboutToShow signal.
        """
        ProjectBaseBrowser._showContextMenuDir(self, self.dirMenu)

        self.showMenu.emit("MainDir", self.dirMenu)

    def __showContextMenuBack(self):
        """
        Private slot called by the backMenu aboutToShow signal.
        """
        ProjectBaseBrowser._showContextMenuBack(self, self.backMenu)

        self.showMenu.emit("MainBack", self.backMenu)

    def _showContextMenu(self, menu):
        """
        Protected slot called before the context menu is shown.

        It enables/disables the VCS menu entries depending on the overall
        VCS status and the file status.

        @param menu Reference to the popup menu
        @type QPopupMenu
        """
        if self.project.vcs is None:
            for act in self.menuActions:
                act.setEnabled(True)
            itm = self.model().item(self.currentIndex())
            if isinstance(
                itm, (ProjectBrowserSimpleDirectoryItem, ProjectBrowserDirectoryItem)
            ):
                self.renameFileAct.setEnabled(False)
        elif self.vcsHelper is not None:
            self.vcsHelper.showContextMenu(menu, self.menuActions)

    def _editPixmap(self):
        """
        Protected slot to handle the open in icon editor popup menu entry.
        """
        itmList = self.getSelectedItems()

        for itm in itmList:
            if isinstance(itm, ProjectBrowserFileItem) and itm.isPixmapFile():
                self.pixmapEditFile.emit(itm.fileName())

    def _openHexEditor(self):
        """
        Protected slot to handle the open in hex editor popup menu entry.
        """
        itmList = self.getSelectedItems()

        for itm in itmList:
            if isinstance(itm, ProjectBrowserFileItem):
                self.binaryFile.emit(itm.fileName())

    def _openPdfViewer(self):
        """
        Protected slot to handle the open in PDF viewer popup menu entry.
        """
        itmList = self.getSelectedItems()

        for itm in itmList:
            if isinstance(itm, ProjectBrowserFileItem) and itm.isPdfFile():
                self.pdfFile.emit(itm.fileName())

    def _openItem(self):
        """
        Protected slot to handle the open popup menu entry.
        """
        itmList = self.getSelectedItems()

        for itm in itmList:
            if isinstance(itm, ProjectBrowserFileItem):
                if itm.isPdfFile():
                    self.pdfFile.emit(itm.fileName())
                elif itm.isSvgFile():
                    self.svgFile.emit(itm.fileName())
                elif itm.isPixmapFile():
                    self.pixmapFile.emit(itm.fileName())
                elif itm.isEricGraphicsFile():
                    self.umlFile.emit(itm.fileName())
                else:
                    if MimeTypes.isTextFile(itm.fileName()):
                        self.sourceFile.emit(itm.fileName())
                    else:
                        QDesktopServices.openUrl(QUrl(itm.fileName()))

    def _openFileInEditor(self):
        """
        Protected slot to handle the Open in Editor menu action.
        """
        itmList = self.getSelectedItems()

        for itm in itmList:
            if isinstance(itm, ProjectBrowserFileItem) and MimeTypes.isTextFile(
                itm.fileName()
            ):
                self.sourceFile.emit(itm.fileName())

    def __showMimeType(self):
        """
        Private slot to show the mime type of the selected entry.
        """
        itmList = self.getSelectedItems()
        if itmList:
            mimetype = MimeTypes.mimeType(itmList[0].fileName())
            if mimetype is None:
                EricMessageBox.warning(
                    self,
                    self.tr("Show Mime-Type"),
                    self.tr("""The mime type of the file could not be determined."""),
                )
            elif mimetype.split("/")[0] == "text":
                EricMessageBox.information(
                    self,
                    self.tr("Show Mime-Type"),
                    self.tr("""The file has the mime type <b>{0}</b>.""").format(
                        mimetype
                    ),
                )
            else:
                textMimeTypesList = Preferences.getUI("TextMimeTypes")
                if mimetype in textMimeTypesList:
                    EricMessageBox.information(
                        self,
                        self.tr("Show Mime-Type"),
                        self.tr("""The file has the mime type <b>{0}</b>.""").format(
                            mimetype
                        ),
                    )
                else:
                    ok = EricMessageBox.yesNo(
                        self,
                        self.tr("Show Mime-Type"),
                        self.tr(
                            """The file has the mime type <b>{0}</b>."""
                            """<br/> Shall it be added to the list of"""
                            """ text mime types?"""
                        ).format(mimetype),
                    )
                    if ok:
                        textMimeTypesList.append(mimetype)
                        Preferences.setUI("TextMimeTypes", textMimeTypesList)

    def __addNewOthersDirectory(self, useCurrent=True):
        """
        Private method to add a new directory to the project.

        @param useCurrent flag indicating to use the current index for the directory
            dialog (defaults to True)
        @type bool (optional)
        """
        from .NewDirectoryDialog import NewDirectoryDialog

        isRemote = FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        dn = self.currentDirectory() if useCurrent else self.project.getProjectPath()
        dlg = NewDirectoryDialog(
            strPath=dn, defaultDirectory=dn, remote=isRemote, parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dirname, addToProject = dlg.getDirectory()
            exists = (
                remotefsInterface.exists(dirname)
                if isRemote
                else os.path.exists(dirname)
            )
            if exists:
                EricMessageBox.critical(
                    self,
                    self.tr("New directory"),
                    self.tr(
                        "<p>A file or directory named <b>{0}</b> already exists."
                        " The action will be aborted.</p>"
                    ).format(dirname),
                )
                return

            try:
                if isRemote:
                    remotefsInterface.makedirs(dirname)
                else:
                    os.makedirs(dirname)
            except OSError as err:
                EricMessageBox.critical(
                    self,
                    self.tr("New directory"),
                    self.tr(
                        "<p>The directory <b>{0}</b> could not be created."
                        " Aborting...</p><p>Reason: {1}</p>"
                    ).format(dirname, str(err)),
                )
                return

            parentDirname = (
                remotefsInterface.dirname(dirname)
                if isRemote
                else os.path.dirname(dirname)
            )

            if addToProject and not self.project.isProjectCategory(dirname, "OTHERS"):
                self.project.addToOthers(dirname)
            elif parentDirname == self.project.getProjectPath():
                dn = self.project.getRelativePath(dirname)
                self._model.addNewItem("OTHERS", dn, simple=True)
            while True:
                # recursively expand all parent items
                dirname = (
                    remotefsInterface.dirname(dirname)
                    if isRemote
                    else os.path.dirname(dirname)
                )
                dirIndex = self._sortModel.mapFromSource(
                    self._model.itemIndexByName(dirname)
                )
                if dirIndex.isValid():
                    self.expand(dirIndex)
                else:
                    break

    def __addNewOthersFile(self, useCurrent=True):
        """
        Private method to add a new source file to the project.

        @param useCurrent flag indicating to use the current index for the directory
            dialog (defaults to True)
        @type bool (optional)
        """
        isRemote = FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        dn = self.currentDirectory() if useCurrent else self.project.getProjectPath()
        filename, ok = EricPathPickerDialog.getStrPath(
            self,
            self.tr("New file"),
            self.tr("Enter the path of the new file:"),
            mode=EricPathPickerModes.SAVE_FILE_ENSURE_EXTENSION_MODE,
            strPath=dn,
            defaultDirectory=dn,
            filters=self.project.getFileCategoryFilters(
                categories=["OTHERS"], withAll=False
            ),
            remote=isRemote,
        )
        if ok:
            exists = (
                remotefsInterface.exists(filename)
                if isRemote
                else os.path.exists(filename)
            )
            if exists:
                EricMessageBox.critical(
                    self,
                    self.tr("New file"),
                    self.tr(
                        "<p>The file <b>{0}</b> already exists. The action will be"
                        " aborted.</p>"
                    ).format(filename),
                )
                return

            dirname = (
                remotefsInterface.dirname(filename)
                if isRemote
                else os.path.dirname(filename)
            )
            try:
                if isRemote:
                    remotefsInterface.makedirs(dirname, exist_ok=True)
                else:
                    os.makedirs(dirname, exist_ok=True)
                newline = (
                    None if self.project.useSystemEol() else self.project.getEolString()
                )
                if isRemote:
                    remotefsInterface.writeFile(filename, b"", newline=newline)
                else:
                    with open(filename, "w", newline=newline) as f:
                        f.write("")
            except OSError as err:
                EricMessageBox.critical(
                    self,
                    self.tr("New file"),
                    self.tr(
                        "<p>The file <b>{0}</b> could not be created. Aborting...</p>"
                        "<p>Reason: {1}</p>"
                    ).format(filename, str(err)),
                )
                return

            if not self.project.isProjectCategory(filename, "OTHERS"):
                self.project.appendFile(filename)
            while True:
                # recursively expand all parent items
                dirIndex = self._sortModel.mapFromSource(
                    self._model.itemIndexByName(dirname)
                )
                if dirIndex.isValid():
                    self.expand(dirIndex)
                    dirname = (
                        remotefsInterface.dirname(dirname)
                        if isRemote
                        else os.path.dirname(dirname)
                    )
                else:
                    break

            if MimeTypes.isTextFile(filename):
                self.sourceFile.emit(filename)

    def __addOthersFiles(self):
        """
        Private method to add files to the project.
        """
        self.project.addFiles("OTHERS", self.currentDirectory())

    def __addOthersDirectory(self):
        """
        Private method to add files of a directory to the project.
        """
        self.project.addDirectory("OTHERS", self.currentDirectory())

    def __removeItem(self):
        """
        Private slot to remove the selected entry from the OTHERS project
        data area.
        """
        itmList = self.getSelectedItems()

        for itm in itmList[:]:
            if isinstance(itm, ProjectBrowserFileItem):
                fn = itm.fileName()
                self.closeSourceWindow.emit(fn)
                self.project.removeFile(fn)
            else:
                dn = itm.dirName()
                self.project.removeDirectory(dn)

    def __deleteItem(self):
        """
        Private method to delete the selected entry from the OTHERS project
        data area.
        """
        itmList = self.getSelectedItems()

        items = []
        names = []
        fullNames = []
        dirItems = []
        dirNames = []
        dirFullNames = []
        for itm in itmList:
            if isinstance(itm, ProjectBrowserFileItem):
                fn2 = itm.fileName()
                fn = self.project.getRelativePath(fn2)
                items.append(itm)
                fullNames.append(fn2)
                names.append(fn)
            else:
                dn2 = itm.dirName()
                dn = self.project.getRelativePath(dn2)
                dirItems.append(itm)
                dirFullNames.append(dn2)
                dirNames.append(dn)
        items.extend(dirItems)
        fullNames.extend(dirFullNames)
        names.extend(dirNames)
        del itmList
        del dirFullNames
        del dirNames

        dlg = DeleteFilesConfirmationDialog(
            self.parent(),
            self.tr("Delete files/directories"),
            self.tr("Do you really want to delete these entries from the project?"),
            names,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            for itm, fn2, fn in zip(items[:], fullNames, names):
                if isinstance(itm, ProjectBrowserFileItem):
                    self.closeSourceWindow.emit(fn2)
                    self.project.deleteFile(fn)
                elif isinstance(itm, ProjectBrowserDirectoryItem):
                    self.project.deleteDirectory(fn2)

    def __refreshItem(self):
        """
        Private slot to refresh (repopulate) an item.
        """
        itm = self.model().item(self.currentIndex())
        if isinstance(itm, ProjectBrowserFileItem):
            name = itm.fileName()
            self.project.repopulateItem(name)
        elif isinstance(itm, ProjectBrowserDirectoryItem):
            name = itm.dirName()
            self._model.directoryChanged(name)
        else:
            name = ""

        self._resizeColumns()
