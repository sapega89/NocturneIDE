# -*- coding: utf-8 -*-

# Copyright (c) 2018 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the threat list info class.
"""


class ThreatList:
    """
    Class implementing the threat list info.
    """

    def __init__(self, threatType, platformType, threatEntryType):
        """
        Constructor

        @param threatType threat type
        @type str
        @param platformType platform type
        @type str
        @param threatEntryType threat entry type
        @type str
        """
        self.threatType = threatType
        self.platformType = platformType
        self.threatEntryType = threatEntryType

    @classmethod
    def fromApiEntry(cls, entry):
        """
        Class method to instantiate a threat list given a threat list entry
        dictionary.

        @param entry threat list entry dictionary
        @type dict
        @return instantiated object
        @rtype ThreatList
        """
        return cls(entry["threatType"], entry["platformType"], entry["threatEntryType"])

    def asTuple(self):
        """
        Public method to convert the object to a tuple.

        @return tuple containing the threat list info
        @rtype tuple of (str, str, str)
        """
        return (self.threatType, self.platformType, self.threatEntryType)

    def __repr__(self):
        """
        Special method to generate a printable representation.

        @return printable representation
        @rtype str
        """
        return "/".join(self.asTuple())


class HashPrefixList:
    """
    Class implementing a container for threat list data.
    """

    def __init__(self, prefixLength, rawHashes):
        """
        Constructor

        @param prefixLength length of each hash prefix
        @type int
        @param rawHashes raw hash prefixes of given length concatenated and
            sorted in lexicographical order
        @type str
        """
        self.__prefixLength = prefixLength
        self.__rawHashes = rawHashes

    def __len__(self):
        """
        Special method to calculate the number of entries.

        @return length
        @rtype int
        """
        return len(self.__rawHashes) // self.__prefixLength

    def __iter__(self):
        """
        Special method to iterate over the raw hashes.

        @return iterator object
        @rtype iterator
        """
        n = self.__prefixLength
        return (
            self.__rawHashes[index : index + n]
            for index in range(0, len(self.__rawHashes), n)
        )
