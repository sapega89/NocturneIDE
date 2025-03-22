# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the file system request handler of the eric-ide server.
"""

import base64
import contextlib
import os
import shutil
import stat
import time

from eric7.SystemUtilities import FileSystemUtilities

from .EricRequestCategory import EricRequestCategory
from .EricServerBaseRequestHandler import EricServerBaseRequestHandler


class EricServerFileSystemRequestHandler(EricServerBaseRequestHandler):
    """
    Class implementing the file system request handler of the eric-ide server.
    """

    def __init__(self, server):
        """
        Constructor

        @param server reference to the eric-ide server object
        @type EricServer
        """
        super().__init__(server)

        self._category = EricRequestCategory.FileSystem

        self._requestMethodMapping = {
            "GetPathSep": self.__getPathSeparator,
            "Chdir": self.__chdir,
            "Getcwd": self.__getcwd,
            "Listdir": self.__listdir,
            "Mkdir": self.__mkdir,
            "MakeDirs": self.__makedirs,
            "Rmdir": self.__rmdir,
            "Replace": self.__replace,
            "Remove": self.__remove,
            "Stat": self.__stat,
            "Exists": self.__exists,
            "Access": self.__access,
            "ReadFile": self.__readFile,
            "WriteFile": self.__writeFile,
            "DirEntries": self.__dirEntries,
            "ExpandUser": self.__expanduser,
            "ShutilCopy": self.__shutilCopy,
            "ShutilRmtree": self.__shutilRmtree,
        }

    def sendError(self, request, reqestUuid=""):
        """
        Public method to send an error report to the IDE.

        @param request request name
        @type str
        @param reqestUuid UUID of the associated request as sent by the eric IDE
            (defaults to "", i.e. no UUID received)
        @type str
        """
        self._server.sendJson(
            category=self._category,
            reply=request,
            params={
                "ok": False,
                "error": f"Request type '{request}' is not supported.",
                "info": list(self._requestMethodMapping.keys()),
            },
            reqestUuid=reqestUuid,
        )

    ############################################################################
    ## File system related methods below
    ############################################################################

    def __getPathSeparator(self, params):  # noqa: U100
        """
        Private method to report the path separator.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        return {"separator": os.sep}

    def __chdir(self, params):
        """
        Private method to change the current working directory.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        try:
            os.chdir(params["directory"])
            return {"ok": True}
        except OSError as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __getcwd(self, params):  # noqa: U100
        """
        Private method to report the current working directory.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        return {"directory": os.getcwd()}

    def __listdir(self, params):
        """
        Private method to report a directory listing.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        directory = params["directory"]
        if not directory:
            directory = os.getcwd()

        try:
            listing = self.__scanDirectory(directory, params["recursive"])

            return {
                "ok": True,
                "directory": directory,
                "listing": listing,
                "separator": os.sep,
            }
        except OSError as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __scanDirectory(self, directory, recursive, withHidden=False):
        """
        Private method to scan a given directory.

        @param directory path of the directory to be scanned
        @type str
        @param recursive flag indicating a recursive scan
        @type bool
        @param withHidden flag indicating to list hidden files and directories
            as well (defaults to False)
        @type bool (optional)
        @return list of file and directory entries
        @rtype list of dict
        """
        listing = []
        for dirEntry in os.scandir(directory):
            filestat = dirEntry.stat()
            if withHidden or not dirEntry.name.startswith("."):
                entry = {
                    "name": dirEntry.name,
                    "path": dirEntry.path,
                    "is_dir": dirEntry.is_dir(),
                    "is_file": dirEntry.is_file(),
                    "is_link": dirEntry.is_symlink(),
                    "mode": filestat.st_mode,
                    "mode_str": stat.filemode(filestat.st_mode),
                    "size": filestat.st_size,
                    "mtime": filestat.st_mtime,
                    "mtime_str": time.strftime(
                        "%Y-%m-%d %H:%M:%S", time.localtime(filestat.st_mtime)
                    ),
                }
                listing.append(entry)

                if entry["is_dir"] and recursive:
                    listing += self.__scanDirectory(dirEntry.path, recursive)

        return listing

    def __stat(self, params):
        """
        Private method to get the status of a file.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        try:
            result = os.stat(params["filename"])
            resultDict = {st: getattr(result, st) for st in params["st_names"]}
            return {"ok": True, "result": resultDict}
        except OSError as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __exists(self, params):
        """
        Private method to check if a file or directory of the given name exists.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        return {"exists": os.path.exists(params["name"])}

    def __access(self, params):
        """
        Private method to test, if the eric-ide server has the given access rights
        to a file or directory..

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        mode = os.F_OK
        for modeStr in params["modes"]:
            if modeStr == "read":
                mode |= os.R_OK
            elif modeStr == "write":
                mode |= os.W_OK
            elif modeStr in ("execute", "exec"):
                mode |= os.X_OK

        return {"ok": os.access(params["name"], mode)}

    def __mkdir(self, params):
        """
        Private method to create a new directory.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        try:
            mode = params["mode"]
        except KeyError:
            mode = 0o777
        try:
            os.mkdir(params["directory"], mode=mode)
            return {"ok": True}
        except OSError as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __makedirs(self, params):
        """
        Private method to create a new directory.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        try:
            os.makedirs(params["directory"], exist_ok=params["exist_ok"])
            return {"ok": True}
        except OSError as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __rmdir(self, params):
        """
        Private method to delete a directory.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        try:
            os.rmdir(params["directory"])
            return {"ok": True}
        except OSError as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __replace(self, params):
        """
        Private method to replace (rename) a file or directory.


        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        try:
            os.replace(params["old_name"], params["new_name"])
            return {"ok": True}
        except OSError as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __remove(self, params):
        """
        Private method to delete a file.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        try:
            os.remove(params["filename"])
            return {"ok": True}
        except OSError as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __readFile(self, params):
        """
        Private method to read the contents of a file.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        filename = params["filename"]

        if params["create"] and not os.path.exists(filename):
            with open(filename, "wb"):
                pass

        newline = None if params["newline"] == "<<none>>" else params["newline"]
        try:
            with open(filename, "rb", newline=newline) as f:
                data = f.read()
            return {
                "ok": True,
                "filedata": str(base64.b85encode(data), encoding="ascii"),
            }
        except OSError as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __writeFile(self, params):
        """
        Private method to write data into a file.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        filename = params["filename"]
        data = base64.b85decode(bytes(params["filedata"], encoding="ascii"))

        # 1. create backup file if asked for
        if params["with_backup"]:
            if os.path.islink(filename):
                filename = os.path.realpath(filename)
            backupFilename = "{0}~".format(filename)
            try:
                permissions = os.stat(filename).st_mode
                perms_valid = True
            except OSError:
                # if there was an error, ignore it
                perms_valid = False
            with contextlib.suppress(OSError):
                os.remove(backupFilename)
            with contextlib.suppress(OSError):
                os.rename(filename, backupFilename)

        # 2. write the data to the file and reset the permissions
        newline = None if params["newline"] == "<<none>>" else params["newline"]
        if newline is None:
            mode = "wb"
        else:
            mode = "w"
            data = data.decode("utf-8")
        try:
            with open(filename, mode, newline=newline) as f:
                f.write(data)
            if params["with_backup"] and perms_valid:
                os.chmod(filename, permissions)
            return {"ok": True}
        except OSError as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __dirEntries(self, params):
        """
        Private method to get a list of all files and directories of a given directory.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        directory = params["directory"]
        result = FileSystemUtilities.direntries(
            directory,
            filesonly=params["files_only"],
            pattern=params["pattern"],
            followsymlinks=params["follow_symlinks"],
            ignore=params["ignore"],
            recursive=params["recursive"],
            dirsonly=params["dirs_only"],
        )
        return {
            "ok": True,
            "result": result,
        }

    def __expanduser(self, params):
        """
        Private method to replace an initial component of ~ or ~user replaced.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        return {
            "ok": True,
            "name": os.path.expanduser(params["name"]),
        }

    def __shutilCopy(self, params):
        """
        Private method to copy a source file to a destination file or directory.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        try:
            return {
                "ok": True,
                "dst": shutil.copy(params["src_name"], params["dst_name"]),
            }
        except OSError as err:
            return {
                "ok": False,
                "error": str(err),
            }

    def __shutilRmtree(self, params):
        """
        Private method to delete an entire directory tree.

        @param params dictionary containing the request data
        @type dict
        @return dictionary containing the reply data
        @rtype dict
        """
        try:
            shutil.rmtree(params["name"], params["ignore_errors"])
            return {"ok": True}
        except OSError as err:
            return {
                "ok": False,
                "error": str(err),
            }
