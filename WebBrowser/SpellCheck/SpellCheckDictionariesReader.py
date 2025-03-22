# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module to read the web browser spell check dictionaries list file.
"""

from eric7 import Preferences
from eric7.XML.XMLStreamReaderBase import XMLStreamReaderBase

# version number of the web browser spell check dictionaries list file
dictionariesListFileFormatVersion = "1.0"


class SpellCheckDictionariesReader(XMLStreamReaderBase):
    """
    Class to read the web browser spell check dictionaries list file.
    """

    supportedVersions = ["1.0"]

    def __init__(self, data, entryCallback):
        """
        Constructor

        @param data reference to the data array to read XML from
        @type QByteArray
        @param entryCallback reference to a function to be called once the
            data for a dictionary has been read
        @type function
        """
        XMLStreamReaderBase.__init__(self, data)

        self.__entryCallback = entryCallback

        self.version = ""
        self.baseUrl = ""

    def readXML(self):
        """
        Public method to read and parse the XML document.
        """
        while not self.atEnd():
            self.readNext()
            if self.isStartElement():
                if self.name() == "Dictionaries":
                    self.version = self.attribute(
                        "version", dictionariesListFileFormatVersion
                    )
                    self.baseUrl = self.attribute("baseurl", "")
                    if self.version not in self.supportedVersions:
                        self.raiseUnsupportedFormatVersion(self.version)
                elif self.name() == "DictionariesUrl":
                    url = self.readElementText()
                    Preferences.setWebBrowser("SpellCheckDictionariesUrl", url)
                elif self.name() == "Dictionary":
                    self.__readDictionary()
                else:
                    self._skipUnknownElement()

        self.showErrorMessage()

    def __readDictionary(self):
        """
        Private method to read the plug-in info.
        """
        dictionaryInfo = {
            "short": "",
            "filename": "",
            "documentation": "",
            "locales": [],
        }

        while not self.atEnd():
            self.readNext()
            if self.isEndElement() and self.name() == "Dictionary":
                self.__entryCallback(
                    dictionaryInfo["short"],
                    dictionaryInfo["filename"],
                    self.baseUrl + dictionaryInfo["filename"],
                    dictionaryInfo["documentation"],
                    dictionaryInfo["locales"],
                )
                break

            if self.isStartElement():
                if self.name() == "Short":
                    dictionaryInfo["short"] = self.readElementText()
                elif self.name() == "Filename":
                    dictionaryInfo["filename"] = self.readElementText()
                elif self.name() == "Documentation":
                    dictionaryInfo["documentation"] = self.readElementText()
                elif self.name() == "Locales":
                    dictionaryInfo["locales"] = self.readElementText().split()
                else:
                    self.raiseUnexpectedStartTag(self.name())
