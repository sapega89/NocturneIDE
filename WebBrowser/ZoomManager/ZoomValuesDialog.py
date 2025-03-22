# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to show all saved zoom values.
"""

from PyQt6.QtCore import QSortFilterProxyModel
from PyQt6.QtGui import QFont, QFontMetrics
from PyQt6.QtWidgets import QDialog

from .Ui_ZoomValuesDialog import Ui_ZoomValuesDialog


class ZoomValuesDialog(QDialog, Ui_ZoomValuesDialog):
    """
    Class implementing a dialog to show all saved zoom values.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        from eric7.WebBrowser.ZoomManager import ZoomManager

        from .ZoomValuesModel import ZoomValuesModel

        super().__init__(parent)
        self.setupUi(self)

        self.removeButton.clicked.connect(self.zoomValuesTable.removeSelected)
        self.removeAllButton.clicked.connect(self.zoomValuesTable.removeAll)

        self.zoomValuesTable.verticalHeader().hide()
        self.__zoomValuesModel = ZoomValuesModel(ZoomManager.instance(), self)
        self.__proxyModel = QSortFilterProxyModel(self)
        self.__proxyModel.setSourceModel(self.__zoomValuesModel)
        self.searchEdit.textChanged.connect(self.__proxyModel.setFilterFixedString)
        self.zoomValuesTable.setModel(self.__proxyModel)

        fm = QFontMetrics(QFont())
        height = fm.height() + fm.height() // 3
        self.zoomValuesTable.verticalHeader().setDefaultSectionSize(height)
        self.zoomValuesTable.verticalHeader().setMinimumSectionSize(-1)

        self.__calculateHeaderSizes()

    def __calculateHeaderSizes(self):
        """
        Private method to calculate the section sizes of the horizontal header.
        """
        fm = QFontMetrics(QFont())
        for section in range(self.__zoomValuesModel.columnCount()):
            header = self.zoomValuesTable.horizontalHeader().sectionSizeHint(section)
            if section == 0:
                header = fm.horizontalAdvance("extraveryveryverylongsitename")
            elif section == 1:
                header = fm.horizontalAdvance("averagelongzoomvalue")
            buffer = fm.horizontalAdvance("mm")
            header += buffer
            self.zoomValuesTable.horizontalHeader().resizeSection(section, header)
        self.zoomValuesTable.horizontalHeader().setStretchLastSection(True)
