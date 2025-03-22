# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to manage the QtHelp documentation database.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QAbstractButton, QDialog, QDialogButtonBox

from .QtHelpDocumentationSettings import QtHelpDocumentationSettings
from .Ui_QtHelpDocumentationConfigurationDialog import (
    Ui_QtHelpDocumentationConfigurationDialog,
)


class QtHelpDocumentationConfigurationDialog(
    QDialog, Ui_QtHelpDocumentationConfigurationDialog
):
    """
    Class implementing a dialog to manage the QtHelp documentation database.
    """

    def __init__(self, engine, parent=None):
        """
        Constructor

        @param engine reference to the Qt help engine
        @type QHelpEngineCore
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__engine = engine

        self.__settings = QtHelpDocumentationSettings.readSettings(self.__engine)

        self.documentationSettingsWidget.documentationSettingsChanged.connect(
            self.__documentationSettingsChanged
        )
        self.documentationSettingsWidget.setDocumentationSettings(self.__settings)

        self.filterSettingsWidget.setAvailableComponents(self.__settings.components())
        self.filterSettingsWidget.setAvailableVersions(self.__settings.versions())
        self.filterSettingsWidget.readSettings(self.__engine.filterEngine())

    @pyqtSlot(QtHelpDocumentationSettings)
    def __documentationSettingsChanged(self, settings):
        """
        Private slot to handle a change of the QtHelp documentation
        configuration.

        @param settings reference to the documentation settings object
        @type QtHelpDocumentationSettings
        """
        self.__settings = settings

        self.filterSettingsWidget.setAvailableComponents(self.__settings.components())
        self.filterSettingsWidget.setAvailableVersions(self.__settings.versions())

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.buttonBox.button(QDialogButtonBox.StandardButton.Apply):
            self.__applyConfiguration()

            self.__settings = QtHelpDocumentationSettings.readSettings(self.__engine)

            self.filterSettingsWidget.setAvailableComponents(
                self.__settings.components()
            )
            self.filterSettingsWidget.setAvailableVersions(self.__settings.versions())
            self.filterSettingsWidget.readSettings(self.__engine.filterEngine())
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Ok):
            self.__applyConfiguration()
            self.accept()

    def __applyConfiguration(self):
        """
        Private method to apply the current QtHelp documentation configuration.
        """
        changed = QtHelpDocumentationSettings.applySettings(
            self.__engine, self.__settings
        )
        changed |= self.filterSettingsWidget.applySettings(self.__engine.filterEngine())

        if changed:
            # In order to update the filter combobox and index widget according
            # to the new filter configuration.
            self.__engine.setupData()
