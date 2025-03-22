# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the central widget showing the web pages.
"""

from PyQt6.QtCore import Qt, QUrl, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QMenu, QToolButton, QWidget

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricTabWidget import EricTabWidget
from eric7.SystemUtilities import FileSystemUtilities
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from . import WebInspector
from .ClosedTabsManager import ClosedTabsManager
from .UrlBar.StackedUrlBar import StackedUrlBar
from .WebBrowserPage import WebBrowserPage
from .WebBrowserTabBar import WebBrowserTabBar
from .WebBrowserView import WebBrowserView


class WebBrowserTabWidget(EricTabWidget):
    """
    Class implementing the central widget showing the web pages.

    @signal sourceChanged(WebBrowserView, QUrl) emitted after the URL of a
        browser has changed
    @signal currentUrlChanged(QUrl) emitted after the URL of the current
        browser has changed
    @signal titleChanged(WebBrowserView, str) emitted after the title of a
        browser has changed
    @signal showMessage(str) emitted to show a message in the main window
        status bar
    @signal browserOpened(QWidget) emitted after a new browser was created
    @signal browserClosed(QWidget) emitted after a browser was closed
    @signal browserZoomValueChanged(int) emitted to signal a change of the
        current browser's zoom level
    """

    sourceChanged = pyqtSignal(WebBrowserView, QUrl)
    currentUrlChanged = pyqtSignal(QUrl)
    titleChanged = pyqtSignal(WebBrowserView, str)
    showMessage = pyqtSignal(str)
    browserOpened = pyqtSignal(QWidget)
    browserClosed = pyqtSignal(QWidget)
    browserZoomValueChanged = pyqtSignal(int)

    def __init__(self, parent):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent, dnd=True)

        self.__tabBar = WebBrowserTabBar(self)
        self.setCustomTabBar(True, self.__tabBar)

        self.__mainWindow = parent

        self.setUsesScrollButtons(True)
        self.setDocumentMode(True)
        self.setElideMode(Qt.TextElideMode.ElideNone)

        self.__closedTabsManager = ClosedTabsManager()
        self.__closedTabsManager.closedTabAvailable.connect(self.__closedTabAvailable)

        self.__stackedUrlBar = StackedUrlBar(self)
        self.__tabBar.tabMoved.connect(self.__stackedUrlBar.moveBar)

        self.__tabContextMenuIndex = -1
        self.currentChanged[int].connect(self.__currentChanged)
        self.setTabContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customTabContextMenuRequested.connect(self.__showContextMenu)

        self.__rightCornerWidget = QWidget(self)
        self.__rightCornerWidgetLayout = QHBoxLayout(self.__rightCornerWidget)
        self.__rightCornerWidgetLayout.setContentsMargins(0, 0, 0, 0)
        self.__rightCornerWidgetLayout.setSpacing(0)

        self.__navigationMenu = QMenu(self)
        self.__navigationMenu.aboutToShow.connect(self.__showNavigationMenu)
        self.__navigationMenu.triggered.connect(self.__navigationMenuTriggered)

        self.__navigationButton = QToolButton(self)
        self.__navigationButton.setIcon(EricPixmapCache.getIcon("1downarrow"))
        self.__navigationButton.setToolTip(self.tr("Show a navigation menu"))
        self.__navigationButton.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.__navigationButton.setMenu(self.__navigationMenu)
        self.__navigationButton.setEnabled(False)
        self.__rightCornerWidgetLayout.addWidget(self.__navigationButton)

        self.__closedTabsMenu = QMenu(self)
        self.__closedTabsMenu.aboutToShow.connect(self.__aboutToShowClosedTabsMenu)

        self.__closedTabsButton = QToolButton(self)
        self.__closedTabsButton.setIcon(EricPixmapCache.getIcon("trash"))
        self.__closedTabsButton.setToolTip(
            self.tr("Show a navigation menu for closed tabs")
        )
        self.__closedTabsButton.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.__closedTabsButton.setMenu(self.__closedTabsMenu)
        self.__closedTabsButton.setEnabled(False)
        self.__rightCornerWidgetLayout.addWidget(self.__closedTabsButton)

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.closeBrowserAt)

        self.setCornerWidget(self.__rightCornerWidget, Qt.Corner.TopRightCorner)

        self.__newTabButton = QToolButton(self)
        self.__newTabButton.setIcon(EricPixmapCache.getIcon("plus"))
        self.__newTabButton.setToolTip(self.tr("Open a new web browser tab"))
        self.setCornerWidget(self.__newTabButton, Qt.Corner.TopLeftCorner)
        self.__newTabButton.clicked.connect(self.__newBrowser)

        self.__initTabContextMenu()

        self.__historyCompleter = None

    def __initTabContextMenu(self):
        """
        Private method to create the tab context menu.
        """
        self.__tabContextMenu = QMenu(self)
        self.tabContextNewAct = self.__tabContextMenu.addAction(
            EricPixmapCache.getIcon("tabNew"), self.tr("New Tab"), self.newBrowser
        )
        self.__tabContextMenu.addSeparator()
        self.leftMenuAct = self.__tabContextMenu.addAction(
            EricPixmapCache.getIcon("1leftarrow"),
            self.tr("Move Left"),
            self.__tabContextMenuMoveLeft,
        )
        self.rightMenuAct = self.__tabContextMenu.addAction(
            EricPixmapCache.getIcon("1rightarrow"),
            self.tr("Move Right"),
            self.__tabContextMenuMoveRight,
        )
        self.__tabContextMenu.addSeparator()
        self.tabContextCloneAct = self.__tabContextMenu.addAction(
            self.tr("Duplicate Page"), self.__tabContextMenuClone
        )
        self.__tabContextMenu.addSeparator()
        self.tabContextCloseAct = self.__tabContextMenu.addAction(
            EricPixmapCache.getIcon("tabClose"),
            self.tr("Close"),
            self.__tabContextMenuClose,
        )
        self.tabContextCloseOthersAct = self.__tabContextMenu.addAction(
            EricPixmapCache.getIcon("tabCloseOther"),
            self.tr("Close Others"),
            self.__tabContextMenuCloseOthers,
        )
        self.__tabContextMenu.addAction(self.tr("Close All"), self.closeAllBrowsers)
        self.__tabContextMenu.addSeparator()
        self.__tabContextMenu.addAction(
            EricPixmapCache.getIcon("printPreview"),
            self.tr("Print Preview"),
            self.__tabContextMenuPrintPreview,
        )
        self.__tabContextMenu.addAction(
            EricPixmapCache.getIcon("print"),
            self.tr("Print"),
            self.__tabContextMenuPrint,
        )
        self.__tabContextMenu.addAction(
            EricPixmapCache.getIcon("printPdf"),
            self.tr("Print as PDF"),
            self.__tabContextMenuPrintPdf,
        )
        self.__tabContextMenu.addSeparator()
        if hasattr(WebBrowserPage, "isAudioMuted"):
            self.__audioAct = self.__tabContextMenu.addAction(
                "", self.__tabContextMenuAudioMute
            )
            self.__tabContextMenu.addSeparator()
        else:
            self.__audioAct = None
        self.__tabContextMenu.addAction(
            EricPixmapCache.getIcon("reload"),
            self.tr("Reload All"),
            self.reloadAllBrowsers,
        )
        self.__tabContextMenu.addSeparator()
        self.__tabContextMenu.addAction(
            EricPixmapCache.getIcon("addBookmark"),
            self.tr("Bookmark All Tabs"),
            self.__mainWindow.bookmarkAll,
        )

        self.__tabBackContextMenu = QMenu(self)
        self.__tabBackContextMenu.addAction(self.tr("Close All"), self.closeAllBrowsers)
        self.__tabBackContextMenu.addAction(
            EricPixmapCache.getIcon("reload"),
            self.tr("Reload All"),
            self.reloadAllBrowsers,
        )
        self.__tabBackContextMenu.addAction(
            EricPixmapCache.getIcon("addBookmark"),
            self.tr("Bookmark All Tabs"),
            self.__mainWindow.bookmarkAll,
        )
        self.__tabBackContextMenu.addSeparator()
        self.__restoreClosedTabAct = self.__tabBackContextMenu.addAction(
            EricPixmapCache.getIcon("trash"), self.tr("Restore Closed Tab")
        )
        self.__restoreClosedTabAct.setEnabled(False)
        self.__restoreClosedTabAct.setData(0)
        self.__restoreClosedTabAct.triggered.connect(
            lambda: self.restoreClosedTab(self.__restoreClosedTabAct)
        )

    def __showContextMenu(self, coord, index):
        """
        Private slot to show the tab context menu.

        @param coord the position of the mouse pointer
        @type QPoint
        @param index index of the tab the menu is requested for
        @type int
        """
        coord = self.mapToGlobal(coord)
        if index == -1:
            self.__tabBackContextMenu.popup(coord)
        else:
            self.__tabContextMenuIndex = index
            self.leftMenuAct.setEnabled(index > 0)
            self.rightMenuAct.setEnabled(index < self.count() - 1)

            self.tabContextCloseOthersAct.setEnabled(self.count() > 1)

            if self.__audioAct is not None:
                if self.widget(self.__tabContextMenuIndex).page().isAudioMuted():
                    self.__audioAct.setText(self.tr("Unmute Tab"))
                    self.__audioAct.setIcon(EricPixmapCache.getIcon("audioVolumeHigh"))
                else:
                    self.__audioAct.setText(self.tr("Mute Tab"))
                    self.__audioAct.setIcon(EricPixmapCache.getIcon("audioVolumeMuted"))

            self.__tabContextMenu.popup(coord)

    def __tabContextMenuMoveLeft(self):
        """
        Private method to move a tab one position to the left.
        """
        self.moveTab(self.__tabContextMenuIndex, self.__tabContextMenuIndex - 1)

    def __tabContextMenuMoveRight(self):
        """
        Private method to move a tab one position to the right.
        """
        self.moveTab(self.__tabContextMenuIndex, self.__tabContextMenuIndex + 1)

    def __tabContextMenuClone(self):
        """
        Private method to clone the selected tab.
        """
        idx = self.__tabContextMenuIndex
        if idx < 0:
            idx = self.currentIndex()
        if idx < 0 or idx > self.count():
            return

        url = self.widget(idx).url()
        self.newBrowser(url)

    def __tabContextMenuClose(self):
        """
        Private method to close the selected tab.
        """
        self.closeBrowserAt(self.__tabContextMenuIndex)

    def __tabContextMenuCloseOthers(self):
        """
        Private slot to close all other tabs.
        """
        index = self.__tabContextMenuIndex
        for i in list(range(self.count() - 1, index, -1)) + list(
            range(index - 1, -1, -1)
        ):
            self.closeBrowserAt(i)

    def __tabContextMenuPrint(self):
        """
        Private method to print the selected tab.
        """
        browser = self.widget(self.__tabContextMenuIndex)
        self.printBrowser(browser)

    def __tabContextMenuPrintPdf(self):
        """
        Private method to print the selected tab as PDF.
        """
        browser = self.widget(self.__tabContextMenuIndex)
        self.printBrowserPdf(browser)

    def __tabContextMenuPrintPreview(self):
        """
        Private method to show a print preview of the selected tab.
        """
        browser = self.widget(self.__tabContextMenuIndex)
        self.printPreviewBrowser(browser)

    def __tabContextMenuAudioMute(self):
        """
        Private method to mute or unmute the selected tab.
        """
        page = self.widget(self.__tabContextMenuIndex).page()
        muted = page.isAudioMuted()
        page.setAudioMuted(not muted)

    @pyqtSlot(bool)
    def __recentlyAudibleChanged(self, recentlyAudible, page):
        """
        Private slot to react on the audible state of a page.

        @param recentlyAudible flag indicating the new audible state
        @type bool
        @param page reference to the web page
        @type WebBrowserPage
        """
        browser = page.view()
        if browser is None:
            return

        index = self.indexOf(browser)
        icon = page.icon()

        if page.isAudioMuted() or (not page.isAudioMuted() and recentlyAudible):
            pix = QPixmap(32, 32)
            pix.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pix)
            icon.paint(painter, 0, 0, 22, 22)
            if page.isAudioMuted():
                audioIcon = EricPixmapCache.getIcon("audioMuted")
            else:
                audioIcon = EricPixmapCache.getIcon("audioPlaying")
            audioIcon.paint(painter, 13, 13, 18, 18)
            painter.end()
            self.setTabIcon(index, QIcon(pix))
        else:
            self.setTabIcon(index, icon)

    @pyqtSlot()
    def __newBrowser(self):
        """
        Private slot to open a new browser tab.
        """
        self.newBrowser()

    def newBrowser(
        self, link=None, position=-1, background=False, restoreSession=False
    ):
        """
        Public method to create a new web browser tab.

        @param link link to be shown
        @type str or QUrl
        @param position position to create the new tab at or -1 to add it
            to the end
        @type int
        @param background flag indicating to open the tab in the
            background
        @type bool
        @param restoreSession flag indicating a restore session action
        @type bool
        @return reference to the new browser
        @rtype WebBrowserView
        """
        from .History.HistoryCompleter import HistoryCompleter, HistoryCompletionModel
        from .UrlBar.UrlBar import UrlBar

        if link is None:
            linkName = ""
        elif isinstance(link, QUrl):
            linkName = link.toString()
        else:
            linkName = link

        urlbar = UrlBar(self.__mainWindow, self)
        if self.__historyCompleter is None:
            histMgr = WebBrowserWindow.historyManager()
            self.__historyCompletionModel = HistoryCompletionModel(self)
            self.__historyCompletionModel.setSourceModel(histMgr.historyFilterModel())
            self.__historyCompleter = HistoryCompleter(
                self.__historyCompletionModel, self
            )
            self.__historyCompleter.activated[str].connect(self.__pathSelected)
        urlbar.setCompleter(self.__historyCompleter)
        urlbar.returnPressed.connect(lambda: self.__lineEditReturnPressed(urlbar))
        if position == -1:
            self.__stackedUrlBar.addWidget(urlbar)
        else:
            self.__stackedUrlBar.insertWidget(position, urlbar)

        browser = WebBrowserView(self.__mainWindow, self)
        urlbar.setBrowser(browser)

        browser.sourceChanged.connect(lambda url: self.__sourceChanged(url, browser))
        browser.titleChanged.connect(lambda title: self.__titleChanged(title, browser))
        browser.highlighted.connect(self.showMessage)
        browser.backwardAvailable.connect(self.__mainWindow.setBackwardAvailable)
        browser.forwardAvailable.connect(self.__mainWindow.setForwardAvailable)
        browser.loadProgress.connect(
            lambda progress: self.__loadProgress(progress, browser)
        )
        browser.loadFinished.connect(lambda ok: self.__loadFinished(ok, browser))
        browser.faviconChanged.connect(lambda: self.__iconChanged(browser))
        browser.search.connect(self.newBrowser)
        browser.page().windowCloseRequested.connect(
            lambda: self.__windowCloseRequested(browser.page())
        )
        browser.zoomValueChanged.connect(self.browserZoomValueChanged)
        if hasattr(WebBrowserPage, "recentlyAudibleChanged"):
            browser.page().recentlyAudibleChanged.connect(
                lambda audible: self.__recentlyAudibleChanged(audible, browser.page())
            )
        browser.page().printRequested.connect(lambda: self.printBrowser(browser))
        browser.showMessage.connect(self.showMessage)

        index = (
            self.addTab(browser, self.tr("..."))
            if position == -1
            else self.insertTab(position, browser, self.tr("..."))
        )
        if not background:
            self.setCurrentIndex(index)

        self.__mainWindow.closeAct.setEnabled(True)
        self.__mainWindow.closeAllAct.setEnabled(True)
        self.__navigationButton.setEnabled(True)

        if not restoreSession and not linkName:
            if Preferences.getWebBrowser("NewTabBehavior") == 0:
                linkName = "about:blank"
            elif Preferences.getWebBrowser("NewTabBehavior") == 1:
                linkName = Preferences.getWebBrowser("HomePage")
            elif Preferences.getWebBrowser("NewTabBehavior") == 2:
                linkName = "eric:speeddial"

        if linkName == "eric:blank":
            linkName = "about:blank"

        if linkName:
            browser.setSource(QUrl(linkName))
            if not browser.documentTitle():
                self.setTabText(
                    index, self.__elide(linkName, Qt.TextElideMode.ElideMiddle)
                )
                self.setTabToolTip(index, linkName)
            else:
                self.setTabText(
                    index, self.__elide(browser.documentTitle().replace("&", "&&"))
                )
                self.setTabToolTip(index, browser.documentTitle())

        self.browserOpened.emit(browser)

        return browser

    def newBrowserAfter(self, browser, link=None, background=False):
        """
        Public method to create a new web browser tab after a given one.

        @param browser reference to the browser to add after
        @type WebBrowserView
        @param link link to be shown
        @type str or QUrl
        @param background flag indicating to open the tab in the background
        @type bool
        @return reference to the new browser
        @rtype WebBrowserView
        """
        position = self.indexOf(browser) + 1 if browser else -1
        return self.newBrowser(link, position, background)

    def __showNavigationMenu(self):
        """
        Private slot to show the navigation button menu.
        """
        self.__navigationMenu.clear()
        for index in range(self.count()):
            act = self.__navigationMenu.addAction(
                self.tabIcon(index), self.tabText(index)
            )
            act.setData(index)

    def __navigationMenuTriggered(self, act):
        """
        Private slot called to handle the navigation button menu selection.

        @param act reference to the selected action
        @type QAction
        """
        index = act.data()
        if index is not None:
            self.setCurrentIndex(index)

    def __windowCloseRequested(self, page):
        """
        Private slot to handle the windowCloseRequested signal of a browser.

        @param page reference to the web page
        @type WebBrowserPage
        """
        browser = page.view()
        if browser is None:
            return

        index = self.indexOf(browser)
        self.closeBrowserAt(index)

    def reloadAllBrowsers(self):
        """
        Public slot to reload all browsers.
        """
        for index in range(self.count()):
            browser = self.widget(index)
            browser and browser.reload()

    @pyqtSlot()
    def closeBrowser(self):
        """
        Public slot called to handle the close action.
        """
        self.closeBrowserAt(self.currentIndex())

    def closeAllBrowsers(self, shutdown=False):
        """
        Public slot called to handle the close all action.

        @param shutdown flag indicating a shutdown action
        @type bool
        """
        for index in range(self.count() - 1, -1, -1):
            self.closeBrowserAt(index, shutdown=shutdown)

    def closeBrowserView(self, browser):
        """
        Public method to close the given browser.

        @param browser reference to the web browser view to be closed
        @type WebBrowserView
        """
        index = self.indexOf(browser)
        self.closeBrowserAt(index)

    def closeBrowserAt(self, index, shutdown=False):
        """
        Public slot to close a browser based on its index.

        @param index index of browser to close
        @type int
        @param shutdown flag indicating a shutdown action
        @type bool
        """
        browser = self.widget(index)
        if browser is None:
            return

        urlbar = self.__stackedUrlBar.widget(index)
        self.__stackedUrlBar.removeWidget(urlbar)
        urlbar.deleteLater()
        del urlbar

        self.__closedTabsManager.recordBrowser(browser, index)

        browser.closeWebInspector()
        WebInspector.unregisterView(browser)
        self.removeTab(index)
        self.browserClosed.emit(browser)
        browser.deleteLater()
        del browser

        if self.count() == 0 and not shutdown:
            self.newBrowser()
        else:
            self.currentChanged[int].emit(self.currentIndex())

    def currentBrowser(self):
        """
        Public method to get a reference to the current browser.

        @return reference to the current browser
        @rtype WebBrowserView
        """
        return self.currentWidget()

    def browserAt(self, index):
        """
        Public method to get a reference to the browser with the given index.

        @param index index of the browser to get
        @type int
        @return reference to the indexed browser
        @rtype WebBrowserView
        """
        return self.widget(index)

    def browsers(self):
        """
        Public method to get a list of references to all browsers.

        @return list of references to browsers
        @rtype list of WebBrowserView
        """
        li = []
        for index in range(self.count()):
            li.append(self.widget(index))
        return li

    @pyqtSlot()
    def printBrowser(self, browser=None):
        """
        Public slot called to print the displayed page.

        @param browser reference to the browser to be printed
        @type WebBrowserView
        """
        if browser is None:
            browser = self.currentBrowser()

        if browser is not None:
            browser.printPage()

    @pyqtSlot()
    def printBrowserPdf(self, browser=None):
        """
        Public slot called to print the displayed page to PDF.

        @param browser reference to the browser to be printed
        @type WebBrowserView
        """
        if browser is None:
            browser = self.currentBrowser()

        if browser is not None:
            browser.printPageToPdf()

    @pyqtSlot()
    def printPreviewBrowser(self, browser=None):
        """
        Public slot called to show a print preview of the displayed file.

        @param browser reference to the browser to be printed
        @type WebBrowserView
        """
        if browser is None:
            browser = self.currentBrowser()

        if browser is not None:
            browser.printPreviewPage()

    def __sourceChanged(self, url, browser):
        """
        Private slot to handle a change of a browsers source.

        @param url URL of the new site
        @type QUrl
        @param browser reference to the web browser
        @type WebBrowserView
        """
        self.sourceChanged.emit(browser, url)

        if browser == self.currentBrowser():
            self.currentUrlChanged.emit(url)

    def __titleChanged(self, title, browser):
        """
        Private slot to handle a change of a browsers title.

        @param title new title
        @type str
        @param browser reference to the web browser
        @type WebBrowserView
        """
        index = self.indexOf(browser)
        if title == "":
            title = browser.url().toString()

        self.setTabText(index, self.__elide(title.replace("&", "&&")))
        self.setTabToolTip(index, title)

        self.titleChanged.emit(browser, title)

    def __elide(self, txt, mode=Qt.TextElideMode.ElideRight, length=40):
        """
        Private method to elide some text.

        @param txt text to be elided
        @type str
        @param mode elide mode
        @type Qt.TextElideMode
        @param length amount of characters to be used
        @type int
        @return the elided text
        @rtype str
        """
        if mode == Qt.TextElideMode.ElideNone or len(txt) < length:
            return txt
        elif mode == Qt.TextElideMode.ElideLeft:
            return "...{0}".format(txt[-length:])
        elif mode == Qt.TextElideMode.ElideMiddle:
            return "{0}...{1}".format(txt[: length // 2], txt[-(length // 2) :])
        elif mode == Qt.TextElideMode.ElideRight:
            return "{0}...".format(txt[:length])
        else:
            # just in case
            return txt

    def preferencesChanged(self):
        """
        Public slot to handle a change of preferences.
        """
        for browser in self.browsers():
            browser.preferencesChanged()

        for urlbar in self.__stackedUrlBar.urlBars():
            urlbar.preferencesChanged()

    def __loadFinished(self, ok, _browser):
        """
        Private method to handle the loadFinished signal.

        @param ok flag indicating the result
        @type bool
        @param _browser reference to the web browser (unused)
        @type WebBrowserView
        """
        if ok:
            self.showMessage.emit(self.tr("Finished loading"))
        else:
            self.showMessage.emit(self.tr("Failed to load"))

    def __loadProgress(self, progress, browser):
        """
        Private method to handle the loadProgress signal.

        Note: This works around wegengine not sending a loadFinished
        signal for navigation on the same page.

        @param progress load progress in percent
        @type int
        @param browser reference to the web browser
        @type WebBrowserView
        """
        index = self.indexOf(browser)
        if progress == 0:
            # page loading has started
            anim = self.animationLabel(index, "loadingAnimation", 40)
            if not anim:
                self.setTabIcon(index, EricPixmapCache.getIcon("loading"))
            else:
                self.setTabIcon(index, QIcon())
            self.setTabText(index, self.tr("Loading..."))
            self.setTabToolTip(index, self.tr("Loading..."))
            self.showMessage.emit(self.tr("Loading..."))

            self.__mainWindow.setLoadingActions(True)
        elif progress == 100:
            self.resetAnimation(index)
            self.setTabIcon(index, WebBrowserWindow.icon(browser.url()))
            self.showMessage.emit(self.tr("Finished loading"))

            self.__mainWindow.setLoadingActions(False)

    def __iconChanged(self, browser):
        """
        Private slot to handle a change of the web site icon.

        @param browser reference to the web browser
        @type WebBrowserView
        """
        self.setTabIcon(self.indexOf(browser), browser.icon())
        self.__mainWindow.bookmarksManager().faviconChanged(browser.url())

    def getSourceFileList(self):
        """
        Public method to get a list of all opened Qt help files.

        @return dictionary with tab id as key and host/namespace as value
        @rtype dict
        """
        sourceList = {}
        for i in range(self.count()):
            browser = self.widget(i)
            if browser is not None and browser.source().isValid():
                sourceList[i] = browser.source().host()

        return sourceList

    def shallShutDown(self):
        """
        Public method to check, if the application should be shut down.

        @return flag indicating a shut down
        @rtype bool
        """
        if self.count() > 1 and Preferences.getWebBrowser("WarnOnMultipleClose"):
            mb = EricMessageBox.EricMessageBox(
                EricMessageBox.Information,
                self.tr("Are you sure you want to close the window?"),
                self.tr(
                    """Are you sure you want to close the window?\n"""
                    """You have %n tab(s) open.""",
                    "",
                    self.count(),
                ),
                modal=True,
                parent=self,
            )
            quitButton = mb.addButton(self.tr("&Quit"), EricMessageBox.AcceptRole)
            quitButton.setIcon(EricPixmapCache.getIcon("exit"))
            closeTabButton = mb.addButton(
                self.tr("C&lose Current Tab"), EricMessageBox.AcceptRole
            )
            closeTabButton.setIcon(EricPixmapCache.getIcon("tabClose"))
            mb.addButton(EricMessageBox.Cancel)
            mb.exec()
            if mb.clickedButton() == quitButton:
                return True
            else:
                if mb.clickedButton() == closeTabButton:
                    self.closeBrowser()
                return False

        return True

    def stackedUrlBar(self):
        """
        Public method to get a reference to the stacked url bar.

        @return reference to the stacked url bar
        @rtype StackedUrlBar
        """
        return self.__stackedUrlBar

    def currentUrlBar(self):
        """
        Public method to get a reference to the current url bar.

        @return reference to the current url bar
        @rtype UrlBar
        """
        return self.__stackedUrlBar.currentWidget()

    def urlBarForView(self, view):
        """
        Public method to get a reference to the UrlBar associated with the
        given view.

        @param view reference to the view to get the urlbar for
        @type WebBrowserView
        @return reference to the associated urlbar
        @rtype UrlBar
        """
        for urlbar in self.__stackedUrlBar.urlBars():
            if urlbar.browser() is view:
                return urlbar

        return None

    def __lineEditReturnPressed(self, edit):
        """
        Private slot to handle the entering of an URL.

        @param edit reference to the line edit
        @type UrlBar
        """
        url = self.__guessUrlFromPath(edit.text())
        if ericApp().keyboardModifiers() == Qt.KeyboardModifier.AltModifier:
            self.newBrowser(url)
        else:
            self.currentBrowser().setSource(url)
            self.currentBrowser().setFocus()

    def __pathSelected(self, path):
        """
        Private slot called when a URL is selected from the completer.

        @param path path to be shown
        @type str
        """
        url = self.__guessUrlFromPath(path)
        self.currentBrowser().setSource(url)

    def __guessUrlFromPath(self, path):
        """
        Private method to guess an URL given a path string.

        @param path path string to guess an URL for
        @type str
        @return guessed URL
        @rtype QUrl
        """
        manager = self.__mainWindow.openSearchManager()
        path = FileSystemUtilities.fromNativeSeparators(path)
        url = manager.convertKeywordSearchToUrl(path)
        if url.isValid():
            return url

        try:
            url = QUrl.fromUserInput(path)
        except AttributeError:
            url = QUrl(path)

        if url.scheme() == "about" and url.path() == "home":
            url = QUrl("eric:home")

        if url.scheme() in ["s", "search"]:
            url = manager.currentEngine().searchUrl(url.path().strip())

        if url.scheme() != "" and (url.host() != "" or url.path() != ""):
            return url

        urlString = Preferences.getWebBrowser("DefaultScheme") + path.strip()
        url = QUrl.fromEncoded(urlString.encode("utf-8"), QUrl.ParsingMode.TolerantMode)

        return url

    def __currentChanged(self, index):
        """
        Private slot to handle an index change.

        @param index new index
        @type int
        """
        self.__stackedUrlBar.setCurrentIndex(index)

        browser = self.browserAt(index)
        if browser is not None:
            if browser.url() == "" and browser.hasFocus():
                self.__stackedUrlBar.currentWidget.setFocus()
            elif browser.url() != "":
                browser.setFocus()

    def restoreClosedTab(self, act):
        """
        Public slot to restore the most recently closed tab.

        @param act reference to the action that triggered
        @type QAction
        """
        if not self.canRestoreClosedTab():
            return

        tab = self.__closedTabsManager.getClosedTabAt(act.data())

        self.newBrowser(tab.url.toString(), position=tab.position)

    def canRestoreClosedTab(self):
        """
        Public method to check, if closed tabs can be restored.

        @return flag indicating that closed tabs can be restored
        @rtype bool
        """
        return self.__closedTabsManager.isClosedTabAvailable()

    def restoreAllClosedTabs(self):
        """
        Public slot to restore all closed tabs.
        """
        if not self.canRestoreClosedTab():
            return

        for tab in self.__closedTabsManager.allClosedTabs():
            self.newBrowser(tab.url.toString(), position=tab.position)
        self.__closedTabsManager.clearList()

    def clearClosedTabsList(self):
        """
        Public slot to clear the list of closed tabs.
        """
        self.__closedTabsManager.clearList()

    def __aboutToShowClosedTabsMenu(self):
        """
        Private slot to populate the closed tabs menu.
        """
        fm = self.__closedTabsMenu.fontMetrics()
        maxWidth = fm.horizontalAdvance("m") * 40

        self.__closedTabsMenu.clear()
        for index, tab in enumerate(self.__closedTabsManager.allClosedTabs()):
            title = fm.elidedText(tab.title, Qt.TextElideMode.ElideRight, maxWidth)
            act = self.__closedTabsMenu.addAction(
                self.__mainWindow.icon(tab.url), title
            )
            act.setData(index)
            act.triggered.connect(lambda: self.restoreClosedTab(act))
        self.__closedTabsMenu.addSeparator()
        self.__closedTabsMenu.addAction(
            self.tr("Restore All Closed Tabs"), self.restoreAllClosedTabs
        )
        self.__closedTabsMenu.addAction(self.tr("Clear List"), self.clearClosedTabsList)

    def closedTabsManager(self):
        """
        Public slot to get a reference to the closed tabs manager.

        @return reference to the closed tabs manager
        @rtype ClosedTabsManager
        """
        return self.__closedTabsManager

    def __closedTabAvailable(self, avail):
        """
        Private slot to handle changes of the availability of closed tabs.

        @param avail flag indicating the availability of closed tabs
        @type bool
        """
        self.__closedTabsButton.setEnabled(avail)
        self.__restoreClosedTabAct.setEnabled(avail)

    ####################################################
    ## Methods below implement session related functions
    ####################################################

    def getSessionData(self):
        """
        Public method to populate the session data.

        @return dictionary containing the session data
        @rtype dict
        """
        sessionData = {
            # 1. current index
            "CurrentTabIndex": self.currentIndex(),
            # 2. tab data
            "Tabs": [],
        }

        for index in range(self.count()):
            browser = self.widget(index)
            data = browser.getSessionData()
            sessionData["Tabs"].append(data)

        return sessionData

    def loadFromSessionData(self, sessionData):
        """
        Public method to load the session data.

        @param sessionData dictionary containing the session data as
            generated by getSessionData()
        @type dict
        """
        tabCount = self.count()

        # 1. load tab data
        if "Tabs" in sessionData:
            loadTabOnActivate = Preferences.getWebBrowser("LoadTabOnActivation")
            for data in sessionData["Tabs"]:
                browser = self.newBrowser(restoreSession=True)
                if loadTabOnActivate:
                    browser.storeSessionData(data)
                    title, _urlStr, icon = browser.extractSessionMetaData(data)
                    index = self.indexOf(browser)
                    self.setTabText(index, title)
                    self.setTabIcon(index, icon)
                else:
                    browser.loadFromSessionData(data)

        # 2. set tab index
        if "CurrentTabIndex" in sessionData and sessionData["CurrentTabIndex"] >= 0:
            index = tabCount + sessionData["CurrentTabIndex"]
            self.setCurrentIndex(index)
            self.browserAt(index).activateSession()
