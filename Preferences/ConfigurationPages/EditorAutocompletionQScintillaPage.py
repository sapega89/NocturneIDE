# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the QScintilla Autocompletion configuration page.
"""

from PyQt6.Qsci import QsciScintilla

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorAutocompletionQScintillaPage import Ui_EditorAutocompletionQScintillaPage


class EditorAutocompletionQScintillaPage(
    ConfigurationPageBase, Ui_EditorAutocompletionQScintillaPage
):
    """
    Class implementing the QScintilla Autocompletion configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorAutocompletionQScintillaPage")

        # set initial values
        self.acShowSingleCheckBox.setChecked(
            Preferences.getEditor("AutoCompletionShowSingle")
        )
        self.acFillupsCheckBox.setChecked(
            Preferences.getEditor("AutoCompletionFillups")
        )

        acSource = Preferences.getEditor("AutoCompletionSource")
        if acSource == QsciScintilla.AutoCompletionSource.AcsDocument:
            self.acSourceDocumentRadioButton.setChecked(True)
        elif acSource == QsciScintilla.AutoCompletionSource.AcsAPIs:
            self.acSourceAPIsRadioButton.setChecked(True)
        elif acSource == QsciScintilla.AutoCompletionSource.AcsAll:
            self.acSourceAllRadioButton.setChecked(True)

    def save(self):
        """
        Public slot to save the Editor Autocompletion configuration.
        """
        Preferences.setEditor(
            "AutoCompletionShowSingle", self.acShowSingleCheckBox.isChecked()
        )
        Preferences.setEditor(
            "AutoCompletionFillups", self.acFillupsCheckBox.isChecked()
        )
        if self.acSourceDocumentRadioButton.isChecked():
            Preferences.setEditor(
                "AutoCompletionSource", QsciScintilla.AutoCompletionSource.AcsDocument
            )
        elif self.acSourceAPIsRadioButton.isChecked():
            Preferences.setEditor(
                "AutoCompletionSource", QsciScintilla.AutoCompletionSource.AcsAPIs
            )
        elif self.acSourceAllRadioButton.isChecked():
            Preferences.setEditor(
                "AutoCompletionSource", QsciScintilla.AutoCompletionSource.AcsAll
            )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorAutocompletionQScintillaPage()
    return page
