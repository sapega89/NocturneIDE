# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the AdBlock search tree.
"""

from dataclasses import dataclass, field

from .AdBlockRule import AdBlockRule, AdBlockRuleType


@dataclass
class AdBlockSearchTreeNode:
    """
    Class implementing the AdBlock search tree node.
    """

    char: str = ""
    rule: AdBlockRule = None
    children: dict = field(default_factory=dict)


class AdBlockSearchTree:
    """
    Class implementing the AdBlock search tree.
    """

    def __init__(self):
        """
        Constructor
        """
        self.__root = AdBlockSearchTreeNode()

    def clear(self):
        """
        Public method to clear the search tree.
        """
        self.__deleteNode(self.__root)
        self.__root = AdBlockSearchTreeNode()

    def add(self, rule):
        """
        Public method to add a rule to the search tree.

        @param rule rule to be added
        @type AdBlockRule
        @return flag indicating a successful addition
        @rtype bool
        """
        if rule.ruleType() != AdBlockRuleType.StringContainsMatchRule:
            return False

        filterString = rule.matchString()

        if len(filterString) <= 0:
            return False

        node = self.__root

        for filterChar in filterString:
            try:
                nextNode = node.children[filterChar]
            except KeyError:
                nextNode = AdBlockSearchTreeNode()
                nextNode.char = filterChar
                node.children[filterChar] = nextNode
            node = nextNode

        node.rule = rule

        return True

    def find(self, request, domain, urlString):
        """
        Public method to find a matching rule.

        @param request URL request to be matched
        @type QWebEngineUrlRequestInfo
        @param domain domain of the URL
        @type str
        @param urlString requested URL as a lowercase string
        @type str
        @return reference to the matched rule
        @rtype AdBlockRule
        """
        length = len(urlString)

        if length <= 0:
            return None

        for index in range(length):
            rule = self.__prefixSearch(
                request, domain, urlString, urlString[index:], length - index
            )
            if rule:
                return rule

        return None

    def __deleteNode(self, node):
        """
        Private method to delete a search tree node.

        @param node reference to the node to be deleted
        @type AdBlockSearchTreeNode
        """
        if not node:
            return

        for key in node.children:
            self.__deleteNode(node.children[key])

        node.children = {}
        node = None

    def __prefixSearch(self, request, domain, urlString, string, length):
        """
        Private method to perform a prefix search.

        @param request URL request to be matched
        @type QWebEngineUrlRequestInfo
        @param domain domain of the URL
        @type str
        @param urlString requested URL as a lowercase string
        @type str
        @param string prefix string to search for
        @type str
        @param length length to be considered
        @type int
        @return reference to the matched rule
        @rtype AdBlockRule
        """
        if length <= 0:
            return None

        char = string[0]

        try:
            node = self.__root.children[char]
        except KeyError:
            return None

        for char in string[1:]:
            if node.rule and node.rule.networkMatch(request, domain, urlString):
                return node.rule

            try:
                node = node.children[char]
            except KeyError:
                return None

        if node.rule and node.rule.networkMatch(request, domain, urlString):
            return node.rule

        return None
