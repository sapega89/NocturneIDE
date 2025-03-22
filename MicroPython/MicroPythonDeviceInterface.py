# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module  implementing an interface base class to talk to a connected MicroPython device.
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class MicroPythonDeviceInterface(QObject):
    """
    Class implementing an interface to talk to a connected MicroPython device.

    @signal executeAsyncFinished() emitted to indicate the end of an
        asynchronously executed list of commands (e.g. a script)
    @signal dataReceived(data) emitted to send data received via the connection
        for further processing
    @signal osdInfo(str) emitted when some OSD data was received from the device
    """

    executeAsyncFinished = pyqtSignal()
    dataReceived = pyqtSignal(bytes)
    osdInfo = pyqtSignal(str)

    PasteModePrompt = b"=== "
    TracebackMarker = b"Traceback (most recent call last):"

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

    def connectToDevice(self, connection):
        """
        Public method to connect to the device.

        @param connection name of the connection to be used
        @type str
        @return flag indicating success and an error message
        @rtype tuple of (bool, str)
        @exception NotImplementedError raised to indicate that this method needs to
            be implemented in a derived class
        """
        raise NotImplementedError(
            "This method needs to be implemented in a derived class."
        )

        return False, ""

    @pyqtSlot()
    def disconnectFromDevice(self):
        """
        Public slot to disconnect from the device.

        @exception NotImplementedError raised to indicate that this method needs to
            be implemented in a derived class
        """
        raise NotImplementedError(
            "This method needs to be implemented in a derived class."
        )

    def isConnected(self):
        """
        Public method to get the connection status.

        @return flag indicating the connection status
        @rtype bool
        @exception NotImplementedError raised to indicate that this method needs to
            be implemented in a derived class
        """
        raise NotImplementedError(
            "This method needs to be implemented in a derived class."
        )

        return False

    @pyqtSlot()
    def handlePreferencesChanged(self):
        """
        Public slot to handle a change of the preferences.
        """
        pass

    def write(self, data):
        """
        Public method to write data to the connected device.

        @param data data to be written
        @type bytes or bytearray
        @exception NotImplementedError raised to indicate that this method needs to
            be implemented in a derived class
        """
        raise NotImplementedError(
            "This method needs to be implemented in a derived class."
        )

    def probeDevice(self):
        """
        Public method to check the device is responding.

        If the device has not been flashed with a MicroPython firmware, the
        probe will fail.

        @return flag indicating a communicating MicroPython device
        @rtype bool
        @exception NotImplementedError raised to indicate that this method needs to
            be implemented in a derived class
        """
        raise NotImplementedError(
            "This method needs to be implemented in a derived class."
        )

        return False

    def execute(self, commands, *, mode="raw", timeout=0):
        """
        Public method to send commands to the connected device and return the
        result.

        If no connection is available, empty results will be returned.

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
        @exception NotImplementedError raised to indicate that this method needs to
            be implemented in a derived class
        @exception ValueError raised in case of an unsupported submit mode
        """
        raise NotImplementedError(
            "This method needs to be implemented in a derived class."
        )

        if mode not in ("paste", "raw"):
            raise ValueError("Unsupported submit mode given ('{0}').".format(mode))

        return b"", b""

    def executeAsync(self, commandsList, submitMode):
        """
        Public method to execute a series of commands over a period of time
        without returning any result (asynchronous execution).

        @param commandsList list of commands to be execute on the device
        @type list of str
        @param submitMode mode to be used to submit the commands (one of 'raw'
            or 'paste')
        @type str
        @exception NotImplementedError raised to indicate that this method needs to
            be implemented in a derived class
        @exception ValueError raised to indicate an unknown submit mode
        """
        raise NotImplementedError(
            "This method needs to be implemented in a derived class."
        )

        if submitMode not in ("raw", "paste"):
            raise ValueError(
                "Unsupported submit mode given ('{0}').".format(submitMode)
            )
