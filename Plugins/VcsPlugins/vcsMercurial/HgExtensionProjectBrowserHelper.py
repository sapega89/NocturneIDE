# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the project browser helper base for Mercurial extension
interfaces.
"""

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QMenu


class HgExtensionProjectBrowserHelper(QObject):
    """
    Class implementing the project browser helper base for Mercurial extension
    interfaces.

    Note: The methods initMenus() and menuTitle() have to be reimplemented by
    derived classes.
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
        super().__init__()

        self.vcs = vcsObject
        self.browser = browserObject
        self.project = projectObject

    def initMenus(self):
        """
        Public method to generate the extension menus.

        Note: Derived class must implement this method.

        @return dictionary of populated menu. The dict must have the keys
            'mainMenu', 'multiMenu', 'backMenu', 'dirMenu' and 'dirMultiMenu'.
        @rtype dict of QMenu
        @exception NotImplementedError raised if the class has not been
            reimplemented
        """
        raise NotImplementedError

        return {
            "mainMenu": QMenu(),
            "multiMenu": QMenu(),
            "backMenu": QMenu(),
            "dirMenu": QMenu(),
            "dirMultiMenu": QMenu(),
        }

    def menuTitle(self):
        """
        Public method to get the menu title.

        Note: Derived class must implement this method.

        @return title of the menu
        @rtype str
        @exception NotImplementedError raised if the class has not been
            reimplemented
        """
        raise NotImplementedError

        return ""

    def showMenu(self, key, controlled):
        """
        Public method to prepare the extension menu for display.

        Note: Derived class must implement this method to adjust the
        enabled states of its menus.

        @param key menu key (one of 'mainMenu', 'multiMenu',
            'backMenu', 'dirMenu' or 'dirMultiMenu')
        @type str
        @param controlled flag indicating to prepare the menu for a
            version controlled entry or a non-version controlled entry
        @type bool
        @exception NotImplementedError raised if the class has not been
            reimplemented
        """
        raise NotImplementedError

    def _updateVCSStatus(self, name):
        """
        Protected method to update the VCS status of an item.

        @param name filename or directory name of the item to be updated
        @type str
        """
        self.project.getModel().updateVCSStatus(name)
