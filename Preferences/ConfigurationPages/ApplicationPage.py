# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Application configuration page.
"""

import multiprocessing

from eric7 import Preferences
from eric7.SystemUtilities import OSUtilities

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_ApplicationPage import Ui_ApplicationPage


class ApplicationPage(ConfigurationPageBase, Ui_ApplicationPage):
    """
    Class implementing the Application configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("ApplicationPage")

        self.backgroundServicesLabel.setText(
            self.tr(
                "<p>eric is using background services for certain things like"
                " syntax checks or code style checks. Per default the number"
                " of processes to use for these checks is determined"
                " automatically based on the number of CPUs. Please note, that"
                " this is an advanced setting.</p>"
                "<p>Available CPUs: <b>{0}</b></p>"
            ).format(multiprocessing.cpu_count())
        )

        self.msgSeverityComboBox.addItem(self.tr("Debug"), 0)
        self.msgSeverityComboBox.addItem(self.tr("Warning"), 1)
        self.msgSeverityComboBox.addItem(self.tr("Critical"), 2)
        self.msgSeverityComboBox.addItem(self.tr("Fatal Error"), 3)

        # set initial values
        self.singleApplicationCheckBox.setChecked(
            Preferences.getUI("SingleApplicationMode")
        )
        self.splashScreenCheckBox.setChecked(Preferences.getUI("ShowSplash"))
        self.globalMenuCheckBox.setChecked(Preferences.getUI("UseNativeMenuBar"))
        if not OSUtilities.isLinuxPlatform() and not OSUtilities.isFreeBsdPlatform():
            self.globalMenuCheckBox.hide()

        openOnStartup = Preferences.getUI("OpenOnStartup")
        if openOnStartup == 0:
            self.noOpenRadioButton.setChecked(True)
        elif openOnStartup == 1:
            self.lastFileRadioButton.setChecked(True)
        elif openOnStartup == 2:
            self.lastProjectRadioButton.setChecked(True)
        elif openOnStartup == 3:
            self.lastMultiprojectRadioButton.setChecked(True)
        elif openOnStartup == 4:
            self.globalSessionRadioButton.setChecked(True)

        period = Preferences.getUI("PerformVersionCheck")
        if period == 0:
            self.noCheckRadioButton.setChecked(True)
        elif period == 1:
            self.alwaysCheckRadioButton.setChecked(True)
        elif period == 2:
            self.dailyCheckRadioButton.setChecked(True)
        elif period == 3:
            self.weeklyCheckRadioButton.setChecked(True)
        elif period == 4:
            self.monthlyCheckRadioButton.setChecked(True)

        self.crashSessionEnabledCheckBox.setChecked(
            Preferences.getUI("CrashSessionEnabled")
        )
        self.openCrashSessionCheckBox.setChecked(
            Preferences.getUI("OpenCrashSessionOnStartup")
        )
        self.deleteCrashSessionCheckBox.setChecked(
            Preferences.getUI("DeleteLoadedCrashSession")
        )

        self.systemEmailClientCheckBox.setChecked(
            Preferences.getUser("UseSystemEmailClient")
        )

        self.errorlogCheckBox.setChecked(Preferences.getUI("CheckErrorLog"))
        severityIndex = self.msgSeverityComboBox.findData(
            Preferences.getUI("MinimumMessageTypeSeverity")
        )
        self.msgSeverityComboBox.setCurrentIndex(severityIndex)

        self.intervalSpinBox.setValue(Preferences.getUI("KeyboardInputInterval"))

        self.backgroundServicesSpinBox.setValue(
            Preferences.getUI("BackgroundServiceProcesses")
        )

        self.upgraderDelaySpinBox.setValue(Preferences.getUI("UpgraderDelay"))

    def save(self):
        """
        Public slot to save the Application configuration.
        """
        Preferences.setUI(
            "SingleApplicationMode", self.singleApplicationCheckBox.isChecked()
        )
        Preferences.setUI("ShowSplash", self.splashScreenCheckBox.isChecked())
        if OSUtilities.isLinuxPlatform() or OSUtilities.isFreeBsdPlatform():
            Preferences.setUI("UseNativeMenuBar", self.globalMenuCheckBox.isChecked())

        if self.noOpenRadioButton.isChecked():
            openOnStartup = 0
        elif self.lastFileRadioButton.isChecked():
            openOnStartup = 1
        elif self.lastProjectRadioButton.isChecked():
            openOnStartup = 2
        elif self.lastMultiprojectRadioButton.isChecked():
            openOnStartup = 3
        elif self.globalSessionRadioButton.isChecked():
            openOnStartup = 4
        Preferences.setUI("OpenOnStartup", openOnStartup)

        if self.noCheckRadioButton.isChecked():
            period = 0
        elif self.alwaysCheckRadioButton.isChecked():
            period = 1
        elif self.dailyCheckRadioButton.isChecked():
            period = 2
        elif self.weeklyCheckRadioButton.isChecked():
            period = 3
        elif self.monthlyCheckRadioButton.isChecked():
            period = 4
        Preferences.setUI("PerformVersionCheck", period)

        Preferences.setUI(
            "CrashSessionEnabled", self.crashSessionEnabledCheckBox.isChecked()
        )
        Preferences.setUI(
            "OpenCrashSessionOnStartup", self.openCrashSessionCheckBox.isChecked()
        )
        Preferences.setUI(
            "DeleteLoadedCrashSession", self.deleteCrashSessionCheckBox.isChecked()
        )

        Preferences.setUser(
            "UseSystemEmailClient", self.systemEmailClientCheckBox.isChecked()
        )

        Preferences.setUI("CheckErrorLog", self.errorlogCheckBox.isChecked())
        Preferences.setUI(
            "MinimumMessageTypeSeverity", self.msgSeverityComboBox.currentData()
        )

        Preferences.setUI("KeyboardInputInterval", self.intervalSpinBox.value())

        Preferences.setUI(
            "BackgroundServiceProcesses", self.backgroundServicesSpinBox.value()
        )

        Preferences.setUI("UpgraderDelay", self.upgraderDelaySpinBox.value())


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = ApplicationPage()
    return page
