# -*- coding: utf-8 -*-

# Copyright (c) 2012 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a clickable label.
"""

from PyQt6.QtCore import QPoint, Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel


class EricClickableLabel(QLabel):
    """
    Class implementing a clickable label.

    @signal clicked(QPoint) emitted upon a click on the label
        with the left button
    @signal middleClicked(QPoint) emitted upon a click on the label
        with the middle button or CTRL and left button
    """

    clicked = pyqtSignal(QPoint)
    middleClicked = pyqtSignal(QPoint)

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mouseReleaseEvent(self, evt):
        """
        Protected method handling mouse release events.

        @param evt mouse event
        @type QMouseEvent
        """
        if evt.button() == Qt.MouseButton.LeftButton and self.rect().contains(
            evt.position().toPoint()
        ):
            if evt.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self.middleClicked.emit(evt.globalPosition().toPoint())
            else:
                self.clicked.emit(evt.globalPosition().toPoint())
        elif evt.button() == Qt.MouseButton.MiddleButton and self.rect().contains(
            evt.position().toPoint()
        ):
            self.middleClicked.emit(evt.globalPosition().toPoint())
        else:
            super().mouseReleaseEvent(evt)
