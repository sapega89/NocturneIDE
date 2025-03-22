# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the closehead extension project helper.
"""

from PyQt6.QtWidgets import QMenu

from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction

from ..HgExtensionProjectHelper import HgExtensionProjectHelper


class CloseheadProjectHelper(HgExtensionProjectHelper):
    """
    Class implementing the closehead extension project helper.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

    def initActions(self):
        """
        Public method to generate the action objects.
        """
        self.hgCloseheadAct = EricAction(
            self.tr("Close Heads"),
            EricPixmapCache.getIcon("closehead"),
            self.tr("Close Heads"),
            0,
            0,
            self,
            "mercurial_closehead",
        )
        self.hgCloseheadAct.setStatusTip(
            self.tr("Close arbitrary heads without checking them out first")
        )
        self.hgCloseheadAct.setWhatsThis(
            self.tr(
                """<b>Close Heads</b>"""
                """<p>This closes arbitrary heads without the need to check them"""
                """ out first.</p>"""
            )
        )
        self.hgCloseheadAct.triggered.connect(self.__hgClosehead)
        self.actions.append(self.hgCloseheadAct)

    def initMenu(self, mainMenu):
        """
        Public method to generate the extension menu.

        @param mainMenu reference to the main menu
        @type QMenu
        @return populated menu
        @rtype QMenu
        """
        menu = QMenu(self.menuTitle(), mainMenu)
        menu.setIcon(EricPixmapCache.getIcon("closehead"))
        menu.setTearOffEnabled(True)

        menu.addAction(self.hgCloseheadAct)

        return menu

    def menuTitle(self):
        """
        Public method to get the menu title.

        @return title of the menu
        @rtype str
        """
        return self.tr("Close Heads")

    def __hgClosehead(self):
        """
        Private slot used to close arbitrary heads.
        """
        self.vcs.getExtensionObject("closehead").hgCloseheads()
