# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing Qt/PyQt/PySide related utility functions.
"""

import contextlib
import os
import sys
import sysconfig

from PyQt6.QtCore import QT_VERSION, QDir, QLibraryInfo, QProcess

from eric7.EricWidgets.EricApplication import ericApp
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities, PythonUtilities

try:
    from eric7.eric7config import getConfig
except ImportError:
    from eric7config import getConfig

###############################################################################
## Qt utility functions below
###############################################################################


def qVersionTuple():
    """
    Module function to get the Qt version as a tuple.

    @return Qt version as a tuple
    @rtype tuple of int
    """
    return (
        (QT_VERSION & 0xFF0000) >> 16,
        (QT_VERSION & 0xFF00) >> 8,
        QT_VERSION & 0xFF,
    )


def generateQtToolName(toolname):
    """
    Module function to generate the executable name for a Qt tool like
    designer.

    @param toolname base name of the tool
    @type str
    @return the Qt tool name without extension
    @rtype str
    """
    from eric7 import Preferences

    return "{0}{1}{2}".format(
        Preferences.getQt("QtToolsPrefix"),
        toolname,
        Preferences.getQt("QtToolsPostfix"),
    )


def getQtBinariesPath(libexec=False):
    """
    Module function to get the path of the Qt binaries.

    @param libexec flag indicating to get the path of the executable library
        (defaults to False)
    @type bool (optional)
    @return path of the Qt binaries
    @rtype str
    """
    from eric7 import Preferences

    binPath = ""

    # step 1: check, if the user has configured a tools path
    qtToolsDir = Preferences.getQt("QtToolsDir")
    if qtToolsDir:
        if libexec:
            binPath = os.path.join(qtToolsDir, "..", "libexec")
            if not os.path.exists(binPath):
                binPath = os.path.join(qtToolsDir, "libexec")
                if not os.path.exists(binPath):
                    binPath = qtToolsDir
        else:
            binPath = os.path.join(qtToolsDir, "bin")
            if not os.path.exists(binPath):
                binPath = qtToolsDir
        if not os.path.exists(binPath):
            binPath = ""

    # step 2: try the qt6_applications package
    if not binPath:
        with contextlib.suppress(ImportError):
            # if qt6-applications is not installed just go to the next step
            import qt6_applications  # __IGNORE_WARNING_I10__

            if libexec:
                binPath = os.path.join(
                    os.path.dirname(qt6_applications.__file__), "Qt", "libexec"
                )
                if not os.path.exists(binPath):
                    binPath = os.path.join(
                        os.path.dirname(qt6_applications.__file__), "Qt", "bin"
                    )
            else:
                binPath = os.path.join(
                    os.path.dirname(qt6_applications.__file__), "Qt", "bin"
                )
            if not os.path.exists(binPath):
                binPath = ""

    # step3: determine via QLibraryInfo
    if not binPath:
        binPath = (
            QLibraryInfo.path(QLibraryInfo.LibraryPath.LibraryExecutablesPath)
            if libexec
            else QLibraryInfo.path(QLibraryInfo.LibraryPath.BinariesPath)
        )
        if not os.path.exists(binPath):
            binPath = ""

    # step 4: determine from used Python interpreter (designer is test object)
    if not binPath:
        program = "designer"
        if OSUtilities.isWindowsPlatform():
            program += ".exe"

        progPath = os.path.join(PythonUtilities.getPythonScriptsDirectory(), program)
        if os.path.exists(progPath):
            binPath = PythonUtilities.getPythonScriptsDirectory()

    return QDir.toNativeSeparators(binPath)


def getQtMacBundle(toolname):
    """
    Module function to determine the correct Mac OS X bundle name for Qt tools.

    @param toolname  plain name of the tool (e.g. "designer")
    @type str
    @return bundle name of the Qt tool
    @rtype str
    """
    qtDir = getQtBinariesPath()
    bundles = [
        os.path.join(qtDir, "bin", generateQtToolName(toolname.capitalize())) + ".app",
        os.path.join(qtDir, "bin", generateQtToolName(toolname)) + ".app",
        os.path.join(qtDir, generateQtToolName(toolname.capitalize())) + ".app",
        os.path.join(qtDir, generateQtToolName(toolname)) + ".app",
    ]
    if toolname == "designer":
        # support the standalone Qt Designer installer from
        # https://build-system.fman.io/qt-designer-download
        designer = "Qt Designer.app"
        bundles.extend(
            [
                os.path.join(qtDir, "bin", designer),
                os.path.join(qtDir, designer),
            ]
        )
    for bundle in bundles:
        if os.path.exists(bundle):
            return bundle
    return ""


def prepareQtMacBundle(toolname, args):
    """
    Module function for starting Qt tools that are Mac OS X bundles.

    @param toolname  plain name of the tool (e.g. "designer")
    @type str
    @param args    name of input file for tool, if any
    @type list of str
    @return command-name and args for QProcess
    @rtype tuple of (str, list of str)
    """
    fullBundle = getQtMacBundle(toolname)
    if fullBundle == "":
        return ("", [])

    newArgs = []
    newArgs.append("-a")
    newArgs.append(fullBundle)
    if args:
        newArgs.append("--args")
        newArgs += args

    return ("open", newArgs)


def hasQtDesigner():
    """
    Function to check for the availabilility of Qt-Designer tool.

    @return flag indicating the availability of the Qt-Designer tool
    @rtype bool
    """
    if OSUtilities.isWindowsPlatform():
        designerExe = os.path.join(
            getQtBinariesPath(),
            "{0}.exe".format(generateQtToolName("designer")),
        )
    elif OSUtilities.isMacPlatform():
        designerExe = getQtMacBundle("designer")
    else:
        designerExe = os.path.join(
            getQtBinariesPath(),
            generateQtToolName("designer"),
        )
    return os.path.exists(designerExe)


def hasQtLinguist():
    """
    Function to check for the availabilility of Qt-Linguist tool.

    @return flag indicating the availability of the Qt-Linguist tool
    @rtype bool
    """
    if OSUtilities.isWindowsPlatform():
        linguistExe = os.path.join(
            getQtBinariesPath(),
            "{0}.exe".format(generateQtToolName("linguist")),
        )
    elif OSUtilities.isMacPlatform():
        linguistExe = getQtMacBundle("linguist")
    else:
        linguistExe = os.path.join(
            getQtBinariesPath(),
            generateQtToolName("linguist"),
        )
    return os.path.exists(linguistExe)


###############################################################################
## PyQt utility functions below
###############################################################################


def getPyQt6ModulesDirectory():
    """
    Function to determine the path to PyQt6 modules directory.

    @return path to the PyQt6 modules directory
    @rtype str
    """
    pyqtPath = os.path.join(sysconfig.get_path("platlib"), "PyQt6")
    if os.path.exists(pyqtPath):
        return pyqtPath

    return ""


def getPyQtToolsPath(version=5):
    """
    Module function to get the path of the PyQt tools.

    @param version PyQt major version
    @type int
    @return path to the PyQt tools
    @rtype str
    """
    from eric7 import Preferences
    from eric7.EricWidgets.EricApplication import ericApp

    toolsPath = ""

    # step 1: check, if the user has configured a tools path
    if version == 5:
        toolsPath = Preferences.getQt("PyQtToolsDir")
        venvName = Preferences.getQt("PyQtVenvName")
    elif version == 6:
        toolsPath = Preferences.getQt("PyQt6ToolsDir")
        venvName = Preferences.getQt("PyQt6VenvName")

    # step 2: determine from used Python interpreter (pylupdate is test object)
    if not toolsPath:
        program = "pylupdate{0}".format(version)
        if venvName:
            venvManager = ericApp().getObject("VirtualEnvManager")
            dirName = venvManager.getVirtualenvDirectory(venvName)
        else:
            dirName = os.path.dirname(sys.executable)

        if OSUtilities.isWindowsPlatform():
            program += ".exe"
            if os.path.exists(os.path.join(dirName, program)):
                toolsPath = dirName
            elif os.path.exists(os.path.join(dirName, "Scripts", program)):
                toolsPath = os.path.join(dirName, "Scripts")
        else:
            if os.path.exists(os.path.join(dirName, program)):
                toolsPath = dirName
            elif os.path.exists(os.path.join(dirName, "bin", program)):
                toolsPath = os.path.join(dirName, "bin")

    return toolsPath


def generatePyQtToolPath(toolname, alternatives=None):
    """
    Module function to generate the executable path for a PyQt tool.

    @param toolname base name of the tool
    @type str
    @param alternatives list of alternative tool names to try
    @type list of str
    @return executable path name of the tool
    @rtype str
    """
    pyqtVariant = int(toolname[-1])
    pyqtToolsPath = getPyQtToolsPath(pyqtVariant)
    if pyqtToolsPath:
        exe = os.path.join(pyqtToolsPath, toolname)
        if OSUtilities.isWindowsPlatform():
            exe += ".exe"
    else:
        exe = toolname

    exePath = FileSystemUtilities.getExecutablePath(exe)
    if not exePath and alternatives:
        ex_ = generatePyQtToolPath(alternatives[0], alternatives[1:])
        exePath = FileSystemUtilities.getExecutablePath(ex_)

    return exePath


###############################################################################
## PySide2/PySide6 utility functions below
###############################################################################


def generatePySideToolPath(toolname, variant=2):
    """
    Module function to generate the executable path for a PySide2/PySide6 tool.

    @param toolname base name of the tool
    @type str
    @param variant indicator for the PySide variant
    @type int or str
    @return the PySide2/PySide6 tool path with extension
    @rtype str
    """
    from eric7 import Preferences

    if OSUtilities.isWindowsPlatform():
        hasPyside = checkPyside(variant)
        if not hasPyside:
            return ""

        venvName = Preferences.getQt("PySide{0}VenvName".format(variant))
        if not venvName:
            venvName = Preferences.getDebugger("Python3VirtualEnv")
        interpreter = (
            ericApp().getObject("VirtualEnvManager").getVirtualenvInterpreter(venvName)
        )
        if interpreter == "" or not FileSystemUtilities.isinpath(interpreter):
            interpreter = PythonUtilities.getPythonExecutable()
        prefix = os.path.dirname(interpreter)
        if not prefix.endswith("Scripts"):
            prefix = os.path.join(prefix, "Scripts")
        return os.path.join(prefix, toolname + ".exe")
    else:
        # step 1: check, if the user has configured a tools path
        path = Preferences.getQt("PySide{0}ToolsDir".format(variant))
        if path:
            return os.path.join(path, toolname)

        # step 2: determine from used Python interpreter
        dirName = os.path.dirname(sys.executable)
        if os.path.exists(os.path.join(dirName, toolname)):
            return os.path.join(dirName, toolname)

        return toolname


def checkPyside(variant=2):
    """
    Module function to check the presence of PySide2/PySide6.

    @param variant indicator for the PySide variant
    @type int or str
    @return flags indicating the presence of PySide2/PySide6
    @rtype bool
    """
    from eric7 import Preferences

    venvName = Preferences.getQt("PySide{0}VenvName".format(variant))
    if not venvName:
        venvName = Preferences.getDebugger("Python3VirtualEnv")
    interpreter = (
        ericApp().getObject("VirtualEnvManager").getVirtualenvInterpreter(venvName)
    )
    if interpreter == "" or not FileSystemUtilities.isinpath(interpreter):
        interpreter = PythonUtilities.getPythonExecutable()

    checker = os.path.join(getConfig("ericDir"), "SystemUtilities", "PySideImporter.py")
    args = [checker, "--variant={0}".format(variant)]
    proc = QProcess()
    proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
    proc.start(interpreter, args)
    finished = proc.waitForFinished(30000)
    return finished and proc.exitCode() == 0
