# -*- coding: utf-8 -*-

# Copyright (c) 2019 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select a SSL certificate.
"""

import contextlib

from PyQt6.QtCore import Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QTreeWidgetItem

with contextlib.suppress(ImportError):
    from PyQt6.QtNetwork import QSslCertificate

from eric7 import EricUtilities
from eric7.EricGui import EricPixmapCache

from .Ui_EricSslCertificateSelectionDialog import Ui_EricSslCertificateSelectionDialog


class EricSslCertificateSelectionDialog(QDialog, Ui_EricSslCertificateSelectionDialog):
    """
    Class implementing a dialog to select a SSL certificate.
    """

    CertRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, certificates, parent=None):
        """
        Constructor

        @param certificates list of SSL certificates to select from
        @type list of QSslCertificate
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.viewButton.setIcon(EricPixmapCache.getIcon("certificates"))

        self.buttonBox.button(QDialogButtonBox.OK).setEnabled(False)
        self.viewButton.setEnabled(False)

        self.__populateCertificatesTree(certificates)

    def __populateCertificatesTree(self, certificates):
        """
        Private slot to populate the certificates tree.

        @param certificates list of SSL certificates to select from
        @type list of QSslCertificate
        """
        for cert in certificates():
            self.__createCertificateEntry(cert)

        self.certificatesTree.expandAll()
        for i in range(self.certificatesTree.columnCount()):
            self.certificatesTree.resizeColumnToContents(i)
        self.certificatesTree.sortItems(0, Qt.SortOrder.AscendingOrder)

    def __createCaCertificateEntry(self, cert):
        """
        Private method to create a certificate entry.

        @param cert certificate to insert
        @type QSslCertificate
        """
        # step 1: extract the info to be shown
        organisation = EricUtilities.decodeString(
            ", ".join(cert.subjectInfo(QSslCertificate.SubjectInfo.Organization))
        )
        commonName = EricUtilities.decodeString(
            ", ".join(cert.subjectInfo(QSslCertificate.SubjectInfo.CommonName))
        )
        if organisation is None or organisation == "":
            organisation = self.tr("(Unknown)")
        if commonName is None or commonName == "":
            commonName = self.tr("(Unknown common name)")
        expiryDate = cert.expiryDate().toString("yyyy-MM-dd")

        # step 2: create the entry
        items = self.certificatesTree.findItems(
            organisation,
            Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchCaseSensitive,
        )
        if len(items) == 0:
            parent = QTreeWidgetItem(self.certificatesTree, [organisation])
            parent.setFirstColumnSpanned(True)
        else:
            parent = items[0]

        itm = QTreeWidgetItem(parent, [commonName, expiryDate])
        itm.setData(0, self.CertRole, cert.toPem())

    @pyqtSlot()
    def on_certificatesTree_itemSelectionChanged(self):
        """
        Private slot to handle the selection of an item.
        """
        enable = (
            len(self.certificatesTree.selectedItems()) > 0
            and self.certificatesTree.selectedItems()[0].parent() is not None
        )
        self.buttonBox.button(QDialogButtonBox.OK).setEnabled(enable)
        self.viewButton.setEnabled(enable)

    @pyqtSlot()
    def on_viewButton_clicked(self):
        """
        Private slot to show data of the selected certificate.
        """
        with contextlib.suppress(ImportError):
            from .EricSslCertificatesInfoDialog import (  # noqa: I101
                EricSslCertificatesInfoDialog,
            )

            cert = QSslCertificate.fromData(
                self.certificatesTree.selectedItems()[0].data(0, self.CertRole)
            )
            dlg = EricSslCertificatesInfoDialog(cert, parent=self)
            dlg.exec()

    def getSelectedCertificate(self):
        """
        Public method to get the selected certificate.

        @return selected certificate
        @rtype QSslCertificate
        """
        valid = (
            len(self.certificatesTree.selectedItems()) > 0
            and self.certificatesTree.selectedItems()[0].parent() is not None
        )

        certificate = (
            QSslCertificate.fromData(
                self.certificatesTree.selectedItems()[0].data(0, self.CertRole)
            )
            if valid
            else None
        )

        return certificate
