# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Diff colours configuration page.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QColorDialog

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_DiffColoursPage import Ui_DiffColoursPage


class DiffColoursPage(ConfigurationPageBase, Ui_DiffColoursPage):
    """
    Class implementing the Diff colours configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("DiffColoursPage")

        self.__coloursDict = {}

        monospacedFont = Preferences.getEditorOtherFonts("MonospacedFont")
        self.__allSamples = (
            self.textSample,
            self.addedSample,
            self.removedSample,
            self.replacedSample,
            self.contextSample,
            self.headerSample,
            self.whitespaceSample,
        )
        for sample in self.__allSamples:
            sample.setFont(monospacedFont)

        # set initial values
        self.__initColour(
            "TextColor",
            self.textButton,
            self.__updateSampleTextColour,
            lambda: self.__selectTextColour(self.textButton),
            self.textSample,
        )
        self.__initColour(
            "AddedColor",
            self.addedButton,
            self.__updateSampleBackgroundColour,
            lambda: self.__selectBackgroundColour(self.addedButton),
            self.addedSample,
        )
        self.__initColour(
            "RemovedColor",
            self.removedButton,
            self.__updateSampleBackgroundColour,
            lambda: self.__selectBackgroundColour(self.removedButton),
            self.removedSample,
        )
        self.__initColour(
            "ReplacedColor",
            self.replacedButton,
            self.__updateSampleBackgroundColour,
            lambda: self.__selectBackgroundColour(self.replacedButton),
            self.replacedSample,
        )
        self.__initColour(
            "ContextColor",
            self.contextButton,
            self.__updateSampleBackgroundColour,
            lambda: self.__selectBackgroundColour(self.contextButton),
            self.contextSample,
        )
        self.__initColour(
            "HeaderColor",
            self.headerButton,
            self.__updateSampleBackgroundColour,
            lambda: self.__selectBackgroundColour(self.headerButton),
            self.headerSample,
        )
        self.__initColour(
            "BadWhitespaceColor",
            self.whitespaceButton,
            self.__updateSampleBackgroundColour,
            lambda: self.__selectBackgroundColour(self.whitespaceButton),
            self.whitespaceSample,
        )

    def save(self):
        """
        Public slot to save the Diff colours configuration.
        """
        for key in self.__coloursDict:
            Preferences.setDiffColour(key, self.__coloursDict[key][0])

    def __initColour(self, colourKey, button, initSlot, selectSlot, sampleWidget):
        """
        Private method to initialize a colour selection button.

        @param colourKey key of the diff colour
        @type str
        @param button reference to the button
        @type QPushButton
        @param initSlot slot to be called to initialize the sample
        @type func
        @param selectSlot slot to be called to select the colour
        @type func
        @param sampleWidget reference to the sample widget
        @type QLineEdit
        """
        colour = Preferences.getDiffColour(colourKey)
        button.setProperty("colorKey", colourKey)
        button.clicked.connect(selectSlot)
        self.__coloursDict[colourKey] = [colour, sampleWidget]
        if initSlot:
            initSlot(colourKey)

    @pyqtSlot()
    def __selectTextColour(self, button):
        """
        Private slot to select the text colour.

        @param button reference to the button been pressed
        @type QPushButton
        """
        colorKey = button.property("colorKey")

        colour = QColorDialog.getColor(self.__coloursDict[colorKey][0], self)
        if colour.isValid():
            self.__coloursDict[colorKey][0] = colour
            self.__updateSampleTextColour(colorKey)

    @pyqtSlot()
    def __selectBackgroundColour(self, button):
        """
        Private slot to select a background colour.

        @param button reference to the button been pressed
        @type QPushButton
        """
        colorKey = button.property("colorKey")

        colour = QColorDialog.getColor(
            self.__coloursDict[colorKey][0],
            self,
            "",
            QColorDialog.ColorDialogOption.ShowAlphaChannel,
        )
        if colour.isValid():
            self.__coloursDict[colorKey][0] = colour
            self.__updateSampleBackgroundColour(colorKey)

    @pyqtSlot()
    def __updateSampleTextColour(self, colourKey):
        """
        Private slot to update the text colour of all samples.

        @param colourKey key of the diff colour
        @type str
        """
        colour = self.__coloursDict[colourKey][0]
        for key in self.__coloursDict:
            if key == "TextColor":
                self.__coloursDict[key][1].setStyleSheet(
                    "QLineEdit {{ color: {0}; }}".format(colour.name())
                )
            else:
                self.__coloursDict[key][1].setStyleSheet(
                    "QLineEdit {{ color: {0}; background-color: {1}; }}".format(
                        colour.name(), self.__coloursDict[key][0].name()
                    )
                )

    def __updateSampleBackgroundColour(self, colourKey):
        """
        Private slot to update the background colour of a sample.

        @param colourKey key of the diff colour
        @type str
        """
        sample = self.__coloursDict[colourKey][1]
        if sample:
            colour = self.__coloursDict[colourKey][0]
            sample.setStyleSheet(
                "QLineEdit {{ color: {0}; background-color: {1}; }}".format(
                    self.__coloursDict["TextColor"][0].name(), colour.name()
                )
            )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = DiffColoursPage()
    return page
