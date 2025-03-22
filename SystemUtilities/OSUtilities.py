# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing Operating System related utility functions.
"""

import contextlib
import ctypes
import getpass
import os
import sys

with contextlib.suppress(ImportError):
    import pwd  # only available on Unix systems


###############################################################################
## functions for platform handling
###############################################################################


def isWindowsPlatform():
    """
    Function to check, if this is a Windows platform.

    @return flag indicating Windows platform
    @rtype bool
    """
    return sys.platform.startswith(("win", "cygwin"))


def isMacPlatform():
    """
    Function to check, if this is a Mac platform.

    @return flag indicating Mac platform
    @rtype bool
    """
    return sys.platform == "darwin"


def isLinuxPlatform():
    """
    Function to check, if this is a Linux platform.

    @return flag indicating Linux platform
    @rtype bool
    """
    return sys.platform.startswith("linux")


def isFreeBsdPlatform():
    """
    Function to check, if this is a BSD (FreeBSD) platform.

    @return flag indicating BSD platform
    @rtype bool
    """
    return sys.platform.startswith("freebsd")


###############################################################################
## functions for user handling
###############################################################################


def getUserName():
    """
    Function to get the user name.

    @return user name
    @rtype str
    """
    user = getpass.getuser()

    if isWindowsPlatform() and not user:
        return win32_GetUserName()

    return user


def getRealName():
    """
    Function to get the real name of the user.

    @return real name of the user
    @rtype str
    """
    if isWindowsPlatform():
        return win32_getRealName()
    else:
        user = getpass.getuser()
        return pwd.getpwnam(user).pw_gecos


def getHomeDir():
    """
    Function to get a users home directory.

    @return home directory
    @rtype str
    """
    return os.path.expanduser("~")


###############################################################################
## functions for environment handling
###############################################################################


def getEnvironmentEntry(key, default=None):
    """
    Module function to get an environment entry.

    @param key key of the requested environment entry
    @type str
    @param default value to be returned, if the environment doesn't contain the
        requested entry
    @type str
    @return the requested entry or the default value, if the entry wasn't found
    @rtype str
    """
    if key in os.environ:
        entryKey = key
    elif isWindowsPlatform() and key.lower() in os.environ:
        entryKey = key.lower()
    else:
        return default

    return os.environ[entryKey].strip()


def hasEnvironmentEntry(key):
    """
    Module function to check, if the environment contains an entry.

    @param key key of the requested environment entry
    @type str
    @return flag indicating the presence of the requested entry
    @rtype bool
    """
    return key in os.environ or (isWindowsPlatform() and key.lower() in os.environ)


###############################################################################
## posix compatibility functions below
###############################################################################

# None right now

###############################################################################
## win32 compatibility functions below
###############################################################################


def win32_Kill(pid):
    """
    Function to provide an os.kill equivalent for Win32.

    @param pid process id
    @type int
    @return result of the kill
    @rtype bool
    """
    import win32api  # __IGNORE_WARNING_I102__

    handle = win32api.OpenProcess(1, 0, pid)
    return 0 != win32api.TerminateProcess(handle, 0)


def win32_GetUserName():
    """
    Function to get the user name under Win32.

    @return user name
    @rtype str
    """
    try:
        import win32api  # __IGNORE_WARNING_I10__

        return win32api.GetUserName()
    except ImportError:
        try:
            u = getEnvironmentEntry("USERNAME")
        except KeyError:
            u = getEnvironmentEntry("username", None)
        return u


def win32_getRealName():
    """
    Function to get the user's real name (aka. display name) under Win32.

    @return real name of the current user
    @rtype str
    """
    GetUserNameEx = ctypes.windll.secur32.GetUserNameExW
    NameDisplay = 3

    size = ctypes.pointer(ctypes.c_ulong(0))
    GetUserNameEx(NameDisplay, None, size)

    nameBuffer = ctypes.create_unicode_buffer(size.contents.value)
    GetUserNameEx(NameDisplay, nameBuffer, size)
    return nameBuffer.value
