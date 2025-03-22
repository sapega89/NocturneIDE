# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class used to display the Sources part of the project.
"""

import contextlib
import os

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QDialog, QInputDialog, QMenu

from eric7 import Utilities
from eric7.CodeFormatting.BlackFormattingAction import BlackFormattingAction
from eric7.CodeFormatting.BlackUtilities import aboutBlack
from eric7.CodeFormatting.IsortFormattingAction import IsortFormattingAction
from eric7.CodeFormatting.IsortUtilities import aboutIsort
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox, EricPathPickerDialog
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPickerDialog import EricPathPickerModes
from eric7.Graphics.UMLDialog import UMLDialog, UMLDialogType
from eric7.SystemUtilities import FileSystemUtilities
from eric7.UI.BrowserModel import (
    BrowserClassAttributeItem,
    BrowserClassItem,
    BrowserFileItem,
    BrowserImportItem,
    BrowserMethodItem,
)
from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog

from .FileCategoryRepositoryItem import FileCategoryRepositoryItem
from .ProjectBaseBrowser import ProjectBaseBrowser
from .ProjectBrowserModel import (
    ProjectBrowserFileItem,
    ProjectBrowserSimpleDirectoryItem,
)
from .ProjectBrowserRepositoryItem import ProjectBrowserRepositoryItem


class ProjectSourcesBrowser(ProjectBaseBrowser):
    """
    A class used to display the Sources part of the project.

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
        ProjectBaseBrowser.__init__(self, project, "source", parent)

        self.selectedItemsFilter = [
            ProjectBrowserFileItem,
            ProjectBrowserSimpleDirectoryItem,
        ]

        self.setWindowTitle(self.tr("Sources"))

        self.setWhatsThis(
            self.tr(
                """<b>Project Sources Browser</b>"""
                """<p>This allows to easily see all sources contained in the"""
                """ current project. Several actions can be executed via the"""
                """ context menu.</p>"""
            )
        )

        # Add the file category handled by the browser.
        project.addFileCategory(
            "SOURCES",
            FileCategoryRepositoryItem(
                fileCategoryFilterTemplate=self.tr("Source Files ({0})"),
                fileCategoryUserString=self.tr("Source Files"),
                fileCategoryTyeString=self.tr("Sources"),
                fileCategoryExtensions=["*.py", "*.pyw"],  # Python files as default
            ),
        )

        # Add the project browser type to the browser type repository.
        projectBrowser.addTypedProjectBrowser(
            "sources",
            ProjectBrowserRepositoryItem(
                projectBrowser=self,
                projectBrowserUserString=self.tr("Sources Browser"),
                priority=100,
                fileCategory="SOURCES",
                fileFilter="source",
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
        self.sourceFile[str].connect(projectBrowser.sourceFile[str])
        self.sourceFile[str, int].connect(projectBrowser.sourceFile[str, int])
        self.sourceFile[str, list].connect(projectBrowser.sourceFile[str, list])
        self.sourceFile[str, int, str].connect(projectBrowser.sourceFile[str, int, str])
        self.sourceFile[str, int, int].connect(projectBrowser.sourceFile[str, int, int])
        self.closeSourceWindow.connect(projectBrowser.closeSourceWindow)
        self.testFile.connect(projectBrowser.testFile)

        self.codemetrics = None
        self.codecoverage = None
        self.profiledata = None
        self.classDiagram = None
        self.importsDiagram = None
        self.packageDiagram = None
        self.applicationDiagram = None
        self.loadedDiagram = None

    def getIcon(self):
        """
        Public method to get an icon for the project browser.

        @return icon for the browser
        @rtype QIcon
        """
        if not self.project.isOpen():
            icon = EricPixmapCache.getIcon("projectSources")
        else:
            if self.project.getProjectLanguage() == "Python3":
                if self.project.isMixedLanguageProject():
                    icon = EricPixmapCache.getIcon("projectSourcesPyMixed")
                else:
                    icon = EricPixmapCache.getIcon("projectSourcesPy")
            elif self.project.getProjectLanguage() == "MicroPython":
                icon = EricPixmapCache.getIcon("micropython")
            elif self.project.getProjectLanguage() == "Ruby":
                if self.project.isMixedLanguageProject():
                    icon = EricPixmapCache.getIcon("projectSourcesRbMixed")
                else:
                    icon = EricPixmapCache.getIcon("projectSourcesRb")
            elif self.project.getProjectLanguage() == "JavaScript":
                icon = EricPixmapCache.getIcon("projectSourcesJavaScript")
            else:
                icon = EricPixmapCache.getIcon("projectSources")

        return icon

    def __closeAllWindows(self):
        """
        Private method to close all project related windows.
        """
        self.codemetrics and self.codemetrics.close()
        self.codecoverage and self.codecoverage.close()
        self.profiledata and self.profiledata.close()
        self.classDiagram and self.classDiagram.close()
        self.importsDiagram and self.importsDiagram.close()
        self.packageDiagram and self.packageDiagram.close()
        self.applicationDiagram and self.applicationDiagram.close()
        self.loadedDiagram and self.loadedDiagram.close()

    def _projectClosed(self):
        """
        Protected slot to handle the projectClosed signal.
        """
        self.__closeAllWindows()
        ProjectBaseBrowser._projectClosed(self)

    def _createPopupMenus(self):
        """
        Protected overloaded method to generate the popup menu.
        """
        ProjectBaseBrowser._createPopupMenus(self)
        self.sourceMenuActions = {}

        if self.project.isPythonProject():
            self.__createPythonPopupMenus()
        elif self.project.isRubyProject():
            self.__createRubyPopupMenus()
        elif self.project.isJavaScriptProject():
            self.__createJavaScriptPopupMenus()
        else:
            # assign generic source menu
            self.mainMenu = self.sourceMenu

    def __createPythonPopupMenus(self):
        """
        Private method to generate the popup menus for a Python project.
        """
        self.checksMenu = QMenu(self.tr("Check"))
        self.checksMenu.aboutToShow.connect(self.__showContextMenuCheck)

        self.formattingMenu = QMenu(self.tr("Code Formatting"))
        act = self.formattingMenu.addAction(self.tr("Black"), aboutBlack)
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        self.formattingMenu.addAction(
            self.tr("Format Code"),
            lambda: self.__performFormatWithBlack(BlackFormattingAction.Format),
        )
        self.formattingMenu.addAction(
            self.tr("Check Formatting"),
            lambda: self.__performFormatWithBlack(BlackFormattingAction.Check),
        )
        self.formattingMenu.addAction(
            self.tr("Formatting Diff"),
            lambda: self.__performFormatWithBlack(BlackFormattingAction.Diff),
        )
        self.formattingMenu.addSeparator()
        act = self.formattingMenu.addAction(self.tr("isort"), aboutIsort)
        font = act.font()
        font.setBold(True)
        act.setFont(font)
        self.formattingMenu.addAction(
            self.tr("Sort Imports"),
            lambda: self.__performImportSortingWithIsort(IsortFormattingAction.Sort),
        )
        self.formattingMenu.addAction(
            self.tr("Imports Sorting Diff"),
            lambda: self.__performImportSortingWithIsort(IsortFormattingAction.Diff),
        )
        self.formattingMenu.addSeparator()
        self.formattingMenu.aboutToShow.connect(self.__showContextMenuFormatting)

        self.menuShow = QMenu(self.tr("Show"))
        self.menuShow.addAction(self.tr("Code metrics..."), self.__showCodeMetrics)
        self.coverageMenuAction = self.menuShow.addAction(
            self.tr("Code coverage..."), self.__showCodeCoverage
        )
        self.profileMenuAction = self.menuShow.addAction(
            self.tr("Profile data..."), self.__showProfileData
        )
        self.menuShow.aboutToShow.connect(self.__showContextMenuShow)

        self.graphicsMenu = QMenu(self.tr("Diagrams"))
        self.classDiagramAction = self.graphicsMenu.addAction(
            self.tr("Class Diagram..."), self.__showClassDiagram
        )
        self.graphicsMenu.addAction(
            self.tr("Package Diagram..."), self.__showPackageDiagram
        )
        self.importsDiagramAction = self.graphicsMenu.addAction(
            self.tr("Imports Diagram..."), self.__showImportsDiagram
        )
        self.graphicsMenu.addAction(
            self.tr("Application Diagram..."), self.__showApplicationDiagram
        )
        self.graphicsMenu.addSeparator()
        self.graphicsMenu.addAction(
            EricPixmapCache.getIcon("open"),
            self.tr("Load Diagram..."),
            self.__loadDiagram,
        )
        self.graphicsMenu.aboutToShow.connect(self.__showContextMenuGraphics)

        self.__startMenu = QMenu(self.tr("Start"), self)
        self.__startMenu.addAction(
            EricPixmapCache.getIcon("runScript"),
            self.tr("Run Script..."),
            self.__contextMenuRunScript,
        )
        self.__startMenu.addAction(
            EricPixmapCache.getIcon("debugScript"),
            self.tr("Debug Script..."),
            self.__contextMenuDebugScript,
        )
        self.__startMenu.addAction(
            EricPixmapCache.getIcon("profileScript"),
            self.tr("Profile Script..."),
            self.__contextMenuProfileScript,
        )
        self.__startMenu.addAction(
            EricPixmapCache.getIcon("coverageScript"),
            self.tr("Coverage run of Script..."),
            self.__contextMenuCoverageScript,
        )

        self.testingAction = self.sourceMenu.addAction(
            self.tr("Run tests..."), self.handleTesting
        )
        self.sourceMenu.addSeparator()
        act = self.sourceMenu.addAction(self.tr("Rename file"), self._renameFile)
        self.menuActions.append(act)
        act = self.sourceMenu.addAction(
            self.tr("Remove from project"), self._removeFile
        )
        self.menuActions.append(act)
        act = self.sourceMenu.addAction(self.tr("Delete"), self.__deleteFile)
        self.menuActions.append(act)
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(self.tr("New package..."), self.__addNewPackage)
        self.sourceMenu.addAction(
            self.tr("New source file..."), self.__addNewSourceFile
        )
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(self.tr("Add source files..."), self.__addSourceFiles)
        self.sourceMenu.addAction(
            self.tr("Add source directory..."), self.__addSourceDirectory
        )
        self.sourceMenu.addSeparator()
        self.sourceMenu.addMenu(self.graphicsMenu)
        self.sourceMenu.addMenu(self.checksMenu)
        self.sourceMenuActions["Formatting"] = self.sourceMenu.addMenu(
            self.formattingMenu
        )
        self.sourceMenuActions["Show"] = self.sourceMenu.addMenu(self.menuShow)
        self.sourceMenu.addSeparator()
        self.__startAct = self.sourceMenu.addMenu(self.__startMenu)
        self.sourceMenu.addSeparator()
        self.__sourceMenuFileManagerAct = self.sourceMenu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.sourceMenu.addAction(
            self.tr("Copy Path to Clipboard"), self._copyToClipboard
        )
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(
            self.tr("Expand all directories"), self._expandAllDirs
        )
        self.sourceMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.sourceMenu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(self.tr("Configure..."), self._configure)

        self.menu.addSeparator()
        self.menu.addAction(self.tr("New package..."), self.__addNewPackage)
        self.menu.addAction(self.tr("New source file..."), self.__addNewSourceFile)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Add source files..."), self.__addSourceFiles)
        self.menu.addAction(
            self.tr("Add source directory..."), self.__addSourceDirectory
        )
        self.menu.addSeparator()
        self.__menuFileManagerAct = self.menu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.menu.addAction(self.tr("Collapse all directories"), self._collapseAllDirs)
        self.menu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Configure..."), self._configure)

        # create the attribute menu
        self.gotoMenu = QMenu(self.tr("Goto"), self)
        self.gotoMenu.aboutToShow.connect(self._showGotoMenu)
        self.gotoMenu.triggered.connect(self._gotoAttribute)

        self.attributeMenu = QMenu(self)
        self.attributeMenu.addMenu(self.gotoMenu)
        self.attributeMenu.addSeparator()
        self.attributeMenu.addAction(self.tr("New package..."), self.__addNewPackage)
        self.attributeMenu.addAction(
            self.tr("New source file..."), self.__addNewSourceFile
        )
        self.attributeMenu.addSeparator()
        self.attributeMenu.addAction(
            self.tr("Add source files..."),
            lambda: self.project.addFiles("SOURCES"),
        )
        self.attributeMenu.addAction(
            self.tr("Add source directory..."),
            lambda: self.project.addDirectory("SOURCES"),
        )
        self.attributeMenu.addSeparator()
        self.__attributeMenuFileManagerAct = self.attributeMenu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.attributeMenu.addSeparator()
        self.attributeMenu.addAction(
            self.tr("Expand all directories"), self._expandAllDirs
        )
        self.attributeMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.attributeMenu.addAction(
            self.tr("Collapse all files"), self._collapseAllFiles
        )
        self.attributeMenu.addSeparator()
        self.attributeMenu.addAction(self.tr("Configure..."), self._configure)

        self.backMenu = QMenu(self)
        self.backMenu.addAction(self.tr("New package..."), self.__addNewPackage)
        self.backMenu.addAction(self.tr("New source file..."), self.__addNewSourceFile)
        self.backMenu.addSeparator()
        self.backMenu.addAction(
            self.tr("Add source files..."),
            lambda: self.project.addFiles("SOURCES"),
        )
        self.backMenu.addAction(
            self.tr("Add source directory..."),
            lambda: self.project.addDirectory("SOURCES"),
        )
        self.backMenu.addSeparator()
        self.__backMenuFileManagerAct = self.backMenu.addAction(
            self.tr("Show in File Manager"), self._showProjectInFileManager
        )
        self.backMenu.addSeparator()
        self.backMenu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.backMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.backMenu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.backMenu.addSeparator()
        self.backMenu.addAction(self.tr("Configure..."), self._configure)
        self.backMenu.setEnabled(False)

        self.multiMenu.addSeparator()
        act = self.multiMenu.addAction(self.tr("Remove from project"), self._removeFile)
        self.multiMenuActions.append(act)
        act = self.multiMenu.addAction(self.tr("Delete"), self.__deleteFile)
        self.multiMenuActions.append(act)
        self.multiMenu.addSeparator()
        self.multiMenu.addMenu(self.checksMenu)
        self.__multiMenuFormattingAct = self.multiMenu.addMenu(self.formattingMenu)
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.multiMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.multiMenu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.tr("Configure..."), self._configure)

        self.dirMenu = QMenu(self)
        act = self.dirMenu.addAction(self.tr("Remove from project"), self._removeDir)
        self.dirMenuActions.append(act)
        act = self.dirMenu.addAction(self.tr("Delete"), self._deleteDirectory)
        self.dirMenuActions.append(act)
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("New package..."), self.__addNewPackage)
        self.dirMenu.addAction(self.tr("New source file..."), self.__addNewSourceFile)
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Add source files..."), self.__addSourceFiles)
        self.dirMenu.addAction(
            self.tr("Add source directory..."), self.__addSourceDirectory
        )
        self.dirMenu.addSeparator()
        act = self.dirMenu.addMenu(self.graphicsMenu)
        self.dirMenu.addMenu(self.checksMenu)
        self.__dirMenuFormattingAct = self.dirMenu.addMenu(self.formattingMenu)
        self.dirMenu.addSeparator()
        self.__dirMenuFileManagerAct = self.dirMenu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.dirMenu.addAction(self.tr("Copy Path to Clipboard"), self._copyToClipboard)
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.dirMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.dirMenu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Configure..."), self._configure)

        self.dirMultiMenu = QMenu(self)
        self.dirMultiMenu.addAction(
            self.tr("Expand all directories"), self._expandAllDirs
        )
        self.dirMultiMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.dirMultiMenu.addAction(
            self.tr("Collapse all files"), self._collapseAllFiles
        )
        self.dirMultiMenu.addSeparator()
        self.dirMultiMenu.addAction(self.tr("Configure..."), self._configure)

        self.sourceMenu.aboutToShow.connect(self.__showContextMenu)
        self.menu.aboutToShow.connect(self.__showContextMenuGeneral)
        self.attributeMenu.aboutToShow.connect(self.__showContextMenuAttribute)
        self.multiMenu.aboutToShow.connect(self.__showContextMenuMulti)
        self.dirMenu.aboutToShow.connect(self.__showContextMenuDir)
        self.dirMultiMenu.aboutToShow.connect(self.__showContextMenuDirMulti)
        self.backMenu.aboutToShow.connect(self.__showContextMenuBack)
        self.mainMenu = self.sourceMenu

    def __createRubyPopupMenus(self):
        """
        Private method to generate the popup menus for a Ruby project.
        """
        self.graphicsMenu = QMenu(self.tr("Diagrams"))
        self.classDiagramAction = self.graphicsMenu.addAction(
            self.tr("Class Diagram..."), self.__showClassDiagram
        )
        self.graphicsMenu.addAction(
            self.tr("Package Diagram..."), self.__showPackageDiagram
        )
        self.graphicsMenu.addAction(
            self.tr("Application Diagram..."), self.__showApplicationDiagram
        )
        self.graphicsMenu.addSeparator()
        self.graphicsMenu.addAction(
            EricPixmapCache.getIcon("fileOpen"),
            self.tr("Load Diagram..."),
            self.__loadDiagram,
        )

        self.sourceMenu.addSeparator()
        act = self.sourceMenu.addAction(self.tr("Rename file"), self._renameFile)
        self.menuActions.append(act)
        act = self.sourceMenu.addAction(
            self.tr("Remove from project"), self._removeFile
        )
        self.menuActions.append(act)
        act = self.sourceMenu.addAction(self.tr("Delete"), self.__deleteFile)
        self.menuActions.append(act)
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(self.tr("Add source files..."), self.__addSourceFiles)
        self.sourceMenu.addAction(
            self.tr("Add source directory..."), self.__addSourceDirectory
        )
        self.sourceMenu.addSeparator()
        act = self.sourceMenu.addMenu(self.graphicsMenu)
        self.sourceMenu.addSeparator()
        self.__sourceMenuFileManagerAct = self.sourceMenu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(
            self.tr("Expand all directories"), self._expandAllDirs
        )
        self.sourceMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.sourceMenu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(self.tr("Configure..."), self._configure)

        self.menu.addSeparator()
        self.menu.addAction(self.tr("Add source files..."), self.__addSourceFiles)
        self.menu.addAction(
            self.tr("Add source directory..."), self.__addSourceDirectory
        )
        self.menu.addSeparator()
        self.__menuFileManagerAct = self.menu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.menu.addAction(self.tr("Collapse all directories"), self._collapseAllDirs)
        self.menu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Configure..."), self._configure)

        # create the attribute menu
        self.gotoMenu = QMenu(self.tr("Goto"), self)
        self.gotoMenu.aboutToShow.connect(self._showGotoMenu)
        self.gotoMenu.triggered.connect(self._gotoAttribute)

        self.attributeMenu = QMenu(self)
        self.attributeMenu.addMenu(self.gotoMenu)
        self.attributeMenu.addSeparator()
        self.attributeMenu.addAction(
            self.tr("Add source files..."),
            lambda: self.project.addFiles("SOURCES"),
        )
        self.attributeMenu.addAction(
            self.tr("Add source directory..."),
            lambda: self.project.addDirectory("SOURCES"),
        )
        self.attributeMenu.addSeparator()
        self.__attributeMenuFileManagerAct = self.attributeMenu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.attributeMenu.addSeparator()
        self.attributeMenu.addAction(
            self.tr("Expand all directories"), self._expandAllDirs
        )
        self.attributeMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.attributeMenu.addAction(
            self.tr("Collapse all files"), self._collapseAllFiles
        )
        self.attributeMenu.addSeparator()
        self.attributeMenu.addAction(self.tr("Configure..."), self._configure)

        self.backMenu = QMenu(self)
        self.backMenu.addAction(
            self.tr("Add source files..."),
            lambda: self.project.addFiles("SOURCES"),
        )
        self.backMenu.addAction(
            self.tr("Add source directory..."),
            lambda: self.project.addDirectory("SOURCES"),
        )
        self.backMenu.addSeparator()
        self.__backMenuFileManagerAct = self.backMenu.addAction(
            self.tr("Show in File Manager"), self._showProjectInFileManager
        )
        self.backMenu.addSeparator()
        self.backMenu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.backMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.backMenu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.backMenu.setEnabled(False)
        self.backMenu.addSeparator()
        self.backMenu.addAction(self.tr("Configure..."), self._configure)

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
        self.multiMenu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.tr("Configure..."), self._configure)

        self.dirMenu = QMenu(self)
        act = self.dirMenu.addAction(self.tr("Remove from project"), self._removeDir)
        self.dirMenuActions.append(act)
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Add source files..."), self.__addSourceFiles)
        self.dirMenu.addAction(
            self.tr("Add source directory..."), self.__addSourceDirectory
        )
        self.dirMenu.addSeparator()
        act = self.dirMenu.addMenu(self.graphicsMenu)
        self.dirMenu.addSeparator()
        self.__dirMenuFileManagerAct = self.dirMenu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.dirMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.dirMenu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Configure..."), self._configure)

        self.dirMultiMenu = QMenu(self)
        self.dirMultiMenu.addAction(
            self.tr("Expand all directories"), self._expandAllDirs
        )
        self.dirMultiMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.dirMultiMenu.addAction(
            self.tr("Collapse all files"), self._collapseAllFiles
        )
        self.dirMultiMenu.addSeparator()
        self.dirMultiMenu.addAction(self.tr("Configure..."), self._configure)

        self.sourceMenu.aboutToShow.connect(self.__showContextMenu)
        self.menu.aboutToShow.connect(self.__showContextMenuGeneral)
        self.attributeMenu.aboutToShow.connect(self.__showContextMenuAttribute)
        self.multiMenu.aboutToShow.connect(self.__showContextMenuMulti)
        self.dirMenu.aboutToShow.connect(self.__showContextMenuDir)
        self.dirMultiMenu.aboutToShow.connect(self.__showContextMenuDirMulti)
        self.backMenu.aboutToShow.connect(self.__showContextMenuBack)
        self.mainMenu = self.sourceMenu

    def __createJavaScriptPopupMenus(self):
        """
        Private method to generate the popup menus for a Python project.
        """
        self.checksMenu = QMenu(self.tr("Check"))
        self.checksMenu.aboutToShow.connect(self.__showContextMenuCheck)

        self.sourceMenu.addSeparator()
        act = self.sourceMenu.addAction(self.tr("Rename file"), self._renameFile)
        self.menuActions.append(act)
        act = self.sourceMenu.addAction(
            self.tr("Remove from project"), self._removeFile
        )
        self.menuActions.append(act)
        act = self.sourceMenu.addAction(self.tr("Delete"), self.__deleteFile)
        self.menuActions.append(act)
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(self.tr("Add source files..."), self.__addSourceFiles)
        self.sourceMenu.addAction(
            self.tr("Add source directory..."), self.__addSourceDirectory
        )
        self.sourceMenu.addSeparator()
        self.sourceMenu.addMenu(self.checksMenu)
        self.sourceMenu.addSeparator()
        self.__sourceMenuFileManagerAct = self.sourceMenu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.sourceMenu.addAction(
            self.tr("Copy Path to Clipboard"), self._copyToClipboard
        )
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(
            self.tr("Expand all directories"), self._expandAllDirs
        )
        self.sourceMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.sourceMenu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.sourceMenu.addSeparator()
        self.sourceMenu.addAction(self.tr("Configure..."), self._configure)

        self.menu.addSeparator()
        self.menu.addAction(self.tr("Add source files..."), self.__addSourceFiles)
        self.menu.addAction(
            self.tr("Add source directory..."), self.__addSourceDirectory
        )
        self.menu.addSeparator()
        self.__menuFileManagerAct = self.menu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.menu.addAction(self.tr("Collapse all directories"), self._collapseAllDirs)
        self.menu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Configure..."), self._configure)

        # create the attribute menu
        self.gotoMenu = QMenu(self.tr("Goto"), self)
        self.gotoMenu.aboutToShow.connect(self._showGotoMenu)
        self.gotoMenu.triggered.connect(self._gotoAttribute)

        self.attributeMenu = QMenu(self)
        self.attributeMenu.addMenu(self.gotoMenu)
        self.attributeMenu.addSeparator()
        self.attributeMenu.addAction(
            self.tr("Add source files..."),
            lambda: self.project.addFiles("SOURCES"),
        )
        self.attributeMenu.addAction(
            self.tr("Add source directory..."),
            lambda: self.project.addDirectory("SOURCES"),
        )
        self.attributeMenu.addSeparator()
        self.__attrMenuFileManagerAct = self.attributeMenu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.attributeMenu.addSeparator()
        self.attributeMenu.addAction(
            self.tr("Expand all directories"), self._expandAllDirs
        )
        self.attributeMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.attributeMenu.addAction(
            self.tr("Collapse all files"), self._collapseAllFiles
        )
        self.attributeMenu.addSeparator()
        self.attributeMenu.addAction(self.tr("Configure..."), self._configure)

        self.backMenu = QMenu(self)
        self.backMenu.addAction(
            self.tr("Add source files..."),
            lambda: self.project.addFiles("SOURCES"),
        )
        self.backMenu.addAction(
            self.tr("Add source directory..."),
            lambda: self.project.addDirectory("SOURCES"),
        )
        self.backMenu.addSeparator()
        self.__backMenuFileManagerAct = self.backMenu.addAction(
            self.tr("Show in File Manager"), self._showProjectInFileManager
        )
        self.backMenu.addSeparator()
        self.backMenu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.backMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.backMenu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.backMenu.addSeparator()
        self.backMenu.addAction(self.tr("Configure..."), self._configure)
        self.backMenu.setEnabled(False)

        self.multiMenu.addSeparator()
        act = self.multiMenu.addAction(self.tr("Remove from project"), self._removeFile)
        self.multiMenuActions.append(act)
        act = self.multiMenu.addAction(self.tr("Delete"), self.__deleteFile)
        self.multiMenuActions.append(act)
        self.multiMenu.addSeparator()
        self.multiMenu.addMenu(self.checksMenu)
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.multiMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.multiMenu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.tr("Configure..."), self._configure)

        self.dirMenu = QMenu(self)
        act = self.dirMenu.addAction(self.tr("Remove from project"), self._removeDir)
        self.dirMenuActions.append(act)
        act = self.dirMenu.addAction(self.tr("Delete"), self._deleteDirectory)
        self.dirMenuActions.append(act)
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Add source files..."), self.__addSourceFiles)
        self.dirMenu.addAction(
            self.tr("Add source directory..."), self.__addSourceDirectory
        )
        self.dirMenu.addSeparator()
        self.dirMenu.addMenu(self.checksMenu)
        self.dirMenu.addSeparator()
        self.__dirMenuFileManagerAct = self.dirMenu.addAction(
            self.tr("Show in File Manager"), self._showInFileManager
        )
        self.dirMenu.addAction(self.tr("Copy Path to Clipboard"), self._copyToClipboard)
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Expand all directories"), self._expandAllDirs)
        self.dirMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.dirMenu.addAction(self.tr("Collapse all files"), self._collapseAllFiles)
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Configure..."), self._configure)

        self.dirMultiMenu = QMenu(self)
        self.dirMultiMenu.addAction(
            self.tr("Expand all directories"), self._expandAllDirs
        )
        self.dirMultiMenu.addAction(
            self.tr("Collapse all directories"), self._collapseAllDirs
        )
        self.dirMultiMenu.addAction(
            self.tr("Collapse all files"), self._collapseAllFiles
        )
        self.dirMultiMenu.addSeparator()
        self.dirMultiMenu.addAction(self.tr("Configure..."), self._configure)

        self.sourceMenu.aboutToShow.connect(self.__showContextMenu)
        self.menu.aboutToShow.connect(self.__showContextMenuGeneral)
        self.attributeMenu.aboutToShow.connect(self.__showContextMenuAttribute)
        self.multiMenu.aboutToShow.connect(self.__showContextMenuMulti)
        self.dirMenu.aboutToShow.connect(self.__showContextMenuDir)
        self.dirMultiMenu.aboutToShow.connect(self.__showContextMenuDirMulti)
        self.backMenu.aboutToShow.connect(self.__showContextMenuBack)
        self.mainMenu = self.sourceMenu

    def _contextMenuRequested(self, coord):
        """
        Protected slot to show the context menu.

        @param coord the position of the mouse pointer
        @type QPoint
        """
        if not self.project.isOpen():
            return

        with contextlib.suppress(Exception):  # secok
            categories = self.getSelectedItemsCountCategorized(
                [
                    ProjectBrowserFileItem,
                    BrowserClassItem,
                    BrowserMethodItem,
                    ProjectBrowserSimpleDirectoryItem,
                    BrowserClassAttributeItem,
                    BrowserImportItem,
                ]
            )
            cnt = categories["sum"]
            if cnt <= 1:
                index = self.indexAt(coord)
                if index.isValid():
                    self._selectSingleItem(index)
                    categories = self.getSelectedItemsCountCategorized(
                        [
                            ProjectBrowserFileItem,
                            BrowserClassItem,
                            BrowserMethodItem,
                            ProjectBrowserSimpleDirectoryItem,
                            BrowserClassAttributeItem,
                            BrowserImportItem,
                        ]
                    )
                    cnt = categories["sum"]

            bfcnt = categories[str(ProjectBrowserFileItem)]
            cmcnt = (
                categories[str(BrowserClassItem)]
                + categories[str(BrowserMethodItem)]
                + categories[str(BrowserClassAttributeItem)]
                + categories[str(BrowserImportItem)]
            )
            sdcnt = categories[str(ProjectBrowserSimpleDirectoryItem)]
            if cnt > 1 and cnt == bfcnt:
                self.multiMenu.popup(self.mapToGlobal(coord))
            elif cnt > 1 and cnt == sdcnt:
                self.dirMultiMenu.popup(self.mapToGlobal(coord))
            else:
                index = self.indexAt(coord)
                if cnt == 1 and index.isValid():
                    if bfcnt == 1 or cmcnt == 1:
                        itm = self.model().item(index)
                        if isinstance(itm, ProjectBrowserFileItem):
                            fn = itm.fileName()
                            if self.project.isPythonProject():
                                if fn.endswith(".ptl"):
                                    for act in self.sourceMenuActions.values():
                                        act.setEnabled(False)
                                    self.classDiagramAction.setEnabled(True)
                                    self.importsDiagramAction.setEnabled(True)
                                    self.testingAction.setEnabled(False)
                                    self.checksMenu.menuAction().setEnabled(False)
                                elif fn.endswith(".rb"):
                                    # entry for mixed mode programs
                                    for act in self.sourceMenuActions.values():
                                        act.setEnabled(False)
                                    self.classDiagramAction.setEnabled(True)
                                    self.importsDiagramAction.setEnabled(False)
                                    self.testingAction.setEnabled(False)
                                    self.checksMenu.menuAction().setEnabled(False)
                                elif fn.endswith(".js"):
                                    # entry for mixed mode programs
                                    for act in self.sourceMenuActions.values():
                                        act.setEnabled(False)
                                    self.testingAction.setEnabled(False)
                                    self.checksMenu.menuAction().setEnabled(False)
                                    self.graphicsMenu.menuAction().setEnabled(False)
                                else:
                                    # assume the source file is a Python file
                                    for act in self.sourceMenuActions.values():
                                        act.setEnabled(True)
                                    self.classDiagramAction.setEnabled(True)
                                    self.importsDiagramAction.setEnabled(True)
                                    self.testingAction.setEnabled(True)
                                    self.checksMenu.menuAction().setEnabled(True)
                            self.sourceMenu.popup(self.mapToGlobal(coord))
                        elif isinstance(
                            itm,
                            (BrowserClassItem, BrowserMethodItem, BrowserImportItem),
                        ):
                            self.menu.popup(self.mapToGlobal(coord))
                        elif isinstance(itm, BrowserClassAttributeItem):
                            self.attributeMenu.popup(self.mapToGlobal(coord))
                        else:
                            self.backMenu.popup(self.mapToGlobal(coord))
                    elif sdcnt == 1:
                        self.classDiagramAction.setEnabled(False)
                        self.dirMenu.popup(self.mapToGlobal(coord))
                    else:
                        self.backMenu.popup(self.mapToGlobal(coord))
                else:
                    self.backMenu.popup(self.mapToGlobal(coord))

    def __showContextMenu(self):
        """
        Private slot called by the sourceMenu aboutToShow signal.
        """
        ProjectBaseBrowser._showContextMenu(self, self.sourceMenu)

        itm = self.model().item(self.currentIndex())
        if itm:
            try:
                self.__startAct.setEnabled(itm.isPython3File())
            except AttributeError:
                self.__startAct.setEnabled(False)
        else:
            self.__startAct.setEnabled(False)

        self.sourceMenuActions["Formatting"].setEnabled(
            self.sourceMenuActions["Formatting"].isEnabled()
            and not FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        )
        self.__sourceMenuFileManagerAct.setEnabled(
            not FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        )

        self.showMenu.emit("Main", self.sourceMenu)

    def __showContextMenuGeneral(self):
        """
        Private slot called by the menu aboutToShow signal.
        """
        ProjectBaseBrowser._showContextMenu(self, self.menu)

        self.__menuFileManagerAct.setEnabled(
            not FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        )

    def __showContextMenuAttribute(self):
        """
        Private slot called by the attributeMenu aboutToShow signal.
        """
        ProjectBaseBrowser._showContextMenu(self, self.menu)

        self.__attributeMenuFileManagerAct.setEnabled(
            not FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        )

    def __showContextMenuMulti(self):
        """
        Private slot called by the multiMenu aboutToShow signal.
        """
        ProjectBaseBrowser._showContextMenuMulti(self, self.multiMenu)

        self.__multiMenuFormattingAct.setEnabled(
            not FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        )

        self.showMenu.emit("MainMulti", self.multiMenu)

    def __showContextMenuDir(self):
        """
        Private slot called by the dirMenu aboutToShow signal.
        """
        ProjectBaseBrowser._showContextMenuDir(self, self.dirMenu)

        self.__dirMenuFormattingAct.setEnabled(
            not FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        )
        self.__dirMenuFileManagerAct.setEnabled(
            not FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        )

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

        self.__backMenuFileManagerAct.setEnabled(
            not FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        )

        self.showMenu.emit("MainBack", self.backMenu)

    def __showContextMenuShow(self):
        """
        Private slot called before the show menu is shown.
        """
        prEnable = False
        coEnable = False

        # first check if the file belongs to a project and there is
        # a project coverage file
        fn = self.project.getMainScript(True)
        if fn is not None:
            prEnable = self.project.isPy3Project() and bool(
                Utilities.getProfileFileNames(fn)
            )
            coEnable = self.project.isPy3Project() and bool(
                Utilities.getCoverageFileNames(fn)
            )

        # now check the selected item
        itm = self.model().item(self.currentIndex())
        fn = itm.fileName()
        if fn is not None:
            prEnable |= itm.isPython3File() and bool(Utilities.getProfileFileNames(fn))
            coEnable |= itm.isPython3File() and bool(Utilities.getCoverageFileName(fn))

        self.profileMenuAction.setEnabled(prEnable)
        self.coverageMenuAction.setEnabled(coEnable)

        self.showMenu.emit("Show", self.menuShow)

    def _openItem(self):
        """
        Protected slot to handle the open popup menu entry.
        """
        itmList = self.getSelectedItems(
            [
                BrowserFileItem,
                BrowserClassItem,
                BrowserMethodItem,
                BrowserClassAttributeItem,
                BrowserImportItem,
            ]
        )

        for itm in itmList:
            if isinstance(itm, BrowserFileItem):
                if itm.isPython3File():
                    self.sourceFile[str].emit(itm.fileName())
                elif itm.isRubyFile():
                    self.sourceFile[str, int, str].emit(itm.fileName(), -1, "Ruby")
                elif itm.isDFile():
                    self.sourceFile[str, int, str].emit(itm.fileName(), -1, "D")
                else:
                    self.sourceFile[str].emit(itm.fileName())
            elif isinstance(itm, BrowserClassItem):
                self.sourceFile[str, int, int].emit(
                    itm.fileName(), itm.lineno(), itm.colOffset()
                )
            elif isinstance(itm, BrowserMethodItem):
                self.sourceFile[str, int, int].emit(
                    itm.fileName(), itm.lineno(), itm.colOffset()
                )
            elif isinstance(itm, BrowserClassAttributeItem):
                self.sourceFile[str, int, int].emit(
                    itm.fileName(), itm.lineno(), itm.colOffset()
                )
            elif isinstance(itm, BrowserImportItem):
                self.sourceFile[str, list].emit(itm.fileName(), itm.linenos())

    def __addNewPackage(self):
        """
        Private method to add a new package to the project.
        """
        from .NewPythonPackageDialog import NewPythonPackageDialog

        isRemote = FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )
        separator = remotefsInterface.separator() if isRemote else os.sep

        dn = self.currentDirectory(relative=True)
        if dn.startswith(separator):
            dn = dn[1:]
        dlg = NewPythonPackageDialog(dn, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            packageName = dlg.getData()
            nameParts = packageName.split(".")
            packagePath = self.project.ppath
            packageFile = ""
            for name in nameParts:
                packagePath = (
                    remotefsInterface.join(packagePath, name)
                    if isRemote
                    else os.path.join(packagePath, name)
                )
                exists = (
                    remotefsInterface.exists(packagePath)
                    if isRemote
                    else os.path.exists(packagePath)
                )
                if not exists:
                    try:
                        if isRemote:
                            remotefsInterface.mkdir(packagePath)
                        else:
                            os.mkdir(packagePath)
                    except OSError as err:
                        EricMessageBox.critical(
                            self,
                            self.tr("Add new Python package"),
                            self.tr(
                                """<p>The package directory <b>{0}</b> could"""
                                """ not be created. Aborting...</p>"""
                                """<p>Reason: {1}</p>"""
                            ).format(packagePath, str(err)),
                        )
                        return
                packageFile = (
                    remotefsInterface.join(packagePath, "__init__.py")
                    if isRemote
                    else os.path.join(packagePath, "__init__.py")
                )
                exists = (
                    remotefsInterface.exists(packageFile)
                    if isRemote
                    else os.path.exists(packageFile)
                )
                if not exists:
                    try:
                        if isRemote:
                            remotefsInterface.writeFile(packageFile, b"")
                        else:
                            with open(packageFile, "w", encoding="utf-8"):
                                pass
                    except OSError as err:
                        EricMessageBox.critical(
                            self,
                            self.tr("Add new Python package"),
                            self.tr(
                                """<p>The package file <b>{0}</b> could"""
                                """ not be created. Aborting...</p>"""
                                """<p>Reason: {1}</p>"""
                            ).format(packageFile, str(err)),
                        )
                        return
                self.project.appendFile(packageFile)
            if packageFile:
                self.sourceFile[str].emit(packageFile)

    def __addNewSourceFile(self):
        """
        Private method to add a new source file to the project.
        """
        isRemote = FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        dn = self.currentDirectory()
        filename, ok = EricPathPickerDialog.getStrPath(
            self,
            self.tr("New source file"),
            self.tr("Enter the path of the new source file:"),
            mode=EricPathPickerModes.SAVE_FILE_ENSURE_EXTENSION_MODE,
            strPath=dn,
            defaultDirectory=dn,
            filters=self.project.getFileCategoryFilters(
                categories=["SOURCES"], withAll=False
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
                    self.tr("New source file"),
                    self.tr(
                        "<p>The file <b>{0}</b> already exists. The action will be"
                        " aborted.</p>"
                    ).format(filename),
                )
                return

            try:
                newline = (
                    None if self.project.useSystemEol() else self.project.getEolString()
                )
                header = "# -*- coding: utf-8 -*-\n# {0}\n".format(
                    self.project.getRelativePath(filename)
                )
                if isRemote:
                    remotefsInterface.writeFile(
                        filename, header.encode("utf-8"), newline=newline
                    )
                else:
                    with open(filename, "w", newline=newline) as f:
                        f.write(header)
            except OSError as err:
                EricMessageBox.critical(
                    self,
                    self.tr("New source file"),
                    self.tr(
                        "<p>The file <b>{0}</b> could not be created. Aborting...</p>"
                        "<p>Reason: {1}</p>"
                    ).format(filename, str(err)),
                )
                return

            self.project.appendFile(filename)
            self.sourceFile[str].emit(filename)

    def __addSourceFiles(self):
        """
        Private method to add a source file to the project.
        """
        self.project.addFiles("SOURCES", self.currentDirectory())

    def __addSourceDirectory(self):
        """
        Private method to add source files of a directory to the project.
        """
        self.project.addDirectory("SOURCES", self.currentDirectory())

    def __deleteFile(self):
        """
        Private method to delete files from the project.
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
            self.tr("Delete files"),
            self.tr("Do you really want to delete these files from the project?"),
            files,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            for fn2, fn in zip(fullNames, files):
                self.closeSourceWindow.emit(fn2)
                self.project.deleteFile(fn)

    ###########################################################################
    ## Methods for the Checks submenu
    ###########################################################################

    def __showContextMenuCheck(self):
        """
        Private slot called before the checks menu is shown.
        """
        self.showMenu.emit("Checks", self.checksMenu)

    ###########################################################################
    ## Methods for the Show submenu
    ###########################################################################

    def __showCodeMetrics(self):
        """
        Private method to handle the code metrics context menu action.
        """
        from eric7.DataViews.CodeMetricsDialog import CodeMetricsDialog

        itm = self.model().item(self.currentIndex())
        fn = itm.fileName()

        self.codemetrics = CodeMetricsDialog()
        self.codemetrics.show()
        self.codemetrics.start(fn)

    def __showCodeCoverage(self):
        """
        Private method to handle the code coverage context menu action.
        """
        from eric7.DataViews.PyCoverageDialog import PyCoverageDialog

        itm = self.model().item(self.currentIndex())
        fn = itm.fileName()
        pfn = self.project.getMainScript(True)

        files = []

        if pfn is not None:
            files.extend(
                [f for f in Utilities.getCoverageFileNames(pfn) if f not in files]
            )

        if fn is not None:
            files.extend(
                [f for f in Utilities.getCoverageFileNames(fn) if f not in files]
            )

        if files:
            if len(files) > 1:
                cfn, ok = QInputDialog.getItem(
                    None,
                    self.tr("Code Coverage"),
                    self.tr("Please select a coverage file"),
                    files,
                    0,
                    False,
                )
                if not ok:
                    return
            else:
                cfn = files[0]
        else:
            return

        self.codecoverage = PyCoverageDialog()
        self.codecoverage.show()
        self.codecoverage.start(cfn, fn)

    def __showProfileData(self):
        """
        Private method to handle the show profile data context menu action.
        """
        from eric7.DataViews.PyProfileDialog import PyProfileDialog

        itm = self.model().item(self.currentIndex())
        fn = itm.fileName()
        pfn = self.project.getMainScript(True)

        files = []

        if pfn is not None:
            files.extend(
                [f for f in Utilities.getProfileFileNames(pfn) if f not in files]
            )

        if fn is not None:
            files.extend(
                [f for f in Utilities.getProfileFileNames(fn) if f not in files]
            )

        if files:
            if len(files) > 1:
                pfn, ok = QInputDialog.getItem(
                    None,
                    self.tr("Profile Data"),
                    self.tr("Please select a profile file"),
                    files,
                    0,
                    False,
                )
                if not ok:
                    return
            else:
                pfn = files[0]
        else:
            return

        self.profiledata = PyProfileDialog()
        self.profiledata.show()
        self.profiledata.start(pfn, fn)

    ###########################################################################
    ## Methods for the Graphics submenu
    ###########################################################################

    def __showContextMenuGraphics(self):
        """
        Private slot called before the checks menu is shown.
        """
        self.showMenu.emit("Graphics", self.graphicsMenu)

    def __showClassDiagram(self):
        """
        Private method to handle the class diagram context menu action.
        """
        itm = self.model().item(self.currentIndex())
        try:
            fn = itm.fileName()
        except AttributeError:
            fn = itm.dirName()
        res = EricMessageBox.yesNo(
            self,
            self.tr("Class Diagram"),
            self.tr("""Include class attributes?"""),
            yesDefault=True,
        )

        self.classDiagram = UMLDialog(
            UMLDialogType.CLASS_DIAGRAM, self.project, fn, self, noAttrs=not res
        )
        self.classDiagram.show()

    def __showImportsDiagram(self):
        """
        Private method to handle the imports diagram context menu action.
        """
        isRemote = FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        itm = self.model().item(self.currentIndex())
        try:
            fn = itm.fileName()
        except AttributeError:
            fn = itm.dirName()
        package = (
            fn
            if remotefsInterface.isdir(fn)
            else (
                remotefsInterface.dirname(fn)
                if isRemote
                else fn if os.path.isdir(fn) else os.path.dirname(fn)
            )
        )
        res = EricMessageBox.yesNo(
            self,
            self.tr("Imports Diagram"),
            self.tr("""Include imports from external modules?"""),
        )

        self.importsDiagram = UMLDialog(
            UMLDialogType.IMPORTS_DIAGRAM,
            self.project,
            package,
            self,
            showExternalImports=res,
        )
        self.importsDiagram.show()

    def __showPackageDiagram(self):
        """
        Private method to handle the package diagram context menu action.
        """
        isRemote = FileSystemUtilities.isRemoteFileName(self.project.getProjectPath())
        remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        itm = self.model().item(self.currentIndex())
        try:
            fn = itm.fileName()
        except AttributeError:
            fn = itm.dirName()
        package = (
            fn
            if remotefsInterface.isdir(fn)
            else (
                remotefsInterface.dirname(fn)
                if isRemote
                else fn if os.path.isdir(fn) else os.path.dirname(fn)
            )
        )
        res = EricMessageBox.yesNo(
            self,
            self.tr("Package Diagram"),
            self.tr("""Include class attributes?"""),
            yesDefault=True,
        )

        self.packageDiagram = UMLDialog(
            UMLDialogType.PACKAGE_DIAGRAM, self.project, package, self, noAttrs=not res
        )
        self.packageDiagram.show()

    def __showApplicationDiagram(self):
        """
        Private method to handle the application diagram context menu action.
        """
        res = EricMessageBox.yesNo(
            self,
            self.tr("Application Diagram"),
            self.tr("""Include module names?"""),
            yesDefault=True,
        )

        self.applicationDiagram = UMLDialog(
            UMLDialogType.APPLICATION_DIAGRAM, self.project, self, noModules=not res
        )
        self.applicationDiagram.show()

    def __loadDiagram(self):
        """
        Private slot to load a diagram from file.
        """
        from eric7.Graphics.UMLDialog import UMLDialog, UMLDialogType

        self.loadedDiagram = None
        loadedDiagram = UMLDialog(UMLDialogType.NO_DIAGRAM, self.project, parent=self)
        if loadedDiagram.load():
            self.loadedDiagram = loadedDiagram
            self.loadedDiagram.show(fromFile=True)

    ###########################################################################
    ## Methods for the Start submenu
    ###########################################################################

    def __contextMenuRunScript(self):
        """
        Private method to run the editor script.
        """
        fn = self.model().item(self.currentIndex()).fileName()
        ericApp().getObject("DebugUI").doRun(False, script=fn)

    def __contextMenuDebugScript(self):
        """
        Private method to debug the editor script.
        """
        fn = self.model().item(self.currentIndex()).fileName()
        ericApp().getObject("DebugUI").doDebug(False, script=fn)

    def __contextMenuProfileScript(self):
        """
        Private method to profile the editor script.
        """
        fn = self.model().item(self.currentIndex()).fileName()
        ericApp().getObject("DebugUI").doProfile(False, script=fn)

    def __contextMenuCoverageScript(self):
        """
        Private method to run a coverage test of the editor script.
        """
        fn = self.model().item(self.currentIndex()).fileName()
        ericApp().getObject("DebugUI").doCoverage(False, script=fn)

    ###########################################################################
    ## Methods for the Code Formatting submenu
    ###########################################################################

    def __showContextMenuFormatting(self):
        """
        Private slot called before the Code Formatting menu is shown.
        """
        self.showMenu.emit("Formatting", self.formattingMenu)

    def __performFormatWithBlack(self, action):
        """
        Private method to format the selected project sources using the 'Black' tool.

        Following actions are supported.
        <ul>
        <li>BlackFormattingAction.Format - the code reformatting is performed</li>
        <li>BlackFormattingAction.Check - a check is performed, if code formatting
            is necessary</li>
        <li>BlackFormattingAction.Diff - a unified diff of potential code formatting
            changes is generated</li>
        </ul>

        @param action formatting operation to be performed
        @type BlackFormattingAction
        """
        from eric7.CodeFormatting.BlackConfigurationDialog import (
            BlackConfigurationDialog,
        )
        from eric7.CodeFormatting.BlackFormattingDialog import BlackFormattingDialog

        files = [
            itm.fileName()
            for itm in self.getSelectedItems([BrowserFileItem])
            if itm.isPython3File()
        ]
        if not files:
            # called for a directory
            itm = self.model().item(self.currentIndex())
            dirName = itm.dirName()
            files = [
                f
                for f in self.project.getProjectFiles("SOURCES", normalized=True)
                if f.startswith(dirName)
            ]

        vm = ericApp().getObject("ViewManager")
        files = [fn for fn in files if vm.checkFileDirty(fn)]

        if files:
            dlg = BlackConfigurationDialog(withProject=True, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                config = dlg.getConfiguration()

                formattingDialog = BlackFormattingDialog(
                    config, files, project=self.project, action=action, parent=self
                )
                formattingDialog.exec()
        else:
            EricMessageBox.information(
                self,
                self.tr("Code Formatting"),
                self.tr("""There are no files left for reformatting."""),
            )

    def __performImportSortingWithIsort(self, action):
        """
        Private method to sort the import statements of the selected project sources
        using the 'isort' tool.

        Following actions are supported.
        <ul>
        <li>IsortFormattingAction.Sort - the import statement sorting is performed</li>
        <li>IsortFormattingAction.Check - a check is performed, if import statement
            resorting is necessary</li>
        <li>IsortFormattingAction.Diff - a unified diff of potential import statement
            changes is generated</li>
        </ul>

        @param action sorting operation to be performed
        @type IsortFormattingAction
        """
        from eric7.CodeFormatting.IsortConfigurationDialog import (
            IsortConfigurationDialog,
        )
        from eric7.CodeFormatting.IsortFormattingDialog import IsortFormattingDialog

        files = [
            itm.fileName()
            for itm in self.getSelectedItems([BrowserFileItem])
            if itm.isPython3File()
        ]
        if not files:
            # called for a directory
            itm = self.model().item(self.currentIndex())
            dirName = itm.dirName()
            files = [
                f
                for f in self.project.getProjectFiles("SOURCES", normalized=True)
                if f.startswith(dirName)
            ]

        vm = ericApp().getObject("ViewManager")
        files = [fn for fn in files if vm.checkFileDirty(fn)]

        if files:
            dlg = IsortConfigurationDialog(withProject=True, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                config = dlg.getConfiguration()

                formattingDialog = IsortFormattingDialog(
                    config, files, project=self.project, action=action, parent=self
                )
                formattingDialog.exec()
        else:
            EricMessageBox.information(
                self,
                self.tr("Import Sorting"),
                self.tr("""There are no files left for import statement sorting."""),
            )
