# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a network proxy factory.
"""

import os
import re

from PyQt6.QtCore import QCoreApplication, QUrl
from PyQt6.QtNetwork import QNetworkProxy, QNetworkProxyFactory, QNetworkProxyQuery
from PyQt6.QtWidgets import QDialog

from eric7 import EricUtilities
from eric7.EricCore import EricPreferences
from eric7.EricWidgets import EricMessageBox
from eric7.SystemUtilities import OSUtilities


def schemeFromProxyType(proxyType):
    """
    Module function to determine the scheme name from the proxy type.

    @param proxyType type of the proxy
    @type QNetworkProxy.ProxyType
    @return schemeone of Http, Https, Ftp)
    @rtype str
    """
    scheme = ""
    if proxyType == QNetworkProxy.ProxyType.HttpProxy:
        scheme = "Http"
    elif proxyType == QNetworkProxy.ProxyType.HttpCachingProxy:
        scheme = "Https"
    elif proxyType == QNetworkProxy.ProxyType.FtpCachingProxy:
        scheme = "Ftp"
    elif proxyType == QNetworkProxy.ProxyType.NoProxy:
        scheme = "NoProxy"
    return scheme


def proxyAuthenticationRequired(proxy, auth):
    """
    Module slot to handle a proxy authentication request.

    @param proxy reference to the proxy object
    @type QNetworkProxy
    @param auth reference to the authenticator object
    @type QAuthenticator
    """
    from eric7.EricWidgets.EricAuthenticationDialog import EricAuthenticationDialog

    info = QCoreApplication.translate(
        "EricNetworkProxyFactory", "<b>Connect to proxy '{0}' using:</b>"
    ).format(EricUtilities.html_encode(proxy.hostName()))

    dlg = EricAuthenticationDialog(info, proxy.user(), True)
    dlg.setData(proxy.user(), proxy.password())
    if dlg.exec() == QDialog.DialogCode.Accepted:
        username, password = dlg.getData()
        auth.setUser(username)
        auth.setPassword(password)
        if dlg.shallSave():
            scheme = schemeFromProxyType(proxy.type())
            if scheme and scheme != "NoProxy":
                EricPreferences.setNetworkProxy(
                    "ProxyUser/{0}".format(scheme), username
                )
                EricPreferences.setNetworkProxy(
                    "ProxyPassword/{0}".format(scheme), password
                )
            proxy.setUser(username)
            proxy.setPassword(password)


class HostnameMatcher:
    """
    Class implementing a matcher for host names.
    """

    def __init__(self, pattern):
        """
        Constructor

        @param pattern pattern to be matched against
        @type str
        """
        self.__regExp = None
        self.setPattern(pattern)

    def setPattern(self, pattern):
        """
        Public method to set the match pattern.

        @param pattern pattern to be matched against
        @type str
        """
        self.__pattern = pattern

        if "?" in pattern or "*" in pattern:
            regexp = "^.*{0}.*$".format(
                pattern.replace(".", "\\.").replace("*", ".*").replace("?", ".")
            )
            self.__regExp = re.compile(regexp, re.IGNORECASE)

    def pattern(self):
        """
        Public method to get the match pattern.

        @return match pattern
        @rtype str
        """
        return self.__pattern

    def match(self, host):
        """
        Public method to test the given string.

        @param host host name to be matched
        @type str
        @return flag indicating a successful match
        @rtype bool
        """
        if self.__regExp is None:
            return self.__pattern in host

        return self.__regExp.search(host) is not None


class EricNetworkProxyFactory(QNetworkProxyFactory):
    """
    Class implementing a network proxy factory.
    """

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.__hostnameMatchers = []
        self.__exceptions = ""

    def __setExceptions(self, exceptions):
        """
        Private method to set the host name exceptions.

        @param exceptions list of exceptions separated by ','
        @type str
        """
        self.__hostnameMatchers = []
        self.__exceptions = exceptions
        for exception in self.__exceptions.split(","):
            self.__hostnameMatchers.append(HostnameMatcher(exception.strip()))

    def queryProxy(self, query):
        """
        Public method to determine a proxy for a given query.

        @param query reference to the query object
        @type QNetworkProxyQuery
        @return list of proxies in order of preference
        @rtype list of QNetworkProxy
        """
        # use proxy at all?
        if not EricPreferences.getNetworkProxy("UseProxy"):
            return [QNetworkProxy(QNetworkProxy.ProxyType.NoProxy)]

        elif (
            query.queryType() == QNetworkProxyQuery.QueryType.UrlRequest
            and query.protocolTag() in ["http", "https", "ftp"]
        ):
            # test for exceptions
            exceptions = EricPreferences.getNetworkProxy("ProxyExceptions")
            if exceptions != self.__exceptions:
                self.__setExceptions(exceptions)
            urlHost = query.url().host()
            for matcher in self.__hostnameMatchers:
                if matcher.match(urlHost):
                    return [QNetworkProxy(QNetworkProxy.ProxyType.NoProxy)]

            # determine proxy
            if EricPreferences.getNetworkProxy("UseSystemProxy"):
                proxyList = QNetworkProxyFactory.systemProxyForQuery(query)
                if (
                    not OSUtilities.isWindowsPlatform()
                    and len(proxyList) == 1
                    and proxyList[0].type() == QNetworkProxy.ProxyType.NoProxy
                ):
                    # try it the Python way
                    # scan the environment for variables named <scheme>_proxy
                    # scan over whole environment to make this case insensitive
                    for name, value in os.environ.items():
                        name = name.lower()
                        if (
                            value
                            and name[-6:] == "_proxy"
                            and name[:-6] == query.protocolTag().lower()
                        ):
                            url = QUrl(value)
                            if url.scheme() in ["http", "https"]:
                                proxyType = QNetworkProxy.ProxyType.HttpProxy
                            elif url.scheme() == "ftp":
                                proxyType = QNetworkProxy.ProxyType.FtpCachingProxy
                            else:
                                proxyType = QNetworkProxy.ProxyType.HttpProxy
                            proxy = QNetworkProxy(
                                proxyType,
                                url.host(),
                                url.port(),
                                url.userName(),
                                url.password(),
                            )
                            proxyList = [proxy]
                            break
                if proxyList:
                    scheme = schemeFromProxyType(proxyList[0].type())
                    if scheme == "":
                        scheme = "Http"
                    if scheme != "NoProxy":
                        proxyList[0].setUser(
                            EricPreferences.getNetworkProxy(
                                "ProxyUser/{0}".format(scheme)
                            )
                        )
                        proxyList[0].setPassword(
                            EricPreferences.getNetworkProxy(
                                "ProxyPassword/{0}".format(scheme)
                            )
                        )
                    return proxyList
                else:
                    return [QNetworkProxy(QNetworkProxy.ProxyType.NoProxy)]
            else:
                if EricPreferences.getNetworkProxy("UseHttpProxyForAll"):
                    protocolKey = "Http"
                else:
                    protocolKey = query.protocolTag().capitalize()
                host = EricPreferences.getNetworkProxy(
                    "ProxyHost/{0}".format(protocolKey)
                )
                if not host:
                    EricMessageBox.critical(
                        None,
                        QCoreApplication.translate(
                            "EricNetworkProxyFactory", "Proxy Configuration Error"
                        ),
                        QCoreApplication.translate(
                            "EricNetworkProxyFactory",
                            """Proxy usage was activated"""
                            """ but no proxy host for protocol"""
                            """ '{0}' configured.""",
                        ).format(protocolKey),
                    )
                    return [QNetworkProxy(QNetworkProxy.ProxyType.DefaultProxy)]
                else:
                    if protocolKey in ["Http", "Https", "Ftp"]:
                        if query.protocolTag() == "ftp":
                            proxyType = QNetworkProxy.ProxyType.FtpCachingProxy
                        else:
                            proxyType = QNetworkProxy.ProxyType.HttpProxy
                        proxy = QNetworkProxy(
                            proxyType,
                            host,
                            EricPreferences.getNetworkProxy("ProxyPort/" + protocolKey),
                            EricPreferences.getNetworkProxy("ProxyUser/" + protocolKey),
                            EricPreferences.getNetworkProxy(
                                "ProxyPassword/" + protocolKey
                            ),
                        )
                    else:
                        proxy = QNetworkProxy(QNetworkProxy.ProxyType.DefaultProxy)
                    return [proxy, QNetworkProxy(QNetworkProxy.ProxyType.DefaultProxy)]

        else:
            return [QNetworkProxy(QNetworkProxy.ProxyType.NoProxy)]
