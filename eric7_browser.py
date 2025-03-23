#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
eric Web Browser.

This is the main Python script that performs the necessary initialization
of the web browser and starts the Qt event loop. This is a standalone version
of the integrated web browser. It is based on QtWebEngine.
"""

import os
import sys

from PyQt6.QtGui import QGuiApplication

import EricUtilities
from WebBrowser.WebBrowserArgumentsCreator import createArgparseNamespace

args = createArgparseNamespace()
if args.config:
    EricUtilities.setConfigDir(args.config)
if args.settings:
    from PyQt6.QtCore import QSettings

    SettingsDir = os.path.expanduser(args.settings)
    if not os.path.isdir(SettingsDir):
        os.makedirs(SettingsDir)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, SettingsDir
    )
else:
    SettingsDir = None

app = None

try:
    from PyQt6 import QtWebEngineWidgets  # __IGNORE_WARNING__
    from PyQt6.QtWebEngineCore import QWebEngineUrlScheme
except ImportError:
    if "--quiet" not in sys.argv:
        from PyQt6.QtCore import QTimer
        from PyQt6.QtWidgets import QApplication

        from EricWidgets import EricMessageBox

        app = QApplication([])
        QTimer.singleShot(
            0,
            lambda: EricMessageBox.critical(
                None,
                "eric Web Browser",
                "QtWebEngineWidgets is not installed but needed to execute the"
                " web browser.",
            ),
        )
        app.exec()
    sys.exit(100)

from EricWidgets.EricApplication import EricApplication  # noqa: NO101
from Toolbox import Startup
from WebBrowser.WebBrowserSingleApplication import (
    WebBrowserSingleApplicationClient,
)


def createMainWidget(args):
    """
    Function to create the main widget.

    @param args namespace object containing the parsed command line parameters
    @type argparse.Namespace
    @return reference to the main widget
    @rtype QWidget
    """
    from WebBrowser.WebBrowserWindow import WebBrowserWindow

    browser = WebBrowserWindow(
        args.home,
        ".",
        None,
        "web_browser",
        searchWord=args.search,
        private=args.private,
        settingsDir=SettingsDir,
        qthelp=args.qthelp,
        single=args.single,
        saname=args.name,
    )
    return browser


def main():
    """
    Main entry point into the application.
    """
    global app

    QGuiApplication.setDesktopFileName("eric7_browser")

    # set the library paths for plugins
    Startup.setLibraryPaths()

    scheme = QWebEngineUrlScheme(b"eric")
    scheme.setSyntax(QWebEngineUrlScheme.Syntax.Path)
    scheme.setFlags(
        QWebEngineUrlScheme.Flag.SecureScheme
        | QWebEngineUrlScheme.Flag.ContentSecurityPolicyIgnored
    )
    QWebEngineUrlScheme.registerScheme(scheme)
    if args.qthelp:
        scheme = QWebEngineUrlScheme(b"qthelp")
        scheme.setSyntax(QWebEngineUrlScheme.Syntax.Path)
        scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme)
        QWebEngineUrlScheme.registerScheme(scheme)

    app = EricApplication(args)
    if not args.private:
        client = WebBrowserSingleApplicationClient()
        res = client.connect()
        if res > 0:
            client.processArgs(args)
            sys.exit(0)
        elif res < 0:
            print("eric7_browser: {0}".format(client.errstr()))
            # __IGNORE_WARNING_M801__
            sys.exit(res)

    res = Startup.appStartup(args, createMainWidget, installErrorHandler=True, app=app)
    sys.exit(res)


if __name__ == "__main__":
    main()
