# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class used to display the forms part of the project.
"""

import contextlib
import os
import pathlib
import shutil
import sys

from PyQt6.QtCore import QProcess, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QDialog, QInputDialog, QMenu

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricProgressDialog import EricProgressDialog
from eric7.Globals import getConfig
from eric7.SystemUtilities import FileSystemUtilities, QtUtilities
from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog
from eric7.UI.NotificationWidget import NotificationTypes

from .FileCategoryRepositoryItem import FileCategoryRepositoryItem
from .ProjectBaseBrowser import ProjectBaseBrowser
from .ProjectBrowserModel import (
    ProjectBrowserFileItem,
    ProjectBrowserSimpleDirectoryItem,
)
from .ProjectBrowserRepositoryItem import ProjectBrowserRepositoryItem


class ProjectFormsBrowser(ProjectBaseBrowser):
    """
    A class used to display the forms part of the project.

    @signal appendStderr(str) emitted after something was received from
        a QProcess on stderr
    @signal uipreview(str) emitted to preview a forms file
    @signal showMenu(str, QMenu) emitted when a menu is about to be shown. The
        name of the menu and a reference to the menu are given.
    @signal menusAboutToBeCreated() emitted when the context menus are about to
        be created. This is the right moment to add or remove hook methods.
    """

    appendStderr = pyqtSignal(str)
    uipreview = pyqtSignal(str)
    showMenu = pyqtSignal(str, QMenu)
    menusAboutToBeCreated = pyqtSignal()

    Pyuic5IndentDefault = 4
    Pyuic6IndentDefault = 4

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
        ProjectBaseBrowser.__init__(self, project, "form", parent)

        self.selectedItemsFilter = [
            ProjectBrowserFileItem,
            ProjectBrowserSimpleDirectoryItem,
        ]

        self.setWindowTitle(self.tr("Forms"))

        self.setWhatsThis(
            self.tr(
                """<b>Project Forms Browser</b>"""
                """<p>This allows to easily see all forms contained in the"""
                """ current project. Several actions can be executed via the"""
                """ context menu.</p>"""
            )
        )

        # templates for Qt
        # these two lists have to stay in sync
        self.templates4 = [
            "dialog4.tmpl",
            "widget4.tmpl",
            "mainwindow4.tmpl",
            "dialogbuttonboxbottom4.tmpl",
            "dialogbuttonboxright4.tmpl",
            "dialogbuttonsbottom4.tmpl",
            "dialogbuttonsbottomcenter4.tmpl",
            "dialogbuttonsright4.tmpl",
            "",
            "wizard4.tmpl",
            "wizardpage4.tmpl",
            "qdockwidget4.tmpl",
            "qframe4.tmpl",
            "qgroupbox4.tmpl",
            "qscrollarea4.tmpl",
            "qmdiarea4.tmpl",
            "qtabwidget4.tmpl",
            "qtoolbox4.tmpl",
            "qstackedwidget4.tmpl",
        ]
        self.templateTypes4 = [
            self.tr("Dialog"),
            self.tr("Widget"),
            self.tr("Main Window"),
            self.tr("Dialog with Buttonbox (Bottom)"),
            self.tr("Dialog with Buttonbox (Right)"),
            self.tr("Dialog with Buttons (Bottom)"),
            self.tr("Dialog with Buttons (Bottom-Center)"),
            self.tr("Dialog with Buttons (Right)"),
            "",
            self.tr("QWizard"),
            self.tr("QWizardPage"),
            self.tr("QDockWidget"),
            self.tr("QFrame"),
            self.tr("QGroupBox"),
            self.tr("QScrollArea"),
            self.tr("QMdiArea"),
            self.tr("QTabWidget"),
            self.tr("QToolBox"),
            self.tr("QStackedWidget"),
        ]

        self.compileProc = None
        self.__uicompiler = ""

        # Add the file category handled by the browser.
        project.addFileCategory(
            "FORMS",
            FileCategoryRepositoryItem(
                fileCategoryFilterTemplate=self.tr("Form Files ({0})"),
                fileCategoryUserString=self.tr("Form Files"),
                fileCategoryTyeString=self.tr("Forms"),
                fileCategoryExtensions=["*.ui"],
            ),
        )

        # Add the project browser type to the browser type repository.
        projectBrowser.addTypedProjectBrowser(
            "forms",
            ProjectBrowserRepositoryItem(
                projectBrowser=self,
                projectBrowserUserString=self.tr("Forms Browser"),
                priority=75,
                fileCategory="FORMS",
                fileFilter="form",
                getIcon=self.getIcon,
            ),
        )

        # Connect signals of Project.
        project.projectClosed.connect(self.__resetUiCompiler)
        project.projectPropertiesChanged.connect(self.__resetUiCompiler)
        project.projectClosed.connect(self._projectClosed)
        project.projectOpened.connect(self._projectOpened)
        project.newProject.connect(self._newProject)
        project.reinitVCS.connect(self._initMenusAndVcs)
        project.projectPropertiesChanged.connect(self._initMenusAndVcs)

        # Connect signals of ProjectBrowser.
        projectBrowser.preferencesChanged.connect(self.handlePreferencesChanged)
        projectBrowser.processChangedProjectFiles.connect(self.__compileChangedForms)

        # Connect some of our own signals.
        self.appendStderr.connect(projectBrowser.appendStderr)
        self.closeSourceWindow.connect(projectBrowser.closeSourceWindow)
        self.sourceFile[str].connect(projectBrowser.sourceFile[str])
        self.designerFile.connect(projectBrowser.designerFile)
        self.uipreview.connect(projectBrowser.uipreview)
        self.trpreview[list].connect(projectBrowser.trpreview[list])

    def getIcon(self):
        """
        Public method to get an icon for the project browser.

        @return icon for the browser
        @rtype QIcon
        """
        return EricPixmapCache.getIcon("projectForms")

    def _createPopupMenus(self):
        """
        Protected overloaded method to generate the popup menu.
        """
        self.menuActions = []
        self.multiMenuActions = []
        self.dirMenuActions = []
        self.dirMultiMenuActions = []

        self.menusAboutToBeCreated.emit()

        projectType = self.project.getProjectType()

        self.menu = QMenu(self)
        if projectType in ["PyQt5", "PyQt6", "E7Plugin", "PySide2", "PySide6"]:
            if FileSystemUtilities.isRemoteFileName(self.project.getProjectPath()):
                self.menu.addAction(self.tr("Open in Editor"), self.__openFileInEditor)
            else:
                self.menu.addAction(self.tr("Compile form"), self.__compileForm)
                self.menu.addAction(
                    self.tr("Compile all forms"), self.__compileAllForms
                )
                self.menu.addAction(
                    self.tr("Generate Dialog Code..."), self.__generateDialogCode
                )
                self.menu.addSeparator()
                self.__pyuicConfigAct = self.menu.addAction(
                    self.tr("Configure uic Compiler"), self.__configureUicCompiler
                )
                self.menu.addSeparator()
                self.menu.addAction(
                    self.tr("Open in Qt-Designer"), self.__openFile
                ).setEnabled(QtUtilities.hasQtDesigner())
                self.menu.addAction(self.tr("Open in Editor"), self.__openFileInEditor)
                self.menu.addSeparator()
                self.menu.addAction(self.tr("Preview form"), self.__UIPreview)
                self.menu.addAction(self.tr("Preview translations"), self.__TRPreview)
        else:
            if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
                if self.hooks["compileForm"] is not None:
                    self.menu.addAction(
                        self.hooksMenuEntries.get(
                            "compileForm", self.tr("Compile form")
                        ),
                        self.__compileForm,
                    )
                if self.hooks["compileAllForms"] is not None:
                    self.menu.addAction(
                        self.hooksMenuEntries.get(
                            "compileAllForms", self.tr("Compile all forms")
                        ),
                        self.__compileAllForms,
                    )
                if self.hooks["generateDialogCode"] is not None:
                    self.menu.addAction(
                        self.hooksMenuEntries.get(
                            "generateDialogCode", self.tr("Generate Dialog Code...")
                        ),
                        self.__generateDialogCode,
                    )
                if (
                    self.hooks["compileForm"] is not None
                    or self.hooks["compileAllForms"] is not None
                    or self.hooks["generateDialogCode"] is not None
                ):
                    self.menu.addSeparator()
            if self.hooks["open"] is not None:
                self.menu.addAction(
                    self.hooksMenuEntries.get("open", self.tr("Open")), self.__openFile
                )
            self.menu.addAction(self.tr("Open"), self.__openFileInEditor)
        self.menu.addSeparator()
        act = self.menu.addAction(self.tr("Rename file"), self._renameFile)
        self.menuActions.append(act)
        act = self.menu.addAction(self.tr("Remove from project"), self._removeFile)
        self.menuActions.append(act)
        act = self.menu.addAction(self.tr("Delete"), self.__deleteFile)
        self.menuActions.append(act)
        self.menu.addSeparator()
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            if projectType in ["PyQt5", "PyQt6", "E7Plugin", "PySide2", "PySide6"]:
                self.menu.addAction(self.tr("New form..."), self.__newForm)
            else:
                if self.hooks["newForm"] is not None:
                    self.menu.addAction(
                        self.hooksMenuEntries.get("newForm", self.tr("New form...")),
                        self.__newForm,
                    )
        self.menu.addAction(self.tr("Add forms..."), self.__addFormFiles)
        self.menu.addAction(self.tr("Add forms directory..."), self.__addFormsDirectory)
        self.menu.addSeparator()
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            self.menu.addAction(
                self.tr("Show in File Manager"), self._showInFileManager
            )
        self.menu.addAction(self.tr("Copy Path to Clipboard"), self._copyToClipboard)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.menu.addAction(self.tr("Collapse all directories"), self._collapseAllDirs)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Configure..."), self._configure)

        self.backMenu = QMenu(self)
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            if (
                projectType in ["PyQt5", "PyQt6", "E7Plugin", "PySide2", "PySide6"]
                or self.hooks["compileAllForms"] is not None
            ):
                self.backMenu.addAction(
                    self.tr("Compile all forms"), self.__compileAllForms
                )
                self.backMenu.addSeparator()
                self.__pyuicBackConfigAct = self.backMenu.addAction(
                    self.tr("Configure uic Compiler"), self.__configureUicCompiler
                )
                self.backMenu.addSeparator()
                self.backMenu.addAction(self.tr("New form..."), self.__newForm)
            else:
                if self.hooks["newForm"] is not None:
                    self.backMenu.addAction(
                        self.hooksMenuEntries.get("newForm", self.tr("New form...")),
                        self.__newForm,
                    )
            self.backMenu.addAction(
                self.tr("Add forms..."), lambda: self.project.addFiles("FORMS")
            )
            self.backMenu.addAction(
                self.tr("Add forms directory..."),
                lambda: self.project.addDirectory("FORMS"),
            )
            self.backMenu.addSeparator()
            self.backMenu.addAction(
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

        # create the menu for multiple selected files
        self.multiMenu = QMenu(self)
        if projectType in ["PyQt5", "PyQt6", "E7Plugin", "PySide2", "PySide6"]:
            if FileSystemUtilities.isRemoteFileName(self.project.getProjectPath()):
                self.multiMenu.addAction(
                    self.tr("Open in Editor"), self.__openFileInEditor
                )
            else:
                self.multiMenu.addAction(
                    self.tr("Compile forms"), self.__compileSelectedForms
                )
                self.multiMenu.addSeparator()
                self.__pyuicMultiConfigAct = self.multiMenu.addAction(
                    self.tr("Configure uic Compiler"), self.__configureUicCompiler
                )
                self.multiMenu.addSeparator()
                self.multiMenu.addAction(
                    self.tr("Open in Qt-Designer"), self.__openFile
                ).setEnabled(QtUtilities.hasQtDesigner())
                self.multiMenu.addAction(
                    self.tr("Open in Editor"), self.__openFileInEditor
                )
                self.multiMenu.addSeparator()
                self.multiMenu.addAction(
                    self.tr("Preview translations"), self.__TRPreview
                )
        else:
            if (
                FileSystemUtilities.isPlainFileName(self.project.getProjectPath())
                and self.hooks["compileSelectedForms"] is not None
            ):
                act = self.multiMenu.addAction(
                    self.hooksMenuEntries.get(
                        "compileSelectedForms", self.tr("Compile forms")
                    ),
                    self.__compileSelectedForms,
                )
                self.multiMenu.addSeparator()
            if self.hooks["open"] is not None:
                self.multiMenu.addAction(
                    self.hooksMenuEntries.get("open", self.tr("Open")), self.__openFile
                )
            self.multiMenu.addAction(self.tr("Open"), self.__openFileInEditor)
        self.multiMenu.addSeparator()
        act = self.multiMenu.addAction(self.tr("Remove from project"), self._removeFile)
        self.multiMenuActions.append(act)
        act = self.multiMenu.addAction(self.tr("Delete"), self.__deleteFile)
        self.multiMenuActions.append(act)
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.multiMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.tr("Configure..."), self._configure)

        self.dirMenu = QMenu(self)
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            if projectType in ["PyQt5", "PyQt6", "E7Plugin", "PySide2", "PySide6"]:
                self.dirMenu.addAction(
                    self.tr("Compile all forms"), self.__compileAllForms
                )
                self.dirMenu.addSeparator()
                self.__pyuicDirConfigAct = self.dirMenu.addAction(
                    self.tr("Configure uic Compiler"), self.__configureUicCompiler
                )
                self.dirMenu.addSeparator()
            else:
                if self.hooks["compileAllForms"] is not None:
                    self.dirMenu.addAction(
                        self.hooksMenuEntries.get(
                            "compileAllForms", self.tr("Compile all forms")
                        ),
                        self.__compileAllForms,
                    )
                    self.dirMenu.addSeparator()
        act = self.dirMenu.addAction(self.tr("Remove from project"), self._removeDir)
        self.dirMenuActions.append(act)
        act = self.dirMenu.addAction(self.tr("Delete"), self._deleteDirectory)
        self.dirMenuActions.append(act)
        self.dirMenu.addSeparator()
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            if projectType in ["PyQt5", "PyQt6", "E7Plugin", "PySide2", "PySide6"]:
                self.dirMenu.addAction(self.tr("New form..."), self.__newForm)
            else:
                if self.hooks["newForm"] is not None:
                    self.dirMenu.addAction(
                        self.hooksMenuEntries.get("newForm", self.tr("New form...")),
                        self.__newForm,
                    )
            self.dirMenu.addAction(self.tr("Add forms..."), self.__addFormFiles)
            self.dirMenu.addAction(
                self.tr("Add forms directory..."), self.__addFormsDirectory
            )
            self.dirMenu.addSeparator()
            self.dirMenu.addAction(
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

        self.dirMultiMenu = QMenu(self)
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            if projectType in ["PyQt5", "PyQt6", "E7Plugin", "PySide2", "PySide6"]:
                self.dirMultiMenu.addAction(
                    self.tr("Compile all forms"), self.__compileAllForms
                )
                self.dirMultiMenu.addSeparator()
                self.__pyuicDirMultiConfigAct = self.dirMultiMenu.addAction(
                    self.tr("Configure uic Compiler"), self.__configureUicCompiler
                )
                self.dirMultiMenu.addSeparator()
            else:
                if self.hooks["compileAllForms"] is not None:
                    self.dirMultiMenu.addAction(
                        self.hooksMenuEntries.get(
                            "compileAllForms", self.tr("Compile all forms")
                        ),
                        self.__compileAllForms,
                    )
                    self.dirMultiMenu.addSeparator()
            self.dirMultiMenu.addAction(
                self.tr("Add forms..."), lambda: self.project.addFiles("FORMS")
            )
            self.dirMultiMenu.addAction(
                self.tr("Add forms directory..."),
                lambda: self.project.addDirectory("FORMS"),
            )
            self.dirMultiMenu.addSeparator()
        self.dirMultiMenu.addAction(
            self.tr("Expand all directories"), self._expandAllDirs
        )
        self.dirMultiMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.dirMultiMenu.addSeparator()
        self.dirMultiMenu.addAction(self.tr("Configure..."), self._configure)

        self.menu.aboutToShow.connect(self.__showContextMenu)
        self.multiMenu.aboutToShow.connect(self.__showContextMenuMulti)
        self.dirMenu.aboutToShow.connect(self.__showContextMenuDir)
        self.dirMultiMenu.aboutToShow.connect(self.__showContextMenuDirMulti)
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

        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            enable = self.project.getProjectType() in ("PyQt5", "PyQt6", "E7Plugin")
            self.__pyuicConfigAct.setEnabled(enable)
            self.__pyuicMultiConfigAct.setEnabled(enable)
            self.__pyuicDirConfigAct.setEnabled(enable)
            self.__pyuicDirMultiConfigAct.setEnabled(enable)
            self.__pyuicBackConfigAct.setEnabled(enable)

        with contextlib.suppress(Exception):  # secok
            categories = self.getSelectedItemsCountCategorized(
                [ProjectBrowserFileItem, ProjectBrowserSimpleDirectoryItem]
            )
            cnt = categories["sum"]
            if cnt <= 1:
                index = self.indexAt(coord)
                if index.isValid():
                    self._selectSingleItem(index)
                    categories = self.getSelectedItemsCountCategorized(
                        [ProjectBrowserFileItem, ProjectBrowserSimpleDirectoryItem]
                    )
                    cnt = categories["sum"]

            bfcnt = categories[str(ProjectBrowserFileItem)]
            sdcnt = categories[str(ProjectBrowserSimpleDirectoryItem)]
            if cnt > 1 and cnt == bfcnt:
                self.multiMenu.popup(self.mapToGlobal(coord))
            elif cnt > 1 and cnt == sdcnt:
                self.dirMultiMenu.popup(self.mapToGlobal(coord))
            else:
                index = self.indexAt(coord)
                if cnt == 1 and index.isValid():
                    if bfcnt == 1:
                        self.menu.popup(self.mapToGlobal(coord))
                    elif sdcnt == 1:
                        self.dirMenu.popup(self.mapToGlobal(coord))
                    else:
                        self.backMenu.popup(self.mapToGlobal(coord))
                else:
                    self.backMenu.popup(self.mapToGlobal(coord))

    def __showContextMenu(self):
        """
        Private slot called by the menu aboutToShow signal.
        """
        ProjectBaseBrowser._showContextMenu(self, self.menu)

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

    def __showContextMenuDirMulti(self):
        """
        Private slot called by the dirMultiMenu aboutToShow signal.
        """
        ProjectBaseBrowser._showContextMenuDirMulti(self, self.dirMultiMenu)

        self.showMenu.emit("MainDirMulti", self.dirMultiMenu)

    def __showContextMenuBack(self):
        """
        Private slot called by the backMenu aboutToShow signal.
        """
        ProjectBaseBrowser._showContextMenuBack(self, self.backMenu)

        self.showMenu.emit("MainBack", self.backMenu)

    def __addFormFiles(self):
        """
        Private method to add form files to the project.
        """
        self.project.addFiles("FORMS", self.currentDirectory())

    def __addFormsDirectory(self):
        """
        Private method to add form files of a directory to the project.
        """
        self.project.addDirectory("FORMS", self.currentDirectory())

    def __openFile(self):
        """
        Private slot to handle the Open menu action.
        """
        itmList = self.getSelectedItems()
        for itm in itmList[:]:
            with contextlib.suppress(Exception):  # secok
                if isinstance(itm, ProjectBrowserFileItem):
                    # hook support
                    if self.hooks["open"] is not None:
                        self.hooks["open"](itm.fileName())
                    else:
                        self.designerFile.emit(itm.fileName())

    def __openFileInEditor(self):
        """
        Private slot to handle the Open in Editor menu action.
        """
        itmList = self.getSelectedItems()
        for itm in itmList[:]:
            self.sourceFile.emit(itm.fileName())

    def _openItem(self):
        """
        Protected slot to handle the open popup menu entry.
        """
        itmList = self.getSelectedItems()
        for itm in itmList:
            if isinstance(itm, ProjectBrowserFileItem):
                if itm.isDesignerFile() and FileSystemUtilities.isPlainFileName(
                    itm.fileName()
                ):
                    self.designerFile.emit(itm.fileName())
                else:
                    self.sourceFile.emit(itm.fileName())

    def __UIPreview(self):
        """
        Private slot to handle the Preview menu action.
        """
        itmList = self.getSelectedItems()
        self.uipreview.emit(itmList[0].fileName())

    def __TRPreview(self):
        """
        Private slot to handle the Preview translations action.
        """
        fileNames = []
        for itm in self.getSelectedItems():
            fileNames.append(itm.fileName())
        trfiles = sorted(self.project.getProjectData(dataKey="TRANSLATIONS")[:])
        fileNames.extend(
            [
                os.path.join(self.project.ppath, trfile)
                for trfile in trfiles
                if trfile.endswith(".qm")
            ]
        )
        self.trpreview[list].emit(fileNames)

    def __newForm(self):
        """
        Private slot to handle the New Form menu action.
        """
        itm = self.model().item(self.currentIndex())
        if itm is None:
            path = self.project.ppath
        else:
            try:
                path = os.path.dirname(itm.fileName())
            except AttributeError:
                try:
                    path = itm.dirName()
                except AttributeError:
                    path = os.path.join(self.project.ppath, itm.data(0))

        if self.hooks["newForm"] is not None:
            self.hooks["newForm"](path)
        else:
            if self.project.getProjectType() in [
                "PyQt5",
                "PyQt6",
                "E7Plugin",
                "PySide2",
                "PySide6",
            ]:
                self.__newUiForm(path)

    def __newUiForm(self, path):
        """
        Private slot to handle the New Form menu action for Qt-related
        projects.

        @param path full directory path for the new form file
        @type str
        """
        selectedForm, ok = QInputDialog.getItem(
            None,
            self.tr("New Form"),
            self.tr("Select a form type:"),
            self.templateTypes4,
            0,
            False,
        )
        if not ok or not selectedForm:
            # user pressed cancel
            return

        templateIndex = self.templateTypes4.index(selectedForm)
        templateFile = os.path.join(
            getConfig("ericTemplatesDir"), self.templates4[templateIndex]
        )

        fname, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.tr("New Form"),
            path,
            self.tr("Qt User-Interface Files (*.ui);;All Files (*)"),
            "",
            EricFileDialog.DontConfirmOverwrite,
        )

        if not fname:
            # user aborted or didn't enter a filename
            return

        fpath = pathlib.Path(fname)
        if not fpath.suffix:
            ex = selectedFilter.split("(*")[1].split(")")[0]
            if ex:
                fpath = fpath.with_suffix(ex)
        if fpath.exists():
            res = EricMessageBox.yesNo(
                self,
                self.tr("New Form"),
                self.tr("The file already exists! Overwrite it?"),
                icon=EricMessageBox.Warning,
            )
            if not res:
                # user selected to not overwrite
                return

        try:
            shutil.copy(templateFile, fpath)
        except OSError as err:
            EricMessageBox.critical(
                self,
                self.tr("New Form"),
                self.tr(
                    "<p>The new form file <b>{0}</b> could not be created.<br>"
                    "Problem: {1}</p>"
                ).format(fpath, str(err)),
            )
            return

        self.project.appendFile(str(fpath))
        self.designerFile.emit(str(fpath))

    def __deleteFile(self):
        """
        Private method to delete a form file from the project.
        """
        itmList = self.getSelectedItems()

        files = []
        fullNames = []
        for itm in itmList:
            fn2 = itm.fileName()
            fullNames.append(fn2)
            fn = self.project.getRelativePath(fn2)
            files.append(fn)

        dlg = DeleteFilesConfirmationDialog(
            self.parent(),
            self.tr("Delete forms"),
            self.tr("Do you really want to delete these forms from the project?"),
            files,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            for fn2, fn in zip(fullNames, files):
                self.closeSourceWindow.emit(fn2)
                self.project.deleteFile(fn)

    ###########################################################################
    ##  Methods to handle the various compile commands
    ###########################################################################

    def __resetUiCompiler(self):
        """
        Private slot to reset the determined UI compiler executable.
        """
        self.__uicompiler = ""

    def __determineUiCompiler(self):
        """
        Private method to determine the UI compiler for the project.
        """
        self.__resetUiCompiler()

        if self.project.getProjectLanguage() == "Python3":
            if self.project.getProjectType() in ["PyQt5"]:
                self.__uicompiler = QtUtilities.generatePyQtToolPath(
                    "pyuic5", ["py3uic5"]
                )
            elif self.project.getProjectType() in ["PyQt6", "E7Plugin"]:
                self.__uicompiler = QtUtilities.generatePyQtToolPath("pyuic6")
            elif self.project.getProjectType() == "PySide2":
                self.__uicompiler = QtUtilities.generatePySideToolPath(
                    "pyside2-uic", variant=2
                )
            elif self.project.getProjectType() == "PySide6":
                self.__uicompiler = QtUtilities.generatePySideToolPath(
                    "pyside6-uic", variant=6
                )

    def getUiCompiler(self):
        """
        Public method to get the UI compiler executable of the project.

        @return UI compiler executable
        @rtype str
        """
        if not self.__uicompiler:
            self.__determineUiCompiler()

        return self.__uicompiler

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal of the
        pyuic5/pyuic6/pyside2-uic/pyside6-uic process.
        """
        if self.compileProc is None:
            return
        self.compileProc.setReadChannel(QProcess.ProcessChannel.StandardOutput)

        while self.compileProc and self.compileProc.canReadLine():
            self.__buf.append(
                str(self.compileProc.readLine(), "utf-8", "replace").rstrip()
            )

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal of the
        pyuic5/pyuic6/pyside2-uic/pyside6-uic process.
        """
        if self.compileProc is None:
            return

        ioEncoding = Preferences.getSystem("IOEncoding")

        self.compileProc.setReadChannel(QProcess.ProcessChannel.StandardError)
        while self.compileProc and self.compileProc.canReadLine():
            s = self.__uicompiler + ": "
            error = str(self.compileProc.readLine(), ioEncoding, "replace")
            s += error
            self.appendStderr.emit(s)

    def __compileUIDone(self, exitCode, exitStatus):
        """
        Private slot to handle the finished signal of the pyuic/rbuic process.

        @param exitCode exit code of the process
        @type int
        @param exitStatus exit status of the process
        @type QProcess.ExitStatus
        """
        self.compileRunning = False
        ericApp().getObject("ViewManager").enableEditorsCheckFocusIn(True)
        ui = ericApp().getObject("UserInterface")
        if (
            exitStatus == QProcess.ExitStatus.NormalExit
            and exitCode == 0
            and self.__buf
        ):
            ofn = os.path.join(self.project.ppath, self.compiledFile)
            try:
                newline = (
                    None if self.project.useSystemEol() else self.project.getEolString()
                )
                with open(ofn, "w", encoding="utf-8", newline=newline) as f:
                    f.write("\n".join(self.__buf) + "\n")
                if self.compiledFile not in self.project.getProjectData(
                    dataKey="SOURCES"
                ):
                    self.project.appendFile(ofn)
                ui.showNotification(
                    EricPixmapCache.getPixmap("designer48"),
                    self.tr("Form Compilation"),
                    self.tr("The compilation of the form file was successful."),
                )
                self.project.projectFileCompiled.emit(self.compiledFile, "FORMS")
            except OSError as msg:
                ui.showNotification(
                    EricPixmapCache.getPixmap("designer48"),
                    self.tr("Form Compilation"),
                    self.tr(
                        "<p>The compilation of the form file failed.</p>"
                        "<p>Reason: {0}</p>"
                    ).format(str(msg)),
                    kind=NotificationTypes.CRITICAL,
                    timeout=0,
                )
        else:
            ui.showNotification(
                EricPixmapCache.getPixmap("designer48"),
                self.tr("Form Compilation"),
                self.tr("The compilation of the form file failed."),
                kind=NotificationTypes.CRITICAL,
                timeout=0,
            )
        self.compileProc = None

    def __compileUI(self, fn, noDialog=False, progress=None):
        """
        Private method to compile a .ui file to a .py/.rb file.

        @param fn filename of the .ui file to be compiled
        @type str
        @param noDialog flag indicating silent operations
        @type bool
        @param progress reference to the progress dialog
        @type QProgressDialog
        @return reference to the compile process
        @rtype QProcess
        """
        self.compileProc = QProcess()
        args = []
        self.__buf = []

        uicompiler = self.getUiCompiler()
        if not uicompiler:
            return None

        ofn, _ext = os.path.splitext(fn)

        if self.project.getProjectLanguage() == "Python3":
            dirname, filename = os.path.split(ofn)
            self.compiledFile = os.path.join(dirname, "Ui_" + filename + ".py")

            if self.project.getProjectType() == "PySide2":
                # PySide2
                if Preferences.getQt("PySide2FromImports"):
                    args.append("--from-imports")
            elif self.project.getProjectType() == "PySide6":
                # PySide6
                if Preferences.getQt("PySide6FromImports"):
                    args.append("--from-imports")
            elif self.project.getProjectType() in ("PyQt6", "E7Plugin"):
                # PyQt6 and E7Plugin
                if Preferences.getQt("Pyuic6Execute"):
                    args.append("-x")
                indentWidth = Preferences.getQt("Pyuic6Indent")
                if indentWidth != self.Pyuic6IndentDefault:
                    args.append("--indent={0}".format(indentWidth))
            else:
                # PyQt5
                if Preferences.getQt("PyuicExecute"):
                    args.append("-x")
                indentWidth = Preferences.getQt("PyuicIndent")
                if indentWidth != self.Pyuic5IndentDefault:
                    args.append("--indent={0}".format(indentWidth))
                if (
                    "uic5" in uicompiler
                    and self.project.getProjectData(dataKey="UICPARAMS")["Package"]
                ):
                    args.append(
                        "--import-from={0}".format(
                            self.project.getProjectData(dataKey="UICPARAMS")["Package"]
                        )
                    )
                elif Preferences.getQt("PyuicFromImports"):
                    args.append("--from-imports")
                if self.project.getProjectData(dataKey="UICPARAMS")["RcSuffix"]:
                    args.append(
                        "--resource-suffix={0}".format(
                            self.project.getProjectData(dataKey="UICPARAMS")["RcSuffix"]
                        )
                    )

        args.append(fn)
        self.compileProc.finished.connect(self.__compileUIDone)
        self.compileProc.readyReadStandardOutput.connect(self.__readStdout)
        self.compileProc.readyReadStandardError.connect(self.__readStderr)

        self.noDialog = noDialog
        self.compileProc.setWorkingDirectory(self.project.getProjectPath())
        self.compileProc.start(uicompiler, args)
        procStarted = self.compileProc.waitForStarted(5000)
        if procStarted:
            self.compileRunning = True
            ericApp().getObject("ViewManager").enableEditorsCheckFocusIn(False)
            return self.compileProc
        else:
            self.compileRunning = False
            if progress is not None:
                progress.cancel()
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "Could not start {0}.<br>Ensure that it is in the search path."
                ).format(uicompiler),
            )
            return None

    def __generateDialogCode(self):
        """
        Private method to generate dialog code for the form (Qt only).
        """
        itm = self.model().item(self.currentIndex())
        fn = itm.fileName()

        if self.hooks["generateDialogCode"] is not None:
            self.hooks["generateDialogCode"](fn)
        else:
            from .CreateDialogCodeDialog import (  # __IGNORE_WARNING_I101__
                CreateDialogCodeDialog,
            )

            # change environment
            sys.path.insert(0, self.project.getProjectPath())
            srcDir = self.project.getProjectData("SOURCESDIR")
            if srcDir:
                sys.path.insert(1, os.path.join(self.project.getAbsolutePath(srcDir)))
            cwd = os.getcwd()
            os.chdir(os.path.dirname(os.path.abspath(fn)))
            try:
                dlg = CreateDialogCodeDialog(fn, self.project, parent=self)
                if not dlg.initError():
                    dlg.exec()
            finally:
                # reset the environment
                os.chdir(cwd)
                if srcDir:
                    del sys.path[1]
                del sys.path[0]

    def __compileForm(self):
        """
        Private method to compile a form to a source file.
        """
        itm = self.model().item(self.currentIndex())
        fn2 = itm.fileName()
        fn = self.project.getRelativePath(fn2)
        if self.hooks["compileForm"] is not None:
            self.hooks["compileForm"](fn)
        else:
            self.__compileUI(fn)

    def __compileAllForms(self):
        """
        Private method to compile all forms to source files.
        """
        if self.hooks["compileAllForms"] is not None:
            self.hooks["compileAllForms"](self.project.getProjectData(dataKey="FORMS"))
        else:
            numForms = len(self.project.getProjectData(dataKey="FORMS"))
            progress = EricProgressDialog(
                self.tr("Compiling forms..."),
                self.tr("Abort"),
                0,
                numForms,
                self.tr("%v/%m Forms"),
                self,
            )
            progress.setModal(True)
            progress.setMinimumDuration(0)
            progress.setWindowTitle(self.tr("Forms"))

            for prog, fn in enumerate(self.project.getProjectData(dataKey="FORMS")):
                progress.setValue(prog)
                if progress.wasCanceled():
                    break

                proc = self.__compileUI(fn, True, progress)
                if proc is not None:
                    while proc.state() == QProcess.ProcessState.Running:
                        QThread.msleep(100)
                        QApplication.processEvents()
                else:
                    break
            progress.setValue(numForms)

    def __compileSelectedForms(self):
        """
        Private method to compile selected forms to source files.
        """
        items = self.getSelectedItems()
        files = [self.project.getRelativePath(itm.fileName()) for itm in items]

        if self.hooks["compileSelectedForms"] is not None:
            self.hooks["compileSelectedForms"](files)
        else:
            numForms = len(files)
            progress = EricProgressDialog(
                self.tr("Compiling forms..."),
                self.tr("Abort"),
                0,
                numForms,
                self.tr("%v/%m Forms"),
                self,
            )
            progress.setModal(True)
            progress.setMinimumDuration(0)
            progress.setWindowTitle(self.tr("Forms"))

            for prog, fn in enumerate(files):
                progress.setValue(prog)
                if progress.wasCanceled():
                    break

                proc = self.__compileUI(fn, True, progress)
                if proc is not None:
                    while proc.state() == QProcess.ProcessState.Running:
                        QThread.msleep(100)
                        QApplication.processEvents()
                else:
                    break
            progress.setValue(numForms)

    def __compileChangedForms(self):
        """
        Private method to compile all changed forms to source files.
        """
        if Preferences.getProject("AutoCompileForms"):
            if self.hooks["compileChangedForms"] is not None:
                self.hooks["compileChangedForms"](
                    self.project.getProjectData(dataKey="FORMS")
                )
            else:
                if self.project.getProjectType() not in [
                    "PyQt5",
                    "PyQt6",
                    "E7Plugin",
                    "PySide2",
                    "PySide6",
                ]:
                    # ignore the request for non Qt GUI projects
                    return

                if len(self.project.getProjectData(dataKey="FORMS")) == 0:
                    # The project does not contain form files.
                    return

                progress = EricProgressDialog(
                    self.tr("Determining changed forms..."),
                    self.tr("Abort"),
                    0,
                    100,
                    self.tr("%v/%m Forms"),
                    self,
                )
                progress.setMinimumDuration(0)
                progress.setWindowTitle(self.tr("Forms"))

                # get list of changed forms
                changedForms = []
                progress.setMaximum(len(self.project.getProjectData(dataKey="FORMS")))
                for prog, fn in enumerate(self.project.getProjectData(dataKey="FORMS")):
                    progress.setValue(prog)
                    QApplication.processEvents()

                    ifn = os.path.join(self.project.ppath, fn)
                    if self.project.getProjectLanguage() == "Python3":
                        dirname, filename = os.path.split(os.path.splitext(ifn)[0])
                        ofn = os.path.join(dirname, "Ui_" + filename + ".py")
                    if (
                        not os.path.exists(ofn)
                        or os.stat(ifn).st_mtime > os.stat(ofn).st_mtime
                    ):
                        changedForms.append(fn)
                progress.setValue(len(self.project.getProjectData(dataKey="FORMS")))
                QApplication.processEvents()

                if changedForms:
                    progress.setLabelText(self.tr("Compiling changed forms..."))
                    progress.setMaximum(len(changedForms))
                    progress.setValue(prog)
                    QApplication.processEvents()
                    for prog, fn in enumerate(changedForms):
                        progress.setValue(prog)
                        if progress.wasCanceled():
                            break

                        proc = self.__compileUI(fn, True, progress)
                        if proc is not None:
                            while proc.state() == QProcess.ProcessState.Running:
                                QApplication.processEvents()
                                QThread.msleep(300)
                                QApplication.processEvents()
                        else:
                            break
                    progress.setValue(len(changedForms))
                    QApplication.processEvents()

    def handlePreferencesChanged(self):
        """
        Public slot used to handle the preferencesChanged signal.
        """
        ProjectBaseBrowser.handlePreferencesChanged(self)

        self.__resetUiCompiler()

    def __configureUicCompiler(self):
        """
        Private slot to configure some non-common uic compiler options.
        """
        from .UicCompilerOptionsDialog import UicCompilerOptionsDialog

        params = self.project.getProjectData(dataKey="UICPARAMS")

        if self.project.getProjectType() in ["PyQt5", "PyQt6", "E7Plugin"]:
            dlg = UicCompilerOptionsDialog(params, self.getUiCompiler(), parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                package, suffix, root = dlg.getData()
                if package != params["Package"]:
                    params["Package"] = package
                    self.project.setDirty(True)
                if suffix != params["RcSuffix"]:
                    params["RcSuffix"] = suffix
                    self.project.setDirty(True)
                if root != params["PackagesRoot"]:
                    params["PackagesRoot"] = root
                    self.project.setDirty(True)

    ###########################################################################
    ## Support for hooks below
    ###########################################################################

    def _initHookMethods(self):
        """
        Protected method to initialize the hooks dictionary.

        Supported hook methods are:
        <ul>
        <li>compileForm: takes filename as parameter</li>
        <li>compileAllForms: takes list of filenames as parameter</li>
        <li>compileSelectedForms: takes list of filenames as parameter</li>
        <li>compileChangedForms: takes list of filenames as parameter</li>
        <li>generateDialogCode: takes filename as parameter</li>
        <li>newForm: takes full directory path of new file as parameter</li>
        <li>open: takes a filename as parameter</li>
        </ul>

        <b>Note</b>: Filenames are relative to the project directory, if not
        specified differently.
        """
        self.hooks = {
            "compileForm": None,
            "compileAllForms": None,
            "compileChangedForms": None,
            "compileSelectedForms": None,
            "generateDialogCode": None,
            "newForm": None,
            "open": None,
        }
