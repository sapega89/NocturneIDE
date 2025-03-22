# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the project browser part of the eric UI.
"""

import contextlib

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon
from PyQt6.QtWidgets import QToolButton

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricLed import EricClickableLed
from eric7.EricWidgets.EricTabWidget import EricTabWidget

from .ProjectBrowserRepositoryItem import ProjectBrowserRepositoryItem
from .ProjectFormsBrowser import ProjectFormsBrowser
from .ProjectOthersBrowser import ProjectOthersBrowser
from .ProjectResourcesBrowser import ProjectResourcesBrowser
from .ProjectSourcesBrowser import ProjectSourcesBrowser
from .ProjectTranslationsBrowser import ProjectTranslationsBrowser


class ProjectBrowser(EricTabWidget):
    """
    Class implementing the project browser part of the eric UI.

    It generates a widget with up to seven tabs. The individual tabs contain
    the project sources browser, the project forms browser,
    the project resources browser, the project translations browser,
    the project interfaces (IDL) browser and a browser for stuff,
    that doesn't fit these categories. Optionally it contains an additional
    tab with the file system browser.

    Note: The following signals are defined here to proxy the individual browser
    signals.

    @signal appendStderr(str) emitted after something was received from
        a QProcess on stderr
    @signal appendStdout(str) emitted after something was received from
        a QProcess on stdout
    @signal binaryFile(filename) emitted to open a file as binary (str)
    @signal closeSourceWindow(str) emitted to close a source file
    @signal designerFile(filename) emitted to open a Qt-Designer file (str)
    @signal linguistFile(filename) emitted to open a Qt-Linguist (*.ts)
        file (str)
    @signal pdfFile(filename) emitted to open a PDF file (str)
    @signal pixmapEditFile(filename) emitted to edit a pixmap file (str)
    @signal pixmapFile(filename) emitted to open a pixmap file (str)
    @signal preferencesChanged() emitted when the preferences have been changed
    @signal sourceFile(filename) emitted to open a Python file at a line (str)
    @signal sourceFile(filename, lineno) emitted to open a Python file at a
        line (str, int)
    @signal sourceFile(filename, lineno, type) emitted to open a Python file
        at a line giving an explicit file type (str, int, str)
    @signal sourceFile(filename, linenos) emitted to open a Python file giving
        a list of lines(str, list)
    @signal sourceFile(filename, lineno, col_offset) emitted to open a Python file at a
        line and column (str, int, int)
    @signal svgFile(filename) emitted to open a SVG file (str)
    @signal testFile(filename) emitted to open a Python file for a
        unit test (str)
    @signal trpreview(filenames) emitted to preview Qt-Linguist (*.qm)
        files (list of str)
    @signal trpreview(filenames, ignore) emitted to preview Qt-Linguist (*.qm)
        files indicating whether non-existent files shall be ignored
        (list of str, bool)
    @signal uipreview(str) emitted to preview a forms file
    @signal umlFile(filename) emitted to open an eric UML file (str)
    @signal processChangedProjectFiles() emitted to indicate, that changed project files
        should be processed
    """

    appendStderr = pyqtSignal(str)
    appendStdout = pyqtSignal(str)
    binaryFile = pyqtSignal(str)
    closeSourceWindow = pyqtSignal(str)
    designerFile = pyqtSignal(str)
    linguistFile = pyqtSignal(str)
    pdfFile = pyqtSignal(str)
    pixmapEditFile = pyqtSignal(str)
    pixmapFile = pyqtSignal(str)
    preferencesChanged = pyqtSignal()
    sourceFile = pyqtSignal(
        (str,), (str, int), (str, int, int), (str, list), (str, int, str)
    )
    svgFile = pyqtSignal(str)
    testFile = pyqtSignal(str)
    trpreview = pyqtSignal((list,), (list, bool))
    uipreview = pyqtSignal(str)
    umlFile = pyqtSignal(str)
    processChangedProjectFiles = pyqtSignal()

    def __init__(self, project, parent=None):
        """
        Constructor

        @param project reference to the project object
        @type Project
        @param parent parent widget
        @type QWidget
        """
        EricTabWidget.__init__(self, parent)
        self.project = project

        self.setWindowIcon(EricPixmapCache.getIcon("eric"))

        self.setUsesScrollButtons(True)

        self.vcsStatusColorNames = {
            "A": "VcsAdded",
            "M": "VcsModified",
            "O": "VcsRemoved",
            "R": "VcsReplaced",
            "U": "VcsUpdate",
            "Z": "VcsConflict",
        }
        self.vcsStatusText = {
            " ": self.tr("up to date"),
            "A": self.tr("files added"),
            "M": self.tr("local modifications"),
            "O": self.tr("files removed"),
            "R": self.tr("files replaced"),
            "U": self.tr("update required"),
            "Z": self.tr("conflict"),
        }
        self.vcsStatusIndicator = EricClickableLed(self)
        self.vcsStatusIndicator.clicked.connect(self.__vcsStatusIndicatorClicked)
        self.setCornerWidget(self.vcsStatusIndicator, Qt.Corner.TopLeftCorner)
        self.vcsCheckStatusButton = QToolButton(self)
        self.vcsCheckStatusButton.setIcon(EricPixmapCache.getIcon("reload"))
        self.vcsCheckStatusButton.setToolTip(
            self.tr("Press to check the current VCS status.")
        )
        self.vcsCheckStatusButton.clicked.connect(self.project.checkVCSStatus)
        self.setCornerWidget(self.vcsCheckStatusButton, Qt.Corner.TopRightCorner)
        self.__vcsStateChanged(" ")

        self.__currentBrowsersList = []
        self.__browserRepository = {}
        self.__fileFilterMapping = {}  # redundant data store for speed reasons

        self.project.getModel().setProjectBrowserReference(self)

        # create all the individual browsers
        for browserClass in (
            ProjectSourcesBrowser,
            ProjectFormsBrowser,
            ProjectResourcesBrowser,
            ProjectTranslationsBrowser,
            ProjectOthersBrowser,
        ):
            browserClass(self.project, self)

        # add signal connection to ourselves
        self.project.projectOpened.connect(self.__projectOpened)
        self.project.projectClosed.connect(self.__projectClosed)
        self.project.newProject.connect(self.__newProject)
        self.project.projectPropertiesChanged.connect(self.__projectPropertiesChanged)
        self.currentChanged.connect(self.__currentChanged)
        self.project.getModel().vcsStateChanged.connect(self.__vcsStateChanged)

        self.__projectPropertiesChanged()
        self.setCurrentIndex(0)

    def addTypedProjectBrowser(self, browserType, projectBrowserItem):
        """
        Public method to add a project browser type to the browser repository.

        @param browserType type of the project browser
        @type str
        @param projectBrowserItem data structure containing the type specific data
        @type ProjectBrowserRepositoryItem
        @exception TypeError raised to signal a wrong type for the project browser item
        """
        if not isinstance(projectBrowserItem, ProjectBrowserRepositoryItem):
            raise TypeError(
                "'projectBrowserItem' must be an instance of"
                " 'ProjectBrowserRepositoryItem'."
            )

        if browserType in self.__browserRepository:
            EricMessageBox.critical(
                self.ui,
                self.tr("Add Project Browser Type"),
                self.tr(
                    "<p>The project browser type <b>{0}</b> has already been added."
                    " This attempt will be ignored.</p>"
                ),
            )
        else:
            self.__browserRepository[browserType] = projectBrowserItem
            self.__fileFilterMapping[projectBrowserItem.fileCategory] = (
                projectBrowserItem.fileFilter
            )

        self.__setBrowsersAvailable(self.__currentBrowsersList)

    def removeTypedProjectBrowser(self, browserType):
        """
        Public method to remove a browser type from the browsers repository.

        Note: If the browser type is not contained in the repository, the request to
        remove it will be ignored silently.

        @param browserType project browser type
        @type str
        """
        with contextlib.suppress(KeyError):
            browserIndex = self.indexOf(self.getProjectBrowser(browserType))
            if browserIndex >= 0:
                self.removeTab(browserIndex)

            del self.__fileFilterMapping[
                self.__browserRepository[browserType].fileCategory
            ]
            del self.__browserRepository[browserType]

        self.__setBrowsersAvailable(self.__currentBrowsersList)

    def getProjectBrowsers(self):
        """
        Public method to get references to the individual project browsers.

        @return list of references to project browsers
        @rtype list of ProjectBaseBrowser
        """
        return [itm.projectBrowser for itm in self.__browserRepository.values()]

    def getProjectBrowser(self, browserType):
        """
        Public method to get a reference to the project browser of given type.

        @param browserType type of the requested project browser
        @type str
        @return reference to the requested browser or None
        @rtype ProjectBaseBrowser or None
        """
        try:
            return self.__browserRepository[browserType].projectBrowser
        except KeyError:
            return None

    def getProjectBrowserNames(self):
        """
        Public method to get the types of the various project browsers.

        @return list of project browser types
        @rtype list of str
        """
        return list(self.__browserRepository)

    def getProjectBrowserUserStrings(self):
        """
        Public method to get a dictionary of defined project browser user strings.

        @return dictionary of defined project browser user strings
        @rtype dict
        """
        return {
            key: item.projectBrowserUserString
            for key, item in self.__browserRepository.items()
        }

    def getProjectBrowserIcon(self, browserType):
        """
        Public method to get the icon for a project browser.

        @param browserType type of the project browser
        @type str
        @return icon for the project browser
        @rtype QIcon
        """
        try:
            return self.__browserRepository[browserType].getIcon()
        except KeyError:
            return QIcon()

    def getProjectBrowserType(self, fileCategory):
        """
        Public method to get the project browser type for a file category.

        @param fileCategory file category
        @type str
        @return project browser type
        @rtype str
        """
        for browserType, browserItem in self.__browserRepository.items():
            if browserItem.fileCategory == fileCategory:
                return browserType

        return ""

    def getProjectBrowserFilter(self, fileCategory):
        """
        Public method to get the project browser file filter for a file category.

        @param fileCategory file category
        @type str
        @return project browser file filter
        @rtype str
        """
        with contextlib.suppress(KeyError):
            return self.__fileFilterMapping[fileCategory]

        return ""

    def __setBrowsersAvailable(self, browsersList):
        """
        Private method to add selected browsers to the project browser.

        @param browsersList list of project browsers to be shown
        @type list of str
        """
        # step 1: remove all tabs
        while self.count() > 0:
            self.removeTab(0)

        # step 2: add browsers
        for browser in sorted(
            [b for b in browsersList if b in self.__browserRepository],
            key=lambda x: self.__browserRepository[x].priority,
            reverse=True,
        ):
            index = self.addTab(
                self.__browserRepository[browser].projectBrowser,
                self.__browserRepository[browser].getIcon(),
                "",
            )
            self.setTabToolTip(
                index,
                self.__browserRepository[browser].projectBrowser.windowTitle(),
            )

    def __currentChanged(self, index):
        """
        Private slot to handle the currentChanged(int) signal.

        @param index index of the tab
        @type int
        """
        if index > -1:
            browser = self.widget(index)
            if browser is not None:
                browser.layoutDisplay()

    def __projectOpened(self):
        """
        Private slot to handle the projectOpened signal.
        """
        self.__projectPropertiesChanged()
        self.setCurrentIndex(0)
        self.__vcsStateChanged(" ")
        self.vcsStatusIndicator.setVisible(self.project.isVcsControlled())
        self.vcsCheckStatusButton.setVisible(self.project.isVcsControlled())

    def __projectClosed(self):
        """
        Private slot to handle the projectClosed signal.
        """
        self.__projectPropertiesChanged()
        self.setCurrentIndex(0)
        self.__setSourcesIcon()
        self.__vcsStateChanged(" ")
        self.vcsStatusIndicator.setVisible(False)
        self.vcsCheckStatusButton.setVisible(False)

    def __newProject(self):
        """
        Private slot to handle the newProject signal.
        """
        self.setCurrentIndex(0)
        self.__projectPropertiesChanged()

    def __projectPropertiesChanged(self):
        """
        Private slot to handle the projectPropertiesChanged signal.
        """
        browsersList = (
            Preferences.getProjectBrowsers(self.project.getProjectType())
            if self.project.isOpen()
            else list(self.__browserRepository)
        )
        browsersList = [b for b in browsersList if b in self.__browserRepository]

        if browsersList != self.__currentBrowsersList:
            self.__currentBrowsersList = browsersList[:]
            self.__setBrowsersAvailable(browsersList)

        endIndex = self.count()
        for index in range(endIndex):
            self.setTabEnabled(index, self.project.isOpen())

        self.__setSourcesIcon()

    def __setSourcesIcon(self):
        """
        Private method to set the right icon for the sources browser tab.
        """
        self.setTabIcon(
            self.indexOf(self.getProjectBrowser("sources")),
            self.getProjectBrowserIcon("sources"),
        )

    def handleEditorChanged(self, fn):
        """
        Public slot to handle the editorChanged signal.

        @param fn filename of the changed file
        @type str
        """
        if Preferences.getProject("FollowEditor"):
            for fileCategory in (
                cat
                for cat in self.project.getFileCategories()
                if cat not in ("TRANSLATIONS", "OTHERS")
            ):
                if self.project.isProjectCategory(fn, fileCategory):
                    self.getProjectBrowser(fileCategory.lower()).selectFile(fn)
                    break

    def handleEditorLineChanged(self, fn, lineno):
        """
        Public slot to handle the editorLineChanged signal.

        @param fn filename of the changed file
        @type str
        @param lineno one based line number of the item
        @type int
        """
        if (
            Preferences.getProject("FollowEditor")
            and Preferences.getProject("FollowCursorLine")
            and self.project.isProjectCategory(fn, "SOURCES")
        ):
            self.getProjectBrowser("sources").selectFileLine(fn, lineno)

    def handlePreferencesChanged(self):
        """
        Public slot used to handle the preferencesChanged signal.
        """
        self.__projectPropertiesChanged()
        self.__vcsStateChanged(self.currentVcsStatus)

        self.preferencesChanged.emit()  # propagate the signal to the browsers

    def __vcsStateChanged(self, state):
        """
        Private slot to handle a change in the vcs state.

        @param state new vcs state
        @type str
        """
        self.vcsStatusIndicator.setVisible(self.project.isVcsControlled())
        self.vcsCheckStatusButton.setVisible(self.project.isVcsControlled())

        self.currentVcsStatus = state
        if state == " " or state not in self.vcsStatusColorNames:
            self.vcsStatusIndicator.setColor(QColor(Qt.GlobalColor.lightGray))
        else:
            self.vcsStatusIndicator.setColor(
                Preferences.getProjectBrowserColour(self.vcsStatusColorNames[state])
            )
        if state not in self.vcsStatusText:
            self.vcsStatusIndicator.setToolTip(self.tr("unknown status"))
        else:
            self.vcsStatusIndicator.setToolTip(self.vcsStatusText[state])

    def __vcsStatusIndicatorClicked(self, _pos):
        """
        Private slot to react upon clicks on the VCS indicator LED.

        @param _pos position of the click (unused)
        @type QPoint
        """
        vcs = self.project.getVcs()
        if vcs:
            if self.currentVcsStatus == " ":
                # call log browser dialog
                vcs.vcsLogBrowser(self.project.getProjectPath())
            else:
                # call status dialog
                vcs.vcsStatus(self.project.getProjectPath())
