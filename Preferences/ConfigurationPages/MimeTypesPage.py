# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Text Mime Types configuration page.
"""

from PyQt6.QtCore import pyqtSlot

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_MimeTypesPage import Ui_MimeTypesPage


class MimeTypesPage(ConfigurationPageBase, Ui_MimeTypesPage):
    """
    Class implementing the Text Mime Types configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("MimeTypesPage")

        self.textMimeTypesList.setResetVisible(True)
        self.textMimeTypesList.setDefaultVisible(True)
        self.textMimeTypesList.setToDefault.connect(self.__setMimeTypesToDefault)

        self.textFilePatternsList.setResetVisible(True)
        self.textFilePatternsList.setDefaultVisible(True)
        self.textFilePatternsList.setToDefault.connect(self.__setFilePatternsToDefault)

        # set initial values
        self.textMimeTypesList.setList(Preferences.getUI("TextMimeTypes"))
        self.textFilePatternsList.setList(Preferences.getUI("TextFilePatterns"))
        self.loadUnknownCheckBox.setChecked(
            Preferences.getUI("LoadUnknownMimeTypeFiles")
        )
        self.askUserCheckBox.setChecked(Preferences.getUI("TextMimeTypesAskUser"))

    def save(self):
        """
        Public slot to save the Interface configuration.
        """
        Preferences.setUI("TextMimeTypes", self.textMimeTypesList.getList())
        Preferences.setUI("TextFilePatterns", self.textFilePatternsList.getList())
        Preferences.setUI(
            "LoadUnknownMimeTypeFiles",
            self.loadUnknownCheckBox.isChecked(),
        )
        Preferences.setUI("TextMimeTypesAskUser", self.askUserCheckBox.isChecked())

    @pyqtSlot()
    def __setMimeTypesToDefault(self):
        """
        Private slot to set the mimetypes list to the default values.
        """
        ok = (
            True
            if self.textMimeTypesList.isListEmpty()
            else EricMessageBox.yesNo(
                self,
                self.tr("Set Mime Types To Default"),
                self.tr(
                    """Do you really want to set the configured list of"""
                    """ mime types to the default value?"""
                ),
            )
        )

        if ok:
            self.textMimeTypesList.setList(
                Preferences.Prefs.uiDefaults["TextMimeTypes"]
            )

    @pyqtSlot()
    def __setFilePatternsToDefault(self):
        """
        Private slot to set the file patterns list to the default values.
        """
        ok = (
            True
            if self.textFilePatternsList.isListEmpty()
            else EricMessageBox.yesNo(
                self,
                self.tr("Set File Patterns To Default"),
                self.tr(
                    """Do you really want to set the configured list of"""
                    """ text file patterns to the default value?"""
                ),
            )
        )

        if ok:
            self.textFilePatternsList.setList(
                Preferences.Prefs.uiDefaults["TextFilePatterns"]
            )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = MimeTypesPage()
    return page
