# -*- coding: utf-8 -*-

# Copyright (c) 2024 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a QTextBrowser widget that resizes automatically.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QSizePolicy, QTextBrowser


class EricAutoResizeTextBrowser(QTextBrowser):
    """
    Class implementing a QTextBrowser widget that adjusts its size automatically to the
    contained text.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent=parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self.textChanged.connect(self.updateGeometry)

    def resizeEvent(self, evt):
        """
        Protected method to handle resize events.

        @param evt reference to the resize event
        @type QResizeEvent
        """
        super().resizeEvent(evt)
        self.updateGeometry()

    def updateGeometry(self):
        """
        Public method to update the geometry depending on the current text.
        """
        # Set the text width of the document to match the width of the text browser.
        self.document().setTextWidth(
            self.width() - 2 * int(self.document().documentMargin())
        )

        # Get the document height and set it as the fixed height of the text browser.
        docHeight = self.document().size().height()
        self.setFixedHeight(int(docHeight))

        # Call the base class updateGeometry() method.
        super().updateGeometry()
