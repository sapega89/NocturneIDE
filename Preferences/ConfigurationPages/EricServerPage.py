# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the eric-ide server related settings.
"""

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EricServerPage import Ui_EricServerPage


class EricServerPage(ConfigurationPageBase, Ui_EricServerPage):
    """
    Class implementing the eric-ide server related settings.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EricServerPage")

        # set initial values
        self.timeoutSpinBox.setValue(Preferences.getEricServer("ConnectionTimeout"))
        self.startShellCheckBox.setChecked(Preferences.getEricServer("AutostartShell"))

    def save(self):
        """
        Public slot to save the Cooperation configuration.
        """
        Preferences.setEricServer("ConnectionTimeout", self.timeoutSpinBox.value())
        Preferences.setEricServer("AutostartShell", self.startShellCheckBox.isChecked())


def create(dlg):  # noqa: U100
    """
    Module function to create the configuration page.

    @param dlg reference to the configuration dialog
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EricServerPage()
    return page
