# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select the styles to be imported/exported.
"""

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QAbstractButton, QDialog, QDialogButtonBox, QListWidgetItem

from .Ui_EditorHighlightingStylesSelectionDialog import (
    Ui_EditorHighlightingStylesSelectionDialog,
)


class EditorHighlightingStylesSelectionDialog(
    QDialog, Ui_EditorHighlightingStylesSelectionDialog
):
    """
    Class implementing a dialog to select the styles to be imported/exported.
    """

    def __init__(self, lexerNames, forImport, preselect=None, parent=None):
        """
        Constructor

        @param lexerNames list of lexer names to select from
        @type list of str
        @param forImport flag indicating a dialog for importing styles
        @type bool
        @param preselect list of lexer names to be preselected
        @type list of str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__selectAllButton = self.buttonBox.addButton(
            self.tr("Select All"), QDialogButtonBox.ButtonRole.ActionRole
        )

        if forImport:
            self.setWindowTitle(self.tr("Import Highlighting Styles"))
            self.infoLabel.setText(
                self.tr("Select the highlighting styles to be imported")
            )
        else:
            self.setWindowTitle(self.tr("Export Highlighting Styles"))
            self.infoLabel.setText(
                self.tr("Select the highlighting styles to be exported")
            )

        if preselect is None:
            preselect = []

        for name in lexerNames:
            itm = QListWidgetItem(name, self.lexersList)
            itm.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            if name in preselect:
                itm.setCheckState(Qt.CheckState.Checked)
            else:
                itm.setCheckState(Qt.CheckState.Unchecked)

        self.__updateOkButton()

    @pyqtSlot()
    def __updateOkButton(self):
        """
        Private slot to update the state of the OK button.
        """
        for row in range(self.lexersList.count()):
            itm = self.lexersList.item(row)
            if itm.checkState() == Qt.CheckState.Checked:
                enable = True
                break
        else:
            enable = False
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    @pyqtSlot(QListWidgetItem)
    def on_lexersList_itemChanged(self, item):
        """
        Private slot to react on changes in check state.

        @param item reference to the changed item
        @type QListWidgetItem
        """
        self.__updateOkButton()

    @pyqtSlot(QAbstractButton)
    def on_buttonBox_clicked(self, button):
        """
        Private slot to handle the user pressing a button.

        @param button reference to the button pressed
        @type QAbstractButton
        """
        if button is self.__selectAllButton:
            for row in range(self.lexersList.count()):
                itm = self.lexersList.item(row)
                itm.setCheckState(Qt.CheckState.Checked)

    def getLexerNames(self):
        """
        Public method to get the selected lexer names.

        @return list of selected lexer names
        @rtype list of str
        """
        lexerNames = []
        for row in range(self.lexersList.count()):
            itm = self.lexersList.item(row)
            if itm.checkState() == Qt.CheckState.Checked:
                lexerNames.append(itm.text())

        return lexerNames
