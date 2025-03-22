# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the cookies configuration dialog.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog

from .CookieJar import CookieAcceptPolicy, CookieKeepPolicy
from .Ui_CookiesConfigurationDialog import Ui_CookiesConfigurationDialog


class CookiesConfigurationDialog(QDialog, Ui_CookiesConfigurationDialog):
    """
    Class implementing the cookies configuration dialog.
    """

    def __init__(self, parent):
        """
        Constructor

        @param parent reference to the parent object
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__mw = parent

        jar = self.__mw.cookieJar()
        acceptPolicy = jar.acceptPolicy()
        if acceptPolicy == CookieAcceptPolicy.Always:
            self.acceptCombo.setCurrentIndex(0)
        elif acceptPolicy == CookieAcceptPolicy.Never:
            self.acceptCombo.setCurrentIndex(1)
        elif acceptPolicy == CookieAcceptPolicy.OnlyFromSitesNavigatedTo:
            self.acceptCombo.setCurrentIndex(2)

        keepPolicy = jar.keepPolicy()
        if keepPolicy == CookieKeepPolicy.UntilExpire:
            self.keepUntilCombo.setCurrentIndex(0)
        elif keepPolicy == CookieKeepPolicy.UntilExit:
            self.keepUntilCombo.setCurrentIndex(1)

        self.filterTrackingCookiesCheckbox.setChecked(jar.filterTrackingCookies())

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def accept(self):
        """
        Public slot to accept the dialog.
        """
        acceptSelection = self.acceptCombo.currentIndex()
        if acceptSelection == 0:
            acceptPolicy = CookieAcceptPolicy.Always
        elif acceptSelection == 1:
            acceptPolicy = CookieAcceptPolicy.Never
        elif acceptSelection == 2:
            acceptPolicy = CookieAcceptPolicy.OnlyFromSitesNavigatedTo

        keepSelection = self.keepUntilCombo.currentIndex()
        if keepSelection == 0:
            keepPolicy = CookieKeepPolicy.UntilExpire
        elif keepSelection == 1:
            keepPolicy = CookieKeepPolicy.UntilExit

        jar = self.__mw.cookieJar()
        jar.setAcceptPolicy(acceptPolicy)
        jar.setKeepPolicy(keepPolicy)
        jar.setFilterTrackingCookies(self.filterTrackingCookiesCheckbox.isChecked())

        super().accept()

    @pyqtSlot()
    def on_exceptionsButton_clicked(self):
        """
        Private slot to show the cookies exceptions dialog.
        """
        from .CookiesExceptionsDialog import CookiesExceptionsDialog

        dlg = CookiesExceptionsDialog(self.__mw.cookieJar(), parent=self)
        dlg.exec()

    @pyqtSlot()
    def on_cookiesButton_clicked(self):
        """
        Private slot to show the cookies dialog.
        """
        from .CookiesDialog import CookiesDialog

        dlg = CookiesDialog(self.__mw.cookieJar(), parent=self)
        dlg.exec()
