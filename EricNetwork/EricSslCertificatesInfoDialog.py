# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show SSL certificate infos.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_EricSslCertificatesInfoDialog import Ui_EricSslCertificatesInfoDialog


class EricSslCertificatesInfoDialog(QDialog, Ui_EricSslCertificatesInfoDialog):
    """
    Class implementing a dialog to show SSL certificate infos.
    """

    def __init__(self, certificateChain, parent=None):
        """
        Constructor

        @param certificateChain SSL certificate chain
        @type list of QSslCertificate
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.sslWidget.showCertificateChain(certificateChain)
