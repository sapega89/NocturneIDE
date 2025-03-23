#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
eric TR Previewer.

This is the main Python script that performs the necessary initialization
of the tr previewer and starts the Qt event loop. This is a standalone version
of the integrated tr previewer.
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
    from __version__ import Version

    # 1. create the argument parser
    parser = argparse.ArgumentParser(
        description="Translations file previewer of the eric tool suite.",
        epilog="Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>.",
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
        nargs="*",
        help="open a list of translation files for previewing",
    )

    # 3. create the Namespace object by parsing the command line
    args = parser.parse_args()
    return args


args = createArgparseNamespace()
if args.config:
    import EricUtilities

    EricUtilities.setConfigDir(args.config)
if args.settings:
    from PyQt6.QtCore import QSettings

    settingsDir = os.path.expanduser(args.settings)
    if not os.path.isdir(settingsDir):
        os.makedirs(settingsDir)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, settingsDir
    )

from EricWidgets.EricApplication import EricApplication
from Toolbox import Startup
from Tools.TRSingleApplication import TRSingleApplicationClient

app = None


def createMainWidget(args):
    """
    Function to create the main widget.

    @param args namespace object containing the parsed command line parameters
    @type argparse.Namespace
    @return reference to the main widget
    @rtype QWidget
    """
    from Tools.TRPreviewer import TRPreviewer

    previewer = TRPreviewer(args.file, None, "TRPreviewer")

    return previewer


def main():
    """
    Main entry point into the application.
    """
    global app

    QGuiApplication.setDesktopFileName("eric7_trpreviewer")

    # set the library paths for plugins
    Startup.setLibraryPaths()

    app = EricApplication(args)
    client = TRSingleApplicationClient()
    res = client.connect()
    if res > 0:
        if args.file:
            client.processArgs(args)
        sys.exit(0)
    elif res < 0:
        print("eric7_trpreviewer: {0}".format(client.errstr()))
        sys.exit(res)
    else:
        res = Startup.appStartup(args, createMainWidget, app=app)
        sys.exit(res)


if __name__ == "__main__":
    main()

#
# eflag: noqa = M801
