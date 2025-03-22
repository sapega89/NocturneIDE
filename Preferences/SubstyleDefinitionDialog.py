# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the sub-style definition dialog.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets import EricMessageBox

from .Ui_SubstyleDefinitionDialog import Ui_SubstyleDefinitionDialog


class SubstyleDefinitionDialog(QDialog, Ui_SubstyleDefinitionDialog):
    """
    Class implementing the sub-style definition dialog.
    """

    def __init__(self, lexer, style, substyle, parent=None):
        """
        Constructor

        @param lexer reference to the lexer object
        @type PreferencesLexer
        @param style style number
        @type int
        @param substyle sub-style number
        @type int
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__lexer = lexer
        self.__style = style
        self.__substyle = substyle

        self.header.setText(
            self.tr("<h3>{0} - {1}</h3>").format(
                self.__lexer.language(), self.__lexer.description(self.__style)
            )
        )
        if self.__substyle >= 0:
            # it's an edit operation
            self.descriptionEdit.setText(
                self.__lexer.description(self.__style, self.__substyle)
            )
            self.wordsEdit.setPlainText(
                self.__lexer.words(self.__style, self.__substyle)
            )

    def __updateOk(self):
        """
        Private slot to update the state of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.descriptionEdit.text().strip())
            and bool(self.wordsEdit.toPlainText().strip())
        )

    @pyqtSlot(str)
    def on_descriptionEdit_textChanged(self, _txt):
        """
        Private slot handling changes of the description.

        @param _txt text of the description (unused)
        @type str
        """
        self.__updateOk()

    @pyqtSlot()
    def on_wordsEdit_textChanged(self):
        """
        Private slot handling changes of the word list.
        """
        self.__updateOk()

    @pyqtSlot()
    def on_resetButton_clicked(self):
        """
        Private slot to reset the dialog contents.
        """
        ok = EricMessageBox.yesNo(
            self,
            self.tr("Reset Sub-Style Data"),
            self.tr("""Shall the entered sub-style data be reset?"""),
        )
        if ok:
            if self.__substyle >= 0:
                self.descriptionEdit.setText(
                    self.__lexer.description(self.__style, self.__substyle)
                )
                self.wordsEdit.setPlainText(
                    self.__lexer.words(self.__style, self.__substyle)
                )
            else:
                self.descriptionEdit.clear()
                self.wordsEdit.clear()

    @pyqtSlot()
    def on_defaultButton_clicked(self):
        """
        Private slot to set the dialog contents to default values.
        """
        filled = bool(self.descriptionEdit.text().strip()) or bool(
            self.wordsEdit.toPlainText().strip()
        )
        ok = (
            EricMessageBox.yesNo(
                self,
                self.tr("Set Sub-Style Data to Default"),
                self.tr("""Shall the sub-style data be set to default values?"""),
            )
            if filled
            else True
        )
        if ok:
            if self.__substyle >= 0:
                self.descriptionEdit.setText(
                    self.__lexer.defaultDescription(self.__style, self.__substyle)
                )
                self.wordsEdit.setPlainText(
                    self.__lexer.defaultWords(self.__style, self.__substyle)
                )
            else:
                self.descriptionEdit.clear()
                self.wordsEdit.clear()

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the sub-style description and words list.
        @rtype tuple of (str, str)
        """
        return (
            self.descriptionEdit.text().strip(),
            self.wordsEdit.toPlainText().strip(),
        )
