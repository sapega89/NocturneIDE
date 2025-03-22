# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Ethernet related functionality.
"""

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QDialog, QMenu

from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox


class EthernetController(QObject):
    """
    Class implementing the Ethernet related functionality.
    """

    def __init__(self, microPython, parent=None):
        """
        Constructor

        @param microPython reference to the MicroPython widget
        @type MicroPythonWidgep
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

        self.__mpy = microPython

    def createMenu(self, menu):
        """
        Public method to create the Ethernet submenu.

        @param menu reference to the parent menu
        @type QMenu
        @return reference to the created menu
        @rtype QMenu
        """
        ethernetMenu = QMenu(self.tr("Ethernet Functions"), menu)
        ethernetMenu.setTearOffEnabled(True)
        ethernetMenu.addAction(
            self.tr("Show Ethernet Status"), self.__showEthernetStatus
        )
        ethernetMenu.addSeparator()
        ethernetMenu.addAction(self.tr("Connect to LAN (DHCP)"), self.__connectLanDhcp)
        ethernetMenu.addAction(
            self.tr("Connect to LAN (fixed IP)"), self.__connectLanIp
        )
        ethernetMenu.addAction(
            self.tr("Check Internet Connection"), self.__checkInternet
        )
        ethernetMenu.addAction(self.tr("Disconnect from LAN"), self.__disconnectLan)
        ethernetMenu.addSeparator()
        ethernetMenu.addAction(
            self.tr("Write Auto-Connect Script"), self.__writeAutoConnect
        )
        ethernetMenu.addAction(
            self.tr("Remove Auto-Connect Script"), self.__removeAutoConnect
        )
        ethernetMenu.addSeparator()
        ethernetMenu.addAction(
            self.tr("Deactivate Ethernet Interface"), self.__deactivateEthernet
        )
        ethernetMenu.addSeparator()
        ethernetMenu.addAction(self.tr("Set Network Time"), self.__setNetworkTime)

        # add device specific entries (if there are any)
        self.__mpy.getDevice().addDeviceEthernetEntries(ethernetMenu)

        return ethernetMenu

    @pyqtSlot()
    def __showEthernetStatus(self):
        """
        Private slot to show a dialog with the WiFi status of the current device.
        """
        from .EthernetStatusDialog import EthernetStatusDialog

        try:
            with EricOverrideCursor():
                status = self.__mpy.getDevice().getEthernetStatus()
                # status is a list of user labels and associated values

            dlg = EthernetStatusDialog(status, parent=self.__mpy)
            dlg.exec()
        except Exception as exc:
            self.__mpy.showError("getEthernetStatus()", str(exc))

    @pyqtSlot()
    def __connectLanDhcp(self):
        """
        Private slot to connect to the LAN with a dynamic IPv4 address (DHCP mode).
        """
        from .HostnameDialog import HostnameDialog

        dlg = HostnameDialog(parent=self.__mpy)
        hostname = (
            dlg.getHostname() if dlg.exec() == QDialog.DialogCode.Accepted else ""
        )
        self.__connectLan("dhcp", hostname)

    @pyqtSlot()
    def __connectLanIp(self):
        """
        Private slot to connect to the LAN with a fixed IPv4 address (fixed address
        mode).
        """
        from .IPv4AddressDialog import IPv4AddressDialog

        dlg = IPv4AddressDialog(withDhcp=False, parent=self.__mpy)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ifconfig, hostname = dlg.getIPv4Address()
            self.__connectLan(ifconfig, hostname)

    def __connectLan(self, config, hostname):
        """
        Private method to connect the connected device to the LAN.

        @param config configuration for the connection (either the string 'dhcp'
            for a dynamic address or a tuple of four strings with the IPv4 parameters.
        @type str of tuple of (str, str, str, str)
        @param hostname host name of the device
        @type str
        """
        success, error = self.__mpy.getDevice().connectToLan(config, hostname)
        if success:
            EricMessageBox.information(
                None,
                self.tr("Connect to LAN"),
                self.tr("<p>The device was connected to the LAN successfully.</p>"),
            )
        else:
            EricMessageBox.critical(
                None,
                self.tr("Connect to LAN"),
                self.tr(
                    "<p>The device could not connect to the LAN.</p><p>Reason: {0}</p>"
                ).format(error if error else self.tr("unknown")),
            )

    @pyqtSlot()
    def __disconnectLan(self):
        """
        Private slot to disconnect from the LAN.
        """
        success, error = self.__mpy.getDevice().disconnectFromLan()
        if success:
            EricMessageBox.information(
                None,
                self.tr("Disconnect from LAN"),
                self.tr("<p>The device was disconnected from the LAN.</p>"),
            )
        else:
            EricMessageBox.critical(
                None,
                self.tr("Disconnect from LAN"),
                self.tr(
                    "<p>The device could not be disconnected from the LAN.</p>"
                    "<p>Reason: {0}</p>"
                ).format(error if error else self.tr("unknown")),
            )

    @pyqtSlot()
    def __checkInternet(self):
        """
        Private slot to check the availability of an internet connection.
        """
        with EricOverrideCursor():
            success, error = self.__mpy.getDevice().checkInternetViaLan()
        if not error:
            msg = (
                self.tr("<p>The internet connection is <b>available</b>.</p>")
                if success
                else self.tr("<p>The internet connection is <b>not available</b>.</p>")
            )
            EricMessageBox.information(
                None,
                self.tr("Check Internet Connection"),
                msg,
            )
        else:
            EricMessageBox.critical(
                None,
                self.tr("Check Internet Connection"),
                self.tr(
                    "<p>The internet is not available.</p><p>Reason: {0}</p>"
                ).format(error if error else self.tr("unknown")),
            )

    @pyqtSlot()
    def __writeAutoConnect(self):
        """
        Private slot to generate a script and associated configuration to connect the
        device during boot time.

        This will also modify the boot script to perform the automatic connection.
        """
        from .IPv4AddressDialog import IPv4AddressDialog

        dlg = IPv4AddressDialog(withDhcp=True, parent=self.__mpy)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ifconfig, hostname = dlg.getIPv4Address()
            ok, err = self.__mpy.getDevice().writeLanAutoConnect(ifconfig, hostname)
            if ok:
                if self.__mpy.getDevice().hasCircuitPython():
                    # CircuitPython will reset for the REPL, so no auto-connect
                    # available.
                    EricMessageBox.information(
                        None,
                        self.tr("Write Auto-Connect Script"),
                        self.tr(
                            "<p>The auto-connect script and associated configuration"
                            " was saved on the device. Use the script like this:</p>"
                            "<p>import wiznet_connect<br/>"
                            "nic = wiznet_connect.connect_lan()</p>"
                        ),
                    )
                else:
                    EricMessageBox.information(
                        None,
                        self.tr("Write Auto-Connect Script"),
                        self.tr(
                            "<p>The auto-connect script and associated configuration"
                            " was saved on the device. The device will connect to the"
                            " LAN at boot time.</p>"
                        ),
                    )
            else:
                EricMessageBox.critical(
                    None,
                    self.tr("Write Auto-Connect Script"),
                    self.tr(
                        "<p>The auto-connect script and associated configuration could"
                        " not be saved on the device.</p><p>Reason: {0}</p>"
                    ).format(err if err else self.tr("unknown")),
                )

    @pyqtSlot()
    def __removeAutoConnect(self):
        """
        Private slot to remove the boot time connect capability.

        This will not remove the auto-connect part of the boot script. This needs to be
        done manually if desired.
        """
        ok = EricMessageBox.yesNo(
            None,
            self.tr("Remove Auto-Connect Script"),
            self.tr(
                "Shall the saved IPv4 parameters really be removed from the connected"
                " device?"
            ),
        )
        if ok:
            ok, err = self.__mpy.getDevice().removeLanAutoConnect()
            if ok:
                if self.__mpy.getDevice().hasCircuitPython():
                    EricMessageBox.information(
                        None,
                        self.tr("Remove Auto-Connect Script"),
                        self.tr(
                            "<p>The IPv4 parameters were removed from the device.</p>"
                        ),
                    )
                else:
                    EricMessageBox.information(
                        None,
                        self.tr("Remove Auto-Connect Script"),
                        self.tr(
                            "<p>The IPv4 parameters were removed from the device. The"
                            " device will not connect to the LAN at boot time anymore."
                            "</p>"
                        ),
                    )
            else:
                EricMessageBox.critical(
                    None,
                    self.tr("Remove Auto-Connect Script"),
                    self.tr(
                        "<p>The IPv4 parameters could not be removed from the device."
                        "</p><p>Reason: {0}</p>"
                    ).format(err if err else self.tr("unknown")),
                )

    @pyqtSlot()
    def __deactivateEthernet(self):
        """
        Private slot to deactivate the Ethernet interface.
        """
        ok, err = self.__mpy.getDevice().deactivateEthernet()
        if ok:
            EricMessageBox.information(
                None,
                self.tr("Deactivate Ethernet Interface"),
                self.tr("The Ethernet interface was deactivated successfully."),
            )
        else:
            msg = self.tr("<p>The Ethernet interface could not be deactivated.</p>")
            if err:
                msg += self.tr("<p>Reason: {0}</p>").format(err)
            EricMessageBox.critical(
                None,
                self.tr("Deactivate Ethernet Interface"),
                msg,
            )

    @pyqtSlot()
    def __setNetworkTime(self):
        """
        Private slot to synchronize the device clock to network time.
        """
        from ..NtpParametersDialog import NtpParametersDialog

        device = self.__mpy.getDevice()
        if not device.hasNetworkTime():
            if device.hasCircuitPython():
                if device.getDeviceData("ethernet"):
                    moduleName = "adafruit_wiznet5k"
                else:
                    moduleName = "adafruit_ntp"
                EricMessageBox.warning(
                    None,
                    self.tr("Set Network Time"),
                    self.tr(
                        "<p>The device does not support network time synchronization."
                        " The module <b>{0}</b> is not installed.</p>"
                    ).format(moduleName),
                )
            else:
                EricMessageBox.critical(
                    None,
                    self.tr("Set Network Time"),
                    self.tr(
                        "<p>The device does not support network time synchronization."
                        " The module <b>ntptime</b> is not available.</p>"
                    ),
                )
            return

        dlg = NtpParametersDialog(parent=self.__mpy)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            server, tzOffset, isDst, timeout = dlg.getParameters()
            if isDst:
                tzOffset += 1

            ok, err = self.__mpy.getDevice().setNetworkTime(
                server=server, tzOffset=tzOffset, timeout=timeout
            )
            if ok:
                EricMessageBox.information(
                    None,
                    self.tr("Set Network Time"),
                    self.tr("The device time was synchronized successfully."),
                )
            else:
                if err:
                    msg = self.tr(
                        "<p>The device time could not be synchronized.</p>"
                        "<p>Reason: {0}</p>"
                    ).format(err)
                else:
                    msg = self.tr(
                        "<p>The device time could not be synchronized. Is the device"
                        " connected to a LAN?</p>"
                    )
                EricMessageBox.critical(
                    None,
                    self.tr("Set Network Time"),
                    msg,
                )
