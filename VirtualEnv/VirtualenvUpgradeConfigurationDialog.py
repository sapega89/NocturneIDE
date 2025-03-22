# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the virtual environment upgrade
parameters.
"""

import re

from PyQt6.QtCore import QProcess, QTimer, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities, PythonUtilities

from .Ui_VirtualenvUpgradeConfigurationDialog import (
    Ui_VirtualenvUpgradeConfigurationDialog,
)


class VirtualenvUpgradeConfigurationDialog(
    QDialog, Ui_VirtualenvUpgradeConfigurationDialog
):
    """
    Class implementing a dialog to enter the virtual environment upgrade
    parameters.
    """

    def __init__(self, envName, envPath, parent=None):
        """
        Constructor

        @param envName name of the environment to be upgraded
        @type str
        @param envPath directory of the environment to be upgraded
        @type str
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.pythonExecPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.pythonExecPicker.setWindowTitle(self.tr("Python Interpreter"))
        self.pythonExecPicker.setDefaultDirectory(PythonUtilities.getPythonExecutable())

        self.envNameLabel.setText(envName)
        self.envDirectoryLabel.setText(envPath)

        self.__versionRe = re.compile(r""".*?(\d+\.\d+\.\d+).*""")

        self.upgradePythonCheckBox.toggled.connect(self.__updateOkButton)
        self.upgradeDepsCheckBox.toggled.connect(self.__updateOkButton)
        self.pythonExecPicker.textChanged.connect(self.__updateUpgradeDepsCheckBox)

        self.__updateUpgradeDepsCheckBox()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __getPyvenvVersion(self):
        """
        Private method to determine the version of the venv module.

        @return tuple containing the venv modules version
        @rtype tuple of (int, int, int)
        """
        calls = []
        if self.pythonExecPicker.text():
            calls.append((self.pythonExecPicker.text(), ["-m", "venv"]))
        calls.extend(
            [
                (PythonUtilities.getPythonExecutable(), ["-m", "venv"]),
                ("python3", ["-m", "venv"]),
                ("python", ["-m", "venv"]),
            ]
        )

        proc = QProcess()
        for prog, args in calls:
            proc.start(prog, args)

            if not proc.waitForStarted(5000):
                # try next entry
                continue

            if not proc.waitForFinished(5000):
                # process hangs, kill it and try next entry
                QTimer.singleShot(2000, proc.kill)
                proc.waitForFinished(3000)
                continue

            if proc.exitCode() not in [0, 2]:
                # returned with error code, try next
                continue

            proc.start(prog, ["--version"])
            proc.waitForFinished(5000)
            output = str(
                proc.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            ).strip()
            match = re.match(self.__versionRe, output)
            if match:
                return EricUtilities.versionToTuple(match.group(1))

        return (0, 0, 0)  # dummy version tuple

    @pyqtSlot()
    def __updateUpgradeDepsCheckBox(self):
        """
        Private slot to set the enabled state of the button depending
        on the version of the given Python interpreter.
        """
        pyvenvVersion = self.__getPyvenvVersion()
        if pyvenvVersion >= (3, 9, 0):
            self.upgradeDepsCheckBox.setEnabled(True)
        else:
            self.upgradeDepsCheckBox.setEnabled(False)
            self.upgradeDepsCheckBox.setChecked(False)

    @pyqtSlot()
    def __updateOkButton(self):
        """
        Private slot to set the enabled state of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            self.upgradePythonCheckBox.isChecked()
            or self.upgradeDepsCheckBox.isChecked()
        )

    def getData(self):
        """
        Public method to retrieve the dialog data.

        @return tuple containing the selected python executable, the list of
            arguments and a flag indicating to write a log file
        @rtype tuple of (str, list of str, bool)
        """
        args = ["-m", "venv"]
        if self.upgradePythonCheckBox.isChecked():
            args.append("--upgrade")
        if self.upgradeDepsCheckBox.isChecked():
            args.append("--upgrade-deps")
        args.append(self.envDirectoryLabel.text())

        return (
            FileSystemUtilities.toNativeSeparators(self.pythonExecPicker.text()),
            args,
            self.logCheckBox.isChecked(),
        )
