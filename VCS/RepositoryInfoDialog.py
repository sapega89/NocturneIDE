# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implemting a dialog to show repository information.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_RepositoryInfoDialog import Ui_VcsRepositoryInfoDialog


class VcsRepositoryInfoDialog(QDialog, Ui_VcsRepositoryInfoDialog):
    """
    Class implemting a dialog to show repository information.
    """

    def __init__(self, parent, info):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        @param info info data to show
        @type str
        """
        super().__init__(parent)
        self.setupUi(self)
        self.infoBrowser.setHtml(info)
