# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing the helpbrowser using QWebView.
"""

import contextlib

from PyQt6.QtCore import (
    QCoreApplication,
    QEventLoop,
    QPoint,
    QTimer,
    QUrl,
    QUrlQuery,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineScript, QWebEngineSettings

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.SystemUtilities import QtUtilities
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .JavaScript.ExternalJsObject import ExternalJsObject
from .Tools import Scripts
from .Tools.WebHitTestResult import WebHitTestResult

try:
    from PyQt6.QtNetwork import QSslCertificate, QSslConfiguration

    from eric7.EricNetwork.EricSslInfoWidget import EricSslInfoWidget

    SSL_AVAILABLE = True
except ImportError:
    SSL_AVAILABLE = False

with contextlib.suppress(ImportError):
    from PyQt6.QtWebEngineCore import QWebEnginePermission


class WebBrowserPage(QWebEnginePage):
    """
    Class implementing an enhanced web page.

    @signal safeBrowsingAbort() emitted to indicate an abort due to a safe
        browsing event
    @signal safeBrowsingBad(threatType, threatMessages) emitted to indicate a
        malicious web site as determined by safe browsing
    @signal printPageRequested() emitted to indicate a print request of the
        shown web page
    @signal navigationRequestAccepted(url, navigation type, main frame) emitted
        to signal an accepted navigation request
    @signal sslConfigurationChanged() emitted to indicate a change of the
        stored SSL configuration data
    """

    SafeJsWorld = QWebEngineScript.ScriptWorldId.ApplicationWorld
    UnsafeJsWorld = QWebEngineScript.ScriptWorldId.MainWorld

    safeBrowsingAbort = pyqtSignal()
    safeBrowsingBad = pyqtSignal(str, str)

    printPageRequested = pyqtSignal()
    navigationRequestAccepted = pyqtSignal(QUrl, QWebEnginePage.NavigationType, bool)

    sslConfigurationChanged = pyqtSignal()

    if QtUtilities.qVersionTuple() >= (6, 8, 0):  # noqa: Y108
        PermissionTypeQuestions = {
            QWebEnginePermission.PermissionType.Geolocation: QCoreApplication.translate(
                "WebBrowserPage",
                "<p>Allow <b>{0}</b> to access your location information?</p>",
            ),
            QWebEnginePermission.PermissionType.MediaAudioCapture: (
                QCoreApplication.translate(
                    "WebBrowserPage",
                    "<p>Allow <b>{0}</b> to access your microphone?</p>",
                )
            ),
            QWebEnginePermission.PermissionType.MediaVideoCapture: (
                QCoreApplication.translate(
                    "WebBrowserPage",
                    "<p>Allow <b>{0}</b> to access your webcam?</p>",
                )
            ),
            QWebEnginePermission.PermissionType.MediaAudioVideoCapture: (
                QCoreApplication.translate(
                    "WebBrowserPage",
                    "<p>Allow <b>{0}</b> to access your microphone and webcam?</p>",
                )
            ),
            QWebEnginePermission.PermissionType.MouseLock: QCoreApplication.translate(
                "WebBrowserPage",
                "<p>Allow <b>{0}</b> to lock your mouse cursor?</p>",
            ),
            QWebEnginePermission.PermissionType.DesktopVideoCapture: (
                QCoreApplication.translate(
                    "WebBrowserPage",
                    "<p>Allow <b>{0}</b> to capture video of your desktop?</p>",
                )
            ),
            QWebEnginePermission.PermissionType.DesktopAudioVideoCapture: (
                QCoreApplication.translate(
                    "WebBrowserPage",
                    "<p>Allow <b>{0}</b> to capture audio and video of your"
                    " desktop?</p>",
                )
            ),
            QWebEnginePermission.PermissionType.Notifications: (
                QCoreApplication.translate(
                    "WebBrowserPage",
                    "<p>Allow <b>{0}</b> to show notifications on your desktop?</p>",
                )
            ),
            QWebEnginePermission.PermissionType.ClipboardReadWrite: (
                QCoreApplication.translate(
                    "WebBrowserPage",
                    "<p>Allow <b>{0}</b> to read from and write to the clipboard?</p>",
                )
            ),
            QWebEnginePermission.PermissionType.LocalFontsAccess: (
                QCoreApplication.translate(
                    "WebBrowserPage",
                    "<p>Allow <b>{0}</b> to access fonts stored on this machine?</p>",
                )
            ),
        }
    else:
        PermissionTypeQuestions = {}

    def __init__(self, view, parent=None):
        """
        Constructor

        @param view reference to the WebBrowserView associated with the page
        @type WebBrowserView
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(WebBrowserWindow.webProfile(), parent)

        self.__printer = None
        self.__badSite = False

        self.__view = view

        try:
            # Qt 6.8+
            self.permissionRequested.connect(self.__permissionRequested)
        except AttributeError:
            # Qt <6.8
            self.featurePermissionRequested.connect(self.__featurePermissionRequested)
        self.authenticationRequired.connect(
            lambda url, auth: WebBrowserWindow.networkManager().authentication(
                url, auth, self
            )
        )
        self.proxyAuthenticationRequired.connect(
            WebBrowserWindow.networkManager().proxyAuthentication
        )
        self.fullScreenRequested.connect(self.__fullScreenRequested)
        self.urlChanged.connect(self.__urlChanged)
        self.contentsSizeChanged.connect(self.__contentsSizeChanged)
        self.registerProtocolHandlerRequested.connect(
            self.__registerProtocolHandlerRequested
        )

        self.__sslConfiguration = None

        # Workaround for changing webchannel world inside
        # acceptNavigationRequest not working
        self.__channelUrl = QUrl()
        self.__channelWorldId = -1
        self.__setupChannelTimer = QTimer(self)
        self.__setupChannelTimer.setSingleShot(True)
        self.__setupChannelTimer.setInterval(100)
        self.__setupChannelTimer.timeout.connect(self.__setupChannelTimeout)

    def view(self):
        """
        Public method to get a reference to the WebBrowserView associated with
        the page.

        @return reference to the WebBrowserView associated with the page
        @rtype WebBrowserView
        """
        return self.__view

    @pyqtSlot()
    def __setupChannelTimeout(self):
        """
        Private slot to initiate the setup of the web channel.
        """
        self.__setupWebChannelForUrl(self.__channelUrl)

    def acceptNavigationRequest(self, url, type_, isMainFrame):
        """
        Public method to determine, if a request may be accepted.

        @param url URL to navigate to
        @type QUrl
        @param type_ type of the navigation request
        @type QWebEnginePage.NavigationType
        @param isMainFrame flag indicating, that the request originated from
            the main frame
        @type bool
        @return flag indicating acceptance
        @rtype bool
        """
        from eric7.WebBrowser.SafeBrowsing.SafeBrowsingManager import (
            SafeBrowsingManager,
        )

        scheme = url.scheme()
        if scheme == "mailto":
            QDesktopServices.openUrl(url)
            return False

        # AdBlock
        if (
            url.scheme() == "abp"
            and WebBrowserWindow.adBlockManager().addSubscriptionFromUrl(url)
        ):
            return False

        # GreaseMonkey
        navigationType = type_ in (
            QWebEnginePage.NavigationType.NavigationTypeLinkClicked,
            QWebEnginePage.NavigationType.NavigationTypeRedirect,
        )
        if navigationType and url.toString().endswith(".user.js"):
            WebBrowserWindow.greaseMonkeyManager().downloadScript(url)
            return False

        if url.scheme() == "eric":
            if url.path() == "AddSearchProvider":
                query = QUrlQuery(url)
                self.__view.mainWindow().openSearchManager().addEngine(
                    QUrl(query.queryItemValue("url"))
                )
                return False
            elif url.path() == "PrintPage":
                self.printPageRequested.emit()
                return False

        # Safe Browsing
        self.__badSite = False
        if (
            SafeBrowsingManager.isEnabled()
            and url.scheme() not in SafeBrowsingManager.getIgnoreSchemes()
        ):
            threatLists = WebBrowserWindow.safeBrowsingManager().lookupUrl(url)[0]
            if threatLists:
                threatMessages = (
                    WebBrowserWindow.safeBrowsingManager().getThreatMessages(
                        threatLists
                    )
                )
                res = EricMessageBox.warning(
                    WebBrowserWindow.getWindow(),
                    self.tr("Suspicuous URL detected"),
                    self.tr(
                        "<p>The URL <b>{0}</b> was found in the Safe"
                        " Browsing database.</p>{1}"
                    ).format(url.toString(), "".join(threatMessages)),
                    EricMessageBox.Abort | EricMessageBox.Ignore,
                    EricMessageBox.Abort,
                )
                if res == EricMessageBox.Abort:
                    self.safeBrowsingAbort.emit()
                    return False

                self.__badSite = True
                threatType = WebBrowserWindow.safeBrowsingManager().getThreatType(
                    threatLists[0]
                )
                self.safeBrowsingBad.emit(threatType, "".join(threatMessages))

        result = QWebEnginePage.acceptNavigationRequest(self, url, type_, isMainFrame)

        if result:
            if isMainFrame:
                isWeb = url.scheme() in ("http", "https", "ftp", "ftps", "file")
                globalJsEnabled = WebBrowserWindow.webSettings().testAttribute(
                    QWebEngineSettings.WebAttribute.JavascriptEnabled
                )
                if isWeb:
                    enable = globalJsEnabled
                else:
                    enable = True
                self.settings().setAttribute(
                    QWebEngineSettings.WebAttribute.JavascriptEnabled, enable
                )

                self.__channelUrl = url
                self.__setupChannelTimer.start()
            self.navigationRequestAccepted.emit(url, type_, isMainFrame)

        return result

    @pyqtSlot(QUrl)
    def __urlChanged(self, url):
        """
        Private slot to handle changes of the URL.

        @param url new URL
        @type QUrl
        """
        if (
            not url.isEmpty()
            and url.scheme() == "eric"
            and not self.isJavaScriptEnabled()
        ):
            self.settings().setAttribute(
                QWebEngineSettings.WebAttribute.JavascriptEnabled, True
            )
            self.triggerAction(QWebEnginePage.WebAction.Reload)

    @classmethod
    def userAgent(cls, resolveEmpty=False):
        """
        Class method to get the global user agent setting.

        @param resolveEmpty flag indicating to resolve an empty
            user agent
        @type bool
        @return user agent string
        @rtype str
        """
        agent = Preferences.getWebBrowser("UserAgent")
        if agent == "" and resolveEmpty:
            agent = cls.userAgentForUrl(QUrl())
        return agent

    @classmethod
    def setUserAgent(cls, agent):
        """
        Class method to set the global user agent string.

        @param agent new current user agent string
        @type str
        """
        Preferences.setWebBrowser("UserAgent", agent)

    @classmethod
    def userAgentForUrl(cls, url):
        """
        Class method to determine the user agent for the given URL.

        @param url URL to determine user agent for
        @type QUrl
        @return user agent string
        @rtype str
        """
        agent = WebBrowserWindow.userAgentsManager().userAgentForUrl(url)
        if agent == "":
            # no agent string specified for the given host -> use global one
            agent = Preferences.getWebBrowser("UserAgent")
            if agent == "":
                # no global agent string specified -> use default one
                agent = WebBrowserWindow.webProfile().httpUserAgent()
        return agent

    def __featurePermissionRequested(self, url, feature):
        """
        Private slot handling a feature permission request.

        @param url url requesting the feature
        @type QUrl
        @param feature requested feature
        @type QWebEnginePage.Feature
        """
        # Qt <6.8
        manager = WebBrowserWindow.featurePermissionManager()
        manager.requestFeaturePermission(self, url, feature)

    def __permissionRequested(self, permission):
        """
        Private slot handling a permission request.

        @param permission reference to the permission request object
        @type QWebEnginePermission
        """
        # Qt 6.8+
        question = self.PermissionTypeQuestions.get(permission.permissionType())
        if question and EricMessageBox.yesNo(
            self.view(),
            self.tr("Permission Request"),
            question.format(permission.origin().host()),
            yesDefault=True,
        ):
            permission.grant()
        else:
            permission.deny()

    def execJavaScript(
        self, script, worldId=QWebEngineScript.ScriptWorldId.MainWorld, timeout=500
    ):
        """
        Public method to execute a JavaScript function synchronously.

        @param script JavaScript script source to be executed
        @type str
        @param worldId ID to run the script under
        @type QWebEngineScript.ScriptWorldId
        @param timeout max. time the script is given to execute
        @type int
        @return result of the script
        @rtype depending upon script result
        """
        loop = QEventLoop()
        resultDict = {"res": None}
        QTimer.singleShot(timeout, loop.quit)

        def resultCallback(res, resDict=resultDict):
            if loop and loop.isRunning():
                resDict["res"] = res
                loop.quit()

        self.runJavaScript(script, worldId, resultCallback)

        loop.exec()
        return resultDict["res"]

    def runJavaScript(self, script, worldId=-1, callback=None):
        """
        Public method to run a script in the context of the page.

        @param script JavaScript script source to be executed
        @type str
        @param worldId ID to run the script under
        @type int
        @param callback callback function to be executed when the script has
            ended
        @type function
        """
        if worldId > -1:
            if callback is None:
                QWebEnginePage.runJavaScript(self, script, worldId)
            else:
                QWebEnginePage.runJavaScript(self, script, worldId, callback)
        else:
            if callback is None:
                QWebEnginePage.runJavaScript(self, script)
            else:
                QWebEnginePage.runJavaScript(self, script, callback)

    def isJavaScriptEnabled(self):
        """
        Public method to test, if JavaScript is enabled.

        @return flag indicating the state of the JavaScript support
        @rtype bool
        """
        return self.settings().testAttribute(
            QWebEngineSettings.WebAttribute.JavascriptEnabled
        )

    def scroll(self, x, y):
        """
        Public method to scroll by the given amount of pixels.

        @param x horizontal scroll value
        @type int
        @param y vertical scroll value
        @type int
        """
        self.runJavaScript(
            "window.scrollTo(window.scrollX + {0}, window.scrollY + {1})".format(x, y),
            WebBrowserPage.SafeJsWorld,
        )

    def scrollTo(self, pos):
        """
        Public method to scroll to the given position.

        @param pos position to scroll to
        @type QPointF
        """
        self.runJavaScript(
            "window.scrollTo({0}, {1});".format(pos.x(), pos.y()),
            WebBrowserPage.SafeJsWorld,
        )

    def mapToViewport(self, pos):
        """
        Public method to map a position to the viewport.

        @param pos position to be mapped
        @type QPoint
        @return viewport position
        @rtype QPoint
        """
        return QPoint(
            int(pos.x() // self.zoomFactor()), int(pos.y() // self.zoomFactor())
        )

    def hitTestContent(self, pos):
        """
        Public method to test the content at a specified position.

        @param pos position to execute the test at
        @type QPoint
        @return test result object
        @rtype WebHitTestResult
        """
        return WebHitTestResult(self, pos)

    def __setupWebChannelForUrl(self, url):
        """
        Private method to setup a web channel to our external object.

        @param url URL for which to setup the web channel
        @type QUrl
        """
        channel = self.webChannel()
        if channel is None:
            channel = QWebChannel(self)
            ExternalJsObject.setupWebChannel(channel, self)

        worldId = -1
        worldId = (
            self.UnsafeJsWorld
            if url.scheme() in ("eric", "qthelp")
            else self.SafeJsWorld
        )
        if worldId != self.__channelWorldId:
            self.__channelWorldId = worldId
            self.setWebChannel(channel, self.__channelWorldId)

    def certificateError(self, error):
        """
        Public method to handle SSL certificate errors.

        @param error object containing the certificate error information
        @type QWebEngineCertificateError
        @return flag indicating to ignore this error
        @rtype bool
        """
        return WebBrowserWindow.networkManager().certificateError(error, self.__view)

    def __fullScreenRequested(self, request):
        """
        Private slot handling a full screen request.

        @param request reference to the full screen request
        @type QWebEngineFullScreenRequest
        """
        self.__view.requestFullScreen(request.toggleOn())

        accepted = request.toggleOn() == self.__view.isFullScreen()

        if accepted:
            request.accept()
        else:
            request.reject()

    def __contentsSizeChanged(self, _size):
        """
        Private slot to work around QWebEnginePage not scrolling to anchors
        when opened in a background tab.

        @param _size changed contents size (unused) (unused)
        @type QSizeF
        """
        fragment = self.url().fragment()
        self.runJavaScript(Scripts.scrollToAnchor(fragment))

    ##############################################
    ## Methods below deal with JavaScript messages
    ##############################################

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceId):
        """
        Public method to show a console message.

        @param level severity
        @type QWebEnginePage.JavaScriptConsoleMessageLevel
        @param message message to be shown
        @type str
        @param lineNumber line number of an error
        @type int
        @param sourceId source URL causing the error
        @type str
        """
        self.__view.mainWindow().javascriptConsole().javaScriptConsoleMessage(
            level, message, lineNumber, sourceId
        )

    ###########################################################################
    ## Methods below implement safe browsing related functions
    ###########################################################################

    def getSafeBrowsingStatus(self):
        """
        Public method to get the safe browsing status of the current page.

        @return flag indicating a safe site
        @rtype bool
        """
        return not self.__badSite

    #############################################################
    ## Methods below implement protocol handler related functions
    #############################################################

    @pyqtSlot("QWebEngineRegisterProtocolHandlerRequest")
    def __registerProtocolHandlerRequested(self, request):
        """
        Private slot to handle the registration of a custom protocol
        handler.

        @param request reference to the registration request
        @type QWebEngineRegisterProtocolHandlerRequest
        """
        acceptRequest = Preferences.getWebBrowser("AcceptProtocolHandlerRequest")
        # map yes/no/ask from (0, 1, 2)
        if acceptRequest == 0:
            # always yes
            ok = True
        elif acceptRequest == 1:
            # always no
            ok = False
        else:
            # ask user
            ok = EricMessageBox.yesNo(
                self,
                self.tr("Register Protocol Handler"),
                self.tr(
                    "<p>Allow the Web Site <b>{0}</b> to handle all <b>{1}</b>"
                    " links?</p>"
                ).format(request.origin().host(), request.scheme()),
            )

        if ok:
            if self.url().host() == request.origin().host():
                url = request.origin()
                scheme = request.scheme()
            else:
                url = QUrl()
                scheme = ""
            WebBrowserWindow.protocolHandlerManager().addProtocolHandler(scheme, url)

        # always reject the original request
        request.reject()

    #############################################################
    ## SSL configuration handling below
    #############################################################

    def setSslConfiguration(self, sslConfiguration):
        """
        Public slot to set the SSL configuration data of the page.

        @param sslConfiguration SSL configuration to be set
        @type QSslConfiguration
        """
        self.__sslConfiguration = QSslConfiguration(sslConfiguration)
        self.__sslConfiguration.url = self.url()
        self.sslConfigurationChanged.emit()

    def getSslConfiguration(self):
        """
        Public method to return a reference to the current SSL configuration.

        @return reference to the SSL configuration in use
        @rtype QSslConfiguration
        """
        return self.__sslConfiguration

    def clearSslConfiguration(self):
        """
        Public slot to clear the stored SSL configuration data.
        """
        self.__sslConfiguration = None
        self.sslConfigurationChanged.emit()

    def getSslCertificate(self):
        """
        Public method to get a reference to the SSL certificate.

        @return amended SSL certificate
        @rtype QSslCertificate
        """
        if self.__sslConfiguration is None:
            return None

        sslCertificate = self.__sslConfiguration.peerCertificate()
        sslCertificate.url = QUrl(self.__sslConfiguration.url)
        return sslCertificate

    def getSslCertificateChain(self):
        """
        Public method to get a reference to the SSL certificate chain.

        @return SSL certificate chain
        @rtype list of QSslCertificate
        """
        if self.__sslConfiguration is None:
            return []

        chain = self.__sslConfiguration.peerCertificateChain()
        return chain

    def showSslInfo(self, pos):
        """
        Public slot to show some SSL information for the loaded page.

        @param pos position to show the info at
        @type QPoint
        """
        if SSL_AVAILABLE and self.__sslConfiguration is not None:
            widget = EricSslInfoWidget(self.url(), self.__sslConfiguration, self.__view)
            widget.showAt(pos)
        else:
            EricMessageBox.warning(
                self.__view,
                self.tr("SSL Info"),
                self.tr("""This site does not contain SSL information."""),
            )

    def hasValidSslInfo(self):
        """
        Public method to check, if the page has a valid SSL certificate.

        @return flag indicating a valid SSL certificate
        @rtype bool
        """
        if self.__sslConfiguration is None:
            return False

        certList = self.__sslConfiguration.peerCertificateChain()
        if not certList:
            return False

        certificateDict = EricUtilities.toDict(
            Preferences.getSettings().value("Ssl/CaCertificatesDict")
        )
        for server in certificateDict:
            localCAList = QSslCertificate.fromData(certificateDict[server])
            if any(cert in localCAList for cert in certList):
                return True

        return all(not cert.isBlacklisted() for cert in certList)
