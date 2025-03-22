# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the largefiles extension project browser helper.
"""

from PyQt6.QtWidgets import QMenu

from eric7.EricGui import EricPixmapCache

from ..HgExtensionProjectBrowserHelper import HgExtensionProjectBrowserHelper


class LargefilesProjectBrowserHelper(HgExtensionProjectBrowserHelper):
    """
    Class implementing the largefiles extension project browser helper.
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

        Note: Derived class must implement this method.

        @return dictionary of populated menu. The dict must have the keys
            'mainMenu', 'multiMenu', 'backMenu', 'dirMenu' and 'dirMultiMenu'.
        @rtype dict of QMenu
        """
        self.__menus = {}
        self.__addSingleActs = []
        self.__addMultiActs = []

        menu = QMenu(self.menuTitle())
        menu.setTearOffEnabled(True)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add as Large File"),
            lambda: self.__hgAddLargefiles("large"),
        )
        self.__addSingleActs.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add as Normal File"),
            lambda: self.__hgAddLargefiles("normal"),
        )
        self.__addSingleActs.append(act)
        self.__menus["mainMenu"] = menu

        menu = QMenu(self.menuTitle())
        menu.setTearOffEnabled(True)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add as Large Files"),
            lambda: self.__hgAddLargefiles("large"),
        )
        self.__addMultiActs.append(act)
        act = menu.addAction(
            EricPixmapCache.getIcon("vcsAdd"),
            self.tr("Add as Normal Files"),
            lambda: self.__hgAddLargefiles("normal"),
        )
        self.__addMultiActs.append(act)
        self.__menus["multiMenu"] = menu

        return self.__menus

    def menuTitle(self):
        """
        Public method to get the menu title.

        Note: Derived class must implement this method.

        @return title of the menu
        @rtype str
        """
        return self.tr("Large Files")

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
        if key == "mainMenu":
            for act in self.__addSingleActs:
                act.setEnabled(not controlled)
        elif key == "multiMenu":
            for act in self.__addMultiActs:
                act.setEnabled(not controlled)

    def __hgAddLargefiles(self, mode):
        """
        Private slot to add the selected files as large files.

        @param mode add mode (string ne of 'normal' or 'large')
        @type str
        """
        names = []
        for itm in self.browser.getSelectedItems():
            try:
                name = itm.fileName()
            except AttributeError:
                continue
            names.append(name)

        if names:
            if len(names) == 1:
                self.vcs.getExtensionObject("largefiles").hgAdd(names[0], mode)
            else:
                self.vcs.getExtensionObject("largefiles").hgAdd(names, mode)
            for fn in names:
                self._updateVCSStatus(fn)
