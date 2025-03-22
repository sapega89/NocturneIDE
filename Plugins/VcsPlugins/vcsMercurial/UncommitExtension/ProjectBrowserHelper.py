# -*- coding: utf-8 -*-

# Copyright (c) 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the uncommit extension project browser helper.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QMenu

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricMessageBox

from ..HgExtensionProjectBrowserHelper import HgExtensionProjectBrowserHelper


class UncommitProjectBrowserHelper(HgExtensionProjectBrowserHelper):
    """
    Class implementing the uncommit extension project browser helper.
    """

    def __init__(self, vcsObject, browserObject, projectObject):
        """
        Constructor

        @param vcsObject reference to the vcs object
        @type Hg
        @param browserObject reference to the project browser object
        @type ProjectBaseBrowser
        @param projectObject reference to the project object
        @type Project
        """
        super().__init__(vcsObject, browserObject, projectObject)

    def initMenus(self):
        """
        Public method to generate the extension menus.

        @return dictionary of populated menu. The dict must have the keys 'mainMenu',
            'multiMenu', 'backMenu', 'dirMenu' and 'dirMultiMenu'.
        @rtype dict of QMenu
        """
        self.__menus = {}

        menu = QMenu(self.menuTitle())
        menu.setIcon(EricPixmapCache.getIcon("vcsUncommit"))
        menu.setTearOffEnabled(True)
        menu.addAction(
            EricPixmapCache.getIcon("vcsUncommit"),
            self.tr("Undo Local Commit"),
            self.__hgUncommit,
        )
        self.__menus["mainMenu"] = menu

        menu = QMenu(self.menuTitle())
        menu.setIcon(EricPixmapCache.getIcon("vcsUncommit"))
        menu.setTearOffEnabled(True)
        menu.addAction(
            EricPixmapCache.getIcon("vcsUncommit"),
            self.tr("Undo Local Commit"),
            self.__hgUncommit,
        )
        self.__menus["multiMenu"] = menu

        menu = QMenu(self.menuTitle())
        menu.setIcon(EricPixmapCache.getIcon("vcsUncommit"))
        menu.setTearOffEnabled(True)
        menu.addAction(
            EricPixmapCache.getIcon("vcsUncommit"),
            self.tr("Undo Local Commit"),
            self.__hgUncommit,
        )
        self.__menus["dirMenu"] = menu

        menu = QMenu(self.menuTitle())
        menu.setIcon(EricPixmapCache.getIcon("vcsUncommit"))
        menu.setTearOffEnabled(True)
        menu.addAction(
            EricPixmapCache.getIcon("vcsUncommit"),
            self.tr("Undo Local Commit"),
            self.__hgUncommit,
        )
        self.__menus["dirMultiMenu"] = menu

        return self.__menus

    def menuTitle(self):
        """
        Public method to get the menu title.

        @return title of the menu
        @rtype str
        """
        return self.tr("Uncommit")

    def showMenu(self, key, controlled):
        """
        Public method to prepare the extension menu for display.

        @param key menu key (one of 'mainMenu', 'multiMenu', 'backMenu', 'dirMenu'
            or 'dirMultiMenu')
        @type str
        @param controlled flag indicating to prepare the menu for a
            version controlled entry or a non-version controlled entry
        @type bool
        """
        if key in self.__menus:
            self.__menus[key].setEnabled(controlled)

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
        Private slot to undo the effect of a local commit.
        """
        names = []
        for itm in self.browser.getSelectedItems():
            try:
                name = itm.fileName()
            except AttributeError:
                name = itm.dirName()
            names.append(name)
        shouldReopen = self.vcs.getExtensionObject("uncommit").hgUncommit(names)
        self.__reopenProject(shouldReopen, self.tr("Undo Local Commit"))
