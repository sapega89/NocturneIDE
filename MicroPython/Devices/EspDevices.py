# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the device interface class for ESP32 and ESP8266 based
boards.
"""

import ast
import binascii
import json
import os

from PyQt6.QtCore import QCoreApplication, QProcess, QUrl, pyqtSlot
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import QDialog, QMenu

from eric7 import EricUtilities, Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricProcessDialog import EricProcessDialog
from eric7.SystemUtilities import PythonUtilities

from ..MicroPythonWidget import HAS_QTCHART
from . import FirmwareGithubUrls
from .CircuitPythonDevices import CircuitPythonDevice
from .DeviceBase import BaseDevice


class EspDevice(BaseDevice):
    """
    Class implementing the device for ESP32 and ESP8266 based boards.
    """

    def __init__(self, microPythonWidget, deviceType, parent=None):
        """
        Constructor

        @param microPythonWidget reference to the main MicroPython widget
        @type MicroPythonWidget
        @param deviceType device type assigned to this device interface
        @type str
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(microPythonWidget, deviceType, parent)

        self.__createEsp32Submenu()

        self.__cpyDevice = None
        # needed to delegate some methods to a CircuitPython variant

        self.__statusTranslations = {
            200: self.tr("beacon timeout"),
            201: self.tr("no matching access point found"),
            202: self.tr("authentication failed"),
            203: self.tr("association failed"),
            204: self.tr("handshake timeout"),
            210: self.tr("no access point with compatible security found"),
            211: self.tr("no access point with suitable authentication mode found"),
            212: self.tr("no access point with sufficient RSSI found"),
            1000: self.tr("idle"),
            1001: self.tr("connecting"),
            1010: self.tr("connected"),
        }
        self.__securityTranslations = {
            0: self.tr("open", "open WiFi network"),
            1: "WEP",
            2: "WPA",
            3: "WPA2",
            4: "WPA/WPA2",
            5: "WPA2 (CCMP)",
            6: "WPA3",
            7: "WPA2/WPA3",
        }

    def __createCpyDevice(self):
        """
        Private method to create a CircuitPython device interface.
        """
        if self.hasCircuitPython() and self.__cpyDevice is None:
            self.__cpyDevice = CircuitPythonDevice(
                self.microPython,
                "esp32_circuitpython",
                "esp32",
                hasWorkspace=False,
                parent=self.parent(),
            )
            self.__cpyDevice.setConnected(True)

    def setConnected(self, connected):
        """
        Public method to set the connection state.

        Note: This method can be overwritten to perform actions upon connect
        or disconnect of the device.

        @param connected connection state
        @type bool
        """
        super().setConnected(connected)

        if self.hasCircuitPython():
            self._submitMode = "paste"
            self.__createCpyDevice()

    def setButtons(self):
        """
        Public method to enable the supported action buttons.
        """
        super().setButtons()

        self.microPython.setActionButtons(
            run=True, repl=True, files=True, chart=HAS_QTCHART
        )

    def forceInterrupt(self):
        """
        Public method to determine the need for an interrupt when opening the
        serial connection.

        @return flag indicating an interrupt is needed
        @rtype bool
        """
        return True

    def deviceName(self):
        """
        Public method to get the name of the device.

        @return name of the device
        @rtype str
        """
        return self.tr("ESP8266, ESP32")

    def canStartRepl(self):
        """
        Public method to determine, if a REPL can be started.

        @return tuple containing a flag indicating it is safe to start a REPL
            and a reason why it cannot.
        @rtype tuple of (bool, str)
        """
        return True, ""

    def canStartPlotter(self):
        """
        Public method to determine, if a Plotter can be started.

        @return tuple containing a flag indicating it is safe to start a
            Plotter and a reason why it cannot.
        @rtype tuple of (bool, str)
        """
        return True, ""

    def canRunScript(self):
        """
        Public method to determine, if a script can be executed.

        @return tuple containing a flag indicating it is safe to start a
            Plotter and a reason why it cannot.
        @rtype tuple of (bool, str)
        """
        return True, ""

    def runScript(self, script):
        """
        Public method to run the given Python script.

        @param script script to be executed
        @type str
        """
        pythonScript = script.split("\n")
        self.sendCommands(pythonScript)

    def canStartFileManager(self):
        """
        Public method to determine, if a File Manager can be started.

        @return tuple containing a flag indicating it is safe to start a
            File Manager and a reason why it cannot.
        @rtype tuple of (bool, str)
        """
        return True, ""

    def __createEsp32Submenu(self):
        """
        Private method to create the ESP32 submenu.
        """
        self.__espMenu = QMenu(self.tr("ESP32 Functions"))

        self.__showMpyAct = self.__espMenu.addAction(
            self.tr("Show MicroPython Versions"), self.__showFirmwareVersions
        )
        self.__espMenu.addSeparator()
        self.__eraseFlashAct = self.__espMenu.addAction(
            self.tr("Erase Flash"), self.__eraseFlash
        )
        self.__flashMpyAct = self.__espMenu.addAction(
            self.tr("Flash MicroPython Firmware"), self.__flashMicroPython
        )
        self.__espMenu.addSeparator()
        self.__flashAdditionalAct = self.__espMenu.addAction(
            self.tr("Flash Additional Firmware"), self.__flashAddons
        )
        self.__espMenu.addSeparator()
        self.__backupAct = self.__espMenu.addAction(
            self.tr("Backup Firmware"), self.__backupFlash
        )
        self.__restoreAct = self.__espMenu.addAction(
            self.tr("Restore Firmware"), self.__restoreFlash
        )
        self.__espMenu.addSeparator()
        self.__chipIdAct = self.__espMenu.addAction(
            self.tr("Show Chip ID"), self.__showChipID
        )
        self.__flashIdAct = self.__espMenu.addAction(
            self.tr("Show Flash ID"), self.__showFlashID
        )
        self.__macAddressAct = self.__espMenu.addAction(
            self.tr("Show MAC Address"), self.__showMACAddress
        )
        self.__securityInfoAct = self.__espMenu.addAction(
            self.tr("Show Security Information"), self.__showSecurityInfo
        )
        self.__espMenu.addSeparator()
        self.__resetAct = self.__espMenu.addAction(
            self.tr("Reset Device"), self.__resetDevice
        )
        self.__espMenu.addSeparator()
        self.__espMenu.addAction(self.tr("Install 'esptool.py'"), self.__installEspTool)

    def addDeviceMenuEntries(self, menu):
        """
        Public method to add device specific entries to the given menu.

        @param menu reference to the context menu
        @type QMenu
        """
        connected = self.microPython.isConnected()
        linkConnected = self.microPython.isLinkConnected()

        self.__showMpyAct.setEnabled(connected)
        self.__eraseFlashAct.setEnabled(not linkConnected)
        self.__flashMpyAct.setEnabled(not linkConnected)
        self.__flashAdditionalAct.setEnabled(not linkConnected)
        self.__backupAct.setEnabled(not linkConnected)
        self.__restoreAct.setEnabled(not linkConnected)
        self.__chipIdAct.setEnabled(not linkConnected)
        self.__flashIdAct.setEnabled(not linkConnected)
        self.__macAddressAct.setEnabled(not linkConnected)
        self.__securityInfoAct.setEnabled(not linkConnected)
        self.__resetAct.setEnabled(connected or not linkConnected)

        menu.addMenu(self.__espMenu)

    def hasFlashMenuEntry(self):
        """
        Public method to check, if the device has its own flash menu entry.

        @return flag indicating a specific flash menu entry
        @rtype bool
        """
        return True

    @pyqtSlot()
    def __eraseFlash(self):
        """
        Private slot to erase the device flash memory.
        """
        eraseFlash(self.microPython.getCurrentPort(), parent=self.microPython)

    @pyqtSlot()
    def __flashMicroPython(self):
        """
        Private slot to flash a MicroPython firmware to the device.
        """
        flashPythonFirmware(self.microPython.getCurrentPort(), parent=self.microPython)

    @pyqtSlot()
    def __flashAddons(self):
        """
        Private slot to flash some additional firmware images.
        """
        flashAddonFirmware(self.microPython.getCurrentPort(), parent=self.microPython)

    @pyqtSlot()
    def __backupFlash(self):
        """
        Private slot to backup the currently flashed firmware.
        """
        from .EspDialogs.EspBackupRestoreFirmwareDialog import (
            EspBackupRestoreFirmwareDialog,
        )

        dlg = EspBackupRestoreFirmwareDialog(backupMode=True, parent=self.microPython)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            chip, flashSize, baudRate, flashMode, firmware = dlg.getData()
            flashArgs = [
                "-u",
                "-m",
                "esptool",
                "--chip",
                chip,
                "--port",
                self.microPython.getCurrentPort(),
                "--baud",
                baudRate,
                "read_flash",
                "0x0",
                flashSize,
                firmware,
            ]
            dlg = EricProcessDialog(
                self.tr("'esptool read_flash' Output"),
                self.tr("Backup Firmware"),
                showProgress=True,
                monospacedFont=Preferences.getEditorOtherFonts("MonospacedFont"),
                encoding=Preferences.getSystem("IOEncoding"),
                parent=self.microPython,
            )
            res = dlg.startProcess(PythonUtilities.getPythonExecutable(), flashArgs)
            if res:
                dlg.exec()

    @pyqtSlot()
    def __restoreFlash(self):
        """
        Private slot to restore a previously saved firmware.
        """
        from .EspDialogs.EspBackupRestoreFirmwareDialog import (
            EspBackupRestoreFirmwareDialog,
        )

        dlg = EspBackupRestoreFirmwareDialog(backupMode=False, parent=self.microPython)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            chip, flashSize, baudRate, flashMode, firmware = dlg.getData()
            flashArgs = [
                "-u",
                "-m",
                "esptool",
                "--chip",
                chip,
                "--port",
                self.microPython.getCurrentPort(),
                "--baud",
                baudRate,
                "write_flash",
            ]
            if flashMode:
                flashArgs.extend(
                    [
                        "--flash_mode",
                        flashMode,
                    ]
                )
            if bool(flashSize):
                flashArgs.extend(
                    [
                        "--flash_size",
                        flashSize,
                    ]
                )
            flashArgs.extend(
                [
                    "0x0",
                    firmware,
                ]
            )
            dlg = EricProcessDialog(
                self.tr("'esptool write_flash' Output"),
                self.tr("Restore Firmware"),
                showProgress=True,
                monospacedFont=Preferences.getEditorOtherFonts("MonospacedFont"),
                encoding=Preferences.getSystem("IOEncoding"),
                parent=self.microPython,
            )
            res = dlg.startProcess(PythonUtilities.getPythonExecutable(), flashArgs)
            if res:
                dlg.exec()

    @pyqtSlot()
    def __showFirmwareVersions(self):
        """
        Private slot to show the firmware version of the connected device and the
        available firmware version.
        """
        if self.hasCircuitPython():
            self.__cpyDevice.showCircuitPythonVersions()

        elif self.microPython.isConnected():
            if self._deviceData["mpy_name"] == "micropython":
                url = QUrl(FirmwareGithubUrls["micropython"])
            elif self._deviceData["mpy_name"] == "circuitpython":
                url = QUrl(FirmwareGithubUrls["circuitpython"])
            else:
                EricMessageBox.critical(
                    self.microPython,
                    self.tr("Show MicroPython Versions"),
                    self.tr(
                        """The firmware of the connected device cannot be"""
                        """ determined or the board does not run MicroPython"""
                        """ or CircuitPython. Aborting..."""
                    ),
                )
                return

            ui = ericApp().getObject("UserInterface")
            request = QNetworkRequest(url)
            reply = ui.networkAccessManager().head(request)
            reply.finished.connect(lambda: self.__firmwareVersionResponse(reply))

    @pyqtSlot(QNetworkReply)
    def __firmwareVersionResponse(self, reply):
        """
        Private slot handling the response of the latest version request.

        @param reply reference to the reply object
        @type QNetworkReply
        """
        latestUrl = reply.url().toString()
        tag = latestUrl.rsplit("/", 1)[-1]
        while tag and not tag[0].isdecimal():
            # get rid of leading non-decimal characters
            tag = tag[1:]
        latestVersion = EricUtilities.versionToTuple(tag)

        if self._deviceData["mpy_version"] == "unknown":
            currentVersionStr = self.tr("unknown")
            currentVersion = (0, 0, 0)
        else:
            currentVersionStr = self._deviceData["mpy_version"]
            currentVersion = EricUtilities.versionToTuple(currentVersionStr)

        if self._deviceData["mpy_name"] == "circuitpython":
            kind = "CircuitPython"
        elif self._deviceData["mpy_name"] == "micropython":
            kind = "MicroPython"

        msg = self.tr(
            "<h4>{0} Version Information</h4>"
            "<table>"
            "<tr><td>Installed:</td><td>{1}</td></tr>"
            "<tr><td>Available:</td><td>{2}</td></tr>"
            "</table>"
        ).format(kind, currentVersionStr, tag)
        if currentVersion < latestVersion:
            msg += self.tr("<p><b>Update available!</b></p>")

        EricMessageBox.information(
            self.microPython,
            self.tr("{0} Version").format(kind),
            msg,
        )

    @pyqtSlot()
    def __showChipID(self):
        """
        Private slot to show the ID of the ESP chip.
        """
        args = [
            "-u",
            "-m",
            "esptool",
            "--port",
            self.microPython.getCurrentPort(),
            "chip_id",
        ]
        dlg = EricProcessDialog(
            self.tr("'esptool chip_id' Output"),
            self.tr("Show Chip ID"),
            monospacedFont=Preferences.getEditorOtherFonts("MonospacedFont"),
            encoding=Preferences.getSystem("IOEncoding"),
            parent=self.microPython,
        )
        res = dlg.startProcess(PythonUtilities.getPythonExecutable(), args)
        if res:
            dlg.exec()

    @pyqtSlot()
    def __showFlashID(self):
        """
        Private slot to show the ID of the ESP flash chip.
        """
        args = [
            "-u",
            "-m",
            "esptool",
            "--port",
            self.microPython.getCurrentPort(),
            "flash_id",
        ]
        dlg = EricProcessDialog(
            self.tr("'esptool flash_id' Output"),
            self.tr("Show Flash ID"),
            monospacedFont=Preferences.getEditorOtherFonts("MonospacedFont"),
            encoding=Preferences.getSystem("IOEncoding"),
            parent=self.microPython,
        )
        res = dlg.startProcess(PythonUtilities.getPythonExecutable(), args)
        if res:
            dlg.exec()

    @pyqtSlot()
    def __showMACAddress(self):
        """
        Private slot to show the MAC address of the ESP chip.
        """
        args = [
            "-u",
            "-m",
            "esptool",
            "--port",
            self.microPython.getCurrentPort(),
            "read_mac",
        ]
        dlg = EricProcessDialog(
            self.tr("'esptool read_mac' Output"),
            self.tr("Show MAC Address"),
            monospacedFont=Preferences.getEditorOtherFonts("MonospacedFont"),
            encoding=Preferences.getSystem("IOEncoding"),
            parent=self.microPython,
        )
        res = dlg.startProcess(PythonUtilities.getPythonExecutable(), args)
        if res:
            dlg.exec()

    @pyqtSlot()
    def __showSecurityInfo(self):
        """
        Private slot to show some security related information of the ESP chip.
        """
        args = [
            "-u",
            "-m",
            "esptool",
            "--port",
            self.microPython.getCurrentPort(),
            "get_security_info",
        ]
        dlg = EricProcessDialog(
            self.tr("'esptool get_security_info' Output"),
            self.tr("Show Security Information"),
            monospacedFont=Preferences.getEditorOtherFonts("MonospacedFont"),
            encoding=Preferences.getSystem("IOEncoding"),
            parent=self.microPython,
        )
        res = dlg.startProcess(PythonUtilities.getPythonExecutable(), args)
        if res:
            dlg.exec()

    @pyqtSlot()
    def __resetDevice(self):
        """
        Private slot to reset the connected device.
        """
        if self.microPython.isConnected() and not self.hasCircuitPython():
            self.executeCommands(
                "import machine\nmachine.reset()\n", mode=self._submitMode
            )
        else:
            # perform a reset via esptool using flash_id command ignoring
            # the output
            args = [
                "-u",
                "-m",
                "esptool",
                "--port",
                self.microPython.getCurrentPort(),
                "flash_id",
            ]
            proc = QProcess()
            proc.start(PythonUtilities.getPythonExecutable(), args)
            procStarted = proc.waitForStarted(10000)
            if procStarted:
                proc.waitForFinished(10000)

    @pyqtSlot()
    def __installEspTool(self):
        """
        Private slot to install the esptool package via pip.
        """
        pip = ericApp().getObject("Pip")
        pip.installPackages(
            ["esptool"], interpreter=PythonUtilities.getPythonExecutable()
        )

    def getDocumentationUrl(self):
        """
        Public method to get the device documentation URL.

        @return documentation URL of the device
        @rtype str
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.getDocumentationUrl()

        return Preferences.getMicroPython("MicroPythonDocuUrl")

    def getFirmwareUrl(self):
        """
        Public method to get the device firmware download URL.

        @return firmware download URL of the device
        @rtype str
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.getFirmwareUrl()

        return Preferences.getMicroPython("MicroPythonFirmwareUrl")

    ##################################################################
    ## time related methods below
    ##################################################################

    def _getSetTimeCode(self):
        """
        Protected method to get the device code to set the time.

        Note: This method must be implemented in the various device specific
        subclasses.

        @return code to be executed on the connected device to set the time
        @rtype str
        """
        # rtc_time[0] - year    4 digit
        # rtc_time[1] - month   1..12
        # rtc_time[2] - day     1..31
        # rtc_time[3] - weekday 1..7 1=Monday
        # rtc_time[4] - hour    0..23
        # rtc_time[5] - minute  0..59
        # rtc_time[6] - second  0..59
        # rtc_time[7] - yearday 1..366
        # rtc_time[8] - isdst   0, 1, or -1

        # The machine.RTC.init() (ESP32) and machine.rtc.datetime() (ESP8266) functions
        # take the arguments in the order:
        # (year, month, day, weekday, hour, minute, second, subseconds)
        # __IGNORE_WARNING_M891__
        # https://docs.micropython.org/en/latest/library/machine.RTC.html#machine-rtc
        #
        # LoBo variant of MPy deviates.
        if self.hasCircuitPython():
            return super()._getSetTimeCode()

        return """
def set_time(rtc_time):
    import machine
    rtc = machine.RTC()
    try:
        rtc.datetime(rtc_time[:7] + (0,))
    except Exception:
        import os
        if 'LoBo' in os.uname()[0]:
            clock_time = rtc_time[:3] + rtc_time[4:7] + (rtc_time[3], rtc_time[7])
        else:
            clock_time = rtc_time[:7] + (0,)
        rtc.init(clock_time)
"""

    ##################################################################
    ## Methods below implement WiFi related methods
    ##################################################################

    def addDeviceWifiEntries(self, menu):
        """
        Public method to add device specific entries to the given menu.

        @param menu reference to the context menu
        @type QMenu
        """
        if not self.hasCircuitPython():
            menu.addSeparator()
            menu.addAction(self.tr("Set Country"), self.__setCountry)
            menu.addAction(self.tr("Reset Country"), self.__resetCountry)

    def hasWifi(self):
        """
        Public method to check the availability of WiFi.

        @return tuple containing a flag indicating the availability of WiFi
            and the WiFi type (esp32)
        @rtype tuple of (bool, str)
        """
        if self.hasCircuitPython():
            self.__createCpyDevice()
            return self.__cpyDevice.hasWifi()

        return True, "esp32"

    def hasWifiCountry(self):
        """
        Public method to check, if the device has support to set the WiFi country.

        @return flag indicating the support of WiFi country
        @rtype bool
        """
        return True

    def getWifiData(self):
        """
        Public method to get data related to the current WiFi status.

        @return tuple of three dictionaries containing the WiFi status data
            for the WiFi client, access point and overall data
        @rtype tuple of (dict, dict, dict)
        @exception OSError raised to indicate an issue with the device
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.getWifiData()

        command = """
def wifi_status():
    import ubinascii
    import ujson
    import network

    wifi = network.WLAN(network.STA_IF)
    station = {
        'active': wifi.active(),
        'connected': wifi.isconnected(),
        'status': wifi.status(),
        'ifconfig': wifi.ifconfig(),
        'mac': ubinascii.hexlify(wifi.config('mac'), ':').decode(),
    }
    if wifi.active():
        try:
            station['txpower'] = wifi.config('txpower')
        except ValueError:
            pass
    print(ujson.dumps(station))

    wifi = network.WLAN(network.AP_IF)
    ap = {
        'active': wifi.active(),
        'connected': wifi.isconnected(),
        'status': wifi.status(),
        'ifconfig': wifi.ifconfig(),
        'mac': ubinascii.hexlify(wifi.config('mac'), ':').decode(),
        'channel': wifi.config('channel'),
        'essid': wifi.config('essid'),
    }
    if wifi.active():
        try:
            ap['txpower'] = wifi.config('txpower')
        except ValueError:
            pass
    print(ujson.dumps(ap))

    overall = {
        'active': station['active'] or ap['active']
    }
    try:
        overall['hostname'] = network.hostname()
    except AttributeError:
        pass
    try:
        overall['country'] = network.country()
    except AttributeError:
        pass
    print(ujson.dumps(overall))

wifi_status()
del wifi_status
"""

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))

        stationStr, apStr, overallStr = out.decode("utf-8").splitlines()
        station = json.loads(stationStr)
        ap = json.loads(apStr)
        overall = json.loads(overallStr)
        try:
            station["status"] = self.__statusTranslations[station["status"]]
        except KeyError:
            station["status"] = str(station["status"])
        try:
            ap["status"] = self.__statusTranslations[ap["status"]]
        except KeyError:
            ap["status"] = str(ap["status"])
        return station, ap, overall

    def connectWifi(self, ssid, password, hostname):
        """
        Public method to connect a device to a WiFi network.

        @param ssid name (SSID) of the WiFi network
        @type str
        @param password password needed to connect
        @type str
        @param hostname host name of the device
        @type str
        @return tuple containing the connection status and an error string
        @rtype tuple of (bool, str)
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.connectWifi(ssid, password, hostname)

        command = """
def connect_wifi(ssid, password, hostname):
    import network
    import ujson
    from time import sleep

    if hostname:
        try:
            network.hostname(hostname)
        except AttributeError:
            pass

    wifi = network.WLAN(network.STA_IF)
    wifi.active(False)
    wifi.active(True)
    wifi.connect(ssid, password)
    max_wait = 140
    while max_wait and wifi.status() == network.STAT_CONNECTING:
        max_wait -= 1
        sleep(0.1)
    status = wifi.status()
    print(ujson.dumps({{'connected': wifi.isconnected(), 'status': status}}))

connect_wifi({0}, {1}, {2})
del connect_wifi
""".format(
            repr(ssid),
            repr(password if password else ""),
            repr(hostname),
        )

        with EricOverrideCursor():
            out, err = self.executeCommands(
                command, mode=self._submitMode, timeout=15000
            )
        if err:
            return False, err

        while not out.startswith(b"{"):
            # discard output until next newline
            _, out = out.split(b"\r\n", 1)
        result = json.loads(out.decode("utf-8").strip())
        if result["connected"]:
            error = ""
        else:
            try:
                error = self.__statusTranslations[result["status"]]
            except KeyError:
                error = str(result["status"])

        return result["connected"], error

    def disconnectWifi(self):
        """
        Public method to disconnect a device from the WiFi network.

        @return tuple containing a flag indicating success and an error string
        @rtype tuple of (bool, str)
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.disconnectWifi()

        command = """
def disconnect_wifi():
    import network
    from time import sleep

    wifi = network.WLAN(network.STA_IF)
    wifi.disconnect()
    wifi.active(False)
    sleep(0.1)
    print(not wifi.isconnected())

disconnect_wifi()
del disconnect_wifi
"""

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            return False, err

        return out.decode("utf-8").strip() == "True", ""

    def isWifiClientConnected(self):
        """
        Public method to check the WiFi connection status as client.

        @return flag indicating the WiFi connection status
        @rtype bool
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.isWifiClientConnected()

        command = """
def wifi_connected():
    import network

    wifi = network.WLAN(network.STA_IF)
    print(wifi.isconnected())

wifi_connected()
del wifi_connected
"""

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            return False

        return out.strip() == b"True"

    def isWifiApConnected(self):
        """
        Public method to check the WiFi connection status as access point.

        @return flag indicating the WiFi connection status
        @rtype bool
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.isWifiApConnected()

        command = """
def wifi_connected():
    import network

    wifi = network.WLAN(network.AP_IF)
    print(wifi.isconnected())

wifi_connected()
del wifi_connected
"""

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            return False

        return out.strip() == b"True"

    def writeCredentials(self, ssid, password, hostname, country):
        """
        Public method to write the given credentials to the connected device and modify
        the start script to connect automatically.

        @param ssid SSID of the network to connect to
        @type str
        @param password password needed to authenticate
        @type str
        @param hostname host name of the device
        @type str
        @param country WiFi country code
        @type str
        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.writeCredentials(ssid, password, hostname)

        nvsCommand = """
def save_wifi_creds(ssid, password, hostname, country):
    import esp32

    nvs = esp32.NVS('wifi_creds')
    nvs.set_blob('ssid', ssid)
    nvs.set_blob('password', password)
    nvs.set_blob('hostname', hostname)
    nvs.set_blob('country', country)
    nvs.commit()

save_wifi_creds({0}, {1}, {2}, {3})
del save_wifi_creds
""".format(
            repr(ssid),
            repr(password) if password else "''",
            repr(hostname) if hostname else "''",
            repr(country.upper()) if country else "''",
        )
        bootCommand = """
def modify_boot():
    add = True
    try:
        with open('/boot.py', 'r') as f:
            for ln in f.readlines():
                if 'wifi_connect' in ln:
                    add = False
                    break
    except:
        pass
    if add:
        with open('/boot.py', 'a') as f:
            f.write('\\nimport wifi_connect\\n')
    print(True)

modify_boot()
del modify_boot
"""

        out, err = self.executeCommands(nvsCommand, mode=self._submitMode)
        if err:
            return False, self.tr("Error saving credentials: {0}").format(err)

        try:
            # copy auto-connect file
            self.put(
                os.path.join(
                    os.path.dirname(__file__), "MCUScripts", "esp32WiFiConnect.py"
                ),
                "/wifi_connect.py",
            )
        except OSError as err:
            return False, self.tr("Error saving auto-connect script: {0}").format(err)

        out, err = self.executeCommands(bootCommand, mode=self._submitMode)
        if err:
            return False, self.tr("Error modifying 'boot.py': {0}").format(err)

        return True, ""

    def removeCredentials(self):
        """
        Public method to remove the saved credentials from the connected device.

        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.removeCredentials()

        nvsCommand = """
def delete_wifi_creds():
    import esp32

    nvs = esp32.NVS('wifi_creds')
    try:
        nvs.erase_key('ssid')
        nvs.erase_key('password')
        nvs.commit()
    except OSError:
        pass

delete_wifi_creds()
del delete_wifi_creds
"""

        out, err = self.executeCommands(nvsCommand, mode=self._submitMode)
        if err:
            return False, self.tr("Error deleting credentials: {0}").format(err)

        return True, ""

    def checkInternet(self):
        """
        Public method to check, if the internet can be reached.

        @return tuple containing a flag indicating reachability and an error string
        @rtype tuple of (bool, str)
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.checkInternet()

        command = """
def check_internet():
    import network
    import socket

    wifi = network.WLAN(network.STA_IF)
    if wifi.isconnected():
        s = socket.socket()
        try:
            s.connect(socket.getaddrinfo('quad9.net', 443)[0][-1])
            s.close()
            print(True)
        except:
            print(False)
    else:
        print(False)

check_internet()
del check_internet
"""

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            return False, err

        return out.decode("utf-8").strip() == "True", ""

    def scanNetworks(self):
        """
        Public method to scan for available WiFi networks.

        @return tuple containing the list of available networks as a tuple of 'Name',
            'MAC-Address', 'channel', 'RSSI' and 'security' and an error string
        @rtype tuple of (list of tuple of (str, str, int, int, str), str)
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.scanNetworks()

        command = """
def scan_networks():
    import network

    wifi = network.WLAN(network.STA_IF)
    active = wifi.active()
    if not active:
        wifi.active(True)
    network_list = wifi.scan()
    if not active:
        wifi.active(False)
    print(network_list)

scan_networks()
del scan_networks
"""

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=15000)
        if err:
            return [], err

        networksList = ast.literal_eval(out.decode("utf-8"))
        networks = []
        for network in networksList:
            if network[0]:
                ssid = network[0].decode("utf-8")
                mac = binascii.hexlify(network[1], ":").decode("utf-8")
                channel = network[2]
                rssi = network[3]
                try:
                    security = self.__securityTranslations[network[4]]
                except KeyError:
                    security = self.tr("unknown ({0})").format(network[4])
                networks.append((ssid, mac, channel, rssi, security))

        return networks, ""

    def deactivateInterface(self, interface):
        """
        Public method to deactivate a given WiFi interface of the connected device.

        @param interface designation of the interface to be deactivated (one of 'AP'
            or 'STA')
        @type str
        @return tuple containg a flag indicating success and an error message
        @rtype tuple of (bool, str)
        @exception ValueError raised to indicate a wrong value for the interface type
        """
        if interface not in ("STA", "AP"):
            raise ValueError(
                "interface must be 'AP' or 'STA', got '{0}'".format(interface)
            )

        if self.hasCircuitPython():
            return self.__cpyDevice.deactivateInterface(interface)

        command = """
def deactivate():
    import network
    from time import sleep

    wifi = network.WLAN(network.{0}_IF)
    wifi.active(False)
    sleep(0.1)
    print(not wifi.active())

deactivate()
del deactivate
""".format(
            interface
        )

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            return False, err
        else:
            return out.decode("utf-8").strip() == "True", ""

    def startAccessPoint(
        self,
        ssid,
        security=None,
        password=None,
        hostname=None,
        ifconfig=None,
    ):
        """
        Public method to start the access point interface.

        @param ssid SSID of the access point
        @type str
        @param security security method (defaults to None)
        @type int (optional)
        @param password password (defaults to None)
        @type str (optional)
        @param hostname host name of the device (defaults to None)
        @type str (optional)
        @param ifconfig IPv4 configuration for the access point if not default
            (IPv4 address, netmask, gateway address, DNS server address)
        @type tuple of (str, str, str, str)
        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.startAccessPoint(
                ssid,
                security=security,
                password=password,
                hostname=hostname,
                ifconfig=ifconfig,
            )

        if security is None or password is None:
            security = 0
            password = ""  # secok
        if security > 4:
            security = 4  # security >4 cause an error thrown by the ESP32

        command = """
def start_ap(ssid, authmode, password, hostname, ifconfig):
    import network

    if hostname:
        try:
            network.hostname(hostname)
        except AttributeError:
            pass

    ap = network.WLAN(network.AP_IF)
    ap.active(False)
    if ifconfig:
        ap.ifconfig(ifconfig)
    ap.active(True)
    try:
        ap.config(ssid=ssid, authmode=authmode, password=password)
    except:
        ap.config(essid=ssid, authmode=authmode, password=password)

start_ap({0}, {1}, {2}, {3}, {4})
del start_ap
""".format(
            repr(ssid), security, repr(password), repr(hostname), ifconfig
        )

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=15000)
        if err:
            return False, err
        else:
            return True, ""

    def stopAccessPoint(self):
        """
        Public method to stop the access point interface.

        @return tuple containg a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.stopAccessPoint()

        return self.deactivateInterface("AP")

    def getConnectedClients(self):
        """
        Public method to get a list of connected clients.

        @return a tuple containing a list of tuples containing the client MAC-Address
            and the RSSI (if supported and available) and an error message
        @rtype tuple of ([(bytes, int)], str)
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.getConnectedClients()

        command = """
def get_stations():
    import network

    ap = network.WLAN(network.AP_IF)
    stations = ap.status('stations')
    print(stations)

get_stations()
del get_stations
"""

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=10000)
        if err:
            return [], err

        clientsList = ast.literal_eval(out.decode("utf-8"))
        return clientsList, ""

    def enableWebrepl(self, password):
        """
        Public method to write the given WebREPL password to the connected device and
        modify the start script to start the WebREPL server.

        @param password password needed to authenticate
        @type str
        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        command = """
def modify_boot():
    import os

    try:
        with open('/boot.py', 'r') as old_f, open('/boot.py.tmp', 'w') as new_f:
            found = False
            for l in old_f.read().splitlines():
                if 'webrepl' in l:
                    found = True
                    if l.startswith('#'):
                        l = l[1:]
                new_f.write(l + '\\n')
            if not found:
                new_f.write('\\nimport webrepl\\nwebrepl.start()\\n')

        os.remove('/boot.py')
        os.rename('/boot.py.tmp', '/boot.py')
    except:
        pass

    print(True)

modify_boot()
del modify_boot
"""

        try:
            # write config file
            config = "PASS = {0}\n".format(repr(password))
            self.putData("/webrepl_cfg.py", config.encode("utf-8"))
        except OSError as err:
            return False, str(err)

        # modify boot.py
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            return False, err

        return out.decode("utf-8").strip() == "True", ""

    def disableWebrepl(self):
        """
        Public method to write the given WebREPL password to the connected device and
        modify the start script to start the WebREPL server.

        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        command = """
def modify_boot():
    import os

    try:
        with open('/boot.py', 'r') as old_f, open('/boot.py.tmp', 'w') as new_f:
            for l in old_f.read().splitlines():
                if 'webrepl' in l:
                    if not l.startswith('#'):
                        l = '#' + l
                new_f.write(l + '\\n')

        os.remove('/boot.py')
        os.rename('/boot.py.tmp', '/boot.py')
    except:
        pass

    print(True)

modify_boot()
del modify_boot
"""

        # modify boot.py
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            return False, err

        return out.decode("utf-8").strip() == "True", ""

    @pyqtSlot()
    def __setCountry(self):
        """
        Private slot to configure the country of the connected ESP32 device.

        The country is the two-letter ISO 3166-1 Alpha-2 country code.
        """
        from ..WifiDialogs.WifiCountryDialog import WifiCountryDialog

        dlg = WifiCountryDialog(parent=self.microPython)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            country, remember = dlg.getCountry()
            if remember:
                Preferences.setMicroPython("WifiCountry", country)

            command = """
try:
    import network
    network.country({0})
except AttributeError:
    pass
""".format(
                repr(country)
            )

            out, err = self.executeCommands(command, mode=self._submitMode)
            if err:
                self.microPython.showError("country()", err)

    @pyqtSlot()
    def __resetCountry(self):
        """
        Private slot to reset the country of the connected ESP32 device.

        The country is the two-letter ISO 3166-1 Alpha-2 country code. This method
        resets it to the default code 'XX' representing the "worldwide" region.
        """
        command = """
try:
    import network
    network.country('XX')
except AttributeError:
    pass
"""

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            self.microPython.showError("country()", err)

    ##################################################################
    ## Methods below implement Bluetooth related methods
    ##################################################################

    def hasBluetooth(self):
        """
        Public method to check the availability of Bluetooth.

        @return flag indicating the availability of Bluetooth
        @rtype bool
        @exception OSError raised to indicate an issue with the device
        """
        if self.hasCircuitPython():
            self.__createCpyDevice()
            return self.__cpyDevice.hasBluetooth()

        command = """
def has_bt():
    try:
        import bluetooth
        if hasattr(bluetooth, 'BLE'):
            return True
    except ImportError:
        pass

    return False

print(has_bt())
del has_bt
"""
        out, err = self.executeCommands(command, mode=self._submitMode, timeout=10000)
        if err:
            raise OSError(self._shortError(err))
        return out.strip() == b"True"

    def getBluetoothStatus(self):
        """
        Public method to get Bluetooth status data of the connected board.

        @return list of tuples containing the translated status data label and
            the associated value
        @rtype list of tuples of (str, str)
        @exception OSError raised to indicate an issue with the device
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.getBluetoothStatus()

        command = """
def ble_status():
    import bluetooth
    import ubinascii
    import ujson

    ble = bluetooth.BLE()

    ble_active = ble.active()
    if not ble_active:
        ble.active(True)

    res = {
        'active': ble_active,
        'mac': ubinascii.hexlify(ble.config('mac')[1], ':').decode(),
        'addr_type': ble.config('mac')[0],
        'name': ble.config('gap_name'),
        'mtu': ble.config('mtu'),
    }

    if not ble_active:
        ble.active(False)

    print(ujson.dumps(res))

ble_status()
del ble_status
"""
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))

        status = []
        bleStatus = json.loads(out.decode("utf-8"))
        status.append((self.tr("Active"), self.bool2str(bleStatus["active"])))
        status.append((self.tr("Name"), bleStatus["name"]))
        status.append((self.tr("MAC-Address"), bleStatus["mac"]))
        status.append(
            (
                self.tr("Address Type"),
                self.tr("Public") if bleStatus == 0 else self.tr("Random"),
            )
        )
        status.append((self.tr("MTU"), self.tr("{0} Bytes").format(bleStatus["mtu"])))

        return status

    def activateBluetoothInterface(self):
        """
        Public method to activate the Bluetooth interface.

        @return flag indicating the new state of the Bluetooth interface
        @rtype bool
        @exception OSError raised to indicate an issue with the device
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.activateBluetoothInterface()

        command = """
def activate_ble():
    import bluetooth

    ble = bluetooth.BLE()
    if not ble.active():
        ble.active(True)
    print(ble.active())

activate_ble()
del activate_ble
"""
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))

        return out.strip() == b"True"

    def deactivateBluetoothInterface(self):
        """
        Public method to deactivate the Bluetooth interface.

        @return flag indicating the new state of the Bluetooth interface
        @rtype bool
        @exception OSError raised to indicate an issue with the device
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.deactivateBluetoothInterface()

        command = """
def deactivate_ble():
    import bluetooth

    ble = bluetooth.BLE()
    if ble.active():
        ble.active(False)
    print(ble.active())

deactivate_ble()
del deactivate_ble
"""
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))

        return out.strip() == b"True"

    def getDeviceScan(self, timeout=10):
        """
        Public method to perform a Bluetooth device scan.

        @param timeout duration of the device scan in seconds (defaults
            to 10)
        @type int (optional)
        @return tuple containing a dictionary with the scan results and
            an error string
        @rtype tuple of (dict, str)
        """
        from ..BluetoothDialogs.BluetoothAdvertisement import BluetoothAdvertisement

        if self.hasCircuitPython():
            return self.__cpyDevice.getDeviceScan(timeout)

        command = """
_scan_done = False

def ble_scan():
    import bluetooth
    import time
    import ubinascii

    IRQ_SCAN_RESULT = 5
    IRQ_SCAN_DONE = 6

    def _bleIrq(event, data):
        global _scan_done
        if event == IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            if addr:
                print({{
                    'address': ubinascii.hexlify(addr,':').decode('utf-8'),
                    'rssi': rssi,
                    'adv_type': adv_type,
                    'advertisement': bytes(adv_data),
                }})
        elif event == IRQ_SCAN_DONE:
            _scan_done = True

    ble = bluetooth.BLE()

    ble_active = ble.active()
    if not ble_active:
        ble.active(True)

    ble.irq(_bleIrq)
    ble.gap_scan({0} * 1000, 1000000, 50000, True)
    while not _scan_done:
        time.sleep(0.2)

    if not ble_active:
        ble.active(False)

ble_scan()
del ble_scan, _scan_done
""".format(
            timeout
        )
        out, err = self.executeCommands(
            command, mode=self._submitMode, timeout=(timeout + 5) * 1000
        )
        if err:
            return {}, err

        scanResults = {}
        for line in out.decode("utf-8").splitlines():
            res = ast.literal_eval(line)
            address = res["address"]
            if address not in scanResults:
                scanResults[address] = BluetoothAdvertisement(address)
            scanResults[address].update(
                res["adv_type"], res["rssi"], res["advertisement"]
            )

        return scanResults, ""

    ##################################################################
    ## Methods below implement NTP related methods
    ##################################################################

    def hasNetworkTime(self):
        """
        Public method to check the availability of network time functions.

        @return flag indicating the availability of network time functions
        @rtype bool
        @exception OSError raised to indicate an issue with the device
        """
        if self.hasCircuitPython():
            self.__createCpyDevice()
            return self.__cpyDevice.hasNetworkTime()

        command = """
def has_ntp():
    try:
        import ntptime
        return True
    except ImportError:
        return False

print(has_ntp())
del has_ntp
"""
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))
        return out.strip() == b"True"

    def setNetworkTime(self, server="0.pool.ntp.org", tzOffset=0, timeout=10):
        """
        Public method to set the time to the network time retrieved from an
        NTP server.

        @param server name of the NTP server to get the network time from
            (defaults to "0.pool.ntp.org")
        @type str (optional)
        @param tzOffset offset with respect to UTC (defaults to 0)
        @type int (optional)
        @param timeout maximum time to wait for a server response in seconds
            (defaults to 10)
        @type int
        @return tuple containing a flag indicating success and an error string
        @rtype tuple of (bool, str)
        """
        if self.hasCircuitPython():
            return self.__cpyDevice.setNetworkTime(
                server=server, tzOffset=tzOffset, timeout=timeout
            )

        command = """
def set_ntp_time(server, tz_offset, timeout):
    import network
    import ntptime
    import machine

    if not network.WLAN(network.STA_IF).isconnected():
        return False

    ntptime.host = server
    ntptime.timeout = timeout
    ntptime.settime()

    rtc = machine.RTC()
    t = list(rtc.datetime())
    t[4] += tz_offset
    rtc.datetime(t)

    return True

try:
    print({{
        'result': set_ntp_time({0}, {1}, {2}),
        'error': '',
    }})
except Exception as err:
    print({{
        'result': False,
        'error': str(err),
    }})
del set_ntp_time
""".format(
            repr(server), tzOffset, timeout
        )
        out, err = self.executeCommands(
            command, mode=self._submitMode, timeout=(timeout + 2) * 1000
        )
        if err:
            return False, err
        else:
            res = ast.literal_eval(out.decode("utf-8"))
            return res["result"], res["error"]


def createDevice(microPythonWidget, deviceType, _vid, _pid, _boardName, _serialNumber):
    """
    Function to instantiate a MicroPython device object.

    @param microPythonWidget reference to the main MicroPython widget
    @type MicroPythonWidget
    @param deviceType device type assigned to this device interface
    @type str
    @param _vid vendor ID (unused)
    @type int
    @param _pid product ID (unused)
    @type int
    @param _boardName name of the board (unused)
    @type str
    @param _serialNumber serial number of the board (unused)
    @type str
    @return reference to the instantiated device object
    @rtype EspDevice
    """
    return EspDevice(microPythonWidget, deviceType)


################################################################################
## Functions below implement flashing related functionality needed elsewhere  ##
## as well.                                                                   ##
################################################################################


@pyqtSlot()
def eraseFlash(port, parent=None):
    """
    Slot to erase the device flash memory.

    @param port name of the serial port device to be used
    @type str
    @param parent reference to the parent widget (defaults to None)
    @type QWidget
    """
    ok = EricMessageBox.yesNo(
        parent,
        QCoreApplication.translate("EspDevice", "Erase Flash"),
        QCoreApplication.translate(
            "EspDevice", """Shall the flash of the selected device really be erased?"""
        ),
    )
    if ok:
        flashArgs = [
            "-u",
            "-m",
            "esptool",
            "--port",
            port,
            "erase_flash",
        ]
        dlg = EricProcessDialog(
            QCoreApplication.translate("EspDevice", "'esptool erase_flash' Output"),
            QCoreApplication.translate("EspDevice", "Erase Flash"),
            showProgress=True,
            monospacedFont=Preferences.getEditorOtherFonts("MonospacedFont"),
            encoding=Preferences.getSystem("IOEncoding"),
            parent=parent,
        )
        res = dlg.startProcess(PythonUtilities.getPythonExecutable(), flashArgs)
        if res:
            dlg.exec()


@pyqtSlot()
def flashPythonFirmware(port, parent=None):
    """
    Slot to flash a MicroPython firmware to the device.

    @param port name of the serial port device to be used
    @type str
    @param parent reference to the parent widget (defaults to None)
    @type QWidget
    """
    from .EspDialogs.EspFirmwareSelectionDialog import EspFirmwareSelectionDialog

    dlg = EspFirmwareSelectionDialog(parent=parent)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        chip, firmware, baudRate, flashMode, flashAddress = dlg.getData()
        flashArgs = [
            "-u",
            "-m",
            "esptool",
            "--chip",
            chip,
            "--port",
            port,
        ]
        if baudRate != "115200":
            flashArgs += ["--baud", baudRate]
        flashArgs.append("write_flash")
        if flashMode:
            flashArgs += ["--flash_mode", flashMode]
        if chip == "esp8266":
            # ESP 8266 seems to need flash size detection
            flashArgs += ["--flash_size", "detect"]
        flashArgs += [
            flashAddress,
            firmware,
        ]
        dlg = EricProcessDialog(
            QCoreApplication.translate("EspDevice", "'esptool write_flash' Output"),
            QCoreApplication.translate("EspDevice", "Flash µPy/CPy Firmware"),
            showProgress=True,
            monospacedFont=Preferences.getEditorOtherFonts("MonospacedFont"),
            encoding=Preferences.getSystem("IOEncoding"),
            parent=parent,
        )
        res = dlg.startProcess(PythonUtilities.getPythonExecutable(), flashArgs)
        if res:
            dlg.exec()


@pyqtSlot()
def flashAddonFirmware(port, parent=None):
    """
    Slot to flash some additional firmware images.

    @param port name of the serial port device to be used
    @type str
    @param parent reference to the parent widget (defaults to None)
    @type QWidget
    """
    from .EspDialogs.EspFirmwareSelectionDialog import EspFirmwareSelectionDialog

    dlg = EspFirmwareSelectionDialog(addon=True, parent=parent)
    if dlg.exec() == QDialog.DialogCode.Accepted:
        chip, firmware, baudRate, flashMode, flashAddress = dlg.getData()
        flashArgs = [
            "-u",
            "-m",
            "esptool",
            "--chip",
            chip,
            "--port",
            port,
        ]
        if baudRate != "115200":
            flashArgs += ["--baud", baudRate]
        flashArgs.append("write_flash")
        if flashMode:
            flashArgs += ["--flash_mode", flashMode]
        flashArgs += [
            flashAddress.lower(),
            firmware,
        ]
        dlg = EricProcessDialog(
            QCoreApplication.translate("EspDevice", "'esptool write_flash' Output"),
            QCoreApplication.translate("EspDevice", "Flash Additional Firmware"),
            showProgress=True,
            monospacedFont=Preferences.getEditorOtherFonts("MonospacedFont"),
            encoding=Preferences.getSystem("IOEncoding"),
            parent=parent,
        )
        res = dlg.startProcess(PythonUtilities.getPythonExecutable(), flashArgs)
        if res:
            dlg.exec()
