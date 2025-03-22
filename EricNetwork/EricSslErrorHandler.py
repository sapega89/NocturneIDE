# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a SSL error handler.
"""

import contextlib
import enum
import platform

from PyQt6.QtCore import QByteArray, QObject
from PyQt6.QtNetwork import QSsl, QSslCertificate, QSslConfiguration, QSslError

from eric7 import EricUtilities
from eric7.EricWidgets import EricMessageBox
from eric7.SystemUtilities import OSUtilities


class EricSslErrorState(enum.Enum):
    """
    Class defining the SSL error handling states.
    """

    NOT_IGNORED = 0
    SYSTEM_IGNORED = 1
    USER_IGNORED = 2


class EricSslErrorHandler(QObject):
    """
    Class implementing a handler for SSL errors.

    It also initializes the default SSL configuration with certificates
    permanently accepted by the user already.
    """

    def __init__(self, settings, parent=None):
        """
        Constructor

        @param settings reference to the settings object
        @type QSettings
        @param parent reference to the parent object (defaults to None)
        @type QObject (optional)
        """
        super().__init__(parent)

        self.__settings = settings

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
        try:
            sslProtocol = QSsl.SslProtocol.TlsV1_1OrLater
            if OSUtilities.isWindowsPlatform() and platform.win32_ver()[0] == "7":
                sslProtocol = QSsl.SslProtocol.SecureProtocols
        except AttributeError:
            sslProtocol = QSsl.SslProtocol.SecureProtocols
        sslCfg.setProtocol(sslProtocol)
        with contextlib.suppress(AttributeError):
            sslCfg.setSslOption(QSsl.SslOption.SslOptionDisableCompression, True)
        QSslConfiguration.setDefaultConfiguration(sslCfg)

    def sslErrorsReplySlot(self, reply, errors):
        """
        Public slot to handle SSL errors for a network reply.

        @param reply reference to the reply object
        @type QNetworkReply
        @param errors list of SSL errors
        @type list of QSslError
        """
        self.sslErrorsReply(reply, errors)

    def sslErrorsReply(self, reply, errors):
        """
        Public slot to handle SSL errors for a network reply.

        @param reply reference to the reply object
        @type QNetworkReply
        @param errors list of SSL errors
        @type list of QSslError
        @return tuple indicating to ignore the SSL errors and indicating a change
            of the default SSL configuration
        @rtype tuple of (EricSslErrorState, bool)
        """
        url = reply.url()
        ignore, defaultChanged = self.sslErrors(errors, url.host(), url.port())
        if ignore:
            if defaultChanged:
                reply.setSslConfiguration(QSslConfiguration.defaultConfiguration())
            reply.ignoreSslErrors()
        else:
            reply.abort()

        return ignore, defaultChanged

    def sslErrors(self, errors, server, port=-1):
        """
        Public method to handle SSL errors.

        @param errors list of SSL errors
        @type list of QSslError
        @param server name of the server
        @type str
        @param port value of the port
        @type int
        @return tuple indicating to ignore the SSL errors and indicating a
            change of the default SSL configuration
        @rtype tuple of (EricSslErrorState, bool)
        """
        caMerge = {}
        certificateDict = EricUtilities.toDict(
            self.__settings.value("Ssl/CaCertificatesDict")
        )
        for caServer in certificateDict:
            caMerge[caServer] = QSslCertificate.fromData(certificateDict[caServer])
        caNew = []

        errorStrings = []
        if port != -1:
            server += ":{0:d}".format(port)
        if errors:
            for err in errors:
                if err.error() == QSslError.SslError.NoError:
                    continue
                if server in caMerge and err.certificate() in caMerge[server]:
                    continue
                errorStrings.append(err.errorString())
                if not err.certificate().isNull():
                    cert = err.certificate()
                    if cert not in caNew:
                        caNew.append(cert)
        if not errorStrings:
            return EricSslErrorState.SYSTEM_IGNORED, False

        errorString = ".</li><li>".join(errorStrings)
        ret = EricMessageBox.yesNo(
            None,
            self.tr("SSL Errors"),
            self.tr(
                """<p>SSL Errors for <br /><b>{0}</b>"""
                """<ul><li>{1}</li></ul></p>"""
                """<p>Do you want to ignore these errors?</p>"""
            ).format(server, errorString),
            icon=EricMessageBox.Warning,
        )

        if ret:
            caRet = False
            if len(caNew) > 0:
                certinfos = []
                for cert in caNew:
                    certinfos.append(self.__certToString(cert))
                caRet = EricMessageBox.yesNo(
                    None,
                    self.tr("Certificates"),
                    self.tr(
                        """<p>Certificates:<br/>{0}<br/>"""
                        """Do you want to accept all these certificates?"""
                        """</p>"""
                    ).format("".join(certinfos)),
                )
                if caRet:
                    if server not in caMerge:
                        caMerge[server] = []
                    for cert in caNew:
                        caMerge[server].append(cert)

                    sslCfg = QSslConfiguration.defaultConfiguration()
                    caList = sslCfg.caCertificates()
                    for cert in caNew:
                        caList.append(cert)
                    sslCfg.setCaCertificates(caList)
                    try:
                        sslCfg.setProtocol(QSsl.SslProtocol.TlsV1_1OrLater)
                    except AttributeError:
                        sslCfg.setProtocol(QSsl.SslProtocol.SecureProtocols)
                    with contextlib.suppress(AttributeError):
                        sslCfg.setSslOption(
                            QSsl.SslOption.SslOptionDisableCompression, True
                        )
                    QSslConfiguration.setDefaultConfiguration(sslCfg)

                    certificateDict = {}
                    for server in caMerge:
                        pems = QByteArray()
                        for cert in caMerge[server]:
                            pems.append(cert.toPem() + b"\n")
                        certificateDict[server] = pems
                    self.__settings.setValue("Ssl/CaCertificatesDict", certificateDict)

            return EricSslErrorState.USER_IGNORED, caRet

        else:
            return EricSslErrorState.NOT_IGNORED, False

    def __certToString(self, cert):
        """
        Private method to convert a certificate to a formatted string.

        @param cert certificate to convert
        @type QSslCertificate
        @return formatted string
        @rtype str
        """
        result = "<p>"

        result += self.tr("Name: {0}").format(
            EricUtilities.html_encode(
                EricUtilities.decodeString(
                    ", ".join(cert.subjectInfo(QSslCertificate.SubjectInfo.CommonName))
                )
            )
        )

        result += self.tr("<br/>Organization: {0}").format(
            EricUtilities.html_encode(
                EricUtilities.decodeString(
                    ", ".join(
                        cert.subjectInfo(QSslCertificate.SubjectInfo.Organization)
                    )
                )
            )
        )

        result += self.tr("<br/>Issuer: {0}").format(
            EricUtilities.html_encode(
                EricUtilities.decodeString(
                    ", ".join(cert.issuerInfo(QSslCertificate.SubjectInfo.CommonName))
                )
            )
        )
        result += self.tr("<br/>Not valid before: {0}<br/>Valid Until: {1}").format(
            EricUtilities.html_encode(cert.effectiveDate().toString("yyyy-MM-dd")),
            EricUtilities.html_encode(cert.expiryDate().toString("yyyy-MM-dd")),
        )

        result += "</p>"

        return result

    def __getSystemCaCertificates(self):
        """
        Private method to get the list of system certificates.

        @return list of system certificates
        @rtype list of QSslCertificate
        """
        caList = QSslCertificate.fromData(
            EricUtilities.toByteArray(self.__settings.value("Ssl/SystemCertificates"))
        )
        if not caList:
            caList = QSslConfiguration.systemCaCertificates()
        return caList
