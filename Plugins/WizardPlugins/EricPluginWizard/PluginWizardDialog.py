# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the eric plug-in wizard dialog.
"""

from PyQt6.QtCore import QDate, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricApplication import ericApp

from .Templates import (
    apiFilesTemplate,
    apiImportsTemplate,
    clearPrivateDataTemplate,
    configTemplate0,
    configTemplate1,
    configTemplate2,
    configTemplate3,
    exeDisplayDataInfoTemplate,
    exeDisplayDataListTemplate,
    exeDisplayDataTemplate,
    installDependenciesTemplate,
    mainTemplate,
    moduleSetupTemplate,
    onDemandTemplate,
    previewPixmapTemplate,
)
from .Ui_PluginWizardDialog import Ui_PluginWizardDialog


class PluginWizardDialog(QDialog, Ui_PluginWizardDialog):
    """
    Class implementing the eric plug-in wizard dialog.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.dataTabWidget.setCurrentIndex(0)

        self.__okButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.__okButton.setEnabled(False)

        projectOpen = ericApp().getObject("Project").isOpen()
        self.projectButton.setEnabled(projectOpen)

        self.nameEdit.textChanged.connect(self.__enableOkButton)
        self.versionEdit.textChanged.connect(self.__enableOkButton)
        self.authorEdit.textChanged.connect(self.__enableOkButton)
        self.authorEmailEdit.textChanged.connect(self.__enableOkButton)
        self.classNameEdit.textChanged.connect(self.__enableOkButton)
        self.packageNameEdit.textChanged.connect(self.__enableOkButton)
        self.shortDescriptionEdit.textChanged.connect(self.__enableOkButton)
        self.longDescriptionEdit.textChanged.connect(self.__enableOkButton)
        self.preferencesKeyEdit.textChanged.connect(self.__enableOkButton)
        self.configurationGroup.toggled.connect(self.__enableOkButton)
        self.autoActivateCheckBox.toggled.connect(self.__enableOkButton)
        self.pluginTypeCombo.currentIndexChanged.connect(self.__enableOkButton)
        self.pluginTypeNameEdit.textChanged.connect(self.__enableOkButton)

        self.pluginTypeCombo.addItems(["", "viewmanager", "version_control"])

    def __enableOkButton(self):
        """
        Private slot to set the state of the OK button.
        """
        enable = (
            bool(self.nameEdit.text())
            and bool(self.versionEdit.text())
            and bool(self.authorEdit.text())
            and bool(self.authorEmailEdit.text())
            and bool(self.classNameEdit.text())
            and bool(self.packageNameEdit.text())
            and bool(self.shortDescriptionEdit.text())
            and bool(self.longDescriptionEdit.toPlainText())
        )
        if self.configurationGroup.isChecked():
            enable = enable and bool(self.preferencesKeyEdit.text())
        if not self.autoActivateCheckBox.isChecked():
            enable = (
                enable
                and bool(self.pluginTypeCombo.currentText())
                and bool(self.pluginTypeNameEdit.text())
            )

        self.__okButton.setEnabled(enable)

    @pyqtSlot()
    def on_projectButton_clicked(self):
        """
        Private slot to populate some fields with data retrieved from the
        current project.
        """
        project = ericApp().getObject("Project")

        try:
            self.versionEdit.setText(project.getProjectVersion())
            self.authorEdit.setText(project.getProjectAuthor())
            self.authorEmailEdit.setText(project.getProjectAuthorEmail())
            description = project.getProjectDescription()
        except AttributeError:
            self.versionEdit.setText(project.getProjectData(dataKey="VERSION")[0])
            self.authorEdit.setText(project.getProjectData(dataKey="AUTHOR")[0])
            self.authorEmailEdit.setText(project.getProjectData(dataKey="EMAIL")[0])
            description = project.getProjectData(dataKey="DESCRIPTION")[0]

        # summary is max. 55 characters long
        summary = (
            description.split(".", 1)[0].replace("\r", "").replace("\n", "") + "."
        )[:55]
        self.shortDescriptionEdit.setText(summary)
        self.longDescriptionEdit.setPlainText(description)

        # prevent overwriting of entries by disabling the button
        self.projectButton.setEnabled(False)

    def getCode(self):
        """
        Public method to get the source code.

        @return generated code
        @rtype str
        """
        templateData = {
            "year": QDate.currentDate().year(),
            "author": self.authorEdit.text(),
            "email": self.authorEmailEdit.text(),
            "name": self.nameEdit.text(),
            "autoactivate": self.autoActivateCheckBox.isChecked(),
            "deactivateable": self.deactivateableCheckBox.isChecked(),
            "version": self.versionEdit.text(),
            "className": self.classNameEdit.text(),
            "packageName": self.packageNameEdit.text(),
            "shortDescription": self.shortDescriptionEdit.text(),
            "longDescription": '"""\n        """'.join(
                self.longDescriptionEdit.toPlainText().splitlines()
            ),
            "needsRestart": self.restartCheckBox.isChecked(),
            "hasCompiledForms": self.compiledFormsCheckBox.isChecked(),
        }

        if self.configurationGroup.isChecked():
            templateData["config0"] = configTemplate0
            templateData["config1"] = configTemplate1.format(
                className=self.classNameEdit.text()
            )
            templateData["config2"] = configTemplate2.format(
                preferencesKey=self.preferencesKeyEdit.text()
            )
            templateData["config3"] = configTemplate3
        else:
            templateData["config0"] = ""
            templateData["config1"] = ""
            templateData["config2"] = ""
            templateData["config3"] = ""

        if self.autoActivateCheckBox.isChecked():
            templateData["onDemand"] = ""
        else:
            templateData["onDemand"] = onDemandTemplate.format(
                pluginType=self.pluginTypeCombo.currentText(),
                pluginTypename=self.pluginTypeNameEdit.text(),
            )

        if self.pixmapCheckBox.isChecked():
            templateData["preview"] = previewPixmapTemplate
        else:
            templateData["preview"] = ""

        if self.moduleSetupCheckBox.isChecked():
            templateData["modulesetup"] = moduleSetupTemplate
        else:
            templateData["modulesetup"] = ""

        templateData["exeData"] = ""
        if self.exeGroup.isChecked():
            if self.exeRadioButton.isChecked():
                templateData["exeData"] = exeDisplayDataTemplate
            elif self.exeInfoRadioButton.isChecked():
                templateData["exeData"] = exeDisplayDataInfoTemplate
            elif self.exeListRadioButton.isChecked():
                templateData["exeData"] = exeDisplayDataListTemplate

        if self.apiFilesCheckBox.isChecked():
            templateData["apiFiles"] = apiFilesTemplate
            templateData["apiImports"] = apiImportsTemplate
        else:
            templateData["apiFiles"] = ""
            templateData["apiImports"] = ""

        if self.installDependenciesCheckBox.isChecked():
            templateData["installDependencies"] = installDependenciesTemplate
        else:
            templateData["installDependencies"] = ""

        if self.clearPrivateDataCheckBox.isChecked():
            templateData["clearPrivateData"] = clearPrivateDataTemplate
        else:
            templateData["clearPrivateData"] = ""

        return mainTemplate.format(**templateData)

    def packageName(self):
        """
        Public method to retrieve the plug-in package name.

        @return plug-in package name
        @rtype str
        """
        if self.createPackageCheckBox.isChecked():
            return self.packageNameEdit.text()
        else:
            return ""

    @pyqtSlot(str)
    def on_pluginTypeCombo_currentTextChanged(self, txt):
        """
        Private slot to react upon the selection of a plug-in type.

        @param txt selected plug-in type
        @type str
        """
        self.pixmapCheckBox.setChecked(txt == "viewmanager")
