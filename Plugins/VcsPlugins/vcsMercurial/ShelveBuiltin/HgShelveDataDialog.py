# -*- coding: utf-8 -*-

# Copyright (c) 2014 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter the data for a shelve operation.
"""

from PyQt6.QtCore import QDateTime
from PyQt6.QtWidgets import QDialog

from .Ui_HgShelveDataDialog import Ui_HgShelveDataDialog


class HgShelveDataDialog(QDialog, Ui_HgShelveDataDialog):
    """
    Class implementing a dialog to enter the data for a shelve operation.
    """

    def __init__(self, version, parent=None):
        """
        Constructor

        @param version Mercurial version
        @type tuple of three int
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__initialDateTime = QDateTime.currentDateTime()
        self.dateTimeEdit.setDateTime(self.__initialDateTime)

        if version < (5, 0, 0):
            self.keepCheckBox.setChecked(False)
            self.keepCheckBox.hide()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getData(self):
        """
        Public method to get the user data.

        @return tuple containing the name, date, message, a flag indicating
            to add/remove new/missing files and a flag indicating to keep the
            shelved changes in the working directory
        @rtype tuple of (str, QDateTime, str, bool, bool)
        """
        dateTime = (
            self.dateTimeEdit.dateTime()
            if self.dateTimeEdit.dateTime() != self.__initialDateTime
            else QDateTime()
        )
        return (
            self.nameEdit.text().replace(" ", "_"),
            dateTime,
            self.messageEdit.text(),
            self.addRemoveCheckBox.isChecked(),
            self.keepCheckBox.isChecked(),
        )
