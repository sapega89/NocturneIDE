# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some startup helper funcions.
"""

import os
import sys

from PyQt6.QtCore import QDir, QLibraryInfo, QLocale, QTranslator
from PyQt6.QtWidgets import QApplication

from eric7 import EricUtilities
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import EricApplication
from eric7.Globals import getConfig
from eric7.SystemUtilities import QtUtilities

application = None


def initializeResourceSearchPath(application):
    """
    Module function to initialize the default mime source factory.

    @param application reference to the application object
    @type EricApplication
    """
    from eric7 import Preferences

    EricPixmapCache.setPreferVectorIcons(Preferences.getIcons("PreferVectorIcons"))

    defaultIconPaths = getDefaultIconPaths(application)
    iconPaths = Preferences.getIcons("Path")
    for iconPath in iconPaths:
        if iconPath:
            EricPixmapCache.addSearchPath(iconPath)
    for defaultIconPath in defaultIconPaths:
        if defaultIconPath not in iconPaths:
            EricPixmapCache.addSearchPath(defaultIconPath)


def getDefaultIconPaths(application):
    """
    Module function to determine the default icon paths.

    @param application reference to the application object
    @type EricApplication
    @return list of default icon paths
    @rtype list of str
    """
    from eric7 import Preferences

    defaultIconsPath = Preferences.getIcons("DefaultIconsPath")
    if defaultIconsPath == "automatic":
        if application.usesDarkPalette():
            # dark desktop
            defaultIconsPath = "breeze-dark"
        else:
            # light desktop
            defaultIconsPath = "breeze-light"

    return [
        os.path.join(getConfig("ericIconDir"), defaultIconsPath),
        os.path.join(getConfig("ericIconDir"), defaultIconsPath, "languages"),
    ]


def setLibraryPaths():
    """
    Module function to set the Qt library paths correctly.
    """
    libPaths = (
        os.path.join(QtUtilities.getPyQt6ModulesDirectory(), "plugins"),
        os.path.join(QtUtilities.getPyQt6ModulesDirectory(), "Qt6", "plugins"),
    )

    libraryPaths = QApplication.libraryPaths()
    for libPath in libPaths:
        if os.path.exists(libPath):
            libPath = QDir.fromNativeSeparators(libPath)
            if libPath not in libraryPaths:
                libraryPaths.insert(0, libPath)
    QApplication.setLibraryPaths(libraryPaths)


# the translator must not be deleted, therefore we save them here
loaded_translators = {}


def loadTranslators(qtTransDir, app, translationFiles=()):
    """
    Module function to load all required translations.

    @param qtTransDir directory of the Qt translations files
    @type str
    @param app reference to the application object
    @type QApplication
    @param translationFiles tuple of additional translations to
        be loaded
    @type tuple of str
    @return the requested locale
    @rtype str
    """
    from eric7 import Preferences

    global loaded_translators

    translations = (
        "qt",
        "qt_help",
        "qtbase",
        "qtmultimedia",
        "qtserialport",
        "qtwebengine",
        "qtwebsockets",
        "eric7",
    ) + translationFiles
    loc = Preferences.getUILanguage()
    if loc is None:
        return ""

    if loc == "System":
        loc = QLocale.system().name()
    if loc != "C":
        dirs = [getConfig("ericTranslationsDir"), EricUtilities.getConfigDir()]
        if qtTransDir is not None:
            dirs.append(qtTransDir)

        loca = loc
        for tf in ["{0}_{1}".format(tr, loc) for tr in translations]:
            translator, ok = loadTranslatorForLocale(dirs, tf)
            loaded_translators[tf] = translator
            if ok:
                app.installTranslator(translator)
            else:
                if tf.startswith("eric7"):
                    loca = None
        loc = loca
    else:
        loc = None
    return loc


def loadTranslatorForLocale(dirs, tn):
    """
    Module function to find and load a specific translation.

    @param dirs searchpath for the translations
    @type list of str
    @param tn translation to be loaded
    @type str
    @return tuple containing a status flag and the loaded translator
    @rtype tuple of (int, QTranslator)
    """
    trans = QTranslator(None)
    for directory in dirs:
        loaded = trans.load(tn, directory)
        if loaded:
            return (trans, True)

    print("Warning: translation file '" + tn + "'could not be loaded.")
    print("Using default.")
    return (None, False)


def appStartup(
    args,
    mwFactory,
    quitOnLastWindowClosed=True,
    app=None,
    raiseIt=True,
    installErrorHandler=False,
):
    """
    Module function to start up an application that doesn't need a specialized
    start up.

    This function is used by all of eric's helper programs.

    @param args namespace object created by ArgumentParser.parse_args() containing
        the parsed command line arguments
    @type argparse.Namespace
    @param mwFactory factory function generating the main widget. This
        function must accept the following parameter.
        <dl>
            <dt>args</dt>
            <dd>parsed command line arguments (argparse.Namespace)</dd>
        </dl>
    @type function
    @param quitOnLastWindowClosed flag indicating to quit the application,
        if the last window was closed
    @type bool
    @param app reference to the application object
    @type QApplication or None
    @param raiseIt flag indicating to raise the generated application
        window
    @type bool
    @param installErrorHandler flag indicating to install an error
        handler dialog
    @type bool
    @return exit result
    @rtype int
    """
    global application

    if "__PYVENV_LAUNCHER__" in os.environ:
        del os.environ["__PYVENV_LAUNCHER__"]

    if app is None:
        # set the library paths for plugins
        setLibraryPaths()
        app = EricApplication(sys.argv)
        application = app
    app.setQuitOnLastWindowClosed(quitOnLastWindowClosed)

    # the following code depends upon a valid application object
    from eric7 import Preferences  # __IGNORE_WARNING_I101__

    # set the application style sheet
    app.setStyleSheetFile(Preferences.getUI("StyleSheet"))

    initializeResourceSearchPath(app)
    QApplication.setWindowIcon(EricPixmapCache.getIcon("eric"))

    qtTransDir = Preferences.getQtTranslationsDir()
    if not qtTransDir:
        qtTransDir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    loadTranslators(qtTransDir, app, ("qscintilla",))
    # qscintilla needed for web browser

    w = mwFactory(args)
    if w is None:
        return 100
    else:
        app.setMainWindow(mainWindow=w)

    if quitOnLastWindowClosed:
        app.lastWindowClosed.connect(app.quit)
    w.show()
    if raiseIt:
        w.raise_()

    if installErrorHandler:
        # generate a graphical error handler
        from eric7.EricWidgets import EricErrorMessage  # __IGNORE_WARNING_I101__

        eMsg = EricErrorMessage.qtHandler(
            minSeverity=Preferences.getUI("MinimumMessageTypeSeverity")
        )
        eMsg.setMinimumSize(600, 400)

    return app.exec()


#
# eflag: noqa = M801
