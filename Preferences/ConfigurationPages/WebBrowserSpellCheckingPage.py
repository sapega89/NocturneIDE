# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Web Browser Spell Checking configuration page.
"""

import contextlib
import os

from PyQt6.QtCore import QCoreApplication, QDir, QLibraryInfo, QLocale, Qt, pyqtSlot
from PyQt6.QtWidgets import QListWidgetItem

from eric7 import Preferences
from eric7.SystemUtilities import OSUtilities

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_WebBrowserSpellCheckingPage import Ui_WebBrowserSpellCheckingPage


class WebBrowserSpellCheckingPage(
    ConfigurationPageBase, Ui_WebBrowserSpellCheckingPage
):
    """
    Class implementing the Web Browser Spell Checking page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("WebBrowserSpellCheckingPage")

        # set initial values
        self.spellCheckEnabledCheckBox.setChecked(
            Preferences.getWebBrowser("SpellCheckEnabled")
        )
        self.on_spellCheckEnabledCheckBox_clicked()
        self.unencryptedCheckBox.setChecked(
            Preferences.getWebBrowser("ForceHttpDictionaryDownload")
        )

        if OSUtilities.isMacPlatform():
            self.__dictionaryDirectories = {
                QDir.cleanPath(
                    QCoreApplication.applicationDirPath()
                    + "/../Resources/qtwebengine_dictionaries"
                ),
                QDir.cleanPath(
                    QCoreApplication.applicationDirPath()
                    + "/../Frameworks/QtWebEngineCore.framework"
                    "/Resources/qtwebengine_dictionaries"
                ),
            }
        else:
            self.__dictionaryDirectories = {
                QDir.cleanPath(
                    QCoreApplication.applicationDirPath() + "/qtwebengine_dictionaries"
                ),
                QDir.cleanPath(
                    QLibraryInfo.path(QLibraryInfo.LibraryPath.DataPath)
                    + "/qtwebengine_dictionaries"
                ),
            }
        self.spellCheckDictionaryDirectoriesEdit.setPlainText(
            "\n".join(self.__dictionaryDirectories)
        )
        # try to create these directories, if they don't exist
        for directory in self.__dictionaryDirectories:
            if not os.path.exists(directory):
                with contextlib.suppress(os.error):
                    os.makedirs(directory)

        self.__writeableDirectories = []
        for directory in self.__dictionaryDirectories:
            if os.access(directory, os.W_OK):
                self.__writeableDirectories.append(directory)
        self.manageDictionariesButton.setEnabled(bool(self.__writeableDirectories))

        self.__populateDictionariesList()

    def __populateDictionariesList(self):
        """
        Private method to populate the spell checking dictionaries list.
        """
        self.spellCheckLanguagesList.clear()

        for path in self.__dictionaryDirectories:
            directory = QDir(path)
            fileNames = directory.entryList(["*.bdic"])
            for fileName in fileNames:
                lang = fileName[:-5]
                langStr = self.__createLanguageString(lang)
                if self.spellCheckLanguagesList.findItems(
                    langStr, Qt.MatchFlag.MatchExactly
                ):
                    continue

                itm = QListWidgetItem(langStr, self.spellCheckLanguagesList)
                itm.setData(Qt.ItemDataRole.UserRole, lang)
                itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                itm.setCheckState(Qt.CheckState.Unchecked)
        self.spellCheckLanguagesList.sortItems(Qt.SortOrder.AscendingOrder)

        spellCheckLanguages = Preferences.getWebBrowser("SpellCheckLanguages")
        topIndex = 0
        for lang in spellCheckLanguages:
            items = self.spellCheckLanguagesList.findItems(
                self.__createLanguageString(lang), Qt.MatchFlag.MatchExactly
            )
            if items:
                itm = items[0]
                self.spellCheckLanguagesList.takeItem(
                    self.spellCheckLanguagesList.row(itm)
                )
                self.spellCheckLanguagesList.insertItem(topIndex, itm)
                itm.setCheckState(Qt.CheckState.Checked)
                topIndex += 1

        if self.spellCheckLanguagesList.count():
            self.noLanguagesLabel.hide()
            self.spellCheckLanguagesList.show()
        else:
            # no dictionaries available, disable spell checking
            self.noLanguagesLabel.show()
            self.spellCheckLanguagesList.hide()
            self.spellCheckEnabledCheckBox.setChecked(False)

    def save(self):
        """
        Public slot to save the Help Viewers configuration.
        """
        languages = []
        for row in range(self.spellCheckLanguagesList.count()):
            itm = self.spellCheckLanguagesList.item(row)
            if itm.checkState() == Qt.CheckState.Checked:
                languages.append(itm.data(Qt.ItemDataRole.UserRole))

        Preferences.setWebBrowser(
            "SpellCheckEnabled", self.spellCheckEnabledCheckBox.isChecked()
        )
        Preferences.setWebBrowser(
            "ForceHttpDictionaryDownload", self.unencryptedCheckBox.isChecked()
        )
        Preferences.setWebBrowser("SpellCheckLanguages", languages)

    @pyqtSlot()
    def on_spellCheckEnabledCheckBox_clicked(self):
        """
        Private slot handling a change of the spell checking enabled state.
        """
        enable = self.spellCheckEnabledCheckBox.isChecked()
        self.noLanguagesLabel.setEnabled(enable)
        self.spellCheckLanguagesList.setEnabled(enable)

    def __createLanguageString(self, language):
        """
        Private method to create a language string given a language identifier.

        @param language language identifier
        @type str
        @return language string
        @rtype str
        """
        loc = QLocale(language)

        if loc.language() == QLocale.Language.C:
            return language

        country = QLocale.countryToString(loc.country())
        lang = QLocale.languageToString(loc.language())
        languageString = "{0}/{1} [{2}]".format(lang, country, language)
        return languageString

    @pyqtSlot()
    def on_manageDictionariesButton_clicked(self):
        """
        Private slot to manage spell checking dictionaries.
        """
        from eric7.WebBrowser.SpellCheck.ManageDictionariesDialog import (
            ManageDictionariesDialog,
        )

        dlg = ManageDictionariesDialog(
            self.__writeableDirectories,
            enforceUnencryptedDownloads=self.unencryptedCheckBox.isChecked(),
            parent=self,
        )
        dlg.exec()

        self.__populateDictionariesList()


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = WebBrowserSpellCheckingPage()
    return page
