# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the device interface class for RP2040/RP2350 based boards
(e.g. Raspberry Pi Pico / Pico 2).
"""

import ast
import binascii
import json
import os

from PyQt6.QtCore import QUrl, pyqtSlot
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import QDialog, QMenu

from eric7 import EricUtilities, Preferences
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from ..EthernetDialogs import WiznetUtilities
from ..MicroPythonWidget import HAS_QTCHART
from . import FirmwareGithubUrls
from .DeviceBase import BaseDevice


class RP2Device(BaseDevice):
    """
    Class implementing the device for RP2040/RP2350 based boards.
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

        self.__createRP2Menu()

        self.__statusTranslations = {
            "picow": {
                -3: self.tr("authentication failed"),
                -2: self.tr("no matching access point found"),
                -1: self.tr("connection failed"),
                0: self.tr("idle"),
                1: self.tr("connecting"),
                2: self.tr("connected, waiting for IP address"),
                3: self.tr("connected"),
            },
            "picowireless": {
                0: self.tr("idle"),
                1: self.tr("no matching access point found"),
                2: self.tr("network scan completed"),
                3: self.tr("connected"),
                4: self.tr("connection failed"),
                5: self.tr("connection lost"),
                6: self.tr("disconnected"),
                7: self.tr("AP listening"),
                8: self.tr("AP connected"),
                9: self.tr("AP failed"),
            },
            "picowiz": {
                0: self.tr("switched off"),
                1: self.tr("switched on, inactive"),
                2: self.tr("switched on, active"),
            },
        }

        self.__securityTranslations = {
            "picow": {
                0: self.tr("open", "open WiFi network"),
                1: "WEP",
                2: "WPA",
                3: "WPA2",
                4: "WPA/WPA2",
                5: "WPA2 (CCMP)",
                6: "WPA3",
                7: "WPA2/WPA3",
            },
            "picowireless": {
                2: "WPA",
                4: "WPA2 (CCMP)",
                5: "WEP",
                7: self.tr("open", "open WiFi network"),
                8: self.tr("automatic"),
            },
        }

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
        return self.tr("RP2040/RP2350")

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

    def __createRP2Menu(self):
        """
        Private method to create the RP2 submenu.
        """
        self.__rp2Menu = QMenu(self.tr("RP2 Functions"))

        self.__showMpyAct = self.__rp2Menu.addAction(
            self.tr("Show MicroPython Versions"), self.__showFirmwareVersions
        )
        self.__rp2Menu.addSeparator()
        self.__bootloaderAct = self.__rp2Menu.addAction(
            self.tr("Activate Bootloader"), self.__activateBootloader
        )
        self.__flashMpyAct = self.__rp2Menu.addAction(
            self.tr("Flash MicroPython Firmware"), self.__flashPython
        )
        self.__rp2Menu.addSeparator()
        self.__resetAct = self.__rp2Menu.addAction(
            self.tr("Reset Device"), self.__resetDevice
        )

    def addDeviceMenuEntries(self, menu):
        """
        Public method to add device specific entries to the given menu.

        @param menu reference to the context menu
        @type QMenu
        """
        connected = self.microPython.isConnected()
        linkConnected = self.microPython.isLinkConnected()

        self.__showMpyAct.setEnabled(connected)
        self.__bootloaderAct.setEnabled(connected)
        self.__flashMpyAct.setEnabled(not linkConnected)
        self.__resetAct.setEnabled(connected)

        menu.addMenu(self.__rp2Menu)

    def hasFlashMenuEntry(self):
        """
        Public method to check, if the device has its own flash menu entry.

        @return flag indicating a specific flash menu entry
        @rtype bool
        """
        return True

    @pyqtSlot()
    def __flashPython(self):
        """
        Private slot to flash a MicroPython firmware to the device.
        """
        from ..UF2FlashDialog import UF2FlashDialog

        dlg = UF2FlashDialog(boardType="rp2", parent=self.microPython)
        dlg.exec()

    @pyqtSlot()
    def __activateBootloader(self):
        """
        Private slot to switch the board into 'bootloader' mode.
        """
        if self.microPython.isConnected():
            self.executeCommands(
                [
                    "import machine",
                    "machine.bootloader()",
                ],
                mode=self._submitMode,
            )
            # simulate pressing the disconnect button
            self.microPython.on_connectButton_clicked()

    @pyqtSlot()
    def __showFirmwareVersions(self):
        """
        Private slot to show the firmware version of the connected device and the
        available firmware version.
        """
        if self.microPython.isConnected():
            if self._deviceData["mpy_name"] != "micropython":
                EricMessageBox.critical(
                    self.microPython,
                    self.tr("Show MicroPython Versions"),
                    self.tr(
                        """The firmware of the connected device cannot be"""
                        """ determined or the board does not run MicroPython."""
                        """ Aborting..."""
                    ),
                )
            else:
                if self._deviceData["mpy_variant"] == "Pimoroni Pico":
                    # MicroPython with Pimoroni add-on libraries
                    url = QUrl(FirmwareGithubUrls["pimoroni_pico"])
                else:
                    url = QUrl(FirmwareGithubUrls["micropython"])
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
            currentVersionStr = (
                self._deviceData["mpy_variant_version"]
                if bool(self._deviceData["mpy_variant_version"])
                else self._deviceData["mpy_version"]
            )
            currentVersion = EricUtilities.versionToTuple(currentVersionStr)

        msg = self.tr(
            "<h4>MicroPython Version Information</h4>"
            "<table>"
            "<tr><td>Installed:</td><td>{0}</td></tr>"
            "<tr><td>Available:</td><td>{1}</td></tr>"
            "{2}"
            "</table>"
        ).format(
            currentVersionStr,
            tag,
            (
                self.tr("<tr><td>Variant:</td><td>{0}</td></tr>").format(
                    self._deviceData["mpy_variant"]
                )
                if self._deviceData["mpy_variant"]
                else ""
            ),
        )
        if self._deviceData["mpy_variant"] in ["Pimoroni Pico"] and not bool(
            self._deviceData["mpy_variant_version"]
        ):
            # cannot derive update info
            msg += self.tr("<p>Update may be available.</p>")
        elif currentVersion < latestVersion:
            msg += self.tr("<p><b>Update available!</b></p>")

        EricMessageBox.information(
            self.microPython,
            self.tr("MicroPython Version"),
            msg,
        )

    @pyqtSlot()
    def __resetDevice(self):
        """
        Private slot to reset the connected device.
        """
        if self.microPython.isConnected():
            self.executeCommands(
                "import machine\nmachine.reset()\n", mode=self._submitMode
            )

    def getDocumentationUrl(self):
        """
        Public method to get the device documentation URL.

        @return documentation URL of the device
        @rtype str
        """
        return Preferences.getMicroPython("MicroPythonDocuUrl")

    def getDownloadMenuEntries(self):
        """
        Public method to retrieve the entries for the downloads menu.

        @return list of tuples with menu text and URL to be opened for each
            entry
        @rtype list of tuple of (str, str)
        """
        return [
            (
                self.tr("MicroPython Firmware"),
                Preferences.getMicroPython("MicroPythonFirmwareUrl"),
            ),
            ("<separator>", ""),
            (self.tr("Pimoroni Pico Firmware"), FirmwareGithubUrls["pimoroni_pico"]),
            ("<separator>", ""),
            (
                self.tr("CircuitPython Firmware"),
                Preferences.getMicroPython("CircuitPythonFirmwareUrl"),
            ),
            (
                self.tr("CircuitPython Libraries"),
                Preferences.getMicroPython("CircuitPythonLibrariesUrl"),
            ),
        ]

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

        # The machine.rtc.datetime() function takes the arguments in the order:
        # (year, month, day, weekday, hour, minute, second, subseconds)
        # __IGNORE_WARNING_M891__
        # https://docs.micropython.org/en/latest/library/machine.RTC.html#machine-rtc
        return """
def set_time(rtc_time):
    import machine
    rtc = machine.RTC()
    rtc.datetime(rtc_time[:7] + (0,))
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
        menu.addSeparator()
        menu.addAction(self.tr("Set Country"), self.__setCountry).setEnabled(
            self._deviceData["wifi_type"] == "picow"
        )
        menu.addAction(self.tr("Reset Country"), self.__resetCountry).setEnabled(
            self._deviceData["wifi_type"] == "picow"
        )

    def hasWifi(self):
        """
        Public method to check the availability of WiFi.

        @return tuple containing a flag indicating the availability of WiFi
            and the WiFi type (picow or picowireless)
        @rtype tuple of (bool, str)
        @exception OSError raised to indicate an issue with the device
        """
        # picowireless:
        # It seems to take up to 20 sec to detect, that no Pico Wireless Pack is
        # attached. Therefore the command will timeout before.
        command = """
def has_wifi():
    try:
        import network
        if hasattr(network, 'WLAN'):
            wifi = network.WLAN(network.STA_IF)
            if not wifi.active():
                wifi.active(True)
                wifi.active(False)
            return True, 'picow'
    except ImportError:
        try:
            import picowireless as pw
            try:
                if pw.get_fw_version() != '':
                    return True, 'picowireless'
            except RuntimeError:
                pw.init()
                return True, 'picowireless'
        except ImportError:
            pass

    return False, ''

print(has_wifi())
del has_wifi
"""
        out, err = self.executeCommands(command, mode=self._submitMode, timeout=20000)
        if err:
            if not err.startswith(b"Timeout "):
                raise OSError(self._shortError(err))
            else:
                # pimoroni firmware loaded but no pico wireless present
                return False, ""
        if b"Failed to start CYW43" in out:
            # network module present but no CYW43 chip
            # (pimoroni firmware has everything)
            return False, ""
        return ast.literal_eval(out.decode("utf-8"))

    def hasWifiCountry(self):
        """
        Public method to check, if the device has support to set the WiFi country.

        @return flag indicating the support of WiFi country
        @rtype bool
        """
        return self._deviceData["wifi_type"] == "picow"

    def getWifiData(self):
        """
        Public method to get data related to the current WiFi status.

        @return tuple of three dictionaries containing the WiFi status data
            for the WiFi client, access point and overall data
        @rtype tuple of (dict, dict, dict)
        @exception OSError raised to indicate an issue with the device
        """
        if self._deviceData["wifi_type"] == "picow":
            command = """
def wifi_status():
    import ubinascii
    import ujson
    import network
    import rp2

    wifi = network.WLAN(network.STA_IF)
    station = {
        'active': wifi.active(),
        'connected': wifi.isconnected(),
        'status': wifi.status(),
        'ifconfig': wifi.ifconfig(),
        'mac': ubinascii.hexlify(wifi.config('mac'), ':').decode(),
        'channel': wifi.config('channel'),
        'txpower': wifi.config('txpower'),
    }
    print(ujson.dumps(station))

    wifi = network.WLAN(network.AP_IF)
    ap = {
        'active': wifi.active(),
        'connected': wifi.isconnected(),
        'status': wifi.status(),
        'ifconfig': wifi.ifconfig(),
        'mac': ubinascii.hexlify(wifi.config('mac'), ':').decode(),
        'channel': wifi.config('channel'),
        'txpower': wifi.config('txpower'),
        'essid': wifi.config('essid'),
    }
    print(ujson.dumps(ap))

    overall = {
        'active': station['active'] or ap['active']
    }
    try:
        overall['country'] = network.country()
    except AttributeError:
        overall['country'] = rp2.country()
    try:
        overall['hostname'] = network.hostname()
    except AttributeError:
        pass
    print(ujson.dumps(overall))

wifi_status()
del wifi_status
"""
        elif self._deviceData["wifi_type"] == "picowireless":
            command = """
def wifi_status():
    import picowireless as pw
    import ubinascii
    import ujson

    def ip_str(ip):
        return '.'.join(str(i) for i in ip)

    station = {
        'active': pw.get_connection_status() not in (0, 7, 8, 9),
        'connected': pw.get_connection_status() == 3,
        'status': pw.get_connection_status(),
        'ifconfig': (
            ip_str(pw.get_ip_address()),
            ip_str(pw.get_subnet_mask()),
            ip_str(pw.get_gateway_ip()),
            '0.0.0.0'
        ),
        'mac': ubinascii.hexlify(pw.get_mac_address(), ':').decode(),
    }
    if station['connected']:
        station.update({
            'ap_ssid': pw.get_current_ssid(),
            'ap_bssid': ubinascii.hexlify(pw.get_current_bssid(), ':'),
            'ap_rssi': pw.get_current_rssi(),
            'ap_security': pw.get_current_encryption_type(),
        })
    print(ujson.dumps(station))

    ap = {
        'active': pw.get_connection_status() in (7, 8, 9),
        'connected': pw.get_connection_status() == 8,
        'status': pw.get_connection_status(),
        'mac': ubinascii.hexlify(pw.get_mac_address(), ':').decode(),
    }
    if ap['active']:
        ap['essid'] = pw.get_current_ssid()
        ap['ifconfig'] = (
            ip_str(pw.get_ip_address()),
            ip_str(pw.get_subnet_mask()),
            ip_str(pw.get_gateway_ip()),
            '0.0.0.0'
        )
    print(ujson.dumps(ap))

    overall = {
        'active': pw.get_connection_status() != 0
    }
    print(ujson.dumps(overall))

wifi_status()
del wifi_status
"""
        else:
            return super().getWifiData()

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))

        stationStr, apStr, overallStr = out.decode("utf-8").splitlines()
        station = json.loads(stationStr)
        ap = json.loads(apStr)
        overall = json.loads(overallStr)
        if "status" in station:
            # translate the numerical status to a string
            try:
                station["status"] = self.__statusTranslations[
                    self._deviceData["wifi_type"]
                ][station["status"]]
            except KeyError:
                station["status"] = str(station["status"])
        if "status" in ap:
            # translate the numerical status to a string
            try:
                ap["status"] = self.__statusTranslations[self._deviceData["wifi_type"]][
                    ap["status"]
                ]
            except KeyError:
                ap["status"] = str(ap["status"])
        if "ap_security" in station:
            # translate the numerical AP security to a string
            try:
                station["ap_security"] = self.__securityTranslations[
                    self._deviceData["wifi_type"]
                ][station["ap_security"]]
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
        if self._deviceData["wifi_type"] == "picow":
            country = Preferences.getMicroPython("WifiCountry").upper()
            command = """
def connect_wifi(ssid, password, hostname, country):
    import network
    import rp2
    import ujson
    from time import sleep

    rp2.country(country)

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
    while max_wait:
        if wifi.status() < 0 or wifi.status() >= 3:
            break
        max_wait -= 1
        sleep(0.1)
    status = wifi.status()
    print(ujson.dumps({{'connected': wifi.isconnected(), 'status': status}}))

connect_wifi({0}, {1}, {2}, {3})
del connect_wifi
""".format(
                repr(ssid),
                repr(password if password else ""),
                repr(hostname),
                repr(country if country else "XX"),
            )
        elif self._deviceData["wifi_type"] == "picowireless":
            command = """
def connect_wifi(ssid, password):
    import picowireless as pw
    import ujson
    from time import sleep

    pw.init()
    if bool(password):
        pw.wifi_set_passphrase(ssid, password)
    else:
        pw.wifi_set_network(ssid)

    max_wait = 140
    while max_wait:
        if pw.get_connection_status() == 3:
            break
        max_wait -= 1
        sleep(0.1)
    status = pw.get_connection_status()
    if status == 3:
        pw.set_led(0, 64, 0)
    else:
        pw.set_led(64, 0, 0)
    print(ujson.dumps({{'connected': status == 3, 'status': status}}))

connect_wifi({0}, {1})
del connect_wifi
""".format(
                repr(ssid),
                repr(password if password else ""),
            )
        else:
            return super().connectWifi(ssid, password, hostname)

        with EricOverrideCursor():
            out, err = self.executeCommands(
                command, mode=self._submitMode, timeout=15000
            )
        if err:
            return False, err

        result = json.loads(out.decode("utf-8").strip())
        if result["connected"]:
            error = ""
        else:
            try:
                error = self.__statusTranslations[self._deviceData["wifi_type"]][
                    result["status"]
                ]
            except KeyError:
                error = str(result["status"])

        return result["connected"], error

    def disconnectWifi(self):
        """
        Public method to disconnect a device from the WiFi network.

        @return tuple containing a flag indicating success and an error string
        @rtype tuple of (bool, str)
        """
        if self._deviceData["wifi_type"] == "picow":
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
        elif self._deviceData["wifi_type"] == "picowireless":
            command = """
def disconnect_wifi():
    import picowireless as pw
    from time import sleep

    pw.disconnect()
    sleep(0.1)
    print(pw.get_connection_status() != 3)
    pw.set_led(0, 0, 0)

disconnect_wifi()
del disconnect_wifi
"""
        else:
            return super().disconnectWifi()

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
        if self._deviceData["wifi_type"] == "picow":
            command = """
def wifi_connected():
    import network

    wifi = network.WLAN(network.STA_IF)
    print(wifi.isconnected())

wifi_connected()
del wifi_connected
"""
        elif self._deviceData["wifi_type"] == "picowireless":
            command = """
def wifi_connected():
    import picowireless as pw

    print(pw.get_connection_status() == 3)

wifi_connected()
del wifi_connected
"""
        else:
            return super().isWifiClientConnected()

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
        if self._deviceData["wifi_type"] == "picow":
            command = """
def wifi_connected():
    import network

    wifi = network.WLAN(network.AP_IF)
    print(wifi.isconnected())

wifi_connected()
del wifi_connected
"""
        elif self._deviceData["wifi_type"] == "picowireless":
            command = """
def wifi_connected():
    import picowireless as pw

    print(pw.get_connection_status() == 8)

wifi_connected()
del wifi_connected
"""
        else:
            return super().isWifiClientConnected()

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
        command = """
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

        if self._deviceData["wifi_type"] == "picow":
            secrets = (
                "WIFI_SSID = {0}\nWIFI_KEY = {1}\nWIFI_COUNTRY={2}\n"
                "WIFI_HOSTNAME = {3}\n"
            ).format(
                repr(ssid),
                repr(password) if password else '""',
                repr(country.upper()) if country else '""',
                repr(hostname) if hostname else '""',
            )
            wifiConnectFile = "picowWiFiConnect.py"
        else:
            secrets = "WIFI_SSID = {0}\nWIFI_KEY = {1}\n".format(
                repr(ssid),
                repr(password) if password else '""',
            )
            if self._deviceData["wifi_type"] == "picowireless":
                wifiConnectFile = "pimoroniWiFiConnect.py"
            else:
                secrets += "WIFI_HOSTNAME = {0}\n".format(
                    repr(hostname if hostname else '""')
                )
                wifiConnectFile = "mpyWiFiConnect.py"
        try:
            # write secrets file
            self.putData("/secrets.py", secrets.encode("utf-8"))
            # copy auto-connect file
            self.put(
                os.path.join(os.path.dirname(__file__), "MCUScripts", wifiConnectFile),
                "/wifi_connect.py",
            )
        except OSError as err:
            return False, str(err)

        # modify boot.py
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            return False, err

        return out.decode("utf-8").strip() == "True", ""

    def removeCredentials(self):
        """
        Public method to remove the saved credentials from the connected device.

        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        try:
            self.rm("/secrets.py")
        except OSError as err:
            return False, str(err)

        return True, ""

    def checkInternet(self):
        """
        Public method to check, if the internet can be reached.

        @return tuple containing a flag indicating reachability and an error string
        @rtype tuple of (bool, str)
        """
        if self._deviceData["wifi_type"] == "picow":
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
        elif self._deviceData["wifi_type"] == "picowireless":
            command = """
def check_internet():
    import picowireless as pw

    if pw.get_connection_status() == 3:
        res = pw.ping((9, 9, 9, 9), 300)
        print(res >= 0)
    else:
        print(False)

check_internet()
del check_internet
"""
        else:
            return super().checkInternet()

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=10000)
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
        if self._deviceData["wifi_type"] == "picow":
            country = Preferences.getMicroPython("WifiCountry").upper()
            command = """
def scan_networks():
    import network
    import rp2

    rp2.country({0})

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
""".format(
                repr(country if country else "XX")
            )

        elif self._deviceData["wifi_type"] == "picowireless":
            command = """
def scan_networks():
    import picowireless as pw

    network_list = []
    pw.init()
    pw.start_scan_networks()
    networks = pw.get_scan_networks()
    for n in range(networks):
        network_list.append((
            pw.get_ssid_networks(n),
            pw.get_bssid_networks(n),
            pw.get_channel_networks(n),
            pw.get_rssi_networks(n),
            pw.get_enc_type_networks(n),
        ))
    print(network_list)

scan_networks()
del scan_networks
"""
        else:
            return super().scanNetworks()

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=15000)
        if err:
            return [], err

        networksList = ast.literal_eval(out.decode("utf-8"))
        networks = []
        for network in networksList:
            if network[0]:
                ssid = (
                    network[0].decode("utf-8")
                    if isinstance(network[0], bytes)
                    else network[0]
                )
                mac = (
                    binascii.hexlify(network[1], ":").decode("utf-8")
                    if network[1] is not None
                    else ""
                )
                channel = network[2]
                rssi = network[3]
                try:
                    security = self.__securityTranslations[
                        self._deviceData["wifi_type"]
                    ][network[4]]
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

        if self._deviceData["wifi_type"] == "picow":
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
        elif self._deviceData["wifi_type"] == "picowireless":
            command = """
def deactivate():
    import picowireless as pw

    pw.init()
    print(True)

deactivate()
del deactivate
"""
        else:
            return super().deactivateInterface(interface)

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

        if self._deviceData["wifi_type"] == "picow":
            country = Preferences.getMicroPython("WifiCountry").upper()
            if security:
                security = 4  # Pico W supports just WPA/WPA2
            command = """
def start_ap(ssid, security, password, hostname, ifconfig, country):
    import network
    import rp2
    from time import sleep

    rp2.country(country)

    if hostname:
        try:
            network.hostname(hostname)
        except AttributeError:
            pass

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    if ifconfig:
        ap.ifconfig(ifconfig)
    ap.config(ssid=ssid, security=security, password=password)
    sleep(0.1)
    print(ap.isconnected())

start_ap({0}, {1}, {2}, {3}, {4}, {5})
del start_ap
""".format(
                repr(ssid),
                security,
                repr(password),
                repr(hostname),
                ifconfig,
                repr(country if country else "XX"),
            )
        elif self._deviceData["wifi_type"] == "picowireless":
            if ifconfig:
                return (
                    False,
                    self.tr(
                        "Pico Wireless does not support setting the IPv4 parameters of"
                        " the WiFi access point."
                    ),
                )

            # AP is fixed at channel 6
            command = """
def start_ap(ssid, password):
    import picowireless as pw

    pw.init()
    if bool(password):
        res = pw.wifi_set_ap_passphrase(ssid, password, 6)
    else:
        res = pw.wifi_set_ap_network(ssid, 6)
    status = pw.get_connection_status()
    if status in (7, 8):
        pw.set_led(0, 64, 0)
    else:
        pw.set_led(64, 0, 0)
    print(res >= 0)

start_ap({0}, {1})
del start_ap
""".format(
                repr(ssid),
                repr(password if password else ""),
            )
        else:
            return super().startAccessPoint(
                ssid,
                security=security,
                password=password,
                hostname=hostname,
                ifconfig=ifconfig,
            )

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=15000)
        if err:
            return False, err
        else:
            return out.decode("utf-8").strip() == "True", ""

    def stopAccessPoint(self):
        """
        Public method to stop the access point interface.

        @return tuple containg a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        if self._deviceData["wifi_type"] in ("picow", "picowireless"):
            return self.deactivateInterface("AP")
        else:
            return super().stopAccessPoint()

    def getConnectedClients(self):
        """
        Public method to get a list of connected clients.

        @return a tuple containing a list of tuples containing the client MAC-Address
            and the RSSI (if supported and available) and an error message
        @rtype tuple of ([(bytes, int)], str)
        """
        if self._deviceData["wifi_type"] == "picow":
            command = """
def get_stations():
    import network

    ap = network.WLAN(network.AP_IF)
    stations = ap.status('stations')
    print(stations)

get_stations()
del get_stations
"""
        elif self._deviceData["wifi_type"] == "picowireless":
            return (
                [],
                self.tr(
                    "Pico Wireless does not support reporting of connected clients."
                ),
            )
        else:
            return super().checkInternet()

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

        if self._deviceData["wifi_type"] == "picow":
            config = "PASS = {0}\n".format(repr(password))
        else:
            return False, self.tr("WebREPL is not supported on this device.")

        try:
            # write config file
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
        Private slot to configure the country of the connected device.

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
    import rp2
    rp2.country({0})
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
        command = """
def has_bt():
    try:
        import bluetooth
        if hasattr(bluetooth, 'BLE'):
            ble = bluetooth.BLE()
            if not ble.active():
                ble.active(True)
                ble.active(False)
            return True
    except (ImportError, OSError):
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
    ## Methods below implement Ethernet related methods
    ##################################################################

    def hasEthernet(self):
        """
        Public method to check the availability of Ethernet.

        @return tuple containing a flag indicating the availability of Ethernet
            and the Ethernet type (picowiz)
        @rtype tuple of (bool, str)
        @exception OSError raised to indicate an issue with the device
        """
        command = """
def has_eth():
    try:
        import network
        if hasattr(network, 'WIZNET5K'):
            return True, 'picowiz'
    except ImportError:
        pass

    return False, ''

print(has_eth())
del has_eth
"""

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=10000)
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
    import network
    import ubinascii
    import ujson

    w5x00_init()

    res = {{
        'active': nic.active(),
        'connected': nic.isconnected(),
        'status': nic.status(),
        'ifconfig': nic.ifconfig(),
        'mac': ubinascii.hexlify(nic.config('mac'), ':').decode(),
    }}
    try:
        res['hostname'] = network.hostname()
    except AttributeError:
        res['hostname'] = ''
    print(ujson.dumps(res))

ethernet_status()
del ethernet_status, w5x00_init
""".format(
            WiznetUtilities.mpyWiznetInit()
        )

        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))

        status = []
        ethStatus = json.loads(out.decode("utf-8"))
        status.append((self.tr("Active"), self.bool2str(ethStatus["active"])))
        status.append((self.tr("Connected"), self.bool2str(ethStatus["connected"])))
        status.append(
            (
                self.tr("Status"),
                self.__statusTranslations["picowiz"][ethStatus["status"]],
            )
        )
        status.append(
            (
                self.tr("Hostname"),
                ethStatus["hostname"] if ethStatus["hostname"] else self.tr("unknown"),
            )
        )
        status.append((self.tr("IPv4 Address"), ethStatus["ifconfig"][0]))
        status.append((self.tr("Netmask"), ethStatus["ifconfig"][1]))
        status.append((self.tr("Gateway"), ethStatus["ifconfig"][2]))
        status.append((self.tr("DNS"), ethStatus["ifconfig"][3]))
        status.append((self.tr("MAC-Address"), ethStatus["mac"]))

        return status

    def connectToLan(self, config, hostname):
        """
        Public method to connect the connected device to the LAN.

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
    import network
    import time

    if hostname:
        try:
            network.hostname(hostname)
        except AttributeError:
            pass

    w5x00_init()

    nic.active(False)
    nic.active(True)
    nic.ifconfig(config)
    max_wait = 140
    while max_wait:
        if nic.isconnected():
            break
        max_wait -= 1
        time.sleep(0.1)
    print(nic.isconnected())

connect_lan({1}, {2})
del connect_lan, w5x00_init
""".format(
            WiznetUtilities.mpyWiznetInit(),
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

    nic.active(False)
    time.sleep(0.1)
    print(not nic.isconnected())

disconnect_lan()
del disconnect_lan, w5x00_init
""".format(
            WiznetUtilities.mpyWiznetInit(),
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
    import network

    w5x00_init()

    print(nic.isconnected())

is_connected()
del is_connected, w5x00_init
""".format(
            WiznetUtilities.mpyWiznetInit(),
        )

        out, err = self.executeCommands(command, mode=self._submitMode)
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
    import network
    import socket

    w5x00_init()

    if nic.isconnected():
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
del check_internet, w5x00_init
""".format(
            WiznetUtilities.mpyWiznetInit(),
        )

        out, err = self.executeCommands(command, mode=self._submitMode, timeout=10000)
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
        command = """
def modify_boot():
    add = True
    try:
        with open('/boot.py', 'r') as f:
            for ln in f.readlines():
                if 'wiznet_connect' in ln:
                    add = False
                    break
    except:
        pass
    if add:
        with open('/boot.py', 'a') as f:
            f.write('\\n')
            f.write('import wiznet_connect\\n')
            f.write('nic = wiznet_connect.connect_lan()\\n')
    print(True)

modify_boot()
del modify_boot
"""
        devconfig = "ifconfig = {0}\nhostname = {1}".format(
            "'dhcp'" if config == "dhcp" else config,
            repr(hostname) if hostname else "''",
        )
        try:
            # write secrets file
            self.putData("/wiznet_config.py", devconfig.encode("utf-8"))
            # copy auto-connect file
            self.put(
                os.path.join(
                    os.path.dirname(__file__), "MCUScripts", "picoWiznetConnect.py"
                ),
                "/wiznet_connect.py",
            )
        except OSError as err:
            return False, str(err)

        # modify boot.py
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            return False, err

        return out.decode("utf-8").strip() == "True", ""

    def removeLanAutoConnect(self):
        """
        Public method to remove the saved IPv4 parameters from the connected device.

        Note: This disables the LAN auto-connect feature.

        @return tuple containing a flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        try:
            self.rm("/wiznet_config.py")
        except OSError as err:
            return False, str(err)

        return True, ""

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

    def setNetworkTime(self, server="pool.ntp.org", tzOffset=0, timeout=10):
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
        command = """
def set_ntp_time(server, tz_offset, timeout):
    import network
    import ntptime
    import machine

    if hasattr(network, 'WLAN') and not network.WLAN(network.STA_IF).isconnected():
        return False
    elif hasattr(network, 'WIZNET5K'):
        try:
            if not nic.isconnected():
                return False
        except NameError:
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
    @rtype RP2Device
    """
    return RP2Device(microPythonWidget, deviceType)
