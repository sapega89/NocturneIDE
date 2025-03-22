# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the project management functionality.
"""

import collections
import contextlib
import copy
import fnmatch
import glob
import json
import os
import pathlib
import shutil
import time
import zipfile

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtCore import (
    QByteArray,
    QCryptographicHash,
    QObject,
    QProcess,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QDialog, QInputDialog, QLineEdit, QMenu, QToolBar

from eric7 import EricUtilities, Preferences, Utilities
from eric7.CodeFormatting.BlackFormattingAction import BlackFormattingAction
from eric7.CodeFormatting.BlackUtilities import aboutBlack
from eric7.CodeFormatting.IsortFormattingAction import IsortFormattingAction
from eric7.CodeFormatting.IsortUtilities import aboutIsort
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction, createActionGroup
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor, EricOverridenCursor
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricListSelectionDialog import EricListSelectionDialog
from eric7.EricWidgets.EricProgressDialog import EricProgressDialog
from eric7.Globals import recentNameProject
from eric7.RemoteServerInterface import EricServerFileDialog
from eric7.Sessions.SessionFile import SessionFile
from eric7.SystemUtilities import (
    FileSystemUtilities,
    OSUtilities,
    PythonUtilities,
    QtUtilities,
)
from eric7.Tasks.TasksFile import TasksFile
from eric7.UI.NotificationWidget import NotificationTypes
from eric7.Utilities.uic import compileOneUi
from eric7.VCS.VersionControl import VersionControlState

from .DebuggerPropertiesFile import DebuggerPropertiesFile
from .FileCategoryRepositoryItem import FileCategoryRepositoryItem
from .ProjectBrowserModel import ProjectBrowserModel
from .ProjectFile import ProjectFile
from .UserProjectFile import UserProjectFile


class Project(QObject):
    """
    Class implementing the project management functionality.

    @signal dirty(bool) emitted when the dirty state changes
    @signal projectFileAdded(str, str) emitted after a new file was added
    @signal projectFileRemoved(str, str) emitted after a file of the project was removed
    @signal projectFileCompiled(str, str) emitted after a form was compiled
    @signal projectLanguageAddedByCode(str) emitted after a new language was
        added. The language code is sent by this signal.
    @signal projectAboutToBeCreated() emitted just before the project will be
        created
    @signal newProjectHooks() emitted after a new project was generated but
        before the newProject() signal is sent
    @signal newProject() emitted after a new project was generated
    @signal sourceFile(str) emitted after a project file was read to
        open the main script
    @signal designerFile(str) emitted to open a found designer file
    @signal linguistFile(str) emitted to open a found translation file
    @signal projectOpenedHooks() emitted after a project file was read but
        before the projectOpened() signal is sent
    @signal projectOpened() emitted after a project file was read
    @signal projectClosedHooks() emitted after a project file was closed but
        before the projectClosed() signal is sent
    @signal projectClosed(shutdown) emitted after a project was closed sending
        a flag indicating the IDE shutdown operation
    @signal projectFileRenamed(str, str) emitted after a file of the project
        has been renamed
    @signal projectPropertiesChanged() emitted after the project properties
        were changed
    @signal directoryRemoved(str) emitted after a directory has been removed
        from the project
    @signal prepareRepopulateItem(str) emitted before an item of the model is
        repopulated
    @signal completeRepopulateItem(str) emitted after an item of the model was
        repopulated
    @signal vcsStatusMonitorData(list) emitted to signal the VCS status data
    @signal vcsStatusMonitorAllData(dict) emitted to signal all VCS status
        (key is project relative file name, value is status)
    @signal vcsStatusMonitorStatus(str, str) emitted to signal the status of
        the monitoring thread (ok, nok, op, off) and a status message
    @signal vcsStatusMonitorInfo(str) emitted to signal some info of the
        monitoring thread
    @signal vcsCommitted() emitted to indicate a completed commit action
    @signal reinitVCS() emitted after the VCS has been reinitialized
    @signal showMenu(str, QMenu) emitted when a menu is about to be shown. The
        name of the menu and a reference to the menu are given.
    @signal lexerAssociationsChanged() emitted after the lexer associations
        have been changed
    @signal projectChanged() emitted to signal a change of the project
    @signal appendStdout(str) emitted after something was received from
        a QProcess on stdout
    @signal appendStderr(str) emitted after something was received from
        a QProcess on stderr
    @signal processChangedProjectFiles() emitted to indicate, that changed project files
        should be processed
    """

    dirty = pyqtSignal(bool)
    projectFileAdded = pyqtSignal(str, str)
    projectFileRemoved = pyqtSignal(str, str)
    projectFileCompiled = pyqtSignal(str, str)
    projectLanguageAddedByCode = pyqtSignal(str)
    projectAboutToBeCreated = pyqtSignal()
    newProjectHooks = pyqtSignal()
    newProject = pyqtSignal()
    sourceFile = pyqtSignal(str)
    designerFile = pyqtSignal(str)
    linguistFile = pyqtSignal(str)
    projectOpenedHooks = pyqtSignal()
    projectOpened = pyqtSignal()
    projectClosedHooks = pyqtSignal()
    projectClosed = pyqtSignal(bool)
    projectFileRenamed = pyqtSignal(str, str)
    projectPropertiesChanged = pyqtSignal()
    directoryRemoved = pyqtSignal(str)
    prepareRepopulateItem = pyqtSignal(str)
    completeRepopulateItem = pyqtSignal(str)
    vcsStatusMonitorData = pyqtSignal(list)
    vcsStatusMonitorAllData = pyqtSignal(dict)
    vcsStatusMonitorStatus = pyqtSignal(str, str)
    vcsStatusMonitorInfo = pyqtSignal(str)
    vcsCommitted = pyqtSignal()
    reinitVCS = pyqtSignal()
    showMenu = pyqtSignal(str, QMenu)
    lexerAssociationsChanged = pyqtSignal()
    projectChanged = pyqtSignal()
    appendStdout = pyqtSignal(str)
    appendStderr = pyqtSignal(str)
    processChangedProjectFiles = pyqtSignal()

    eols = [os.linesep, "\n", "\r", "\r\n"]

    DefaultMake = "make"
    DefaultMakefile = "makefile"

    def __init__(self, parent=None, filename=None, remoteServer=None):
        """
        Constructor

        @param parent parent widget (usually the ui object)
        @type QWidget
        @param filename optional filename of a project file to open (defaults to None)
        @type str (optional)
        @param remoteServer reference to the 'eric-ide' server interface object
        @type EricServerInterface
        """
        super().__init__(parent)

        self.ui = parent
        self.__remoteServer = remoteServer
        self.__remotefsInterface = remoteServer.getServiceInterface("FileSystem")

        self.__progLanguages = [
            "Python3",
            "MicroPython",
            "Ruby",
            "JavaScript",
        ]

        self.__dbgFilters = {
            "Python3": self.tr(
                "Python3 Files (*.py *.py3);;Python3 GUI Files (*.pyw *.pyw3);;"
            ),
        }

        self.__fileCategoriesRepository = {}
        # This dictionary will be populated by the various project browsers with
        # classes of type 'FileCategoryRepositoryItem' using the 'addFileCategory()
        # and removeFileCategory() methods.

        self.vcsMenu = None
        self.__makeProcess = None

        self.__initProjectTypes()

        self.__initData()

        self.__projectFile = ProjectFile(self)
        self.__userProjectFile = UserProjectFile(self)
        self.__debuggerPropertiesFile = DebuggerPropertiesFile(self)
        self.__sessionFile = SessionFile(False)
        self.__tasksFile = TasksFile(False)

        self.recent = []
        self.__loadRecent()

        if filename is not None:
            self.openProject(filename)
        else:
            self.vcs = self.initVCS()

        self.__model = ProjectBrowserModel(self, fsInterface=self.__remotefsInterface)

        self.codemetrics = None
        self.codecoverage = None
        self.profiledata = None
        self.applicationDiagram = None
        self.loadedDiagram = None
        self.__findProjectFileDialog = None

        self.processChangedProjectFiles.connect(self.__autoExecuteMake)

    def addFileCategory(self, category, categoryItem):
        """
        Public method to add a file category to the categories repository.

        Note: The given category must not be contained in the repository already.

        @param category file category (must be unique)
        @type str
        @param categoryItem data class instance containing the category data
        @type FileCategoryRepositoryItem
        @exception TypeError raised to signal a wrong type for the category item
        """
        if not isinstance(categoryItem, FileCategoryRepositoryItem):
            raise TypeError(
                "'categoryItem' must be an instance of 'FileCategoryRepositoryItem'."
            )

        category = category.upper()
        if category in self.__fileCategoriesRepository:
            EricMessageBox.critical(
                self.ui,
                self.tr("Add File Category"),
                self.tr(
                    "<p>The file category <b>{0}</b> has already been added. This"
                    " attempt will be ignored.</p>"
                ).format(category),
            )
        else:
            self.__fileCategoriesRepository[category] = categoryItem
            with contextlib.suppress(AttributeError):
                self.__pdata[category] = []

    def removeFileCategory(self, category):
        """
        Public method to remove a category from the categories repository.

        Note: If the category is not contained in the repository, the request to
        remove it will be ignored silently.

        @param category file category
        @type str
        """
        with contextlib.suppress(KeyError):
            del self.__fileCategoriesRepository[category.upper()]

    def __sourceExtensions(self, language):
        """
        Private method to get the source extensions of a programming language.

        @param language programming language
        @type str
        @return source extensions
        @rtype list of str
        """
        if language == "Python3":
            extensions = Preferences.getPython("Python3Extensions")
            # *.py and *.pyw should always be associated with source files
            for ext in [".py", ".pyw"]:
                if ext not in extensions:
                    extensions.append(ext)
            return extensions
        elif language == "MicroPython":
            extensions = Preferences.getPython("Python3Extensions")
            # *.py should always be associated with source files
            for ext in [".py"]:
                if ext not in extensions:
                    extensions.append(ext)
            return extensions
        else:
            return {
                "Ruby": [".rb"],
                "JavaScript": [".js"],
                "Mixed": (Preferences.getPython("Python3Extensions") + [".rb", ".js"]),
            }.get(language, "")

    def getProgrammingLanguages(self):
        """
        Public method to get the programming languages supported by project.

        @return list of supported programming languages
        @rtype list of str
        """
        return self.__progLanguages[:]

    def getDebuggerFilters(self, language):
        """
        Public method to get the debugger filters for a programming language.

        @param language programming language
        @type str
        @return filter string
        @rtype str
        """
        try:
            return self.__dbgFilters[language]
        except KeyError:
            return ""

    def __initProjectTypes(self):
        """
        Private method to initialize the list of supported project types.
        """
        self.__fileTypeCallbacks = {}
        self.__lexerAssociationCallbacks = {}
        self.__binaryTranslationsCallbacks = {}

        self.__projectTypes = {
            "PyQt5": self.tr("PyQt5 GUI"),
            "PyQt5C": self.tr("PyQt5 Console"),
            "PyQt6": self.tr("PyQt6 GUI"),
            "PyQt6C": self.tr("PyQt6 Console"),
            "E7Plugin": self.tr("Eric7 Plugin"),
            "Console": self.tr("Console"),
            "Other": self.tr("Other"),
        }

        self.__projectProgLanguages = {
            "Python3": [
                "PyQt5",
                "PyQt5C",
                "PyQt6",
                "PyQt6C",
                "E7Plugin",
                "Console",
                "Other",
            ],
            "MicroPython": ["Console", "Other"],
            "Ruby": ["Console", "Other"],
            "JavaScript": ["Other"],
        }

        if QtUtilities.checkPyside(variant=2):
            self.__projectTypes["PySide2"] = self.tr("PySide2 GUI")
            self.__projectTypes["PySide2C"] = self.tr("PySide2 Console")
            self.__projectProgLanguages["Python3"].extend(["PySide2", "PySide2C"])

        if QtUtilities.checkPyside(variant=6):
            self.__projectTypes["PySide6"] = self.tr("PySide6 GUI")
            self.__projectTypes["PySide6C"] = self.tr("PySide6 Console")
            self.__projectProgLanguages["Python3"].extend(["PySide6", "PySide6C"])

    def getProjectTypes(self, progLanguage=""):
        """
        Public method to get the list of supported project types.

        @param progLanguage programming language to get project types for
        @type str
        @return reference to the dictionary of project types.
        @rtype dict
        """
        if progLanguage and progLanguage in self.__projectProgLanguages:
            ptypes = {}
            for ptype in self.__projectProgLanguages[progLanguage]:
                ptypes[ptype] = self.__projectTypes[ptype]
            return ptypes
        else:
            return self.__projectTypes

    def hasProjectType(self, type_, progLanguage=""):
        """
        Public method to check, if a project type is already registered.

        @param type_ internal type designator
        @type str
        @param progLanguage programming language of the project type
        @type str
        @return flag indicating presence of the project type
        @rtype bool
        """
        if progLanguage:
            return (
                progLanguage in self.__projectProgLanguages
                and type_ in self.__projectProgLanguages[progLanguage]
            )
        else:
            return type_ in self.__projectTypes

    def registerProjectType(
        self,
        type_,
        description,
        fileTypeCallback=None,
        binaryTranslationsCallback=None,
        lexerAssociationCallback=None,
        progLanguages=None,
    ):
        """
        Public method to register a project type.

        @param type_ internal type designator to be registered
        @type str
        @param description more verbose type name (display string)
        @type str
        @param fileTypeCallback reference to a method returning a dictionary
            of filetype associations
        @type function
        @param binaryTranslationsCallback reference to a method returning
            the name of the binary translation file given the name of the raw
            translation file
        @type function
        @param lexerAssociationCallback reference to a method returning the
            lexer type to be used for syntax highlighting given the name of
            a file
        @type function
        @param progLanguages programming languages supported by the
            project type
        @type list of str
        """
        if progLanguages:
            for progLanguage in progLanguages:
                if progLanguage not in self.__projectProgLanguages:
                    EricMessageBox.critical(
                        self.ui,
                        self.tr("Registering Project Type"),
                        self.tr(
                            """<p>The Programming Language <b>{0}</b> is not"""
                            """ supported (project type: {1}).</p>"""
                        ).format(progLanguage, type_),
                    )
                    return

                if type_ in self.__projectProgLanguages[progLanguage]:
                    EricMessageBox.critical(
                        self.ui,
                        self.tr("Registering Project Type"),
                        self.tr(
                            """<p>The Project type <b>{0}</b> is already"""
                            """ registered with Programming Language"""
                            """ <b>{1}</b>.</p>"""
                        ).format(type_, progLanguage),
                    )
                    return

        if type_ in self.__projectTypes:
            EricMessageBox.critical(
                self.ui,
                self.tr("Registering Project Type"),
                self.tr(
                    """<p>The Project type <b>{0}</b> is already"""
                    """ registered.</p>"""
                ).format(type_),
            )
        else:
            self.__projectTypes[type_] = description
            self.__fileTypeCallbacks[type_] = fileTypeCallback
            self.__lexerAssociationCallbacks[type_] = lexerAssociationCallback
            self.__binaryTranslationsCallbacks[type_] = binaryTranslationsCallback
            if progLanguages:
                for progLanguage in progLanguages:
                    self.__projectProgLanguages[progLanguage].append(type_)
            else:
                # no specific programming languages given -> add to all
                for progLanguage in self.__projectProgLanguages:
                    self.__projectProgLanguages[progLanguage].append(type_)

    def unregisterProjectType(self, type_):
        """
        Public method to unregister a project type.

        @param type_ internal type designator to be unregistered
        @type str
        """
        for progLanguage in self.__projectProgLanguages:
            if type_ in self.__projectProgLanguages[progLanguage]:
                self.__projectProgLanguages[progLanguage].remove(type_)
        if type_ in self.__projectTypes:
            del self.__projectTypes[type_]
        if type_ in self.__fileTypeCallbacks:
            del self.__fileTypeCallbacks[type_]
        if type_ in self.__lexerAssociationCallbacks:
            del self.__lexerAssociationCallbacks[type_]
        if type_ in self.__binaryTranslationsCallbacks:
            del self.__binaryTranslationsCallbacks[type_]

    def __initData(self):
        """
        Private method to initialize the project data part.
        """
        self.loaded = False  # flag for the loaded status
        self.__dirty = False  # dirty flag
        self.pfile = ""  # name of the project file
        self.ppath = ""  # name of the project directory
        self.translationsRoot = ""  # the translations prefix
        self.name = ""
        self.opened = False
        self.subdirs = []
        # record the project dir as a relative path (i.e. empty path)
        self.vcs = None
        self.vcsRequested = False
        self.dbgVirtualEnv = ""
        self.dbgCmdline = ""
        self.dbgWd = ""
        self.dbgEnv = ""
        self.dbgExcList = []
        self.dbgExcIgnoreList = []
        self.dbgAutoClearShell = True
        self.dbgTracePython = False
        self.dbgAutoContinue = True
        self.dbgReportAllExceptions = False
        self.dbgEnableMultiprocess = True
        self.dbgMultiprocessNoDebug = ""
        self.dbgGlobalConfigOverride = {
            "enable": False,
            "redirect": True,
        }

        self.__pdata = {
            "DESCRIPTION": "",
            "VERSION": "",
            "TRANSLATIONEXCEPTIONS": [],
            "TRANSLATIONPATTERN": "",
            "TRANSLATIONSBINPATH": "",
            "TRANSLATIONSOURCESTARTPATH": "",
            "MAINSCRIPT": "",
            "VCS": "None",
            "VCSOPTIONS": {},
            "VCSOTHERDATA": {},
            "AUTHOR": "",
            "EMAIL": "",
            "HASH": "",
            "PROGLANGUAGE": "Python3",
            "MIXEDLANGUAGE": False,
            "PROJECTTYPE": "PyQt6",
            "SPELLLANGUAGE": Preferences.getEditor("SpellCheckingDefaultLanguage"),
            "SPELLWORDS": "",
            "SPELLEXCLUDES": "",
            "FILETYPES": {},
            "LEXERASSOCS": {},
            "PROJECTTYPESPECIFICDATA": {},
            "CHECKERSPARMS": {},
            "PACKAGERSPARMS": {},
            "DOCUMENTATIONPARMS": {},
            "OTHERTOOLSPARMS": {},
            "MAKEPARAMS": {
                "MakeEnabled": False,
                "MakeExecutable": "",
                "MakeFile": "",
                "MakeTarget": "",
                "MakeParameters": "",
                "MakeTestOnly": True,
            },
            "IDLPARAMS": {
                "IncludeDirs": [],
                "DefinedNames": [],
                "UndefinedNames": [],
            },
            "UICPARAMS": {
                "Package": "",
                "RcSuffix": "",
                "PackagesRoot": "",
            },
            "RCCPARAMS": {
                "CompressionThreshold": 70,  # default value
                "CompressLevel": 0,  # use zlib default
                "CompressionDisable": False,
                "PathPrefix": "",
            },
            "EOL": -1,
            "DOCSTRING": "",
            "TESTING_FRAMEWORK": "",
            "LICENSE": "",
            "EMBEDDED_VENV": False,
            "SOURCESDIR": "",
        }
        for category in self.__fileCategoriesRepository:
            self.__pdata[category] = []

        self.__initDebugProperties()

        self.pudata = {
            "VCSOVERRIDE": "",
            "VCSSTATUSMONITORINTERVAL": 0,
        }

        self.vcs = self.initVCS()

        self.__initVenvConfiguration()

    def getProjectData(self, dataKey=None, default=None):
        """
        Public method to get the data associated with the given data key.

        Note: If dataKey is None, a copy of the project data structure
        is returned.

        @param dataKey key of the data to get (defaults to None)
        @type str (optional)
        @param default default value for non-existent keys (defaults to None)
        @type Any (optional)
        @return requested data or None if the data key doesn't exist or
            a copy of the project data dictionary
        @rtype Any
        """
        if dataKey is None:
            return copy.deepcopy(self.__pdata)

        return self.__pdata.get(dataKey, default)

    def setProjectData(self, data, dataKey=None, setDirty=True):
        """
        Public method to set data associated with the given data key in the project
        dictionary.

        Note: If no data key is given or is None, the data must be a dictionary used
        to update the project data.

        @param data data to be set or a dictionary to update the project data
        @type Any
        @param dataKey key of the data to set (defaults to None)
        @type str (optional)
        @param setDirty flag indicating to set the dirty flag if the data is different
            from the current one (defaults to True)
        @type bool (optional)
        """
        if dataKey is None:
            self.__pdata.update(data)
        else:
            if self.__pdata[dataKey] != data and setDirty:
                self.setDirty(True)
            self.__pdata[dataKey] = data

    def getData(self, category, key, default=None):
        """
        Public method to get data out of the project data store.

        @param category category of the data to get (one of
            PROJECTTYPESPECIFICDATA, CHECKERSPARMS, PACKAGERSPARMS,
            DOCUMENTATIONPARMS or OTHERTOOLSPARMS)
        @type str
        @param key key of the data entry to get
        @type str
        @param default value to return in case the key is not found (defaults to None)
        @type Any (optional)
        @return a copy of the requested data or None
        @rtype Any
        """
        # __IGNORE_WARNING_D202__
        if (
            category
            in [
                "PROJECTTYPESPECIFICDATA",
                "CHECKERSPARMS",
                "PACKAGERSPARMS",
                "DOCUMENTATIONPARMS",
                "OTHERTOOLSPARMS",
            ]
            and key in self.__pdata[category]
        ):
            return copy.deepcopy(self.__pdata[category][key])
        else:
            return default

    def setData(self, category, key, data):
        """
        Public method to store data in the project data store.

        @param category category of the data to get (one of
            PROJECTTYPESPECIFICDATA, CHECKERSPARMS, PACKAGERSPARMS,
            DOCUMENTATIONPARMS or OTHERTOOLSPARMS)
        @type str
        @param key key of the data entry to get
        @type str
        @param data data to be stored
        @type Any
        @return flag indicating success
        @rtype bool
        """
        # __IGNORE_WARNING_D202__
        if category not in [
            "PROJECTTYPESPECIFICDATA",
            "CHECKERSPARMS",
            "PACKAGERSPARMS",
            "DOCUMENTATIONPARMS",
            "OTHERTOOLSPARMS",
        ]:
            return False

        # test for changes of data and save them in the project
        # 1. there were none, now there are
        if key not in self.__pdata[category] and len(data) > 0:
            self.__pdata[category][key] = copy.deepcopy(data)
            self.setDirty(True)
        # 2. there were some, now there aren't
        elif key in self.__pdata[category] and len(data) == 0:
            del self.__pdata[category][key]
            self.setDirty(True)
        # 3. there were some and still are
        elif key in self.__pdata[category] and len(data) > 0:
            if data != self.__pdata[category][key]:
                self.__pdata[category][key] = copy.deepcopy(data)
                self.setDirty(True)
        # 4. there were none and none are given
        else:
            return False
        return True

    def getFileCategories(self):
        """
        Public method to get the list of known file categories.

        @return list of known file categories
        @rtype list of str
        """
        return list(self.__fileCategoriesRepository)

    def getFileCategoryFilters(self, categories=None, withOthers=False, withAll=True):
        """
        Public method to get a list of file selection filters for the given categories.

        @param categories list of file type categories (defaults to None).
            A value of None means all categories except 'OTHERS'.
        @type list of str (optional)
        @param withOthers flag indicating to include the 'OTHERS' category
            (defaults to False)
        @type bool (optional)
        @param withAll flag indicating to include a filter for 'All Files'
            (defaults to True)
        @type bool (optional)
        @return list of file selection filter strings
        @rtype list of str
        """
        if categories is None:
            categories = [c for c in self.__fileCategoriesRepository if c != "OTHERS"]
            if withOthers:
                categories.append("OTHERS")

        patterns = collections.defaultdict(list)
        for pattern, filetype in self.__pdata["FILETYPES"].items():
            if filetype in categories and filetype in self.__fileCategoriesRepository:
                patterns[filetype].append(pattern)

        filters = []
        for filetype in patterns:
            filters.append(
                self.__fileCategoriesRepository[
                    filetype.upper()
                ].fileCategoryFilterTemplate.format(
                    " ".join(sorted(patterns[filetype]))
                )
            )
        filters = sorted(filters)
        if withAll:
            filters.append(self.tr("All Files (*)"))

        return filters

    def getFileCategoryFilterString(
        self, categories=None, withOthers=False, withAll=True
    ):
        """
        Public method to get a file selection string for the given categories.

        @param categories list of file type categories (defaults to None).
            A value of None means all categories except 'OTHERS'.
        @type list of str (optional)
        @param withOthers flag indicating to include the 'OTHERS' category
            (defaults to False)
        @type bool (optional)
        @param withAll flag indicating to include a filter for 'All Files'
            (defaults to True)
        @type bool (optional)
        @return file selection filter string
        @rtype str
        """
        return ";;".join(
            self.getFileCategoryFilters(
                categories=categories, withOthers=withOthers, withAll=withAll
            )
        )

    def getFileCategoryString(self, category):
        """
        Public method to get a user string for the given category.

        @param category file type category
        @type str
        @return user string for the category
        @rtype str
        """
        return self.__fileCategoriesRepository[category.upper()].fileCategoryUserString

    def getFileCategoryType(self, category):
        """
        Public method to get a user type string for the given category.

        @param category file type category
        @type str
        @return user type string for the category
        @rtype str
        """
        return self.__fileCategoriesRepository[category.upper()].fileCategoryTyeString

    def getFileCategoryExtension(self, category, reverse=False):
        """
        Public method to get a list of default file extensions for the given category.

        @param category file type category
        @type str
        @param reverse flag indicating to get all other extensions except the one of
            the given category
        @type bool
        @return list of default file extensions for the category
        @rtype list of str
        """
        if reverse:
            extensions = []
            for cat, item in self.__fileCategoriesRepository.items():
                if cat != category:
                    extensions += item.fileCategoryExtensions[:]
            return extensions
        else:
            return self.__fileCategoriesRepository[
                category.upper()
            ].fileCategoryExtensions[:]

    def initFileTypes(self):
        """
        Public method to initialize the file type associations with default
        values.
        """
        self.__pdata["FILETYPES"] = self.defaultFileTypes(
            self.__pdata["PROGLANGUAGE"],
            self.__pdata["MIXEDLANGUAGE"],
            self.__pdata["PROJECTTYPE"],
        )
        self.setDirty(True)

    def defaultFileTypes(self, progLanguage, isMixed, projectType):
        """
        Public method to get a dictionary containing the default file type associations.

        @param progLanguage programming language (main language)
        @type str
        @param isMixed flag indicating a project with multiple programming languages
        @type bool
        @param projectType type of the project
        @type str
        @return dictionary containing the default file type associations
        @rtype dict
        """
        fileTypesDict = {
            "*.txt": "OTHERS",
            "*.md": "OTHERS",
            "*.rst": "OTHERS",
            "README": "OTHERS",
            "README.*": "OTHERS",
            "*.epj": "OTHERS",
            "GNUmakefile": "OTHERS",
            "makefile": "OTHERS",
            "Makefile": "OTHERS",
            "*.ini": "OTHERS",
            "*.cfg": "OTHERS",
            "*.toml": "OTHERS",
            "*.json": "OTHERS",
            "*.yml": "OTHERS",
            "*.yaml": "OTHERS",
        }

        # Sources
        sourceKey = "Mixed" if isMixed else progLanguage
        for ext in self.__sourceExtensions(sourceKey):
            fileTypesDict["*{0}".format(ext)] = "SOURCES"

        # Forms
        if projectType in [
            "E7Plugin",
            "PyQt5",
            "PyQt6",
            "PySide2",
            "PySide6",
        ]:
            fileTypesDict["*.ui"] = "FORMS"

        # Resources
        if projectType in [
            "PyQt5",
            "PyQt5C",
            "PySide2",
            "PySide2C",
            "PySide6",
            "PySide6C",
        ]:
            fileTypesDict["*.qrc"] = "RESOURCES"

        # Translations
        if projectType in [
            "E7Plugin",
            "PyQt5",
            "PyQt5C",
            "PyQt6",
            "PyQt6C",
            "PySide2",
            "PySide2C",
            "PySide6",
            "PySide6C",
        ]:
            fileTypesDict["*.ts"] = "TRANSLATIONS"
            fileTypesDict["*.qm"] = "TRANSLATIONS"

        # File categories handled by activated plugin project browsers
        for fileCategory in [
            f
            for f in self.__fileCategoriesRepository
            if f not in ["SOURCES", "FORMS", "RESOURCES", "TRANSLATIONS", "OTHERS"]
        ]:
            for ext in self.__fileCategoriesRepository[
                fileCategory.upper()
            ].fileCategoryExtensions:
                fileTypesDict[ext] = fileCategory
        # Project type specific ones
        with contextlib.suppress(KeyError):
            if self.__fileTypeCallbacks[projectType] is not None:
                ftypes = self.__fileTypeCallbacks[projectType]()
                fileTypesDict.update(ftypes)

        return fileTypesDict

    def updateFileTypes(self):
        """
        Public method to update the filetype associations with new default
        values.
        """
        if self.__pdata["PROJECTTYPE"] in [
            "E7Plugin",
            "PyQt5",
            "PyQt5C",
            "PyQt6",
            "PyQt6C",
            "PySide2",
            "PySide2C",
            "PySide6",
            "PySide6C",
        ]:
            if "*.ts" not in self.__pdata["FILETYPES"]:
                self.__pdata["FILETYPES"]["*.ts"] = "TRANSLATIONS"
            if "*.qm" not in self.__pdata["FILETYPES"]:
                self.__pdata["FILETYPES"]["*.qm"] = "TRANSLATIONS"
        with contextlib.suppress(KeyError):
            if self.__fileTypeCallbacks[self.__pdata["PROJECTTYPE"]] is not None:
                ftypes = self.__fileTypeCallbacks[self.__pdata["PROJECTTYPE"]]()
                for pattern, ftype in ftypes.items():
                    if pattern not in self.__pdata["FILETYPES"]:
                        self.__pdata["FILETYPES"][pattern] = ftype
                        self.setDirty(True)

    def __loadRecent(self):
        """
        Private method to load the recently opened project filenames.
        """
        self.recent = []
        Preferences.Prefs.rsettings.sync()
        rp = Preferences.Prefs.rsettings.value(recentNameProject)
        if rp is not None:
            for f in rp:
                if (
                    FileSystemUtilities.isRemoteFileName(f)
                    and (
                        not self.__remoteServer.isServerConnected()
                        or self.__remotefsInterface.exists(f)
                    )
                ) or pathlib.Path(f).exists():
                    self.recent.append(f)

    def __saveRecent(self):
        """
        Private method to save the list of recently opened filenames.
        """
        Preferences.Prefs.rsettings.setValue(recentNameProject, self.recent)
        Preferences.Prefs.rsettings.sync()

    def getMostRecent(self):
        """
        Public method to get the most recently opened project.

        @return path of the most recently opened project
        @rtype str
        """
        if len(self.recent):
            return self.recent[0]
        else:
            return None

    def getModel(self):
        """
        Public method to get a reference to the project browser model.

        @return reference to the project browser model
        @rtype ProjectBrowserModel
        """
        return self.__model

    def startFileSystemMonitoring(self):
        """
        Public method to (re)start monitoring the project file system.
        """
        self.__model.startFileSystemMonitoring()

    def stopFileSystemMonitoring(self):
        """
        Public method to stop monitoring the project file system.
        """
        self.__model.stopFileSystemMonitoring()

    def getVcs(self):
        """
        Public method to get a reference to the VCS object.

        @return reference to the VCS object
        @rtype VersionControl
        """
        return self.vcs

    def isVcsControlled(self):
        """
        Public method to check, if the project is controlled by a VCS.

        @return flag indicating a VCS controlled project
        @rtype bool
        """
        return self.vcs is not None

    def handlePreferencesChanged(self):
        """
        Public slot used to handle the preferencesChanged signal.
        """
        if self.pudata["VCSSTATUSMONITORINTERVAL"]:
            self.setStatusMonitorInterval(self.pudata["VCSSTATUSMONITORINTERVAL"])
        else:
            self.setStatusMonitorInterval(Preferences.getVCS("StatusMonitorInterval"))

        self.__model.preferencesChanged()

    def setDirty(self, dirty):
        """
        Public method to set the dirty state.

        It emits the signal dirty(bool).

        @param dirty dirty state
        @type bool
        """
        self.__dirty = dirty
        self.saveAct.setEnabled(dirty)
        self.dirty.emit(dirty)
        if self.__dirty:
            self.projectChanged.emit()

        # autosave functionality
        if dirty and Preferences.getProject("AutoSaveProject"):
            self.saveProject()

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

    def __checkFilesExist(self, index):
        """
        Private method to check, if the files in a list exist.

        The files in the indicated list are checked for existance in the
        filesystem. Non existant files are removed from the list and the
        dirty state of the project is changed accordingly.

        @param index key of the list to be checked
        @type str
        """
        removed = False
        removelist = []
        if FileSystemUtilities.isRemoteFileName(self.ppath):
            for file in self.__pdata[index]:
                if not self.__remotefsInterface.exists(
                    self.__remotefsInterface.join(self.ppath, file)
                ):
                    removelist.append(file)
                    removed = True
        else:
            for file in self.__pdata[index]:
                if not os.path.exists(os.path.join(self.ppath, file)):
                    removelist.append(file)
                    removed = True

        if removed:
            for file in removelist:
                self.__pdata[index].remove(file)
            self.setDirty(True)

    def __readProject(self, fn):
        """
        Private method to read in a project file (.epj).

        @param fn filename of the project file to be read
        @type str
        @return flag indicating success
        @rtype bool
        """
        with EricOverrideCursor():
            res = self.__projectFile.readFile(fn)

        if res:
            if FileSystemUtilities.isRemoteFileName(fn):
                self.pfile = fn
                self.ppath = self.__remotefsInterface.dirname(fn)
                self.name = self.__remotefsInterface.splitext(
                    self.__remotefsInterface.basename(fn)
                )[0]
                self.__remotefsInterface.populateFsCache(self.ppath)
            else:
                self.pfile = os.path.abspath(fn)
                self.ppath = os.path.abspath(os.path.dirname(fn))
                self.name = os.path.splitext(os.path.basename(fn))[0]

            # insert filename into list of recently opened projects
            self.__syncRecent()

            if self.__pdata["TRANSLATIONPATTERN"]:
                self.translationsRoot = self.__pdata["TRANSLATIONPATTERN"].split(
                    "%language%"
                )[0]
            elif self.__pdata["MAINSCRIPT"]:
                self.translationsRoot = os.path.splitext(self.__pdata["MAINSCRIPT"])[0]

            if FileSystemUtilities.isRemoteFileName(self.ppath):
                if self.__remotefsInterface.isdir(
                    self.__remotefsInterface.join(self.ppath, self.translationsRoot)
                ):
                    dn = self.translationsRoot
                else:
                    dn = self.__remotefsInterface.dirname(self.translationsRoot)
            else:
                if os.path.isdir(os.path.join(self.ppath, self.translationsRoot)):
                    dn = self.translationsRoot
                else:
                    dn = os.path.dirname(self.translationsRoot)
            if dn and dn not in self.subdirs:
                self.subdirs.append(dn)

            # check, if the files of the project still exist in the
            # project directory
            for fileCategory in self.getFileCategories():
                if fileCategory != "TRANSLATIONS":
                    self.__checkFilesExist(fileCategory)

            # get the names of subdirectories the files are stored in
            for fileCategory in [c for c in self.getFileCategories() if c != "OTHERS"]:
                for fn in self.__pdata[fileCategory]:
                    dn = (
                        self.__remotefsInterface.dirname(fn)
                        if FileSystemUtilities.isRemoteFileName(self.ppath)
                        else os.path.dirname(fn)
                    )
                    if dn and dn not in self.subdirs:
                        self.subdirs.append(dn)

        return res

    def __writeProject(self, fn=None):
        """
        Private method to save the project infos to a project file.

        @param fn optional filename of the project file to be written (string).
            If fn is None, the filename stored in the project object
            is used. This is the 'save' action. If fn is given, this filename
            is used instead of the one in the project object. This is the
            'save as' action.
        @type str
        @return flag indicating success
        @rtype bool
        """
        if self.vcs is not None:
            self.__pdata["VCSOPTIONS"] = copy.deepcopy(self.vcs.vcsGetOptions())
            self.__pdata["VCSOTHERDATA"] = copy.deepcopy(self.vcs.vcsGetOtherData())

        if not self.__pdata["HASH"]:
            hashStr = str(
                QCryptographicHash.hash(
                    QByteArray(self.ppath.encode("utf-8")),
                    QCryptographicHash.Algorithm.Sha1,
                ).toHex(),
                encoding="utf-8",
            )
            self.__pdata["HASH"] = hashStr

        if fn is None:
            fn = self.pfile

        with EricOverrideCursor():
            res = self.__projectFile.writeFile(fn)

        if res:
            if FileSystemUtilities.isRemoteFileName(fn):
                self.pfile = fn
                self.ppath = self.__remotefsInterface.dirname(fn)
                self.name = self.__remotefsInterface.splitext(
                    self.__remotefsInterface.basename(fn)
                )[0]
            else:
                self.pfile = os.path.abspath(fn)
                self.ppath = os.path.abspath(os.path.dirname(fn))
                self.name = os.path.splitext(os.path.basename(fn))[0]
            self.setDirty(False)

            # insert filename into list of recently opened projects
            self.__syncRecent()

        return res

    def __readUserProperties(self):
        """
        Private method to read in the user specific project file (.eqj).
        """
        if self.pfile is None:
            return

        if FileSystemUtilities.isRemoteFileName(self.pfile):
            fn1, _ext = self.__remotefsInterface.splitext(
                self.__remotefsInterface.basename(self.pfile)
            )
            fn = self.__remotefsInterface.join(
                self.getProjectManagementDir(), f"{fn1}.eqj"
            )
            if not self.__remotefsInterface.exists(fn):
                return
        else:
            fn1, _ext = os.path.splitext(os.path.basename(self.pfile))
            fn = os.path.join(self.getProjectManagementDir(), f"{fn1}.eqj")
            if not os.path.exists(fn):
                return

        self.__userProjectFile.readFile(fn)

    def __writeUserProperties(self):
        """
        Private method to write the user specific project data to a JSON file.
        """
        if self.pfile is None:
            return

        if FileSystemUtilities.isRemoteFileName(self.pfile):
            fn1, _ext = self.__remotefsInterface.splitext(
                self.__remotefsInterface.basename(self.pfile)
            )
            fn = self.__remotefsInterface.join(
                self.getProjectManagementDir(), f"{fn1}.eqj"
            )
        else:
            fn1, _ext = os.path.splitext(os.path.basename(self.pfile))
            fn = os.path.join(self.getProjectManagementDir(), f"{fn1}.eqj")

        with EricOverrideCursor():
            self.__userProjectFile.writeFile(fn)

    def __showContextMenuSession(self):
        """
        Private slot called before the Session menu is shown.
        """
        enable = True
        if self.pfile is None:
            enable = False
        else:
            if FileSystemUtilities.isRemoteFileName(self.pfile):
                fn, _ext = self.__remotefsInterface.splitext(
                    self.__remotefsInterface.basename(self.pfile)
                )
                fn_sess = self.__remotefsInterface.join(
                    self.getProjectManagementDir(), f"{fn}.esj"
                )
                enable = self.__remotefsInterface.exists(fn)
            else:
                fn, _ext = os.path.splitext(os.path.basename(self.pfile))
                fn_sess = os.path.join(self.getProjectManagementDir(), f"{fn}.esj")
                enable = os.path.exists(fn_sess)
        self.sessActGrp.findChild(QAction, "project_load_session").setEnabled(enable)
        self.sessActGrp.findChild(QAction, "project_delete_session").setEnabled(enable)

    @pyqtSlot()
    def __readSession(self, quiet=False, indicator=""):
        """
        Private method to read in the project session file (.esj).

        @param quiet flag indicating quiet operations.
                If this flag is true, no errors are reported.
        @type bool
        @param indicator indicator string
        @type str
        """
        if self.pfile is None:
            if not quiet:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Read Project Session"),
                    self.tr("Please save the project first."),
                )
            return

        if FileSystemUtilities.isRemoteFileName(self.pfile):
            fn1, _ext = self.__remotefsInterface.splitext(
                self.__remotefsInterface.basename(self.pfile)
            )
            fn = self.__remotefsInterface.join(
                self.getProjectManagementDir(), f"{fn1}{indicator}.esj"
            )
            if not self.__remotefsInterface.exists(fn):
                return
        else:
            fn1, _ext = os.path.splitext(os.path.basename(self.pfile))
            fn = os.path.join(self.getProjectManagementDir(), f"{fn1}{indicator}.esj")
            if not os.path.exists(fn):
                return

        self.__sessionFile.readFile(fn)

    @pyqtSlot()
    def __writeSession(self, quiet=False, indicator=""):
        """
        Private method to write the session data to an XML file (.esj).

        @param quiet flag indicating quiet operations.
            If this flag is true, no errors are reported.
        @type bool
        @param indicator indicator string
        @type str
        """
        if self.pfile is None:
            if not quiet:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Save Project Session"),
                    self.tr("Please save the project first."),
                )
            return

        if FileSystemUtilities.isRemoteFileName(self.pfile):
            fn1, _ext = self.__remotefsInterface.splitext(
                self.__remotefsInterface.basename(self.pfile)
            )
            fn = self.__remotefsInterface.join(
                self.getProjectManagementDir(), f"{fn1}{indicator}.esj"
            )
        else:
            fn1, _ext = os.path.splitext(os.path.basename(self.pfile))
            fn = os.path.join(self.getProjectManagementDir(), f"{fn1}{indicator}.esj")

        self.__sessionFile.writeFile(fn, withServer=False)

    def __deleteSession(self):
        """
        Private method to delete the session file.
        """
        if self.pfile is None:
            EricMessageBox.critical(
                self.ui,
                self.tr("Delete Project Session"),
                self.tr("Please save the project first."),
            )
            return

        try:
            if FileSystemUtilities.isRemoteFileName(self.pfile):
                title = self.tr("Delete Remote Project Session")
                fname, _ext = self.__remotefsInterface.splitext(
                    self.__remotefsInterface.basename(self.pfile)
                )
                fn = self.__remotefsInterface.join(
                    self.getProjectManagementDir(), f"{fname}.esj"
                )
                if self.__remotefsInterface.exists(fn):
                    self.__remotefsInterface.remove(fn)
            else:
                title = self.tr("Delete Project Session")
                fname, _ext = os.path.splitext(os.path.basename(self.pfile))
                fn = os.path.join(self.getProjectManagementDir(), f"{fname}.esj")
                if os.path.exists(fn):
                    os.remove(fn)
        except OSError:
            EricMessageBox.critical(
                self.ui,
                title,
                self.tr(
                    "<p>The project session file <b>{0}</b> could"
                    " not be deleted.</p>"
                ).format(fn),
            )

    def __readTasks(self):
        """
        Private method to read in the project tasks file (.etj).
        """
        if self.pfile is None:
            EricMessageBox.critical(
                self.ui,
                self.tr("Read Tasks"),
                self.tr("Please save the project first."),
            )
            return

        if FileSystemUtilities.isRemoteFileName(self.pfile):
            base, _ext = self.__remotefsInterface.splitext(
                self.__remotefsInterface.basename(self.pfile)
            )
            fn = self.__remotefsInterface.join(
                self.getProjectManagementDir(), f"{base}.etj"
            )
            if not self.__remotefsInterface.exists(fn):
                return
        else:
            base, ext = os.path.splitext(os.path.basename(self.pfile))
            fn = os.path.join(self.getProjectManagementDir(), f"{base}.etj")
            if not os.path.exists(fn):
                return

        self.__tasksFile.readFile(fn)

    def writeTasks(self):
        """
        Public method to write the tasks data to a JSON file (.etj).
        """
        if self.pfile is None:
            return

        if FileSystemUtilities.isRemoteFileName(self.pfile):
            base, _ext = self.__remotefsInterface.splitext(
                self.__remotefsInterface.basename(self.pfile)
            )
            fn = self.__remotefsInterface.join(
                self.getProjectManagementDir(), f"{base}.etj"
            )
        else:
            base, ext = os.path.splitext(os.path.basename(self.pfile))
            fn = os.path.join(self.getProjectManagementDir(), f"{base}.etj")

        self.__tasksFile.writeFile(fn)

    def __showContextMenuDebugger(self):
        """
        Private slot called before the Debugger menu is shown.
        """
        enable = True
        if self.pfile is None:
            enable = False
        else:
            if FileSystemUtilities.isRemoteFileName(self.pfile):
                fn1, _ext = self.__remotefsInterface.splitext(
                    self.__remotefsInterface.basename(self.pfile)
                )
                fn = self.__remotefsInterface.join(
                    self.getProjectManagementDir(), f"{fn1}.edj"
                )
                enable = self.__remotefsInterface.exists(fn)
            else:
                fn1, _ext = os.path.splitext(os.path.basename(self.pfile))
                fn = os.path.join(self.getProjectManagementDir(), f"{fn1}.edj")
                enable = os.path.exists(fn)
        self.dbgActGrp.findChild(
            QAction, "project_debugger_properties_load"
        ).setEnabled(enable)
        self.dbgActGrp.findChild(
            QAction, "project_debugger_properties_delete"
        ).setEnabled(enable)

    @pyqtSlot()
    def __readDebugProperties(self, quiet=False):
        """
        Private method to read in the project debugger properties file (.edj).

        @param quiet flag indicating quiet operations.
            If this flag is true, no errors are reported.
        @type bool
        """
        if self.pfile is None:
            if not quiet:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Read Debugger Properties"),
                    self.tr("Please save the project first."),
                )
            return

        if FileSystemUtilities.isRemoteFileName(self.pfile):
            fn1, _ext = self.__remotefsInterface.splitext(
                self.__remotefsInterface.basename(self.pfile)
            )
            fn = self.__remotefsInterface.join(
                self.getProjectManagementDir(), f"{fn1}.edj"
            )
            if not self.__remotefsInterface.exists(fn):
                return
        else:
            fn1, _ext = os.path.splitext(os.path.basename(self.pfile))
            fn = os.path.join(self.getProjectManagementDir(), f"{fn1}.edj")
            if not os.path.exists(fn):
                return
        if self.__debuggerPropertiesFile.readFile(fn):
            self.debugPropertiesLoaded = True
            self.debugPropertiesChanged = False

    @pyqtSlot()
    def __writeDebugProperties(self, quiet=False):
        """
        Private method to write the project debugger properties file (.edj).

        @param quiet flag indicating quiet operations.
                If this flag is true, no errors are reported.
        @type bool
        """
        if self.pfile is None:
            if not quiet:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Save Debugger Properties"),
                    self.tr("Please save the project first."),
                )
            return

        if FileSystemUtilities.isRemoteFileName(self.pfile):
            fn1, _ext = self.__remotefsInterface.splitext(
                self.__remotefsInterface.basename(self.pfile)
            )
            fn = self.__remotefsInterface.join(
                self.getProjectManagementDir(), f"{fn1}.edj"
            )
        else:
            fn1, _ext = os.path.splitext(os.path.basename(self.pfile))
            fn = os.path.join(self.getProjectManagementDir(), f"{fn1}.edj")

        with EricOverrideCursor():
            self.__debuggerPropertiesFile.writeFile(fn)

    def __deleteDebugProperties(self):
        """
        Private method to delete the project debugger properties file (.edj).
        """
        if self.pfile is None:
            EricMessageBox.critical(
                self.ui,
                self.tr("Delete Debugger Properties"),
                self.tr("Please save the project first."),
            )
            return

        try:
            if FileSystemUtilities.isRemoteFileName(self.pfile):
                title = self.tr("Delete Remote Debugger Properties")
                fname, _ext = self.__remotefsInterface.splitext(
                    self.__remotefsInterface.basename(self.pfile)
                )
                fn = self.__remotefsInterface.join(
                    self.getProjectManagementDir(), f"{fname}.edj"
                )
                if self.__remotefsInterface.exists(fn):
                    self.__remotefsInterface.remove(fn)
            else:
                title = self.tr("Delete Debugger Properties")
                fname, _ext = os.path.splitext(os.path.basename(self.pfile))
                fn = os.path.join(self.getProjectManagementDir(), f"{fname}.edj")
                if os.path.exists(fn):
                    os.remove(fn)
        except OSError:
            EricMessageBox.critical(
                self.ui,
                title,
                self.tr(
                    "<p>The project debugger properties file"
                    " <b>{0}</b> could not be deleted.</p>"
                ).format(fn),
            )

    def __initDebugProperties(self):
        """
        Private method to initialize the debug properties.
        """
        self.debugPropertiesLoaded = False
        self.debugPropertiesChanged = False
        self.debugProperties = {
            "VIRTUALENV": "",
            "DEBUGCLIENT": "",
            "ENVIRONMENTOVERRIDE": False,
            "ENVIRONMENTSTRING": "",
            "REMOTEDEBUGGER": False,
            "REMOTEHOST": "",
            "REMOTECOMMAND": "",
            "REMOTEDEBUGCLIENT": "",
            "PATHTRANSLATION": False,
            "REMOTEPATH": "",
            "LOCALPATH": "",
            "CONSOLEDEBUGGER": False,
            "CONSOLECOMMAND": "",
            "REDIRECT": False,
            "NOENCODING": False,
        }

    def isDebugPropertiesLoaded(self):
        """
        Public method to return the status of the debug properties.

        @return load status of debug properties
        @rtype bool
        """
        return self.debugPropertiesLoaded

    def __showDebugProperties(self):
        """
        Private slot to display the debugger properties dialog.
        """
        from .DebuggerPropertiesDialog import DebuggerPropertiesDialog

        dlg = DebuggerPropertiesDialog(
            self,
            isRemote=FileSystemUtilities.isRemoteFileName(self.ppath),
            parent=self.ui,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.storeData()

    def getDebugProperty(self, key):
        """
        Public method to retrieve a debugger property.

        @param key key of the property
        @type str
        @return value of the property
        @rtype Any
        """
        if key == "INTERPRETER" and not FileSystemUtilities.isRemoteFileName(
            self.ppath
        ):
            return (
                ericApp()
                .getObject("VirtualEnvManager")
                .getVirtualenvInterpreter(self.debugProperties["VIRTUALENV"])
            )
        else:
            return self.debugProperties[key]

    def setDbgInfo(
        self,
        venvName,
        argv,
        wd,
        env,
        excList,
        excIgnoreList,
        autoClearShell,
        tracePython=None,
        autoContinue=None,
        reportAllExceptions=None,
        enableMultiprocess=None,
        multiprocessNoDebug=None,
        configOverride=None,
    ):
        """
        Public method to set the debugging information.

        @param venvName name of the virtual environment used
        @type str
        @param argv command line arguments to be used
        @type str
        @param wd working directory
        @type str
        @param env environment setting
        @type str
        @param excList list of exceptions to be highlighted
        @type list of str
        @param excIgnoreList list of exceptions to be ignored
        @type list of str
        @param autoClearShell flag indicating, that the interpreter window
            should be cleared
        @type bool
        @param tracePython flag to indicate if the Python library should be
            traced as well
        @type bool
        @param autoContinue flag indicating, that the debugger should not
            stop at the first executable line
        @type bool
        @param reportAllExceptions flag indicating to report all exceptions
            instead of unhandled exceptions only
        @type bool
        @param enableMultiprocess flag indicating, that the debugger should
            run in multi process mode
        @type bool
        @param multiprocessNoDebug list of programs not to be debugged in
            multi process mode
        @type str
        @param configOverride dictionary containing the global config override
            data
        @type dict
        """
        self.dbgVirtualEnv = venvName
        self.dbgCmdline = argv
        self.dbgWd = wd
        self.dbgEnv = env
        self.dbgExcList = excList[:]  # keep a copy of the list
        self.dbgExcIgnoreList = excIgnoreList[:]  # keep a copy of the list
        self.dbgAutoClearShell = autoClearShell
        if tracePython is not None:
            self.dbgTracePython = tracePython
        if autoContinue is not None:
            self.dbgAutoContinue = autoContinue
        if reportAllExceptions is not None:
            self.dbgReportAllExceptions = reportAllExceptions
        if enableMultiprocess is not None:
            self.dbgEnableMultiprocess = enableMultiprocess
        if multiprocessNoDebug is not None:
            self.dbgMultiprocessNoDebug = multiprocessNoDebug
        if configOverride is not None:
            self.dbgGlobalConfigOverride = copy.deepcopy(configOverride)

    def getTranslationPattern(self):
        """
        Public method to get the translation pattern.

        @return translation pattern
        @rtype str
        """
        return self.__pdata["TRANSLATIONPATTERN"]

    def setTranslationPattern(self, pattern):
        """
        Public method to set the translation pattern.

        @param pattern translation pattern
        @type str
        """
        self.__pdata["TRANSLATIONPATTERN"] = pattern

    def addLanguage(self):
        """
        Public slot used to add a language to the project.
        """
        from .AddLanguageDialog import AddLanguageDialog

        if not self.__pdata["TRANSLATIONPATTERN"]:
            EricMessageBox.critical(
                self.ui,
                self.tr("Add Language"),
                self.tr("You have to specify a translation pattern first."),
            )
            return

        dlg = AddLanguageDialog(parent=self.parent())
        if dlg.exec() == QDialog.DialogCode.Accepted:
            lang = dlg.getSelectedLanguage()
            if self.__pdata["PROJECTTYPE"] in [
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
                langFile = self.__pdata["TRANSLATIONPATTERN"].replace(
                    "%language%", lang
                )
                self.appendFile(langFile)
            self.projectLanguageAddedByCode.emit(lang)

    def __binaryTranslationFile(self, langFile):
        """
        Private method to calculate the filename of the binary translations
        file given the name of the raw translations file.

        @param langFile name of the raw translations file
        @type str
        @return name of the binary translations file
        @rtype str
        """
        qmFile = ""
        try:
            if (
                self.__binaryTranslationsCallbacks[self.__pdata["PROJECTTYPE"]]
                is not None
            ):
                qmFile = self.__binaryTranslationsCallbacks[
                    self.__pdata["PROJECTTYPE"]
                ](langFile)
        except KeyError:
            qmFile = langFile.replace(".ts", ".qm")
        if qmFile == langFile:
            qmFile = ""
        return qmFile

    def checkLanguageFiles(self):
        """
        Public slot to check the language files after a release process.
        """
        tbPath = self.__pdata["TRANSLATIONSBINPATH"]
        for langFile in self.__pdata["TRANSLATIONS"][:]:
            qmFile = self.__binaryTranslationFile(langFile)
            if qmFile:
                if FileSystemUtilities.isRemoteFileName(self.ppath):
                    if qmFile not in self.__pdata[
                        "TRANSLATIONS"
                    ] and self.__remotefsInterface.exists(
                        self.__remotefsInterface.join(self.ppath, qmFile)
                    ):
                        self.appendFile(qmFile)
                    if tbPath:
                        qmFile = self.__remotefsInterface.join(
                            tbPath, self.__remotefsInterface.basename(qmFile)
                        )
                        if qmFile not in self.__pdata[
                            "TRANSLATIONS"
                        ] and self.__remotefsInterface.exists(
                            self.__remotefsInterface.join(self.ppath, qmFile)
                        ):
                            self.appendFile(qmFile)
                else:
                    if qmFile not in self.__pdata["TRANSLATIONS"] and os.path.exists(
                        os.path.join(self.ppath, qmFile)
                    ):
                        self.appendFile(qmFile)
                    if tbPath:
                        qmFile = os.path.join(tbPath, os.path.basename(qmFile))
                        if qmFile not in self.__pdata[
                            "TRANSLATIONS"
                        ] and os.path.exists(os.path.join(self.ppath, qmFile)):
                            self.appendFile(qmFile)

    def removeLanguageFile(self, langFile):
        """
        Public slot to remove a translation from the project.

        The translation file is not deleted from the project directory.

        @param langFile the translation file to be removed
        @type str
        """
        langFile = self.getRelativePath(langFile)
        qmFile = self.__binaryTranslationFile(langFile)
        with contextlib.suppress(ValueError):
            self.__model.removeItem(langFile)
            self.__pdata["TRANSLATIONS"].remove(langFile)
        if qmFile:
            with contextlib.suppress(ValueError):
                if self.__pdata["TRANSLATIONSBINPATH"]:
                    if FileSystemUtilities.isRemoteFileName(self.ppath):
                        qmFile = self.__remotefsInterface.join(
                            self.__pdata["TRANSLATIONSBINPATH"],
                            self.__remotefsInterface.basename(qmFile),
                        )
                    else:
                        qmFile = self.getRelativePath(
                            os.path.join(
                                self.__pdata["TRANSLATIONSBINPATH"],
                                os.path.basename(qmFile),
                            )
                        )
                self.__model.removeItem(qmFile)
                self.__pdata["TRANSLATIONS"].remove(qmFile)
        self.setDirty(True)

    def deleteLanguageFile(self, langFile):
        """
        Public slot to delete a translation from the project directory.

        @param langFile the translation file to be removed
        @type str
        """
        langFile = self.getRelativePath(langFile)
        qmFile = self.__binaryTranslationFile(langFile)

        try:
            if FileSystemUtilities.isRemoteFileName(self.ppath):
                fn = self.__remotefsInterface.join(self.ppath, langFile)
                if self.__remotefsInterface.exists(fn):
                    self.__remotefsInterface.remove(fn)
            else:
                fn = os.path.join(self.ppath, langFile)
                if os.path.exists(fn):
                    os.remove(fn)
        except OSError as err:
            EricMessageBox.critical(
                self.ui,
                self.tr("Delete Translation"),
                self.tr(
                    "<p>The selected translation file <b>{0}</b> could not be"
                    " deleted.</p><p>Reason: {1}</p>"
                ).format(langFile, str(err)),
            )
            return

        self.removeLanguageFile(langFile)

        # now get rid of the .qm file
        if qmFile:
            try:
                if self.__pdata["TRANSLATIONSBINPATH"]:
                    qmFile = self.getRelativePath(
                        os.path.join(
                            self.__pdata["TRANSLATIONSBINPATH"],
                            os.path.basename(qmFile),
                        )
                    )
                fn = os.path.join(self.ppath, qmFile)
                if os.path.exists(fn):
                    os.remove(fn)
            except OSError as err:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Delete translation"),
                    self.tr(
                        "<p>The selected translation file <b>{0}</b> could"
                        " not be deleted.</p><p>Reason: {1}</p>"
                    ).format(qmFile, str(err)),
                )
                return

    def appendFile(self, fn, isSourceFile=False, updateModel=True):
        """
        Public method to append a file to the project.

        @param fn filename to be added to the project
        @type str
        @param isSourceFile flag indicating that this is a source file
            even if it doesn't have the source extension
        @type bool
        @param updateModel flag indicating an update of the model is
            requested
        @type bool
        """
        dirty = False

        # make it relative to the project root, if it starts with that path
        # assume relative paths are relative to the project root
        if FileSystemUtilities.isRemoteFileName(self.ppath):
            newfn = self.getRelativePath(fn) if fn.startswith(self.ppath) else fn
            newdir = self.__remotefsInterface.dirname(newfn)
        else:
            newfn = self.getRelativePath(fn) if os.path.isabs(fn) else fn
            newdir = os.path.dirname(newfn)

        if isSourceFile:
            filetype = "SOURCES"
        else:
            filetype = "OTHERS"
            bfn = (
                self.__remotefsInterface.basename(newfn)
                if FileSystemUtilities.isRemoteFileName(self.ppath)
                else os.path.basename(newfn)
            )
            if fnmatch.fnmatch(bfn, "*.ts") or fnmatch.fnmatch(bfn, "*.qm"):
                filetype = "TRANSLATIONS"
            else:
                for pattern in sorted(self.__pdata["FILETYPES"], reverse=True):
                    if fnmatch.fnmatch(bfn, pattern):
                        filetype = self.__pdata["FILETYPES"][pattern]
                        break

        if filetype == "__IGNORE__":
            return

        if filetype in (
            category
            for category in self.getFileCategories()
            if category not in ("TRANSLATIONS", "OTHERS")
        ):
            if newfn not in self.__pdata[filetype]:
                self.__pdata[filetype].append(newfn)
                self.projectFileAdded.emit(newfn, filetype)
                updateModel and self.__model.addNewItem(filetype, newfn)
                dirty = True
            else:
                updateModel and self.repopulateItem(newfn)
            if newdir not in self.subdirs:
                self.subdirs.append(newdir)
        elif filetype == "TRANSLATIONS":
            if newfn not in self.__pdata["TRANSLATIONS"]:
                self.__pdata["TRANSLATIONS"].append(newfn)
                updateModel and self.__model.addNewItem("TRANSLATIONS", newfn)
                self.projectFileAdded.emit(newfn, "TRANSLATIONS")
                dirty = True
            else:
                updateModel and self.repopulateItem(newfn)
        elif filetype == "OTHERS":
            if newfn not in self.__pdata["OTHERS"]:
                self.__pdata["OTHERS"].append(newfn)
                self.othersAdded(newfn, updateModel)
                dirty = True
            else:
                updateModel and self.repopulateItem(newfn)

        if dirty:
            self.setDirty(True)

    @pyqtSlot()
    def addFiles(self, fileTypeFilter=None, startdir=None):
        """
        Public slot used to add files to the project.

        @param fileTypeFilter filter to be used by the add file dialog
        @type str
        @param startdir start directory for the selection dialog
        @type str
        """
        from .AddFileDialog import AddFileDialog

        if not startdir:
            startdir = self.ppath

        dlg = AddFileDialog(
            self, parent=self.parent(), fileTypeFilter=fileTypeFilter, startdir=startdir
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            fnames, target, isSource = dlg.getData()
            if target != "":
                isRemote = FileSystemUtilities.isRemoteFileName(target)
                for fn in fnames:
                    targetfile = (
                        self.__remotefsInterface.join(
                            target, self.__remotefsInterface.basename(fn)
                        )
                        if isRemote
                        else os.path.join(target, os.path.basename(fn))
                    )
                    if not FileSystemUtilities.samepath(
                        (
                            self.__remotefsInterface.dirname(fn)
                            if isRemote
                            else os.path.dirname(fn)
                        ),
                        target,
                    ):
                        try:
                            if isRemote:
                                if not self.__remotefsInterface.isdir(target):
                                    self.__remotefsInterface.makedirs(target)
                            else:
                                if not os.path.isdir(target):
                                    os.makedirs(target)

                            if (not isRemote and os.path.exists(targetfile)) or (
                                isRemote and self.__remotefsInterface.exists(targetfile)
                            ):
                                res = EricMessageBox.yesNo(
                                    self.ui,
                                    self.tr("Add File"),
                                    self.tr(
                                        "<p>The file <b>{0}</b> already"
                                        " exists.</p><p>Overwrite it?</p>"
                                    ).format(targetfile),
                                    icon=EricMessageBox.Warning,
                                )
                                if not res:
                                    return  # don't overwrite

                            if isRemote:
                                self.__remotefsInterface.shutilCopy(fn, target)
                            else:
                                shutil.copy(fn, target)
                        except OSError as why:
                            EricMessageBox.critical(
                                self.ui,
                                self.tr("Add File"),
                                self.tr(
                                    "<p>The selected file <b>{0}</b> could"
                                    " not be added to <b>{1}</b>.</p>"
                                    "<p>Reason: {2}</p>"
                                ).format(fn, target, str(why)),
                            )
                            continue

                    self.appendFile(targetfile, isSource or fileTypeFilter == "source")
            else:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Add file"),
                    self.tr("The target directory must not be empty."),
                )

    def __addSingleDirectory(self, filetype, source, target, quiet=False):
        """
        Private method used to add all files of a single directory to the
        project.

        @param filetype type of files to add
        @type str
        @param source source directory
        @type str
        @param target target directory
        @type str
        @param quiet flag indicating quiet operations
        @type bool
        """
        # get all relevant filename patterns
        patterns = []
        ignorePatterns = []
        for pattern, patterntype in self.__pdata["FILETYPES"].items():
            if patterntype == filetype:
                patterns.append(pattern)
            elif patterntype == "__IGNORE__":
                ignorePatterns.append(pattern)

        files = []
        isRemote = FileSystemUtilities.isRemoteFileName(target)
        for pattern in patterns:
            if isRemote:
                sstring = self.__remotefsInterface.join(source, pattern)
                files.extend(self.__remotefsInterface.glob(sstring))
            else:
                sstring = os.path.join(source, pattern)
                files.extend(glob.glob(sstring))

        if len(files) == 0:
            if not quiet:
                EricMessageBox.information(
                    self.ui,
                    self.tr("Add Directory"),
                    self.tr(
                        "<p>The source directory doesn't contain"
                        " any files belonging to the selected category.</p>"
                    ),
                )
            return

        if not FileSystemUtilities.samepath(target, source) and not (
            (not isRemote and os.path.isdir(target))
            or (isRemote and self.__remotefsInterface.isdir(target))
        ):
            try:
                if isRemote:
                    self.__remotefsInterface.makedirs(target)
                else:
                    os.makedirs(target)
            except OSError as why:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Add Directory"),
                    self.tr(
                        "<p>The target directory <b>{0}</b> could not be"
                        " created.</p><p>Reason: {1}</p>"
                    ).format(target, str(why)),
                )
                return

        for file in files:
            for pattern in ignorePatterns:
                if fnmatch.fnmatch(file, pattern):
                    continue

            targetfile = (
                self.__remotefsInterface.join(
                    target, self.__remotefsInterface.basename(file)
                )
                if isRemote
                else os.path.join(target, os.path.basename(file))
            )
            if not FileSystemUtilities.samepath(target, source):
                try:
                    if (not isRemote and os.path.exists(targetfile)) or (
                        isRemote and self.__remotefsInterface.exists(targetfile)
                    ):
                        res = EricMessageBox.yesNo(
                            self.ui,
                            self.tr("Add Directory"),
                            self.tr(
                                "<p>The file <b>{0}</b> already exists.</p>"
                                "<p>Overwrite it?</p>"
                            ).format(targetfile),
                            icon=EricMessageBox.Warning,
                        )
                        if not res:
                            continue
                            # don't overwrite, carry on with next file

                    if isRemote:
                        self.__remotefsInterface.shutilCopy(file, target)
                    else:
                        shutil.copy(file, target)
                except OSError:
                    continue
            self.appendFile(targetfile)

    def __addRecursiveDirectory(self, filetype, source, target):
        """
        Private method used to add all files of a directory tree.

        The tree is rooted at source to another one rooted at target. This
        method decents down to the lowest subdirectory.

        @param filetype type of files to add
        @type str
        @param source source directory
        @type str
        @param target target directory
        @type str
        """
        # first perform the addition of source
        self.__addSingleDirectory(filetype, source, target, True)

        ignore_patterns = [
            ".svn",
            ".hg",
            ".git",
            ".ropeproject",
            ".eric7project",
            ".jedi",
            "__pycache__",
        ] + [
            pattern
            for pattern, filetype in self.__pdata["FILETYPES"].items()
            if filetype == "__IGNORE__"
        ]

        # now recurs into subdirectories
        if FileSystemUtilities.isRemoteFileName(target):
            for entry in self.__remotefsInterface.listdir(source)[2]:
                if entry["is_dir"] and not any(
                    fnmatch.fnmatch(entry["name"], ignore_pattern)
                    for ignore_pattern in ignore_patterns
                ):
                    self.__addRecursiveDirectory(
                        filetype,
                        entry["path"],
                        self.__remotefsInterface.join(target, entry["name"]),
                    )
        else:
            with os.scandir(source) as dirEntriesIterator:
                for dirEntry in dirEntriesIterator:
                    if dirEntry.is_dir() and not any(
                        fnmatch.fnmatch(dirEntry.name, ignore_pattern)
                        for ignore_pattern in ignore_patterns
                    ):
                        self.__addRecursiveDirectory(
                            filetype, dirEntry.path, os.path.join(target, dirEntry.name)
                        )

    @pyqtSlot()
    def addDirectory(self, fileTypeFilter=None, startdir=None):
        """
        Public method used to add all files of a directory to the project.

        @param fileTypeFilter filter to be used by the add directory dialog
        @type str
        @param startdir start directory for the selection dialog
        @type str
        """
        from .AddDirectoryDialog import AddDirectoryDialog

        if not startdir:
            startdir = self.ppath

        dlg = AddDirectoryDialog(
            self, fileTypeFilter, parent=self.parent(), startdir=startdir
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            filetype, source, target, recursive = dlg.getData()
            if target == "":
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Add directory"),
                    self.tr("The target directory must not be empty."),
                )
                return

            if filetype == "OTHERS":
                self.addToOthers(source)
                return

            if source == "":
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Add directory"),
                    self.tr("The source directory must not be empty."),
                )
                return

            if recursive:
                self.__addRecursiveDirectory(filetype, source, target)
            else:
                self.__addSingleDirectory(filetype, source, target)

    def addToOthers(self, fn):
        """
        Public method to add a file/directory to the OTHERS project data.

        @param fn file name or directory name to add
        @type str
        """
        if fn:
            separator = (
                self.__remotefsInterface.separator()
                if FileSystemUtilities.isRemoteFileName(fn)
                else os.sep
            )

            # if it is below the project directory, make it relative to that
            fn = self.getRelativePath(fn)

            # if it ends with the directory separator character, remove it
            if fn.endswith(separator):
                fn = fn[:-1]

            if fn not in self.__pdata["OTHERS"]:
                self.__pdata["OTHERS"].append(fn)
                self.othersAdded(fn)
                self.setDirty(True)

    def renameMainScript(self, oldfn, newfn):
        """
        Public method to rename the main script.

        @param oldfn old filename
        @type str
        @param newfn new filename of the main script
        @type str
        """
        if self.__pdata["MAINSCRIPT"]:
            ofn = self.getRelativePath(oldfn)
            if ofn != self.__pdata["MAINSCRIPT"]:
                return

            fn = self.getRelativePath(newfn)
            self.__pdata["MAINSCRIPT"] = fn
            self.setDirty(True)

    def renameFile(self, oldfn, newfn=None):
        """
        Public slot to rename a file of the project.

        @param oldfn old filename of the file
        @type str
        @param newfn new filename of the file
        @type str
        @return flag indicating success
        @rtype bool
        """
        isRemote = FileSystemUtilities.isRemoteFileName(oldfn)

        fn = self.getRelativePath(oldfn)
        isSourceFile = fn in self.__pdata["SOURCES"]

        if newfn is None:
            if isRemote:
                newfn = EricServerFileDialog.getSaveFileName(
                    None,
                    self.tr("Rename File"),
                    oldfn,
                    "",
                )
            else:
                newfn = EricFileDialog.getSaveFileName(
                    None,
                    self.tr("Rename File"),
                    oldfn,
                    "",
                    options=EricFileDialog.DontConfirmOverwrite,
                )
                if newfn:
                    newfn = FileSystemUtilities.toNativeSeparators(newfn)

            if not newfn:
                return False

        if (not isRemote and os.path.exists(newfn)) or (
            isRemote and self.__remotefsInterface.exists(newfn)
        ):
            res = EricMessageBox.yesNo(
                self.ui,
                self.tr("Rename File"),
                self.tr(
                    """<p>The file <b>{0}</b> already exists."""
                    """ Overwrite it?</p>"""
                ).format(newfn),
                icon=EricMessageBox.Warning,
            )
            if not res:
                return False

        try:
            if isRemote:
                self.__remotefsInterface.replace(oldfn, newfn)
            else:
                os.rename(oldfn, newfn)
        except OSError as msg:
            EricMessageBox.critical(
                self.ui,
                self.tr("Rename File"),
                self.tr(
                    """<p>The file <b>{0}</b> could not be renamed.<br />"""
                    """Reason: {1}</p>"""
                ).format(oldfn, str(msg)),
            )
            return False

        if any(fn in self.__pdata[category] for category in self.getFileCategories()):
            self.renameFileInPdata(oldfn, newfn, isSourceFile)

        return True

    def renameFileInPdata(self, oldname, newname, isSourceFile=False):
        """
        Public method to rename a file in the __pdata structure.

        @param oldname old filename
        @type str
        @param newname new filename
        @type str
        @param isSourceFile flag indicating that this is a source file
                even if it doesn't have the source extension
        @type bool
        """
        if FileSystemUtilities.isRemoteFileName(oldname):
            oldDirName = self.__remotefsInterface.dirname(oldname)
            newDirName = self.__remotefsInterface.dirname(newname)
        else:
            oldDirName = os.path.dirname(oldname)
            newDirName = os.path.dirname(newname)

        fn = self.getRelativePath(oldname)
        if oldDirName == newDirName:
            if self.__isInPdata(oldname):
                self.removeFile(oldname, False)
                self.appendFile(newname, isSourceFile, False)
            self.__model.renameItem(fn, newname)
        else:
            self.removeFile(oldname)
            self.appendFile(newname, isSourceFile)
        self.projectFileRenamed.emit(oldname, newname)

        self.renameMainScript(fn, newname)

    def getFiles(self, start):
        """
        Public method to get all files starting with a common prefix.

        @param start prefix
        @type str
        @return list of files starting with a common prefix
        @rtype list of str
        """
        isRemote = FileSystemUtilities.isRemoteFileName(self.ppath)

        filelist = []
        start = self.getRelativePath(start)
        for fileCategory in [
            c for c in self.getFileCategories() if c != "TRANSLATIONS"
        ]:
            for entry in self.__pdata[fileCategory][:]:
                if entry.startswith(start):
                    filelist.append(
                        self.__remotefsInterface.join(self.ppath, entry)
                        if isRemote
                        else os.path.join(self.ppath, entry)
                    )
        return filelist

    def __reorganizeFiles(self):
        """
        Private method to reorganize files stored in the project.
        """
        reorganized = False
        isRemote = FileSystemUtilities.isRemoteFileName(self.ppath)

        # initialize data store for the reorganization
        newPdata = {}
        for fileCategory in self.getFileCategories():
            newPdata[fileCategory] = []

        # iterate over all files checking for a reassignment
        for fileCategory in self.getFileCategories():
            for fn in self.__pdata[fileCategory][:]:
                filetype = fileCategory
                bfn = (
                    self.__remotefsInterface.basename(fn)
                    if isRemote
                    else os.path.basename(fn)
                )
                for pattern in sorted(self.__pdata["FILETYPES"], reverse=True):
                    if fnmatch.fnmatch(bfn, pattern):
                        filetype = self.__pdata["FILETYPES"][pattern]
                        break

                if filetype != "__IGNORE__":
                    newPdata[filetype].append(fn)
                    if filetype != fileCategory:
                        reorganized = True

        if reorganized:
            # copy the reorganized files back to the project
            for fileCategory in self.getFileCategories():
                self.__pdata[fileCategory] = newPdata[fileCategory][:]

            # repopulate the model
            self.__model.projectClosed()
            self.__model.projectOpened()

    def copyDirectory(self, olddn, newdn):
        """
        Public slot to copy a directory.

        @param olddn original directory name
        @type str
        @param newdn new directory name
        @type str
        """
        isRemote = FileSystemUtilities.isRemoteFileName(self.ppath)

        olddn = self.getRelativePath(olddn)
        newdn = self.getRelativePath(newdn)
        for fileCategory in [
            c for c in self.getFileCategories() if c != "TRANSLATIONS"
        ]:
            for entry in self.__pdata[fileCategory][:]:
                if entry.startswith(olddn):
                    entry = entry.replace(olddn, newdn)
                    self.appendFile(
                        (
                            self.__remotefsInterface.join(self.ppath, entry)
                            if isRemote
                            else os.path.join(self.ppath, entry)
                        ),
                        fileCategory == "SOURCES",
                    )
        self.setDirty(True)

    def moveDirectory(self, olddn, newdn):
        """
        Public slot to move a directory.

        @param olddn old directory name
        @type str
        @param newdn new directory name
        @type str
        """
        olddn = self.getRelativePath(olddn)
        newdn = self.getRelativePath(newdn)
        typeStrings = []
        for fileCategory in [
            c for c in self.getFileCategories() if c != "TRANSLATIONS"
        ]:
            for entry in self.__pdata[fileCategory][:]:
                if entry.startswith(olddn):
                    if fileCategory not in typeStrings:
                        typeStrings.append(fileCategory)
                    self.__pdata[fileCategory].remove(entry)
                    entry = entry.replace(olddn, newdn)
                    self.__pdata[fileCategory].append(entry)
            if fileCategory != "OTHERS" and newdn not in self.subdirs:
                self.subdirs.append(newdn)
        if typeStrings:
            # the directory is controlled by the project
            self.setDirty(True)
            self.__model.removeItem(olddn)
            typeString = typeStrings[0]
            del typeStrings[0]
            self.__model.addNewItem(typeString, newdn, typeStrings)
        else:
            self.__model.renameItem(olddn, self.getAbsolutePath(newdn))
        self.directoryRemoved.emit(olddn)

    def removeFile(self, fn, updateModel=True):
        """
        Public slot to remove a file from the project.

        The file is not deleted from the project directory.

        @param fn filename to be removed from the project
        @type str
        @param updateModel flag indicating an update of the model is requested
        @type bool
        """
        fn = self.getRelativePath(fn)
        for fileCategory in self.getFileCategories():
            if fn in self.__pdata[fileCategory]:
                self.__pdata[fileCategory].remove(fn)
                self.projectFileRemoved.emit(fn, fileCategory)
                self.setDirty(True)
                if updateModel:
                    self.__model.removeItem(fn)
                break

    def removeDirectory(self, dn):
        """
        Public method to remove a directory from the project.

        The directory is not deleted from the project directory.

        @param dn directory name to be removed from the project
        @type str
        """
        separator = (
            self.__remotefsInterface.separator()
            if FileSystemUtilities.isRemoteFileName(self.ppath)
            else os.sep
        )

        dirty = False
        dn = self.getRelativePath(dn)
        for entry in self.__pdata["OTHERS"][:]:
            if entry.startswith(dn):
                self.__pdata["OTHERS"].remove(entry)
                dirty = True
        dn2 = dn if dn.endswith(separator) else dn + separator
        for fileCategory in [c for c in self.getFileCategories() if c != "OTHERS"]:
            for entry in self.__pdata[fileCategory][:]:
                if entry.startswith(dn2):
                    self.__pdata[fileCategory].remove(entry)
                    dirty = True
        self.__model.removeItem(dn)
        if dirty:
            self.setDirty(True)
        self.directoryRemoved.emit(dn)

    def deleteFile(self, fn):
        """
        Public method to delete a file from the project directory.

        @param fn filename to be deleted from the project
        @type str
        @return flag indicating success
        @rtype bool
        """
        try:
            if FileSystemUtilities.isRemoteFileName(self.ppath):
                self.__remotefsInterface.remove(
                    self.__remotefsInterface.join(self.ppath, fn)
                )
                filepath = self.__remotefsInterface.splitext(fn)[0]
                head, tail = self.__remotefsInterface.split(filepath)
                for ext in [".pyc", ".pyo"]:
                    fn2 = self.__remotefsInterface.join(self.ppath, filepath + ext)
                    if self.__remotefsInterface.isfile(fn2):
                        self.__remotefsInterface.remove(fn2)
                    pat = self.__remotefsInterface.join(
                        self.ppath, head, "__pycache__", "{0}.*{1}".format(tail, ext)
                    )
                    for f in self.__remotefsInterface.glob(pat):
                        self.__remotefsInterface.remove(f)
            else:
                os.remove(os.path.join(self.ppath, fn))
                filepath = os.path.splitext(fn)[0]
                head, tail = os.path.split(filepath)
                for ext in [".pyc", ".pyo"]:
                    fn2 = os.path.join(self.ppath, filepath + ext)
                    if os.path.isfile(fn2):
                        os.remove(fn2)
                    pat = os.path.join(
                        self.ppath, head, "__pycache__", "{0}.*{1}".format(tail, ext)
                    )
                    for f in glob.glob(pat):
                        os.remove(f)
        except OSError as err:
            EricMessageBox.critical(
                self.ui,
                self.tr("Delete File"),
                self.tr(
                    "<p>The selected file <b>{0}</b> could not be"
                    " deleted.</p><p>Reason: {1}</p>"
                ).format(fn, str(err)),
            )
            return False

        self.removeFile(fn)
        return True

    def deleteDirectory(self, dn):
        """
        Public method to delete a directory from the project directory.

        @param dn directory name to be removed from the project
        @type str
        @return flag indicating success
        @rtype bool
        """
        dn = self.getAbsolutePath(dn)
        try:
            if FileSystemUtilities.isRemoteFileName(dn):
                self.__remotefsInterface.shutilRmtree(dn, ignore_errors=True)
            else:
                shutil.rmtree(dn, ignore_errors=True)
        except OSError as err:
            EricMessageBox.critical(
                self.ui,
                self.tr("Delete Directory"),
                self.tr(
                    "<p>The selected directory <b>{0}</b> could not be"
                    " deleted.</p><p>Reason: {1}</p>"
                ).format(dn, str(err)),
            )
            return False

        self.removeDirectory(dn)
        return True

    def hasEntry(self, fn):
        """
        Public method to check the project for a file.

        @param fn filename to be checked
        @type str
        @return flag indicating, if the project contains the file
        @rtype bool
        """
        fn = self.getRelativePath(fn)
        return any(
            fn in self.__pdata[category]
            for category in self.getFileCategories()
            if category != "TRANSLATIONS"
        )

    def createNewProject(self):
        """
        Public slot to built a new project.

        This method displays the new project dialog and initializes
        the project object with the data entered.
        """
        #       assume remote project without VCS if connected to server
        from eric7.VCS.CommandOptionsDialog import VcsCommandOptionsDialog

        from .PropertiesDialog import PropertiesDialog

        if not self.checkDirty():
            return

        isRemote = self.__remoteServer.isServerConnected()

        dlg = PropertiesDialog(self, new=True, isRemote=isRemote, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.closeProject()

            # reset the auto save flag
            autoSaveProject = Preferences.getProject("AutoSaveProject")
            Preferences.setProject("AutoSaveProject", False)

            dlg.storeData()
            self.__pdata["VCS"] = "None"
            self.opened = True
            if not self.__pdata["FILETYPES"]:
                self.initFileTypes()
            self.setDirty(True)
            self.reloadAct.setEnabled(True)
            self.closeAct.setEnabled(True)
            self.saveasAct.setEnabled(True)
            self.saveasRemoteAct.setEnabled(
                self.__remoteServer.isServerConnected()
                and FileSystemUtilities.isRemoteFileName(self.pfile)
            )
            self.actGrp2.setEnabled(True)
            self.propsAct.setEnabled(True)
            self.userPropsAct.setEnabled(not isRemote)
            self.filetypesAct.setEnabled(True)
            self.lexersAct.setEnabled(True)
            self.sessActGrp.setEnabled(False)
            self.dbgActGrp.setEnabled(True)
            self.menuDebuggerAct.setEnabled(True)
            self.menuSessionAct.setEnabled(False)
            self.menuCheckAct.setEnabled(True)
            self.menuShowAct.setEnabled(True)
            self.menuDiagramAct.setEnabled(True)
            self.menuApidocAct.setEnabled(
                not FileSystemUtilities.isRemoteFileName(self.ppath)
            )
            self.menuPackagersAct.setEnabled(True)
            self.pluginGrp.setEnabled(
                self.__pdata["PROJECTTYPE"] in ["E7Plugin"]
                and not FileSystemUtilities.isRemoteFileName(self.ppath)
            )
            self.addLanguageAct.setEnabled(bool(self.__pdata["TRANSLATIONPATTERN"]))
            self.makeGrp.setEnabled(
                self.__pdata["MAKEPARAMS"]["MakeEnabled"]
                and not FileSystemUtilities.isRemoteFileName(self.ppath)
            )
            self.menuMakeAct.setEnabled(
                self.__pdata["MAKEPARAMS"]["MakeEnabled"]
                and not FileSystemUtilities.isRemoteFileName(self.ppath)
            )
            self.menuOtherToolsAct.setEnabled(True)
            self.menuFormattingAct.setEnabled(
                not FileSystemUtilities.isRemoteFileName(self.ppath)
            )
            self.menuVcsAct.setEnabled(
                not FileSystemUtilities.isRemoteFileName(self.ppath)
            )

            self.projectAboutToBeCreated.emit()

            hashStr = str(
                QCryptographicHash.hash(
                    QByteArray(self.ppath.encode("utf-8")),
                    QCryptographicHash.Algorithm.Sha1,
                ).toHex(),
                encoding="utf-8",
            )
            self.__pdata["HASH"] = hashStr

            if self.__pdata["PROGLANGUAGE"] == "MicroPython":
                # change the lexer association for *.py files
                self.__pdata["LEXERASSOCS"] = {
                    "*.py": "MicroPython",
                }

            # create the project directory if it doesn't exist already
            ppathExists = (
                self.__remotefsInterface.isdir(self.ppath)
                if isRemote
                else os.path.isdir(self.ppath)
            )
            if not ppathExists:
                try:
                    if isRemote:
                        self.__remotefsInterface.makedirs(self.ppath)
                    else:
                        os.makedirs(self.ppath)
                except OSError:
                    EricMessageBox.critical(
                        self.ui,
                        self.tr("Create project directory"),
                        self.tr(
                            "<p>The project directory <b>{0}</b> could not"
                            " be created.</p>"
                        ).format(self.ppath),
                    )
                    self.vcs = self.initVCS()
                    # set the auto save flag to its supposed value
                    Preferences.setProject("AutoSaveProject", autoSaveProject)
                    return

                # create an empty __init__.py file to make it a Python package
                # (only for Python and Python3)
                if self.__pdata["PROGLANGUAGE"] in ["Python3", "MicroPython"]:
                    if isRemote:
                        fn = self.__remotefsInterface.join(self.ppath, "__init__.py")
                        self.__remotefsInterface.writeFile(fn, b"")
                    else:
                        fn = os.path.join(self.ppath, "__init__.py")
                        with open(fn, "w", encoding="utf-8"):
                            pass
                    self.appendFile(fn, True)

                # create an empty main script file, if a name was given
                if self.__pdata["MAINSCRIPT"]:
                    if isRemote:
                        if not self.__remotefsInterface.isabs(
                            self.__pdata["MAINSCRIPT"]
                        ):
                            ms = self.__remotefsInterface.join(
                                self.ppath, self.__pdata["MAINSCRIPT"]
                            )
                        else:
                            ms = self.__pdata["MAINSCRIPT"]
                        self.__remotefsInterface.makedirs(
                            self.__remotefsInterface.dirname(ms), exist_ok=True
                        )
                        self.__remotefsInterface.writeFile(ms, b"")
                    else:
                        if not os.path.isabs(self.__pdata["MAINSCRIPT"]):
                            ms = os.path.join(self.ppath, self.__pdata["MAINSCRIPT"])
                        else:
                            ms = self.__pdata["MAINSCRIPT"]
                        os.makedirs(os.path.dirname(ms), exist_ok=True)
                        with open(ms, "w"):
                            pass
                    self.appendFile(ms, True)

                if self.__pdata["MAKEPARAMS"]["MakeEnabled"] and not isRemote:
                    mf = self.__pdata["MAKEPARAMS"]["MakeFile"]
                    if mf:
                        if not os.path.isabs(mf):
                            mf = os.path.join(self.ppath, mf)
                    else:
                        mf = os.path.join(self.ppath, Project.DefaultMakefile)
                    os.makedirs(os.path.dirname(mf), exist_ok=True)
                    with open(mf, "w"):
                        pass
                    self.appendFile(mf)

                if isRemote:
                    tpd = self.__remotefsInterface.join(
                        self.ppath, self.translationsRoot
                    )
                    if not self.translationsRoot.endswith(
                        self.__remotefsInterface.separator()
                    ):
                        tpd = self.__remotefsInterface.dirname(tpd)
                    if not self.__remotefsInterface.isdir(tpd):
                        self.__remotefsInterface.makedirs(tpd, exist_ok=True)
                    if self.__pdata["TRANSLATIONSBINPATH"]:
                        tpd = self.__remotefsInterface.join(
                            self.ppath, self.__pdata["TRANSLATIONSBINPATH"]
                        )
                        if not self.__remotefsInterface.isdir(tpd):
                            self.__remotefsInterface.makedirs(tpd, exist_ok=True)
                else:
                    tpd = os.path.join(self.ppath, self.translationsRoot)
                    if not self.translationsRoot.endswith(os.sep):
                        tpd = os.path.dirname(tpd)
                    if not os.path.isdir(tpd):
                        os.makedirs(tpd, exist_ok=True)
                    if self.__pdata["TRANSLATIONSBINPATH"]:
                        tpd = os.path.join(
                            self.ppath, self.__pdata["TRANSLATIONSBINPATH"]
                        )
                        if not os.path.isdir(tpd):
                            os.makedirs(tpd, exist_ok=True)

                # create management directory if not present
                self.createProjectManagementDir()

                self.saveProject()
                addAllToVcs = True
            else:
                try:
                    # create management directory if not present
                    self.createProjectManagementDir()
                except OSError:
                    EricMessageBox.critical(
                        self.ui,
                        self.tr("Create project management directory"),
                        self.tr(
                            "<p>The project directory <b>{0}</b> is not"
                            " writable.</p>"
                        ).format(self.ppath),
                    )
                    # set the auto save flag to its supposed value
                    Preferences.setProject("AutoSaveProject", autoSaveProject)
                    return

                if self.__pdata["MAINSCRIPT"]:
                    if isRemote:
                        if not self.__remotefsInterface.isabs(
                            self.__pdata["MAINSCRIPT"]
                        ):
                            ms = self.__remotefsInterface.join(
                                self.ppath, self.__pdata["MAINSCRIPT"]
                            )
                        else:
                            ms = self.__pdata["MAINSCRIPT"]
                        msExists = self.__remotefsInterface.exists(ms)
                    else:
                        if not os.path.isabs(self.__pdata["MAINSCRIPT"]):
                            ms = os.path.join(self.ppath, self.__pdata["MAINSCRIPT"])
                        else:
                            ms = self.__pdata["MAINSCRIPT"]
                        msExists = os.path.exists(ms)
                    if not msExists:
                        try:
                            if isRemote:
                                self.__remotefsInterface.makedirs(
                                    self.__remotefsInterface.dirname(ms), exist_ok=True
                                )
                                self.__remotefsInterface.writeFile(ms, b"")
                            else:
                                os.makedirs(os.path.dirname(ms), exist_ok=True)
                                with open(ms, "w"):
                                    pass
                        except OSError as err:
                            EricMessageBox.critical(
                                self.ui,
                                self.tr("Create main script"),
                                self.tr(
                                    "<p>The main script <b>{0}</b> could not"
                                    " be created.<br/>Reason: {1}</p>"
                                ).format(ms, str(err)),
                            )
                    self.appendFile(ms, True)
                else:
                    ms = ""

                if self.__pdata["MAKEPARAMS"]["MakeEnabled"] and not isRemote:
                    mf = self.__pdata["MAKEPARAMS"]["MakeFile"]
                    if mf:
                        if not os.path.isabs(mf):
                            mf = os.path.join(self.ppath, mf)
                    else:
                        mf = os.path.join(self.ppath, Project.DefaultMakefile)
                    if not os.path.exists(mf):
                        try:
                            os.makedirs(os.path.dirname(mf), exist_ok=True)
                            with open(mf, "w"):
                                pass
                        except OSError as err:
                            EricMessageBox.critical(
                                self.ui,
                                self.tr("Create Makefile"),
                                self.tr(
                                    "<p>The makefile <b>{0}</b> could not"
                                    " be created.<br/>Reason: {1}</p>"
                                ).format(mf, str(err)),
                            )
                    self.appendFile(mf)

                # add existing files to the project
                res = EricMessageBox.yesNo(
                    self.ui,
                    self.tr("New Project"),
                    self.tr("""Add existing files to the project?"""),
                    yesDefault=True,
                )
                if res:
                    self.newProjectAddFiles(ms, isRemote=isRemote)
                addAllToVcs = res and not isRemote

                # create an empty __init__.py file to make it a Python package
                # if none exists (only for Python and Python3)
                if self.__pdata["PROGLANGUAGE"] in ["Python3", "MicroPython"]:
                    if isRemote:
                        fn = self.__remotefsInterface.join(self.ppath, "__init__.py")
                        if not self.__remotefsInterface.exists(fn):
                            self.__remotefsInterface.writeFile(fn, b"")
                            self.appendFile(fn, True)
                    else:
                        fn = os.path.join(self.ppath, "__init__.py")
                        if not os.path.exists(fn):
                            with open(fn, "w", encoding="utf-8"):
                                pass
                            self.appendFile(fn, True)
                self.saveProject()

                # check, if the existing project directory is already under
                # VCS control
                if not isRemote:
                    pluginManager = ericApp().getObject("PluginManager")
                    for indicator, vcsData in list(
                        pluginManager.getVcsSystemIndicators().items()
                    ):
                        if os.path.exists(os.path.join(self.ppath, indicator)):
                            if len(vcsData) > 1:
                                vcsList = []
                                for _vcsSystemStr, vcsSystemDisplay in vcsData:
                                    vcsList.append(vcsSystemDisplay)
                                res, vcs_ok = QInputDialog.getItem(
                                    None,
                                    self.tr("New Project"),
                                    self.tr("Select Version Control System"),
                                    vcsList,
                                    0,
                                    False,
                                )
                                if vcs_ok:
                                    for vcsSystemStr, vcsSystemDisplay in vcsData:
                                        if res == vcsSystemDisplay:
                                            vcsSystem = vcsSystemStr
                                            break
                                    else:
                                        vcsSystem = "None"
                                else:
                                    vcsSystem = "None"
                            else:
                                vcsSystem = vcsData[0][1]
                            self.__pdata["VCS"] = vcsSystem
                            self.vcs = self.initVCS()
                            self.setDirty(True)
                            if self.vcs is not None:
                                # edit VCS command options
                                if self.vcs.vcsSupportCommandOptions():
                                    vcores = EricMessageBox.yesNo(
                                        self.ui,
                                        self.tr("New Project"),
                                        self.tr(
                                            """Would you like to edit the VCS"""
                                            """ command options?"""
                                        ),
                                    )
                                else:
                                    vcores = False
                                if vcores:
                                    codlg = VcsCommandOptionsDialog(
                                        self.vcs, parent=self.ui
                                    )
                                    if codlg.exec() == QDialog.DialogCode.Accepted:
                                        self.vcs.vcsSetOptions(codlg.getOptions())
                                # add project file to repository
                                if res == 0:
                                    apres = EricMessageBox.yesNo(
                                        self.ui,
                                        self.tr("New Project"),
                                        self.tr(
                                            "Shall the project file be added"
                                            " to the repository?"
                                        ),
                                        yesDefault=True,
                                    )
                                    if apres:
                                        self.saveProject()
                                        self.vcs.vcsAdd(self.pfile)
                            else:
                                self.__pdata["VCS"] = "None"
                            self.saveProject()
                            break

            # put the project under VCS control
            if (
                not isRemote
                and self.vcs is None
                and self.vcsSoftwareAvailable()
                and self.vcsRequested
            ):
                vcsSystemsDict = (
                    ericApp()
                    .getObject("PluginManager")
                    .getPluginDisplayStrings("version_control")
                )
                vcsSystemsDisplay = [self.tr("None")]
                for key in sorted(vcsSystemsDict):
                    vcsSystemsDisplay.append(vcsSystemsDict[key])
                vcsSelected, ok = QInputDialog.getItem(
                    None,
                    self.tr("New Project"),
                    self.tr("Select version control system for the project"),
                    vcsSystemsDisplay,
                    0,
                    False,
                )
                if ok and vcsSelected != self.tr("None"):
                    for vcsSystem, vcsSystemDisplay in vcsSystemsDict.items():
                        if vcsSystemDisplay == vcsSelected:
                            self.__pdata["VCS"] = vcsSystem
                            break
                    else:
                        self.__pdata["VCS"] = "None"
                else:
                    self.__pdata["VCS"] = "None"
                self.vcs = self.initVCS()
                if self.vcs is not None:
                    vcsdlg = self.vcs.vcsOptionsDialog(self, self.name, parent=self.ui)
                    if vcsdlg.exec() == QDialog.DialogCode.Accepted:
                        vcsDataDict = vcsdlg.getData()
                    else:
                        self.__pdata["VCS"] = "None"
                        self.vcs = self.initVCS()
                self.setDirty(True)
                if self.vcs is not None:
                    # edit VCS command options
                    if self.vcs.vcsSupportCommandOptions():
                        vcores = EricMessageBox.yesNo(
                            self.ui,
                            self.tr("New Project"),
                            self.tr(
                                """Would you like to edit the VCS command"""
                                """ options?"""
                            ),
                        )
                    else:
                        vcores = False
                    if vcores:
                        codlg = VcsCommandOptionsDialog(self.vcs, parent=self.ui)
                        if codlg.exec() == QDialog.DialogCode.Accepted:
                            self.vcs.vcsSetOptions(codlg.getOptions())

                    # create the project in the VCS
                    self.vcs.vcsSetDataFromDict(vcsDataDict)
                    self.saveProject()
                    self.vcs.vcsConvertProject(vcsDataDict, self, addAll=addAllToVcs)
                else:
                    self.newProjectHooks.emit()
                    self.newProject.emit()

            else:
                self.newProjectHooks.emit()
                self.newProject.emit()

            # set the auto save flag to its supposed value
            Preferences.setProject("AutoSaveProject", autoSaveProject)

            if self.__pdata[
                "EMBEDDED_VENV"
            ] and not FileSystemUtilities.isRemoteFileName(self.ppath):
                self.__createEmbeddedEnvironment()
            self.menuEnvironmentAct.setEnabled(
                self.__pdata["EMBEDDED_VENV"]
                and not FileSystemUtilities.isRemoteFileName(self.ppath)
            )

            self.projectOpenedHooks.emit()
            self.projectOpened.emit()

            # open the main script
            if self.__pdata["MAINSCRIPT"]:
                if isRemote:
                    if not self.__remotefsInterface.isabs(self.__pdata["MAINSCRIPT"]):
                        ms = self.__remotefsInterface.join(
                            self.ppath, self.__pdata["MAINSCRIPT"]
                        )
                    else:
                        ms = self.__pdata["MAINSCRIPT"]
                else:
                    if not os.path.isabs(self.__pdata["MAINSCRIPT"]):
                        ms = os.path.join(self.ppath, self.__pdata["MAINSCRIPT"])
                    else:
                        ms = self.__pdata["MAINSCRIPT"]
                self.sourceFile.emit(ms)

    def newProjectAddFiles(self, mainscript, isRemote=False):
        """
        Public method to add files to a new project.

        @param mainscript name of the mainscript
        @type str
        @param isRemote flag indicating a remote project (defaults to False)
        @type bool (optional)
        """
        # Show the file type associations for the user to change
        self.__showFiletypeAssociations()

        ignoreList = []
        if self.__pdata["EMBEDDED_VENV"]:
            environmentPath = self.__findEmbeddedEnvironment()
            if environmentPath:
                # there is already an embedded venv; ignore this when adding files
                ignoreList = (
                    [self.__remotefsInterface.split(environmentPath)[-1]]
                    if isRemote
                    else [os.path.split(environmentPath)[-1]]
                )
        with EricOverrideCursor():
            # search the project directory for files with known extensions
            for filespec in self.__pdata["FILETYPES"]:
                files = (
                    self.__remotefsInterface.direntries(
                        self.ppath,
                        filesonly=True,
                        pattern=filespec,
                        ignore=ignoreList,
                    )
                    if isRemote
                    else FileSystemUtilities.direntries(
                        self.ppath,
                        filesonly=True,
                        pattern=filespec,
                        ignore=ignoreList,
                    )
                )
                for file in files:
                    self.appendFile(file)

            # special handling for translation files
            if self.translationsRoot:
                if isRemote:
                    tpd = self.__remotefsInterface.join(
                        self.ppath, self.translationsRoot
                    )
                    if not self.translationsRoot.endswith(os.sep):
                        tpd = self.__remotefsInterface.dirname(tpd)
                else:
                    tpd = os.path.join(self.ppath, self.translationsRoot)
                    if not self.translationsRoot.endswith(os.sep):
                        tpd = os.path.dirname(tpd)
            else:
                tpd = self.ppath
            tslist = []
            if self.__pdata["TRANSLATIONPATTERN"]:
                pattern = (
                    self.__remotefsInterface.basename(
                        self.__pdata["TRANSLATIONPATTERN"]
                    )
                    if isRemote
                    else os.path.basename(self.__pdata["TRANSLATIONPATTERN"])
                )
                if "%language%" in pattern:
                    pattern = pattern.replace("%language%", "*")
                else:
                    tpd = self.__pdata["TRANSLATIONPATTERN"].split("%language%")[0]
            else:
                pattern = "*.ts"
            tslist.extend(
                self.__remotefsInterface.direntries(tpd, True, pattern)
                if isRemote
                else FileSystemUtilities.direntries(tpd, True, pattern)
            )

            pattern = self.__binaryTranslationFile(pattern)
            if pattern:
                tslist.extend(
                    self.__remotefsInterface.direntries(tpd, True, pattern)
                    if isRemote
                    else FileSystemUtilities.direntries(tpd, True, pattern)
                )
            if tslist:
                hasUnderscore = (
                    "_" in self.__remotefsInterface.basename(tslist[0])
                    if isRemote
                    else "_" in os.path.basename(tslist[0])
                )
                if hasUnderscore:
                    # the first entry determines the main script name
                    if isRemote:
                        mainscriptname = (
                            self.__remotefsInterface.splitext(mainscript)[0]
                            or self.__remotefsInterface.basename(tslist[0]).split("_")[
                                0
                            ]
                        )
                        self.__pdata["TRANSLATIONPATTERN"] = (
                            self.__remotefsInterface.join(
                                self.__remotefsInterface.dirname(tslist[0]),
                                "{0}_%language%{1}".format(
                                    self.__remotefsInterface.basename(tslist[0]).split(
                                        "_"
                                    )[0],
                                    self.__remotefsInterface.splitext(tslist[0])[1],
                                ),
                            )
                        )
                    else:
                        mainscriptname = (
                            os.path.splitext(mainscript)[0]
                            or os.path.basename(tslist[0]).split("_")[0]
                        )
                        self.__pdata["TRANSLATIONPATTERN"] = os.path.join(
                            os.path.dirname(tslist[0]),
                            "{0}_%language%{1}".format(
                                os.path.basename(tslist[0]).split("_")[0],
                                os.path.splitext(tslist[0])[1],
                            ),
                        )
                else:
                    mainscriptname = ""
                    pattern, ok = QInputDialog.getText(
                        None,
                        self.tr("Translation Pattern"),
                        self.tr(
                            "Enter the path pattern for translation files "
                            "(use '%language%' in place of the language"
                            " code):"
                        ),
                        QLineEdit.EchoMode.Normal,
                        tslist[0],
                    )
                    if pattern:
                        self.__pdata["TRANSLATIONPATTERN"] = pattern
                if self.__pdata["TRANSLATIONPATTERN"]:
                    self.__pdata["TRANSLATIONPATTERN"] = self.getRelativePath(
                        self.__pdata["TRANSLATIONPATTERN"]
                    )
                    pattern = self.__pdata["TRANSLATIONPATTERN"].replace(
                        "%language%", "*"
                    )
                    for ts in tslist:
                        if fnmatch.fnmatch(ts, pattern):
                            self.__pdata["TRANSLATIONS"].append(ts)
                            self.projectFileAdded.emit(ts, "TRANSLATIONS")
                    if self.__pdata["TRANSLATIONSBINPATH"]:
                        if isRemote:
                            tpd = self.__remotefsInterface.join(
                                self.ppath, self.__pdata["TRANSLATIONSBINPATH"]
                            )
                            pattern = self.__remotefsInterface.basename(
                                self.__pdata["TRANSLATIONPATTERN"]
                            ).replace("%language%", "*")
                        else:
                            tpd = os.path.join(
                                self.ppath, self.__pdata["TRANSLATIONSBINPATH"]
                            )
                            pattern = os.path.basename(
                                self.__pdata["TRANSLATIONPATTERN"]
                            ).replace("%language%", "*")
                        pattern = self.__binaryTranslationFile(pattern)
                        qmlist = FileSystemUtilities.direntries(tpd, True, pattern)
                        for qm in qmlist:
                            self.__pdata["TRANSLATIONS"].append(qm)
                            self.projectFileAdded.emit(qm, "TRANSLATIONS")
                if not self.__pdata["MAINSCRIPT"] and bool(mainscriptname):
                    if self.__pdata["PROGLANGUAGE"] in ["Python3", "MicroPython"]:
                        self.__pdata["MAINSCRIPT"] = "{0}.py".format(mainscriptname)
                    elif self.__pdata["PROGLANGUAGE"] == "Ruby":
                        self.__pdata["MAINSCRIPT"] = "{0}.rb".format(mainscriptname)
            self.setDirty(True)

    def __showProperties(self):
        """
        Private slot to display the properties dialog.
        """
        from .PropertiesDialog import PropertiesDialog

        isRemote = FileSystemUtilities.isRemoteFileName(self.ppath)
        dlg = PropertiesDialog(self, new=False, isRemote=isRemote, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            fileTypesDict = copy.copy(self.__pdata["FILETYPES"])
            dlg.storeData()
            self.setDirty(True)
            if self.__pdata["MAINSCRIPT"]:
                if isRemote:
                    if not self.__remotefsInterface.isabs(self.__pdata["MAINSCRIPT"]):
                        ms = self.__remotefsInterface.join(
                            self.ppath, self.__pdata["MAINSCRIPT"]
                        )
                    else:
                        ms = self.__pdata["MAINSCRIPT"]
                    if self.__remotefsInterface.exists(ms):
                        self.appendFile(ms)
                else:
                    if not os.path.isabs(self.__pdata["MAINSCRIPT"]):
                        ms = os.path.join(self.ppath, self.__pdata["MAINSCRIPT"])
                    else:
                        ms = self.__pdata["MAINSCRIPT"]
                    if os.path.exists(ms):
                        self.appendFile(ms)

            if self.__pdata["MAKEPARAMS"]["MakeEnabled"]:
                mf = self.__pdata["MAKEPARAMS"]["MakeFile"]
                if isRemote:
                    if mf:
                        if not self.__remotefsInterface.isabs(mf):
                            mf = self.__remotefsInterface.join(self.ppath, mf)
                    else:
                        mf = self.__remotefsInterface.join(
                            self.ppath, Project.DefaultMakefile
                        )
                    exists = self.__remotefsInterface.exists(mf)
                else:
                    if mf:
                        if not os.path.isabs(mf):
                            mf = os.path.join(self.ppath, mf)
                    else:
                        mf = os.path.join(self.ppath, Project.DefaultMakefile)
                    exists = os.path.exists(mf)
                if not exists:
                    try:
                        if isRemote:
                            self.__remotefsInterface.writeFile(mf, b"")
                        else:
                            with open(mf, "w"):
                                pass
                    except OSError as err:
                        EricMessageBox.critical(
                            self.ui,
                            self.tr("Create Makefile"),
                            self.tr(
                                "<p>The makefile <b>{0}</b> could not"
                                " be created.<br/>Reason: {1}</p>"
                            ).format(mf, str(err)),
                        )
                self.appendFile(mf)

            if self.translationsRoot:
                if isRemote:
                    tp = self.__remotefsInterface.join(
                        self.ppath, self.translationsRoot
                    )
                    if not self.translationsRoot.endswith(
                        self.__remotefsInterface.separator()
                    ):
                        tp = self.__remotefsInterface.dirname(tp)
                    if not self.__remotefsInterface.isdir(tp):
                        self.__remotefsInterface.makedirs(tp)
                else:
                    tp = os.path.join(self.ppath, self.translationsRoot)
                    if not self.translationsRoot.endswith(os.sep):
                        tp = os.path.dirname(tp)
                    if not os.path.isdir(tp):
                        os.makedirs(tp)
            else:
                tp = self.ppath
            if tp != self.ppath and tp not in self.subdirs:
                self.subdirs.append(tp)

            if self.__pdata["TRANSLATIONSBINPATH"]:
                if isRemote:
                    tp = self.__remotefsInterface.join(
                        self.ppath, self.__pdata["TRANSLATIONSBINPATH"]
                    )
                    if not self.__remotefsInterface.isdir(tp):
                        self.__remotefsInterface.makedirs(tp)
                else:
                    tp = os.path.join(self.ppath, self.__pdata["TRANSLATIONSBINPATH"])
                    if not os.path.isdir(tp):
                        os.makedirs(tp)
                if tp != self.ppath and tp not in self.subdirs:
                    self.subdirs.append(tp)

            self.pluginGrp.setEnabled(self.__pdata["PROJECTTYPE"] in ["E7Plugin"])

            self.__model.projectPropertiesChanged()
            self.projectPropertiesChanged.emit()

            if self.__pdata["FILETYPES"] != fileTypesDict:
                self.__reorganizeFiles()

            if (
                self.__pdata["EMBEDDED_VENV"]
                and not FileSystemUtilities.isRemoteFileName(self.ppath)
                and not self.__findEmbeddedEnvironment()
            ):
                self.__createEmbeddedEnvironment()

    def __showUserProperties(self):
        """
        Private slot to display the user specific properties dialog.
        """
        from .UserPropertiesDialog import UserPropertiesDialog

        vcsSystem = self.__pdata["VCS"] or None
        vcsSystemOverride = self.pudata["VCSOVERRIDE"] or None

        dlg = UserPropertiesDialog(self, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.storeData()

            if (
                (self.__pdata["VCS"] and self.__pdata["VCS"] != vcsSystem)
                or (
                    self.pudata["VCSOVERRIDE"]
                    and self.pudata["VCSOVERRIDE"] != vcsSystemOverride
                )
                or (vcsSystemOverride is not None and not self.pudata["VCSOVERRIDE"])
            ):
                # stop the VCS monitor thread and shutdown VCS
                if self.vcs is not None:
                    self.vcs.stopStatusMonitor()
                    self.vcs.vcsShutdown()
                    self.vcs.deleteLater()
                    self.vcs = None
                    ericApp().getObject("PluginManager").deactivateVcsPlugins()
                # reinit VCS
                self.vcs = self.initVCS()
                # start the VCS monitor thread
                self.__vcsConnectStatusMonitor()
                self.reinitVCS.emit()

            if self.pudata["VCSSTATUSMONITORINTERVAL"]:
                self.setStatusMonitorInterval(self.pudata["VCSSTATUSMONITORINTERVAL"])
            else:
                self.setStatusMonitorInterval(
                    Preferences.getVCS("StatusMonitorInterval")
                )

    def __showFiletypeAssociations(self):
        """
        Private slot to display the filetype association dialog.
        """
        from .FiletypeAssociationDialog import FiletypeAssociationDialog

        dlg = FiletypeAssociationDialog(
            self, self.getProjectData(dataKey="FILETYPES"), parent=self.ui
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            fileTypes = dlg.getData()
            self.setProjectData(fileTypes, dataKey="FILETYPES")
            self.setDirty(True)
            self.__reorganizeFiles()

    def getFiletypeAssociations(self, associationType):
        """
        Public method to get the list of file type associations for
        the given association type.

        @param associationType type of the association (one of the known file categories
            or __IGNORE__)
        @type str
        @return list of file patterns for the given type
        @rtype list of str
        """
        return [
            assoc
            for assoc in self.__pdata["FILETYPES"]
            if self.__pdata["FILETYPES"][assoc] == associationType
        ]

    def __showLexerAssociations(self):
        """
        Private slot to display the lexer association dialog.
        """
        from .LexerAssociationDialog import LexerAssociationDialog

        dlg = LexerAssociationDialog(self, parent=self.ui)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.transferData()
            self.setDirty(True)
            self.lexerAssociationsChanged.emit()

    def getEditorLexerAssoc(self, filename):
        """
        Public method to retrieve a lexer association.

        @param filename filename used to determine the associated lexer
            language
        @type str
        @return the requested lexer language
        @rtype str
        """
        # try user settings first
        for pattern, language in self.__pdata["LEXERASSOCS"].items():
            if fnmatch.fnmatch(filename, pattern):
                return language

        # try project type specific defaults next
        projectType = self.__pdata["PROJECTTYPE"]
        with contextlib.suppress(KeyError):
            if self.__lexerAssociationCallbacks[projectType] is not None:
                return self.__lexerAssociationCallbacks[projectType](filename)

        # return empty string to signal to use the global setting
        return ""

    def getIgnorePatterns(self):
        """
        Public method to get the list of file name patterns for files to be
        ignored.

        @return list of ignore file name patterns
        @rtype list of str
        """
        return self.getFiletypeAssociations("__IGNORE__")

    @pyqtSlot()
    @pyqtSlot(str)
    def openProject(self, fn=None, restoreSession=True, reopen=False):
        """
        Public slot to open a project.

        @param fn optional filename of the project file to be read
        @type str
        @param restoreSession flag indicating to restore the project
            session
        @type bool
        @param reopen flag indicating a reopening of the project
        @type bool
        """
        if not self.checkDirty():
            return

        if fn is None:
            fn = EricFileDialog.getOpenFileName(
                self.parent(),
                self.tr("Open Project"),
                Preferences.getMultiProject("Workspace") or OSUtilities.getHomeDir(),
                self.tr("Project Files (*.epj)"),
            )

        if fn and self.closeProject():
            with EricOverrideCursor():
                ok = self.__readProject(fn)
            if ok:
                self.opened = True
                if not self.__pdata["FILETYPES"]:
                    self.initFileTypes()
                else:
                    self.updateFileTypes()

                try:
                    # create management directory if not present
                    self.createProjectManagementDir()
                except OSError:
                    EricMessageBox.critical(
                        self.ui,
                        self.tr("Create project management directory"),
                        self.tr(
                            "<p>The project directory <b>{0}</b> is not"
                            " writable.</p>"
                        ).format(self.ppath),
                    )
                    return

                # read a user specific project file
                self.__readUserProperties()

                with EricOverrideCursor():
                    oldState = self.isDirty()
                    self.vcs = self.initVCS()
                    if not FileSystemUtilities.isRemoteFileName(self.ppath):
                        if self.vcs is None and self.isDirty() == oldState:
                            # check, if project is version controlled
                            pluginManager = ericApp().getObject("PluginManager")
                            for (
                                indicator,
                                vcsData,
                            ) in pluginManager.getVcsSystemIndicators().items():
                                if os.path.exists(os.path.join(self.ppath, indicator)):
                                    if len(vcsData) > 1:
                                        vcsList = []
                                        for _vcsSystemStr, vcsSystemDisplay in vcsData:
                                            vcsList.append(vcsSystemDisplay)
                                        with EricOverridenCursor():
                                            res, vcs_ok = QInputDialog.getItem(
                                                None,
                                                self.tr("New Project"),
                                                self.tr(
                                                    "Select Version Control System"
                                                ),
                                                vcsList,
                                                0,
                                                False,
                                            )
                                        if vcs_ok:
                                            for (
                                                vcsSystemStr,
                                                vcsSystemDisplay,
                                            ) in vcsData:
                                                if res == vcsSystemDisplay:
                                                    vcsSystem = vcsSystemStr
                                                    break
                                            else:
                                                vcsSystem = "None"
                                        else:
                                            vcsSystem = "None"
                                    else:
                                        vcsSystem = vcsData[0][0]
                                    self.__pdata["VCS"] = vcsSystem
                                    self.vcs = self.initVCS()
                                    self.setDirty(True)
                        if self.vcs is not None and (
                            self.vcs.vcsRegisteredState(self.ppath)
                            != VersionControlState.Controlled
                        ):
                            self.__pdata["VCS"] = "None"
                            self.vcs = self.initVCS()
                    self.reloadAct.setEnabled(True)
                    self.closeAct.setEnabled(True)
                    self.saveasAct.setEnabled(True)
                    self.saveasRemoteAct.setEnabled(
                        self.__remoteServer.isServerConnected()
                        and FileSystemUtilities.isRemoteFileName(self.pfile)
                    )
                    self.actGrp2.setEnabled(True)
                    self.propsAct.setEnabled(True)
                    self.userPropsAct.setEnabled(
                        not FileSystemUtilities.isRemoteFileName(self.pfile)
                    )
                    self.filetypesAct.setEnabled(True)
                    self.lexersAct.setEnabled(True)
                    self.sessActGrp.setEnabled(True)
                    self.dbgActGrp.setEnabled(True)
                    self.menuDebuggerAct.setEnabled(True)
                    self.menuSessionAct.setEnabled(True)
                    self.menuCheckAct.setEnabled(True)
                    self.menuShowAct.setEnabled(True)
                    self.menuDiagramAct.setEnabled(True)
                    self.menuApidocAct.setEnabled(
                        not FileSystemUtilities.isRemoteFileName(self.ppath)
                    )
                    self.menuPackagersAct.setEnabled(
                        not FileSystemUtilities.isRemoteFileName(self.ppath)
                    )
                    self.pluginGrp.setEnabled(
                        self.__pdata["PROJECTTYPE"] in ["E7Plugin"]
                        and not FileSystemUtilities.isRemoteFileName(self.ppath)
                    )
                    self.addLanguageAct.setEnabled(
                        bool(self.__pdata["TRANSLATIONPATTERN"])
                    )
                    self.makeGrp.setEnabled(
                        self.__pdata["MAKEPARAMS"]["MakeEnabled"]
                        and not FileSystemUtilities.isRemoteFileName(self.ppath)
                    )
                    self.menuMakeAct.setEnabled(
                        self.__pdata["MAKEPARAMS"]["MakeEnabled"]
                        and not FileSystemUtilities.isRemoteFileName(self.ppath)
                    )
                    self.menuOtherToolsAct.setEnabled(True)
                    self.menuFormattingAct.setEnabled(
                        not FileSystemUtilities.isRemoteFileName(self.ppath)
                    )
                    self.menuVcsAct.setEnabled(
                        not FileSystemUtilities.isRemoteFileName(self.ppath)
                    )

                    # open a project debugger properties file being quiet
                    # about errors
                    if Preferences.getProject("AutoLoadDbgProperties"):
                        self.__readDebugProperties(True)

                    self.__model.projectOpened()

                if self.__pdata[
                    "EMBEDDED_VENV"
                ] and not FileSystemUtilities.isRemoteFileName(self.ppath):
                    envPath = self.__findEmbeddedEnvironment()
                    if bool(envPath):
                        self.__loadEnvironmentConfiguration()
                        if not bool(
                            self.__venvConfiguration["interpreter"]
                        ) or not os.access(
                            self.__venvConfiguration["interpreter"], os.X_OK
                        ):
                            self.__configureEnvironment(envPath)
                    else:
                        self.__createEmbeddedEnvironment()
                self.menuEnvironmentAct.setEnabled(
                    self.__pdata["EMBEDDED_VENV"]
                    and not FileSystemUtilities.isRemoteFileName(self.ppath)
                )

                self.projectOpenedHooks.emit()
                self.projectOpened.emit()

                if Preferences.getProject("SearchNewFiles"):
                    self.__doSearchNewFiles()

                # read a project tasks file
                self.__readTasks()
                self.ui.taskViewer.setProjectOpen(True)
                # rescan project tasks
                if Preferences.getProject("TasksProjectRescanOnOpen"):
                    ericApp().getObject("TaskViewer").regenerateProjectTasks(quiet=True)

                if restoreSession:
                    # open the main script
                    if self.__pdata["MAINSCRIPT"]:
                        ms = self.getAbsolutePath(self.__pdata["MAINSCRIPT"])
                        self.sourceFile.emit(ms)

                    # open a project session file being quiet about errors
                    if reopen:
                        self.__readSession(quiet=True, indicator="_tmp")
                    elif Preferences.getProject("AutoLoadSession"):
                        self.__readSession(quiet=True)

                # start the VCS monitor thread
                if not FileSystemUtilities.isRemoteFileName(self.ppath):
                    self.__vcsConnectStatusMonitor()
            else:
                self.__initData()  # delete all invalid data read

    def reopenProject(self):
        """
        Public slot to reopen the current project.
        """
        projectFile = self.pfile
        res = self.closeProject(reopen=True)
        if res:
            self.openProject(projectFile, reopen=True)

    def saveProject(self):
        """
        Public slot to save the current project.

        @return flag indicating success
        @rtype bool
        """
        if self.isDirty():
            if len(self.pfile) > 0:
                ok = self.__writeProject()
            else:
                ok = self.saveProjectAs()
        else:
            ok = True
        self.sessActGrp.setEnabled(ok)
        self.menuSessionAct.setEnabled(ok)
        return ok

    def saveProjectAs(self):
        """
        Public slot to save the current project to a different file.

        @return flag indicating success
        @rtype bool
        """
        defaultFilter = self.tr("Project Files (*.epj)")
        defaultPath = (
            self.ppath
            if self.ppath
            else (Preferences.getMultiProject("Workspace") or OSUtilities.getHomeDir())
        )
        fn, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self.parent(),
            self.tr("Save Project"),
            defaultPath,
            self.tr("Project Files (*.epj)"),
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
                    self.ui,
                    self.tr("Save Project"),
                    self.tr(
                        """<p>The file <b>{0}</b> already exists."""
                        """ Overwrite it?</p>"""
                    ).format(fpath),
                    icon=EricMessageBox.Warning,
                )
                if not res:
                    return False

            ok = self.__writeProject(str(fpath))

            if ok:
                # create management directory if not present
                self.createProjectManagementDir()

                # now save the tasks
                self.writeTasks()

            self.sessActGrp.setEnabled(ok)
            self.menuSessionAct.setEnabled(ok)
            self.projectClosedHooks.emit()
            self.projectClosed.emit(False)
            self.projectOpenedHooks.emit()
            self.projectOpened.emit()
            return ok
        else:
            return False

    def checkDirty(self):
        """
        Public method to check dirty status and open a message window.

        @return flag indicating whether this operation was successful
        @rtype bool
        """
        if self.isDirty():
            res = EricMessageBox.okToClearData(
                self.parent(),
                self.tr("Close Project"),
                self.tr("The current project has unsaved changes."),
                self.saveProject,
            )
            if res:
                self.setDirty(False)
            return res

        return True

    def __closeAllWindows(self):
        """
        Private method to close all project related windows.
        """
        self.codemetrics and self.codemetrics.close()
        self.codecoverage and self.codecoverage.close()
        self.profiledata and self.profiledata.close()
        self.applicationDiagram and self.applicationDiagram.close()
        self.loadedDiagram and self.loadedDiagram.close()

    @pyqtSlot()
    def closeProject(self, reopen=False, noSave=False, shutdown=False):
        """
        Public slot to close the current project.

        @param reopen flag indicating a reopening of the project
        @type bool
        @param noSave flag indicating to not perform save actions
        @type bool
        @param shutdown flag indicating the IDE shutdown
        @type bool
        @return flag indicating success
        @rtype bool
        """
        # save the list of recently opened projects
        self.__saveRecent()

        if not self.isOpen():
            return True

        if not self.checkDirty():
            return False

        ericApp().getObject("TaskViewer").stopProjectTaskExtraction()

        # save the user project properties
        if not noSave:
            self.__writeUserProperties()

        # save the project session file being quiet about error
        if reopen:
            self.__writeSession(quiet=True, indicator="_tmp")
        elif Preferences.getProject("AutoSaveSession") and not noSave:
            self.__writeSession(quiet=True)

        # save the project debugger properties file being quiet about error
        if (
            Preferences.getProject("AutoSaveDbgProperties")
            and self.isDebugPropertiesLoaded()
            and not noSave
            and self.debugPropertiesChanged
        ):
            self.__writeDebugProperties(True)

        vm = ericApp().getObject("ViewManager")

        # check dirty status of all project files first
        for fn in vm.getOpenFilenames():
            if self.isProjectFile(fn):
                reset = vm.checkFileDirty(fn)
                if not reset:
                    # abort shutting down
                    return False

        # close all project related editors
        success = True
        for fn in vm.getOpenFilenames():
            if self.isProjectFile(fn):
                success &= vm.closeWindow(fn, ignoreDirty=True)
        if not success:
            return False

        # stop the VCS monitor thread
        if (
            not FileSystemUtilities.isRemoteFileName(self.ppath)
            and self.vcs is not None
        ):
            self.vcs.stopStatusMonitor()

        # now save the tasks
        if not noSave:
            self.writeTasks()
        self.ui.taskViewer.clearProjectTasks()
        self.ui.taskViewer.setProjectOpen(False)

        if FileSystemUtilities.isRemoteFileName(self.ppath):
            self.__remotefsInterface.removeFromFsCache(self.ppath)

        # now shutdown the vcs interface
        if not FileSystemUtilities.isRemoteFileName(self.ppath) and self.vcs:
            self.vcs.vcsShutdown()
            self.vcs.deleteLater()
            self.vcs = None
            ericApp().getObject("PluginManager").deactivateVcsPlugins()

        # now close all project related tool windows
        self.__closeAllWindows()

        self.__initData()
        self.reloadAct.setEnabled(False)
        self.closeAct.setEnabled(False)
        self.saveasRemoteAct.setEnabled(False)
        self.saveasAct.setEnabled(False)
        self.saveAct.setEnabled(False)
        self.actGrp2.setEnabled(False)
        self.propsAct.setEnabled(False)
        self.userPropsAct.setEnabled(False)
        self.filetypesAct.setEnabled(False)
        self.lexersAct.setEnabled(False)
        self.sessActGrp.setEnabled(False)
        self.dbgActGrp.setEnabled(False)
        self.menuDebuggerAct.setEnabled(False)
        self.menuSessionAct.setEnabled(False)
        self.menuCheckAct.setEnabled(False)
        self.menuShowAct.setEnabled(False)
        self.menuDiagramAct.setEnabled(False)
        self.menuApidocAct.setEnabled(False)
        self.menuPackagersAct.setEnabled(False)
        self.pluginGrp.setEnabled(False)
        self.makeGrp.setEnabled(False)
        self.menuMakeAct.setEnabled(False)
        self.menuOtherToolsAct.setEnabled(False)
        self.menuFormattingAct.setEnabled(False)
        self.menuEnvironmentAct.setEnabled(False)

        self.__model.projectClosed()
        self.projectClosedHooks.emit()
        self.projectClosed.emit(shutdown)

        return True

    def saveAllScripts(self, reportSyntaxErrors=False):
        """
        Public method to save all scripts belonging to the project.

        @param reportSyntaxErrors flag indicating special reporting
            for syntax errors
        @type bool
        @return flag indicating success
        @rtype bool
        """
        vm = ericApp().getObject("ViewManager")
        success = True
        filesWithSyntaxErrors = 0
        for fn in vm.getOpenFilenames():
            rfn = self.getRelativePath(fn)
            if rfn in self.__pdata["SOURCES"] or rfn in self.__pdata["OTHERS"]:
                editor = vm.getOpenEditor(fn)
                success &= vm.saveEditorEd(editor)
                if reportSyntaxErrors and editor.hasSyntaxErrors():
                    filesWithSyntaxErrors += 1

        if reportSyntaxErrors and filesWithSyntaxErrors > 0:
            EricMessageBox.critical(
                self.ui,
                self.tr("Syntax Errors Detected"),
                self.tr(
                    """The project contains %n file(s) with syntax errors.""",
                    "",
                    filesWithSyntaxErrors,
                ),
            )
            return False
        else:
            return success

    def checkAllScriptsDirty(self, reportSyntaxErrors=False):
        """
        Public method to check all scripts belonging to the project for
        their dirty status.

        @param reportSyntaxErrors flag indicating special reporting
            for syntax errors
        @type bool
        @return flag indicating success
        @rtype bool
        """
        vm = ericApp().getObject("ViewManager")
        success = True
        filesWithSyntaxErrors = 0
        for fn in vm.getOpenFilenames():
            rfn = self.getRelativePath(fn)
            if rfn in self.__pdata["SOURCES"] or rfn in self.__pdata["OTHERS"]:
                editor = vm.getOpenEditor(fn)
                success &= editor.checkDirty()
                if reportSyntaxErrors and editor.hasSyntaxErrors():
                    filesWithSyntaxErrors += 1

        if reportSyntaxErrors and filesWithSyntaxErrors > 0:
            EricMessageBox.critical(
                self.ui,
                self.tr("Syntax Errors Detected"),
                self.tr(
                    """The project contains %n file(s) with syntax errors.""",
                    "",
                    filesWithSyntaxErrors,
                ),
            )
            return False
        else:
            return success

    def getMainScript(self, normalized=False):
        """
        Public method to return the main script filename.

        The normalized name is the name of the main script prepended with
        the project path.

        @param normalized flag indicating a normalized filename is wanted
        @type bool
        @return filename of the projects main script
        @rtype str
        """
        if self.__pdata["MAINSCRIPT"]:
            if normalized:
                if FileSystemUtilities.isRemoteFileName(self.ppath):
                    return self.__remotefsInterface.join(
                        self.ppath, self.__pdata["MAINSCRIPT"]
                    )
                else:
                    return os.path.join(self.ppath, self.__pdata["MAINSCRIPT"])
            else:
                return self.__pdata["MAINSCRIPT"]
        else:
            return ""

    def getSources(self, normalized=False):
        """
        Public method to return the source script files.

        @param normalized flag indicating a normalized filename is wanted
        @type bool
        @return list of the projects scripts
        @rtype list of str
        """
        return self.getProjectFiles("SOURCES", normalized=normalized)

    def getProjectFiles(self, fileType, normalized=False):
        """
        Public method to get the file entries of the given type.

        @param fileType project file type (one of the known file categories)
        @type str
        @param normalized flag indicating normalized file names are wanted
        @type boolean
        @return list of file names
        @rtype list of str
        @exception ValueError raised when an unsupported file type is given
        """
        if fileType not in self.getFileCategories():
            raise ValueError("Given file type has incorrect value.")

        if normalized:
            if FileSystemUtilities.isRemoteFileName(self.ppath):
                return [
                    self.__remotefsInterface.join(self.ppath, fn)
                    for fn in self.__pdata[fileType]
                ]
            else:
                return [os.path.join(self.ppath, fn) for fn in self.__pdata[fileType]]
        else:
            return self.__pdata[fileType]

    def getProjectType(self):
        """
        Public method to get the type of the project.

        @return UI type of the project
        @rtype str
        """
        return self.__pdata["PROJECTTYPE"]

    def getProjectLanguage(self):
        """
        Public method to get the project's programming language.

        @return programming language
        @rtype str
        """
        return self.__pdata["PROGLANGUAGE"]

    def isMixedLanguageProject(self):
        """
        Public method to check, if this is a mixed language project.

        @return flag indicating a mixed language project
        @rtype bool
        """
        return self.__pdata["MIXEDLANGUAGE"]

    def isPythonProject(self):
        """
        Public method to check, if this project is a Python3 or MicroPython
        project.

        @return flag indicating a Python project
        @rtype bool
        """
        return self.__pdata["PROGLANGUAGE"] in ["Python3", "MicroPython"]

    def isPy3Project(self):
        """
        Public method to check, if this project is a Python3 project.

        @return flag indicating a Python3 project
        @rtype bool
        """
        return self.__pdata["PROGLANGUAGE"] == "Python3"

    def isMicroPythonProject(self):
        """
        Public method to check, if this project is a MicroPython project.

        @return flag indicating a MicroPython project
        @rtype bool
        """
        return self.__pdata["PROGLANGUAGE"] == "MicroPython"

    def isRubyProject(self):
        """
        Public method to check, if this project is a Ruby project.

        @return flag indicating a Ruby project
        @rtype bool
        """
        return self.__pdata["PROGLANGUAGE"] == "Ruby"

    def isJavaScriptProject(self):
        """
        Public method to check, if this project is a JavaScript project.

        @return flag indicating a JavaScript project
        @rtype bool
        """
        return self.__pdata["PROGLANGUAGE"] == "JavaScript"

    def getProjectSpellLanguage(self):
        """
        Public method to get the project's programming language.

        @return programming language
        @rtype str
        """
        return self.__pdata["SPELLLANGUAGE"]

    def getProjectDictionaries(self):
        """
        Public method to get the names of the project specific dictionaries.

        @return tuple containing the absolute path names of the project specific
            word and exclude list
        @rtype tuple of (str, str)
        """
        pwl = ""
        pel = ""

        if not FileSystemUtilities.isRemoteFileName(self.ppath):
            if self.__pdata["SPELLWORDS"]:
                pwl = os.path.join(self.ppath, self.__pdata["SPELLWORDS"])
                if not os.path.isfile(pwl):
                    pwl = ""

            if self.__pdata["SPELLEXCLUDES"]:
                pel = os.path.join(self.ppath, self.__pdata["SPELLEXCLUDES"])
                if not os.path.isfile(pel):
                    pel = ""

        return (pwl, pel)

    def getDefaultSourceExtension(self):
        """
        Public method to get the default extension for the project's
        programming language.

        @return default extension (including the dot)
        @rtype str
        """
        lang = self.__pdata["PROGLANGUAGE"]
        if lang in ("", "Python"):
            lang = "Python3"
        return self.__sourceExtensions(lang)[0]

    def getProjectPath(self):
        """
        Public method to get the project path.

        @return project path
        @rtype str
        """
        return self.ppath

    def startswithProjectPath(self, checkpath):
        """
        Public method to check, if a path starts with the project path.

        @param checkpath path to be checked
        @type str
        @return flag indicating that the path starts with the project path
        @rtype bool
        """
        if FileSystemUtilities.isRemoteFileName(self.ppath):
            return checkpath == self.ppath or checkpath.startswith(
                self.ppath + self.__remotefsInterface.separator()
            )
        else:
            return bool(self.ppath) and (
                checkpath == self.ppath
                or FileSystemUtilities.normcasepath(
                    FileSystemUtilities.toNativeSeparators(checkpath)
                ).startswith(
                    FileSystemUtilities.normcasepath(
                        FileSystemUtilities.toNativeSeparators(self.ppath + "/")
                    )
                )
            )

    def getProjectFile(self):
        """
        Public method to get the path of the project file.

        @return path of the project file
        @rtype str
        """
        return self.pfile

    def getProjectName(self):
        """
        Public method to get the name of the project.

        The project name is determined from the name of the project file.

        @return name of the project
        @rtype str
        """
        if self.pfile:
            return self.name
        else:
            return ""

    def getProjectManagementDir(self):
        """
        Public method to get the path of the management directory.

        @return path of the management directory
        @rtype str
        """
        if FileSystemUtilities.isRemoteFileName(self.ppath):
            return self.__remotefsInterface.join(self.ppath, ".eric7project")
        else:
            return os.path.join(self.ppath, ".eric7project")

    def createProjectManagementDir(self):
        """
        Public method to create the project management directory.

        It does nothing, if it already exists.
        """
        # create management directory if not present
        mgmtDir = self.getProjectManagementDir()
        if FileSystemUtilities.isRemoteFileName(mgmtDir):
            self.__remotefsInterface.makedirs(mgmtDir, exist_ok=True)
        else:
            os.makedirs(mgmtDir, exist_ok=True)

    def getHash(self):
        """
        Public method to get the project hash.

        @return project hash as a hex string
        @rtype str
        """
        return self.__pdata["HASH"]

    def getRelativePath(self, fullpath):
        """
        Public method to convert a file path to a project relative
        file path.

        @param fullpath file or directory name to convert
        @type str
        @return project relative path or unchanged path, if path doesn't
            belong to the project
        @rtype str
        """
        if fullpath is None:
            return ""

        try:
            if FileSystemUtilities.isRemoteFileName(self.ppath):
                if self.__remotefsInterface.separator() == "\\":
                    return str(
                        pathlib.PureWindowsPath(fullpath).relative_to(self.ppath)
                    )
                else:
                    return str(pathlib.PurePosixPath(fullpath).relative_to(self.ppath))
            else:
                return str(pathlib.PurePath(fullpath).relative_to(self.ppath))
        except ValueError:
            return fullpath

    def getRelativeUniversalPath(self, fullpath):
        """
        Public method to convert a file path to a project relative
        file path with universal separators.

        @param fullpath file or directory name to convert
        @type str
        @return project relative path or unchanged path, if path doesn't
            belong to the project
        @rtype str
        """
        if FileSystemUtilities.isRemoteFileName(self.ppath):
            return self.__remotefsInterface.fromNativeSeparators(
                self.getRelativePath(fullpath)
            )
        else:
            return FileSystemUtilities.fromNativeSeparators(
                self.getRelativePath(fullpath)
            )

    def getAbsolutePath(self, fn):
        """
        Public method to convert a project relative file path to an absolute
        file path.

        @param fn file or directory name to convert
        @type str
        @return absolute path
        @rtype str
        """
        if not fn.startswith(self.ppath):
            if FileSystemUtilities.isRemoteFileName(self.ppath):
                fn = self.__remotefsInterface.join(self.ppath, fn)
            else:
                fn = os.path.join(self.ppath, fn)
        return fn

    def getAbsoluteUniversalPath(self, fn):
        """
        Public method to convert a project relative file path with universal
        separators to an absolute file path.

        @param fn file or directory name to convert
        @type str
        @return absolute path
        @rtype str
        """
        if not fn.startswith(self.ppath):
            if FileSystemUtilities.isRemoteFileName(self.ppath):
                fn = self.__remotefsInterface.join(
                    self.ppath, self.__remotefsInterface.fromNativeSeparators(fn)
                )
            else:
                fn = os.path.join(
                    self.ppath, FileSystemUtilities.fromNativeSeparators(fn)
                )
        return fn

    def getEolString(self):
        """
        Public method to get the EOL-string to be used by the project.

        @return eol string
        @rtype str
        """
        if self.__pdata["EOL"] >= 0:
            return self.eols[self.__pdata["EOL"]]
        else:
            eolMode = Preferences.getEditor("EOLMode")
            if eolMode == QsciScintilla.EolMode.EolWindows:
                eol = "\r\n"
            elif eolMode == QsciScintilla.EolMode.EolUnix:
                eol = "\n"
            elif eolMode == QsciScintilla.EolMode.EolMac:
                eol = "\r"
            else:
                eol = os.linesep
            return eol

    def useSystemEol(self):
        """
        Public method to check, if the project uses the system eol setting.

        @return flag indicating the usage of system eol
        @rtype bool
        """
        return self.__pdata["EOL"] == 0

    def getProjectVersion(self):
        """
        Public mehod to get the version number of the project.

        @return version number
        @rtype str
        """
        return self.__pdata["VERSION"]

    def getProjectAuthor(self):
        """
        Public method to get the author of the project.

        @return author name
        @rtype str
        """
        return self.__pdata["AUTHOR"]

    def getProjectAuthorEmail(self):
        """
        Public method to get the email address of the project author.

        @return project author email
        @rtype str
        """
        return self.__pdata["EMAIL"]

    def getProjectDescription(self):
        """
        Public method to get the description of the project.

        @return project description
        @rtype str
        """
        return self.__pdata["DESCRIPTION"]

    def getProjectVenv(self, resolveDebugger=True):
        """
        Public method to get the name of the virtual environment used by the
        project.

        @param resolveDebugger flag indicating to resolve the virtual
            environment name via the debugger settings if none was configured
        @type bool
        @return name of the project's virtual environment
        @rtype str
        """
        venvName = (
            self.__venvConfiguration["name"]
            if (
                self.__pdata["EMBEDDED_VENV"]
                and not FileSystemUtilities.isRemoteFileName(self.ppath)
                and bool(self.__venvConfiguration["name"])
            )
            else self.getDebugProperty("VIRTUALENV")
        )
        if (
            not venvName
            and resolveDebugger
            and self.getProjectLanguage() in ("Python3", "MicroPython", "Cython")
        ):
            venvName = Preferences.getDebugger("Python3VirtualEnv")

        return venvName

    def getProjectVenvPath(self):
        """
        Public method to get the path name of the embedded virtual environment.

        @return path name of the embedded virtual environment
        @rtype str
        """
        if self.__pdata["EMBEDDED_VENV"] and not FileSystemUtilities.isRemoteFileName(
            self.ppath
        ):
            return self.__findEmbeddedEnvironment()
        else:
            return ""

    def getProjectInterpreter(self, resolveGlobal=True):
        """
        Public method to get the path of the interpreter used by the project.

        @param resolveGlobal flag indicating to resolve the interpreter using
            the global interpreter if no project or debugger specific
            environment was configured
        @type bool
        @return path of the project's interpreter
        @rtype str
        """
        interpreter = (
            self.__venvConfiguration["interpreter"]
            if (
                self.__pdata["EMBEDDED_VENV"]
                and not FileSystemUtilities.isRemoteFileName(self.ppath)
            )
            else ""
        )
        if not interpreter:
            venvName = self.getProjectVenv()
            if venvName:
                interpreter = (
                    ericApp()
                    .getObject("VirtualEnvManager")
                    .getVirtualenvInterpreter(venvName)
                )
        if not interpreter and resolveGlobal:
            interpreter = PythonUtilities.getPythonExecutable()

        return interpreter

    def getProjectExecPath(self):
        """
        Public method to get the executable search path prefix of the project.

        @return executable search path prefix
        @rtype str
        """
        if self.__pdata["EMBEDDED_VENV"]:
            execPath = self.__venvConfiguration["exec_path"]
        else:
            execPath = ""
            venvName = self.getProjectVenv()
            if venvName:
                execPath = (
                    ericApp()
                    .getObject("VirtualEnvManager")
                    .getVirtualenvExecPath(venvName)
                )

        return execPath

    def getProjectTestingFramework(self):
        """
        Public method to get the testing framework name of the project.

        @return testing framework name of the project
        @rtype str
        """
        try:
            return self.__pdata["TESTING_FRAMEWORK"]
        except KeyError:
            return ""

    def getProjectLicense(self):
        """
        Public method to get the license type used by the project.

        @return license type of the project
        @rtype str
        """
        try:
            return self.__pdata["LICENSE"]
        except KeyError:
            return ""

    def __isInPdata(self, fn):
        """
        Private method used to check, if the passed in filename is project
        controlled..

        @param fn filename to be checked
        @type str
        @return flag indicating membership
        @rtype bool
        """
        newfn = (
            self.__remotefsInterface.abspath(fn)
            if FileSystemUtilities.isRemoteFileName(self.ppath)
            else os.path.abspath(fn)
        )
        newfn = self.getRelativePath(newfn)
        return any(
            newfn in self.__pdata[category] for category in self.getFileCategories()
        )

    def isProjectFile(self, fn):
        """
        Public method used to check, if the passed in filename belongs to the
        project.

        @param fn filename to be checked
        @type str
        @return flag indicating membership
        @rtype bool
        """
        return any(
            self.__checkProjectFileGroup(fn, category)
            for category in self.getFileCategories()
        )

    def __checkProjectFileGroup(self, fn, group):
        """
        Private method to check, if a file is in a specific file group of the
        project.

        @param fn filename to be checked
        @type str
        @param group group to check
        @type str
        @return flag indicating membership
        @rtype bool
        """
        newfn = (
            self.__remotefsInterface.abspath(fn)
            if FileSystemUtilities.isRemoteFileName(fn)
            else os.path.abspath(fn)
        )
        newfn = self.getRelativePath(newfn)
        if newfn in self.__pdata[group] or (
            group == "OTHERS"
            and any(newfn.startswith(entry) for entry in self.__pdata[group])
        ):
            return True

        if (
            OSUtilities.isWindowsPlatform()
            or self.__remotefsInterface.separator() == "\\"
        ):
            # try the above case-insensitive
            newfn = newfn.lower()
            if any(entry.lower() == newfn for entry in self.__pdata[group]):
                return True

            elif group == "OTHERS" and any(
                newfn.startswith(entry.lower()) for entry in self.__pdata[group]
            ):
                return True

        return False

    def isProjectCategory(self, fn, category):
        """
        Public method to check, if the passed in filename belongs to the given
        category.

        @param fn filename to be checked
        @type str
        @param category file category to check against
        @type str
        @return flag indicating membership
        @rtype bool
        """
        if category in self.getFileCategories():
            return self.__checkProjectFileGroup(fn, category)
        else:
            return False  # unknown category always returns False

    def initActions(self):
        """
        Public slot to initialize the project related actions.
        """
        self.actions = []

        ###################################################################
        ## Project actions
        ###################################################################

        self.actGrp1 = createActionGroup(self)

        act = EricAction(
            self.tr("New project"),
            EricPixmapCache.getIcon("projectNew"),
            self.tr("&New..."),
            0,
            0,
            self.actGrp1,
            "project_new",
        )
        act.setStatusTip(self.tr("Generate a new project"))
        act.setWhatsThis(
            self.tr(
                """<b>New...</b>"""
                """<p>This opens a dialog for entering the info for a"""
                """ new project.</p>"""
            )
        )
        act.triggered.connect(self.createNewProject)
        self.actions.append(act)

        act = EricAction(
            self.tr("Open project"),
            EricPixmapCache.getIcon("projectOpen"),
            self.tr("&Open..."),
            0,
            0,
            self.actGrp1,
            "project_open",
        )
        act.setStatusTip(self.tr("Open an existing project"))
        act.setWhatsThis(
            self.tr("""<b>Open...</b><p>This opens an existing project.</p>""")
        )
        act.triggered.connect(self.openProject)
        self.actions.append(act)

        self.openRemoteAct = EricAction(
            self.tr("Open remote project"),
            EricPixmapCache.getIcon("projectOpen-remote"),
            self.tr("Open (Remote)..."),
            0,
            0,
            self.actGrp1,
            "project_open_remote",
        )
        self.openRemoteAct.setStatusTip(self.tr("Open an existing remote project"))
        self.openRemoteAct.setWhatsThis(
            self.tr(
                "<b>Open (Remote)...</b><p>This opens an existing remote project.</p>"
            )
        )
        self.openRemoteAct.triggered.connect(self.__openRemoteProject)
        self.actions.append(self.openRemoteAct)
        self.openRemoteAct.setEnabled(False)  # server is not connected initially

        self.reloadAct = EricAction(
            self.tr("Reload project"),
            EricPixmapCache.getIcon("projectReload"),
            self.tr("Re&load"),
            0,
            0,
            self.actGrp1,
            "project_reload",
        )
        self.reloadAct.setStatusTip(self.tr("Reload the current project"))
        self.reloadAct.setWhatsThis(
            self.tr("""<b>Reload</b><p>This reloads the current project.</p>""")
        )
        self.reloadAct.triggered.connect(self.reopenProject)
        self.actions.append(self.reloadAct)

        self.closeAct = EricAction(
            self.tr("Close project"),
            EricPixmapCache.getIcon("projectClose"),
            self.tr("&Close"),
            0,
            0,
            self,
            "project_close",
        )
        self.closeAct.setStatusTip(self.tr("Close the current project"))
        self.closeAct.setWhatsThis(
            self.tr("""<b>Close</b><p>This closes the current project.</p>""")
        )
        self.closeAct.triggered.connect(self.closeProject)
        self.actions.append(self.closeAct)

        self.saveAct = EricAction(
            self.tr("Save project"),
            EricPixmapCache.getIcon("projectSave"),
            self.tr("&Save"),
            0,
            0,
            self,
            "project_save",
        )
        self.saveAct.setStatusTip(self.tr("Save the current project"))
        self.saveAct.setWhatsThis(
            self.tr("""<b>Save</b><p>This saves the current project.</p>""")
        )
        self.saveAct.triggered.connect(self.saveProject)
        self.actions.append(self.saveAct)

        self.saveasAct = EricAction(
            self.tr("Save project as"),
            EricPixmapCache.getIcon("projectSaveAs"),
            self.tr("Save &as..."),
            0,
            0,
            self,
            "project_save_as",
        )
        self.saveasAct.setStatusTip(self.tr("Save the current project to a new file"))
        self.saveasAct.setWhatsThis(
            self.tr(
                """<b>Save as</b>"""
                """<p>This saves the current project to a new file.</p>"""
            )
        )
        self.saveasAct.triggered.connect(self.saveProjectAs)
        self.actions.append(self.saveasAct)

        self.saveasRemoteAct = EricAction(
            self.tr("Save project as (Remote)"),
            EricPixmapCache.getIcon("projectSaveAs-remote"),
            self.tr("Save as (Remote)..."),
            0,
            0,
            self,
            "project_save_as_remote",
        )
        self.saveasRemoteAct.setStatusTip(
            self.tr("Save the current project to a new remote file")
        )
        self.saveasRemoteAct.setWhatsThis(
            self.tr(
                """<b>Save as (Remote)</b>"""
                """<p>This saves the current project to a new remote file.</p>"""
            )
        )
        self.saveasRemoteAct.triggered.connect(self.__saveRemoteProjectAs)
        self.actions.append(self.saveasRemoteAct)
        self.saveasRemoteAct.setEnabled(False)  # server is not connected initially

        ###################################################################
        ## Project management actions
        ###################################################################

        self.actGrp2 = createActionGroup(self)

        self.addFilesAct = EricAction(
            self.tr("Add files to project"),
            EricPixmapCache.getIcon("fileMisc"),
            self.tr("Add &files..."),
            0,
            0,
            self.actGrp2,
            "project_add_file",
        )
        self.addFilesAct.setStatusTip(self.tr("Add files to the current project"))
        self.addFilesAct.setWhatsThis(
            self.tr(
                """<b>Add files...</b>"""
                """<p>This opens a dialog for adding files"""
                """ to the current project. The place to add is"""
                """ determined by the file extension.</p>"""
            )
        )
        self.addFilesAct.triggered.connect(self.addFiles)
        self.actions.append(self.addFilesAct)

        self.addDirectoryAct = EricAction(
            self.tr("Add directory to project"),
            EricPixmapCache.getIcon("dirOpen"),
            self.tr("Add directory..."),
            0,
            0,
            self.actGrp2,
            "project_add_directory",
        )
        self.addDirectoryAct.setStatusTip(
            self.tr("Add a directory to the current project")
        )
        self.addDirectoryAct.setWhatsThis(
            self.tr(
                """<b>Add directory...</b>"""
                """<p>This opens a dialog for adding a directory"""
                """ to the current project.</p>"""
            )
        )
        self.addDirectoryAct.triggered.connect(self.addDirectory)
        self.actions.append(self.addDirectoryAct)

        self.addLanguageAct = EricAction(
            self.tr("Add translation to project"),
            EricPixmapCache.getIcon("linguist4"),
            self.tr("Add &translation..."),
            0,
            0,
            self.actGrp2,
            "project_add_translation",
        )
        self.addLanguageAct.setStatusTip(
            self.tr("Add a translation to the current project")
        )
        self.addLanguageAct.setWhatsThis(
            self.tr(
                """<b>Add translation...</b>"""
                """<p>This opens a dialog for add a translation"""
                """ to the current project.</p>"""
            )
        )
        self.addLanguageAct.triggered.connect(self.addLanguage)
        self.actions.append(self.addLanguageAct)

        act = EricAction(
            self.tr("Search new files"),
            self.tr("Searc&h new files..."),
            0,
            0,
            self.actGrp2,
            "project_search_new_files",
        )
        act.setStatusTip(self.tr("Search new files in the project directory."))
        act.setWhatsThis(
            self.tr(
                """<b>Search new files...</b>"""
                """<p>This searches for new files (sources, forms, ...) in the"""
                """ project directory and registered subdirectories.</p>"""
            )
        )
        act.triggered.connect(self.__searchNewFiles)
        self.actions.append(act)

        act = EricAction(
            self.tr("Search Project File"),
            self.tr("Search Project File..."),
            QKeySequence(self.tr("Alt+Ctrl+P", "Project|Search Project File")),
            0,
            self.actGrp2,
            "project_search_project_file",
        )
        act.setStatusTip(self.tr("Search for a file in the project list of files."))
        act.setWhatsThis(
            self.tr(
                """<b>Search Project File</b>"""
                """<p>This searches for a file in the project list of files.</p>"""
            )
        )
        act.triggered.connect(self.__searchProjectFile)
        self.actions.append(act)

        self.propsAct = EricAction(
            self.tr("Project properties"),
            EricPixmapCache.getIcon("projectProps"),
            self.tr("&Properties..."),
            0,
            0,
            self,
            "project_properties",
        )
        self.propsAct.setStatusTip(self.tr("Show the project properties"))
        self.propsAct.setWhatsThis(
            self.tr(
                """<b>Properties...</b>"""
                """<p>This shows a dialog to edit the project properties.</p>"""
            )
        )
        self.propsAct.triggered.connect(self.__showProperties)
        self.actions.append(self.propsAct)

        self.userPropsAct = EricAction(
            self.tr("User project properties"),
            EricPixmapCache.getIcon("projectUserProps"),
            self.tr("&User Properties..."),
            0,
            0,
            self,
            "project_user_properties",
        )
        self.userPropsAct.setStatusTip(
            self.tr("Show the user specific project properties")
        )
        self.userPropsAct.setWhatsThis(
            self.tr(
                """<b>User Properties...</b>"""
                """<p>This shows a dialog to edit the user specific project"""
                """ properties.</p>"""
            )
        )
        self.userPropsAct.triggered.connect(self.__showUserProperties)
        self.actions.append(self.userPropsAct)

        self.filetypesAct = EricAction(
            self.tr("Filetype Associations"),
            self.tr("Filetype Associations..."),
            0,
            0,
            self,
            "project_filetype_associations",
        )
        self.filetypesAct.setStatusTip(
            self.tr("Show the project file type associations")
        )
        self.filetypesAct.setWhatsThis(
            self.tr(
                """<b>Filetype Associations...</b>"""
                """<p>This shows a dialog to edit the file type associations of"""
                """ the project. These associations determine the type"""
                """ (source, form, interface, protocol or others) with a"""
                """ filename pattern. They are used when adding a file to the"""
                """ project and when performing a search for new files.</p>"""
            )
        )
        self.filetypesAct.triggered.connect(self.__showFiletypeAssociations)
        self.actions.append(self.filetypesAct)

        self.lexersAct = EricAction(
            self.tr("Lexer Associations"),
            self.tr("Lexer Associations..."),
            0,
            0,
            self,
            "project_lexer_associations",
        )
        self.lexersAct.setStatusTip(
            self.tr("Show the project lexer associations (overriding defaults)")
        )
        self.lexersAct.setWhatsThis(
            self.tr(
                """<b>Lexer Associations...</b>"""
                """<p>This shows a dialog to edit the lexer associations of"""
                """ the project. These associations override the global lexer"""
                """ associations. Lexers are used to highlight the editor"""
                """ text.</p>"""
            )
        )
        self.lexersAct.triggered.connect(self.__showLexerAssociations)
        self.actions.append(self.lexersAct)

        ###################################################################
        ## Project debug actions
        ###################################################################

        self.dbgActGrp = createActionGroup(self)

        act = EricAction(
            self.tr("Debugger Properties"),
            self.tr("Debugger &Properties..."),
            0,
            0,
            self.dbgActGrp,
            "project_debugger_properties",
        )
        act.setStatusTip(self.tr("Show the debugger properties"))
        act.setWhatsThis(
            self.tr(
                """<b>Debugger Properties...</b>"""
                """<p>This shows a dialog to edit project specific debugger"""
                """ settings.</p>"""
            )
        )
        act.triggered.connect(self.__showDebugProperties)
        self.actions.append(act)

        act = EricAction(
            self.tr("Load"),
            self.tr("&Load"),
            0,
            0,
            self.dbgActGrp,
            "project_debugger_properties_load",
        )
        act.setStatusTip(self.tr("Load the debugger properties"))
        act.setWhatsThis(
            self.tr(
                """<b>Load Debugger Properties</b>"""
                """<p>This loads the project specific debugger settings.</p>"""
            )
        )
        act.triggered.connect(self.__readDebugProperties)
        self.actions.append(act)

        act = EricAction(
            self.tr("Save"),
            self.tr("&Save"),
            0,
            0,
            self.dbgActGrp,
            "project_debugger_properties_save",
        )
        act.setStatusTip(self.tr("Save the debugger properties"))
        act.setWhatsThis(
            self.tr(
                """<b>Save Debugger Properties</b>"""
                """<p>This saves the project specific debugger settings.</p>"""
            )
        )
        act.triggered.connect(self.__writeDebugProperties)
        self.actions.append(act)

        act = EricAction(
            self.tr("Delete"),
            self.tr("&Delete"),
            0,
            0,
            self.dbgActGrp,
            "project_debugger_properties_delete",
        )
        act.setStatusTip(self.tr("Delete the debugger properties"))
        act.setWhatsThis(
            self.tr(
                """<b>Delete Debugger Properties</b>"""
                """<p>This deletes the file containing the project specific"""
                """ debugger settings.</p>"""
            )
        )
        act.triggered.connect(self.__deleteDebugProperties)
        self.actions.append(act)

        act = EricAction(
            self.tr("Reset"),
            self.tr("&Reset"),
            0,
            0,
            self.dbgActGrp,
            "project_debugger_properties_resets",
        )
        act.setStatusTip(self.tr("Reset the debugger properties"))
        act.setWhatsThis(
            self.tr(
                """<b>Reset Debugger Properties</b>"""
                """<p>This resets the project specific debugger settings.</p>"""
            )
        )
        act.triggered.connect(self.__initDebugProperties)
        self.actions.append(act)

        ###################################################################
        ## Project session actions
        ###################################################################

        self.sessActGrp = createActionGroup(self)

        act = EricAction(
            self.tr("Load session"),
            self.tr("Load session"),
            0,
            0,
            self.sessActGrp,
            "project_load_session",
        )
        act.setStatusTip(self.tr("Load the projects session file."))
        act.setWhatsThis(
            self.tr(
                """<b>Load session</b>"""
                """<p>This loads the projects session file. The session consists"""
                """ of the following data.<br>"""
                """- all open source files<br>"""
                """- all breakpoint<br>"""
                """- the commandline arguments<br>"""
                """- the working directory<br>"""
                """- the exception reporting flag</p>"""
            )
        )
        act.triggered.connect(self.__readSession)
        self.actions.append(act)

        act = EricAction(
            self.tr("Save session"),
            self.tr("Save session"),
            0,
            0,
            self.sessActGrp,
            "project_save_session",
        )
        act.setStatusTip(self.tr("Save the projects session file."))
        act.setWhatsThis(
            self.tr(
                """<b>Save session</b>"""
                """<p>This saves the projects session file. The session consists"""
                """ of the following data.<br>"""
                """- all open source files<br>"""
                """- all breakpoint<br>"""
                """- the commandline arguments<br>"""
                """- the working directory<br>"""
                """- the exception reporting flag</p>"""
            )
        )
        act.triggered.connect(self.__writeSession)
        self.actions.append(act)

        act = EricAction(
            self.tr("Delete session"),
            self.tr("Delete session"),
            0,
            0,
            self.sessActGrp,
            "project_delete_session",
        )
        act.setStatusTip(self.tr("Delete the projects session file."))
        act.setWhatsThis(
            self.tr(
                """<b>Delete session</b>"""
                """<p>This deletes the projects session file</p>"""
            )
        )
        act.triggered.connect(self.__deleteSession)
        self.actions.append(act)

        ###################################################################
        ## Project Tools - check actions
        ###################################################################

        self.chkGrp = createActionGroup(self)

        self.codeMetricsAct = EricAction(
            self.tr("Code Metrics"),
            self.tr("&Code Metrics..."),
            0,
            0,
            self.chkGrp,
            "project_code_metrics",
        )
        self.codeMetricsAct.setStatusTip(
            self.tr("Show some code metrics for the project.")
        )
        self.codeMetricsAct.setWhatsThis(
            self.tr(
                """<b>Code Metrics...</b>"""
                """<p>This shows some code metrics for all Python files in"""
                """ the project.</p>"""
            )
        )
        self.codeMetricsAct.triggered.connect(self.__showCodeMetrics)
        self.actions.append(self.codeMetricsAct)

        self.codeCoverageAct = EricAction(
            self.tr("Python Code Coverage"),
            self.tr("Code Co&verage..."),
            0,
            0,
            self.chkGrp,
            "project_code_coverage",
        )
        self.codeCoverageAct.setStatusTip(
            self.tr("Show code coverage information for the project.")
        )
        self.codeCoverageAct.setWhatsThis(
            self.tr(
                """<b>Code Coverage...</b>"""
                """<p>This shows the code coverage information for all Python"""
                """ files in the project.</p>"""
            )
        )
        self.codeCoverageAct.triggered.connect(self.__showCodeCoverage)
        self.actions.append(self.codeCoverageAct)

        self.codeProfileAct = EricAction(
            self.tr("Profile Data"),
            self.tr("&Profile Data..."),
            0,
            0,
            self.chkGrp,
            "project_profile_data",
        )
        self.codeProfileAct.setStatusTip(
            self.tr("Show profiling data for the project.")
        )
        self.codeProfileAct.setWhatsThis(
            self.tr(
                """<b>Profile Data...</b>"""
                """<p>This shows the profiling data for the project.</p>"""
            )
        )
        self.codeProfileAct.triggered.connect(self.__showProfileData)
        self.actions.append(self.codeProfileAct)

        ###################################################################
        ## Project Tools - graphics actions
        ###################################################################

        self.graphicsGrp = createActionGroup(self)

        self.applicationDiagramAct = EricAction(
            self.tr("Application Diagram"),
            self.tr("&Application Diagram..."),
            0,
            0,
            self.graphicsGrp,
            "project_application_diagram",
        )
        self.applicationDiagramAct.setStatusTip(
            self.tr("Show a diagram of the project.")
        )
        self.applicationDiagramAct.setWhatsThis(
            self.tr(
                """<b>Application Diagram...</b>"""
                """<p>This shows a diagram of the project.</p>"""
            )
        )
        self.applicationDiagramAct.triggered.connect(self.handleApplicationDiagram)
        self.actions.append(self.applicationDiagramAct)

        self.loadDiagramAct = EricAction(
            self.tr("Load Diagram"),
            self.tr("&Load Diagram..."),
            0,
            0,
            self.graphicsGrp,
            "project_load_diagram",
        )
        self.loadDiagramAct.setStatusTip(self.tr("Load a diagram from file."))
        self.loadDiagramAct.setWhatsThis(
            self.tr(
                """<b>Load Diagram...</b>"""
                """<p>This loads a diagram from file.</p>"""
            )
        )
        self.loadDiagramAct.triggered.connect(self.__loadDiagram)
        self.actions.append(self.loadDiagramAct)

        ###################################################################
        ## Project Tools - plugin packaging actions
        ###################################################################

        self.pluginGrp = createActionGroup(self)

        self.pluginPkgListAct = EricAction(
            self.tr("Create Package List"),
            EricPixmapCache.getIcon("pluginArchiveList"),
            self.tr("Create &Package List"),
            0,
            0,
            self.pluginGrp,
            "project_plugin_pkglist",
        )
        self.pluginPkgListAct.setStatusTip(
            self.tr("Create an initial PKGLIST file for an eric plugin.")
        )
        self.pluginPkgListAct.setWhatsThis(
            self.tr(
                """<b>Create Package List</b>"""
                """<p>This creates an initial list of files to include in an"""
                """ eric plugin archive. The list is created from the project"""
                """ file.</p>"""
            )
        )
        self.pluginPkgListAct.triggered.connect(self.__pluginCreatePkgList)
        self.actions.append(self.pluginPkgListAct)

        self.pluginArchiveAct = EricAction(
            self.tr("Create Plugin Archives"),
            EricPixmapCache.getIcon("pluginArchive"),
            self.tr("Create Plugin &Archives"),
            0,
            0,
            self.pluginGrp,
            "project_plugin_archive",
        )
        self.pluginArchiveAct.setStatusTip(self.tr("Create eric plugin archive files."))
        self.pluginArchiveAct.setWhatsThis(
            self.tr(
                """<b>Create Plugin Archives</b>"""
                """<p>This creates eric plugin archive files using the list"""
                """ of files given in a PKGLIST* file. The archive name is"""
                """ built from the main script name if not designated in"""
                """ the package list file.</p>"""
            )
        )
        self.pluginArchiveAct.triggered.connect(self.__pluginCreateArchives)
        self.actions.append(self.pluginArchiveAct)

        self.pluginSArchiveAct = EricAction(
            self.tr("Create Plugin Archives (Snapshot)"),
            EricPixmapCache.getIcon("pluginArchiveSnapshot"),
            self.tr("Create Plugin Archives (&Snapshot)"),
            0,
            0,
            self.pluginGrp,
            "project_plugin_sarchive",
        )
        self.pluginSArchiveAct.setStatusTip(
            self.tr("Create eric plugin archive files (snapshot releases).")
        )
        self.pluginSArchiveAct.setWhatsThis(
            self.tr(
                """<b>Create Plugin Archives (Snapshot)</b>"""
                """<p>This creates eric plugin archive files using the list"""
                """ of files given in the PKGLIST* file. The archive name is"""
                """ built from the main script name if not designated in"""
                """ the package list file. The version entry of the main script"""
                """ is modified to reflect a snapshot release.</p>"""
            )
        )
        self.pluginSArchiveAct.triggered.connect(self.__pluginCreateSnapshotArchives)
        self.actions.append(self.pluginSArchiveAct)

        ###################################################################
        ## Project Tools - make actions
        ###################################################################

        self.makeGrp = createActionGroup(self)

        self.makeExecuteAct = EricAction(
            self.tr("Execute Make"),
            self.tr("&Execute Make"),
            0,
            0,
            self.makeGrp,
            "project_make_execute",
        )
        self.makeExecuteAct.setStatusTip(self.tr("Perform a 'make' run."))
        self.makeExecuteAct.setWhatsThis(
            self.tr(
                """<b>Execute Make</b>"""
                """<p>This performs a 'make' run to rebuild the configured"""
                """ target.</p>"""
            )
        )
        self.makeExecuteAct.triggered.connect(self.__executeMake)
        self.actions.append(self.makeExecuteAct)

        self.makeTestAct = EricAction(
            self.tr("Test for Changes"),
            self.tr("&Test for Changes"),
            0,
            0,
            self.makeGrp,
            "project_make_test",
        )
        self.makeTestAct.setStatusTip(
            self.tr("Question 'make', if a rebuild is needed.")
        )
        self.makeTestAct.setWhatsThis(
            self.tr(
                """<b>Test for Changes</b>"""
                """<p>This questions 'make', if a rebuild of the configured"""
                """ target is necessary.</p>"""
            )
        )
        self.makeTestAct.triggered.connect(
            lambda: self.__executeMake(questionOnly=True)
        )
        self.actions.append(self.makeTestAct)

        ###################################################################
        ## Project Tools - other tools actions
        ###################################################################

        self.othersGrp = createActionGroup(self)

        self.createSBOMAct = EricAction(
            self.tr("Create SBOM File"),
            self.tr("Create &SBOM File"),
            0,
            0,
            self.othersGrp,
            "project_create_sbom",
        )
        self.createSBOMAct.setStatusTip(
            self.tr("Create a SBOM file of the project dependencies.")
        )
        self.createSBOMAct.setWhatsThis(
            self.tr(
                """<b>Create SBOM File</b>"""
                """<p>This allows the creation of a SBOM file of the project"""
                """ dependencies. This may be based on various input sources"""
                """ and will be saved as a CycloneDX SBOM file.</p>"""
            )
        )
        self.createSBOMAct.triggered.connect(self.__createSBOMFile)
        self.actions.append(self.createSBOMAct)

        self.clearByteCodeCachesAct = EricAction(
            self.tr("Clear Byte Code Caches"),
            self.tr("Clear Byte Code &Caches"),
            0,
            0,
            self.othersGrp,
            "project_clear_bytecode_caches",
        )
        self.clearByteCodeCachesAct.setStatusTip(
            self.tr("Clear the byte code caches of the project.")
        )
        self.clearByteCodeCachesAct.setWhatsThis(
            self.tr(
                """<b>Clear Byte Code Caches</b>"""
                """<p>This deletes all directories containing byte code cache files."""
                """</p>"""
            )
        )
        self.clearByteCodeCachesAct.triggered.connect(self.__clearByteCodeCaches)
        self.actions.append(self.clearByteCodeCachesAct)

        ###################################################################
        ## Project Tools - code formatting actions - Black
        ###################################################################

        self.blackFormattingGrp = createActionGroup(self)

        self.blackAboutAct = EricAction(
            self.tr("About Black"),
            self.tr("&Black"),
            0,
            0,
            self.blackFormattingGrp,
            "project_black_about",
        )
        self.blackAboutAct.setStatusTip(self.tr("Show some information about 'Black'."))
        self.blackAboutAct.setWhatsThis(
            self.tr(
                "<b>Black</b>"
                "<p>This shows some information about the installed 'Black' tool.</p>"
            )
        )
        self.blackAboutAct.triggered.connect(aboutBlack)
        self.actions.append(self.blackAboutAct)
        font = self.blackAboutAct.font()
        font.setBold(True)
        self.blackAboutAct.setFont(font)

        self.blackFormatAct = EricAction(
            self.tr("Format Code"),
            self.tr("&Format Code"),
            0,
            0,
            self.blackFormattingGrp,
            "project_black_format_code",
        )
        self.blackFormatAct.setStatusTip(
            self.tr("Format the project sources with 'Black'.")
        )
        self.blackFormatAct.setWhatsThis(
            self.tr(
                "<b>Format Code</b>"
                "<p>This shows a dialog to enter parameters for the formatting run and"
                " reformats the project sources using 'Black'.</p>"
            )
        )
        self.blackFormatAct.triggered.connect(
            lambda: self.__performFormatWithBlack(BlackFormattingAction.Format)
        )
        self.actions.append(self.blackFormatAct)

        self.blackCheckFormattingAct = EricAction(
            self.tr("Check Code Formatting"),
            self.tr("&Check Code Formatting"),
            0,
            0,
            self.blackFormattingGrp,
            "project_black_check_code",
        )
        self.blackCheckFormattingAct.setStatusTip(
            self.tr(
                "Check, if the project sources need to be reformatted with 'Black'."
            )
        )
        self.blackCheckFormattingAct.setWhatsThis(
            self.tr(
                "<b>Check Code Formatting</b>"
                "<p>This shows a dialog to enter parameters for the format check run"
                " and performs a check, if the project sources need to be reformatted"
                " using 'Black'.</p>"
            )
        )
        self.blackCheckFormattingAct.triggered.connect(
            lambda: self.__performFormatWithBlack(BlackFormattingAction.Check)
        )
        self.actions.append(self.blackCheckFormattingAct)

        self.blackDiffFormattingAct = EricAction(
            self.tr("Code Formatting Diff"),
            self.tr("Code Formatting &Diff"),
            0,
            0,
            self.blackFormattingGrp,
            "project_black_diff_code",
        )
        self.blackDiffFormattingAct.setStatusTip(
            self.tr(
                "Generate a unified diff of potential project source reformatting"
                " with 'Black'."
            )
        )
        self.blackDiffFormattingAct.setWhatsThis(
            self.tr(
                "<b>Diff Code Formatting</b>"
                "<p>This shows a dialog to enter parameters for the format diff run and"
                " generates a unified diff of potential project source reformatting"
                " using 'Black'.</p>"
            )
        )
        self.blackDiffFormattingAct.triggered.connect(
            lambda: self.__performFormatWithBlack(BlackFormattingAction.Diff)
        )
        self.actions.append(self.blackDiffFormattingAct)

        self.blackConfigureAct = EricAction(
            self.tr("Configure"),
            self.tr("Configure"),
            0,
            0,
            self.blackFormattingGrp,
            "project_black_configure",
        )
        self.blackConfigureAct.setStatusTip(
            self.tr(
                "Enter the parameters for formatting the project sources with 'Black'."
            )
        )
        self.blackConfigureAct.setWhatsThis(
            self.tr(
                "<b>Configure</b>"
                "<p>This shows a dialog to enter the parameters for formatting the"
                " project sources with 'Black'.</p>"
            )
        )
        self.blackConfigureAct.triggered.connect(self.__configureBlack)
        self.actions.append(self.blackConfigureAct)

        ###################################################################
        ## Project Tools - code formatting actions - isort
        ###################################################################

        self.isortFormattingGrp = createActionGroup(self)

        self.isortAboutAct = EricAction(
            self.tr("About isort"),
            self.tr("&isort"),
            0,
            0,
            self.isortFormattingGrp,
            "project_isort_about",
        )
        self.isortAboutAct.setStatusTip(self.tr("Show some information about 'isort'."))
        self.isortAboutAct.setWhatsThis(
            self.tr(
                "<b>isort</b>"
                "<p>This shows some information about the installed 'isort' tool.</p>"
            )
        )
        self.isortAboutAct.triggered.connect(aboutIsort)
        self.actions.append(self.isortAboutAct)
        font = self.isortAboutAct.font()
        font.setBold(True)
        self.isortAboutAct.setFont(font)

        self.isortSortImportsAct = EricAction(
            self.tr("Sort Imports"),
            self.tr("Sort Imports"),
            0,
            0,
            self.isortFormattingGrp,
            "project_isort_sort_imports",
        )
        self.isortSortImportsAct.setStatusTip(
            self.tr("Sort the import statements of the project sources with 'isort'.")
        )
        self.isortSortImportsAct.setWhatsThis(
            self.tr(
                "<b>Sort Imports</b>"
                "<p>This shows a dialog to enter parameters for the imports sorting"
                " run and sorts the import statements of the project sources using"
                " 'isort'.</p>"
            )
        )
        self.isortSortImportsAct.triggered.connect(
            lambda: self.__performImportSortingWithIsort(IsortFormattingAction.Sort)
        )
        self.actions.append(self.isortSortImportsAct)

        self.isortDiffSortingAct = EricAction(
            self.tr("Imports Sorting Diff"),
            self.tr("Imports Sorting Diff"),
            0,
            0,
            self.isortFormattingGrp,
            "project_isort_diff_code",
        )
        self.isortDiffSortingAct.setStatusTip(
            self.tr(
                "Generate a unified diff of potential project source imports"
                " resorting with 'isort'."
            )
        )
        self.isortDiffSortingAct.setWhatsThis(
            self.tr(
                "<b>Imports Sorting Diff</b>"
                "<p>This shows a dialog to enter parameters for the imports sorting"
                " diff run and generates a unified diff of potential project source"
                " changes using 'isort'.</p>"
            )
        )
        self.isortDiffSortingAct.triggered.connect(
            lambda: self.__performImportSortingWithIsort(IsortFormattingAction.Diff)
        )
        self.actions.append(self.isortDiffSortingAct)

        self.isortConfigureAct = EricAction(
            self.tr("Configure"),
            self.tr("Configure"),
            0,
            0,
            self.isortFormattingGrp,
            "project_isort_configure",
        )
        self.isortConfigureAct.setStatusTip(
            self.tr(
                "Enter the parameters for resorting the project sources import"
                " statements with 'isort'."
            )
        )
        self.isortConfigureAct.setWhatsThis(
            self.tr(
                "<b>Configure</b>"
                "<p>This shows a dialog to enter the parameters for resorting the"
                " import statements of the project sources with 'isort'.</p>"
            )
        )
        self.isortConfigureAct.triggered.connect(self.__configureIsort)
        self.actions.append(self.isortConfigureAct)

        ###################################################################
        ## Project - embedded environment actions
        ###################################################################

        self.embeddedEnvironmentGrp = createActionGroup(self)

        self.installVenvAct = EricAction(
            self.tr("Install Project"),
            self.tr("&Install Project"),
            0,
            0,
            self.embeddedEnvironmentGrp,
            "project_venv_install",
        )
        self.installVenvAct.setStatusTip(
            self.tr("Install the project into the embedded environment.")
        )
        self.installVenvAct.setWhatsThis(
            self.tr(
                "<b>Install Project</b>"
                "<p>This installs the project into the embedded virtual environment"
                " in editable mode (i.e. development mode).</p>"
            )
        )
        self.installVenvAct.triggered.connect(self.__installProjectIntoEnvironment)
        self.actions.append(self.installVenvAct)

        self.configureVenvAct = EricAction(
            self.tr("Configure"),
            self.tr("&Configure"),
            0,
            0,
            self.embeddedEnvironmentGrp,
            "project_venv_configure",
        )
        self.configureVenvAct.setStatusTip(
            self.tr("Configure the embedded environment.")
        )
        self.configureVenvAct.setWhatsThis(
            self.tr(
                "<b>Configure</b>"
                "<p>This opens a dialog to configure the embedded virtual environment"
                " of the project.</p>"
            )
        )
        self.configureVenvAct.triggered.connect(self.__configureEnvironment)
        self.actions.append(self.configureVenvAct)

        self.upgradeVenvAct = EricAction(
            self.tr("Upgrade"),
            self.tr("&Upgrade"),
            0,
            0,
            self.embeddedEnvironmentGrp,
            "project_venv_upgrade",
        )
        self.upgradeVenvAct.setStatusTip(self.tr("Upgrade the embedded environment."))
        self.upgradeVenvAct.setWhatsThis(
            self.tr(
                "<b>Upgrade</b>"
                "<p>This opens a dialog to enter the parameters to upgrade the"
                " embedded virtual environment of the project.</p>"
            )
        )
        self.upgradeVenvAct.triggered.connect(
            lambda: self.__createEmbeddedEnvironment(upgrade=True)
        )
        self.actions.append(self.upgradeVenvAct)

        self.recreateVenvAct = EricAction(
            self.tr("Recreate"),
            self.tr("&Recreate"),
            0,
            0,
            self.embeddedEnvironmentGrp,
            "project_venv_recreate",
        )
        self.recreateVenvAct.setStatusTip(self.tr("Recreate the embedded environment."))
        self.recreateVenvAct.setWhatsThis(
            self.tr(
                "<b>Recreate</b>"
                "<p>This opens a dialog to enter the parameters to recreate the"
                " embedded virtual environment of the project. The existing environment"
                " is cleared first.</p>"
            )
        )
        self.recreateVenvAct.triggered.connect(
            lambda: self.__createEmbeddedEnvironment(force=True)
        )
        self.actions.append(self.recreateVenvAct)

        self.reloadAct.setEnabled(False)
        self.closeAct.setEnabled(False)
        self.saveAct.setEnabled(False)
        self.saveasAct.setEnabled(False)
        self.actGrp2.setEnabled(False)
        self.propsAct.setEnabled(False)
        self.userPropsAct.setEnabled(False)
        self.filetypesAct.setEnabled(False)
        self.lexersAct.setEnabled(False)
        self.sessActGrp.setEnabled(False)
        self.dbgActGrp.setEnabled(False)
        self.pluginGrp.setEnabled(False)

    def initMenus(self):
        """
        Public slot to initialize the project menus.

        @return tuple of generated menus
        @rtype tuple of (QMenu, QMenu)
        """
        menu = QMenu(self.tr("&Project"), self.parent())
        self.recentMenu = QMenu(self.tr("Open &Recent Projects"), menu)
        self.recentMenu.setIcon(EricPixmapCache.getIcon("projectOpenRecent"))
        self.sessionMenu = QMenu(self.tr("Session"), menu)
        self.debuggerMenu = QMenu(self.tr("Debugger"), menu)
        self.environmentMenu = QMenu(self.tr("Embedded Environment"), menu)

        toolsMenu = QMenu(self.tr("Project-T&ools"), self.parent())
        self.vcsMenu = QMenu(self.tr("&Version Control"), toolsMenu)
        self.vcsMenu.setTearOffEnabled(True)
        self.vcsProjectHelper.initMenu(self.vcsMenu)
        self.vcsMenu.setEnabled(self.vcsSoftwareAvailable())
        self.checksMenu = QMenu(self.tr("Chec&k"), toolsMenu)
        self.checksMenu.setTearOffEnabled(True)
        self.formattingMenu = QMenu(self.tr("Code &Formatting"), toolsMenu)
        self.formattingMenu.setTearOffEnabled(True)
        self.menuShow = QMenu(self.tr("Sho&w"), toolsMenu)
        self.graphicsMenu = QMenu(self.tr("&Diagrams"), toolsMenu)
        self.packagersMenu = QMenu(self.tr("Pac&kagers"), toolsMenu)
        self.apidocMenu = QMenu(self.tr("Source &Documentation"), toolsMenu)
        self.apidocMenu.setTearOffEnabled(True)
        self.makeMenu = QMenu(self.tr("Make"), toolsMenu)
        self.othersMenu = QMenu(self.tr("Other Tools"), toolsMenu)

        self.__menus = {
            "Main": menu,
            "Recent": self.recentMenu,
            "VCS": self.vcsMenu,
            "Checks": self.checksMenu,
            "Show": self.menuShow,
            "Graphics": self.graphicsMenu,
            "Session": self.sessionMenu,
            "Apidoc": self.apidocMenu,
            "Debugger": self.debuggerMenu,
            "Packagers": self.packagersMenu,
            "Make": self.makeMenu,
            "OtherTools": self.othersMenu,
            "Formatting": self.formattingMenu,
            "Environment": self.environmentMenu,
        }

        # connect the aboutToShow signals
        self.recentMenu.aboutToShow.connect(self.__showContextMenuRecent)
        self.recentMenu.triggered.connect(self.__openRecent)
        self.vcsMenu.aboutToShow.connect(self.__showContextMenuVCS)
        self.checksMenu.aboutToShow.connect(self.__showContextMenuChecks)
        self.menuShow.aboutToShow.connect(self.__showContextMenuShow)
        self.graphicsMenu.aboutToShow.connect(self.__showContextMenuGraphics)
        self.apidocMenu.aboutToShow.connect(self.__showContextMenuApiDoc)
        self.packagersMenu.aboutToShow.connect(self.__showContextMenuPackagers)
        self.sessionMenu.aboutToShow.connect(self.__showContextMenuSession)
        self.debuggerMenu.aboutToShow.connect(self.__showContextMenuDebugger)
        self.makeMenu.aboutToShow.connect(self.__showContextMenuMake)
        self.othersMenu.aboutToShow.connect(self.__showContextMenuOthers)
        self.formattingMenu.aboutToShow.connect(self.__showContextMenuFormat)
        self.environmentMenu.aboutToShow.connect(self.__showContextMenuEnvironment)
        menu.aboutToShow.connect(self.__showMenu)

        # build the show menu
        self.menuShow.setTearOffEnabled(True)
        self.menuShow.addAction(self.codeMetricsAct)
        self.menuShow.addAction(self.codeCoverageAct)
        self.menuShow.addAction(self.codeProfileAct)

        # build the diagrams menu
        self.graphicsMenu.setTearOffEnabled(True)
        self.graphicsMenu.addAction(self.applicationDiagramAct)
        self.graphicsMenu.addSeparator()
        self.graphicsMenu.addAction(self.loadDiagramAct)

        # build the session menu
        self.sessionMenu.setTearOffEnabled(True)
        self.sessionMenu.addActions(self.sessActGrp.actions())

        # build the debugger menu
        self.debuggerMenu.setTearOffEnabled(True)
        self.debuggerMenu.addActions(self.dbgActGrp.actions())

        # build the environment menu
        self.environmentMenu.setTearOffEnabled(True)
        self.environmentMenu.addAction(self.installVenvAct)
        self.environmentMenu.addSeparator()
        self.environmentMenu.addAction(self.configureVenvAct)
        self.environmentMenu.addAction(self.upgradeVenvAct)
        self.environmentMenu.addSeparator()
        self.environmentMenu.addAction(self.recreateVenvAct)

        # build the packagers menu
        self.packagersMenu.setTearOffEnabled(True)
        self.packagersMenu.addActions(self.pluginGrp.actions())
        self.packagersMenu.addSeparator()

        # build the make menu
        self.makeMenu.setTearOffEnabled(True)
        self.makeMenu.addActions(self.makeGrp.actions())
        self.makeMenu.addSeparator()

        # build the 'Other Tools' menu
        self.othersMenu.setTearOffEnabled(True)
        self.othersMenu.addActions(self.othersGrp.actions())
        self.othersMenu.addSeparator()

        # build the 'Code Formatting' menu
        self.formattingMenu.setTearOffEnabled(True)
        self.formattingMenu.addActions(self.blackFormattingGrp.actions())
        self.formattingMenu.addSeparator()
        self.formattingMenu.addActions(self.isortFormattingGrp.actions())
        self.formattingMenu.addSeparator()

        # build the project main menu
        menu.setTearOffEnabled(True)
        menu.addActions(self.actGrp1.actions())
        self.menuRecentAct = menu.addMenu(self.recentMenu)
        menu.addSeparator()
        menu.addAction(self.closeAct)
        menu.addSeparator()
        menu.addAction(self.saveAct)
        menu.addAction(self.saveasAct)
        menu.addAction(self.saveasRemoteAct)
        menu.addSeparator()
        menu.addActions(self.actGrp2.actions())
        menu.addSeparator()
        menu.addAction(self.propsAct)
        menu.addAction(self.userPropsAct)
        menu.addAction(self.filetypesAct)
        menu.addAction(self.lexersAct)
        menu.addSeparator()
        self.menuEnvironmentAct = menu.addMenu(self.environmentMenu)
        menu.addSeparator()
        self.menuDebuggerAct = menu.addMenu(self.debuggerMenu)
        self.menuSessionAct = menu.addMenu(self.sessionMenu)

        # build the project tools menu
        toolsMenu.setTearOffEnabled(True)
        toolsMenu.addSeparator()
        self.menuVcsAct = toolsMenu.addMenu(self.vcsMenu)
        toolsMenu.addSeparator()
        self.menuCheckAct = toolsMenu.addMenu(self.checksMenu)
        toolsMenu.addSeparator()
        self.menuFormattingAct = toolsMenu.addMenu(self.formattingMenu)
        toolsMenu.addSeparator()
        self.menuMakeAct = toolsMenu.addMenu(self.makeMenu)
        toolsMenu.addSeparator()
        self.menuDiagramAct = toolsMenu.addMenu(self.graphicsMenu)
        toolsMenu.addSeparator()
        self.menuShowAct = toolsMenu.addMenu(self.menuShow)
        toolsMenu.addSeparator()
        self.menuApidocAct = toolsMenu.addMenu(self.apidocMenu)
        toolsMenu.addSeparator()
        self.menuPackagersAct = toolsMenu.addMenu(self.packagersMenu)
        toolsMenu.addSeparator()
        self.menuOtherToolsAct = toolsMenu.addMenu(self.othersMenu)

        self.menuCheckAct.setEnabled(False)
        self.menuShowAct.setEnabled(False)
        self.menuDiagramAct.setEnabled(False)
        self.menuSessionAct.setEnabled(False)
        self.menuDebuggerAct.setEnabled(False)
        self.menuApidocAct.setEnabled(False)
        self.menuPackagersAct.setEnabled(False)
        self.menuMakeAct.setEnabled(False)
        self.menuOtherToolsAct.setEnabled(False)
        self.menuFormattingAct.setEnabled(False)
        self.menuEnvironmentAct.setEnabled(False)

        self.__menu = menu
        self.__toolsMenu = toolsMenu

        return menu, toolsMenu

    def initToolbars(self, toolbarManager):
        """
        Public slot to initialize the project toolbar and the basic VCS
        toolbar.

        @param toolbarManager reference to a toolbar manager object
        @type EricToolBarManager
        @return tuple of the generated toolbars
        @rtype tuple of two QToolBar
        """
        from eric7 import VCS

        tb = QToolBar(self.tr("Project"), self.ui)
        tb.setObjectName("ProjectToolbar")
        tb.setToolTip(self.tr("Project"))

        tb.addActions(self.actGrp1.actions())
        tb.addAction(self.closeAct)
        tb.addSeparator()
        tb.addAction(self.saveAct)
        tb.addAction(self.saveasAct)
        tb.addAction(self.saveasRemoteAct)

        toolbarManager.addToolBar(tb, tb.windowTitle())
        toolbarManager.addAction(self.addFilesAct, tb.windowTitle())
        toolbarManager.addAction(self.addDirectoryAct, tb.windowTitle())
        toolbarManager.addAction(self.addLanguageAct, tb.windowTitle())
        toolbarManager.addAction(self.propsAct, tb.windowTitle())
        toolbarManager.addAction(self.userPropsAct, tb.windowTitle())

        vcstb = VCS.getBasicHelper(self).initBasicToolbar(self.ui, toolbarManager)

        return tb, vcstb

    def __showMenu(self):
        """
        Private method to set up the project menu.
        """
        self.menuRecentAct.setEnabled(len(self.recent) > 0)
        self.menuEnvironmentAct.setEnabled(
            self.__pdata["EMBEDDED_VENV"]
            and not FileSystemUtilities.isRemoteFileName(self.ppath)
        )

        self.showMenu.emit("Main", self.__menus["Main"])

    def __syncRecent(self):
        """
        Private method to synchronize the list of recently opened projects
        with the central store.
        """
        for recent in self.recent[:]:
            if (
                FileSystemUtilities.isRemoteFileName(recent) and recent == self.pfile
            ) or FileSystemUtilities.samepath(self.pfile, recent):
                self.recent.remove(recent)
        self.recent.insert(0, self.pfile)
        maxRecent = Preferences.getProject("RecentNumber")
        if len(self.recent) > maxRecent:
            self.recent = self.recent[:maxRecent]
        self.__saveRecent()

    def __showContextMenuRecent(self):
        """
        Private method to set up the recent projects menu.
        """
        self.__loadRecent()

        self.recentMenu.clear()

        for idx, rp in enumerate(self.recent, start=1):
            formatStr = "&{0:d}. {1}" if idx < 10 else "{0:d}. {1}"
            act = self.recentMenu.addAction(
                formatStr.format(
                    idx,
                    (
                        self.__remotefsInterface.compactPath(
                            rp, self.ui.maxMenuFilePathLen
                        )
                        if FileSystemUtilities.isRemoteFileName(rp)
                        else FileSystemUtilities.compactPath(
                            rp, self.ui.maxMenuFilePathLen
                        )
                    ),
                )
            )
            act.setData(rp)
            if FileSystemUtilities.isRemoteFileName(rp):
                act.setEnabled(
                    self.__remoteServer.isServerConnected
                    and self.__remotefsInterface.exists(rp)
                )
            else:
                act.setEnabled(pathlib.Path(rp).exists())

        self.recentMenu.addSeparator()
        self.recentMenu.addAction(self.tr("&Clear"), self.clearRecent)

    def __openRecent(self, act):
        """
        Private method to open a project from the list of rencently opened
        projects.

        @param act reference to the action that triggered
        @type QAction
        """
        file = act.data()
        if file:
            self.openProject(file)

    def clearRecent(self):
        """
        Public method to clear the recent projects menu.
        """
        self.recent = []
        self.__saveRecent()

    def clearHistories(self):
        """
        Public method to clear the project related histories.
        """
        self.clearRecent()

        for key in ["DebugClientsHistory", "DebuggerInterpreterHistory"]:
            Preferences.setProject(key, [])
        Preferences.syncPreferences()

    def __searchNewFiles(self):
        """
        Private slot used to handle the search new files action.
        """
        self.__doSearchNewFiles(False, True)

    def __searchProjectFile(self):
        """
        Private slot to show the Find Project File dialog.
        """
        from .QuickFindFileDialog import QuickFindFileDialog

        if self.__findProjectFileDialog is None:
            self.__findProjectFileDialog = QuickFindFileDialog(self)
            self.__findProjectFileDialog.sourceFile.connect(self.sourceFile)
            self.__findProjectFileDialog.designerFile.connect(self.designerFile)
            self.__findProjectFileDialog.linguistFile.connect(self.linguistFile)
        self.__findProjectFileDialog.show(
            FileSystemUtilities.isRemoteFileName(self.ppath)
        )
        self.__findProjectFileDialog.raise_()
        self.__findProjectFileDialog.activateWindow()

    def __doSearchNewFiles(self, AI=True, onUserDemand=False):
        """
        Private method to search for new files in the project directory.

        If new files were found, it shows a dialog listing these files and
        gives the user the opportunity to select the ones he wants to
        include. If 'Automatic Inclusion' is enabled, the new files are
        automatically added to the project.

        @param AI flag indicating whether the automatic inclusion should
                be honoured
        @type bool
        @param onUserDemand flag indicating whether this method was
                requested by the user via a menu action
        @type bool
        """
        from .AddFoundFilesDialog import AddFoundFilesDialog

        autoInclude = Preferences.getProject("AutoIncludeNewFiles")
        recursiveSearch = Preferences.getProject("SearchNewFilesRecursively")
        newFiles = []

        isRemote = FileSystemUtilities.isRemoteFileName(self.ppath)

        ignore_patterns = [
            pattern
            for pattern, filetype in self.__pdata["FILETYPES"].items()
            if filetype == "__IGNORE__"
        ]

        dirs = [""] if recursiveSearch else self.subdirs[:] + [""]
        for directory in dirs:
            if any(
                fnmatch.fnmatch(directory, ignore_pattern)
                for ignore_pattern in ignore_patterns
            ):
                continue

            curpath = (
                self.__remotefsInterface.join(self.ppath, directory)
                if isRemote
                else os.path.join(self.ppath, directory)
            )
            try:
                newSources = (
                    [e["name"] for e in self.__remotefsInterface.listdir(curpath)[2]]
                    if isRemote
                    else os.listdir(curpath)
                )
            except OSError:
                newSources = []
            pattern = (
                self.__pdata["TRANSLATIONPATTERN"].replace("%language%", "*")
                if self.__pdata["TRANSLATIONPATTERN"]
                else "*.ts"
            )
            binpattern = self.__binaryTranslationFile(pattern)
            for ns in newSources:
                # ignore hidden files and directories
                if ns.startswith(".") or ns == "__pycache__":
                    continue

                # set fn to project relative name
                # then reset ns to fully qualified name for insertion,
                # possibly.
                if isRemote:
                    fn = (
                        self.__remotefsInterface.join(directory, ns)
                        if directory
                        else ns
                    )
                    ns = self.__remotefsInterface.abspath(
                        self.__remotefsInterface.join(curpath, ns)
                    )

                    isdir_ns = self.__remotefsInterface.isdir(ns)
                else:
                    fn = os.path.join(directory, ns) if directory else ns
                    ns = os.path.abspath(os.path.join(curpath, ns))
                    isdir_ns = os.path.isdir(ns)

                # do not bother with dirs here...
                if isdir_ns:
                    if recursiveSearch:
                        d = self.getRelativePath(ns)
                        if d not in dirs:
                            dirs.append(d)  # noqa: M569
                    continue

                filetype = ""
                bfn = (
                    self.__remotefsInterface.basename(fn)
                    if isRemote
                    else os.path.basename(fn)
                )

                # check against ignore patterns first (see issue 553)
                if any(
                    fnmatch.fnmatch(bfn, ignore_pattern)
                    for ignore_pattern in ignore_patterns
                ):
                    continue

                for pattern in self.__pdata["FILETYPES"]:
                    if fnmatch.fnmatch(bfn, pattern):
                        filetype = self.__pdata["FILETYPES"][pattern]
                        break

                if (
                    filetype in self.getFileCategories()
                    and (
                        fn not in self.__pdata[filetype]
                        or (
                            filetype == "OTHERS"
                            and fn not in self.__pdata[filetype]
                            and os.path.dirname(fn) not in self.__pdata["OTHERS"]
                        )
                    )
                    and (
                        filetype != "TRANSLATIONS"
                        or (
                            filetype == "TRANSLATIONS"
                            and (
                                fnmatch.fnmatch(ns, pattern)
                                or fnmatch.fnmatch(ns, binpattern)
                            )
                        )
                    )
                ):
                    if autoInclude and AI:
                        self.appendFile(ns)
                    else:
                        newFiles.append(ns)

        # if autoInclude is set there is no more work left
        if autoInclude and AI:
            return

        # if newfiles is empty, put up message box informing user nothing found
        if not newFiles:
            if onUserDemand:
                EricMessageBox.information(
                    self.ui,
                    self.tr("Search New Files"),
                    self.tr("There were no new files found to be added."),
                )
            return

        # autoInclude is not set, show a dialog
        dlg = AddFoundFilesDialog(newFiles, self.parent(), None)
        res = dlg.exec()

        # the 'Add All' button was pressed
        if res == 1:
            for file in newFiles:
                self.appendFile(file)

        # the 'Add Selected' button was pressed
        elif res == 2:
            files = dlg.getSelection()
            for file in files:
                self.appendFile(file)

    def othersAdded(self, fn, updateModel=True):
        """
        Public slot to be called, if something was added to the OTHERS project
        data area.

        @param fn filename or directory name added
        @type str
        @param updateModel flag indicating an update of the model is requested
        @type bool
        """
        self.projectFileAdded.emit(fn, "OTHERS")
        updateModel and self.__model.addNewItem("OTHERS", fn)

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
        @return reference to the requested menu or None
        @rtype QMenu
        """
        try:
            return self.__menus[menuName]
        except KeyError:
            return None

    def repopulateItem(self, fullname):
        """
        Public slot to repopulate a named item.

        @param fullname full name of the item to repopulate
        @type str
        """
        if not self.isOpen():
            return

        with EricOverrideCursor():
            name = self.getRelativePath(fullname)
            self.prepareRepopulateItem.emit(name)
            self.__model.repopulateItem(name)
            self.completeRepopulateItem.emit(name)

    ##############################################################
    ## Below is the VCS interface
    ##############################################################

    def initVCS(self, vcsSystem=None, nooverride=False):
        """
        Public method used to instantiate a vcs system.

        @param vcsSystem type of VCS to be used
        @type str
        @param nooverride flag indicating to ignore an override request
        @type bool
        @return a reference to the vcs object
        @rtype VersionControl
        """
        from eric7 import VCS

        vcs = None
        forProject = True
        override = False

        if FileSystemUtilities.isRemoteFileName(self.ppath):
            return None

        if vcsSystem is None:
            if self.__pdata["VCS"] and self.__pdata["VCS"] != "None":
                vcsSystem = self.__pdata["VCS"]
        else:
            forProject = False

        if (
            forProject
            and self.__pdata["VCS"]
            and self.__pdata["VCS"] != "None"
            and self.pudata["VCSOVERRIDE"]
            and not nooverride
        ):
            vcsSystem = self.pudata["VCSOVERRIDE"]
            override = True

        if vcsSystem is not None:
            try:
                vcs = VCS.factory(vcsSystem)
            except ImportError:
                if override:
                    # override failed, revert to original
                    self.pudata["VCSOVERRIDE"] = ""
                    return self.initVCS(nooverride=True)

        if vcs:
            vcsExists, msg = vcs.vcsExists()
            if not vcsExists:
                if override:
                    # override failed, revert to original
                    with EricOverridenCursor():
                        EricMessageBox.critical(
                            self.ui,
                            self.tr("Version Control System"),
                            self.tr(
                                "<p>The selected VCS <b>{0}</b> could not be"
                                " found. <br/>Reverting override.</p><p>{1}"
                                "</p>"
                            ).format(vcsSystem, msg),
                        )
                        self.pudata["VCSOVERRIDE"] = ""
                    return self.initVCS(nooverride=True)

                with EricOverridenCursor():
                    EricMessageBox.critical(
                        self.ui,
                        self.tr("Version Control System"),
                        self.tr(
                            "<p>The selected VCS <b>{0}</b> could not be"
                            " found.<br/>Disabling version control.</p>"
                            "<p>{1}</p>"
                        ).format(vcsSystem, msg),
                    )
                vcs = None
                if forProject:
                    self.__pdata["VCS"] = "None"
                    self.setDirty(True)
            else:
                vcs.vcsInitConfig(self)

        if vcs and forProject:
            # set the vcs options
            if vcs.vcsSupportCommandOptions():
                with contextlib.suppress(LookupError):
                    vcsopt = copy.deepcopy(self.__pdata["VCSOPTIONS"])
                    vcs.vcsSetOptions(vcsopt)
            # set vcs specific data
            with contextlib.suppress(LookupError):
                vcsother = copy.deepcopy(self.__pdata["VCSOTHERDATA"])
                vcs.vcsSetOtherData(vcsother)

        if forProject:
            if vcs is None:
                self.vcsProjectHelper = VCS.getBasicHelper(self)
                self.vcsBasicHelper = True
            else:
                self.vcsProjectHelper = vcs.vcsGetProjectHelper(self)
                self.vcsBasicHelper = False
            if self.vcsMenu is not None:
                self.vcsProjectHelper.initMenu(self.vcsMenu)
                self.vcsMenu.setEnabled(self.vcsSoftwareAvailable())

        return vcs

    def resetVCS(self):
        """
        Public method to reset the VCS.
        """
        self.__pdata["VCS"] = "None"
        self.vcs = self.initVCS()
        ericApp().getObject("PluginManager").deactivateVcsPlugins()

    def __showContextMenuVCS(self):
        """
        Private slot called before the vcs menu is shown.
        """
        self.vcsProjectHelper.showMenu()
        if self.vcsBasicHelper:
            self.showMenu.emit("VCS", self.vcsMenu)

    def vcsSoftwareAvailable(self):
        """
        Public method to check, if some supported VCS software is available
        to the IDE.

        @return flag indicating availability of VCS software
        @rtype bool
        """
        vcsSystemsDict = (
            ericApp()
            .getObject("PluginManager")
            .getPluginDisplayStrings("version_control")
        )
        return len(vcsSystemsDict) != 0

    def __vcsStatusChanged(self):
        """
        Private slot to handle a change of the overall VCS status.
        """
        self.projectChanged.emit()

    def __vcsConnectStatusMonitor(self):
        """
        Private method to start the VCS monitor and connect its signals.
        """
        if self.vcs is not None:
            self.vcs.committed.connect(self.vcsCommitted)

            self.vcs.startStatusMonitor(self)
            self.vcs.vcsStatusMonitorData.connect(self.__model.changeVCSStates)
            self.vcs.vcsStatusMonitorData.connect(self.vcsStatusMonitorData)
            self.vcs.vcsStatusMonitorAllData.connect(self.vcsStatusMonitorAllData)
            self.vcs.vcsStatusMonitorStatus.connect(self.vcsStatusMonitorStatus)
            self.vcs.vcsStatusMonitorInfo.connect(self.vcsStatusMonitorInfo)
            self.vcs.vcsStatusChanged.connect(self.__vcsStatusChanged)

    #########################################################################
    ## Below is the interface to the checker tools
    #########################################################################

    def __showContextMenuChecks(self):
        """
        Private slot called before the checks menu is shown.
        """
        self.showMenu.emit("Checks", self.checksMenu)

    #########################################################################
    ## Below is the interface to the packagers tools
    #########################################################################

    def __showContextMenuPackagers(self):
        """
        Private slot called before the packagers menu is shown.
        """
        self.showMenu.emit("Packagers", self.packagersMenu)

    #########################################################################
    ## Below is the interface to the apidoc tools
    #########################################################################

    def __showContextMenuApiDoc(self):
        """
        Private slot called before the apidoc menu is shown.
        """
        self.showMenu.emit("Apidoc", self.apidocMenu)

    #########################################################################
    ## Below is the interface to the show tools
    #########################################################################

    def __showCodeMetrics(self):
        """
        Private slot used to calculate some code metrics for the project files.
        """
        from eric7.DataViews.CodeMetricsDialog import CodeMetricsDialog

        files = (
            [
                self.__remotefsInterface.join(self.ppath, file)
                for file in self.__pdata["SOURCES"]
                if file.endswith(".py")
            ]
            if FileSystemUtilities.isRemoteFileName(self.ppath)
            else [
                os.path.join(self.ppath, file)
                for file in self.__pdata["SOURCES"]
                if file.endswith(".py")
            ]
        )
        self.codemetrics = CodeMetricsDialog()
        self.codemetrics.show()
        self.codemetrics.prepare(files)

    def __showCodeCoverage(self):
        """
        Private slot used to show the code coverage information for the
        project files.
        """
        from eric7.DataViews.PyCoverageDialog import PyCoverageDialog

        fn = self.getMainScript(True)
        if fn is None:
            EricMessageBox.critical(
                self.ui,
                self.tr("Coverage Data"),
                self.tr(
                    "There is no main script defined for the"
                    " current project. Aborting"
                ),
            )
            return

        files = Utilities.getCoverageFileNames(fn)
        if files:
            if len(files) > 1:
                fn, ok = QInputDialog.getItem(
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
                fn = files[0]
        else:
            return

        files = (
            [
                self.__remotefsInterface.join(self.ppath, file)
                for file in self.__pdata["SOURCES"]
                if self.__remotefsInterface.splitext(file)[1].startswith(".py")
            ]
            if FileSystemUtilities.isRemoteFileName(self.ppath)
            else [
                os.path.join(self.ppath, file)
                for file in self.__pdata["SOURCES"]
                if os.path.splitext(file)[1].startswith(".py")
            ]
        )
        self.codecoverage = PyCoverageDialog()
        self.codecoverage.show()
        self.codecoverage.start(fn, files)

    def __showProfileData(self):
        """
        Private slot used to show the profiling information for the project.
        """
        from eric7.DataViews.PyProfileDialog import PyProfileDialog

        fn = self.getMainScript(True)
        if fn is None:
            EricMessageBox.critical(
                self.ui,
                self.tr("Profile Data"),
                self.tr(
                    "There is no main script defined for the"
                    " current project. Aborting"
                ),
            )
            return

        files = Utilities.getProfileFileNames(fn)
        if files:
            if len(files) > 1:
                fn, ok = QInputDialog.getItem(
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
                fn = files[0]
        else:
            return

        self.profiledata = PyProfileDialog()
        self.profiledata.show()
        self.profiledata.start(fn)

    def __showContextMenuShow(self):
        """
        Private slot called before the show menu is shown.
        """
        fn = self.getMainScript(True)
        if not fn:
            fn = self.getProjectPath()

        self.codeProfileAct.setEnabled(
            self.isPy3Project() and bool(Utilities.getProfileFileName(fn))
        )
        self.codeCoverageAct.setEnabled(
            self.isPy3Project() and bool(Utilities.getCoverageFileNames(fn))
        )

        self.showMenu.emit("Show", self.menuShow)

    #########################################################################
    ## Below is the interface to the diagrams
    #########################################################################

    def __showContextMenuGraphics(self):
        """
        Private slot called before the graphics menu is shown.
        """
        self.showMenu.emit("Graphics", self.graphicsMenu)

    def handleApplicationDiagram(self):
        """
        Public method to handle the application diagram context menu action.
        """
        from eric7.Graphics.UMLDialog import UMLDialog, UMLDialogType

        res = EricMessageBox.yesNo(
            self.ui,
            self.tr("Application Diagram"),
            self.tr("""Include module names?"""),
            yesDefault=True,
        )

        self.applicationDiagram = UMLDialog(
            UMLDialogType.APPLICATION_DIAGRAM, self, self.parent(), noModules=not res
        )
        self.applicationDiagram.show()

    def __loadDiagram(self):
        """
        Private slot to load a diagram from file.
        """
        from eric7.Graphics.UMLDialog import UMLDialog, UMLDialogType

        self.loadedDiagram = None
        loadedDiagram = UMLDialog(UMLDialogType.NO_DIAGRAM, self, parent=self.parent())
        if loadedDiagram.load():
            self.loadedDiagram = loadedDiagram
            self.loadedDiagram.show(fromFile=True)

    #########################################################################
    ## Below is the interface to the VCS monitor thread
    #########################################################################

    def setStatusMonitorInterval(self, interval):
        """
        Public method to se the interval of the VCS status monitor thread.

        @param interval status monitor interval in seconds
        @type int
        """
        if self.vcs is not None:
            self.vcs.setStatusMonitorInterval(interval, self)

    def getStatusMonitorInterval(self):
        """
        Public method to get the monitor interval.

        @return interval in seconds
        @rtype int
        """
        if self.vcs is not None:
            return self.vcs.getStatusMonitorInterval()
        else:
            return 0

    def setStatusMonitorAutoUpdate(self, auto):
        """
        Public method to enable the auto update function.

        @param auto status of the auto update function
        @type bool
        """
        if self.vcs is not None:
            self.vcs.setStatusMonitorAutoUpdate(auto)

    def getStatusMonitorAutoUpdate(self):
        """
        Public method to retrieve the status of the auto update function.

        @return status of the auto update function
        @rtype bool
        """
        if self.vcs is not None:
            return self.vcs.getStatusMonitorAutoUpdate()
        else:
            return False

    def checkVCSStatus(self):
        """
        Public method to wake up the VCS status monitor thread.
        """
        if self.vcs is not None:
            self.vcs.checkVCSStatus()

    def clearStatusMonitorCachedState(self, name):
        """
        Public method to clear the cached VCS state of a file/directory.

        @param name name of the entry to be cleared
        @type str
        """
        if self.vcs is not None:
            self.vcs.clearStatusMonitorCachedState(name)

    def startStatusMonitor(self):
        """
        Public method to start the VCS status monitor thread.
        """
        if self.vcs is not None:
            self.vcs.startStatusMonitor(self)

    def stopStatusMonitor(self):
        """
        Public method to stop the VCS status monitor thread.
        """
        if self.vcs is not None:
            self.vcs.stopStatusMonitor()

    #########################################################################
    ## Below are the plugin development related methods
    #########################################################################

    def __pluginCreatePkgList(self):
        """
        Private slot to create a PKGLIST file needed for archive file creation.
        """
        pkglist = os.path.join(self.ppath, "PKGLIST")
        if os.path.exists(pkglist):
            res = EricMessageBox.yesNo(
                self.ui,
                self.tr("Create Package List"),
                self.tr(
                    "<p>The file <b>PKGLIST</b> already"
                    " exists.</p><p>Overwrite it?</p>"
                ),
                icon=EricMessageBox.Warning,
            )
            if not res:
                return  # don't overwrite

        # build the list of entries
        lst_ = []
        for key in self.getFileCategories():
            lst_.extend(self.__pdata[key])
        lst = []
        for entry in lst_:
            if os.path.isdir(self.getAbsolutePath(entry)):
                lst.extend(
                    [
                        self.getRelativePath(p)
                        for p in FileSystemUtilities.direntries(
                            self.getAbsolutePath(entry), True
                        )
                    ]
                )
                continue
            else:
                lst.append(entry)
        lst.sort()
        if "PKGLIST" in lst:
            lst.remove("PKGLIST")

        # build the header to indicate a freshly generated list
        header = [
            ";",
            "; initial_list (REMOVE THIS LINE WHEN DONE)",
            ";",
            " ",
        ]

        # write the file
        try:
            newline = None if self.__pdata["EOL"] == 0 else self.getEolString()
            with open(pkglist, "w", encoding="utf-8", newline=newline) as pkglistFile:
                pkglistFile.write("\n".join(header) + "\n")
                pkglistFile.write(
                    "\n".join(
                        [FileSystemUtilities.fromNativeSeparators(f) for f in lst]
                    )
                )
                pkglistFile.write("\n")
                # ensure the file ends with an empty line
        except OSError as why:
            EricMessageBox.critical(
                self.ui,
                self.tr("Create Package List"),
                self.tr(
                    """<p>The file <b>PKGLIST</b> could not be created.</p>"""
                    """<p>Reason: {0}</p>"""
                ).format(str(why)),
            )
            return

        if "PKGLIST" not in self.__pdata["OTHERS"]:
            self.appendFile("PKGLIST")

    @pyqtSlot()
    def __pluginCreateArchives(self, snapshot=False):
        """
        Private slot to create eric plugin archives.

        @param snapshot flag indicating snapshot archives
        @type bool
        """
        if not self.__pdata["MAINSCRIPT"]:
            EricMessageBox.critical(
                self.ui,
                self.tr("Create Plugin Archive"),
                self.tr(
                    """The project does not have a main script defined. """
                    """Aborting..."""
                ),
            )
            return

        selectedLists = []
        pkglists = [
            os.path.basename(f) for f in glob.glob(os.path.join(self.ppath, "PKGLIST*"))
        ]
        if len(pkglists) == 1:
            selectedLists = [os.path.join(self.ppath, pkglists[0])]
        elif len(pkglists) > 1:
            dlg = EricListSelectionDialog(
                sorted(pkglists),
                title=self.tr("Create Plugin Archive"),
                message=self.tr("Select package lists:"),
                checkBoxSelection=True,
                parent=self.ui,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                selectedLists = [
                    os.path.join(self.ppath, s) for s in dlg.getSelection()
                ]
            else:
                return

        if not selectedLists:
            EricMessageBox.critical(
                self.ui,
                self.tr("Create Plugin Archive"),
                self.tr(
                    """<p>No package list files (PKGLIST*) available or"""
                    """ selected. Aborting...</p>"""
                ),
            )
            return

        progress = EricProgressDialog(
            self.tr("Creating plugin archives..."),
            self.tr("Abort"),
            0,
            len(selectedLists),
            self.tr("%v/%m Archives"),
            self.ui,
        )
        progress.setMinimumDuration(0)
        progress.setWindowTitle(self.tr("Create Plugin Archives"))
        errors = 0
        for count, pkglist in enumerate(selectedLists):
            progress.setValue(count)
            if progress.wasCanceled():
                break

            try:
                with open(pkglist, "r", encoding="utf-8") as pkglistFile:
                    names = pkglistFile.read()
            except OSError as why:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Create Plugin Archive"),
                    self.tr(
                        """<p>The file <b>{0}</b> could not be read.</p>"""
                        """<p>Reason: {1}</p>"""
                    ).format(os.path.basename(pkglist), str(why)),
                )
                errors += 1
                continue

            lines = names.splitlines()
            archiveName = ""
            archiveVersion = ""
            names = []
            listOK = True
            for line in lines:
                if line.startswith(";"):
                    line = line[1:].strip()
                    # it's a comment possibly containing a directive
                    # supported directives are:
                    # - archive_name= defines the name of the archive
                    # - archive_version= defines the version of the archive
                    if line.startswith("archive_name="):
                        archiveName = line.split("=")[1]
                    elif line.startswith("archive_version="):
                        archiveVersion = line.split("=")[1]
                    elif line.startswith("initial_list "):
                        EricMessageBox.critical(
                            self.ui,
                            self.tr("Create Plugin Archive"),
                            self.tr(
                                """<p>The file <b>{0}</b> is not ready yet."""
                                """</p><p>Please rework it and delete the"""
                                """'; initial_list' line of the header."""
                                """</p>"""
                            ).format(os.path.basename(pkglist)),
                        )
                        errors += 1
                        listOK = False
                        break
                elif line.strip():
                    names.append(line.strip())

            if not listOK:
                continue

            names = sorted(names)
            archive = (
                os.path.join(self.ppath, archiveName)
                if archiveName
                else os.path.join(
                    self.ppath, self.__pdata["MAINSCRIPT"].replace(".py", ".zip")
                )
            )
            try:
                archiveFile = zipfile.ZipFile(archive, "w")
            except OSError as why:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Create Plugin Archive"),
                    self.tr(
                        """<p>The eric plugin archive file <b>{0}</b>"""
                        """ could not be created.</p>"""
                        """<p>Reason: {1}</p>"""
                    ).format(archive, str(why)),
                )
                errors += 1
                continue

            # recompile all included compiled forms
            for name in names:
                nameList = os.path.split(name)
                if nameList[1].startswith("Ui_") and nameList[1].endswith(".py"):
                    # It is a compiled form file.
                    formPath = os.path.join(
                        nameList[0],
                        nameList[1].replace("Ui_", "").replace(".py", ".ui"),
                    )
                    compileOneUi(
                        os.path.join(self.ppath, formPath), uiheadername=formPath
                    )

            # create the plugin archive
            for name in names:
                if name:
                    try:
                        self.__createZipDirEntries(os.path.split(name)[0], archiveFile)
                        if snapshot and name == self.__pdata["MAINSCRIPT"]:
                            snapshotSource, version = self.__createSnapshotSource(
                                os.path.join(self.ppath, self.__pdata["MAINSCRIPT"])
                            )
                            archiveFile.writestr(name, snapshotSource)
                        else:
                            archiveFile.write(os.path.join(self.ppath, name), name)
                            if name == self.__pdata["MAINSCRIPT"]:
                                version = self.__pluginExtractVersion(
                                    os.path.join(self.ppath, self.__pdata["MAINSCRIPT"])
                                )
                                if archiveVersion and (
                                    EricUtilities.versionToTuple(version)
                                    < EricUtilities.versionToTuple(archiveVersion)
                                ):
                                    version = archiveVersion
                    except OSError as why:
                        EricMessageBox.critical(
                            self.ui,
                            self.tr("Create Plugin Archive"),
                            self.tr(
                                """<p>The file <b>{0}</b> could not be"""
                                """ stored in the archive. Ignoring it.</p>"""
                                """<p>Reason: {1}</p>"""
                            ).format(os.path.join(self.ppath, name), str(why)),
                        )
            archiveFile.writestr("VERSION", version.encode("utf-8"))
            archiveFile.close()

            if archive not in self.__pdata["OTHERS"]:
                self.appendFile(archive)

        progress.setValue(len(selectedLists))

        if errors:
            self.ui.showNotification(
                EricPixmapCache.getPixmap("pluginArchive48"),
                self.tr("Create Plugin Archive"),
                self.tr(
                    "<p>The eric plugin archive files were "
                    "created with some errors.</p>"
                ),
                kind=NotificationTypes.CRITICAL,
                timeout=0,
            )
        else:
            self.ui.showNotification(
                EricPixmapCache.getPixmap("pluginArchive48"),
                self.tr("Create Plugin Archive"),
                self.tr(
                    "<p>The eric plugin archive files were created successfully.</p>"
                ),
            )

    def __pluginCreateSnapshotArchives(self):
        """
        Private slot to create eric plugin archive snapshot releases.
        """
        self.__pluginCreateArchives(True)

    def __createZipDirEntries(self, path, zipFile):
        """
        Private method to create dir entries in the zip file.

        @param path name of the directory entry to create
        @type str
        @param zipFile open ZipFile object
        @type zipfile.ZipFile
        """
        if path in ("", "/", "\\"):
            return

        if not path.endswith("/") and not path.endswith("\\"):
            path = "{0}/".format(path)

        if path not in zipFile.namelist():
            self.__createZipDirEntries(os.path.split(path[:-1])[0], zipFile)
            zipFile.writestr(path, b"")

    def __createSnapshotSource(self, filename):
        """
        Private method to create a snapshot plugin version.

        The version entry in the plugin module is modified to signify
        a snapshot version. This method appends the string "-snapshot-"
        and date indicator to the version string.

        @param filename name of the plugin file to modify
        @type str
        @return modified source (bytes), snapshot version string
        @rtype str
        """
        try:
            sourcelines, encoding = Utilities.readEncodedFile(filename)
            sourcelines = sourcelines.splitlines(True)
        except (OSError, UnicodeError) as why:
            EricMessageBox.critical(
                self.ui,
                self.tr("Create Plugin Archive"),
                self.tr(
                    """<p>The plugin file <b>{0}</b> could """
                    """not be read.</p>"""
                    """<p>Reason: {1}</p>"""
                ).format(filename, str(why)),
            )
            return b"", ""

        lineno = 0
        while lineno < len(sourcelines):
            if sourcelines[lineno].startswith("version = "):
                # found the line to modify
                datestr = time.strftime("%Y%m%d")
                lineend = sourcelines[lineno].replace(sourcelines[lineno].rstrip(), "")
                sversion = "{0}-snapshot-{1}".format(
                    sourcelines[lineno].replace("version = ", "").strip()[1:-1], datestr
                )
                sourcelines[lineno] = '{0} + "-snapshot-{1}"{2}'.format(
                    sourcelines[lineno].rstrip(), datestr, lineend
                )
                break

            lineno += 1

        source = Utilities.encode("".join(sourcelines), encoding)[0]
        return source, sversion

    def __pluginExtractVersion(self, filename):
        """
        Private method to extract the version number entry.

        @param filename name of the plugin file
        @type str
        @return version string
        @rtype str
        """
        version = "0.0.0"
        try:
            sourcelines = Utilities.readEncodedFile(filename)[0]
            sourcelines = sourcelines.splitlines(True)
        except (OSError, UnicodeError) as why:
            EricMessageBox.critical(
                self.ui,
                self.tr("Create Plugin Archive"),
                self.tr(
                    """<p>The plugin file <b>{0}</b> could """
                    """not be read.</p> <p>Reason: {1}</p>"""
                ).format(filename, str(why)),
            )
            return ""

        for sourceline in sourcelines:
            if sourceline.startswith("version = "):
                # old variant of plugin header
                version = (
                    sourceline.replace("version = ", "")
                    .strip()
                    .replace('"', "")
                    .replace("'", "")
                )
                break
            elif sourceline.strip().startswith(('"version":', "'version':")):
                # new variant of plugin header
                version = (
                    sourceline.replace('"version":', "")
                    .replace("'version':", "")
                    .replace('"', "")
                    .replace("'", "")
                    .replace(",", "")
                    .strip()
                )
                break

        return version

    #########################################################################
    ## Below are methods implementing the 'make' support
    #########################################################################

    def __showContextMenuMake(self):
        """
        Private slot called before the make menu is shown.
        """
        self.showMenu.emit("Make", self.makeMenu)

    def hasDefaultMakeParameters(self):
        """
        Public method to test, if the project contains the default make
        parameters.

        @return flag indicating default parameter set
        @rtype bool
        """
        return self.__pdata["MAKEPARAMS"] == {
            "MakeEnabled": False,
            "MakeExecutable": "",
            "MakeFile": "",
            "MakeTarget": "",
            "MakeParameters": "",
            "MakeTestOnly": True,
        }

    def isMakeEnabled(self):
        """
        Public method to test, if make is enabled for the project.

        @return flag indicating enabled make support
        @rtype bool
        """
        return self.__pdata["MAKEPARAMS"][
            "MakeEnabled"
        ] and not FileSystemUtilities.isRemoteFileName(self.ppath)

    @pyqtSlot()
    def __autoExecuteMake(self):
        """
        Private slot to execute a project specific make run (auto-run)
        (execute or question).
        """
        if Preferences.getProject(
            "AutoExecuteMake"
        ) and not FileSystemUtilities.isRemoteFileName(self.ppath):
            self.__executeMake(questionOnly=self.__pdata["MAKEPARAMS"]["MakeTestOnly"])

    @pyqtSlot()
    def __executeMake(self, questionOnly=False):
        """
        Private method to execute a project specific make run.

        @param questionOnly flag indicating to ask make for changes only
        @type bool
        """
        if FileSystemUtilities.isRemoteFileName(self.ppath):
            EricMessageBox.critical(
                self.ui,
                self.tr("Execute Make"),
                self.tr("'Make' is not supported for remote projects. Aborting..."),
            )
            return

        if (
            not self.__pdata["MAKEPARAMS"]["MakeEnabled"]
            or self.__makeProcess is not None
        ):
            return

        prog = (
            self.__pdata["MAKEPARAMS"]["MakeExecutable"]
            if self.__pdata["MAKEPARAMS"]["MakeExecutable"]
            else Project.DefaultMake
        )

        args = []
        if self.__pdata["MAKEPARAMS"]["MakeParameters"]:
            args.extend(
                Utilities.parseOptionString(
                    self.__pdata["MAKEPARAMS"]["MakeParameters"]
                )
            )

        if self.__pdata["MAKEPARAMS"]["MakeFile"]:
            args.append("--makefile={0}".format(self.__pdata["MAKEPARAMS"]["MakeFile"]))

        if questionOnly:
            args.append("--question")

        if self.__pdata["MAKEPARAMS"]["MakeTarget"]:
            args.append(self.__pdata["MAKEPARAMS"]["MakeTarget"])

        self.__makeProcess = QProcess(self)
        self.__makeProcess.readyReadStandardOutput.connect(self.__makeReadStdOut)
        self.__makeProcess.readyReadStandardError.connect(self.__makeReadStdErr)
        self.__makeProcess.finished.connect(
            lambda exitCode, exitStatus: self.__makeFinished(
                exitCode, exitStatus, questionOnly
            )
        )
        self.__makeProcess.setWorkingDirectory(self.getProjectPath())
        self.__makeProcess.start(prog, args)

        if not self.__makeProcess.waitForStarted():
            EricMessageBox.critical(
                self.ui,
                self.tr("Execute Make"),
                self.tr("""The make process did not start."""),
            )

            self.__cleanupMake()

    @pyqtSlot()
    def __makeReadStdOut(self):
        """
        Private slot to process process output received via stdout.
        """
        if self.__makeProcess is not None:
            output = str(
                self.__makeProcess.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.appendStdout.emit(output)

    @pyqtSlot()
    def __makeReadStdErr(self):
        """
        Private slot to process process output received via stderr.
        """
        if self.__makeProcess is not None:
            error = str(
                self.__makeProcess.readAllStandardError(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            )
            self.appendStderr.emit(error)

    def __makeFinished(self, exitCode, exitStatus, questionOnly):
        """
        Private slot handling the make process finished signal.

        @param exitCode exit code of the make process
        @type int
        @param exitStatus exit status of the make process
        @type QProcess.ExitStatus
        @param questionOnly flag indicating a test only run
        @type bool
        """
        if exitStatus == QProcess.ExitStatus.CrashExit:
            EricMessageBox.critical(
                self.ui,
                self.tr("Execute Make"),
                self.tr("""The make process crashed."""),
            )
        else:
            if questionOnly and exitCode == 1:
                # a rebuild is needed
                title = self.tr("Test for Changes")

                if self.__pdata["MAKEPARAMS"]["MakeTarget"]:
                    message = self.tr(
                        """<p>There are changes that require the configured"""
                        """ make target <b>{0}</b> to be rebuilt.</p>"""
                    ).format(self.__pdata["MAKEPARAMS"]["MakeTarget"])
                else:
                    message = self.tr(
                        """<p>There are changes that require the default"""
                        """ make target to be rebuilt.</p>"""
                    )

                self.ui.showNotification(
                    EricPixmapCache.getPixmap("makefile48"),
                    title,
                    message,
                    kind=NotificationTypes.WARNING,
                    timeout=0,
                )
            elif exitCode > 1:
                EricMessageBox.critical(
                    self.ui,
                    self.tr("Execute Make"),
                    self.tr("""The makefile contains errors."""),
                )

        self.__cleanupMake()

    def __cleanupMake(self):
        """
        Private method to clean up make related stuff.
        """
        self.__makeProcess.readyReadStandardOutput.disconnect()
        self.__makeProcess.readyReadStandardError.disconnect()
        self.__makeProcess.finished.disconnect()
        self.__makeProcess.deleteLater()
        self.__makeProcess = None

    #########################################################################
    ## Below are methods implementing some 'UIC' support functions
    #########################################################################

    def hasDefaultUicCompilerParameters(self):
        """
        Public method to test, if the project contains the default uic compiler
        parameters.

        @return flag indicating default parameter set
        @rtype bool
        """
        return self.__pdata["UICPARAMS"] == {
            "Package": "",
            "RcSuffix": "",
            "PackagesRoot": "",
        }

    def getUicParameter(self, name):
        """
        Public method to get a named uic related parameter.

        @param name name of the parameter
        @type str
        @return value of the given parameter
        @rtype Any, None in case on non-existence
        """
        if name in self.__pdata["UICPARAMS"]:
            return self.__pdata["UICPARAMS"][name]
        else:
            return None

    #########################################################################
    ## Below are methods implementing some 'RCC' support functions
    #########################################################################

    def hasDefaultRccCompilerParameters(self):
        """
        Public method to test, if the project contains the default rcc compiler
        parameters.

        @return flag indicating default parameter set
        @rtype bool
        """
        return self.__pdata["RCCPARAMS"] == self.getDefaultRccCompilerParameters()

    def getDefaultRccCompilerParameters(self):
        """
        Public method to get the default rcc compiler parameters.

        @return dictionary containing the default rcc compiler parameters
        @rtype dict
        """
        return {
            "CompressionThreshold": 70,  # default value
            "CompressLevel": 0,  # use zlib default
            "CompressionDisable": False,
            "PathPrefix": "",
        }

    #########################################################################
    ## Below are methods implementing some 'docstring' support functions
    #########################################################################

    def hasDefaultDocstringParameter(self):
        """
        Public method to test, if the project contains the default docstring
        parameter.

        @return flag indicating default parameter
        @rtype bool
        """
        return self.__pdata["DOCSTRING"] == ""

    def getDocstringType(self):
        """
        Public method to get the configured docstring style.

        @return configured docstring style
        @rtype str
        """
        return self.__pdata["DOCSTRING"]

    #########################################################################
    ## Below are methods implementing the 'SBOM' support
    #########################################################################

    def __showContextMenuOthers(self):
        """
        Private slot called before the 'Other Tools' menu is shown.
        """
        self.createSBOMAct.setEnabled(
            not FileSystemUtilities.isRemoteFileName(self.ppath)
        )

        self.showMenu.emit("OtherTools", self.othersMenu)

    @pyqtSlot()
    def __createSBOMFile(self):
        """
        Private slot to create a SBOM file of the project dependencies.
        """
        from eric7 import CycloneDXInterface

        CycloneDXInterface.createCycloneDXFile("<project>", parent=self.ui)

    #########################################################################
    ## Below are methods implementing the 'Code Formatting' support
    #########################################################################

    def __showContextMenuFormat(self):
        """
        Private slot called before the 'Code Formatting' menu is shown.
        """
        self.showMenu.emit("Formatting", self.formattingMenu)

    def __performFormatWithBlack(self, action):
        """
        Private method to format the project sources using the 'Black' tool.

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

        if ericApp().getObject("ViewManager").checkAllDirty():
            dlg = BlackConfigurationDialog(withProject=True, parent=self.ui)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                config = dlg.getConfiguration(saveToProject=True)

                formattingDialog = BlackFormattingDialog(
                    config,
                    self.getProjectFiles("SOURCES", normalized=True),
                    project=self,
                    action=action,
                    parent=self.ui,
                )
                formattingDialog.exec()

    @pyqtSlot()
    def __configureBlack(self):
        """
        Private slot to enter the parameters for formatting the project sources with
        'Black'.
        """
        from eric7.CodeFormatting.BlackConfigurationDialog import (
            BlackConfigurationDialog,
        )

        dlg = BlackConfigurationDialog(
            withProject=True, onlyProject=True, parent=self.ui
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.getConfiguration(saveToProject=True)
            # The data is saved to the project as a side effect.

    def __performImportSortingWithIsort(self, action):
        """
        Private method to format the project sources import statements using the
        'isort' tool.

        Following actions are supported.
        <ul>
        <li>IsortFormattingAction.Format - the imports reformatting is performed</li>
        <li>IsortFormattingAction.Check - a check is performed, if imports formatting
            is necessary</li>
        <li>IsortFormattingAction.Diff - a unified diff of potential imports formatting
            changes is generated</li>
        </ul>

        @param action formatting operation to be performed
        @type IsortFormattingAction
        """
        from eric7.CodeFormatting.IsortConfigurationDialog import (
            IsortConfigurationDialog,
        )
        from eric7.CodeFormatting.IsortFormattingDialog import IsortFormattingDialog

        if ericApp().getObject("ViewManager").checkAllDirty():
            dlg = IsortConfigurationDialog(withProject=True, parent=self.ui)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                config = dlg.getConfiguration(saveToProject=True)

                isortDialog = IsortFormattingDialog(
                    config,
                    self.getProjectFiles("SOURCES", normalized=True),
                    project=self,
                    action=action,
                    parent=self.ui,
                )
                isortDialog.exec()

    @pyqtSlot()
    def __configureIsort(self):
        """
        Private slot to enter the parameters for formatting the import statements of the
        project sources with 'isort'.
        """
        from eric7.CodeFormatting.IsortConfigurationDialog import (
            IsortConfigurationDialog,
        )

        dlg = IsortConfigurationDialog(
            withProject=True, onlyProject=True, parent=self.ui
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            dlg.getConfiguration(saveToProject=True)
            # The data is saved to the project as a side effect.

    #########################################################################
    ## Below are methods implementing the 'Embedded Environment' support
    #########################################################################

    def __showContextMenuEnvironment(self):
        """
        Private slot called before the 'Embedded Environment' menu is shown.
        """
        self.upgradeVenvAct.setEnabled(bool(self.__findEmbeddedEnvironment()))

        self.showMenu.emit("Environment", self.environmentMenu)

    def __findEmbeddedEnvironment(self):
        """
        Private method to find the path of the embedded virtual environment.

        @return path of the embedded virtual environment (empty if not found)
        @rtype str
        """
        ppath = self.getProjectPath()
        if FileSystemUtilities.isRemoteFileName(ppath):
            # check for some common names
            for venvPathName in (".venv", "venv", ".env", "env"):
                venvPath = self.__remotefsInterface.join(ppath, venvPathName)
                if self.__remotefsInterface.isdir(venvPath):
                    return venvPath
        else:
            if ppath and os.path.exists(ppath):
                with os.scandir(self.getProjectPath()) as ppathDirEntriesIterator:
                    for dirEntry in ppathDirEntriesIterator:
                        # potential venv directory; check for 'pyvenv.cfg'
                        if dirEntry.is_dir() and os.path.exists(
                            os.path.join(dirEntry.path, "pyvenv.cfg")
                        ):
                            return dirEntry.path

                # check for some common names in case 'pyvenv.cfg' is missing
                for venvPathName in (".venv", "venv", ".env", "env"):
                    venvPath = os.path.join(ppath, venvPathName)
                    if os.path.isdir(venvPath):
                        return venvPath

        return ""

    def __setEmbeddedEnvironmentProjectConfig(self, value):
        """
        Private method to set the embedded environment project configuration.

        @param value flag indicating an embedded environment
        @type bool
        """
        if value != self.__pdata["EMBEDDED_VENV"]:
            self.__pdata["EMBEDDED_VENV"] = value
            self.setDirty(True)

    def __initVenvConfiguration(self):
        """
        Private method to initialize the environment configuration.
        """
        self.__venvConfiguration = {
            "name": "embedded environment",
            "interpreter": "",
            "exec_path": "",
            "system_site_packages": False,
        }

    def __createEmbeddedEnvironment(self, upgrade=False, force=False):
        """
        Private method to create the embedded virtual environment.

        @param upgrade flag indicating an upgrade operation (defaults to False)
        @type bool (optional)
        @param force flag indicating to force the creation (defaults to False)
        @type bool (optional)
        """
        from eric7.VirtualEnv.VirtualenvExecDialog import VirtualenvExecDialog

        from .ProjectVenvCreationParametersDialog import (
            ProjectVenvCreationParametersDialog,
        )

        environmentPath = self.__findEmbeddedEnvironment()
        if force or upgrade or not environmentPath:
            dlg = ProjectVenvCreationParametersDialog(
                withSystemSitePackages=self.__venvConfiguration["system_site_packages"],
                parent=self.ui,
            )
            if dlg.exec() != QDialog.DialogCode.Accepted:
                # user canceled the environment creation
                self.__setEmbeddedEnvironmentProjectConfig(False)
                return

            pythonPath, withSystemSitePackages = dlg.getData()
            configuration = {
                "envType": "pyvenv",
                "targetDirectory": os.path.join(self.getProjectPath(), ".venv"),
                "openTarget": False,
                "createLog": True,
                "createScript": True,
                "logicalName": self.__venvConfiguration["name"],
                "pythonExe": pythonPath,
            }

            args = []
            if upgrade:
                args.append("--upgrade")
            else:
                if os.path.exists(os.path.join(self.getProjectPath(), ".venv")):
                    args.append("--clear")
            if withSystemSitePackages:
                args.append("--system-site-packages")
            args.append(configuration["targetDirectory"])
            dia = VirtualenvExecDialog(configuration, None, parent=self.ui)
            dia.show()
            dia.start(args)
            dia.exec()

            self.__venvConfiguration["system_site_packages"] = withSystemSitePackages

            self.__configureEnvironment()
            if not self.__venvConfiguration["interpreter"]:
                # user canceled the environment creation, delete the created directory
                shutil.rmtree(configuration["targetDirectory"], ignore_errors=True)
                self.__setEmbeddedEnvironmentProjectConfig(False)
                return

            if upgrade and not withSystemSitePackages:
                # re-install the project into the upgraded environment
                # Note: seems to fail on some systems with access to system
                #       site-packages
                self.__installProjectIntoEnvironment()

        if environmentPath and not self.__venvConfiguration["interpreter"].startswith(
            environmentPath
        ):
            self.__configureEnvironment(environmentPath)

    @pyqtSlot()
    def __configureEnvironment(self, environmentPath=""):
        """
        Private slot to configure the embedded environment.

        @param environmentPath path of the virtual environment (defaults to "")
        @type str (optional)
        """
        from .ProjectVenvConfigurationDialog import ProjectVenvConfigurationDialog

        if not environmentPath:
            environmentPath = self.__findEmbeddedEnvironment()
            if not environmentPath:
                environmentPath = os.path.join(self.getProjectPath(), ".venv")

        dlg = ProjectVenvConfigurationDialog(
            self.__venvConfiguration["name"],
            environmentPath,
            self.__venvConfiguration["interpreter"],
            self.__venvConfiguration["exec_path"],
            parent=self.ui,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            (
                self.__venvConfiguration["interpreter"],
                self.__venvConfiguration["exec_path"],
            ) = dlg.getData()
            self.__saveEnvironmentConfiguration()
            self.__setEmbeddedEnvironmentProjectConfig(True)
        elif not self.__venvConfiguration["interpreter"]:
            self.__setEmbeddedEnvironmentProjectConfig(False)

    def __installProjectIntoEnvironment(self):
        """
        Private method to install the project into the embedded environment in
        development mode.
        """
        pip = ericApp().getObject("Pip")
        pip.installEditableProject(self.getProjectInterpreter(), self.getProjectPath())

    def __saveEnvironmentConfiguration(self):
        """
        Private method to save the embedded environment configuration.
        """
        with contextlib.suppress(OSError), open(
            os.path.join(self.getProjectManagementDir(), "venv_config.json"), "w"
        ) as f:
            json.dump(self.__venvConfiguration, f, indent=2)

    def __loadEnvironmentConfiguration(self):
        """
        Private method to load the embedded environment configuration.
        """
        try:
            with open(
                os.path.join(self.getProjectManagementDir(), "venv_config.json"), "r"
            ) as f:
                self.__venvConfiguration = json.load(f)

            if not os.path.isfile(
                self.__venvConfiguration["interpreter"]
            ) or not os.access(self.__venvConfiguration["interpreter"], os.X_OK):
                self.__venvConfiguration["interpreter"] = ""
                upgrade = EricMessageBox.yesNo(
                    None,
                    self.tr("Interpreter Missing"),
                    self.tr(
                        "The configured interpreter of the embedded environment does"
                        " not exist anymore. Shall the environment be upgraded?"
                    ),
                    yesDefault=True,
                )
                if upgrade:
                    self.__createEmbeddedEnvironment(upgrade=True)
        except (OSError, json.JSONDecodeError):
            # the configuration file does not exist or is invalid JSON
            self.__initVenvConfiguration()

    #########################################################################
    ## Below are methods implementing some tool functionality
    #########################################################################

    @pyqtSlot()
    def __clearByteCodeCaches(self, directory=None):
        """
        Private method to recursively clear the byte code caches of a given directory.

        Note: The byte code cache directories are named '__pycache__'.

        @param directory directory name to clear byte code caches from (defaults to
            None)
        @type str (optional)
        """
        if directory is None:
            # When directory is 'None', we were called by the QAction.
            if self.ppath:
                directory = self.ppath
            else:
                return

        # step 1: delete the __pycache__ directory
        cacheDir = os.path.join(directory, "__pycache__")
        if os.path.exists(cacheDir):
            shutil.rmtree(cacheDir, ignore_errors=True)

        # step 2: descent into subdirectories
        with os.scandir(directory) as dirEntriesIterator:
            for dirEntry in dirEntriesIterator:
                if dirEntry.is_dir():
                    self.__clearByteCodeCaches(dirEntry.path)

    #############################################################################
    ## Below are methods implementing the support for 'eric-ide server projects
    #############################################################################

    @pyqtSlot(bool)
    def remoteConnectionChanged(self, connected):
        """
        Public slot to handle a change of the 'eric-ide' server connection state.

        @param connected flag indicating the connection state
        @type bool
        """
        self.openRemoteAct.setEnabled(connected)
        self.saveasRemoteAct.setEnabled(
            connected
            and self.opened
            and FileSystemUtilities.isRemoteFileName(self.pfile)
        )
        if not connected and FileSystemUtilities.isRemoteFileName(self.ppath):
            self.closeProject(noSave=True)

    @pyqtSlot()
    def remoteConnectionAboutToDisconnect(self):
        """
        Public slot to handle the imminent disconnect from an 'eric-ide' server.
        """
        if FileSystemUtilities.isRemoteFileName(self.ppath):
            self.closeProject()

    @pyqtSlot()
    def __openRemoteProject(self):
        """
        Private slot to open a project of an 'eric-ide' server.
        """
        fn = EricServerFileDialog.getOpenFileName(
            self.parent(),
            self.tr("Open Remote Project"),
            "",
            self.tr("Project Files (*.epj)"),
        )
        if fn:
            self.openProject(fn=fn)

    @pyqtSlot()
    def __saveRemoteProjectAs(self):
        """
        Private slot to save the current remote project to different remote file.
        """
        defaultFilter = self.tr("Project Files (*.epj)")
        defaultPath = self.ppath if self.ppath else ""
        fn, selectedFilter = EricServerFileDialog.getSaveFileNameAndFilter(
            self.parent(),
            self.tr("Save Remote Project"),
            defaultPath,
            self.tr("Project Files (*.epj)"),
            defaultFilter,
        )

        if fn:
            fname, ext = self.__remotefsInterface.splitext(fn)
            if not ext:
                ex = selectedFilter.split("(*")[1].split(")")[0]
                if ex:
                    fn = f"{fname}{ex}"
            if self.__remotefsInterface.exists(fn):
                res = EricMessageBox.yesNo(
                    self.ui,
                    self.tr("Save Remote Project"),
                    self.tr(
                        """<p>The file <b>{0}</b> already exists."""
                        """ Overwrite it?</p>"""
                    ).format(fn),
                    icon=EricMessageBox.Warning,
                )
                if not res:
                    return

            ok = self.__writeProject(fn)

            if ok:
                # create management directory if not present
                self.createProjectManagementDir()

                # now save the tasks
                self.writeTasks()

            self.sessActGrp.setEnabled(ok)
            self.menuSessionAct.setEnabled(ok)
            self.projectClosedHooks.emit()
            self.projectClosed.emit(False)
            self.projectOpenedHooks.emit()
            self.projectOpened.emit()


#
# eflag: noqa = M601
