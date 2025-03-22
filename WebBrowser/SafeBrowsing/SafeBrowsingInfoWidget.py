# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to show some threat information.
"""

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMenu, QSizePolicy

from eric7.EricGui import EricPixmapCache


class SafeBrowsingInfoWidget(QMenu):
    """
    Class implementing a widget to show some threat information.
    """

    def __init__(self, info, parent=None):
        """
        Constructor

        @param info information string to be shown
        @type str
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setMinimumWidth(500)

        layout = QHBoxLayout(self)

        iconLabel = QLabel(self)
        iconLabel.setPixmap(EricPixmapCache.getPixmap("safeBrowsing48"))
        layout.addWidget(iconLabel, 0, Qt.AlignmentFlag.AlignTop)

        infoLabel = QLabel(self)
        infoLabel.setWordWrap(True)
        infoLabel.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        infoLabel.setText(info)
        layout.addWidget(infoLabel, 0, Qt.AlignmentFlag.AlignTop)

    def showAt(self, pos):
        """
        Public method to show the widget.

        @param pos position to show at
        @type QPoint
        """
        self.adjustSize()
        xpos = pos.x() - self.width()
        if xpos < 0:
            xpos = 10
        p = QPoint(xpos, pos.y() + 10)
        self.move(p)
        self.show()
