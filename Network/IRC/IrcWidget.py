# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the IRC window.
"""

import enum
import logging
import re

from PyQt6.QtCore import QByteArray, QDateTime, Qt, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtNetwork import QAbstractSocket, QTcpSocket
from PyQt6.QtWidgets import QLabel, QTabWidget, QToolButton, QWidget

try:
    from PyQt6.QtNetwork import QSslConfiguration, QSslSocket

    from eric7.EricNetwork.EricSslErrorHandler import (
        EricSslErrorHandler,
        EricSslErrorState,
    )

    SSL_AVAILABLE = True
except ImportError:
    SSL_AVAILABLE = False

from eric7 import Preferences
from eric7.__version__ import Version
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox
from eric7.SystemUtilities import OSUtilities
from eric7.UI.Info import Copyright

from .IrcNetworkManager import IrcNetworkManager
from .Ui_IrcWidget import Ui_IrcWidget


class IrcConnectionState(enum.Enum):
    """
    Class defining the connection states.
    """

    Disconnected = 1
    Connected = 2
    Connecting = 3


class IrcWidget(QWidget, Ui_IrcWidget):
    """
    Class implementing the IRC window.

    @signal autoConnected() emitted after an automatic connection was initiated
    """

    autoConnected = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__ircNetworkManager = IrcNetworkManager(self)

        self.__leaveButton = QToolButton(self)
        self.__leaveButton.setIcon(EricPixmapCache.getIcon("ircCloseChannel"))
        self.__leaveButton.setToolTip(self.tr("Press to leave the current channel"))
        self.__leaveButton.clicked.connect(self.__leaveChannel)
        self.__leaveButton.setEnabled(False)
        self.channelsWidget.setCornerWidget(
            self.__leaveButton, Qt.Corner.BottomRightCorner
        )
        self.channelsWidget.setTabsClosable(False)
        if not OSUtilities.isMacPlatform():
            self.channelsWidget.setTabPosition(QTabWidget.TabPosition.South)

        height = self.height()
        self.splitter.setSizes([int(height * 0.6), int(height * 0.4)])

        self.__channelList = []
        self.__channelTypePrefixes = ""
        self.__userName = ""
        self.__identityName = ""
        self.__quitMessage = ""
        self.__nickIndex = -1
        self.__nickName = ""
        self.__server = None
        self.__registering = False

        self.__connectionState = IrcConnectionState.Disconnected
        self.__sslErrorLock = False

        self.__buffer = ""
        self.__userPrefix = {}

        self.__socket = None
        if SSL_AVAILABLE:
            self.__sslErrorHandler = EricSslErrorHandler(
                Preferences.getSettings(), self
            )
        else:
            self.__sslErrorHandler = None

        self.__patterns = [
            # :foo_!n=foo@foohost.bar.net PRIVMSG bar_ :some long message
            (re.compile(r":([^!]+)!([^ ]+)\sPRIVMSG\s([^ ]+)\s:(.*)"), self.__query),
            # :foo.bar.net COMMAND some message
            (re.compile(r""":([^ ]+)\s+([A-Z]+)\s+(.+)"""), self.__handleNamedMessage),
            # :foo.bar.net 123 * :info
            (re.compile(r""":([^ ]+)\s+(\d{3})\s+(.+)"""), self.__handleNumericMessage),
            # PING :ping message
            (re.compile(r"""PING\s+:(.*)"""), self.__ping),
        ]
        self.__prefixRe = re.compile(r""".*\sPREFIX=\((.*)\)([^ ]+).*""")
        self.__chanTypesRe = re.compile(r""".*\sCHANTYPES=([^ ]+).*""")

        ircPic = EricPixmapCache.getPixmap("irc128")
        self.__emptyLabel = QLabel()
        self.__emptyLabel.setPixmap(ircPic)
        self.__emptyLabel.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
        )
        self.channelsWidget.addTab(self.__emptyLabel, "")

        # all initialized, do connections now
        self.__ircNetworkManager.dataChanged.connect(self.__networkDataChanged)
        self.networkWidget.initialize(self.__ircNetworkManager)
        self.networkWidget.connectNetwork.connect(self.__connectNetwork)
        self.networkWidget.editNetwork.connect(self.__editNetwork)
        self.networkWidget.joinChannel.connect(self.joinChannel)
        self.networkWidget.nickChanged.connect(self.__changeNick)
        self.networkWidget.sendData.connect(self.__send)
        self.networkWidget.away.connect(self.__away)
        self.networkWidget.autoConnected.connect(self.autoConnected)

    def shutdown(self):
        """
        Public method to shut down the widget.

        @return flag indicating successful shutdown
        @rtype bool
        """
        if self.__server:
            if Preferences.getIrc("AskOnShutdown"):
                ok = EricMessageBox.yesNo(
                    self,
                    self.tr("Disconnect from Server"),
                    self.tr(
                        """<p>Do you really want to disconnect from"""
                        """ <b>{0}</b>?</p><p>All channels will be closed."""
                        """</p>"""
                    ).format(self.__server.getName()),
                )
            else:
                ok = True
            if ok:
                self.__connectNetwork("", False, True)
        else:
            ok = True

        if ok:
            self.__ircNetworkManager.close()

        return ok

    def autoConnect(self):
        """
        Public method to initiate the IRC auto connection.
        """
        self.networkWidget.autoConnect()

    def __connectNetwork(self, name, connect, silent):
        """
        Private slot to connect to or disconnect from the given network.

        @param name name of the network to connect to
        @type str
        @param connect flag indicating to connect
        @type bool
        @param silent flag indicating a silent connect/disconnect
        @type bool
        """
        if connect:
            network = self.__ircNetworkManager.getNetwork(name)
            if network:
                self.__server = network.getServer()
                self.__identityName = network.getIdentityName()
                identity = self.__ircNetworkManager.getIdentity(self.__identityName)
                if identity:
                    self.__userName = identity.getIdent()
                    self.__quitMessage = identity.getQuitMessage()
                    if self.__server:
                        useSSL = self.__server.useSSL()
                        if useSSL and not SSL_AVAILABLE:
                            EricMessageBox.critical(
                                self,
                                self.tr("SSL Connection"),
                                self.tr(
                                    """An encrypted connection to the IRC"""
                                    """ network was requested but SSL is not"""
                                    """ available. Please change the server"""
                                    """ configuration."""
                                ),
                            )
                            return

                        if useSSL:
                            # create SSL socket
                            self.__socket = QSslSocket(self)
                            self.__socket.encrypted.connect(self.__hostConnected)
                            self.__socket.sslErrors.connect(self.__sslErrors)
                        else:
                            # create TCP socket
                            self.__socket = QTcpSocket(self)
                            self.__socket.connected.connect(self.__hostConnected)
                        self.__socket.hostFound.connect(self.__hostFound)
                        self.__socket.disconnected.connect(self.__hostDisconnected)
                        self.__socket.readyRead.connect(self.__readyRead)
                        self.__socket.errorOccurred.connect(self.__tcpError)

                        self.__connectionState = IrcConnectionState.Connecting
                        if useSSL:
                            self.networkWidget.addServerMessage(
                                self.tr("Info"),
                                self.tr(
                                    "Looking for server {0} (port {1})"
                                    " using an SSL encrypted connection"
                                    "..."
                                ).format(
                                    self.__server.getName(), self.__server.getPort()
                                ),
                            )
                            self.__socket.connectToHostEncrypted(
                                self.__server.getName(), self.__server.getPort()
                            )
                        else:
                            self.networkWidget.addServerMessage(
                                self.tr("Info"),
                                self.tr("Looking for server {0} (port {1})...").format(
                                    self.__server.getName(), self.__server.getPort()
                                ),
                            )
                            self.__socket.connectToHost(
                                self.__server.getName(), self.__server.getPort()
                            )
        else:
            if silent:
                ok = True
            else:
                ok = EricMessageBox.yesNo(
                    self,
                    self.tr("Disconnect from Server"),
                    self.tr(
                        """<p>Do you really want to disconnect from"""
                        """ <b>{0}</b>?</p><p>All channels will be"""
                        """ closed.</p>"""
                    ).format(self.__server.getName()),
                )
            if ok:
                if self.__server is not None:
                    self.networkWidget.addServerMessage(
                        self.tr("Info"),
                        self.tr("Disconnecting from server {0}...").format(
                            self.__server.getName()
                        ),
                    )
                elif name:
                    self.networkWidget.addServerMessage(
                        self.tr("Info"),
                        self.tr("Disconnecting from network {0}...").format(name),
                    )
                else:
                    self.networkWidget.addServerMessage(
                        self.tr("Info"), self.tr("Disconnecting from server.")
                    )
                self.__closeAllChannels()
                self.__send("QUIT :" + self.__quitMessage)
                if self.__socket:
                    self.__socket.flush()
                    self.__socket.close()
                    if self.__socket:
                        # socket is still existing
                        self.__socket.deleteLater()
                        self.__socket = None
                self.__userName = ""
                self.__identityName = ""
                self.__quitMessage = ""

    @pyqtSlot()
    def __editNetwork(self):
        """
        Private slot to edit the network configuration.
        """
        from .IrcNetworkListDialog import IrcNetworkListDialog

        dlg = IrcNetworkListDialog(self.__ircNetworkManager, parent=self)
        dlg.exec()

    def __networkDataChanged(self):
        """
        Private slot handling changes of the network and identity definitions.
        """
        identity = self.__ircNetworkManager.getIdentity(self.__identityName)
        if identity:
            partMsg = identity.getPartMessage()
            for channel in self.__channelList:
                channel.setPartMessage(partMsg)

    def joinChannel(self, name, key=""):
        """
        Public slot to join a channel.

        @param name name of the channel
        @type str
        @param key key of the channel
        @type str
        """
        from .IrcChannelWidget import IrcChannelWidget

        # step 1: check, if this channel is already joined
        for channel in self.__channelList:
            if channel.name() == name:
                return

        channel = IrcChannelWidget(self)
        channel.setName(name)
        channel.setUserName(self.__nickName)
        identity = self.__ircNetworkManager.getIdentity(self.__identityName)
        if identity:
            channel.setPartMessage(identity.getPartMessage())
        channel.setUserPrivilegePrefix(self.__userPrefix)
        channel.initAutoWho()

        channel.sendData.connect(self.__send)
        channel.sendCtcpRequest.connect(self.__sendCtcpRequest)
        channel.sendCtcpReply.connect(self.__sendCtcpReply)
        channel.channelClosed.connect(self.__closeChannel)
        channel.openPrivateChat.connect(self.__openPrivate)
        channel.awayCommand.connect(self.networkWidget.handleAwayCommand)
        channel.leaveChannels.connect(self.__leaveChannels)
        channel.leaveAllChannels.connect(self.__leaveAllChannels)

        self.channelsWidget.addTab(channel, name)
        self.__channelList.append(channel)
        self.channelsWidget.setCurrentWidget(channel)

        joinCommand = ["JOIN", name]
        if key:
            joinCommand.append(key)
        self.__send(" ".join(joinCommand))
        self.__send("MODE " + name)

        emptyIndex = self.channelsWidget.indexOf(self.__emptyLabel)
        if emptyIndex > -1:
            self.channelsWidget.removeTab(emptyIndex)
            self.__leaveButton.setEnabled(True)
        self.channelsWidget.setTabsClosable(True)

    def __query(self, match):
        """
        Private method to handle a new private connection.

        @param match reference to the match object
        @type re.Match
        @return flag indicating, if the message was handled
        @rtype bool
        """
        # group(1)   sender user name
        # group(2)   sender user@host
        # group(3)   target nick
        # group(4)   message
        if match.group(4).startswith("\x01"):
            return self.__handleCtcp(match)

        self.__openPrivate(match.group(1))
        # the above call sets the new channel as the current widget
        channel = self.channelsWidget.currentWidget()
        channel.addMessage(match.group(1), match.group(4))
        channel.setPrivateInfo("{0} - {1}".format(match.group(1), match.group(2)))

        return True

    @pyqtSlot(str)
    def __openPrivate(self, name):
        """
        Private slot to open a private chat with the given user.

        @param name name of the user
        @type str
        """
        from .IrcChannelWidget import IrcChannelWidget

        channel = IrcChannelWidget(self)
        channel.setName(self.__nickName)
        channel.setUserName(self.__nickName)
        identity = self.__ircNetworkManager.getIdentity(self.__identityName)
        if identity:
            channel.setPartMessage(identity.getPartMessage())
        channel.setUserPrivilegePrefix(self.__userPrefix)
        channel.setPrivate(True, name)
        channel.addUsers([name, self.__nickName])

        channel.sendData.connect(self.__send)
        channel.sendCtcpRequest.connect(self.__sendCtcpRequest)
        channel.sendCtcpReply.connect(self.__sendCtcpReply)
        channel.channelClosed.connect(self.__closeChannel)
        channel.awayCommand.connect(self.networkWidget.handleAwayCommand)
        channel.leaveChannels.connect(self.__leaveChannels)
        channel.leaveAllChannels.connect(self.__leaveAllChannels)

        self.channelsWidget.addTab(channel, name)
        self.__channelList.append(channel)
        self.channelsWidget.setCurrentWidget(channel)

    @pyqtSlot()
    def __leaveChannel(self):
        """
        Private slot to leave a channel and close the associated tab.
        """
        channel = self.channelsWidget.currentWidget()
        channel.requestLeave()

    @pyqtSlot(list)
    def __leaveChannels(self, channelNames):
        """
        Private slot to leave a list of channels and close their associated
        tabs.

        @param channelNames list of channels to leave
        @type list of str
        """
        for channelName in channelNames:
            for channel in self.__channelList:
                if channel.name() == channelName:
                    channel.leaveChannel()

    @pyqtSlot()
    def __leaveAllChannels(self):
        """
        Private slot to leave all channels and close their tabs.
        """
        while self.__channelList:
            channel = self.__channelList[0]
            channel.leaveChannel()

    def __closeAllChannels(self):
        """
        Private method to close all channels.
        """
        while self.__channelList:
            channel = self.__channelList.pop()
            self.channelsWidget.removeTab(self.channelsWidget.indexOf(channel))
            channel.deleteLater()
            channel = None

        self.channelsWidget.addTab(self.__emptyLabel, "")
        self.__emptyLabel.show()
        self.__leaveButton.setEnabled(False)
        self.channelsWidget.setTabsClosable(False)

    def __closeChannel(self, name):
        """
        Private slot handling the closing of a channel.

        @param name name of the closed channel
        @type str
        """
        for channel in self.__channelList[:]:
            if channel.name() == name:
                self.channelsWidget.removeTab(self.channelsWidget.indexOf(channel))
                self.__channelList.remove(channel)
                channel.deleteLater()

        if self.channelsWidget.count() == 0:
            self.channelsWidget.addTab(self.__emptyLabel, "")
            self.__emptyLabel.show()
            self.__leaveButton.setEnabled(False)
            self.channelsWidget.setTabsClosable(False)

    @pyqtSlot(int)
    def on_channelsWidget_tabCloseRequested(self, index):
        """
        Private slot to close a channel by pressing the close button of
        the channels widget.

        @param index index of the tab to be closed
        @type int
        """
        channel = self.channelsWidget.widget(index)
        channel.requestLeave()

    def __send(self, data):
        """
        Private slot to send data to the IRC server.

        @param data data to be sent
        @type str
        """
        if self.__socket:
            self.__socket.write(QByteArray("{0}\r\n".format(data).encode("utf-8")))

    def __sendCtcpRequest(self, receiver, request, arguments):
        """
        Private slot to send a CTCP request.

        @param receiver nick name of the receiver
        @type str
        @param request CTCP request to be sent
        @type str
        @param arguments arguments to be sent
        @type str
        """
        request = request.upper()
        if request == "PING":
            arguments = "Eric IRC {0}".format(QDateTime.currentMSecsSinceEpoch())

        self.__send("PRIVMSG {0} :\x01{1} {2}\x01".format(receiver, request, arguments))

    def __sendCtcpReply(self, receiver, text):
        """
        Private slot to send a CTCP reply.

        @param receiver nick name of the receiver
        @type str
        @param text text to be sent
        @type str
        """
        self.__send("NOTICE {0} :\x01{1}\x01".format(receiver, text))

    def __hostFound(self):
        """
        Private slot to indicate the host was found.
        """
        self.networkWidget.addServerMessage(
            self.tr("Info"), self.tr("Server found,connecting...")
        )

    def __hostConnected(self):
        """
        Private slot to log in to the server after the connection was
        established.
        """
        self.networkWidget.addServerMessage(
            self.tr("Info"), self.tr("Connected,logging in...")
        )
        self.networkWidget.setConnected(True)

        self.__registering = True
        serverPassword = self.__server.getPassword()
        if serverPassword:
            self.__send("PASS " + serverPassword)

        identity = self.__ircNetworkManager.getIdentity(self.__identityName)
        nick = self.networkWidget.getNickname()
        if not nick and identity:
            self.__nickIndex = 0
            try:
                nick = identity.getNickNames()[self.__nickIndex]
            except IndexError:
                nick = ""
        if not nick:
            nick = self.__userName
        self.__nickName = nick
        self.networkWidget.setNickName(nick)
        if identity:
            realName = identity.getRealName()
            if not realName:
                realName = "eric IDE chat"
            self.__send("NICK " + nick)
            self.__send("USER " + self.__userName + " 0 * :" + realName)

    def __hostDisconnected(self):
        """
        Private slot to indicate the host was disconnected.
        """
        if self.networkWidget.isConnected():
            self.__closeAllChannels()
            self.networkWidget.addServerMessage(
                self.tr("Info"), self.tr("Server disconnected.")
            )
            self.networkWidget.setRegistered(False)
            self.networkWidget.setConnected(False)
            self.__server = None
            self.__nickName = ""
            self.__nickIndex = -1
            self.__channelTypePrefixes = ""

            if self.__socket:
                self.__socket.deleteLater()
            self.__socket = None

            self.__connectionState = IrcConnectionState.Disconnected
            self.__sslErrorLock = False

    def __readyRead(self):
        """
        Private slot to read data from the socket.
        """
        if self.__socket:
            self.__buffer += str(
                self.__socket.readAll(), Preferences.getSystem("IOEncoding"), "replace"
            )
            if self.__buffer.endswith("\r\n"):
                for line in self.__buffer.splitlines():
                    line = line.strip()
                    if line:
                        logging.getLogger(__name__).debug("<IRC> %s", line)
                        handled = False
                        # step 1: give channels a chance to handle the message
                        for channel in self.__channelList:
                            handled = channel.handleMessage(line)
                            if handled:
                                break
                        else:
                            # step 2: try to process the message ourselves
                            for patternRe, patternFunc in self.__patterns:
                                match = patternRe.match(line)
                                if match is not None and patternFunc(match):
                                    break
                            else:
                                # Oops, the message wasn't handled
                                self.networkWidget.addErrorMessage(
                                    self.tr("Message Error"),
                                    self.tr(
                                        "Unknown message received from server:"
                                        "<br/>{0}"
                                    ).format(line),
                                )

                self.__updateUsersCount()
                self.__buffer = ""

    def __handleCtcpReply(self, match):
        """
        Private method to handle a server message containing a CTCP reply.

        @param match reference to the match object
        @type re.Match
        """
        if "!" in match.group(1):
            sender = match.group(1).split("!", 1)[0]

            try:
                ctcpCommand = match.group(3).split(":", 1)[1]
            except IndexError:
                ctcpCommand = match.group(3)
            ctcpCommand = ctcpCommand[1:].split("\x01", 1)[0]
            if " " in ctcpCommand:
                ctcpReply, ctcpArg = ctcpCommand.split(" ", 1)
            else:
                ctcpReply, ctcpArg = ctcpCommand, ""
            ctcpReply = ctcpReply.upper()

            if ctcpReply == "PING" and ctcpArg.startswith("Eric IRC "):
                # it is a response to a ping request
                pingDateTime = int(ctcpArg.split()[-1])
                latency = QDateTime.currentMSecsSinceEpoch() - pingDateTime
                self.networkWidget.addServerMessage(
                    self.tr("CTCP"),
                    self.tr(
                        "Received CTCP-PING response from {0} with latency"
                        " of {1} ms."
                    ).format(sender, latency),
                )
            else:
                self.networkWidget.addServerMessage(
                    self.tr("CTCP"),
                    self.tr("Received unknown CTCP-{0} response from {1}.").format(
                        ctcpReply, sender
                    ),
                )

    def __handleNamedMessage(self, match):
        """
        Private method to handle a server message containing a message name.

        @param match reference to the match object
        @type re.Match
        @return flag indicating, if the message was handled
        @rtype bool
        """
        name = match.group(2)
        if name == "NOTICE":
            try:
                msg = match.group(3).split(":", 1)[1]
            except IndexError:
                msg = match.group(3)

            if msg.startswith("\x01"):
                self.__handleCtcpReply(match)
                return True

            if "!" in match.group(1):
                name = match.group(1).split("!", 1)[0]
                msg = "-{0}- {1}".format(name, msg)
            self.networkWidget.addServerMessage(self.tr("Notice"), msg)
            return True
        elif name == "MODE":
            self.__registering = False
            if ":" in match.group(3):
                # :foo MODE foo :+i
                name, modes = match.group(3).split(" :")
                sourceNick = match.group(1)
                if not self.isChannelName(name) and name == self.__nickName:
                    if sourceNick == self.__nickName:
                        msg = self.tr(
                            "You have set your personal modes to <b>[{0}]</b>."
                        ).format(modes)
                    else:
                        msg = self.tr(
                            "{0} has changed your personal modes to <b>[{1}]</b>."
                        ).format(sourceNick, modes)
                    self.networkWidget.addServerMessage(
                        self.tr("Mode"), msg, filterMsg=False
                    )
                    return True
        elif name == "PART":
            nick = match.group(1).split("!", 1)[0]
            if nick == self.__nickName:
                channel = match.group(3).split(None, 1)[0]
                self.networkWidget.addMessage(
                    self.tr("You have left channel {0}.").format(channel)
                )
                return True
        elif name == "QUIT":
            # don't do anything with it here
            return True
        elif name == "NICK":
            # :foo_!n=foo@foohost.bar.net NICK :newnick
            oldNick = match.group(1).split("!", 1)[0]
            newNick = match.group(3).split(":", 1)[1]
            if oldNick == self.__nickName:
                self.networkWidget.addMessage(
                    self.tr("You are now known as {0}.").format(newNick)
                )
                self.__nickName = newNick
                self.networkWidget.setNickName(newNick)
            else:
                self.networkWidget.addMessage(
                    self.tr("User {0} is now known as {1}.").format(oldNick, newNick)
                )
            return True
        elif name == "PONG":
            nick = match.group(3).split(":", 1)[1]
            self.networkWidget.addMessage(
                self.tr("Received PONG from {0}").format(nick)
            )
            return True
        elif name == "ERROR":
            self.networkWidget.addErrorMessage(
                self.tr("Server Error"), match.group(3).split(":", 1)[1]
            )
            return True

        return False

    def __handleNumericMessage(self, match):
        """
        Private method to handle a server message containing a numeric code.

        @param match reference to the match object
        @type re.Match
        @return flag indicating, if the message was handled
        @rtype bool
        """
        code = int(match.group(2))
        if code < 400:
            return self.__handleServerReply(code, match.group(1), match.group(3))
        else:
            return self.__handleServerError(code, match.group(3))

    def __handleServerError(self, code, message):
        """
        Private slot to handle a server error reply.

        @param code numerical code sent by the server
        @type int
        @param message message sent by the server
        @type str
        @return flag indicating, if the message was handled
        @rtype bool
        """
        if code == 433:
            if self.__registering:
                self.__handleNickInUseLogin()
            else:
                self.__handleNickInUse()
        else:
            self.networkWidget.addServerMessage(self.tr("Error"), message)

        return True

    def __handleServerReply(self, code, server, message):
        """
        Private slot to handle a server reply.

        @param code numerical code sent by the server
        @type int
        @param server name of the server
        @type str
        @param message message sent by the server
        @type str
        @return flag indicating, if the message was handled
        @rtype bool
        """
        # determine message type
        if code in [1, 2, 3, 4]:
            msgType = self.tr("Welcome")
        elif code == 5:
            msgType = self.tr("Support")
        elif code in [250, 251, 252, 253, 254, 255, 265, 266]:
            msgType = self.tr("User")
        elif code in [372, 375, 376]:
            msgType = self.tr("MOTD")
        elif code in [305, 306]:
            msgType = self.tr("Away")
        else:
            msgType = self.tr("Info ({0})").format(code)

        # special treatment for some messages
        if code == 375:
            message = self.tr("Message of the day")
        elif code == 376:
            message = self.tr("End of message of the day")
        elif code == 4:
            parts = message.strip().split()
            message = self.tr(
                "Server {0} (Version {1}), User-Modes: {2}, Channel-Modes: {3}"
            ).format(parts[1], parts[2], parts[3], parts[4])
        elif code == 265:
            parts = message.strip().split()
            message = self.tr("Current users on {0}: {1}, max. {2}").format(
                server, parts[1], parts[2]
            )
        elif code == 266:
            parts = message.strip().split()
            message = self.tr("Current users on the network: {0}, max. {1}").format(
                parts[1], parts[2]
            )
        elif code == 305:
            message = self.tr("You are no longer marked as being away.")
        elif code == 306:
            message = self.tr("You have been marked as being away.")
        else:
            _first, message = message.split(None, 1)
            if message.startswith(":"):
                message = message[1:]
            else:
                message = message.replace(":", "", 1)

        self.networkWidget.addServerMessage(msgType, message)

        if code == 1:
            # register with services after the welcome message
            self.__connectionState = IrcConnectionState.Connected
            self.__registerWithServices()
            self.networkWidget.setRegistered(True)
            QTimer.singleShot(1000, self.__autoJoinChannels)
        elif code == 5:
            # extract the user privilege prefixes
            # ... PREFIX=(ov)@+ ...
            m = self.__prefixRe.match(message)
            if m:
                self.__setUserPrivilegePrefix(m.group(1), m.group(2))
            # extract the channel type prefixes
            # ... CHANTYPES=# ...
            m = self.__chanTypesRe.match(message)
            if m:
                self.__setChannelTypePrefixes(m.group(1))

        return True

    def __registerWithServices(self):
        """
        Private method to register to services.
        """
        identity = self.__ircNetworkManager.getIdentity(self.__identityName)
        if identity:
            service = identity.getServiceName()
            password = identity.getPassword()
            if service and password:
                self.__send("PRIVMSG " + service + " :identify " + password)

    def __autoJoinChannels(self):
        """
        Private slot to join channels automatically once a server got
        connected.
        """
        for channel in self.networkWidget.getNetworkChannels():
            if channel.autoJoin():
                name = channel.getName()
                key = channel.getKey()
                self.joinChannel(name, key)

    def __tcpError(self, error):
        """
        Private slot to handle errors reported by the TCP socket.

        @param error error code reported by the socket
        @type QAbstractSocket.SocketError
        """
        if error == QAbstractSocket.SocketError.RemoteHostClosedError:
            # ignore this one, it's a disconnect
            if self.__sslErrorLock:
                self.networkWidget.addErrorMessage(
                    self.tr("SSL Error"),
                    self.tr(
                        """Connection to server {0} (port {1}) lost while"""
                        """ waiting for user response to an SSL error."""
                    ).format(self.__server.getName(), self.__server.getPort()),
                )
                self.__connectionState = IrcConnectionState.Disconnected
        elif error == QAbstractSocket.SocketError.HostNotFoundError:
            self.networkWidget.addErrorMessage(
                self.tr("Socket Error"),
                self.tr(
                    "The host was not found. Please check the host name"
                    " and port settings."
                ),
            )
        elif error == QAbstractSocket.SocketError.ConnectionRefusedError:
            self.networkWidget.addErrorMessage(
                self.tr("Socket Error"),
                self.tr(
                    "The connection was refused by the peer. Please check the"
                    " host name and port settings."
                ),
            )
        elif error == QAbstractSocket.SocketError.SslHandshakeFailedError:
            self.networkWidget.addErrorMessage(
                self.tr("Socket Error"), self.tr("The SSL handshake failed.")
            )
        else:
            if self.__socket:
                self.networkWidget.addErrorMessage(
                    self.tr("Socket Error"),
                    self.tr("The following network error occurred:<br/>{0}").format(
                        self.__socket.errorString()
                    ),
                )
            else:
                self.networkWidget.addErrorMessage(
                    self.tr("Socket Error"), self.tr("A network error occurred.")
                )

    def __sslErrors(self, errors):
        """
        Private slot to handle SSL errors.

        @param errors list of SSL errors
        @type list of QSslError
        """
        ignored, defaultChanged = self.__sslErrorHandler.sslErrors(
            errors, self.__server.getName(), self.__server.getPort()
        )
        if ignored == EricSslErrorState.NOT_IGNORED:
            self.networkWidget.addErrorMessage(
                self.tr("SSL Error"),
                self.tr(
                    """Could not connect to {0} (port {1}) using an SSL"""
                    """ encrypted connection. Either the server does not"""
                    """ support SSL (did you use the correct port?) or"""
                    """ you rejected the certificate."""
                ).format(self.__server.getName(), self.__server.getPort()),
            )
            self.__socket.close()
        else:
            if defaultChanged:
                self.__socket.setSslConfiguration(
                    QSslConfiguration.defaultConfiguration()
                )
            if ignored == EricSslErrorState.USER_IGNORED:
                self.networkWidget.addErrorMessage(
                    self.tr("SSL Error"),
                    self.tr(
                        """The SSL certificate for the server {0} (port {1})"""
                        """ failed the authenticity check. SSL errors"""
                        """ were accepted by you."""
                    ).format(self.__server.getName(), self.__server.getPort()),
                )
            if self.__connectionState == IrcConnectionState.Connecting:
                self.__socket.ignoreSslErrors()

    def __setUserPrivilegePrefix(self, prefix1, prefix2):
        """
        Private method to set the user privilege prefix.

        @param prefix1 first part of the prefix
        @type str
        @param prefix2 indictors the first part gets mapped to
        @type str
        """
        # PREFIX=(ov)@+
        # o = @ -> @ircbot , channel operator
        # v = + -> +userName , voice operator
        for i in range(len(prefix1)):
            self.__userPrefix["+" + prefix1[i]] = prefix2[i]
            self.__userPrefix["-" + prefix1[i]] = ""

    def __ping(self, match):
        """
        Private method to handle a PING message.

        @param match reference to the match object
        @type re.Match
        @return flag indicating, if the message was handled
        @rtype bool
        """
        self.__send("PONG " + match.group(1))
        return True

    def __handleCtcp(self, match):
        """
        Private method to handle a CTCP command.

        @param match reference to the match object
        @type re.Match
        @return flag indicating, if the message was handled
        @rtype bool
        """
        # group(1)   sender user name
        # group(2)   sender user@host
        # group(3)   target nick
        # group(4)   message
        if match.group(4).startswith("\x01"):
            ctcpCommand = match.group(4)[1:].split("\x01", 1)[0]
            if " " in ctcpCommand:
                ctcpRequest, ctcpArg = ctcpCommand.split(" ", 1)
            else:
                ctcpRequest, ctcpArg = ctcpCommand, ""
            ctcpRequest = ctcpRequest.lower()
            if ctcpRequest == "version":
                if Version.startswith("@@"):
                    vers = ""
                else:
                    vers = " " + Version
                msg = "Eric IRC client{0}, {1}".format(vers, Copyright)
                self.networkWidget.addServerMessage(
                    self.tr("CTCP"),
                    self.tr("Received Version request from {0}.").format(
                        match.group(1)
                    ),
                )
                self.__sendCtcpReply(match.group(1), "VERSION " + msg)
            elif ctcpRequest == "ping":
                self.networkWidget.addServerMessage(
                    self.tr("CTCP"),
                    self.tr(
                        "Received CTCP-PING request from {0}, sending answer."
                    ).format(match.group(1)),
                )
                self.__sendCtcpReply(match.group(1), "PING {0}".format(ctcpArg))
            elif ctcpRequest == "clientinfo":
                self.networkWidget.addServerMessage(
                    self.tr("CTCP"),
                    self.tr(
                        "Received CTCP-CLIENTINFO request from {0}, sending answer."
                    ).format(match.group(1)),
                )
                self.__sendCtcpReply(
                    match.group(1), "CLIENTINFO CLIENTINFO PING VERSION"
                )
            else:
                self.networkWidget.addServerMessage(
                    self.tr("CTCP"),
                    self.tr("Received unknown CTCP-{0} request from {1}.").format(
                        ctcpRequest, match.group(1)
                    ),
                )
            return True

        return False

    def __updateUsersCount(self):
        """
        Private method to update the users count on the channel tabs.
        """
        for channel in self.__channelList:
            index = self.channelsWidget.indexOf(channel)
            self.channelsWidget.setTabText(
                index,
                self.tr("{0} ({1})", "channel name, users count").format(
                    channel.name(), channel.getUsersCount()
                ),
            )

    def __handleNickInUseLogin(self):
        """
        Private method to handle a 443 server error at login.
        """
        self.__nickIndex += 1
        try:
            identity = self.__ircNetworkManager.getIdentity(self.__identityName)
            if identity:
                nick = identity.getNickNames()[self.__nickIndex]
                self.__nickName = nick
            else:
                self.__connectNetwork("", False, True)
                self.__nickName = ""
                self.__nickIndex = -1
                return
        except IndexError:
            self.networkWidget.addServerMessage(
                self.tr("Critical"),
                self.tr(
                    "No nickname acceptable to the server configured"
                    " for <b>{0}</b>. Disconnecting..."
                ).format(self.__userName),
                filterMsg=False,
            )
            self.__connectNetwork("", False, True)
            self.__nickName = ""
            self.__nickIndex = -1
            return

        self.networkWidget.setNickName(nick)
        self.__send("NICK " + nick)

    def __handleNickInUse(self):
        """
        Private method to handle a 443 server error.
        """
        self.networkWidget.addServerMessage(
            self.tr("Critical"), self.tr("The given nickname is already in use.")
        )

    def __changeNick(self, nick):
        """
        Private slot to use a new nick name.

        @param nick nick name to use
        @type str
        """
        if nick and nick != self.__nickName:
            self.__send("NICK " + nick)

    def __setChannelTypePrefixes(self, prefixes):
        """
        Private method to set the channel type prefixes.

        @param prefixes channel prefix characters
        @type str
        """
        self.__channelTypePrefixes = prefixes

    def isChannelName(self, name):
        """
        Public method to check, if the given name is a channel name.

        @param name name to check
        @type str
        @return flag indicating a channel name
        @rtype bool
        """
        if not name:
            return False

        if self.__channelTypePrefixes:
            return name[0] in self.__channelTypePrefixes
        else:
            return name[0] in "#&"

    def __away(self, isAway):
        """
        Private slot handling the change of the away state.

        @param isAway flag indicating the current away state
        @type bool
        """
        if isAway and self.__identityName:
            identity = self.__ircNetworkManager.getIdentity(self.__identityName)
            if identity and identity.rememberAwayPosition():
                for channel in self.__channelList:
                    channel.setMarkerLine()
