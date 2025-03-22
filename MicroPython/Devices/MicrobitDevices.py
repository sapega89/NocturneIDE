# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the device interface class for BBC micro:bit and
Calliope mini boards.
"""

import ast
import contextlib
import os
import shutil

from PyQt6.QtCore import QStandardPaths, QUrl, pyqtSlot
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import QMenu

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities

from ..MicroPythonWidget import HAS_QTCHART
from . import FirmwareGithubUrls
from .DeviceBase import BaseDevice


class MicrobitDevice(BaseDevice):
    """
    Class implementing the device for BBC micro:bit and Calliope mini boards.
    """

    def __init__(self, microPythonWidget, deviceType, serialNumber, parent=None):
        """
        Constructor

        @param microPythonWidget reference to the main MicroPython widget
        @type MicroPythonWidget
        @param deviceType type of the device
        @type str
        @param serialNumber serial number of the board
        @type str
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(microPythonWidget, deviceType, parent)

        self.__boardId = 0  # illegal ID
        if serialNumber:
            with contextlib.suppress(ValueError):
                self.__boardId = int(serialNumber[:4], 16)

        self.__createMicrobitMenu()

        self.__bleAddressType = {
            0: self.tr("Public"),
            1: self.tr("Random Static"),
            2: self.tr("Random Private Resolvable"),
            3: self.tr("Random Private Non-Resolvable"),
        }

    def setConnected(self, connected):
        """
        Public method to set the connection state.

        Note: This method can be overwritten to perform actions upon connect
        or disconnect of the device.

        @param connected connection state
        @type bool
        """
        super().setConnected(connected)

        self._deviceData["local_mip"] = False

        if self.hasCircuitPython():
            self._submitMode = "paste"

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
        if self.getDeviceType() == "bbc_microbit":
            # BBC micro:bit
            return self.tr("BBC micro:bit")
        else:
            # Calliope mini
            return self.tr("Calliope mini")

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

    def hasTimeCommands(self):
        """
        Public method to check, if the device supports time commands.

        The default returns True.

        @return flag indicating support for time commands
        @rtype bool
        """
        if self.microPython.isConnected() and self.hasCircuitPython():
            return True

        return False

    def __isMicroBitV1(self):
        """
        Private method to check, if the device is a BBC micro:bit v1.

        @return falg indicating a BBC micro:bit v1
        @rtype bool
        """
        return self.__boardId in (0x9900, 0x9901)

    def __isMicroBitV2(self):
        """
        Private method to check, if the device is a BBC micro:bit v2.

        @return falg indicating a BBC micro:bit v2
        @rtype bool
        """
        return self.__boardId in (0x9903, 0x9904, 0x9905, 0x9906)

    def __isCalliope(self):
        """
        Private method to check, if the device is a Calliope mini.

        @return flag indicating a Calliope mini
        @rtype bool
        """
        return self.__boardId in (0x12A0,)

    def __createMicrobitMenu(self):
        """
        Private method to create the microbit submenu.
        """
        self.__microbitMenu = QMenu(self.tr("BBC micro:bit/Calliope Functions"))

        self.__showMpyAct = self.__microbitMenu.addAction(
            self.tr("Show MicroPython Versions"), self.__showFirmwareVersions
        )
        self.__microbitMenu.addSeparator()
        self.__flashMpyAct = self.__microbitMenu.addAction(
            self.tr("Flash MicroPython"), self.__flashMicroPython
        )
        self.__flashDAPLinkAct = self.__microbitMenu.addAction(
            self.tr("Flash Firmware"), lambda: self.__flashMicroPython(firmware=True)
        )
        self.__microbitMenu.addSeparator()
        self.__saveMainScriptAct = self.__microbitMenu.addAction(
            self.tr("Save Script as 'main.py'"), self.__saveMain
        )
        self.__saveMainScriptAct.setToolTip(
            self.tr("Save the current script as 'main.py' on the connected device")
        )
        self.__microbitMenu.addSeparator()
        self.__resetAct = self.__microbitMenu.addAction(
            self.tr("Reset {0}").format(self.deviceName()), self.__resetDevice
        )

    def addDeviceMenuEntries(self, menu):
        """
        Public method to add device specific entries to the given menu.

        @param menu reference to the context menu
        @type QMenu
        """
        connected = self.microPython.isConnected()
        linkConnected = self.microPython.isLinkConnected()

        aw = ericApp().getObject("ViewManager").activeWindow()
        canSaveMain = (
            aw is not None
            and (aw.isPyFile() or aw.isMicroPythonFile())
            and bool(aw.text().strip())
        )

        self.__showMpyAct.setEnabled(connected and self.getDeviceType() != "calliope")
        self.__flashMpyAct.setEnabled(not linkConnected)
        self.__flashDAPLinkAct.setEnabled(not linkConnected)
        self.__saveMainScriptAct.setEnabled(connected and canSaveMain)
        self.__resetAct.setEnabled(connected)

        menu.addMenu(self.__microbitMenu)

    def hasFlashMenuEntry(self):
        """
        Public method to check, if the device has its own flash menu entry.

        @return flag indicating a specific flash menu entry
        @rtype bool
        """
        return True

    @pyqtSlot()
    def __flashMicroPython(self, firmware=False):
        """
        Private slot to flash MicroPython or the DAPLink firmware to the
        device.

        @param firmware flag indicating to flash the DAPLink firmware
        @type bool
        """
        # Attempts to find the path on the file system that represents the
        # plugged in micro:bit board. To flash the DAPLink firmware, it must be
        # in maintenance mode, for MicroPython in standard mode.
        if self.getDeviceType() == "bbc_microbit":
            # BBC micro:bit
            if firmware:
                deviceDirectories = FileSystemUtilities.findVolume(
                    "MAINTENANCE", findAll=True
                )
            else:
                deviceDirectories = FileSystemUtilities.findVolume(
                    "MICROBIT", findAll=True
                )
        else:
            # Calliope mini
            if firmware:
                deviceDirectories = FileSystemUtilities.findVolume(
                    "MAINTENANCE", findAll=True
                )
            else:
                deviceDirectories = FileSystemUtilities.findVolume("MINI", findAll=True)
        if len(deviceDirectories) == 0:
            if self.getDeviceType() == "bbc_microbit":
                # BBC micro:bit is not ready or not mounted
                if firmware:
                    EricMessageBox.critical(
                        self.microPython,
                        self.tr("Flash MicroPython/Firmware"),
                        self.tr(
                            "<p>The BBC micro:bit is not ready for flashing"
                            " the DAPLink firmware. Follow these"
                            " instructions. </p>"
                            "<ul>"
                            "<li>unplug USB cable and any batteries</li>"
                            "<li>keep RESET button pressed and plug USB cable"
                            " back in</li>"
                            "<li>a drive called MAINTENANCE should be"
                            " available</li>"
                            "</ul>"
                            "<p>See the "
                            '<a href="https://microbit.org/guide/firmware/">'
                            "micro:bit web site</a> for details.</p>"
                        ),
                    )
                else:
                    EricMessageBox.critical(
                        self.microPython,
                        self.tr("Flash MicroPython/Firmware"),
                        self.tr(
                            "<p>The BBC micro:bit is not ready for flashing"
                            " the MicroPython firmware. Please make sure,"
                            " that a drive called MICROBIT is available."
                            "</p>"
                        ),
                    )
            else:
                # Calliope mini is not ready or not mounted
                if firmware:
                    EricMessageBox.critical(
                        self.microPython,
                        self.tr("Flash MicroPython/Firmware"),
                        self.tr(
                            '<p>The "Calliope mini" is not ready for flashing'
                            " the DAPLink firmware. Follow these"
                            " instructions. </p>"
                            "<ul>"
                            "<li>unplug USB cable and any batteries</li>"
                            "<li>keep RESET button pressed an plug USB cable"
                            " back in</li>"
                            "<li>a drive called MAINTENANCE should be"
                            " available</li>"
                            "</ul>"
                        ),
                    )
                else:
                    EricMessageBox.critical(
                        self.microPython,
                        self.tr("Flash MicroPython/Firmware"),
                        self.tr(
                            '<p>The "Calliope mini" is not ready for flashing'
                            " the MicroPython firmware. Please make sure,"
                            " that a drive called MINI is available."
                            "</p>"
                        ),
                    )
        elif len(deviceDirectories) == 1:
            downloadsPath = QStandardPaths.standardLocations(
                QStandardPaths.StandardLocation.DownloadLocation
            )[0]
            firmware = EricFileDialog.getOpenFileName(
                self.microPython,
                self.tr("Flash MicroPython/Firmware"),
                downloadsPath,
                self.tr("MicroPython/Firmware Files (*.hex *.bin);;All Files (*)"),
            )
            if firmware and os.path.exists(firmware):
                shutil.copy2(firmware, deviceDirectories[0])
        else:
            EricMessageBox.warning(
                self.microPython,
                self.tr("Flash MicroPython/Firmware"),
                self.tr(
                    "There are multiple devices ready for flashing."
                    " Please make sure, that only one device is prepared."
                ),
            )

    @pyqtSlot()
    def __showFirmwareVersions(self):
        """
        Private slot to show the firmware version of the connected device and the
        available firmware version.
        """
        if self.microPython.isConnected() and self.checkDeviceData(quiet=False):
            if self._deviceData["mpy_name"] not in ("micropython", "circuitpython"):
                EricMessageBox.critical(
                    self.microPython,
                    self.tr("Show MicroPython Versions"),
                    self.tr(
                        """The firmware of the connected device cannot be"""
                        """ determined or the board does not run MicroPython"""
                        """ or CircuitPython. Aborting..."""
                    ),
                )
            else:
                if self.getDeviceType() == "bbc_microbit":
                    if self._deviceData["mpy_name"] == "micropython":
                        if self.__isMicroBitV1():
                            url = QUrl(FirmwareGithubUrls["microbit_v1"])
                        elif self.__isMicroBitV2():
                            url = QUrl(FirmwareGithubUrls["microbit_v2"])
                        else:
                            EricMessageBox.critical(
                                None,
                                self.tr("Show MicroPython Versions"),
                                self.tr(
                                    """<p>The BBC micro:bit generation cannot be"""
                                    """ determined. Aborting...</p>"""
                                ),
                            )
                            return
                    elif self._deviceData["mpy_name"] == "circuitpython":
                        url = QUrl(FirmwareGithubUrls["circuitpython"])
                else:
                    EricMessageBox.critical(
                        self.microPython,
                        self.tr("Show MicroPython Versions"),
                        self.tr(
                            """<p>The firmware URL for the device type <b>{0}</b>"""
                            """ is not known. Aborting...</p>"""
                        ).format(self.getDeviceType()),
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

        if self._deviceData["release"] == "unknown":
            currentVersionStr = self.tr("unknown")
            currentVersion = (0, 0, 0)
        else:
            currentVersionStr = self._deviceData["release"]
            currentVersion = EricUtilities.versionToTuple(currentVersionStr)

        if self._deviceData["mpy_name"] == "circuitpython":
            kind = "CircuitPython"
            microbitVersion = "2"  # only v2 device can run CircuitPython
        elif self._deviceData["mpy_name"] == "micropython":
            kind = "MicroPython"
            if self.__isMicroBitV1():
                microbitVersion = "1"
            elif self.__isMicroBitV2():
                microbitVersion = "2"
        else:
            kind = self.tr("Firmware")
            microbitVersion = "?"

        msg = self.tr(
            "<h4>{0} Version Information<br/>"
            "(BBC micro:bit v{1})</h4>"
            "<table>"
            "<tr><td>Installed:</td><td>{2}</td></tr>"
            "<tr><td>Available:</td><td>{3}</td></tr>"
            "</table>"
        ).format(kind, microbitVersion, currentVersionStr, tag)
        if currentVersion < latestVersion:
            msg += self.tr("<p><b>Update available!</b></p>")

        EricMessageBox.information(
            self.microPython,
            self.tr("{0} Version").format(kind),
            msg,
        )

    @pyqtSlot()
    def __saveMain(self):
        """
        Private slot to copy the current script as 'main.py' onto the
        connected device.
        """
        aw = ericApp().getObject("ViewManager").activeWindow()
        if aw:
            title = self.tr("Save Script as 'main.py'")

            if not (aw.isPyFile() or aw.isMicroPythonFile()):
                yes = EricMessageBox.yesNo(
                    self.microPython,
                    title,
                    self.tr(
                        """The current editor does not contain a Python"""
                        """ script. Write it anyway?"""
                    ),
                )
                if not yes:
                    return

            script = aw.text().strip()
            if not script:
                EricMessageBox.warning(
                    self.microPython,
                    title,
                    self.tr("""The script is empty. Aborting."""),
                )
                return

            self.putData("main.py", script.encode("utf-8"))

            # reset the device
            self.__resetDevice()

    @pyqtSlot()
    def __resetDevice(self):
        """
        Private slot to reset the connected device.
        """
        if self.microPython.isConnected():
            if self.getDeviceType() == "bbc_microbit":
                # BBC micro:bit
                self.executeCommands(
                    "import microbit\nmicrobit.reset()\n", mode=self._submitMode
                )
            else:
                # Calliope mini
                self.executeCommands(
                    "import calliope_mini\ncalliope_mini.reset()\n",
                    mode=self._submitMode,
                )

    def getDocumentationUrl(self):
        """
        Public method to get the device documentation URL.

        @return documentation URL of the device
        @rtype str
        """
        if self.getDeviceType() == "bbc_microbit":
            # BBC micro:bit
            if self._deviceData and self._deviceData["mpy_name"] == "circuitpython":
                return Preferences.getMicroPython("CircuitPythonDocuUrl")
            else:
                return Preferences.getMicroPython("MicrobitDocuUrl")
        else:
            # Calliope mini
            return Preferences.getMicroPython("CalliopeDocuUrl")

    def getDownloadMenuEntries(self):
        """
        Public method to retrieve the entries for the downloads menu.

        @return list of tuples with menu text and URL to be opened for each
            entry
        @rtype list of tuple of (str, str)
        """
        if self.getDeviceType() == "bbc_microbit":
            if self.__isMicroBitV1():
                return [
                    (
                        self.tr("MicroPython Firmware for BBC micro:bit V1"),
                        Preferences.getMicroPython("MicrobitMicroPythonUrl"),
                    ),
                    (
                        self.tr("DAPLink Firmware"),
                        Preferences.getMicroPython("MicrobitFirmwareUrl"),
                    ),
                ]
            elif self.__isMicroBitV2():
                return [
                    (
                        self.tr("MicroPython Firmware for BBC micro:bit V2"),
                        Preferences.getMicroPython("MicrobitV2MicroPythonUrl"),
                    ),
                    (
                        self.tr("CircuitPython Firmware for BBC micro:bit V2"),
                        "https://circuitpython.org/board/microbit_v2/",
                    ),
                    (
                        self.tr("DAPLink Firmware"),
                        Preferences.getMicroPython("MicrobitFirmwareUrl"),
                    ),
                ]
            else:
                return []
        else:
            return [
                (
                    self.tr("MicroPython Firmware"),
                    Preferences.getMicroPython("CalliopeMicroPythonUrl"),
                ),
                (
                    self.tr("DAPLink Firmware"),
                    Preferences.getMicroPython("CalliopeDAPLinkUrl"),
                ),
            ]

    ##################################################################
    ## Methods below implement the file system commands
    ##################################################################

    def ls(self, dirname=""):
        """
        Public method to get a directory listing of the connected device.

        @param dirname name of the directory to be listed
        @type str
        @return tuple containg the directory listing
        @rtype tuple of str
        @exception OSError raised to indicate an issue with the device
        """
        if self.hasCircuitPython():
            return super().ls(dirname=dirname)
        else:
            # BBC micro:bit with MicroPython does not support directories
            command = """
import os as __os_
print(__os_.listdir())
del __os_
"""
            out, err = self.executeCommands(command, mode=self._submitMode)
            if err:
                raise OSError(self._shortError(err))
            return ast.literal_eval(out.decode("utf-8"))

    def lls(self, dirname="", fullstat=False, showHidden=False):
        """
        Public method to get a long directory listing of the connected device
        including meta data.

        @param dirname name of the directory to be listed
        @type str
        @param fullstat flag indicating to return the full stat() tuple
        @type bool
        @param showHidden flag indicating to show hidden files as well
        @type bool
        @return list containing the directory listing with tuple entries of
            the name and and a tuple of mode, size and time (if fullstat is
            false) or the complete stat() tuple. 'None' is returned in case the
            directory doesn't exist.
        @rtype tuple of (str, tuple)
        @exception OSError raised to indicate an issue with the device
        """
        if self.hasCircuitPython():
            return super().lls(
                dirname=dirname, fullstat=fullstat, showHidden=showHidden
            )
        else:
            # BBC micro:bit with MicroPython does not support directories
            command = """
import os as __os_

def is_visible(filename, showHidden):
    return showHidden or (filename[0] != '.' and filename[-1] != '~')

def stat(filename):
    size = __os_.size(filename)
    return (0, 0, 0, 0, 0, 0, size, 0, 0, 0)

def listdir_stat(showHidden):
    files = __os_.listdir()
    return list((f, stat(f)) for f in files if is_visible(f,showHidden))

print(listdir_stat({0}))
del __os_, stat, listdir_stat, is_visible
""".format(
                showHidden
            )
            out, err = self.executeCommands(command, mode=self._submitMode)
            if err:
                raise OSError(self._shortError(err))
            fileslist = ast.literal_eval(out.decode("utf-8"))
            if fileslist is None:
                return None
            else:
                if fullstat:
                    return fileslist
                else:
                    return [(f, (s[0], s[6], s[8])) for f, s in fileslist]

    def pwd(self):
        """
        Public method to get the current directory of the connected device.

        @return current directory
        @rtype str
        """
        if self.hasCircuitPython():
            return super().pwd()
        else:
            # BBC micro:bit with MicroPython does not support directories
            return ""

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
        if self.hasCircuitPython():
            return super()._getSetTimeCode()
        else:
            return ""

    ##################################################################
    ## Methods below implement Bluetooth related methods
    ##
    ## Note: These functions are only available on BBC micro:bit v2
    ##       with CircuitPython firmware loaded. This is handled
    ##       through the 'hasBluetooth()' method.
    ##
    ## The Bluetooth related code below is a copy of the one found in
    ## the CircuitPythonDevices.py module with modifications to cope
    ## with the limited set of available modules (e.g. no binascii
    ## or json).
    ##################################################################

    def hasBluetooth(self):
        """
        Public method to check the availability of Bluetooth.

        @return flag indicating the availability of Bluetooth
        @rtype bool
        @exception OSError raised to indicate an issue with the device
        """
        if not self.hasCircuitPython():
            return False

        command = """
def has_bt():
    try:
        import _bleio
        if hasattr(_bleio, 'adapter'):
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
        command = """
def ble_status():
    import _bleio

    def address2str(address):
        return ':'.join('{0:02x}'.format(x) for x in address)

    a = _bleio.adapter

    ble_enabled = a.enabled
    if not ble_enabled:
        a.enabled = True

    res = {
        'active': ble_enabled,
        'mac': address2str(bytes(reversed(a.address.address_bytes))),
        'addr_type': a.address.type,
        'name': a.name,
        'advertising': a.advertising,
        'connected': a.connected,
    }

    if not ble_enabled:
        a.enabled = False

    print(res)

ble_status()
del ble_status
"""
        out, err = self.executeCommands(command, mode=self._submitMode)
        if err:
            raise OSError(self._shortError(err))

        status = []
        bleStatus = ast.literal_eval(out.decode("utf-8"))
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
    import time

    def address2str(address):
        return ':'.join('{{0:02x}}'.format(x) for x in address)

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
            'address': address2str(bytes(reversed(res.address.address_bytes))),
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


def createDevice(microPythonWidget, deviceType, _vid, _pid, _boardName, serialNumber):
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
    @param serialNumber serial number of the board
    @type str
    @return reference to the instantiated device object
    @rtype MicrobitDevice
    """
    return MicrobitDevice(microPythonWidget, deviceType, serialNumber)
