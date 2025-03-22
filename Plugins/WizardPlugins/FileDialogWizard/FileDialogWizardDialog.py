# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the file dialog wizard dialog.
"""

import os

from PyQt6.QtCore import QCoreApplication, QUrl, pyqtSlot
from PyQt6.QtWidgets import QButtonGroup, QDialog, QDialogButtonBox, QFileDialog

from eric7.EricWidgets.EricCompleters import EricDirCompleter, EricFileCompleter

from .Ui_FileDialogWizardDialog import Ui_FileDialogWizardDialog


class FileDialogWizardDialog(QDialog, Ui_FileDialogWizardDialog):
    """
    Class implementing the color dialog wizard dialog.

    It displays a dialog for entering the parameters for the
    EricFileDialog or QFileDialog code generator.
    """

    EricTypes = (
        (
            QCoreApplication.translate("FileDialogWizardDialog", "eric (String)"),
            "eric_string",
        ),
        (
            QCoreApplication.translate("FileDialogWizardDialog", "eric (pathlib.Path)"),
            "eric_pathlib",
        ),
    )
    PyQtTypes = (
        ("PyQt5", "pyqt5"),
        ("PyQt6", "pyqt6"),
    )

    def __init__(self, dialogVariant, parent=None):
        """
        Constructor

        @param dialogVariant variant of the file dialog to be generated
            (-2 = EricFileDialog (pathlib.Path based), -1 = EricFileDialog (string
            based), 0 = unknown, 5 = PyQt5, 6 = PyQt6)
        @type int
        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.eStartWithCompleter = EricFileCompleter(self.eStartWith)
        self.eWorkDirCompleter = EricDirCompleter(self.eWorkDir)

        self.__dialogVariant = dialogVariant

        self.__typeButtonsGroup = QButtonGroup(self)
        self.__typeButtonsGroup.setExclusive(True)
        self.__typeButtonsGroup.addButton(self.rOpenFile, 1)
        self.__typeButtonsGroup.addButton(self.rOpenFiles, 2)
        self.__typeButtonsGroup.addButton(self.rSaveFile, 3)
        self.__typeButtonsGroup.addButton(self.rfOpenFile, 11)
        self.__typeButtonsGroup.addButton(self.rfOpenFiles, 12)
        self.__typeButtonsGroup.addButton(self.rfSaveFile, 13)
        self.__typeButtonsGroup.addButton(self.rOpenFileUrl, 21)
        self.__typeButtonsGroup.addButton(self.rOpenFileUrls, 22)
        self.__typeButtonsGroup.addButton(self.rSaveFileUrl, 23)
        self.__typeButtonsGroup.addButton(self.rDirectory, 30)
        self.__typeButtonsGroup.addButton(self.rDirectoryUrl, 31)
        self.__typeButtonsGroup.idClicked.connect(self.__toggleInitialFilterAndResult)
        self.__toggleInitialFilterAndResult(1)

        if self.__dialogVariant < 0:
            for name, type_ in FileDialogWizardDialog.EricTypes:
                self.pyqtComboBox.addItem(name, type_)
            self.setWindowTitle(self.tr("EricFileDialog Wizard"))
            if self.__dialogVariant == -1:
                self.pyqtComboBox.setCurrentIndex(0)
            elif self.__dialogVariant == -2:
                self.pyqtComboBox.setCurrentIndex(1)
            else:
                self.pyqtComboBox.setCurrentIndex(0)
        else:
            for name, type_ in FileDialogWizardDialog.PyQtTypes:
                self.pyqtComboBox.addItem(name, type_)
            self.setWindowTitle(self.tr("QFileDialog Wizard"))
            if self.__dialogVariant == 5:
                self.pyqtComboBox.setCurrentIndex(0)
            elif self.__dialogVariant == 6:
                self.pyqtComboBox.setCurrentIndex(1)
            else:
                self.pyqtComboBox.setCurrentIndex(0)

        self.rSaveFile.toggled[bool].connect(self.__toggleConfirmCheckBox)
        self.rfSaveFile.toggled[bool].connect(self.__toggleConfirmCheckBox)
        self.rSaveFileUrl.toggled[bool].connect(self.__toggleConfirmCheckBox)
        self.rDirectory.toggled[bool].connect(self.__toggleGroupsAndTest)
        self.rDirectoryUrl.toggled[bool].connect(self.__toggleGroupsAndTest)
        self.cStartWith.toggled[bool].connect(self.__toggleGroupsAndTest)
        self.cWorkDir.toggled[bool].connect(self.__toggleGroupsAndTest)
        self.cFilters.toggled[bool].connect(self.__toggleGroupsAndTest)

        self.bTest = self.buttonBox.addButton(
            self.tr("Test"), QDialogButtonBox.ButtonRole.ActionRole
        )

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(int)
    def on_pyqtComboBox_currentIndexChanged(self, index):
        """
        Private slot to setup the dialog for the selected PyQt variant.

        @param index index of the current item
        @type int
        """
        txt = self.pyqtComboBox.itemData(index)
        self.rfOpenFile.setEnabled(txt.startswith("eric_"))
        self.rfOpenFiles.setEnabled(txt.startswith("eric_"))
        self.rfSaveFile.setEnabled(txt.startswith("eric_"))

        self.rOpenFileUrl.setEnabled(txt in ["pyqt5", "pyqt6"])
        self.rOpenFileUrls.setEnabled(txt in ["pyqt5", "pyqt6"])
        self.rSaveFileUrl.setEnabled(txt in ["pyqt5", "pyqt6"])
        self.rDirectoryUrl.setEnabled(txt in ["pyqt5", "pyqt6"])

        if txt in ["pyqt5", "pyqt6"]:
            if self.rfOpenFile.isChecked():
                self.rOpenFile.setChecked(True)
            elif self.rfOpenFiles.isChecked():
                self.rOpenFiles.setChecked(True)
            elif self.rfSaveFile.isChecked():
                self.rSaveFile.setChecked(True)
        else:
            if self.rOpenFileUrl.isChecked():
                self.rOpenFile.setChecked(True)
            if self.rOpenFileUrls.isChecked():
                self.rOpenFiles.setChecked(True)
            if self.rSaveFileUrl.isChecked():
                self.rSaveFile.setChecked(True)
            if self.rDirectoryUrl.isChecked():
                self.rDirectory.setChecked(True)

        if txt == "eric_string":
            self.__dialogVariant = -1
        elif txt == "eric_pathlib":
            self.__dialogVariant = -2
        elif txt == "PyQt5":
            self.__dialogVariant = 5
        elif txt == "PyQt6":
            self.__dialogVariant = 6
        else:
            # default is PyQt6
            self.__dialogVariant = 6

        self.__toggleInitialFilterAndResult(self.__typeButtonsGroup.checkedId())

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.bTest:
            self.on_bTest_clicked()

    @pyqtSlot()
    def on_bTest_clicked(self):
        """
        Private method to test the selected options.
        """
        if self.rOpenFile.isChecked() or self.rfOpenFile.isChecked():
            if not self.cSymlinks.isChecked():
                options = QFileDialog.Option.DontResolveSymlinks
            else:
                options = QFileDialog.Option(0)
            QFileDialog.getOpenFileName(
                None,
                self.eCaption.text(),
                self.eStartWith.text(),
                self.eFilters.text(),
                self.eInitialFilter.text(),
                options,
            )
        elif self.rOpenFileUrl.isChecked():
            if not self.cSymlinks.isChecked():
                options = QFileDialog.Option.DontResolveSymlinks
            else:
                options = QFileDialog.Option(0)
            QFileDialog.getOpenFileUrl(
                None,
                self.eCaption.text(),
                QUrl(self.eStartWith.text()),
                self.eFilters.text(),
                self.eInitialFilter.text(),
                options,
                self.schemesEdit.text().split(),
            )
        elif self.rOpenFiles.isChecked() or self.rfOpenFiles.isChecked():
            if not self.cSymlinks.isChecked():
                options = QFileDialog.Option.DontResolveSymlinks
            else:
                options = QFileDialog.Option(0)
            QFileDialog.getOpenFileNames(
                None,
                self.eCaption.text(),
                self.eStartWith.text(),
                self.eFilters.text(),
                self.eInitialFilter.text(),
                options,
            )
        elif self.rOpenFileUrls.isChecked():
            if not self.cSymlinks.isChecked():
                options = QFileDialog.Option.DontResolveSymlinks
            else:
                options = QFileDialog.Option(0)
            QFileDialog.getOpenFileUrls(
                None,
                self.eCaption.text(),
                QUrl(self.eStartWith.text()),
                self.eFilters.text(),
                self.eInitialFilter.text(),
                options,
                self.schemesEdit.text().split(),
            )
        elif self.rSaveFile.isChecked() or self.rfSaveFile.isChecked():
            if not self.cSymlinks.isChecked():
                options = QFileDialog.Option.DontResolveSymlinks
            else:
                options = QFileDialog.Option(0)
            QFileDialog.getSaveFileName(
                None,
                self.eCaption.text(),
                self.eStartWith.text(),
                self.eFilters.text(),
                self.eInitialFilter.text(),
                options,
            )
        elif self.rSaveFileUrl.isChecked():
            if not self.cSymlinks.isChecked():
                options = QFileDialog.Option.DontResolveSymlinks
            else:
                options = QFileDialog.Option(0)
            QFileDialog.getSaveFileUrl(
                None,
                self.eCaption.text(),
                QUrl(self.eStartWith.text()),
                self.eFilters.text(),
                self.eInitialFilter.text(),
                options,
                self.schemesEdit.text().split(),
            )
        elif self.rDirectory.isChecked():
            options = QFileDialog.Option(0)
            if not self.cSymlinks.isChecked():
                options |= QFileDialog.Option.DontResolveSymlinks
            if self.cDirOnly.isChecked():
                options |= QFileDialog.Option.ShowDirsOnly
            else:
                options |= QFileDialog.Option(0)
            QFileDialog.getExistingDirectory(
                None, self.eCaption.text(), self.eWorkDir.text(), options
            )
        elif self.rDirectoryUrl.isChecked():
            options = QFileDialog.Option(0)
            if not self.cSymlinks.isChecked():
                options |= QFileDialog.Option.DontResolveSymlinks
            if self.cDirOnly.isChecked():
                options |= QFileDialog.Option.ShowDirsOnly
            else:
                options |= QFileDialog.Option(0)
            QFileDialog.getExistingDirectoryUrl(
                None,
                self.eCaption.text(),
                QUrl(self.eWorkDir.text()),
                options,
                self.schemesEdit.text().split(),
            )

    def __toggleConfirmCheckBox(self):
        """
        Private slot to enable/disable the confirmation check box.
        """
        self.cConfirmOverwrite.setEnabled(
            self.rSaveFile.isChecked()
            or self.rfSaveFile.isChecked()
            or self.rSaveFileUrl.isChecked()
        )

    def __toggleGroupsAndTest(self):
        """
        Private slot to enable/disable certain groups and the test button.
        """
        if self.rDirectory.isChecked() or self.rDirectoryUrl.isChecked():
            self.filePropertiesGroup.setEnabled(False)
            self.dirPropertiesGroup.setEnabled(True)
            self.bTest.setDisabled(self.cWorkDir.isChecked())
        else:
            self.filePropertiesGroup.setEnabled(True)
            self.dirPropertiesGroup.setEnabled(False)
            self.bTest.setDisabled(
                self.cStartWith.isChecked() or self.cFilters.isChecked()
            )

    def __toggleInitialFilterAndResult(self, checkedId):
        """
        Private slot to enable/disable the initial filter elements and the
        results entries.

        @param checkedId id of the clicked button
        @type int
        """
        enable = (
            self.__dialogVariant in (-1, -2) and checkedId in [1, 2, 3, 11, 12, 13]
        ) or (self.__dialogVariant in (5, 6) and checkedId in [1, 2, 3, 21, 22, 23])

        self.lInitialFilter.setEnabled(enable)
        self.eInitialFilter.setEnabled(enable)
        self.cInitialFilter.setEnabled(enable)

        self.lFilterVariable.setEnabled(enable)
        self.eFilterVariable.setEnabled(enable)

        self.urlPropertiesGroup.setEnabled(checkedId in (21, 22, 23, 31))

    def getCode(self, indLevel, indString):
        """
        Public method to get the source code for Qt6.

        @param indLevel indentation level
        @type int
        @param indString string used for indentation (space or tab)
        @type str
        @return generated code
        @rtype str
        """
        # calculate our indentation level and the indentation string
        il = indLevel + 1
        istring = il * indString
        estring = os.linesep + indLevel * indString

        # now generate the code
        if self.parentSelf.isChecked():
            parent = "self"
        elif self.parentNone.isChecked():
            parent = "None"
        elif self.parentOther.isChecked():
            parent = self.parentEdit.text()
            if parent == "":
                parent = "None"

        # prepare the result variables
        nameVariable = self.eNameVariable.text()
        if not nameVariable:
            if self.__typeButtonsGroup.checkedButton() in [
                self.rOpenFile,
                self.rfOpenFile,
                self.rSaveFile,
                self.rfSaveFile,
            ]:
                nameVariable = "filePath" if self.__dialogVariant == -2 else "fileName"
            elif self.__typeButtonsGroup.checkedButton() in [
                self.rOpenFiles,
                self.rfOpenFiles,
            ]:
                nameVariable = (
                    "filePaths" if self.__dialogVariant == -2 else "fileNames"
                )
            elif self.__typeButtonsGroup.checkedButton() == self.rDirectory:
                nameVariable = "dirPath" if self.__dialogVariant == -2 else "dirName"
            else:
                nameVariable = "res"
        filterVariable = self.eFilterVariable.text()
        if not filterVariable:
            if (
                self.__dialogVariant in (-1,)
                and self.__typeButtonsGroup.checkedButton()
                in [self.rfOpenFile, self.rfOpenFiles, self.rfSaveFile]
            ) or (
                self.__dialogVariant in (5, 6)
                and self.__typeButtonsGroup.checkedButton()
                in [self.rOpenFile, self.rOpenFiles, self.rSaveFile]
            ):
                filterVariable = ", selectedFilter"
            else:
                filterVariable = ""
        else:
            filterVariable = ", " + filterVariable

        if self.__dialogVariant in (-1, -2):
            dialogType = "EricFileDialog"
            optionStr = ""
        else:
            dialogType = "QFileDialog"
            optionStr = ".Option"

        code = "{0}{1} = {2}.".format(nameVariable, filterVariable, dialogType)
        if (
            self.rOpenFile.isChecked()
            or self.rfOpenFile.isChecked()
            or self.rOpenFileUrl.isChecked()
        ):
            #
            # getOpenFile...
            #
            if self.rOpenFile.isChecked():
                method = (
                    "getOpenFilePath"
                    if self.__dialogVariant == -2
                    else "getOpenFileName"
                )
                code += "{0}({1}{2}".format(method, os.linesep, istring)
            elif self.rOpenFileUrl.isChecked():
                code += "getOpenFileUrl({0}{1}".format(os.linesep, istring)
            else:
                method = (
                    "getOpenFilePathAndFilter"
                    if self.__dialogVariant == -2
                    else "getOpenFileNameAndFilter"
                )
                code += "{0}({1}{2}".format(method, os.linesep, istring)
            code += "{0},{1}{2}".format(parent, os.linesep, istring)
            if not self.eCaption.text():
                code += '"",{0}{1}'.format(os.linesep, istring)
            else:
                code += 'self.tr("{0}"),{1}{2}'.format(
                    self.eCaption.text(), os.linesep, istring
                )
            if self.rOpenFileUrl.isChecked():
                if not self.eStartWith.text():
                    code += "QUrl(),{0}{1}".format(os.linesep, istring)
                else:
                    if self.cStartWith.isChecked():
                        fmt = "{0},{1}{2}"
                    else:
                        fmt = 'QUrl("{0}"),{1}{2}'
                    code += fmt.format(self.eStartWith.text(), os.linesep, istring)
            else:
                if not self.eStartWith.text():
                    code += '"",{0}{1}'.format(os.linesep, istring)
                else:
                    if self.cStartWith.isChecked():
                        fmt = "{0},{1}{2}"
                    else:
                        fmt = '"{0}",{1}{2}'
                    code += fmt.format(self.eStartWith.text(), os.linesep, istring)
            if self.eFilters.text() == "":
                code += '""'
            else:
                if self.cFilters.isChecked():
                    fmt = "{0}"
                else:
                    fmt = 'self.tr("{0}")'
                code += fmt.format(self.eFilters.text())
            if self.eInitialFilter.text() == "":
                initialFilter = "None"
            else:
                if self.cInitialFilter.isChecked():
                    fmt = "{0}"
                else:
                    fmt = 'self.tr("{0}")'
                initialFilter = fmt.format(self.eInitialFilter.text())
            code += ",{0}{1}{2}".format(os.linesep, istring, initialFilter)
            if not self.cSymlinks.isChecked():
                code += ",{0}{1}{2}{3}.DontResolveSymlinks".format(
                    os.linesep, istring, dialogType, optionStr
                )
            if self.rOpenFileUrl.isChecked() and bool(self.schemesEdit.text()):
                code += ",{0}{1}{2}".format(
                    os.linesep, istring, self.__prepareSchemesList()
                )
            code += ",{0}){0}".format(estring)
        elif (
            self.rOpenFiles.isChecked()
            or self.rfOpenFiles.isChecked()
            or self.rOpenFileUrls.isChecked()
        ):
            #
            # getOpenFile...s
            #
            if self.rOpenFiles.isChecked():
                method = (
                    "getOpenFilePaths"
                    if self.__dialogVariant == -2
                    else "getOpenFileNames"
                )
                code += "{0}({1}{2}".format(method, os.linesep, istring)
            elif self.rOpenFileUrls.isChecked():
                code += "getOpenFileUrls({0}{1}".format(os.linesep, istring)
            else:
                method = (
                    "getOpenFilePathsAndFilter"
                    if self.__dialogVariant == -2
                    else "getOpenFileNamesAndFilter"
                )
                code += "{0}({1}{2}".format(method, os.linesep, istring)
            code += "{0},{1}{2}".format(parent, os.linesep, istring)
            if not self.eCaption.text():
                code += '"",{0}{1}'.format(os.linesep, istring)
            else:
                code += 'self.tr("{0}"),{1}{2}'.format(
                    self.eCaption.text(), os.linesep, istring
                )
            if self.rOpenFileUrls.isChecked():
                if not self.eStartWith.text():
                    code += "QUrl(),{0}{1}".format(os.linesep, istring)
                else:
                    if self.cStartWith.isChecked():
                        fmt = "{0},{1}{2}"
                    else:
                        fmt = 'QUrl("{0}"),{1}{2}'
                    code += fmt.format(self.eStartWith.text(), os.linesep, istring)
            else:
                if not self.eStartWith.text():
                    code += '"",{0}{1}'.format(os.linesep, istring)
                else:
                    if self.cStartWith.isChecked():
                        fmt = "{0},{1}{2}"
                    else:
                        fmt = '"{0}",{1}{2}'
                    code += fmt.format(self.eStartWith.text(), os.linesep, istring)
            if not self.eFilters.text():
                code += '""'
            else:
                if self.cFilters.isChecked():
                    fmt = "{0}"
                else:
                    fmt = 'self.tr("{0}")'
                code += fmt.format(self.eFilters.text())
            if self.eInitialFilter.text() == "":
                initialFilter = "None"
            else:
                if self.cInitialFilter.isChecked():
                    fmt = "{0}"
                else:
                    fmt = 'self.tr("{0}")'
                initialFilter = fmt.format(self.eInitialFilter.text())
            code += ",{0}{1}{2}".format(os.linesep, istring, initialFilter)
            if not self.cSymlinks.isChecked():
                code += ",{0}{1}{2}{3}.DontResolveSymlinks".format(
                    os.linesep, istring, dialogType, optionStr
                )
            if self.rOpenFileUrls.isChecked() and bool(self.schemesEdit.text()):
                code += ",{0}{1}{2}".format(
                    os.linesep, istring, self.__prepareSchemesList()
                )
            code += ",{0}){0}".format(estring)
        elif (
            self.rSaveFile.isChecked()
            or self.rfSaveFile.isChecked()
            or self.rSaveFileUrl.isChecked()
        ):
            #
            # getSaveFile...
            #
            if self.rSaveFile.isChecked():
                method = (
                    "getSaveFilePath"
                    if self.__dialogVariant == -2
                    else "getSaveFileName"
                )
                code += "{0}({1}{2}".format(method, os.linesep, istring)
            elif self.rSaveFileUrl.isChecked():
                code += "getSaveFileUrl({0}{1}".format(os.linesep, istring)
            else:
                method = (
                    "getSaveFilePathAndFilter"
                    if self.__dialogVariant == -2
                    else "getSaveFileNameAndFilter"
                )
                code += "{0}({1}{2}".format(method, os.linesep, istring)
            code += "{0},{1}{2}".format(parent, os.linesep, istring)
            if not self.eCaption.text():
                code += '"",{0}{1}'.format(os.linesep, istring)
            else:
                code += 'self.tr("{0}"),{1}{2}'.format(
                    self.eCaption.text(), os.linesep, istring
                )
            if self.rSaveFileUrl.isChecked():
                if not self.eStartWith.text():
                    code += "QUrl(),{0}{1}".format(os.linesep, istring)
                else:
                    if self.cStartWith.isChecked():
                        fmt = "{0},{1}{2}"
                    else:
                        fmt = 'QUrl("{0}"),{1}{2}'
                    code += fmt.format(self.eStartWith.text(), os.linesep, istring)
            else:
                if not self.eStartWith.text():
                    code += '"",{0}{1}'.format(os.linesep, istring)
                else:
                    if self.cStartWith.isChecked():
                        fmt = "{0},{1}{2}"
                    else:
                        fmt = '"{0}",{1}{2}'
                    code += fmt.format(self.eStartWith.text(), os.linesep, istring)
            if not self.eFilters.text():
                code += '""'
            else:
                if self.cFilters.isChecked():
                    fmt = "{0}"
                else:
                    fmt = 'self.tr("{0}")'
                code += fmt.format(self.eFilters.text())
            if self.eInitialFilter.text() == "":
                initialFilter = "None"
            else:
                if self.cInitialFilter.isChecked():
                    fmt = "{0}"
                else:
                    fmt = 'self.tr("{0}")'
                initialFilter = fmt.format(self.eInitialFilter.text())
            code += ",{0}{1}{2}".format(os.linesep, istring, initialFilter)
            if (not self.cSymlinks.isChecked()) or (
                not self.cConfirmOverwrite.isChecked()
            ):
                code += ",{0}{1}".format(os.linesep, istring)
                if not self.cSymlinks.isChecked():
                    code += "{0}{1}.DontResolveSymlinks".format(dialogType, optionStr)
                if (not self.cSymlinks.isChecked()) and (
                    not self.cConfirmOverwrite.isChecked()
                ):
                    code += " | "
                if not self.cConfirmOverwrite.isChecked():
                    code += "{0}{1}.DontConfirmOverwrite".format(dialogType, optionStr)
            if self.rSaveFileUrl.isChecked() and bool(self.schemesEdit.text()):
                code += ",{0}{1}{2}".format(
                    os.linesep, istring, self.__prepareSchemesList()
                )

            code += ",{0}){0}".format(estring)
        elif self.rDirectory.isChecked() or self.rDirectoryUrl.isChecked():
            if self.rDirectory.isChecked():
                method = (
                    "getExistingDirectoryPath"
                    if self.__dialogVariant == -2
                    else "getExistingDirectory"
                )
                code += "{0}({1}{2}".format(method, os.linesep, istring)
            else:
                code += "getExistingDirectoryUrl({0}{1}".format(os.linesep, istring)
            code += "{0},{1}{2}".format(parent, os.linesep, istring)
            if not self.eCaption.text():
                code += '"",{0}{1}'.format(os.linesep, istring)
            else:
                code += 'self.tr("{0}"),{1}{2}'.format(
                    self.eCaption.text(), os.linesep, istring
                )
            if self.rDirectoryUrl.isChecked():
                if not self.eWorkDir.text():
                    code += "QUrl()"
                else:
                    if self.cWorkDir.isChecked():
                        fmt = "{0}"
                    else:
                        fmt = 'QUrl("{0}")'
                    code += fmt.format(self.eWorkDir.text())
            else:
                if not self.eWorkDir.text():
                    code += '""'
                else:
                    if self.cWorkDir.isChecked():
                        fmt = "{0}"
                    else:
                        fmt = '"{0}"'
                    code += fmt.format(self.eWorkDir.text())
            code += ",{0}{1}".format(os.linesep, istring)
            if (not self.cSymlinks.isChecked()) or self.cDirOnly.isChecked():
                if not self.cSymlinks.isChecked():
                    code += "{0}{1}.DontResolveSymlinks".format(dialogType, optionStr)
                if (not self.cSymlinks.isChecked()) and self.cDirOnly.isChecked():
                    code += " | "
                if self.cDirOnly.isChecked():
                    code += "{0}{1}.ShowDirsOnly".format(dialogType, optionStr)
            else:
                code += "{0}.Option(0)".format(dialogType)
            if self.rDirectoryUrl.isChecked():
                code += ",{0}{1}{2}".format(
                    os.linesep, istring, self.__prepareSchemesList()
                )
            code += ",{0}){0}".format(estring)

        return code

    def __prepareSchemesList(self):
        """
        Private method to prepare the list of supported schemes.

        @return string representation of the supported schemes
        @rtype str
        """
        return repr(self.schemesEdit.text().strip().split())
