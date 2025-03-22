# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Translator plugin.
"""

import os

from PyQt6.QtCore import QCoreApplication, QObject, pyqtSignal

from eric7 import EricUtilities, Preferences
from eric7.__version__ import VersionOnly
from eric7.EricWidgets.EricApplication import ericApp
from eric7.Plugins.UiExtensionPlugins.Translator.Translator import Translator

# Start-Of-Header
__header__ = {
    "name": "Translator Plugin",
    "author": "Detlev Offenbach <detlev@die-offenbachs.de>",
    "autoactivate": True,
    "deactivateable": True,
    "version": VersionOnly,
    "className": "TranslatorPlugin",
    "packageName": "__core__",
    "shortDescription": "Translation utility using various translators.",
    "longDescription": (
        """This plug-in implements a utility to translate text using"""
        """ various online translation services."""
    ),
    "needsRestart": False,
    "pyqtApi": 2,
}
# End-Of-Header

error = ""  # noqa: U200

translatorPluginObject = None


def createTranslatorPage(_configDlg):
    """
    Module function to create the Translator configuration page.

    @param _configDlg reference to the configuration dialog (unused)
    @type ConfigurationWidget
    @return reference to the configuration page
    @rtype TranslatorPage
    """
    from eric7.Plugins.UiExtensionPlugins.Translator.ConfigurationPage import (
        TranslatorPage,
    )

    page = TranslatorPage.TranslatorPage(translatorPluginObject)
    return page


def getConfigData():
    """
    Module function returning data as required by the configuration dialog.

    @return dictionary containing the relevant data
    @rtype dict
    """
    icon = (
        os.path.join("UiExtensionPlugins", "Translator", "icons", "flag-dark")
        if ericApp().usesDarkPalette()
        else os.path.join("UiExtensionPlugins", "Translator", "icons", "flag-light")
    )
    return {
        "translatorPage": [
            QCoreApplication.translate("TranslatorPlugin", "Translator"),
            icon,
            createTranslatorPage,
            None,
            None,
        ],
    }


def prepareUninstall():
    """
    Module function to prepare for an uninstallation.
    """
    Preferences.getSettings().remove(TranslatorPlugin.PreferencesKey)


class TranslatorPlugin(QObject):
    """
    Class implementing the Translator plug-in.

    @signal updateLanguages() emitted to indicate a languages update
    """

    PreferencesKey = "Translator"

    updateLanguages = pyqtSignal()

    def __init__(self, ui):
        """
        Constructor

        @param ui reference to the user interface object
        @type UI.UserInterface
        """
        super().__init__(ui)
        self.__ui = ui
        self.__initialize()

        self.__defaults = {
            "OriginalLanguage": "en",
            "TranslationLanguage": "de",
            "SelectedEngine": "deepl",
            "EnabledLanguages": [
                "en",
                "de",
                "fr",
                "cs",
                "es",
                "pt",
                "ru",
                "tr",
                "zh-CN",
                "zh-TW",
            ],
            "MultimediaEnabled": False,
            # service specific settings below
            # DeepL
            "DeeplKey": "",
            # Google V1
            "GoogleEnableDictionary": False,
            # Google V2
            "GoogleV2Key": "",
            # IBM Watson
            "IbmUrl": "",
            "IbmKey": "",
            # LibreTranslate
            "LibreTranslateUrl": "http://localhost:5000",
            "libreTranslateKey": "",
            # Microsoft
            "MsTranslatorKey": "",
            "MsTranslatorRegion": "",
            # MyMemory
            "MyMemoryKey": "",
            "MyMemoryEmail": "",
            # Yandex
            "YandexKey": "",
        }

    def __initialize(self):
        """
        Private slot to (re)initialize the plugin.
        """
        self.__object = None

    def activate(self):
        """
        Public method to activate this plugin.

        @return tuple of None and activation status
        @rtype tuple of (None, bool)
        """
        global error
        error = ""  # clear previous error

        global translatorPluginObject
        translatorPluginObject = self

        self.__object = Translator(self, ericApp().usesDarkPalette(), self.__ui)
        self.__object.activate()
        ericApp().registerPluginObject("Translator", self.__object)

        return None, True

    def deactivate(self):
        """
        Public method to deactivate this plugin.
        """
        ericApp().unregisterPluginObject("Translator")
        self.__object.deactivate()

        self.__initialize()

    def getPreferencesDefault(self, key):
        """
        Public method to retrieve the various default settings.

        @param key the key of the value to get
        @type str
        @return the requested setting
        @rtype Any
        """
        return self.__defaults[key]

    def getPreferences(self, key):
        """
        Public method to retrieve the various settings.

        @param key the key of the value to get
        @type str
        @return the requested setting
        @rtype Any
        """
        if key in ("EnabledLanguages"):
            return EricUtilities.toList(
                Preferences.getSettings().value(
                    self.PreferencesKey + "/" + key, self.__defaults[key]
                )
            )
        elif key in ("GoogleEnableDictionary", "MultimediaEnabled"):
            return EricUtilities.toBool(
                Preferences.getSettings().value(
                    self.PreferencesKey + "/" + key, self.__defaults[key]
                )
            )
        else:
            return Preferences.getSettings().value(
                self.PreferencesKey + "/" + key, self.__defaults[key]
            )

    def setPreferences(self, key, value):
        """
        Public method to store the various settings.

        @param key the key of the setting to be set
        @type str
        @param value the value to be set
        @type Any
        """
        Preferences.getSettings().setValue(self.PreferencesKey + "/" + key, value)

        if key in ["EnabledLanguages"]:
            self.updateLanguages.emit()
