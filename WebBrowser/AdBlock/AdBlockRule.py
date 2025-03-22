# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the AdBlock rule class.
"""

import re

from enum import IntEnum

from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineCore import QWebEngineUrlRequestInfo

from eric7.EricNetwork import EricTldExtractor


def toSecondLevelDomain(url):
    """
    Module function to get a second level domain from the given URL.

    @param url URL to extract domain from
    @type QUrl
    @return name of second level domain
    @rtype str
    """
    topLevelDomain = EricTldExtractor.instance().tld(url.host())
    urlHost = url.host()

    if not topLevelDomain or not urlHost:
        return ""

    domain = urlHost[: len(urlHost) - len(topLevelDomain)]
    if domain.count(".") == 0:
        return urlHost

    while domain.count(".") != 0:
        domain = domain[domain.find(".") + 1 :]

    return domain + topLevelDomain


class AdBlockRuleType(IntEnum):
    """
    Class implementing the rule type enum.
    """

    CssRule = 0
    DomainMatchRule = 1
    RegExpMatchRule = 2
    StringEndsMatchRule = 3
    StringContainsMatchRule = 4
    MatchAllUrlsRule = 5
    Invalid = 6


class AdBlockRuleOption(IntEnum):
    """
    Class implementing the rule option enum.
    """

    NoOption = 0
    DomainRestrictedOption = 1
    ThirdPartyOption = 2
    ObjectOption = 4
    SubdocumentOption = 8
    XMLHttpRequestOption = 16
    ImageOption = 32
    ScriptOption = 64
    StyleSheetOption = 128
    ObjectSubrequestOption = 256
    PingOption = 512
    MediaOption = 1024
    FontOption = 2048
    OtherOption = 4096

    # Exception only options
    DocumentOption = 8192
    ElementHideOption = 16384


class AdBlockRule:
    """
    Class implementing the AdBlock rule.
    """

    def __init__(self, filterRule="", subscription=None):
        """
        Constructor

        @param filterRule filter string of the rule
        @type str
        @param subscription reference to the subscription object
        @type AdBlockSubscription
        """
        self.__subscription = subscription

        self.__regExp = None
        self.__stringMatchers = []

        self.__blockedDomains = []
        self.__allowedDomains = []

        self.__isEnabled = True
        self.__isException = False
        self.__isInternalDisabled = False
        self.__caseSensitivity = Qt.CaseSensitivity.CaseInsensitive

        self.__type = AdBlockRuleType.StringContainsMatchRule
        self.__options = AdBlockRuleOption.NoOption
        self.__exceptions = AdBlockRuleOption.NoOption

        self.setFilter(filterRule)

    def subscription(self):
        """
        Public method to get the subscription this rule belongs to.

        @return subscription of the rule
        @rtype AdBlockSubscription
        """
        return self.__subscription

    def setSubscription(self, subscription):
        """
        Public method to set the subscription this rule belongs to.

        @param subscription subscription of the rule
        @type AdBlockSubscription
        """
        self.__subscription = subscription

    def filter(self):
        """
        Public method to get the rule filter string.

        @return rule filter string
        @rtype str
        """
        return self.__filter

    def setFilter(self, filterRule):
        """
        Public method to set the rule filter string.

        @param filterRule rule filter string
        @type str
        """
        self.__filter = filterRule
        self.__parseFilter()

    def __parseFilter(self):
        """
        Private method to parse the filter pattern.
        """
        parsedLine = self.__filter

        # empty rule or just a comment
        if not parsedLine.strip() or parsedLine.startswith("!"):
            self.__isEnabled = False
            self.__isInternalDisabled = True
            self.__type = AdBlockRuleType.Invalid
            return

        # CSS element hiding rule
        if "##" in parsedLine or "#@#" in parsedLine:
            self.__type = AdBlockRuleType.CssRule
            pos = parsedLine.find("#")

            # domain restricted rule
            if not parsedLine.startswith("##"):
                domains = parsedLine[:pos]
                self.__parseDomains(domains, ",")

            self.__isException = parsedLine[pos + 1] == "@"
            if self.__isException:
                self.__matchString = parsedLine[pos + 3 :]
            else:
                self.__matchString = parsedLine[pos + 2 :]

            # CSS rule cannot have more options -> stop parsing
            return

        # Exception always starts with @@
        if parsedLine.startswith("@@"):
            self.__isException = True
            parsedLine = parsedLine[2:]

        # Parse all options following '$' character
        optionsIndex = parsedLine.find("$")
        if optionsIndex >= 0:
            options = [opt for opt in parsedLine[optionsIndex + 1 :].split(",") if opt]

            handledOptions = 0
            for option in options:
                if option.startswith("domain="):
                    self.__parseDomains(option[7:], "|")
                    handledOptions += 1
                elif option == "match-case":
                    self.__caseSensitivity = Qt.CaseSensitivity.CaseSensitive
                    handledOptions += 1
                elif option.endswith("third-party"):
                    self.setOption(AdBlockRuleOption.ThirdPartyOption)
                    self.__setException(
                        AdBlockRuleOption.ThirdPartyOption, option.startswith("~")
                    )
                    handledOptions += 1
                elif option.endswith("object"):
                    self.setOption(AdBlockRuleOption.ObjectOption)
                    self.__setException(
                        AdBlockRuleOption.ObjectOption, option.startswith("~")
                    )
                    handledOptions += 1
                elif option.endswith("subdocument"):
                    self.setOption(AdBlockRuleOption.SubdocumentOption)
                    self.__setException(
                        AdBlockRuleOption.SubdocumentOption, option.startswith("~")
                    )
                    handledOptions += 1
                elif option.endswith("xmlhttprequest"):
                    self.setOption(AdBlockRuleOption.XMLHttpRequestOption)
                    self.__setException(
                        AdBlockRuleOption.XMLHttpRequestOption, option.startswith("~")
                    )
                    handledOptions += 1
                elif option.endswith("image"):
                    self.setOption(AdBlockRuleOption.ImageOption)
                    self.__setException(
                        AdBlockRuleOption.ImageOption, option.startswith("~")
                    )
                elif option.endswith("script"):
                    self.setOption(AdBlockRuleOption.ScriptOption)
                    self.__setException(
                        AdBlockRuleOption.ScriptOption, option.startswith("~")
                    )
                elif option.endswith("stylesheet"):
                    self.setOption(AdBlockRuleOption.StyleSheetOption)
                    self.__setException(
                        AdBlockRuleOption.StyleSheetOption, option.startswith("~")
                    )
                elif option.endswith("object-subrequest"):
                    self.setOption(AdBlockRuleOption.ObjectSubrequestOption)
                    self.__setException(
                        AdBlockRuleOption.ObjectSubrequestOption, option.startswith("~")
                    )
                elif option.endswith("ping"):
                    self.setOption(AdBlockRuleOption.PingOption)
                    self.__setException(
                        AdBlockRuleOption.PingOption, option.startswith("~")
                    )
                elif option.endswith("media"):
                    self.setOption(AdBlockRuleOption.MediaOption)
                    self.__setException(
                        AdBlockRuleOption.MediaOption, option.startswith("~")
                    )
                elif option.endswith("font"):
                    self.setOption(AdBlockRuleOption.FontOption)
                    self.__setException(
                        AdBlockRuleOption.FontOption, option.startswith("~")
                    )
                elif option.endswith("other"):
                    self.setOption(AdBlockRuleOption.OtherOption)
                    self.__setException(
                        AdBlockRuleOption.OtherOption, option.startswith("~")
                    )
                elif option == "document" and self.__isException:
                    self.setOption(AdBlockRuleOption.DocumentOption)
                    handledOptions += 1
                elif option == "elemhide" and self.__isException:
                    self.setOption(AdBlockRuleOption.ElementHideOption)
                    handledOptions += 1
                elif option == "collapse":
                    # Hiding placeholders of blocked elements is enabled by
                    # default
                    handledOptions += 1

            # If we don't handle all options, it's safer to just disable
            # this rule
            if handledOptions != len(options):
                self.__isInternalDisabled = True
                self.__type = AdBlockRuleType.Invalid
                return

            parsedLine = parsedLine[:optionsIndex]

        # Rule is classic regexp
        if parsedLine.startswith("/") and parsedLine.endswith("/"):
            parsedLine = parsedLine[1:-1]
            self.__type = AdBlockRuleType.RegExpMatchRule
            if self.__caseSensitivity:
                self.__regExp = re.compile(parsedLine)
            else:
                self.__regExp = re.compile(parsedLine, re.IGNORECASE)
            self.__stringMatchers = self.__parseRegExpFilter(parsedLine)
            return

        # Remove starting / ending wildcards (*)
        if parsedLine.startswith("*"):
            parsedLine = parsedLine[1:]
        if parsedLine.endswith("*"):
            parsedLine = parsedLine[:-1]

        # Fast string matching for domain here
        if self.__filterIsOnlyDomain(parsedLine):
            parsedLine = parsedLine[2:-1]
            self.__type = AdBlockRuleType.DomainMatchRule
            self.__matchString = parsedLine
            return

        # If rule contains '|' only at the end, string matching can be used
        if self.__filterIsOnlyEndsMatch(parsedLine):
            parsedLine = parsedLine[:-1]
            self.__type = AdBlockRuleType.StringEndsMatchRule
            self.__matchString = parsedLine
            return

        # If there is still a wildcard (*) or separator (^) or (|),
        # the rule must be modified to comply with re.
        if "*" in parsedLine or "^" in parsedLine or "|" in parsedLine:
            self.__type = AdBlockRuleType.RegExpMatchRule
            pattern = self.__convertPatternToRegExp(parsedLine)
            if self.__caseSensitivity:
                self.__regExp = re.compile(pattern)
            else:
                self.__regExp = re.compile(pattern, re.IGNORECASE)
            self.__stringMatchers = self.__parseRegExpFilter(parsedLine)
            return

        # This rule matches all URLs
        if len(parsedLine) == 0:
            if self.__options == AdBlockRuleOption.NoOption:
                self.__isInternalDisabled = True
                self.__type = AdBlockRuleType.Invalid
                return

            self.__type = AdBlockRuleType.MatchAllUrlsRule
            return

        # no regexp required
        self.__type = AdBlockRuleType.StringContainsMatchRule
        self.__matchString = parsedLine

    def __parseDomains(self, domains, separator):
        """
        Private method to parse a string with a domain list.

        @param domains list of domains
        @type str
        @param separator separator character used by the list
        @type str
        """
        domainsList = [d for d in domains.split(separator) if d]

        for domain in domainsList:
            if not domain:
                continue
            if domain.startswith("~"):
                self.__blockedDomains.append(domain[1:])
            else:
                self.__allowedDomains.append(domain)

        if bool(self.__blockedDomains) or bool(self.__allowedDomains):
            self.setOption(AdBlockRuleOption.DomainRestrictedOption)

    def networkMatch(self, request, domain, encodedUrl):
        """
        Public method to check the rule for a match.

        @param request reference to the network request
        @type QWebEngineUrlRequestInfo
        @param domain domain name
        @type str
        @param encodedUrl string encoded URL to be checked
        @type str
        @return flag indicating a match
        @rtype bool
        """
        if (
            self.__type == AdBlockRuleType.CssRule
            or not self.__isEnabled
            or self.__isInternalDisabled
        ):
            return False

        matched = self.__stringMatch(domain, encodedUrl)

        if matched:
            # check domain restrictions
            if self.__hasOption(
                AdBlockRuleOption.DomainRestrictedOption
            ) and not self.matchDomain(request.firstPartyUrl().host()):
                return False

            # check third-party restrictions
            if self.__hasOption(
                AdBlockRuleOption.ThirdPartyOption
            ) and not self.matchThirdParty(request):
                return False

            # check object restrictions
            if self.__hasOption(
                AdBlockRuleOption.ObjectOption
            ) and not self.matchObject(request):
                return False

            # check subdocument restrictions
            if self.__hasOption(
                AdBlockRuleOption.SubdocumentOption
            ) and not self.matchSubdocument(request):
                return False

            # check xmlhttprequest restriction
            if self.__hasOption(
                AdBlockRuleOption.XMLHttpRequestOption
            ) and not self.matchXmlHttpRequest(request):
                return False

            # check image restriction
            if self.__hasOption(AdBlockRuleOption.ImageOption) and not self.matchImage(
                request
            ):
                return False

            # check script restriction
            if self.__hasOption(
                AdBlockRuleOption.ScriptOption
            ) and not self.matchScript(request):
                return False

            # check stylesheet restriction
            if self.__hasOption(
                AdBlockRuleOption.StyleSheetOption
            ) and not self.matchStyleSheet(request):
                return False

            # check object-subrequest restriction
            if self.__hasOption(
                AdBlockRuleOption.ObjectSubrequestOption
            ) and not self.matchObjectSubrequest(request):
                return False

            # check ping restriction
            if self.__hasOption(AdBlockRuleOption.PingOption) and not self.matchPing(
                request
            ):
                return False

            # check media restriction
            if self.__hasOption(AdBlockRuleOption.MediaOption) and not self.matchMedia(
                request
            ):
                return False

            # check font restriction
            if self.__hasOption(AdBlockRuleOption.FontOption) and not self.matchFont(
                request
            ):
                return False

        return matched

    def urlMatch(self, url):
        """
        Public method to check an URL against the rule.

        @param url URL to check
        @type QUrl
        @return flag indicating a match
        @rtype bool
        """
        if not self.__hasOption(
            AdBlockRuleOption.DocumentOption
        ) and not self.__hasOption(AdBlockRuleOption.ElementHideOption):
            return False

        encodedUrl = bytes(url.toEncoded()).decode()
        domain = url.host()
        return self.__stringMatch(domain, encodedUrl)

    def __stringMatch(self, domain, encodedUrl):
        """
        Private method to match a domain string.

        @param domain domain to match
        @type str
        @param encodedUrl URL in encoded form
        @type str
        @return flag indicating a match
        @rtype bool
        """
        matched = False

        if self.__type == AdBlockRuleType.StringContainsMatchRule:
            if self.__caseSensitivity == Qt.CaseSensitivity.CaseInsensitive:
                matched = self.__matchString.lower() in encodedUrl.lower()
            else:
                matched = self.__matchString in encodedUrl
        elif self.__type == AdBlockRuleType.DomainMatchRule:
            matched = self.__isMatchingDomain(domain, self.__matchString)
        elif self.__type == AdBlockRuleType.StringEndsMatchRule:
            if self.__caseSensitivity == Qt.CaseSensitivity.CaseInsensitive:
                matched = encodedUrl.lower().endswith(self.__matchString.lower())
            else:
                matched = encodedUrl.endswith(self.__matchString)
        elif self.__type == AdBlockRuleType.RegExpMatchRule:
            if not self.__isMatchingRegExpStrings(encodedUrl):
                matched = False
            else:
                matched = self.__regExp.search(encodedUrl) is not None
        elif self.__type == AdBlockRuleType.MatchAllUrlsRule:
            matched = True

        return matched

    def matchDomain(self, domain):
        """
        Public method to match a domain.

        @param domain domain name to check
        @type str
        @return flag indicating a match
        @rtype bool
        """
        if not self.__isEnabled:
            return False

        if not self.__hasOption(AdBlockRuleOption.DomainRestrictedOption):
            return True

        if len(self.__blockedDomains) == 0:
            return any(
                self.__isMatchingDomain(domain, dom) for dom in self.__allowedDomains
            )
        elif len(self.__allowedDomains) == 0:
            return all(
                not self.__isMatchingDomain(domain, dom)
                for dom in self.__blockedDomains
            )
        else:
            return all(
                not self.__isMatchingDomain(domain, dom)
                for dom in self.__blockedDomains
            ) and any(
                self.__isMatchingDomain(domain, dom) for dom in self.__allowedDomains
            )

    def matchThirdParty(self, req):
        """
        Public method to match a third-party rule.

        @param req request object to check
        @type QWebEngineUrlRequestInfo
        @return flag indicating a match
        @rtype boolean
        """
        # Third-party matching should be performed on second-level domains
        firstPartyHost = toSecondLevelDomain(req.firstPartyUrl())
        host = toSecondLevelDomain(req.requestUrl())

        match = firstPartyHost != host

        if self.__hasException(AdBlockRuleOption.ThirdPartyOption):
            return not match
        else:
            return match

    def matchObject(self, req):
        """
        Public method to match an object rule.

        @param req request object to check
        @type QWebEngineUrlRequestInfo
        @return flag indicating a match
        @rtype bool
        """
        match = (
            req.resourceType()
            == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeObject
        )

        if self.__hasException(AdBlockRuleOption.ObjectOption):
            return not match
        else:
            return match

    def matchSubdocument(self, req):
        """
        Public method to match a sub-document rule.

        @param req request object to check
        @type QWebEngineUrlRequestInfo
        @return flag indicating a match
        @rtype boolean
        """
        match = (
            req.resourceType()
            == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeSubFrame
        )

        if self.__hasException(AdBlockRuleOption.SubdocumentOption):
            return not match
        else:
            return match

    def matchXmlHttpRequest(self, req):
        """
        Public method to match a XmlHttpRequest rule.

        @param req request object to check
        @type QWebEngineUrlRequestInfo
        @return flag indicating a match
        @rtype bool
        """
        match = (
            req.resourceType() == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeXhr
        )

        if self.__hasException(AdBlockRuleOption.XMLHttpRequestOption):
            return not match
        else:
            return match

    def matchImage(self, req):
        """
        Public method to match an Image rule.

        @param req request object to check
        @type QWebEngineUrlRequestInfo
        @return flag indicating a match
        @rtype bool
        """
        match = (
            req.resourceType()
            == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeImage
        )

        if self.__hasException(AdBlockRuleOption.ImageOption):
            return not match
        else:
            return match

    def matchScript(self, req):
        """
        Public method to match a Script rule.

        @param req request object to check
        @type QWebEngineUrlRequestInfo
        @return flag indicating a match
        @rtype bool
        """
        match = (
            req.resourceType()
            == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeScript
        )

        if self.__hasException(AdBlockRuleOption.ScriptOption):
            return not match
        else:
            return match

    def matchStyleSheet(self, req):
        """
        Public method to match a StyleSheet rule.

        @param req request object to check
        @type QWebEngineUrlRequestInfo
        @return flag indicating a match
        @rtype bool
        """
        match = (
            req.resourceType()
            == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeStylesheet
        )

        if self.__hasException(AdBlockRuleOption.StyleSheetOption):
            return not match
        else:
            return match

    def matchObjectSubrequest(self, req):
        """
        Public method to match an Object Subrequest rule.

        @param req request object to check
        @type QWebEngineUrlRequestInfo
        @return flag indicating a match
        @rtype boolean
        """
        match = (
            req.resourceType()
            == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeSubResource
        )
        match = match or (
            req.resourceType()
            == QWebEngineUrlRequestInfo.ResourceType.ResourceTypePluginResource
        )

        if self.__objectSubrequestException:
            return not match
        else:
            return match

    def matchPing(self, req):
        """
        Public method to match a Ping rule.

        @param req request object to check
        @type QWebEngineUrlRequestInfo
        @return flag indicating a match
        @rtype bool
        """
        match = (
            req.resourceType() == QWebEngineUrlRequestInfo.ResourceType.ResourceTypePing
        )

        if self.__hasException(AdBlockRuleOption.PingOption):
            return not match
        else:
            return match

    def matchMedia(self, req):
        """
        Public method to match a Media rule.

        @param req request object to check
        @type QWebEngineUrlRequestInfo
        @return flag indicating a match
        @rtype bool
        """
        match = (
            req.resourceType()
            == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMedia
        )

        if self.__hasException(AdBlockRuleOption.MediaOption):
            return not match
        else:
            return match

    def matchFont(self, req):
        """
        Public method to match a Font rule.

        @param req request object to check
        @type QWebEngineUrlRequestInfo
        @return flag indicating a match
        @rtype bool
        """
        match = (
            req.resourceType()
            == QWebEngineUrlRequestInfo.ResourceType.ResourceTypeFontResource
        )

        if self.__hasException(AdBlockRuleOption.FontOption):
            return not match
        else:
            return match

    def matchOther(self, req):
        """
        Public method to match any other rule.

        @param req request object to check
        @type QWebEngineUrlRequestInfo
        @return flag indicating a match
        @rtype bool
        """
        match = req.resourceType() in [
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeSubResource,
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeWorker,
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeSharedWorker,
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeServiceWorker,
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypePrefetch,
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeFavicon,
            QWebEngineUrlRequestInfo.ResourceType.ResourceTypeUnknown,
        ]

        if self.__hasException(AdBlockRuleOption.OtherOption):
            return not match
        else:
            return match

    def isException(self):
        """
        Public method to check, if the rule defines an exception.

        @return flag indicating an exception
        @rtype bool
        """
        return self.__isException

    def setException(self, exception):
        """
        Public method to set the rule's exception flag.

        @param exception flag indicating an exception rule
        @type bool
        """
        self.__isException = exception

    def isEnabled(self):
        """
        Public method to check, if the rule is enabled.

        @return flag indicating enabled state
        @rtype bool
        """
        return self.__isEnabled

    def setEnabled(self, enabled):
        """
        Public method to set the rule's enabled state.

        @param enabled flag indicating the new enabled state
        @type bool
        """
        self.__isEnabled = enabled

    def isCSSRule(self):
        """
        Public method to check, if the rule is a CSS rule.

        @return flag indicating a CSS rule
        @rtype bool
        """
        return self.__type == AdBlockRuleType.CssRule

    def cssSelector(self):
        """
        Public method to get the CSS selector of the rule.

        @return CSS selector
        @rtype str
        """
        return self.__matchString

    def isDocument(self):
        """
        Public method to check, if this is a document rule.

        @return flag indicating a document rule
        @rtype bool
        """
        return self.__hasOption(AdBlockRuleOption.DocumentOption)

    def isElementHiding(self):
        """
        Public method to check, if this is an element hiding rule.

        @return flag indicating an element hiding rule
        @rtype bool
        """
        return self.__hasOption(AdBlockRuleOption.ElementHideOption)

    def isDomainRestricted(self):
        """
        Public method to check, if this rule is restricted by domain.

        @return flag indicating a domain restriction
        @rtype bool
        """
        return self.__hasOption(AdBlockRuleOption.DomainRestrictedOption)

    def isComment(self):
        """
        Public method to check, if this is a comment.

        @return flag indicating a comment
        @rtype bool
        """
        return self.__filter.startswith("!")

    def isHeader(self):
        """
        Public method to check, if this is a header.

        @return flag indicating a header
        @rtype bool
        """
        return self.__filter.startswith("[Adblock")

    def isSlow(self):
        """
        Public method to check, if this is a slow rule.

        @return flag indicating a slow rule
        @rtype bool
        """
        return self.__regExp is not None

    def isInternalDisabled(self):
        """
        Public method to check, if this rule was disabled internally.

        @return flag indicating an internally disabled rule
        @rtype bool
        """
        return self.__isInternalDisabled

    def __convertPatternToRegExp(self, wildcardPattern):
        """
        Private method to convert a wildcard pattern to a regular expression.

        @param wildcardPattern string containing the wildcard pattern
        @type str
        @return string containing a regular expression
        @rtype string
        """
        pattern = wildcardPattern

        # remove multiple wildcards
        pattern = re.sub(r"\*+", "*", pattern)
        # remove anchors following separator placeholder
        pattern = re.sub(r"\^\|$", "^", pattern)
        # remove leading wildcards
        pattern = re.sub(r"^(\*)", "", pattern)
        # remove trailing wildcards
        pattern = re.sub(r"(\*)$", "", pattern)
        # escape special symbols
        pattern = re.sub(r"(\W)", r"\\\1", pattern)
        # process extended anchor at expression start
        pattern = re.sub(r"^\\\|\\\|", r"^[\\w\-]+:\/+(?!\/)(?:[^\/]+\.)?", pattern)
        # process separator placeholders
        pattern = re.sub(r"\\\^", r"(?:[^\\w\\d\-.%]|$)", pattern)
        # process anchor at expression start
        pattern = re.sub(r"^\\\|", "^", pattern)
        # process anchor at expression end
        pattern = re.sub(r"\\\|$", "$", pattern)
        # replace wildcards by .*
        pattern = re.sub(r"\\\*", ".*", pattern)

        return pattern

    def __hasOption(self, opt):
        """
        Private method to check, if the given option has been set.

        @param opt option to check for
        @type AdBlockRuleOption
        @return flag indicating the state of the option
        @rtype bool
        """
        return bool(self.__options & opt)

    def setOption(self, opt):
        """
        Public method to set the given option.

        @param opt option to be set
        @type AdBlockRuleOption
        """
        self.__options |= opt

    def __hasException(self, opt):
        """
        Private method to check, if the given option has been set as an
        exception.

        @param opt option to check for
        @type AdBlockRuleOption
        @return flag indicating the exception state of the option
        @rtype bool
        """
        return bool(self.__exceptions & opt)

    def __setException(self, opt, on):
        """
        Private method to set the given option as an exception.

        @param opt option to be set
        @type AdBlockRuleOption
        @param on flag indicating to set or unset the exception
        @type bool
        """
        if on:
            self.__exceptions |= opt
        else:
            self.__exceptions &= ~opt

    def __filterIsOnlyDomain(self, filterString):
        """
        Private method to check, if the given filter is a domain only filter.

        @param filterString filter string to be checked
        @type str
        @return flag indicating a domain only filter
        @rtype bool
        """
        if not filterString.endswith("^") or not filterString.startswith("||"):
            return False

        return all(
            filterChar not in ["/", ":", "?", "=", "&", "*"]
            for filterChar in filterString
        )

    def __filterIsOnlyEndsMatch(self, filterString):
        """
        Private method to check, if the given filter is to match against the
        end of a string.

        @param filterString filter string to be checked
        @type str
        @return flag indicating a end of string match filter
        @rtype bool
        """
        for index, filterChar in enumerate(filterString):  # noqa: Y111
            if filterChar in ["^", "*"]:
                return False
            elif filterChar == "|":
                return index == len(filterString) - 1

        return False

    def __isMatchingDomain(self, domain, filterString):
        """
        Private method to check, if a given domain matches the given filter
        string.

        @param domain domain to be checked
        @type str
        @param filterString filter string to check against
        @type str
        @return flag indicating a match
        @rtype bool
        """
        if filterString == domain:
            return True

        if not domain.endswith(filterString):
            return False

        index = domain.find(filterString)

        return bool(index > 0 and domain[index - 1] == ".")

    def __isMatchingRegExpStrings(self, url):
        """
        Private method to check the given URL against the fixed parts of
        the regexp.

        @param url URL to be checked
        @type str
        @return flag indicating a match
        @rtype bool
        """
        if self.__regExp is not None:
            return all(matcher in url for matcher in self.__stringMatchers)

        return True

    def __parseRegExpFilter(self, filterString):
        """
        Private method to split the given regular expression into strings that
        can be used with 'in'.

        @param filterString regexp filter string to be parsed
        @type str
        @return fixed string parts of the filter
        @rtype list of str
        """
        matchers = []

        startPos = -1
        for index in range(len(filterString)):
            filterChar = filterString[index]
            if filterChar in ["|", "*", "^"]:
                sub = filterString[startPos:index]
                if len(sub) > 1:
                    matchers.append(sub)
                startPos = index + 1

        sub = filterString[startPos:]
        if len(sub) > 1:
            matchers.append(sub)

        return list(set(matchers))

    def ruleType(self):
        """
        Public method to get the rule type.

        @return rule type
        @rtype AdBlockRuleType
        """
        return self.__type

    def ruleOptions(self):
        """
        Public method to get the rule options.

        @return rule options
        @rtype AdBlockRuleOption
        """
        return self.__options

    def ruleExceptions(self):
        """
        Public method to get the rule exceptions.

        @return rule exceptions
        @rtype AdBlockRuleOption
        """
        return self.__exceptions

    def matchString(self):
        """
        Public method to get the match string.

        @return match string
        @rtype str
        """
        return self.__matchString

    def caseSensitivity(self):
        """
        Public method to get the case sensitivity.

        @return case sensitivity
        @rtype Qt.CaseSensitivity
        """
        return self.__caseSensitivity

    def allowedDomains(self):
        """
        Public method to get a copy of the list of allowed domains.

        @return list of allowed domains
        @rtype list of str
        """
        return self.__allowedDomains[:]

    def blockedDomains(self):
        """
        Public method to get a copy of the list of blocked domains.

        @return list of blocked domains
        @rtype list of str
        """
        return self.__blockedDomains[:]

    def addBlockedDomains(self, domains):
        """
        Public method to add to the list of blocked domains.

        @param domains list of domains to be added
        @type str or list of str
        """
        if isinstance(domains, list):
            self.__blockedDomains.extend(domains)
        else:
            self.__blockedDomains.append(domains)

    def getRegExpAndMatchers(self):
        """
        Public method to get the regular expression and associated string
        matchers.

        @return tuple containing the regular expression and the list of
            string matchers
        @rtype tuple of (re.Pattern, list of str)
        """
        if self.__regExp is not None:
            return (re.compile(self.__regExp.pattern), self.__stringMatchers[:])
        else:
            return (None, [])

    def copyFrom(self, other):
        """
        Public method to copy another AdBlock rule.

        @param other reference to the AdBlock rule to copy from
        @type AdBlockRule
        """
        self.__subscription = other.subscription()
        self.__type = other.ruleType()
        self.__options = other.ruleOptions()
        self.__exceptions = other.ruleExceptions()
        self.__filter = other.filter()
        self.__matchString = other.matchString()
        self.__caseSensitivity = other.caseSensitivity()
        self.__isEnabled = other.isEnabled()
        self.__isException = other.isException()
        self.__isInternalDisabled = other.isInternalDisabled()
        self.__allowedDomains = other.allowedDomains()
        self.__blockedDomains = other.blockedDomains()
        self.__regExp, self.__stringMatchers = other.getRegExpAndMatchers()
