# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing file system related utility functions.
"""

import contextlib
import ctypes
import fnmatch
import os
import pathlib
import shutil
import subprocess  # secok

from eric7.SystemUtilities import OSUtilities


def toNativeSeparators(path):
    """
    Function returning a path, that is using native separator characters.

    @param path path to be converted
    @type str
    @return path with converted separator characters
    @rtype str
    """
    return str(pathlib.PurePath(path)) if bool(path) else ""


def fromNativeSeparators(path):
    """
    Function returning a path, that is using "/" separator characters.

    @param path path to be converted
    @type str
    @return path with converted separator characters
    @rtype str
    """
    return pathlib.PurePath(path).as_posix() if bool(path) else ""


def normcasepath(path):
    """
    Function returning a path, that is normalized with respect to its case
    and references.

    @param path file path
    @type str
    @return case normalized path
    @rtype str
    """
    return os.path.normcase(os.path.normpath(path))


def normcaseabspath(path):
    """
    Function returning an absolute path, that is normalized with respect to
    its case and references.

    @param path file path
    @type str
    @return absolute, normalized path
    @rtype str
    """
    return os.path.normcase(os.path.abspath(path))


def normjoinpath(a, *p):
    """
    Function returning a normalized path of the joined parts passed into it.

    @param a first path to be joined
    @type str
    @param p variable number of path parts to be joined
    @type str
    @return normalized path
    @rtype str
    """
    return os.path.normpath(os.path.join(a, *p))


def normabsjoinpath(a, *p):
    """
    Function returning a normalized, absolute path of the joined parts passed
    into it.

    @param a first path to be joined
    @type str
    @param p variable number of path parts to be joined
    @type str
    @return absolute, normalized path
    @rtype str
    """
    return os.path.abspath(os.path.join(a, *p))


def isinpath(file):
    """
    Function to check for an executable file.

    @param file filename of the executable to check
    @type str
    @return flag indicating, if the executable file is accessible via the executable
        search path defined by the PATH environment variable.
    @rtype bool
    """
    return bool(shutil.which(file))


def startsWithPath(path, start):
    """
    Function to check, if a path starts with a given start path.

    @param path path to be checked
    @type str
    @param start start path
    @type str
    @return flag indicating that the path starts with the given start
        path
    @rtype bool
    """
    start1 = start if start.endswith(os.sep) else f"{start}{os.sep}"
    return bool(start) and (
        path == start or normcasepath(path).startswith(normcasepath(start1))
    )


def relativeUniversalPath(path, start):
    """
    Function to convert a file path to a path relative to a start path
    with universal separators.

    @param path file or directory name to convert
    @type str
    @param start start path
    @type str
    @return relative path or unchanged path, if path does not start with
        the start path with universal separators
    @rtype str
    """
    return fromNativeSeparators(os.path.relpath(path, start))


def absolutePath(path, start):
    """
    Public method to convert a path relative to a start path to an
    absolute path.

    @param path file or directory name to convert
    @type str
    @param start start path
    @type str
    @return absolute path
    @rtype str
    """
    if not os.path.isabs(path):
        path = os.path.normpath(os.path.join(start, path))
    return path


def absoluteUniversalPath(path, start):
    """
    Public method to convert a path relative to a start path with
    universal separators to an absolute path.

    @param path file or directory name to convert
    @type str
    @param start start path
    @type str
    @return absolute path with native separators
    @rtype str
    """
    if not os.path.isabs(path):
        path = toNativeSeparators(os.path.normpath(os.path.join(start, path)))
    return path


def getExecutablePath(file):
    """
    Function to build the full path of an executable file from the environment.

    @param file filename of the executable to check
    @type str
    @return full executable name, if the executable file is accessible
        via the executable search path defined by the PATH environment variable, or an
        empty string otherwise.
    @rtype str
    """
    exe = shutil.which(file)
    return exe if bool(exe) else ""


def getExecutablePaths(file):
    """
    Function to build all full path of an executable file from the environment.

    @param file filename of the executable
    @type str
    @return list of full executable names, if the executable file is accessible via
        the executable search path defined by the PATH environment variable, or an
        empty list otherwise.
    @rtype list of str
    """
    paths = []

    if os.path.isabs(file):
        if os.access(file, os.X_OK):
            return [file]
        else:
            return []

    cur_path = os.path.join(os.curdir, file)
    if os.path.exists(cur_path) and os.access(cur_path, os.X_OK):
        paths.append(cur_path)

    path = os.getenv("PATH")

    # environment variable not defined
    if path is not None:
        dirs = path.split(os.pathsep)
        for directory in dirs:
            exe = os.path.join(directory, file)
            if os.access(exe, os.X_OK) and exe not in paths:
                paths.append(exe)

    return paths


def isExecutable(exe):
    """
    Function to check, if a file is executable.

    @param exe filename of the executable to check
    @type str
    @return flag indicating executable status
    @rtype bool
    """
    return os.access(exe, os.X_OK)


def isDrive(path):
    """
    Function to check, if a path is a Windows drive.

    @param path path name to be checked
    @type str
    @return flag indicating a Windows drive
    @rtype bool
    """
    isWindowsDrive = False
    drive, directory = os.path.splitdrive(path)
    if (
        drive
        and len(drive) == 2
        and drive.endswith(":")
        and directory in ["", "\\", "/"]
    ):
        isWindowsDrive = True

    return isWindowsDrive


def samepath(f1, f2, followSymlinks=True):
    """
    Function to compare two paths.

    @param f1 first filepath for the compare
    @type str
    @param f2 second filepath for the compare
    @type str
    @param followSymlinks flag indicating to respect symbolic links for the comparison
        (i.e. compare the real paths) (defaults to True)
    @type bool (optional)
    @return flag indicating whether the two paths represent the
        same path on disk
    @rtype bool
    """
    if f1 is None or f2 is None:
        return False

    if isPlainFileName(f1) and isPlainFileName(f2):
        if followSymlinks:
            if normcaseabspath(os.path.realpath(f1)) == normcaseabspath(
                os.path.realpath(f2)
            ):
                return True
        else:
            if normcaseabspath(f1) == normcaseabspath(f2):
                return True

    else:
        return f1 == f2

    return False


def samefilepath(f1, f2, followSymlinks=True):
    """
    Function to compare two paths. Strips the filename.

    @param f1 first filepath for the compare
    @type str
    @param f2 second filepath for the compare
    @type str
    @param followSymlinks flag indicating to respect symbolic links for the comparison
        (i.e. compare the real paths) (defaults to True)
    @type bool (optional)
    @return flag indicating whether the two paths represent the
        same path on disk
    @rtype bool
    """
    if f1 is None or f2 is None:
        return False

    if isPlainFileName(f1) and isPlainFileName(f2):
        if followSymlinks:
            if normcaseabspath(
                os.path.dirname(os.path.realpath(f1))
            ) == normcaseabspath(os.path.dirname(os.path.realpath(f2))):
                return True
        else:
            if normcaseabspath(os.path.dirname(f1)) == normcaseabspath(
                os.path.dirname(f2)
            ):
                return True

    else:
        return os.path.dirname(f1) == os.path.dirname(f2)

    return False


try:
    EXTSEP = os.extsep
except AttributeError:
    EXTSEP = "."


def splitPath(name):
    """
    Function to split a pathname into a directory part and a file part.

    @param name path name
    @type str
    @return tuple containing directory name and file name
    @rtype tuple of (str, str)
    """
    if os.path.isdir(name):
        dn = os.path.abspath(name)
        fn = "."
    else:
        dn, fn = os.path.split(name)
    return (dn, fn)


def joinext(prefix, ext):
    """
    Function to join a file extension to a path.

    The leading "." of ext is replaced by a platform specific extension
    separator if necessary.

    @param prefix the basepart of the filename
    @type str
    @param ext the extension part
    @type str
    @return the complete filename
    @rtype str
    """
    if ext[0] != ".":
        ext = ".{0}".format(ext)
        # require leading separator to match os.path.splitext
    return prefix + EXTSEP + ext[1:]


def compactPath(path, width, measure=len):
    """
    Function to return a compacted path fitting inside the given width.

    @param path path to be compacted
    @type str
    @param width width for the compacted path
    @type int
    @param measure reference to a function used to measure the length of the
        string
    @type function(str)
    @return compacted path
    @rtype str
    """
    if measure(path) <= width:
        return path

    ellipsis = "..."

    head, tail = os.path.split(path)
    mid = len(head) // 2
    head1 = head[:mid]
    head2 = head[mid:]
    while head1:
        # head1 is same size as head2 or one shorter
        path = os.path.join("{0}{1}{2}".format(head1, ellipsis, head2), tail)
        if measure(path) <= width:
            return path
        head1 = head1[:-1]
        head2 = head2[1:]
    path = os.path.join(ellipsis, tail)
    if measure(path) <= width:
        return path
    while tail:
        path = "{0}{1}".format(ellipsis, tail)
        if measure(path) <= width:
            return path
        tail = tail[1:]
    return ""


def direntries(
    path,
    filesonly=False,
    pattern=None,
    followsymlinks=True,
    checkStop=None,
    ignore=None,
    recursive=True,
    dirsonly=False,
):
    """
    Function returning a list of all files and directories.

    @param path root of the tree to check
    @type str
    @param filesonly flag indicating that only files are wanted (defaults to False)
    @type bool (optional)
    @param pattern a filename pattern or list of filename patterns to check
        against (defaults to None)
    @type str or list of str (optional)
    @param followsymlinks flag indicating whether symbolic links
        should be followed (defaults to True)
    @type bool (optional)
    @param checkStop function to be called to check for a stop (defaults to None)
    @type function (optional)
    @param ignore list of entries to be ignored (defaults to None)
    @type list of str (optional)
    @param recursive flag indicating a recursive search (defaults to True)
    @type bool (optional)
    @param dirsonly flag indicating to return only directories. When True it has
        precedence over the 'filesonly' parameter ((defaults to False)
    @type bool
    @return list of all files and directories in the tree rooted
        at path. The names are expanded to start with path.
    @rtype list of str
    """
    patterns = pattern if isinstance(pattern, list) else [pattern]
    files = [] if (filesonly and not dirsonly) else [path]
    ignoreList = [
        ".svn",
        ".hg",
        ".git",
        ".ropeproject",
        ".eric7project",
        ".jedi",
        "__pycache__",
    ]
    if ignore is not None:
        ignoreList.extend(ignore)

    with contextlib.suppress(OSError, UnicodeDecodeError), os.scandir(
        path
    ) as dirEntriesIterator:
        for dirEntry in dirEntriesIterator:
            if checkStop and checkStop():
                break

            if dirEntry.name in ignoreList:
                continue

            if (
                pattern
                and not dirEntry.is_dir()
                and not any(fnmatch.fnmatch(dirEntry.name, p) for p in patterns)
            ):
                # entry doesn't fit the given pattern
                continue

            if dirEntry.is_dir():
                if dirEntry.path in ignoreList or (
                    dirEntry.is_symlink() and not followsymlinks
                ):
                    continue
                if recursive:
                    files += direntries(
                        dirEntry.path,
                        filesonly=filesonly,
                        pattern=pattern,
                        followsymlinks=followsymlinks,
                        checkStop=checkStop,
                        ignore=ignore,
                    )
                elif dirsonly:
                    files.append(dirEntry.path)
            else:
                files.append(dirEntry.path)
    return files


def getDirs(path, excludeDirs):
    """
    Function returning a list of all directories below path.

    @param path root of the tree to check
    @type str
    @param excludeDirs base name of directories to ignore
    @type list of str
    @return list of all directories found
    @rtype list of str
    """
    try:
        dirs = []
        with os.scandir(path) as dirEntriesIterator:
            for dirEntry in dirEntriesIterator:
                if (
                    dirEntry.is_dir()
                    and not dirEntry.is_symlink()
                    and dirEntry.name not in excludeDirs
                ):
                    dirs.append(dirEntry.path)
                    dirs.extend(getDirs(dirEntry.path, excludeDirs))
        return dirs
    except OSError:
        return []


def findVolume(volumeName, findAll=False):
    """
    Function to find the directory belonging to a given volume name.

    @param volumeName name of the volume to search for
    @type str
    @param findAll flag indicating to get the directories for all volumes
        starting with the given name (defaults to False)
    @type bool (optional)
    @return directory path or list of directory paths for the given volume
        name
    @rtype str or list of str
    """
    volumeDirectories = []
    volumeDirectory = None

    if OSUtilities.isWindowsPlatform():
        # we are on a Windows platform
        def getVolumeName(diskName):
            """
            Local function to determine the volume of a disk or device.

            Each disk or external device connected to windows has an
            attribute called "volume name". This function returns the
            volume name for the given disk/device.

            Code from http://stackoverflow.com/a/12056414
            """
            volumeNameBuffer = ctypes.create_unicode_buffer(1024)
            ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(diskName),
                volumeNameBuffer,
                ctypes.sizeof(volumeNameBuffer),
                None,
                None,
                None,
                None,
                0,
            )
            return volumeNameBuffer.value

        #
        # In certain circumstances, volumes are allocated to USB
        # storage devices which cause a Windows popup to raise if their
        # volume contains no media. Wrapping the check in SetErrorMode
        # with SEM_FAILCRITICALERRORS (1) prevents this popup.
        #
        oldMode = ctypes.windll.kernel32.SetErrorMode(1)
        try:
            for disk in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                dirpath = "{0}:\\".format(disk)
                if os.path.exists(dirpath):
                    if findAll:
                        if getVolumeName(dirpath).startswith(volumeName):
                            volumeDirectories.append(dirpath)
                    else:
                        if getVolumeName(dirpath) == volumeName:
                            volumeDirectory = dirpath
                            break
        finally:
            ctypes.windll.kernel32.SetErrorMode(oldMode)
    else:
        # we are on a Linux, FreeBSD or macOS platform
        for mountCommand in ["mount", "/sbin/mount", "/usr/sbin/mount"]:
            with contextlib.suppress(FileNotFoundError):
                mountOutput = subprocess.run(  # secok
                    mountCommand, check=True, capture_output=True, text=True
                ).stdout.splitlines()
                mountedVolumes = [
                    x.split(" type", 1)[0].split(" (", 1)[0].split(maxsplit=2)[-1]
                    for x in mountOutput
                ]
                if findAll:
                    for volume in mountedVolumes:
                        if os.path.basename(volume).startswith(volumeName):
                            volumeDirectories.append(volume)
                    if volumeDirectories:
                        break
                else:
                    for volume in mountedVolumes:
                        if os.path.basename(volume) == volumeName:
                            volumeDirectory = volume
                            break
                    if volumeDirectory:
                        break

    if findAll:
        return volumeDirectories
    else:
        return volumeDirectory


def getUserMounts():
    """
    Function to determine all available user mounts.

    Note: On Windows platforms all available drives are returned.

    @return list of user mounts or drives
    @rtype list of str
    """
    mountedPaths = []

    if OSUtilities.isWindowsPlatform():
        # we are on a Windows platform
        for disk in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            dirpath = "{0}:\\".format(disk)
            if os.path.exists(dirpath):
                mountedPaths.append(dirpath)
    else:
        # we are on a Linux, FreeBSD or macOS platform
        if OSUtilities.isMacPlatform():
            # macOS
            mountPathStart = "/Volumes/"
        elif OSUtilities.isLinuxPlatform():
            # Linux
            mountPathStart = "/media/{0}/".format(OSUtilities.getUserName())
        elif OSUtilities.isFreeBsdPlatform():
            # FreeBSD
            mountPathStart = "/media/"
        else:
            # unsupported platform
            return []

        for mountCommand in ["mount", "/sbin/mount", "/usr/sbin/mount"]:
            with contextlib.suppress(FileNotFoundError):
                mountOutput = subprocess.run(  # secok
                    mountCommand, check=True, capture_output=True, text=True
                ).stdout.splitlines()
                mounts = [
                    x.split(" type", 1)[0].split(" (", 1)[0].split(maxsplit=2)[-1]
                    for x in mountOutput
                ]
                mountedPaths = [x for x in mounts if x.startswith(mountPathStart)]
                break

    return mountedPaths


def startfile(filePath):
    """
    Function to open the given file path with the system default application.

    @param filePath file path to be opened
    @type str or Path
    @return flag indicating a successful start of the associated application
    @rtype bool
    """
    filePath = str(filePath)

    with contextlib.suppress(OSError):
        if OSUtilities.isWindowsPlatform():
            os.startfile(filePath)  # secok
            return True

        elif OSUtilities.isMacPlatform():
            return subprocess.call(("open", filePath)) == 0  # secok

        elif OSUtilities.isLinuxPlatform() or OSUtilities.isFreeBsdPlatform():
            return subprocess.call(("xdg-open", filePath)) == 0  # secok

    # unsupported platform or OSError
    return False


################################################################################
## Functions below handle (MicroPython) device and remote file names.
################################################################################


_DeviceFileMarker = "device::"
_RemoteFileMarker = "remote::"


def deviceFileName(fileName):
    """
    Function to create a device (MicroPython) file name given a plain file name.

    @param fileName plain file name
    @type str
    @return device file name
    @rtype str
    """
    if fileName.startswith(_DeviceFileMarker):
        # it is already a device file name
        return fileName
    else:
        return f"{_DeviceFileMarker}{fileName}"


def isDeviceFileName(fileName):
    """
    Function to check, if the given file name is a device file name.

    @param fileName file name to be checked
    @type str
    @return flag indicating a device file name
    @rtype bool
    """
    return fileName.startswith(_DeviceFileMarker)


def remoteFileName(fileName):
    """
    Function to create a remote file name given a plain file name.

    @param fileName plain file name
    @type str
    @return remote file name
    @rtype str
    """
    if fileName.startswith(_RemoteFileMarker):
        # it is already a remote file name
        return fileName
    else:
        return f"{_RemoteFileMarker}{fileName}"


def isRemoteFileName(fileName):
    """
    Function to check, if the given file name is a remote file name.

    @param fileName file name to be checked
    @type str
    @return flag indicating a remote file name
    @rtype bool
    """
    return fileName.startswith(_RemoteFileMarker)


def isPlainFileName(fileName):
    """
    Function to check, if the given file name is a plain (i.e. local) file name.

    @param fileName file name to be checked
    @type str
    @return flag indicating a local file name
    @rtype bool
    """
    return not fileName.startswith((_DeviceFileMarker, _RemoteFileMarker))


def plainFileName(fileName):
    """
    Function to create a plain file name given a device or remote file name.

    @param fileName device or remote file name
    @type str
    @return plain file name
    @rtype str
    """
    return fileName.replace(_DeviceFileMarker, "").replace(_RemoteFileMarker, "")
