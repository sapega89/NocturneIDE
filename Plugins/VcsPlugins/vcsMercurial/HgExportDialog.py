# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter data for the Mercurial export command.
"""

import os

from PyQt6.QtCore import QDir, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_HgExportDialog import Ui_HgExportDialog


class HgExportDialog(QDialog, Ui_HgExportDialog):
    """
    Class implementing a dialog to enter data for the Mercurial export command.
    """

    def __init__(self, bookmarksList, bookmarkAvailable, parent=None):
        """
        Constructor

        @param bookmarksList list of defined bookmarks
        @type list of str
        @param bookmarkAvailable flag indicating the availability of the
            "--bookmark" option
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.directoryPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        # set default values for directory and pattern
        self.patternEdit.setText("%b_%r_%h_%n_of_%N.diff")
        self.directoryPicker.setText(QDir.tempPath())

        self.bookmarkCombo.addItem("")
        self.bookmarkCombo.addItems(sorted(bookmarksList))
        self.bookmarkCombo.setEnabled(bookmarkAvailable)

    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = True

        if (
            self.directoryPicker.text() == ""
            or self.patternEdit.text() == ""
            or (
                self.changesetsEdit.toPlainText() == ""
                and self.bookmarkCombo.currentText() == ""
            )
        ):
            enabled = False

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    @pyqtSlot(str)
    def on_directoryPicker_textChanged(self, _txt):
        """
        Private slot to react on changes of the export directory edit.

        @param _txt contents of the line edit (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_patternEdit_textChanged(self, _txt):
        """
        Private slot to react on changes of the export file name pattern edit.

        @param _txt contents of the line edit (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot()
    def on_changesetsEdit_textChanged(self):
        """
        Private slot to react on changes of the changesets edit.
        """
        self.__updateOK()

    def getParameters(self):
        """
        Public method to retrieve the export data.

        @return tuple naming the output file name, the list of revisions to
            export, the name of a bookmarked branch and flags indicating to
            compare against the second parent, to treat all files as text,
            to omit dates in the diff headers and to use the git extended
            diff format
        @rtype tuple of (str, list of str, str, bool, bool, bool, bool)
        """
        return (
            os.path.join(self.directoryPicker.text(), self.patternEdit.text()),
            self.changesetsEdit.toPlainText().splitlines(),
            self.bookmarkCombo.currentText(),
            self.switchParentCheckBox.isChecked(),
            self.textCheckBox.isChecked(),
            self.datesCheckBox.isChecked(),
            self.gitCheckBox.isChecked(),
        )
