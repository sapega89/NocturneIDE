# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the device interface class for Teensy boards with MicroPython.
"""

from PyQt6.QtCore import QCoreApplication, QProcess, QUrl, pyqtSlot
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest
from PyQt6.QtWidgets import QMenu

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from ..MicroPythonWidget import HAS_QTCHART
from . import FirmwareGithubUrls
from .DeviceBase import BaseDevice


class TeensyDevice(BaseDevice):
    """
    Class implementing the device for Teensy boards with MicroPython.
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

        self.__createTeensyMenu()

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
        return self.tr("Teensy")

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

    def __createTeensyMenu(self):
        """
        Private method to create the microbit submenu.
        """
        self.__teensyMenu = QMenu(self.tr("Teensy Functions"))

        self.__showMpyAct = self.__teensyMenu.addAction(
            self.tr("Show MicroPython Versions"), self.__showFirmwareVersions
        )
        self.__teensyMenu.addSeparator()
        self.__teensyMenu.addAction(
            self.tr("MicroPython Flash Instructions"), showTeensyFlashInstructions
        )
        self.__flashMpyAct = self.__teensyMenu.addAction(
            self.tr("Flash MicroPython Firmware"), startTeensyLoader
        )
        self.__flashMpyAct.setToolTip(
            self.tr("Start the 'Teensy Loader' application to flash the Teensy device.")
        )
        self.__teensyMenu.addSeparator()
        self.__resetAct = self.__teensyMenu.addAction(
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
        self.__flashMpyAct.setEnabled(not linkConnected)
        self.__resetAct.setEnabled(connected)

        menu.addMenu(self.__teensyMenu)

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

        # The machine.RTC.init() function takes the arguments in the
        # order: (year, month, day, weekday, hour, minute, second,
        # subseconds)
        # https://docs.micropython.org/en/latest/library/machine.RTC.html#machine-rtc
        return """
def set_time(rtc_time):
    import machine
    rtc = machine.RTC()
    rtc.init(rtc_time[:7] + (0,))
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
    return TeensyDevice(microPythonWidget, deviceType)


@pyqtSlot()
def showTeensyFlashInstructions():
    """
    Slot to show a message box with instruction to flash the Teensy.
    """
    EricMessageBox.information(
        None,
        QCoreApplication.translate("TeensyDevice", "Flash MicroPython Firmware"),
        QCoreApplication.translate(
            "TeensyDevice",
            """<p>Teensy 4.0 and Teensy 4.1 are flashed using the 'Teensy Loader'"""
            """ application. Make sure you downloaded the MicroPython or"""
            """ CircuitPython .hex file.</p>"""
            """<p>See <a href="{0}">the PJRC Teensy web site</a>"""
            """ for details.</p>""",
        ).format("https://www.pjrc.com/teensy/loader.html"),
    )


@pyqtSlot()
def startTeensyLoader():
    """
    Slot to start the 'Teensy Loader' application.

    Note: The application must be accessible via the application search path.
    """
    ok, _ = QProcess.startDetached("teensy")
    if not ok:
        EricMessageBox.warning(
            None,
            QCoreApplication.translate("TeensyDevice", "Start 'Teensy Loader'"),
            QCoreApplication.translate(
                "TeensyDevice",
                """<p>The 'Teensy Loader' application <b>teensy</b> could not"""
                """ be started. Ensure it is in the application search path or"""
                """ start it manually.</p>""",
            ),
        )
