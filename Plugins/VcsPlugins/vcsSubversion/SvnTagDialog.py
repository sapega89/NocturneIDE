# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a tagging operation.
"""

from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_SvnTagDialog import Ui_SvnTagDialog


class SvnTagDialog(QDialog, Ui_SvnTagDialog):
    """
    Class implementing a dialog to enter the data for a tagging operation.
    """

    def __init__(self, taglist, reposURL, standardLayout, parent=None):
        """
        Constructor

        @param taglist list of previously entered tags
        @type list of str
        @param reposURL repository path or None
        @type str
        @param standardLayout flag indicating the layout of the
            repository
        @type bool
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.okButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)

        self.tagCombo.clear()
        self.tagCombo.addItems(sorted(taglist, reverse=True))

        if reposURL is not None and reposURL != "":
            self.tagCombo.setEditText(reposURL)

        if not standardLayout:
            self.TagActionGroup.setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def on_tagCombo_editTextChanged(self, text):
        """
        Private method used to enable/disable the OK-button.

        @param text text of the tag combobox
        @type str
        """
        self.okButton.setDisabled(text == "")

    def getParameters(self):
        """
        Public method to retrieve the tag data.

        @return tuple containing the tag and tag operation
        @rtype tuple of (str, int)
        """
        tag = self.tagCombo.currentText()
        tagOp = 0
        if self.createRegularButton.isChecked():
            tagOp = 1
        elif self.createBranchButton.isChecked():
            tagOp = 2
        elif self.deleteRegularButton.isChecked():
            tagOp = 4
        elif self.deleteBranchButton.isChecked():
            tagOp = 8
        return (tag, tagOp)
