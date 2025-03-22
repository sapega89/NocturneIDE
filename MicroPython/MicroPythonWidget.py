# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the MicroPython REPL widget.
"""

import contextlib
import functools
import os
import time

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import (
    QDialog,
    QInputDialog,
    QLineEdit,
    QMenu,
    QToolButton,
    QWidget,
)

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricGui.EricOverrideCursor import EricOverrideCursor, EricOverridenCursor
from eric7.EricWidgets import EricFileDialog, EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricListSelectionDialog import EricListSelectionDialog
from eric7.EricWidgets.EricPlainTextDialog import EricPlainTextDialog
from eric7.EricWidgets.EricProcessDialog import EricProcessDialog
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities
from eric7.UI.Info import BugAddress
from eric7.UI.UserInterface import UserInterfaceSide

from . import ConvertToUF2Dialog, Devices, UF2FlashDialog
from .BluetoothDialogs.BluetoothController import BluetoothController
from .EthernetDialogs.EthernetController import EthernetController
from .MicroPythonFileManager import MicroPythonFileManager
from .MicroPythonFileManagerWidget import MicroPythonFileManagerWidget
from .MicroPythonWebreplDeviceInterface import MicroPythonWebreplDeviceInterface
from .Ui_MicroPythonWidget import Ui_MicroPythonWidget
from .WifiDialogs.WifiController import WifiController

try:
    from .MicroPythonGraphWidget import MicroPythonGraphWidget

    HAS_QTCHART = True
except ImportError:
    HAS_QTCHART = False

try:
    from .MicroPythonSerialDeviceInterface import MicroPythonSerialDeviceInterface

    HAS_QTSERIALPORT = True
except ImportError:
    HAS_QTSERIALPORT = False


class MicroPythonWidget(QWidget, Ui_MicroPythonWidget):
    """
    Class implementing the MicroPython REPL widget.

    @signal aboutToDisconnect() emitted to indicate the imminent disconnect from the
        currently device
    @signal disconnected() emitted after the device was disconnected
    @signal dataReceived(data) emitted to send data received via the serial
        connection for further processing
    """

    DeviceTypeRole = Qt.ItemDataRole.UserRole
    DeviceBoardRole = Qt.ItemDataRole.UserRole + 1
    DevicePortRole = Qt.ItemDataRole.UserRole + 2
    DeviceVidRole = Qt.ItemDataRole.UserRole + 3
    DevicePidRole = Qt.ItemDataRole.UserRole + 4
    DeviceSerNoRole = Qt.ItemDataRole.UserRole + 5
    DeviceInterfaceTypeRole = Qt.ItemDataRole.UserRole + 6
    DeviceWebreplUrlRole = Qt.ItemDataRole.UserRole + 7

    dataReceived = pyqtSignal(bytes)
    aboutToDisconnect = pyqtSignal()
    disconnected = pyqtSignal()

    ManualMarker = "<manual>"

    def __init__(self, parent=None, forMPyWindow=False):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        @param forMPyWindow flag indicating the MicroPythonWindow variant
            (defaults to False)
        @type bool (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        if not forMPyWindow:
            self.layout().setContentsMargins(0, 3, 0, 0)

        self.__ui = parent
        self.__forMPyWindow = forMPyWindow

        self.__wifiController = WifiController(self, self)
        self.__wifiMenu = None

        self.__bluetoothController = BluetoothController(self, self)
        self.__btMenu = None

        self.__ethernetController = EthernetController(self, self)
        self.__ethernetMenu = None

        self.__superMenu = QMenu(self)
        self.__superMenu.aboutToShow.connect(self.__aboutToShowSuperMenu)

        self.menuButton.setObjectName("micropython_supermenu_button")
        self.menuButton.setIcon(EricPixmapCache.getIcon("superMenu"))
        self.menuButton.setToolTip(self.tr("MicroPython Menu"))
        self.menuButton.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.menuButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.menuButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.menuButton.setShowMenuInside(True)
        self.menuButton.setMenu(self.__superMenu)

        self.deviceIconLabel.setPixmap(Devices.getDeviceIcon("", False))

        self.repopulateButton.setIcon(EricPixmapCache.getIcon("question"))
        self.webreplConfigButton.setIcon(EricPixmapCache.getIcon("edit"))
        self.runButton.setIcon(EricPixmapCache.getIcon("start"))
        self.replButton.setIcon(EricPixmapCache.getIcon("terminal"))
        self.filesButton.setIcon(EricPixmapCache.getIcon("filemanager"))
        self.chartButton.setIcon(EricPixmapCache.getIcon("chart"))
        self.connectButton.setIcon(EricPixmapCache.getIcon("linkConnect"))

        for button in (
            self.runButton,
            self.replButton,
            self.filesButton,
            self.chartButton,
        ):
            button.setEnabled(False)

        self.__fileManager = None
        self.__fileManagerWidget = None
        self.__chartWidget = None

        self.__unknownPorts = []
        self.__lastPort = None
        self.__lastDeviceType = None

        self.__lastWebreplUrl = None

        self.__interface = None
        self.__device = None
        self.__connected = False
        self.__linkConnected = False
        self.__setConnected(False)

        if not HAS_QTSERIALPORT:
            self.replWidget.replEdit().setHtml(
                self.tr(
                    "<h3>The QtSerialPort package is not available.<br/>"
                    "MicroPython support is deactivated.</h3>"
                )
            )
            self.setEnabled(False)
            return

        self.__populateDeviceTypeComboBox()

        self.repopulateButton.clicked.connect(self.__populateDeviceTypeComboBox)
        self.webreplConfigButton.clicked.connect(self.__configureWebreplUrls)
        self.__ui.preferencesChanged.connect(self.__handlePreferencesChanged)

        self.__handlePreferencesChanged()

    def __populateDeviceTypeComboBox(self):
        """
        Private method to populate the device type selector.
        """
        currentDevice = self.deviceTypeComboBox.currentText()

        self.deviceTypeComboBox.clear()
        self.deviceInfoLabel.clear()

        self.deviceTypeComboBox.addItem("", "")
        devices, unknownDevices, unknownPorts = Devices.getFoundDevices()
        if devices:
            supportedMessage = self.tr(
                "%n supported serial device(s) detected.", "", len(devices)
            )

            for index, (
                boardType,
                boardName,
                description,
                portName,
                vid,
                pid,
                serialNumber,
            ) in enumerate(sorted(devices), 1):
                self.deviceTypeComboBox.addItem(
                    self.tr(
                        "{0} - {1} ({2})", "board name, description, port name"
                    ).format(boardName, description, portName)
                )
                self.deviceTypeComboBox.setItemData(
                    index, boardType, self.DeviceTypeRole
                )
                self.deviceTypeComboBox.setItemData(
                    index, boardName, self.DeviceBoardRole
                )
                self.deviceTypeComboBox.setItemData(
                    index, portName, self.DevicePortRole
                )
                self.deviceTypeComboBox.setItemData(index, vid, self.DeviceVidRole)
                self.deviceTypeComboBox.setItemData(index, pid, self.DevicePidRole)
                self.deviceTypeComboBox.setItemData(
                    index, serialNumber, self.DeviceSerNoRole
                )
                self.deviceTypeComboBox.setItemData(
                    index, "serial", self.DeviceInterfaceTypeRole
                )

        else:
            supportedMessage = self.tr("No supported serial devices detected.")

        self.__unknownPorts = unknownPorts
        if self.__unknownPorts:
            unknownMessage = self.tr(
                "\n%n unknown device(s) for manual selection.",
                "",
                len(self.__unknownPorts),
            )
            if self.deviceTypeComboBox.count():
                self.deviceTypeComboBox.insertSeparator(self.deviceTypeComboBox.count())
            self.deviceTypeComboBox.addItem(self.tr("Manual Selection"))
            self.deviceTypeComboBox.setItemData(
                self.deviceTypeComboBox.count() - 1,
                self.ManualMarker,
                self.DeviceTypeRole,
            )
        else:
            unknownMessage = ""

        # add WebREPL entries
        self.deviceTypeComboBox.insertSeparator(self.deviceTypeComboBox.count())
        self.deviceTypeComboBox.addItem(self.tr("WebREPL (manual)"))
        index = self.deviceTypeComboBox.count() - 1
        self.deviceTypeComboBox.setItemData(
            index, "webrepl", self.DeviceInterfaceTypeRole
        )
        webreplUrlsDict = Preferences.getMicroPython("WebreplUrls")
        for name in sorted(webreplUrlsDict):
            self.deviceTypeComboBox.addItem(webreplUrlsDict[name]["description"])
            index = self.deviceTypeComboBox.count() - 1
            self.deviceTypeComboBox.setItemData(
                index, webreplUrlsDict[name]["device_type"], self.DeviceTypeRole
            )
            self.deviceTypeComboBox.setItemData(
                index, "webrepl", self.DeviceInterfaceTypeRole
            )
            self.deviceTypeComboBox.setItemData(
                index, webreplUrlsDict[name]["url"], self.DeviceWebreplUrlRole
            )
        webreplMessage = (
            self.tr("\n%n WebREPL connection(s) defined.", "", len(webreplUrlsDict))
            if webreplUrlsDict
            else ""
        )

        self.deviceInfoLabel.setText(supportedMessage + unknownMessage + webreplMessage)

        index = self.deviceTypeComboBox.findText(
            currentDevice, Qt.MatchFlag.MatchExactly
        )
        if index == -1:
            # entry is no longer present
            index = 0
            if self.__linkConnected:
                # we are still connected, so disconnect
                self.on_connectButton_clicked()
            self.__device = None

        if self.__device is None:
            self.on_deviceTypeComboBox_activated(index)
        self.deviceTypeComboBox.setCurrentIndex(index)

        if unknownDevices:
            ignoredUnknown = {
                tuple(d) for d in Preferences.getMicroPython("IgnoredUnknownDevices")
            }
            uf2Devices = {(*x[2], x[1]) for x in UF2FlashDialog.getFoundDevices()}
            newUnknownDevices = set(unknownDevices) - ignoredUnknown - uf2Devices
            if newUnknownDevices:
                button = EricMessageBox.information(
                    self,
                    self.tr("Unknown MicroPython Device"),
                    self.tr(
                        "<p>Detected these unknown serial devices</p>"
                        "<ul>"
                        "<li>{0}</li>"
                        "</ul>"
                        "<p>Please report them together with the board name"
                        ' and a short description to <a href="mailto:{1}">'
                        " the eric bug reporting address</a> if it is a"
                        " MicroPython board.</p>"
                    ).format(
                        "</li><li>".join(
                            [
                                self.tr(
                                    "{0} (0x{1:04x}/0x{2:04x})", "description, VID, PID"
                                ).format(desc, vid, pid)
                                for vid, pid, desc in newUnknownDevices
                            ]
                        ),
                        BugAddress,
                    ),
                    EricMessageBox.Ignore | EricMessageBox.Ok,
                )
                if button == EricMessageBox.Ignore:
                    ignoredUnknown = list(ignoredUnknown | newUnknownDevices)
                    Preferences.setMicroPython("IgnoredUnknownDevices", ignoredUnknown)
                else:
                    yes = EricMessageBox.yesNo(
                        self,
                        self.tr("Unknown MicroPython Device"),
                        self.tr(
                            """Would you like to add them to the list of"""
                            """ manually configured devices?"""
                        ),
                        yesDefault=True,
                    )
                    if yes:
                        self.__addUnknownDevices(list(newUnknownDevices))

    def __handlePreferencesChanged(self):
        """
        Private slot to handle a change in preferences.
        """
        self.replWidget.replEdit().handlePreferencesChanged()

        if self.__interface is not None:
            self.__interface.handlePreferencesChanged

        if self.__chartWidget is not None:
            self.__chartWidget.preferencesChanged()

    @pyqtSlot()
    def __configureWebreplUrls(self):
        """
        Private slot to configure the list of selectable WebREPL URLs.
        """
        from .MicroPythonWebreplUrlsConfigDialog import (
            MicroPythonWebreplUrlsConfigDialog,
        )

        webreplUrlsDict = Preferences.getMicroPython("WebreplUrls")
        dlg = MicroPythonWebreplUrlsConfigDialog(webreplUrlsDict, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            webreplUrlsDict = dlg.getWebreplDict()
            Preferences.setMicroPython("WebreplUrls", webreplUrlsDict)

            self.__populateDeviceTypeComboBox()

    def deviceInterface(self):
        """
        Public method to get a reference to the device interface object.

        @return reference to the commands interface object
        @rtype MicroPythonDeviceInterface
        """
        return self.__interface

    def isMicrobit(self):
        """
        Public method to check, if the connected/selected device is a
        BBC micro:bit or Calliope mini.

        @return flag indicating a micro:bit device
        @rtype bool
        """
        if (
            self.__device
            and (
                "micro:bit" in self.__device.deviceName()
                or "Calliope" in self.__device.deviceName()
            )
            and not self.__device.hasCircuitPython()
        ):
            return True

        return False

    @pyqtSlot(int)
    def on_deviceTypeComboBox_activated(self, index):
        """
        Private slot handling the selection of a device type.

        @param index index of the selected device
        @type int
        """
        deviceType = self.deviceTypeComboBox.itemData(index, self.DeviceTypeRole)
        if deviceType == self.ManualMarker:
            self.connectButton.setEnabled(bool(self.__unknownPorts))
        else:
            self.deviceIconLabel.setPixmap(Devices.getDeviceIcon(deviceType, False))

            boardName = self.deviceTypeComboBox.itemData(index, self.DeviceBoardRole)
            vid = self.deviceTypeComboBox.itemData(index, self.DeviceVidRole)
            pid = self.deviceTypeComboBox.itemData(index, self.DevicePidRole)
            serNo = self.deviceTypeComboBox.itemData(index, self.DeviceSerNoRole)

            if deviceType or (vid is not None and pid is not None):
                self.__device = Devices.getDevice(
                    deviceType, self, vid, pid, boardName=boardName, serialNumber=serNo
                )
                self.__device.setButtons()

                self.connectButton.setEnabled(bool(deviceType))
            else:
                self.__device = None

    def setActionButtons(self, **kwargs):
        """
        Public method to set the enabled state of the various action buttons.

        @keyparam kwargs keyword arguments containg the enabled states (keys
            are 'run', 'repl', 'files', 'chart', 'open', 'save'
        @type dict
        """
        if "run" in kwargs:
            self.runButton.setEnabled(kwargs["run"] and self.__connected)
        if "repl" in kwargs:
            self.replButton.setEnabled(kwargs["repl"] and self.__linkConnected)
        if "files" in kwargs:
            self.filesButton.setEnabled(kwargs["files"] and self.__connected)
        if "chart" in kwargs:
            self.chartButton.setEnabled(
                kwargs["chart"] and HAS_QTCHART and self.__connected
            )

    def __setConnected(self, connected):
        """
        Private method to set the connection status LED.

        @param connected connection state
        @type bool
        """
        self.__connected = connected
        self.__linkConnected = bool(self.__interface) and self.__interface.isConnected()

        self.deviceConnectedLed.setOn(self.__linkConnected)
        if self.__fileManagerWidget:
            self.__fileManagerWidget.deviceConnectedLed.setOn(connected)

        self.deviceTypeComboBox.setEnabled(not self.__linkConnected)

        if self.__linkConnected:
            self.connectButton.setIcon(EricPixmapCache.getIcon("linkDisconnect"))
            self.connectButton.setToolTip(
                self.tr("Press to disconnect the current device")
            )
        else:
            self.connectButton.setIcon(EricPixmapCache.getIcon("linkConnect"))
            self.connectButton.setToolTip(
                self.tr("Press to connect the selected device")
            )

        if not connected:
            for menu in (self.__wifiMenu, self.__btMenu, self.__ethernetMenu):
                if menu and menu.isTearOffMenuVisible():
                    menu.hideTearOffMenu()

    def isConnected(self):
        """
        Public method to get the MicroPython device connection state.

        @return connection state
        @rtype bool
        """
        return self.__connected

    def isLinkConnected(self):
        """
        Public method to get the link connection state.

        @return connection state
        @rtype bool
        """
        return self.__linkConnected

    def __showNoDeviceMessage(self):
        """
        Private method to show a message dialog indicating a missing device.
        """
        EricMessageBox.critical(
            self,
            self.tr("No device attached"),
            self.tr(
                """Please ensure the device is plugged into your"""
                """ computer and selected.\n\nIt must have a version"""
                """ of MicroPython (or CircuitPython) flashed onto"""
                """ it before anything will work.\n\nFinally press"""
                """ the device's reset button and wait a few seconds"""
                """ before trying again."""
            ),
        )

    @pyqtSlot(bool)
    def on_replButton_clicked(self, checked):
        """
        Private slot to connect to enable or disable the REPL widget.

        If the selected device is not connected yet, this will be done now.

        @param checked state of the button
        @type bool
        """
        if not self.__device:
            self.__showNoDeviceMessage()
            return

        if checked:
            ok, reason = self.__device.canStartRepl()
            if not ok:
                EricMessageBox.warning(
                    self,
                    self.tr("Start REPL"),
                    self.tr(
                        """<p>The REPL cannot be started.</p><p>Reason:"""
                        """ {0}</p>"""
                    ).format(reason),
                )
                return

            self.replWidget.replEdit().clear()
            if self.__interface is None:
                return
            self.__interface.dataReceived.connect(
                self.replWidget.replEdit().processData
            )

            if not self.__interface.isConnected():
                self.__connectToDevice()
                if self.__device.forceInterrupt():
                    # send a Ctrl-B (exit raw mode)
                    self.__interface.write(b"\x02")
                    # send Ctrl-C (keyboard interrupt)
                    self.__interface.write(b"\x03")

            self.__device.setRepl(True)
            self.replWidget.replEdit().setFocus(Qt.FocusReason.OtherFocusReason)
        else:
            with contextlib.suppress(TypeError):
                if self.__interface is not None:
                    self.__interface.dataReceived.disconnect(
                        self.replWidget.replEdit().processData
                    )
            if not self.chartButton.isChecked() and not self.filesButton.isChecked():
                self.__disconnectFromDevice()
            self.__device.setRepl(False)
        self.replButton.setChecked(checked)

    @pyqtSlot()
    def on_connectButton_clicked(self):
        """
        Private slot to connect to the selected device or disconnect from the
        currently connected device.
        """
        self.replWidget.clearOSD()
        if self.__linkConnected:
            self.aboutToDisconnect.emit()
            with EricOverrideCursor():
                self.__disconnectFromDevice()
            self.disconnected.emit()

            if self.replButton.isChecked():
                self.on_replButton_clicked(False)
            if self.filesButton.isChecked():
                self.on_filesButton_clicked(False)
            if self.chartButton.isChecked():
                self.on_chartButton_clicked(False)
            if self.runButton.isChecked():
                self.on_runButton_clicked(False)
        else:
            with EricOverrideCursor():
                self.__connectToDevice(withAutostart=True)

    def getCurrentPort(self):
        """
        Public method to determine the port path of the selected device.

        @return path of the port of the selected device
        @rtype str
        """
        portName = self.deviceTypeComboBox.currentData(self.DevicePortRole)
        if portName:
            if OSUtilities.isWindowsPlatform():
                # return it unchanged
                return portName
            else:
                # return with device path prepended
                return "/dev/{0}".format(portName)
        else:
            return ""

    def getDevice(self):
        """
        Public method to get a reference to the current device.

        @return reference to the current device
        @rtype BaseDevice
        """
        return self.__device

    def getDeviceWorkspace(self):
        """
        Public method to get the workspace directory of the device.

        @return workspace directory of the device
        @rtype str
        """
        if self.__device:
            return self.__device.getWorkspace()
        else:
            return ""

    def deviceSupportsLocalFileAccess(self):
        """
        Public method to indicate that the device access the device file system
        via a local directory.

        @return flag indicating file access via local directory
        @rtype bool
        """
        return self.__device is not None and self.__device.supportsLocalFileAccess()

    def __connectToDevice(self, withAutostart=False):
        """
        Private method to connect to the selected device.

        @param withAutostart flag indicating to start the repl and file manager
            automatically
        @type bool
        @exception ValueError raised to indicate an unsupported interface type
        """
        from .ConnectionSelectionDialog import ConnectionSelectionDialog
        from .MicroPythonWebreplConnectionDialog import (
            MicroPythonWebreplConnectionDialog,
        )

        interfaceType = (
            self.deviceTypeComboBox.currentData(self.DeviceInterfaceTypeRole)
            or "serial"
        )  # 'serial' is the default

        if interfaceType not in ("serial", "webrepl"):
            raise ValueError(
                "Unsupported interface type detected ('{0}')".format(interfaceType)
            )

        if interfaceType == "serial":
            port = self.getCurrentPort()
            if not port:
                with EricOverridenCursor():
                    dlg = ConnectionSelectionDialog(
                        self.__unknownPorts,
                        self.__lastPort,
                        self.__lastDeviceType,
                        parent=self,
                    )
                    if dlg.exec() == QDialog.DialogCode.Accepted:
                        vid, pid, port, deviceType = dlg.getData()

                        self.deviceIconLabel.setPixmap(
                            Devices.getDeviceIcon(deviceType, False)
                        )
                        self.__device = Devices.getDevice(deviceType, self, vid, pid)

                        self.__lastPort = port
                        self.__lastDeviceType = deviceType
                    else:
                        return

            self.__interface = MicroPythonSerialDeviceInterface(self)
        elif interfaceType == "webrepl":
            port = self.deviceTypeComboBox.currentData(self.DeviceWebreplUrlRole)
            if not port:
                with EricOverridenCursor():
                    dlg = MicroPythonWebreplConnectionDialog(
                        self.__lastWebreplUrl, self.__lastDeviceType, parent=self
                    )
                    if dlg.exec() == QDialog.DialogCode.Accepted:
                        port, deviceType = dlg.getWebreplConnectionParameters()

                        self.deviceIconLabel.setPixmap(
                            Devices.getDeviceIcon(deviceType, False)
                        )
                        self.__device = Devices.getDevice(deviceType, self, None, None)

                        self.__lastWebreplUrl = port
                        self.__lastDeviceType = deviceType
                    else:
                        return

            self.__interface = MicroPythonWebreplDeviceInterface(self)
        self.replWidget.replEdit().setInterface(self.__interface)
        self.__interface.osdInfo.connect(self.replWidget.setOSDInfo)

        ok, error = self.__interface.connectToDevice(port)
        if ok:
            deviceResponding = self.__interface.probeDevice()
            self.__setConnected(deviceResponding)
            self.__device.setConnected(deviceResponding)
            if deviceResponding:
                if (
                    Preferences.getMicroPython("SyncTimeAfterConnect")
                    and self.__device.hasTimeCommands()
                ):
                    self.__synchronizeTime(quiet=True)
            else:
                with EricOverridenCursor():
                    EricMessageBox.warning(
                        self,
                        self.tr("Serial Device Connect"),
                        self.tr(
                            """<p>The device at serial port <b>{0}</b> does not"""
                            """ respond. It may not have a MicroPython firmware"""
                            """ flashed.</p>"""
                        ).format(port),
                    )
        else:
            msg = self.tr(
                "<p>Cannot connect to device at serial port <b>{0}</b>.</p>"
                "<p><b>Reason:</b> {1}</p>"
            ).format(port, error if error else self.tr("unknown"))
            with EricOverridenCursor():
                EricMessageBox.warning(self, self.tr("Serial Device Connect"), msg)

        self.__device.setButtons()
        if withAutostart:
            self.on_replButton_clicked(
                self.replButton.isEnabled() and self.__linkConnected
            )
            self.on_filesButton_clicked(
                self.filesButton.isEnabled() and self.__connected
            )

    def __disconnectFromDevice(self):
        """
        Private method to disconnect from the device.
        """
        self.__device and self.__device.setConnected(False)
        self.__setConnected(False)

        if self.__interface is not None:
            self.__interface.disconnectFromDevice()
            self.__interface.deleteLater()
            self.__interface = None
            self.replWidget.replEdit().setInterface(None)

    @pyqtSlot()
    def on_runButton_clicked(self):
        """
        Private slot to execute the script of the active editor on the
        selected device.

        If the REPL is not active yet, it will be activated, which might cause
        an unconnected device to be connected.
        """
        if not self.__device:
            self.__showNoDeviceMessage()
            return

        aw = ericApp().getObject("ViewManager").activeWindow()
        if aw is None:
            EricMessageBox.critical(
                self,
                self.tr("Run Script"),
                self.tr("""There is no editor open. Abort..."""),
            )
            return

        script = aw.text()
        if not script:
            EricMessageBox.critical(
                self,
                self.tr("Run Script"),
                self.tr("""The current editor does not contain a script. Abort..."""),
            )
            return

        ok, reason = self.__device.canRunScript()
        if not ok:
            EricMessageBox.warning(
                self,
                self.tr("Run Script"),
                self.tr("""<p>Cannot run script.</p><p>Reason: {0}</p>""").format(
                    reason
                ),
            )
            return

        if not self.replButton.isChecked():
            # activate on the REPL
            self.on_replButton_clicked(True)
        if self.replButton.isChecked():
            self.__device.runScript(script)

    @pyqtSlot(bool)
    def on_chartButton_clicked(self, checked):
        """
        Private slot to open a chart view to plot data received from the
        connected device.

        If the selected device is not connected yet, this will be done now.

        @param checked state of the button
        @type bool
        """
        if not HAS_QTCHART:
            # QtCharts not available => fail silently
            return

        if not self.__device:
            self.__showNoDeviceMessage()
            return

        if checked:
            ok, reason = self.__device.canStartPlotter()
            if not ok:
                EricMessageBox.warning(
                    self,
                    self.tr("Start Chart"),
                    self.tr(
                        """<p>The Chart cannot be started.</p><p>Reason:"""
                        """ {0}</p>"""
                    ).format(reason),
                )
                return

            self.__chartWidget = MicroPythonGraphWidget(self)
            self.__interface.dataReceived.connect(self.__chartWidget.processData)
            self.__chartWidget.dataFlood.connect(self.handleDataFlood)

            self.__ui.addSideWidget(
                UserInterfaceSide.Bottom,
                self.__chartWidget,
                EricPixmapCache.getIcon("chart"),
                self.tr("µPy Chart"),
            )
            self.__ui.showSideWidget(self.__chartWidget)

            if not self.__interface.isConnected():
                self.__connectToDevice()
                if self.__device.forceInterrupt():
                    # send a Ctrl-B (exit raw mode)
                    self.__interface.write(b"\x02")
                    # send Ctrl-C (keyboard interrupt)
                    self.__interface.write(b"\x03")

            self.__device.setPlotter(True)
        else:
            if self.__chartWidget.isDirty():
                res = EricMessageBox.okToClearData(
                    self,
                    self.tr("Unsaved Chart Data"),
                    self.tr("""The chart contains unsaved data."""),
                    self.__chartWidget.saveData,
                )
                if not res:
                    # abort
                    return

            self.__interface.dataReceived.disconnect(self.__chartWidget.processData)
            self.__chartWidget.dataFlood.disconnect(self.handleDataFlood)

            if not self.replButton.isChecked() and not self.filesButton.isChecked():
                self.__disconnectFromDevice()

            self.__device.setPlotter(False)
            self.__ui.removeSideWidget(self.__chartWidget)

            self.__chartWidget.deleteLater()
            self.__chartWidget = None

        self.chartButton.setChecked(checked)

    @pyqtSlot()
    def handleDataFlood(self):
        """
        Public slot handling a data flood from the device.
        """
        self.on_connectButton_clicked()
        self.__device.handleDataFlood()

    @pyqtSlot(bool)
    def on_filesButton_clicked(self, checked):
        """
        Private slot to open a file manager window to the connected device.

        If the selected device is not connected yet, this will be done now.

        @param checked state of the button
        @type bool
        """
        if not self.__device:
            self.__showNoDeviceMessage()
            return

        if checked:
            ok, reason = self.__device.canStartFileManager()
            if not ok:
                EricMessageBox.warning(
                    self,
                    self.tr("Start File Manager"),
                    self.tr(
                        """<p>The File Manager cannot be started.</p>"""
                        """<p>Reason: {0}</p>"""
                    ).format(reason),
                )
                return

            with EricOverrideCursor():
                if not self.__interface.isConnected():
                    self.__connectToDevice()
                if self.__connected:
                    self.__fileManager = MicroPythonFileManager(self.__device, self)
                    self.__fileManagerWidget = MicroPythonFileManagerWidget(
                        self.__fileManager, parent=self
                    )

                    self.__ui.addSideWidget(
                        UserInterfaceSide.Bottom,
                        self.__fileManagerWidget,
                        EricPixmapCache.getIcon("filemanager"),
                        self.tr("µPy Files"),
                    )
                    self.__ui.showSideWidget(self.__fileManagerWidget)

                    self.__device.setFileManager(True)

                    self.__fileManagerWidget.start()
        else:
            if self.__fileManagerWidget is not None:
                self.__fileManagerWidget.stop()
                self.__fileManagerWidget.deleteLater()
            if self.__fileManager is not None:
                self.__fileManager.deleteLater()

            if not self.replButton.isChecked() and not self.chartButton.isChecked():
                self.__disconnectFromDevice()

            self.__device.setFileManager(False)
            self.__ui.removeSideWidget(self.__fileManagerWidget)

            self.__fileManagerWidget = None
            self.__fileManager = None

        self.filesButton.setChecked(checked)

    def getFileManager(self):
        """
        Public method to get a reference to the file manager interface.

        @return reference to the file manager interface
        @rtype MicroPythonFileManager
        """
        return self.__fileManager

    def shutdown(self):
        """
        Public method to perform some shutdown actions.
        """
        if self.__linkConnected:
            with EricOverrideCursor():
                self.__disconnectFromDevice()

    ##################################################################
    ## Super Menu related methods below
    ##################################################################

    def __aboutToShowSuperMenu(self):
        """
        Private slot to populate the Super Menu before showing it.
        """
        self.__superMenu.clear()

        if (
            self.__device
            and self.__linkConnected
            and not self.__device.hasCircuitPython()
        ):
            networkConnected = self.__device.isNetworkConnected()
            useLocalMip = (
                (
                    self.__device.getDeviceData("mip")
                    or self.__device.getDeviceData("upip")
                )
                and not networkConnected
            ) or self.__device.getDeviceData("local_mip")
            hasMip = self.__device.getDeviceData("mip") and networkConnected
            hasUPip = self.__device.getDeviceData("upip") and networkConnected
        else:
            hasMip = False
            hasUPip = False
            useLocalMip = False

        # prepare the download menu
        if self.__device:
            menuEntries = self.__device.getDownloadMenuEntries()
            if menuEntries:
                downloadMenu = QMenu(self.tr("Downloads"), self.__superMenu)
                for text, url in menuEntries:
                    if text == "<separator>":
                        downloadMenu.addSeparator()
                    else:
                        downloadMenu.addAction(
                            text, functools.partial(self.__downloadFromUrl, url)
                        )
            else:
                downloadMenu = None

        # prepare the WiFi menu
        if self.__device and self.__connected and self.__device.getDeviceData("wifi"):
            if self.__wifiMenu is not None:
                self.__wifiMenu.deleteLater()
            self.__wifiMenu = self.__wifiController.createMenu(self.__superMenu)
        else:
            self.__wifiMenu = None

        # prepare the Bluetooth menu
        if (
            self.__device
            and self.__connected
            and self.__device.getDeviceData("bluetooth")
        ):
            if self.__btMenu is not None:
                self.__btMenu.deleteLater()
            self.__btMenu = self.__bluetoothController.createMenu(self.__superMenu)
        else:
            self.__btMenu = None

        # prepare the Ethernet menu
        if (
            self.__device
            and self.__connected
            and self.__device.getDeviceData("ethernet")
        ):
            if self.__ethernetMenu is not None:
                self.__ethernetMenu.deleteLater()
            self.__ethernetMenu = self.__ethernetController.createMenu(self.__superMenu)
        else:
            self.__ethernetMenu = None

        # populate the super menu
        hasTime = self.__device.hasTimeCommands() if self.__device else False

        self.__superMenu.addAction(
            self.tr("Show Version"), self.__showDeviceVersion
        ).setEnabled(self.__connected)
        self.__superMenu.addAction(
            self.tr("Show Implementation"), self.__showImplementation
        ).setEnabled(self.__connected)
        self.__superMenu.addAction(
            self.tr("Show Board Data"), self.__showBoardInformation
        ).setEnabled(self.__connected)
        self.__superMenu.addSeparator()
        if hasTime:
            self.__superMenu.addAction(
                self.tr("Synchronize Time"), self.__synchronizeTime
            ).setEnabled(self.__connected)
            self.__superMenu.addAction(
                self.tr("Show Device Time"), self.__showDeviceTime
            ).setEnabled(self.__connected)
        self.__superMenu.addAction(self.tr("Show Local Time"), self.__showLocalTime)
        if hasTime:
            self.__superMenu.addAction(
                self.tr("Show Time"), self.__showLocalAndDeviceTime
            ).setEnabled(self.__connected)
        self.__superMenu.addSeparator()
        self.__superMenu.addAction(
            self.tr("Show Builtin Modules"), self.__showBuiltinModules
        ).setEnabled(self.__connected)
        if hasMip:
            self.__superMenu.addAction(
                self.tr("Install Package"), lambda: self.__installPackage("mip")
            ).setEnabled(self.__connected)
        elif hasUPip:
            self.__superMenu.addAction(
                self.tr("Install Packages"), lambda: self.__installPackage("upip")
            ).setEnabled(self.__connected)
        elif useLocalMip:
            self.__superMenu.addAction(
                self.tr("Install Package"), lambda: self.__installPackage("local_mip")
            ).setEnabled(self.__connected)
        self.__superMenu.addSeparator()
        if not OSUtilities.isWindowsPlatform():
            available = self.__mpyCrossAvailable()
            self.__superMenu.addAction(
                self.tr("Compile Python File"), self.__compileFile2Mpy
            ).setEnabled(available)
            aw = ericApp().getObject("ViewManager").activeWindow()
            self.__superMenu.addAction(
                self.tr("Compile Current Editor"), self.__compileEditor2Mpy
            ).setEnabled(available and bool(aw))
            self.__superMenu.addSeparator()
        if self.__device:
            self.__device.addDeviceMenuEntries(self.__superMenu)
            self.__superMenu.addSeparator()
            if self.__wifiMenu is not None:
                self.__superMenu.addMenu(self.__wifiMenu)
            if self.__btMenu is not None:
                self.__superMenu.addMenu(self.__btMenu)
            if self.__ethernetMenu is not None:
                self.__superMenu.addMenu(self.__ethernetMenu)
            if (
                self.__wifiMenu is not None
                or self.__btMenu is not None
                or self.__ethernetMenu is not None
            ):
                self.__superMenu.addSeparator()
            if downloadMenu is None:
                # generic download action
                self.__superMenu.addAction(
                    self.tr("Download Firmware"), self.__downloadFirmware
                ).setEnabled(self.__device.hasFirmwareUrl())
            else:
                # download sub-menu
                self.__superMenu.addMenu(downloadMenu)
            self.__superMenu.addSeparator()
            self.__superMenu.addAction(
                self.tr("Show Documentation"), self.__showDocumentation
            ).setEnabled(self.__device.hasDocumentationUrl())
            self.__superMenu.addSeparator()
        self.__superMenu.addAction(self.tr("Convert To UF2"), self.__convertToUF2)
        self.__superMenu.addAction(self.tr("Flash UF2 Device"), self.__flashUF2)
        self.__superMenu.addSeparator()
        self.__superMenu.addAction(
            self.tr("Manage Unknown Devices"), self.__manageUnknownDevices
        )
        self.__superMenu.addAction(
            self.tr("Ignored Serial Devices"), self.__manageIgnored
        )
        self.__superMenu.addSeparator()
        self.__superMenu.addAction(self.tr("Configure"), self.__configure)
        if self.__forMPyWindow:
            self.__superMenu.addSeparator()
            self.__superMenu.addAction(self.tr("Quit"), self.__quit)

    @pyqtSlot()
    def __showDeviceVersion(self):
        """
        Private slot to show some version info about MicroPython of the device.
        """
        data = self.__device.getDeviceData()
        if data:
            msg = self.tr("<h3>Device Version Information</h3>")
            msg += "<table>"
            for key in ("sysname", "nodename", "release", "version", "machine"):
                msg += "<tr><td><b>{0}</b></td><td>{1}</td></tr>".format(
                    key.capitalize(), data[key]
                )
            msg += "</table>"
            EricMessageBox.information(self, self.tr("Device Version Information"), msg)
        else:
            EricMessageBox.critical(
                self,
                self.tr("Device Version Information"),
                self.tr("No version information available."),
            )

    @pyqtSlot()
    def __showImplementation(self):
        """
        Private slot to show some implementation related information.
        """
        data = self.__device.getDeviceData()
        if data:
            # name
            if data["mpy_name"] == "micropython":
                name = "MicroPython"
            elif data["mpy_name"] == "circuitpython":
                name = "CircuitPython"
            elif data["mpy_name"] == "unknown":
                name = self.tr("unknown")
            else:
                name = data["mpy_name"]

            # version
            if data["mpy_variant_version"]:
                version = data["mpy_variant_version"]
            elif data["mpy_version"] == "unknown":
                version = self.tr("unknown")
            else:
                version = data["mpy_version"]

            # variant
            variant = (
                self.tr(" ({0})").format(data["mpy_variant"])
                if data["mpy_variant"]
                else ""
            )

            EricMessageBox.information(
                self,
                self.tr("Device Implementation Information"),
                self.tr(
                    "<h3>Device Implementation Information</h3>"
                    "<p>This device contains <b>{0} {1}{2}</b>.</p>"
                ).format(name, version, variant),
            )
        else:
            EricMessageBox.critical(
                self,
                self.tr("Device Implementation Information"),
                self.tr("No device implementation information available."),
            )

    @pyqtSlot()
    def __showBoardInformation(self):
        """
        Private slot to show all available information about a board.
        """
        from .BoardDataDialog import BoardDataDialog

        try:
            with EricOverrideCursor():
                boardInfo = self.__device.getBoardInformation()
                boardInfo.update(
                    self.__device.getDeviceData(
                        [
                            "wifi",
                            "bluetooth",
                            "ethernet",
                            "mip",
                            "upip",
                            "local_mip",
                        ]
                    )
                )
                boardInfo["ntp"] = self.__device.hasNetworkTime()

            dlg = BoardDataDialog(boardInfo, parent=self)
            dlg.exec()
        except Exception as exc:
            self.showError("getBoardInformation()", str(exc))

    @pyqtSlot()
    def __synchronizeTime(self, quiet=False):
        """
        Private slot to set the time of the connected device to the local
        computer's time.

        @param quiet flag indicating to not show a message
        @type bool
        """
        if self.__device and self.__device.hasTimeCommands():
            try:
                self.__device.syncTime(
                    self.__device.getDeviceType(),
                    hasCPy=self.__device.hasCircuitPython(),
                )

                if not quiet:
                    with EricOverridenCursor():
                        EricMessageBox.information(
                            self,
                            self.tr("Synchronize Time"),
                            self.tr(
                                "<p>The time of the connected device was"
                                " synchronized with the local time.</p>"
                            )
                            + self.__getDeviceTime(),
                        )
            except Exception as exc:
                self.showError("syncTime()", str(exc))

    def __getDeviceTime(self):
        """
        Private method to get a string containing the date and time of the
        connected device.

        @return date and time of the connected device
        @rtype str
        """
        if self.__device and self.__device.hasTimeCommands():
            try:
                dateTimeString = self.__device.getTime()
                try:
                    date, time = dateTimeString.strip().split(None, 1)
                    return self.tr(
                        "<h3>Device Date and Time</h3>"
                        "<table>"
                        "<tr><td><b>Date</b></td><td>{0}</td></tr>"
                        "<tr><td><b>Time</b></td><td>{1}</td></tr>"
                        "</table>"
                    ).format(date, time)
                except ValueError:
                    return self.tr("<h3>Device Date and Time</h3><p>{0}</p>").format(
                        dateTimeString.strip()
                    )
            except Exception as exc:
                self.showError("getTime()", str(exc))
                return ""
        else:
            return ""

    @pyqtSlot()
    def __showDeviceTime(self):
        """
        Private slot to show the date and time of the connected device.
        """
        msg = self.__getDeviceTime()
        if msg:
            EricMessageBox.information(self, self.tr("Device Date and Time"), msg)

    @pyqtSlot()
    def __showLocalTime(self):
        """
        Private slot to show the local date and time.
        """
        localdatetime = time.localtime()
        localdate = time.strftime("%Y-%m-%d", localdatetime)
        localtime = time.strftime("%H:%M:%S", localdatetime)
        EricMessageBox.information(
            self,
            self.tr("Local Date and Time"),
            self.tr(
                "<h3>Local Date and Time</h3>"
                "<table>"
                "<tr><td><b>Date</b></td><td>{0}</td></tr>"
                "<tr><td><b>Time</b></td><td>{1}</td></tr>"
                "</table>"
            ).format(localdate, localtime),
        )

    @pyqtSlot()
    def __showLocalAndDeviceTime(self):
        """
        Private slot to show the local and device time side-by-side.
        """
        localdatetime = time.localtime()
        localdate = time.strftime("%Y-%m-%d", localdatetime)
        localtime = time.strftime("%H:%M:%S", localdatetime)

        try:
            deviceDateTimeString = self.__device.getTime()
            try:
                devicedate, devicetime = deviceDateTimeString.strip().split(None, 1)
                EricMessageBox.information(
                    self,
                    self.tr("Date and Time"),
                    self.tr(
                        "<table>"
                        "<tr><th></th><th>Local Date and Time</th>"
                        "<th>Device Date and Time</th></tr>"
                        "<tr><td><b>Date</b></td>"
                        "<td align='center'>{0}</td>"
                        "<td align='center'>{2}</td></tr>"
                        "<tr><td><b>Time</b></td>"
                        "<td align='center'>{1}</td>"
                        "<td align='center'>{3}</td></tr>"
                        "</table>"
                    ).format(localdate, localtime, devicedate, devicetime),
                )
            except ValueError:
                EricMessageBox.information(
                    self,
                    self.tr("Date and Time"),
                    self.tr(
                        "<table>"
                        "<tr><th>Local Date and Time</th>"
                        "<th>Device Date and Time</th></tr>"
                        "<tr><td align='center'>{0} {1}</td>"
                        "<td align='center'>{2}</td></tr>"
                        "</table>"
                    ).format(localdate, localtime, deviceDateTimeString.strip()),
                )
        except Exception as exc:
            self.showError("getTime()", str(exc))

    def showError(self, method, error):
        """
        Public method to show some error message.

        @param method name of the method the error occured in
        @type str
        @param error error message
        @type str
        """
        with EricOverridenCursor():
            EricMessageBox.warning(
                self,
                self.tr("Error handling device"),
                self.tr(
                    "<p>There was an error communicating with the"
                    " connected device.</p><p>Method: {0}</p>"
                    "<p>Message: {1}</p>"
                ).format(method, error),
            )

    def __mpyCrossAvailable(self):
        """
        Private method to check the availability of mpy-cross.

        @return flag indicating the availability of mpy-cross
        @rtype bool
        """
        available = False
        program = Preferences.getMicroPython("MpyCrossCompiler")
        if not program:
            program = "mpy-cross"
            if FileSystemUtilities.isinpath(program):
                available = True
        else:
            if FileSystemUtilities.isExecutable(program):
                available = True

        return available

    def __crossCompile(self, pythonFile="", title=""):
        """
        Private method to cross compile a Python file to a .mpy file.

        @param pythonFile name of the Python file to be compiled
        @type str
        @param title title for the various dialogs
        @type str
        """
        program = Preferences.getMicroPython("MpyCrossCompiler")
        if not program:
            program = "mpy-cross"
            if not FileSystemUtilities.isinpath(program):
                EricMessageBox.critical(
                    self,
                    title,
                    self.tr(
                        """The MicroPython cross compiler"""
                        """ <b>mpy-cross</b> cannot be found. Ensure it"""
                        """ is in the search path or configure it on"""
                        """ the MicroPython configuration page."""
                    ),
                )
                return

        if not pythonFile:
            defaultDirectory = ""
            aw = ericApp().getObject("ViewManager").activeWindow()
            if aw:
                fn = aw.getFileName()
                if fn:
                    defaultDirectory = os.path.dirname(fn)
            if not defaultDirectory:
                defaultDirectory = (
                    Preferences.getMicroPython("MpyWorkspace")
                    or Preferences.getMultiProject("Workspace")
                    or os.path.expanduser("~")
                )
            pythonFile = EricFileDialog.getOpenFileName(
                self,
                title,
                defaultDirectory,
                self.tr("Python Files (*.py);;All Files (*)"),
            )
            if not pythonFile:
                # user cancelled
                return

        if not os.path.exists(pythonFile):
            EricMessageBox.critical(
                self,
                title,
                self.tr(
                    """The Python file <b>{0}</b> does not exist. Aborting..."""
                ).format(pythonFile),
            )
            return

        compileArgs = [
            pythonFile,
        ]
        dlg = EricProcessDialog(
            self.tr("'mpy-cross' Output"),
            title,
            monospacedFont=Preferences.getEditorOtherFonts("MonospacedFont"),
            encoding=Preferences.getSystem("IOEncoding"),
            parent=self,
        )
        res = dlg.startProcess(program, compileArgs)
        if res:
            dlg.exec()

    @pyqtSlot()
    def __compileFile2Mpy(self):
        """
        Private slot to cross compile a Python file (*.py) to a .mpy file.
        """
        self.__crossCompile(title=self.tr("Compile Python File"))

    @pyqtSlot()
    def __compileEditor2Mpy(self):
        """
        Private slot to cross compile the current editor to a .mpy file.
        """
        aw = ericApp().getObject("ViewManager").activeWindow()
        if aw:
            if not aw.checkDirty():
                # editor still has unsaved changes, abort...
                return

            if not aw.isPyFile():
                # no Python file
                EricMessageBox.critical(
                    self,
                    self.tr("Compile Current Editor"),
                    self.tr(
                        """The current editor does not contain a Python"""
                        """ file. Aborting..."""
                    ),
                )
                return

            self.__crossCompile(
                pythonFile=aw.getFileName(), title=self.tr("Compile Current Editor")
            )

    @pyqtSlot()
    def __showDocumentation(self):
        """
        Private slot to open the documentation URL for the selected device.
        """
        if self.__device is None or not self.__device.hasDocumentationUrl():
            # abort silently
            return

        url = self.__device.getDocumentationUrl()
        ericApp().getObject("UserInterface").launchHelpViewer(url)

    @pyqtSlot()
    def __downloadFirmware(self):
        """
        Private slot to open the firmware download page.
        """
        if self.__device is None or not self.__device.hasFirmwareUrl():
            # abort silently
            return

        self.__device.downloadFirmware()

    def __downloadFromUrl(self, url):
        """
        Private method to open a web browser for the given URL.

        @param url URL to be opened
        @type str
        """
        if self.__device is None:
            # abort silently
            return

        if url:
            ericApp().getObject("UserInterface").launchHelpViewer(url)

    @pyqtSlot()
    def __manageIgnored(self):
        """
        Private slot to manage the list of ignored serial devices.
        """
        from .IgnoredDevicesDialog import IgnoredDevicesDialog

        dlg = IgnoredDevicesDialog(
            Preferences.getMicroPython("IgnoredUnknownDevices"), parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ignoredDevices = dlg.getDevices()
            Preferences.setMicroPython("IgnoredUnknownDevices", ignoredDevices)

    @pyqtSlot()
    def __configure(self):
        """
        Private slot to open the MicroPython configuration page.
        """
        ericApp().getObject("UserInterface").showPreferences("microPythonPage")

    @pyqtSlot()
    def __manageUnknownDevices(self):
        """
        Private slot to manage manually added boards (i.e. those not in the
        list of supported boards).
        """
        from .UnknownDevicesDialog import UnknownDevicesDialog

        dlg = UnknownDevicesDialog(parent=None)
        dlg.exec()

    def __addUnknownDevices(self, devices):
        """
        Private method to add devices to the list of manually added boards.

        @param devices list of not ignored but unknown devices
        @type list of tuple of (int, int, str)
        """
        from .AddEditDevicesDialog import AddEditDevicesDialog

        if len(devices) > 1:
            sdlg = EricListSelectionDialog(
                [d[2] for d in devices],
                title=self.tr("Add Unknown Devices"),
                message=self.tr("Select the devices to be added:"),
                checkBoxSelection=True,
                parent=self,
            )
            if sdlg.exec() == QDialog.DialogCode.Accepted:
                selectedDevices = sdlg.getSelection()
        else:
            selectedDevices = devices[0][2]

        if selectedDevices:
            manualDevices = Preferences.getMicroPython("ManualDevices")
            for vid, pid, description in devices:
                if description in selectedDevices:
                    dlg = AddEditDevicesDialog(vid, pid, description, parent=self)
                    if dlg.exec() == QDialog.DialogCode.Accepted:
                        manualDevices.append(dlg.getDeviceDict())
            Preferences.setMicroPython("ManualDevices", manualDevices)

            # rescan the ports
            self.__populateDeviceTypeComboBox()

    @pyqtSlot()
    def __flashUF2(self):
        """
        Private slot to flash MicroPython/CircuitPython to a device
        support the UF2 bootloader.
        """
        dlg = UF2FlashDialog.UF2FlashDialog(parent=self)
        dlg.exec()

    @pyqtSlot()
    def __convertToUF2(self):
        """
        Private slot to convert a non-UF2 MicroPython firmware file to UF2.
        """
        dlg = ConvertToUF2Dialog.ConvertToUF2Dialog(parent=self)
        dlg.exec()

    @pyqtSlot()
    def __showBuiltinModules(self):
        """
        Private slot to show a list of builtin modules.
        """
        from .ShowModulesDialog import ShowModulesDialog

        if self.__connected:
            try:
                moduleNames = self.__device.getModules()
                dlg = ShowModulesDialog(
                    moduleNames,
                    info=self.tr("Plus any modules on the filesystem."),
                    parent=self,
                )
                dlg.show()
            except Exception as exc:
                self.showError("getModules()", str(exc))

    @pyqtSlot()
    def __installPackage(self, method):
        """
        Private slot to install packages using the given method.

        @param method package management method to be used (one of 'upip' or 'mip')
        @type str
        @exception ValueError raised to indicate an unsupported package management
            method
        """
        from .MipLocalInstaller import MipLocalInstaller
        from .MipPackageDialog import MipPackageDialog

        if method not in ("local_mip", "mip", "upip"):
            raise ValueError(
                "Unsupported method given. Expected 'local_mip', 'mip' or 'upip' but"
                " got {0}."
            ).format(method)

        if method in ("local_mip", "mip"):
            title = self.tr("Install Package")
            dlg = MipPackageDialog(parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                package, version, mpy, target, index = dlg.getData()
                if method == "mip":
                    with EricOverrideCursor():
                        out, err = self.__device.mipInstall(
                            package,
                            index=index,
                            target=target,
                            version=version,
                            mpy=mpy,
                        )
                else:
                    installer = MipLocalInstaller(self.__device)
                    with EricOverrideCursor():
                        ok = installer.installPackage(
                            package,
                            index=index,
                            target=target,
                            version=version,
                            mpy=mpy,
                        )
                    if ok:
                        out = (
                            self.tr("Package '{0}' was installed successfully.")
                            .format(package)
                            .encode("utf-8")
                        )
                        err = b""
                    else:
                        out = b""
                        err = installer.errorString().encode("utf-8")
            else:
                return
        elif method == "upip":
            title = self.tr("Install Packages")
            packagesStr, ok = QInputDialog.getText(
                self,
                self.tr("Install Packages"),
                self.tr("Enter the packages to be installed separated by whitespace:"),
                QLineEdit.EchoMode.Normal,
            )
            if ok and packagesStr:
                packages = packagesStr.split()
                with EricOverrideCursor():
                    out, err = self.__device.upipInstall(packages)
            else:
                return
        else:
            return

        if err:
            self.showError(title, err.decode("utf-8"))
        if out:
            dlg = EricPlainTextDialog(
                title=title, text=out.decode("utf-8"), parent=self
            )
            dlg.exec()

    #######################################################################
    ## Methods below are specific for the MicroPython window.
    #######################################################################

    @pyqtSlot()
    def __quit(self):
        """
        Private slot to quit the main (MicroPython) window.
        """
        self.__ui.close()
