# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the parameters for a Black formatting run.
"""

import contextlib
import copy
import pathlib

import black
import tomlkit

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QFontMetricsF, QGuiApplication
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem

from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from . import BlackUtilities
from .Ui_BlackConfigurationDialog import Ui_BlackConfigurationDialog


class BlackConfigurationDialog(QDialog, Ui_BlackConfigurationDialog):
    """
    Class implementing a dialog to enter the parameters for a Black formatting run.
    """

    def __init__(self, withProject=True, onlyProject=False, parent=None):
        """
        Constructor

        @param withProject flag indicating to look for project configurations
            (defaults to True)
        @type bool (optional)
        @param onlyProject flag indicating to only look for project configurations
            (defaults to False)
        @type bool (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__project = (
            ericApp().getObject("Project") if (withProject or onlyProject) else None
        )
        self.__onlyProject = onlyProject

        indentTabWidth = (
            QFontMetricsF(self.excludeEdit.font()).horizontalAdvance(" ") * 2
        )
        self.excludeEdit.document().setIndentWidth(indentTabWidth)
        self.excludeEdit.setTabStopDistance(indentTabWidth)

        self.__pyprojectData = {}
        self.__projectData = {}

        self.__tomlButton = self.buttonBox.addButton(
            self.tr("Generate TOML"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__tomlButton.setToolTip(
            self.tr("Place a code snippet for 'pyproject.toml' into the clipboard.")
        )
        self.__tomlButton.clicked.connect(self.__createTomlSnippet)

        # setup the source combobox
        self.sourceComboBox.addItem("", "")
        if self.__project:
            pyprojectPath = (
                pathlib.Path(self.__project.getProjectPath()) / "pyproject.toml"
            )
            if pyprojectPath.exists():
                with contextlib.suppress(tomlkit.exceptions.ParseError, OSError):
                    with pyprojectPath.open("r", encoding="utf-8") as f:
                        data = tomlkit.load(f)
                    config = data.get("tool", {}).get("black", {})
                if config:
                    self.__pyprojectData = {
                        k.replace("--", ""): v for k, v in config.items()
                    }
                    self.sourceComboBox.addItem("pyproject.toml", "pyproject")
            if self.__project.getData("OTHERTOOLSPARMS", "Black") is not None:
                self.__projectData = copy.deepcopy(
                    self.__project.getData("OTHERTOOLSPARMS", "Black")
                )
                self.sourceComboBox.addItem(self.tr("Project File"), "project")
            elif onlyProject:
                self.sourceComboBox.addItem(self.tr("Project File"), "project")
        if not onlyProject:
            self.sourceComboBox.addItem(self.tr("Defaults"), "default")
            self.sourceComboBox.addItem(self.tr("Configuration Below"), "dialog")

        self.__populateTargetVersionsList()

        if self.__projectData:
            source = self.__projectData.get("source", "")
            self.sourceComboBox.setCurrentIndex(self.sourceComboBox.findData(source))
        elif onlyProject:
            self.sourceComboBox.setCurrentIndex(self.sourceComboBox.findData("project"))

    def __populateTargetVersionsList(self):
        """
        Private method to populate the target versions list widget with checkable
        Python version entries.
        """
        targets = [
            (int(t[2]), int(t[3:]), t)
            for t in dir(black.TargetVersion)
            if t.startswith("PY")
        ]
        for target in sorted(targets, reverse=True):
            itm = QListWidgetItem(
                "Python {0}.{1}".format(target[0], target[1]), self.targetVersionsList
            )
            itm.setData(Qt.ItemDataRole.UserRole, target[2])
            itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            itm.setCheckState(Qt.CheckState.Unchecked)

    def __loadConfiguration(self, configurationDict):
        """
        Private method to load the configuration section with data of the given
        dictionary.

        @param configurationDict reference to the data to be loaded
        @type dict
        """
        confDict = copy.deepcopy(BlackUtilities.getDefaultConfiguration())
        confDict.update(configurationDict)

        self.lineLengthSpinBox.setValue(int(confDict["line-length"]))
        self.skipStringNormalCheckBox.setChecked(confDict["skip-string-normalization"])
        self.skipMagicCommaCheckBox.setChecked(confDict["skip-magic-trailing-comma"])
        self.excludeEdit.setPlainText(confDict["extend-exclude"])
        for row in range(self.targetVersionsList.count()):
            itm = self.targetVersionsList.item(row)
            itm.setCheckState(
                Qt.CheckState.Checked
                if itm.data(Qt.ItemDataRole.UserRole).lower()
                in confDict["target-version"]
                else Qt.CheckState.Unchecked
            )

    @pyqtSlot(str)
    def on_sourceComboBox_currentTextChanged(self, selection):
        """
        Private slot to handle the selection of a configuration source.

        @param selection text of the currently selected item
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(selection) or self.__onlyProject
        )

        source = self.sourceComboBox.currentData()
        if source == "pyproject":
            self.__loadConfiguration(self.__pyprojectData)
        elif source == "project":
            self.__loadConfiguration(self.__projectData)
        elif source == "default":
            self.__loadConfiguration(BlackUtilities.getDefaultConfiguration())
        elif source == "dialog":
            # just leave the current entries
            pass

    @pyqtSlot()
    def on_excludeEdit_textChanged(self):
        """
        Private slot to enable the validate button depending on the exclude text.
        """
        self.validateButton.setEnabled(bool(self.excludeEdit.toPlainText()))

    @pyqtSlot()
    def on_validateButton_clicked(self):
        """
        Private slot to validate the entered exclusion regular expression.
        """
        regexp = self.excludeEdit.toPlainText()
        valid, error = BlackUtilities.validateRegExp(regexp)
        if valid:
            EricMessageBox.information(
                self,
                self.tr("Validation"),
                self.tr("""The exclusion expression is valid."""),
            )
        else:
            EricMessageBox.critical(self, self.tr("Validation Error"), error)

    def __getTargetList(self):
        """
        Private method to get the list of checked target versions.

        @return list of target versions
        @rtype list of str
        """
        targets = []
        for row in range(self.targetVersionsList.count()):
            itm = self.targetVersionsList.item(row)
            if itm.checkState() == Qt.CheckState.Checked:
                targets.append(itm.data(Qt.ItemDataRole.UserRole).lower())

        return targets

    @pyqtSlot()
    def __createTomlSnippet(self):
        """
        Private slot to generate a TOML snippet of the current configuration.

        Note: Only non-default values are included in this snippet.

        The code snippet is copied to the clipboard and may be placed inside the
        'pyproject.toml' file.
        """
        doc = tomlkit.document()

        black = tomlkit.table()
        targetList = self.__getTargetList()
        if targetList:
            black["target-version"] = targetList
        black["line-length"] = self.lineLengthSpinBox.value()
        if self.skipStringNormalCheckBox.isChecked():
            black["skip-string-normalization"] = True
        if self.skipMagicCommaCheckBox.isChecked():
            black["skip-magic-trailing-comma"] = True

        excludeRegexp = self.excludeEdit.toPlainText()
        if excludeRegexp and BlackUtilities.validateRegExp(excludeRegexp)[0]:
            black["extend-exclude"] = tomlkit.string(
                "\n{0}\n".format(excludeRegexp.strip()), literal=True, multiline=True
            )

        doc["tool"] = tomlkit.table(is_super_table=True)
        doc["tool"]["black"] = black

        QGuiApplication.clipboard().setText(tomlkit.dumps(doc))

        EricMessageBox.information(
            self,
            self.tr("Create TOML snippet"),
            self.tr(
                """The 'pyproject.toml' snippet was copied to the clipboard"""
                """ successfully."""
            ),
        )

    def getConfiguration(self, saveToProject=False):
        """
        Public method to get the current configuration parameters.

        @param saveToProject flag indicating to save the configuration data in the
            project file (defaults to False)
        @type bool (optional)
        @return dictionary containing the configuration parameters
        @rtype dict
        """
        configuration = BlackUtilities.getDefaultConfiguration()

        configuration["source"] = self.sourceComboBox.currentData()
        configuration["target-version"] = self.__getTargetList()
        configuration["line-length"] = self.lineLengthSpinBox.value()
        configuration["skip-string-normalization"] = (
            self.skipStringNormalCheckBox.isChecked()
        )
        configuration["skip-magic-trailing-comma"] = (
            self.skipMagicCommaCheckBox.isChecked()
        )
        configuration["extend-exclude"] = self.excludeEdit.toPlainText().strip()

        if saveToProject and self.__project:
            self.__project.setData("OTHERTOOLSPARMS", "Black", configuration)

        return configuration
