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
    "name": "Listspace Plugin",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": False,
    "deactivateable": False,
    "version": VersionOnly,
    "pluginType": "viewmanager",
    "pluginTypename": "listspace",
    "displayString": QT_TRANSLATE_NOOP("VmListspacePlugin", "Listspace"),
    "className": "VmListspacePlugin",
    "packageName": "__core__",
    "shortDescription": "Implements the Listspace view manager.",
    "longDescription": """This plugin provides the listspace view manager.""",
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
        os.path.dirname(__file__), "ViewManagerPlugins", "Listspace", "preview.png"
    )
    return QPixmap(fname)


class VmListspacePlugin(QObject):
    """
    Class implementing the Listspace view manager plugin.
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
        from eric7.Plugins.ViewManagerPlugins.Listspace.Listspace import Listspace

        self.__object = Listspace(self.__ui)
        return self.__object, True

    def deactivate(self):
        """
        Public method to deactivate this plugin.
        """
        # do nothing for the moment
        pass
