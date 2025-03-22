# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Class implementing a specialized application class.
"""

import contextlib
import os
import pathlib
import sys

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

if not QCoreApplication.testAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts):
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts, True)

from . import EricMessageBox


class EricApplication(QApplication):
    """
    Eric application class with an object registry.
    """

    PaletteRoleMapping = {
        "alternate-base": QPalette.ColorRole.AlternateBase,
        "base": QPalette.ColorRole.Base,
        "text": QPalette.ColorRole.Text,
        "bright-text": QPalette.ColorRole.BrightText,
        "placeholder-text": QPalette.ColorRole.PlaceholderText,
        "window": QPalette.ColorRole.Window,
        "window-text": QPalette.ColorRole.WindowText,
        "tooltip-base": QPalette.ColorRole.ToolTipBase,
        "tooltip-text": QPalette.ColorRole.ToolTipText,
        "button": QPalette.ColorRole.Button,
        "button-text": QPalette.ColorRole.ButtonText,
        "highlight": QPalette.ColorRole.Highlight,
        "highlighted-text": QPalette.ColorRole.HighlightedText,
        "link": QPalette.ColorRole.Link,
        "link-visited": QPalette.ColorRole.LinkVisited,
    }

    def __init__(self, args):
        """
        Constructor

        @param args namespace object containing the parsed command line parameters
        @type argparse.Namespace
        """
        super().__init__(sys.argv)

        QCoreApplication.setAttribute(
            Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings, True
        )

        self.__objectRegistry = {}
        self.__pluginObjectRegistry = {}

        try:
            self.__smallScreen = args.small_screen
        except AttributeError:
            self.__smallScreen = False
        if not self.__smallScreen:
            primaryScreenSize = self.primaryScreen().size()
            self.__smallScreen = (
                primaryScreenSize.width() < 1920 or primaryScreenSize.height() < 1080
            )

        self.__hasNonStandardPalette = False

        self.__mainWindow = None

    def usesSmallScreen(self):
        """
        Public method to determine, if the application is used on a small
        screen.

        @return flag indicating the use of a small screen
        @rtype bool
        """
        return self.__smallScreen

    def registerObject(self, name, objectRef):
        """
        Public method to register an object in the object registry.

        @param name name of the object
        @type str
        @param objectRef reference to the object
        @type Any
        @exception KeyError raised when the given name is already in use
        """
        if name in self.__objectRegistry:
            raise KeyError('Object "{0}" already registered.'.format(name))
        else:
            self.__objectRegistry[name] = objectRef

    def getObject(self, name):
        """
        Public method to get a reference to a registered object.

        @param name name of the object
        @type str
        @return reference to the registered object
        @rtype Any
        @exception KeyError raised when the given name is not known
        """
        if name not in self.__objectRegistry:
            raise KeyError('Object "{0}" is not registered.'.format(name))

        return self.__objectRegistry[name]

    def registerPluginObject(self, name, objectRef, pluginType=None):
        """
        Public method to register a plugin object in the object registry.

        @param name name of the plugin object
        @type str
        @param objectRef reference to the plugin object
        @type Any
        @param pluginType type of the plugin object
        @type str
        @exception KeyError raised when the given name is already in use
        """
        if name in self.__pluginObjectRegistry:
            raise KeyError('Pluginobject "{0}" already registered.'.format(name))
        else:
            self.__pluginObjectRegistry[name] = (objectRef, pluginType)

    def unregisterPluginObject(self, name):
        """
        Public method to unregister a plugin object in the object registry.

        @param name name of the plugin object
        @type str
        """
        if name in self.__pluginObjectRegistry:
            del self.__pluginObjectRegistry[name]

    def getPluginObject(self, name):
        """
        Public method to get a reference to a registered plugin object.

        @param name name of the plugin object
        @type str
        @return reference to the registered plugin object
        @rtype Any
        @exception KeyError raised when the given name is not known
        """
        if name not in self.__pluginObjectRegistry:
            raise KeyError('Pluginobject "{0}" is not registered.'.format(name))

        return self.__pluginObjectRegistry[name][0]

    def getPluginObjects(self):
        """
        Public method to get a list of (name, reference) pairs of all
        registered plugin objects.

        @return list of (name, reference) pairs
        @rtype list of (str, any)
        """
        objects = []
        for name in self.__pluginObjectRegistry:
            objects.append((name, self.__pluginObjectRegistry[name][0]))
        return objects

    def getPluginObjectType(self, name):
        """
        Public method to get the type of a registered plugin object.

        @param name name of the plugin object
        @type str
        @return type of the plugin object
        @rtype str
        @exception KeyError raised when the given name is not known
        """
        if name not in self.__pluginObjectRegistry:
            raise KeyError('Pluginobject "{0}" is not registered.'.format(name))

        return self.__pluginObjectRegistry[name][1]

    def getStyleIconsPath(self, universal=False):
        """
        Public method to get the path for the style icons.

        @param universal flag indicating a universal file path (defaults to
            False)
        @type bool (optional)
        @return directory path containing the style icons
        @rtype str
        """
        from eric7 import Preferences
        from eric7.Globals import getConfig

        styleIconsPath = Preferences.getUI("StyleIconsPath")
        if not styleIconsPath:
            # default is the 'StyleIcons' sub-directory of the icons
            # directory
            styleIconsPath = os.path.join(getConfig("ericIconDir"), "StyleIcons")

        if universal:
            return (
                pathlib.PurePath(styleIconsPath).as_posix()
                if bool(styleIconsPath)
                else ""
            )
        else:
            return styleIconsPath

    def setStyleSheetFile(self, filename):
        """
        Public method to read a QSS style sheet file and set the application
        style sheet based on its contents.

        @param filename name of the QSS style sheet file
        @type str
        """
        if filename:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    styleSheet = f.read()
            except OSError as msg:
                EricMessageBox.warning(
                    None,
                    QCoreApplication.translate(
                        "EricApplication", "Loading Style Sheet"
                    ),
                    QCoreApplication.translate(
                        "EricApplication",
                        """<p>The Qt Style Sheet file <b>{0}</b> could"""
                        """ not be read.<br>Reason: {1}</p>""",
                    ).format(filename, str(msg)),
                )
                return
        else:
            styleSheet = ""

        if styleSheet:
            # pre-process the style sheet to replace the placeholder for the
            # path to the icons
            styleIconsPath = self.getStyleIconsPath(universal=True)
            styleSheet = styleSheet.replace("${path}", styleIconsPath)

        if "QPalette {" in styleSheet:
            self.__setPaletteFromStyleSheet(styleSheet)

        ericApp().setStyleSheet(styleSheet)

    def __setPaletteFromStyleSheet(self, styleSheet):
        """
        Private method to set the palette from a style sheet.

        @param styleSheet style sheet
        @type str
        """
        palette = self.palette()

        paletteStr = styleSheet.split("QPalette {")[1].split("}")[0]
        paletteLines = paletteStr.strip().splitlines()
        for line in paletteLines:
            role, value = line.strip().split()
            role = role.strip("\t :").lower()
            value = value.strip("\t ;")
            if role in self.PaletteRoleMapping and value.startswith("#"):
                palette.setColor(self.PaletteRoleMapping[role], QColor(value))

        self.setPalette(palette)

        self.__hasNonStandardPalette = True

    def usesDarkPalette(self):
        """
        Public method to check, if the application uses a palette with a dark
        background.

        @return flag indicating the use of a palette with a dark background
        @rtype bool
        """
        if not self.__hasNonStandardPalette:
            with contextlib.suppress(AttributeError):
                return self.styleHints().colorScheme() == Qt.ColorScheme.Dark

        # backward compatibility for Qt < 6.5.0 or changed by user
        palette = self.palette()
        return (
            palette.color(QPalette.ColorRole.WindowText).lightness()
            > palette.color(QPalette.ColorRole.Window).lightness()
        )

    def setMainWindow(self, mainWindow):
        """
        Public method to set the reference to the application main window.

        @param mainWindow reference to the application main window
        @type QWidget
        """
        self.__mainWindow = mainWindow

    def getMainWindow(self):
        """
        Public method to get a reference to the application main window.

        @return reference to the application main window
        @rtype QWidget
        """
        return self.__mainWindow


ericApp = QCoreApplication.instance
