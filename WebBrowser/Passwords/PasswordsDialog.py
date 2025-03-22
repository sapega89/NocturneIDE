# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show all saved logins.
"""

from PyQt6.QtCore import QSortFilterProxyModel, pyqtSlot
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import QDialog

from eric7.EricWidgets import EricMessageBox
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .PasswordModel import PasswordModel
from .Ui_PasswordsDialog import Ui_PasswordsDialog


class PasswordsDialog(QDialog, Ui_PasswordsDialog):
    """
    Class implementing a dialog to show all saved logins.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__showPasswordsText = self.tr("Show Passwords")
        self.__hidePasswordsText = self.tr("Hide Passwords")
        self.passwordsButton.setText(self.__showPasswordsText)

        self.removeButton.clicked.connect(self.passwordsTable.removeSelected)
        self.removeAllButton.clicked.connect(self.passwordsTable.removeAll)

        self.passwordsTable.verticalHeader().hide()
        self.__passwordModel = PasswordModel(WebBrowserWindow.passwordManager(), self)
        self.__proxyModel = QSortFilterProxyModel(self)
        self.__proxyModel.setSourceModel(self.__passwordModel)
        self.searchEdit.textChanged.connect(self.__proxyModel.setFilterFixedString)
        self.passwordsTable.setModel(self.__proxyModel)

        fm = QFontMetrics(QFont())
        height = fm.height() + fm.height() // 3
        self.passwordsTable.verticalHeader().setDefaultSectionSize(height)
        self.passwordsTable.verticalHeader().setMinimumSectionSize(-1)

        self.__calculateHeaderSizes()

    def __calculateHeaderSizes(self):
        """
        Private method to calculate the section sizes of the horizontal header.
        """
        fm = QFontMetrics(QFont())
        for section in range(self.__passwordModel.columnCount()):
            header = self.passwordsTable.horizontalHeader().sectionSizeHint(section)
            if section == 0:
                header = fm.horizontalAdvance("averagebiglongsitename")
            elif section == 1:
                header = fm.horizontalAdvance("averagelongusername")
            elif section == 2:
                header = fm.horizontalAdvance("averagelongpassword")
            buffer = fm.horizontalAdvance("mm")
            header += buffer
            self.passwordsTable.horizontalHeader().resizeSection(section, header)
        self.passwordsTable.horizontalHeader().setStretchLastSection(True)

    @pyqtSlot()
    def on_passwordsButton_clicked(self):
        """
        Private slot to switch the password display mode.
        """
        if self.__passwordModel.showPasswords():
            self.__passwordModel.setShowPasswords(False)
            self.passwordsButton.setText(self.__showPasswordsText)
        else:
            res = EricMessageBox.yesNo(
                self,
                self.tr("Saved Passwords"),
                self.tr("""Do you really want to show passwords?"""),
            )
            if res:
                self.__passwordModel.setShowPasswords(True)
                self.passwordsButton.setText(self.__hidePasswordsText)
        self.__calculateHeaderSizes()
