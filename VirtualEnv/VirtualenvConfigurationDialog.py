# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the parameters for the
virtual environment.
"""

import os
import re

from PyQt6.QtCore import QProcess, QTimer, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import CondaInterface, Preferences
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import PythonUtilities

from .Ui_VirtualenvConfigurationDialog import Ui_VirtualenvConfigurationDialog


class VirtualenvConfigurationDialog(QDialog, Ui_VirtualenvConfigurationDialog):
    """
    Class implementing a dialog to enter the parameters for the
    virtual environment.
    """

    def __init__(self, baseDir="", parent=None):
        """
        Constructor

        @param baseDir base directory for the virtual environments
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        if not baseDir:
            baseDir = os.path.expanduser("~")
        self.__envBaseDir = baseDir

        self.targetDirectoryPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.targetDirectoryPicker.setWindowTitle(
            self.tr("Virtualenv Target Directory")
        )
        self.targetDirectoryPicker.setText(baseDir)
        self.targetDirectoryPicker.setDefaultDirectory(baseDir)

        self.extraSearchPathPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.extraSearchPathPicker.setWindowTitle(
            self.tr("Extra Search Path for setuptools/pip")
        )
        self.extraSearchPathPicker.setDefaultDirectory(os.path.expanduser("~"))

        self.pythonExecPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.pythonExecPicker.setWindowTitle(self.tr("Python Interpreter"))
        self.pythonExecPicker.setDefaultDirectory(PythonUtilities.getPythonExecutable())

        self.condaTargetDirectoryPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.condaTargetDirectoryPicker.setWindowTitle(
            self.tr("Conda Environment Location")
        )
        self.condaTargetDirectoryPicker.setDefaultDirectory(os.path.expanduser("~"))

        self.condaCloneDirectoryPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.condaCloneDirectoryPicker.setWindowTitle(
            self.tr("Conda Environment Location")
        )
        self.condaCloneDirectoryPicker.setDefaultDirectory(os.path.expanduser("~"))

        self.condaRequirementsFilePicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.condaRequirementsFilePicker.setWindowTitle(
            self.tr("Conda Requirements File")
        )
        self.condaRequirementsFilePicker.setDefaultDirectory(os.path.expanduser("~"))
        self.condaRequirementsFilePicker.setFilters(
            self.tr("Text Files (*.txt);;All Files (*)")
        )

        self.__versionRe = re.compile(r""".*?(\d+\.\d+\.\d+).*""")

        self.__virtualenvFound = False
        self.__pyvenvFound = False
        self.__condaFound = False
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.__mandatoryStyleSheet = (
            "QLineEdit {border: 2px solid; border-color: #dd8888}"
            if ericApp().usesDarkPalette()
            else "QLineEdit {border: 2px solid; border-color: #800000}"
        )
        self.targetDirectoryPicker.setStyleSheet(self.__mandatoryStyleSheet)
        self.nameEdit.setStyleSheet(self.__mandatoryStyleSheet)
        self.condaTargetDirectoryPicker.setStyleSheet(self.__mandatoryStyleSheet)
        self.condaNameEdit.setStyleSheet(self.__mandatoryStyleSheet)

        self.__setVirtualenvVersion()
        self.__setPyvenvVersion()
        self.__setCondaVersion()
        if self.__pyvenvFound:
            self.pyvenvButton.setChecked(True)
        elif self.__virtualenvFound:
            self.virtualenvButton.setChecked(True)
        elif self.__condaFound:
            self.condaButton.setChecked(True)

        self.condaInsecureCheckBox.setEnabled(
            CondaInterface.condaVersion() >= (4, 3, 18)
        )

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateOK(self):
        """
        Private method to update the enabled status of the OK button.
        """
        if self.virtualenvButton.isChecked() or self.pyvenvButton.isChecked():
            enable = (
                (self.__virtualenvFound or self.__pyvenvFound)
                and bool(self.targetDirectoryPicker.text())
                and bool(self.nameEdit.text())
            )
            enable &= self.targetDirectoryPicker.text() != self.__envBaseDir
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)
        elif self.condaButton.isChecked():
            enable = bool(self.condaNameEdit.text()) or bool(
                self.condaTargetDirectoryPicker.text()
            )
            if self.condaSpecialsGroup.isChecked():
                if self.condaCloneButton.isChecked():
                    enable &= bool(self.condaCloneNameEdit.text()) or bool(
                        self.condaCloneDirectoryPicker.text()
                    )
                elif self.condaRequirementsButton.isChecked():
                    enable &= bool(self.condaRequirementsFilePicker.text())
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)
        else:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def __updateUi(self):
        """
        Private method to update the UI depending on the selected
        virtual environment creator (virtualenv or pyvenv).
        """
        # venv page
        enable = self.virtualenvButton.isChecked()
        self.extraSearchPathLabel.setEnabled(enable)
        self.extraSearchPathPicker.setEnabled(enable)
        self.promptPrefixLabel.setEnabled(enable)
        self.promptPrefixEdit.setEnabled(enable)
        self.verbosityLabel.setEnabled(enable)
        self.verbositySpinBox.setEnabled(enable)
        self.versionLabel.setEnabled(enable)
        self.versionComboBox.setEnabled(enable)
        self.unzipCheckBox.setEnabled(enable)
        self.noSetuptoolsCheckBox.setEnabled(enable)
        self.symlinkCheckBox.setEnabled(not enable)
        self.upgradeCheckBox.setEnabled(not enable)

        # conda page
        enable = not self.condaSpecialsGroup.isChecked()
        self.condaPackagesEdit.setEnabled(enable)
        self.condaPythonEdit.setEnabled(enable)
        self.condaInsecureCheckBox.setEnabled(
            enable and CondaInterface.condaVersion() >= (4, 3, 18)
        )
        self.condaDryrunCheckBox.setEnabled(enable)

        # select page
        if self.condaButton.isChecked():
            self.venvStack.setCurrentWidget(self.condaPage)
        else:
            self.venvStack.setCurrentWidget(self.venvPage)

    @pyqtSlot(str)
    def on_nameEdit_textChanged(self, _txt):
        """
        Private slot handling a change of the virtual environment name.

        @param _txt name of the virtual environment (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_targetDirectoryPicker_textChanged(self, _txt):
        """
        Private slot handling a change of the target directory.

        @param _txt target directory (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_pythonExecPicker_textChanged(self, _txt):
        """
        Private slot to react to a change of the Python executable.

        @param _txt contents of the picker's line edit (unused)
        @type str
        """
        self.__setVirtualenvVersion()
        self.__setPyvenvVersion()
        self.__updateOK()

    @pyqtSlot(bool)
    def on_virtualenvButton_toggled(self, _checked):
        """
        Private slot to react to the selection of 'virtualenv'.

        @param _checked state of the checkbox (unused)
        @type bool
        """
        self.__updateUi()

    @pyqtSlot(bool)
    def on_pyvenvButton_toggled(self, _checked):
        """
        Private slot to react to the selection of 'pyvenv'.

        @param _checked state of the checkbox (unused)
        @type bool
        """
        self.__updateUi()

    @pyqtSlot(bool)
    def on_condaButton_toggled(self, _checked):
        """
        Private slot to react to the selection of 'conda'.

        @param _checked state of the checkbox (unused)
        @type bool
        """
        self.__updateUi()

    @pyqtSlot(str)
    def on_condaNameEdit_textChanged(self, _txt):
        """
        Private slot handling a change of the conda environment name.

        @param _txt environment name (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_condaTargetDirectoryPicker_textChanged(self, _txt):
        """
        Private slot handling a change of the conda target directory.

        @param _txt target directory (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot()
    def on_condaSpecialsGroup_clicked(self):
        """
        Private slot handling the selection of the specials group.
        """
        self.__updateOK()
        self.__updateUi()

    @pyqtSlot(str)
    def on_condaCloneNameEdit_textChanged(self, _txt):
        """
        Private slot handling a change of the conda source environment name.

        @param _txt name of the environment to be cloned (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_condaCloneDirectoryPicker_textChanged(self, _txt):
        """
        Private slot handling a change of the cloned from directory.

        @param _txt target directory (unused)
        @type str
        """
        self.__updateOK()

    @pyqtSlot()
    def on_condaCloneButton_clicked(self):
        """
        Private slot handling the selection of the clone button.
        """
        self.__updateOK()

    @pyqtSlot()
    def on_condaRequirementsButton_clicked(self):
        """
        Private slot handling the selection of the requirements button.
        """
        self.__updateOK()

    @pyqtSlot(str)
    def on_condaRequirementsFilePicker_textChanged(self, _txt):
        """
        Private slot handling a change of the requirements file entry.

        @param _txt current text of the requirements file entry (unused)
        @type str
        """
        self.__updateOK()

    def __setVirtualenvVersion(self):
        """
        Private method to determine the virtualenv version and set the
        respective label.
        """
        calls = []
        if self.pythonExecPicker.text():
            calls.append(
                (self.pythonExecPicker.text(), ["-m", "virtualenv", "--version"])
            )
        calls.extend(
            [
                (
                    PythonUtilities.getPythonExecutable(),
                    ["-m", "virtualenv", "--version"],
                ),
                ("virtualenv", ["--version"]),
            ]
        )

        proc = QProcess()
        for prog, args in calls:
            proc.start(prog, args)

            if not proc.waitForStarted(5000):
                # try next entry
                continue

            if not proc.waitForFinished(5000):
                # process hangs, kill it
                QTimer.singleShot(2000, proc.kill)
                proc.waitForFinished(3000)
                version = self.tr("<virtualenv did not finish within 5s.>")
                self.__virtualenvFound = False
                break

            if proc.exitCode() != 0:
                # returned with error code, try next
                continue

            output = str(
                proc.readAllStandardOutput(),
                Preferences.getSystem("IOEncoding"),
                "replace",
            ).strip()
            match = re.match(self.__versionRe, output)
            if match:
                self.__virtualenvFound = True
                version = match.group(1)
                break
        else:
            self.__virtualenvFound = False
            version = self.tr("<No suitable virtualenv found.>")

        self.virtualenvButton.setText(
            self.tr("virtualenv Version: {0}".format(version))
        )
        self.virtualenvButton.setEnabled(self.__virtualenvFound)
        if not self.__virtualenvFound:
            self.virtualenvButton.setChecked(False)

    def __setPyvenvVersion(self):
        """
        Private method to determine the pyvenv version and set the respective
        label.
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
                # process hangs, kill it
                QTimer.singleShot(2000, proc.kill)
                proc.waitForFinished(3000)
                version = self.tr("<pyvenv did not finish within 5s.>")
                self.__pyvenvFound = False
                break

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
                self.__pyvenvFound = True
                version = match.group(1)
                break
        else:
            self.__pyvenvFound = False
            version = self.tr("<No suitable pyvenv found.>")

        self.pyvenvButton.setText(self.tr("pyvenv Version: {0}".format(version)))
        self.pyvenvButton.setEnabled(self.__pyvenvFound)
        if not self.__pyvenvFound:
            self.pyvenvButton.setChecked(False)

    def __setCondaVersion(self):
        """
        Private method to determine the conda version and set the respective
        label.
        """
        self.__condaFound = bool(CondaInterface.condaVersion())
        self.condaButton.setText(
            self.tr("conda Version: {0}".format(CondaInterface.condaVersionStr()))
        )
        self.condaButton.setEnabled(self.__condaFound)
        if not self.__condaFound:
            self.condaButton.setChecked(False)

    def __generateTargetDir(self):
        """
        Private method to generate a valid target directory path.

        @return target directory path
        @rtype str
        """
        targetDirectory = self.targetDirectoryPicker.text()
        if not os.path.isabs(targetDirectory):
            targetDirectory = os.path.join(os.path.expanduser("~"), targetDirectory)
        return targetDirectory

    def __generateArguments(self):
        """
        Private method to generate the process arguments.

        @return process arguments
        @rtype list of str
        """
        args = []
        if self.condaButton.isChecked():
            if bool(self.condaNameEdit.text()):
                args.extend(["--name", self.condaNameEdit.text()])
            if bool(self.condaTargetDirectoryPicker.text()):
                args.extend(["--prefix", self.condaTargetDirectoryPicker.text()])
            if self.condaSpecialsGroup.isChecked():
                if self.condaCloneButton.isChecked():
                    if bool(self.condaCloneNameEdit.text()):
                        args.extend(["--clone", self.condaCloneNameEdit.text()])
                    elif bool(self.condaCloneDirectoryPicker.text()):
                        args.extend(["--clone", self.condaCloneDirectoryPicker.text()])
                elif self.condaRequirementsButton.isChecked():
                    args.extend(["--file", self.condaRequirementsFilePicker.text()])
            if self.condaInsecureCheckBox.isChecked():
                args.append("--insecure")
            if self.condaDryrunCheckBox.isChecked():
                args.append("--dry-run")
            if not self.condaSpecialsGroup.isChecked():
                if bool(self.condaPythonEdit.text()):
                    args.append("python={0}".format(self.condaPythonEdit.text()))
                if bool(self.condaPackagesEdit.text()):
                    args.extend(self.condaPackagesEdit.text().split())
        else:
            if self.virtualenvButton.isChecked():
                if self.extraSearchPathPicker.text():
                    args.append(
                        "--extra-search-dir={0}".format(
                            self.extraSearchPathPicker.text()
                        )
                    )
                if self.promptPrefixEdit.text():
                    args.append(
                        "--prompt={0}".format(
                            self.promptPrefixEdit.text().replace(" ", "_")
                        )
                    )
                if self.pythonExecPicker.text():
                    args.append("--python={0}".format(self.pythonExecPicker.text()))
                elif self.versionComboBox.currentText():
                    args.append(
                        "--python=python{0}".format(self.versionComboBox.currentText())
                    )
                if self.verbositySpinBox.value() == 1:
                    args.append("--verbose")
                elif self.verbositySpinBox.value() == -1:
                    args.append("--quiet")
                if self.clearCheckBox.isChecked():
                    args.append("--clear")
                if self.systemCheckBox.isChecked():
                    args.append("--system-site-packages")
                if self.unzipCheckBox.isChecked():
                    args.append("--unzip-setuptools")
                if self.noSetuptoolsCheckBox.isChecked():
                    args.append("--no-setuptools")
                if self.noPipCcheckBox.isChecked():
                    args.append("--no-pip")
                if self.copyCheckBox.isChecked():
                    args.append("--always-copy")
            elif self.pyvenvButton.isChecked():
                if self.clearCheckBox.isChecked():
                    args.append("--clear")
                if self.systemCheckBox.isChecked():
                    args.append("--system-site-packages")
                if self.noPipCcheckBox.isChecked():
                    args.append("--without-pip")
                if self.copyCheckBox.isChecked():
                    args.append("--copies")
                if self.symlinkCheckBox.isChecked():
                    args.append("--symlinks")
                if self.upgradeCheckBox.isChecked():
                    args.append("--upgrade")
            targetDirectory = self.__generateTargetDir()
            args.append(targetDirectory)

        return args

    def getData(self):
        """
        Public method to retrieve the dialog data.

        @return dictionary containing the data for the two environment
            variants. The keys for both variants are 'arguments' containing the
            command line arguments, 'logicalName' containing the environment
            name to be used with the virtual env manager and 'envType'
            containing the environment type (virtualenv, pyvenv or conda). The
            virtualenv/pyvenv specific keys are 'openTarget' containg a flag to
            open the target directory after creation, 'createLog' containing a
            flag to write a log file, 'createScript' containing a flag to write
            a script, 'targetDirectory' containing the target directory and
            'pythonExe' containing the Python interpreter to be used. The
            conda specific key is 'command' giving the conda command to be
            executed (always 'create').
        @rtype dict
        """
        args = self.__generateArguments()
        resultDict = {
            "arguments": args,
            "logicalName": self.nameEdit.text(),
        }
        if self.condaButton.isChecked():
            resultDict.update(
                {
                    "envType": "conda",
                    "command": "create",
                }
            )
        else:
            resultDict.update(
                {
                    "envType": (
                        "pyvenv" if self.pyvenvButton.isChecked() else "virtualenv"
                    ),
                    "openTarget": self.openCheckBox.isChecked(),
                    "createLog": self.logCheckBox.isChecked(),
                    "createScript": self.scriptCheckBox.isChecked(),
                    "targetDirectory": self.__generateTargetDir(),
                    "pythonExe": self.pythonExecPicker.text(),
                }
            )

        return resultDict
