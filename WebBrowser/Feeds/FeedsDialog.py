# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to add RSS feeds.
"""

import functools

from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QDialog, QLabel, QPushButton

from eric7.EricGui import EricPixmapCache
from eric7.UI.NotificationWidget import NotificationTypes
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .Ui_FeedsDialog import Ui_FeedsDialog


class FeedsDialog(QDialog, Ui_FeedsDialog):
    """
    Class implementing a dialog to add RSS feeds.
    """

    def __init__(self, availableFeeds, browser, parent=None):
        """
        Constructor

        @param availableFeeds list of available RSS feeds
        @type list of [(str, str)]
        @param browser reference to the browser widget
        @type WebBrowserView
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.iconLabel.setPixmap(EricPixmapCache.getPixmap("rss48"))

        self.__browser = browser

        self.__availableFeeds = availableFeeds[:]
        for row in range(len(self.__availableFeeds)):
            feed = self.__availableFeeds[row]
            button = QPushButton(self)
            button.setText(self.tr("Add"))
            button.feed = feed
            label = QLabel(self)
            label.setText(feed[0])
            self.feedsLayout.addWidget(label, row, 0)
            self.feedsLayout.addWidget(button, row, 1)
            button.clicked.connect(functools.partial(self.__addFeed, button))

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __addFeed(self, button):
        """
        Private slot to add a RSS feed.

        @param button reference to the feed button
        @type QPushButton
        """
        urlString = button.feed[1]
        url = QUrl(urlString)
        if url.isRelative():
            url = self.__browser.url().resolved(url)
            urlString = url.toDisplayString(QUrl.ComponentFormattingOption.FullyDecoded)

        if not url.isValid():
            return

        title = button.feed[0] if button.feed[0] else self.__browser.url().host()

        feedsManager = WebBrowserWindow.feedsManager()
        if feedsManager.addFeed(urlString, title, self.__browser.icon()):
            WebBrowserWindow.showNotification(
                EricPixmapCache.getPixmap("rss48"),
                self.tr("Add RSS Feed"),
                self.tr("""The feed was added successfully."""),
            )
        else:
            WebBrowserWindow.showNotification(
                EricPixmapCache.getPixmap("rss48"),
                self.tr("Add RSS Feed"),
                self.tr("""The feed was already added before."""),
                kind=NotificationTypes.WARNING,
                timeout=0,
            )

        self.close()
