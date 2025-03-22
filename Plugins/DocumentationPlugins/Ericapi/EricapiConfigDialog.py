# -*- coding: utf-8 -*-

# Copyright (c) 2004 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the parameters for eric7_api.
"""

import copy
import os

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import DocumentationTools
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.Globals import getConfig
from eric7.SystemUtilities import FileSystemUtilities, PythonUtilities

from .Ui_EricapiConfigDialog import Ui_EricapiConfigDialog


class EricapiConfigDialog(QDialog, Ui_EricapiConfigDialog):
    """
    Class implementing a dialog to enter the parameters for eric7_api.
    """

    def __init__(self, project, parms=None, parent=None):
        """
        Constructor

        @param project reference to the project object
        @type Project
        @param parms parameters to set in the dialog
        @type dict
        @param parent parent widget of this dialog
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.startDirPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.startDirPicker.setDefaultDirectory(project.getProjectPath())

        self.outputFilePicker.setMode(EricPathPickerModes.SAVE_FILE_MODE)
        self.outputFilePicker.setDefaultDirectory(project.getProjectPath())
        self.outputFilePicker.setFilters(self.tr("API files (*.api);;All files (*)"))

        self.ignoreDirPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.ignoreDirPicker.setDefaultDirectory(project.getProjectPath())

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)
        for language in sorted(DocumentationTools.supportedExtensionsDictForApis):
            self.languagesList.addItem(language)

        self.ppath = project.getProjectPath()
        self.project = project

        self.__initializeDefaults()

        # get a copy of the defaults to store the user settings
        self.parameters = copy.deepcopy(self.defaults)

        # combine it with the values of parms
        if parms is not None:
            self.parameters.update(parms)
        self.parameters["startDirectory"] = FileSystemUtilities.toNativeSeparators(
            self.parameters["startDirectory"]
        )
        self.parameters["outputFile"] = FileSystemUtilities.toNativeSeparators(
            self.parameters["outputFile"]
        )

        self.recursionCheckBox.setChecked(self.parameters["useRecursion"])
        self.includePrivateCheckBox.setChecked(self.parameters["includePrivate"])
        self.startDirPicker.setText(self.parameters["startDirectory"])
        self.outputFilePicker.setText(self.parameters["outputFile"])
        self.baseEdit.setText(self.parameters["basePackage"])
        self.ignoreDirsList.clear()
        for d in self.parameters["ignoreDirectories"]:
            self.ignoreDirsList.addItem(d)
        self.sourceExtEdit.setText(", ".join(self.parameters["sourceExtensions"]))
        self.excludeFilesEdit.setText(", ".join(self.parameters["ignoreFilePatterns"]))
        for language in self.parameters["languages"]:
            if language == "Python":
                # convert Python to the more specific Python3
                language = "Python3"
            items = self.languagesList.findItems(language, Qt.MatchFlag.MatchExactly)
            items and items[0].setSelected(True)

    def __initializeDefaults(self):
        """
        Private method to set the default values.

        These are needed later on to generate the commandline
        parameters.
        """
        self.defaults = {
            "useRecursion": False,
            "includePrivate": False,
            "startDirectory": "",
            "outputFile": "",
            "basePackage": "",
            "ignoreDirectories": [],
            "ignoreFilePatterns": [],
            "sourceExtensions": [],
        }

        lang = self.project.getProjectLanguage()
        if lang in DocumentationTools.supportedExtensionsDictForApis:
            self.defaults["languages"] = [lang]
        else:
            self.defaults["languages"] = ["Python3"]

    def generateParameters(self):
        """
        Public method that generates the command line parameters.

        It generates a list of strings to be used
        to set the QProcess arguments for the ericapi call and
        a dictionary containing the non default parameters. This
        dictionary can be passed back upon object generation to overwrite
        the default settings.

        @return a tuple containing the commandline parameters, non default
            parameters and the start directory
        @rtype tuple of (list of str, dict, str)
        """
        parms = {}
        args = []

        # 1. the program name
        args.append(PythonUtilities.getPythonExecutable())
        args.append(
            FileSystemUtilities.normabsjoinpath(getConfig("ericDir"), "eric7_api.py")
        )

        # 2. the commandline options
        if self.parameters["startDirectory"] != self.defaults["startDirectory"]:
            parms["startDirectory"] = self.project.getRelativeUniversalPath(
                self.parameters["startDirectory"]
            )
        else:
            self.parameters["startDirectory"] = self.defaults["startDirectory"]
            parms["startDirectory"] = self.parameters["startDirectory"]
        if self.parameters["outputFile"] != self.defaults["outputFile"]:
            parms["outputFile"] = self.project.getRelativeUniversalPath(
                self.parameters["outputFile"]
            )
            args.append("-o")
            args.append(self.project.getAbsolutePath(self.parameters["outputFile"]))
        else:
            self.parameters["outputFile"] = self.defaults["outputFile"]
        if self.parameters["basePackage"] != self.defaults["basePackage"]:
            parms["basePackage"] = self.parameters["basePackage"]
            args.append("-b")
            args.append(self.parameters["basePackage"])
        if self.parameters["ignoreDirectories"] != self.defaults["ignoreDirectories"]:
            parms["ignoreDirectories"] = self.parameters["ignoreDirectories"][:]
            for d in self.parameters["ignoreDirectories"]:
                args.append("-x")
                args.append(d)
        if self.parameters["ignoreFilePatterns"] != self.defaults["ignoreFilePatterns"]:
            parms["ignoreFilePatterns"] = self.parameters["ignoreFilePatterns"][:]
            for pattern in self.parameters["ignoreFilePatterns"]:
                args.append("--exclude-file={0}".format(pattern))
        if self.parameters["useRecursion"] != self.defaults["useRecursion"]:
            parms["useRecursion"] = self.parameters["useRecursion"]
            args.append("-r")
        if self.parameters["sourceExtensions"] != self.defaults["sourceExtensions"]:
            parms["sourceExtensions"] = self.parameters["sourceExtensions"][:]
            for ext in self.parameters["sourceExtensions"]:
                args.append("-t")
                args.append(ext)
        if self.parameters["includePrivate"] != self.defaults["includePrivate"]:
            parms["includePrivate"] = self.parameters["includePrivate"]
            args.append("-p")
        parms["languages"] = self.parameters["languages"][:]
        for lang in self.parameters["languages"]:
            args.append("--language={0}".format(lang))

        startDir = (
            self.project.getAbsolutePath(self.parameters["startDirectory"])
            if self.parameters["startDirectory"]
            else ""
        )
        return args, parms, startDir

    @pyqtSlot(str)
    def on_startDirPicker_pathSelected(self, path):
        """
        Private slot handling the selection of a start directory.

        @param path path of the start directory
        @type str
        """
        # make it relative, if it is in a subdirectory of the project path
        dn = self.project.getRelativePath(path)
        while dn.endswith(os.sep):
            dn = dn[:-1]
        self.startDirPicker.setText(dn)

    @pyqtSlot()
    def on_outputFilePicker_aboutToShowPathPickerDialog(self):
        """
        Private slot called before the file selection dialog is shown.
        """
        startFile = self.outputFilePicker.text()
        if not startFile:
            self.outputFilePicker.setText(self.project.getProjectName() + ".api")

    @pyqtSlot(str)
    def on_outputFilePicker_pathSelected(self, path):
        """
        Private slot handling the selection of an output file.

        @param path path of the output file
        @type str
        """
        # make it relative, if it is in a subdirectory of the project path
        fn = self.project.getRelativePath(path)
        self.outputFilePicker.setText(fn)

    def on_outputFilePicker_textChanged(self, filename):
        """
        Private slot to enable/disable the "OK" button.

        @param filename name of the file
        @type str
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            filename != ""
        )

    @pyqtSlot(str)
    def on_ignoreDirPicker_pathSelected(self, path):
        """
        Private slot handling the selection of a directory to be ignored.

        @param path path of the directory to be ignored
        @type str
        """
        # make it relative, if it is in a subdirectory of the project path
        dn = self.project.getRelativePath(path)
        while dn.endswith(os.sep):
            dn = dn[:-1]
        self.ignoreDirPicker.setText(dn)

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add the directory displayed to the listview.

        The directory in the ignore directories
        line edit is moved to the listbox above and the edit is cleared.
        """
        basename = os.path.basename(self.ignoreDirPicker.text())
        if basename:
            self.ignoreDirsList.addItem(basename)
            self.ignoreDirPicker.clear()

    @pyqtSlot()
    def on_deleteButton_clicked(self):
        """
        Private slot to delete the currently selected directory of the listbox.
        """
        itm = self.ignoreDirsList.takeItem(self.ignoreDirsList.currentRow())
        del itm

    def accept(self):
        """
        Public slot called by the Ok button.

        It saves the values in the parameters dictionary.
        """
        self.parameters["useRecursion"] = self.recursionCheckBox.isChecked()
        self.parameters["includePrivate"] = self.includePrivateCheckBox.isChecked()

        startdir = self.startDirPicker.text()
        if startdir:
            startdir = os.path.normpath(startdir)
            if startdir.endswith(os.sep):
                startdir = startdir[:-1]
        self.parameters["startDirectory"] = startdir

        outfile = self.outputFilePicker.text()
        if outfile != "":
            outfile = os.path.normpath(outfile)
        self.parameters["outputFile"] = outfile

        self.parameters["basePackage"] = self.baseEdit.text()
        self.parameters["ignoreDirectories"] = []
        for row in range(0, self.ignoreDirsList.count()):
            itm = self.ignoreDirsList.item(row)
            self.parameters["ignoreDirectories"].append(os.path.normpath(itm.text()))
        extensions = self.sourceExtEdit.text().split(",")
        self.parameters["sourceExtensions"] = [
            ext.strip() for ext in extensions if len(ext) > 0
        ]
        patterns = self.excludeFilesEdit.text().split(",")
        self.parameters["ignoreFilePatterns"] = [
            pattern.strip() for pattern in patterns
        ]
        self.parameters["languages"] = []
        for itm in self.languagesList.selectedItems():
            self.parameters["languages"].append(itm.text())

        # call the accept slot of the base class
        super().accept()
