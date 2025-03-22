# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Project Browser configuration page.
"""

import contextlib

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QListWidgetItem

from eric7 import Preferences
from eric7.EricWidgets.EricApplication import ericApp

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_ProjectBrowserPage import Ui_ProjectBrowserPage


class ProjectBrowserPage(ConfigurationPageBase, Ui_ProjectBrowserPage):
    """
    Class implementing the Project Browser configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("ProjectBrowserPage")

        self.__currentProjectTypeIndex = 0

        # populate the project browser type list
        self.__populateProjectBrowserList()

        # set initial values
        self.projectTypeCombo.addItem("", "")
        self.__projectBrowsersLists = {"": []}
        try:
            projectTypes = ericApp().getObject("Project").getProjectTypes()
            for projectType in sorted(projectTypes):
                self.projectTypeCombo.addItem(projectTypes[projectType], projectType)
                self.__projectBrowsersLists[projectType] = (
                    Preferences.getProjectBrowsers(projectType)
                )
        except KeyError:
            self.pbGroup.setEnabled(False)
            self.pbGroup.setVisible(False)

        self.initColour(
            "Highlighted", self.pbHighlightedButton, Preferences.getProjectBrowserColour
        )

        self.followEditorCheckBox.setChecked(Preferences.getProject("FollowEditor"))
        self.followCursorLineCheckBox.setChecked(
            Preferences.getProject("FollowCursorLine")
        )
        self.autoPopulateCheckBox.setChecked(
            Preferences.getProject("AutoPopulateItems")
        )
        self.showHiddenCheckBox.setChecked(
            Preferences.getProject("BrowsersListHiddenFiles")
        )

    def save(self):
        """
        Public slot to save the Project Browser configuration.
        """
        self.saveColours(Preferences.setProjectBrowserColour)

        Preferences.setProject("FollowEditor", self.followEditorCheckBox.isChecked())
        Preferences.setProject(
            "FollowCursorLine", self.followCursorLineCheckBox.isChecked()
        )
        Preferences.setProject(
            "AutoPopulateItems", self.autoPopulateCheckBox.isChecked()
        )
        Preferences.setProject(
            "BrowsersListHiddenFiles", self.showHiddenCheckBox.isChecked()
        )

        if self.pbGroup.isEnabled():
            self.__storeProjectBrowsersList(
                self.projectTypeCombo.itemData(self.__currentProjectTypeIndex)
            )
            for projectType, browsersList in self.__projectBrowsersLists.items():
                if bool(projectType):
                    Preferences.setProjectBrowsers(projectType, browsersList)

    def __populateProjectBrowserList(self):
        """
        Private method to populate the project browsers list.
        """
        with contextlib.suppress(KeyError):
            projectBrowser = ericApp().getObject("ProjectBrowser")
            for (
                browserType,
                userString,
            ) in projectBrowser.getProjectBrowserUserStrings().items():
                itm = QListWidgetItem(userString, self.projectBrowserListWidget)
                itm.setData(Qt.ItemDataRole.UserRole, browserType)
                itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                itm.setCheckState(Qt.CheckState.Unchecked)

    def __storeProjectBrowsersList(self, projectType):
        """
        Private method to store the list of enabled browsers for the selected project
        type.

        @param projectType type of the selected project
        @type str
        """
        browsersList = []
        for row in range(self.projectBrowserListWidget.count()):
            itm = self.projectBrowserListWidget.item(row)
            if itm.checkState() == Qt.CheckState.Checked:
                browsersList.append(itm.data(Qt.ItemDataRole.UserRole))
        self.__projectBrowsersLists[projectType] = browsersList

    def __setProjectBrowsersList(self, projectType):
        """
        Private method to check the project browser entries according to the selected
        project type.

        @param projectType selected project type
        @type str
        """
        browsersList = self.__projectBrowsersLists[projectType]
        for row in range(self.projectBrowserListWidget.count()):
            itm = self.projectBrowserListWidget.item(row)
            if (
                projectType in ("PyQt6", "PyQt6C", "E7Plugin")
                and itm.data(Qt.ItemDataRole.UserRole) == "resources"
            ):
                itm.setFlags(itm.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            else:
                itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsEnabled)
            itm.setCheckState(
                Qt.CheckState.Checked
                if itm.data(Qt.ItemDataRole.UserRole) in browsersList
                else Qt.CheckState.Unchecked
            )

    @pyqtSlot(int)
    def on_projectTypeCombo_activated(self, index):
        """
        Private slot to set the browser checkboxes according to the selected
        project type.

        @param index index of the selected project type
        @type int
        """
        if self.__currentProjectTypeIndex == index:
            return

        self.__storeProjectBrowsersList(
            self.projectTypeCombo.itemData(self.__currentProjectTypeIndex)
        )
        self.__setProjectBrowsersList(self.projectTypeCombo.itemData(index))
        self.__currentProjectTypeIndex = index

    @pyqtSlot(bool)
    def on_followEditorCheckBox_toggled(self, checked):
        """
        Private slot to handle the change of the 'Follow Editor' checkbox.

        @param checked flag indicating the state of the checkbox
        @type bool
        """
        if not checked:
            self.followCursorLineCheckBox.setChecked(False)

    @pyqtSlot(bool)
    def on_followCursorLineCheckBox_toggled(self, checked):
        """
        Private slot to handle the change of the 'Follow Cursor Line' checkbox.

        @param checked flag indicating the state of the checkbox
        @type bool
        """
        if checked:
            self.followEditorCheckBox.setChecked(True)


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = ProjectBrowserPage()
    return page
