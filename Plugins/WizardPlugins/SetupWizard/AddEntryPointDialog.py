# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for an entry point.
"""

import pathlib

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog

from .Ui_AddEntryPointDialog import Ui_AddEntryPointDialog


class AddEntryPointDialog(QDialog, Ui_AddEntryPointDialog):
    """
    Class implementing a dialog to enter the data for an entry point.
    """

    def __init__(self, rootDirectory, epType="", name="", script="", parent=None):
        """
        Constructor

        @param rootDirectory root directory for selecting script modules via
            a file selection dialog
        @type str
        @param epType type of the entry point (defaults to "")
        @type str (optional)
        @param name name of the entry point (defaults to "")
        @type str (optional)
        @param script script function of the entry point (defaults to "")
        @type str (optional)
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        for typeStr, category in (
            ("", ""),
            (self.tr("Console"), "console_scripts"),
            (self.tr("GUI"), "gui_scripts"),
        ):
            self.typeComboBox.addItem(typeStr, category)

        self.scriptButton.setIcon(EricPixmapCache.getIcon("open"))

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        self.__rootDirectory = rootDirectory

        self.typeComboBox.currentTextChanged.connect(self.__updateOK)
        self.nameEdit.textChanged.connect(self.__updateOK)
        self.scriptEdit.textChanged.connect(self.__updateOK)

        self.typeComboBox.setCurrentText(epType)
        self.nameEdit.setText(name)
        self.scriptEdit.setText(script)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def __updateOK(self):
        """
        Private slot to update the enabled state of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.typeComboBox.currentText())
            and bool(self.nameEdit.text())
            and bool(self.scriptEdit.text())
        )

    @pyqtSlot()
    def on_scriptButton_clicked(self):
        """
        Private slot to select a script via a file selection dialog.
        """
        script = self.scriptEdit.text()
        if script:
            if ":" in script:
                scriptFile, scriptFunction = script.rsplit(":", 1)
            else:
                scriptFile, scriptFunction = script, "main"
            scriptFile = scriptFile.replace(".", "/") + ".py"
            root = str(pathlib.Path(self.__rootDirectory) / scriptFile)
        else:
            root = self.__rootDirectory
            scriptFunction = "main"

        script = EricFileDialog.getOpenFileName(
            self,
            self.tr("Select Script File"),
            root,
            self.tr("Python Files (*.py);;All Files (*)"),
        )

        if script:
            scriptPath = pathlib.Path(script)
            try:
                relativeScriptPath = scriptPath.relative_to(self.__rootDirectory)
            except ValueError:
                relativeScriptPath = scriptPath
            self.scriptEdit.setText(
                "{0}:{1}".format(
                    str(relativeScriptPath.with_suffix(""))
                    .replace("/", ".")
                    .replace("\\", "."),
                    scriptFunction,
                )
            )

    def getEntryPoint(self):
        """
        Public method to get the data for the entry point.

        @return tuple containing the entry point type, category, name and
            script function
        @rtype tuple of (str, str, str)
        """
        return (
            self.typeComboBox.currentText(),
            self.typeComboBox.currentData(),
            self.nameEdit.text(),
            self.scriptEdit.text(),
        )
