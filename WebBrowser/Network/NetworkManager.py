# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a network manager class.
"""

import contextlib
import json

from PyQt6.QtCore import QByteArray, pyqtSignal
from PyQt6.QtNetwork import (
    QNetworkAccessManager,
    QNetworkProxy,
    QNetworkProxyFactory,
    QNetworkRequest,
)
from PyQt6.QtWidgets import QDialog, QStyle

from eric7 import EricUtilities, Preferences
from eric7.EricCore import EricPreferences
from eric7.EricNetwork.EricNetworkProxyFactory import (
    EricNetworkProxyFactory,
    proxyAuthenticationRequired,
)
from eric7.EricWidgets import EricMessageBox
from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricAuthenticationDialog import EricAuthenticationDialog
from eric7.Utilities.AutoSaver import AutoSaver
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

try:
    from eric7.EricNetwork.EricSslErrorHandler import EricSslErrorHandler

    SSL_AVAILABLE = True
except ImportError:
    SSL_AVAILABLE = False

from ..Tools.WebBrowserTools import getHtmlPage, pixmapToDataUrl
from .EricSchemeHandler import EricSchemeHandler
from .NetworkUrlInterceptor import NetworkUrlInterceptor


class NetworkManager(QNetworkAccessManager):
    """
    Class implementing a network manager.

    @signal changed() emitted to indicate a change
    """

    changed = pyqtSignal()

    def __init__(self, engine, parent=None):
        """
        Constructor

        @param engine reference to the help engine
        @type QHelpEngine
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        if EricPreferences.getNetworkProxy("UseSystemProxy"):
            QNetworkProxyFactory.setUseSystemConfiguration(True)
        else:
            self.__proxyFactory = EricNetworkProxyFactory()
            QNetworkProxyFactory.setApplicationProxyFactory(self.__proxyFactory)
            QNetworkProxyFactory.setUseSystemConfiguration(False)

        self.languagesChanged()

        if SSL_AVAILABLE:
            self.__sslErrorHandler = EricSslErrorHandler(
                Preferences.getSettings(), self
            )
            self.sslErrors.connect(self.__sslErrorHandlingSlot)

        self.__temporarilyIgnoredSslErrors = {}
        self.__permanentlyIgnoredSslErrors = {}
        # dictionaries of permanently and temporarily ignored SSL errors

        self.__insecureHosts = set()

        self.__loaded = False
        self.__saveTimer = AutoSaver(self, self.__save)

        self.changed.connect(self.__saveTimer.changeOccurred)
        self.proxyAuthenticationRequired.connect(proxyAuthenticationRequired)
        self.authenticationRequired.connect(
            lambda reply, auth: self.authentication(reply.url(), auth)
        )

        self.__ericSchemeHandler = EricSchemeHandler()
        WebBrowserWindow.webProfile().installUrlSchemeHandler(
            QByteArray(b"eric"), self.__ericSchemeHandler
        )

        if engine:
            from eric7.QtHelpInterface.QtHelpSchemeHandler import (  # noqa: I101
                QtHelpSchemeHandler,
            )

            self.__qtHelpSchemeHandler = QtHelpSchemeHandler(engine)
            WebBrowserWindow.webProfile().installUrlSchemeHandler(
                QByteArray(b"qthelp"), self.__qtHelpSchemeHandler
            )

        self.__interceptor = NetworkUrlInterceptor(self)
        WebBrowserWindow.webProfile().setUrlRequestInterceptor(self.__interceptor)

        WebBrowserWindow.cookieJar()

    def __save(self):
        """
        Private slot to save the permanent SSL error exceptions.
        """
        if not self.__loaded:
            return

        if not WebBrowserWindow.isPrivate():
            dbString = json.dumps(self.__permanentlyIgnoredSslErrors)
            Preferences.setWebBrowser("SslExceptionsDB", dbString)

    def __load(self):
        """
        Private method to load the permanent SSL error exceptions.
        """
        if self.__loaded:
            return

        dbString = Preferences.getWebBrowser("SslExceptionsDB")
        if dbString:
            with contextlib.suppress(ValueError):
                db = json.loads(dbString)
                self.__permanentlyIgnoredSslErrors = db

        self.__loaded = True

    def shutdown(self):
        """
        Public method to shut down the network manager.
        """
        self.__saveTimer.saveIfNeccessary()
        self.__loaded = False
        self.__temporarilyIgnoredSslErrors = {}
        self.__permanentlyIgnoredSslErrors = {}

        # set proxy factory to None to avoid crashes
        QNetworkProxyFactory.setApplicationProxyFactory(None)

    def showSslErrorExceptionsDialog(self, parent=None):
        """
        Public method to show the SSL error exceptions dialog.

        @param parent reference to the parent widget
        @type QWidget
        """
        from .SslErrorExceptionsDialog import SslErrorExceptionsDialog

        self.__load()

        dlg = SslErrorExceptionsDialog(
            self.__permanentlyIgnoredSslErrors,
            parent=parent,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.__permanentlyIgnoredSslErrors = dlg.getSslErrorExceptions()
            self.changed.emit()

    def clearSslExceptions(self):
        """
        Public method to clear the permanent SSL certificate error exceptions.
        """
        self.__load()

        self.__permanentlyIgnoredSslErrors = {}
        self.changed.emit()
        self.__saveTimer.saveIfNeccessary()

    def certificateError(self, error, view):
        """
        Public method to handle SSL certificate errors.

        @param error object containing the certificate error information
        @type QWebEngineCertificateError
        @param view reference to a view to be used as parent for the dialog
        @type QWidget
        @return flag indicating to ignore this error
        @rtype bool
        """
        if Preferences.getWebBrowser("AlwaysRejectFaultyCertificates"):
            return False

        self.__load()

        host = error.url().host()

        self.__insecureHosts.add(host)

        if (
            host in self.__temporarilyIgnoredSslErrors
            and error.error() in self.__temporarilyIgnoredSslErrors[host]
        ):
            return True

        if (
            host in self.__permanentlyIgnoredSslErrors
            and error.error() in self.__permanentlyIgnoredSslErrors[host]
        ):
            return True

        title = self.tr("SSL Certificate Error")
        msgBox = EricMessageBox.EricMessageBox(
            EricMessageBox.Warning,
            title,
            self.tr(
                """<b>{0}</b>"""
                """<p>The host <b>{1}</b> you are trying to access has"""
                """ errors in the SSL certificate.</p>"""
                """<ul><li>{2}</li></ul>"""
                """<p>Would you like to make an exception?</p>"""
            ).format(title, host, error.errorDescription()),
            modal=True,
            parent=view,
        )
        permButton = msgBox.addButton(
            self.tr("&Permanent accept"), EricMessageBox.AcceptRole
        )
        tempButton = msgBox.addButton(
            self.tr("&Temporary accept"), EricMessageBox.AcceptRole
        )
        msgBox.addButton(self.tr("&Reject"), EricMessageBox.RejectRole)
        msgBox.exec()
        if msgBox.clickedButton() == permButton:
            if host not in self.__permanentlyIgnoredSslErrors:
                self.__permanentlyIgnoredSslErrors[host] = []
            self.__permanentlyIgnoredSslErrors[host].append(error.error())
            self.changed.emit()
            return True
        elif msgBox.clickedButton() == tempButton:
            if host not in self.__temporarilyIgnoredSslErrors:
                self.__temporarilyIgnoredSslErrors[host] = []
            self.__temporarilyIgnoredSslErrors[host].append(error.error())
            return True
        else:
            return False

    def __sslErrorHandlingSlot(self, reply, errors):
        """
        Private slot to handle SSL errors for a network reply.

        @param reply reference to the reply object
        @type QNetworkReply
        @param errors list of SSL errors
        @type list of QSslError
        """
        if Preferences.getWebBrowser("AlwaysRejectFaultyCertificates"):
            return

        self.__load()

        host = reply.url().host()
        if (
            host in self.__permanentlyIgnoredSslErrors
            or host in self.__temporarilyIgnoredSslErrors
        ):
            reply.ignoreSslErrors()
        else:
            self.__sslErrorHandler.sslErrorsReply(reply, errors)

    def isInsecureHost(self, host):
        """
        Public method to check a host against the list of insecure hosts.

        @param host name of the host to be checked
        @type str
        @return flag indicating an insecure host
        @rtype bool
        """
        return host in self.__insecureHosts

    def authentication(self, url, auth, page=None):
        """
        Public slot to handle an authentication request.

        @param url URL requesting authentication
        @type QUrl
        @param auth reference to the authenticator object
        @type QAuthenticator
        @param page reference to the web page
        @type QWebEnginePage or None
        """
        urlRoot = "{0}://{1}".format(url.scheme(), url.authority())
        realm = auth.realm()
        if not realm and "realm" in auth.options():
            realm = auth.option("realm")
        info = (
            self.tr("<b>Enter username and password for '{0}', realm '{1}'</b>").format(
                urlRoot, realm
            )
            if realm
            else self.tr("<b>Enter username and password for '{0}'</b>").format(urlRoot)
        )

        dlg = EricAuthenticationDialog(
            info,
            auth.user(),
            Preferences.getUser("SavePasswords"),
            Preferences.getUser("SavePasswords"),
        )
        if Preferences.getUser("SavePasswords"):
            (
                username,
                password,
            ) = WebBrowserWindow.passwordManager().getLogin(url, realm)
            if username:
                dlg.setData(username, password)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            username, password = dlg.getData()
            auth.setUser(username)
            auth.setPassword(password)
            if Preferences.getUser("SavePasswords") and dlg.shallSave():
                pm = WebBrowserWindow.passwordManager()
                pm.setLogin(url, realm, username, password)
        else:
            if page is not None:
                self.__showAuthenticationErrorPage(page, url)

    def __showAuthenticationErrorPage(self, page, url):
        """
        Private method to show an authentication error page.

        @param page reference to the page
        @type QWebEnginePage
        @param url reference to the URL requesting authentication
        @type QUrl
        """
        html = getHtmlPage("authenticationErrorPage.html")
        html = html.replace(
            "@IMAGE@",
            pixmapToDataUrl(
                ericApp()
                .style()
                .standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
                .pixmap(48, 48)
            ).toString(),
        )
        html = html.replace(
            "@FAVICON@",
            pixmapToDataUrl(
                ericApp()
                .style()
                .standardIcon(QStyle.StandardPixmap.SP_MessageBoxCritical)
                .pixmap(16, 16)
            ).toString(),
        )
        html = html.replace("@TITLE@", self.tr("Authentication required"))
        html = html.replace("@H1@", self.tr("Authentication required"))
        html = html.replace("@LI-1@", self.tr("Authentication is required to access:"))
        html = html.replace("@LI-2@", '<a href="{0}">{0}</a>'.format(url.toString()))
        page.setHtml(html, url)

    def proxyAuthentication(self, _requestUrl, auth, _proxyHost):
        """
        Public slot to handle a proxy authentication request.

        @param _requestUrl requested URL (unused)
        @type QUrl
        @param auth reference to the authenticator object
        @type QAuthenticator
        @param _proxyHost name of the proxy host (unused)
        @type str
        """
        proxy = QNetworkProxy.applicationProxy()
        if proxy.user() and proxy.password():
            auth.setUser(proxy.user())
            auth.setPassword(proxy.password())
            return

        proxyAuthenticationRequired(proxy, auth)

    def languagesChanged(self):
        """
        Public slot to (re-)load the list of accepted languages.
        """
        from eric7.WebBrowser.WebBrowserLanguagesDialog import WebBrowserLanguagesDialog

        languages = EricUtilities.toList(
            Preferences.getSettings().value(
                "WebBrowser/AcceptLanguages",
                WebBrowserLanguagesDialog.defaultAcceptLanguages(),
            )
        )
        self.__acceptLanguage = WebBrowserLanguagesDialog.httpString(languages)

        WebBrowserWindow.webProfile().setHttpAcceptLanguage(self.__acceptLanguage)

    def installUrlInterceptor(self, interceptor):
        """
        Public method to install an URL interceptor.

        @param interceptor URL interceptor to be installed
        @type UrlInterceptor
        """
        self.__interceptor.installUrlInterceptor(interceptor)

    def removeUrlInterceptor(self, interceptor):
        """
        Public method to remove an URL interceptor.

        @param interceptor URL interceptor to be removed
        @type UrlInterceptor
        """
        self.__interceptor.removeUrlInterceptor(interceptor)

    def preferencesChanged(self):
        """
        Public slot to handle a change of preferences.
        """
        self.__interceptor.preferencesChanged()

        if EricPreferences.getNetworkProxy("UseSystemProxy"):
            QNetworkProxyFactory.setUseSystemConfiguration(True)
        else:
            self.__proxyFactory = EricNetworkProxyFactory()
            QNetworkProxyFactory.setApplicationProxyFactory(self.__proxyFactory)
            QNetworkProxyFactory.setUseSystemConfiguration(False)

    def createRequest(self, op, request, data):
        """
        Public method to launch a network action.

        @param op operation to be performed
        @type QNetworkAccessManager.Operation
        @param request request to be operated on
        @type QNetworkRequest
        @param data reference to the data to be sent
        @type QIODevice
        @return reference to the network reply
        @rtype QNetworkReply
        """
        req = QNetworkRequest(request)
        req.setAttribute(QNetworkRequest.Attribute.Http2AllowedAttribute, True)

        return super().createRequest(op, req, data)
