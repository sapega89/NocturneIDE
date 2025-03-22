# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the low level interface for Google Safe Browsing.
"""

import base64
import json

from PyQt6.QtCore import (
    QByteArray,
    QCoreApplication,
    QDateTime,
    QEventLoop,
    QObject,
    QUrl,
    pyqtSignal,
)
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest

from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from .SafeBrowsingThreatList import ThreatList


class SafeBrowsingAPIClient(QObject):
    """
    Class implementing the low level interface for Google Safe Browsing.

    @signal networkError(str) emitted to indicate a network error
    """

    ClientId = "eric7_API_client"
    ClientVersion = "2.0.0"

    GsbUrlTemplate = "https://safebrowsing.googleapis.com/v4/{0}?key={1}"

    networkError = pyqtSignal(str)

    def __init__(self, apiKey, fairUse=True, parent=None):
        """
        Constructor

        @param apiKey API key to be used
        @type str
        @param fairUse flag indicating to follow the fair use policy
        @type bool
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__apiKey = apiKey
        self.__fairUse = fairUse

        self.__nextRequestNoSoonerThan = QDateTime()
        self.__failCount = 0

        self.__lookupApiCache = {}
        # Temporary cache used by the lookup API (v4)
        # key: URL as string
        # value: dictionary with these entries:
        #   "validUntil": (QDateTime)
        #   "threatInfo": (list of ThreatList)

    def setApiKey(self, apiKey):
        """
        Public method to set the API key.

        @param apiKey API key to be set
        @type str
        """
        self.__apiKey = apiKey

    def getThreatLists(self):
        """
        Public method to retrieve all available threat lists.

        @return tuple containing list of threat lists and an error message
        @rtype tuple of (list of dict containing 'threatType', 'platformType'
            and 'threatEntryType', bool)
        """
        url = QUrl(self.GsbUrlTemplate.format("threatLists", self.__apiKey))
        req = QNetworkRequest(url)
        reply = WebBrowserWindow.networkManager().get(req)

        while reply.isRunning():
            QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 200)
            # max. 200 ms processing

        res = None
        error = ""
        if reply.error() != QNetworkReply.NetworkError.NoError:
            error = reply.errorString()
            self.networkError.emit(error)
        else:
            result = self.__extractData(reply)
            res = result["threatLists"]

        reply.deleteLater()
        return res, error

    #######################################################################
    ## Methods below implement the 'Update API (v4)'
    #######################################################################

    def getThreatsUpdate(self, clientStates):
        """
        Public method to fetch hash prefix updates for the given threat list.

        @param clientStates dictionary of client states with keys like
            (threatType, platformType, threatEntryType)
        @type dict
        @return tuple containing the list of threat updates and an error
            message
        @rtype tuple of (list of dict, bool)
        """
        requestBody = {
            "client": {
                "clientId": self.ClientId,
                "clientVersion": self.ClientVersion,
            },
            "listUpdateRequests": [],
        }

        for (
            threatType,
            platformType,
            threatEntryType,
        ), currentState in clientStates.items():
            requestBody["listUpdateRequests"].append(
                {
                    "threatType": threatType,
                    "platformType": platformType,
                    "threatEntryType": threatEntryType,
                    "state": currentState,
                    "constraints": {
                        "supportedCompressions": ["RAW"],
                    },
                }
            )

        data = QByteArray(json.dumps(requestBody).encode("utf-8"))
        url = QUrl(self.GsbUrlTemplate.format("threatListUpdates:fetch", self.__apiKey))
        req = QNetworkRequest(url)
        req.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json"
        )
        reply = WebBrowserWindow.networkManager().post(req, data)

        while reply.isRunning():
            QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 200)
            # max. 200 ms processing

        res = None
        error = ""
        if reply.error() != QNetworkReply.NetworkError.NoError:
            error = reply.errorString()
            self.networkError.emit(error)
        else:
            result = self.__extractData(reply)
            res = result["listUpdateResponses"]

        reply.deleteLater()
        return res, error

    def getFullHashes(self, prefixes, clientState):
        """
        Public method to find full hashes matching hash prefixes.

        @param prefixes list of hash prefixes to find
        @type list of bytes
        @param clientState dictionary of client states with keys like
            (threatType, platformType, threatEntryType)
        @type dict
        @return dictionary containing the list of found hashes and the
            negative cache duration
        @rtype dict
        """
        requestBody = {
            "client": {
                "clientId": self.ClientId,
                "clientVersion": self.ClientVersion,
            },
            "clientStates": [],
            "threatInfo": {
                "threatTypes": [],
                "platformTypes": [],
                "threatEntryTypes": [],
                "threatEntries": [],
            },
        }

        for prefix in prefixes:
            requestBody["threatInfo"]["threatEntries"].append(
                {"hash": base64.b64encode(prefix).decode("ascii")}
            )

        for (
            threatType,
            platformType,
            threatEntryType,
        ), currentState in clientState.items():
            requestBody["clientStates"].append(currentState)
            if threatType not in requestBody["threatInfo"]["threatTypes"]:
                requestBody["threatInfo"]["threatTypes"].append(threatType)
            if platformType not in requestBody["threatInfo"]["platformTypes"]:
                requestBody["threatInfo"]["platformTypes"].append(platformType)
            if threatEntryType not in requestBody["threatInfo"]["threatEntryTypes"]:
                requestBody["threatInfo"]["threatEntryTypes"].append(threatEntryType)

        data = QByteArray(json.dumps(requestBody).encode("utf-8"))
        url = QUrl(self.GsbUrlTemplate.format("fullHashes:find", self.__apiKey))
        req = QNetworkRequest(url)
        req.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json"
        )
        reply = WebBrowserWindow.networkManager().post(req, data)

        while reply.isRunning():
            QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 200)
            # max. 200 ms processing

        res = []
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.networkError.emit(reply.errorString())
        else:
            res = self.__extractData(reply)

        reply.deleteLater()
        return res

    def __extractData(self, reply):
        """
        Private method to extract the data of a network reply.

        @param reply reference to the network reply object
        @type QNetworkReply
        @return extracted data
        @rtype list or dict
        """
        result = json.loads(str(reply.readAll(), "utf-8"))
        self.__setWaitDuration(result.get("minimumWaitDuration"))
        return result

    def __setWaitDuration(self, minimumWaitDuration):
        """
        Private method to set the minimum wait duration.

        @param minimumWaitDuration duration to be set
        @type str
        """
        if not self.__fairUse or minimumWaitDuration is None:
            self.__nextRequestNoSoonerThan = QDateTime()
        else:
            waitDuration = int(float(minimumWaitDuration.rstrip("s")))
            self.__nextRequestNoSoonerThan = QDateTime.currentDateTime().addSecs(
                waitDuration
            )

    def fairUseDelayExpired(self):
        """
        Public method to check, if the fair use wait period has expired.

        @return flag indicating expiration
        @rtype bool
        """
        return (
            self.__fairUse
            and QDateTime.currentDateTime() >= self.__nextRequestNoSoonerThan
        ) or not self.__fairUse

    def getFairUseDelayExpirationDateTime(self):
        """
        Public method to get the date and time the fair use delay will expire.

        @return fair use delay expiration date and time
        @rtype QDateTime
        """
        return self.__nextRequestNoSoonerThan

    #######################################################################
    ## Methods below implement the 'Lookup API (v4)'
    #######################################################################

    def lookupUrl(self, url, platforms):
        """
        Public method to send an URL to Google for checking.

        @param url URL to be checked
        @type QUrl
        @param platforms list of platform types to check against
        @type list of str
        @return tuple containing the list of threat list info objects and
            an error message
        @rtype tuple of (list of ThreatList, str)
        """
        error = ""

        # sanitize the URL by removing user info and query data
        url = url.adjusted(
            QUrl.UrlFormattingOption.RemoveUserInfo
            | QUrl.UrlFormattingOption.RemoveQuery
            | QUrl.UrlFormattingOption.RemoveFragment
        )
        urlStr = url.toString()

        # check the local cache first
        if urlStr in self.__lookupApiCache:
            if (
                self.__lookupApiCache[urlStr]["validUntil"]
                > QDateTime.currentDateTime()
            ):
                # cached entry is still valid
                return self.__lookupApiCache[urlStr]["threatInfo"], error
            else:
                del self.__lookupApiCache[urlStr]

        # no valid entry found, ask the safe browsing server
        requestBody = {
            "client": {
                "clientId": self.ClientId,
                "clientVersion": self.ClientVersion,
            },
            "threatInfo": {
                "threatTypes": SafeBrowsingAPIClient.definedThreatTypes(),
                "platformTypes": platforms,
                "threatEntryTypes": SafeBrowsingAPIClient.definedThreatEntryTypes(),
                "threatEntries": [
                    {"url": urlStr},
                ],
            },
        }

        data = QByteArray(json.dumps(requestBody).encode("utf-8"))
        url = QUrl(self.GsbUrlTemplate.format("threatMatches:find", self.__apiKey))
        req = QNetworkRequest(url)
        req.setHeader(
            QNetworkRequest.KnownHeaders.ContentTypeHeader, "application/json"
        )
        reply = WebBrowserWindow.networkManager().post(req, data)

        while reply.isRunning():
            QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.AllEvents, 200)
            # max. 200 ms processing

        threats = []
        if reply.error() != QNetworkReply.NetworkError.NoError:
            error = reply.errorString()
            self.networkError.emit(error)
        else:
            res = json.loads(str(reply.readAll(), "utf-8"))
            if res and "matches" in res:
                cacheDuration = 0
                for match in res["matches"]:
                    threatInfo = ThreatList(
                        match["threatType"],
                        match["platformType"],
                        match["threatEntryType"],
                    )
                    threats.append(threatInfo)
                    if "cacheDuration" in match:
                        cacheDurationSec = int(
                            match["cacheDuration"].strip().rstrip("s").split(".")[0]
                        )
                        if cacheDurationSec > cacheDuration:
                            cacheDuration = cacheDurationSec
                if cacheDuration > 0 and bool(threats):
                    validUntil = QDateTime.currentDateTime().addSecs(cacheDuration)
                    self.__lookupApiCache[urlStr] = {
                        "validUntil": validUntil,
                        "threatInfo": threats,
                    }

        reply.deleteLater()
        return threats, error

    #######################################################################
    ## Methods below implement global (class wide) functionality
    #######################################################################

    @classmethod
    def getThreatMessage(cls, threatType):
        """
        Class method to get a warning message for the given threat type.

        @param threatType threat type to get the message for
        @type str
        @return threat message
        @rtype str
        """
        threatType = threatType.lower()
        if threatType == "malware":
            msg = QCoreApplication.translate(
                "SafeBrowsingAPI",
                "<h3>Malware Warning</h3>"
                "<p>The web site you are about to visit may try to install"
                " harmful programs on your computer in order to steal or"
                " destroy your data.</p>",
            )
        elif threatType == "social_engineering":
            msg = QCoreApplication.translate(
                "SafeBrowsingAPI",
                "<h3>Phishing Warning</h3>"
                "<p>The web site you are about to visit may try to trick you"
                " into doing something dangerous online, such as revealing"
                " passwords or personal information, usually through a fake"
                " website.</p>",
            )
        elif threatType == "unwanted_software":
            msg = QCoreApplication.translate(
                "SafeBrowsingAPI",
                "<h3>Unwanted Software Warning</h3>"
                "<p>The software you are about to download may negatively"
                " affect your browsing or computing experience.</p>",
            )
        elif threatType == "potentially_harmful_application":
            msg = QCoreApplication.translate(
                "SafeBrowsingAPI",
                "<h3>Potentially Harmful Application</h3>"
                "<p>The web site you are about to visit may try to trick you"
                " into installing applications, that may negatively affect"
                " your browsing experience.</p>",
            )
        elif threatType == "malicious_binary":
            msg = QCoreApplication.translate(
                "SafeBrowsingAPI",
                "<h3>Malicious Binary Warning</h3>"
                "<p>The software you are about to download may be harmful"
                " to your computer.</p>",
            )
        else:
            # unknow threat
            msg = QCoreApplication.translate(
                "SafeBrowsingAPI",
                "<h3>Unknown Threat Warning</h3>"
                "<p>The web site you are about to visit was found in the Safe"
                " Browsing Database but was not classified yet.</p>",
            )

        return msg

    @classmethod
    def getThreatType(cls, threatType):
        """
        Class method to get a display string for a given threat type.

        @param threatType threat type to get display string for
        @type str
        @return display string
        @rtype str
        """
        threatType = threatType.lower()
        if threatType == "malware":
            displayString = QCoreApplication.translate("SafeBrowsingAPI", "Malware")
        elif threatType == "social_engineering":
            displayString = QCoreApplication.translate("SafeBrowsingAPI", "Phishing")
        elif threatType == "unwanted_software":
            displayString = QCoreApplication.translate(
                "SafeBrowsingAPI", "Unwanted Software"
            )
        elif threatType == "potentially_harmful_application":
            displayString = QCoreApplication.translate(
                "SafeBrowsingAPI", "Harmful Application"
            )
        elif threatType == "malcious_binary":
            displayString = QCoreApplication.translate(
                "SafeBrowsingAPI", "Malicious Binary"
            )
        else:
            displayString = QCoreApplication.translate(
                "SafeBrowsingAPI", "Unknown Threat"
            )

        return displayString

    @classmethod
    def definedThreatTypes(cls):
        """
        Class method to get all threat types defined in API v4.

        @return list of defined threat types
        @rtype list of str
        """
        return [
            "THREAT_TYPE_UNSPECIFIED",
            "MALWARE",
            "SOCIAL_ENGINEERING",
            "UNWANTED_SOFTWARE",
            "POTENTIALLY_HARMFUL_APPLICATION",
        ]

    @classmethod
    def getThreatEntryString(cls, threatEntry):
        """
        Class method to get the threat entry string.

        @param threatEntry threat entry type as defined in the v4 API
        @type str
        @return threat entry string
        @rtype str
        """
        if threatEntry == "URL":
            return "URL"
        elif threatEntry == "EXECUTABLE":
            return QCoreApplication.translate("SafeBrowsingAPI", "executable program")
        else:
            return QCoreApplication.translate("SafeBrowsingAPI", "unknown type")

    @classmethod
    def definedThreatEntryTypes(cls):
        """
        Class method to get all threat entry types defined in API v4.

        @return list of all defined threat entry types
        @rtype list of str
        """
        return [
            "THREAT_ENTRY_TYPE_UNSPECIFIED",
            "URL",
            "EXECUTABLE",
        ]

    @classmethod
    def getPlatformString(cls, platformType):
        """
        Class method to get the platform string for a given platform type.

        @param platformType platform type as defined in the v4 API
        @type str
        @return platform string
        @rtype str
        """
        platformStrings = {
            "WINDOWS": "Windows",
            "LINUX": "Linux",
            "ANDROID": "Android",
            "OSX": "macOS",
            "IOS": "iOS",
            "CHROME": "Chrome OS",
        }
        if platformType in platformStrings:
            return platformStrings[platformType]

        if platformType == "ANY_PLATFORM":
            return QCoreApplication.translate("SafeBrowsingAPI", "any defined platform")
        elif platformType == "ALL_PLATFORMS":
            return QCoreApplication.translate(
                "SafeBrowsingAPI", "all defined platforms"
            )
        else:
            return QCoreApplication.translate("SafeBrowsingAPI", "unknown platform")

    @classmethod
    def getPlatformTypes(cls, platform):
        """
        Class method to get the platform types for a given platform.

        @param platform platform string
        @type str (one of 'linux', 'windows', 'macos')
        @return list of platform types as defined in the v4 API for the
            given platform
        @rtype list of str
        @exception ValueError raised to indicate an invalid platform string
        """
        platform = platform.lower()

        if platform not in ("linux", "windows", "macos"):
            raise ValueError("Unsupported platform")

        platformTypes = ["ANY_PLATFORM", "ALL_PLATFORMS"]
        if platform == "linux":
            platformTypes.append("LINUX")
        elif platform == "windows":
            platformTypes.append("WINDOWS")
        else:
            platformTypes.append("OSX")

        return platformTypes

    @classmethod
    def definedPlatformTypes(cls):
        """
        Class method to get all platform types defined in API v4.

        @return list of all defined platform types
        @rtype list of str
        """
        return [
            "PLATFORM_TYPE_UNSPECIFIED",
            "WINDOWS",
            "LINUX",
            "ANDROID",
            "OSX",
            "IOS",
            "ANY_PLATFORM",
            "ALL_PLATFORMS",
            "CHROME",
        ]
