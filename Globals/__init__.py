# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module defining common data to be used by all modules.
"""

#
# Note: Do not import any eric stuff in here!!!!!!!
#

import os

from PyQt6.QtCore import QProcess, qVersion

from eric7.EricUtilities import (  # noqa
    dataString,
    getConfigDir,
    setConfigDir,
    strGroup,
    strToQByteArray,
    toBool,
    toByteArray,
    toDict,
    toList,
    versionIsValid,
    versionToTuple,
)
from eric7.SystemUtilities import PythonUtilities

try:
    from eric7.eric7config import getConfig
except ImportError:
    from eric7config import getConfig

# names of the various settings objects
settingsNameOrganization = "Eric7"
settingsNameGlobal = "eric7"
settingsNameRecent = "eric7recent"

# key names of the various recent entries
recentNameBreakpointConditions = "BreakPointConditions"
recentNameBreakpointFiles = "BreakPointFiles"
recentNameFiles = "Files"
recentNameHexFiles = "HexFiles"
recentNameHosts = "Hosts"
recentNameMultiProject = "MultiProjects"
recentNamePdfFiles = "PdfFiles"
recentNameProject = "Projects"
recentNameTestDiscoverHistory = "UTDiscoverHistory"
recentNameTestFileHistory = "UTFileHistory"
recentNameTestNameHistory = "UTTestnameHistory"
recentNameTestFramework = "UTTestFramework"
recentNameTestEnvironment = "UTEnvironmentName"


def getInstallInfoFilePath():
    """
    Public method to get the path name of the install info file.

    @return file path of the install info file
    @rtype str
    """
    filename = "eric7install.{0}.json".format(
        getConfig("ericDir")
        .replace(":", "_")
        .replace("\\", "_")
        .replace("/", "_")
        .replace(" ", "_")
        .strip("_")
    )
    return os.path.join(getConfigDir(), filename)


###############################################################################
## functions for web browser variant detection
###############################################################################


def getWebBrowserSupport():
    """
    Module function to determine the supported web browser variant.

    @return string indicating the supported web browser variant ("QtWebEngine",
        or "None")
    @rtype str
    """
    try:
        from eric7.eric7config import getConfig  # __IGNORE_WARNING_I101__
    except ImportError:
        from eric7config import getConfig  # __IGNORE_WARNING_I10__

    scriptPath = os.path.join(getConfig("ericDir"), "Tools", "webBrowserSupport.py")
    proc = QProcess()
    proc.start(PythonUtilities.getPythonExecutable(), [scriptPath, qVersion()])
    variant = (
        str(proc.readAllStandardOutput(), "utf-8", "replace").strip()
        if proc.waitForFinished(10000)
        else "None"
    )
    return variant


#
# eflag: noqa = M801, U200
