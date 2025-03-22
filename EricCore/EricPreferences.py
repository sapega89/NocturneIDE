# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the preferences for the eric library.
"""

import sys

from PyQt6.QtCore import QCoreApplication, QDir, QSettings

from eric7 import EricUtilities
from eric7.EricNetwork.EricFtp import EricFtpProxyType
from eric7.EricUtilities.crypto import pwConvert

# names of the various settings objects
settingsNameOrganization = "Eric7"
settingsNameGlobal = "eric7-lib"


class EricPreferences:
    """
    A class to hold all configuration items.
    """

    # defaults for network proxy settings
    proxyDefaults = {
        "UseProxy": False,
        "UseSystemProxy": True,
        "UseHttpProxyForAll": False,
        "ProxyHost/Http": "",
        "ProxyHost/Https": "",
        "ProxyHost/Ftp": "",
        "ProxyPort/Http": 80,
        "ProxyPort/Https": 443,
        "ProxyPort/Ftp": 21,
        "ProxyUser/Http": "",
        "ProxyUser/Https": "",
        "ProxyUser/Ftp": "",
        "ProxyPassword/Http": "",
        "ProxyPassword/Https": "",
        "ProxyPassword/Ftp": "",
        "ProxyType/Ftp": EricFtpProxyType.NO_PROXY,
        "ProxyAccount/Ftp": "",
        "ProxyExceptions": "localhost,127.0.0.,::1",
    }


################################################################################
## Functions dealing with the preferences class.
################################################################################


def initPreferences():
    """
    Function to initialize the central configuration store.
    """
    EricPreferences.settings = QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        settingsNameOrganization,
        settingsNameGlobal,
        QCoreApplication.instance(),
    )
    if not sys.platform.startswith(("win", "cygwin")):
        hp = QDir.homePath()
        dn = QDir(hp)
        dn.mkdir(".eric7")

    EricPreferences.settings.value("NetworkProxy/ProxyExceptions")


def syncPreferences():
    """
    Module function to sync the preferences to disk.

    In addition to syncing, the central configuration store is reinitialized
    as well.
    """
    EricPreferences.settings.sync()


################################################################################
## Functions dealing with the preferences categories.
################################################################################


def getNetworkProxy(key):
    """
    Function to retrieve the various Network Proxy related settings.

    @param key the key of the value to get
    @type str
    @return the requested network proxy setting
    @rtype Any
    """
    if key in (
        "UseProxy",
        "UseSystemProxy",
        "UseHttpProxyForAll",
    ):
        return EricUtilities.toBool(
            EricPreferences.settings.value(
                "NetworkProxy/" + key, EricPreferences.proxyDefaults[key]
            )
        )

    elif key in (
        "ProxyPort/Http",
        "ProxyPort/Https",
        "ProxyPort/Ftp",
    ):
        return int(
            EricPreferences.settings.value(
                "NetworkProxy/" + key, EricPreferences.proxyDefaults[key]
            )
        )

    elif key in ("ProxyType/Ftp",):
        return EricFtpProxyType(
            int(
                EricPreferences.settings.value(
                    "NetworkProxy/" + key, EricPreferences.proxyDefaults[key].value
                )
            )
        )

    elif key in (
        "ProxyPassword/Http",
        "ProxyPassword/Https",
        "ProxyPassword/Ftp",
    ):
        return pwConvert(
            EricPreferences.settings.value(
                "NetworkProxy/" + key, EricPreferences.proxyDefaults[key]
            ),
            encode=False,
        )

    else:
        return EricPreferences.settings.value(
            "NetworkProxy/" + key, EricPreferences.proxyDefaults[key]
        )


def setNetworkProxy(key, value):
    """
    Function to store the various Network Proxy settings.

    @param key the key of the setting to be set
    @type str
    @param value the value to be set
    @type Any
    """
    if key in (
        "ProxyPassword/Http",
        "ProxyPassword/Https",
        "ProxyPassword/Ftp",
    ):
        EricPreferences.settings.setValue(
            "NetworkProxy/" + key, pwConvert(value, encode=True)
        )
    elif key in ("ProxyType/Ftp",):
        # value is an enum.Enum derived item
        EricPreferences.settings.setValue("NetworkProxy/" + key, value.value)
    else:
        EricPreferences.settings.setValue("NetworkProxy/" + key, value)


################################################################################
## Functions dealing with passwords.
################################################################################


def convertPasswords(oldPassword, newPassword):
    """
    Module function to convert all passwords.

    @param oldPassword current password
    @type str
    @param newPassword new password
    @type str
    """
    from eric7.EricUtilities.crypto import pwRecode

    for key in [
        "ProxyPassword/Http",
        "ProxyPassword/Https",
        "ProxyPassword/Ftp",
    ]:
        EricPreferences.settings.setValue(
            "NetworkProxy/" + key,
            pwRecode(
                EricPreferences.settings.value(
                    "NetworkProxy/" + key, EricPreferences.proxyDefaults[key]
                ),
                oldPassword,
                newPassword,
            ),
        )
