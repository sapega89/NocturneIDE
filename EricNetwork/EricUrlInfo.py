# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class replacing QUrlInfo.
"""

import enum

from PyQt6.QtCore import QDateTime


class EricUrlPermission(enum.IntEnum):
    """
    Class defining the URL permissions.
    """

    READ_OWNER = 0o0400
    WRITE_OWNER = 0o0200
    EXE_OWNER = 0o0100
    READ_GROUP = 0o0040
    WRITE_GROUP = 0o0020
    EXE_GROUP = 0o0010
    READ_OTHER = 0o0004
    WRITE_OTHER = 0o0002
    EXE_OTHER = 0o0001


class EricUrlInfo:
    """
    Class implementing a replacement for QUrlInfo.
    """

    def __init__(self):
        """
        Constructor
        """
        self.__valid = False

        self.__permissions = 0
        self.__size = 0
        self.__isDir = False
        self.__isFile = True
        self.__isSymlink = False
        self.__isWritable = True
        self.__isReadable = True
        self.__isExecutable = False
        self.__name = ""
        self.__owner = ""
        self.__group = ""
        self.__lastModified = QDateTime()
        self.__lastRead = QDateTime()

    def isValid(self):
        """
        Public method to check the validity of the object.

        @return flag indicating validity
        @rtype bool
        """
        return self.__valid

    def setName(self, name):
        """
        Public method to set the name.

        @param name name to be set
        @type str
        """
        self.__name = name
        self.__valid = True

    def setPermissions(self, permissions):
        """
        Public method to set the permissions.

        @param permissions permissions to be set
        @type int
        """
        self.__permissions = permissions
        self.__valid = True

    def setDir(self, isDir):
        """
        Public method to indicate a directory.

        @param isDir flag indicating a directory
        @type bool
        """
        self.__isDir = isDir
        self.__valid = True

    def setFile(self, isFile):
        """
        Public method to indicate a file.

        @param isFile flag indicating a file
        @type bool
        """
        self.__isFile = isFile
        self.__valid = True

    def setSymLink(self, isSymLink):
        """
        Public method to indicate a symbolic link.

        @param isSymLink flag indicating a symbolic link
        @type bool
        """
        self.__isSymLink = isSymLink
        self.__valid = True

    def setOwner(self, owner):
        """
        Public method to set the owner.

        @param owner owner to be set
        @type str
        """
        self.__owner = owner
        self.__valid = True

    def setGroup(self, group):
        """
        Public method to set the group.

        @param group group to be set
        @type str
        """
        self.__group = group
        self.__valid = True

    def setSize(self, size):
        """
        Public method to set the size.

        @param size size to be set
        @type int
        """
        self.__size = size
        self.__valid = True

    def setWritable(self, isWritable):
        """
        Public method to a writable entry.

        @param isWritable flag indicating a writable entry
        @type bool
        """
        self.__isWritable = isWritable
        self.__valid = True

    def setReadable(self, isReadable):
        """
        Public method to a readable entry.

        @param isReadable flag indicating a readable entry
        @type bool
        """
        self.__isReadable = isReadable
        self.__valid = True

    def setLastModified(self, dt):
        """
        Public method to set the last modified date and time.

        @param dt date and time to set
        @type QDateTime
        """
        self.__lastModified = QDateTime(dt)
        self.__valid = True

    def setLastRead(self, dt):
        """
        Public method to set the last read date and time.

        @param dt date and time to set
        @type QDateTime
        """
        self.__lastRead = QDateTime(dt)
        self.__valid = True

    def name(self):
        """
        Public method to get the name.

        @return name
        @rtype str
        """
        return self.__name

    def permissions(self):
        """
        Public method to get the permissions.

        @return permissions
        @rtype int
        """
        return self.__permissions

    def owner(self):
        """
        Public method to get the owner.

        @return owner
        @rtype str
        """
        return self.__owner

    def group(self):
        """
        Public method to get the group.

        @return group
        @rtype str
        """
        return self.__group

    def size(self):
        """
        Public method to get the size.

        @return size
        @rtype int
        """
        return self.__size

    def lastModified(self):
        """
        Public method to get the last modified date and time.

        @return last modified date and time
        @rtype QDateTime
        """
        return QDateTime(self.__lastModified)

    def lastRead(self):
        """
        Public method to get the last read date and time.

        @return last read date and time
        @rtype QDateTime
        """
        return QDateTime(self.__lastRead)

    def isDir(self):
        """
        Public method to test, if the entry is a directory.

        @return flag indicating a directory
        @rtype bool
        """
        return self.__isDir

    def isFile(self):
        """
        Public method to test, if the entry is a file.

        @return flag indicating a file
        @rtype bool
        """
        return self.__isFile

    def isSymLink(self):
        """
        Public method to test, if the entry is a symbolic link.

        @return flag indicating a symbolic link
        @rtype bool
        """
        return self.__isSymlink

    def isWritable(self):
        """
        Public method to test, if the entry is writable.

        @return flag indicating writable
        @rtype bool
        """
        return self.__isWritable

    def isReadable(self):
        """
        Public method to test, if the entry is readable.

        @return flag indicating readable
        @rtype bool
        """
        return self.__isReadable

    def isExecutable(self):
        """
        Public method to test, if the entry is executable.

        @return flag indicating executable
        @rtype bool
        """
        return self.__isExecutable
