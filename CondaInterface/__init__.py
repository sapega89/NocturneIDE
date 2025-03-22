# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing the various conda related modules.
"""

import json

from PyQt6.QtCore import QCoreApplication, QProcess

from eric7 import Preferences

__CondaVersion = ()
__CondaVersionStr = ""
__CondaRootPrefix = ""
__CondaUserConfig = ""

__initialized = False


def __initializeCondaInterface():
    """
    Private module function to (re-)initialize the conda interface.
    """
    global __CondaVersionStr, __CondaVersion, __CondaRootPrefix
    global __CondaUserConfig, __initialized

    if not __initialized:
        exe = Preferences.getConda("CondaExecutable")
        if not exe:
            exe = "conda"

        proc = QProcess()
        proc.start(exe, ["info", "--json"])
        if not proc.waitForStarted(msecs=15000):
            __CondaVersionStr = QCoreApplication.translate(
                "CondaInterface", "<conda not found or not configured.>"
            )
        else:
            proc.waitForFinished(msecs=15000)
            output = str(
                proc.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            ).strip()
            try:
                jsonDict = json.loads(output)
            except Exception:
                __CondaVersionStr = QCoreApplication.translate(
                    "CondaInterface", "<conda returned invalid data.>"
                )
                return

            if "error" in jsonDict:
                __CondaVersionStr = QCoreApplication.translate(
                    "CondaInterface", "<conda returned an error: {0}.>"
                ).format(jsonDict["error"])
            else:
                __CondaVersionStr = jsonDict["conda_version"]
                __CondaVersion = tuple(int(i) for i in __CondaVersionStr.split("."))
                __CondaRootPrefix = jsonDict["root_prefix"]
                __CondaUserConfig = jsonDict.get("user_rc_path")
                if __CondaUserConfig is None:
                    __CondaUserConfig = jsonDict.get("rc_path")

                __initialized = True


def condaVersion():
    """
    Module function to get the conda version.

    @return tuple containing the conda version
    @rtype tuple of (int, int, int)
    """
    __initializeCondaInterface()
    return __CondaVersion


def condaVersionStr():
    """
    Module function to get the conda version as a string.

    @return conda version as a string
    @rtype str
    """
    __initializeCondaInterface()
    return __CondaVersionStr


def rootPrefix():
    """
    Module function to get the root prefix.

    @return root prefix
    @rtype str
    """
    __initializeCondaInterface()
    return __CondaRootPrefix


def userConfiguration():
    """
    Module function to get the path of the user configuration file.

    @return path of the user configuration file
    @rtype str
    """
    __initializeCondaInterface()
    return __CondaUserConfig


def isCondaAvailable():
    """
    Module function to check the availability of conda.

    @return flag indicating conda availability
    @rtype bool
    """
    __initializeCondaInterface()
    return bool(__CondaVersion)


def resetInterface():
    """
    Module function to reset the conda interface.
    """
    global __initialized

    __initialized = False
