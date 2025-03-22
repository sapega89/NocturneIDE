# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Network configuration page.
"""

from eric7 import Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_NetworkPage import Ui_NetworkPage


class NetworkPage(ConfigurationPageBase, Ui_NetworkPage):
    """
    Class implementing the Network configuration page.
    """

    def __init__(self, configDialog):
        """
        Constructor

        @param configDialog reference to the configuration dialog
        @type ConfigurationDialog
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("NetworkPage")

        self.__configDlg = configDialog
        self.__displayMode = None
        self.__webEngine = False

        self.downloadDirPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)

        # set initial values
        self.dynamicOnlineCheckBox.setChecked(Preferences.getUI("DynamicOnlineCheck"))

        self.downloadDirPicker.setText(Preferences.getUI("DownloadPath"))
        self.requestFilenameCheckBox.setChecked(
            Preferences.getUI("RequestDownloadFilename")
        )

    def setMode(self, displayMode):
        """
        Public method to perform mode dependent setups.

        @param displayMode mode of the configuration dialog
        @type ConfigurationMode
        """
        from ..ConfigurationDialog import ConfigurationMode

        if displayMode in (
            ConfigurationMode.DEFAULTMODE,
            ConfigurationMode.WEBBROWSERMODE,
        ):
            self.__displayMode = displayMode
            if not self.__configDlg.isUsingWebEngine():
                self.cleanupGroup.hide()
                self.displayGroup.hide()
            else:
                from eric7.WebBrowser.Download.DownloadManager import (  # noqa
                    DownloadManagerDefaultRemovePolicy,
                    DownloadManagerRemovePolicy,
                )

                try:
                    policy = DownloadManagerRemovePolicy(
                        Preferences.getWebBrowser("DownloadManagerRemovePolicy")
                    )
                except ValueError:
                    # reset to default
                    policy = DownloadManagerDefaultRemovePolicy

                if policy == DownloadManagerRemovePolicy.Never:
                    self.cleanupNeverButton.setChecked(True)
                elif policy == DownloadManagerRemovePolicy.Exit:
                    self.cleanupExitButton.setChecked(True)
                else:
                    self.cleanupSuccessfulButton.setChecked(True)
                self.openOnStartCheckBox.setChecked(
                    Preferences.getWebBrowser("DownloadManagerAutoOpen")
                )
                self.closeOnFinishedCheckBox.setChecked(
                    Preferences.getWebBrowser("DownloadManagerAutoClose")
                )
                self.__webEngine = True

    def save(self):
        """
        Public slot to save the Networj configuration.
        """
        Preferences.setUI("DynamicOnlineCheck", self.dynamicOnlineCheckBox.isChecked())
        Preferences.setUI("DownloadPath", self.downloadDirPicker.text())
        Preferences.setUI(
            "RequestDownloadFilename", self.requestFilenameCheckBox.isChecked()
        )
        if self.__webEngine:
            from eric7.WebBrowser.Download.DownloadManager import (  # noqa: I101
                DownloadManagerRemovePolicy,
            )

            if self.cleanupNeverButton.isChecked():
                policy = DownloadManagerRemovePolicy.Never
            elif self.cleanupExitButton.isChecked():
                policy = DownloadManagerRemovePolicy.Exit
            else:
                policy = DownloadManagerRemovePolicy.SuccessfullDownload
            Preferences.setWebBrowser("DownloadManagerRemovePolicy", policy.value)
            Preferences.setWebBrowser(
                "DownloadManagerAutoOpen", self.openOnStartCheckBox.isChecked()
            )
            Preferences.setWebBrowser(
                "DownloadManagerAutoClose", self.closeOnFinishedCheckBox.isChecked()
            )


def create(dlg):
    """
    Module function to create the configuration page.

    @param dlg reference to the configuration dialog
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = NetworkPage(dlg)
    return page
