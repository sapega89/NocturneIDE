# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the JavaScript settings dialog.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7 import Preferences

from .Ui_JavaScriptSettingsDialog import Ui_JavaScriptSettingsDialog


class JavaScriptSettingsDialog(QDialog, Ui_JavaScriptSettingsDialog):
    """
    Class implementing the JavaScript settings dialog.

    Note: it contains the JavaScript part of the web browser configuration
    dialog.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.javaScriptGroup.setChecked(Preferences.getWebBrowser("JavaScriptEnabled"))
        self.jsOpenWindowsCheckBox.setChecked(
            Preferences.getWebBrowser("JavaScriptCanOpenWindows")
        )
        self.jsActivateWindowsCheckBox.setChecked(
            Preferences.getWebBrowser("AllowWindowActivationFromJavaScript")
        )
        self.jsClipboardCheckBox.setChecked(
            Preferences.getWebBrowser("JavaScriptCanAccessClipboard")
        )
        self.jsPasteCheckBox.setChecked(Preferences.getWebBrowser("JavaScriptCanPaste"))

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def accept(self):
        """
        Public slot to accept the dialog.
        """
        Preferences.setWebBrowser("JavaScriptEnabled", self.javaScriptGroup.isChecked())
        Preferences.setWebBrowser(
            "JavaScriptCanOpenWindows", self.jsOpenWindowsCheckBox.isChecked()
        )
        if self.jsActivateWindowsCheckBox.isEnabled():
            Preferences.setWebBrowser(
                "AllowWindowActivationFromJavaScript",
                self.jsActivateWindowsCheckBox.isChecked(),
            )
        Preferences.setWebBrowser(
            "JavaScriptCanAccessClipboard", self.jsClipboardCheckBox.isChecked()
        )
        if self.jsPasteCheckBox.isEnabled():
            Preferences.setWebBrowser(
                "JavaScriptCanPaste", self.jsPasteCheckBox.isChecked()
            )

        Preferences.syncPreferences()

        super().accept()
