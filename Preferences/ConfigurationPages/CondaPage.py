# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the conda configuration page.
"""

from eric7 import CondaInterface, Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_CondaPage import Ui_CondaPage


class CondaPage(ConfigurationPageBase, Ui_CondaPage):
    """
    Class implementing the conda configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("CondaPage")

        self.condaExePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.condaExePicker.setToolTip(
            self.tr("Press to select the conda executable via a file selection dialog.")
        )

        # set initial values
        self.__condaExecutable = Preferences.getConda("CondaExecutable")
        self.condaExePicker.setText(self.__condaExecutable)

    def save(self):
        """
        Public slot to save the conda configuration.
        """
        condaExecutable = self.condaExePicker.text()
        if condaExecutable != self.__condaExecutable:
            Preferences.setConda("CondaExecutable", condaExecutable)

            CondaInterface.resetInterface()


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = CondaPage()
    return page
