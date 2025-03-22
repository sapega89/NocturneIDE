# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter data needed for the initial creation
of a repository configuration file (hgrc).
"""

from PyQt6.QtCore import QUrl, pyqtSlot
from PyQt6.QtWidgets import QDialog, QLineEdit

from eric7.EricGui import EricPixmapCache

from .LargefilesExtension import getDefaults as getLargefilesDefaults
from .Ui_HgRepoConfigDataDialog import Ui_HgRepoConfigDataDialog


class HgRepoConfigDataDialog(QDialog, Ui_HgRepoConfigDataDialog):
    """
    Class implementing a dialog to enter data needed for the initial creation
    of a repository configuration file (hgrc).
    """

    def __init__(self, withLargefiles=False, largefilesData=None, parent=None):
        """
        Constructor

        @param withLargefiles flag indicating to configure the largefiles section
        @type bool
        @param largefilesData dictionary with data for the largefiles section
        @type dictdict
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.defaultShowPasswordButton.setIcon(EricPixmapCache.getIcon("showPassword"))
        self.defaultPushShowPasswordButton.setIcon(
            EricPixmapCache.getIcon("showPassword")
        )

        self.__withLargefiles = withLargefiles
        if withLargefiles:
            if largefilesData is None:
                largefilesData = getLargefilesDefaults()
            self.lfFileSizeSpinBox.setValue(largefilesData["minsize"])
            self.lfFilePatternsEdit.setText(" ".join(largefilesData["pattern"]))
        else:
            self.largefilesGroup.setVisible(False)

        self.resize(self.width(), self.minimumSizeHint().height())

    @pyqtSlot(bool)
    def on_defaultShowPasswordButton_clicked(self, checked):
        """
        Private slot to switch the default password visibility
        of the default password.

        @param checked state of the push button
        @type bool
        """
        if checked:
            self.defaultPasswordEdit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.defaultPasswordEdit.setEchoMode(QLineEdit.EchoMode.Password)

    @pyqtSlot(bool)
    def on_defaultPushShowPasswordButton_clicked(self, checked):
        """
        Private slot to switch the default password visibility
        of the default push password.

        @param checked state of the push button
        @type bool
        """
        if checked:
            self.defaultPushPasswordEdit.setEchoMode(QLineEdit.EchoMode.Normal)
        else:
            self.defaultPushPasswordEdit.setEchoMode(QLineEdit.EchoMode.Password)

    def getData(self):
        """
        Public method to get the data entered into the dialog.

        @return tuple giving the default and default push URLs
        @rtype tuple of (str, str)
        """
        defaultUrl = QUrl.fromUserInput(self.defaultUrlEdit.text())
        username = self.defaultUserEdit.text()
        password = self.defaultPasswordEdit.text()
        if username:
            defaultUrl.setUserName(username)
        if password:
            defaultUrl.setPassword(password)
        defaultUrl = defaultUrl.toString() if defaultUrl.isValid() else ""

        defaultPushUrl = QUrl.fromUserInput(self.defaultPushUrlEdit.text())
        username = self.defaultPushUserEdit.text()
        password = self.defaultPushPasswordEdit.text()
        if username:
            defaultPushUrl.setUserName(username)
        if password:
            defaultPushUrl.setPassword(password)
        defaultPushUrl = defaultPushUrl.toString() if defaultPushUrl.isValid() else ""

        return defaultUrl, defaultPushUrl

    def getLargefilesData(self):
        """
        Public method to get the data for the largefiles extension.

        @return tuple with the minimum file size and file patterns. None as value
            denote to use the default value.
        @rtype tuple of (int, list of str)
        """
        if self.__withLargefiles:
            lfDefaults = getLargefilesDefaults()
            if self.lfFileSizeSpinBox.value() == lfDefaults["minsize"]:
                minsize = None
            else:
                minsize = self.lfFileSizeSpinBox.value()
            patterns = self.lfFilePatternsEdit.text().split()
            if set(patterns) == set(lfDefaults["pattern"]):
                patterns = None

            return minsize, patterns
        else:
            return None, None
