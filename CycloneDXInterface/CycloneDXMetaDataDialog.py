# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit the metadata of the CycloneDX SBOM.
"""

import trove_classifiers

from cyclonedx.model.component import ComponentType
from PyQt6.QtCore import QCoreApplication, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_CycloneDXMetaDataDialog import Ui_CycloneDXMetaDataDialog


class CycloneDXMetaDataDialog(QDialog, Ui_CycloneDXMetaDataDialog):
    """
    Class implementing a dialog to edit the metadata of the CycloneDX SBOM.
    """

    ComponentTypeMapping = {
        ComponentType.APPLICATION: QCoreApplication.translate(
            "CycloneDXMetaDataDialog", "Application"
        ),
        ComponentType.CONTAINER: QCoreApplication.translate(
            "CycloneDXMetaDataDialog", "Container"
        ),
        ComponentType.DEVICE: QCoreApplication.translate(
            "CycloneDXMetaDataDialog", "Device"
        ),
        ComponentType.FILE: QCoreApplication.translate(
            "CycloneDXMetaDataDialog", "File"
        ),
        ComponentType.FIRMWARE: QCoreApplication.translate(
            "CycloneDXMetaDataDialog", "Firmware"
        ),
        ComponentType.FRAMEWORK: QCoreApplication.translate(
            "CycloneDXMetaDataDialog", "Framework"
        ),
        ComponentType.LIBRARY: QCoreApplication.translate(
            "CycloneDXMetaDataDialog", "Library"
        ),
        ComponentType.OPERATING_SYSTEM: QCoreApplication.translate(
            "CycloneDXMetaDataDialog", "Operating System"
        ),
    }

    def __init__(self, metadata=None, parent=None):
        """
        Constructor

        @param metadata dictionary containing metadata to populate the dialog
            (defaults to None)
        @type dict (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__populateComponentTypeSelector()
        self.__populateLicenseSelector()

        if metadata:
            # populate the dialog from given metadata dictionary
            self.nameEdit.setText(metadata["Name"])
            self.versionEdit.setText(metadata["Version"])
            self.descriptionEdit.setPlainText(metadata["Description"])
            self.authorEdit.setText(metadata["AuthorName"])
            self.emailEdit.setText(metadata["AuthorEmail"])
            self.licenseComboBox.setCurrentText(metadata["License"])
            self.manufacturerEdit.setText(metadata["Manufacturer"])
            self.supplierEdit.setText(metadata["Supplier"])
            index = self.typeComboBox.findData(metadata["Type"])
            self.typeComboBox.setCurrentIndex(index)

        self.nameEdit.textChanged.connect(self.__updateOkButton)
        self.typeComboBox.currentTextChanged.connect(self.__updateOkButton)
        self.licenseComboBox.currentTextChanged.connect(self.__updateOkButton)

        self.__updateOkButton()

    def __populateComponentTypeSelector(self):
        """
        Private method to populate the component type selector.
        """
        self.typeComboBox.addItem("", "")
        for componentType, displayStr in sorted(
            CycloneDXMetaDataDialog.ComponentTypeMapping.items(), key=lambda x: x[1]
        ):
            self.typeComboBox.addItem(displayStr, componentType)

    def __populateLicenseSelector(self):
        """
        Private method to populate the license selector with the list of trove
        license types.
        """
        self.licenseComboBox.addItem("")
        self.licenseComboBox.addItems(
            sorted(
                classifier.split("::")[-1].strip()
                for classifier in trove_classifiers.classifiers
                if classifier.startswith("License ::")
            )
        )

    @pyqtSlot()
    def __updateOkButton(self):
        """
        Private slot to update the enabled state of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.nameEdit.text())
            and bool(self.typeComboBox.currentText())
            and bool(self.licenseComboBox.currentText())
        )

    def getMetaData(self):
        """
        Public method to get the entered data.

        @return dictionary containing the metadata.
        @rtype dict
        """
        return {
            "Name": self.nameEdit.text(),
            "Type": self.typeComboBox.currentData(),
            "Version": self.versionEdit.text(),
            "Description": self.descriptionEdit.toPlainText(),
            "AuthorName": self.authorEdit.text(),
            "AuthorEmail": self.emailEdit.text(),
            "License": self.licenseComboBox.currentText(),
            "Manufacturer": self.manufacturerEdit.text(),
            "Supplier": self.supplierEdit.text(),
        }
