# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the variables filter dialog.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QListWidgetItem

from eric7 import Preferences
from eric7.Debugger.Config import ConfigVarTypeDispStrings

from .Ui_VariablesFilterDialog import Ui_VariablesFilterDialog


class VariablesFilterDialog(QDialog, Ui_VariablesFilterDialog):
    """
    Class implementing the variables filter dialog.

    It opens a dialog window for the configuration of the variables type
    filters to be applied during a debugging session. Pressing 'Apply' will
    show the effect of the current selection on the currently shown variables.
    'Reset' will reset the selection to the one the dialog was opened with.

    @signal applyFilterLists(list of str, list of str) emitted to apply the given
        locals and globals filters to the currently shown variables
    """

    applyFilterLists = pyqtSignal(list, list)

    def __init__(self, parent=None, name=None, modal=False):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        @param name name of this dialog
        @type str
        @param modal flag to indicate a modal dialog
        @type bool
        """
        super().__init__(parent)
        if name:
            self.setObjectName(name)
        self.setModal(modal)
        self.setupUi(self)

        self.__defaultButton = self.buttonBox.addButton(
            self.tr("Save Default"), QDialogButtonBox.ButtonRole.ActionRole
        )

        self.__localsFilters = []
        self.__globalsFilters = []

        # populate the list widgets and set the default selection
        for widget in self.localsList, self.globalsList:
            for varType, varTypeStr in ConfigVarTypeDispStrings.items():
                itm = QListWidgetItem(self.tr(varTypeStr), widget)
                itm.setData(Qt.ItemDataRole.UserRole, varType)
                itm.setFlags(
                    Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable
                )
                itm.setCheckState(Qt.CheckState.Unchecked)
                widget.addItem(itm)

        lDefaultFilter, gDefaultFilter = Preferences.getVarFilters()
        self.setSelection(lDefaultFilter, gDefaultFilter)

    def getSelection(self):
        """
        Public slot to retrieve the current selections.

        @return tuple of lists containing the variable filters. The first list
            is the locals variables filter, the second the globals variables
            filter.
        @rtype tuple of (list of str, list of str)
        """
        lList = []
        for row in range(self.localsList.count()):
            itm = self.localsList.item(row)
            if itm.checkState() == Qt.CheckState.Unchecked:
                lList.append(itm.data(Qt.ItemDataRole.UserRole))

        gList = []
        for row in range(self.globalsList.count()):
            itm = self.globalsList.item(row)
            if itm.checkState() == Qt.CheckState.Unchecked:
                gList.append(itm.data(Qt.ItemDataRole.UserRole))
        return (lList, gList)

    def setSelection(self, lList, gList):
        """
        Public slot to set the current selection.

        @param lList local variables filter
        @type list of str
        @param gList global variables filter
        @type list of str
        """
        self.__localsFilters = lList
        self.__globalsFilters = gList

        for row in range(self.localsList.count()):
            itm = self.localsList.item(row)
            if itm.data(Qt.ItemDataRole.UserRole) in lList:
                itm.setCheckState(Qt.CheckState.Unchecked)
            else:
                itm.setCheckState(Qt.CheckState.Checked)

        for row in range(self.globalsList.count()):
            itm = self.globalsList.item(row)
            if itm.data(Qt.ItemDataRole.UserRole) in gList:
                itm.setCheckState(Qt.CheckState.Unchecked)
            else:
                itm.setCheckState(Qt.CheckState.Checked)

    def on_buttonBox_clicked(self, button):
        """
        Private slot called by a button of the button box clicked.

        @param button button that was clicked
        @type QAbstractButton
        """
        if button == self.__defaultButton:
            Preferences.setVarFilters(self.getSelection())
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Reset):
            self.setSelection(self.__localsFilters, self.__globalsFilters)
        elif button == self.buttonBox.button(QDialogButtonBox.StandardButton.Apply):
            self.applyFilterLists.emit(*self.getSelection())
