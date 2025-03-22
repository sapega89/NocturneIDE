# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the URL bar widget.
"""

from PyQt6.QtCore import QDateTime, QPoint, Qt, QTimer, QUrl, pyqtSlot
from PyQt6.QtGui import QColor, QIcon, QPalette
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWidgets import QApplication, QDialog, QLineEdit

try:
    from PyQt6.QtNetwork import QSslCertificate  # __IGNORE_EXCEPTION__
except ImportError:
    QSslCertificate = None  # __IGNORE_WARNING__

from eric7 import EricUtilities, Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricLineEdit import EricClearableLineEdit, EricLineEditSide
from eric7.WebBrowser.SafeBrowsing.SafeBrowsingLabel import SafeBrowsingLabel
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .FavIconLabel import FavIconLabel
from .SslLabel import SslLabel


class UrlBar(EricClearableLineEdit):
    """
    Class implementing a line edit for entering URLs.
    """

    def __init__(self, mainWindow, parent=None):
        """
        Constructor

        @param mainWindow reference to the main window
        @type WebBrowserWindow
        @param parent reference to the parent widget
        @type WebBrowserView
        """
        super().__init__(parent)
        self.setPlaceholderText(self.tr("Enter the URL here."))
        self.setWhatsThis(self.tr("Enter the URL here."))

        self.__mw = mainWindow
        self.__browser = None
        self.__privateMode = WebBrowserWindow.isPrivate()

        self.__bmActiveIcon = EricPixmapCache.getIcon("bookmark16")
        self.__bmInactiveIcon = QIcon(
            self.__bmActiveIcon.pixmap(16, 16, QIcon.Mode.Disabled)
        )

        self.__safeBrowsingLabel = SafeBrowsingLabel(self)
        self.addWidget(self.__safeBrowsingLabel, EricLineEditSide.LEFT)
        self.__safeBrowsingLabel.setVisible(False)

        self.__favicon = FavIconLabel(self)
        self.addWidget(self.__favicon, EricLineEditSide.LEFT)

        self.__sslLabel = SslLabel(self)
        self.addWidget(self.__sslLabel, EricLineEditSide.LEFT)
        self.__sslLabel.setVisible(False)

        self.__rssAction = self.addAction(
            EricPixmapCache.getIcon("rss16"), QLineEdit.ActionPosition.TrailingPosition
        )
        self.__rssAction.setVisible(False)

        self.__bookmarkAction = self.addAction(
            self.__bmInactiveIcon, QLineEdit.ActionPosition.TrailingPosition
        )
        self.__bookmarkAction.setVisible(False)

        self.__safeBrowsingLabel.clicked.connect(self.__showThreatInfo)
        self.__bookmarkAction.triggered.connect(self.__showBookmarkInfo)
        self.__rssAction.triggered.connect(self.__rssTriggered)

        self.__mw.bookmarksManager().entryChanged.connect(self.__bookmarkChanged)
        self.__mw.bookmarksManager().entryAdded.connect(self.__bookmarkChanged)
        self.__mw.bookmarksManager().entryRemoved.connect(self.__bookmarkChanged)
        self.__mw.speedDial().pagesChanged.connect(self.__bookmarkChanged)

    def setBrowser(self, browser):
        """
        Public method to set the browser connection.

        @param browser reference to the browser widget
        @type WebBrowserView
        """
        self.__browser = browser
        self.__favicon.setBrowser(browser)

        self.__browser.urlChanged.connect(self.__browserUrlChanged)
        self.__browser.loadProgress.connect(self.__loadProgress)
        self.__browser.loadFinished.connect(self.__loadFinished)
        self.__browser.loadStarted.connect(self.__loadStarted)

        self.__browser.safeBrowsingBad.connect(self.__safeBrowsingLabel.setThreatInfo)

        self.__sslLabel.clicked.connect(self.__browser.page().showSslInfo)
        self.__browser.page().sslConfigurationChanged.connect(
            self.__sslConfigurationChanged
        )

    def browser(self):
        """
        Public method to get the associated browser.

        @return reference to the associated browser
        @rtype WebBrowserView
        """
        return self.__browser

    @pyqtSlot(QUrl)
    def __browserUrlChanged(self, url):
        """
        Private slot to handle a URL change of the associated browser.

        @param url new URL of the browser
        @type QUrl
        """
        strUrl = url.toString()
        if strUrl in ["eric:speeddial", "eric:home", "about:blank", "about:config"]:
            strUrl = ""

        if self.text() != strUrl:
            self.setText(strUrl)
        self.setCursorPosition(0)

    @pyqtSlot()
    def __checkBookmark(self):
        """
        Private slot to check the current URL for the bookmarked state.
        """
        from eric7.WebBrowser.Bookmarks.BookmarkNode import BookmarkTimestampType

        manager = self.__mw.bookmarksManager()
        if manager.bookmarkForUrl(self.__browser.url()) is not None:
            self.__bookmarkAction.setIcon(self.__bmActiveIcon)
            bookmarks = manager.bookmarksForUrl(self.__browser.url())
            for bookmark in bookmarks:
                manager.setTimestamp(
                    bookmark, BookmarkTimestampType.Visited, QDateTime.currentDateTime()
                )
        elif self.__mw.speedDial().pageForUrl(self.__browser.url()).url != "":
            self.__bookmarkAction.setIcon(self.__bmActiveIcon)
        else:
            self.__bookmarkAction.setIcon(self.__bmInactiveIcon)

    @pyqtSlot()
    def __loadStarted(self):
        """
        Private slot to perform actions before the page is loaded.
        """
        self.__bookmarkAction.setVisible(False)
        self.__rssAction.setVisible(False)
        self.__sslLabel.setVisible(False)

    @pyqtSlot(int)
    def __loadProgress(self, progress):
        """
        Private slot to track the load progress.

        @param progress load progress in percent
        @type int
        """
        foregroundColor = QApplication.palette().color(QPalette.ColorRole.Text)

        backgroundColor = (
            Preferences.getWebBrowser("PrivateModeUrlColor")
            if self.__privateMode
            else QApplication.palette().color(QPalette.ColorRole.Base)
        )

        if not self.__browser.getSafeBrowsingStatus():
            # malicious web site
            backgroundColor = Preferences.getWebBrowser("MaliciousUrlColor")
        elif self.__browser.url().scheme() == "https":
            if WebBrowserWindow.networkManager().isInsecureHost(
                self.__browser.url().host()
            ):
                backgroundColor = Preferences.getWebBrowser("InsecureUrlColor")
            else:
                backgroundColor = Preferences.getWebBrowser("SecureUrlColor")

        if progress in (0, 100):
            styleSheet = (
                f"color: {foregroundColor.name()}; "
                f"background-color: {backgroundColor.name()};"
            )
        else:
            highlight = QApplication.palette().color(QPalette.ColorRole.Highlight)
            r = (highlight.red() + 2 * backgroundColor.red()) // 3
            g = (highlight.green() + 2 * backgroundColor.green()) // 3
            b = (highlight.blue() + 2 * backgroundColor.blue()) // 3

            loadingColor = QColor(r, g, b)
            if abs(loadingColor.lightness() - backgroundColor.lightness()) < 20:
                r = (2 * highlight.red() + backgroundColor.red()) // 3
                g = (2 * highlight.green() + backgroundColor.green()) // 3
                b = (2 * highlight.blue() + backgroundColor.blue()) // 3
                loadingColor = QColor(r, g, b)

            styleSheet = (
                f"color: {foregroundColor.name()}; "
                f"background-color: qlineargradient("
                f"spread: pad, x1: 0, y1: 0, x2: 1, y2: 0, "
                f"stop: 0 {loadingColor.name()}, "
                f"stop: {progress / 100.0 - 0.001} {loadingColor.name()}, "
                f"stop: {progress / 100.0 + 0.001} {backgroundColor.name()}, "
                f"stop: 1 {backgroundColor.name()});"
            )

        self.setStyleSheet(styleSheet)
        self.repaint()

    @pyqtSlot(bool)
    def __loadFinished(self, ok):
        """
        Private slot to set some data after the page was loaded.

        @param ok flag indicating a successful load
        @type bool
        """
        if self.__browser.url().scheme() in ["eric", "about"]:
            self.__bookmarkAction.setVisible(False)
        else:
            self.__checkBookmark()
            self.__bookmarkAction.setVisible(True)

        self.__browserUrlChanged(self.__browser.url())
        self.__safeBrowsingLabel.setVisible(not self.__browser.getSafeBrowsingStatus())

        if ok:
            QTimer.singleShot(0, self.__setRssButton)

    @pyqtSlot()
    def preferencesChanged(self):
        """
        Public slot to handle a change of preferences.
        """
        self.update()

    @pyqtSlot()
    def __showBookmarkInfo(self):
        """
        Private slot to show a dialog with some bookmark info.
        """
        from .BookmarkActionSelectionDialog import (
            BookmarkAction,
            BookmarkActionSelectionDialog,
        )
        from .BookmarkInfoDialog import BookmarkInfoDialog

        url = self.__browser.url()
        dlg = BookmarkActionSelectionDialog(url, parent=self.__browser)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            action = dlg.getAction()
            if action == BookmarkAction.AddBookmark:
                self.__browser.addBookmark()
            elif action == BookmarkAction.EditBookmark:
                bookmark = self.__mw.bookmarksManager().bookmarkForUrl(url)
                dlg = BookmarkInfoDialog(bookmark, self.__browser)
                dlg.exec()
            elif action == BookmarkAction.AddSpeeddial:
                self.__mw.speedDial().addPage(url, self.__browser.title())
            elif action == BookmarkAction.RemoveSpeeddial:
                self.__mw.speedDial().removePage(url)

    @pyqtSlot()
    def __bookmarkChanged(self):
        """
        Private slot to handle bookmark or speed dial changes.
        """
        self.__checkBookmark()

    def focusOutEvent(self, evt):
        """
        Protected method to handle focus out event.

        @param evt reference to the focus event
        @type QFocusEvent
        """
        if self.text() == "" and self.__browser is not None:
            self.__browserUrlChanged(self.__browser.url())
        super().focusOutEvent(evt)

    def mousePressEvent(self, evt):
        """
        Protected method called by a mouse press event.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.XButton1:
            self.__mw.currentBrowser().triggerPageAction(QWebEnginePage.WebAction.Back)
        elif evt.button() == Qt.MouseButton.XButton2:
            self.__mw.currentBrowser().triggerPageAction(
                QWebEnginePage.WebAction.Forward
            )
        else:
            super().mousePressEvent(evt)

    def mouseDoubleClickEvent(self, evt):
        """
        Protected method to handle mouse double click events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.LeftButton:
            self.selectAll()
        else:
            super().mouseDoubleClickEvent(evt)

    def keyPressEvent(self, evt):
        """
        Protected method to handle key presses.

        @param evt reference to the key press event
        @type QKeyEvent
        """
        if evt.key() == Qt.Key.Key_Escape:
            if self.__browser is not None:
                self.setText(str(self.__browser.url().toEncoded(), encoding="utf-8"))
                self.selectAll()
            completer = self.completer()
            if completer:
                completer.popup().hide()
            return

        currentText = self.text().strip()
        if evt.key() in [
            Qt.Key.Key_Enter,
            Qt.Key.Key_Return,
        ] and not currentText.lower().startswith(("http://", "https://")):
            append = ""
            if evt.modifiers() == Qt.KeyboardModifier.ControlModifier:
                append = ".com"
            elif evt.modifiers() == (
                Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
            ):
                append = ".org"
            elif evt.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                append = ".net"

            if append != "":
                url = QUrl("http://www." + currentText)
                host = url.host()
                if not host.lower().endswith(append):
                    host += append
                    url.setHost(host)
                    self.setText(url.toString())

        super().keyPressEvent(evt)

    def dragEnterEvent(self, evt):
        """
        Protected method to handle drag enter events.

        @param evt reference to the drag enter event
        @type QDragEnterEvent
        """
        mimeData = evt.mimeData()
        if mimeData.hasUrls() or mimeData.hasText():
            evt.acceptProposedAction()

        super().dragEnterEvent(evt)

    def dropEvent(self, evt):
        """
        Protected method to handle drop events.

        @param evt reference to the drop event
        @type QDropEvent
        """
        mimeData = evt.mimeData()

        url = QUrl()
        if mimeData.hasUrls():
            url = mimeData.urls()[0]
        elif mimeData.hasText():
            url = QUrl.fromEncoded(
                mimeData.text().encode("utf-8"), QUrl.ParsingMode.TolerantMode
            )

        if url.isEmpty() or not url.isValid():
            super().dropEvent(evt)
            return

        self.setText(str(url.toEncoded(), encoding="utf-8"))
        self.selectAll()

        evt.acceptProposedAction()

    @pyqtSlot()
    def __setRssButton(self):
        """
        Private slot to show the RSS button.
        """
        self.__rssAction.setVisible(self.__browser.checkRSS())

    @pyqtSlot()
    def __rssTriggered(self):
        """
        Private slot to handle clicking the RSS icon.
        """
        from eric7.WebBrowser.Feeds.FeedsDialog import FeedsDialog

        feeds = self.__browser.getRSS()
        dlg = FeedsDialog(feeds, self.__browser, parent=self.__browser)
        dlg.exec()

    @pyqtSlot(QPoint)
    def __showThreatInfo(self, pos):
        """
        Private slot to show the threat info widget.

        @param pos position to show the info at
        @type QPoint
        """
        from eric7.WebBrowser.SafeBrowsing.SafeBrowsingInfoWidget import (
            SafeBrowsingInfoWidget,
        )

        threatInfo = self.__safeBrowsingLabel.getThreatInfo()
        if threatInfo:
            widget = SafeBrowsingInfoWidget(threatInfo, self.__browser)
            widget.showAt(pos)

    @pyqtSlot()
    def __sslConfigurationChanged(self):
        """
        Private slot to handle a change of the associated web page SSL
        configuration.
        """
        sslConfiguration = self.__browser.page().getSslConfiguration()
        if sslConfiguration is not None and QSslCertificate is not None:
            sslCertificate = self.__browser.page().getSslCertificate()
            if sslCertificate is not None:
                org = EricUtilities.decodeString(
                    ", ".join(
                        sslCertificate.subjectInfo(
                            QSslCertificate.SubjectInfo.Organization
                        )
                    )
                )
                if org == "":
                    cn = EricUtilities.decodeString(
                        ", ".join(
                            sslCertificate.subjectInfo(
                                QSslCertificate.SubjectInfo.CommonName
                            )
                        )
                    )
                    if cn != "":
                        org = cn.split(".", 1)[1]
                    if org == "":
                        org = self.tr("Unknown")
                self.__sslLabel.setText(" {0} ".format(org))
                self.__sslLabel.setVisible(True)
                valid = not sslCertificate.isBlacklisted()
                if valid:
                    config = self.__browser.page().getSslConfiguration()
                    if config is None or config.sessionCipher().isNull():
                        valid = False
                self.__sslLabel.setValidity(valid)
            else:
                self.__sslLabel.setVisible(False)
        else:
            self.__sslLabel.setVisible(False)
