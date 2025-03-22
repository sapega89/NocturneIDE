# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the VCS configuration page.
"""

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_VcsPage import Ui_VcsPage


class VcsPage(ConfigurationPageBase, Ui_VcsPage):
    """
    Class implementing the VCS configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("VcsPage")

        # set initial values
        self.vcsAutoCloseCheckBox.setChecked(Preferences.getVCS("AutoClose"))
        self.vcsAutoSaveCheckBox.setChecked(Preferences.getVCS("AutoSaveFiles"))
        self.vcsAutoSaveProjectCheckBox.setChecked(
            Preferences.getVCS("AutoSaveProject")
        )
        self.commitSpinBox.setValue(Preferences.getVCS("CommitMessages"))
        self.perProjectCommitHistoryCheckBox.setChecked(
            Preferences.getVCS("PerProjectCommitHistory")
        )
        self.vcsStatusMonitorIntervalSpinBox.setValue(
            Preferences.getVCS("StatusMonitorInterval")
        )
        self.vcsMonitorLocalStatusCheckBox.setChecked(
            Preferences.getVCS("MonitorLocalStatus")
        )
        self.autoUpdateCheckBox.setChecked(Preferences.getVCS("AutoUpdate"))
        self.vcsToolbarCheckBox.setChecked(Preferences.getVCS("ShowVcsToolbar"))

        self.initColour(
            "VcsAdded", self.pbVcsAddedButton, Preferences.getProjectBrowserColour
        )
        self.initColour(
            "VcsConflict", self.pbVcsConflictButton, Preferences.getProjectBrowserColour
        )
        self.initColour(
            "VcsModified", self.pbVcsModifiedButton, Preferences.getProjectBrowserColour
        )
        self.initColour(
            "VcsReplaced", self.pbVcsReplacedButton, Preferences.getProjectBrowserColour
        )
        self.initColour(
            "VcsUpdate", self.pbVcsUpdateButton, Preferences.getProjectBrowserColour
        )
        self.initColour(
            "VcsRemoved", self.pbVcsRemovedButton, Preferences.getProjectBrowserColour
        )

    def save(self):
        """
        Public slot to save the VCS configuration.
        """
        Preferences.setVCS("AutoClose", self.vcsAutoCloseCheckBox.isChecked())
        Preferences.setVCS("AutoSaveFiles", self.vcsAutoSaveCheckBox.isChecked())
        Preferences.setVCS(
            "AutoSaveProject", self.vcsAutoSaveProjectCheckBox.isChecked()
        )
        Preferences.setVCS("CommitMessages", self.commitSpinBox.value())
        Preferences.setVCS(
            "PerProjectCommitHistory", self.perProjectCommitHistoryCheckBox.isChecked()
        )
        Preferences.setVCS(
            "StatusMonitorInterval", self.vcsStatusMonitorIntervalSpinBox.value()
        )
        Preferences.setVCS(
            "MonitorLocalStatus", self.vcsMonitorLocalStatusCheckBox.isChecked()
        )
        Preferences.setVCS("AutoUpdate", self.autoUpdateCheckBox.isChecked())
        Preferences.setVCS("ShowVcsToolbar", self.vcsToolbarCheckBox.isChecked())

        self.saveColours(Preferences.setProjectBrowserColour)


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = VcsPage()
    return page
