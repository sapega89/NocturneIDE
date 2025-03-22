# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show defined test markers.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem, QWidget

from .Ui_MarkersWindow import Ui_MarkersWindow


class MarkersWindow(QWidget, Ui_MarkersWindow):
    """
    Class documentation goes here.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget (defaults to None)
        @type QWidget (optional)
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__lastGeometry = None

    def showMarkers(self, markers):
        """
        Public method to show the dialog with the given markers.

        @param markers dictionary containing the markers and their descriptions
        @type dict
        """
        self.markersList.clear()

        for marker, description in markers.items():
            QTreeWidgetItem(self.markersList, [marker, description])

        self.markersList.setColumnWidth(0, 250)
        self.markersList.resizeColumnToContents(1)

        self.markersList.sortItems(0, Qt.SortOrder.AscendingOrder)

        if self.__lastGeometry is not None:
            self.restoreGeometry(self.__lastGeometry)

        self.show()

    def closeEvent(self, _evt):
        """
        Protected slot implementing a close event handler.

        @param _evt close event (unused)
        @type QCloseEvent
        """
        self.__lastGeometry = self.saveGeometry()
