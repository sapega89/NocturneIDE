# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the download manager class.
"""

import enum

from PyQt6.QtCore import (
    QBasicTimer,
    QFileInfo,
    QModelIndex,
    QPoint,
    Qt,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QCursor, QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QDialog, QFileIconProvider, QMenu, QStyle

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import OSUtilities
from eric7.Utilities.AutoSaver import AutoSaver
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .DownloadModel import DownloadModel
from .DownloadUtilities import speedString, timeString
from .Ui_DownloadManager import Ui_DownloadManager


class DownloadManagerRemovePolicy(enum.Enum):
    """
    Class defining the remove policies.
    """

    Never = 0
    Exit = 1
    SuccessfullDownload = 2


DownloadManagerDefaultRemovePolicy = DownloadManagerRemovePolicy.Never


class DownloadManager(QDialog, Ui_DownloadManager):
    """
    Class implementing the download manager.

    @signal downloadsCountChanged() emitted to indicate a change of the
        count of download items
    """

    UpdateTimerTimeout = 1000

    downloadsCountChanged = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.__winTaskbarButton = None

        self.__saveTimer = AutoSaver(self, self.save)

        self.__model = DownloadModel(self)
        self.__manager = WebBrowserWindow.networkManager()

        self.__iconProvider = None
        self.__downloads = []
        self.__downloadDirectory = ""
        self.__loaded = False

        self.__rowHeightMultiplier = 1.1

        self.setDownloadDirectory(Preferences.getUI("DownloadPath"))

        self.downloadsView.setShowGrid(False)
        self.downloadsView.verticalHeader().hide()
        self.downloadsView.horizontalHeader().hide()
        self.downloadsView.setAlternatingRowColors(True)
        self.downloadsView.horizontalHeader().setStretchLastSection(True)
        self.downloadsView.setModel(self.__model)
        self.downloadsView.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.downloadsView.customContextMenuRequested.connect(
            self.__customContextMenuRequested
        )

        self.__clearShortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        self.__clearShortcut.activated.connect(self.on_cleanupButton_clicked)

        self.__load()

        self.__updateTimer = QBasicTimer()

    @pyqtSlot(QPoint)
    def __customContextMenuRequested(self, pos):
        """
        Private slot to handle the context menu request for the bookmarks tree.

        @param pos position the context menu was requested
        @type QPoint
        """
        menu = QMenu()

        selectedRowsCount = len(self.downloadsView.selectionModel().selectedRows())

        if selectedRowsCount == 1:
            row = self.downloadsView.selectionModel().selectedRows()[0].row()
            itm = self.__downloads[row]
            if itm.exists():
                menu.addAction(
                    EricPixmapCache.getIcon("open"),
                    self.tr("Open"),
                    self.__contextMenuOpen,
                )
            elif itm.downloading():
                menu.addAction(
                    EricPixmapCache.getIcon("stopLoading"),
                    self.tr("Cancel"),
                    self.__contextMenuCancel,
                )
                menu.addSeparator()
            menu.addAction(
                self.tr("Open Containing Folder"), self.__contextMenuOpenFolder
            )
            menu.addSeparator()
            menu.addAction(self.tr("Go to Download Page"), self.__contextMenuGotoPage)
            menu.addAction(self.tr("Copy Download Link"), self.__contextMenuCopyLink)
            menu.addSeparator()
        menu.addAction(self.tr("Select All"), self.__contextMenuSelectAll)
        if selectedRowsCount > 1 or (
            selectedRowsCount == 1
            and not self.__downloads[
                self.downloadsView.selectionModel().selectedRows()[0].row()
            ].downloading()
        ):
            menu.addSeparator()
            menu.addAction(
                self.tr("Remove From List"), self.__contextMenuRemoveSelected
            )

        menu.exec(QCursor.pos())

    def shutdown(self):
        """
        Public method to stop the download manager.
        """
        self.save()
        self.close()

    def activeDownloadsCount(self):
        """
        Public method to get the number of active downloads.

        @return number of active downloads
        @rtype int
        """
        count = 0

        for download in self.__downloads:
            if download.downloading():
                count += 1
        return count

    def allowQuit(self):
        """
        Public method to check, if it is ok to quit.

        @return flag indicating allowance to quit
        @rtype bool
        """
        if self.activeDownloadsCount() > 0:
            res = EricMessageBox.yesNo(
                self,
                self.tr(""),
                self.tr(
                    """There are %n downloads in progress.\n"""
                    """Do you want to quit anyway?""",
                    "",
                    self.activeDownloadsCount(),
                ),
                icon=EricMessageBox.Warning,
            )
            if not res:
                self.show()
                return False

        self.close()
        return True

    def __testWebBrowserView(self, view, url):
        """
        Private method to test a web browser view against an URL.

        @param view reference to the web browser view to be tested
        @type WebBrowserView
        @param url URL to test against
        @type QUrl
        @return flag indicating, that the view is the one for the URL
        @rtype bool
        """
        if view.tabWidget().count() < 2:
            return False

        page = view.page()
        if page.history().count() != 0:
            return False

        if not page.url().isEmpty() and page.url().host() == url.host():
            return True

        requestedUrl = page.requestedUrl()
        if requestedUrl.isEmpty():
            requestedUrl = QUrl(view.tabWidget().urlBarForView(view).text())
        return requestedUrl.isEmpty() or requestedUrl.host() == url.host()

    def __closeDownloadTab(self, url):
        """
        Private method to close an empty tab, that was opened only for loading
        the download URL.

        @param url download URL
        @type QUrl
        """
        if self.__testWebBrowserView(
            WebBrowserWindow.getWindow().currentBrowser(), url
        ):
            WebBrowserWindow.getWindow().closeCurrentBrowser()
            return

        for window in WebBrowserWindow.mainWindows():
            for browser in window.browsers():
                if self.__testWebBrowserView(browser, url):
                    window.closeBrowser(browser)
                    return

    def download(self, downloadRequest):
        """
        Public method to download a file.

        @param downloadRequest reference to the download object containing the
        download data.
        @type QWebEngineDownloadRequest
        """
        from eric7.WebBrowser.SafeBrowsing.SafeBrowsingManager import (
            SafeBrowsingManager,
        )

        from .DownloadItem import DownloadItem

        url = downloadRequest.url()
        if url.isEmpty():
            return

        self.__closeDownloadTab(url)

        # Safe Browsing
        if SafeBrowsingManager.isEnabled():
            threatLists = WebBrowserWindow.safeBrowsingManager().lookupUrl(url)[0]
            if threatLists:
                threatMessages = (
                    WebBrowserWindow.safeBrowsingManager().getThreatMessages(
                        threatLists
                    )
                )
                res = EricMessageBox.warning(
                    WebBrowserWindow.getWindow(),
                    self.tr("Suspicuous URL detected"),
                    self.tr(
                        "<p>The URL <b>{0}</b> was found in the Safe"
                        " Browsing database.</p>{1}"
                    ).format(url.toString(), "".join(threatMessages)),
                    EricMessageBox.Abort | EricMessageBox.Ignore,
                    EricMessageBox.Abort,
                )
                if res == EricMessageBox.Abort:
                    downloadRequest.cancel()
                    return

        window = WebBrowserWindow.getWindow()
        pageUrl = window.currentBrowser().url() if window else QUrl()
        itm = DownloadItem(
            downloadRequest=downloadRequest, pageUrl=pageUrl, parent=self
        )
        self.__addItem(itm)

        if Preferences.getWebBrowser("DownloadManagerAutoOpen"):
            self.show()
        else:
            self.__startUpdateTimer()

    def show(self):
        """
        Public slot to show the download manager dialog.
        """
        self.__startUpdateTimer()

        for itm in self.__downloads:
            itm.updateButtonsAndLabels()

        super().show()
        self.activateWindow()
        self.raise_()

    def __addItem(self, itm, append=False):
        """
        Private method to add a download to the list of downloads.

        @param itm reference to the download item
        @type DownloadItem
        @param append flag indicating to append the item
        @type bool
        """
        itm.statusChanged.connect(lambda: self.__updateRow(itm))
        itm.downloadFinished.connect(self.__finished)

        # insert at top of window
        row = self.downloadsCount() if append else 0
        self.__model.beginInsertRows(QModelIndex(), row, row)
        if append:
            self.__downloads.append(itm)
        else:
            self.__downloads.insert(0, itm)
        self.__model.endInsertRows()

        self.downloadsView.setIndexWidget(self.__model.index(row, 0), itm)
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        itm.setIcon(icon)
        self.downloadsView.setRowHeight(
            row, int(itm.sizeHint().height() * self.__rowHeightMultiplier)
        )
        # just in case the download finished before the constructor returned
        self.__updateRow(itm)
        self.changeOccurred()

        self.downloadsCountChanged.emit()

    def __updateRow(self, itm):
        """
        Private slot to update a download item.

        @param itm reference to the download item
        @type DownloadItem
        """
        if itm not in self.__downloads:
            return

        row = self.__downloads.index(itm)

        if self.__iconProvider is None:
            self.__iconProvider = QFileIconProvider()

        icon = self.__iconProvider.icon(QFileInfo(itm.fileName()))
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        itm.setIcon(icon)

        self.downloadsView.setRowHeight(
            row, int(itm.minimumSizeHint().height() * self.__rowHeightMultiplier)
        )

        remove = False

        if (
            itm.downloadedSuccessfully()
            and self.removePolicy() == DownloadManagerRemovePolicy.SuccessfullDownload
        ):
            remove = True

        if remove:
            self.__model.removeRow(row)

        self.cleanupButton.setEnabled(
            (self.downloadsCount() - self.activeDownloadsCount()) > 0
        )

        # record the change
        self.changeOccurred()

    def removePolicy(self):
        """
        Public method to get the remove policy.

        @return remove policy
        @rtype DownloadManagerRemovePolicy
        """
        try:
            return DownloadManagerRemovePolicy(
                Preferences.getWebBrowser("DownloadManagerRemovePolicy")
            )
        except ValueError:
            # default value
            return DownloadManagerDefaultRemovePolicy

    def setRemovePolicy(self, policy):
        """
        Public method to set the remove policy.

        @param policy remove policy to be set
        @type DownloadManagerRemovePolicy
        """
        if policy == self.removePolicy():
            return

        Preferences.setWebBrowser("DownloadManagerRemovePolicy", self.policy.value)

    def save(self):
        """
        Public method to save the download settings.
        """
        if not self.__loaded:
            return

        Preferences.setWebBrowser("DownloadManagerSize", self.size())
        Preferences.setWebBrowser("DownloadManagerPosition", self.pos())
        if self.removePolicy() == DownloadManagerRemovePolicy.Exit:
            return

        if WebBrowserWindow.isPrivate():
            return

        downloads = []
        for download in self.__downloads:
            downloads.append(download.getData())
        Preferences.setWebBrowser("DownloadManagerDownloads", downloads)

    def __load(self):
        """
        Private method to load the download settings.
        """
        from .DownloadItem import DownloadItem

        if self.__loaded:
            return

        size = Preferences.getWebBrowser("DownloadManagerSize")
        if size.isValid():
            self.resize(size)
        pos = Preferences.getWebBrowser("DownloadManagerPosition")
        self.move(pos)

        if not WebBrowserWindow.isPrivate():
            downloads = Preferences.getWebBrowser("DownloadManagerDownloads")
            for download in downloads:
                if not download["URL"].isEmpty() and bool(download["Location"]):
                    itm = DownloadItem(parent=self)
                    itm.setData(download)
                    self.__addItem(itm, append=True)
            self.cleanupButton.setEnabled(
                (self.downloadsCount() - self.activeDownloadsCount()) > 0
            )

        self.__loaded = True

        self.downloadsCountChanged.emit()

    def closeEvent(self, evt):
        """
        Protected event handler for the close event.

        @param evt reference to the close event
        @type QCloseEvent
        """
        self.save()

    def cleanup(self):
        """
        Public slot to cleanup the downloads.
        """
        self.on_cleanupButton_clicked()

    @pyqtSlot()
    def on_cleanupButton_clicked(self):
        """
        Private slot to cleanup the downloads.
        """
        if self.downloadsCount() == 0:
            return

        self.__model.removeRows(0, self.downloadsCount())
        if self.downloadsCount() == 0 and self.__iconProvider is not None:
            self.__iconProvider = None

        self.changeOccurred()

        self.downloadsCountChanged.emit()

    def __finished(self, success):
        """
        Private slot to handle a finished download.

        @param success flag indicating a successful download
        @type bool
        """
        if self.isVisible():
            QApplication.alert(self)

        self.downloadsCountChanged.emit()

        if self.activeDownloadsCount() == 0:
            # all active downloads are done
            if success and ericApp().activeWindow() is not self:
                WebBrowserWindow.showNotification(
                    EricPixmapCache.getPixmap("downloads48"),
                    self.tr("Downloads finished"),
                    self.tr("All files have been downloaded."),
                )
                if not Preferences.getWebBrowser("DownloadManagerAutoClose"):
                    self.raise_()
                    self.activateWindow()

            self.__stopUpdateTimer()
            self.infoLabel.clear()
            self.setWindowTitle(self.tr("Download Manager"))
            if OSUtilities.isWindowsPlatform():
                self.__taskbarButton().progress().hide()

            if Preferences.getWebBrowser("DownloadManagerAutoClose"):
                self.close()

    def setDownloadDirectory(self, directory):
        """
        Public method to set the current download directory.

        @param directory current download directory
        @type str
        """
        self.__downloadDirectory = directory
        if self.__downloadDirectory != "":
            self.__downloadDirectory += "/"

    def downloadDirectory(self):
        """
        Public method to get the current download directory.

        @return current download directory
        @rtype str
        """
        return self.__downloadDirectory

    def downloadsCount(self):
        """
        Public method to get the number of downloads.

        @return number of downloads
        @rtype int
        """
        return len(self.__downloads)

    def downloads(self):
        """
        Public method to get a reference to the downloads.

        @return reference to the downloads
        @rtype list of DownloadItem
        """
        return self.__downloads

    def changeOccurred(self):
        """
        Public method to signal a change.
        """
        self.__saveTimer.changeOccurred()

    def __taskbarButton(self):
        """
        Private method to get a reference to the task bar button (Windows
        only).

        @return reference to the task bar button
        @rtype QWinTaskbarButton or None
        """
        if OSUtilities.isWindowsPlatform():
            from PyQt6.QtWinExtras import QWinTaskbarButton  # __IGNORE_WARNING_I10__

            if self.__winTaskbarButton is None:
                window = WebBrowserWindow.mainWindow()
                self.__winTaskbarButton = QWinTaskbarButton(window.windowHandle())
                self.__winTaskbarButton.progress().setRange(0, 100)

        return self.__winTaskbarButton

    def timerEvent(self, evt):
        """
        Protected event handler for timer events.

        @param evt reference to the timer event
        @type QTimerEvent
        """
        if evt.timerId() == self.__updateTimer.timerId():
            if self.activeDownloadsCount() == 0:
                self.__stopUpdateTimer()
                self.infoLabel.clear()
                self.setWindowTitle(self.tr("Download Manager"))
                if OSUtilities.isWindowsPlatform():
                    self.__taskbarButton().progress().hide()
            else:
                progresses = []
                for itm in self.__downloads:
                    if itm is None or itm.downloadCanceled() or not itm.downloading():
                        continue

                    progresses.append(
                        (
                            itm.downloadProgress(),
                            itm.remainingTime(),
                            itm.currentSpeed(),
                        )
                    )

                if not progresses:
                    return

                remaining = 0
                progress = 0
                speed = 0.0

                for progressData in progresses:
                    if progressData[1] > remaining:
                        remaining = progressData[1]
                    progress += progressData[0]
                    speed += progressData[2]
                progress /= len(progresses)

                if self.isVisible():
                    self.infoLabel.setText(
                        self.tr(
                            "{0}% of %n file(s) ({1}) {2}", "", len(progresses)
                        ).format(
                            progress,
                            speedString(speed),
                            timeString(remaining),
                        )
                    )
                    self.setWindowTitle(self.tr("{0}% - Download Manager"))

                if OSUtilities.isWindowsPlatform():
                    self.__taskbarButton().progress().show()
                    self.__taskbarButton().progress().setValue(progress)

        super().timerEvent(evt)

    def __startUpdateTimer(self):
        """
        Private slot to start the update timer.
        """
        if self.activeDownloadsCount() and not self.__updateTimer.isActive():
            self.__updateTimer.start(DownloadManager.UpdateTimerTimeout, self)

    def __stopUpdateTimer(self):
        """
        Private slot to stop the update timer.
        """
        self.__updateTimer.stop()

    ###########################################################################
    ## Context menu related methods below
    ###########################################################################

    def __currentItem(self):
        """
        Private method to get a reference to the current item.

        @return reference to the current item
        @rtype DownloadItem
        """
        index = self.downloadsView.currentIndex()
        if index and index.isValid():
            row = index.row()
            return self.__downloads[row]

        return None

    def __contextMenuOpen(self):
        """
        Private method to open the downloaded file.
        """
        itm = self.__currentItem()
        if itm is not None:
            itm.openFile()

    def __contextMenuOpenFolder(self):
        """
        Private method to open the folder containing the downloaded file.
        """
        itm = self.__currentItem()
        if itm is not None:
            itm.openFolder()

    def __contextMenuCancel(self):
        """
        Private method to cancel the current download.
        """
        itm = self.__currentItem()
        if itm is not None:
            itm.cancelDownload()

    def __contextMenuGotoPage(self):
        """
        Private method to open the download page.
        """
        itm = self.__currentItem()
        if itm is not None:
            url = itm.getPageUrl()
            WebBrowserWindow.mainWindow().openUrl(url, "")

    def __contextMenuCopyLink(self):
        """
        Private method to copy the download link to the clipboard.
        """
        itm = self.__currentItem()
        if itm is not None:
            url = itm.getPageUrl().toDisplayString(
                QUrl.ComponentFormattingOption.FullyDecoded
            )
            QApplication.clipboard().setText(url)

    def __contextMenuSelectAll(self):
        """
        Private method to select all downloads.
        """
        self.downloadsView.selectAll()

    def __contextMenuRemoveSelected(self):
        """
        Private method to remove the selected downloads from the list.
        """
        self.downloadsView.removeSelected()
