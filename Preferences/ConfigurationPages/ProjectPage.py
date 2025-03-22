# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Project configuration page.
"""

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_ProjectPage import Ui_ProjectPage


class ProjectPage(ConfigurationPageBase, Ui_ProjectPage):
    """
    Class implementing the Project configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("ProjectPage")

        # set initial values
        self.projectAutoSaveCheckBox.setChecked(
            Preferences.getProject("AutoSaveProject")
        )
        self.projectSearchNewFilesRecursiveCheckBox.setChecked(
            Preferences.getProject("SearchNewFilesRecursively")
        )
        self.projectSearchNewFilesCheckBox.setChecked(
            Preferences.getProject("SearchNewFiles")
        )
        self.projectAutoIncludeNewFilesCheckBox.setChecked(
            Preferences.getProject("AutoIncludeNewFiles")
        )
        self.projectLoadSessionCheckBox.setChecked(
            Preferences.getProject("AutoLoadSession")
        )
        self.projectSaveSessionCheckBox.setChecked(
            Preferences.getProject("AutoSaveSession")
        )
        self.projectSessionAllBpCheckBox.setChecked(
            Preferences.getProject("SessionAllBreakpoints")
        )
        self.projectLoadDebugPropertiesCheckBox.setChecked(
            Preferences.getProject("AutoLoadDbgProperties")
        )
        self.projectSaveDebugPropertiesCheckBox.setChecked(
            Preferences.getProject("AutoSaveDbgProperties")
        )
        self.projectAutoCompileFormsCheckBox.setChecked(
            Preferences.getProject("AutoCompileForms")
        )
        self.projectAutoCompileResourcesCheckBox.setChecked(
            Preferences.getProject("AutoCompileResources")
        )
        self.projectAutoMakeCheckBox.setChecked(
            Preferences.getProject("AutoExecuteMake")
        )
        self.projectTimestampCheckBox.setChecked(
            Preferences.getProject("TimestampFile")
        )
        self.projectRecentSpinBox.setValue(Preferences.getProject("RecentNumber"))
        self.pythonVariantCheckBox.setChecked(
            Preferences.getProject("DeterminePyFromProject")
        )
        self.autosaveTasksCheckBox.setChecked(
            Preferences.getProject("TasksProjectAutoSave")
        )
        self.rescanTasksCheckBox.setChecked(
            Preferences.getProject("TasksProjectRescanOnOpen")
        )
        self.restartShellCheckBox.setChecked(
            Preferences.getProject("RestartShellForProject")
        )

    def save(self):
        """
        Public slot to save the Project configuration.
        """
        Preferences.setProject(
            "AutoSaveProject",
            self.projectAutoSaveCheckBox.isChecked(),
        )
        Preferences.setProject(
            "SearchNewFilesRecursively",
            self.projectSearchNewFilesRecursiveCheckBox.isChecked(),
        )
        Preferences.setProject(
            "SearchNewFiles", self.projectSearchNewFilesCheckBox.isChecked()
        )
        Preferences.setProject(
            "AutoIncludeNewFiles", self.projectAutoIncludeNewFilesCheckBox.isChecked()
        )
        Preferences.setProject(
            "AutoLoadSession", self.projectLoadSessionCheckBox.isChecked()
        )
        Preferences.setProject(
            "AutoSaveSession", self.projectSaveSessionCheckBox.isChecked()
        )
        Preferences.setProject(
            "SessionAllBreakpoints", self.projectSessionAllBpCheckBox.isChecked()
        )
        Preferences.setProject(
            "AutoLoadDbgProperties", self.projectLoadDebugPropertiesCheckBox.isChecked()
        )
        Preferences.setProject(
            "AutoSaveDbgProperties", self.projectSaveDebugPropertiesCheckBox.isChecked()
        )
        Preferences.setProject(
            "AutoCompileForms", self.projectAutoCompileFormsCheckBox.isChecked()
        )
        Preferences.setProject(
            "AutoCompileResources", self.projectAutoCompileResourcesCheckBox.isChecked()
        )
        Preferences.setProject(
            "AutoExecuteMake", self.projectAutoMakeCheckBox.isChecked()
        )
        Preferences.setProject(
            "TimestampFile", self.projectTimestampCheckBox.isChecked()
        )
        Preferences.setProject("RecentNumber", self.projectRecentSpinBox.value())
        Preferences.setProject(
            "DeterminePyFromProject", self.pythonVariantCheckBox.isChecked()
        )
        Preferences.setProject(
            "TasksProjectAutoSave", self.autosaveTasksCheckBox.isChecked()
        )
        Preferences.setProject(
            "TasksProjectRescanOnOpen", self.rescanTasksCheckBox.isChecked()
        )
        Preferences.setProject(
            "RestartShellForProject", self.restartShellCheckBox.isChecked()
        )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = ProjectPage()
    return page
