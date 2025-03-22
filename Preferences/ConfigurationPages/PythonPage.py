# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Python configuration page.
"""

from PyQt6.QtCore import pyqtSlot

from eric7 import Preferences
from eric7.Utilities import supportedCodecs

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_PythonPage import Ui_PythonPage


class PythonPage(ConfigurationPageBase, Ui_PythonPage):
    """
    Class implementing the Python configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("PythonPage")

        self.stringEncodingComboBox.addItems(sorted(supportedCodecs))
        self.ioEncodingComboBox.addItems(sorted(supportedCodecs))

        # set initial values
        index = self.stringEncodingComboBox.findText(
            Preferences.getSystem("StringEncoding")
        )
        self.stringEncodingComboBox.setCurrentIndex(index)
        index = self.ioEncodingComboBox.findText(Preferences.getSystem("IOEncoding"))
        self.ioEncodingComboBox.setCurrentIndex(index)

        self.showCodeInfoDetailsCeckBox.setChecked(
            Preferences.getPython("DisViewerExpandCodeInfoDetails")
        )

        # these are the same as in the debugger pages
        self.py3ExtensionsEdit.setText(Preferences.getDebugger("Python3Extensions"))

        self.py3EnvironmentEdit.setText(Preferences.getDebugger("Python3VirtualEnv"))

        # colours
        self.initColour(
            "ASTViewerErrorColor", self.astErrorItemButton, Preferences.getPython
        )
        self.initColour(
            "DisViewerErrorColor", self.disErrorItemButton, Preferences.getPython
        )
        self.initColour(
            "DisViewerCurrentColor",
            self.disCurrentInstructionButton,
            Preferences.getPython,
        )
        self.initColour(
            "DisViewerLabeledColor",
            self.disLabeledInstructionButton,
            Preferences.getPython,
        )

    def save(self):
        """
        Public slot to save the Python configuration.
        """
        enc = self.stringEncodingComboBox.currentText()
        if not enc:
            enc = "utf-8"
        Preferences.setSystem("StringEncoding", enc)

        enc = self.ioEncodingComboBox.currentText()
        if not enc:
            enc = "utf-8"
        Preferences.setSystem("IOEncoding", enc)

        Preferences.setDebugger("Python3Extensions", self.py3ExtensionsEdit.text())

        Preferences.setPython(
            "DisViewerExpandCodeInfoDetails",
            self.showCodeInfoDetailsCeckBox.isChecked(),
        )

        # colours
        self.saveColours(Preferences.setPython)

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot handling a click of the refresh button.
        """
        self.py3EnvironmentEdit.setText(Preferences.getDebugger("Python3VirtualEnv"))


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = PythonPage()
    return page
