# -*- coding: utf-8 -*-

# Copyright (c) 2003 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the font dialog wizard dialog.
"""

import os

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QFontDialog

from .Ui_FontDialogWizardDialog import Ui_FontDialogWizardDialog


class FontDialogWizardDialog(QDialog, Ui_FontDialogWizardDialog):
    """
    Class implementing the font dialog wizard dialog.

    It displays a dialog for entering the parameters
    for the QFontDialog code generator.
    """

    FontWeight2Code = {
        100: "Thin",
        200: "ExtraLight",
        300: "Light",
        400: "Normal",
        500: "Medium",
        600: "DemiBold",
        700: "Bold",
        800: "ExtraBold",
        900: "Black",
    }

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

        self.font = None
        self.fontOptions = {
            "noNativeDialog": False,
            "scalableFonts": False,
            "nonScalableFonts": False,
            "monospacedFonts": False,
            "proportionalFonts": False,
        }

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
        if self.font is None:
            QFontDialog.getFont()
        else:
            options = QFontDialog.FontDialogOption(0)
            if any(self.fontOptions.values()):
                if self.fontOptions["noNativeDialog"]:
                    options |= QFontDialog.FontDialogOption.DontUseNativeDialog
                if self.fontOptions["scalableFonts"]:
                    options |= QFontDialog.FontDialogOption.ScalableFonts
                if self.fontOptions["nonScalableFonts"]:
                    options |= QFontDialog.FontDialogOption.NonScalableFonts
                if self.fontOptions["monospacedFonts"]:
                    options |= QFontDialog.FontDialogOption.MonospacedFonts
                if self.fontOptions["proportionalFonts"]:
                    options |= QFontDialog.FontDialogOption.ProportionalFonts
            QFontDialog.getFont(self.font, self, self.eCaption.text(), options)

    def on_eVariable_textChanged(self, text):
        """
        Private slot to handle the textChanged signal of eVariable.

        @param text the new text
        @type str
        """
        if not text:
            self.bTest.setEnabled(True)
        else:
            self.bTest.setEnabled(False)

    @pyqtSlot()
    def on_fontButton_clicked(self):
        """
        Private slot to handle the button press to select a font via a
        font selection dialog.
        """
        if self.font is None:
            font, ok = QFontDialog.getFont()
        else:
            font, ok = QFontDialog.getFont(self.font)
        if ok:
            self.font = font
        else:
            self.font = None

    @pyqtSlot()
    def on_optionsButton_clicked(self):
        """
        Private slot to handle the selection of font dialog options.
        """
        from .FontDialogOptionsDialog import FontDialogOptionsDialog

        dlg = FontDialogOptionsDialog(self.fontOptions, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.fontOptions = dlg.getOptions()

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

        # generate the code
        resvar = self.eResultVar.text()
        if not resvar:
            resvar = "font"
        title = self.eCaption.text()
        if self.parentSelf.isChecked():
            parent = "self"
        elif self.parentNone.isChecked():
            parent = "None"
        elif self.parentOther.isChecked():
            parent = self.parentEdit.text()
            if parent == "":
                parent = "None"

        code = "{0}, ok = QFontDialog.getFont(".format(resvar)
        if self.eVariable.text() or self.font is not None:
            if title or parent != "None":
                code += "{0}{1}".format(os.linesep, istring)
            if not self.eVariable.text():
                if self.font is not None:
                    code += 'QFont(["{0}"], {1:d}, QFont.Weight.{2}, {3})'.format(
                        self.font.family(),
                        self.font.pointSize(),
                        FontDialogWizardDialog.FontWeight2Code[self.font.weight()],
                        "True" if self.font.italic() else "False",
                    )
            else:
                code += self.eVariable.text()
            if title:
                code += ",{0}{1}{2}".format(os.linesep, istring, parent)
                code += ',{0}{1}self.tr("{2}")'.format(os.linesep, istring, title)
            elif parent != "None":
                code += ",{0}{1}{2}".format(os.linesep, istring, parent)
            if any(self.fontOptions.values()):
                options = []
                if self.fontOptions["noNativeDialog"]:
                    options.append("QFontDialog.FontDialogOption.DontUseNativeDialog")
                if self.fontOptions["scalableFonts"]:
                    options.append("QFontDialog.FontDialogOption.ScalableFonts")
                if self.fontOptions["nonScalableFonts"]:
                    options.append("QFontDialog.FontDialogOption.NonScalableFonts")
                if self.fontOptions["monospacedFonts"]:
                    options.append("QFontDialog.FontDialogOption.MonospacedFonts")
                if self.fontOptions["proportionalFonts"]:
                    options.append("QFontDialog.FontDialogOption.ProportionalFonts")
                fontOptionsString = "{0}{1}| ".format(os.linesep, istring).join(options)
                code += ",{0}{1}{2}".format(os.linesep, istring, fontOptionsString)
        code += ",{0}){0}".format(estring)

        return code
