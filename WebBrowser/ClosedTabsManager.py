# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to manage closed tabs.
"""

from dataclasses import dataclass, field

from PyQt6.QtCore import QObject, QUrl, pyqtSignal


@dataclass
class ClosedTab:
    """
    Class implementing a structure to store data about a closed tab.
    """

    url: QUrl = field(default_factory=QUrl)
    title: str = ""
    position: int = -1


class ClosedTabsManager(QObject):
    """
    Class implementing a manager for closed tabs.

    @signal closedTabAvailable(boolean) emitted to signal a change of
        availability of closed tabs
    """

    closedTabAvailable = pyqtSignal(bool)

    def __init__(self):
        """
        Constructor
        """
        super().__init__()

        self.__closedTabs = []

    def recordBrowser(self, browser, position):
        """
        Public method to record the data of a browser about to be closed.

        @param browser reference to the browser to be closed
        @type WebBrowserView
        @param position index of the tab to be closed
        @type int
        """
        from eric7.WebBrowser.WebBrowserWindow import WebBrowserWindow

        if WebBrowserWindow.isPrivate():
            return

        if browser.url().isEmpty():
            return

        tab = ClosedTab(browser.url(), browser.title(), position)
        self.__closedTabs.insert(0, tab)
        self.closedTabAvailable.emit(True)

    def getClosedTabAt(self, index):
        """
        Public method to get the indexed closed tab.

        @param index index of the tab to return
        @type int
        @return requested tab
        @rtype ClosedTab
        """
        tab = (
            self.__closedTabs.pop(index)
            if (len(self.__closedTabs) > 0 and len(self.__closedTabs) > index)
            else ClosedTab()
        )
        self.closedTabAvailable.emit(len(self.__closedTabs) > 0)
        return tab

    def isClosedTabAvailable(self):
        """
        Public method to check for closed tabs.

        @return flag indicating the availability of closed tab data
        @rtype bool
        """
        return len(self.__closedTabs) > 0

    def clearList(self):
        """
        Public method to clear the list of closed tabs.
        """
        self.__closedTabs = []
        self.closedTabAvailable.emit(False)

    def allClosedTabs(self):
        """
        Public method to get a list of all closed tabs.

        @return list of closed tabs
        @rtype list of ClosedTab
        """
        return self.__closedTabs
