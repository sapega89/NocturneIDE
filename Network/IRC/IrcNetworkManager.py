# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the IRC data structures and their manager.
"""

import copy

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

from eric7 import EricUtilities, Preferences
from eric7.EricUtilities.crypto import pwConvert
from eric7.SystemUtilities import OSUtilities
from eric7.Utilities.AutoSaver import AutoSaver


class IrcIdentity:
    """
    Class implementing the IRC identity object.
    """

    DefaultIdentityName = "0default"
    DefaultIdentityDisplay = QCoreApplication.translate(
        "IrcIdentity", "Default Identity"
    )

    DefaultAwayMessage = QCoreApplication.translate("IrcIdentity", "Gone away for now.")
    DefaultQuitMessage = QCoreApplication.translate("IrcIdentity", "IRC for eric IDE")
    DefaultPartMessage = QCoreApplication.translate("IrcIdentity", "IRC for eric IDE")

    def __init__(self, name):
        """
        Constructor

        @param name name of the identity
        @type str
        """
        super().__init__()

        self.__name = name
        self.__realName = ""
        self.__nickNames = []
        self.__serviceName = ""
        self.__password = ""
        self.__ident = OSUtilities.getUserName()

        self.__rememberPosOnAway = True
        self.__awayMessage = IrcIdentity.DefaultAwayMessage

        self.__quitMessage = IrcIdentity.DefaultQuitMessage
        self.__partMessage = IrcIdentity.DefaultPartMessage

    def save(self, settings):
        """
        Public method to save the identity data.

        @param settings reference to the settings object
        @type QSettings
        """
        # no need to save the name because that is the group key
        settings.setValue("Ident", self.__ident)
        settings.setValue("RealName", self.__realName)
        settings.setValue("NickNames", self.__nickNames)
        settings.setValue("ServiceName", self.__serviceName)
        settings.setValue("Password", self.__password)
        settings.setValue("QuitMessage", self.__quitMessage)
        settings.setValue("PartMessage", self.__partMessage)
        settings.setValue("RememberAwayPosition", self.__rememberPosOnAway)
        settings.setValue("AwayMessage", self.__awayMessage)

    def load(self, settings):
        """
        Public method to load the identity data.

        @param settings reference to the settings object
        @type QSettings
        """
        self.__ident = settings.value("Ident", OSUtilities.getUserName())
        self.__realName = settings.value("RealName", "")
        self.__nickNames = EricUtilities.toList(settings.value("NickNames", []))
        self.__serviceName = settings.value("ServiceName", "")
        self.__password = settings.value("Password", "")
        self.__quitMessage = settings.value(
            "QuitMessage", IrcIdentity.DefaultQuitMessage
        )
        self.__partMessage = settings.value(
            "PartMessage", IrcIdentity.DefaultPartMessage
        )
        self.__rememberPosOnAway = EricUtilities.toBool(
            settings.value("RememberAwayPosition", True)
        )
        self.__awayMessage = settings.value(
            "AwayMessage", IrcIdentity.DefaultAwayMessage
        )

    def setName(self, name):
        """
        Public method to set the identity name.

        @param name identity name
        @type str
        """
        self.__name = name

    def getName(self):
        """
        Public method to get the identity name.

        @return identity name
        @rtype str
        """
        return self.__name

    def setIdent(self, name):
        """
        Public method to set the real identity name.

        @param name real identity name
        @type str
        """
        self.__ident = name

    def getIdent(self):
        """
        Public method to get the real identity name.

        @return real identity name
        @rtype str
        """
        return self.__ident

    def setRealName(self, name):
        """
        Public method to set the real name of the identity.

        @param name real name
        @type str
        """
        self.__realName = name

    def getRealName(self):
        """
        Public method to get the real name.

        @return real name
        @rtype str
        """
        return self.__realName

    def setNickNames(self, names):
        """
        Public method to set the nick names of the identity.

        @param names nick names
        @type list of str
        """
        self.__nickNames = names[:]

    def getNickNames(self):
        """
        Public method to get the nick names.

        @return nick names
        @rtype list of str
        """
        return self.__nickNames

    def setServiceName(self, name):
        """
        Public method to set the service name of the identity used for
        identification.

        @param name service name
        @type str
        """
        self.__serviceName = name

    def getServiceName(self):
        """
        Public method to get the service name of the identity used for
        identification.

        @return service name
        @rtype str
        """
        return self.__serviceName

    def setPassword(self, password):
        """
        Public method to set a new password.

        @param password password to set
        @type str
        """
        self.__password = pwConvert(password, encode=True)

    def getPassword(self):
        """
        Public method to get the password.

        @return password
        @rtype str
        """
        return pwConvert(self.__password, encode=False)

    def setQuitMessage(self, message):
        """
        Public method to set the QUIT message.

        @param message QUIT message
        @type str
        """
        if message:
            self.__quitMessage = message
        else:
            self.__quitMessage = IrcIdentity.DefaultQuitMessage

    def getQuitMessage(self):
        """
        Public method to get the QUIT message.

        @return QUIT message
        @rtype str
        """
        return self.__quitMessage

    def setPartMessage(self, message):
        """
        Public method to set the PART message.

        @param message PART message
        @type str
        """
        if message:
            self.__partMessage = message
        else:
            self.__partMessage = IrcIdentity.DefaultPartMessage

    def getPartMessage(self):
        """
        Public method to get the PART message.

        @return PART message
        @rtype str
        """
        return self.__partMessage

    def setRememberAwayPosition(self, remember):
        """
        Public method to set to remember the chat position upon AWAY.

        @param remember flag indicating to remember the chat position
        @type bool
        """
        self.__rememberPosOnAway = remember

    def rememberAwayPosition(self):
        """
        Public method to get a flag indicating to remember the chat position
        upon AWAY.

        @return flag indicating to remember the chat position
        @rtype bool
        """
        return self.__rememberPosOnAway

    def setAwayMessage(self, message):
        """
        Public method to set the AWAY message.

        @param message AWAY message
        @type str
        """
        if message:
            self.__awayMessage = message
        else:
            self.__awayMessage = IrcIdentity.DefaultAwayMessage

    def getAwayMessage(self):
        """
        Public method to get the AWAY message.

        @return AWAY message
        @rtype str
        """
        return self.__awayMessage

    @classmethod
    def createDefaultIdentity(cls):
        """
        Class method to create the default identity.

        @return default identity
        @rtype IrcIdentity
        """
        userName = OSUtilities.getUserName()
        realName = OSUtilities.getRealName()
        if not realName:
            realName = "eric IDE chat"
        identity = IrcIdentity(IrcIdentity.DefaultIdentityName)
        identity.setNickNames([userName, userName + "_", userName + "__"])
        identity.setRealName(realName)
        identity.setIdent(userName)
        return identity


class IrcServer:
    """
    Class implementing the IRC identity object.
    """

    DefaultPort = 6667
    DefaultSslPort = 6697

    def __init__(self, name):
        """
        Constructor

        @param name name of the server
        @type str
        """
        super().__init__()

        self.__server = name
        self.__port = IrcServer.DefaultPort
        self.__ssl = False
        self.__password = ""

    def save(self, settings):
        """
        Public method to save the server data.

        @param settings reference to the settings object
        @type QSettings
        """
        settings.setValue("Name", self.__server)
        settings.setValue("Port", self.__port)
        settings.setValue("SSL", self.__ssl)
        settings.setValue("Password", self.__password)

    def load(self, settings):
        """
        Public method to load the server data.

        @param settings reference to the settings object
        @type QSettings
        """
        self.__server = settings.value("Name", "")
        self.__port = int(settings.value("Port", IrcServer.DefaultPort))
        self.__ssl = EricUtilities.toBool(settings.value("SSL", False))
        self.__password = settings.value("Password", "")

    def getName(self):
        """
        Public method to get the server name.

        @return server name
        @rtype str
        """
        return self.__server

    def setName(self, name):
        """
        Public method to set the server name.

        @param name server name
        @type str
        """
        self.__server = name

    def getPort(self):
        """
        Public method to get the server port number.

        @return port number
        @rtype int
        """
        return self.__port

    def setPort(self, port):
        """
        Public method to set the server port number.

        @param port server port number
        @type int
        """
        self.__port = port

    def useSSL(self):
        """
        Public method to check for SSL usage.

        @return flag indicating SSL usage
        @rtype bool
        """
        return self.__ssl

    def setUseSSL(self, on):
        """
        Public method to set the SSL usage.

        @param on flag indicating SSL usage
        @type bool
        """
        self.__ssl = on

    def setPassword(self, password):
        """
        Public method to set a new password.

        @param password password to set
        @type str
        """
        self.__password = pwConvert(password, encode=True)

    def getPassword(self):
        """
        Public method to get the password.

        @return password
        @rtype str
        """
        return pwConvert(self.__password, encode=False)


class IrcChannel:
    """
    Class implementing the IRC channel object.
    """

    def __init__(self, name):
        """
        Constructor

        @param name name of the network
        @type str
        """
        super().__init__()

        self.__name = name
        self.__key = ""
        self.__autoJoin = False

    def save(self, settings):
        """
        Public method to save the channel data.

        @param settings reference to the settings object
        @type QSettings
        """
        # no need to save the channel name because that is the group key
        settings.setValue("Key", self.__key)
        settings.setValue("AutoJoin", self.__autoJoin)

    def load(self, settings):
        """
        Public method to load the network data.

        @param settings reference to the settings object
        @type QSettings
        """
        self.__key = settings.value("Key", "")
        self.__autoJoin = EricUtilities.toBool(settings.value("AutoJoin", False))

    def getName(self):
        """
        Public method to get the channel name.

        @return channel name
        @rtype str
        """
        return self.__name

    def setKey(self, key):
        """
        Public method to set a new channel key.

        @param key channel key to set
        @type str
        """
        self.__key = pwConvert(key, encode=True)

    def getKey(self):
        """
        Public method to get the channel key.

        @return channel key
        @rtype str
        """
        return pwConvert(self.__key, encode=False)

    def autoJoin(self):
        """
        Public method to check the auto join status.

        @return flag indicating if the channel should be
            joined automatically
        @rtype bool
        """
        return self.__autoJoin

    def setAutoJoin(self, enable):
        """
        Public method to set the auto join status of the channel.

        @param enable flag indicating if the channel should be
            joined automatically
        @type bool
        """
        self.__autoJoin = enable


class IrcNetwork:
    """
    Class implementing the IRC network object.
    """

    def __init__(self, name):
        """
        Constructor

        @param name name of the network
        @type str
        """
        super().__init__()

        self.__name = name
        self.__identity = ""
        self.__server = None
        self.__channels = {}
        self.__autoConnect = False

    def save(self, settings):
        """
        Public method to save the network data.

        @param settings reference to the settings object
        @type QSettings
        """
        # no need to save the network name because that is the group key
        settings.setValue("Identity", self.__identity)
        settings.setValue("AutoConnect", self.__autoConnect)

        settings.beginGroup("Server")
        self.__server.save(settings)
        settings.endGroup()

        settings.beginGroup("Channels")
        for key in self.__channels:
            settings.beginGroup(key)
            self.__channels[key].save(settings)
            settings.endGroup()
        settings.endGroup()

    def load(self, settings):
        """
        Public method to load the network data.

        @param settings reference to the settings object
        @type QSettings
        """
        self.__identity = settings.value("Identity", "")
        self.__autoConnect = EricUtilities.toBool(settings.value("AutoConnect", False))

        settings.beginGroup("Server")
        self.__server = IrcServer("")
        self.__server.load(settings)
        settings.endGroup()

        settings.beginGroup("Channels")
        for key in settings.childGroups():
            self.__channels[key] = IrcChannel(key)
            settings.beginGroup(key)
            self.__channels[key].load(settings)
            settings.endGroup()
        settings.endGroup()

    def setName(self, name):
        """
        Public method to set the network name.

        @param name network name
        @type str
        """
        self.__name = name

    def getName(self):
        """
        Public method to get the network name.

        @return network name
        @rtype str
        """
        return self.__name

    def setIdentityName(self, name):
        """
        Public method to set the name of the identity.

        @param name identity name
        @type str
        """
        self.__identity = name

    def getIdentityName(self):
        """
        Public method to get the name of the identity.

        @return identity name
        @rtype str
        """
        return self.__identity

    def getServerName(self):
        """
        Public method to get the server name.

        @return server name
        @rtype str
        """
        if self.__server:
            return self.__server.getName()
        else:
            return ""

    def getServer(self):
        """
        Public method to get the server object.

        @return reference to the server
        @rtype IrcServer
        """
        return self.__server

    def setServer(self, server):
        """
        Public method to set the server.

        @param server server object to set
        @type IrcServer
        """
        self.__server = server

    def setChannels(self, channels):
        """
        Public method to set the list of channels.

        @param channels list of channels for the network
        @type list of IrcChannel
        """
        self.__channels = {}
        for channel in channels:
            self.__channels[channel.getName()] = channel

    def getChannels(self):
        """
        Public method to get the channels.

        @return list of channels for the network
        @rtype list of IrcChannel
        """
        return list(copy.deepcopy(self.__channels).values())

    def getChannelNames(self):
        """
        Public method to get the list of channels.

        @return list of channel names
        @rtype list of str
        """
        return sorted(self.__channels)

    def getChannel(self, channelName):
        """
        Public method to get a channel.

        @param channelName name of the channel to retrieve
        @type str
        @return reference to the channel
        @rtype IrcChannel
        """
        if channelName in self.__channels:
            return self.__channels[channelName]
        else:
            return None

    def setChannel(self, channel):
        """
        Public method to set a channel.

        @param channel channel object to set
        @type IrcChannel
        """
        channelName = channel.getName()
        if channelName in self.__channels:
            self.__channels[channelName] = channel

    def addChannel(self, channel):
        """
        Public method to add a channel.

        @param channel channel object to add
        @type IrcChannel
        """
        channelName = channel.getName()
        if channelName not in self.__channels:
            self.__channels[channelName] = channel

    def deleteChannel(self, channelName):
        """
        Public method to delete the given channel.

        @param channelName name of the channel to be deleted
        @type str
        """
        if channelName in self.__channels:
            del self.__channels[channelName]

    def setAutoConnect(self, enable):
        """
        Public method to set the auto connect flag.

        @param enable flag indicate to connect to the network at start-up
        @type bool
        """
        self.__autoConnect = enable

    def autoConnect(self):
        """
        Public method to check, if the network should be connected to at
        start-up.

        @return flag indicating an auto connect
        @rtype bool
        """
        return self.__autoConnect

    @classmethod
    def createDefaultNetwork(cls, ssl=False):
        """
        Class method to create the default network.

        @param ssl flag indicating to create a SSL network configuration
        @type bool
        @return default network object
        @rtype IrcNetwork
        """
        # network
        networkName = "libera.chat (SSL)" if ssl else "libera.chat"
        network = IrcNetwork(networkName)
        network.setIdentityName(IrcIdentity.DefaultIdentityName)

        # server
        serverName = "irc.libera.chat"
        server = IrcServer(serverName)
        if ssl:
            server.setPort(IrcServer.DefaultSslPort)
            server.setUseSSL(True)
        else:
            server.setPort(IrcServer.DefaultPort)
        network.setServer(server)

        # channel
        channel = IrcChannel("#eric-ide")
        channel.setAutoJoin(False)
        network.addChannel(channel)

        # auto connect
        network.setAutoConnect(False)

        return network


class IrcNetworkManager(QObject):
    """
    Class implementing the IRC identity object.

    @signal dataChanged() emitted after some data has changed
    @signal networksChanged() emitted after a network object has changed
    @signal identitiesChanged() emitted after an identity object has changed
    """

    dataChanged = pyqtSignal()
    networksChanged = pyqtSignal()
    identitiesChanged = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__loaded = False
        self.__saveTimer = AutoSaver(self, self.save)

        self.__settings = Preferences.getSettings()

        self.__networks = {}
        self.__identities = {}

        self.dataChanged.connect(self.__saveTimer.changeOccurred)

    def close(self):
        """
        Public method to close the open search engines manager.
        """
        self.__saveTimer.saveIfNeccessary()

    def save(self):
        """
        Public slot to save the IRC data.
        """
        if not self.__loaded:
            return

        # save IRC data
        self.__settings.beginGroup("IRC")

        # identities
        self.__settings.remove("Identities")
        self.__settings.beginGroup("Identities")
        for key in self.__identities:
            self.__settings.beginGroup(key)
            self.__identities[key].save(self.__settings)
            self.__settings.endGroup()
        self.__settings.endGroup()

        # networks
        self.__settings.remove("Networks")
        self.__settings.beginGroup("Networks")
        for key in self.__networks:
            self.__settings.beginGroup(key)
            self.__networks[key].save(self.__settings)
            self.__settings.endGroup()
        self.__settings.endGroup()

        self.__settings.endGroup()

    def __load(self):
        """
        Private slot to load the IRC data.
        """
        if self.__loaded:
            return

        # load IRC data
        self.__settings.beginGroup("IRC")

        # identities
        self.__settings.beginGroup("Identities")
        for key in self.__settings.childGroups():
            self.__identities[key] = IrcIdentity(key)
            self.__settings.beginGroup(key)
            self.__identities[key].load(self.__settings)
            self.__settings.endGroup()
        self.__settings.endGroup()

        # networks
        self.__settings.beginGroup("Networks")
        for key in self.__settings.childGroups():
            self.__networks[key] = IrcNetwork(key)
            self.__settings.beginGroup(key)
            self.__networks[key].load(self.__settings)
            self.__settings.endGroup()
        self.__settings.endGroup()

        self.__settings.endGroup()

        if not self.__identities or not self.__networks:
            # data structures got corrupted; load defaults
            self.__loadDefaults()

        if IrcIdentity.DefaultIdentityName not in self.__identities:
            self.__loadDefaults(identityOnly=True)

        self.__loaded = True

    def __loadDefaults(self, identityOnly=False):
        """
        Private method to load default values.

        @param identityOnly flag indicating to just load the default
            identity
        @type bool
        """
        if not identityOnly:
            self.__networks = {}
            self.__identities = {}

        # identity
        identity = IrcIdentity.createDefaultIdentity()
        self.__identities[identity.getName()] = identity

        if not identityOnly:
            network = IrcNetwork.createDefaultNetwork()
            self.__networks[network.getName()] = network
            network = IrcNetwork.createDefaultNetwork(True)
            self.__networks[network.getName()] = network

        self.dataChanged.emit()

    ##################################################################
    ## Identity related methods below
    ##################################################################

    def getIdentity(self, name, create=False):
        """
        Public method to get an identity object.

        @param name name of the identity to get
        @type str
        @param create flag indicating to create a new object,
            if none exists
        @type bool
        @return reference to the identity
        @rtype IrcIdentity
        """
        if not name:
            return None

        if not self.__loaded:
            self.__load()

        if name in self.__identities:
            return self.__identities[name]
        elif create:
            ircId = IrcIdentity(name)
            self.__identities[name] = ircId

            self.dataChanged.emit()

            return ircId
        else:
            return None

    def getIdentities(self):
        """
        Public method to get a copy of all identities.

        @return dictionary of all identities
        @rtype dict of IrcIdentity
        """
        return copy.deepcopy(self.__identities)

    def setIdentities(self, identities):
        """
        Public method to set the identities.

        @param identities dictionary of all identities
        @type dict of IrcIdentity
        """
        self.__identities = copy.deepcopy(identities)
        self.identityChanged()

        # Check all networks, if the identity they use is still available.
        # If it isn't, change them to use the default identity.
        for network in self.__networks.values():
            if network.getIdentityName() not in self.__identities:
                network.setIdentityName(IrcIdentity.DefaultIdentityName)

    def getIdentityNames(self):
        """
        Public method to get the names of all identities.

        @return names of all identities
        @rtype list of string)
        """
        return list(self.__identities)

    def addIdentity(self, identity):
        """
        Public method to add a new identity.

        @param identity reference to the identity to add
        @type IrcIdentity
        """
        name = identity.getName()
        self.__identities[name] = identity
        self.identityChanged()

    def deleteIdentity(self, name):
        """
        Public method to delete the given identity.

        @param name name of the identity to delete
        @type str
        """
        if name in self.__identities and name != IrcIdentity.DefaultIdentityName:
            del self.__identities[name]
            self.identityChanged()

    def renameIdentity(self, oldName, newName):
        """
        Public method to rename an identity.

        @param oldName old name of the identity
        @type str
        @param newName new name of the identity
        @type str
        """
        if oldName in self.__identities:
            self.__identities[newName] = self.__identities[oldName]
            del self.__identities[oldName]

            for network in self.__networks:
                if network.getIdentityName() == oldName:
                    network.setIdentityName(newName)

            self.identityChanged()

    def identityChanged(self):
        """
        Public method to indicate a change of an identity object.
        """
        self.dataChanged.emit()
        self.identitiesChanged.emit()

    ##################################################################
    ## Network related methods below
    ##################################################################

    def getNetwork(self, name):
        """
        Public method to get a network object.

        @param name name of the network
        @type str
        @return reference to the network object
        @rtype IrcNetwork
        """
        if not self.__loaded:
            self.__load()

        if name in self.__networks:
            return self.__networks[name]
        else:
            return None

    def setNetwork(self, network, networkName=""):
        """
        Public method to set a network.

        @param network network object to set
        @type IrcNetwork
        @param networkName name the network was known for
        @type str
        """
        name = network.getName()
        if networkName and name != networkName:
            # the network name has changed
            self.deleteNetwork(networkName)
            self.addNetwork(network)
        elif name in self.__networks:
            self.__networks[name] = network
            self.networkChanged()

    def addNetwork(self, network):
        """
        Public method to add a network.

        @param network network object to add
        @type IrcNetwork
        """
        name = network.getName()
        if name not in self.__networks:
            self.__networks[name] = network
            self.networkChanged()

    def deleteNetwork(self, name):
        """
        Public method to delete the given network.

        @param name name of the network to delete
        @type str
        """
        if name in self.__networks:
            del self.__networks[name]
            self.networkChanged()

    def networkChanged(self):
        """
        Public method to indicate a change of a network object.
        """
        self.dataChanged.emit()
        self.networksChanged.emit()

    def getNetworkNames(self):
        """
        Public method to get a list of all known network names.

        @return list of network names
        @rtype list of str
        """
        if not self.__loaded:
            self.__load()

        return sorted(self.__networks)
