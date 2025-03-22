# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the JavaScript status bar icon.
"""

#
# This is modeled after the code found in Qupzilla
# Copyright (C) 2014  David Rosca <nowrep@gmail.com>
#

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSlot
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWidgets import QDialog, QGraphicsColorizeEffect, QMenu

from eric7.EricGui import EricPixmapCache

from .StatusBarIcon import StatusBarIcon


class JavaScriptIcon(StatusBarIcon):
    """
    Class implementing the JavaScript status bar icon.
    """

    def __init__(self, window):
        """
        Constructor

        @param window reference to the web browser window
        @type WebBrowserWindow
        """
        super().__init__(window)

        self.setToolTip(
            self.tr("Modify JavaScript settings temporarily for a site or globally")
        )
        self.__icon = EricPixmapCache.getPixmap("fileJavascript").scaled(16, 16)
        self.setPixmap(self.__icon)

        self.__settings = {}

        self._window.tabWidget().currentChanged.connect(self.__updateIcon)
        self._window.tabWidget().currentUrlChanged.connect(self.__updateIcon)
        self.clicked.connect(self.__showMenu)

        self.__updateIcon()

    def preferencesChanged(self):
        """
        Public method to handle changes of the settings.
        """
        self.__updateIcon()

    @pyqtSlot(QPoint)
    def __showMenu(self, pos):
        """
        Private slot to show the menu.

        @param pos position to show the menu at
        @type QPoint
        """
        boldFont = self.font()
        boldFont.setBold(True)

        menu = QMenu()
        menu.addAction(self.tr("Current Page Settings")).setFont(boldFont)

        act = (
            menu.addAction(
                self.tr("Disable JavaScript (temporarily)"), self.__toggleJavaScript
            )
            if self._testCurrentPageWebAttribute(
                QWebEngineSettings.WebAttribute.JavascriptEnabled
            )
            else menu.addAction(
                self.tr("Enable JavaScript (temporarily)"), self.__toggleJavaScript
            )
        )
        if (
            self._currentPage() is not None
            and self._currentPage().url().scheme() == "eric"
        ):
            # JavaScript is needed for eric: scheme
            act.setEnabled(False)

        menu.addSeparator()
        menu.addAction(self.tr("Global Settings")).setFont(boldFont)
        menu.addAction(
            self.tr("Manage JavaScript Settings"), self.__showJavaScriptSettingsDialog
        )
        menu.exec(pos)

    @pyqtSlot()
    def __updateIcon(self):
        """
        Private slot to update the icon.
        """
        if self._testCurrentPageWebAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled
        ):
            self.setGraphicsEffect(None)
        else:
            effect = QGraphicsColorizeEffect(self)
            effect.setColor(Qt.GlobalColor.gray)
            self.setGraphicsEffect(effect)

    @pyqtSlot()
    def __toggleJavaScript(self):
        """
        Private slot to toggle the JavaScript setting.
        """
        page = self._currentPage()
        if page is None:
            return

        current = self._testCurrentPageWebAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled
        )
        self._setCurrentPageWebAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled, not current
        )

        self.__settings[page] = not current
        page.navigationRequestAccepted.connect(
            lambda u, t, mf: self.__navigationRequestAccepted(u, t, mf, page)
        )

        self._window.currentBrowser().reload()

        self.__updateIcon()

    @pyqtSlot()
    def __showJavaScriptSettingsDialog(self):
        """
        Private slot to show the JavaScript settings dialog.

        Note: This is the JavaScript subset of the web browser configuration
        page.
        """
        from .JavaScriptSettingsDialog import JavaScriptSettingsDialog

        dlg = JavaScriptSettingsDialog(self._window)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._window.preferencesChanged()
            QTimer.singleShot(500, self.__updateIcon)

    def __navigationRequestAccepted(self, url, _navigationType, isMainFrame, page):
        """
        Private method to handle the navigationRequestAccepted signal.

        @param url URL being loaded
        @type QUrl
        @param _navigationType type of navigation request (unused)
        @type QWebEnginePage.NavigationType
        @param isMainFrame flag indicating a navigation request of the
            main frame
        @type bool
        @param page reference to the web page
        @type WebBrowserPage
        """
        enable = True if url.scheme() in ("eric", "qthelp") else self.__settings[page]
        if isMainFrame:
            page.settings().setAttribute(
                QWebEngineSettings.WebAttribute.JavascriptEnabled, enable
            )
