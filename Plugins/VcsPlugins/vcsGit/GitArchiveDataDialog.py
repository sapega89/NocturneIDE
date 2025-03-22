# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for the creation of an archive.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_GitArchiveDataDialog import Ui_GitArchiveDataDialog


class GitArchiveDataDialog(QDialog, Ui_GitArchiveDataDialog):
    """
    Class implementing a dialog to enter the data for the creation of an
    archive.
    """

    def __init__(self, tagsList, branchesList, formatsList, parent=None):
        """
        Constructor

        @param tagsList list of tags
        @type list of str
        @param branchesList list of branches
        @type list of str
        @param formatsList list of archive formats
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.fileButton.setIcon(EricPixmapCache.getIcon("open"))

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.tagCombo.addItems(sorted(tagsList))
        self.branchCombo.addItems(["main"] + sorted(branchesList))
        self.formatComboBox.addItems(sorted(formatsList))
        self.formatComboBox.setCurrentIndex(self.formatComboBox.findText("zip"))

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = True
        if self.revButton.isChecked():
            enabled = self.revEdit.text() != ""
        elif self.tagButton.isChecked():
            enabled = self.tagCombo.currentText() != ""
        elif self.branchButton.isChecked():
            enabled = self.branchCombo.currentText() != ""

        enabled &= bool(self.fileEdit.text())

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    @pyqtSlot(str)
    def on_fileEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the file edit.

        @param _txt text of the edit (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot()
    def on_fileButton_clicked(self):
        """
        Private slot to select a file via a file selection dialog.
        """
        fileName = EricFileDialog.getSaveFileName(
            self,
            self.tr("Select Archive File"),
            FileSystemUtilities.fromNativeSeparators(self.fileEdit.text()),
            "",
        )

        if fileName:
            root, ext = os.path.splitext(fileName)
            if not ext:
                ext = "." + self.formatComboBox.currentText()
            fileName = root + ext
            self.fileEdit.setText(FileSystemUtilities.toNativeSeparators(fileName))

    @pyqtSlot(bool)
    def on_revButton_toggled(self, _checked):
        """
        Private slot to handle changes of the rev select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_revEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the rev edit.

        @param _txt text of the edit (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(bool)
    def on_tagButton_toggled(self, _checked):
        """
        Private slot to handle changes of the Tag select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_tagCombo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the Tag combo.

        @param _txt text of the combo (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(bool)
    def on_branchButton_toggled(self, _checked):
        """
        Private slot to handle changes of the Branch select button.

        @param _checked state of the button (unused)
        @type bool
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_branchCombo_editTextChanged(self, _txt):
        """
        Private slot to handle changes of the Branch combo.

        @param _txt text of the combo (unused)
        @type str
        """
        self.__updateOK()

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple of selected revision, archive format, archive file and prefix
        @rtype tuple of (str, str, str, str)
        """
        if self.revButton.isChecked():
            rev = self.revEdit.text()
        elif self.tagButton.isChecked():
            rev = self.tagCombo.currentText()
        elif self.branchButton.isChecked():
            rev = self.branchCombo.currentText()
        else:
            rev = "HEAD"

        return (
            rev,
            self.formatComboBox.currentText(),
            FileSystemUtilities.toNativeSeparators(self.fileEdit.text()),
            self.prefixEdit.text(),
        )
