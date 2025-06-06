# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Plugin Details Dialog.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog

from .Ui_PluginDetailsDialog import Ui_PluginDetailsDialog


class PluginDetailsDialog(QDialog, Ui_PluginDetailsDialog):
    """
    Class implementing the Plugin Details Dialog.
    """

    def __init__(self, details, parent=None):
        """
        Constructor

        @param details dictionary containing the info to be displayed
        @type dict
        @param parent parent of this dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.__autoactivate = details["autoactivate"]
        self.__active = details["active"]

        self.moduleNameEdit.setText(details["moduleName"])
        self.moduleFileNameEdit.setText(details["moduleFileName"])
        self.pluginNameEdit.setText(details["pluginName"])
        self.versionEdit.setText(details["version"])
        self.authorEdit.setText(details["author"])
        self.descriptionEdit.setText(details["description"])
        self.errorEdit.setText(details["error"])
        self.autoactivateCheckBox.setChecked(details["autoactivate"])
        self.activeCheckBox.setChecked(details["active"])

    @pyqtSlot()
    def on_activeCheckBox_clicked(self):
        """
        Private slot called, when the activeCheckBox was clicked.
        """
        self.activeCheckBox.setChecked(self.__active)

    @pyqtSlot()
    def on_autoactivateCheckBox_clicked(self):
        """
        Private slot called, when the autoactivateCheckBox was clicked.
        """
        self.autoactivateCheckBox.setChecked(self.__autoactivate)
