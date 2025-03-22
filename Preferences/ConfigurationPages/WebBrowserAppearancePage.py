# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Web Browser Appearance configuration page.
"""

from PyQt6.QtGui import QFont

from eric7 import Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_WebBrowserAppearancePage import Ui_WebBrowserAppearancePage


class WebBrowserAppearancePage(ConfigurationPageBase, Ui_WebBrowserAppearancePage):
    """
    Class implementing the Web Browser Appearance page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("WebBrowserAppearancePage")

        self.styleSheetPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.styleSheetPicker.setFilters(
            self.tr("Cascading Style Sheets (*.css);;All files (*)")
        )

        self.__displayMode = None

        # set initial values
        defaultFontSize = Preferences.getWebBrowser("DefaultFontSize")
        fixedFontSize = Preferences.getWebBrowser("DefaultFixedFontSize")
        self.defaultSizeSpinBox.setValue(defaultFontSize)
        self.fixedSizeSpinBox.setValue(fixedFontSize)
        self.minSizeSpinBox.setValue(Preferences.getWebBrowser("MinimumFontSize"))
        self.minLogicalSizeSpinBox.setValue(
            Preferences.getWebBrowser("MinimumLogicalFontSize")
        )

        self.standardFontCombo.setCurrentFont(
            QFont(
                [Preferences.getWebBrowser("StandardFontFamily")],
                defaultFontSize,
                QFont.Weight.Normal,
                False,
            )
        )
        self.fixedFontCombo.setCurrentFont(
            QFont(
                [Preferences.getWebBrowser("FixedFontFamily")],
                fixedFontSize,
                QFont.Weight.Normal,
                False,
            )
        )
        self.serifFontCombo.setCurrentFont(
            QFont(
                [Preferences.getWebBrowser("SerifFontFamily")],
                defaultFontSize,
                QFont.Weight.Normal,
                False,
            )
        )
        self.sansSerifFontCombo.setCurrentFont(
            QFont(
                [Preferences.getWebBrowser("SansSerifFontFamily")],
                defaultFontSize,
                QFont.Weight.Normal,
                False,
            )
        )
        self.cursiveFontCombo.setCurrentFont(
            QFont(
                [Preferences.getWebBrowser("CursiveFontFamily")],
                defaultFontSize,
                QFont.Weight.Normal,
                True,
            )
        )
        self.fantasyFontCombo.setCurrentFont(
            QFont(
                [Preferences.getWebBrowser("FantasyFontFamily")],
                defaultFontSize,
                QFont.Weight.Normal,
                False,
            )
        )

        self.initColour(
            "SecureUrlColor", self.secureURLsColourButton, Preferences.getWebBrowser
        )
        self.initColour(
            "InsecureUrlColor", self.insecureURLsColourButton, Preferences.getWebBrowser
        )
        self.initColour(
            "MaliciousUrlColor",
            self.maliciousURLsColourButton,
            Preferences.getWebBrowser,
        )
        self.initColour(
            "PrivateModeUrlColor",
            self.privateModeURLsColourButton,
            Preferences.getWebBrowser,
        )

        self.autoLoadImagesCheckBox.setChecked(
            Preferences.getWebBrowser("AutoLoadImages")
        )

        self.styleSheetPicker.setText(Preferences.getWebBrowser("UserStyleSheet"))

        self.warnOnMultipleCloseCheckBox.setChecked(
            Preferences.getWebBrowser("WarnOnMultipleClose")
        )

        self.scrollbarsCheckBox.setChecked(Preferences.getWebBrowser("ShowScrollBars"))
        self.toolbarsCheckBox.setChecked(Preferences.getWebBrowser("ShowToolbars"))

    def setMode(self, displayMode):
        """
        Public method to perform mode dependent setups.

        @param displayMode mode of the configuration dialog
        @type ConfigurationMode
        """
        from ..ConfigurationDialog import ConfigurationMode

        if displayMode in (
            ConfigurationMode.DEFAULTMODE,
            ConfigurationMode.WEBBROWSERMODE,
        ):
            self.__displayMode = displayMode

    def save(self):
        """
        Public slot to save the Help Viewers configuration.
        """
        Preferences.setWebBrowser(
            "StandardFontFamily", self.standardFontCombo.currentFont().family()
        )
        Preferences.setWebBrowser(
            "FixedFontFamily", self.fixedFontCombo.currentFont().family()
        )
        Preferences.setWebBrowser(
            "SerifFontFamily", self.serifFontCombo.currentFont().family()
        )
        Preferences.setWebBrowser(
            "SansSerifFontFamily", self.sansSerifFontCombo.currentFont().family()
        )
        Preferences.setWebBrowser(
            "CursiveFontFamily", self.cursiveFontCombo.currentFont().family()
        )
        Preferences.setWebBrowser(
            "FantasyFontFamily", self.fantasyFontCombo.currentFont().family()
        )

        Preferences.setWebBrowser("DefaultFontSize", self.defaultSizeSpinBox.value())
        Preferences.setWebBrowser("DefaultFixedFontSize", self.fixedSizeSpinBox.value())
        Preferences.setWebBrowser("MinimumFontSize", self.minSizeSpinBox.value())
        Preferences.setWebBrowser(
            "MinimumLogicalFontSize", self.minLogicalSizeSpinBox.value()
        )

        Preferences.setWebBrowser(
            "AutoLoadImages", self.autoLoadImagesCheckBox.isChecked()
        )

        Preferences.setWebBrowser("UserStyleSheet", self.styleSheetPicker.text())

        self.saveColours(Preferences.setWebBrowser)

        Preferences.setWebBrowser(
            "WarnOnMultipleClose", self.warnOnMultipleCloseCheckBox.isChecked()
        )

        if self.scrollbarsCheckBox.isEnabled():
            Preferences.setWebBrowser(
                "ShowScrollBars", self.scrollbarsCheckBox.isChecked()
            )

        Preferences.setWebBrowser("ShowToolbars", self.toolbarsCheckBox.isChecked())


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = WebBrowserAppearancePage()
    return page
