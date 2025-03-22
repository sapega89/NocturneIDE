# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the WiFi related functionality.
"""

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QDialog, QMenu

from eric7 import EricUtilities
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox


class WifiController(QObject):
    """
    Class implementing the WiFi related functionality.
    """

    def __init__(self, microPython, parent=None):
        """
        Constructor

        @param microPython reference to the MicroPython widget
        @type MicroPythonWidget
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

        self.__mpy = microPython

    def createMenu(self, menu):
        """
        Public method to create the WiFi submenu.

        @param menu reference to the parent menu
        @type QMenu
        @return reference to the created menu
        @rtype QMenu
        """
        wifiMenu = QMenu(self.tr("WiFi Functions"), menu)
        wifiMenu.setTearOffEnabled(True)
        wifiMenu.addAction(self.tr("Show WiFi Status"), self.__showWifiStatus)
        wifiMenu.addSeparator()
        wifiMenu.addAction(self.tr("Connect WiFi"), self.__connectWifi)
        wifiMenu.addAction(self.tr("Check Internet Connection"), self.__checkInternet)
        wifiMenu.addAction(self.tr("Disconnect WiFi"), self.__disconnectWifi)
        wifiMenu.addSeparator()
        wifiMenu.addAction(self.tr("Scan Networks"), self.__scanNetwork)
        wifiMenu.addSeparator()
        wifiMenu.addAction(self.tr("Write WiFi Credentials"), self.__writeCredentials)
        wifiMenu.addAction(self.tr("Remove WiFi Credentials"), self.__removeCredentials)
        if not self.__mpy.getDevice().hasCircuitPython():
            wifiMenu.addAction(self.tr("Enable WebREPL"), self.__enableWebrepl)
            wifiMenu.addAction(self.tr("Disable WebREPL"), self.__disableWebrepl)
        wifiMenu.addSeparator()
        wifiMenu.addAction(self.tr("Start WiFi Access Point"), self.__startAccessPoint)
        wifiMenu.addAction(
            self.tr("Start WiFi Access Point with IP"), self.__startAccessPointIP
        )
        wifiMenu.addAction(
            self.tr("Show Connected Clients"), self.__showConnectedClients
        )
        wifiMenu.addAction(self.tr("Stop WiFi Access Point"), self.__stopAccessPoint)
        wifiMenu.addSeparator()
        wifiMenu.addAction(
            self.tr("Deactivate Client Interface"),
            lambda: self.__deactivateInterface("STA"),
        )
        wifiMenu.addAction(
            self.tr("Deactivate Access Point Interface"),
            lambda: self.__deactivateInterface("AP"),
        )
        wifiMenu.addSeparator()
        wifiMenu.addAction(self.tr("Set Network Time"), self.__setNetworkTime)

        # add device specific entries (if there are any)
        self.__mpy.getDevice().addDeviceWifiEntries(wifiMenu)

        return wifiMenu

    @pyqtSlot()
    def __showWifiStatus(self):
        """
        Private slot to show a dialog with the WiFi status of the current device.
        """
        from .WifiStatusDialog import WifiStatusDialog

        try:
            clientStatus, apStatus, overallStatus = self.__mpy.getDevice().getWifiData()

            dlg = WifiStatusDialog(
                clientStatus, apStatus, overallStatus, parent=self.__mpy
            )
            dlg.exec()
        except Exception as exc:
            self.__mpy.showError("getWifiData()", str(exc))

    @pyqtSlot()
    def __connectWifi(self):
        """
        Private slot to connect the current device to a WiFi network.
        """
        from .WifiConnectionDialog import WifiConnectionDialog

        dlg = WifiConnectionDialog(parent=self.__mpy)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ssid, password, hostname = dlg.getConnectionParameters()
            success, error = self.__mpy.getDevice().connectWifi(
                ssid, password, hostname
            )
            if success:
                EricMessageBox.information(
                    None,
                    self.tr("Connect WiFi"),
                    self.tr(
                        "<p>The device was connected to <b>{0}</b> successfully.</p>"
                    ).format(ssid),
                )
            else:
                EricMessageBox.critical(
                    None,
                    self.tr("Connect WiFi"),
                    self.tr(
                        "<p>The device could not connect to <b>{0}</b>.</p>"
                        "<p>Reason: {1}</p>"
                    ).format(ssid, error if error else self.tr("unknown")),
                )

    @pyqtSlot()
    def __disconnectWifi(self):
        """
        Private slot to disconnect the current device from the WiFi network.
        """
        success, error = self.__mpy.getDevice().disconnectWifi()
        if success:
            EricMessageBox.information(
                None,
                self.tr("Disconnect WiFi"),
                self.tr("<p>The device was disconnected from the WiFi network.</p>"),
            )
        else:
            EricMessageBox.critical(
                None,
                self.tr("Disconnect WiFi"),
                self.tr(
                    "<p>The device could not be disconnected.</p><p>Reason: {0}</p>"
                ).format(error if error else self.tr("unknown")),
            )

    @pyqtSlot()
    def __checkInternet(self):
        """
        Private slot to check the availability of an internet connection.
        """
        success, error = self.__mpy.getDevice().checkInternet()
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
    def __scanNetwork(self):
        """
        Private slot to scan for visible WiFi networks.
        """
        from .WifiNetworksWindow import WifiNetworksWindow

        win = WifiNetworksWindow(self.__mpy.getDevice(), self.__mpy)
        win.show()
        win.scanNetworks()

    @pyqtSlot()
    def __writeCredentials(self):
        """
        Private slot to save the WiFi login credentials to the connected device.

        This will also modify the boot script to perform an automatic WiFi connection.
        """
        from .WifiConnectionDialog import WifiConnectionDialog

        dlg = WifiConnectionDialog(
            withCountry=self.__mpy.getDevice().hasWifiCountry(),
            parent=self.__mpy,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ssid, password, hostname = dlg.getConnectionParameters()
            country = dlg.getCountryCode()
            success, error = self.__mpy.getDevice().writeCredentials(
                ssid, password, hostname, country
            )
            if success:
                if self.__mpy.getDevice().hasCircuitPython():
                    # CircuitPython will reset for the REPL, so no auto-connect
                    # available.
                    if EricUtilities.versionToTuple(
                        self.__mpy.getDevice().getDeviceData("release")
                    ) >= (8, 0, 0):
                        EricMessageBox.information(
                            None,
                            self.tr("Write WiFi Credentials"),
                            self.tr(
                                "<p>The WiFi credentials were saved on the device. The"
                                " device will connect to the WiFi network at boot time."
                                "</p>"
                            ),
                        )
                    else:
                        EricMessageBox.information(
                            None,
                            self.tr("Write WiFi Credentials"),
                            self.tr(
                                "<p>The WiFi credentials and a connect script were"
                                " saved on the device. Use the script by simply"
                                " importing it.</p>"
                            ),
                        )
                else:
                    EricMessageBox.information(
                        None,
                        self.tr("Write WiFi Credentials"),
                        self.tr(
                            "<p>The WiFi credentials were saved on the device. The"
                            " device will connect to the WiFi network at boot time.</p>"
                        ),
                    )
            else:
                EricMessageBox.critical(
                    None,
                    self.tr("Write WiFi Credentials"),
                    self.tr(
                        "<p>The WiFi credentials could not be saved on the device.</p>"
                        "<p>Reason: {0}</p>"
                    ).format(error if error else self.tr("unknown")),
                )

    @pyqtSlot()
    def __removeCredentials(self):
        """
        Private slot to remove the saved WiFi credentials from the connected device.

        This will not remove the auto-connect part of the boot script. This needs to be
        done manually if desired.
        """
        ok = EricMessageBox.yesNo(
            None,
            self.tr("Remove WiFi Credentials"),
            self.tr(
                "Shall the saved WiFi credentials really be removed from the connected"
                " device?"
            ),
        )
        if ok:
            success, error = self.__mpy.getDevice().removeCredentials()
            if success:
                EricMessageBox.information(
                    None,
                    self.tr("Remove WiFi Credentials"),
                    self.tr(
                        "<p>The WiFi credentials were removed from the device. The"
                        " device will not connect to the WiFi network at boot time"
                        " anymore.</p>"
                    ),
                )
            else:
                EricMessageBox.critical(
                    None,
                    self.tr("Remove WiFi Credentials"),
                    self.tr(
                        "<p>The WiFi credentials could not be removed from the device."
                        "</p><p>Reason: {0}</p>"
                    ).format(error if error else self.tr("unknown")),
                )

    @pyqtSlot()
    def __startAccessPoint(self, withIP=False):
        """
        Private slot to start the Access Point interface of the connected device.

        @param withIP flag indicating to start the access point with an IP configuration
        @type bool
        """
        from .WifiApConfigDialog import WifiApConfigDialog

        dlg = WifiApConfigDialog(withIP=withIP, parent=self.__mpy)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ssid, password, security, hostname, ifconfig = dlg.getApConfig()

            ok, err = self.__mpy.getDevice().startAccessPoint(
                ssid,
                security=security,
                password=password,
                hostname=hostname,
                ifconfig=ifconfig if withIP else None,
            )
            if ok:
                EricMessageBox.information(
                    None,
                    self.tr("Start WiFi Access Point"),
                    self.tr(
                        "The WiFi Access Point interface was started successfully."
                    ),
                )
            else:
                msg = self.tr("<p>The WiFi Access Point could not be started.</p>")
                if err:
                    msg += self.tr("<p>Reason: {0}</p>").format(err)
                EricMessageBox.critical(
                    None,
                    self.tr("Start WiFi Access Point"),
                    msg,
                )

    @pyqtSlot()
    def __startAccessPointIP(self):
        """
        Private slot to start the Access Point interface of the connected device
        with given IP parameters.
        """
        self.__startAccessPoint(withIP=True)

    @pyqtSlot()
    def __stopAccessPoint(self):
        """
        Private slot to stop the Access Point interface of the connected device.
        """
        ok, err = self.__mpy.getDevice().stopAccessPoint()
        if ok:
            EricMessageBox.information(
                None,
                self.tr("Stop WiFi Access Point"),
                self.tr("The WiFi Access Point interface was stopped successfully."),
            )
        else:
            msg = self.tr("<p>The WiFi Access Point could not be stopped.</p>")
            if err:
                msg += self.tr("<p>Reason: {0}</p>").format(err)
            EricMessageBox.critical(
                None,
                self.tr("Stop WiFi Access Point"),
                msg,
            )

    @pyqtSlot()
    def __showConnectedClients(self):
        """
        Private slot to show a list of WiFi clients connected to the Access Point
        interface.
        """
        from .WifiApStationsDialog import WifiApStationsDialog

        with EricOverrideCursor():
            stations, err = self.__mpy.getDevice().getConnectedClients()

        if err:
            self.__mpy.showError("getConnectedClients()", err)
        else:
            if stations:
                dlg = WifiApStationsDialog(stations, parent=self.__mpy)
                dlg.exec()
            else:
                EricMessageBox.information(
                    None,
                    self.tr("Show Connected Clients"),
                    self.tr("No clients are connected to the access point."),
                )

    def __deactivateInterface(self, interface):
        """
        Private method to deactivate a given WiFi interface of the connected device.

        @param interface designation of the interface to be deactivated (one of 'AP'
            or 'STA')
        @type str
        """
        ok, err = self.__mpy.getDevice().deactivateInterface(interface)
        if ok:
            EricMessageBox.information(
                None,
                self.tr("Deactivate WiFi Interface"),
                self.tr("The WiFi interface was deactivated successfully."),
            )
        else:
            msg = self.tr("<p>The WiFi interface could not be deactivated.</p>")
            if err:
                msg += self.tr("<p>Reason: {0}</p>").format(err)
            EricMessageBox.critical(
                None,
                self.tr("Deactivate WiFi Interface"),
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
                EricMessageBox.warning(
                    None,
                    self.tr("Set Network Time"),
                    self.tr(
                        "<p>The device does not support network time synchronization."
                        " The module <b>adafruit_ntp</b> is not installed.</p>"
                    ),
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
                        " connected to a WiFi network?</p>"
                    )
                EricMessageBox.critical(
                    None,
                    self.tr("Set Network Time"),
                    msg,
                )

    @pyqtSlot()
    def __enableWebrepl(self):
        """
        Private slot to enable the WebREPL server of the device.

        This will also modify the boot script.
        """
        from ..MicroPythonWebreplParametersDialog import (
            MicroPythonWebreplParametersDialog,
        )

        dlg = MicroPythonWebreplParametersDialog(parent=self.__mpy)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            (password,) = dlg.getParameters()
            success, error = self.__mpy.getDevice().enableWebrepl(password)
            if success:
                EricMessageBox.information(
                    None,
                    self.tr("Enable WebREPL"),
                    self.tr(
                        "<p>The WebREPL server of the device will be activated after a"
                        " reboot.</p>"
                    ),
                )
            else:
                EricMessageBox.critical(
                    None,
                    self.tr("Enable WebREPL"),
                    self.tr(
                        "<p>The WebREPL server of the device could not be enabled.</p>"
                        "<p>Reason: {0}</p>"
                    ).format(error if error else self.tr("unknown")),
                )

    @pyqtSlot()
    def __disableWebrepl(self):
        """
        Private slot to disable the WebREPL server of the device.

        This will not remove the 'webrepl_cfg.py' file. It will just modify the boot
        script.
        """
        ok = EricMessageBox.yesNo(
            None,
            self.tr("Disable WebREPL"),
            self.tr("Shall the WebREPL server of the device really be disabled?"),
        )
        if ok:
            success, error = self.__mpy.getDevice().disableWebrepl()
            if success:
                EricMessageBox.information(
                    None,
                    self.tr("Disable WebREPL"),
                    self.tr(
                        "<p>The WebREPL server of the device will not be enabled"
                        " at boot time anymore.</p>"
                    ),
                )
            else:
                EricMessageBox.critical(
                    None,
                    self.tr("Disable WebREPL"),
                    self.tr(
                        "<p>The WebREPL server of the device could not be disabled."
                        "</p><p>Reason: {0}</p>"
                    ).format(error if error else self.tr("unknown")),
                )
