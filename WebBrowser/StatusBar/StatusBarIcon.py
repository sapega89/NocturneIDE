# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the status bar icon base class.
"""

#
# This is modeled after the code found in Qupzilla
# Copyright (C) 2014  David Rosca <nowrep@gmail.com>
#

from eric7.EricWidgets.EricClickableLabel import EricClickableLabel


class StatusBarIcon(EricClickableLabel):
    """
    Class implementing common methods for all status bar icons.
    """

    def __init__(self, window):
        """
        Constructor

        @param window reference to the web browser window
        @type WebBrowserWindow
        """
        super().__init__(window)

        self._window = window

    def _testCurrentPageWebAttribute(self, attr):
        """
        Protected method to test a web attribute on the current page.

        @param attr attribute to test
        @type QWebEngineSettings.WebAttribute
        @return flag indicating the attribute is set
        @rtype bool
        """
        settings = self._currentPageSettings()
        return settings is not None and settings.testAttribute(attr)

    def _setCurrentPageWebAttribute(self, attr, val):
        """
        Protected method to set a web attribute on the current page.

        @param attr attribute to sett
        @type QWebEngineSettings.WebAttribute
        @param val value to be set
        @type bool
        """
        settings = self._currentPageSettings()
        if settings is not None:
            settings.setAttribute(attr, val)

    def _currentPageSettings(self):
        """
        Protected method to get a reference to the web settings of the
        current page.

        @return reference to the web settings object
        @rtype QWebEngineSettings
        """
        view = self._window.currentBrowser()
        if view is None:
            return None

        return view.page().settings()

    def _currentPage(self):
        """
        Protected method to get a reference to the current page.

        @return reference to the current page
        @rtype WebBrowserPage
        """
        view = self._window.currentBrowser()
        if view is None:
            return None

        return view.page()

    def preferencesChanged(self):
        """
        Public method to handle changes of the settings.
        """
        # do nothing
        pass
