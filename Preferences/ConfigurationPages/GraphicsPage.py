# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Printer configuration page.
"""

from PyQt6.QtCore import pyqtSlot

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_GraphicsPage import Ui_GraphicsPage


class GraphicsPage(ConfigurationPageBase, Ui_GraphicsPage):
    """
    Class implementing the Printer configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("GraphicsPage")

        # set initial values
        self.graphicsFont = Preferences.getGraphics("Font")
        self.graphicsFontSample.setFont(self.graphicsFont)

        drawingMode = Preferences.getGraphics("DrawingMode")
        if drawingMode == "black_white":
            self.blackWhiteButton.setChecked(True)
        elif drawingMode == "white_black":
            self.whiteBlackButton.setChecked(True)
        else:
            self.automaticButton.setChecked(True)

    def save(self):
        """
        Public slot to save the Printer configuration.
        """
        Preferences.setGraphics("Font", self.graphicsFont)

        if self.blackWhiteButton.isChecked():
            drawingMode = "black_white"
        elif self.whiteBlackButton.isChecked():
            drawingMode = "white_black"
        else:
            # default is automatic
            drawingMode = "automatic"
        Preferences.setGraphics("DrawingMode", drawingMode)

    @pyqtSlot()
    def on_graphicsFontButton_clicked(self):
        """
        Private method used to select the font for the graphics items.
        """
        self.graphicsFont = self.selectFont(self.graphicsFontSample, self.graphicsFont)

    def polishPage(self):
        """
        Public slot to perform some polishing actions.
        """
        self.graphicsFontSample.setFont(self.graphicsFont)


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = GraphicsPage()
    return page
