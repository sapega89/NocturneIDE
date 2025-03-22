# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to handle URL requests before they get processed
by QtWebEngine.
"""

from PyQt6.QtCore import QMutex, QUrl
from PyQt6.QtWebEngineCore import (
    QWebEngineUrlRequestInfo,
    QWebEngineUrlRequestInterceptor,
)

from eric7 import Preferences
from eric7.EricUtilities.EricMutexLocker import EricMutexLocker

from ..WebBrowserPage import WebBrowserPage


class NetworkUrlInterceptor(QWebEngineUrlRequestInterceptor):
    """
    Class implementing an URL request handler.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__interceptors = []
        self.__mutex = QMutex()

        self.__loadSettings()

    def interceptRequest(self, info):
        """
        Public method handling an URL request.

        @param info URL request information
        @type QWebEngineUrlRequestInfo
        """
        with EricMutexLocker(self.__mutex):
            # Do Not Track feature
            if self.__doNotTrack:
                info.setHttpHeader(b"DNT", b"1")
                info.setHttpHeader(b"X-Do-Not-Track", b"1")

            # Send referrer header?
            if info.requestUrl().host() not in Preferences.getWebBrowser(
                "SendRefererWhitelist"
            ):
                self.__setRefererHeader(info)

            # User Agents header
            userAgent = WebBrowserPage.userAgentForUrl(info.requestUrl())
            info.setHttpHeader(b"User-Agent", userAgent.encode())

            for interceptor in self.__interceptors:
                interceptor.interceptRequest(info)

    def installUrlInterceptor(self, interceptor):
        """
        Public method to install an URL interceptor.

        @param interceptor URL interceptor to be installed
        @type UrlInterceptor
        """
        with EricMutexLocker(self.__mutex):
            if interceptor not in self.__interceptors:
                self.__interceptors.append(interceptor)

    def removeUrlInterceptor(self, interceptor):
        """
        Public method to remove an URL interceptor.

        @param interceptor URL interceptor to be removed
        @type UrlInterceptor
        """
        with EricMutexLocker(self.__mutex):
            if interceptor in self.__interceptors:
                self.__interceptors.remove(interceptor)

    def __loadSettings(self):
        """
        Private method to load the Network Manager settings.
        """
        with EricMutexLocker(self.__mutex):
            self.__doNotTrack = Preferences.getWebBrowser("DoNotTrack")
            self.__sendReferer = Preferences.getWebBrowser("RefererSendReferer")
            self.__refererDefaultPolicy = Preferences.getWebBrowser(
                "RefererDefaultPolicy"
            )
            self.__refererTrimmingPolicy = Preferences.getWebBrowser(
                "RefererTrimmingPolicy"
            )

    def preferencesChanged(self):
        """
        Public slot to handle a change of preferences.
        """
        self.__loadSettings()

    def __setRefererHeader(self, info):
        """
        Private method to set the 'Referer' header depending on the configured
        rule set.

        @param info URL request information
        @type QWebEngineUrlRequestInfo
        @see <a href="https://wiki.mozilla.org/Security/Referrer">
            Mozilla Referrer</a>
        @see <a href="https://www.w3.org/TR/referrer-policy/">
            W3C Referrer Policy</a>
        """
        # 1. SendReferer:
        #       0 = never
        #       1 = only on click (NavigationTypeLink)
        #       2 = always (default)
        # 2. RefererTrimmingPolicy:
        #       0 = send full URL (no trimming) (default)
        #       1 = send the URL without its query string
        #       2 = only send the origin (ensure trailing /)
        # 3. RefererDefaultPolicy:
        #   set the default referrer policy (which can be overriden by
        #   the site)
        #       0 = no-referrer
        #       1 = same-origin
        #       2 = strict-origin-when-cross-origin
        #       3 = no-referrer-when-downgrade (default)
        # see: https://wiki.mozilla.org/Security/Referrer
        # see: https://www.w3.org/TR/referrer-policy/

        if (
            self.__sendReferer == 0
            # never send referrer header
            or (
                self.__sendReferer == 1
                and (
                    info.navigationType()
                    != QWebEngineUrlRequestInfo.NavigationType.NavigationTypeLink
                )
            )
            # send referrer header only on click
        ):
            info.setHttpHeader(b"Referer", b"")
        else:
            # send referer header always applying further policies
            url = info.firstPartyUrl()
            reqUrl = info.requestUrl()
            if self.__refererDefaultPolicy == 0:
                # no-referrer
                refererUrl = b""
            elif self.__refererDefaultPolicy == 1:
                # same-origin
                if self.__sameOrigin(url, reqUrl):
                    refererUrl = self.__trimmedReferer(url)
                else:
                    refererUrl = b""
            elif self.__refererDefaultPolicy == 2:
                # strict-origin-when-cross-origin
                if self.__sameOrigin(url, reqUrl):
                    refererUrl = self.__trimmedReferer(url)
                elif url.scheme() in ("https", "wss"):
                    if self.__potentiallyTrustworthy(url):
                        refererUrl = self.__refererOrigin(url)
                    else:
                        refererUrl = b""
                else:
                    refererUrl = self.__refererOrigin(url)
            else:
                # no-referrer-when-downgrade
                if url.scheme() in (
                    "https",
                    "wss",
                ) and not self.__potentiallyTrustworthy(url):
                    refererUrl = b""
                else:
                    refererUrl = self.__trimmedReferer(url)

            info.setHttpHeader(b"Referer", refererUrl)

    def __sameOrigin(self, url1, url2):
        """
        Private method to test the "same origin" policy.

        @param url1 first URL for the test
        @type QUrl
        @param url2 second URL for the test
        @type QUrl
        @return flag indicating that both URLs have the same origin
        @rtype bool
        """
        origin1 = url1.url(
            QUrl.UrlFormattingOption.RemoveUserInfo
            | QUrl.UrlFormattingOption.RemovePath
        )
        origin2 = url2.url(
            QUrl.UrlFormattingOption.RemoveUserInfo
            | QUrl.UrlFormattingOption.RemovePath
        )

        return origin1 == origin2

    def __potentiallyTrustworthy(self, url):
        """
        Private method to check, if the given URL is potentially trustworthy.

        @param url URL to be checked
        @type QUrl
        @return flag indicating a potentially trustworthy URL
        @rtype bool
        """
        if url.scheme() == "data":
            return False

        if url.toString() in ("about:blank", "about:srcdoc"):
            return True

        origin = url.adjusted(
            QUrl.UrlFormattingOption.RemoveUserInfo
            | QUrl.UrlFormattingOption.RemovePath
        )

        if origin.isEmpty() or origin.scheme() == "":
            return False
        if origin.scheme() in ("https", "wss"):
            return True
        if origin.host().startswith("127.") or origin.host().endswith(":1"):
            return True
        if origin.host() == "localhost" or origin.host().endswith(".localhost"):
            return True
        if origin.scheme() == "file":
            return True
        if origin.scheme() in ("qrc", "qthelp", "eric"):
            return True

        return False

    def __trimmedReferer(self, url):
        """
        Private method to generate the trimmed referer header URL.

        @param url URL to be trimmed as a referer header
        @type QUrl
        @return trimmed referer header URL
        @rtype QByteArray or bytes
        """
        if self.__refererTrimmingPolicy == 0:
            # send full URL (no trimming) (default)
            refererUrl = url.toEncoded(
                QUrl.UrlFormattingOption.RemoveUserInfo
                | QUrl.UrlFormattingOption.RemoveFragment
            )
        elif self.__refererTrimmingPolicy == 1:
            # send the URL without its query string
            refererUrl = url.toEncoded(
                QUrl.UrlFormattingOption.RemoveUserInfo
                | QUrl.UrlFormattingOption.RemoveFragment
                | QUrl.UrlFormattingOption.RemoveQuery
            )
        else:
            # only send the origin (ensure trailing /)
            refererUrl = self.__refererOrigin(url)

        return refererUrl

    def __refererOrigin(self, url):
        """
        Private method to generate an origin referer header URL.

        @param url URL to generate the header from
        @type QUrl
        @return origin referer header URL
        @rtype QByteArray or bytes
        """
        referer = url.toEncoded(
            QUrl.UrlFormattingOption.RemoveUserInfo
            | QUrl.UrlFormattingOption.RemovePath
        )
        if not referer.endsWith(b"/"):
            referer += b"/"

        return referer
