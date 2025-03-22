# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the message box wizard dialog.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from .Ui_MessageBoxWizardDialog import Ui_MessageBoxWizardDialog


class MessageBoxWizardDialog(QDialog, Ui_MessageBoxWizardDialog):
    """
    Class implementing the message box wizard dialog.

    It displays a dialog for entering the parameters
    for the QMessageBox code generator.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget
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
            QMessageBox.StandardButton.NoButton,
            QMessageBox.StandardButton.Abort,
            QMessageBox.StandardButton.Apply,
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Close,
            QMessageBox.StandardButton.Discard,
            QMessageBox.StandardButton.Help,
            QMessageBox.StandardButton.Ignore,
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.NoToAll,
            QMessageBox.StandardButton.Ok,
            QMessageBox.StandardButton.Open,
            QMessageBox.StandardButton.Reset,
            QMessageBox.StandardButton.RestoreDefaults,
            QMessageBox.StandardButton.Retry,
            QMessageBox.StandardButton.Save,
            QMessageBox.StandardButton.SaveAll,
            QMessageBox.StandardButton.Yes,
            QMessageBox.StandardButton.YesToAll,
        ]
        self.buttonsCodeListText = [
            "QMessageBox.StandardButton.NoButton",
            "QMessageBox.StandardButton.Abort",
            "QMessageBox.StandardButton.Apply",
            "QMessageBox.StandardButton.Cancel",
            "QMessageBox.StandardButton.Close",
            "QMessageBox.StandardButton.Discard",
            "QMessageBox.StandardButton.Help",
            "QMessageBox.StandardButton.Ignore",
            "QMessageBox.StandardButton.No",
            "QMessageBox.StandardButton.NoToAll",
            "QMessageBox.StandardButton.Ok",
            "QMessageBox.StandardButton.Open",
            "QMessageBox.StandardButton.Reset",
            "QMessageBox.StandardButton.RestoreDefaults",
            "QMessageBox.StandardButton.Retry",
            "QMessageBox.StandardButton.Save",
            "QMessageBox.StandardButton.SaveAll",
            "QMessageBox.StandardButton.Yes",
            "QMessageBox.StandardButton.YesToAll",
        ]

        self.defaultCombo.addItems(self.buttonsList)

        self.bTest = self.buttonBox.addButton(
            self.tr("Test"), QDialogButtonBox.ButtonRole.ActionRole
        )

    def __testSelectedOptions(self):
        """
        Private method to test the selected options.
        """
        buttons = QMessageBox.StandardButton.NoButton
        if self.abortCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Abort
        if self.applyCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Apply
        if self.cancelCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Cancel
        if self.closeCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Close
        if self.discardCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Discard
        if self.helpCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Help
        if self.ignoreCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Ignore
        if self.noCheck.isChecked():
            buttons |= QMessageBox.StandardButton.No
        if self.notoallCheck.isChecked():
            buttons |= QMessageBox.StandardButton.NoToAll
        if self.okCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Ok
        if self.openCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Open
        if self.resetCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Reset
        if self.restoreCheck.isChecked():
            buttons |= QMessageBox.StandardButton.RestoreDefaults
        if self.retryCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Retry
        if self.saveCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Save
        if self.saveallCheck.isChecked():
            buttons |= QMessageBox.StandardButton.SaveAll
        if self.yesCheck.isChecked():
            buttons |= QMessageBox.StandardButton.Yes
        if self.yestoallCheck.isChecked():
            buttons |= QMessageBox.StandardButton.YesToAll
        if buttons == QMessageBox.StandardButton.NoButton:
            buttons = QMessageBox.StandardButton.Ok

        defaultButton = self.buttonsCodeListBinary[self.defaultCombo.currentIndex()]

        if self.rInformation.isChecked():
            QMessageBox.information(
                self,
                self.eCaption.text(),
                self.eMessage.toPlainText(),
                buttons,
                defaultButton,
            )
        elif self.rQuestion.isChecked():
            QMessageBox.question(
                self,
                self.eCaption.text(),
                self.eMessage.toPlainText(),
                buttons,
                defaultButton,
            )
        elif self.rWarning.isChecked():
            QMessageBox.warning(
                self,
                self.eCaption.text(),
                self.eMessage.toPlainText(),
                buttons,
                defaultButton,
            )
        elif self.rCritical.isChecked():
            QMessageBox.critical(
                self,
                self.eCaption.text(),
                self.eMessage.toPlainText(),
                buttons,
                defaultButton,
            )

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
            QMessageBox.about(None, self.eCaption.text(), self.eMessage.toPlainText())
        elif self.rAboutQt.isChecked():
            QMessageBox.aboutQt(None, self.eCaption.text())
        else:
            self.__testSelectedOptions()

    def __enabledGroups(self):
        """
        Private method to enable/disable some group boxes.
        """
        enable = not self.rAbout.isChecked() and not self.rAboutQt.isChecked()
        self.standardButtons.setEnabled(enable)
        self.lResultVar.setEnabled(enable)
        self.eResultVar.setEnabled(enable)

        self.eMessage.setEnabled(not self.rAboutQt.isChecked())

    @pyqtSlot()
    def on_rAbout_toggled(self):
        """
        Private slot to handle the toggled signal of the rAbout radio button.
        """
        self.__enabledGroups()

    @pyqtSlot()
    def on_rAboutQt_toggled(self):
        """
        Private slot to handle the toggled signal of the rAboutQt radio button.
        """
        self.__enabledGroups()

    def __getButtonCode(self, istring, indString):
        """
        Private method to generate the button code.

        @param istring indentation string
        @type str
        @param indString string used for indentation (space or tab)
        @type str
        @return the button code
        @rtype str
        """
        buttons = []
        if self.abortCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Abort")
        if self.applyCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Apply")
        if self.cancelCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Cancel")
        if self.closeCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Close")
        if self.discardCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Discard")
        if self.helpCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Help")
        if self.ignoreCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Ignore")
        if self.noCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.No")
        if self.notoallCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.NoToAll")
        if self.okCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Ok")
        if self.openCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Open")
        if self.resetCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Reset")
        if self.restoreCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.RestoreDefaults")
        if self.retryCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Retry")
        if self.saveCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Save")
        if self.saveallCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.SaveAll")
        if self.yesCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.Yes")
        if self.yestoallCheck.isChecked():
            buttons.append("QMessageBox.StandardButton.YesToAll")
        if len(buttons) == 0:
            return ""

        istring2 = istring + indString
        joinstring = "{0}{1}| ".format(os.linesep, istring2)
        btnCode = ",{0}{1}(".format(os.linesep, istring)
        btnCode += "{0}{1}{2})".format(os.linesep, istring2, joinstring.join(buttons))
        defaultIndex = self.defaultCombo.currentIndex()
        if defaultIndex:
            btnCode += ",{0}{1}{2}".format(
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

        resvar = self.eResultVar.text()
        if not resvar:
            resvar = "res"

        if self.rAbout.isChecked():
            msgdlg = "QMessageBox.about("
        elif self.rAboutQt.isChecked():
            msgdlg = "QMessageBox.aboutQt("
        elif self.rInformation.isChecked():
            msgdlg = "{0} = QMessageBox.information(".format(resvar)
        elif self.rQuestion.isChecked():
            msgdlg = "{0} = QMessageBox.question(".format(resvar)
        elif self.rWarning.isChecked():
            msgdlg = "{0} = QMessageBox.warning(".format(resvar)
        else:
            msgdlg = "{0} = QMessageBox.critical(".format(resvar)

        if self.rAboutQt.isChecked():
            if self.eCaption.text():
                msgdlg += "{0}{1}{2}".format(os.linesep, istring, parent)
                msgdlg += ',{0}{1}self.tr("{2}")'.format(
                    os.linesep, istring, self.eCaption.text()
                )
            else:
                msgdlg += parent
        else:
            msgdlg += "{0}{1}{2}".format(os.linesep, istring, parent)
            msgdlg += ',{0}{1}self.tr("{2}")'.format(
                os.linesep, istring, self.eCaption.text()
            )
            msgdlg += ',{0}{1}self.tr("""{2}""")'.format(
                os.linesep, istring, self.eMessage.toPlainText()
            )
            if not self.rAbout.isChecked() and not self.rAboutQt.isChecked():
                msgdlg += self.__getButtonCode(istring, indString)
        msgdlg += ",{0}){0}".format(estring)
        return msgdlg
