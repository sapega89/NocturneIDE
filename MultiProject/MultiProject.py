# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the multi project management functionality.
"""

import contextlib
import os
import pathlib
import shutil

from PyQt6.QtCore import QObject, QUuid, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QDialog, QMenu, QToolBar

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction, createActionGroup
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricFileDialog, EricMessageBox, EricPathPickerDialog
from eric7.EricWidgets.EricPathPickerDialog import EricPathPickerModes
from eric7.Globals import recentNameMultiProject
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities

from .MultiProjectFile import MultiProjectFile
from .MultiProjectProjectMeta import MultiProjectProjectMeta


class MultiProject(QObject):
    """
    Class implementing the project management functionality.

    @signal dirty(bool) emitted when the dirty state changes
    @signal newMultiProject() emitted after a new multi project was generated
    @signal multiProjectOpened() emitted after a multi project file was read
    @signal multiProjectClosed() emitted after a multi project was closed
    @signal multiProjectPropertiesChanged() emitted after the multi project
            properties were changed
    @signal showMenu(string, QMenu) emitted when a menu is about to be shown.
            The name of the menu and a reference to the menu are given.
    @signal projectDataChanged(project metadata) emitted after a project entry
            has been changed
    @signal projectAdded(project metadata) emitted after a project entry
            has been added
    @signal projectRemoved(project metadata) emitted after a project entry
            has been removed
    @signal projectOpened(filename) emitted after the project has been opened
    """

    dirty = pyqtSignal(bool)
    newMultiProject = pyqtSignal()
    multiProjectOpened = pyqtSignal()
    multiProjectClosed = pyqtSignal()
    multiProjectPropertiesChanged = pyqtSignal()
    showMenu = pyqtSignal(str, QMenu)
    projectDataChanged = pyqtSignal(MultiProjectProjectMeta)
    projectAdded = pyqtSignal(MultiProjectProjectMeta)
    projectRemoved = pyqtSignal(MultiProjectProjectMeta)
    projectOpened = pyqtSignal(str)

    def __init__(self, project, parent=None, filename=None):
        """
        Constructor

        @param project reference to the project object
        @type Project.Project
        @param parent parent widget (usually the ui object)
        @type QWidget
        @param filename optional filename of a multi project file to open
        @type str
        """
        super().__init__(parent)

        self.ui = parent
        self.projectObject = project

        self.__initData()

        self.__multiProjectFile = MultiProjectFile(self)

        self.recent = []
        self.__loadRecent()

        if filename is not None:
            self.openMultiProject(filename)

    def __initData(self):
        """
        Private method to initialize the multi project data part.
        """
        self.loaded = False  # flag for the loaded status
        self.__dirty = False  # dirty flag
        self.pfile = ""  # name of the multi project file
        self.ppath = ""  # name of the multi project directory
        self.description = ""  # description of the multi project
        self.name = ""
        self.opened = False
        self.__projects = {}
        # dict of project info keyed by 'uid'; each info entry is a MultiProjectProject
        self.categories = []

    def __loadRecent(self):
        """
        Private method to load the recently opened multi project filenames.
        """
        self.recent = []
        Preferences.Prefs.rsettings.sync()
        rp = Preferences.Prefs.rsettings.value(recentNameMultiProject)
        if rp is not None:
            for f in rp:
                if pathlib.Path(f).exists():
                    self.recent.append(f)

    def __saveRecent(self):
        """
        Private method to save the list of recently opened filenames.
        """
        Preferences.Prefs.rsettings.setValue(recentNameMultiProject, self.recent)
        Preferences.Prefs.rsettings.sync()

    def getMostRecent(self):
        """
        Public method to get the most recently opened multiproject.

        @return path of the most recently opened multiproject
        @rtype str
        """
        if len(self.recent):
            return self.recent[0]
        else:
            return None

    def setDirty(self, b):
        """
        Public method to set the dirty state.

        It emits the signal dirty(int).

        @param b dirty state
        @type bool
        """
        self.__dirty = b
        self.saveAct.setEnabled(b)
        self.dirty.emit(bool(b))

    def isDirty(self):
        """
        Public method to return the dirty state.

        @return dirty state
        @rtype bool
        """
        return self.__dirty

    def isOpen(self):
        """
        Public method to return the opened state.

        @return open state
        @rtype bool
        """
        return self.opened

    def getMultiProjectPath(self):
        """
        Public method to get the multi project path.

        @return multi project path
        @rtype str
        """
        return self.ppath

    def getMultiProjectFile(self):
        """
        Public method to get the path of the multi project file.

        @return path of the multi project file
        @rtype str
        """
        return self.pfile

    def __extractCategories(self):
        """
        Private slot to extract the categories used in the project definitions.
        """
        for project in self.__projects.values():
            if project.category and project.category not in self.categories:
                self.categories.append(project.category)

    def getCategories(self):
        """
        Public method to get the list of defined categories.

        @return list of categories
        @rtype list of str
        """
        return [c for c in self.categories if c]

    def __readMultiProject(self, fn):
        """
        Private method to read in a multi project (.emj) file.

        @param fn filename of the multi project file to be read
        @type str
        @return flag indicating success
        @rtype bool
        """
        with EricOverrideCursor():
            res = self.__multiProjectFile.readFile(fn)

        if res:
            self.pfile = os.path.abspath(fn)
            self.ppath = os.path.abspath(os.path.dirname(fn))

            self.__extractCategories()

            # insert filename into list of recently opened multi projects
            self.__syncRecent()

            self.name = os.path.splitext(os.path.basename(fn))[0]

            # check, if the files of the multi project still exist
            self.__checkFilesExist()

        return res

    def __writeMultiProject(self, fn=None):
        """
        Private method to save the multi project infos to a multi project file.

        @param fn optional filename of the multi project file to be written.
            If fn is None, the filename stored in the multi project object
            is used. This is the 'save' action. If fn is given, this filename
            is used instead of the one in the multi project object. This is the
            'save as' action.
        @type str
        @return flag indicating success
        @rtype bool
        """
        if fn is None:
            fn = self.pfile

        res = self.__multiProjectFile.writeFile(fn)
        if res:
            self.pfile = os.path.abspath(fn)
            self.ppath = os.path.abspath(os.path.dirname(fn))
            self.name = os.path.splitext(os.path.basename(fn))[0]
            self.setDirty(False)

            # insert filename into list of recently opened projects
            self.__syncRecent()

        return res

    def addProject(self, project):
        """
        Public method to add a project to the multi-project.

        @param project dictionary containing the project data to be added
        @type MultiProjectProjectMeta
        """
        self.__projects[project.uid] = project

    @pyqtSlot()
    def addNewProject(self, startdir="", category=""):
        """
        Public slot used to add a new project to the multi-project.

        @param startdir start directory for the selection dialog
        @type str
        @param category category to be preset
        @type str
        """
        from .AddProjectDialog import AddProjectDialog

        if not startdir:
            startdir = self.ppath
        if not startdir:
            startdir = Preferences.getMultiProject("Workspace")
        dlg = AddProjectDialog(
            parent=self.ui,
            startdir=startdir,
            categories=self.categories,
            category=category,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            newProject = dlg.getProjectMetadata()

            # step 1: check, if project was already added
            for project in self.__projects.values():
                if project.file == newProject.file:
                    return

            # step 2: check, if main should be changed
            if newProject.main:
                for project in self.__projects.values():
                    if project.main:
                        project.main = False
                        self.projectDataChanged.emit(project)
                        self.setDirty(True)
                        break

            # step 3: add the project entry
            self.__projects[newProject.uid] = newProject
            if category not in self.categories:
                self.categories.append(category)
            self.projectAdded.emit(newProject)
            self.setDirty(True)

    def copyProject(self, uid):
        """
        Public method to copy the project with given UID on disk.

        @param uid UID of the project to copy
        @type str
        """
        if uid in self.__projects:
            startdir = self.ppath
            if not startdir:
                startdir = Preferences.getMultiProject("Workspace")
            srcProject = self.__projects[uid]
            srcProjectDirectory = os.path.dirname(srcProject.file)
            dstProjectDirectory, ok = EricPathPickerDialog.getStrPath(
                self.parent(),
                self.tr("Copy Project"),
                self.tr(
                    "Enter directory for the new project (must not exist already):"
                ),
                mode=EricPathPickerModes.DIRECTORY_MODE,
                strPath=srcProjectDirectory,
                defaultDirectory=startdir,
            )
            if ok and dstProjectDirectory and not os.path.exists(dstProjectDirectory):
                try:
                    shutil.copytree(srcProjectDirectory, dstProjectDirectory)
                except shutil.Error:
                    EricMessageBox.critical(
                        self.parent(),
                        self.tr("Copy Project"),
                        self.tr(
                            "<p>The source project <b>{0}</b> could not"
                            " be copied to its destination <b>{1}</b>."
                            "</p>"
                        ).format(srcProjectDirectory, dstProjectDirectory),
                    )
                    return

                dstUid = QUuid.createUuid().toString()
                dstProject = MultiProjectProjectMeta(
                    name=self.tr("{0} - Copy").format(srcProject["name"]),
                    file=os.path.join(
                        dstProjectDirectory, os.path.basename(srcProject["file"])
                    ),
                    main=False,
                    description=srcProject.description,
                    category=srcProject.category,
                    uid=dstUid,
                )
                self.__projects[dstUid] = dstProject
                self.projectAdded.emit(dstProject)
                self.setDirty(True)

    def changeProjectProperties(self, pro):
        """
        Public method to change the data of a project entry.

        @param pro dictionary with the project data
        @type str
        """
        # step 1: check, if main should be changed
        if pro.main:
            for project in self.__projects.values():
                if project.main:
                    if project.uid != pro.uid:
                        project.main = False
                        self.projectDataChanged.emit(project)
                        self.setDirty(True)
                    break

        # step 2: change the entry
        project = self.__projects[pro.uid]
        # project UID is not changeable via interface
        project.file = pro.file
        project.name = pro.name
        project.main = pro.main
        project.description = pro.description
        project.category = pro.category
        if project.category not in self.categories:
            self.categories.append(project.category)
        self.projectDataChanged.emit(project)
        self.setDirty(True)

    def getProjects(self):
        """
        Public method to get all project entries.

        @return list of all project entries
        @rtype list of MultiProjectProjectMeta
        """
        return self.__projects.values()

    def getProject(self, uid):
        """
        Public method to get a reference to a project entry.

        @param uid UID of the project to get
        @type str
        @return project metadata
        @rtype MultiProjectProjectMeta
        """
        if uid in self.__projects:
            return self.__projects[uid]
        else:
            return None

    def removeProject(self, uid):
        """
        Public slot to remove a project from the multi project.

        @param uid UID of the project to be removed from the multi
            project
        @type str
        """
        if uid in self.__projects:
            project = self.__projects[uid]
            del self.__projects[uid]
            self.projectRemoved.emit(project)
            self.setDirty(True)

    def deleteProject(self, uid):
        """
        Public slot to delete project(s) from the multi project and disk.

        @param uid UID of the project to be removed from the multi
            project
        @type str
        """
        if uid in self.__projects:
            project = self.__projects[uid]
            projectPath = os.path.dirname(project.file)
            shutil.rmtree(projectPath, ignore_errors=True)

            self.removeProject(uid)

    def __newMultiProject(self):
        """
        Private slot to build a new multi project.

        This method displays the new multi project dialog and initializes
        the multi project object with the data entered.
        """
        from .PropertiesDialog import PropertiesDialog

        if not self.checkDirty():
            return

        dlg = PropertiesDialog(self, True, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.closeMultiProject()
            dlg.storeData()
            self.opened = True
            self.setDirty(True)
            self.closeAct.setEnabled(True)
            self.saveasAct.setEnabled(True)
            self.addProjectAct.setEnabled(True)
            self.propsAct.setEnabled(True)
            self.newMultiProject.emit()

    def __showProperties(self):
        """
        Private slot to display the properties dialog.
        """
        from .PropertiesDialog import PropertiesDialog

        dlg = PropertiesDialog(self, False, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.storeData()
            self.setDirty(True)
            self.multiProjectPropertiesChanged.emit()

    @pyqtSlot()
    @pyqtSlot(str)
    def openMultiProject(self, fn=None, openMain=True):
        """
        Public slot to open a multi project.

        @param fn optional filename of the multi project file to be
            read
        @type str
        @param openMain flag indicating, that the main project
            should be opened depending on the configuration
        @type bool
        """
        if not self.checkDirty():
            return

        if fn is None:
            fn = EricFileDialog.getOpenFileName(
                self.parent(),
                self.tr("Open Multi Project"),
                Preferences.getMultiProject("Workspace") or OSUtilities.getHomeDir(),
                self.tr("Multi Project Files (*.emj)"),
            )

            if fn == "":
                fn = None

        if fn is not None:
            self.closeMultiProject()
            ok = self.__readMultiProject(fn)
            if ok:
                self.opened = True

                self.closeAct.setEnabled(True)
                self.saveasAct.setEnabled(True)
                self.addProjectAct.setEnabled(True)
                self.propsAct.setEnabled(True)

                self.multiProjectOpened.emit()

                if openMain and Preferences.getMultiProject("OpenMainAutomatically"):
                    self.__openMainProject(False)

    def saveMultiProject(self):
        """
        Public slot to save the current multi project.

        @return flag indicating success
        @rtype bool
        """
        if self.isDirty():
            if len(self.pfile) > 0:
                ok = self.__writeMultiProject()
            else:
                ok = self.saveMultiProjectAs()
        else:
            ok = True
        return ok

    def saveMultiProjectAs(self):
        """
        Public slot to save the current multi project to a different file.

        @return flag indicating success
        @rtype bool
        """
        defaultFilter = self.tr("Multi Project Files (*.emj)")
        defaultPath = (
            self.ppath
            if self.ppath
            else (Preferences.getMultiProject("Workspace") or OSUtilities.getHomeDir())
        )
        fn, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self.parent(),
            self.tr("Save Multiproject"),
            defaultPath,
            self.tr("Multi Project Files (*.emj)"),
            defaultFilter,
            EricFileDialog.DontConfirmOverwrite,
        )

        if fn:
            fpath = pathlib.Path(fn)
            if not fpath.suffix:
                ex = selectedFilter.split("(*")[1].split(")")[0]
                if ex:
                    fpath = fpath.with_suffix(ex)
            if fpath.exists():
                res = EricMessageBox.yesNo(
                    self.parent(),
                    self.tr("Save File"),
                    self.tr(
                        "<p>The file <b>{0}</b> already exists. Overwrite it?</p>"
                    ).format(fn),
                    icon=EricMessageBox.Warning,
                )
                if not res:
                    return False

            self.name = fpath.stem
            self.__writeMultiProject(str(fpath))

            self.multiProjectClosed.emit()
            self.multiProjectOpened.emit()
            return True
        else:
            return False

    def checkDirty(self):
        """
        Public method to check the dirty status and open a message window.

        @return flag indicating whether this operation was successful
        @rtype bool
        """
        if self.isDirty():
            res = EricMessageBox.okToClearData(
                self.parent(),
                self.tr("Close Multiproject"),
                self.tr("The current multiproject has unsaved changes."),
                self.saveMultiProject,
            )
            if res:
                self.setDirty(False)
            return res

        return True

    def closeMultiProject(self):
        """
        Public slot to close the current multi project.

        @return flag indicating success
        @rtype bool
        """
        # save the list of recently opened projects
        self.__saveRecent()

        if not self.isOpen():
            return True

        if not self.checkDirty():
            return False

        # now close the current project, if it belongs to the multi project
        pfile = self.projectObject.getProjectFile()
        if pfile:
            for project in self.__projects.values():
                if project.file == pfile:
                    if not self.projectObject.closeProject():
                        return False
                    break

        self.__initData()
        self.closeAct.setEnabled(False)
        self.saveasAct.setEnabled(False)
        self.saveAct.setEnabled(False)
        self.addProjectAct.setEnabled(False)
        self.propsAct.setEnabled(False)

        self.multiProjectClosed.emit()

        return True

    def initActions(self):
        """
        Public slot to initialize the multi project related actions.
        """
        self.actions = []

        self.actGrp1 = createActionGroup(self)

        act = EricAction(
            self.tr("New multiproject"),
            EricPixmapCache.getIcon("multiProjectNew"),
            self.tr("&New..."),
            0,
            0,
            self.actGrp1,
            "multi_project_new",
        )
        act.setStatusTip(self.tr("Generate a new multiproject"))
        act.setWhatsThis(
            self.tr(
                """<b>New...</b>"""
                """<p>This opens a dialog for entering the info for a"""
                """ new multiproject.</p>"""
            )
        )
        act.triggered.connect(self.__newMultiProject)
        self.actions.append(act)

        act = EricAction(
            self.tr("Open multiproject"),
            EricPixmapCache.getIcon("multiProjectOpen"),
            self.tr("&Open..."),
            0,
            0,
            self.actGrp1,
            "multi_project_open",
        )
        act.setStatusTip(self.tr("Open an existing multiproject"))
        act.setWhatsThis(
            self.tr("""<b>Open...</b><p>This opens an existing multiproject.</p>""")
        )
        act.triggered.connect(self.openMultiProject)
        self.actions.append(act)

        self.closeAct = EricAction(
            self.tr("Close multiproject"),
            EricPixmapCache.getIcon("multiProjectClose"),
            self.tr("&Close"),
            0,
            0,
            self,
            "multi_project_close",
        )
        self.closeAct.setStatusTip(self.tr("Close the current multiproject"))
        self.closeAct.setWhatsThis(
            self.tr("""<b>Close</b><p>This closes the current multiproject.</p>""")
        )
        self.closeAct.triggered.connect(self.closeMultiProject)
        self.actions.append(self.closeAct)

        self.saveAct = EricAction(
            self.tr("Save multiproject"),
            EricPixmapCache.getIcon("multiProjectSave"),
            self.tr("&Save"),
            0,
            0,
            self,
            "multi_project_save",
        )
        self.saveAct.setStatusTip(self.tr("Save the current multiproject"))
        self.saveAct.setWhatsThis(
            self.tr("""<b>Save</b><p>This saves the current multiproject.</p>""")
        )
        self.saveAct.triggered.connect(self.saveMultiProject)
        self.actions.append(self.saveAct)

        self.saveasAct = EricAction(
            self.tr("Save multiproject as"),
            EricPixmapCache.getIcon("multiProjectSaveAs"),
            self.tr("Save &as..."),
            0,
            0,
            self,
            "multi_project_save_as",
        )
        self.saveasAct.setStatusTip(
            self.tr("Save the current multiproject to a new file")
        )
        self.saveasAct.setWhatsThis(
            self.tr(
                """<b>Save as</b>"""
                """<p>This saves the current multiproject to a new file.</p>"""
            )
        )
        self.saveasAct.triggered.connect(self.saveMultiProjectAs)
        self.actions.append(self.saveasAct)

        self.addProjectAct = EricAction(
            self.tr("Add project to multiproject"),
            EricPixmapCache.getIcon("fileProject"),
            self.tr("Add &project..."),
            0,
            0,
            self,
            "multi_project_add_project",
        )
        self.addProjectAct.setStatusTip(
            self.tr("Add a project to the current multiproject")
        )
        self.addProjectAct.setWhatsThis(
            self.tr(
                """<b>Add project...</b>"""
                """<p>This opens a dialog for adding a project"""
                """ to the current multiproject.</p>"""
            )
        )
        self.addProjectAct.triggered.connect(self.addNewProject)
        self.actions.append(self.addProjectAct)

        self.propsAct = EricAction(
            self.tr("Multiproject properties"),
            EricPixmapCache.getIcon("multiProjectProps"),
            self.tr("&Properties..."),
            0,
            0,
            self,
            "multi_project_properties",
        )
        self.propsAct.setStatusTip(self.tr("Show the multiproject properties"))
        self.propsAct.setWhatsThis(
            self.tr(
                """<b>Properties...</b>"""
                """<p>This shows a dialog to edit the multiproject"""
                """ properties.</p>"""
            )
        )
        self.propsAct.triggered.connect(self.__showProperties)
        self.actions.append(self.propsAct)

        self.clearRemovedAct = EricAction(
            self.tr("Clear Out"),
            EricPixmapCache.getIcon("clear"),
            self.tr("Clear Out"),
            0,
            0,
            self,
            "multi_project_clearout",
        )
        self.clearRemovedAct.setStatusTip(
            self.tr("Remove all projects marked as removed")
        )
        self.clearRemovedAct.setWhatsThis(
            self.tr(
                """<b>Clear Out...</b>"""
                """<p>This removes all projects marked as removed.</p>"""
            )
        )
        self.clearRemovedAct.triggered.connect(self.clearRemovedProjects)
        self.actions.append(self.clearRemovedAct)

        self.closeAct.setEnabled(False)
        self.saveAct.setEnabled(False)
        self.saveasAct.setEnabled(False)
        self.addProjectAct.setEnabled(False)
        self.propsAct.setEnabled(False)
        self.clearRemovedAct.setEnabled(False)

    def initMenu(self):
        """
        Public slot to initialize the multi project menu.

        @return the menu generated
        @rtype QMenu
        """
        menu = QMenu(self.tr("&Multiproject"), self.parent())
        self.recentMenu = QMenu(self.tr("Open &Recent Multiprojects"), menu)
        self.recentMenu.setIcon(EricPixmapCache.getIcon("multiProjectOpenRecent"))

        self.__menus = {
            "Main": menu,
            "Recent": self.recentMenu,
        }

        # connect the aboutToShow signals
        self.recentMenu.aboutToShow.connect(self.__showContextMenuRecent)
        self.recentMenu.triggered.connect(self.__openRecent)
        menu.aboutToShow.connect(self.__showMenu)

        # build the main menu
        menu.setTearOffEnabled(True)
        menu.addActions(self.actGrp1.actions())
        self.menuRecentAct = menu.addMenu(self.recentMenu)
        menu.addSeparator()
        menu.addAction(self.closeAct)
        menu.addSeparator()
        menu.addAction(self.saveAct)
        menu.addAction(self.saveasAct)
        menu.addSeparator()
        menu.addAction(self.addProjectAct)
        menu.addSeparator()
        menu.addAction(self.clearRemovedAct)
        menu.addSeparator()
        menu.addAction(self.propsAct)

        self.menu = menu
        return menu

    def initToolbar(self, toolbarManager):
        """
        Public slot to initialize the multi project toolbar.

        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        @return the toolbar generated
        @rtype QToolBar
        """
        tb = QToolBar(self.tr("Multiproject"), self.ui)
        tb.setObjectName("MultiProjectToolbar")
        tb.setToolTip(self.tr("Multiproject"))

        tb.addActions(self.actGrp1.actions())
        tb.addAction(self.closeAct)
        tb.addSeparator()
        tb.addAction(self.saveAct)
        tb.addAction(self.saveasAct)

        toolbarManager.addToolBar(tb, tb.windowTitle())
        toolbarManager.addAction(self.addProjectAct, tb.windowTitle())
        toolbarManager.addAction(self.propsAct, tb.windowTitle())
        toolbarManager.addAction(self.clearRemovedAct, tb.windowTitle())

        return tb

    def __showMenu(self):
        """
        Private method to set up the multi project menu.
        """
        self.menuRecentAct.setEnabled(len(self.recent) > 0)

        self.showMenu.emit("Main", self.__menus["Main"])

    def __syncRecent(self):
        """
        Private method to synchronize the list of recently opened multi
        projects with the central store.
        """
        for recent in self.recent[:]:
            if FileSystemUtilities.samepath(self.pfile, recent):
                self.recent.remove(recent)
        self.recent.insert(0, self.pfile)
        maxRecent = Preferences.getProject("RecentNumber")
        if len(self.recent) > maxRecent:
            self.recent = self.recent[:maxRecent]
        self.__saveRecent()

    def __showContextMenuRecent(self):
        """
        Private method to set up the recent multi projects menu.
        """
        self.__loadRecent()

        self.recentMenu.clear()

        for idx, rp in enumerate(self.recent, start=1):
            formatStr = "&{0:d}. {1}" if idx < 10 else "{0:d}. {1}"
            act = self.recentMenu.addAction(
                formatStr.format(
                    idx, FileSystemUtilities.compactPath(rp, self.ui.maxMenuFilePathLen)
                )
            )
            act.setData(rp)
            act.setEnabled(pathlib.Path(rp).exists())

        self.recentMenu.addSeparator()
        self.recentMenu.addAction(self.tr("&Clear"), self.clearRecent)

    def __openRecent(self, act):
        """
        Private method to open a multi project from the list of rencently
        opened multi projects.

        @param act reference to the action that triggered
        @type QAction
        """
        file = act.data()
        if file:
            self.openMultiProject(file)

    def clearRecent(self):
        """
        Public method to clear the recent multi projects menu.
        """
        self.recent = []
        self.__saveRecent()

    def getActions(self):
        """
        Public method to get a list of all actions.

        @return list of all actions
        @rtype list of EricAction
        """
        return self.actions[:]

    def addEricActions(self, actions):
        """
        Public method to add actions to the list of actions.

        @param actions list of actions
        @type list of EricAction
        """
        self.actions.extend(actions)

    def removeEricActions(self, actions):
        """
        Public method to remove actions from the list of actions.

        @param actions list of actions
        @type list of EricAction
        """
        for act in actions:
            with contextlib.suppress(ValueError):
                self.actions.remove(act)

    def getMenu(self, menuName):
        """
        Public method to get a reference to the main menu or a submenu.

        @param menuName name of the menu
        @type str
        @return reference to the requested menu
        @rtype QMenu or None
        """
        try:
            return self.__menus[menuName]
        except KeyError:
            return None

    def openProject(self, filename):
        """
        Public slot to open a project.

        @param filename filename of the project file
        @type str
        """
        self.projectObject.openProject(filename)
        self.projectOpened.emit(filename)

    def __openMainProject(self, reopen=True):
        """
        Private slot to open the main project.

        @param reopen flag indicating, that the main project should be
            reopened, if it has been opened already
        @type bool
        """
        for project in self.__projects.values():
            if (
                project.main
                and not project.removed
                and (
                    reopen
                    or not self.projectObject.isOpen()
                    or self.projectObject.getProjectFile() != project.file
                )
            ):
                self.openProject(project.file)
                return

    def getMainProjectFile(self):
        """
        Public method to get the filename of the main project.

        @return name of the main project file
        @rtype str
        """
        for project in self.__projects:
            if project.main:
                return project.file

        return None

    def getDependantProjectFiles(self):
        """
        Public method to get the filenames of the dependent projects.

        @return names of the dependent project files
        @rtype list of str
        """
        files = []
        for project in self.__projects.values():
            if not project.main:
                files.append(project.file)
        return files

    def __checkFilesExist(self):
        """
        Private method to check, if the files in a list exist.

        The project files are checked for existance in the
        filesystem. Non existant projects are removed from the list and the
        dirty state of the multi project is changed accordingly.
        """
        for project in self.__projects.values():
            project.removed = not os.path.exists(project.file)
            self.clearRemovedAct.setEnabled(True)

    @pyqtSlot()
    def clearRemovedProjects(self):
        """
        Public slot to clear out all projects marked as removed.
        """
        for key in list(self.__projects.keys()):
            if self.__projects[key].removed:
                self.removeProject(key)

        self.clearRemovedAct.setEnabled(False)

    def hasRemovedProjects(self):
        """
        Public method to check for removed projects.

        @return flag indicating the existence of a removed project
        @rtype bool
        """
        return any(p.removed for p in self.__projects.values())
