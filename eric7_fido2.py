#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
eric FIDO2 Token Management.

This is the main Python script that performs the necessary initialization
of the FIDO2 Security Key Management module and starts the Qt event loop.
This is a standalone version of the integrated FIDO2 Security Key Management
module.
"""

import argparse
import importlib
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
        description="Management tool for FIDO2 Security Keys.",
        epilog="Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>.",
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

if importlib.util.find_spec("fido2") is None:
    from PyQt6.QtCore import QTimer
    from PyQt6.QtWidgets import QApplication

    from eric7.EricWidgets import EricMessageBox

    app = QApplication([])
    QTimer.singleShot(
        0,
        lambda: EricMessageBox.critical(
            None,
            "FIDO2 Security Key Management",
            "The required 'fido2' package is not installed. Aborting...",
        ),
    )
    app.exec()
    sys.exit(100)

from eric7.Toolbox import Startup


def createMainWidget(_args):
    """
    Function to create the main widget.

    @param _args namespace object containing the parsed command line parameters
        (unused)
    @type argparse.Namespace
    @return reference to the main widget
    @rtype QWidget
    """
    from eric7.WebBrowser.WebAuth.Fido2ManagementDialog import Fido2ManagementDialog

    return Fido2ManagementDialog(standalone=True)


def main():
    """
    Main entry point into the application.
    """
    QGuiApplication.setDesktopFileName("eric7_fido2")

    res = Startup.appStartup(args, createMainWidget)
    sys.exit(res)


if __name__ == "__main__":
    if os.name == "nt":
        from command_runner.elevate import elevate

        elevate(main)
    else:
        main()
