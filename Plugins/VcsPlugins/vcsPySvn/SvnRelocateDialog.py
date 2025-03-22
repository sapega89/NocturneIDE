# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data to relocate the workspace.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_SvnRelocateDialog import Ui_SvnRelocateDialog


class SvnRelocateDialog(QDialog, Ui_SvnRelocateDialog):
    """
    Class implementing a dialog to enter the data to relocate the workspace.
    """

    def __init__(self, currUrl, parent=None):
        """
        Constructor

        @param currUrl current repository URL
        @type str
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.currUrlLabel.setText(currUrl)
        self.newUrlEdit.setText(currUrl)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getData(self):
        """
        Public slot used to retrieve the data entered into the dialog.

        @return the new repository URL and an indication, if the relocate is inside
            the repository
        @rtype tuple of (str, bool)
        """
        return self.newUrlEdit.text(), self.insideCheckBox.isChecked()
