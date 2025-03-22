# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter data for the Mercurial import command.
"""

from PyQt6.QtCore import QDateTime, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_HgImportDialog import Ui_HgImportDialog


class HgImportDialog(QDialog, Ui_HgImportDialog):
    """
    Class implementing a dialog to enter data for the Mercurial import command.
    """

    def __init__(self, vcs, parent=None):
        """
        Constructor

        @param vcs reference to the VCS object
        @type Hg
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.patchFilePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.patchFilePicker.setFilters(
            self.tr("Patch Files (*.diff *.patch);;All Files (*)")
        )

        self.secretCheckBox.setEnabled(vcs.version >= (5, 3, 0))

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        project = ericApp().getObject("Project")
        pwl, pel = project.getProjectDictionaries()
        language = project.getProjectSpellLanguage()
        self.messageEdit.setLanguageWithPWL(language, pwl or None, pel or None)

        self.__initDateTime = QDateTime.currentDateTime()
        self.dateEdit.setDateTime(self.__initDateTime)

    def __updateOK(self):
        """
        Private slot to update the OK button.
        """
        enabled = True
        if self.patchFilePicker.text() == "":
            enabled = False

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enabled)

    @pyqtSlot(str)
    def on_patchFilePicker_textChanged(self, _txt):
        """
        Private slot to react on changes of the patch file edit.

        @param _txt contents of the line edit (unused)
        @type str
        """
        self.__updateOK()

    def getParameters(self):
        """
        Public method to retrieve the import data.

        @return tuple naming the patch file, a flag indicating to not commit,
            a commit message, a commit date, a commit user, a flag indicating
            to commit with the secret phase, a strip count and a flag
            indicating to enforce the import
        @rtype tuple of (str, bool, str, str, str, bool, int, bool)
        """
        date = (
            self.dateEdit.dateTime().toString("yyyy-MM-dd hh:mm")
            if self.dateEdit.dateTime() != self.__initDateTime
            else ""
        )

        return (
            self.patchFilePicker.text(),
            self.noCommitCheckBox.isChecked(),
            self.messageEdit.toPlainText(),
            date,
            self.userEdit.text(),
            self.secretCheckBox.isChecked(),
            self.stripSpinBox.value(),
            self.forceCheckBox.isChecked(),
        )
