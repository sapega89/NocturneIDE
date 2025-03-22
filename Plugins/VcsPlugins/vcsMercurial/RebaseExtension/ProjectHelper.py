# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the rebase extension project helper.
"""

from PyQt6.QtWidgets import QMenu

from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction
from eric7.EricWidgets import EricMessageBox

from ..HgExtensionProjectHelper import HgExtensionProjectHelper


class RebaseProjectHelper(HgExtensionProjectHelper):
    """
    Class implementing the rebase extension project helper.
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
        self.hgRebaseAct = EricAction(
            self.tr("Rebase Changesets"),
            EricPixmapCache.getIcon("vcsRebase"),
            self.tr("Rebase Changesets"),
            0,
            0,
            self,
            "mercurial_rebase",
        )
        self.hgRebaseAct.setStatusTip(self.tr("Rebase changesets to another branch"))
        self.hgRebaseAct.setWhatsThis(
            self.tr(
                """<b>Rebase Changesets</b>"""
                """<p>This rebases changesets to another branch.</p>"""
            )
        )
        self.hgRebaseAct.triggered.connect(self.__hgRebase)
        self.actions.append(self.hgRebaseAct)

        self.hgRebaseContinueAct = EricAction(
            self.tr("Continue Rebase Session"),
            self.tr("Continue Rebase Session"),
            0,
            0,
            self,
            "mercurial_rebase_continue",
        )
        self.hgRebaseContinueAct.setStatusTip(
            self.tr("Continue the last rebase session after repair")
        )
        self.hgRebaseContinueAct.setWhatsThis(
            self.tr(
                """<b>Continue Rebase Session</b>"""
                """<p>This continues the last rebase session after repair.</p>"""
            )
        )
        self.hgRebaseContinueAct.triggered.connect(self.__hgRebaseContinue)
        self.actions.append(self.hgRebaseContinueAct)

        self.hgRebaseAbortAct = EricAction(
            self.tr("Abort Rebase Session"),
            self.tr("Abort Rebase Session"),
            0,
            0,
            self,
            "mercurial_rebase_abort",
        )
        self.hgRebaseAbortAct.setStatusTip(self.tr("Abort the last rebase session"))
        self.hgRebaseAbortAct.setWhatsThis(
            self.tr(
                """<b>Abort Rebase Session</b>"""
                """<p>This aborts the last rebase session.</p>"""
            )
        )
        self.hgRebaseAbortAct.triggered.connect(self.__hgRebaseAbort)
        self.actions.append(self.hgRebaseAbortAct)

    def initMenu(self, mainMenu):
        """
        Public method to generate the extension menu.

        @param mainMenu reference to the main menu
        @type QMenu
        @return populated menu
        @rtype QMenu
        """
        menu = QMenu(self.menuTitle(), mainMenu)
        menu.setIcon(EricPixmapCache.getIcon("vcsRebase"))
        menu.setTearOffEnabled(True)

        menu.addAction(self.hgRebaseAct)
        menu.addAction(self.hgRebaseContinueAct)
        menu.addAction(self.hgRebaseAbortAct)

        return menu

    def menuTitle(self):
        """
        Public method to get the menu title.

        @return title of the menu
        @rtype str
        """
        return self.tr("Rebase")

    def __hgRebase(self):
        """
        Private slot used to rebase changesets to another branch.
        """
        shouldReopen = self.vcs.getExtensionObject("rebase").hgRebase()
        if shouldReopen:
            res = EricMessageBox.yesNo(
                None,
                self.tr("Rebase Changesets"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __hgRebaseContinue(self):
        """
        Private slot used to continue the last rebase session after repair.
        """
        shouldReopen = self.vcs.getExtensionObject("rebase").hgRebaseContinue()
        if shouldReopen:
            res = EricMessageBox.yesNo(
                None,
                self.tr("Rebase Changesets (Continue)"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()

    def __hgRebaseAbort(self):
        """
        Private slot used to abort the last rebase session.
        """
        shouldReopen = self.vcs.getExtensionObject("rebase").hgRebaseAbort()
        if shouldReopen:
            res = EricMessageBox.yesNo(
                None,
                self.tr("Rebase Changesets (Abort)"),
                self.tr("""The project should be reread. Do this now?"""),
                yesDefault=True,
            )
            if res:
                self.project.reopenProject()
