# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Interface configuration page.
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
from .Ui_InterfacePage import Ui_InterfacePage


class InterfacePage(ConfigurationPageBase, Ui_InterfacePage):
    """
    Class implementing the Interface configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("InterfacePage")

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

        self.uiBrowsersListFoldersFirstCheckBox.setChecked(
            Preferences.getUI("BrowsersListFoldersFirst")
        )
        self.uiBrowsersHideNonPublicCheckBox.setChecked(
            Preferences.getUI("BrowsersHideNonPublic")
        )
        self.uiBrowsersSortByOccurrenceCheckBox.setChecked(
            Preferences.getUI("BrowsersListContentsByOccurrence")
        )
        self.browserShowCodingCheckBox.setChecked(
            Preferences.getUI("BrowserShowCoding")
        )
        self.browserShowConnectedServerOnlyCheckBox.setChecked(
            Preferences.getUI("BrowsersFilterRemoteEntries")
        )
        self.fileFiltersEdit.setText(Preferences.getUI("BrowsersFileFilters"))

        self.uiCaptionShowsFilenameGroupBox.setChecked(
            Preferences.getUI("CaptionShowsFilename")
        )
        self.filenameLengthSpinBox.setValue(Preferences.getUI("CaptionFilenameLength"))
        self.styleSheetPicker.setText(Preferences.getUI("StyleSheet"))
        self.styleIconsPathPicker.setText(Preferences.getUI("StyleIconsPath"))

        itemSelectionIndex = self.itemSelectionStyleComboBox.findData(
            Preferences.getUI("ActivateItemOnSingleClick")
        )
        if itemSelectionIndex < 0:
            itemSelectionIndex = 0
        self.itemSelectionStyleComboBox.setCurrentIndex(itemSelectionIndex)

        layoutType = Preferences.getUI("LayoutType")
        if layoutType == "Sidebars":
            index = 0
        elif layoutType == "Toolboxes":
            index = 1
        else:
            index = 0  # default for bad values
        self.layoutComboBox.setCurrentIndex(index)

        # integrated tools activation
        # left side
        self.findReplaceCheckBox.setChecked(Preferences.getUI("ShowFindFileWidget"))
        self.findLocationCheckBox.setChecked(
            Preferences.getUI("ShowFindLocationWidget")
        )
        self.templateViewerCheckBox.setChecked(Preferences.getUI("ShowTemplateViewer"))
        self.fileBrowserCheckBox.setChecked(Preferences.getUI("ShowFileBrowser"))
        self.symbolsCheckBox.setChecked(Preferences.getUI("ShowSymbolsViewer"))
        # right side
        self.codeDocumentationViewerCheckBox.setChecked(
            Preferences.getUI("ShowCodeDocumentationViewer")
        )
        self.helpViewerCheckBox.setChecked(Preferences.getUI("ShowInternalHelpViewer"))
        self.condaCheckBox.setChecked(Preferences.getUI("ShowCondaPackageManager"))
        self.pypiCheckBox.setChecked(Preferences.getUI("ShowPyPIPackageManager"))
        self.cooperationCheckBox.setChecked(Preferences.getUI("ShowCooperation"))
        self.ircCheckBox.setChecked(Preferences.getUI("ShowIrc"))
        self.microPythonCheckBox.setChecked(Preferences.getUI("ShowMicroPython"))
        # bottom side
        self.numbersCheckBox.setChecked(Preferences.getUI("ShowNumbersViewer"))

        self.iconSizeComboBox.setCurrentIndex(
            self.iconSizeComboBox.findData(Preferences.getUI("IconBarSize"))
        )
        self.__iconBarColor = Preferences.getUI("IconBarColor")
        self.__setIconBarSamples()

        self.combinedLeftRightSidebarCheckBox.setChecked(
            Preferences.getUI("CombinedLeftRightSidebar")
        )

        # connect the icon size combo box after initialization is complete
        self.iconSizeComboBox.currentIndexChanged.connect(self.__setIconBarSamples)

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

        # save the other UI related settings
        Preferences.setUI(
            "BrowsersListFoldersFirst",
            self.uiBrowsersListFoldersFirstCheckBox.isChecked(),
        )
        Preferences.setUI(
            "BrowsersHideNonPublic", self.uiBrowsersHideNonPublicCheckBox.isChecked()
        )
        Preferences.setUI(
            "BrowsersListContentsByOccurrence",
            self.uiBrowsersSortByOccurrenceCheckBox.isChecked(),
        )
        Preferences.setUI(
            "BrowserShowCoding", self.browserShowCodingCheckBox.isChecked()
        )
        Preferences.setUI(
            "BrowsersFilterRemoteEntries",
            self.browserShowConnectedServerOnlyCheckBox.isChecked(),
        )
        Preferences.setUI("BrowsersFileFilters", self.fileFiltersEdit.text())

        Preferences.setUI(
            "CaptionShowsFilename", self.uiCaptionShowsFilenameGroupBox.isChecked()
        )
        Preferences.setUI("CaptionFilenameLength", self.filenameLengthSpinBox.value())

        # save the language settings
        uiLanguageIndex = self.languageComboBox.currentIndex()
        uiLanguage = (
            self.languageComboBox.itemData(uiLanguageIndex) if uiLanguageIndex else None
        )
        Preferences.setUILanguage(uiLanguage)

        # save the interface layout settings
        if self.layoutComboBox.currentIndex() == 0:
            layoutType = "Sidebars"
        elif self.layoutComboBox.currentIndex() == 1:
            layoutType = "Toolboxes"
        else:
            layoutType = "Sidebars"  # just in case
        Preferences.setUI("LayoutType", layoutType)

        # save the integrated tools activation
        # left side
        Preferences.setUI("ShowFindFileWidget", self.findReplaceCheckBox.isChecked())
        Preferences.setUI(
            "ShowFindLocationWidget", self.findLocationCheckBox.isChecked()
        )
        Preferences.setUI("ShowTemplateViewer", self.templateViewerCheckBox.isChecked())
        Preferences.setUI("ShowFileBrowser", self.fileBrowserCheckBox.isChecked())
        Preferences.setUI("ShowSymbolsViewer", self.symbolsCheckBox.isChecked())
        # right side
        Preferences.setUI(
            "ShowCodeDocumentationViewer",
            self.codeDocumentationViewerCheckBox.isChecked(),
        )
        Preferences.setUI("ShowInternalHelpViewer", self.helpViewerCheckBox.isChecked())
        Preferences.setUI("ShowCondaPackageManager", self.condaCheckBox.isChecked())
        Preferences.setUI("ShowPyPIPackageManager", self.pypiCheckBox.isChecked())
        Preferences.setUI("ShowCooperation", self.cooperationCheckBox.isChecked())
        Preferences.setUI("ShowIrc", self.ircCheckBox.isChecked())
        Preferences.setUI("ShowMicroPython", self.microPythonCheckBox.isChecked())
        # bottom side
        Preferences.setUI("ShowNumbersViewer", self.numbersCheckBox.isChecked())

        # save the sidebars settings
        Preferences.setUI("IconBarSize", self.iconSizeComboBox.currentData())
        Preferences.setUI("IconBarColor", self.__iconBarColor)
        Preferences.setUI(
            "CombinedLeftRightSidebar",
            self.combinedLeftRightSidebarCheckBox.isChecked(),
        )

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
    def on_resetLayoutButton_clicked(self):
        """
        Private method to reset layout to factory defaults.
        """
        Preferences.resetLayout()

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

    @pyqtSlot(bool)
    def on_combinedLeftRightSidebarCheckBox_toggled(self, checked):
        """
        Private slot handling a change of the combined sidebars checkbox.

        @param checked state of the checkbox
        @type bool
        """
        self.leftRightGroupBox.setTitle(
            self.tr("Combined Left Side") if checked else self.tr("Right Side")
        )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = InterfacePage()
    return page
