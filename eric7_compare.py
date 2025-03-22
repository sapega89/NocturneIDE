#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
eric Compare.

This is the main Python script that performs the necessary initialization
of the Compare module and starts the Qt event loop. This is a standalone
version of the integrated Compare module.
"""

import argparse
import os
import sys

from PyQt6.QtGui import QGuiApplication


def createArgparseNamespace():
    """
    Function to create an argument parser.

    @return created argument parser object
    @rtype argparse.ArgumentParser
    """
    from eric7.__version__ import Version

    # 1. create the argument parser
    parser = argparse.ArgumentParser(
        description="Simple graphical tool to compare two files side-by-side."
        " It is part of the eric tool suite.",
        epilog="Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>.",
    )

    # 2. add the arguments
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version="%(prog)s {0}".format(Version),
        help="show version information and exit",
    )
    parser.add_argument(
        "--config",
        metavar="config_dir",
        help="use the given directory as the one containing the config files",
    )
    parser.add_argument(
        "--settings",
        metavar="settings_dir",
        help="use the given directory to store the settings files",
    )
    parser.add_argument(
        "file_1",
        nargs="?",
        help="first file to be compared",
    )
    parser.add_argument(
        "file_2",
        nargs="?",
        help="second file to be compared",
    )

    # 3. create the Namespace object by parsing the command line
    args = parser.parse_args()
    if args.file_1 and not args.file_2:
        parser.error("Two files to be compared or none should be given.")
    return args


args = createArgparseNamespace()
if args.config:
    from eric7 import EricUtilities

    EricUtilities.setConfigDir(args.config)
if args.settings:
    from PyQt6.QtCore import QSettings

    SettingsDir = os.path.expanduser(args.settings)
    if not os.path.isdir(SettingsDir):
        os.makedirs(SettingsDir)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, SettingsDir
    )

from eric7.Toolbox import Startup


def createMainWidget(args):
    """
    Function to create the main widget.

    @param args namespace object containing the parsed command line parameters
    @type argparse.Namespace
    @return reference to the main widget
    @rtype QWidget
    """
    from eric7.UI.CompareDialog import CompareWindow

    if args.file_1 and args.file_2:
        return CompareWindow([("", args.file_1), ("", args.file_2)])
    else:
        return CompareWindow()


def main():
    """
    Main entry point into the application.
    """
    QGuiApplication.setDesktopFileName("eric7_compare")

    res = Startup.appStartup(args, createMainWidget)
    sys.exit(res)


if __name__ == "__main__":
    main()
