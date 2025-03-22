# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the PDF Viewer configuration page.
"""

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_PdfViewerPage import Ui_PdfViewerPage


class PdfViewerPage(ConfigurationPageBase, Ui_PdfViewerPage):
    """
    Class implementing the PDF Viewer configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("PdfViewerPage")

        # set initial values
        self.contextLengthSpinBox.setValue(
            Preferences.getPdfViewer("PdfSearchContextLength")
        )
        self.highlightCheckBox.setChecked(
            Preferences.getPdfViewer("PdfSearchHighlightAll")
        )
        self.recentFilesSpinBox.setValue(Preferences.getPdfViewer("RecentNumber"))

    def save(self):
        """
        Public slot to save the IRC configuration.
        """
        Preferences.setPdfViewer(
            "PdfSearchContextLength", self.contextLengthSpinBox.value()
        )
        Preferences.setPdfViewer(
            "PdfSearchHighlightAll", self.highlightCheckBox.isChecked()
        )
        Preferences.setPdfViewer("RecentNumber", self.recentFilesSpinBox.value())


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = PdfViewerPage()
    return page
