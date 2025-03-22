# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the MicroPython configuration page.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QLineEdit

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.MicroPython.MicroPythonReplWidget import AnsiColorSchemes
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities, PythonUtilities

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_MicroPythonPage import Ui_MicroPythonPage

try:
    from PyQt6.QtCharts import QChart
except ImportError:
    QChart = None


class MicroPythonPage(ConfigurationPageBase, Ui_MicroPythonPage):
    """
    Class implementing the MicroPython configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("MicroPythonPage")

        self.showPasswordButton.setIcon(EricPixmapCache.getIcon("showPassword"))
        self.apShowPasswordButton.setIcon(EricPixmapCache.getIcon("showPassword"))

        self.workspacePicker.setMode(EricPathPickerModes.DIRECTORY_MODE)

        self.colorSchemeComboBox.addItems(sorted(AnsiColorSchemes))

        # populate the chart theme combobox
        if QChart is not None:
            self.chartThemeComboBox.addItem(self.tr("Automatic"), -1)
            self.chartThemeComboBox.addItem(
                self.tr("Light"), QChart.ChartTheme.ChartThemeLight
            )
            self.chartThemeComboBox.addItem(
                self.tr("Dark"), QChart.ChartTheme.ChartThemeDark
            )
            self.chartThemeComboBox.addItem(
                self.tr("Blue Cerulean"), QChart.ChartTheme.ChartThemeBlueCerulean
            )
            self.chartThemeComboBox.addItem(
                self.tr("Brown Sand"), QChart.ChartTheme.ChartThemeBrownSand
            )
            self.chartThemeComboBox.addItem(
                self.tr("Blue NCS"), QChart.ChartTheme.ChartThemeBlueNcs
            )
            self.chartThemeComboBox.addItem(
                self.tr("High Contrast"), QChart.ChartTheme.ChartThemeHighContrast
            )
            self.chartThemeComboBox.addItem(
                self.tr("Blue Icy"), QChart.ChartTheme.ChartThemeBlueIcy
            )
            self.chartThemeComboBox.addItem(
                self.tr("Qt"), QChart.ChartTheme.ChartThemeQt
            )
        else:
            self.chartThemeComboBox.setEnabled(False)

        self.mpyCrossPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.mpyCrossPicker.setFilters(self.tr("All Files (*)"))

        self.dfuUtilPathPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.dfuUtilPathPicker.setFilters(self.tr("All Files (*)"))

        self.stInfoPathPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.stInfoPathPicker.setFilters(self.tr("All Files (*)"))
        self.stFlashPathPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.stFlashPathPicker.setFilters(self.tr("All Files (*)"))

        # populate the WiFi security mode combo box
        self.apSecurityComboBox.addItem(self.tr("open"), 0)
        self.apSecurityComboBox.addItem("WEP", 1)
        self.apSecurityComboBox.addItem("WPA", 2)
        self.apSecurityComboBox.addItem("WPA2", 3)
        self.apSecurityComboBox.addItem("WPA/WPA2", 4)
        self.apSecurityComboBox.addItem("WPA2 (CCMP)", 5)
        self.apSecurityComboBox.addItem("WPA3", 6)
        self.apSecurityComboBox.addItem("WPA2/WPA3", 7)

        # set initial values
        # workspace
        self.workspacePicker.setText(
            FileSystemUtilities.toNativeSeparators(
                Preferences.getMicroPython("MpyWorkspace") or OSUtilities.getHomeDir()
            )
        )

        # devices parameters
        self.manualSelectionCheckBox.setChecked(
            Preferences.getMicroPython("EnableManualDeviceSelection")
        )

        # device communication
        self.serialTimeoutSpinBox.setValue(
            Preferences.getMicroPython("SerialTimeout") // 1000
        )  # converted to seconds
        self.webreplTimeoutSpinBox.setValue(
            Preferences.getMicroPython("WebreplTimeout") // 1000
        )  # converted to seconds

        # device time handling
        self.syncTimeCheckBox.setChecked(
            Preferences.getMicroPython("SyncTimeAfterConnect")
        )

        # REPL Pane
        self.colorSchemeComboBox.setCurrentIndex(
            self.colorSchemeComboBox.findText(Preferences.getMicroPython("ColorScheme"))
        )
        self.replWrapCheckBox.setChecked(Preferences.getMicroPython("ReplLineWrap"))

        # Chart Pane
        index = self.chartThemeComboBox.findData(
            Preferences.getMicroPython("ChartColorTheme")
        )
        if index < 0:
            index = 0
        self.chartThemeComboBox.setCurrentIndex(index)

        # WiFi
        self.countryEdit.setText(Preferences.getMicroPython("WifiCountry").upper())
        self.ssidEdit.setText(Preferences.getMicroPython("WifiName"))
        self.passwordEdit.setText(Preferences.getMicroPython("WifiPassword"))
        self.apSsidEdit.setText(Preferences.getMicroPython("WifiApName"))
        self.apPasswordEdit.setText(Preferences.getMicroPython("WifiApPassword"))
        index = self.apSecurityComboBox.findData(
            Preferences.getMicroPython("WifiApAuthMode")
        )
        if index == -1:
            index = 5  # default it to WPA/WPA2 in case of an issue
        self.apSecurityComboBox.setCurrentIndex(index)
        self.apAddressEdit.setText(Preferences.getMicroPython("WifiApAddress"))
        self.apNetmaskEdit.setText(Preferences.getMicroPython("WifiApNetmask"))
        self.apGatewayEdit.setText(Preferences.getMicroPython("WifiApGateway"))
        self.apDnsEdit.setText(Preferences.getMicroPython("WifiApDNS"))

        # NTP
        self.ntpServerEdit.setText(Preferences.getMicroPython("NtpServer"))
        self.ntpOffsetSpinBox.setValue(Preferences.getMicroPython("NtpOffset"))
        self.ntpDstCheckBox.setChecked(Preferences.getMicroPython("NtpDaylight"))
        self.ntpTimeoutSpinBox.setValue(Preferences.getMicroPython("NtpTimeout"))

        # MPY Cross Compiler
        self.mpyCrossPicker.setText(Preferences.getMicroPython("MpyCrossCompiler"))

        # PyBoard specifics
        self.dfuUtilPathPicker.setText(Preferences.getMicroPython("DfuUtilPath"))

        # STLink specifics
        self.stInfoPathPicker.setText(Preferences.getMicroPython("StInfoPath"))
        self.stFlashPathPicker.setText(Preferences.getMicroPython("StFlashPath"))

        # MicroPython URLs
        self.micropythonFirmwareUrlLineEdit.setText(
            Preferences.getMicroPython("MicroPythonFirmwareUrl")
        )
        self.micropythonDocuUrlLineEdit.setText(
            Preferences.getMicroPython("MicroPythonDocuUrl")
        )

        # CircuitPython URLs
        self.circuitpythonFirmwareUrlLineEdit.setText(
            Preferences.getMicroPython("CircuitPythonFirmwareUrl")
        )
        self.circuitpythonLibrariesUrlLineEdit.setText(
            Preferences.getMicroPython("CircuitPythonLibrariesUrl")
        )
        self.circuitpythonDocuUrlLineEdit.setText(
            Preferences.getMicroPython("CircuitPythonDocuUrl")
        )

        # BBC micro:bit URLs
        self.microbitFirmwareUrlLineEdit.setText(
            Preferences.getMicroPython("MicrobitFirmwareUrl")
        )
        self.microbitV1MicroPythonUrlLineEdit.setText(
            Preferences.getMicroPython("MicrobitMicroPythonUrl")
        )
        self.microbitV2MicroPythonUrlLineEdit.setText(
            Preferences.getMicroPython("MicrobitV2MicroPythonUrl")
        )
        self.microbitDocuUrlLineEdit.setText(
            Preferences.getMicroPython("MicrobitDocuUrl")
        )

        # Calliope mini URLs
        self.calliopeFirmwareUrlLineEdit.setText(
            Preferences.getMicroPython("CalliopeDAPLinkUrl")
        )
        self.calliopeMicroPythonUrlLineEdit.setText(
            Preferences.getMicroPython("CalliopeMicroPythonUrl")
        )
        self.calliopeDocuUrlLineEdit.setText(
            Preferences.getMicroPython("CalliopeDocuUrl")
        )

    def save(self):
        """
        Public slot to save the MicroPython configuration.
        """
        # workspace
        Preferences.setMicroPython("MpyWorkspace", self.workspacePicker.text())

        # devices parameters
        Preferences.setMicroPython(
            "EnableManualDeviceSelection", self.manualSelectionCheckBox.isChecked()
        )

        # device communication
        Preferences.setMicroPython(
            "SerialTimeout", self.serialTimeoutSpinBox.value() * 1000
        )  # converted to milliseconds
        Preferences.setMicroPython(
            "WebreplTimeout", self.webreplTimeoutSpinBox.value() * 1000
        )  # converted to milliseconds

        # device time handling
        Preferences.setMicroPython(
            "SyncTimeAfterConnect", self.syncTimeCheckBox.isChecked()
        )

        # REPL Pane
        Preferences.setMicroPython(
            "ColorScheme", self.colorSchemeComboBox.currentText()
        )
        Preferences.setMicroPython("ReplLineWrap", self.replWrapCheckBox.isChecked())

        # Chart Pane
        Preferences.setMicroPython(
            "ChartColorTheme", self.chartThemeComboBox.currentData()
        )

        # WiFi
        Preferences.setMicroPython("WifiCountry", self.countryEdit.text().upper())
        Preferences.setMicroPython("WifiName", self.ssidEdit.text())
        Preferences.setMicroPython("WifiPassword", self.passwordEdit.text())
        Preferences.setMicroPython("WifiApName", self.apSsidEdit.text())
        Preferences.setMicroPython("WifiApPassword", self.apPasswordEdit.text())
        Preferences.setMicroPython(
            "WifiApAuthMode", self.apSecurityComboBox.currentData()
        )
        Preferences.setMicroPython("WifiApAddress", self.apAddressEdit.text())
        Preferences.setMicroPython("WifiApNetmask", self.apNetmaskEdit.text())
        Preferences.setMicroPython("WifiApGateway", self.apGatewayEdit.text())
        Preferences.setMicroPython("WifiApDNS", self.apDnsEdit.text())

        # NTP
        Preferences.setMicroPython("NtpServer", self.ntpServerEdit.text())
        Preferences.setMicroPython("NtpOffset", self.ntpOffsetSpinBox.value())
        Preferences.setMicroPython("NtpDaylight", self.ntpDstCheckBox.isChecked())
        Preferences.setMicroPython("NtpTimeout", self.ntpTimeoutSpinBox.value())

        # MPY Cross Compiler
        Preferences.setMicroPython("MpyCrossCompiler", self.mpyCrossPicker.text())

        # PyBoard specifics
        Preferences.setMicroPython("DfuUtilPath", self.dfuUtilPathPicker.text())

        # STLink specifics
        Preferences.setMicroPython("StInfoPath", self.stInfoPathPicker.text())
        Preferences.setMicroPython("StFlashPath", self.stFlashPathPicker.text())

        # MicroPython URLs
        Preferences.setMicroPython(
            "MicroPythonFirmwareUrl", self.micropythonFirmwareUrlLineEdit.text()
        )
        Preferences.setMicroPython(
            "MicroPythonDocuUrl", self.micropythonDocuUrlLineEdit.text()
        )

        # CircuitPython URLs
        Preferences.setMicroPython(
            "CircuitPythonFirmwareUrl", self.circuitpythonFirmwareUrlLineEdit.text()
        )
        Preferences.setMicroPython(
            "CircuitPythonLibrariesUrl", self.circuitpythonLibrariesUrlLineEdit.text()
        )
        Preferences.setMicroPython(
            "CircuitPythonDocuUrl", self.circuitpythonDocuUrlLineEdit.text()
        )

        # BBC micro:bit URLs
        Preferences.setMicroPython(
            "MicrobitFirmwareUrl", self.microbitFirmwareUrlLineEdit.text()
        )
        Preferences.setMicroPython(
            "MicrobitMicroPythonUrl", self.microbitV1MicroPythonUrlLineEdit.text()
        )
        Preferences.setMicroPython(
            "MicrobitV2MicroPythonUrl", self.microbitV2MicroPythonUrlLineEdit.text()
        )
        Preferences.setMicroPython(
            "MicrobitDocuUrl", self.microbitDocuUrlLineEdit.text()
        )

        # Calliope mini URLs
        Preferences.setMicroPython(
            "CalliopeDAPLinkUrl", self.calliopeFirmwareUrlLineEdit.text()
        )
        Preferences.setMicroPython(
            "CalliopeMicroPythonUrl", self.calliopeMicroPythonUrlLineEdit.text()
        )
        Preferences.setMicroPython(
            "CalliopeDocuUrl", self.calliopeDocuUrlLineEdit.text()
        )

    @pyqtSlot(bool)
    def on_showPasswordButton_clicked(self, checked):
        """
        Private slot to show or hide the WiFi client password.

        @param checked state of the button
        @type bool
        """
        if checked:
            self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.showPasswordButton.setIcon(EricPixmapCache.getIcon("hidePassword"))
            self.showPasswordButton.setToolTip(self.tr("Press to hide the password"))
        else:
            self.passwordEdit.setEchoMode(QLineEdit.EchoMode.Password)
            self.showPasswordButton.setIcon(EricPixmapCache.getIcon("showPassword"))
            self.showPasswordButton.setToolTip(self.tr("Press to show the password"))

    @pyqtSlot(bool)
    def on_apShowPasswordButton_clicked(self, checked):
        """
        Private slot to show or hide the WiFi Access Point password.

        @param checked state of the button
        @type bool
        """
        if checked:
            self.apPasswordEdit.setEchoMode(QLineEdit.EchoMode.Normal)
            self.apShowPasswordButton.setIcon(EricPixmapCache.getIcon("hidePassword"))
            self.apShowPasswordButton.setToolTip(self.tr("Press to hide the password"))
        else:
            self.apPasswordEdit.setEchoMode(QLineEdit.EchoMode.Password)
            self.apShowPasswordButton.setIcon(EricPixmapCache.getIcon("showPassword"))
            self.apShowPasswordButton.setToolTip(self.tr("Press to show the password"))

    @pyqtSlot()
    def on_mpyCrossInstallButton_clicked(self):
        """
        Private slot to install the 'mpy-cross' compiler.
        """
        pip = ericApp().getObject("Pip")
        pip.installPackages(
            ["mpy-cross"], interpreter=PythonUtilities.getPythonExecutable()
        )

        mpycrossPath = os.path.join(
            PythonUtilities.getPythonScriptsDirectory(), "mpy-cross"
        )
        if OSUtilities.isWindowsPlatform():
            mpycrossPath += ".exe"
        self.mpyCrossPicker.setText(mpycrossPath)

    @pyqtSlot(str)
    def on_mpyCrossPicker_textChanged(self, mpycrossPath):
        """
        Private slot to handle a change of the selected 'mpy-cross' compiler.

        @param mpycrossPath entered path of the 'mpy-cross' compiler
        @type str
        """
        self.mpyCrossInstallButton.setEnabled(not bool(mpycrossPath))


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    return MicroPythonPage()
