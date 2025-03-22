# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the AdBlock matcher.
"""

from PyQt6.QtCore import QObject

from .AdBlockRule import AdBlockRule, AdBlockRuleOption
from .AdBlockSearchTree import AdBlockSearchTree


class AdBlockMatcher(QObject):
    """
    Class implementing the AdBlock matcher.
    """

    def __init__(self, manager):
        """
        Constructor

        @param manager reference to the AdBlock manager object
        @type AdBlockManager
        """
        super().__init__(manager)

        self.__manager = manager

        self.__createdRules = []
        self.__networkExceptionRules = []
        self.__networkBlockRules = []
        self.__domainRestrictedCssRules = []
        self.__documentRules = []
        self.__elemhideRules = []

        self.__elementHidingRules = ""
        self.__networkBlockTree = AdBlockSearchTree()
        self.__networkExceptionTree = AdBlockSearchTree()

    def match(self, request, urlDomain, urlString):
        """
        Public method to match a request.

        @param request URL request to be matched
        @type QWebEngineUrlRequestInfo
        @param urlDomain domain of the URL
        @type str
        @param urlString requested URL as a lowercase string
        @type str
        @return reference to the matched rule
        @rtype AdBlockRule
        """
        # exception rules
        if self.__networkExceptionTree.find(request, urlDomain, urlString):
            return None

        for rule in self.__networkExceptionRules:
            if rule.networkMatch(request, urlDomain, urlString):
                return None

        # block rules
        rule = self.__networkBlockTree.find(request, urlDomain, urlString)
        if rule:
            return rule

        for rule in self.__networkBlockRules:
            if rule.networkMatch(request, urlDomain, urlString):
                return rule

        return None

    def adBlockDisabledForUrl(self, url):
        """
        Public method to check, if AdBlock is disabled for the given URL.

        @param url URL to check
        @type QUrl
        @return flag indicating disabled state
        @rtype bool
        """
        return any(rule.urlMatch(url) for rule in self.__documentRules)

    def elemHideDisabledForUrl(self, url):
        """
        Public method to check, if element hiding is disabled for the given
        URL.

        @param url URL to check
        @type QUrl
        @return flag indicating disabled state
        @rtype bool
        """
        if self.adBlockDisabledForUrl(url):
            return True

        return any(rule.urlMatch(url) for rule in self.__elemhideRules)

    def elementHidingRules(self):
        """
        Public method to get the element hiding rules.

        @return element hiding rules
        @rtype str
        """
        return self.__elementHidingRules

    def elementHidingRulesForDomain(self, domain):
        """
        Public method to get the element hiding rules for the given domain.

        @param domain domain name
        @type str
        @return element hiding rules
        @rtype str
        """
        rules = ""
        addedRulesCount = 0

        for rule in self.__domainRestrictedCssRules:
            if not rule.matchDomain(domain):
                continue

            if addedRulesCount == 1000:
                rules += rule.cssSelector()
                rules += "{display:none !important;}\n"
                addedRulesCount = 0
            else:
                rules += rule.cssSelector() + ","
                addedRulesCount += 1

        if addedRulesCount != 0:
            rules = rules[:-1]
            rules += "{display:none !important;}\n"

        return rules

    def update(self):
        """
        Public slot to update the internal state.
        """
        self.clear()

        cssRulesDict = {}
        exceptionCssRules = []

        for subscription in self.__manager.subscriptions():
            if subscription.isEnabled():
                for rule in subscription.allRules():
                    # Don't add internally disabled rules to the cache
                    if rule.isInternalDisabled():
                        continue

                    if rule.isCSSRule():
                        # Only enabled CSS rules are added to the cache because
                        # there is no enabled/disabled check on match. They are
                        # directly embedded to pages.
                        if not rule.isEnabled():
                            continue

                        if rule.isException():
                            exceptionCssRules.append(rule)
                        else:
                            cssRulesDict[rule.cssSelector()] = rule
                    elif rule.isDocument():
                        self.__documentRules.append(rule)
                    elif rule.isElementHiding():
                        self.__elemhideRules.append(rule)
                    elif rule.isException():
                        if not self.__networkExceptionTree.add(rule):
                            self.__networkBlockRules.append(rule)
                    else:
                        if not self.__networkBlockTree.add(rule):
                            self.__networkBlockRules.append(rule)

        for rule in exceptionCssRules:
            try:
                originalRule = cssRulesDict[rule.cssSelector()]
            except KeyError:
                # If there is no such selector, the exception does nothing.
                continue

            copiedRule = AdBlockRule()
            copiedRule.copyFrom(originalRule)
            copiedRule.setOption(AdBlockRuleOption.DomainRestrictedOption)
            copiedRule.addBlockedDomains(rule.allowedDomains())

            cssRulesDict[rule.cssSelector()] = copiedRule
            self.__createdRules.append(copiedRule)

        # Excessive amount of selectors for one CSS rule is not what the
        # rendering engine likes. So split them up by 1.000 selectors.
        hidingRulesCount = 0
        for key in cssRulesDict:
            rule = cssRulesDict[key]

            if rule.isDomainRestricted():
                self.__domainRestrictedCssRules.append(rule)
            elif hidingRulesCount == 1000:
                self.__elementHidingRules += rule.cssSelector()
                self.__elementHidingRules += "{display:none !important;} "
                hidingRulesCount = 0
            else:
                self.__elementHidingRules += rule.cssSelector() + ","
                hidingRulesCount += 1

        if hidingRulesCount != 0:
            self.__elementHidingRules = self.__elementHidingRules[:-1]
            self.__elementHidingRules += "{display:none !important;} "

    def clear(self):
        """
        Public slot to clear the internal structures.
        """
        self.__createdRules = []
        self.__networkExceptionRules = []
        self.__networkBlockRules = []
        self.__domainRestrictedCssRules = []
        self.__documentRules = []
        self.__elemhideRules = []

        self.__elementHidingRules = ""
        self.__networkBlockTree.clear()
        self.__networkExceptionTree.clear()
