# -*- coding: utf-8 -*-

# Copyright (c) 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the fastexport extension project helper.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QMenu

from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction

from ..HgExtensionProjectHelper import HgExtensionProjectHelper


class FastexportProjectHelper(HgExtensionProjectHelper):
    """
    Class implementing the fastexport extension project helper.
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
        self.hgFastexportAct = EricAction(
            self.tr("Export to git"),
            EricPixmapCache.getIcon("vcsFastexport"),
            self.tr("Export to git"),
            0,
            0,
            self,
            "mercurial_fastexport",
        )
        self.hgFastexportAct.setStatusTip(
            self.tr("Export the repository as git fast-import stream.")
        )
        self.hgFastexportAct.setWhatsThis(
            self.tr(
                """<b>Export to git</b>"""
                """<p>This exports the repository as a git fast-import stream.</p>"""
            )
        )
        self.hgFastexportAct.triggered.connect(self.__hgFastexport)
        self.actions.append(self.hgFastexportAct)

    def initMenu(self, mainMenu):
        """
        Public method to generate the extension menu.

        @param mainMenu reference to the main menu
        @type QMenu
        @return populated menu
        @rtype QMenu
        """
        menu = QMenu(self.menuTitle(), mainMenu)
        menu.setIcon(EricPixmapCache.getIcon("vcsFastexport"))
        menu.setTearOffEnabled(True)

        menu.addAction(self.hgFastexportAct)

        return menu

    def menuTitle(self):
        """
        Public method to get the menu title.

        @return title of the menu
        @rtype str
        """
        return self.tr("Fastexport")

    @pyqtSlot()
    def __hgFastexport(self):
        """
        Private slot used to generate a git fast-import file.
        """
        self.vcs.getExtensionObject("fastexport").hgFastexport()
