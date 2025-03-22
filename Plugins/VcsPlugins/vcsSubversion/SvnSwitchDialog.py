# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a switch operation.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_SvnSwitchDialog import Ui_SvnSwitchDialog


class SvnSwitchDialog(QDialog, Ui_SvnSwitchDialog):
    """
    Class implementing a dialog to enter the data for a switch operation.
    """

    def __init__(self, taglist, reposURL, standardLayout, parent=None):
        """
        Constructor

        @param taglist list of previously entered tags
        @type list of str
        @param reposURL repository path or None
        @type str
        @param standardLayout flag indicating the layout of the repository
        @type bool
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.tagCombo.clear()
        self.tagCombo.addItems(sorted(taglist))

        if reposURL is not None and reposURL != "":
            self.tagCombo.setEditText(reposURL)

        if not standardLayout:
            self.TagTypeGroup.setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getParameters(self):
        """
        Public method to retrieve the tag data.

        @return tuple containing the tag and tag type)
        @rtype tuple of (str, int)
        """
        tag = self.tagCombo.currentText()
        tagType = 0
        if self.regularButton.isChecked():
            tagType = 1
        elif self.branchButton.isChecked():
            tagType = 2
        if not tag:
            tagType = 4
        return (tag, tagType)
