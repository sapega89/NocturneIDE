# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to stack url bars.
"""

from PyQt6.QtWidgets import QSizePolicy, QStackedWidget


class StackedUrlBar(QStackedWidget):
    """
    Class implementing a widget to stack URL bars.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        sizePolicy = QSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        sizePolicy.setHorizontalStretch(6)
        sizePolicy.setVerticalStretch(0)
        self.setSizePolicy(sizePolicy)
        self.setMinimumSize(200, 22)

    def currentUrlBar(self):
        """
        Public method to get a reference to the current URL bar.

        @return reference to the current URL bar
        @rtype UrlBar
        """
        return self.urlBar(self.currentIndex())

    def urlBar(self, index):
        """
        Public method to get a reference to the URL bar for a given index.

        @param index index of the url bar
        @type int
        @return reference to the URL bar for the given index
        @rtype UrlBar
        """
        return self.widget(index)

    def moveBar(self, from_, to_):
        """
        Public slot to move an URL bar.

        @param from_ index of URL bar to be moved
        @type int
        @param to_ index to move the URL bar to
        @type int
        """
        fromBar = self.widget(from_)
        self.removeWidget(fromBar)
        self.insertWidget(to_, fromBar)

    def urlBars(self):
        """
        Public method to get a list of references to all URL bars.

        @return list of references to URL bars
        @rtype list of UrlBar
        """
        urlBars = []
        for index in range(self.count()):
            urlBars.append(self.widget(index))
        return urlBars
