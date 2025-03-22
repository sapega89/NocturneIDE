# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the project properties dialog.
"""

import contextlib
import os

import trove_classifiers

from PyQt6.QtCore import QDir, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7 import Preferences
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.QScintilla.DocstringGenerator import getSupportedDocstringTypes
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities
from eric7.Testing.Interfaces import FrameworkNames

from .Ui_PropertiesDialog import Ui_PropertiesDialog


class PropertiesDialog(QDialog, Ui_PropertiesDialog):
    """
    Class implementing the project properties dialog.
    """

    def __init__(self, project, new=True, isRemote=False, parent=None, name=None):
        """
        Constructor

        @param project reference to the project object
        @type Project
        @param new flag indicating the generation of a new project
            (defaults to True)
        @type bool (optional)
        @param isRemote flag indicating a remote project (defaults to False)
        @type bool (optional)
        @param parent parent widget of this dialog (defaults to None)
        @type QWidget (optional)
        @param name name of this dialog (defaults to None)
        @type str (optional)
        """
        super().__init__(parent)
        if name:
            self.setObjectName(name)
        self.setupUi(self)

        self.__remoteProject = isRemote
        self.__remotefsInterface = (
            ericApp().getObject("EricServer").getServiceInterface("FileSystem")
        )

        self.dirPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.dirPicker.setRemote(isRemote)

        self.srcDirPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.srcDirPicker.setRemote(isRemote)

        self.mainscriptPicker.setMode(EricPathPickerModes.OPEN_FILE_MODE)
        self.mainscriptPicker.setRemote(isRemote)

        self.makeButton.setIcon(EricPixmapCache.getIcon("makefile"))

        self.docstringStyleComboBox.addItem(self.tr("None"), "")
        for docstringType, docstringStyle in sorted(getSupportedDocstringTypes()):
            self.docstringStyleComboBox.addItem(docstringStyle, docstringType)

        self.project = project
        self.newProject = new

        self.transPropertiesDlg = None
        self.spellPropertiesDlg = None
        self.makePropertiesDlg = None
        self.__fileTypesDict = {}

        if self.__remoteProject:
            # some stuff is not supported for remote projects
            self.makeCheckBox.setEnabled(False)
            self.makeButton.setEnabled(False)
            self.testingFrameworkComboBox.setEnabled(False)
            self.embeddedVenvCheckBox.setEnabled(False)
            self.spellPropertiesButton.setEnabled(False)
        self.languageComboBox.addItems(project.getProgrammingLanguages())

        projectTypes = []
        for projectTypeItem in project.getProjectTypes().items():
            projectTypes.append((projectTypeItem[1], projectTypeItem[0]))
        self.projectTypeComboBox.clear()
        for projectType in sorted(projectTypes):
            self.projectTypeComboBox.addItem(projectType[0], projectType[1])

        if self.__remoteProject:
            ipath = self.__remotefsInterface.getcwd()
            self.__initPaths = [ipath, ipath + self.__remotefsInterface.separator()]
        else:
            ipath = Preferences.getMultiProject("Workspace") or OSUtilities.getHomeDir()
            self.__initPaths = [
                FileSystemUtilities.fromNativeSeparators(ipath),
                FileSystemUtilities.fromNativeSeparators(ipath) + "/",
            ]
        self.dirInfoLabel.setText(
            self.tr("<p>The project directory must not be '<b>{0}</b>'.</p>").format(
                ipath
            )
        )

        self.licenseComboBox.lineEdit().setClearButtonEnabled(True)
        self.__populateLicenseComboBox()

        if not new:
            self.nameEdit.setReadOnly(True)
            self.dirPicker.setReadOnly(True)

            if self.__remoteProject:
                name = self.__remotefsInterface.splitext(self.project.pfile)[0]
                self.nameEdit.setText(self.__remotefsInterface.basename(name))
            else:
                name = os.path.splitext(self.project.pfile)[0]
                self.nameEdit.setText(os.path.basename(name))
            self.nameEdit.setReadOnly(True)
            self.languageComboBox.setCurrentIndex(
                self.languageComboBox.findText(
                    self.project.getProjectData(dataKey="PROGLANGUAGE")
                )
            )
            self.mixedLanguageCheckBox.setChecked(
                self.project.getProjectData(dataKey="MIXEDLANGUAGE")
            )
            curIndex = self.projectTypeComboBox.findData(
                self.project.getProjectData(dataKey="PROJECTTYPE")
            )
            if curIndex == -1:
                curIndex = self.projectTypeComboBox.findData("PyQt6")
            self.projectTypeComboBox.setCurrentIndex(curIndex)
            self.dirPicker.setText(self.project.ppath)
            self.srcDirPicker.setText(self.project.getProjectData(dataKey="SOURCESDIR"))
            self.versionEdit.setText(self.project.getProjectData(dataKey="VERSION"))
            self.mainscriptPicker.setText(
                self.project.getProjectData(dataKey="MAINSCRIPT")
            )
            self.authorEdit.setText(self.project.getProjectData(dataKey="AUTHOR"))
            self.emailEdit.setText(self.project.getProjectData(dataKey="EMAIL"))
            self.descriptionEdit.setPlainText(
                self.project.getProjectData(dataKey="DESCRIPTION")
            )
            self.eolComboBox.setCurrentIndex(self.project.getProjectData(dataKey="EOL"))
            self.vcsLabel.show()
            if not self.__remoteProject:
                # VCS not supported for remote projects
                if self.project.vcs is not None:
                    vcsSystemsDict = (
                        ericApp()
                        .getObject("PluginManager")
                        .getPluginDisplayStrings("version_control")
                    )
                    try:
                        vcsSystemDisplay = vcsSystemsDict[
                            self.project.getProjectData(dataKey="VCS")
                        ]
                    except KeyError:
                        vcsSystemDisplay = "None"
                    self.vcsLabel.setText(
                        self.tr(
                            "The project is version controlled by <b>{0}</b>."
                        ).format(vcsSystemDisplay)
                    )
                    self.vcsInfoButton.show()
                else:
                    self.vcsLabel.setText(
                        self.tr("The project is not version controlled.")
                    )
                    self.vcsInfoButton.hide()
            else:
                self.vcsLabel.setText(
                    self.tr("Version control is not available for remote projects.")
                )
                self.vcsInfoButton.hide()
            self.vcsCheckBox.hide()
            if self.__remoteProject:
                self.makeCheckBox.setChecked(False)
            else:
                self.makeCheckBox.setChecked(
                    self.project.getProjectData(dataKey="MAKEPARAMS")["MakeEnabled"]
                )
            cindex = self.docstringStyleComboBox.findData(
                self.project.getProjectData(dataKey="DOCSTRING")
            )
            self.docstringStyleComboBox.setCurrentIndex(cindex)
            if not self.__remoteProject:
                with contextlib.suppress(KeyError):
                    cindex = self.testingFrameworkComboBox.findData(
                        self.project.getProjectData(dataKey="TESTING_FRAMEWORK")
                    )
                    self.testingFrameworkComboBox.setCurrentIndex(cindex)
            with contextlib.suppress(KeyError):
                self.licenseComboBox.setCurrentText(
                    self.project.getProjectData(dataKey="LICENSE")
                )
            self.embeddedVenvCheckBox.setChecked(
                self.project.getProjectData(dataKey="EMBEDDED_VENV")
            )
        else:
            self.languageComboBox.setCurrentText("Python3")
            self.projectTypeComboBox.setCurrentIndex(
                self.projectTypeComboBox.findData("PyQt6")
            )
            self.dirPicker.setText(self.__initPaths[0])
            self.versionEdit.setText("0.1")
            self.vcsLabel.hide()
            self.vcsInfoButton.hide()
            if self.__remoteProject or not self.project.vcsSoftwareAvailable():
                self.vcsCheckBox.hide()

        self.__origProgrammingLanguage = self.languageComboBox.currentText()
        self.__origMixedFlag = self.mixedLanguageCheckBox.isChecked()
        self.__origProjectType = self.getProjectType()

        self.__initFileTypesDict(force=True)

        self.languageComboBox.currentTextChanged.connect(self.__initFileTypesDict)
        try:
            self.mixedLanguageCheckBox.checkStateChanged.connect(
                self.__initFileTypesDict
            )
        except AttributeError:
            # backward compatibility for Qt < 6.7
            self.mixedLanguageCheckBox.stateChanged.connect(self.__initFileTypesDict)
        self.projectTypeComboBox.currentIndexChanged.connect(self.__initFileTypesDict)

        self.__updateOk()

    def __updateOk(self):
        """
        Private method to update the state of the OK button.
        """
        projectDir = self.dirPicker.text()
        if self.__remoteProject:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                FileSystemUtilities.isRemoteFileName(projectDir)
                and not self.__remotefsInterface.isEmpty(projectDir)
                and projectDir not in self.__initPaths
            )
        else:
            self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
                bool(projectDir)
                and not FileSystemUtilities.isRemoteFileName(projectDir)
                and FileSystemUtilities.fromNativeSeparators(projectDir)
                not in self.__initPaths
            )

    def __setMainScriptPickerFilters(self):
        """
        Private method to set the filters for the main script file picker.
        """
        patterns = []
        for pattern, filetype in self.__fileTypesDict.items():
            if filetype == "SOURCES":
                patterns.append(pattern)
        filters = (
            self.tr("Source Files ({0});;All Files (*)").format(
                " ".join(sorted(patterns))
            )
            if patterns
            else self.tr("All Files (*)")
        )
        self.mainscriptPicker.setFilters(filters)

    def __populateLicenseComboBox(self):
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

    @pyqtSlot(str)
    def on_languageComboBox_currentTextChanged(self, language):
        """
        Private slot handling the selection of a programming language.

        @param language text of the current item
        @type str
        """
        curProjectType = self.getProjectType()

        self.projectTypeComboBox.clear()
        for projectType in sorted(
            self.project.getProjectTypes(language).items(), key=lambda k: k[1]
        ):
            self.projectTypeComboBox.addItem(projectType[1], projectType[0])

        index = self.projectTypeComboBox.findData(curProjectType)
        if index == -1:
            index = 0
        self.projectTypeComboBox.setCurrentIndex(index)

        curTestingFramework = self.testingFrameworkComboBox.currentText()
        self.testingFrameworkComboBox.clear()
        self.testingFrameworkComboBox.addItem(self.tr("None"), "")
        with contextlib.suppress(KeyError):
            for framework in sorted(FrameworkNames[language]):
                self.testingFrameworkComboBox.addItem(framework, framework)
        self.testingFrameworkComboBox.setCurrentText(curTestingFramework)

    @pyqtSlot(str)
    def on_dirPicker_textChanged(self, txt):
        """
        Private slot to handle a change of the project directory.

        @param txt name of the project directory
        @type str
        """
        self.__updateOk()

    @pyqtSlot(str)
    def on_srcDirPicker_pathSelected(self, srcDir):
        """
        Private slot to check the selected sources sub-directory name.

        @param srcDir name of the sources directory name
        @type str
        """
        if srcDir:
            ppath = self.dirPicker.text()
            if ppath:
                if self.__remoteProject:
                    ppath = (
                        FileSystemUtilities.remoteFileName(ppath)
                        + self.__remotefsInterface.separator()
                    )
                else:
                    ppath = os.path.abspath(ppath) + os.sep
                srcDir = srcDir.replace(ppath, "")
            self.srcDirPicker.setText(srcDir)

    @pyqtSlot()
    def on_srcDirPicker_aboutToShowPathPickerDialog(self):
        """
        Private slot to perform actions before the sources sub-directory selection
        dialog is shown.
        """
        ppath = self.dirPicker.text()
        if not ppath:
            if self.__remoteProject:
                ppath = self.__remotefsInterface.getcwd()
            else:
                ppath = QDir.currentPath()
        self.srcDirPicker.setDefaultDirectory(ppath)

    @pyqtSlot()
    def on_spellPropertiesButton_clicked(self):
        """
        Private slot to display the spelling properties dialog.
        """
        from .SpellingPropertiesDialog import SpellingPropertiesDialog

        if self.spellPropertiesDlg is None:
            self.spellPropertiesDlg = SpellingPropertiesDialog(
                self.project, self.newProject, parent=self
            )
        res = self.spellPropertiesDlg.exec()
        if res == QDialog.DialogCode.Rejected:
            self.spellPropertiesDlg.initDialog()  # reset the dialogs contents

    @pyqtSlot()
    def on_transPropertiesButton_clicked(self):
        """
        Private slot to display the translations properties dialog.
        """
        from .TranslationPropertiesDialog import TranslationPropertiesDialog

        if self.transPropertiesDlg is None:
            self.transPropertiesDlg = TranslationPropertiesDialog(
                self.project,
                self.newProject,
                parent=self,
                isRemote=self.__remoteProject,
            )
        else:
            self.transPropertiesDlg.initFilters()
        res = self.transPropertiesDlg.exec()
        if res == QDialog.DialogCode.Rejected:
            self.transPropertiesDlg.initDialog()  # reset the dialogs contents

    @pyqtSlot()
    def on_makeButton_clicked(self):
        """
        Private slot to display the make properties dialog.
        """
        from .MakePropertiesDialog import MakePropertiesDialog

        if self.makePropertiesDlg is None:
            self.makePropertiesDlg = MakePropertiesDialog(
                self.project, self.newProject, parent=self
            )
        res = self.makePropertiesDlg.exec()
        if res == QDialog.DialogCode.Rejected:
            self.makePropertiesDlg.initDialog()

    @pyqtSlot(str)
    def on_mainscriptPicker_pathSelected(self, script):
        """
        Private slot to check the selected main script name.

        @param script name of the main script
        @type str
        """
        if script:
            ppath = self.dirPicker.text()
            if ppath:
                if self.__remoteProject:
                    ppath = (
                        FileSystemUtilities.remoteFileName(ppath)
                        + self.__remotefsInterface.separator()
                    )
                else:
                    ppath = os.path.abspath(ppath) + os.sep
                script = script.replace(ppath, "")
            self.mainscriptPicker.setText(script)

    @pyqtSlot()
    def on_mainscriptPicker_aboutToShowPathPickerDialog(self):
        """
        Private slot to perform actions before the main script selection dialog
        is shown.
        """
        ppath = self.dirPicker.text()
        if not ppath:
            if self.__remoteProject:
                ppath = self.__remotefsInterface.getcwd()
            else:
                ppath = QDir.currentPath()
        self.mainscriptPicker.setDefaultDirectory(ppath)

    @pyqtSlot()
    def on_vcsInfoButton_clicked(self):
        """
        Private slot to display a vcs information dialog.
        """
        from eric7.VCS.RepositoryInfoDialog import VcsRepositoryInfoDialog

        if self.project.vcs is None:
            return

        info = self.project.vcs.vcsRepositoryInfos(self.project.ppath)
        dlg = VcsRepositoryInfoDialog(parent=self, info=info)
        dlg.exec()

    def getProjectType(self):
        """
        Public method to get the selected project type.

        @return selected UI type
        @rtype str
        """
        return self.projectTypeComboBox.itemData(
            self.projectTypeComboBox.currentIndex()
        )

    def getPPath(self):
        """
        Public method to get the project path.

        @return data of the project directory edit
        @rtype str
        """
        if self.__remoteProject:
            return FileSystemUtilities.remoteFileName(self.dirPicker.text())
        else:
            return os.path.abspath(self.dirPicker.text())

    @pyqtSlot()
    def __initFileTypesDict(self, force=False):
        """
        Private slot to (re-)initialize the filetype dictionary.

        @param force flag indicating to force the initialization (defaults to False)
        @type bool (optional)
        """
        if (
            force
            or self.__origProgrammingLanguage != self.languageComboBox.currentText()
            or self.__origMixedFlag != self.mixedLanguageCheckBox.isChecked()
            or self.__origProjectType != self.getProjectType()
        ):
            # any of the defining data got changed
            self.__fileTypesDict = self.project.defaultFileTypes(
                self.languageComboBox.currentText(),
                self.mixedLanguageCheckBox.isChecked(),
                self.getProjectType(),
            )
        else:
            # all of the defining data was changed back to original
            self.__fileTypesDict = self.project.getProjectData(dataKey="FILETYPES")

        self.__setMainScriptPickerFilters()

    @pyqtSlot()
    def on_filetypesButton_clicked(self):
        """
        Private slot to open a dialog to edit the filetype associations.
        """
        from .FiletypeAssociationDialog import FiletypeAssociationDialog

        if not self.__fileTypesDict:
            self.__fileTypesDict = self.project.getProjectData(dataKey="FILETYPES")
            if (
                not self.__fileTypesDict
                or self.__origProgrammingLanguage != self.languageComboBox.currentText()
                or self.__origMixedFlag != self.mixedLanguageCheckBox.isChecked()
                or self.__origProjectType != self.getProjectType()
            ):
                # the associations were not defined yet or any of the defining data got
                # changed
                self.__fileTypesDict = self.project.defaultFileTypes(
                    self.languageComboBox.currentText(),
                    self.mixedLanguageCheckBox.isChecked(),
                    self.getProjectType(),
                )

        dlg = FiletypeAssociationDialog(self.project, self.__fileTypesDict, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.__fileTypesDict = dlg.getData()

        self.__setMainScriptPickerFilters()

        self.__setMainScriptPickerFilters()

    def storeData(self):
        """
        Public method to store the entered/modified data.
        """
        if self.newProject:
            if self.__remoteProject:
                self.project.ppath = FileSystemUtilities.remoteFileName(
                    self.__remotefsInterface.abspath(self.dirPicker.text())
                )
                fn = self.nameEdit.text()
                if fn:
                    self.project.name = fn
                    fn = f"{fn}.epj"
                    self.project.pfile = self.__remotefsInterface.join(
                        self.project.ppath, fn
                    )
                else:
                    self.project.pfile = ""
            else:
                self.project.ppath = os.path.abspath(self.dirPicker.text())
                fn = self.nameEdit.text()
                if fn:
                    self.project.name = fn
                    fn = f"{fn}.epj"
                    self.project.pfile = os.path.join(self.project.ppath, fn)
                else:
                    self.project.pfile = ""
        self.project.setProjectData(self.versionEdit.text(), dataKey="VERSION")
        srcDir = self.srcDirPicker.text()
        if srcDir:
            srcDir = self.project.getRelativePath(srcDir)
            self.project.setProjectData(srcDir, dataKey="SOURCESDIR")
        else:
            self.project.setProjectData("", dataKey="SOURCESDIR")
        fn = self.mainscriptPicker.text()
        if fn:
            fn = self.project.getRelativePath(fn)
            self.project.setProjectData(fn, dataKey="MAINSCRIPT")
            if self.__remoteProject:
                self.project.translationsRoot = self.__remotefsInterface.splitext(fn)[0]
            else:
                self.project.translationsRoot = os.path.splitext(fn)[0]
        else:
            self.project.setProjectData("", dataKey="MAINSCRIPT")
            self.project.translationsRoot = ""
        self.project.setProjectData(self.authorEdit.text(), dataKey="AUTHOR")
        self.project.setProjectData(self.emailEdit.text(), dataKey="EMAIL")
        self.project.setProjectData(
            self.descriptionEdit.toPlainText(), dataKey="DESCRIPTION"
        )
        self.project.setProjectData(
            self.languageComboBox.currentText(), dataKey="PROGLANGUAGE"
        )
        self.project.setProjectData(
            self.mixedLanguageCheckBox.isChecked(), dataKey="MIXEDLANGUAGE"
        )
        projectType = self.getProjectType()
        if projectType is not None:
            self.project.setProjectData(projectType, dataKey="PROJECTTYPE")
        self.project.setProjectData(self.eolComboBox.currentIndex(), dataKey="EOL")

        self.project.vcsRequested = self.vcsCheckBox.isChecked()

        if self.spellPropertiesDlg is not None:
            self.spellPropertiesDlg.storeData()

        if self.transPropertiesDlg is not None:
            self.transPropertiesDlg.storeData()

        makeParams = self.project.getProjectData(dataKey="MAKEPARAMS")
        makeParams["MakeEnabled"] = self.makeCheckBox.isChecked()
        self.project.setProjectData(makeParams, dataKey="MAKEPARAMS")
        if self.makePropertiesDlg is not None:
            self.makePropertiesDlg.storeData()

        self.project.setProjectData(
            self.docstringStyleComboBox.currentData(), dataKey="DOCSTRING"
        )

        self.project.setProjectData(
            self.testingFrameworkComboBox.currentData(), dataKey="TESTING_FRAMEWORK"
        )

        self.project.setProjectData(
            self.licenseComboBox.currentText(), dataKey="LICENSE"
        )

        self.project.setProjectData(
            self.embeddedVenvCheckBox.isChecked(), dataKey="EMBEDDED_VENV"
        )

        if self.__fileTypesDict:
            self.project.setProjectData(self.__fileTypesDict, dataKey="FILETYPES")
