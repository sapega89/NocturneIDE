# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the label to show some SSL info (if available).
"""

from PyQt6.QtCore import Qt

from eric7.EricWidgets.EricClickableLabel import EricClickableLabel


class SslLabel(EricClickableLabel):
    """
    Class implementing the label to show some SSL info (if available).
    """

    okStyle = "QLabel { color : white; background-color : green; }"
    nokStyle = "QLabel { color : white; background-color : red; }"

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def setValidity(self, valid):
        """
        Public method to set the validity indication.

        @param valid flag indicating the certificate validity
        @type bool
        """
        if valid:
            self.setStyleSheet(SslLabel.okStyle)
        else:
            self.setStyleSheet(SslLabel.nokStyle)
