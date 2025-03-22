# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the QScintilla Calltips configuration page.
"""

from PyQt6.Qsci import QsciScintilla

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorCalltipsQScintillaPage import Ui_EditorCalltipsQScintillaPage


class EditorCalltipsQScintillaPage(
    ConfigurationPageBase, Ui_EditorCalltipsQScintillaPage
):
    """
    Class implementing the QScintilla Calltips configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorCalltipsQScintillaPage")

        # set initial values
        ctContext = Preferences.getEditor("CallTipsStyle")
        if ctContext == QsciScintilla.CallTipsStyle.CallTipsNoContext:
            self.ctNoContextButton.setChecked(True)
        elif ctContext == QsciScintilla.CallTipsStyle.CallTipsNoAutoCompletionContext:
            self.ctNoAutoCompletionButton.setChecked(True)
        elif ctContext == QsciScintilla.CallTipsStyle.CallTipsContext:
            self.ctContextButton.setChecked(True)

    def save(self):
        """
        Public slot to save the EditorCalltips configuration.
        """
        if self.ctNoContextButton.isChecked():
            Preferences.setEditor(
                "CallTipsStyle", QsciScintilla.CallTipsStyle.CallTipsNoContext
            )
        elif self.ctNoAutoCompletionButton.isChecked():
            Preferences.setEditor(
                "CallTipsStyle",
                QsciScintilla.CallTipsStyle.CallTipsNoAutoCompletionContext,
            )
        elif self.ctContextButton.isChecked():
            Preferences.setEditor(
                "CallTipsStyle", QsciScintilla.CallTipsStyle.CallTipsContext
            )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorCalltipsQScintillaPage()
    return page
