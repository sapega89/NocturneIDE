# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing a class to read user agent data files.
"""

from PyQt6.QtCore import QCoreApplication, QFile, QIODevice, QXmlStreamReader


class UserAgentReader(QXmlStreamReader):
    """
    Class implementing a reader object for user agent data files.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

    def read(self, fileNameOrDevice):
        """
        Public method to read a user agent file.

        @param fileNameOrDevice name of the file to read or reference to the device
            to read
        @type str or QIODevice
        @return dictionary with user agent data (host as key, agent string as value)
        @rtype dict
        """
        self.__agents = {}

        if isinstance(fileNameOrDevice, QIODevice):
            self.setDevice(fileNameOrDevice)
        else:
            f = QFile(fileNameOrDevice)
            if not f.exists():
                return self.__agents
            f.open(QIODevice.OpenModeFlag.ReadOnly)
            self.setDevice(f)

        while not self.atEnd():
            self.readNext()
            if self.isStartElement():
                version = self.attributes().value("version")
                if self.name() == "UserAgents" and (not version or version == "1.0"):
                    self.__readUserAgents()
                else:
                    self.raiseError(
                        QCoreApplication.translate(
                            "UserAgentReader",
                            "The file is not a UserAgents version 1.0 file.",
                        )
                    )

        return self.__agents

    def __readUserAgents(self):
        """
        Private method to read the user agents data.
        """
        if not self.isStartElement() and self.name() != "UserAgents":
            return

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                if self.name() == "UserAgent":
                    continue
                else:
                    break

            if self.isStartElement():
                if self.name() == "UserAgent":
                    attributes = self.attributes()
                    host = attributes.value("host")
                    agent = attributes.value("agent")
                    self.__agents[host] = agent
                else:
                    self.__skipUnknownElement()

    def __skipUnknownElement(self):
        """
        Private method to skip over all unknown elements.
        """
        if not self.isStartElement():
            return

        while not self.atEnd():
            self.readNext()
            if self.isEndElement():
                break

            if self.isStartElement():
                self.__skipUnknownElement()
