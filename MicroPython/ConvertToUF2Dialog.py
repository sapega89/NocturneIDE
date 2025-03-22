# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to convert a .hex or .bin firmware file to .uf2.
"""

import json
import os

from PyQt6.QtCore import QProcess, QRegularExpression, pyqtSlot
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import QDialog

from eric7 import Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities.PythonUtilities import getPythonExecutable

from .Ui_ConvertToUF2Dialog import Ui_ConvertToUF2Dialog


class ConvertToUF2Dialog(QDialog, Ui_ConvertToUF2Dialog):
    """
    Class implementing a dialog to convert a .hex or .bin firmware file to .uf2.
    """

    FamiliesFile = os.path.join(os.path.dirname(__file__), "Tools", "uf2families.json")
    ConvertScript = os.path.join(os.path.dirname(__file__), "Tools", "uf2conv.py")

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.firmwarePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.firmwarePicker.setFilters(
            self.tr("MicroPython Firmware Files (*.hex *.bin);;All Files (*)")
        )

        self.__validator = QRegularExpressionValidator(
            QRegularExpression(r"[0-9a-fA-F]{0,7}")
        )
        self.addressEdit.setValidator(self.__validator)
        self.addressEdit.setEnabled(False)

        self.__populateFamilyComboBox()

        self.__process = QProcess(self)
        self.__process.readyReadStandardOutput.connect(self.__readOutput)
        self.__process.readyReadStandardError.connect(self.__readError)
        self.__process.finished.connect(self.__conversionFinished)

        self.__updateConvertButton()

    def __populateFamilyComboBox(self):
        """
        Private method to populate the chip family combo box with values read from
        'uf2families.json' file.
        """
        with open(ConvertToUF2Dialog.FamiliesFile, "r") as f:
            families = json.load(f)

        self.familiesComboBox.addItem("", "")
        for family in families:
            self.familiesComboBox.addItem(family["description"], family["id"])
        self.familiesComboBox.model().sort(0)

    def __updateConvertButton(self):
        """
        Private method to set the enabled status of the 'Convert' button.
        """
        self.convertButton.setEnabled(
            bool(self.firmwarePicker.text())
            and bool(self.familiesComboBox.currentText())
        )

    @pyqtSlot(str)
    def on_firmwarePicker_textChanged(self, firmware):
        """
        Private slot handling a change of the firmware file name.

        @param firmware name of the firmware file
        @type str
        """
        self.addressEdit.setEnabled(firmware.lower().endswith(".bin"))
        self.__updateConvertButton()

    @pyqtSlot(str)
    def on_familiesComboBox_currentTextChanged(self, family):
        """
        Private slot handling the selection of a chip family.

        @param family name of the selected chip family
        @type str
        """
        self.__updateConvertButton()

    @pyqtSlot()
    def on_convertButton_clicked(self):
        """
        Private slot activating the conversion process.
        """
        self.outputEdit.clear()

        inputFile = self.firmwarePicker.text()
        outputFile = os.path.splitext(inputFile)[0] + ".uf2"
        args = [
            ConvertToUF2Dialog.ConvertScript,
            "--convert",
            "--family",
            self.familiesComboBox.currentData(),
            "--output",
            outputFile,
        ]
        if inputFile.lower().endswith(".bin"):
            address = self.addressEdit.text()
            if address:
                args.extend(["--base", "0x{0}".format(address)])
        args.append(inputFile)
        python = getPythonExecutable()

        # output the generated command
        self.outputEdit.insertPlainText(
            "{0} {1}\n{2}\n\n".format(python, " ".join(args), "=" * 40)
        )
        self.outputEdit.ensureCursorVisible()

        # start the conversion process
        self.convertButton.setEnabled(False)
        self.__process.start(python, args)

    @pyqtSlot()
    def __readOutput(self):
        """
        Private slot to read the standard output channel of the conversion process.
        """
        out = str(
            self.__process.readAllStandardOutput(),
            Preferences.getSystem("IOEncoding"),
            "replace",
        )
        self.outputEdit.insertPlainText(out)
        self.outputEdit.ensureCursorVisible()

    @pyqtSlot()
    def __readError(self):
        """
        Private slot to read the standard error channel of the conversion process.
        """
        out = str(
            self.__process.readAllStandardError(),
            Preferences.getSystem("IOEncoding"),
            "replace",
        )
        self.outputEdit.insertPlainText(self.tr("--- ERROR ---\n"))
        self.outputEdit.insertPlainText(out)
        self.outputEdit.ensureCursorVisible()

    @pyqtSlot(int, QProcess.ExitStatus)
    def __conversionFinished(self, _exitCode, _exitStatus):
        """
        Private slot handling the end of the conversion process.

        @param _exitCode exit code of the process (unused)
        @type int
        @param _exitStatus exit status of the process (unused)
        @type QProcess.ExitStatus
        """
        self.convertButton.setEnabled(True)
