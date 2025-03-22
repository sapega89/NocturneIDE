#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
eric Python IDE.

This is the main Python script that performs the necessary initialization
of the IDE and starts the Qt event loop.
"""

import argparse
import contextlib
import io
import logging
import multiprocessing
import os
import sys
import time
import traceback


originalPathString = os.getenv("PATH")

# generate list of arguments to be remembered for a restart
restartArgsList = [
    "--config",
    "--debug",
    "--disable-crash",
    "--disable-plugin",
    "--no-multimedia",
    "--no-splash",
    "--plugin",
    "--settings",
]
restartArgs = [arg for arg in sys.argv[1:] if arg.split("=", 1)[0] in restartArgsList]

try:
    from PyQt6.QtCore import QCoreApplication, QLibraryInfo, QTimer, qWarning
    from PyQt6.QtGui import QGuiApplication
except ImportError:
    try:
        from tkinter import messagebox
    except ImportError:
        sys.exit(100)
    messagebox.showerror(
        "eric7 Error",
        "PyQt could not be imported. Please make sure"
        " it is installed and accessible.",
    )
    sys.exit(100)

try:
    from PyQt6 import QtWebEngineWidgets  # __IGNORE_WARNING__ __IGNORE_EXCEPTION__
    from PyQt6.QtWebEngineCore import QWebEngineUrlScheme

    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False


def createArgparseNamespace():
    """
    Function to create an argument parser.

    @return created argument parser object
    @rtype argparse.ArgumentParser
    """
    from eric7.__version__ import Version

    # 1. create the argument parser
    parser = argparse.ArgumentParser(
        description="The full featured eric Python IDE.",
        epilog="Use '--' to indicate that there are options for the program to be"
        " debugged (everything after that is considered arguments for this program)",
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
        "--debug",
        action="store_true",
        help="activate debugging output to the console",
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
        "--small-screen",
        action="store_true",
        help="adjust the interface for screens smaller than FHD",
    )
    parser.add_argument(
        "--no-multimedia",
        action="store_true",
        help="disable the support of multimedia functions",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="don't open anything at startup except that given in command",
    )
    parser.add_argument(
        "--no-splash",
        action="store_true",
        help="don't show the splash screen",
    )
    parser.add_argument(
        "--no-crash",
        action="store_true",
        help="don't check for a crash session file on startup",
    )
    parser.add_argument(
        "--disable-crash",
        action="store_true",
        help="disable the support for crash sessions",
    )
    parser.add_argument(
        "--disable-plugin",
        metavar="plugin-name",
        default=[],
        action="append",
        help="disable the given plugin (may be repeated)",
    )
    parser.add_argument(
        "--plugin",
        metavar="plugin-file",
        help="load the given plugin file (plugin development)",
    )
    parser.add_argument(
        "--start-file",
        action="store_true",
        help="load the most recently opened file",
    )
    parser.add_argument(
        "--start-multi",
        action="store_true",
        help="load the most recently opened multi-project",
    )
    parser.add_argument(
        "--start-project",
        action="store_true",
        help="load the most recently opened project",
    )
    parser.add_argument(
        "--start-session",
        action="store_true",
        help="load the global session file",
    )
    parser.add_argument(
        "file_or_project",
        nargs="*",
        metavar="multi-project | project | file",
        help="open a project, multi-project or a list of files",
    )

    # 3. preprocess the command line ('--' detection and split)
    if "--" in sys.argv:
        ddindex = sys.argv.index("--")
        argv = sys.argv[1:ddindex]
        dd_argv = sys.argv[ddindex + 1 :]
    else:
        argv = sys.argv[1:]
        dd_argv = []

    # 4. create the Namespace object by parsing the command line
    args = parser.parse_args(argv)
    args.dd_args = dd_argv

    return args


# some global variables needed to start the application
args = createArgparseNamespace()
mainWindow = None
splash = None
inMainLoop = False
app = None

from eric7 import EricUtilities

if args.config:
    EricUtilities.setConfigDir(args.config)

if args.debug:
    logging.basicConfig(
        filename=os.path.join(EricUtilities.getConfigDir(), "eric7_debug.txt"),
        filemode="w",
        format="[%(asctime)s] %(levelname)s: %(name)s:%(lineno)d - %(message)s",
        level=logging.DEBUG,
    )

if args.settings:
    from PyQt6.QtCore import QSettings

    settingsDir = os.path.expanduser(args.settings)
    if not os.path.isdir(settingsDir):
        os.makedirs(settingsDir)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, settingsDir
    )

from eric7.EricWidgets.EricApplication import EricApplication


def handleSingleApplication():
    """
    Global function to handle the single application mode.
    """
    from eric7.EricWidgets.EricSingleApplication import EricSingleApplicationClient

    client = EricSingleApplicationClient()
    res = client.connect()
    if res > 0:
        client.processArgs(args)
        sys.exit(0)

    elif res < 0:
        print("eric7: {0}".format(client.errstr()))
        # __IGNORE_WARNING_M801__
        sys.exit(res)


def excepthook(excType, excValue, tracebackobj):
    """
    Global function to catch unhandled exceptions.

    @param excType exception type
    @type Class
    @param excValue exception value
    @type Exception
    @param tracebackobj traceback object
    @type Traceback
    """
    from eric7 import EricUtilities, Utilities
    from eric7.UI.Info import BugAddress

    # Workaround for a strange issue with QScintilla
    if str(excValue) == "unable to convert a QVariant back to a Python object":
        return

    separator = "-" * 80
    logFile = os.path.join(EricUtilities.getConfigDir(), "eric7_error.log")
    notice = (
        """An unhandled exception occurred. Please report the problem\n"""
        """using the error reporting dialog or via email to <{0}>.\n"""
        """A log has been written to "{1}".\n\nError information:\n""".format(
            BugAddress, logFile
        )
    )
    timeString = time.strftime("%Y-%m-%d, %H:%M:%S")

    versionInfo = "\n{0}\n{1}".format(separator, Utilities.generateVersionInfo())
    pluginVersionInfo = Utilities.generatePluginsVersionInfo()
    if pluginVersionInfo:
        versionInfo += "\n{0}\n{1}".format(separator, pluginVersionInfo)
    distroInfo = Utilities.generateDistroInfo()
    if distroInfo:
        versionInfo += "\n{0}\n{1}".format(separator, distroInfo)

    if isinstance(excType, str):
        tbinfo = tracebackobj
    else:
        tbinfofile = io.StringIO()
        traceback.print_tb(tracebackobj, None, tbinfofile)
        tbinfofile.seek(0)
        tbinfo = tbinfofile.read()
    errmsg = "{0}: \n{1}".format(str(excType), str(excValue))
    sections = ["", separator, timeString, separator, errmsg, separator, tbinfo]
    msg = "\n".join(sections)
    with contextlib.suppress(OSError), open(logFile, "a", encoding="utf-8") as f:
        # Open in append mode to be able to catch multiple (follow-on) exceptions.
        f.write(msg)
        f.write(versionInfo)

    if inMainLoop:
        warning = notice + msg + versionInfo
        # Escape &<> otherwise it's not visible in the error dialog
        warning = (
            warning.replace("&", "&amp;").replace(">", "&gt;").replace("<", "&lt;")
        )
        qWarning(warning)
    else:
        warning = notice + msg + versionInfo
        print(warning)  # __IGNORE_WARNING_M801__


def uiStartUp():
    """
    Global function to finalize the start up of the main UI.

    Note: It is activated by a zero timeout single-shot timer.
    """
    global args, mainWindow, splash

    if splash:
        splash.finish(mainWindow)
        del splash

    mainWindow.checkForErrorLog()
    if not mainWindow.performVersionCheck(startup=True):
        mainWindow.processArgs(args)
        mainWindow.processInstallInfoFile()
        mainWindow.checkProjectsWorkspace()
        mainWindow.checkConfigurationStatus()
        mainWindow.checkPluginUpdatesAvailable()
        mainWindow.autoConnectIrc()


def main():
    """
    Main entry point into the application.
    """
    from eric7.SystemUtilities import OSUtilities, QtUtilities
    from eric7.Toolbox import Startup

    global app, args, mainWindow, splash, restartArgs, inMainLoop

    sys.excepthook = excepthook
    if OSUtilities.isLinuxPlatform() or OSUtilities.isFreeBsdPlatform():
        multiprocessing.set_start_method("spawn")

    QGuiApplication.setDesktopFileName("eric7")

    if "__PYVENV_LAUNCHER__" in os.environ:
        del os.environ["__PYVENV_LAUNCHER__"]

    # make sure our executable directory (i.e. that of the used Python
    # interpreter) is included in the executable search path
    pathList = os.environ["PATH"].split(os.pathsep)
    exeDir = os.path.dirname(sys.executable)
    if exeDir not in pathList:
        pathList.insert(0, exeDir)
    os.environ["PATH"] = os.pathsep.join(pathList)

    # set the library paths for plugins
    Startup.setLibraryPaths()

    if WEBENGINE_AVAILABLE:
        scheme = QWebEngineUrlScheme(b"qthelp")
        scheme.setSyntax(QWebEngineUrlScheme.Syntax.Path)
        scheme.setFlags(QWebEngineUrlScheme.Flag.SecureScheme)
        QWebEngineUrlScheme.registerScheme(scheme)

    app = EricApplication(args)

    logging.getLogger(__name__).debug("Importing Preferences")
    from eric7 import Preferences  # __IGNORE_WARNING_I101__

    if Preferences.getUI("SingleApplicationMode"):
        handleSingleApplication()

    # set the application style sheet
    app.setStyleSheetFile(Preferences.getUI("StyleSheet"))

    # set the search path for icons
    Startup.initializeResourceSearchPath(app)

    # generate and show a splash window, if not suppressed
    from eric7.UI.SplashScreen import (  # __IGNORE_WARNING_I101__
        NoneSplashScreen,
        SplashScreen,
    )

    if args.no_splash:
        splash = NoneSplashScreen()
    elif not Preferences.getUI("ShowSplash"):
        splash = NoneSplashScreen()
    else:
        splash = SplashScreen()
    QCoreApplication.processEvents()

    # modify the executable search path for the PyQt6 installer
    if OSUtilities.isWindowsPlatform():
        pyqtDataDir = QtUtilities.getPyQt6ModulesDirectory()
        if os.path.exists(os.path.join(pyqtDataDir, "bin")):
            path = os.path.join(pyqtDataDir, "bin")
        else:
            path = pyqtDataDir
        os.environ["PATH"] = path + os.pathsep + os.environ["PATH"]

    # get the Qt translations directory
    qtTransDir = Preferences.getQtTranslationsDir()
    if not qtTransDir:
        qtTransDir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)

    # Load translation files and install them
    loc = Startup.loadTranslators(qtTransDir, app, ("qscintilla",))

    # generate a graphical error handler
    from eric7.EricWidgets import EricErrorMessage  # __IGNORE_WARNING_I101__

    eMsg = EricErrorMessage.qtHandler(
        minSeverity=Preferences.getUI("MinimumMessageTypeSeverity")
    )
    eMsg.setMinimumSize(600, 400)

    # Initialize SSL stuff
    from eric7.EricNetwork.EricSslUtilities import initSSL  # __IGNORE_WARNING_I101__

    initSSL()

    splash.showMessage(QCoreApplication.translate("eric7_ide", "Starting..."))
    logging.getLogger(__name__).debug("Starting...")

    # We can only import these after creating the EricApplication because they
    # make Qt calls that need the EricApplication to exist.
    from eric7.UI.UserInterface import UserInterface  # __IGNORE_WARNING_I101__

    splash.showMessage(
        QCoreApplication.translate("eric7_ide", "Generating Main Window...")
    )
    logging.getLogger(__name__).debug("Generating Main Window...")
    mainWindow = UserInterface(
        app,
        loc,
        splash,
        (
            None
            if args.plugin is None
            else os.path.abspath(os.path.expanduser(args.plugin))
        ),
        args.disable_plugin,
        args.no_open,
        args.no_crash,
        args.disable_crash,
        restartArgs,
        originalPathString,
    )
    app.setMainWindow(mainWindow=mainWindow)
    app.lastWindowClosed.connect(app.quit)
    mainWindow.show()

    QTimer.singleShot(0, uiStartUp)

    # start the event loop
    inMainLoop = True
    res = app.exec()
    logging.getLogger(__name__).debug("Shutting down, result %d", res)
    logging.shutdown()
    sys.exit(res)


if __name__ == "__main__":
    main()
