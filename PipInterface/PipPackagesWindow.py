# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing the standalone pip packages management window.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialogButtonBox, QVBoxLayout, QWidget

from eric7.EricWidgets.EricApplication import ericApp
from eric7.EricWidgets.EricMainWindow import EricMainWindow
from eric7.PipInterface.Pip import Pip
from eric7.PipInterface.PipPackagesWidget import PipPackagesWidget
from eric7.VirtualEnv.VirtualenvManager import VirtualenvManager


class PipPackagesWindow(EricMainWindow):
    """
    Main window class for the standalone  pip packages manager.
    """

    def __init__(self, parent=None):
        """
        Constructor

        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)

        self.__pip = Pip(self)
        ericApp().registerObject("Pip", self.__pip)

        self.__venvManager = VirtualenvManager(self)
        ericApp().registerObject("VirtualEnvManager", self.__venvManager)

        self.__centralWidget = QWidget(self)
        self.__layout = QVBoxLayout(self.__centralWidget)
        self.__centralWidget.setLayout(self.__layout)

        self.__pipPackagesWidget = PipPackagesWidget(
            self.__pip, parent=self.__centralWidget
        )
        self.__layout.addWidget(self.__pipPackagesWidget)

        self.__buttonBox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, Qt.Orientation.Horizontal, self
        )
        self.__layout.addWidget(self.__buttonBox)

        self.setCentralWidget(self.__centralWidget)
        self.resize(700, 900)
        self.setWindowTitle(self.tr("Manage Packages"))

        self.__buttonBox.accepted.connect(self.close)
        self.__buttonBox.rejected.connect(self.close)

    def closeEvent(self, evt):
        """
        Protected method handling a close event.

        @param evt reference to the close event object
        @type QCloseEvent
        """
        self.__pip.shutdown()
