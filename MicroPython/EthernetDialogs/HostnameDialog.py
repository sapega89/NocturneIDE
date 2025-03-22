# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter a host name for the device.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_HostnameDialog import Ui_HostnameDialog


class HostnameDialog(QDialog, Ui_HostnameDialog):
    """
    Class implementing a dialog to enter a host name for the device.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

    def getHostname(self):
        """
        Public method to get the entered host name.

        @return host name for the device
        @rtype str
        """
        return self.hostnameEdit.text()
