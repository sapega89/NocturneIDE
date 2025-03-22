# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to edit the SSL error exceptions.
"""

from PyQt6.QtCore import QPoint, Qt, pyqtSlot
from PyQt6.QtWebEngineCore import QWebEngineCertificateError
from PyQt6.QtWidgets import QDialog, QMenu, QTreeWidgetItem

from .Ui_SslErrorExceptionsDialog import Ui_SslErrorExceptionsDialog


class SslErrorExceptionsDialog(QDialog, Ui_SslErrorExceptionsDialog):
    """
    Class implementing a dialog to edit the SSL error exceptions.
    """

    def __init__(self, errorsDict, parent=None):
        """
        Constructor

        @param errorsDict error exceptions
        @type dict of list of int
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__errorDescriptions = {
            QWebEngineCertificateError.Type.SslPinnedKeyNotInCertificateChain: self.tr(
                "The certificate did not match the built-in public"
                " keys pinned for the host name."
            ),
            QWebEngineCertificateError.Type.CertificateCommonNameInvalid: self.tr(
                "The certificate's common name did not match the host name."
            ),
            QWebEngineCertificateError.Type.CertificateDateInvalid: self.tr(
                "The certificate is not valid at the current date and time."
            ),
            QWebEngineCertificateError.Type.CertificateAuthorityInvalid: self.tr(
                "The certificate is not signed by a trusted authority."
            ),
            QWebEngineCertificateError.Type.CertificateContainsErrors: self.tr(
                "The certificate contains errors."
            ),
            QWebEngineCertificateError.Type.CertificateNoRevocationMechanism: self.tr(
                "The certificate has no mechanism for determining if"
                " it has been revoked."
            ),
            QWebEngineCertificateError.Type.CertificateUnableToCheckRevocation: self.tr(
                "Revocation information for the certificate is not available."
            ),
            QWebEngineCertificateError.Type.CertificateRevoked: self.tr(
                "The certificate has been revoked."
            ),
            QWebEngineCertificateError.Type.CertificateInvalid: self.tr(
                "The certificate is invalid."
            ),
            QWebEngineCertificateError.Type.CertificateWeakSignatureAlgorithm: self.tr(
                "The certificate is signed using a weak signature algorithm."
            ),
            QWebEngineCertificateError.Type.CertificateNonUniqueName: self.tr(
                "The host name specified in the certificate is not unique."
            ),
            QWebEngineCertificateError.Type.CertificateWeakKey: self.tr(
                "The certificate contains a weak key."
            ),
            QWebEngineCertificateError.Type.CertificateNameConstraintViolation: self.tr(
                "The certificate claimed DNS names that are in"
                " violation of name constraints."
            ),
            QWebEngineCertificateError.Type.CertificateValidityTooLong: self.tr(
                "The certificate has a validity period that is too long."
            ),
            QWebEngineCertificateError.Type.CertificateTransparencyRequired: self.tr(
                "Certificate Transparency was required for this"
                " connection, but the server did not provide"
                " information that complied with the policy."
            ),
            QWebEngineCertificateError.Type.CertificateKnownInterceptionBlocked: (
                self.tr(
                    "The certificate is known to be used for interception"
                    " by an entity other than the device owner."
                )
            ),
            QWebEngineCertificateError.Type.SslObsoleteVersion: self.tr(
                "The connection uses an obsolete version of SSL/TLS."
            ),
            QWebEngineCertificateError.Type.CertificateSymantecLegacy: self.tr(
                "The certificate is a legacy Symantec one that's no longer valid."
            ),
        }

        for host, errors in errorsDict.items():
            itm = QTreeWidgetItem(self.errorsTree, [host])
            self.errorsTree.setFirstItemColumnSpanned(itm, True)
            for error in errors:
                try:
                    errorDesc = self.__errorDescriptions[error]
                except KeyError:
                    errorDesc = self.tr("No error description available.")
                QTreeWidgetItem(itm, [str(error), errorDesc])

        self.errorsTree.expandAll()
        for i in range(self.errorsTree.columnCount()):
            self.errorsTree.resizeColumnToContents(i)
        self.errorsTree.sortItems(0, Qt.SortOrder.AscendingOrder)

        self.__setRemoveButtons()

    def __setRemoveButtons(self):
        """
        Private method to set the state of the 'remove' buttons.
        """
        if self.errorsTree.topLevelItemCount() == 0:
            self.removeButton.setEnabled(False)
            self.removeAllButton.setEnabled(False)
        else:
            self.removeAllButton.setEnabled(True)
            self.removeButton.setEnabled(len(self.errorsTree.selectedItems()) > 0)

    @pyqtSlot(QPoint)
    def on_errorsTree_customContextMenuRequested(self, pos):
        """
        Private slot to show the context menu.

        @param pos cursor position
        @type QPoint
        """
        menu = QMenu()
        menu.addAction(
            self.tr("Remove Selected"), self.on_removeButton_clicked
        ).setEnabled(
            self.errorsTree.topLevelItemCount() > 0
            and len(self.errorsTree.selectedItems()) > 0
        )
        menu.addAction(
            self.tr("Remove All"), self.on_removeAllButton_clicked
        ).setEnabled(self.errorsTree.topLevelItemCount() > 0)

        menu.exec(self.errorsTree.mapToGlobal(pos))

    @pyqtSlot()
    def on_errorsTree_itemSelectionChanged(self):
        """
        Private slot handling the selection of entries.
        """
        self.__setRemoveButtons()

    @pyqtSlot()
    def on_removeButton_clicked(self):
        """
        Private slot to remove the selected items.
        """
        for itm in self.errorsTree.selectedItems():
            pitm = itm.parent()
            if pitm:
                pitm.removeChild(itm)
            else:
                index = self.errorsTree.indexOfTopLevelItem(itm)
                self.errorsTree.takeTopLevelItem(index)
            del itm

        # remove all hosts without an exception
        for index in range(self.errorsTree.topLevelItemCount() - 1, -1, -1):
            itm = self.errorsTree.topLevelItem(index)
            if itm.childCount() == 0:
                self.errorsTree.takeTopLevelItem(index)
                del itm

    @pyqtSlot()
    def on_removeAllButton_clicked(self):
        """
        Private slot to remove all entries.
        """
        self.errorsTree.clear()

    def getSslErrorExceptions(self):
        """
        Public method to retrieve the list of SSL error exceptions.

        @return error exceptions
        @rtype dict of list of int
        """
        errors = {}

        for index in range(self.errorsTree.topLevelItemCount()):
            itm = self.errorsTree.topLevelItem(index)
            host = itm.text(0)
            errors[host] = []
            for cindex in range(itm.childCount()):
                citm = itm.child(cindex)
                errors[host].append(int(citm.text(0)))

        return errors
