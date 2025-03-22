# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to select a PDF zoom factor.
"""

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWidgets import QComboBox


class PdfZoomSelector(QComboBox):
    """
    Class implementing a widget to select a PDF zoom factor.

    @signal zoomFactorChanged(factor) emitted to indicate the selected zoom factor
    @signal zoomModeChanged(zoomMode) emitted to indicate the selected zoom mode
    """

    zoomFactorChanged = pyqtSignal(float)
    zoomModeChanged = pyqtSignal(QPdfView.ZoomMode)

    ZoomValues = (
        0.12,
        0.25,
        0.33,
        0.5,
        0.66,
        0.75,
        1.0,
        1.25,
        1.50,
        2.0,
        4.0,
        8.0,
        16.0,
        25.0,
        50.0,
    )

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)

        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)

        self.__pageWidthLabel = self.tr("Page Width")
        self.__wholePageLabel = self.tr("Whole Page")

        self.addItem(self.__pageWidthLabel)
        self.addItem(self.__wholePageLabel)
        for val in PdfZoomSelector.ZoomValues:
            self.addItem(self.tr("{0}%").format(int(val * 100)))

        self.lineEdit().setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.currentIndexChanged.connect(self.__editingFinished)
        self.lineEdit().editingFinished.connect(self.__editingFinished)

    @pyqtSlot()
    def __editingFinished(self):
        """
        Private slot handling the end of entering a zoom factor.
        """
        self.__processText(self.lineEdit().text())

    @pyqtSlot(str)
    def __processText(self, text):
        """
        Private slot to handle the change of the entered zoom factor.

        @param text text to be handled
        @type str
        """
        if text == self.__pageWidthLabel:
            self.zoomModeChanged.emit(QPdfView.ZoomMode.FitToWidth)
        elif text == self.__wholePageLabel:
            self.zoomModeChanged.emit(QPdfView.ZoomMode.FitInView)
        else:
            withoutPercent = text.replace("%", "").replace("&", "")
            try:
                zoomLevel = int(withoutPercent)
                factor = zoomLevel / 100.0
            except ValueError:
                factor = 1.0

            self.zoomModeChanged.emit(QPdfView.ZoomMode.Custom)
            self.zoomFactorChanged.emit(factor)

    @pyqtSlot()
    def reset(self):
        """
        Public slot to reset the zoom factor to 100%.
        """
        self.setCurrentIndex(8)  # index 8 is 100%
        self.__editingFinished()

    @pyqtSlot(float)
    @pyqtSlot("qreal")
    def setZoomFactor(self, zoomFactor):
        """
        Public slot to set the current zoom factor.

        @param zoomFactor current zoom factor
        @type float
        """
        self.setCurrentText(self.tr("{0}%").format(round(zoomFactor * 100)))
        self.__editingFinished()

    @pyqtSlot(QPdfView.ZoomMode)
    def setZoomMode(self, zoomMode):
        """
        Public slot to set the zoom value iaw. the zoom mode.

        @param zoomMode current zoom mode
        @type QPdfView.ZoomMode
        """
        if zoomMode == QPdfView.ZoomMode.FitToWidth:
            self.setCurrentIndex(0)  # index 0 is 'Page Width'
        elif zoomMode == QPdfView.ZoomMode.FitInView:
            self.setCurrentIndex(1)  # index 1 is 'Whole Page'
        else:
            # ignore Custom mode here
            return
        self.__editingFinished()
