# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a button alternating between reload and stop.
"""

from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot

from eric7.EricGui import EricPixmapCache
from eric7.EricWidgets.EricToolButton import EricToolButton


class ReloadStopButton(EricToolButton):
    """
    Class implementing a button alternating between reload and stop.

    @signal reloadClicked() emitted to initiate a reload action
    @signal stopClicked() emitted to initiate a stop action
    """

    reloadClicked = pyqtSignal()
    stopClicked = pyqtSignal()

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.setObjectName("navigation_reloadstop_button")
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAutoRaise(True)

        self.__loading = False

        self.clicked.connect(self.__buttonClicked)

        self.__updateButton()

    @pyqtSlot()
    def __buttonClicked(self):
        """
        Private slot handling a user clicking the button.
        """
        if self.__loading:
            self.stopClicked.emit()
        else:
            self.reloadClicked.emit()

    @pyqtSlot()
    def __updateButton(self):
        """
        Private slot to update the button.
        """
        if self.__loading:
            self.setIcon(EricPixmapCache.getIcon("stopLoading"))
            self.setToolTip(self.tr("Stop loading"))
        else:
            self.setIcon(EricPixmapCache.getIcon("reload"))
            self.setToolTip(self.tr("Reload the current screen"))

    def setLoading(self, loading):
        """
        Public method to set the loading state.

        @param loading flag indicating the new loading state
        @type bool
        """
        self.__loading = loading
        self.__updateButton()
