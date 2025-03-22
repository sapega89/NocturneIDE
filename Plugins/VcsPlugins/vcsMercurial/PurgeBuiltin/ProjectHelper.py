# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the purge extension project helper.
"""

from PyQt6.QtWidgets import QMenu

from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricAction import EricAction

from ..HgExtensionProjectHelper import HgExtensionProjectHelper


class PurgeProjectHelper(HgExtensionProjectHelper):
    """
    Class implementing the purge extension project helper.
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
        self.hgPurgeAct = EricAction(
            self.tr("Purge Files"),
            EricPixmapCache.getIcon("fileDelete"),
            self.tr("Purge Files"),
            0,
            0,
            self,
            "mercurial_purge",
        )
        self.hgPurgeAct.setStatusTip(
            self.tr("Delete not version controlled files and directories")
        )
        self.hgPurgeAct.setWhatsThis(
            self.tr(
                """<b>Purge Files</b>"""
                """<p>This deletes not version controlled files and directories."""
                """ That means that purge will delete:<ul>"""
                """<li>not version controlled files (marked with "not tracked" in"""
                """ the status dialog)</li>"""
                """<li>empty directories</li>"""
                """</ul>Note that ignored files will be left untouched.</p>"""
            )
        )
        self.hgPurgeAct.triggered.connect(self.__hgPurge)
        self.actions.append(self.hgPurgeAct)

        self.hgPurgeAllAct = EricAction(
            self.tr("Purge All Files"),
            self.tr("Purge All Files"),
            0,
            0,
            self,
            "mercurial_purge_all",
        )
        self.hgPurgeAllAct.setStatusTip(
            self.tr(
                "Delete not version controlled files and directories including"
                " ignored ones"
            )
        )
        self.hgPurgeAllAct.setWhatsThis(
            self.tr(
                """<b>Purge All Files</b>"""
                """<p>This deletes not version controlled files and directories."""
                """ That means that purge will delete:<ul>"""
                """<li>not version controlled files (marked with "not tracked" in"""
                """ the status dialog)</li>"""
                """<li>empty directories</li>"""
                """<li>ignored files and directories</li>"""
                """</ul></p>"""
            )
        )
        self.hgPurgeAllAct.triggered.connect(self.__hgPurgeAll)
        self.actions.append(self.hgPurgeAllAct)

        self.hgPurgeIgnoredAct = EricAction(
            self.tr("Purge Ignored Files"),
            self.tr("Purge Ignored Files"),
            0,
            0,
            self,
            "mercurial_purge_ignored",
        )
        self.hgPurgeIgnoredAct.setStatusTip(
            self.tr("Delete ignored files and directories")
        )
        self.hgPurgeIgnoredAct.setWhatsThis(
            self.tr(
                """<b>Purge Ignored Files</b>"""
                """<p>This deletes ignored files and directories.</p>"""
            )
        )
        self.hgPurgeIgnoredAct.triggered.connect(self.__hgPurgeIgnored)
        self.actions.append(self.hgPurgeIgnoredAct)

        self.hgPurgeListAct = EricAction(
            self.tr("List Files to be Purged"),
            EricPixmapCache.getIcon("fileDeleteList"),
            self.tr("List Files to be Purged..."),
            0,
            0,
            self,
            "mercurial_purge_list",
        )
        self.hgPurgeListAct.setStatusTip(
            self.tr("List not version controlled files and directories")
        )
        self.hgPurgeListAct.setWhatsThis(
            self.tr(
                """<b>List Files to be Purged</b>"""
                """<p>This lists not version controlled files and directories."""
                """ These would be deleted by the "Purge Files" menu entry.</p>"""
            )
        )
        self.hgPurgeListAct.triggered.connect(self.__hgPurgeList)
        self.actions.append(self.hgPurgeListAct)

        self.hgPurgeAllListAct = EricAction(
            self.tr("List All Files to be Purged"),
            self.tr("List All Files to be Purged..."),
            0,
            0,
            self,
            "mercurial_purge_all_list",
        )
        self.hgPurgeAllListAct.setStatusTip(
            self.tr(
                "List not version controlled files and directories including"
                " ignored ones"
            )
        )
        self.hgPurgeAllListAct.setWhatsThis(
            self.tr(
                """<b>List All Files to be Purged</b>"""
                """<p>This lists not version controlled files and directories"""
                """ including ignored ones. These would be deleted by the"""
                """ "Purge All Files" menu entry.</p>"""
            )
        )
        self.hgPurgeAllListAct.triggered.connect(self.__hgPurgeAllList)
        self.actions.append(self.hgPurgeAllListAct)

        self.hgPurgeIgnoredListAct = EricAction(
            self.tr("List Ignored Files to be Purged"),
            self.tr("List Ignored Files to be Purged..."),
            0,
            0,
            self,
            "mercurial_purge_ignored_list",
        )
        self.hgPurgeIgnoredListAct.setStatusTip(
            self.tr("List ignored files and directories")
        )
        self.hgPurgeIgnoredListAct.setWhatsThis(
            self.tr(
                """<b>List Ignored Files to be Purged</b>"""
                """<p>This lists ignored files and directories. These would be"""
                """ deleted by the "Purge Ignored Files" menu entry.</p>"""
            )
        )
        self.hgPurgeIgnoredListAct.triggered.connect(self.__hgPurgeIgnoredList)
        self.actions.append(self.hgPurgeIgnoredListAct)

    def initMenu(self, mainMenu):
        """
        Public method to generate the extension menu.

        @param mainMenu reference to the main menu
        @type QMenu
        @return populated menu
        @rtype QMenu
        """
        menu = QMenu(self.menuTitle(), mainMenu)
        menu.setIcon(EricPixmapCache.getIcon("fileDelete"))
        menu.setTearOffEnabled(True)

        menu.addAction(self.hgPurgeListAct)
        menu.addAction(self.hgPurgeAllListAct)
        menu.addAction(self.hgPurgeIgnoredListAct)
        menu.addSeparator()
        menu.addAction(self.hgPurgeAct)
        menu.addAction(self.hgPurgeAllAct)
        menu.addAction(self.hgPurgeIgnoredAct)

        return menu

    def menuTitle(self):
        """
        Public method to get the menu title.

        @return title of the menu
        @rtype str
        """
        return self.tr("Purge")

    def __hgPurge(self):
        """
        Private slot used to remove not version controlled files.
        """
        self.vcs.getBuiltinObject("purge").hgPurge(deleteAll=False, ignoredOnly=False)

    def __hgPurgeAll(self):
        """
        Private slot used to remove not version controlled files including ignored ones.
        """
        self.vcs.getBuiltinObject("purge").hgPurge(deleteAll=True, ignoredOnly=False)

    def __hgPurgeIgnored(self):
        """
        Private slot used to remove ignored files.
        """
        self.vcs.getBuiltinObject("purge").hgPurge(deleteAll=False, ignoredOnly=True)

    def __hgPurgeList(self):
        """
        Private slot used to list not version controlled files.
        """
        self.vcs.getBuiltinObject("purge").hgPurgeList(
            deleteAll=False, ignoredOnly=False
        )

    def __hgPurgeAllList(self):
        """
        Private slot used to list not version controlled files including ignored ones.
        """
        self.vcs.getBuiltinObject("purge").hgPurgeList(
            deleteAll=True, ignoredOnly=False
        )

    def __hgPurgeIgnoredList(self):
        """
        Private slot used to list ignored files.
        """
        self.vcs.getBuiltinObject("purge").hgPurgeList(
            deleteAll=False, ignoredOnly=True
        )
