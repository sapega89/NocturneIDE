# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Qt configuration page.
"""

from PyQt6.QtCore import pyqtSlot

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_QtPage import Ui_QtPage


class QtPage(ConfigurationPageBase, Ui_QtPage):
    """
    Class implementing the Qt configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("QtPage")

        try:
            self.__virtualenvManager = ericApp().getObject("VirtualEnvManager")
            self.__standalone = False
        except KeyError:
            from eric7.VirtualEnv.VirtualenvManager import (  # __IGNORE_WARNING_I101__
                VirtualenvManager,
            )

            self.__virtualenvManager = VirtualenvManager()
            self.__standalone = True

        for button in (
            self.pyqt5VenvDlgButton,
            self.pyqt6VenvDlgButton,
            self.pyside2VenvDlgButton,
            self.pyside6VenvDlgButton,
        ):
            button.setIcon(EricPixmapCache.getIcon("virtualenv"))
            button.clicked.connect(self.__showVirtualEnvManager)
            button.setVisible(self.__standalone)

        for button in (
            self.pyqt5VenvRefreshButton,
            self.pyqt6VenvRefreshButton,
            self.pyside2VenvRefreshButton,
            self.pyside6VenvRefreshButton,
        ):
            button.setIcon(EricPixmapCache.getIcon("reload"))
            button.clicked.connect(self.__populateAndSetVenvComboBoxes)
            button.setVisible(not self.__standalone)

        self.qtTransPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        for picker in (self.lreleasePicker, self.qhelpgeneratorPicker):
            picker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        for picker in (
            self.qtToolsDirPicker,
            self.pyqtToolsDirPicker,
            self.pyqt6ToolsDirPicker,
            self.pyside2ToolsDirPicker,
            self.pyside6ToolsDirPicker,
        ):
            picker.setMode(EricPathPickerModes.DIRECTORY_SHOW_FILES_MODE)

        self.__populateAndSetVenvComboBoxes(True)

        # set initial values
        self.qtTransPicker.setText(Preferences.getQt("Qt6TranslationsDir"))

        # Qt
        self.qtToolsDirPicker.setText(Preferences.getQt("QtToolsDir"))
        self.qtPrefixEdit.setText(Preferences.getQt("QtToolsPrefix"))
        self.qtPostfixEdit.setText(Preferences.getQt("QtToolsPostfix"))
        self.__updateQtSample()
        self.qhelpgeneratorPicker.setText(Preferences.getQt("QHelpGenerator"))
        self.qhelpgeneratorPicker.setDefaultDirectory(Preferences.getQt("QtToolsDir"))
        self.lreleasePicker.setText(Preferences.getQt("Lrelease"))
        self.lreleasePicker.setDefaultDirectory(Preferences.getQt("QtToolsDir"))

        # PyQt 5
        self.pyqtToolsDirPicker.setText(Preferences.getQt("PyQtToolsDir"))
        self.pyuicIndentSpinBox.setValue(Preferences.getQt("PyuicIndent"))
        self.pyuicImportsCheckBox.setChecked(Preferences.getQt("PyuicFromImports"))
        self.pyuicExecuteCheckBox.setChecked(Preferences.getQt("PyuicExecute"))

        # PyQt 6
        self.pyqt6ToolsDirPicker.setText(Preferences.getQt("PyQt6ToolsDir"))
        self.pyuic6IndentSpinBox.setValue(Preferences.getQt("Pyuic6Indent"))
        self.pyuic6ExecuteCheckBox.setChecked(Preferences.getQt("Pyuic6Execute"))

        # PySide 2
        self.pyside2ToolsDirPicker.setText(Preferences.getQt("PySide2ToolsDir"))
        self.pyside2uicImportsCheckBox.setChecked(
            Preferences.getQt("PySide2FromImports")
        )

        # PySide 6
        self.pyside6ToolsDirPicker.setText(Preferences.getQt("PySide6ToolsDir"))
        self.pyside6uicImportsCheckBox.setChecked(
            Preferences.getQt("PySide6FromImports")
        )

    def save(self):
        """
        Public slot to save the Qt configuration.
        """
        Preferences.setQt("Qt6TranslationsDir", self.qtTransPicker.text())
        Preferences.setQt("QtToolsDir", self.qtToolsDirPicker.text())
        Preferences.setQt("QtToolsPrefix", self.qtPrefixEdit.text())
        Preferences.setQt("QtToolsPostfix", self.qtPostfixEdit.text())
        Preferences.setQt("QHelpGenerator", self.qhelpgeneratorPicker.text())
        Preferences.setQt("Lrelease", self.lreleasePicker.text())

        Preferences.setQt("PyQtVenvName", self.pyqt5VenvComboBox.currentText())
        Preferences.setQt("PyQtToolsDir", self.pyqtToolsDirPicker.text())
        Preferences.setQt("PyuicIndent", self.pyuicIndentSpinBox.value())
        Preferences.setQt("PyuicFromImports", self.pyuicImportsCheckBox.isChecked())
        Preferences.setQt("PyuicExecute", self.pyuicExecuteCheckBox.isChecked())

        Preferences.setQt("PyQt6VenvName", self.pyqt6VenvComboBox.currentText())
        Preferences.setQt("PyQt6ToolsDir", self.pyqt6ToolsDirPicker.text())
        Preferences.setQt("Pyuic6Indent", self.pyuic6IndentSpinBox.value())
        Preferences.setQt("Pyuic6Execute", self.pyuic6ExecuteCheckBox.isChecked())

        Preferences.setQt("PySide2VenvName", self.pyside2VenvComboBox.currentText())
        Preferences.setQt("PySide2ToolsDir", self.pyside2ToolsDirPicker.text())
        Preferences.setQt(
            "PySide2FromImports", self.pyside2uicImportsCheckBox.isChecked()
        )

        Preferences.setQt("PySide6VenvName", self.pyside6VenvComboBox.currentText())
        Preferences.setQt("PySide6ToolsDir", self.pyside6ToolsDirPicker.text())
        Preferences.setQt(
            "PySide6FromImports", self.pyside6uicImportsCheckBox.isChecked()
        )

    def __updateQtSample(self):
        """
        Private slot to update the Qt tools sample label.
        """
        self.qtSampleLabel.setText(
            self.tr("Sample: {0}designer{1}").format(
                self.qtPrefixEdit.text(), self.qtPostfixEdit.text()
            )
        )

    @pyqtSlot(str)
    def on_qtPrefixEdit_textChanged(self, _txt):
        """
        Private slot to handle a change in the entered Qt directory.

        @param _txt the entered string (unused)
        @type str
        """
        self.__updateQtSample()

    @pyqtSlot(str)
    def on_qtPostfixEdit_textChanged(self, _txt):
        """
        Private slot to handle a change in the entered Qt directory.

        @param _txt the entered string (unused)
        @type str
        """
        self.__updateQtSample()

    @pyqtSlot(str)
    def on_qtToolsDirPicker_editTextChanged(self, directory):
        """
        Private slot handling a change of the Qt Tools directory.

        @param directory text entered into the Qt Tools directory edit
        @type str
        """
        if directory:
            self.qhelpgeneratorPicker.setDefaultDirectory(directory)
            self.lreleasePicker.setDefaultDirectory(directory)

    def __populateAndSetVenvComboBox(self, comboBox, envKey, initial):
        """
        Private method to populate and set the virtual environment combo boxes.

        @param comboBox reference to the combo box to be populated
        @type QComboBox
        @param envKey preferences key for the environment
        @type str
        @param initial flag indicating an initial population
        @type bool
        """
        venvName = Preferences.getQt(envKey) if initial else comboBox.currentText()

        comboBox.clear()
        comboBox.addItems(
            [""] + sorted(self.__virtualenvManager.getVirtualenvNames(noServer=True))
        )

        if venvName:
            index = comboBox.findText(venvName)
            if index < 0:
                index = 0
            comboBox.setCurrentIndex(index)

    def __populateAndSetVenvComboBoxes(self, initial):
        """
        Private method to populate the virtual environment combo boxes.

        @param initial flag indicating an initial population
        @type bool
        """
        self.__populateAndSetVenvComboBox(
            self.pyqt5VenvComboBox, "PyQtVenvName", initial
        )
        self.__populateAndSetVenvComboBox(
            self.pyqt6VenvComboBox, "PyQt6VenvName", initial
        )
        self.__populateAndSetVenvComboBox(
            self.pyside2VenvComboBox, "PySide2VenvName", initial
        )
        self.__populateAndSetVenvComboBox(
            self.pyside6VenvComboBox, "PySide6VenvName", initial
        )

    def __showVirtualEnvManager(self):
        """
        Private method to show the virtual environment manager dialog.
        """
        self.__virtualenvManager.showVirtualenvManagerDialog(modal=True)
        self.__populateAndSetVenvComboBoxes(False)
        self.activateWindow()
        self.raise_()


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = QtPage()
    return page
