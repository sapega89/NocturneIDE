# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some file system utility functions.
"""

import os
import stat
import time

MPY_EPOCH = time.mktime((2000, 1, 1, 0, 0, 0, 0, 1, -1))
# MPy epoch is 2000-01-01 0:0:0 UTC


def mtime2string(mtime, adjustEpoch=False):
    """
    Function to convert a time value to a string representation.

    @param mtime time value
    @type int
    @param adjustEpoch flag indicating to adjust the time for the difference
        of the MPy epoch (defaults to False)
    @type bool (optional)
    @return string representation of the given time
    @rtype str
    """
    if adjustEpoch:
        mtime += MPY_EPOCH
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(mtime))


def mode2string(mode):
    """
    Function to convert a mode value to a string representation.

    @param mode mode value
    @type int
    @return string representation of the given mode value
    @rtype str
    """
    return stat.filemode(mode)


def decoratedName(name, mode, isDir=False):
    """
    Function to decorate the given name according to the given mode.

    @param name file or directory name
    @type str
    @param mode mode value
    @type int
    @param isDir flag indicating that name is a directory
    @type bool
    @return decorated file or directory name
    @rtype str
    """
    if stat.S_ISDIR(mode) or isDir:
        # append a '/' for directories
        return name + "/"
    elif stat.S_ISLNK(mode):
        # append a '@' for links
        return name + "@"
    else:
        # no change
        return name


def isVisible(name, showHidden):
    """
    Function to check, if a filesystem entry is a hidden file or directory.

    @param name name to be checked
    @type str
    @param showHidden flag indicating to show hidden files as well
    @type bool
    @return flag indicating a visible filesystem entry
    @rtype bool
    """
    return showHidden or (not name.startswith(".") and not name.endswith("~"))


def fstat(filename):
    """
    Function to get the stat() of file.

    @param filename name of the file
    @type str
    @return tuple containing the stat() result
    @rtype tuple
    """
    try:
        rstat = os.lstat(filename)
    except Exception:
        rstat = os.stat(filename)
    return tuple(rstat)


def listdirStat(dirname, showHidden=False):
    """
    Function to get a list of directory entries and associated stat() tuples.

    @param dirname name of the directory to list
    @type str
    @param showHidden flag indicating to show hidden files as well
    @type bool
    @return list of tuples containing the entry name and the associated
        stat() tuple
    @rtype list of tuple of (str, tuple)
    """
    try:
        files = os.listdir(dirname) if dirname else os.listdir()
    except OSError:
        return []

    if dirname:
        return [
            (f, fstat(os.path.join(dirname, f)))
            for f in files
            if isVisible(f, showHidden)
        ]
    else:
        return [(f, fstat(f)) for f in files if isVisible(f, showHidden)]
