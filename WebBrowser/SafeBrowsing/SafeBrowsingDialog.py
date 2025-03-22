# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to configure safe browsing support.
"""

from PyQt6.QtCore import QDateTime, Qt, QUrl, pyqtSlot
from PyQt6.QtWidgets import QAbstractButton, QDialog, QDialogButtonBox

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricSimpleHelpDialog import EricSimpleHelpDialog

from .Ui_SafeBrowsingDialog import Ui_SafeBrowsingDialog


class SafeBrowsingDialog(QDialog, Ui_SafeBrowsingDialog):
    """
    Class implementing a dialog to configure safe browsing support.
    """

    def __init__(self, manager, parent=None):
        """
        Constructor

        @param manager reference to the safe browsing manager
        @type SafeBrowsingManager
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.__manager = manager
        self.__manager.progressMessage.connect(self.__setProgressMessage)
        self.__manager.progress.connect(self.__setProgress)

        self.iconLabel.setPixmap(EricPixmapCache.getPixmap("safeBrowsing48"))

        self.__gsbHelpDialog = None

        self.__enabled = Preferences.getWebBrowser("SafeBrowsingEnabled")
        self.__apiKey = Preferences.getWebBrowser("SafeBrowsingApiKey")
        self.__filterPlatform = Preferences.getWebBrowser("SafeBrowsingFilterPlatform")
        self.__automaticUpdate = Preferences.getWebBrowser("SafeBrowsingAutoUpdate")
        self.__useLookupApi = Preferences.getWebBrowser("SafeBrowsingUseLookupApi")

        self.buttonBox.setFocus()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def show(self):
        """
        Public slot to show the dialog.
        """
        self.gsbGroupBox.setChecked(self.__enabled)
        self.gsbApiKeyEdit.setText(self.__apiKey)
        self.gsbFilterPlatformCheckBox.setChecked(self.__filterPlatform)
        self.gsbAutoUpdateCheckBox.setChecked(self.__automaticUpdate)
        self.gsbLookupCheckBox.setChecked(self.__useLookupApi)

        self.__updateCacheButtons()

        super().show()

    @pyqtSlot()
    def on_gsbHelpButton_clicked(self):
        """
        Private slot to show some help text "How to create a safe
        browsing API key.".
        """
        from . import SafeBrowsingHelp

        if self.__gsbHelpDialog is None:
            helpStr = SafeBrowsingHelp()
            self.__gsbHelpDialog = EricSimpleHelpDialog(
                title=self.tr("Google Safe Browsing API Help"),
                helpStr=helpStr,
                parent=self,
            )

        self.__gsbHelpDialog.show()

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Close):
            self.close()

    @pyqtSlot()
    def __save(self):
        """
        Private slot to save the configuration.

        @return flag indicating success
        @rtype bool
        """
        self.__enabled = self.gsbGroupBox.isChecked()
        self.__apiKey = self.gsbApiKeyEdit.text()
        self.__filterPlatform = self.gsbFilterPlatformCheckBox.isChecked()
        self.__automaticUpdate = self.gsbAutoUpdateCheckBox.isChecked()
        self.__useLookupApi = self.gsbLookupCheckBox.isChecked()

        Preferences.setWebBrowser("SafeBrowsingEnabled", self.__enabled)
        Preferences.setWebBrowser("SafeBrowsingApiKey", self.__apiKey)
        Preferences.setWebBrowser("SafeBrowsingFilterPlatform", self.__filterPlatform)
        Preferences.setWebBrowser("SafeBrowsingAutoUpdate", self.__automaticUpdate)
        Preferences.setWebBrowser("SafeBrowsingUseLookupApi", self.__useLookupApi)

        self.__manager.configurationChanged()

        self.__updateCacheButtons()

        return True

    def closeEvent(self, evt):
        """
        Protected method to handle close events.

        @param evt reference to the close event
        @type QCloseEvent
        """
        if self.__okToClose():
            evt.accept()
        else:
            evt.ignore()

    def __isModified(self):
        """
        Private method to check, if the dialog contains modified data.

        @return flag indicating the presence of modified data
        @rtype bool
        """
        return (
            (self.__enabled != self.gsbGroupBox.isChecked())
            or (self.__apiKey != self.gsbApiKeyEdit.text())
            or (self.__filterPlatform != self.gsbFilterPlatformCheckBox.isChecked())
            or (self.__automaticUpdate != self.gsbAutoUpdateCheckBox.isChecked())
            or (self.__useLookupApi != self.gsbLookupCheckBox.isChecked())
        )

    def __okToClose(self):
        """
        Private method to check, if it is safe to close the dialog.

        @return flag indicating safe to close
        @rtype bool
        """
        if self.__isModified():
            res = EricMessageBox.okToClearData(
                self,
                self.tr("Safe Browsing Management"),
                self.tr("""The dialog contains unsaved changes."""),
                self.__save,
            )
            if not res:
                return False
        return True

    def __updateCacheButtons(self):
        """
        Private method to set enabled state of the cache buttons.
        """
        enable = self.__enabled and bool(self.__apiKey)

        self.updateCacheButton.setEnabled(enable)
        self.clearCacheButton.setEnabled(enable)

        self.showUpdateTimeButton.setEnabled(enable and self.__automaticUpdate)

    @pyqtSlot()
    def on_updateCacheButton_clicked(self):
        """
        Private slot to update the local cache database.
        """
        EricMessageBox.information(
            self,
            self.tr("Update Safe Browsing Cache"),
            self.tr(
                """Updating the Safe Browsing cache might be a lengthy"""
                """ operation. Please be patient!"""
            ),
        )

        with EricOverrideCursor():
            ok, error = self.__manager.updateHashPrefixCache()
            self.__resetProgress()
        if not ok:
            if error:
                EricMessageBox.critical(
                    self,
                    self.tr("Update Safe Browsing Cache"),
                    self.tr(
                        """<p>Updating the Safe Browsing cache failed."""
                        """</p><p>Reason: {0}</p>"""
                    ).format(error),
                )
            else:
                EricMessageBox.critical(
                    self,
                    self.tr("Update Safe Browsing Cache"),
                    self.tr("""<p>Updating the Safe Browsing cache failed.</p>"""),
                )

    @pyqtSlot()
    def on_clearCacheButton_clicked(self):
        """
        Private slot to clear the local cache database.
        """
        res = EricMessageBox.yesNo(
            self,
            self.tr("Clear Safe Browsing Cache"),
            self.tr(
                """Do you really want to clear the Safe Browsing cache?"""
                """ Re-populating it might take some time."""
            ),
        )
        if res:
            with EricOverrideCursor():
                self.__manager.fullCacheCleanup()

    @pyqtSlot(str, int)
    def __setProgressMessage(self, message, maximum):
        """
        Private slot to set the progress message and the maximum value.

        @param message progress message to be set
        @type str
        @param maximum maximum value to be set
        @type int
        """
        self.progressLabel.setText(message)
        self.progressBar.setMaximum(maximum)
        self.progressBar.setValue(0)

    @pyqtSlot(int)
    def __setProgress(self, value):
        """
        Private slot to set the progress value.

        @param value progress value to be set
        @type int
        """
        if bool(self.progressLabel.text()):
            self.progressBar.setValue(value)

    def __resetProgress(self):
        """
        Private method to reset the progress info.
        """
        self.progressLabel.clear()
        self.progressBar.setMaximum(100)
        self.progressBar.setValue(0)

    @pyqtSlot(str)
    def on_urlEdit_textChanged(self, text):
        """
        Private slot to handle changes of the entered URL text.

        @param text entered URL text
        @type str
        """
        url = QUrl.fromUserInput(text)
        enable = (
            url.isValid()
            and bool(url.scheme())
            and url.scheme() not in self.__manager.getIgnoreSchemes()
        )
        self.urlCheckButton.setEnabled(enable)

    @pyqtSlot()
    def on_urlCheckButton_clicked(self):
        """
        Private slot to check the entered URL.
        """
        # Malicious URL for testing:
        # http://malware.testing.google.test/testing/malware/*
        # http://ianfette.org
        #
        urlStr = self.urlEdit.text()
        url = QUrl.fromUserInput(urlStr)
        threatLists, error = self.__manager.lookupUrl(url)

        if error:
            EricMessageBox.warning(
                self,
                self.tr("Check URL"),
                self.tr(
                    "<p>The Google Safe Browsing Server reported an"
                    " error.</p><p>{0}</p>"
                ).format(error),
            )
        elif threatLists:
            threatMessages = self.__manager.getThreatMessages(threatLists)
            EricMessageBox.warning(
                self,
                self.tr("Check URL"),
                self.tr(
                    "<p>The URL <b>{0}</b> was found in the Safe"
                    " Browsing Database.</p>{1}"
                ).format(urlStr, "".join(threatMessages)),
            )
        else:
            EricMessageBox.information(
                self,
                self.tr("Check URL"),
                self.tr(
                    "<p>The URL <b>{0}</b> was not found in the Safe"
                    " Browsing Database and may be considered safe."
                    "</p>"
                ).format(urlStr),
            )

    @pyqtSlot()
    def on_saveButton_clicked(self):
        """
        Private slot to save the configuration data.
        """
        self.__save()

    @pyqtSlot()
    def on_showUpdateTimeButton_clicked(self):
        """
        Private slot to show the time of the next automatic threat list update.
        """
        nextUpdateDateTime = Preferences.getWebBrowser("SafeBrowsingUpdateDateTime")
        message = (
            self.tr("The next automatic threat list update will be done now.")
            if (
                not nextUpdateDateTime.isValid()
                or nextUpdateDateTime <= QDateTime.currentDateTime()
            )
            else self.tr(
                "<p>The next automatic threat list update will be done at"
                " <b>{0}</b>.</p>"
            ).format(nextUpdateDateTime.toString("yyyy-MM-dd, HH:mm:ss"))
        )

        EricMessageBox.information(self, self.tr("Update Time"), message)
