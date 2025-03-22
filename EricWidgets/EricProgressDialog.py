# -*- coding: utf-8 -*-

# Copyright (c) 2013 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a progress dialog allowing a customized progress bar label.
"""

from PyQt6.QtCore import QCoreApplication, Qt
from PyQt6.QtWidgets import QProgressBar, QProgressDialog


class EricProgressDialog(QProgressDialog):
    """
    Class implementing a progress dialog allowing a customized progress bar
    label.
    """

    def __init__(
        self,
        labelText,
        cancelButtonText,
        minimum,
        maximum,
        labelFormat=None,
        parent=None,
        flags=None,
    ):
        """
        Constructor

        @param labelText text of the dialog label
        @type str
        @param cancelButtonText text of the cancel button
        @type str
        @param minimum minimum value
        @type int
        @param maximum maximum value
        @type int
        @param labelFormat label format of the progress bar
        @type str
        @param parent reference to the parent widget
        @type QWidget
        @param flags window flags of the dialog
        @type Qt.WindowFlags
        """
        if parent is None:
            parent = QCoreApplication.instance().getMainWindow()

        if flags is None:
            flags = Qt.WindowType(0)
        super().__init__(labelText, cancelButtonText, minimum, maximum, parent, flags)

        self.__progressBar = QProgressBar(self)
        self.__progressBar.setMinimum(minimum)
        self.__progressBar.setMaximum(maximum)
        if labelFormat:
            self.__progressBar.setFormat(labelFormat)

        self.setBar(self.__progressBar)

    def format(self):
        """
        Public method to get the progress bar format.

        @return progress bar format
        @rtype str
        """
        return self.__progressBar.format()

    def setFormat(self, labelFormat):
        """
        Public method to set the progress bar format.

        @param labelFormat progress bar format
        @type str
        """
        self.__progressBar.setFormat(labelFormat)
