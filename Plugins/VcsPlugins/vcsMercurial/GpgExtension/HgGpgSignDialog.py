# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter data for signing a revision.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricApplication import ericApp

from .Ui_HgGpgSignDialog import Ui_HgGpgSignDialog


class HgGpgSignDialog(QDialog, Ui_HgGpgSignDialog):
    """
    Class implementing a dialog to enter data for signing a revision.
    """

    def __init__(self, tagsList, branchesList, bookmarksList=None, parent=None):
        """
        Constructor

        @param tagsList list of tags
        @type list of str
        @param branchesList list of branches
        @type list of str
        @param bookmarksList list of bookmarks
        @type list of str
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        project = ericApp().getObject("Project")
        pwl, pel = project.getProjectDictionaries()
        language = project.getProjectSpellLanguage()
        self.messageEdit.setLanguageWithPWL(language, pwl or None, pel or None)

        self.tagCombo.addItems(sorted(tagsList))
        self.branchCombo.addItems(["default"] + sorted(branchesList))
        if bookmarksList is not None:
            self.bookmarkCombo.addItems(sorted(bookmarksList))
        else:
            self.bookmarkButton.setHidden(True)
            self.bookmarkCombo.setHidden(True)

        # connect various radio buttons and input fields
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

    @pyqtSlot()
    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = True
        if self.idButton.isChecked():
            enabled = enabled and self.idEdit.text() != ""
        elif self.tagButton.isChecked():
            enabled = enabled and self.tagCombo.currentText() != ""
        elif self.branchButton.isChecked():
            enabled = enabled and self.branchCombo.currentText() != ""
        elif self.bookmarkButton.isChecked():
            enabled = enabled and self.bookmarkCombo.currentText() != ""
        elif self.expressionButton.isChecked():
            enabled = enabled and bool(self.expressionEdit.text())

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple giving the revision, a flag indicating not to commit
            the signature, a commit message, an ID of the key to be used,
            a flag indicating a local signature and a flag indicating a forced
            signature
        @rtype tuple of (str, bool, str, str, bool, bool)
        """
        if self.numberButton.isChecked():
            rev = str(self.numberSpinBox.value())
        elif self.idButton.isChecked():
            rev = self.idEdit.text()
        elif self.tagButton.isChecked():
            rev = self.tagCombo.currentText()
        elif self.branchButton.isChecked():
            rev = self.branchCombo.currentText()
        elif self.bookmarkButton.isChecked():
            rev = self.bookmarkCombo.currentText()
        elif self.expressionButton.isChecked():
            rev = self.expressionEdit.text()
        else:
            rev = ""

        return (
            rev,
            self.nocommitCheckBox.isChecked(),
            self.messageEdit.toPlainText(),
            self.keyEdit.text(),
            self.localCheckBox.isChecked(),
            self.forceCheckBox.isChecked(),
        )
