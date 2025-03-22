# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show and edit all certificates.
"""

import contextlib
import pathlib

from PyQt6.QtCore import QByteArray, Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QTreeWidgetItem

with contextlib.suppress(ImportError):
    from PyQt6.QtNetwork import QSslCertificate, QSslConfiguration, QSsl

from eric7 import EricUtilities
from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets import EricFileDialog, EricMessageBox

from .Ui_EricSslCertificatesDialog import Ui_EricSslCertificatesDialog


class EricSslCertificatesDialog(QDialog, Ui_EricSslCertificatesDialog):
    """
    Class implementing a dialog to show and edit all certificates.
    """

    CertRole = Qt.ItemDataRole.UserRole + 1

    def __init__(self, settings, parent=None):
        """
        Constructor

        @param settings reference to the settings object
        @type QSettings
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__settings = settings

        self.serversViewButton.setIcon(EricPixmapCache.getIcon("certificates"))
        self.serversDeleteButton.setIcon(EricPixmapCache.getIcon("certificateDelete"))
        self.serversExportButton.setIcon(EricPixmapCache.getIcon("certificateExport"))
        self.serversImportButton.setIcon(EricPixmapCache.getIcon("certificateImport"))

        self.caViewButton.setIcon(EricPixmapCache.getIcon("certificates"))
        self.caDeleteButton.setIcon(EricPixmapCache.getIcon("certificateDelete"))
        self.caExportButton.setIcon(EricPixmapCache.getIcon("certificateExport"))
        self.caImportButton.setIcon(EricPixmapCache.getIcon("certificateImport"))

        self.__populateServerCertificatesTree()
        self.__populateCaCertificatesTree()

    def __populateServerCertificatesTree(self):
        """
        Private slot to populate the server certificates tree.
        """
        certificateDict = EricUtilities.toDict(
            self.__settings.value("Ssl/CaCertificatesDict")
        )
        for server in certificateDict:
            for cert in QSslCertificate.fromData(certificateDict[server]):
                self.__createServerCertificateEntry(server, cert)

        self.serversCertificatesTree.expandAll()
        for i in range(self.serversCertificatesTree.columnCount()):
            self.serversCertificatesTree.resizeColumnToContents(i)

    def __createServerCertificateEntry(self, server, cert):
        """
        Private method to create a server certificate entry.

        @param server server name of the certificate
        @type str
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
        items = self.serversCertificatesTree.findItems(
            organisation,
            Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchCaseSensitive,
        )
        if len(items) == 0:
            parent = QTreeWidgetItem(self.serversCertificatesTree, [organisation])
            parent.setFirstColumnSpanned(True)
        else:
            parent = items[0]

        itm = QTreeWidgetItem(parent, [commonName, server, expiryDate])
        itm.setData(0, self.CertRole, cert.toPem())

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_serversCertificatesTree_currentItemChanged(self, current, _previous):
        """
        Private slot handling a change of the current item in the
        server certificates list.

        @param current new current item
        @type QTreeWidgetItem
        @param _previous previous current item (unused)
        @type QTreeWidgetItem
        """
        enable = current is not None and current.parent() is not None
        self.serversViewButton.setEnabled(enable)
        self.serversDeleteButton.setEnabled(enable)
        self.serversExportButton.setEnabled(enable)

    @pyqtSlot()
    def on_serversViewButton_clicked(self):
        """
        Private slot to show data of the selected server certificate.
        """
        with contextlib.suppress(ImportError):
            from .EricSslCertificatesInfoDialog import (  # noqa: I101
                EricSslCertificatesInfoDialog,
            )

            cert = QSslCertificate.fromData(
                self.serversCertificatesTree.currentItem().data(0, self.CertRole)
            )
            dlg = EricSslCertificatesInfoDialog(cert, parent=self)
            dlg.exec()

    @pyqtSlot()
    def on_serversDeleteButton_clicked(self):
        """
        Private slot to delete the selected server certificate.
        """
        itm = self.serversCertificatesTree.currentItem()
        res = EricMessageBox.yesNo(
            self,
            self.tr("Delete Server Certificate"),
            self.tr(
                """<p>Shall the server certificate really be"""
                """ deleted?</p><p>{0}</p>"""
                """<p>If the server certificate is deleted, the"""
                """ normal security checks will be reinstantiated"""
                """ and the server has to present a valid"""
                """ certificate.</p>"""
            ).format(itm.text(0)),
        )
        if res:
            server = itm.text(1)
            cert = self.serversCertificatesTree.currentItem().data(0, self.CertRole)

            # delete the selected entry and its parent entry,
            # if it was the only one
            parent = itm.parent()
            parent.takeChild(parent.indexOfChild(itm))
            if parent.childCount() == 0:
                self.serversCertificatesTree.takeTopLevelItem(
                    self.serversCertificatesTree.indexOfTopLevelItem(parent)
                )

            # delete the certificate from the user certificate store
            certificateDict = EricUtilities.toDict(
                self.__settings.value("Ssl/CaCertificatesDict")
            )
            if server in certificateDict:
                certs = [
                    c.toPem() for c in QSslCertificate.fromData(certificateDict[server])
                ]
                if cert in certs:
                    certs.remove(cert)
                if certs:
                    pems = QByteArray()
                    for cert in certs:
                        pems.append(cert + b"\n")
                    certificateDict[server] = pems
                else:
                    del certificateDict[server]
            self.__settings.setValue("Ssl/CaCertificatesDict", certificateDict)

            # delete the certificate from the default certificates
            self.__updateDefaultConfiguration()

    @pyqtSlot()
    def on_serversImportButton_clicked(self):
        """
        Private slot to import server certificates.
        """
        certs = self.__importCertificate()
        if certs:
            server = "*"
            certificateDict = EricUtilities.toDict(
                self.__settings.value("Ssl/CaCertificatesDict")
            )
            if server in certificateDict:
                sCerts = QSslCertificate.fromData(certificateDict[server])
            else:
                sCerts = []

            pems = QByteArray()
            for cert in certs:
                if cert in sCerts:
                    commonStr = ", ".join(
                        cert.subjectInfo(QSslCertificate.SubjectInfo.CommonName)
                    )
                    EricMessageBox.warning(
                        self,
                        self.tr("Import Certificate"),
                        self.tr(
                            """<p>The certificate <b>{0}</b> already exists."""
                            """ Skipping.</p>"""
                        ).format(EricUtilities.decodeString(commonStr)),
                    )
                else:
                    pems.append(cert.toPem() + b"\n")
            if server not in certificateDict:
                certificateDict[server] = QByteArray()
            certificateDict[server].append(pems)
            self.__settings.setValue("Ssl/CaCertificatesDict", certificateDict)

            self.serversCertificatesTree.clear()
            self.__populateServerCertificatesTree()

            self.__updateDefaultConfiguration()

    @pyqtSlot()
    def on_serversExportButton_clicked(self):
        """
        Private slot to export the selected server certificate.
        """
        cert = self.serversCertificatesTree.currentItem().data(0, self.CertRole)
        fname = (
            self.serversCertificatesTree.currentItem()
            .text(0)
            .replace(" ", "")
            .replace("\t", "")
        )
        self.__exportCertificate(fname, cert)

    def __updateDefaultConfiguration(self):
        """
        Private method to update the default SSL configuration.
        """
        caList = self.__getSystemCaCertificates()
        certificateDict = EricUtilities.toDict(
            self.__settings.value("Ssl/CaCertificatesDict")
        )
        for server in certificateDict:
            for cert in QSslCertificate.fromData(certificateDict[server]):
                if cert not in caList:
                    caList.append(cert)
        sslCfg = QSslConfiguration.defaultConfiguration()
        sslCfg.setCaCertificates(caList)
        QSslConfiguration.setDefaultConfiguration(sslCfg)

    def __getSystemCaCertificates(self):
        """
        Private method to get the list of system certificates.

        @return list of system certificates
        @rtype list of QSslCertificate
        """
        caList = QSslCertificate.fromData(
            EricUtilities.toByteArray(self.__settings.value("Help/SystemCertificates"))
        )
        if not caList:
            caList = QSslConfiguration.systemCaCertificates()
        return caList

    def __populateCaCertificatesTree(self):
        """
        Private slot to populate the CA certificates tree.
        """
        for cert in self.__getSystemCaCertificates():
            self.__createCaCertificateEntry(cert)

        self.caCertificatesTree.expandAll()
        for i in range(self.caCertificatesTree.columnCount()):
            self.caCertificatesTree.resizeColumnToContents(i)
        self.caCertificatesTree.sortItems(0, Qt.SortOrder.AscendingOrder)

    def __createCaCertificateEntry(self, cert):
        """
        Private method to create a CA certificate entry.

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
        items = self.caCertificatesTree.findItems(
            organisation,
            Qt.MatchFlag.MatchFixedString | Qt.MatchFlag.MatchCaseSensitive,
        )
        if len(items) == 0:
            parent = QTreeWidgetItem(self.caCertificatesTree, [organisation])
            parent.setFirstColumnSpanned(True)
        else:
            parent = items[0]

        itm = QTreeWidgetItem(parent, [commonName, expiryDate])
        itm.setData(0, self.CertRole, cert.toPem())

    @pyqtSlot(QTreeWidgetItem, QTreeWidgetItem)
    def on_caCertificatesTree_currentItemChanged(self, current, _previous):
        """
        Private slot handling a change of the current item
        in the CA certificates list.

        @param current new current item
        @type QTreeWidgetItem
        @param _previous previous current item (unused)
        @type QTreeWidgetItem
        """
        enable = current is not None and current.parent() is not None
        self.caViewButton.setEnabled(enable)
        self.caDeleteButton.setEnabled(enable)
        self.caExportButton.setEnabled(enable)

    @pyqtSlot()
    def on_caViewButton_clicked(self):
        """
        Private slot to show data of the selected CA certificate.
        """
        with contextlib.suppress(ImportError):
            from .EricSslCertificatesInfoDialog import (  # noqa: I101
                EricSslCertificatesInfoDialog,
            )

            cert = QSslCertificate.fromData(
                self.caCertificatesTree.currentItem().data(0, self.CertRole)
            )
            dlg = EricSslCertificatesInfoDialog(cert, parent=self)
            dlg.exec()

    @pyqtSlot()
    def on_caDeleteButton_clicked(self):
        """
        Private slot to delete the selected CA certificate.
        """
        itm = self.caCertificatesTree.currentItem()
        res = EricMessageBox.yesNo(
            self,
            self.tr("Delete CA Certificate"),
            self.tr(
                """<p>Shall the CA certificate really be deleted?</p>"""
                """<p>{0}</p>"""
                """<p>If the CA certificate is deleted, the browser"""
                """ will not trust any certificate issued by this CA.</p>"""
            ).format(itm.text(0)),
        )
        if res:
            cert = self.caCertificatesTree.currentItem().data(0, self.CertRole)

            # delete the selected entry and its parent entry,
            # if it was the only one
            parent = itm.parent()
            parent.takeChild(parent.indexOfChild(itm))
            if parent.childCount() == 0:
                self.caCertificatesTree.takeTopLevelItem(
                    self.caCertificatesTree.indexOfTopLevelItem(parent)
                )

            # delete the certificate from the CA certificate store
            caCerts = self.__getSystemCaCertificates()
            if cert in caCerts:
                caCerts.remove(cert)
            pems = QByteArray()
            for cert in caCerts:
                pems.append(cert.toPem() + b"\n")
            self.__settings.setValue("Help/SystemCertificates", pems)

            # delete the certificate from the default certificates
            self.__updateDefaultConfiguration()

    @pyqtSlot()
    def on_caImportButton_clicked(self):
        """
        Private slot to import server certificates.
        """
        certs = self.__importCertificate()
        if certs:
            caCerts = self.__getSystemCaCertificates()
            for cert in certs:
                if cert in caCerts:
                    commonStr = ", ".join(
                        cert.subjectInfo(QSslCertificate.SubjectInfo.CommonName)
                    )
                    EricMessageBox.warning(
                        self,
                        self.tr("Import Certificate"),
                        self.tr(
                            """<p>The certificate <b>{0}</b> already exists."""
                            """ Skipping.</p>"""
                        ).format(EricUtilities.decodeString(commonStr)),
                    )
                else:
                    caCerts.append(cert)

            pems = QByteArray()
            for cert in caCerts:
                pems.append(cert.toPem() + b"\n")
            self.__settings.setValue("Help/SystemCertificates", pems)

            self.caCertificatesTree.clear()
            self.__populateCaCertificatesTree()

            self.__updateDefaultConfiguration()

    @pyqtSlot()
    def on_caExportButton_clicked(self):
        """
        Private slot to export the selected CA certificate.
        """
        cert = self.caCertificatesTree.currentItem().data(0, self.CertRole)
        fname = (
            self.caCertificatesTree.currentItem()
            .text(0)
            .replace(" ", "")
            .replace("\t", "")
        )
        self.__exportCertificate(fname, cert)

    def __exportCertificate(self, name, cert):
        """
        Private slot to export a certificate.

        @param name default file name without extension
        @type str
        @param cert certificate to be exported encoded as PEM
        @type QByteArray
        """
        if cert is not None:
            fname, selectedFilter = EricFileDialog.getSaveFileNameAndFilter(
                self,
                self.tr("Export Certificate"),
                name,
                self.tr(
                    "Certificate File (PEM) (*.pem);;Certificate File (DER) (*.der)"
                ),
                None,
                EricFileDialog.DontConfirmOverwrite,
            )

            if fname:
                fpath = pathlib.Path(fname)
                if not fpath.suffix:
                    ex = selectedFilter.split("(*")[1].split(")")[0]
                    if ex:
                        fpath = fpath.with_suffix(ex)
                if fpath.exists():
                    res = EricMessageBox.yesNo(
                        self,
                        self.tr("Export Certificate"),
                        self.tr(
                            "<p>The file <b>{0}</b> already exists."
                            " Overwrite it?</p>"
                        ).format(fname),
                        icon=EricMessageBox.Warning,
                    )
                    if not res:
                        return

                if fpath.suffix == ".pem":
                    crt = bytes(cert)
                else:
                    crt = bytes(
                        QSslCertificate.fromData(crt, QSsl.EncodingFormat.Pem)[
                            0
                        ].toDer()
                    )
                try:
                    with fpath.open("wb") as f:
                        f.write(crt)
                except OSError as err:
                    EricMessageBox.critical(
                        self,
                        self.tr("Export Certificate"),
                        self.tr(
                            """<p>The certificate could not be written"""
                            """ to file <b>{0}</b></p><p>Error: {1}</p>"""
                        ).format(fpath, str(err)),
                    )

    def __importCertificate(self):
        """
        Private method to read a certificate.

        @return certificates read
        @rtype list of QSslCertificate
        """
        fname = EricFileDialog.getOpenFileName(
            self,
            self.tr("Import Certificate"),
            "",
            self.tr("Certificate Files (*.pem *.crt *.der *.cer *.ca);;All Files (*)"),
        )

        if fname:
            try:
                with pathlib.Path(fname).open("rb") as f:
                    crt = QByteArray(f.read())
                cert = QSslCertificate.fromData(crt, QSsl.EncodingFormat.Pem)
                if not cert:
                    cert = QSslCertificate.fromData(crt, QSsl.EncodingFormat.Der)

                return cert
            except OSError as err:
                EricMessageBox.critical(
                    self,
                    self.tr("Import Certificate"),
                    self.tr(
                        """<p>The certificate could not be read from file"""
                        """ <b>{0}</b></p><p>Error: {1}</p>"""
                    ).format(fname, str(err)),
                )

        return []
