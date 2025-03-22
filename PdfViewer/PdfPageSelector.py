# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a widget to select a PDF page to be shown.
"""

import contextlib

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QIntValidator
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from eric7.EricGui import EricPixmapCache


class PdfPageSelector(QWidget):
    """
    Class implementing a widget to select a PDF page to be shown.

    @signal valueChanged(int) emitted to signal the new value of the selector
    @signal gotoPage() emitted to indicate the want to enter a page number via the
        Go To dialog
    """

    valueChanged = pyqtSignal(int)
    gotoPage = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)

        self.__document = None

        self.__prevButton = QToolButton(self)
        self.__prevButton.setIcon(EricPixmapCache.getIcon("1uparrow"))

        self.__nextButton = QToolButton(self)
        self.__nextButton.setIcon(EricPixmapCache.getIcon("1downarrow"))

        self.__pageButton = QToolButton()
        self.__pageButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)

        self.__pageEntry = QLineEdit()
        self.__pageEntry.setMaximumWidth(50)
        self.__pageEntry.setMaxLength(10)
        self.__pageEntry.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.__pageEntry.setSizePolicy(
            QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed
        )
        self.__pageLabel = QLabel()

        self.__layout = QHBoxLayout()
        self.__layout.addWidget(self.__prevButton)
        self.__layout.addWidget(self.__pageEntry)
        self.__layout.addWidget(self.__pageLabel)
        self.__layout.addWidget(QLabel(self.tr("of")))
        self.__layout.addWidget(self.__pageButton)
        self.__layout.addWidget(self.__nextButton)

        self.setLayout(self.__layout)

        # Setup signal/slot connections
        self.__prevButton.clicked.connect(self.__decrement)
        self.__nextButton.clicked.connect(self.__increment)
        self.__pageButton.clicked.connect(self.__pageButtonTriggered)
        self.__pageEntry.editingFinished.connect(self.__pageEntered)

        self.__initialize()

    def __initialize(self):
        """
        Private method to initialize some internal state.
        """
        self.__value = -1
        self.__minimum = 0
        self.__maximum = 0

        self.__prevButton.setEnabled(False)
        self.__nextButton.setEnabled(False)
        self.__pageEntry.clear()
        self.__pageLabel.clear()
        self.__pageButton.setText(" ")

        self.setEnabled(False)

    def setDocument(self, document):
        """
        Public method to set a reference to the associated PDF document.

        @param document reference to the associated PDF document
        @type QPdfDocument
        """
        self.__document = document
        self.__document.statusChanged.connect(self.__documentStatusChanged)

    @pyqtSlot(int)
    def setValue(self, value):
        """
        Public slot to set the value.

        Note: value is 0 based.

        @param value value to be set
        @type int
        """
        if value != self.__value:
            with contextlib.suppress(RuntimeError):
                self.__pageEntry.setText(self.__document.pageLabel(value))
            self.__pageLabel.setText(str(value + 1))

            self.__value = value

            self.__prevButton.setEnabled(value > self.__minimum)
            self.__nextButton.setEnabled(value < self.__maximum)

            self.valueChanged.emit(value)

    def value(self):
        """
        Public method to get the current value.

        @return current value
        @rtype int
        """
        return self.__value

    def setMaximum(self, maximum):
        """
        Public method to set the maximum value.

        Note: maximum is 0 based.

        @param maximum maximum value to be set
        @type int
        """
        self.__maximum = maximum
        self.__nextButton.setEnabled(self.__value < self.__maximum)
        self.__pageButton.setText(str(maximum + 1))

    @pyqtSlot()
    def __pageEntered(self):
        """
        Private slot to handle the entering of a page value.
        """
        model = self.__document.pageModel()
        start = model.index(0)
        indices = model.match(
            start, QPdfDocument.PageModelRole.Label.value, self.__pageEntry.text()
        )
        if indices:
            self.setValue(indices[0].row())
        else:
            # reset
            blocked = self.__pageEntry.blockSignals(True)
            self.__pageEntry.setText(self.__document.pageLabel(self.__value))
            self.__pageEntry.blockSignals(blocked)

    @pyqtSlot()
    def __decrement(self):
        """
        Private slot to decrement the current value.
        """
        if self.__value > self.__minimum:
            self.setValue(self.__value - 1)

    @pyqtSlot()
    def __increment(self):
        """
        Private slot to increment the current value.
        """
        if self.__value < self.__maximum:
            self.setValue(self.__value + 1)

    @pyqtSlot()
    def __pageButtonTriggered(self):
        """
        Private slot to handle the page button trigger.
        """
        self.gotoPage.emit()

    @pyqtSlot(QPdfDocument.Status)
    def __documentStatusChanged(self, status):
        """
        Private slot to handle a change of the document status.

        @param status current document status
        @type QPdfDocument.Status
        """
        self.setEnabled(status == QPdfDocument.Status.Ready)
        if status == QPdfDocument.Status.Ready:
            numericalEntry = True
            # test the first page
            try:
                _ = int(self.__document.pageLabel(0))
            except ValueError:
                numericalEntry = False
            # test the last page
            try:
                _ = int(self.__document.pageLabel(self.__document.pageCount() - 1))
            except ValueError:
                numericalEntry = False
            self.__pageEntry.setValidator(
                QIntValidator(1, 99999) if numericalEntry else None
            )
            self.__pageLabel.setVisible(not numericalEntry)
        elif status == QPdfDocument.Status.Null:
            self.__initialize()
