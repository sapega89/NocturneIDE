# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Viewmanager configuration page.
"""

from PyQt6.QtCore import pyqtSlot

from eric7 import Preferences
from eric7.EricWidgets.EricApplication import ericApp

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_ViewmanagerPage import Ui_ViewmanagerPage


class ViewmanagerPage(ConfigurationPageBase, Ui_ViewmanagerPage):
    """
    Class implementing the Viewmanager configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("ViewmanagerPage")

        # set initial values
        self.pluginManager = ericApp().getObject("PluginManager")
        self.viewmanagers = self.pluginManager.getPluginDisplayStrings("viewmanager")
        self.windowComboBox.clear()
        currentVm = Preferences.getViewManager()

        for key in sorted(self.viewmanagers):
            self.windowComboBox.addItem(self.tr(self.viewmanagers[key]), key)
        currentIndex = self.windowComboBox.findText(
            self.tr(self.viewmanagers[currentVm])
        )
        self.windowComboBox.setCurrentIndex(currentIndex)
        self.on_windowComboBox_activated(currentIndex)

        self.tabViewGroupBox.setTitle(self.tr(self.viewmanagers["tabview"]))

        self.filenameLengthSpinBox.setValue(
            Preferences.getUI("TabViewManagerFilenameLength")
        )
        self.filenameOnlyCheckBox.setChecked(
            Preferences.getUI("TabViewManagerFilenameOnly")
        )
        self.recentFilesSpinBox.setValue(Preferences.getUI("RecentNumber"))

    def save(self):
        """
        Public slot to save the Viewmanager configuration.
        """
        vm = self.windowComboBox.itemData(self.windowComboBox.currentIndex())
        Preferences.setViewManager(vm)
        Preferences.setUI(
            "TabViewManagerFilenameLength", self.filenameLengthSpinBox.value()
        )
        Preferences.setUI(
            "TabViewManagerFilenameOnly", self.filenameOnlyCheckBox.isChecked()
        )
        Preferences.setUI("RecentNumber", self.recentFilesSpinBox.value())

    @pyqtSlot(int)
    def on_windowComboBox_activated(self, _index):
        """
        Private slot to show a preview of the selected workspace view type.

        @param _index index of selected workspace view type (unused)
        @type int
        """
        workspace = self.windowComboBox.itemData(self.windowComboBox.currentIndex())
        pixmap = self.pluginManager.getPluginPreviewPixmap("viewmanager", workspace)

        self.previewPixmap.setPixmap(pixmap)
        self.tabViewGroupBox.setEnabled(workspace == "tabview")


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = ViewmanagerPage()
    return page
