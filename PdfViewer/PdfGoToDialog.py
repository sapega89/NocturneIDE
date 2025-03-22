# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter a PDF page number to jump to.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QSlider,
    QSpinBox,
    QVBoxLayout,
)


class PdfGoToDialog(QDialog):
    """
    Class implementing a dialog to enter a PDF page number to jump to.
    """

    def __init__(self, curPage, pageCount, parent=None):
        """
        Constructor

        @param curPage current page number (0 based)
        @type int
        @param pageCount number of pages in the document
        @type int
        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)

        self.__layout = QVBoxLayout()
        self.setLayout(self.__layout)

        self.__hLayout = QHBoxLayout()
        self.__valueSlider = QSlider(Qt.Orientation.Horizontal)
        self.__valueSlider.setTickPosition(QSlider.TickPosition.TicksBothSides)
        self.__valueSlider.setSingleStep(1)
        self.__valueSlider.setPageStep(10)
        self.__valueSlider.setMinimum(1)
        self.__valueSlider.setMaximum(pageCount)
        self.__valueSlider.setValue(curPage + 1)
        self.__hLayout.addWidget(self.__valueSlider)
        self.__valueSpinBox = QSpinBox()
        self.__valueSpinBox.setMinimum(1)
        self.__valueSpinBox.setMaximum(pageCount)
        self.__valueSpinBox.setValue(curPage + 1)
        self.__valueSpinBox.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.__hLayout.addWidget(self.__valueSpinBox)
        self.__layout.addLayout(self.__hLayout)

        self.__buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            Qt.Orientation.Horizontal,
        )
        self.__layout.addWidget(self.__buttonBox)

        self.__valueSpinBox.setFocus(Qt.FocusReason.OtherFocusReason)

        # connect signals and slots
        self.__buttonBox.accepted.connect(self.accept)
        self.__buttonBox.rejected.connect(self.reject)
        self.__valueSlider.valueChanged.connect(self.__valueSpinBox.setValue)
        self.__valueSpinBox.valueChanged.connect(self.__valueSlider.setValue)

    def getPage(self):
        """
        Public method to get the selected page.

        @return selected page (0 based)
        @rtype int
        """
        return self.__valueSpinBox.value() - 1
