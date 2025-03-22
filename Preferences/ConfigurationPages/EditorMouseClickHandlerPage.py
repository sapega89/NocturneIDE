# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor Mouse Click Handlers configuration page.
"""

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorMouseClickHandlerPage import Ui_EditorMouseClickHandlerPage


class EditorMouseClickHandlerPage(
    ConfigurationPageBase, Ui_EditorMouseClickHandlerPage
):
    """
    Class implementing the Editor Mouse Click Handlers configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorMouseClickHandlerPage")

        # set initial values
        self.mcEnabledCheckBox.setChecked(
            Preferences.getEditor("MouseClickHandlersEnabled")
        )

    def save(self):
        """
        Public slot to save the Editor Mouse Click Handlers configuration.
        """
        Preferences.setEditor(
            "MouseClickHandlersEnabled", self.mcEnabledCheckBox.isChecked()
        )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorMouseClickHandlerPage()
    return page
