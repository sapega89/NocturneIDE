# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a user agent manager.
"""

import os

from PyQt6.QtCore import QObject, QXmlStreamReader, pyqtSignal

from eric7 import EricUtilities
from eric7.EricWidgets import EricMessageBox
from eric7.Utilities.AutoSaver import AutoSaver


class UserAgentManager(QObject):
    """
    Class implementing a user agent manager.

    @signal changed() emitted to indicate a change
    @signal userAgentSettingsSaved() emitted after the user agent settings
        were saved
    """

    changed = pyqtSignal()
    userAgentSettingsSaved = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__agents = {}
        # dictionary with agent strings indexed by host name
        self.__loaded = False
        self.__saveTimer = AutoSaver(self, self.save)

        self.changed.connect(self.__saveTimer.changeOccurred)

    def getFileName(self):
        """
        Public method to get the file name of the user agents file.

        @return name of the user agents file
        @rtype str
        """
        return os.path.join(
            EricUtilities.getConfigDir(), "web_browser", "userAgentSettings.xml"
        )

    def save(self):
        """
        Public slot to save the user agent entries to disk.
        """
        from .UserAgentWriter import UserAgentWriter

        if not self.__loaded:
            return

        agentFile = self.getFileName()
        writer = UserAgentWriter()
        if not writer.write(agentFile, self.__agents):
            EricMessageBox.critical(
                None,
                self.tr("Saving user agent data"),
                self.tr(
                    """<p>User agent data could not be saved to <b>{0}</b></p>"""
                ).format(agentFile),
            )
        else:
            self.userAgentSettingsSaved.emit()

    def __load(self):
        """
        Private method to load the saved user agent settings.
        """
        from .UserAgentReader import UserAgentReader

        agentFile = self.getFileName()
        reader = UserAgentReader()
        self.__agents = reader.read(agentFile)
        if reader.error() != QXmlStreamReader.Error.NoError:
            EricMessageBox.warning(
                None,
                self.tr("Loading user agent data"),
                self.tr(
                    """Error when loading user agent data on"""
                    """ line {0}, column {1}:\n{2}"""
                ).format(
                    reader.lineNumber(), reader.columnNumber(), reader.errorString()
                ),
            )

        self.__loaded = True

    def reload(self):
        """
        Public method to reload the user agent settings.
        """
        if not self.__loaded:
            return

        self.__agents = {}
        self.__load()

    def close(self):
        """
        Public method to close the user agents manager.
        """
        self.__saveTimer.saveIfNeccessary()

    def removeUserAgent(self, host):
        """
        Public method to remove a user agent entry.

        @param host host name
        @type str
        """
        if host in self.__agents:
            del self.__agents[host]
            self.changed.emit()

    def allHostNames(self):
        """
        Public method to get a list of all host names we a user agent setting
        for.

        @return sorted list of all host names
        @rtype list of str
        """
        if not self.__loaded:
            self.__load()

        return sorted(self.__agents)

    def hostsCount(self):
        """
        Public method to get the number of available user agent settings.

        @return number of user agent settings
        @rtype int
        """
        if not self.__loaded:
            self.__load()

        return len(self.__agents)

    def userAgent(self, host):
        """
        Public method to get the user agent setting for a host.

        @param host host name
        @type str
        @return user agent string
        @rtype str
        """
        if not self.__loaded:
            self.__load()

        for agentHost in self.__agents:
            if host.endswith(agentHost):
                return self.__agents[agentHost]

        return ""

    def setUserAgent(self, host, agent):
        """
        Public method to set the user agent string for a host.

        @param host host name
        @type str
        @param agent user agent string
        @type str
        """
        if host != "" and agent != "":
            self.__agents[host] = agent
            self.changed.emit()

    def userAgentForUrl(self, url):
        """
        Public method to determine the user agent for the given URL.

        @param url URL to determine user agent for
        @type QUrl
        @return user agent string
        @rtype str
        """
        if url.isValid():
            host = url.host()
            return self.userAgent(host)

        return ""

    def setUserAgentForUrl(self, url, agent):
        """
        Public method to set the user agent string for an URL.

        @param url URL to register user agent setting for
        @type QUrl
        @param agent new current user agent string
        @type str
        """
        if url.isValid():
            host = url.host()
            self.setUserAgent(host, agent)
