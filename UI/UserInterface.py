# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the main user interface.
"""

import contextlib
import datetime
import enum
import functools
import getpass
import glob
import importlib
import json
import logging
import os
import pathlib
import shutil
import sys

import psutil
from PyQt6 import sip
from PyQt6.Qsci import QSCINTILLA_VERSION_STR, QsciScintilla
from PyQt6.QtCore import (
    PYQT_VERSION_STR,
    QDate,
    QProcess,
    QSize,
    Qt,
    QThread,
    QTimer,
    QUrl,
    QUrlQuery,
    QUuid,
    pyqtSignal,
    pyqtSlot,
    qVersion,
)
from PyQt6.QtGui import (
    QAction,
    QDesktopServices,
    QGuiApplication,
    QKeySequence,
    QSessionManager,
)
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkProxyFactory
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDockWidget,
    QLabel,
    QMenu,
    QSizePolicy,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWhatsThis,
    QWidget, QMessageBox,
)

from eric7 import EricUtilities, Globals, Preferences, Testing, Utilities
from eric7.__version__ import Version, VersionOnly
from eric7.CondaInterface.Conda import Conda
from eric7.Debugger.DebugServer import DebugServer
from eric7.Debugger.DebugUI import DebugUI
from eric7.EricCore import EricFileSystemWatcher, EricPreferences
from eric7.EricCore.EricStdRedirector import EricStdRedirector
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction, createActionGroup
from eric7.EricNetwork.EricNetworkIcon import EricNetworkIcon
from eric7.EricNetwork.EricNetworkProxyFactory import (
    EricNetworkProxyFactory,
    proxyAuthenticationRequired,
)
from eric7.EricWidgets import EricErrorMessage, EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricClickableLabel import EricClickableLabel
from eric7.EricWidgets.EricListSelectionDialog import EricListSelectionDialog
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.EricWidgets.EricSingleApplication import EricSingleApplicationServer
from eric7.EricWidgets.EricToolBarManager import EricToolBarManager
from eric7.EricWidgets.EricZoomWidget import EricZoomWidget
from eric7.Globals import getConfig
from eric7.MultiProject.MultiProject import MultiProject
from eric7.PipInterface.Pip import Pip
from eric7.PluginManager.PluginManager import PluginManager
from eric7.PluginManager.PluginRepositoryDialog import PluginRepositoryDownloadCleanup
from eric7.Preferences import Shortcuts
from eric7.Project.Project import Project
from eric7.QScintilla.SpellChecker import SpellChecker
from eric7.RemoteServerInterface.EricServerInterface import EricServerInterface
from eric7.Sessions.SessionFile import SessionFile
from eric7.SystemUtilities import (
    DesktopUtilities,
    FileSystemUtilities,
    OSUtilities,
    PythonUtilities,
    QtUtilities,
)
from eric7.Tasks.TasksFile import TasksFile
from eric7.Testing.TestingWidget import clearSavedHistories
from eric7.Utilities.BackgroundService import BackgroundService
from eric7.VirtualEnv.VirtualenvManager import VirtualenvManager

from .Info import BugAddress, FeatureAddress, Program
from .NotificationWidget import NotificationTypes
from .ai_core import ask_ai
from .main import AIAssistantPanel

try:
    from eric7.EricNetwork.EricSslErrorHandler import (
        EricSslErrorHandler,
        EricSslErrorState,
    )

    SSL_AVAILABLE = True
except ImportError:
    SSL_AVAILABLE = False

sys.path.append(os.path.abspath(os.path.dirname(__file__)))


class UserInterfaceSide(enum.Enum):
    """
    Class defining the supported sides of the user interface.
    """

    Left = 1
    Bottom = 2
    Right = 3


class UserInterface(EricMainWindow):
    """
    Class implementing the main user interface.

    @signal appendStderr(str) emitted to write data to stderr logger
    @signal appendStdout(str) emitted to write data to stdout logger
    @signal preferencesChanged() emitted after the preferences were changed
    @signal reloadAPIs() emitted to reload the api information
    @signal showMenu(str, QMenu) emitted when a menu is about to be shown. The
        name of the menu and a reference to the menu are given.
    @signal mainPasswordChanged(str, str) emitted after the main
        password has been changed with the old and the new password
    @signal onlineStateChanged(online) emitted to indicate a change of the
        network state
    """

    appendStderr = pyqtSignal(str)
    appendStdout = pyqtSignal(str)
    preferencesChanged = pyqtSignal()
    reloadAPIs = pyqtSignal()
    showMenu = pyqtSignal(str, QMenu)
    mainPasswordChanged = pyqtSignal(str, str)
    onlineStateChanged = pyqtSignal(bool)

    maxFilePathLen = 100
    maxMenuFilePathLen = 75

    # NOTE: change this to 'True' for official releases
    ReleaseMode = True

    ErrorLogFileName = "eric7_error.log"

    def analyze_code(self):
        """
        Ищет QsciScintilla редактор и анализирует код.
        """
        try:
            splitter = self.centralWidget()
            editor = splitter.findChild(QsciScintilla)

            if editor:
                code = editor.text()  # QsciScintilla использует .text()
                response = ask_ai(code)
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.information(self, "AI Code Analysis", response)
            else:
                QMessageBox.warning(self, "No Code", "Редактор не найден.")
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Error", f"Error accessing editor: {str(e)}")

    def __init__(
        self,
        app,
        locale,
        splash,
        plugin,
        disabledPlugins,
        noOpenAtStartup,
        noCrashOpenAtStartup,
        disableCrashSession,
        restartArguments,
        originalPathString,
    ):
        """
        Constructor

        @param app reference to the application object
        @type EricApplication
        @param locale locale to be used by the UI
        @type str
        @param splash reference to the splashscreen
        @type UI.SplashScreen.SplashScreen
        @param plugin filename of a plug-in to be loaded (used for plugin
            development)
        @type str
        @param disabledPlugins list of plug-ins that have been disabled via
            the command line parameters '--disable-plugin='
        @type list of str
        @param noOpenAtStartup flag indicating that the open at startup option
            should not be executed
        @type bool
        @param noCrashOpenAtStartup flag indicating to ignore any crash session
            file found at statup
        @type bool
        @param disableCrashSession flag indicating to disable the crash session
            support
        @type bool
        @param restartArguments list of command line parameters to be used for
            a restart
        @type list of str
        @param originalPathString original PATH environment variable
        @type str
        """
        super().__init__()

        self.__restartArgs = restartArguments[:]

        self.setStyle(
            styleName=Preferences.getUI("Style"),
            styleSheetFile=Preferences.getUI("StyleSheet"),
            itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
        )

        self.maxEditorPathLen = Preferences.getUI("CaptionFilenameLength")
        self.locale = locale
        self.__openAtStartup = not noOpenAtStartup
        self.__noCrashOpenAtStartup = noCrashOpenAtStartup
        self.__disableCrashSession = disableCrashSession
        self.__disabledPlugins = disabledPlugins[:]

        self.__originalPathString = originalPathString

        if app.usesSmallScreen():
            # override settings for small screens
            Preferences.setUI("LayoutType", "Sidebars")
            Preferences.setUI("CombinedLeftRightSidebar", True)
            Preferences.setUI("IconBarSize", "sm")

        self.__layoutType = Preferences.getUI("LayoutType")

        self.passiveMode = Preferences.getDebugger("PassiveDbgEnabled")

        g = Preferences.getGeometry("MainGeometry")
        if g.isEmpty():
            s = QSize(1280, 720)
            self.resize(s)
        else:
            self.restoreGeometry(g)
        self.__startup = True

        if EricPreferences.getNetworkProxy("UseSystemProxy"):
            QNetworkProxyFactory.setUseSystemConfiguration(True)
        else:
            self.__proxyFactory = EricNetworkProxyFactory()
            QNetworkProxyFactory.setApplicationProxyFactory(self.__proxyFactory)
            QNetworkProxyFactory.setUseSystemConfiguration(False)

        self.capProject = ""
        self.capEditor = ""
        self.captionShowsFilename = Preferences.getUI("CaptionShowsFilename")

        QApplication.setWindowIcon(EricPixmapCache.getIcon("eric"))
        self.setWindowIcon(EricPixmapCache.getIcon("eric"))
        self.__setWindowCaption()

        # load the view profiles
        self.profiles = Preferences.getUI("ViewProfiles")

        splash.showMessage(self.tr("Initializing Basic Services..."))
        logging.getLogger(__name__).debug("Initializing Basic Services...")

        # Redirect sys.stdout and/or sys.stderr if those are None
        if sys.stdout is None or UserInterface.ReleaseMode:
            self.__stdout = EricStdRedirector(False, self)
            self.__stdout.stdoutString.connect(self.appendToStdout)
            sys.stdout = self.__stdout
        if sys.stderr is None or UserInterface.ReleaseMode:
            self.__stderr = EricStdRedirector(True, self)
            self.__stderr.stderrString.connect(self.appendToStderr)
            sys.stderr = self.__stderr

        # create the remote server interface
        logging.getLogger(__name__).debug("Creating 'eric-ide' Server Interface...")
        self.__ericServerInterface = EricServerInterface(self)
        # register it early because it is needed very soon
        ericApp().registerObject("EricServer", self.__ericServerInterface)

        # Generate the conda interface
        logging.getLogger(__name__).debug("Creating Conda Interface...")
        self.condaInterface = Conda(self)
        # register it early because it is needed very soon
        ericApp().registerObject("Conda", self.condaInterface)

        # Generate the pip interface
        logging.getLogger(__name__).debug("Creating Pip Interface...")
        self.pipInterface = Pip(self)
        # register it early because it is needed very soon
        ericApp().registerObject("Pip", self.pipInterface)

        # Generate the virtual environment manager
        logging.getLogger(__name__).debug("Creating Virtual Environments Manager...")
        self.virtualenvManager = VirtualenvManager(self)
        # register it early because it is needed very soon
        ericApp().registerObject("VirtualEnvManager", self.virtualenvManager)

        # Generate an empty project object
        logging.getLogger(__name__).debug("Creating Project Manager...")
        self.project = Project(self, remoteServer=self.__ericServerInterface)
        ericApp().registerObject("Project", self.project)

        # Generate the multi project object
        logging.getLogger(__name__).debug("Creating Multi-Project Manager...")
        self.multiProject = MultiProject(self.project, self)

        # Generate the debug server object
        logging.getLogger(__name__).debug("Creating Debug Server...")
        self.__debugServer = DebugServer(
            self.__originalPathString, project=self.project, parent=self
        )

        # Create the background service object
        logging.getLogger(__name__).debug("Creating Background Service...")
        self.backgroundService = BackgroundService(self)

        splash.showMessage(self.tr("Initializing Plugin Manager..."))
        logging.getLogger(__name__).debug("Initializing Plugin Manager...")

        # Initialize the Plugin Manager (Plugins are initialized later)
        self.pluginManager = PluginManager(
            self, self.__disabledPlugins, develPlugin=plugin
        )

        splash.showMessage(self.tr("Generating Main User Interface..."))
        logging.getLogger(__name__).debug("Generating Main User Interface...")

        self.__webBrowserProcess = None
        self.__webBrowserClient = None
        self.__webBrowserSAName = QUuid.createUuid().toString()[1:-1]

        # set spellchecker defaults
        SpellChecker.setDefaultLanguage(
            Preferences.getEditor("SpellCheckingDefaultLanguage")
        )

        with contextlib.suppress(ImportError, AttributeError):
            from eric7.EricWidgets.EricSpellCheckedTextEdit import (  # noqa: I101
                SpellCheckMixin,
            )

            pwl = SpellChecker.getUserDictionaryPath(isException=False)
            pel = SpellChecker.getUserDictionaryPath(isException=True)
            SpellCheckMixin.setDefaultLanguage(
                Preferences.getEditor("SpellCheckingDefaultLanguage"), pwl, pel
            )

        logging.getLogger(__name__).debug("Creating Application Objects...")
        self.__createObjects()

        # Create the main window now so that we can connect QActions to it.
        logging.getLogger(__name__).debug("Creating Layout...")
        self.__createLayout()
        self.__currentRightWidget = None
        self.__currentBottomWidget = None

        # Generate the debugger part of the ui
        logging.getLogger(__name__).debug("Creating Debugger UI...")
        self.debuggerUI = DebugUI(
            self, self.viewmanager, self.__debugServer, self.debugViewer, self.project
        )
        self.debugViewer.setDebugger(self.debuggerUI)
        self.shell.setDebuggerUI(self.debuggerUI)

        # set a few dialog members for non-modal dialogs created on demand
        self.programsDialog = None
        self.shortcutsDialog = None
        self.__testingWidget = None
        self.findFileNameDialog = None
        self.diffDlg = None
        self.compareDlg = None
        self.findFilesDialog = None
        self.replaceFilesDialog = None
        self.__notification = None
        self.__readingSession = False
        self.__versionsDialog = None
        self.__configurationDialog = None

        # now setup the connections
        splash.showMessage(self.tr("Setting up signal/slot-connections..."))
        logging.getLogger(__name__).debug(
            self.tr("Setting up signal/slot-connections...")
        )

        self.debugViewer.exceptionLogger.sourceFile.connect(
            self.viewmanager.openSourceFile
        )

        self.debugViewer.sourceFile.connect(self.viewmanager.showDebugSource)

        self.taskViewer.displayFile.connect(self.viewmanager.openSourceFile)

        self.projectBrowser.appendStderr.connect(self.appendToStderr)
        self.projectBrowser.appendStdout.connect(self.appendToStdout)
        self.projectBrowser.sourceFile[str].connect(self.viewmanager.openSourceFile)
        self.projectBrowser.sourceFile[str, int].connect(
            self.viewmanager.openSourceFile
        )
        self.projectBrowser.sourceFile[str, list].connect(
            self.viewmanager.openSourceFile
        )
        self.projectBrowser.sourceFile[str, int, str].connect(
            self.viewmanager.openSourceFile
        )
        self.projectBrowser.sourceFile[str, int, int].connect(
            self.viewmanager.openSourceFileLinePos
        )
        self.projectBrowser.closeSourceWindow.connect(self.viewmanager.closeWindow)
        self.projectBrowser.testFile.connect(self.__startTestScript)
        self.projectBrowser.designerFile.connect(self.__designer)
        self.projectBrowser.uipreview.connect(self.__UIPreviewer)
        self.projectBrowser.trpreview[list].connect(self.__TRPreviewer)
        self.projectBrowser.trpreview[list, bool].connect(self.__TRPreviewer)
        self.projectBrowser.linguistFile.connect(self.__linguist)
        self.projectBrowser.pixmapEditFile.connect(self.__editPixmap)
        self.projectBrowser.pixmapFile.connect(self.__showPixmap)
        self.projectBrowser.svgFile.connect(self.__showSvg)
        self.projectBrowser.umlFile.connect(self.__showUml)
        self.projectBrowser.binaryFile.connect(self.__openHexEditor)
        self.projectBrowser.pdfFile.connect(self.__openPdfViewer)

        self.project.sourceFile.connect(self.viewmanager.openSourceFile)
        self.project.designerFile.connect(self.__designer)
        self.project.linguistFile.connect(self.__linguist)
        self.project.projectOpened.connect(self.viewmanager.projectOpened)
        self.project.projectClosed.connect(self.viewmanager.projectClosed)
        self.project.projectFileRenamed.connect(self.viewmanager.projectFileRenamed)
        self.project.lexerAssociationsChanged.connect(
            self.viewmanager.projectLexerAssociationsChanged
        )
        self.project.newProject.connect(self.__newProject)
        self.project.projectOpened.connect(self.__projectOpened)
        self.project.projectOpened.connect(self.__activateProjectBrowser)
        self.project.projectClosed.connect(self.__projectClosed)
        self.project.projectClosed.connect(
            self.backgroundService.preferencesOrProjectChanged
        )
        self.project.projectOpened.connect(self.__writeCrashSession)
        self.project.projectClosed.connect(self.__writeCrashSession)
        self.project.appendStdout.connect(self.appendToStdout)
        self.project.appendStderr.connect(self.appendToStderr)

        self.multiProject.multiProjectOpened.connect(self.__activateMultiProjectBrowser)
        self.multiProject.multiProjectOpened.connect(self.__writeCrashSession)
        self.multiProject.multiProjectClosed.connect(self.__writeCrashSession)

        self.debuggerUI.resetUI.connect(self.viewmanager.handleResetUI)
        self.debuggerUI.resetUI.connect(self.debugViewer.handleResetUI)
        self.debuggerUI.resetUI.connect(self.__debuggingDone)
        self.debuggerUI.debuggingStarted.connect(self.__programChange)
        self.debuggerUI.debuggingStarted.connect(self.__debuggingStarted)
        self.debuggerUI.processChangedProjectFiles.connect(
            self.projectBrowser.processChangedProjectFiles
        )
        self.debuggerUI.processChangedProjectFiles.connect(
            self.project.processChangedProjectFiles
        )

        self.__debugServer.clientDisassembly.connect(
            self.debugViewer.disassemblyViewer.showDisassembly
        )
        self.__debugServer.clientProcessStdout.connect(self.appendToStdout)
        self.__debugServer.clientProcessStderr.connect(self.appendToStderr)
        self.__debugServer.appendStdout.connect(self.appendToStdout)

        self.preferencesChanged.connect(self.viewmanager.preferencesChanged)
        self.reloadAPIs.connect(self.viewmanager.getAPIsManager().reloadAPIs)
        self.preferencesChanged.connect(self.logViewer.preferencesChanged)
        self.appendStdout.connect(self.logViewer.appendToStdout)
        self.appendStderr.connect(self.logViewer.appendToStderr)
        self.preferencesChanged.connect(self.shell.handlePreferencesChanged)
        self.preferencesChanged.connect(self.project.handlePreferencesChanged)
        self.preferencesChanged.connect(self.projectBrowser.handlePreferencesChanged)
        self.preferencesChanged.connect(self.taskViewer.handlePreferencesChanged)
        self.preferencesChanged.connect(self.pluginManager.preferencesChanged)
        self.preferencesChanged.connect(self.__debugServer.preferencesChanged)
        self.preferencesChanged.connect(self.debugViewer.preferencesChanged)
        self.preferencesChanged.connect(
            self.backgroundService.preferencesOrProjectChanged
        )
        self.preferencesChanged.connect(self.__previewer.preferencesChanged)
        self.preferencesChanged.connect(self.__astViewer.preferencesChanged)
        self.preferencesChanged.connect(self.__disViewer.preferencesChanged)

        if self.browser is not None:
            self.browser.sourceFile[str].connect(self.viewmanager.openSourceFile)
            self.browser.sourceFile[str, int].connect(self.viewmanager.openSourceFile)
            self.browser.sourceFile[str, list].connect(self.viewmanager.openSourceFile)
            self.browser.sourceFile[str, int, str].connect(
                self.viewmanager.openSourceFile
            )
            self.browser.sourceFile[str, int, int].connect(
                self.viewmanager.openSourceFileLinePos
            )
            self.browser.designerFile.connect(self.__designer)
            self.browser.linguistFile.connect(self.__linguist)
            self.browser.projectFile.connect(self.project.openProject)
            self.browser.multiProjectFile.connect(self.multiProject.openMultiProject)
            self.browser.pixmapEditFile.connect(self.__editPixmap)
            self.browser.pixmapFile.connect(self.__showPixmap)
            self.browser.svgFile.connect(self.__showSvg)
            self.browser.umlFile.connect(self.__showUml)
            self.browser.binaryFile.connect(self.__openHexEditor)
            self.browser.pdfFile.connect(self.__openPdfViewer)
            self.browser.testFile.connect(self.__startTestScript)
            self.browser.trpreview.connect(self.__TRPreviewer)

            self.debuggerUI.debuggingStarted.connect(self.browser.handleProgramChange)

            self.__debugServer.clientInterpreterChanged.connect(
                self.browser.handleInterpreterChanged
            )

            self.preferencesChanged.connect(self.browser.handlePreferencesChanged)

        if self.codeDocumentationViewer is not None:
            self.preferencesChanged.connect(
                self.codeDocumentationViewer.preferencesChanged
            )

        self.viewmanager.editorSaved.connect(self.project.repopulateItem)
        self.viewmanager.lastEditorClosed.connect(self.__lastEditorClosed)
        self.viewmanager.editorOpened.connect(self.__editorOpened)
        self.viewmanager.changeCaption.connect(self.__setWindowCaption)
        self.viewmanager.checkActions.connect(self.__checkActions)
        self.viewmanager.editorChanged.connect(self.projectBrowser.handleEditorChanged)
        self.viewmanager.editorLineChanged.connect(
            self.projectBrowser.handleEditorLineChanged
        )
        self.viewmanager.editorOpened.connect(self.__writeCrashSession)
        self.viewmanager.editorClosed.connect(self.__writeCrashSession)
        self.viewmanager.editorRenamed.connect(self.__writeCrashSession)
        self.viewmanager.editorChanged.connect(self.__writeCrashSession)

        self.shell.zoomValueChanged.connect(
            lambda v: self.viewmanager.zoomValueChanged(v, self.shell)
        )

        if self.cooperation is not None:
            self.viewmanager.checkActions.connect(self.cooperation.checkEditorActions)
            self.preferencesChanged.connect(self.cooperation.preferencesChanged)
            self.cooperation.shareEditor.connect(self.viewmanager.shareEditor)
            self.cooperation.startEdit.connect(self.viewmanager.startSharedEdit)
            self.cooperation.sendEdit.connect(self.viewmanager.sendSharedEdit)
            self.cooperation.cancelEdit.connect(self.viewmanager.cancelSharedEdit)
            self.cooperation.connected.connect(self.viewmanager.shareConnected)
            self.cooperation.editorCommand.connect(self.viewmanager.receive)
            self.viewmanager.setCooperationClient(self.cooperation.getClient())

        if self.symbolsViewer is not None:
            self.symbolsViewer.insertSymbol.connect(self.viewmanager.insertSymbol)

        if self.numbersViewer is not None:
            self.numbersViewer.insertNumber.connect(self.viewmanager.insertNumber)

        if self.irc is not None:
            self.irc.autoConnected.connect(self.__ircAutoConnected)

        if self.pipWidget is not None:
            self.preferencesChanged.connect(self.pipWidget.preferencesChanged)

        if self.microPythonWidget is not None:
            self.microPythonWidget.aboutToDisconnect.connect(
                self.viewmanager.closeDeviceEditors
            )

        self.__ericServerInterface.connectionStateChanged.connect(
            self.project.remoteConnectionChanged
        )
        self.__ericServerInterface.connectionStateChanged.connect(
            self.viewmanager.remoteConnectionChanged
        )
        self.__ericServerInterface.connectionStateChanged.connect(
            self.shell.remoteConnectionChanged
        )

        self.__ericServerInterface.aboutToDisconnect.connect(
            self.project.remoteConnectionAboutToDisconnect
        )
        self.__ericServerInterface.aboutToDisconnect.connect(
            self.viewmanager.closeRemoteEditors
        )

        # create the toolbar manager object
        self.toolbarManager = EricToolBarManager(
            ui=self, iconSize=Preferences.getIcons("IconSize"), parent=self
        )
        self.toolbarManager.setMainWindow(self)

        # Initialize the tool groups and list of started tools
        splash.showMessage(self.tr("Initializing Tools..."))
        logging.getLogger(__name__).debug("Initializing Tools...")
        self.toolGroups, self.currentToolGroup = Preferences.readToolGroups()
        self.toolProcs = []
        self.__initExternalToolsActions()

        # redirect handling of http, https and file URLs to ourselves
        QDesktopServices.setUrlHandler("file", self.handleUrl)
        QDesktopServices.setUrlHandler("http", self.handleUrl)
        QDesktopServices.setUrlHandler("https", self.handleUrl)

        # register all relevant objects
        splash.showMessage(self.tr("Registering Objects..."))
        logging.getLogger(__name__).debug("Registering Objects...")
        ericApp().registerObject("UserInterface", self)
        ericApp().registerObject("DebugUI", self.debuggerUI)
        ericApp().registerObject("DebugServer", self.__debugServer)
        ericApp().registerObject("BackgroundService", self.backgroundService)
        ericApp().registerObject("ViewManager", self.viewmanager)
        ericApp().registerObject("ProjectBrowser", self.projectBrowser)
        ericApp().registerObject("MultiProject", self.multiProject)
        ericApp().registerObject("TaskViewer", self.taskViewer)
        if self.templateViewer is not None:
            ericApp().registerObject("TemplateViewer", self.templateViewer)
        ericApp().registerObject("Shell", self.shell)
        ericApp().registerObject("PluginManager", self.pluginManager)
        ericApp().registerObject("ToolbarManager", self.toolbarManager)
        if self.cooperation is not None:
            ericApp().registerObject("Cooperation", self.cooperation)
        if self.irc is not None:
            ericApp().registerObject("IRC", self.irc)
        if self.symbolsViewer is not None:
            ericApp().registerObject("Symbols", self.symbolsViewer)
        if self.numbersViewer is not None:
            ericApp().registerObject("Numbers", self.numbersViewer)
        if self.codeDocumentationViewer is not None:
            ericApp().registerObject("DocuViewer", self.codeDocumentationViewer)
        if self.microPythonWidget is not None:
            ericApp().registerObject("MicroPython", self.microPythonWidget)
        ericApp().registerObject("JediAssistant", self.jediAssistant)
        ericApp().registerObject("PluginRepositoryViewer", self.pluginRepositoryViewer)

        # create the various JSON file interfaces
        self.__sessionFile = SessionFile(True)
        self.__tasksFile = TasksFile(True)

        # Initialize the actions, menus, toolbars and statusbar
        splash.showMessage(self.tr("Initializing Actions..."))
        logging.getLogger(__name__).debug("Initializing Actions...")
        self.__initActions()
        splash.showMessage(self.tr("Initializing Menus..."))
        logging.getLogger(__name__).debug("Initializing Menus...")
        self.__initMenus()
        splash.showMessage(self.tr("Initializing Toolbars..."))
        logging.getLogger(__name__).debug("Initializing Toolbars...")
        self.__initToolbars()
        splash.showMessage(self.tr("Initializing Statusbar..."))
        logging.getLogger(__name__).debug("Initializing Statusbar...")
        self.__initStatusbar()

        # connect the appFocusChanged signal after all actions are ready
        app.focusChanged.connect(self.viewmanager.appFocusChanged)

        # Initialize the instance variables.
        self.currentProg = None
        self.isProg = False
        self.__testingEditorOpen = False
        self.__testingProjectOpen = False

        self.inDragDrop = False
        self.setAcceptDrops(True)

        self.currentProfile = None

        self.shutdownCalled = False
        self.inCloseEvent = False

        # now fire up the single application server
        if Preferences.getUI("SingleApplicationMode"):
            splash.showMessage(self.tr("Initializing Single Application Server..."))
            logging.getLogger(__name__).debug(
                self.tr("Initializing Single Application Server...")
            )
            self.SAServer = EricSingleApplicationServer()
        else:
            self.SAServer = None

        # now finalize the plugin manager setup
        splash.showMessage(self.tr("Initializing Plugins..."))
        logging.getLogger(__name__).debug("Initializing Plugins...")
        self.pluginManager.finalizeSetup()
        # now activate plugins having autoload set to True
        splash.showMessage(self.tr("Activating Plugins..."))
        logging.getLogger(__name__).debug("Activating Plugins...")
        self.pluginManager.activatePlugins()
        splash.showMessage(self.tr("Generating Plugins Toolbars..."))
        logging.getLogger(__name__).debug("Generating Plugins Toolbars...")
        self.pluginManager.initPluginToolbars(self.toolbarManager)
        if Preferences.getPluginManager("StartupCleanup"):
            splash.showMessage(self.tr("Cleaning Plugins Download Area..."))
            logging.getLogger(__name__).debug("Cleaning Plugins Download Area...")
            PluginRepositoryDownloadCleanup(quiet=True)

        if self.__findFileWidget:
            self.__findFileWidget.populateFileCategories()

        # now read the keyboard shortcuts for all the actions
        Shortcuts.readShortcuts()

        # restore toolbar manager state
        splash.showMessage(self.tr("Restoring Toolbarmanager..."))
        logging.getLogger(__name__).debug("Restoring Toolbarmanager...")
        self.toolbarManager.restoreState(Preferences.getUI("ToolbarManagerState"))

        if self.codeDocumentationViewer is not None:
            # finalize the initialization of the code documentation viewer
            self.codeDocumentationViewer.finalizeSetup()

        # now activate the initial view profile
        splash.showMessage(self.tr("Setting View Profile..."))
        logging.getLogger(__name__).debug("Setting View Profile...")
        self.__setEditProfile()

        # special treatment for the VCS toolbars
        for tb in self.getToolbarsByCategory("vcs"):
            tb.setVisible(False)
            tb.setEnabled(False)
        tb = self.getToolbar("vcs")[1]
        tb.setEnabled(True)
        if Preferences.getVCS("ShowVcsToolbar"):
            tb.setVisible(True)

        # now read the saved tasks
        splash.showMessage(self.tr("Reading Tasks..."))
        logging.getLogger(__name__).debug("Reading Tasks...")
        self.__readTasks()

        if self.templateViewer is not None:
            # now read the saved templates
            splash.showMessage(self.tr("Reading Templates..."))
            logging.getLogger(__name__).debug("Reading Templates...")
            self.templateViewer.readTemplates()

        # now start the debug client with the most recently used virtual
        # environment
        splash.showMessage(self.tr("Starting Debugger..."))
        logging.getLogger(__name__).debug("Starting Debugger...")
        if Preferences.getShell("StartWithMostRecentlyUsedEnvironment"):
            venvName = Preferences.getShell("LastVirtualEnvironment")
            if venvName == "embedded environment":
                venvName = ""
            self.__debugServer.startClient(False, venvName=venvName)
        else:
            self.__debugServer.startClient(False)

        # attributes for the network objects
        self.__networkManager = QNetworkAccessManager(self)
        self.__networkManager.proxyAuthenticationRequired.connect(
            proxyAuthenticationRequired
        )
        if SSL_AVAILABLE:
            self.__sslErrorHandler = EricSslErrorHandler(
                Preferences.getSettings(), self
            )
            self.__networkManager.sslErrors.connect(self.__sslErrors)
        self.__replies = []

        # attributes for the last shown configuration page and the
        # extended configuration entries
        self.__lastConfigurationPageName = ""
        self.__expandedConfigurationEntries = []

        # set the keyboard input interval
        interval = Preferences.getUI("KeyboardInputInterval")
        if interval > 0:
            QApplication.setKeyboardInputInterval(interval)

        # connect to the desktop environment session manager
        app.commitDataRequest.connect(
            self.__commitData, Qt.ConnectionType.DirectConnection
        )

    def networkAccessManager(self):
        """
        Public method to get a reference to the network access manager object.

        @return reference to the network access manager object
        @rtype QNetworkAccessManager
        """
        return self.__networkManager

    def __createObjects(self):
        """
        Private method to create the various application objects.
        """
        from eric7 import ViewManager
        from eric7.Debugger.DebugViewer import DebugViewer
        from eric7.JediInterface.AssistantJedi import AssistantJedi
        from eric7.MultiProject.MultiProjectBrowser import MultiProjectBrowser
        from eric7.PluginManager.PluginRepositoryDialog import PluginRepositoryWidget
        from eric7.Project.ProjectBrowser import ProjectBrowser
        from eric7.QScintilla.Shell import ShellAssembly
        from eric7.Tasks.TaskViewer import TaskViewer
        from eric7.VCS.StatusWidget import StatusWidget
        from eric7.VirtualEnv.VirtualenvManagerWidgets import VirtualenvManagerWidget

        from .LogView import LogViewer
        from .Previewer import Previewer
        from .PythonAstViewer import PythonAstViewer
        from .PythonDisViewer import PythonDisViewer

        # Create the view manager depending on the configuration setting
        logging.getLogger(__name__).debug("Creating Viewmanager...")
        self.viewmanager = ViewManager.factory(
            self, self.__debugServer, self.__ericServerInterface, self.pluginManager
        )

        # Create previewer
        logging.getLogger(__name__).debug("Creating Previewer...")
        self.__previewer = Previewer(self.viewmanager)

        # Create AST viewer
        logging.getLogger(__name__).debug("Creating Python AST Viewer")
        self.__astViewer = PythonAstViewer(self.viewmanager)

        # Create DIS viewer
        logging.getLogger(__name__).debug("Creating Python Disassembly Viewer")
        self.__disViewer = PythonDisViewer(self.viewmanager)

        # Create the project browser
        logging.getLogger(__name__).debug("Creating Project Browser...")
        self.projectBrowser = ProjectBrowser(self.project)

        # Create the multi project browser
        logging.getLogger(__name__).debug("Creating Multi Project Browser...")
        self.multiProjectBrowser = MultiProjectBrowser(self.multiProject, self.project)

        # Create the task viewer part of the user interface
        logging.getLogger(__name__).debug("Creating Task Viewer...")
        self.taskViewer = TaskViewer(None, self.project)

        # Create the log viewer part of the user interface
        logging.getLogger(__name__).debug("Creating Log Viewer...")
        self.logViewer = LogViewer(self)

        # Create the debug viewer
        logging.getLogger(__name__).debug("Creating Debug Viewer...")
        self.debugViewer = DebugViewer(self.__debugServer)

        # Create the shell
        logging.getLogger(__name__).debug("Creating Shell...")
        self.shellAssembly = ShellAssembly(
            self.__debugServer, self.viewmanager, self.project, True
        )
        self.shell = self.shellAssembly.shell()

        if Preferences.getUI("ShowTemplateViewer"):
            # Create the template viewer part of the user interface
            logging.getLogger(__name__).debug("Creating Template Viewer...")
            from eric7.Templates.TemplateViewer import TemplateViewer  # noqa: I101

            self.templateViewer = TemplateViewer(None, self.viewmanager)
        else:
            logging.getLogger(__name__).debug("Template Viewer disabled")
            self.templateViewer = None

        if Preferences.getUI("ShowFileBrowser"):
            # Create the file browser
            logging.getLogger(__name__).debug("Creating File Browser...")
            from .Browser import Browser  # noqa: I101

            self.browser = Browser(self.__ericServerInterface)
        else:
            logging.getLogger(__name__).debug("File Browser disabled")
            self.browser = None

        if Preferences.getUI("ShowSymbolsViewer"):
            # Create the symbols viewer
            logging.getLogger(__name__).debug("Creating Symbols Viewer...")
            from .SymbolsWidget import SymbolsWidget  # noqa: I101

            self.symbolsViewer = SymbolsWidget()
        else:
            logging.getLogger(__name__).debug("Symbols Viewer disabled")
            self.symbolsViewer = None

        if Preferences.getUI("ShowCodeDocumentationViewer"):
            # Create the code documentation viewer
            logging.getLogger(__name__).debug("Creating Code Documentation Viewer...")
            from .CodeDocumentationViewer import CodeDocumentationViewer  # noqa: I101

            self.codeDocumentationViewer = CodeDocumentationViewer(self)
        else:
            logging.getLogger(__name__).debug("Code Documentation Viewer disabled")
            self.codeDocumentationViewer = None

        if Preferences.getUI("ShowPyPIPackageManager"):
            # Create the PyPI package manager
            logging.getLogger(__name__).debug("Creating PyPI Package Manager...")
            from eric7.PipInterface.PipPackagesWidget import (  # noqa: I101
                PipPackagesWidget,
            )

            self.pipWidget = PipPackagesWidget(self.pipInterface)
        else:
            logging.getLogger(__name__).debug("PyPI Package Manager disabled")
            self.pipWidget = None

        if Preferences.getUI("ShowCondaPackageManager"):
            # Create the conda package manager
            logging.getLogger(__name__).debug("Creating Conda Package Manager...")
            from eric7.CondaInterface.CondaPackagesWidget import (  # noqa: I101
                CondaPackagesWidget,
            )

            self.condaWidget = CondaPackagesWidget(self.condaInterface)
        else:
            logging.getLogger(__name__).debug("Conda Package Manager disabled")
            self.condaWidget = None

        if Preferences.getUI("ShowCooperation"):
            # Create the chat part of the user interface
            logging.getLogger(__name__).debug("Creating Chat Widget...")
            from eric7.Cooperation.ChatWidget import ChatWidget  # noqa: I101

            self.cooperation = ChatWidget(self)
        else:
            logging.getLogger(__name__).debug("Chat Widget disabled")
            self.cooperation = None

        if Preferences.getUI("ShowIrc"):
            # Create the IRC part of the user interface
            logging.getLogger(__name__).debug("Creating IRC Widget...")
            from eric7.Network.IRC.IrcWidget import IrcWidget  # noqa: I101

            self.irc = IrcWidget(self)
        else:
            logging.getLogger(__name__).debug("IRC Widget disabled")
            self.irc = None

        if Preferences.getUI("ShowMicroPython"):
            # Create the MicroPython part of the user interface
            logging.getLogger(__name__).debug("Creating MicroPython Widget...")
            from eric7.MicroPython.MicroPythonWidget import (  # noqa: I101
                MicroPythonWidget,
            )

            self.microPythonWidget = MicroPythonWidget(self)
        else:
            logging.getLogger(__name__).debug("MicroPython Widget disabled")
            self.microPythonWidget = None

        if Preferences.getUI("ShowNumbersViewer"):
            # Create the numbers viewer
            logging.getLogger(__name__).debug("Creating Numbers Viewer...")
            from .NumbersWidget import NumbersWidget  # noqa: I101

            self.numbersViewer = NumbersWidget()
        else:
            logging.getLogger(__name__).debug("Numbers Viewer disabled")
            self.numbersViewer = None

        # Create the Jedi Assistant
        logging.getLogger(__name__).debug("Creating Jedi Assistant...")
        self.jediAssistant = AssistantJedi(self, self.viewmanager, self.project)

        # Create the plug-ins repository viewer
        logging.getLogger(__name__).debug("Creating Plugin Repository Viewer...")
        self.pluginRepositoryViewer = PluginRepositoryWidget(
            self.pluginManager, integrated=True, parent=self
        )
        self.pluginRepositoryViewer.closeAndInstall.connect(
            self.__installDownloadedPlugins
        )

        # Create the virtual environments management widget
        logging.getLogger(__name__).debug("Creating Virtual Environments Viewer...")
        self.__virtualenvManagerWidget = VirtualenvManagerWidget(
            self.virtualenvManager, self
        )

        self.__findFileDialog = None
        self.__replaceFileDialog = None
        if Preferences.getUI("ShowFindFileWidget"):
            # Create the find in files widget
            from .FindFileWidget import FindFileWidget  # noqa: I101

            logging.getLogger(__name__).debug("Creating Find/Replace Pane...")
            self.__findFileWidget = FindFileWidget(self.project, self)
            self.__findFileWidget.sourceFile.connect(self.viewmanager.openSourceFile)
            self.__findFileWidget.designerFile.connect(self.__designer)
            self.__findFileWidget.linguistFile.connect(self.__linguist)
            self.__findFileWidget.trpreview.connect(self.__TRPreviewer)
            self.__findFileWidget.pixmapFile.connect(self.__showPixmap)
            self.__findFileWidget.svgFile.connect(self.__showSvg)
            self.__findFileWidget.umlFile.connect(self.__showUml)
        else:
            logging.getLogger(__name__).debug("Find/Replace Pane disabled...")
            self.__findFileWidget = None

        self.__findLocationDialog = None
        if Preferences.getUI("ShowFindLocationWidget"):
            # Create the find location (file) widget
            from .FindLocationWidget import FindLocationWidget  # noqa: I101

            logging.getLogger(__name__).debug("Creating Find File Pane...")
            self.__findLocationWidget = FindLocationWidget(self.project, self)
            self.__findLocationWidget.sourceFile.connect(
                self.viewmanager.openSourceFile
            )
            self.__findLocationWidget.designerFile.connect(self.__designer)
            self.__findLocationWidget.linguistFile.connect(self.__linguist)
            self.__findLocationWidget.trpreview.connect(self.__TRPreviewer)
            self.__findLocationWidget.pixmapFile.connect(self.__showPixmap)
            self.__findLocationWidget.svgFile.connect(self.__showSvg)
            self.__findLocationWidget.umlFile.connect(self.__showUml)
        else:
            logging.getLogger(__name__).debug("Find File Pane disabled...")
            self.__findLocationWidget = None

        # Create the VCS Status widget
        logging.getLogger(__name__).debug("Creating VCS Status Viewer...")
        self.__vcsStatusWidget = StatusWidget(self.project, self.viewmanager, self)

        if (
            Preferences.getUI("ShowInternalHelpViewer")
            or Preferences.getHelp("HelpViewerType") == 0
        ):
            # Create the embedded help viewer
            logging.getLogger(__name__).debug("Creating Internal Help Viewer...")
            from eric7.HelpViewer.HelpViewerWidget import HelpViewerWidget  # noqa: I101

            self.__helpViewerWidget = HelpViewerWidget(self)
        else:
            logging.getLogger(__name__).debug("Internal Help Viewer disabled...")
            self.__helpViewerWidget = None

    def __createLayout(self):
        """
        Private method to create the layout of the various windows.

        @exception ValueError raised to indicate an invalid layout type
        """
        leftWidget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(1)
        layout.addWidget(self.viewmanager.mainWidget())
        layout.addWidget(self.viewmanager.searchReplaceWidget())
        self.viewmanager.mainWidget().setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        leftWidget.setLayout(layout)
        self.viewmanager.searchReplaceWidget().hide()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(leftWidget)
        self.setCentralWidget(splitter)

        self.__previewer.setSplitter(splitter)
        splitter.addWidget(self.__previewer)

        splitter.addWidget(self.__astViewer)

        splitter.addWidget(self.__disViewer)

        # Initialize the widgets of the layouts to None
        self.lToolbox = None
        self.rToolbox = None
        self.hToolbox = None
        self.leftSidebar = None
        self.rightSidebar = None
        self.bottomSidebar = None

        # Create layout with toolbox windows embedded in dock windows
        if self.__layoutType == "Toolboxes":
            logging.getLogger(__name__).debug("Creating toolboxes...")
            self.__createToolboxesLayout()

        # Create layout with sidebar windows embedded in dock windows
        elif self.__layoutType == "Sidebars":
            logging.getLogger(__name__).debug("Creating sidebars...")
            self.__createSidebarsLayout()

        else:
            raise ValueError("Wrong layout type given ({0})".format(self.__layoutType))
        logging.getLogger(__name__).debug("Created Layout")

    def __createToolboxesLayout(self):
        """
        Private method to create the Toolboxes layout.
        """
        from eric7.EricWidgets.EricToolBox import (
            EricHorizontalToolBox,
            EricVerticalToolBox,
        )

        logging.getLogger(__name__).debug("Creating Toolboxes Layout...")

        # Create the left toolbox
        self.lToolboxDock = self.__createDockWindow("lToolboxDock")
        self.lToolbox = EricVerticalToolBox(self.lToolboxDock)
        self.__setupDockWindow(
            self.lToolboxDock,
            Qt.DockWidgetArea.LeftDockWidgetArea,
            self.lToolbox,
            self.tr("Left Toolbox"),
        )

        # Create the horizontal toolbox
        self.hToolboxDock = self.__createDockWindow("hToolboxDock")
        self.hToolbox = EricHorizontalToolBox(self.hToolboxDock)
        self.__setupDockWindow(
            self.hToolboxDock,
            Qt.DockWidgetArea.BottomDockWidgetArea,
            self.hToolbox,
            self.tr("Horizontal Toolbox"),
        )
        self.hToolbox.currentChanged.connect(self.__hToolboxCurrentChanged)

        # Create the right toolbox
        self.rToolboxDock = self.__createDockWindow("rToolboxDock")
        self.rToolbox = EricVerticalToolBox(self.rToolboxDock)
        self.__setupDockWindow(
            self.rToolboxDock,
            Qt.DockWidgetArea.RightDockWidgetArea,
            self.rToolbox,
            self.tr("Right Toolbox"),
        )

        ####################################################
        ## Populate the left toolbox
        ####################################################

        self.lToolbox.addItem(
            self.multiProjectBrowser,
            EricPixmapCache.getIcon("multiProjectViewer"),
            self.tr("Multiproject-Viewer"),
        )

        self.lToolbox.addItem(
            self.projectBrowser,
            EricPixmapCache.getIcon("projectViewer"),
            self.tr("Project-Viewer"),
        )

        if self.__findFileWidget:
            self.lToolbox.addItem(
                self.__findFileWidget,
                EricPixmapCache.getIcon("find"),
                self.tr("Find/Replace In Files"),
            )

        if self.__findLocationWidget:
            self.lToolbox.addItem(
                self.__findLocationWidget,
                EricPixmapCache.getIcon("findLocation"),
                self.tr("Find File"),
            )

        self.lToolbox.addItem(
            self.__vcsStatusWidget,
            EricPixmapCache.getIcon("tbVcsStatus"),
            self.tr("VCS Status"),
        )

        if self.templateViewer:
            self.lToolbox.addItem(
                self.templateViewer,
                EricPixmapCache.getIcon("templateViewer"),
                self.tr("Template-Viewer"),
            )

        if self.browser:
            self.lToolbox.addItem(
                self.browser,
                EricPixmapCache.getIcon("browser"),
                self.tr("File-Browser"),
            )

        if self.symbolsViewer:
            self.lToolbox.addItem(
                self.symbolsViewer,
                EricPixmapCache.getIcon("symbols"),
                self.tr("Symbols"),
            )

        ####################################################
        ## Populate the right toolbox
        ####################################################

        self.rToolbox.addItem(
            self.debugViewer,
            EricPixmapCache.getIcon("debugViewer"),
            self.tr("Debug-Viewer"),
        )

        if self.codeDocumentationViewer:
            self.rToolbox.addItem(
                self.codeDocumentationViewer,
                EricPixmapCache.getIcon("codeDocuViewer"),
                self.tr("Code Documentation Viewer"),
            )

        if self.__helpViewerWidget:
            self.rToolbox.addItem(
                self.__helpViewerWidget,
                EricPixmapCache.getIcon("help"),
                self.tr("Help Viewer"),
            )

        self.rToolbox.addItem(
            self.pluginRepositoryViewer,
            EricPixmapCache.getIcon("pluginRepository"),
            self.tr("Plugin Repository"),
        )

        self.rToolbox.addItem(
            self.__virtualenvManagerWidget,
            EricPixmapCache.getIcon("virtualenv"),
            self.tr("Virtual Environments"),
        )

        if self.pipWidget:
            self.rToolbox.addItem(
                self.pipWidget,
                EricPixmapCache.getIcon("pypi"),
                self.tr("PyPI Package Management"),
            )

        if self.condaWidget:
            self.rToolbox.addItem(
                self.condaWidget, EricPixmapCache.getIcon("miniconda"), self.tr("Conda")
            )

        if self.cooperation:
            self.rToolbox.addItem(
                self.cooperation,
                EricPixmapCache.getIcon("cooperation"),
                self.tr("Cooperation"),
            )

        if self.irc:
            self.rToolbox.addItem(
                self.irc, EricPixmapCache.getIcon("irc"), self.tr("IRC")
            )

        if self.microPythonWidget:
            self.rToolbox.addItem(
                self.microPythonWidget,
                EricPixmapCache.getIcon("micropython"),
                self.tr("MicroPython"),
            )

        ####################################################
        ## Populate the bottom toolbox
        ####################################################

        self.hToolbox.addItem(
            self.shellAssembly, EricPixmapCache.getIcon("shell"), self.tr("Shell")
        )

        self.hToolbox.addItem(
            self.taskViewer, EricPixmapCache.getIcon("task"), self.tr("Task-Viewer")
        )

        self.hToolbox.addItem(
            self.logViewer, EricPixmapCache.getIcon("logViewer"), self.tr("Log-Viewer")
        )

        if self.numbersViewer:
            self.hToolbox.addItem(
                self.numbersViewer,
                EricPixmapCache.getIcon("numbers"),
                self.tr("Numbers"),
            )

        ####################################################
        ## Set the start index of each toolbox
        ####################################################

        self.lToolbox.setCurrentIndex(0)
        self.rToolbox.setCurrentIndex(0)
        self.hToolbox.setCurrentIndex(0)

    def __createSidebarsLayout(self):
        """
        Private method to create the Sidebars layout.
        """
        from eric7.EricWidgets.EricSideBar import EricSideBar, EricSideBarSide

        logging.getLogger(__name__).debug("Creating Sidebars Layout...")

        # Create the left sidebar
        self.leftSidebar = EricSideBar(
            EricSideBarSide.WEST, Preferences.getUI("IconBarSize")
        )
        self.leftSidebar.setIconBarColor(Preferences.getUI("IconBarColor"))

        # Create the bottom sidebar
        self.bottomSidebar = EricSideBar(
            EricSideBarSide.SOUTH, Preferences.getUI("IconBarSize")
        )
        self.bottomSidebar.setIconBarColor(Preferences.getUI("IconBarColor"))
        self.bottomSidebar.currentChanged.connect(self.__bottomSidebarCurrentChanged)

        # Create the right sidebar
        if Preferences.getUI("CombinedLeftRightSidebar"):
            # combine left and right sidebar on the left side
            self.rightSidebar = None
        else:
            self.rightSidebar = EricSideBar(
                EricSideBarSide.EAST, Preferences.getUI("IconBarSize")
            )
            self.rightSidebar.setIconBarColor(Preferences.getUI("IconBarColor"))

        ####################################################
        ## Populate the left side bar
        ####################################################

        self.leftSidebar.addTab(
            self.multiProjectBrowser,
            EricPixmapCache.getIcon("sbMultiProjectViewer96"),
            self.tr("Multiproject-Viewer"),
        )

        self.leftSidebar.addTab(
            self.projectBrowser,
            EricPixmapCache.getIcon("sbProjectViewer96"),
            self.tr("Project-Viewer"),
        )

        if self.__findFileWidget:
            self.leftSidebar.addTab(
                self.__findFileWidget,
                EricPixmapCache.getIcon("sbFind96"),
                self.tr("Find/Replace In Files"),
            )

        if self.__findLocationWidget:
            self.leftSidebar.addTab(
                self.__findLocationWidget,
                EricPixmapCache.getIcon("sbFindLocation96"),
                self.tr("Find File"),
            )

        self.leftSidebar.addTab(
            self.__vcsStatusWidget,
            EricPixmapCache.getIcon("sbVcsStatus96"),
            self.tr("VCS Status"),
        )

        if self.templateViewer:
            self.leftSidebar.addTab(
                self.templateViewer,
                EricPixmapCache.getIcon("sbTemplateViewer96"),
                self.tr("Template-Viewer"),
            )

        if self.browser:
            self.leftSidebar.addTab(
                self.browser,
                EricPixmapCache.getIcon("sbFileBrowser96"),
                self.tr("File-Browser"),
            )

        if self.symbolsViewer:
            self.leftSidebar.addTab(
                self.symbolsViewer,
                EricPixmapCache.getIcon("sbSymbolsViewer96"),
                self.tr("Symbols"),
            )

        ##############################################################
        ## Populate the right side bar or combined left sidebar
        ##############################################################

        sidebar = self.rightSidebar or self.leftSidebar

        if sidebar is self.leftSidebar:
            # place debug viewer after 'VCS Status' widget
            index = self.leftSidebar.indexOf(self.__vcsStatusWidget) + 1
            sidebar.insertTab(
                index,
                self.debugViewer,
                EricPixmapCache.getIcon("sbDebugViewer96"),
                self.tr("Debug-Viewer"),
            )
        else:
            sidebar.addTab(
                self.debugViewer,
                EricPixmapCache.getIcon("sbDebugViewer96"),
                self.tr("Debug-Viewer"),
            )

        if self.codeDocumentationViewer:
            sidebar.addTab(
                self.codeDocumentationViewer,
                EricPixmapCache.getIcon("sbCodeDocuViewer96"),
                self.tr("Code Documentation Viewer"),
            )

        if self.__helpViewerWidget:
            sidebar.addTab(
                self.__helpViewerWidget,
                EricPixmapCache.getIcon("sbHelpViewer96"),
                self.tr("Help Viewer"),
            )

        sidebar.addTab(
            self.pluginRepositoryViewer,
            EricPixmapCache.getIcon("sbPluginRepository96"),
            self.tr("Plugin Repository"),
        )

        sidebar.addTab(
            self.__virtualenvManagerWidget,
            EricPixmapCache.getIcon("sbVirtenvManager96"),
            self.tr("Virtual Environments"),
        )

        if self.pipWidget:
            sidebar.addTab(
                self.pipWidget,
                EricPixmapCache.getIcon("sbPyPI96"),
                self.tr("PyPI Package Management"),
            )

        if self.condaWidget:
            sidebar.addTab(
                self.condaWidget,
                EricPixmapCache.getIcon("sbMiniconda96"),
                self.tr("Conda"),
            )

        if self.cooperation:
            sidebar.addTab(
                self.cooperation,
                EricPixmapCache.getIcon("sbCooperation96"),
                self.tr("Cooperation"),
            )

        if self.irc:
            sidebar.addTab(self.irc, EricPixmapCache.getIcon("sbIrc96"), self.tr("IRC"))

        if self.microPythonWidget:
            sidebar.addTab(
                self.microPythonWidget,
                EricPixmapCache.getIcon("sbMicroPython96"),
                self.tr("MicroPython"),
            )

        ####################################################
        ## Populate the bottom side bar
        ####################################################

        self.bottomSidebar.addTab(
            self.shellAssembly, EricPixmapCache.getIcon("sbShell96"), self.tr("Shell")
        )

        self.bottomSidebar.addTab(
            self.taskViewer,
            EricPixmapCache.getIcon("sbTasksViewer96"),
            self.tr("Task-Viewer"),
        )

        self.bottomSidebar.addTab(
            self.logViewer,
            EricPixmapCache.getIcon("sbLogViewer96"),
            self.tr("Log-Viewer"),
        )

        if self.numbersViewer:
            self.bottomSidebar.addTab(
                self.numbersViewer,
                EricPixmapCache.getIcon("sbNumbers96"),
                self.tr("Numbers"),
            )

        ####################################################
        ## Set the start index of each side bar
        ####################################################

        self.leftSidebar.setCurrentIndex(0)
        if self.rightSidebar:
            if self.__helpViewerWidget is not None:
                self.rightSidebar.setCurrentWidget(self.__helpViewerWidget)
            else:
                self.rightSidebar.setCurrentIndex(0)
        self.bottomSidebar.setCurrentIndex(0)

        # create the central widget
        logging.getLogger(__name__).debug("Creating central widget...")
        cw = self.centralWidget()  # save the current central widget
        self.horizontalSplitter = QSplitter(Qt.Orientation.Horizontal)
        self.horizontalSplitter.setChildrenCollapsible(False)
        self.verticalSplitter = QSplitter(Qt.Orientation.Vertical)
        self.verticalSplitter.setChildrenCollapsible(False)
        self.verticalSplitter.addWidget(cw)
        self.verticalSplitter.addWidget(self.bottomSidebar)
        self.horizontalSplitter.addWidget(self.leftSidebar)
        self.horizontalSplitter.addWidget(self.verticalSplitter)
        if self.rightSidebar:
            self.horizontalSplitter.addWidget(self.rightSidebar)
        self.setCentralWidget(self.horizontalSplitter)

    def addSideWidget(self, side, widget, icon, label):
        """
        Public method to add a widget to the sides.

        @param side side to add the widget to
        @type UserInterfaceSide
        @param widget reference to the widget to add
        @type QWidget
        @param icon icon to be used
        @type QIcon
        @param label label text to be shown
        @type str
        """
        if self.__layoutType == "Toolboxes":
            if side == UserInterfaceSide.Left:
                self.lToolbox.addItem(widget, icon, label)
            elif side == UserInterfaceSide.Bottom:
                self.hToolbox.addItem(widget, icon, label)
            elif side == UserInterfaceSide.Right:
                self.rToolbox.addItem(widget, icon, label)
        elif self.__layoutType == "Sidebars":
            if side == UserInterfaceSide.Left:
                self.leftSidebar.addTab(widget, icon, label)
            elif side == UserInterfaceSide.Bottom:
                self.bottomSidebar.addTab(widget, icon, label)
            elif side == UserInterfaceSide.Right:
                if self.rightSidebar:
                    self.rightSidebar.addTab(widget, icon, label)
                else:
                    self.leftSidebar.addTab(widget, icon, label)

    def removeSideWidget(self, widget):
        """
        Public method to remove a widget added using addSideWidget().

        @param widget reference to the widget to remove
        @type QWidget
        """
        if self.__layoutType == "Toolboxes":
            for container in [self.lToolbox, self.hToolbox, self.rToolbox]:
                index = container.indexOf(widget)
                if index != -1:
                    container.removeItem(index)
        elif self.__layoutType == "Sidebars":
            for container in [self.leftSidebar, self.bottomSidebar, self.rightSidebar]:
                if container is not None:
                    index = container.indexOf(widget)
                    if index != -1:
                        container.removeTab(index)

    def showSideWidget(self, widget):
        """
        Public method to show a specific widget placed in the side widgets.

        @param widget reference to the widget to be shown
        @type QWidget
        """
        if self.__layoutType == "Toolboxes":
            for dock in [self.lToolboxDock, self.hToolboxDock, self.rToolboxDock]:
                container = dock.widget()
                index = container.indexOf(widget)
                if index != -1:
                    dock.show()
                    container.setCurrentIndex(index)
                    dock.raise_()
        elif self.__layoutType == "Sidebars":
            for container in [self.leftSidebar, self.bottomSidebar, self.rightSidebar]:
                if container is not None:
                    index = container.indexOf(widget)
                    if index != -1:
                        container.show()
                        container.setCurrentIndex(index)
                        container.raise_()

    def showLogViewer(self):
        """
        Public method to show the Log-Viewer.
        """
        if Preferences.getUI("LogViewerAutoRaise"):
            if self.__layoutType == "Toolboxes":
                self.hToolboxDock.show()
                self.hToolbox.setCurrentWidget(self.logViewer)
                self.hToolboxDock.raise_()
            elif self.__layoutType == "Sidebars":
                self.bottomSidebar.show()
                self.bottomSidebar.setCurrentWidget(self.logViewer)
                self.bottomSidebar.raise_()
        else:
            if self.__layoutType == "Toolboxes":
                logViewerIndex = self.hToolbox.indexOf(self.logViewer)
                if self.hToolbox.currentIndex() != logViewerIndex:
                    self.hToolbox.setTabIcon(
                        logViewerIndex, EricPixmapCache.getIcon("logViewerNew")
                    )
            elif self.__layoutType == "Sidebars":
                logViewerIndex = self.bottomSidebar.indexOf(self.logViewer)
                if self.bottomSidebar.currentIndex() != logViewerIndex:
                    self.bottomSidebar.setTabIcon(
                        logViewerIndex, EricPixmapCache.getIcon("sbLogViewerNew96")
                    )

    def __openOnStartup(self, startupType=None):
        """
        Private method to open the last file, project or multiproject.

        @param startupType type of startup requested (one of
            "Nothing", "File", "Project", "MultiProject" or "Session")
        @type str
        """
        startupTypeMapping = {
            "Nothing": 0,
            "File": 1,
            "Project": 2,
            "MultiProject": 3,
            "Session": 4,
        }

        if startupType is None:
            startup = Preferences.getUI("OpenOnStartup")
        else:
            try:
                startup = startupTypeMapping[startupType]
            except KeyError:
                startup = Preferences.getUI("OpenOnStartup")

        if startup == 0:
            # open nothing
            pass
        elif startup == 1:
            # open last file
            recent = self.viewmanager.getMostRecent()
            if recent is not None:
                self.viewmanager.openFiles(recent)
        elif startup == 2:
            # open last project
            recent = self.project.getMostRecent()
            if recent is not None:
                self.project.openProject(recent)
        elif startup == 3:
            # open last multiproject
            recent = self.multiProject.getMostRecent()
            if recent is not None:
                self.multiProject.openMultiProject(recent)
        elif startup == 4:
            # open from session file
            self.__readSession()

    def processArgs(self, args):
        """
        Public method to process the command line args passed to the UI.

        @param args namespace object containing the parsed command line
            parameters
        @type argparse.Namespace
        """
        # check and optionally read a crash session and ignore any arguments
        if self.__readCrashSession():
            return

        if args.dd_args:
            # store away any args we had
            argsStr = " ".join(args.dd_args)
            self.debuggerUI.setArgvHistory(argsStr)

        if args.start_file:
            self.__openOnStartup("File")
            return
        elif args.start_multi:
            self.__openOnStartup("MultiProject")
            return
        elif args.start_project:
            self.__openOnStartup("Project")
            return
        elif args.start_session:
            self.__openOnStartup("Session")
            return

        opens = 0
        for filename in args.file_or_project:
            try:
                ext = os.path.splitext(filename)[1].lower()
            except IndexError:
                ext = ""

            if ext in (".epj",):
                self.project.openProject(filename)
                opens += 1
            elif ext in (".emj",):
                self.multiProject.openMultiProject(filename)
                opens += 1
            else:
                self.viewmanager.openFiles(filename)
                opens += 1

        if opens == 0 and self.__openAtStartup:
            # no files, project or multiproject was given
            self.__openOnStartup()

    def processInstallInfoFile(self):
        """
        Public method to process the file containing installation information.
        """
        from eric7 import Globals

        installInfoFile = Globals.getInstallInfoFilePath()
        if not os.path.exists(installInfoFile):
            filename = os.path.join(getConfig("ericDir"), "eric7install.json")
            if os.path.exists(filename):
                # eric was installed via the install.py script
                shutil.copy2(filename, installInfoFile)
            else:
                filename = os.path.join(getConfig("ericDir"), "eric7installpip.json")
                if os.path.exists(filename):
                    # eric was installed via pip (i.e. eric-ide)
                    with contextlib.suppress(OSError):
                        installDateTime = datetime.datetime.now(
                            tz=datetime.timezone.utc
                        )
                        with open(filename, "r") as infoFile:
                            installInfo = json.load(infoFile)
                        installInfo["guessed"] = True
                        installInfo["eric"] = getConfig("ericDir")
                        installInfo["virtualenv"] = installInfo["eric"].startswith(
                            os.path.expanduser("~")
                        )
                        if installInfo["virtualenv"]:
                            installInfo["user"] = getpass.getuser()
                            installInfo["exe"] = sys.executable
                        installInfo["installed"] = True
                        installInfo["installed_on"] = installDateTime.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        installInfo["sudo"] = not os.access(
                            installInfo["eric"], os.W_OK
                        )
                        with open(installInfoFile, "w") as infoFile:
                            json.dump(installInfo, infoFile, indent=2)
        else:
            changed = False
            with open(installInfoFile, "r") as infoFile:
                installInfo = json.load(infoFile)

            # 1. adapt stored file to latest format
            if "install_cwd" not in installInfo:
                installInfo["install_cwd"] = ""
                installInfo["install_cwd_edited"] = False
                changed = True
            if "installed_on" not in installInfo:
                installInfo["installed_on"] = ""
                changed = True

            # 2. merge new data into stored file
            filename = os.path.join(getConfig("ericDir"), "eric7install.json")
            if os.path.exists(filename):
                # eric was updated via the install.py script
                if os.path.getmtime(filename) > os.path.getmtime(installInfoFile):
                    if not installInfo["edited"]:
                        shutil.copy2(filename, installInfoFile)
                    else:
                        with open(filename, "r") as infoFile:
                            installInfo2 = json.load(infoFile)
                        if not installInfo["install_cwd_edited"]:
                            installInfo2["install_cwd"] = installInfo["install_cwd"]
                        if not installInfo["exe_edited"]:
                            installInfo2["exe"] = installInfo["exe"]
                        if not installInfo["argv_edited"]:
                            installInfo2["argv"] = installInfo["argv"]
                        if not installInfo["eric_edited"]:
                            installInfo2["eric"] = installInfo["eric"]
                        installInfo = installInfo2
                        changed = True
            else:
                filename = os.path.join(getConfig("ericDir"), "eric7installpip.json")
                if os.path.exists(filename) and os.path.getmtime(
                    filename
                ) > os.path.getmtime(installInfoFile):
                    # eric was updated via pip (i.e. eric-ide)
                    # just update the installation date and time
                    installDateTime = datetime.datetime.now(tz=datetime.timezone.utc)
                    installInfo["installed_on"] = installDateTime.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                    changed = True

            if changed:
                with open(installInfoFile, "w") as infoFile:
                    json.dump(installInfo, infoFile, indent=2)

    def __createDockWindow(self, name):
        """
        Private method to create a dock window with common properties.

        @param name object name of the new dock window
        @type str
        @return the generated dock window
        @rtype QDockWindow
        """
        dock = QDockWidget()
        dock.setObjectName(name)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        return dock

    def __setupDockWindow(self, dock, where, widget, caption):
        """
        Private method to configure the dock window created with
        __createDockWindow().

        @param dock the dock window
        @type QDockWindow
        @param where dock area to be docked to
        @type Qt.DockWidgetArea
        @param widget widget to be shown in the dock window
        @type QWidget
        @param caption caption of the dock window
        @type str
        """
        if caption is None:
            caption = ""
        self.addDockWidget(where, dock)
        dock.setWidget(widget)
        dock.setWindowTitle(caption)
        dock.show()

    def __setWindowCaption(self, editor=None, project=None):
        """
        Private method to set the caption of the Main Window.

        @param editor filename to be displayed
        @type str
        @param project project name to be displayed
        @type str
        """
        if editor is not None and self.captionShowsFilename:
            self.capEditor = FileSystemUtilities.compactPath(
                editor, self.maxFilePathLen
            )
        if project is not None:
            self.capProject = project

        if self.passiveMode:
            if not self.capProject and not self.capEditor:
                self.setWindowTitle(self.tr("{0} - Passive Mode").format("eric-ide"))
            elif self.capProject and not self.capEditor:
                self.setWindowTitle(
                    self.tr("{0} - {1} - Passive Mode").format(
                        self.capProject, "eric-ide"
                    )
                )
            elif not self.capProject and self.capEditor:
                self.setWindowTitle(
                    self.tr("{0} - {1} - Passive Mode").format(
                        self.capEditor, "eric-ide"
                    )
                )
            else:
                self.setWindowTitle(
                    self.tr("{0} - {1} - {2} - Passive Mode").format(
                        self.capProject, self.capEditor, "eric-ide"
                    )
                )
        else:
            if not self.capProject and not self.capEditor:
                self.setWindowTitle("eric-ide")
            elif self.capProject and not self.capEditor:
                self.setWindowTitle("{0} - {1}".format(self.capProject, "eric-ide"))
            elif not self.capProject and self.capEditor:
                self.setWindowTitle("{0} - {1}".format(self.capEditor, "eric-ide"))
            else:
                self.setWindowTitle(
                    "{0} - {1} - {2}".format(
                        self.capProject, self.capEditor, "eric-ide"
                    )
                )

    def __initActions(self):
        """
        Private method to define the user interface actions.
        """
        self.actions = []
        self.wizardsActions = []

        self.exitAct = EricAction(
            self.tr("Quit"),
            EricPixmapCache.getIcon("exit"),
            self.tr("&Quit"),
            QKeySequence(self.tr("Ctrl+Q", "File|Quit")),
            0,
            self,
            "quit",
        )
        self.exitAct.setStatusTip(self.tr("Quit the IDE"))
        self.exitAct.setWhatsThis(
            self.tr(
                """<b>Quit the IDE</b>"""
                """<p>This quits the IDE. Any unsaved changes may be saved"""
                """ first. Any Python program being debugged will be stopped"""
                """ and the preferences will be written to disc.</p>"""
            )
        )
        self.exitAct.triggered.connect(self.__quit)
        self.exitAct.setMenuRole(QAction.MenuRole.QuitRole)
        self.actions.append(self.exitAct)

        self.restartAct = EricAction(
            self.tr("Restart"),
            EricPixmapCache.getIcon("restart"),
            self.tr("Restart"),
            QKeySequence(self.tr("Ctrl+Shift+Q", "File|Quit")),
            0,
            self,
            "restart_eric",
        )
        self.restartAct.setStatusTip(self.tr("Restart the IDE"))
        self.restartAct.setWhatsThis(
            self.tr(
                """<b>Restart the IDE</b>"""
                """<p>This restarts the IDE. Any unsaved changes may be saved"""
                """ first. Any Python program being debugged will be stopped"""
                """ and the preferences will be written to disc.</p>"""
            )
        )
        self.restartAct.triggered.connect(self.__restart)
        self.actions.append(self.restartAct)

        self.saveSessionAct = EricAction(
            self.tr("Save session"),
            self.tr("Save session..."),
            0,
            0,
            self,
            "save_session_to_file",
        )
        self.saveSessionAct.setStatusTip(self.tr("Save session"))
        self.saveSessionAct.setWhatsThis(
            self.tr(
                """<b>Save session...</b>"""
                """<p>This saves the current session to disk. A dialog is"""
                """ opened to select the file name.</p>"""
            )
        )
        self.saveSessionAct.triggered.connect(self.__saveSessionToFile)
        self.actions.append(self.saveSessionAct)

        self.loadSessionAct = EricAction(
            self.tr("Load session"),
            self.tr("Load session..."),
            0,
            0,
            self,
            "load_session_from_file",
        )
        self.loadSessionAct.setStatusTip(self.tr("Load session"))
        self.loadSessionAct.setWhatsThis(
            self.tr(
                """<b>Load session...</b>"""
                """<p>This loads a session saved to disk previously. A dialog is"""
                """ opened to select the file name.</p>"""
            )
        )
        self.loadSessionAct.triggered.connect(self.__loadSessionFromFile)
        self.actions.append(self.loadSessionAct)

        self.newWindowAct = EricAction(
            self.tr("New Window"),
            EricPixmapCache.getIcon("newWindow"),
            self.tr("New &Window"),
            QKeySequence(self.tr("Ctrl+Shift+N", "File|New Window")),
            0,
            self,
            "new_window",
        )
        self.newWindowAct.setStatusTip(self.tr("Open a new eric instance"))
        self.newWindowAct.setWhatsThis(
            self.tr(
                """<b>New Window</b>"""
                """<p>This opens a new instance of the eric IDE.</p>"""
            )
        )
        self.newWindowAct.triggered.connect(self.__newWindow)
        self.actions.append(self.newWindowAct)
        self.newWindowAct.setEnabled(not Preferences.getUI("SingleApplicationMode"))

        self.viewProfileActGrp = createActionGroup(self, "viewprofiles", True)

        self.setEditProfileAct = EricAction(
            self.tr("Edit Profile"),
            EricPixmapCache.getIcon("viewProfileEdit"),
            self.tr("Edit Profile"),
            0,
            0,
            self.viewProfileActGrp,
            "edit_profile",
            True,
        )
        self.setEditProfileAct.setStatusTip(self.tr("Activate the edit view profile"))
        self.setEditProfileAct.setWhatsThis(
            self.tr(
                """<b>Edit Profile</b>"""
                """<p>Activate the "Edit View Profile". Windows being shown,"""
                """ if this profile is active, may be configured with the"""
                """ "View Profile Configuration" dialog.</p>"""
            )
        )
        self.setEditProfileAct.triggered.connect(self.__setEditProfile)
        self.actions.append(self.setEditProfileAct)

        self.setDebugProfileAct = EricAction(
            self.tr("Debug Profile"),
            EricPixmapCache.getIcon("viewProfileDebug"),
            self.tr("Debug Profile"),
            0,
            0,
            self.viewProfileActGrp,
            "debug_profile",
            True,
        )
        self.setDebugProfileAct.setStatusTip(self.tr("Activate the debug view profile"))
        self.setDebugProfileAct.setWhatsThis(
            self.tr(
                """<b>Debug Profile</b>"""
                """<p>Activate the "Debug View Profile". Windows being shown,"""
                """ if this profile is active, may be configured with the"""
                """ "View Profile Configuration" dialog.</p>"""
            )
        )
        self.setDebugProfileAct.triggered.connect(self.setDebugProfile)
        self.actions.append(self.setDebugProfileAct)

        self.pbActivateAct = EricAction(
            self.tr("Project-Viewer"),
            self.tr("&Project-Viewer"),
            QKeySequence(self.tr("Alt+Shift+P")),
            0,
            self,
            "project_viewer_activate",
        )
        self.pbActivateAct.setStatusTip(
            self.tr("Switch the input focus to the Project-Viewer window.")
        )
        self.pbActivateAct.setWhatsThis(
            self.tr(
                """<b>Activate Project-Viewer</b>"""
                """<p>This switches the input focus to the Project-Viewer"""
                """ window.</p>"""
            )
        )
        self.pbActivateAct.triggered.connect(self.__activateProjectBrowser)
        self.actions.append(self.pbActivateAct)
        self.addAction(self.pbActivateAct)

        self.mpbActivateAct = EricAction(
            self.tr("Multiproject-Viewer"),
            self.tr("&Multiproject-Viewer"),
            QKeySequence(self.tr("Alt+Shift+M")),
            0,
            self,
            "multi_project_viewer_activate",
        )
        self.mpbActivateAct.setStatusTip(
            self.tr("Switch the input focus to the Multiproject-Viewer window.")
        )
        self.mpbActivateAct.setWhatsThis(
            self.tr(
                """<b>Activate Multiproject-Viewer</b>"""
                """<p>This switches the input focus to the Multiproject-Viewer"""
                """ window.</p>"""
            )
        )
        self.mpbActivateAct.triggered.connect(self.__activateMultiProjectBrowser)
        self.actions.append(self.mpbActivateAct)
        self.addAction(self.mpbActivateAct)

        self.debugViewerActivateAct = EricAction(
            self.tr("Debug-Viewer"),
            self.tr("&Debug-Viewer"),
            QKeySequence(self.tr("Alt+Shift+D")),
            0,
            self,
            "debug_viewer_activate",
        )
        self.debugViewerActivateAct.setStatusTip(
            self.tr("Switch the input focus to the Debug-Viewer window.")
        )
        self.debugViewerActivateAct.setWhatsThis(
            self.tr(
                """<b>Activate Debug-Viewer</b>"""
                """<p>This switches the input focus to the Debug-Viewer"""
                """ window.</p>"""
            )
        )
        self.debugViewerActivateAct.triggered.connect(self.activateDebugViewer)
        self.actions.append(self.debugViewerActivateAct)
        self.addAction(self.debugViewerActivateAct)

        self.shellActivateAct = EricAction(
            self.tr("Shell"),
            self.tr("&Shell"),
            QKeySequence(self.tr("Alt+Shift+S")),
            0,
            self,
            "interpreter_shell_activate",
        )
        self.shellActivateAct.setStatusTip(
            self.tr("Switch the input focus to the Shell window.")
        )
        self.shellActivateAct.setWhatsThis(
            self.tr(
                """<b>Activate Shell</b>"""
                """<p>This switches the input focus to the Shell window.</p>"""
            )
        )
        self.shellActivateAct.triggered.connect(self.__activateShell)
        self.actions.append(self.shellActivateAct)
        self.addAction(self.shellActivateAct)

        if self.browser is not None:
            self.browserActivateAct = EricAction(
                self.tr("File-Browser"),
                self.tr("&File-Browser"),
                QKeySequence(self.tr("Alt+Shift+F")),
                0,
                self,
                "file_browser_activate",
            )
            self.browserActivateAct.setStatusTip(
                self.tr("Switch the input focus to the File-Browser window.")
            )
            self.browserActivateAct.setWhatsThis(
                self.tr(
                    """<b>Activate File-Browser</b>"""
                    """<p>This switches the input focus to the File-Browser"""
                    """ window.</p>"""
                )
            )
            self.browserActivateAct.triggered.connect(self.__activateBrowser)
            self.actions.append(self.browserActivateAct)
            self.addAction(self.browserActivateAct)

        self.logViewerActivateAct = EricAction(
            self.tr("Log-Viewer"),
            self.tr("Lo&g-Viewer"),
            QKeySequence(self.tr("Alt+Shift+G")),
            0,
            self,
            "log_viewer_activate",
        )
        self.logViewerActivateAct.setStatusTip(
            self.tr("Switch the input focus to the Log-Viewer window.")
        )
        self.logViewerActivateAct.setWhatsThis(
            self.tr(
                """<b>Activate Log-Viewer</b>"""
                """<p>This switches the input focus to the Log-Viewer"""
                """ window.</p>"""
            )
        )
        self.logViewerActivateAct.triggered.connect(self.__activateLogViewer)
        self.actions.append(self.logViewerActivateAct)
        self.addAction(self.logViewerActivateAct)

        self.taskViewerActivateAct = EricAction(
            self.tr("Task-Viewer"),
            self.tr("&Task-Viewer"),
            QKeySequence(self.tr("Alt+Shift+T")),
            0,
            self,
            "task_viewer_activate",
        )
        self.taskViewerActivateAct.setStatusTip(
            self.tr("Switch the input focus to the Task-Viewer window.")
        )
        self.taskViewerActivateAct.setWhatsThis(
            self.tr(
                """<b>Activate Task-Viewer</b>"""
                """<p>This switches the input focus to the Task-Viewer"""
                """ window.</p>"""
            )
        )
        self.taskViewerActivateAct.triggered.connect(self.__activateTaskViewer)
        self.actions.append(self.taskViewerActivateAct)
        self.addAction(self.taskViewerActivateAct)

        if self.templateViewer is not None:
            self.templateViewerActivateAct = EricAction(
                self.tr("Template-Viewer"),
                self.tr("Templ&ate-Viewer"),
                QKeySequence(self.tr("Alt+Shift+A")),
                0,
                self,
                "template_viewer_activate",
            )
            self.templateViewerActivateAct.setStatusTip(
                self.tr("Switch the input focus to the Template-Viewer window.")
            )
            self.templateViewerActivateAct.setWhatsThis(
                self.tr(
                    """<b>Activate Template-Viewer</b>"""
                    """<p>This switches the input focus to the Template-Viewer"""
                    """ window.</p>"""
                )
            )
            self.templateViewerActivateAct.triggered.connect(
                self.__activateTemplateViewer
            )
            self.actions.append(self.templateViewerActivateAct)
            self.addAction(self.templateViewerActivateAct)

        if self.lToolbox:
            self.ltAct = EricAction(
                self.tr("Left Toolbox"),
                self.tr("&Left Toolbox"),
                0,
                0,
                self,
                "vertical_toolbox",
                True,
            )
            self.ltAct.setStatusTip(self.tr("Toggle the Left Toolbox window"))
            self.ltAct.setWhatsThis(
                self.tr(
                    """<b>Toggle the Left Toolbox window</b>"""
                    """<p>If the Left Toolbox window is hidden then display it."""
                    """ If it is displayed then close it.</p>"""
                )
            )
            self.ltAct.triggered.connect(self.__toggleLeftToolbox)
            self.actions.append(self.ltAct)
        else:
            self.ltAct = None

        if self.rToolbox:
            self.rtAct = EricAction(
                self.tr("Right Toolbox"),
                self.tr("&Right Toolbox"),
                0,
                0,
                self,
                "vertical_toolbox",
                True,
            )
            self.rtAct.setStatusTip(self.tr("Toggle the Right Toolbox window"))
            self.rtAct.setWhatsThis(
                self.tr(
                    """<b>Toggle the Right Toolbox window</b>"""
                    """<p>If the Right Toolbox window is hidden then display it."""
                    """ If it is displayed then close it.</p>"""
                )
            )
            self.rtAct.triggered.connect(self.__toggleRightToolbox)
            self.actions.append(self.rtAct)
        else:
            self.rtAct = None

        if self.hToolbox:
            self.htAct = EricAction(
                self.tr("Horizontal Toolbox"),
                self.tr("&Horizontal Toolbox"),
                0,
                0,
                self,
                "horizontal_toolbox",
                True,
            )
            self.htAct.setStatusTip(self.tr("Toggle the Horizontal Toolbox window"))
            self.htAct.setWhatsThis(
                self.tr(
                    """<b>Toggle the Horizontal Toolbox window</b>"""
                    """<p>If the Horizontal Toolbox window is hidden then"""
                    """ display it. If it is displayed then close it.</p>"""
                )
            )
            self.htAct.triggered.connect(self.__toggleHorizontalToolbox)
            self.actions.append(self.htAct)
        else:
            self.htAct = None

        if self.leftSidebar:
            self.lsbAct = EricAction(
                self.tr("Left Sidebar"),
                self.tr("&Left Sidebar"),
                0,
                0,
                self,
                "left_sidebar",
                True,
            )
            self.lsbAct.setStatusTip(self.tr("Toggle the left sidebar window"))
            self.lsbAct.setWhatsThis(
                self.tr(
                    """<b>Toggle the left sidebar window</b>"""
                    """<p>If the left sidebar window is hidden then display it."""
                    """ If it is displayed then close it.</p>"""
                )
            )
            self.lsbAct.triggered.connect(self.__toggleLeftSidebar)
            self.actions.append(self.lsbAct)
        else:
            self.lsbAct = None

        if self.rightSidebar:
            self.rsbAct = EricAction(
                self.tr("Right Sidebar"),
                self.tr("&Right Sidebar"),
                0,
                0,
                self,
                "right_sidebar",
                True,
            )
            self.rsbAct.setStatusTip(self.tr("Toggle the right sidebar window"))
            self.rsbAct.setWhatsThis(
                self.tr(
                    """<b>Toggle the right sidebar window</b>"""
                    """<p>If the right sidebar window is hidden then display it."""
                    """ If it is displayed then close it.</p>"""
                )
            )
            self.rsbAct.triggered.connect(self.__toggleRightSidebar)
            self.actions.append(self.rsbAct)
        else:
            self.rsbAct = None

        if self.bottomSidebar:
            self.bsbAct = EricAction(
                self.tr("Bottom Sidebar"),
                self.tr("&Bottom Sidebar"),
                0,
                0,
                self,
                "bottom_sidebar",
                True,
            )
            self.bsbAct.setStatusTip(self.tr("Toggle the bottom sidebar window"))
            self.bsbAct.setWhatsThis(
                self.tr(
                    """<b>Toggle the bottom sidebar window</b>"""
                    """<p>If the bottom sidebar window is hidden then display"""
                    """ it. If it is displayed then close it.</p>"""
                )
            )
            self.bsbAct.triggered.connect(self.__toggleBottomSidebar)
            self.actions.append(self.bsbAct)
        else:
            self.bsbAct = None

        if self.cooperation is not None:
            self.cooperationViewerActivateAct = EricAction(
                self.tr("Cooperation-Viewer"),
                self.tr("Co&operation-Viewer"),
                QKeySequence(self.tr("Alt+Shift+O")),
                0,
                self,
                "cooperation_viewer_activate",
            )
            self.cooperationViewerActivateAct.setStatusTip(
                self.tr("Switch the input focus to the Cooperation-Viewer window.")
            )
            self.cooperationViewerActivateAct.setWhatsThis(
                self.tr(
                    """<b>Activate Cooperation-Viewer</b>"""
                    """<p>This switches the input focus to the"""
                    """ Cooperation-Viewer window.</p>"""
                )
            )
            self.cooperationViewerActivateAct.triggered.connect(
                self.activateCooperationViewer
            )
            self.actions.append(self.cooperationViewerActivateAct)
            self.addAction(self.cooperationViewerActivateAct)

        if self.irc is not None:
            self.ircActivateAct = EricAction(
                self.tr("IRC"),
                self.tr("&IRC"),
                QKeySequence(self.tr("Ctrl+Alt+Shift+I")),
                0,
                self,
                "irc_widget_activate",
            )
            self.ircActivateAct.setStatusTip(
                self.tr("Switch the input focus to the IRC window.")
            )
            self.ircActivateAct.setWhatsThis(
                self.tr(
                    """<b>Activate IRC</b>"""
                    """<p>This switches the input focus to the IRC window.</p>"""
                )
            )
            self.ircActivateAct.triggered.connect(self.__activateIRC)
            self.actions.append(self.ircActivateAct)
            self.addAction(self.ircActivateAct)

        if self.symbolsViewer is not None:
            self.symbolsViewerActivateAct = EricAction(
                self.tr("Symbols-Viewer"),
                self.tr("S&ymbols-Viewer"),
                QKeySequence(self.tr("Alt+Shift+Y")),
                0,
                self,
                "symbols_viewer_activate",
            )
            self.symbolsViewerActivateAct.setStatusTip(
                self.tr("Switch the input focus to the Symbols-Viewer window.")
            )
            self.symbolsViewerActivateAct.setWhatsThis(
                self.tr(
                    """<b>Activate Symbols-Viewer</b>"""
                    """<p>This switches the input focus to the Symbols-Viewer"""
                    """ window.</p>"""
                )
            )
            self.symbolsViewerActivateAct.triggered.connect(
                self.__activateSymbolsViewer
            )
            self.actions.append(self.symbolsViewerActivateAct)
            self.addAction(self.symbolsViewerActivateAct)

        if self.numbersViewer is not None:
            self.numbersViewerActivateAct = EricAction(
                self.tr("Numbers-Viewer"),
                self.tr("Num&bers-Viewer"),
                QKeySequence(self.tr("Alt+Shift+B")),
                0,
                self,
                "numbers_viewer_activate",
            )
            self.numbersViewerActivateAct.setStatusTip(
                self.tr("Switch the input focus to the Numbers-Viewer window.")
            )
            self.numbersViewerActivateAct.setWhatsThis(
                self.tr(
                    """<b>Activate Numbers-Viewer</b>"""
                    """<p>This switches the input focus to the Numbers-Viewer"""
                    """ window.</p>"""
                )
            )
            self.numbersViewerActivateAct.triggered.connect(
                self.__activateNumbersViewer
            )
            self.actions.append(self.numbersViewerActivateAct)
            self.addAction(self.numbersViewerActivateAct)

        if self.codeDocumentationViewer is not None:
            self.codeDocumentationViewerActivateAct = EricAction(
                self.tr("Code Documentation Viewer"),
                self.tr("Code Documentation Viewer"),
                QKeySequence(self.tr("Ctrl+Alt+Shift+D")),
                0,
                self,
                "code_documentation_viewer_activate",
            )
            self.codeDocumentationViewerActivateAct.setStatusTip(
                self.tr(
                    "Switch the input focus to the Code Documentation Viewer window."
                )
            )
            self.codeDocumentationViewerActivateAct.setWhatsThis(
                self.tr(
                    """<b>Code Documentation Viewer</b>"""
                    """<p>This switches the input focus to the Code"""
                    """ Documentation Viewer window.</p>"""
                )
            )
            self.codeDocumentationViewerActivateAct.triggered.connect(
                self.activateCodeDocumentationViewer
            )
            self.actions.append(self.codeDocumentationViewerActivateAct)
            self.addAction(self.codeDocumentationViewerActivateAct)

        if self.pipWidget is not None:
            self.pipWidgetActivateAct = EricAction(
                self.tr("PyPI Package Management"),
                self.tr("PyPI Package Management"),
                QKeySequence(self.tr("Ctrl+Alt+Shift+P")),
                0,
                self,
                "pip_widget_activate",
            )
            self.pipWidgetActivateAct.setStatusTip(
                self.tr("Switch the input focus to the PyPI Package Management window.")
            )
            self.pipWidgetActivateAct.setWhatsThis(
                self.tr(
                    """<b>PyPI</b>"""
                    """<p>This switches the input focus to the PyPI window.</p>"""
                )
            )
            self.pipWidgetActivateAct.triggered.connect(self.__activatePipWidget)
            self.actions.append(self.pipWidgetActivateAct)
            self.addAction(self.pipWidgetActivateAct)

        if self.condaWidget is not None:
            self.condaWidgetActivateAct = EricAction(
                self.tr("Conda"),
                self.tr("Conda"),
                QKeySequence(self.tr("Ctrl+Alt+Shift+C")),
                0,
                self,
                "conda_widget_activate",
            )
            self.condaWidgetActivateAct.setStatusTip(
                self.tr("Switch the input focus to the Conda window.")
            )
            self.condaWidgetActivateAct.setWhatsThis(
                self.tr(
                    """<b>Conda</b>"""
                    """<p>This switches the input focus to the Conda window.</p>"""
                )
            )
            self.condaWidgetActivateAct.triggered.connect(self.__activateCondaWidget)
            self.actions.append(self.condaWidgetActivateAct)
            self.addAction(self.condaWidgetActivateAct)

        if self.microPythonWidget is not None:
            self.microPythonWidgetActivateAct = EricAction(
                self.tr("MicroPython"),
                self.tr("MicroPython"),
                QKeySequence(self.tr("Ctrl+Alt+Shift+M")),
                0,
                self,
                "micropython_widget_activate",
            )
            self.microPythonWidgetActivateAct.setStatusTip(
                self.tr("Switch the input focus to the MicroPython window.")
            )
            self.microPythonWidgetActivateAct.setWhatsThis(
                self.tr(
                    """<b>MicroPython</b>"""
                    """<p>This switches the input focus to the MicroPython"""
                    """ window.</p>"""
                )
            )
            self.microPythonWidgetActivateAct.triggered.connect(
                self.__activateMicroPython
            )
            self.actions.append(self.microPythonWidgetActivateAct)
            self.addAction(self.microPythonWidgetActivateAct)

        self.pluginRepositoryViewerActivateAct = EricAction(
            self.tr("Plugin Repository"),
            self.tr("Plugin Repository"),
            QKeySequence(self.tr("Ctrl+Alt+Shift+R")),
            0,
            self,
            "plugin_repository_viewer_activate",
        )
        self.pluginRepositoryViewerActivateAct.setStatusTip(
            self.tr("Switch the input focus to the Plugin Repository window.")
        )
        self.pluginRepositoryViewerActivateAct.setWhatsThis(
            self.tr(
                """<b>Plugin Repository</b>"""
                """<p>This switches the input focus to the Plugin Repository"""
                """ window.</p>"""
            )
        )
        self.pluginRepositoryViewerActivateAct.triggered.connect(
            self.activatePluginRepositoryViewer
        )
        self.actions.append(self.pluginRepositoryViewerActivateAct)
        self.addAction(self.pluginRepositoryViewerActivateAct)

        self.virtualenvManagerActivateAct = EricAction(
            self.tr("Virtual Environments"),
            self.tr("Virtual Environments"),
            QKeySequence(self.tr("Ctrl+Alt+V")),
            0,
            self,
            "virtualenv_manager_activate",
        )
        self.virtualenvManagerActivateAct.setStatusTip(
            self.tr(
                "Switch the input focus to the Virtual Environments Manager window."
            )
        )
        self.virtualenvManagerActivateAct.setWhatsThis(
            self.tr(
                """<b>Virtual Environments</b>"""
                """<p>This switches the input focus to the Virtual Environments"""
                """ Manager window.</p>"""
            )
        )
        self.virtualenvManagerActivateAct.triggered.connect(
            self.activateVirtualenvManager
        )
        self.actions.append(self.virtualenvManagerActivateAct)
        self.addAction(self.virtualenvManagerActivateAct)

        if self.__findFileWidget is not None:
            self.findFileActivateAct = EricAction(
                self.tr("Find/Replace In Files"),
                self.tr("Find/Replace In Files"),
                QKeySequence(self.tr("Ctrl+Alt+Shift+F")),
                0,
                self,
                "find_file_activate",
            )
            self.findFileActivateAct.setStatusTip(
                self.tr("Switch the input focus to the Find/Replace In Files window.")
            )
            self.findFileActivateAct.setWhatsThis(
                self.tr(
                    """<b>Find/Replace In Files</b>"""
                    """<p>This switches the input focus to the Find/Replace In"""
                    """ Files window.</p>"""
                )
            )
            self.findFileActivateAct.triggered.connect(self.__activateFindFileWidget)
            self.actions.append(self.findFileActivateAct)
            self.addAction(self.findFileActivateAct)

        if self.__findLocationWidget is not None:
            self.findLocationActivateAct = EricAction(
                self.tr("Find File"),
                self.tr("Find File"),
                QKeySequence(self.tr("Ctrl+Alt+Shift+L")),
                0,
                self,
                "find_location_activate",
            )
            self.findLocationActivateAct.setStatusTip(
                self.tr("Switch the input focus to the Find File window.")
            )
            self.findLocationActivateAct.setWhatsThis(
                self.tr(
                    """<b>Find File</b>"""
                    """<p>This switches the input focus to the Find File window."""
                    """</p>"""
                )
            )
            self.findLocationActivateAct.triggered.connect(
                self.__activateFindLocationWidget
            )
            self.actions.append(self.findLocationActivateAct)
            self.addAction(self.findLocationActivateAct)

        self.vcsStatusListActivateAct = EricAction(
            self.tr("VCS Status List"),
            self.tr("VCS Status List"),
            QKeySequence(self.tr("Alt+Shift+V")),
            0,
            self,
            "vcs_status_list_activate",
        )
        self.vcsStatusListActivateAct.setStatusTip(
            self.tr("Switch the input focus to the VCS Status List window.")
        )
        self.vcsStatusListActivateAct.setWhatsThis(
            self.tr(
                """<b>VCS Status List</b>"""
                """<p>This switches the input focus to the VCS Status List"""
                """ window.</p>"""
            )
        )
        self.vcsStatusListActivateAct.triggered.connect(self.__activateVcsStatusList)
        self.actions.append(self.vcsStatusListActivateAct)
        self.addAction(self.vcsStatusListActivateAct)

        self.helpViewerActivateAct = EricAction(
            self.tr("Help Viewer"),
            self.tr("Help Viewer"),
            QKeySequence(self.tr("Alt+Shift+H")),
            0,
            self,
            "help_viewer_activate",
        )
        self.helpViewerActivateAct.setStatusTip(
            self.tr("Switch the input focus to the embedded Help Viewer window.")
        )
        self.helpViewerActivateAct.setWhatsThis(
            self.tr(
                """<b>Help Viewer</b>"""
                """<p>This switches the input focus to the embedded Help Viewer"""
                """ window. It will show HTML help files and help from Qt help"""
                """ collections.</p><p>If called with a word selected, this word"""
                """ is searched in the Qt help collection.</p>"""
            )
        )
        self.helpViewerActivateAct.triggered.connect(self.__activateHelpViewerWidget)
        self.actions.append(self.helpViewerActivateAct)
        self.addAction(self.helpViewerActivateAct)

        self.whatsThisAct = EricAction(
            self.tr("What's This?"),
            EricPixmapCache.getIcon("whatsThis"),
            self.tr("&What's This?"),
            QKeySequence(self.tr("Shift+F1")),
            0,
            self,
            "whatsThis",
        )
        self.whatsThisAct.setStatusTip(self.tr("Context sensitive help"))
        self.whatsThisAct.setWhatsThis(
            self.tr(
                """<b>Display context sensitive help</b>"""
                """<p>In What's This? mode, the mouse cursor shows an arrow with"""
                """ a question mark, and you can click on the interface elements"""
                """ to get a short description of what they do and how to use"""
                """ them. In dialogs, this feature can be accessed using the"""
                """ context help button in the titlebar.</p>"""
            )
        )
        self.whatsThisAct.triggered.connect(self.__whatsThis)
        self.actions.append(self.whatsThisAct)

        self.helpviewerAct = EricAction(
            self.tr("Helpviewer"),
            EricPixmapCache.getIcon("help"),
            self.tr("&Helpviewer..."),
            QKeySequence(self.tr("F1")),
            0,
            self,
            "helpviewer",
        )
        self.helpviewerAct.setStatusTip(self.tr("Open the helpviewer window"))
        self.helpviewerAct.setWhatsThis(
            self.tr(
                """<b>Helpviewer</b>"""
                """<p>Display the eric web browser. This window will show"""
                """ HTML help files and help from Qt help collections. It"""
                """ has the capability to navigate to links, set bookmarks,"""
                """ print the displayed help and some more features. You may"""
                """ use it to browse the internet as well</p><p>If called"""
                """ with a word selected, this word is searched in the Qt help"""
                """ collection.</p>"""
            )
        )
        self.helpviewerAct.triggered.connect(self.__helpViewer)
        self.actions.append(self.helpviewerAct)

        self.__initQtDocActions()
        self.__initPythonDocActions()
        self.__initEricDocAction()
        self.__initPySideDocActions()

        self.versionAct = EricAction(
            self.tr("Show Versions"),
            self.tr("Show &Versions"),
            0,
            0,
            self,
            "show_versions",
        )
        self.versionAct.setStatusTip(self.tr("Display version information"))
        self.versionAct.setWhatsThis(
            self.tr("""<b>Show Versions</b><p>Display version information.</p>""")
        )
        self.versionAct.triggered.connect(self.__showVersions)
        self.actions.append(self.versionAct)

        self.copyVersionAct = EricAction(
            self.tr("Copy Versions"),
            self.tr("&Copy Versions"),
            0,
            0,
            self,
            "copy_versions",
        )
        self.copyVersionAct.setStatusTip(
            self.tr("Copy version information to the clipboard")
        )
        self.copyVersionAct.setWhatsThis(
            self.tr(
                "<b>Copy Versions</b><p>This generates version information and copies"
                " it to the clipboard.</p>"
            )
        )
        self.copyVersionAct.triggered.connect(self.__copyVersions)
        self.actions.append(self.copyVersionAct)

        self.showErrorLogAct = EricAction(
            self.tr("Show Error Log"),
            self.tr("Show Error &Log..."),
            0,
            0,
            self,
            "show_error_log",
        )
        self.showErrorLogAct.setStatusTip(self.tr("Show Error Log"))
        self.showErrorLogAct.setWhatsThis(
            self.tr(
                """<b>Show Error Log...</b>"""
                """<p>Opens a dialog showing the most recent error log.</p>"""
            )
        )
        self.showErrorLogAct.triggered.connect(self.__showErrorLog)
        self.actions.append(self.showErrorLogAct)

        self.showInstallInfoAct = EricAction(
            self.tr("Show Install Info"),
            self.tr("Show Install &Info..."),
            0,
            0,
            self,
            "show_install_info",
        )
        self.showInstallInfoAct.setStatusTip(self.tr("Show Installation Information"))
        self.showInstallInfoAct.setWhatsThis(
            self.tr(
                """<b>Show Install Info...</b>"""
                """<p>Opens a dialog showing some information about the"""
                """ installation process.</p>"""
            )
        )
        self.showInstallInfoAct.triggered.connect(self.__showInstallInfo)
        self.actions.append(self.showInstallInfoAct)

        self.reportBugAct = EricAction(
            self.tr("Report Bug"), self.tr("Report &Bug..."), 0, 0, self, "report_bug"
        )
        self.reportBugAct.setStatusTip(self.tr("Report a bug"))
        self.reportBugAct.setWhatsThis(
            self.tr("""<b>Report Bug...</b><p>Opens a dialog to report a bug.</p>""")
        )
        self.reportBugAct.triggered.connect(self.__reportBug)
        self.actions.append(self.reportBugAct)

        self.requestFeatureAct = EricAction(
            self.tr("Request Feature"),
            self.tr("Request &Feature..."),
            0,
            0,
            self,
            "request_feature",
        )
        self.requestFeatureAct.setStatusTip(self.tr("Send a feature request"))
        self.requestFeatureAct.setWhatsThis(
            self.tr(
                """<b>Request Feature...</b>"""
                """<p>Opens a dialog to send a feature request.</p>"""
            )
        )
        self.requestFeatureAct.triggered.connect(self.__requestFeature)
        self.actions.append(self.requestFeatureAct)

        self.testingActGrp = createActionGroup(self)

        self.testingDialogAct = EricAction(
            self.tr("Testing"),
            EricPixmapCache.getIcon("unittest"),
            self.tr("&Testing..."),
            0,
            0,
            self.testingActGrp,
            "unittest",
        )
        self.testingDialogAct.setStatusTip(self.tr("Start the testing dialog"))
        self.testingDialogAct.setWhatsThis(
            self.tr(
                """<b>Testing</b>"""
                """<p>Perform test runs. The dialog gives the"""
                """ ability to select and run a test suite or"""
                """ auto discover them.</p>"""
            )
        )
        self.testingDialogAct.triggered.connect(self.__startTesting)
        self.actions.append(self.testingDialogAct)

        self.restartTestAct = EricAction(
            self.tr("Restart Last Test"),
            EricPixmapCache.getIcon("unittestRestart"),
            self.tr("&Restart Last Test..."),
            0,
            0,
            self.testingActGrp,
            "unittest_restart",
        )
        self.restartTestAct.setStatusTip(self.tr("Restarts the last test"))
        self.restartTestAct.setWhatsThis(
            self.tr(
                """<b>Restart Last Test</b>"""
                """<p>Restarts the test performed last.</p>"""
            )
        )
        self.restartTestAct.triggered.connect(self.__restartTest)
        self.restartTestAct.setEnabled(False)
        self.actions.append(self.restartTestAct)

        self.rerunFailedTestsAct = EricAction(
            self.tr("Rerun Failed Tests"),
            EricPixmapCache.getIcon("unittestRerunFailed"),
            self.tr("Rerun Failed Tests..."),
            0,
            0,
            self.testingActGrp,
            "unittest_rerun_failed",
        )
        self.rerunFailedTestsAct.setStatusTip(
            self.tr("Rerun failed tests of the last run")
        )
        self.rerunFailedTestsAct.setWhatsThis(
            self.tr(
                """<b>Rerun Failed Tests</b>"""
                """<p>Rerun all tests that failed during the last test run.</p>"""
            )
        )
        self.rerunFailedTestsAct.triggered.connect(self.__rerunFailedTests)
        self.rerunFailedTestsAct.setEnabled(False)
        self.actions.append(self.rerunFailedTestsAct)

        self.testScriptAct = EricAction(
            self.tr("Test Script"),
            EricPixmapCache.getIcon("unittestScript"),
            self.tr("Test &Script..."),
            0,
            0,
            self.testingActGrp,
            "unittest_script",
        )
        self.testScriptAct.setStatusTip(self.tr("Run tests of the current script"))
        self.testScriptAct.setWhatsThis(
            self.tr("""<b>Test Script</b><p>Run tests with the current script.</p>""")
        )
        self.testScriptAct.triggered.connect(self.__startTestScript)
        self.testScriptAct.setEnabled(False)
        self.actions.append(self.testScriptAct)

        self.testProjectAct = EricAction(
            self.tr("Test Project"),
            EricPixmapCache.getIcon("unittestProject"),
            self.tr("Test &Project..."),
            0,
            0,
            self.testingActGrp,
            "unittest_project",
        )
        self.testProjectAct.setStatusTip(self.tr("Run tests of the current project"))
        self.testProjectAct.setWhatsThis(
            self.tr("""<b>Test Project</b><p>Run test of the current project.</p>""")
        )
        self.testProjectAct.triggered.connect(self.__startTestProject)
        self.testProjectAct.setEnabled(False)
        self.actions.append(self.testProjectAct)

        # check for Qt6 designer and linguist
        if QtUtilities.hasQtDesigner():
            self.designer4Act = EricAction(
                self.tr("Qt-Designer"),
                EricPixmapCache.getIcon("designer4"),
                self.tr("Qt-&Designer..."),
                0,
                0,
                self,
                "qt_designer4",
            )
            self.designer4Act.setStatusTip(self.tr("Start Qt-Designer"))
            self.designer4Act.setWhatsThis(
                self.tr("""<b>Qt-Designer</b><p>Start Qt-Designer.</p>""")
            )
            self.designer4Act.triggered.connect(self.__designer)
            self.actions.append(self.designer4Act)
        else:
            self.designer4Act = None

        if QtUtilities.hasQtLinguist():
            self.linguist4Act = EricAction(
                self.tr("Qt-Linguist"),
                EricPixmapCache.getIcon("linguist4"),
                self.tr("Qt-&Linguist..."),
                0,
                0,
                self,
                "qt_linguist4",
            )
            self.linguist4Act.setStatusTip(self.tr("Start Qt-Linguist"))
            self.linguist4Act.setWhatsThis(
                self.tr("""<b>Qt-Linguist</b><p>Start Qt-Linguist.</p>""")
            )
            self.linguist4Act.triggered.connect(self.__linguist)
            self.actions.append(self.linguist4Act)
        else:
            self.linguist4Act = None

        self.uipreviewerAct = EricAction(
            self.tr("UI Previewer"),
            EricPixmapCache.getIcon("uiPreviewer"),
            self.tr("&UI Previewer..."),
            0,
            0,
            self,
            "ui_previewer",
        )
        self.uipreviewerAct.setStatusTip(self.tr("Start the UI Previewer"))
        self.uipreviewerAct.setWhatsThis(
            self.tr("""<b>UI Previewer</b><p>Start the UI Previewer.</p>""")
        )
        self.uipreviewerAct.triggered.connect(self.__UIPreviewer)
        self.actions.append(self.uipreviewerAct)

        self.trpreviewerAct = EricAction(
            self.tr("Translations Previewer"),
            EricPixmapCache.getIcon("trPreviewer"),
            self.tr("&Translations Previewer..."),
            0,
            0,
            self,
            "tr_previewer",
        )
        self.trpreviewerAct.setStatusTip(self.tr("Start the Translations Previewer"))
        self.trpreviewerAct.setWhatsThis(
            self.tr(
                """<b>Translations Previewer</b>"""
                """<p>Start the Translations Previewer.</p>"""
            )
        )
        self.trpreviewerAct.triggered.connect(self.__TRPreviewer)
        self.actions.append(self.trpreviewerAct)

        self.diffAct = EricAction(
            self.tr("Compare Files"),
            EricPixmapCache.getIcon("diffFiles"),
            self.tr("&Compare Files..."),
            0,
            0,
            self,
            "diff_files",
        )
        self.diffAct.setStatusTip(self.tr("Compare two files"))
        self.diffAct.setWhatsThis(
            self.tr(
                """<b>Compare Files</b>"""
                """<p>Open a dialog to compare two files.</p>"""
            )
        )
        self.diffAct.triggered.connect(self.__compareFiles)
        self.actions.append(self.diffAct)

        self.compareAct = EricAction(
            self.tr("Compare Files side by side"),
            EricPixmapCache.getIcon("compareFiles"),
            self.tr("Compare &Files side by side..."),
            0,
            0,
            self,
            "compare_files",
        )
        self.compareAct.setStatusTip(self.tr("Compare two files"))
        self.compareAct.setWhatsThis(
            self.tr(
                """<b>Compare Files side by side</b>"""
                """<p>Open a dialog to compare two files and show the result"""
                """ side by side.</p>"""
            )
        )
        self.compareAct.triggered.connect(self.__compareFilesSbs)
        self.actions.append(self.compareAct)

        self.sqlBrowserAct = EricAction(
            self.tr("SQL Browser"),
            EricPixmapCache.getIcon("sqlBrowser"),
            self.tr("SQL &Browser..."),
            0,
            0,
            self,
            "sql_browser",
        )
        self.sqlBrowserAct.setStatusTip(self.tr("Browse a SQL database"))
        self.sqlBrowserAct.setWhatsThis(
            self.tr("""<b>SQL Browser</b><p>Browse a SQL database.</p>""")
        )
        self.sqlBrowserAct.triggered.connect(self.__sqlBrowser)
        self.actions.append(self.sqlBrowserAct)

        self.miniEditorAct = EricAction(
            self.tr("Mini Editor"),
            EricPixmapCache.getIcon("editor"),
            self.tr("Mini &Editor..."),
            0,
            0,
            self,
            "mini_editor",
        )
        self.miniEditorAct.setStatusTip(self.tr("Mini Editor"))
        self.miniEditorAct.setWhatsThis(
            self.tr(
                """<b>Mini Editor</b>"""
                """<p>Open a dialog with a simplified editor.</p>"""
            )
        )
        self.miniEditorAct.triggered.connect(self.__openMiniEditor)
        self.actions.append(self.miniEditorAct)

        self.hexEditorAct = EricAction(
            self.tr("Hex Editor"),
            EricPixmapCache.getIcon("hexEditor"),
            self.tr("&Hex Editor..."),
            0,
            0,
            self,
            "hex_editor",
        )
        self.hexEditorAct.setStatusTip(self.tr("Start the eric Hex Editor"))
        self.hexEditorAct.setWhatsThis(
            self.tr(
                """<b>Hex Editor</b>"""
                """<p>Starts the eric Hex Editor for viewing or editing"""
                """ binary files.</p>"""
            )
        )
        self.hexEditorAct.triggered.connect(self.__openHexEditor)
        self.actions.append(self.hexEditorAct)

        self.webBrowserAct = EricAction(
            self.tr("eric Web Browser"),
            EricPixmapCache.getIcon("ericWeb"),
            self.tr("eric &Web Browser..."),
            0,
            0,
            self,
            "web_browser",
        )
        self.webBrowserAct.setStatusTip(self.tr("Start the eric Web Browser"))
        self.webBrowserAct.setWhatsThis(
            self.tr(
                """<b>eric Web Browser</b>"""
                """<p>Browse the Internet with the eric Web Browser.</p>"""
            )
        )
        self.webBrowserAct.triggered.connect(self.__startWebBrowser)
        self.actions.append(self.webBrowserAct)

        if importlib.util.find_spec("fido2"):
            self.securityKeyMgmtAct = EricAction(
                self.tr("FIDO2 Security Key Management"),
                EricPixmapCache.getIcon("securityKey"),
                self.tr("FIDO2 Security Key Management..."),
                0,
                0,
                self,
                "fido2_security_key_mgmt",
            )
            self.securityKeyMgmtAct.setStatusTip(
                self.tr("Start the FIDO2 Security Key Management tool")
            )
            self.securityKeyMgmtAct.setWhatsThis(
                self.tr(
                    """<b>FIDO2 Security Key Management</b>"""
                    """<p>Start a tool to manage FIDO2 securit y keys.</p>"""
                )
            )
            self.securityKeyMgmtAct.triggered.connect(self.__startFido2SecurityKeyMgmt)
            self.actions.append(self.securityKeyMgmtAct)
        else:
            self.securityKeyMgmtAct = None

        self.iconEditorAct = EricAction(
            self.tr("Icon Editor"),
            EricPixmapCache.getIcon("iconEditor"),
            self.tr("&Icon Editor..."),
            0,
            0,
            self,
            "icon_editor",
        )
        self.iconEditorAct.setStatusTip(self.tr("Start the eric Icon Editor"))
        self.iconEditorAct.setWhatsThis(
            self.tr(
                """<b>Icon Editor</b>"""
                """<p>Starts the eric Icon Editor for editing simple icons.</p>"""
            )
        )
        self.iconEditorAct.triggered.connect(self.__editPixmap)
        self.actions.append(self.iconEditorAct)

        if DesktopUtilities.isWaylandSession():
            self.snapshotAct = None
        else:
            self.snapshotAct = EricAction(
                self.tr("Snapshot"),
                EricPixmapCache.getIcon("ericSnap"),
                self.tr("&Snapshot..."),
                0,
                0,
                self,
                "snapshot",
            )
            self.snapshotAct.setStatusTip(self.tr("Take snapshots of a screen region"))
            self.snapshotAct.setWhatsThis(
                self.tr(
                    """<b>Snapshot</b>"""
                    """<p>This opens a dialog to take snapshots of a screen"""
                    """ region.</p>"""
                )
            )
            self.snapshotAct.triggered.connect(self.__snapshot)
            self.actions.append(self.snapshotAct)

        self.pdfViewerAct = EricAction(
            self.tr("eric PDF Viewer"),
            EricPixmapCache.getIcon("ericPdf"),
            self.tr("eric PDF &Viewer..."),
            0,
            0,
            self,
            "pdf_viewer",
        )
        self.pdfViewerAct.setStatusTip(self.tr("Start the eric PDF Viewer"))
        self.pdfViewerAct.setWhatsThis(
            self.tr(
                """<b>eric PDF Viewer</b>"""
                """<p>Starts the eric PDF Viewer for viewing PDF files.</p>"""
            )
        )
        self.pdfViewerAct.triggered.connect(self.__openPdfViewer)
        self.actions.append(self.pdfViewerAct)

        self.prefAct = EricAction(
            self.tr("Preferences"),
            EricPixmapCache.getIcon("configure"),
            self.tr("&Preferences..."),
            0,
            0,
            self,
            "preferences",
        )
        self.prefAct.setStatusTip(self.tr("Set the prefered configuration"))
        self.prefAct.setWhatsThis(
            self.tr(
                """<b>Preferences</b>"""
                """<p>Set the configuration items of the application"""
                """ with your prefered values.</p>"""
            )
        )
        self.prefAct.triggered.connect(self.showPreferences)
        self.prefAct.setMenuRole(QAction.MenuRole.PreferencesRole)
        self.actions.append(self.prefAct)

        self.prefExportAct = EricAction(
            self.tr("Export Preferences"),
            EricPixmapCache.getIcon("configureExport"),
            self.tr("E&xport Preferences..."),
            0,
            0,
            self,
            "export_preferences",
        )
        self.prefExportAct.setStatusTip(self.tr("Export the current configuration"))
        self.prefExportAct.setWhatsThis(
            self.tr(
                """<b>Export Preferences</b>"""
                """<p>Export the current configuration to a file.</p>"""
            )
        )
        self.prefExportAct.triggered.connect(self.__exportPreferences)
        self.actions.append(self.prefExportAct)

        self.prefImportAct = EricAction(
            self.tr("Import Preferences"),
            EricPixmapCache.getIcon("configureImport"),
            self.tr("I&mport Preferences..."),
            0,
            0,
            self,
            "import_preferences",
        )
        self.prefImportAct.setStatusTip(
            self.tr("Import a previously exported configuration")
        )
        self.prefImportAct.setWhatsThis(
            self.tr(
                """<b>Import Preferences</b>"""
                """<p>Import a previously exported configuration.</p>"""
            )
        )
        self.prefImportAct.triggered.connect(self.__importPreferences)
        self.actions.append(self.prefImportAct)

        self.themeExportAct = EricAction(
            self.tr("Export Theme"),
            EricPixmapCache.getIcon("themeExport"),
            self.tr("Export Theme..."),
            0,
            0,
            self,
            "export_theme",
        )
        self.themeExportAct.setStatusTip(self.tr("Export the current theme"))
        self.themeExportAct.setWhatsThis(
            self.tr(
                """<b>Export Theme</b>"""
                """<p>Export the current theme to a file.</p>"""
            )
        )
        self.themeExportAct.triggered.connect(self.__exportTheme)
        self.actions.append(self.themeExportAct)

        self.themeImportAct = EricAction(
            self.tr("Import Theme"),
            EricPixmapCache.getIcon("themeImport"),
            self.tr("Import Theme..."),
            0,
            0,
            self,
            "import_theme",
        )
        self.themeImportAct.setStatusTip(self.tr("Import a previously exported theme"))
        self.themeImportAct.setWhatsThis(
            self.tr(
                """<b>Import Theme</b>"""
                """<p>Import a previously exported theme.</p>"""
            )
        )
        self.themeImportAct.triggered.connect(self.__importTheme)
        self.actions.append(self.themeImportAct)

        self.reloadAPIsAct = EricAction(
            self.tr("Reload APIs"), self.tr("Reload &APIs"), 0, 0, self, "reload_apis"
        )
        self.reloadAPIsAct.setStatusTip(self.tr("Reload the API information"))
        self.reloadAPIsAct.setWhatsThis(
            self.tr("""<b>Reload APIs</b><p>Reload the API information.</p>""")
        )
        self.reloadAPIsAct.triggered.connect(self.__reloadAPIs)
        self.actions.append(self.reloadAPIsAct)

        self.showExternalToolsAct = EricAction(
            self.tr("Show external tools"),
            EricPixmapCache.getIcon("showPrograms"),
            self.tr("Show external &tools"),
            0,
            0,
            self,
            "show_external_tools",
        )
        self.showExternalToolsAct.setStatusTip(self.tr("Show external tools"))
        self.showExternalToolsAct.setWhatsThis(
            self.tr(
                """<b>Show external tools</b>"""
                """<p>Opens a dialog to show the path and versions of all"""
                """ extenal tools used by eric.</p>"""
            )
        )
        self.showExternalToolsAct.triggered.connect(self.__showExternalTools)
        self.actions.append(self.showExternalToolsAct)

        self.configViewProfilesAct = EricAction(
            self.tr("View Profiles"),
            EricPixmapCache.getIcon("configureViewProfiles"),
            self.tr("&View Profiles..."),
            0,
            0,
            self,
            "view_profiles",
        )
        self.configViewProfilesAct.setStatusTip(self.tr("Configure view profiles"))
        self.configViewProfilesAct.setWhatsThis(
            self.tr(
                """<b>View Profiles</b>"""
                """<p>Configure the view profiles. With this dialog you may"""
                """ set the visibility of the various windows for the"""
                """ predetermined view profiles.</p>"""
            )
        )
        self.configViewProfilesAct.triggered.connect(self.__configViewProfiles)
        self.actions.append(self.configViewProfilesAct)

        self.configToolBarsAct = EricAction(
            self.tr("Toolbars"),
            EricPixmapCache.getIcon("toolbarsConfigure"),
            self.tr("Tool&bars..."),
            0,
            0,
            self,
            "configure_toolbars",
        )
        self.configToolBarsAct.setStatusTip(self.tr("Configure toolbars"))
        self.configToolBarsAct.setWhatsThis(
            self.tr(
                """<b>Toolbars</b>"""
                """<p>Configure the toolbars. With this dialog you may"""
                """ change the actions shown on the various toolbars and"""
                """ define your own toolbars.</p>"""
            )
        )
        self.configToolBarsAct.triggered.connect(self.__configToolBars)
        self.actions.append(self.configToolBarsAct)

        self.shortcutsAct = EricAction(
            self.tr("Keyboard Shortcuts"),
            EricPixmapCache.getIcon("configureShortcuts"),
            self.tr("Keyboard &Shortcuts..."),
            0,
            0,
            self,
            "keyboard_shortcuts",
        )
        self.shortcutsAct.setStatusTip(self.tr("Set the keyboard shortcuts"))
        self.shortcutsAct.setWhatsThis(
            self.tr(
                """<b>Keyboard Shortcuts</b>"""
                """<p>Set the keyboard shortcuts of the application"""
                """ with your prefered values.</p>"""
            )
        )
        self.shortcutsAct.triggered.connect(self.__configShortcuts)
        self.actions.append(self.shortcutsAct)

        self.exportShortcutsAct = EricAction(
            self.tr("Export Keyboard Shortcuts"),
            EricPixmapCache.getIcon("exportShortcuts"),
            self.tr("&Export Keyboard Shortcuts..."),
            0,
            0,
            self,
            "export_keyboard_shortcuts",
        )
        self.exportShortcutsAct.setStatusTip(self.tr("Export the keyboard shortcuts"))
        self.exportShortcutsAct.setWhatsThis(
            self.tr(
                """<b>Export Keyboard Shortcuts</b>"""
                """<p>Export the keyboard shortcuts of the application.</p>"""
            )
        )
        self.exportShortcutsAct.triggered.connect(self.__exportShortcuts)
        self.actions.append(self.exportShortcutsAct)

        self.importShortcutsAct = EricAction(
            self.tr("Import Keyboard Shortcuts"),
            EricPixmapCache.getIcon("importShortcuts"),
            self.tr("&Import Keyboard Shortcuts..."),
            0,
            0,
            self,
            "import_keyboard_shortcuts",
        )
        self.importShortcutsAct.setStatusTip(self.tr("Import the keyboard shortcuts"))
        self.importShortcutsAct.setWhatsThis(
            self.tr(
                """<b>Import Keyboard Shortcuts</b>"""
                """<p>Import the keyboard shortcuts of the application.</p>"""
            )
        )
        self.importShortcutsAct.triggered.connect(self.__importShortcuts)
        self.actions.append(self.importShortcutsAct)

        if SSL_AVAILABLE:
            self.certificatesAct = EricAction(
                self.tr("Manage SSL Certificates"),
                EricPixmapCache.getIcon("certificates"),
                self.tr("Manage SSL Certificates..."),
                0,
                0,
                self,
                "manage_ssl_certificates",
            )
            self.certificatesAct.setStatusTip(
                self.tr("Manage the saved SSL certificates")
            )
            self.certificatesAct.setWhatsThis(
                self.tr(
                    """<b>Manage SSL Certificates...</b>"""
                    """<p>Opens a dialog to manage the saved SSL certificates."""
                    """</p>"""
                )
            )
            self.certificatesAct.triggered.connect(self.__showCertificatesDialog)
            self.actions.append(self.certificatesAct)

        self.editMessageFilterAct = EricAction(
            self.tr("Edit Message Filters"),
            EricPixmapCache.getIcon("warning"),
            self.tr("Edit Message Filters..."),
            0,
            0,
            self,
            "manage_message_filters",
        )
        self.editMessageFilterAct.setStatusTip(
            self.tr("Edit the message filters used to suppress unwanted messages")
        )
        self.editMessageFilterAct.setWhatsThis(
            self.tr(
                """<b>Edit Message Filters</b>"""
                """<p>Opens a dialog to edit the message filters used to"""
                """ suppress unwanted messages been shown in an error"""
                """ window.</p>"""
            )
        )
        self.editMessageFilterAct.triggered.connect(EricErrorMessage.editMessageFilters)
        self.actions.append(self.editMessageFilterAct)

        self.clearPrivateDataAct = EricAction(
            self.tr("Clear private data"),
            EricPixmapCache.getIcon("clearPrivateData"),
            self.tr("Clear private data"),
            0,
            0,
            self,
            "clear_private_data",
        )
        self.clearPrivateDataAct.setStatusTip(self.tr("Clear private data"))
        self.clearPrivateDataAct.setWhatsThis(
            self.tr(
                """<b>Clear private data</b>"""
                """<p>Clears the private data like the various list of"""
                """ recently opened files, projects or multi projects.</p>"""
            )
        )
        self.clearPrivateDataAct.triggered.connect(self.__clearPrivateData)
        self.actions.append(self.clearPrivateDataAct)

        self.viewmanagerActivateAct = EricAction(
            self.tr("Activate current editor"),
            self.tr("Activate current editor"),
            QKeySequence(self.tr("Alt+Shift+E")),
            0,
            self,
            "viewmanager_activate",
        )
        self.viewmanagerActivateAct.triggered.connect(self.__activateViewmanager)
        self.actions.append(self.viewmanagerActivateAct)
        self.addAction(self.viewmanagerActivateAct)

        self.nextTabAct = EricAction(
            self.tr("Show next"),
            self.tr("Show next"),
            QKeySequence(self.tr("Ctrl+Alt+Tab")),
            0,
            self,
            "view_next_tab",
        )
        self.nextTabAct.triggered.connect(self.__showNext)
        self.actions.append(self.nextTabAct)
        self.addAction(self.nextTabAct)

        self.prevTabAct = EricAction(
            self.tr("Show previous"),
            self.tr("Show previous"),
            QKeySequence(self.tr("Shift+Ctrl+Alt+Tab")),
            0,
            self,
            "view_previous_tab",
        )
        self.prevTabAct.triggered.connect(self.__showPrevious)
        self.actions.append(self.prevTabAct)
        self.addAction(self.prevTabAct)

        self.switchTabAct = EricAction(
            self.tr("Switch between tabs"),
            self.tr("Switch between tabs"),
            QKeySequence(self.tr("Ctrl+1")),
            0,
            self,
            "switch_tabs",
        )
        self.switchTabAct.triggered.connect(self.__switchTab)
        self.actions.append(self.switchTabAct)
        self.addAction(self.switchTabAct)

        self.pluginInfoAct = EricAction(
            self.tr("Plugin Infos"),
            EricPixmapCache.getIcon("plugin"),
            self.tr("&Plugin Infos..."),
            0,
            0,
            self,
            "plugin_infos",
        )
        self.pluginInfoAct.setStatusTip(self.tr("Show Plugin Infos"))
        self.pluginInfoAct.setWhatsThis(
            self.tr(
                """<b>Plugin Infos...</b>"""
                """<p>This opens a dialog, that show some information about"""
                """ loaded plugins.</p>"""
            )
        )
        self.pluginInfoAct.triggered.connect(self.__showPluginInfo)
        self.actions.append(self.pluginInfoAct)

        self.pluginInstallAct = EricAction(
            self.tr("Install Plugins"),
            EricPixmapCache.getIcon("pluginInstall"),
            self.tr("&Install Plugins..."),
            0,
            0,
            self,
            "plugin_install",
        )
        self.pluginInstallAct.setStatusTip(self.tr("Install Plugins"))
        self.pluginInstallAct.setWhatsThis(
            self.tr(
                """<b>Install Plugins...</b>"""
                """<p>This opens a dialog to install or update plugins.</p>"""
            )
        )
        self.pluginInstallAct.triggered.connect(self.__installPlugins)
        self.actions.append(self.pluginInstallAct)

        self.pluginDeinstallAct = EricAction(
            self.tr("Uninstall Plugin"),
            EricPixmapCache.getIcon("pluginUninstall"),
            self.tr("&Uninstall Plugin..."),
            0,
            0,
            self,
            "plugin_deinstall",
        )
        self.pluginDeinstallAct.setStatusTip(self.tr("Uninstall Plugin"))
        self.pluginDeinstallAct.setWhatsThis(
            self.tr(
                """<b>Uninstall Plugin...</b>"""
                """<p>This opens a dialog to uninstall a plugin.</p>"""
            )
        )
        self.pluginDeinstallAct.triggered.connect(self.__deinstallPlugin)
        self.actions.append(self.pluginDeinstallAct)

        self.pluginRepoAct = EricAction(
            self.tr("Plugin Repository"),
            EricPixmapCache.getIcon("pluginRepository"),
            self.tr("Plugin &Repository..."),
            0,
            0,
            self,
            "plugin_repository",
        )
        self.pluginRepoAct.setStatusTip(self.tr("Show Plugins available for download"))
        self.pluginRepoAct.setWhatsThis(
            self.tr(
                """<b>Plugin Repository...</b>"""
                """<p>This opens a dialog, that shows a list of plugins """
                """available on the Internet.</p>"""
            )
        )
        self.pluginRepoAct.triggered.connect(self.__showPluginsAvailable)
        self.actions.append(self.pluginRepoAct)

        # initialize viewmanager actions
        self.viewmanager.initActions()

        # initialize debugger actions
        self.debuggerUI.initActions()

        # initialize project actions
        self.project.initActions()

        # initialize multi project actions
        self.multiProject.initActions()

        # initialize eric-ide server actions
        self.__ericServerInterface.initActions()

    def __initQtDocActions(self):
        """
        Private slot to initialize the action to show the Qt documentation.
        """
        self.qt5DocAct = EricAction(
            self.tr("Qt5 Documentation"),
            self.tr("Qt5 Documentation"),
            0,
            0,
            self,
            "qt5_documentation",
        )
        self.qt5DocAct.setStatusTip(self.tr("Open Qt5 Documentation"))
        self.qt5DocAct.setWhatsThis(
            self.tr(
                """<b>Qt5 Documentation</b>"""
                """<p>Display the Qt5 Documentation. Dependent upon your"""
                """ settings, this will either show the help in Eric's internal"""
                """ help viewer/web browser, or execute a web browser or Qt"""
                """ Assistant. </p>"""
            )
        )
        self.qt5DocAct.triggered.connect(lambda: self.__showQtDoc(5))
        self.actions.append(self.qt5DocAct)

        self.qt6DocAct = EricAction(
            self.tr("Qt6 Documentation"),
            self.tr("Qt6 Documentation"),
            0,
            0,
            self,
            "qt6_documentation",
        )
        self.qt6DocAct.setStatusTip(self.tr("Open Qt6 Documentation"))
        self.qt6DocAct.setWhatsThis(
            self.tr(
                """<b>Qt6 Documentation</b>"""
                """<p>Display the Qt6 Documentation. Dependent upon your"""
                """ settings, this will either show the help in Eric's internal"""
                """ help viewer/web browser, or execute a web browser or Qt"""
                """ Assistant. </p>"""
            )
        )
        self.qt6DocAct.triggered.connect(lambda: self.__showQtDoc(6))
        self.actions.append(self.qt6DocAct)

        self.pyqt5DocAct = EricAction(
            self.tr("PyQt5 Documentation"),
            self.tr("PyQt5 Documentation"),
            0,
            0,
            self,
            "pyqt5_documentation",
        )
        self.pyqt5DocAct.setStatusTip(self.tr("Open PyQt5 Documentation"))
        self.pyqt5DocAct.setWhatsThis(
            self.tr(
                """<b>PyQt5 Documentation</b>"""
                """<p>Display the PyQt5 Documentation. Dependent upon your"""
                """ settings, this will either show the help in Eric's"""
                """ internal help viewer/web browser, or execute a web"""
                """ browser or Qt Assistant. </p>"""
            )
        )
        self.pyqt5DocAct.triggered.connect(lambda: self.__showPyQtDoc(variant=5))
        self.actions.append(self.pyqt5DocAct)

        self.pyqt6DocAct = EricAction(
            self.tr("PyQt6 Documentation"),
            self.tr("PyQt6 Documentation"),
            0,
            0,
            self,
            "pyqt6_documentation",
        )
        self.pyqt6DocAct.setStatusTip(self.tr("Open PyQt6 Documentation"))
        self.pyqt6DocAct.setWhatsThis(
            self.tr(
                """<b>PyQt6 Documentation</b>"""
                """<p>Display the PyQt6 Documentation. Dependent upon your"""
                """ settings, this will either show the help in Eric's"""
                """ internal help viewer/web browser, or execute a web"""
                """ browser or Qt Assistant. </p>"""
            )
        )
        self.pyqt6DocAct.triggered.connect(lambda: self.__showPyQtDoc(variant=6))
        self.actions.append(self.pyqt6DocAct)

    def __initPythonDocActions(self):
        """
        Private slot to initialize the actions to show the Python
        documentation.
        """
        self.pythonDocAct = EricAction(
            self.tr("Python 3 Documentation"),
            self.tr("Python 3 Documentation"),
            0,
            0,
            self,
            "python3_documentation",
        )
        self.pythonDocAct.setStatusTip(self.tr("Open Python 3 Documentation"))
        self.pythonDocAct.setWhatsThis(
            self.tr(
                """<b>Python 3 Documentation</b>"""
                """<p>Display the Python 3 documentation. If no documentation"""
                """ directory is configured, the location of the Python 3"""
                """ documentation is assumed to be the doc directory underneath"""
                """ the location of the Python 3 executable on Windows and"""
                """ <i>/usr/share/doc/packages/python/html</i> on Unix. Set"""
                """ PYTHON3DOCDIR in your environment to override this.</p>"""
            )
        )
        self.pythonDocAct.triggered.connect(self.__showPythonDoc)
        self.actions.append(self.pythonDocAct)

    def __initEricDocAction(self):
        """
        Private slot to initialize the action to show the eric documentation.
        """
        self.ericDocAct = EricAction(
            self.tr("eric API Documentation"),
            self.tr("eric API Documentation"),
            0,
            0,
            self,
            "eric_documentation",
        )
        self.ericDocAct.setStatusTip(self.tr("Open eric API Documentation"))
        self.ericDocAct.setWhatsThis(
            self.tr(
                """<b>eric API Documentation</b>"""
                """<p>Display the eric API documentation. The location for the"""
                """ documentation is the Documentation/Source subdirectory of"""
                """ the eric installation directory.</p>"""
            )
        )
        self.ericDocAct.triggered.connect(self.__showEricDoc)
        self.actions.append(self.ericDocAct)

    def __initPySideDocActions(self):
        """
        Private slot to initialize the actions to show the PySide
        documentation.
        """
        if QtUtilities.checkPyside(variant=2):
            self.pyside2DocAct = EricAction(
                self.tr("PySide2 Documentation"),
                self.tr("PySide2 Documentation"),
                0,
                0,
                self,
                "pyside2_documentation",
            )
            self.pyside2DocAct.setStatusTip(self.tr("Open PySide2 Documentation"))
            self.pyside2DocAct.setWhatsThis(
                self.tr(
                    """<b>PySide2 Documentation</b>"""
                    """<p>Display the PySide2 Documentation. Dependent upon your"""
                    """ settings, this will either show the help in Eric's"""
                    """ internal help viewer/web browser, or execute a web"""
                    """ browser or Qt Assistant. </p>"""
                )
            )
            self.pyside2DocAct.triggered.connect(
                lambda: self.__showPySideDoc(variant=2)
            )
            self.actions.append(self.pyside2DocAct)
        else:
            self.pyside2DocAct = None

        if QtUtilities.checkPyside(variant=6):
            self.pyside6DocAct = EricAction(
                self.tr("PySide6 Documentation"),
                self.tr("PySide6 Documentation"),
                0,
                0,
                self,
                "pyside6_documentation",
            )
            self.pyside6DocAct.setStatusTip(self.tr("Open PySide6 Documentation"))
            self.pyside6DocAct.setWhatsThis(
                self.tr(
                    """<b>PySide6 Documentation</b>"""
                    """<p>Display the PySide6 Documentation. Dependent upon your"""
                    """ settings, this will either show the help in Eric's"""
                    """ internal help viewer/web browser, or execute a web"""
                    """ browser or Qt Assistant. </p>"""
                )
            )
            self.pyside6DocAct.triggered.connect(
                lambda: self.__showPySideDoc(variant=6)
            )
            self.actions.append(self.pyside6DocAct)
        else:
            self.pyside6DocAct = None

    def __initMenus(self):
        """
        Private slot to create the menus.
        """
        self.__menus = {}
        mb = self.menuBar()
        if (
            OSUtilities.isLinuxPlatform() or OSUtilities.isFreeBsdPlatform()
        ) and not Preferences.getUI("UseNativeMenuBar"):
            mb.setNativeMenuBar(False)

        ##############################################################
        ## Remote Server menu
        ##############################################################

        self.__menus["server"] = self.__ericServerInterface.initMenus()

        ##############################################################
        ## Sessions menu
        ##############################################################

        self.__menus["sessions"] = QMenu(self.tr("Sessions"))
        self.__menus["sessions"].aboutToShow.connect(self.__showSessionsMenu)

        ##############################################################
        ## File menu
        ##############################################################

        self.__menus["file"] = self.viewmanager.initFileMenu()
        mb.addMenu(self.__menus["file"])
        self.__menus["file"].addSeparator()
        self.__menus["file"].addMenu(self.__menus["sessions"])
        self.__menus["file"].addSeparator()
        self.__menus["file"].addAction(self.restartAct)
        self.__menus["file"].addAction(self.exitAct)
        act = self.__menus["file"].actions()[0]
        sep = self.__menus["file"].insertSeparator(act)
        self.__menus["file"].insertAction(sep, self.newWindowAct)
        self.__menus["file"].insertSeparator(sep)
        self.__menus["file"].insertMenu(sep, self.__menus["server"])
        self.__menus["file"].insertSeparator(sep)
        self.__menus["file"].aboutToShow.connect(self.__showFileMenu)

        ##############################################################
        ## Edit menu
        ##############################################################

        self.__menus["edit"] = self.viewmanager.initEditMenu()
        mb.addMenu(self.__menus["edit"])

        ##############################################################
        ## Search menu
        ##############################################################

        self.__menus["search"] = self.viewmanager.initSearchMenu()
        mb.addMenu(self.__menus["search"])

        ##############################################################
        ## View menu
        ##############################################################

        self.__menus["view"] = self.viewmanager.initViewMenu()
        mb.addMenu(self.__menus["view"])

        ##############################################################
        ## Bookmarks menu
        ##############################################################

        self.__menus["bookmarks"] = self.viewmanager.initBookmarkMenu()
        mb.addMenu(self.__menus["bookmarks"])
        self.__menus["bookmarks"].setTearOffEnabled(True)

        ##############################################################
        ## Multiproject menu
        ##############################################################

        self.__menus["multiproject"] = self.multiProject.initMenu()
        mb.addMenu(self.__menus["multiproject"])

        ##############################################################
        ## Project menu
        ##############################################################

        (
            self.__menus["project"],
            self.__menus["project_tools"],
        ) = self.project.initMenus()
        mb.addMenu(self.__menus["project"])
        mb.addMenu(self.__menus["project_tools"])

        ##############################################################
        ## Start and Debug menus
        ##############################################################

        self.__menus["start"], self.__menus["debug"] = self.debuggerUI.initMenus()
        mb.addMenu(self.__menus["start"])
        mb.addMenu(self.__menus["debug"])

        ##############################################################
        ## Extras menu
        ##############################################################

        self.__menus["extras"] = QMenu(self.tr("E&xtras"), self)
        self.__menus["extras"].setTearOffEnabled(True)
        self.__menus["extras"].aboutToShow.connect(self.__showExtrasMenu)
        mb.addMenu(self.__menus["extras"])
        self.viewmanager.addToExtrasMenu(self.__menus["extras"])

        ##############################################################
        ## Extras/Wizards menu
        ##############################################################

        self.__menus["wizards"] = QMenu(self.tr("Wi&zards"), self)
        self.__menus["wizards"].setTearOffEnabled(True)
        self.__menus["wizards"].aboutToShow.connect(self.__showWizardsMenu)
        self.wizardsMenuAct = self.__menus["extras"].addMenu(self.__menus["wizards"])
        self.wizardsMenuAct.setEnabled(False)

        ##############################################################
        ## Extras/Macros menu
        ##############################################################

        self.__menus["macros"] = self.viewmanager.initMacroMenu()
        self.__menus["extras"].addMenu(self.__menus["macros"])
        self.__menus["extras"].addSeparator()

        ##############################################################
        ## Extras/Plugins menu
        ##############################################################

        pluginsMenu = QMenu(self.tr("P&lugins"), self)
        pluginsMenu.setIcon(EricPixmapCache.getIcon("plugin"))
        pluginsMenu.setTearOffEnabled(True)
        pluginsMenu.addAction(self.pluginInfoAct)
        pluginsMenu.addAction(self.pluginInstallAct)
        pluginsMenu.addAction(self.pluginDeinstallAct)
        pluginsMenu.addSeparator()
        pluginsMenu.addAction(self.pluginRepoAct)
        pluginsMenu.addSeparator()
        pluginsMenu.addAction(self.tr("Configure..."), self.__pluginsConfigure)

        self.__menus["extras"].addMenu(pluginsMenu)
        self.__menus["extras"].addSeparator()

        ##############################################################
        ## Extras/Unittest menu
        ##############################################################

        self.__menus["testing"] = QMenu(self.tr("&Testing"), self)
        self.__menus["testing"].setTearOffEnabled(True)
        self.__menus["testing"].addAction(self.testingDialogAct)
        self.__menus["testing"].addSeparator()
        self.__menus["testing"].addAction(self.restartTestAct)
        self.__menus["testing"].addAction(self.rerunFailedTestsAct)
        self.__menus["testing"].addSeparator()
        self.__menus["testing"].addAction(self.testScriptAct)
        self.__menus["testing"].addAction(self.testProjectAct)

        self.__menus["extras"].addMenu(self.__menus["testing"])
        self.__menus["extras"].addSeparator()

        ##############################################################
        ## Extras/Builtin,Plugin,User tools menus
        ##############################################################

        self.toolGroupsMenu = QMenu(self.tr("Select Tool Group"), self)
        self.toolGroupsMenu.aboutToShow.connect(self.__showToolGroupsMenu)
        self.toolGroupsMenu.triggered.connect(self.__toolGroupSelected)
        self.toolGroupsMenuTriggered = False
        self.__initToolsMenus(self.__menus["extras"])
        self.__menus["extras"].addSeparator()

        ##############################################################
        ## Settings menu
        ##############################################################

        self.__menus["settings"] = QMenu(self.tr("Se&ttings"), self)
        mb.addMenu(self.__menus["settings"])
        self.__menus["settings"].setTearOffEnabled(True)

        self.__menus["settings"].addAction(self.prefAct)
        self.__menus["settings"].addAction(self.prefExportAct)
        self.__menus["settings"].addAction(self.prefImportAct)
        self.__menus["settings"].addSeparator()
        self.__menus["settings"].addAction(self.themeExportAct)
        self.__menus["settings"].addAction(self.themeImportAct)
        self.__menus["settings"].addSeparator()
        self.__menus["settings"].addAction(self.reloadAPIsAct)
        self.__menus["settings"].addSeparator()
        self.__menus["settings"].addAction(self.configViewProfilesAct)
        self.__menus["settings"].addAction(self.configToolBarsAct)
        self.__menus["settings"].addSeparator()
        self.__menus["settings"].addAction(self.shortcutsAct)
        self.__menus["settings"].addAction(self.exportShortcutsAct)
        self.__menus["settings"].addAction(self.importShortcutsAct)
        self.__menus["settings"].addSeparator()
        self.__menus["settings"].addAction(self.showExternalToolsAct)
        if SSL_AVAILABLE:
            self.__menus["settings"].addSeparator()
            self.__menus["settings"].addAction(self.certificatesAct)
        self.__menus["settings"].addSeparator()
        self.__menus["settings"].addAction(self.editMessageFilterAct)
        self.__menus["settings"].addSeparator()
        self.__menus["settings"].addAction(self.clearPrivateDataAct)

        ##############################################################
        ## Window menu
        ##############################################################

        self.__menus["window"] = QMenu(self.tr("&Window"), self)
        mb.addMenu(self.__menus["window"])
        self.__menus["window"].setTearOffEnabled(True)
        self.__menus["window"].aboutToShow.connect(self.__showWindowMenu)

        ##############################################################
        ## Window/Windows menu
        ##############################################################

        self.__menus["subwindow"] = QMenu(self.tr("&Windows"), self.__menus["window"])
        self.__menus["subwindow"].setTearOffEnabled(True)

        # central park
        self.__menus["subwindow"].addSection(self.tr("Central Park"))
        self.__menus["subwindow"].addAction(self.viewmanagerActivateAct)

        # left side
        self.__menus["subwindow"].addSection(self.tr("Left Side"))
        self.__menus["subwindow"].addAction(self.mpbActivateAct)
        self.__menus["subwindow"].addAction(self.pbActivateAct)
        if self.__findFileWidget is not None:
            self.__menus["subwindow"].addAction(self.findFileActivateAct)
        if self.__findLocationWidget is not None:
            self.__menus["subwindow"].addAction(self.findLocationActivateAct)
        self.__menus["subwindow"].addAction(self.vcsStatusListActivateAct)
        if not self.rightSidebar:
            self.__menus["subwindow"].addAction(self.debugViewerActivateAct)
        if self.templateViewer is not None:
            self.__menus["subwindow"].addAction(self.templateViewerActivateAct)
        if self.browser is not None:
            self.__menus["subwindow"].addAction(self.browserActivateAct)
        if self.symbolsViewer is not None:
            self.__menus["subwindow"].addAction(self.symbolsViewerActivateAct)

        # right side
        if self.rightSidebar:
            self.__menus["subwindow"].addSection(self.tr("Right Side"))
            self.__menus["subwindow"].addAction(self.debugViewerActivateAct)
        if self.codeDocumentationViewer is not None:
            self.__menus["subwindow"].addAction(self.codeDocumentationViewerActivateAct)
        self.__menus["subwindow"].addAction(self.helpViewerActivateAct)
        self.__menus["subwindow"].addAction(self.pluginRepositoryViewerActivateAct)
        self.__menus["subwindow"].addAction(self.virtualenvManagerActivateAct)
        if self.pipWidget is not None:
            self.__menus["subwindow"].addAction(self.pipWidgetActivateAct)
        if self.condaWidget is not None:
            self.__menus["subwindow"].addAction(self.condaWidgetActivateAct)
        if self.cooperation is not None:
            self.__menus["subwindow"].addAction(self.cooperationViewerActivateAct)
        if self.irc is not None:
            self.__menus["subwindow"].addAction(self.ircActivateAct)
        if self.microPythonWidget is not None:
            self.__menus["subwindow"].addAction(self.microPythonWidgetActivateAct)

        # bottom side
        self.__menus["subwindow"].addSection(self.tr("Bottom Side"))
        self.__menus["subwindow"].addAction(self.shellActivateAct)
        self.__menus["subwindow"].addAction(self.taskViewerActivateAct)
        self.__menus["subwindow"].addAction(self.logViewerActivateAct)
        if self.numbersViewer is not None:
            self.__menus["subwindow"].addAction(self.numbersViewerActivateAct)

        # plug-in provided windows
        self.__menus["subwindow"].addSection(self.tr("Plug-ins"))

        ##############################################################
        ## Window/Toolbars menu
        ##############################################################

        self.__menus["toolbars"] = QMenu(self.tr("&Toolbars"), self.__menus["window"])
        self.__menus["toolbars"].setTearOffEnabled(True)
        self.__menus["toolbars"].aboutToShow.connect(self.__showToolbarsMenu)
        self.__menus["toolbars"].triggered.connect(self.__TBMenuTriggered)

        self.__showWindowMenu()  # to initialize these actions

        mb.addSeparator()

        ##############################################################
        ## Help menu
        ##############################################################

        self.__menus["help"] = QMenu(self.tr("&Help"), self)
        mb.addMenu(self.__menus["help"])
        self.__menus["help"].setTearOffEnabled(True)
        if self.helpviewerAct:
            self.__menus["help"].addAction(self.helpviewerAct)
            self.__menus["help"].addSeparator()
        self.__menus["help"].addAction(self.ericDocAct)
        self.__menus["help"].addAction(self.pythonDocAct)
        self.__menus["help"].addAction(self.qt5DocAct)
        self.__menus["help"].addAction(self.qt6DocAct)
        self.__menus["help"].addAction(self.pyqt5DocAct)
        self.__menus["help"].addAction(self.pyqt6DocAct)
        if self.pyside2DocAct is not None:
            self.__menus["help"].addAction(self.pyside2DocAct)
        if self.pyside6DocAct is not None:
            self.__menus["help"].addAction(self.pyside6DocAct)
        self.__menus["help"].addSeparator()
        self.__menus["help"].addAction(self.versionAct)
        self.__menus["help"].addAction(self.copyVersionAct)
        self.__menus["help"].addSeparator()
        self.__menus["help"].addAction(self.showInstallInfoAct)
        self.__menus["help"].addSeparator()
        self.__menus["help"].addAction(self.showErrorLogAct)
        self.__menus["help"].addAction(self.reportBugAct)
        self.__menus["help"].addAction(self.requestFeatureAct)
        self.__menus["help"].addSeparator()
        self.__menus["help"].addAction(self.whatsThisAct)
        self.__menus["help"].aboutToShow.connect(self.__showHelpMenu)

    def __initToolbars(self):
        """
        Private slot to create the toolbars.
        """
        filetb = self.viewmanager.initFileToolbar(self.toolbarManager)
        edittb = self.viewmanager.initEditToolbar(self.toolbarManager)
        searchtb = self.viewmanager.initSearchToolbar(self.toolbarManager)
        viewtb = self.viewmanager.initViewToolbar(self.toolbarManager)
        starttb, debugtb = self.debuggerUI.initToolbars(self.toolbarManager)
        multiprojecttb = self.multiProject.initToolbar(self.toolbarManager)
        projecttb, vcstb = self.project.initToolbars(self.toolbarManager)
        toolstb = QToolBar(self.tr("Tools"), self)
        testingtb = QToolBar(self.tr("Testing"), self)
        bookmarktb = self.viewmanager.initBookmarkToolbar(self.toolbarManager)
        spellingtb = self.viewmanager.initSpellingToolbar(self.toolbarManager)
        settingstb = QToolBar(self.tr("Settings"), self)
        helptb = QToolBar(self.tr("Help"), self)
        profilestb = QToolBar(self.tr("Profiles"), self)
        pluginstb = QToolBar(self.tr("Plugins"), self)
        servertb = self.__ericServerInterface.initToolbar(self.toolbarManager)

        toolstb.setObjectName("ToolsToolbar")
        testingtb.setObjectName("UnittestToolbar")
        settingstb.setObjectName("SettingsToolbar")
        helptb.setObjectName("HelpToolbar")
        profilestb.setObjectName("ProfilesToolbar")
        pluginstb.setObjectName("PluginsToolbar")

        toolstb.setToolTip(self.tr("Tools"))
        testingtb.setToolTip(self.tr("Unittest"))
        settingstb.setToolTip(self.tr("Settings"))
        helptb.setToolTip(self.tr("Help"))
        profilestb.setToolTip(self.tr("Profiles"))
        pluginstb.setToolTip(self.tr("Plugins"))

        filetb.addSeparator()
        filetb.addAction(self.restartAct)
        filetb.addAction(self.exitAct)
        act = filetb.actions()[0]
        sep = filetb.insertSeparator(act)
        filetb.insertAction(sep, self.newWindowAct)
        self.toolbarManager.addToolBar(filetb, filetb.windowTitle())

        # setup the testing toolbar
        testingtb.addAction(self.testingDialogAct)
        testingtb.addSeparator()
        testingtb.addAction(self.restartTestAct)
        testingtb.addAction(self.rerunFailedTestsAct)
        testingtb.addSeparator()
        testingtb.addAction(self.testScriptAct)
        testingtb.addAction(self.testProjectAct)
        self.toolbarManager.addToolBar(testingtb, testingtb.windowTitle())

        # setup the tools toolbar
        if self.designer4Act is not None:
            toolstb.addAction(self.designer4Act)
        if self.linguist4Act is not None:
            toolstb.addAction(self.linguist4Act)
        toolstb.addAction(self.uipreviewerAct)
        toolstb.addAction(self.trpreviewerAct)
        toolstb.addSeparator()
        toolstb.addAction(self.diffAct)
        toolstb.addAction(self.compareAct)
        toolstb.addSeparator()
        toolstb.addAction(self.sqlBrowserAct)
        toolstb.addSeparator()
        toolstb.addAction(self.miniEditorAct)
        toolstb.addAction(self.hexEditorAct)
        toolstb.addAction(self.iconEditorAct)
        if self.snapshotAct is not None:
            toolstb.addAction(self.snapshotAct)
        toolstb.addAction(self.pdfViewerAct)
        toolstb.addSeparator()
        toolstb.addAction(self.webBrowserAct)
        if self.securityKeyMgmtAct is not None:
            toolstb.addAction(self.securityKeyMgmtAct)
        self.toolbarManager.addToolBar(toolstb, toolstb.windowTitle())

        # setup the settings toolbar
        settingstb.addAction(self.prefAct)
        settingstb.addAction(self.configViewProfilesAct)
        settingstb.addAction(self.configToolBarsAct)
        settingstb.addAction(self.shortcutsAct)
        settingstb.addAction(self.showExternalToolsAct)
        self.toolbarManager.addToolBar(settingstb, settingstb.windowTitle())
        self.toolbarManager.addActions(
            [
                self.exportShortcutsAct,
                self.importShortcutsAct,
                self.prefExportAct,
                self.prefImportAct,
                self.themeExportAct,
                self.themeImportAct,
                self.showExternalToolsAct,
                self.editMessageFilterAct,
                self.clearPrivateDataAct,
            ],
            settingstb.windowTitle(),
        )
        if SSL_AVAILABLE:
            self.toolbarManager.addAction(
                self.certificatesAct, settingstb.windowTitle()
            )

        # setup the help toolbar
        helptb.addAction(self.whatsThisAct)
        self.toolbarManager.addToolBar(helptb, helptb.windowTitle())
        if self.helpviewerAct:
            self.toolbarManager.addAction(self.helpviewerAct, helptb.windowTitle())

        # setup the view profiles toolbar
        profilestb.addActions(self.viewProfileActGrp.actions())
        self.toolbarManager.addToolBar(profilestb, profilestb.windowTitle())

        # setup the plugins toolbar
        pluginstb.addAction(self.pluginInfoAct)
        pluginstb.addAction(self.pluginInstallAct)
        pluginstb.addAction(self.pluginDeinstallAct)
        pluginstb.addSeparator()
        pluginstb.addAction(self.pluginRepoAct)
        self.toolbarManager.addToolBar(pluginstb, pluginstb.windowTitle())

        # add the various toolbars
        self.addToolBar(filetb)
        self.addToolBar(servertb)
        self.addToolBar(edittb)
        self.addToolBar(searchtb)
        self.addToolBar(viewtb)
        self.addToolBar(starttb)
        self.addToolBar(debugtb)
        self.addToolBar(multiprojecttb)
        self.addToolBar(projecttb)
        self.addToolBar(vcstb)
        self.addToolBar(Qt.ToolBarArea.RightToolBarArea, settingstb)
        self.addToolBar(Qt.ToolBarArea.RightToolBarArea, toolstb)
        self.addToolBar(helptb)
        self.addToolBar(bookmarktb)
        self.addToolBar(spellingtb)
        self.addToolBar(testingtb)
        self.addToolBar(profilestb)
        self.addToolBar(pluginstb)

        # hide toolbars not wanted in the initial layout
        searchtb.hide()
        viewtb.hide()
        debugtb.hide()
        multiprojecttb.hide()
        helptb.hide()
        spellingtb.hide()
        testingtb.hide()
        pluginstb.hide()

        # just add new toolbars to the end of the list
        self.__toolbars = {}
        self.__toolbars["file"] = [filetb.windowTitle(), filetb, ""]
        self.__toolbars["edit"] = [edittb.windowTitle(), edittb, ""]
        self.__toolbars["search"] = [searchtb.windowTitle(), searchtb, ""]
        self.__toolbars["view"] = [viewtb.windowTitle(), viewtb, ""]
        self.__toolbars["start"] = [starttb.windowTitle(), starttb, ""]
        self.__toolbars["debug"] = [debugtb.windowTitle(), debugtb, ""]
        self.__toolbars["project"] = [projecttb.windowTitle(), projecttb, ""]
        self.__toolbars["tools"] = [toolstb.windowTitle(), toolstb, ""]
        self.__toolbars["help"] = [helptb.windowTitle(), helptb, ""]
        self.__toolbars["settings"] = [settingstb.windowTitle(), settingstb, ""]
        self.__toolbars["bookmarks"] = [bookmarktb.windowTitle(), bookmarktb, ""]
        self.__toolbars["testing"] = [testingtb.windowTitle(), testingtb, ""]
        self.__toolbars["view_profiles"] = [profilestb.windowTitle(), profilestb, ""]
        self.__toolbars["plugins"] = [pluginstb.windowTitle(), pluginstb, ""]
        self.__toolbars["multiproject"] = [
            multiprojecttb.windowTitle(),
            multiprojecttb,
            "",
        ]
        self.__toolbars["spelling"] = [spellingtb.windowTitle(), spellingtb, ""]
        self.__toolbars["vcs"] = [vcstb.windowTitle(), vcstb, "vcs"]
        self.__toolbars["server"] = [servertb.windowTitle(), servertb, ""]

    def __initDebugToolbarsLayout(self):
        """
        Private slot to initialize the toolbars layout for the debug profile.
        """
        # Step 1: set the edit profile to be sure
        self.__setEditProfile()

        # Step 2: switch to debug profile and do the layout
        initSize = self.size()
        self.setDebugProfile()
        self.__toolbars["project"][1].hide()
        self.__toolbars["debug"][1].show()
        self.resize(initSize)

        # Step 3: switch back to edit profile
        self.__setEditProfile()

    def __initStatusbar(self):
        """
        Private slot to set up the status bar.
        """
        from eric7.VCS.StatusMonitorLed import StatusMonitorLedWidget

        self.__statusBar = self.statusBar()
        self.__statusBar.setSizeGripEnabled(True)

        self.sbLanguage = EricClickableLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbLanguage)
        self.sbLanguage.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays the"""
                """ current editors language.</p>"""
            )
        )

        self.sbEncoding = EricClickableLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbEncoding)
        self.sbEncoding.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays the"""
                """ current editors encoding.</p>"""
            )
        )

        self.sbEol = EricClickableLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbEol)
        self.sbEol.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays the"""
                """ current editors eol setting.</p>"""
            )
        )

        self.sbWritable = QLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbWritable)
        self.sbWritable.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays an indication of the"""
                """ current editors files writability.</p>"""
            )
        )

        self.sbLine = QLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbLine)
        self.sbLine.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays the line number of"""
                """ the current editor.</p>"""
            )
        )

        self.sbPos = QLabel(self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbPos)
        self.sbPos.setWhatsThis(
            self.tr(
                """<p>This part of the status bar displays the cursor position"""
                """ of the current editor.</p>"""
            )
        )

        self.sbZoom = EricZoomWidget(
            EricPixmapCache.getPixmap("zoomOut"),
            EricPixmapCache.getPixmap("zoomIn"),
            EricPixmapCache.getPixmap("zoomReset"),
            self.__statusBar,
        )
        self.__statusBar.addPermanentWidget(self.sbZoom)
        self.sbZoom.setWhatsThis(
            self.tr(
                """<p>This part of the status bar allows zooming the current"""
                """ editor or shell.</p>"""
            )
        )

        self.viewmanager.setSbInfo(
            self.sbLine,
            self.sbPos,
            self.sbWritable,
            self.sbEncoding,
            self.sbLanguage,
            self.sbEol,
            self.sbZoom,
        )

        self.sbVcsMonitorLed = StatusMonitorLedWidget(self.project, self.__statusBar)
        self.__statusBar.addPermanentWidget(self.sbVcsMonitorLed)

        self.networkIcon = EricNetworkIcon(
            dynamicOnlineCheck=Preferences.getUI("DynamicOnlineCheck"),
            parent=self.__statusBar,
        )
        self.__statusBar.addPermanentWidget(self.networkIcon)
        self.networkIcon.onlineStateChanged.connect(self.onlineStateChanged)
        self.networkIcon.onlineStateChanged.connect(self.__onlineStateChanged)

    def __initExternalToolsActions(self):
        """
        Private slot to create actions for the configured external tools.
        """
        self.toolGroupActions = {}
        for toolGroup in self.toolGroups:
            category = self.tr("External Tools/{0}").format(toolGroup[0])
            for tool in toolGroup[1]:
                if tool["menutext"] != "--":
                    act = QAction(
                        EricPixmapCache.getIcon(tool["icon"]), tool["menutext"], self
                    )
                    act.setObjectName("{0}@@{1}".format(toolGroup[0], tool["menutext"]))
                    act.triggered.connect(
                        functools.partial(self.__toolActionTriggered, act)
                    )
                    self.toolGroupActions[act.objectName()] = act

                    self.toolbarManager.addAction(act, category)

    def __updateExternalToolsActions(self):
        """
        Private method to update the external tools actions for the current
        tool group.
        """
        toolGroup = self.toolGroups[self.currentToolGroup]
        groupkey = "{0}@@".format(toolGroup[0])
        groupActionKeys = []
        # step 1: get actions for this group
        for key in self.toolGroupActions:
            if key.startswith(groupkey):
                groupActionKeys.append(key)

        # step 2: build keys for all actions i.a.w. current configuration
        ckeys = []
        for tool in toolGroup[1]:
            if tool["menutext"] != "--":
                ckeys.append("{0}@@{1}".format(toolGroup[0], tool["menutext"]))

        # step 3: remove all actions not configured any more
        for key in groupActionKeys:
            if key not in ckeys:
                self.toolbarManager.removeAction(self.toolGroupActions[key])
                self.toolGroupActions[key].triggered.disconnect()
                del self.toolGroupActions[key]

        # step 4: add all newly configured tools
        category = self.tr("External Tools/{0}").format(toolGroup[0])
        for tool in toolGroup[1]:
            if tool["menutext"] != "--":
                key = "{0}@@{1}".format(toolGroup[0], tool["menutext"])
                if key not in groupActionKeys:
                    act = QAction(
                        EricPixmapCache.getIcon(tool["icon"]), tool["menutext"], self
                    )
                    act.setObjectName(key)
                    act.triggered.connect(
                        functools.partial(self.__toolActionTriggered, act)
                    )
                    self.toolGroupActions[key] = act

                    self.toolbarManager.addAction(act, category)

    def __showFileMenu(self):
        """
        Private slot to display the File menu.
        """
        self.showMenu.emit("File", self.__menus["file"])

    def __showExtrasMenu(self):
        """
        Private slot to display the Extras menu.
        """
        self.showMenu.emit("Extras", self.__menus["extras"])

    def __showWizardsMenu(self):
        """
        Private slot to display the Wizards menu.
        """
        actionsList = self.__menus["wizards"].actions()
        self.__menus["wizards"].clear()
        self.__menus["wizards"].addActions(
            sorted(actionsList, key=lambda a: a.text().replace("&", ""))
        )
        self.showMenu.emit("Wizards", self.__menus["wizards"])

    def __showHelpMenu(self):
        """
        Private slot to display the Help menu.
        """
        self.showErrorLogAct.setEnabled(self.__hasErrorLog())

        infoFileName = Globals.getInstallInfoFilePath()
        self.showInstallInfoAct.setEnabled(os.path.exists(infoFileName))

        self.showMenu.emit("Help", self.__menus["help"])

    def __showSettingsMenu(self):
        """
        Private slot to show the Settings menu.
        """
        self.editMessageFilterAct.setEnabled(EricErrorMessage.messageHandlerInstalled())

        self.showMenu.emit("Settings", self.__menus["settings"])

    def __showNext(self):
        """
        Private slot used to show the next tab or file.
        """
        fwidget = QApplication.focusWidget()
        while fwidget and not hasattr(fwidget, "nextTab"):
            fwidget = fwidget.parent()
        if fwidget:
            fwidget.nextTab()

    def __showPrevious(self):
        """
        Private slot used to show the previous tab or file.
        """
        fwidget = QApplication.focusWidget()
        while fwidget and not hasattr(fwidget, "prevTab"):
            fwidget = fwidget.parent()
        if fwidget:
            fwidget.prevTab()

    def __switchTab(self):
        """
        Private slot used to switch between the current and the previous
        current tab.
        """
        fwidget = QApplication.focusWidget()
        while fwidget and not hasattr(fwidget, "switchTab"):
            fwidget = fwidget.parent()
        if fwidget:
            fwidget.switchTab()

    def __whatsThis(self):
        """
        Private slot called in to enter Whats This mode.
        """
        QWhatsThis.enterWhatsThisMode()

    def __showVersions(self):
        """
        Private slot to handle the Versions dialog.
        """
        from .VersionsDialog import VersionsDialog

        try:
            sip_version_str = sip.SIP_VERSION_STR
        except AttributeError:
            sip_version_str = "sip version not available"

        sizeStr = "64-Bit" if sys.maxsize > 2**32 else "32-Bit"

        versionInfo = [self.tr("""<h2>Version Numbers</h2><table>""")]

        # eric7 version
        versionInfo.extend(
            [
                "<tr><td></td><td></td></tr>",
                f"<tr><td><b>{Program}</b></td><td>{Version}</td></tr>",
                "<tr><td></td><td></td></tr>",
            ]
        )

        # Python version
        versionInfo.append(
            f"<tr><td><b>Python</b></td><td>{sys.version.split()[0]},"
            f" {sizeStr}</td></tr>"
        )

        # Qt version
        versionInfo.append(f"<tr><td><b>Qt</b></td><td>{qVersion()}</td></tr>")

        # PyQt versions
        versionInfo.append(f"<tr><td><b>PyQt6</b></td><td>{PYQT_VERSION_STR}</td></tr>")
        with contextlib.suppress(ImportError, AttributeError):
            from PyQt6 import QtCharts  # __IGNORE_WARNING_I10__

            versionInfo.append(
                "<tr><td><b>PyQt6-Charts</b></td>"
                f"<td>{QtCharts.PYQT_CHART_VERSION_STR}</td></tr>"
            )
        with contextlib.suppress(ImportError, AttributeError):
            from PyQt6 import QtWebEngineCore  # __IGNORE_WARNING_I10__

            versionInfo.append(
                "<tr><td><b>PyQt6-WebEngine</b></td>"
                f"<td>{QtWebEngineCore.PYQT_WEBENGINE_VERSION_STR}</td></tr>"
            )
        versionInfo.extend(
            [
                "<tr><td><b>PyQt6-QScintilla</b></td>"
                f"<td>{QSCINTILLA_VERSION_STR}</td></tr>",
                f"<tr><td><b>sip</b></td><td>{sip_version_str}</td></tr>",
            ]
        )

        # webengine (chromium) version
        with contextlib.suppress(ImportError):
            from eric7.WebBrowser.Tools import (  # __IGNORE_WARNING_I101__
                WebBrowserTools,
            )

            (
                chromiumVersion,
                chromiumSecurityVersion,
            ) = WebBrowserTools.getWebEngineVersions()[0:2]
            versionInfo.append(
                f"<tr><td><b>WebEngine</b></td><td>{chromiumVersion}</td></tr>"
            )
            if chromiumSecurityVersion:
                versionInfo.append(
                    "<tr><td><b>WebEngine (Security)</b></td>"
                    f"<td>{chromiumSecurityVersion}</td></tr>"
                )

        # desktop and session type
        desktop = DesktopUtilities.desktopName()
        session = DesktopUtilities.sessionType()
        if desktop or session:
            versionInfo.append("<tr><td></td><td></td></tr>")
            if desktop:
                versionInfo.append(
                    f"<tr><td><b>{self.tr('Desktop')}</b></td><td>{desktop}</td></tr>"
                )
            if session:
                versionInfo.append(
                    f"<tr><td><b>{self.tr('Session Type')}</b></td>"
                    f"<td>{session}</td></tr>"
                )

        versionInfo.append("</table>")

        VersionsDialog(parent=self, title=Program, text="".join(versionInfo))

    def __copyVersions(self):
        """
        Private method to generated version information and copy that to the clipboard.
        """
        QGuiApplication.clipboard().setText(
            "\n----\n\n{0}\n\n----\n\n{1}\n\n----\n\n{2}".format(
                Utilities.generateVersionInfo("\n"),
                Utilities.generatePluginsVersionInfo("\n"),
                Utilities.generateDistroInfo("\n"),
            )
        )

    def __reportBug(self):
        """
        Private slot to handle the Report Bug dialog.
        """
        self.showEmailDialog("bug")

    def __requestFeature(self):
        """
        Private slot to handle the Feature Request dialog.
        """
        self.showEmailDialog("feature")

    def showEmailDialog(self, mode, attachFile=None, deleteAttachFile=False):
        """
        Public slot to show the email dialog in a given mode.

        @param mode mode of the email dialog ("bug" or "feature")
        @type str
        @param attachFile name of a file to attach to the email
        @type str
        @param deleteAttachFile flag indicating to delete the attached file
            after it has been sent
        @type bool
        """
        from .EmailDialog import EmailDialog

        if Preferences.getUser("UseSystemEmailClient"):
            self.__showSystemEmailClient(mode, attachFile, deleteAttachFile)
        else:
            if not Preferences.getUser("UseGoogleMailOAuth2") and (
                Preferences.getUser("Email") == ""
                or Preferences.getUser("MailServer") == ""
            ):
                EricMessageBox.critical(
                    self,
                    self.tr("Report Bug"),
                    self.tr(
                        """Email address or mail server address is empty."""
                        """ Please configure your Email settings in the"""
                        """ Preferences Dialog."""
                    ),
                )
                self.showPreferences("emailPage")
                return

            self.dlg = EmailDialog(mode=mode)
            if attachFile is not None:
                self.dlg.attachFile(attachFile, deleteAttachFile)
            self.dlg.show()

    def __showSystemEmailClient(self, mode, attachFile=None, deleteAttachFile=False):
        """
        Private slot to show the system email dialog.

        @param mode mode of the email dialog ("bug" or "feature")
        @type str
        @param attachFile name of a file to put into the body of the
            email
        @type str
        @param deleteAttachFile flag indicating to delete the file after
            it has been read
        @type bool
        """
        address = FeatureAddress if mode == "feature" else BugAddress
        subject = "[eric] "
        if attachFile is not None:
            with open(attachFile, "r", encoding="utf-8") as f:
                body = f.read()
            if deleteAttachFile:
                os.remove(attachFile)
        else:
            body = "\r\n----\r\n{0}\r\n----\r\n{1}\r\n----\r\n{2}".format(
                Utilities.generateVersionInfo("\r\n"),
                Utilities.generatePluginsVersionInfo("\r\n"),
                Utilities.generateDistroInfo("\r\n"),
            )

        url = QUrl("mailto:{0}".format(address))
        urlQuery = QUrlQuery(url)
        urlQuery.addQueryItem("subject", subject)
        urlQuery.addQueryItem("body", body)
        url.setQuery(urlQuery)
        QDesktopServices.openUrl(url)

    def checkForErrorLog(self):
        """
        Public method to check for the presence of an error log and ask the
        user, what to do with it.
        """
        from .ErrorLogDialog import ErrorLogDialog

        if Preferences.getUI("CheckErrorLog"):
            logFile = os.path.join(EricUtilities.getConfigDir(), self.ErrorLogFileName)
            if os.path.exists(logFile):
                dlg = ErrorLogDialog(logFile, False, parent=self)
                dlg.exec()

    def __hasErrorLog(self):
        """
        Private method to check, if an error log file exists.

        @return flag indicating the existence of an error log file
        @rtype bool
        """
        logFile = os.path.join(EricUtilities.getConfigDir(), self.ErrorLogFileName)
        return os.path.exists(logFile)

    def __showErrorLog(self):
        """
        Private slot to show the most recent error log message.
        """
        from .ErrorLogDialog import ErrorLogDialog

        logFile = os.path.join(EricUtilities.getConfigDir(), self.ErrorLogFileName)
        if os.path.exists(logFile):
            dlg = ErrorLogDialog(logFile, True, self)
            dlg.show()

    def __showInstallInfo(self):
        """
        Private slot to show a dialog containing information about the
        installation process.
        """
        from .InstallInfoDialog import InstallInfoDialog

        dlg = InstallInfoDialog(parent=self)
        if dlg.wasLoaded():
            dlg.exec()

    def __compareFiles(self):
        """
        Private slot to handle the Compare Files dialog.
        """
        from .DiffDialog import DiffDialog

        aw = self.viewmanager.activeWindow()
        fn = aw and aw.getFileName() or None
        if self.diffDlg is None:
            self.diffDlg = DiffDialog()
        self.diffDlg.show(fn)

    def __compareFilesSbs(self):
        """
        Private slot to handle the Compare Files dialog.
        """
        from .CompareDialog import CompareDialog

        aw = self.viewmanager.activeWindow()
        fn = aw and aw.getFileName() or None
        if self.compareDlg is None:
            self.compareDlg = CompareDialog()
        self.compareDlg.show(fn)

    def __openMiniEditor(self):
        """
        Private slot to show a mini editor window.
        """
        from eric7.QScintilla.MiniEditor import MiniEditor

        editor = MiniEditor(parent=self)
        editor.show()

    def addEricActions(self, actions, actionType):
        """
        Public method to add actions to the list of actions.

        @param actions list of actions to be added
        @type list of EricAction
        @param actionType string denoting the action set to add to.
            It must be one of "ui" or "wizards".
        @type str
        """
        if actionType == "ui":
            self.actions.extend(actions)
        elif actionType == "wizards":
            self.wizardsActions.extend(actions)

    def removeEricActions(self, actions, actionType="ui"):
        """
        Public method to remove actions from the list of actions.

        @param actions list of actions
        @type list of EricActio
        @param actionType string denoting the action set to remove from.
            It must be one of "ui" or "wizards".
        @type str
        """
        for act in actions:
            with contextlib.suppress(ValueError):
                if actionType == "ui":
                    self.actions.remove(act)
                elif actionType == "wizards":
                    self.wizardsActions.remove(act)

    def getActions(self, actionType):
        """
        Public method to get a list of all actions.

        @param actionType string denoting the action set to get.
            It must be one of "ui" or "wizards".
        @type str
        @return list of all actions
        @rtype list of EricAction
        """
        if actionType == "ui":
            return self.actions[:]
        elif actionType == "wizards":
            return self.wizardsActions[:]
        else:
            return []

    def getMenuAction(self, menuName, actionName):
        """
        Public method to get a reference to an action of a menu.

        @param menuName name of the menu to search in
        @type str
        @param actionName object name of the action to search for
        @type str
        @return reference to the menu action
        @rtype QAction
        """
        try:
            menu = self.__menus[menuName]
        except KeyError:
            return None

        for act in menu.actions():
            if act.objectName() == actionName:
                return act

        return None

    def getMenuBarAction(self, menuName):
        """
        Public method to get a reference to an action of the main menu.

        @param menuName name of the menu to search in
        @type str
        @return reference to the menu bar action
        @rtype QAction
        """
        try:
            menu = self.__menus[menuName]
        except KeyError:
            return None

        return menu.menuAction()

    def getMenu(self, name):
        """
        Public method to get a reference to a specific menu.

        @param name name of the menu
        @type str
        @return reference to the menu
        @rtype QMenu
        """
        try:
            return self.__menus[name]
        except KeyError:
            return None

    def registerToolbar(self, name, text, toolbar, category=""):
        """
        Public method to register a toolbar.

        This method must be called in order to make a toolbar manageable by the
        UserInterface object.

        @param name name of the toolbar. This is used as the key into
            the dictionary of toolbar references.
        @type str
        @param text user visible text for the toolbar entry
        @type str
        @param toolbar reference to the toolbar to be registered
        @type QToolBar
        @param category toolbar category
        @type str
        @exception KeyError raised, if a toolbar with the given name was
            already registered
        """
        if name in self.__toolbars:
            raise KeyError("Toolbar '{0}' already registered.".format(name))

        self.__toolbars[name] = [text, toolbar, category]

    def reregisterToolbar(self, name, text, category=""):
        """
        Public method to change the visible text for the named toolbar.

        @param name name of the toolbar to be changed
        @type str
        @param text new user visible text for the toolbar entry
        @type str
        @param category new toolbar category for the toolbar entry
        @type str
        """
        if name in self.__toolbars:
            self.__toolbars[name][0] = text
            self.__toolbars[name][2] = category

    def unregisterToolbar(self, name):
        """
        Public method to unregister a toolbar.

        @param name name of the toolbar
        @type str
        """
        if name in self.__toolbars:
            del self.__toolbars[name]

    def getToolbar(self, name):
        """
        Public method to get a reference to a specific toolbar.

        @param name name of the toolbar
        @type str
        @return reference to the toolbar entry
        @rtype tuple of (str, QToolBar)
        """
        try:
            return self.__toolbars[name]
        except KeyError:
            return None

    def getToolbarsByCategory(self, category):
        """
        Public method to get a list of toolbars belonging to a given toolbar
        category.

        @param category toolbar category
        @type str
        @return list of toolbars
        @rtype list of QToolBar
        """
        toolbars = []
        for tbName in self.__toolbars:
            with contextlib.suppress(IndexError):
                if self.__toolbars[tbName][2] == category:
                    toolbars.append(self.__toolbars[tbName][1])

        return toolbars

    def getLocale(self):
        """
        Public method to get the locale of the IDE.

        @return locale of the IDE
        @rtype str
        """
        return self.locale

    def __quit(self):
        """
        Private method to quit the application.
        """
        if self.__shutdown():
            ericApp().closeAllWindows()

    @pyqtSlot()
    def __restart(self, ask=False):
        """
        Private method to restart the application.

        @param ask flag indicating to ask the user for permission
        @type bool
        """
        res = (
            EricMessageBox.yesNo(
                self,
                self.tr("Restart application"),
                self.tr("""The application needs to be restarted. Do it now?"""),
                yesDefault=True,
            )
            if ask
            else True
        )

        if res and self.__shutdown():
            ericApp().closeAllWindows()
            program = PythonUtilities.getPythonExecutable()
            args = ["-m", "eric7", "--start-session"]
            args.extend(self.__restartArgs)
            QProcess.startDetached(program, args)

    @pyqtSlot()
    def upgradePyQt(self):
        """
        Public slot to upgrade the PyQt packages of the eric7 environment.

        @return flag indicating a successful upgrade
        @rtype bool
        """
        yes = EricMessageBox.yesNo(
            None,
            self.tr("Upgrade PyQt"),
            self.tr(
                """eric needs to be closed in order to upgrade PyQt. It"""
                """ will be restarted once the upgrade process has"""
                """ finished. This may take some time.\n\nShall the"""
                """ upgrade be done now?"""
            ),
        )

        if yes and self.__shutdown():
            self.__performUpgrade("pyqt")
            return True

        return False

    @pyqtSlot()
    def upgradeEric(self):
        """
        Public slot to upgrade the eric-ide package of the eric7 environment.

        @return flag indicating a successful upgrade
        @rtype bool
        """
        yes = EricMessageBox.yesNo(
            None,
            self.tr("Upgrade Eric"),
            self.tr(
                """eric needs to be closed in order to be upgraded. It"""
                """ will be restarted once the upgrade process has"""
                """ finished. This may take some time.\n\nShall the"""
                """ upgrade be done now?"""
            ),
        )

        if yes and self.__shutdown():
            self.__performUpgrade("eric")
            return True

        return False

    @pyqtSlot()
    def upgradeEricPyQt(self):
        """
        Public slot to upgrade the eric-ide and PyQt packages of the eric7
        environment.

        @return flag indicating a successful upgrade
        @rtype bool
        """
        yes = EricMessageBox.yesNo(
            None,
            self.tr("Upgrade Eric and PyQt6"),
            self.tr(
                """eric needs to be closed in order to upgrade eric and"""
                """ PyQt. It will be restarted once the upgrade process"""
                """ has finished. This may take some time.\n\n Shall"""
                """ the upgrade be done now?"""
            ),
        )

        if yes and self.__shutdown():
            self.__performUpgrade("ericpyqt")
            return True

        return False

    def __performUpgrade(self, upgradeType, startup=False):
        """
        Private method to perform the requested upgrade operation.

        This action needs to shut down eric first, start a non-PyQt application
        performing the upgrade of the PyQt packages via pip and restart eric
        with the passed arguments. The upgrade process is not visible.

        @param upgradeType upgrade operation (one of 'eric', 'ericpyqt',
            'pyqt')
        @type str
        @param startup flag indicating a call during the IDE startup (defaults to False)
        @type bool (optional)
        """
        ericApp().closeAllWindows()
        program = PythonUtilities.getPythonExecutable()
        ericStartArgs = (
            ["-m", "eric7"] if startup else ["-m", "eric7", "--start-session"]
        )
        ericStartArgs.extend(self.__restartArgs)

        upgrader = os.path.join(os.path.dirname(__file__), "upgrader.py")
        upgraderArgs = [
            upgrader,
            "--type={0}".format(upgradeType),
            "--delay={0}".format(Preferences.getUI("UpgraderDelay")),
            "--",
        ] + ericStartArgs
        QProcess.startDetached(program, upgraderArgs)

    def __newWindow(self):
        """
        Private slot to start a new instance of eric.
        """
        if not Preferences.getUI("SingleApplicationMode"):
            # start eric without loading anything and without crash session
            program = PythonUtilities.getPythonExecutable()
            eric7 = os.path.join(os.path.dirname(__file__), "..", "eric7_ide.py")
            args = [eric7, "--no-open", "--disable-crash"]
            QProcess.startDetached(program, args)

    def __initToolsMenus(self, menu):
        """
        Private slot to initialize the various tool menus.

        @param menu reference to the parent menu
        @type QMenu
        """
        btMenu = QMenu(self.tr("&Builtin Tools"), self)
        if self.designer4Act is not None:
            btMenu.addAction(self.designer4Act)
        if self.linguist4Act is not None:
            btMenu.addAction(self.linguist4Act)
        btMenu.addAction(self.uipreviewerAct)
        btMenu.addAction(self.trpreviewerAct)
        btMenu.addAction(self.diffAct)
        btMenu.addAction(self.compareAct)
        btMenu.addAction(self.sqlBrowserAct)
        btMenu.addAction(self.miniEditorAct)
        btMenu.addAction(self.hexEditorAct)
        btMenu.addAction(self.iconEditorAct)
        if self.snapshotAct is not None:
            btMenu.addAction(self.snapshotAct)
        btMenu.addAction(self.pdfViewerAct)
        btMenu.addAction(self.webBrowserAct)
        if self.securityKeyMgmtAct is not None:
            btMenu.addAction(self.securityKeyMgmtAct)

        ptMenu = QMenu(self.tr("&Plugin Tools"), self)
        ptMenu.aboutToShow.connect(self.__showPluginToolsMenu)

        utMenu = QMenu(self.tr("&User Tools"), self)
        utMenu.triggered.connect(self.__toolExecute)
        utMenu.aboutToShow.connect(self.__showUserToolsMenu)

        menu.addMenu(btMenu)
        menu.addMenu(ptMenu)
        menu.addMenu(utMenu)

        self.__menus["builtin_tools"] = btMenu
        self.__menus["plugin_tools"] = ptMenu
        self.__menus["user_tools"] = utMenu


    def __showPluginToolsMenu(self):
        """
        Private slot to show the Plugin Tools menu.
        """
        self.showMenu.emit("PluginTools", self.__menus["plugin_tools"])

    def __showUserToolsMenu(self):
        """
        Private slot to display the User Tools menu.
        """
        self.__menus["user_tools"].clear()

        self.__menus["user_tools"].addMenu(self.toolGroupsMenu)
        act = self.__menus["user_tools"].addAction(
            self.tr("Configure Tool Groups ..."), self.__toolGroupsConfiguration
        )
        act.setData(-1)
        act = self.__menus["user_tools"].addAction(
            self.tr("Configure current Tool Group ..."), self.__toolsConfiguration
        )
        act.setData(-2)
        act.setEnabled(self.currentToolGroup >= 0)
        self.__menus["user_tools"].addSeparator()

        # add the configurable entries
        try:
            for idx, tool in enumerate(self.toolGroups[self.currentToolGroup][1]):
                if tool["menutext"] == "--":
                    self.__menus["user_tools"].addSeparator()
                else:
                    act = self.__menus["user_tools"].addAction(
                        EricPixmapCache.getIcon(tool["icon"]), tool["menutext"]
                    )
                    act.setData(idx)
        except IndexError:
            # the current tool group might have been deleted
            act = self.__menus["user_tools"].addAction(
                self.tr("No User Tools Configured")
            )
            act.setData(-3)

    def __showToolGroupsMenu(self):
        """
        Private slot to display the Tool Groups menu.
        """
        self.toolGroupsMenu.clear()

        # add the configurable tool groups
        if self.toolGroups:
            for idx, toolGroup in enumerate(self.toolGroups):
                act = self.toolGroupsMenu.addAction(toolGroup[0])
                act.setData(idx)
                if self.currentToolGroup == idx:
                    font = act.font()
                    font.setBold(True)
                    act.setFont(font)
        else:
            act = self.toolGroupsMenu.addAction(self.tr("No User Tools Configured"))
            act.setData(-3)

    def __toolGroupSelected(self, act):
        """
        Private slot to set the current tool group.

        @param act reference to the action that was triggered
        @type QAction
        """
        self.toolGroupsMenuTriggered = True
        idx = act.data()
        if idx is not None:
            self.currentToolGroup = idx

    def __showWindowMenu(self):
        """
        Private slot to display the Window menu.
        """
        self.__menus["window"].clear()

        self.__menus["window"].addActions(self.viewProfileActGrp.actions())
        self.__menus["window"].addSeparator()

        if self.__layoutType == "Toolboxes":
            self.__menus["window"].addAction(self.ltAct)
            self.ltAct.setChecked(not self.lToolboxDock.isHidden())
            self.__menus["window"].addAction(self.rtAct)
            self.rtAct.setChecked(not self.lToolboxDock.isHidden())
            self.__menus["window"].addAction(self.htAct)
            self.htAct.setChecked(not self.hToolboxDock.isHidden())
        elif self.__layoutType == "Sidebars":
            self.__menus["window"].addAction(self.lsbAct)
            self.lsbAct.setChecked(not self.leftSidebar.isHidden())
            if self.rsbAct:
                self.__menus["window"].addAction(self.rsbAct)
                self.rsbAct.setChecked(not self.rightSidebar.isHidden())
            self.__menus["window"].addAction(self.bsbAct)
            self.bsbAct.setChecked(not self.bottomSidebar.isHidden())

        # Insert menu entry for sub-windows
        self.__menus["window"].addSeparator()
        self.__menus["window"].addMenu(self.__menus["subwindow"])

        # Insert menu entry for toolbar settings
        self.__menus["window"].addSeparator()
        self.__menus["window"].addMenu(self.__menus["toolbars"])

        # Now do any Source Viewer related stuff.
        self.viewmanager.showWindowMenu(self.__menus["window"])

        self.showMenu.emit("Window", self.__menus["window"])

    def __showSubWindowMenu(self):
        """
        Private slot to display the Window menu of the Window menu.
        """
        self.showMenu.emit("Subwindows", self.__menus["subwindow"])

    def __populateToolbarsMenu(self, menu):
        """
        Private method to populate a toolbars menu.

        @param menu reference to the menu to be populated
        @type QMenu
        """
        menu.clear()

        for name, (text, tb, _category) in sorted(
            self.__toolbars.items(), key=lambda t: t[1][0]
        ):
            act = menu.addAction(text)
            act.setCheckable(True)
            act.setChecked(not tb.isHidden())
            act.setData(name)
        menu.addSeparator()
        act = menu.addAction(self.tr("&Show all"))
        act.setData("__SHOW__")
        act = menu.addAction(self.tr("&Hide all"))
        act.setData("__HIDE__")

    def createPopupMenu(self):
        """
        Public method to create the toolbars menu for Qt.

        @return toolbars menu
        @rtype QMenu
        """
        menu = QMenu(self)
        menu.triggered.connect(self.__TBPopupMenuTriggered)

        self.__populateToolbarsMenu(menu)

        return menu

    def __showToolbarsMenu(self):
        """
        Private slot to display the Toolbars menu.
        """
        self.__populateToolbarsMenu(self.__menus["toolbars"])

    def __TBMenuTriggered(self, act):
        """
        Private method to handle the toggle of a toolbar via the Window->
        Toolbars submenu.

        @param act reference to the action that was triggered
        @type QAction
        """
        name = act.data()
        if name:
            if name == "__SHOW__":
                for _text, tb, _category in self.__toolbars.values():
                    tb.show()
                if self.__menus["toolbars"].isTearOffMenuVisible():
                    self.__menus["toolbars"].hideTearOffMenu()
            elif name == "__HIDE__":
                for _text, tb, _category in self.__toolbars.values():
                    tb.hide()
                if self.__menus["toolbars"].isTearOffMenuVisible():
                    self.__menus["toolbars"].hideTearOffMenu()
            else:
                tb = self.__toolbars[name][1]
                if act.isChecked():
                    tb.show()
                    tb.setEnabled(True)
                else:
                    tb.hide()

    def __TBPopupMenuTriggered(self, act):
        """
        Private method to handle the toggle of a toolbar via the QMainWindow
        Toolbars popup menu.

        @param act reference to the action that was triggered
        @type QAction
        """
        name = act.data()
        if name:
            if name == "__SHOW__":
                for _text, tb, _category in self.__toolbars.values():
                    tb.show()
            elif name == "__HIDE__":
                for _text, tb, _category in self.__toolbars.values():
                    tb.hide()
            else:
                tb = self.__toolbars[name][1]
                if act.isChecked():
                    tb.show()
                    tb.setEnabled(True)
                else:
                    tb.hide()
            if self.__menus["toolbars"].isTearOffMenuVisible():
                self.__menus["toolbars"].hideTearOffMenu()

    def __saveCurrentViewProfile(self, save):
        """
        Private slot to save the window geometries of the active profile.

        @param save flag indicating that the current profile should
            be saved
        @type bool
        """
        if self.currentProfile and save:
            # step 1: save the window geometries of the active profile
            if self.__layoutType in ["Toolboxes", "Sidebars"]:
                state = self.saveState()
                self.profiles[self.currentProfile][0] = state
                if self.__layoutType == "Sidebars":
                    state = self.horizontalSplitter.saveState()
                    self.profiles[self.currentProfile][2][0] = state
                    state = self.verticalSplitter.saveState()
                    self.profiles[self.currentProfile][2][1] = state

                    state = self.leftSidebar.saveState()
                    self.profiles[self.currentProfile][2][2] = state
                    state = self.bottomSidebar.saveState()
                    self.profiles[self.currentProfile][2][3] = state
                    if self.rightSidebar:
                        state = self.rightSidebar.saveState()
                        self.profiles[self.currentProfile][2][4] = state

            # step 2: save the visibility of the windows of the active profile
            if self.__layoutType == "Toolboxes":
                self.profiles[self.currentProfile][1][0] = self.lToolboxDock.isVisible()
                self.profiles[self.currentProfile][1][1] = self.hToolboxDock.isVisible()
                self.profiles[self.currentProfile][1][2] = self.rToolboxDock.isVisible()
            elif self.__layoutType == "Sidebars":
                self.profiles[self.currentProfile][1][0] = self.leftSidebar.isVisible()
                self.profiles[self.currentProfile][1][
                    1
                ] = self.bottomSidebar.isVisible()
                if self.rightSidebar:
                    self.profiles[self.currentProfile][1][
                        2
                    ] = self.rightSidebar.isVisible()
            Preferences.setUI("ViewProfiles", self.profiles)

    def __activateViewProfile(self, name, save=True):
        """
        Private slot to activate a view profile.

        @param name name of the profile to be activated
        @type str
        @param save flag indicating that the current profile should
            be saved
        @type bool
        """
        if self.currentProfile != name or not save:
            # step 1: save the active profile
            self.__saveCurrentViewProfile(save)

            # step 2: set the window geometries of the new profile
            if self.__layoutType in ["Toolboxes", "Sidebars"]:
                state = self.profiles[name][0]
                if not state.isEmpty():
                    self.restoreState(state)
                if self.__layoutType == "Sidebars":
                    state = self.profiles[name][2][0]
                    if not state.isEmpty():
                        self.horizontalSplitter.restoreState(state)
                    state = self.profiles[name][2][1]
                    if not state.isEmpty():
                        self.verticalSplitter.restoreState(state)

                    state = self.profiles[name][2][2]
                    if state:
                        self.leftSidebar.restoreState(state)
                    state = self.profiles[name][2][3]
                    if state:
                        self.bottomSidebar.restoreState(state)
                    if self.rightSidebar:
                        state = self.profiles[name][2][4]
                        if state:
                            self.rightSidebar.restoreState(state)

                if self.__layoutType == "Toolboxes":
                    # set the corner usages
                    self.setCorner(
                        Qt.Corner.TopLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea
                    )
                    self.setCorner(
                        Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea
                    )
                    self.setCorner(
                        Qt.Corner.TopRightCorner, Qt.DockWidgetArea.RightDockWidgetArea
                    )
                    self.setCorner(
                        Qt.Corner.BottomRightCorner,
                        Qt.DockWidgetArea.RightDockWidgetArea,
                    )

            # step 3: activate the windows of the new profile
            if self.__layoutType == "Toolboxes":
                self.lToolboxDock.setVisible(self.profiles[name][1][0])
                self.hToolboxDock.setVisible(self.profiles[name][1][1])
                self.rToolboxDock.setVisible(self.profiles[name][1][2])
            elif self.__layoutType == "Sidebars":
                self.leftSidebar.setVisible(self.profiles[name][1][0])
                self.bottomSidebar.setVisible(self.profiles[name][1][1])
                if self.rightSidebar:
                    self.rightSidebar.setVisible(self.profiles[name][1][2])

            # step 4: remember the new profile
            self.currentProfile = name

            # step 5: make sure that cursor of the shell is visible
            self.shell.ensureCursorVisible()

            # step 6: make sure, that the toolbars and window menu are
            #         shown correctly
            if self.__menus["toolbars"].isTearOffMenuVisible():
                self.__showToolbarsMenu()
            if self.__menus["window"].isTearOffMenuVisible():
                self.__showWindowMenu()

    def __debuggingStarted(self):
        """
        Private slot to handle the start of a debugging session.
        """
        self.setDebugProfile()
        if self.__layoutType == "Toolboxes":
            self.__currentRightWidget = self.rToolbox.currentWidget()
            self.rToolbox.setCurrentWidget(self.debugViewer)
            self.__currentBottomWidget = self.hToolbox.currentWidget()
            self.hToolbox.setCurrentWidget(self.shellAssembly)
        elif self.__layoutType == "Sidebars":
            if self.rightSidebar:
                self.__currentRightWidget = self.rightSidebar.currentWidget()
                self.rightSidebar.setCurrentWidget(self.debugViewer)
            else:
                self.__currentRightWidget = self.leftSidebar.currentWidget()
                self.leftSidebar.setCurrentWidget(self.debugViewer)
            self.__currentBottomWidget = self.bottomSidebar.currentWidget()
            self.bottomSidebar.setCurrentWidget(self.shellAssembly)

    def __debuggingDone(self):
        """
        Private slot to handle the end of a debugging session.
        """
        self.__setEditProfile()
        if self.__layoutType == "Toolboxes":
            if self.__currentRightWidget:
                self.rToolbox.setCurrentWidget(self.__currentRightWidget)
            if self.__currentBottomWidget:
                self.hToolbox.setCurrentWidget(self.__currentBottomWidget)
        elif self.__layoutType == "Sidebars":
            if self.__currentRightWidget:
                if self.rightSidebar:
                    self.rightSidebar.setCurrentWidget(self.__currentRightWidget)
                else:
                    self.leftSidebar.setCurrentWidget(self.__currentRightWidget)
            if self.__currentBottomWidget:
                self.bottomSidebar.setCurrentWidget(self.__currentBottomWidget)
        self.__currentRightWidget = None
        self.__currentBottomWidget = None
        self.__activateViewmanager()

    @pyqtSlot()
    def __setEditProfile(self, save=True):
        """
        Private slot to activate the edit view profile.

        @param save flag indicating that the current profile should
            be saved
        @type bool
        """
        self.__activateViewProfile("edit", save)
        self.setEditProfileAct.setChecked(True)

    @pyqtSlot()
    def setDebugProfile(self, save=True):
        """
        Public slot to activate the debug view profile.

        @param save flag indicating that the current profile should
            be saved
        @type bool
        """
        self.viewmanager.searchReplaceWidget().hide()
        self.__activateViewProfile("debug", save)
        self.setDebugProfileAct.setChecked(True)

    def getViewProfile(self):
        """
        Public method to get the current view profile.

        @return the name of the current view profile
        @rtype str
        """
        return self.currentProfile

    def getLayoutType(self):
        """
        Public method to get the current layout type.

        @return current layout type
        @rtype str
        """
        return self.__layoutType

    def setLeftRightSidebarWidgetIcon(self, widget, icon):
        """
        Public method to set the icon of the given widget in the left or right
        sidebar.

        @param widget reference to the widget to set the icon for
        @type QWidget
        @param icon icon to be set
        @type QIcon
        """
        sidebar = (
            self.leftSidebar
            if Preferences.getUI("CombinedLeftRightSidebar")
            else self.rightSidebar
        )
        index = sidebar.indexOf(widget)
        sidebar.setTabIcon(index, icon)

    def activateLeftRightSidebarWidget(self, widget):
        """
        Public method to activate the given widget in the left or right
        sidebar.

        @param widget reference to the widget to be activated
        @type QWidget
        """
        sidebar = (
            self.leftSidebar
            if Preferences.getUI("CombinedLeftRightSidebar")
            else self.rightSidebar
        )
        sidebar.show()
        sidebar.setCurrentWidget(widget)

    def __activateProjectBrowser(self):
        """
        Private slot to handle the activation of the project browser.
        """
        if self.__layoutType == "Toolboxes":
            self.lToolboxDock.show()
            self.lToolbox.setCurrentWidget(self.projectBrowser)
        elif self.__layoutType == "Sidebars":
            self.leftSidebar.show()
            self.leftSidebar.setCurrentWidget(self.projectBrowser)
        if self.projectBrowser.currentWidget() is not None:
            self.projectBrowser.currentWidget().setFocus(
                Qt.FocusReason.ActiveWindowFocusReason
            )

    def __activateMultiProjectBrowser(self):
        """
        Private slot to handle the activation of the project browser.
        """
        if self.__layoutType == "Toolboxes":
            self.lToolboxDock.show()
            self.lToolbox.setCurrentWidget(self.multiProjectBrowser)
        elif self.__layoutType == "Sidebars":
            self.leftSidebar.show()
            self.leftSidebar.setCurrentWidget(self.multiProjectBrowser)
        self.multiProjectBrowser.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def activateDebugViewer(self):
        """
        Public slot to handle the activation of the debug viewer.
        """
        if self.__layoutType == "Toolboxes":
            self.rToolboxDock.show()
            self.rToolbox.setCurrentWidget(self.debugViewer)
        elif self.__layoutType == "Sidebars":
            self.activateLeftRightSidebarWidget(self.debugViewer)
        self.debugViewer.currentWidget().setFocus(
            Qt.FocusReason.ActiveWindowFocusReason
        )

    def __activateShell(self):
        """
        Private slot to handle the activation of the Shell window.
        """
        if self.__layoutType == "Toolboxes":
            self.hToolboxDock.show()
            self.hToolboxDock.setCurrentWidget(self.shellAssembly)
        elif self.__layoutType == "Sidebars":
            self.bottomSidebar.show()
            self.bottomSidebar.setCurrentWidget(self.shellAssembly)
        self.shell.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __activateLogViewer(self):
        """
        Private slot to handle the activation of the Log Viewer.
        """
        if self.__layoutType == "Toolboxes":
            self.hToolboxDock.show()
            self.hToolbox.setCurrentWidget(self.logViewer)
            self.hToolbox.setTabIcon(
                self.hToolbox.currentIndex(),
                EricPixmapCache.getIcon("logViewer"),
            )
        elif self.__layoutType == "Sidebars":
            self.bottomSidebar.show()
            self.bottomSidebar.setCurrentWidget(self.logViewer)
            self.bottomSidebar.setTabIcon(
                self.bottomSidebar.currentIndex(),
                EricPixmapCache.getIcon("sbLogViewer96"),
            )
        self.logViewer.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __activateTaskViewer(self):
        """
        Private slot to handle the activation of the Task Viewer.
        """
        if self.__layoutType == "Toolboxes":
            self.hToolboxDock.show()
            self.hToolbox.setCurrentWidget(self.taskViewer)
        elif self.__layoutType == "Sidebars":
            self.bottomSidebar.show()
            self.bottomSidebar.setCurrentWidget(self.taskViewer)
        self.taskViewer.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __activateTemplateViewer(self):
        """
        Private slot to handle the activation of the Template Viewer.
        """
        if self.templateViewer is not None:
            if self.__layoutType == "Toolboxes":
                self.lToolboxDock.show()
                self.lToolbox.setCurrentWidget(self.templateViewer)
            elif self.__layoutType == "Sidebars":
                self.leftSidebar.show()
                self.leftSidebar.setCurrentWidget(self.templateViewer)
            self.templateViewer.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __activateBrowser(self):
        """
        Private slot to handle the activation of the file browser.
        """
        if self.browser is not None:
            if self.__layoutType == "Toolboxes":
                self.lToolboxDock.show()
                self.lToolbox.setCurrentWidget(self.browser)
            elif self.__layoutType == "Sidebars":
                self.leftSidebar.show()
                self.leftSidebar.setCurrentWidget(self.browser)
            self.browser.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __toggleLeftToolbox(self):
        """
        Private slot to handle the toggle of the Left Toolbox window.
        """
        hasFocus = self.lToolbox.currentWidget().hasFocus()
        shown = self.__toggleWindow(self.lToolboxDock)
        if shown:
            self.lToolbox.currentWidget().setFocus(
                Qt.FocusReason.ActiveWindowFocusReason
            )
        else:
            if hasFocus:
                self.__activateViewmanager()

    def __toggleRightToolbox(self):
        """
        Private slot to handle the toggle of the Right Toolbox window.
        """
        hasFocus = self.rToolbox.currentWidget().hasFocus()
        shown = self.__toggleWindow(self.rToolboxDock)
        if shown:
            self.rToolbox.currentWidget().setFocus(
                Qt.FocusReason.ActiveWindowFocusReason
            )
        else:
            if hasFocus:
                self.__activateViewmanager()

    def __toggleHorizontalToolbox(self):
        """
        Private slot to handle the toggle of the Horizontal Toolbox window.
        """
        hasFocus = self.hToolbox.currentWidget().hasFocus()
        shown = self.__toggleWindow(self.hToolboxDock)
        if shown:
            self.hToolbox.currentWidget().setFocus(
                Qt.FocusReason.ActiveWindowFocusReason
            )
        else:
            if hasFocus:
                self.__activateViewmanager()

    @pyqtSlot(int)
    def __hToolboxCurrentChanged(self, index):
        """
        Private slot handling a change of the current index of the Horizontal Toolbox.

        @param index current index of the horizontal toolbox
        @type int
        """
        if index == self.hToolbox.indexOf(self.logViewer):
            self.hToolbox.setTabIcon(index, EricPixmapCache.getIcon("logViewer"))

    def __toggleLeftSidebar(self):
        """
        Private slot to handle the toggle of the left sidebar window.
        """
        hasFocus = self.leftSidebar.currentWidget().hasFocus()
        shown = self.__toggleWindow(self.leftSidebar)
        if shown:
            self.leftSidebar.currentWidget().setFocus(
                Qt.FocusReason.ActiveWindowFocusReason
            )
        else:
            if hasFocus:
                self.__activateViewmanager()

    def __toggleRightSidebar(self):
        """
        Private slot to handle the toggle of the right sidebar window.
        """
        hasFocus = self.rightSidebar.currentWidget().hasFocus()
        shown = self.__toggleWindow(self.rightSidebar)
        if shown:
            self.rightSidebar.currentWidget().setFocus(
                Qt.FocusReason.ActiveWindowFocusReason
            )
        else:
            if hasFocus:
                self.__activateViewmanager()

    def __toggleBottomSidebar(self):
        """
        Private slot to handle the toggle of the bottom sidebar window.
        """
        hasFocus = self.bottomSidebar.currentWidget().hasFocus()
        shown = self.__toggleWindow(self.bottomSidebar)
        if shown:
            self.bottomSidebar.currentWidget().setFocus(
                Qt.FocusReason.ActiveWindowFocusReason
            )
        else:
            if hasFocus:
                self.__activateViewmanager()

    @pyqtSlot(int)
    def __bottomSidebarCurrentChanged(self, index):
        """
        Private slot handling a change of the current index of the Bottom Sidebar.

        @param index current index of the bottom sidebar
        @type int
        """
        if index == self.bottomSidebar.indexOf(self.logViewer):
            self.bottomSidebar.setTabIcon(
                index, EricPixmapCache.getIcon("sbLogViewer96")
            )

    def activateCooperationViewer(self):
        """
        Public slot to handle the activation of the cooperation window.
        """
        if self.cooperation is not None:
            if self.__layoutType == "Toolboxes":
                self.rToolboxDock.show()
                self.rToolbox.setCurrentWidget(self.cooperation)
            elif self.__layoutType == "Sidebars":
                self.activateLeftRightSidebarWidget(self.cooperation)
            self.cooperation.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __activateIRC(self):
        """
        Private slot to handle the activation of the IRC window.
        """
        if self.irc is not None:
            if self.__layoutType == "Toolboxes":
                self.rToolboxDock.show()
                self.rToolbox.setCurrentWidget(self.irc)
            elif self.__layoutType == "Sidebars":
                self.activateLeftRightSidebarWidget(self.irc)
            self.irc.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __activateSymbolsViewer(self):
        """
        Private slot to handle the activation of the Symbols Viewer.
        """
        if self.symbolsViewer is not None:
            if self.__layoutType == "Toolboxes":
                self.lToolboxDock.show()
                self.lToolbox.setCurrentWidget(self.symbolsViewer)
            elif self.__layoutType == "Sidebars":
                self.leftSidebar.show()
                self.leftSidebar.setCurrentWidget(self.symbolsViewer)
            self.symbolsViewer.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __activateNumbersViewer(self):
        """
        Private slot to handle the activation of the Numbers Viewer.
        """
        if self.numbersViewer is not None:
            if self.__layoutType == "Toolboxes":
                self.hToolboxDock.show()
                self.hToolbox.setCurrentWidget(self.numbersViewer)
            elif self.__layoutType == "Sidebars":
                self.bottomSidebar.show()
                self.bottomSidebar.setCurrentWidget(self.numbersViewer)
            self.numbersViewer.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __activateViewmanager(self):
        """
        Private slot to handle the activation of the current editor.
        """
        aw = self.viewmanager.activeWindow()
        if aw is not None:
            aw.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def activateCodeDocumentationViewer(self, switchFocus=True):
        """
        Public slot to handle the activation of the Code Documentation Viewer.

        @param switchFocus flag indicating to transfer the input focus
        @type bool
        """
        if self.codeDocumentationViewer is not None and (
            switchFocus or self.codeDocumentationViewer.isEnabled()
        ):
            if self.__layoutType == "Toolboxes":
                self.rToolboxDock.show()
                self.rToolbox.setCurrentWidget(self.codeDocumentationViewer)
            elif self.__layoutType == "Sidebars":
                self.activateLeftRightSidebarWidget(self.codeDocumentationViewer)
            if switchFocus:
                self.codeDocumentationViewer.setFocus(
                    Qt.FocusReason.ActiveWindowFocusReason
                )

    def __activatePipWidget(self):
        """
        Private slot to handle the activation of the PyPI manager widget.
        """
        if self.pipWidget is not None:
            if self.__layoutType == "Toolboxes":
                self.rToolboxDock.show()
                self.rToolbox.setCurrentWidget(self.pipWidget)
            elif self.__layoutType == "Sidebars":
                self.activateLeftRightSidebarWidget(self.pipWidget)
            self.pipWidget.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __activateCondaWidget(self):
        """
        Private slot to handle the activation of the Conda manager widget.
        """
        if self.condaWidget is not None:
            if self.__layoutType == "Toolboxes":
                self.rToolboxDock.show()
                self.rToolbox.setCurrentWidget(self.condaWidget)
            elif self.__layoutType == "Sidebars":
                self.activateLeftRightSidebarWidget(self.condaWidget)
            self.condaWidget.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __activateMicroPython(self):
        """
        Private slot to handle the activation of the MicroPython widget.
        """
        if self.microPythonWidget is not None:
            if self.__layoutType == "Toolboxes":
                self.rToolboxDock.show()
                self.rToolbox.setCurrentWidget(self.microPythonWidget)
            elif self.__layoutType == "Sidebars":
                self.activateLeftRightSidebarWidget(self.microPythonWidget)
            self.microPythonWidget.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __toggleWindow(self, w):
        """
        Private method to toggle a workspace editor window.

        @param w reference to the workspace editor window
        @type Editor
        @return flag indicating, if the window was shown
        @rtype bool
        """
        if w.isHidden():
            w.show()
            return True
        else:
            w.hide()
            return False

    def __toolsConfiguration(self):
        """
        Private slot to handle the tools configuration menu entry.
        """
        from eric7.Preferences.ToolConfigurationDialog import ToolConfigurationDialog

        dlg = ToolConfigurationDialog(
            self.toolGroups[self.currentToolGroup][1], parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.toolGroups[self.currentToolGroup][1] = dlg.getToollist()
            self.__updateExternalToolsActions()

    def __toolGroupsConfiguration(self):
        """
        Private slot to handle the tool groups configuration menu entry.
        """
        from eric7.Preferences.ToolGroupConfigurationDialog import (
            ToolGroupConfigurationDialog,
        )

        dlg = ToolGroupConfigurationDialog(
            self.toolGroups, self.currentToolGroup, parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.toolGroups, self.currentToolGroup = dlg.getToolGroups()

    def __createTestingDialog(self):
        """
        Private slot to generate the testing dialog on demand.
        """
        from eric7.Testing.TestingWidget import TestingWidget

        if self.__testingWidget is None:
            self.__testingWidget = TestingWidget()
            self.__testingWidget.testFile.connect(self.viewmanager.setFileLine)
            self.__testingWidget.testRunStopped.connect(self.__testingStopped)

    def __testingStopped(self):
        """
        Private slot to handle the end of a test run.
        """
        self.rerunFailedTestsAct.setEnabled(self.__testingWidget.hasFailedTests())
        self.restartTestAct.setEnabled(True)

    def __startTesting(self):
        """
        Private slot for displaying the testing dialog.
        """
        self.__createTestingDialog()
        self.__testingWidget.show()
        self.__testingWidget.raise_()

    @pyqtSlot()
    @pyqtSlot(str)
    def __startTestScript(self, testFile=None):
        """
        Private slot for displaying the testing dialog and run the current
        script.

        @param testFile file containing the tests to be run
        @type str
        """
        if testFile is None:
            aw = self.viewmanager.activeWindow()
            fn = aw.getFileName()
            testFile = [
                f for f in Utilities.getTestFileNames(fn) + [fn] if os.path.exists(f)
            ][0]

        self.__startTesting()
        self.__testingWidget.setTestFile(testFile, forProject=False)
        self.restartTestAct.setEnabled(False)
        self.rerunFailedTestsAct.setEnabled(False)

    @pyqtSlot()
    def __startTestProject(self):
        """
        Private slot for displaying the testing dialog and run the test for
        the current project.
        """
        testFile = None
        fn = self.project.getMainScript(True)
        if fn:
            testFile = [
                f for f in Utilities.getTestFileNames(fn) + [fn] if os.path.exists(f)
            ][0]

        self.__startTesting()
        self.__testingWidget.setTestFile(testFile, forProject=True)
        self.restartTestAct.setEnabled(False)
        self.rerunFailedTestsAct.setEnabled(False)

    def __restartTest(self):
        """
        Private slot to display the testing dialog and rerun the last
        test run.
        """
        self.__startTesting()
        self.__testingWidget.startTests()

    def __rerunFailedTests(self):
        """
        Private slot to display the testing dialog and rerun all failed tests
        of the last run.
        """
        self.__startTesting()
        self.__testingWidget.startTests(failedOnly=True)

    @pyqtSlot()
    @pyqtSlot(str)
    def __designer(self, fn=None):
        """
        Private slot to start the Qt-Designer executable.

        @param fn filename of the form to be opened
        @type str
        """
        args = []
        if fn is not None:
            try:
                if os.path.isfile(fn) and os.path.getsize(fn):
                    args.append(fn)
                else:
                    EricMessageBox.critical(
                        self,
                        self.tr("Problem"),
                        self.tr(
                            "<p>The file <b>{0}</b> does not exist or"
                            " is zero length.</p>"
                        ).format(fn),
                    )
                    return
            except OSError:
                EricMessageBox.critical(
                    self,
                    self.tr("Problem"),
                    self.tr(
                        "<p>The file <b>{0}</b> does not exist or"
                        " is zero length.</p>"
                    ).format(fn),
                )
                return

        if OSUtilities.isMacPlatform():
            designer, args = QtUtilities.prepareQtMacBundle("designer", args)
        else:
            designer = os.path.join(
                QtUtilities.getQtBinariesPath(),
                QtUtilities.generateQtToolName("designer"),
            )
            if OSUtilities.isWindowsPlatform():
                designer += ".exe"

        if designer:
            proc = QProcess()
            if not proc.startDetached(designer, args):
                EricMessageBox.critical(
                    self,
                    self.tr("Process Generation Error"),
                    self.tr(
                        "<p>Could not start Qt-Designer.<br>"
                        "Ensure that it is available as <b>{0}</b>.</p>"
                    ).format(designer),
                )
        else:
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "<p>Could not find the Qt-Designer executable.<br>"
                    "Ensure that it is installed and optionally configured on"
                    " the Qt configuration page.</p>"
                ),
            )

    @pyqtSlot()
    @pyqtSlot(str)
    def __linguist(self, fn=None):
        """
        Private slot to start the Qt-Linguist executable.

        @param fn filename of the translation file to be opened
        @type str
        """
        args = []
        if fn is not None:
            fn = fn.replace(".qm", ".ts")
            try:
                if os.path.isfile(fn) and os.path.getsize(fn) and fn not in args:
                    args.append(fn)
                else:
                    EricMessageBox.critical(
                        self,
                        self.tr("Problem"),
                        self.tr(
                            "<p>The file <b>{0}</b> does not exist or"
                            " is zero length.</p>"
                        ).format(fn),
                    )
                    return
            except OSError:
                EricMessageBox.critical(
                    self,
                    self.tr("Problem"),
                    self.tr(
                        "<p>The file <b>{0}</b> does not exist or"
                        " is zero length.</p>"
                    ).format(fn),
                )
                return

        if OSUtilities.isMacPlatform():
            linguist, args = QtUtilities.prepareQtMacBundle("linguist", args)
        else:
            linguist = os.path.join(
                QtUtilities.getQtBinariesPath(),
                QtUtilities.generateQtToolName("linguist"),
            )
            if OSUtilities.isWindowsPlatform():
                linguist += ".exe"

        if linguist:
            proc = QProcess()
            if not proc.startDetached(linguist, args):
                EricMessageBox.critical(
                    self,
                    self.tr("Process Generation Error"),
                    self.tr(
                        "<p>Could not start Qt-Linguist.<br>"
                        "Ensure that it is available as <b>{0}</b>.</p>"
                    ).format(linguist),
                )
        else:
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "<p>Could not find the Qt-Linguist executable.<br>"
                    "Ensure that it is installed and optionally configured on"
                    " the Qt configuration page.</p>"
                ),
            )

    def __assistant(self, home=None):
        """
        Private slot to start the Qt-Assistant executable.

        @param home full pathname of a file to display
        @type str
        """
        args = []
        if home:
            args.append("-showUrl")
            args.append(home)

        if OSUtilities.isMacPlatform():
            assistant, args = QtUtilities.prepareQtMacBundle("assistant", args)
        else:
            assistant = os.path.join(
                QtUtilities.getQtBinariesPath(),
                QtUtilities.generateQtToolName("assistant"),
            )
            if OSUtilities.isWindowsPlatform():
                assistant += ".exe"

        if assistant:
            proc = QProcess()
            if not proc.startDetached(assistant, args):
                EricMessageBox.critical(
                    self,
                    self.tr("Process Generation Error"),
                    self.tr(
                        "<p>Could not start Qt-Assistant.<br>"
                        "Ensure that it is available as <b>{0}</b>.</p>"
                    ).format(assistant),
                )
        else:
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "<p>Could not find the Qt-Assistant executable.<br>"
                    "Ensure that it is installed and optionally configured on"
                    " the Qt configuration page.</p>"
                ),
            )

    def __startWebBrowser(self):
        """
        Private slot to start the eric web browser.
        """
        self.launchHelpViewer("")

    @pyqtSlot()
    def __startFido2SecurityKeyMgmt(self):
        """
        Private slot to start the FIDO2 Security Key Management.
        """
        fido2Mgmt = os.path.join(os.path.dirname(__file__), "..", "eric7_fido2.py")
        QProcess.startDetached(PythonUtilities.getPythonExecutable(), [fido2Mgmt])

    def __customViewer(self, home=None):
        """
        Private slot to start a custom viewer.

        @param home full pathname of a file to display
        @type str
        """
        customViewer = Preferences.getHelp("CustomViewer")
        if not customViewer:
            EricMessageBox.information(
                self,
                self.tr("Help"),
                self.tr(
                    """Currently no custom viewer is selected."""
                    """ Please use the preferences dialog to specify one."""
                ),
            )
            return

        proc = QProcess()
        args = []
        if home:
            args.append(home)

        if not proc.startDetached(customViewer, args):
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "<p>Could not start custom viewer.<br>"
                    "Ensure that it is available as <b>{0}</b>.</p>"
                ).format(customViewer),
            )

    def __chmViewer(self, home=None):
        """
        Private slot to start the win help viewer to show *.chm files.

        @param home full pathname of a file to display
        @type str
        """
        if home:
            proc = QProcess()
            args = []
            args.append(home)

            if not proc.startDetached("hh", args):
                EricMessageBox.critical(
                    self,
                    self.tr("Process Generation Error"),
                    self.tr(
                        "<p>Could not start the help viewer.<br>"
                        "Ensure that it is available as <b>hh</b>.</p>"
                    ),
                )

    @pyqtSlot()
    @pyqtSlot(str)
    def __UIPreviewer(self, fn=None):
        """
        Private slot to start the UI Previewer executable.

        @param fn filename of the form to be previewed
        @type str
        """
        proc = QProcess()

        viewer = os.path.join(getConfig("ericDir"), "eric7_uipreviewer.py")

        args = []
        args.append(viewer)

        if fn is not None:
            try:
                if os.path.isfile(fn) and os.path.getsize(fn):
                    args.append(fn)
                else:
                    EricMessageBox.critical(
                        self,
                        self.tr("Problem"),
                        self.tr(
                            "<p>The file <b>{0}</b> does not exist or"
                            " is zero length.</p>"
                        ).format(fn),
                    )
                    return
            except OSError:
                EricMessageBox.critical(
                    self,
                    self.tr("Problem"),
                    self.tr(
                        "<p>The file <b>{0}</b> does not exist or"
                        " is zero length.</p>"
                    ).format(fn),
                )
                return

        if not os.path.isfile(viewer) or not proc.startDetached(
            PythonUtilities.getPythonExecutable(), args
        ):
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "<p>Could not start UI Previewer.<br>"
                    "Ensure that it is available as <b>{0}</b>.</p>"
                ).format(viewer),
            )

    @pyqtSlot()
    @pyqtSlot(list)
    @pyqtSlot(list, bool)
    def __TRPreviewer(self, fileNames=None, ignore=False):
        """
        Private slot to start the Translation Previewer executable.

        @param fileNames filenames of forms and/or translations to be previewed
        @type list of str
        @param ignore flag indicating non existing files should be ignored
        @type bool
        """
        proc = QProcess()

        viewer = os.path.join(getConfig("ericDir"), "eric7_trpreviewer.py")

        args = []
        args.append(viewer)

        if fileNames is not None:
            for fn in fileNames:
                try:
                    if os.path.isfile(fn) and os.path.getsize(fn):
                        args.append(fn)
                    else:
                        if not ignore:
                            EricMessageBox.critical(
                                self,
                                self.tr("Problem"),
                                self.tr(
                                    "<p>The file <b>{0}</b> does not exist or"
                                    " is zero length.</p>"
                                ).format(fn),
                            )
                            return
                except OSError:
                    if not ignore:
                        EricMessageBox.critical(
                            self,
                            self.tr("Problem"),
                            self.tr(
                                "<p>The file <b>{0}</b> does not exist or"
                                " is zero length.</p>"
                            ).format(fn),
                        )
                        return

        if not os.path.isfile(viewer) or not proc.startDetached(
            PythonUtilities.getPythonExecutable(), args
        ):
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "<p>Could not start Translation Previewer.<br>"
                    "Ensure that it is available as <b>{0}</b>.</p>"
                ).format(viewer),
            )

    def __sqlBrowser(self):
        """
        Private slot to start the SQL browser tool.
        """
        proc = QProcess()

        browser = os.path.join(getConfig("ericDir"), "eric7_sqlbrowser.py")

        args = []
        args.append(browser)

        if not os.path.isfile(browser) or not proc.startDetached(
            PythonUtilities.getPythonExecutable(), args
        ):
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "<p>Could not start SQL Browser.<br>"
                    "Ensure that it is available as <b>{0}</b>.</p>"
                ).format(browser),
            )

    @pyqtSlot()
    @pyqtSlot(str)
    def __openHexEditor(self, fn=""):
        """
        Private slot to open the hex editor window.

        @param fn path of the file to show (defaults to "")
        @type str (optional)
        """
        from eric7.HexEdit.HexEditMainWindow import HexEditMainWindow

        dlg = HexEditMainWindow(fn, self, fromEric=True, project=self.project)
        dlg.show()

    @pyqtSlot()
    @pyqtSlot(str)
    def __openPdfViewer(self, fn=""):
        """
        Private slot to open the PDF viewer window.

        @param fn path of the file to show (defaults to "")
        @type str (optional)
        """
        from eric7.PdfViewer.PdfViewerWindow import PdfViewerWindow

        dlg = PdfViewerWindow(fn, self, fromEric=True, project=self.project)
        dlg.show()

    @pyqtSlot()
    @pyqtSlot(str)
    def __editPixmap(self, fn=""):
        """
        Private slot to show a pixmap in a dialog.

        @param fn path of the file to show (defaults to "")
        @type str (optional)
        """
        from eric7.IconEditor.IconEditorWindow import IconEditorWindow

        dlg = IconEditorWindow(fn, self, fromEric=True, project=self.project)
        dlg.show()

    @pyqtSlot(str)
    def __showPixmap(self, fn):
        """
        Private slot to show a pixmap in a dialog.

        @param fn path of the file to show (defaults to "")
        @type str (optional)
        """
        from eric7.Graphics.PixmapDiagram import PixmapDiagram

        dlg = PixmapDiagram(fn, self)
        if dlg.getStatus():
            dlg.show()

    @pyqtSlot(str)
    def __showSvg(self, fn):
        """
        Private slot to show a SVG file in a dialog.

        @param fn filename of the file to show
        @type str
        """
        from eric7.Graphics.SvgDiagram import SvgDiagram

        dlg = SvgDiagram(fn, self)
        dlg.show()

    @pyqtSlot(str)
    def __showUml(self, fn):
        """
        Private slot to show an eric graphics file in a dialog.

        @param fn name of the file to be shown
        @type str
        """
        from eric7.Graphics.UMLDialog import UMLDialog, UMLDialogType

        dlg = UMLDialog(UMLDialogType.NO_DIAGRAM, self.project, parent=self)
        if dlg.load(fn):
            dlg.show(fromFile=True)

    def __snapshot(self):
        """
        Private slot to start the snapshot tool.
        """
        if DesktopUtilities.isWaylandSession():
            EricMessageBox.critical(
                self,
                self.tr("Snapshot"),
                self.tr(
                    "<p>The snapshot utility is not available for Wayland desktop"
                    " sessions.</p>"
                ),
            )
            return

        proc = QProcess()

        snap = os.path.join(getConfig("ericDir"), "eric7_snap.py")

        args = []
        args.append(snap)

        if not os.path.isfile(snap) or not proc.startDetached(
            PythonUtilities.getPythonExecutable(), args
        ):
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "<p>Could not start Snapshot tool.<br>"
                    "Ensure that it is available as <b>{0}</b>.</p>"
                ).format(snap),
            )

    def __toolActionTriggered(self, act):
        """
        Private slot called by external tools toolbar actions.

        @param act reference to the action that triggered the slot
        @type QAction
        """
        toolGroupName, toolMenuText = act.objectName().split("@@", 1)
        for toolGroup in self.toolGroups:
            if toolGroup[0] == toolGroupName:
                for tool in toolGroup[1]:
                    if tool["menutext"] == toolMenuText:
                        self.__startToolProcess(tool)
                        return

                EricMessageBox.information(
                    self,
                    self.tr("External Tools"),
                    self.tr(
                        """No tool entry found for external tool '{0}' """
                        """in tool group '{1}'."""
                    ).format(toolMenuText, toolGroupName),
                )
                return

        EricMessageBox.information(
            self,
            self.tr("External Tools"),
            self.tr("""No toolgroup entry '{0}' found.""").format(toolGroupName),
        )

    def __toolExecute(self, act):
        """
        Private slot to execute a particular tool.

        @param act reference to the action that was triggered
        @type QAction
        """
        if self.toolGroupsMenuTriggered:
            # ignore actions triggered from the select tool group submenu
            self.toolGroupsMenuTriggered = False
            return

        if self.currentToolGroup < 0:
            # it was an action not to be handled here
            return

        idx = act.data()
        if idx is not None and idx >= 0:
            tool = self.toolGroups[self.currentToolGroup][1][idx]
            self.__startToolProcess(tool)

    def __startToolProcess(self, tool):
        """
        Private slot to start an external tool process.

        @param tool dictionary of tool entries
        @type dict
        """
        proc = QProcess(self)
        procData = (None,)
        program = tool["executable"]
        args = []
        argv = Utilities.parseOptionString(tool["arguments"])
        args.extend(argv)
        t = self.tr("Starting process '{0} {1}'.\n").format(program, tool["arguments"])
        self.appendToStdout(t)

        proc.finished.connect(self.__toolFinished)
        if tool["redirect"] != "no":
            proc.readyReadStandardOutput.connect(self.__processToolStdout)
            proc.readyReadStandardError.connect(self.__processToolStderr)
            if tool["redirect"] in ["insert", "replaceSelection"]:
                aw = self.viewmanager.activeWindow()
                procData = (aw, tool["redirect"], [])
                if aw is not None:
                    aw.beginUndoAction()

        proc.start(program, args)
        if not proc.waitForStarted():
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "<p>Could not start the tool entry <b>{0}</b>.<br>"
                    "Ensure that it is available as <b>{1}</b>.</p>"
                ).format(tool["menutext"], tool["executable"]),
            )
        else:
            self.toolProcs.append((program, proc, procData))
            if tool["redirect"] == "no":
                proc.closeReadChannel(QProcess.ProcessChannel.StandardOutput)
                proc.closeReadChannel(QProcess.ProcessChannel.StandardError)
                proc.closeWriteChannel()

    def __processToolStdout(self):
        """
        Private slot to handle the readyReadStdout signal of a tool process.
        """
        ioEncoding = Preferences.getSystem("IOEncoding")

        # loop through all running tool processes
        for program, toolProc, toolProcData in self.toolProcs:
            toolProc.setReadChannel(QProcess.ProcessChannel.StandardOutput)

            if toolProcData[0] is None or toolProcData[1] not in [
                "insert",
                "replaceSelection",
            ]:
                # not connected to an editor or wrong mode
                while toolProc.canReadLine():
                    output = str(toolProc.readLine(), ioEncoding, "replace")
                    s = "{0} - {1}".format(program, output)
                    self.appendToStdout(s)
            else:
                if toolProcData[1] == "insert":
                    text = str(toolProc.readAll(), ioEncoding, "replace")
                    toolProcData[0].insert(text)
                elif toolProcData[1] == "replaceSelection":
                    text = str(toolProc.readAll(), ioEncoding, "replace")
                    toolProcData[2].append(text)

    def __processToolStderr(self):
        """
        Private slot to handle the readyReadStderr signal of a tool process.
        """
        ioEncoding = Preferences.getSystem("IOEncoding")

        # loop through all running tool processes
        for program, toolProc, _toolProcData in self.toolProcs:
            toolProc.setReadChannel(QProcess.ProcessChannel.StandardError)

            while toolProc.canReadLine():
                error = str(toolProc.readLine(), ioEncoding, "replace")
                s = "{0} - {1}".format(program, error)
                self.appendToStderr(s)

    @pyqtSlot(int, QProcess.ExitStatus)
    def __toolFinished(self, exitCode, exitStatus):
        """
        Private slot to handle the finished signal of a tool process.

        @param exitCode exit code of the process
        @type int
        @param exitStatus exit status of the process
        @type QProcess.ExitStatus
        """
        exitedProcs = []

        # loop through all running tool processes
        for program, toolProc, toolProcData in self.toolProcs:
            if toolProc.state() == QProcess.ProcessState.NotRunning:
                exitedProcs.append((program, toolProc, toolProcData))
                if toolProcData[0] is not None:
                    if toolProcData[1] == "replaceSelection":
                        text = "".join(toolProcData[2])
                        toolProcData[0].replace(text)
                    toolProcData[0].endUndoAction()

        # now delete the exited processes from the list of running processes
        for proc in exitedProcs:
            self.toolProcs.remove(proc)
            t = self.tr("Process '{0}' has exited.\n").format(proc[0])
            self.appendToStdout(t)
            proc.deleteLater()

    def __showPythonDoc(self):
        """
        Private slot to show the Python 3 documentation.
        """
        pythonDocDir = Preferences.getHelp("PythonDocDir")
        if not pythonDocDir:
            if OSUtilities.isWindowsPlatform():
                venvName = Preferences.getDebugger("Python3VirtualEnv")
                interpreter = (
                    ericApp()
                    .getObject("VirtualEnvManager")
                    .getVirtualenvInterpreter(venvName)
                )
                if interpreter:
                    default = os.path.join(os.path.dirname(interpreter), "doc")
                else:
                    default = ""
                pythonDocDir = OSUtilities.getEnvironmentEntry("PYTHON3DOCDIR", default)
            else:
                pythonDocDir = OSUtilities.getEnvironmentEntry(
                    "PYTHON3DOCDIR", "/usr/share/doc/packages/python3/html"
                )
        if not pythonDocDir.startswith(("http://", "https://", "qthelp://")):
            if pythonDocDir.startswith("file://"):
                pythonDocDir = pythonDocDir[7:]
            if not os.path.splitext(pythonDocDir)[1]:
                home = FileSystemUtilities.normjoinpath(pythonDocDir, "index.html")

                if OSUtilities.isWindowsPlatform() and not os.path.exists(home):
                    pyversion = sys.hexversion >> 16
                    vers = "{0:d}{1:d}".format(
                        (pyversion >> 8) & 0xFF, pyversion & 0xFF
                    )
                    home = os.path.join(pythonDocDir, "python{0}.chm".format(vers))
            else:
                home = pythonDocDir

            if not os.path.exists(home):
                EricMessageBox.warning(
                    self,
                    self.tr("Documentation Missing"),
                    self.tr(
                        """<p>The documentation starting point"""
                        """ "<b>{0}</b>" could not be found.</p>"""
                    ).format(home),
                )
                return

            if not home.endswith(".chm"):
                if OSUtilities.isWindowsPlatform():
                    home = "file:///" + FileSystemUtilities.fromNativeSeparators(home)
                else:
                    home = "file://" + home
        else:
            home = pythonDocDir

        if home.endswith(".chm"):
            self.__chmViewer(home)
        else:
            hvType = Preferences.getHelp("HelpViewerType")
            if hvType == 0:
                self.__activateHelpViewerWidget(urlStr=home)
            elif hvType == 1:
                self.launchHelpViewer(home)
            elif hvType == 2:
                if home.startswith("qthelp://"):
                    self.__assistant(home)
                else:
                    self.__webBrowser(home)
            elif hvType == 3:
                self.__webBrowser(home)
            else:
                self.__customViewer(home)

    def __showQtDoc(self, version):
        """
        Private method to show the Qt documentation.

        @param version Qt version to show documentation for
        @type int
        """
        if version in [5, 6]:
            qtDocDir = Preferences.getQtDocDir(version)
        else:
            return

        if qtDocDir.startswith("qthelp://"):
            if not os.path.splitext(qtDocDir)[1]:
                home = qtDocDir + "/index.html"
            else:
                home = qtDocDir
        elif qtDocDir.startswith(("http://", "https://")):
            home = qtDocDir
        else:
            if qtDocDir.startswith("file://"):
                qtDocDir = qtDocDir[7:]
            if not os.path.splitext(qtDocDir)[1]:
                home = FileSystemUtilities.normjoinpath(qtDocDir, "index.html")
            else:
                home = qtDocDir

            if not os.path.exists(home):
                EricMessageBox.warning(
                    self,
                    self.tr("Documentation Missing"),
                    self.tr(
                        """<p>The documentation starting point"""
                        """ "<b>{0}</b>" could not be found.</p>"""
                    ).format(home),
                )
                return

            if OSUtilities.isWindowsPlatform():
                home = "file:///" + FileSystemUtilities.fromNativeSeparators(home)
            else:
                home = "file://" + home

        hvType = Preferences.getHelp("HelpViewerType")
        if hvType == 0:
            self.__activateHelpViewerWidget(urlStr=home)
        elif hvType == 1:
            self.launchHelpViewer(home)
        elif hvType == 2:
            if home.startswith("qthelp://"):
                self.__assistant(home)
            else:
                self.__webBrowser(home)
        elif hvType == 3:
            self.__webBrowser(home)
        else:
            self.__customViewer(home)

    def __showPyQtDoc(self, variant=5):
        """
        Private slot to show the PyQt5/6 documentation.

        @param variant PyQt variant to show documentation for (5 or 6)
        @type int or str
        """
        pyqtDocDir = Preferences.getHelp("PyQt{0}DocDir".format(variant))
        if not pyqtDocDir:
            pyqtDocDir = OSUtilities.getEnvironmentEntry(
                "PYQT{0}DOCDIR".format(variant), None
            )

        if not pyqtDocDir:
            EricMessageBox.warning(
                self,
                self.tr("Documentation"),
                self.tr(
                    """<p>The PyQt{0} documentation starting point"""
                    """ has not been configured.</p>"""
                ).format(variant),
            )
            return

        if not pyqtDocDir.startswith(("http://", "https://", "qthelp://")):
            home = ""
            if pyqtDocDir:
                if pyqtDocDir.startswith("file://"):
                    pyqtDocDir = pyqtDocDir[7:]
                if not os.path.splitext(pyqtDocDir)[1]:
                    possibleHomes = [
                        FileSystemUtilities.normjoinpath(pyqtDocDir, "index.html"),
                        FileSystemUtilities.normjoinpath(
                            pyqtDocDir, "class_reference.html"
                        ),
                    ]
                    for possibleHome in possibleHomes:
                        if os.path.exists(possibleHome):
                            home = possibleHome
                            break
                else:
                    home = pyqtDocDir

            if not home or not os.path.exists(home):
                EricMessageBox.warning(
                    self,
                    self.tr("Documentation Missing"),
                    self.tr(
                        """<p>The documentation starting point"""
                        """ "<b>{0}</b>" could not be found.</p>"""
                    ).format(home),
                )
                return

            if OSUtilities.isWindowsPlatform():
                home = "file:///" + FileSystemUtilities.fromNativeSeparators(home)
            else:
                home = "file://" + home
        else:
            home = pyqtDocDir

        hvType = Preferences.getHelp("HelpViewerType")
        if hvType == 0:
            self.__activateHelpViewerWidget(urlStr=home)
        elif hvType == 1:
            self.launchHelpViewer(home)
        elif hvType == 2:
            if home.startswith("qthelp://"):
                self.__assistant(home)
            else:
                self.__webBrowser(home)
        elif hvType == 3:
            self.__webBrowser(home)
        else:
            self.__customViewer(home)

    def __showEricDoc(self):
        """
        Private slot to show the Eric documentation.
        """
        home = Preferences.getHelp("EricDocDir")
        if not home:
            home = FileSystemUtilities.normjoinpath(
                getConfig("ericDocDir"), "Source", "index.html"
            )

        if not home.startswith(("http://", "https://", "qthelp://")):
            if not os.path.exists(home):
                EricMessageBox.warning(
                    self,
                    self.tr("Documentation Missing"),
                    self.tr(
                        """<p>The documentation starting point"""
                        """ "<b>{0}</b>" could not be found.</p>"""
                    ).format(home),
                )
                return

            if OSUtilities.isWindowsPlatform():
                home = "file:///" + FileSystemUtilities.fromNativeSeparators(home)
            else:
                home = "file://" + home

        hvType = Preferences.getHelp("HelpViewerType")
        if hvType == 0:
            self.__activateHelpViewerWidget(urlStr=home)
        elif hvType == 1:
            self.launchHelpViewer(home)
        elif hvType == 2:
            if home.startswith("qthelp://"):
                self.__assistant(home)
            else:
                self.__webBrowser(home)
        elif hvType == 3:
            self.__webBrowser(home)
        else:
            self.__customViewer(home)

    def __showPySideDoc(self, variant=2):
        """
        Private slot to show the PySide2/PySide6 documentation.

        @param variant PySide variant (2 or 6)
        @type int or str
        """
        pysideDocDir = Preferences.getHelp("PySide{0}DocDir".format(variant))
        if not pysideDocDir:
            pysideDocDir = OSUtilities.getEnvironmentEntry(
                "PYSIDE{0}DOCDIR".format(variant), None
            )

        if not pysideDocDir:
            EricMessageBox.warning(
                self,
                self.tr("Documentation"),
                self.tr(
                    """<p>The PySide{0} documentation starting point"""
                    """ has not been configured.</p>"""
                ).format(variant),
            )
            return

        if not pysideDocDir.startswith(("http://", "https://", "qthelp://")):
            if pysideDocDir.startswith("file://"):
                pysideDocDir = pysideDocDir[7:]
            if not os.path.splitext(pysideDocDir)[1]:
                home = FileSystemUtilities.normjoinpath(pysideDocDir, "index.html")
            else:
                home = pysideDocDir
            if not os.path.exists(home):
                EricMessageBox.warning(
                    self,
                    self.tr("Documentation Missing"),
                    self.tr(
                        """<p>The documentation starting point"""
                        """ "<b>{0}</b>" could not be found.</p>"""
                    ).format(home),
                )
                return

            if OSUtilities.isWindowsPlatform():
                home = "file:///" + FileSystemUtilities.fromNativeSeparators(home)
            else:
                home = "file://" + home
        else:
            home = pysideDocDir

        hvType = Preferences.getHelp("HelpViewerType")
        if hvType == 0:
            self.__activateHelpViewerWidget(urlStr=home)
        elif hvType == 1:
            self.launchHelpViewer(home)
        elif hvType == 2:
            if home.startswith("qthelp://"):
                self.__assistant(home)
            else:
                self.__webBrowser(home)
        elif hvType == 3:
            self.__webBrowser(home)
        else:
            self.__customViewer(home)

    @pyqtSlot(QUrl)
    def handleUrl(self, url):
        """
        Public slot to handle opening a URL.

        @param url URL to be shown
        @type QUrl
        """
        self.launchHelpViewer(url)

    def launchHelpViewer(self, home, searchWord=None):
        """
        Public slot to start the help viewer/web browser.

        @param home filename of file to be shown or URL to be opened
        @type str or QUrl
        @param searchWord word to search for
        @type str
        """
        if isinstance(home, QUrl):
            home = home.toString(QUrl.UrlFormattingOption.None_)

        if len(home) > 0:
            homeUrl = QUrl(home)
            if not homeUrl.scheme():
                home = QUrl.fromLocalFile(home).toString()

        launchResult = self.__launchExternalWebBrowser(home, searchWord=searchWord)
        if not launchResult:
            self.__webBrowser(home)

    def __launchExternalWebBrowser(self, home, searchWord=None):
        """
        Private method to start an external web browser and communicate with
        it.

        @param home filename of file to be shown or URL to be opened
        @type str
        @param searchWord word to search for
        @type str
        @return flag indicating a successful launch
        @rtype bool
        """
        from eric7.WebBrowser import WebBrowserArgumentsCreator

        clientArgs = []
        if searchWord:
            clientArgs.append("--search={0}".format(searchWord))

        if self.__webBrowserProcess is None:
            webBrowsers = [
                os.path.join(os.path.dirname(__file__), "..", "eric7_browser.py"),
                # QtWebEngine based web browser
            ]
            process = QProcess()
            for browser in webBrowsers:
                args = [
                    browser,
                    "--quiet",
                    "--qthelp",
                    "--single",
                    "--name={0}".format(self.__webBrowserSAName),
                    home,
                ]
                process.start(PythonUtilities.getPythonExecutable(), args)
                if not process.waitForStarted():
                    EricMessageBox.warning(
                        self,
                        self.tr("Start Web Browser"),
                        self.tr("""The eric web browser could not be started."""),
                    )
                    return False

                res = self.__connectToWebBrowser(process)
                if res == 1:
                    # connection unsuccessful
                    return False
                elif res == 0:
                    # successful
                    break
                elif res == -1:
                    # web browser did not start
                    continue
            else:
                return False

            process.finished.connect(self.__webBrowserFinished)
            self.__webBrowserProcess = process

        else:
            clientArgs.append("--new-tab={0}".format(home))

        if clientArgs and self.__webBrowserClient:
            args = WebBrowserArgumentsCreator.createArgparseNamespace(clientArgs)
            self.__webBrowserClient.processArgs(args, disconnect=False)

        return True

    def __connectToWebBrowser(self, process):
        """
        Private method to connect to a started web browser.

        @param process reference to the started web browser process
        @type QProcess
        @return error indication (1 = connection not possible, 0 = ok,
            -1 = server exited with an error code)
        @rtype int
        """
        from eric7.WebBrowser.WebBrowserSingleApplication import (
            WebBrowserSingleApplicationClient,
        )

        webBrowserClient = WebBrowserSingleApplicationClient(self.__webBrowserSAName)
        connectCount = 30
        while connectCount:
            res = webBrowserClient.connect()
            if res != 0:
                break
            else:
                connectCount -= 1
                QThread.msleep(1000)
                QApplication.processEvents()
            if (
                process.state() == QProcess.ProcessState.NotRunning
                and process.exitStatus() == QProcess.ExitStatus.NormalExit
                and process.exitCode() == 100
            ):
                # Process exited prematurely due to missing pre-requisites
                return -1
        if res <= 0:
            EricMessageBox.warning(
                self,
                self.tr("Start Web Browser"),
                self.tr(
                    """<p>The eric web browser is not started.</p>"""
                    """<p>Reason: {0}</p>"""
                ).format(webBrowserClient.errstr()),
            )
            return 1

        self.__webBrowserClient = webBrowserClient
        return 0

    def __webBrowserFinished(self):
        """
        Private slot handling the end of the external web browser process.
        """
        self.__webBrowserProcess = None
        self.__webBrowserClient = None

    def __webBrowserShutdown(self):
        """
        Private method to shut down the web browser.
        """
        from eric7.WebBrowser import WebBrowserArgumentsCreator

        args = WebBrowserArgumentsCreator.createArgparseNamespace(["--shutdown"])
        self.__webBrowserClient.processArgs(args, disconnect=False)

    def __helpViewer(self):
        """
        Private slot to start an empty help viewer/web browser.
        """
        searchWord = self.viewmanager.textForFind(False)
        if searchWord == "":
            searchWord = None

        self.launchHelpViewer("", searchWord=searchWord)

    def __webBrowser(self, home=""):
        """
        Private slot to start the eric web browser.

        @param home full pathname of a file to display
        @type str
        """
        started = QDesktopServices.openUrl(QUrl(home))
        if not started:
            EricMessageBox.critical(
                self, self.tr("Open Browser"), self.tr("Could not start a web browser")
            )

    @pyqtSlot()
    @pyqtSlot(str)
    def showPreferences(self, pageName=None):
        """
        Public slot to set the preferences.

        @param pageName name of the configuration page to show
        @type str
        """
        from eric7.Preferences.ConfigurationDialog import ConfigurationDialog

        if self.__configurationDialog is None:
            # only one invocation at a time is allowed
            self.__configurationDialog = ConfigurationDialog(
                parent=self,
                name="Configuration",
                expandedEntries=self.__expandedConfigurationEntries,
            )
            self.__configurationDialog.preferencesChanged.connect(
                self.__preferencesChanged
            )
            self.__configurationDialog.mainPasswordChanged.connect(
                self.__mainPasswordChanged
            )
            self.__configurationDialog.show()
            if pageName is not None:
                self.__configurationDialog.showConfigurationPageByName(pageName)
            elif self.__lastConfigurationPageName:
                self.__configurationDialog.showConfigurationPageByName(
                    self.__lastConfigurationPageName
                )
            else:
                self.__configurationDialog.showConfigurationPageByName("empty")
            self.__configurationDialog.exec()
            QApplication.processEvents()
            if self.__configurationDialog.result() == QDialog.DialogCode.Accepted:
                self.__configurationDialog.setPreferences()
                Preferences.syncPreferences()
                self.__preferencesChanged()
            self.__lastConfigurationPageName = (
                self.__configurationDialog.getConfigurationPageName()
            )
            self.__expandedConfigurationEntries = (
                self.__configurationDialog.getExpandedEntries()
            )

            self.__configurationDialog.deleteLater()
            self.__configurationDialog = None

    @pyqtSlot()
    def __exportPreferences(self):
        """
        Private slot to export the current preferences.
        """
        Preferences.exportPreferences()

    @pyqtSlot()
    def __importPreferences(self):
        """
        Private slot to from eric7 import Preferences.
        """
        Preferences.importPreferences()
        self.__preferencesChanged()

    @pyqtSlot()
    def __exportTheme(self):
        """
        Private slot to export the current theme to a file.
        """
        from eric7.Preferences.ThemeManager import ThemeManager

        ThemeManager().exportTheme()

    @pyqtSlot()
    def __importTheme(self):
        """
        Private slot to import a previously exported theme.
        """
        from eric7.Preferences.ThemeManager import ThemeManager

        if ThemeManager().importTheme():
            self.__preferencesChanged()

    @pyqtSlot()
    def __preferencesChanged(self):
        """
        Private slot to handle a change of the preferences.
        """
        from eric7.HexEdit.HexEditMainWindow import HexEditMainWindow

        self.setStyle(
            styleName=Preferences.getUI("Style"),
            styleSheetFile=Preferences.getUI("StyleSheet"),
            itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
        )

        if Preferences.getUI("SingleApplicationMode"):
            if self.SAServer is None:
                self.SAServer = EricSingleApplicationServer()
        else:
            if self.SAServer is not None:
                self.SAServer.shutdown()
                self.SAServer = None
        self.newWindowAct.setEnabled(not Preferences.getUI("SingleApplicationMode"))

        if self.__layoutType == "Sidebars":
            self.leftSidebar.setIconBarColor(Preferences.getUI("IconBarColor"))
            self.leftSidebar.setIconBarSize(Preferences.getUI("IconBarSize"))

            self.bottomSidebar.setIconBarColor(Preferences.getUI("IconBarColor"))
            self.bottomSidebar.setIconBarSize(Preferences.getUI("IconBarSize"))

            if self.rightSidebar:
                self.rightSidebar.setIconBarColor(Preferences.getUI("IconBarColor"))
                self.rightSidebar.setIconBarSize(Preferences.getUI("IconBarSize"))

        self.toolbarManager.setIconSize(Preferences.getIcons("IconSize"))

        self.maxEditorPathLen = Preferences.getUI("CaptionFilenameLength")
        self.captionShowsFilename = Preferences.getUI("CaptionShowsFilename")
        if not self.captionShowsFilename:
            self.__setWindowCaption(editor="")
        else:
            aw = self.viewmanager.activeWindow()
            fn = aw and aw.getFileName() or None
            if fn:
                self.__setWindowCaption(editor=fn)
            else:
                self.__setWindowCaption(editor="")

        self.performVersionCheck()

        SpellChecker.setDefaultLanguage(
            Preferences.getEditor("SpellCheckingDefaultLanguage")
        )

        with contextlib.suppress(ImportError, AttributeError):
            from eric7.EricWidgets.EricSpellCheckedTextEdit import (  # noqa: I101
                SpellCheckMixin,
            )

            pwl = SpellChecker.getUserDictionaryPath(isException=False)
            pel = SpellChecker.getUserDictionaryPath(isException=True)
            SpellCheckMixin.setDefaultLanguage(
                Preferences.getEditor("SpellCheckingDefaultLanguage"), pwl, pel
            )

        if EricPreferences.getNetworkProxy("UseSystemProxy"):
            QNetworkProxyFactory.setUseSystemConfiguration(True)
        else:
            self.__proxyFactory = EricNetworkProxyFactory()
            QNetworkProxyFactory.setApplicationProxyFactory(self.__proxyFactory)
            QNetworkProxyFactory.setUseSystemConfiguration(False)

        for hexEditor in HexEditMainWindow.windows:
            hexEditor.preferencesChanged()

        # set the keyboard input interval
        interval = Preferences.getUI("KeyboardInputInterval")
        if interval > 0:
            QApplication.setKeyboardInputInterval(interval)
        else:
            QApplication.setKeyboardInputInterval(-1)

        if not self.__disableCrashSession:
            if Preferences.getUI("CrashSessionEnabled"):
                self.__writeCrashSession()
            else:
                self.__deleteCrashSession()

        self.preferencesChanged.emit()

    def __mainPasswordChanged(self, oldPassword, newPassword):
        """
        Private slot to handle the change of the main password.

        @param oldPassword current main password
        @type str
        @param newPassword new main password
        @type str
        """
        from eric7 import Globals

        self.mainPasswordChanged.emit(oldPassword, newPassword)
        Preferences.convertPasswords(oldPassword, newPassword)
        variant = Globals.getWebBrowserSupport()
        if variant == "QtWebEngine":
            from eric7.WebBrowser.Passwords.PasswordManager import (  # noqa: I101
                PasswordManager,
            )

            pwManager = PasswordManager()
            pwManager.mainPasswordChanged(oldPassword, newPassword)
        EricUtilities.crypto.changeRememberedMain(newPassword)

    def __reloadAPIs(self):
        """
        Private slot to reload the api information.
        """
        self.reloadAPIs.emit()

    def __showExternalTools(self):
        """
        Private slot to display a dialog show a list of external tools used
        by eric.
        """
        from eric7.Preferences.ProgramsDialog import ProgramsDialog

        if self.programsDialog is None:
            self.programsDialog = ProgramsDialog(self)
        self.programsDialog.show()

    def __configViewProfiles(self):
        """
        Private slot to configure the various view profiles.
        """
        from eric7.Preferences.ViewProfileDialog import ViewProfileDialog

        dlg = ViewProfileDialog(
            self.__layoutType,
            self.profiles["edit"][1],
            self.profiles["debug"][1],
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            edit, debug = dlg.getVisibilities()
            self.profiles["edit"][1] = edit
            self.profiles["debug"][1] = debug
            Preferences.setUI("ViewProfiles", self.profiles)
            if self.currentProfile == "edit":
                self.__setEditProfile(False)
            elif self.currentProfile == "debug":
                self.setDebugProfile(False)

    def __configToolBars(self):
        """
        Private slot to configure the various toolbars.
        """
        from eric7.EricWidgets.EricToolBarDialog import EricToolBarDialog

        dlg = EricToolBarDialog(self.toolbarManager, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            Preferences.setUI("ToolbarManagerState", self.toolbarManager.saveState())

    def __configShortcuts(self):
        """
        Private slot to configure the keyboard shortcuts.
        """
        from eric7.Preferences.ShortcutsDialog import ShortcutsDialog

        if self.shortcutsDialog is None:
            self.shortcutsDialog = ShortcutsDialog(self)
        self.shortcutsDialog.populate()
        self.shortcutsDialog.show()

    def __exportShortcuts(self):
        """
        Private slot to export the keyboard shortcuts.
        """
        fn, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            None,
            self.tr("Export Keyboard Shortcuts"),
            "",
            self.tr("Keyboard Shortcuts File (*.ekj)"),
            "",
            EricFileDialog.DontConfirmOverwrite,
        )

        if not fn:
            return

        fpath = pathlib.Path(fn)
        if not fpath.suffix:
            ex = selectedFilter.split("(*")[1].split(")")[0]
            if ex:
                fpath = fpath.with_suffix(ex)

        ok = (
            EricMessageBox.yesNo(
                self,
                self.tr("Export Keyboard Shortcuts"),
                self.tr(
                    """<p>The keyboard shortcuts file <b>{0}</b> exists"""
                    """ already. Overwrite it?</p>"""
                ).format(fpath),
            )
            if fpath.exists()
            else True
        )

        if ok:
            Shortcuts.exportShortcuts(str(fpath))

    def __importShortcuts(self):
        """
        Private slot to import the keyboard shortcuts.
        """
        fn = EricFileDialog.getOpenFileName(
            None,
            self.tr("Import Keyboard Shortcuts"),
            "",
            self.tr("Keyboard Shortcuts File (*.ekj)"),
        )

        if fn:
            Shortcuts.importShortcuts(fn)

    def __showCertificatesDialog(self):
        """
        Private slot to show the certificates management dialog.
        """
        from eric7.EricNetwork.EricSslCertificatesDialog import (
            EricSslCertificatesDialog,
        )

        dlg = EricSslCertificatesDialog(settings=Preferences.getSettings(), parent=self)
        dlg.exec()

    def __clearPrivateData(self):
        """
        Private slot to clear the private data lists.
        """
        from .ClearPrivateDataDialog import ClearPrivateDataDialog

        dlg = ClearPrivateDataDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # recent files, recent projects, recent multi  projects,
            # debug histories, shell histories
            (
                files,
                projects,
                multiProjects,
                debug,
                shell,
                testing,
                vcs,
                plugins,
            ) = dlg.getData()
            if files:
                # clear list of recently opened files
                self.viewmanager.clearRecent()
            if projects:
                # clear list of recently opened projects and other histories
                self.project.clearHistories()
            if multiProjects:
                # clear list of recently opened multi projects
                self.multiProject.clearRecent()
            if debug:
                # clear the various debug histories
                self.debuggerUI.clearHistories()
            if shell:
                # clear the shell histories
                self.shell.clearAllHistories()
            if testing:
                # clear the unit test histories
                if self.__testingWidget is None:
                    clearSavedHistories()
                else:
                    self.__testingWidget.clearRecent()
            if vcs:
                # clear the VCS related histories
                self.pluginManager.clearPluginsPrivateData("version_control")
            if plugins:
                # clear private data of plug-ins not covered above
                self.pluginManager.clearPluginsPrivateData("")

            Preferences.syncPreferences()

    def __newProject(self):
        """
        Private slot to handle the NewProject signal.
        """
        self.__setWindowCaption(project=self.project.name)

    def __projectOpened(self):
        """
        Private slot to handle the projectOpened signal.
        """
        from eric7 import Testing

        self.__setWindowCaption(project=self.project.name)
        supported = Testing.isLanguageSupported(self.project.getProjectLanguage())
        self.testProjectAct.setEnabled(supported)
        self.__testingProjectOpen = supported

    def __projectClosed(self):
        """
        Private slot to handle the projectClosed signal.
        """
        self.__setWindowCaption(project="")
        self.testProjectAct.setEnabled(False)
        if not self.__testingEditorOpen:
            self.restartTestAct.setEnabled(False)
            self.rerunFailedTestsAct.setEnabled(False)
        self.__testingProjectOpen = False

    def __programChange(self, fn):
        """
        Private slot to handle the programChange signal.

        This primarily is here to set the currentProg variable.

        @param fn filename to be set as current prog
        @type str
        """
        # Delete the old program if there was one.
        if self.currentProg is not None:
            del self.currentProg

        self.currentProg = os.path.normpath(fn)

    def __lastEditorClosed(self):
        """
        Private slot to handle the lastEditorClosed signal.
        """
        self.wizardsMenuAct.setEnabled(False)
        self.testScriptAct.setEnabled(False)
        self.__testingEditorOpen = False
        if not self.__testingProjectOpen:
            self.restartTestAct.setEnabled(False)
            self.rerunFailedTestsAct.setEnabled(False)
        self.__setWindowCaption(editor="")

    def __editorOpened(self, fn):
        """
        Private slot to handle the editorOpened signal.

        @param fn filename of the opened editor
        @type str
        """
        self.wizardsMenuAct.setEnabled(len(self.__menus["wizards"].actions()) > 0)

        if (
            fn
            and str(fn) != "None"
            and Testing.isLanguageSupported(
                self.viewmanager.getOpenEditor(fn).getFileType()
            )
        ):
            self.testScriptAct.setEnabled(True)
            self.__testingEditorOpen = True

    def __checkActions(self, editor):
        """
        Private slot to check some actions for their enable/disable status.

        @param editor editor window
        @type Editor
        """
        fn = editor.getFileName() if editor else None

        if fn and Testing.isLanguageSupported(editor.getFileType()):
            self.testScriptAct.setEnabled(True)
            self.__testingEditorOpen = True
            return

        self.testScriptAct.setEnabled(False)

    def __writeTasks(self):
        """
        Private slot to write the tasks data to a JSON file (.etj).
        """
        fn = os.path.join(EricUtilities.getConfigDir(), "eric7tasks.etj")
        self.__tasksFile.writeFile(fn)

    def __readTasks(self):
        """
        Private slot to read in the tasks file (.etj).
        """
        fn = os.path.join(EricUtilities.getConfigDir(), "eric7tasks.etj")
        if os.path.exists(fn):
            self.__tasksFile.readFile(fn)

    @pyqtSlot()
    def __showSessionsMenu(self):
        """
        Private slot to mofify the state of some session actions.
        """
        crashSessionsAvailable = bool(self.__getCrashedSessions())

        menu = self.__menus["sessions"]
        menu.clear()
        menu.addAction(self.saveSessionAct)
        menu.addAction(self.loadSessionAct)
        menu.addSeparator()
        act = menu.addAction(self.tr("Load crash session..."), self.__loadCrashSession)
        act.setEnabled(crashSessionsAvailable)
        act = menu.addAction(
            self.tr("Clean crash sessions..."), self.__cleanCrashSessions
        )
        act.setEnabled(crashSessionsAvailable)

    def __writeSession(self, filename=""):
        """
        Private slot to write the session data to a JSON file (.esj).

        @param filename name of a session file to write
        @type str
        @return flag indicating success
        @rtype bool
        """
        fn = (
            filename
            if filename
            else os.path.join(EricUtilities.getConfigDir(), "eric7session.esj")
        )

        return self.__sessionFile.writeFile(fn)

    def __readSession(self, filename=""):
        """
        Private slot to read in the session file (.esj).

        @param filename name of a session file to read
        @type str
        @return flag indicating success
        @rtype bool
        """
        if filename:
            fn = filename
        else:
            fn = os.path.join(EricUtilities.getConfigDir(), "eric7session.esj")
            if not os.path.exists(fn):
                EricMessageBox.critical(
                    self,
                    self.tr("Read Session"),
                    self.tr(
                        "<p>The session file <b>{0}</b> could not be read.</p>"
                    ).format(fn),
                )
                fn = ""

        res = False
        if fn:
            self.__readingSession = True
            res = self.__sessionFile.readFile(fn)
            self.__readingSession = False

        # Write a crash session after a session was read.
        self.__writeCrashSession()

        return res

    def __saveSessionToFile(self):
        """
        Private slot to save a session to disk.
        """
        sessionFile, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            self,
            self.tr("Save Session"),
            OSUtilities.getHomeDir(),
            self.tr("eric Session Files (*.esj)"),
            "",
        )

        if not sessionFile:
            return

        fpath = pathlib.Path(sessionFile)
        if not fpath.suffix:
            ex = selectedFilter.split("(*")[1].split(")")[0]
            if ex:
                fpath = fpath.with_suffix(ex)

        self.__writeSession(filename=str(fpath))

    def __loadSessionFromFile(self):
        """
        Private slot to load a session from disk.
        """
        sessionFile = EricFileDialog.getOpenFileName(
            self,
            self.tr("Load session"),
            OSUtilities.getHomeDir(),
            self.tr("eric Session Files (*.esj)"),
        )

        if not sessionFile:
            return

        self.__readSession(filename=sessionFile)

    def __crashSessionFilePath(self, globPattern=False):
        """
        Private method to generate a path name for a unique crash session file.

        @param globPattern flag indicating to get the glob pattern for crash
            session files (defaults to False)
        @type bool (optional)
        @return crash session file path
        @rtype str
        """
        if globPattern:
            return os.path.join(
                EricUtilities.getConfigDir(), "eric7_crash_session_*.esj"
            )
        else:
            return os.path.join(
                EricUtilities.getConfigDir(), f"eric7_crash_session_{os.getpid()}.esj"
            )

    def __getCrashedSessions(self):
        """
        Private method to get a list of crash session file paths of crashed sessions.

        Note: Crashed sessions are those, whose PID does not exist anymore.

        @return list of crashed session file paths
        @rtype list of str
        """
        crashedSessionsList = []

        crashSessionPattern = self.__crashSessionFilePath(globPattern=True)
        crashSessionPatternParts = crashSessionPattern.split("*", 1)
        # crashSessionPatternParts is used to extract the PID from the crash session
        # file path
        crashSessionsList = glob.glob(crashSessionPattern)
        if crashSessionsList:
            for crashSession in crashSessionsList:
                pid = crashSession.replace(crashSessionPatternParts[0], "").replace(
                    crashSessionPatternParts[1], ""
                )
                if not psutil.pid_exists(int(pid)):
                    # it is a real crash session
                    crashedSessionsList.append(crashSession)

        return crashedSessionsList

    def __checkCrashSessionExists(self):
        """
        Private method to check for the existence of crash session files and
        select the one to open.

        @return file path of the crash session file to open. An empty string indicates
            that no crash session file should be opened or exists.
        @rtype str
        """
        selectedCrashSessionFile = ""
        crashedSessionsList = self.__getCrashedSessions()
        if crashedSessionsList:
            dlg = EricListSelectionDialog(
                sorted(crashedSessionsList),
                selectionMode=QAbstractItemView.SelectionMode.SingleSelection,
                title=self.tr("Found Crash Sessions"),
                message=self.tr(
                    "These crash session files were found. Select the one to"
                    " open. Select 'Cancel' to not open a crash session."
                ),
                doubleClickOk=True,
                parent=self,
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                selectedCrashSessionFile = dlg.getSelection()[0]

        return selectedCrashSessionFile

    def __deleteCrashSession(self):
        """
        Private slot to delete the crash session file.
        """
        fn = self.__crashSessionFilePath()
        if os.path.exists(fn):
            with contextlib.suppress(OSError):
                os.remove(fn)

    def __writeCrashSession(self):
        """
        Private slot to write a crash session file.
        """
        if (
            not self.__readingSession
            and not self.__disableCrashSession
            and Preferences.getUI("CrashSessionEnabled")
        ):
            self.__writeSession(filename=self.__crashSessionFilePath())

    def __readCrashSession(self):
        """
        Private method to check for and read a crash session.

        @return flag indicating a crash session file was found and read
        @rtype bool
        """
        res = False
        if (
            not self.__disableCrashSession
            and not self.__noCrashOpenAtStartup
            and Preferences.getUI("OpenCrashSessionOnStartup")
        ):
            fn = self.__checkCrashSessionExists()
            if fn:
                res = self.__readSession(filename=fn)
                if res and Preferences.getUI("DeleteLoadedCrashSession"):
                    os.remove(fn)

        return res

    @pyqtSlot()
    def __loadCrashSession(self):
        """
        Private slot to load a crash session.
        """
        fn = self.__checkCrashSessionExists()
        if fn:
            self.__readSession(filename=fn)

    @pyqtSlot()
    def __cleanCrashSessions(self):
        """
        Private slot to clean all stale crash sessions.
        """
        from .DeleteFilesConfirmationDialog import DeleteFilesConfirmationDialog

        crashedSessionsList = self.__getCrashedSessions()
        if crashedSessionsList:
            dlg = DeleteFilesConfirmationDialog(
                parent=self,
                caption=self.tr("Clean stale crash sessions"),
                message=self.tr(
                    "Do you really want to delete these stale crash session files?"
                ),
                files=sorted(crashedSessionsList),
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                for crashSession in crashedSessionsList:
                    os.remove(crashSession)

    def showFindFileByNameDialog(self):
        """
        Public slot to show the Find File by Name dialog.
        """
        from .FindFileNameDialog import FindFileNameDialog

        if self.findFileNameDialog is None:
            self.findFileNameDialog = FindFileNameDialog(self.project)
            self.findFileNameDialog.sourceFile.connect(self.viewmanager.openSourceFile)
            self.findFileNameDialog.designerFile.connect(self.__designer)
        self.findFileNameDialog.show()
        self.findFileNameDialog.raise_()
        self.findFileNameDialog.activateWindow()

    def showFindFilesWidget(self, txt="", searchDir="", openFiles=False):
        """
        Public slot to show the Find In Files widget.

        @param txt text to search for (defaults to "")
        @type str (optional)
        @param searchDir directory to search in (defaults to "")
        @type str (optional)
        @param openFiles flag indicating to operate on open files only
            (defaults to False)
        @type bool (optional)
        """
        from .FindFileWidget import FindFileDialog

        if Preferences.getUI("ShowFindFileWidget"):
            # embedded tool
            self.__activateFindFileWidget()
            self.__findFileWidget.activate(
                replaceMode=False, txt=txt, searchDir=searchDir, openFiles=openFiles
            )
        else:
            # external dialog
            if self.__findFileDialog is None:
                self.__findFileDialog = FindFileDialog(self.project, self)
                self.__findFileDialog.sourceFile.connect(
                    self.viewmanager.openSourceFile
                )
                self.__findFileDialog.designerFile.connect(self.__designer)
                self.__findFileDialog.linguistFile.connect(self.__linguist)
                self.__findFileDialog.trpreview.connect(self.__TRPreviewer)
                self.__findFileDialog.pixmapFile.connect(self.__showPixmap)
                self.__findFileDialog.svgFile.connect(self.__showSvg)
                self.__findFileDialog.umlFile.connect(self.__showUml)
            self.__findFileDialog.activate(
                replaceMode=False, txt=txt, searchDir=searchDir, openFiles=openFiles
            )

    def showReplaceFilesWidget(self, txt="", searchDir="", openFiles=False):
        """
        Public slot to show the Find In Files widget in replace mode.

        @param txt text to search for (defaults to "")
        @type str (optional)
        @param searchDir directory to search in (defaults to "")
        @type str (optional)
        @param openFiles flag indicating to operate on open files only
            (defaults to False)
        @type bool (optional)
        """
        from .FindFileWidget import FindFileDialog

        if Preferences.getUI("ShowFindFileWidget"):
            # embedded tool
            self.__activateFindFileWidget()
            self.__findFileWidget.activate(
                replaceMode=True, txt=txt, searchDir=searchDir, openFiles=openFiles
            )
        else:
            # external dialog
            if self.__replaceFileDialog is None:
                self.__replaceFileDialog = FindFileDialog(self.project, self)
                self.__replaceFileDialog.sourceFile.connect(
                    self.viewmanager.openSourceFile
                )
                self.__replaceFileDialog.designerFile.connect(self.__designer)
                self.__replaceFileDialog.linguistFile.connect(self.__linguist)
                self.__replaceFileDialog.trpreview.connect(self.__TRPreviewer)
                self.__replaceFileDialog.pixmapFile.connect(self.__showPixmap)
                self.__replaceFileDialog.svgFile.connect(self.__showSvg)
                self.__replaceFileDialog.umlFile.connect(self.__showUml)
            self.__replaceFileDialog.activate(
                replaceMode=True, txt=txt, searchDir=searchDir, openFiles=openFiles
            )

    def __activateFindFileWidget(self):
        """
        Private slot to activate the Find In Files widget.
        """
        if self.__layoutType == "Toolboxes":
            self.lToolboxDock.show()
            self.lToolbox.setCurrentWidget(self.__findFileWidget)
        elif self.__layoutType == "Sidebars":
            self.leftSidebar.show()
            self.leftSidebar.setCurrentWidget(self.__findFileWidget)
        self.__findFileWidget.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

        self.__findFileWidget.activate()

    def showFindLocationWidget(self):
        """
        Public method to show the Find File widget.
        """
        from .FindLocationWidget import FindLocationDialog

        if Preferences.getUI("ShowFindLocationWidget"):
            # embedded tool
            self.__activateFindLocationWidget()
        else:
            # external dialog
            if self.__findLocationDialog is None:
                self.__findLocationDialog = FindLocationDialog(self.project, self)
                self.__findLocationDialog.sourceFile.connect(
                    self.viewmanager.openSourceFile
                )
                self.__findLocationDialog.designerFile.connect(self.__designer)
                self.__findLocationDialog.linguistFile.connect(self.__linguist)
                self.__findLocationDialog.trpreview.connect(self.__TRPreviewer)
                self.__findLocationDialog.pixmapFile.connect(self.__showPixmap)
                self.__findLocationDialog.svgFile.connect(self.__showSvg)
                self.__findLocationDialog.umlFile.connect(self.__showUml)
            self.__findLocationDialog.activate()

    def __activateFindLocationWidget(self):
        """
        Private method to activate the Find File widget.
        """
        if self.__layoutType == "Toolboxes":
            self.lToolboxDock.show()
            self.lToolbox.setCurrentWidget(self.__findLocationWidget)
        elif self.__layoutType == "Sidebars":
            self.leftSidebar.show()
            self.leftSidebar.setCurrentWidget(self.__findLocationWidget)
        self.__findLocationWidget.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

        self.__findLocationWidget.activate()

    def __activateVcsStatusList(self):
        """
        Private slot to activate the VCS Status List.
        """
        if self.__layoutType == "Toolboxes":
            self.lToolboxDock.show()
            self.lToolbox.setCurrentWidget(self.__vcsStatusWidget)
        elif self.__layoutType == "Sidebars":
            self.leftSidebar.show()
            self.leftSidebar.setCurrentWidget(self.__vcsStatusWidget)
        self.__vcsStatusWidget.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def __activateHelpViewerWidget(self, urlStr=None):
        """
        Private method to activate the embedded Help Viewer window.

        @param urlStr URL to be shown
        @type str
        """
        if self.__helpViewerWidget is not None:
            if self.__layoutType == "Toolboxes":
                self.rToolboxDock.show()
                self.rToolbox.setCurrentWidget(self.__helpViewerWidget)
            elif self.__layoutType == "Sidebars":
                self.activateLeftRightSidebarWidget(self.__helpViewerWidget)
            self.__helpViewerWidget.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

            url = None
            searchWord = None

            if urlStr:
                url = QUrl(urlStr)
                if not url.isValid():
                    url = None

            if url is None:
                searchWord = self.viewmanager.textForFind(False)
                if searchWord == "":
                    searchWord = None

            self.__helpViewerWidget.activate(searchWord=searchWord, url=url)

    ##########################################################
    ## Below are slots to handle StdOut and StdErr
    ##########################################################

    def appendToStdout(self, s):
        """
        Public slot to append text to the stdout log viewer tab.

        @param s output to be appended
        @type str
        """
        self.appendStdout.emit(s)

    def appendToStderr(self, s):
        """
        Public slot to append text to the stderr log viewer tab.

        @param s output to be appended
        @type str
        """
        self.appendStderr.emit(s)

    ##########################################################
    ## Below are slots needed by the plugin menu
    ##########################################################

    def __showPluginInfo(self):
        """
        Private slot to show the plugin info dialog.
        """
        from eric7.PluginManager.PluginInfoDialog import PluginInfoDialog

        self.__pluginInfoDialog = PluginInfoDialog(self.pluginManager, self)
        self.__pluginInfoDialog.show()

    @pyqtSlot()
    def __installPlugins(self, pluginFileNames=None):
        """
        Private slot to show a dialog to install a new plugin.

        @param pluginFileNames list of plugin files suggested for
            installation
        @type list of str
        """
        from eric7.PluginManager.PluginInstallDialog import PluginInstallDialog

        self.__pluginInstallDialog = PluginInstallDialog(
            self.pluginManager,
            [] if pluginFileNames is None else pluginFileNames[:],
            self,
        )
        self.__pluginInstallDialog.setModal(False)
        self.__pluginInstallDialog.finished.connect(self.__pluginInstallFinished)
        self.__pluginInstallDialog.show()

    @pyqtSlot()
    def __pluginInstallFinished(self):
        """
        Private slot to handle the finishing of the plugin install dialog.
        """
        if self.__pluginInstallDialog.restartNeeded():
            self.__pluginInstallDialog.deleteLater()
            del self.__pluginInstallDialog
            self.__restart(ask=True)

        self.pluginRepositoryViewer.reloadList()

        if self.__findFileWidget:
            self.__findFileWidget.populateFileCategories()
        if self.__findFileDialog:
            self.__findFileDialog.populateFileCategories()

    def __deinstallPlugin(self):
        """
        Private slot to show a dialog to uninstall a plugin.
        """
        from eric7.PluginManager.PluginUninstallDialog import PluginUninstallDialog

        dlg = PluginUninstallDialog(self.pluginManager, parent=self)
        dlg.exec()

        if self.__findFileWidget:
            self.__findFileWidget.populateFileCategories()
        if self.__findFileDialog:
            self.__findFileDialog.populateFileCategories()

    @pyqtSlot()
    def __showPluginsAvailable(self):
        """
        Private slot to show the plugins available for download.
        """
        from eric7.PluginManager.PluginRepositoryDialog import PluginRepositoryDialog

        dlg = PluginRepositoryDialog(self.pluginManager, parent=self)
        res = dlg.exec()
        if res == (QDialog.DialogCode.Accepted + 1):
            self.__installPlugins(dlg.getDownloadedPlugins())

    def __pluginsConfigure(self):
        """
        Private slot to show the plugin manager configuration page.
        """
        self.showPreferences("pluginManagerPage")

    def checkPluginUpdatesAvailable(self):
        """
        Public method to check the availability of updates of plug-ins.
        """
        if self.isOnline():
            self.pluginManager.checkPluginUpdatesAvailable()

    @pyqtSlot()
    def __installDownloadedPlugins(self):
        """
        Private slot to handle the installation of plugins downloaded via the
        plugin repository viewer.
        """
        self.__installPlugins(self.pluginRepositoryViewer.getDownloadedPlugins())

    @pyqtSlot()
    def activatePluginRepositoryViewer(self):
        """
        Public slot to activate the plugin repository viewer.
        """
        self.pluginRepositoryViewer.reloadList()

        if self.__layoutType == "Toolboxes":
            self.rToolboxDock.show()
            self.rToolbox.setCurrentWidget(self.pluginRepositoryViewer)
        elif self.__layoutType == "Sidebars":
            self.activateLeftRightSidebarWidget(self.pluginRepositoryViewer)
        self.pluginRepositoryViewer.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    #################################################################
    ## Drag and Drop Support
    #################################################################

    def dragEnterEvent(self, event):
        """
        Protected method to handle the drag enter event.

        @param event the drag enter event
        @type QDragEnterEvent
        """
        self.inDragDrop = event.mimeData().hasUrls()
        if self.inDragDrop:
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """
        Protected method to handle the drag move event.

        @param event the drag move event
        @type QDragMoveEvent
        """
        if self.inDragDrop:
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """
        Protected method to handle the drag leave event.

        @param event the drag leave event
        @type QDragLeaveEvent
        """
        if self.inDragDrop:
            self.inDragDrop = False

    def dropEvent(self, event):
        """
        Protected method to handle the drop event.

        @param event the drop event
        @type QDropEvent
        """
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            for url in event.mimeData().urls():
                fname = url.toLocalFile()
                if fname:
                    if pathlib.Path(fname).is_file():
                        self.viewmanager.openSourceFile(fname)
                    else:
                        EricMessageBox.information(
                            self,
                            self.tr("Drop Error"),
                            self.tr("""<p><b>{0}</b> is not a file.</p>""").format(
                                fname
                            ),
                        )

        self.inDragDrop = False

    ##########################################################
    ## Below are methods needed for shutting down the IDE
    ##########################################################

    def closeEvent(self, event):
        """
        Protected event handler for the close event.

        This event handler saves the preferences.

        @param event close event
        @type QCloseEvent
        """
        if self.__shutdown():
            event.accept()
            if not self.inCloseEvent:
                self.inCloseEvent = True
                QTimer.singleShot(0, ericApp().closeAllWindows)
        else:
            event.ignore()

    def __shutdown(self):
        """
        Private method to perform all necessary steps to close down the IDE.

        @return flag indicating success
        @rtype bool
        """
        if self.shutdownCalled:
            return True

        if not self.viewmanager.checkAllDirty():
            return False

        if self.__webBrowserProcess is not None:
            self.__webBrowserShutdown()

        if self.irc is not None and not self.irc.shutdown():
            return False

        sessionCreated = self.__writeSession()

        self.__astViewer.hide()

        self.shell.closeShell()

        if not self.project.closeProject(shutdown=True):
            return False

        if not self.multiProject.closeMultiProject():
            return False

        if not self.viewmanager.closeViewManager():
            return False

        QDesktopServices.unsetUrlHandler("file")
        QDesktopServices.unsetUrlHandler("http")
        QDesktopServices.unsetUrlHandler("https")

        if sessionCreated and not self.__disableCrashSession:
            self.__deleteCrashSession()

        if self.codeDocumentationViewer is not None:
            self.codeDocumentationViewer.shutdown()

        self.__previewer.shutdown()

        self.__astViewer.shutdown()

        self.__writeTasks()

        if self.templateViewer is not None:
            self.templateViewer.save()

        if not self.debuggerUI.shutdownServer():
            return False
        self.debuggerUI.shutdown()

        self.backgroundService.shutdown()

        if self.cooperation is not None:
            self.cooperation.shutdown()

        if self.__helpViewerWidget is not None:
            self.__helpViewerWidget.shutdown()

        if self.microPythonWidget is not None:
            self.microPythonWidget.shutdown()

        self.pipInterface.shutdown()

        self.pluginManager.doShutdown()

        if self.SAServer is not None:
            self.SAServer.shutdown()
            self.SAServer = None

        # set proxy factory to None to avoid crashes
        QNetworkProxyFactory.setApplicationProxyFactory(None)

        Preferences.setGeometry("MainMaximized", self.isMaximized())
        if not self.isMaximized():
            Preferences.setGeometry("MainGeometry", self.saveGeometry())

        if self.browser is not None:
            self.browser.saveToplevelDirs()

        Preferences.setUI("ToolbarManagerState", self.toolbarManager.saveState())
        self.__saveCurrentViewProfile(True)
        Preferences.saveToolGroups(self.toolGroups, self.currentToolGroup)
        Preferences.syncPreferences()
        self.shutdownCalled = True

        # shut down the global file system watcher
        EricFileSystemWatcher.instance().shutdown()

        # revert changes to sys.stdout and sys.stderr
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__

        return True

    def isOnline(self):
        """
        Public method to get the online state.

        @return online state
        @rtype bool
        """
        return self.networkIcon.isOnline()

    def __onlineStateChanged(self, online):
        """
        Private slot handling changes in online state.

        @param online flag indicating the online state
        @type bool
        """
        if online:
            self.performVersionCheck()

    ##############################################
    ## Below are methods to check for new versions
    ##############################################

    def performVersionCheck(self, startup=False):
        """
        Public method to check for an update even if not installed via PyPI.

        @param startup flag indicating a call during the IDE startup (defaults to False)
        @type bool (optional)
        @return flag indicating an upgrade is available and was selected by the user
        @rtype bool
        """
        if self.isOnline():
            if VersionOnly.startswith(("rev_", "@@")):
                # cannot check against development or source installation
                return False
            else:
                period = Preferences.getUI("PerformVersionCheck")
                if period == 0:
                    return False
                elif period in [2, 3, 4]:
                    lastCheck = Preferences.getSettings().value(
                        "Updates/LastCheckDate", QDate(1970, 1, 1)
                    )
                    if lastCheck.isValid():
                        now = QDate.currentDate()
                        if (
                            (period == 2 and lastCheck.daysTo(now) < 1)
                            or (period == 3 and lastCheck.daysTo(now) < 7)
                            or (
                                period == 4
                                and (lastCheck.daysTo(now) < lastCheck.daysInMonth())
                            )
                        ):
                            # daily, weekly, monthly
                            return False

            versionTuple = EricUtilities.versionToTuple(VersionOnly)
            availableVersions = self.pipInterface.getPackageVersions("eric-ide")
            newerVersionsTuple = [
                EricUtilities.versionToTuple(v)
                for v in availableVersions
                if EricUtilities.versionToTuple(v) > versionTuple
            ]
            updateAvailable = bool(newerVersionsTuple)
            if updateAvailable:
                yes = EricMessageBox.yesNo(
                    self,
                    self.tr("Upgrade available"),
                    self.tr(
                        """<p>A newer version of the <b>eric-ide</b> package is"""
                        """ available at <a href="{0}/eric-ide/">"""
                        """PyPI</a>.</p><p>Installed: {1}<br/>Available: <b>{2}</b>"""
                        """</p><p>Shall <b>eric-ide</b> be upgraded?</p>"""
                    ).format(
                        self.pipInterface.getIndexUrlPypi(),
                        VersionOnly,
                        ".".join(
                            str(p)
                            for p in max(newerVersionsTuple)
                            if p not in (0, None)
                        ),
                    ),
                )
                if yes and self.__shutdown():
                    self.__performUpgrade("eric", startup=startup)
                    return True

        return False

    def __sslErrors(self, reply, errors):
        """
        Private slot to handle SSL errors.

        @param reply reference to the reply object
        @type QNetworkReply
        @param errors list of SSL errors
        @type list of QSslError
        """
        ignored = self.__sslErrorHandler.sslErrorsReply(reply, errors)[0]
        if ignored == EricSslErrorState.NOT_IGNORED:
            self.__downloadCancelled = True

    #######################################
    ## Below are methods for various checks
    #######################################

    def checkConfigurationStatus(self):
        """
        Public method to check, if eric has been configured. If it is not,
        the configuration dialog is shown.
        """
        if not Preferences.isConfigured():
            self.__initDebugToolbarsLayout()

            EricMessageBox.information(
                self,
                self.tr("First time usage"),
                self.tr(
                    """eric has not been configured yet. """
                    """The configuration dialog will be started."""
                ),
            )
            self.showPreferences()
            Preferences.setConfigured()

    def checkProjectsWorkspace(self):
        """
        Public method to check, if a projects workspace has been configured. If
        it has not, a dialog is shown.
        """
        if not Preferences.isConfigured():
            # eric hasn't been configured at all
            self.checkConfigurationStatus()

        workspace = Preferences.getMultiProject("Workspace")
        if workspace == "":
            default = OSUtilities.getHomeDir()
            workspace = EricFileDialog.getExistingDirectory(
                None,
                self.tr("Select Workspace Directory"),
                default,
                EricFileDialog.Option(0),
            )
            Preferences.setMultiProject("Workspace", workspace)

    def versionIsNewer(self, required, snapshot=None):
        """
        Public method to check, if the eric version is good compared to
        the required version.

        @param required required version
        @type str
        @param snapshot required snapshot version
        @type str
        @return flag indicating, that the version is newer than the required one
        @rtype bool
        """
        if VersionOnly.startswith("@@"):
            # development version, always newer
            return True

        if VersionOnly.startswith("rev_"):
            # installed from cloned sources, always newer
            return True

        if "snapshot-" in VersionOnly:
            # check snapshot version
            if snapshot is None:
                return True
            else:
                vers = VersionOnly.split("snapshot-")[1]
                return vers > snapshot

        versionTuple = EricUtilities.versionToTuple(VersionOnly)
        if isinstance(required, str):
            required = EricUtilities.versionToTuple(required)
        try:
            res = versionTuple > required
        except TypeError:
            # some mismatching types, assume newer
            res = True
        return res

    #################################
    ## Below are some utility methods
    #################################

    def __getFloatingGeometry(self, w):
        """
        Private method to get the geometry of a floating windows.

        @param w reference to the widget to be saved
        @type QWidget
        @return list giving the widget's geometry and its visibility
        @rtype list of [int, int, int, int, bool]
        """
        s = w.size()
        p = w.pos()
        return [p.x(), p.y(), s.width(), s.height(), not w.isHidden()]

    def getOriginalPathString(self):
        """
        Public method to get the original PATH environment variable
        (i.e. before modifications by eric and PyQt5).

        @return original PATH environment variable
        @rtype str
        """
        return self.__originalPathString

    ############################
    ## some event handlers below
    ############################

    def showEvent(self, _evt):
        """
        Protected method to handle the show event.

        @param _evt reference to the show event (unused)
        @type QShowEvent
        """
        if self.__startup:
            if (
                Preferences.getGeometry("MainMaximized")
                and not DesktopUtilities.isWaylandSession()
            ):
                self.setWindowState(Qt.WindowState.WindowMaximized)
            self.__startup = False

    ##########################################
    ## Support for desktop notifications below
    ##########################################

    def showNotification(
        self, icon, heading, text, kind=NotificationTypes.INFORMATION, timeout=None
    ):
        """
        Public method to show a desktop notification.

        @param icon icon to be shown in the notification
        @type QPixmap
        @param heading heading of the notification
        @type str
        @param text text of the notification
        @type str
        @param kind kind of notification to be shown
        @type NotificationTypes
        @param timeout time in seconds the notification should be shown
            (None = use configured timeout, 0 = indefinitely)
        @type int
        """
        from .NotificationWidget import NotificationWidget

        if self.__notification is None:
            self.__notification = NotificationWidget(parent=self)
        if timeout is None:
            timeout = Preferences.getUI("NotificationTimeout")
        self.__notification.showNotification(
            icon, heading, text, kind=kind, timeout=timeout
        )

    #########################
    ## Support for IRC  below
    #########################

    def autoConnectIrc(self):
        """
        Public method to initiate the IRC auto connection.
        """
        if self.irc is not None:
            self.irc.autoConnect()

    def __ircAutoConnected(self):
        """
        Private slot handling the automatic connection of the IRC client.
        """
        self.__activateIRC()

    ##############################################
    ## Support for Code Documentation Viewer below
    ##############################################

    def documentationViewer(self):
        """
        Public method to provide a reference to the code documentation viewer.

        @return reference to the code documentation viewer
        @rtype CodeDocumentationViewer
        """
        return self.codeDocumentationViewer

    ###############################################
    ## Support for Desktop session management below
    ###############################################

    def __commitData(self, manager: QSessionManager):
        """
        Private slot to commit unsaved data when instructed by the desktop
        session manager.

        @param manager reference to the desktop session manager
        @type QSessionManager
        """
        if self.viewmanager.hasDirtyEditor():
            if manager.allowsInteraction():
                res = EricMessageBox.warning(
                    self,
                    self.tr("Unsaved Data Detected"),
                    self.tr("Some editors contain unsaved data. Shall these be saved?"),
                    EricMessageBox.Abort
                    | EricMessageBox.Discard
                    | EricMessageBox.Save
                    | EricMessageBox.SaveAll,
                    EricMessageBox.SaveAll,
                )
                if res == EricMessageBox.SaveAll:
                    manager.release()
                    self.viewmanager.saveAllEditors()
                elif res == EricMessageBox.Save:
                    manager.release()
                    ok = self.viewmanager.checkAllDirty()
                    if not ok:
                        manager.cancel()
                elif res == EricMessageBox.Discard:
                    # nothing to do
                    pass
                else:
                    # default action is to abort shutdown
                    manager.cancel()
            else:
                # We did not get permission to interact, play it safe and
                # save all data.
                self.viewmanager.saveAllEditors()

    ############################################################
    ## Interface to the virtual environment manager widget below
    ############################################################

    @pyqtSlot()
    def activateVirtualenvManager(self):
        """
        Public slot to activate the virtual environments manager widget.
        """
        if self.__layoutType == "Toolboxes":
            self.rToolboxDock.show()
            self.rToolbox.setCurrentWidget(self.__virtualenvManagerWidget)
        elif self.__layoutType == "Sidebars":
            self.activateLeftRightSidebarWidget(self.__virtualenvManagerWidget)
        self.__virtualenvManagerWidget.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    ############################################################
    ## Interface to the eric-ide server interface
    ############################################################

    def isEricServerConnected(self):
        """
        Public method to check, if a connection to an eric-ide server has been
        established.

        @return flag indicating the interface connection state
        @rtype bool
        """
        # simply delegated to the eric-ide server interface object
        return self.__ericServerInterface.isServerConnected()
