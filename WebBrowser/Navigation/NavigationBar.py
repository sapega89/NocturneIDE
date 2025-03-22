# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the navigation bar widget.
"""

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QMenu,
    QSizePolicy,
    QSplitter,
    QStyle,
    QToolButton,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricToolButton import EricToolButton
from eric7.WebBrowser.Download.DownloadManagerButton import DownloadManagerButton
from eric7.WebBrowser.WebBrowserWebSearchWidget import WebBrowserWebSearchWidget
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .ReloadStopButton import ReloadStopButton


class NavigationBar(QWidget):
    """
    Class implementing the navigation bar.
    """

    def __init__(self, mainWindow, parent=None):
        """
        Constructor

        @param mainWindow reference to the browser main window
        @type WebBrowserWindow
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setObjectName("navigationbar")

        self.__mw = mainWindow

        self.__layout = QHBoxLayout(self)
        margin = self.style().pixelMetric(
            QStyle.PixelMetric.PM_ToolBarItemMargin, None, self
        )
        self.__layout.setContentsMargins(margin, margin, margin, margin)
        self.__layout.setSpacing(
            self.style().pixelMetric(
                QStyle.PixelMetric.PM_ToolBarItemSpacing, None, self
            )
        )
        self.setLayout(self.__layout)

        self.__backButton = EricToolButton(self)
        self.__backButton.setObjectName("navigation_back_button")
        self.__backButton.setToolTip(self.tr("Move one screen backward"))
        self.__backButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.__backButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.__backButton.setAutoRaise(True)
        self.__backButton.setIcon(EricPixmapCache.getIcon("back"))
        self.__backButton.setEnabled(False)

        self.__forwardButton = EricToolButton(self)
        self.__forwardButton.setObjectName("navigation_forward_button")
        self.__forwardButton.setToolTip(self.tr("Move one screen forward"))
        self.__forwardButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.__forwardButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.__forwardButton.setAutoRaise(True)
        self.__forwardButton.setIcon(EricPixmapCache.getIcon("forward"))
        self.__forwardButton.setEnabled(False)

        self.__backNextLayout = QHBoxLayout()
        self.__backNextLayout.setContentsMargins(0, 0, 0, 0)
        self.__backNextLayout.setSpacing(0)
        self.__backNextLayout.addWidget(self.__backButton)
        self.__backNextLayout.addWidget(self.__forwardButton)

        self.__reloadStopButton = ReloadStopButton(self)

        self.__homeButton = EricToolButton(self)
        self.__homeButton.setObjectName("navigation_home_button")
        self.__homeButton.setToolTip(self.tr("Move to the initial screen"))
        self.__homeButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.__homeButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.__homeButton.setAutoRaise(True)
        self.__homeButton.setIcon(EricPixmapCache.getIcon("home"))

        self.__exitFullScreenButton = EricToolButton(self)
        self.__exitFullScreenButton.setObjectName("navigation_exitfullscreen_button")
        self.__exitFullScreenButton.setIcon(EricPixmapCache.getIcon("windowRestore"))
        self.__exitFullScreenButton.setToolTip(self.tr("Exit Fullscreen"))
        self.__exitFullScreenButton.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonIconOnly
        )
        self.__exitFullScreenButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.__exitFullScreenButton.setAutoRaise(True)
        self.__exitFullScreenButton.clicked.connect(self.__mw.toggleFullScreen)
        self.__exitFullScreenButton.setVisible(False)

        self.__downloadManagerButton = DownloadManagerButton(self)

        self.__superMenuButton = EricToolButton(self)
        self.__superMenuButton.setObjectName("navigation_supermenu_button")
        self.__superMenuButton.setIcon(EricPixmapCache.getIcon("superMenu"))
        self.__superMenuButton.setToolTip(self.tr("Main Menu"))
        self.__superMenuButton.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup
        )
        self.__superMenuButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.__superMenuButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.__superMenuButton.setAutoRaise(True)
        self.__superMenuButton.setShowMenuInside(True)

        self.__navigationSplitter = QSplitter(self)
        urlBar = self.__mw.tabWidget().stackedUrlBar()
        self.__navigationSplitter.addWidget(urlBar)

        self.__searchEdit = WebBrowserWebSearchWidget(self.__mw, self)
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        sizePolicy.setHorizontalStretch(2)
        sizePolicy.setVerticalStretch(0)
        self.__searchEdit.setSizePolicy(sizePolicy)
        self.__searchEdit.search.connect(self.__mw.openUrl)
        self.__navigationSplitter.addWidget(self.__searchEdit)

        self.__navigationSplitter.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum
        )
        self.__navigationSplitter.setCollapsible(0, False)

        self.__layout.addLayout(self.__backNextLayout)
        self.__layout.addWidget(self.__reloadStopButton)
        self.__layout.addWidget(self.__homeButton)
        self.__layout.addWidget(self.__navigationSplitter)
        self.__layout.addWidget(self.__downloadManagerButton)
        self.__layout.addWidget(self.__exitFullScreenButton)
        self.__layout.addWidget(self.__superMenuButton)

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.__contextMenuRequested)

        self.__backMenu = QMenu(self)
        self.__backMenu.triggered.connect(self.__navigationMenuActionTriggered)
        self.__backButton.setMenu(self.__backMenu)
        self.__backButton.aboutToShowMenu.connect(self.__showBackMenu)

        self.__forwardMenu = QMenu(self)
        self.__forwardMenu.triggered.connect(self.__navigationMenuActionTriggered)
        self.__forwardButton.setMenu(self.__forwardMenu)
        self.__forwardButton.aboutToShowMenu.connect(self.__showForwardMenu)

        self.__backButton.clicked.connect(self.__goBack)
        self.__backButton.middleClicked.connect(self.__goBackInNewTab)
        self.__backButton.controlClicked.connect(self.__goBackInNewTab)
        self.__forwardButton.clicked.connect(self.__goForward)
        self.__forwardButton.middleClicked.connect(self.__goForwardInNewTab)
        self.__forwardButton.controlClicked.connect(self.__goForwardInNewTab)
        self.__reloadStopButton.reloadClicked.connect(self.__reload)
        self.__reloadStopButton.stopClicked.connect(self.__stopLoad)
        self.__homeButton.clicked.connect(self.__goHome)
        self.__homeButton.middleClicked.connect(self.__goHomeInNewTab)
        self.__homeButton.controlClicked.connect(self.__goHomeInNewTab)

    def superMenuButton(self):
        """
        Public method to get a reference to the super menu button.

        @return reference to the super menu button
        @rtype QToolButton
        """
        return self.__superMenuButton

    def backButton(self):
        """
        Public method to get a reference to the back button.

        @return reference to the back button
        @rtype QToolButton
        """
        return self.__backButton

    def forwardButton(self):
        """
        Public method to get a reference to the forward button.

        @return reference to the forward button
        @rtype QToolButton
        """
        return self.__forwardButton

    def reloadStopButton(self):
        """
        Public method to get a reference to the reload/stop button.

        @return reference to the reload/stop button
        @rtype QToolButton
        """
        return self.__reloadStopButton

    def exitFullScreenButton(self):
        """
        Public method to get a reference to the exit full screen button.

        @return reference to the exit full screen button
        @rtype QToolButton
        """
        return self.__exitFullScreenButton

    def searchEdit(self):
        """
        Public method to get a reference to the web search edit.

        @return reference to the web search edit
        @rtype WebBrowserWebSearchWidget
        """
        return self.__searchEdit

    def __showBackMenu(self):
        """
        Private slot showing the backwards navigation menu.
        """
        self.__backMenu.clear()
        history = self.__mw.currentBrowser().history()
        backItems = history.backItems(20)
        # show max. 20 items

        for item in reversed(backItems):
            act = QAction(self)
            act.setData(item)
            icon = WebBrowserWindow.icon(item.url())
            act.setIcon(icon)
            act.setText(item.title())
            self.__backMenu.addAction(act)

        self.__backMenu.addSeparator()
        self.__backMenu.addAction(self.tr("Clear History"), self.__clearHistory)

    def __showForwardMenu(self):
        """
        Private slot showing the forwards navigation menu.
        """
        self.__forwardMenu.clear()
        history = self.__mw.currentBrowser().history()
        forwardItems = history.forwardItems(20)
        # show max. 20 items

        for item in forwardItems:
            act = QAction(self)
            act.setData(item)
            icon = WebBrowserWindow.icon(item.url())
            act.setIcon(icon)
            act.setText(item.title())
            self.__forwardMenu.addAction(act)

        self.__forwardMenu.addSeparator()
        self.__forwardMenu.addAction(self.tr("Clear History"), self.__clearHistory)

    def __navigationMenuActionTriggered(self, act):
        """
        Private slot to go to the selected page.

        @param act reference to the action selected in the navigation menu
        @type QAction
        """
        historyItem = act.data()
        if historyItem is not None:
            history = self.__mw.currentBrowser().history()
            history.goToItem(historyItem)

    def __goBack(self):
        """
        Private slot called to handle the backward button.
        """
        self.__mw.currentBrowser().backward()

    def __goBackInNewTab(self):
        """
        Private slot handling a middle click or Ctrl left click of the
        backward button.
        """
        history = self.__mw.currentBrowser().history()
        if history.canGoBack():
            backItem = history.backItem()
            self.__mw.newTab(
                link=backItem.url(),
                addNextTo=self.__mw.currentBrowser(),
                background=True,
            )

    def __goForward(self):
        """
        Private slot called to handle the forward button.
        """
        self.__mw.currentBrowser().forward()

    def __goForwardInNewTab(self):
        """
        Private slot handling a middle click or Ctrl left click of the
        forward button.
        """
        history = self.__mw.currentBrowser().history()
        if history.canGoForward():
            forwardItem = history.forwardItem()
            self.__mw.newTab(
                link=forwardItem.url(),
                addNextTo=self.__mw.currentBrowser(),
                background=True,
            )

    def __goHome(self):
        """
        Private slot called to handle the home button.
        """
        self.__mw.currentBrowser().home()

    def __goHomeInNewTab(self):
        """
        Private slot handling a middle click or Ctrl left click of the
        home button.
        """
        homeUrl = QUrl(Preferences.getWebBrowser("HomePage"))
        self.__mw.newTab(
            link=homeUrl, addNextTo=self.__mw.currentBrowser(), background=True
        )

    def __reload(self):
        """
        Private slot called to handle the reload button.
        """
        self.__mw.currentBrowser().reloadBypassingCache()

    def __stopLoad(self):
        """
        Private slot called to handle loading of the current page.
        """
        self.__mw.currentBrowser().stop()

    def __clearHistory(self):
        """
        Private slot to clear the history of the current web browser tab.
        """
        cb = self.__mw.currentBrowser()
        if cb is not None:
            cb.history().clear()
            self.__mw.setForwardAvailable(cb.isForwardAvailable())
            self.__mw.setBackwardAvailable(cb.isBackwardAvailable())

    def __contextMenuRequested(self, pos):
        """
        Private method to handle a context menu request.

        @param pos position of the request
        @type QPoint
        """
        menu = self.__mw.createPopupMenu()
        menu.exec(self.mapToGlobal(pos))
