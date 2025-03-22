# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the device interface class for CircuitPython boards.
"""

import ast
import binascii
import json
import os
import shutil

from PyQt6.QtCore import QUrl, pyqtSlot
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import QInputDialog, QMenu

from eric7 import EricUtilities, Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor, EricOverridenCursor
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities

from ..EthernetDialogs import WiznetUtilities
from ..MicroPythonWidget import HAS_QTCHART
from . import FirmwareGithubUrls
from .CircuitPythonUpdater.CircuitPythonUpdaterInterface import (
    CircuitPythonUpdaterInterface,
    isCircupAvailable,
)
from .DeviceBase import BaseDevice


class CircuitPythonDevice(BaseDevice):
    """
    Class implementing the device for CircuitPython boards.
    """

    DeviceVolumeName = "CIRCUITPY"

    def __init__(
        self,
        microPythonWidget,
        deviceType,
        boardName,
        vid=0,
        pid=0,
        hasWorkspace=True,
        parent=None,
    ):
        """
        Constructor

        @param microPythonWidget reference to the main MicroPython widget
        @type MicroPythonWidget
        @param deviceType device type assigned to this device interface
        @type str
        @param boardName name of the board
        @type str
        @param vid vendor ID (defaults to 0)
        @type int (optional)
        @param pid product ID (defaults to 0)
        @type int (optional)
        @param hasWorkspace flag indicating that the devices supports access via
            a mounted volume (defaults to True)
        @type bool (optional)
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(microPythonWidget, deviceType, parent)

        self._submitMode = "paste"  # use 'paste' mode to avoid loosing state

        self.__boardName = boardName
        self.__vidpid = (vid, pid)

        self.__workspaceSelected = False
        self.__workspace = self.__findWorkspace() if hasWorkspace else None

        self.__updater = CircuitPythonUpdaterInterface(self)

        self.__createCPyMenu()

        self.__wiznetVidPid = (
            (0x2E8A, 0x1027),  # WIZnet W5100S-EVB-Pico
            (0x2E8A, 0x1029),  # WIZnet W5500-EVB-Pico
        )

        self.__securityTranslations = {
            "OPEN": self.tr("open", "open WiFi network"),
            "WEP": "WEP",
            "WPA_PSK": "WPA",
            "WPA2_PSK": "WPA2",
            "WPA_WPA2_PSK": "WPA/WPA2",
            "WPA2_ENTERPRISE": "WPA2 (CCMP)",
            "WPA3_PSK": "WPA3",
            "WPA2_WPA3_PSK": "WPA2/WPA3",
        }
        self.__securityCode2AuthModeString = {
            0: "[wifi.AuthMode.OPEN]",
            1: "[wifi.AuthMode.WEP]",
            2: "[wifi.AuthMode.WPA, wifi.AuthMode.PSK]",
            3: "[wifi.AuthMode.WPA2, wifi.AuthMode.PSK]",
            4: "[wifi.AuthMode.WPA, wifi.AuthMode.WPA2, wifi.AuthMode.PSK]",
            5: "[wifi.AuthMode.WPA2, wifi.AuthMode.ENTERPRISE]",
            6: "[wifi.AuthMode.WPA3, wifi.AuthMode.PSK]",
            7: "[wifi.AuthMode.WPA2, wifi.AuthMode.WPA3, wifi.AuthMode.PSK]",
        }
        self.__bleAddressType = {
            0: self.tr("Public"),
            1: self.tr("Random Static"),
            2: self.tr("Random Private Resolvable"),
            3: self.tr("Random Private Non-Resolvable"),
        }

    def setConnected(self, connected):
        """
        Public method to set the connection state.

        @param connected connection state
        @type bool
        """
        if not connected and self.__libraryMenu.isTearOffMenuVisible():
            self.__libraryMenu.hideTearOffMenu()

        if self.__flashMenu.isTearOffMenuVisible():
            self.__flashMenu.hideTearOffMenu()

        super().setConnected(connected)
        self._deviceData["local_mip"] = False

        if (
            connected
            and not self._deviceData["ethernet"]
            and self.__vidpid in self.__wiznetVidPid
        ):
            with EricOverridenCursor():
                EricMessageBox.warning(
                    None,
                    self.tr("WIZnet 5x00 Ethernet"),
                    self.tr(
                        "<p>Support for <b>WIZnet 5x00</b> Ethernet boards could not be"
                        " detected. Is the module <b>adafruit_wiznet5k</b> installed?"
                        "</p>"
                    ),
                )

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
        return False

    def deviceName(self):
        """
        Public method to get the name of the device.

        @return name of the device
        @rtype str
        """
        return self.tr("CircuitPython")

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

    def supportsLocalFileAccess(self):
        """
        Public method to indicate file access via a local directory.

        @return flag indicating file access via local directory
        @rtype bool
        """
        return self.__deviceVolumeMounted()

    def __deviceVolumeMounted(self):
        """
        Private method to check, if the device volume is mounted.

        @return flag indicated a mounted device
        @rtype bool
        """
        if self.__workspace and not os.path.exists(self.__workspace):
            self.__workspace = ""  # reset

        if (
            self.__workspace
            and self.DeviceVolumeName not in self.__workspace
            and not self.__workspaceSelected
        ):
            self.__workspace = ""  # reset

        return self.__workspaceSelected or self.DeviceVolumeName in self.getWorkspace(
            silent=True
        )

    def __findDeviceDirectories(self, directories):
        """
        Private method to find the device directories associated with the
        current board name.

        @param directories list of directories to be checked
        @type list of str
        @return list of associated directories
        @rtype list of str
        """
        boardDirectories = []
        for directory in directories:
            bootFile = os.path.join(directory, "boot_out.txt")
            if os.path.exists(bootFile):
                with open(bootFile, "r") as f:
                    line = f.readline()
                if self.__boardName in line:
                    boardDirectories.append(directory)

        return boardDirectories

    def __findWorkspace(self, silent=False):
        """
        Private method to find the workspace directory.

        @param silent flag indicating silent operations (defaults to False)
        @type bool (optional)
        @return workspace directory used for saving files
        @rtype str
        """
        # Attempts to find the paths on the filesystem that represents the
        # plugged in CIRCUITPY boards.
        deviceDirectories = FileSystemUtilities.findVolume(
            self.DeviceVolumeName, findAll=True
        )

        if deviceDirectories:
            if len(deviceDirectories) == 1:
                return deviceDirectories[0]
            else:
                boardDirectories = self.__findDeviceDirectories(deviceDirectories)
                if len(boardDirectories) == 1:
                    return boardDirectories[0]
                elif len(boardDirectories) > 1:
                    return self.selectDeviceDirectory(boardDirectories)
                else:
                    return self.selectDeviceDirectory(deviceDirectories)
        else:
            # return the default workspace and give the user a warning (unless
            # silent mode is selected)
            if not silent:
                EricMessageBox.warning(
                    self.microPython,
                    self.tr("Workspace Directory"),
                    self.tr(
                        "Python files for CircuitPython can be edited in"
                        " place, if the device volume is locally"
                        " available. Such a volume was not found. In"
                        " place editing will not be available."
                    ),
                )

            return super().getWorkspace()

    def getWorkspace(self, silent=False):
        """
        Public method to get the workspace directory.

        @param silent flag indicating silent operations
        @type bool
        @return workspace directory used for saving files
        @rtype str
        """
        if self.__workspace:
            # return cached entry
            return self.__workspace
        else:
            self.__workspace = self.__findWorkspace(silent=silent)
            return self.__workspace

    def setWorkspace(self, workspacePath):
        """
        Public method to set the device workspace directory.

        @param workspacePath directory to be used for saving files
        @type str
        """
        self.__workspace = workspacePath
        self.__workspaceSelected = True

    def __createCPyMenu(self):
        """
        Private method to create the CircuitPython submenu.
        """
        self.__libraryMenu = QMenu(self.tr("Library Management"))
        self.__libraryMenu.aboutToShow.connect(self.__aboutToShowLibraryMenu)
        self.__libraryMenu.setTearOffEnabled(True)

        self.__flashMenu = self.__createFlashMenus()

        self.__cpyMenu = QMenu(self.tr("CircuitPython Functions"))
        self.__cpyMenu.addAction(
            self.tr("Show CircuitPython Versions"), self.showCircuitPythonVersions
        )
        self.__cpyMenu.addSeparator()
        self.__cpyMenu.addAction(
            self.tr("Select Device Volume"), self.__selectDeviceVolume
        )
        self.__cpyMenu.addSeparator()
        self.__bootloaderAct = self.__cpyMenu.addAction(
            self.tr("Activate Bootloader"), self.__activateBootloader
        )
        self.__uf2Act = self.__cpyMenu.addAction(
            self.tr("Activate UF2 Mode"), self.__activateUF2Boot
        )
        self.__flashCpyAct = self.__cpyMenu.addMenu(self.__flashMenu)
        self.__cpyMenu.addSeparator()
        self.__cpyMenu.addMenu(self.__libraryMenu)
        self.__cpyMenu.addSeparator()
        self.__resetAct = self.__cpyMenu.addAction(
            self.tr("Reset Device"), self.__resetDevice
        )

    def __createFlashMenus(self):
        """
        Private method to create the various menus to flash a CircuitPython firmware.

        @return reference to the created top level flash menu
        @rtype QMenu
        """
        menu = QMenu(self.tr("Flash CircuitPython Firmware"))
        menu.setTearOffEnabled(True)

        # UF2 devices
        menu.addAction(self.tr("UF2 Device"), self.__flashCircuitPython)
        menu.addSeparator()

        # ESP32 specific submenu
        self.__esp32FlashMenu = QMenu(self.tr("ESP32 Device"))
        self.__esp32FlashMenu.addAction(self.tr("Erase Flash"), self.__esp32EraseFlash)
        self.__esp32FlashMenu.addAction(
            self.tr("Flash MicroPython Firmware"), self.__esp32FlashPython
        )
        self.__esp32FlashMenu.addSeparator()
        self.__esp32FlashMenu.addAction(
            self.tr("Flash Additional Firmware"), self.__esp32FlashAddons
        )
        menu.addMenu(self.__esp32FlashMenu)

        # Teensy 4.0 and 4.1 specific submenu
        self.__teensyFlashMenu = QMenu(self.tr("Teensy Device"))
        self.__teensyFlashMenu.addAction(
            self.tr("CircuitPython Flash Instructions"),
            self.__showTeensyFlashInstructions,
        )
        act = self.__teensyFlashMenu.addAction(
            self.tr("Start 'Teensy Loader'"), self.__startTeensyLoader
        )
        act.setToolTip(
            self.tr("Start the 'Teensy Loader' application to flash the Teensy device.")
        )
        menu.addMenu(self.__teensyFlashMenu)

        return menu

    def addDeviceMenuEntries(self, menu):
        """
        Public method to add device specific entries to the given menu.

        @param menu reference to the context menu
        @type QMenu
        """
        connected = self.microPython.isConnected()
        linkConnected = self.microPython.isLinkConnected()

        self.__flashCpyAct.setEnabled(not linkConnected)
        self.__resetAct.setEnabled(connected)
        self.__bootloaderAct.setEnabled(connected)
        self.__uf2Act.setEnabled(connected)

        menu.addMenu(self.__cpyMenu)

    @pyqtSlot()
    def __aboutToShowLibraryMenu(self):
        """
        Private slot to populate the 'Library Management' menu.
        """
        self.__libraryMenu.clear()

        if isCircupAvailable():
            self.__updater.populateMenu(self.__libraryMenu)
        else:
            act = self.__libraryMenu.addAction(
                self.tr("Install Library Files"), self.__installLibraryFiles
            )
            act.setEnabled(self.__deviceVolumeMounted())
            act = self.__libraryMenu.addAction(
                self.tr("Install Library Package"),
                lambda: self.__installLibraryFiles(packageMode=True),
            )
            act.setEnabled(self.__deviceVolumeMounted())
            self.__libraryMenu.addSeparator()
            self.__libraryMenu.addAction(
                self.tr("Install 'circup' Package"),
                self.__updater.installCircup,
            )

    @pyqtSlot()
    def __resetDevice(self):
        """
        Private slot to reset the connected device.
        """
        if self.microPython.isConnected():
            self.executeCommands(
                "import microcontroller as mc\n"
                "mc.on_next_reset(mc.RunMode.NORMAL)"
                "mc.reset()\n",
                mode=self._submitMode,
            )

    def hasFlashMenuEntry(self):
        """
        Public method to check, if the device has its own flash menu entry.

        @return flag indicating a specific flash menu entry
        @rtype bool
        """
        return True

    @pyqtSlot()
    def __flashCircuitPython(self):
        """
        Private slot to flash a CircuitPython firmware to a device supporting UF2.
        """
        from ..UF2FlashDialog import UF2FlashDialog

        dlg = UF2FlashDialog(boardType="circuitpython", parent=self.microPython)
        dlg.exec()

    @pyqtSlot()
    def __activateBootloader(self):
        """
        Private slot to switch the board into 'bootloader' mode.
        """
        if self.microPython.isConnected():
            self.executeCommands(
                "import microcontroller as mc\n"
                "mc.on_next_reset(mc.RunMode.BOOTLOADER)\n"
                "mc.reset()\n",
                mode=self._submitMode,
            )

    @pyqtSlot()
    def __activateUF2Boot(self):
        """
        Private slot to switch the board into 'UF2 Boot' mode.
        """
        if self.microPython.isConnected():
            self.executeCommands(
                "import microcontroller as mc\n"
                "mc.on_next_reset(mc.RunMode.UF2)\n"
                "mc.reset()\n",
                mode=self._submitMode,
            )

    @pyqtSlot()
    def __showTeensyFlashInstructions(self):
        """
        Private slot to show a message box because Teensy does not support
        the UF2 bootloader yet.
        """
        from .TeensyDevices import showTeensyFlashInstructions

        showTeensyFlashInstructions()

    @pyqtSlot()
    def __startTeensyLoader(self):
        """
        Private slot to start the 'Teensy Loader' application.

        Note: The application must be accessible via the application search path.
        """
        from .TeensyDevices import startTeensyLoader

        startTeensyLoader()

    @pyqtSlot()
    def __esp32EraseFlash(self):
        """
        Private slot to erase the flash of an ESP32 device.
        """
        from .EspDevices import eraseFlash

        eraseFlash(self.microPython.getCurrentPort(), parent=self.microPython)

    @pyqtSlot()
    def __esp32FlashPython(self):
        """
        Private slot to flash a MicroPython or CircuitPython firmware to an ESP32
        device.
        """
        from .EspDevices import flashPythonFirmware

        flashPythonFirmware(self.microPython.getCurrentPort(), parent=self.microPython)

    @pyqtSlot()
    def __esp32FlashAddons(self):
        """
        Private slot to flash additional firmware to an ESP32 device.
        """
        from .EspDevices import flashAddonFirmware

        flashAddonFirmware(self.microPython.getCurrentPort(), parent=self.microPython)

    @pyqtSlot()
    def showCircuitPythonVersions(self):
        """
        Public slot to show the CircuitPython version of a connected device and
        the latest available one (from Github).
        """
        ui = ericApp().getObject("UserInterface")
        request = QNetworkRequest(QUrl(FirmwareGithubUrls["circuitpython"]))
        reply = ui.networkAccessManager().head(request)
        reply.finished.connect(lambda: self.__cpyVersionResponse(reply))

    @pyqtSlot(QNetworkReply)
    def __cpyVersionResponse(self, reply):
        """
        Private slot handling the response of the latest version request.

        @param reply reference to the reply object
        @type QNetworkReply
        """
        latestUrl = reply.url().toString()
        tag = latestUrl.rsplit("/", 1)[-1]
        latestVersion = EricUtilities.versionToTuple(tag)

        cpyVersionStr = self.tr("unknown")
        cpyVersion = (0, 0, 0)
        if self.supportsLocalFileAccess():
            bootFile = os.path.join(self.getWorkspace(), "boot_out.txt")
            if os.path.exists(bootFile):
                with open(bootFile, "r") as f:
                    line = f.readline()
                cpyVersionStr = line.split(";")[0].split()[2]
                cpyVersion = EricUtilities.versionToTuple(cpyVersionStr)
        if (
            cpyVersion == (0, 0, 0)
            and self._deviceData
            and self._deviceData["mpy_version"] != "unknown"
        ):
            # drive is not mounted or 'boot_out.txt' is missing but the device
            # is connected via the serial console
            cpyVersionStr = self._deviceData["mpy_version"]
            cpyVersion = EricUtilities.versionToTuple(cpyVersionStr)

        msg = self.tr(
            "<h4>CircuitPython Version Information</h4>"
            "<table>"
            "<tr><td>Installed:</td><td>{0}</td></tr>"
            "<tr><td>Available:</td><td>{1}</td></tr>"
            "</table>"
        ).format(cpyVersionStr, tag)
        if cpyVersion < latestVersion and cpyVersion != (0, 0, 0):
            msg += self.tr("<p><b>Update available!</b></p>")

        EricMessageBox.information(
            None,
            self.tr("CircuitPython Version"),
            msg,
        )

    @pyqtSlot()
    def __installLibraryFiles(self, packageMode=False):
        """
        Private slot to install Python files into the onboard library.

        @param packageMode flag indicating to install a library package
            (defaults to False)
        @type bool (optional)
        """
        title = (
            self.tr("Install Library Package")
            if packageMode
            else self.tr("Install Library Files")
        )
        if not self.__deviceVolumeMounted():
            EricMessageBox.critical(
                self.microPython,
                title,
                self.tr(
                    """The device volume "<b>{0}</b>" is not available."""
                    """ Ensure it is mounted properly and try again."""
                ),
            )
            return

        target = os.path.join(self.getWorkspace(), "lib")
        # ensure that the library directory exists on the device
        if not os.path.isdir(target):
            os.makedirs(target)

        if packageMode:
            libraryPackage = EricFileDialog.getExistingDirectory(
                self.microPython,
                title,
                os.path.expanduser("~"),
                EricFileDialog.Option(0),
            )
            if libraryPackage:
                target = os.path.join(target, os.path.basename(libraryPackage))
                shutil.rmtree(target, ignore_errors=True)
                shutil.copytree(libraryPackage, target)
        else:
            libraryFiles = EricFileDialog.getOpenFileNames(
                self.microPython,
                title,
                os.path.expanduser("~"),
                self.tr(
                    "Compiled Python Files (*.mpy);;"
                    "Python Files (*.py);;"
                    "All Files (*)"
                ),
            )

            for libraryFile in libraryFiles:
                if os.path.exists(libraryFile):
                    shutil.copy2(libraryFile, target)

    def getDocumentationUrl(self):
        """
        Public method to get the device documentation URL.

        @return documentation URL of the device
        @rtype str
        """
        return Preferences.getMicroPython("CircuitPythonDocuUrl")

    def getDownloadMenuEntries(self):
        """
        Public method to retrieve the entries for the downloads menu.

        @return list of tuples with menu text and URL to be opened for each
            entry
        @rtype list of tuple of (str, str)
        """
        return [
            (
                self.tr("CircuitPython Firmware"),
                Preferences.getMicroPython("CircuitPythonFirmwareUrl"),
            ),
            (
                self.tr("CircuitPython Libraries"),
                Preferences.getMicroPython("CircuitPythonLibrariesUrl"),
            ),
        ]

    @pyqtSlot()
    def __selectDeviceVolume(self):
        """
        Private slot to select the mounted device volume, if it could not be found
        automatically.
        """
        userMounts = FileSystemUtilities.getUserMounts()
        msg = (
            self.tr("Select the drive letter of the device:")
            if OSUtilities.isWindowsPlatform()
            else self.tr("Select the path of the mounted device:")
        )
        selectedMount, ok = QInputDialog.getItem(
            None,
            self.tr("Select Device Volume"),
            msg,
            userMounts,
            0,
            False,
        )
        if ok and selectedMount:
            self.__workspace = selectedMount
            self.__workspaceSelected = self.DeviceVolumeName not in self.__workspace

    ##################################################################
    ## Methods below implement WiFi related methods
    ##################################################################

    def hasWifi(self):
        """
        Public method to check the availability of WiFi.

        @return tuple containing a flag indicating the availability of WiFi
            and the WiFi type (circuitpython)
        @rtype tuple of (bool, str)
        @exception OSError raised to indicate an issue with the device
        """
        command = """
def has_wifi():
    try:
        import wifi
        if hasattr(wifi, 'radio'):
            return True, 'circuitpython'
    except (ImportError, MemoryError):
        pass

    return False, ''

print(has_wifi())
del has_wifi
"""
        try:
            return self._deviceData["wifi"], self._deviceData["wifi_type"]
        except KeyError:
            out, err = self.executeCommands(command, mode=self._submitMode)
            if err:
                raise OSError(self._shortError(err))
            return ast.literal_eval(out.decode("utf-8"))

    def getWifiData(self):
        """
        Public method to get data related to the current WiFi status.

        @return tuple of three dictionaries containing the WiFi status data
            for the WiFi client, access point and overall data
        @rtype tuple of (dict, dict, dict)
        @exception OSError raised to indicate an issue with the device
        """
        command = """
def wifi_status():
    import binascii
    import json
    import wifi

    r = wifi.radio

    station = {
        'active': r.enabled and r.ipv4_address is not None,
        'connected': r.ipv4_address is not None,
        'ifconfig': (
            str(r.ipv4_address) if r.ipv4_address else'0.0.0.0',
            str(r.ipv4_subnet) if r.ipv4_subnet else'0.0.0.0',
            str(r.ipv4_gateway) if r.ipv4_gateway else'0.0.0.0',
            str(r.ipv4_dns) if r.ipv4_dns else'0.0.0.0',
        ),
        'mac': binascii.hexlify(r.mac_address, ':').decode(),
    }
    try:
        station['txpower'] = r.tx_power
    except AttributeError:
        pass
    try:
        if r.ap_info is not None:
            station.update({
                'ap_ssid': r.ap_info.ssid,
                'ap_bssid': binascii.hexlify(r.ap_info.bssid, ':'),
                'ap_rssi': r.ap_info.rssi,
                'ap_channel': r.ap_info.channel,
                'ap_country': r.ap_info.country,
            })
            authmode = r.ap_info.authmode
            station['ap_security'] = (
                '_'.join(str(x).split('.')[-1] for x in authmode)
                if isinstance(authmode, list)
                else authmode
            )
    except (NotImplementedError, AttributeError):
        pass
    print(json.dumps(station))

    ap = {
        'active': r.enabled and r.ipv4_address_ap is not None,
        'connected': r.ipv4_address_ap is not None,
        'ifconfig': (
            str(r.ipv4_address_ap) if r.ipv4_address_ap else'0.0.0.0',
            str(r.ipv4_subnet_ap) if r.ipv4_subnet_ap else'0.0.0.0',
            str(r.ipv4_gateway_ap) if r.ipv4_gateway_ap else'0.0.0.0',
            str(r.ipv4_dns) if r.ipv4_dns else'0.0.0.0',
        ),
        'mac': binascii.hexlify(r.mac_address_ap, ':').decode(),
    }
    try:
        ap['txpower'] = r.tx_power
    except AttributeError:
        pass
    print(json.dumps(ap))

    overall = {
        'active': r.enabled,
        'hostname': r.hostname,
    }
    print(json.dumps(overall))

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
        if "ap_security" in station:
            try:
                station["ap_security"] = self.__securityTranslations[
                    station["ap_security"]
                ]
            except KeyError:
                station["ap_security"] = self.tr("unknown ({0})").format(
                    station["ap_security"]
                )

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
        command = """
def connect_wifi(ssid, password, hostname):
    import json
    import wifi

    r = wifi.radio
    try:
        if hostname:
            r.hostname = hostname
        r.start_station()
        r.connect(ssid, password)
        status = 'connected'
    except Exception as exc:
        status = str(exc)

    print(json.dumps({{'connected': r.ipv4_address is not None, 'status': status}}))

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

        result = json.loads(out.decode("utf-8").strip())
        error = "" if result["connected"] else result["status"]

        return result["connected"], error

    def disconnectWifi(self):
        """
        Public method to disconnect a device from the WiFi network.

        @return tuple containing a flag indicating success and an error string
        @rtype tuple of (bool, str)
        """
        command = """
def disconnect_wifi():
    import json
    import wifi

    r = wifi.radio
    try:
        r.stop_station()
        status = ''
    except Exception as exc:
        status = str(exc)

    print(json.dumps({'success': status == '', 'status': status}))

disconnect_wifi()
del disconnect_wifi
"""

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            return False, err

        result = json.loads(out.decode("utf-8").strip())
        return result["success"], result["status"]

    def isWifiClientConnected(self):
        """
        Public method to check the WiFi connection status as client.

        @return flag indicating the WiFi connection status
        @rtype bool
        """
        command = """
def wifi_connected():
    import wifi

    r = wifi.radio
    print(r.ipv4_address is not None)

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
        command = """
def wifi_connected():
    import wifi

    r = wifi.radio
    print(r.ipv4_address_ap is not None)
"""

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            return False

        return out.strip() == b"True"

    def writeCredentials(self, ssid, password, hostname, _country):
        """
        Public method to write the given credentials to the connected device and modify
        the start script to connect automatically.

        @param ssid SSID of the network to connect to
        @type str
        @param password password needed to authenticate
        @type str
        @param hostname host name of the device
        @type str
        @param _country WiFi country code (unused)
        @type str
        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        if not self.__deviceVolumeMounted():
            return False, self.tr("The device volume is not available.")

        workspace = self.getWorkspace()

        if EricUtilities.versionToTuple(self._deviceData["release"]) >= (8, 0, 0):
            # CircuitPython >= 8.0.0: generate 'settings.toml' file
            contents = (
                'CIRCUITPY_WIFI_SSID = "{0}"\nCIRCUITPY_WIFI_PASSWORD = "{1}"\n'
                'CIRCUITPY_WIFI_HOSTNAME = "{2}"\n'.format(ssid, password, hostname)
            )
            filename = os.path.join(workspace, "settings.toml")
            if os.path.exists(filename):
                ok = EricMessageBox.yesNo(
                    None,
                    self.tr("Write WiFi Credentials"),
                    self.tr(
                        """<p>The file <b>{0}</b> exists already. Shall it be"""
                        """ replaced?</p>"""
                    ).format(filename),
                    icon=EricMessageBox.Warning,
                )
                if not ok:
                    return False, self.tr("Aborted")
            try:
                with open(filename, "w") as f:
                    f.write(contents)
                    return True, ""
            except OSError as err:
                return False, str(err)

        else:
            # CircuitPython < 8.0.0: generate a secrets.py script
            # step 1: generate the secrets.py file
            contents = (
                'secrets = {{\n    "ssid": "{0}",\n    "password": "{1}",\n'
                '    "hostname": "{2}",\n}}\n'.format(ssid, password, hostname)
            )
            filename = os.path.join(workspace, "secrets.py")
            if os.path.exists(filename):
                ok = EricMessageBox.yesNo(
                    None,
                    self.tr("Write WiFi Credentials"),
                    self.tr(
                        """<p>The file <b>{0}</b> exists already. Shall it be"""
                        """ replaced?</p>"""
                    ).format(filename),
                    icon=EricMessageBox.Warning,
                )
                if not ok:
                    return False, self.tr("Aborted")
            try:
                with open(filename, "w") as f:
                    f.write(contents)
            except OSError as err:
                return False, str(err)

            # step 2: create the auto-connect script (wifi_connect.py)
            scriptFile = os.path.join(
                os.path.dirname(__file__), "MCUScripts", "circuitPy7WiFiConnect.py"
            )
            targetFile = os.path.join(workspace, "wifi_connect.py")
            try:
                shutil.copy2(scriptFile, targetFile)
            except OSError as err:
                return False, str(err)
            # Note: code.py will not be modified because the connection will be
            #       reset anyway
            return True, ""

    def removeCredentials(self):
        """
        Public method to remove the saved credentials from the connected device.

        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        if not self.__deviceVolumeMounted():
            return False, self.tr("The device volume is not available.")

        workspace = self.getWorkspace()
        for name in ("settings.toml", "secrets.py"):
            filename = os.path.join(workspace, name)
            if os.path.exists(filename):
                os.remove(filename)

        return True, ""

    def checkInternet(self):
        """
        Public method to check, if the internet can be reached.

        @return tuple containing a flag indicating reachability and an error string
        @rtype tuple of (bool, str)
        """
        command = """
def check_internet():
    import ipaddress
    import wifi

    r = wifi.radio
    if r.ipv4_address is not None:
        ping = r.ping(ipaddress.IPv4Address("9.9.9.9"))
        print(ping is not None)
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
        command = """
def scan_networks():
    import wifi

    r = wifi.radio
    network_list = []
    enabled = r.enabled
    if not enabled:
        r.enabled = True
    for net in r.start_scanning_networks():
        network_list.append(
            (net.ssid, net.bssid, net.channel, net.rssi,
             '_'.join(str(x).split('.')[-1] for x in net.authmode))
        )
    r.stop_scanning_networks()
    if not enabled:
        r.enabled = False
    print(network_list)

scan_networks()
del scan_networks
"""

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=15000)
        if err:
            return [], err

        networksList = ast.literal_eval(out.decode("utf-8"))
        networks = []
        seenNetworks = []
        for network in networksList:
            if network[0]:
                ssid = network[0]
                mac = binascii.hexlify(network[1], ":").decode("utf-8")
                channel = network[2]
                rssi = network[3]
                try:
                    security = self.__securityTranslations[network[4]]
                except KeyError:
                    security = self.tr("unknown ({0})").format(network[4])
                if (ssid, mac, channel) not in seenNetworks:
                    seenNetworks.append((ssid, mac, channel))
                    networks.append((ssid, mac, channel, rssi, security))

        return networks, ""

    def deactivateInterface(self, interface):
        """
        Public method to deactivate a given WiFi interface of the connected device.

        Note: With CircuitPython it is not possible to deactivate the station and
        access point interfaces separately.

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

        command = """
def deactivate():
    import wifi

    wifi.radio.enabled = False
    print(not wifi.radio.enabled)

deactivate()
del deactivate
"""

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
        if security is None or password is None:
            security = 0
            password = ""  # secok
        authmode = self.__securityCode2AuthModeString[security]

        if ifconfig:
            return (
                False,
                self.tr(
                    "CircuitPython does not support setting the IPv4 parameters of the"
                    " WiFi access point."
                ),
            )

        command = """
def start_ap(ssid, password, hostname):
    import wifi

    r = wifi.radio
    r.enabled = True
    if hostname:
        r.hostname = hostname
    try:
        r.start_ap(ssid, password, authmode={3})
    except (NotImplementedError, ValueError) as exc:
        print('Error:', str(exc))

start_ap({0}, {1}, {2})
del start_ap
""".format(
            repr(ssid), repr(password), repr(hostname), authmode
        )

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=15000)
        if err:
            return False, err
        elif out and out.startswith(b"Error:"):
            return False, out.decode("utf-8").split(None, 1)[-1]
        else:
            return True, ""

    def stopAccessPoint(self):
        """
        Public method to stop the access point interface.

        @return tuple containg a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        command = """
def stop_ap():
    import wifi

    r = wifi.radio
    try:
        r.stop_ap()
    except NotImplementedError as exc:
        print('Error:', str(exc))

stop_ap()
del stop_ap
"""

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            return False, err
        elif out and out.startswith(b"Error:"):
            return False, out.decode("utf-8").split(None, 1)[-1]
        else:
            return True, ""

    def getConnectedClients(self):
        """
        Public method to get a list of connected clients.

        @return a tuple containing a list of tuples containing the client MAC-Address
            and the RSSI (if supported and available) and an error message
        @rtype tuple of ([(bytes, int)], str)
        """
        return (
            [],
            self.tr("CircuitPython does not support reporting of connected clients."),
        )

    ##################################################################
    ## Methods below implement Ethernet related methods
    ##################################################################

    def hasEthernet(self):
        """
        Public method to check the availability of Ethernet.

        @return tuple containing a flag indicating the availability of Ethernet
            and the Ethernet type
        @rtype tuple of (bool, str)
        @exception OSError raised to indicate an issue with the device
        """
        command = """
def has_eth():
    try:
        from adafruit_wiznet5k import adafruit_wiznet5k
        if hasattr(adafruit_wiznet5k, 'WIZNET5K'):
            return True, 'cpypicowiz'
    except ImportError:
        pass

    return False, ''

print(has_eth())
del has_eth
"""
        try:
            return self._deviceData["ethernet"], self._deviceData["ethernet_type"]
        except KeyError:
            out, err = self.executeCommands(
                command, mode=self._submitMode, timeout=10000
            )
            if err:
                raise OSError(self._shortError(err))

            return ast.literal_eval(out.decode("utf-8"))

    def getEthernetStatus(self):
        """
        Public method to get Ethernet status data of the connected board.

        @return list of tuples containing the translated status data label and
            the associated value
        @rtype list of tuples of (str, str)
        @exception OSError raised to indicate an issue with the device
        """
        command = """{0}
def ethernet_status():
    import binascii
    import json

    w5x00_init()

    res = {{
        'active': nic.link_status != 0,
        'connected': nic.link_status == 1 and nic.ifconfig[0] != b'\x00\x00\x00\x00',
        'ifconfig': (
            nic.pretty_ip(nic.ifconfig[0]),
            nic.pretty_ip(nic.ifconfig[1]),
            nic.pretty_ip(nic.ifconfig[2]),
            nic.pretty_ip(nic.ifconfig[3]),
        ),
        'mac': binascii.hexlify(nic.mac_address, ':').decode(),
        'chip': nic.chip,
        'max_sockets': nic.max_sockets,
    }}
    print(json.dumps(res))

ethernet_status()
del ethernet_status, w5x00_init
""".format(
            WiznetUtilities.cpyWiznetInit()
        )

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=10000)
        if err:
            raise OSError(self._shortError(err))

        status = []
        ethStatus = json.loads(out.decode("utf-8"))
        status.append((self.tr("Active"), self.bool2str(ethStatus["active"])))
        status.append((self.tr("Connected"), self.bool2str(ethStatus["connected"])))
        status.append((self.tr("IPv4 Address"), ethStatus["ifconfig"][0]))
        status.append((self.tr("Netmask"), ethStatus["ifconfig"][1]))
        status.append((self.tr("Gateway"), ethStatus["ifconfig"][2]))
        status.append((self.tr("DNS"), ethStatus["ifconfig"][3]))
        status.append((self.tr("MAC-Address"), ethStatus["mac"]))
        status.append((self.tr("Chip Type"), ethStatus["chip"]))
        status.append((self.tr("max. Sockets"), ethStatus["max_sockets"]))

        return status

    def connectToLan(self, config, hostname):
        """
        Public method to connect the connected device to the LAN.

        Note: The MAC address of the interface is configured with the WIZ

        @param config configuration for the connection (either the string 'dhcp'
            for a dynamic address or a tuple of four strings with the IPv4 parameters.
        @type str or tuple of (str, str, str, str)
        @param hostname host name of the device
        @type str
        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        command = """{0}
def connect_lan(config, hostname):
    from adafruit_wiznet5k import adafruit_wiznet5k

    w5x00_init()

    nic.mac_address = adafruit_wiznet5k._DEFAULT_MAC
    if config == 'dhcp':
        nic.set_dhcp(hostname=hostname)
    else:
        nic.ifconfig = (
            nic.unpretty_ip(config[0]),
            nic.unpretty_ip(config[1]),
            nic.unpretty_ip(config[2]),
            tuple(int(a) for a in config[3].split('.')),
        )
    print(nic.ifconfig[0] != b'\x00\x00\x00\x00')

connect_lan({1}, {2})
del connect_lan, w5x00_init
""".format(
            WiznetUtilities.cpyWiznetInit(),
            "'dhcp'" if config == "dhcp" else config,
            repr(hostname) if hostname else "''",
        )

        with EricOverrideCursor():
            out, err = self.executeCommands(
                command, mode=self._submitMode, timeout=15000
            )
        if err:
            return False, err

        return out.strip() == b"True", ""

    def disconnectFromLan(self):
        """
        Public method  to disconnect from the LAN.

        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        command = """{0}
def disconnect_lan():
    import time

    w5x00_init()

    nic.sw_reset()
    time.sleep(1)
    print(nic.ifconfig[0] == b'\x00\x00\x00\x00')

disconnect_lan()
del disconnect_lan, w5x00_init
""".format(
            WiznetUtilities.cpyWiznetInit(),
        )

        with EricOverrideCursor():
            out, err = self.executeCommands(
                command, mode=self._submitMode, timeout=15000
            )
        if err:
            return False, err

        return out.strip() == b"True", ""

    def isLanConnected(self):
        """
        Public method to check the LAN connection status.

        @return flag indicating that the device is connected to the LAN
        @rtype bool
        """
        command = """{0}
def is_connected():
    w5x00_init()

    print(nic.link_status == 1 and nic.ifconfig[0] != b'\x00\x00\x00\x00')

is_connected()
del is_connected, w5x00_init
""".format(
            WiznetUtilities.cpyWiznetInit(),
        )

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=10000)
        if err:
            return False

        return out.strip() == b"True"

    def checkInternetViaLan(self):
        """
        Public method to check, if the internet can be reached (LAN variant).

        @return tuple containing a flag indicating reachability and an error string
        @rtype tuple of (bool, str)
        """
        command = """{0}
def check_internet():
    w5x00_init()

    if nic.ifconfig[0] != b'\x00\x00\x00\x00':
        sock = nic.get_socket()
        try:
            nic.socket_connect(sock, nic.get_host_by_name('quad9.net'), 443)
            nic.socket_disconnect(sock)
            print(True)
        except:
            print(False)
        nic.socket_close(sock)
    else:
        print(False)

check_internet()
del check_internet, w5x00_init
""".format(
            WiznetUtilities.cpyWiznetInit(),
        )

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=15000)
        if err:
            return False, err

        return out.strip() == b"True", ""

    def deactivateEthernet(self):
        """
        Public method to deactivate the Ethernet interface of the connected device.

        @return tuple containg a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        # The WIZnet 5x00 interface cannot be switched off explicitly. That means,
        # disconnect from the LAN is all we can do.

        return self.disconnectFromLan()

    def writeLanAutoConnect(self, config, hostname):
        """
        Public method to generate a script and associated configuration to connect the
        device to the LAN during boot time.

        @param config configuration for the connection (either the string 'dhcp'
            for a dynamic address or a tuple of four strings with the IPv4 parameters.
        @type str or tuple of (str, str, str, str)
        @param hostname host name of the device
        @type str
        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        if not self.__deviceVolumeMounted():
            return False, self.tr("The device volume is not available.")

        workspace = self.getWorkspace()

        if EricUtilities.versionToTuple(self._deviceData["release"]) >= (8, 0, 0):
            # CircuitPython >= 8.0.0: generate 'settings.toml' file
            newConfig = (
                {
                    "WIZNET_IFCONFIG_0": '"dhcp"',
                    "WIZNET_IFCONFIG_1": "",
                    "WIZNET_IFCONFIG_2": "",
                    "WIZNET_IFCONFIG_3": "",
                    "WIZNET_HOSTNAME": '"{0}"'.format(hostname) if hostname else '""',
                }
                if config == "dhcp"
                else {
                    "WIZNET_IFCONFIG_0": '"{0}"'.format(config[0]),
                    "WIZNET_IFCONFIG_1": '"{0}"'.format(config[1]),
                    "WIZNET_IFCONFIG_2": '"{0}"'.format(config[2]),
                    "WIZNET_IFCONFIG_3": '"{0}"'.format(config[3]),
                }
            )
            ok, err = self.__modifySettings(newConfig)
            if not ok:
                return False, err

            scriptFile = os.path.join(
                os.path.dirname(__file__), "MCUScripts", "picoWiznetConnectCpy8.py"
            )

        else:
            # step 1: generate the wiznet_config.py file
            ifconfig = "ifconfig = {0}\nhostname={1}\n".format(
                "'dhcp'" if config == "dhcp" else config,
                repr(hostname) if hostname else "''",
            )
            filename = os.path.join(workspace, "wiznet_config.py")
            if os.path.exists(filename):
                ok = EricMessageBox.yesNo(
                    None,
                    self.tr("Write Connect Script"),
                    self.tr(
                        """<p>The file <b>{0}</b> exists already. Shall it be"""
                        """ replaced?</p>"""
                    ).format(filename),
                    icon=EricMessageBox.Warning,
                )
                if not ok:
                    return False, self.tr("Aborted")
            try:
                with open(filename, "w") as f:
                    f.write(ifconfig)
            except OSError as err:
                return False, str(err)

            scriptFile = os.path.join(
                os.path.dirname(__file__), "MCUScripts", "picoWiznetConnectCpy7.py"
            )

        # step 2: create the auto-connect script (wiznet_connect.py)
        targetFile = os.path.join(workspace, "wiznet_connect.py")
        try:
            shutil.copy2(scriptFile, targetFile)
        except OSError as err:
            return False, str(err)
        # Note: code.py will not be modified because the connection will be
        #       reset anyway
        return True, ""

    def removeLanAutoConnect(self):
        """
        Public method to remove the saved IPv4 parameters from the connected device.

        Note: This disables the LAN auto-connect feature.

        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        if not self.__deviceVolumeMounted():
            return False, self.tr("The device volume is not available.")

        workspace = self.getWorkspace()

        if EricUtilities.versionToTuple(self._deviceData["release"]) >= (8, 0, 0):
            # CircuitPython >= 8.0.0: generate 'settings.toml' file
            newConfig = {
                "WIZNET_IFCONFIG_0": "",
                "WIZNET_IFCONFIG_1": "",
                "WIZNET_IFCONFIG_2": "",
                "WIZNET_IFCONFIG_3": "",
            }
            self.__modifySettings(newConfig)

        for name in ("wiznet_config.py", "wiznet_connect.py"):
            filename = os.path.join(workspace, name)
            if os.path.exists(filename):
                os.remove(filename)

        return True, ""

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
        command = """
def has_bt():
    try:
        import _bleio
        if hasattr(_bleio, 'adapter') and _bleio.adapter is not None:
            return True
    except ImportError:
        pass

    return False

print(has_bt())
del has_bt
"""
        try:
            return self._deviceData["bluetooth"]
        except KeyError:
            out, err = self.executeCommands(
                command, mode=self._submitMode, timeout=10000
            )
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
        command = """
def ble_status():
    import _bleio
    import binascii
    import json

    a = _bleio.adapter

    ble_enabled = a.enabled
    if not ble_enabled:
        a.enabled = True

    res = {
        'active': ble_enabled,
        'mac': binascii.hexlify(bytes(reversed(a.address.address_bytes)), ':').decode(),
        'addr_type': a.address.type,
        'name': a.name,
        'advertising': a.advertising,
        'connected': a.connected,
    }

    if not ble_enabled:
        a.enabled = False

    print(json.dumps(res))

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
            (self.tr("Address Type"), self.__bleAddressType[bleStatus["addr_type"]])
        )
        status.append((self.tr("Connected"), self.bool2str(bleStatus["connected"])))
        status.append((self.tr("Advertising"), self.bool2str(bleStatus["advertising"])))

        return status

    def activateBluetoothInterface(self):
        """
        Public method to activate the Bluetooth interface.

        @return flag indicating the new state of the Bluetooth interface
        @rtype bool
        @exception OSError raised to indicate an issue with the device
        """
        command = """
def activate_ble():
    import _bleio

    a = _bleio.adapter
    if not a.enabled:
        a.enabled = True
    print(a.enabled)

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
        command = """
def deactivate_ble():
    import _bleio

    a = _bleio.adapter
    if a.enabled:
        a.enabled = False
    print(a.enabled)

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
        from ..BluetoothDialogs.BluetoothAdvertisement import (
            ADV_IND,
            ADV_SCAN_IND,
            SCAN_RSP,
            BluetoothAdvertisement,
        )

        command = """
def ble_scan():
    import _bleio
    import binascii
    import time

    a = _bleio.adapter

    ble_enabled = a.enabled
    if not ble_enabled:
        a.enabled = True

    scanResults = a.start_scan(
        buffer_size=1024, extended=True, timeout={0}, minimum_rssi=-120, active=True
    )
    time.sleep({0} + 0.2)
    a.stop_scan()

    for res in scanResults:
        print({{
            'address': binascii.hexlify(
                bytes(reversed(res.address.address_bytes)), ':'
            ).decode(),
            'advertisement': res.advertisement_bytes,
            'connectable': res.connectable,
            'rssi': res.rssi,
            'scan_response': res.scan_response,
        }})

    if not ble_enabled:
        a.enabled = False

ble_scan()
del ble_scan
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
            if res["scan_response"]:
                advType = SCAN_RSP
            elif res["connectable"]:
                advType = ADV_IND
            else:
                advType = ADV_SCAN_IND
            scanResults[address].update(advType, res["rssi"], res["advertisement"])

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
        command = """
def has_ntp():
    try:
        import adafruit_ntp
        if hasattr(adafruit_ntp, 'NTP'):
            return True
    except ImportError:
        pass

    try:
        from adafruit_wiznet5k import adafruit_wiznet5k_ntp
        if hasattr(adafruit_wiznet5k_ntp, 'NTP'):
            return True
    except ImportError:
        pass

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
        if self.getDeviceData("ethernet"):
            # WIZnet 5x00 Ethernet interface
            # Note: The Adafruit NTP implementation does not close the socket after
            #       calling get_time(). That causes follow-on calls to fail. We
            #       close the socket in our code as a workaround.
            command = """{0}
def set_ntp_time(server, tz_offset, timeout):
    import rtc

    try:
        import adafruit_ntp
        from adafruit_wiznet5k import adafruit_wiznet5k_socket as socket

        w5x00_init()

        socket.set_interface(nic)
        ntp = adafruit_ntp.NTP(
            socket, server=server, tz_offset=tz_offset, socket_timeout=timeout
        )
        rtc.RTC().datetime = ntp.datetime
        return True
    except ImportError:
        from adafruit_wiznet5k import adafruit_wiznet5k_ntp

        w5x00_init()

        server_ip = nic.pretty_ip(nic.get_host_by_name(server))
        ntp = adafruit_wiznet5k_ntp.NTP(iface=nic, ntp_address=server_ip, utc=tz_offset)
        rtc.RTC().datetime = ntp.get_time()
        ntp._sock.close()
        return True

try:
    print({{
        'result': set_ntp_time({1}, {2}, {3}),
        'error': '',
    }})
except Exception as err:
    print({{
        'result': False,
        'error': str(err),
    }})
del set_ntp_time, w5x00_init
""".format(
                WiznetUtilities.cpyWiznetInit(), repr(server), tzOffset, timeout
            )

        elif self.getDeviceData("wifi"):
            # WiFi enabled board
            command = """
def set_ntp_time(server, tz_offset, timeout):
    import rtc
    import socketpool
    import wifi

    import adafruit_ntp


    r = wifi.radio
    if r.ipv4_address is None:
        return False

    pool = socketpool.SocketPool(r)
    ntp = adafruit_ntp.NTP(
        pool, server=server, tz_offset=tz_offset, socket_timeout=timeout
    )
    rtc.RTC().datetime = ntp.datetime
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

    ##################################################################
    ## Methods below implement some utility methods
    ##################################################################

    def __modifySettings(self, changedEntries):
        """
        Private method to modify the 'settings.toml' file as of CircuitPython 8.0.0.

        @param changedEntries dictionary containing the TOML entries to be changed
        @type dict of {str: str}
        @return tuple containing a success flag and an error message
        @rtype tuple of (bool, str)
        """
        workspace = self.getWorkspace()
        filename = os.path.join(workspace, "settings.toml")
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    lines = f.read().splitlines()
            except OSError as err:
                return False, str(err)
        else:
            lines = []

        for key, value in changedEntries.items():
            newLine = "{0} = {1}".format(key, value)
            for row in range(len(lines)):
                if lines[row].split("=")[0].strip() == key:
                    if value == "":
                        del lines[row]
                    else:
                        lines[row] = newLine
                    break
            else:
                if value != "":
                    lines.append(newLine)

        try:
            with open(filename, "w") as f:
                f.write("\n".join(lines))
        except OSError as err:
            return False, str(err)

        return True, ""


def createDevice(microPythonWidget, deviceType, vid, pid, boardName, _serialNumber):
    """
    Function to instantiate a MicroPython device object.

    @param microPythonWidget reference to the main MicroPython widget
    @type MicroPythonWidget
    @param deviceType device type assigned to this device interface
    @type str
    @param vid vendor ID
    @type int
    @param pid product ID
    @type int
    @param boardName name of the board
    @type str
    @param _serialNumber serial number of the board (unused)
    @type str
    @return reference to the instantiated device object
    @rtype CircuitPythonDevice
    """
    return CircuitPythonDevice(
        microPythonWidget, deviceType, boardName, vid=vid, pid=pid
    )
