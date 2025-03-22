# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Jedi Auto-completion configuration page.
"""

from eric7 import Preferences
from eric7.Preferences.ConfigurationPages.ConfigurationPageBase import (
    ConfigurationPageBase,
)

from .Ui_EditorAutoCompletionJediPage import Ui_EditorAutoCompletionJediPage


class EditorAutoCompletionJediPage(
    ConfigurationPageBase, Ui_EditorAutoCompletionJediPage
):
    """
    Class implementing the Jedi Auto-completion configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorAutoCompletionJediPage")

        # set initial values
        self.jediAutocompletionCheckBox.setChecked(
            Preferences.getJedi("JediCompletionsEnabled")
        )
        self.jediFuzzyAutocompletionCheckBox.setChecked(
            Preferences.getJedi("JediFuzzyCompletionsEnabled")
        )

    def save(self):
        """
        Public slot to save the Jedi Auto-completion configuration.
        """
        Preferences.setJedi(
            "JediCompletionsEnabled", self.jediAutocompletionCheckBox.isChecked()
        )
        Preferences.setJedi(
            "JediFuzzyCompletionsEnabled",
            self.jediFuzzyAutocompletionCheckBox.isChecked(),
        )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorAutoCompletionJediPage()
    return page
