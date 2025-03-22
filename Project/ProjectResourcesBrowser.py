# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class used to display the resources part of the project.
"""

import contextlib
import os
import pathlib

from PyQt6.QtCore import QProcess, QThread, pyqtSignal
from PyQt6.QtWidgets import QApplication, QDialog, QMenu

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricProgressDialog import EricProgressDialog
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


class ProjectResourcesBrowser(ProjectBaseBrowser):
    """
    A class used to display the resources part of the project.

    @signal appendStderr(str) emitted after something was received from
        a QProcess on stderr
    @signal showMenu(str, QMenu) emitted when a menu is about to be shown.
        The name of the menu and a reference to the menu are given.
    """

    appendStderr = pyqtSignal(str)
    showMenu = pyqtSignal(str, QMenu)

    RCFilenameFormatPython = "{0}_rc.py"

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
        ProjectBaseBrowser.__init__(self, project, "resource", parent)

        self.selectedItemsFilter = [
            ProjectBrowserFileItem,
            ProjectBrowserSimpleDirectoryItem,
        ]

        self.setWindowTitle(self.tr("Resources"))

        self.setWhatsThis(
            self.tr(
                """<b>Project Resources Browser</b>"""
                """<p>This allows to easily see all resources contained in the"""
                """ current project. Several actions can be executed via the"""
                """ context menu.</p>"""
            )
        )

        self.compileProc = None

        # Add the file category handled by the browser.
        project.addFileCategory(
            "RESOURCES",
            FileCategoryRepositoryItem(
                fileCategoryFilterTemplate=self.tr("Resource Files ({0})"),
                fileCategoryUserString=self.tr("Resource Files"),
                fileCategoryTyeString=self.tr("Resources"),
                fileCategoryExtensions=["*.qrc"],
            ),
        )

        # Add the project browser type to the browser type repository.
        projectBrowser.addTypedProjectBrowser(
            "resources",
            ProjectBrowserRepositoryItem(
                projectBrowser=self,
                projectBrowserUserString=self.tr("Resources Browser"),
                priority=75,
                fileCategory="RESOURCES",
                fileFilter="resource",
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
        projectBrowser.processChangedProjectFiles.connect(
            self.__compileChangedResources
        )

        # Connect some of our own signals.
        self.appendStderr.connect(projectBrowser.appendStderr)
        self.closeSourceWindow.connect(projectBrowser.closeSourceWindow)
        self.sourceFile[str].connect(projectBrowser.sourceFile[str])

    def getIcon(self):
        """
        Public method to get an icon for the project browser.

        @return icon for the browser
        @rtype QIcon
        """
        return EricPixmapCache.getIcon("projectResources")

    def _createPopupMenus(self):
        """
        Protected overloaded method to generate the popup menu.
        """
        self.menuActions = []
        self.multiMenuActions = []
        self.dirMenuActions = []
        self.dirMultiMenuActions = []

        self.menu = QMenu(self)
        if FileSystemUtilities.isPlainFileName(
            self.project.getProjectPath()
        ) and self.project.getProjectType() in [
            "PyQt5",
            "PyQt5C",
            "PySide2",
            "PySide2C",
            "PySide6",
            "PySide6C",
        ]:
            self.menu.addAction(self.tr("Compile resource"), self.__compileResource)
            self.menu.addAction(
                self.tr("Compile all resources"), self.__compileAllResources
            )
            self.menu.addSeparator()
            self.menu.addAction(
                self.tr("Configure rcc Compiler"), self.__configureRccCompiler
            )
            self.menu.addSeparator()
        else:
            if self.hooks["compileResource"] is not None:
                self.menu.addAction(
                    self.hooksMenuEntries.get(
                        "compileResource", self.tr("Compile resource")
                    ),
                    self.__compileResource,
                )
            if self.hooks["compileAllResources"] is not None:
                self.menu.addAction(
                    self.hooksMenuEntries.get(
                        "compileAllResources", self.tr("Compile all resources")
                    ),
                    self.__compileAllResources,
                )
            if (
                self.hooks["compileResource"] is not None
                or self.hooks["compileAllResources"] is not None
            ):
                self.menu.addSeparator()
        self.menu.addAction(self.tr("Open"), self.__openFile)
        self.menu.addSeparator()
        act = self.menu.addAction(self.tr("Rename file"), self._renameFile)
        self.menuActions.append(act)
        act = self.menu.addAction(self.tr("Remove from project"), self._removeFile)
        self.menuActions.append(act)
        act = self.menu.addAction(self.tr("Delete"), self.__deleteFile)
        self.menuActions.append(act)
        self.menu.addSeparator()
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            if self.project.getProjectType() in [
                "PyQt5",
                "PyQt5C",
                "PySide2",
                "PySide2C",
                "PySide6",
                "PySide6C",
            ]:
                self.menu.addAction(self.tr("New resource..."), self.__newResource)
            else:
                if self.hooks["newResource"] is not None:
                    self.menu.addAction(
                        self.hooksMenuEntries.get(
                            "newResource", self.tr("New resource...")
                        ),
                        self.__newResource,
                    )
        self.menu.addAction(self.tr("Add resources..."), self.__addResourceFiles)
        self.menu.addAction(
            self.tr("Add resources directory..."), self.__addResourcesDirectory
        )
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
            if self.project.getProjectType() in [
                "PyQt5",
                "PyQt5C",
                "PySide2",
                "PySide2C",
                "PySide6",
                "PySide6C",
            ]:
                self.backMenu.addAction(
                    self.tr("Compile all resources"), self.__compileAllResources
                )
                self.backMenu.addSeparator()
                self.backMenu.addAction(
                    self.tr("Configure rcc Compiler"), self.__configureRccCompiler
                )
                self.backMenu.addSeparator()
                self.backMenu.addAction(self.tr("New resource..."), self.__newResource)
            else:
                if self.hooks["compileAllResources"] is not None:
                    self.backMenu.addAction(
                        self.hooksMenuEntries.get(
                            "compileAllResources", self.tr("Compile all resources")
                        ),
                        self.__compileAllResources,
                    )
                    self.backMenu.addSeparator()
                if self.hooks["newResource"] is not None:
                    self.backMenu.addAction(
                        self.hooksMenuEntries.get(
                            "newResource", self.tr("New resource...")
                        ),
                        self.__newResource,
                    )
        self.backMenu.addAction(
            self.tr("Add resources..."), lambda: self.project.addFiles("RECOURCES")
        )
        self.backMenu.addAction(
            self.tr("Add resources directory..."),
            lambda: self.project.addDirectory("RESOURCES"),
        )
        self.backMenu.addSeparator()
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
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
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            if self.project.getProjectType() in [
                "PyQt5",
                "PyQt5C",
                "PySide2",
                "PySide2C",
                "PySide6",
                "PySide6C",
            ]:
                act = self.multiMenu.addAction(
                    self.tr("Compile resources"), self.__compileSelectedResources
                )
                self.multiMenu.addSeparator()
                self.multiMenu.addAction(
                    self.tr("Configure rcc Compiler"), self.__configureRccCompiler
                )
                self.multiMenu.addSeparator()
            else:
                if self.hooks["compileSelectedResources"] is not None:
                    act = self.multiMenu.addAction(
                        self.hooksMenuEntries.get(
                            "compileSelectedResources", self.tr("Compile resources")
                        ),
                        self.__compileSelectedResources,
                    )
                    self.multiMenu.addSeparator()
        self.multiMenu.addAction(self.tr("Open"), self.__openFile)
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
            if self.project.getProjectType() in [
                "PyQt5",
                "PyQt5C",
                "PySide2",
                "PySide2C",
                "PySide6",
                "PySide6C",
            ]:
                self.dirMenu.addAction(
                    self.tr("Compile all resources"), self.__compileAllResources
                )
                self.dirMenu.addSeparator()
                self.dirMenu.addAction(
                    self.tr("Configure rcc Compiler"), self.__configureRccCompiler
                )
                self.dirMenu.addSeparator()
            else:
                if self.hooks["compileAllResources"] is not None:
                    self.dirMenu.addAction(
                        self.hooksMenuEntries.get(
                            "compileAllResources", self.tr("Compile all resources")
                        ),
                        self.__compileAllResources,
                    )
                    self.dirMenu.addSeparator()
        act = self.dirMenu.addAction(self.tr("Remove from project"), self._removeDir)
        self.dirMenuActions.append(act)
        act = self.dirMenu.addAction(self.tr("Delete"), self._deleteDirectory)
        self.dirMenuActions.append(act)
        self.dirMenu.addSeparator()
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
            self.dirMenu.addAction(self.tr("New resource..."), self.__newResource)
        self.dirMenu.addAction(self.tr("Add resources..."), self.__addResourceFiles)
        self.dirMenu.addAction(
            self.tr("Add resources directory..."), self.__addResourcesDirectory
        )
        self.dirMenu.addSeparator()
        if FileSystemUtilities.isPlainFileName(self.project.getProjectPath()):
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
            if self.project.getProjectType() in [
                "PyQt5",
                "PyQt5C",
                "PySide2",
                "PySide2C",
                "PySide6",
                "PySide6C",
            ]:
                self.dirMultiMenu.addAction(
                    self.tr("Compile all resources"), self.__compileAllResources
                )
                self.dirMultiMenu.addSeparator()
                self.dirMultiMenu.addAction(
                    self.tr("Configure rcc Compiler"), self.__configureRccCompiler
                )
                self.dirMultiMenu.addSeparator()
            else:
                if self.hooks["compileAllResources"] is not None:
                    self.dirMultiMenu.addAction(
                        self.hooksMenuEntries.get(
                            "compileAllResources", self.tr("Compile all resources")
                        ),
                        self.__compileAllResources,
                    )
                    self.dirMultiMenu.addSeparator()
        self.dirMultiMenu.addAction(
            self.tr("Add resources..."), lambda: self.project.addFiles("RECOURCES")
        )
        self.dirMultiMenu.addAction(
            self.tr("Add resources directory..."),
            lambda: self.project.addDirectory("RESOURCES"),
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

    def __addResourceFiles(self):
        """
        Private method to add resource files to the project.
        """
        self.project.addFiles("RESOURCES", self.currentDirectory())

    def __addResourcesDirectory(self):
        """
        Private method to add resource files of a directory to the project.
        """
        self.project.addDirectory("RESOURCES", self.currentDirectory())

    def _openItem(self):
        """
        Protected slot to handle the open popup menu entry.
        """
        self.__openFile()

    def __openFile(self):
        """
        Private slot to handle the Open menu action.
        """
        itmList = self.getSelectedItems()
        for itm in itmList[:]:
            if isinstance(itm, ProjectBrowserFileItem):
                self.sourceFile.emit(itm.fileName())

    def __newResource(self):
        """
        Private slot to handle the New Resource menu action.
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

        if self.hooks["newResource"] is not None:
            self.hooks["newResource"](path)
        else:
            fname, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
                self,
                self.tr("New Resource"),
                path,
                self.tr("Qt Resource Files (*.qrc)"),
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
                    self.tr("New Resource"),
                    self.tr("The file already exists! Overwrite it?"),
                    icon=EricMessageBox.Warning,
                )
                if not res:
                    # user selected to not overwrite
                    return

            try:
                newline = (
                    None if self.project.useSystemEol() else self.project.getEolString()
                )
                with fpath.open("w", encoding="utf-8", newline=newline) as rcfile:
                    rcfile.write("<!DOCTYPE RCC>\n")
                    rcfile.write('<RCC version="1.0">\n')
                    rcfile.write("<qresource>\n")
                    rcfile.write("</qresource>\n")
                    rcfile.write("</RCC>\n")
            except OSError as e:
                EricMessageBox.critical(
                    self,
                    self.tr("New Resource"),
                    self.tr(
                        "<p>The new resource file <b>{0}</b> could not"
                        " be created.<br>Problem: {1}</p>"
                    ).format(fpath, str(e)),
                )
                return

            self.project.appendFile(str(fpath))
            self.sourceFile.emit(str(fpath))

    def __deleteFile(self):
        """
        Private method to delete a resource file from the project.
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
            self.tr("Delete resources"),
            self.tr("Do you really want to delete these resources from the project?"),
            files,
        )

        if dlg.exec() == QDialog.DialogCode.Accepted:
            for fn2, fn in zip(fullNames, files):
                self.closeSourceWindow.emit(fn2)
                self.project.deleteFile(fn)

    ###########################################################################
    ##  Methods to handle the various compile commands
    ###########################################################################

    def __readStdout(self):
        """
        Private slot to handle the readyReadStandardOutput signal of the
        pyrcc5/pyside2-rcc/pyside6-rcc process.
        """
        if self.compileProc is None:
            return
        self.compileProc.setReadChannel(QProcess.ProcessChannel.StandardOutput)

        while self.compileProc and self.compileProc.canReadLine():
            self.__buf.append(
                str(
                    self.compileProc.readLine(),
                    Preferences.getSystem("IOEncoding"),
                    "replace",
                ).rstrip()
            )

    def __readStderr(self):
        """
        Private slot to handle the readyReadStandardError signal of the
        pyrcc5/pyside2-rcc/pyside6-rcc process.
        """
        if self.compileProc is None:
            return

        ioEncoding = Preferences.getSystem("IOEncoding")

        self.compileProc.setReadChannel(QProcess.ProcessChannel.StandardError)
        while self.compileProc and self.compileProc.canReadLine():
            s = self.rccCompiler + ": "
            error = str(self.compileProc.readLine(), ioEncoding, "replace")
            s += error
            self.appendStderr.emit(s)

    def __compileQRCDone(self, exitCode, exitStatus):
        """
        Private slot to handle the finished signal of the compile process.

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
                    EricPixmapCache.getPixmap("resourcesCompiler48"),
                    self.tr("Resource Compilation"),
                    self.tr("The compilation of the resource file was successful."),
                )
            except OSError as msg:
                if not self.noDialog:
                    EricMessageBox.information(
                        self,
                        self.tr("Resource Compilation"),
                        self.tr(
                            "<p>The compilation of the resource file"
                            " failed.</p><p>Reason: {0}</p>"
                        ).format(str(msg)),
                    )
        else:
            ui.showNotification(
                EricPixmapCache.getPixmap("resourcesCompiler48"),
                self.tr("Resource Compilation"),
                self.tr("The compilation of the resource file failed."),
                kind=NotificationTypes.CRITICAL,
                timeout=0,
            )
        self.compileProc = None

    def __compileQRC(self, fn, noDialog=False, progress=None):
        """
        Private method to compile a .qrc file to a .py file.

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

        if self.project.getProjectLanguage() == "Python3":
            if self.project.getProjectType() in ["PyQt5", "PyQt5C"]:
                self.rccCompiler = QtUtilities.generatePyQtToolPath("pyrcc5")
            elif self.project.getProjectType() in ["PySide2", "PySide2C"]:
                self.rccCompiler = QtUtilities.generatePySideToolPath(
                    "pyside2-rcc", variant=2
                )
            elif self.project.getProjectType() in ["PySide6", "PySide6C"]:
                self.rccCompiler = QtUtilities.generatePySideToolPath(
                    "pyside6-rcc", variant=6
                )
            else:
                return None
            defaultParameters = self.project.getDefaultRccCompilerParameters()
            rccParameters = self.project.getProjectData(dataKey="RCCPARAMS")
            if (
                rccParameters["CompressionThreshold"]
                != defaultParameters["CompressionThreshold"]
            ):
                args.append("-threshold")
                args.append(str(rccParameters["CompressionThreshold"]))
            if rccParameters["CompressLevel"] != defaultParameters["CompressLevel"]:
                args.append("-compress")
                args.append(str(rccParameters["CompressLevel"]))
            if (
                rccParameters["CompressionDisable"]
                != defaultParameters["CompressionDisable"]
            ):
                args.append("-no-compress")
            if rccParameters["PathPrefix"] != defaultParameters["PathPrefix"]:
                args.append("-root")
                args.append(rccParameters["PathPrefix"])
        else:
            return None

        rcc = self.rccCompiler

        ofn, _ext = os.path.splitext(fn)
        fn = os.path.join(self.project.ppath, fn)

        dirname, filename = os.path.split(ofn)
        if self.project.getProjectLanguage() == "Python3":
            self.compiledFile = os.path.join(
                dirname, self.RCFilenameFormatPython.format(filename)
            )

        args.append(fn)
        self.compileProc.finished.connect(self.__compileQRCDone)
        self.compileProc.readyReadStandardOutput.connect(self.__readStdout)
        self.compileProc.readyReadStandardError.connect(self.__readStderr)

        self.noDialog = noDialog
        self.compileProc.start(rcc, args)
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
                ).format(self.rccCompiler),
            )
            return None

    def __compileResource(self):
        """
        Private method to compile a resource to a source file.
        """
        itm = self.model().item(self.currentIndex())
        fn2 = itm.fileName()
        fn = self.project.getRelativePath(fn2)
        if self.hooks["compileResource"] is not None:
            self.hooks["compileResource"](fn)
        else:
            self.__compileQRC(fn)

    def __compileAllResources(self):
        """
        Private method to compile all resources to source files.
        """
        if self.hooks["compileAllResources"] is not None:
            self.hooks["compileAllResources"](
                self.project.getProjectData(dataKey="RESOURCES")
            )
        else:
            numResources = len(self.project.getProjectData(dataKey="RESOURCES"))
            progress = EricProgressDialog(
                self.tr("Compiling resources..."),
                self.tr("Abort"),
                0,
                numResources,
                self.tr("%v/%m Resources"),
                self,
            )
            progress.setModal(True)
            progress.setMinimumDuration(0)
            progress.setWindowTitle(self.tr("Resources"))

            for prog, fn in enumerate(self.project.getProjectData(dataKey="RESOURCES")):
                progress.setValue(prog)
                if progress.wasCanceled():
                    break
                proc = self.__compileQRC(fn, True, progress)
                if proc is not None:
                    while proc.state() == QProcess.ProcessState.Running:
                        QThread.msleep(100)
                        QApplication.processEvents()
                else:
                    break
            progress.setValue(numResources)

    def __compileSelectedResources(self):
        """
        Private method to compile selected resources to source files.
        """
        items = self.getSelectedItems()
        files = [self.project.getRelativePath(itm.fileName()) for itm in items]

        if self.hooks["compileSelectedResources"] is not None:
            self.hooks["compileSelectedResources"](files)
        else:
            numResources = len(files)
            progress = EricProgressDialog(
                self.tr("Compiling resources..."),
                self.tr("Abort"),
                0,
                numResources,
                self.tr("%v/%m Resources"),
                self,
            )
            progress.setModal(True)
            progress.setMinimumDuration(0)
            progress.setWindowTitle(self.tr("Resources"))

            for prog, fn in enumerate(files):
                progress.setValue(prog)
                if progress.wasCanceled():
                    break
                if not fn.endswith(".ui.h"):
                    proc = self.__compileQRC(fn, True, progress)
                    if proc is not None:
                        while proc.state() == QProcess.ProcessState.Running:
                            QThread.msleep(100)
                            QApplication.processEvents()
                    else:
                        break
            progress.setValue(numResources)

    def __checkResourcesNewer(self, filename, mtime):
        """
        Private method to check, if any file referenced in a resource
        file is newer than a given time.

        @param filename filename of the resource file
        @type str
        @param mtime modification time to check against
        @type int
        @return flag indicating some file is newer
        @rtype boolean)
        """
        try:
            with open(filename, "r", encoding="utf-8") as f:
                buf = f.read()
        except OSError:
            return False

        qrcDirName = os.path.dirname(filename)
        lbuf = ""
        for line in buf.splitlines():
            line = line.strip()
            if line.lower().startswith("<file>") or line.lower().startswith("<file "):
                lbuf = line
            elif lbuf:
                lbuf = "{0}{1}".format(lbuf, line)
            if lbuf.lower().endswith("</file>"):
                rfile = lbuf.split(">", 1)[1].split("<", 1)[0]
                if not os.path.isabs(rfile):
                    rfile = os.path.join(qrcDirName, rfile)
                if os.path.exists(rfile) and os.stat(rfile).st_mtime > mtime:
                    return True

                lbuf = ""

        return False

    def __compileChangedResources(self):
        """
        Private method to compile all changed resources to source files.
        """
        if Preferences.getProject("AutoCompileResources"):
            if self.hooks["compileChangedResources"] is not None:
                self.hooks["compileChangedResources"](
                    self.project.getProjectData(dataKey="RESOURCES")
                )
            else:
                if len(self.project.getProjectData(dataKey="RESOURCES")) == 0:
                    # The project does not contain resource files
                    return

                progress = EricProgressDialog(
                    self.tr("Determining changed resources..."),
                    self.tr("Abort"),
                    0,
                    100,
                    self.tr("%v/%m Resources"),
                    self,
                )
                progress.setMinimumDuration(0)
                progress.setWindowTitle(self.tr("Resources"))

                # get list of changed resources
                changedResources = []
                progress.setMaximum(
                    len(self.project.getProjectData(dataKey="RESOURCES"))
                )
                for prog, fn in enumerate(
                    self.project.getProjectData(dataKey="RESOURCES")
                ):
                    progress.setValue(prog)
                    QApplication.processEvents()
                    ifn = os.path.join(self.project.ppath, fn)
                    if self.project.getProjectLanguage() == "Python3":
                        dirname, filename = os.path.split(os.path.splitext(ifn)[0])
                        ofn = os.path.join(
                            dirname, self.RCFilenameFormatPython.format(filename)
                        )
                    else:
                        return
                    if (
                        not os.path.exists(ofn)
                        or os.stat(ifn).st_mtime > os.stat(ofn).st_mtime
                        or self.__checkResourcesNewer(ifn, os.stat(ofn).st_mtime)
                    ):
                        changedResources.append(fn)
                progress.setValue(len(self.project.getProjectData(dataKey="RESOURCES")))
                QApplication.processEvents()

                if changedResources:
                    progress.setLabelText(self.tr("Compiling changed resources..."))
                    progress.setMaximum(len(changedResources))
                    progress.setValue(0)
                    QApplication.processEvents()
                    for prog, fn in enumerate(changedResources):
                        progress.setValue(prog)
                        if progress.wasCanceled():
                            break
                        proc = self.__compileQRC(fn, True, progress)
                        if proc is not None:
                            while proc.state() == QProcess.ProcessState.Running:
                                QThread.msleep(100)
                                QApplication.processEvents()
                        else:
                            break
                    progress.setValue(len(changedResources))
                    QApplication.processEvents()

    def handlePreferencesChanged(self):
        """
        Public slot used to handle the preferencesChanged signal.
        """
        ProjectBaseBrowser.handlePreferencesChanged(self)

    def __configureRccCompiler(self):
        """
        Private slot to configure some non-common rcc compiler options.
        """
        from .RccCompilerOptionsDialog import RccCompilerOptionsDialog

        params = self.project.getProjectData(dataKey="RCCPARAMS")

        dlg = RccCompilerOptionsDialog(params, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            threshold, compression, noCompression, root = dlg.getData()
            if threshold != params["CompressionThreshold"]:
                params["CompressionThreshold"] = threshold
                self.project.setDirty(True)
            if compression != params["CompressLevel"]:
                params["CompressLevel"] = compression
                self.project.setDirty(True)
            if noCompression != params["CompressionDisable"]:
                params["CompressionDisable"] = noCompression
                self.project.setDirty(True)
            if root != params["PathPrefix"]:
                params["PathPrefix"] = root
                self.project.setDirty(True)

    ###########################################################################
    ## Support for hooks below
    ###########################################################################

    def _initHookMethods(self):
        """
        Protected method to initialize the hooks dictionary.

        Supported hook methods are:
        <ul>
        <li>compileResource: takes filename as parameter</li>
        <li>compileAllResources: takes list of filenames as parameter</li>
        <li>compileChangedResources: takes list of filenames as parameter</li>
        <li>compileSelectedResources: takes list of all form filenames as
            parameter</li>
        <li>newResource: takes full directory path of new file as
            parameter</li>
        </ul>

        <b>Note</b>: Filenames are relative to the project directory, if not
        specified differently.
        """
        self.hooks = {
            "compileResource": None,
            "compileAllResources": None,
            "compileChangedResources": None,
            "compileSelectedResources": None,
            "newResource": None,
        }
