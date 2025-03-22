# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the project helper base for Mercurial extension interfaces.
"""

from PyQt6.QtCore import QObject
from PyQt6.QtWidgets import QMenu


class HgExtensionProjectHelper(QObject):
    """
    Class implementing the project helper base for Mercurial extension
    interfaces.

    Note: The methods initActions(), initMenu(mainMenu) and menuTitle() have
    to be reimplemented by derived classes.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.actions = []

        self.initActions()

    def setObjects(self, vcsObject, projectObject):
        """
        Public method to set references to the vcs and project objects.

        @param vcsObject reference to the vcs object
        @type Hg
        @param projectObject reference to the project object
        @type Project
        """
        self.vcs = vcsObject
        self.project = projectObject

    def getActions(self):
        """
        Public method to get a list of all actions.

        @return list of all actions
        @rtype list of EricAction
        """
        return self.actions[:]

    def initActions(self):
        """
        Public method to generate the action objects.

        Note: Derived class must implement this method.

        @exception NotImplementedError raised if the class has not been
            reimplemented
        """
        raise NotImplementedError

    def initMenu(self, mainMenu):
        """
        Public method to generate the extension menu.

        Note: Derived class must implement this method.

        @param mainMenu reference to the main menu
        @type QMenu
        @return populated menu
        @rtype QMenu
        @exception NotImplementedError raised if the class has not been
            reimplemented
        """
        raise NotImplementedError

        return QMenu()

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

    def shutdown(self):
        """
        Public method to perform shutdown actions.

        Note: Derived class may implement this method if needed.
        """
        pass
