# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a websocket class to be connect to the MicroPython webrepl
interface.
"""

from PyQt6.QtCore import (
    QCoreApplication,
    QEventLoop,
    QMutex,
    QTime,
    QTimer,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtNetwork import QAbstractSocket
from PyQt6.QtWebSockets import QWebSocket

from eric7.EricUtilities.EricMutexLocker import EricMutexLocker


class MicroPythonWebreplSocket(QWebSocket):
    """
    Class implementing a websocket client to be connected to the MicroPython webrepl
    interface.

    @signal readyRead() emitted to signal the availability of data
    """

    readyRead = pyqtSignal()

    def __init__(self, timeout=10000, parent=None):
        """
        Constructor

        @param timeout timout in milliseconds to be set
        @type int
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent=parent)

        self.__connected = False
        self.__timeout = timeout  # 10s default timeout
        self.__timedOut = False

        self.__mutex = QMutex()
        self.__buffer = b""
        self.textMessageReceived.connect(self.__textDataReceived)

    @pyqtSlot(str)
    def __textDataReceived(self, strMessage):
        """
        Private slot handling a received text message.

        @param strMessage received text message
        @type str
        """
        with EricMutexLocker(self.__mutex):
            self.__buffer += strMessage.encode("utf-8")

        self.readyRead.emit()

    def setTimeout(self, timeout):
        """
        Public method to set the socket timeout value.

        @param timeout timout in milliseconds to be set
        @type int
        """
        self.__timeout = timeout

    def waitForConnected(self):
        """
        Public method to wait for the websocket being connected.

        @return flag indicating the connect result
        @rtype bool
        """
        loop = QEventLoop()
        self.connected.connect(loop.quit)
        self.errorOccurred.connect(loop.quit)

        def timeout():
            loop.quit()
            self.__timedOut = True

        self.__timedOut = False
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(timeout)
        timer.start(self.__timeout)

        loop.exec()
        timer.stop()
        if self.state() == QAbstractSocket.SocketState.ConnectedState:
            self.__connected = True
            return True
        else:
            self.__connected = False
            return False

    def connectToDevice(self, host, port):
        """
        Public method to connect to the given host and port.

        @param host host name or IP address
        @type str
        @param port port number
        @type int
        @return flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        if self.__connected:
            self.disconnectFromDevice()

        url = QUrl(f"ws://{host}:{port}")
        self.open(url)
        ok = self.waitForConnected()
        if not ok:
            return False, self.tr("Connection to device webrepl failed.")

        self.__connected = True
        return True, ""

    def disconnect(self):
        """
        Public method to disconnect the websocket.
        """
        if self.__connected:
            self.close()
            self.__connected = False

    def isConnected(self):
        """
        Public method to check the connected state of the websocket.

        @return flag indicating the connected state
        @rtype bool
        """
        return self.__connected

    def hasTimedOut(self):
        """
        Public method to check, if the last 'readUntil()' has timed out.

        @return flag indicating a timeout
        @rtype bool
        """
        return self.__timedOut

    def login(self, password):
        """
        Public method to login to the webrepl console of the device.

        @param password password
        @type str
        @return flag indicating a successful login and an error indication
        @rtype tuple of (bool, str)
        """
        self.readUntil(expected=b": ")
        self.writeTextMessage(password.encode("utf-8") + b"\r")
        data = self.readUntil([b">>> ", b"denied\r\n"])
        error = (
            self.tr("WebRepl login failed (access denied).")
            if data.endswith(b"denied\r\n")
            else ""
        )

        return error == "", error

    def writeTextMessage(self, data):
        """
        Public method write some text data to the webrepl server of the connected
        device.

        @param data text data to be sent
        @type bytes
        """
        self.sendTextMessage(data.decode("utf-8"))
        self.flush()

    def readAll(self, timeout=0):
        """
        Public method to read all available data.

        @param timeout timeout in milliseconds (0 for no timeout)
            (defaults to 0)
        @type int (optional)
        @return received data
        @rtype bytes
        """
        QCoreApplication.processEvents(
            QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents
        )
        if timeout > 0:
            # receive data for 'timeout' milliseconds
            loop = QEventLoop()
            QTimer.singleShot(timeout, loop.quit)
            loop.exec()

        # return all buffered data
        with EricMutexLocker(self.__mutex):
            data = self.__buffer
            self.__buffer = b""

        return data

    def readUntil(self, expected=b"\n", size=None, timeout=0):
        r"""
        Public method to read data until an expected sequence is found
        (default: \n) or a specific size is exceeded.

        @param expected expected bytes sequence
        @type bytes
        @param size maximum data to be read (defaults to None)
        @type int (optional)
        @param timeout timeout in milliseconds (0 for configured default)
            (defaults to 0)
        @type int (optional)
        @return bytes read from the device including the expected sequence
        @rtype bytes
        """
        data = b""
        self.__timedOut = False

        if timeout == 0:
            timeout = self.__timeout

        if not isinstance(expected, list):
            expected = [expected]

        t = QTime.currentTime()
        while True:
            QCoreApplication.processEvents(
                QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents, 500
            )
            with EricMutexLocker(self.__mutex):
                if any(e in self.__buffer for e in expected):
                    for e in expected:
                        index = self.__buffer.find(e)
                        if index >= 0:
                            endIndex = index + len(e)
                            data = self.__buffer[:endIndex]
                            self.__buffer = self.__buffer[endIndex:]
                            break
                    break
                if size is not None and len(self.__buffer) >= size:
                    data = self.__buffer[:size]
                    self.__buffer = self.__buffer[size:]
                    break
                if t.msecsTo(QTime.currentTime()) > timeout:
                    self.__timedOut = True
                    data = self.__buffer
                    self.__buffer = b""
                    break

        return data
