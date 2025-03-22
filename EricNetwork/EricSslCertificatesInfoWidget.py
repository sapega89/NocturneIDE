# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to show SSL certificate infos.
"""

from PyQt6.QtCore import QCryptographicHash, QDateTime, pyqtSlot
from PyQt6.QtWidgets import QWidget

try:
    from PyQt6.QtNetwork import QSslCertificate
except ImportError:
    QSslCertificate = None

from eric7 import EricUtilities

from .Ui_EricSslCertificatesInfoWidget import Ui_EricSslCertificatesInfoWidget


class EricSslCertificatesInfoWidget(QWidget, Ui_EricSslCertificatesInfoWidget):
    """
    Class implementing a widget to show SSL certificate infos.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__chain = []

    def showCertificateChain(self, certificateChain):
        """
        Public method to show the SSL certificates of a certificate chain.

        @param certificateChain list od SSL certificates
        @type list of QSslCertificate
        """
        if QSslCertificate:
            self.chainLabel.show()
            self.chainComboBox.show()
            self.chainComboBox.clear()

            self.__chain = certificateChain[:]

            for cert in self.__chain:
                name = ", ".join(
                    cert.subjectInfo(QSslCertificate.SubjectInfo.CommonName)
                )
                if not name:
                    name = ", ".join(
                        cert.subjectInfo(QSslCertificate.SubjectInfo.Organization)
                    )
                if not name:
                    name = cert.serialNumber()
                self.chainComboBox.addItem(name)

            self.on_chainComboBox_activated(0)

    def showCertificate(self, certificate):
        """
        Public method to show the SSL certificate information.

        @param certificate reference to the SSL certificate
        @type QSslCertificate
        """
        self.chainLabel.hide()
        self.chainComboBox.hide()
        self.chainComboBox.clear()

        self.__chain = []

        if QSslCertificate:
            self.__showCertificate(certificate)

    def __showCertificate(self, certificate):
        """
        Private method to show the  SSL certificate information.

        @param certificate reference to the SSL certificate
        @type QSslCertificate
        """
        if QSslCertificate:
            self.prohibitedLabel.setVisible(False)
            self.prohibitedLabel.setStyleSheet(
                "QLabel { color : white; background-color : red; }"
            )
            self.expiredLabel.setVisible(False)
            self.expiredLabel.setStyleSheet(
                "QLabel { color : white; background-color : red; }"
            )

            self.subjectCommonNameLabel.setText(
                self.__certificateString(
                    ", ".join(
                        certificate.subjectInfo(QSslCertificate.SubjectInfo.CommonName)
                    )
                )
            )
            self.subjectOrganizationLabel.setText(
                self.__certificateString(
                    ", ".join(
                        certificate.subjectInfo(
                            QSslCertificate.SubjectInfo.Organization
                        )
                    )
                )
            )
            self.subjectOrganizationalUnitLabel.setText(
                self.__certificateString(
                    ", ".join(
                        certificate.subjectInfo(
                            QSslCertificate.SubjectInfo.OrganizationalUnitName
                        )
                    )
                )
            )
            self.issuerCommonNameLabel.setText(
                self.__certificateString(
                    ", ".join(
                        certificate.issuerInfo(QSslCertificate.SubjectInfo.CommonName)
                    )
                )
            )
            self.issuerOrganizationLabel.setText(
                self.__certificateString(
                    ", ".join(
                        certificate.issuerInfo(QSslCertificate.SubjectInfo.Organization)
                    )
                )
            )
            self.issuerOrganizationalUnitLabel.setText(
                self.__certificateString(
                    ", ".join(
                        certificate.issuerInfo(
                            QSslCertificate.SubjectInfo.OrganizationalUnitName
                        )
                    )
                )
            )
            self.serialNumberLabel.setText(self.__serialNumber(certificate))
            self.effectiveLabel.setText(
                certificate.effectiveDate().toString("yyyy-MM-dd")
            )
            self.expiresLabel.setText(certificate.expiryDate().toString("yyyy-MM-dd"))
            self.sha1Label.setText(
                self.__formatHexString(
                    str(
                        certificate.digest(QCryptographicHash.Algorithm.Sha1).toHex(),
                        encoding="ascii",
                    )
                )
            )
            self.md5Label.setText(
                self.__formatHexString(
                    str(
                        certificate.digest(QCryptographicHash.Algorithm.Md5).toHex(),
                        encoding="ascii",
                    )
                )
            )

            if certificate.isBlacklisted():
                # something is wrong; indicate it to the user
                if self.__hasExpired(
                    certificate.effectiveDate(), certificate.expiryDate()
                ):
                    self.expiredLabel.setVisible(True)
                else:
                    self.prohibitedLabel.setVisible(True)

    def __certificateString(self, txt):
        """
        Private method to prepare some text for display.

        @param txt text to be displayed
        @type str
        @return prepared text
        @rtype str
        """
        if txt is None or txt == "":
            return self.tr("<not part of the certificate>")

        return EricUtilities.decodeString(txt)

    def __serialNumber(self, cert):
        """
        Private slot to format the certificate serial number.

        @param cert reference to the SSL certificate
        @type QSslCertificate
        @return formated serial number
        @rtype str
        """
        serial = cert.serialNumber()
        if serial == "":
            return self.tr("<not part of the certificate>")

        if b":" in serial:
            return str(serial, encoding="ascii").upper()
        else:
            hexString = hex(int(serial))[2:]
            return self.__formatHexString(hexString)

    def __formatHexString(self, hexString):
        """
        Private method to format a hex string for display.

        @param hexString hex string to be formatted
        @type str
        @return formatted string
        @rtype str
        """
        hexString = hexString.upper()

        if len(hexString) % 2 == 1:
            hexString = "0" + hexString

        hexList = []
        while hexString:
            hexList.append(hexString[:2])
            hexString = hexString[2:]

        return ":".join(hexList)

    def __hasExpired(self, effectiveDate, expiryDate):
        """
        Private method to check for a certificate expiration.

        @param effectiveDate date the certificate becomes effective
        @type QDateTime
        @param expiryDate date the certificate expires
        @type QDateTime
        @return flag indicating the expiration status
        @rtype bool
        """
        now = QDateTime.currentDateTime()

        return now < effectiveDate or now >= expiryDate

    @pyqtSlot(int)
    def on_chainComboBox_activated(self, index):
        """
        Private slot to show the certificate info for the selected entry.

        @param index number of the certificate in the certificate chain
        @type int
        """
        self.__showCertificate(self.__chain[index])
