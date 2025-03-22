# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the device interface class for PyBoard boards.
"""

import os

from PyQt6.QtCore import QStandardPaths, QUrl, pyqtSlot
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import QMenu

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricProcessDialog import EricProcessDialog
from eric7.SystemUtilities import FileSystemUtilities

from ..MicroPythonWidget import HAS_QTCHART
from . import FirmwareGithubUrls
from .DeviceBase import BaseDevice


class PyBoardDevice(BaseDevice):
    """
    Class implementing the device for PyBoard boards.
    """

    DeviceVolumeName = "PYBFLASH"

    FlashInstructionsURL = (
        "https://github.com/micropython/micropython/wiki/Pyboard-Firmware-Update"
    )

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

        self._submitMode = "paste"  # use 'paste' mode

        self.__workspace = self.__findWorkspace()

        self.__createPyboardMenu()

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
        return self.tr("PyBoard")

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

        return self.DeviceVolumeName in self.getWorkspace(silent=True)

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

    def __findWorkspace(self, silent=False):
        """
        Private method to find the workspace directory.

        @param silent flag indicating silent operations
        @type bool
        @return workspace directory used for saving files
        @rtype str
        """
        # Attempts to find the path on the filesystem that represents the
        # plugged in PyBoard board.
        deviceDirectories = FileSystemUtilities.findVolume(
            self.DeviceVolumeName, findAll=True
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
                        "Python files for PyBoard can be edited in"
                        " place, if the device volume is locally"
                        " available. Such a volume was not found. In"
                        " place editing will not be available."
                    ),
                )

            return super().getWorkspace()

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

    def __createPyboardMenu(self):
        """
        Private method to create the pyboard submenu.
        """
        self.__pyboardMenu = QMenu(self.tr("PyBoard Functions"))

        self.__showMpyAct = self.__pyboardMenu.addAction(
            self.tr("Show MicroPython Versions"), self.__showFirmwareVersions
        )
        self.__pyboardMenu.addSeparator()
        self.__bootloaderAct = self.__pyboardMenu.addAction(
            self.tr("Activate Bootloader"), self.__activateBootloader
        )
        self.__dfuAct = self.__pyboardMenu.addAction(
            self.tr("List DFU-capable Devices"), self.__listDfuCapableDevices
        )
        self.__pyboardMenu.addSeparator()
        self.__flashMpyAct = self.__pyboardMenu.addAction(
            self.tr("Flash MicroPython Firmware"), self.__flashMicroPython
        )
        self.__pyboardMenu.addAction(
            self.tr("MicroPython Flash Instructions"), self.__showFlashInstructions
        )
        self.__pyboardMenu.addSeparator()
        self.__resetAct = self.__pyboardMenu.addAction(
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

        self.__bootloaderAct.setEnabled(connected)
        self.__dfuAct.setEnabled(not linkConnected)
        self.__showMpyAct.setEnabled(connected)
        self.__flashMpyAct.setEnabled(not linkConnected)
        self.__resetAct.setEnabled(connected)

        menu.addMenu(self.__pyboardMenu)

    def hasFlashMenuEntry(self):
        """
        Public method to check, if the device has its own flash menu entry.

        @return flag indicating a specific flash menu entry
        @rtype bool
        """
        return True

    @pyqtSlot()
    def __showFlashInstructions(self):
        """
        Private slot to open the URL containing instructions for installing
        MicroPython on the pyboard.
        """
        ericApp().getObject("UserInterface").launchHelpViewer(
            PyBoardDevice.FlashInstructionsURL
        )

    def __dfuUtilAvailable(self):
        """
        Private method to check the availability of dfu-util.

        @return flag indicating the availability of dfu-util
        @rtype bool
        """
        available = False
        program = Preferences.getMicroPython("DfuUtilPath")
        if not program:
            program = "dfu-util"
            if FileSystemUtilities.isinpath(program):
                available = True
        else:
            if FileSystemUtilities.isExecutable(program):
                available = True

        if not available:
            EricMessageBox.critical(
                self.microPython,
                self.tr("dfu-util not available"),
                self.tr(
                    """The dfu-util firmware flashing tool"""
                    """ <b>dfu-util</b> cannot be found or is not"""
                    """ executable. Ensure it is in the search path"""
                    """ or configure it on the MicroPython"""
                    """ configuration page."""
                ),
            )

        return available

    def __showDfuEnableInstructions(self, flash=True):
        """
        Private method to show some instructions to enable the DFU mode.

        @param flash flag indicating to show a warning message for flashing
        @type bool
        @return flag indicating OK to continue or abort
        @rtype bool
        """
        msg = self.tr(
            "<h3>Enable DFU Mode</h3>"
            "<p>1. Disconnect everything from your board</p>"
            "<p>2. Disconnect your board</p>"
            "<p>3. Connect the DFU/BOOT0 pin with a 3.3V pin</p>"
            "<p>4. Re-connect your board</p>"
            "<hr />"
        )

        if flash:
            msg += self.tr(
                "<p><b>Warning:</b> Make sure that all other DFU capable"
                " devices except your PyBoard are disconnected."
                "<hr />"
            )

        msg += self.tr("<p>Press <b>OK</b> to continue...</p>")
        res = EricMessageBox.information(
            self.microPython,
            self.tr("Enable DFU mode"),
            msg,
            EricMessageBox.Abort | EricMessageBox.Ok,
        )

        return res == EricMessageBox.Ok

    def __showDfuDisableInstructions(self):
        """
        Private method to show some instructions to disable the DFU mode.
        """
        msg = self.tr(
            "<h3>Disable DFU Mode</h3>"
            "<p>1. Disconnect your board</p>"
            "<p>2. Remove the DFU jumper</p>"
            "<p>3. Re-connect your board</p>"
            "<hr />"
            "<p>Press <b>OK</b> to continue...</p>"
        )
        EricMessageBox.information(self.microPython, self.tr("Disable DFU mode"), msg)

    @pyqtSlot()
    def __listDfuCapableDevices(self):
        """
        Private slot to list all DFU-capable devices.
        """
        if self.__dfuUtilAvailable():
            ok2continue = self.__showDfuEnableInstructions(flash=False)
            if ok2continue:
                program = Preferences.getMicroPython("DfuUtilPath")
                if not program:
                    program = "dfu-util"

                args = [
                    "--list",
                ]
                dlg = EricProcessDialog(
                    self.tr("'dfu-util' Output"),
                    self.tr("List DFU capable Devices"),
                    monospacedFont=Preferences.getEditorOtherFonts("MonospacedFont"),
                    encoding=Preferences.getSystem("IOEncoding"),
                    parent=self.microPython,
                )
                res = dlg.startProcess(program, args)
                if res:
                    dlg.exec()

    @pyqtSlot()
    def __flashMicroPython(self):
        """
        Private slot to flash a MicroPython firmware.
        """
        if self.__dfuUtilAvailable():
            ok2continue = self.__showDfuEnableInstructions()
            if ok2continue:
                program = Preferences.getMicroPython("DfuUtilPath")
                if not program:
                    program = "dfu-util"

                downloadsPath = QStandardPaths.standardLocations(
                    QStandardPaths.StandardLocation.DownloadLocation
                )[0]
                firmware = EricFileDialog.getOpenFileName(
                    self.microPython,
                    self.tr("Flash MicroPython/CircuitPython Firmware"),
                    downloadsPath,
                    self.tr(
                        "MicroPython Firmware Files (*.dfu);;"
                        "CircuitPython Firmware Files (*.bin);;"
                        "All Files (*)"
                    ),
                )
                if firmware and os.path.exists(firmware):
                    args = ["--alt", "0"]
                    if firmware.endswith(".bin"):
                        # it's a CircuitPython firmware; give the flash address
                        args.extend(["--dfuse-address", "0x08000000"])
                    args.extend(["--download", firmware])
                    dlg = EricProcessDialog(
                        self.tr("'dfu-util' Output"),
                        self.tr("Flash MicroPython Firmware"),
                        monospacedFont=Preferences.getEditorOtherFonts(
                            "MonospacedFont"
                        ),
                        encoding=Preferences.getSystem("IOEncoding"),
                        parent=self.microPython,
                    )
                    res = dlg.startProcess(program, args)
                    if res:
                        dlg.exec()
                        self.__showDfuDisableInstructions()

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
            currentVersionStr = self._deviceData["mpy_version"]
            currentVersion = EricUtilities.versionToTuple(currentVersionStr)

        msg = self.tr(
            "<h4>MicroPython Version Information</h4>"
            "<table>"
            "<tr><td>Installed:</td><td>{0}</td></tr>"
            "<tr><td>Available:</td><td>{1}</td></tr>"
            "</table>"
        ).format(currentVersionStr, tag)
        if currentVersion < latestVersion:
            msg += self.tr("<p><b>Update available!</b></p>")

        EricMessageBox.information(
            self.microPython,
            self.tr("MicroPython Version"),
            msg,
        )

    @pyqtSlot()
    def __activateBootloader(self):
        """
        Private slot to activate the bootloader and disconnect.
        """
        if self.microPython.isConnected():
            self.executeCommands(
                [
                    "import pyb",
                    "pyb.bootloader()",
                ],
                mode=self._submitMode,
            )
            # simulate pressing the disconnect button
            self.microPython.on_connectButton_clicked()

    @pyqtSlot()
    def __resetDevice(self):
        """
        Private slot to reset the connected device.
        """
        if self.microPython.isConnected():
            self.executeCommands(
                "import machine\nmachine.reset()\n", mode=self._submitMode
            )

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

        # The pyb.RTC.datetime() function takes the arguments in the
        # order: (year, month, day, weekday, hour, minute, second,
        # subseconds)
        # http://docs.micropython.org/en/latest/library/pyb.RTC.html#pyb.RTC.datetime
        return """
def set_time(rtc_time):
    import pyb
    rtc = pyb.RTC()
    rtc.datetime(rtc_time[:7] + (0,))
"""


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
    @rtype PyBoardDevice
    """
    return PyBoardDevice(microPythonWidget, deviceType)
