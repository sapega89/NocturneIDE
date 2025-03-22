# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing Python related utility functions.
"""

import contextlib
import os
import platform
import sys
import sysconfig

from .OSUtilities import isWindowsPlatform


def getPythonExecutable():
    """
    Function to determine the path of the (non-windowed) Python executable.

    @return path of the Python executable
    @rtype str
    """
    if sys.platform.startswith(("linux", "freebsd")):
        return sys.executable
    elif sys.platform == "darwin":
        return sys.executable.replace("pythonw", "python")
    else:
        return sys.executable.replace("pythonw.exe", "python.exe")


def getPythonLibraryDirectory():
    """
    Function to determine the path to Python's library directory.

    @return path to the Python library directory
    @rtype str
    """
    return sysconfig.get_path("platlib")


def getPythonScriptsDirectory():
    """
    Function to determine the path to Python's scripts directory.

    @return path to the Python scripts directory
    @rtype str
    """
    return sysconfig.get_path("scripts")


def getPythonLibPath():
    """
    Function to determine the path to Python's library.

    @return path to the Python library
    @rtype str
    """
    return sysconfig.get_path("platstdlib")


def getPythonVersion():
    """
    Function to get the Python version (major, minor) as an integer value.

    @return integer representing major and minor version number
    @rtype int
    """
    return sys.hexversion >> 16


def isPythonSource(filename, source, editor=None):
    """
    Function to check for a Python source code file.

    @param filename name of the file with extension
    @type str
    @param source of the file
    @type str
    @param editor reference to the editor, if the file is opened already
        (defaults to None)
    @type Editor (optional)
    @return flag indicating Python source code
    @rtype bool
    """
    from eric7 import Preferences, Utilities
    from eric7.EricWidgets.EricApplication import ericApp

    pythonEquivalents = ("Cython", "MicroPython", "Python3")

    if not editor:
        viewManager = ericApp().getObject("ViewManager")
        editor = viewManager.getOpenEditor(filename)

    # Maybe the user has changed the language
    if editor and editor.getFileType() in pythonEquivalents:
        return True

    if filename:
        if not source and os.path.exists(filename):
            source = Utilities.readEncodedFile(filename)[0]
        flags = Utilities.extractFlags(source)
        ext = os.path.splitext(filename)[1]
        py3Ext = Preferences.getPython("Python3Extensions")
        project = ericApp().getObject("Project")
        basename = os.path.basename(filename)

        if "FileType" in flags and flags["FileType"] in pythonEquivalents:
            return True
        elif project.isOpen() and project.isProjectFile(filename):
            language = project.getEditorLexerAssoc(basename)
            if not language:
                language = Preferences.getEditorLexerAssoc(basename)
            if language == "Python3":
                return True

        if (
            Preferences.getProject("DeterminePyFromProject")
            and project.isOpen()
            and project.isProjectFile(filename)
            and ext in py3Ext
            and project.getProjectLanguage() in pythonEquivalents
        ):
            return True
        elif ext in py3Ext:
            return True
        elif source:
            if isinstance(source, str):
                line0 = source.splitlines()[0]
            else:
                line0 = source[0]
            if line0.startswith("#!") and (("python3" in line0) or ("python" in line0)):
                return True

    return False


def searchInterpreters(environments=None):
    """
    Function to determine a list of all Python interpreters available via the
    executable search path (i.e. PATH) (Windows variant).

    @param environments list of environment directories to scan for Python interpreters
        (defaults to None)
    @type list of str (optional)
    @return list of found interpreter executables
    @rtype list of str
    """
    if isWindowsPlatform():
        return __searchInterpreters_Windows(environments=environments)
    else:
        return __searchInterpreters_Linux(environments=environments)


def __searchInterpreters_Windows(environments=None):
    """
    Function to determine a list of all Python interpreters available via the
    executable search path (i.e. PATH) (Windows variant).

    @param environments list of environment directories to scan for Python interpreters
        (defaults to None)
    @type list of str (optional)
    @return list of found interpreter executables
    @rtype list of str
    """
    try:
        import winreg  # noqa: I101, I103
    except ImportError:
        import _winreg as winreg  # noqa: I101, I102

    def getExePath(branch, access, versionStr):
        with contextlib.suppress(WindowsError, OSError):
            software = winreg.OpenKey(branch, "Software", 0, access)
            python = winreg.OpenKey(software, "Python", 0, access)
            pcore = winreg.OpenKey(python, "PythonCore", 0, access)
            version = winreg.OpenKey(pcore, versionStr, 0, access)
            installpath = winreg.QueryValue(version, "InstallPath")
            exe = os.path.join(installpath, "python.exe")
            if os.access(exe, os.X_OK):
                return exe

        return None

    minorVersions = range(8, 16)  # Py 3.8 until Py 3.15
    interpreters = set()

    if environments:
        for directory in [os.path.join(d, "Scripts") for d in environments]:
            exe = os.path.join(directory, "python.exe")
            if os.access(exe, os.X_OK):
                interpreters.add(exe)

    else:
        versionSuffixes = ["", "-32", "-64"]
        for minorVersion in minorVersions:
            for versionSuffix in versionSuffixes:
                versionStr = "{0}.{1}{2}".format("3", minorVersion, versionSuffix)
                exePath = getExePath(
                    winreg.HKEY_CURRENT_USER,
                    winreg.KEY_WOW64_32KEY | winreg.KEY_READ,
                    versionStr,
                )
                if exePath:
                    interpreters.add(exePath)

                exePath = getExePath(
                    winreg.HKEY_LOCAL_MACHINE,
                    winreg.KEY_WOW64_32KEY | winreg.KEY_READ,
                    versionStr,
                )
                if exePath:
                    interpreters.add(exePath)

                # Even on Intel 64-bit machines it's 'AMD64'
                if platform.machine() == "AMD64":
                    exePath = getExePath(
                        winreg.HKEY_CURRENT_USER,
                        winreg.KEY_WOW64_64KEY | winreg.KEY_READ,
                        versionStr,
                    )
                    if exePath:
                        interpreters.add(exePath)

                    exePath = getExePath(
                        winreg.HKEY_LOCAL_MACHINE,
                        winreg.KEY_WOW64_64KEY | winreg.KEY_READ,
                        versionStr,
                    )
                    if exePath:
                        interpreters.add(exePath)

    return list(interpreters)


def __searchInterpreters_Linux(environments=None):
    """
    Function to determine a list of all Python interpreters available via the
    executable search path (i.e. PATH) (non Windows variant).

    @param environments list of environment directories to scan for Python interpreters
        (defaults to None)
    @type list of str (optional)
    @return list of found interpreter executables
    @rtype list of str
    """
    from eric7.SystemUtilities import OSUtilities

    minorVersions = range(8, 16)  # Py 3.8 until Py 3.15
    interpreters = []

    if environments:
        directories = [os.path.join(d, "bin") for d in environments]
    else:
        searchpath = OSUtilities.getEnvironmentEntry("PATH")
        directories = searchpath.split(os.pathsep) if searchpath else []

    if directories:
        pythonNames = ["python3.{0}".format(v) for v in minorVersions]
        for directory in directories:
            for interpreter in pythonNames:
                exe = os.path.join(directory, interpreter)
                if os.access(exe, os.X_OK):
                    interpreters.append(exe)

    return interpreters
