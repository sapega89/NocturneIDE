# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the versions of various components.
"""

import sys

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.EricGui.EricOverrideCursor import EricOverrideCursor
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp

from .Ui_VersionsDialog import Ui_VersionsDialog


class VersionsDialog(QDialog, Ui_VersionsDialog):
    """
    Class implementing a dialog to show the versions of various components.
    """

    def __init__(self, parent, title, text):
        """
        Constructor

        @param parent reference to the parent widget
        @type UserInterface
        @param title dialog title
        @type str
        @param text versions text to be shown
        @type str
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__ui = parent
        icon = QGuiApplication.windowIcon().pixmap(64, 64)

        self.setWindowTitle(title)
        self.iconLabel.setPixmap(icon)
        self.textLabel.setText(text)

        self.__checkUpdateButton = self.buttonBox.addButton(
            self.tr("Check for Upgrades..."), QDialogButtonBox.ButtonRole.ActionRole
        )
        self.__checkUpdateButton.clicked.connect(self.__checkForUpdate)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

        self.exec()

    @pyqtSlot()
    def __checkForUpdate(self):
        """
        Private slot to check, if updates of PyQt6 packages or the eric-ide
        package are available.
        """
        upgradeButtonTemplate = self.tr("Upgrade {0}...")
        headerTemplate = self.tr("<p>An upgrade of <b>{0}</b> is available.</p>")
        tableTemplate = self.tr(
            "<table>"
            "<tr><th>Package</th><th>Installed</th><th>Available</th></tr>{0}"
            "</table>"
        )
        entryTemplate = self.tr("<tr><td><b>{0}</b></td><td>{1}</td><td>{2}</td></tr>")

        msg = ""

        with EricOverrideCursor():
            pip = ericApp().getObject("Pip")
            outdatedVersionsData = pip.checkPackagesOutdated(
                ["pyqt6", "eric-ide"], "<system>", interpreter=sys.executable
            )

        pyqtVersionsData = [
            v for v in outdatedVersionsData if v[0].lower().startswith("pyqt6")
        ]
        ericVersionsData = [
            v for v in outdatedVersionsData if v[0].lower().startswith("eric-ide")
        ]

        if bool(pyqtVersionsData) or bool(ericVersionsData):
            self.buttonBox.removeButton(self.__checkUpdateButton)
            self.__checkUpdateButton = None
        else:
            msg = self.tr("No upgrades available.")

        if bool(ericVersionsData):
            self.__upgradeEricButton = self.buttonBox.addButton(
                upgradeButtonTemplate.format("eric7"),
                QDialogButtonBox.ButtonRole.ActionRole,
            )
            self.__upgradeEricButton.clicked.connect(self.__ui.upgradeEric)
            msg += headerTemplate.format("eric7")
            msg += tableTemplate.format(entryTemplate.format(*ericVersionsData[0]))

        if bool(pyqtVersionsData):
            self.__upgradePyQtButton = self.buttonBox.addButton(
                upgradeButtonTemplate.format("PyQt6"),
                QDialogButtonBox.ButtonRole.ActionRole,
            )
            self.__upgradePyQtButton.clicked.connect(self.__ui.upgradePyQt)
            msg += headerTemplate.format("PyQt6")
            msg += tableTemplate.format(
                "".join(entryTemplate.format(*v) for v in pyqtVersionsData)
            )

        if bool(ericVersionsData) and bool(pyqtVersionsData):
            self.__upgradeBothButton = self.buttonBox.addButton(
                upgradeButtonTemplate.format(self.tr("Both")),
                QDialogButtonBox.ButtonRole.ActionRole,
            )
            self.__upgradeBothButton.clicked.connect(self.__ui.upgradeEricPyQt)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setDefault(True)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Close).setFocus(
            Qt.FocusReason.OtherFocusReason
        )

        EricMessageBox.information(self, self.tr("Check for Upgrades"), msg)
