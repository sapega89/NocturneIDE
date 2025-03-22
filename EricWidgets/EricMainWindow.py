# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a main window class with styling support.
"""

from PyQt6.QtWidgets import QApplication, QMainWindow, QStyleFactory

from .EricApplication import ericApp
from .EricProxyStyle import EricProxyStyle


class EricMainWindow(QMainWindow):
    """
    Class implementing a main window with styling support.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.defaultStyleName = QApplication.style().objectName()

    def setStyle(self, styleName, styleSheetFile, itemClickBehavior="default"):
        """
        Public method to set the style of the interface.

        @param styleName name of the style to set
        @type str
        @param styleSheetFile name of a style sheet file to read to overwrite
            defaults of the given style
        @type str
        @param itemClickBehavior string describing the item activation behavior (one of
            "default", "doubleclick" or "singleclick") (defaults to "default")
        @type str (optional)
        """
        # step 1: set the style
        style = None
        if styleName != "System" and styleName in QStyleFactory.keys():  # noqa: Y118
            style = QStyleFactory.create(styleName)
        if style is None:
            style = QStyleFactory.create(self.defaultStyleName)

        QApplication.setStyle(
            EricProxyStyle(style=style, itemClickBehavior=itemClickBehavior)
        )

        # step 2: set a style sheet
        ericApp().setStyleSheetFile(styleSheetFile)
