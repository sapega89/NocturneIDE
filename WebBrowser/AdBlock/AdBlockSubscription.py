# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the AdBlock subscription class.
"""

import base64
import hashlib
import os
import re

from PyQt6.QtCore import (
    QByteArray,
    QCryptographicHash,
    QDate,
    QDateTime,
    QObject,
    Qt,
    QTime,
    QUrl,
    QUrlQuery,
    pyqtSignal,
)
from PyQt6.QtNetwork import QNetworkReply, QNetworkRequest

from eric7 import EricUtilities, Preferences
from eric7.EricWidgets import EricMessageBox
from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow


class AdBlockSubscription(QObject):
    """
    Class implementing the AdBlock subscription.

    @signal changed() emitted after the subscription has changed
    @signal rulesChanged() emitted after the subscription's rules have changed
    @signal enabledChanged(bool) emitted after the enabled state was changed
    @signal rulesEnabledChanged() emitted after a rule enabled state was
        changed
    """

    changed = pyqtSignal()
    rulesChanged = pyqtSignal()
    enabledChanged = pyqtSignal(bool)
    rulesEnabledChanged = pyqtSignal()

    def __init__(self, url, custom, parent=None, default=False):
        """
        Constructor

        @param url AdBlock URL for the subscription
        @type QUrl
        @param custom flag indicating a custom subscription
        @type bool
        @param parent reference to the parent object
        @type QObject
        @param default flag indicating a default subscription
        @type bool
        """
        super().__init__(parent)

        self.__custom = custom
        self.__url = url.toEncoded()
        self.__enabled = False
        self.__downloading = None
        self.__defaultSubscription = default

        self.__title = ""
        self.__location = QByteArray()
        self.__lastUpdate = QDateTime()
        self.__requiresLocation = ""
        self.__requiresTitle = ""

        self.__updatePeriod = 0  # update period in hours, 0 = use default
        self.__remoteModified = QDateTime()

        self.__rules = []  # list containing all AdBlock rules

        self.__checksumRe = re.compile(
            r"""^\s*!\s*checksum[\s\-:]+([\w\+\/=]+).*\n""",
            re.IGNORECASE | re.MULTILINE,
        )
        self.__expiresRe = re.compile(
            r"""(?:expires:|expires after)\s*(\d+)\s*(hour|h)?""", re.IGNORECASE
        )
        self.__remoteModifiedRe = re.compile(
            r"""!\s*(?:Last modified|Updated):\s*(\d{1,2})\s*"""
            r"""(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*"""
            r"""(\d{2,4})\s*((\d{1,2}):(\d{2}))?""",
            re.IGNORECASE,
        )

        self.__monthNameToNumber = {
            "Jan": 1,
            "Feb": 2,
            "Mar": 3,
            "Apr": 4,
            "May": 5,
            "Jun": 6,
            "Jul": 7,
            "Aug": 8,
            "Sep": 9,
            "Oct": 10,
            "Nov": 11,
            "Dec": 12,
        }

        self.__parseUrl(url)

    def __parseUrl(self, url):
        """
        Private method to parse the AdBlock URL for the subscription.

        @param url AdBlock URL for the subscription
        @type QUrl
        """
        if url.scheme() != "abp":
            return

        if url.path() != "subscribe":
            return

        urlQuery = QUrlQuery(url)
        self.__title = QUrl.fromPercentEncoding(
            QByteArray(urlQuery.queryItemValue("title").encode())
        )
        self.__enabled = urlQuery.queryItemValue("enabled") != "false"
        self.__location = QByteArray(
            QUrl.fromPercentEncoding(
                QByteArray(urlQuery.queryItemValue("location").encode())
            ).encode("utf-8")
        )

        # Check for required subscription
        self.__requiresLocation = QUrl.fromPercentEncoding(
            QByteArray(urlQuery.queryItemValue("requiresLocation").encode())
        )
        self.__requiresTitle = QUrl.fromPercentEncoding(
            QByteArray(urlQuery.queryItemValue("requiresTitle").encode())
        )
        if self.__requiresLocation and self.__requiresTitle:
            WebBrowserWindow.adBlockManager().loadRequiredSubscription(
                self.__requiresLocation, self.__requiresTitle
            )

        lastUpdateString = urlQuery.queryItemValue("lastUpdate")
        self.__lastUpdate = QDateTime.fromString(
            lastUpdateString, Qt.DateFormat.ISODate
        )

        self.__loadRules()

    def url(self):
        """
        Public method to generate the URL for this subscription.

        @return AdBlock URL for the subscription
        @rtype QUrl
        """
        url = QUrl()
        url.setScheme("abp")
        url.setPath("subscribe")

        queryItems = []
        queryItems.append(("location", bytes(self.__location).decode()))
        queryItems.append(("title", self.__title))
        if self.__requiresLocation and self.__requiresTitle:
            queryItems.append(("requiresLocation", self.__requiresLocation))
            queryItems.append(("requiresTitle", self.__requiresTitle))
        if not self.__enabled:
            queryItems.append(("enabled", "false"))
        if self.__lastUpdate.isValid():
            queryItems.append(
                ("lastUpdate", self.__lastUpdate.toString(Qt.DateFormat.ISODate))
            )

        query = QUrlQuery()
        query.setQueryItems(queryItems)
        url.setQuery(query)
        return url

    def isEnabled(self):
        """
        Public method to check, if the subscription is enabled.

        @return flag indicating the enabled status
        @rtype bool
        """
        return self.__enabled

    def setEnabled(self, enabled):
        """
        Public method to set the enabled status.

        @param enabled flag indicating the enabled status
        @type bool
        """
        if self.__enabled == enabled:
            return

        self.__enabled = enabled
        self.enabledChanged.emit(enabled)

    def title(self):
        """
        Public method to get the subscription title.

        @return subscription title
        @rtype string
        """
        return self.__title

    def setTitle(self, title):
        """
        Public method to set the subscription title.

        @param title subscription title
        @type str
        """
        if self.__title == title:
            return

        self.__title = title
        self.changed.emit()

    def location(self):
        """
        Public method to get the subscription location.

        @return URL of the subscription location
        @rtype QUrl
        """
        return QUrl.fromEncoded(self.__location)

    def setLocation(self, url):
        """
        Public method to set the subscription location.

        @param url URL of the subscription location
        @type QUrl
        """
        if url == self.location():
            return

        self.__location = url.toEncoded()
        self.__lastUpdate = QDateTime()
        self.changed.emit()

    def requiresLocation(self):
        """
        Public method to get the location of a required subscription.

        @return location of a required subscription
        @rtype str
        """
        return self.__requiresLocation

    def lastUpdate(self):
        """
        Public method to get the date and time of the last update.

        @return date and time of the last update
        @rtype QDateTime
        """
        return self.__lastUpdate

    def rulesFileName(self):
        """
        Public method to get the name of the rules file.

        @return name of the rules file
        @rtype str
        """
        if self.location().scheme() == "file":
            return self.location().toLocalFile()

        if self.__location.isEmpty():
            return ""

        sha1 = bytes(
            QCryptographicHash.hash(
                self.__location, QCryptographicHash.Algorithm.Sha1
            ).toHex()
        ).decode()
        dataDir = os.path.join(
            EricUtilities.getConfigDir(), "web_browser", "subscriptions"
        )
        if not os.path.exists(dataDir):
            os.makedirs(dataDir)
        fileName = os.path.join(dataDir, "adblock_subscription_{0}".format(sha1))
        return fileName

    def __loadRules(self):
        """
        Private method to load the rules of the subscription.
        """
        from .AdBlockRule import AdBlockRule

        fileName = self.rulesFileName()
        if os.path.exists(fileName):
            try:
                with open(fileName, "r", encoding="utf-8") as f:
                    header = f.readline().strip()
                    if not header.startswith("[Adblock"):
                        EricMessageBox.warning(
                            None,
                            self.tr("Load subscription rules"),
                            self.tr(
                                """AdBlock file '{0}' does not start"""
                                """ with [Adblock."""
                            ).format(fileName),
                        )
                        f.close()
                        os.unlink(fileName)
                        self.__lastUpdate = QDateTime()
                    else:
                        self.__updatePeriod = 0
                        self.__remoteModified = QDateTime()
                        self.__rules = []
                        self.__rules.append(AdBlockRule(header, self))
                        for line in f.readlines():
                            line = line.strip()
                            if not line:
                                continue
                            self.__rules.append(AdBlockRule(line, self))
                            expires = self.__expiresRe.search(line)
                            if expires:
                                period, kind = expires.groups()
                                if kind:
                                    # hours
                                    self.__updatePeriod = int(period)
                                else:
                                    # days
                                    self.__updatePeriod = int(period) * 24
                            remoteModified = self.__remoteModifiedRe.search(line)
                            if remoteModified:
                                (
                                    day,
                                    month,
                                    year,
                                    time,
                                    hour,
                                    minute,
                                ) = remoteModified.groups()
                                self.__remoteModified.setDate(
                                    QDate(
                                        int(year),
                                        self.__monthNameToNumber[month],
                                        int(day),
                                    )
                                )
                                if time:
                                    self.__remoteModified.setTime(
                                        QTime(int(hour), int(minute))
                                    )
                                else:
                                    # no time given, set it to 23:59
                                    self.__remoteModified.setTime(QTime(23, 59))
                        self.changed.emit()
            except OSError as err:
                EricMessageBox.warning(
                    None,
                    self.tr("Load subscription rules"),
                    self.tr(
                        """Unable to read AdBlock file '{0}'.\nReason: {1}"""
                    ).format(fileName, str(err)),
                )

        elif not fileName.endswith("_custom"):
            self.__lastUpdate = QDateTime()

        self.checkForUpdate()

    def checkForUpdate(self):
        """
        Public method to check for an update.
        """
        updatePeriod = (
            self.__updatePeriod
            if self.__updatePeriod
            else Preferences.getWebBrowser("AdBlockUpdatePeriod") * 24
        )
        if (
            not self.__lastUpdate.isValid()
            or (
                self.__remoteModified.isValid()
                and self.__remoteModified.addSecs(updatePeriod * 3600)
                < QDateTime.currentDateTime()
            )
            or self.__lastUpdate.addSecs(updatePeriod * 3600)
            < QDateTime.currentDateTime()
        ):
            self.updateNow()

    def updateNow(self):
        """
        Public method to update the subscription immediately.
        """
        if self.__downloading is not None:
            return

        if not self.location().isValid():
            return

        if self.location().scheme() == "file":
            self.__lastUpdate = QDateTime.currentDateTime()
            self.__loadRules()
            return

        reply = WebBrowserWindow.networkManager().get(QNetworkRequest(self.location()))
        reply.finished.connect(lambda: self.__rulesDownloaded(reply))
        self.__downloading = reply

    def __rulesDownloaded(self, reply):
        """
        Private slot to deal with the downloaded rules.

        @param reply reference to the network reply
        @type QNetworkReply
        """
        response = bytes(reply.readAll())
        reply.close()
        self.__downloading = None

        if reply.error() != QNetworkReply.NetworkError.NoError:
            if not self.__defaultSubscription:
                # don't show error if we try to load the default
                EricMessageBox.warning(
                    None,
                    self.tr("Downloading subscription rules"),
                    self.tr(
                        """<p>Subscription rules could not be"""
                        """ downloaded.</p><p>Error: {0}</p>"""
                    ).format(reply.errorString()),
                )
            else:
                # reset after first download attempt
                self.__defaultSubscription = False
            return

        if not response:
            EricMessageBox.warning(
                None,
                self.tr("Downloading subscription rules"),
                self.tr("""Got empty subscription rules."""),
            )
            return

        fileName = self.rulesFileName()
        try:
            with open(fileName, "wb") as f:
                if (
                    WebBrowserWindow.adBlockManager().useLimitedEasyList()
                    and self.url()
                    .toString()
                    .startswith(
                        WebBrowserWindow.adBlockManager().getDefaultSubscriptionUrl()
                    )
                ):
                    limited = True
                    # ignore Third-party advertisers rules for performance
                    # whitelist rules at the end will be used
                    index = response.find(
                        b"!---------------------------"
                        b"Third-party advertisers"
                        b"---------------------------!"
                    )
                    part1 = response[:index]
                    index = response.find(
                        b"!-----------------------"
                        b"Whitelists to fix broken sites"
                        b"------------------------!"
                    )
                    part2 = response[index:]
                    f.write(part1)
                    f.write(part2)
                else:
                    limited = False
                    f.write(response)
                f.close()
                self.__lastUpdate = QDateTime.currentDateTime()

                if limited or self.__validateCheckSum(fileName):
                    self.__loadRules()
                else:
                    os.unlink(fileName)
        except OSError:
            EricMessageBox.warning(
                None,
                self.tr("Downloading subscription rules"),
                self.tr("""Unable to write to AdBlock file '{0}'.""").file(fileName),
            )
        self.__downloading = None
        reply.deleteLater()

    def __validateCheckSum(self, fileName):
        """
        Private method to check the subscription file's checksum.

        @param fileName name of the file containing the subscription
        @type str
        @return flag indicating a valid file. A file is considered
            valid, if the checksum is OK, the file does not contain a
            checksum (i.e. cannot be checked) or we are using the limited
            EasyList (because we fiddled with the original).
        @rtype bool
        """
        try:
            with open(fileName, "r", encoding="utf-8") as f:
                data = f.read()
        except OSError:
            return False

        match = re.search(self.__checksumRe, data)
        if match:
            expectedChecksum = match.group(1)
        else:
            # consider it as valid
            return True

        # normalize the data
        data = re.sub(r"\r", "", data)  # normalize eol
        data = re.sub(r"\n+", "\n", data)  # remove empty lines
        data = re.sub(self.__checksumRe, "", data)  # remove checksum line

        # calculate checksum
        md5 = hashlib.md5()  # secok
        md5.update(data.encode("utf-8"))
        calculatedChecksum = base64.b64encode(md5.digest()).decode().rstrip("=")
        if calculatedChecksum == expectedChecksum:
            return True
        else:
            res = EricMessageBox.yesNo(
                None,
                self.tr("Downloading subscription rules"),
                self.tr(
                    """<p>AdBlock subscription <b>{0}</b> has a wrong"""
                    """ checksum.<br/>"""
                    """Found: {1}<br/>"""
                    """Calculated: {2}<br/>"""
                    """Use it anyway?</p>"""
                ).format(self.__title, expectedChecksum, calculatedChecksum),
            )
            return res

    def saveRules(self):
        """
        Public method to save the subscription rules.
        """
        fileName = self.rulesFileName()
        if not fileName:
            return

        try:
            with open(fileName, "w", encoding="utf-8") as f:
                if not self.__rules or not self.__rules[0].isHeader():
                    f.write("[Adblock Plus 2.0]\n")
                for rule in self.__rules:
                    f.write(rule.filter() + "\n")
        except OSError:
            EricMessageBox.warning(
                None,
                self.tr("Saving subscription rules"),
                self.tr("""Unable to write to AdBlock file '{0}'.""").format(fileName),
            )

    def rule(self, offset):
        """
        Public method to get a specific rule.

        @param offset offset of the rule
        @type int
        @return requested rule
        @rtype AdBlockRule
        """
        if offset >= len(self.__rules):
            return None

        return self.__rules[offset]

    def allRules(self):
        """
        Public method to get the list of rules.

        @return list of rules
        @rtype list of AdBlockRule
        """
        return self.__rules[:]

    def addRule(self, rule):
        """
        Public method to add a rule.

        @param rule reference to the rule to add
        @type AdBlockRule
        @return offset of the rule
        @rtype int
        """
        self.__rules.append(rule)
        self.rulesChanged.emit()

        return len(self.__rules) - 1

    def removeRule(self, offset):
        """
        Public method to remove a rule given the offset.

        @param offset offset of the rule to remove
        @type int
        """
        if offset < 0 or offset > len(self.__rules):
            return

        del self.__rules[offset]
        self.rulesChanged.emit()

    def replaceRule(self, rule, offset):
        """
        Public method to replace a rule given the offset.

        @param rule reference to the rule to set
        @type AdBlockRule
        @param offset offset of the rule to remove
        @type int
        @return requested rule
        @rtype AdBlockRule
        """
        if offset >= len(self.__rules):
            return None

        self.__rules[offset] = rule
        self.rulesChanged.emit()

        return self.__rules[offset]

    def canEditRules(self):
        """
        Public method to check, if rules can be edited.

        @return flag indicating rules may be edited
        @rtype bool
        """
        return self.__custom

    def canBeRemoved(self):
        """
        Public method to check, if the subscription can be removed.

        @return flag indicating removal is allowed
        @rtype bool
        """
        return not self.__custom and not self.__defaultSubscription

    def setRuleEnabled(self, offset, enabled):
        """
        Public method to enable a specific rule.

        @param offset offset of the rule
        @type int
        @param enabled new enabled state
        @type bool
        @return reference to the changed rule
        @rtype AdBlockRule
        """
        if offset >= len(self.__rules):
            return None

        rule = self.__rules[offset]
        rule.setEnabled(enabled)
        self.rulesEnabledChanged.emit()

        if rule.isCSSRule():
            WebBrowserWindow.mainWindow().reloadUserStyleSheet()

        return rule
