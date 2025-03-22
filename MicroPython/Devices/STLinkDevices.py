# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the device interface class for STM32 STLink boards.
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


class STLinkDevice(BaseDevice):
    """
    Class implementing the device for PyBoard boards.
    """

    DeviceVolumeName = "NODE_"

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

        self.__createSTLinkMenu()

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
        return self.tr("STM32 STLink")

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
                        "Python files for STLink boards can be edited in"
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

    def __createSTLinkMenu(self):
        """
        Private method to create the STLink submenu.
        """
        self.__stlinkMenu = QMenu(self.tr("STLink Functions"))

        self.__showMpyAct = self.__stlinkMenu.addAction(
            self.tr("Show MicroPython Versions"), self.__showFirmwareVersions
        )
        self.__stlinkMenu.addSeparator()
        self.__stlinkInfoAct = self.__stlinkMenu.addAction(
            self.tr("Show STLink Device Information"), self.__showDeviceInfo
        )
        self.__stlinkMenu.addSeparator()
        self.__flashMpyAct = self.__stlinkMenu.addAction(
            self.tr("Flash MicroPython Firmware"), self.__flashMicroPython
        )
        self.__stlinkMenu.addSeparator()
        self.__resetAct = self.__stlinkMenu.addAction(
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
        self.__stlinkInfoAct.setEnabled(not linkConnected)
        self.__flashMpyAct.setEnabled(not linkConnected)
        self.__resetAct.setEnabled(connected)

        menu.addMenu(self.__stlinkMenu)

    def hasFlashMenuEntry(self):
        """
        Public method to check, if the device has its own flash menu entry.

        @return flag indicating a specific flash menu entry
        @rtype bool
        """
        return True

    def __stlinkToolAvailable(self, toolname):
        """
        Private method to check the availability of the given STLink tool.

        Note: supported tools are st-info and st-flash

        @param toolname name of the tool to be checked
        @type str
        @return flag indicating the availability of the given STLink tool
        @rtype bool
        @exception ValueError raised to indicate an illegal tool name
        """
        if toolname not in ("st-info", "st-flash"):
            raise ValueError("Illegal tool name given.")

        preferencesKey = "StInfoPath" if toolname == "st-info" else "StFlashPath"

        available = False
        program = Preferences.getMicroPython(preferencesKey)
        if not program:
            program = toolname
            if FileSystemUtilities.isinpath(program):
                available = True
        else:
            if FileSystemUtilities.isExecutable(program):
                available = True

        if not available:
            msg = (
                self.tr(
                    """The STLink information tool <b>st-info</b> cannot be found or"""
                    """ is not executable. Ensure it is in the search path or"""
                    """ configure it on the MicroPython configuration page."""
                )
                if toolname == "st-info"
                else self.tr(
                    """The STLink firmware flashing tool <b>st-flash</b> cannot be"""
                    """ found or is not executable. Ensure it is in the search path"""
                    """ or configure it on the MicroPython configuration page."""
                )
            )
            EricMessageBox.critical(
                self.microPython,
                self.tr("{0} not available").format(toolname),
                msg,
            )

        return available

    def __stflashAvailable(self):
        """
        Private method to check the availability of the 'st-flash' firmware flashing
        tool.

        @return flag indicating the availability of the 'st-flash' firmware flashing
            tool
        @rtype bool
        """
        return self.__stlinkToolAvailable("st-flash")

    def __stinfoAvailable(self):
        """
        Private method to check the availability of the 'st-info' tool.

        @return flag indicating the availability of the 'st-info' tool
        @rtype bool
        """
        return self.__stlinkToolAvailable("st-flash")

    @pyqtSlot()
    def __flashMicroPython(self):
        """
        Private slot to flash a MicroPython firmware.
        """
        if self.__stflashAvailable():
            ok2continue = EricMessageBox.question(
                None,
                self.tr("Flash MicroPython Firmware"),
                self.tr(
                    """Ensure that only one STLink device is connected. Press OK"""
                    """ to continue."""
                ),
                EricMessageBox.Cancel | EricMessageBox.Ok,
                EricMessageBox.Cancel,
            )
            if ok2continue:
                program = Preferences.getMicroPython("StFlashPath")
                if not program:
                    program = "st-flash"

                downloadsPath = QStandardPaths.standardLocations(
                    QStandardPaths.StandardLocation.DownloadLocation
                )[0]
                firmware = EricFileDialog.getOpenFileName(
                    self.microPython,
                    self.tr("Flash MicroPython Firmware"),
                    downloadsPath,
                    self.tr("MicroPython Firmware Files (*.hex *.bin);; All Files (*)"),
                )
                if firmware and os.path.exists(firmware):
                    args = ["--connect-under-reset"]
                    if os.path.splitext(firmware)[-1].lower() == ".hex":
                        args.extend(["--format", "ihex", "write", firmware])
                    else:
                        args.extend(["write", firmware, "0x08000000"])
                    dlg = EricProcessDialog(
                        outputTitle=self.tr("'st-flash' Output"),
                        windowTitle=self.tr("Flash MicroPython Firmware"),
                        showInput=False,
                        combinedOutput=True,
                        monospacedFont=Preferences.getEditorOtherFonts(
                            "MonospacedFont"
                        ),
                        encoding=Preferences.getSystem("IOEncoding"),
                        parent=self.microPython,
                    )
                    res = dlg.startProcess(program, args)
                    if res:
                        dlg.exec()

    @pyqtSlot()
    def __showDeviceInfo(self):
        """
        Private slot to show some information about connected STLink devices.
        """
        if self.__stinfoAvailable():
            program = Preferences.getMicroPython("StInfoPath")
            if not program:
                program = "st-info"

            dlg = EricProcessDialog(
                self.tr("'st-info' Output"),
                self.tr("STLink Device Information"),
                monospacedFont=Preferences.getEditorOtherFonts("MonospacedFont"),
                encoding=Preferences.getSystem("IOEncoding"),
                parent=self.microPython,
            )
            res = dlg.startProcess(program, ["--probe"])
            if res:
                dlg.exec()

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
    def __resetDevice(self):
        """
        Private slot to reset the connected device.
        """
        if self.microPython.isConnected():
            self.executeCommands(
                "import machine\nmachine.reset()\n", mode=self._submitMode
            )


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
    return STLinkDevice(microPythonWidget, deviceType)
