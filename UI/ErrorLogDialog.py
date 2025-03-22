# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to display an error log.
"""

import contextlib
import os

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QStyle

from .Ui_ErrorLogDialog import Ui_ErrorLogDialog


class ErrorLogDialog(QDialog, Ui_ErrorLogDialog):
    """
    Class implementing a dialog to display an error log.
    """

    def __init__(self, logFile, showMode, parent=None):
        """
        Constructor

        @param logFile name of the log file containing the error info
        @type str
        @param showMode flag indicating to just show the error log message
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        pixmap = (
            self.style()
            .standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)
            .pixmap(32, 32)
        )
        self.icon.setPixmap(pixmap)

        if showMode:
            self.icon.hide()
            self.label.hide()
            self.deleteButton.setText(self.tr("Delete"))
            self.keepButton.setText(self.tr("Close"))
            self.setWindowTitle(self.tr("Error Log"))

        self.__ui = parent
        self.__logFile = logFile

        with contextlib.suppress(OSError):
            with open(logFile, "r", encoding="utf-8") as f:
                txt = f.read()
            self.logEdit.setPlainText(txt)

    @pyqtSlot()
    def on_emailButton_clicked(self):
        """
        Private slot to send an email.
        """
        self.accept()
        self.__ui.showEmailDialog(
            "bug", attachFile=self.__logFile, deleteAttachFile=True
        )

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to delete the log file.
        """
        if os.path.exists(self.__logFile):
            os.remove(self.__logFile)
        self.accept()

    @pyqtSlot()
    def on_keepButton_clicked(self):
        """
        Private slot to just do nothing.
        """
        self.accept()
