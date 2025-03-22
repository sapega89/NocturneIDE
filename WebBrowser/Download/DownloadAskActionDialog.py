# -*- coding: utf-8 -*-

# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to ask for a download action.
"""

from PyQt6.QtWidgets import QDialog

from eric7 import Preferences

from .Ui_DownloadAskActionDialog import Ui_DownloadAskActionDialog


class DownloadAskActionDialog(QDialog, Ui_DownloadAskActionDialog):
    """
    Class implementing a dialog to ask for a download action.
    """

    def __init__(self, fileName, mimeType, baseUrl, parent=None):
        """
        Constructor

        @param fileName file name
        @type str
        @param mimeType mime type
        @type str
        @param baseUrl URL
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.infoLabel.setText("<b>{0}</b>".format(fileName))
        self.typeLabel.setText(mimeType)
        self.siteLabel.setText(baseUrl)

        if (
            not Preferences.getWebBrowser("VirusTotalEnabled")
            or Preferences.getWebBrowser("VirusTotalServiceKey") == ""
        ):
            self.scanButton.setHidden(True)

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getAction(self):
        """
        Public method to get the selected action.

        @return selected action ("save", "open", "scan" or "cancel")
        @rtype str
        """
        if self.openButton.isChecked():
            return "open"
        elif self.scanButton.isChecked():
            return "scan"
        elif self.saveButton.isChecked():
            return "save"
        else:
            # should not happen, but keep it safe
            return "cancel"
