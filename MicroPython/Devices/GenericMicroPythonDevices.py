# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the device interface class for generic MicroPython devices
(i.e. those devices not specifically supported yet).
"""

import os

from PyQt6.QtCore import QUrl, pyqtSlot
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import QMenu

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities

from ..MicroPythonWidget import HAS_QTCHART
from . import FirmwareGithubUrls
from .DeviceBase import BaseDevice


class GenericMicroPythonDevice(BaseDevice):
    """
    Class implementing the device interface for generic MicroPython boards.
    """

    def __init__(self, microPythonWidget, deviceType, vid, pid, parent=None):
        """
        Constructor

        @param microPythonWidget reference to the main MicroPython widget
        @type MicroPythonWidget
        @param deviceType device type assigned to this device interface
        @type str
        @param vid vendor ID
        @type int
        @param pid product ID
        @type int
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(microPythonWidget, deviceType, parent)

        self.__createGenericMenu()

        self.__directAccess = False
        self.__deviceVolumeName = ""
        self.__workspace = ""
        self.__deviceName = ""

        for deviceData in Preferences.getMicroPython("ManualDevices"):
            if deviceData["vid"] == vid and deviceData["pid"] == pid:
                self.__deviceVolumeName = deviceData["data_volume"]
                self.__directAccess = bool(deviceData["data_volume"])
                self.__deviceName = deviceData["description"]

                if self.__directAccess:
                    self.__workspace = self.__findWorkspace()

    def setButtons(self):
        """
        Public method to enable the supported action buttons.
        """
        super().setButtons()

        self.microPython.setActionButtons(
            run=True, repl=True, files=True, chart=HAS_QTCHART
        )

    def deviceName(self):
        """
        Public method to get the name of the device.

        @return name of the device
        @rtype str
        """
        return self.__deviceName

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

    def __createGenericMenu(self):
        """
        Private method to create the Generic submenu.
        """
        self.__genericMenu = QMenu(self.tr("Generic Device Functions"))

        self.__showMpyAct = self.__genericMenu.addAction(
            self.tr("Show MicroPython Versions"), self.__showFirmwareVersions
        )
        self.__genericMenu.addSeparator()
        self.__bootloaderAct = self.__genericMenu.addAction(
            self.tr("Activate Bootloader"), self.__activateBootloader
        )
        self.__genericMenu.addSeparator()
        self.__resetAct = self.__genericMenu.addAction(
            self.tr("Reset Device"), self.__resetDevice
        )

    def addDeviceMenuEntries(self, menu):
        """
        Public method to add device specific entries to the given menu.

        @param menu reference to the context menu
        @type QMenu
        """
        connected = self.microPython.isConnected()

        self.__showMpyAct.setEnabled(connected)
        self.__bootloaderAct.setEnabled(connected)
        self.__resetAct.setEnabled(connected)

        menu.addMenu(self.__genericMenu)

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

        return self.__directAccess and self.__deviceVolumeName in self.getWorkspace(
            silent=True
        )

    def getWorkspace(self, silent=False):
        """
        Public method to get the workspace directory.

        @param silent flag indicating silent operations
        @type bool
        @return workspace directory used for saving files
        @rtype str
        """
        if self.__directAccess:
            if self.__workspace:
                # return cached entry
                return self.__workspace
            else:
                self.__workspace = self.__findWorkspace(silent=silent)
                return self.__workspace
        else:
            return super().getWorkspace()

    def __findWorkspace(self, silent=False):
        """
        Private method to find the workspace directory.

        @param silent flag indicating silent operations
        @type bool
        @return workspace directory used for saving files
        @rtype str
        """
        # Attempts to find the path on the filesystem that represents the
        # plugged in board.
        deviceDirectories = FileSystemUtilities.findVolume(
            self.__deviceVolumeName, findAll=True
        )

        if deviceDirectories:
            if len(deviceDirectories) == 1:
                return deviceDirectories[0]
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
                        "Python files for this generic board can be"
                        " edited in place, if the device volume is locally"
                        " available. A volume named '{0}' was not found."
                        " In place editing will not be available."
                    ).format(self.__deviceVolumeName),
                )

            return super().getWorkspace()

    @pyqtSlot()
    def __activateBootloader(self):
        """
        Private slot to switch the board into 'bootloader' mode.
        """
        if self.microPython.isConnected():
            self.executeCommands(
                "import machine\nmachine.bootloader()\n", mode=self._submitMode
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
                ui = ericApp().getObject("UserInterface")
                request = QNetworkRequest(QUrl(FirmwareGithubUrls["micropython"]))
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
        if currentVersion < latestVersion:
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
            # simulate pressing the disconnect button
            self.microPython.on_connectButton_clicked()

    def getDocumentationUrl(self):
        """
        Public method to get the device documentation URL.

        @return documentation URL of the device
        @rtype str
        """
        return Preferences.getMicroPython("MicroPythonDocuUrl")

    def getFirmwareUrl(self):
        """
        Public method to get the device firmware download URL.

        @return firmware download URL of the device
        @rtype str
        """
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
        #
        # https://docs.micropython.org/en/latest/library/machine.RTC.html#machine-rtc
        return """
def set_time(rtc_time):
    try:
        import machine
        rtc = machine.RTC()
        rtc.datetime(rtc_time[:7] + (0,))
    except Exception:
        pass
"""


def createDevice(microPythonWidget, deviceType, vid, pid, _boardName, _serialNumber):
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
    @param _boardName name of the board (unused)
    @type str
    @param _serialNumber serial number of the board (unused)
    @type str
    @return reference to the instantiated device object
    @rtype GenericMicroPythonDevice
    """
    return GenericMicroPythonDevice(microPythonWidget, deviceType, vid, pid)
