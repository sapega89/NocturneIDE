# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the gpg extension project helper.
"""

from PyQt6.QtWidgets import QMenu

from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction

from ..HgExtensionProjectHelper import HgExtensionProjectHelper


class GpgProjectHelper(HgExtensionProjectHelper):
    """
    Class implementing the gpg extension project helper.
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
        self.hgGpgListAct = EricAction(
            self.tr("List Signed Changesets"),
            EricPixmapCache.getIcon("changesetSignList"),
            self.tr("List Signed Changesets..."),
            0,
            0,
            self,
            "mercurial_gpg_list",
        )
        self.hgGpgListAct.setStatusTip(self.tr("List signed changesets"))
        self.hgGpgListAct.setWhatsThis(
            self.tr(
                """<b>List Signed Changesets</b>"""
                """<p>This opens a dialog listing all signed changesets.</p>"""
            )
        )
        self.hgGpgListAct.triggered.connect(self.__hgGpgSignatures)
        self.actions.append(self.hgGpgListAct)

        self.hgGpgVerifyAct = EricAction(
            self.tr("Verify Signatures"),
            EricPixmapCache.getIcon("changesetSignVerify"),
            self.tr("Verify Signatures"),
            0,
            0,
            self,
            "mercurial_gpg_verify",
        )
        self.hgGpgVerifyAct.setStatusTip(
            self.tr("Verify all signatures there may be for a particular revision")
        )
        self.hgGpgVerifyAct.setWhatsThis(
            self.tr(
                """<b>Verify Signatures</b>"""
                """<p>This verifies all signatures there may be for a particular"""
                """ revision.</p>"""
            )
        )
        self.hgGpgVerifyAct.triggered.connect(self.__hgGpgVerifySignatures)
        self.actions.append(self.hgGpgVerifyAct)

        self.hgGpgSignAct = EricAction(
            self.tr("Sign Revision"),
            EricPixmapCache.getIcon("changesetSign"),
            self.tr("Sign Revision"),
            0,
            0,
            self,
            "mercurial_gpg_sign",
        )
        self.hgGpgSignAct.setStatusTip(
            self.tr("Add a signature for a selected revision")
        )
        self.hgGpgSignAct.setWhatsThis(
            self.tr(
                """<b>Sign Revision</b>"""
                """<p>This adds a signature for a selected revision.</p>"""
            )
        )
        self.hgGpgSignAct.triggered.connect(self.__hgGpgSign)
        self.actions.append(self.hgGpgSignAct)

    def initMenu(self, mainMenu):
        """
        Public method to generate the extension menu.

        @param mainMenu reference to the main menu
        @type QMenu
        @return populated menu
        @rtype QMenu
        """
        menu = QMenu(self.menuTitle(), mainMenu)
        menu.setIcon(EricPixmapCache.getIcon("changesetSign"))
        menu.setTearOffEnabled(True)

        menu.addAction(self.hgGpgListAct)
        menu.addAction(self.hgGpgVerifyAct)
        menu.addAction(self.hgGpgSignAct)

        return menu

    def menuTitle(self):
        """
        Public method to get the menu title.

        @return title of the menu
        @rtype str
        """
        return self.tr("GPG")

    def __hgGpgSignatures(self):
        """
        Private slot used to list all signed changesets.
        """
        self.vcs.getExtensionObject("gpg").hgGpgSignatures()

    def __hgGpgVerifySignatures(self):
        """
        Private slot used to verify the signatures of a revision.
        """
        self.vcs.getExtensionObject("gpg").hgGpgVerifySignatures()

    def __hgGpgSign(self):
        """
        Private slot used to sign a revision.
        """
        self.vcs.getExtensionObject("gpg").hgGpgSign()
