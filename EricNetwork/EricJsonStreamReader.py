# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a JSON based reader class.
"""

import json

from PyQt6.QtCore import pyqtSignal, pyqtSlot
from PyQt6.QtNetwork import QHostAddress, QTcpServer

from eric7 import EricUtilities
from eric7.EricWidgets import EricMessageBox


class EricJsonReader(QTcpServer):
    """
    Class implementing a JSON based reader class.

    The reader is responsible for opening a socket to listen for writer
    connections.

    @signal dataReceived(object) emitted after a data object was received
    """

    dataReceived = pyqtSignal(object)

    def __init__(self, name="", interface="127.0.0.1", parent=None):
        """
        Constructor

        @param name name of the server (used for output only) (defaults to "")
        @type str (optional)
        @param interface network interface to be used (IP address or one of "all",
            "allv4", "allv6", "localv4" or "localv6") (defaults to "127.0.0.1")
        @type str (optional)
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

        self.__name = name
        self.__connection = None

        # setup the network interface
        if interface in ("allv4", "localv4") or "." in interface:
            # IPv4
            self.__hostAddress = "127.0.0.1"
        elif interface in ("all", "allv6", "localv6"):
            # IPv6
            self.__hostAddress = "::1"
        else:
            self.__hostAddress = interface
        self.listen(QHostAddress(self.__hostAddress))

        self.newConnection.connect(self.handleNewConnection)

        ## Note: Need the address and port if client is started external in debugger.
        hostAddressStr = (
            "[{0}]".format(self.__hostAddress)
            if ":" in self.__hostAddress
            else self.__hostAddress
        )
        print(  # __IGNORE_WARNING_M801__
            "JSON server ({2}) listening on: {0}:{1:d}".format(
                hostAddressStr, self.serverPort(), self.__name
            )
        )

    def address(self):
        """
        Public method to get the host address.

        @return host address
        @rtype str
        """
        return self.__hostAddress

    def port(self):
        """
        Public method to get the port number to connect to.

        @return port number
        @rtype int
        """
        return self.serverPort()

    @pyqtSlot()
    def handleNewConnection(self):
        """
        Public slot for new incoming connections from a writer.
        """
        connection = self.nextPendingConnection()
        if not connection.isValid():
            return

        if self.__connection is not None:
            self.__connection.close()

        self.__connection = connection

        connection.readyRead.connect(self.__receiveJson)
        connection.disconnected.connect(self.__handleDisconnect)

    @pyqtSlot()
    def __handleDisconnect(self):
        """
        Private slot handling a disconnect of the writer.
        """
        if self.__connection is not None:
            self.__receiveJson()  # read all buffered data first
            self.__connection.close()

        self.__connection = None

    @pyqtSlot()
    def __receiveJson(self):
        """
        Private slot handling received data from the writer.
        """
        while self.__connection and self.__connection.canReadLine():
            dataStr = self.__connection.readLine()
            jsonLine = bytes(dataStr).decode("utf-8", "backslashreplace")

            # - print("JSON Reader ({0}): {1}".format(self.__name, jsonLine))
            # - this is for debugging only

            try:
                data = json.loads(jsonLine.strip())
            except (TypeError, ValueError) as err:
                EricMessageBox.critical(
                    None,
                    self.tr("JSON Protocol Error"),
                    self.tr(
                        """<p>The data received from the writer"""
                        """ could not be decoded. Please report"""
                        """ this issue with the received data to the"""
                        """ eric bugs email address.</p>"""
                        """<p>Error: {0}</p>"""
                        """<p>Data:<br/>{1}</p>"""
                    ).format(str(err), EricUtilities.html_encode(jsonLine.strip())),
                    EricMessageBox.Ok,
                )
                return

            self.dataReceived.emit(data)
