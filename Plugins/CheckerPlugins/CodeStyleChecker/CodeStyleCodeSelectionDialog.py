# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select code style message codes.
"""

import textwrap

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

from . import CodeStyleCheckerUtilities
from .CodeStyleFixer import FixableCodeStyleIssues
from .translations import getMessageCodes, getTranslatedMessage
from .Ui_CodeStyleCodeSelectionDialog import Ui_CodeStyleCodeSelectionDialog


class CodeStyleCodeSelectionDialog(QDialog, Ui_CodeStyleCodeSelectionDialog):
    """
    Class implementing a dialog to select code style message codes.
    """

    def __init__(self, codes, categories, showFixCodes, parent=None):
        """
        Constructor

        @param codes comma separated list of selected codes
        @type str
        @param categories list of message categories to omit
        @type list of str
        @param showFixCodes flag indicating to show a list of fixable
            issues
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        textWrapper = textwrap.TextWrapper(width=60)

        self.codeTable.headerItem().setText(self.codeTable.columnCount(), "")
        codeList = [code.strip() for code in codes.split(",") if code.strip()]
        if categories:
            codeList = [code for code in codeList if code[0] not in categories]

        if showFixCodes:
            selectableCodes = FixableCodeStyleIssues
        else:
            selectableCodes = [x for x in getMessageCodes() if not x.startswith("FIX")]
            if categories:
                # filter by category
                selectableCodes = [x for x in selectableCodes if x[0] not in categories]
        for msgCode in sorted(selectableCodes):
            message = getTranslatedMessage(msgCode, [], example=True)
            if message is None:
                # try with extension
                for ext in ("L", "M", "H", "1"):
                    message = getTranslatedMessage(
                        "{0}.{1}".format(msgCode, ext), [], example=True
                    )
                    if message is not None:
                        break
                else:
                    continue
            itm = QTreeWidgetItem(
                self.codeTable, [msgCode, "\n".join(textWrapper.wrap(message))]
            )
            CodeStyleCheckerUtilities.setItemIcon(itm, 0, msgCode)
            itm.setFlags(itm.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            if msgCode in codeList:
                itm.setCheckState(0, Qt.CheckState.Checked)
                codeList.remove(msgCode)
            else:
                itm.setCheckState(0, Qt.CheckState.Unchecked)
        self.codeTable.resizeColumnToContents(0)
        self.codeTable.resizeColumnToContents(1)
        self.codeTable.header().setStretchLastSection(True)

        self.__extraCodes = codeList[:]

    def getSelectedCodes(self):
        """
        Public method to get a comma separated list of codes selected.

        @return comma separated list of selected codes
        @rtype str
        """
        selectedCodes = []

        for index in range(self.codeTable.topLevelItemCount()):
            itm = self.codeTable.topLevelItem(index)
            if itm.checkState(0) == Qt.CheckState.Checked:
                selectedCodes.append(itm.text(0))

        return ", ".join(self.__extraCodes + selectedCodes)
