# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Debugger Python3 configuration page.
"""

from PyQt6.QtCore import pyqtSlot

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_DebuggerPython3Page import Ui_DebuggerPython3Page


class DebuggerPython3Page(ConfigurationPageBase, Ui_DebuggerPython3Page):
    """
    Class implementing the Debugger Python3 configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("DebuggerPython3Page")

        try:
            self.__virtualenvManager = ericApp().getObject("VirtualEnvManager")
            self.__standalone = False
        except KeyError:
            from eric7.VirtualEnv.VirtualenvManager import (  # __IGNORE_WARNING_I101__
                VirtualenvManager,
            )

            self.__virtualenvManager = VirtualenvManager()
            self.__standalone = True

        self.venvDlgButton.setVisible(self.__standalone)
        self.venvDlgButton.setIcon(EricPixmapCache.getIcon("virtualenv"))

        self.venvRefreshButton.setVisible(not self.__standalone)
        self.venvRefreshButton.setIcon(EricPixmapCache.getIcon("reload"))

        self.debugClientPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.debugClientPicker.setToolTip(
            self.tr("Press to select the Debug Client via a file selection dialog")
        )
        self.debugClientPicker.setFilters(self.tr("Python Files (*.py *.py3)"))

        self.__populateAndSetVenvComboBox()

        # set initial values
        dct = Preferences.getDebugger("DebugClientType3")
        if dct == "standard":
            self.standardButton.setChecked(True)
        else:
            self.customButton.setChecked(True)
        self.debugClientPicker.setText(
            Preferences.getDebugger("DebugClient3"), toNative=False
        )
        self.pyRedirectCheckBox.setChecked(Preferences.getDebugger("Python3Redirect"))
        self.pyNoEncodingCheckBox.setChecked(
            Preferences.getDebugger("Python3NoEncoding")
        )
        self.sourceExtensionsEdit.setText(Preferences.getDebugger("Python3Extensions"))
        self.callTraceCheckBox.setChecked(
            Preferences.getDebugger("PythonCallTraceOptimization")
        )

    def save(self):
        """
        Public slot to save the Debugger Python configuration.
        """
        Preferences.setDebugger("Python3VirtualEnv", self.venvComboBox.currentText())
        dct = "standard" if self.standardButton.isChecked() else "custom"
        Preferences.setDebugger("DebugClientType3", dct)
        Preferences.setDebugger(
            "DebugClient3", self.debugClientPicker.text(toNative=False)
        )
        Preferences.setDebugger("Python3Redirect", self.pyRedirectCheckBox.isChecked())
        Preferences.setDebugger(
            "Python3NoEncoding", self.pyNoEncodingCheckBox.isChecked()
        )
        Preferences.setDebugger(
            "PythonCallTraceOptimization", self.callTraceCheckBox.isChecked()
        )

    def __populateAndSetVenvComboBox(self):
        """
        Private method to populate and set the virtual environment combo box.
        """
        self.venvComboBox.clear()
        self.venvComboBox.addItems(
            [""] + sorted(self.__virtualenvManager.getVirtualenvNames(noServer=True))
        )

        # set initial value
        venvName = Preferences.getDebugger("Python3VirtualEnv")
        if venvName:
            index = self.venvComboBox.findText(venvName)
            if index < 0:
                index = 0
            self.venvComboBox.setCurrentIndex(index)

    @pyqtSlot()
    def on_refreshButton_clicked(self):
        """
        Private slot handling a click of the refresh button.
        """
        self.sourceExtensionsEdit.setText(Preferences.getDebugger("Python3Extensions"))

    @pyqtSlot()
    def on_venvDlgButton_clicked(self):
        """
        Private slot to show the virtual environment manager dialog.
        """
        if self.__standalone:
            self.__virtualenvManager.showVirtualenvManagerDialog(modal=True)
            self.__populateAndSetVenvComboBox()
            self.activateWindow()
            self.raise_()

    @pyqtSlot()
    def on_venvRefreshButton_clicked(self):
        """
        Private slot to reload the list of virtual environments.
        """
        self.__populateAndSetVenvComboBox()


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = DebuggerPython3Page()
    return page
