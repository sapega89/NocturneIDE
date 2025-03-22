# -*- coding: utf-8 -*-

# Copyright (c) 2010 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a spinbox with textual entries.
"""

from PyQt6.QtWidgets import QSpinBox


class EricTextSpinBox(QSpinBox):
    """
    Class implementing a spinbox with textual entries.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__items = []

        self.setMinimum(0)
        self.setMaximum(0)

    def addItem(self, txt, data=None):
        """
        Public method to add an item with item data.

        @param txt text to be shown
        @type str
        @param data associated data
        @type Any
        """
        self.__items.append((txt, data))
        self.setMaximum(len(self.__items) - 1)

    def itemData(self, index):
        """
        Public method to retrieve the data associated with an item.

        @param index index of the item
        @type int
        @return associated data
        @rtype Any
        """
        try:
            return self.__items[index][1]
        except IndexError:
            return None

    def currentIndex(self):
        """
        Public method to retrieve the current index.

        @return current index
        @rtype int
        """
        return self.value()

    def textFromValue(self, value):
        """
        Public method to convert a value to text.

        @param value value to be converted
        @type int
        @return text for the given value
        @rtype str
        """
        try:
            return self.__items[value][0]
        except IndexError:
            return ""

    def valueFromText(self, txt):
        """
        Public method to convert a text to a value.

        @param txt text to be converted
        @type str
        @return value for the given text
        @rtype int
        """
        for index in range(len(self.__items)):
            if self.__items[index][0] == txt:
                return index

        return self.minimum()
