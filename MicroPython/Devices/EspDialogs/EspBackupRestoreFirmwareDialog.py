# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select the ESP chip type and the backup and
restore parameters.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_EspBackupRestoreFirmwareDialog import Ui_EspBackupRestoreFirmwareDialog


class EspBackupRestoreFirmwareDialog(QDialog, Ui_EspBackupRestoreFirmwareDialog):
    """
    Class implementing a dialog to select the ESP chip type and the backup and
    restore parameters.
    """

    Chips = (
        ("", ""),
        ("ESP32", "esp32"),
        ("ESP32-C3", "esp32c3"),
        ("ESP32-S2", "esp32s2"),
        ("ESP32-S3", "esp32s3"),
        ("ESP8266", "esp8266"),
    )

    FlashModes = [
        ("", ""),
        ("Quad I/O", "qio"),
        ("Quad Output", "qout"),
        ("Dual I/O", "dio"),
        ("Dual Output", "dout"),
    ]

    FlashSizes = {
        "esp32": [
            (" 1 MB", "0x100000"),
            (" 2 MB", "0x200000"),
            (" 4 MB", "0x400000"),
            (" 8 MB", "0x800000"),
            ("16 MB", "0x1000000"),
        ],
        "esp32c3": [
            (" 1 MB", "0x100000"),
            (" 2 MB", "0x200000"),
            (" 4 MB", "0x400000"),
            (" 8 MB", "0x800000"),
            ("16 MB", "0x1000000"),
        ],
        "esp32s2": [
            (" 1 MB", "0x100000"),
            (" 2 MB", "0x200000"),
            (" 4 MB", "0x400000"),
            (" 8 MB", "0x800000"),
            ("16 MB", "0x1000000"),
        ],
        "esp32s3": [
            (" 1 MB", "0x100000"),
            (" 2 MB", "0x200000"),
            (" 4 MB", "0x400000"),
            (" 8 MB", "0x800000"),
            ("16 MB", "0x1000000"),
        ],
        "esp8266": [
            ("256 KB", "0x40000"),
            ("512 KB", "0x80000"),
            (" 1 MB", "0x100000"),
            (" 2 MB", "0x200000"),
            (" 4 MB", "0x400000"),
            (" 8 MB", "0x800000"),
            ("16 MB", "0x1000000"),
        ],
    }

    def __init__(self, backupMode=True, parent=None):
        """
        Constructor

        @param backupMode flag indicating parameters for a firmware backup are
            requested
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__isBackupMode = backupMode

        for text, chip in self.Chips:
            self.espComboBox.addItem(text, chip)

        self.baudRateComboBox.addItems(
            ["74.880", "115.200", "230.400", "460.800", "921.600", "1.500.000"]
        )
        self.baudRateComboBox.setCurrentIndex(3)

        self.firmwarePicker.setFilters(self.tr("Firmware Files (*.img);;All Files (*)"))
        if self.__isBackupMode:
            self.firmwarePicker.setMode(
                EricPathPickerModes.SAVE_FILE_ENSURE_EXTENSION_MODE
            )
            self.sizeInfoLabel.clear()
            self.modeComboBox.setEnabled(False)
            self.modeInfoLabel.setEnabled(False)
            self.setWindowTitle(self.tr("Backup Firmware"))
        else:
            self.firmwarePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
            for text, mode in self.FlashModes:
                self.modeComboBox.addItem(text, mode)
            self.setWindowTitle(self.tr("Restore Firmware"))

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateOkButton(self):
        """
        Private method to update the state of the OK button.
        """
        firmwareFile = self.firmwarePicker.text()
        enable = bool(self.espComboBox.currentText()) and bool(firmwareFile)
        if self.__isBackupMode:
            enable &= bool(self.sizeComboBox.currentText())
        else:
            enable &= os.path.exists(firmwareFile)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    @pyqtSlot(str)
    def on_espComboBox_currentTextChanged(self, chip):
        """
        Private slot to handle the selection of a chip type.

        @param chip selected chip type
        @type str
        """
        selectedSize = self.sizeComboBox.currentText()
        self.sizeComboBox.clear()
        chipType = self.espComboBox.currentData()
        if chipType and chipType in self.FlashSizes:
            self.sizeComboBox.addItem("")
            for text, data in self.FlashSizes[chipType]:
                self.sizeComboBox.addItem(text, data)

            self.sizeComboBox.setCurrentText(selectedSize)

        self.__updateOkButton()

    @pyqtSlot(str)
    def on_sizeComboBox_currentTextChanged(self, _size):
        """
        Private slot handling a change of the selected firmware size.

        @param _size selected size text (unused)
        @type str
        """
        self.__updateOkButton()

    @pyqtSlot(str)
    def on_firmwarePicker_textChanged(self, _firmware):
        """
        Private slot handling a change of the firmware path.

        @param _firmware path to the firmware (unused)
        @type str
        """
        self.__updateOkButton()

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the selected chip type, the firmware size,
            the baud rate or flashing, the flash mode and the path of the
            firmware file
        @rtype tuple of (str, str, str, str, str)
        """
        flashSize = (
            self.sizeComboBox.currentData()
            if self.__isBackupMode
            else self.sizeComboBox.currentText().replace(" ", "")
        )

        return (
            self.espComboBox.currentData(),
            flashSize,
            self.baudRateComboBox.currentText().replace(".", ""),
            self.modeComboBox.currentData(),
            self.firmwarePicker.text(),
        )
