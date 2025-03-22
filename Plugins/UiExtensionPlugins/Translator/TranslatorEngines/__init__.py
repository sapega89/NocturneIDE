# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package containing the various translation engines.
"""

import contextlib
import importlib
import os

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QIcon

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp


def supportedEngineNames():
    """
    Module function to get the list of supported translation engines.

    @return names of supported engines
    @rtype list of str
    """
    return [
        "deepl",
        "googlev1",
        "googlev2",
        "ibm_watson",
        "libre_translate",
        "microsoft",
        "mymemory",
        "yandex",
    ]


def engineDisplayName(name):
    """
    Module function to get a translated name for an engine.

    @param name name of a translation engine
    @type str
    @return translated engine name
    @rtype str
    """
    return {
        "deepl": QCoreApplication.translate("TranslatorEngines", "DeepL"),
        "googlev1": QCoreApplication.translate("TranslatorEngines", "Google V.1"),
        "googlev2": QCoreApplication.translate("TranslatorEngines", "Google V.2"),
        "ibm_watson": QCoreApplication.translate("TranslatorEngines", "IBM Watson"),
        "libre_translate": QCoreApplication.translate(
            "TranslatorEngines", "LibreTranslate"
        ),
        "microsoft": QCoreApplication.translate("TranslatorEngines", "Microsoft"),
        "mymemory": QCoreApplication.translate("TranslatorEngines", "MyMemory"),
        "yandex": QCoreApplication.translate("TranslatorEngines", "Yandex"),
    }.get(
        name,
        QCoreApplication.translate(
            "TranslatorEngines", "Unknow translation service name ({0})"
        ).format(name),
    )


def getTranslationEngine(name, plugin, parent=None):
    """
    Module function to instantiate an engine object for the named service.

    @param name name of the online translation service
    @type str
    @param plugin reference to the plugin object
    @type TranslatorPlugin
    @param parent reference to the parent object
    @type QObject
    @return translation engine
    @rtype TranslatorEngine
    """
    engineMapping = {
        "deepl": ".DeepLEngine",
        "googlev1": ".GoogleV1Engine",
        "googlev2": ".GoogleV2Engine",
        "ibm_watson": ".IbmWatsonEngine",
        "libre_translate": ".LibreTranslateEngine",
        "microsoft": ".MicrosoftEngine",
        "mymemory": ".MyMemoryEngine",
        "yandex": ".YandexEngine",
    }

    with contextlib.suppress(KeyError):
        mod = importlib.import_module(engineMapping[name], __package__)
        if mod:
            return mod.createEngine(plugin, parent)

    return None


def getEngineIcon(name):
    """
    Module function to get the icon of the named engine.

    @param name name of the translation engine
    @type str
    @return engine icon
    @rtype QIcon
    """
    iconSuffix = "dark" if ericApp().usesDarkPalette() else "light"
    if name in supportedEngineNames():
        icon = EricPixmapCache.getIcon(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "icons",
                "engines",
                "{0}-{1}".format(name, iconSuffix),
            )
        )
        if icon.isNull():
            # try variant without suffix
            icon = EricPixmapCache.getIcon(
                os.path.join(
                    os.path.dirname(__file__),
                    "..",
                    "icons",
                    "engines",
                    "{0}".format(name),
                )
            )
        return icon
    else:
        return QIcon()


def getKeyUrl(name):
    """
    Module function to get an URL to request a user key.

    @param name name of the online translation service
    @type str
    @return key request URL
    @rtype str
    """
    return {
        "deepl": "https://www.deepl.com/de/pro-api",
        "googlev2": "https://console.developers.google.com/",
        "ibm_watson": "https://www.ibm.com/watson/services/language-translator/",
        "microsoft": "https://portal.azure.com",
        "mymemory": "http://mymemory.translated.net/doc/keygen.php",
        "yandex": "http://api.yandex.com/key/form.xml?service=trnsl",
    }.get(name, "")
