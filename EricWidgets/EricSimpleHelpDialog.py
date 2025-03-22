# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show some help text.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from .Ui_EricSimpleHelpDialog import Ui_EricSimpleHelpDialog


class EricSimpleHelpDialog(QDialog, Ui_EricSimpleHelpDialog):
    """
    Class implementing a dialog to show some help text.
    """

    def __init__(self, title="", label="", helpStr="", parent=None):
        """
        Constructor

        @param title title of the window
        @type str
        @param label label for the help
        @type str
        @param helpStr HTML help text
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setWindowFlags(Qt.WindowType.Window)

        self.setWindowTitle(title)
        if label:
            self.helpLabel.setText(label)
        else:
            self.helpLabel.hide()
        self.helpEdit.setHtml(helpStr)
