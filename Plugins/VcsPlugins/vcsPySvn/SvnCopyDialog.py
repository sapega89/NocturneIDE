# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a copy operation.
"""

import os.path

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_SvnCopyDialog import Ui_SvnCopyDialog


class SvnCopyDialog(QDialog, Ui_SvnCopyDialog):
    """
    Class implementing a dialog to enter the data for a copy or rename
    operation.
    """

    def __init__(self, source, parent=None, move=False, force=False):
        """
        Constructor

        @param source name of the source file/directory
        @type str
        @param parent parent widget
        @type QWidget
        @param move flag indicating a move operation
        @type bool
        @param force flag indicating a forced operation
        @type bool
        """
        super().__init__(parent)
        self.setupUi(self)

        self.source = source
        if os.path.isdir(self.source):
            self.targetPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        else:
            self.targetPicker.setMode(EricPathPickerModes.SAVE_FILE_MODE)

        if move:
            self.setWindowTitle(self.tr("Subversion Move"))
        else:
            self.forceCheckBox.setEnabled(False)
        self.forceCheckBox.setChecked(force)

        self.sourceEdit.setText(source)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getData(self):
        """
        Public method to retrieve the copy data.

        @return the target name and a flag indicating the operation should be enforced
        @rtype tuple of (str, bool)
        """
        target = self.targetPicker.text()
        if not os.path.isabs(target):
            sourceDir = os.path.dirname(self.sourceEdit.text())
            target = os.path.join(sourceDir, target)
        return (target, self.forceCheckBox.isChecked())

    @pyqtSlot(str)
    def on_targetPicker_textChanged(self, txt):
        """
        Private slot to handle changes of the target.

        @param txt contents of the target edit
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            os.path.isabs(txt) or os.path.dirname(txt) == ""
        )
