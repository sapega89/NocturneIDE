# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor Syntax Checker configuration page.
"""

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorSyntaxPage import Ui_EditorSyntaxPage


class EditorSyntaxPage(ConfigurationPageBase, Ui_EditorSyntaxPage):
    """
    Class implementing the Editor Syntax Checker configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorSyntaxPage")

        # set initial values
        self.onlineCheckBox.setChecked(Preferences.getEditor("OnlineSyntaxCheck"))
        self.onlineTimeoutSpinBox.setValue(
            Preferences.getEditor("OnlineSyntaxCheckInterval")
        )

        # pyflakes related stuff
        self.includeCheckBox.setChecked(Preferences.getFlakes("IncludeInSyntaxCheck"))
        self.ignoreStarImportCheckBox.setChecked(
            Preferences.getFlakes("IgnoreStarImportWarnings")
        )
        self.builtinsEdit.setPlainText(
            " ".join(Preferences.getFlakes("AdditionalBuiltins"))
        )

    def save(self):
        """
        Public slot to save the Editor Syntax Checker configuration.
        """
        Preferences.setEditor("OnlineSyntaxCheck", self.onlineCheckBox.isChecked())
        Preferences.setEditor(
            "OnlineSyntaxCheckInterval", self.onlineTimeoutSpinBox.value()
        )

        # pyflakes related stuff
        Preferences.setFlakes("IncludeInSyntaxCheck", self.includeCheckBox.isChecked())
        Preferences.setFlakes(
            "IgnoreStarImportWarnings", self.ignoreStarImportCheckBox.isChecked()
        )
        Preferences.setFlakes(
            "AdditionalBuiltins", self.builtinsEdit.toPlainText().strip().split()
        )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorSyntaxPage()
    return page
