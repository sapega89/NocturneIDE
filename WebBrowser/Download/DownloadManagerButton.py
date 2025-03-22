# -*- coding: utf-8 -*-

# Copyright (c) 2018 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a tool button for the download manager.
"""

from PyQt6.QtCore import Qt, pyqtSlot

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricToolButton import EricToolButton
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow


class DownloadManagerButton(EricToolButton):
    """
    Class implementing a tool button for the download manager.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__manager = WebBrowserWindow.downloadManager()

        self.setObjectName("navigation_download_manager_button")
        self.setIcon(EricPixmapCache.getIcon("downloads"))
        self.setToolTip(self.tr("Open Download Manager"))
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoRaise(True)

        self.clicked.connect(self.__buttonClicked)
        self.__manager.downloadsCountChanged.connect(self.__updateState)

        self.__updateState()

    @pyqtSlot()
    def __buttonClicked(self):
        """
        Private slot handling a user clicking the button.
        """
        self.__manager.show()

    @pyqtSlot()
    def __updateState(self):
        """
        Private slot to update the button state.
        """
        self.setVisible(bool(self.__manager.downloadsCount()))
        count = self.__manager.activeDownloadsCount()
        if bool(count):
            self.setBadgeText(str(count))
        else:
            self.setBadgeText("")
