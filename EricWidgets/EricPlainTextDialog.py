# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show some plain text.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_EricPlainTextDialog import Ui_EricPlainTextDialog


class EricPlainTextDialog(QDialog, Ui_EricPlainTextDialog):
    """
    Class implementing a dialog to show some plain text.
    """

    def __init__(self, title="", text="", readOnly=True, parent=None):
        """
        Constructor

        @param title title of the dialog (defaults to "")
        @type str (optional)
        @param text text to be shown (defaults to "")
        @type str (optional)
        @param readOnly flag indicating a read-only dialog (defaults to True)
        @type bool (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.copyButton = self.buttonBox.addButton(
            self.tr("Copy to Clipboard"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.copyButton.clicked.connect(self.on_copyButton_clicked)

        self.setWindowTitle(title)
        self.textEdit.setPlainText(text)
        self.textEdit.setReadOnly(readOnly)

    @pyqtSlot()
    def on_copyButton_clicked(self):
        """
        Private slot to copy the text to the clipboard.
        """
        txt = self.textEdit.toPlainText()
        cb = QGuiApplication.clipboard()
        cb.setText(txt)

    def toPlainText(self):
        """
        Public method to get the plain text.

        @return contents of the plain text edit
        @rtype str
        """
        return self.textEdit.toPlainText()
