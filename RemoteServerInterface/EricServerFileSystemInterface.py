# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the file system interface to the eric-ide server.
"""

import base64
import contextlib
import logging
import os
import re
import stat

from PyQt6.QtCore import QByteArray, QEventLoop, QObject, pyqtSlot

from eric7 import Utilities
from eric7.RemoteServer.EricRequestCategory import EricRequestCategory
from eric7.SystemUtilities import FileSystemUtilities

_RemoteFsCache = {}
# dictionary containing cached remote file system data keyed by remote path


class EricServerNotConnectedError(OSError):
    """
    Class defining a special OSError indicating a missing server connection.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__("Not connected to an 'eric-ide' server.")


class EricServerFileSystemInterface(QObject):
    """
    Class implementing the file system interface to the eric-ide server.
    """

    _MagicCheck = re.compile("([*?[])")

    NotConnectedMessage = "Not connected to an 'eric-ide' server."

    def __init__(self, serverInterface):
        """
        Constructor

        @param serverInterface reference to the eric-ide server interface
        @type EricServerInterface
        """
        super().__init__(parent=serverInterface)

        self.__serverInterface = serverInterface
        self.__serverInterface.connectionStateChanged.connect(
            self.__connectionStateChanged
        )

        self.__serverPathSep = self.__getPathSep()

    def serverInterface(self):
        """
        Public method to get a reference to the server interface object.

        @return reference to the server interface object
        @rtype EricServerInterface
        """
        return self.__serverInterface

    def __hasMagic(self, pathname):
        """
        Private method to check, if a given path contains glob style magic characters.

        Note: This was taken from 'glob.glob'.

        @param pathname path name to be checked
        @type str
        @return flag indicating the presence of magic characters
        @rtype bool
        """
        match = self._MagicCheck.search(pathname)
        return match is not None

    @pyqtSlot(bool)
    def __connectionStateChanged(self, connected):
        """
        Private slot handling a change of the server connection state.

        @param connected flag indicating a connected state
        @type bool
        """
        if connected and not bool(self.__serverPathSep):
            self.__serverPathSep = self.__getPathSep()

    def __getPathSep(self):
        """
        Private method to get the path separator of the connected server.

        @return path separator character of the server
        @rtype str
        """
        loop = QEventLoop()
        sep = ""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal sep

            if reply == "GetPathSep":
                sep = params["separator"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="GetPathSep",
                params={},
                callback=callback,
            )

            loop.exec()

        return sep

    def getcwd(self):
        """
        Public method to get the current working directory of the eric-ide server.

        @return current working directory of the eric-ide server
        @rtype str
        """
        loop = QEventLoop()
        cwd = ""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal cwd

            if reply == "Getcwd":
                cwd = params["directory"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="Getcwd",
                params={},
                callback=callback,
            )

            loop.exec()

        return FileSystemUtilities.remoteFileName(cwd)

    def chdir(self, directory):
        """
        Public method to change the current working directory of the eric-ide server.

        @param directory absolute path of the working directory to change to
        @type str
        @return tuple containing an OK flag and an error string in case of an issue
        @rtype tuple of (bool, str)
        """
        loop = QEventLoop()
        ok = False
        error = ""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error

            if reply == "Chdir":
                ok = params["ok"]
                with contextlib.suppress(KeyError):
                    error = params["error"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="Chdir",
                params={"directory": FileSystemUtilities.plainFileName(directory)},
                callback=callback,
            )

            loop.exec()
            return ok, error

        else:
            return False, EricServerFileSystemInterface.NotConnectedMessage

    def listdir(self, directory="", recursive=False):
        """
        Public method to get a directory listing.

        @param directory directory to be listed. An empty directory means to list
            the eric-ide server current directory. (defaults to "")
        @type str (optional)
        @param recursive flag indicating a recursive listing (defaults to False)
        @type bool (optional)
        @return tuple containing the listed directory, the path separator and the
            directory listing. Each directory listing entry contains a dictionary
            with the relevant data.
        @rtype tuple of (str, str, dict)
        @exception OSError raised in case the server reported an issue
        """
        if directory is None:
            # sanitize the directory in case it is None
            directory = ""

        loop = QEventLoop()
        ok = False
        error = ""
        listedDirectory = ""
        separator = ""
        listing = []

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal listedDirectory, listing, separator, ok, error

            if reply == "Listdir":
                ok = params["ok"]
                if ok:
                    listedDirectory = params["directory"]
                    listing = params["listing"]
                    separator = params["separator"]
                else:
                    error = params["error"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="Listdir",
                params={
                    "directory": FileSystemUtilities.plainFileName(directory),
                    "recursive": recursive,
                },
                callback=callback,
            )

            loop.exec()
            if not ok:
                raise OSError(error)

            for entry in listing:
                entry["path"] = FileSystemUtilities.remoteFileName(entry["path"])

        return listedDirectory, separator, listing

    def direntries(
        self,
        directory,
        filesonly=False,
        pattern=None,
        followsymlinks=True,
        ignore=None,
        recursive=True,
        dirsonly=False,
    ):
        """
        Public method to get a list of all files and directories of a given directory.

        @param directory root of the tree to check
        @type str
        @param filesonly flag indicating that only files are wanted (defaults to False)
        @type bool (optional)
        @param pattern a filename pattern or list of filename patterns to check
            against (defaults to None)
        @type str or list of str (optional)
        @param followsymlinks flag indicating whether symbolic links should be
            followed (defaults to True)
        @type bool (optional)
        @param ignore list of entries to be ignored (defaults to None)
        @type list of str (optional)
        @param recursive flag indicating a recursive search (defaults to True)
        @type bool (optional)
        @param dirsonly flag indicating to return only directories. When True it has
            precedence over the 'filesonly' parameter (defaults to False)
        @type bool
        @return list of all files and directories in the tree rooted at path.
            The names are expanded to start with the given directory name.
        @rtype list of str
        @exception OSError raised in case the server reported an issue
        """
        loop = QEventLoop()
        ok = False
        error = ""
        result = []

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal result, ok, error

            if reply == "DirEntries":
                ok = params["ok"]
                if ok:
                    result = params["result"]
                else:
                    error = params["error"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="DirEntries",
                params={
                    "directory": FileSystemUtilities.plainFileName(directory),
                    "files_only": filesonly,
                    "pattern": [] if pattern is None else pattern,
                    "follow_symlinks": followsymlinks,
                    "ignore": [] if ignore is None else ignore,
                    "recursive": recursive,
                    "dirs_only": dirsonly,
                },
                callback=callback,
            )

            loop.exec()
            if not ok:
                raise OSError(error)

        return [FileSystemUtilities.remoteFileName(r) for r in result]

    def glob(self, pathname, recursive=False, includeHidden=False):
        """
        Public method to get a list of of all files matching a given pattern
        like 'glob.glob()'.

        @param pathname path name pattern with simple shell-style wildcards
        @type str
        @param recursive flag indicating a recursive list (defaults to False)
        @type bool (optional)
        @param includeHidden flag indicating to include hidden files (defaults to False)
        @type bool (optional)
        @return list of all files matching the pattern
        @rtype list of str
        """
        result = []

        pathname = FileSystemUtilities.plainFileName(pathname)
        dirname, basename = os.path.split(pathname)
        if dirname and not self.__hasMagic(dirname):
            with contextlib.suppress(OSError):
                entries = self.direntries(
                    dirname, pattern=basename, recursive=recursive, filesonly=True
                )
                result = (
                    [FileSystemUtilities.remoteFileName(e) for e in entries]
                    if includeHidden
                    else [
                        FileSystemUtilities.remoteFileName(e)
                        for e in entries
                        if not e.startswith(".")
                    ]
                )

        return result

    def stat(self, filename, stNames):
        """
        Public method to get the status of a file.

        @param filename name of the file
        @type str
        @param stNames list of 'stat_result' members to retrieve
        @type list of str
        @return dictionary containing the requested status data
        @rtype dict
        @exception OSError raised in case the server reported an issue
        """
        loop = QEventLoop()
        ok = False
        error = ""
        stResult = {}

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error, stResult

            if reply == "Stat":
                ok = params["ok"]
                if ok:
                    stResult = params["result"]
                else:
                    error = params["error"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="Stat",
                params={
                    "filename": FileSystemUtilities.plainFileName(filename),
                    "st_names": stNames,
                },
                callback=callback,
            )

            loop.exec()
            if not ok:
                raise OSError(error)

        return stResult

    def isdir(self, name):
        """
        Public method to check, if the given name is a directory.

        @param name name to be checked
        @type str
        @return flag indicating a directory
        @rtype bool
        """
        try:
            return stat.S_ISDIR(_RemoteFsCache[name]["mode"])
        except KeyError:
            with contextlib.suppress(KeyError, OSError):
                result = self.stat(name, ["st_mode"])
                return stat.S_ISDIR(result["st_mode"])

        return False

    def isfile(self, name):
        """
        Public method to check, if the given name is a regular file.

        @param name name to be checked
        @type str
        @return flag indicating a regular file
        @rtype bool
        """
        try:
            return stat.S_ISREG(_RemoteFsCache[name]["mode"])
        except KeyError:
            with contextlib.suppress(KeyError, OSError):
                result = self.stat(name, ["st_mode"])
                return stat.S_ISREG(result["st_mode"])

        return False

    def exists(self, name):
        """
        Public method the existence of a file or directory.

        @param name name of the file or directory
        @type str
        @return flag indicating the file existence
        @rtype bool
        """
        loop = QEventLoop()
        nameExists = False

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal nameExists

            if reply == "Exists":
                nameExists = params["exists"]
                loop.quit()

        if name in _RemoteFsCache:
            return True

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="Exists",
                params={"name": FileSystemUtilities.plainFileName(name)},
                callback=callback,
            )

            loop.exec()

        return nameExists

    def access(self, name, modes):
        """
        Public method to test the given access rights to a file or directory.

        The modes to check for are 'read', 'write' or 'execute' or any combination.

        @param name name of the file or directory
        @type str
        @param modes list of modes to check for
        @type str or list of str
        @return flag indicating the user has the asked for permissions
        @rtype bool
        @exception ValueError raised for an illegal modes list
        """
        if not modes:
            raise ValueError(
                "At least one of 'read', 'write' or 'execute' must be specified."
            )

        if isinstance(modes, str):
            # convert to a list with one element
            modes = [modes]

        loop = QEventLoop()
        accessOK = False

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal accessOK

            if reply == "Access":
                accessOK = params["ok"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="Access",
                params={
                    "name": FileSystemUtilities.plainFileName(name),
                    "modes": modes,
                },
                callback=callback,
            )

            loop.exec()

        return accessOK

    def isEmpty(self, name):
        """
        Public method to check, if the given name is empty (i.e. just the remote
        name indicator).

        @param name file or directory path to be checked
        @type str
        @return flag indicating an empty path
        @rtype bool
        """
        return not bool(FileSystemUtilities.plainFileName(name))

    def mkdir(self, directory, mode=0o777):
        """
        Public method to create a new directory on the eric-ide server.

        @param directory absolute path of the new directory
        @type str
        @param mode permissions value (defaults to 0o777)
        @type int
        @return tuple containing an OK flag and an error string in case of an issue
        @rtype tuple of (bool, str)
        """
        loop = QEventLoop()
        ok = False
        error = ""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error

            if reply == "Mkdir":
                ok = params["ok"]
                with contextlib.suppress(KeyError):
                    error = params["error"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="Mkdir",
                params={
                    "directory": FileSystemUtilities.plainFileName(directory),
                    "mode": mode,
                },
                callback=callback,
            )

            loop.exec()
            if ok:
                self.populateFsCache(directory)
            return ok, error

        else:
            return False, EricServerFileSystemInterface.NotConnectedMessage

    def makedirs(self, directory, exist_ok=False):
        """
        Public method to create a new directory on the eric-ide serverincluding all
        intermediate-level directories.

        @param directory absolute path of the new directory
        @type str
        @param exist_ok flag indicating that the existence of the directory is
            acceptable (defaults to False)
        @type bool (optional)
        @return tuple containing an OK flag and an error string in case of an issue
        @rtype tuple of (bool, str)
        """
        loop = QEventLoop()
        ok = False
        error = ""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error

            if reply == "MakeDirs":
                ok = params["ok"]
                with contextlib.suppress(KeyError):
                    error = params["error"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="MakeDirs",
                params={
                    "directory": FileSystemUtilities.plainFileName(directory),
                    "exist_ok": exist_ok,
                },
                callback=callback,
            )

            loop.exec()
            if ok:
                self.populateFsCache(directory)
            return ok, error

        else:
            return False, EricServerFileSystemInterface.NotConnectedMessage

    def rmdir(self, directory):
        """
        Public method to delete a directory on the eric-ide server.

        @param directory absolute path of the directory
        @type str
        @return tuple containing an OK flag and an error string in case of an issue
        @rtype tuple of (bool, str)
        """
        loop = QEventLoop()
        ok = False
        error = ""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error

            if reply == "Rmdir":
                ok = params["ok"]
                with contextlib.suppress(KeyError):
                    error = params["error"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="Rmdir",
                params={"directory": FileSystemUtilities.plainFileName(directory)},
                callback=callback,
            )

            loop.exec()
            if ok:
                self.removeFromFsCache(directory)
            return ok, error

        else:
            return False, EricServerFileSystemInterface.NotConnectedMessage

    def replace(self, oldName, newName):
        """
        Public method to rename a file or directory.

        @param oldName current name of the file or directory
        @type str
        @param newName new name for the file or directory
        @type str
        @return tuple containing an OK flag and an error string in case of an issue
        @rtype tuple of (bool, str)
        """
        loop = QEventLoop()
        ok = False
        error = ""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error

            if reply == "Replace":
                ok = params["ok"]
                with contextlib.suppress(KeyError):
                    error = params["error"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="Replace",
                params={
                    "old_name": FileSystemUtilities.plainFileName(oldName),
                    "new_name": FileSystemUtilities.plainFileName(newName),
                },
                callback=callback,
            )

            loop.exec()
            if ok:
                with contextlib.suppress(KeyError):
                    entry = _RemoteFsCache.pop(oldName)
                    entry["path"] = newName
                    entry["name"] = self.basename(newName)
                    _RemoteFsCache[newName] = entry
            return ok, error

        else:
            return False, EricServerFileSystemInterface.NotConnectedMessage

    def remove(self, filename):
        """
        Public method to delete a file on the eric-ide server.

        @param filename absolute path of the file
        @type str
        @return tuple containing an OK flag and an error string in case of an issue
        @rtype tuple of (bool, str)
        """
        loop = QEventLoop()
        ok = False
        error = ""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error

            if reply == "Remove":
                ok = params["ok"]
                with contextlib.suppress(KeyError):
                    error = params["error"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="Remove",
                params={"filename": FileSystemUtilities.plainFileName(filename)},
                callback=callback,
            )

            loop.exec()
            if ok:
                with contextlib.suppress(KeyError):
                    del _RemoteFsCache[filename]
            return ok, error

        else:
            return False, EricServerFileSystemInterface.NotConnectedMessage

    def expanduser(self, name):
        """
        Public method to expand an initial '~' or '~user' component.

        @param name path name to be expanded
        @type str
        @return expanded path name
        @rtype str
        """
        loop = QEventLoop()
        ok = False
        expandedName = name

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, expandedName

            if reply == "ExpandUser":
                ok = params["ok"]
                expandedName = params["name"]
                loop.quit()

        if self.__serverInterface.isServerConnected():
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="ExpandUser",
                params={"name": FileSystemUtilities.plainFileName(name)},
                callback=callback,
            )

            loop.exec()
        if FileSystemUtilities.isRemoteFileName(name):
            return FileSystemUtilities.remoteFileName(expandedName)
        else:
            return expandedName

    #######################################################################
    ## Methods for splitting or joining remote path names.
    ##
    ## These are simplified variants of the os.path functions. If the
    ## 'eric-ide' server is not connected, the os.path functions are used.
    #######################################################################

    def separator(self):
        """
        Public method to return the server side path separator string.

        @return path separator
        @rtype str
        """
        return self.__serverPathSep

    def isabs(self, p):
        """
        Public method to chack a path for being an absolute path.

        @param p path to be checked
        @type str
        @return flag indicating an absolute path
        @rtype bool
        """
        if self.__serverPathSep == "\\":
            s = FileSystemUtilities.plainFileName(p)[:3].replace("/", "\\")
            return s.startswith("\\)") or s.startswith(":\\", 1)
        else:
            return FileSystemUtilities.plainFileName(p).startswith("/")

    def abspath(self, p):
        """
        Public method to convert the given path to an absolute path.

        @param p path to be converted
        @type str
        @return absolute path
        @rtype str
        """
        p = FileSystemUtilities.plainFileName(p)
        if not self.isabs(p):
            p = self.join(self.getcwd(), p)
        return FileSystemUtilities.remoteFileName(p)

    def join(self, a, *p):
        """
        Public method to join two or more path name components using the path separator
        of the server side.

        @param a first path component
        @type str
        @param *p list of additional path components
        @type list of str
        @return joined path name
        @rtype str
        """
        path = a
        for b in p:
            if b.startswith(self.__serverPathSep):
                path = b
            elif not path or path.endswith(self.__serverPathSep):
                path += b
            else:
                path += self.__serverPathSep + b
        return path

    def split(self, p):
        """
        Public method to split a path name.

        @param p path name to be split
        @type str
        @return tuple containing head and tail, where tail is everything after the last
            path separator.
        @rtype tuple of (str, str)
        """
        normp = (
            p.replace("/", "\\")  # remote is a Windows system
            if self.__serverPathSep == "\\"
            else p.replace("\\", "/")  # remote is a Posix system
        )

        i = normp.rfind(self.__serverPathSep) + 1
        head, tail = normp[:i], normp[i:]
        if head and head != self.__serverPathSep * len(head):
            head = head.rstrip(self.__serverPathSep)
        return head, tail

    def splitext(self, p):
        """
        Public method to split a path name into a root part and an extension.

        @param p path name to be split
        @type str
        @return tuple containing the root part and the extension
        @rtype tuple of (str, str)
        """
        return os.path.splitext(p)

    def splitdrive(self, p):
        """
        Public method to split a path into drive and path.

        @param p path name to be split
        @type str
        @return tuple containing the drive letter (incl. colon) and the path
        @rtype tuple of (str, str)
        """
        plainp = FileSystemUtilities.plainFileName(p)

        if self.__serverPathSep == "\\":
            # remote is a Windows system
            normp = plainp.replace("/", "\\")
            if normp[1:2] == ":":
                return normp[:2], normp[2:]
            else:
                return "", normp
        else:
            # remote is a Posix system
            normp = plainp.replace("\\", "/")
            return "", normp

    def dirname(self, p):
        """
        Public method to extract the directory component of a path name.

        @param p path name
        @type str
        @return directory component
        @rtype str
        """
        return self.split(p)[0]

    def basename(self, p):
        """
        Public method to extract the final component of a path name.

        @param p path name
        @type str
        @return final component
        @rtype str
        """
        return self.split(p)[1]

    def toNativeSeparators(self, p):
        """
        Public method to convert a path to use server native separator characters.

        @param p path name to be converted
        @type str
        @return path name with converted separator characters
        @rtype str
        """
        if self.__serverPathSep == "/":
            return p.replace("\\", "/")
        else:
            return p.replace("/", "\\")

    def fromNativeSeparators(self, p):
        """
        Public method to convert a path using server native separator characters to
        use "/" separator characters.

        @param p path name to be converted
        @type str
        @return path name with converted separator characters
        @rtype str
        """
        return p.replace(self.__serverPathSep, "/")

    #######################################################################
    ## Methods for reading and writing files
    #######################################################################

    def readFile(self, filename, create=False, newline=None):
        """
        Public method to read a file from the eric-ide server.

        @param filename name of the file to read
        @type str
        @param create flag indicating to create an empty file, if it does not exist
            (defaults to False)
        @type bool (optional)
        @param newline determines how to parse newline characters from the stream
            (defaults to None)
        @type str (optional)
        @return bytes data read from the eric-ide server
        @rtype bytes
        @exception EricServerNotConnectedError raised to indicate a missing server
            connection
        @exception OSError raised in case the server reported an issue
        """
        loop = QEventLoop()
        ok = False
        error = ""
        bText = b""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error, bText

            if reply == "ReadFile":
                ok = params["ok"]
                if ok:
                    bText = base64.b85decode(
                        bytes(params["filedata"], encoding="ascii")
                    )
                else:
                    error = params["error"]
                loop.quit()

        if not self.__serverInterface.isServerConnected():
            raise EricServerNotConnectedError()

        else:
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="ReadFile",
                params={
                    "filename": FileSystemUtilities.plainFileName(filename),
                    "create": create,
                    "newline": "<<none>>" if newline is None else newline,
                },
                callback=callback,
            )

            loop.exec()
            if not ok:
                raise OSError(error)

            return bText

    def writeFile(self, filename, data, withBackup=False, newline=None):
        """
        Public method to write the data to a file on the eric-ide server.

        @param filename name of the file to write
        @type str
        @param data data to be written
        @type bytes or QByteArray
        @param withBackup flag indicating to create a backup file first
            (defaults to False)
        @type bool (optional)
        @param newline determines how to parse newline characters from the stream
            (defaults to None)
        @type str (optional)
        @exception EricServerNotConnectedError raised to indicate a missing server
            connection
        @exception OSError raised in case the server reported an issue
        """
        loop = QEventLoop()
        ok = False
        error = ""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error

            if reply == "WriteFile":
                ok = params["ok"]
                with contextlib.suppress(KeyError):
                    error = params["error"]
                loop.quit()

        if not self.__serverInterface.isServerConnected():
            raise EricServerNotConnectedError

        else:
            if isinstance(data, QByteArray):
                data = bytes(data)
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="WriteFile",
                params={
                    "filename": FileSystemUtilities.plainFileName(filename),
                    "filedata": str(base64.b85encode(data), encoding="ascii"),
                    "with_backup": withBackup,
                    "newline": "<<none>>" if newline is None else newline,
                },
                callback=callback,
            )

            loop.exec()
            if not ok:
                raise OSError(error)

    def readEncodedFile(self, filename, create=False):
        """
        Public method to read a file and decode its contents into proper text.

        @param filename name of the file to read
        @type str
        @param create flag indicating to create an empty file, if it does not exist
            (defaults to False)
        @type bool (optional)
        @return tuple of decoded text and encoding
        @rtype tuple of (str, str)
        """
        data = self.readFile(filename, create=create)
        return Utilities.decode(data)

    def readEncodedFileWithEncoding(self, filename, encoding, create=False):
        """
        Public method to read a file and decode its contents into proper text.

        @param filename name of the file to read
        @type str
        @param encoding encoding to be used to read the file
        @type str
        @param create flag indicating to create an empty file, if it does not exist
            (defaults to False)
        @type bool (optional)
        @return tuple of decoded text and encoding
        @rtype tuple of (str, str)
        """
        data = self.readFile(filename, create=create)
        return Utilities.decodeWithEncoding(data, encoding)

    def writeEncodedFile(
        self, filename, text, origEncoding, forcedEncoding="", withBackup=False
    ):
        """
        Public method to write a file with properly encoded text.

        @param filename name of the file to read
        @type str
        @param text text to be written
        @type str
        @param origEncoding type of the original encoding
        @type str
        @param forcedEncoding encoding to be used for writing, if no coding
            line is present (defaults to "")
        @type str (optional)
        @param withBackup flag indicating to create a backup file first
            (defaults to False)
        @type bool (optional)
        @return encoding used for writing the file
        @rtype str
        """
        data, encoding = Utilities.encode(
            text, origEncoding, forcedEncoding=forcedEncoding
        )
        self.writeFile(filename, data, withBackup=withBackup)

        return encoding

    #######################################################################
    ## Methods implementing some 'shutil' like functionality.
    #######################################################################

    def shutilCopy(self, srcName, dstName):
        """
        Public method to copy a source file to a given destination file or directory.

        @param srcName name of the source file
        @type str
        @param dstName name of the destination file or directory
        @type str
        @return name of the destination file
        @rtype str
        @exception EricServerNotConnectedError raised to indicate a missing server
            connection
        @exception OSError raised to indicate an issue
        """
        loop = QEventLoop()
        ok = False
        error = ""
        dst = ""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error, dst

            if reply == "ShutilCopy":
                ok = params["ok"]
                if ok:
                    dst = params["dst"]
                else:
                    error = params["error"]
                loop.quit()

        if not self.__serverInterface.isServerConnected():
            raise EricServerNotConnectedError

        else:
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="ShutilCopy",
                params={
                    "src_name": FileSystemUtilities.plainFileName(srcName),
                    "dst_name": FileSystemUtilities.plainFileName(dstName),
                },
                callback=callback,
            )

            loop.exec()
            if not ok:
                raise OSError(error)

            return dst

    def shutilRmtree(self, pathname, ignore_errors=False):
        """
        Public method to delete an entire directory tree.

        @param pathname name of the directory to be deleted
        @type str
        @param ignore_errors flag indicating to ignore error resulting from failed
            removals (defaults to False)
        @type bool (optional)
        @exception EricServerNotConnectedError raised to indicate a missing server
            connection
        @exception OSError raised to indicate an issue
        """
        loop = QEventLoop()
        ok = False
        error = ""

        def callback(reply, params):
            """
            Function to handle the server reply

            @param reply name of the server reply
            @type str
            @param params dictionary containing the reply data
            @type dict
            """
            nonlocal ok, error

            if reply == "ShutilRmtree":
                ok = params["ok"]
                if not ok:
                    error = params["error"]
                loop.quit()

        if not self.__serverInterface.isServerConnected():
            raise EricServerNotConnectedError

        else:
            self.__serverInterface.sendJson(
                category=EricRequestCategory.FileSystem,
                request="ShutilRmtree",
                params={
                    "name": FileSystemUtilities.plainFileName(pathname),
                    "ignore_errors": ignore_errors,
                },
                callback=callback,
            )

            loop.exec()
            if ok:
                self.removeFromFsCache(pathname)

            if not ok:
                raise OSError(error)

    #######################################################################
    ## Utility methods.
    #######################################################################

    def compactPath(self, longPath, width, measure=len):
        """
        Public method to return a compacted path fitting inside the given width.

        @param longPath path to be compacted
        @type str
        @param width width for the compacted path
        @type int
        @param measure reference to a function used to measure the length of the
            string (defaults to len)
        @type function (optional)
        @return compacted path
        @rtype str
        """
        if measure(longPath) <= width:
            return longPath

        ellipsis = "..."

        head, tail = self.split(longPath)
        mid = len(head) // 2
        head1 = head[:mid]
        head2 = head[mid:]
        while head1:
            # head1 is same size as head2 or one shorter
            cpath = self.join(f"{head1}{ellipsis}{head2}", tail)
            if measure(cpath) <= width:
                return cpath
            head1 = head1[:-1]
            head2 = head2[1:]
        cpath = self.join(ellipsis, tail)
        if measure(cpath) <= width:
            return cpath
        remoteMarker = FileSystemUtilities.remoteFileName("")
        if width <= len(remoteMarker):
            return f"{remoteMarker}{ellipsis}{tail}"
        while tail:
            cpath = f"{remoteMarker}{ellipsis}{tail}"
            if measure(cpath) <= width:
                return cpath
            tail = tail[1:]
        return ""

    #######################################################################
    ## Remote file system cache methods.
    #######################################################################

    def populateFsCache(self, directory):
        """
        Public method to populate the remote file system cache for a given directory.

        @param directory remote directory to be cached
        @type str
        @exception ValueError raised to indicate an empty directory
        """
        if not directory:
            raise ValueError("The directory to be cached must not be empty.")

        try:
            listing = self.listdir(directory=directory, recursive=True)[2]
            for entry in listing:
                _RemoteFsCache[FileSystemUtilities.remoteFileName(entry["path"])] = (
                    entry
                )
            logging.getLogger(__name__).debug(
                f"Remote Cache Size: {len(_RemoteFsCache)} entries"
            )
        except OSError as err:
            print("Error in 'populateFsCache()':", str(err))  # noqa: M801

    def removeFromFsCache(self, directory):
        """
        Public method to remove a given directory from the remote file system cache.

        @param directory remote directory to be removed
        @type str
        """
        for entryPath in list(_RemoteFsCache.keys()):
            if entryPath.startswith(directory):
                del _RemoteFsCache[entryPath]
        logging.getLogger(__name__).debug(
            f"Remote Cache Size: {len(_RemoteFsCache)} entries"
        )
