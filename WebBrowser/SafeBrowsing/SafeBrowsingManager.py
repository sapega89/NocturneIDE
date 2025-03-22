# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the interface for Google Safe Browsing.
"""

#
# Some part of this code were ported from gglsbl.client and adapted
# to Qt.
#
# https://github.com/afilipovich/gglsbl
#

import base64
import os

from PyQt6.QtCore import (
    QCoreApplication,
    QDateTime,
    QObject,
    QTimer,
    QUrl,
    pyqtSignal,
    pyqtSlot,
)

from eric7 import EricUtilities, Preferences
from eric7.EricGui import EricPixmapCache
from eric7.SystemUtilities import OSUtilities
from eric7.UI.NotificationWidget import NotificationTypes
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .SafeBrowsingAPIClient import SafeBrowsingAPIClient
from .SafeBrowsingCache import SafeBrowsingCache
from .SafeBrowsingThreatList import HashPrefixList, ThreatList
from .SafeBrowsingUrl import SafeBrowsingUrl


class SafeBrowsingManager(QObject):
    """
    Class implementing the interface for Google Safe Browsing.

    @signal progressMessage(message,maximum) emitted to give a message for the
        action about to be performed and the maximum value
    @signal progress(current) emitted to signal the current progress
    """

    progressMessage = pyqtSignal(str, int)
    progress = pyqtSignal(int)

    enabled = Preferences.getWebBrowser("SafeBrowsingEnabled") and bool(
        Preferences.getWebBrowser("SafeBrowsingApiKey")
    )

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.__apiKey = Preferences.getWebBrowser("SafeBrowsingApiKey")
        if self.__apiKey:
            self.__apiClient = SafeBrowsingAPIClient(self.__apiKey, parent=self)
        else:
            self.__apiClient = None

        gsbCachePath = os.path.join(
            EricUtilities.getConfigDir(), "web_browser", "safe_browsing"
        )
        self.__cache = SafeBrowsingCache(gsbCachePath, self)

        self.__gsbDialog = None
        self.__setPlatforms()
        self.__setLookupMethod()

        self.__updatingThreatLists = False
        self.__threatListsUpdateTimer = QTimer(self)
        self.__threatListsUpdateTimer.setSingleShot(True)
        self.__threatListsUpdateTimer.timeout.connect(
            self.__threatListsUpdateTimerTimeout
        )
        self.__setAutoUpdateThreatLists()

    def configurationChanged(self):
        """
        Public method to handle changes of the settings.
        """
        apiKey = Preferences.getWebBrowser("SafeBrowsingApiKey")
        if apiKey != self.__apiKey:
            self.__apiKey = apiKey
            if self.__apiKey:
                if self.__apiClient:
                    self.__apiClient.setApiKey(self.__apiKey)
                else:
                    self.__apiClient = SafeBrowsingAPIClient(self.__apiKey, parent=self)

        SafeBrowsingManager.enabled = Preferences.getWebBrowser(
            "SafeBrowsingEnabled"
        ) and bool(self.__apiKey)

        self.__setPlatforms()
        self.__setLookupMethod()
        self.__setAutoUpdateThreatLists()

    def __setPlatforms(self):
        """
        Private method to set the platforms to be checked against.
        """
        self.__platforms = None
        if Preferences.getWebBrowser("SafeBrowsingFilterPlatform"):
            if OSUtilities.isWindowsPlatform():
                platform = "windows"
            elif OSUtilities.isMacPlatform():
                platform = "macos"
            else:
                # treat all other platforms like linux
                platform = "linux"
            self.__platforms = SafeBrowsingAPIClient.getPlatformTypes(platform)

    def __setLookupMethod(self):
        """
        Private method to set the lookup method (Update API or Lookup API).
        """
        self.__useLookupApi = Preferences.getWebBrowser("SafeBrowsingUseLookupApi")

    @classmethod
    def isEnabled(cls):
        """
        Class method to check, if safe browsing is enabled.

        @return flag indicating the enabled state
        @rtype bool
        """
        return cls.enabled

    def close(self):
        """
        Public method to close the safe browsing interface.
        """
        self.__cache.close()

    def fairUseDelayExpired(self):
        """
        Public method to check, if the fair use wait period has expired.

        @return flag indicating expiration
        @rtype bool
        """
        return self.isEnabled() and self.__apiClient.fairUseDelayExpired()

    def __showNotificationMessage(self, message, timeout=5):
        """
        Private method to show some message in a notification widget.

        @param message message to be shown
        @type str
        @param timeout amount of time in seconds the message should be shown
            (0 = indefinitely)
        @type int
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        kind = (
            NotificationTypes.CRITICAL
            if timeout == 0
            else NotificationTypes.INFORMATION
        )

        WebBrowserWindow.showNotification(
            EricPixmapCache.getPixmap("safeBrowsing48"),
            self.tr("Google Safe Browsing"),
            message,
            kind=kind,
            timeout=timeout,
        )

    def __setAutoUpdateThreatLists(self):
        """
        Private method to set auto update for the threat lists.
        """
        autoUpdateEnabled = Preferences.getWebBrowser(
            "SafeBrowsingAutoUpdate"
        ) and not Preferences.getWebBrowser("SafeBrowsingUseLookupApi")
        if autoUpdateEnabled and self.isEnabled():
            nextUpdateDateTime = Preferences.getWebBrowser("SafeBrowsingUpdateDateTime")
            if nextUpdateDateTime.isValid():
                interval = (
                    QDateTime.currentDateTime().secsTo(nextUpdateDateTime)
                    + 2
                    # 2 seconds extra wait time; interval in milliseconds
                )

                if interval < 5:
                    interval = 5
                    # minimum 5 seconds interval
            else:
                interval = 5
                # just wait 5 seconds
            self.__threatListsUpdateTimer.start(interval * 1000)
        else:
            if self.__threatListsUpdateTimer.isActive():
                self.__threatListsUpdateTimer.stop()

    @pyqtSlot()
    def __threatListsUpdateTimerTimeout(self):
        """
        Private slot to perform the auto update of the threat lists.
        """
        ok = False
        if self.isEnabled():
            self.__showNotificationMessage(self.tr("Updating threat lists..."), 0)
            ok = self.updateHashPrefixCache()[0]
            if ok:
                self.__showNotificationMessage(self.tr("Updating threat lists done."))
            else:
                self.__showNotificationMessage(
                    self.tr("Updating threat lists failed."), timeout=0
                )

        if ok:
            nextUpdateDateTime = self.__apiClient.getFairUseDelayExpirationDateTime()
            Preferences.setWebBrowser("SafeBrowsingUpdateDateTime", nextUpdateDateTime)
            self.__threatListsUpdateTimer.start(
                (QDateTime.currentDateTime().secsTo(nextUpdateDateTime) + 2) * 1000
            )
            # 2 seconds extra wait time; interval in milliseconds
        else:
            Preferences.setWebBrowser("SafeBrowsingUpdateDateTime", QDateTime())

    def updateHashPrefixCache(self):
        """
        Public method to load or update the locally cached threat lists.

        @return flag indicating success and an error message
        @rtype tuple of (bool, str)
        """
        if not self.isEnabled():
            return False, self.tr("Safe Browsing is disabled.")

        if not self.__apiClient.fairUseDelayExpired():
            return (
                False,
                self.tr(
                    "The fair use wait period has not expired yet."
                    "Expiration will be at {0}."
                ).format(
                    self.__apiClient.getFairUseDelayExpirationDateTime().toString(
                        "yyyy-MM-dd, HH:mm:ss"
                    )
                ),
            )

        self.__updatingThreatLists = True
        ok = True
        errorMessage = ""

        # step 1: remove expired hashes
        self.__cache.cleanupFullHashes()
        QCoreApplication.processEvents()

        # step 2: update threat lists
        threatListsForRemove = {}
        for threatList, _clientState in self.__cache.getThreatLists():
            threatListsForRemove[repr(threatList)] = threatList
        threatLists, error = self.__apiClient.getThreatLists()
        if error:
            return False, error

        maximum = len(threatLists)
        self.progressMessage.emit(self.tr("Updating threat lists"), maximum)
        for current, entry in enumerate(threatLists, start=1):
            self.progress.emit(current)
            QCoreApplication.processEvents()
            threatList = ThreatList.fromApiEntry(entry)
            if self.__platforms is None or threatList.platformType in self.__platforms:
                self.__cache.addThreatList(threatList)
                key = repr(threatList)
                if key in threatListsForRemove:
                    del threatListsForRemove[key]

        maximum = len(threatListsForRemove.values())
        self.progressMessage.emit(self.tr("Deleting obsolete threat lists"), maximum)
        for current, threatList in enumerate(threatListsForRemove.values(), start=1):
            self.progress.emit(current)
            QCoreApplication.processEvents()
            self.__cache.deleteHashPrefixList(threatList)
            self.__cache.deleteThreatList(threatList)
        del threatListsForRemove

        # step 3: update threats
        threatLists = self.__cache.getThreatLists()
        clientStates = {}
        for threatList, clientState in threatLists:
            clientStates[threatList.asTuple()] = clientState
        threatsUpdateResponses, error = self.__apiClient.getThreatsUpdate(clientStates)
        if error:
            return False, error

        maximum = len(threatsUpdateResponses)
        self.progressMessage.emit(self.tr("Updating hash prefixes"), maximum)
        for current, response in enumerate(threatsUpdateResponses, start=1):
            self.progress.emit(current)
            QCoreApplication.processEvents()
            responseThreatList = ThreatList.fromApiEntry(response)
            if response["responseType"] == "FULL_UPDATE":
                self.__cache.deleteHashPrefixList(responseThreatList)
            for removal in response.get("removals", []):
                self.__cache.removeHashPrefixIndices(
                    responseThreatList, removal["rawIndices"]["indices"]
                )
                QCoreApplication.processEvents()
            for addition in response.get("additions", []):
                hashPrefixList = HashPrefixList(
                    addition["rawHashes"]["prefixSize"],
                    base64.b64decode(addition["rawHashes"]["rawHashes"]),
                )
                self.__cache.populateHashPrefixList(responseThreatList, hashPrefixList)
                QCoreApplication.processEvents()
            expectedChecksum = base64.b64decode(response["checksum"]["sha256"])
            if self.__verifyThreatListChecksum(responseThreatList, expectedChecksum):
                self.__cache.updateThreatListClientState(
                    responseThreatList, response["newClientState"]
                )
            else:
                ok = False
                errorMessage = self.tr(
                    "Local cache checksum does not match the server. Consider"
                    " cleaning the cache. Threat update has been aborted."
                )

        self.__updatingThreatLists = False

        return ok, errorMessage

    def isUpdatingThreatLists(self):
        """
        Public method to check, if we are in the process of updating the
        threat lists.

        @return flag indicating an update process is active
        @rtype bool
        """
        return self.__updatingThreatLists

    def __verifyThreatListChecksum(self, threatList, remoteChecksum):
        """
        Private method to verify the local checksum of a threat list with the
        checksum of the safe browsing server.

        @param threatList threat list to calculate checksum for
        @type ThreatList
        @param remoteChecksum SHA256 checksum as reported by the Google server
        @type bytes
        @return flag indicating equality
        @rtype bool
        """
        localChecksum = self.__cache.hashPrefixListChecksum(threatList)
        return remoteChecksum == localChecksum

    def fullCacheCleanup(self):
        """
        Public method to clean up the cache completely.
        """
        self.__cache.prepareCacheDb()

    def showSafeBrowsingDialog(self):
        """
        Public slot to show the safe browsing management dialog.
        """
        from .SafeBrowsingDialog import SafeBrowsingDialog

        if self.__gsbDialog is None:
            self.__gsbDialog = SafeBrowsingDialog(
                self, parent=WebBrowserWindow.mainWindow()
            )

        self.__gsbDialog.show()

    def lookupUrl(self, url):
        """
        Public method to lookup an URL.

        @param url URL to be checked
        @type str or QUrl
        @return tuple containing the list of threat lists the URL was found in
            and an error message
        @rtype tuple of (list of ThreatList, str)
        @exception ValueError raised for an invalid URL
        """
        if self.isEnabled():
            if self.__useLookupApi:
                if isinstance(url, str):
                    url = QUrl(url.strip())

                if url.isEmpty():
                    raise ValueError("Empty URL given.")

                listNames, error = self.__apiClient.lookupUrl(url, self.__platforms)
                return listNames, error
            else:
                if isinstance(url, QUrl):
                    urlStr = url.toString().strip()
                else:
                    urlStr = url.strip()

                if not urlStr:
                    raise ValueError("Empty URL given.")

                urlHashes = SafeBrowsingUrl(urlStr).hashes()
                listNames = self.__lookupHashes(urlHashes)

                return listNames, ""

        return None, ""

    def __lookupHashes(self, fullHashes):
        """
        Private method to lookup the given hashes.

        @param fullHashes list of hashes to lookup
        @type list of bytes
        @return names of threat lists hashes were found in
        @rtype list of ThreatList
        """
        fullHashes = list(fullHashes)
        cues = [fh[:4].hex() for fh in fullHashes]
        result = []

        matchingPrefixes = {}
        matchingFullHashes = set()
        isPotentialThreat = False
        # Lookup hash prefixes which match full URL hash
        for (
            _threatList,
            hashPrefix,
            negativeCacheExpired,
        ) in self.__cache.lookupHashPrefix(cues):
            for fullHash in fullHashes:
                if fullHash.startswith(hashPrefix):
                    isPotentialThreat = True
                    # consider hash prefix negative cache as expired if it
                    # is expired in at least one threat list
                    matchingPrefixes[hashPrefix] = (
                        matchingPrefixes.get(hashPrefix, False) or negativeCacheExpired
                    )
                    matchingFullHashes.add(fullHash)

        # if none matches, url hash is clear
        if not isPotentialThreat:
            return []

        # if there is non-expired full hash, URL is blocked
        matchingExpiredThreatLists = set()
        for threatList, hasExpired in self.__cache.lookupFullHashes(matchingFullHashes):
            if hasExpired:
                matchingExpiredThreatLists.add(threatList)
            else:
                result.append(threatList)
        if result:
            return result

        # If there are no matching expired full hash entries and negative
        # cache is still current for all prefixes, consider it safe.
        if (
            len(matchingExpiredThreatLists) == 0
            and sum(map(int, matchingPrefixes.values())) == 0
        ):
            return []

        # Now it can be assumed that there are expired matching full hash
        # entries and/or cache prefix entries with expired negative cache.
        # Both require full hash synchronization.
        self.__syncFullHashes(matchingPrefixes.keys())

        # Now repeat full hash lookup
        for threatList, hasExpired in self.__cache.lookupFullHashes(matchingFullHashes):
            if not hasExpired:
                result.append(threatList)

        return result

    def __syncFullHashes(self, hashPrefixes):
        """
        Private method to download full hashes matching given prefixes.

        This also updates the cache expiration timestamps.

        @param hashPrefixes list of hash prefixes to get full hashes for
        @type list of bytes
        """
        threatLists = self.__cache.getThreatLists()
        clientStates = {}
        for threatList, clientState in threatLists:
            clientStates[threatList.asTuple()] = clientState

        fullHashResponses = self.__apiClient.getFullHashes(hashPrefixes, clientStates)

        # update negative cache for each hash prefix
        # store full hash with positive cache bumped up
        for match in fullHashResponses["matches"]:
            threatList = ThreatList.fromApiEntry(match)
            hashValue = base64.b64decode(match["threat"]["hash"])
            cacheDuration = int(match["cacheDuration"].rstrip("s"))
            malwareThreatType = None
            for metadata in match["threatEntryMetadata"].get("entries", []):
                key = base64.b64decode(metadata["key"])
                value = base64.b64decode(metadata["value"])
                if key == b"malware_threat_type":
                    malwareThreatType = value
                    if not isinstance(malwareThreatType, str):
                        malwareThreatType = malwareThreatType.decode()
            self.__cache.storeFullHash(
                threatList, hashValue, cacheDuration, malwareThreatType
            )

        negativeCacheDuration = int(
            fullHashResponses["negativeCacheDuration"].rstrip("s")
        )
        for prefixValue in hashPrefixes:
            for threatList, _clientState in threatLists:
                self.__cache.updateHashPrefixExpiration(
                    threatList, prefixValue, negativeCacheDuration
                )

    @classmethod
    def getIgnoreSchemes(cls):
        """
        Class method to get the schemes not to be checked.

        @return list of schemes to be ignored
        @rtype list of str
        """
        return [
            "about",
            "eric",
            "qrc",
            "qthelp",
            "chrome",
            "abp",
            "file",
        ]

    def getThreatMessage(self, threatType):
        """
        Public method to get a warning message for the given threat type.

        @param threatType threat type to get the message for
        @type str
        @return threat message
        @rtype str
        """
        msg = self.__apiClient.getThreatMessage(threatType) if self.__apiClient else ""

        return msg

    def getThreatMessages(self, threatLists):
        """
        Public method to get threat messages for the given threats.

        @param threatLists list of threat lists to get a message for
        @type list of ThreatList
        @return list of threat messages, one per unique threat type
        @rtype list of str
        """
        threatTypes = set()
        for threatList in threatLists:
            threatTypes.add(threatList.threatType)

        messages = []
        if self.__apiClient:
            for threatType in sorted(threatTypes):
                msg = self.__apiClient.getThreatMessage(threatType)
                messages.append(msg)

        return messages

    def getThreatType(self, threatList):
        """
        Public method to get a display string for a given threat type.

        @param threatList threat list to get display string for
        @type str
        @return display string
        @rtype str
        """
        displayString = ""
        if self.__apiClient:
            displayString = self.__apiClient.getThreatType(threatList.threatType)
        return displayString

    def getPlatformString(self, platformType):
        """
        Public method to get the platform string for a given platform type.

        @param platformType platform type as defined in the v4 API
        @type str
        @return platform string
        @rtype str
        """
        if self.__apiClient:
            return self.__apiClient.getPlatformString(platformType)
        else:
            return ""

    def getThreatEntryString(self, threatEntry):
        """
        Public method to get the threat entry string.

        @param threatEntry threat entry type as defined in the v4 API
        @type str
        @return threat entry string
        @rtype str
        """
        if self.__apiClient:
            return self.__apiClient.getThreatEntryString(threatEntry)
        else:
            return ""
