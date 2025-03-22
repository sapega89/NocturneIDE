# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the AdBlock manager.
"""

import contextlib
import os

from PyQt6.QtCore import QByteArray, QMutex, QObject, QUrl, QUrlQuery, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInfo

from eric7 import EricUtilities, Preferences
from eric7.EricUtilities.EricMutexLocker import EricMutexLocker
from eric7.EricWidgets import EricMessageBox
from eric7.Utilities.AutoSaver import AutoSaver
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .AdBlockMatcher import AdBlockMatcher
from .AdBlockSubscription import AdBlockSubscription
from .AdBlockUrlInterceptor import AdBlockUrlInterceptor


class AdBlockManager(QObject):
    """
    Class implementing the AdBlock manager.

    @signal rulesChanged() emitted after some rule has changed
    @signal requiredSubscriptionLoaded(subscription) emitted to indicate
        loading of a required subscription is finished (AdBlockSubscription)
    @signal enabledChanged(enabled) emitted to indicate a change of the
        enabled state
    """

    rulesChanged = pyqtSignal()
    requiredSubscriptionLoaded = pyqtSignal(AdBlockSubscription)
    enabledChanged = pyqtSignal(bool)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__loaded = False
        self.__subscriptionsLoaded = False
        self.__enabled = False
        self.__adBlockDialog = None
        self.__adBlockExceptionsDialog = None
        self.__adBlockNetwork = None
        self.__adBlockPage = None
        self.__subscriptions = []
        self.__exceptedHosts = Preferences.getWebBrowser("AdBlockExceptions")
        self.__saveTimer = AutoSaver(self, self.save)
        self.__limitedEasyList = Preferences.getWebBrowser("AdBlockUseLimitedEasyList")

        self.__defaultSubscriptionUrlString = (
            "abp:subscribe?location="
            "https://easylist-downloads.adblockplus.org/easylist.txt&"
            "title=EasyList"
        )
        self.__additionalDefaultSubscriptionUrlStrings = (
            "abp:subscribe?location=https://raw.githubusercontent.com/"
            "hoshsadiq/adblock-nocoin-list/master/nocoin.txt&"
            "title=NoCoin",
        )
        self.__customSubscriptionUrlString = bytes(
            self.__customSubscriptionUrl().toEncoded()
        ).decode()

        self.__mutex = QMutex()
        self.__matcher = AdBlockMatcher(self)

        self.rulesChanged.connect(self.__saveTimer.changeOccurred)
        self.rulesChanged.connect(self.__rulesChanged)

        self.__interceptor = AdBlockUrlInterceptor(self)

        WebBrowserWindow.networkManager().installUrlInterceptor(self.__interceptor)

    def __rulesChanged(self):
        """
        Private slot handling a change of the AdBlock rules.
        """
        WebBrowserWindow.mainWindow().reloadUserStyleSheet()
        self.__updateMatcher()

    def close(self):
        """
        Public method to close the open search engines manager.
        """
        self.__adBlockDialog and self.__adBlockDialog.close()
        (self.__adBlockExceptionsDialog and self.__adBlockExceptionsDialog.close())

        self.__saveTimer.saveIfNeccessary()

    def isEnabled(self):
        """
        Public method to check, if blocking ads is enabled.

        @return flag indicating the enabled state
        @rtype bool
        """
        if not self.__loaded:
            self.load()

        return self.__enabled

    def setEnabled(self, enabled):
        """
        Public slot to set the enabled state.

        @param enabled flag indicating the enabled state
        @type bool
        """
        if self.isEnabled() == enabled:
            return

        self.__enabled = enabled
        for mainWindow in WebBrowserWindow.mainWindows():
            mainWindow.adBlockIcon().setEnabled(enabled)
        if enabled:
            self.__loadSubscriptions()

        self.rulesChanged.emit()
        self.enabledChanged.emit(enabled)

    def block(self, info):
        """
        Public method to check, if a request should be blocked.

        @param info request info object
        @type QWebEngineUrlRequestInfo
        @return flag indicating to block the request
        @rtype bool
        """
        with EricMutexLocker(self.__mutex):
            if not self.isEnabled():
                return False

            urlString = bytes(info.requestUrl().toEncoded()).decode().lower()
            urlDomain = info.requestUrl().host().lower()
            urlScheme = info.requestUrl().scheme().lower()

            if not self.canRunOnScheme(urlScheme) or not self.__canBeBlocked(
                info.firstPartyUrl()
            ):
                return False

            res = False
            blockedRule = self.__matcher.match(info, urlDomain, urlString)

            if blockedRule:
                res = True
                if (
                    info.resourceType()
                    == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMainFrame
                ):
                    url = QUrl("eric:adblock")
                    query = QUrlQuery()
                    query.addQueryItem("rule", blockedRule.filter())
                    query.addQueryItem(
                        "subscription", blockedRule.subscription().title()
                    )
                    url.setQuery(query)
                    info.redirect(url)
                else:
                    info.block(True)

            return res

    def canRunOnScheme(self, scheme):
        """
        Public method to check, if AdBlock can be performed on the scheme.

        @param scheme scheme to check
        @type str
        @return flag indicating, that AdBlock can be performed
        @rtype bool
        """
        return scheme not in ["data", "eric", "qthelp", "qrc", "file", "abp"]

    def page(self):
        """
        Public method to get a reference to the page block object.

        @return reference to the page block object
        @rtype AdBlockPage
        """
        from .AdBlockPage import AdBlockPage

        if self.__adBlockPage is None:
            self.__adBlockPage = AdBlockPage(self)
        return self.__adBlockPage

    def __customSubscriptionLocation(self):
        """
        Private method to generate the path for custom subscriptions.

        @return URL for custom subscriptions
        @rtype QUrl
        """
        dataDir = os.path.join(
            EricUtilities.getConfigDir(), "web_browser", "subscriptions"
        )
        if not os.path.exists(dataDir):
            os.makedirs(dataDir)
        fileName = os.path.join(dataDir, "adblock_subscription_custom")
        return QUrl.fromLocalFile(fileName)

    def __customSubscriptionUrl(self):
        """
        Private method to generate the URL for custom subscriptions.

        @return URL for custom subscriptions
        @rtype QUrl
        """
        location = self.__customSubscriptionLocation()
        encodedUrl = bytes(location.toEncoded()).decode()
        url = QUrl(
            "abp:subscribe?location={0}&title={1}".format(
                encodedUrl, self.tr("Custom Rules")
            )
        )
        return url

    def customRules(self):
        """
        Public method to get a subscription for custom rules.

        @return subscription object for custom rules
        @rtype AdBlockSubscription
        """
        location = self.__customSubscriptionLocation()
        for subscription in self.__subscriptions:
            if subscription.location() == location:
                return subscription

        url = self.__customSubscriptionUrl()
        customAdBlockSubscription = AdBlockSubscription(url, True, self)
        self.addSubscription(customAdBlockSubscription)
        return customAdBlockSubscription

    def subscriptions(self):
        """
        Public method to get all subscriptions.

        @return list of subscriptions
        @rtype list of AdBlockSubscription
        """
        if not self.__loaded:
            self.load()

        return self.__subscriptions[:]

    def subscription(self, location):
        """
        Public method to get a subscription based on its location.

        @param location location of the subscription to search for
        @type str
        @return subscription or None
        @rtype AdBlockSubscription
        """
        if location != "":
            for subscription in self.__subscriptions:
                if subscription.location().toString() == location:
                    return subscription

        return None

    def updateAllSubscriptions(self):
        """
        Public method to update all subscriptions.
        """
        for subscription in self.__subscriptions:
            subscription.updateNow()

    def removeSubscription(self, subscription, emitSignal=True):
        """
        Public method to remove an AdBlock subscription.

        @param subscription AdBlock subscription to be removed
        @type AdBlockSubscription
        @param emitSignal flag indicating to send a signal
        @type bool
        """
        if subscription is None:
            return

        if (
            subscription.url()
            .toString()
            .startswith(
                (
                    self.__defaultSubscriptionUrlString,
                    self.__customSubscriptionUrlString,
                )
            )
        ):
            return

        with contextlib.suppress(ValueError):
            self.__subscriptions.remove(subscription)
            rulesFileName = subscription.rulesFileName()
            os.unlink(rulesFileName)
            requiresSubscriptions = self.getRequiresSubscriptions(subscription)
            for requiresSubscription in requiresSubscriptions:
                self.removeSubscription(requiresSubscription, False)
            if emitSignal:
                self.rulesChanged.emit()

    def addSubscriptionFromUrl(self, url):
        """
        Public method to ad an AdBlock subscription given the abp URL.

        @param url URL to subscribe an AdBlock subscription
        @type QUrl
        @return flag indicating success
        @rtype bool
        """
        from .AdBlockSubscription import AdBlockSubscription

        if url.path() != "subscribe":
            return False

        title = QUrl.fromPercentEncoding(
            QByteArray(QUrlQuery(url).queryItemValue("title").encode())
        )
        if not title:
            return False

        res = EricMessageBox.yesNo(
            None,
            self.tr("Subscribe?"),
            self.tr(
                """<p>Subscribe to this AdBlock subscription?</p><p>{0}</p>"""
            ).format(title),
        )
        if res:
            dlg = WebBrowserWindow.adBlockManager().showDialog()
            subscription = AdBlockSubscription(
                url, False, WebBrowserWindow.adBlockManager()
            )
            WebBrowserWindow.adBlockManager().addSubscription(subscription)
            dlg.addSubscription(subscription, False)
            dlg.setFocus()
            dlg.raise_()

        return res

    def addSubscription(self, subscription):
        """
        Public method to add an AdBlock subscription.

        @param subscription AdBlock subscription to be added
        @type AdBlockSubscription
        """
        if subscription is None:
            return

        self.__subscriptions.insert(-1, subscription)

        subscription.rulesChanged.connect(self.rulesChanged)
        subscription.changed.connect(self.rulesChanged)
        subscription.enabledChanged.connect(self.rulesChanged)

        self.rulesChanged.emit()

    def save(self):
        """
        Public method to save the AdBlock subscriptions.
        """
        if not self.__loaded:
            return

        Preferences.setWebBrowser("AdBlockEnabled", self.__enabled)
        if self.__subscriptionsLoaded:
            subscriptions = []
            requiresSubscriptions = []
            # intermediate store for subscription requiring others
            for subscription in self.__subscriptions:
                if subscription is None:
                    continue
                urlString = bytes(subscription.url().toEncoded()).decode()
                if "requiresLocation" in urlString:
                    requiresSubscriptions.append(urlString)
                else:
                    subscriptions.append(urlString)
                subscription.saveRules()
            for subscription in requiresSubscriptions:
                subscriptions.insert(-1, subscription)  # custom should be last
            Preferences.setWebBrowser("AdBlockSubscriptions", subscriptions)

    def load(self):
        """
        Public method to load the AdBlock subscriptions.
        """
        if self.__loaded:
            return

        self.__loaded = True

        self.__enabled = Preferences.getWebBrowser("AdBlockEnabled")
        if self.__enabled:
            self.__loadSubscriptions()

    def __loadSubscriptions(self):
        """
        Private method to load the set of subscriptions.
        """
        if self.__subscriptionsLoaded:
            return

        subscriptions = Preferences.getWebBrowser("AdBlockSubscriptions")
        if subscriptions:
            for subscription in subscriptions:
                if subscription.startswith(self.__customSubscriptionUrlString):
                    break
            else:
                subscriptions.append(self.__customSubscriptionUrlString)
        else:
            subscriptions = (
                [self.__defaultSubscriptionUrlString]
                + list(self.__additionalDefaultSubscriptionUrlStrings)
                + [self.__customSubscriptionUrlString]
            )
        for subscription in subscriptions:
            url = QUrl.fromEncoded(subscription.encode("utf-8"))
            adBlockSubscription = AdBlockSubscription(
                url,
                subscription.startswith(self.__customSubscriptionUrlString),
                self,
                subscription.startswith(self.__defaultSubscriptionUrlString),
            )
            adBlockSubscription.rulesChanged.connect(self.rulesChanged)
            adBlockSubscription.changed.connect(self.rulesChanged)
            adBlockSubscription.enabledChanged.connect(self.rulesChanged)
            adBlockSubscription.rulesEnabledChanged.connect(self.__updateMatcher)
            adBlockSubscription.rulesEnabledChanged.connect(
                self.__saveTimer.changeOccurred
            )
            self.__subscriptions.append(adBlockSubscription)

        self.__subscriptionsLoaded = True

        self.__updateMatcher()

    def loadRequiredSubscription(self, location, title):
        """
        Public method to load a subscription required by another one.

        @param location location of the required subscription
        @type str
        @param title title of the required subscription
        @type str
        """
        # Step 1: check, if the subscription is in the list of subscriptions
        urlString = "abp:subscribe?location={0}&title={1}".format(location, title)
        for subscription in self.__subscriptions:
            if subscription.url().toString().startswith(urlString):
                # We found it!
                return

        # Step 2: if it is not, get it
        url = QUrl.fromEncoded(urlString.encode("utf-8"))
        adBlockSubscription = AdBlockSubscription(url, False, self)
        self.addSubscription(adBlockSubscription)
        self.requiredSubscriptionLoaded.emit(adBlockSubscription)

    def getRequiresSubscriptions(self, subscription):
        """
        Public method to get a list of subscriptions, that require the given
        one.

        @param subscription subscription to check for
        @type AdBlockSubscription
        @return list of subscription requiring the given one
        @rtype list of AdBlockSubscription
        """
        subscriptions = []
        location = subscription.location().toString()
        for subscription in self.__subscriptions:
            if subscription.requiresLocation() == location:
                subscriptions.append(subscription)

        return subscriptions

    def showDialog(self, parent=None):
        """
        Public slot to show the AdBlock subscription management dialog.

        @param parent reference to the parent widget
        @type QWidget
        @return reference to the dialog
        @rtype AdBlockDialog
        """
        from .AdBlockDialog import AdBlockDialog

        if self.__adBlockDialog is None:
            self.__adBlockDialog = AdBlockDialog(self, parent=parent)

        self.__adBlockDialog.show()
        return self.__adBlockDialog

    def elementHidingRules(self, url):
        """
        Public method to get the element hiding rules.


        @param url URL to get hiding rules for
        @type QUrl
        @return element hiding rules
        @rtype str
        """
        if (
            not self.isEnabled()
            or not self.canRunOnScheme(url.scheme())
            or not self.__canBeBlocked(url)
        ):
            return ""

        return self.__matcher.elementHidingRules()

    def elementHidingRulesForDomain(self, url):
        """
        Public method to get the element hiding rules for a domain.

        @param url URL to get hiding rules for
        @type QUrl
        @return element hiding rules
        @rtype str
        """
        if (
            not self.isEnabled()
            or not self.canRunOnScheme(url.scheme())
            or not self.__canBeBlocked(url)
        ):
            return ""

        return self.__matcher.elementHidingRulesForDomain(url.host())

    def exceptions(self):
        """
        Public method to get a list of excepted hosts.

        @return list of excepted hosts
        @rtype list of str
        """
        return self.__exceptedHosts

    def setExceptions(self, hosts):
        """
        Public method to set the list of excepted hosts.

        @param hosts list of excepted hosts
        @type list of str
        """
        self.__exceptedHosts = [host.lower() for host in hosts]
        Preferences.setWebBrowser("AdBlockExceptions", self.__exceptedHosts)

    def addException(self, host):
        """
        Public method to add an exception.

        @param host to be excepted
        @type str
        """
        host = host.lower()
        if host and host not in self.__exceptedHosts:
            self.__exceptedHosts.append(host)
            Preferences.setWebBrowser("AdBlockExceptions", self.__exceptedHosts)

    def removeException(self, host):
        """
        Public method to remove an exception.

        @param host to be removed from the list of exceptions
        @type str
        """
        host = host.lower()
        if host in self.__exceptedHosts:
            self.__exceptedHosts.remove(host)
            Preferences.setWebBrowser("AdBlockExceptions", self.__exceptedHosts)

    def isHostExcepted(self, host):
        """
        Public slot to check, if a host is excepted.

        @param host host to check
        @type str
        @return flag indicating an exception
        @rtype bool
        """
        host = host.lower()
        return host in self.__exceptedHosts

    def showExceptionsDialog(self):
        """
        Public method to show the AdBlock Exceptions dialog.

        @return reference to the exceptions dialog
        @rtype AdBlockExceptionsDialog
        """
        from .AdBlockExceptionsDialog import AdBlockExceptionsDialog

        if self.__adBlockExceptionsDialog is None:
            self.__adBlockExceptionsDialog = AdBlockExceptionsDialog()

        self.__adBlockExceptionsDialog.load(self.__exceptedHosts)
        self.__adBlockExceptionsDialog.show()
        return self.__adBlockExceptionsDialog

    def useLimitedEasyList(self):
        """
        Public method to test, if limited EasyList rules shall be used.

        @return flag indicating limited EasyList rules
        @rtype bool
        """
        return self.__limitedEasyList

    def setUseLimitedEasyList(self, limited):
        """
        Public method to set the limited EasyList flag.

        @param limited flag indicating to use limited EasyList
        @type bool
        """
        self.__limitedEasyList = limited

        for subscription in self.__subscriptions:
            if (
                subscription.url()
                .toString()
                .startswith(self.__defaultSubscriptionUrlString)
            ):
                subscription.updateNow()

        Preferences.setWebBrowser("AdBlockUseLimitedEasyList", limited)

    def getDefaultSubscriptionUrl(self):
        """
        Public method to get the default subscription URL.

        @return default subscription URL
        @rtype str
        """
        return self.__defaultSubscriptionUrlString

    def __updateMatcher(self):
        """
        Private slot to update the adblock matcher.
        """
        WebBrowserWindow.networkManager().removeUrlInterceptor(self.__interceptor)

        if self.__enabled:
            self.__matcher.update()
        else:
            self.__matcher.clear()

        WebBrowserWindow.networkManager().installUrlInterceptor(self.__interceptor)

    def __canBeBlocked(self, url):
        """
        Private method to check, if the given URL could be blocked (i.e. is
        not whitelisted).

        @param url URL to be checked
        @type QUrl
        @return flag indicating that the given URL can be blocked
        @rtype bool
        """
        return not self.__matcher.adBlockDisabledForUrl(url)
