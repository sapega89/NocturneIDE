# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the setup.py wizard dialog.
"""

import configparser
import datetime
import io
import os
import pathlib

import tomlkit
import trove_classifiers

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem, QTreeWidgetItem

from eric7 import Preferences
from eric7.EricWidgets import EricFileDialog
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricPathPicker import EricPathPickerModes
from eric7.SystemUtilities import FileSystemUtilities, OSUtilities

from .AddEntryPointDialog import AddEntryPointDialog
from .AddProjectUrlDialog import AddProjectUrlDialog
from .Ui_SetupWizardDialog import Ui_SetupWizardDialog


class SetupWizardDialog(QDialog, Ui_SetupWizardDialog):
    """
    Class implementing the setup.py wizard dialog.

    It displays a dialog for entering the parameters for the setup.py code
    generator.
    """

    def __init__(self, category, editor, parent=None):
        """
        Constructor

        @param category category of setup file to create
        @type str
        @param editor reference to the editor object to receive the code
        @type Editor
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        @exception ValueError raised for an illegal setup file category
        """
        if category not in ("setup.py", "setup.cfg", "pyproject.toml"):
            raise ValueError("illegal setup file category given")

        super().__init__(parent)
        self.setupUi(self)

        self.setWindowTitle(self.tr("{0} Wizard").format(category))

        self.__replies = []
        self.__category = category
        self.__editor = editor

        if category != "setup.py":
            self.introCheckBox.setVisible(False)
            self.importCheckBox.setVisible(False)
            self.metaDataCheckBox.setVisible(False)

        self.dataTabWidget.setCurrentIndex(0)

        self.packageRootPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)
        self.sourceDirectoryPicker.setMode(EricPathPickerModes.DIRECTORY_MODE)

        self.__mandatoryStyleSheet = (
            "QLineEdit {border: 2px solid; border-color: #dd8888}"
            if ericApp().usesDarkPalette()
            else "QLineEdit {border: 2px solid; border-color: #800000}"
        )
        for lineEdit in [
            self.nameEdit,
            self.versionEdit,
            self.homePageUrlEdit,
            self.authorEdit,
            self.authorEmailEdit,
            self.maintainerEdit,
            self.maintainerEmailEdit,
        ]:
            lineEdit.setStyleSheet(self.__mandatoryStyleSheet)

        self.__populateClassifiers()

        self.__okButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Ok)
        self.__okButton.setEnabled(False)

        projectOpen = ericApp().getObject("Project").isOpen()
        self.projectButton.setEnabled(projectOpen)

        self.projectUrlsList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        self.entryPointsList.header().setSortIndicator(0, Qt.SortOrder.AscendingOrder)

        self.descriptionContentTypeComboBox.addItem("", "")
        for contentType, mimetype in sorted(
            [
                (self.tr("Plain Text"), "text/plain"),
                (self.tr("Markdown"), "text/markdown"),
                (self.tr("reStructuredText"), "text/x-rst"),
            ]
        ):
            self.descriptionContentTypeComboBox.addItem(contentType, mimetype)

        self.homePageUrlEdit.textChanged.connect(self.__enableOkButton)
        self.nameEdit.textChanged.connect(self.__enableOkButton)
        self.versionEdit.textChanged.connect(self.__enableOkButton)
        self.authorEdit.textChanged.connect(self.__enableOkButton)
        self.authorEmailEdit.textChanged.connect(self.__enableOkButton)
        self.maintainerEdit.textChanged.connect(self.__enableOkButton)
        self.maintainerEmailEdit.textChanged.connect(self.__enableOkButton)

    def __enableOkButton(self):
        """
        Private slot to set the state of the OK button.
        """
        enable = (
            bool(self.nameEdit.text())
            and bool(self.versionEdit.text())
            and bool(self.homePageUrlEdit.text())
            and (
                (bool(self.authorEdit.text()) and bool(self.authorEmailEdit.text()))
                or (
                    bool(self.maintainerEdit.text())
                    and bool(self.maintainerEmailEdit.text())
                )
            )
            and self.homePageUrlEdit.text().startswith(("http://", "https://"))
        )

        self.__okButton.setEnabled(enable)

    def __populateClassifiers(self):
        """
        Private method to populate the classifiers.
        """
        self.licenseClassifierComboBox.clear()
        self.classifiersList.clear()
        self.developmentStatusComboBox.clear()

        self.developmentStatusComboBox.addItem("", "")

        self.__classifiersDict = {}
        for classifier in trove_classifiers.sorted_classifiers:
            if classifier.startswith("License ::"):
                self.licenseClassifierComboBox.addItem(
                    "/".join(classifier.split(" :: ")[1:]), classifier
                )
            elif classifier.startswith("Development Status ::"):
                self.developmentStatusComboBox.addItem(
                    classifier.split(" :: ")[1], classifier
                )
            else:
                self.__addClassifierEntry(classifier)
        self.__classifiersDict = {}

        self.licenseClassifierComboBox.setCurrentIndex(
            self.licenseClassifierComboBox.findText(
                "(GPLv3)", Qt.MatchFlag.MatchContains | Qt.MatchFlag.MatchCaseSensitive
            )
        )

    def __addClassifierEntry(self, classifier):
        """
        Private method to add a new entry to the list of trove classifiers.

        @param classifier classifier containing the data for the entry
        @type str
        """
        itm = None
        pitm = None
        dataList = classifier.split(" :: ")
        for index in range(len(dataList)):
            key = " :: ".join(dataList[: index + 1])
            if key not in self.__classifiersDict:
                if pitm is None:
                    itm = QTreeWidgetItem(self.classifiersList, [dataList[index]])
                    pitm = itm
                else:
                    itm = QTreeWidgetItem(pitm, [dataList[index]])
                itm.setExpanded(True)
                self.__classifiersDict[key] = itm
            else:
                pitm = self.__classifiersDict[key]
        itm.setCheckState(0, Qt.CheckState.Unchecked)
        itm.setData(0, Qt.ItemDataRole.UserRole, classifier)

    def __getLicenseText(self):
        """
        Private method to get the license text.

        @return license text
        @rtype str
        """
        if not self.licenseClassifierCheckBox.isChecked():
            return self.licenseEdit.text()
        else:
            lic = self.licenseClassifierComboBox.currentText()
            if "(" in lic:
                lic = lic.rsplit("(", 1)[1].split(")", 1)[0]
            return lic

    def __getSetupPyCode(self, indLevel, indString):
        """
        Private method to get the source code for a 'setup.py' file.

        @param indLevel indentation level
        @type int
        @param indString string used for indentation (space or tab)
        @type str
        @return generated code
        @rtype str
        """
        # Note: all paths are created with '/'; setup will do the right thing

        # calculate our indentation level and the indentation string
        il = indLevel + 1
        istring = il * indString
        i1string = (il + 1) * indString
        i2string = (il + 2) * indString
        estring = os.linesep + indLevel * indString

        # now generate the code
        if self.introCheckBox.isChecked():
            sourceCode = "#!/usr/bin/env python3{0}".format(os.linesep)
            sourceCode += "# -*- coding: utf-8 -*-{0}{0}".format(os.linesep)
        else:
            sourceCode = ""

        if self.metaDataCheckBox.isChecked():
            sourceCode += "# metadata{0}".format(os.linesep)
            sourceCode += '"{0}"{1}'.format(
                self.summaryEdit.text() or "Setup routine", os.linesep
            )
            sourceCode += '__version__ = "{0}"{1}'.format(
                self.versionEdit.text(), os.linesep
            )
            sourceCode += '__license__ = "{0}"{1}'.format(
                self.__getLicenseText(), os.linesep
            )
            sourceCode += '__author__ = "{0}"{1}'.format(
                self.authorEdit.text() or self.maintainerEdit.text(), os.linesep
            )
            sourceCode += '__email__ = "{0}"{1}'.format(
                self.authorEmailEdit.text() or self.maintainerEmailEdit.text(),
                os.linesep,
            )
            sourceCode += '__url__ = "{0}"{1}'.format(
                self.homePageUrlEdit.text(), os.linesep
            )
            sourceCode += '__date__ = "{0}"{1}'.format(
                datetime.datetime.now(tz=datetime.timezone.utc)
                .isoformat()
                .split(".")[0],
                os.linesep,
            )
            sourceCode += '__prj__ = "{0}"{1}'.format(self.nameEdit.text(), os.linesep)
            sourceCode += os.linesep

        if self.importCheckBox.isChecked():
            additionalImport = ", find_packages"
            sourceCode += "from setuptools import setup{0}{1}".format(
                additionalImport, os.linesep
            )
        if sourceCode:
            sourceCode += "{0}{0}".format(os.linesep)

        if self.descriptionFromFilesCheckBox.isChecked():
            sourceCode += "def get_long_description():{0}".format(os.linesep)
            sourceCode += "{0}descr = []{1}".format(istring, os.linesep)
            sourceCode += '{0}for fname in ("{1}"):{2}'.format(
                istring,
                '", "'.join(self.descriptionEdit.toPlainText().splitlines()),
                os.linesep,
            )
            sourceCode += (
                '{0}with open(fname, "r", encoding="utf-8") as f:{1}'
            ).format(i1string, os.linesep)
            sourceCode += "{0}descr.append(f.read()){1}".format(i2string, os.linesep)
            sourceCode += '{0}return "\\n\\n".join(descr){1}'.format(
                istring, os.linesep
            )
            sourceCode += "{0}{0}".format(os.linesep)

        sourceCode += "setup({0}".format(os.linesep)
        sourceCode += '{0}name="{1}",{2}'.format(
            istring, self.nameEdit.text(), os.linesep
        )
        sourceCode += '{0}version="{1}",{2}'.format(
            istring, self.versionEdit.text(), os.linesep
        )

        if self.summaryEdit.text():
            sourceCode += '{0}description="{1}",{2}'.format(
                istring, self.summaryEdit.text(), os.linesep
            )

        if self.descriptionFromFilesCheckBox.isChecked():
            sourceCode += "{0}long_description=get_long_description(),{1}".format(
                istring, os.linesep
            )
        elif self.descriptionEdit.toPlainText():
            sourceCode += '{0}long_description="""{1}""",{2}'.format(
                istring, self.descriptionEdit.toPlainText(), os.linesep
            )

        if self.descriptionContentTypeComboBox.currentData():
            sourceCode += '{0}long_description_content_type="{1}",{2}'.format(
                istring, self.descriptionContentTypeComboBox.currentData(), os.linesep
            )

        if self.authorEdit.text():
            sourceCode += '{0}author="{1}",{2}'.format(
                istring, self.authorEdit.text(), os.linesep
            )
            sourceCode += '{0}author_email="{1}",{2}'.format(
                istring, self.authorEmailEdit.text(), os.linesep
            )

        if self.maintainerEdit.text():
            sourceCode += '{0}maintainer="{1}",{2}'.format(
                istring, self.maintainerEdit.text(), os.linesep
            )
            sourceCode += '{0}maintainer_email="{1}",{2}'.format(
                istring, self.maintainerEmailEdit.text(), os.linesep
            )

        sourceCode += '{0}url="{1}",{2}'.format(
            istring, self.homePageUrlEdit.text(), os.linesep
        )
        if self.downloadUrlEdit.text():
            sourceCode += '{0}download_url="{1}",{2}'.format(
                istring, self.downloadUrlEdit.text(), os.linesep
            )

        if self.projectUrlsList.topLevelItemCount():
            sourceCode += "{0}project_urls={{{1}".format(istring, os.linesep)
            for row in range(self.projectUrlsList.topLevelItemCount()):
                urlItem = self.projectUrlsList.topLevelItem(row)
                sourceCode += '{0}"{1}": "{2}",{3}'.format(
                    i1string, urlItem.text(0), urlItem.text(1), os.linesep
                )
            sourceCode += "{0}}},{1}".format(istring, os.linesep)

        classifiers = []
        if not self.licenseClassifierCheckBox.isChecked():
            sourceCode += '{0}license="{1}",{2}'.format(
                istring, self.licenseEdit.text(), os.linesep
            )
        else:
            classifiers.append(
                self.licenseClassifierComboBox.itemData(
                    self.licenseClassifierComboBox.currentIndex()
                )
            )

        platforms = self.platformsEdit.toPlainText().splitlines()
        if platforms:
            sourceCode += "{0}platforms=[{1}".format(istring, os.linesep)
            sourceCode += '{0}"{1}",{2}'.format(
                i1string,
                '",{0}{1}"'.format(os.linesep, i1string).join(platforms),
                os.linesep,
            )
            sourceCode += "{0}],{1}".format(istring, os.linesep)

        if self.developmentStatusComboBox.currentIndex() != 0:
            classifiers.append(self.developmentStatusComboBox.currentData())

        itm = self.classifiersList.topLevelItem(0)
        while itm:
            itm.setExpanded(True)
            if itm.checkState(0) == Qt.CheckState.Checked:
                classifiers.append(itm.data(0, Qt.ItemDataRole.UserRole))
            itm = self.classifiersList.itemBelow(itm)

        # cleanup classifiers list - remove all invalid entries
        classifiers = [c for c in classifiers if bool(c)]
        if classifiers:
            sourceCode += "{0}classifiers=[{1}".format(istring, os.linesep)
            sourceCode += '{0}"{1}",{2}'.format(
                i1string,
                '",{0}{1}"'.format(os.linesep, i1string).join(classifiers),
                os.linesep,
            )
            sourceCode += "{0}],{1}".format(istring, os.linesep)
        del classifiers

        if self.keywordsEdit.text():
            sourceCode += '{0}keywords="{1}",{2}'.format(
                istring, self.keywordsEdit.text(), os.linesep
            )

        if self.pyVersionEdit.text():
            sourceCode += '{0}python_requires="{1}",{2}'.format(
                istring, self.pyVersionEdit.text(), os.linesep
            )

        sourceCode += "{0}packages=find_packages(".format(istring)
        src = FileSystemUtilities.fromNativeSeparators(
            self.sourceDirectoryPicker.text()
        )
        excludePatterns = []
        for row in range(self.excludePatternList.count()):
            excludePatterns.append(self.excludePatternList.item(row).text())
        if src:
            sourceCode += '{0}{1}"{2}"'.format(os.linesep, i1string, src)
            if excludePatterns:
                sourceCode += ","
            else:
                sourceCode += "{0}{1}".format(os.linesep, istring)
        if excludePatterns:
            sourceCode += "{0}{1}exclude=[{0}".format(os.linesep, i1string)
            sourceCode += '{0}"{1}",{2}'.format(
                i2string,
                '",{0}{1}"'.format(os.linesep, i2string).join(excludePatterns),
                os.linesep,
            )
            sourceCode += "{0}]{1}{2}".format(i1string, os.linesep, istring)
        sourceCode += "),{0}".format(os.linesep)

        if self.includePackageDataCheckBox.isChecked():
            sourceCode += "{0}include_package_data = True,{1}".format(
                istring, os.linesep
            )

        modules = []
        for row in range(self.modulesList.count()):
            modules.append(self.modulesList.item(row).text())
        if modules:
            sourceCode += "{0}py_modules=[{1}".format(istring, os.linesep)
            sourceCode += '{0}"{1}",{2}'.format(
                i1string,
                '",{0}{1}"'.format(os.linesep, i1string).join(modules),
                os.linesep,
            )
            sourceCode += "{0}],{1}".format(istring, os.linesep)
        del modules

        if self.entryPointsList.topLevelItemCount():
            entryPoints = {
                "console_scripts": [],
                "gui_scripts": [],
            }
            for row in range(self.entryPointsList.topLevelItemCount()):
                itm = self.entryPointsList.topLevelItem(row)
                entryPoints[itm.data(0, Qt.ItemDataRole.UserRole)].append(
                    "{0} = {1}".format(itm.text(1), itm.text(2))
                )
            sourceCode += "{0}entry_points={{{1}".format(istring, os.linesep)
            for epCategory in entryPoints:
                if entryPoints[epCategory]:
                    sourceCode += '{0}"{1}": [{2}'.format(
                        i1string, epCategory, os.linesep
                    )
                    for entryPoint in entryPoints[epCategory]:
                        sourceCode += '{0}"{1}",{2}'.format(
                            i2string, entryPoint, os.linesep
                        )
                    sourceCode += "{0}],{1}".format(i1string, os.linesep)
            sourceCode += "{0}}},{1}".format(istring, os.linesep)

        sourceCode += "){0}".format(estring)
        return sourceCode

    def __getSetupCfgCode(self):
        """
        Private method to get the source code for a 'setup.cfg' file.

        @return generated code
        @rtype str
        """
        from . import SetupCfgUtilities

        metadata = {
            "name": self.nameEdit.text(),
            "version": self.versionEdit.text(),
        }

        if self.summaryEdit.text():
            metadata["description"] = self.summaryEdit.text()

        if self.descriptionEdit.toPlainText():
            metadata["long_description"] = (
                "file: {0}".format(
                    ", ".join(self.descriptionEdit.toPlainText().splitlines())
                )
                if self.descriptionFromFilesCheckBox.isChecked()
                else self.descriptionEdit.toPlainText()
            )

        if self.descriptionContentTypeComboBox.currentData():
            metadata["long_description_content_type"] = (
                self.descriptionContentTypeComboBox.currentData()
            )

        if self.authorEdit.text():
            metadata["author"] = self.authorEdit.text()
            metadata["author_email"] = self.authorEmailEdit.text()

        if self.maintainerEdit.text():
            metadata["maintainer"] = self.maintainerEdit.text()
            metadata["maintainer_email"] = self.maintainerEmailEdit.text()

        metadata["url"] = self.homePageUrlEdit.text()
        if self.downloadUrlEdit.text():
            metadata["download_url"] = self.downloadUrlEdit.text()

        if self.projectUrlsList.topLevelItemCount():
            projectURLs = {}
            for row in range(self.projectUrlsList.topLevelItemCount()):
                urlItem = self.projectUrlsList.topLevelItem(row)
                projectURLs[urlItem.text(0)] = urlItem.text(1)
            metadata["project_urls"] = SetupCfgUtilities.toString(projectURLs)

        classifiers = []
        if not self.licenseClassifierCheckBox.isChecked():
            metadata["license"] = self.licenseEdit.text()
        else:
            classifiers.append(
                self.licenseClassifierComboBox.itemData(
                    self.licenseClassifierComboBox.currentIndex()
                )
            )

        platforms = self.platformsEdit.toPlainText().splitlines()
        if platforms:
            metadata["platforms"] = SetupCfgUtilities.toString(platforms)

        if self.developmentStatusComboBox.currentIndex() != 0:
            classifiers.append(self.developmentStatusComboBox.currentData())

        itm = self.classifiersList.topLevelItem(0)
        while itm:
            itm.setExpanded(True)
            if itm.checkState(0) == Qt.CheckState.Checked:
                classifiers.append(itm.data(0, Qt.ItemDataRole.UserRole))
            itm = self.classifiersList.itemBelow(itm)

        # cleanup classifiers list - remove all invalid entries
        classifiers = [c for c in classifiers if bool(c)]
        if classifiers:
            metadata["classifiers"] = SetupCfgUtilities.toString(classifiers)

        if self.keywordsEdit.text():
            metadata["keywords"] = SetupCfgUtilities.toString(
                self.keywordsEdit.text().split()
            )

        options = {"packages": "find:"}

        if self.pyVersionEdit.text():
            options["python_requires"] = self.pyVersionEdit.text()

        findOptions = {}
        src = FileSystemUtilities.fromNativeSeparators(
            self.sourceDirectoryPicker.text()
        )
        excludePatterns = []
        for row in range(self.excludePatternList.count()):
            excludePatterns.append(self.excludePatternList.item(row).text())
        if src:
            options["package_dir"] = SetupCfgUtilities.toString({"": src})
            findOptions["where"] = src
        if excludePatterns:
            findOptions["exclude"] = SetupCfgUtilities.toString(excludePatterns)

        if self.includePackageDataCheckBox.isChecked():
            options["include_package_data"] = SetupCfgUtilities.toString(True)
            packageData = {}  # placeholder section
        else:
            packageData = None

        modules = []
        for row in range(self.modulesList.count()):
            modules.append(self.modulesList.item(row).text())
        if modules:
            options["py_modules"] = SetupCfgUtilities.toString(modules)

        if self.entryPointsList.topLevelItemCount():
            entryPoints = {
                "console_scripts": {},
                "gui_scripts": {},
            }
            for row in range(self.entryPointsList.topLevelItemCount()):
                itm = self.entryPointsList.topLevelItem(row)
                entryPoints[itm.data(0, Qt.ItemDataRole.UserRole)][itm.text(1)] = (
                    itm.text(2)
                )
            for epType in list(entryPoints):
                if entryPoints[epType]:
                    entryPoints[epType] = SetupCfgUtilities.toString(
                        entryPoints[epType]
                    )
                else:
                    del entryPoints[epType]
        else:
            entryPoints = {}

        configDict = {
            "metadata": metadata,
            "options": options,
            "options.packages.find": findOptions,
        }
        if packageData is not None:
            configDict["options.package_data"] = packageData
        if entryPoints:
            configDict["options.entry_points"] = entryPoints

        cparser = configparser.ConfigParser()
        cparser.read_dict(configDict)
        sio = io.StringIO()
        cparser.write(sio)
        sourceCode = sio.getvalue()
        return sourceCode

    def __getPyprojectCode(self):
        """
        Private method to get the source code for a 'pyproject.toml' file.

        @return generated code
        @rtype str
        """
        doc = tomlkit.document()

        buildSystem = tomlkit.table()
        buildSystem["requires"] = ["setuptools>=61.0.0", "wheel"]
        buildSystem["build-backend"] = "setuptools.build_meta"
        doc["build-system"] = buildSystem

        project = tomlkit.table()
        project["name"] = self.nameEdit.text()
        project["version"] = self.versionEdit.text()

        if self.summaryEdit.text():
            project["description"] = self.summaryEdit.text()

        if self.descriptionEdit.toPlainText():
            if self.descriptionFromFilesCheckBox.isChecked():
                project["readme"] = self.descriptionEdit.toPlainText().splitlines()[0]
            else:
                readme = tomlkit.table()
                readme["text"] = self.descriptionEdit.toPlainText()
                readme["content-type"] = (
                    self.descriptionContentTypeComboBox.currentData()
                )
                project["readme"] = readme

        if self.authorEdit.text():
            authors = tomlkit.array()
            author = tomlkit.inline_table()
            author["name"] = self.authorEdit.text()
            authors.add_line(author)
            author = tomlkit.inline_table()
            author["name"] = self.authorEdit.text()
            author["email"] = self.authorEmailEdit.text()
            authors.add_line(author)
            authors.append(tomlkit.nl())
            project["authors"] = authors

        if self.maintainerEdit.text():
            maintainers = tomlkit.array()
            maintainer = tomlkit.inline_table()
            maintainer["name"] = self.maintainerEdit.text()
            maintainers.add_line(maintainer)
            maintainer = tomlkit.inline_table()
            maintainer["name"] = self.maintainerEdit.text()
            maintainer["email"] = self.maintainerEmailEdit.text()
            maintainers.add_line(maintainer)
            maintainers.append(tomlkit.nl())
            project["maintainers"] = maintainers

        urls = tomlkit.table()
        urls["Homepage"] = self.homePageUrlEdit.text()
        if self.downloadUrlEdit.text():
            urls["Download"] = self.downloadUrlEdit.text()

        if self.projectUrlsList.topLevelItemCount():
            for row in range(self.projectUrlsList.topLevelItemCount()):
                urlItem = self.projectUrlsList.topLevelItem(row)
                urls[urlItem.text(0)] = urlItem.text(1)
        project["urls"] = urls

        classifiers = []
        if not self.licenseClassifierCheckBox.isChecked():
            licenseTbl = tomlkit.table()
            licenseTbl["text"] = self.licenseEdit.text()
            project["license"] = licenseTbl
        else:
            classifiers.append(
                self.licenseClassifierComboBox.itemData(
                    self.licenseClassifierComboBox.currentIndex()
                )
            )

        if self.developmentStatusComboBox.currentIndex() != 0:
            classifiers.append(self.developmentStatusComboBox.currentData())

        itm = self.classifiersList.topLevelItem(0)
        while itm:
            itm.setExpanded(True)
            if itm.checkState(0) == Qt.CheckState.Checked:
                classifiers.append(itm.data(0, Qt.ItemDataRole.UserRole))
            itm = self.classifiersList.itemBelow(itm)

        # cleanup classifiers list - remove all invalid entries
        classifiers = [c for c in classifiers if bool(c)]
        if classifiers:
            classifiersArray = tomlkit.array()
            for classifier in classifiers:
                classifiersArray.add_line(classifier)
            classifiersArray.append(tomlkit.nl())
            project["classifiers"] = classifiersArray

        if self.keywordsEdit.text():
            keywords = tomlkit.array()
            for kw in self.keywordsEdit.text().split():
                keywords.add_line(kw)
            keywords.append(tomlkit.nl())
            project["keywords"] = keywords

        if self.pyVersionEdit.text():
            project["requires-python"] = self.pyVersionEdit.text()

        if self.entryPointsList.topLevelItemCount():
            entryPoints = {
                "console_scripts": {},
                "gui_scripts": {},
            }
            for row in range(self.entryPointsList.topLevelItemCount()):
                itm = self.entryPointsList.topLevelItem(row)
                entryPoints[itm.data(0, Qt.ItemDataRole.UserRole)][itm.text(1)] = (
                    itm.text(2)
                )

            if entryPoints["console_scripts"]:
                scripts = tomlkit.table()
                for name, function in entryPoints["console_scripts"].items():
                    scripts[name] = function
                project["scripts"] = scripts

            if entryPoints["gui_scripts"]:
                guiScripts = tomlkit.table()
                for name, function in entryPoints["gui_scripts"].items():
                    guiScripts[name] = function
                project["gui-scripts"] = guiScripts

        # placeholder
        dependencies = tomlkit.array()
        dependencies.append(
            tomlkit.comment("TODO: enter project dependencies ")  # __NO-TASK__
        )
        project["dependencies"] = dependencies

        doc["project"] = project

        setuptools = tomlkit.table()

        platforms = self.platformsEdit.toPlainText().splitlines()
        if platforms:
            platformsArray = tomlkit.array()
            for plt in platforms:
                platformsArray.add_line(plt)
            platformsArray.append(tomlkit.nl())
            setuptools["platforms"] = platformsArray

        setuptools["include-package-data"] = self.includePackageDataCheckBox.isChecked()
        if self.includePackageDataCheckBox.isChecked():
            # placeholder
            setuptools["package-data"] = tomlkit.table()
            setuptools["package-data"].add(
                tomlkit.comment("TODO: enter package data patterns")  # __NO-TASK__
            )

        if self.modulesList.count():
            modulesArray = tomlkit.array()
            for row in range(self.modulesList.count()):
                modulesArray.add_line(self.modulesList.item(row).text())
            modulesArray.append(tomlkit.nl())
            setuptools["py-modules"] = modulesArray

        findspec = tomlkit.table()
        src = FileSystemUtilities.fromNativeSeparators(
            self.sourceDirectoryPicker.text()
        )
        excludePatterns = []
        for row in range(self.excludePatternList.count()):
            excludePatterns.append(self.excludePatternList.item(row).text())
        if src:
            findspec["where"] = [ericApp().getObject("Project").getRelativePath(src)]
        if excludePatterns:
            excludePatternsArray = tomlkit.array()
            for pattern in excludePatterns:
                excludePatternsArray.add_line(pattern)
            excludePatternsArray.append(tomlkit.nl())
            findspec["exclude"] = excludePatternsArray

        if bool(findspec):
            setuptools["packages"] = tomlkit.table(is_super_table=True)
            setuptools["packages"]["find"] = findspec

        doc["tool"] = tomlkit.table(is_super_table=True)
        doc["tool"]["setuptools"] = setuptools

        sourceCode = tomlkit.dumps(doc)
        return sourceCode

    @pyqtSlot()
    def accept(self):
        """
        Public slot to handle pressing the OK button.
        """
        line, index = self.__editor.getCursorPosition()
        indLevel = self.__editor.indentation(line) // self.__editor.indentationWidth()
        indString = (
            "\t"
            if self.__editor.indentationsUseTabs()
            else self.__editor.indentationWidth() * " "
        )

        if self.__category == "setup.py":
            sourceCode = self.__getSetupPyCode(indLevel, indString)
        elif self.__category == "setup.cfg":
            sourceCode = self.__getSetupCfgCode()
        elif self.__category == "pyproject.toml":
            sourceCode = self.__getPyprojectCode()
        else:
            # should not happen, but play it safe
            sourceCode = ""

        if sourceCode:
            line, index = self.__editor.getCursorPosition()
            # It should be done this way to allow undo
            self.__editor.beginUndoAction()
            self.__editor.insertAt(sourceCode, line, index)
            self.__editor.endUndoAction()

        super().accept()

    @pyqtSlot()
    def on_projectButton_clicked(self):
        """
        Private slot to populate some fields with data retrieved from the
        current project.
        """
        project = ericApp().getObject("Project")

        self.nameEdit.setText(project.getProjectName())
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

        summary = description.split(".", 1)[0].replace("\r", "").replace("\n", "") + "."
        self.summaryEdit.setText(summary)
        self.descriptionEdit.setPlainText(description)

        self.packageRootPicker.setText(project.getProjectPath())

        # prevent overwriting of entries by disabling the button
        self.projectButton.setEnabled(False)

    def __getStartDir(self):
        """
        Private method to get the start directory for selection dialogs.

        @return start directory
        @rtype str
        """
        return Preferences.getMultiProject("Workspace") or OSUtilities.getHomeDir()

    @pyqtSlot()
    def on_entryPointsList_itemSelectionChanged(self):
        """
        Private slot to handle a change of selected items of the
        entry points list.
        """
        self.deleteEntryPointButton.setEnabled(
            bool(self.entryPointsList.selectedItems())
        )
        self.editEntryPointButton.setEnabled(
            len(self.entryPointsList.selectedItems()) == 1
        )

    @pyqtSlot()
    def on_deleteEntryPointButton_clicked(self):
        """
        Private slot to delete the selected entry point items.
        """
        for itm in self.entryPointsList.selectedItems():
            self.entryPointsList.takeTopLevelItem(self.entryPointsList.row(itm))
            del itm

    @pyqtSlot()
    def on_addEntryPointButton_clicked(self):
        """
        Private slot to add an entry point to the list.
        """
        project = ericApp().getObject("Project")
        rootDir = project.getProjectPath() if project.isOpen() else ""
        dlg = AddEntryPointDialog(rootDir, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            epType, epCategory, name, script = dlg.getEntryPoint()
            itm = QTreeWidgetItem(self.entryPointsList, [epType, name, script])
            itm.setData(0, Qt.ItemDataRole.UserRole, epCategory)

    @pyqtSlot()
    def on_editEntryPointButton_clicked(self):
        """
        Private slot to edit the selected entry point.
        """
        project = ericApp().getObject("Project")
        rootDir = project.getProjectPath() if project.isOpen() else ""
        itm = self.entryPointsList.selectedItems()[0]
        dlg = AddEntryPointDialog(
            rootDir,
            epType=itm.text(0),
            name=itm.text(1),
            script=itm.text(2),
            parent=self,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            epType, epCategory, name, script = dlg.getEntryPoint()
            itm.setText(0, epType)
            itm.setText(1, name)
            itm.setText(2, script)
            itm.setData(0, Qt.ItemDataRole.UserRole, epCategory)

    @pyqtSlot()
    def on_modulesList_itemSelectionChanged(self):
        """
        Private slot to handle a change of selected items of the
        modules list.
        """
        self.deleteModuleButton.setEnabled(bool(self.modulesList.selectedItems()))

    @pyqtSlot()
    def on_deleteModuleButton_clicked(self):
        """
        Private slot to delete the selected module items.
        """
        for itm in self.modulesList.selectedItems():
            self.modulesList.takeItem(self.modulesList.row(itm))
            del itm

    @pyqtSlot()
    def on_addModuleButton_clicked(self):
        """
        Private slot to add Python modules to the list.
        """
        startDir = self.packageRootPicker.text() or self.__getStartDir()
        modulesList = EricFileDialog.getOpenFileNames(
            self,
            self.tr("Add Python Modules"),
            startDir,
            self.tr("Python Files (*.py)"),
        )
        for module in modulesList:
            module = module.replace(
                FileSystemUtilities.toNativeSeparators(startDir), ""
            )
            if module.startswith(("\\", "/")):
                module = module[1:]
            if module:
                QListWidgetItem(
                    str(pathlib.Path(module).with_suffix(""))
                    .replace("\\", ".")
                    .replace("/", "."),
                    self.modulesList,
                )

    @pyqtSlot()
    def on_excludePatternList_itemSelectionChanged(self):
        """
        Private slot to handle a change of selected items of the
        exclude pattern list.
        """
        self.deleteExcludePatternButton.setEnabled(
            bool(self.excludePatternList.selectedItems())
        )

    @pyqtSlot()
    def on_deleteExcludePatternButton_clicked(self):
        """
        Private slot to delete the selected exclude pattern items.
        """
        for itm in self.excludePatternList.selectedItems():
            self.excludePatternList.takeItem(self.excludePatternList.row(itm))
            del itm

    @pyqtSlot()
    def on_addExludePatternButton_clicked(self):
        """
        Private slot to add an exclude pattern to the list.
        """
        pattern = self.excludePatternEdit.text().replace("\\", ".").replace("/", ".")
        if not self.excludePatternList.findItems(
            pattern, Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive
        ):
            QListWidgetItem(pattern, self.excludePatternList)

    @pyqtSlot(str)
    def on_excludePatternEdit_textChanged(self, txt):
        """
        Private slot to handle a change of the exclude pattern text.

        @param txt text of the line edit
        @type str
        """
        self.addExludePatternButton.setEnabled(bool(txt))

    @pyqtSlot()
    def on_excludePatternEdit_returnPressed(self):
        """
        Private slot handling a press of the return button of the
        exclude pattern edit.
        """
        self.on_addExludePatternButton_clicked()

    @pyqtSlot()
    def on_urlDeleteButton_clicked(self):
        """
        Private slot to delete the selected URL items.
        """
        for itm in self.projectUrlsList.selectedItems():
            self.projectUrlsList.takeTopLevelItem(self.projectUrlsList.row(itm))
            del itm

    @pyqtSlot()
    def on_urlAddButton_clicked(self):
        """
        Private slot to add a project URL to the list.
        """
        dlg = AddProjectUrlDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, url = dlg.getUrl()
            QTreeWidgetItem(self.projectUrlsList, [name, url])

    @pyqtSlot()
    def on_urlEditButton_clicked(self):
        """
        Private slot to edit the selected project URL.
        """
        itm = self.projectUrlsList.selectedItems()[0]
        dlg = AddProjectUrlDialog(name=itm.text(0), url=itm.text(1), parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            name, url = dlg.getUrl()
            itm.setText(0, name)
            itm.setText(1, url)

    @pyqtSlot()
    def on_projectUrlsList_itemSelectionChanged(self):
        """
        Private slot to handle a change of selected items of the
        project URLs list.
        """
        self.urlDeleteButton.setEnabled(bool(self.projectUrlsList.selectedItems()))
        self.urlEditButton.setEnabled(len(self.projectUrlsList.selectedItems()) == 1)
