# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the single application server and client.
"""

import json

from PyQt6.QtCore import QByteArray
from PyQt6.QtNetwork import QLocalServer, QLocalSocket

from eric7 import EricUtilities
from eric7.EricWidgets import EricMessageBox


class SingleApplicationServer(QLocalServer):
    """
    Class implementing the single application server base class.
    """

    def __init__(self, name):
        """
        Constructor

        @param name name this server is listening to
        @type str
        """
        super().__init__()

        res = self.listen(name)
        if not res:
            # maybe it crashed last time
            self.removeServer(name)
            self.listen(name)

        self.newConnection.connect(self.__newConnection)

        self.qsock = None

    def __newConnection(self):
        """
        Private slot to handle a new connection.
        """
        sock = self.nextPendingConnection()

        # If we already have a connection, refuse this one. It will be closed
        # automatically.
        if self.qsock is not None:
            return

        self.qsock = sock

        self.qsock.readyRead.connect(self.__receiveJson)
        self.qsock.disconnected.connect(self.__disconnected)

    def __receiveJson(self):
        """
        Private method to receive the data from the client.
        """
        while self.qsock and self.qsock.canReadLine():
            line = bytes(self.qsock.readLine()).decode()

            ##print(line)          ## debug         # __IGNORE_WARNING_M891__

            try:
                commandDict = json.loads(line.strip())
            except (TypeError, ValueError) as err:
                EricMessageBox.critical(
                    None,
                    self.tr("Single Application Protocol Error"),
                    self.tr(
                        """<p>The response received from the single"""
                        """ application client could not be decoded."""
                        """ Please report this issue with the received"""
                        """ data to the eric bugs email address.</p>"""
                        """<p>Error: {0}</p>"""
                        """<p>Data:<br/>{1}</p>"""
                    ).format(str(err), EricUtilities.html_encode(line.strip())),
                    EricMessageBox.Ok,
                )
                return

            command = commandDict["command"]
            arguments = commandDict["arguments"]

            self.handleCommand(command, arguments)

    def __disconnected(self):
        """
        Private method to handle the closure of the socket.
        """
        self.qsock = None

    def shutdown(self):
        """
        Public method used to shut down the server.
        """
        if self.qsock is not None:
            self.qsock.readyRead.disconnect(self.__receiveJson)
            self.qsock.disconnected.disconnect(self.__disconnected)

        self.qsock = None

        self.close()

    def handleCommand(self, command, arguments):
        """
        Public slot to handle the command sent by the client.

        <b>Note</b>: This method must be overridden by subclasses.

        @param command command sent by the client
        @type str
        @param arguments list of command arguments
        @type list of str
        @exception NotImplementedError raised to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("'handleCommand' must be overridden")


class SingleApplicationClient:
    """
    Class implementing the single application client base class.
    """

    def __init__(self, name):
        """
        Constructor

        @param name name of the local server to connect to
        @type str
        """
        self.name = name
        self.connected = False

    def connect(self, timeout=10000):
        """
        Public method to connect the single application client to its server.

        @param timeout connection timeout value in milliseconds
        @type int
        @return value indicating success or an error number. Value is one of:
            <table>
                <tr><td>0</td><td>No application is running</td></tr>
                <tr><td>1</td><td>Application is already running</td></tr>
            </table>
        @rtype int
        """
        self.sock = QLocalSocket()
        self.sock.connectToServer(self.name)
        if self.sock.waitForConnected(timeout):
            self.connected = True
            return 1
        else:
            err = self.sock.error()
            if err == QLocalSocket.LocalSocketError.ServerNotFoundError:
                return 0
            else:
                return -err.value

    def disconnect(self):
        """
        Public method to disconnect from the Single Appliocation server.
        """
        self.sock.disconnectFromServer()
        self.connected = False

    def processArgs(self, args):
        """
        Public method to process the command line arguments passed to the UI.

        <b>Note</b>: This method must be overridden by subclasses.

        @param args namespace object containing the parsed command line parameters
        @type argparse.Namespace
        @exception NotImplementedError raised to indicate that this method must be
            implemented by a subclass
        """
        raise NotImplementedError("'processArgs' must be overridden")

    def sendCommand(self, command, arguments):
        """
        Public method to send the command to the application server.

        @param command command to be sent to the server
        @type str
        @param arguments list of command arguments
        @type list of str
        """
        if self.connected:
            commandDict = {
                "command": command,
                "arguments": arguments,
            }
            self.sock.write(
                QByteArray("{0}\n".format(json.dumps(commandDict)).encode())
            )
            self.sock.flush()

    def errstr(self):
        """
        Public method to return a meaningful error string for the last error.

        @return error string for the last error
        @rtype str
        """
        return self.sock.errorString()
