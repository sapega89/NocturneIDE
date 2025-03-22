# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class used to display the translations part of the
project.
"""

import contextlib
import fnmatch
import functools
import os
import shutil

from PyQt6.QtCore import QEventLoop, QProcess, Qt, pyqtSignal
from PyQt6.QtGui import QCursor, QGuiApplication
from PyQt6.QtWidgets import QDialog, QMenu

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricOverrideCursor import EricOverridenCursor
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities, QtUtilities
from eric7.UI.DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog
from eric7.UI.NotificationWidget import NotificationTypes

from .FileCategoryRepositoryItem import FileCategoryRepositoryItem
from .ProjectBaseBrowser import ProjectBaseBrowser
from .ProjectBrowserModel import (
    ProjectBrowserFileItem,
    ProjectBrowserSimpleDirectoryItem,
)
from .ProjectBrowserRepositoryItem import ProjectBrowserRepositoryItem


class ProjectTranslationsBrowser(ProjectBaseBrowser):
    """
    A class used to display the translations part of the project.

    @signal appendStdout(str) emitted after something was received from
        a QProcess on stdout
    @signal appendStderr(str) emitted after something was received from
        a QProcess on stderr
    @signal showMenu(str, QMenu) emitted when a menu is about to be shown.
        The name of the menu and a reference to the menu are given.
    """

    appendStdout = pyqtSignal(str)
    appendStderr = pyqtSignal(str)
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
        ProjectBaseBrowser.__init__(self, project, "translation", parent)
        self.isTranslationsBrowser = True

        self.selectedItemsFilter = [
            ProjectBrowserFileItem,
            ProjectBrowserSimpleDirectoryItem,
        ]

        self.setWindowTitle(self.tr("Translations"))

        self.setWhatsThis(
            self.tr(
                """<b>Project Translations Browser</b>"""
                """<p>This allows to easily see all translations contained in"""
                """ the current project. Several actions can be executed via"""
                """ the context menu.</p>"""
            )
        )

        self.__lreleaseProcesses = []
        self.__pylupdateProcesses = []
        self.lreleaseProcRunning = False
        self.pylupdateProcRunning = False
        self.__tmpProjects = []

        # Add the file category handled by the browser.
        project.addFileCategory(
            "TRANSLATIONS",
            FileCategoryRepositoryItem(
                fileCategoryFilterTemplate=self.tr("Translation Files ({0})"),
                fileCategoryUserString=self.tr("Translation Files"),
                fileCategoryTyeString=self.tr("Translations"),
                fileCategoryExtensions=["*.ts", "*.qm"],
            ),
        )

        # Add the project browser type to the browser type repository.
        projectBrowser.addTypedProjectBrowser(
            "translations",
            ProjectBrowserRepositoryItem(
                projectBrowser=self,
                projectBrowserUserString=self.tr("Translations Browser"),
                priority=75,
                fileCategory="TRANSLATIONS",
                fileFilter="translation",
                getIcon=self.getIcon,
            ),
        )

        # Connect signals of Project.
        project.projectClosed.connect(self._projectClosed)
        project.projectOpened.connect(self._projectOpened)
        project.newProject.connect(self._newProject)
        project.reinitVCS.connect(self._initMenusAndVcs)
        project.projectPropertiesChanged.connect(self._initMenusAndVcs)

        # Connect signals of ProjectBrowser.
        projectBrowser.preferencesChanged.connect(self.handlePreferencesChanged)

        # Connect some of our own signals.
        self.appendStderr.connect(projectBrowser.appendStderr)
        self.appendStdout.connect(projectBrowser.appendStdout)
        self.closeSourceWindow.connect(projectBrowser.closeSourceWindow)
        self.sourceFile[str].connect(projectBrowser.sourceFile[str])
        self.linguistFile.connect(projectBrowser.linguistFile)
        self.trpreview[list].connect(projectBrowser.trpreview[list])
        self.trpreview[list, bool].connect(projectBrowser.trpreview[list, bool])

    def getIcon(self):
        """
        Public method to get an icon for the project browser.

        @return icon for the browser
        @rtype QIcon
        """
        return EricPixmapCache.getIcon("projectTranslations")

    def _createPopupMenus(self):
        """
        Protected overloaded method to generate the popup menu.
        """
        self.menuActions = []
        self.multiMenuActions = []
        self.dirMenuActions = []
        self.dirMultiMenuActions = []

        self.tsMenuActions = []
        self.qmMenuActions = []
        self.tsprocMenuActions = []
        self.qmprocMenuActions = []

        self.tsMultiMenuActions = []
        self.qmMultiMenuActions = []
        self.tsprocMultiMenuActions = []
        self.qmprocMultiMenuActions = []

        self.tsprocDirMenuActions = []
        self.qmprocDirMenuActions = []

        self.tsprocBackMenuActions = []
        self.qmprocBackMenuActions = []

        self.menu = QMenu(self)
        if self.project.getProjectType() in [
            "PyQt5",
            "PyQt5C",
            "PyQt6",
            "PyQt6C",
            "E7Plugin",
            "PySide2",
            "PySide2C",
            "PySide6",
            "PySide6C",
        ]:
            if FileSystemUtilities.isRemoteFileName(self.project.getProjectPath()):
                act = self.menu.addAction(
                    self.tr("Open in Editor"), self.__openFileInEditor
                )
                self.tsMenuActions.append(act)
                self.menu.addSeparator()
            else:
                act = self.menu.addAction(
                    self.tr("Generate translation"), self.__generateSelected
                )
                self.tsMenuActions.append(act)
                self.tsprocMenuActions.append(act)
                act = self.menu.addAction(
                    self.tr("Generate translation (with obsolete)"),
                    self.__generateObsoleteSelected,
                )
                self.tsMenuActions.append(act)
                self.tsprocMenuActions.append(act)
                act = self.menu.addAction(
                    self.tr("Generate all translations"), self.__generateAll
                )
                self.tsprocMenuActions.append(act)
                act = self.menu.addAction(
                    self.tr("Generate all translations (with obsolete)"),
                    self.__generateObsoleteAll,
                )
                self.tsprocMenuActions.append(act)
                self.menu.addSeparator()
                self.__qtLinguistAct = self.menu.addAction(
                    self.tr("Open in Qt-Linguist"), self._openItem
                )
                self.tsMenuActions.append(self.__qtLinguistAct)
                act = self.menu.addAction(
                    self.tr("Open in Editor"), self.__openFileInEditor
                )
                self.tsMenuActions.append(act)
                self.menu.addSeparator()
                act = self.menu.addAction(
                    self.tr("Release translation"), self.__releaseSelected
                )
                self.tsMenuActions.append(act)
                self.qmprocMenuActions.append(act)
                act = self.menu.addAction(
                    self.tr("Release all translations"), self.__releaseAll
                )
                self.qmprocMenuActions.append(act)
                self.menu.addSeparator()
                act = self.menu.addAction(
                    self.tr("Preview translation"), self.__TRPreview
                )
                self.qmMenuActions.append(act)
                act = self.menu.addAction(
                    self.tr("Preview all translations"), self.__TRPreviewAll
                )
                self.menu.addSeparator()
        else:
            if FileSystemUtilities.isRemoteFileName(self.project.getProjectPath()):
                act = self.menu.addAction(
                    self.tr("Open in Editor"), self.__openFileInEditor
                )
                self.tsMenuActions.append(act)
                self.menu.addSeparator()
            else:
                if self.hooks["extractMessages"] is not None:
                    act = self.menu.addAction(
                        self.hooksMenuEntries.get(
                            "extractMessages", self.tr("Extract messages")
                        ),
                        self.__extractMessages,
                    )
                    self.menuActions.append(act)
                    self.menu.addSeparator()
                if self.hooks["generateSelected"] is not None:
                    act = self.menu.addAction(
                        self.hooksMenuEntries.get(
                            "generateSelected", self.tr("Generate translation")
                        ),
                        self.__generateSelected,
                    )
                    self.tsMenuActions.append(act)
                    self.tsprocMenuActions.append(act)
                if self.hooks["generateSelectedWithObsolete"] is not None:
                    act = self.menu.addAction(
                        self.hooksMenuEntries.get(
                            "generateSelectedWithObsolete",
                            self.tr("Generate translation (with obsolete)"),
                        ),
                        self.__generateObsoleteSelected,
                    )
                    self.tsMenuActions.append(act)
                    self.tsprocMenuActions.append(act)
                if self.hooks["generateAll"] is not None:
                    act = self.menu.addAction(
                        self.hooksMenuEntries.get(
                            "generateAll", self.tr("Generate all translations")
                        ),
                        self.__generateAll,
                    )
                    self.tsprocMenuActions.append(act)
                if self.hooks["generateAllWithObsolete"] is not None:
                    act = self.menu.addAction(
                        self.hooksMenuEntries.get(
                            "generateAllWithObsolete",
                            self.tr("Generate all translations (with obsolete)"),
                        ),
                        self.__generateObsoleteAll,
                    )
                    self.tsprocMenuActions.append(act)
                self.menu.addSeparator()
                if self.hooks["open"] is not None:
                    act = self.menu.addAction(
                        self.hooksMenuEntries.get("open", self.tr("Open")),
                        self._openItem,
                    )
                    self.tsMenuActions.append(act)
                act = self.menu.addAction(
                    self.tr("Open in Editor"), self.__openFileInEditor
                )
                self.tsMenuActions.append(act)
                self.menu.addSeparator()
                if self.hooks["releaseSelected"] is not None:
                    act = self.menu.addAction(
                        self.hooksMenuEntries.get(
                            "releaseSelected", self.tr("Release translation")
                        ),
                        self.__releaseSelected,
                    )
                    self.tsMenuActions.append(act)
                    self.qmprocMenuActions.append(act)
                if self.hooks["releaseAll"] is not None:
                    act = self.menu.addAction(
                        self.hooksMenuEntries.get(
                            "releaseAll", self.tr("Release all translations")
                        ),
                        self.__releaseAll,
                    )
                    self.qmprocMenuActions.append(act)
                self.menu.addSeparator()
        act = self.menu.addAction(
            self.tr("Remove from project"), self.__removeLanguageFile
        )
        self.menuActions.append(act)
        act = self.menu.addAction(self.tr("Delete"), self.__deleteLanguageFile)
        self.menuActions.append(act)
        self.menu.addSeparator()
        self.__addTranslationAct = self.menu.addAction(
            self.tr("New translation..."), self.project.addLanguage
        )
        self.menu.addAction(
            self.tr("Add translation files..."), self.__addTranslationFiles
        )
        self.menu.addSeparator()
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            self.menu.addAction(
                self.tr("Show in File Manager"), self._showInFileManager
            )
        self.menu.addAction(self.tr("Copy Path to Clipboard"), self._copyToClipboard)
        self.menu.addSeparator()
        self.menu.addAction(self.tr("Configure..."), self._configure)

        self.backMenu = QMenu(self)
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            if self.project.getProjectType() in [
                "PyQt5",
                "PyQt5C",
                "PyQt6",
                "PyQt6C",
                "E7Plugin",
                "PySide2",
                "PySide2C",
                "PySide6",
                "PySide6C",
            ]:
                act = self.backMenu.addAction(
                    self.tr("Generate all translations"), self.__generateAll
                )
                self.tsprocBackMenuActions.append(act)
                act = self.backMenu.addAction(
                    self.tr("Generate all translations (with obsolete)"),
                    self.__generateObsoleteAll,
                )
                self.tsprocBackMenuActions.append(act)
                act = self.backMenu.addAction(
                    self.tr("Release all translations"), self.__releaseAll
                )
                self.qmprocBackMenuActions.append(act)
                self.backMenu.addSeparator()
                act = self.backMenu.addAction(
                    self.tr("Preview all translations"), self.__TRPreview
                )
            else:
                if self.hooks["extractMessages"] is not None:
                    act = self.backMenu.addAction(
                        self.hooksMenuEntries.get(
                            "extractMessages", self.tr("Extract messages")
                        ),
                        self.__extractMessages,
                    )
                    self.backMenu.addSeparator()
                if self.hooks["generateAll"] is not None:
                    act = self.backMenu.addAction(
                        self.hooksMenuEntries.get(
                            "generateAll", self.tr("Generate all translations")
                        ),
                        self.__generateAll,
                    )
                    self.tsprocBackMenuActions.append(act)
                if self.hooks["generateAllWithObsolete"] is not None:
                    act = self.backMenu.addAction(
                        self.hooksMenuEntries.get(
                            "generateAllWithObsolete",
                            self.tr("Generate all translations (with obsolete)"),
                        ),
                        self.__generateObsoleteAll,
                    )
                    self.tsprocBackMenuActions.append(act)
                if self.hooks["releaseAll"] is not None:
                    act = self.backMenu.addAction(
                        self.hooksMenuEntries.get(
                            "releaseAll", self.tr("Release all translations")
                        ),
                        self.__releaseAll,
                    )
                    self.qmprocBackMenuActions.append(act)
            self.backMenu.addSeparator()
        self.__addTranslationBackAct = self.backMenu.addAction(
            self.tr("New translation..."), self.project.addLanguage
        )
        self.backMenu.addAction(
            self.tr("Add translation files..."), self.__addTranslationFiles
        )
        self.backMenu.addSeparator()
        self.backMenu.addAction(
            self.tr("Show in File Manager"), self._showProjectInFileManager
        )
        self.backMenu.addSeparator()
        self.backMenu.addAction(self.tr("Configure..."), self._configure)
        self.backMenu.setEnabled(False)

        # create the menu for multiple selected files
        self.multiMenu = QMenu(self)
        if self.project.getProjectType() in [
            "PyQt5",
            "PyQt5C",
            "PyQt6",
            "PyQt6C",
            "E7Plugin",
            "PySide2",
            "PySide2C",
            "PySide6",
            "PySide6C",
        ]:
            if FileSystemUtilities.isRemoteFileName(self.project.getProjectPath()):
                act = self.multiMenu.addAction(
                    self.tr("Open in Editor"), self.__openFileInEditor
                )
                self.tsMultiMenuActions.append(act)
                self.multiMenu.addSeparator()
            else:
                act = self.multiMenu.addAction(
                    self.tr("Generate translations"), self.__generateSelected
                )
                self.tsMultiMenuActions.append(act)
                self.tsprocMultiMenuActions.append(act)
                act = self.multiMenu.addAction(
                    self.tr("Generate translations (with obsolete)"),
                    self.__generateObsoleteSelected,
                )
                self.tsMultiMenuActions.append(act)
                self.tsprocMultiMenuActions.append(act)
                self.multiMenu.addSeparator()
                self.__qtLinguistMultiAct = self.multiMenu.addAction(
                    self.tr("Open in Qt-Linguist"), self._openItem
                )
                self.tsMultiMenuActions.append(self.__qtLinguistMultiAct)
                act = self.multiMenu.addAction(
                    self.tr("Open in Editor"), self.__openFileInEditor
                )
                self.tsMultiMenuActions.append(act)
                self.multiMenu.addSeparator()
                act = self.multiMenu.addAction(
                    self.tr("Release translations"), self.__releaseSelected
                )
                self.tsMultiMenuActions.append(act)
                self.qmprocMultiMenuActions.append(act)
                self.multiMenu.addSeparator()
                act = self.multiMenu.addAction(
                    self.tr("Preview translations"), self.__TRPreview
                )
                self.qmMultiMenuActions.append(act)
        else:
            if FileSystemUtilities.isRemoteFileName(self.project.getProjectPath()):
                act = self.multiMenu.addAction(
                    self.tr("Open in Editor"), self.__openFileInEditor
                )
                self.tsMultiMenuActions.append(act)
                self.multiMenu.addSeparator()
            else:
                if self.hooks["extractMessages"] is not None:
                    act = self.multiMenu.addAction(
                        self.hooksMenuEntries.get(
                            "extractMessages", self.tr("Extract messages")
                        ),
                        self.__extractMessages,
                    )
                    self.multiMenuActions.append(act)
                    self.multiMenu.addSeparator()
                if self.hooks["generateSelected"] is not None:
                    act = self.multiMenu.addAction(
                        self.hooksMenuEntries.get(
                            "generateSelected", self.tr("Generate translations")
                        ),
                        self.__generateSelected,
                    )
                    self.tsMultiMenuActions.append(act)
                    self.tsprocMultiMenuActions.append(act)
                if self.hooks["generateSelectedWithObsolete"] is not None:
                    act = self.multiMenu.addAction(
                        self.hooksMenuEntries.get(
                            "generateSelectedWithObsolete",
                            self.tr("Generate translations (with obsolete)"),
                        ),
                        self.__generateObsoleteSelected,
                    )
                    self.tsMultiMenuActions.append(act)
                    self.tsprocMultiMenuActions.append(act)
                self.multiMenu.addSeparator()
                if self.hooks["open"] is not None:
                    act = self.multiMenu.addAction(
                        self.hooksMenuEntries.get("open", self.tr("Open")),
                        self._openItem,
                    )
                    self.tsMultiMenuActions.append(act)
                act = self.multiMenu.addAction(
                    self.tr("Open in Editor"), self.__openFileInEditor
                )
                self.tsMultiMenuActions.append(act)
                self.multiMenu.addSeparator()
                if self.hooks["releaseSelected"] is not None:
                    act = self.multiMenu.addAction(
                        self.hooksMenuEntries.get(
                            "releaseSelected", self.tr("Release translations")
                        ),
                        self.__releaseSelected,
                    )
                    self.tsMultiMenuActions.append(act)
                    self.qmprocMultiMenuActions.append(act)
        self.multiMenu.addSeparator()
        act = self.multiMenu.addAction(
            self.tr("Remove from project"), self.__removeLanguageFile
        )
        self.multiMenuActions.append(act)
        act = self.multiMenu.addAction(self.tr("Delete"), self.__deleteLanguageFile)
        self.multiMenuActions.append(act)
        self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.tr("Configure..."), self._configure)

        self.dirMenu = QMenu(self)
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            if self.project.getProjectType() in [
                "PyQt5",
                "PyQt5C",
                "PyQt6",
                "PyQt6C",
                "E7Plugin",
                "PySide2",
                "PySide2C",
                "PySide6",
                "PySide6C",
            ]:
                act = self.dirMenu.addAction(
                    self.tr("Generate all translations"), self.__generateAll
                )
                self.tsprocDirMenuActions.append(act)
                act = self.dirMenu.addAction(
                    self.tr("Generate all translations (with obsolete)"),
                    self.__generateObsoleteAll,
                )
                self.tsprocDirMenuActions.append(act)
                act = self.dirMenu.addAction(
                    self.tr("Release all translations"), self.__releaseAll
                )
                self.qmprocDirMenuActions.append(act)
                self.dirMenu.addSeparator()
                act = self.dirMenu.addAction(
                    self.tr("Preview all translations"), self.__TRPreview
                )
            else:
                if self.hooks["extractMessages"] is not None:
                    act = self.dirMenu.addAction(
                        self.hooksMenuEntries.get(
                            "extractMessages", self.tr("Extract messages")
                        ),
                        self.__extractMessages,
                    )
                    self.dirMenuActions.append(act)
                    self.dirMenu.addSeparator()
                if self.hooks["generateAll"] is not None:
                    act = self.dirMenu.addAction(
                        self.hooksMenuEntries.get(
                            "generateAll", self.tr("Generate all translations")
                        ),
                        self.__generateAll,
                    )
                    self.tsprocDirMenuActions.append(act)
                if self.hooks["generateAllWithObsolete"] is not None:
                    act = self.dirMenu.addAction(
                        self.hooksMenuEntries.get(
                            "generateAllWithObsolete",
                            self.tr("Generate all translations (with obsolete)"),
                        ),
                        self.__generateObsoleteAll,
                    )
                    self.tsprocDirMenuActions.append(act)
                if self.hooks["releaseAll"] is not None:
                    act = self.dirMenu.addAction(
                        self.hooksMenuEntries.get(
                            "releaseAll", self.tr("Release all translations")
                        ),
                        self.__releaseAll,
                    )
                    self.qmprocDirMenuActions.append(act)
        self.dirMenu.addSeparator()
        act = self.dirMenu.addAction(self.tr("Delete"), self._deleteDirectory)
        self.dirMenuActions.append(act)
        self.dirMenu.addSeparator()
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            self.__addTranslationDirAct = self.dirMenu.addAction(
                self.tr("New translation..."), self.project.addLanguage
            )
            self.dirMenu.addAction(
                self.tr("Add translation files..."), self.__addTranslationFiles
            )
            self.dirMenu.addSeparator()
            self.dirMenu.addAction(
                self.tr("Show in File Manager"), self._showInFileManager
            )
        self.dirMenu.addAction(self.tr("Copy Path to Clipboard"), self._copyToClipboard)
        self.dirMenu.addSeparator()
        self.dirMenu.addAction(self.tr("Configure..."), self._configure)

        self.dirMultiMenu = None

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
        if self.project.getProjectType() in [
            "PyQt5",
            "PyQt5C",
            "PyQt6",
            "PyQt6C",
            "E7Plugin",
            "PySide2",
            "PySide2C",
            "PySide6",
            "PySide6C",
        ]:
            tsFiles = 0
            qmFiles = 0
            itmList = self.getSelectedItems()
            for itm in itmList[:]:
                if itm.fileName().endswith(".ts"):
                    tsFiles += 1
                elif itm.fileName().endswith(".qm"):
                    qmFiles += 1
            if (tsFiles > 0 and qmFiles > 0) or (tsFiles == 0 and qmFiles == 0):
                for act in self.tsMenuActions + self.qmMenuActions:
                    act.setEnabled(False)
            elif tsFiles > 0:
                for act in self.tsMenuActions:
                    act.setEnabled(True)
                if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
                    self.__qtLinguistAct.setEnabled(QtUtilities.hasQtLinguist())
                    self.__qtLinguistMultiAct.setEnabled(QtUtilities.hasQtLinguist())
                for act in self.qmMenuActions:
                    act.setEnabled(False)
            elif qmFiles > 0:
                for act in self.tsMenuActions:
                    act.setEnabled(False)
                for act in self.qmMenuActions:
                    act.setEnabled(True)
            if self.pylupdateProcRunning:
                for act in self.tsprocMenuActions:
                    act.setEnabled(False)
            if self.lreleaseProcRunning:
                for act in self.qmprocMenuActions:
                    act.setEnabled(True)
        self.__addTranslationAct.setEnabled(self.project.getTranslationPattern() != "")

        ProjectBaseBrowser._showContextMenu(self, self.menu)

        self.showMenu.emit("Main", self.menu)

    def __showContextMenuMulti(self):
        """
        Private slot called by the multiMenu aboutToShow signal.
        """
        if self.project.getProjectType() in [
            "PyQt5",
            "PyQt5C",
            "PyQt6",
            "PyQt6C",
            "E7Plugin",
            "PySide2",
            "PySide2C",
            "PySide6",
            "PySide6C",
        ]:
            tsFiles = 0
            qmFiles = 0
            itmList = self.getSelectedItems()
            for itm in itmList[:]:
                if itm.fileName().endswith(".ts"):
                    tsFiles += 1
                elif itm.fileName().endswith(".qm"):
                    qmFiles += 1
            if (tsFiles > 0 and qmFiles > 0) or (tsFiles == 0 and qmFiles == 0):
                for act in self.tsMultiMenuActions + self.qmMultiMenuActions:
                    act.setEnabled(False)
            elif tsFiles > 0:
                for act in self.tsMultiMenuActions:
                    act.setEnabled(True)
                for act in self.qmMultiMenuActions:
                    act.setEnabled(False)
            elif qmFiles > 0:
                for act in self.tsMultiMenuActions:
                    act.setEnabled(False)
                for act in self.qmMultiMenuActions:
                    act.setEnabled(True)
            if self.pylupdateProcRunning:
                for act in self.tsprocMultiMenuActions:
                    act.setEnabled(False)
            if self.lreleaseProcRunning:
                for act in self.qmprocMultiMenuActions:
                    act.setEnabled(True)

        ProjectBaseBrowser._showContextMenuMulti(self, self.multiMenu)

        self.showMenu.emit("MainMulti", self.multiMenu)

    def __showContextMenuDir(self):
        """
        Private slot called by the dirMenu aboutToShow signal.
        """
        if FileSystemUtilities.isPlainFileName(
            self.project.getProjectPath()
        ) and self.project.getProjectType() in [
            "PyQt5",
            "PyQt5C",
            "PyQt6",
            "PyQt6C",
            "E7Plugin",
            "PySide2",
            "PySide2C",
            "PySide6",
            "PySide6C",
        ]:
            if self.pylupdateProcRunning:
                for act in self.tsprocDirMenuActions:
                    act.setEnabled(False)
            if self.lreleaseProcRunning:
                for act in self.qmprocDirMenuActions:
                    act.setEnabled(True)
        self.__addTranslationDirAct.setEnabled(
            self.project.getTranslationPattern() != ""
        )

        ProjectBaseBrowser._showContextMenuDir(self, self.dirMenu)

        self.showMenu.emit("MainDir", self.dirMenu)

    def __showContextMenuBack(self):
        """
        Private slot called by the backMenu aboutToShow signal.
        """
        if FileSystemUtilities.isPlainFileName(
            self.project.getProjectPath()
        ) and self.project.getProjectType() in [
            "PyQt5",
            "PyQt5C",
            "PyQt6",
            "PyQt6C",
            "E7Plugin",
            "PySide2",
            "PySide2C",
            "PySide6",
            "PySide6C",
        ]:
            if self.pylupdateProcRunning:
                for act in self.tsprocBackMenuActions:
                    act.setEnabled(False)
            if self.lreleaseProcRunning:
                for act in self.qmprocBackMenuActions:
                    act.setEnabled(True)
        self.__addTranslationBackAct.setEnabled(
            self.project.getTranslationPattern() != ""
        )

        self.showMenu.emit("MainBack", self.backMenu)

    def __addTranslationFiles(self):
        """
        Private method to add translation files to the project.
        """
        self.project.addFiles("TRANSLATIONS", self.currentDirectory())

    def _openItem(self):
        """
        Protected slot to handle the open popup menu entry.
        """
        itmList = self.getSelectedItems()
        for itm in itmList:
            if isinstance(itm, ProjectBrowserFileItem):
                # hook support
                if self.hooks["open"] is not None:
                    self.hooks["open"](itm.fileName())
                elif itm.isLinguistFile() and FileSystemUtilities.isPlainFileName(
                    itm.fileName()
                ):
                    if itm.fileExt() == ".ts":
                        self.linguistFile.emit(itm.fileName())
                    else:
                        self.trpreview.emit([itm.fileName()])
                else:
                    self.sourceFile.emit(itm.fileName())

    def __openFileInEditor(self):
        """
        Private slot to handle the Open in Editor menu action.
        """
        itmList = self.getSelectedItems()
        for itm in itmList[:]:
            self.sourceFile.emit(itm.fileName())

    def __removeLanguageFile(self):
        """
        Private method to remove a translation from the project.
        """
        itmList = self.getSelectedItems()

        for itm in itmList[:]:
            fn = itm.fileName()
            self.closeSourceWindow.emit(fn)
            self.project.removeLanguageFile(fn)

    def __deleteLanguageFile(self):
        """
        Private method to delete a translation file from the project.
        """
        itmList = self.getSelectedItems()

        translationFiles = [itm.fileName() for itm in itmList]

        dlg = DeleteFilesConfirmationDialog(
            self.parent(),
            self.tr("Delete translation files"),
            self.tr(
                "Do you really want to delete these translation files"
                " from the project?"
            ),
            translationFiles,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            for fn in translationFiles:
                self.closeSourceWindow.emit(fn)
                self.project.deleteLanguageFile(fn)

    def __TRPreview(self, previewAll=False):
        """
        Private slot to handle the Preview translations action.

        @param previewAll flag indicating, that all translations
            should be previewed
        @type bool
        """
        fileNames = []
        itmList = self.getSelectedItems()
        if itmList and not previewAll:
            for itm in itmList:
                if isinstance(itm, ProjectBrowserSimpleDirectoryItem):
                    dname = self.project.getRelativePath(itm.dirName())
                    trfiles = sorted(
                        self.project.getProjectData(dataKey="TRANSLATIONS")[:]
                    )
                    for trfile in trfiles:
                        if trfile.startswith(dname) and trfile not in fileNames:
                            fileNames.append(os.path.join(self.project.ppath, trfile))
                else:
                    fn = itm.fileName()
                    if fn not in fileNames:
                        fileNames.append(os.path.join(self.project.ppath, fn))
        else:
            trfiles = sorted(self.project.getProjectData(dataKey="TRANSLATIONS")[:])
            fileNames.extend(
                [
                    os.path.join(self.project.ppath, trfile)
                    for trfile in trfiles
                    if trfile.endswith(".qm")
                ]
            )
        self.trpreview[list, bool].emit(fileNames, True)

    def __TRPreviewAll(self):
        """
        Private slot to handle the Preview all translations action.
        """
        self.__TRPreview(True)

    ###########################################################################
    ##  Methods to support the generation and release commands
    ###########################################################################

    def __writeTempProjectFile(self, langs, filterList):
        """
        Private method to write a temporary project file suitable for
        pylupdate and lrelease.

        @param langs list of languages to include in the process. An empty
            list (default) means that all translations should be included.
        @type list of ProjectBrowserFileItem
        @param filterList list of source file extension that should be
            considered
        @type list of str
        @return flag indicating success
        @rtype bool
        """
        path, _ext = os.path.splitext(self.project.pfile)
        pfile = "{0}_e4x.pro".format(path)

        # only consider files satisfying the filter criteria
        _sources = [
            s
            for s in self.project.getProjectData(dataKey="SOURCES")
            if os.path.splitext(s)[1] in filterList
        ]
        sources = []
        for s in _sources:
            addIt = True
            for transExcept in self.project.getProjectData(
                dataKey="TRANSLATIONEXCEPTIONS"
            ):
                if s.startswith(transExcept):
                    addIt = False
                    break
            if addIt:
                sources.append(s)

        _forms = [
            f for f in self.project.getProjectData(dataKey="FORMS") if f.endswith(".ui")
        ]
        forms = []
        for f in _forms:
            addIt = True
            for transExcept in self.project.getProjectData(
                dataKey="TRANSLATIONEXCEPTIONS"
            ):
                if f.startswith(transExcept):
                    addIt = False
                    break
            if addIt:
                forms.append(f)

        if langs:
            langs = [
                self.project.getRelativePath(lang.fileName())
                for lang in langs
                if lang.fileName().endswith(".ts")
            ]
        else:
            try:
                pattern = self.project.getProjectData(
                    dataKey="TRANSLATIONPATTERN"
                ).replace("%language%", "*")
                langs = [
                    lang
                    for lang in self.project.getProjectData(dataKey="TRANSLATIONS")
                    if fnmatch.fnmatch(lang, pattern)
                ]
            except IndexError:
                langs = []
        if not langs:
            EricMessageBox.warning(
                self,
                self.tr("Write temporary project file"),
                self.tr("""No translation files (*.ts) selected."""),
            )
            return False

        # create a prefix relative from the *.ts down to the project path
        langLevel = {}
        for lang in langs:
            level = lang.count(os.sep)
            lst = langLevel.get(level, [])
            lst.append(lang)
            langLevel[level] = lst

        for level, langs in langLevel.items():
            prefix = "../" * level
            sections = [("SOURCES", [prefix + src for src in sources])]
            sections.append(("FORMS", [prefix + form for form in forms]))
            sections.append(("TRANSLATIONS", [prefix + lang for lang in langs]))

            directory, name = os.path.split(pfile)
            outFile = os.path.join(directory, os.path.dirname(langs[0]), name)
            outDir = os.path.dirname(outFile)
            if not os.path.exists(outDir):
                os.makedirs(outDir)
            try:
                with open(outFile, "w", encoding="utf-8") as pf:
                    for key, fileList in sections:
                        if len(fileList) > 0:
                            pf.write("{0} = ".format(key))
                            pf.write(
                                " \\\n\t".join(
                                    [f.replace(os.sep, "/") for f in fileList]
                                )
                            )
                            pf.write("\n\n")

                self.__tmpProjects.append(outFile)
            except OSError:
                EricMessageBox.critical(
                    self,
                    self.tr("Write temporary project file"),
                    self.tr(
                        "<p>The temporary project file <b>{0}</b> could not"
                        " be written.</p>"
                    ).format(outFile),
                )

        if len(self.__tmpProjects) == 0:
            return False

        return True

    def __readStdoutLupdate(self, proc):
        """
        Private slot to handle the readyReadStandardOutput signal of the
        pylupdate process.

        @param proc reference to the process
        @type QProcess
        """
        out = self.__readStdout(proc, "{0}: ".format(self.pylupdate))
        for index in range(len(self.__pylupdateProcesses)):
            if proc is self.__pylupdateProcesses[index][0]:
                self.__pylupdateProcesses[index][2].append(out)
                break

    def __readStdoutLrelease(self, proc):
        """
        Private slot to handle the readyReadStandardOutput signal of the
        lrelease process.

        @param proc reference to the process
        @type QProcess
        """
        out = self.__readStdout(proc, "lrelease: ")
        for index in range(len(self.__lreleaseProcesses)):
            if proc is self.__lreleaseProcesses[index][0]:
                self.__lreleaseProcesses[index][1].append(out)
                break

    def __readStdout(self, proc, ps):
        """
        Private method to read from a process' stdout channel.

        @param proc process to read from
        @type QProcess
        @param ps prompt string
        @type str
        @return string read from the process
        @rtype str
        """
        ioEncoding = Preferences.getSystem("IOEncoding")
        out = ""

        proc.setReadChannel(QProcess.ProcessChannel.StandardOutput)
        while proc and proc.canReadLine():
            out += ps
            output = str(proc.readLine(), ioEncoding, "replace")
            out += output

        return out

    def __readStderrLupdate(self, proc):
        """
        Private slot to handle the readyReadStandardError signal of the
        pylupdate5 / pylupdate6 / pyside2-lupdate / pyside6-lupdate process.

        @param proc reference to the process
        @type QProcess
        """
        self.__readStderr(proc, "{0}: ".format(self.pylupdate))

    def __readStderrLrelease(self, proc):
        """
        Private slot to handle the readyReadStandardError signal of the
        lrelease process.

        @param proc reference to the process
        @type QProcess
        """
        self.__readStderr(proc, "lrelease: ")

    def __readStderr(self, proc, ps):
        """
        Private method to read from a process' stderr channel.

        @param proc process to read from
        @type QProcess
        @param ps propmt string
        @type str
        """
        ioEncoding = Preferences.getSystem("IOEncoding")

        proc.setReadChannel(QProcess.ProcessChannel.StandardError)
        while proc and proc.canReadLine():
            s = ps
            error = str(proc.readLine(), ioEncoding, "replace")
            s += error
            self.appendStderr.emit(s)

    ###########################################################################
    ##  Methods for the generation commands
    ###########################################################################

    def __extractMessages(self):
        """
        Private slot to extract the messages to form a messages template file.
        """
        if self.hooks["extractMessages"] is not None:
            self.hooks["extractMessages"]()

    def __generateTSFileDone(self, proc, exitCode, exitStatus):
        """
        Private slot to handle the finished signal of the pylupdate process.

        @param proc reference to the process
        @type QProcess
        @param exitCode exit code of the process
        @type int
        @param exitStatus exit status of the process
        @type QProcess.ExitStatus
        """
        ui = ericApp().getObject("UserInterface")
        if exitStatus == QProcess.ExitStatus.NormalExit and exitCode == 0:
            ui.showNotification(
                EricPixmapCache.getPixmap("linguist48"),
                self.tr("Translation file generation"),
                self.tr(
                    "The generation of the translation files (*.ts) was successful."
                ),
            )
        else:
            if exitStatus == QProcess.ExitStatus.CrashExit:
                info = self.tr(" The process has crashed.")
            else:
                info = ""
            ui.showNotification(
                EricPixmapCache.getPixmap("linguist48"),
                self.tr("Translation file generation"),
                self.tr(
                    "The generation of the translation files (*.ts) has failed.{0}"
                ).format(info),
                kind=NotificationTypes.CRITICAL,
                timeout=0,
            )

        for index in range(len(self.__pylupdateProcesses)):
            if proc is self.__pylupdateProcesses[index][0]:
                processData = self.__pylupdateProcesses[index]
                tmpProjectFile = processData[1]
                if tmpProjectFile:
                    with contextlib.suppress(OSError):
                        self.__tmpProjects.remove(tmpProjectFile)
                        os.remove(tmpProjectFile)

                if processData[2]:
                    self.appendStdout.emit("".join(processData[2]))

                self.__pylupdateProcesses.remove(processData)
                break

        if not self.__pylupdateProcesses:
            # all done
            self.pylupdateProcRunning = False

            QGuiApplication.restoreOverrideCursor()
            QGuiApplication.processEvents(
                QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
            )

    def __generateTSFile(self, noobsolete=False, generateAll=True):
        """
        Private method used to run pylupdate5 / pylupdate6 / pyside2-lupdate /
        pyside6-lupdate to generate the .ts files.

        @param noobsolete flag indicating whether obsolete entries should be
            kept
        @type bool
        @param generateAll flag indicating whether all translations should be
            generated
        @type bool
        """
        langs = [] if generateAll else self.getSelectedItems()

        # Hook support
        if generateAll:
            if noobsolete:
                if self.hooks["generateAll"] is not None:
                    self.hooks["generateAll"](
                        self.project.getProjectData(dataKey="TRANSLATIONS")
                    )
                    return
            else:
                if self.hooks["generateAllWithObsolete"] is not None:
                    self.hooks["generateAllWithObsolete"](
                        self.project.getProjectData(dataKey="TRANSLATIONS")
                    )
                    return
        else:
            if noobsolete:
                if self.hooks["generateSelected"] is not None:
                    li = [
                        self.project.getRelativePath(lang.fileName()) for lang in langs
                    ]
                    self.hooks["generateSelected"](li)
                    return
            else:
                if self.hooks["generateSelectedWithObsolete"] is not None:
                    li = [
                        self.project.getRelativePath(lang.fileName()) for lang in langs
                    ]
                    self.hooks["generateSelectedWithObsolete"](li)
                    return

        if self.project.getProjectLanguage() not in ["Python", "Python3"]:
            return

        if self.project.getProjectType() in ["PyQt5", "PyQt5C"]:
            self.pylupdate = QtUtilities.generatePyQtToolPath("pylupdate5")
        elif self.project.getProjectType() in ["PyQt6", "PyQt6C", "E7Plugin"]:
            self.pylupdate = QtUtilities.generatePyQtToolPath("pylupdate6")
        elif self.project.getProjectType() in ["PySide2", "PySide2C"]:
            self.pylupdate = QtUtilities.generatePySideToolPath(
                "pyside2-lupdate", variant=2
            )
        elif self.project.getProjectType() in ["PySide6", "PySide6C"]:
            self.pylupdate = QtUtilities.generatePySideToolPath(
                "pyside6-lupdate", variant=6
            )
        else:
            return

        self.__pylupdateProcesses = []
        if self.project.getProjectType() in ["PyQt6", "PyQt6C", "E7Plugin"]:
            if langs:
                langs = [
                    self.project.getRelativePath(lang.fileName())
                    for lang in langs
                    if lang.fileName().endswith(".ts")
                ]
            else:
                try:
                    pattern = self.project.getProjectData(
                        dataKey="TRANSLATIONPATTERN"
                    ).replace("%language%", "*")
                    langs = [
                        lang
                        for lang in self.project.getProjectData(dataKey="TRANSLATIONS")
                        if fnmatch.fnmatch(lang, pattern)
                    ]
                except IndexError:
                    langs = []
            if not langs:
                EricMessageBox.warning(
                    self,
                    self.tr("Translation file generation"),
                    self.tr("""No translation files (*.ts) selected."""),
                )
                return

            excludePatterns = [
                pat
                for pat in self.project.getIgnorePatterns()
                if pat.endswith((".py", ".ui"))
            ]

            QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            QGuiApplication.processEvents(
                QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
            )

            for lang in langs:
                proc = QProcess()
                args = []

                for pattern in excludePatterns:
                    args += ["--exclude", pattern]

                if noobsolete:
                    args.append("--no-obsolete")

                args += ["--ts", lang]

                startPath = self.project.getProjectData(
                    dataKey="TRANSLATIONSOURCESTARTPATH",
                    default="",
                )
                args.append(startPath if bool(startPath) else ".")

                proc.setWorkingDirectory(self.project.ppath)
                proc.finished.connect(
                    functools.partial(self.__generateTSFileDone, proc)
                )
                proc.readyReadStandardOutput.connect(
                    functools.partial(self.__readStdoutLupdate, proc)
                )
                proc.readyReadStandardError.connect(
                    functools.partial(self.__readStderrLupdate, proc)
                )

                proc.start(self.pylupdate, args)
                procStarted = proc.waitForStarted()
                if procStarted:
                    self.pylupdateProcRunning = True
                    self.__pylupdateProcesses.append((proc, "", []))
                else:
                    with EricOverridenCursor():
                        EricMessageBox.critical(
                            self,
                            self.tr("Process Generation Error"),
                            self.tr(
                                "Could not start {0}.<br>"
                                "Ensure that it is in the search path."
                            ).format(self.pylupdate),
                        )
        else:
            # generate a minimal temporary project file suitable for pylupdate
            self.__tmpProjects = []
            ok = self.__writeTempProjectFile(langs, [".py"])
            if not ok:
                return

            QGuiApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
            QGuiApplication.processEvents(
                QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
            )

            for tempProjectFile in self.__tmpProjects[:]:
                proc = QProcess()
                args = []

                if noobsolete:
                    args.append("-noobsolete")

                args.append("-verbose")
                path, filename = os.path.split(tempProjectFile)
                args.append(filename)
                proc.setWorkingDirectory(os.path.join(self.project.ppath, path))
                proc.finished.connect(
                    functools.partial(self.__generateTSFileDone, proc)
                )
                proc.readyReadStandardOutput.connect(
                    functools.partial(self.__readStdoutLupdate, proc)
                )
                proc.readyReadStandardError.connect(
                    functools.partial(self.__readStderrLupdate, proc)
                )

                proc.start(self.pylupdate, args)
                procStarted = proc.waitForStarted()
                if procStarted:
                    self.pylupdateProcRunning = True
                    self.__pylupdateProcesses.append((proc, tempProjectFile, []))
                else:
                    with EricOverridenCursor():
                        EricMessageBox.critical(
                            self,
                            self.tr("Process Generation Error"),
                            self.tr(
                                "Could not start {0}.<br>"
                                "Ensure that it is in the search path."
                            ).format(self.pylupdate),
                        )
                    # cleanup
                    with contextlib.suppress(OSError):
                        self.__tmpProjects.remove(tempProjectFile)
                        os.remove(tempProjectFile)

        if not self.__pylupdateProcesses:
            # no processes could be started, revert override cursor
            QGuiApplication.restoreOverrideCursor()
            QGuiApplication.processEvents(
                QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
            )

    def __generateAll(self):
        """
        Private method to generate all translation files (.ts) for Qt Linguist.

        All obsolete strings are removed from the .ts file.
        """
        self.__generateTSFile(noobsolete=True, generateAll=True)

    def __generateObsoleteAll(self):
        """
        Private method to generate all translation files (.ts) for Qt Linguist.

        Obsolete strings are kept.
        """
        self.__generateTSFile(noobsolete=False, generateAll=True)

    def __generateSelected(self):
        """
        Private method to generate selected translation files (.ts) for
        Qt Linguist.

        All obsolete strings are removed from the .ts file.
        """
        self.__generateTSFile(noobsolete=True, generateAll=False)

    def __generateObsoleteSelected(self):
        """
        Private method to generate selected translation files (.ts) for
        Qt Linguist.

        Obsolete strings are kept.
        """
        self.__generateTSFile(noobsolete=False, generateAll=False)

    ###########################################################################
    ##  Methods for the release commands
    ###########################################################################

    def __releaseTSFileDone(self, proc, exitCode, exitStatus):
        """
        Private slot to handle the finished signal of the lrelease process.

        @param proc reference to the process
        @type QProcess
        @param exitCode exit code of the process
        @type int
        @param exitStatus exit status of the process
        @type QProcess.ExitStatus
        """
        ui = ericApp().getObject("UserInterface")
        if exitStatus == QProcess.ExitStatus.NormalExit and exitCode == 0:
            ui.showNotification(
                EricPixmapCache.getPixmap("linguist48"),
                self.tr("Translation file release"),
                self.tr("The release of the translation files (*.qm) was successful."),
            )
            if self.project.getProjectData(dataKey="TRANSLATIONSBINPATH"):
                target = os.path.join(
                    self.project.ppath,
                    self.project.getProjectData(dataKey="TRANSLATIONSBINPATH"),
                )
                for langFile in self.project.getProjectData(dataKey="TRANSLATIONS")[:]:
                    if langFile.endswith(".ts"):
                        qmFile = os.path.join(
                            self.project.ppath, langFile.replace(".ts", ".qm")
                        )
                        if os.path.exists(qmFile):
                            shutil.move(qmFile, target)
        else:
            ui.showNotification(
                EricPixmapCache.getPixmap("linguist48"),
                self.tr("Translation file release"),
                self.tr("The release of the translation files (*.qm) has failed."),
                kind=NotificationTypes.CRITICAL,
                timeout=0,
            )

        for index in range(len(self.__lreleaseProcesses)):
            if proc is self.__lreleaseProcesses[index][0]:
                processData = self.__lreleaseProcesses[index]
                if processData[1]:
                    self.appendStdout.emit("".join(self.__lreleaseProcesses[index][1]))

                self.__lreleaseProcesses.remove(processData)
                break
        if not self.__lreleaseProcesses:
            # all done
            self.lreleaseProcRunning = False
            self.project.checkLanguageFiles()

    def __releaseTSFile(self, generateAll=False):
        """
        Private method to run lrelease to release the translation files (.qm).

        @param generateAll flag indicating whether all translations should be
            released
        @type bool
        """
        langs = [] if generateAll else self.getSelectedItems()

        # Hooks support
        if generateAll:
            if self.hooks["releaseAll"] is not None:
                self.hooks["releaseAll"](
                    self.project.getProjectData(dataKey="TRANSLATIONS")
                )
                return
        else:
            if self.hooks["releaseSelected"] is not None:
                li = [self.project.getRelativePath(lang.fileName()) for lang in langs]
                self.hooks["releaseSelected"](li)
                return

        if self.project.getProjectType() in [
            "PyQt5",
            "PyQt5C",
            "PyQt6",
            "PyQt6C",
            "E7Plugin",
            "PySide2",
            "PySide2C",
            "PySide6",
            "PySide6C",
        ]:
            lrelease = Preferences.getQt("Lrelease")
            if not lrelease:
                lrelease = os.path.join(
                    QtUtilities.getQtBinariesPath(),
                    QtUtilities.generateQtToolName("lrelease"),
                )
                if OSUtilities.isWindowsPlatform():
                    lrelease += ".exe"
        else:
            return

        if langs:
            langs = [
                self.project.getRelativePath(lang.fileName())
                for lang in langs
                if lang.fileName().endswith(".ts")
            ]
        else:
            try:
                pattern = self.project.getProjectData(
                    dataKey="TRANSLATIONPATTERN"
                ).replace("%language%", "*")
                langs = [
                    lang
                    for lang in self.project.getProjectData(dataKey="TRANSLATIONS")
                    if fnmatch.fnmatch(lang, pattern)
                ]
            except IndexError:
                langs = []
        if not langs:
            EricMessageBox.warning(
                self,
                self.tr("Write temporary project file"),
                self.tr("""No translation files (*.ts) selected."""),
            )
            return

        self.__lreleaseProcesses = []
        args = []
        args.append("-verbose")
        for langFile in langs:
            path, filename = os.path.split(langFile)
            args.append(filename)

        proc = QProcess()
        proc.setWorkingDirectory(os.path.join(self.project.ppath, path))
        proc.finished.connect(functools.partial(self.__releaseTSFileDone, proc))
        proc.readyReadStandardOutput.connect(
            functools.partial(self.__readStdoutLrelease, proc)
        )
        proc.readyReadStandardError.connect(
            functools.partial(self.__readStderrLrelease, proc)
        )

        proc.start(lrelease, args)
        procStarted = proc.waitForStarted()
        if procStarted:
            self.lreleaseProcRunning = True
            self.__lreleaseProcesses.append((proc, []))
        else:
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "<p>Could not start lrelease.<br>"
                    "Ensure that it is available as <b>{0}</b>.</p>"
                ).format(lrelease),
            )

    def __releaseSelected(self):
        """
        Private method to release the translation files (.qm).
        """
        self.__releaseTSFile(generateAll=False)

    def __releaseAll(self):
        """
        Private method to release the translation files (.qm).
        """
        self.__releaseTSFile(generateAll=True)

    ###########################################################################
    ## Support for hooks below
    ###########################################################################

    def _initHookMethods(self):
        """
        Protected method to initialize the hooks dictionary.

        Supported hook methods are:
        <ul>
        <li>extractMessages: takes no parameters</li>
        <li>generateAll: takes list of filenames as parameter</li>
        <li>generateAllWithObsolete: takes list of filenames as parameter</li>
        <li>generateSelected: takes list of filenames as parameter</li>
        <li>generateSelectedWithObsolete: takes list of filenames as
            parameter</li>
        <li>releaseAll: takes list of filenames as parameter</li>
        <li>releaseSelected: takes list of filenames as parameter</li>
        <li>open: takes a filename as parameter</li>
        </ul>

        <b>Note</b>: Filenames are relative to the project directory.
        """
        self.hooks = {
            "extractMessages": None,
            "generateAll": None,
            "generateAllWithObsolete": None,
            "generateSelected": None,
            "generateSelectedWithObsolete": None,
            "releaseAll": None,
            "releaseSelected": None,
            "open": None,
        }
