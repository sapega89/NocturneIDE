# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Multi Project configuration page.
"""

from eric7 import Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_MultiProjectPage import Ui_MultiProjectPage


class MultiProjectPage(ConfigurationPageBase, Ui_MultiProjectPage):
    """
    Class implementing the Multi Project configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("MultiProjectPage")

        self.workspacePicker.setMode(EricPathPickerModes.DIRECTORY_MODE)

        # set initial values
        self.openMainAutomaticallyCheckBox.setChecked(
            Preferences.getMultiProject("OpenMainAutomatically")
        )
        self.multiProjectTimestampCheckBox.setChecked(
            Preferences.getMultiProject("TimestampFile")
        )
        self.multiProjectRecentSpinBox.setValue(
            Preferences.getMultiProject("RecentNumber")
        )
        self.workspacePicker.setText(
            FileSystemUtilities.toNativeSeparators(
                Preferences.getMultiProject("Workspace") or OSUtilities.getHomeDir()
            )
        )

    def save(self):
        """
        Public slot to save the Project configuration.
        """
        Preferences.setMultiProject(
            "OpenMainAutomatically", self.openMainAutomaticallyCheckBox.isChecked()
        )
        Preferences.setMultiProject(
            "TimestampFile", self.multiProjectTimestampCheckBox.isChecked()
        )
        Preferences.setMultiProject(
            "RecentNumber", self.multiProjectRecentSpinBox.value()
        )
        Preferences.setMultiProject("Workspace", self.workspacePicker.text())


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = MultiProjectPage()
    return page
