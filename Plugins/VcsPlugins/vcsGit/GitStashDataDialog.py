# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a stash operation.
"""

import enum

from PyQt6.QtWidgets import QDialog

from .Ui_GitStashDataDialog import Ui_GitStashDataDialog


class GitStashKind(enum.Enum):
    """
    Class defining the kind of stash to be performed.
    """

    NoUntracked = 0
    UntrackedOnly = 1
    UntrackedAndIgnored = 2


class GitStashDataDialog(QDialog, Ui_GitStashDataDialog):
    """
    Class implementing a dialog to enter the data for a stash operation.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getData(self):
        """
        Public method to get the user data.

        @return tuple containing the message, a flag indicating to keep changes
            in the staging area and an indication to stash untracked and/or
            ignored files
        @rtype tuple of (str, bool, GitStashKind)
        """
        if self.noneRadioButton.isChecked():
            untracked = GitStashKind.NoUntracked
        elif self.untrackedRadioButton.isChecked():
            untracked = GitStashKind.UntrackedOnly
        else:
            untracked = GitStashKind.UntrackedAndIgnored

        return (self.messageEdit.text(), self.keepCheckBox.isChecked(), untracked)
