# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module  implementing an interface to talk to a connected MicroPython device via
a serial link.
"""

from PyQt6.QtCore import QCoreApplication, QEventLoop, QThread, QTimer, pyqtSlot

from eric7 import Preferences

from .MicroPythonDeviceInterface import MicroPythonDeviceInterface
from .MicroPythonSerialPort import MicroPythonSerialPort


class MicroPythonSerialDeviceInterface(MicroPythonDeviceInterface):
    """
    Class implementing an interface to talk to a connected MicroPython device via
    a serial link.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__blockReadyRead = False

        self.__serial = MicroPythonSerialPort(
            timeout=Preferences.getMicroPython("SerialTimeout"), parent=self
        )
        self.__serial.readyRead.connect(self.__readSerial)

    @pyqtSlot()
    def __readSerial(self):
        """
        Private slot to read all available serial data and emit it with the
        "dataReceived" signal for further processing.
        """
        if not self.__blockReadyRead:
            data = bytes(self.__serial.readAll())
            self.dataReceived.emit(data)

    def connectToDevice(self, connection):
        """
        Public method to connect to the device.

        @param connection name of the connection to be used
        @type str
        @return flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        return self.__serial.openSerialLink(connection)

    @pyqtSlot()
    def disconnectFromDevice(self):
        """
        Public slot to disconnect from the device.
        """
        self.__serial.closeSerialLink()

    def isConnected(self):
        """
        Public method to get the connection status.

        @return flag indicating the connection status
        @rtype bool
        """
        return self.__serial.isConnected()

    @pyqtSlot()
    def handlePreferencesChanged(self):
        """
        Public slot to handle a change of the preferences.
        """
        self.__serial.setTimeout(Preferences.getMicroPython("SerialTimeout"))

    def write(self, data):
        """
        Public method to write data to the connected device.

        @param data data to be written
        @type bytes or bytearray
        """
        self.__serial.isConnected() and self.__serial.write(data)

    def __pasteOn(self):
        """
        Private method to switch the connected device to 'paste' mode.

        Note: switching to paste mode is done with synchronous writes.

        @return flag indicating success
        @rtype bool
        """
        if not self.__serial:
            return False

        pasteMessage = b"paste mode; Ctrl-C to cancel, Ctrl-D to finish\r\n=== "

        self.__serial.clear()  # clear any buffered output before entering paste mode
        self.__serial.write(b"\x02")  # end raw mode if required
        written = self.__serial.waitForBytesWritten(500)
        # time out after 500ms if device is not responding
        if not written:
            return False
        for _i in range(3):
            # CTRL-C three times to break out of loops
            self.__serial.write(b"\r\x03")
            written = self.__serial.waitForBytesWritten(500)
            # time out after 500ms if device is not responding
            if not written:
                return False
            QThread.msleep(10)
        self.__serial.readAll()  # read all data and discard it
        self.__serial.write(b"\r\x05")  # send CTRL-E to enter paste mode
        self.__serial.readUntil(pasteMessage)

        if self.__serial.hasTimedOut():
            # it timed out; try it again and than fail
            self.__serial.write(b"\r\x05")  # send CTRL-E again
            self.__serial.readUntil(pasteMessage)
            if self.__serial.hasTimedOut():
                return False

        QCoreApplication.processEvents(
            QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
        )
        self.__serial.readAll()  # read all data and discard it
        return True

    def __pasteOff(self):
        """
        Private method to switch 'paste' mode off.
        """
        if self.__serial:
            self.__serial.write(b"\x04")  # send CTRL-D to cancel paste mode

    def __rawOn(self):
        """
        Private method to switch the connected device to 'raw' mode.

        Note: switching to raw mode is done with synchronous writes.

        @return flag indicating success
        @rtype bool
        """
        if not self.__serial:
            return False

        rawReplMessage = b"raw REPL; CTRL-B to exit\r\n>"

        self.__serial.write(b"\x02")  # end raw mode if required
        written = self.__serial.waitForBytesWritten(500)
        # time out after 500ms if device is not responding
        if not written:
            return False
        for _i in range(3):
            # CTRL-C three times to break out of loops
            self.__serial.write(b"\r\x03")
            written = self.__serial.waitForBytesWritten(500)
            # time out after 500ms if device is not responding
            if not written:
                return False
            QThread.msleep(10)
        self.__serial.readAll()  # read all data and discard it
        self.__serial.write(b"\r\x01")  # send CTRL-A to enter raw mode
        self.__serial.readUntil(rawReplMessage)
        if self.__serial.hasTimedOut():
            # it timed out; try it again and than fail
            self.__serial.write(b"\r\x01")  # send CTRL-A again
            self.__serial.readUntil(rawReplMessage)
            if self.__serial.hasTimedOut():
                return False

        QCoreApplication.processEvents(
            QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
        )
        self.__serial.readAll()  # read all data and discard it
        return True

    def __rawOff(self):
        """
        Private method to switch 'raw' mode off.
        """
        if self.__serial:
            self.__serial.write(b"\x02")  # send CTRL-B to cancel raw mode
            self.__serial.readUntil(b">>> ")  # read until Python prompt
            self.__serial.readAll()  # read all data and discard it

    def probeDevice(self):
        """
        Public method to check the device is responding.

        If the device has not been flashed with a MicroPython firmware, the
        probe will fail.

        @return flag indicating a communicating MicroPython device
        @rtype bool
        """
        if not self.__serial:
            return False

        if not self.__serial.isConnected():
            return False

        # switch on paste mode
        self.__blockReadyRead = True
        ok = self.__pasteOn()
        if not ok:
            self.__blockReadyRead = False
            return False

        # switch off paste mode
        QThread.msleep(10)
        self.__pasteOff()
        self.__blockReadyRead = False

        return True

    def execute(self, commands, *, mode="raw", timeout=0):
        """
        Public method to send commands to the connected device and return the
        result.

        If no serial connection is available, empty results will be returned.

        @param commands list of commands to be executed
        @type str or list of str
        @keyparam mode submit mode to be used (one of 'raw' or 'paste') (defaults to
            'raw')
        @type str
        @keyparam timeout per command timeout in milliseconds (0 for configured default)
            (defaults to 0)
        @type int (optional)
        @return tuple containing stdout and stderr output of the device
        @rtype tuple of (bytes, bytes)
        @exception ValueError raised in case of an unsupported submit mode
        """
        if mode not in ("paste", "raw"):
            raise ValueError("Unsupported submit mode given ('{0}').".format(mode))

        if mode == "raw":
            return self.__execute_raw(commands, timeout=timeout)
        elif mode == "paste":
            return self.__execute_paste(commands, timeout=timeout)
        else:
            # just in case
            return b"", b""

    def __execute_raw(self, commands, timeout=0):
        """
        Private method to send commands to the connected device using 'raw REPL' mode
        and return the result.

        If no serial connection is available, empty results will be returned.

        @param commands list of commands to be executed
        @type str or list of str
        @param timeout per command timeout in milliseconds (0 for configured default)
            (defaults to 0)
        @type int (optional)
        @return tuple containing stdout and stderr output of the device
        @rtype tuple of (bytes, bytes)
        """
        if not self.__serial:
            return b"", b""

        if not self.__serial.isConnected():
            return b"", b"Device not connected or not switched on."

        result = bytearray()
        err = b""

        if isinstance(commands, str):
            commands = [commands]

        # switch on raw mode
        self.__blockReadyRead = True
        ok = self.__rawOn()
        if not ok:
            self.__blockReadyRead = False
            return (b"", b"Could not switch to raw mode. Is the device switched on?")

        # send commands
        QThread.msleep(10)
        for command in commands:
            if command:
                commandBytes = command.encode("utf-8")
                self.__serial.write(commandBytes + b"\x04")
                QCoreApplication.processEvents(
                    QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
                )
                ok = self.__serial.readUntil(b"OK")
                if ok != b"OK":
                    self.__blockReadyRead = False
                    return (
                        b"",
                        "Expected 'OK', got '{0}', followed by '{1}'".format(
                            ok, self.__serial.readAll()
                        ).encode("utf-8"),
                    )

                # read until prompt
                response = self.__serial.readUntil(b"\x04>", timeout=timeout)
                if self.__serial.hasTimedOut():
                    out, err = b"", b"Timeout while processing commands."
                    break
                if b"\x04" in response[:-2]:
                    # split stdout, stderr
                    out, err = response[:-2].split(b"\x04")
                    result += out
                else:
                    err = b"invalid response received: " + response
                if err:
                    result = b""
                    break

        # switch off raw mode
        QThread.msleep(10)
        self.__rawOff()
        self.__blockReadyRead = False

        return bytes(result), err

    def __execute_paste(self, commands, timeout=0):
        """
        Private method to send commands to the connected device using 'paste' mode
        and return the result.

        If no serial connection is available, empty results will be returned.

        @param commands list of commands to be executed
        @type str or list of str
        @param timeout per command timeout in milliseconds (0 for configured default)
            (defaults to 0)
        @type int (optional)
        @return tuple containing stdout and stderr output of the device
        @rtype tuple of (bytes, bytes)
        """
        if not self.__serial:
            return b"", b""

        if not self.__serial.isConnected():
            return b"", b"Device is not connected or not switched on."

        if isinstance(commands, list):
            commands = "\n".join(commands)

        # switch on paste mode
        self.__blockReadyRead = True
        ok = self.__pasteOn()
        if not ok:
            self.__blockReadyRead = False
            return (b"", b"Could not switch to paste mode. Is the device switched on?")

        # send commands
        QThread.msleep(10)
        for command in commands.splitlines(keepends=True):
            # send the data as single lines
            commandBytes = command.encode("utf-8")
            self.__serial.write(commandBytes)
            QCoreApplication.processEvents(
                QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
            )
            QThread.msleep(10)
            ok = self.__serial.readUntil(commandBytes)
            if ok != commandBytes:
                self.__blockReadyRead = False
                return (
                    b"",
                    "Expected '{0}', got '{1}', followed by '{2}'".format(
                        commandBytes, ok, self.__serial.readAll()
                    ).encode("utf-8"),
                )

        # switch off paste mode causing the commands to be executed
        self.__pasteOff()
        QThread.msleep(10)
        # read until Python prompt
        result = (
            self.__serial.readUntil(b">>> ", timeout=timeout)
            .replace(b">>> ", b"")
            .strip()
        )
        if self.__serial.hasTimedOut():
            out, err = b"", b"Timeout while processing commands."
        else:
            # get rid of any OSD string and send it
            while result.startswith(b"\x1b]0;"):
                osd, result = result.split(b"\x1b\\", 1)
                self.osdInfo.emit(osd[4:].decode("utf-8"))

            if self.TracebackMarker in result:
                errorIndex = result.find(self.TracebackMarker)
                out, err = result[:errorIndex], result[errorIndex:]
            else:
                out = result
                err = b""

        self.__blockReadyRead = False
        return out, err

    def executeAsync(self, commandsList, submitMode):
        """
        Public method to execute a series of commands over a period of time
        without returning any result (asynchronous execution).

        @param commandsList list of commands to be execute on the device
        @type list of str
        @param submitMode mode to be used to submit the commands
        @type str (one of 'raw' or 'paste')
        @exception ValueError raised to indicate an unknown submit mode
        """
        if submitMode not in ("raw", "paste"):
            raise ValueError("Illegal submit mode given ({0})".format(submitMode))

        if submitMode == "raw":
            startSequence = [  # sequence of commands to enter raw mode
                b"\x02",  # Ctrl-B: exit raw repl (just in case)
                b"\r\x03\x03\x03",  # Ctrl-C three times: interrupt any running program
                b"\r\x01",  # Ctrl-A: enter raw REPL
                b'print("\\n")\r',
            ]
            endSequence = [
                b"\r",
                b"\x04",
            ]
            self.__executeAsyncRaw(
                startSequence
                + [c.encode("utf-8") + b"\r" for c in commandsList]
                + endSequence
            )
        elif submitMode == "paste":
            self.__executeAsyncPaste(commandsList)

    def __executeAsyncRaw(self, commandsList):
        """
        Private method to execute a series of commands over a period of time
        without returning any result (asynchronous execution).

        @param commandsList list of commands to be execute on the device
        @type list of bytes
        """
        if commandsList:
            command = commandsList.pop(0)
            self.__serial.write(command)
            QTimer.singleShot(2, lambda: self.__executeAsyncRaw(commandsList))
        else:
            self.__rawOff()
            self.executeAsyncFinished.emit()

    def __executeAsyncPaste(self, commandsList):
        """
        Private method to execute a series of commands over a period of time
        without returning any result (asynchronous execution).

        @param commandsList list of commands to be execute on the device
        @type list of str
        """
        self.__blockReadyRead = True
        self.__pasteOn()
        command = b"\n".join(c.encode("utf-8)") for c in commandsList)
        self.__serial.write(command)
        self.__serial.readUntil(command)
        self.__blockReadyRead = False
        self.__pasteOff()
        self.executeAsyncFinished.emit()
