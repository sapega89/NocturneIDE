# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to install spell checking dictionaries.
"""

import contextlib
import glob
import io
import os
import shutil
import zipfile

from PyQt6.QtCore import Qt, QUrl, pyqtSlot
from PyQt6.QtNetwork import QNetworkInformation, QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import QAbstractButton, QDialog, QDialogButtonBox, QListWidgetItem

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .SpellCheckDictionariesReader import SpellCheckDictionariesReader
from .Ui_ManageDictionariesDialog import Ui_ManageDictionariesDialog


class ManageDictionariesDialog(QDialog, Ui_ManageDictionariesDialog):
    """
    Class implementing a dialog to install spell checking dictionaries.
    """

    FilenameRole = Qt.ItemDataRole.UserRole
    UrlRole = Qt.ItemDataRole.UserRole + 1
    DocumentationDirRole = Qt.ItemDataRole.UserRole + 2
    LocalesRole = Qt.ItemDataRole.UserRole + 3

    def __init__(
        self,
        writeableDirectories,
        enforceUnencryptedDownloads=False,
        parent=None,
    ):
        """
        Constructor

        @param writeableDirectories list of writable directories
        @type list of str
        @param enforceUnencryptedDownloads flag indicating to perform unencrypted
            downloads (defaults to False)
        @type bool (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__enforceUnencryptedDownloads = enforceUnencryptedDownloads

        self.__refreshButton = self.buttonBox.addButton(
            self.tr("Refresh"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__installButton = self.buttonBox.addButton(
            self.tr("Install Selected"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__installButton.setEnabled(False)
        self.__uninstallButton = self.buttonBox.addButton(
            self.tr("Uninstall Selected"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__uninstallButton.setEnabled(False)
        self.__cancelButton = self.buttonBox.addButton(
            self.tr("Cancel"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__cancelButton.setEnabled(False)

        self.locationComboBox.addItems(writeableDirectories)

        self.dictionariesUrlEdit.setText(
            Preferences.getWebBrowser("SpellCheckDictionariesUrl")
        )

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
        self.__replies = []

        self.__downloadCancelled = False
        self.__dictionariesToDownload = []

        self.__populateList()

    def __reachabilityChanged(self, reachability):
        """
        Private slot handling reachability state changes.

        @param reachability new reachability state
        @type QNetworkInformation.Reachability
        """
        online = reachability == QNetworkInformation.Reachability.Online
        self.__online = online

        self.__refreshButton.setEnabled(online)

        msg = (
            self.tr("Internet Reachability Status: Reachable")
            if online
            else self.tr("Internet Reachability Status: Not Reachable")
        )
        self.statusLabel.setText(msg)

        self.on_dictionariesList_itemSelectionChanged()

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot to handle the click of a button of the button box.

        @param button reference to the button pressed
        @type QAbstractButton
        """
        if button == self.__refreshButton:
            self.__populateList()
        elif button == self.__cancelButton:
            self.__downloadCancel()
        elif button == self.__installButton:
            self.__installSelected()
        elif button == self.__uninstallButton:
            self.__uninstallSelected()

    @pyqtSlot()
    def on_dictionariesList_itemSelectionChanged(self):
        """
        Private slot to handle a change of the selection.
        """
        self.__installButton.setEnabled(
            self.locationComboBox.count() > 0
            and len(self.dictionariesList.selectedItems()) > 0
            and self.__online
        )

        self.__uninstallButton.setEnabled(
            self.locationComboBox.count() > 0
            and len(
                [
                    itm
                    for itm in self.dictionariesList.selectedItems()
                    if itm.checkState() == Qt.CheckState.Checked
                ]
            )
        )

    @pyqtSlot(bool)
    def on_dictionariesUrlEditButton_toggled(self, checked):
        """
        Private slot to set the read only status of the dictionaries URL line
        edit.

        @param checked state of the push button
        @type bool
        """
        self.dictionariesUrlEdit.setReadOnly(not checked)

    @pyqtSlot(str)
    def on_locationComboBox_currentTextChanged(self, _txt):
        """
        Private slot to handle a change of the installation location.

        @param _txt installation location (unused)
        @type str
        """
        self.__checkInstalledDictionaries()

    def __populateList(self):
        """
        Private method to populate the list of available plugins.
        """
        self.dictionariesList.clear()
        self.downloadProgress.setValue(0)

        url = self.dictionariesUrlEdit.text()
        if self.__enforceUnencryptedDownloads or Preferences.getWebBrowser(
            "ForceHttpDictionaryDownload"
        ):
            url = url.replace("https://", "http://")

        if self.__online:
            self.__refreshButton.setEnabled(False)
            self.__installButton.setEnabled(False)
            self.__uninstallButton.setEnabled(False)
            self.__cancelButton.setEnabled(True)

            self.statusLabel.setText(url)

            self.__downloadCancelled = False

            request = QNetworkRequest(QUrl(url))
            request.setAttribute(
                QNetworkRequest.Attribute.CacheLoadControlAttribute,
                QNetworkRequest.CacheLoadControl.AlwaysNetwork,
            )
            reply = WebBrowserWindow.networkManager().get(request)
            reply.finished.connect(lambda: self.__listFileDownloaded(reply))
            reply.downloadProgress.connect(self.__downloadProgress)
            self.__replies.append(reply)
        else:
            EricMessageBox.warning(
                self,
                self.tr("Error populating list of dictionaries"),
                self.tr(
                    """<p>Could not download the dictionaries list"""
                    """ from {0}.</p><p>Error: {1}</p>"""
                ).format(url, self.tr("No connection to Internet.")),
            )

    def __listFileDownloaded(self, reply):
        """
        Private method called, after the dictionaries list file has been
        downloaded from the Internet.

        @param reply reference to the network reply
        @type QNetworkReply
        """
        self.__refreshButton.setEnabled(True)
        self.__cancelButton.setEnabled(False)

        self.downloadProgress.setValue(0)

        if reply in self.__replies:
            self.__replies.remove(reply)
        reply.deleteLater()

        if reply.error() != QNetworkReply.NetworkError.NoError:
            if not self.__downloadCancelled:
                EricMessageBox.warning(
                    self,
                    self.tr("Error downloading dictionaries list"),
                    self.tr(
                        """<p>Could not download the dictionaries list"""
                        """ from {0}.</p><p>Error: {1}</p>"""
                    ).format(self.dictionariesUrlEdit.text(), reply.errorString()),
                )
            self.downloadProgress.setValue(0)
            return

        listFileData = reply.readAll()

        # extract the dictionaries
        reader = SpellCheckDictionariesReader(listFileData, self.addEntry)
        reader.readXML()
        url = Preferences.getWebBrowser("SpellCheckDictionariesUrl")
        if url != self.dictionariesUrlEdit.text():
            self.dictionariesUrlEdit.setText(url)
            EricMessageBox.warning(
                self,
                self.tr("Dictionaries URL Changed"),
                self.tr(
                    """The URL of the spell check dictionaries has"""
                    """ changed. Select the "Refresh" button to get"""
                    """ the new dictionaries list."""
                ),
            )

        if self.locationComboBox.count() == 0:
            # no writable locations available
            EricMessageBox.warning(
                self,
                self.tr("Error installing dictionaries"),
                self.tr(
                    """<p>None of the dictionary locations is writable by"""
                    """ you. Please download required dictionaries manually"""
                    """ and install them as administrator.</p>"""
                ),
            )

        self.__checkInstalledDictionaries()

    def __downloadCancel(self):
        """
        Private slot to cancel the current download.
        """
        if self.__replies:
            reply = self.__replies[0]
            self.__downloadCancelled = True
            self.__dictionariesToDownload = []
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

    def addEntry(self, short, filename, url, documentationDir, locales):
        """
        Public method to add an entry to the list.

        @param short data for the description field
        @type str
        @param filename data for the filename field
        @type str
        @param url download URL for the dictionary entry
        @type str
        @param documentationDir name of the directory containing the
            dictionary documentation
        @type str
        @param locales list of locales
        @type list of str
        """
        itm = QListWidgetItem(
            self.tr("{0} ({1})").format(short, " ".join(locales)), self.dictionariesList
        )
        itm.setCheckState(Qt.CheckState.Unchecked)

        itm.setData(ManageDictionariesDialog.FilenameRole, filename)
        itm.setData(ManageDictionariesDialog.UrlRole, url)
        itm.setData(ManageDictionariesDialog.DocumentationDirRole, documentationDir)
        itm.setData(ManageDictionariesDialog.LocalesRole, locales)

    def __checkInstalledDictionaries(self):
        """
        Private method to check all installed dictionaries.

        Note: A dictionary is assumed to be installed, if at least one of its
        binary dictionaries (*.bdic) is found in the selected dictionaries
        location.
        """
        if self.locationComboBox.currentText():
            installedLocales = {
                os.path.splitext(os.path.basename(dic))[0]
                for dic in glob.glob(
                    os.path.join(self.locationComboBox.currentText(), "*.bdic")
                )
            }

            for row in range(self.dictionariesList.count()):
                itm = self.dictionariesList.item(row)
                locales = set(itm.data(ManageDictionariesDialog.LocalesRole))
                if locales.intersection(installedLocales):
                    itm.setCheckState(Qt.CheckState.Checked)
                else:
                    itm.setCheckState(Qt.CheckState.Unchecked)
        else:
            for row in range(self.dictionariesList.count()):
                itm = self.dictionariesList.item(row)
                itm.setCheckState(Qt.CheckState.Unchecked)

    def __installSelected(self):
        """
        Private method to install the selected dictionaries.
        """
        if self.__online and bool(self.locationComboBox.currentText()):
            self.__dictionariesToDownload = [
                itm.data(ManageDictionariesDialog.UrlRole)
                for itm in self.dictionariesList.selectedItems()
            ]

            self.__refreshButton.setEnabled(False)
            self.__installButton.setEnabled(False)
            self.__uninstallButton.setEnabled(False)
            self.__cancelButton.setEnabled(True)

            self.__downloadCancelled = False

            self.__downloadDictionary()

    def __downloadDictionary(self):
        """
        Private slot to download a dictionary.
        """
        if self.__online:
            if self.__dictionariesToDownload:
                url = self.__dictionariesToDownload.pop(0)
                if self.__enforceUnencryptedDownloads or Preferences.getWebBrowser(
                    "ForceHttpDictionaryDownload"
                ):
                    url = url.replace("https://", "http://")
                self.statusLabel.setText(url)

                self.__downloadCancelled = False

                request = QNetworkRequest(QUrl(url))
                request.setAttribute(
                    QNetworkRequest.Attribute.CacheLoadControlAttribute,
                    QNetworkRequest.CacheLoadControl.AlwaysNetwork,
                )
                reply = WebBrowserWindow.networkManager().get(request)
                reply.finished.connect(lambda: self.__installDictionary(reply))
                reply.downloadProgress.connect(self.__downloadProgress)
                self.__replies.append(reply)
            else:
                self.__installationFinished()
        else:
            EricMessageBox.warning(
                self,
                self.tr("Error downloading dictionary file"),
                self.tr(
                    """<p>Could not download the requested dictionary file"""
                    """ from {0}.</p><p>Error: {1}</p>"""
                ).format(url, self.tr("No connection to Internet.")),
            )

            self.__installationFinished()

    def __installDictionary(self, reply):
        """
        Private slot to install the downloaded dictionary.

        @param reply reference to the network reply
        @type QNetworkReply
        """
        if reply in self.__replies:
            self.__replies.remove(reply)
        reply.deleteLater()

        if reply.error() != QNetworkReply.NetworkError.NoError:
            if not self.__downloadCancelled:
                EricMessageBox.warning(
                    self,
                    self.tr("Error downloading dictionary file"),
                    self.tr(
                        """<p>Could not download the requested dictionary"""
                        """ file from {0}.</p><p>Error: {1}</p>"""
                    ).format(reply.url(), reply.errorString()),
                )
            self.downloadProgress.setValue(0)
            return

        archiveData = reply.readAll()
        archiveFile = io.BytesIO(bytes(archiveData))
        archive = zipfile.ZipFile(archiveFile, "r")
        if archive.testzip() is not None:
            EricMessageBox.critical(
                self,
                self.tr("Error downloading dictionary"),
                self.tr(
                    """<p>The downloaded dictionary archive is invalid."""
                    """ Skipping it.</p>"""
                ),
            )
        else:
            installDir = self.locationComboBox.currentText()
            archive.extractall(installDir)

        if self.__dictionariesToDownload:
            self.__downloadDictionary()
        else:
            self.__installationFinished()

    def __installationFinished(self):
        """
        Private method called after all selected dictionaries have been
        installed.
        """
        self.__refreshButton.setEnabled(True)
        self.__cancelButton.setEnabled(False)

        self.dictionariesList.clearSelection()
        self.downloadProgress.setValue(0)

        self.__checkInstalledDictionaries()

    def __uninstallSelected(self):
        """
        Private method to uninstall the selected dictionaries.
        """
        installLocation = self.locationComboBox.currentText()
        if not installLocation:
            return

        itemsToDelete = [
            itm
            for itm in self.dictionariesList.selectedItems()
            if itm.checkState() == Qt.CheckState.Checked
        ]
        for itm in itemsToDelete:
            documentationDir = itm.data(ManageDictionariesDialog.DocumentationDirRole)
            shutil.rmtree(
                os.path.join(installLocation, documentationDir), ignore_errors=True
            )

            locales = itm.data(ManageDictionariesDialog.LocalesRole)
            for locale in locales:
                bdic = os.path.join(installLocation, locale + ".bdic")
                with contextlib.suppress(OSError):
                    os.remove(bdic)

        self.dictionariesList.clearSelection()

        self.__checkInstalledDictionaries()
