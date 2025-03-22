# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the color dialog wizard dialog.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QColorDialog, QDialog, QDialogButtonBox

from eric7.EricWidgets import EricMessageBox

from .Ui_ColorDialogWizardDialog import Ui_ColorDialogWizardDialog


class ColorDialogWizardDialog(QDialog, Ui_ColorDialogWizardDialog):
    """
    Class implementing the color dialog wizard dialog.

    It displays a dialog for entering the parameters
    for the QColorDialog code generator.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.bTest = self.buttonBox.addButton(
            self.tr("Test"), QDialogButtonBox.ButtonRole.ActionRole
        )

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

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
        if self.rColor.isChecked():
            if not self.eColor.currentText():
                QColorDialog.getColor()
            else:
                coStr = self.eColor.currentText()
                if coStr.startswith("#"):
                    coStr = "QColor('{0}')".format(coStr)
                else:
                    coStr = "QColor({0})".format(coStr)
                try:
                    exec(  # secok
                        "from PyQt6.QtCore import Qt;"
                        ' QColorDialog.getColor({0}, None, "{1}")'.format(
                            coStr, self.eTitle.text()
                        )
                    )
                except Exception:
                    EricMessageBox.critical(
                        self,
                        self.tr("QColorDialog Wizard Error"),
                        self.tr("""<p>The color <b>{0}</b> is not valid.</p>""").format(
                            coStr
                        ),
                    )

        elif self.rRGBA.isChecked():
            QColorDialog.getColor(
                QColor(
                    self.sRed.value(),
                    self.sGreen.value(),
                    self.sBlue.value(),
                    self.sAlpha.value(),
                ),
                None,
                self.eTitle.text(),
                QColorDialog.ColorDialogOption.ShowAlphaChannel,
            )

    def on_eRGB_textChanged(self, text):
        """
        Private slot to handle the textChanged signal of eRGB.

        @param text the new text
        @type str
        """
        if not text:
            self.sRed.setEnabled(True)
            self.sGreen.setEnabled(True)
            self.sBlue.setEnabled(True)
            self.sAlpha.setEnabled(True)
            self.bTest.setEnabled(True)
        else:
            self.sRed.setEnabled(False)
            self.sGreen.setEnabled(False)
            self.sBlue.setEnabled(False)
            self.sAlpha.setEnabled(False)
            self.bTest.setEnabled(False)

    def on_eColor_editTextChanged(self, text):
        """
        Private slot to handle the editTextChanged signal of eColor.

        @param text the new text
        @type str
        """
        if not text or text.startswith("Qt.") or text.startswith("#"):
            self.bTest.setEnabled(True)
        else:
            self.bTest.setEnabled(False)

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
            resvar = "color"
        code = "{0} = QColorDialog.".format(resvar)
        if self.rColor.isChecked():
            code += "getColor({0}".format(os.linesep)
            if self.eColor.currentText():
                col = self.eColor.currentText()
                if col.startswith("#"):
                    code += '{0}QColor("{1}"),{2}'.format(istring, col, os.linesep)
                else:
                    code += "{0}QColor({1}),{2}".format(istring, col, os.linesep)
            else:
                code += "{0}QColor(Qt.GlobalColor.white),{1}".format(
                    istring, os.linesep
                )
            code += "{0}{1},{2}".format(istring, parent, os.linesep)
            code += '{0}self.tr("{1}"),{2}'.format(
                istring, self.eTitle.text(), os.linesep
            )
            code += "{0}QColorDialog.ColorDialogOption.ShowAlphaChannel".format(istring)
            code += ",{0}){0}".format(estring)
        elif self.rRGBA.isChecked():
            code += "getColor({0}".format(os.linesep)
            if not self.eRGB.text():
                code += "{0}QColor({1:d}, {2:d}, {3:d}, {4:d}),{5}".format(
                    istring,
                    self.sRed.value(),
                    self.sGreen.value(),
                    self.sBlue.value(),
                    self.sAlpha.value(),
                    os.linesep,
                )
            else:
                code += "{0}{1},{2}".format(istring, self.eRGB.text(), os.linesep)
            code += "{0}{1},{2}".format(istring, parent, os.linesep)
            code += '{0}self.tr("{1}"),{2}'.format(
                istring, self.eTitle.text(), os.linesep
            )
            code += "{0}QColorDialog.ColorDialogOption.ShowAlphaChannel".format(istring)
            code += ",{0}){0}".format(estring)

        return code
