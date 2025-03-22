# -*- coding: utf-8 -*-

# Copyright (c) 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the uncommit extension project helper.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QMenu

from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox

from ..HgExtensionProjectHelper import HgExtensionProjectHelper


class UncommitProjectHelper(HgExtensionProjectHelper):
    """
    Class implementing the uncommit extension project helper.
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
        self.hgUncommitAct = EricAction(
            self.tr("Undo Local Commit"),
            EricPixmapCache.getIcon("vcsUncommit"),
            self.tr("Undo Local Commit"),
            0,
            0,
            self,
            "mercurial_uncommit",
        )
        self.hgUncommitAct.setStatusTip(self.tr("Undo the effect of a local commit."))
        self.hgUncommitAct.setWhatsThis(
            self.tr(
                """<b>Undo Local Commit</b>"""
                """<p>This undoes the effect of a local commit, returning the"""
                """ affected files to their uncommitted state.</p>"""
            )
        )
        self.hgUncommitAct.triggered.connect(self.__hgUncommit)
        self.actions.append(self.hgUncommitAct)

    def initMenu(self, mainMenu):
        """
        Public method to generate the extension menu.

        @param mainMenu reference to the main menu
        @type QMenu
        @return populated menu
        @rtype QMenu
        """
        menu = QMenu(self.menuTitle(), mainMenu)
        menu.setIcon(EricPixmapCache.getIcon("vcsUncommit"))
        menu.setTearOffEnabled(True)

        menu.addAction(self.hgUncommitAct)

        return menu

    def menuTitle(self):
        """
        Public method to get the menu title.

        @return title of the menu
        @rtype str
        """
        return self.tr("Uncommit")

    def __reopenProject(self, shouldReopen, title):
        """
        Private method to reopen the project if needed and wanted.

        @param shouldReopen flag indicating that the project should
            be reopened
        @type bool
        @param title title of the message box
        @type str
        """
        if shouldReopen:
            res = EricMessageBox.yesNo(
                None,
                title,
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    @pyqtSlot()
    def __hgUncommit(self):
        """
        Private slot to undo a local commit.
        """
        shouldReopen = self.vcs.getExtensionObject("uncommit").hgUncommit()
        self.__reopenProject(shouldReopen, self.tr("Undo Local Commit"))
