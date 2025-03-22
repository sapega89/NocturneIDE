# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the Python side for calling the password manager.
"""

from PyQt6.QtCore import QByteArray, QObject, pyqtSlot


class PasswordManagerJsObject(QObject):
    """
    Class implementing the Python side for calling the password manager.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type ExternalJsObject
        """
        super().__init__(parent)

        self.__external = parent

    @pyqtSlot(str, str, str, QByteArray)
    def formSubmitted(self, urlStr, userName, password, data):
        """
        Public slot passing form data to the password manager.

        @param urlStr form submission URL
        @type str
        @param userName name of the user
        @type str
        @param password user password
        @type str
        @param data data to be submitted
        @type QByteArray
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        WebBrowserWindow.passwordManager().formSubmitted(
            urlStr, userName, password, data, self.__external.page()
        )
