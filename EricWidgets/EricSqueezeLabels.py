# -*- coding: utf-8 -*-

# Copyright (c) 2008 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing labels that squeeze their contents to fit the size of the
label.
"""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel


class EricSqueezeLabel(QLabel):
    """
    Class implementing a label that squeezes its contents to fit its size.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent Widget
        @type QWidget
        """
        super().__init__(parent)

        self.__text = ""
        self.__elided = ""

    def paintEvent(self, event):
        """
        Protected method called when some painting is required.

        @param event reference to the paint event
        @type QPaintEvent
        """
        fm = self.fontMetrics()
        pixelLength = fm.horizontalAdvance(self.__text)
        if pixelLength > self.contentsRect().width():
            self.__elided = fm.elidedText(
                self.text(), Qt.TextElideMode.ElideMiddle, self.width()
            )
            super().setText(self.__elided)
        else:
            super().setText(self.__text)
        super().paintEvent(event)

    def setText(self, txt):
        """
        Public method to set the label's text.

        @param txt the text to be shown
        @type str
        """
        self.__text = txt
        super().setText(self.__text)


class EricSqueezeLabelPath(QLabel):
    """
    Class implementing a label showing a file path compacted to fit its size.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent Widget
        @type QWidget
        """
        super().__init__(parent)

        self.__path = ""
        self.__surrounding = "{0}"

    def setSurrounding(self, surrounding):
        """
        Public method to set the surrounding of the path string.

        @param surrounding the a string containing placeholders for the path
        @type str
        """
        self.__surrounding = surrounding
        super().setText(self.__surrounding.format(self.__path))

    def setPath(self, path):
        """
        Public method to set the path of the label.

        @param path path to be shown
        @type str
        """
        self.__path = path
        super().setText(self.__surrounding.format(self.__path))

    def setTextPath(self, surrounding, path):
        """
        Public method to set the surrounding and the path of the label.

        @param surrounding the a string containing placeholders for the path
        @type str
        @param path path to be shown
        @type str
        """
        self.__surrounding = surrounding
        self.__path = path
        super().setText(self.__surrounding.format(self.__path))

    def paintEvent(self, event):
        """
        Protected method called when some painting is required.

        @param event reference to the paint event
        @type QPaintEvent
        """
        if self.length(self.__path) > self.contentsRect().width():
            super().setText(self.__surrounding.format(self.__compactPath()))
        else:
            super().setText(self.__surrounding.format(self.__path))
        super().paintEvent(event)

    def length(self, txt):
        """
        Public method to return the length of a text in pixels.

        @param txt text to calculate the length for after wrapped
        @type str
        @return length of the wrapped text in pixels
        @rtype int
        """
        fm = self.fontMetrics()
        return fm.horizontalAdvance(self.__surrounding.format(txt))

    ############################################################################
    ## Internal path handling methods.
    ############################################################################

    def __compactPath(self):
        """
        Private method to return a compacted path fitting inside the label width.

        @return compacted path
        @rtype str
        """
        width = self.contentsRect().width()
        path = self.__path

        if self.length(path) <= width:
            return path

        ellipsis = "..."

        head, tail = os.path.split(path)
        mid = len(head) // 2
        head1 = head[:mid]
        head2 = head[mid:]
        while head1:
            # head1 is same size as head2 or one shorter
            path = os.path.join("{0}{1}{2}".format(head1, ellipsis, head2), tail)
            if self.length(path) <= width:
                return path
            head1 = head1[:-1]
            head2 = head2[1:]
        path = os.path.join(ellipsis, tail)
        if self.length(path) <= width:
            return path
        while tail:
            path = "{0}{1}".format(ellipsis, tail)
            if self.length(path) <= width:
                return path
            tail = tail[1:]
        return ""
