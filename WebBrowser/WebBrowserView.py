# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing the web browser using QWebEngineView.
"""

import contextlib
import functools
import os
import pathlib

from PyQt6.QtCore import (
    QByteArray,
    QDataStream,
    QDateTime,
    QEvent,
    QEventLoop,
    QIODevice,
    QMarginsF,
    QPoint,
    QPointF,
    QStandardPaths,
    Qt,
    QTimer,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import (
    QClipboard,
    QCursor,
    QDesktopServices,
    QIcon,
    QPageLayout,
    QPixmap,
)
from PyQt6.QtPrintSupport import (
    QAbstractPrintDialog,
    QPrintDialog,
    QPrinter,
    QPrintPreviewDialog,
)
from PyQt6.QtWebEngineCore import (
    QWebEngineDownloadRequest,
    QWebEnginePage,
    QWebEngineWebAuthUxRequest,
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QDialog, QMenu, QStyle

from eric7 import EricUtilities, Preferences
from eric7.__version__ import VersionOnly
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities
from eric7.UI.Info import Homepage
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow
from eric7.WebBrowser.ZoomManager import ZoomManager

from . import WebInspector
from .Tools import Scripts, WebBrowserTools
from .Tools.WebBrowserTools import getHtmlPage, pixmapToDataUrl
from .Tools.WebIconLoader import WebIconLoader
from .WebBrowserPage import WebBrowserPage


def isCupsAvailable():
    """
    Static method to test the availability of CUPS.

    @return flag indicating the availability of CUPS
    @rtype bool
    """
    if OSUtilities.isMacPlatform():
        # OS X/MacOS always have CUPS
        return True
    elif OSUtilities.isLinuxPlatform() or OSUtilities.isFreeBsdPlatform():
        testPrinter = QPrinter()
        return testPrinter.supportsMultipleCopies()
    else:
        return False


class WebBrowserView(QWebEngineView):
    """
    Class implementing the web browser view widget.

    @signal sourceChanged(QUrl) emitted after the current URL has changed
    @signal forwardAvailable(bool) emitted after the current URL has changed
    @signal backwardAvailable(bool) emitted after the current URL has changed
    @signal highlighted(str) emitted, when the mouse hovers over a link
    @signal search(QUrl) emitted, when a search is requested
    @signal zoomValueChanged(int) emitted to signal a change of the zoom value
    @signal faviconChanged() emitted to signal a changed web site icon
    @signal safeBrowsingAbort() emitted to indicate an abort due to a safe
        browsing event
    @signal safeBrowsingBad(threatType, threatMessages) emitted to indicate a
        malicious web site as determined by safe browsing
    @signal showMessage(str) emitted to show a message in the main window
        status bar
    """

    sourceChanged = pyqtSignal(QUrl)
    forwardAvailable = pyqtSignal(bool)
    backwardAvailable = pyqtSignal(bool)
    highlighted = pyqtSignal(str)
    search = pyqtSignal(QUrl)
    zoomValueChanged = pyqtSignal(int)
    faviconChanged = pyqtSignal()
    safeBrowsingAbort = pyqtSignal()
    safeBrowsingBad = pyqtSignal(str, str)
    showMessage = pyqtSignal(str)

    ZoomLevels = [
        30,
        40,
        50,
        67,
        80,
        90,
        100,
        110,
        120,
        133,
        150,
        170,
        200,
        220,
        233,
        250,
        270,
        285,
        300,
    ]
    ZoomLevelDefault = 100

    def __init__(self, mainWindow, parent=None, name=""):
        """
        Constructor

        @param mainWindow reference to the main window
        @type WebBrowserWindow
        @param parent parent widget of this window
        @type QWidget
        @param name name of this window
        @type str
        """
        super().__init__(parent)
        self.setObjectName(name)

        self.__rwhvqt = None
        self.installEventFilter(self)

        self.__speedDial = WebBrowserWindow.speedDial()

        self.__page = None
        self.__createNewPage()

        self.__mw = mainWindow
        self.__tabWidget = parent
        self.__isLoading = False
        self.__progress = 0
        self.__siteIconLoader = None
        self.__siteIcon = QIcon()
        self.__menu = QMenu(self)
        self.__clickedPos = QPoint()
        self.__firstLoad = False
        self.__preview = QPixmap()
        self.__currentPrinter = None
        self.__printPreviewLoop = None
        self.__webAuthDialog = None

        self.__currentZoom = 100
        self.__zoomLevels = WebBrowserView.ZoomLevels[:]

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__showContextMenu)

        self.iconUrlChanged.connect(self.__iconUrlChanged)
        self.urlChanged.connect(self.__urlChanged)
        self.page().linkHovered.connect(self.__linkHovered)

        self.loadStarted.connect(self.__loadStarted)
        self.loadProgress.connect(self.__loadProgress)
        self.loadFinished.connect(self.__loadFinished)
        self.renderProcessTerminated.connect(self.__renderProcessTerminated)

        self.printRequested.connect(self.printPage)
        self.printFinished.connect(self.__printPageFinished)
        self.pdfPrintingFinished.connect(self.__printPageToPdfFinished)

        self.__mw.openSearchManager().currentEngineChanged.connect(
            self.__currentEngineChanged
        )

        self.setAcceptDrops(True)

        self.__rss = []

        self.__clickedFrame = None

        self.__mw.personalInformationManager().connectPage(self.page())

        self.__inspector = None
        WebInspector.registerView(self)

        self.__restoreData = None

        if self.parentWidget() is not None:
            self.parentWidget().installEventFilter(self)

        self.grabGesture(Qt.GestureType.PinchGesture)

    def __createNewPage(self):
        """
        Private method to create a new page object.
        """
        self.__page = WebBrowserPage(self, self)
        self.setPage(self.__page)

        self.__page.safeBrowsingAbort.connect(self.safeBrowsingAbort)
        self.__page.safeBrowsingBad.connect(self.safeBrowsingBad)
        with contextlib.suppress(AttributeError):
            # deprecated with Qt 6.5+
            self.__page.quotaRequested.connect(self.__quotaRequested)
        with contextlib.suppress(AttributeError):
            # Qt 6.4+
            self.__page.fileSystemAccessRequested.connect(
                self.__fileSystemAccessRequested
            )
        with contextlib.suppress(AttributeError):
            # Qt 6.7+
            self.__page.webAuthUxRequested.connect(self.__webAuthUxRequested)
        # The registerProtocolHandlerRequested signal is handled in
        # WebBrowserPage.
        self.__page.selectClientCertificate.connect(self.__selectClientCertificate)
        self.__page.findTextFinished.connect(self.__findTextFinished)

    def __setRwhvqt(self):
        """
        Private slot to set widget that receives input events.
        """
        self.grabGesture(Qt.GestureType.PinchGesture)
        self.__rwhvqt = self.focusProxy()
        if self.__rwhvqt:
            self.__rwhvqt.grabGesture(Qt.GestureType.PinchGesture)
            self.__rwhvqt.installEventFilter(self)
        else:
            print("Focus proxy is null!")  # __IGNORE_WARNING_M801__

    def __currentEngineChanged(self):
        """
        Private slot to track a change of the current search engine.
        """
        if self.url().toString() == "eric:home":
            self.reload()

    def mainWindow(self):
        """
        Public method to get a reference to the main window.

        @return reference to the main window
        @rtype WebBrowserWindow
        """
        return self.__mw

    def tabWidget(self):
        """
        Public method to get a reference to the tab widget containing this
        view.

        @return reference to the tab widget
        @rtype WebBrowserTabWidget
        """
        return self.__tabWidget

    def load(self, url):
        """
        Public method to load a web site.

        @param url URL to be loaded
        @type QUrl
        """
        if self.__page is not None and not self.__page.acceptNavigationRequest(
            url, QWebEnginePage.NavigationType.NavigationTypeTyped, True
        ):
            return

        super().load(url)

        if not self.__firstLoad:
            self.__firstLoad = True
            WebInspector.pushView(self)

    def setSource(self, name, newTab=False):
        """
        Public method used to set the source to be displayed.

        @param name filename to be shown
        @type QUrl
        @param newTab flag indicating to open the URL in a new tab
        @type bool
        """
        if name is None or not name.isValid():
            return

        if newTab:
            # open in a new tab
            self.__mw.newTab(name)
            return

        if not name.scheme():
            if not os.path.exists(name.toString()):
                name.setScheme(Preferences.getWebBrowser("DefaultScheme"))
            else:
                if OSUtilities.isWindowsPlatform():
                    name.setUrl(
                        "file:///"
                        + FileSystemUtilities.fromNativeSeparators(name.toString())
                    )
                else:
                    name.setUrl("file://" + name.toString())

        if len(name.scheme()) == 1 or name.scheme() == "file":
            # name is a local file
            if name.scheme() and len(name.scheme()) == 1:
                # it is a local path on win os
                name = QUrl.fromLocalFile(name.toString())

            if not pathlib.Path(name.toLocalFile()).exists():
                EricMessageBox.critical(
                    self,
                    self.tr("eric Web Browser"),
                    self.tr("""<p>The file <b>{0}</b> does not exist.</p>""").format(
                        name.toLocalFile()
                    ),
                )
                return

            if name.toLocalFile().lower().endswith((".pdf", ".chm")):
                started = QDesktopServices.openUrl(name)
                if not started:
                    EricMessageBox.critical(
                        self,
                        self.tr("eric Web Browser"),
                        self.tr(
                            """<p>Could not start a viewer"""
                            """ for file <b>{0}</b>.</p>"""
                        ).format(name.path()),
                    )
                return
        elif name.scheme() in ["mailto"]:
            started = QDesktopServices.openUrl(name)
            if not started:
                EricMessageBox.critical(
                    self,
                    self.tr("eric Web Browser"),
                    self.tr(
                        """<p>Could not start an application"""
                        """ for URL <b>{0}</b>.</p>"""
                    ).format(name.toString()),
                )
            return
        else:
            if name.toString().lower().endswith((".pdf", ".chm")):
                started = QDesktopServices.openUrl(name)
                if not started:
                    EricMessageBox.critical(
                        self,
                        self.tr("eric Web Browser"),
                        self.tr(
                            """<p>Could not start a viewer"""
                            """ for file <b>{0}</b>.</p>"""
                        ).format(name.path()),
                    )
                return

        self.load(name)

    def source(self):
        """
        Public method to return the URL of the loaded page.

        @return URL loaded in the help browser
        @rtype QUrl
        """
        return self.url()

    def documentTitle(self):
        """
        Public method to return the title of the loaded page.

        @return title
        @rtype str
        """
        return self.title()

    def backward(self):
        """
        Public slot to move backwards in history.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Back)
        self.__urlChanged(self.history().currentItem().url())

    def forward(self):
        """
        Public slot to move forward in history.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Forward)
        self.__urlChanged(self.history().currentItem().url())

    def home(self):
        """
        Public slot to move to the first page loaded.
        """
        homeUrl = QUrl(Preferences.getWebBrowser("HomePage"))
        self.setSource(homeUrl)
        self.__urlChanged(self.history().currentItem().url())

    def reload(self):
        """
        Public slot to reload the current page.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Reload)

    def reloadBypassingCache(self):
        """
        Public slot to reload the current page bypassing the cache.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.ReloadAndBypassCache)

    def copy(self):
        """
        Public slot to copy the selected text.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Copy)

    def cut(self):
        """
        Public slot to cut the selected text.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Cut)

    def paste(self):
        """
        Public slot to paste text from the clipboard.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Paste)

    def undo(self):
        """
        Public slot to undo the last edit action.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Undo)

    def redo(self):
        """
        Public slot to redo the last edit action.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Redo)

    def selectAll(self):
        """
        Public slot to select all text.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.SelectAll)

    def unselect(self):
        """
        Public slot to clear the current selection.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.Unselect)

    def isForwardAvailable(self):
        """
        Public method to determine, if a forward move in history is possible.

        @return flag indicating move forward is possible
        @rtype bool
        """
        return self.history().canGoForward()

    def isBackwardAvailable(self):
        """
        Public method to determine, if a backwards move in history is possible.

        @return flag indicating move backwards is possible
        @rtype bool
        """
        return self.history().canGoBack()

    def __levelForZoom(self, zoom):
        """
        Private method determining the zoom level index given a zoom factor.

        @param zoom zoom factor
        @type int
        @return index of zoom factor
        @rtype int
        """
        try:
            index = self.__zoomLevels.index(zoom)
        except ValueError:
            for index in range(len(self.__zoomLevels)):
                if zoom <= self.__zoomLevels[index]:
                    break
        return index

    def setZoomValue(self, value, saveValue=True):
        """
        Public method to set the zoom value.

        @param value zoom value
        @type int
        @param saveValue flag indicating to save the zoom value with the
            zoom manager
        @type bool
        """
        if value != self.__currentZoom:
            self.setZoomFactor(value / 100.0)
            self.__currentZoom = value
            if saveValue and not self.__mw.isPrivate():
                ZoomManager.instance().setZoomValue(self.url(), value)
            self.zoomValueChanged.emit(value)

    def zoomValue(self):
        """
        Public method to get the current zoom value.

        @return zoom value
        @rtype int
        """
        val = self.zoomFactor() * 100
        return int(val)

    def zoomIn(self):
        """
        Public slot to zoom into the page.
        """
        index = self.__levelForZoom(self.__currentZoom)
        if index < len(self.__zoomLevels) - 1:
            self.setZoomValue(self.__zoomLevels[index + 1])

    def zoomOut(self):
        """
        Public slot to zoom out of the page.
        """
        index = self.__levelForZoom(self.__currentZoom)
        if index > 0:
            self.setZoomValue(self.__zoomLevels[index - 1])

    def zoomReset(self):
        """
        Public method to reset the zoom factor.
        """
        index = self.__levelForZoom(WebBrowserView.ZoomLevelDefault)
        self.setZoomValue(self.__zoomLevels[index])

    def mapToViewport(self, pos):
        """
        Public method to map a position to the viewport.

        @param pos position to be mapped
        @type QPoint
        @return viewport position
        @rtype QPoint
        """
        return self.page().mapToViewport(pos)

    def hasSelection(self):
        """
        Public method to determine, if there is some text selected.

        @return flag indicating text has been selected
        @rtype bool
        """
        return self.selectedText() != ""

    def findNextPrev(self, txt, case, backwards, callback):
        """
        Public slot to find the next occurrence of a text.

        @param txt text to search for
        @type str
        @param case flag indicating a case sensitive search
        @type bool
        @param backwards flag indicating a backwards search
        @type bool
        @param callback reference to a function with a bool parameter
        @type function(bool) or None
        """
        findFlags = QWebEnginePage.FindFlag(0)
        if case:
            findFlags |= QWebEnginePage.FindFlag.FindCaseSensitively
        if backwards:
            findFlags |= QWebEnginePage.FindFlag.FindBackward

        if callback is None:
            self.findText(txt, findFlags)
        else:
            self.findText(txt, findFlags, callback)

    def __findTextFinished(self, result):
        """
        Private slot handling the findTextFinished signal of the web page.

        @param result reference to the QWebEngineFindTextResult object of the
            last search
        @type QWebEngineFindTextResult
        """
        self.showMessage.emit(
            self.tr("Match {0} of {1}").format(
                result.activeMatch(), result.numberOfMatches()
            )
        )

    @pyqtSlot(QPoint)
    def __showContextMenu(self, pos):
        """
        Private slot to show a context menu.

        @param pos position for the context menu
        @type QPoint
        """
        self.__menu.clear()

        hitTest = self.page().hitTestContent(pos)

        self.__createContextMenu(self.__menu, hitTest)

        if not hitTest.isContentEditable() and not hitTest.isContentSelected():
            self.__menu.addSeparator()
            self.__menu.addMenu(self.__mw.adBlockIcon().menu())

        self.__menu.addSeparator()
        self.__menu.addAction(
            EricPixmapCache.getIcon("webInspector"),
            self.tr("Inspect Element..."),
            self.__webInspector,
        )

        if not self.__menu.isEmpty():
            self.__menu.popup(self.mapToGlobal(pos))

    def __createContextMenu(self, menu, hitTest):
        """
        Private method to populate the context menu.

        @param menu reference to the menu to be populated
        @type QMenu
        @param hitTest reference to the hit test object
        @type WebHitTestResult
        """
        spellCheckActionCount = 0
        contextMenuData = self.lastContextMenuRequest()
        hitTest.updateWithContextMenuData(contextMenuData)

        if bool(contextMenuData.misspelledWord()):
            boldFont = menu.font()
            boldFont.setBold(True)

            for suggestion in contextMenuData.spellCheckerSuggestions():
                act = menu.addAction(suggestion)
                act.setFont(boldFont)
                act.triggered.connect(
                    functools.partial(self.__replaceMisspelledWord, act)
                )

            if not bool(menu.actions()):
                menu.addAction(self.tr("No suggestions")).setEnabled(False)

            menu.addSeparator()
            spellCheckActionCount = len(menu.actions())

        if (
            not hitTest.linkUrl().isEmpty()
            and hitTest.linkUrl().scheme() != "javascript"
        ):
            self.__createLinkContextMenu(menu, hitTest)

        if not hitTest.imageUrl().isEmpty():
            self.__createImageContextMenu(menu, hitTest)

        if not hitTest.mediaUrl().isEmpty():
            self.__createMediaContextMenu(menu, hitTest)

        if hitTest.isContentEditable():
            # check, if only spell checker actions were added
            if len(menu.actions()) == spellCheckActionCount:
                menu.addAction(self.__mw.undoAct)
                menu.addAction(self.__mw.redoAct)
                menu.addSeparator()
                menu.addAction(self.__mw.cutAct)
                menu.addAction(self.__mw.copyAct)
                menu.addAction(self.__mw.pasteAct)
                menu.addSeparator()
                self.__mw.personalInformationManager().createSubMenu(
                    menu, self, hitTest
                )

            if hitTest.tagName() == "input":
                menu.addSeparator()
                act = menu.addAction("")
                act.setVisible(False)
                self.__checkForForm(act, hitTest.pos())

        if self.selectedText():
            self.__createSelectedTextContextMenu(menu, hitTest)

        if self.__menu.isEmpty():
            self.__createPageContextMenu(menu)

    def __createLinkContextMenu(self, menu, hitTest):
        """
        Private method to populate the context menu for URLs.

        @param menu reference to the menu to be populated
        @type QMenu
        @param hitTest reference to the hit test object
        @type WebHitTestResult
        """
        if not menu.isEmpty():
            menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("openNewTab"),
            self.tr("Open Link in New Tab\tCtrl+LMB"),
        )
        act.setData(hitTest.linkUrl())
        act.triggered.connect(functools.partial(self.__openLinkInNewTab, act))
        act = menu.addAction(
            EricPixmapCache.getIcon("newWindow"), self.tr("Open Link in New Window")
        )
        act.setData(hitTest.linkUrl())
        act.triggered.connect(functools.partial(self.__openLinkInNewWindow, act))
        act = menu.addAction(
            EricPixmapCache.getIcon("privateMode"),
            self.tr("Open Link in New Private Window"),
        )
        act.setData(hitTest.linkUrl())
        act.triggered.connect(functools.partial(self.__openLinkInNewPrivateWindow, act))
        menu.addSeparator()
        menu.addAction(
            EricPixmapCache.getIcon("download"),
            self.tr("Save Lin&k"),
            self.__downloadLink,
        )
        act = menu.addAction(
            EricPixmapCache.getIcon("bookmark22"), self.tr("Bookmark this Link")
        )
        act.setData(hitTest.linkUrl())
        act.triggered.connect(functools.partial(self.__bookmarkLink, act))
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy URL to Clipboard")
        )
        act.setData(hitTest.linkUrl())
        act.triggered.connect(functools.partial(self.__copyLink, act))
        act = menu.addAction(EricPixmapCache.getIcon("mailSend"), self.tr("Send URL"))
        act.setData(hitTest.linkUrl())
        act.triggered.connect(functools.partial(self.__sendLink, act))
        if (
            Preferences.getWebBrowser("VirusTotalEnabled")
            and Preferences.getWebBrowser("VirusTotalServiceKey") != ""
        ):
            act = menu.addAction(
                EricPixmapCache.getIcon("virustotal"),
                self.tr("Scan Link with VirusTotal"),
            )
            act.setData(hitTest.linkUrl())
            act.triggered.connect(functools.partial(self.__virusTotal, act))

    def __createImageContextMenu(self, menu, hitTest):
        """
        Private method to populate the context menu for images.

        @param menu reference to the menu to be populated
        @type QMenu
        @param hitTest reference to the hit test object
        @type WebHitTestResult
        """
        if not menu.isEmpty():
            menu.addSeparator()

        act = menu.addAction(
            EricPixmapCache.getIcon("openNewTab"), self.tr("Open Image in New Tab")
        )
        act.setData(hitTest.imageUrl())
        act.triggered.connect(functools.partial(self.__openLinkInNewTab, act))
        menu.addSeparator()
        menu.addAction(
            EricPixmapCache.getIcon("download"),
            self.tr("Save Image"),
            self.__downloadImage,
        )
        menu.addAction(self.tr("Copy Image to Clipboard"), self.__copyImage)
        act = menu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy Image URL to Clipboard")
        )
        act.setData(hitTest.imageUrl())
        act.triggered.connect(functools.partial(self.__copyLink, act))
        act = menu.addAction(
            EricPixmapCache.getIcon("mailSend"), self.tr("Send Image URL")
        )
        act.setData(hitTest.imageUrl())
        act.triggered.connect(functools.partial(self.__sendLink, act))

        if hitTest.imageUrl().scheme() in ["http", "https"]:
            menu.addSeparator()
            engine = WebBrowserWindow.imageSearchEngine()
            searchEngineName = engine.searchEngine()
            act = menu.addAction(
                EricPixmapCache.getIcon("{0}".format(searchEngineName.lower())),
                self.tr("Search image in {0}").format(searchEngineName),
            )
            act.setData(engine.getSearchQuery(hitTest.imageUrl()))
            act.triggered.connect(functools.partial(self.__searchImage, act))
            self.__imageSearchMenu = menu.addMenu(self.tr("Search image with..."))
            for searchEngineName in engine.searchEngineNames():
                act = self.__imageSearchMenu.addAction(
                    EricPixmapCache.getIcon("{0}".format(searchEngineName.lower())),
                    self.tr("Search image in {0}").format(searchEngineName),
                )
                act.setData(engine.getSearchQuery(hitTest.imageUrl(), searchEngineName))
                act.triggered.connect(functools.partial(self.__searchImage, act))

        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("adBlockPlus"), self.tr("Block Image")
        )
        act.setData(hitTest.imageUrl().toString())
        act.triggered.connect(functools.partial(self.__blockImage, act))
        if (
            Preferences.getWebBrowser("VirusTotalEnabled")
            and Preferences.getWebBrowser("VirusTotalServiceKey") != ""
        ):
            act = menu.addAction(
                EricPixmapCache.getIcon("virustotal"),
                self.tr("Scan Image with VirusTotal"),
            )
            act.setData(hitTest.imageUrl())
            act.triggered.connect(functools.partial(self.__virusTotal, act))

    def __createMediaContextMenu(self, menu, hitTest):
        """
        Private method to populate the context menu for media elements.

        @param menu reference to the menu to be populated
        @type QMenu
        @param hitTest reference to the hit test object
        @type WebHitTestResult
        """
        if not menu.isEmpty():
            menu.addSeparator()

        if hitTest.mediaPaused():
            menu.addAction(
                EricPixmapCache.getIcon("mediaPlaybackStart"),
                self.tr("Play"),
                self.__pauseMedia,
            )
        else:
            menu.addAction(
                EricPixmapCache.getIcon("mediaPlaybackPause"),
                self.tr("Pause"),
                self.__pauseMedia,
            )
        if hitTest.mediaMuted():
            menu.addAction(
                EricPixmapCache.getIcon("audioVolumeHigh"),
                self.tr("Unmute"),
                self.__muteMedia,
            )
        else:
            menu.addAction(
                EricPixmapCache.getIcon("audioVolumeMuted"),
                self.tr("Mute"),
                self.__muteMedia,
            )
        menu.addSeparator()
        act = menu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy Media URL to Clipboard")
        )
        act.setData(hitTest.mediaUrl())
        act.triggered.connect(functools.partial(self.__copyLink, act))
        act = menu.addAction(
            EricPixmapCache.getIcon("mailSend"), self.tr("Send Media URL")
        )
        act.setData(hitTest.mediaUrl())
        act.triggered.connect(functools.partial(self.__sendLink, act))
        menu.addAction(
            EricPixmapCache.getIcon("download"),
            self.tr("Save Media"),
            self.__downloadMedia,
        )

    def __createSelectedTextContextMenu(self, menu, _hitTest):
        """
        Private method to populate the context menu for selected text.

        @param menu reference to the menu to be populated
        @type QMenu
        @param _hitTest reference to the hit test object (unused)
        @type WebHitTestResult
        """
        from .OpenSearch.OpenSearchEngineAction import OpenSearchEngineAction
        from .WebBrowserLanguagesDialog import WebBrowserLanguagesDialog

        if not menu.isEmpty():
            menu.addSeparator()

        menu.addAction(self.__mw.copyAct)
        menu.addSeparator()
        act = menu.addAction(EricPixmapCache.getIcon("mailSend"), self.tr("Send Text"))
        act.setData(self.selectedText())
        act.triggered.connect(functools.partial(self.__sendLink, act))

        engineName = self.__mw.openSearchManager().currentEngineName()
        if engineName:
            menu.addAction(
                self.tr("Search with '{0}'").format(engineName),
                self.__searchDefaultRequested,
            )

        self.__searchMenu = menu.addMenu(self.tr("Search with..."))
        engineNames = self.__mw.openSearchManager().allEnginesNames()
        for engineName in engineNames:
            engine = self.__mw.openSearchManager().engine(engineName)
            act = OpenSearchEngineAction(engine, self.__searchMenu)
            act.setData(engineName)
            self.__searchMenu.addAction(act)
        self.__searchMenu.triggered.connect(self.__searchRequested)

        menu.addSeparator()

        languages = EricUtilities.toList(
            Preferences.getSettings().value(
                "WebBrowser/AcceptLanguages",
                WebBrowserLanguagesDialog.defaultAcceptLanguages(),
            )
        )
        if languages:
            language = languages[0]
            langCode = language.split("[")[1][:2]
            googleTranslatorUrl = QUrl(
                "http://translate.google.com/#auto/{0}/{1}".format(
                    langCode, self.selectedText()
                )
            )
            act = menu.addAction(
                EricPixmapCache.getIcon("translate"), self.tr("Google Translate")
            )
            act.setData(googleTranslatorUrl)
            act.triggered.connect(functools.partial(self.__openLinkInNewTab, act))
            wiktionaryUrl = QUrl(
                "http://{0}.wiktionary.org/wiki/Special:Search?search={1}".format(
                    langCode, self.selectedText()
                )
            )
            act = menu.addAction(
                EricPixmapCache.getIcon("wikipedia"), self.tr("Dictionary")
            )
            act.setData(wiktionaryUrl)
            act.triggered.connect(functools.partial(self.__openLinkInNewTab, act))
            menu.addSeparator()

        guessedUrl = QUrl.fromUserInput(self.selectedText().strip())
        if self.__isUrlValid(guessedUrl):
            act = menu.addAction(self.tr("Go to web address"))
            act.setData(guessedUrl)
            act.triggered.connect(functools.partial(self.__openLinkInNewTab, act))

    def __createPageContextMenu(self, menu):
        """
        Private method to populate the basic context menu.

        @param menu reference to the menu to be populated
        @type QMenu
        """
        from .UserAgent.UserAgentMenu import UserAgentMenu
        from .WebBrowserLanguagesDialog import WebBrowserLanguagesDialog

        menu.addAction(self.__mw.newTabAct)
        menu.addAction(self.__mw.newAct)
        menu.addSeparator()
        if self.__mw.saveAsAct is not None:
            menu.addAction(self.__mw.saveAsAct)
        menu.addAction(self.__mw.saveVisiblePageScreenAct)
        menu.addSeparator()

        if self.url().toString() == "eric:speeddial":
            # special menu for the spedd dial page
            menu.addAction(self.__mw.backAct)
            menu.addAction(self.__mw.forwardAct)
            menu.addSeparator()
            menu.addAction(
                EricPixmapCache.getIcon("plus"),
                self.tr("Add New Page"),
                self.__addSpeedDial,
            )
            menu.addAction(
                EricPixmapCache.getIcon("preferences-general"),
                self.tr("Configure Speed Dial"),
                self.__configureSpeedDial,
            )
            menu.addSeparator()
            menu.addAction(
                EricPixmapCache.getIcon("reload"),
                self.tr("Reload All Dials"),
                self.__reloadAllSpeedDials,
            )
            menu.addSeparator()
            menu.addAction(self.tr("Reset to Default Dials"), self.__resetSpeedDials)
            return

        menu.addAction(
            EricPixmapCache.getIcon("bookmark22"),
            self.tr("Bookmark this Page"),
            self.addBookmark,
        )
        act = menu.addAction(
            EricPixmapCache.getIcon("editCopy"), self.tr("Copy Page URL to Clipboard")
        )
        act.setData(self.url())
        act.triggered.connect(functools.partial(self.__copyLink, act))
        act = menu.addAction(
            EricPixmapCache.getIcon("mailSend"), self.tr("Send Page URL")
        )
        act.setData(self.url())
        act.triggered.connect(functools.partial(self.__sendLink, act))
        menu.addSeparator()

        self.__userAgentMenu = UserAgentMenu(self.tr("User Agent"), url=self.url())
        menu.addMenu(self.__userAgentMenu)
        menu.addSeparator()
        menu.addAction(self.__mw.backAct)
        menu.addAction(self.__mw.forwardAct)
        menu.addAction(self.__mw.homeAct)
        menu.addAction(self.__mw.reloadAct)
        menu.addAction(self.__mw.stopAct)
        menu.addSeparator()
        menu.addAction(self.__mw.zoomInAct)
        menu.addAction(self.__mw.zoomResetAct)
        menu.addAction(self.__mw.zoomOutAct)
        menu.addSeparator()
        menu.addAction(self.__mw.selectAllAct)
        menu.addSeparator()
        menu.addAction(self.__mw.findAct)
        menu.addSeparator()
        menu.addAction(self.__mw.pageSourceAct)
        menu.addSeparator()
        menu.addAction(self.__mw.siteInfoAct)
        if self.url().scheme() in ["http", "https"]:
            menu.addSeparator()

            w3url = QUrl.fromEncoded(
                b"http://validator.w3.org/check?uri="
                + QUrl.toPercentEncoding(bytes(self.url().toEncoded()).decode())
            )
            act = menu.addAction(
                EricPixmapCache.getIcon("w3"), self.tr("Validate Page")
            )
            act.setData(w3url)
            act.triggered.connect(functools.partial(self.__openLinkInNewTab, act))

            languages = EricUtilities.toList(
                Preferences.getSettings().value(
                    "WebBrowser/AcceptLanguages",
                    WebBrowserLanguagesDialog.defaultAcceptLanguages(),
                )
            )
            if languages:
                language = languages[0]
                langCode = language.split("[")[1][:2]
                googleTranslatorUrl = QUrl.fromEncoded(
                    b"http://translate.google.com/translate?sl=auto&tl="
                    + langCode.encode()
                    + b"&u="
                    + QUrl.toPercentEncoding(bytes(self.url().toEncoded()).decode())
                )
                act = menu.addAction(
                    EricPixmapCache.getIcon("translate"), self.tr("Google Translate")
                )
                act.setData(googleTranslatorUrl)
                act.triggered.connect(functools.partial(self.__openLinkInNewTab, act))

    def __checkForForm(self, act, pos):
        """
        Private method to check the given position for an open search form.

        @param act reference to the action to be populated upon success
        @type QAction
        @param pos position to be tested
        @type QPoint
        """
        from .Tools import Scripts

        self.__clickedPos = self.mapToViewport(pos)

        script = Scripts.getFormData(self.__clickedPos)
        self.page().runJavaScript(
            script,
            WebBrowserPage.SafeJsWorld,
            lambda res: self.__checkForFormCallback(res, act),
        )

    def __checkForFormCallback(self, res, act):
        """
        Private method handling the __checkForForm result.

        @param res result dictionary generated by JavaScript
        @type dict
        @param act reference to the action to be populated upon success
        @type QAction
        """
        if act is None or not bool(res):
            return

        url = QUrl(res["action"])
        method = res["method"]

        if not url.isEmpty() and method in ["get", "post"]:
            act.setVisible(True)
            act.setText(self.tr("Add to web search toolbar"))
            act.triggered.connect(self.__addSearchEngine)

    def __isUrlValid(self, url):
        """
        Private method to check a URL for validity.

        @param url URL to be checked
        @type QUrl
        @return flag indicating a valid URL
        @rtype bool
        """
        return (
            url.isValid()
            and bool(url.host())
            and bool(url.scheme())
            and "." in url.host()
        )

    def __replaceMisspelledWord(self, act):
        """
        Private slot to replace a misspelled word under the context menu.

        @param act reference to the action that triggered
        @type QAction
        """
        suggestion = act.text()
        self.page().replaceMisspelledWord(suggestion)

    def __openLinkInNewTab(self, act):
        """
        Private method called by the context menu to open a link in a new
        tab.

        @param act reference to the action that triggered
        @type QAction
        """
        url = act.data()
        if url.isEmpty():
            return

        self.setSource(url, newTab=True)

    def __openLinkInNewWindow(self, act):
        """
        Private slot called by the context menu to open a link in a new
        window.

        @param act reference to the action that triggered
        @type QAction
        """
        url = act.data()
        if url.isEmpty():
            return

        self.__mw.newWindow(url)

    def __openLinkInNewPrivateWindow(self, act):
        """
        Private slot called by the context menu to open a link in a new
        private window.

        @param act reference to the action that triggered
        @type QAction
        """
        url = act.data()
        if url.isEmpty():
            return

        self.__mw.newPrivateWindow(url)

    def __bookmarkLink(self, act):
        """
        Private slot to bookmark a link via the context menu.

        @param act reference to the action that triggered
        @type QAction
        """
        from .Bookmarks.AddBookmarkDialog import AddBookmarkDialog

        url = act.data()
        if url.isEmpty():
            return

        dlg = AddBookmarkDialog(parent=self)
        dlg.setUrl(bytes(url.toEncoded()).decode())
        dlg.exec()

    def __sendLink(self, act):
        """
        Private slot to send a link via email.

        @param act reference to the action that triggered
        @type QAction
        """
        data = act.data()
        if isinstance(data, QUrl) and data.isEmpty():
            return

        if isinstance(data, QUrl):
            data = data.toString()
        QDesktopServices.openUrl(QUrl("mailto:?body=" + data))

    def __copyLink(self, act):
        """
        Private slot to copy a link to the clipboard.

        @param act reference to the action that triggered
        @type QAction
        """
        data = act.data()
        if isinstance(data, QUrl) and data.isEmpty():
            return

        if isinstance(data, QUrl):
            data = data.toString()

        # copy the URL to both clipboard areas
        QApplication.clipboard().setText(data, QClipboard.Mode.Clipboard)
        QApplication.clipboard().setText(data, QClipboard.Mode.Selection)

    def __downloadLink(self):
        """
        Private slot to download a link and save it to disk.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.DownloadLinkToDisk)

    def __downloadImage(self):
        """
        Private slot to download an image and save it to disk.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.DownloadImageToDisk)

    def __copyImage(self):
        """
        Private slot to copy an image to the clipboard.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.CopyImageToClipboard)

    def __blockImage(self, act):
        """
        Private slot to add a block rule for an image URL.

        @param act reference to the action that triggered
        @type QAction
        """
        url = act.data()
        dlg = WebBrowserWindow.adBlockManager().showDialog()
        dlg.addCustomRule(url)

    def __searchImage(self, act):
        """
        Private slot to search for an image URL.

        @param act reference to the action that triggered
        @type QAction
        """
        url = act.data()
        self.setSource(url, newTab=True)

    def __downloadMedia(self):
        """
        Private slot to download a media and save it to disk.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.DownloadMediaToDisk)

    def __pauseMedia(self):
        """
        Private slot to pause or play the selected media.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.ToggleMediaPlayPause)

    def __muteMedia(self):
        """
        Private slot to (un)mute the selected media.
        """
        self.triggerPageAction(QWebEnginePage.WebAction.ToggleMediaMute)

    def __virusTotal(self, act):
        """
        Private slot to scan the selected URL with VirusTotal.

        @param act reference to the action that triggered
        @type QAction
        """
        url = act.data()
        self.__mw.requestVirusTotalScan(url)

    def __searchDefaultRequested(self):
        """
        Private slot to search for some text with the current search engine.
        """
        searchText = self.selectedText()

        if not searchText:
            return

        engine = self.__mw.openSearchManager().currentEngine()
        if engine:
            self.search.emit(engine.searchUrl(searchText))

    def __searchRequested(self, act):
        """
        Private slot to search for some text with a selected search engine.

        @param act reference to the action that triggered this slot
        @type QAction
        """
        searchText = self.selectedText()

        if not searchText:
            return

        engineName = act.data()
        engine = (
            self.__mw.openSearchManager().engine(engineName)
            if engineName
            else self.__mw.openSearchManager().currentEngine()
        )
        if engine:
            self.search.emit(engine.searchUrl(searchText))

    def __addSearchEngine(self):
        """
        Private slot to add a new search engine.
        """
        from .Tools import Scripts

        script = Scripts.getFormData(self.__clickedPos)
        self.page().runJavaScript(
            script,
            WebBrowserPage.SafeJsWorld,
            lambda res: self.__mw.openSearchManager().addEngineFromForm(res, self),
        )

    def __webInspector(self):
        """
        Private slot to show the web inspector window.
        """
        from .WebInspector import WebInspector

        if WebInspector.isEnabled():
            if self.__inspector is None:
                self.__inspector = WebInspector()
                self.__inspector.setView(self, True)
                self.__inspector.inspectorClosed.connect(self.closeWebInspector)
                self.__inspector.show()
            else:
                self.closeWebInspector()

    def closeWebInspector(self):
        """
        Public slot to close the web inspector.
        """
        if self.__inspector is not None:
            if self.__inspector.isVisible():
                self.__inspector.hide()
            WebInspector.unregisterView(self.__inspector)
            self.__inspector.deleteLater()
            self.__inspector = None

    def addBookmark(self):
        """
        Public slot to bookmark the current page.
        """
        from .Tools import Scripts

        script = Scripts.getAllMetaAttributes()
        self.page().runJavaScript(
            script, WebBrowserPage.SafeJsWorld, self.__addBookmarkCallback
        )

    def __addBookmarkCallback(self, res):
        """
        Private callback method of __addBookmark().

        @param res reference to the result list containing all
            meta attributes
        @type list
        """
        from .Bookmarks.AddBookmarkDialog import AddBookmarkDialog

        description = ""
        for meta in res:
            if meta["name"] == "description":
                description = meta["content"]

        dlg = AddBookmarkDialog(parent=self)
        dlg.setUrl(bytes(self.url().toEncoded()).decode())
        dlg.setTitle(self.title())
        dlg.setDescription(description)
        dlg.exec()

    def dragEnterEvent(self, evt):
        """
        Protected method called by a drag enter event.

        @param evt reference to the drag enter event
        @type QDragEnterEvent
        """
        evt.acceptProposedAction()

    def dragMoveEvent(self, evt):
        """
        Protected method called by a drag move event.

        @param evt reference to the drag move event
        @type QDragMoveEvent
        """
        evt.ignore()
        if evt.source() != self:
            if len(evt.mimeData().urls()) > 0:
                evt.acceptProposedAction()
            else:
                url = QUrl(evt.mimeData().text())
                if url.isValid():
                    evt.acceptProposedAction()

        if not evt.isAccepted():
            super().dragMoveEvent(evt)

    def dropEvent(self, evt):
        """
        Protected method called by a drop event.

        @param evt reference to the drop event
        @type QDropEvent
        """
        super().dropEvent(evt)
        if (
            not evt.isAccepted()
            and evt.source() != self
            and evt.possibleActions() & Qt.DropAction.CopyAction
        ):
            url = QUrl()
            if len(evt.mimeData().urls()) > 0:
                url = evt.mimeData().urls()[0]
            if not url.isValid():
                url = QUrl(evt.mimeData().text())
            if url.isValid():
                self.setSource(url)
                evt.acceptProposedAction()

    def _mousePressEvent(self, evt):
        """
        Protected method called by a mouse press event.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if WebBrowserWindow.autoScroller().mousePress(self, evt):
            evt.accept()
            return

    def _mouseReleaseEvent(self, evt):
        """
        Protected method called by a mouse release event.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if WebBrowserWindow.autoScroller().mouseRelease(evt):
            evt.accept()
            return

        accepted = evt.isAccepted()
        self.__page.event(evt)
        if not evt.isAccepted() and evt.button() == Qt.MouseButton.MiddleButton:
            url = QUrl(QApplication.clipboard().text(QClipboard.Mode.Selection))
            if not url.isEmpty() and url.isValid() and url.scheme() != "":
                self.setSource(url)
        evt.setAccepted(accepted)

    def _mouseMoveEvent(self, evt):
        """
        Protected method to handle mouse move events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if self.__mw and self.__mw.isFullScreen():
            if self.__mw.isFullScreenNavigationVisible():
                self.__mw.hideFullScreenNavigation()
            elif evt.y() < 10:
                # mouse is within 10px to the top
                self.__mw.showFullScreenNavigation()

        if WebBrowserWindow.autoScroller().mouseMove(evt):
            evt.accept()

    def _wheelEvent(self, evt):
        """
        Protected method to handle wheel events.

        @param evt reference to the wheel event
        @type QWheelEvent
        """
        if WebBrowserWindow.autoScroller().wheel():
            evt.accept()
            return

        delta = evt.angleDelta().y()
        if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if delta < 0:
                self.zoomOut()
            elif delta > 0:
                self.zoomIn()
            evt.accept()

        elif evt.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            if delta < 0:
                self.backward()
            elif delta > 0:
                self.forward()
            evt.accept()

    def _keyPressEvent(self, evt):
        """
        Protected method called by a key press.

        @param evt reference to the key event
        @type QKeyEvent
        """
        if self.__mw.personalInformationManager().viewKeyPressEvent(self, evt):
            evt.accept()
            return

        if evt.key() == Qt.Key.Key_ZoomIn:
            self.zoomIn()
            evt.accept()
        elif evt.key() == Qt.Key.Key_ZoomOut:
            self.zoomOut()
            evt.accept()
        elif evt.key() == Qt.Key.Key_Plus:
            if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.zoomIn()
                evt.accept()
        elif evt.key() == Qt.Key.Key_Minus:
            if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.zoomOut()
                evt.accept()
        elif evt.key() == Qt.Key.Key_0:
            if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.zoomReset()
                evt.accept()
        elif evt.key() == Qt.Key.Key_M:
            if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
                self.__muteMedia()
                evt.accept()
        elif evt.key() == Qt.Key.Key_Backspace:
            pos = QCursor.pos()
            pos = self.mapFromGlobal(pos)
            hitTest = self.page().hitTestContent(pos)
            if not hitTest.isContentEditable():
                self.pageAction(QWebEnginePage.WebAction.Back).trigger()
                evt.accept()

    def _keyReleaseEvent(self, evt):
        """
        Protected method called by a key release.

        @param evt reference to the key event
        @type QKeyEvent
        """
        if evt.key() == Qt.Key.Key_Escape and self.isFullScreen():
            self.triggerPageAction(QWebEnginePage.WebAction.ExitFullScreen)
            evt.accept()
            self.requestFullScreen(False)

    def _gestureEvent(self, evt):
        """
        Protected method handling gesture events.

        @param evt reference to the gesture event
        @type QGestureEvent
        """
        pinch = evt.gesture(Qt.GestureType.PinchGesture)
        if pinch:
            if pinch.state() == Qt.GestureState.GestureStarted:
                pinch.setTotalScaleFactor(self.__currentZoom / 100.0)
            elif pinch.state() == Qt.GestureState.GestureUpdated:
                scaleFactor = pinch.totalScaleFactor()
                self.setZoomValue(int(scaleFactor * 100))
            evt.accept()

    def eventFilter(self, obj, evt):
        """
        Public method to process event for other objects.

        @param obj reference to object to process events for
        @type QObject
        @param evt reference to event to be processed
        @type QEvent
        @return flag indicating that the event should be filtered out
        @rtype bool
        """
        if (
            obj is self
            and evt.type() == QEvent.Type.ParentChange
            and self.parentWidget() is not None
        ):
            self.parentWidget().installEventFilter(self)

        # find the render widget receiving events for the web page
        if obj is self and evt.type() == QEvent.Type.ChildAdded:
            QTimer.singleShot(0, self.__setRwhvqt)

        # forward events to WebBrowserView
        if obj is self.__rwhvqt and evt.type() in [
            QEvent.Type.KeyPress,
            QEvent.Type.KeyRelease,
            QEvent.Type.MouseButtonPress,
            QEvent.Type.MouseButtonRelease,
            QEvent.Type.MouseMove,
            QEvent.Type.Wheel,
            QEvent.Type.Gesture,
        ]:
            wasAccepted = evt.isAccepted()
            evt.setAccepted(False)
            if evt.type() == QEvent.Type.KeyPress:
                self._keyPressEvent(evt)
            elif evt.type() == QEvent.Type.KeyRelease:
                self._keyReleaseEvent(evt)
            elif evt.type() == QEvent.Type.MouseButtonPress:
                self._mousePressEvent(evt)
            elif evt.type() == QEvent.Type.MouseButtonRelease:
                self._mouseReleaseEvent(evt)
            elif evt.type() == QEvent.Type.MouseMove:
                self._mouseMoveEvent(evt)
            elif evt.type() == QEvent.Type.Wheel:
                self._wheelEvent(evt)
            elif evt.type() == QEvent.Type.Gesture:
                self._gestureEvent(evt)
            ret = evt.isAccepted()
            evt.setAccepted(wasAccepted)
            return ret

        if obj is self.parentWidget() and evt.type() in [
            QEvent.Type.KeyPress,
            QEvent.Type.KeyRelease,
        ]:
            wasAccepted = evt.isAccepted()
            evt.setAccepted(False)
            if evt.type() == QEvent.Type.KeyPress:
                self._keyPressEvent(evt)
            elif evt.type() == QEvent.Type.KeyRelease:
                self._keyReleaseEvent(evt)
            ret = evt.isAccepted()
            evt.setAccepted(wasAccepted)
            return ret

        # block already handled events
        if obj is self:
            if evt.type() in [
                QEvent.Type.KeyPress,
                QEvent.Type.KeyRelease,
                QEvent.Type.MouseButtonPress,
                QEvent.Type.MouseButtonRelease,
                QEvent.Type.MouseMove,
                QEvent.Type.Wheel,
                QEvent.Type.Gesture,
            ]:
                return True

            elif evt.type() == QEvent.Type.Hide and self.isFullScreen():
                self.triggerPageAction(QWebEnginePage.WebAction.ExitFullScreen)

        return super().eventFilter(obj, evt)

    def event(self, evt):
        """
        Public method handling events.

        @param evt reference to the event
        @type QEvent
        @return flag indicating, if the event was handled
        @rtype bool
        """
        if evt.type() == QEvent.Type.Gesture:
            self._gestureEvent(evt)
            return True

        return super().event(evt)

    def inputWidget(self):
        """
        Public method to get a reference to the render widget.

        @return reference to the render widget
        @rtype QWidget
        """
        return self.__rwhvqt

    def clearHistory(self):
        """
        Public slot to clear the history.
        """
        self.history().clear()
        self.__urlChanged(self.history().currentItem().url())

    ###########################################################################
    ## Signal converters below
    ###########################################################################

    def __urlChanged(self, url):
        """
        Private slot to handle the urlChanged signal.

        @param url the new url
        @type QUrl
        """
        self.sourceChanged.emit(url)

        self.forwardAvailable.emit(self.isForwardAvailable())
        self.backwardAvailable.emit(self.isBackwardAvailable())

    def __iconUrlChanged(self, url):
        """
        Private slot to handle the iconUrlChanged signal.

        @param url URL to get web site icon from
        @type QUrl
        """
        self.__siteIcon = QIcon()
        if self.__siteIconLoader is not None:
            self.__siteIconLoader.deleteLater()
        self.__siteIconLoader = WebIconLoader(url, self)
        self.__siteIconLoader.iconLoaded.connect(self.__iconLoaded)
        with contextlib.suppress(AttributeError):
            self.__siteIconLoader.sslConfiguration.connect(
                self.page().setSslConfiguration
            )
            self.__siteIconLoader.clearSslConfiguration.connect(
                self.page().clearSslConfiguration
            )

    def __iconLoaded(self, icon):
        """
        Private slot handling the loaded web site icon.

        @param icon web site icon
        @type QIcon
        """
        from eric7.WebBrowser.Tools import WebIconProvider

        self.__siteIcon = icon

        WebIconProvider.instance().saveIcon(self)

        self.faviconChanged.emit()

    def icon(self):
        """
        Public method to get the web site icon.

        @return web site icon
        @rtype QIcon
        """
        from eric7.WebBrowser.Tools import WebIconProvider

        if not self.__siteIcon.isNull():
            return QIcon(self.__siteIcon)

        return WebIconProvider.instance().iconForUrl(self.url())

    def title(self):
        """
        Public method to get the view title.

        @return view title
        @rtype str
        """
        titleStr = super().title()
        if not titleStr:
            if self.url().isEmpty():
                url = self.__page.requestedUrl()
            else:
                url = self.url()

            titleStr = url.host()
            if not titleStr:
                titleStr = url.toString(QUrl.UrlFormattingOption.RemoveFragment)

        if not titleStr or titleStr == "about:blank":
            titleStr = self.tr("Empty Page")

        return titleStr

    def __linkHovered(self, link):
        """
        Private slot to handle the linkHovered signal.

        @param link the URL of the link
        @type str
        """
        self.highlighted.emit(link)

    ###########################################################################
    ## Signal handlers below
    ###########################################################################

    def __renderProcessTerminated(self, status, _exitCode):
        """
        Private slot handling a crash of the web page render process.

        @param status termination status
        @type QWebEnginePage.RenderProcessTerminationStatus
        @param _exitCode exit code of the process (unused)
        @type int
        """
        if (
            status
            == QWebEnginePage.RenderProcessTerminationStatus.NormalTerminationStatus
        ):
            return

        QTimer.singleShot(0, functools.partial(self.__showTabCrashPage, status))

    def __showTabCrashPage(self, status):
        """
        Private slot to show the tab crash page.

        @param status termination status
        @type QWebEnginePage.RenderProcessTerminationStatus
        """
        self.page().deleteLater()
        self.__createNewPage()

        html = getHtmlPage("tabCrashPage.html")
        html = html.replace(
            "@IMAGE@",
            pixmapToDataUrl(
                ericApp()
                .style()
                .standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
                .pixmap(48, 48)
            ).toString(),
        )
        html = html.replace(
            "@FAVICON@",
            pixmapToDataUrl(
                ericApp()
                .style()
                .standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)
                .pixmap(16, 16)
            ).toString(),
        )
        html = html.replace("@TITLE@", self.tr("Render Process terminated abnormally"))
        html = html.replace("@H1@", self.tr("Render Process terminated abnormally"))
        if (
            status
            == QWebEnginePage.RenderProcessTerminationStatus.CrashedTerminationStatus
        ):
            msg = self.tr("The render process crashed while loading this page.")
        elif (
            status
            == QWebEnginePage.RenderProcessTerminationStatus.KilledTerminationStatus
        ):
            msg = self.tr("The render process was killed.")
        else:
            msg = self.tr("The render process terminated while loading this page.")
        html = html.replace("@LI-1@", msg)
        html = html.replace(
            "@LI-2@",
            self.tr(
                "Try reloading the page or closing some tabs to make more"
                " memory available."
            ),
        )
        self.page().setHtml(html, self.url())

    def __loadStarted(self):
        """
        Private method to handle the loadStarted signal.
        """
        # reset search
        self.findText("")
        self.__isLoading = True
        self.__progress = 0

    def __loadProgress(self, progress):
        """
        Private method to handle the loadProgress signal.

        @param progress progress value
        @type int
        """
        self.__progress = progress

    def __loadFinished(self, ok):
        """
        Private method to handle the loadFinished signal.

        @param ok flag indicating the result
        @type bool
        """
        self.__isLoading = False
        self.__progress = 0

        QApplication.processEvents()
        QTimer.singleShot(200, self.__renderPreview)

        zoomValue = ZoomManager.instance().zoomValue(self.url())
        self.setZoomValue(zoomValue)

        if ok:
            self.__mw.historyManager().addHistoryEntry(self)
            self.__mw.adBlockManager().page().hideBlockedPageEntries(self.page())
            self.__mw.passwordManager().completePage(self.page())

            self.page().runJavaScript(
                "document.lastModified",
                WebBrowserPage.SafeJsWorld,
                lambda res: self.__adjustBookmark(res),
            )

    def __adjustBookmark(self, lastModified):
        """
        Private slot to adjust the 'lastModified' value of bookmarks.

        @param lastModified last modified value
        @type str
        """
        from .Bookmarks.BookmarkNode import BookmarkTimestampType

        modified = QDateTime.fromString(lastModified, "MM/dd/yyyy hh:mm:ss")
        if modified.isValid():
            manager = WebBrowserWindow.bookmarksManager()
            for bookmark in manager.bookmarksForUrl(self.url()):
                manager.setTimestamp(bookmark, BookmarkTimestampType.Modified, modified)

    def isLoading(self):
        """
        Public method to get the loading state.

        @return flag indicating the loading state
        @rtype bool
        """
        return self.__isLoading

    def progress(self):
        """
        Public method to get the load progress.

        @return load progress
        @rtype int
        """
        return self.__progress

    def __renderPreview(self):
        """
        Private slot to render a preview pixmap after the page was loaded.
        """
        from .WebBrowserSnap import renderTabPreview

        w = 600  # some default width, the preview gets scaled when shown
        h = int(w * self.height() / self.width())
        self.__preview = renderTabPreview(self, w, h)

    def getPreview(self):
        """
        Public method to get the preview pixmap.

        @return preview pixmap
        @rtype QPixmap
        """
        return self.__preview

    def saveAs(self):
        """
        Public method to save the current page to a file.
        """
        url = self.url()
        if url.isEmpty():
            return

        fileName, savePageFormat = self.__getSavePageFileNameAndFormat()
        if fileName:
            self.page().save(fileName, savePageFormat)

    def __getSavePageFileNameAndFormat(self):
        """
        Private method to get the file name to save the page to.

        @return tuple containing the file name to save to and the
            save page format
        @rtype tuple of (str, QWebEngineDownloadRequest.SavePageFormat)
        """
        documentLocation = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        filterList = [
            self.tr("Web Archive (*.mhtml *.mht)"),
            self.tr("HTML File (*.html *.htm)"),
            self.tr("HTML File with all resources (*.html *.htm)"),
        ]
        extensionsList = [
            # tuple of extensions for *nix and Windows
            # keep in sync with filters list
            (".mhtml", ".mht"),
            (".html", ".htm"),
            (".html", ".htm"),
        ]
        if self.url().fileName():
            defaultFileName = os.path.join(documentLocation, self.url().fileName())
        else:
            defaultFileName = os.path.join(documentLocation, self.page().title())
            if OSUtilities.isWindowsPlatform():
                defaultFileName += ".mht"
            else:
                defaultFileName += ".mhtml"

        fileName = ""
        saveFormat = QWebEngineDownloadRequest.SavePageFormat.MimeHtmlSaveFormat

        fileName, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
            None, self.tr("Save Web Page"), defaultFileName, ";;".join(filterList), None
        )
        if fileName:
            index = filterList.index(selectedFilter)
            if index == 0:
                saveFormat = QWebEngineDownloadRequest.SavePageFormat.MimeHtmlSaveFormat
            elif index == 1:
                saveFormat = (
                    QWebEngineDownloadRequest.SavePageFormat.SingleHtmlSaveFormat
                )
            else:
                saveFormat = (
                    QWebEngineDownloadRequest.SavePageFormat.CompleteHtmlSaveFormat
                )

            extension = os.path.splitext(fileName)[1]
            if not extension:
                # add the platform specific default extension
                if OSUtilities.isWindowsPlatform():
                    extensionsIndex = 1
                else:
                    extensionsIndex = 0
                extensions = extensionsList[index]
                fileName += extensions[extensionsIndex]

        return fileName, saveFormat

    @pyqtSlot("QWebEngineClientCertificateSelection")
    def __selectClientCertificate(self, clientCertificateSelection):
        """
        Private slot to handle the client certificate selection request.

        @param clientCertificateSelection list of client SSL certificates
            found in system's client certificate store
        @type QWebEngineClientCertificateSelection
        """
        from eric7.EricNetwork.EricSslCertificateSelectionDialog import (
            EricSslCertificateSelectionDialog,
        )

        certificates = clientCertificateSelection.certificates()
        if len(certificates) == 0:
            clientCertificateSelection.selectNone()
        elif len(certificates) == 1:
            clientCertificateSelection.select(certificates[0])
        else:
            certificate = None
            dlg = EricSslCertificateSelectionDialog(certificates, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                certificate = dlg.getSelectedCertificate()

            if certificate is None:
                clientCertificateSelection.selectNone()
            else:
                clientCertificateSelection.select(certificate)

    ###########################################################################
    ## Miscellaneous methods below
    ###########################################################################

    def createWindow(self, windowType):
        """
        Public method called, when a new window should be created.

        @param windowType type of the requested window
        @type QWebEnginePage.WebWindowType
        @return reference to the created browser window
        @rtype WebBrowserView
        """
        if windowType in [
            QWebEnginePage.WebWindowType.WebBrowserTab,
            QWebEnginePage.WebWindowType.WebDialog,
        ]:
            return self.__mw.newTab(addNextTo=self)
        elif windowType == QWebEnginePage.WebWindowType.WebBrowserWindow:
            return self.__mw.newWindow().currentBrowser()
        elif windowType == QWebEnginePage.WebWindowType.WebBrowserBackgroundTab:
            return self.__mw.newTab(addNextTo=self, background=True)
        else:
            # default for unknow/new window types
            return self.__mw.newTab(addNextTo=self)

    def preferencesChanged(self):
        """
        Public method to indicate a change of the settings.
        """
        self.reload()

    ###########################################################################
    ## RSS related methods below
    ###########################################################################

    def checkRSS(self):
        """
        Public method to check, if the loaded page contains feed links.

        @return flag indicating the existence of feed links
        @rtype bool
        """
        self.__rss = []

        script = Scripts.getFeedLinks()
        feeds = self.page().execJavaScript(script)

        if feeds is not None:
            for feed in feeds:
                if feed["url"] and feed["title"]:
                    self.__rss.append((feed["title"], feed["url"]))

        return len(self.__rss) > 0

    def getRSS(self):
        """
        Public method to get the extracted RSS feeds.

        @return list of RSS feeds
        @rtype list of [(str, str)]
        """
        return self.__rss

    def hasRSS(self):
        """
        Public method to check, if the loaded page has RSS links.

        @return flag indicating the presence of RSS links
        @rtype bool
        """
        return len(self.__rss) > 0

    ###########################################################################
    ## Full Screen handling below
    ###########################################################################

    def isFullScreen(self):
        """
        Public method to check, if full screen mode is active.

        @return flag indicating full screen mode
        @rtype bool
        """
        return self.__mw.isFullScreen()

    def requestFullScreen(self, enable):
        """
        Public method to request full screen mode.

        @param enable flag indicating full screen mode on or off
        @type bool
        """
        if enable:
            self.__mw.enterHtmlFullScreen()
        else:
            self.__mw.showNormal()

    ###########################################################################
    ## Speed Dial slots below
    ###########################################################################

    def __addSpeedDial(self):
        """
        Private slot to add a new speed dial.
        """
        self.__page.runJavaScript("addSpeedDial();", WebBrowserPage.UnsafeJsWorld)

    def __configureSpeedDial(self):
        """
        Private slot to configure the speed dial.
        """
        self.page().runJavaScript("configureSpeedDial();", WebBrowserPage.UnsafeJsWorld)

    def __reloadAllSpeedDials(self):
        """
        Private slot to reload all speed dials.
        """
        self.page().runJavaScript("reloadAll();", WebBrowserPage.UnsafeJsWorld)

    def __resetSpeedDials(self):
        """
        Private slot to reset all speed dials to the default pages.
        """
        self.__speedDial.resetDials()

    ###########################################################################
    ## Methods below implement session related functions
    ###########################################################################

    def storeSessionData(self, data):
        """
        Public method to store session data to be restored later on.

        @param data dictionary with session data to be restored
        @type dict
        """
        self.__restoreData = data

    def __showEventSlot(self):
        """
        Private slot to perform actions when the view is shown and the event
        loop is running.
        """
        if self.__restoreData:
            sessionData, self.__restoreData = self.__restoreData, None
            self.loadFromSessionData(sessionData)

    def showEvent(self, evt):
        """
        Protected method to handle show events.

        @param evt reference to the show event object
        @type QShowEvent
        """
        super().showEvent(evt)
        self.activateSession()

    def activateSession(self):
        """
        Public slot to activate a restored session.
        """
        if self.__restoreData and not self.__mw.isClosing():
            QTimer.singleShot(0, self.__showEventSlot)

    def getSessionData(self):
        """
        Public method to populate the session data.

        @return dictionary containing the session data
        @rtype dict
        """
        if self.__restoreData:
            # page has not been shown yet
            return self.__restoreData

        sessionData = {}
        page = self.page()

        # 1. zoom factor
        sessionData["ZoomFactor"] = page.zoomFactor()

        # 2. scroll position
        scrollPos = page.scrollPosition()
        sessionData["ScrollPosition"] = {
            "x": scrollPos.x(),
            "y": scrollPos.y(),
        }

        # 3. page history
        historyArray = QByteArray()
        stream = QDataStream(historyArray, QIODevice.OpenModeFlag.WriteOnly)
        stream << page.history()
        sessionData["History"] = str(
            historyArray.toBase64(QByteArray.Base64Option.Base64UrlEncoding),
            encoding="ascii",
        )
        sessionData["HistoryIndex"] = page.history().currentItemIndex()

        # 4. current URL and title
        sessionData["Url"] = self.url().toString()
        sessionData["Title"] = self.title()

        # 5. web icon
        iconArray = QByteArray()
        stream = QDataStream(iconArray, QIODevice.OpenModeFlag.WriteOnly)
        stream << page.icon()
        sessionData["Icon"] = str(iconArray.toBase64(), encoding="ascii")

        return sessionData

    def loadFromSessionData(self, sessionData):
        """
        Public method to load the session data.

        @param sessionData dictionary containing the session data as
            generated by getSessionData()
        @type dict
        """
        page = self.page()
        # blank the page
        page.setUrl(QUrl("about:blank"))

        # 1. page history
        if "History" in sessionData:
            historyArray = QByteArray.fromBase64(
                sessionData["History"].encode("ascii"),
                QByteArray.Base64Option.Base64UrlEncoding,
            )
            stream = QDataStream(historyArray, QIODevice.OpenModeFlag.ReadOnly)
            stream >> page.history()

            if "HistoryIndex" in sessionData:
                item = page.history().itemAt(sessionData["HistoryIndex"])
                if item is not None:
                    page.history().goToItem(item)

        # 2. zoom factor
        if "ZoomFactor" in sessionData:
            page.setZoomFactor(sessionData["ZoomFactor"])

        # 3. scroll position
        if "ScrollPosition" in sessionData:
            scrollPos = sessionData["ScrollPosition"]
            page.scrollTo(QPointF(scrollPos["x"], scrollPos["y"]))

    def extractSessionMetaData(self, sessionData):
        """
        Public method to extract some session meta data elements needed by the
        tab widget in case of deferred loading.

        @param sessionData dictionary containing the session data as
            generated by getSessionData()
        @type dict
        @return tuple containing the title, URL and web icon
        @rtype tuple of (str, str, QIcon)
        """
        from eric7.WebBrowser.Tools import WebIconProvider

        title = sessionData.get("Title", "")
        urlStr = sessionData.get("Url", "")

        if "Icon" in sessionData:
            iconArray = QByteArray.fromBase64(sessionData["Icon"].encode("ascii"))
            stream = QDataStream(iconArray, QIODevice.OpenModeFlag.ReadOnly)
            icon = QIcon()
            stream >> icon
        else:
            icon = WebIconProvider.instance().iconForUrl(QUrl.fromUserInput(urlStr))

        return title, urlStr, icon

    ###########################################################################
    ## Methods below implement safe browsing related functions
    ###########################################################################

    def getSafeBrowsingStatus(self):
        """
        Public method to get the safe browsing status of the current page.

        @return flag indicating a safe site
        @rtype bool
        """
        if self.__page:
            return self.__page.getSafeBrowsingStatus()
        else:
            return True

    ###########################################################################
    ## Methods below implement print support
    ###########################################################################

    def __setupPrinter(self, filePath=None):
        """
        Private method to create and initialize a QPrinter object.

        @param filePath name of the output file for the printer (defaults to None)
        @type str (optional)
        @return initialized QPrinter object
        @rtype QPrinter
        """
        printer = QPrinter(mode=QPrinter.PrinterMode.HighResolution)
        if Preferences.getPrinter("ColorMode"):
            printer.setColorMode(QPrinter.ColorMode.Color)
        else:
            printer.setColorMode(QPrinter.ColorMode.GrayScale)
        if Preferences.getPrinter("FirstPageFirst"):
            printer.setPageOrder(QPrinter.PageOrder.FirstPageFirst)
        else:
            printer.setPageOrder(QPrinter.PageOrder.LastPageFirst)
        printer.setPageMargins(
            QMarginsF(
                Preferences.getPrinter("LeftMargin") * 10,
                Preferences.getPrinter("TopMargin") * 10,
                Preferences.getPrinter("RightMargin") * 10,
                Preferences.getPrinter("BottomMargin") * 10,
            ),
            QPageLayout.Unit.Millimeter,
        )
        printerName = Preferences.getPrinter("PrinterName")
        if printerName:
            printer.setPrinterName(printerName)
        printer.setResolution(Preferences.getPrinter("Resolution"))
        documentName = WebBrowserTools.getFileNameFromUrl(self.url())
        printer.setDocName(documentName)
        documentsPath = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.DocumentsLocation
        )
        if filePath is None:
            filePath = "{0}.pdf".format(documentName)
        filePath = (
            os.path.join(documentsPath, filePath)
            if documentsPath
            else os.path.abspath(filePath)
        )
        printer.setOutputFileName(filePath)
        printer.setCreator(self.tr("eric7 {0} ({1})").format(VersionOnly, Homepage))
        return printer

    @pyqtSlot()
    def printPage(self):
        """
        Public slot to print the current page.
        """
        if self.__currentPrinter is not None:
            EricMessageBox.warning(
                self,
                self.tr("Print Page"),
                self.tr(
                    "There is already a print job in progress. Printing is temporarily"
                    " disabled until the current job is finished."
                ),
            )
            return

        printer = self.__setupPrinter()

        printDialog = QPrintDialog(printer, self)
        printDialog.setOptions(
            QAbstractPrintDialog.PrintDialogOption.PrintToFile
            | QAbstractPrintDialog.PrintDialogOption.PrintShowPageSize
        )
        if not OSUtilities.isWindowsPlatform():
            if isCupsAvailable():
                printDialog.setOption(
                    QAbstractPrintDialog.PrintDialogOption.PrintCollateCopies
                )
            printDialog.setOption(QAbstractPrintDialog.PrintDialogOption.PrintPageRange)
        if printDialog.exec() == QDialog.DialogCode.Accepted:
            if printer.outputFormat() == QPrinter.OutputFormat.PdfFormat:
                self.printToPdf(
                    printer.outputFileName(), printer.pageLayout(), printer.pageRanges()
                )
            else:
                self.__currentPrinter = printer
                self.print(printer)

    @pyqtSlot()
    def printPageToPdf(self):
        """
        Public slot to save the current page as a PDF file.
        """
        from .Tools.PrintToPdfDialog import PrintToPdfDialog

        name = WebBrowserTools.getFileNameFromUrl(self.url())
        name = name.rsplit(".", 1)[0] + ".pdf" if name else "printout.pdf"
        dlg = PrintToPdfDialog(self.__setupPrinter(filePath=name), parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            filePath, pageLayout = dlg.getData()
            if filePath:
                if os.path.exists(filePath):
                    res = EricMessageBox.warning(
                        self,
                        self.tr("Print to PDF"),
                        self.tr(
                            """<p>The file <b>{0}</b> exists"""
                            """ already. Shall it be"""
                            """ overwritten?</p>"""
                        ).format(filePath),
                        EricMessageBox.No | EricMessageBox.Yes,
                        EricMessageBox.No,
                    )
                    if res == EricMessageBox.No:
                        return
                self.printToPdf(filePath, pageLayout)

    @pyqtSlot()
    def printPreviewPage(self):
        """
        Public slot to create a print preview of the current page.
        """
        printer = self.__setupPrinter()
        preview = QPrintPreviewDialog(printer, self)
        preview.resize(800, 750)
        preview.paintRequested.connect(self.__printPreviewRequested)
        preview.exec()

    @pyqtSlot(QPrinter)
    def __printPreviewRequested(self, printer):
        """
        Private slot to generate the print preview.

        @param printer reference to the printer object
        @type QPrinter
        """
        # This needs to run its own event loop to prevent a premature return from
        # the method.
        self.__printPreviewLoop = QEventLoop()

        self.print(printer)

        self.__printPreviewLoop.exec()
        self.__printPreviewLoop = None

    @pyqtSlot(bool)
    def __printPageFinished(self, success):
        """
        Private slot to handle the finishing of a print job.

        @param success flag indicating success (not used)
        @type bool
        """
        if self.__printPreviewLoop is not None:
            # The print preview was created, now stop the print preview loop.
            self.__printPreviewLoop.quit()
            return

        # we printed to a real printer
        self.__currentPrinter = None

    @pyqtSlot(str, bool)
    def __printPageToPdfFinished(self, filepath, success):
        """
        Private slot to handle the finishing of a PDF print job.

        @param filepath path of the output PDF file
        @type str
        @param success flag indicating success
        @type bool
        """
        if not success:
            EricMessageBox.critical(
                self,
                self.tr("Print to PDF"),
                self.tr(
                    """<p>The PDF file <b>{0}</b> could not be generated.</p>"""
                ).format(filepath),
            )

    ###########################################################################
    ## Methods below implement slots for Qt 6.0 to 6.4
    ###########################################################################

    # deprecated with Qt 6.5+
    @pyqtSlot("QWebEngineQuotaRequest")
    def __quotaRequested(self, quotaRequest):
        """
        Private slot to handle quota requests of the web page.

        @param quotaRequest reference to the quota request object
        @type QWebEngineQuotaRequest
        """
        from .Download.DownloadUtilities import dataString

        acceptRequest = Preferences.getWebBrowser("AcceptQuotaRequest")
        # map yes/no/ask from (0, 1, 2)
        if acceptRequest == 0:
            # always yes
            ok = True
        elif acceptRequest == 1:
            # always no
            ok = False
        else:
            # ask user
            sizeStr = dataString(quotaRequest.requestedSize())

            ok = EricMessageBox.yesNo(
                self,
                self.tr("Quota Request"),
                self.tr(
                    """<p> Allow the website at <b>{0}</b> to use"""
                    """ <b>{1}</b> of persistent storage?</p>"""
                ).format(quotaRequest.origin().host(), sizeStr),
            )

        if ok:
            quotaRequest.accept()
        else:
            quotaRequest.reject()

    ###########################################################################
    ## Methods below implement slots for Qt 6.4+
    ###########################################################################

    with contextlib.suppress(TypeError):

        @pyqtSlot("QWebEngineFileSystemAccessRequest")
        def __fileSystemAccessRequested(self, accessRequest):
            """
            Private slot to handle file system access requests of the web page.

            @param accessRequest reference to the file system access request object
            @type QWebEngineFileSystemAccessRequest
            """
            from PyQt6.QtWebEngineCore import (  # __IGNORE_WARNING_I102__
                QWebEngineFileSystemAccessRequest,
            )

            acceptRequest = Preferences.getWebBrowser("AcceptFileSystemAccessRequest")
            # map yes/no/ask from (0, 1, 2)
            if acceptRequest == 0:
                # always yes
                ok = True
            elif acceptRequest == 1:
                # always no
                ok = False
            else:
                # ask user
                if (
                    accessRequest.accessFlags()
                    == QWebEngineFileSystemAccessRequest.AccessFlag.Read
                ):
                    msgTemplate = self.tr(
                        "<p>Grant the website at <b>{0}</b> <b>Read</b> access"
                        " to '{1}'?</p>"
                    )
                elif (
                    accessRequest.accessFlags()
                    == QWebEngineFileSystemAccessRequest.AccessFlag.Write
                ):
                    msgTemplate = self.tr(
                        "<p>Grant the website at <b>{0}</b> <b>Write</b> access"
                        " to '{1}'?</p>"
                    )
                else:
                    msgTemplate = self.tr(
                        "<p>Grant the website at <b>{0}</b> <b>Read and Write</b>"
                        " access to '{1}'?</p>"
                    )

                ok = EricMessageBox.yesNo(
                    self,
                    self.tr("File System Access Request"),
                    msgTemplate.format(
                        accessRequest.origin().host(),
                        accessRequest.filePath().toLocalFile(),
                    ),
                )

            if ok:
                accessRequest.accept()
            else:
                accessRequest.reject()

    ###########################################################################
    ## Methods below implement slots for Qt 6.7+
    ###########################################################################

    with contextlib.suppress(TypeError):

        @pyqtSlot("QWebEngineWebAuthUxRequest*")
        def __webAuthUxRequested(self, authUxRequest):
            """
            Private slot to handle WebAuth requests.

            @param authUxRequest reference to the WebAuth request object
            @type QWebEngineWebAuthUxRequest
            """
            from .WebAuth.WebBrowserWebAuthDialog import WebBrowserWebAuthDialog

            if self.__webAuthDialog is not None:
                del self.__webAuthDialog
                self.__webAuthDialog = None

            self.__webAuthDialog = WebBrowserWebAuthDialog(authUxRequest, self.__mw)
            self.__webAuthDialog.setModal(False)
            self.__webAuthDialog.setWindowFlags(
                self.__webAuthDialog.windowFlags()
                & ~Qt.WindowType.WindowContextHelpButtonHint
            )

            authUxRequest.stateChanged.connect(self.__webAuthUxRequestStateChanged)
            self.__webAuthDialog.show()

    with contextlib.suppress(TypeError):

        @pyqtSlot("QWebEngineWebAuthUxRequest::WebAuthUxState")
        def __webAuthUxRequestStateChanged(self, state):
            """
            Private slot to handle a change of state of the current WebAuth request.

            @param state new state
            @type QWebEngineWebAuthUxRequest.WebAuthUxState
            """
            if state in (
                QWebEngineWebAuthUxRequest.WebAuthUxState.Cancelled,
                QWebEngineWebAuthUxRequest.WebAuthUxState.Completed,
            ):
                self.__webAuthDialog.hide()
                del self.__webAuthDialog
                self.__webAuthDialog = None
            else:
                self.__webAuthDialog.updateDialog()
                self.__webAuthDialog.show()
