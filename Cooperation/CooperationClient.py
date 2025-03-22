# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the client of the cooperation package.
"""

import collections

from PyQt6.QtCore import QObject, QProcess, pyqtSignal
from PyQt6.QtNetwork import QAbstractSocket, QHostAddress, QHostInfo, QNetworkInterface

from eric7 import Preferences

from .Connection import Connection
from .CooperationServer import CooperationServer


class CooperationClient(QObject):
    """
    Class implementing the client of the cooperation package.

    @signal newMessage(user, message) emitted after a new message has
        arrived (string, string)
    @signal newParticipant(nickname) emitted after a new participant joined
        (string)
    @signal participantLeft(nickname) emitted after a participant left (string)
    @signal connectionError(message) emitted when a connection error occurs
        (string)
    @signal cannotConnect() emitted, if the initial connection fails
    @signal editorCommand(hash, filename, message) emitted when an editor
        command has been received (string, string, string)
    """

    newMessage = pyqtSignal(str, str)
    newParticipant = pyqtSignal(str)
    participantLeft = pyqtSignal(str)
    connectionError = pyqtSignal(str)
    cannotConnect = pyqtSignal()
    editorCommand = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__chatWidget = parent

        self.__servers = []
        for networkInterface in QNetworkInterface.allInterfaces():
            for addressEntry in networkInterface.addressEntries():
                address = addressEntry.ip()
                # fix scope of link local addresses
                if address.toString().lower().startswith("fe80"):
                    address.setScopeId(networkInterface.humanReadableName())
                server = CooperationServer(address, self)
                server.newConnection.connect(self.__newConnection)
                self.__servers.append(server)

        self.__peers = collections.defaultdict(list)

        self.__initialConnection = None

        envVariables = ["USERNAME", "USERDOMAIN", "USER", "HOSTNAME", "DOMAINNAME"]
        environment = QProcess.systemEnvironment()
        found = False
        for envVariable in envVariables:
            for env in environment:
                if env.startswith(envVariable):
                    envList = env.split("=")
                    if len(envList) == 2:
                        self.__username = envList[1].strip()
                        found = True
                        break

            if found:
                break

        if self.__username == "":
            self.__username = self.tr("unknown")

        self.__listening = False
        self.__serversErrorString = ""

    def chatWidget(self):
        """
        Public method to get a reference to the chat widget.

        @return reference to the chat widget
        @rtype ChatWidget
        """
        return self.__chatWidget

    def sendMessage(self, message):
        """
        Public method to send a message.

        @param message message to be sent
        @type str
        """
        if message == "":
            return

        for connectionList in self.__peers.values():
            for connection in connectionList:
                connection.sendMessage(message)

    def nickName(self):
        """
        Public method to get the nick name.

        @return nick name
        @rtype str
        """
        return "{0}@{1}@{2}".format(
            self.__username, QHostInfo.localHostName(), self.__servers[0].serverPort()
        )

    def hasConnection(self, senderIp, senderPort=-1):
        """
        Public method to check for an existing connection.

        @param senderIp address of the sender
        @type QHostAddress
        @param senderPort port of the sender
        @type int
        @return flag indicating an existing connection
        @rtype bool
        """
        if senderPort == -1:
            return senderIp in self.__peers

        if senderIp not in self.__peers:
            return False

        return any(
            connection.peerPort() == senderPort for connection in self.__peers[senderIp]
        )

    def hasConnections(self):
        """
        Public method to check, if there are any connections established.

        @return flag indicating the presence of connections
        @rtype bool
        """
        return any(bool(connectionList) for connectionList in self.__peers.values())

    def removeConnection(self, connection):
        """
        Public method to remove a connection.

        @param connection reference to the connection to be removed
        @type Connection
        """
        if (
            connection.peerAddress() in self.__peers
            and connection in self.__peers[connection.peerAddress()]
        ):
            self.__peers[connection.peerAddress()].remove(connection)
            nick = connection.name()
            if nick != "":
                self.participantLeft.emit(nick)

        if connection.isValid():
            connection.abort()

    def disconnectConnections(self):
        """
        Public slot to disconnect from the chat network.
        """
        for connectionList in self.__peers.values():
            while connectionList:
                self.removeConnection(connectionList[0])

    def __newConnection(self, connection):
        """
        Private slot to handle a new connection.

        @param connection reference to the new connection
        @type Connection
        """
        connection.setParent(self)
        connection.setClient(self)
        connection.setGreetingMessage(self.__username, self.__servers[0].serverPort())

        connection.errorOccurred.connect(
            lambda err: self.__connectionError(err, connection)
        )
        connection.disconnected.connect(lambda: self.__disconnected(connection))
        connection.readyForUse.connect(lambda: self.__readyForUse(connection))
        connection.rejected.connect(self.__connectionRejected)

    def __connectionRejected(self, msg):
        """
        Private slot to handle the rejection of a connection.

        @param msg error message
        @type str
        """
        self.connectionError.emit(msg)

    def __connectionError(self, socketError, connection):
        """
        Private slot to handle a connection error.

        @param socketError reference to the error object
        @type QAbstractSocket.SocketError
        @param connection connection that caused the error
        @type Connection
        """
        if socketError != QAbstractSocket.SocketError.RemoteHostClosedError:
            if connection.peerPort() != 0:
                msg = "* {0}:{1}\n{2}\n".format(
                    connection.peerAddress().toString(),
                    connection.peerPort(),
                    connection.errorString(),
                )
            else:
                msg = "* {0}\n".format(connection.errorString())
            self.connectionError.emit(msg)
        if connection == self.__initialConnection:
            self.cannotConnect.emit()
        self.removeConnection(connection)

    def __disconnected(self, connection):
        """
        Private slot to handle the disconnection of a chat client.

        @param connection connection that was disconnected
        @type Connection
        """
        self.removeConnection(connection)

    def __readyForUse(self, connection):
        """
        Private slot to handle a connection getting ready for use.

        @param connection connection that got ready for use
        @type Connection
        """
        if self.hasConnection(connection.peerAddress(), connection.peerPort()):
            return

        connection.newMessage.connect(self.newMessage)
        connection.getParticipants.connect(lambda: self.__getParticipants(connection))
        connection.editorCommand.connect(self.editorCommand)

        self.__peers[connection.peerAddress()].append(connection)
        nick = connection.name()
        if nick != "":
            self.newParticipant.emit(nick)

        if connection == self.__initialConnection:
            connection.sendGetParticipants()
            self.__initialConnection = None

    def connectToHost(self, host, port):
        """
        Public method to connect to a host.

        @param host host to connect to
        @type str
        @param port port to connect to
        @type int
        """
        self.__initialConnection = Connection(self)
        self.__newConnection(self.__initialConnection)
        self.__initialConnection.participants.connect(self.__processParticipants)
        self.__initialConnection.connectToHost(host, port)

    def __getParticipants(self, reqConnection):
        """
        Private slot to handle the request for a list of participants.

        @param reqConnection reference to the connection to get
            participants for
        @type Connection
        """
        participants = []
        for connectionList in self.__peers.values():
            for connection in connectionList:
                if connection != reqConnection:
                    participants.append(
                        "{0}@{1}".format(
                            connection.peerAddress().toString(), connection.serverPort()
                        )
                    )
        reqConnection.sendParticipants(participants)

    def __processParticipants(self, participants):
        """
        Private slot to handle the receipt of a list of participants.

        @param participants list of participants (list of "host:port" strings)
        @type list of str
        """
        for participant in participants:
            host, port = participant.split("@")
            port = int(port)

            if port == 0:
                msg = self.tr("Illegal address: {0}@{1}\n").format(host, port)
                self.connectionError.emit(msg)
            else:
                if not self.hasConnection(QHostAddress(host), port):
                    connection = Connection(self)
                    self.__newConnection(connection)
                    connection.connectToHost(host, port)

    def sendEditorCommand(self, projectHash, filename, message):
        """
        Public method to send an editor command.

        @param projectHash hash of the project
        @type str
        @param filename project relative universal file name of
            the sending editor
        @type str
        @param message editor command to be sent
        @type str
        """
        for connectionList in self.__peers.values():
            for connection in connectionList:
                connection.sendEditorCommand(projectHash, filename, message)

    def __findConnections(self, nick):
        """
        Private method to get a list of connection given a nick name.

        @param nick nick name in the format of self.nickName()
        @type str
        @return list of references to the connection objects
        @rtype list of Connection
        """
        if "@" not in nick:
            # nick given in wrong format
            return []

        user, host, port = nick.split("@")
        senderIp = QHostAddress(host)

        if senderIp not in self.__peers:
            return []

        return self.__peers[senderIp][:]

    def kickUser(self, nick):
        """
        Public method to kick a user by its nick name.

        @param nick nick name in the format of self.nickName()
        @type str
        """
        for connection in self.__findConnections(nick):
            connection.abort()

    def banUser(self, nick):
        """
        Public method to ban a user by its nick name.

        @param nick nick name in the format of self.nickName()
        @type str
        """
        Preferences.syncPreferences()
        user = nick.rsplit("@")[0]
        bannedUsers = Preferences.getCooperation("BannedUsers")[:]
        if user not in bannedUsers:
            bannedUsers.append(user)
            Preferences.setCooperation("BannedUsers", bannedUsers)

    def banKickUser(self, nick):
        """
        Public method to ban and kick a user by its nick name.

        @param nick nick name in the format of self.nickName()
        @type str
        """
        self.banUser(nick)
        self.kickUser(nick)

    def startListening(self, port=-1):
        """
        Public method to start listening for new connections.

        @param port port to listen on
        @type int
        @return tuple giving a flag indicating success and the port the
            server listens on
        @rtype tuple of (bool, int)
        """
        if self.__servers:
            # do first server and determine free port
            res, port = self.__servers[0].startListening(port, True)
            if res and len(self.__servers) > 1:
                for server in self.__servers[1:]:
                    res, port = server.startListening(port, False)
                    if not res:
                        self.__serversErrorString = server.errorString()
            else:
                self.__serversErrorString = self.__servers[0].errorString()
        else:
            res = False
            self.__serversErrorString = self.tr("No servers present.")

        if res:
            self.__serversErrorString = ""
        self.__listening = res
        return res, port

    def isListening(self):
        """
        Public method to check, if the client is listening for connections.

        @return flag indicating the listening state
        @rtype bool
        """
        return self.__listening

    def close(self):
        """
        Public method to close all connections and stop listening.
        """
        for server in self.__servers:
            server.close()
        self.__listening = False

    def errorString(self):
        """
        Public method to get a human readable error message about the last
        server error.

        @return human readable error message about the last server error
        @rtype str
        """
        return self.__serversErrorString
