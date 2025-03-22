# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Jedi Calltips configuration page.
"""

from eric7 import Preferences
from eric7.Preferences.ConfigurationPages.ConfigurationPageBase import (
    ConfigurationPageBase,
)

from .Ui_EditorCallTipsJediPage import Ui_EditorCallTipsJediPage


class EditorCallTipsJediPage(ConfigurationPageBase, Ui_EditorCallTipsJediPage):
    """
    Class implementing the Jedi Calltips configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorCallTipsJediPage")

        # set initial values
        self.jediCalltipsCheckBox.setChecked(Preferences.getJedi("JediCalltipsEnabled"))

    def save(self):
        """
        Public slot to save the Jedi Calltips configuration.
        """
        Preferences.setJedi(
            "JediCalltipsEnabled", self.jediCalltipsCheckBox.isChecked()
        )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorCallTipsJediPage()
    return page
