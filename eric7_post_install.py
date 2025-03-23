#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the post install logic for 'pip install'.
"""

import contextlib
import os
import shutil
import sys
import sysconfig

######################################################################
## Post installation hooks for Windows below
######################################################################


def createWindowsLinks():
    """
    Create Desktop and Start Menu links.
    """
    regPath = (
        "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\User Shell Folders"
    )

    # 1. create desktop shortcuts
    regName = "Desktop"
    desktopFolder = os.path.normpath(
        os.path.expandvars(getWinregEntry(regName, regPath))
    )
    for linkName, targetPath, iconPath in windowsDesktopEntries():
        linkPath = os.path.join(desktopFolder, linkName)
        createWindowsShortcut(linkPath, targetPath, iconPath)

    # 2. create start menu entry and shortcuts
    regName = "Programs"
    programsEntry = getWinregEntry(regName, regPath)
    if programsEntry:
        programsFolder = os.path.normpath(os.path.expandvars(programsEntry))
        eric7EntryPath = os.path.join(programsFolder, windowsProgramsEntry())
        if not os.path.exists(eric7EntryPath):
            try:
                os.makedirs(eric7EntryPath)
            except OSError:
                # maybe restrictions prohibited link creation
                return

        for linkName, targetPath, iconPath in windowsDesktopEntries():
            linkPath = os.path.join(eric7EntryPath, linkName)
            createWindowsShortcut(linkPath, targetPath, iconPath)


def getWinregEntry(name, path):
    """
    Function to get an entry from the Windows Registry.

    @param name variable name
    @type str
    @param path registry path of the variable
    @type str
    @return value of requested registry variable
    @rtype Any
    """
    try:
        import winreg  # __IGNORE_WARNING_I10__
    except ImportError:
        return None

    try:
        registryKey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(registryKey, name)
        winreg.CloseKey(registryKey)
        return value
    except WindowsError:
        return None


def windowsDesktopEntries():
    """
    Function to generate data for the Windows Desktop links.

    @return list of tuples containing the desktop link name,
        the link target and the icon target
    @rtype list of tuples of (str, str, str)
    """
    from . import __file__

    majorVersion, minorVersion = sys.version_info[:2]
    scriptsDir = sysconfig.get_path("scripts")
    iconsDir = os.path.join(os.path.dirname(__file__), "pixmaps")
    entriesTemplates = [
        (
            "eric7 IDE (Python {0}.{1}).lnk",
            os.path.join(scriptsDir, "eric7_ide.exe"),
            os.path.join(iconsDir, "eric7.ico"),
        ),
        (
            "eric7 MicroPython (Python {0}.{1}).lnk",
            os.path.join(scriptsDir, "eric7_mpy.exe"),
            os.path.join(iconsDir, "ericMPy48.ico"),
        ),
        (
            "eric7 Browser (Python {0}.{1}).lnk",
            os.path.join(scriptsDir, "eric7_browser.exe"),
            os.path.join(iconsDir, "ericWeb48.ico"),
        ),
    ]

    return [
        (e[0].format(majorVersion, minorVersion), e[1], e[2]) for e in entriesTemplates
    ]


def createWindowsShortcut(linkPath, targetPath, iconPath):
    """
    Create Windows shortcut.

    @param linkPath path of the shortcut file
    @type str
    @param targetPath path the shortcut shall point to
    @type str
    @param iconPath path of the icon file
    @type str
    """
    from pywintypes import com_error  # __IGNORE_WARNING_I102__
    from win32com.client import Dispatch  # __IGNORE_WARNING_I102__

    with contextlib.suppress(com_error):
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(linkPath)
        shortcut.Targetpath = targetPath
        shortcut.WorkingDirectory = os.path.dirname(targetPath)
        shortcut.IconLocation = iconPath
        shortcut.save()


def windowsProgramsEntry():
    """
    Function to generate the name of the Start Menu top entry.

    @return name of the Start Menu top entry
    @rtype str
    """
    majorVersion, minorVersion = sys.version_info[:2]
    return "eric7 (Python {0}.{1})".format(majorVersion, minorVersion)


######################################################################
## Post installation hooks for Linux below
######################################################################


def copyLinuxMetaData():
    """
    Function to copy the meta data files.
    """

    ericDir = os.path.dirname(__file__)
    scriptsDir = sysconfig.get_path("scripts")
    dstDir = os.path.join(os.path.expanduser("~"), ".local", "share")
    iconsDir = os.path.join(ericDir, "pixmaps")
    linuxDir = os.path.join(ericDir, "data", "linux")

    for metaDir in ["appdata", "metainfo"]:
        copyMetaFile(
            os.path.join(linuxDir, "eric7.appdata.xml"),
            os.path.join(dstDir, metaDir),
            "eric7.appdata.xml",
        )

    for svgIcon in ("eric.svg", "ericMPy48.svg", "ericWeb48.svg"):
        copyMetaFile(
            os.path.join(iconsDir, svgIcon), os.path.join(dstDir, "icons"), svgIcon
        )
    for icon in ("eric48_icon.png", "ericMPy48_icon.png", "ericWeb48_icon.png"):
        copyMetaFile(os.path.join(iconsDir, icon), os.path.join(dstDir, "icons"), icon)
        copyMetaFile(
            os.path.join(iconsDir, icon),
            os.path.join(dstDir, "icons", "hicolor", "48x48", "apps"),
            icon.replace("48_icon", ""),
        )

    for desktop in ["eric7_ide.desktop", "eric7_browser.desktop", "eric7_mpy.desktop"]:
        copyDesktopFile(
            os.path.join(linuxDir, desktop),
            os.path.join(dstDir, "applications"),
            desktop,
            scriptsDir,
        )


def copyMetaFile(srcname, dstpath, dstname):
    """
    Function to copy a file to its destination.

    @param srcname name of the source file
    @type str
    @param dstpath name of the destination path
    @type str
    @param dstname name of the destination file (without path)
    @type str
    """
    if not os.path.isdir(dstpath):
        os.makedirs(dstpath)
    dstname = os.path.join(dstpath, dstname)
    shutil.copy2(srcname, dstname)
    os.chmod(dstname, 0o644)


def copyDesktopFile(src, dstPath, dstFile, scriptsdir):
    """
    Modify a desktop file and write it to its destination.

    @param src source file name
    @type str
    @param dstPath path name of the directory for the file to be written
    @type str
    @param dstFile name of the file to be written
    @type str
    @param scriptsdir directory containing the scripts
    @type str
    """
    with open(src, "r", encoding="utf-8") as f:
        text = f.read()

    text = text.replace("@BINDIR@", scriptsdir)

    if not os.path.isdir(dstPath):
        os.makedirs(dstPath)
    dst = os.path.join(dstPath, dstFile)
    with open(dst, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(dst, 0o644)


######################################################################
## Main script below
######################################################################


def main():
    """
    Main script orchestrating the platform dependent post installation tasks.
    """
    if sys.platform.startswith(("win", "cygwin")):
        createWindowsLinks()
    elif sys.platform.startswith(("linux", "freebsd")):
        copyLinuxMetaData()

    sys.exit(0)


if __name__ == "__main__":
    main()
