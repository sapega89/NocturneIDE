# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class representing a peer connection.
"""

from PyQt6.QtCore import QByteArray, QTime, QTimer, pyqtSignal
from PyQt6.QtNetwork import QHostInfo, QTcpSocket

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

MaxBufferSize = 1024 * 1024
TransferTimeout = 30 * 1000
PongTimeout = 60 * 1000
PingInterval = 5 * 1000
SeparatorToken = "|||"
SeparatorToken_b = b"|||"


class Connection(QTcpSocket):
    """
    Class representing a peer connection.

    @signal readyForUse() emitted when the connection is ready for use
    @signal newMessage(user, message) emitted after a new message has
        arrived (string, string)
    @signal getParticipants() emitted after a get participants message has
        arrived
    @signal participants(participants) emitted after the list of participants
        has arrived (list of strings of "host:port")
    @signal editorCommand(hash, fn, message) emitted after an editor command
        has arrived (string, string, string)
    @signal rejected(message) emitted after a connection has been rejected
        (string)
    """

    WaitingForGreeting = 0
    ReadingGreeting = 1
    ReadyForUse = 2

    PlainText = 0
    Ping = 1
    Pong = 2
    Greeting = 3
    GetParticipants = 4
    Participants = 5
    Editor = 6
    Undefined = 99

    ProtocolMessage = "MESSAGE"
    ProtocolPing = "PING"
    ProtocolPong = "PONG"
    ProtocolGreeting = "GREETING"
    ProtocolGetParticipants = "GET_PARTICIPANTS"
    ProtocolParticipants = "PARTICIPANTS"
    ProtocolEditor = "EDITOR"

    readyForUse = pyqtSignal()
    newMessage = pyqtSignal(str, str)
    getParticipants = pyqtSignal()
    participants = pyqtSignal(list)
    editorCommand = pyqtSignal(str, str, str)
    rejected = pyqtSignal(str)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent referenec to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__greetingMessage = self.tr("undefined")
        self.__username = self.tr("unknown")
        self.__serverPort = 0
        self.__state = Connection.WaitingForGreeting
        self.__currentDataType = Connection.Undefined
        self.__numBytesForCurrentDataType = -1
        self.__transferTimerId = 0
        self.__isGreetingMessageSent = False
        self.__pingTimer = QTimer(self)
        self.__pingTimer.setInterval(PingInterval)
        self.__pongTime = QTime()
        self.__buffer = QByteArray()
        self.__client = None

        self.readyRead.connect(self.__processReadyRead)
        self.disconnected.connect(self.__disconnected)
        self.__pingTimer.timeout.connect(self.__sendPing)
        self.connected.connect(self.__sendGreetingMessage)

    def name(self):
        """
        Public method to get the connection name.

        @return connection name
        @rtype str
        """
        return self.__username

    def serverPort(self):
        """
        Public method to get the server port.

        @return server port
        @rtype int
        """
        return self.__serverPort

    def setClient(self, client):
        """
        Public method to set the reference to the cooperation client.

        @param client reference to the cooperation client
        @type CooperationClient
        """
        self.__client = client

    def setGreetingMessage(self, message, serverPort):
        """
        Public method to set the greeting message.

        @param message greeting message
        @type str
        @param serverPort port number to include in the message
        @type int
        """
        self.__greetingMessage = "{0}:{1}".format(message, serverPort)

    def sendMessage(self, message):
        """
        Public method to send a message.

        @param message message to be sent
        @type str
        @return flag indicating a successful send
        @rtype bool
        """
        if message == "":
            return False

        msg = QByteArray(message.encode("utf-8"))
        data = (
            QByteArray(
                "{0}{1}{2}{1}".format(
                    Connection.ProtocolMessage, SeparatorToken, msg.size()
                ).encode("utf-8")
            )
            + msg
        )
        return self.write(data) == data.size()

    def timerEvent(self, evt):
        """
        Protected method to handle timer events.

        @param evt reference to the timer event
        @type QTimerEvent
        """
        if evt.timerId() == self.__transferTimerId:
            self.abort()
            self.killTimer(self.__transferTimerId)
            self.__transferTimerId = 0

    def __processReadyRead(self):
        """
        Private slot to handle the readyRead signal.
        """
        if self.__state == Connection.WaitingForGreeting:
            if not self.__readProtocolHeader():
                return
            if self.__currentDataType != Connection.Greeting:
                self.abort()
                return
            self.__state = Connection.ReadingGreeting

        if self.__state == Connection.ReadingGreeting:
            if not self.__hasEnoughData():
                return

            self.__buffer = QByteArray(self.read(self.__numBytesForCurrentDataType))
            if self.__buffer.size() != self.__numBytesForCurrentDataType:
                self.abort()
                return

            try:
                user, serverPort = str(self.__buffer, encoding="utf-8").split(":")
            except ValueError:
                self.abort()
                return
            self.__serverPort = int(serverPort)

            hostInfo = QHostInfo.fromName(self.peerAddress().toString())
            self.__username = "{0}@{1}@{2}".format(
                user, hostInfo.hostName(), self.peerPort()
            )
            self.__currentDataType = Connection.Undefined
            self.__numBytesForCurrentDataType = 0
            self.__buffer.clear()

            if not self.isValid():
                self.abort()
                return

            bannedName = "{0}@{1}".format(
                user,
                hostInfo.hostName(),
            )
            Preferences.syncPreferences()
            if bannedName in Preferences.getCooperation("BannedUsers"):
                self.rejected.emit(
                    self.tr("* Connection attempted by banned user '{0}'.").format(
                        bannedName
                    )
                )
                self.abort()
                return

            if self.__serverPort != self.peerPort() and not Preferences.getCooperation(
                "AutoAcceptConnections"
            ):
                # don't ask for reverse connections or
                # if we shall accept automatically
                res = EricMessageBox.yesNo(
                    None,
                    self.tr("New Connection"),
                    self.tr(
                        """<p>Accept connection from """
                        """<strong>{0}@{1}</strong>?</p>"""
                    ).format(user, hostInfo.hostName()),
                    yesDefault=True,
                )
                if not res:
                    self.abort()
                    return

            if self.__client is not None:
                chatWidget = self.__client.chatWidget()
                if chatWidget is not None and not chatWidget.isVisible():
                    ericApp().getObject("UserInterface").activateCooperationViewer()

            if not self.__isGreetingMessageSent:
                self.__sendGreetingMessage()

            self.__pingTimer.start()
            self.__pongTime = QTime.currentTime()
            self.__state = Connection.ReadyForUse
            self.readyForUse.emit()

        while self.bytesAvailable():
            if (
                self.__currentDataType == Connection.Undefined
                and not self.__readProtocolHeader()
            ):
                return

            if not self.__hasEnoughData():
                return

            self.__processData()

    def __sendPing(self):
        """
        Private slot to send a ping message.
        """
        if self.__pongTime.msecsTo(QTime.currentTime()) > PongTimeout:
            self.abort()
            return

        self.write(
            QByteArray(
                "{0}{1}1{1}p".format(Connection.ProtocolPing, SeparatorToken).encode(
                    "utf-8"
                )
            )
        )

    def __sendGreetingMessage(self):
        """
        Private slot to send a greeting message.
        """
        greeting = QByteArray(self.__greetingMessage.encode("utf-8"))
        data = (
            QByteArray(
                "{0}{1}{2}{1}".format(
                    Connection.ProtocolGreeting, SeparatorToken, greeting.size()
                ).encode("utf-8")
            )
            + greeting
        )
        if self.write(data) == data.size():
            self.__isGreetingMessageSent = True

    def __readDataIntoBuffer(self, maxSize=MaxBufferSize):
        """
        Private method to read some data into the buffer.

        @param maxSize maximum size of data to read
        @type int
        @return size of data read
        @rtype int
        """
        if maxSize > MaxBufferSize:
            return 0

        numBytesBeforeRead = self.__buffer.size()
        if numBytesBeforeRead == MaxBufferSize:
            self.abort()
            return 0

        while self.bytesAvailable() and self.__buffer.size() < maxSize:
            self.__buffer.append(self.read(1))
            if self.__buffer.endsWith(SeparatorToken_b):
                break

        return self.__buffer.size() - numBytesBeforeRead

    def __dataLengthForCurrentDataType(self):
        """
        Private method to get the data length for the current data type.

        @return data length
        @rtype int
        """
        if (
            self.bytesAvailable() <= 0
            or self.__readDataIntoBuffer() <= 0
            or not self.__buffer.endsWith(SeparatorToken_b)
        ):
            return 0

        self.__buffer.chop(len(SeparatorToken_b))
        number = self.__buffer.toInt()[0]
        self.__buffer.clear()
        return number

    def __readProtocolHeader(self):
        """
        Private method to read the protocol header.

        @return flag indicating a successful read
        @rtype bool
        """
        if self.__transferTimerId:
            self.killTimer(self.__transferTimerId)
            self.__transferTimerId = 0

        if self.__readDataIntoBuffer() <= 0:
            self.__transferTimerId = self.startTimer(TransferTimeout)
            return False

        self.__buffer.chop(len(SeparatorToken))
        protocolHeader = str(self.__buffer, encoding="utf-8")
        if protocolHeader == Connection.ProtocolPing:
            self.__currentDataType = Connection.Ping
        elif protocolHeader == Connection.ProtocolPong:
            self.__currentDataType = Connection.Pong
        elif protocolHeader == Connection.ProtocolMessage:
            self.__currentDataType = Connection.PlainText
        elif protocolHeader == Connection.ProtocolGreeting:
            self.__currentDataType = Connection.Greeting
        elif protocolHeader == Connection.ProtocolGetParticipants:
            self.__currentDataType = Connection.GetParticipants
        elif protocolHeader == Connection.ProtocolParticipants:
            self.__currentDataType = Connection.Participants
        elif protocolHeader == Connection.ProtocolEditor:
            self.__currentDataType = Connection.Editor
        else:
            self.__currentDataType = Connection.Undefined
            self.abort()
            return False

        self.__buffer.clear()
        self.__numBytesForCurrentDataType = self.__dataLengthForCurrentDataType()
        return True

    def __hasEnoughData(self):
        """
        Private method to check, if enough data is available.

        @return flag indicating availability of enough data
        @rtype bool
        """
        if self.__transferTimerId:
            self.killTimer(self.__transferTimerId)
            self.__transferTimerId = 0

        if self.__numBytesForCurrentDataType <= 0:
            self.__numBytesForCurrentDataType = self.__dataLengthForCurrentDataType()

        if (
            self.bytesAvailable() < self.__numBytesForCurrentDataType
            or self.__numBytesForCurrentDataType <= 0
        ):
            self.__transferTimerId = self.startTimer(TransferTimeout)
            return False

        return True

    def __processData(self):
        """
        Private method to process the received data.
        """
        self.__buffer = QByteArray(self.read(self.__numBytesForCurrentDataType))
        if self.__buffer.size() != self.__numBytesForCurrentDataType:
            self.abort()
            return

        if self.__currentDataType == Connection.PlainText:
            self.newMessage.emit(self.__username, str(self.__buffer, encoding="utf-8"))
        elif self.__currentDataType == Connection.Ping:
            self.write(
                QByteArray(
                    "{0}{1}1{1}p".format(
                        Connection.ProtocolPong, SeparatorToken
                    ).encode("utf-8")
                )
            )
        elif self.__currentDataType == Connection.Pong:
            self.__pongTime = QTime.currentTime()
        elif self.__currentDataType == Connection.GetParticipants:
            self.getParticipants.emit()
        elif self.__currentDataType == Connection.Participants:
            msg = str(self.__buffer, encoding="utf-8")
            if msg == "<empty>":
                participantsList = []
            else:
                participantsList = msg.split(SeparatorToken)
            self.participants.emit(participantsList[:])
        elif self.__currentDataType == Connection.Editor:
            hashStr, fn, msg = str(self.__buffer, encoding="utf-8").split(
                SeparatorToken
            )
            self.editorCommand.emit(hashStr, fn, msg)

        self.__currentDataType = Connection.Undefined
        self.__numBytesForCurrentDataType = 0
        self.__buffer.clear()

    def sendGetParticipants(self):
        """
        Public method to request a list of participants.
        """
        self.write(
            QByteArray(
                "{0}{1}1{1}l".format(
                    Connection.ProtocolGetParticipants, SeparatorToken
                ).encode("utf-8")
            )
        )

    def sendParticipants(self, participants):
        """
        Public method to send the list of participants.

        @param participants list of participants (list of "host:port" strings)
        @type list of str
        """
        message = SeparatorToken.join(participants) if participants else "<empty>"
        msg = QByteArray(message.encode("utf-8"))
        data = (
            QByteArray(
                "{0}{1}{2}{1}".format(
                    Connection.ProtocolParticipants, SeparatorToken, msg.size()
                ).encode("utf-8")
            )
            + msg
        )
        self.write(data)

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
        msg = QByteArray(
            "{0}{1}{2}{1}{3}".format(
                projectHash, SeparatorToken, filename, message
            ).encode("utf-8")
        )
        data = (
            QByteArray(
                "{0}{1}{2}{1}".format(
                    Connection.ProtocolEditor, SeparatorToken, msg.size()
                ).encode("utf-8")
            )
            + msg
        )
        self.write(data)

    def __disconnected(self):
        """
        Private slot to handle the connection being dropped.
        """
        self.__pingTimer.stop()
        if self.__state == Connection.WaitingForGreeting:
            self.rejected.emit(
                self.tr("* Connection to {0}:{1} refused.").format(
                    self.peerName(), self.peerPort()
                )
            )
