# -*- coding: utf-8 -*-

# Copyright (c) 2016 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an object to scroll a web page.
"""

#
# This module is based on the Qupzilla frame scroller.
# Copyright (C) 2014  David Rosca <nowrep@gmail.com>
#

import math

from PyQt6.QtCore import QObject, QTimer, pyqtSlot


class FrameScroller(QObject):
    """
    Class implementing a web page scroller object.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__page = None

        self.__lengthX = 0
        self.__lengthY = 0
        self.__divider = 8.0

        self.__timer = QTimer(self)
        self.__timer.setInterval(10)
        self.__timer.timeout.connect(self.__scrollStep)

    def setPage(self, page):
        """
        Public method to set the web page to be scrolled.

        @param page page to be scrolled
        @type WebBrowserPage
        """
        self.__page = page

    def scrollDivider(self):
        """
        Public method to get the current scroll divider value.

        @return scroll divider
        @rtype float
        """
        return self.__divider

    def setScrollDivider(self, divider):
        """
        Public method to set the scroll divider value.

        @param divider scroll divider
        @type float
        """
        self.__divider = divider

    def startScrolling(self, lengthX, lengthY):
        """
        Public method to start scrolling.

        @param lengthX X distance from scroll indicator
        @type int
        @param lengthY Y distance from scroll indicator
        @type int
        """
        self.__lengthX = lengthX
        self.__lengthY = lengthY

        if not self.__lengthX and not self.__lengthY:
            self.__timer.stop()
        elif not self.__timer.isActive():
            self.__timer.start()

    def stopScrolling(self):
        """
        Public method to stop scrolling.
        """
        self.__timer.stop()

    @pyqtSlot()
    def __scrollStep(self):
        """
        Private slot to scroll one step.
        """
        self.__page.scroll(
            math.ceil(self.__lengthX / self.__divider),
            math.ceil(self.__lengthY / self.__divider),
        )
