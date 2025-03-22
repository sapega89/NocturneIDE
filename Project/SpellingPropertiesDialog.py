# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Spelling Properties dialog.
"""

from PyQt6.QtWidgets import QDialog

from eric7 import Preferences
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.QScintilla.SpellChecker import SpellChecker

from .Ui_SpellingPropertiesDialog import Ui_SpellingPropertiesDialog


class SpellingPropertiesDialog(QDialog, Ui_SpellingPropertiesDialog):
    """
    Class implementing the Spelling Properties dialog.
    """

    def __init__(self, project, new, parent):
        """
        Constructor

        @param project reference to the project object
        @type Project
        @param new flag indicating the generation of a new project
        @type str
        @param parent parent widget of this dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.pwlPicker.setMode(EricPathPickerModes.SAVE_FILE_MODE)
        self.pwlPicker.setDefaultDirectory(project.ppath)
        self.pwlPicker.setFilters(self.tr("Dictionary File (*.dic);;All Files (*)"))

        self.pelPicker.setMode(EricPathPickerModes.SAVE_FILE_MODE)
        self.pelPicker.setDefaultDirectory(project.ppath)
        self.pelPicker.setFilters(self.tr("Dictionary File (*.dic);;All Files (*)"))

        self.project = project
        self.parent = parent

        self.spellingComboBox.addItem(self.tr("<default>"))
        self.spellingComboBox.addItems(sorted(SpellChecker.getAvailableLanguages()))

        if not new:
            self.initDialog()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def initDialog(self):
        """
        Public method to initialize the dialogs data.
        """
        index = self.spellingComboBox.findText(
            self.project.getProjectData(dataKey="SPELLLANGUAGE")
        )
        if index == -1:
            index = 0
        self.spellingComboBox.setCurrentIndex(index)
        if self.project.getProjectData(dataKey="SPELLWORDS"):
            self.pwlPicker.setText(self.project.getProjectData(dataKey="SPELLWORDS"))
        if self.project.getProjectData(dataKey="SPELLEXCLUDES"):
            self.pelPicker.setText(self.project.getProjectData(dataKey="SPELLEXCLUDES"))

    def storeData(self):
        """
        Public method to store the entered/modified data.
        """
        if self.spellingComboBox.currentIndex() == 0:
            self.project.setProjectData(
                Preferences.getEditor("SpellCheckingDefaultLanguage"),
                dataKey="SPELLLANGUAGE",
            )
        else:
            self.project.setProjectData(
                self.spellingComboBox.currentText(), dataKey="SPELLLANGUAGE"
            )
        self.project.setProjectData(
            self.project.getRelativePath(self.pwlPicker.text()),
            dataKey="SPELLWORDS",
        )
        self.project.setProjectData(
            self.project.getRelativePath(self.pelPicker.text()),
            dataKey="SPELLEXCLUDES",
        )
