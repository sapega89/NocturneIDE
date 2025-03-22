# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog showing the available plugins.
"""

import enum
import glob
import os
import re
import zipfile

from collections import ChainMap, defaultdict

from PyQt6.QtCore import (
    QCoreApplication,
    QFile,
    QIODevice,
    QPoint,
    QProcess,
    Qt,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkInformation,
    QNetworkReply,
    QNetworkRequest,
)
from PyQt6.QtWidgets import (
    QAbstractButton,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMenu,
    QToolButton,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from eric7 import EricUtilities, Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricNetwork.EricNetworkProxyFactory import proxyAuthenticationRequired
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.Globals import getConfig
from eric7.SystemUtilities import PythonUtilities

try:
    from eric7.EricNetwork.EricSslErrorHandler import (
        EricSslErrorHandler,
        EricSslErrorState,
    )

    SSL_AVAILABLE = True
except ImportError:
    SSL_AVAILABLE = False

from .PluginManager import PluginManager
from .PluginRepositoryReader import PluginRepositoryReader
from .Ui_PluginRepositoryDialog import Ui_PluginRepositoryDialog


class PluginStatus(enum.Enum):
    """
    Class defining the various plugin status.
    """

    UpToDate = 0
    New = 1
    LocalUpdate = 2
    RemoteUpdate = 3
    Error = 4


class PluginRepositoryWidget(QWidget, Ui_PluginRepositoryDialog):
    """
    Class implementing a dialog showing the available plugins.

    @signal closeAndInstall() emitted when the Close & Install button is
        pressed
    """

    closeAndInstall = pyqtSignal()

    DescrRole = Qt.ItemDataRole.UserRole
    UrlRole = Qt.ItemDataRole.UserRole + 1
    FilenameRole = Qt.ItemDataRole.UserRole + 2
    AuthorRole = Qt.ItemDataRole.UserRole + 3

    def __init__(self, pluginManager, integrated=False, parent=None):
        """
        Constructor

        @param pluginManager reference to the plugin manager object
        @type PluginManager
        @param integrated flag indicating the integration into the sidebar
        @type bool
        @param parent parent of this dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        if pluginManager is None:
            # started as external plug-in repository dialog
            self.__pluginManager = PluginManager()
            self.__external = True
        else:
            self.__pluginManager = pluginManager
            self.__external = False

        self.__integratedWidget = integrated

        self.__statusTranslations = {
            "obsolete": self.tr("Obsolete"),
            "stable": self.tr("Stable"),
            "unknown": self.tr("Unknown"),
            "unstable": self.tr("Unstable"),
            "upgrade": self.tr("Upgrade Available"),
        }
        self.__statusOrder = ("upgrade", "stable", "unstable", "obsolete", "unknown")

        self.__initHeaderItemsCache()

        if self.__integratedWidget:
            self.layout().setContentsMargins(0, 3, 0, 0)

            self.__actionButtonsLayout = QHBoxLayout()
            self.__actionButtonsLayout.addStretch()

            self.__updateButton = QToolButton(self)
            self.__updateButton.setIcon(EricPixmapCache.getIcon("reload"))
            self.__updateButton.setToolTip(self.tr("Update"))
            self.__updateButton.clicked.connect(self.__updateList)
            self.__actionButtonsLayout.addWidget(self.__updateButton)

            self.__downloadButton = QToolButton(self)
            self.__downloadButton.setIcon(EricPixmapCache.getIcon("download"))
            self.__downloadButton.setToolTip(self.tr("Download"))
            self.__downloadButton.clicked.connect(self.__downloadButtonClicked)
            self.__actionButtonsLayout.addWidget(self.__downloadButton)

            self.__downloadInstallButton = QToolButton(self)
            self.__downloadInstallButton.setIcon(
                EricPixmapCache.getIcon("downloadPlus")
            )
            self.__downloadInstallButton.setToolTip(self.tr("Download & Install"))
            self.__downloadInstallButton.clicked.connect(
                self.__downloadInstallButtonClicked
            )
            self.__actionButtonsLayout.addWidget(self.__downloadInstallButton)

            self.__downloadCancelButton = QToolButton(self)
            self.__downloadCancelButton.setIcon(EricPixmapCache.getIcon("cancel"))
            self.__downloadCancelButton.setToolTip(self.tr("Cancel"))
            self.__downloadCancelButton.clicked.connect(self.__downloadCancel)
            self.__actionButtonsLayout.addWidget(self.__downloadCancelButton)

            self.__installButton = QToolButton(self)
            self.__installButton.setIcon(EricPixmapCache.getIcon("plus"))
            self.__installButton.setToolTip(self.tr("Install"))
            self.__installButton.clicked.connect(self.__closeAndInstall)
            self.__actionButtonsLayout.addWidget(self.__installButton)

            self.__actionButtonsLayout.addStretch()

            self.layout().insertLayout(0, self.__actionButtonsLayout)
            self.buttonBox.hide()

            self.repositoryList.setHeaderHidden(True)
        else:
            self.__updateButton = self.buttonBox.addButton(
                self.tr("Update"), QDialogButtonBox.ButtonRole.ActionRole
            )
            self.__downloadButton = self.buttonBox.addButton(
                self.tr("Download"), QDialogButtonBox.ButtonRole.ActionRole
            )
            self.__downloadInstallButton = self.buttonBox.addButton(
                self.tr("Download && Install"), QDialogButtonBox.ButtonRole.ActionRole
            )
            self.__downloadCancelButton = self.buttonBox.addButton(
                self.tr("Cancel"), QDialogButtonBox.ButtonRole.ActionRole
            )
            self.__installButton = self.buttonBox.addButton(
                self.tr("Close && Install"), QDialogButtonBox.ButtonRole.ActionRole
            )
            self.__closeButton = self.buttonBox.addButton(
                self.tr("Close"), QDialogButtonBox.ButtonRole.RejectRole
            )

            self.__closeButton.setEnabled(True)

            self.repositoryList.headerItem().setText(
                self.repositoryList.columnCount(), ""
            )

        self.__downloadButton.setEnabled(False)
        self.__downloadInstallButton.setEnabled(False)
        self.__downloadCancelButton.setEnabled(False)
        self.__installButton.setEnabled(False)

        self.repositoryUrlEdit.setText(Preferences.getUI("PluginRepositoryUrl7"))

        self.__pluginContextMenu = QMenu(self)
        self.__hideAct = self.__pluginContextMenu.addAction(
            self.tr("Hide"), self.__hidePlugin
        )
        self.__hideSelectedAct = self.__pluginContextMenu.addAction(
            self.tr("Hide Selected"), self.__hideSelectedPlugins
        )
        self.__pluginContextMenu.addSeparator()
        self.__showAllAct = self.__pluginContextMenu.addAction(
            self.tr("Show All"), self.__showAllPlugins
        )
        self.__pluginContextMenu.addSeparator()
        self.__pluginContextMenu.addAction(
            self.tr("Cleanup Downloads"), self.__cleanupDownloads
        )

        self.pluginRepositoryFile = os.path.join(
            EricUtilities.getConfigDir(), "PluginRepository"
        )

        self.__pluginManager.pluginRepositoryFileDownloaded.connect(self.__populateList)

        # attributes for the network objects
        self.__networkManager = QNetworkAccessManager(self)
        self.__networkManager.proxyAuthenticationRequired.connect(
            proxyAuthenticationRequired
        )
        if SSL_AVAILABLE:
            self.__sslErrorHandler = EricSslErrorHandler(
                Preferences.getSettings(), self
            )
            self.__networkManager.sslErrors.connect(self.__sslErrors)
        self.__replies = []

        if Preferences.getUI("DynamicOnlineCheck") and QNetworkInformation.load(
            QNetworkInformation.Feature.Reachability
        ):
            self.__reachabilityChanged(QNetworkInformation.instance().reachability())
            QNetworkInformation.instance().reachabilityChanged.connect(
                self.__reachabilityChanged
            )
        else:
            # assume to be 'always online' if no backend could be loaded or
            # dynamic online check is switched of
            self.__reachabilityChanged(QNetworkInformation.Reachability.Online)

        self.__pluginsToDownload = []
        self.__pluginsDownloaded = []
        self.__isDownloadInstall = False
        self.__allDownloadedOk = False

        self.__hiddenPlugins = Preferences.getPluginManager("HiddenPlugins")

        self.on_repositoryList_itemSelectionChanged()
        self.__populateList()

    def __reachabilityChanged(self, reachability):
        """
        Private slot handling reachability state changes.

        @param reachability new reachability state
        @type QNetworkInformation.Reachability
        """
        online = reachability == QNetworkInformation.Reachability.Online
        self.__online = online

        self.__updateButton.setEnabled(online)
        self.on_repositoryList_itemSelectionChanged()

        if not self.__integratedWidget:
            msg = (
                self.tr("Internet Reachability Status: Reachable")
                if online
                else self.tr("Internet Reachability Status: Not Reachable")
            )
            self.statusLabel.setText(msg)

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot to handle the click of a button of the button box.

        @param button reference to the button pressed
        @type QAbstractButton
        """
        if button == self.__updateButton:
            self.__updateList()
        elif button == self.__downloadButton:
            self.__downloadButtonClicked()
        elif button == self.__downloadInstallButton:
            self.__downloadInstallButtonClicked()
        elif button == self.__downloadCancelButton:
            self.__downloadCancel()
        elif button == self.__installButton:
            self.__closeAndInstall()

    @pyqtSlot()
    def __downloadButtonClicked(self):
        """
        Private slot to handle a click of the Download button.
        """
        self.__isDownloadInstall = False
        self.__downloadPlugins()

    @pyqtSlot()
    def __downloadInstallButtonClicked(self):
        """
        Private slot to handle a click of the Download & Install button.
        """
        self.__isDownloadInstall = True
        self.__allDownloadedOk = True
        self.__downloadPlugins()

    def __formatDescription(self, lines):
        """
        Private method to format the description.

        @param lines lines of the description
        @type list of str
        @return formatted description
        @rtype str
        """
        # remove empty line at start and end
        newlines = lines[:]
        if len(newlines) and newlines[0] == "":
            del newlines[0]
        if len(newlines) and newlines[-1] == "":
            del newlines[-1]

        # replace empty lines by newline character
        index = 0
        while index < len(newlines):
            if newlines[index] == "":
                newlines[index] = "\n"
            index += 1

        # join lines by a blank
        return " ".join(newlines)

    def __changeScheme(self, url, newScheme=""):
        """
        Private method to change the scheme of the given URL.

        @param url URL to be modified
        @type str
        @param newScheme scheme to be set for the given URL
        @type str
        @return modified URL
        @rtype str
        """
        if not newScheme:
            newScheme = (
                "http:"
                if Preferences.getPluginManager("ForceHttpPluginDownload")
                else self.repositoryUrlEdit.text().split("//", 1)[0]
            )

        return newScheme + "//" + url.split("//", 1)[1]

    @pyqtSlot(QPoint)
    def on_repositoryList_customContextMenuRequested(self, pos):
        """
        Private slot to show the context menu.

        @param pos position to show the menu
        @type QPoint
        """
        self.__hideAct.setEnabled(
            self.repositoryList.currentItem() is not None
            and len(self.__selectedItems()) == 1
        )
        self.__hideSelectedAct.setEnabled(len(self.__selectedItems()) > 1)
        self.__showAllAct.setEnabled(bool(self.__hasHiddenPlugins()))
        self.__pluginContextMenu.popup(self.repositoryList.mapToGlobal(pos))

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_repositoryList_currentItemChanged(self, current, _previous):
        """
        Private slot to handle the change of the current item.

        @param current reference to the new current item
        @type QTreeWidgetItem
        @param _previous reference to the old current item (unused)
        @type QTreeWidgetItem
        """
        if self.__repositoryMissing or current is None:
            self.descriptionEdit.clear()
            self.authorEdit.clear()
            return

        url = current.data(0, PluginRepositoryWidget.UrlRole)
        url = "" if url is None else self.__changeScheme(url)
        self.urlEdit.setText(url)
        self.descriptionEdit.setPlainText(
            current.data(0, PluginRepositoryWidget.DescrRole)
            and self.__formatDescription(
                current.data(0, PluginRepositoryWidget.DescrRole)
            )
            or ""
        )
        self.authorEdit.setText(
            current.data(0, PluginRepositoryWidget.AuthorRole) or ""
        )

    def __selectedItems(self):
        """
        Private method to get all selected items without the status and category items.

        @return list of selected items without header items
        @rtype list of QTreeWidgetItem
        """
        selectedItems = []
        allCategoryItems = ChainMap(*self.__categoryItems.values())
        for itm in self.repositoryList.selectedItems():
            if (
                itm not in self.__statusItems.values()
                and itm not in allCategoryItems.values()
            ):
                selectedItems.append(itm)
        return selectedItems

    @pyqtSlot()
    def on_repositoryList_itemSelectionChanged(self):
        """
        Private slot to handle a change of the selection.
        """
        enable = bool(self.__selectedItems())
        self.__downloadButton.setEnabled(enable and self.__online)
        self.__downloadInstallButton.setEnabled(enable and self.__online)
        self.__installButton.setEnabled(enable)

        self.selectedLabel.setText(
            self.tr("Selected: <b>{0}</b>").format(len(self.__selectedItems()))
        )

    def reloadList(self):
        """
        Public method to reload the list of plugins.
        """
        self.__populateList()

    @pyqtSlot()
    def __updateList(self):
        """
        Private slot to download a new list and display the contents.
        """
        url = self.repositoryUrlEdit.text()
        if Preferences.getPluginManager("ForceHttpPluginDownload"):
            url = url.replace("https://", "http://")
        self.__pluginManager.downLoadRepositoryFile(url=url)

    def __downloadPluginDone(self, status, filename):
        """
        Private method called, when the download of a plugin is finished.

        @param status flag indicating a successful download
        @type bool
        @param filename full path of the downloaded file
        @type str
        """
        if status:
            self.__pluginsDownloaded.append(filename)
        if self.__isDownloadInstall:
            self.__allDownloadedOk &= status

        if len(self.__pluginsToDownload):
            self.__pluginsToDownload.pop(0)

        if len(self.__pluginsToDownload):
            self.__downloadPlugin()
        else:
            self.__downloadPluginsDone()

    def __downloadPlugin(self):
        """
        Private method to download the next plugin.
        """
        self.__downloadFile(
            self.__pluginsToDownload[0][0],
            self.__pluginsToDownload[0][1],
            self.__downloadPluginDone,
        )

    def __downloadPlugins(self):
        """
        Private slot to download the selected plugins.
        """
        self.__pluginsDownloaded = []
        self.__pluginsToDownload = []
        self.__downloadButton.setEnabled(False)
        self.__downloadInstallButton.setEnabled(False)
        self.__installButton.setEnabled(False)

        newScheme = (
            "http:"
            if Preferences.getPluginManager("ForceHttpPluginDownload")
            else self.repositoryUrlEdit.text().split("//", 1)[0]
        )
        for itm in self.__selectedItems():
            url = self.__changeScheme(
                itm.data(0, PluginRepositoryWidget.UrlRole), newScheme
            )
            filename = os.path.join(
                Preferences.getPluginManager("DownloadPath"),
                itm.data(0, PluginRepositoryWidget.FilenameRole),
            )
            self.__pluginsToDownload.append((url, filename))
        if self.__pluginsToDownload:
            self.__downloadPlugin()

    def __downloadPluginsDone(self):
        """
        Private method called, when the download of the plugins is finished.
        """
        self.__downloadButton.setEnabled(len(self.__selectedItems()))
        self.__downloadInstallButton.setEnabled(len(self.__selectedItems()))
        self.__installButton.setEnabled(len(self.__selectedItems()))
        ui = ericApp().getObject("UserInterface") if not self.__external else None
        if ui is not None:
            ui.showNotification(
                EricPixmapCache.getPixmap("plugin48"),
                self.tr("Download Plugin Files"),
                self.tr("""The requested plugins were downloaded."""),
            )

        if self.__isDownloadInstall:
            self.closeAndInstall.emit()
        else:
            if ui is None:
                EricMessageBox.information(
                    self,
                    self.tr("Download Plugin Files"),
                    self.tr("""The requested plugins were downloaded."""),
                )

            self.downloadProgress.setValue(0)

            # repopulate the list to update the refresh icons
            self.__populateList()

    def __initHeaderItemsCache(self):
        """
        Private method to initialize the cache variables for the header items.
        """
        self.__statusItems = defaultdict(lambda: None)
        self.__categoryItems = defaultdict(dict)

    def __populateList(self):
        """
        Private method to populate the list of available plugins.
        """
        self.__initHeaderItemsCache()
        self.repositoryList.clear()

        self.__newItems = 0
        self.__updateLocalItems = 0
        self.__updateRemoteItems = 0

        self.downloadProgress.setValue(0)

        if os.path.exists(self.pluginRepositoryFile):
            self.__repositoryMissing = False
            f = QFile(self.pluginRepositoryFile)
            if f.open(QIODevice.OpenModeFlag.ReadOnly):
                reader = PluginRepositoryReader(f, self.addEntry)
                reader.readXML()
                self.__updateStatusItemTexts()

                self.repositoryList.resizeColumnToContents(0)
                self.repositoryList.resizeColumnToContents(1)
                self.repositoryList.resizeColumnToContents(2)
                self.repositoryList.sortItems(0, Qt.SortOrder.AscendingOrder)

                url = Preferences.getUI("PluginRepositoryUrl7")
                if url != self.repositoryUrlEdit.text():
                    self.repositoryUrlEdit.setText(url)
                    EricMessageBox.warning(
                        self,
                        self.tr("Plugins Repository URL Changed"),
                        self.tr(
                            """The URL of the Plugins Repository has"""
                            """ changed. Select the "Update" button to get"""
                            """ the new repository file."""
                        ),
                    )
            else:
                EricMessageBox.critical(
                    self,
                    self.tr("Read plugins repository file"),
                    self.tr(
                        "<p>The plugins repository file <b>{0}</b> "
                        "could not be read. Select Update</p>"
                    ).format(self.pluginRepositoryFile),
                )
        else:
            self.__repositoryMissing = True
            QTreeWidgetItem(
                self.repositoryList,
                ["", self.tr("No plugin repository file available.\nSelect Update.")],
            )
            self.repositoryList.resizeColumnToContents(1)

        self.newLabel.setText(self.tr("New: <b>{0}</b>").format(self.__newItems))
        self.updateLocalLabel.setText(
            self.tr("Local Updates: <b>{0}</b>").format(self.__updateLocalItems)
        )
        self.updateRemoteLabel.setText(
            self.tr("Remote Updates: <b>{0}</b>").format(self.__updateRemoteItems)
        )

    def __downloadFile(self, url, filename, doneMethod=None):
        """
        Private slot to download the given file.

        @param url URL for the download
        @type str
        @param filename local name of the file
        @type str
        @param doneMethod method to be called when done
        @type function
        """
        if self.__online:
            self.__updateButton.setEnabled(False)
            self.__downloadButton.setEnabled(False)
            self.__downloadInstallButton.setEnabled(False)
            if not self.__integratedWidget:
                self.__closeButton.setEnabled(False)
            self.__downloadCancelButton.setEnabled(True)

            if Preferences.getPluginManager("ForceHttpPluginDownload"):
                url = url.replace("https://", "http://")

            self.statusLabel.setText(url)

            request = QNetworkRequest(QUrl(url))
            request.setAttribute(
                QNetworkRequest.Attribute.CacheLoadControlAttribute,
                QNetworkRequest.CacheLoadControl.AlwaysNetwork,
            )
            reply = self.__networkManager.get(request)
            reply.finished.connect(
                lambda: self.__downloadFileDone(reply, filename, doneMethod)
            )
            reply.downloadProgress.connect(self.__downloadProgress)
            self.__replies.append(reply)
        else:
            EricMessageBox.warning(
                self,
                self.tr("Error downloading file"),
                self.tr(
                    """<p>Could not download the requested file"""
                    """ from {0}.</p><p>Error: {1}</p>"""
                ).format(url, self.tr("No connection to Internet.")),
            )

    def __downloadFileDone(self, reply, fileName, doneMethod):
        """
        Private method called, after the file has been downloaded
        from the Internet.

        @param reply reference to the reply object of the download
        @type QNetworkReply
        @param fileName local name of the file
        @type str
        @param doneMethod method to be called when done
        @type function
        """
        self.__updateButton.setEnabled(True)
        if not self.__integratedWidget:
            self.__closeButton.setEnabled(True)
        self.__downloadCancelButton.setEnabled(False)

        ok = True
        if reply in self.__replies:
            self.__replies.remove(reply)
        if reply.error() != QNetworkReply.NetworkError.NoError:
            ok = False
            if reply.error() != QNetworkReply.NetworkError.OperationCanceledError:
                EricMessageBox.warning(
                    self,
                    self.tr("Error downloading file"),
                    self.tr(
                        """<p>Could not download the requested file"""
                        """ from {0}.</p><p>Error: {1}</p>"""
                    ).format(reply.url().toString(), reply.errorString()),
                )
            self.downloadProgress.setValue(0)
            if self.repositoryList.topLevelItemCount():
                if self.repositoryList.currentItem() is None:
                    self.repositoryList.setCurrentItem(
                        self.repositoryList.topLevelItem(0)
                    )
                else:
                    self.__downloadButton.setEnabled(len(self.__selectedItems()))
                    self.__downloadInstallButton.setEnabled(len(self.__selectedItems()))
            reply.deleteLater()
            return

        downloadIODevice = QFile(fileName + ".tmp")
        downloadIODevice.open(QIODevice.OpenModeFlag.WriteOnly)
        # read data in chunks
        chunkSize = 64 * 1024 * 1024
        while True:
            data = reply.read(chunkSize)
            if data is None or len(data) == 0:
                break
            downloadIODevice.write(data)
        downloadIODevice.close()
        if QFile.exists(fileName):
            QFile.remove(fileName)
        downloadIODevice.rename(fileName)
        reply.deleteLater()

        if doneMethod is not None:
            doneMethod(ok, fileName)

    def __downloadCancel(self, reply=None):
        """
        Private slot to cancel the current download.

        @param reply reference to the network reply
        @type QNetworkReply
        """
        if reply is None and bool(self.__replies):
            reply = self.__replies[0]
        self.__pluginsToDownload = []
        if reply is not None:
            reply.abort()

    def __downloadProgress(self, done, total):
        """
        Private slot to show the download progress.

        @param done number of bytes downloaded so far
        @type int
        @param total total bytes to be downloaded
        @type int
        """
        if total:
            self.downloadProgress.setMaximum(total)
            self.downloadProgress.setValue(done)

    def __addPluginItem(
        self,
        parentItem,
        name,
        short,
        description,
        url,
        author,
        version,
        filename,
        updateStatus,
        countIt=True,
    ):
        """
        Private method to add an item for the given plugin parameters.

        @param parentItem reference to the parent item
        @type QTreeWidgetItem
        @param name data for the name field
        @type str
        @param short data for the short field
        @type str
        @param description data for the description field
        @type list of str
        @param url data for the url field
        @type str
        @param author data for the author field
        @type str
        @param version data for the version field
        @type str
        @param filename data for the filename field
        @type str
        @param updateStatus update status
        @type PluginStatus
        @param countIt flag indicating to count the item for status labels
            (defaults to True)
        @type bool (optional)
        """
        if self.__integratedWidget:
            entryFormat = "<b>{0}</b> - Version: <i>{1}</i><br/>{2}"
            itm = QTreeWidgetItem(parentItem)
            itm.setFirstColumnSpanned(True)
            label = QLabel(entryFormat.format(name, version, short))
            self.repositoryList.setItemWidget(itm, 0, label)
        else:
            itm = QTreeWidgetItem(parentItem, [name, version, short])

        itm.setData(0, PluginRepositoryWidget.UrlRole, url)
        itm.setData(0, PluginRepositoryWidget.FilenameRole, filename)
        itm.setData(0, PluginRepositoryWidget.AuthorRole, author)
        itm.setData(0, PluginRepositoryWidget.DescrRole, description)

        iconColumn = 0 if self.__integratedWidget else 1
        if updateStatus == PluginStatus.UpToDate:
            itm.setIcon(iconColumn, EricPixmapCache.getIcon("empty"))
            itm.setToolTip(iconColumn, self.tr("up-to-date"))
        elif updateStatus == PluginStatus.New:
            itm.setIcon(iconColumn, EricPixmapCache.getIcon("download"))
            itm.setToolTip(iconColumn, self.tr("new download available"))
            if countIt:
                self.__newItems += 1
        elif updateStatus == PluginStatus.LocalUpdate:
            itm.setIcon(iconColumn, EricPixmapCache.getIcon("updateLocal"))
            itm.setToolTip(iconColumn, self.tr("update installable"))
            if countIt:
                self.__updateLocalItems += 1
        elif updateStatus == PluginStatus.RemoteUpdate:
            itm.setIcon(iconColumn, EricPixmapCache.getIcon("updateRemote"))
            itm.setToolTip(iconColumn, self.tr("updated download available"))
            if countIt:
                self.__updateRemoteItems += 1
        elif updateStatus == PluginStatus.Error:
            itm.setIcon(iconColumn, EricPixmapCache.getIcon("warning"))
            itm.setToolTip(iconColumn, self.tr("error determining status"))

    def addEntry(
        self,
        name,
        short,
        description,
        url,
        author,
        version,
        filename,
        status,
        category,
    ):
        """
        Public method to add an entry to the list.

        @param name data for the name field
        @type str
        @param short data for the short field
        @type str
        @param description data for the description field
        @type list of str
        @param url data for the url field
        @type str
        @param author data for the author field
        @type str
        @param version data for the version field
        @type str
        @param filename data for the filename field
        @type str
        @param status status of the plugin (one of stable, unstable, unknown)
        @type str
        @param category category designation of the plugin
        @type str
        """
        pluginName = filename.rsplit("-", 1)[0]
        if pluginName in self.__hiddenPlugins:
            return

        # 1. determine and create the status item
        statusItem = self.__statusItems[status]
        if statusItem is None:
            if status not in self.__statusTranslations:
                status = "unknown"
            statusItem = QTreeWidgetItem(self.repositoryList, [""])
            statusItem.setExpanded(True)
            statusItem.setFirstColumnSpanned(True)
            self.__statusItems[status] = statusItem

        # 2. determine and create the category item
        try:
            categoryItem = self.__categoryItems[status][category]
        except KeyError:
            # create the category item
            categoryItem = QTreeWidgetItem(statusItem, [category])
            categoryItem.setExpanded(True)
            categoryItem.setFirstColumnSpanned(True)
            self.__categoryItems[status][category] = categoryItem

        # 3. create the plugin item
        updateStatus = self.__updateStatus(filename, version)
        self.__addPluginItem(
            categoryItem,
            name,
            short,
            description,
            url,
            author,
            version,
            filename,
            updateStatus,
        )

        # 4. create the upgradable plugin item
        if updateStatus in (PluginStatus.LocalUpdate, PluginStatus.RemoteUpdate):
            status = "upgrade"

            statusItem = self.__statusItems[status]
            if statusItem is None:
                statusItem = QTreeWidgetItem(self.repositoryList, [""])
                statusItem.setExpanded(True)
                statusItem.setFirstColumnSpanned(True)
                self.__statusItems[status] = statusItem

            self.__addPluginItem(
                statusItem,
                name,
                short,
                description,
                url,
                author,
                version,
                filename,
                updateStatus,
                countIt=False,
            )

    def __updateStatus(self, filename, version):
        """
        Private method to check the given archive update status.

        @param filename data for the filename field
        @type str
        @param version data for the version field
        @type str
        @return plug-in update status
        @rtype int (one of PluginStatusNew, PluginStatusUpToDate,
            PluginStatusLocalUpdate, PluginStatusRemoteUpdate)
        """
        archive = os.path.join(Preferences.getPluginManager("DownloadPath"), filename)

        # check, if it is an update (i.e. we already have archives
        # with the same pattern)
        archivesPattern = archive.rsplit("-", 1)[0] + "-*.zip"
        if len(glob.glob(archivesPattern)) == 0:
            # Check against installed/loaded plug-ins
            pluginName = filename.rsplit("-", 1)[0]
            pluginDetails = self.__pluginManager.getPluginDetails(pluginName)
            if pluginDetails is None or pluginDetails["moduleName"] != pluginName:
                return PluginStatus.New
            if pluginDetails["error"]:
                return PluginStatus.Error
            pluginVersionTuple = EricUtilities.versionToTuple(pluginDetails["version"])[
                :3
            ]
            versionTuple = EricUtilities.versionToTuple(version)[:3]
            if pluginVersionTuple < versionTuple:
                return PluginStatus.RemoteUpdate
            else:
                return PluginStatus.UpToDate

        # check, if the archive exists
        if not os.path.exists(archive):
            return PluginStatus.RemoteUpdate

        # check, if the archive is a valid zip file
        if not zipfile.is_zipfile(archive):
            return PluginStatus.RemoteUpdate

        zipFile = zipfile.ZipFile(archive, "r")
        try:
            aversion = zipFile.read("VERSION").decode("utf-8")
        except KeyError:
            aversion = ""
        zipFile.close()

        if aversion == version:
            # Check against installed/loaded plug-ins
            pluginName = filename.rsplit("-", 1)[0]
            pluginDetails = self.__pluginManager.getPluginDetails(pluginName)
            if pluginDetails is None:
                return PluginStatus.LocalUpdate
            if (
                EricUtilities.versionToTuple(pluginDetails["version"])[:3]
                < EricUtilities.versionToTuple(version)[:3]
            ):
                return PluginStatus.LocalUpdate
            else:
                return PluginStatus.UpToDate
        else:
            return PluginStatus.RemoteUpdate

    def __updateStatusItemTexts(self):
        """
        Private method to update the status item texts to include a number determined
        by a given status order.
        """
        index = 1
        for status in self.__statusOrder:
            statusItem = self.__statusItems[status]
            if statusItem is not None:
                statusItem.setText(
                    0,
                    self.tr("{0}. {1}").format(
                        index, self.__statusTranslations[status]
                    ),
                )
                index += 1

    def __sslErrors(self, reply, errors):
        """
        Private slot to handle SSL errors.

        @param reply reference to the reply object
        @type QNetworkReply
        @param errors list of SSL errors
        @type list of QSslError
        """
        ignored = self.__sslErrorHandler.sslErrorsReply(reply, errors)[0]
        if ignored == EricSslErrorState.NOT_IGNORED:
            self.__downloadCancel(reply)

    def getDownloadedPlugins(self):
        """
        Public method to get the list of recently downloaded plugin files.

        @return list of plugin filenames
        @rtype list of str
        """
        return self.__pluginsDownloaded

    @pyqtSlot(bool)
    def on_repositoryUrlEditButton_toggled(self, checked):
        """
        Private slot to set the read only status of the repository URL line
        edit.

        @param checked state of the push button
        @type bool
        """
        self.repositoryUrlEdit.setReadOnly(not checked)

    def __closeAndInstall(self):
        """
        Private method to close the dialog and invoke the install dialog.
        """
        if not self.__pluginsDownloaded and self.__selectedItems():
            for itm in self.__selectedItems():
                filename = os.path.join(
                    Preferences.getPluginManager("DownloadPath"),
                    itm.data(0, PluginRepositoryWidget.FilenameRole),
                )
                self.__pluginsDownloaded.append(filename)
        self.closeAndInstall.emit()

    def __hidePlugin(self):
        """
        Private slot to hide the current plug-in.
        """
        itm = self.__selectedItems()[0]
        pluginName = itm.data(0, PluginRepositoryWidget.FilenameRole).rsplit("-", 1)[0]
        self.__updateHiddenPluginsList([pluginName])

    def __hideSelectedPlugins(self):
        """
        Private slot to hide all selected plug-ins.
        """
        hideList = []
        for itm in self.__selectedItems():
            pluginName = itm.data(0, PluginRepositoryWidget.FilenameRole).rsplit(
                "-", 1
            )[0]
            hideList.append(pluginName)
        self.__updateHiddenPluginsList(hideList)

    def __showAllPlugins(self):
        """
        Private slot to show all plug-ins.
        """
        self.__hiddenPlugins = []
        self.__updateHiddenPluginsList([])

    def __hasHiddenPlugins(self):
        """
        Private method to check, if there are any hidden plug-ins.

        @return flag indicating the presence of hidden plug-ins
        @rtype bool
        """
        return bool(self.__hiddenPlugins)

    def __updateHiddenPluginsList(self, hideList):
        """
        Private method to store the list of hidden plug-ins to the settings.

        @param hideList list of plug-ins to add to the list of hidden ones
        @type list of str
        """
        if hideList:
            self.__hiddenPlugins.extend(
                [p for p in hideList if p not in self.__hiddenPlugins]
            )
        Preferences.setPluginManager("HiddenPlugins", self.__hiddenPlugins)
        self.__populateList()

    def __cleanupDownloads(self):
        """
        Private slot to cleanup the plug-in downloads area.
        """
        PluginRepositoryDownloadCleanup()


class PluginRepositoryDialog(QDialog):
    """
    Class for the dialog variant.
    """

    def __init__(self, pluginManager, parent=None):
        """
        Constructor

        @param pluginManager reference to the plugin manager object
        @type PluginManager
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setSizeGripEnabled(True)

        self.__layout = QVBoxLayout(self)
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.__layout)

        self.cw = PluginRepositoryWidget(pluginManager, parent=self)
        size = self.cw.size()
        self.__layout.addWidget(self.cw)
        self.resize(size)
        self.setWindowTitle(self.cw.windowTitle())

        self.cw.buttonBox.accepted.connect(self.accept)
        self.cw.buttonBox.rejected.connect(self.reject)
        self.cw.closeAndInstall.connect(self.__closeAndInstall)

    def __closeAndInstall(self):
        """
        Private slot to handle the closeAndInstall signal.
        """
        self.done(QDialog.DialogCode.Accepted + 1)

    def getDownloadedPlugins(self):
        """
        Public method to get the list of recently downloaded plugin files.

        @return list of plugin filenames
        @rtype list of str
        """
        return self.cw.getDownloadedPlugins()


class PluginRepositoryWindow(EricMainWindow):
    """
    Main window class for the standalone dialog.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.cw = PluginRepositoryWidget(None, parent=self)
        size = self.cw.size()
        self.setCentralWidget(self.cw)
        self.resize(size)
        self.setWindowTitle(self.cw.windowTitle())

        self.setStyle(
            styleName=Preferences.getUI("Style"),
            styleSheetFile=Preferences.getUI("StyleSheet"),
            itemClickBehavior=Preferences.getUI("ActivateItemOnSingleClick"),
        )

        self.cw.buttonBox.accepted.connect(self.close)
        self.cw.buttonBox.rejected.connect(self.close)
        self.cw.closeAndInstall.connect(self.__startPluginInstall)

    def __startPluginInstall(self):
        """
        Private slot to start the eric plugin installation dialog.
        """
        proc = QProcess()
        applPath = os.path.join(getConfig("ericDir"), "eric7_plugininstall.py")

        args = []
        args.append(applPath)
        args += self.cw.getDownloadedPlugins()

        if not os.path.isfile(applPath) or not proc.startDetached(
            PythonUtilities.getPythonExecutable(), args
        ):
            EricMessageBox.critical(
                self,
                self.tr("Process Generation Error"),
                self.tr(
                    "<p>Could not start the process.<br>"
                    "Ensure that it is available as <b>{0}</b>.</p>"
                ).format(applPath),
                self.tr("OK"),
            )

        self.close()


def PluginRepositoryDownloadCleanup(quiet=False):
    """
    Module function to clean up the plug-in downloads area.

    @param quiet flag indicating quiet operations
    @type bool
    """
    pluginsRegister = []  # list of plug-ins contained in the repository

    def registerPlugin(
        _name,
        _short,
        _description,
        url,
        _author,
        _version,
        _filename,
        _status,
        _category,
    ):
        """
        Method to register a plug-in's data.

        @param _name data for the name field (unused)
        @type str
        @param _short data for the short field (unused)
        @type str
        @param _description data for the description field (unused)
        @type list of str
        @param url data for the url field
        @type str
        @param _author data for the author field (unused)
        @type str
        @param _version data for the version field (unused)
        @type str
        @param _filename data for the filename field (unused)
        @type str
        @param _status status of the plugin (one of stable, unstable, unknown) (unused)
        @type str
        @param _category category designation of the plugin (unused)
        @type str
        """
        pluginName = os.path.splitext(url.rsplit("/", 1)[1])[0]
        if pluginName not in pluginsRegister:
            pluginsRegister.append(pluginName)

    downloadPath = Preferences.getPluginManager("DownloadPath")
    downloads = {}  # plug-in name as key, file name and version as value

    # step 1: extract plug-ins and downloaded files
    with os.scandir(downloadPath) as dirEntriesIterator:
        for pluginFile in dirEntriesIterator:
            if not pluginFile.is_file():
                continue

            try:
                pluginName, pluginVersion = pluginFile.name.replace(".zip", "").rsplit(
                    "-", 1
                )
                pluginVersionList = re.split("[._-]", pluginVersion)
                for index in range(len(pluginVersionList)):
                    try:
                        pluginVersionList[index] = int(pluginVersionList[index])
                    except ValueError:
                        # use default of 0
                        pluginVersionList[index] = 0
            except ValueError:
                # rsplit() returned just one entry, i.e. file name doesn't contain
                # version info separated by '-'
                # => assume version 0.0.0
                pluginName = pluginFile.replace(".zip", "")
                pluginVersionList = [0, 0, 0]

            if pluginName not in downloads:
                downloads[pluginName] = []
            downloads[pluginName].append((pluginFile, tuple(pluginVersionList)))

    # step 2: delete old entries
    hiddenPlugins = Preferences.getPluginManager("HiddenPlugins")
    for pluginName in downloads:
        downloads[pluginName].sort(key=lambda x: x[1])

        removeFiles = (
            [f[0] for f in downloads[pluginName]]
            if (
                pluginName in hiddenPlugins
                and not Preferences.getPluginManager("KeepHidden")
            )
            else [
                f[0]
                for f in downloads[pluginName][
                    : -Preferences.getPluginManager("KeepGenerations")
                ]
            ]
        )
        for removeFile in removeFiles:
            try:
                os.remove(os.path.join(downloadPath, removeFile))
            except OSError as err:
                if not quiet:
                    EricMessageBox.critical(
                        None,
                        QCoreApplication.translate(
                            "PluginRepositoryWidget", "Cleanup of Plugin Downloads"
                        ),
                        QCoreApplication.translate(
                            "PluginRepositoryWidget",
                            """<p>The plugin download <b>{0}</b> could"""
                            """ not be deleted.</p><p>Reason: {1}</p>""",
                        ).format(removeFile, str(err)),
                    )

    # step 3: delete entries of obsolete plug-ins
    pluginRepositoryFile = os.path.join(
        EricUtilities.getConfigDir(), "PluginRepository"
    )
    if os.path.exists(pluginRepositoryFile):
        f = QFile(pluginRepositoryFile)
        if f.open(QIODevice.OpenModeFlag.ReadOnly):
            reader = PluginRepositoryReader(f, registerPlugin)
            reader.readXML()

            for pluginName in downloads:
                if pluginName not in pluginsRegister:
                    removeFiles = [f[0] for f in downloads[pluginName]]
                    for removeFile in removeFiles:
                        try:
                            os.remove(os.path.join(downloadPath, removeFile))
                        except OSError as err:
                            if not quiet:
                                EricMessageBox.critical(
                                    None,
                                    QCoreApplication.translate(
                                        "PluginRepositoryWidget",
                                        "Cleanup of Plugin Downloads",
                                    ),
                                    QCoreApplication.translate(
                                        "PluginRepositoryWidget",
                                        "<p>The plugin download <b>{0}</b>"
                                        " could not be deleted.</p>"
                                        "<p>Reason: {1}</p>"
                                        "",
                                    ).format(removeFile, str(err)),
                                )
