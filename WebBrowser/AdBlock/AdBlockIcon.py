# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the AdBlock icon for the main window status bar.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMenu

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricClickableLabel import EricClickableLabel


class AdBlockIcon(EricClickableLabel):
    """
    Class implementing the AdBlock icon for the main window status bar.
    """

    def __init__(self, parent):
        """
        Constructor

        @param parent reference to the parent widget
        @type WebBrowserWindow
        """
        super().__init__(parent)

        self.__mw = parent
        self.__menu = QMenu(self.tr("AdBlock"))
        self.__enabled = False

        self.setMaximumHeight(16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(
            self.tr("AdBlock lets you block unwanted content on web pages.")
        )

        self.__menu.aboutToShow.connect(self.__aboutToShowMenu)
        self.clicked.connect(self.__showMenu)

    def setEnabled(self, enabled):
        """
        Public slot to set the enabled state.

        @param enabled enabled state
        @type bool
        """
        self.__enabled = enabled
        if enabled:
            self.currentChanged()
        else:
            self.setPixmap(EricPixmapCache.getPixmap("adBlockPlusDisabled16"))

    def __aboutToShowMenu(self):
        """
        Private slot to show the context menu.
        """
        self.__menu.clear()

        manager = self.__mw.adBlockManager()

        if manager.isEnabled():
            act = self.__menu.addAction(
                EricPixmapCache.getIcon("adBlockPlusDisabled"),
                self.tr("Disable AdBlock"),
            )
            act.triggered.connect(lambda: self.__enableAdBlock(False))
        else:
            act = self.__menu.addAction(
                EricPixmapCache.getIcon("adBlockPlus"), self.tr("Enable AdBlock")
            )
            act.triggered.connect(lambda: self.__enableAdBlock(True))
        self.__menu.addSeparator()
        if manager.isEnabled() and self.__mw.currentBrowser().url().host():
            if self.__isCurrentHostExcepted():
                act = self.__menu.addAction(
                    EricPixmapCache.getIcon("adBlockPlus"),
                    self.tr("Remove AdBlock Exception"),
                )
                act.triggered.connect(lambda: self.__setException(False))
            else:
                act = self.__menu.addAction(
                    EricPixmapCache.getIcon("adBlockPlusGreen"),
                    self.tr("Add AdBlock Exception"),
                )
                act.triggered.connect(lambda: self.__setException(True))
        self.__menu.addAction(
            EricPixmapCache.getIcon("adBlockPlusGreen"),
            self.tr("AdBlock Exceptions..."),
            manager.showExceptionsDialog,
        )
        self.__menu.addSeparator()
        self.__menu.addAction(
            EricPixmapCache.getIcon("adBlockPlus"),
            self.tr("AdBlock Configuration..."),
            manager.showDialog,
        )

    def menu(self):
        """
        Public method to get a reference to the menu.

        @return reference to the menu
        @rtype QMenu
        """
        if self.__enabled:
            self.__menu.setIcon(EricPixmapCache.getIcon("adBlockPlus"))
        else:
            self.__menu.setIcon(EricPixmapCache.getIcon("adBlockPlusDisabled"))

        return self.__menu

    def __showMenu(self, pos):
        """
        Private slot to show the context menu.

        @param pos position the context menu should be shown
        @type QPoint
        """
        self.__menu.exec(pos)

    def __enableAdBlock(self, enable):
        """
        Private slot to enable or disable AdBlock.

        @param enable flag indicating the desired enable state
        @type bool
        """
        self.__mw.adBlockManager().setEnabled(enable)

    def __isCurrentHostExcepted(self):
        """
        Private method to check, if the host of the current browser is
        excepted.

        @return flag indicating an exception
        @rtype bool
        """
        browser = self.__mw.currentBrowser()
        if browser is None:
            return False

        urlHost = browser.page().url().host()

        return urlHost and self.__mw.adBlockManager().isHostExcepted(urlHost)

    def currentChanged(self):
        """
        Public slot to handle a change of the current browser tab.
        """
        if self.__enabled:
            if self.__isCurrentHostExcepted():
                self.setPixmap(EricPixmapCache.getPixmap("adBlockPlusGreen16"))
            else:
                self.setPixmap(EricPixmapCache.getPixmap("adBlockPlus16"))

    def __setException(self, enable):
        """
        Private slot to add or remove the current host from the list of
        exceptions.

        @param enable flag indicating to set or remove an exception
        @type bool
        """
        urlHost = self.__mw.currentBrowser().url().host()
        if enable:
            self.__mw.adBlockManager().addException(urlHost)
        else:
            self.__mw.adBlockManager().removeException(urlHost)
        self.currentChanged()

    def sourceChanged(self, browser, _url):
        """
        Public slot to handle URL changes.

        @param browser reference to the browser
        @type WebBrowserView
        @param _url new URL (unused)
        @type QUrl
        """
        if browser == self.__mw.currentBrowser():
            self.currentChanged()
