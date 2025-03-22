# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a tagging operation.
"""

import enum

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_GitTagDialog import Ui_GitTagDialog


class GitTagOperation(enum.Enum):
    """
    Class defining the supported git tag operations.
    """

    Create = 1
    Delete = 2
    Verify = 3


class GitTagType(enum.Enum):
    """
    Class defining the supported git tag types.
    """

    Annotated = 1
    Signed = 2
    Local = 3


class GitTagDialog(QDialog, Ui_GitTagDialog):
    """
    Class implementing a dialog to enter the data for a tagging operation.
    """

    def __init__(self, taglist, revision=None, tagName=None, parent=None):
        """
        Constructor

        @param taglist list of previously entered tags
        @type list of str
        @param revision revision to set tag for
        @type str
        @param tagName name of the tag
        @type str
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.okButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.okButton.setEnabled(False)

        self.tagCombo.clear()
        self.tagCombo.addItem("")
        self.tagCombo.addItems(sorted(taglist, reverse=True))

        if revision:
            self.revisionEdit.setText(revision)

        if tagName:
            index = self.tagCombo.findText(tagName)
            if index > -1:
                self.tagCombo.setCurrentIndex(index)
                # suggest the most relevant tag action
                self.verifyTagButton.setChecked(True)
            else:
                self.tagCombo.setEditText(tagName)
                self.createTagButton.setChecked(True)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(str)
    def on_tagCombo_editTextChanged(self, text):
        """
        Private method used to enable/disable the OK-button.

        @param text tag name entered in the combo
        @type str
        """
        self.okButton.setDisabled(text == "")

    def getParameters(self):
        """
        Public method to retrieve the tag data.

        @return tuple containing the tag, revision, tag operation, tag type,
            and a flag indicating to enforce the operation
        @rtype tuple of (str, str, GitTagOperation, GitTagType, bool)
        """
        tag = self.tagCombo.currentText().replace(" ", "_")

        if self.createTagButton.isChecked():
            tagOp = GitTagOperation.Create
        elif self.deleteTagButton.isChecked():
            tagOp = GitTagOperation.Delete
        else:
            tagOp = GitTagOperation.Verify

        if self.globalTagButton.isChecked():
            tagType = GitTagType.Annotated
        elif self.signedTagButton.isChecked():
            tagType = GitTagType.Signed
        else:
            tagType = GitTagType.Local

        return (
            tag,
            self.revisionEdit.text(),
            tagOp,
            tagType,
            self.forceCheckBox.isChecked(),
        )
