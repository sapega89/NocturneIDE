# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the cooperation server.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtNetwork import QTcpServer

from eric7 import Preferences

from .Connection import Connection


class CooperationServer(QTcpServer):
    """
    Class implementing the cooperation server.

    @signal newConnection(connection) emitted after a new connection was
        received (Connection)
    """

    newConnection = pyqtSignal(Connection)

    def __init__(self, address, parent=None):
        """
        Constructor

        @param address address the server should listen on
        @type QHostAddress
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__address = address

    def incomingConnection(self, socketDescriptor):
        """
        Public method handling an incoming connection.

        @param socketDescriptor native socket descriptor
        @type int
        """
        connection = Connection(self)
        connection.setSocketDescriptor(socketDescriptor)
        self.newConnection.emit(connection)

    def startListening(self, port=-1, findFreePort=False):
        """
        Public method to start listening for new connections.

        @param port port to listen on
        @type int
        @param findFreePort flag indicating to search for a free port
            depending on the configuration
        @type bool
        @return tuple giving a flag indicating success and the port the
            server listens on
        @rtype tuple of (bool, int)
        """
        res = self.listen(self.__address, port)
        if findFreePort and Preferences.getCooperation("TryOtherPorts"):
            endPort = port + Preferences.getCooperation("MaxPortsToTry")
            while not res and port < endPort:
                port += 1
                res = self.listen(self.__address, port)
        return res, port
