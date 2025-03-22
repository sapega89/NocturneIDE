# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module  implementing an interface to talk to a connected MicroPython device via
a webrepl connection.
"""

from PyQt6.QtCore import QThread, pyqtSlot
from PyQt6.QtWidgets import QInputDialog, QLineEdit

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox

from .MicroPythonDeviceInterface import MicroPythonDeviceInterface
from .MicroPythonWebreplSocket import MicroPythonWebreplSocket


class MicroPythonWebreplDeviceInterface(MicroPythonDeviceInterface):
    """
    Class implementing an interface to talk to a connected MicroPython device via
    a webrepl connection.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__blockReadyRead = False

        self.__socket = MicroPythonWebreplSocket(
            timeout=Preferences.getMicroPython("WebreplTimeout"), parent=self
        )
        self.__connected = False
        self.__socket.readyRead.connect(self.__readSocket)

    @pyqtSlot()
    def __readSocket(self):
        """
        Private slot to read all available data and emit it with the
        "dataReceived" signal for further processing.
        """
        if not self.__blockReadyRead:
            data = bytes(self.__socket.readAll())
            self.dataReceived.emit(data)

    def __readAll(self):
        """
        Private method to read all data and emit it for further processing.
        """
        data = self.__socket.readAll()
        self.dataReceived.emit(data)

    def connectToDevice(self, connection):
        """
        Public method to connect to the device.

        @param connection name of the connection to be used in the form of an URL string
            (ws://password@host:port)
        @type str
        @return flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        connection = connection.replace("ws://", "")
        try:
            password, hostPort = connection.split("@", 1)
        except ValueError:
            password, hostPort = None, connection
        if password is None:
            password, ok = QInputDialog.getText(
                None,
                self.tr("WebREPL Password"),
                self.tr("Enter the WebREPL password:"),
                QLineEdit.EchoMode.Password,
            )
            if not ok:
                return False, self.tr("No password given")

        try:
            host, port = hostPort.split(":", 1)
            port = int(port)
        except ValueError:
            host, port = hostPort, 8266  # default port is 8266

        self.__blockReadyRead = True
        ok, error = self.__socket.connectToDevice(host, port)
        if ok:
            ok, error = self.__socket.login(password)
            if not ok:
                EricMessageBox.warning(
                    None,
                    self.tr("WebREPL Login"),
                    self.tr(
                        "The login to the selected device 'webrepl' failed. The given"
                        " password may be incorrect."
                    ),
                )

        self.__connected = ok
        self.__blockReadyRead = False

        return self.__connected, error

    @pyqtSlot()
    def disconnectFromDevice(self):
        """
        Public slot to disconnect from the device.
        """
        self.__socket.disconnect()
        self.__connected = False

    def isConnected(self):
        """
        Public method to get the connection status.

        @return flag indicating the connection status
        @rtype bool
        """
        return self.__connected

    @pyqtSlot()
    def handlePreferencesChanged(self):
        """
        Public slot to handle a change of the preferences.
        """
        self.__socket.setTimeout(Preferences.getMicroPython("WebreplTimeout"))

    def write(self, data):
        """
        Public method to write data to the connected device.

        @param data data to be written
        @type bytes or bytearray
        """
        self.__connected and self.__socket.writeTextMessage(data)

    def probeDevice(self):
        """
        Public method to check the device is responding.

        If the device has not been flashed with a MicroPython firmware, the
        probe will fail.

        @return flag indicating a communicating MicroPython device
        @rtype bool
        """
        if not self.__connected:
            return False

        # switch on paste mode
        self.__blockReadyRead = True
        ok = self.__pasteOn()
        if not ok:
            self.__blockReadyRead = False
            return False

        # switch off raw mode
        QThread.msleep(10)
        self.__pasteOff()
        self.__blockReadyRead = False

        return True

    def execute(self, commands, *, mode="raw", timeout=0):  # noqa: U100
        """
        Public method to send commands to the connected device and return the
        result.

        @param commands list of commands to be executed
        @type str or list of str
        @keyparam mode submit mode to be used (one of 'raw' or 'paste') (defaults to
            'raw'). This is ignored because webrepl always uses 'paste' mode. (unused)
        @type str
        @keyparam timeout per command timeout in milliseconds (0 for configured default)
            (defaults to 0)
        @type int (optional)
        @return tuple containing stdout and stderr output of the device
        @rtype tuple of (bytes, bytes)
        """
        if not self.__connected:
            return b"", b"Device is not connected."

        if isinstance(commands, list):
            commands = "\n".join(commands)

        # switch on paste mode
        self.__blockReadyRead = True
        ok = self.__pasteOn()
        if not ok:
            self.__blockReadyRead = False
            return (b"", b"Could not switch to paste mode. Is the device switched on?")

        # send commands
        for command in commands.splitlines(keepends=True):
            # send the data as single lines
            commandBytes = command.encode("utf-8")
            self.__socket.writeTextMessage(commandBytes)
            ok = self.__socket.readUntil(commandBytes)
            if ok != commandBytes:
                self.__blockReadyRead = False
                return (
                    b"",
                    "Expected '{0}', got '{1}', followed by '{2}'".format(
                        commandBytes, ok, self.__socket.readAll()
                    ).encode("utf-8"),
                )

        # switch off paste mode causing the commands to be executed
        self.__pasteOff()

        # read until Python prompt
        result = (
            self.__socket.readUntil(b">>> ", timeout=timeout)
            .replace(b">>> ", b"")
            .strip()
        )
        if self.__socket.hasTimedOut():
            out, err = b"", b"Timeout while processing commands."
        else:
            # get rid of any OSD string and send it
            while result.startswith(b"\x1b]0;"):
                osd, result = result.split(b"\x1b\\", 1)
                self.osdInfo.emit(osd[4:].decode("utf-8"))

            if self.TracebackMarker in result:
                errorIndex = result.find(self.TracebackMarker)
                out, err = result[:errorIndex], result[errorIndex:].replace(">>> ", "")
            else:
                out = result
                err = b""

        self.__blockReadyRead = False
        return out, err

    def executeAsync(self, commandsList, _submitMode):
        """
        Public method to execute a series of commands over a period of time
        without returning any result (asynchronous execution).

        @param commandsList list of commands to be execute on the device
        @type list of str
        @param _submitMode mode to be used to submit the commands (unused)
        @type str (one of 'raw' or 'paste')
        """
        self.__blockReadyRead = True
        self.__pasteOn()
        command = b"\n".join(c.encode("utf-8)") for c in commandsList)
        self.__socket.writeTextMessage(command)
        self.__socket.readUntil(command)
        self.__blockReadyRead = False
        self.__pasteOff()
        self.executeAsyncFinished.emit()

    def __pasteOn(self):
        """
        Private method to switch the connected device to 'paste' mode.

        Note: switching to paste mode is done with synchronous writes.

        @return flag indicating success
        @rtype bool
        """
        if not self.__connected:
            return False

        pasteMessage = b"paste mode; Ctrl-C to cancel, Ctrl-D to finish\r\n=== "

        self.__socket.writeTextMessage(b"\x02")  # end raw mode if required
        for _i in range(3):
            # CTRL-C three times to break out of loops
            self.__socket.writeTextMessage(b"\r\x03")
            # time out after 500ms if device is not responding
        self.__socket.readAll()  # read all data and discard it
        self.__socket.writeTextMessage(b"\r\x05")  # send CTRL-E to enter paste mode
        self.__socket.readUntil(pasteMessage)

        if self.__socket.hasTimedOut():
            # it timed out; try it again and than fail
            self.__socket.writeTextMessage(b"\r\x05")  # send CTRL-E again
            self.__socket.readUntil(pasteMessage)
            if self.__socket.hasTimedOut():
                return False

        self.__socket.readAll()  # read all data and discard it
        return True

    def __pasteOff(self):
        """
        Private method to switch 'paste' mode off.
        """
        if self.__connected:
            self.__socket.writeTextMessage(b"\x04")  # send CTRL-D to cancel paste mode
