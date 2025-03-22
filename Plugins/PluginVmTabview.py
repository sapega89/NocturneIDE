# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Tabview view manager plugin.
"""

import os

from PyQt6.QtCore import QT_TRANSLATE_NOOP, QObject
from PyQt6.QtGui import QPixmap

from eric7.__version__ import VersionOnly

# Start-Of-Header
__header__ = {
    "name": "Tabview Plugin",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": False,
    "deactivateable": False,
    "version": VersionOnly,
    "pluginType": "viewmanager",
    "pluginTypename": "tabview",
    "displayString": QT_TRANSLATE_NOOP("VmTabviewPlugin", "Tabbed View"),
    "className": "VmTabviewPlugin",
    "packageName": "__core__",
    "shortDescription": "Implements the Tabview view manager.",
    "longDescription": """This plugin provides the tabbed view view manager.""",
    "pyqtApi": 2,
}
# End-Of-Header

error = ""  # noqa: U200


def previewPix():
    """
    Module function to return a preview pixmap.

    @return preview pixmap
    @rtype QPixmap
    """
    fname = os.path.join(
        os.path.dirname(__file__), "ViewManagerPlugins", "Tabview", "preview.png"
    )
    return QPixmap(fname)


class VmTabviewPlugin(QObject):
    """
    Class implementing the Tabview view manager plugin.
    """

    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UserInterface
        """
        super().__init__(ui)
        self.__ui = ui

    def activate(self):
        """
        Public method to activate this plugin.

        @return tuple of reference to instantiated viewmanager and
            activation status
        @rtype bool
        """
        from eric7.Plugins.ViewManagerPlugins.Tabview.Tabview import Tabview

        self.__object = Tabview(self.__ui)
        return self.__object, True

    def deactivate(self):
        """
        Public method to deactivate this plugin.
        """
        # do nothing for the moment
        pass
