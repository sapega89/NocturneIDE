# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select multiple entries from a list.
"""

from PyQt6.QtWidgets import QAbstractItemView, QDialog, QListWidgetItem

from .Ui_DotDesktopListSelectionDialog import Ui_DotDesktopListSelectionDialog


class DotDesktopListSelectionDialog(QDialog, Ui_DotDesktopListSelectionDialog):
    """
    Class implementing a dialog to select multiple entries from a list.
    """

    def __init__(
        self,
        entries,
        selectedEntries,
        separator,
        subEntries=None,
        allowMultiMain=True,
        allowMultiSub=True,
        parent=None,
    ):
        """
        Constructor

        @param entries list of entries to be shown
        @type list of str
        @param selectedEntries list of entries to be selected or a string with
            entries separated by separator
        @type list of str or str
        @param separator separator string
        @type str
        @param subEntries secondary list of entries
        @type list of str
        @param allowMultiMain flag indicating to allow multiple selections for
            the main entry
        @type bool
        @param allowMultiSub flag indicating to allow multiple selections for
            the sub entry
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        if isinstance(selectedEntries, str):
            selectedEntries = selectedEntries.split(separator)

        if not allowMultiMain:
            self.entriesList.setSelectionMode(
                QAbstractItemView.SelectionMode.SingleSelection
            )
        if not allowMultiSub:
            self.subList.setSelectionMode(
                QAbstractItemView.SelectionMode.SingleSelection
            )

        for entry in entries:
            itm = QListWidgetItem(entry, self.entriesList)
            if entry in selectedEntries:
                itm.setSelected(True)

        if subEntries:
            for entry in subEntries:
                itm = QListWidgetItem(entry, self.subList)
                if entry in selectedEntries:
                    itm.setSelected(True)
        else:
            self.subList.setVisible(False)

    def getData(self, separator=None, separatorAtEnd=False):
        """
        Public method to extract the selected entries as a list
        or a string.

        @param separator separator string
        @type str
        @param separatorAtEnd flag indicating to append the separator
        @type bool
        @return list of selected entries if the separator is None or a string
            with entries delimited by separator
        @rtype list od str or str
        """
        entries = []
        for itm in self.entriesList.selectedItems():
            entries.append(itm.text())
        for itm in self.subList.selectedItems():
            entries.append(itm.text())

        if separator is None:
            return entries
        else:
            entriesStr = separator.join(entries)
            if separatorAtEnd:
                entriesStr += separator
            return entriesStr
