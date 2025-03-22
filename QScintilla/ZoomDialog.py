# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to select the zoom scale.
"""

from PyQt6.QtWidgets import QDialog

from .Ui_ZoomDialog import Ui_ZoomDialog


class ZoomDialog(QDialog, Ui_ZoomDialog):
    """
    Class implementing a dialog to select the zoom scale.
    """

    def __init__(self, zoom, parent, name=None, modal=False):
        """
        Constructor

        @param zoom zoom factor to show in the spinbox
        @type int
        @param parent parent widget of this dialog
        @type QWidget
        @param name name of this dialog
        @type str
        @param modal modal dialog state
        @type bool
        """
        super().__init__(parent)
        if name:
            self.setObjectName(name)
        self.setupUi(self)
        self.setModal(modal)

        self.zoomSpinBox.setValue(zoom)
        self.zoomSpinBox.selectAll()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def getZoomSize(self):
        """
        Public method to retrieve the zoom size.

        @return zoom size
        @rtype int
        """
        return self.zoomSpinBox.value()
