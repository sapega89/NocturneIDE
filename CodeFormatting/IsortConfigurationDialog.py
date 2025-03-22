# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the parameters for an isort formatting run.
"""

import contextlib
import copy
import pathlib

import tomlkit

from isort import Config
from isort.profiles import profiles
from isort.settings import VALID_PY_TARGETS
from isort.wrap_modes import WrapModes
from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from .Ui_IsortConfigurationDialog import Ui_IsortConfigurationDialog


class IsortConfigurationDialog(QDialog, Ui_IsortConfigurationDialog):
    """
    Class implementing a dialog to enter the parameters for an isort formatting run.
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

        self.profileComboBox.lineEdit().setClearButtonEnabled(True)

        self.__parameterWidgetMapping = {
            "profile": self.profileComboBox,
            "py_version": self.pythonComboBox,
            "multi_line_output": self.multiLineComboBox,
            "sort_order": self.sortOrderComboBox,
            "supported_extensions": self.extensionsEdit,
            "line_length": self.lineLengthSpinBox,
            "lines_before_imports": self.linesBeforeImportsSpinBox,
            "lines_after_imports": self.linesAfterImportsSpinBox,
            "lines_between_sections": self.linesBetweenSectionsSpinBox,
            "lines_between_types": self.linesBetweenTypesSpinBox,
            "include_trailing_comma": self.trailingCommaCheckBox,
            "use_parentheses": self.parenthesesCheckBox,
            "combine_as_imports": self.combineAsCheckBox,
            "sections": self.sectionsEdit,
            "extend_skip_glob": self.excludeEdit,
            "case_sensitive": self.sortCaseSensitiveCheckBox,
            "force_sort_within_sections": self.sortIgnoreStyleCheckBox,
            "from_first": self.sortFromFirstCheckBox,
            "known_first_party": self.firstPartyEdit,
        }

        self.__project = (
            ericApp().getObject("Project") if (withProject or onlyProject) else None
        )
        self.__onlyProject = onlyProject

        self.__pyprojectData = {}
        self.__projectData = {}

        self.__defaultConfig = Config()

        self.__tomlButton = self.buttonBox.addButton(
            self.tr("Generate TOML"), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__tomlButton.setToolTip(
            self.tr("Place a code snippet for 'pyproject.toml' into the clipboard.")
        )
        self.__tomlButton.clicked.connect(self.__createTomlSnippet)

        self.profileComboBox.addItem("")
        self.profileComboBox.addItems(sorted(profiles))

        self.pythonComboBox.addItem("", "")
        self.pythonComboBox.addItem(self.tr("All Versions"), "all")
        for pyTarget in VALID_PY_TARGETS:
            if pyTarget.startswith("3"):
                self.pythonComboBox.addItem(
                    (
                        self.tr("Python {0}").format(pyTarget)
                        if len(pyTarget) == 1
                        else self.tr("Python {0}.{1}").format(pyTarget[0], pyTarget[1:])
                    ),
                    pyTarget,
                )

        self.sortOrderComboBox.addItem("", "")
        self.sortOrderComboBox.addItem("Natural", "natural")
        self.sortOrderComboBox.addItem("Native Python", "native")

        self.__populateMultiLineComboBox()

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
                    config = data.get("tool", {}).get("isort", {})
                if config:
                    self.__pyprojectData = {
                        k.replace("--", ""): v for k, v in config.items()
                    }
                    self.sourceComboBox.addItem("pyproject.toml", "pyproject")
            if self.__project.getData("OTHERTOOLSPARMS", "isort") is not None:
                self.__projectData = copy.deepcopy(
                    self.__project.getData("OTHERTOOLSPARMS", "isort")
                )
                self.sourceComboBox.addItem(self.tr("Project File"), "project")
            elif onlyProject:
                self.sourceComboBox.addItem(self.tr("Project File"), "project")
        if not onlyProject:
            self.sourceComboBox.addItem(self.tr("Defaults"), "default")
            self.sourceComboBox.addItem(self.tr("Configuration Below"), "dialog")

        if self.__projectData:
            source = self.__projectData.get("config_source", "")
            self.sourceComboBox.setCurrentIndex(self.sourceComboBox.findData(source))
        elif onlyProject:
            self.sourceComboBox.setCurrentIndex(self.sourceComboBox.findData("project"))

    def __populateMultiLineComboBox(self):
        """
        Private method to populate the multi line output selector.
        """
        self.multiLineComboBox.addItem("", -1)
        for entry, wrapMode in (
            (self.tr("Grid"), WrapModes.GRID),
            (self.tr("Vertical"), WrapModes.VERTICAL),
            (self.tr("Hanging Indent"), WrapModes.HANGING_INDENT),
            (
                self.tr("Vertical Hanging Indent"),
                WrapModes.VERTICAL_HANGING_INDENT,
            ),
            (self.tr("Hanging Grid"), WrapModes.VERTICAL_GRID),
            (self.tr("Hanging Grid Grouped"), WrapModes.VERTICAL_GRID_GROUPED),
            (self.tr("NOQA"), WrapModes.NOQA),
            (
                self.tr("Vertical Hanging Indent Bracket"),
                WrapModes.VERTICAL_HANGING_INDENT_BRACKET,
            ),
            (
                self.tr("Vertical Prefix From Module Import"),
                WrapModes.VERTICAL_PREFIX_FROM_MODULE_IMPORT,
            ),
            (
                self.tr("Hanging Indent With Parentheses"),
                WrapModes.HANGING_INDENT_WITH_PARENTHESES,
            ),
            (self.tr("Backslash Grid"), WrapModes.BACKSLASH_GRID),
        ):
            self.multiLineComboBox.addItem(entry, wrapMode.value)

    def __loadConfiguration(self, confDict):
        """
        Private method to load the configuration section with data of the given
        dictionary.

        Note: Default values will be loaded for missing parameters.

        @param confDict reference to the data to be loaded
        @type dict
        """
        self.pythonComboBox.setCurrentIndex(
            self.pythonComboBox.findData(
                str(confDict["py_version"])
                if "py_version" in confDict
                else self.__defaultConfig.py_version.replace("py", "")
            )
        )
        self.multiLineComboBox.setCurrentIndex(
            self.multiLineComboBox.findData(
                int(confDict["multi_line_output"])
                if "multi_line_output" in confDict
                else self.__defaultConfig.multi_line_output.value
            )
        )
        self.sortOrderComboBox.setCurrentIndex(
            self.sortOrderComboBox.findData(
                str(confDict["sort_order"])
                if "sort_order" in confDict
                else self.__defaultConfig.sort_order
            )
        )
        self.extensionsEdit.setText(
            " ".join(
                confDict["supported_extensions"]
                if "supported_extensions" in confDict
                else self.__defaultConfig.supported_extensions
            )
        )
        for parameter in (
            "line_length",
            "lines_before_imports",
            "lines_after_imports",
            "lines_between_sections",
            "lines_between_types",
        ):
            # set spin box values
            self.__parameterWidgetMapping[parameter].setValue(
                confDict[parameter]
                if parameter in confDict
                else getattr(self.__defaultConfig, parameter)
            )
        for parameter in (
            "include_trailing_comma",
            "use_parentheses",
            "combine_as_imports",
            "case_sensitive",
            "force_sort_within_sections",
            "from_first",
        ):
            # set check box values
            self.__parameterWidgetMapping[parameter].setChecked(
                confDict[parameter]
                if parameter in confDict
                else getattr(self.__defaultConfig, parameter)
            )
        for parameter in (
            "sections",
            "extend_skip_glob",
            "known_first_party",
        ):
            # set the plain text edits
            self.__parameterWidgetMapping[parameter].setPlainText(
                "\n".join(
                    confDict[parameter]
                    if parameter in confDict
                    else getattr(self.__defaultConfig, parameter)
                )
            )
        # set the profile combo box last because it may change other entries
        self.profileComboBox.setEditText(
            confDict["profile"]
            if "profile" in confDict
            else self.__defaultConfig.profile
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
        if source != "dialog":
            # reset the profile combo box first
            self.profileComboBox.setCurrentIndex(0)

        if source == "pyproject":
            self.__loadConfiguration(self.__pyprojectData)
        elif source == "project":
            self.__loadConfiguration(self.__projectData)
        elif source == "default":
            self.__loadConfiguration({})  # loads the default values
        elif source == "dialog":
            # just leave the current entries
            pass

    @pyqtSlot(str)
    def on_profileComboBox_editTextChanged(self, profileName):
        """
        Private slot to react upon changes of the selected/entered profile.

        @param profileName name of the current profile
        @type str
        """
        if profileName and profileName in profiles:
            confDict = self.__getConfigurationDict()
            confDict["profile"] = profileName
            confDict.update(profiles[profileName])
            self.__loadConfiguration(confDict)

            for parameter in self.__parameterWidgetMapping:
                self.__parameterWidgetMapping[parameter].setEnabled(
                    parameter not in profiles[profileName]
                )
        else:
            for widget in self.__parameterWidgetMapping.values():
                widget.setEnabled(True)

    @pyqtSlot()
    def __createTomlSnippet(self):
        """
        Private slot to generate a TOML snippet of the current configuration.

        Note: Only non-default values are included in this snippet.

        The code snippet is copied to the clipboard and may be placed inside the
        'pyproject.toml' file.
        """
        configDict = self.__getConfigurationDict()

        isort = tomlkit.table()
        for key, value in configDict.items():
            isort[key] = value

        doc = tomlkit.document()
        doc["tool"] = tomlkit.table(is_super_table=True)
        doc["tool"]["isort"] = isort

        QGuiApplication.clipboard().setText(tomlkit.dumps(doc))

        EricMessageBox.information(
            self,
            self.tr("Create TOML snippet"),
            self.tr(
                """The 'pyproject.toml' snippet was copied to the clipboard"""
                """ successfully."""
            ),
        )

    def __getConfigurationDict(self):
        """
        Private method to assemble and return a dictionary containing the entered
        non-default configuration parameters.

        @return dictionary containing the non-default configuration parameters
        @rtype dict
        """
        configDict = {}

        if self.profileComboBox.currentText():
            configDict["profile"] = self.profileComboBox.currentText()
        if (
            self.pythonComboBox.currentText()
            and self.pythonComboBox.currentData()
            != self.__defaultConfig.py_version.replace("py", "")
        ):
            configDict["py_version"] = self.pythonComboBox.currentData()
        if self.multiLineComboBox.isEnabled() and self.multiLineComboBox.currentText():
            configDict["multi_line_output"] = self.multiLineComboBox.currentData()
        if self.sortOrderComboBox.isEnabled() and self.sortOrderComboBox.currentText():
            configDict["sort_order"] = self.sortOrderComboBox.currentData()
        if self.extensionsEdit.isEnabled() and self.extensionsEdit.text():
            configDict["supported_extensions"] = [
                e.lstrip(".")
                for e in self.extensionsEdit.text().strip().split()
                if e.lstrip(".")
            ]

        for parameter in (
            "line_length",
            "lines_before_imports",
            "lines_after_imports",
            "lines_between_sections",
            "lines_between_types",
        ):
            if self.__parameterWidgetMapping[
                parameter
            ].isEnabled() and self.__parameterWidgetMapping[
                parameter
            ].value() != getattr(
                self.__defaultConfig, parameter
            ):
                configDict[parameter] = self.__parameterWidgetMapping[parameter].value()

        for parameter in (
            "include_trailing_comma",
            "use_parentheses",
            "combine_as_imports",
            "case_sensitive",
            "force_sort_within_sections",
            "from_first",
        ):
            if self.__parameterWidgetMapping[
                parameter
            ].isEnabled() and self.__parameterWidgetMapping[
                parameter
            ].isChecked() != getattr(
                self.__defaultConfig, parameter
            ):
                configDict[parameter] = self.__parameterWidgetMapping[
                    parameter
                ].isChecked()

        for parameter in (
            "sections",
            "extend_skip_glob",
            "known_first_party",
        ):
            if self.__parameterWidgetMapping[parameter].isEnabled():
                value = (
                    self.__parameterWidgetMapping[parameter].toPlainText().splitlines()
                )
                if value != list(getattr(self.__defaultConfig, parameter)):
                    configDict[parameter] = value

        return configDict

    def getConfiguration(self, saveToProject=False):
        """
        Public method to get the current configuration parameters.

        @param saveToProject flag indicating to save the configuration data in the
            project file (defaults to False)
        @type bool (optional)
        @return dictionary containing the configuration parameters
        @rtype dict
        """
        configuration = self.__getConfigurationDict()

        if saveToProject and self.__project:
            configuration["config_source"] = self.sourceComboBox.currentData()
            self.__project.setData("OTHERTOOLSPARMS", "isort", configuration)

        return configuration
