# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to list all files not tracked by Mercurial.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from .Ui_HgPurgeListDialog import Ui_HgPurgeListDialog


class HgPurgeListDialog(QDialog, Ui_HgPurgeListDialog):
    """
    Class implementing a dialog to list all files not tracked by Mercurial.
    """

    def __init__(self, entries, parent=None):
        """
        Constructor

        @param entries list of entries to be shown
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.purgeList.addItems(sorted(entries))
