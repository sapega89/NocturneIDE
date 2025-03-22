# -*- coding: utf-8 -*-

# Copyright (c) 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the fastexport configuration dialog.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_HgFastexportConfigDialog import Ui_HgFastexportConfigDialog


class HgFastexportConfigDialog(QDialog, Ui_HgFastexportConfigDialog):
    """
    Class implementing the fastexport configuration dialog.
    """

    def __init__(self, revisions=None, parent=None):
        """
        Constructor

        @param revisions list of revisions, tags or branches to be exported
            (defaults to None)
        @type list of str (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.outputPicker.setMode(EricPathPickerModes.SAVE_FILE_ENSURE_EXTENSION_MODE)
        self.authormapPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.importMarksPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.exportMarksPicker.setMode(
            EricPathPickerModes.SAVE_FILE_ENSURE_EXTENSION_MODE
        )
        fileFilters = self.tr("Text Files (*.txt);;All Files (*)")
        for picker in (
            self.outputPicker,
            self.authormapPicker,
            self.importMarksPicker,
            self.exportMarksPicker,
        ):
            picker.setFilters(fileFilters)

        self.outputPicker.textChanged.connect(self.__updateOK)

        if revisions:
            self.revisionsEdit.setText(", ".join(revisions))

        self.__updateOK()

    @pyqtSlot()
    def __updateOK(self):
        """
        Private slot to updated the enabled state of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.outputPicker.text())
        )

    def getData(self):
        """
        Public method to get the entered fastexport configuration data.

        @return tuple containing the fastexport configuration (output file,
            list of revisions, author map file, import marks file, export marks
            file)
        @rtype tuple of (str, list of str, str, str, str)
        """
        return (
            self.outputPicker.text(),
            [r.strip() for r in self.revisionsEdit.text().split(",") if r.strip()],
            self.authormapPicker.text(),
            self.importMarksPicker.text(),
            self.exportMarksPicker.text(),
        )
