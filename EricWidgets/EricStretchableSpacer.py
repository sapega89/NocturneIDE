# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a stretchable spacer widget.
"""

from PyQt6.QtWidgets import QHBoxLayout, QWidget


class EricStretchableSpacer(QWidget):
    """
    Class implementing a stretchable spacer widget.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)

        self.__layout = QHBoxLayout()
        self.__layout.setContentsMargins(0, 0, 0, 0)
        self.__layout.addStretch()

        self.setLayout(self.__layout)
