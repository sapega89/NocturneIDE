# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to apply AdBlock rules to a web page.
"""

from PyQt6.QtCore import QObject

from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

from ..Tools import Scripts
from ..WebBrowserPage import WebBrowserPage


class AdBlockPage(QObject):
    """
    Class to apply AdBlock rules to a web page.
    """

    def hideBlockedPageEntries(self, page):
        """
        Public method to apply AdBlock rules to a web page.

        @param page reference to the web page
        @type HelpWebPage
        """
        if page is None:
            return

        manager = WebBrowserWindow.adBlockManager()
        if not manager.isEnabled():
            return

        # apply global element hiding rules
        elementHiding = manager.elementHidingRules(page.url())
        if elementHiding:
            script = Scripts.setCss(elementHiding)
            page.runJavaScript(script, WebBrowserPage.SafeJsWorld)

        # apply domain specific element hiding rules
        elementHiding = manager.elementHidingRulesForDomain(page.url())
        if elementHiding:
            script = Scripts.setCss(elementHiding)
            page.runJavaScript(script, WebBrowserPage.SafeJsWorld)
