# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter options used to start a project in
the VCS.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_HgOptionsDialog import Ui_HgOptionsDialog


class HgOptionsDialog(QDialog, Ui_HgOptionsDialog):
    """
    Class implementing a dialog to enter options used to start a project in the
    repository.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getData(self):
        """
        Public slot to retrieve the data entered into the dialog.

        @return a dictionary containing the data entered
        @rtype dict
        """
        vcsdatadict = {
            "message": self.vcsLogEdit.text(),
        }
        return vcsdatadict
