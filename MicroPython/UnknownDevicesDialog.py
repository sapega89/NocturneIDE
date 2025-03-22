# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to manage the list of unknown devices.
"""

from PyQt6.QtCore import Qt, QUrl, QUrlQuery, pyqtSlot
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QListWidgetItem

from eric7 import Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.UI.Info import BugAddress

from .Ui_UnknownDevicesDialog import Ui_UnknownDevicesDialog


class UnknownDevicesDialog(QDialog, Ui_UnknownDevicesDialog):
    """
    Class implementing a dialog to manage the list of unknown devices.
    """

    DeviceDataRole = Qt.ItemDataRole.UserRole
    ModifiedRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__loadDevices()

    def __loadDevices(self):
        """
        Private method to load the list of unknown devices.
        """
        self.deviceList.clear()

        devices = Preferences.getMicroPython("ManualDevices")
        for device in devices:
            itm = QListWidgetItem(
                self.tr("{0} (0x{1:04x}/0x{2:04x})", "description, VID, PID").format(
                    device["description"], device["vid"], device["pid"]
                ),
                self.deviceList,
            )
            itm.setData(self.DeviceDataRole, device)
            itm.setData(self.ModifiedRole, False)

        self.__initialDeviceCount = self.deviceList.count()

        self.__checkButtons()

    def __isDirty(self):
        """
        Private method to check, if the dialog contains unsaved data.

        @return flag indicating the presence of unsaved data
        @rtype bool
        """
        dirty = False
        for row in range(self.deviceList.count()):
            dirty |= self.deviceList.item(row).data(self.ModifiedRole)
        dirty |= self.deviceList.count() != self.__initialDeviceCount
        return dirty

    def __editItem(self, item):
        """
        Private method to edit the given item.

        @param item reference to the item to be edited
        @type QListWidgetItem
        """
        from .AddEditDevicesDialog import AddEditDevicesDialog

        if item is None:
            # play it safe
            return

        dlg = AddEditDevicesDialog(
            deviceData=item.data(self.DeviceDataRole), parent=self
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            deviceDict = dlg.getDeviceDict()
            item.setData(self.DeviceDataRole, deviceDict)
            item.setData(self.ModifiedRole, True)

            item.setText(
                self.tr("{0} (*)", "list entry is modified").format(item.text())
            )

    def __saveDeviceData(self):
        """
        Private method to save the device data.

        @return flag indicating a successful save
        @rtype bool
        """
        devices = []

        for row in range(self.deviceList.count()):
            devices.append(self.deviceList.item(row).data(self.DeviceDataRole))
        Preferences.setMicroPython("ManualDevices", devices)

        return True

    @pyqtSlot()
    def __checkButtons(self):
        """
        Private slot to set the enabled state of the buttons.
        """
        selectedItemsCount = len(self.deviceList.selectedItems())
        self.editButton.setEnabled(selectedItemsCount == 1)
        self.deleteButton.setEnabled(selectedItemsCount >= 1)

    @pyqtSlot(QListWidgetItem)
    def on_deviceList_itemActivated(self, item):
        """
        Private slot to edit the data of the activated item.

        @param item reference to the activated item
        @type QListWidgetItem
        """
        self.__editItem(item)

    @pyqtSlot()
    def on_deviceList_itemSelectionChanged(self):
        """
        Private slot to handle a change of selected items.
        """
        self.__checkButtons()

    @pyqtSlot()
    def on_editButton_clicked(self):
        """
        Private slot to edit the selected item.
        """
        itm = self.deviceList.selectedItems()[0]
        self.__editItem(itm)

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to delete the selected entries.
        """
        unsaved = False
        for itm in self.deviceList.selectedItems():
            unsaved |= itm.data(self.ModifiedRole)
        if unsaved:
            ok = EricMessageBox.yesNo(
                self,
                self.tr("Delete Unknown Devices"),
                self.tr(
                    "The selected entries contain some with modified"
                    " data. Shall they really be deleted?"
                ),
            )
            if not ok:
                return

        for itm in self.deviceList.selectedItems():
            self.deviceList.takeItem(self.deviceList.row(itm))
            del itm

    @pyqtSlot()
    def on_deleteAllButton_clicked(self):
        """
        Private slot to delete all devices.
        """
        if self.__isDirty():
            ok = EricMessageBox.yesNo(
                self,
                self.tr("Delete Unknown Devices"),
                self.tr(
                    "The list contains some devices with modified"
                    " data. Shall they really be deleted?"
                ),
            )
            if not ok:
                return

        self.deviceList.clear()

    @pyqtSlot()
    def on_restoreButton_clicked(self):
        """
        Private slot to restore the list of unknown devices.
        """
        if self.__isDirty():
            ok = EricMessageBox.yesNo(
                self,
                self.tr("Restore Unknown Devices"),
                self.tr(
                    "Restoring the list of unknown devices will overwrite"
                    " all changes made. Do you really want to restore the"
                    " list?"
                ),
            )
            if not ok:
                return

        self.__loadDevices()

    @pyqtSlot()
    def on_reportButton_clicked(self):
        """
        Private slot to report the data of all boards to the eric-bugs email
        address.
        """
        if self.deviceList.count() > 0:
            bodyList = [
                "These are my MicroPython devices not yet known by eric."
                " Please add them.",
                "",
            ]

            for row in range(self.deviceList.count()):
                deviceDict = self.deviceList.item(row).data(self.DeviceDataRole)
                bodyList += [
                    "Board #{0}:".format(row),
                    "  VID: {0}".format(deviceDict["vid"]),
                    "  PID: {0}".format(deviceDict["pid"]),
                    "  Description: {0}".format(deviceDict["description"]),
                    "  Device Type: {0}".format(deviceDict["type"]),
                    "  Data Volume: {0}".format(deviceDict["data_volume"]),
                    "  Flash Volume: {0}".format(deviceDict["flash_volume"]),
                    "",
                ]

            urlQuery = QUrlQuery()
            urlQuery.addQueryItem("subject", "Unsupported MicroPython Devices")
            urlQuery.addQueryItem("body", "\r\n".join(bodyList))

            url = QUrl("mailto:{0}".format(BugAddress))
            url.setQuery(urlQuery)

            QDesktopServices.openUrl(url)

    @pyqtSlot()
    def on_buttonBox_accepted(self):
        """
        Private slot to handle the OK button press.

        This action saves the edited list to the preferences store.
        """
        self.__saveDeviceData()
        self.accept()

    @pyqtSlot()
    def on_buttonBox_rejected(self):
        """
        Private slot handling the cancellation of the dialog.
        """
        if self.__isDirty():
            ok = EricMessageBox.okToClearData(
                self,
                self.tr("Unsaved Data"),
                self.tr("""The list of devices contains some with modified data."""),
                self.__saveDeviceData,
            )
            if not ok:
                return

        self.reject()
