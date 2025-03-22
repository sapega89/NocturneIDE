# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog to enter data to insert a hyperlink.
"""

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from .Ui_HyperlinkMarkupDialog import Ui_HyperlinkMarkupDialog


class HyperlinkMarkupDialog(QDialog, Ui_HyperlinkMarkupDialog):
    """
    Class implementing a dialog to enter data to insert a hyperlink.
    """

    def __init__(self, textMayBeEmpty, targetMayBeEmpty, noTitle=False, parent=None):
        """
        Constructor

        @param textMayBeEmpty flag indicating, that the link text may
            be empty
        @type bool
        @param targetMayBeEmpty flag indicating, that the link target may
            be empty
        @type bool
        @param noTitle flag indicating, that no title is supported
        @type bool
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)

        self.__allowEmptyText = textMayBeEmpty
        self.__allowEmptyTarget = targetMayBeEmpty

        self.titelEdit.setEnabled(not noTitle)

        self.__updateOkButton()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    def __updateOkButton(self):
        """
        Private method to update the state of the OK button.
        """
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            (bool(self.textEdit.text()) or self.__allowEmptyText)
            and (bool(self.targetEdit.text()) or self.__allowEmptyTarget)
        )

    @pyqtSlot(str)
    def on_textEdit_textChanged(self, _txt):
        """
        Private slot handling a change of the link text.

        @param _txt link text (unused)
        @type str
        """
        self.__updateOkButton()

    @pyqtSlot(str)
    def on_targetEdit_textChanged(self, _txt):
        """
        Private slot handling a change of the link target.

        @param _txt link target (unused)
        @type str
        """
        self.__updateOkButton()

    def getData(self):
        """
        Public method to get the entered data.

        @return tuple containing the link text, link target and the optional
            link title
        @rtype tuple of (str, str, str)
        """
        return (self.textEdit.text(), self.targetEdit.text(), self.titelEdit.text())
