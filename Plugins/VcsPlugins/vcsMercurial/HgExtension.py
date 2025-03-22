# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the base class for Mercurial extension interfaces.
"""

from PyQt6.QtCore import QObject


class HgExtension(QObject):
    """
    Class implementing the base class for Mercurial extension interfaces.
    """

    def __init__(self, vcs, ui=None):
        """
        Constructor

        @param vcs reference to the Mercurial vcs object
        @type Hg
        @param ui reference to a UI widget (defaults to None)
        @type QWidget
        """
        super().__init__(vcs)

        self.vcs = vcs
        self.ui = ui

    def shutdown(self):
        """
        Public method used to shutdown the extension interface.

        The method of this base class does nothing.
        """
        pass
