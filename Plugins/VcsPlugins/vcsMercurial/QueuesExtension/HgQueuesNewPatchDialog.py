# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to get the data for a new patch.
"""

import enum

from PyQt6.QtCore import QDateTime, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricWidgets.EricApplication import ericApp

from .Ui_HgQueuesNewPatchDialog import Ui_HgQueuesNewPatchDialog


class HgQueuesNewPatchDialogMode(enum.Enum):
    """
    Class defining the dialog modes.
    """

    NEW = 0
    REFRESH = 1


class HgQueuesNewPatchDialog(QDialog, Ui_HgQueuesNewPatchDialog):
    """
    Class implementing a dialog to get the data for a new patch.
    """

    def __init__(self, mode, message="", parent=None):
        """
        Constructor

        @param mode mode of the dialog
        @type HgQueuesNewPatchDialogMode
        @param message text to set as the commit message
        @type str
        @param parent reference to the parent widget
        @type QWidget
        @exception ValueError raised to indicate an invalid dialog mode
        """
        super().__init__(parent)
        self.setupUi(self)

        if not isinstance(mode, HgQueuesNewPatchDialogMode):
            raise ValueError("invalid value for mode")

        self.__mode = mode
        if self.__mode == HgQueuesNewPatchDialogMode.REFRESH:
            self.nameLabel.hide()
            self.nameEdit.hide()

        project = ericApp().getObject("Project")
        pwl, pel = project.getProjectDictionaries()
        language = project.getProjectSpellLanguage()
        self.messageEdit.setLanguageWithPWL(language, pwl or None, pel or None)
        if message:
            self.messageEdit.setPlainText(message)

        self.dateTimeEdit.setDateTime(QDateTime.currentDateTime())

        self.__updateUI()

    def __updateUI(self):
        """
        Private slot to update the UI.
        """
        enable = (
            self.messageEdit.toPlainText() != ""
            if self.__mode == HgQueuesNewPatchDialogMode.REFRESH
            else (self.nameEdit.text() != "" and self.messageEdit.toPlainText() != "")
        )
        if self.userGroup.isChecked():
            enable = enable and (
                self.currentUserCheckBox.isChecked() or self.userEdit.text() != ""
            )

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(enable)

    @pyqtSlot(str)
    def on_nameEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the patch name.

        @param _txt text of the edit (unused)
        @type str
        """
        self.__updateUI()

    @pyqtSlot()
    def on_messageEdit_textChanged(self):
        """
        Private slot to handle changes of the patch message.
        """
        self.__updateUI()

    @pyqtSlot(bool)
    def on_userGroup_toggled(self, _checked):
        """
        Private slot to handle changes of the user group state.

        @param _checked flag giving the checked state (unused)
        @type bool
        """
        self.__updateUI()

    @pyqtSlot(bool)
    def on_currentUserCheckBox_toggled(self, _checked):
        """
        Private slot to handle changes of the currentuser state.

        @param _checked flag giving the checked state (unused)
        @type bool
        """
        self.__updateUI()

    @pyqtSlot(str)
    def on_userEdit_textChanged(self, _txt):
        """
        Private slot to handle changes of the user name.

        @param _txt text of the edit (unused)
        @type str
        """
        self.__updateUI()

    def getData(self):
        """
        Public method to retrieve the entered data.

        @return tuple giving the patch name and message, a tuple giving a
            flag indicating to set the user, a flag indicating to use the
            current user and the user name and another tuple giving a flag
            indicating to set the date, a flag indicating to use the
            current date and the date
        @rtype tuple of (str, str, tuple of (bool, bool, str), tuple of
            (bool, bool, str))
        """
        userData = (
            self.userGroup.isChecked(),
            self.currentUserCheckBox.isChecked(),
            self.userEdit.text(),
        )
        dateData = (
            self.dateGroup.isChecked(),
            self.currentDateCheckBox.isChecked(),
            self.dateTimeEdit.dateTime().toString("yyyy-MM-dd hh:mm"),
        )
        return (
            self.nameEdit.text().replace(" ", "_"),
            self.messageEdit.toPlainText(),
            userData,
            dateData,
        )
