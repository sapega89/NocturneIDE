# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Jedi Mouse Click Handler configuration page.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog

from eric7 import Preferences
from eric7.Preferences.ConfigurationPages.ConfigurationPageBase import (
    ConfigurationPageBase,
)
from eric7.Preferences.MouseClickDialog import MouseClickDialog
from eric7.Utilities import MouseUtilities

from .Ui_EditorMouseClickHandlerJediPage import Ui_EditorMouseClickHandlerJediPage


class EditorMouseClickHandlerJediPage(
    ConfigurationPageBase, Ui_EditorMouseClickHandlerJediPage
):
    """
    Class implementing the Jedi Mouse Click Handler configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("MouseClickHandlerJediPage")

        # set initial values
        self.__modifiers = {
            "goto": (
                Preferences.getJedi("MouseClickGotoModifiers"),
                Preferences.getJedi("MouseClickGotoButton"),
            )
        }

        self.jediClickHandlerCheckBox.setChecked(
            Preferences.getJedi("MouseClickEnabled")
        )
        self.gotoClickEdit.setText(
            MouseUtilities.MouseButtonModifier2String(*self.__modifiers["goto"])
        )

    def save(self):
        """
        Public slot to save the Jedi Mouse Click Handler configuration.
        """
        Preferences.setJedi(
            "MouseClickEnabled", self.jediClickHandlerCheckBox.isChecked()
        )
        Preferences.setJedi("MouseClickGotoModifiers", self.__modifiers["goto"][0])
        Preferences.setJedi("MouseClickGotoButton", self.__modifiers["goto"][1])

    @pyqtSlot()
    def on_changeGotoButton_clicked(self):
        """
        Private slot to change the 'goto' mouse click sequence.
        """
        dlg = MouseClickDialog(*self.__modifiers["goto"], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.__modifiers["goto"] = dlg.getClick()
            self.gotoClickEdit.setText(
                MouseUtilities.MouseButtonModifier2String(*self.__modifiers["goto"])
            )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorMouseClickHandlerJediPage()
    return page
