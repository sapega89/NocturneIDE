# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Editor File Handling configuration page.
"""

import importlib.util

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QInputDialog, QLineEdit, QListWidgetItem

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.QScintilla import Lexers
from eric7.SystemUtilities import PythonUtilities
from eric7.Utilities import supportedCodecs

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_EditorFilePage import Ui_EditorFilePage


class EditorFilePage(ConfigurationPageBase, Ui_EditorFilePage):
    """
    Class implementing the Editor File Handling configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("EditorFilePage")

        self.__showsOpenFilters = True
        self.openFileFilters = Preferences.getEditor("AdditionalOpenFilters")[:]
        self.saveFileFilters = Preferences.getEditor("AdditionalSaveFilters")[:]
        self.fileFiltersList.addItems(self.openFileFilters)

        self.__setDefaultFiltersLists()

        self.defaultEncodingComboBox.addItems(sorted(supportedCodecs))

        self.previewMarkdownHTMLFormatComboBox.addItems(["XHTML1", "HTML4", "HTML5"])
        self.previewRestDocutilsHTMLFormatComboBox.addItems(["HTML4", "HTML5"])

        # set initial values
        self.autosaveSpinBox.setValue(Preferences.getEditor("AutosaveIntervalSeconds"))
        self.autosaveOnFocusLostCheckBox.setChecked(
            Preferences.getEditor("AutosaveOnFocusLost")
        )
        self.createBackupFileCheckBox.setChecked(
            Preferences.getEditor("CreateBackupFile")
        )
        self.defaultEncodingComboBox.setCurrentIndex(
            self.defaultEncodingComboBox.findText(
                Preferences.getEditor("DefaultEncoding")
            )
        )
        self.advEncodingCheckBox.setChecked(
            Preferences.getEditor("AdvancedEncodingDetection")
        )
        self.warnFilesizeSpinBox.setValue(Preferences.getEditor("WarnFilesize"))
        self.rejectFilesizeSpinBox.setValue(Preferences.getEditor("RejectFilesize"))
        self.clearBreakpointsCheckBox.setChecked(
            Preferences.getEditor("ClearBreaksOnClose")
        )
        self.automaticReopenCheckBox.setChecked(Preferences.getEditor("AutoReopen"))
        self.stripWhitespaceCheckBox.setChecked(
            Preferences.getEditor("StripTrailingWhitespace")
        )
        self.openFilesFilterComboBox.setCurrentIndex(
            self.openFilesFilterComboBox.findText(
                Preferences.getEditor("DefaultOpenFilter")
            )
        )
        self.saveFilesFilterComboBox.setCurrentIndex(
            self.saveFilesFilterComboBox.findText(
                Preferences.getEditor("DefaultSaveFilter")
            )
        )
        self.automaticEolConversionCheckBox.setChecked(
            Preferences.getEditor("AutomaticEOLConversion")
        )
        self.insertFinalNewlineCheckBox.setChecked(
            Preferences.getEditor("InsertFinalNewline")
        )

        eolMode = Preferences.getEditor("EOLMode")
        if eolMode == QsciScintilla.EolMode.EolWindows:
            self.crlfRadioButton.setChecked(True)
        elif eolMode == QsciScintilla.EolMode.EolMac:
            self.crRadioButton.setChecked(True)
        elif eolMode == QsciScintilla.EolMode.EolUnix:
            self.lfRadioButton.setChecked(True)

        self.previewRefreshTimeoutSpinBox.setValue(
            Preferences.getEditor("PreviewRefreshWaitTimer")
        )

        self.previewHtmlExtensionsEdit.setText(
            " ".join(Preferences.getEditor("PreviewHtmlFileNameExtensions"))
        )

        self.previewMarkdownExtensionsEdit.setText(
            " ".join(Preferences.getEditor("PreviewMarkdownFileNameExtensions"))
        )
        self.previewRestSphinxCheckBox.setChecked(
            Preferences.getEditor("PreviewRestUseSphinx")
        )
        self.previewMarkdownNLtoBreakCheckBox.setChecked(
            Preferences.getEditor("PreviewMarkdownNLtoBR")
        )
        self.previewMarkdownPyMdownCheckBox.setChecked(
            Preferences.getEditor("PreviewMarkdownUsePyMdownExtensions")
        )
        self.previewMarkdownMathJaxCheckBox.setChecked(
            Preferences.getEditor("PreviewMarkdownMathJax")
        )
        self.previewMarkdownMermaidCheckBox.setChecked(
            Preferences.getEditor("PreviewMarkdownMermaid")
        )
        index = self.previewMarkdownHTMLFormatComboBox.findText(
            Preferences.getEditor("PreviewMarkdownHTMLFormat")
        )
        self.previewMarkdownHTMLFormatComboBox.setCurrentIndex(index)

        self.previewRestExtensionsEdit.setText(
            " ".join(Preferences.getEditor("PreviewRestFileNameExtensions"))
        )
        index = self.previewRestDocutilsHTMLFormatComboBox.findText(
            Preferences.getEditor("PreviewRestDocutilsHTMLFormat")
        )
        self.previewRestDocutilsHTMLFormatComboBox.setCurrentIndex(index)

        self.previewQssExtensionsEdit.setText(
            " ".join(Preferences.getEditor("PreviewQssFileNameExtensions"))
        )

    def save(self):
        """
        Public slot to save the Editor File Handling configuration.
        """
        Preferences.setEditor("AutosaveIntervalSeconds", self.autosaveSpinBox.value())
        Preferences.setEditor(
            "AutosaveOnFocusLost", self.autosaveOnFocusLostCheckBox.isChecked()
        )
        Preferences.setEditor(
            "CreateBackupFile", self.createBackupFileCheckBox.isChecked()
        )
        enc = self.defaultEncodingComboBox.currentText()
        if not enc:
            enc = "utf-8"
        Preferences.setEditor("DefaultEncoding", enc)
        Preferences.setEditor(
            "AdvancedEncodingDetection", self.advEncodingCheckBox.isChecked()
        )
        Preferences.setEditor("WarnFilesize", self.warnFilesizeSpinBox.value())
        Preferences.setEditor("RejectFilesize", self.rejectFilesizeSpinBox.value())
        Preferences.setEditor(
            "ClearBreaksOnClose", self.clearBreakpointsCheckBox.isChecked()
        )
        Preferences.setEditor("AutoReopen", self.automaticReopenCheckBox.isChecked())
        Preferences.setEditor(
            "StripTrailingWhitespace", self.stripWhitespaceCheckBox.isChecked()
        )
        Preferences.setEditor(
            "DefaultOpenFilter", self.openFilesFilterComboBox.currentText()
        )
        Preferences.setEditor(
            "DefaultSaveFilter", self.saveFilesFilterComboBox.currentText()
        )
        Preferences.setEditor(
            "AutomaticEOLConversion", self.automaticEolConversionCheckBox.isChecked()
        )
        Preferences.setEditor(
            "InsertFinalNewline", self.insertFinalNewlineCheckBox.isChecked()
        )

        if self.crlfRadioButton.isChecked():
            Preferences.setEditor("EOLMode", QsciScintilla.EolMode.EolWindows)
        elif self.crRadioButton.isChecked():
            Preferences.setEditor("EOLMode", QsciScintilla.EolMode.EolMac)
        elif self.lfRadioButton.isChecked():
            Preferences.setEditor("EOLMode", QsciScintilla.EolMode.EolUnix)

        self.__extractFileFilters()
        Preferences.setEditor("AdditionalOpenFilters", self.openFileFilters)
        Preferences.setEditor("AdditionalSaveFilters", self.saveFileFilters)

        Preferences.setEditor(
            "PreviewRefreshWaitTimer", self.previewRefreshTimeoutSpinBox.value()
        )

        Preferences.setEditor(
            "PreviewHtmlFileNameExtensions",
            [ext.strip() for ext in self.previewHtmlExtensionsEdit.text().split()],
        )

        Preferences.setEditor(
            "PreviewMarkdownFileNameExtensions",
            [ext.strip() for ext in self.previewMarkdownExtensionsEdit.text().split()],
        )
        Preferences.setEditor(
            "PreviewRestUseSphinx", self.previewRestSphinxCheckBox.isChecked()
        )
        Preferences.setEditor(
            "PreviewMarkdownNLtoBR", self.previewMarkdownNLtoBreakCheckBox.isChecked()
        )
        Preferences.setEditor(
            "PreviewMarkdownUsePyMdownExtensions",
            self.previewMarkdownPyMdownCheckBox.isChecked(),
        )
        Preferences.setEditor(
            "PreviewMarkdownMathJax", self.previewMarkdownMathJaxCheckBox.isChecked()
        )
        Preferences.setEditor(
            "PreviewMarkdownMermaid", self.previewMarkdownMermaidCheckBox.isChecked()
        )
        Preferences.setEditor(
            "PreviewMarkdownHTMLFormat",
            self.previewMarkdownHTMLFormatComboBox.currentText(),
        )

        Preferences.setEditor(
            "PreviewRestFileNameExtensions",
            [ext.strip() for ext in self.previewRestExtensionsEdit.text().split()],
        )
        Preferences.setEditor(
            "PreviewRestDocutilsHTMLFormat",
            self.previewRestDocutilsHTMLFormatComboBox.currentText(),
        )

        Preferences.setEditor(
            "PreviewQssFileNameExtensions",
            [ext.strip() for ext in self.previewQssExtensionsEdit.text().split()],
        )

    def __setDefaultFiltersLists(self, keepSelection=False):
        """
        Private slot to set the default file filter combo boxes.

        @param keepSelection flag indicating to keep the current selection
            if possible
        @type bool
        """
        if keepSelection:
            selectedOpenFilter = self.openFilesFilterComboBox.currentText()
            selectedSaveFilter = self.saveFilesFilterComboBox.currentText()

        openFileFiltersList = (
            Lexers.getOpenFileFiltersList(False, withAdditional=False)
            + self.openFileFilters
        )
        openFileFiltersList.sort()
        self.openFilesFilterComboBox.clear()
        self.openFilesFilterComboBox.addItems(openFileFiltersList)
        saveFileFiltersList = (
            Lexers.getSaveFileFiltersList(False, withAdditional=False)
            + self.saveFileFilters
        )
        saveFileFiltersList.sort()
        self.saveFilesFilterComboBox.clear()
        self.saveFilesFilterComboBox.addItems(saveFileFiltersList)

        if keepSelection:
            self.openFilesFilterComboBox.setCurrentIndex(
                self.openFilesFilterComboBox.findText(selectedOpenFilter)
            )
            self.saveFilesFilterComboBox.setCurrentIndex(
                self.saveFilesFilterComboBox.findText(selectedSaveFilter)
            )

    def __extractFileFilters(self):
        """
        Private method to extract the file filters.
        """
        filters = []
        for row in range(self.fileFiltersList.count()):
            filters.append(self.fileFiltersList.item(row).text())
        if self.__showsOpenFilters:
            self.openFileFilters = filters
        else:
            self.saveFileFilters = filters

    def __checkFileFilter(self, fileFilter):
        """
        Private method to check a file filter for validity.

        @param fileFilter file filter pattern to check
        @type str
        @return flag indicating validity
        @rtype bool
        """
        if not self.__showsOpenFilters and fileFilter.count("*") != 1:
            EricMessageBox.critical(
                self,
                self.tr("Add File Filter"),
                self.tr(
                    """A Save File Filter must contain exactly one"""
                    """ wildcard pattern. Yours contains {0}."""
                ).format(fileFilter.count("*")),
            )
            return False

        if fileFilter.count("*") == 0:
            EricMessageBox.critical(
                self,
                self.tr("Add File Filter"),
                self.tr(
                    """A File Filter must contain at least one"""
                    """ wildcard pattern."""
                ),
            )
            return False

        return True

    @pyqtSlot()
    def on_addFileFilterButton_clicked(self):
        """
        Private slot to add a file filter to the list.
        """
        fileFilter, ok = QInputDialog.getText(
            self,
            self.tr("Add File Filter"),
            self.tr("Enter the file filter entry:"),
            QLineEdit.EchoMode.Normal,
        )
        if ok and fileFilter and self.__checkFileFilter(fileFilter):
            self.fileFiltersList.addItem(fileFilter)
            self.__extractFileFilters()
            self.__setDefaultFiltersLists(keepSelection=True)

    @pyqtSlot()
    def on_editFileFilterButton_clicked(self):
        """
        Private slot called to edit a file filter entry.
        """
        fileFilter = self.fileFiltersList.currentItem().text()
        fileFilter, ok = QInputDialog.getText(
            self,
            self.tr("Add File Filter"),
            self.tr("Enter the file filter entry:"),
            QLineEdit.EchoMode.Normal,
            fileFilter,
        )
        if ok and fileFilter and self.__checkFileFilter(fileFilter):
            self.fileFiltersList.currentItem().setText(fileFilter)
            self.__extractFileFilters()
            self.__setDefaultFiltersLists(keepSelection=True)

    @pyqtSlot()
    def on_deleteFileFilterButton_clicked(self):
        """
        Private slot called to delete a file filter entry.
        """
        self.fileFiltersList.takeItem(self.fileFiltersList.currentRow())
        self.__extractFileFilters()
        self.__setDefaultFiltersLists(keepSelection=True)

    @pyqtSlot(bool)
    def on_openFiltersButton_toggled(self, checked):
        """
        Private slot to switch the list of file filters.

        @param checked flag indicating the check state of the button
        @type bool
        """
        self.__extractFileFilters()
        self.__showsOpenFilters = checked
        self.fileFiltersList.clear()
        if checked:
            self.fileFiltersList.addItems(self.openFileFilters)
        else:
            self.fileFiltersList.addItems(self.saveFileFilters)

    @pyqtSlot(QListWidgetItem, QListWidgetItem)
    def on_fileFiltersList_currentItemChanged(self, current, _previous):
        """
        Private slot to set the state of the edit and delete buttons.

        @param current new current item
        @type QListWidgetItem
        @param _previous previous current item (unused)
        @type QListWidgetItem
        """
        self.editFileFilterButton.setEnabled(current is not None)
        self.deleteFileFilterButton.setEnabled(current is not None)

    @pyqtSlot()
    def on_previewMarkdownPyMdownInstallPushButton_clicked(self):
        """
        Private slot to install the pymdown extensions package via pip.
        """
        pip = ericApp().getObject("Pip")
        pip.installPackages(
            ["pymdown-extensions"], interpreter=PythonUtilities.getPythonExecutable()
        )
        self.polishPage()

    def polishPage(self):
        """
        Public slot to perform some polishing actions.
        """
        self.previewMarkdownPyMdownInstallPushButton.setEnabled(
            bool(importlib.util.find_spec("pymdownx"))
        )


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = EditorFilePage()
    return page
