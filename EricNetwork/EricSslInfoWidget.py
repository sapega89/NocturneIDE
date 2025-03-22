# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to show SSL information.
"""

from PyQt6.QtCore import QPoint, Qt, QUrl
from PyQt6.QtNetwork import QSsl, QSslCertificate, QSslConfiguration
from PyQt6.QtWidgets import QGridLayout, QLabel, QMenu, QSizePolicy

from eric7 import EricUtilities
from eric7.EricGui import EricPixmapCache


class EricSslInfoWidget(QMenu):
    """
    Class implementing a widget to show SSL certificate infos.
    """

    def __init__(self, url, configuration, parent=None):
        """
        Constructor

        @param url URL to show SSL info for
        @type QUrl
        @param configuration SSL configuration
        @type QSslConfiguration
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__url = QUrl(url)
        self.__configuration = QSslConfiguration(configuration)

        self.setMinimumWidth(400)

        certList = self.__configuration.peerCertificateChain()
        cert = certList[0] if certList else QSslCertificate()

        layout = QGridLayout(self)
        rows = 0

        ##########################################
        ## Identity Information
        ##########################################
        imageLabel = QLabel(self)
        layout.addWidget(imageLabel, rows, 0, Qt.AlignmentFlag.AlignCenter)

        label = QLabel(self)
        label.setWordWrap(True)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        label.setText(self.tr("Identity"))
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label, rows, 1)
        rows += 1

        label = QLabel(self)
        label.setWordWrap(True)
        if cert.isNull():
            label.setText(self.tr("Warning: this site is NOT carrying a certificate."))
            imageLabel.setPixmap(EricPixmapCache.getPixmap("securityLow32"))
        else:
            valid = not cert.isBlacklisted()
            if valid:
                txt = ", ".join(cert.issuerInfo(QSslCertificate.SubjectInfo.CommonName))
                label.setText(
                    self.tr(
                        "The certificate for this site is valid"
                        " and has been verified by:\n{0}"
                    ).format(EricUtilities.decodeString(txt))
                )
                imageLabel.setPixmap(EricPixmapCache.getPixmap("securityHigh32"))
            else:
                label.setText(self.tr("The certificate for this site is NOT valid."))
                imageLabel.setPixmap(EricPixmapCache.getPixmap("securityLow32"))
            layout.addWidget(label, rows, 1)
            rows += 1

            label = QLabel(self)
            label.setWordWrap(True)
            label.setText(
                '<a href="moresslinfos">' + self.tr("Certificate Information") + "</a>"
            )
            label.linkActivated.connect(self.__showCertificateInfos)
            layout.addWidget(label, rows, 1)
            rows += 1

        ##########################################
        ## Identity Information
        ##########################################
        imageLabel = QLabel(self)
        layout.addWidget(imageLabel, rows, 0, Qt.AlignmentFlag.AlignCenter)

        label = QLabel(self)
        label.setWordWrap(True)
        label.setText(self.tr("Encryption"))
        font = label.font()
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label, rows, 1)
        rows += 1

        cipher = self.__configuration.sessionCipher()
        if cipher.isNull():
            label = QLabel(self)
            label.setWordWrap(True)
            label.setText(
                self.tr('Your connection to "{0}" is NOT encrypted.\n').format(
                    self.__url.host()
                )
            )
            layout.addWidget(label, rows, 1)
            imageLabel.setPixmap(EricPixmapCache.getPixmap("securityLow32"))
            rows += 1
        else:
            label = QLabel(self)
            label.setWordWrap(True)
            label.setText(
                self.tr('Your connection to "{0}" is encrypted.').format(
                    self.__url.host()
                )
            )
            layout.addWidget(label, rows, 1)

            proto = cipher.protocol()
            if proto == QSsl.SslProtocol.TlsV1_0:
                sslVersion = "TLS v1.0"
                imageLabel.setPixmap(EricPixmapCache.getPixmap("securityLow32"))
            elif proto == QSsl.SslProtocol.TlsV1_1:
                sslVersion = "TLS v1.1"
                imageLabel.setPixmap(EricPixmapCache.getPixmap("securityMedium32"))
            elif proto == QSsl.SslProtocol.TlsV1_2:
                sslVersion = "TLS v1.2"
                imageLabel.setPixmap(EricPixmapCache.getPixmap("securityHigh32"))
            elif proto == QSsl.SslProtocol.TlsV1_3:
                sslVersion = "TLS v1.3"
                imageLabel.setPixmap(EricPixmapCache.getPixmap("securityHigh32"))
            elif proto == QSsl.SslProtocol.DtlsV1_0:
                sslVersion = "DTLS v1.0"
                imageLabel.setPixmap(EricPixmapCache.getPixmap("securityLow32"))
            elif proto == QSsl.SslProtocol.DtlsV1_2:
                sslVersion = "DTLS v1.2"
                imageLabel.setPixmap(EricPixmapCache.getPixmap("securityHigh32"))
            else:
                sslVersion = self.tr("unknown")
                imageLabel.setPixmap(EricPixmapCache.getPixmap("securityLow32"))
            rows += 1

            label = QLabel(self)
            label.setWordWrap(True)
            label.setText(self.tr("It uses protocol: {0}").format(sslVersion))
            layout.addWidget(label, rows, 1)
            rows += 1

            label = QLabel(self)
            label.setWordWrap(True)
            if (
                not cipher.encryptionMethod()
                or not cipher.usedBits()
                or not cipher.authenticationMethod()
                or not cipher.keyExchangeMethod()
            ):
                label.setText(self.tr("The cipher data is incomplete or not known."))
            else:
                label.setText(
                    self.tr(
                        "It is encrypted using {0} at {1} bits, "
                        "with {2} for message authentication and "
                        "{3} as key exchange mechanism.\n\n"
                    ).format(
                        cipher.encryptionMethod(),
                        cipher.usedBits(),
                        cipher.authenticationMethod(),
                        cipher.keyExchangeMethod(),
                    )
                )
            layout.addWidget(label, rows, 1)
            rows += 1

    def showAt(self, pos):
        """
        Public method to show the widget.

        @param pos position to show at
        @type QPoint
        """
        self.adjustSize()
        xpos = pos.x() - self.width()
        if xpos < 0:
            xpos = 10
        p = QPoint(xpos, pos.y() + 10)
        self.move(p)
        self.show()

    def __showCertificateInfos(self):
        """
        Private slot to show certificate information.
        """
        from .EricSslCertificatesInfoDialog import EricSslCertificatesInfoDialog

        dlg = EricSslCertificatesInfoDialog(
            self.__configuration.peerCertificateChain(), parent=self
        )
        dlg.exec()

    def accept(self):
        """
        Public method to accept the widget.
        """
        self.close()
