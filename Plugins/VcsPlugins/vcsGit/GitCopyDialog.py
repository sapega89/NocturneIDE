# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a copy or rename operation.
"""

import os.path

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog
from eric7.EricWidgets.EricCompleters import EricDirCompleter, EricFileCompleter
from eric7.SystemUtilities import FileSystemUtilities

from .Ui_GitCopyDialog import Ui_GitCopyDialog


class GitCopyDialog(QDialog, Ui_GitCopyDialog):
    """
    Class implementing a dialog to enter the data for a copy or rename
    operation.
    """

    def __init__(self, source, parent=None, move=False):
        """
        Constructor

        @param source name of the source file/directory
        @type str
        @param parent parent widget
        @type QWidget
        @param move flag indicating a move operation
        @type bool
        """
        super().__init__(parent)
        self.setupUi(self)

        self.dirButton.setIcon(EricPixmapCache.getIcon("open"))

        self.source = source
        if os.path.isdir(self.source):
            self.targetCompleter = EricDirCompleter(self.targetEdit)
        else:
            self.targetCompleter = EricFileCompleter(self.targetEdit)

        if move:
            self.setWindowTitle(self.tr("Git Move"))
        else:
            self.forceCheckBox.setEnabled(False)

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
        target = self.targetEdit.text()
        if not os.path.isabs(target):
            sourceDir = os.path.dirname(self.sourceEdit.text())
            target = os.path.join(sourceDir, target)
        return (
            FileSystemUtilities.toNativeSeparators(target),
            self.forceCheckBox.isChecked(),
        )

    @pyqtSlot()
    def on_dirButton_clicked(self):
        """
        Private slot to handle the button press for selecting the target via a
        selection dialog.
        """
        target = (
            EricFileDialog.getExistingDirectory(
                self,
                self.tr("Select target"),
                self.targetEdit.text(),
                EricFileDialog.ShowDirsOnly,
            )
            if os.path.isdir(self.source)
            else EricFileDialog.getSaveFileName(
                self,
                self.tr("Select target"),
                self.targetEdit.text(),
                "",
                options=EricFileDialog.DontConfirmOverwrite,
            )
        )

        if target:
            self.targetEdit.setText(FileSystemUtilities.toNativeSeparators(target))

    @pyqtSlot(str)
    def on_targetEdit_textChanged(self, txt):
        """
        Private slot to handle changes of the target.

        @param txt contents of the target edit
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            os.path.isabs(txt) or os.path.dirname(txt) == ""
        )
