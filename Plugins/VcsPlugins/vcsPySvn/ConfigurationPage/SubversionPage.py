# -*- coding: utf-8 -*-

# Copyright (c) 2007 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Subversion configuration page.
"""

from PyQt6.QtCore import pyqtSlot

from eric7.Preferences.ConfigurationPages.ConfigurationPageBase import (
    ConfigurationPageBase,
)

from .Ui_SubversionPage import Ui_SubversionPage


class SubversionPage(ConfigurationPageBase, Ui_SubversionPage):
    """
    Class implementing the Subversion configuration page.
    """

    def __init__(self, plugin):
        """
        Constructor

        @param plugin reference to the plugin object
        @type VcsPySvnPlugin
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("SubversionPage")

        self.__plugin = plugin

        # set initial values
        self.logSpinBox.setValue(self.__plugin.getPreferences("LogLimit"))

    def save(self):
        """
        Public slot to save the Subversion configuration.
        """
        self.__plugin.setPreferences("LogLimit", self.logSpinBox.value())

    @pyqtSlot()
    def on_configButton_clicked(self):
        """
        Private slot to edit the Subversion config file.
        """
        from eric7.QScintilla.MiniEditor import MiniEditor

        cfgFile = self.__plugin.getConfigPath()
        editor = MiniEditor(cfgFile, "Properties", self)
        editor.show()

    @pyqtSlot()
    def on_serversButton_clicked(self):
        """
        Private slot to edit the Subversion servers file.
        """
        from eric7.QScintilla.MiniEditor import MiniEditor

        serversFile = self.__plugin.getServersPath()
        editor = MiniEditor(serversFile, "Properties", self)
        editor.show()
