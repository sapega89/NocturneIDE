# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the input dialog wizard dialog.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QInputDialog, QLineEdit

from .Ui_InputDialogWizardDialog import Ui_InputDialogWizardDialog


class InputDialogWizardDialog(QDialog, Ui_InputDialogWizardDialog):
    """
    Class implementing the input dialog wizard dialog.

    It displays a dialog for entering the parameters
    for the QInputDialog code generator.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        # set the validators for the double line edits
        self.eDoubleDefault.setValidator(
            QDoubleValidator(-2147483647, 2147483647, 99, self.eDoubleDefault)
        )
        self.eDoubleFrom.setValidator(
            QDoubleValidator(-2147483647, 2147483647, 99, self.eDoubleFrom)
        )
        self.eDoubleTo.setValidator(
            QDoubleValidator(-2147483647, 2147483647, 99, self.eDoubleTo)
        )

        self.rText.toggled.connect(self.__typeSelectButtonToggled)
        self.rMultiLineText.toggled.connect(self.__typeSelectButtonToggled)
        self.rInteger.toggled.connect(self.__typeSelectButtonToggled)
        self.rDouble.toggled.connect(self.__typeSelectButtonToggled)
        self.rItem.toggled.connect(self.__typeSelectButtonToggled)

        self.bTest = self.buttonBox.addButton(
            self.tr("Test"), QDialogButtonBox.ButtonRole.ActionRole
        )

        # simulate a dialog type selection
        self.__typeSelectButtonToggled(True)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot(bool)
    def __typeSelectButtonToggled(self, checked):
        """
        Private slot to modify the dialog according to the selected type.

        Note: This is a multiplexed slot. Therefore it just reacts upon a
        positive check state (i.e. checked == True).

        @param checked flag indicating the checked state
        @type bool
        """
        self.bTest.setEnabled(True)
        if checked:
            if self.rText.isChecked():
                self.specificsStack.setCurrentWidget(self.textPage)
            elif self.rMultiLineText.isChecked():
                self.specificsStack.setCurrentWidget(self.multiLineTextPage)
            elif self.rInteger.isChecked():
                self.specificsStack.setCurrentWidget(self.integerPage)
            elif self.rDouble.isChecked():
                self.specificsStack.setCurrentWidget(self.doublePage)
            elif self.rItem.isChecked():
                self.specificsStack.setCurrentWidget(self.itemPage)
                self.bTest.setEnabled(False)

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
        if self.rText.isChecked():
            if self.rEchoNormal.isChecked():
                echomode = QLineEdit.EchoMode.Normal
            elif self.rEchoNoEcho.isChecked():
                echomode = QLineEdit.EchoMode.NoEcho
            else:
                echomode = QLineEdit.EchoMode.Password
            QInputDialog.getText(
                None,
                self.eCaption.text(),
                self.eLabel.text(),
                echomode,
                self.eTextDefault.text(),
            )
        elif self.rMultiLineText.isChecked():
            QInputDialog.getMultiLineText(
                None,
                self.eCaption.text(),
                self.eLabel.text(),
                self.eMultiTextDefault.toPlainText(),
            )
        elif self.rInteger.isChecked():
            QInputDialog.getInt(
                None,
                self.eCaption.text(),
                self.eLabel.text(),
                self.sIntDefault.value(),
                self.sIntFrom.value(),
                self.sIntTo.value(),
                self.sIntStep.value(),
            )
        elif self.rDouble.isChecked():
            try:
                doubleDefault = float(self.eDoubleDefault.text())
            except ValueError:
                doubleDefault = 0
            try:
                doubleFrom = float(self.eDoubleFrom.text())
            except ValueError:
                doubleFrom = -2147483647
            try:
                doubleTo = float(self.eDoubleTo.text())
            except ValueError:
                doubleTo = 2147483647
            QInputDialog.getDouble(
                None,
                self.eCaption.text(),
                self.eLabel.text(),
                doubleDefault,
                doubleFrom,
                doubleTo,
                self.sDoubleDecimals.value(),
            )

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

        resvar = self.eResultVar.text()
        if not resvar:
            resvar = "result"
        code = "{0}, ok = QInputDialog.".format(resvar)
        if self.rText.isChecked():
            code += "getText({0}{1}".format(os.linesep, istring)
            code += "{0},{1}{2}".format(parent, os.linesep, istring)
            code += 'self.tr("{0}"),{1}{2}'.format(
                self.eCaption.text(), os.linesep, istring
            )
            code += 'self.tr("{0}"),{1}{2}'.format(
                self.eLabel.text(), os.linesep, istring
            )
            if self.rEchoNormal.isChecked():
                code += "QLineEdit.EchoMode.Normal"
            elif self.rEchoNoEcho.isChecked():
                code += "QLineEdit.EchoMode.NoEcho"
            else:
                code += "QLineEdit.EchoMode.Password"
            if self.eTextDefault.text():
                if self.cTranslateTextDefault.isChecked():
                    code += ',{0}{1}self.tr("{2}")'.format(
                        os.linesep, istring, self.eTextDefault.text()
                    )
                else:
                    code += ',{0}{1}"{2}"'.format(
                        os.linesep, istring, self.eTextDefault.text()
                    )
            code += ",{0}){0}".format(estring)
        elif self.rMultiLineText.isChecked():
            code += "getMultiLineText({0}{1}".format(os.linesep, istring)
            code += "{0},{1}{2}".format(parent, os.linesep, istring)
            code += 'self.tr("{0}"),{1}{2}'.format(
                self.eCaption.text(), os.linesep, istring
            )
            code += 'self.tr("{0}")'.format(self.eLabel.text())
            if self.eMultiTextDefault.toPlainText():
                defTxt = "\\n".join(self.eMultiTextDefault.toPlainText().splitlines())
                if self.cTranslateMultiTextDefault.isChecked():
                    code += ',{0}{1}self.tr("{2}")'.format(os.linesep, istring, defTxt)
                else:
                    code += ',{0}{1}"{2}"'.format(os.linesep, istring, defTxt)
            code += ",{0}){0}".format(estring)
        elif self.rInteger.isChecked():
            code += "getInt({0}{1}".format(os.linesep, istring)
            code += "{0},{1}{2}".format(parent, os.linesep, istring)
            code += 'self.tr("{0}"),{1}{2}'.format(
                self.eCaption.text(), os.linesep, istring
            )
            code += 'self.tr("{0}"),{1}{2}'.format(
                self.eLabel.text(), os.linesep, istring
            )
            code += "{0:d}, {1:d}, {2:d}, {3:d}".format(
                self.sIntDefault.value(),
                self.sIntFrom.value(),
                self.sIntTo.value(),
                self.sIntStep.value(),
            )
            code += ",{0}){0}".format(estring)
        elif self.rDouble.isChecked():
            try:
                doubleDefault = float(self.eDoubleDefault.text())
            except ValueError:
                doubleDefault = 0
            try:
                doubleFrom = float(self.eDoubleFrom.text())
            except ValueError:
                doubleFrom = -2147483647
            try:
                doubleTo = float(self.eDoubleTo.text())
            except ValueError:
                doubleTo = 2147483647
            code += "getDouble({0}{1}".format(os.linesep, istring)
            code += "{0},{1}{2}".format(parent, os.linesep, istring)
            code += 'self.tr("{0}"),{1}{2}'.format(
                self.eCaption.text(), os.linesep, istring
            )
            code += 'self.tr("{0}"),{1}{2}'.format(
                self.eLabel.text(), os.linesep, istring
            )
            code += "{0}, {1}, {2}, {3:d}".format(
                doubleDefault, doubleFrom, doubleTo, self.sDoubleDecimals.value()
            )
            code += ",{0}){0}".format(estring)
        elif self.rItem.isChecked():
            code += "getItem({0}{1}".format(os.linesep, istring)
            code += "{0},{1}{2}".format(parent, os.linesep, istring)
            code += 'self.tr("{0}"),{1}{2}'.format(
                self.eCaption.text(), os.linesep, istring
            )
            code += 'self.tr("{0}"),{1}{2}'.format(
                self.eLabel.text(), os.linesep, istring
            )
            code += "{0},{1}{2}".format(self.eVariable.text(), os.linesep, istring)
            code += "{0:d}, {1}".format(
                self.sCurrentItem.value(), self.cEditable.isChecked()
            )
            code += ",{0}){0}".format(estring)

        return code
