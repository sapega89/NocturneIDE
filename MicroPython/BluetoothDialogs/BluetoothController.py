# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Bluetooth related functionality.
"""

from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QMenu

from eric7.EricWidgets import EricMessageBox


class BluetoothController(QObject):
    """
    Class implementing the Bluetooth related functionality.
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
        Public method to create the Bluetooth submenu.

        @param menu reference to the parent menu
        @type QMenu
        @return reference to the created menu
        @rtype QMenu
        """
        btMenu = QMenu(self.tr("Bluetooth Functions"), menu)
        btMenu.setTearOffEnabled(True)
        btMenu.addAction(self.tr("Show Bluetooth Status"), self.__showBtStatus)
        btMenu.addSeparator()
        btMenu.addAction(self.tr("Perform Scan"), self.__scan)
        btMenu.addSeparator()
        btMenu.addAction(
            self.tr("Activate Bluetooth Interface"),
            lambda: self.__activateInterface(),
        )
        btMenu.addAction(
            self.tr("Deactivate Bluetooth Interface"),
            lambda: self.__deactivateInterface(),
        )

        # add device specific entries (if there are any)
        self.__mpy.getDevice().addDeviceBluetoothEntries(btMenu)

        return btMenu

    @pyqtSlot()
    def __showBtStatus(self):
        """
        Private slot to show the status and some parameters of the Bluetooth interface.
        """
        from .BluetoothStatusDialog import BluetoothStatusDialog

        try:
            status = self.__mpy.getDevice().getBluetoothStatus()
            # status is a list of user labels and associated values

            dlg = BluetoothStatusDialog(status, parent=self.__mpy)
            dlg.exec()
        except Exception as exc:
            self.__mpy.showError("getBluetoothStatus()", str(exc))

    @pyqtSlot()
    def __activateInterface(self):
        """
        Private slot to activate the Bluetooth interface.
        """
        try:
            status = self.__mpy.getDevice().activateBluetoothInterface()
            if status:
                EricMessageBox.information(
                    None,
                    self.tr("Activate Bluetooth Interface"),
                    self.tr("""Bluetooth was activated successfully."""),
                )
            else:
                EricMessageBox.warning(
                    None,
                    self.tr("Activate Bluetooth Interface"),
                    self.tr("""Bluetooth could not be activated."""),
                )
        except Exception as exc:
            self.__mpy.showError("activateBluetoothInterface()", str(exc))

    @pyqtSlot()
    def __deactivateInterface(self):
        """
        Private slot to deactivate the Bluetooth interface.
        """
        try:
            status = self.__mpy.getDevice().deactivateBluetoothInterface()
            if not status:
                EricMessageBox.information(
                    None,
                    self.tr("Deactivate Bluetooth Interface"),
                    self.tr("""Bluetooth was deactivated successfully."""),
                )
            else:
                EricMessageBox.warning(
                    None,
                    self.tr("Deactivate Bluetooth Interface"),
                    self.tr("""Bluetooth could not be deactivated."""),
                )
        except Exception as exc:
            self.__mpy.showError("deactivateBluetoothInterface()", str(exc))

    @pyqtSlot()
    def __scan(self):
        """
        Private slot to scan for Bluetooth devices.
        """
        from .BluetoothScanWindow import BluetoothScanWindow

        win = BluetoothScanWindow(self.__mpy.getDevice(), self.__mpy)
        win.show()
