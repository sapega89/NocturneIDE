# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a structure to hold the data for a speed dial page.
"""


class Page:
    """
    Class to hold the data for a speed dial page.
    """

    def __init__(self, url="", title="", broken=False):
        """
        Constructor

        @param url URL of the page
        @type str
        @param title title of the page
        @type str
        @param broken flag indicating a broken connection
        @type bool
        """
        self.url = url
        self.title = title
        self.broken = broken

    def __eq__(self, other):
        """
        Special method implementing the equality operator.

        @param other reference to the other page object
        @type Page
        @return flag indicating equality
        @rtype bool
        """
        return self.title == other.title and self.url == other.url

    def isValid(self):
        """
        Public method to check the validity.

        @return flag indicating a valid object
        @rtype bool
        """
        return bool(self.url)
