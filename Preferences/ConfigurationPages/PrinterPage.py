# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Printer configuration page.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QButtonGroup

from eric7 import Preferences
from eric7.QScintilla.QsciScintillaCompat import QsciScintillaPrintColorMode

from ..ConfigurationDialog import ConfigurationMode
from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_PrinterPage import Ui_PrinterPage


class PrinterPage(ConfigurationPageBase, Ui_PrinterPage):
    """
    Class implementing the Printer configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("PrinterPage")

        self.__displayMode = None

        self.__printColorModeGroup = QButtonGroup()
        self.__printColorModeGroup.addButton(
            self.normalModeButton, QsciScintillaPrintColorMode.Normal
        )
        self.__printColorModeGroup.addButton(
            self.invertLightModeButton, QsciScintillaPrintColorMode.InvertLight
        )
        self.__printColorModeGroup.addButton(
            self.blackOnWhiteModeButton, QsciScintillaPrintColorMode.BlackOnWhite
        )
        self.__printColorModeGroup.addButton(
            self.colorOnWhiteModeButton, QsciScintillaPrintColorMode.ColorOnWhite
        )
        self.__printColorModeGroup.addButton(
            self.colorOnWhiteDefaultModeButton,
            QsciScintillaPrintColorMode.ColorOnWhiteDefaultBackground,
        )
        self.__printColorModeGroup.addButton(
            self.screenColorsModeButton, QsciScintillaPrintColorMode.ScreenColors
        )

        # set initial values
        self.printerNameEdit.setText(Preferences.getPrinter("PrinterName"))
        if Preferences.getPrinter("ColorMode"):
            self.printerColorButton.setChecked(True)
        else:
            self.printerGrayscaleButton.setChecked(True)
        if Preferences.getPrinter("FirstPageFirst"):
            self.printFirstPageFirstButton.setChecked(True)
        else:
            self.printFirstPageLastButton.setChecked(True)
        self.printMagnificationSpinBox.setValue(Preferences.getPrinter("Magnification"))
        self.printheaderFont = Preferences.getPrinter("HeaderFont")
        self.printheaderFontSample.setFont(self.printheaderFont)
        self.leftMarginSpinBox.setValue(Preferences.getPrinter("LeftMargin"))
        self.rightMarginSpinBox.setValue(Preferences.getPrinter("RightMargin"))
        self.topMarginSpinBox.setValue(Preferences.getPrinter("TopMargin"))
        self.bottomMarginSpinBox.setValue(Preferences.getPrinter("BottomMargin"))
        self.resolutionSpinBox.setValue(Preferences.getPrinter("Resolution"))

        # editor related printer setting
        self.__printColorModeGroup.button(
            Preferences.getEditor("PrintColorMode")
        ).setChecked(True)

    def setMode(self, displayMode):
        """
        Public method to perform mode dependent setups.

        @param displayMode mode of the configuration dialog
        @type ConfigurationMode
        """
        self.__displayMode = displayMode
        self.printColorModeBox.setVisible(
            self.__displayMode
            in (
                ConfigurationMode.DEFAULTMODE,
                ConfigurationMode.EDITORMODE,
            )
        )

    def save(self):
        """
        Public slot to save the Printer configuration.
        """
        Preferences.setPrinter("PrinterName", self.printerNameEdit.text())
        if self.printerColorButton.isChecked():
            Preferences.setPrinter("ColorMode", 1)
        else:
            Preferences.setPrinter("ColorMode", 0)
        if self.printFirstPageFirstButton.isChecked():
            Preferences.setPrinter("FirstPageFirst", 1)
        else:
            Preferences.setPrinter("FirstPageFirst", 0)
        Preferences.setPrinter("Magnification", self.printMagnificationSpinBox.value())
        Preferences.setPrinter("HeaderFont", self.printheaderFont)
        Preferences.setPrinter("LeftMargin", self.leftMarginSpinBox.value())
        Preferences.setPrinter("RightMargin", self.rightMarginSpinBox.value())
        Preferences.setPrinter("TopMargin", self.topMarginSpinBox.value())
        Preferences.setPrinter("BottomMargin", self.bottomMarginSpinBox.value())
        Preferences.setPrinter("Resolution", self.resolutionSpinBox.value())

        if self.__displayMode in (
            ConfigurationMode.DEFAULTMODE,
            ConfigurationMode.EDITORMODE,
        ):
            # editor related printer setting
            Preferences.setEditor(
                "PrintColorMode",
                QsciScintillaPrintColorMode(self.__printColorModeGroup.checkedId()),
            )

    @pyqtSlot()
    def on_printheaderFontButton_clicked(self):
        """
        Private method used to select the font for the page header.
        """
        self.printheaderFont = self.selectFont(
            self.printheaderFontSample, self.printheaderFont
        )

    def polishPage(self):
        """
        Public slot to perform some polishing actions.
        """
        self.printheaderFontSample.setFont(self.printheaderFont)


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = PrinterPage()
    return page
