# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a backout operation.
"""

from PyQt6.QtCore import QDateTime, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricApplication import ericApp

from .Ui_HgBackoutDialog import Ui_HgBackoutDialog


class HgBackoutDialog(QDialog, Ui_HgBackoutDialog):
    """
    Class implementing a dialog to enter the data for a backout operation.
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
        self.noneButton.toggled.connect(self.__updateOK)

        self.idEdit.textChanged.connect(self.__updateOK)
        self.expressionEdit.textChanged.connect(self.__updateOK)

        self.tagCombo.editTextChanged.connect(self.__updateOK)
        self.branchCombo.editTextChanged.connect(self.__updateOK)
        self.bookmarkCombo.editTextChanged.connect(self.__updateOK)

        self.__initDateTime = QDateTime.currentDateTime()
        self.dateEdit.setDateTime(self.__initDateTime)

    @pyqtSlot()
    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = True
        if self.noneButton.isChecked():
            enabled = False
        elif self.idButton.isChecked():
            enabled = bool(self.idEdit.text())
        elif self.tagButton.isChecked():
            enabled = bool(self.tagCombo.currentText())
        elif self.branchButton.isChecked():
            enabled = bool(self.branchCombo.currentText())
        elif self.bookmarkButton.isChecked():
            enabled = bool(self.bookmarkCombo.currentText())
        elif self.expressionButton.isChecked():
            enabled = enabled and bool(self.expressionEdit.text())

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    def getParameters(self):
        """
        Public method to retrieve the backout data.

        @return tuple naming the revision, a flag indicating a
            merge, the commit date, the commit user and a commit message
        @rtype tuple of (str, bool, str, str, str)
        """
        if self.numberButton.isChecked():
            rev = "rev({0})".format(self.numberSpinBox.value())
        elif self.idButton.isChecked():
            rev = "id({0})".format(self.idEdit.text())
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

        date = (
            self.dateEdit.dateTime().toString("yyyy-MM-dd hh:mm")
            if self.dateEdit.dateTime() != self.__initDateTime
            else ""
        )

        msg = (
            self.messageEdit.toPlainText()
            if self.messageEdit.toPlainText()
            else self.tr("Backed out changeset <{0}>.").format(rev)
        )

        return (rev, self.mergeCheckBox.isChecked, date, self.userEdit.text(), msg)
