# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Cooperation configuration page.
"""

from PyQt6.QtCore import QRegularExpression, pyqtSlot
from PyQt6.QtGui import QRegularExpressionValidator, QValidator

from eric7 import Preferences

from .ConfigurationPageBase import ConfigurationPageBase
from .Ui_CooperationPage import Ui_CooperationPage


class CooperationPage(ConfigurationPageBase, Ui_CooperationPage):
    """
    Class implementing the Cooperation configuration page.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()
        self.setupUi(self)
        self.setObjectName("CooperationPage")

        self.__bannedUserValidator = QRegularExpressionValidator(
            QRegularExpression(
                r"[a-zA-Z0-9.-]+@"
                r"(?:(?:2(?:[0-4][0-9]|5[0-5])|[01]?[0-9]{1,2})\.){3}"
                r"(?:2(?:[0-4][0-9]|5[0-5])|[01]?[0-9]{1,2})"
            ),
            self.bannedUserEdit,
        )
        self.bannedUserEdit.setValidator(self.__bannedUserValidator)

        # set initial values
        self.autostartCheckBox.setChecked(Preferences.getCooperation("AutoStartServer"))
        self.otherPortsCheckBox.setChecked(Preferences.getCooperation("TryOtherPorts"))
        self.serverPortSpin.setValue(Preferences.getCooperation("ServerPort"))
        self.portToTrySpin.setValue(Preferences.getCooperation("MaxPortsToTry"))
        self.autoAcceptCheckBox.setChecked(
            Preferences.getCooperation("AutoAcceptConnections")
        )

        self.bannedUsersList.addItems(sorted(Preferences.getCooperation("BannedUsers")))

    def save(self):
        """
        Public slot to save the Cooperation configuration.
        """
        Preferences.setCooperation(
            "AutoStartServer", self.autostartCheckBox.isChecked()
        )
        Preferences.setCooperation("TryOtherPorts", self.otherPortsCheckBox.isChecked())
        Preferences.setCooperation(
            "AutoAcceptConnections", self.autoAcceptCheckBox.isChecked()
        )
        Preferences.setCooperation("ServerPort", self.serverPortSpin.value())
        Preferences.setCooperation("MaxPortsToTry", self.portToTrySpin.value())

        bannedUsers = []
        for row in range(self.bannedUsersList.count()):
            bannedUsers.append(self.bannedUsersList.item(row).text())
        Preferences.setCooperation("BannedUsers", bannedUsers)

    @pyqtSlot()
    def on_bannedUsersList_itemSelectionChanged(self):
        """
        Private slot to react on changes of selected banned users.
        """
        self.deleteBannedUsersButton.setEnabled(
            len(self.bannedUsersList.selectedItems()) > 0
        )

    @pyqtSlot(str)
    def on_bannedUserEdit_textChanged(self, txt):
        """
        Private slot to handle the user entering a banned user.

        @param txt text entered by the user
        @type str
        """
        self.addBannedUserButton.setEnabled(
            self.__bannedUserValidator.validate(txt, len(txt))[0]
            == QValidator.State.Acceptable
        )

    @pyqtSlot()
    def on_deleteBannedUsersButton_clicked(self):
        """
        Private slot to remove the selected users from the list of
        banned users.
        """
        for itm in self.bannedUsersList.selectedItems():
            row = self.bannedUsersList.row(itm)
            itm = self.bannedUsersList.takeItem(row)
            del itm

    @pyqtSlot()
    def on_addBannedUserButton_clicked(self):
        """
        Private slot to add a user to the list of banned users.
        """
        self.bannedUsersList.addItem(self.bannedUserEdit.text())
        self.bannedUserEdit.clear()


def create(_dlg):
    """
    Module function to create the configuration page.

    @param _dlg reference to the configuration dialog (unused)
    @type ConfigurationDialog
    @return reference to the instantiated page
    @rtype ConfigurationPageBase
    """
    page = CooperationPage()
    return page
