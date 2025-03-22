#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the main script for histedit.

Depending on the file name given by the Mercurial histedit command one
of two possible dialogs will be shown.
"""

import argparse
import os
import sys


def createArgparseNamespace():
    """
    Function to create an argument parser.

    @return created argument parser object
    @rtype argparse.ArgumentParser
    """
    from eric7.__version__ import Version

    # 1. create the argument parser
    parser = argparse.ArgumentParser(
        description="Graphical editor for the Mercurial 'histedit' command.",
        epilog="Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>.",
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
        "file",
        nargs="?",
        help="'histedit' file to be edited",
    )

    # 3. create the Namespace object by parsing the command line
    args = parser.parse_args()
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
    if args.file:
        fileName = os.path.basename(args.file)
        if fileName.startswith("hg-histedit-"):
            from HgHisteditPlanEditor import HgHisteditPlanEditor  # noqa: I101, I102

            return HgHisteditPlanEditor(args.file)
        elif fileName.startswith("hg-editor-"):
            from HgHisteditCommitEditor import (  # noqa: I101, I102
                HgHisteditCommitEditor,
            )

            return HgHisteditCommitEditor(args.file)

    return None


def main():
    """
    Main entry point into the application.
    """
    res = Startup.appStartup(args, createMainWidget)
    sys.exit(res)


if __name__ == "__main__":
    main()
