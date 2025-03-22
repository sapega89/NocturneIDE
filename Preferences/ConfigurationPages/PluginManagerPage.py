# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Plugin Manager configuration page.
"""

from PyQt6.QtCore import pyqtSlot

from eric7 import Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_PluginManagerPage import Ui_PluginManagerPage


class PluginManagerPage(ConfigurationPageBase, Ui_PluginManagerPage):
    """
    Class implementing the Plugin Manager configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("PluginManagerPage")

        self.downloadDirPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)

        # set initial values
        self.activateExternalPluginsCheckBox.setChecked(
            Preferences.getPluginManager("ActivateExternal")
        )
        self.downloadDirPicker.setText(Preferences.getPluginManager("DownloadPath"))
        self.generationsSpinBox.setValue(
            Preferences.getPluginManager("KeepGenerations")
        )
        self.keepHiddenCheckBox.setChecked(Preferences.getPluginManager("KeepHidden"))
        self.startupCleanupCheckBox.setChecked(
            Preferences.getPluginManager("StartupCleanup")
        )
        self.unencryptedCheckBox.setChecked(
            Preferences.getPluginManager("ForceHttpPluginDownload")
        )

        period = Preferences.getPluginManager("UpdatesCheckInterval")
        if period == 0:
            self.noCheckRadioButton.setChecked(True)
        elif period == 1:
            self.dailyCheckRadioButton.setChecked(True)
        elif period == 2:
            self.weeklyCheckRadioButton.setChecked(True)
        elif period == 3:
            self.monthlyCheckRadioButton.setChecked(True)
        elif period == 4:
            self.alwaysCheckRadioButton.setChecked(True)
        else:
            # invalid value, default to daily
            self.dailyCheckRadioButton.setChecked(True)

        self.downloadedOnlyCheckBox.setChecked(
            Preferences.getPluginManager("CheckInstalledOnly")
        )

        self.__repositoryUrl = Preferences.getUI("PluginRepositoryUrl7")
        self.repositoryUrlEdit.setText(self.__repositoryUrl)

        self.autoInstallCheckBox.setChecked(
            Preferences.getPluginManager("AutoInstallDependencies")
        )

    def save(self):
        """
        Public slot to save the Viewmanager configuration.
        """
        Preferences.setPluginManager(
            "ActivateExternal", self.activateExternalPluginsCheckBox.isChecked()
        )
        Preferences.setPluginManager("DownloadPath", self.downloadDirPicker.text())
        Preferences.setPluginManager("KeepGenerations", self.generationsSpinBox.value())
        Preferences.setPluginManager("KeepHidden", self.keepHiddenCheckBox.isChecked())
        Preferences.setPluginManager(
            "StartupCleanup", self.startupCleanupCheckBox.isChecked()
        )
        Preferences.setPluginManager(
            "ForceHttpPluginDownload", self.unencryptedCheckBox.isChecked()
        )

        if self.noCheckRadioButton.isChecked():
            period = 0
        elif self.dailyCheckRadioButton.isChecked():
            period = 1
        elif self.weeklyCheckRadioButton.isChecked():
            period = 2
        elif self.monthlyCheckRadioButton.isChecked():
            period = 3
        elif self.alwaysCheckRadioButton.isChecked():
            period = 4
        Preferences.setPluginManager("UpdatesCheckInterval", period)

        Preferences.setPluginManager(
            "CheckInstalledOnly", self.downloadedOnlyCheckBox.isChecked()
        )

        if self.repositoryUrlEdit.text() != self.__repositoryUrl:
            Preferences.setUI("PluginRepositoryUrl7", self.repositoryUrlEdit.text())

        Preferences.setPluginManager(
            "AutoInstallDependencies", self.autoInstallCheckBox.isChecked()
        )

    @pyqtSlot(bool)
    def on_repositoryUrlEditButton_toggled(self, checked):
        """
        Private slot to set the read only status of the repository URL line
        edit.

        @param checked state of the push button
        @type bool
        """
        self.repositoryUrlEdit.setReadOnly(not checked)


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = PluginManagerPage()
    return page
