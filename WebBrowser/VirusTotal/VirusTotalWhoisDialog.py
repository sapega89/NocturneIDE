# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show the 'whois' information.
"""

from PyQt6.QtWidgets import QDialog

from eric7.EricGui import EricPixmapCache

from .Ui_VirusTotalWhoisDialog import Ui_VirusTotalWhoisDialog


class VirusTotalWhoisDialog(QDialog, Ui_VirusTotalWhoisDialog):
    """
    Class implementing a dialog to show the 'whois' information.
    """

    def __init__(self, domain, whois, parent=None):
        """
        Constructor

        @param domain domain name
        @type str
        @param whois whois information
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.headerLabel.setText(
            self.tr("<b>Whois information for domain {0}</b>").format(domain)
        )
        self.headerPixmap.setPixmap(EricPixmapCache.getPixmap("virustotal"))
        self.whoisEdit.setPlainText(whois)
