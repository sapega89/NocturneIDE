# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the eric message box wizard dialog.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QAbstractButton, QDialog, QDialogButtonBox

from eric7.EricWidgets import EricMessageBox

from .Ui_EricMessageBoxWizardDialog import Ui_EricMessageBoxWizardDialog


class EricMessageBoxWizardDialog(QDialog, Ui_EricMessageBoxWizardDialog):
    """
    Class implementing the eric message box wizard dialog.

    It displays a dialog for entering the parameters
    for the EricMessageBox code generator.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        # keep the following three lists in sync
        self.buttonsList = [
            self.tr("No button"),
            self.tr("Abort"),
            self.tr("Apply"),
            self.tr("Cancel"),
            self.tr("Close"),
            self.tr("Discard"),
            self.tr("Help"),
            self.tr("Ignore"),
            self.tr("No"),
            self.tr("No to all"),
            self.tr("Ok"),
            self.tr("Open"),
            self.tr("Reset"),
            self.tr("Restore defaults"),
            self.tr("Retry"),
            self.tr("Save"),
            self.tr("Save all"),
            self.tr("Yes"),
            self.tr("Yes to all"),
        ]
        self.buttonsCodeListBinary = [
            EricMessageBox.NoButton,
            EricMessageBox.Abort,
            EricMessageBox.Apply,
            EricMessageBox.Cancel,
            EricMessageBox.Close,
            EricMessageBox.Discard,
            EricMessageBox.Help,
            EricMessageBox.Ignore,
            EricMessageBox.No,
            EricMessageBox.NoToAll,
            EricMessageBox.Ok,
            EricMessageBox.Open,
            EricMessageBox.Reset,
            EricMessageBox.RestoreDefaults,
            EricMessageBox.Retry,
            EricMessageBox.Save,
            EricMessageBox.SaveAll,
            EricMessageBox.Yes,
            EricMessageBox.YesToAll,
        ]
        self.buttonsCodeListText = [
            "EricMessageBox.NoButton",
            "EricMessageBox.Abort",
            "EricMessageBox.Apply",
            "EricMessageBox.Cancel",
            "EricMessageBox.Close",
            "EricMessageBox.Discard",
            "EricMessageBox.Help",
            "EricMessageBox.Ignore",
            "EricMessageBox.No",
            "EricMessageBox.NoToAll",
            "EricMessageBox.Ok",
            "EricMessageBox.Open",
            "EricMessageBox.Reset",
            "EricMessageBox.RestoreDefaults",
            "EricMessageBox.Retry",
            "EricMessageBox.Save",
            "EricMessageBox.SaveAll",
            "EricMessageBox.Yes",
            "EricMessageBox.YesToAll",
        ]

        self.defaultCombo.addItems(self.buttonsList)

        self.bTest = self.buttonBox.addButton(
            self.tr("Test"), QDialogButtonBox.ButtonRole.ActionRole
        )

        self.__enabledGroups()

    def __enabledGroups(self):
        """
        Private method to enable/disable some group boxes.
        """
        self.standardButtons.setEnabled(
            self.rInformation.isChecked()
            or self.rQuestion.isChecked()
            or self.rWarning.isChecked()
            or self.rCritical.isChecked()
            or self.rStandard.isChecked()
        )

        self.defaultButton.setEnabled(
            self.rInformation.isChecked()
            or self.rQuestion.isChecked()
            or self.rWarning.isChecked()
            or self.rCritical.isChecked()
        )

        self.iconBox.setEnabled(
            self.rYesNo.isChecked()
            or self.rRetryAbort.isChecked()
            or self.rStandard.isChecked()
        )

        self.bTest.setEnabled(not self.rStandard.isChecked())

        self.eMessage.setEnabled(not self.rAboutQt.isChecked())

    @pyqtSlot(bool)
    def on_rInformation_toggled(self, _on):
        """
        Private slot to handle the toggled signal of the rInformation
        radio button.

        @param _on toggle state (unused)
        @type bool
        """
        self.__enabledGroups()

    @pyqtSlot(bool)
    def on_rQuestion_toggled(self, _on):
        """
        Private slot to handle the toggled signal of the rQuestion
        radio button.

        @param _on toggle state (unused)
        @type bool
        """
        self.__enabledGroups()

    @pyqtSlot(bool)
    def on_rWarning_toggled(self, _on):
        """
        Private slot to handle the toggled signal of the rWarning
        radio button.

        @param _on toggle state (unused)
        @type bool
        """
        self.__enabledGroups()

    @pyqtSlot(bool)
    def on_rCritical_toggled(self, _on):
        """
        Private slot to handle the toggled signal of the rCritical
        radio button.

        @param _on toggle state (unused)
        @type bool
        """
        self.__enabledGroups()

    @pyqtSlot(bool)
    def on_rYesNo_toggled(self, _on):
        """
        Private slot to handle the toggled signal of the rYesNo
        radio button.

        @param _on toggle state (unused)
        @type bool
        """
        self.__enabledGroups()

    @pyqtSlot(bool)
    def on_rRetryAbort_toggled(self, _on):
        """
        Private slot to handle the toggled signal of the rRetryAbort
        radio button.

        @param _on toggle state (unused)
        @type bool
        """
        self.__enabledGroups()

    @pyqtSlot(bool)
    def on_rOkToClearData_toggled(self, _on):
        """
        Private slot to handle the toggled signal of the rOkToClearData
        radio button.

        @param _on toggle state (unused)
        @type bool
        """
        self.__enabledGroups()

    @pyqtSlot(bool)
    def on_rAbout_toggled(self, _on):
        """
        Private slot to handle the toggled signal of the rAbout
        radio button.

        @param _on toggle state (unused)
        @type bool
        """
        self.__enabledGroups()

    @pyqtSlot(bool)
    def on_rAboutQt_toggled(self, _on):
        """
        Private slot to handle the toggled signal of the rAboutQt
        radio button.

        @param _on toggle state (unused)
        @type bool
        """
        self.__enabledGroups()

    @pyqtSlot(bool)
    def on_rStandard_toggled(self, _on):
        """
        Private slot to handle the toggled signal of the rStandard
        radio button.

        @param _on toggle state (unused)
        @type bool
        """
        self.__enabledGroups()

    @pyqtSlot(QAbstractButton)
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
        if self.rAbout.isChecked():
            EricMessageBox.about(
                None, self.eCaption.text(), self.eMessage.toPlainText()
            )
        elif self.rAboutQt.isChecked():
            EricMessageBox.aboutQt(None, self.eCaption.text())
        elif (
            self.rInformation.isChecked()
            or self.rQuestion.isChecked()
            or self.rWarning.isChecked()
            or self.rCritical.isChecked()
        ):
            buttons = EricMessageBox.NoButton
            if self.abortCheck.isChecked():
                buttons |= EricMessageBox.Abort
            if self.applyCheck.isChecked():
                buttons |= EricMessageBox.Apply
            if self.cancelCheck.isChecked():
                buttons |= EricMessageBox.Cancel
            if self.closeCheck.isChecked():
                buttons |= EricMessageBox.Close
            if self.discardCheck.isChecked():
                buttons |= EricMessageBox.Discard
            if self.helpCheck.isChecked():
                buttons |= EricMessageBox.Help
            if self.ignoreCheck.isChecked():
                buttons |= EricMessageBox.Ignore
            if self.noCheck.isChecked():
                buttons |= EricMessageBox.No
            if self.notoallCheck.isChecked():
                buttons |= EricMessageBox.NoToAll
            if self.okCheck.isChecked():
                buttons |= EricMessageBox.Ok
            if self.openCheck.isChecked():
                buttons |= EricMessageBox.Open
            if self.resetCheck.isChecked():
                buttons |= EricMessageBox.Reset
            if self.restoreCheck.isChecked():
                buttons |= EricMessageBox.RestoreDefaults
            if self.retryCheck.isChecked():
                buttons |= EricMessageBox.Retry
            if self.saveCheck.isChecked():
                buttons |= EricMessageBox.Save
            if self.saveallCheck.isChecked():
                buttons |= EricMessageBox.SaveAll
            if self.yesCheck.isChecked():
                buttons |= EricMessageBox.Yes
            if self.yestoallCheck.isChecked():
                buttons |= EricMessageBox.YesToAll
            if buttons == EricMessageBox.NoButton:
                buttons = EricMessageBox.Ok

            defaultButton = self.buttonsCodeListBinary[self.defaultCombo.currentIndex()]

            if self.rInformation.isChecked():
                EricMessageBox.information(
                    self,
                    self.eCaption.text(),
                    self.eMessage.toPlainText(),
                    buttons,
                    defaultButton,
                )
            elif self.rQuestion.isChecked():
                EricMessageBox.question(
                    self,
                    self.eCaption.text(),
                    self.eMessage.toPlainText(),
                    buttons,
                    defaultButton,
                )
            elif self.rWarning.isChecked():
                EricMessageBox.warning(
                    self,
                    self.eCaption.text(),
                    self.eMessage.toPlainText(),
                    buttons,
                    defaultButton,
                )
            elif self.rCritical.isChecked():
                EricMessageBox.critical(
                    self,
                    self.eCaption.text(),
                    self.eMessage.toPlainText(),
                    buttons,
                    defaultButton,
                )
        elif self.rYesNo.isChecked() or self.rRetryAbort.isChecked():
            if self.iconInformation.isChecked():
                icon = EricMessageBox.Information
            elif self.iconQuestion.isChecked():
                icon = EricMessageBox.Question
            elif self.iconWarning.isChecked():
                icon = EricMessageBox.Warning
            elif self.iconCritical.isChecked():
                icon = EricMessageBox.Critical

            if self.rYesNo.isChecked():
                EricMessageBox.yesNo(
                    self,
                    self.eCaption.text(),
                    self.eMessage.toPlainText(),
                    icon=icon,
                    yesDefault=self.yesDefaultCheck.isChecked(),
                )
            elif self.rRetryAbort.isChecked():
                EricMessageBox.retryAbort(
                    self, self.eCaption.text(), self.eMessage.toPlainText(), icon=icon
                )
        elif self.rOkToClearData.isChecked():
            EricMessageBox.okToClearData(
                self, self.eCaption.text(), self.eMessage.toPlainText(), lambda: True
            )

    def __getStandardButtonCode(self, istring, withIntro=True):
        """
        Private method to generate the button code for the standard buttons.

        @param istring indentation string
        @type str
        @param withIntro flag indicating to generate a first line
            with introductory text
        @type bool
        @return the button code
        @rtype str
        """
        buttons = []
        if self.abortCheck.isChecked():
            buttons.append("EricMessageBox.Abort")
        if self.applyCheck.isChecked():
            buttons.append("EricMessageBox.Apply")
        if self.cancelCheck.isChecked():
            buttons.append("EricMessageBox.Cancel")
        if self.closeCheck.isChecked():
            buttons.append("EricMessageBox.Close")
        if self.discardCheck.isChecked():
            buttons.append("EricMessageBox.Discard")
        if self.helpCheck.isChecked():
            buttons.append("EricMessageBox.Help")
        if self.ignoreCheck.isChecked():
            buttons.append("EricMessageBox.Ignore")
        if self.noCheck.isChecked():
            buttons.append("EricMessageBox.No")
        if self.notoallCheck.isChecked():
            buttons.append("EricMessageBox.NoToAll")
        if self.okCheck.isChecked():
            buttons.append("EricMessageBox.Ok")
        if self.openCheck.isChecked():
            buttons.append("EricMessageBox.Open")
        if self.resetCheck.isChecked():
            buttons.append("EricMessageBox.Reset")
        if self.restoreCheck.isChecked():
            buttons.append("EricMessageBox.RestoreDefaults")
        if self.retryCheck.isChecked():
            buttons.append("EricMessageBox.Retry")
        if self.saveCheck.isChecked():
            buttons.append("EricMessageBox.Save")
        if self.saveallCheck.isChecked():
            buttons.append("EricMessageBox.SaveAll")
        if self.yesCheck.isChecked():
            buttons.append("EricMessageBox.Yes")
        if self.yestoallCheck.isChecked():
            buttons.append("EricMessageBox.YesToAll")
        if len(buttons) == 0:
            return ""

        joinstring = "{0}{1}| ".format(os.linesep, istring)
        intro = "," if withIntro else ""
        btnCode = "{0}{1}{2}{3}".format(
            intro, os.linesep, istring, joinstring.join(buttons)
        )

        return btnCode

    def __getDefaultButtonCode(self, istring):
        """
        Private method to generate the button code for the default button.

        @param istring indentation string
        @type str
        @return the button code
        @rtype str
        """
        btnCode = ""
        defaultIndex = self.defaultCombo.currentIndex()
        if defaultIndex:
            btnCode = ",{0}{1}{2}".format(
                os.linesep, istring, self.buttonsCodeListText[defaultIndex]
            )
        return btnCode

    def getCode(self, indLevel, indString):
        """
        Public method to get the source code.

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

        if self.iconInformation.isChecked():
            icon = "EricMessageBox.Information"
        elif self.iconQuestion.isChecked():
            icon = "EricMessageBox.Question"
        elif self.iconWarning.isChecked():
            icon = "EricMessageBox.Warning"
        elif self.iconCritical.isChecked():
            icon = "EricMessageBox.Critical"

        if not self.rStandard.isChecked():
            resvar = self.eResultVar.text()
            if not resvar:
                resvar = "res"

            if self.rAbout.isChecked():
                msgdlg = "EricMessageBox.about({0}".format(os.linesep)
            elif self.rAboutQt.isChecked():
                msgdlg = "EricMessageBox.aboutQt({0}".format(os.linesep)
            elif self.rInformation.isChecked():
                msgdlg = "{0} = EricMessageBox.information({1}".format(
                    resvar, os.linesep
                )
            elif self.rQuestion.isChecked():
                msgdlg = "{0} = EricMessageBox.question({1}".format(resvar, os.linesep)
            elif self.rWarning.isChecked():
                msgdlg = "{0} = EricMessageBox.warning({1}".format(resvar, os.linesep)
            elif self.rCritical.isChecked():
                msgdlg = "{0} = EricMessageBox.critical({1}".format(resvar, os.linesep)
            elif self.rYesNo.isChecked():
                msgdlg = "{0} = EricMessageBox.yesNo({1}".format(resvar, os.linesep)
            elif self.rRetryAbort.isChecked():
                msgdlg = "{0} = EricMessageBox.retryAbort({1}".format(
                    resvar, os.linesep
                )
            elif self.rOkToClearData.isChecked():
                msgdlg = "{0} = EricMessageBox.okToClearData({1}".format(
                    resvar, os.linesep
                )

            msgdlg += "{0}{1},{2}".format(istring, parent, os.linesep)
            msgdlg += '{0}self.tr("{1}")'.format(istring, self.eCaption.text())

            if not self.rAboutQt.isChecked():
                msgdlg += ',{0}{1}self.tr("""{2}""")'.format(
                    os.linesep, istring, self.eMessage.toPlainText()
                )

            if (
                self.rInformation.isChecked()
                or self.rQuestion.isChecked()
                or self.rWarning.isChecked()
                or self.rCritical.isChecked()
            ):
                msgdlg += self.__getStandardButtonCode(istring)
                msgdlg += self.__getDefaultButtonCode(istring)
            elif self.rYesNo.isChecked():
                if not self.iconQuestion.isChecked():
                    msgdlg += ",{0}{1}icon={2}".format(os.linesep, istring, icon)
                if self.yesDefaultCheck.isChecked():
                    msgdlg += ",{0}{1}yesDefault=True".format(os.linesep, istring)
            elif self.rRetryAbort.isChecked():
                if not self.iconQuestion.isChecked():
                    msgdlg += ",{0}{1}icon={2}".format(os.linesep, istring, icon)
            elif self.rOkToClearData.isChecked():
                saveFunc = self.saveFuncEdit.text()
                if saveFunc == "":
                    saveFunc = "lambda: True"
                msgdlg += ",{0}{1}{2}".format(os.linesep, istring, saveFunc)
        else:
            resvar = self.eResultVar.text()
            if not resvar:
                resvar = "dlg"

            msgdlg = "{0} = EricMessageBox.EricMessageBox({1}".format(
                resvar, os.linesep
            )
            msgdlg += "{0}{1},{2}".format(istring, icon, os.linesep)
            msgdlg += '{0}self.tr("{1}")'.format(istring, self.eCaption.text())
            msgdlg += ',{0}{1}self.tr("""{2}""")'.format(
                os.linesep, istring, self.eMessage.toPlainText()
            )
            if self.modalCheck.isChecked():
                msgdlg += ",{0}{1}modal=True".format(os.linesep, istring)
            btnCode = self.__getStandardButtonCode(istring, withIntro=False)
            if btnCode:
                msgdlg += ",{0}{1}buttons={2}".format(os.linesep, istring, btnCode)
            if not self.parentNone.isChecked():
                msgdlg += ",{0}{1}parent={2}".format(os.linesep, istring, parent)

        msgdlg += ",{0}){0}".format(estring)
        return msgdlg
