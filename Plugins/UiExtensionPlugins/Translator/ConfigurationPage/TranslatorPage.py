# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Time Tracker configuration page.
"""

import sys

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QListWidgetItem

from eric7.EricWidgets import EricMessageBox
from eric7.Preferences.ConfigurationPages.ConfigurationPageBase import (
    ConfigurationPageBase,
)

from .. import TranslatorEngines
from ..TranslatorLanguagesDb import TranslatorLanguagesDb
from .Ui_TranslatorPage import Ui_TranslatorPage


class TranslatorPage(ConfigurationPageBase, Ui_TranslatorPage):
    """
    Class implementing the Time Tracker configuration page.
    """

    def __init__(self, plugin):
        """
        Constructor

        @param plugin reference to the plugin object
        @type TranslatorPlugin
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("TranslatorPage")

        self.__plugin = plugin
        self.__enableLanguageWarning = True

        self.deeplLabel.setText(
            self.tr(
                """<p>A key is <b>required</b> to use this service."""
                """ <a href="{0}">Get a commercial or free API key.</a></p>"""
            ).format(TranslatorEngines.getKeyUrl("deepl"))
        )
        self.googlev2Label.setText(
            self.tr(
                """<p>A key is <b>required</b> to use this service."""
                """ <a href="{0}">Get a commercial API key.</a></p>"""
            ).format(TranslatorEngines.getKeyUrl("googlev2"))
        )
        self.ibmLabel.setText(
            self.tr(
                """<p>A key is <b>required</b> to use this service."""
                """ <a href="{0}">Register with IBM Cloud.</a></p>"""
            ).format(TranslatorEngines.getKeyUrl("ibm_watson"))
        )
        self.libreLabel.setText(
            self.tr(
                """<p>A key is <b>optional</b> to use this service and depends on the"""
                """ server configuration. Contact your server admin for details.</p>"""
            )
        )
        self.msLabel.setText(
            self.tr(
                """<p>A registration of the text translation service is"""
                """ <b>required</b>. <a href="{0}">Register with Microsoft"""
                """ Azure.</a></p>"""
            ).format(TranslatorEngines.getKeyUrl("microsoft"))
        )
        self.mymemoryLabel.setText(
            self.tr(
                """<p>A key is <b>optional</b> to use this service."""
                """ <a href="{0}">Get a free API key.</a></p>"""
            ).format(TranslatorEngines.getKeyUrl("mymemory"))
        )
        self.yandexLabel.setText(
            self.tr(
                """<p>A key is <b>required</b> to use this service."""
                """ <a href="{0}">Get a free API key.</a></p>"""
            ).format(TranslatorEngines.getKeyUrl("yandex"))
        )

        # set initial values
        enabledLanguages = self.__plugin.getPreferences("EnabledLanguages")
        languages = TranslatorLanguagesDb()
        for languageCode in languages.getAllLanguages():
            itm = QListWidgetItem()
            itm.setText(languages.getLanguage(languageCode))
            itm.setIcon(languages.getLanguageIcon(languageCode))
            itm.setData(Qt.ItemDataRole.UserRole, languageCode)
            if languageCode in enabledLanguages or not enabledLanguages:
                itm.setCheckState(Qt.CheckState.Checked)
            else:
                itm.setCheckState(Qt.CheckState.Unchecked)
            self.languagesList.addItem(itm)
        self.languagesList.sortItems()

        if "--no-multimedia" in sys.argv:
            self.pronounceCheckBox.setChecked(False)
            self.pronounceCheckBox.setEnabled(False)
        else:
            self.pronounceCheckBox.setChecked(
                self.__plugin.getPreferences("MultimediaEnabled")
            )

        # DeepL settings
        self.deeplKeyEdit.setText(self.__plugin.getPreferences("DeeplKey"))
        # Google settings
        self.dictionaryCheckBox.setChecked(
            self.__plugin.getPreferences("GoogleEnableDictionary")
        )
        self.googlev2KeyEdit.setText(self.__plugin.getPreferences("GoogleV2Key"))
        # IBM Watson settings
        self.ibmUrlEdit.setText(self.__plugin.getPreferences("IbmUrl"))
        self.ibmKeyEdit.setText(self.__plugin.getPreferences("IbmKey"))
        # LibreTranslate settings
        self.libreUrlEdit.setText(self.__plugin.getPreferences("LibreTranslateUrl"))
        self.libreKeyEdit.setText(self.__plugin.getPreferences("libreTranslateKey"))
        # Microsoft settings
        self.msSubscriptionKeyEdit.setText(
            self.__plugin.getPreferences("MsTranslatorKey")
        )
        self.msSubscriptionRegionEdit.setText(
            self.__plugin.getPreferences("MsTranslatorRegion")
        )
        # MyMemory settings
        self.mymemoryKeyEdit.setText(self.__plugin.getPreferences("MyMemoryKey"))
        self.mymemoryEmailEdit.setText(self.__plugin.getPreferences("MyMemoryEmail"))
        # Yandex settings
        self.yandexKeyEdit.setText(self.__plugin.getPreferences("YandexKey"))

    def save(self):
        """
        Public slot to save the translators configuration.
        """
        enabledLanguages = [
            itm.data(Qt.ItemDataRole.UserRole) for itm in self.__checkedLanguageItems()
        ]
        self.__plugin.setPreferences("EnabledLanguages", enabledLanguages)

        self.__plugin.setPreferences(
            "MultimediaEnabled", self.pronounceCheckBox.isChecked()
        )

        # DeepL settings
        self.__plugin.setPreferences("DeeplKey", self.deeplKeyEdit.text())
        # Google settings
        self.__plugin.setPreferences(
            "GoogleEnableDictionary", self.dictionaryCheckBox.isChecked()
        )
        self.__plugin.setPreferences("GoogleV2Key", self.googlev2KeyEdit.text())
        # IBM Watson settings
        self.__plugin.setPreferences("IbmUrl", self.ibmUrlEdit.text())
        self.__plugin.setPreferences("IbmKey", self.ibmKeyEdit.text())
        # LibreTranslate settings
        self.__plugin.setPreferences("LibreTranslateUrl", self.libreUrlEdit.text())
        self.__plugin.setPreferences("libreTranslateKey", self.libreKeyEdit.text())
        # Microsoft settings
        self.__plugin.setPreferences(
            "MsTranslatorKey", self.msSubscriptionKeyEdit.text()
        )
        self.__plugin.setPreferences(
            "MsTranslatorRegion", self.msSubscriptionRegionEdit.text()
        )
        # MyMemory settings
        self.__plugin.setPreferences("MyMemoryKey", self.mymemoryKeyEdit.text())
        # Yandex settings
        self.__plugin.setPreferences("YandexKey", self.yandexKeyEdit.text())

    def __checkedLanguageItems(self):
        """
        Private method to get a list of checked language items.

        @return list of checked language items
        @rtype list of QListWidgetItem
        """
        items = []
        for index in range(self.languagesList.count()):
            itm = self.languagesList.item(index)
            if itm.checkState() == Qt.CheckState.Checked:
                items.append(itm)

        return items

    @pyqtSlot()
    def on_setButton_clicked(self):
        """
        Private slot to set or unset all items.
        """
        self.__enableLanguageWarning = False

        unset = len(self.__checkedLanguageItems()) > 0
        for index in range(self.languagesList.count()):
            itm = self.languagesList.item(index)
            if unset:
                itm.setCheckState(Qt.CheckState.Unchecked)
            else:
                itm.setCheckState(Qt.CheckState.Checked)

        self.__enableLanguageWarning = True

    @pyqtSlot()
    def on_defaultButton_clicked(self):
        """
        Private slot to set the default languages.
        """
        self.__enableLanguageWarning = False

        defaults = self.__plugin.getPreferencesDefault("EnabledLanguages")
        for index in range(self.languagesList.count()):
            itm = self.languagesList.item(index)
            if itm.data(Qt.ItemDataRole.UserRole) in defaults:
                itm.setCheckState(Qt.CheckState.Checked)
            else:
                itm.setCheckState(Qt.CheckState.Unchecked)

        self.__enableLanguageWarning = True

    @pyqtSlot(QListWidgetItem)
    def on_languagesList_itemChanged(self, item):
        """
        Private slot to handle the selection of an item.

        @param item reference to the changed item
        @type QListWidgetItem
        """
        if self.__enableLanguageWarning and len(self.__checkedLanguageItems()) < 2:
            EricMessageBox.warning(
                self,
                self.tr("Enabled Languages"),
                self.tr(
                    """At least two languages should be selected to"""
                    """ work correctly."""
                ),
            )
