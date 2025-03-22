# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the images loading status bar icon.
"""

#
# This is modeled after the code found in Qupzilla
# Copyright (C) 2014  David Rosca <nowrep@gmail.com>
#

from PyQt6.QtCore import QPoint, Qt, pyqtSlot
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtWidgets import QGraphicsColorizeEffect, QMenu

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache

from .StatusBarIcon import StatusBarIcon


class ImagesIcon(StatusBarIcon):
    """
    Class implementing the images loading status bar icon.
    """

    def __init__(self, window):
        """
        Constructor

        @param window reference to the web browser window
        @type WebBrowserWindow
        """
        super().__init__(window)

        self.setToolTip(
            self.tr("Modify images loading settings temporarily or globally")
        )
        self.__icon = EricPixmapCache.getPixmap("filePixmap").scaled(16, 16)
        self.setPixmap(self.__icon)

        self._window.tabWidget().currentChanged.connect(self.__updateIcon)
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

        if self._testCurrentPageWebAttribute(
            QWebEngineSettings.WebAttribute.AutoLoadImages
        ):
            menu.addAction(
                self.tr("Disable loading images (temporarily)"),
                self.__toggleLoadingImages,
            )
        else:
            menu.addAction(
                self.tr("Enable loading images (temporarily)"),
                self.__toggleLoadingImages,
            )

        menu.addSeparator()
        menu.addAction(self.tr("Global Settings")).setFont(boldFont)
        act = menu.addAction(self.tr("Automatically load images"))
        act.setCheckable(True)
        act.setChecked(Preferences.getWebBrowser("AutoLoadImages"))
        act.toggled.connect(self.__setGlobalLoadingImages)

        menu.exec(pos)

    @pyqtSlot()
    def __updateIcon(self):
        """
        Private slot to update the icon.
        """
        if self._testCurrentPageWebAttribute(
            QWebEngineSettings.WebAttribute.AutoLoadImages
        ):
            self.setGraphicsEffect(None)
        else:
            effect = QGraphicsColorizeEffect(self)
            effect.setColor(Qt.GlobalColor.gray)
            self.setGraphicsEffect(effect)

    @pyqtSlot()
    def __toggleLoadingImages(self):
        """
        Private slot to toggle the images loading setting.
        """
        if self._currentPage() is None:
            return

        current = self._testCurrentPageWebAttribute(
            QWebEngineSettings.WebAttribute.AutoLoadImages
        )
        self._setCurrentPageWebAttribute(
            QWebEngineSettings.WebAttribute.AutoLoadImages, not current
        )

        if current:
            # reload page upon disabling loading images
            self._window.currentBrowser().reload()

        self.__updateIcon()

    @pyqtSlot(bool)
    def __setGlobalLoadingImages(self, enable):
        """
        Private slot to toggle the global images loading setting.

        @param enable flag indicating the state to set
        @type bool
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        WebBrowserWindow.webSettings().setAttribute(
            QWebEngineSettings.WebAttribute.AutoLoadImages, enable
        )
        Preferences.setWebBrowser("AutoLoadImages", enable)

        Preferences.syncPreferences()
        self._window.preferencesChanged()

        self.__updateIcon()

        if not enable:
            # reload page upon disabling loading images
            self._window.currentBrowser().reload()
