# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a tagging operation.
"""

import enum

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricGui import EricPixmapCache

from .Ui_HgTagDialog import Ui_HgTagDialog


class HgTagOperation(enum.Enum):
    """
    Class defining the supported tagging operations.
    """

    CreateGlobal = 1
    CreateLocal = 2
    DeleteGlobal = 3
    DeleteLocal = 4


class HgTagDialog(QDialog, Ui_HgTagDialog):
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
        self.tagCombo.addItem("", False)
        for tag, isLocal in sorted(taglist, reverse=True):
            icon = (
                EricPixmapCache.getIcon("vcsTagLocal")
                if isLocal
                else EricPixmapCache.getIcon("vcsTagGlobal")
            )
            self.tagCombo.addItem(icon, tag, isLocal)

        if revision:
            self.revisionEdit.setText(revision)

        if tagName:
            index = self.tagCombo.findText(tagName)
            if index > -1:
                self.tagCombo.setCurrentIndex(index)
                # suggest the most relevant tag action
                self.deleteTagButton.setChecked(True)
            else:
                self.tagCombo.setEditText(tagName)

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

    @pyqtSlot(int)
    def on_tagCombo_currentIndexChanged(self, index):
        """
        Private slot setting the local status of the selected entry.

        @param index index of the selected entrie
        @type int
        """
        isLocal = self.tagCombo.itemData(index)
        if isLocal:
            self.localTagButton.setChecked(True)
        else:
            self.globalTagButton.setChecked(True)

    def getParameters(self):
        """
        Public method to retrieve the tag data.

        @return tuple containing the tag, revision, tag operation and a flag
            indicating to enforce the operation
        @rtype tuple of str, str, HgTagOperation, bool
        """
        tag = self.tagCombo.currentText().replace(" ", "_")
        tagOp = 0
        if self.createTagButton.isChecked():
            if self.globalTagButton.isChecked():
                tagOp = HgTagOperation.CreateGlobal
            else:
                tagOp = HgTagOperation.CreateLocal
        else:
            if self.globalTagButton.isChecked():
                tagOp = HgTagOperation.DeleteGlobal
            else:
                tagOp = HgTagOperation.DeleteLocal
        return (tag, self.revisionEdit.text(), tagOp, self.forceCheckBox.isChecked)
