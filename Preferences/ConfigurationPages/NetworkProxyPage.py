# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Network configuration page.
"""

from PyQt6.QtCore import pyqtSlot

from eric7.EricCore import EricPreferences
from eric7.EricNetwork.EricFtp import EricFtpProxyType

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_NetworkProxyPage import Ui_NetworkProxyPage


class NetworkProxyPage(ConfigurationPageBase, Ui_NetworkProxyPage):
    """
    Class implementing the Network configuration page.
    """

    def __init__(self, configDialog):
        """
        Constructor

        @param configDialog reference to the configuration dialog
        @type ConfigurationDialog
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("NetworkProxyPage")

        self.__configDlg = configDialog

        self.ftpProxyTypeCombo.addItem(
            self.tr("No FTP Proxy"), EricFtpProxyType.NO_PROXY.value
        )
        self.ftpProxyTypeCombo.addItem(
            self.tr("No Proxy Authentication required"),
            EricFtpProxyType.NON_AUTHORIZING.value,
        )
        self.ftpProxyTypeCombo.addItem(
            self.tr("User@Server"), EricFtpProxyType.USER_SERVER.value
        )
        self.ftpProxyTypeCombo.addItem(self.tr("SITE"), EricFtpProxyType.SITE.value)
        self.ftpProxyTypeCombo.addItem(self.tr("OPEN"), EricFtpProxyType.OPEN.value)
        self.ftpProxyTypeCombo.addItem(
            self.tr("User@Proxyuser@Server"),
            EricFtpProxyType.USER_PROXYUSER_SERVER.value,
        )
        self.ftpProxyTypeCombo.addItem(
            self.tr("Proxyuser@Server"), EricFtpProxyType.PROXYUSER_SERVER.value
        )
        self.ftpProxyTypeCombo.addItem(
            self.tr("AUTH and RESP"), EricFtpProxyType.AUTH_RESP.value
        )
        self.ftpProxyTypeCombo.addItem(
            self.tr("Bluecoat Proxy"), EricFtpProxyType.BLUECOAT.value
        )

        # set initial values

        # HTTP proxy
        self.httpProxyHostEdit.setText(
            EricPreferences.getNetworkProxy("ProxyHost/Http")
        )
        self.httpProxyPortSpin.setValue(
            EricPreferences.getNetworkProxy("ProxyPort/Http")
        )

        # HTTPS proxy
        self.httpsProxyHostEdit.setText(
            EricPreferences.getNetworkProxy("ProxyHost/Https")
        )
        self.httpsProxyPortSpin.setValue(
            EricPreferences.getNetworkProxy("ProxyPort/Https")
        )

        # FTP proxy
        self.ftpProxyHostEdit.setText(EricPreferences.getNetworkProxy("ProxyHost/Ftp"))
        self.ftpProxyPortSpin.setValue(EricPreferences.getNetworkProxy("ProxyPort/Ftp"))
        self.ftpProxyTypeCombo.setCurrentIndex(
            self.ftpProxyTypeCombo.findData(
                EricPreferences.getNetworkProxy("ProxyType/Ftp").value
            )
        )
        self.ftpProxyUserEdit.setText(EricPreferences.getNetworkProxy("ProxyUser/Ftp"))
        self.ftpProxyPasswordEdit.setText(
            EricPreferences.getNetworkProxy("ProxyPassword/Ftp")
        )
        self.ftpProxyAccountEdit.setText(
            EricPreferences.getNetworkProxy("ProxyAccount/Ftp")
        )

        self.httpProxyForAllCheckBox.setChecked(
            EricPreferences.getNetworkProxy("UseHttpProxyForAll")
        )
        if not EricPreferences.getNetworkProxy("UseProxy"):
            self.noProxyButton.setChecked(True)
        elif EricPreferences.getNetworkProxy("UseSystemProxy"):
            self.systemProxyButton.setChecked(True)
        else:
            self.manualProxyButton.setChecked(True)

        self.exceptionsEdit.setText(
            ", ".join(EricPreferences.getNetworkProxy("ProxyExceptions").split(","))
        )

    def save(self):
        """
        Public slot to save the Networj configuration.
        """
        EricPreferences.setNetworkProxy("UseProxy", not self.noProxyButton.isChecked())
        EricPreferences.setNetworkProxy(
            "UseSystemProxy", self.systemProxyButton.isChecked()
        )
        EricPreferences.setNetworkProxy(
            "UseHttpProxyForAll", self.httpProxyForAllCheckBox.isChecked()
        )

        EricPreferences.setNetworkProxy(
            "ProxyExceptions",
            ",".join([h.strip() for h in self.exceptionsEdit.text().split(",")]),
        )

        # HTTP proxy
        EricPreferences.setNetworkProxy("ProxyHost/Http", self.httpProxyHostEdit.text())
        EricPreferences.setNetworkProxy(
            "ProxyPort/Http", self.httpProxyPortSpin.value()
        )

        # HTTPS proxy
        EricPreferences.setNetworkProxy(
            "ProxyHost/Https", self.httpsProxyHostEdit.text()
        )
        EricPreferences.setNetworkProxy(
            "ProxyPort/Https", self.httpsProxyPortSpin.value()
        )

        # FTP proxy
        EricPreferences.setNetworkProxy("ProxyHost/Ftp", self.ftpProxyHostEdit.text())
        EricPreferences.setNetworkProxy("ProxyPort/Ftp", self.ftpProxyPortSpin.value())
        EricPreferences.setNetworkProxy(
            "ProxyType/Ftp", EricFtpProxyType(self.ftpProxyTypeCombo.currentData())
        )
        EricPreferences.setNetworkProxy("ProxyUser/Ftp", self.ftpProxyUserEdit.text())
        EricPreferences.setNetworkProxy(
            "ProxyPassword/Ftp", self.ftpProxyPasswordEdit.text()
        )
        EricPreferences.setNetworkProxy(
            "ProxyAccount/Ftp", self.ftpProxyAccountEdit.text()
        )

    @pyqtSlot()
    def on_clearProxyPasswordsButton_clicked(self):
        """
        Private slot to clear the saved HTTP(S) proxy passwords.
        """
        EricPreferences.setNetworkProxy("ProxyPassword/Http", "")
        EricPreferences.setNetworkProxy("ProxyPassword/Https", "")

    @pyqtSlot(int)
    def on_ftpProxyTypeCombo_currentIndexChanged(self, index):
        """
        Private slot handling the selection of a proxy type.

        @param index index of the selected item
        @type int
        """
        proxyType = EricFtpProxyType(self.ftpProxyTypeCombo.itemData(index))
        self.ftpProxyHostEdit.setEnabled(proxyType != EricFtpProxyType.NO_PROXY)
        self.ftpProxyPortSpin.setEnabled(proxyType != EricFtpProxyType.NO_PROXY)
        self.ftpProxyUserEdit.setEnabled(
            proxyType
            not in [EricFtpProxyType.NO_PROXY, EricFtpProxyType.NON_AUTHORIZING]
        )
        self.ftpProxyPasswordEdit.setEnabled(
            proxyType
            not in [EricFtpProxyType.NO_PROXY, EricFtpProxyType.NON_AUTHORIZING]
        )
        self.ftpProxyAccountEdit.setEnabled(
            proxyType
            not in [EricFtpProxyType.NO_PROXY, EricFtpProxyType.NON_AUTHORIZING]
        )


def create(dlg):
    """
    Module function to create the configuration page.

    @param dlg reference to the configuration dialog
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = NetworkProxyPage(dlg)
    return page
