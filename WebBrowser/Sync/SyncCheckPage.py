# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the synchronization status wizard page.
"""

from PyQt6.QtCore import QTimer, pyqtSlot
from PyQt6.QtWidgets import QWizardPage

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from . import SyncGlobals
from .Ui_SyncCheckPage import Ui_SyncCheckPage


class SyncCheckPage(QWizardPage, Ui_SyncCheckPage):
    """
    Class implementing the synchronization status wizard page.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

    def initializePage(self):
        """
        Public method to initialize the page.
        """
        self.syncErrorLabel.hide()

        forceUpload = self.field("ReencryptData")

        syncMgr = WebBrowserWindow.syncManager()
        syncMgr.syncError.connect(self.__syncError)
        syncMgr.syncStatus.connect(self.__updateMessages)
        syncMgr.syncFinished.connect(self.__updateLabels)

        if Preferences.getWebBrowser("SyncType") == SyncGlobals.SyncTypeFtp:
            self.handlerLabel.setText(self.tr("FTP"))
            self.infoLabel.setText(self.tr("Host:"))
            self.infoDataLabel.setText(Preferences.getWebBrowser("SyncFtpServer"))
        elif Preferences.getWebBrowser("SyncType") == SyncGlobals.SyncTypeDirectory:
            self.handlerLabel.setText(self.tr("Shared Directory"))
            self.infoLabel.setText(self.tr("Directory:"))
            self.infoDataLabel.setText(Preferences.getWebBrowser("SyncDirectoryPath"))
        else:
            self.handlerLabel.setText(self.tr("No Synchronization"))
            self.hostLabel.setText("")

        self.bookmarkMsgLabel.setText("")
        self.historyMsgLabel.setText("")
        self.passwordsMsgLabel.setText("")
        self.userAgentsMsgLabel.setText("")
        self.speedDialMsgLabel.setText("")

        if not syncMgr.syncEnabled():
            self.bookmarkLabel.setPixmap(EricPixmapCache.getPixmap("syncNo"))
            self.historyLabel.setPixmap(EricPixmapCache.getPixmap("syncNo"))
            self.passwordsLabel.setPixmap(EricPixmapCache.getPixmap("syncNo"))
            self.userAgentsLabel.setPixmap(EricPixmapCache.getPixmap("syncNo"))
            self.speedDialLabel.setPixmap(EricPixmapCache.getPixmap("syncNo"))
            return

        # bookmarks
        if Preferences.getWebBrowser("SyncBookmarks"):
            self.__makeAnimatedLabel("loadingAnimation", self.bookmarkLabel)
        else:
            self.bookmarkLabel.setPixmap(EricPixmapCache.getPixmap("syncNo"))

        # history
        if Preferences.getWebBrowser("SyncHistory"):
            self.__makeAnimatedLabel("loadingAnimation", self.historyLabel)
        else:
            self.historyLabel.setPixmap(EricPixmapCache.getPixmap("syncNo"))

        # Passwords
        if Preferences.getWebBrowser("SyncPasswords"):
            self.__makeAnimatedLabel("loadingAnimation", self.passwordsLabel)
        else:
            self.passwordsLabel.setPixmap(EricPixmapCache.getPixmap("syncNo"))

        # user agent settings
        if Preferences.getWebBrowser("SyncUserAgents"):
            self.__makeAnimatedLabel("loadingAnimation", self.userAgentsLabel)
        else:
            self.userAgentsLabel.setPixmap(EricPixmapCache.getPixmap("syncNo"))

        # speed dial settings
        if Preferences.getWebBrowser("SyncSpeedDial"):
            self.__makeAnimatedLabel("loadingAnimation", self.speedDialLabel)
        else:
            self.speedDialLabel.setPixmap(EricPixmapCache.getPixmap("syncNo"))

        QTimer.singleShot(0, lambda: syncMgr.loadSettings(forceUpload=forceUpload))

    def __makeAnimatedLabel(self, fileName, label):
        """
        Private slot to create an animated label.

        @param fileName name of the file containing the animation
        @type str
        @param label reference to the label to be animated
        @type EricAnimatedLabel
        """
        label.setInterval(40)
        label.setAnimationFile(fileName)
        label.start()

    def __updateMessages(self, type_, msg):
        """
        Private slot to update the synchronization status info.

        @param type_ type of synchronization data
        @type str
        @param msg synchronization message
        @type str
        """
        if type_ == "bookmarks":
            self.bookmarkMsgLabel.setText(msg)
        elif type_ == "history":
            self.historyMsgLabel.setText(msg)
        elif type_ == "passwords":
            self.passwordsMsgLabel.setText(msg)
        elif type_ == "useragents":
            self.userAgentsMsgLabel.setText(msg)
        elif type_ == "speeddial":
            self.speedDialMsgLabel.setText(msg)

    @pyqtSlot(str, bool, bool)
    def __updateLabels(self, type_, status, _download):
        """
        Private slot to handle a finished synchronization event.

        @param type_ type of the synchronization event (one of "bookmarks",
            "history", "passwords", "useragents" or "speeddial")
        @type str
        @param status flag indicating success
        @type bool
        @param _download flag indicating a download of a file (unused)
        @type bool
        """
        if type_ == "bookmarks":
            if status:
                self.bookmarkLabel.setPixmap(EricPixmapCache.getPixmap("syncCompleted"))
            else:
                self.bookmarkLabel.setPixmap(EricPixmapCache.getPixmap("syncFailed"))
        elif type_ == "history":
            if status:
                self.historyLabel.setPixmap(EricPixmapCache.getPixmap("syncCompleted"))
            else:
                self.historyLabel.setPixmap(EricPixmapCache.getPixmap("syncFailed"))
        elif type_ == "passwords":
            if status:
                self.passwordsLabel.setPixmap(
                    EricPixmapCache.getPixmap("syncCompleted")
                )
            else:
                self.passwordsLabel.setPixmap(EricPixmapCache.getPixmap("syncFailed"))
        elif type_ == "useragents":
            if status:
                self.userAgentsLabel.setPixmap(
                    EricPixmapCache.getPixmap("syncCompleted")
                )
            else:
                self.userAgentsLabel.setPixmap(EricPixmapCache.getPixmap("syncFailed"))
        elif type_ == "speeddial":
            if status:
                self.speedDialLabel.setPixmap(
                    EricPixmapCache.getPixmap("syncCompleted")
                )
            else:
                self.speedDialLabel.setPixmap(EricPixmapCache.getPixmap("syncFailed"))

    def __syncError(self, message):
        """
        Private slot to handle general synchronization issues.

        @param message error message
        @type str
        """
        self.syncErrorLabel.show()
        self.syncErrorLabel.setText(
            self.tr('<font color="#FF0000"><b>Error:</b> {0}</font>').format(message)
        )
