# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an input widget for network host names.
"""

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtWidgets import QLineEdit


class EricHostnameInputWidget(QLineEdit):
    """
    Class implementing an input widget for network host names.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)

        self.setClearButtonEnabled(True)

        self.setValidator(
            QRegularExpressionValidator(
                QRegularExpression(r"""([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])""")
            )
        )
        self.setMaxLength(63)
