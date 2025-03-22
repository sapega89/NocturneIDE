# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a proxy style to allow item selection by single/double click or
platform default.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QProxyStyle, QStyle


class EricProxyStyle(QProxyStyle):
    """
    Class implementing a proxy style to allow item selection by single/double click or
    platform default.
    """

    def __init__(self, style=None, itemClickBehavior="default"):
        """
        Constructor

        @param style style object or style name or None for the default native style
            (defaults to None)
        @type QStyle, str or None (optional)
        @param itemClickBehavior string describing the item activation behavior (one of
            "default", "doubleclick" or "singleclick") (defaults to "default")
        @type str (optional)
        """
        super().__init__(style)

        self.__itemClickBehavior = itemClickBehavior

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        """
        Public method returning a style hint for the given widget described by the
        provided style option.

        @param hint style hint to be determined
        @type QStyle.StyleHint
        @param option style option (defaults to None)
        @type QStyleOption (optional)
        @param widget reference to the widget (defaults to None)
        @type QWidget (optional)
        @param returnData data structure to return more data (defaults to None)
        @type QStyleHintReturn (optional)
        @return integer representing the style hint
        @rtype int
        """
        if (
            hint == QStyle.StyleHint.SH_ItemView_ActivateItemOnSingleClick
            and QApplication.keyboardModifiers() == Qt.KeyboardModifier.NoModifier
        ):
            # Activate item with a single click?
            if self.__itemClickBehavior == "singleclick":
                return 1
            elif self.__itemClickBehavior == "doubleclick":
                return 0

        # return the default style hint
        return super().styleHint(
            hint, option=option, widget=widget, returnData=returnData
        )
