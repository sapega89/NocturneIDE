# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the About plugin.
"""

from PyQt6.QtCore import QObject
from PyQt6.QtGui import QAction

from eric7.__version__ import VersionOnly
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox
from eric7.UI import Info

# Start-Of-Header
__header__ = {
    "name": "About Plugin",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": True,
    "deactivateable": True,
    "version": VersionOnly,
    "className": "AboutPlugin",
    "packageName": "__core__",
    "shortDescription": "Show the About dialogs.",
    "longDescription": """This plugin shows the About dialogs.""",
    "pyqtApi": 2,
}
# End-Of-Header

error = ""  # noqa: U200


class AboutPlugin(QObject):
    """
    Class implementing the About plugin.
    """

    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UserInterface
        """
        super().__init__(ui)
        self.__ui = ui

        self.__aboutDialog = None

    def activate(self):
        """
        Public method to activate this plugin.

        @return tuple of None and activation status
        @rtype bool
        """
        self.__initActions()
        self.__initMenu()

        return None, True

    def deactivate(self):
        """
        Public method to deactivate this plugin.
        """
        menu = self.__ui.getMenu("help")
        if menu:
            menu.removeAction(self.aboutAct)
            menu.removeAction(self.aboutQtAct)
        acts = [self.aboutAct, self.aboutQtAct]
        self.__ui.removeEricActions(acts, "ui")

    def __initActions(self):
        """
        Private method to initialize the actions.
        """
        acts = []

        self.aboutAct = EricAction(
            self.tr("About {0}").format(Info.Program),
            EricPixmapCache.getIcon("helpAbout"),
            self.tr("&About {0}").format(Info.Program),
            0,
            0,
            self,
            "about_eric",
        )
        self.aboutAct.setStatusTip(self.tr("Display information about this software"))
        self.aboutAct.setWhatsThis(
            self.tr(
                """<b>About {0}</b>"""
                """<p>Display some information about this software.</p>"""
            ).format(Info.Program)
        )
        self.aboutAct.triggered.connect(self.__about)
        self.aboutAct.setMenuRole(QAction.MenuRole.AboutRole)
        acts.append(self.aboutAct)

        self.aboutQtAct = EricAction(
            self.tr("About Qt"),
            EricPixmapCache.getIcon("helpAboutQt"),
            self.tr("About &Qt"),
            0,
            0,
            self,
            "about_qt",
        )
        self.aboutQtAct.setStatusTip(
            self.tr("Display information about the Qt toolkit")
        )
        self.aboutQtAct.setWhatsThis(
            self.tr(
                """<b>About Qt</b>"""
                """<p>Display some information about the Qt toolkit.</p>"""
            )
        )
        self.aboutQtAct.triggered.connect(self.__aboutQt)
        self.aboutQtAct.setMenuRole(QAction.MenuRole.AboutQtRole)
        acts.append(self.aboutQtAct)

        self.__ui.addEricActions(acts, "ui")

    def __initMenu(self):
        """
        Private method to add the actions to the right menu.
        """
        menu = self.__ui.getMenu("help")
        if menu:
            act = self.__ui.getMenuAction("help", "show_versions")
            if act:
                menu.insertAction(act, self.aboutAct)
                menu.insertAction(act, self.aboutQtAct)
                menu.insertSeparator(act)
            else:
                menu.addAction(self.aboutAct)
                menu.addAction(self.aboutQtAct)
                menu.addSeparator()

    def __about(self):
        """
        Private slot to handle the About dialog.
        """
        from eric7.Plugins.AboutPlugin.AboutDialog import AboutDialog

        if self.__aboutDialog is None:
            self.__aboutDialog = AboutDialog(self.__ui)
        self.__aboutDialog.show()

    def __aboutQt(self):
        """
        Private slot to handle the About Qt dialog.
        """
        EricMessageBox.aboutQt(self.__ui, Info.Program)
