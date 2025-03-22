# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to configure the CycloneDX SBOM generation.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .Ui_CycloneDXConfigDialog import Ui_CycloneDXConfigDialog


class CycloneDXConfigDialog(QDialog, Ui_CycloneDXConfigDialog):
    """
    Class implementing a dialog to configure the CycloneDX SBOM generation.
    """

    SupportedSchemas = {
        "JSON": [
            (1, 4),
            (1, 3),
            (1, 2),
        ],
        "XML": [
            (1, 4),
            (1, 3),
            (1, 2),
            (1, 1),
            (1, 0),
        ],
    }
    Sources = {
        "pipenv": "Pipfile.lock",
        "poetry": "poetry.lock",
        "requirements": "requirements.txt",
    }
    DefaultFileFormat = "JSON"
    DefaultFileNames = {
        "JSON": "cyclonedx.json",
        "XML": "cyclonedx.xml",
    }

    def __init__(self, environment, parent=None):
        """
        Constructor

        @param environment name of the virtual environment
        @type str
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        if environment == "<project>":
            self.__project = ericApp().getObject("Project")
            self.__defaultDirectory = self.__project.getProjectPath()
        else:
            self.__project = None
            venvManager = ericApp().getObject("VirtualEnvManager")
            self.__defaultDirectory = venvManager.getVirtualenvDirectory(environment)

        self.environmentLabel.setText(environment)

        self.pipenvButton.setEnabled(
            os.path.isfile(
                os.path.join(
                    self.__defaultDirectory, CycloneDXConfigDialog.Sources["pipenv"]
                )
            )
        )
        self.poetryButton.setEnabled(
            os.path.isfile(
                os.path.join(
                    self.__defaultDirectory, CycloneDXConfigDialog.Sources["poetry"]
                )
            )
        )
        self.requirementsButton.setEnabled(
            os.path.isfile(
                os.path.join(
                    self.__defaultDirectory,
                    CycloneDXConfigDialog.Sources["requirements"],
                )
            )
        )

        self.vulnerabilityCheckBox.toggled.connect(
            self.__repopulateSchemaVersionComboBox
        )

        self.filePicker.setMode(EricPathPickerModes.SAVE_FILE_ENSURE_EXTENSION_MODE)
        self.filePicker.setDefaultDirectory(self.__defaultDirectory)

        self.fileFormatComboBox.setCurrentText(CycloneDXConfigDialog.DefaultFileFormat)
        self.on_fileFormatComboBox_currentTextChanged(
            CycloneDXConfigDialog.DefaultFileFormat
        )

        self.__metadata = None
        self.__metadataButton = self.buttonBox.addButton(
            self.tr("Edit Metadata..."), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__metadataButton.clicked.connect(self.__editMetaData)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __repopulateSchemaVersionComboBox(self):
        """
        Private slot to repopulate the schema version selector.
        """
        fileFormat = self.fileFormatComboBox.currentText()
        minSchemaVersion = (1, 4) if self.vulnerabilityCheckBox.isChecked() else (1, 0)
        self.schemaVersionComboBox.clear()
        self.schemaVersionComboBox.addItems(
            "{0}.{1}".format(*f)
            for f in CycloneDXConfigDialog.SupportedSchemas[fileFormat]
            if f >= minSchemaVersion
        )

    @pyqtSlot(str)
    def on_fileFormatComboBox_currentTextChanged(self, fileFormat):
        """
        Private slot to handle the selection of a SBOM file format.

        @param fileFormat selected format
        @type str
        """
        # re-populate the file schema combo box
        self.__repopulateSchemaVersionComboBox()

        # set the file filter
        if fileFormat == "JSON":
            self.filePicker.setFilters(self.tr("JSON Files (*.json);;All Files (*)"))
            suffix = ".json"
        elif fileFormat == "XML":
            self.filePicker.setFilters(self.tr("XML Files (*.xml);;All Files (*)"))
            suffix = ".xml"
        else:
            self.filePicker.setFilters(self.tr("All Files (*)"))
            suffix = ""

        filePath = self.filePicker.path()
        if bool(filePath.name):
            self.filePicker.setPath(filePath.with_suffix(suffix))

    @pyqtSlot()
    def __editMetaData(self):
        """
        Private slot to open a dialog for editing the SBOM metadata.
        """
        from .CycloneDXMetaDataDialog import CycloneDXMetaDataDialog

        # populate a metadata dictionary from project data
        metadata = (
            {
                "Name": self.__project.getProjectName(),
                "Type": "",
                "Version": self.__project.getProjectVersion(),
                "Description": self.__project.getProjectDescription(),
                "AuthorName": self.__project.getProjectAuthor(),
                "AuthorEmail": self.__project.getProjectAuthorEmail(),
                "License": self.__project.getProjectLicense(),
                "Manufacturer": "",
                "Supplier": "",
            }
            if self.__metadata is None and self.__project is not None
            else self.__metadata
        )

        dlg = CycloneDXMetaDataDialog(metadata=metadata, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.__metadata = dlg.getMetaData()

    def getData(self):
        """
        Public method to get the SBOM configuration data.

        @return tuple containing the input source, the input file name, the
            file format, the schema version, the path of the SBOM file to be
            written, a flag indicating to include vulnerability information,
            a flag indicating to include dependency information, a flag indicating
            to generate readable output and a dictionary containing the SBOM meta data
        @rtype tuple of (str, str, str, str, str, bool, bool, bool, dict)
        """
        if self.environmentButton.isChecked():
            inputSource = "environment"
            inputFile = None
        elif self.pipenvButton.isChecked():
            inputSource = "pipenv"
            inputFile = os.path.join(
                self.__defaultDirectory, CycloneDXConfigDialog.Sources["pipenv"]
            )
        elif self.poetryButton.isChecked():
            inputSource = "poetry"
            inputFile = os.path.join(
                self.__defaultDirectory, CycloneDXConfigDialog.Sources["poetry"]
            )
        elif self.requirementsButton.isChecked():
            inputSource = "requirements"
            inputFile = os.path.join(
                self.__defaultDirectory, CycloneDXConfigDialog.Sources["requirements"]
            )
        else:
            # should not happen
            inputSource = None
            inputFile = None

        fileFormat = self.fileFormatComboBox.currentText()
        schemaVersion = self.schemaVersionComboBox.currentText()
        sbomFile = self.filePicker.text()
        if not sbomFile:
            try:
                sbomFile = os.path.join(
                    self.__defaultDirectory,
                    CycloneDXConfigDialog.DefaultFileNames[fileFormat],
                )
            except KeyError:
                # should not happen
                sbomFile = None

        return (
            inputSource,
            inputFile,
            fileFormat,
            schemaVersion,
            sbomFile,
            self.vulnerabilityCheckBox.isChecked(),
            self.dependenciesCheckBox.isChecked(),
            self.readableCheckBox.isChecked(),
            self.__metadata,
        )
