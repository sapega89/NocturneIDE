# -*- coding: utf-8 -*-

# Copyright (c) 2006 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a splashscreen for eric.
"""

import os.path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from PyQt6.QtWidgets import QApplication, QSplashScreen

from eric7.Globals import getConfig


class SplashScreen(QSplashScreen):
    """
    Class implementing a splashscreen for eric.
    """

    def __init__(self):
        """
        Constructor
        """
        ericPic = QPixmap(os.path.join(getConfig("ericPixDir"), "ericSplash.png"))
        self.labelAlignment = (
            Qt.AlignmentFlag.AlignBottom
            | Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignAbsolute
        )
        super().__init__(ericPic)
        self.show()
        QApplication.processEvents()

    def showMessage(self, msg):
        """
        Public method to show a message in the bottom part of the splashscreen.

        @param msg message to be shown
        @type str
        """
        super().showMessage(msg, self.labelAlignment, QColor(Qt.GlobalColor.white))
        QApplication.processEvents()

    def clearMessage(self):
        """
        Public method to clear the message shown.
        """
        super().clearMessage()
        QApplication.processEvents()


class NoneSplashScreen:
    """
    Class implementing a "None" splashscreen for eric.

    This class implements the same interface as the real splashscreen,
    but simply does nothing.
    """

    def __init__(self):
        """
        Constructor
        """
        pass

    def showMessage(self, msg):
        """
        Public method to show a message in the bottom part of the splashscreen.

        @param msg message to be shown
        @type str
        """
        pass

    def clearMessage(self):
        """
        Public method to clear the message shown.
        """
        pass

    def finish(self, _widget):
        """
        Public method to finish the splash screen.

        @param _widget widget to wait for (unused)
        @type QWidget
        """
        pass
