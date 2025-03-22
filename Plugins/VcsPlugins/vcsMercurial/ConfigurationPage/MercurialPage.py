# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Mercurial configuration page.
"""

import os

from PyQt6.QtCore import pyqtSlot

from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.Preferences.ConfigurationPages.ConfigurationPageBase import (
    ConfigurationPageBase,
)
from eric7.SystemUtilities import OSUtilities, PythonUtilities
from eric7.Utilities import supportedCodecs

from .. import HgUtilities
from .Ui_MercurialPage import Ui_MercurialPage


class MercurialPage(ConfigurationPageBase, Ui_MercurialPage):
    """
    Class implementing the Mercurial configuration page.
    """

    def __init__(self, plugin):
        """
        Constructor

        @param plugin reference to the plugin object
        @type Hg
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("MercurialPage")

        self.__plugin = plugin

        self.hgPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        if OSUtilities.isWindowsPlatform():
            self.hgPicker.setFilters(self.tr("Executable Files (*.exe);;All Files (*)"))
        else:
            self.hgPicker.setFilters(self.tr("All Files (*)"))

        self.encodingComboBox.addItems(sorted(supportedCodecs))
        self.encodingModeComboBox.addItems(["strict", "ignore", "replace"])

        self.installButton.setEnabled(not self.__mercurialInstalled())

        # set initial values
        # executable override
        self.hgPicker.setText(self.__plugin.getPreferences("MercurialExecutablePath"))

        # global options
        index = self.encodingComboBox.findText(self.__plugin.getPreferences("Encoding"))
        self.encodingComboBox.setCurrentIndex(index)
        index = self.encodingModeComboBox.findText(
            self.__plugin.getPreferences("EncodingMode")
        )
        self.encodingModeComboBox.setCurrentIndex(index)
        self.hiddenChangesetsCheckBox.setChecked(
            self.__plugin.getPreferences("ConsiderHidden")
        )
        # log
        self.logSpinBox.setValue(self.__plugin.getPreferences("LogLimit"))
        self.logWidthSpinBox.setValue(
            self.__plugin.getPreferences("LogMessageColumnWidth")
        )
        self.startFullLogCheckBox.setChecked(
            self.__plugin.getPreferences("LogBrowserShowFullLog")
        )
        # commit
        self.commitAuthorsSpinBox.setValue(
            self.__plugin.getPreferences("CommitAuthorsLimit")
        )
        # pull
        self.pullUpdateCheckBox.setChecked(self.__plugin.getPreferences("PullUpdate"))
        self.preferUnbundleCheckBox.setChecked(
            self.__plugin.getPreferences("PreferUnbundle")
        )
        # cleanup
        self.cleanupPatternEdit.setText(self.__plugin.getPreferences("CleanupPatterns"))
        # revert
        self.backupCheckBox.setChecked(self.__plugin.getPreferences("CreateBackup"))
        # merge
        self.internalMergeCheckBox.setChecked(
            self.__plugin.getPreferences("InternalMerge")
        )

    def save(self):
        """
        Public slot to save the Mercurial configuration.
        """
        # executable override
        self.__plugin.setPreferences("MercurialExecutablePath", self.hgPicker.text())
        # global options
        self.__plugin.setPreferences("Encoding", self.encodingComboBox.currentText())
        self.__plugin.setPreferences(
            "EncodingMode", self.encodingModeComboBox.currentText()
        )
        self.__plugin.setPreferences(
            "ConsiderHidden", self.hiddenChangesetsCheckBox.isChecked()
        )
        # log
        self.__plugin.setPreferences("LogLimit", self.logSpinBox.value())
        self.__plugin.setPreferences(
            "LogMessageColumnWidth", self.logWidthSpinBox.value()
        )
        self.__plugin.setPreferences(
            "LogBrowserShowFullLog", self.startFullLogCheckBox.isChecked()
        )
        # commit
        self.__plugin.setPreferences(
            "CommitAuthorsLimit", self.commitAuthorsSpinBox.value()
        )
        # pull
        self.__plugin.setPreferences("PullUpdate", self.pullUpdateCheckBox.isChecked())
        self.__plugin.setPreferences(
            "PreferUnbundle", self.preferUnbundleCheckBox.isChecked()
        )
        # cleanup
        self.__plugin.setPreferences("CleanupPatterns", self.cleanupPatternEdit.text())
        # revert
        self.__plugin.setPreferences("CreateBackup", self.backupCheckBox.isChecked())
        # merge
        self.__plugin.setPreferences(
            "InternalMerge", self.internalMergeCheckBox.isChecked()
        )

    @pyqtSlot()
    def on_configButton_clicked(self):
        """
        Private slot to edit the (per user) Mercurial configuration file.
        """
        from ..HgUserConfigDialog import HgUserConfigDialog
        from ..HgUtilities import hgVersion

        dlg = HgUserConfigDialog(version=hgVersion(self.__plugin)[1], parent=self)
        dlg.exec()

    @pyqtSlot()
    def on_installButton_clicked(self):
        """
        Private slot to install Mercurial alongside eric7.
        """
        pip = ericApp().getObject("Pip")
        pip.installPackages(
            ["mercurial"], interpreter=PythonUtilities.getPythonExecutable()
        )
        self.installButton.setEnabled(not self.__mercurialInstalled())

    def __mercurialInstalled(self):
        """
        Private method to check, if Mercurial is installed alongside eric7.

        @return flag indicating an installed Mercurial executable
        @rtype bool
        """
        hg = HgUtilities.getHgExecutable()
        # assume local installation, if the path is absolute
        return os.path.isabs(hg)
