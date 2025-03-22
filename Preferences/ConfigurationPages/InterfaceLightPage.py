# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2019 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Interface configuration page (variant for web browser).
"""

import glob
import os

from PyQt6.QtCore import QTranslator, pyqtSlot
from PyQt6.QtWidgets import QColorDialog, QDialog, QStyleFactory

from eric7 import EricUtilities, Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricIconBar import EricIconBar
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.Globals import getConfig

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_InterfaceLightPage import Ui_InterfaceLightPage


class InterfaceLightPage(ConfigurationPageBase, Ui_InterfaceLightPage):
    """
    Class implementing the Interface configuration page (variant for generic
    use).
    """

    def __init__(self, withSidebars=False):
        """
        Constructor

        @param withSidebars flag indicating to show the sidebars configuration group
            (defaults to False)
        @type bool (optional)
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("InterfacePage")

        self.__withSidebars = withSidebars

        self.styleSheetPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.styleSheetPicker.setFilters(
            self.tr(
                "Qt Style Sheets (*.qss);;Cascading Style Sheets (*.css);;"
                "All files (*)"
            )
        )
        self.styleSheetPicker.setDefaultDirectory(getConfig("ericStylesDir"))

        styleIconsPath = ericApp().getStyleIconsPath()
        self.styleIconsPathPicker.setMode(EricPathPickerModes.DIRECTORY_SHOW_FILES_MODE)
        self.styleIconsPathPicker.setDefaultDirectory(styleIconsPath)

        self.itemSelectionStyleComboBox.addItem(self.tr("System Default"), "default")
        self.itemSelectionStyleComboBox.addItem(self.tr("Double Click"), "doubleclick")
        self.itemSelectionStyleComboBox.addItem(self.tr("Single Click"), "singleclick")

        for iconBarSize in EricIconBar.BarSizes:
            self.iconSizeComboBox.addItem(
                EricIconBar.BarSizes[iconBarSize][2], iconBarSize
            )

        # set initial values
        self.__populateStyleCombo()
        self.__populateLanguageCombo()

        self.styleSheetPicker.setText(Preferences.getUI("StyleSheet"))
        self.styleIconsPathPicker.setText(Preferences.getUI("StyleIconsPath"))

        itemSelectionIndex = self.itemSelectionStyleComboBox.findData(
            Preferences.getUI("ActivateItemOnSingleClick")
        )
        if itemSelectionIndex < 0:
            itemSelectionIndex = 0
        self.itemSelectionStyleComboBox.setCurrentIndex(itemSelectionIndex)

        if self.__withSidebars:
            self.iconSizeComboBox.setCurrentIndex(
                self.iconSizeComboBox.findData(Preferences.getUI("IconBarSize"))
            )
            self.__iconBarColor = Preferences.getUI("IconBarColor")
            self.__setIconBarSamples()

            # connect the icon size combo box after initialization is complete
            self.iconSizeComboBox.currentIndexChanged.connect(self.__setIconBarSamples)
        else:
            self.sidebarsGroup.setVisible(False)

    def save(self):
        """
        Public slot to save the Interface configuration.
        """
        # save the style settings
        styleIndex = self.styleComboBox.currentIndex()
        style = self.styleComboBox.itemData(styleIndex)
        Preferences.setUI("Style", style)
        Preferences.setUI("StyleSheet", self.styleSheetPicker.text())
        Preferences.setUI("StyleIconsPath", self.styleIconsPathPicker.text())
        Preferences.setUI(
            "ActivateItemOnSingleClick", self.itemSelectionStyleComboBox.currentData()
        )

        # save the language settings
        uiLanguageIndex = self.languageComboBox.currentIndex()
        uiLanguage = (
            self.languageComboBox.itemData(uiLanguageIndex) if uiLanguageIndex else None
        )
        Preferences.setUILanguage(uiLanguage)

        if self.__withSidebars:
            # save the sidebars settings
            Preferences.setUI("IconBarSize", self.iconSizeComboBox.currentData())
            Preferences.setUI("IconBarColor", self.__iconBarColor)

    def __populateStyleCombo(self):
        """
        Private method to populate the style combo box.
        """
        curStyle = Preferences.getUI("Style")
        styles = sorted(QStyleFactory.keys())
        self.styleComboBox.addItem(self.tr("System"), "System")
        for style in styles:
            self.styleComboBox.addItem(style, style)
        currentIndex = self.styleComboBox.findData(curStyle)
        if currentIndex == -1:
            currentIndex = 0
        self.styleComboBox.setCurrentIndex(currentIndex)

    def __populateLanguageCombo(self):
        """
        Private method to initialize the language combo box.
        """
        self.languageComboBox.clear()

        fnlist = (
            glob.glob("eric7_*.qm")
            + glob.glob(os.path.join(getConfig("ericTranslationsDir"), "eric7_*.qm"))
            + glob.glob(os.path.join(EricUtilities.getConfigDir(), "eric7_*.qm"))
        )
        locales = {}
        for fn in fnlist:
            locale = os.path.basename(fn)[6:-3]
            if locale not in locales:
                translator = QTranslator()
                translator.load(fn)
                locales[locale] = translator.translate(
                    "InterfacePage", "English", "Translate this with your language"
                ) + " ({0})".format(locale)
        localeList = sorted(locales)
        try:
            uiLanguage = Preferences.getUILanguage()
            if uiLanguage == "None" or uiLanguage is None:
                currentIndex = 0
            elif uiLanguage == "System":
                currentIndex = 1
            else:
                currentIndex = localeList.index(uiLanguage) + 2
        except ValueError:
            currentIndex = 0
        self.languageComboBox.clear()

        self.languageComboBox.addItem("English (default)", "None")
        self.languageComboBox.addItem(self.tr("System"), "System")
        for locale in localeList:
            self.languageComboBox.addItem(locales[locale], locale)
        self.languageComboBox.setCurrentIndex(currentIndex)

    @pyqtSlot()
    def __setIconBarSamples(self):
        """
        Private slot to set the colors of the icon bar color samples.
        """
        iconBarSize = self.iconSizeComboBox.currentData()
        iconSize, borderSize = EricIconBar.BarSizes[iconBarSize][:2]
        size = iconSize + 2 * borderSize

        self.sampleLabel.setFixedSize(size, size)
        self.sampleLabel.setStyleSheet(
            EricIconBar.LabelStyleSheetTemplate.format(self.__iconBarColor.name())
        )
        self.sampleLabel.setPixmap(
            EricPixmapCache.getIcon("sbDebugViewer96").pixmap(iconSize, iconSize)
        )

        self.highlightedSampleLabel.setFixedSize(size, size)
        self.highlightedSampleLabel.setStyleSheet(
            EricIconBar.LabelStyleSheetTemplate.format(
                self.__iconBarColor.darker().name()
            )
        )
        self.highlightedSampleLabel.setPixmap(
            EricPixmapCache.getIcon("sbDebugViewer96").pixmap(iconSize, iconSize)
        )

    @pyqtSlot()
    def on_iconBarButton_clicked(self):
        """
        Private slot to select the icon bar color.
        """
        colDlg = QColorDialog(parent=self)
        # Set current colour last to avoid conflicts with alpha channel
        colDlg.setCurrentColor(self.__iconBarColor)
        if colDlg.exec() == QDialog.DialogCode.Accepted:
            self.__iconBarColor = colDlg.selectedColor()
            self.__setIconBarSamples()


def create(_dlg, withSidebars=False):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @param withSidebars flag indicating to show the sidebars configuration group
        (defaults to False)
    @type bool (optional)
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = InterfaceLightPage(withSidebars=withSidebars)
    return page
