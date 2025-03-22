# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the web browser main window.
"""

import contextlib
import functools
import importlib
import os
import pathlib
import shutil

from PyQt6.QtCore import (
    QByteArray,
    QEvent,
    QProcess,
    QSize,
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QAction,
    QDesktopServices,
    QFont,
    QFontMetrics,
    QKeySequence,
    QPixmap,
)
from PyQt6.QtWebEngineCore import (
    QWebEnginePage,
    QWebEngineProfile,
    QWebEngineScript,
    QWebEngineSettings,
)
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDockWidget,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWhatsThis,
    QWidget,
)

try:
    from PyQt6.QtHelp import QHelpEngine

    QTHELP_AVAILABLE = True
except ImportError:
    QTHELP_AVAILABLE = False

from eric7 import EricUtilities, Preferences, Utilities
from eric7.__version__ import Version
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricNetwork.EricNetworkIcon import EricNetworkIcon
from eric7.EricNetwork.EricSslUtilities import initSSL
from eric7.EricWidgets import EricErrorMessage, EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.EricWidgets.EricZoomWidget import EricZoomWidget
from eric7.Globals import getConfig
from eric7.Preferences import Shortcuts
from eric7.Preferences.ShortcutsDialog import ShortcutsDialog
from eric7.QtHelpInterface.HelpIndexWidget import HelpIndexWidget
from eric7.QtHelpInterface.HelpSearchWidget import HelpSearchWidget
from eric7.QtHelpInterface.HelpTocWidget import HelpTocWidget
from eric7.SystemUtilities import (
    FileSystemUtilities,
    OSUtilities,
    PythonUtilities,
    QtUtilities,
)
from eric7.UI.NotificationWidget import NotificationTypes
from eric7.WebBrowser.Tools import WebIconProvider
from eric7.WebBrowser.ZoomManager import ZoomManager

from .Tools import Scripts, WebBrowserTools
from .WebBrowserSingleApplication import WebBrowserSingleApplicationServer


class WebBrowserWindow(EricMainWindow):
    """
    Class implementing the web browser main window.

    @signal webBrowserWindowOpened(window) emitted after a new web browser
        window was opened
    @signal webBrowserWindowClosed(window) emitted after the window was
        requested to close
    @signal webBrowserOpened(browser) emitted after a new web browser tab was
        created
    @signal webBrowserClosed(browser) emitted after a web browser tab was
        closed
    """

    webBrowserWindowClosed = pyqtSignal(EricMainWindow)
    webBrowserWindowOpened = pyqtSignal(EricMainWindow)
    webBrowserOpened = pyqtSignal(QWidget)
    webBrowserClosed = pyqtSignal(QWidget)

    BrowserWindows = []

    _useQtHelp = QTHELP_AVAILABLE
    _isPrivate = False

    _webProfile = None
    _networkManager = None
    _cookieJar = None
    _helpEngine = None
    _bookmarksManager = None
    _historyManager = None
    _passwordManager = None
    _adblockManager = None
    _downloadManager = None
    _feedsManager = None
    _userAgentsManager = None
    _syncManager = None
    _speedDial = None
    _personalInformationManager = None
    _greaseMonkeyManager = None
    _notification = None
    _featurePermissionManager = None
    _imageSearchEngine = None
    _autoScroller = None
    _tabManager = None
    _sessionManager = None
    _safeBrowsingManager = None
    _protocolHandlerManager = None

    _performingStartup = True
    _performingShutdown = False
    _lastActiveWindow = None

    def __init__(
        self,
        home,
        path,
        parent,
        name,
        searchWord=None,
        private=False,
        qthelp=False,
        settingsDir="",
        restoreSession=False,
        single=False,
        saname="",
    ):
        """
        Constructor

        @param home the URL to be shown
        @type str
        @param path the path of the working dir (usually '.')
        @type str
        @param parent parent widget of this window
        @type QWidget
        @param name name of this window
        @type str
        @param searchWord word to search for
        @type str
        @param private flag indicating a private browsing window
        @type bool
        @param qthelp flag indicating to enable the QtHelp support
        @type bool
        @param settingsDir directory to be used for the settings files
        @type str
        @param restoreSession flag indicating a restore session action
        @type bool
        @param single flag indicating to start in single application mode
        @type bool
        @param saname name to be used for the single application server
        @type str
        """
        from .AdBlock.AdBlockIcon import AdBlockIcon
        from .Bookmarks.BookmarksToolBar import BookmarksToolBar
        from .Navigation.NavigationBar import NavigationBar
        from .Navigation.NavigationContainer import NavigationContainer
        from .SearchWidget import SearchWidget
        from .StatusBar.ImagesIcon import ImagesIcon
        from .StatusBar.JavaScriptIcon import JavaScriptIcon
        from .VirusTotal.VirusTotalApi import VirusTotalAPI
        from .WebBrowserJavaScriptConsole import WebBrowserJavaScriptConsole
        from .WebBrowserTabWidget import WebBrowserTabWidget
        from .WebBrowserView import WebBrowserView

        self.__hideNavigationTimer = None

        super().__init__(parent)
        self.setObjectName(name)
        if private:
            self.setWindowTitle(self.tr("eric Web Browser (Private Mode)"))
        else:
            self.setWindowTitle(self.tr("eric Web Browser"))

        self.__settingsDir = settingsDir
        self.setWindowIcon(EricPixmapCache.getIcon("ericWeb"))

        self.__mHistory = []
        self.__lastConfigurationPageName = ""

        WebBrowserWindow._isPrivate = private

        self.__shortcutsDialog = None

        WebBrowserWindow.setUseQtHelp(qthelp or bool(searchWord))

        self.webProfile(private)
        self.networkManager()

        self.__htmlFullScreen = False
        self.__windowStates = Qt.WindowState.WindowNoState
        self.__isClosing = False

        self.setStyle(
            styleName=Preferences.getUI("Style"),
            styleSheetFile=Preferences.getUI("StyleSheet"),
            itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
        )

        # initialize some SSL stuff
        initSSL()

        if WebBrowserWindow._useQtHelp:
            self.__helpEngine = QHelpEngine(
                WebBrowserWindow.getQtHelpCollectionFileName(), self
            )
            self.__helpEngine.setReadOnly(False)
            self.__helpEngine.setupData()
            self.__helpEngine.setUsesFilterEngine(True)
            self.__removeOldDocumentation()
            self.__helpEngine.warning.connect(self.__warning)
        else:
            self.__helpEngine = None
        self.__helpInstaller = None

        self.__zoomWidget = EricZoomWidget(
            EricPixmapCache.getPixmap("zoomOut"),
            EricPixmapCache.getPixmap("zoomIn"),
            EricPixmapCache.getPixmap("zoomReset"),
            self,
        )
        self.statusBar().addPermanentWidget(self.__zoomWidget)
        self.__zoomWidget.setMapping(
            WebBrowserView.ZoomLevels, WebBrowserView.ZoomLevelDefault
        )
        self.__zoomWidget.valueChanged.connect(self.__zoomValueChanged)

        self.__tabWidget = WebBrowserTabWidget(self)
        self.__tabWidget.currentChanged[int].connect(self.__currentChanged)
        self.__tabWidget.titleChanged.connect(self.__titleChanged)
        self.__tabWidget.showMessage.connect(self.statusBar().showMessage)
        self.__tabWidget.browserZoomValueChanged.connect(self.__zoomWidget.setValue)
        self.__tabWidget.browserClosed.connect(self.webBrowserClosed)
        self.__tabWidget.browserOpened.connect(self.webBrowserOpened)

        self.__searchWidget = SearchWidget(self, self)

        self.setIconDatabasePath()

        bookmarksModel = self.bookmarksManager().bookmarksModel()
        self.__bookmarksToolBar = BookmarksToolBar(self, bookmarksModel, self)
        self.__bookmarksToolBar.openUrl.connect(self.openUrl)
        self.__bookmarksToolBar.newTab.connect(self.openUrlNewTab)
        self.__bookmarksToolBar.newWindow.connect(self.openUrlNewWindow)

        self.__navigationBar = NavigationBar(self)

        self.__navigationContainer = NavigationContainer(self)
        self.__navigationContainer.addWidget(self.__navigationBar)
        self.__navigationContainer.addWidget(self.__bookmarksToolBar)

        centralWidget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        layout.addWidget(self.__navigationContainer)
        layout.addWidget(self.__tabWidget)
        layout.addWidget(self.__searchWidget)
        self.__tabWidget.setSizePolicy(
            QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
        )
        centralWidget.setLayout(layout)
        self.setCentralWidget(centralWidget)
        self.__searchWidget.hide()

        if WebBrowserWindow._useQtHelp:
            # setup the TOC widget
            self.__tocWindow = HelpTocWidget(self.__helpEngine)
            self.__tocDock = QDockWidget(self.tr("Contents"), self)
            self.__tocDock.setObjectName("TocWindow")
            self.__tocDock.setWidget(self.__tocWindow)
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.__tocDock)

            # setup the index widget
            self.__indexWindow = HelpIndexWidget(self.__helpEngine)
            self.__indexDock = QDockWidget(self.tr("Index"), self)
            self.__indexDock.setObjectName("IndexWindow")
            self.__indexDock.setWidget(self.__indexWindow)
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.__indexDock)

            # setup the search widget
            self.__indexing = False
            self.__indexingProgress = None
            self.__searchEngine = self.__helpEngine.searchEngine()
            self.__searchEngine.indexingStarted.connect(self.__indexingStarted)
            self.__searchEngine.indexingFinished.connect(self.__indexingFinished)
            self.__searchWindow = HelpSearchWidget(self.__searchEngine)
            self.__searchDock = QDockWidget(self.tr("Search"), self)
            self.__searchDock.setObjectName("SearchWindow")
            self.__searchDock.setWidget(self.__searchWindow)
            self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.__searchDock)

        # JavaScript Console window
        self.__javascriptConsole = WebBrowserJavaScriptConsole(self)
        self.__javascriptConsoleDock = QDockWidget(self.tr("JavaScript Console"))
        self.__javascriptConsoleDock.setObjectName("JavascriptConsole")
        self.__javascriptConsoleDock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea
        )
        self.__javascriptConsoleDock.setWidget(self.__javascriptConsole)
        self.addDockWidget(
            Qt.DockWidgetArea.BottomDockWidgetArea, self.__javascriptConsoleDock
        )

        g = (
            Preferences.getGeometry("WebBrowserGeometry")
            if Preferences.getWebBrowser("SaveGeometry")
            else QByteArray()
        )
        if g.isEmpty():
            s = QSize(800, 800)
            self.resize(s)
        else:
            self.restoreGeometry(g)

        WebBrowserWindow.BrowserWindows.append(self)

        self.__initWebEngineSettings()

        # initialize some of our class objects
        self.passwordManager()
        self.historyManager()
        self.greaseMonkeyManager()
        self.protocolHandlerManager()

        # initialize the actions
        self.__initActions()

        # initialize the menus
        self.__initMenus()
        self.__initSuperMenu()
        if Preferences.getWebBrowser("MenuBarVisible"):
            self.__navigationBar.superMenuButton().hide()
        else:
            self.menuBar().hide()

        # save references to toolbars in order to hide them
        # when going full screen
        self.__toolbars = {}
        # initialize toolbars
        if Preferences.getWebBrowser("ShowToolbars"):
            self.__initToolbars()
        self.__bookmarksToolBar.setVisible(
            Preferences.getWebBrowser("BookmarksToolBarVisible")
        )

        syncMgr = self.syncManager()
        syncMgr.syncMessage.connect(self.statusBar().showMessage)
        syncMgr.syncError.connect(self.statusBar().showMessage)

        restoreSessionData = {}
        if (
            WebBrowserWindow._performingStartup
            and not home
            and not WebBrowserWindow.isPrivate()
        ):
            startupBehavior = Preferences.getWebBrowser("StartupBehavior")
            if not private and startupBehavior in [3, 4]:
                if startupBehavior == 3:
                    # restore last session
                    restoreSessionFile = self.sessionManager().lastActiveSessionFile()
                elif startupBehavior == 4:
                    # select session
                    restoreSessionFile = self.sessionManager().selectSession()
                sessionData = self.sessionManager().readSessionFromFile(
                    restoreSessionFile
                )
                if self.sessionManager().isValidSession(sessionData):
                    restoreSessionData = sessionData
                    restoreSession = True
            else:
                if Preferences.getWebBrowser("StartupBehavior") == 0:
                    home = "about:blank"
                elif Preferences.getWebBrowser("StartupBehavior") == 1:
                    home = Preferences.getWebBrowser("HomePage")
                elif Preferences.getWebBrowser("StartupBehavior") == 2:
                    home = "eric:speeddial"

        if not restoreSession:
            self.__tabWidget.newBrowser(QUrl.fromUserInput(home))
            self.__tabWidget.currentBrowser().setFocus()
        WebBrowserWindow._performingStartup = False

        self.__imagesIcon = ImagesIcon(self)
        self.statusBar().addPermanentWidget(self.__imagesIcon)
        self.__javaScriptIcon = JavaScriptIcon(self)
        self.statusBar().addPermanentWidget(self.__javaScriptIcon)

        self.__adBlockIcon = AdBlockIcon(self)
        self.statusBar().addPermanentWidget(self.__adBlockIcon)
        self.__adBlockIcon.setEnabled(Preferences.getWebBrowser("AdBlockEnabled"))
        self.__tabWidget.currentChanged[int].connect(self.__adBlockIcon.currentChanged)
        self.__tabWidget.sourceChanged.connect(self.__adBlockIcon.sourceChanged)

        self.__tabManagerIcon = self.tabManager().createStatusBarIcon()
        self.statusBar().addPermanentWidget(self.__tabManagerIcon)

        self.networkIcon = EricNetworkIcon(
            dynamicOnlineCheck=Preferences.getUI("DynamicOnlineCheck"), parent=self
        )
        self.statusBar().addPermanentWidget(self.networkIcon)

        if not Preferences.getWebBrowser("StatusBarVisible"):
            self.statusBar().hide()

        if len(WebBrowserWindow.BrowserWindows):
            QDesktopServices.setUrlHandler(
                "http", WebBrowserWindow.BrowserWindows[0].urlHandler
            )
            QDesktopServices.setUrlHandler(
                "https", WebBrowserWindow.BrowserWindows[0].urlHandler
            )

        # setup connections
        self.__activating = False
        if WebBrowserWindow._useQtHelp:
            # TOC window
            self.__tocWindow.escapePressed.connect(self.__activateCurrentBrowser)
            self.__tocWindow.openUrl.connect(self.openUrl)
            self.__tocWindow.newTab.connect(self.openUrlNewTab)
            self.__tocWindow.newBackgroundTab.connect(self.openUrlNewBackgroundTab)
            self.__tocWindow.newWindow.connect(self.openUrlNewWindow)

            # index window
            self.__indexWindow.escapePressed.connect(self.__activateCurrentBrowser)
            self.__indexWindow.openUrl.connect(self.openUrl)
            self.__indexWindow.newTab.connect(self.openUrlNewTab)
            self.__indexWindow.newBackgroundTab.connect(self.openUrlNewBackgroundTab)
            self.__indexWindow.newWindow.connect(self.openUrlNewWindow)

            # search window
            self.__searchWindow.escapePressed.connect(self.__activateCurrentBrowser)
            self.__searchWindow.openUrl.connect(self.openUrl)
            self.__searchWindow.newTab.connect(self.openUrlNewTab)
            self.__searchWindow.newBackgroundTab.connect(self.openUrlNewBackgroundTab)
            self.__searchWindow.newWindow.connect(self.openUrlNewWindow)

        state = Preferences.getWebBrowser("WebBrowserState")
        self.restoreState(state)

        self.__virusTotal = VirusTotalAPI(self)
        self.__virusTotal.submitUrlError.connect(self.__virusTotalSubmitUrlError)
        self.__virusTotal.urlScanReport.connect(self.__virusTotalUrlScanReport)
        self.__virusTotal.fileScanReport.connect(self.__virusTotalFileScanReport)

        ericApp().focusChanged.connect(self.__appFocusChanged)

        self.__toolbarStates = self.saveState()

        if single:
            self.SAServer = WebBrowserSingleApplicationServer(saname)
            self.SAServer.loadUrl.connect(self.__saLoadUrl)
            self.SAServer.newTab.connect(self.__saNewTab)
            self.SAServer.search.connect(self.__saSearchWord)
            self.SAServer.shutdown.connect(self.shutdown)
        else:
            self.SAServer = None

        self.__hideNavigationTimer = QTimer(self)
        self.__hideNavigationTimer.setInterval(1000)
        self.__hideNavigationTimer.setSingleShot(True)
        self.__hideNavigationTimer.timeout.connect(self.__hideNavigation)

        self.__forcedClose = False

        if restoreSessionData and not WebBrowserWindow.isPrivate():
            self.sessionManager().restoreSessionFromData(self, restoreSessionData)

        if not WebBrowserWindow.isPrivate():
            self.sessionManager().activateTimer()

        QTimer.singleShot(0, syncMgr.loadSettings)

        if WebBrowserWindow._useQtHelp:
            if Preferences.getHelp("QtHelpSearchNewOnStart"):
                QTimer.singleShot(50, self.__lookForNewDocumentation)
            if searchWord:
                QTimer.singleShot(0, lambda: self.__searchForWord(searchWord))

    def __del__(self):
        """
        Special method called during object destruction.

        Note: This empty variant seems to get rid of the Qt message
        'Warning: QBasicTimer::start: QBasicTimer can only be used with
        threads started with QThread'
        """
        pass

    def tabWidget(self):
        """
        Public method to get a reference to the tab widget.

        @return reference to the tab widget
        @rtype WebBrowserTabWidget
        """
        return self.__tabWidget

    @classmethod
    def setIconDatabasePath(cls, enable=True):
        """
        Class method to set the favicons path.

        @param enable flag indicating to enabled icon storage
        @type bool
        """
        if enable:
            iconDatabasePath = os.path.join(
                EricUtilities.getConfigDir(), "web_browser", "favicons"
            )
            if not os.path.exists(iconDatabasePath):
                os.makedirs(iconDatabasePath)
        else:
            iconDatabasePath = ""  # setting an empty path disables it

        WebIconProvider.instance().setIconDatabasePath(iconDatabasePath)

    def __initWebEngineSettings(self):
        """
        Private method to set the global web settings.
        """
        settings = self.webSettings()

        settings.setFontFamily(
            QWebEngineSettings.FontFamily.StandardFont,
            Preferences.getWebBrowser("StandardFontFamily"),
        )
        settings.setFontFamily(
            QWebEngineSettings.FontFamily.FixedFont,
            Preferences.getWebBrowser("FixedFontFamily"),
        )
        settings.setFontFamily(
            QWebEngineSettings.FontFamily.SerifFont,
            Preferences.getWebBrowser("SerifFontFamily"),
        )
        settings.setFontFamily(
            QWebEngineSettings.FontFamily.SansSerifFont,
            Preferences.getWebBrowser("SansSerifFontFamily"),
        )
        settings.setFontFamily(
            QWebEngineSettings.FontFamily.CursiveFont,
            Preferences.getWebBrowser("CursiveFontFamily"),
        )
        settings.setFontFamily(
            QWebEngineSettings.FontFamily.FantasyFont,
            Preferences.getWebBrowser("FantasyFontFamily"),
        )

        settings.setFontSize(
            QWebEngineSettings.FontSize.DefaultFontSize,
            Preferences.getWebBrowser("DefaultFontSize"),
        )
        settings.setFontSize(
            QWebEngineSettings.FontSize.DefaultFixedFontSize,
            Preferences.getWebBrowser("DefaultFixedFontSize"),
        )
        settings.setFontSize(
            QWebEngineSettings.FontSize.MinimumFontSize,
            Preferences.getWebBrowser("MinimumFontSize"),
        )
        settings.setFontSize(
            QWebEngineSettings.FontSize.MinimumLogicalFontSize,
            Preferences.getWebBrowser("MinimumLogicalFontSize"),
        )

        styleSheet = Preferences.getWebBrowser("UserStyleSheet")
        self.__setUserStyleSheet(styleSheet)

        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AutoLoadImages,
            Preferences.getWebBrowser("AutoLoadImages"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled,
            Preferences.getWebBrowser("JavaScriptEnabled"),
        )
        # JavaScript is needed for the web browser functionality
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows,
            Preferences.getWebBrowser("JavaScriptCanOpenWindows"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard,
            Preferences.getWebBrowser("JavaScriptCanAccessClipboard"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PluginsEnabled,
            Preferences.getWebBrowser("PluginsEnabled"),
        )

        if self.isPrivate():
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.LocalStorageEnabled, False
            )
        else:
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.LocalStorageEnabled,
                Preferences.getWebBrowser("LocalStorageEnabled"),
            )
        settings.setDefaultTextEncoding(
            Preferences.getWebBrowser("DefaultTextEncoding")
        )

        settings.setAttribute(
            QWebEngineSettings.WebAttribute.SpatialNavigationEnabled,
            Preferences.getWebBrowser("SpatialNavigationEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LinksIncludedInFocusChain,
            Preferences.getWebBrowser("LinksIncludedInFocusChain"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls,
            Preferences.getWebBrowser("LocalContentCanAccessRemoteUrls"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls,
            Preferences.getWebBrowser("LocalContentCanAccessFileUrls"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.XSSAuditingEnabled,
            Preferences.getWebBrowser("XSSAuditingEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled,
            Preferences.getWebBrowser("ScrollAnimatorEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ErrorPageEnabled,
            Preferences.getWebBrowser("ErrorPageEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.FullScreenSupportEnabled,
            Preferences.getWebBrowser("FullScreenSupportEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ScreenCaptureEnabled,
            Preferences.getWebBrowser("ScreenCaptureEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.WebGLEnabled,
            Preferences.getWebBrowser("WebGLEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled,
            Preferences.getWebBrowser("FocusOnNavigationEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PrintElementBackgrounds,
            Preferences.getWebBrowser("PrintElementBackgrounds"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowRunningInsecureContent,
            Preferences.getWebBrowser("AllowRunningInsecureContent"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowGeolocationOnInsecureOrigins,
            Preferences.getWebBrowser("AllowGeolocationOnInsecureOrigins"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.AllowWindowActivationFromJavaScript,
            Preferences.getWebBrowser("AllowWindowActivationFromJavaScript"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.ShowScrollBars,
            Preferences.getWebBrowser("ShowScrollBars"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture,
            Preferences.getWebBrowser("PlaybackRequiresUserGesture"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.JavascriptCanPaste,
            Preferences.getWebBrowser("JavaScriptCanPaste"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.WebRTCPublicInterfacesOnly,
            Preferences.getWebBrowser("WebRTCPublicInterfacesOnly"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.DnsPrefetchEnabled,
            Preferences.getWebBrowser("DnsPrefetchEnabled"),
        )
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.PdfViewerEnabled,
            Preferences.getWebBrowser("PdfViewerEnabled"),
        )
        if QtUtilities.qVersionTuple() >= (6, 4, 0):
            # Qt 6.4+
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.NavigateOnDropEnabled,
                Preferences.getWebBrowser("NavigateOnDropEnabled"),
            )
        if QtUtilities.qVersionTuple() >= (6, 6, 0):
            # Qt 6.6+
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.ReadingFromCanvasEnabled,
                Preferences.getWebBrowser("ReadingFromCanvasEnabled"),
            )
        if QtUtilities.qVersionTuple() >= (6, 7, 0):
            # Qt 6.7+
            settings.setAttribute(
                QWebEngineSettings.WebAttribute.ForceDarkMode,
                Preferences.getWebBrowser("ForceDarkMode"),
            )

    def __initActions(self):
        """
        Private method to define the user interface actions.
        """
        # list of all actions
        self.__actions = []

        self.newTabAct = EricAction(
            self.tr("New Tab"),
            EricPixmapCache.getIcon("tabNew"),
            self.tr("&New Tab"),
            QKeySequence(self.tr("Ctrl+T", "File|New Tab")),
            0,
            self,
            "webbrowser_file_new_tab",
        )
        self.newTabAct.setStatusTip(self.tr("Open a new web browser tab"))
        self.newTabAct.setWhatsThis(
            self.tr("""<b>New Tab</b><p>This opens a new web browser tab.</p>""")
        )
        self.newTabAct.triggered.connect(self.newTab)
        self.__actions.append(self.newTabAct)

        self.newAct = EricAction(
            self.tr("New Window"),
            EricPixmapCache.getIcon("newWindow"),
            self.tr("New &Window"),
            QKeySequence(self.tr("Ctrl+N", "File|New Window")),
            0,
            self,
            "webbrowser_file_new_window",
        )
        self.newAct.setStatusTip(self.tr("Open a new web browser window"))
        self.newAct.setWhatsThis(
            self.tr(
                """<b>New Window</b>"""
                """<p>This opens a new web browser window in the current"""
                """ privacy mode.</p>"""
            )
        )
        self.newAct.triggered.connect(self.newWindow)
        self.__actions.append(self.newAct)

        self.newPrivateAct = EricAction(
            self.tr("New Private Window"),
            EricPixmapCache.getIcon("privateMode"),
            self.tr("New &Private Window"),
            QKeySequence(self.tr("Ctrl+Shift+P", "File|New Private Window")),
            0,
            self,
            "webbrowser_file_new_private_window",
        )
        self.newPrivateAct.setStatusTip(
            self.tr("Open a new private web browser window")
        )
        self.newPrivateAct.setWhatsThis(
            self.tr(
                """<b>New Private Window</b>"""
                """<p>This opens a new private web browser window by starting"""
                """ a new web browser instance in private mode.</p>"""
            )
        )
        self.newPrivateAct.triggered.connect(self.newPrivateWindow)
        self.__actions.append(self.newPrivateAct)

        self.openAct = EricAction(
            self.tr("Open File"),
            EricPixmapCache.getIcon("open"),
            self.tr("&Open File"),
            QKeySequence(self.tr("Ctrl+O", "File|Open")),
            0,
            self,
            "webbrowser_file_open",
        )
        self.openAct.setStatusTip(self.tr("Open a file for display"))
        self.openAct.setWhatsThis(
            self.tr(
                """<b>Open File</b>"""
                """<p>This opens a new file for display."""
                """ It pops up a file selection dialog.</p>"""
            )
        )
        self.openAct.triggered.connect(self.__openFile)
        self.__actions.append(self.openAct)

        self.openTabAct = EricAction(
            self.tr("Open File in New Tab"),
            EricPixmapCache.getIcon("openNewTab"),
            self.tr("Open File in New &Tab"),
            QKeySequence(self.tr("Shift+Ctrl+O", "File|Open in new tab")),
            0,
            self,
            "webbrowser_file_open_tab",
        )
        self.openTabAct.setStatusTip(self.tr("Open a file for display in a new tab"))
        self.openTabAct.setWhatsThis(
            self.tr(
                """<b>Open File in New Tab</b>"""
                """<p>This opens a new file for display in a new tab."""
                """ It pops up a file selection dialog.</p>"""
            )
        )
        self.openTabAct.triggered.connect(self.__openFileNewTab)
        self.__actions.append(self.openTabAct)

        if hasattr(QWebEnginePage, "SavePage"):
            self.saveAsAct = EricAction(
                self.tr("Save As"),
                EricPixmapCache.getIcon("fileSaveAs"),
                self.tr("&Save As..."),
                QKeySequence(self.tr("Shift+Ctrl+S", "File|Save As")),
                0,
                self,
                "webbrowser_file_save_as",
            )
            self.saveAsAct.setStatusTip(self.tr("Save the current page to disk"))
            self.saveAsAct.setWhatsThis(
                self.tr("""<b>Save As...</b><p>Saves the current page to disk.</p>""")
            )
            self.saveAsAct.triggered.connect(self.__savePageAs)
            self.__actions.append(self.saveAsAct)
        else:
            self.saveAsAct = None

        self.saveVisiblePageScreenAct = EricAction(
            self.tr("Save Page Screen"),
            EricPixmapCache.getIcon("fileSavePixmap"),
            self.tr("Save Page Screen..."),
            0,
            0,
            self,
            "webbrowser_file_save_visible_page_screen",
        )
        self.saveVisiblePageScreenAct.setStatusTip(
            self.tr("Save the visible part of the current page as a screen shot")
        )
        self.saveVisiblePageScreenAct.setWhatsThis(
            self.tr(
                """<b>Save Page Screen...</b>"""
                """<p>Saves the visible part of the current page as a"""
                """ screen shot.</p>"""
            )
        )
        self.saveVisiblePageScreenAct.triggered.connect(self.__saveVisiblePageScreen)
        self.__actions.append(self.saveVisiblePageScreenAct)

        bookmarksManager = self.bookmarksManager()
        self.importBookmarksAct = EricAction(
            self.tr("Import Bookmarks"),
            self.tr("&Import Bookmarks..."),
            0,
            0,
            self,
            "webbrowser_file_import_bookmarks",
        )
        self.importBookmarksAct.setStatusTip(
            self.tr("Import bookmarks from other browsers")
        )
        self.importBookmarksAct.setWhatsThis(
            self.tr(
                """<b>Import Bookmarks</b>"""
                """<p>Import bookmarks from other browsers.</p>"""
            )
        )
        self.importBookmarksAct.triggered.connect(bookmarksManager.importBookmarks)
        self.__actions.append(self.importBookmarksAct)

        self.exportBookmarksAct = EricAction(
            self.tr("Export Bookmarks"),
            self.tr("&Export Bookmarks..."),
            0,
            0,
            self,
            "webbrowser_file_export_bookmarks",
        )
        self.exportBookmarksAct.setStatusTip(
            self.tr("Export the bookmarks into a file")
        )
        self.exportBookmarksAct.setWhatsThis(
            self.tr(
                """<b>Export Bookmarks</b>"""
                """<p>Export the bookmarks into a file.</p>"""
            )
        )
        self.exportBookmarksAct.triggered.connect(bookmarksManager.exportBookmarks)
        self.__actions.append(self.exportBookmarksAct)

        self.printAct = EricAction(
            self.tr("Print"),
            EricPixmapCache.getIcon("print"),
            self.tr("&Print"),
            QKeySequence(self.tr("Ctrl+P", "File|Print")),
            0,
            self,
            "webbrowser_file_print",
        )
        self.printAct.setStatusTip(self.tr("Print the displayed help"))
        self.printAct.setWhatsThis(
            self.tr("""<b>Print</b><p>Print the displayed help text.</p>""")
        )
        self.printAct.triggered.connect(self.__tabWidget.printBrowser)
        self.__actions.append(self.printAct)

        self.printPdfAct = EricAction(
            self.tr("Print as PDF"),
            EricPixmapCache.getIcon("printPdf"),
            self.tr("Print as PDF"),
            0,
            0,
            self,
            "webbrowser_file_print_pdf",
        )
        self.printPdfAct.setStatusTip(self.tr("Print the displayed help as PDF"))
        self.printPdfAct.setWhatsThis(
            self.tr(
                """<b>Print as PDF</b>"""
                """<p>Print the displayed help text as a PDF file.</p>"""
            )
        )
        self.printPdfAct.triggered.connect(self.__tabWidget.printBrowserPdf)
        self.__actions.append(self.printPdfAct)

        self.printPreviewAct = EricAction(
            self.tr("Print Preview"),
            EricPixmapCache.getIcon("printPreview"),
            self.tr("Print Preview"),
            0,
            0,
            self,
            "webbrowser_file_print_preview",
        )
        self.printPreviewAct.setStatusTip(
            self.tr("Print preview of the displayed help")
        )
        self.printPreviewAct.setWhatsThis(
            self.tr(
                """<b>Print Preview</b>"""
                """<p>Print preview of the displayed help text.</p>"""
            )
        )
        self.printPreviewAct.triggered.connect(self.__tabWidget.printPreviewBrowser)
        self.__actions.append(self.printPreviewAct)

        self.sendPageLinkAct = EricAction(
            self.tr("Send Page Link"),
            EricPixmapCache.getIcon("mailSend"),
            self.tr("Send Page Link"),
            0,
            0,
            self,
            "webbrowser_send_page_link",
        )
        self.sendPageLinkAct.setStatusTip(
            self.tr("Send the link of the current page via email")
        )
        self.sendPageLinkAct.setWhatsThis(
            self.tr(
                """<b>Send Page Link</b>"""
                """<p>Send the link of the current page via email.</p>"""
            )
        )
        self.sendPageLinkAct.triggered.connect(self.__sendPageLink)
        self.__actions.append(self.sendPageLinkAct)

        self.closeAct = EricAction(
            self.tr("Close"),
            EricPixmapCache.getIcon("close"),
            self.tr("&Close"),
            QKeySequence(self.tr("Ctrl+W", "File|Close")),
            0,
            self,
            "webbrowser_file_close",
        )
        self.closeAct.setStatusTip(self.tr("Close the current help window"))
        self.closeAct.setWhatsThis(
            self.tr("""<b>Close</b><p>Closes the current web browser window.</p>""")
        )
        self.closeAct.triggered.connect(self.__tabWidget.closeBrowser)
        self.__actions.append(self.closeAct)

        self.closeAllAct = EricAction(
            self.tr("Close All"),
            self.tr("Close &All"),
            0,
            0,
            self,
            "webbrowser_file_close_all",
        )
        self.closeAllAct.setStatusTip(self.tr("Close all help windows"))
        self.closeAllAct.setWhatsThis(
            self.tr(
                """<b>Close All</b>"""
                """<p>Closes all web browser windows except the first one.</p>"""
            )
        )
        self.closeAllAct.triggered.connect(self.__tabWidget.closeAllBrowsers)
        self.__actions.append(self.closeAllAct)

        self.exitAct = EricAction(
            self.tr("Quit"),
            EricPixmapCache.getIcon("exit"),
            self.tr("&Quit"),
            QKeySequence(self.tr("Ctrl+Q", "File|Quit")),
            0,
            self,
            "webbrowser_file_quit",
        )
        self.exitAct.setStatusTip(self.tr("Quit the eric Web Browser"))
        self.exitAct.setWhatsThis(
            self.tr("""<b>Quit</b><p>Quit the eric Web Browser.</p>""")
        )
        self.exitAct.triggered.connect(self.shutdown)
        self.__actions.append(self.exitAct)

        self.backAct = EricAction(
            self.tr("Backward"),
            EricPixmapCache.getIcon("back"),
            self.tr("&Backward"),
            QKeySequence(self.tr("Alt+Left", "Go|Backward")),
            0,
            self,
            "webbrowser_go_backward",
        )
        self.backAct.setStatusTip(self.tr("Move one screen backward"))
        self.backAct.setWhatsThis(
            self.tr(
                """<b>Backward</b>"""
                """<p>Moves one screen backward. If none is"""
                """ available, this action is disabled.</p>"""
            )
        )
        self.backAct.triggered.connect(self.__backward)
        self.__actions.append(self.backAct)

        self.forwardAct = EricAction(
            self.tr("Forward"),
            EricPixmapCache.getIcon("forward"),
            self.tr("&Forward"),
            QKeySequence(self.tr("Alt+Right", "Go|Forward")),
            0,
            self,
            "webbrowser_go_foreward",
        )
        self.forwardAct.setStatusTip(self.tr("Move one screen forward"))
        self.forwardAct.setWhatsThis(
            self.tr(
                """<b>Forward</b>"""
                """<p>Moves one screen forward. If none is"""
                """ available, this action is disabled.</p>"""
            )
        )
        self.forwardAct.triggered.connect(self.__forward)
        self.__actions.append(self.forwardAct)

        self.homeAct = EricAction(
            self.tr("Home"),
            EricPixmapCache.getIcon("home"),
            self.tr("&Home"),
            QKeySequence(self.tr("Ctrl+Home", "Go|Home")),
            0,
            self,
            "webbrowser_go_home",
        )
        self.homeAct.setStatusTip(self.tr("Move to the initial screen"))
        self.homeAct.setWhatsThis(
            self.tr("""<b>Home</b><p>Moves to the initial screen.</p>""")
        )
        self.homeAct.triggered.connect(self.__home)
        self.__actions.append(self.homeAct)

        self.reloadAct = EricAction(
            self.tr("Reload"),
            EricPixmapCache.getIcon("reload"),
            self.tr("&Reload"),
            QKeySequence(self.tr("Ctrl+R", "Go|Reload")),
            QKeySequence(self.tr("F5", "Go|Reload")),
            self,
            "webbrowser_go_reload",
        )
        self.reloadAct.setStatusTip(self.tr("Reload the current screen"))
        self.reloadAct.setWhatsThis(
            self.tr("""<b>Reload</b><p>Reloads the current screen.</p>""")
        )
        self.reloadAct.triggered.connect(self.__reload)
        self.__actions.append(self.reloadAct)

        self.stopAct = EricAction(
            self.tr("Stop"),
            EricPixmapCache.getIcon("stopLoading"),
            self.tr("&Stop"),
            QKeySequence(self.tr("Ctrl+.", "Go|Stop")),
            QKeySequence(self.tr("Esc", "Go|Stop")),
            self,
            "webbrowser_go_stop",
        )
        self.stopAct.setStatusTip(self.tr("Stop loading"))
        self.stopAct.setWhatsThis(
            self.tr("""<b>Stop</b><p>Stops loading of the current tab.</p>""")
        )
        self.stopAct.triggered.connect(self.__stopLoading)
        self.__actions.append(self.stopAct)

        self.copyAct = EricAction(
            self.tr("Copy"),
            EricPixmapCache.getIcon("editCopy"),
            self.tr("&Copy"),
            QKeySequence(self.tr("Ctrl+C", "Edit|Copy")),
            0,
            self,
            "webbrowser_edit_copy",
        )
        self.copyAct.setStatusTip(self.tr("Copy the selected text"))
        self.copyAct.setWhatsThis(
            self.tr("""<b>Copy</b><p>Copy the selected text to the clipboard.</p>""")
        )
        self.copyAct.triggered.connect(self.__copy)
        self.__actions.append(self.copyAct)

        self.cutAct = EricAction(
            self.tr("Cut"),
            EricPixmapCache.getIcon("editCut"),
            self.tr("Cu&t"),
            QKeySequence(self.tr("Ctrl+X", "Edit|Cut")),
            0,
            self,
            "webbrowser_edit_cut",
        )
        self.cutAct.setStatusTip(self.tr("Cut the selected text"))
        self.cutAct.setWhatsThis(
            self.tr("""<b>Cut</b><p>Cut the selected text to the clipboard.</p>""")
        )
        self.cutAct.triggered.connect(self.__cut)
        self.__actions.append(self.cutAct)

        self.pasteAct = EricAction(
            self.tr("Paste"),
            EricPixmapCache.getIcon("editPaste"),
            self.tr("&Paste"),
            QKeySequence(self.tr("Ctrl+V", "Edit|Paste")),
            0,
            self,
            "webbrowser_edit_paste",
        )
        self.pasteAct.setStatusTip(self.tr("Paste text from the clipboard"))
        self.pasteAct.setWhatsThis(
            self.tr("""<b>Paste</b><p>Paste some text from the clipboard.</p>""")
        )
        self.pasteAct.triggered.connect(self.__paste)
        self.__actions.append(self.pasteAct)

        self.undoAct = EricAction(
            self.tr("Undo"),
            EricPixmapCache.getIcon("editUndo"),
            self.tr("&Undo"),
            QKeySequence(self.tr("Ctrl+Z", "Edit|Undo")),
            0,
            self,
            "webbrowser_edit_undo",
        )
        self.undoAct.setStatusTip(self.tr("Undo the last edit action"))
        self.undoAct.setWhatsThis(
            self.tr("""<b>Undo</b><p>Undo the last edit action.</p>""")
        )
        self.undoAct.triggered.connect(self.__undo)
        self.__actions.append(self.undoAct)

        self.redoAct = EricAction(
            self.tr("Redo"),
            EricPixmapCache.getIcon("editRedo"),
            self.tr("&Redo"),
            QKeySequence(self.tr("Ctrl+Shift+Z", "Edit|Redo")),
            0,
            self,
            "webbrowser_edit_redo",
        )
        self.redoAct.setStatusTip(self.tr("Redo the last edit action"))
        self.redoAct.setWhatsThis(
            self.tr("""<b>Redo</b><p>Redo the last edit action.</p>""")
        )
        self.redoAct.triggered.connect(self.__redo)
        self.__actions.append(self.redoAct)

        self.selectAllAct = EricAction(
            self.tr("Select All"),
            EricPixmapCache.getIcon("editSelectAll"),
            self.tr("&Select All"),
            QKeySequence(self.tr("Ctrl+A", "Edit|Select All")),
            0,
            self,
            "webbrowser_edit_select_all",
        )
        self.selectAllAct.setStatusTip(self.tr("Select all text"))
        self.selectAllAct.setWhatsThis(
            self.tr(
                """<b>Select All</b>"""
                """<p>Select all text of the current browser.</p>"""
            )
        )
        self.selectAllAct.triggered.connect(self.__selectAll)
        self.__actions.append(self.selectAllAct)

        self.unselectAct = EricAction(
            self.tr("Unselect"),
            self.tr("Unselect"),
            QKeySequence(self.tr("Alt+Ctrl+A", "Edit|Unselect")),
            0,
            self,
            "webbrowser_edit_unselect",
        )
        self.unselectAct.setStatusTip(self.tr("Clear current selection"))
        self.unselectAct.setWhatsThis(
            self.tr(
                """<b>Unselect</b>"""
                """<p>Clear the selection of the current browser.</p>"""
            )
        )
        self.unselectAct.triggered.connect(self.__unselect)
        self.__actions.append(self.unselectAct)

        self.findAct = EricAction(
            self.tr("Find..."),
            EricPixmapCache.getIcon("find"),
            self.tr("&Find..."),
            QKeySequence(self.tr("Ctrl+F", "Edit|Find")),
            0,
            self,
            "webbrowser_edit_find",
        )
        self.findAct.setStatusTip(self.tr("Find text in page"))
        self.findAct.setWhatsThis(
            self.tr("""<b>Find</b><p>Find text in the current page.</p>""")
        )
        self.findAct.triggered.connect(self.__find)
        self.__actions.append(self.findAct)

        self.findNextAct = EricAction(
            self.tr("Find next"),
            EricPixmapCache.getIcon("findNext"),
            self.tr("Find &next"),
            QKeySequence(self.tr("F3", "Edit|Find next")),
            0,
            self,
            "webbrowser_edit_find_next",
        )
        self.findNextAct.setStatusTip(self.tr("Find next occurrence of text in page"))
        self.findNextAct.setWhatsThis(
            self.tr(
                """<b>Find next</b>"""
                """<p>Find the next occurrence of text in the current page.</p>"""
            )
        )
        self.findNextAct.triggered.connect(self.__searchWidget.findNext)
        self.__actions.append(self.findNextAct)

        self.findPrevAct = EricAction(
            self.tr("Find previous"),
            EricPixmapCache.getIcon("findPrev"),
            self.tr("Find &previous"),
            QKeySequence(self.tr("Shift+F3", "Edit|Find previous")),
            0,
            self,
            "webbrowser_edit_find_previous",
        )
        self.findPrevAct.setStatusTip(
            self.tr("Find previous occurrence of text in page")
        )
        self.findPrevAct.setWhatsThis(
            self.tr(
                """<b>Find previous</b>"""
                """<p>Find the previous occurrence of text in the current"""
                """ page.</p>"""
            )
        )
        self.findPrevAct.triggered.connect(self.__searchWidget.findPrevious)
        self.__actions.append(self.findPrevAct)

        self.bookmarksManageAct = EricAction(
            self.tr("Manage Bookmarks"),
            self.tr("&Manage Bookmarks..."),
            QKeySequence(self.tr("Ctrl+Shift+B", "Help|Manage bookmarks")),
            0,
            self,
            "webbrowser_bookmarks_manage",
        )
        self.bookmarksManageAct.setStatusTip(
            self.tr("Open a dialog to manage the bookmarks.")
        )
        self.bookmarksManageAct.setWhatsThis(
            self.tr(
                """<b>Manage Bookmarks...</b>"""
                """<p>Open a dialog to manage the bookmarks.</p>"""
            )
        )
        self.bookmarksManageAct.triggered.connect(self.__showBookmarksDialog)
        self.__actions.append(self.bookmarksManageAct)

        self.bookmarksAddAct = EricAction(
            self.tr("Add Bookmark"),
            EricPixmapCache.getIcon("addBookmark"),
            self.tr("Add &Bookmark..."),
            QKeySequence(self.tr("Ctrl+D", "Help|Add bookmark")),
            0,
            self,
            "webbrowser_bookmark_add",
        )
        self.bookmarksAddAct.setIconVisibleInMenu(False)
        self.bookmarksAddAct.setStatusTip(self.tr("Open a dialog to add a bookmark."))
        self.bookmarksAddAct.setWhatsThis(
            self.tr(
                """<b>Add Bookmark</b>"""
                """<p>Open a dialog to add the current URL as a bookmark.</p>"""
            )
        )
        self.bookmarksAddAct.triggered.connect(self.__addBookmark)
        self.__actions.append(self.bookmarksAddAct)

        self.bookmarksAddFolderAct = EricAction(
            self.tr("Add Folder"),
            self.tr("Add &Folder..."),
            0,
            0,
            self,
            "webbrowser_bookmark_show_all",
        )
        self.bookmarksAddFolderAct.setStatusTip(
            self.tr("Open a dialog to add a new bookmarks folder.")
        )
        self.bookmarksAddFolderAct.setWhatsThis(
            self.tr(
                """<b>Add Folder...</b>"""
                """<p>Open a dialog to add a new bookmarks folder.</p>"""
            )
        )
        self.bookmarksAddFolderAct.triggered.connect(self.__addBookmarkFolder)
        self.__actions.append(self.bookmarksAddFolderAct)

        self.bookmarksAllTabsAct = EricAction(
            self.tr("Bookmark All Tabs"),
            self.tr("Bookmark All Tabs..."),
            0,
            0,
            self,
            "webbrowser_bookmark_all_tabs",
        )
        self.bookmarksAllTabsAct.setStatusTip(self.tr("Bookmark all open tabs."))
        self.bookmarksAllTabsAct.setWhatsThis(
            self.tr(
                """<b>Bookmark All Tabs...</b>"""
                """<p>Open a dialog to add a new bookmarks folder for"""
                """ all open tabs.</p>"""
            )
        )
        self.bookmarksAllTabsAct.triggered.connect(self.bookmarkAll)
        self.__actions.append(self.bookmarksAllTabsAct)

        self.whatsThisAct = EricAction(
            self.tr("What's This?"),
            EricPixmapCache.getIcon("whatsThis"),
            self.tr("&What's This?"),
            QKeySequence(self.tr("Shift+F1", "Help|What's This?'")),
            0,
            self,
            "webbrowser_help_whats_this",
        )
        self.whatsThisAct.setStatusTip(self.tr("Context sensitive help"))
        self.whatsThisAct.setWhatsThis(
            self.tr(
                """<b>Display context sensitive help</b>"""
                """<p>In What's This? mode, the mouse cursor shows an arrow"""
                """ with a question mark, and you can click on the interface"""
                """ elements to get a short description of what they do and how"""
                """ to use them. In dialogs, this feature can be accessed using"""
                """ the context help button in the titlebar.</p>"""
            )
        )
        self.whatsThisAct.triggered.connect(self.__whatsThis)
        self.__actions.append(self.whatsThisAct)

        self.aboutAct = EricAction(
            self.tr("About"), self.tr("&About"), 0, 0, self, "webbrowser_help_about"
        )
        self.aboutAct.setStatusTip(self.tr("Display information about this software"))
        self.aboutAct.setWhatsThis(
            self.tr(
                """<b>About</b>"""
                """<p>Display some information about this software.</p>"""
            )
        )
        self.aboutAct.triggered.connect(self.__about)
        self.__actions.append(self.aboutAct)

        self.aboutQtAct = EricAction(
            self.tr("About Qt"),
            self.tr("About &Qt"),
            0,
            0,
            self,
            "webbrowser_help_about_qt",
        )
        self.aboutQtAct.setStatusTip(
            self.tr("Display information about the Qt toolkit")
        )
        self.aboutQtAct.setWhatsThis(
            self.tr(
                """<b>About Qt</b>"""
                """<p>Display some information about the Qt toolkit.</p>"""
            )
        )
        self.aboutQtAct.triggered.connect(self.__aboutQt)
        self.__actions.append(self.aboutQtAct)

        self.zoomInAct = EricAction(
            self.tr("Zoom in"),
            EricPixmapCache.getIcon("zoomIn"),
            self.tr("Zoom &in"),
            QKeySequence(self.tr("Ctrl++", "View|Zoom in")),
            QKeySequence(self.tr("Zoom In", "View|Zoom in")),
            self,
            "webbrowser_view_zoom_in",
        )
        self.zoomInAct.setStatusTip(self.tr("Zoom in on the web page"))
        self.zoomInAct.setWhatsThis(
            self.tr(
                """<b>Zoom in</b>"""
                """<p>Zoom in on the web page."""
                """ This makes the web page bigger.</p>"""
            )
        )
        self.zoomInAct.triggered.connect(self.__zoomIn)
        self.__actions.append(self.zoomInAct)

        self.zoomOutAct = EricAction(
            self.tr("Zoom out"),
            EricPixmapCache.getIcon("zoomOut"),
            self.tr("Zoom &out"),
            QKeySequence(self.tr("Ctrl+-", "View|Zoom out")),
            QKeySequence(self.tr("Zoom Out", "View|Zoom out")),
            self,
            "webbrowser_view_zoom_out",
        )
        self.zoomOutAct.setStatusTip(self.tr("Zoom out on the web page"))
        self.zoomOutAct.setWhatsThis(
            self.tr(
                """<b>Zoom out</b>"""
                """<p>Zoom out on the web page."""
                """ This makes the web page smaller.</p>"""
            )
        )
        self.zoomOutAct.triggered.connect(self.__zoomOut)
        self.__actions.append(self.zoomOutAct)

        self.zoomResetAct = EricAction(
            self.tr("Zoom reset"),
            EricPixmapCache.getIcon("zoomReset"),
            self.tr("Zoom &reset"),
            QKeySequence(self.tr("Ctrl+0", "View|Zoom reset")),
            0,
            self,
            "webbrowser_view_zoom_reset",
        )
        self.zoomResetAct.setStatusTip(self.tr("Reset the zoom of the web page"))
        self.zoomResetAct.setWhatsThis(
            self.tr(
                """<b>Zoom reset</b>"""
                """<p>Reset the zoom of the web page. """
                """This sets the zoom factor to 100%.</p>"""
            )
        )
        self.zoomResetAct.triggered.connect(self.__zoomReset)
        self.__actions.append(self.zoomResetAct)

        self.pageSourceAct = EricAction(
            self.tr("Show page source"),
            self.tr("Show page source"),
            QKeySequence(self.tr("Ctrl+U")),
            0,
            self,
            "webbrowser_show_page_source",
        )
        self.pageSourceAct.setStatusTip(self.tr("Show the page source in an editor"))
        self.pageSourceAct.setWhatsThis(
            self.tr(
                """<b>Show page source</b>"""
                """<p>Show the page source in an editor.</p>"""
            )
        )
        self.pageSourceAct.triggered.connect(self.__showPageSource)
        self.__actions.append(self.pageSourceAct)
        self.addAction(self.pageSourceAct)

        self.fullScreenAct = EricAction(
            self.tr("Full Screen"),
            EricPixmapCache.getIcon("windowFullscreen"),
            self.tr("&Full Screen"),
            0,
            0,
            self,
            "webbrowser_view_full_screen",
        )
        if OSUtilities.isMacPlatform():
            self.fullScreenAct.setShortcut(QKeySequence(self.tr("Meta+Ctrl+F")))
        else:
            self.fullScreenAct.setShortcut(QKeySequence(self.tr("F11")))
        self.fullScreenAct.triggered.connect(self.toggleFullScreen)
        self.__actions.append(self.fullScreenAct)
        self.addAction(self.fullScreenAct)

        self.nextTabAct = EricAction(
            self.tr("Show next tab"),
            self.tr("Show next tab"),
            QKeySequence(self.tr("Ctrl+Alt+Tab")),
            0,
            self,
            "webbrowser_view_next_tab",
        )
        self.nextTabAct.triggered.connect(self.__nextTab)
        self.__actions.append(self.nextTabAct)
        self.addAction(self.nextTabAct)

        self.prevTabAct = EricAction(
            self.tr("Show previous tab"),
            self.tr("Show previous tab"),
            QKeySequence(self.tr("Shift+Ctrl+Alt+Tab")),
            0,
            self,
            "webbrowser_view_previous_tab",
        )
        self.prevTabAct.triggered.connect(self.__prevTab)
        self.__actions.append(self.prevTabAct)
        self.addAction(self.prevTabAct)

        self.switchTabAct = EricAction(
            self.tr("Switch between tabs"),
            self.tr("Switch between tabs"),
            QKeySequence(self.tr("Ctrl+1")),
            0,
            self,
            "webbrowser_switch_tabs",
        )
        self.switchTabAct.triggered.connect(self.__switchTab)
        self.__actions.append(self.switchTabAct)
        self.addAction(self.switchTabAct)

        self.prefAct = EricAction(
            self.tr("Preferences"),
            EricPixmapCache.getIcon("configure"),
            self.tr("&Preferences..."),
            0,
            0,
            self,
            "webbrowser_preferences",
        )
        self.prefAct.setStatusTip(self.tr("Set the prefered configuration"))
        self.prefAct.setWhatsThis(
            self.tr(
                """<b>Preferences</b>"""
                """<p>Set the configuration items of the application"""
                """ with your prefered values.</p>"""
            )
        )
        self.prefAct.triggered.connect(self.__showPreferences)
        self.__actions.append(self.prefAct)

        self.acceptedLanguagesAct = EricAction(
            self.tr("Languages"),
            EricPixmapCache.getIcon("flag"),
            self.tr("&Languages..."),
            0,
            0,
            self,
            "webbrowser_accepted_languages",
        )
        self.acceptedLanguagesAct.setStatusTip(
            self.tr("Configure the accepted languages for web pages")
        )
        self.acceptedLanguagesAct.setWhatsThis(
            self.tr(
                """<b>Languages</b>"""
                """<p>Configure the accepted languages for web pages.</p>"""
            )
        )
        self.acceptedLanguagesAct.triggered.connect(self.__showAcceptedLanguages)
        self.__actions.append(self.acceptedLanguagesAct)

        self.cookiesAct = EricAction(
            self.tr("Cookies"),
            EricPixmapCache.getIcon("cookie"),
            self.tr("C&ookies..."),
            0,
            0,
            self,
            "webbrowser_cookies",
        )
        self.cookiesAct.setStatusTip(self.tr("Configure cookies handling"))
        self.cookiesAct.setWhatsThis(
            self.tr("""<b>Cookies</b><p>Configure cookies handling.</p>""")
        )
        self.cookiesAct.triggered.connect(self.__showCookiesConfiguration)
        self.__actions.append(self.cookiesAct)

        self.personalDataAct = EricAction(
            self.tr("Personal Information"),
            EricPixmapCache.getIcon("pim"),
            self.tr("Personal Information..."),
            0,
            0,
            self,
            "webbrowser_personal_information",
        )
        self.personalDataAct.setStatusTip(
            self.tr("Configure personal information for completing form fields")
        )
        self.personalDataAct.setWhatsThis(
            self.tr(
                """<b>Personal Information...</b>"""
                """<p>Opens a dialog to configure the personal information"""
                """ used for completing form fields.</p>"""
            )
        )
        self.personalDataAct.triggered.connect(self.__showPersonalInformationDialog)
        self.__actions.append(self.personalDataAct)

        self.greaseMonkeyAct = EricAction(
            self.tr("GreaseMonkey Scripts"),
            EricPixmapCache.getIcon("greaseMonkey"),
            self.tr("GreaseMonkey Scripts..."),
            0,
            0,
            self,
            "webbrowser_greasemonkey",
        )
        self.greaseMonkeyAct.setStatusTip(self.tr("Configure the GreaseMonkey Scripts"))
        self.greaseMonkeyAct.setWhatsThis(
            self.tr(
                """<b>GreaseMonkey Scripts...</b>"""
                """<p>Opens a dialog to configure the available GreaseMonkey"""
                """ Scripts.</p>"""
            )
        )
        self.greaseMonkeyAct.triggered.connect(self.__showGreaseMonkeyConfigDialog)
        self.__actions.append(self.greaseMonkeyAct)

        self.editMessageFilterAct = EricAction(
            self.tr("Edit Message Filters"),
            EricPixmapCache.getIcon("warning"),
            self.tr("Edit Message Filters..."),
            0,
            0,
            self,
            "webbrowser_manage_message_filters",
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
        self.__actions.append(self.editMessageFilterAct)

        self.featurePermissionAct = EricAction(
            self.tr("Edit HTML5 Feature Permissions"),
            EricPixmapCache.getIcon("featurePermission"),
            self.tr("Edit HTML5 Feature Permissions..."),
            0,
            0,
            self,
            "webbrowser_edit_feature_permissions",
        )
        self.featurePermissionAct.setStatusTip(
            self.tr("Edit the remembered HTML5 feature permissions")
        )
        self.featurePermissionAct.setWhatsThis(
            self.tr(
                """<b>Edit HTML5 Feature Permissions</b>"""
                """<p>Opens a dialog to edit the remembered HTML5"""
                """ feature permissions.</p>"""
            )
        )
        self.featurePermissionAct.triggered.connect(self.__showFeaturePermissionDialog)
        self.__actions.append(self.featurePermissionAct)

        if WebBrowserWindow._useQtHelp:
            self.syncTocAct = EricAction(
                self.tr("Sync with Table of Contents"),
                EricPixmapCache.getIcon("syncToc"),
                self.tr("Sync with Table of Contents"),
                0,
                0,
                self,
                "webbrowser_sync_toc",
            )
            self.syncTocAct.setStatusTip(
                self.tr("Synchronizes the table of contents with current page")
            )
            self.syncTocAct.setWhatsThis(
                self.tr(
                    """<b>Sync with Table of Contents</b>"""
                    """<p>Synchronizes the table of contents with current"""
                    """ page.</p>"""
                )
            )
            self.syncTocAct.triggered.connect(self.__syncTOC)
            self.__actions.append(self.syncTocAct)

            self.showTocAct = EricAction(
                self.tr("Table of Contents"),
                self.tr("Table of Contents"),
                0,
                0,
                self,
                "webbrowser_show_toc",
            )
            self.showTocAct.setStatusTip(self.tr("Shows the table of contents window"))
            self.showTocAct.setWhatsThis(
                self.tr(
                    """<b>Table of Contents</b>"""
                    """<p>Shows the table of contents window.</p>"""
                )
            )
            self.showTocAct.triggered.connect(self.__showTocWindow)
            self.__actions.append(self.showTocAct)

            self.showIndexAct = EricAction(
                self.tr("Index"), self.tr("Index"), 0, 0, self, "webbrowser_show_index"
            )
            self.showIndexAct.setStatusTip(self.tr("Shows the index window"))
            self.showIndexAct.setWhatsThis(
                self.tr("""<b>Index</b><p>Shows the index window.</p>""")
            )
            self.showIndexAct.triggered.connect(self.__showIndexWindow)
            self.__actions.append(self.showIndexAct)

            self.showSearchAct = EricAction(
                self.tr("Search"),
                self.tr("Search"),
                0,
                0,
                self,
                "webbrowser_show_search",
            )
            self.showSearchAct.setStatusTip(self.tr("Shows the search window"))
            self.showSearchAct.setWhatsThis(
                self.tr("""<b>Search</b><p>Shows the search window.</p>""")
            )
            self.showSearchAct.triggered.connect(self.__showSearchWindow)
            self.__actions.append(self.showSearchAct)

            self.manageQtHelpDocsAct = EricAction(
                self.tr("Manage QtHelp Documents"),
                self.tr("Manage QtHelp &Documents"),
                0,
                0,
                self,
                "webbrowser_qthelp_documents",
            )
            self.manageQtHelpDocsAct.setStatusTip(
                self.tr("Shows a dialog to manage the QtHelp documentation set")
            )
            self.manageQtHelpDocsAct.setWhatsThis(
                self.tr(
                    """<b>Manage QtHelp Documents</b>"""
                    """<p>Shows a dialog to manage the QtHelp documentation"""
                    """ set.</p>"""
                )
            )
            self.manageQtHelpDocsAct.triggered.connect(self.__manageQtHelpDocumentation)
            self.__actions.append(self.manageQtHelpDocsAct)

            self.reindexDocumentationAct = EricAction(
                self.tr("Reindex Documentation"),
                self.tr("&Reindex Documentation"),
                0,
                0,
                self,
                "webbrowser_qthelp_reindex",
            )
            self.reindexDocumentationAct.setStatusTip(
                self.tr("Reindexes the documentation set")
            )
            self.reindexDocumentationAct.setWhatsThis(
                self.tr(
                    """<b>Reindex Documentation</b>"""
                    """<p>Reindexes the documentation set.</p>"""
                )
            )
            self.reindexDocumentationAct.triggered.connect(
                self.__searchEngine.reindexDocumentation
            )
            self.__actions.append(self.reindexDocumentationAct)

        self.clearPrivateDataAct = EricAction(
            self.tr("Clear private data"),
            EricPixmapCache.getIcon("clearPrivateData"),
            self.tr("Clear private data"),
            0,
            0,
            self,
            "webbrowser_clear_private_data",
        )
        self.clearPrivateDataAct.setStatusTip(self.tr("Clear private data"))
        self.clearPrivateDataAct.setWhatsThis(
            self.tr(
                """<b>Clear private data</b>"""
                """<p>Clears the private data like browsing history, search"""
                """ history or the favicons database.</p>"""
            )
        )
        self.clearPrivateDataAct.triggered.connect(self.__clearPrivateData)
        self.__actions.append(self.clearPrivateDataAct)

        self.clearIconsAct = EricAction(
            self.tr("Clear icons database"),
            self.tr("Clear &icons database"),
            0,
            0,
            self,
            "webbrowser_clear_icons_db",
        )
        self.clearIconsAct.setStatusTip(self.tr("Clear the database of favicons"))
        self.clearIconsAct.setWhatsThis(
            self.tr(
                """<b>Clear icons database</b>"""
                """<p>Clears the database of favicons of previously visited"""
                """ URLs.</p>"""
            )
        )
        self.clearIconsAct.triggered.connect(self.__clearIconsDatabase)
        self.__actions.append(self.clearIconsAct)

        self.manageIconsAct = EricAction(
            self.tr("Manage Saved Favicons"),
            EricPixmapCache.getIcon("icons"),
            self.tr("Manage Saved Favicons"),
            0,
            0,
            self,
            "webbrowser_manage_icons_db",
        )
        self.manageIconsAct.setStatusTip(
            self.tr("Show a dialog to manage the saved favicons")
        )
        self.manageIconsAct.setWhatsThis(
            self.tr(
                """<b>Manage Saved Favicons</b>"""
                """<p>This shows a dialog to manage the saved favicons of"""
                """ previously visited URLs.</p>"""
            )
        )
        self.manageIconsAct.triggered.connect(self.__showWebIconsDialog)
        self.__actions.append(self.manageIconsAct)

        self.searchEnginesAct = EricAction(
            self.tr("Configure Search Engines"),
            self.tr("Configure Search &Engines..."),
            0,
            0,
            self,
            "webbrowser_search_engines",
        )
        self.searchEnginesAct.setStatusTip(
            self.tr("Configure the available search engines")
        )
        self.searchEnginesAct.setWhatsThis(
            self.tr(
                """<b>Configure Search Engines...</b>"""
                """<p>Opens a dialog to configure the available search"""
                """ engines.</p>"""
            )
        )
        self.searchEnginesAct.triggered.connect(self.__showEnginesConfigurationDialog)
        self.__actions.append(self.searchEnginesAct)

        self.passwordsAct = EricAction(
            self.tr("Manage Saved Passwords"),
            EricPixmapCache.getIcon("passwords"),
            self.tr("Manage Saved Passwords..."),
            0,
            0,
            self,
            "webbrowser_manage_passwords",
        )
        self.passwordsAct.setStatusTip(self.tr("Manage the saved passwords"))
        self.passwordsAct.setWhatsThis(
            self.tr(
                """<b>Manage Saved Passwords...</b>"""
                """<p>Opens a dialog to manage the saved passwords.</p>"""
            )
        )
        self.passwordsAct.triggered.connect(self.__showPasswordsDialog)
        self.__actions.append(self.passwordsAct)

        self.securityKeysAct = EricAction(
            self.tr("Manage FIDO2 Security Keys"),
            EricPixmapCache.getIcon("securityKey"),
            self.tr("Manage FIDO2 Security Keys..."),
            0,
            0,
            self,
            "webbrowser_manage_security_keys",
        )
        self.securityKeysAct.setStatusTip(self.tr("Manage FIDO2 security keys"))
        self.securityKeysAct.setWhatsThis(
            self.tr(
                """<b>Manage FIDO2 Security Keys...</b>"""
                """<p>Opens a dialog to manage FIDO2 security keys.</p>"""
            )
        )
        self.securityKeysAct.triggered.connect(self.__showSecurityKeysDialog)
        self.__actions.append(self.securityKeysAct)
        self.securityKeysAct.setEnabled(importlib.util.find_spec("fido2") is not None)

        self.adblockAct = EricAction(
            self.tr("Ad Block"),
            EricPixmapCache.getIcon("adBlockPlus"),
            self.tr("&Ad Block..."),
            0,
            0,
            self,
            "webbrowser_adblock",
        )
        self.adblockAct.setStatusTip(
            self.tr("Configure AdBlock subscriptions and rules")
        )
        self.adblockAct.setWhatsThis(
            self.tr(
                """<b>Ad Block...</b>"""
                """<p>Opens a dialog to configure AdBlock subscriptions and"""
                """ rules.</p>"""
            )
        )
        self.adblockAct.triggered.connect(self.__showAdBlockDialog)
        self.__actions.append(self.adblockAct)

        self.certificateErrorsAct = EricAction(
            self.tr("Manage SSL Certificate Errors"),
            EricPixmapCache.getIcon("certificates"),
            self.tr("Manage SSL Certificate Errors..."),
            0,
            0,
            self,
            "webbrowser_manage_certificate_errors",
        )
        self.certificateErrorsAct.setStatusTip(
            self.tr("Manage the accepted SSL certificate Errors")
        )
        self.certificateErrorsAct.setWhatsThis(
            self.tr(
                """<b>Manage SSL Certificate Errors...</b>"""
                """<p>Opens a dialog to manage the accepted SSL"""
                """ certificate errors.</p>"""
            )
        )
        self.certificateErrorsAct.triggered.connect(self.__showCertificateErrorsDialog)
        self.__actions.append(self.certificateErrorsAct)

        self.safeBrowsingAct = EricAction(
            self.tr("Manage Safe Browsing"),
            EricPixmapCache.getIcon("safeBrowsing"),
            self.tr("Manage Safe Browsing..."),
            0,
            0,
            self,
            "webbrowser_manage_safe_browsing",
        )
        self.safeBrowsingAct.setStatusTip(
            self.tr("Configure Safe Browsing and manage local cache")
        )
        self.safeBrowsingAct.setWhatsThis(
            self.tr(
                """<b>Manage Safe Browsing</b>"""
                """<p>This opens a dialog to configure Safe Browsing and"""
                """ to manage the local cache.</p>"""
            )
        )
        self.safeBrowsingAct.triggered.connect(self.__showSafeBrowsingDialog)
        self.__actions.append(self.safeBrowsingAct)

        self.showDownloadManagerAct = EricAction(
            self.tr("Downloads"),
            self.tr("Downloads"),
            0,
            0,
            self,
            "webbrowser_show_downloads",
        )
        self.showDownloadManagerAct.setStatusTip(self.tr("Shows the downloads window"))
        self.showDownloadManagerAct.setWhatsThis(
            self.tr("""<b>Downloads</b><p>Shows the downloads window.</p>""")
        )
        self.showDownloadManagerAct.triggered.connect(self.__showDownloadsWindow)
        self.__actions.append(self.showDownloadManagerAct)

        self.feedsManagerAct = EricAction(
            self.tr("RSS Feeds Dialog"),
            EricPixmapCache.getIcon("rss22"),
            self.tr("&RSS Feeds Dialog..."),
            QKeySequence(self.tr("Ctrl+Shift+F", "Help|RSS Feeds Dialog")),
            0,
            self,
            "webbrowser_rss_feeds",
        )
        self.feedsManagerAct.setStatusTip(
            self.tr("Open a dialog showing the configured RSS feeds.")
        )
        self.feedsManagerAct.setWhatsThis(
            self.tr(
                """<b>RSS Feeds Dialog...</b>"""
                """<p>Open a dialog to show the configured RSS feeds."""
                """ It can be used to mange the feeds and to show their"""
                """ contents.</p>"""
            )
        )
        self.feedsManagerAct.triggered.connect(self.__showFeedsManager)
        self.__actions.append(self.feedsManagerAct)

        self.siteInfoAct = EricAction(
            self.tr("Siteinfo Dialog"),
            EricPixmapCache.getIcon("helpAbout"),
            self.tr("&Siteinfo Dialog..."),
            QKeySequence(self.tr("Ctrl+Shift+I", "Help|Siteinfo Dialog")),
            0,
            self,
            "webbrowser_siteinfo",
        )
        self.siteInfoAct.setStatusTip(
            self.tr("Open a dialog showing some information about the current site.")
        )
        self.siteInfoAct.setWhatsThis(
            self.tr(
                """<b>Siteinfo Dialog...</b>"""
                """<p>Opens a dialog showing some information about the current"""
                """ site.</p>"""
            )
        )
        self.siteInfoAct.triggered.connect(self.__showSiteinfoDialog)
        self.__actions.append(self.siteInfoAct)

        self.userAgentManagerAct = EricAction(
            self.tr("Manage User Agent Settings"),
            self.tr("Manage &User Agent Settings"),
            0,
            0,
            self,
            "webbrowser_user_agent_settings",
        )
        self.userAgentManagerAct.setStatusTip(
            self.tr("Shows a dialog to manage the User Agent settings")
        )
        self.userAgentManagerAct.setWhatsThis(
            self.tr(
                """<b>Manage User Agent Settings</b>"""
                """<p>Shows a dialog to manage the User Agent settings.</p>"""
            )
        )
        self.userAgentManagerAct.triggered.connect(self.__showUserAgentsDialog)
        self.__actions.append(self.userAgentManagerAct)

        self.synchronizationAct = EricAction(
            self.tr("Synchronize data"),
            EricPixmapCache.getIcon("sync"),
            self.tr("&Synchronize Data..."),
            0,
            0,
            self,
            "webbrowser_synchronize_data",
        )
        self.synchronizationAct.setStatusTip(
            self.tr("Shows a dialog to synchronize data via the network")
        )
        self.synchronizationAct.setWhatsThis(
            self.tr(
                """<b>Synchronize Data...</b>"""
                """<p>This shows a dialog to synchronize data via the"""
                """ network.</p>"""
            )
        )
        self.synchronizationAct.triggered.connect(self.__showSyncDialog)
        self.__actions.append(self.synchronizationAct)

        self.zoomValuesAct = EricAction(
            self.tr("Manage Saved Zoom Values"),
            EricPixmapCache.getIcon("zoomReset"),
            self.tr("Manage Saved Zoom Values..."),
            0,
            0,
            self,
            "webbrowser_manage_zoom_values",
        )
        self.zoomValuesAct.setStatusTip(self.tr("Manage the saved zoom values"))
        self.zoomValuesAct.setWhatsThis(
            self.tr(
                """<b>Manage Saved Zoom Values...</b>"""
                """<p>Opens a dialog to manage the saved zoom values.</p>"""
            )
        )
        self.zoomValuesAct.triggered.connect(self.__showZoomValuesDialog)
        self.__actions.append(self.zoomValuesAct)

        self.showJavaScriptConsoleAct = EricAction(
            self.tr("JavaScript Console"),
            self.tr("JavaScript Console"),
            0,
            0,
            self,
            "webbrowser_show_javascript_console",
        )
        self.showJavaScriptConsoleAct.setStatusTip(
            self.tr("Toggle the JavaScript console window")
        )
        self.showJavaScriptConsoleAct.setWhatsThis(
            self.tr(
                """<b>JavaScript Console</b>"""
                """<p>This toggles the JavaScript console window.</p>"""
            )
        )
        self.showJavaScriptConsoleAct.triggered.connect(self.__toggleJavaScriptConsole)
        self.__actions.append(self.showJavaScriptConsoleAct)

        self.showTabManagerAct = EricAction(
            self.tr("Tab Manager"),
            self.tr("Tab Manager"),
            0,
            0,
            self,
            "webbrowser_show_tab_manager",
        )
        self.showTabManagerAct.setStatusTip(self.tr("Shows the tab manager window"))
        self.showTabManagerAct.setWhatsThis(
            self.tr("""<b>Tab Manager</b><p>Shows the tab manager window.</p>""")
        )
        self.showTabManagerAct.triggered.connect(
            lambda: self.__showTabManager(self.showTabManagerAct)
        )
        self.__actions.append(self.showTabManagerAct)

        self.showSessionsManagerAct = EricAction(
            self.tr("Session Manager"),
            self.tr("Session Manager..."),
            0,
            0,
            self,
            "webbrowser_show_session_manager",
        )
        self.showSessionsManagerAct.setStatusTip(
            self.tr("Shows the session manager window")
        )
        self.showSessionsManagerAct.setWhatsThis(
            self.tr(
                """<b>Session Manager</b>"""
                """<p>Shows the session manager window.</p>"""
            )
        )
        self.showSessionsManagerAct.triggered.connect(self.__showSessionManagerDialog)
        self.__actions.append(self.showSessionsManagerAct)

        self.virustotalScanCurrentAct = EricAction(
            self.tr("Scan current site"),
            EricPixmapCache.getIcon("virustotal"),
            self.tr("Scan current site"),
            0,
            0,
            self,
            "webbrowser_virustotal_scan_site",
        )
        self.virustotalScanCurrentAct.triggered.connect(
            self.__virusTotalScanCurrentSite
        )
        self.__actions.append(self.virustotalScanCurrentAct)

        self.virustotalIpReportAct = EricAction(
            self.tr("IP Address Report"),
            EricPixmapCache.getIcon("virustotal"),
            self.tr("IP Address Report"),
            0,
            0,
            self,
            "webbrowser_virustotal_ip_report",
        )
        self.virustotalIpReportAct.triggered.connect(self.__virusTotalIpAddressReport)
        self.__actions.append(self.virustotalIpReportAct)

        self.virustotalDomainReportAct = EricAction(
            self.tr("Domain Report"),
            EricPixmapCache.getIcon("virustotal"),
            self.tr("Domain Report"),
            0,
            0,
            self,
            "webbrowser_virustotal_domain_report",
        )
        self.virustotalDomainReportAct.triggered.connect(self.__virusTotalDomainReport)
        self.__actions.append(self.virustotalDomainReportAct)

        if (
            not Preferences.getWebBrowser("VirusTotalEnabled")
            or Preferences.getWebBrowser("VirusTotalServiceKey") == ""
        ):
            self.virustotalScanCurrentAct.setEnabled(False)
            self.virustotalIpReportAct.setEnabled(False)
            self.virustotalDomainReportAct.setEnabled(False)

        self.shortcutsAct = EricAction(
            self.tr("Keyboard Shortcuts"),
            EricPixmapCache.getIcon("configureShortcuts"),
            self.tr("Keyboard &Shortcuts..."),
            0,
            0,
            self,
            "webbrowser_keyboard_shortcuts",
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
        self.__actions.append(self.shortcutsAct)

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
        self.__actions.append(self.exportShortcutsAct)

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
        self.__actions.append(self.importShortcutsAct)

        self.showProtocolHandlerManagerAct = EricAction(
            self.tr("Protocol Handler Manager"),
            self.tr("Protocol Handler Manager..."),
            0,
            0,
            self,
            "webbrowser_show_protocol_handler_manager",
        )
        self.showProtocolHandlerManagerAct.setStatusTip(
            self.tr("Shows the protocol handler manager window")
        )
        self.showProtocolHandlerManagerAct.setWhatsThis(
            self.tr(
                """<b>Protocol Handler Manager</b>"""
                """<p>Shows the protocol handler manager window.</p>"""
            )
        )
        self.showProtocolHandlerManagerAct.triggered.connect(
            self.__showProtocolHandlerManagerDialog
        )
        self.__actions.append(self.showProtocolHandlerManagerAct)

        self.backAct.setEnabled(False)
        self.forwardAct.setEnabled(False)

        # now read the keyboard shortcuts for the actions
        Shortcuts.readShortcuts(webBrowser=self)

    def getActions(self):
        """
        Public method to get a list of all actions.

        @return list of all actions
        @rtype list of EricAction
        """
        return self.__actions[:]

    def getActionsCategory(self):
        """
        Public method to get the category of the defined actions.

        @return category of the actions
        @rtype str
        """
        return "WebBrowser"

    def __initMenus(self):
        """
        Private method to create the menus.
        """
        from .Bookmarks.BookmarksMenu import BookmarksMenuBarMenu
        from .History.HistoryMenu import HistoryMenu
        from .UserAgent.UserAgentMenu import UserAgentMenu

        mb = self.menuBar()

        menu = mb.addMenu(self.tr("&File"))
        menu.addAction(self.newTabAct)
        menu.addAction(self.newAct)
        menu.addAction(self.newPrivateAct)
        menu.addAction(self.openAct)
        menu.addAction(self.openTabAct)
        menu.addSeparator()
        if not self.isPrivate():
            sessionsMenu = menu.addMenu(self.tr("Sessions"))
            sessionsMenu.aboutToShow.connect(
                lambda: self.sessionManager().aboutToShowSessionsMenu(sessionsMenu)
            )
            menu.addAction(self.showSessionsManagerAct)
            menu.addSeparator()
        if self.saveAsAct is not None:
            menu.addAction(self.saveAsAct)
        menu.addAction(self.saveVisiblePageScreenAct)
        menu.addSeparator()
        if self.printPreviewAct:
            menu.addAction(self.printPreviewAct)
        if self.printAct:
            menu.addAction(self.printAct)
        if self.printPdfAct:
            menu.addAction(self.printPdfAct)
        menu.addAction(self.sendPageLinkAct)
        menu.addSeparator()
        menu.addAction(self.closeAct)
        menu.addAction(self.closeAllAct)
        menu.addSeparator()
        menu.addAction(self.exitAct)
        self.addActions(menu.actions())

        menu = mb.addMenu(self.tr("&Edit"))
        menu.addAction(self.undoAct)
        menu.addAction(self.redoAct)
        menu.addSeparator()
        menu.addAction(self.copyAct)
        menu.addAction(self.cutAct)
        menu.addAction(self.pasteAct)
        menu.addSeparator()
        menu.addAction(self.selectAllAct)
        menu.addAction(self.unselectAct)
        menu.addSeparator()
        menu.addAction(self.findAct)
        menu.addAction(self.findNextAct)
        menu.addAction(self.findPrevAct)
        self.addActions(menu.actions())

        menu = mb.addMenu(self.tr("&View"))
        menu.addAction(self.stopAct)
        menu.addAction(self.reloadAct)
        if WebBrowserWindow._useQtHelp:
            menu.addSeparator()
            menu.addAction(self.syncTocAct)
        menu.addSeparator()
        menu.addAction(self.zoomInAct)
        menu.addAction(self.zoomResetAct)
        menu.addAction(self.zoomOutAct)
        menu.addSeparator()
        self.__textEncodingMenu = menu.addMenu(self.tr("Text Encoding"))
        self.__textEncodingMenu.aboutToShow.connect(self.__aboutToShowTextEncodingMenu)
        self.__textEncodingMenu.triggered.connect(self.__setTextEncoding)
        menu.addSeparator()
        menu.addAction(self.pageSourceAct)
        menu.addAction(self.fullScreenAct)
        self.addActions(menu.actions())

        self.historyMenu = HistoryMenu(self, self.__tabWidget)
        self.historyMenu.setTitle(self.tr("H&istory"))
        self.historyMenu.openUrl.connect(self.openUrl)
        self.historyMenu.newTab.connect(self.openUrlNewTab)
        self.historyMenu.newBackgroundTab.connect(self.openUrlNewBackgroundTab)
        self.historyMenu.newWindow.connect(self.openUrlNewWindow)
        self.historyMenu.newPrivateWindow.connect(self.openUrlNewPrivateWindow)
        mb.addMenu(self.historyMenu)

        historyActions = []
        historyActions.append(self.backAct)
        historyActions.append(self.forwardAct)
        historyActions.append(self.homeAct)
        self.historyMenu.setInitialActions(historyActions)
        self.addActions(historyActions)

        self.bookmarksMenu = BookmarksMenuBarMenu(self)
        self.bookmarksMenu.setTitle(self.tr("&Bookmarks"))
        self.bookmarksMenu.openUrl.connect(self.openUrl)
        self.bookmarksMenu.newTab.connect(self.openUrlNewTab)
        self.bookmarksMenu.newWindow.connect(self.openUrlNewWindow)
        mb.addMenu(self.bookmarksMenu)

        bookmarksActions = []
        bookmarksActions.append(self.bookmarksManageAct)
        bookmarksActions.append(self.bookmarksAddAct)
        bookmarksActions.append(self.bookmarksAllTabsAct)
        bookmarksActions.append(self.bookmarksAddFolderAct)
        bookmarksActions.append("--SEPARATOR--")
        bookmarksActions.append(self.importBookmarksAct)
        bookmarksActions.append(self.exportBookmarksAct)
        self.bookmarksMenu.setInitialActions(bookmarksActions)

        menu = mb.addMenu(self.tr("&Settings"))
        menu.addAction(self.prefAct)
        menu.addSeparator()
        menu.addAction(self.shortcutsAct)
        menu.addAction(self.exportShortcutsAct)
        menu.addAction(self.importShortcutsAct)
        menu.addSeparator()
        menu.addAction(self.acceptedLanguagesAct)
        menu.addAction(self.cookiesAct)
        menu.addAction(self.personalDataAct)
        menu.addAction(self.greaseMonkeyAct)
        menu.addAction(self.featurePermissionAct)
        menu.addSeparator()
        menu.addAction(self.editMessageFilterAct)
        menu.addSeparator()
        menu.addAction(self.searchEnginesAct)
        menu.addSeparator()
        menu.addAction(self.passwordsAct)
        menu.addAction(self.securityKeysAct)
        menu.addAction(self.certificateErrorsAct)
        menu.addSeparator()
        menu.addAction(self.zoomValuesAct)
        menu.addAction(self.manageIconsAct)
        menu.addSeparator()
        menu.addAction(self.adblockAct)
        menu.addSeparator()
        menu.addAction(self.safeBrowsingAct)
        menu.addSeparator()
        self.__settingsMenu = menu
        self.__settingsMenu.aboutToShow.connect(self.__aboutToShowSettingsMenu)

        self.__userAgentMenu = UserAgentMenu(self.tr("Global User Agent"))
        menu.addMenu(self.__userAgentMenu)
        menu.addAction(self.userAgentManagerAct)
        menu.addSeparator()

        if WebBrowserWindow._useQtHelp:
            menu.addAction(self.manageQtHelpDocsAct)
            menu.addAction(self.reindexDocumentationAct)
            menu.addSeparator()
        menu.addAction(self.clearPrivateDataAct)
        menu.addAction(self.clearIconsAct)

        menu = mb.addMenu(self.tr("&Tools"))
        menu.addAction(self.feedsManagerAct)
        menu.addAction(self.siteInfoAct)
        menu.addSeparator()
        menu.addAction(self.synchronizationAct)
        menu.addSeparator()
        vtMenu = menu.addMenu(
            EricPixmapCache.getIcon("virustotal"), self.tr("&VirusTotal")
        )
        vtMenu.addAction(self.virustotalScanCurrentAct)
        vtMenu.addAction(self.virustotalIpReportAct)
        vtMenu.addAction(self.virustotalDomainReportAct)

        menu = mb.addMenu(self.tr("&Windows"))
        menu.addAction(self.showDownloadManagerAct)
        menu.addAction(self.showJavaScriptConsoleAct)
        menu.addAction(self.showTabManagerAct)
        menu.addAction(self.showProtocolHandlerManagerAct)
        if WebBrowserWindow._useQtHelp:
            menu.addSection(self.tr("QtHelp"))
            menu.addAction(self.showTocAct)
            menu.addAction(self.showIndexAct)
            menu.addAction(self.showSearchAct)
        menu.addSeparator()
        self.__toolbarsMenu = menu.addMenu(self.tr("&Toolbars"))
        self.__toolbarsMenu.aboutToShow.connect(self.__showToolbarsMenu)
        self.__toolbarsMenu.triggered.connect(self.__TBMenuTriggered)

        mb.addSeparator()

        menu = mb.addMenu(self.tr("&Help"))
        menu.addAction(self.aboutAct)
        menu.addAction(self.aboutQtAct)
        menu.addSeparator()
        menu.addAction(self.whatsThisAct)
        self.addActions(menu.actions())

    def __initSuperMenu(self):
        """
        Private method to create the super menu and attach it to the super
        menu button.
        """
        self.__superMenu = QMenu(self)

        self.__superMenu.addAction(self.newTabAct)
        self.__superMenu.addAction(self.newAct)
        self.__superMenu.addAction(self.newPrivateAct)
        self.__superMenu.addAction(self.openAct)
        self.__superMenu.addAction(self.openTabAct)
        self.__superMenu.addSeparator()

        if not self.isPrivate():
            sessionsMenu = self.__superMenu.addMenu(self.tr("Sessions"))
            sessionsMenu.aboutToShow.connect(
                lambda: self.sessionManager().aboutToShowSessionsMenu(sessionsMenu)
            )
            self.__superMenu.addAction(self.showSessionsManagerAct)
            self.__superMenu.addSeparator()

        menu = self.__superMenu.addMenu(self.tr("Save"))
        if self.saveAsAct:
            menu.addAction(self.saveAsAct)
        menu.addAction(self.saveVisiblePageScreenAct)

        if self.printPreviewAct or self.printAct or self.printPdfAct:
            menu = self.__superMenu.addMenu(self.tr("Print"))
            if self.printPreviewAct:
                menu.addAction(self.printPreviewAct)
            if self.printAct:
                menu.addAction(self.printAct)
            if self.printPdfAct:
                menu.addAction(self.printPdfAct)

        self.__superMenu.addAction(self.sendPageLinkAct)
        self.__superMenu.addSeparator()
        self.__superMenu.addAction(self.selectAllAct)
        self.__superMenu.addAction(self.findAct)
        self.__superMenu.addSeparator()
        act = self.__superMenu.addAction(
            EricPixmapCache.getIcon("history"), self.tr("Show All History...")
        )
        act.triggered.connect(self.historyMenu.showHistoryDialog)
        self.__superMenu.addAction(self.bookmarksManageAct)
        self.__superMenu.addSeparator()
        self.__superMenu.addAction(self.prefAct)

        menu = self.__superMenu.addMenu(self.tr("Settings"))
        menu.addAction(self.shortcutsAct)
        menu.addAction(self.exportShortcutsAct)
        menu.addAction(self.importShortcutsAct)
        menu.addSeparator()
        menu.addAction(self.acceptedLanguagesAct)
        menu.addAction(self.cookiesAct)
        menu.addAction(self.personalDataAct)
        menu.addAction(self.greaseMonkeyAct)
        menu.addAction(self.featurePermissionAct)
        menu.addSeparator()
        menu.addAction(self.editMessageFilterAct)
        menu.addSeparator()
        menu.addAction(self.searchEnginesAct)
        menu.addSeparator()
        menu.addAction(self.passwordsAct)
        menu.addAction(self.securityKeysAct)
        menu.addAction(self.certificateErrorsAct)
        menu.addSeparator()
        menu.addAction(self.zoomValuesAct)
        menu.addAction(self.manageIconsAct)
        menu.addSeparator()
        menu.addAction(self.adblockAct)
        menu.addSeparator()
        menu.addAction(self.safeBrowsingAct)
        menu.addSeparator()
        menu.addMenu(self.__userAgentMenu)
        menu.addAction(self.userAgentManagerAct)
        menu.addSeparator()
        if WebBrowserWindow._useQtHelp:
            menu.addAction(self.manageQtHelpDocsAct)
            menu.addAction(self.reindexDocumentationAct)
            menu.addSeparator()
        menu.addAction(self.clearPrivateDataAct)
        menu.addAction(self.clearIconsAct)
        menu.aboutToShow.connect(self.__aboutToShowSettingsMenu)

        self.__superMenu.addSeparator()

        menu = self.__superMenu.addMenu(self.tr("&View"))
        menu.addMenu(self.__toolbarsMenu)
        windowsMenu = menu.addMenu(self.tr("&Windows"))
        windowsMenu.addAction(self.showDownloadManagerAct)
        windowsMenu.addAction(self.showJavaScriptConsoleAct)
        windowsMenu.addAction(self.showTabManagerAct)
        windowsMenu.addAction(self.showProtocolHandlerManagerAct)
        if WebBrowserWindow._useQtHelp:
            windowsMenu.addSection(self.tr("QtHelp"))
            windowsMenu.addAction(self.showTocAct)
            windowsMenu.addAction(self.showIndexAct)
            windowsMenu.addAction(self.showSearchAct)
        menu.addSeparator()
        menu.addAction(self.stopAct)
        menu.addAction(self.reloadAct)
        if WebBrowserWindow._useQtHelp:
            menu.addSeparator()
            menu.addAction(self.syncTocAct)
        menu.addSeparator()
        menu.addAction(self.zoomInAct)
        menu.addAction(self.zoomResetAct)
        menu.addAction(self.zoomOutAct)
        menu.addSeparator()
        menu.addMenu(self.__textEncodingMenu)
        menu.addSeparator()
        menu.addAction(self.pageSourceAct)
        menu.addAction(self.fullScreenAct)

        self.__superMenu.addMenu(self.historyMenu)
        self.__superMenu.addMenu(self.bookmarksMenu)

        menu = self.__superMenu.addMenu(self.tr("&Tools"))
        menu.addAction(self.feedsManagerAct)
        menu.addAction(self.siteInfoAct)
        menu.addSeparator()
        menu.addAction(self.synchronizationAct)
        menu.addSeparator()
        vtMenu = menu.addMenu(
            EricPixmapCache.getIcon("virustotal"), self.tr("&VirusTotal")
        )
        vtMenu.addAction(self.virustotalScanCurrentAct)
        vtMenu.addAction(self.virustotalIpReportAct)
        vtMenu.addAction(self.virustotalDomainReportAct)

        self.__superMenu.addSeparator()
        self.__superMenu.addAction(self.aboutAct)
        self.__superMenu.addAction(self.aboutQtAct)
        self.__superMenu.addSeparator()
        self.__superMenu.addAction(self.exitAct)

        self.__navigationBar.superMenuButton().setMenu(self.__superMenu)

    def __initToolbars(self):
        """
        Private method to create the toolbars.
        """
        filetb = self.addToolBar(self.tr("File"))
        filetb.setObjectName("FileToolBar")
        filetb.addAction(self.newTabAct)
        filetb.addAction(self.newAct)
        filetb.addAction(self.newPrivateAct)
        filetb.addAction(self.openAct)
        filetb.addAction(self.openTabAct)
        filetb.addSeparator()
        if self.saveAsAct is not None:
            filetb.addAction(self.saveAsAct)
        filetb.addAction(self.saveVisiblePageScreenAct)
        filetb.addSeparator()
        if self.printPreviewAct:
            filetb.addAction(self.printPreviewAct)
        if self.printAct:
            filetb.addAction(self.printAct)
        if self.printPdfAct:
            filetb.addAction(self.printPdfAct)
        if self.printPreviewAct or self.printAct or self.printPdfAct:
            filetb.addSeparator()
        filetb.addAction(self.closeAct)
        filetb.addAction(self.exitAct)
        self.__toolbars["file"] = (filetb.windowTitle(), filetb)

        edittb = self.addToolBar(self.tr("Edit"))
        edittb.setObjectName("EditToolBar")
        edittb.addAction(self.undoAct)
        edittb.addAction(self.redoAct)
        edittb.addSeparator()
        edittb.addAction(self.copyAct)
        edittb.addAction(self.cutAct)
        edittb.addAction(self.pasteAct)
        edittb.addSeparator()
        edittb.addAction(self.selectAllAct)
        self.__toolbars["edit"] = (edittb.windowTitle(), edittb)

        viewtb = self.addToolBar(self.tr("View"))
        viewtb.setObjectName("ViewToolBar")
        viewtb.addAction(self.zoomInAct)
        viewtb.addAction(self.zoomResetAct)
        viewtb.addAction(self.zoomOutAct)
        viewtb.addSeparator()
        viewtb.addAction(self.fullScreenAct)
        self.__toolbars["view"] = (viewtb.windowTitle(), viewtb)

        findtb = self.addToolBar(self.tr("Find"))
        findtb.setObjectName("FindToolBar")
        findtb.addAction(self.findAct)
        findtb.addAction(self.findNextAct)
        findtb.addAction(self.findPrevAct)
        self.__toolbars["find"] = (findtb.windowTitle(), findtb)

        if WebBrowserWindow._useQtHelp:
            filtertb = self.addToolBar(self.tr("Filter"))
            filtertb.setObjectName("FilterToolBar")
            self.filterCombo = QComboBox()
            comboWidth = QFontMetrics(QFont()).horizontalAdvance(
                "ComboBoxWithEnoughWidth"
            )
            self.filterCombo.setMinimumWidth(comboWidth)
            filtertb.addWidget(QLabel(self.tr("Filtered by: ")))
            filtertb.addWidget(self.filterCombo)
            self.__helpEngine.setupFinished.connect(self.__setupFilterCombo)
            self.filterCombo.currentIndexChanged.connect(
                self.__filterQtHelpDocumentation
            )
            self.__setupFilterCombo()
            self.__toolbars["filter"] = (filtertb.windowTitle(), filtertb)

        settingstb = self.addToolBar(self.tr("Settings"))
        settingstb.setObjectName("SettingsToolBar")
        settingstb.addAction(self.prefAct)
        settingstb.addAction(self.shortcutsAct)
        settingstb.addAction(self.acceptedLanguagesAct)
        settingstb.addAction(self.cookiesAct)
        settingstb.addAction(self.personalDataAct)
        settingstb.addAction(self.greaseMonkeyAct)
        settingstb.addAction(self.featurePermissionAct)
        self.__toolbars["settings"] = (settingstb.windowTitle(), settingstb)

        toolstb = self.addToolBar(self.tr("Tools"))
        toolstb.setObjectName("ToolsToolBar")
        toolstb.addAction(self.feedsManagerAct)
        toolstb.addAction(self.siteInfoAct)
        toolstb.addSeparator()
        toolstb.addAction(self.synchronizationAct)
        self.__toolbars["tools"] = (toolstb.windowTitle(), toolstb)

        helptb = self.addToolBar(self.tr("Help"))
        helptb.setObjectName("HelpToolBar")
        helptb.addAction(self.whatsThisAct)
        self.__toolbars["help"] = (helptb.windowTitle(), helptb)

        self.addToolBarBreak()
        vttb = self.addToolBar(self.tr("VirusTotal"))
        vttb.setObjectName("VirusTotalToolBar")
        vttb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        vttb.addAction(self.virustotalScanCurrentAct)
        vttb.addAction(self.virustotalIpReportAct)
        vttb.addAction(self.virustotalDomainReportAct)
        self.__toolbars["virustotal"] = (vttb.windowTitle(), vttb)

    @pyqtSlot()
    def __nextTab(self):
        """
        Private slot used to show the next tab.
        """
        fwidget = QApplication.focusWidget()
        while fwidget and not hasattr(fwidget, "nextTab"):
            fwidget = fwidget.parent()
        if fwidget:
            fwidget.nextTab()

    @pyqtSlot()
    def __prevTab(self):
        """
        Private slot used to show the previous tab.
        """
        fwidget = QApplication.focusWidget()
        while fwidget and not hasattr(fwidget, "prevTab"):
            fwidget = fwidget.parent()
        if fwidget:
            fwidget.prevTab()

    @pyqtSlot()
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

    @pyqtSlot()
    def __whatsThis(self):
        """
        Private slot called in to enter Whats This mode.
        """
        QWhatsThis.enterWhatsThisMode()

    def __titleChanged(self, browser, title):
        """
        Private slot called to handle a change of a browser's title.

        @param browser reference to the browser
        @type WebBrowserView
        @param title new title
        @type str
        """
        self.historyManager().updateHistoryEntry(browser.url().toString(), title)

    @pyqtSlot()
    def newTab(self, link=None, addNextTo=None, background=False):
        """
        Public slot called to open a new web browser tab.

        @param link file to be displayed in the new window
        @type str or QUrl
        @param addNextTo reference to the browser to open the tab after
        @type WebBrowserView
        @param background flag indicating to open the tab in the background
        @type bool
        @return reference to the new browser
        @rtype WebBrowserView
        """
        if addNextTo:
            return self.__tabWidget.newBrowserAfter(
                addNextTo, link, background=background
            )
        else:
            return self.__tabWidget.newBrowser(link, background=background)

    @pyqtSlot()
    def newWindow(self, link=None, restoreSession=False):
        """
        Public slot called to open a new web browser window.

        @param link URL to be displayed in the new window
        @type str or QUrl
        @param restoreSession flag indicating a restore session action
        @type bool
        @return reference to the new window
        @rtype WebBrowserWindow
        """
        if link is None:
            linkName = ""
        elif isinstance(link, QUrl):
            linkName = link.toString()
        else:
            linkName = link
        h = WebBrowserWindow(
            linkName,
            ".",
            self.parent(),
            "webbrowser",
            private=self.isPrivate(),
            restoreSession=restoreSession,
        )
        h.show()

        self.webBrowserWindowOpened.emit(h)

        return h

    @pyqtSlot()
    def newPrivateWindow(self, link=None):
        """
        Public slot called to open a new private web browser window.

        @param link URL to be displayed in the new window
        @type str or QUrl
        """
        if link is None:
            linkName = ""
        elif isinstance(link, QUrl):
            linkName = link.toString()
        else:
            linkName = link

        applPath = os.path.join(getConfig("ericDir"), "eric7_browser.py")
        args = []
        args.append(applPath)
        args.append("--config={0}".format(EricUtilities.getConfigDir()))
        if self.__settingsDir:
            args.append("--settings={0}".format(self.__settingsDir))
        args.append("--private")
        if linkName:
            args.append(linkName)

        if not os.path.isfile(applPath) or not QProcess.startDetached(
            PythonUtilities.getPythonExecutable(), args
        ):
            EricMessageBox.critical(
                self,
                self.tr("New Private Window"),
                self.tr(
                    "<p>Could not start the process.<br>"
                    "Ensure that it is available as <b>{0}</b>.</p>"
                ).format(applPath),
                self.tr("OK"),
            )

    @pyqtSlot()
    def __openFile(self):
        """
        Private slot called to open a file.
        """
        fn = EricFileDialog.getOpenFileName(
            self,
            self.tr("Open File"),
            "",
            self.tr(
                "HTML Files (*.html *.htm *.mhtml *.mht);;"
                "PDF Files (*.pdf);;"
                "CHM Files (*.chm);;"
                "All Files (*)"
            ),
        )
        if fn:
            if OSUtilities.isWindowsPlatform():
                url = "file:///" + FileSystemUtilities.fromNativeSeparators(fn)
            else:
                url = "file://" + fn
            self.currentBrowser().setSource(QUrl(url))

    @pyqtSlot()
    def __openFileNewTab(self):
        """
        Private slot called to open a file in a new tab.
        """
        fn = EricFileDialog.getOpenFileName(
            self,
            self.tr("Open File"),
            "",
            self.tr(
                "HTML Files (*.html *.htm *.mhtml *.mht);;"
                "PDF Files (*.pdf);;"
                "CHM Files (*.chm);;"
                "All Files (*)"
            ),
        )
        if fn:
            if OSUtilities.isWindowsPlatform():
                url = "file:///" + FileSystemUtilities.fromNativeSeparators(fn)
            else:
                url = "file://" + fn
            self.newTab(url)

    @pyqtSlot()
    def __savePageAs(self):
        """
        Private slot to save the current page.
        """
        browser = self.currentBrowser()
        if browser is not None:
            browser.saveAs()

    @pyqtSlot()
    def __saveVisiblePageScreen(self):
        """
        Private slot to save the visible part of the current page as a screen
        shot.
        """
        from .PageScreenDialog import PageScreenDialog

        self.__pageScreen = PageScreenDialog(self.currentBrowser())
        self.__pageScreen.show()

    @pyqtSlot()
    def __about(self):
        """
        Private slot to show the about information.
        """
        (
            chromiumVersion,
            chromiumSecurityVersion,
            webengineVersion,
        ) = WebBrowserTools.getWebEngineVersions()
        if chromiumSecurityVersion:
            EricMessageBox.about(
                self,
                self.tr("eric Web Browser"),
                self.tr(
                    """<b>eric Web Browser - {0}</b>"""
                    """<p>The eric Web Browser is a combined help file and"""
                    """ HTML browser. It is part of the eric development"""
                    """ toolset.</p>"""
                    """<p>It is based on QtWebEngine {1} and Chromium {2}"""
                    """ with Security Patches {3}.</p>"""
                ).format(
                    Version, webengineVersion, chromiumVersion, chromiumSecurityVersion
                ),
            )
        else:
            EricMessageBox.about(
                self,
                self.tr("eric Web Browser"),
                self.tr(
                    """<b>eric Web Browser - {0}</b>"""
                    """<p>The eric Web Browser is a combined help file and"""
                    """ HTML browser. It is part of the eric development"""
                    """ toolset.</p>"""
                    """<p>It is based on QtWebEngine {1} and Chromium {2}."""
                    """</p>"""
                ).format(Version, webengineVersion, chromiumVersion),
            )

    @pyqtSlot()
    def __aboutQt(self):
        """
        Private slot to show info about Qt.
        """
        EricMessageBox.aboutQt(self, self.tr("eric Web Browser"))

    @pyqtSlot(bool)
    def setBackwardAvailable(self, b):
        """
        Public slot called when backward references are available.

        @param b flag indicating availability of the backwards action
        @type bool
        """
        self.backAct.setEnabled(b)
        self.__navigationBar.backButton().setEnabled(b)

    @pyqtSlot(bool)
    def setForwardAvailable(self, b):
        """
        Public slot called when forward references are available.

        @param b flag indicating the availability of the forwards action
        @type bool
        """
        self.forwardAct.setEnabled(b)
        self.__navigationBar.forwardButton().setEnabled(b)

    @pyqtSlot(bool)
    def setLoadingActions(self, b):
        """
        Public slot to set the loading dependent actions.

        @param b flag indicating the loading state to consider
        @type bool
        """
        self.reloadAct.setEnabled(not b)
        self.stopAct.setEnabled(b)

        self.__navigationBar.reloadStopButton().setLoading(b)

    @pyqtSlot()
    def __addBookmark(self):
        """
        Private slot called to add the displayed file to the bookmarks.
        """
        from .WebBrowserPage import WebBrowserPage

        view = self.currentBrowser()
        view.addBookmark()
        urlStr = bytes(view.url().toEncoded()).decode()
        title = view.title()

        script = Scripts.getAllMetaAttributes()
        view.page().runJavaScript(
            script,
            WebBrowserPage.SafeJsWorld,
            lambda res: self.__addBookmarkCallback(urlStr, title, res),
        )

    def __addBookmarkCallback(self, url, title, res):
        """
        Private callback method of __addBookmark().

        @param url URL for the bookmark
        @type str
        @param title title for the bookmark
        @type str
        @param res result of the JavaScript
        @type list
        """
        from .Bookmarks.AddBookmarkDialog import AddBookmarkDialog

        description = ""
        for meta in res:
            if meta["name"] == "description":
                description = meta["content"]

        dlg = AddBookmarkDialog(parent=self)
        dlg.setUrl(url)
        dlg.setTitle(title)
        dlg.setDescription(description)
        menu = self.bookmarksManager().menu()
        idx = self.bookmarksManager().bookmarksModel().nodeIndex(menu)
        dlg.setCurrentIndex(idx)
        dlg.exec()

    @pyqtSlot()
    def __addBookmarkFolder(self):
        """
        Private slot to add a new bookmarks folder.
        """
        from .Bookmarks.AddBookmarkDialog import AddBookmarkDialog

        dlg = AddBookmarkDialog(parent=self)
        menu = self.bookmarksManager().menu()
        idx = self.bookmarksManager().bookmarksModel().nodeIndex(menu)
        dlg.setCurrentIndex(idx)
        dlg.setFolder(True)
        dlg.exec()

    @pyqtSlot()
    def __showBookmarksDialog(self):
        """
        Private slot to show the bookmarks dialog.
        """
        from .Bookmarks.BookmarksDialog import BookmarksDialog

        self.__bookmarksDialog = BookmarksDialog(self)
        self.__bookmarksDialog.openUrl.connect(self.openUrl)
        self.__bookmarksDialog.newTab.connect(self.openUrlNewTab)
        self.__bookmarksDialog.newBackgroundTab.connect(self.openUrlNewBackgroundTab)
        self.__bookmarksDialog.show()

    @pyqtSlot()
    def bookmarkAll(self):
        """
        Public slot to bookmark all open tabs.
        """
        from .Bookmarks.AddBookmarkDialog import AddBookmarkDialog
        from .WebBrowserPage import WebBrowserPage

        dlg = AddBookmarkDialog(parent=self)
        dlg.setFolder(True)
        dlg.setTitle(self.tr("Saved Tabs"))
        dlg.exec()

        folder = dlg.addedNode()
        if folder is None:
            return

        for view in self.__tabWidget.browsers():
            urlStr = bytes(view.url().toEncoded()).decode()
            title = view.title()

            script = Scripts.getAllMetaAttributes()
            view.page().runJavaScript(
                script,
                WebBrowserPage.SafeJsWorld,
                functools.partial(self.__bookmarkAllCallback, folder, urlStr, title),
            )

    def __bookmarkAllCallback(self, folder, url, title, res):
        """
        Private callback method of __addBookmark().

        @param folder reference to the bookmarks folder
        @type BookmarkNode
        @param url URL for the bookmark
        @type str
        @param title title for the bookmark
        @type str
        @param res result of the JavaScript
        @type list
        """
        from .Bookmarks.BookmarkNode import BookmarkNode, BookmarkNodeType

        description = ""
        for meta in res:
            if meta["name"] == "description":
                description = meta["content"]

        bookmark = BookmarkNode(BookmarkNodeType.Bookmark)
        bookmark.url = url
        bookmark.title = title
        bookmark.desc = description

        self.bookmarksManager().addBookmark(folder, bookmark)

    @pyqtSlot()
    def __find(self):
        """
        Private slot to handle the find action.

        It opens the search dialog in order to perform the various
        search actions and to collect the various search info.
        """
        self.__searchWidget.showFind()

    def forceClose(self):
        """
        Public method to force closing the window.
        """
        self.__forcedClose = True
        self.close()

    def closeEvent(self, e):
        """
        Protected event handler for the close event.

        @param e the close event
            <br />This event is simply accepted after the history has been
            saved and all window references have been deleted.
        @type QCloseEvent
        """
        res = self.__shutdownWindow()

        if res:
            e.accept()
            self.webBrowserWindowClosed.emit(self)
        else:
            e.ignore()

    def isClosing(self):
        """
        Public method to test, if the window is closing.

        @return flag indicating that the window is closing
        @rtype bool
        """
        return self.__isClosing

    def __shutdownWindow(self):
        """
        Private method to shut down a web browser window.

        @return flag indicating successful shutdown
        @rtype bool
        """
        if (
            not WebBrowserWindow._performingShutdown
            and not self.__forcedClose
            and not self.__tabWidget.shallShutDown()
        ):
            return False

        self.__isClosing = True

        if (
            not WebBrowserWindow._performingShutdown
            and len(WebBrowserWindow.BrowserWindows) == 1
            and not WebBrowserWindow.isPrivate()
        ):
            # shut down the session manager in case the last window is
            # about to be closed
            self.sessionManager().shutdown()

        self.__bookmarksToolBar.setModel(None)

        self.__virusTotal.close()

        self.__navigationBar.searchEdit().openSearchManager().close()

        if WebBrowserWindow._useQtHelp:
            self.__searchEngine.cancelIndexing()
            self.__searchEngine.cancelSearching()

            if self.__helpInstaller:
                self.__helpInstaller.stop()

        self.__navigationBar.searchEdit().saveSearches()

        self.__tabWidget.closeAllBrowsers(shutdown=True)

        state = self.saveState()
        Preferences.setWebBrowser("WebBrowserState", state)

        if Preferences.getWebBrowser("SaveGeometry"):
            if not self.isFullScreen():
                Preferences.setGeometry("WebBrowserGeometry", self.saveGeometry())
        else:
            Preferences.setGeometry("WebBrowserGeometry", QByteArray())

        with contextlib.suppress(ValueError):
            browserIndex = WebBrowserWindow.BrowserWindows.index(self)
            if len(WebBrowserWindow.BrowserWindows) and browserIndex == 0:
                if len(WebBrowserWindow.BrowserWindows) > 1:
                    # first window will be deleted
                    QDesktopServices.setUrlHandler(
                        "http", WebBrowserWindow.BrowserWindows[1].urlHandler
                    )
                    QDesktopServices.setUrlHandler(
                        "https", WebBrowserWindow.BrowserWindows[1].urlHandler
                    )
                else:
                    QDesktopServices.unsetUrlHandler("http")
                    QDesktopServices.unsetUrlHandler("https")
            if len(WebBrowserWindow.BrowserWindows) > 0:
                del WebBrowserWindow.BrowserWindows[browserIndex]

        Preferences.syncPreferences()
        if (
            not WebBrowserWindow._performingShutdown
            and len(WebBrowserWindow.BrowserWindows) == 0
        ):
            # shut down the browser in case the last window was
            # simply closed
            self.shutdown()

        return True

    def __shallShutDown(self):
        """
        Private method to check, if the application should be shut down.

        @return flag indicating a shut down
        @rtype bool
        """
        if Preferences.getWebBrowser("WarnOnMultipleClose"):
            windowCount = len(WebBrowserWindow.BrowserWindows)
            tabCount = 0
            for browser in WebBrowserWindow.BrowserWindows:
                tabCount += browser.tabWidget().count()

            if windowCount > 1 or tabCount > 1:
                mb = EricMessageBox.EricMessageBox(
                    EricMessageBox.Information,
                    self.tr("Are you sure you want to close the web browser?"),
                    self.tr(
                        """Are you sure you want to close the web"""
                        """ browser?\n"""
                        """You have {0} windows with {1} tabs open."""
                    ).format(windowCount, tabCount),
                    modal=True,
                    parent=self,
                )
                quitButton = mb.addButton(self.tr("&Quit"), EricMessageBox.AcceptRole)
                quitButton.setIcon(EricPixmapCache.getIcon("exit"))
                mb.addButton(EricMessageBox.Cancel)
                mb.exec()
                return mb.clickedButton() == quitButton

        return True

    def shutdown(self):
        """
        Public method to shut down the web browser.

        @return flag indicating successful shutdown
        @rtype bool
        """
        if not self.__shallShutDown():
            return False

        if (
            WebBrowserWindow._downloadManager is not None
            and not self.downloadManager().allowQuit()
        ):
            return False

        WebBrowserWindow._performingShutdown = True

        if not WebBrowserWindow.isPrivate():
            self.sessionManager().shutdown()

        if WebBrowserWindow._downloadManager is not None:
            self.downloadManager().shutdown()

        self.cookieJar().close()

        self.bookmarksManager().close()

        self.historyManager().close()

        self.passwordManager().close()

        self.adBlockManager().close()

        self.userAgentsManager().close()

        self.speedDial().close()

        self.syncManager().close()

        ZoomManager.instance().close()

        WebIconProvider.instance().close()

        if len(WebBrowserWindow.BrowserWindows) == 1:
            # it is the last window
            self.tabManager().close()

        self.networkManager().shutdown()

        if WebBrowserWindow._safeBrowsingManager:
            self.safeBrowsingManager().close()

        if self.SAServer is not None:
            self.SAServer.shutdown()

        for browser in WebBrowserWindow.BrowserWindows:
            if browser != self:
                browser.close()
        self.close()

        return True

    @pyqtSlot()
    def __backward(self):
        """
        Private slot called to handle the backward action.
        """
        self.currentBrowser().backward()

    @pyqtSlot()
    def __forward(self):
        """
        Private slot called to handle the forward action.
        """
        self.currentBrowser().forward()

    @pyqtSlot()
    def __home(self):
        """
        Private slot called to handle the home action.
        """
        self.currentBrowser().home()

    @pyqtSlot()
    def __reload(self):
        """
        Private slot called to handle the reload action.
        """
        self.currentBrowser().reloadBypassingCache()

    @pyqtSlot()
    def __stopLoading(self):
        """
        Private slot called to handle loading of the current page.
        """
        self.currentBrowser().stop()

    @pyqtSlot(int)
    def __zoomValueChanged(self, value):
        """
        Private slot to handle value changes of the zoom widget.

        @param value zoom value
        @type int
        """
        self.currentBrowser().setZoomValue(value)

    @pyqtSlot()
    def __zoomIn(self):
        """
        Private slot called to handle the zoom in action.
        """
        self.currentBrowser().zoomIn()
        self.__zoomWidget.setValue(self.currentBrowser().zoomValue())

    @pyqtSlot()
    def __zoomOut(self):
        """
        Private slot called to handle the zoom out action.
        """
        self.currentBrowser().zoomOut()
        self.__zoomWidget.setValue(self.currentBrowser().zoomValue())

    @pyqtSlot()
    def __zoomReset(self):
        """
        Private slot called to handle the zoom reset action.
        """
        self.currentBrowser().zoomReset()
        self.__zoomWidget.setValue(self.currentBrowser().zoomValue())

    @pyqtSlot()
    def toggleFullScreen(self):
        """
        Public slot called to toggle the full screen mode.
        """
        if self.__htmlFullScreen:
            self.currentBrowser().triggerPageAction(
                QWebEnginePage.WebAction.ExitFullScreen
            )
            return

        if self.isFullScreen():
            # switch back to normal
            self.showNormal()
        else:
            # switch to full screen
            self.showFullScreen()

    def enterHtmlFullScreen(self):
        """
        Public method to switch to full screen initiated by the
        HTML page.
        """
        self.showFullScreen()
        self.__htmlFullScreen = True

    def isFullScreenNavigationVisible(self):
        """
        Public method to check, if full screen navigation is active.

        @return flag indicating visibility of the navigation container in full
            screen mode
        @rtype bool
        """
        return self.isFullScreen() and self.__navigationContainer.isVisible()

    @pyqtSlot()
    def showFullScreenNavigation(self):
        """
        Public slot to show full screen navigation.
        """
        if self.__htmlFullScreen:
            return

        if self.__hideNavigationTimer.isActive():
            self.__hideNavigationTimer.stop()

        self.__navigationContainer.show()
        self.__tabWidget.tabBar().show()

    @pyqtSlot()
    def hideFullScreenNavigation(self):
        """
        Public slot to hide full screen navigation.
        """
        if not self.__hideNavigationTimer.isActive():
            self.__hideNavigationTimer.start()

    @pyqtSlot()
    def __hideNavigation(self):
        """
        Private slot to hide full screen navigation by timer.
        """
        browser = self.currentBrowser()
        mouseInBrowser = browser and browser.underMouse()

        if self.isFullScreen() and mouseInBrowser:
            self.__navigationContainer.hide()
            self.__tabWidget.tabBar().hide()

    @pyqtSlot()
    def __copy(self):
        """
        Private slot called to handle the copy action.
        """
        self.currentBrowser().copy()

    @pyqtSlot()
    def __cut(self):
        """
        Private slot called to handle the cut action.
        """
        self.currentBrowser().cut()

    @pyqtSlot()
    def __paste(self):
        """
        Private slot called to handle the paste action.
        """
        self.currentBrowser().paste()

    @pyqtSlot()
    def __undo(self):
        """
        Private slot to handle the undo action.
        """
        self.currentBrowser().undo()

    @pyqtSlot()
    def __redo(self):
        """
        Private slot to handle the redo action.
        """
        self.currentBrowser().redo()

    @pyqtSlot()
    def __selectAll(self):
        """
        Private slot to handle the select all action.
        """
        self.currentBrowser().selectAll()

    @pyqtSlot()
    def __unselect(self):
        """
        Private slot to clear the selection of the current browser.
        """
        self.currentBrowser().unselect()

    @classmethod
    def isPrivate(cls):
        """
        Class method to check the private browsing mode.

        @return flag indicating private browsing mode
        @rtype bool
        """
        return cls._isPrivate

    def closeCurrentBrowser(self):
        """
        Public method to close the current web browser.
        """
        self.__tabWidget.closeBrowser()

    def closeBrowser(self, browser):
        """
        Public method to close the given browser.

        @param browser reference to the web browser view to be closed
        @type WebBrowserView
        """
        self.__tabWidget.closeBrowserView(browser)

    def currentBrowser(self):
        """
        Public method to get a reference to the current web browser.

        @return reference to the current help browser
        @rtype WebBrowserView
        """
        return self.__tabWidget.currentBrowser()

    def browserAt(self, index):
        """
        Public method to get a reference to the web browser with the given
        index.

        @param index index of the browser to get
        @type int
        @return reference to the indexed web browser
        @rtype WebBrowserView
        """
        return self.__tabWidget.browserAt(index)

    def browsers(self):
        """
        Public method to get a list of references to all web browsers.

        @return list of references to web browsers
        @rtype list of WebBrowserView
        """
        return self.__tabWidget.browsers()

    @pyqtSlot(int)
    def __currentChanged(self, index):
        """
        Private slot to handle the currentChanged signal.

        @param index index of the current tab
        @type int
        """
        if index > -1:
            cb = self.currentBrowser()
            if cb is not None:
                self.setForwardAvailable(cb.isForwardAvailable())
                self.setBackwardAvailable(cb.isBackwardAvailable())
                self.setLoadingActions(cb.isLoading())

                # set value of zoom widget
                self.__zoomWidget.setValue(cb.zoomValue())

    @pyqtSlot()
    def __showPreferences(self):
        """
        Private slot to set the preferences.
        """
        from eric7.Preferences.ConfigurationDialog import (
            ConfigurationDialog,
            ConfigurationMode,
        )

        dlg = ConfigurationDialog(
            parent=self,
            name="Configuration",
            modal=True,
            fromEric=False,
            displayMode=ConfigurationMode.WEBBROWSERMODE,
        )
        dlg.preferencesChanged.connect(self.preferencesChanged)
        dlg.mainPasswordChanged.connect(
            lambda old, new: self.mainPasswordChanged(old, new, local=True)
        )
        dlg.show()
        if self.__lastConfigurationPageName:
            dlg.showConfigurationPageByName(self.__lastConfigurationPageName)
        else:
            dlg.showConfigurationPageByName("empty")
        dlg.exec()
        QApplication.processEvents()
        if dlg.result() == QDialog.DialogCode.Accepted:
            dlg.setPreferences()
            Preferences.syncPreferences()
            self.preferencesChanged()
        self.__lastConfigurationPageName = dlg.getConfigurationPageName()

    @pyqtSlot()
    def preferencesChanged(self):
        """
        Public slot to handle a change of preferences.
        """
        self.setStyle(
            styleName=Preferences.getUI("Style"),
            styleSheetFile=Preferences.getUI("StyleSheet"),
            itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
        )

        self.__initWebEngineSettings()

        self.networkManager().preferencesChanged()

        self.historyManager().preferencesChanged()

        self.__tabWidget.preferencesChanged()

        self.__navigationBar.searchEdit().preferencesChanged()

        self.autoScroller().preferencesChanged()

        profile = self.webProfile()
        if not self.isPrivate():
            if Preferences.getWebBrowser("DiskCacheEnabled"):
                profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)
                profile.setHttpCacheMaximumSize(
                    Preferences.getWebBrowser("DiskCacheSize") * 1024 * 1024
                )
            else:
                profile.setHttpCacheType(
                    QWebEngineProfile.HttpCacheType.MemoryHttpCache
                )
                profile.setHttpCacheMaximumSize(0)

        with contextlib.suppress(AttributeError):
            profile.setSpellCheckEnabled(Preferences.getWebBrowser("SpellCheckEnabled"))
            profile.setSpellCheckLanguages(
                Preferences.getWebBrowser("SpellCheckLanguages")
            )

        self.__virusTotal.preferencesChanged()
        if (
            not Preferences.getWebBrowser("VirusTotalEnabled")
            or Preferences.getWebBrowser("VirusTotalServiceKey") == ""
        ):
            self.virustotalScanCurrentAct.setEnabled(False)
            self.virustotalIpReportAct.setEnabled(False)
            self.virustotalDomainReportAct.setEnabled(False)
        else:
            self.virustotalScanCurrentAct.setEnabled(True)
            self.virustotalIpReportAct.setEnabled(True)
            self.virustotalDomainReportAct.setEnabled(True)

        self.__javaScriptIcon.preferencesChanged()

        if not WebBrowserWindow.isPrivate():
            self.sessionManager().preferencesChanged()

    def mainPasswordChanged(self, oldPassword, newPassword, local=False):
        """
        Public slot to handle the change of the main password.

        @param oldPassword current main password
        @type str
        @param newPassword new main password
        @type str
        @param local flag indicating being called from the local configuration
            dialog
        @type bool
        """
        self.passwordManager().mainPasswordChanged(oldPassword, newPassword)
        if local:
            # we were called from our local configuration dialog
            Preferences.convertPasswords(oldPassword, newPassword)
            EricUtilities.crypto.changeRememberedMain(newPassword)

    @pyqtSlot()
    def __showAcceptedLanguages(self):
        """
        Private slot to configure the accepted languages for web pages.
        """
        from .WebBrowserLanguagesDialog import WebBrowserLanguagesDialog

        dlg = WebBrowserLanguagesDialog(parent=self)
        dlg.exec()
        self.networkManager().languagesChanged()

    @pyqtSlot()
    def __showCookiesConfiguration(self):
        """
        Private slot to configure the cookies handling.
        """
        from .CookieJar.CookiesConfigurationDialog import CookiesConfigurationDialog

        dlg = CookiesConfigurationDialog(parent=self)
        dlg.exec()

    @classmethod
    def setUseQtHelp(cls, use):
        """
        Class method to set the QtHelp usage.

        @param use flag indicating usage
        @type bool
        """
        if use:
            cls._useQtHelp = use and QTHELP_AVAILABLE
        else:
            cls._useQtHelp = False

    @classmethod
    def helpEngine(cls):
        """
        Class method to get a reference to the help engine.

        @return reference to the help engine
        @rtype QHelpEngine
        """
        if cls._useQtHelp:
            if cls._helpEngine is None:
                cls._helpEngine = QHelpEngine(
                    WebBrowserWindow.getQtHelpCollectionFileName()
                )
                cls._helpEngine.setUsesFilterEngine(True)
            return cls._helpEngine
        else:
            return None

    @classmethod
    def getQtHelpCollectionFileName(cls):
        """
        Class method to determine the name of the QtHelp collection file.

        @return path of the QtHelp collection file
        @rtype str
        """
        qthelpDir = os.path.join(EricUtilities.getConfigDir(), "qthelp")
        if not os.path.exists(qthelpDir):
            os.makedirs(qthelpDir)
        return os.path.join(qthelpDir, "eric7help.qhc")

    @classmethod
    def networkManager(cls):
        """
        Class method to get a reference to the network manager object.

        @return reference to the network access manager
        @rtype NetworkManager
        """
        from .Network.NetworkManager import NetworkManager

        if cls._networkManager is None:
            cls._networkManager = NetworkManager(cls.helpEngine())

        return cls._networkManager

    @classmethod
    def cookieJar(cls):
        """
        Class method to get a reference to the cookie jar.

        @return reference to the cookie jar
        @rtype CookieJar
        """
        from .CookieJar.CookieJar import CookieJar

        if cls._cookieJar is None:
            cls._cookieJar = CookieJar()

        return cls._cookieJar

    @pyqtSlot()
    def __clearIconsDatabase(self):
        """
        Private slot to clear the favicons databse.
        """
        WebIconProvider.instance().clear()

    @pyqtSlot()
    def __showWebIconsDialog(self):
        """
        Private slot to show a dialog to manage the favicons database.
        """
        WebIconProvider.instance().showWebIconDialog(self)

    @pyqtSlot(QUrl)
    def urlHandler(self, url):
        """
        Public slot used as desktop URL handler.

        @param url URL to be handled
        @type QUrl
        """
        self.__linkActivated(url)

    @pyqtSlot(QUrl)
    def __linkActivated(self, url):
        """
        Private slot to handle the selection of a link.

        @param url URL to be shown
        @type QUrl
        """
        if not self.__activating:
            self.__activating = True
            cb = self.currentBrowser()
            if cb is None:
                self.newTab(url)
            else:
                cb.setUrl(url)
            self.__activating = False

    @pyqtSlot()
    def __activateCurrentBrowser(self):
        """
        Private slot to activate the current browser.
        """
        self.currentBrowser().setFocus()

    @pyqtSlot()
    def __syncTOC(self):
        """
        Private slot to synchronize the TOC with the currently shown page.
        """
        if WebBrowserWindow._useQtHelp:
            with EricOverrideCursor():
                url = self.currentBrowser().source()
                self.__showTocWindow()
                if not self.__tocWindow.syncToContent(url):
                    self.statusBar().showMessage(
                        self.tr("Could not find any associated content."), 5000
                    )

    def __showTocWindow(self):
        """
        Private method to show the table of contents window.
        """
        if WebBrowserWindow._useQtHelp:
            self.__activateDock(self.__tocWindow)

    def __showIndexWindow(self):
        """
        Private method to show the index window.
        """
        if WebBrowserWindow._useQtHelp:
            self.__activateDock(self.__indexWindow)

    def __showSearchWindow(self):
        """
        Private method to show the search window.
        """
        if WebBrowserWindow._useQtHelp:
            self.__activateDock(self.__searchWindow)

    def __activateDock(self, widget):
        """
        Private method to activate the dock widget of the given widget.

        @param widget reference to the widget to be activated
        @type QWidget
        """
        widget.parent().show()
        widget.parent().raise_()
        widget.setFocus()

    @pyqtSlot()
    def __setupFilterCombo(self):
        """
        Private slot to setup the filter combo box.
        """
        if WebBrowserWindow._useQtHelp:
            activeFilter = self.filterCombo.currentText()
            if not activeFilter:
                activeFilter = self.__helpEngine.filterEngine().activeFilter()
            allFilters = self.__helpEngine.filterEngine().filters()
            self.filterCombo.clear()
            self.filterCombo.addItem(self.tr("Unfiltered"))
            if allFilters:
                self.filterCombo.insertSeparator(1)
                for helpFilter in sorted(allFilters):
                    self.filterCombo.addItem(helpFilter, helpFilter)
            self.filterCombo.setCurrentText(activeFilter)

    @pyqtSlot(int)
    def __filterQtHelpDocumentation(self, index):
        """
        Private slot to filter the QtHelp documentation.

        @param index index of the selected QtHelp documentation filter
        @type int
        """
        if self.__helpEngine:
            helpFilter = self.filterCombo.itemData(index)
            self.__helpEngine.filterEngine().setActiveFilter(helpFilter)

    @pyqtSlot()
    def __manageQtHelpDocumentation(self):
        """
        Private slot to manage the QtHelp documentation database.
        """
        if WebBrowserWindow._useQtHelp:
            from eric7.QtHelpInterface.QtHelpDocumentationConfigurationDialog import (  # noqa: I101
                QtHelpDocumentationConfigurationDialog,
            )

            dlg = QtHelpDocumentationConfigurationDialog(self.__helpEngine, parent=self)
            dlg.exec()

    def getSourceFileList(self):
        """
        Public method to get a list of all opened source files.

        @return dictionary with tab id as key and host/namespace as value
        @rtype dict
        """
        return self.__tabWidget.getSourceFileList()

    @pyqtSlot()
    def __indexingStarted(self):
        """
        Private slot to handle the start of the indexing process.
        """
        if WebBrowserWindow._useQtHelp:
            self.__indexing = True
            if self.__indexingProgress is None:
                self.__indexingProgress = QWidget()
                layout = QHBoxLayout(self.__indexingProgress)
                layout.setContentsMargins(0, 0, 0, 0)
                sizePolicy = QSizePolicy(
                    QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
                )

                label = QLabel(self.tr("Updating search index"))
                label.setSizePolicy(sizePolicy)
                layout.addWidget(label)

                progressBar = QProgressBar()
                progressBar.setRange(0, 0)
                progressBar.setTextVisible(False)
                progressBar.setFixedHeight(16)
                progressBar.setSizePolicy(sizePolicy)
                layout.addWidget(progressBar)

                self.statusBar().insertPermanentWidget(0, self.__indexingProgress)

    @pyqtSlot()
    def __indexingFinished(self):
        """
        Private slot to handle the start of the indexing process.
        """
        if WebBrowserWindow._useQtHelp:
            self.statusBar().removeWidget(self.__indexingProgress)
            self.__indexingProgress = None
            self.__indexing = False

    @pyqtSlot(str)
    def __searchForWord(self, searchWord):
        """
        Private slot to search for a word.

        @param searchWord word to search for
        @type str
        """
        if WebBrowserWindow._useQtHelp and searchWord:
            if self.__indexing:
                # Try again a second later
                QTimer.singleShot(1000, lambda: self.__searchForWord(searchWord))
            else:
                self.__searchDock.show()
                self.__searchDock.raise_()
                self.__searchEngine.search(searchWord)

    def search(self, word):
        """
        Public method to search for a word.

        @param word word to search for
        @type str
        """
        if WebBrowserWindow._useQtHelp:
            self.__searchForWord(word)

    @pyqtSlot()
    def __removeOldDocumentation(self):
        """
        Private slot to remove non-existing documentation from the help engine.
        """
        if WebBrowserWindow._useQtHelp:
            for namespace in self.__helpEngine.registeredDocumentations():
                docFile = self.__helpEngine.documentationFileName(namespace)
                if not os.path.exists(docFile):
                    self.__helpEngine.unregisterDocumentation(namespace)

    @pyqtSlot()
    def __lookForNewDocumentation(self):
        """
        Private slot to look for new documentation to be loaded into the
        help database.
        """
        if WebBrowserWindow._useQtHelp:
            from eric7.QtHelpInterface.HelpDocsInstaller import (  # noqa: I101
                HelpDocsInstaller,
            )

            self.__helpInstaller = HelpDocsInstaller(self.__helpEngine.collectionFile())
            self.__helpInstaller.errorMessage.connect(self.__showInstallationError)
            self.__helpInstaller.docsInstalled.connect(self.__docsInstalled)

            self.statusBar().showMessage(self.tr("Looking for Documentation..."))
            self.__helpInstaller.installDocs()

    @pyqtSlot(str)
    def __showInstallationError(self, message):
        """
        Private slot to show installation errors.

        @param message message to be shown
        @type str
        """
        EricMessageBox.warning(self, self.tr("eric Web Browser"), message)

    @pyqtSlot(bool)
    def __docsInstalled(self, _installed):
        """
        Private slot handling the end of documentation installation.

        @param _installed flag indicating that documents were installed (unused)
        @type bool
        """
        if WebBrowserWindow._useQtHelp:
            self.statusBar().clearMessage()
            self.__helpEngine.setupData()

    @pyqtSlot(str)
    def __warning(self, msg):
        """
        Private slot handling warnings from the help engine.

        @param msg message sent by the help  engine
        @type str
        """
        EricMessageBox.warning(self, self.tr("Help Engine"), msg)

    @pyqtSlot()
    def __aboutToShowSettingsMenu(self):
        """
        Private slot to show the Settings menu.
        """
        self.editMessageFilterAct.setEnabled(EricErrorMessage.messageHandlerInstalled())

    @pyqtSlot()
    def __clearPrivateData(self):
        """
        Private slot to clear the private data.
        """
        from .WebBrowserClearPrivateDataDialog import WebBrowserClearPrivateDataDialog

        dlg = WebBrowserClearPrivateDataDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            # browsing history, search history, favicons, disk cache, cookies,
            # passwords, web databases, downloads, zoom values, SSL error
            # exceptions, website permissions, history period
            (
                history,
                searches,
                favicons,
                cache,
                cookies,
                passwords,
                downloads,
                zoomValues,
                sslExceptions,
                permissions,
                historyPeriod,
            ) = dlg.getData()
            if history:
                self.historyManager().clear(historyPeriod)
                self.__tabWidget.clearClosedTabsList()
                self.webProfile().clearAllVisitedLinks()
            if searches:
                self.__navigationBar.searchEdit().clear()
            if downloads:
                self.downloadManager().cleanup()
                self.downloadManager().hide()
            if favicons:
                self.__clearIconsDatabase()
            if cache:
                try:
                    self.webProfile().clearHttpCache()
                except AttributeError:
                    cachePath = self.webProfile().cachePath()
                    if cachePath:
                        shutil.rmtree(cachePath)
            if cookies:
                self.cookieJar().clear()
                self.webProfile().cookieStore().deleteAllCookies()
            if passwords:
                self.passwordManager().clear()
            if zoomValues:
                ZoomManager.instance().clear()
            if sslExceptions:
                self.networkManager().clearSslExceptions()
            if permissions and QtUtilities.qVersionTuple() >= (6, 8, 0):
                for permission in self.webProfile().listAllPermissions():
                    permission.reset()

    @pyqtSlot()
    def __showEnginesConfigurationDialog(self):
        """
        Private slot to show the search engines configuration dialog.
        """
        from .OpenSearch.OpenSearchDialog import OpenSearchDialog

        dlg = OpenSearchDialog(parent=self)
        dlg.exec()

    def searchEnginesAction(self):
        """
        Public method to get a reference to the search engines configuration
        action.

        @return reference to the search engines configuration action
        @rtype QAction
        """
        return self.searchEnginesAct

    @pyqtSlot()
    def __showPasswordsDialog(self):
        """
        Private slot to show the passwords management dialog.
        """
        from .Passwords.PasswordsDialog import PasswordsDialog

        dlg = PasswordsDialog(parent=self)
        dlg.exec()

    @pyqtSlot()
    def __showSecurityKeysDialog(self):
        """
        Private slot to show a dialog for managing FIDO2 security keys.
        """
        from .WebAuth.Fido2ManagementDialog import Fido2ManagementDialog

        dlg = Fido2ManagementDialog(parent=self)
        dlg.exec()

    @pyqtSlot()
    def __showCertificateErrorsDialog(self):
        """
        Private slot to show the certificate errors management dialog.
        """
        self.networkManager().showSslErrorExceptionsDialog(self)

    @pyqtSlot()
    def __showAdBlockDialog(self):
        """
        Private slot to show the AdBlock configuration dialog.
        """
        self.adBlockManager().showDialog(self)

    @pyqtSlot()
    def __showPersonalInformationDialog(self):
        """
        Private slot to show the Personal Information configuration dialog.
        """
        self.personalInformationManager().showConfigurationDialog(parent=self)

    @pyqtSlot()
    def __showGreaseMonkeyConfigDialog(self):
        """
        Private slot to show the GreaseMonkey scripts configuration dialog.
        """
        self.greaseMonkeyManager().showConfigurationDialog(parent=self)

    @pyqtSlot()
    def __showFeaturePermissionDialog(self):
        """
        Private slot to show the feature permission dialog.
        """
        if QtUtilities.qVersionTuple() >= (6, 8, 0):
            # Qt 6.8+
            from .FeaturePermissions.FeaturePermissionsDialog import (  # noqa: I101
                FeaturePermissionsDialog,
            )

            dlg = FeaturePermissionsDialog(
                self.webProfile().listAllPermissions(), parent=self
            )
            if dlg.exec() == QDialog.DialogCode.Accepted:
                dlg.persistChanges()
        else:
            # Qt <6.8
            self.featurePermissionManager().showFeaturePermissionsDialog(self)

    @pyqtSlot()
    def __showZoomValuesDialog(self):
        """
        Private slot to show the zoom values management dialog.
        """
        from .ZoomManager.ZoomValuesDialog import ZoomValuesDialog

        dlg = ZoomValuesDialog(parent=self)
        dlg.exec()

    @pyqtSlot()
    def __showDownloadsWindow(self):
        """
        Private slot to show the downloads dialog.
        """
        self.downloadManager().show()

    @pyqtSlot()
    def __showPageSource(self):
        """
        Private slot to show the source of the current page in an editor.
        """
        self.currentBrowser().page().toHtml(self.__showPageSourceCallback)

    def __showPageSourceCallback(self, src):
        """
        Private method to show the source of the current page in an editor.

        @param src source of the web page
        @type str
        """
        from eric7.QScintilla.MiniEditor import MiniEditor

        editor = MiniEditor(parent=self)
        editor.setText(src, "Html")
        editor.setLanguage("dummy.html")
        editor.show()

    @pyqtSlot()
    def __toggleJavaScriptConsole(self):
        """
        Private slot to toggle the JavaScript console.
        """
        if self.__javascriptConsoleDock.isVisible():
            self.__javascriptConsoleDock.hide()
        else:
            self.__javascriptConsoleDock.show()

    def javascriptConsole(self):
        """
        Public method to get a reference to the JavaScript console widget.

        @return reference to the JavaScript console
        @rtype WebBrowserJavaScriptConsole
        """
        return self.__javascriptConsole

    @classmethod
    def icon(cls, url):
        """
        Class method to get the icon for an URL.

        @param url URL to get icon for
        @type QUrl
        @return icon for the URL
        @rtype QIcon
        """
        return WebIconProvider.instance().iconForUrl(url)

    @classmethod
    def bookmarksManager(cls):
        """
        Class method to get a reference to the bookmarks manager.

        @return reference to the bookmarks manager
        @rtype BookmarksManager
        """
        from .Bookmarks.BookmarksManager import BookmarksManager

        if cls._bookmarksManager is None:
            cls._bookmarksManager = BookmarksManager()

        return cls._bookmarksManager

    @pyqtSlot(QUrl)
    @pyqtSlot(QUrl, str)
    def openUrl(self, url, title=None):
        """
        Public slot to load a URL in the current tab.

        @param url URL to be opened
        @type QUrl
        @param title title of the bookmark
        @type str
        """
        self.__linkActivated(url)

    @pyqtSlot(QUrl)
    @pyqtSlot(QUrl, str)
    def openUrlNewTab(self, url, title=None):
        """
        Public slot to load a URL in a new tab.

        @param url URL to be opened
        @type QUrl
        @param title title of the bookmark
        @type str
        """
        self.newTab(url)

    @pyqtSlot(QUrl)
    @pyqtSlot(QUrl, str)
    def openUrlNewBackgroundTab(self, url, title=None):
        """
        Public slot to load a URL in a new background tab.

        @param url URL to be opened
        @type QUrl
        @param title title of the bookmark
        @type str
        """
        self.newTab(url, background=True)

    @pyqtSlot(QUrl)
    @pyqtSlot(QUrl, str)
    def openUrlNewWindow(self, url, title=None):
        """
        Public slot to load a URL in a new window.

        @param url URL to be opened
        @type QUrl
        @param title title of the bookmark
        @type str
        """
        self.newWindow(url)

    @pyqtSlot(QUrl)
    @pyqtSlot(QUrl, str)
    def openUrlNewPrivateWindow(self, url, title=None):
        """
        Public slot to load a URL in a new private window.

        @param url URL to be opened
        @type QUrl
        @param title title of the bookmark
        @type str
        """
        self.newPrivateWindow(url)

    @pyqtSlot()
    def __sendPageLink(self):
        """
        Private slot to send the link of the current page via email.
        """
        url = self.currentBrowser().url()
        if not url.isEmpty():
            urlStr = url.toString()
            QDesktopServices.openUrl(QUrl("mailto:?body=" + urlStr))

    @classmethod
    def historyManager(cls):
        """
        Class method to get a reference to the history manager.

        @return reference to the history manager
        @rtype HistoryManager
        """
        from .History.HistoryManager import HistoryManager

        if cls._historyManager is None:
            cls._historyManager = HistoryManager()

        return cls._historyManager

    @classmethod
    def passwordManager(cls):
        """
        Class method to get a reference to the password manager.

        @return reference to the password manager
        @rtype PasswordManager
        """
        from .Passwords.PasswordManager import PasswordManager

        if cls._passwordManager is None:
            cls._passwordManager = PasswordManager()

        return cls._passwordManager

    @classmethod
    def adBlockManager(cls):
        """
        Class method to get a reference to the AdBlock manager.

        @return reference to the AdBlock manager
        @rtype AdBlockManager
        """
        from .AdBlock.AdBlockManager import AdBlockManager

        if cls._adblockManager is None:
            cls._adblockManager = AdBlockManager()

        return cls._adblockManager

    def adBlockIcon(self):
        """
        Public method to get a reference to the AdBlock icon.

        @return reference to the AdBlock icon
        @rtype AdBlockIcon
        """
        return self.__adBlockIcon

    @classmethod
    def downloadManager(cls):
        """
        Class method to get a reference to the download manager.

        @return reference to the download manager
        @rtype DownloadManager
        """
        from .Download.DownloadManager import DownloadManager

        if cls._downloadManager is None:
            cls._downloadManager = DownloadManager()

        return cls._downloadManager

    @classmethod
    def personalInformationManager(cls):
        """
        Class method to get a reference to the personal information manager.

        @return reference to the personal information manager
        @rtype PersonalInformationManager
        """
        from .PersonalInformationManager import PersonalInformationManager

        if cls._personalInformationManager is None:
            cls._personalInformationManager = (
                PersonalInformationManager.PersonalInformationManager()
            )

        return cls._personalInformationManager

    @classmethod
    def greaseMonkeyManager(cls):
        """
        Class method to get a reference to the GreaseMonkey manager.

        @return reference to the GreaseMonkey manager
        @rtype GreaseMonkeyManager
        """
        from .GreaseMonkey.GreaseMonkeyManager import GreaseMonkeyManager

        if cls._greaseMonkeyManager is None:
            cls._greaseMonkeyManager = GreaseMonkeyManager()

        return cls._greaseMonkeyManager

    @classmethod
    def featurePermissionManager(cls):
        """
        Class method to get a reference to the feature permission manager.

        @return reference to the feature permission manager
        @rtype FeaturePermissionManager
        """
        from .FeaturePermissions.FeaturePermissionManager import (
            FeaturePermissionManager,
        )

        if cls._featurePermissionManager is None:
            cls._featurePermissionManager = FeaturePermissionManager()

        return cls._featurePermissionManager

    @classmethod
    def imageSearchEngine(cls):
        """
        Class method to get a reference to the image search engine.

        @return reference to the image finder object
        @rtype ImageSearchEngine
        """
        from .ImageSearch.ImageSearchEngine import ImageSearchEngine

        if cls._imageSearchEngine is None:
            cls._imageSearchEngine = ImageSearchEngine()

        return cls._imageSearchEngine

    @classmethod
    def autoScroller(cls):
        """
        Class method to get a reference to the auto scroller.

        @return reference to the auto scroller object
        @rtype AutoScroller
        """
        from .AutoScroll.AutoScroller import AutoScroller

        if cls._autoScroller is None:
            cls._autoScroller = AutoScroller()

        return cls._autoScroller

    @classmethod
    def tabManager(cls):
        """
        Class method to get a reference to the tab manager widget.

        @return reference to the tab manager widget
        @rtype TabManagerWidget
        """
        from .TabManager.TabManagerWidget import TabManagerWidget

        if cls._tabManager is None:
            cls._tabManager = TabManagerWidget(cls.mainWindow())

            # do the connections
            for window in cls.mainWindows():
                cls._tabManager.mainWindowCreated(window)

            cls._tabManager.delayedRefreshTree()

        return cls._tabManager

    def __showTabManager(self, act):
        """
        Private method to show the tab manager window.

        @param act reference to the act that triggered
        @type QAction
        """
        self.tabManager().raiseTabManager(act)

    @classmethod
    def mainWindow(cls):
        """
        Class method to get a reference to the main window.

        @return reference to the main window
        @rtype WebBrowserWindow
        """
        if cls.BrowserWindows:
            return cls.BrowserWindows[0]
        else:
            return None

    @classmethod
    def mainWindows(cls):
        """
        Class method to get references to all main windows.

        @return references to all main window
        @rtype list of WebBrowserWindow
        """
        return cls.BrowserWindows

    @pyqtSlot()
    def __appFocusChanged(self):
        """
        Private slot to handle a change of the focus.
        """
        focusWindow = ericApp().activeWindow()
        if isinstance(focusWindow, WebBrowserWindow):
            WebBrowserWindow._lastActiveWindow = focusWindow

    @classmethod
    def getWindow(cls):
        """
        Class method to get a reference to the most recent active
        web browser window.

        @return reference to most recent web browser window
        @rtype WebBrowserWindow
        """
        if cls._lastActiveWindow:
            return cls._lastActiveWindow

        return cls.mainWindow()

    def openSearchManager(self):
        """
        Public method to get a reference to the opensearch manager object.

        @return reference to the opensearch manager object
        @rtype OpenSearchManager
        """
        return self.__navigationBar.searchEdit().openSearchManager()

    def __createTextEncodingAction(self, codec, defaultCodec, parentMenu, name=None):
        """
        Private method to create an action for the text encoding menu.

        @param codec name of the codec to create an action for
        @type str
        @param defaultCodec name of the default codec
        @type str
        @param parentMenu reference to the parent menu
        @type QMenu
        @param name name for the action
        @type str
        """
        act = QAction(name, parentMenu) if name else QAction(codec, parentMenu)
        act.setData(codec)
        act.setCheckable(True)
        if defaultCodec == codec:
            act.setChecked(True)

        parentMenu.addAction(act)

    def __createTextEncodingSubmenu(self, title, codecNames, parentMenu):
        """
        Private method to create a text encoding sub menu.

        @param title title of the menu
        @type str
        @param codecNames list of codec names for the menu
        @type list of str
        @param parentMenu reference to the parent menu
        @type QMenu
        """
        if codecNames:
            defaultCodec = self.webSettings().defaultTextEncoding().lower()

            menu = QMenu(title, parentMenu)
            for codec in codecNames:
                self.__createTextEncodingAction(codec, defaultCodec, menu)

            parentMenu.addMenu(menu)

    @pyqtSlot()
    def __aboutToShowTextEncodingMenu(self):
        """
        Private slot to populate the text encoding menu.
        """
        self.__textEncodingMenu.clear()

        defaultTextEncoding = self.webSettings().defaultTextEncoding().lower()
        currentCodec = (
            defaultTextEncoding
            if defaultTextEncoding in Utilities.supportedCodecs
            else ""
        )

        isoCodecs = []
        winCodecs = []
        uniCodecs = []
        cpCodecs = []
        macCodecs = []
        otherCodecs = []

        for codec in sorted(Utilities.supportedCodecs):
            if codec.startswith(("iso-", "latin")):
                isoCodecs.append(codec)
            elif codec.startswith(("windows-")):
                winCodecs.append(codec)
            elif codec.startswith("utf-"):
                uniCodecs.append(codec)
            elif codec.startswith("cp"):
                cpCodecs.append(codec)
            elif codec.startswith("mac-"):
                macCodecs.append(codec)
            else:
                otherCodecs.append(codec)

        self.__createTextEncodingAction(
            "", currentCodec, self.__textEncodingMenu, name=self.tr("System")
        )
        self.__textEncodingMenu.addSeparator()
        self.__createTextEncodingSubmenu(
            self.tr("ISO"), isoCodecs, self.__textEncodingMenu
        )
        self.__createTextEncodingSubmenu(
            self.tr("Unicode"), uniCodecs, self.__textEncodingMenu
        )
        self.__createTextEncodingSubmenu(
            self.tr("Windows"), winCodecs, self.__textEncodingMenu
        )
        self.__createTextEncodingSubmenu(
            self.tr("IBM"), cpCodecs, self.__textEncodingMenu
        )
        self.__createTextEncodingSubmenu(
            self.tr("Apple"), macCodecs, self.__textEncodingMenu
        )
        self.__createTextEncodingSubmenu(
            self.tr("Other"), otherCodecs, self.__textEncodingMenu
        )

    @pyqtSlot(QAction)
    def __setTextEncoding(self, act):
        """
        Private slot to set the selected text encoding as the default for
        this session.

        @param act reference to the selected action
        @type QAction
        """
        codec = act.data()
        if codec == "":
            self.webSettings().setDefaultTextEncoding("")
        else:
            self.webSettings().setDefaultTextEncoding(codec)

    def __populateToolbarsMenu(self, menu):
        """
        Private method to populate the toolbars menu.

        @param menu reference to the menu to be populated
        @type QMenu
        """
        menu.clear()

        act = menu.addAction(self.tr("Menu Bar"))
        act.setCheckable(True)
        act.setChecked(not self.menuBar().isHidden())
        act.setData("menubar")

        act = menu.addAction(self.tr("Bookmarks"))
        act.setCheckable(True)
        act.setChecked(not self.__bookmarksToolBar.isHidden())
        act.setData("bookmarks")

        act = menu.addAction(self.tr("Status Bar"))
        act.setCheckable(True)
        act.setChecked(not self.statusBar().isHidden())
        act.setData("statusbar")

        if Preferences.getWebBrowser("ShowToolbars"):
            menu.addSeparator()
            for name, (text, tb) in sorted(
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
        menu.triggered.connect(self.__TBMenuTriggered)

        self.__populateToolbarsMenu(menu)

        return menu

    @pyqtSlot()
    def __showToolbarsMenu(self):
        """
        Private slot to display the Toolbars menu.
        """
        self.__populateToolbarsMenu(self.__toolbarsMenu)

    def __TBMenuTriggered(self, act):
        """
        Private method to handle the toggle of a toolbar via the Window->
        Toolbars submenu or the toolbars popup menu.

        @param act reference to the action that was triggered
        @type QAction
        """
        name = act.data()
        if name:
            if name == "bookmarks":
                # special handling of bookmarks toolbar
                self.__setBookmarksToolbarVisibility(act.isChecked())

            elif name == "menubar":
                # special treatment of the menu bar
                self.__setMenuBarVisibility(act.isChecked())

            elif name == "statusbar":
                # special treatment of the status bar
                self.__setStatusBarVisible(act.isChecked())

            elif name == "__SHOW__":
                for _text, tb in self.__toolbars.values():
                    tb.show()

            elif name == "__HIDE__":
                for _text, tb in self.__toolbars.values():
                    tb.hide()

            else:
                tb = self.__toolbars[name][1]
                if act.isChecked():
                    tb.show()
                else:
                    tb.hide()

    def __setBookmarksToolbarVisibility(self, visible):
        """
        Private method to set the visibility of the bookmarks toolbar.

        @param visible flag indicating the toolbar visibility
        @type bool
        """
        if visible:
            self.__bookmarksToolBar.show()
        else:
            self.__bookmarksToolBar.hide()

        # save state for next invokation
        Preferences.setWebBrowser("BookmarksToolBarVisible", visible)

    def __setMenuBarVisibility(self, visible):
        """
        Private method to set the visibility of the menu bar.

        @param visible flag indicating the menu bar visibility
        @type bool
        """
        if visible:
            self.menuBar().show()
            self.__navigationBar.superMenuButton().hide()
        else:
            self.menuBar().hide()
            self.__navigationBar.superMenuButton().show()

        Preferences.setWebBrowser("MenuBarVisible", visible)

    def __setStatusBarVisible(self, visible):
        """
        Private method to set the visibility of the status bar.

        @param visible flag indicating the status bar visibility
        @type bool
        """
        self.statusBar().setVisible(visible)

        Preferences.setWebBrowser("StatusBarVisible", visible)

    @classmethod
    def feedsManager(cls):
        """
        Class method to get a reference to the RSS feeds manager.

        @return reference to the RSS feeds manager
        @rtype FeedsManager
        """
        from .Feeds.FeedsManager import FeedsManager

        if cls._feedsManager is None:
            cls._feedsManager = FeedsManager()

        return cls._feedsManager

    @pyqtSlot()
    def __showFeedsManager(self):
        """
        Private slot to show the feeds manager dialog.
        """
        feedsManager = self.feedsManager()
        feedsManager.openUrl.connect(self.openUrl)
        feedsManager.newTab.connect(self.openUrlNewTab)
        feedsManager.newBackgroundTab.connect(self.openUrlNewBackgroundTab)
        feedsManager.newWindow.connect(self.openUrlNewWindow)
        feedsManager.newPrivateWindow.connect(self.openUrlNewPrivateWindow)
        feedsManager.rejected.connect(lambda: self.__feedsManagerClosed(feedsManager))
        feedsManager.show()

    def __feedsManagerClosed(self, feedsManager):
        """
        Private slot to handle closing the feeds manager dialog.

        @param feedsManager reference to the feeds manager object
        @type FeedsManager
        """
        feedsManager.openUrl.disconnect(self.openUrl)
        feedsManager.newTab.disconnect(self.openUrlNewTab)
        feedsManager.newBackgroundTab.disconnect(self.openUrlNewBackgroundTab)
        feedsManager.newWindow.disconnect(self.openUrlNewWindow)
        feedsManager.newPrivateWindow.disconnect(self.openUrlNewPrivateWindow)
        feedsManager.rejected.disconnect()

    @pyqtSlot()
    def __showSiteinfoDialog(self):
        """
        Private slot to show the site info dialog.
        """
        from .SiteInfo.SiteInfoDialog import SiteInfoDialog

        self.__siteinfoDialog = SiteInfoDialog(self.currentBrowser(), self)
        self.__siteinfoDialog.show()

    @classmethod
    def userAgentsManager(cls):
        """
        Class method to get a reference to the user agents manager.

        @return reference to the user agents manager
        @rtype UserAgentManager
        """
        from .UserAgent.UserAgentManager import UserAgentManager

        if cls._userAgentsManager is None:
            cls._userAgentsManager = UserAgentManager()

        return cls._userAgentsManager

    @pyqtSlot()
    def __showUserAgentsDialog(self):
        """
        Private slot to show the user agents management dialog.
        """
        from .UserAgent.UserAgentsDialog import UserAgentsDialog

        dlg = UserAgentsDialog(parent=self)
        dlg.exec()

    @classmethod
    def syncManager(cls):
        """
        Class method to get a reference to the data synchronization manager.

        @return reference to the data synchronization manager
        @rtype SyncManager
        """
        from .Sync.SyncManager import SyncManager

        if cls._syncManager is None:
            cls._syncManager = SyncManager()

        return cls._syncManager

    @pyqtSlot()
    def __showSyncDialog(self):
        """
        Private slot to show the synchronization dialog.
        """
        self.syncManager().showSyncDialog()

    @classmethod
    def speedDial(cls):
        """
        Class method to get a reference to the speed dial.

        @return reference to the speed dial
        @rtype SpeedDial
        """
        from .SpeedDial.SpeedDial import SpeedDial

        if cls._speedDial is None:
            cls._speedDial = SpeedDial()

        return cls._speedDial

    def keyPressEvent(self, evt):
        """
        Protected method to handle key presses.

        @param evt reference to the key press event
        @type QKeyEvent
        """
        number = -1
        key = evt.key()

        if key == Qt.Key.Key_1:
            number = 1
        elif key == Qt.Key.Key_2:
            number = 2
        elif key == Qt.Key.Key_3:
            number = 3
        elif key == Qt.Key.Key_4:
            number = 4
        elif key == Qt.Key.Key_5:
            number = 5
        elif key == Qt.Key.Key_6:
            number = 6
        elif key == Qt.Key.Key_7:
            number = 7
        elif key == Qt.Key.Key_8:
            number = 8
        elif key == Qt.Key.Key_9:
            number = 9
        elif key == Qt.Key.Key_0:
            number = 10

        if number != -1:
            if evt.modifiers() == Qt.KeyboardModifier.AltModifier:
                if number == 10:
                    number = self.__tabWidget.count()
                self.__tabWidget.setCurrentIndex(number - 1)
                return

            if evt.modifiers() == Qt.KeyboardModifier.MetaModifier:
                url = self.speedDial().urlForShortcut(number - 1)
                if url.isValid():
                    self.__linkActivated(url)
                    return

        super().keyPressEvent(evt)

    def event(self, evt):
        """
        Public method handling events.

        @param evt reference to the event
        @type QEvent
        @return flag indicating a handled event
        @rtype bool
        """
        if evt.type() == QEvent.Type.WindowStateChange:
            if not bool(evt.oldState() & Qt.WindowState.WindowFullScreen) and bool(
                self.windowState() & Qt.WindowState.WindowFullScreen
            ):
                # enter full screen mode
                self.__windowStates = evt.oldState()
                self.__toolbarStates = self.saveState()
                self.menuBar().hide()
                self.statusBar().hide()
                self.__searchWidget.hide()
                self.__tabWidget.tabBar().hide()
                if Preferences.getWebBrowser("ShowToolbars"):
                    for _title, toolbar in self.__toolbars.values():
                        if toolbar is not self.__bookmarksToolBar:
                            toolbar.hide()
                self.__navigationBar.exitFullScreenButton().setVisible(True)
                self.__navigationContainer.hide()

            elif bool(evt.oldState() & Qt.WindowState.WindowFullScreen) and not bool(
                self.windowState() & Qt.WindowState.WindowFullScreen
            ):
                # leave full screen mode
                self.setWindowState(self.__windowStates)
                self.__htmlFullScreen = False
                if Preferences.getWebBrowser("MenuBarVisible"):
                    self.menuBar().show()
                if Preferences.getWebBrowser("StatusBarVisible"):
                    self.statusBar().show()
                self.restoreState(self.__toolbarStates)
                self.__tabWidget.tabBar().show()
                self.__navigationBar.exitFullScreenButton().setVisible(False)
                self.__navigationContainer.show()

            if self.__hideNavigationTimer:
                self.__hideNavigationTimer.stop()

        return super().event(evt)

    ###########################################################################
    ## Interface to VirusTotal below                                         ##
    ###########################################################################

    @pyqtSlot()
    def __virusTotalScanCurrentSite(self):
        """
        Private slot to ask VirusTotal for a scan of the URL of the current
        browser.
        """
        cb = self.currentBrowser()
        if cb is not None:
            url = cb.url()
            if url.scheme() in ["http", "https", "ftp"]:
                self.requestVirusTotalScan(url)

    def requestVirusTotalScan(self, url):
        """
        Public method to submit a request to scan an URL by VirusTotal.

        @param url URL to be scanned
        @type QUrl
        """
        self.__virusTotal.submitUrl(url)

    @pyqtSlot(str)
    def __virusTotalSubmitUrlError(self, msg):
        """
        Private slot to handle an URL scan submission error.

        @param msg error message
        @type str
        """
        EricMessageBox.critical(
            self,
            self.tr("VirusTotal Scan"),
            self.tr(
                """<p>The VirusTotal scan could not be"""
                """ scheduled.<p>\n<p>Reason: {0}</p>"""
            ).format(msg),
        )

    @pyqtSlot(str)
    def __virusTotalUrlScanReport(self, url):
        """
        Private slot to initiate the display of the URL scan report page.

        @param url URL of the URL scan report page
        @type str
        """
        self.newTab(url)

    @pyqtSlot(str)
    def __virusTotalFileScanReport(self, url):
        """
        Private slot to initiate the display of the file scan report page.

        @param url URL of the file scan report page
        @type str
        """
        self.newTab(url)

    @pyqtSlot()
    def __virusTotalIpAddressReport(self):
        """
        Private slot to retrieve an IP address report.
        """
        ip, ok = QInputDialog.getText(
            self,
            self.tr("IP Address Report"),
            self.tr("Enter a valid IPv4 address in dotted quad notation:"),
            QLineEdit.EchoMode.Normal,
        )
        if ok and ip:
            if ip.count(".") == 3:
                self.__virusTotal.getIpAddressReport(ip)
            else:
                EricMessageBox.information(
                    self,
                    self.tr("IP Address Report"),
                    self.tr(
                        """The given IP address is not in dotted quad"""
                        """ notation."""
                    ),
                )

    @pyqtSlot()
    def __virusTotalDomainReport(self):
        """
        Private slot to retrieve a domain report.
        """
        domain, ok = QInputDialog.getText(
            self,
            self.tr("Domain Report"),
            self.tr("Enter a valid domain name:"),
            QLineEdit.EchoMode.Normal,
        )
        if ok and domain:
            self.__virusTotal.getDomainReport(domain)

    ###########################################################################
    ## Style sheet handling below                                            ##
    ###########################################################################

    def reloadUserStyleSheet(self):
        """
        Public method to reload the user style sheet.
        """
        styleSheet = Preferences.getWebBrowser("UserStyleSheet")
        self.__setUserStyleSheet(styleSheet)

    def __setUserStyleSheet(self, styleSheetFile):
        """
        Private method to set a user style sheet.

        @param styleSheetFile name of the user style sheet file
        @type str
        """
        from .WebBrowserPage import WebBrowserPage

        name = "_eric_userstylesheet"
        userStyle = ""

        userStyle += WebBrowserTools.readAllFileContents(styleSheetFile).replace(
            "\n", ""
        )

        scripts = self.webProfile().scripts().find(name)
        if scripts:
            self.webProfile().scripts().remove(scripts[0])

        if userStyle:
            script = QWebEngineScript()
            script.setName(name)
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(WebBrowserPage.SafeJsWorld)
            script.setRunsOnSubFrames(True)
            script.setSourceCode(Scripts.setStyleSheet(userStyle))
            self.webProfile().scripts().insert(script)

    ##########################################
    ## Support for desktop notifications below
    ##########################################

    @classmethod
    def showNotification(
        cls, icon, heading, text, kind=NotificationTypes.INFORMATION, timeout=None
    ):
        """
        Class method to show a desktop notification.

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
        from eric7.UI.NotificationWidget import NotificationWidget

        if cls._notification is None:
            cls._notification = NotificationWidget()

        if timeout is None:
            timeout = Preferences.getUI("NotificationTimeout")
        cls._notification.showNotification(
            icon, heading, text, kind=kind, timeout=timeout
        )

    @classmethod
    def __showWebNotification(cls, webNotification):
        """
        Class method to show a notification sent by Chromium.

        @param webNotification notification sent by Chromium
        @type QWebEngineNotification
        """
        cls.showNotification(
            QPixmap.fromImage(webNotification.icon()),
            webNotification.title(),
            webNotification.message(),
            kind=NotificationTypes.OTHER,
            timeout=0,
        )

    ######################################
    ## Support for global status bar below
    ######################################

    @classmethod
    def globalStatusBar(cls):
        """
        Class method to get a reference to a global status bar.

        The global status bar is the status bar of the main window. If
        no such window exists and the web browser was called from the eric IDE,
        the status bar of the IDE is returned.

        @return reference to the global status bar
        @rtype QStatusBar
        """
        if cls.BrowserWindows:
            return cls.BrowserWindows[0].statusBar()
        else:
            return None

    ###################################
    ## Support for download files below
    ###################################

    @classmethod
    def downloadRequested(cls, downloadRequest):
        """
        Class method to handle a download request.

        @param downloadRequest reference to the download data
        @type QWebEngineDownloadRequest
        """
        cls.downloadManager().download(downloadRequest)

    ########################################
    ## Support for web engine profiles below
    ########################################

    @classmethod
    def webProfile(cls, private=False):
        """
        Class method handling the web engine profile.

        @param private flag indicating the privacy mode
        @type bool
        @return reference to the web profile object
        @rtype QWebEngineProfile
        """
        from .WebBrowserPage import WebBrowserPage

        if cls._webProfile is None:
            if private:
                cls._webProfile = QWebEngineProfile.defaultProfile()
            else:
                cls._webProfile = QWebEngineProfile("eric7")
            cls._webProfile.downloadRequested.connect(cls.downloadRequested)

            # add the default user agent string
            userAgent = cls._webProfile.httpUserAgent()
            cls._webProfile.defaultUserAgent = userAgent

            if not private:
                if Preferences.getWebBrowser("DiskCacheEnabled"):
                    cls._webProfile.setHttpCacheType(
                        QWebEngineProfile.HttpCacheType.DiskHttpCache
                    )
                    cls._webProfile.setHttpCacheMaximumSize(
                        Preferences.getWebBrowser("DiskCacheSize") * 1024 * 1024
                    )
                    cls._webProfile.setCachePath(
                        os.path.join(EricUtilities.getConfigDir(), "web_browser")
                    )
                else:
                    cls._webProfile.setHttpCacheType(
                        QWebEngineProfile.HttpCacheType.MemoryHttpCache
                    )
                    cls._webProfile.setHttpCacheMaximumSize(0)
                cls._webProfile.setPersistentStoragePath(
                    os.path.join(
                        EricUtilities.getConfigDir(), "web_browser", "persistentstorage"
                    )
                )
                cls._webProfile.setPersistentCookiesPolicy(
                    QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
                )
                with contextlib.suppress(AttributeError):
                    # Qt 6.5+
                    cls._webProfile.setPushServiceEnabled(
                        Preferences.getWebBrowser("PushServiceEnabled")
                    )
                with contextlib.suppress(AttributeError):
                    # Qt 6.8+
                    cls._webProfile.setPersistentPermissionsPolicy(
                        QWebEngineProfile.PersistentPermissionsPolicy.StoreInMemory
                        if Preferences.getWebBrowser("NoPersistentPermissions")
                        else QWebEngineProfile.PersistentPermissionsPolicy.StoreOnDisk
                    )

            with contextlib.suppress(AttributeError):
                cls._webProfile.setSpellCheckEnabled(
                    Preferences.getWebBrowser("SpellCheckEnabled")
                )
                cls._webProfile.setSpellCheckLanguages(
                    Preferences.getWebBrowser("SpellCheckLanguages")
                )

            # configure notifications
            cls._webProfile.setNotificationPresenter(cls.__showWebNotification)

            # Setup QWebChannel user scripts
            # WebChannel for SafeJsWorld
            script = QWebEngineScript()
            script.setName("_eric_webchannel")
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(WebBrowserPage.SafeJsWorld)
            script.setRunsOnSubFrames(True)
            script.setSourceCode(Scripts.setupWebChannel(script.worldId()))
            cls._webProfile.scripts().insert(script)

            # WebChannel for UnsafeJsWorld
            script2 = QWebEngineScript()
            script2.setName("_eric_webchannel2")
            script2.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script2.setWorldId(WebBrowserPage.UnsafeJsWorld)
            script2.setRunsOnSubFrames(True)
            script2.setSourceCode(Scripts.setupWebChannel(script2.worldId()))
            cls._webProfile.scripts().insert(script2)

            # document.window object addons
            script3 = QWebEngineScript()
            script3.setName("_eric_window_object")
            script3.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script3.setWorldId(WebBrowserPage.UnsafeJsWorld)
            script3.setRunsOnSubFrames(True)
            script3.setSourceCode(Scripts.setupWindowObject())
            cls._webProfile.scripts().insert(script3)

        return cls._webProfile

    @classmethod
    def webSettings(cls):
        """
        Class method to get the web settings of the current profile.

        @return web settings of the current profile
        @rtype QWebEngineSettings
        """
        return cls.webProfile().settings()

    ####################################################
    ## Methods below implement session related functions
    ####################################################

    @classmethod
    def sessionManager(cls):
        """
        Class method to get a reference to the session manager.

        @return reference to the session manager
        @rtype SessionManager
        """
        from .Session.SessionManager import SessionManager

        if cls._sessionManager is None and not cls._isPrivate:
            cls._sessionManager = SessionManager()

        return cls._sessionManager

    @pyqtSlot()
    def __showSessionManagerDialog(self):
        """
        Private slot to show the session manager dialog.
        """
        self.sessionManager().showSessionManagerDialog()

    ##########################################################
    ## Methods below implement safe browsing related functions
    ##########################################################

    @classmethod
    def safeBrowsingManager(cls):
        """
        Class method to get a reference to the safe browsing interface.

        @return reference to the safe browsing manager
        @rtype SafeBrowsingManager
        """
        from .SafeBrowsing.SafeBrowsingManager import SafeBrowsingManager

        if cls._safeBrowsingManager is None:
            cls._safeBrowsingManager = SafeBrowsingManager()

        return cls._safeBrowsingManager

    @pyqtSlot()
    def __showSafeBrowsingDialog(self):
        """
        Private slot to show the safe browsing management dialog.
        """
        self.safeBrowsingManager().showSafeBrowsingDialog()

    #############################################################
    ## Methods below implement protocol handler related functions
    #############################################################

    @classmethod
    def protocolHandlerManager(cls):
        """
        Class method to get a reference to the protocol handler manager.

        @return reference to the protocol handler manager
        @rtype ProtocolHandlerManager
        """
        from .Network.ProtocolHandlerManager import ProtocolHandlerManager

        if cls._protocolHandlerManager is None:
            cls._protocolHandlerManager = ProtocolHandlerManager()

        return cls._protocolHandlerManager

    @pyqtSlot()
    def __showProtocolHandlerManagerDialog(self):
        """
        Private slot to show the protocol handler manager dialog.
        """
        self.protocolHandlerManager().showProtocolHandlerManagerDialog()

    ###############################################################
    ## Methods below implement single application related functions
    ###############################################################

    @pyqtSlot(str)
    def __saLoadUrl(self, urlStr):
        """
        Private slot to load an URL received via the single application
        protocol.

        @param urlStr URL to be loaded
        @type str
        """
        url = QUrl.fromUserInput(urlStr)
        self.__linkActivated(url)

        self.raise_()
        self.activateWindow()

    @pyqtSlot(str)
    def __saNewTab(self, urlStr):
        """
        Private slot to load an URL received via the single application
        protocol in a new tab.

        @param urlStr URL to be loaded
        @type str
        """
        url = QUrl.fromUserInput(urlStr)
        self.newTab(url)

        self.raise_()
        self.activateWindow()

    @pyqtSlot(str)
    def __saSearchWord(self, word):
        """
        Private slot to search for the given word.

        @param word word to be searched for
        @type str
        """
        if WebBrowserWindow._useQtHelp:
            self.__searchForWord(word)

        self.raise_()
        self.activateWindow()

    ######################################################
    ## Methods below implement shortcuts related functions
    ######################################################

    @pyqtSlot()
    def __configShortcuts(self):
        """
        Private slot to configure the keyboard shortcuts.
        """
        if self.__shortcutsDialog is None:
            self.__shortcutsDialog = ShortcutsDialog(self)
        self.__shortcutsDialog.populate(webBrowser=self)
        self.__shortcutsDialog.show()

    @pyqtSlot()
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
            Shortcuts.exportShortcuts(fn, helpViewer=self)

    @pyqtSlot()
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
            Shortcuts.importShortcuts(fn, helpViewer=self)
