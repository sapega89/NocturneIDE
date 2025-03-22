# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the translator object.
"""

import os

from PyQt6.QtCore import QObject, Qt
from PyQt6.QtGui import QKeySequence

from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.UI.UserInterface import UserInterfaceSide


class Translator(QObject):
    """
    Class implementing the translator object.
    """

    def __init__(self, plugin, usesDarkPalette, parent=None):
        """
        Constructor

        @param plugin reference to the plugin object
        @type TranslatorPlugin
        @param usesDarkPalette flag indicating that the platform uses a palette
            with a dark background
        @type bool
        @param parent parent
        @type QObject
        """
        QObject.__init__(self, parent)

        self.__plugin = plugin
        self.__ui = parent

        self.__widget = None

        if usesDarkPalette:
            self.__iconSuffix = "dark"
        else:
            self.__iconSuffix = "light"

    def activate(self):
        """
        Public method to activate the translator.
        """
        from .TranslatorWidget import TranslatorWidget

        self.__widget = TranslatorWidget(self.__plugin, self)
        iconName = (
            "sbTranslator96"
            if self.__ui.getLayoutType() == "Sidebars"
            else "flag-{0}".format(self.__iconSuffix)
        )
        self.__ui.addSideWidget(
            UserInterfaceSide.Bottom,
            self.__widget,
            EricPixmapCache.getIcon(
                os.path.join(os.path.dirname(__file__), "icons", iconName)
            ),
            self.tr("Translator"),
        )

        self.__activateAct = EricAction(
            self.tr("Translator"),
            self.tr("T&ranslator"),
            QKeySequence(self.tr("Alt+Shift+R")),
            0,
            self,
            "translator_activate",
        )
        self.__activateAct.setStatusTip(
            self.tr("Switch the input focus to the Translator window.")
        )
        self.__activateAct.setWhatsThis(
            self.tr(
                """<b>Activate Translator</b>"""
                """<p>This switches the input focus to the Translator"""
                """ window.</p>"""
            )
        )
        self.__activateAct.triggered.connect(self.__activateWidget)

        self.__ui.addEricActions([self.__activateAct], "ui")
        menu = self.__ui.getMenu("subwindow")
        menu.addAction(self.__activateAct)

    def deactivate(self):
        """
        Public method to deactivate the time tracker.
        """
        menu = self.__ui.getMenu("subwindow")
        menu.removeAction(self.__activateAct)
        self.__ui.removeEricActions([self.__activateAct], "ui")
        self.__ui.removeSideWidget(self.__widget)

    def getAppIcon(self, name):
        """
        Public method to get an icon.

        @param name name of the icon file
        @type str
        @return icon
        @rtype QIcon
        """
        return EricPixmapCache.getIcon(
            os.path.join(
                os.path.dirname(__file__),
                "icons",
                "{0}-{1}".format(name, self.__iconSuffix),
            )
        )

    def __activateWidget(self):
        """
        Private slot to handle the activation of the project browser.
        """
        uiLayoutType = self.__ui.getLayoutType()
        if uiLayoutType == "Toolboxes":
            self.__ui.hToolboxDock.show()
            self.__ui.hToolbox.setCurrentWidget(self.__widget)
        elif uiLayoutType == "Sidebars":
            self.__ui.bottomSidebar.show()
            self.__ui.bottomSidebar.setCurrentWidget(self.__widget)
        else:
            self.__widget.show()
        self.__widget.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
