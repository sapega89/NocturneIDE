# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the histedit parameters.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QButtonGroup, QDialog, QDialogButtonBox

from .Ui_HgHisteditConfigDialog import Ui_HgHisteditConfigDialog


class HgHisteditConfigDialog(QDialog, Ui_HgHisteditConfigDialog):
    """
    Class implementing a dialog to enter the histedit parameters.
    """

    def __init__(self, tagsList, branchesList, bookmarksList=None, rev="", parent=None):
        """
        Constructor

        @param tagsList list of tags
        @type list of str
        @param branchesList list of branches
        @type list of str
        @param bookmarksList list of bookmarks
        @type list of str
        @param rev revision to strip from
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__sourceRevisionButtonGroup = QButtonGroup(self)
        self.__sourceRevisionButtonGroup.addButton(self.defaultButton)
        self.__sourceRevisionButtonGroup.addButton(self.outgoingButton)
        self.__sourceRevisionButtonGroup.addButton(self.revisionButton)

        self.tagCombo.addItems(sorted(tagsList))
        self.branchCombo.addItems(["default"] + sorted(branchesList))
        if bookmarksList is not None:
            self.bookmarkCombo.addItems(sorted(bookmarksList))

        # connect various radio buttons and input fields
        self.defaultButton.toggled.connect(self.__updateOK)
        self.outgoingButton.toggled.connect(self.__updateOK)
        self.revisionButton.toggled.connect(self.__updateOK)
        self.idButton.toggled.connect(self.__updateOK)
        self.tagButton.toggled.connect(self.__updateOK)
        self.branchButton.toggled.connect(self.__updateOK)
        self.bookmarkButton.toggled.connect(self.__updateOK)
        self.expressionButton.toggled.connect(self.__updateOK)

        self.idEdit.textChanged.connect(self.__updateOK)
        self.expressionEdit.textChanged.connect(self.__updateOK)

        self.tagCombo.editTextChanged.connect(self.__updateOK)
        self.branchCombo.editTextChanged.connect(self.__updateOK)
        self.bookmarkCombo.editTextChanged.connect(self.__updateOK)

        self.numberSpinBox.valueChanged.connect(self.__updateOK)

        self.idEdit.setText(rev)
        if rev:
            self.revisionButton.setChecked(True)
        else:
            self.defaultButton.setChecked(True)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

        self.__updateOK()

    @pyqtSlot()
    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = True

        if self.revisionButton.isChecked():
            if self.idButton.isChecked():
                enabled = enabled and bool(self.idEdit.text())
            elif self.tagButton.isChecked():
                enabled = enabled and bool(self.tagCombo.currentText())
            elif self.branchButton.isChecked():
                enabled = enabled and bool(self.branchCombo.currentText())
            elif self.bookmarkButton.isChecked():
                enabled = enabled and bool(self.bookmarkCombo.currentText())
            elif self.expressionButton.isChecked():
                enabled = enabled and bool(self.expressionEdit.text())

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    def __getRevision(self):
        """
        Private method to generate the revision.

        @return revision
        @rtype str
        """
        if self.defaultButton.isChecked():
            return ""
        elif self.outgoingButton.isChecked():
            return "--outgoing"
        else:
            if self.numberButton.isChecked():
                return "rev({0})".format(self.numberSpinBox.value())
            elif self.idButton.isChecked():
                return "id({0})".format(self.idEdit.text())
            elif self.tagButton.isChecked():
                return self.tagCombo.currentText()
            elif self.branchButton.isChecked():
                return self.branchCombo.currentText()
            elif self.bookmarkButton.isChecked():
                return self.bookmarkCombo.currentText()
            elif self.expressionButton.isChecked():
                return self.expressionEdit.text()

        return ""

    def getData(self):
        """
        Public method to retrieve the data for the strip action.

        @return tuple with the revision, a flag indicating to to outgoing and a
            flag indicating to keep old nodes
        @rtype tuple (str, bool, bool)
        """
        return (
            self.__getRevision(),
            self.forceCheckBox.isChecked(),
            self.keepCheckBox.isChecked(),
        )
