# -*- coding: utf-8 -*-

# Copyright (c) 2015 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dialog for the configuration of a mouse click sequence.
"""

from PyQt6.QtCore import QEvent, Qt, pyqtSlot
from PyQt6.QtWidgets import QDialog, QDialogButtonBox

from eric7.Utilities import MouseUtilities

from .Ui_MouseClickDialog import Ui_MouseClickDialog


class MouseClickDialog(QDialog, Ui_MouseClickDialog):
    """
    Class implementing a dialog for the configuration of a mouse click
    sequence.
    """

    def __init__(self, modifiers, button, parent=None):
        """
        Constructor

        @param modifiers keyboard modifiers of the handler
        @type Qt.KeyboardModifiers
        @param button mouse button of the handler
        @type Qt.MouseButton
        @param parent reference to the parent widget
        @type QWidget
        """
        super().__init__(parent)
        self.setupUi(self)
        self.setModal(True)

        self.clickGroup.installEventFilter(self)
        self.clearButton.installEventFilter(self)
        self.clickEdit.installEventFilter(self)

        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).installEventFilter(
            self
        )
        self.buttonBox.button(
            QDialogButtonBox.StandardButton.Cancel
        ).installEventFilter(self)

        self.__modifiers = modifiers
        self.__button = button

        self.__showClickText()

        msh = self.minimumSizeHint()
        self.resize(max(self.width(), msh.width()), msh.height())

    @pyqtSlot()
    def on_clearButton_clicked(self):
        """
        Private slot to clear the entered sequence.
        """
        self.__modifiers = Qt.KeyboardModifier.NoModifier
        self.__button = Qt.MouseButton.NoButton
        self.__showClickText()

    def __showClickText(self):
        """
        Private method to show a string representing the entered mouse click
        sequence.
        """
        if self.__button == Qt.MouseButton.NoButton:
            self.clickEdit.setText("")
        else:
            self.clickEdit.setText(
                MouseUtilities.MouseButtonModifier2String(
                    self.__modifiers, self.__button
                )
            )

    def eventFilter(self, watched, event):
        """
        Public method called to filter the event queue.

        @param watched reference to the watched object
        @type QObject
        @param event reference to the event that occurred
        @type QEvent
        @return flag indicating a handled event
        @rtype bool
        """
        if event.type() == QEvent.Type.MouseButtonRelease and watched == self.clickEdit:
            self.__modifiers = event.modifiers()
            self.__button = event.button()
            self.__showClickText()
            return True

        return False

    def getClick(self):
        """
        Public method to get the entered mouse click sequence.

        @return tuple containing the modifiers and the mouse button
        @rtype tuple of Qt.KeyboardModifiers and Qt.MouseButton
        """
        return (self.__modifiers, self.__button)
