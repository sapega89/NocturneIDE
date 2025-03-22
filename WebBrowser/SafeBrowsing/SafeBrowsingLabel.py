# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the label to show some SSL info.
"""

from PyQt6.QtCore import QPoint, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QLabel


class SafeBrowsingLabel(QLabel):
    """
    Class implementing a label to show some Safe Browsing info.

    @signal clicked(pos) emitted to indicate a click of the label (QPoint)
    """

    clicked = pyqtSignal(QPoint)

    nokStyle = "QLabel { color : white; background-color : red; }"

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setStyleSheet(SafeBrowsingLabel.nokStyle)

        self.__threatType = ""
        self.__threatMessages = ""

        self.__deafultText = self.tr("Malicious Site")
        self.__updateLabel()

    def mouseReleaseEvent(self, evt):
        """
        Protected method to handle mouse release events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(evt.globalPosition().toPoint())
        else:
            super().mouseReleaseEvent(evt)

    def mouseDoubleClickEvent(self, evt):
        """
        Protected method to handle mouse double click events.

        @param evt reference to the mouse event
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(evt.globalPosition().toPoint())
        else:
            super().mouseDoubleClickEvent(evt)

    @pyqtSlot()
    def __updateLabel(self):
        """
        Private slot to update the label text.
        """
        if self.__threatType:
            self.setText(self.__threatType)
        else:
            self.setText(self.__deafultText)

    @pyqtSlot(str, str)
    def setThreatInfo(self, threatType, threatMessages):
        """
        Public slot to set threat information.

        @param threatType threat type
        @type str
        @param threatMessages more verbose info about detected threats
        @type str
        """
        self.__threatType = threatType
        self.__threatMessages = threatMessages

        self.__updateLabel()

    def getThreatInfo(self):
        """
        Public method to get the threat info text.

        @return threat info text
        @rtype str
        """
        return self.__threatMessages
