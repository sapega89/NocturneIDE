# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit a list of strings.
"""

from PyQt6.QtCore import (
    QSortFilterProxyModel,
    QStringListModel,
    Qt,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtWidgets import QInputDialog, QLineEdit, QWidget

from eric7.EricWidgets import EricMessageBox

from .Ui_EricStringListEditWidget import Ui_EricStringListEditWidget


class EricStringListEditWidget(QWidget, Ui_EricStringListEditWidget):
    """
    Class implementing a dialog to edit a list of strings.

    @signal setToDefault() emitted to request the default list of values
    """

    setToDefault = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__model = QStringListModel(self)
        self.__proxyModel = QSortFilterProxyModel(self)
        self.__proxyModel.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.__proxyModel.setSourceModel(self.__model)
        self.stringList.setModel(self.__proxyModel)

        self.defaultButton.hide()
        self.resetButton.hide()
        self.resetLine.hide()

        # store some internal state
        self.__defaultVisible = False
        self.__resetVisible = False

        self.searchEdit.textChanged.connect(self.__proxyModel.setFilterFixedString)

        self.removeButton.clicked.connect(self.stringList.removeSelected)
        self.removeAllButton.clicked.connect(self.stringList.removeAll)
        self.defaultButton.clicked.connect(self.setToDefault)

    def setList(self, stringList):
        """
        Public method to set the list of strings to be edited.

        @param stringList list of strings to be edited
        @type list of str
        """
        self.__initialList = stringList[:]
        self.__model.setStringList(stringList)
        self.__model.sort(0)

    def getList(self):
        """
        Public method to get the edited list of strings.

        @return edited list of string
        @rtype list of str
        """
        return self.__model.stringList()[:]

    def count(self):
        """
        Public method to get the number of entries of the list.

        @return number of list entries
        @rtype int
        """
        return self.__model.rowCount()

    def isListEmpty(self):
        """
        Public method to check, if the list is empty.

        @return flag indicating an empty list
        @rtype bool
        """
        return self.__model.rowCount() == 0

    def setListWhatsThis(self, txt):
        """
        Public method to set a what's that help text for the string list.

        @param txt help text to be set
        @type str
        """
        self.stringList.setWhatsThis(txt)

    def setDefaultVisible(self, visible):
        """
        Public method to show or hide the default button.

        @param visible flag indicating the visibility of the default button
        @type bool
        """
        self.defaultButton.setVisible(visible)
        self.__defaultVisible = visible
        self.resetLine.setVisible(self.__defaultVisible and self.__resetVisible)

    def setResetVisible(self, visible):
        """
        Public method to show or hide the reset button.

        @param visible flag indicating the visibility of the reset button
        @type bool
        """
        self.resetButton.setVisible(visible)
        self.__resetVisible = visible
        self.resetLine.setVisible(self.__defaultVisible and self.__resetVisible)

    def setAddVisible(self, visible):
        """
        Public method to show or hide the add button.

        @param visible flag indicating the visibility of the add button
        @type bool
        """
        self.addButton.setVisible(visible)
        self.addLine.setVisible(visible)

    @pyqtSlot()
    def on_addButton_clicked(self):
        """
        Private slot to add an entry to the list.
        """
        entry, ok = QInputDialog.getText(
            self,
            self.tr("Add Entry"),
            self.tr("Enter the entry to add to the list:"),
            QLineEdit.EchoMode.Normal,
        )
        if ok and entry != "" and entry not in self.__model.stringList():
            self.__model.insertRow(self.__model.rowCount())
            self.__model.setData(self.__model.index(self.__model.rowCount() - 1), entry)
            self.__model.sort(0)

    @pyqtSlot()
    def on_resetButton_clicked(self):
        """
        Private slot to reset the list to its initial value.
        """
        ok = EricMessageBox.yesNo(
            self,
            self.tr("Reset List"),
            self.tr(
                "Do you really want to reset the list to its initial value? All changes"
                " will be lost."
            ),
        )
        if ok:
            self.__model.setStringList(self.__initialList)
            self.__model.sort(0)
